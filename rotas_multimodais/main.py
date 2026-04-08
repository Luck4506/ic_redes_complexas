# main.py
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import folium
import osmnx as ox

import config


@dataclass
class PathMetrics:
    total_distance_km: float
    total_cost_reais: float
    total_co2e_kg: float
    steps_by_mode: Dict[str, int]


def ensure_output_directory_exists(output_directory: str) -> None:
    os.makedirs(output_directory, exist_ok=True)


def build_road_graph(place_name: str, network_type: str) -> nx.MultiDiGraph:
    """Baixa a rede viária do OpenStreetMap.

    Observação importante (compatibilidade OSMnx):
    - Em versões diferentes do OSMnx, a função para adicionar comprimentos pode mudar.
    - Além disso, `graph_from_place` geralmente já retorna arestas com o atributo `length`.

    Então aqui fazemos:
    1) Baixa o grafo.
    2) Garante (se possível) que exista `length` em todas as arestas.
    """
    ox.settings.use_cache = True
    ox.settings.log_console = False

    road_graph = ox.graph_from_place(place_name, network_type=network_type)

    # Muitas versões do OSMnx já trazem `length` pronto.
    # Mas, se estiver faltando, tentamos adicionar de forma compatível.
    try:
        # OSMnx (algumas versões)
        if hasattr(ox, "add_edge_lengths"):
            road_graph = ox.add_edge_lengths(road_graph)
        # Outras versões expõem via ox.distance
        elif hasattr(ox, "distance") and hasattr(ox.distance, "add_edge_lengths"):
            road_graph = ox.distance.add_edge_lengths(road_graph)
    except Exception:
        # Se der algum erro aqui, seguimos: o código abaixo ainda funciona
        # desde que a maioria das arestas já tenha `length`.
        pass

    return road_graph


def nearest_road_node(road_graph: nx.MultiDiGraph, latitude: float, longitude: float) -> int:
    # OSMnx usa x=lon e y=lat.
    return int(ox.distance.nearest_nodes(road_graph, X=longitude, Y=latitude))


def great_circle_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Usa a função do OSMnx (distância aproximada em metros).
    distance_m = ox.distance.great_circle_vec(lat1, lon1, lat2, lon2)
    return float(distance_m) / 1000.0


def terminal_node_id(terminal_name: str, mode_label: str = "TERMINAL") -> str:
    # IDs textuais para não conflitar com IDs numéricos de nós da rede viária.
    return f"{mode_label}:{terminal_name}"


def add_costs_and_emissions_to_road_edges(multimodal_graph: nx.MultiDiGraph) -> None:
    """
    Para cada aresta da rede rodoviária, adiciona:
    - mode = "road"
    - distance_km
    - cost_reais
    - co2e_kg
    """
    for u, v, key, data in multimodal_graph.edges(keys=True, data=True):
        # Só aplica na parte rodoviária: nós numéricos tendem a ser da road network.
        if not isinstance(u, (int, np.integer)) or not isinstance(v, (int, np.integer)):
            continue

        length_m = float(data.get("length", 0.0))
        distance_km = length_m / 1000.0

        data["mode"] = "road"
        data["distance_km"] = distance_km
        data["cost_reais"] = distance_km * config.ROAD_COST_REAIS_PER_KM
        data["co2e_kg"] = distance_km * config.ROAD_CO2E_KG_PER_KM


def add_terminal_nodes(multimodal_graph: nx.MultiDiGraph, terminals: List[Dict]) -> None:
    """
    Adiciona nós de terminais ao grafo com coordenadas (x=lon, y=lat).
    """
    for terminal in terminals:
        node_id = terminal_node_id(terminal["name"])
        multimodal_graph.add_node(
            node_id,
            x=float(terminal["lon"]),
            y=float(terminal["lat"]),
            terminal_name=terminal["name"]
        )


