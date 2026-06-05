from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import folium
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph
from .spatial_multiscale import _build_grid, _color, _mean
from .vulnerability_index import _as_float, _edge_key


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


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    q = max(0.0, min(1.0, q))
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    frac = pos - lower
    return ordered[lower] * (1 - frac) + ordered[upper] * frac


def _minmax_dict(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    lo = min(values.values())
    hi = max(values.values())
    if hi == lo:
        return {key: 0.0 for key in values}
    return {key: (value - lo) / (hi - lo) for key, value in values.items()}


def _cell_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def _is_cardinal_neighbor(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return abs(int(a["row"]) - int(b["row"])) + abs(int(a["col"]) - int(b["col"])) == 1


def _possible_neighbor_pairs(cells: dict[str, dict[str, Any]]) -> set[tuple[str, str]]:
    populated = {cid: cell for cid, cell in cells.items() if cell.get("nodes")}
    pairs: set[tuple[str, str]] = set()
    by_position = {(int(cell["row"]), int(cell["col"])): cid for cid, cell in populated.items()}
    for cid, cell in populated.items():
        row = int(cell["row"])
        col = int(cell["col"])
        for neighbor_pos in ((row + 1, col), (row - 1, col), (row, col + 1), (row, col - 1)):
            other = by_position.get(neighbor_pos)
            if other:
                pairs.add(_cell_pair(cid, other))
    return pairs


def _load_bridge_edges(city_id: str) -> set[str]:
    bridges: set[str] = set()
    for row in _read_csv(f"outputs/{city_id}/metrics/structural_bridges.csv"):
        u = row.get("u", "")
        v = row.get("v", "")
        if u and v:
            bridges.add(_edge_key(u, v))
    return bridges


def _load_articulation_cells(city_id: str, node_to_cell: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in _read_csv(f"outputs/{city_id}/metrics/structural_articulations.csv"):
        cid = node_to_cell.get(row.get("node", ""))
        if cid:
            counts[cid] = counts.get(cid, 0) + 1
    return counts


def _load_communities(city_id: str) -> dict[str, str]:
    return {
        row.get("node", ""): row.get("community_id", "")
        for row in _read_csv(f"outputs/{city_id}/metrics/nodes_communities.csv")
        if row.get("node")
    }


def _connection_rows(
    city_id: str,
    G: nx.Graph,
    cells: dict[str, dict[str, Any]],
    node_to_cell: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], set[str]]:
    bridge_edges = _load_bridge_edges(city_id)
    communities = _load_communities(city_id)
    possible_pairs = _possible_neighbor_pairs(cells)
    long_threshold = _percentile([float(data.get("length", 0.0)) for _, _, data in G.edges(data=True)], 0.95)
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}

    for u, v, data in G.edges(data=True):
        cu = node_to_cell.get(str(u))
        cv = node_to_cell.get(str(v))
        if not cu or not cv or cu == cv:
            continue
        pair = _cell_pair(cu, cv)
        length = float(data.get("length", 0.0))
        key = _edge_key(u, v)
        comm_u = communities.get(str(u), "")
        comm_v = communities.get(str(v), "")
        row = by_pair.setdefault(
            pair,
            {
                "cell_a": pair[0],
                "cell_b": pair[1],
                "row_a": cells[pair[0]]["row"],
                "col_a": cells[pair[0]]["col"],
                "row_b": cells[pair[1]]["row"],
                "col_b": cells[pair[1]]["col"],
                "center_lat_a": (cells[pair[0]]["south"] + cells[pair[0]]["north"]) / 2.0,
                "center_lon_a": (cells[pair[0]]["west"] + cells[pair[0]]["east"]) / 2.0,
                "center_lat_b": (cells[pair[1]]["south"] + cells[pair[1]]["north"]) / 2.0,
                "center_lon_b": (cells[pair[1]]["west"] + cells[pair[1]]["east"]) / 2.0,
                "is_cardinal_neighbor": int(_is_cardinal_neighbor(cells[pair[0]], cells[pair[1]])),
                "crossing_edges": 0,
                "crossing_length_m": 0.0,
                "max_crossing_length_m": 0.0,
                "long_crossing_edges": 0,
                "structural_bridge_edges": 0,
                "community_boundary_edges": 0,
            },
        )
        row["crossing_edges"] += 1
        row["crossing_length_m"] += length
        row["max_crossing_length_m"] = max(float(row["max_crossing_length_m"]), length)
        row["long_crossing_edges"] += int(length >= long_threshold and long_threshold > 0)
        row["structural_bridge_edges"] += int(key in bridge_edges)
        row["community_boundary_edges"] += int(bool(comm_u and comm_v and comm_u != comm_v))

    for pair in possible_pairs:
        by_pair.setdefault(
            pair,
            {
                "cell_a": pair[0],
                "cell_b": pair[1],
                "row_a": cells[pair[0]]["row"],
                "col_a": cells[pair[0]]["col"],
                "row_b": cells[pair[1]]["row"],
                "col_b": cells[pair[1]]["col"],
                "center_lat_a": (cells[pair[0]]["south"] + cells[pair[0]]["north"]) / 2.0,
                "center_lon_a": (cells[pair[0]]["west"] + cells[pair[0]]["east"]) / 2.0,
                "center_lat_b": (cells[pair[1]]["south"] + cells[pair[1]]["north"]) / 2.0,
                "center_lon_b": (cells[pair[1]]["west"] + cells[pair[1]]["east"]) / 2.0,
                "is_cardinal_neighbor": 1,
                "crossing_edges": 0,
                "crossing_length_m": 0.0,
                "max_crossing_length_m": 0.0,
                "long_crossing_edges": 0,
                "structural_bridge_edges": 0,
                "community_boundary_edges": 0,
            },
        )

    crossing_norm = _minmax_dict({f"{a}|{b}": float(row["crossing_edges"]) for (a, b), row in by_pair.items()})
    length_norm = _minmax_dict({f"{a}|{b}": float(row["max_crossing_length_m"]) for (a, b), row in by_pair.items()})
    rows: list[dict[str, Any]] = []
    for pair, row in by_pair.items():
        key = f"{pair[0]}|{pair[1]}"
        crossing_edges = int(row["crossing_edges"])
        community_share = int(row["community_boundary_edges"]) / crossing_edges if crossing_edges else 0.0
        bridge_share = int(row["structural_bridge_edges"]) / crossing_edges if crossing_edges else 0.0
        weak_connection = 1.0 - crossing_norm.get(key, 0.0) if crossing_edges else 1.0
        long_crossing = length_norm.get(key, 0.0)
        missing_adjacent = int(row["is_cardinal_neighbor"]) and crossing_edges == 0
        barrier_score = (
            0.45 * weak_connection
            + 0.20 * long_crossing
            + 0.20 * bridge_share
            + 0.10 * community_share
            + 0.05 * int(missing_adjacent)
        )
        row["mean_crossing_length_m"] = float(row["crossing_length_m"]) / crossing_edges if crossing_edges else 0.0
        row["community_boundary_share"] = community_share
        row["structural_bridge_share"] = bridge_share
        row["missing_adjacent_connection"] = int(missing_adjacent)
        row["barrier_score"] = barrier_score
        rows.append(row)

    rows.sort(
        key=lambda row: (
            float(row["barrier_score"]),
            int(row["missing_adjacent_connection"]),
            int(row["structural_bridge_edges"]),
            float(row["max_crossing_length_m"]),
        ),
        reverse=True,
    )
    for rank, row in enumerate(rows, start=1):
        row["barrier_connection_rank"] = rank
    connected_pairs = {row["cell_a"] + "|" + row["cell_b"] for row in rows if int(row["crossing_edges"]) > 0}
    return rows, by_pair, connected_pairs


def _cell_rows(
    G: nx.Graph,
    cells: dict[str, dict[str, Any]],
    connection_rows: list[dict[str, Any]],
    articulation_cells: dict[str, int],
) -> list[dict[str, Any]]:
    possible_by_cell: dict[str, int] = {cid: 0 for cid in cells}
    connected_by_cell: dict[str, int] = {cid: 0 for cid in cells}
    crossing_edges_by_cell: dict[str, int] = {cid: 0 for cid in cells}
    bridge_edges_by_cell: dict[str, int] = {cid: 0 for cid in cells}
    long_edges_by_cell: dict[str, int] = {cid: 0 for cid in cells}
    barrier_score_by_cell: dict[str, list[float]] = {cid: [] for cid in cells}

    for row in connection_rows:
        a = row["cell_a"]
        b = row["cell_b"]
        if int(row["is_cardinal_neighbor"]):
            possible_by_cell[a] += 1
            possible_by_cell[b] += 1
        if int(row["crossing_edges"]) > 0:
            connected_by_cell[a] += int(row["is_cardinal_neighbor"])
            connected_by_cell[b] += int(row["is_cardinal_neighbor"])
            crossing_edges_by_cell[a] += int(row["crossing_edges"])
            crossing_edges_by_cell[b] += int(row["crossing_edges"])
            bridge_edges_by_cell[a] += int(row["structural_bridge_edges"])
            bridge_edges_by_cell[b] += int(row["structural_bridge_edges"])
            long_edges_by_cell[a] += int(row["long_crossing_edges"])
            long_edges_by_cell[b] += int(row["long_crossing_edges"])
        barrier_score_by_cell[a].append(float(row["barrier_score"]))
        barrier_score_by_cell[b].append(float(row["barrier_score"]))

    bottleneck_norm = _minmax_dict({cid: float(articulation_cells.get(cid, 0) + bridge_edges_by_cell.get(cid, 0)) for cid in cells})
    long_norm = _minmax_dict({cid: float(long_edges_by_cell.get(cid, 0)) for cid in cells})
    missing_norm = _minmax_dict({
        cid: float(max(0, possible_by_cell.get(cid, 0) - connected_by_cell.get(cid, 0)))
        for cid in cells
    })

    rows: list[dict[str, Any]] = []
    for cid, cell in sorted(cells.items(), key=lambda item: (item[1]["row"], item[1]["col"])):
        nodes = cell["nodes"]
        if not nodes:
            continue
        H = G.subgraph(nodes).copy()
        possible = possible_by_cell.get(cid, 0)
        connected = connected_by_cell.get(cid, 0)
        permeability = connected / possible if possible else 0.0
        low_permeability_score = (
            0.55 * (1.0 - permeability)
            + 0.20 * missing_norm.get(cid, 0.0)
            + 0.15 * bottleneck_norm.get(cid, 0.0)
            + 0.10 * long_norm.get(cid, 0.0)
        )
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
                "nodes": H.number_of_nodes(),
                "internal_edges": H.number_of_edges(),
                "possible_neighbor_cells": possible,
                "connected_neighbor_cells": connected,
                "missing_neighbor_connections": max(0, possible - connected),
                "permeability_index": permeability,
                "crossing_edges_incident": crossing_edges_by_cell.get(cid, 0),
                "structural_bridge_edges_incident": bridge_edges_by_cell.get(cid, 0),
                "articulation_nodes": articulation_cells.get(cid, 0),
                "long_crossing_edges_incident": long_edges_by_cell.get(cid, 0),
                "mean_neighbor_barrier_score": _mean(barrier_score_by_cell.get(cid, [])),
                "low_permeability_score": low_permeability_score,
                "degree_mean": _mean([float(degree) for _, degree in H.degree()]),
                "density": nx.density(H) if H.number_of_nodes() > 1 else 0.0,
            }
        )

    rows.sort(
        key=lambda row: (
            float(row["low_permeability_score"]),
            int(row["missing_neighbor_connections"]),
            int(row["structural_bridge_edges_incident"]),
            int(row["nodes"]),
        ),
        reverse=True,
    )
    for rank, row in enumerate(rows, start=1):
        row["low_permeability_rank"] = rank
    return rows


