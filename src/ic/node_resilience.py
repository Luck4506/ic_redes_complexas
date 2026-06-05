from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph
from .resilience import _efficiency_retained, _largest_cc_stats


def _efficiency_on_original_nodes(
    G: nx.Graph,
    original_nodes: int,
    samples: int,
    seed: int,
    weight: str | None = None,
    sampled_original_nodes: list[Any] | None = None,
) -> float:
    """Usa fontes originais fixas e conta vértices removidos como desconectados."""
    if original_nodes < 2:
        return 0.0
    if sampled_original_nodes is None:
        nodes = list(G.nodes())
        sampled_original_nodes = nodes if len(nodes) <= samples else random.Random(seed).sample(nodes, samples)
    if not sampled_original_nodes:
        return 0.0

    total = 0.0
    for source in sampled_original_nodes:
        if not G.has_node(source):
            continue
        if weight is None:
            distances = nx.single_source_shortest_path_length(G, source)
        else:
            distances = nx.single_source_dijkstra_path_length(G, source, weight=weight)
        total += sum(1.0 / float(distance) for target, distance in distances.items() if target != source and distance > 0)
    return total / (len(sampled_original_nodes) * (original_nodes - 1))


def _static_node_order(
    G: nx.Graph,
    strategy: str,
    k_node: int,
    seed: int,
    rng: random.Random,
) -> tuple[list[Any], dict[Any, float]]:
    nodes = list(G.nodes())
    if strategy == "random":
        rng.shuffle(nodes)
        print("[E7V] Estratégia: random", flush=True)
        return nodes, {}

    k = max(1, min(k_node, G.number_of_nodes()))
    print(f"[E7V] Estratégia: targeted (node betweenness aprox estático, k={k})", flush=True)
    scores = nx.betweenness_centrality(G, k=k, normalized=True, seed=seed)
    return [node for node, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)], scores


def _adaptive_node_batch(G: nx.Graph, batch_size: int, k_node: int, seed: int) -> list[tuple[Any, float]]:
    if batch_size <= 0 or G.number_of_nodes() == 0:
        return []
    k = max(1, min(k_node, G.number_of_nodes()))
    scores = nx.betweenness_centrality(G, k=k, normalized=True, seed=seed)
    selected = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:batch_size]
    G.remove_nodes_from(node for node, _ in selected)
    return selected


