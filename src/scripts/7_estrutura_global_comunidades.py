import csv
import math
import random
import statistics
from collections import Counter

import osmnx as ox
import networkx as nx

# Visualização (gráfico)
import matplotlib.pyplot as plt

# Visualização (mapa)
import folium


# =========================
# CONFIGURAÇÕES (autoexplicativas)
# =========================
ARQUIVO_GRAFO_ENTRADA = "campinas_drive_adicionado.graphml"

ARQUIVO_SAIDA_RESUMO_TXT = "9_resumo_metricas_estruturais.txt"
ARQUIVO_SAIDA_DISTRIBUICAO_GRAUS_CSV = "9_distribuicao_graus.csv"
ARQUIVO_SAIDA_GRAFICO_GRAUS_PNG = "9_distribuicao_graus.png"

# Métricas que podem ficar pesadas -> vamos aproximar com amostragem
SEMENTE_ALEATORIA = 42
AMOSTRAS_PARA_CAMINHOS = 30  # aumenta p/ melhor estimativa, mas fica mais lento

# Comunidades (modularidade) em grafo muito grande pode ser pesado.
# Estratégia: pegar um subgrafo “mais denso” por grau (nós com mais conexões).
GRAU_MINIMO_PARA_SUBGRAFO_COMUNIDADES = 4
LIMITE_MAXIMO_NOS_SUBGRAFO_COMUNIDADES = 15000

ARQUIVO_SAIDA_COMUNIDADES_CSV = "9_comunidades_resumo.csv"
ARQUIVO_SAIDA_MAPA_COMUNIDADES_HTML = "9_comunidades_mapa.html"

# Para o mapa não ficar gigantesco, vamos desenhar só alguns pontos
LIMITE_PONTOS_NO_MAPA = 2000
TOP_COMUNIDADES_PARA_DESENHAR = 8


# =========================
# FUNÇÕES AUXILIARES
# =========================
def construir_grafo_simples_nao_direcionado_com_menor_comprimento(grafo_multidigraph: nx.MultiDiGraph) -> nx.Graph:
    """
    Converte o grafo viário (MultiDiGraph dirigido, com múltiplas arestas) em um grafo simples NÃO-direcionado (Graph).
    Se houver múltiplas arestas entre os mesmos nós, guardamos a menor 'length' (em metros).

    Por que isso?
    - Muitas métricas (clustering, assortatividade, comunidades) são mais “clássicas” em grafos simples/undirected.
    - Para não perder a noção de distância, mantemos 'length' como o menor comprimento entre pares (u,v).
    """
    grafo_simples = nx.Graph()

    # Mantém nós com atributos (x, y etc.)
    grafo_simples.add_nodes_from(grafo_multidigraph.nodes(data=True))

    # Para cada aresta dirigida (u -> v), adicionamos como não dirigida (u -- v)
    for no_u, no_v, dados_aresta in grafo_multidigraph.edges(data=True):
        comprimento_m = float(dados_aresta.get("length", 1.0))

        if grafo_simples.has_edge(no_u, no_v):
            # Se já existe, mantemos a menor distância
            if comprimento_m < float(grafo_simples[no_u][no_v].get("length", math.inf)):
                grafo_simples[no_u][no_v]["length"] = comprimento_m
        else:
            grafo_simples.add_edge(no_u, no_v, length=comprimento_m)

    return grafo_simples


def pegar_maior_componente_conexa(grafo_nao_direcionado: nx.Graph) -> nx.Graph:
    """
    Em redes viárias, é comum existir mais de um componente (ex.: vias desconectadas, ilhas, etc.).
    Para métricas globais, normalmente usamos a maior componente conectada.
    """
    if nx.is_connected(grafo_nao_direcionado):
        return grafo_nao_direcionado

    nos_maior_componente = max(nx.connected_components(grafo_nao_direcionado), key=len)
    return grafo_nao_direcionado.subgraph(nos_maior_componente).copy()


