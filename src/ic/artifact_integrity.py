from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .io_utils import infer_dataset_network_type


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
DEFAULT_HASH_SIZE_LIMIT_BYTES: int | None = None
_HASH_CHUNK_SIZE = 1024 * 1024
_STATUS_PRIORITY = {PASS: 0, WARN: 1, FAIL: 2}
_DATASET_COLUMNS = ("dataset", "dataset_id", "city_id")


def _is_audit_control_path(relative: Path) -> bool:
    """Return whether a dataset-relative file is mutable runtime control state."""
    return (
        relative.parent == Path("metrics")
        and relative.name.startswith("artifact_integrity_audit")
        and relative.suffix == ".csv"
    ) or (
        relative.parent == Path("logs")
        and relative.name.startswith("artifact_integrity_report")
        and relative.suffix == ".txt"
    ) or (relative.parent == Path("logs") and relative.name == "cli_runs.jsonl")


def _audit_scope(stages: Sequence[str] | None, active_stages: Sequence[str]) -> tuple[str, str]:
    """Build a stable human label and filename suffix for an audit scope."""
    if stages is None:
        return "automatico", ""
    if not active_stages:
        return "manifesto", "__manifesto"
    if len(active_stages) == 1:
        return active_stages[0], f"__{active_stages[0]}"
    joined = "--".join(active_stages)
    if len(joined) <= 96:
        return ",".join(active_stages), f"__{joined}"
    digest = hashlib.sha256(",".join(active_stages).encode("utf-8")).hexdigest()[:12]
    return ",".join(active_stages), f"__subset_{digest}"


@dataclass(frozen=True)
class ArtifactSpec:
    relative_path: str
    scope: str = "output"
    required_columns: tuple[str, ...] = ()
    min_rows: int | None = None
    min_size_bytes: int = 1
    anchor: bool = False


@dataclass(frozen=True)
class StageContract:
    artifacts: tuple[ArtifactSpec, ...]
    dependencies: tuple[ArtifactSpec, ...] = ()
    commands: tuple[str, ...] = ()


@dataclass
class ManifestEntry:
    raw_path: str
    path: Path
    role: str
    sha256: str | None = None
    size_bytes: int | None = None
    size_value: Any = None
    mtime_ns: int | None = None
    mtime_ns_value: Any = None
    mtime_value: str | float | None = None


@dataclass
class CsvProfile:
    header: tuple[str, ...]
    row_count: int
    malformed_rows: int
    duplicate_columns: tuple[str, ...]
    dataset_values: dict[str, set[str]]
    error: str | None = None


def _out(
    path: str,
    columns: Sequence[str] = (),
    *,
    rows: int | None = None,
    anchor: bool = False,
) -> ArtifactSpec:
    return ArtifactSpec(path, "output", tuple(columns), rows, 1, anchor)


def _project(path: str, *, anchor: bool = False) -> ArtifactSpec:
    return ArtifactSpec(path, "project", (), None, 1, anchor)


_RAW_GRAPH = _project("data/graphs/{dataset}_{network_type}_raw.graphml", anchor=True)
_RAW_METADATA = ArtifactSpec(
    "data/metadata/{dataset}_{network_type}_raw.json", "project", (), None, 2, True
)
_CLEAN_GRAPH = _project("data/graphs/{dataset}_{network_type}_clean.graphml", anchor=True)


def _analysis_stage(
    *artifacts: ArtifactSpec,
    dependencies: Sequence[ArtifactSpec] = (),
    commands: Sequence[str] = (),
) -> StageContract:
    return StageContract(
        tuple(artifacts),
        (_CLEAN_GRAPH, *tuple(dependencies)),
        tuple(commands),
    )


