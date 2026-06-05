from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import folium
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import approximate_global_efficiency, simple_undirected_min_length_graph
from .resilience import _largest_cc_stats
from .vulnerability_index import _as_float, _edge_key, _first_label


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


ROAD_CLASS_ORDER = {
    "motorway": 1,
    "trunk": 2,
    "primary": 3,
    "secondary": 4,
    "tertiary": 5,
    "residential": 6,
    "living_street": 7,
    "service": 8,
    "unclassified": 9,
    "other": 10,
    "unknown": 11,
}


def _road_class(value: Any) -> str:
    label = _first_label(value).lower()
    if not label:
        return "unknown"
    if label.endswith("_link"):
        label = label.removesuffix("_link")
    return label if label in ROAD_CLASS_ORDER else "other"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _edge_lookup(rows: list[dict[str, str]], value_field: str) -> dict[tuple[str, str], float]:
    return {
        _edge_key(row.get("u", ""), row.get("v", "")): _as_float(row.get(value_field))
        for row in rows
    }


def _class_color(road_class: str) -> str:
    return {
        "motorway": "#7b1fa2",
        "trunk": "#8e24aa",
        "primary": "#d32f2f",
        "secondary": "#f57c00",
        "tertiary": "#fbc02d",
        "residential": "#388e3c",
        "living_street": "#43a047",
        "service": "#1976d2",
        "unclassified": "#607d8b",
        "other": "#795548",
        "unknown": "#9e9e9e",
    }.get(road_class, "#9e9e9e")


