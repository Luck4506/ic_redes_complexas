from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from datetime import date, datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict

import networkx as nx
import osmnx as ox
from osmnx import distance as ox_distance
from osmnx import graph as ox_graph
from osmnx import settings as ox_settings
import yaml

from .io_utils import (
    ensure_city_dirs,
    now_iso,
    resolve_dataset_id,
    save_graphml,
    save_json,
    year_to_historical_date,
)


_DEFAULT_OVERPASS_SETTINGS = "[out:json][timeout:{timeout}]{maxsize}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _serializable_deterministic(value: Any) -> Any:
    """Converte valores do YAML/GeoPandas para JSON com ordenação estável."""

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    if isinstance(value, Mapping):
        return {
            str(key): _serializable_deterministic(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple)):
        return [_serializable_deterministic(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_serializable_deterministic(item) for item in sorted(value, key=str)]

    # Escalares NumPy/Pandas aparecem nos identificadores retornados pelo
    # geocodificador, mas não são aceitos diretamente por json.dump.
    scalar = getattr(value, "item", None)
    if callable(scalar):
        try:
            return _serializable_deterministic(scalar())
        except (TypeError, ValueError):
            pass
    return str(value)


def _osmnx_version() -> str | None:
    version = getattr(ox, "__version__", None)
    if version not in (None, ""):
        return str(version)
    try:
        return importlib_metadata.version("osmnx")
    except importlib_metadata.PackageNotFoundError:
        return None


def _first_column_value(frame: Any, column: str) -> Any:
    try:
        if column not in frame.columns:
            return None
        values = frame[column]
    except (AttributeError, KeyError, TypeError):
        return None

    try:
        iterator = iter(values)
    except TypeError:
        iterator = iter((values,))
    for value in iterator:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, float) and math.isnan(value):
            continue
        return _serializable_deterministic(value)
    return None


def _osm_boundary_identity(place_gdf: Any | None) -> dict[str, Any]:
    element_type = _first_column_value(place_gdf, "osm_type") if place_gdf is not None else None
    osm_id = _first_column_value(place_gdf, "osm_id") if place_gdf is not None else None

    # Algumas versões/fontes representam (tipo, id) no índice em vez de
    # expor ambas as colunas.
    if place_gdf is not None and (element_type is None or osm_id is None):
        try:
            first_index = next(iter(place_gdf.index))
        except (AttributeError, StopIteration, TypeError):
            first_index = None
        if isinstance(first_index, tuple) and len(first_index) >= 2:
            index_type = str(first_index[0]).lower()
            if index_type in {"node", "way", "relation"}:
                element_type = element_type or index_type
                osm_id = osm_id if osm_id is not None else _serializable_deterministic(first_index[1])

    if element_type is not None:
        element_type = str(element_type).lower()
    relation_id = osm_id if element_type == "relation" else None
    return {
        "available": osm_id is not None,
        "element_type": element_type,
        "osm_id": osm_id,
        "relation_id": relation_id,
    }


def _boundary_geometry_sha256(place_gdf: Any | None) -> str | None:
    if place_gdf is None:
        return None
    try:
        geometries = list(place_gdf.geometry)
    except (AttributeError, TypeError):
        return None

    canonical_wkb: list[bytes] = []
    for geometry in geometries:
        if geometry is None or getattr(geometry, "is_empty", False) is True:
            continue
        normalized = geometry
        normalize = getattr(geometry, "normalize", None)
        if callable(normalize):
            try:
                normalized_candidate = normalize()
                if normalized_candidate is not None:
                    normalized = normalized_candidate
            except (AttributeError, TypeError, ValueError):
                normalized = geometry
        try:
            canonical_wkb.append(bytes(normalized.wkb))
        except (AttributeError, TypeError, ValueError):
            continue

    if not canonical_wkb:
        return None

    digest = hashlib.sha256()
    for payload in sorted(canonical_wkb):
        digest.update(len(payload).to_bytes(8, byteorder="big", signed=False))
        digest.update(payload)
    return digest.hexdigest()