def _summary_rows(cell_rows: list[dict[str, Any]], connection_rows: list[dict[str, Any]], cell_size_m: float) -> list[dict[str, Any]]:
    low_cells = [row for row in cell_rows if float(row["permeability_index"]) < 0.50 and int(row["possible_neighbor_cells"]) > 0]
    missing_connections = [row for row in connection_rows if int(row["missing_adjacent_connection"])]
    critical_connections = [row for row in connection_rows if int(row["structural_bridge_edges"]) > 0]
    top_cell = cell_rows[0] if cell_rows else {}
    top_connection = connection_rows[0] if connection_rows else {}
    permeability = _mean([float(row["permeability_index"]) for row in cell_rows if int(row["possible_neighbor_cells"]) > 0])
    exposure = (
        0.45 * (1.0 - permeability)
        + 0.25 * (len(low_cells) / len(cell_rows) if cell_rows else 0.0)
        + 0.20 * (len(missing_connections) / len(connection_rows) if connection_rows else 0.0)
        + 0.10 * (len(critical_connections) / len(connection_rows) if connection_rows else 0.0)
    )
    return [
        {"metric": "cell_size_m", "value": cell_size_m},
        {"metric": "populated_cells", "value": len(cell_rows)},
        {"metric": "neighbor_connections_ranked", "value": len(connection_rows)},
        {"metric": "spatial_permeability_index", "value": permeability},
        {"metric": "barrier_exposure_index", "value": exposure},
        {"metric": "low_permeability_cells_lt_0_50", "value": len(low_cells)},
        {"metric": "missing_adjacent_connections", "value": len(missing_connections)},
        {"metric": "critical_structural_connections", "value": len(critical_connections)},
        {"metric": "top_low_permeability_cell", "value": top_cell.get("cell_id", "")},
        {"metric": "top_low_permeability_score", "value": top_cell.get("low_permeability_score", "")},
        {"metric": "top_barrier_connection", "value": f"{top_connection.get('cell_a', '')}|{top_connection.get('cell_b', '')}"},
        {"metric": "top_barrier_score", "value": top_connection.get("barrier_score", "")},
        {"metric": "top_barrier_crossing_edges", "value": top_connection.get("crossing_edges", "")},
    ]


