from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import osmnx as ox


def ensure_city_dirs(city_id: str) -> None:
    Path("config").mkdir(parents=True, exist_ok=True)
    Path("data/graphs").mkdir(parents=True, exist_ok=True)
    Path("data/metadata").mkdir(parents=True, exist_ok=True)
    Path("data/cache").mkdir(parents=True, exist_ok=True)

    Path(f"outputs/{city_id}/metrics").mkdir(parents=True, exist_ok=True)
    Path(f"outputs/{city_id}/figures").mkdir(parents=True, exist_ok=True)
    Path(f"outputs/{city_id}/maps").mkdir(parents=True, exist_ok=True)
    Path(f"outputs/{city_id}/logs").mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def year_to_historical_date(year: int | str | None) -> str | None:
    if year in (None, ""):
        return None

    try:
        year_int = int(year)
    except (TypeError, ValueError) as exc:
        raise ValueError("--year deve ser um ano com 4 dígitos, ex.: 2021.") from exc

    if year_int < 1900 or year_int > datetime.now().year:
        raise ValueError(f"--year deve estar entre 1900 e {datetime.now().year}.")

    return f"{year_int:04d}-01-01"


def dataset_id_for_year(city_id: str, year: int | str | None) -> str:
    if year in (None, ""):
        return city_id

    historical_date = year_to_historical_date(year)
    return f"{city_id}_{historical_date[:4]}"


def resolve_dataset_id(
    city_id: str,
    *,
    configured_dataset_id: str | None = None,
    historical_date: str | None = None,
    year: int | str | None = None,
) -> str:
    """Resolve o identificador exatamente como a aquisição de dados.

    ``--year`` tem precedência e usa a cidade-base, inclusive quando o YAML
    declara um ``dataset_id`` customizado. Sem ``--year``, um ``dataset_id``
    explícito é preservado; a data completa só é anexada quando não existe
    identificador customizado.
    """
    city = str(city_id).strip()
    if not city:
        raise ValueError("city_id não pode ser vazio.")
    if year not in (None, ""):
        return dataset_id_for_year(city, year)
    if configured_dataset_id not in (None, ""):
        return str(configured_dataset_id).strip()
    if historical_date not in (None, ""):
        return f"{city}_{str(historical_date).strip()}"
    return city


def infer_dataset_network_type(
    dataset_id: str,
    *,
    project_root: str | Path = ".",
) -> str:
    """Infer a dataset's network type from its unique metadata/graph family.

    Legacy datasets without discoverable evidence default to ``drive``. More
    than one family is rejected instead of silently selecting the wrong graph.
    """
    root = Path(project_root)
    candidates: set[str] = set()
    metadata_dir = root / "data" / "metadata"
    for path in sorted(metadata_dir.glob(f"{dataset_id}_*_raw.json")):
        prefix = f"{dataset_id}_"
        suffix = "_raw.json"
        filename_type = path.name[len(prefix) : -len(suffix)]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            payload = {}
        declared = payload.get("network_type") if isinstance(payload, dict) else None
        candidates.add(str(declared or filename_type))
    graph_dir = root / "data" / "graphs"
    for path in sorted(graph_dir.glob(f"{dataset_id}_*_raw.graphml")):
        prefix = f"{dataset_id}_"
        suffix = "_raw.graphml"
        candidates.add(path.name[len(prefix) : -len(suffix)])
    candidates.discard("")
    if not candidates:
        return "drive"
    if len(candidates) > 1:
        raise ValueError(
            f"Dataset {dataset_id!r} possui múltiplos network_type: "
            + ", ".join(sorted(candidates))
        )
    return next(iter(candidates))


def dataset_graph_path(
    dataset_id: str,
    stage: str,
    *,
    network_type: str | None = None,
    project_root: str | Path = ".",
) -> Path:
    if stage not in {"raw", "clean"}:
        raise ValueError("stage deve ser 'raw' ou 'clean'.")
    selected_network = network_type or infer_dataset_network_type(
        dataset_id,
        project_root=project_root,
    )
    return Path(project_root) / "data" / "graphs" / f"{dataset_id}_{selected_network}_{stage}.graphml"


def dataset_metadata_path(
    dataset_id: str,
    stage: str = "raw",
    *,
    network_type: str | None = None,
    project_root: str | Path = ".",
) -> Path:
    if stage not in {"raw", "clean"}:
        raise ValueError("stage deve ser 'raw' ou 'clean'.")
    selected_network = network_type or infer_dataset_network_type(
        dataset_id,
        project_root=project_root,
    )
    return Path(project_root) / "data" / "metadata" / f"{dataset_id}_{selected_network}_{stage}.json"


def save_json(path: str, payload: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_graphml(G, path: str) -> None:
    # Compatível com OSMnx 2.x
    try:
        ox.save_graphml(G, path)
    except Exception:
        ox.io.save_graphml(G, path)


def load_graphml(path: str):
    try:
        return ox.load_graphml(path)
    except Exception:
        return ox.io.load_graphml(path)
