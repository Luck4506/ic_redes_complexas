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


def _write_rows(path: str, rows: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.cos(math.radians(lon2 - lon1))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 180.0


def _orientation_bin(angle: float, bins: int = 18) -> int:
    width = 180.0 / bins
    return min(bins - 1, int(angle / width))


def _entropy(counts: Counter[int], bins: int = 18) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    raw = 0.0
    for count in counts.values():
        p = count / total
        raw -= p * math.log(p)
    return raw / math.log(bins) if bins > 1 else 0.0


def _orientation_dominance(counts: Counter[int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    return max(counts.values()) / total


def _orthogonal_share(counts: Counter[int], bins: int = 18) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    best = 0
    quarter_turn = bins // 2
    for bin_id, count in counts.items():
        best = max(best, count + counts.get((bin_id + quarter_turn) % bins, 0))
    return best / total


def _classify_pattern(
    *,
    node_count: int,
    edge_count: int,
    degree_mean: float,
    largest_component_fraction: float,
    entropy: float,
    dominance: float,
    orthogonal_share: float,
    mean_segment_length: float,
) -> tuple[str, str]:
    if node_count < 10 or edge_count < 8:
        return "insuficiente", "Poucos elementos viários na célula para inferir padrão urbano."
    if largest_component_fraction < 0.65 or degree_mean < 2.0:
        return "fragmentada", "Baixa conectividade local ou maior componente pequena."
    if orthogonal_share >= 0.52 and entropy <= 0.78 and degree_mean >= 2.35:
        return "gradeada", "Orientações ortogonais dominantes e conectividade local relativamente alta."
    if dominance >= 0.35 and entropy <= 0.68:
        return "radial_linear", "Forte concentração em poucos eixos de orientação."
    if entropy >= 0.78 and mean_segment_length >= 75.0:
        return "organica", "Orientações dispersas e segmentos mais longos sugerem traçado irregular."
    if entropy >= 0.72:
        return "organica", "Alta diversidade angular, com baixa dominância direcional."
    return "mista", "A célula combina sinais de mais de um padrão morfológico."


def _cell_morphology_rows(G: nx.Graph, cells: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cid, cell in sorted(cells.items(), key=lambda item: (item[1]["row"], item[1]["col"])):
        nodes = cell["nodes"]
        H = G.subgraph(nodes).copy()
        node_count = H.number_of_nodes()
        edge_count = H.number_of_edges()
        degrees = [float(degree) for _, degree in H.degree()]
        lengths = [float(data.get("length", 0.0)) for _, _, data in H.edges(data=True)]
        components = list(nx.connected_components(H)) if node_count else []
        largest_component = max((len(component) for component in components), default=0)

        orientation_counts: Counter[int] = Counter()
        for u, v in H.edges():
            u_data = H.nodes[u]
            v_data = H.nodes[v]
            angle = _bearing_degrees(float(u_data["y"]), float(u_data["x"]), float(v_data["y"]), float(v_data["x"]))
            orientation_counts[_orientation_bin(angle)] += 1

        entropy = _entropy(orientation_counts)
        dominance = _orientation_dominance(orientation_counts)
        orthogonal = _orthogonal_share(orientation_counts)
        degree_mean = _mean(degrees)
        mean_segment_length = _mean(lengths)
        lcc_fraction = largest_component / node_count if node_count else 0.0
        pattern, reason = _classify_pattern(
            node_count=node_count,
            edge_count=edge_count,
            degree_mean=degree_mean,
            largest_component_fraction=lcc_fraction,
            entropy=entropy,
            dominance=dominance,
            orthogonal_share=orthogonal,
            mean_segment_length=mean_segment_length,
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
                "nodes": node_count,
                "internal_edges": edge_count,
                "total_length_m": sum(lengths),
                "mean_segment_length_m": mean_segment_length,
                "degree_mean": degree_mean,
                "density": nx.density(H) if node_count > 1 else 0.0,
                "components": len(components),
                "largest_component_fraction": lcc_fraction,
                "orientation_entropy": entropy,
                "orientation_dominance": dominance,
                "orthogonal_orientation_share": orthogonal,
                "morphology_class": pattern,
                "classification_reason": reason,
            }
        )

    rows.sort(
        key=lambda row: (
            row["morphology_class"],
            -float(row["nodes"]),
            -float(row["internal_edges"]),
        )
    )
    return rows


def _summary_rows(rows: list[dict[str, Any]], cell_size_m: float) -> list[dict[str, Any]]:
    populated = [row for row in rows if row["nodes"] > 0]
    classified = [row for row in populated if row["morphology_class"] != "insuficiente"]
    counts = Counter(row["morphology_class"] for row in classified)
    populated_counts = Counter(row["morphology_class"] for row in populated)
    total_classified = len(classified)
    dominant = counts.most_common(1)[0] if counts else ("", 0)
    return [
        {"metric": "cell_size_m", "value": cell_size_m},
        {"metric": "populated_cells", "value": len(populated)},
        {"metric": "classified_cells", "value": total_classified},
        {"metric": "dominant_morphology_class", "value": dominant[0]},
        {"metric": "dominant_morphology_fraction", "value": dominant[1] / total_classified if total_classified else 0.0},
        {"metric": "insufficient_cells", "value": populated_counts.get("insuficiente", 0)},
        {"metric": "insufficient_fraction", "value": populated_counts.get("insuficiente", 0) / len(populated) if populated else 0.0},
        {"metric": "grid_cells", "value": counts.get("gradeada", 0)},
        {"metric": "grid_fraction", "value": counts.get("gradeada", 0) / total_classified if total_classified else 0.0},
        {"metric": "radial_linear_cells", "value": counts.get("radial_linear", 0)},
        {"metric": "radial_linear_fraction", "value": counts.get("radial_linear", 0) / total_classified if total_classified else 0.0},
        {"metric": "organic_cells", "value": counts.get("organica", 0)},
        {"metric": "organic_fraction", "value": counts.get("organica", 0) / total_classified if total_classified else 0.0},
        {"metric": "fragmented_cells", "value": counts.get("fragmentada", 0)},
        {"metric": "fragmented_fraction", "value": counts.get("fragmentada", 0) / total_classified if total_classified else 0.0},
        {"metric": "mixed_cells", "value": counts.get("mista", 0)},
        {"metric": "mixed_fraction", "value": counts.get("mista", 0) / total_classified if total_classified else 0.0},
        {"metric": "mean_orientation_entropy", "value": _mean([float(row["orientation_entropy"]) for row in classified])},
        {"metric": "mean_orthogonal_orientation_share", "value": _mean([float(row["orthogonal_orientation_share"]) for row in classified])},
        {"metric": "mean_segment_length_m", "value": _mean([float(row["mean_segment_length_m"]) for row in classified])},
        {"metric": "mean_degree_by_cell", "value": _mean([float(row["degree_mean"]) for row in classified])},
    ]


def _class_color(label: str) -> str:
    return {
        "gradeada": "#2e7d32",
        "radial_linear": "#1565c0",
        "organica": "#ef6c00",
        "fragmentada": "#b71c1c",
        "mista": "#6a1b9a",
        "insuficiente": "#9e9e9e",
    }.get(label, "#9e9e9e")


def _class_map(path: str, rows: list[dict[str, Any]]) -> None:
    selected = [row for row in rows if row["nodes"] > 0]
    if not selected:
        return
    center = (_mean([float(row["center_lat"]) for row in selected]), _mean([float(row["center_lon"]) for row in selected]))
    fmap = folium.Map(location=center, zoom_start=12)
    for row in selected:
        popup = (
            f"classe={row['morphology_class']}<br>"
            f"cell={row['cell_id']}<br>"
            f"nodes={row['nodes']}<br>"
            f"edges={row['internal_edges']}<br>"
            f"entropy={float(row['orientation_entropy']):.4f}<br>"
            f"orthogonal_share={float(row['orthogonal_orientation_share']):.4f}<br>"
            f"degree_mean={float(row['degree_mean']):.4f}<br>"
            f"segment_mean_m={float(row['mean_segment_length_m']):.2f}<br>"
            f"{row['classification_reason']}"
        )
        folium.Rectangle(
            bounds=[(float(row["south"]), float(row["west"])), (float(row["north"]), float(row["east"]))],
            color="#333333",
            weight=0.5,
            fill=True,
            fill_color=_class_color(str(row["morphology_class"])),
            fill_opacity=0.48,
            popup=popup,
        ).add_to(fmap)
    fmap.save(path)


def _metric_map(path: str, rows: list[dict[str, Any]], metric: str, title: str) -> None:
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
            f"class={row['morphology_class']}<br>"
            f"{metric}={value:.4f}<br>"
            f"nodes={row['nodes']}<br>"
            f"edges={row['internal_edges']}"
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


def analisar_morfologia_urbana(city_id: str, cell_size_m: float = 1000.0) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = str(dataset_graph_path(city_id, "clean"))
    G_dir = load_graphml(graph_path)
    G = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    cells, _ = _build_grid(G, cell_size_m)
    rows = _cell_morphology_rows(G, cells)
    summary = _summary_rows(rows, cell_size_m)

    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    cells_csv = f"{metrics_dir}/urban_morphology_cells.csv"
    summary_csv = f"{metrics_dir}/urban_morphology_summary.csv"
    class_map = f"{maps_dir}/urban_morphology_classes.html"
    entropy_map = f"{maps_dir}/urban_morphology_orientation_entropy.html"
    connectivity_map = f"{maps_dir}/urban_morphology_connectivity.html"
    report_txt = f"{logs_dir}/urban_morphology_report.txt"

    _write_rows(cells_csv, rows)
    _write_rows(summary_csv, summary)
    _class_map(class_map, rows)
    _metric_map(entropy_map, rows, "orientation_entropy", "Entropia angular")
    _metric_map(connectivity_map, rows, "degree_mean", "Conectividade morfológica local")

    summary_map = {str(row["metric"]): row["value"] for row in summary}
    Path(report_txt).write_text(
        "\n".join(
            [
                "Análise de morfologia urbana",
                f"Dataset: {city_id}",
                f"Célula espacial: {cell_size_m} m",
                f"Células povoadas: {summary_map.get('populated_cells', 0)}",
                f"Células classificadas: {summary_map.get('classified_cells', 0)}",
                f"Classe dominante: {summary_map.get('dominant_morphology_class', '')}",
                "",
                "Critério: classificação heurística baseada em orientação das vias, entropia angular,",
                "conectividade local, tamanho da maior componente e comprimento médio dos segmentos.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "cells_csv": cells_csv,
        "summary_csv": summary_csv,
        "class_map": class_map,
        "entropy_map": entropy_map,
        "connectivity_map": connectivity_map,
        "report_txt": report_txt,
    }
