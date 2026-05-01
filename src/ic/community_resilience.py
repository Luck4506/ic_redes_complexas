from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import approximate_global_efficiency, edge_length_m, simple_undirected_min_length_graph


def _read_node_communities(path: str) -> dict[str, int]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Comunidades nao encontradas: {path}. Execute antes: ic communities --city <cidade>."
        )

    mapping: dict[str, int] = {}
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node = row.get("node")
            community = row.get("community_id")
            if node in (None, "") or community in (None, ""):
                continue
            mapping[str(node)] = int(community)
    return mapping


def _node_community(node: Any, mapping: dict[str, int]) -> int | None:
    return mapping.get(str(node))


def _largest_component_weighted_fraction(G: nx.Graph) -> tuple[int, float]:
    if G.number_of_nodes() == 0:
        return 0, 0.0

    total_size = sum(float(data.get("size", 0.0)) for _, data in G.nodes(data=True))
    largest_nodes = max(nx.connected_components(G), key=len)
    largest_size = sum(float(G.nodes[n].get("size", 0.0)) for n in largest_nodes)
    return len(largest_nodes), largest_size / total_size if total_size else 0.0


def _community_lcc_stats(G: nx.Graph) -> tuple[int, int, float, int]:
    if G.number_of_nodes() == 0:
        return 0, 0, 0.0, 0
    components = list(nx.connected_components(G))
    lcc_count, lcc_node_fraction = _largest_component_weighted_fraction(G)
    return lcc_count, len(components), lcc_node_fraction, max((len(c) for c in components), default=0)


def _build_community_graph(
    G: nx.Graph,
    node_to_comm: dict[str, int],
    min_size: int,
) -> tuple[nx.Graph, list[dict[str, Any]], dict[int, int]]:
    community_sizes = Counter(
        comm for node in G.nodes() if (comm := _node_community(node, node_to_comm)) is not None
    )
    included = {comm for comm, size in community_sizes.items() if size >= min_size}

    C = nx.Graph()
    for comm in sorted(included):
        C.add_node(comm, size=community_sizes[comm])

    internal_edges = Counter()
    boundary_edges = Counter()
    boundary_length = defaultdict(float)

    for u, v, data in G.edges(data=True):
        cu = _node_community(u, node_to_comm)
        cv = _node_community(v, node_to_comm)
        if cu is None or cv is None or cu not in included or cv not in included:
            continue

        length = edge_length_m(data)
        if cu == cv:
            internal_edges[cu] += 1
            continue

        boundary_edges[cu] += 1
        boundary_edges[cv] += 1
        boundary_length[cu] += length
        boundary_length[cv] += length

        a, b = sorted((cu, cv))
        if C.has_edge(a, b):
            edge_data = C[a][b]
            edge_data["edge_count"] += 1
            edge_data["total_length_m"] += length
            edge_data["length"] = min(edge_data["length"], length)
        else:
            C.add_edge(a, b, edge_count=1, total_length_m=length, length=length)

    summary_rows = []
    for comm in sorted(included):
        summary_rows.append(
            {
                "community_id": comm,
                "size": community_sizes[comm],
                "community_degree": C.degree(comm),
                "internal_edges": internal_edges[comm],
                "boundary_edges": boundary_edges[comm],
                "boundary_length_m": boundary_length[comm],
            }
        )

    return C, summary_rows, dict(community_sizes)


def _removal_order(G: nx.Graph, strategy: str, seed: int, rng: random.Random) -> list[tuple[int, int]]:
    edges = list(G.edges())
    if strategy == "random":
        rng.shuffle(edges)
        return edges
    eb = nx.edge_betweenness_centrality(G, normalized=True, weight=None)
    return [edge for edge, _ in sorted(eb.items(), key=lambda item: item[1], reverse=True)]


def _remove_adaptive_batch(G: nx.Graph, batch_size: int) -> int:
    if batch_size <= 0 or G.number_of_edges() == 0:
        return 0
    eb = nx.edge_betweenness_centrality(G, normalized=True, weight=None)
    selected = [edge for edge, _ in sorted(eb.items(), key=lambda item: item[1], reverse=True)[:batch_size]]
    G.remove_edges_from(selected)
    return len(selected)