def connect_terminals(
    multimodal_graph: nx.MultiDiGraph,
    terminals: List[Dict],
    connections: List[Tuple[str, str]],
    mode: str,
    cost_per_km: float,
    co2e_per_km: float
) -> None:
    """
    Cria arestas sintéticas entre terminais para um modal (rail/water).
    As arestas são bidirecionais (ida e volta).
    """
    terminals_by_name = {t["name"]: t for t in terminals}

    for start_name, end_name in connections:
        start = terminals_by_name[start_name]
        end = terminals_by_name[end_name]

        distance_km = great_circle_distance_km(start["lat"], start["lon"], end["lat"], end["lon"])
        cost_reais = distance_km * cost_per_km
        co2e_kg = distance_km * co2e_per_km

        start_id = terminal_node_id(start_name)
        end_id = terminal_node_id(end_name)

        # Geometria simples: linha reta (guardamos como lista de coordenadas lat/lon)
        geometry_latlon = [(start["lat"], start["lon"]), (end["lat"], end["lon"])]

        for (u, v) in [(start_id, end_id), (end_id, start_id)]:
            multimodal_graph.add_edge(
                u, v,
                mode=mode,
                distance_km=distance_km,
                cost_reais=cost_reais,
                co2e_kg=co2e_kg,
                geometry_latlon=geometry_latlon
            )


def connect_terminals_to_road_with_transfer_edges(
    multimodal_graph: nx.MultiDiGraph,
    road_graph: nx.MultiDiGraph,
    terminals: List[Dict]
) -> None:
    """
    Conecta cada terminal ao nó rodoviário mais próximo por arestas de transbordo.
    """
    transfer_cost = config.TRANSFER_COST_REAIS_PER_TU * float(config.CARGO_TU)

    for terminal in terminals:
        terminal_id = terminal_node_id(terminal["name"])
        nearest_node = nearest_road_node(road_graph, terminal["lat"], terminal["lon"])

        # Transbordo: custo fixo, emissões zero (simplificado), distância zero.
        # Bidirecional (entrar e sair do terminal).
        multimodal_graph.add_edge(
            nearest_node, terminal_id,
            mode="transfer",
            distance_km=0.0,
            cost_reais=transfer_cost,
            co2e_kg=0.0
        )
        multimodal_graph.add_edge(
            terminal_id, nearest_node,
            mode="transfer",
            distance_km=0.0,
            cost_reais=transfer_cost,
            co2e_kg=0.0
        )


def build_best_edge_digraph(multigraph: nx.MultiDiGraph, weight_attribute: str) -> nx.DiGraph:
    """
    Converte MultiDiGraph -> DiGraph escolhendo, para cada par (u,v),
    a aresta com menor weight_attribute.

    Isso simplifica o shortest_path e preserva atributos do “melhor” edge.
    """
    digraph = nx.DiGraph()
    digraph.add_nodes_from(multigraph.nodes(data=True))

    for u, v, key, data in multigraph.edges(keys=True, data=True):
        if weight_attribute not in data:
            continue

        candidate_weight = float(data[weight_attribute])

        if digraph.has_edge(u, v):
            current_weight = float(digraph[u][v][weight_attribute])
            if candidate_weight >= current_weight:
                continue

        digraph.add_edge(u, v, **data, selected_key=key)

    return digraph


def compute_path_metrics(path_nodes: List, path_graph: nx.DiGraph) -> PathMetrics:
    """
    Soma distância/custo/emissões ao longo do caminho.
    Também conta quantos “passos” (arestas) foram feitos em cada modo.
    """
    total_distance_km = 0.0
    total_cost_reais = 0.0
    total_co2e_kg = 0.0
    steps_by_mode: Dict[str, int] = {}

    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i + 1]
        edge_data = path_graph[u][v]

        total_distance_km += float(edge_data.get("distance_km", 0.0))
        total_cost_reais += float(edge_data.get("cost_reais", 0.0))
        total_co2e_kg += float(edge_data.get("co2e_kg", 0.0))

        mode = str(edge_data.get("mode", "unknown"))
        steps_by_mode[mode] = steps_by_mode.get(mode, 0) + 1

    return PathMetrics(total_distance_km, total_cost_reais, total_co2e_kg, steps_by_mode)


def create_score_attribute(multigraph: nx.MultiDiGraph, lambda_value: float) -> None:
    """
    Cria/atualiza o atributo 'score' em cada aresta:
    score = cost_reais + lambda * co2e_kg
    """
    for _, _, _, data in multigraph.edges(keys=True, data=True):
        cost_reais = float(data.get("cost_reais", 0.0))
        co2e_kg = float(data.get("co2e_kg", 0.0))
        data["score"] = cost_reais + float(lambda_value) * co2e_kg


