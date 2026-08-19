from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from .community_resilience import _node_community, _read_node_communities
from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml
from .metric_graphs import approximate_global_efficiency, simple_undirected_min_length_graph
from .resilience import _largest_cc_stats


def _normalized_auc(records: list[dict[str, Any]], metric: str) -> float:
    """Area media sob a curva no intervalo efetivamente simulado."""
    if len(records) < 2:
        return float(records[0][metric]) if records else 0.0

    area = 0.0
    for left, right in zip(records, records[1:]):
        width = float(right["removed_fraction"]) - float(left["removed_fraction"])
        area += width * (float(left[metric]) + float(right[metric])) / 2.0
    interval = float(records[-1]["removed_fraction"]) - float(records[0]["removed_fraction"])
    return area / interval if interval > 0 else float(records[-1][metric])


def _removal_order(
    G: nx.Graph,
    strategy: str,
    k_edge: int,
    seed: int,
    rng: random.Random,
) -> list[tuple[Any, Any]]:
    edges = list(G.edges())
    if strategy == "random":
        rng.shuffle(edges)
        return edges
    k = max(1, min(k_edge, G.number_of_nodes()))
    centrality = nx.edge_betweenness_centrality(G, k=k, normalized=True, seed=seed)
    return [edge for edge, _ in sorted(centrality.items(), key=lambda item: item[1], reverse=True)]


def _remove_adaptive_batch(G: nx.Graph, batch_size: int, k_edge: int, seed: int) -> int:
    if batch_size <= 0 or G.number_of_edges() == 0:
        return 0
    k = max(1, min(k_edge, G.number_of_nodes()))
    centrality = nx.edge_betweenness_centrality(G, k=k, normalized=True, seed=seed)
    selected = [edge for edge, _ in sorted(centrality.items(), key=lambda item: item[1], reverse=True)[:batch_size]]
    G.remove_edges_from(selected)
    return len(selected)