STAGE_CONTRACTS: dict[str, StageContract] = {
    "download": StageContract((_RAW_GRAPH, _RAW_METADATA), commands=("download",)),
    "preprocess": StageContract(
        (
            _CLEAN_GRAPH,
            _out("logs/grafo_resumo.txt", anchor=True),
        ),
        (_RAW_GRAPH,),
        ("preprocess",),
    ),
    "structural": _analysis_stage(
        _out("metrics/structural_metrics.csv", ("metric", "value"), rows=1, anchor=True),
        _out("metrics/degree_distribution.csv", ("degree", "count", "probability"), rows=1),
        _out("figures/degree_distribution_loglog.png"),
        _out("logs/structural_report.txt"),
        commands=("structural",),
    ),
    "representation_audit": _analysis_stage(
        _out(
            "metrics/graph_representation_audit.csv",
            ("city_id", "dataset_stage", "representation", "nodes", "edges"),
            rows=8,
            anchor=True,
        ),
        _out(
            "metrics/representation_metric_sensitivity.csv",
            ("dataset_a", "representation_a", "dataset_b", "representation_b", "metric", "status"),
            rows=1,
        ),
        _out("logs/graph_representation_report.txt"),
        dependencies=(_RAW_GRAPH,),
        commands=("representation-audit",),
    ),
    "paths": _analysis_stage(
        _out(
            "metrics/rota_distancia_resumo.csv",
            ("city_id", "orig_node", "dest_node", "distance_total_m"),
            rows=1,
            anchor=True,
        ),
        _out("metrics/rota_distancia.json"),
        _out("maps/rota_distancia.html"),
        commands=("paths",),
    ),
    "centrality": _analysis_stage(
        _out(
            "metrics/node_centralities.csv",
            ("node", "lat", "lon", "degree_centrality", "betweenness"),
            rows=1,
            anchor=True,
        ),
        _out(
            "metrics/edge_centralities.csv",
            ("u", "v", "edge_betweenness"),
            rows=1,
        ),
        _out("metrics/centrality_rankings.csv", ("metric", "rank", "node", "value"), rows=1),
        _out("metrics/top_nodes.csv", ("node", "betweenness"), rows=1),
        _out("metrics/top_edges.csv", ("rank", "u", "v", "edge_betweenness"), rows=1),
        _out("logs/centrality_report.txt"),
        _out("maps/pontos_criticos.html"),
        _out("maps/arestas_criticas.html"),
        commands=("centrality",),
    ),
    "functional_relations": _analysis_stage(
        _out(
            "metrics/functional_topology_correlations.csv",
            ("attribute", "topology_metric", "observations", "spearman_correlation"),
            rows=1,
            anchor=True,
        ),
        _out(
            "metrics/functional_topology_groups.csv",
            ("attribute", "category", "edges"),
            rows=1,
        ),
        _out("logs/functional_topology_report.txt"),
        dependencies=(
            _out("metrics/node_centralities.csv"),
            _out("metrics/edge_centralities.csv"),
        ),
        commands=("functional-relations",),
    ),
    "approximation_validation": _analysis_stage(
        _out(
            "metrics/approximation_validation.csv",
            ("metric", "sample_size", "repeat", "runtime_seconds"),
            rows=1,
            anchor=True,
        ),
        _out("logs/approximation_validation_report.txt"),
        commands=("validate-approximations",),
    ),
    "communities": _analysis_stage(
        _out("metrics/nodes_communities.csv", ("node", "community_id"), rows=1, anchor=True),
        _out("metrics/community_summary.csv", ("community_id", "size"), rows=1),
        _out("logs/communities_report.txt"),
        _out("maps/comunidades.html"),
        commands=("communities",),
    ),
    "vulnerability_index": _analysis_stage(
        _out(
            "metrics/vulnerability_nodes.csv",
            ("rank", "node", "vulnerability_score"),
            rows=1,
            anchor=True,
        ),
        _out(
            "metrics/vulnerability_edges.csv",
            ("rank", "u", "v", "vulnerability_score", "edge_betweenness"),
            rows=1,
        ),
        _out("maps/vulnerability_nodes.html"),
        _out("maps/vulnerability_edges.html"),
        _out("logs/vulnerability_index_report.txt"),
        dependencies=(
            _out("metrics/node_centralities.csv"),
            _out("metrics/edge_centralities.csv"),
            _out("metrics/nodes_communities.csv"),
            _out("metrics/node_resilience_removed_targeted.csv"),
            _out("metrics/node_resilience_removed_targeted_adaptive.csv"),
        ),
        commands=("vulnerability-index",),
    ),
    "structural_bottlenecks": _analysis_stage(
        _out(
            "metrics/structural_bottlenecks.csv",
            ("rank", "type", "element", "bottleneck_score"),
            rows=0,
            anchor=True,
        ),
        _out("metrics/structural_articulations.csv", ("rank", "node"), rows=0),
        _out("metrics/structural_bridges.csv", ("rank", "u", "v", "edge_betweenness"), rows=0),
        _out("maps/structural_articulations.html"),
        _out("maps/structural_bridges.html"),
        _out("maps/structural_bottlenecks.html"),
        _out("logs/structural_bottlenecks_report.txt"),
        dependencies=(
            _out("metrics/node_centralities.csv"),
            _out("metrics/edge_centralities.csv"),
            _out("metrics/nodes_communities.csv"),
        ),
        commands=("structural-bottlenecks",),
    ),
    "route_redundancy": _analysis_stage(
        _out(
            "metrics/route_redundancy_pairs.csv",
            ("pair_id", "origin", "destination", "alternative_exists"),
            rows=1,
            anchor=True,
        ),
        _out("metrics/route_redundancy_summary.csv", ("metric", "value"), rows=1),
        _out("maps/route_redundancy.html"),
        _out("logs/route_redundancy_report.txt"),
        commands=("route-redundancy",),
    ),
    "spatial_multiscale": _analysis_stage(
        _out("metrics/spatial_multiscale_cells.csv", ("cell_id", "nodes"), rows=1, anchor=True),
        _out("metrics/spatial_multiscale_summary.csv", ("metric", "value"), rows=1),
        _out("maps/spatial_multiscale_vulnerability.html"),
        _out("maps/spatial_multiscale_connectivity.html"),
        _out("maps/spatial_multiscale_redundancy.html"),
        _out("logs/spatial_multiscale_report.txt"),
        commands=("spatial-multiscale",),
    ),
    "spatial_robustness": _analysis_stage(
        _out(
            "metrics/spatial_robustness_cells.csv",
            ("cell_id", "removed_edges", "lcc_fraction_after"),
            rows=1,
            anchor=True,
        ),
        _out("metrics/spatial_robustness_summary.csv", ("metric", "value"), rows=1),
        _out("maps/spatial_robustness_lcc_drop.html"),
        _out("maps/spatial_robustness_efficiency_drop.html"),
        _out("maps/spatial_robustness_fragmentation.html"),
        _out("logs/spatial_robustness_report.txt"),
        commands=("spatial-robustness",),
    ),
    "road_hierarchy": _analysis_stage(
        _out(
            "metrics/road_hierarchy_by_class.csv",
            ("road_class", "edge_count", "length_m"),
            rows=1,
            anchor=True,
        ),
        _out("metrics/road_hierarchy_summary.csv", ("metric", "value"), rows=1),
        _out("maps/road_hierarchy_impact.html"),
        _out("logs/road_hierarchy_report.txt"),
        commands=("road-hierarchy",),
    ),
    "urban_morphology": _analysis_stage(
        _out(
            "metrics/urban_morphology_cells.csv",
            ("cell_id", "nodes", "morphology_class"),
            rows=1,
            anchor=True,
        ),
        _out("metrics/urban_morphology_summary.csv", ("metric", "value"), rows=1),
        _out("maps/urban_morphology_classes.html"),
        _out("maps/urban_morphology_orientation_entropy.html"),
        _out("maps/urban_morphology_connectivity.html"),
        _out("logs/urban_morphology_report.txt"),
        commands=("urban-morphology",),
    ),
    "od_efficiency": _analysis_stage(
        _out(
            "metrics/od_efficiency_pairs.csv",
            ("pair_id", "origin", "destination", "route_distance_m"),
            rows=1,
            anchor=True,
        ),
        _out("metrics/od_efficiency_summary.csv", ("metric", "value"), rows=1),
        _out("maps/od_efficiency_routes.html"),
        _out("logs/od_efficiency_report.txt"),
        commands=("od-efficiency",),
    ),
    "subcenters": _analysis_stage(
        _out("metrics/subcenters_cells.csv", ("cell_id", "subcenter_score"), rows=1, anchor=True),
        _out("metrics/subcenters.csv", ("cell_id", "subcenter_score"), rows=0),
        _out("metrics/subcenters_summary.csv", ("metric", "value"), rows=1),
        _out("maps/subcenters.html"),
        _out("logs/subcenters_report.txt"),
        commands=("subcenters",),
    ),
    "urban_barriers": _analysis_stage(
        _out("metrics/urban_barriers_cells.csv", ("cell_id", "permeability_index"), rows=1, anchor=True),
        _out("metrics/urban_barriers_connections.csv", ("cell_a", "cell_b", "barrier_score"), rows=0),
        _out("metrics/urban_barriers_summary.csv", ("metric", "value"), rows=1),
        _out("maps/urban_barriers_permeability.html"),
        _out("maps/urban_barriers_connections.html"),
        _out("logs/urban_barriers_report.txt"),
        commands=("urban-barriers",),
    ),
    "network_scale_profile": _analysis_stage(
        _out("metrics/network_scale_profile_scales.csv", ("scale_m", "populated_cells"), rows=1, anchor=True),
        _out("metrics/network_scale_profile_cells.csv", ("scale_m", "cell_id"), rows=1),
        _out("metrics/network_scale_profile_stability.csv", ("metric", "stability_score"), rows=1),
        _out("metrics/network_scale_profile_summary.csv", ("metric", "value"), rows=1),
        _out("figures/network_scale_profile_metrics.png"),
        _out("figures/network_scale_profile_stability.png"),
        _out("maps/network_scale_profile_low_permeability.html"),
        _out("logs/network_scale_profile_report.txt"),
        commands=("network-scale-profile",),
    ),
    "robustness_summary": _analysis_stage(
        _out(
            "metrics/robustness_summary.csv",
            ("dataset", "modality", "strategy", "metric", "auc_normalized_mean"),
            rows=1,
            anchor=True,
        ),
        _out("figures/robustness_summary_auc.png"),
        _out("figures/robustness_summary_losses.png"),
        _out("logs/robustness_summary_report.txt"),
        commands=("robustness-summary",),
    ),
    "inventory": _analysis_stage(
        _out(
            "metrics/graph_inventory_summary.csv",
            ("grupo", "indicador", "valor", "unidade"),
            rows=1,
            anchor=True,
        ),
        _out("metrics/graph_inventory_highway.csv", ("categoria", "arestas"), rows=1),
        _out("metrics/graph_inventory_surface.csv", ("categoria", "arestas"), rows=1),
        _out("metrics/graph_inventory_maxspeed.csv", ("categoria", "arestas"), rows=1),
        _out("metrics/graph_inventory_lanes.csv", ("categoria", "arestas"), rows=1),
        _out("metrics/graph_inventory_oneway.csv", ("categoria", "arestas"), rows=1),
        _out("metrics/graph_inventory_degree.csv", ("grau", "nos"), rows=1),
        _out("logs/graph_inventory_report.txt"),
        commands=("inventory",),
    ),
    "dashboard": _analysis_stage(
        _out("dashboard_{dataset}.html", anchor=True),
        commands=("dashboard",),
    ),
    "report": _analysis_stage(
        _out("REPORT_{dataset}.md", anchor=True),
        _out("MANIFEST_{dataset}.txt"),
        _out("EXPERIMENT_MANIFEST_{dataset}.json"),
        commands=("report",),
    ),
    "plot_graphs": _analysis_stage(
        _out("figures/grafo_{dataset}_clean_ruas.png", anchor=True),
        _out("figures/grafo_{dataset}_clean_ruas_nos.png"),
        _out("figures/grafo_{dataset}_clean_comunidades.png"),
        commands=("plot-graphs",),
    ),
    "export_kepler": _analysis_stage(
        _out("kepler/edges_{dataset}_clean.geojson", anchor=True),
        _out("kepler/nodes_{dataset}_clean.csv", ("node_id", "latitude", "longitude"), rows=1),
        commands=("export-kepler",),
    ),
}


