import json
import osmnx as ox
import folium
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

#BAIXAR A REDE VIÁRIA DE CAMPINAS (OSMnx)


ox.settings.log_console = True      
ox.settings.use_cache = True        
ox.settings.requests_timeout = 60   

# Definir um ponto central por latitude e longitude

# Coordenadas de Campinas
center_lat = -22.9056
center_lon = -47.0608

# Centro aproximado de Campinas:
# -22.9056, -47.0608

# Centro de barão Geraldo:
# -22.8281, -47.0792

# Definir o tamanho do raio de recorte
dist_m = 10000

# Baixa a rede viária e devolve um grafo do NetworkX (MultiDiGraph)
G = ox.graph_from_point(
    (center_lat, center_lon), dist=dist_m, network_type="drive", simplify=True
)

# Resumo  do grafo
print("\nResumo:")
print(G)

# Salva o grafo em arquivo GraphML
ox.save_graphml(G, "campinas_drive.graphml")
print("\nSalvo em: campinas_drive.graphml")

# Visualização estática
fig, ax = ox.plot_graph(G, show=False, close=False)
fig.savefig("campinas_grafo.png", dpi=200)

# Carrega o grafo salvo
G = ox.load_graphml("campinas_drive.graphml") 

print("\nGrafo carregado do arquivo")

# Printa propriedades básicas do grafo
print("Tipo do grafo:", type(G))
print("Nós:", G.number_of_nodes())
print("Arestas:", G.number_of_edges())

# Pega um nó qualquer (o primeiro do iterador)
node_id = next(iter(G.nodes)) # G.nodes é um conjunto de ids de nós

print("\nExemplo de nó (id):", node_id)
print("Atributos do nó:") # street_count = quantidade de ruas conectadas
print(G.nodes[node_id]) 

# Pega uma aresta
# Obs: Em MultiDiGraph, arestas são identificadas por (u, v, k)
u, v, k = next(iter(G.edges(keys=True)))

print("\nExemplo de aresta:", (u, v, k))
print("Atributos da rua (aresta):")
print(G.edges[u, v, k])

# Amostra de 5 nós e 5 arestas 
print("\nAmostra de 5 nós:")
for i, n in enumerate(G.nodes):
    if i == 5:
        break
    print(n, G.nodes[n])

print("\nAmostra de 5 arestas (mostrando o comprimento):")
for i, (uu, vv, kk) in enumerate(G.edges(keys=True)):
    if i == 5:
        break
    print((uu, vv, kk), "comprimento=", G.edges[uu, vv, kk].get("length")) 

# CRIAR DISTÂNCIA E TEMPO

#Carrega o grafo
G = ox.load_graphml("campinas_drive.graphml")

# Checar atributos da aresta para comparação antes/depois
u, v, k = next(iter(G.edges(keys=True)))
edge_before = G.edges[u, v, k]

print("\nDados antes de adicionar speeds/travel_time:")
print("u,v,k =", (u, v, k))
print("length =", edge_before.get("length"))
print("speed_kph =", edge_before.get("speed_kph"))
print("travel_time =", edge_before.get("travel_time"))

# Adiciona velocidades estimadas
# ajusta o 'speed_kph' nas arestas
G = ox.add_edge_speeds(G) # Faz para todas as arestas que não têm speed_kph (como se tivesse um for/While)

# Adiciona tempo de viagem
# Cria o 'travel_time' (em segundos) nas arestas
G = ox.add_edge_travel_times(G)

# Checa novamente a mesma aresta (para ver a diferença)
u2, v2, k2 = next(iter(G.edges(keys=True)))
edge_after = G.edges[u2, v2, k2]

print("\nDados depois de adicionar speeds/travel_time:")
print("u,v,k =", (u2, v2, k2))
print("length =", edge_after.get("length"))
print("speed_kph =", edge_after.get("speed_kph"))
print("travel_time =", edge_after.get("travel_time"))



# Salva grafo atualizado 
ox.save_graphml(G, "campinas_drive_adicionado.graphml")



# ORIGEM/DESTINO E CÁLCULO DE ROTA PELO NetworkX

# Carrega o grafo com os pesos adicionados
G = ox.load_graphml("campinas_drive_adicionado.graphml")

# Defina origem e destino por coordenadas (lat, lon)
# Origem (Puc)
latitude_origem, longitude_origem = -22.8344, -47.0528

# Destino (Bosque dos Jequitibás)
latitude_destino, longitude_destino = -22.9092, -47.0508

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
lengths_m = route_edge_attributes(G, distancia_rota, "length")
times_s = route_edge_attributes(G, tempo_rota, "travel_time")

total_length_m = sum(lengths_m)
total_time_s = sum(times_s)

print("\n--- RESULTADOS ---")
print(f"Distância total (rota por length): {total_length_m:.1f} m ({total_length_m/1000:.3f} km)")
print(f"Tempo total estimado (rota por travel_time): {total_time_s:.1f} s ({total_time_s/60:.2f} min)")

# Salva as rotas em JSON
# A rota é uma lista de IDs de nós.
# Para desenhar no mapa, a gente transforma isso em uma linha (“polyline”) ligando os nós na ordem.

with open("rota_por_distancia.json", "w", encoding="utf-8") as f:
    json.dump(distancia_rota, f, ensure_ascii=False, indent=2)

with open("rota_por_tempo.json", "w", encoding="utf-8") as f:
    json.dump(tempo_rota, f, ensure_ascii=False, indent=2)


# VISUALIZAR O MAPA USANDO FOLIUM

#Carrega o grafo
G = ox.load_graphml("campinas_drive_adicionado.graphml")

# Carrega a rota salva
with open("rota_por_tempo.json", "r", encoding="utf-8") as f:
    route = json.load(f)


# Obs: GraphML pode transformar IDs em string
example_node = next(iter(G.nodes))
if isinstance(example_node, str):
    route = [str(n) for n in route]
    print("[Etapa 5] Converti a rota para string (GraphML carregou nós como str).")


# Desenha a rota no Folium 
# Transformamos a rota (lista de nós) em uma lista de coordenadas (lat, lon)
route_latlon = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]

# Centraliza o mapa aproximadamente no meio da rota
mid_idx = len(route_latlon) // 2
center_lat, center_lon = route_latlon[mid_idx]

# Cria o mapa base
m = folium.Map(location=(center_lat, center_lon), zoom_start=13)

# Desenha a rota como uma linha
folium.PolyLine(route_latlon, weight=5, opacity=0.8).add_to(m)

#Marca a origem e destino (não estético)
orig_node = route[0]
dest_node = route[-1]

orig_lat = G.nodes[orig_node]["y"]
orig_lon = G.nodes[orig_node]["x"]
dest_lat = G.nodes[dest_node]["y"]
dest_lon = G.nodes[dest_node]["x"]

# Adiciona marcadores
folium.Marker(location=(orig_lat, orig_lon), popup="Origem", icon=folium.Icon(icon="play", prefix="fa")
).add_to(m)

folium.Marker( location=(dest_lat, dest_lon), popup="Destino", icon=folium.Icon(icon="stop", prefix="fa")
).add_to(m)

# Salva o HTML
output_file = "rota_campinas_por_tempo.html"
m.save(output_file)
print(f"\nMapa salvo em: {output_file}")