from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any

import folium
import networkx as nx

from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml
from .metric_graphs import edge_length_m


def _write_rows(path: str, rows: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _simple_directed_min_length_graph(G: nx.MultiDiGraph) -> nx.DiGraph:
    D = nx.DiGraph()
    D.add_nodes_from(G.nodes(data=True))
    for u, v, data in G.edges(data=True):
        length = edge_length_m(data)
        if D.has_edge(u, v):
            if length < D[u][v].get("length", float("inf")):
                D[u][v].update(data)
                D[u][v]["length"] = length
        else:
            attrs = dict(data)
            attrs["length"] = length
            D.add_edge(u, v, **attrs)
    return D


def _path_length(G: nx.Graph, path: list[Any]) -> float:
    return sum(float(G[u][v].get("length", 1.0)) for u, v in zip(path[:-1], path[1:]))


def _remove_path_edges(G: nx.DiGraph, path: list[Any]) -> nx.DiGraph:
    H = G.copy()
    H.remove_edges_from((u, v) for u, v in zip(path[:-1], path[1:]) if H.has_edge(u, v))
    return H


def _sample_reachable_pair(G: nx.DiGraph, rng: random.Random, max_tries: int = 100) -> tuple[Any, Any] | None:
    nodes = list(G.nodes())
    for _ in range(max_tries):
        source = rng.choice(nodes)
        lengths = nx.single_source_dijkstra_path_length(G, source, weight="length")
        reachable = [node for node in lengths if node != source]
        if reachable:
            return source, rng.choice(reachable)
    return None


def _coords(G: nx.Graph, path: list[Any]) -> list[tuple[float, float]]:
    return [(float(G.nodes[n]["y"]), float(G.nodes[n]["x"])) for n in path]


def _route_map(path: str, G: nx.Graph, rows: list[dict[str, Any]], route_cache: dict[int, dict[str, list[Any]]], limit: int) -> None:
    selected = [row for row in rows if row.get("alternative_exists") == 1][:limit]
    if not selected:
        selected = rows[:limit]
    if not selected:
        return

    first_route = route_cache[int(selected[0]["pair_id"])]["best"]
    fmap = folium.Map(location=_coords(G, first_route)[0], zoom_start=12)
    for row in selected:
        pair_id = int(row["pair_id"])
        best = route_cache[pair_id]["best"]
        alternative = route_cache[pair_id].get("alternative", [])
        popup = (
            f"pair_id={pair_id}<br>origin={row['origin']}<br>destination={row['destination']}<br>"
            f"best_m={float(row['best_distance_m']):.1f}<br>"
            f"alternative_m={float(row['alternative_distance_m']):.1f}<br>"
            f"ratio={float(row['alternative_ratio']):.3f}<br>"
            f"reasonable={row['reasonable_alternative']}"
        )
        folium.PolyLine(_coords(G, best), color="#1565c0", weight=4, opacity=0.65, popup=popup).add_to(fmap)
        if alternative:
            folium.PolyLine(_coords(G, alternative), color="#2e7d32", weight=4, opacity=0.75, popup=popup).add_to(fmap)

    fmap.save(path)


def _summarize(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    sampled = len(rows)
    with_alt = [row for row in rows if row["alternative_exists"] == 1]
    reasonable = [row for row in rows if row["reasonable_alternative"] == 1]
    ratios = [float(row["alternative_ratio"]) for row in with_alt if float(row["alternative_ratio"]) > 0]
    detours = [float(row["detour_distance_m"]) for row in with_alt]
    disconnected = sampled - len(with_alt)
    return {
        "sampled_pairs": sampled,
        "pairs_with_alternative": len(with_alt),
        "alternative_rate": len(with_alt) / sampled if sampled else 0.0,
        "reasonable_alternative_threshold": threshold,
        "reasonable_alternative_pairs": len(reasonable),
        "reasonable_alternative_rate": len(reasonable) / sampled if sampled else 0.0,
        "disconnected_after_block_pairs": disconnected,
        "disconnected_after_block_rate": disconnected / sampled if sampled else 0.0,
        "alternative_ratio_mean": sum(ratios) / len(ratios) if ratios else 0.0,
        "alternative_ratio_max": max(ratios) if ratios else 0.0,
        "detour_distance_m_mean": sum(detours) / len(detours) if detours else 0.0,
    }


def analisar_redundancia_rotas(
    city_id: str,
    pairs: int = 100,
    threshold: float = 1.50,
    seed: int = 42,
    map_limit: int = 20,
) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = str(dataset_graph_path(city_id, "clean"))
    G_raw = load_graphml(graph_path)
    G = _simple_directed_min_length_graph(G_raw)

    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    route_cache: dict[int, dict[str, list[Any]]] = {}
    attempts = 0
    max_attempts = max(500, pairs * 20)

    while len(rows) < pairs and attempts < max_attempts:
        attempts += 1
        pair = _sample_reachable_pair(G, rng)
        if pair is None:
            break
        origin, destination = pair
        try:
            best_path = nx.shortest_path(G, origin, destination, weight="length")
        except nx.NetworkXNoPath:
            continue
        if len(best_path) < 2:
            continue

        best_distance = _path_length(G, best_path)
        blocked = _remove_path_edges(G, best_path)
        alternative_path: list[Any] = []
        alternative_distance = 0.0
        alternative_exists = 0
        reasonable = 0
        ratio = 0.0

        try:
            alternative_path = nx.shortest_path(blocked, origin, destination, weight="length")
            alternative_distance = _path_length(blocked, alternative_path)
            alternative_exists = 1
            ratio = alternative_distance / best_distance if best_distance > 0 else 0.0
            reasonable = 1 if ratio <= threshold else 0
        except nx.NetworkXNoPath:
            pass

        pair_id = len(rows) + 1
        route_cache[pair_id] = {"best": best_path, "alternative": alternative_path}
        rows.append(
            {
                "pair_id": pair_id,
                "origin": str(origin),
                "destination": str(destination),
                "best_distance_m": best_distance,
                "best_hops": len(best_path) - 1,
                "blocked_edges": len(best_path) - 1,
                "alternative_exists": alternative_exists,
                "reasonable_alternative": reasonable,
                "alternative_distance_m": alternative_distance,
                "alternative_hops": len(alternative_path) - 1 if alternative_path else 0,
                "alternative_ratio": ratio,
                "detour_distance_m": max(0.0, alternative_distance - best_distance) if alternative_exists else 0.0,
                "origin_lat": G.nodes[origin].get("y", ""),
                "origin_lon": G.nodes[origin].get("x", ""),
                "destination_lat": G.nodes[destination].get("y", ""),
                "destination_lon": G.nodes[destination].get("x", ""),
            }
        )

    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    pairs_csv = f"{metrics_dir}/route_redundancy_pairs.csv"
    summary_csv = f"{metrics_dir}/route_redundancy_summary.csv"
    map_html = f"{maps_dir}/route_redundancy.html"
    report_txt = f"{logs_dir}/route_redundancy_report.txt"

    summary = _summarize(rows, threshold)
    _write_rows(pairs_csv, rows)
    _write_rows(summary_csv, [{"metric": key, "value": value} for key, value in summary.items()])
    _route_map(map_html, G, rows, route_cache, map_limit)

    Path(report_txt).write_text(
        "\n".join(
            [
                "=== Perfil de Redundância de Rotas ===",
                "",
                f"Dataset: {city_id}",
                f"Entrada: {graph_path}",
                f"Pares solicitados: {pairs}",
                f"Pares analisados: {summary['sampled_pairs']}",
                f"Limiar de alternativa razoável: {threshold:.2f}x a melhor rota",
                f"Taxa com alternativa: {summary['alternative_rate']:.4f}",
                f"Taxa com alternativa razoável: {summary['reasonable_alternative_rate']:.4f}",
                f"Taxa sem rota após bloqueio: {summary['disconnected_after_block_rate']:.4f}",
                f"Razão média alternativa/melhor: {summary['alternative_ratio_mean']:.4f}",
                "",
                "Interpretação:",
                "  - A melhor rota é calculada por distância no grafo dirigido.",
                "  - Todos os segmentos direcionados da melhor rota são bloqueados.",
                "  - Uma alternativa razoável existe quando ainda há caminho e sua distância não ultrapassa o limiar.",
                "  - A métrica é amostral; compare datasets usando os mesmos parâmetros e seed.",
                "",
                f"CSV pares: {pairs_csv}",
                f"CSV resumo: {summary_csv}",
                f"Mapa: {map_html}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "pairs_csv": pairs_csv,
        "summary_csv": summary_csv,
        "map_html": map_html,
        "report_txt": report_txt,
        **summary,
    }
