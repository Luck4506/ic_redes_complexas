from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import folium
import networkx as nx

from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph
from .vulnerability_index import (
    _as_float,
    _edge_key,
    _first_label,
    _highway_importance,
    _load_complete_edge_betweenness,
    _minmax,
)


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


def _component_sizes_after_node_removal(G: nx.Graph, node: Any) -> list[int]:
    seen = {node}
    sizes: list[int] = []
    for neighbor in G.neighbors(node):
        if neighbor in seen:
            continue
        stack = [neighbor]
        seen.add(neighbor)
        size = 0
        while stack:
            current = stack.pop()
            size += 1
            for nxt in G.neighbors(current):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def _component_sizes_after_edge_removal(G: nx.Graph, u: Any, v: Any) -> list[int]:
    seen = {u}
    stack = [u]
    size_u = 0
    while stack:
        current = stack.pop()
        size_u += 1
        for nxt in G.neighbors(current):
            if (current == u and nxt == v) or (current == v and nxt == u):
                continue
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    if size_u == G.number_of_nodes():
        return [size_u]
    return sorted([size_u, G.number_of_nodes() - size_u], reverse=True)


def _impact_from_sizes(sizes: list[int], original_nodes_after_removal: int) -> dict[str, Any]:
    largest = sizes[0] if sizes else 0
    second = sizes[1] if len(sizes) > 1 else 0
    detached = max(0, original_nodes_after_removal - largest)
    denominator = max(1, original_nodes_after_removal)
    return {
        "components_after_removal": len(sizes),
        "largest_component_after_removal": largest,
        "second_largest_component_after_removal": second,
        "detached_nodes_after_removal": detached,
        "detached_fraction_after_removal": detached / denominator,
    }


