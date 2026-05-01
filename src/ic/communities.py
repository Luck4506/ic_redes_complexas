from __future__ import annotations

import csv
import random
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set

import folium
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph


def _paleta_cores() -> List[str]:
    # Paleta simples e bem distinta (não precisa de libs extras)
    return [
        "#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
        "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080",
        "#e6beff", "#9A6324", "#fffac8", "#800000", "#aaffc3",
        "#808000", "#ffd8b1", "#000075", "#808080", "#000000",
    ]


def detectar_comunidades(
    city_id: str,
    method: str = "greedy",
    min_size_for_map: int = 30,
    seed: int = 42,
) -> dict:
    """
    E6: Detecção de comunidades na rede viária (grafo limpo).
    - Converte para grafo não-direcionado
    - Pega maior componente conexa
    - Detecta comunidades (greedy modularity por padrão)
    - Salva CSVs + mapa

    Saídas:
      outputs/<city>/metrics/nodes_communities.csv
      outputs/<city>/metrics/community_summary.csv
      outputs/<city>/maps/comunidades.html
      outputs/<city>/logs/communities_report.txt
    """
    ensure_city_dirs(city_id)
    random.seed(seed)

    grafo_path = f"data/graphs/{city_id}_drive_clean.graphml"
    print(f"[E6] Carregando grafo: {grafo_path}", flush=True)
    G_dir = load_graphml(grafo_path)

    # Trabalhar com estrutura (unweighted) -> undirected
    Gu = simple_undirected_min_length_graph(G_dir)

    # Maior componente conexa (evita comunidades “falsas” por desconexão)
    if nx.is_connected(Gu):
        G = Gu
        used_cc = False
    else:
        largest_cc = max(nx.connected_components(Gu), key=len)
        G = Gu.subgraph(largest_cc).copy()
        used_cc = True

    print(f"[E6] Grafo para comunidades: nós={G.number_of_nodes()} arestas={G.number_of_edges()}", flush=True)
    print(f"[E6] Usou maior componente? {'SIM' if used_cc else 'NÃO'}", flush=True)

    # 1) Detectar comunidades
    if method == "greedy":
        print("[E6] Rodando greedy_modularity_communities...", flush=True)
        comunidades: List[Set[int]] = list(nx.algorithms.community.greedy_modularity_communities(G))
    elif method == "louvain":
        # Só funciona se sua versão do networkx tiver louvain_communities
        if not hasattr(nx.algorithms.community, "louvain_communities"):
            raise RuntimeError("Seu NetworkX não tem louvain_communities. Use --method greedy.")
        print("[E6] Rodando louvain_communities...", flush=True)
        comunidades = list(nx.algorithms.community.louvain_communities(G, seed=seed))
    else:
        raise ValueError("method deve ser 'greedy' ou 'louvain'.")

    num_com = len(comunidades)
    tamanhos = [len(c) for c in comunidades]

    # Modularidade (quanto maior, melhor separação; em redes reais costuma ser moderada)
    modularidade = nx.algorithms.community.modularity(G, comunidades)
    print(f"[E6] Comunidades detectadas: {num_com} | modularidade={modularidade:.4f}", flush=True)

    # 2) Mapear nó -> id da comunidade
    node_to_comm: Dict[int, int] = {}
    for cid, nodes in enumerate(comunidades):
        for n in nodes:
            node_to_comm[int(n)] = cid

    # 3) Salvar outputs
    pasta_metrics = f"outputs/{city_id}/metrics"
    pasta_maps = f"outputs/{city_id}/maps"
    pasta_logs = f"outputs/{city_id}/logs"
    Path(pasta_metrics).mkdir(parents=True, exist_ok=True)
    Path(pasta_maps).mkdir(parents=True, exist_ok=True)
    Path(pasta_logs).mkdir(parents=True, exist_ok=True)

    nodes_csv = f"{pasta_metrics}/nodes_communities.csv"
    summary_csv = f"{pasta_metrics}/community_summary.csv"
    report_txt = f"{pasta_logs}/communities_report.txt"
    map_html = f"{pasta_maps}/comunidades.html"

    # CSV nó -> comunidade
    with open(nodes_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "lat", "lon", "community_id"])
        for node in G.nodes():
            lat = float(G_dir.nodes[node]["y"])
            lon = float(G_dir.nodes[node]["x"])
            w.writerow([node, lat, lon, node_to_comm[int(node)]])

    # Resumo por comunidade
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["community_id", "size"])
        for cid, size in sorted(enumerate(tamanhos), key=lambda x: x[1], reverse=True):
            w.writerow([cid, size])

    # Relatório
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("=== Comunidades (E6) ===\n\n")
        f.write(f"Entrada: {grafo_path}\n")
        f.write(f"Undirected + maior componente? {'SIM' if used_cc else 'NÃO'}\n")
        f.write(f"Nós analisados: {G.number_of_nodes()} | Arestas: {G.number_of_edges()}\n")
        f.write(f"Método: {method}\n")
        f.write(f"Comunidades: {num_com}\n")
        f.write(f"Modularidade: {modularidade:.6f}\n\n")
        f.write("Top 10 tamanhos:\n")
        for cid, size in sorted(enumerate(tamanhos), key=lambda x: x[1], reverse=True)[:10]:
            f.write(f"  cid={cid} size={size}\n")

    # 4) Mapa (mostramos só comunidades acima de min_size_for_map)
    cores = _paleta_cores()
    # Pega a maior comunidade para centralizar
    maior_cid = max(range(num_com), key=lambda c: tamanhos[c])
    any_node = next(iter(comunidades[maior_cid]))
    center_lat = float(G_dir.nodes[any_node]["y"])
    center_lon = float(G_dir.nodes[any_node]["x"])

    mapa = folium.Map(location=(center_lat, center_lon), zoom_start=12)

    # Filtrar comunidades pequenas no mapa (senão vira ruído)
    allowed = {cid for cid, size in enumerate(tamanhos) if size >= min_size_for_map}

    for node in G.nodes():
        cid = node_to_comm[int(node)]
        if cid not in allowed:
            continue
        lat = float(G_dir.nodes[node]["y"])
        lon = float(G_dir.nodes[node]["x"])
        color = cores[cid % len(cores)]
        folium.CircleMarker(
            location=(lat, lon),
            radius=2,
            color=color,
            fill=True,
            fill_opacity=0.7,
            opacity=0.7,
            popup=f"node={node}<br>community={cid}",
        ).add_to(mapa)

    mapa.save(map_html)
    print("[E6] Pronto ✅", flush=True)

    return {
        "nodes_csv": nodes_csv,
        "summary_csv": summary_csv,
        "report_txt": report_txt,
        "map_html": map_html,
        "num_communities": num_com,
        "modularity": modularidade,
    }