def _strategy_stage(prefix: str, strategy: str) -> StageContract:
    if prefix == "resilience":
        return _analysis_stage(
            _out(
                f"metrics/resilience_curve_{strategy}.csv",
                ("removed_edges", "removed_fraction", "lcc_fraction"),
                rows=2,
                anchor=True,
            ),
            _out(f"figures/resilience_curve_{strategy}.png"),
            _out(f"logs/resilience_report_{strategy}.txt"),
            commands=("resilience",),
        )
    if prefix == "node_resilience":
        return _analysis_stage(
            _out(
                f"metrics/node_resilience_curve_{strategy}.csv",
                ("removed_nodes", "removed_fraction", "lcc_fraction"),
                rows=2,
                anchor=True,
            ),
            _out(
                f"metrics/node_resilience_removed_{strategy}.csv",
                ("removal_rank", "step", "node"),
                rows=1,
            ),
            _out(f"figures/node_resilience_curve_{strategy}.png"),
            _out(f"logs/node_resilience_report_{strategy}.txt"),
            commands=("node-resilience",),
        )
    if prefix == "community_resilience":
        return _analysis_stage(
            _out(
                f"metrics/community_resilience_curve_{strategy}.csv",
                ("removed_edges", "removed_fraction", "lcc_nodes_fraction"),
                rows=2,
                anchor=True,
            ),
            _out("metrics/community_resilience_summary.csv", ("community_id", "size"), rows=1),
            _out(
                "metrics/community_resilience_top_edges.csv",
                ("source_community", "target_community", "edge_betweenness"),
                rows=1,
            ),
            _out(f"figures/community_resilience_curve_{strategy}.png"),
            _out(f"logs/community_resilience_report_{strategy}.txt"),
            dependencies=(_out("metrics/nodes_communities.csv"),),
            commands=("community-resilience",),
        )
    return _analysis_stage(
        _out(
            f"metrics/intra_community_resilience_curve_{strategy}.csv",
            ("community_id", "removed_edges", "removed_fraction", "lcc_fraction"),
            rows=2,
            anchor=True,
        ),
        _out(
            f"metrics/intra_community_resilience_summary_{strategy}.csv",
            ("community_id", "nodes", "resilience_auc_lcc"),
            rows=1,
        ),
        _out(f"figures/intra_community_resilience_{strategy}.png"),
        _out(f"logs/intra_community_resilience_report_{strategy}.txt"),
        dependencies=(_out("metrics/nodes_communities.csv"),),
        commands=("intra-community-resilience",),
    )


for _prefix in (
    "resilience",
    "node_resilience",
    "community_resilience",
    "intra_community_resilience",
):
    for _strategy in ("random", "targeted", "targeted_adaptive"):
        STAGE_CONTRACTS[f"{_prefix}_{_strategy}"] = _strategy_stage(_prefix, _strategy)


def _resolve_root(project_root: str | os.PathLike[str], path: str | os.PathLike[str]) -> Path:
    root = Path(project_root).expanduser().resolve()
    candidate = Path(path).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _resolve_spec(
    spec: ArtifactSpec,
    dataset: str,
    network_type: str,
    project_root: Path,
    output_root: Path,
) -> Path:
    rendered = spec.relative_path.format(dataset=dataset, network_type=network_type)
    if spec.scope == "project":
        return (project_root / rendered).resolve()
    return (output_root / dataset / rendered).resolve()


def _display_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())


def _manifest_path_value(value: Any) -> str | None:
    if isinstance(value, (str, os.PathLike)):
        text = os.fspath(value).strip()
        return text or None
    return None