def testar_resiliencia_comunidades(
    city_id: str,
    strategy: str = "targeted",
    max_fraction: float = 0.30,
    steps: int = 15,
    min_size: int = 30,
    seed: int = 42,
) -> dict:
    """Resiliência do grafo agregado de comunidades."""
    ensure_city_dirs(city_id)
    if strategy not in {"random", "targeted", "targeted_adaptive"}:
        raise ValueError("strategy deve ser 'random', 'targeted' ou 'targeted_adaptive'.")
    if not 0 < max_fraction <= 1:
        raise ValueError("max_fraction deve estar no intervalo (0, 1].")

    graph_path = f"data/graphs/{city_id}_drive_clean.graphml"
    communities_path = f"outputs/{city_id}/metrics/nodes_communities.csv"

    print(f"[E7C] Carregando grafo: {graph_path}", flush=True)
    G_dir = load_graphml(graph_path)
    G = simple_undirected_min_length_graph(G_dir)
    node_to_comm = _read_node_communities(communities_path)
    C, summary_rows, community_sizes = _build_community_graph(G, node_to_comm, min_size=min_size)

    n0 = C.number_of_nodes()
    m0 = C.number_of_edges()
    print(f"[E7C] Grafo de comunidades: comunidades={n0} conexoes={m0} min_size={min_size}", flush=True)

    if n0 == 0:
        raise RuntimeError("Nenhuma comunidade passou pelo filtro min_size.")

    rng = random.Random(seed)
    removal_order = _removal_order(C, strategy, seed, rng) if strategy != "targeted_adaptive" else []

    max_remove = max(1, int(max_fraction * m0)) if m0 else 0
    steps = max(2, steps)
    removals = [int(round(i * max_remove / (steps - 1))) for i in range(steps)]
    removals = sorted(set(removals))

    H = C.copy()
    removed = 0
    eff0 = approximate_global_efficiency(H, samples=n0, seed=seed)
    eff_len0 = approximate_global_efficiency(H, samples=n0, seed=seed, weight="length")

    records = []

    def add_record() -> None:
        lcc_count, num_components, lcc_nodes_fraction, lcc_communities = _community_lcc_stats(H)
        eff = approximate_global_efficiency(H, samples=n0, seed=seed)
        eff_len = approximate_global_efficiency(H, samples=n0, seed=seed, weight="length")
        records.append(
            {
                "removed_edges": removed,
                "removed_fraction": removed / m0 if m0 else 0.0,
                "lcc_communities": lcc_communities,
                "lcc_communities_fraction": lcc_count / n0 if n0 else 0.0,
                "lcc_nodes_fraction": lcc_nodes_fraction,
                "num_components": num_components,
                "efficiency_topological": eff,
                "efficiency_topological_retained": eff / eff0 if eff0 else 0.0,
                "efficiency_length": eff_len,
                "efficiency_length_retained": eff_len / eff_len0 if eff_len0 else 0.0,
            }
        )

    add_record()

    for target_removed in removals[1:]:
        if strategy == "targeted_adaptive":
            removed += _remove_adaptive_batch(H, target_removed - removed)
        else:
            while removed < target_removed and removed < len(removal_order):
                u, v = removal_order[removed]
                if H.has_edge(u, v):
                    H.remove_edge(u, v)
                removed += 1
        add_record()
        last = records[-1]
        print(
            f"[E7C] removidas={removed}/{m0} | LCC comunidades={last['lcc_communities_fraction']:.3f} "
            f"| LCC nos={last['lcc_nodes_fraction']:.3f} | comps={last['num_components']}",
            flush=True,
        )

    metrics_dir = f"outputs/{city_id}/metrics"
    figures_dir = f"outputs/{city_id}/figures"
    logs_dir = f"outputs/{city_id}/logs"
    Path(metrics_dir).mkdir(parents=True, exist_ok=True)
    Path(figures_dir).mkdir(parents=True, exist_ok=True)
    Path(logs_dir).mkdir(parents=True, exist_ok=True)

    curve_csv = f"{metrics_dir}/community_resilience_curve_{strategy}.csv"
    summary_csv = f"{metrics_dir}/community_resilience_summary.csv"
    top_edges_csv = f"{metrics_dir}/community_resilience_top_edges.csv"
    plot_path = f"{figures_dir}/community_resilience_curve_{strategy}.png"
    report_txt = f"{logs_dir}/community_resilience_report_{strategy}.txt"

    with open(curve_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["community_id", "size", "community_degree", "internal_edges", "boundary_edges", "boundary_length_m"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    eb = nx.edge_betweenness_centrality(C, normalized=True, weight=None) if C.number_of_edges() else {}
    with open(top_edges_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "source_community",
            "target_community",
            "source_size",
            "target_size",
            "edge_count",
            "total_length_m",
            "min_length_m",
            "edge_betweenness",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for (u, v), score in sorted(eb.items(), key=lambda item: item[1], reverse=True):
            data = C[u][v]
            writer.writerow(
                {
                    "source_community": u,
                    "target_community": v,
                    "source_size": community_sizes.get(u, 0),
                    "target_size": community_sizes.get(v, 0),
                    "edge_count": data.get("edge_count", 0),
                    "total_length_m": data.get("total_length_m", 0.0),
                    "min_length_m": data.get("length", 0.0),
                    "edge_betweenness": score,
                }
            )

    xs = [row["removed_fraction"] for row in records]
    ys_comm = [row["lcc_communities_fraction"] for row in records]
    ys_nodes = [row["lcc_nodes_fraction"] for row in records]
    plt.figure()
    plt.plot(xs, ys_comm, marker="o", label="Comunidades")
    plt.plot(xs, ys_nodes, marker="s", label="Nós representados")
    plt.xlabel("Fração de conexões entre comunidades removidas")
    plt.ylabel("Fração na maior componente")
    plt.title(f"Resiliência por comunidades ({city_id}) — {strategy}")
    plt.grid(True)
    plt.legend()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("=== Resiliência por Comunidades ===\n\n")
        f.write(f"Entrada grafo: {graph_path}\n")
        f.write(f"Entrada comunidades: {communities_path}\n")
        f.write(f"Estratégia: {strategy}\n")
        f.write(f"Comunidades analisadas: {n0}\n")
        f.write(f"Conexões entre comunidades: {m0}\n")
        f.write(f"min_size: {min_size}\n")
        f.write(f"max_fraction: {max_fraction}\n")
        f.write(f"steps: {steps}\n\n")
        f.write("Interpretação: cada comunidade é um nó do grafo agregado; arestas representam conexões viárias entre comunidades.\n")
        f.write("lcc_nodes_fraction pondera a maior componente pelo tamanho das comunidades, não só pela contagem de comunidades.\n\n")
        f.write("Último ponto:\n")
        for key, value in records[-1].items():
            f.write(f"  {key} = {value}\n")

    return {
        "curve_csv": curve_csv,
        "summary_csv": summary_csv,
        "top_edges_csv": top_edges_csv,
        "curve_plot": plot_path,
        "report_txt": report_txt,
    }
