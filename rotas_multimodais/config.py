# config.py
# Ajuste aqui para mudar cidade, origem/destino e terminais.

PLACE_NAME = "Campinas, São Paulo, Brazil"
NETWORK_TYPE = "drive"

# Use coordenadas para evitar depender de geocoding (mais robusto).
# (lat, lon)
ORIGIN_COORDINATES = (-22.9056, -47.0608)
DESTINATION_COORDINATES = (-22.8945, -47.0417)

# “Carga” em TU (unidade de transbordo). Serve só para escalar o custo de transbordo.
CARGO_TU = 1.0

# Custos e emissões por km (didáticos).
ROAD_COST_REAIS_PER_KM = 3.0
ROAD_CO2E_KG_PER_KM = 0.18

RAIL_COST_REAIS_PER_KM = 1.6
RAIL_CO2E_KG_PER_KM = 0.06

WATER_COST_REAIS_PER_KM = 1.2
WATER_CO2E_KG_PER_KM = 0.04

# Custo de transbordo por TU (didático; você pode calibrar).
TRANSFER_COST_REAIS_PER_TU = 9.0

# Terminais sintéticos (nó “terminal” com lat/lon).
# Você pode posicionar próximos a polos logísticos reais que faça sentido no seu estudo.
TERMINALS = [
    {"name": "Terminal Norte", "lat": -22.86, "lon": -47.07},
    {"name": "Terminal Centro", "lat": -22.91, "lon": -47.06},
    {"name": "Terminal Sul", "lat": -22.95, "lon": -47.05},
]

# Conexões entre terminais (sintéticas) para cada modal.
RAIL_CONNECTIONS = [
    ("Terminal Norte", "Terminal Centro"),
    ("Terminal Centro", "Terminal Sul"),
]

WATER_CONNECTIONS = [
    ("Terminal Norte", "Terminal Sul"),
]

# Lambdas para “trade-off” (score = custo + lambda * emissões).
LAMBDA_VALUES = [0, 2, 5, 10, 20]

OUTPUT_DIR = "outputs"