def add_path_to_map(
    folium_map: folium.Map,
    path_nodes: List,
    path_graph: nx.DiGraph,
    feature_group_name: str
) -> None:
    """
    Desenha o caminho no mapa, colorindo cada segmento pelo modo.
    """
    mode_color = {
        "road": "blue",
        "rail": "green",
        "water": "purple",
        "transfer": "black",
        "unknown": "gray"
    }

    layer = folium.FeatureGroup(name=feature_group_name, show=True)

    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i + 1]
        edge_data = path_graph[u][v]

        mode = str(edge_data.get("mode", "unknown"))
        color = mode_color.get(mode, "gray")

        # Se tiver geometria lat/lon (terminais), use.
        if "geometry_latlon" in edge_data:
            segment_latlon = edge_data["geometry_latlon"]
        else:
            # Caso rodoviário: tenta geometry do OSM (LineString) se existir.
            geometry = edge_data.get("geometry", None)
            if geometry is not None and hasattr(geometry, "coords"):
                segment_latlon = [(lat, lon) for (lon, lat) in geometry.coords]
            else:
                # fallback: linha reta entre os nós.
                node_u = path_graph.nodes[u]
                node_v = path_graph.nodes[v]
                segment_latlon = [(float(node_u["y"]), float(node_u["x"])),
                                 (float(node_v["y"]), float(node_v["x"]))]

        tooltip_text = (
            f"Modo: {mode} | "
            f"Dist(km): {edge_data.get('distance_km', 0):.2f} | "
            f"Custo(R$): {edge_data.get('cost_reais', 0):.2f} | "
            f"CO2e(kg): {edge_data.get('co2e_kg', 0):.3f}"
        )

        folium.PolyLine(
            locations=segment_latlon,
            color=color,
            weight=5 if mode != "transfer" else 3,
            opacity=0.8,
            tooltip=tooltip_text
        ).add_to(layer)

    layer.add_to(folium_map)


