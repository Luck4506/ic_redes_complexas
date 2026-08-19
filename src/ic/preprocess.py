from __future__ import annotations

from pathlib import Path
import networkx as nx

from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml, save_graphml


def preprocess_city(city_id: str) -> dict:
    ensure_city_dirs(city_id)

    raw_path = str(dataset_graph_path(city_id, "raw"))
    clean_path = str(dataset_graph_path(city_id, "clean"))
    log_path = f"outputs/{city_id}/logs/grafo_resumo.txt"

    G = load_graphml(raw_path)

    nodes_before = G.number_of_nodes()
    edges_before = G.number_of_edges()

    if nx.is_weakly_connected(G):
        G_clean = G
        used_lcc = False
    else:
        largest_wcc = max(nx.weakly_connected_components(G), key=len)
        G_clean = G.subgraph(largest_wcc).copy()
        used_lcc = True

    nodes_after = G_clean.number_of_nodes()
    edges_after = G_clean.number_of_edges()

    missing_length = 0
    for _, _, data in G_clean.edges(data=True):
        if "length" not in data:
            missing_length += 1

    save_graphml(G_clean, clean_path)

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("=== Resumo do Grafo (E2) ===\n\n")
        f.write(f"Entrada: {raw_path}\n")
        f.write(f"Saída:   {clean_path}\n\n")
        f.write(f"Nós (antes): {nodes_before}\n")
        f.write(f"Arestas (antes): {edges_before}\n\n")
        f.write(f"Usou maior componente (weakly connected)? {'SIM' if used_lcc else 'NÃO'}\n")
        f.write(f"Nós (depois): {nodes_after}\n")
        f.write(f"Arestas (depois): {edges_after}\n\n")
        f.write(f"Arestas sem 'length': {missing_length}\n")

    return {
        "raw_path": raw_path,
        "clean_path": clean_path,
        "log_path": log_path,
        "nodes_before": nodes_before,
        "edges_before": edges_before,
        "nodes_after": nodes_after,
        "edges_after": edges_after,
        "missing_length_edges": missing_length,
    }
