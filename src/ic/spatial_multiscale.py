from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import folium
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph
from .vulnerability_index import _as_float


def _read_csv(path: str) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(path: str, rows: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _cell_size_degrees(cell_size_m: float, center_lat: float) -> tuple[float, float]:
    lat_step = cell_size_m / 111_320.0
    lon_step = cell_size_m / (111_320.0 * max(0.2, math.cos(math.radians(center_lat))))
    return lat_step, lon_step


def _cell_id(row: int, col: int) -> str:
    return f"r{row:03d}_c{col:03d}"


def _build_grid(G: nx.Graph, cell_size_m: float) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    lats = [float(data["y"]) for _, data in G.nodes(data=True)]
    lons = [float(data["x"]) for _, data in G.nodes(data=True)]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    lat_step, lon_step = _cell_size_degrees(cell_size_m, (min_lat + max_lat) / 2.0)

    cells: dict[str, dict[str, Any]] = {}
    node_to_cell: dict[str, str] = {}
    for node, data in G.nodes(data=True):
        lat = float(data["y"])
        lon = float(data["x"])
        row = int((lat - min_lat) / lat_step) if lat_step > 0 else 0
        col = int((lon - min_lon) / lon_step) if lon_step > 0 else 0
        cid = _cell_id(row, col)
        if cid not in cells:
            south = min_lat + row * lat_step
            north = south + lat_step
            west = min_lon + col * lon_step
            east = west + lon_step
            cells[cid] = {
                "cell_id": cid,
                "row": row,
                "col": col,
                "south": south,
                "north": north,
                "west": west,
                "east": east,
                "nodes": [],
            }
        cells[cid]["nodes"].append(node)
        node_to_cell[str(node)] = cid
    return cells, node_to_cell


def _load_vulnerability_by_cell(city_id: str, node_to_cell: dict[str, str]) -> dict[str, list[float]]:
    by_cell: dict[str, list[float]] = {}
    for row in _read_csv(f"outputs/{city_id}/metrics/vulnerability_nodes.csv"):
        cid = node_to_cell.get(row.get("node", ""))
        if cid:
            by_cell.setdefault(cid, []).append(_as_float(row.get("vulnerability_score")))
    return by_cell


def _load_route_redundancy_by_cell(city_id: str, node_to_cell: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    by_cell: dict[str, list[dict[str, str]]] = {}
    for row in _read_csv(f"outputs/{city_id}/metrics/route_redundancy_pairs.csv"):
        cid = node_to_cell.get(row.get("origin", ""))
        if cid:
            by_cell.setdefault(cid, []).append(row)
    return by_cell


def _cell_rows(city_id: str, G: nx.Graph, cells: dict[str, dict[str, Any]], node_to_cell: dict[str, str]) -> list[dict[str, Any]]:
    vulnerability_by_cell = _load_vulnerability_by_cell(city_id, node_to_cell)
    redundancy_by_cell = _load_route_redundancy_by_cell(city_id, node_to_cell)

    rows: list[dict[str, Any]] = []
    for cid, cell in sorted(cells.items(), key=lambda item: (item[1]["row"], item[1]["col"])):
        nodes = cell["nodes"]
        H = G.subgraph(nodes).copy()
        node_count = H.number_of_nodes()
        edge_count = H.number_of_edges()
        degrees = [degree for _, degree in H.degree()]
        lengths = [float(data.get("length", 0.0)) for _, _, data in H.edges(data=True)]
        components = list(nx.connected_components(H)) if node_count else []
        largest_component = max((len(c) for c in components), default=0)
        articulation_count = len(list(nx.articulation_points(H))) if node_count >= 3 else 0
        bridge_count = len(list(nx.bridges(H))) if edge_count else 0
        vulnerability_values = vulnerability_by_cell.get(cid, [])
        redundancy_rows = redundancy_by_cell.get(cid, [])
        redundancy_pairs = len(redundancy_rows)
        redundancy_reasonable = sum(1 for row in redundancy_rows if row.get("reasonable_alternative") == "1")
        redundancy_disconnected = sum(1 for row in redundancy_rows if row.get("alternative_exists") == "0")

        rows.append(
            {
                "cell_id": cid,
                "row": cell["row"],
                "col": cell["col"],
                "south": cell["south"],
                "north": cell["north"],
                "west": cell["west"],
                "east": cell["east"],
                "center_lat": (cell["south"] + cell["north"]) / 2.0,
                "center_lon": (cell["west"] + cell["east"]) / 2.0,
                "nodes": node_count,
                "internal_edges": edge_count,
                "total_length_m": sum(lengths),
                "degree_mean": _mean([float(value) for value in degrees]),
                "density": nx.density(H) if node_count > 1 else 0.0,
                "components": len(components),
                "largest_component_fraction": largest_component / node_count if node_count else 0.0,
                "articulation_nodes": articulation_count,
                "bridge_edges": bridge_count,
                "vulnerability_nodes": len(vulnerability_values),
                "vulnerability_mean": _mean(vulnerability_values),
                "vulnerability_max": max(vulnerability_values) if vulnerability_values else 0.0,
                "route_redundancy_pairs": redundancy_pairs,
                "route_redundancy_reasonable_rate": redundancy_reasonable / redundancy_pairs if redundancy_pairs else 0.0,
                "route_redundancy_disconnected_rate": redundancy_disconnected / redundancy_pairs if redundancy_pairs else 0.0,
            }
        )

    rows.sort(
        key=lambda row: (
            row["vulnerability_max"],
            row["articulation_nodes"] + row["bridge_edges"],
            row["route_redundancy_disconnected_rate"],
            row["nodes"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(rows, start=1):
        row["risk_rank"] = rank
    return rows


def _summary_rows(rows: list[dict[str, Any]], cell_size_m: float) -> list[dict[str, Any]]:
    populated = [row for row in rows if row["nodes"] > 0]
    sparse = [row for row in populated if row["nodes"] < 10]
    redundancy = [row for row in populated if row["route_redundancy_pairs"] > 0]
    top_vulnerability = max(populated, key=lambda row: row["vulnerability_max"], default={})
    top_connectivity = max(populated, key=lambda row: row["degree_mean"], default={})
    low_redundancy = max(redundancy, key=lambda row: row["route_redundancy_disconnected_rate"], default={})
    return [
        {"metric": "cell_size_m", "value": cell_size_m},
        {"metric": "populated_cells", "value": len(populated)},
        {"metric": "sparse_cells_lt_10_nodes", "value": len(sparse)},
        {"metric": "mean_nodes_per_cell", "value": _mean([float(row["nodes"]) for row in populated])},
        {"metric": "mean_degree_by_cell", "value": _mean([float(row["degree_mean"]) for row in populated])},
        {"metric": "mean_vulnerability_by_cell", "value": _mean([float(row["vulnerability_mean"]) for row in populated])},
        {"metric": "cells_with_route_redundancy_pairs", "value": len(redundancy)},
        {"metric": "mean_route_redundancy_reasonable_rate", "value": _mean([float(row["route_redundancy_reasonable_rate"]) for row in redundancy])},
        {"metric": "mean_route_redundancy_disconnected_rate", "value": _mean([float(row["route_redundancy_disconnected_rate"]) for row in redundancy])},
        {"metric": "top_vulnerability_cell", "value": top_vulnerability.get("cell_id", "")},
        {"metric": "top_vulnerability_value", "value": top_vulnerability.get("vulnerability_max", "")},
        {"metric": "top_connectivity_cell", "value": top_connectivity.get("cell_id", "")},
        {"metric": "top_connectivity_degree_mean", "value": top_connectivity.get("degree_mean", "")},
        {"metric": "lowest_redundancy_cell", "value": low_redundancy.get("cell_id", "")},
        {"metric": "lowest_redundancy_disconnected_rate", "value": low_redundancy.get("route_redundancy_disconnected_rate", "")},
    ]


def _color(value: float, max_value: float) -> str:
    if max_value <= 0:
        return "#d9e2ec"
    ratio = max(0.0, min(1.0, value / max_value))
    if ratio < 0.25:
        return "#fee8c8"
    if ratio < 0.50:
        return "#fdbb84"
    if ratio < 0.75:
        return "#e34a33"
    return "#b30000"


def _grid_map(path: str, rows: list[dict[str, Any]], metric: str, title: str) -> None:
    selected = [row for row in rows if row["nodes"] > 0]
    if not selected:
        return
    center = (_mean([float(row["center_lat"]) for row in selected]), _mean([float(row["center_lon"]) for row in selected]))
    max_value = max(float(row.get(metric, 0.0)) for row in selected)
    fmap = folium.Map(location=center, zoom_start=12)
    for row in selected:
        value = float(row.get(metric, 0.0))
        popup = (
            f"{title}<br>cell={row['cell_id']}<br>"
            f"nodes={row['nodes']}<br>edges={row['internal_edges']}<br>"
            f"{metric}={value:.4f}<br>"
            f"vulnerability_max={float(row['vulnerability_max']):.4f}<br>"
            f"reasonable_route_rate={float(row['route_redundancy_reasonable_rate']):.4f}"
        )
        folium.Rectangle(
            bounds=[(float(row["south"]), float(row["west"])), (float(row["north"]), float(row["east"]))],
            color="#333333",
            weight=0.5,
            fill=True,
            fill_color=_color(value, max_value),
            fill_opacity=0.45,
            popup=popup,
        ).add_to(fmap)
    fmap.save(path)


def analisar_multiescala_espacial(city_id: str, cell_size_m: float = 1000.0) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = f"data/graphs/{city_id}_drive_clean.graphml"
    G_dir = load_graphml(graph_path)
    G = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    cells, node_to_cell = _build_grid(G, cell_size_m)
    rows = _cell_rows(city_id, G, cells, node_to_cell)
    summary = _summary_rows(rows, cell_size_m)

    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    cells_csv = f"{metrics_dir}/spatial_multiscale_cells.csv"
    summary_csv = f"{metrics_dir}/spatial_multiscale_summary.csv"
    vulnerability_map = f"{maps_dir}/spatial_multiscale_vulnerability.html"
    connectivity_map = f"{maps_dir}/spatial_multiscale_connectivity.html"
    redundancy_map = f"{maps_dir}/spatial_multiscale_redundancy.html"
    report_txt = f"{logs_dir}/spatial_multiscale_report.txt"

    _write_rows(cells_csv, rows)
    _write_rows(summary_csv, summary)
    _grid_map(vulnerability_map, rows, "vulnerability_max", "Vulnerabilidade local")
    _grid_map(connectivity_map, rows, "degree_mean", "Conectividade local")
    _grid_map(redundancy_map, rows, "route_redundancy_disconnected_rate", "Baixa redundância local")

    summary_map = {row["metric"]: row["value"] for row in summary}
    Path(report_txt).write_text(
        "\n".join(
            [
                "=== Análise Multiescala por Grade Espacial ===",
                "",
                f"Dataset: {city_id}",
                f"Entrada: {graph_path}",
                f"Tamanho da célula: {cell_size_m:.1f} m",
                f"Células povoadas: {summary_map.get('populated_cells', 0)}",
                f"Célula de maior vulnerabilidade: {summary_map.get('top_vulnerability_cell', '')}",
                f"Célula de maior conectividade média: {summary_map.get('top_connectivity_cell', '')}",
                f"Célula de menor redundância observada: {summary_map.get('lowest_redundancy_cell', '')}",
                "",
                "Interpretação:",
                "  - A análise usa grade espacial regular derivada da extensão do grafo.",
                "  - Métricas locais são calculadas no subgrafo induzido pelos nós de cada célula.",
                "  - Vulnerabilidade e redundância são agregadas quando os respectivos módulos já foram executados.",
                "  - Células com poucos nós devem ser interpretadas com cautela.",
                "",
                f"CSV células: {cells_csv}",
                f"CSV resumo: {summary_csv}",
                f"Mapa vulnerabilidade: {vulnerability_map}",
                f"Mapa conectividade: {connectivity_map}",
                f"Mapa redundância: {redundancy_map}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "cells_csv": cells_csv,
        "summary_csv": summary_csv,
        "vulnerability_map": vulnerability_map,
        "connectivity_map": connectivity_map,
        "redundancy_map": redundancy_map,
        "report_txt": report_txt,
        **summary_map,
    }