# =========================
# PIPELINE PRINCIPAL
# =========================
def main():
    random.seed(SEMENTE_ALEATORIA)

    # 1) Carregar grafo viário
    grafo_viario_dirigido = ox.load_graphml(ARQUIVO_GRAFO_ENTRADA)
    print(f"[Etapa 9] Grafo carregado: {ARQUIVO_GRAFO_ENTRADA}")
    print("Tipo:", type(grafo_viario_dirigido))
    print("Nós:", grafo_viario_dirigido.number_of_nodes(), "| Arestas:", grafo_viario_dirigido.number_of_edges())

    # 2) Transformar em grafo simples não-direcionado (mantendo o menor length por par)
    grafo_simples = construir_grafo_simples_nao_direcionado_com_menor_comprimento(grafo_viario_dirigido)
    print("\n[Etapa 9] Convertido para grafo simples não-direcionado.")
    print("Nós:", grafo_simples.number_of_nodes(), "| Arestas:", grafo_simples.number_of_edges())

    # 3) Usar a maior componente conectada
    grafo_analise = pegar_maior_componente_conexa(grafo_simples)
    print("\n[Etapa 9] Maior componente conectada selecionada.")
    print("Nós:", grafo_analise.number_of_nodes(), "| Arestas:", grafo_analise.number_of_edges())

    total_nos = grafo_analise.number_of_nodes()
    total_arestas = grafo_analise.number_of_edges()

    # 4) Estatísticas básicas do grau
    graus_por_no = dict(grafo_analise.degree())
    lista_graus = list(graus_por_no.values())

    grau_min = min(lista_graus)
    grau_max = max(lista_graus)
    grau_medio = statistics.mean(lista_graus)
    grau_mediano = statistics.median(lista_graus)

    densidade = nx.density(grafo_analise)

    # 5) Distribuição de graus (CSV + gráfico)
    contagem_graus = Counter(lista_graus)  # {grau: quantidade_de_nos}
    graus_ordenados = sorted(contagem_graus.items(), key=lambda x: x[0])  # ordena por grau

    with open(ARQUIVO_SAIDA_DISTRIBUICAO_GRAUS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["grau", "quantidade_nos", "probabilidade"])
        for grau, quantidade in graus_ordenados:
            w.writerow([grau, quantidade, quantidade / total_nos])

    # Gráfico (log-log costuma ser útil em redes)
    graus_x = [g for g, _ in graus_ordenados]
    counts_y = [c for _, c in graus_ordenados]

    plt.figure()
    plt.loglog(graus_x, counts_y, marker="o", linestyle="None")
    plt.xlabel("Grau (k)")
    plt.ylabel("Quantidade de nós com grau k")
    plt.title("Distribuição de graus (log-log)")
    plt.savefig(ARQUIVO_SAIDA_GRAFICO_GRAUS_PNG, dpi=200, bbox_inches="tight")
    plt.close()

    # 6) Clustering (coeficiente de agrupamento)
    # - transitivity: “clustering global” (triângulos / triplas conectadas)
    # - average_clustering (aproximado): média local aproximada (mais leve)
    transitivity_global = nx.transitivity(grafo_analise)

    # Aproximação para não ficar pesado:
    # trials = quantos nós sorteados para estimar a média local
    trials_clustering = min(2000, total_nos)
    clustering_medio_aproximado = nx.approximation.average_clustering(
        grafo_analise, trials=trials_clustering, seed=SEMENTE_ALEATORIA
    )

    # 7) Assortatividade (correlação de grau: nós “altos” conectam em “altos”?)
    assortatividade_grau = nx.degree_assortativity_coefficient(grafo_analise)

    # 8) Comprimento médio de caminhos (aproximado por amostragem)
    amostras_reais = min(AMOSTRAS_PARA_CAMINHOS, total_nos)
    nos_amostrados = random.sample(list(grafo_analise.nodes()), k=amostras_reais)

    distancias_em_hops = []
    distancias_em_metros = []

    for no_origem in nos_amostrados:
        # Em "hops" (quantidade de arestas)
        comprimentos_hops = nx.single_source_shortest_path_length(grafo_analise, no_origem)
        distancias_em_hops.extend(d for d in comprimentos_hops.values() if d > 0)

        # Em metros (usa o atributo length)
        comprimentos_metros = nx.single_source_dijkstra_path_length(grafo_analise, no_origem, weight="length")
        distancias_em_metros.extend(d for d in comprimentos_metros.values() if d > 0)

    caminho_medio_hops_aprox = statistics.mean(distancias_em_hops) if distancias_em_hops else float("nan")
    caminho_medio_metros_aprox = statistics.mean(distancias_em_metros) if distancias_em_metros else float("nan")

    # 9) Diâmetro aproximado (em hops) — útil como noção de “tamanho topológico”
    diametro_aproximado_hops = nx.approximation.diameter(grafo_analise)

    # 10) Comunidades / modularidade (em subgrafo)
    # Pegamos nós com grau >= um limiar (evita rodar em grafo gigantesco completo)
    nos_candidatos = [no for no, g in graus_por_no.items() if g >= GRAU_MINIMO_PARA_SUBGRAFO_COMUNIDADES]

    # Se ficar enorme, limita pelos nós de maior grau
    if len(nos_candidatos) > LIMITE_MAXIMO_NOS_SUBGRAFO_COMUNIDADES:
        nos_ordenados_por_grau = sorted(graus_por_no.items(), key=lambda x: x[1], reverse=True)
        nos_candidatos = [no for no, _ in nos_ordenados_por_grau[:LIMITE_MAXIMO_NOS_SUBGRAFO_COMUNIDADES]]

    subgrafo_comunidades = grafo_analise.subgraph(nos_candidatos).copy()

    print("\n[Etapa 9] Subgrafo para comunidades:")
    print("Nós:", subgrafo_comunidades.number_of_nodes(), "| Arestas:", subgrafo_comunidades.number_of_edges())

    # Label propagation é bem mais leve para grafos grandes
    comunidades = list(nx.community.asyn_lpa_communities(subgrafo_comunidades, seed=SEMENTE_ALEATORIA))
    modularidade = nx.community.modularity(subgrafo_comunidades, comunidades)

    # 11) Salvar resumo das comunidades
    # Vamos ordenar por tamanho
    comunidades_ordenadas = sorted(comunidades, key=lambda c: len(c), reverse=True)

    with open(ARQUIVO_SAIDA_COMUNIDADES_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id_comunidade", "tamanho", "lat_centroide", "lon_centroide"])
        for idx, conjunto_nos in enumerate(comunidades_ordenadas):
            latitudes = []
            longitudes = []
            for no in conjunto_nos:
                latitudes.append(subgrafo_comunidades.nodes[no].get("y"))
                longitudes.append(subgrafo_comunidades.nodes[no].get("x"))
            lat_centroide = statistics.mean(latitudes)
            lon_centroide = statistics.mean(longitudes)
            w.writerow([idx, len(conjunto_nos), lat_centroide, lon_centroide])

    # 12) Criar um mapa Folium com uma amostra de pontos por comunidade (para não explodir)
    # Centro do mapa: centroide da maior comunidade
    maior_comunidade = comunidades_ordenadas[0]
    lat_centro = statistics.mean([subgrafo_comunidades.nodes[n]["y"] for n in maior_comunidade])
    lon_centro = statistics.mean([subgrafo_comunidades.nodes[n]["x"] for n in maior_comunidade])

    mapa = folium.Map(location=(lat_centro, lon_centro), zoom_start=12)

    paleta_cores = [
        "red", "blue", "green", "purple", "orange", "darkred", "cadetblue", "darkblue",
        "darkgreen", "pink", "gray", "black"
    ]

    # Vamos desenhar só as TOP comunidades (por tamanho)
    comunidades_para_desenhar = comunidades_ordenadas[:TOP_COMUNIDADES_PARA_DESENHAR]

    # Limite global de pontos no mapa
    pontos_restantes = LIMITE_PONTOS_NO_MAPA

    for idx, conjunto_nos in enumerate(comunidades_para_desenhar):
        if pontos_restantes <= 0:
            break

        cor = paleta_cores[idx % len(paleta_cores)]

        # Quantos pontos vamos pegar desta comunidade?
        # (proporcional ao tamanho, mas limitado)
        tamanho = len(conjunto_nos)
        max_desta_comunidade = max(50, int(LIMITE_PONTOS_NO_MAPA / TOP_COMUNIDADES_PARA_DESENHAR))
        quantidade_a_pegar = min(tamanho, max_desta_comunidade, pontos_restantes)

        nos_amostra = random.sample(list(conjunto_nos), k=quantidade_a_pegar)

        for no in nos_amostra:
            lat = subgrafo_comunidades.nodes[no]["y"]
            lon = subgrafo_comunidades.nodes[no]["x"]

            folium.CircleMarker(
                location=(lat, lon),
                radius=3,
                popup=f"comunidade={idx}<br>node={no}",
                color=cor,
                fill=True,
                fill_opacity=0.7
            ).add_to(mapa)

        pontos_restantes -= quantidade_a_pegar

    mapa.save(ARQUIVO_SAIDA_MAPA_COMUNIDADES_HTML)

    # 13) Salvar um resumo geral em TXT (bom para relatório)
    with open(ARQUIVO_SAIDA_RESUMO_TXT, "w", encoding="utf-8") as f:
        f.write("===== RESUMO MÉTRICAS ESTRUTURAIS (ETAPA 9) =====\n\n")
        f.write(f"Arquivo de entrada: {ARQUIVO_GRAFO_ENTRADA}\n")
        f.write(f"Nós (maior componente): {total_nos}\n")
        f.write(f"Arestas (maior componente): {total_arestas}\n\n")

        f.write("---- Estatísticas de grau ----\n")
        f.write(f"Grau mínimo: {grau_min}\n")
        f.write(f"Grau máximo: {grau_max}\n")
        f.write(f"Grau médio: {grau_medio:.4f}\n")
        f.write(f"Grau mediano: {grau_mediano}\n\n")

        f.write("---- Métricas globais ----\n")
        f.write(f"Densidade: {densidade:.8f}\n")
        f.write(f"Transitivity (clustering global): {transitivity_global:.8f}\n")
        f.write(f"Clustering médio aproximado (trials={trials_clustering}): {clustering_medio_aproximado:.8f}\n")
        f.write(f"Assortatividade de grau: {assortatividade_grau:.8f}\n\n")

        f.write("---- Caminhos (aproximado por amostragem) ----\n")
        f.write(f"Amostras para caminhos: {amostras_reais}\n")
        f.write(f"Comprimento médio em hops (aprox): {caminho_medio_hops_aprox:.4f}\n")
        f.write(f"Comprimento médio em metros (aprox): {caminho_medio_metros_aprox:.2f}\n")
        f.write(f"Diâmetro aproximado (hops): {diametro_aproximado_hops}\n\n")

        f.write("---- Comunidades / modularidade ----\n")
        f.write(f"Subgrafo comunidades - nós: {subgrafo_comunidades.number_of_nodes()}\n")
        f.write(f"Subgrafo comunidades - arestas: {subgrafo_comunidades.number_of_edges()}\n")
        f.write(f"Número de comunidades: {len(comunidades)}\n")
        f.write(f"Modularidade (partition do subgrafo): {modularidade:.6f}\n\n")

        f.write("Arquivos gerados:\n")
        f.write(f"- {ARQUIVO_SAIDA_RESUMO_TXT}\n")
        f.write(f"- {ARQUIVO_SAIDA_DISTRIBUICAO_GRAUS_CSV}\n")
        f.write(f"- {ARQUIVO_SAIDA_GRAFICO_GRAUS_PNG}\n")
        f.write(f"- {ARQUIVO_SAIDA_COMUNIDADES_CSV}\n")
        f.write(f"- {ARQUIVO_SAIDA_MAPA_COMUNIDADES_HTML}\n")

    print("\n[Etapa 9] Concluído! Arquivos gerados:")
    print("-", ARQUIVO_SAIDA_RESUMO_TXT)
    print("-", ARQUIVO_SAIDA_DISTRIBUICAO_GRAUS_CSV)
    print("-", ARQUIVO_SAIDA_GRAFICO_GRAUS_PNG)
    print("-", ARQUIVO_SAIDA_COMUNIDADES_CSV)
    print("-", ARQUIVO_SAIDA_MAPA_COMUNIDADES_HTML)


if __name__ == "__main__":
    main()