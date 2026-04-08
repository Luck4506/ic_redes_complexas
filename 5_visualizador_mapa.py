import json
import osmnx as ox
import folium
# O Folium cria um arquivo .html com um mapa interativo (zoom, arrastar, camadas).
# Ele usa por baixo o Leaflet.js (JavaScript).


# VISUALIZAR O MAPA USANDO FOLIUM

#Carrega o grafo
G = ox.load_graphml("campinas_drive_adicionado.graphml")

# Carrega a rota salva
with open("rota_por_tempo.json", "r", encoding="utf-8") as f:
    rota = json.load(f)


# Obs: GraphML pode transformar IDs em string
no_exemplo = next(iter(G.nodes))
if isinstance(no_exemplo, str):
    rota = [str(n) for n in rota]
    print("Convertendo a rota para string (GraphML carregou nós como str).")


# Desenha a rota no Folium 
# Transformamos a rota (lista de nós) em uma lista de coordenadas (lat, lon)
rota_latlon = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in rota]

# Centraliza o mapa aproximadamente no meio da rota
mid_idx = len(rota_latlon) // 2
centro_latitude, centro_longitude = rota_latlon[mid_idx]

# Cria o mapa base
m = folium.Map(location=(centro_latitude, centro_longitude), zoom_start=13)

# Desenha a rota como uma linha
folium.PolyLine(rota_latlon, weight=5, opacity=0.8).add_to(m)

#Marca a origem e destino (não estético)
no_origem = rota[0]
no_destino = rota[-1]

origem_latatitude = G.nodes[no_origem]["y"]
origem_longitude = G.nodes[no_origem]["x"]
destino_latitude = G.nodes[no_destino]["y"]
destino_longitude = G.nodes[no_destino]["x"]

# Adiciona marcadores
folium.Marker(location=(origem_latatitude, origem_longitude), popup="Origem", icon=folium.Icon(icon="play", prefix="fa")
).add_to(m)

folium.Marker( location=(destino_latitude, destino_longitude), popup="Destino", icon=folium.Icon(icon="stop", prefix="fa")
).add_to(m)

# Salva o HTML
output_file = "rota_campinas_por_tempo.html"
m.save(output_file)

print(f"\nMapa salvo em: {output_file}")