def _extract_sha256(item: Mapping[str, Any]) -> str | None:
    value = item.get("sha256") or item.get("checksum_sha256")
    if value in (None, "") and isinstance(item.get("hash"), Mapping):
        hash_data = item["hash"]
        if str(hash_data.get("algorithm", "")).lower().replace("-", "") == "sha256":
            value = hash_data.get("value") or hash_data.get("digest")
    return str(value).strip().lower() if value not in (None, "") else None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) and value.is_integer() else None
    text = str(value).strip()
    return int(text) if re.fullmatch(r"[+-]?\d+", text) else None


def _resolve_manifest_artifact(
    raw_path: str,
    dataset: str,
    project_root: Path,
    output_root: Path,
) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    parts = candidate.parts
    if parts and parts[0] == "outputs":
        return output_root.joinpath(*parts[1:]).resolve()
    if parts and parts[0] in {"metrics", "logs", "figures", "maps", "kepler"}:
        return (output_root / dataset / candidate).resolve()
    if parts and parts[0] == dataset:
        return (output_root / candidate).resolve()
    return (project_root / candidate).resolve()


def _load_manifest(
    manifest: str | os.PathLike[str] | Mapping[str, Any] | None,
    project_root: Path,
) -> tuple[dict[str, Any], Path | None, str | None]:
    if manifest is None:
        return {}, None, None
    if isinstance(manifest, Mapping):
        return dict(manifest), None, None
    path = Path(manifest).expanduser()
    if not path.is_absolute():
        path = project_root / path
    path = path.resolve()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, path, f"manifesto nao pode ser lido: {exc}"
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return {}, path, f"JSON de manifesto invalido: {exc}"
        if not isinstance(payload, Mapping):
            return {}, path, "manifesto JSON deve conter um objeto no nivel superior"
        return dict(payload), path, None
    outputs = [line.strip() for line in text.splitlines() if line.strip()]
    return {"outputs": outputs, "outputs_complete": True}, path, None


def _infer_dataset(payload: Mapping[str, Any], manifest_path: Path | None) -> str | None:
    for key in ("dataset", "dataset_id", "city_id"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value).strip()
    datasets = payload.get("datasets")
    if isinstance(datasets, Sequence) and not isinstance(datasets, (str, bytes)):
        values = [str(value).strip() for value in datasets if str(value).strip()]
        if len(values) == 1:
            return values[0]
    if manifest_path is not None:
        match = re.match(r"(?:EXPERIMENT_)?MANIFEST_(.+?)(?:\.json|\.txt)?$", manifest_path.name)
        if match:
            return match.group(1)
    return None


def _validate_dataset(dataset: str) -> str:
    value = str(dataset).strip()
    if not value or value in {".", ".."} or Path(value).name != value:
        raise ValueError("dataset deve ser um identificador simples, sem separadores de caminho.")
    return value


def _iter_manifest_items(value: Any, role: str) -> list[tuple[str, Mapping[str, Any], str]]:
    items: list[tuple[str, Mapping[str, Any], str]] = []
    direct = _manifest_path_value(value)
    if direct is not None:
        items.append((direct, {}, role))
        return items
    if isinstance(value, Mapping):
        path_value = _manifest_path_value(value.get("path"))
        if path_value is not None:
            items.append((path_value, value, role))
            return items
        for key, nested in value.items():
            nested_path = _manifest_path_value(nested)
            if nested_path is not None:
                items.append((nested_path, {}, role))
            elif isinstance(nested, Mapping):
                nested_value = _manifest_path_value(nested.get("path"))
                if nested_value is not None:
                    items.append((nested_value, nested, role))
                elif "/" in str(key) or "\\" in str(key):
                    items.append((str(key), nested, role))
        return items
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            items.extend(_iter_manifest_items(nested, role))
    return items


def _manifest_entries(
    payload: Mapping[str, Any],
    dataset: str,
    project_root: Path,
    output_root: Path,
) -> list[ManifestEntry]:
    raw_items: list[tuple[str, Mapping[str, Any], str]] = []
    raw_items.extend(_iter_manifest_items(payload.get("inputs"), "input"))
    raw_items.extend(_iter_manifest_items(payload.get("outputs"), "output"))
    raw_items.extend(_iter_manifest_items(payload.get("artifacts"), "output"))
    raw_items.extend(_iter_manifest_items(payload.get("files"), "output"))

    entries: dict[tuple[Path, str], ManifestEntry] = {}
    for raw_path, metadata, role in raw_items:
        resolved = _resolve_manifest_artifact(raw_path, dataset, project_root, output_root)
        size_value = metadata.get("size_bytes", metadata.get("size"))
        mtime_ns_value = metadata.get("mtime_ns")
        entry = ManifestEntry(
            raw_path=raw_path,
            path=resolved,
            role=role,
            sha256=_extract_sha256(metadata),
            size_bytes=_optional_int(size_value),
            size_value=size_value,
            mtime_ns=_optional_int(mtime_ns_value),
            mtime_ns_value=mtime_ns_value,
            mtime_value=metadata.get("mtime_utc", metadata.get("mtime")),
        )
        key = (resolved, role)
        previous = entries.get(key)
        if previous is None:
            entries[key] = entry
        else:
            previous.sha256 = previous.sha256 or entry.sha256
            previous.size_bytes = previous.size_bytes if previous.size_bytes is not None else entry.size_bytes
            previous.size_value = (
                previous.size_value if previous.size_value not in (None, "") else entry.size_value
            )
            previous.mtime_ns = previous.mtime_ns if previous.mtime_ns is not None else entry.mtime_ns
            previous.mtime_ns_value = (
                previous.mtime_ns_value
                if previous.mtime_ns_value not in (None, "")
                else entry.mtime_ns_value
            )
            previous.mtime_value = previous.mtime_value or entry.mtime_value
    return sorted(entries.values(), key=lambda item: (item.role, str(item.path)))


