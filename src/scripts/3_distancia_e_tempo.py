import osmnx as ox

# CRIAR DISTÂNCIA E TEMPO

# rota mais curta = minimizar soma de length
# rota mais rápida = minimizar soma de travel_time
# Faz uma estimativa desconciiderando o trânsito real

#Carrega o grafo
G = ox.load_graphml("campinas_drive.graphml")

# Checar atributos da aresta para comparação
u, v, k = next(iter(G.edges(keys=True)))
aresta = G.edges[u, v, k]

print("\nDados antes de adicionar speeds/travel_time:")
print("u,v,k =", (u, v, k))
print("length =", aresta.get("length"))
print("speed_kph =", aresta.get("speed_kph"))
print("travel_time =", aresta.get("travel_time"))

# Adiciona velocidades estimadas
# ajusta o 'speed_kph' nas arestas
G = ox.add_edge_speeds(G) # Faz para todas as arestas que não têm speed_kph (como se tivesse um for/While)

# Adiciona tempo de viagem
# Cria o 'travel_time' (em segundos) nas arestas
G = ox.add_edge_travel_times(G)

# Checa novamente a mesma aresta (para ver a diferença)
u2, v2, k2 = next(iter(G.edges(keys=True)))
aresta_adicionada = G.edges[u2, v2, k2]

print("\nDados depois de adicionar speeds/travel_time:")
print("u,v,k =", (u2, v2, k2))
print(f"length = {aresta_adicionada.get("length"):0f}")
print("speed_kph =", aresta_adicionada.get("speed_kph"))
print(f"travel_time = {aresta_adicionada.get("travel_time"):0f}")

# Verifica quantas arestas têm travel_time preenchido (sanidade)
# count_tt = 0
# total = 0
# for uu, vv, kk in G.edges(keys=True):
#     total += 1
#     if G.edges[uu, vv, kk].get("travel_time") is not None:
#         count_tt += 1

# print(f"\nArestas com travel_time preenchido: {count_tt}/{total}")

# Salva grafo atualizado para a próxima etapa
ox.save_graphml(G, "campinas_drive_adicionado.graphml")