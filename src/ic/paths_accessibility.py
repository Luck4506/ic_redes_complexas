from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import folium
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml


# =========================
# MODELOS (autoexplicativos)
# =========================
@dataclass(frozen=True)
class Coordenada:
    latitude: float
    longitude: float


# =========================
# DISTÂNCIA HAVERSINE
# =========================
def haversine_metros(a: Coordenada, b: Coordenada) -> float:
    """Distância aproximada em metros entre duas coordenadas (lat/lon)."""
    raio_terra_m = 6_371_000.0
    lat1, lon1 = math.radians(a.latitude), math.radians(a.longitude)
    lat2, lon2 = math.radians(b.latitude), math.radians(b.longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * raio_terra_m * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def encontrar_no_mais_proximo(G: nx.MultiDiGraph, coord: Coordenada) -> Tuple[int, float]:
    """
    Encontra o nó mais próximo em distância geográfica (Haversine).
    Retorna (node_id, distancia_em_metros).
    """
    melhor_no = None
    melhor_dist = float("inf")

    for node_id, dados in G.nodes(data=True):
        node_coord = Coordenada(latitude=float(dados["y"]), longitude=float(dados["x"]))
        dist = haversine_metros(coord, node_coord)
        if dist < melhor_dist:
            melhor_dist = dist
            melhor_no = node_id

    return int(melhor_no), float(melhor_dist)


def distancia_total_rota_m(G: nx.MultiDiGraph, rota: List[int]) -> float:
    """
    Soma o atributo 'length' nas arestas do caminho.
    Como é MultiDiGraph, pode ter múltiplas arestas (u,v,k). Usamos a menor length.
    """
    total = 0.0
    for u, v in zip(rota[:-1], rota[1:]):
        edges_uv = G.get_edge_data(u, v)
        if not edges_uv:
            raise RuntimeError(f"Sem aresta entre {u}->{v} (rota inválida para o grafo).")

        menor = float("inf")
        for _k, data in edges_uv.items():
            length = float(data.get("length", float("inf")))
            if length < menor:
                menor = length

        if math.isinf(menor):
            raise RuntimeError(f"Aresta {u}->{v} sem 'length' válido.")
        total += menor

    return total


def rota_para_latlon(G: nx.MultiDiGraph, rota: List[int]) -> List[Tuple[float, float]]:
    """Converte rota de nós para lista de (lat, lon) para desenhar no Folium."""
    return [(float(G.nodes[n]["y"]), float(G.nodes[n]["x"])) for n in rota]


# =========================
# PIPELINE E4
# =========================
def gerar_rota_distancia(
    city_id: str,
    origem: Optional[Coordenada] = None,
    destino: Optional[Coordenada] = None,
    usar_aleatorio: bool = False,
    seed: int = 42,
) -> dict:
    """
    E4: gera uma rota por menor distância (weight='length') e salva outputs.
    """
    ensure_city_dirs(city_id)
    random.seed(seed)

    caminho_grafo = f"data/graphs/{city_id}_drive_clean.graphml"
    G = load_graphml(caminho_grafo)

    # 1) Escolher origem/destino
    if usar_aleatorio:
        n1, n2 = random.sample(list(G.nodes()), k=2)
        origem = Coordenada(float(G.nodes[n1]["y"]), float(G.nodes[n1]["x"]))
        destino = Coordenada(float(G.nodes[n2]["y"]), float(G.nodes[n2]["x"]))
    else:
        if origem is None or destino is None:
            raise ValueError("Se não usar aleatório, você deve informar origem e destino (lat/lon).")

    # 2) Mapear coordenadas -> nós do grafo
    no_origem, dist_o = encontrar_no_mais_proximo(G, origem)
    no_destino, dist_d = encontrar_no_mais_proximo(G, destino)

    # Diagnóstico útil: se der muito alto, o grafo não cobre a área
    if dist_o > 1500 or dist_d > 1500:
        print(f"[E4] Aviso: origem está a {dist_o:.1f}m do nó mais próximo no grafo.")
        print(f"[E4] Aviso: destino está a {dist_d:.1f}m do nó mais próximo no grafo.")
        print("[E4] Isso normalmente indica que o bbox/radius não cobre bem a região.")

    # 3) Calcular caminho mínimo por distância
    try:
        rota_nodes = nx.shortest_path(G, no_origem, no_destino, weight="length")
    except nx.NetworkXNoPath:
        raise RuntimeError("Não existe caminho entre origem e destino no grafo dirigido (pode ser direção/mão única ou desconexão).")

    distancia_m = distancia_total_rota_m(G, rota_nodes)

    # 4) Salvar outputs
    pasta_metrics = f"outputs/{city_id}/metrics"
    pasta_maps = f"outputs/{city_id}/maps"
    Path(pasta_metrics).mkdir(parents=True, exist_ok=True)
    Path(pasta_maps).mkdir(parents=True, exist_ok=True)

    json_path = f"{pasta_metrics}/rota_distancia.json"
    csv_path = f"{pasta_metrics}/rota_distancia_resumo.csv"
    html_path = f"{pasta_maps}/rota_distancia.html"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"city_id": city_id, "route_nodes": rota_nodes}, f, ensure_ascii=False, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["city_id", "orig_node", "dest_node", "distance_total_m", "num_nodes_in_route"])
        w.writerow([city_id, no_origem, no_destino, f"{distancia_m:.2f}", len(rota_nodes)])

    # 5) Mapa Folium
    coords = rota_para_latlon(G, rota_nodes)
    mapa = folium.Map(location=coords[0], zoom_start=13)

    folium.Marker((origem.latitude, origem.longitude), popup=f"Origem (node={no_origem})", icon=folium.Icon(color="green")).add_to(mapa)
    folium.Marker((destino.latitude, destino.longitude), popup=f"Destino (node={no_destino})", icon=folium.Icon(color="red")).add_to(mapa)
    folium.PolyLine(coords, weight=5, opacity=0.85).add_to(mapa)
    mapa.fit_bounds(coords)
    mapa.save(html_path)

    return {
        "json_path": json_path,
        "csv_path": csv_path,
        "html_path": html_path,
        "orig_node": no_origem,
        "dest_node": no_destino,
        "distance_total_m": distancia_m,
        "num_nodes_in_route": len(rota_nodes),
        "orig_dist_to_graph_m": dist_o,
        "dest_dist_to_graph_m": dist_d,
    }