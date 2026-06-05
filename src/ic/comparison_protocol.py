from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


REQUIRED_METRICS = [
    "structural_metrics.csv",
    "node_centralities.csv",
    "functional_topology_correlations.csv",
    "approximation_validation.csv",
]


def _bbox_area_km2(clip: dict[str, Any]) -> float | None:
    if clip.get("area_km2") not in (None, ""):
        return float(clip["area_km2"])
    if clip.get("mode") != "bbox":
        return None
    north, south = float(clip["north"]), float(clip["south"])
    east, west = float(clip["east"]), float(clip["west"])
    mean_lat = math.radians((north + south) / 2.0)
    height = abs(north - south) * 111.32
    width = abs(east - west) * 111.32 * math.cos(mean_lat)
    return height * width


def auditar_comparabilidade(datasets: list[str], output_path: str | None = None) -> dict:
    rows = []
    for dataset in datasets:
        meta_path = Path(f"data/metadata/{dataset}_drive_raw.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        clip = meta.get("clip", {})
        missing = [
            name for name in REQUIRED_METRICS
            if not Path(f"outputs/{dataset}/metrics/{name}").exists()
        ]
        rows.append({
            "dataset": dataset,
            "historical_date": meta.get("historical_date") or "OSM_atual",
            "clip_mode": clip.get("mode", "desconhecido"),
            "clip_area_km2_approx": _bbox_area_km2(clip) or "",
            "raw_nodes": meta.get("nodes", ""),
            "raw_edges": meta.get("edges", ""),
            "required_outputs_complete": "sim" if not missing else "nao",
            "missing_required_outputs": ";".join(missing),
        })

    areas = [float(row["clip_area_km2_approx"]) for row in rows if row["clip_area_km2_approx"] != ""]
    dates = {row["historical_date"] for row in rows}
    modes = {row["clip_mode"] for row in rows}
    same_area = bool(areas) and max(areas) / min(areas) <= 1.10
    administrative_boundaries = modes == {"place"}
    complete = all(row["required_outputs_complete"] == "sim" for row in rows)
    status = "comparavel" if (same_area or administrative_boundaries) and len(dates) == 1 and len(modes) == 1 and complete else "exploratorio"
    for row in rows:
        row["comparison_status"] = status
        row["status_reason"] = (
            "protocolo mínimo atendido"
            if status == "comparavel"
            else "recortes/datas/cobertura experimental não equivalentes; não inferir padrões universais"
        )

    output_path = output_path or "outputs/comparisons/comparability_audit.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return {"audit_csv": output_path, "status": status, "rows": rows}
