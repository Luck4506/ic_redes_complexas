from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any

import folium
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph


def _edge_label(value: Any) -> str:
    if value in (None, "", "nan"):
        return ""
    return str(value)


def calcular_centralidades(
    city_id: str,
    top_k: int = 30,
    k_betweenness: int = 120,
    k_edge_betweenness: int = 60,
    k_closeness: int = 120,
    seed: int = 42,
) -> dict:
    ensure_city_dirs(city_id)

    grafo_path = f"data/graphs/{city_id}_drive_clean.graphml"

    print(f"[E5] Carregando grafo de {city_id}...", flush=True)
    G_dir = load_graphml(grafo_path)

    print("[E5] Convertendo para undirected + maior componente...", flush=True)
    Gu = simple_undirected_min_length_graph(G_dir)

    if nx.is_connected(Gu):
        G = Gu
    else:
        largest_cc = max(nx.connected_components(Gu), key=len)
        G = Gu.subgraph(largest_cc).copy()

    n = G.number_of_nodes()
    m = G.number_of_edges()
    print(f"[E5] Grafo pronto: nós={n}, arestas={m}", flush=True)

    print("[E5] 1/5 degree_centrality...", flush=True)
    degree_c = nx.degree_centrality(G)

    k_b = min(k_betweenness, n)
    print(f"[E5] 2/5 betweenness (aprox, k={k_b})...", flush=True)
    betw = nx.betweenness_centrality(G, k=k_b, normalized=True, seed=seed)

    k_e = min(k_edge_betweenness, n)
    print(f"[E5] 3/5 edge_betweenness (aprox, k={k_e})...", flush=True)
    edge_b = nx.edge_betweenness_centrality(G, k=k_e, normalized=True, seed=seed)

    k_c = min(max(1, k_closeness), n)
    print(f"[E5] 4/5 closeness (aprox, landmarks={k_c})...", flush=True)
    closeness = approximate_closeness_centrality(G, samples=k_c, seed=seed)

    print("[E5] 5/5 eigenvector centrality (espectral)...", flush=True)
    eigenvector = nx.eigenvector_centrality_numpy(G)

    top_nodes = sorted(betw.items(), key=lambda x: x[1], reverse=True)[:top_k]
    top_edges = sorted(edge_b.items(), key=lambda x: x[1], reverse=True)[:top_k]
    top_closeness = sorted(closeness.items(), key=lambda x: x[1], reverse=True)[:top_k]
    top_eigenvector = sorted(eigenvector.items(), key=lambda x: x[1], reverse=True)[:top_k]

    pasta_metrics = f"outputs/{city_id}/metrics"
    pasta_maps = f"outputs/{city_id}/maps"
    pasta_logs = f"outputs/{city_id}/logs"
    Path(pasta_metrics).mkdir(parents=True, exist_ok=True)
    Path(pasta_maps).mkdir(parents=True, exist_ok=True)
    Path(pasta_logs).mkdir(parents=True, exist_ok=True)

    nodes_csv = f"{pasta_metrics}/top_nodes.csv"
    with open(nodes_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "lat", "lon", "degree_centrality", "betweenness", "closeness_approx", "eigenvector"])
        for node, _score in top_nodes:
            lat = float(G_dir.nodes[node]["y"])
            lon = float(G_dir.nodes[node]["x"])
            w.writerow([
                node,
                lat,
                lon,
                degree_c.get(node, 0.0),
                betw.get(node, 0.0),
                closeness.get(node, 0.0),
                eigenvector.get(node, 0.0),
            ])

    all_nodes_csv = f"{pasta_metrics}/node_centralities.csv"
    with open(all_nodes_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "lat", "lon", "degree_centrality", "betweenness", "closeness_approx", "eigenvector"])
        for node in G.nodes():
            w.writerow([
                node,
                float(G_dir.nodes[node]["y"]),
                float(G_dir.nodes[node]["x"]),
                degree_c.get(node, 0.0),
                betw.get(node, 0.0),
                closeness.get(node, 0.0),
                eigenvector.get(node, 0.0),
            ])

    rankings_csv = f"{pasta_metrics}/centrality_rankings.csv"
    with open(rankings_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "rank", "node", "lat", "lon", "value"])
        rankings = {
            "degree_centrality": sorted(degree_c.items(), key=lambda x: x[1], reverse=True)[:top_k],
            "betweenness": top_nodes,
            "closeness_approx": top_closeness,
            "eigenvector": top_eigenvector,
        }
        for metric, ranking in rankings.items():
            for rank, (node, value) in enumerate(ranking, start=1):
                w.writerow([metric, rank, node, G_dir.nodes[node]["y"], G_dir.nodes[node]["x"], value])

    edges_csv = f"{pasta_metrics}/top_edges.csv"
    with open(edges_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "rank",
            "u",
            "v",
            "u_lat",
            "u_lon",
            "v_lat",
            "v_lon",
            "edge_betweenness",
            "length_m",
            "name",
            "highway",
            "osmid",
        ])
        for rank, ((u, v), score) in enumerate(top_edges, start=1):
            data = G.get_edge_data(u, v, default={})
            w.writerow([
                rank,
                u,
                v,
                G_dir.nodes[u]["y"],
                G_dir.nodes[u]["x"],
                G_dir.nodes[v]["y"],
                G_dir.nodes[v]["x"],
                score,
                data.get("length", ""),
                _edge_label(data.get("name")),
                _edge_label(data.get("highway")),
                _edge_label(data.get("osmid")),
            ])

    report_txt = f"{pasta_logs}/centrality_report.txt"
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("=== Centralidades (E5) ===\n\n")
        f.write(f"Entrada: {grafo_path}\n")
        f.write(f"Nós: {n} | Arestas: {m}\n")
        f.write(f"Betweenness aprox: k={k_b}, seed={seed}\n")
        f.write(f"Edge betweenness aprox: k={k_e}, seed={seed}\n\n")
        f.write(f"Closeness aprox: landmarks={k_c}, seed={seed}\n")
        f.write("Eigenvector: método espectral sobre grafo simples não direcionado.\n\n")
        f.write("Top 10 nós por betweenness:\n")
        for node, score in top_nodes[:10]:
            f.write(f"  node={node}  betweenness={score:.6f}\n")
        f.write("\nTop 10 nós por closeness aproximada:\n")
        for node, score in top_closeness[:10]:
            f.write(f"  node={node}  closeness_approx={score:.6f}\n")
        f.write("\nTop 10 nós por eigenvector:\n")
        for node, score in top_eigenvector[:10]:
            f.write(f"  node={node}  eigenvector={score:.6f}\n")

    best_node = top_nodes[0][0] if top_nodes else list(G_dir.nodes())[0]
    center_lat = float(G_dir.nodes[best_node]["y"])
    center_lon = float(G_dir.nodes[best_node]["x"])
    mapa = folium.Map(location=(center_lat, center_lon), zoom_start=13)

    for node, score in top_nodes:
        lat = float(G_dir.nodes[node]["y"])
        lon = float(G_dir.nodes[node]["x"])
        radius = 4 + 60 * float(score)
        folium.CircleMarker(
            location=(lat, lon),
            radius=radius,
            popup=f"node={node}<br>betweenness={score:.6f}",
            fill=True,
            fill_opacity=0.7,
        ).add_to(mapa)

    map_html = f"{pasta_maps}/pontos_criticos.html"
    mapa.save(map_html)

    edge_map = folium.Map(location=(center_lat, center_lon), zoom_start=13)
    for rank, ((u, v), score) in enumerate(top_edges, start=1):
        data = G.get_edge_data(u, v, default={})
        u_lat = float(G_dir.nodes[u]["y"])
        u_lon = float(G_dir.nodes[u]["x"])
        v_lat = float(G_dir.nodes[v]["y"])
        v_lon = float(G_dir.nodes[v]["x"])
        weight = 2 + min(10, 80 * float(score))
        popup = (
            f"rank={rank}<br>"
            f"u={u}<br>v={v}<br>"
            f"edge_betweenness={score:.6f}<br>"
            f"length_m={data.get('length', '')}<br>"
            f"name={_edge_label(data.get('name'))}<br>"
            f"highway={_edge_label(data.get('highway'))}"
        )
        folium.PolyLine(
            locations=[(u_lat, u_lon), (v_lat, v_lon)],
            color="#d62728",
            weight=weight,
            opacity=0.75,
            popup=popup,
        ).add_to(edge_map)

    edge_map_html = f"{pasta_maps}/arestas_criticas.html"
    edge_map.save(edge_map_html)

    print("[E5] Pronto ✅", flush=True)

    return {
        "top_nodes_csv": nodes_csv,
        "all_nodes_csv": all_nodes_csv,
        "rankings_csv": rankings_csv,
        "top_edges_csv": edges_csv,
        "report_txt": report_txt,
        "map_html": map_html,
        "edge_map_html": edge_map_html,
    }


def approximate_closeness_centrality(G: nx.Graph, samples: int = 120, seed: int = 42) -> dict:
    """Estima closeness como o inverso da distância média a landmarks aleatórios."""
    nodes = list(G.nodes())
    if not nodes:
        return {}
    landmarks = nodes if len(nodes) <= samples else random.Random(seed).sample(nodes, samples)
    distance_sums = {node: 0.0 for node in nodes}
    reached = {node: 0 for node in nodes}
    for landmark in landmarks:
        for node, distance in nx.single_source_shortest_path_length(G, landmark).items():
            if node != landmark and distance > 0:
                distance_sums[node] += float(distance)
                reached[node] += 1
    return {
        node: reached[node] / distance_sums[node] if distance_sums[node] > 0 else 0.0
        for node in nodes
    }