def _cell_map(path: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    center = (_mean([float(row["center_lat"]) for row in rows]), _mean([float(row["center_lon"]) for row in rows]))
    max_value = max(float(row["low_permeability_score"]) for row in rows)
    fmap = folium.Map(location=center, zoom_start=12)
    for row in rows:
        value = float(row["low_permeability_score"])
        popup = (
            f"cell={row['cell_id']}<br>"
            f"rank={row['low_permeability_rank']}<br>"
            f"permeability={float(row['permeability_index']):.4f}<br>"
            f"low_permeability_score={value:.4f}<br>"
            f"nodes={row['nodes']}<br>"
            f"missing_neighbors={row['missing_neighbor_connections']}<br>"
            f"structural_bridges={row['structural_bridge_edges_incident']}<br>"
            f"articulations={row['articulation_nodes']}"
        )
        folium.Rectangle(
            bounds=[(float(row["south"]), float(row["west"])), (float(row["north"]), float(row["east"]))],
            color="#222222",
            weight=0.5,
            fill=True,
            fill_color=_color(value, max_value),
            fill_opacity=0.45,
            popup=popup,
        ).add_to(fmap)
    fmap.save(path)


def _connection_map(path: str, rows: list[dict[str, Any]], limit: int) -> None:
    selected = rows[:limit]
    if not selected:
        return
    center = (
        _mean([float(row["center_lat_a"]) for row in selected] + [float(row["center_lat_b"]) for row in selected]),
        _mean([float(row["center_lon_a"]) for row in selected] + [float(row["center_lon_b"]) for row in selected]),
    )
    max_value = max(float(row["barrier_score"]) for row in selected)
    fmap = folium.Map(location=center, zoom_start=12)
    for row in selected:
        score = float(row["barrier_score"])
        popup = (
            f"rank={row['barrier_connection_rank']}<br>"
            f"{row['cell_a']} -> {row['cell_b']}<br>"
            f"barrier_score={score:.4f}<br>"
            f"crossing_edges={row['crossing_edges']}<br>"
            f"missing_adjacent={row['missing_adjacent_connection']}<br>"
            f"structural_bridge_share={float(row['structural_bridge_share']):.4f}<br>"
            f"community_boundary_share={float(row['community_boundary_share']):.4f}<br>"
            f"max_crossing_length_m={float(row['max_crossing_length_m']):.1f}"
        )
        folium.PolyLine(
            locations=[
                (float(row["center_lat_a"]), float(row["center_lon_a"])),
                (float(row["center_lat_b"]), float(row["center_lon_b"])),
            ],
            color="#b30000" if int(row["missing_adjacent_connection"]) else "#ef6c00",
            weight=2 + min(8, 10 * score / max_value) if max_value else 3,
            opacity=0.75,
            dash_array="8,6" if int(row["missing_adjacent_connection"]) else None,
            popup=popup,
        ).add_to(fmap)
    fmap.save(path)


def analisar_barreiras_urbanas(
    city_id: str,
    cell_size_m: float = 1000.0,
    map_limit: int = 250,
) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = f"data/graphs/{city_id}_drive_clean.graphml"
    G_dir = load_graphml(graph_path)
    G = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    cells, node_to_cell = _build_grid(G, cell_size_m)
    connections, _by_pair, _connected = _connection_rows(city_id, G, cells, node_to_cell)
    articulation_cells = _load_articulation_cells(city_id, node_to_cell)
    cell_rows = _cell_rows(G, cells, connections, articulation_cells)
    summary = _summary_rows(cell_rows, connections, cell_size_m)

    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    cells_csv = f"{metrics_dir}/urban_barriers_cells.csv"
    connections_csv = f"{metrics_dir}/urban_barriers_connections.csv"
    summary_csv = f"{metrics_dir}/urban_barriers_summary.csv"
    permeability_map = f"{maps_dir}/urban_barriers_permeability.html"
    connections_map = f"{maps_dir}/urban_barriers_connections.html"
    report_txt = f"{logs_dir}/urban_barriers_report.txt"

    _write_rows(cells_csv, cell_rows)
    _write_rows(connections_csv, connections)
    _write_rows(summary_csv, summary)
    _cell_map(permeability_map, cell_rows)
    _connection_map(connections_map, connections, map_limit)

    summary_map = {row["metric"]: row["value"] for row in summary}
    Path(report_txt).write_text(
        "\n".join(
            [
                "Exposição da Rede a Barreiras Urbanas",
                f"Dataset: {city_id}",
                f"Célula espacial: {cell_size_m} m",
                f"Índice de permeabilidade espacial: {float(summary_map.get('spatial_permeability_index', 0.0)):.4f}",
                f"Índice de exposição a barreiras: {float(summary_map.get('barrier_exposure_index', 0.0)):.4f}",
                f"Células com baixa permeabilidade: {summary_map.get('low_permeability_cells_lt_0_50', 0)}",
                f"Conexões adjacentes ausentes: {summary_map.get('missing_adjacent_connections', 0)}",
                f"Conexões críticas estruturais: {summary_map.get('critical_structural_connections', 0)}",
                "",
                "Interpretação:",
                "  - A análise infere barreiras a partir da rede viária: poucas conexões entre células, travessias longas, pontes estruturais e fronteiras de comunidade.",
                "  - Não afirma a existência física de rio, ferrovia ou rodovia sem uma camada externa; indica regiões onde a própria topologia sugere baixa permeabilidade.",
                "  - O mapa de conexões destaca pares de regiões com travessia fraca ou ausente.",
                "",
                f"CSV células: {cells_csv}",
                f"CSV conexões: {connections_csv}",
                f"CSV resumo: {summary_csv}",
                f"Mapa permeabilidade: {permeability_map}",
                f"Mapa conexões: {connections_map}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "cells_csv": cells_csv,
        "connections_csv": connections_csv,
        "summary_csv": summary_csv,
        "permeability_map": permeability_map,
        "connections_map": connections_map,
        "report_txt": report_txt,
        **summary_map,
    }
