from __future__ import annotations

import csv
import random
import statistics
import time
from pathlib import Path
from typing import Any

import networkx as nx

from .centrality import approximate_closeness_centrality
from .functional_relations import spearman_correlation
from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph


def _connected_sample(G: nx.Graph, size: int, seed: int) -> nx.Graph:
    rng = random.Random(seed)
    start = rng.choice(list(G.nodes()))
    nodes = []
    seen = {start}
    queue = [start]
    while queue and len(nodes) < size:
        node = queue.pop(0)
        nodes.append(node)
        neighbors = list(G.neighbors(node))
        rng.shuffle(neighbors)
        for neighbor in neighbors:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return G.subgraph(nodes).copy()


def _top_overlap(exact: dict[Any, float], approx: dict[Any, float], top_k: int) -> float:
    exact_top = {node for node, _ in sorted(exact.items(), key=lambda item: item[1], reverse=True)[:top_k]}
    approx_top = {node for node, _ in sorted(approx.items(), key=lambda item: item[1], reverse=True)[:top_k]}
    return len(exact_top & approx_top) / len(exact_top) if exact_top else 0.0


def _relative_error(approx: float, exact: float) -> float:
    return abs(approx - exact) / abs(exact) if exact else 0.0


def validar_aproximacoes(
    city_id: str,
    subgraph_size: int = 400,
    sample_sizes: list[int] | None = None,
    repeats: int = 3,
    seed: int = 42,
) -> dict:
    """Compara aproximações com valores exatos em subgrafo conectado controlado."""
    ensure_city_dirs(city_id)
    sample_sizes = sample_sizes or [10, 30, 60, 120]
    G = simple_undirected_min_length_graph(load_graphml(f"data/graphs/{city_id}_drive_clean.graphml"))
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    H = _connected_sample(G, min(subgraph_size, G.number_of_nodes()), seed)
    n = H.number_of_nodes()
    top_k = min(20, n)

    started = time.perf_counter()
    exact_betweenness = nx.betweenness_centrality(H, normalized=True)
    exact_closeness = nx.closeness_centrality(H)
    exact_clustering = nx.average_clustering(H)
    exact_path = nx.average_shortest_path_length(H)
    exact_diameter = nx.diameter(H)
    exact_seconds = time.perf_counter() - started

    rows = []
    nodes = list(H.nodes())
    for sample_size in sample_sizes:
        effective = min(max(1, sample_size), n)
        for repeat in range(repeats):
            run_seed = seed + repeat
            started = time.perf_counter()
            approx_betweenness = nx.betweenness_centrality(H, k=effective, normalized=True, seed=run_seed)
            approx_closeness = approximate_closeness_centrality(H, samples=effective, seed=run_seed)
            trials = min(max(1, effective), n)
            approx_clustering = nx.approximation.average_clustering(H, trials=trials, seed=run_seed)
            sampled_nodes = random.Random(run_seed).sample(nodes, effective)
            distances = []
            eccentricities = []
            for node in sampled_nodes:
                values = list(nx.single_source_shortest_path_length(H, node).values())
                distances.extend(value for value in values if value > 0)
                eccentricities.append(max(values))
            approx_path = statistics.mean(distances)
            approx_diameter = max(eccentricities)
            seconds = time.perf_counter() - started

            for metric, approx, exact in [
                ("avg_clustering", approx_clustering, exact_clustering),
                ("avg_shortest_path", approx_path, exact_path),
                ("diameter", approx_diameter, exact_diameter),
            ]:
                rows.append({
                    "metric": metric,
                    "sample_size": effective,
                    "repeat": repeat,
                    "exact_value": exact,
                    "approx_value": approx,
                    "relative_error": _relative_error(approx, exact),
                    "rank_spearman": "",
                    "top20_overlap": "",
                    "runtime_seconds": seconds,
                })
            for metric, approx, exact in [
                ("betweenness", approx_betweenness, exact_betweenness),
                ("closeness", approx_closeness, exact_closeness),
            ]:
                rows.append({
                    "metric": metric,
                    "sample_size": effective,
                    "repeat": repeat,
                    "exact_value": "",
                    "approx_value": "",
                    "relative_error": "",
                    "rank_spearman": spearman_correlation(
                        [exact[node] for node in nodes],
                        [approx[node] for node in nodes],
                    ),
                    "top20_overlap": _top_overlap(exact, approx, top_k),
                    "runtime_seconds": seconds,
                })

    metrics_dir = Path(f"outputs/{city_id}/metrics")
    logs_dir = Path(f"outputs/{city_id}/logs")
    csv_path = metrics_dir / "approximation_validation.csv"
    report_path = logs_dir / "approximation_validation_report.txt"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with report_path.open("w", encoding="utf-8") as f:
        f.write("=== Validação das Aproximações ===\n\n")
        f.write(f"Dataset: {city_id}\nSubgrafo conectado: {n} nós / {H.number_of_edges()} arestas\n")
        f.write(f"Tempo dos cálculos exatos: {exact_seconds:.4f}s\n")
        f.write(f"Amostras avaliadas: {sample_sizes}; repetições: {repeats}; semente base: {seed}\n\n")
        f.write("Interpretação: erros menores, Spearman próximo de 1 e maior sobreposição de top-20 indicam maior estabilidade.\n")
        f.write("A validação é feita em subgrafo controlado; não prova erro idêntico no grafo completo.\n")
    return {"validation_csv": str(csv_path), "report_txt": str(report_path)}
