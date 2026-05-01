from __future__ import annotations

import inspect
from datetime import date, datetime
from typing import Any, Dict

import osmnx as ox
import yaml

from .io_utils import dataset_id_for_year, ensure_city_dirs, now_iso, save_graphml, save_json, year_to_historical_date


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

        G = _graph_from_bbox(
            north=north,
            south=south,
            east=east,
            west=west,
            network_type=network_type,
            simplify=simplify,
            retain_all=True,
            truncate_by_edge=True,
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
            truncate_by_edge=True,
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
    }
    save_json(meta_path, metadata)

    return {"graph_path": graph_path, "meta_path": meta_path, **metadata}