def _parse_timestamp(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _profile_csv(path: Path) -> CsvProfile:
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.reader(stream)
            header_list = next(reader, None)
            if header_list is None:
                return CsvProfile((), 0, 0, (), {}, "arquivo CSV vazio")
            header = tuple(header_list)
            duplicate_columns = tuple(
                sorted(column for column, count in Counter(header).items() if count > 1)
            )
            dataset_indexes = {
                column: header.index(column) for column in _DATASET_COLUMNS if column in header
            }
            dataset_values = {column: set() for column in dataset_indexes}
            row_count = 0
            malformed = 0
            for row in reader:
                row_count += 1
                if len(row) != len(header):
                    malformed += 1
                    continue
                for column, index in dataset_indexes.items():
                    value = row[index].strip()
                    if value:
                        dataset_values[column].add(value)
            return CsvProfile(
                header,
                row_count,
                malformed,
                duplicate_columns,
                dataset_values,
            )
    except (OSError, UnicodeError, csv.Error) as exc:
        return CsvProfile((), 0, 0, (), {}, str(exc))


def _dataset_value_matches(column: str, value: str, dataset: str) -> bool:
    if column == "city_id":
        return value == dataset or dataset.startswith(f"{value}_")
    return value == dataset


def _command_stage(payload: Mapping[str, Any]) -> str | None:
    command = payload.get("command")
    if command in (None, ""):
        recommended = str(payload.get("recommended_command", "")).strip().split()
        command = recommended[1] if len(recommended) >= 2 and recommended[0] == "ic" else None
    command = str(command or "").strip().replace("_", "-")
    if not command:
        return None
    parameters = payload.get("parameters") if isinstance(payload.get("parameters"), Mapping) else payload
    strategy = str(parameters.get("strategy", "")).strip().replace("-", "_")
    prefixes = {
        "resilience": "resilience",
        "node-resilience": "node_resilience",
        "community-resilience": "community_resilience",
        "intra-community-resilience": "intra_community_resilience",
    }
    if command in prefixes and strategy in {"random", "targeted", "targeted_adaptive"}:
        return f"{prefixes[command]}_{strategy}"
    for stage, contract in STAGE_CONTRACTS.items():
        if command in contract.commands:
            return stage
    return None


def _active_stages(
    requested: Sequence[str] | None,
    payload: Mapping[str, Any],
    manifest_entries: Sequence[ManifestEntry],
    dataset: str,
    network_type: str,
    project_root: Path,
    output_root: Path,
) -> list[str]:
    if requested is not None:
        unknown = sorted(set(requested) - set(STAGE_CONTRACTS))
        if unknown:
            raise ValueError(f"Etapas desconhecidas: {', '.join(unknown)}")
        requested_set = set(requested)
        return [stage for stage in STAGE_CONTRACTS if stage in requested_set]

    entry_paths = {entry.path for entry in manifest_entries}
    active: set[str] = set()
    command_stage = _command_stage(payload)
    if command_stage is not None:
        active.add(command_stage)
    for stage, contract in STAGE_CONTRACTS.items():
        anchors = [spec for spec in contract.artifacts if spec.anchor]
        for anchor in anchors:
            path = _resolve_spec(anchor, dataset, network_type, project_root, output_root)
            if path.exists() or path in entry_paths:
                active.add(stage)
                break
    return [stage for stage in STAGE_CONTRACTS if stage in active]


def auditar_integridade_artefatos(
    dataset: str | None = None,
    manifest: str | os.PathLike[str] | Mapping[str, Any] | None = None,
    *,
    project_root: str | os.PathLike[str] = ".",
    output_root: str | os.PathLike[str] = "outputs",
    stages: Sequence[str] | None = None,
    hash_size_limit_bytes: int | None = DEFAULT_HASH_SIZE_LIMIT_BYTES,
    mtime_tolerance_seconds: float = 2.0,
    mixed_stage_tolerance_seconds: float = 3600.0,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Audita completude, integridade, proveniência e frescor de um dataset.

    Somente ``PASS`` é considerado seguro para uso downstream. ``WARN`` também
    fecha o gate (`safe_to_use=False`), preservando o comportamento fail-closed.
    Hashes são recalculados apenas quando o manifesto declara SHA-256 e o arquivo
    respeita ``hash_size_limit_bytes``; ``None`` remove o limite explicitamente.
    """

    if hash_size_limit_bytes is not None and hash_size_limit_bytes < 0:
        raise ValueError("hash_size_limit_bytes deve ser >= 0 ou None.")
    if mtime_tolerance_seconds < 0 or mixed_stage_tolerance_seconds < 0:
        raise ValueError("Tolerancias de mtime devem ser >= 0.")

    project = Path(project_root).expanduser().resolve()
    outputs = _resolve_root(project, output_root)
    payload, manifest_file, manifest_error = _load_manifest(manifest, project)
    inferred_dataset = _infer_dataset(payload, manifest_file)
    if dataset is None and inferred_dataset is None:
        raise ValueError("Informe dataset ou um manifesto que identifique exatamente um dataset.")
    selected_dataset = _validate_dataset(dataset or inferred_dataset or "")
    network_type = infer_dataset_network_type(selected_dataset, project_root=project)
    entries = _manifest_entries(payload, selected_dataset, project, outputs)
    active_stages = _active_stages(
        stages,
        payload,
        entries,
        selected_dataset,
        network_type,
        project,
        outputs,
    )

    rows: list[dict[str, str]] = []
    csv_cache: dict[Path, CsvProfile] = {}
    dataset_checked: set[Path] = set()
    json_checked: set[Path] = set()

    def add(
        stage: str,
        check: str,
        status: str,
        path: Path | None,
        expected: Any = "",
        observed: Any = "",
        details: str = "",
    ) -> None:
        rows.append(
            {
                "dataset": selected_dataset,
                "stage": stage,
                "check": check,
                "status": status,
                "path": _display_path(path, project) if path is not None else "",
                "expected": str(expected),
                "observed": str(observed),
                "details": details,
            }
        )

    if manifest_error is not None:
        add("manifest", "manifest_parse", FAIL, manifest_file, "manifesto valido", "erro", manifest_error)
    elif manifest is not None:
        add("manifest", "manifest_parse", PASS, manifest_file, "manifesto valido", "valido")

    if dataset is not None and inferred_dataset is not None and selected_dataset != inferred_dataset:
        add(
            "manifest",
            "dataset_match",
            FAIL,
            manifest_file,
            selected_dataset,
            inferred_dataset,
            "O dataset informado diverge do identificador registrado no manifesto.",
        )
    elif inferred_dataset is not None:
        add("manifest", "dataset_match", PASS, manifest_file, selected_dataset, inferred_dataset)

    run_status = payload.get("status")
    if run_status not in (None, ""):
        normalized_run_status = str(run_status).strip().lower()
        successful_statuses = {"success", "succeeded", "complete", "completed", "pass", "passed"}
        status = PASS if normalized_run_status in successful_statuses else FAIL
        add(
            "manifest",
            "recorded_run_status",
            status,
            manifest_file,
            "execucao concluida com sucesso",
            run_status,
            "O manifesto registra uma execução que não terminou com sucesso."
            if status == FAIL
            else "",
        )

    def csv_profile(path: Path) -> CsvProfile:
        if path not in csv_cache:
            csv_cache[path] = _profile_csv(path)
        return csv_cache[path]

    def audit_dataset_columns(stage: str, path: Path, profile: CsvProfile) -> None:
        if path in dataset_checked:
            return
        dataset_checked.add(path)
        mismatches: list[str] = []
        observed_parts: list[str] = []
        for column, values in profile.dataset_values.items():
            if not values:
                continue
            observed_parts.append(f"{column}={sorted(values)}")
            mismatches.extend(
                f"{column}={value}"
                for value in sorted(values)
                if not _dataset_value_matches(column, value, selected_dataset)
            )
        if mismatches:
            add(
                stage,
                "csv_dataset_consistency",
                FAIL,
                path,
                selected_dataset,
                "; ".join(observed_parts),
                f"Outputs misturados ou atribuídos a outro dataset: {', '.join(mismatches)}",
            )
        elif observed_parts:
            add(
                stage,
                "csv_dataset_consistency",
                PASS,
                path,
                selected_dataset,
                "; ".join(observed_parts),
            )

    def audit_json_dataset(stage: str, path: Path) -> None:
        if path in json_checked or path.suffix.lower() != ".json":
            return
        json_checked.add(path)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            add(stage, "json_parse", FAIL, path, "JSON valido", "erro", str(exc))
            return
        add(stage, "json_parse", PASS, path, "JSON valido", "valido")
        if not isinstance(value, Mapping):
            return
        declared = value.get("dataset_id") or value.get("dataset")
        city = value.get("city_id")
        if declared not in (None, ""):
            status = PASS if str(declared) == selected_dataset else FAIL
            add(
                stage,
                "json_dataset_consistency",
                status,
                path,
                selected_dataset,
                declared,
                "Identificador interno divergente." if status == FAIL else "",
            )
        elif "metadata" in path.parts:
            add(
                stage,
                "json_dataset_id_missing",
                WARN,
                path,
                selected_dataset,
                "ausente",
                "Metadado legado sem dataset_id; city_id foi usado apenas como evidência auxiliar.",
            )
        if city not in (None, "") and not _dataset_value_matches("city_id", str(city), selected_dataset):
            add(
                stage,
                "json_city_consistency",
                FAIL,
                path,
                selected_dataset,
                city,
                "city_id não corresponde ao dataset nem à sua cidade-base.",
            )

    def audit_file(stage: str, spec: ArtifactSpec) -> Path:
        path = _resolve_spec(spec, selected_dataset, network_type, project, outputs)
        if not path.exists():
            add(stage, "required_file", FAIL, path, "arquivo existente", "ausente")
            return path
        if not path.is_file():
            add(stage, "required_file", FAIL, path, "arquivo regular", "nao e arquivo")
            return path
        add(stage, "required_file", PASS, path, "arquivo existente", "presente")
        size = path.stat().st_size
        add(
            stage,
            "minimum_size",
            PASS if size >= spec.min_size_bytes else FAIL,
            path,
            f">={spec.min_size_bytes}",
            size,
            "Artefato vazio ou truncado." if size < spec.min_size_bytes else "",
        )
        if path.suffix.lower() == ".csv":
            profile = csv_profile(path)
            if profile.error is not None:
                add(stage, "csv_parse", FAIL, path, "CSV valido", "erro", profile.error)
                return path
            add(stage, "csv_parse", PASS, path, "CSV valido", "valido")
            if profile.duplicate_columns:
                add(
                    stage,
                    "csv_unique_columns",
                    FAIL,
                    path,
                    "cabecalho sem duplicatas",
                    ", ".join(profile.duplicate_columns),
                )
            else:
                add(stage, "csv_unique_columns", PASS, path, "cabecalho sem duplicatas", "ok")
            missing_columns = sorted(set(spec.required_columns) - set(profile.header))
            add(
                stage,
                "csv_schema",
                FAIL if missing_columns else PASS,
                path,
                ",".join(spec.required_columns),
                ",".join(profile.header),
                f"Colunas ausentes: {', '.join(missing_columns)}" if missing_columns else "",
            )
            if spec.min_rows is not None:
                add(
                    stage,
                    "csv_min_rows",
                    PASS if profile.row_count >= spec.min_rows else FAIL,
                    path,
                    f">={spec.min_rows}",
                    profile.row_count,
                    "CSV sem o número mínimo de registros." if profile.row_count < spec.min_rows else "",
                )
            if profile.malformed_rows:
                add(
                    stage,
                    "csv_row_width",
                    FAIL,
                    path,
                    "0 linhas malformadas",
                    profile.malformed_rows,
                )
            else:
                add(stage, "csv_row_width", PASS, path, "0 linhas malformadas", 0)
            audit_dataset_columns(stage, path, profile)
        elif path.suffix.lower() == ".json":
            audit_json_dataset(stage, path)
        return path

    stage_paths: dict[str, list[Path]] = {}
    for stage in active_stages:
        contract = STAGE_CONTRACTS[stage]
        stage_paths[stage] = [audit_file(stage, spec) for spec in contract.artifacts]

        dependency_paths = [
            _resolve_spec(spec, selected_dataset, network_type, project, outputs)
            for spec in contract.dependencies
        ]
        existing_dependencies: list[Path] = []
        for dependency in dependency_paths:
            if dependency.is_file():
                existing_dependencies.append(dependency)
                add(stage, "freshness_dependency", PASS, dependency, "dependencia existente", "presente")
            else:
                add(stage, "freshness_dependency", FAIL, dependency, "dependencia existente", "ausente")
        if existing_dependencies:
            newest_input = max(path.stat().st_mtime for path in existing_dependencies)
            for artifact in stage_paths[stage]:
                if not artifact.is_file():
                    continue
                delta = artifact.stat().st_mtime - newest_input
                add(
                    stage,
                    "freshness_vs_inputs",
                    PASS if delta + mtime_tolerance_seconds >= 0 else FAIL,
                    artifact,
                    f"mtime >= entrada - {mtime_tolerance_seconds:.3f}s",
                    f"delta={delta:.6f}s",
                    "Output mais antigo que sua entrada; provável artefato stale."
                    if delta + mtime_tolerance_seconds < 0
                    else "",
                )

        mtimes = [path.stat().st_mtime for path in stage_paths[stage] if path.is_file()]
        if len(mtimes) >= 2:
            spread = max(mtimes) - min(mtimes)
            add(
                stage,
                "mixed_stage_outputs",
                PASS if spread <= mixed_stage_tolerance_seconds else FAIL,
                None,
                f"spread <= {mixed_stage_tolerance_seconds:.3f}s",
                f"spread={spread:.6f}s",
                "Arquivos obrigatórios da mesma etapa parecem vir de execuções diferentes."
                if spread > mixed_stage_tolerance_seconds
                else "",
            )

    if not active_stages and not entries and manifest_error is None:
        add(
            "audit",
            "artifacts_discovered",
            FAIL,
            outputs / selected_dataset,
            "ao menos uma etapa ou entrada de manifesto",
            "nenhuma",
            "Nenhum contrato pôde ser ativado; o resultado não pode ser considerado íntegro.",
        )

    manifest_generated_value = payload.get(
        "generated_at_utc",
        payload.get(
            "generated_at",
            payload.get("finished_at", payload.get("ended_at")),
        ),
    )
    manifest_generated_at = _parse_timestamp(manifest_generated_value)
    if manifest_generated_value not in (None, "") and manifest_generated_at is None:
        add(
            "manifest",
            "generated_at_parse",
            FAIL,
            manifest_file,
            "timestamp valido",
            manifest_generated_value,
        )

    for entry in entries:
        path = entry.path
        stage = "manifest_input" if entry.role == "input" else "manifest_output"
        if not path.is_file():
            add(stage, "manifest_file", FAIL, path, "arquivo listado existente", "ausente")
            continue
        add(stage, "manifest_file", PASS, path, "arquivo listado existente", "presente")
        stat = path.stat()
        if stat.st_size <= 0:
            add(stage, "manifest_size_nonzero", FAIL, path, ">0", stat.st_size)
        else:
            add(stage, "manifest_size_nonzero", PASS, path, ">0", stat.st_size)
        if entry.size_value not in (None, "") and (
            entry.size_bytes is None or entry.size_bytes < 0
        ):
            add(
                stage,
                "manifest_size_format",
                FAIL,
                path,
                "inteiro >= 0",
                entry.size_value,
                "Tamanho declarado no manifesto é inválido.",
            )
        elif entry.size_bytes is not None:
            add(
                stage,
                "manifest_size_match",
                PASS if stat.st_size == entry.size_bytes else FAIL,
                path,
                entry.size_bytes,
                stat.st_size,
                "Tamanho atual diverge do manifesto." if stat.st_size != entry.size_bytes else "",
            )
        if entry.mtime_ns_value not in (None, "") and (
            entry.mtime_ns is None or entry.mtime_ns < 0
        ):
            add(
                stage,
                "manifest_mtime_format",
                FAIL,
                path,
                "inteiro >= 0",
                entry.mtime_ns_value,
                "mtime_ns declarado no manifesto é inválido.",
            )
        elif entry.mtime_ns is not None:
            add(
                stage,
                "manifest_mtime_match",
                PASS if stat.st_mtime_ns == entry.mtime_ns else FAIL,
                path,
                entry.mtime_ns,
                stat.st_mtime_ns,
                "mtime atual diverge do manifesto." if stat.st_mtime_ns != entry.mtime_ns else "",
            )
        elif entry.mtime_value not in (None, ""):
            expected_mtime = _parse_timestamp(entry.mtime_value)
            if expected_mtime is None:
                add(stage, "manifest_mtime_parse", FAIL, path, "mtime valido", entry.mtime_value)
            else:
                delta = abs(stat.st_mtime - expected_mtime)
                add(
                    stage,
                    "manifest_mtime_match",
                    PASS if delta <= mtime_tolerance_seconds else FAIL,
                    path,
                    f"delta <= {mtime_tolerance_seconds:.3f}s",
                    f"delta={delta:.6f}s",
                )

        if entry.sha256 is not None:
            if not re.fullmatch(r"[0-9a-f]{64}", entry.sha256):
                add(stage, "sha256_format", FAIL, path, "64 caracteres hexadecimais", entry.sha256)
            elif hash_size_limit_bytes is not None and stat.st_size > hash_size_limit_bytes:
                add(
                    stage,
                    "sha256",
                    WARN,
                    path,
                    entry.sha256,
                    "SKIPPED_SIZE_LIMIT",
                    f"Hash não recalculado: {stat.st_size} bytes excedem o limite "
                    f"de {hash_size_limit_bytes} bytes.",
                )
            else:
                observed_hash = _sha256(path)
                add(
                    stage,
                    "sha256",
                    PASS if observed_hash == entry.sha256 else FAIL,
                    path,
                    entry.sha256,
                    observed_hash,
                    "Conteúdo diverge do SHA-256 do manifesto."
                    if observed_hash != entry.sha256
                    else "",
                )

        if entry.role == "output":
            expected_directory = (outputs / selected_dataset).resolve()
            try:
                path.resolve().relative_to(expected_directory)
                correct_directory = True
            except ValueError:
                correct_directory = False
            add(
                stage,
                "output_dataset_directory",
                PASS if correct_directory else FAIL,
                path,
                str(expected_directory),
                str(path.parent),
                "Manifesto mistura output de outro dataset ou de outra raiz."
                if not correct_directory
                else "",
            )
            if manifest_generated_at is not None:
                delta = stat.st_mtime - manifest_generated_at
                add(
                    stage,
                    "manifest_freshness",
                    PASS if delta <= mtime_tolerance_seconds else FAIL,
                    path,
                    f"mtime <= generated_at + {mtime_tolerance_seconds:.3f}s",
                    f"delta={delta:.6f}s",
                    "Output foi alterado após a geração do manifesto."
                    if delta > mtime_tolerance_seconds
                    else "",
                )

        if path.suffix.lower() == ".csv":
            profile = csv_profile(path)
            if profile.error is not None:
                add(stage, "csv_parse", FAIL, path, "CSV valido", "erro", profile.error)
            else:
                add(stage, "csv_parse", PASS, path, "CSV valido", "valido")
                if not profile.header or any(not column.strip() for column in profile.header):
                    add(
                        stage,
                        "csv_schema",
                        FAIL,
                        path,
                        "cabecalho não vazio",
                        ",".join(profile.header),
                        "CSV do manifesto tem coluna sem nome ou não possui cabeçalho.",
                    )
                elif profile.duplicate_columns:
                    add(
                        stage,
                        "csv_schema",
                        FAIL,
                        path,
                        "colunas únicas",
                        ", ".join(profile.duplicate_columns),
                        "CSV do manifesto tem nomes de coluna duplicados.",
                    )
                else:
                    add(
                        stage,
                        "csv_schema",
                        PASS,
                        path,
                        "cabecalho não vazio e colunas únicas",
                        ",".join(profile.header),
                    )
                if profile.malformed_rows:
                    add(stage, "csv_row_width", FAIL, path, 0, profile.malformed_rows)
                else:
                    add(stage, "csv_row_width", PASS, path, 0, 0)
                add(
                    stage,
                    "csv_rows_observed",
                    PASS,
                    path,
                    "contagem disponível para contrato de etapa",
                    profile.row_count,
                )
                audit_dataset_columns(stage, path, profile)
        elif path.suffix.lower() == ".json" and entry.role == "input":
            audit_json_dataset(stage, path)

    input_mtimes = [entry.path.stat().st_mtime for entry in entries if entry.role == "input" and entry.path.is_file()]
    if input_mtimes:
        newest_manifest_input = max(input_mtimes)
        for entry in entries:
            if entry.role != "output" or not entry.path.is_file():
                continue
            delta = entry.path.stat().st_mtime - newest_manifest_input
            add(
                "manifest_output",
                "freshness_vs_manifest_inputs",
                PASS if delta + mtime_tolerance_seconds >= 0 else FAIL,
                entry.path,
                f"mtime >= entrada - {mtime_tolerance_seconds:.3f}s",
                f"delta={delta:.6f}s",
                "Output listado é mais antigo que as entradas do manifesto."
                if delta + mtime_tolerance_seconds < 0
                else "",
            )

    authoritative_outputs = (
        "outputs" in payload
        and bool(payload.get("outputs_complete", True))
        and not bool(payload.get("partial", False))
    )
    if authoritative_outputs:
        dataset_directory = (outputs / selected_dataset).resolve()
        manifest_control_path = manifest_file.resolve() if manifest_file is not None else None
        actual_outputs: set[Path] = set()
        if dataset_directory.is_dir():
            for path in dataset_directory.rglob("*"):
                if not path.is_file():
                    continue
                if manifest_control_path is not None and path.resolve() == manifest_control_path:
                    continue
                try:
                    relative = path.relative_to(dataset_directory)
                except ValueError:
                    continue
                if _is_audit_control_path(relative):
                    continue
                actual_outputs.add(path.resolve())
        listed_outputs = {
            entry.path.resolve()
            for entry in entries
            if entry.role == "output"
            and entry.path.resolve().is_relative_to(dataset_directory)
            and entry.path.resolve() != manifest_control_path
        }
        extra = sorted(actual_outputs - listed_outputs)
        missing = sorted(path for path in listed_outputs - actual_outputs if not path.is_file())
        status = PASS if not extra and not missing else FAIL
        details = []
        if extra:
            details.append(
                "não listados=" + ", ".join(_display_path(path, project) for path in extra[:10])
            )
        if missing:
            details.append(
                "ausentes=" + ", ".join(_display_path(path, project) for path in missing[:10])
            )
        add(
            "manifest",
            "authoritative_output_set",
            status,
            dataset_directory,
            f"{len(listed_outputs)} arquivos listados",
            f"{len(actual_outputs)} atuais; extras={len(extra)}; ausentes={len(missing)}",
            "; ".join(details),
        )

    if not rows:
        add(
            "audit",
            "checks_executed",
            FAIL,
            None,
            ">0 verificacoes",
            0,
            "Auditoria sem evidência é reprovada por padrão.",
        )

    overall = max((row["status"] for row in rows), key=lambda status: _STATUS_PRIORITY[status])
    counts_before_overall = Counter(row["status"] for row in rows)
    add(
        "audit",
        "overall",
        overall,
        None,
        PASS,
        overall,
        "Fail-closed: somente PASS libera o uso downstream.",
    )

    audit_csv: str | None = None
    report_txt: str | None = None
    scope_label, scope_suffix = _audit_scope(stages, active_stages)
    if write_outputs:
        audit_path = (
            outputs
            / selected_dataset
            / "metrics"
            / f"artifact_integrity_audit{scope_suffix}.csv"
        )
        report_path = (
            outputs
            / selected_dataset
            / "logs"
            / f"artifact_integrity_report{scope_suffix}.txt"
        )
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        findings = [row for row in rows if row["status"] != PASS and row["check"] != "overall"]
        report_lines = [
            "=== Auditoria de Integridade e Frescor de Artefatos ===",
            "",
            f"Dataset: {selected_dataset}",
            f"Escopo: {scope_label}",
            f"Status do escopo: {overall}",
            f"Seguro dentro do escopo auditado: {'SIM' if overall == PASS else 'NAO'}",
            f"Etapas auditadas: {', '.join(active_stages) if active_stages else 'somente manifesto'}",
            f"Manifesto: {_display_path(manifest_file, project) if manifest_file else 'nao informado'}",
            f"Política SHA-256: limite={hash_size_limit_bytes if hash_size_limit_bytes is not None else 'sem limite explicito'} bytes",
            "",
            "Resumo de verificações (antes da linha overall):",
            f"- PASS: {counts_before_overall[PASS]}",
            f"- WARN: {counts_before_overall[WARN]}",
            f"- FAIL: {counts_before_overall[FAIL]}",
            "",
            "Achados que impedem PASS:",
        ]
        if findings:
            for row in findings:
                report_lines.append(
                    f"- [{row['status']}] {row['stage']}/{row['check']} | "
                    f"{row['path'] or '(sem arquivo)'} | {row['details'] or row['observed']}"
                )
        else:
            report_lines.append("- Nenhum.")
        report_lines.extend(
            [
                "",
                "Regra de decisão:",
                "- PASS: todos os contratos e verificações executadas foram satisfeitos.",
                "- WARN: evidência incompleta (por exemplo, hash declarado maior que o limite).",
                "- FAIL: arquivo obrigatório ausente/inválido, output stale/misturado ou divergência de manifesto.",
                "- O gate é fail-closed: WARN e FAIL resultam em safe_to_use=False.",
                "- PASS certifica somente as etapas listadas; não libera etapas fora do escopo.",
                "",
                f"CSV detalhado: {_display_path(audit_path, project)}",
            ]
        )
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        audit_csv = str(audit_path)
        report_txt = str(report_path)

    return {
        "dataset": selected_dataset,
        "network_type": network_type,
        "status": overall,
        "overall_status": overall,
        "ok": overall == PASS,
        "safe_to_use": overall == PASS,
        "fail_closed": overall != PASS,
        "scope": scope_label,
        "scope_is_explicit": stages is not None,
        "stages": active_stages,
        "rows": rows,
        "counts": dict(Counter(row["status"] for row in rows)),
        "audit_csv": audit_csv,
        "report_txt": report_txt,
        "hash_size_limit_bytes": hash_size_limit_bytes,
    }


audit_artifact_integrity = auditar_integridade_artefatos


__all__ = [
    "DEFAULT_HASH_SIZE_LIMIT_BYTES",
    "FAIL",
    "PASS",
    "STAGE_CONTRACTS",
    "WARN",
    "audit_artifact_integrity",
    "auditar_integridade_artefatos",
]