def _boundary_identity_sha256(
    clip_config: Mapping[str, Any],
    geometry_sha256: str | None,
) -> tuple[str | None, str | None]:
    """Fingerprint the effective spatial unit for every supported clip mode."""
    mode = str(clip_config.get("mode") or "")
    if mode == "place":
        return geometry_sha256, "normalized_boundary_wkb" if geometry_sha256 else None
    keys = {
        "bbox": ("north", "south", "east", "west"),
        "radius": ("lat", "lon", "dist_meters"),
    }.get(mode)
    if keys is None:
        return None, None
    canonical = {
        "schema": "osm-clip-identity-v1",
        "mode": mode,
        **{key: _serializable_deterministic(clip_config.get(key)) for key in keys},
    }
    payload = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest(), "canonical_clip_parameters"


def _resolved_configuration(
    cfg: Mapping[str, Any],
    *,
    city_id: str,
    dataset_id: str,
    network_type: str,
    simplify: bool,
    historical_date: str | None,
    clip_mode: str,
    clip_config: Mapping[str, Any],
    overpass_cfg: Mapping[str, Any],
    overpass_settings: str,
) -> dict[str, Any]:
    resolved = dict(_serializable_deterministic(cfg))
    resolved.update(
        {
            "city_id": city_id,
            "dataset_id": dataset_id,
            "network_type": network_type,
            "simplify": simplify,
            "historical_date": historical_date,
            "clip_mode": clip_mode,
            "clip": dict(clip_config),
        }
    )
    if clip_mode == "bbox":
        resolved["bbox"] = {
            key: clip_config[key] for key in ("north", "south", "east", "west")
        }
    elif clip_mode == "radius":
        resolved["center"] = {key: clip_config[key] for key in ("lat", "lon")}
        resolved["dist_meters"] = clip_config["dist_meters"]
    elif clip_mode == "place":
        resolved["place_query"] = clip_config["query"]
    resolved_overpass = dict(_serializable_deterministic(overpass_cfg))
    resolved_overpass.update(
        {
            "use_cache": bool(overpass_cfg.get("use_cache", True)),
            "cache_folder": _serializable_deterministic(
                overpass_cfg.get("cache_folder", "data/cache")
            ),
            "settings": str(overpass_cfg.get("settings", _DEFAULT_OVERPASS_SETTINGS)),
            "effective_settings": overpass_settings,
        }
    )
    resolved["overpass"] = resolved_overpass
    return dict(_serializable_deterministic(resolved))


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

    base_settings = overpass_cfg.get("settings", _DEFAULT_OVERPASS_SETTINGS)
    if historical_date is None:
        ox.settings.overpass_settings = base_settings
        return base_settings

    timestamp = f'{historical_date}T00:00:00Z'
    historical_settings = f'{base_settings}[date:"{timestamp}"]'
    ox.settings.overpass_settings = historical_settings
    return historical_settings