def main() -> None:
    ensure_output_directory_exists(config.OUTPUT_DIR)

    road_graph = build_road_graph(config.PLACE_NAME, config.NETWORK_TYPE)

    origin_lat, origin_lon = config.ORIGIN_COORDINATES
    dest_lat, dest_lon = config.DESTINATION_COORDINATES

    origin_node = nearest_road_node(road_graph, origin_lat, origin_lon)
    destination_node = nearest_road_node(road_graph, dest_lat, dest_lon)

    # Começamos do grafo rodoviário e adicionamos camadas multimodais em cima dele.
    multimodal_graph = road_graph.copy()

    # 1) Atribui custo/emissões na parte rodoviária
    add_costs_and_emissions_to_road_edges(multimodal_graph)

    # 2) Adiciona nós de terminais
    add_terminal_nodes(multimodal_graph, config.TERMINALS)

    # 3) Conecta terminais entre si (rail e water)
    connect_terminals(
        multimodal_graph,
        config.TERMINALS,
        config.RAIL_CONNECTIONS,
        mode="rail",
        cost_per_km=config.RAIL_COST_REAIS_PER_KM,
        co2e_per_km=config.RAIL_CO2E_KG_PER_KM
    )

    connect_terminals(
        multimodal_graph,
        config.TERMINALS,
        config.WATER_CONNECTIONS,
        mode="water",
        cost_per_km=config.WATER_COST_REAIS_PER_KM,
        co2e_per_km=config.WATER_CO2E_KG_PER_KM
    )

    # 4) Transbordo: liga terminal ao nó rodoviário mais próximo
    connect_terminals_to_road_with_transfer_edges(multimodal_graph, road_graph, config.TERMINALS)

    # --------- Rotas: custo mínimo e emissões mínimas ----------
    best_by_cost_graph = build_best_edge_digraph(multimodal_graph, weight_attribute="cost_reais")
    best_by_emissions_graph = build_best_edge_digraph(multimodal_graph, weight_attribute="co2e_kg")

    path_min_cost = nx.shortest_path(best_by_cost_graph, origin_node, destination_node, weight="cost_reais")
    path_min_emissions = nx.shortest_path(best_by_emissions_graph, origin_node, destination_node, weight="co2e_kg")

    metrics_min_cost = compute_path_metrics(path_min_cost, best_by_cost_graph)
    metrics_min_emissions = compute_path_metrics(path_min_emissions, best_by_emissions_graph)

    # --------- Trade-off: varre lambdas ----------
    scenario_rows = []
    pareto_points = []

    for lambda_value in config.LAMBDA_VALUES:
        create_score_attribute(multimodal_graph, lambda_value)
        best_by_score_graph = build_best_edge_digraph(multimodal_graph, weight_attribute="score")

        path_tradeoff = nx.shortest_path(best_by_score_graph, origin_node, destination_node, weight="score")
        metrics_tradeoff = compute_path_metrics(path_tradeoff, best_by_score_graph)

        scenario_rows.append({
            "lambda": lambda_value,
            "distance_km": metrics_tradeoff.total_distance_km,
            "cost_reais": metrics_tradeoff.total_cost_reais,
            "co2e_kg": metrics_tradeoff.total_co2e_kg,
            "steps_modes": dict(metrics_tradeoff.steps_by_mode)
        })
        pareto_points.append((metrics_tradeoff.total_cost_reais, metrics_tradeoff.total_co2e_kg, lambda_value))

    scenarios_df = pd.DataFrame(scenario_rows)
    csv_output_path = os.path.join(config.OUTPUT_DIR, "cenarios_tradeoff.csv")
    scenarios_df.to_csv(csv_output_path, index=False)

    # --------- Mapa (Folium) ----------
    map_center = [float(origin_lat), float(origin_lon)]
    folium_map = folium.Map(location=map_center, zoom_start=12)

    # Marcadores de origem/destino
    folium.Marker([origin_lat, origin_lon], tooltip="Origem").add_to(folium_map)
    folium.Marker([dest_lat, dest_lon], tooltip="Destino").add_to(folium_map)

    # Marcadores dos terminais
    for terminal in config.TERMINALS:
        folium.CircleMarker(
            location=[terminal["lat"], terminal["lon"]],
            radius=6,
            tooltip=f"Terminal: {terminal['name']}",
            fill=True,
            fill_opacity=0.9
        ).add_to(folium_map)

    # Desenha rotas “extremas”
    add_path_to_map(folium_map, path_min_cost, best_by_cost_graph, "Rota (custo mínimo)")
    add_path_to_map(folium_map, path_min_emissions, best_by_emissions_graph, "Rota (CO2e mínimo)")

    # Desenha uma rota trade-off (pega o lambda do meio, se existir)
    lambda_for_map = config.LAMBDA_VALUES[len(config.LAMBDA_VALUES) // 2]
    create_score_attribute(multimodal_graph, lambda_for_map)
    best_by_score_graph_for_map = build_best_edge_digraph(multimodal_graph, weight_attribute="score")
    path_tradeoff_for_map = nx.shortest_path(best_by_score_graph_for_map, origin_node, destination_node, weight="score")
    add_path_to_map(folium_map, path_tradeoff_for_map, best_by_score_graph_for_map, f"Rota trade-off (lambda={lambda_for_map})")

    folium.LayerControl(collapsed=False).add_to(folium_map)
    html_output_path = os.path.join(config.OUTPUT_DIR, "mapa_rotas_multimodais.html")
    folium_map.save(html_output_path)

    # --------- Gráfico custo x emissões ----------
    costs = [p[0] for p in pareto_points]
    emissions = [p[1] for p in pareto_points]
    lambdas = [p[2] for p in pareto_points]

    plt.figure()
    plt.scatter(costs, emissions)
    for x, y, lam in pareto_points:
        plt.annotate(str(lam), (x, y), fontsize=9)

    plt.xlabel("Custo total (R$)")
    plt.ylabel("CO2e total (kg)")
    plt.title("Trade-off: custo vs CO2e (anotado por lambda)")
    plot_output_path = os.path.join(config.OUTPUT_DIR, "tradeoff_custo_vs_co2e.png")
    plt.savefig(plot_output_path, dpi=200, bbox_inches="tight")
    plt.close()

    # Resumo no terminal
    print("OK! Arquivos gerados:")
    print(f"- {csv_output_path}")
    print(f"- {html_output_path}")
    print(f"- {plot_output_path}")
    print("\nResumo rotas extremas:")
    print(f"  Custo mínimo -> Dist: {metrics_min_cost.total_distance_km:.2f} km | "
          f"Custo: R$ {metrics_min_cost.total_cost_reais:.2f} | CO2e: {metrics_min_cost.total_co2e_kg:.3f} kg")
    print(f"  CO2e mínimo  -> Dist: {metrics_min_emissions.total_distance_km:.2f} km | "
          f"Custo: R$ {metrics_min_emissions.total_cost_reais:.2f} | CO2e: {metrics_min_emissions.total_co2e_kg:.3f} kg")


if __name__ == "__main__":
    main()