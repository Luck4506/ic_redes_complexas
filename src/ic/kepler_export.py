from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List

import osmnx as ox

from .io_utils import dataset_graph_path


def _ensure_kepler_dir(city_id: str) -> Path:
    out_dir = Path(f"outputs/{city_id}/kepler")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _copy_if_exists(src: str, dst: str) -> bool:
    s = Path(src)
    if not s.exists():
        return False
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(s, dst)
    return True


def _export_nodes_csv(gdf_nodes, out_csv: str) -> None:
    """Exporta nós (pontos) como CSV com colunas padrão que o Kepler entende."""

    cols = list(gdf_nodes.columns)

    # OSMnx normalmente fornece x (lon) e y (lat) nos nós
    optional = [c for c in ["street_count", "highway"] if c in cols]

    # Índice do GeoDataFrame costuma ser node_id
    gdf = gdf_nodes.copy()
    gdf["node_id"] = gdf.index.astype(int)

    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["node_id", "latitude", "longitude"] + optional
        w.writerow(header)

        for _, row in gdf.iterrows():
            lat = float(row["y"]) if "y" in row else None
            lon = float(row["x"]) if "x" in row else None
            line = [int(row["node_id"]), lat, lon]
            for c in optional:
                line.append(row.get(c))
            w.writerow(line)


def _export_edges_geojson(gdf_edges, out_geojson: str) -> None:
    """Exporta arestas (linhas) como GeoJSON compatível com Kepler.

    Motivos:
    - Kepler costuma falhar com GeoJSON muito grande e/ou com propriedades não-serializáveis.
    - O GeoDataFrame de arestas do OSMnx pode conter listas/dicts (ex.: highway, name),
      e também vem com MultiIndex (u, v, key).

    Estratégia:
    - reset_index() para transformar u/v/key em colunas
    - manter apenas um subconjunto de colunas úteis
    - converter listas/dicts/tuplas/set para string
    - garantir EPSG:4326
    - simplificar geometria para reduzir tamanho (mantendo a topologia)
    """

    Path(out_geojson).parent.mkdir(parents=True, exist_ok=True)

    # Remove MultiIndex e vira colunas normais u,v,key
    gdf = gdf_edges.reset_index()

    # Mantém apenas propriedades simples e úteis (evita campos problemáticos)
    keep = ["u", "v", "key", "length", "highway", "name", "oneway", "maxspeed", "geometry"]
    cols = [c for c in keep if c in gdf.columns]
    gdf = gdf[cols].copy()

    # Converte valores complexos (listas/dicts/tuplas) em string
    def _safe(v):
        if isinstance(v, (list, dict, tuple, set)):
            return str(v)
        return v

    for c in gdf.columns:
        if c == "geometry":
            continue
        gdf[c] = gdf[c].apply(_safe)

    # Remove geometrias nulas
    if "geometry" in gdf.columns:
        gdf = gdf[gdf["geometry"].notna()].copy()

    # Kepler funciona melhor com EPSG:4326
    try:
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        elif str(gdf.crs).lower() != "epsg:4326":
            gdf = gdf.to_crs("EPSG:4326")
    except Exception:
        pass

    # Simplificação geométrica para reduzir tamanho (73MB -> geralmente cai bastante)
    # Se ainda ficar grande, aumente para 0.0004.
    try:
        gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.0002, preserve_topology=True)
    except Exception:
        pass

    gdf.to_file(out_geojson, driver="GeoJSON")


def _export_route_geojson(city_id: str, G, out_geojson: str) -> bool:
    """Se existir o JSON de rota (E4), exporta a rota como GeoJSON LineString."""

    route_json = Path(f"outputs/{city_id}/metrics/rota_distancia.json")
    if not route_json.exists():
        return False

    data = json.loads(route_json.read_text(encoding="utf-8"))
    route_nodes: List[int] = data.get("route_nodes", [])
    if not route_nodes or len(route_nodes) < 2:
        return False

    coords = [(float(G.nodes[n]["x"]), float(G.nodes[n]["y"])) for n in route_nodes]  # (lon, lat)

    feature = {
        "type": "Feature",
        "properties": {"city_id": city_id, "type": "route"},
        "geometry": {"type": "LineString", "coordinates": coords},
    }
    fc = {"type": "FeatureCollection", "features": [feature]}

    Path(out_geojson).parent.mkdir(parents=True, exist_ok=True)
    Path(out_geojson).write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def exportar_para_kepler(city_id: str, which: str = "clean") -> Dict[str, Any]:
    """Exporta arquivos (GeoJSON/CSV) para abrir no Kepler.gl."""

    if which not in {"raw", "clean"}:
        raise ValueError("which deve ser 'raw' ou 'clean'.")

    out_dir = _ensure_kepler_dir(city_id)

    graph_path = str(dataset_graph_path(city_id, which))
    G = ox.load_graphml(graph_path)

    # Converter grafo em GeoDataFrames
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)

    edges_geojson = str(out_dir / f"edges_{city_id}_{which}.geojson")
    nodes_csv = str(out_dir / f"nodes_{city_id}_{which}.csv")
    route_geojson = str(out_dir / f"route_{city_id}.geojson")

    _export_edges_geojson(gdf_edges, edges_geojson)
    _export_nodes_csv(gdf_nodes, nodes_csv)

    # Copiar resultados de E5/E6 se existirem
    copied_top_nodes = _copy_if_exists(
        f"outputs/{city_id}/metrics/top_nodes.csv",
        str(out_dir / "top_nodes.csv"),
    )
    copied_nodes_communities = _copy_if_exists(
        f"outputs/{city_id}/metrics/nodes_communities.csv",
        str(out_dir / "nodes_communities.csv"),
    )
    copied_comm_summary = _copy_if_exists(
        f"outputs/{city_id}/metrics/community_summary.csv",
        str(out_dir / "community_summary.csv"),
    )

    has_route = _export_route_geojson(city_id, G, route_geojson)

    return {
        "kepler_dir": str(out_dir),
        "graph_path": graph_path,
        "edges_geojson": edges_geojson,
        "nodes_csv": nodes_csv,
        "top_nodes_csv": str(out_dir / "top_nodes.csv") if copied_top_nodes else None,
        "nodes_communities_csv": str(out_dir / "nodes_communities.csv") if copied_nodes_communities else None,
        "community_summary_csv": str(out_dir / "community_summary.csv") if copied_comm_summary else None,
        "route_geojson": route_geojson if has_route else None,
    }