def download_from_config(config_path: str, year: int | str | None = None) -> Dict[str, Any]:
    config_file = Path(config_path)
    config_bytes = config_file.read_bytes()
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    cfg_loaded = yaml.safe_load(config_bytes.decode("utf-8"))
    if not isinstance(cfg_loaded, Mapping):
        raise ValueError("A configuração YAML deve ser um objeto com chaves e valores.")
    cfg = dict(cfg_loaded)

    city_id = str(cfg["city_id"])

    network_type = str(cfg.get("network_type", "drive"))
    simplify = bool(cfg.get("simplify", True))
    historical_date = (
        year_to_historical_date(year)
        if year not in (None, "")
        else _parse_historical_date(cfg.get("historical_date"))
    )
    dataset_id = resolve_dataset_id(
        city_id,
        configured_dataset_id=(
            str(cfg["dataset_id"])
            if cfg.get("dataset_id") not in (None, "")
            else None
        ),
        historical_date=historical_date,
        year=year,
    )

    ensure_city_dirs(dataset_id)

    overpass_value = cfg.get("overpass", {})
    if not isinstance(overpass_value, Mapping):
        raise ValueError("A seção 'overpass' da configuração deve ser um objeto.")
    overpass_cfg = dict(overpass_value)
    overpass_settings = _configure_overpass(overpass_cfg, historical_date)

    clip_mode = str(cfg.get("clip_mode", "bbox"))
    place_gdf = None
    boundary_crs = None
    clip_config: dict[str, Any]
    query_started_at_utc = _utc_now_iso()

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
        clip_config = {
            "mode": "bbox",
            "north": north,
            "south": south,
            "east": east,
            "west": west,
        }
        clip_info = dict(clip_config)

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
        clip_config = {"mode": "radius", "lat": lat, "lon": lon, "dist_meters": dist}
        clip_info = dict(clip_config)

    elif clip_mode == "place":
        place_query = str(cfg["place_query"])
        place_gdf = ox.geocode_to_gdf(place_query)
        area_km2 = float(ox.projection.project_gdf(place_gdf).geometry.area.sum() / 1_000_000)
        G = ox.graph_from_place(
            place_query,
            network_type=network_type,
            simplify=simplify,
            retain_all=True,
            truncate_by_edge=False,
        )
        clip_config = {"mode": "place", "query": place_query}
        clip_info = {
            **clip_config,
            "boundary": "administrative",
            "area_km2": area_km2,
        }
        place_crs = getattr(place_gdf, "crs", None)
        boundary_crs = str(place_crs) if place_crs is not None else None

    else:
        raise ValueError("clip_mode inválido. Use bbox, radius ou place.")

    query_finished_at_utc = _utc_now_iso()
    boundary_geometry_sha256 = _boundary_geometry_sha256(place_gdf)
    boundary_identity_sha256, boundary_identity_kind = _boundary_identity_sha256(
        clip_config,
        boundary_geometry_sha256,
    )
    osm_boundary = _osm_boundary_identity(place_gdf)
    clip_info.update(
        {
            "boundary_geometry_sha256": boundary_geometry_sha256,
            "boundary_geometry_hash_format": (
                "sha256:sorted-length-prefixed-normalized-wkb"
                if boundary_geometry_sha256 is not None
                else None
            ),
            "boundary_identity_sha256": boundary_identity_sha256,
            "boundary_identity_kind": boundary_identity_kind,
            "boundary_crs": boundary_crs,
            "osm_boundary": osm_boundary,
        }
    )

    resolved_config = _resolved_configuration(
        cfg,
        city_id=city_id,
        dataset_id=dataset_id,
        network_type=network_type,
        simplify=simplify,
        historical_date=historical_date,
        clip_mode=clip_mode,
        clip_config=clip_config,
        overpass_cfg=overpass_cfg,
        overpass_settings=overpass_settings,
    )

    graph_path = f"data/graphs/{dataset_id}_{network_type}_raw.graphml"
    meta_path = f"data/metadata/{dataset_id}_{network_type}_raw.json"

    save_graphml(G, graph_path)

    metadata = {
        "city_id": city_id,
        "dataset_id": dataset_id,
        "created_at": now_iso(),
        "query_started_at_utc": query_started_at_utc,
        "query_finished_at_utc": query_finished_at_utc,
        "snapshot_mode": "historical" if historical_date is not None else "live_unfrozen",
        "snapshot_frozen": historical_date is not None,
        "snapshot_timestamp_utc": (
            f"{historical_date}T00:00:00Z" if historical_date is not None else None
        ),
        "snapshot_notice": (
            None
            if historical_date is not None
            else "Consulta ao estado atual do OSM; os dados não constituem um snapshot congelado."
        ),
        "network_type": network_type,
        "simplify": simplify,
        "historical_date": historical_date,
        "config_path": config_file.as_posix(),
        "config_sha256": config_sha256,
        "config_size_bytes": len(config_bytes),
        "resolved_config": resolved_config,
        "overpass_settings": overpass_settings,
        "clip": clip_info,
        "boundary_geometry_sha256": boundary_geometry_sha256,
        "boundary_identity_sha256": boundary_identity_sha256,
        "boundary_identity_kind": boundary_identity_kind,
        "boundary_crs": boundary_crs,
        "osm_boundary": osm_boundary,
        "nodes": int(G.number_of_nodes()),
        "edges": int(G.number_of_edges()),
        "crs": str(G.graph.get("crs", "")),
        "osmnx_version": _osmnx_version(),
        "dropped_incomplete_historical_ways": int(
            G.graph.get("dropped_incomplete_historical_ways", 0)
        ),
    }
    save_json(meta_path, metadata)

    return {"graph_path": graph_path, "meta_path": meta_path, **metadata}
