import json
import osmnx as ox

import networkx as nx


def route_edge_attributes(G, route, attr_name):
    """Retorna uma lista com os valores de um atributo (ex.: length, travel_time)
    ao longo de uma rota.
    """

    values = []
    for u, v in zip(route[:-1], route[1:]):
        data = G.get_edge_data(u, v)
        if data is None:
            raise ValueError(f"Não existe aresta entre {u} -> {v} na rota")

        candidates = []
        for k, attrs in data.items():
            val = attrs.get(attr_name)
            if val is not None:
                candidates.append(val)

        if not candidates:
            raise ValueError(f"Aresta {u}->{v} não possui atributo '{attr_name}'")

        values.append(min(candidates))

    return values

# ORIGEM/DESTINO E CÁLCULO DE ROTA PELO NetworkX
# Definir origem e destino por coordenadas (lat, lon)
# Achar nós mais próximos
# Calcular rota por distância (length) e por tempo (travel_time)
# Somar distância/tempo totais
# Salvar rotas em JSON para a Etapa 5 (mapa)

# /usr/local/bin/python3 -m pip install -U scikit-learn         

# Carrega o grafo com os pesos adicionados
G = ox.load_graphml("campinas_drive_adicionado.graphml")

# Define origem e destino por coordenadas

# Origem (Rio Branco)
latitude_origem, longitude_origem = -22.8267, -47.0744

# Destino (Praça tenente Gertúlio)
latitude_destino, longitude_destino = -22.8294, -47.0869

print("\nOrigem (lat, lon):", (latitude_origem, longitude_origem))
print("Destino (lat, lon):", (latitude_destino, longitude_destino))

# Converte coordenadas em nós do grafo (nó mais próximo)
# nearest_nodes recebe X=longitude e Y=latitude

try:
    no_de_origem = ox.nearest_nodes(G, X=longitude_origem, Y=latitude_origem)
    no_de_destino = ox.nearest_nodes(G, X=longitude_destino, Y=latitude_destino)

except ImportError as e:
    print("\nERRO ao buscar nós mais próximos:")
    print(e)
    raise

print("\nNó origem:", no_de_origem)
print("Nó destino:", no_de_destino)

# Calcula duas rotas:
# - rota mais curta (minimiza length)
# - rota mais rápida estimada (minimiza travel_time)
distancia_rota = nx.shortest_path(G, no_de_origem, no_de_destino, weight="length")
tempo_rota = nx.shortest_path(G, no_de_origem, no_de_destino, weight="travel_time")

print("\nRota por DISTÂNCIA: nós =", len(distancia_rota))
print("Rota por TEMPO: nós =", len(tempo_rota))

# Soma distância total e tempo total das rotas
# O OSMnx tem um helper que pega atributos das arestas ao longo da rota.
distancias_m = route_edge_attributes(G, distancia_rota, "length") #em metros
tempos_s = route_edge_attributes(G, tempo_rota, "travel_time") #em segundos

distancia_total_m = sum(distancias_m)
tempo_total_s = sum(tempos_s)

print("\n--- RESULTADOS ---")
print(f"Distância total (rota por length): {distancia_total_m:.1f} m ({distancia_total_m/1000:.3f} km)") #converte para km
print(f"Tempo total estimado (rota por travel_time): {tempo_total_s:.1f} s ({tempo_total_s/60:.2f} min)") #converte para minutos

# Salva as rotas em JSON
# A rota é uma lista de IDs de nós.

with open("rota_por_distancia.json", "w", encoding="utf-8") as f:
    json.dump(distancia_rota, f, ensure_ascii=False, indent=2)

with open("rota_por_tempo.json", "w", encoding="utf-8") as f:
    json.dump(tempo_rota, f, ensure_ascii=False, indent=2)


