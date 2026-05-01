from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict

import networkx as nx
import osmnx as ox
from osmnx import distance as ox_distance
from osmnx import graph as ox_graph
from osmnx import settings as ox_settings
import yaml

from .io_utils import dataset_id_for_year, ensure_city_dirs, now_iso, save_graphml, save_json, year_to_historical_date


def _create_graph_skipping_incomplete_paths(response_jsons, bidirectional: bool):
    nodes: dict[int, dict[str, Any]] = {}
    paths: dict[int, dict[str, Any]] = {}
    dropped_paths = 0

    for response_json in response_jsons:
        if ox_settings.cache_only_mode:
            continue
        nodes_temp, paths_temp = ox_graph._parse_nodes_paths(response_json)
        nodes.update(nodes_temp)
        paths.update(paths_temp)

    node_ids = set(nodes)
    complete_paths = {}
    for path_id, path in paths.items():
        path_nodes = path.get("nodes", [])
        if len(path_nodes) >= 2 and all(node_id in node_ids for node_id in path_nodes):
            complete_paths[path_id] = path
        else:
            dropped_paths += 1

    if not nodes and not complete_paths:
        raise ValueError("Nenhum dado OSM completo retornado para montar o grafo.")

    G = nx.MultiDiGraph(
        created_date=ox.utils.ts(),
        created_with="OSMnx with incomplete historical ways skipped",
        crs=ox_settings.default_crs,
    )
    G.add_nodes_from(nodes.items())
    ox_graph._add_paths(G, complete_paths.values(), bidirectional)
    G.graph["dropped_incomplete_historical_ways"] = dropped_paths

    if len(G.edges) > 0:
        G = ox_distance.add_edge_lengths(G)
    return G


def _graph_from_bbox_with_missing_node_fallback(
    north: float,
    south: float,
    east: float,
    west: float,
    **kwargs,
):
    original_create_graph = ox_graph._create_graph
    try:
        ox_graph._create_graph = _create_graph_skipping_incomplete_paths
        return _graph_from_bbox(north=north, south=south, east=east, west=west, **kwargs)
    finally:
        ox_graph._create_graph = original_create_graph


def _graph_from_bbox(north: float, south: float, east: float, west: float, **kwargs):
    """Baixa grafo por BBOX de forma compatível e segura.

    Para evitar inversão de latitude/longitude, tentamos primeiro chamar
    com argumentos nomeados (north/south/east/west). Se a versão do OSMnx
    não aceitar essa assinatura, usamos o parâmetro `bbox` no formato
    (west, south, east, north).
    """
    # 1) Preferência: chamada com keywords (evita inversão de lat/lon)
    try:
        return ox.graph_from_bbox(north=north, south=south, east=east, west=west, **kwargs)
    except TypeError:
        pass

    # 2) Fallback: versões que só aceitam bbox=...
    bbox = (west, south, east, north)
    return ox.graph_from_bbox(bbox=bbox, **kwargs)


def _download_graph_from_bbox(
    north: float,
    south: float,
    east: float,
    west: float,
    historical_date: str | None,
    **kwargs,
):
    try:
        return _graph_from_bbox(north=north, south=south, east=east, west=west, **kwargs)
    except ValueError as exc:
        if historical_date is None or "missing nodes" not in str(exc):
            raise
        return _graph_from_bbox_with_missing_node_fallback(
            north=north,
            south=south,
            east=east,
            west=west,
            **kwargs,
        )


def _parse_historical_date(value: Any) -> str | None:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        except ValueError as exc:
            raise ValueError("historical_date deve usar o formato YYYY-MM-DD.") from exc

    raise ValueError("historical_date deve usar o formato YYYY-MM-DD.")


def _configure_overpass(overpass_cfg: Dict[str, Any], historical_date: str | None) -> str:
    ox.settings.use_cache = bool(overpass_cfg.get("use_cache", True))
    ox.settings.cache_folder = overpass_cfg.get("cache_folder", "data/cache")
    ox.settings.log_console = True
    extra_tags = ["surface", "smoothness", "tracktype", "lit", "sidewalk"]
    for tag in extra_tags:
        if tag not in ox.settings.useful_tags_way:
            ox.settings.useful_tags_way.append(tag)

    base_settings = overpass_cfg.get("settings", "[out:json][timeout:{timeout}]{maxsize}")
    if historical_date is None:
        ox.settings.overpass_settings = base_settings
        return base_settings

    timestamp = f'{historical_date}T00:00:00Z'
    historical_settings = f'{base_settings}[date:"{timestamp}"]'
    ox.settings.overpass_settings = historical_settings
    return historical_settings


def download_from_config(config_path: str, year: int | str | None = None) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    city_id = cfg["city_id"]

    network_type = cfg.get("network_type", "drive")
    simplify = bool(cfg.get("simplify", True))
    historical_date = year_to_historical_date(year) if year not in (None, "") else _parse_historical_date(cfg.get("historical_date"))
    dataset_id = cfg.get("dataset_id") or city_id
    if year not in (None, ""):
        dataset_id = dataset_id_for_year(city_id, year)
    elif historical_date is not None and "dataset_id" not in cfg:
        dataset_id = f"{city_id}_{historical_date}"

    ensure_city_dirs(dataset_id)

    overpass_cfg = cfg.get("overpass", {})
    overpass_settings = _configure_overpass(overpass_cfg, historical_date)

    clip_mode = cfg.get("clip_mode", "bbox")

    if clip_mode == "bbox":
        b = cfg["bbox"]
        north = float(b["north"])
        south = float(b["south"])
        east = float(b["east"])
        west = float(b["west"])

        G = _download_graph_from_bbox(
            north=north,
            south=south,
            east=east,
            west=west,
            historical_date=historical_date,
            network_type=network_type,
            simplify=simplify,
            retain_all=True,
            truncate_by_edge=False,
        )
        clip_info = {"mode": "bbox", "north": north, "south": south, "east": east, "west": west}

    elif clip_mode == "radius":
        center = cfg["center"]
        lat = float(center["lat"])
        lon = float(center["lon"])
        dist = float(cfg["dist_meters"])

        G = ox.graph_from_point(
            (lat, lon),
            dist=dist,
            network_type=network_type,
            simplify=simplify,
            retain_all=True,
            truncate_by_edge=False,
        )
        clip_info = {"mode": "radius", "lat": lat, "lon": lon, "dist_meters": dist}

    else:
        raise ValueError("clip_mode inválido. Use bbox ou radius.")

    graph_path = f"data/graphs/{dataset_id}_{network_type}_raw.graphml"
    meta_path = f"data/metadata/{dataset_id}_{network_type}_raw.json"

    save_graphml(G, graph_path)

    metadata = {
        "city_id": city_id,
        "dataset_id": dataset_id,
        "created_at": now_iso(),
        "network_type": network_type,
        "simplify": simplify,
        "historical_date": historical_date,
        "overpass_settings": overpass_settings,
        "clip": clip_info,
        "nodes": int(G.number_of_nodes()),
        "edges": int(G.number_of_edges()),
        "crs": str(G.graph.get("crs", "")),
        "dropped_incomplete_historical_ways": int(G.graph.get("dropped_incomplete_historical_ways", 0)),
    }
    save_json(meta_path, metadata)

    return {"graph_path": graph_path, "meta_path": meta_path, **metadata}
