import osmnx as ox

# ENTENDER A ESTRUTURA DO GRAFO

# Carrega o grafo salvo
G = ox.load_graphml("campinas_drive.graphml") 

print("\nGrafo carregado do arquivo")

# Printa propriedades básicas do grafo
print("Tipo do grafo:", type(G))
print("Nós:", G.number_of_nodes())
print("Arestas:", G.number_of_edges())

# Pega um nó qualquer (o primeiro do iterador)
no_id = next(iter(G.nodes)) # G.nodes é um conjunto de ids de nós

print("\nExemplo de nó (id):", no_id)
print("Atributos do nó:") # street_count = quantidade de ruas conectadas
print(G.nodes[no_id]) 

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

