import osmnx as ox

#BAIXAR A REDE VIÁRIA DE CAMPINAS (OSMnx)

# Para rodar 
# python -m venv .venv
# source .venv/bin/activate
# pip install osmnx networkx

ox.settings.log_console = True      
ox.settings.use_cache = True        # cache local (não baixa tudo de novo à toa)
ox.settings.requests_timeout = 60   

# Definir um ponto central por latitude e longitude e definir o raio

# Coordenadas de Campinas
latitide_centro = -22.8278
longitude_centro = -47.0792
dist_raio = 1000 # Definir o tamanho do raio de recorte

# Centro de Campinas:
# -22.9056, -47.0608

# Centro de barão Geraldo:
# -22.8278, -47.0792


# Baixa a rede viária e devolve um MultiDiGraph
G = ox.graph_from_point(
    (latitide_centro, longitude_centro), dist=dist_raio, network_type="drive", simplify=True
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