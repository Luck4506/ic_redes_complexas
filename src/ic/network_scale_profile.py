from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import folium
import matplotlib
import networkx as nx

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph
from .spatial_multiscale import _build_grid, _color, _mean
from .urban_barriers import _cell_rows as _barrier_cell_rows
from .urban_barriers import _connection_rows as _barrier_connection_rows
from .urban_barriers import _load_articulation_cells


def _write_rows(path: str, rows: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _coefficient_variation(values: list[float]) -> float:
    mean = abs(_mean(values))
    if mean <= 1e-12:
        return 0.0 if _std(values) <= 1e-12 else float("inf")
    return _std(values) / mean


def _stability_score(values: list[float]) -> float:
    cv = _coefficient_variation(values)
    if not math.isfinite(cv):
        return 0.0
    return 1.0 / (1.0 + cv)


def _scale_label(scale: float) -> str:
    if float(scale).is_integer():
        return str(int(scale))
    return str(scale).replace(".", "_")


def _cell_metrics_for_scale(city_id: str, G: nx.Graph, scale_m: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cells, node_to_cell = _build_grid(G, scale_m)
    connections, _by_pair, _connected = _barrier_connection_rows(city_id, G, cells, node_to_cell)
    articulation_cells = _load_articulation_cells(city_id, node_to_cell)
    barrier_rows_by_cell = {
        row["cell_id"]: row
        for row in _barrier_cell_rows(G, cells, connections, articulation_cells)
    }

    rows: list[dict[str, Any]] = []
    for cid, cell in sorted(cells.items(), key=lambda item: (item[1]["row"], item[1]["col"])):
        nodes = cell["nodes"]
        if not nodes:
            continue
        H = G.subgraph(nodes).copy()
        node_count = H.number_of_nodes()
        edge_count = H.number_of_edges()
        lengths = [float(data.get("length", 0.0)) for _, _, data in H.edges(data=True)]
        degrees = [float(degree) for _, degree in H.degree()]
        components = list(nx.connected_components(H)) if node_count else []
        largest_component = max((len(component) for component in components), default=0)
        articulation_count = len(list(nx.articulation_points(H))) if node_count >= 3 else 0
        bridge_count = len(list(nx.bridges(H))) if edge_count else 0
        barrier = barrier_rows_by_cell.get(cid, {})
        rows.append(
            {
                "scale_m": scale_m,
                "cell_id": cid,
                "scale_cell_id": f"{_scale_label(scale_m)}m_{cid}",
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
                "degree_mean": _mean(degrees),
                "density": nx.density(H) if node_count > 1 else 0.0,
                "components": len(components),
                "largest_component_fraction": largest_component / node_count if node_count else 0.0,
                "articulation_nodes": articulation_count,
                "bridge_edges": bridge_count,
                "permeability_index": float(barrier.get("permeability_index", 0.0)),
                "low_permeability_score": float(barrier.get("low_permeability_score", 0.0)),
                "missing_neighbor_connections": int(barrier.get("missing_neighbor_connections", 0)),
                "connected_neighbor_cells": int(barrier.get("connected_neighbor_cells", 0)),
                "possible_neighbor_cells": int(barrier.get("possible_neighbor_cells", 0)),
            }
        )
    return rows, connections


def _scale_summary(scale_m: float, cell_rows: list[dict[str, Any]], connection_rows: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [float(row["nodes"]) for row in cell_rows]
    degrees = [float(row["degree_mean"]) for row in cell_rows]
    densities = [float(row["density"]) for row in cell_rows]
    lcc = [float(row["largest_component_fraction"]) for row in cell_rows]
    permeability = [
        float(row["permeability_index"])
        for row in cell_rows
        if int(row["possible_neighbor_cells"]) > 0
    ]
    low_perm = [float(row["low_permeability_score"]) for row in cell_rows]
    low_perm_cells = [
        row
        for row in cell_rows
        if float(row["permeability_index"]) < 0.50 and int(row["possible_neighbor_cells"]) > 0
    ]
    missing_connections = [row for row in connection_rows if int(row.get("missing_adjacent_connection", 0))]

    return {
        "scale_m": scale_m,
        "populated_cells": len(cell_rows),
        "neighbor_connections_ranked": len(connection_rows),
        "mean_nodes_per_cell": _mean(nodes),
        "cv_nodes_per_cell": _coefficient_variation(nodes),
        "mean_degree_by_cell": _mean(degrees),
        "cv_degree_by_cell": _coefficient_variation(degrees),
        "mean_density_by_cell": _mean(densities),
        "cv_density_by_cell": _coefficient_variation(densities),
        "mean_largest_component_fraction": _mean(lcc),
        "mean_articulation_nodes": _mean([float(row["articulation_nodes"]) for row in cell_rows]),
        "mean_bridge_edges": _mean([float(row["bridge_edges"]) for row in cell_rows]),
        "mean_spatial_permeability": _mean(permeability),
        "low_permeability_cells": len(low_perm_cells),
        "low_permeability_fraction": len(low_perm_cells) / len(cell_rows) if cell_rows else 0.0,
        "missing_adjacent_connections": len(missing_connections),
        "mean_low_permeability_score": _mean(low_perm),
        "top_low_permeability_cell": cell_rows[0].get("cell_id", "") if cell_rows else "",
        "top_low_permeability_score": max(low_perm) if low_perm else 0.0,
    }


def _stability_rows(scale_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = [
        ("mean_nodes_per_cell", "Nós médios por célula"),
        ("mean_degree_by_cell", "Grau médio local"),
        ("mean_density_by_cell", "Densidade média local"),
        ("mean_largest_component_fraction", "Maior componente local média"),
        ("mean_spatial_permeability", "Permeabilidade espacial média"),
        ("low_permeability_fraction", "Fração de células pouco permeáveis"),
        ("mean_low_permeability_score", "Score médio de baixa permeabilidade"),
    ]
    rows: list[dict[str, Any]] = []
    for metric, label in metrics:
        values = [float(row[metric]) for row in scale_rows]
        rows.append(
            {
                "metric": metric,
                "label": label,
                "mean_across_scales": _mean(values),
                "std_across_scales": _std(values),
                "coefficient_variation": _coefficient_variation(values),
                "min_value": min(values) if values else 0.0,
                "max_value": max(values) if values else 0.0,
                "stability_score": _stability_score(values),
            }
        )
    rows.sort(key=lambda row: float(row["stability_score"]))
    return rows


def _summary_rows(scale_rows: list[dict[str, Any]], stability_rows: list[dict[str, Any]], scales: list[float]) -> list[dict[str, Any]]:
    core_metrics = {
        "mean_degree_by_cell",
        "mean_density_by_cell",
        "mean_largest_component_fraction",
        "mean_spatial_permeability",
        "low_permeability_fraction",
        "mean_low_permeability_score",
    }
    core_scores = [float(row["stability_score"]) for row in stability_rows if row["metric"] in core_metrics]
    least_stable = stability_rows[0] if stability_rows else {}
    most_stable = max(stability_rows, key=lambda row: float(row["stability_score"]), default={})
    return [
        {"metric": "tested_scales_m", "value": ";".join(str(int(scale)) if float(scale).is_integer() else str(scale) for scale in scales)},
        {"metric": "tested_scales_count", "value": len(scales)},
        {"metric": "multiscale_robustness_index", "value": _mean(core_scores)},
        {"metric": "least_stable_metric", "value": least_stable.get("metric", "")},
        {"metric": "least_stable_score", "value": least_stable.get("stability_score", "")},
        {"metric": "least_stable_cv", "value": least_stable.get("coefficient_variation", "")},
        {"metric": "most_stable_metric", "value": most_stable.get("metric", "")},
        {"metric": "most_stable_score", "value": most_stable.get("stability_score", "")},
        {"metric": "min_scale_m", "value": min(scales) if scales else ""},
        {"metric": "max_scale_m", "value": max(scales) if scales else ""},
        {"metric": "populated_cells_min_scale", "value": scale_rows[0].get("populated_cells", "") if scale_rows else ""},
        {"metric": "populated_cells_max_scale", "value": scale_rows[-1].get("populated_cells", "") if scale_rows else ""},
    ]


def _plot_metrics(path: str, scale_rows: list[dict[str, Any]]) -> None:
    if not scale_rows:
        return
    xs = [float(row["scale_m"]) for row in scale_rows]
    metrics = [
        ("mean_degree_by_cell", "Grau médio"),
        ("mean_largest_component_fraction", "LCC local"),
        ("mean_spatial_permeability", "Permeabilidade"),
        ("low_permeability_fraction", "Baixa permeabilidade"),
    ]
    fig, ax = plt.subplots(figsize=(9, 5))
    for metric, label in metrics:
        ax.plot(xs, [float(row[metric]) for row in scale_rows], marker="o", label=label)
    ax.set_xlabel("Escala da célula (m)")
    ax.set_ylabel("Valor agregado")
    ax.set_title("Perfil de escala da rede viária")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _plot_stability(path: str, stability_rows: list[dict[str, Any]]) -> None:
    if not stability_rows:
        return
    rows = sorted(stability_rows, key=lambda row: float(row["stability_score"]))
    labels = [str(row["label"]) for row in rows]
    values = [float(row["stability_score"]) for row in rows]
    fig, ax = plt.subplots(figsize=(10, max(4, len(rows) * 0.55)))
    ax.barh(labels, values, color="#1769aa")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Score de estabilidade multiescalar")
    ax.set_title("Estabilidade das métricas entre escalas")
    ax.grid(True, axis="x", alpha=0.3)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _scale_map(path: str, rows: list[dict[str, Any]]) -> None:
    selected = [row for row in rows if int(row["nodes"]) > 0]
    if not selected:
        return
    center = (_mean([float(row["center_lat"]) for row in selected]), _mean([float(row["center_lon"]) for row in selected]))
    max_value = max(float(row["low_permeability_score"]) for row in selected)
    fmap = folium.Map(location=center, zoom_start=12)
    for scale in sorted({float(row["scale_m"]) for row in selected}):
        group = folium.FeatureGroup(name=f"{int(scale)} m" if scale.is_integer() else f"{scale} m", show=scale == 1000.0)
        for row in [item for item in selected if float(item["scale_m"]) == scale]:
            value = float(row["low_permeability_score"])
            popup = (
                f"scale={row['scale_m']} m<br>"
                f"cell={row['cell_id']}<br>"
                f"nodes={row['nodes']}<br>"
                f"degree_mean={float(row['degree_mean']):.4f}<br>"
                f"permeability={float(row['permeability_index']):.4f}<br>"
                f"low_permeability_score={value:.4f}<br>"
                f"missing_neighbors={row['missing_neighbor_connections']}"
            )
            folium.Rectangle(
                bounds=[(float(row["south"]), float(row["west"])), (float(row["north"]), float(row["east"]))],
                color="#333333",
                weight=0.4,
                fill=True,
                fill_color=_color(value, max_value),
                fill_opacity=0.35,
                popup=popup,
            ).add_to(group)
        group.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)
    fmap.save(path)


def analisar_perfil_escala_rede(
    city_id: str,
    scales_m: list[float] | None = None,
) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    scales = sorted({float(scale) for scale in (scales_m or [500.0, 1000.0, 2000.0, 3000.0]) if float(scale) > 0})
    if not scales:
        raise ValueError("Informe ao menos uma escala positiva.")

    graph_path = str(dataset_graph_path(city_id, "clean"))
    G_dir = load_graphml(graph_path)
    G = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    all_cell_rows: list[dict[str, Any]] = []
    scale_rows: list[dict[str, Any]] = []
    for scale in scales:
        cell_rows, connection_rows = _cell_metrics_for_scale(city_id, G, scale)
        cell_rows.sort(
            key=lambda row: (
                float(row["low_permeability_score"]),
                int(row["missing_neighbor_connections"]),
                int(row["nodes"]),
            ),
            reverse=True,
        )
        for rank, row in enumerate(cell_rows, start=1):
            row["scale_low_permeability_rank"] = rank
        all_cell_rows.extend(cell_rows)
        scale_rows.append(_scale_summary(scale, cell_rows, connection_rows))

    scale_rows.sort(key=lambda row: float(row["scale_m"]))
    stability = _stability_rows(scale_rows)
    summary = _summary_rows(scale_rows, stability, scales)

    metrics_dir = f"outputs/{city_id}/metrics"
    figures_dir = f"outputs/{city_id}/figures"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    scales_csv = f"{metrics_dir}/network_scale_profile_scales.csv"
    cells_csv = f"{metrics_dir}/network_scale_profile_cells.csv"
    stability_csv = f"{metrics_dir}/network_scale_profile_stability.csv"
    summary_csv = f"{metrics_dir}/network_scale_profile_summary.csv"
    metrics_plot = f"{figures_dir}/network_scale_profile_metrics.png"
    stability_plot = f"{figures_dir}/network_scale_profile_stability.png"
    scale_map = f"{maps_dir}/network_scale_profile_low_permeability.html"
    report_txt = f"{logs_dir}/network_scale_profile_report.txt"

    _write_rows(scales_csv, scale_rows)
    _write_rows(cells_csv, all_cell_rows)
    _write_rows(stability_csv, stability)
    _write_rows(summary_csv, summary)
    _plot_metrics(metrics_plot, scale_rows)
    _plot_stability(stability_plot, stability)
    _scale_map(scale_map, all_cell_rows)

    summary_map = {row["metric"]: row["value"] for row in summary}
    Path(report_txt).write_text(
        "\n".join(
            [
                "Perfil de Escala da Rede Viária",
                f"Dataset: {city_id}",
                f"Escalas testadas: {summary_map.get('tested_scales_m', '')} m",
                f"Índice de robustez multiescalar: {float(summary_map.get('multiscale_robustness_index', 0.0)):.4f}",
                f"Métrica menos estável: {summary_map.get('least_stable_metric', '')}",
                f"Métrica mais estável: {summary_map.get('most_stable_metric', '')}",
                "",
                "Interpretação:",
                "  - Métricas estáveis em várias escalas são mais defensáveis metodologicamente.",
                "  - Métricas instáveis indicam sensibilidade à escolha da grade e devem ser interpretadas com cautela.",
                "  - O índice de robustez multiescalar resume a estabilidade média das principais métricas locais.",
                "",
                f"CSV por escala: {scales_csv}",
                f"CSV células: {cells_csv}",
                f"CSV estabilidade: {stability_csv}",
                f"CSV resumo: {summary_csv}",
                f"Gráfico métricas: {metrics_plot}",
                f"Gráfico estabilidade: {stability_plot}",
                f"Mapa: {scale_map}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "scales_csv": scales_csv,
        "cells_csv": cells_csv,
        "stability_csv": stability_csv,
        "summary_csv": summary_csv,
        "metrics_plot": metrics_plot,
        "stability_plot": stability_plot,
        "scale_map": scale_map,
        "report_txt": report_txt,
        **summary_map,
    }