def _node_rows(city_id: str, G: nx.Graph, articulations: list[Any]) -> list[dict[str, Any]]:
    communities = {row.get("node", ""): row.get("community_id", "") for row in _read_csv(f"outputs/{city_id}/metrics/nodes_communities.csv")}
    centralities = {row.get("node", ""): row for row in _read_csv(f"outputs/{city_id}/metrics/node_centralities.csv")}
    betweenness_values = {
        str(node): _as_float(centralities.get(str(node), {}).get("betweenness"))
        for node in articulations
    }
    betweenness_norm = _minmax(betweenness_values)

    rows: list[dict[str, Any]] = []
    for node in articulations:
        impact = _impact_from_sizes(_component_sizes_after_node_removal(G, node), G.number_of_nodes() - 1)
        centrality = centralities.get(str(node), {})
        score = 0.75 * impact["detached_fraction_after_removal"] + 0.25 * betweenness_norm.get(str(node), 0.0)
        rows.append(
            {
                "rank": 0,
                "node": str(node),
                "lat": G.nodes[node].get("y", ""),
                "lon": G.nodes[node].get("x", ""),
                "bottleneck_score": score,
                **impact,
                "community_id": communities.get(str(node), ""),
                "degree": G.degree(node),
                "betweenness": centrality.get("betweenness", ""),
                "degree_centrality": centrality.get("degree_centrality", ""),
                "closeness_approx": centrality.get("closeness_approx", ""),
                "eigenvector": centrality.get("eigenvector", ""),
            }
        )

    rows.sort(key=lambda row: (row["detached_nodes_after_removal"], row["bottleneck_score"]), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def _edge_rows(city_id: str, G: nx.Graph, bridges: list[tuple[Any, Any]]) -> list[dict[str, Any]]:
    node_to_comm = {row.get("node", ""): row.get("community_id", "") for row in _read_csv(f"outputs/{city_id}/metrics/nodes_communities.csv")}
    edge_betweenness = _load_complete_edge_betweenness(city_id, G)
    edge_betweenness_norm = _minmax(edge_betweenness)

    rows: list[dict[str, Any]] = []
    for u, v in bridges:
        data = G.get_edge_data(u, v, default={})
        key = _edge_key(u, v)
        impact = _impact_from_sizes(_component_sizes_after_edge_removal(G, u, v), G.number_of_nodes())
        score = (
            0.65 * impact["detached_fraction_after_removal"]
            + 0.20 * edge_betweenness_norm.get(key, 0.0)
            + 0.15 * _highway_importance(data.get("highway"))
        )
        rows.append(
            {
                "rank": 0,
                "u": str(u),
                "v": str(v),
                "u_lat": G.nodes[u].get("y", ""),
                "u_lon": G.nodes[u].get("x", ""),
                "v_lat": G.nodes[v].get("y", ""),
                "v_lon": G.nodes[v].get("x", ""),
                "bottleneck_score": score,
                **impact,
                "edge_betweenness": edge_betweenness[key],
                "length_m": data.get("length", ""),
                "highway": data.get("highway", ""),
                "highway_label": _first_label(data.get("highway")),
                "name": data.get("name", ""),
                "osmid": data.get("osmid", ""),
                "source_community": node_to_comm.get(str(u), ""),
                "target_community": node_to_comm.get(str(v), ""),
                "community_boundary": 1 if node_to_comm.get(str(u)) != node_to_comm.get(str(v)) else 0,
            }
        )

    rows.sort(key=lambda row: (row["detached_nodes_after_removal"], row["bottleneck_score"]), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def _combined_rows(node_rows: list[dict[str, Any]], edge_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in node_rows:
        rows.append(
            {
                "rank": 0,
                "type": "articulation_node",
                "element": row["node"],
                "bottleneck_score": row["bottleneck_score"],
                "detached_nodes_after_removal": row["detached_nodes_after_removal"],
                "detached_fraction_after_removal": row["detached_fraction_after_removal"],
                "components_after_removal": row["components_after_removal"],
                "community_id": row["community_id"],
                "lat": row["lat"],
                "lon": row["lon"],
                "u": "",
                "v": "",
                "u_lat": "",
                "u_lon": "",
                "v_lat": "",
                "v_lon": "",
                "name": "",
                "highway": "",
            }
        )
    for row in edge_rows:
        rows.append(
            {
                "rank": 0,
                "type": "bridge_edge",
                "element": f"{row['u']}--{row['v']}",
                "bottleneck_score": row["bottleneck_score"],
                "detached_nodes_after_removal": row["detached_nodes_after_removal"],
                "detached_fraction_after_removal": row["detached_fraction_after_removal"],
                "components_after_removal": row["components_after_removal"],
                "community_id": f"{row['source_community']}->{row['target_community']}",
                "lat": "",
                "lon": "",
                "u": row["u"],
                "v": row["v"],
                "u_lat": row["u_lat"],
                "u_lon": row["u_lon"],
                "v_lat": row["v_lat"],
                "v_lon": row["v_lon"],
                "name": row["name"],
                "highway": row["highway"],
            }
        )
    rows.sort(key=lambda row: (row["detached_nodes_after_removal"], row["bottleneck_score"]), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def _center_from_graph(G: nx.Graph) -> tuple[float, float]:
    node = next(iter(G.nodes))
    return float(G.nodes[node].get("y", 0.0)), float(G.nodes[node].get("x", 0.0))


def _articulation_map(path: str, rows: list[dict[str, Any]], G: nx.Graph, top_k: int) -> None:
    fmap = folium.Map(location=_center_from_graph(G), zoom_start=12)
    for row in rows[:top_k]:
        score = float(row["bottleneck_score"])
        folium.CircleMarker(
            location=(float(row["lat"]), float(row["lon"])),
            radius=5 + min(16, 20 * score),
            color="#7b1fa2",
            fill=True,
            fill_opacity=0.75,
            popup=(
                f"rank={row['rank']}<br>node={row['node']}<br>"
                f"detached_nodes={row['detached_nodes_after_removal']}<br>"
                f"detached_fraction={float(row['detached_fraction_after_removal']):.4f}<br>"
                f"components_after_removal={row['components_after_removal']}<br>"
                f"community={row['community_id']}"
            ),
        ).add_to(fmap)
    fmap.save(path)


def _bridge_map(path: str, rows: list[dict[str, Any]], G: nx.Graph, top_k: int) -> None:
    fmap = folium.Map(location=_center_from_graph(G), zoom_start=12)
    for row in rows[:top_k]:
        score = float(row["bottleneck_score"])
        folium.PolyLine(
            locations=[
                (float(row["u_lat"]), float(row["u_lon"])),
                (float(row["v_lat"]), float(row["v_lon"])),
            ],
            color="#ef6c00",
            weight=3 + min(8, 12 * score),
            opacity=0.8,
            popup=(
                f"rank={row['rank']}<br>u={row['u']}<br>v={row['v']}<br>"
                f"detached_nodes={row['detached_nodes_after_removal']}<br>"
                f"detached_fraction={float(row['detached_fraction_after_removal']):.4f}<br>"
                f"components_after_removal={row['components_after_removal']}<br>"
                f"name={row['name']}<br>highway={row['highway_label']}"
            ),
        ).add_to(fmap)
    fmap.save(path)


def _combined_map(path: str, rows: list[dict[str, Any]], G: nx.Graph, top_k: int) -> None:
    fmap = folium.Map(location=_center_from_graph(G), zoom_start=12)
    for row in rows[:top_k]:
        score = float(row["bottleneck_score"])
        popup = (
            f"rank={row['rank']}<br>type={row['type']}<br>element={row['element']}<br>"
            f"detached_nodes={row['detached_nodes_after_removal']}<br>"
            f"detached_fraction={float(row['detached_fraction_after_removal']):.4f}<br>"
            f"components_after_removal={row['components_after_removal']}"
        )
        if row["type"] == "articulation_node":
            folium.CircleMarker(
                location=(float(row["lat"]), float(row["lon"])),
                radius=5 + min(16, 20 * score),
                color="#7b1fa2",
                fill=True,
                fill_opacity=0.75,
                popup=popup,
            ).add_to(fmap)
        else:
            folium.PolyLine(
                locations=[
                    (float(row["u_lat"]), float(row["u_lon"])),
                    (float(row["v_lat"]), float(row["v_lon"])),
                ],
                color="#ef6c00",
                weight=3 + min(8, 12 * score),
                opacity=0.8,
                popup=popup,
            ).add_to(fmap)
    fmap.save(path)


def analisar_gargalos_estruturais(city_id: str, top_k: int = 100) -> dict[str, Any]:
    ensure_city_dirs(city_id)
    graph_path = str(dataset_graph_path(city_id, "clean"))
    G_dir = load_graphml(graph_path)
    Gu = simple_undirected_min_length_graph(G_dir)
    if nx.is_connected(Gu):
        G = Gu
    else:
        G = Gu.subgraph(max(nx.connected_components(Gu), key=len)).copy()

    articulations = list(nx.articulation_points(G))
    bridges = list(nx.bridges(G))
    articulation_rows = _node_rows(city_id, G, articulations)
    bridge_rows = _edge_rows(city_id, G, bridges)
    bottleneck_rows = _combined_rows(articulation_rows, bridge_rows)

    metrics_dir = f"outputs/{city_id}/metrics"
    maps_dir = f"outputs/{city_id}/maps"
    logs_dir = f"outputs/{city_id}/logs"
    articulations_csv = f"{metrics_dir}/structural_articulations.csv"
    bridges_csv = f"{metrics_dir}/structural_bridges.csv"
    bottlenecks_csv = f"{metrics_dir}/structural_bottlenecks.csv"
    articulations_map = f"{maps_dir}/structural_articulations.html"
    bridges_map = f"{maps_dir}/structural_bridges.html"
    bottlenecks_map = f"{maps_dir}/structural_bottlenecks.html"
    report_txt = f"{logs_dir}/structural_bottlenecks_report.txt"

    _write_rows(articulations_csv, articulation_rows)
    _write_rows(bridges_csv, bridge_rows)
    _write_rows(bottlenecks_csv, bottleneck_rows)
    _articulation_map(articulations_map, articulation_rows, G, top_k)
    _bridge_map(bridges_map, bridge_rows, G, top_k)
    _combined_map(bottlenecks_map, bottleneck_rows, G, top_k)

    top_node = articulation_rows[0] if articulation_rows else {}
    top_edge = bridge_rows[0] if bridge_rows else {}
    Path(report_txt).write_text(
        "\n".join(
            [
                "=== Pontes, Articulações e Gargalos Estruturais ===",
                "",
                f"Dataset: {city_id}",
                f"Entrada: {graph_path}",
                f"Nós analisados: {G.number_of_nodes()}",
                f"Arestas analisadas: {G.number_of_edges()}",
                f"Nós de articulação: {len(articulation_rows)}",
                f"Pontes estruturais: {len(bridge_rows)}",
                f"Elementos no ranking combinado: {len(bottleneck_rows)}",
                "",
                "Maiores impactos observados:",
                f"  - Nó de articulação: {top_node.get('node', 'n/a')} | nós destacados={top_node.get('detached_nodes_after_removal', 'n/a')}",
                f"  - Ponte estrutural: {top_edge.get('u', 'n/a')}--{top_edge.get('v', 'n/a')} | nós destacados={top_edge.get('detached_nodes_after_removal', 'n/a')}",
                "",
                "Interpretação:",
                "  - Ponte estrutural é uma aresta cuja remoção aumenta o número de componentes.",
                "  - Nó de articulação é um vértice cuja remoção aumenta o número de componentes.",
                "  - O ranking de gargalos prioriza elementos que destacam mais nós da maior componente.",
                "",
                f"CSV articulações: {articulations_csv}",
                f"CSV pontes: {bridges_csv}",
                f"CSV gargalos: {bottlenecks_csv}",
                f"Mapa articulações: {articulations_map}",
                f"Mapa pontes: {bridges_map}",
                f"Mapa gargalos: {bottlenecks_map}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "articulations_csv": articulations_csv,
        "bridges_csv": bridges_csv,
        "bottlenecks_csv": bottlenecks_csv,
        "articulations_map": articulations_map,
        "bridges_map": bridges_map,
        "bottlenecks_map": bottlenecks_map,
        "report_txt": report_txt,
        "articulation_points": len(articulation_rows),
        "bridges": len(bridge_rows),
        "top_articulation_detached_nodes": top_node.get("detached_nodes_after_removal", 0),
        "top_bridge_detached_nodes": top_edge.get("detached_nodes_after_removal", 0),
    }
