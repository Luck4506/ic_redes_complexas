from __future__ import annotations

import csv
from pathlib import Path

import folium
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph


def calcular_centralidades(
    city_id: str,
    top_k: int = 30,
    k_betweenness: int = 120,
    k_edge_betweenness: int = 60,
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

    print("[E5] 1/3 degree_centrality...", flush=True)
    degree_c = nx.degree_centrality(G)

    k_b = min(k_betweenness, n)
    print(f"[E5] 2/3 betweenness (aprox, k={k_b})...", flush=True)
    betw = nx.betweenness_centrality(G, k=k_b, normalized=True, seed=seed)

    k_e = min(k_edge_betweenness, n)
    print(f"[E5] 3/3 edge_betweenness (aprox, k={k_e})...", flush=True)
    edge_b = nx.edge_betweenness_centrality(G, k=k_e, normalized=True, seed=seed)

    top_nodes = sorted(betw.items(), key=lambda x: x[1], reverse=True)[:top_k]
    top_edges = sorted(edge_b.items(), key=lambda x: x[1], reverse=True)[:top_k]

    pasta_metrics = f"outputs/{city_id}/metrics"
    pasta_maps = f"outputs/{city_id}/maps"
    pasta_logs = f"outputs/{city_id}/logs"
    Path(pasta_metrics).mkdir(parents=True, exist_ok=True)
    Path(pasta_maps).mkdir(parents=True, exist_ok=True)
    Path(pasta_logs).mkdir(parents=True, exist_ok=True)

    nodes_csv = f"{pasta_metrics}/top_nodes.csv"
    with open(nodes_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "lat", "lon", "degree_centrality", "betweenness"])
        for node, _score in top_nodes:
            lat = float(G_dir.nodes[node]["y"])
            lon = float(G_dir.nodes[node]["x"])
            w.writerow([node, lat, lon, degree_c.get(node, 0.0), betw.get(node, 0.0)])

    edges_csv = f"{pasta_metrics}/top_edges.csv"
    with open(edges_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["u", "v", "edge_betweenness"])
        for (u, v), score in top_edges:
            w.writerow([u, v, score])

    report_txt = f"{pasta_logs}/centrality_report.txt"
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("=== Centralidades (E5) ===\n\n")
        f.write(f"Entrada: {grafo_path}\n")
        f.write(f"Nós: {n} | Arestas: {m}\n")
        f.write(f"Betweenness aprox: k={k_b}, seed={seed}\n")
        f.write(f"Edge betweenness aprox: k={k_e}, seed={seed}\n\n")
        f.write("Top 10 nós por betweenness:\n")
        for node, score in top_nodes[:10]:
            f.write(f"  node={node}  betweenness={score:.6f}\n")

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

    print("[E5] Pronto ✅", flush=True)

    return {
        "top_nodes_csv": nodes_csv,
        "top_edges_csv": edges_csv,
        "report_txt": report_txt,
        "map_html": map_html,
    }