def _simulate_community(
    community_id: int,
    G0: nx.Graph,
    strategy: str,
    max_fraction: float,
    steps: int,
    k_edge: int,
    efficiency_samples: int,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    n0 = G0.number_of_nodes()
    m0 = G0.number_of_edges()
    rng = random.Random(seed + community_id)

    if strategy in {"random", "targeted"}:
        removal_order = _removal_order(G0, strategy, k_edge, seed + community_id, rng)
    elif strategy == "targeted_adaptive":
        removal_order = []
    else:
        raise ValueError("strategy deve ser 'random', 'targeted' ou 'targeted_adaptive'.")

    max_remove = min(m0, max(1, int(max_fraction * m0))) if m0 else 0
    removals = sorted(set(int(round(i * max_remove / (max(2, steps) - 1))) for i in range(max(2, steps))))

    G = G0.copy()
    removed = 0
    samples = min(max(1, efficiency_samples), n0)
    eff0 = approximate_global_efficiency(G, samples=samples, seed=seed)
    eff_len0 = approximate_global_efficiency(G, samples=samples, seed=seed, weight="length")
    records: list[dict[str, Any]] = []

    def add_record() -> None:
        lcc_size, num_components = _largest_cc_stats(G)
        eff = approximate_global_efficiency(G, samples=samples, seed=seed)
        eff_len = approximate_global_efficiency(G, samples=samples, seed=seed, weight="length")
        records.append(
            {
                "community_id": community_id,
                "community_nodes": n0,
                "initial_internal_edges": m0,
                "removed_edges": removed,
                "removed_fraction": removed / m0 if m0 else 0.0,
                "lcc_size": lcc_size,
                "lcc_fraction": lcc_size / n0 if n0 else 0.0,
                "num_components": num_components,
                "efficiency_topological_retained": eff / eff0 if eff0 else 0.0,
                "efficiency_length_retained": eff_len / eff_len0 if eff_len0 else 0.0,
            }
        )

    add_record()
    for target_removed in removals[1:]:
        if strategy == "targeted_adaptive":
            removed += _remove_adaptive_batch(G, target_removed - removed, k_edge, seed + community_id)
        else:
            while removed < target_removed and removed < len(removal_order):
                u, v = removal_order[removed]
                if G.has_edge(u, v):
                    G.remove_edge(u, v)
                removed += 1
        add_record()

    final = records[-1]
    summary = {
        "community_id": community_id,
        "nodes": n0,
        "internal_edges": m0,
        "initial_components": records[0]["num_components"],
        "tested_removed_edges": final["removed_edges"],
        "tested_removed_fraction": final["removed_fraction"],
        "final_lcc_fraction": final["lcc_fraction"],
        "lcc_fraction_drop": float(records[0]["lcc_fraction"]) - float(final["lcc_fraction"]),
        "final_num_components": final["num_components"],
        "final_efficiency_topological_retained": final["efficiency_topological_retained"],
        "final_efficiency_length_retained": final["efficiency_length_retained"],
        "resilience_auc_lcc": _normalized_auc(records, "lcc_fraction"),
        "resilience_auc_efficiency_topological": _normalized_auc(records, "efficiency_topological_retained"),
        "resilience_auc_efficiency_length": _normalized_auc(records, "efficiency_length_retained"),
    }
    return records, summary


def testar_resiliencia_interna_comunidades(
    city_id: str,
    strategy: str = "targeted",
    max_fraction: float = 0.15,
    steps: int = 10,
    min_size: int = 2,
    k_edge: int = 40,
    efficiency_samples: int = 20,
    seed: int = 42,
) -> dict:
    """Mede a robustez estrutural do subgrafo induzido de cada comunidade."""
    ensure_city_dirs(city_id)
    if strategy not in {"random", "targeted", "targeted_adaptive"}:
        raise ValueError("strategy deve ser 'random', 'targeted' ou 'targeted_adaptive'.")
    if not 0 < max_fraction <= 1:
        raise ValueError("max_fraction deve estar no intervalo (0, 1].")
    if min_size < 2:
        raise ValueError("min_size deve ser pelo menos 2.")

    graph_path = str(dataset_graph_path(city_id, "clean"))
    communities_path = f"outputs/{city_id}/metrics/nodes_communities.csv"
    print(f"[E7I] Carregando grafo: {graph_path}", flush=True)
    G = simple_undirected_min_length_graph(load_graphml(graph_path))
    node_to_comm = _read_node_communities(communities_path)

    nodes_by_community: dict[int, list[Any]] = defaultdict(list)
    for node in G.nodes():
        community_id = _node_community(node, node_to_comm)
        if community_id is not None:
            nodes_by_community[community_id].append(node)

    selected = [
        (community_id, nodes)
        for community_id, nodes in sorted(nodes_by_community.items())
        if len(nodes) >= min_size
    ]
    if not selected:
        raise RuntimeError("Nenhuma comunidade passou pelo filtro min_size.")

    print(f"[E7I] Comunidades selecionadas: {len(selected)} | min_size={min_size}", flush=True)
    all_records: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    skipped: list[tuple[int, int, str]] = []

    for index, (community_id, nodes) in enumerate(selected, start=1):
        subgraph = G.subgraph(nodes).copy()
        if subgraph.number_of_edges() == 0:
            skipped.append((community_id, len(nodes), "sem arestas internas"))
            continue
        records, summary = _simulate_community(
            community_id,
            subgraph,
            strategy,
            max_fraction,
            steps,
            k_edge,
            efficiency_samples,
            seed,
        )
        all_records.extend(records)
        summaries.append(summary)
        print(
            f"[E7I] {index}/{len(selected)} comunidade={community_id} nos={summary['nodes']} "
            f"arestas={summary['internal_edges']} LCC_final={summary['final_lcc_fraction']:.3f} "
            f"AUC_LCC={summary['resilience_auc_lcc']:.3f}",
            flush=True,
        )

    if not summaries:
        raise RuntimeError("Nenhuma comunidade com arestas internas pôde ser analisada.")

    summaries.sort(key=lambda row: (row["resilience_auc_lcc"], row["community_id"]))
    metrics_dir = Path(f"outputs/{city_id}/metrics")
    figures_dir = Path(f"outputs/{city_id}/figures")
    logs_dir = Path(f"outputs/{city_id}/logs")
    curve_csv = metrics_dir / f"intra_community_resilience_curve_{strategy}.csv"
    summary_csv = metrics_dir / f"intra_community_resilience_summary_{strategy}.csv"
    plot_path = figures_dir / f"intra_community_resilience_{strategy}.png"
    report_txt = logs_dir / f"intra_community_resilience_report_{strategy}.txt"

    with curve_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_records[0].keys()))
        writer.writeheader()
        writer.writerows(all_records)

    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    xs = [row["nodes"] for row in summaries]
    ys = [row["resilience_auc_lcc"] for row in summaries]
    plt.figure(figsize=(10, 6))
    plt.scatter(xs, ys, alpha=0.7)
    for row in summaries[: min(10, len(summaries))]:
        plt.annotate(str(row["community_id"]), (row["nodes"], row["resilience_auc_lcc"]), fontsize=8)
    plt.xlabel("Número de nós da comunidade")
    plt.ylabel("Robustez interna (AUC normalizada da LCC)")
    plt.title(f"Robustez estrutural interna das comunidades ({city_id}) — {strategy}")
    plt.grid(True, alpha=0.3)
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    with report_txt.open("w", encoding="utf-8") as f:
        f.write("=== Robustez Estrutural Interna por Comunidade (E7I) ===\n\n")
        f.write(f"Entrada grafo: {graph_path}\n")
        f.write(f"Entrada comunidades: {communities_path}\n")
        f.write(f"Estratégia: {strategy}\n")
        f.write(f"Comunidades analisadas: {len(summaries)}\n")
        f.write(f"Comunidades ignoradas: {len(skipped)}\n")
        f.write(f"min_size: {min_size}\n")
        f.write(f"max_fraction: {max_fraction}\n")
        f.write(f"steps: {steps}\n")
        f.write(f"k_edge: {k_edge}\n")
        f.write(f"efficiency_samples: {efficiency_samples}\n\n")
        f.write("Interpretação:\n")
        f.write("  - Cada comunidade é analisada separadamente como subgrafo induzido.\n")
        f.write("  - Somente arestas internas são removidas; conexões com outras comunidades não entram nesta análise.\n")
        f.write("  - resilience_auc_lcc próximo de 1 indica maior preservação da conectividade no intervalo testado.\n")
        f.write("  - Compare AUCs apenas entre execuções com os mesmos parâmetros.\n\n")
        f.write("10 comunidades mais frágeis por AUC da LCC:\n")
        for row in summaries[:10]:
            f.write(
                f"  community={row['community_id']} nodes={row['nodes']} internal_edges={row['internal_edges']} "
                f"final_lcc={row['final_lcc_fraction']} auc_lcc={row['resilience_auc_lcc']}\n"
            )
        if skipped:
            f.write("\nComunidades ignoradas:\n")
            for community_id, size, reason in skipped:
                f.write(f"  community={community_id} nodes={size} reason={reason}\n")

    return {
        "curve_csv": str(curve_csv),
        "summary_csv": str(summary_csv),
        "curve_plot": str(plot_path),
        "report_txt": str(report_txt),
        "communities_analyzed": len(summaries),
    }
