import os
import csv
import osmnx as ox
import networkx as nx
from operator import itemgetter


# Entrada: campinas_drive_adicionado.graphml
# Saídas:
#  - 6_top_nos.csv (top nós por métricas)
#  - 6_top_arestas.csv (top arestas por betweenness)
#  - 6_pontos_criticos.html (mapa com top nós marcados)
#
# Observação: betweenness/closeness em grafos grandes é pesado.
# Aqui usamos aproximação com amostragem (k = número de fontes amostradas).

ARQUIVO_GRAFO = "campinas_drive_adicionado.graphml"
QUANTIDADE_TOP_PONTOS = 20       
AMOSTRAS_BETWEENNESS = 400 
AMOSTRAS_BETWEENNESS_ARESTAS = 200
#Quanto maior a quantidade de amostras, mais pesado 

grafo = ox.load_graphml(ARQUIVO_GRAFO)
print(f"\nGrafo carregado: {ARQUIVO_GRAFO}")
print("Tipo:", type(grafo))
print("Nós:", grafo.number_of_nodes(), " | Arestas:", grafo.number_of_edges())

# Garante que está no maior componente conectado 
if nx.is_weakly_connected(grafo): #fracamente conexo -> Se for ignorada a direção das arestas, ainda dá para encontar um nó.
    grafo_conexo = grafo
    print("Grafo já é fracamente conexo.")
else:
    maior_componente = max(nx.weakly_connected_components(grafo), key=len)
    grafo_conexo = grafo.subgraph(maior_componente).copy()
    print("Grafo NÃO era conexo. Usando maior componente:")
    print("Nós:", grafo_conexo.number_of_nodes(), "| Arestas:", grafo_conexo.number_of_edges())

grafo_nao_direcionado = nx.Graph(grafo_conexo)  # colapsa múltiplas arestas entre nós; bom para métricas gerais
total_nos = grafo_nao_direcionado.number_of_nodes()
total_arestas = grafo_nao_direcionado.number_of_edges()
print("\nVersão undirected para métricas.")
print("Nós:", total_nos, "| Arestas:", total_arestas)

# 4) Métricas básicas rápidas
densidade = nx.density(grafo_nao_direcionado)
grau_medio = sum(dict(grafo_nao_direcionado.degree()).values()) / total_nos
print("\n[Métricas básicas]")
print("Densidade:", densidade)
print("Grau médio:", grau_medio)

# 5) Degree centrality (rápida)
centralidade_grau = nx.degree_centrality(grafo_nao_direcionado)

# 6) Betweenness (aproximada com amostragem)
# k não pode ser maior que total_nos
amostras_betweenness_nos = min(AMOSTRAS_BETWEENNESS, total_nos)
print(f"\n[Etapa 6] Calculando betweenness (aprox), k={amostras_betweenness_nos} ...")
centralidade_intermediacao = nx.betweenness_centrality(grafo_nao_direcionado, k=amostras_betweenness_nos, normalized=True, seed=42)

# 7) Closeness/harmonic: harmonic costuma ser mais estável em grafos grandes
# (ainda pode ser pesado; se travar, comente esta parte)
print("[Etapa 6] Calculando harmonic centrality ...")
centralidade_harmonica = nx.harmonic_centrality(grafo_nao_direcionado)

# 8) Arestas críticas: edge betweenness (aproximado)
amostras_betweenness_arestas = min(AMOSTRAS_BETWEENNESS_ARESTAS, total_nos)
print(f"[Etapa 6] Calculando edge betweenness (aprox), k={amostras_betweenness_arestas} ...")
intermediacao_arestas = nx.edge_betweenness_centrality(grafo_nao_direcionado, k=amostras_betweenness_arestas, normalized=True, seed=42)

# 9) Rankear nós (pontos críticos)
top_nos_por_intermediacao = sorted(centralidade_intermediacao.items(), key=itemgetter(1), reverse=True)[:QUANTIDADE_TOP_PONTOS]
top_nos_por_grau = sorted(centralidade_grau.items(), key=itemgetter(1), reverse=True)[:QUANTIDADE_TOP_PONTOS]
top_nos_por_harmonica = sorted(centralidade_harmonica.items(), key=itemgetter(1), reverse=True)[:QUANTIDADE_TOP_PONTOS]

print("\n[TOP nós por betweenness]")
for id_no, pontuacao in top_nos_por_intermediacao[:10]:
    print(id_no, pontuacao)

# 10) Salvar CSV com top nós + coordenadas (para você usar em relatório e análises)
arquivo_csv_nos = "principais_nos.csv"
with open(arquivo_csv_nos, "w", newline="", encoding="utf-8") as arquivo_saida:
    escritor_csv = csv.writer(arquivo_saida)
    escritor_csv.writerow(["node", "lat", "lon", "degree_centrality", "betweenness", "harmonic"])
    # Vamos salvar o top por betweenness (mais “pontos críticos”)
    for id_no, _ in top_nos_por_intermediacao:
        latitude = grafo_conexo.nodes[id_no]["y"]
        longitude = grafo_conexo.nodes[id_no]["x"]
        escritor_csv.writerow([id_no, latitude, longitude, centralidade_grau[id_no], centralidade_intermediacao[id_no], centralidade_harmonica[id_no]])

print(f"\n[Etapa 6] CSV salvo: {arquivo_csv_nos}")

# 11) Rankear top arestas por edge betweenness
top_arestas_por_intermediacao = sorted(intermediacao_arestas.items(), key=itemgetter(1), reverse=True)[:QUANTIDADE_TOP_PONTOS]
arquivo_csv_arestas = "principais_arestas.csv"
with open(arquivo_csv_arestas, "w", newline="", encoding="utf-8") as arquivo_saida:
    escritor_csv = csv.writer(arquivo_saida)
    escritor_csv.writerow(["u", "v", "edge_betweenness"])
    for (no_origem, no_destino), pontuacao in top_arestas_por_intermediacao:
        escritor_csv.writerow([no_origem, no_destino, pontuacao])

print(f"CSV salvo: {arquivo_csv_arestas}")

# 12) (Bônus útil) Visualizar top nós num mapa Folium
# Vamos marcar os TOP nós por betweenness
import folium

# centralizar no primeiro top nó
no_central = top_nos_por_intermediacao[0][0]
latitude_central = grafo_conexo.nodes[no_central]["y"]
longitude_central = grafo_conexo.nodes[no_central]["x"]
mapa = folium.Map(location=(latitude_central, longitude_central), zoom_start=13)

for id_no, pontuacao in top_nos_por_intermediacao:
    latitude = grafo_conexo.nodes[id_no]["y"]
    longitude = grafo_conexo.nodes[id_no]["x"]
    # raio proporcional (apenas para visualização)
    raio = 4 + 60 * pontuacao
    folium.CircleMarker(
        location=(latitude, longitude),
        radius=raio,
        popup=f"node={id_no}<br>betweenness={pontuacao:.6f}",
        fill=True
    ).add_to(mapa)

arquivo_html_mapa = "6_pontos_criticos.html"
mapa.save(arquivo_html_mapa)
print(f"\nMapa salvo: {arquivo_html_mapa}")
