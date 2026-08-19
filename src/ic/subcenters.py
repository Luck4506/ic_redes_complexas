from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path
from typing import Any

import folium
import networkx as nx

from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph
from .spatial_multiscale import _build_grid, _color, _mean
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


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(value - lo) / (hi - lo) for value in values]


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


def _load_centralities(city_id: str) -> dict[str, dict[str, float]]:
    rows = _read_csv(f"outputs/{city_id}/metrics/node_centralities.csv")
    if not rows:
        raise FileNotFoundError(f"Centralidades completas não encontradas para {city_id}. Execute `ic centrality`.")
    return {
        row.get("node", ""): {
            "betweenness": _as_float(row.get("betweenness")),
            "degree_centrality": _as_float(row.get("degree_centrality")),
            "closeness_approx": _as_float(row.get("closeness_approx")),
            "eigenvector": _as_float(row.get("eigenvector")),
        }
        for row in rows
        if row.get("node")
    }


def _load_communities(city_id: str) -> dict[str, str]:
    return {
        row.get("node", ""): row.get("community_id", "")
        for row in _read_csv(f"outputs/{city_id}/metrics/nodes_communities.csv")
        if row.get("node")
    }


def _raw_cell_rows(city_id: str, G: nx.Graph, cells: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    centralities = _load_centralities(city_id)
    communities = _load_communities(city_id)
    rows: list[dict[str, Any]] = []

    for cid, cell in sorted(cells.items(), key=lambda item: (item[1]["row"], item[1]["col"])):
        nodes = cell["nodes"]
        H = G.subgraph(nodes).copy()
        centrality_values = [centralities.get(str(node), {}) for node in nodes]
        betweenness = [value.get("betweenness", 0.0) for value in centrality_values]
        degree_c = [value.get("degree_centrality", 0.0) for value in centrality_values]
        closeness = [value.get("closeness_approx", 0.0) for value in centrality_values]
        eigenvector = [value.get("eigenvector", 0.0) for value in centrality_values]
        lengths = [float(data.get("length", 0.0)) for _, _, data in H.edges(data=True)]
        community_counts = Counter(communities.get(str(node), "") for node in nodes if communities.get(str(node), ""))
        dominant_community, dominant_count = community_counts.most_common(1)[0] if community_counts else ("", 0)
        node_count = H.number_of_nodes()
        edge_count = H.number_of_edges()

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
                "density": nx.density(H) if node_count > 1 else 0.0,
                "degree_mean_local": _mean([float(degree) for _, degree in H.degree()]),
                "betweenness_sum": sum(betweenness),
                "betweenness_mean": _mean(betweenness),
                "betweenness_max": max(betweenness) if betweenness else 0.0,
                "degree_centrality_mean": _mean(degree_c),
                "closeness_mean": _mean(closeness),
                "eigenvector_mean": _mean(eigenvector),
                "communities_touched": len(community_counts),
                "dominant_community_id": dominant_community,
                "dominant_community_share": dominant_count / node_count if node_count else 0.0,
            }
        )
    return rows


