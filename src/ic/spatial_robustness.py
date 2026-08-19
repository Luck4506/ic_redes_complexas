from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any

import folium
import networkx as nx

from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml
from .metric_graphs import approximate_global_efficiency, simple_undirected_min_length_graph
from .resilience import _largest_cc_stats
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


def _cell_incident_edges(G: nx.Graph, nodes: list[Any]) -> set[tuple[Any, Any]]:
    node_set = set(nodes)
    edges: set[tuple[Any, Any]] = set()
    for u, v in G.edges():
        if u in node_set or v in node_set:
            edges.add((u, v))
    return edges


def _cell_internal_edges(G: nx.Graph, nodes: list[Any]) -> set[tuple[Any, Any]]:
    node_set = set(nodes)
    return {(u, v) for u, v in G.edges() if u in node_set and v in node_set}


def _edges_for_mode(G: nx.Graph, nodes: list[Any], mode: str) -> set[tuple[Any, Any]]:
    if mode == "internal":
        return _cell_internal_edges(G, nodes)
    if mode == "incident":
        return _cell_incident_edges(G, nodes)
    raise ValueError("mode deve ser 'incident' ou 'internal'.")


def _edge_payloads(G: nx.Graph, edges: set[tuple[Any, Any]]) -> list[tuple[Any, Any, dict[str, Any]]]:
    payloads = []
    for u, v in edges:
        if G.has_edge(u, v):
            payloads.append((u, v, dict(G[u][v])))
    return payloads


def _select_efficiency_cell_ids(
    rows: list[dict[str, Any]],
    limit: int,
    seed: int,
) -> set[str]:
    """Select cells independently of their observed impact on the LCC.

    Selecting the largest LCC losses first biases the reported mean efficiency
    loss upward. A seeded simple random sample provides a reproducible estimate
    for the population of tested cells; when the limit covers all cells no
    sampling is performed.
    """
    eligible = sorted(str(row["cell_id"]) for row in rows if row["removed_edges"] > 0)
    if limit <= 0:
        return set()
    if len(eligible) <= limit:
        return set(eligible)
    return set(random.Random(seed).sample(eligible, limit))


def _summary_rows(
    rows: list[dict[str, Any]],
    cell_size_m: float,
    mode: str,
    efficiency_samples: int,
    max_efficiency_cells: int,
) -> list[dict[str, Any]]:
    tested = [row for row in rows if row["removed_edges"] > 0]
    efficiency_rows = [row for row in tested if row.get("efficiency_evaluated") == 1]
    top_lcc = max(tested, key=lambda row: row["lcc_fraction_drop"], default={})
    top_eff = min(efficiency_rows, key=lambda row: row["efficiency_topological_retained"], default={})
    top_components = max(tested, key=lambda row: row["components_increase"], default={})
    return [
        {"metric": "cell_size_m", "value": cell_size_m},
        {"metric": "block_mode", "value": mode},
        {"metric": "efficiency_samples", "value": efficiency_samples},
        {"metric": "max_efficiency_cells", "value": max_efficiency_cells},
        {"metric": "efficiency_cell_selection", "value": "simple_random_without_replacement"},
        {"metric": "tested_cells", "value": len(tested)},
        {"metric": "mean_removed_edges", "value": _mean([float(row["removed_edges"]) for row in tested])},
        {"metric": "mean_lcc_fraction_drop", "value": _mean([float(row["lcc_fraction_drop"]) for row in tested])},
        {"metric": "max_lcc_fraction_drop", "value": top_lcc.get("lcc_fraction_drop", "")},
        {"metric": "top_lcc_impact_cell", "value": top_lcc.get("cell_id", "")},
        {"metric": "efficiency_evaluated_cells", "value": len(efficiency_rows)},
        {"metric": "efficiency_evaluated_fraction", "value": len(efficiency_rows) / len(tested) if tested else 0.0},
        {"metric": "mean_efficiency_topological_retained", "value": _mean([float(row["efficiency_topological_retained"]) for row in efficiency_rows])},
        {"metric": "min_efficiency_topological_retained", "value": top_eff.get("efficiency_topological_retained", "")},
        {"metric": "top_efficiency_impact_cell", "value": top_eff.get("cell_id", "")},
        {"metric": "max_components_increase", "value": top_components.get("components_increase", "")},
        {"metric": "top_fragmentation_cell", "value": top_components.get("cell_id", "")},
    ]


