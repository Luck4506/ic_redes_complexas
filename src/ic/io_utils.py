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