def testar_resiliencia_vertices(
    city_id: str,
    strategy: str = "targeted",
    max_fraction: float = 0.15,
    steps: int = 15,
    k_node: int = 80,
    efficiency_samples: int = 20,
    seed: int = 42,
    output_suffix: str | None = None,
) -> dict:
    """Remove exclusivamente vértices e mede a degradação da rede."""
    ensure_city_dirs(city_id)
    if not 0 < max_fraction < 1:
        raise ValueError("max_fraction deve estar no intervalo (0, 1).")

    graph_path = f"data/graphs/{city_id}_drive_clean.graphml"
    print(f"[E7V] Carregando grafo: {graph_path}", flush=True)
    G_dir = load_graphml(graph_path)
    Gu = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(Gu):
        Gu = Gu.subgraph(max(nx.connected_components(Gu), key=len)).copy()
        used_cc = True
    else:
        used_cc = False

    G0 = Gu
    n0, m0 = G0.number_of_nodes(), G0.number_of_edges()
    rng = random.Random(seed)
    print(f"[E7V] Grafo base: nós={n0} arestas={m0} | maior componente? {'SIM' if used_cc else 'NÃO'}", flush=True)

    if strategy in {"random", "targeted"}:
        removal_order, initial_scores = _static_node_order(G0, strategy, k_node, seed, rng)
    elif strategy == "targeted_adaptive":
        removal_order, initial_scores = [], {}
        print(f"[E7V] Estratégia: targeted_adaptive (recalcula por ponto, k_node={k_node})", flush=True)
    else:
        raise ValueError("strategy deve ser 'random', 'targeted' ou 'targeted_adaptive'.")

    max_remove = max(1, min(n0 - 1, int(max_fraction * n0)))
    steps = max(2, steps)
    removals = sorted({int(round(i * max_remove / (steps - 1))) for i in range(steps)})

    G = G0.copy()
    removed = 0
    records: list[dict[str, float]] = []
    removed_records: list[dict[str, Any]] = []
    original_node_list = list(G0.nodes())
    efficiency_sources = (
        original_node_list
        if len(original_node_list) <= efficiency_samples
        else random.Random(seed).sample(original_node_list, efficiency_samples)
    )

    eff0 = _efficiency_on_original_nodes(G, n0, efficiency_samples, seed, sampled_original_nodes=efficiency_sources)
    eff_len0 = _efficiency_on_original_nodes(G, n0, efficiency_samples, seed, weight="length", sampled_original_nodes=efficiency_sources)

    def record_state() -> None:
        size_lcc, num_components = _largest_cc_stats(G)
        eff = _efficiency_on_original_nodes(G, n0, efficiency_samples, seed, sampled_original_nodes=efficiency_sources)
        eff_len = _efficiency_on_original_nodes(G, n0, efficiency_samples, seed, weight="length", sampled_original_nodes=efficiency_sources)
        remaining = G.number_of_nodes()
        records.append({
            "removed_nodes": removed,
            "removed_fraction": removed / n0 if n0 else 0.0,
            "remaining_nodes": remaining,
            "remaining_nodes_fraction": remaining / n0 if n0 else 0.0,
            "lcc_size": size_lcc,
            "lcc_fraction": size_lcc / n0 if n0 else 0.0,
            "lcc_remaining_fraction": size_lcc / remaining if remaining else 0.0,
            "num_components": num_components,
            "efficiency_topological_approx": eff,
            "efficiency_topological_retained": _efficiency_retained(eff, eff0),
            "efficiency_length_approx": eff_len,
            "efficiency_length_retained": _efficiency_retained(eff_len, eff_len0),
        })

    record_state()
    for step_index, target_removed in enumerate(removals[1:], start=1):
        if strategy == "targeted_adaptive":
            selected = _adaptive_node_batch(G, target_removed - removed, k_node, seed + step_index)
            for node, score in selected:
                removed_records.append(_removed_node_row(G0, node, removed + 1, step_index, score))
                removed += 1
        else:
            while removed < target_removed and removed < len(removal_order):
                node = removal_order[removed]
                removed_records.append(_removed_node_row(G0, node, removed + 1, step_index, initial_scores.get(node, "")))
                if G.has_node(node):
                    G.remove_node(node)
                removed += 1
        record_state()
        last = records[-1]
        print(
            f"[E7V] removidos={removed}/{n0} | LCC={int(last['lcc_size'])} ({last['lcc_fraction']:.3f}) "
            f"| comps={int(last['num_components'])} | eff_topo_retida≈{last['efficiency_topological_retained']:.4f}",
            flush=True,
        )

    metrics_dir = Path(f"outputs/{city_id}/metrics")
    figures_dir = Path(f"outputs/{city_id}/figures")
    logs_dir = Path(f"outputs/{city_id}/logs")
    suffix = output_suffix or strategy
    curve_csv = metrics_dir / f"node_resilience_curve_{suffix}.csv"
    removed_csv = metrics_dir / f"node_resilience_removed_{suffix}.csv"
    curve_plot = figures_dir / f"node_resilience_curve_{suffix}.png"
    report_txt = logs_dir / f"node_resilience_report_{suffix}.txt"

    _write_dict_rows(curve_csv, records)
    _write_dict_rows(removed_csv, removed_records)

    xs = [row["removed_fraction"] for row in records]
    plt.figure()
    plt.plot(xs, [row["lcc_fraction"] for row in records], marker="o", label="LCC / nós originais")
    plt.plot(xs, [row["efficiency_topological_retained"] for row in records], marker="s", label="Eficiência topológica retida")
    plt.xlabel("Fração de vértices removidos")
    plt.ylabel("Fração retida")
    plt.title(f"Resiliência por remoção de vértices ({city_id}) — {strategy}")
    plt.grid(True)
    plt.legend()
    plt.savefig(curve_plot, dpi=150, bbox_inches="tight")
    plt.close()

    with report_txt.open("w", encoding="utf-8") as f:
        f.write("=== Resiliência por Remoção de Vértices (E7V) ===\n\n")
        f.write(f"Entrada: {graph_path}\nGrafo analisado: nós={n0} arestas={m0}\n")
        f.write(f"Estratégia: {strategy}\nMax fraction removida: {max_fraction}\nSteps: {steps}\n")
        f.write(f"k_node (targeted): {k_node}\nefficiency_samples: {efficiency_samples}\n\n")
        f.write("Notas metodológicas:\n")
        f.write("  - Esta análise remove exclusivamente vértices; a análise por arestas permanece separada.\n")
        f.write("  - Grafo simples, não-direcionado e maior componente conectada.\n")
        f.write("  - targeted usa node betweenness aproximada inicial; targeted_adaptive recalcula por etapa.\n")
        f.write("  - LCC e eficiência usam os nós originais como denominador; vértices removidos contam como desconectados.\n\n")
        f.write("  - As mesmas fontes amostradas são mantidas em todos os pontos da curva para reduzir ruído.\n\n")
        f.write("Último ponto:\n")
        for key, value in records[-1].items():
            f.write(f"  {key} = {value}\n")

    print("[E7V] Pronto ✅", flush=True)
    return {
        "curve_csv": str(curve_csv),
        "removed_nodes_csv": str(removed_csv),
        "curve_plot": str(curve_plot),
        "report_txt": str(report_txt),
    }


def _removed_node_row(G0: nx.Graph, node: Any, rank: int, step: int, score: Any) -> dict[str, Any]:
    data = G0.nodes[node]
    return {
        "removal_rank": rank,
        "step": step,
        "node": node,
        "betweenness_score_at_selection": score,
        "initial_degree": G0.degree(node),
        "lat": data.get("y", ""),
        "lon": data.get("x", ""),
    }


def _write_dict_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