def _build_rows(city_id: str, G: nx.Graph, efficiency_samples: int, seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    n0 = G.number_of_nodes()
    m0 = G.number_of_edges()
    total_length = sum(float(data.get("length", 0.0)) for _, _, data in G.edges(data=True))
    lcc0, components0 = _largest_cc_stats(G)
    eff0 = approximate_global_efficiency(G, samples=efficiency_samples, seed=seed) if efficiency_samples > 0 else 0.0
    eff_len0 = (
        approximate_global_efficiency(G, samples=efficiency_samples, seed=seed, weight="length")
        if efficiency_samples > 0
        else 0.0
    )

    centrality_lookup = _edge_lookup(_read_csv(f"outputs/{city_id}/metrics/top_edges.csv"), "edge_betweenness")
    vulnerability_lookup = _edge_lookup(_read_csv(f"outputs/{city_id}/metrics/vulnerability_edges.csv"), "vulnerability_score")
    bridges = {_edge_key(row.get("u", ""), row.get("v", "")) for row in _read_csv(f"outputs/{city_id}/metrics/structural_bridges.csv")}

    grouped: dict[str, dict[str, Any]] = {}
    edge_classes: dict[tuple[Any, Any], str] = {}
    for u, v, data in G.edges(data=True):
        road_class = _road_class(data.get("highway"))
        edge_classes[(u, v)] = road_class
        key = _edge_key(u, v)
        group = grouped.setdefault(
            road_class,
            {
                "road_class": road_class,
                "edge_count": 0,
                "length_m": 0.0,
                "nodes_touched": set(),
                "edge_betweenness_values": [],
                "vulnerability_values": [],
                "bridge_edges": 0,
            },
        )
        group["edge_count"] += 1
        group["length_m"] += float(data.get("length", 0.0))
        group["nodes_touched"].update([u, v])
        if key in centrality_lookup:
            group["edge_betweenness_values"].append(centrality_lookup[key])
        if key in vulnerability_lookup:
            group["vulnerability_values"].append(vulnerability_lookup[key])
        if key in bridges:
            group["bridge_edges"] += 1

    rows: list[dict[str, Any]] = []
    for road_class, group in grouped.items():
        edges_to_remove = [edge for edge, cls in edge_classes.items() if cls == road_class]
        H = G.copy()
        H.remove_edges_from(edges_to_remove)
        lcc, components = _largest_cc_stats(H)
        eff = approximate_global_efficiency(H, samples=efficiency_samples, seed=seed) if efficiency_samples > 0 else 0.0
        eff_len = (
            approximate_global_efficiency(H, samples=efficiency_samples, seed=seed, weight="length")
            if efficiency_samples > 0
            else 0.0
        )
        edge_count = int(group["edge_count"])
        length_m = float(group["length_m"])
        row = {
            "road_class": road_class,
            "hierarchy_rank": ROAD_CLASS_ORDER.get(road_class, 99),
            "edge_count": edge_count,
            "edge_fraction": edge_count / m0 if m0 else 0.0,
            "length_m": length_m,
            "length_km": length_m / 1000.0,
            "length_fraction": length_m / total_length if total_length else 0.0,
            "nodes_touched": len(group["nodes_touched"]),
            "nodes_touched_fraction": len(group["nodes_touched"]) / n0 if n0 else 0.0,
            "bridge_edges": group["bridge_edges"],
            "bridge_fraction_within_class": group["bridge_edges"] / edge_count if edge_count else 0.0,
            "top_edge_betweenness_count": len(group["edge_betweenness_values"]),
            "edge_betweenness_mean_observed": _mean(group["edge_betweenness_values"]),
            "edge_betweenness_max_observed": max(group["edge_betweenness_values"]) if group["edge_betweenness_values"] else 0.0,
            "vulnerability_mean": _mean(group["vulnerability_values"]),
            "vulnerability_max": max(group["vulnerability_values"]) if group["vulnerability_values"] else 0.0,
            "removal_lcc_fraction_after": lcc / n0 if n0 else 0.0,
            "removal_lcc_fraction_drop": (lcc0 / n0 if n0 else 0.0) - (lcc / n0 if n0 else 0.0),
            "removal_components_after": components,
            "removal_components_increase": components - components0,
            "removal_efficiency_topological_retained": eff / eff0 if eff0 > 0 else 0.0,
            "removal_efficiency_length_retained": eff_len / eff_len0 if eff_len0 > 0 else 0.0,
        }
        rows.append(row)

    rows.sort(key=lambda row: (row["hierarchy_rank"], row["road_class"]))
    return rows, {
        "nodes": n0,
        "edges": m0,
        "total_length_m": total_length,
        "initial_lcc_fraction": lcc0 / n0 if n0 else 0.0,
        "initial_components": components0,
    }


def _summary_rows(rows: list[dict[str, Any]], base: dict[str, Any], efficiency_samples: int) -> list[dict[str, Any]]:
    arterial_classes = {"motorway", "trunk", "primary", "secondary"}
    arterial = [row for row in rows if row["road_class"] in arterial_classes]
    local = [row for row in rows if row["road_class"] in {"residential", "living_street", "service"}]
    top_lcc = max(rows, key=lambda row: row["removal_lcc_fraction_drop"], default={})
    top_eff = min(rows, key=lambda row: row["removal_efficiency_topological_retained"], default={})
    top_centrality = max(rows, key=lambda row: row["edge_betweenness_max_observed"], default={})
    return [
        {"metric": "road_classes", "value": len(rows)},
        {"metric": "efficiency_samples", "value": efficiency_samples},
        {"metric": "arterial_edge_fraction", "value": sum(float(row["edge_fraction"]) for row in arterial)},
        {"metric": "arterial_length_fraction", "value": sum(float(row["length_fraction"]) for row in arterial)},
        {"metric": "local_edge_fraction", "value": sum(float(row["edge_fraction"]) for row in local)},
        {"metric": "local_length_fraction", "value": sum(float(row["length_fraction"]) for row in local)},
        {"metric": "top_lcc_dependency_class", "value": top_lcc.get("road_class", "")},
        {"metric": "top_lcc_dependency_drop", "value": top_lcc.get("removal_lcc_fraction_drop", "")},
        {"metric": "top_efficiency_dependency_class", "value": top_eff.get("road_class", "")},
        {"metric": "top_efficiency_retained", "value": top_eff.get("removal_efficiency_topological_retained", "")},
        {"metric": "top_centrality_class", "value": top_centrality.get("road_class", "")},
        {"metric": "top_centrality_value", "value": top_centrality.get("edge_betweenness_max_observed", "")},
        {"metric": "total_edges", "value": base["edges"]},
        {"metric": "total_length_km", "value": float(base["total_length_m"]) / 1000.0},
    ]


def _impact_map(path: str, G: nx.Graph, rows: list[dict[str, Any]], max_edges_per_class: int) -> None:
    selected_classes = {row["road_class"] for row in sorted(rows, key=lambda row: row["removal_lcc_fraction_drop"], reverse=True)[:5]}
    if not selected_classes:
        return
    first_node = next(iter(G.nodes))
    fmap = folium.Map(location=(float(G.nodes[first_node]["y"]), float(G.nodes[first_node]["x"])), zoom_start=12)
    counts: dict[str, int] = {road_class: 0 for road_class in selected_classes}
    row_by_class = {row["road_class"]: row for row in rows}
    for u, v, data in G.edges(data=True):
        road_class = _road_class(data.get("highway"))
        if road_class not in selected_classes or counts[road_class] >= max_edges_per_class:
            continue
        counts[road_class] += 1
        row = row_by_class[road_class]
        popup = (
            f"class={road_class}<br>"
            f"lcc_drop={float(row['removal_lcc_fraction_drop']):.4f}<br>"
            f"edge_fraction={float(row['edge_fraction']):.4f}<br>"
            f"length_fraction={float(row['length_fraction']):.4f}<br>"
            f"highway={data.get('highway', '')}"
        )
        folium.PolyLine(
            locations=[(float(G.nodes[u]["y"]), float(G.nodes[u]["x"])), (float(G.nodes[v]["y"]), float(G.nodes[v]["x"]))],
            color=_class_color(road_class),
            weight=3,
            opacity=0.7,
            popup=popup,
        ).add_to(fmap)
    fmap.save(path)


def analisar_hierarquia_viaria(
    city_id: str,
    efficiency_samples: int = 20,
    seed: int = 42,
    map_edges_per_class: int = 1200,
) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = f"data/graphs/{city_id}_drive_clean.graphml"
    G_dir = load_graphml(graph_path)
    G = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    rows, base = _build_rows(city_id, G, efficiency_samples, seed)
    summary = _summary_rows(rows, base, efficiency_samples)

    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    by_class_csv = f"{metrics_dir}/road_hierarchy_by_class.csv"
    summary_csv = f"{metrics_dir}/road_hierarchy_summary.csv"
    map_html = f"{maps_dir}/road_hierarchy_impact.html"
    report_txt = f"{logs_dir}/road_hierarchy_report.txt"

    _write_rows(by_class_csv, rows)
    _write_rows(summary_csv, summary)
    _impact_map(map_html, G, rows, map_edges_per_class)

    summary_map = {row["metric"]: row["value"] for row in summary}
    Path(report_txt).write_text(
        "\n".join(
            [
                "=== Análise de Hierarquia Viária ===",
                "",
                f"Dataset: {city_id}",
                f"Entrada: {graph_path}",
                f"Classes encontradas: {summary_map.get('road_classes', 0)}",
                f"Fração de arestas arteriais: {summary_map.get('arterial_edge_fraction', 0)}",
                f"Fração de extensão arterial: {summary_map.get('arterial_length_fraction', 0)}",
                f"Classe de maior dependência LCC: {summary_map.get('top_lcc_dependency_class', '')}",
                f"Classe de maior centralidade observada: {summary_map.get('top_centrality_class', '')}",
                "",
                "Interpretação:",
                "  - Classes *_link são agregadas à classe principal, por exemplo primary_link -> primary.",
                "  - O impacto de remoção mede a dependência global do grafo em cada classe viária.",
                "  - Edge betweenness é observado a partir do ranking top_edges.csv, portanto é um indicador de concentração nos trechos mais críticos.",
                "  - Compare cidades usando o mesmo pipeline e os mesmos parâmetros.",
                "",
                f"CSV por classe: {by_class_csv}",
                f"CSV resumo: {summary_csv}",
                f"Mapa: {map_html}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "by_class_csv": by_class_csv,
        "summary_csv": summary_csv,
        "map_html": map_html,
        "report_txt": report_txt,
        **summary_map,
    }