def _robustness_map(path: str, rows: list[dict[str, Any]], metric: str, title: str) -> None:
    selected = [row for row in rows if row["removed_edges"] > 0]
    if metric.startswith("efficiency_"):
        selected = [row for row in selected if row.get("efficiency_evaluated") == 1]
    if not selected:
        return
    center = (_mean([float(row["center_lat"]) for row in selected]), _mean([float(row["center_lon"]) for row in selected]))
    max_value = max(float(row.get(metric, 0.0)) for row in selected)
    fmap = folium.Map(location=center, zoom_start=12)
    for row in selected:
        value = float(row.get(metric, 0.0))
        retained = row.get("efficiency_topological_retained")
        retained_label = "não avaliada" if retained in (None, "") else f"{float(retained):.4f}"
        popup = (
            f"{title}<br>cell={row['cell_id']}<br>"
            f"nodes={row['nodes']}<br>removed_edges={row['removed_edges']}<br>"
            f"lcc_drop={float(row['lcc_fraction_drop']):.4f}<br>"
            f"components_increase={row['components_increase']}<br>"
            f"eff_retained={retained_label}"
        )
        folium.Rectangle(
            bounds=[(float(row["south"]), float(row["west"])), (float(row["north"]), float(row["east"]))],
            color="#222222",
            weight=0.5,
            fill=True,
            fill_color=_color(value, max_value),
            fill_opacity=0.5,
            popup=popup,
        ).add_to(fmap)
    fmap.save(path)


