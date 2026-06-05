from __future__ import annotations

import csv
import random
from pathlib import Path
from statistics import mean, median
from typing import Any

import folium
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .paths_accessibility import Coordenada, haversine_metros
from .route_redundancy import _path_length, _sample_reachable_pair, _simple_directed_min_length_graph


def _write_rows(path: str, rows: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _coords(G: nx.Graph, path: list[Any]) -> list[tuple[float, float]]:
    return [(float(G.nodes[n]["y"]), float(G.nodes[n]["x"])) for n in path]


def _direct_distance_m(G: nx.Graph, origin: Any, destination: Any) -> float:
    return haversine_metros(
        Coordenada(float(G.nodes[origin]["y"]), float(G.nodes[origin]["x"])),
        Coordenada(float(G.nodes[destination]["y"]), float(G.nodes[destination]["x"])),
    )


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    frac = pos - lower
    return ordered[lower] * (1.0 - frac) + ordered[upper] * frac


def _summarize(rows: list[dict[str, Any]], requested_pairs: int, attempts: int) -> list[dict[str, Any]]:
    distances = [float(row["route_distance_m"]) for row in rows]
    direct = [float(row["direct_distance_m"]) for row in rows]
    hops = [float(row["hops"]) for row in rows]
    circuity = [float(row["circuity_ratio"]) for row in rows]
    efficiency = [float(row["route_efficiency"]) for row in rows]
    speeds = [float(row["approx_speed_kmh"]) for row in rows]
    return [
        {"metric": "requested_pairs", "value": requested_pairs},
        {"metric": "sampled_pairs", "value": len(rows)},
        {"metric": "sampling_attempts", "value": attempts},
        {"metric": "route_distance_m_mean", "value": mean(distances) if distances else 0.0},
        {"metric": "route_distance_m_median", "value": median(distances) if distances else 0.0},
        {"metric": "route_distance_m_p90", "value": _percentile(distances, 0.90)},
        {"metric": "direct_distance_m_mean", "value": mean(direct) if direct else 0.0},
        {"metric": "hops_mean", "value": mean(hops) if hops else 0.0},
        {"metric": "hops_median", "value": median(hops) if hops else 0.0},
        {"metric": "circuity_ratio_mean", "value": mean(circuity) if circuity else 0.0},
        {"metric": "circuity_ratio_median", "value": median(circuity) if circuity else 0.0},
        {"metric": "circuity_ratio_p90", "value": _percentile(circuity, 0.90)},
        {"metric": "route_efficiency_mean", "value": mean(efficiency) if efficiency else 0.0},
        {"metric": "route_efficiency_median", "value": median(efficiency) if efficiency else 0.0},
        {"metric": "approx_speed_kmh_mean", "value": mean(speeds) if speeds else 0.0},
        {"metric": "accessibility_within_2km_rate", "value": sum(1 for value in distances if value <= 2_000) / len(distances) if distances else 0.0},
        {"metric": "accessibility_within_5km_rate", "value": sum(1 for value in distances if value <= 5_000) / len(distances) if distances else 0.0},
        {"metric": "accessibility_within_10km_rate", "value": sum(1 for value in distances if value <= 10_000) / len(distances) if distances else 0.0},
        {"metric": "low_detour_rate_circuity_le_1_25", "value": sum(1 for value in circuity if value <= 1.25) / len(circuity) if circuity else 0.0},
        {"metric": "high_detour_rate_circuity_gt_1_75", "value": sum(1 for value in circuity if value > 1.75) / len(circuity) if circuity else 0.0},
    ]


def _route_map(path: str, G: nx.Graph, route_cache: dict[int, list[Any]], rows: list[dict[str, Any]], limit: int) -> None:
    selected = rows[:limit]
    if not selected:
        return
    first = route_cache[int(selected[0]["pair_id"])]
    fmap = folium.Map(location=_coords(G, first)[0], zoom_start=12)
    for row in selected:
        pair_id = int(row["pair_id"])
        route = route_cache[pair_id]
        circuity = float(row["circuity_ratio"])
        color = "#2e7d32" if circuity <= 1.25 else "#f57c00" if circuity <= 1.75 else "#b71c1c"
        popup = (
            f"pair_id={pair_id}<br>"
            f"route_m={float(row['route_distance_m']):.1f}<br>"
            f"direct_m={float(row['direct_distance_m']):.1f}<br>"
            f"hops={row['hops']}<br>"
            f"circuity={circuity:.3f}<br>"
            f"efficiency={float(row['route_efficiency']):.3f}"
        )
        folium.PolyLine(_coords(G, route), color=color, weight=3, opacity=0.62, popup=popup).add_to(fmap)
    fmap.save(path)


def analisar_eficiencia_od(
    city_id: str,
    pairs: int = 1000,
    seed: int = 42,
    map_limit: int = 80,
) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = f"data/graphs/{city_id}_drive_clean.graphml"
    G_raw = load_graphml(graph_path)
    G = _simple_directed_min_length_graph(G_raw)

    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    route_cache: dict[int, list[Any]] = {}
    attempts = 0
    max_attempts = max(2_000, pairs * 20)

    while len(rows) < pairs and attempts < max_attempts:
        attempts += 1
        pair = _sample_reachable_pair(G, rng)
        if pair is None:
            break
        origin, destination = pair
        try:
            route = nx.shortest_path(G, origin, destination, weight="length")
        except nx.NetworkXNoPath:
            continue
        if len(route) < 2:
            continue

        route_distance = _path_length(G, route)
        direct_distance = _direct_distance_m(G, origin, destination)
        if route_distance <= 0 or direct_distance <= 0:
            continue

        hops = len(route) - 1
        circuity = route_distance / direct_distance
        efficiency = direct_distance / route_distance
        pair_id = len(rows) + 1
        route_cache[pair_id] = route
        rows.append(
            {
                "pair_id": pair_id,
                "origin": str(origin),
                "destination": str(destination),
                "route_distance_m": route_distance,
                "direct_distance_m": direct_distance,
                "detour_distance_m": route_distance - direct_distance,
                "circuity_ratio": circuity,
                "route_efficiency": efficiency,
                "hops": hops,
                "mean_edge_length_m": route_distance / hops if hops else 0.0,
                "approx_time_min_30kmh": (route_distance / 1000.0) / 30.0 * 60.0,
                "approx_speed_kmh": (direct_distance / route_distance) * 30.0,
                "origin_lat": G.nodes[origin].get("y", ""),
                "origin_lon": G.nodes[origin].get("x", ""),
                "destination_lat": G.nodes[destination].get("y", ""),
                "destination_lon": G.nodes[destination].get("x", ""),
            }
        )

    rows.sort(key=lambda row: (float(row["circuity_ratio"]), float(row["route_distance_m"])), reverse=True)
    summary = _summarize(rows, pairs, attempts)

    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    pairs_csv = f"{metrics_dir}/od_efficiency_pairs.csv"
    summary_csv = f"{metrics_dir}/od_efficiency_summary.csv"
    map_html = f"{maps_dir}/od_efficiency_routes.html"
    report_txt = f"{logs_dir}/od_efficiency_report.txt"

    _write_rows(pairs_csv, rows)
    _write_rows(summary_csv, summary)
    _route_map(map_html, G, route_cache, rows, map_limit)

    summary_map = {row["metric"]: row["value"] for row in summary}
    Path(report_txt).write_text(
        "\n".join(
            [
                "Eficiência de rotas em múltiplos pares OD",
                f"Dataset: {city_id}",
                f"Pares solicitados: {pairs}",
                f"Pares amostrados: {summary_map.get('sampled_pairs', 0)}",
                f"Distância média da rota: {float(summary_map.get('route_distance_m_mean', 0.0)):.2f} m",
                f"Circuity média: {float(summary_map.get('circuity_ratio_mean', 0.0)):.4f}",
                f"Eficiência média: {float(summary_map.get('route_efficiency_mean', 0.0)):.4f}",
                "",
                "Interpretação:",
                "  - Cada par origem-destino é amostrado no grafo dirigido.",
                "  - A rota é a menor distância ponderada por length.",
                "  - Circuity = distância da rota / distância direta geográfica.",
                "  - Eficiência = distância direta / distância da rota; quanto maior, menor o desvio.",
                "  - Acessibilidade por limiar mede a fração de pares alcançáveis até 2 km, 5 km e 10 km.",
                "",
                f"CSV pares: {pairs_csv}",
                f"CSV resumo: {summary_csv}",
                f"Mapa: {map_html}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "pairs_csv": pairs_csv,
        "summary_csv": summary_csv,
        "map_html": map_html,
        "report_txt": report_txt,
        "sampled_pairs": len(rows),
    }
