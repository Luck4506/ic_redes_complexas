from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from .scientific_comparability import CONFIRMED, auditar_comparabilidade_cientifica


REQUIRED_METRICS = [
    "structural_metrics.csv",
    "node_centralities.csv",
    "functional_topology_correlations.csv",
    "approximation_validation.csv",
]

LEGACY_FIELDS = (
    "dataset",
    "historical_date",
    "clip_mode",
    "clip_area_km2_approx",
    "raw_nodes",
    "raw_edges",
    "required_outputs_complete",
    "missing_required_outputs",
    "comparison_status",
    "status_reason",
)


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


def _metadata_for_legacy_row(dataset: str, summary: dict[str, Any]) -> dict[str, Any]:
    metadata_value = summary.get("metadata_path")
    if metadata_value in (None, ""):
        network_type = str(summary.get("network_type") or "drive")
        metadata_path = Path(f"data/metadata/{dataset}_{network_type}_raw.json")
    else:
        metadata_path = Path(str(metadata_value))
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_legacy_comparison_csv(
    datasets: list[str],
    scientific_result: dict[str, Any],
    output_path: str,
) -> dict[str, Any]:
    """Write the former CSV shape without bypassing the scientific gate.

    ``comparison_status`` remains available to old readers, but it can become
    ``comparavel`` only when the fail-closed audit is fully confirmed.  The
    authoritative three-state result stays in ``scientific_result['state']``.
    """

    target = Path(output_path)
    scientific_csv = scientific_result.get("datasets_csv")
    if scientific_csv not in (None, "") and target.resolve() == Path(str(scientific_csv)).resolve():
        raise ValueError(
            "--output deve ser diferente do CSV científico para não sobrescrever a auditoria."
        )

    summaries = {
        str(row.get("dataset")): row
        for row in scientific_result.get("dataset_rows", [])
        if isinstance(row, dict) and row.get("dataset") not in (None, "")
    }
    scientific_state = str(scientific_result.get("state") or "nao_comprovada")
    legacy_status = "comparavel" if scientific_state == CONFIRMED else "exploratorio"
    if scientific_state == CONFIRMED:
        status_reason = "gate científico fail-closed confirmado"
    else:
        status_reason = (
            f"estado científico: {scientific_state}; não inferir comparabilidade universal"
        )

    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        summary = summaries.get(dataset, {})
        metadata = _metadata_for_legacy_row(dataset, summary)
        clip_value = metadata.get("clip", {})
        clip = clip_value if isinstance(clip_value, dict) else {}
        try:
            area = _bbox_area_km2(clip)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            area = None
        missing = [
            name
            for name in REQUIRED_METRICS
            if not Path(f"outputs/{dataset}/metrics/{name}").is_file()
        ]
        rows.append(
            {
                "dataset": dataset,
                "historical_date": metadata.get("historical_date") or "OSM_atual",
                "clip_mode": clip.get("mode", "desconhecido"),
                "clip_area_km2_approx": area if area is not None else "",
                "raw_nodes": metadata.get("nodes", ""),
                "raw_edges": metadata.get("edges", ""),
                "required_outputs_complete": "sim" if not missing else "nao",
                "missing_required_outputs": ";".join(missing),
                "comparison_status": legacy_status,
                "status_reason": status_reason,
            }
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEGACY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return {
        "path": str(target),
        "rows": rows,
        "legacy_status": legacy_status,
        "scientific_state": scientific_state,
    }


def auditar_comparabilidade(datasets: list[str], output_path: str | None = None) -> dict:
    """Compatibility facade for the fail-closed scientific audit.

    The former implementation treated a shared ``place`` clip and the label
    ``OSM_atual`` as proof of comparability.  That could turn missing evidence
    into a positive scientific claim.  Existing callers keep the compact
    return shape, while all decisions now come from the evidence-rich audit.
    """
    output_dir = str(Path(output_path).parent) if output_path else "outputs/comparisons"
    result = auditar_comparabilidade_cientifica(
        datasets,
        output_dir=output_dir,
        perfil="cientifico",
        snapshot_policy="same",
    )
    audit_csv = result["datasets_csv"]
    legacy_rows: list[dict[str, Any]] = []
    if output_path:
        legacy = write_legacy_comparison_csv(datasets, result, output_path)
        audit_csv = legacy["path"]
        legacy_rows = legacy["rows"]
    return {
        "audit_csv": audit_csv,
        "status": result["state"],
        "rows": result["dataset_rows"],
        "legacy_rows": legacy_rows,
        "criteria_csv": result["criteria_csv"],
        "pairs_csv": result["pairs_csv"],
        "report_txt": result["report_txt"],
        "scientific_datasets_csv": result["datasets_csv"],
    }


__all__ = [
    "LEGACY_FIELDS",
    "REQUIRED_METRICS",
    "auditar_comparabilidade",
    "write_legacy_comparison_csv",
]