def _score_rows(rows: list[dict[str, Any]], min_nodes: int, percentile: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    metrics = {
        "nodes_norm": _minmax([float(row["nodes"]) for row in rows]),
        "density_norm": _minmax([float(row["density"]) for row in rows]),
        "degree_mean_norm": _minmax([float(row["degree_mean_local"]) for row in rows]),
        "betweenness_sum_norm": _minmax([float(row["betweenness_sum"]) for row in rows]),
        "betweenness_max_norm": _minmax([float(row["betweenness_max"]) for row in rows]),
        "closeness_norm": _minmax([float(row["closeness_mean"]) for row in rows]),
        "eigenvector_norm": _minmax([float(row["eigenvector_mean"]) for row in rows]),
        "communities_norm": _minmax([float(row["communities_touched"]) for row in rows]),
    }
    weights = {
        "betweenness_sum_norm": 0.25,
        "betweenness_max_norm": 0.18,
        "closeness_norm": 0.14,
        "eigenvector_norm": 0.10,
        "density_norm": 0.12,
        "degree_mean_norm": 0.10,
        "nodes_norm": 0.07,
        "communities_norm": 0.04,
    }

    for idx, row in enumerate(rows):
        for metric, values in metrics.items():
            row[metric] = values[idx] if idx < len(values) else 0.0
        row["subcenter_score"] = sum(float(row[metric]) * weight for metric, weight in weights.items())
        row["is_subcenter"] = 0

    eligible_scores = [float(row["subcenter_score"]) for row in rows if int(row["nodes"]) >= min_nodes]
    threshold = _percentile(eligible_scores, percentile)
    subcenters = [
        row
        for row in rows
        if int(row["nodes"]) >= min_nodes and float(row["subcenter_score"]) >= threshold and float(row["subcenter_score"]) > 0
    ]
    subcenters.sort(key=lambda row: (float(row["subcenter_score"]), int(row["nodes"])), reverse=True)
    for rank, row in enumerate(subcenters, start=1):
        row["subcenter_rank"] = rank
        row["is_subcenter"] = 1

    rows.sort(key=lambda row: (float(row["subcenter_score"]), int(row["nodes"])), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["centrality_region_rank"] = rank
        row.setdefault("subcenter_rank", "")

    return rows, subcenters, threshold


def _polycentricity(subcenters: list[dict[str, Any]]) -> dict[str, float]:
    scores = [float(row["subcenter_score"]) for row in subcenters if float(row["subcenter_score"]) > 0]
    if not scores:
        return {
            "polycentricity_index": 0.0,
            "monocentricity_index": 0.0,
            "subcenter_score_entropy": 0.0,
            "top_subcenter_score_share": 0.0,
        }
    total = sum(scores)
    shares = [score / total for score in scores]
    entropy = -sum(share * math.log(share) for share in shares if share > 0)
    entropy_norm = entropy / math.log(len(shares)) if len(shares) > 1 else 0.0
    top_share = max(shares)
    return {
        "polycentricity_index": entropy_norm * (1.0 - top_share),
        "monocentricity_index": top_share,
        "subcenter_score_entropy": entropy_norm,
        "top_subcenter_score_share": top_share,
    }


def _summary_rows(
    rows: list[dict[str, Any]],
    subcenters: list[dict[str, Any]],
    cell_size_m: float,
    percentile: float,
    threshold: float,
) -> list[dict[str, Any]]:
    populated = [row for row in rows if int(row["nodes"]) > 0]
    poly = _polycentricity(subcenters)
    top = subcenters[0] if subcenters else {}
    return [
        {"metric": "cell_size_m", "value": cell_size_m},
        {"metric": "subcenter_percentile", "value": percentile},
        {"metric": "subcenter_score_threshold", "value": threshold},
        {"metric": "populated_cells", "value": len(populated)},
        {"metric": "subcenters_count", "value": len(subcenters)},
        {"metric": "subcenters_fraction", "value": len(subcenters) / len(populated) if populated else 0.0},
        {"metric": "polycentricity_index", "value": poly["polycentricity_index"]},
        {"metric": "monocentricity_index", "value": poly["monocentricity_index"]},
        {"metric": "subcenter_score_entropy", "value": poly["subcenter_score_entropy"]},
        {"metric": "top_subcenter_score_share", "value": poly["top_subcenter_score_share"]},
        {"metric": "top_subcenter_cell", "value": top.get("cell_id", "")},
        {"metric": "top_subcenter_score", "value": top.get("subcenter_score", "")},
        {"metric": "top_subcenter_nodes", "value": top.get("nodes", "")},
        {"metric": "top_subcenter_dominant_community", "value": top.get("dominant_community_id", "")},
    ]


def _subcenters_map(path: str, rows: list[dict[str, Any]], subcenters: list[dict[str, Any]]) -> None:
    selected = [row for row in rows if int(row["nodes"]) > 0]
    if not selected:
        return
    center = (_mean([float(row["center_lat"]) for row in selected]), _mean([float(row["center_lon"]) for row in selected]))
    max_score = max(float(row["subcenter_score"]) for row in selected)
    fmap = folium.Map(location=center, zoom_start=12)
    subcenter_ids = {row["cell_id"] for row in subcenters}
    for row in selected:
        score = float(row["subcenter_score"])
        is_subcenter = row["cell_id"] in subcenter_ids
        popup = (
            f"cell={row['cell_id']}<br>"
            f"rank={row['centrality_region_rank']}<br>"
            f"subcenter={int(is_subcenter)}<br>"
            f"score={score:.4f}<br>"
            f"nodes={row['nodes']}<br>"
            f"edges={row['internal_edges']}<br>"
            f"betweenness_sum={float(row['betweenness_sum']):.4f}<br>"
            f"communities={row['communities_touched']}<br>"
            f"dominant_comm={row['dominant_community_id']}"
        )
        folium.Rectangle(
            bounds=[(float(row["south"]), float(row["west"])), (float(row["north"]), float(row["east"]))],
            color="#111111" if is_subcenter else "#555555",
            weight=1.4 if is_subcenter else 0.4,
            fill=True,
            fill_color=_color(score, max_score),
            fill_opacity=0.52 if is_subcenter else 0.30,
            popup=popup,
        ).add_to(fmap)

    for row in subcenters:
        folium.CircleMarker(
            location=(float(row["center_lat"]), float(row["center_lon"])),
            radius=5 + 8 * float(row["subcenter_score"]) / max_score if max_score else 6,
            color="#0d47a1",
            fill=True,
            fill_color="#42a5f5",
            fill_opacity=0.9,
            popup=f"Subcentro #{row['subcenter_rank']}<br>cell={row['cell_id']}<br>score={float(row['subcenter_score']):.4f}",
        ).add_to(fmap)
    fmap.save(path)


def detectar_subcentros(
    city_id: str,
    cell_size_m: float = 1000.0,
    percentile: float = 0.90,
    min_nodes: int = 20,
) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = str(dataset_graph_path(city_id, "clean"))
    G_dir = load_graphml(graph_path)
    G = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    cells, _node_to_cell = _build_grid(G, cell_size_m)
    rows = _raw_cell_rows(city_id, G, cells)
    rows, subcenters, threshold = _score_rows(rows, min_nodes=min_nodes, percentile=percentile)
    summary = _summary_rows(rows, subcenters, cell_size_m, percentile, threshold)

    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    cells_csv = f"{metrics_dir}/subcenters_cells.csv"
    subcenters_csv = f"{metrics_dir}/subcenters.csv"
    summary_csv = f"{metrics_dir}/subcenters_summary.csv"
    map_html = f"{maps_dir}/subcenters.html"
    report_txt = f"{logs_dir}/subcenters_report.txt"

    _write_rows(cells_csv, rows)
    _write_rows(subcenters_csv, subcenters)
    _write_rows(summary_csv, summary)
    _subcenters_map(map_html, rows, subcenters)

    summary_map = {row["metric"]: row["value"] for row in summary}
    Path(report_txt).write_text(
        "\n".join(
            [
                "Células Candidatas de Alta Centralidade Topológica",
                f"Dataset: {city_id}",
                f"Célula espacial: {cell_size_m} m",
                f"Percentil de corte: {percentile}",
                f"Nós mínimos por célula: {min_nodes}",
                f"Candidatos selecionados: {summary_map.get('subcenters_count', 0)}",
                f"Índice exploratório de dispersão: {float(summary_map.get('polycentricity_index', 0.0)):.4f}",
                f"Índice exploratório de dominância: {float(summary_map.get('monocentricity_index', 0.0)):.4f}",
                "",
                "Interpretação:",
                "  - O score combina centralidade acumulada, centralidade máxima, densidade local, conectividade e comunidades tocadas.",
                "  - Dispersão alta indica que várias células candidatas dividem a importância topológica.",
                "  - Dominância alta indica concentração do score em uma célula candidata.",
                "  - Sem empregos, população, atividades ou fluxos, o módulo não comprova subcentros nem policentricidade urbana.",
                "",
                f"CSV células: {cells_csv}",
                f"CSV subcentros: {subcenters_csv}",
                f"CSV resumo: {summary_csv}",
                f"Mapa: {map_html}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "cells_csv": cells_csv,
        "subcenters_csv": subcenters_csv,
        "summary_csv": summary_csv,
        "map_html": map_html,
        "report_txt": report_txt,
        "subcenters_count": len(subcenters),
    }