def simular_robustez_espacial(
    city_id: str,
    cell_size_m: float = 1000.0,
    mode: str = "incident",
    efficiency_samples: int = 10,
    max_efficiency_cells: int = 100,
    seed: int = 42,
) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = str(dataset_graph_path(city_id, "clean"))
    G_dir = load_graphml(graph_path)
    G = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    n0 = G.number_of_nodes()
    m0 = G.number_of_edges()
    lcc0, components0 = _largest_cc_stats(G)
    evaluate_efficiency = efficiency_samples > 0 and max_efficiency_cells > 0
    eff0 = approximate_global_efficiency(G, samples=efficiency_samples, seed=seed) if evaluate_efficiency else 0.0
    eff_len0 = approximate_global_efficiency(G, samples=efficiency_samples, seed=seed, weight="length") if evaluate_efficiency else 0.0

    cells, _node_to_cell = _build_grid(G, cell_size_m)
    rows: list[dict[str, Any]] = []
    H = G.copy()
    for cell in cells.values():
        edges_to_remove = _edges_for_mode(G, cell["nodes"], mode)
        edge_payloads = _edge_payloads(H, edges_to_remove)
        H.remove_edges_from(edges_to_remove)
        lcc, components = _largest_cc_stats(H)
        lcc_fraction = lcc / n0 if n0 else 0.0
        rows.append(
            {
                "cell_id": cell["cell_id"],
                "row": cell["row"],
                "col": cell["col"],
                "south": cell["south"],
                "north": cell["north"],
                "west": cell["west"],
                "east": cell["east"],
                "center_lat": (cell["south"] + cell["north"]) / 2.0,
                "center_lon": (cell["west"] + cell["east"]) / 2.0,
                "nodes": len(cell["nodes"]),
                "removed_edges": len(edges_to_remove),
                "removed_edge_fraction": len(edges_to_remove) / m0 if m0 else 0.0,
                "lcc_size_after": lcc,
                "lcc_fraction_after": lcc_fraction,
                "lcc_fraction_drop": (lcc0 / n0 if n0 else 0.0) - lcc_fraction,
                "components_after": components,
                "components_increase": components - components0,
                "efficiency_evaluated": 0,
                "efficiency_topological_retained": "",
                "efficiency_length_retained": "",
            }
        )
        H.add_edges_from(edge_payloads)

    rows.sort(
        key=lambda row: (
            row["lcc_fraction_drop"],
            row["components_increase"],
            row["removed_edges"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(rows, start=1):
        row["impact_rank"] = rank

    if evaluate_efficiency:
        cells_by_id = {cell["cell_id"]: cell for cell in cells.values()}
        H = G.copy()
        selected_cell_ids = _select_efficiency_cell_ids(rows, max_efficiency_cells, seed)
        for row in rows:
            if str(row["cell_id"]) not in selected_cell_ids:
                continue
            cell = cells_by_id[row["cell_id"]]
            edges_to_remove = _edges_for_mode(G, cell["nodes"], mode)
            edge_payloads = _edge_payloads(H, edges_to_remove)
            H.remove_edges_from(edges_to_remove)
            eff = approximate_global_efficiency(H, samples=efficiency_samples, seed=seed)
            eff_len = approximate_global_efficiency(H, samples=efficiency_samples, seed=seed, weight="length")
            row["efficiency_evaluated"] = 1
            row["efficiency_topological_retained"] = eff / eff0 if eff0 > 0 else 0.0
            row["efficiency_length_retained"] = eff_len / eff_len0 if eff_len0 > 0 else 0.0
            H.add_edges_from(edge_payloads)

    summary = _summary_rows(rows, cell_size_m, mode, efficiency_samples, max_efficiency_cells)
    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    cells_csv = f"{metrics_dir}/spatial_robustness_cells.csv"
    summary_csv = f"{metrics_dir}/spatial_robustness_summary.csv"
    lcc_map = f"{maps_dir}/spatial_robustness_lcc_drop.html"
    efficiency_map = f"{maps_dir}/spatial_robustness_efficiency_drop.html"
    fragmentation_map = f"{maps_dir}/spatial_robustness_fragmentation.html"
    report_txt = f"{logs_dir}/spatial_robustness_report.txt"

    for row in rows:
        retained = row.get("efficiency_topological_retained")
        row["efficiency_topological_drop"] = 1.0 - float(retained) if retained not in (None, "") else ""

    _write_rows(cells_csv, rows)
    _write_rows(summary_csv, summary)
    _robustness_map(lcc_map, rows, "lcc_fraction_drop", "Impacto espacial na LCC")
    _robustness_map(efficiency_map, rows, "efficiency_topological_drop", "Impacto espacial na eficiência")
    _robustness_map(fragmentation_map, rows, "components_increase", "Fragmentação espacial")

    summary_map = {row["metric"]: row["value"] for row in summary}
    Path(report_txt).write_text(
        "\n".join(
            [
                "=== Robustez Espacial: Impacto de Bloqueios por Região ===",
                "",
                f"Dataset: {city_id}",
                f"Entrada: {graph_path}",
                f"Tamanho da célula: {cell_size_m:.1f} m",
                f"Modo de bloqueio: {mode}",
                f"Amostras de eficiência: {efficiency_samples}",
                f"Máximo de células com eficiência calculada: {max_efficiency_cells}",
                "Seleção para eficiência: amostra aleatória simples, reprodutível e independente do impacto na LCC",
                f"Células testadas: {summary_map.get('tested_cells', 0)}",
                f"Maior queda de LCC: {summary_map.get('max_lcc_fraction_drop', '')}",
                f"Célula de maior impacto na LCC: {summary_map.get('top_lcc_impact_cell', '')}",
                f"Célula de maior fragmentação: {summary_map.get('top_fragmentation_cell', '')}",
                "",
                "Interpretação:",
                "  - Cada cenário remove vias associadas a uma única célula espacial.",
                "  - mode=incident remove arestas que tocam nós da célula; mode=internal remove apenas arestas totalmente internas.",
                "  - O impacto é medido no grafo inteiro, não apenas dentro da célula.",
                "  - Células com muitas arestas removidas tendem a representar bloqueios urbanos mais amplos.",
                "  - Quando a eficiência não é calculada em todas as células, a média usa uma amostra aleatória simples; valores não avaliados ficam explicitamente marcados.",
                "",
                f"CSV células: {cells_csv}",
                f"CSV resumo: {summary_csv}",
                f"Mapa LCC: {lcc_map}",
                f"Mapa eficiência: {efficiency_map}",
                f"Mapa fragmentação: {fragmentation_map}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "cells_csv": cells_csv,
        "summary_csv": summary_csv,
        "lcc_map": lcc_map,
        "efficiency_map": efficiency_map,
        "fragmentation_map": fragmentation_map,
        "report_txt": report_txt,
        **summary_map,
    }
