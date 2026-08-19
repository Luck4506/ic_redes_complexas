from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CONFIRMED = "confirmada"
NOT_PROVEN = "nao_comprovada"
INCOMPARABLE = "incomparavel"
ALLOWED_STATES = {CONFIRMED, NOT_PROVEN, INCOMPARABLE}

SCIENTIFIC_PROFILE = "cientifico"
EXPLORATORY_PROFILE = "exploratorio"
ALLOWED_PROFILES = {SCIENTIFIC_PROFILE, EXPLORATORY_PROFILE}

DEFAULT_SCIENTIFIC_ARTIFACTS = (
    "metrics/structural_metrics.csv",
    "metrics/node_centralities.csv",
    "metrics/centrality_rankings.csv",
    "metrics/functional_topology_correlations.csv",
    "metrics/approximation_validation.csv",
    "metrics/resilience_random_aggregate.csv",
    "metrics/node_resilience_random_aggregate.csv",
    "metrics/robustness_summary.csv",
    "metrics/graph_representation_audit.csv",
    "metrics/representation_metric_sensitivity.csv",
)

DEFAULT_EXPLORATORY_ARTIFACTS = (
    "metrics/structural_metrics.csv",
    "metrics/node_centralities.csv",
    "metrics/functional_topology_correlations.csv",
    "metrics/approximation_validation.csv",
)

KNOWN_NETWORK_TYPES = {"all", "all_public", "bike", "drive", "drive_service", "walk"}
STOCHASTIC_COMMANDS = {
    "centrality",
    "communities",
    "community-resilience",
    "intra-community-resilience",
    "node-resilience",
    "od-efficiency",
    "paths",
    "random-resilience-stats",
    "representation-audit",
    "resilience",
    "road-hierarchy",
    "route-redundancy",
    "spatial-robustness",
    "structural",
    "validate-approximations",
}
SUCCESS_STATES = {"success", "successful", "ok", "completed", "complete", "sucesso"}
PLACEHOLDER_TIMESTAMPS = {
    "atual",
    "current",
    "latest",
    "now",
    "osm_atual",
    "osm-current",
    "present",
}
HEX_40 = re.compile(r"^[0-9a-fA-F]{40}$")
HEX_64 = re.compile(r"^[0-9a-fA-F]{64}$")
SAFE_DATASET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
YEAR_SUFFIX = re.compile(r"_(?:19|20)\d{2}(?:-\d{2}-\d{2})?$")

CRITERIA_FIELDS = (
    "profile",
    "scope",
    "dataset_a",
    "dataset_b",
    "criterion",
    "required_in_profile",
    "state",
    "observed_a",
    "observed_b",
    "evidence",
    "reason",
)

DATASET_FIELDS = (
    "profile",
    "dataset",
    "state",
    "required_criteria",
    "confirmed_required_criteria",
    "not_proven_required_criteria",
    "incomparable_required_criteria",
    "metadata_path",
    "network_type",
    "simplify",
    "clip_mode",
    "osm_snapshot_timestamp",
    "boundary_relation_id",
    "boundary_geometry_sha256",
    "boundary_identity_sha256",
    "raw_graph_path",
    "raw_graph_sha256",
    "clean_graph_path",
    "clean_graph_sha256",
    "git_signature",
    "protocol_signature",
    "seed_signature",
    "required_artifacts",
    "valid_required_artifacts",
    "provenance_covered_artifacts",
    "artifact_matrix_state",
)

PAIR_FIELDS = (
    "profile",
    "dataset_a",
    "dataset_b",
    "state",
    "required_criteria",
    "confirmed_required_criteria",
    "not_proven_required_criteria",
    "incomparable_required_criteria",
    "snapshot_policy",
    "network_type_a",
    "network_type_b",
    "snapshot_a",
    "snapshot_b",
    "reason",
)


@dataclass
class _DatasetEvidence:
    dataset: str
    criteria: list[dict[str, Any]] = field(default_factory=list)
    metadata_path: str = ""
    network_type: str = ""
    simplify: bool | None = None
    clip_mode: str = ""
    snapshot: str = ""
    boundary_relation_id: str = ""
    boundary_geometry_sha256: str = ""
    boundary_identity_sha256: str = ""
    raw_graph_path: str = ""
    raw_graph_sha256: str = ""
    clean_graph_path: str = ""
    clean_graph_sha256: str = ""
    git_signature: str = ""
    protocol_signature: str = ""
    seed_signature: str = ""
    artifact_matrix_state: str = NOT_PROVEN
    required_artifacts: int = 0
    valid_artifacts: int = 0
    provenance_covered_artifacts: int = 0
    state: str = NOT_PROVEN


def _criterion(
    profile: str,
    scope: str,
    dataset_a: str,
    criterion: str,
    required: bool,
    state: str,
    *,
    dataset_b: str = "",
    observed_a: Any = "",
    observed_b: Any = "",
    evidence: str = "",
    reason: str,
) -> dict[str, Any]:
    if state not in ALLOWED_STATES:
        raise ValueError(f"Estado inválido: {state}")
    return {
        "profile": profile,
        "scope": scope,
        "dataset_a": dataset_a,
        "dataset_b": dataset_b,
        "criterion": criterion,
        "required_in_profile": "sim" if required else "nao",
        "state": state,
        "observed_a": _display(observed_a),
        "observed_b": _display(observed_b),
        "evidence": evidence,
        "reason": reason,
    }


def _display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def _aggregate_state(rows: Sequence[Mapping[str, Any]]) -> str:
    required = [row for row in rows if row.get("required_in_profile") == "sim"]
    if any(row.get("state") == INCOMPARABLE for row in required):
        return INCOMPARABLE
    if any(row.get("state") == NOT_PROVEN for row in required):
        return NOT_PROVEN
    return CONFIRMED


def _state_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    required = [row for row in rows if row.get("required_in_profile") == "sim"]
    return {
        "required": len(required),
        "confirmed": sum(row.get("state") == CONFIRMED for row in required),
        "not_proven": sum(row.get("state") == NOT_PROVEN for row in required),
        "incomparable": sum(row.get("state") == INCOMPARABLE for row in required),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _nested(mapping: Mapping[str, Any], *path: str) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def _first(mapping: Mapping[str, Any], paths: Sequence[tuple[str, ...]]) -> Any:
    for path in paths:
        value = _nested(mapping, *path)
        if value not in (None, ""):
            return value
    return None


def _parse_timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.lower().replace(" ", "_") in PLACEHOLDER_TIMESTAMPS:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            parsed = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        else:
            parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
            if parsed.tzinfo is None:
                return None
            parsed = parsed.astimezone(timezone.utc)
    except ValueError:
        return None
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _snapshot_from_metadata(metadata: Mapping[str, Any]) -> tuple[str, str, str]:
    candidates: list[tuple[Any, str]] = [
        (_nested(metadata, "snapshot_timestamp_utc"), "metadata.snapshot_timestamp_utc"),
        (_nested(metadata, "osm_snapshot_timestamp"), "metadata.osm_snapshot_timestamp"),
        (_nested(metadata, "snapshot_timestamp"), "metadata.snapshot_timestamp"),
        (_nested(metadata, "query_timestamp"), "metadata.query_timestamp"),
        (_nested(metadata, "osm", "snapshot_timestamp"), "metadata.osm.snapshot_timestamp"),
        (_nested(metadata, "overpass", "query_timestamp"), "metadata.overpass.query_timestamp"),
        (_nested(metadata, "historical_date"), "metadata.historical_date"),
    ]
    settings = metadata.get("overpass_settings")
    if isinstance(settings, str):
        match = re.search(r'\[date\s*:\s*"([^"]+)"\]', settings)
        if match:
            candidates.append((match.group(1), "metadata.overpass_settings[date]"))

    saw_placeholder = False
    saw_invalid = False
    for value, source in candidates:
        if value in (None, ""):
            continue
        normalized = str(value).strip().lower().replace(" ", "_")
        if normalized in PLACEHOLDER_TIMESTAMPS:
            saw_placeholder = True
            continue
        parsed = _parse_timestamp(value)
        if parsed is not None:
            return parsed, source, CONFIRMED
        saw_invalid = True
    if saw_invalid:
        return "", "metadata", INCOMPARABLE
    if saw_placeholder:
        return "", "metadata", NOT_PROVEN
    return "", "metadata", NOT_PROVEN


def _valid_relation_id(value: Any) -> str | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    match = re.fullmatch(r"(?:relation[/ :]?|r)?(\d+)", str(value).strip(), flags=re.IGNORECASE)
    if not match or int(match.group(1)) <= 0:
        return None
    return match.group(1)


def _valid_sha256(value: Any) -> str | None:
    if isinstance(value, str) and HEX_64.fullmatch(value.strip()):
        return value.strip().lower()
    return None


def _metadata_candidates(dataset: str) -> list[Path]:
    return sorted(Path("data/metadata").glob(f"{dataset}_*_raw.json"))


def _network_from_metadata_filename(dataset: str, path: Path) -> str:
    prefix = f"{dataset}_"
    suffix = "_raw.json"
    name = path.name
    if name.startswith(prefix) and name.endswith(suffix):
        return name[len(prefix) : -len(suffix)]
    return ""


def _read_json_object(path: Path) -> tuple[dict[str, Any], str, str]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, INCOMPARABLE, f"JSON inválido ou ilegível: {type(exc).__name__}."
    if not isinstance(loaded, dict):
        return {}, INCOMPARABLE, "O JSON deve conter um objeto no nível raiz."
    return loaded, CONFIRMED, "JSON válido."


def _valid_created_at(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _valid_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _clip_validity(clip: Any) -> tuple[str, str, str]:
    if not isinstance(clip, Mapping):
        return "", NOT_PROVEN, "Objeto clip ausente."
    mode = clip.get("mode")
    if mode not in {"bbox", "radius", "place"}:
        return _display(mode), INCOMPARABLE if mode not in (None, "") else NOT_PROVEN, "clip.mode ausente ou inválido."
    try:
        if mode == "bbox":
            north = float(clip["north"])
            south = float(clip["south"])
            east = float(clip["east"])
            west = float(clip["west"])
            valid = north > south and east > west and -90 <= south < north <= 90 and -180 <= west < east <= 180
        elif mode == "radius":
            lat = float(clip["lat"])
            lon = float(clip["lon"])
            distance = float(clip["dist_meters"])
            valid = -90 <= lat <= 90 and -180 <= lon <= 180 and distance > 0
        else:
            valid = isinstance(clip.get("query"), str) and bool(clip.get("query", "").strip())
    except (KeyError, TypeError, ValueError):
        valid = False
    return str(mode), CONFIRMED if valid else INCOMPARABLE, "Recorte válido." if valid else "Parâmetros do recorte ausentes ou inválidos."


def _clip_parameter_identity(clip: Any) -> str | None:
    """Derive an exact identity for bbox/radius units from validated parameters."""
    if not isinstance(clip, Mapping):
        return None
    mode = clip.get("mode")
    keys = {
        "bbox": ("north", "south", "east", "west"),
        "radius": ("lat", "lon", "dist_meters"),
    }.get(mode)
    if keys is None:
        return None
    try:
        canonical = {
            "schema": "osm-clip-identity-v1",
            "mode": mode,
            **{key: float(clip[key]) for key in keys},
        }
    except (KeyError, TypeError, ValueError):
        return None
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _graph_file_validity(path: Path) -> tuple[str, str]:
    if not path.is_file():
        return NOT_PROVEN, "Arquivo não encontrado."
    try:
        if path.stat().st_size == 0:
            return INCOMPARABLE, "Arquivo vazio."
        with path.open("rb") as stream:
            header = stream.read(8192).lower()
    except OSError as exc:
        return INCOMPARABLE, f"Arquivo ilegível: {type(exc).__name__}."
    if b"<graphml" not in header:
        return INCOMPARABLE, "Conteúdo não apresenta cabeçalho GraphML."
    return CONFIRMED, "GraphML presente e não vazio."


def _artifact_validity(path: Path) -> tuple[str, str]:
    if not path.is_file():
        return NOT_PROVEN, "Artefato ausente."
    try:
        if path.stat().st_size == 0:
            return INCOMPARABLE, "Artefato vazio."
        if path.suffix.lower() == ".csv":
            with path.open(newline="", encoding="utf-8") as stream:
                reader = csv.reader(stream)
                header = next(reader, None)
                row = next(reader, None)
            if not header or row is None:
                return INCOMPARABLE, "CSV sem cabeçalho ou sem linhas de dados."
        elif path.suffix.lower() == ".json":
            json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
        return INCOMPARABLE, f"Artefato inválido: {type(exc).__name__}."
    return CONFIRMED, "Artefato presente, não vazio e estruturalmente legível."


def _normalize_record_path(value: Any) -> str:
    if not isinstance(value, (str, Path)):
        return ""
    path = Path(str(value))
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(Path.cwd().resolve())
        except (OSError, ValueError):
            return path.as_posix()
    return path.as_posix().lstrip("./")


def _iter_fingerprints(record: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    for collection_name in ("inputs", "artifacts", "outputs"):
        collection = record.get(collection_name)
        if isinstance(collection, Mapping):
            values: Iterable[Any] = collection.values()
        elif isinstance(collection, list):
            values = collection
        else:
            continue
        for item in values:
            if isinstance(item, Mapping):
                path = item.get("path")
                digest = item.get("sha256") or item.get("hash")
                if path not in (None, ""):
                    yield {"path": _normalize_record_path(path), "sha256": digest}


def _load_provenance(dataset: str) -> tuple[list[dict[str, Any]], str, str]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    log_path = Path(f"outputs/{dataset}/logs/cli_runs.jsonl")
    if log_path.is_file():
        try:
            for line_number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"linha {line_number} inválida em {log_path}")
                    continue
                if isinstance(record, dict):
                    records.append(record)
                else:
                    errors.append(f"linha {line_number} não contém objeto")
        except (OSError, UnicodeError) as exc:
            errors.append(f"log ilegível: {type(exc).__name__}")

    manifest_path = Path(f"outputs/{dataset}/EXPERIMENT_MANIFEST_{dataset}.json")
    if manifest_path.is_file():
        manifest, state, reason = _read_json_object(manifest_path)
        if state == INCOMPARABLE:
            errors.append(f"manifesto inválido: {reason}")
        else:
            provenance = manifest.get("provenance")
            record = dict(provenance) if isinstance(provenance, Mapping) else dict(manifest)
            record.setdefault("status", "success")
            record.setdefault("datasets", [manifest.get("dataset_id") or manifest.get("city_id") or dataset])
            if "artifacts" not in record and "outputs" in manifest:
                record["artifacts"] = manifest["outputs"]
            if "inputs" not in record and "inputs" in manifest:
                record["inputs"] = manifest["inputs"]
            records.insert(0, record)

    if errors:
        return records, INCOMPARABLE, "; ".join(errors)
    if not records:
        return [], NOT_PROVEN, "Nenhum cli_runs.jsonl ou manifesto encontrado."
    return records, CONFIRMED, "Fonte de proveniência legível."


def _successful_records(records: Sequence[Mapping[str, Any]], dataset: str) -> list[dict[str, Any]]:
    result = []
    for record in records:
        status = str(record.get("status", "")).strip().lower()
        if status not in SUCCESS_STATES:
            continue
        datasets = record.get("datasets")
        if isinstance(datasets, list) and datasets and dataset not in {str(item) for item in datasets}:
            continue
        result.append(dict(record))
    return result


def _latest_fingerprint(
    records: Sequence[Mapping[str, Any]], relative_path: str
) -> tuple[str, Mapping[str, Any] | None]:
    found_hash = ""
    found_record: Mapping[str, Any] | None = None
    for record in records:
        for fingerprint in _iter_fingerprints(record):
            if fingerprint["path"] == relative_path:
                found_hash = _valid_sha256(fingerprint.get("sha256")) or _display(fingerprint.get("sha256"))
                found_record = record
    return found_hash, found_record


def _metadata_graph_hash(metadata: Mapping[str, Any], stage: str) -> str:
    candidates = (
        (f"{stage}_graph_sha256",),
        ("graph_hashes", stage),
        ("graph_hashes", f"{stage}_sha256"),
        ("hashes", f"graphml_{stage}"),
        ("hashes", f"{stage}_graph"),
    )
    return _valid_sha256(_first(metadata, candidates)) or ""


def _normalize_parameters(value: Any) -> Any:
    identity_keys = {
        "city",
        "city_id",
        "dataset",
        "datasets",
        "reference",
        "year",
        "historical_date",
        "config",
        "input",
        "input_path",
        "output",
        "output_dir",
        "out",
        "out_dir",
    }
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_parameters(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key).lower().replace("-", "_") not in identity_keys
        }
    if isinstance(value, list):
        return [_normalize_parameters(item) for item in value]
    return value


def _record_identity(record: Mapping[str, Any], fallback: int) -> str:
    run_id = record.get("run_id")
    return str(run_id) if run_id not in (None, "") else f"record-{fallback}-{id(record)}"


def _deduplicate_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        unique[_record_identity(record, index)] = dict(record)
    return list(unique.values())


def _seed_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in parameters.items()
        if "seed" in str(key).lower() and value not in (None, "", [])
    }


def _command(record: Mapping[str, Any]) -> str:
    command = record.get("command")
    if command in (None, "") and isinstance(record.get("parameters"), Mapping):
        command = record["parameters"].get("cmd")
    return str(command or "").strip().lower().replace("_", "-")


def _git_evidence(records: Sequence[Mapping[str, Any]]) -> tuple[str, str, str]:
    if not records:
        return "", NOT_PROVEN, "Nenhuma execução produtora dos artefatos foi identificada."
    states: set[tuple[str, bool, str]] = set()
    for record in records:
        git = record.get("git")
        if not isinstance(git, Mapping):
            return "", NOT_PROVEN, "Execução sem objeto git."
        commit = git.get("commit")
        dirty = git.get("dirty")
        diff_hash = git.get("diff_sha256")
        if not isinstance(commit, str) or not HEX_40.fullmatch(commit):
            return "", NOT_PROVEN, "Commit Git ausente ou inválido."
        if not isinstance(dirty, bool):
            return "", NOT_PROVEN, "Estado dirty não foi registrado como booleano."
        valid_diff = _valid_sha256(diff_hash)
        if valid_diff is None:
            return "", NOT_PROVEN, "Hash SHA-256 do status/diff Git ausente."
        states.add((commit.lower(), dirty, valid_diff))
    if len(states) != 1:
        return "", INCOMPARABLE, "Artefatos obrigatórios foram produzidos em estados Git distintos."
    state = next(iter(states))
    return _canonical_hash(state), CONFIRMED, f"commit={state[0]}; dirty={str(state[1]).lower()}; diff_sha256={state[2]}"


def _protocol_evidence(records: Sequence[Mapping[str, Any]]) -> tuple[str, str, str, str, str, str]:
    if not records:
        return "", NOT_PROVEN, "", NOT_PROVEN, NOT_PROVEN, "Nenhum produtor rastreado."

    protocol: list[dict[str, Any]] = []
    seed_protocol: list[dict[str, Any]] = []
    argv_missing = []
    parameters_missing = []
    stochastic_missing_seed = []
    for record in records:
        command = _command(record)
        argv = record.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            argv_missing.append(command or "desconhecido")
        parameters = record.get("parameters")
        if not isinstance(parameters, Mapping) or not parameters:
            parameters_missing.append(command or "desconhecido")
            continue
        normalized = _normalize_parameters(parameters)
        protocol.append({"command": command, "parameters": normalized})
        seeds = _seed_parameters(parameters)
        if command in STOCHASTIC_COMMANDS:
            if not seeds:
                stochastic_missing_seed.append(command)
            else:
                seed_protocol.append({"command": command, "seeds": seeds})

    if argv_missing:
        argv_state = NOT_PROVEN
        argv_reason = "argv ausente em: " + ", ".join(sorted(set(argv_missing)))
    else:
        argv_state = CONFIRMED
        argv_reason = "argv completo nas execuções produtoras."

    if parameters_missing:
        protocol_state = NOT_PROVEN
        protocol_hash = ""
        protocol_reason = "Parâmetros resolvidos ausentes em: " + ", ".join(sorted(set(parameters_missing)))
    else:
        protocol_state = CONFIRMED
        protocol_hash = _canonical_hash(sorted(protocol, key=lambda row: _display(row)))
        protocol_reason = "Configuração resolvida registrada para os produtores."

    if stochastic_missing_seed:
        seed_state = NOT_PROVEN
        seed_hash = ""
        seed_reason = "Sementes ausentes em: " + ", ".join(sorted(set(stochastic_missing_seed)))
    elif seed_protocol:
        seed_state = CONFIRMED
        seed_hash = _canonical_hash(sorted(seed_protocol, key=lambda row: _display(row)))
        seed_reason = "Sementes explícitas registradas nos comandos estocásticos."
    else:
        seed_state = NOT_PROVEN
        seed_hash = ""
        seed_reason = "Nenhum comando estocástico produtor foi comprovado."
    return protocol_hash, protocol_state, seed_hash, seed_state, argv_state, f"{argv_reason} {protocol_reason} {seed_reason}"


def _required_artifact_paths(
    profile: str, required_artifacts: Sequence[str] | None
) -> tuple[str, ...]:
    selected = required_artifacts
    if selected is None:
        selected = DEFAULT_SCIENTIFIC_ARTIFACTS if profile == SCIENTIFIC_PROFILE else DEFAULT_EXPLORATORY_ARTIFACTS
    normalized = []
    for value in selected:
        path = Path(str(value))
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError(f"Artefato obrigatório deve ser relativo ao diretório do dataset: {value}")
        text = path.as_posix().lstrip("./")
        if text and text not in normalized:
            normalized.append(text)
    if not normalized:
        raise ValueError("A matriz de artefatos obrigatórios não pode ser vazia.")
    return tuple(normalized)


def _add_dataset_criterion(
    evidence: _DatasetEvidence,
    profile: str,
    name: str,
    required: bool,
    state: str,
    *,
    observed: Any = "",
    source: str = "",
    reason: str,
) -> None:
    evidence.criteria.append(
        _criterion(
            profile,
            "dataset",
            evidence.dataset,
            name,
            required,
            state,
            observed_a=observed,
            evidence=source,
            reason=reason,
        )
    )


def _audit_dataset(
    dataset: str,
    profile: str,
    required_artifacts: tuple[str, ...],
) -> _DatasetEvidence:
    scientific = profile == SCIENTIFIC_PROFILE
    result = _DatasetEvidence(dataset=dataset, required_artifacts=len(required_artifacts))

    candidates = _metadata_candidates(dataset)
    if not candidates:
        metadata_path = Path(f"data/metadata/{dataset}_drive_raw.json")
        metadata: dict[str, Any] = {}
        metadata_state = NOT_PROVEN
        metadata_reason = "Metadados não encontrados."
    elif len(candidates) > 1:
        metadata_path = candidates[0]
        metadata = {}
        metadata_state = INCOMPARABLE
        metadata_reason = "Mais de um metadata *_raw.json encontrado; seleção ambígua: " + ", ".join(path.name for path in candidates)
    else:
        metadata_path = candidates[0]
        metadata, metadata_state, metadata_reason = _read_json_object(metadata_path)
    result.metadata_path = metadata_path.as_posix()
    _add_dataset_criterion(
        result,
        profile,
        "metadata_presence_and_json_validity",
        True,
        metadata_state,
        observed=result.metadata_path,
        source=result.metadata_path,
        reason=metadata_reason,
    )

    dataset_id = metadata.get("dataset_id")
    if dataset_id in (None, ""):
        dataset_state, dataset_reason = NOT_PROVEN, "metadata.dataset_id ausente."
    elif str(dataset_id) != dataset:
        dataset_state, dataset_reason = INCOMPARABLE, "metadata.dataset_id diverge do dataset auditado."
    else:
        dataset_state, dataset_reason = CONFIRMED, "Identificador do dataset coincide."
    _add_dataset_criterion(result, profile, "metadata_dataset_identity", True, dataset_state, observed=dataset_id, source=result.metadata_path, reason=dataset_reason)

    core_valid = (
        _valid_created_at(metadata.get("created_at"))
        and _valid_nonnegative_int(metadata.get("nodes"))
        and _valid_nonnegative_int(metadata.get("edges"))
        and isinstance(metadata.get("crs"), str)
        and bool(metadata.get("crs", "").strip())
    )
    core_missing = any(metadata.get(key) in (None, "") for key in ("created_at", "nodes", "edges", "crs"))
    core_state = CONFIRMED if core_valid else (NOT_PROVEN if core_missing else INCOMPARABLE)
    _add_dataset_criterion(
        result,
        profile,
        "metadata_core_fields",
        True,
        core_state,
        observed={key: metadata.get(key) for key in ("created_at", "nodes", "edges", "crs")},
        source=result.metadata_path,
        reason="created_at, nodes, edges e crs válidos." if core_valid else "Campos centrais ausentes ou inválidos; created_at não substitui timestamp OSM.",
    )

    network_type = metadata.get("network_type")
    if network_type in (None, ""):
        network_state, network_reason = NOT_PROVEN, "network_type ausente."
        result.network_type = _network_from_metadata_filename(dataset, metadata_path)
    elif not isinstance(network_type, str) or network_type not in KNOWN_NETWORK_TYPES:
        network_state, network_reason = INCOMPARABLE, "network_type inválido para OSMnx."
        result.network_type = _display(network_type)
    else:
        network_state, network_reason = CONFIRMED, "network_type explícito e reconhecido."
        result.network_type = network_type
    _add_dataset_criterion(result, profile, "network_type_validity", True, network_state, observed=network_type, source=result.metadata_path, reason=network_reason)

    filename_network = _network_from_metadata_filename(dataset, metadata_path)
    if not filename_network or not result.network_type:
        filename_network_state, filename_network_reason = NOT_PROVEN, "Não foi possível confrontar nome do metadata e network_type."
    elif filename_network != result.network_type:
        filename_network_state, filename_network_reason = INCOMPARABLE, "network_type diverge do nome do metadata."
    else:
        filename_network_state, filename_network_reason = CONFIRMED, "Nome do arquivo e network_type coincidem."
    _add_dataset_criterion(result, profile, "metadata_filename_network_type", True, filename_network_state, observed=filename_network, source=result.metadata_path, reason=filename_network_reason)

    simplify = metadata.get("simplify")
    result.simplify = simplify if isinstance(simplify, bool) else None
    simplify_state = CONFIRMED if isinstance(simplify, bool) else (NOT_PROVEN if simplify in (None, "") else INCOMPARABLE)
    _add_dataset_criterion(result, profile, "simplify_validity", True, simplify_state, observed=simplify, source=result.metadata_path, reason="simplify explicitamente booleano." if simplify_state == CONFIRMED else "simplify ausente ou não booleano.")

    clip = metadata.get("clip")
    clip_mode, clip_state, clip_reason = _clip_validity(clip)
    result.clip_mode = clip_mode
    _add_dataset_criterion(result, profile, "clip_mode_and_parameters", True, clip_state, observed=clip, source=result.metadata_path, reason=clip_reason)

    snapshot, snapshot_source, snapshot_state = _snapshot_from_metadata(metadata)
    result.snapshot = snapshot
    snapshot_reason = (
        "Snapshot/query timestamp OSM explícito e normalizado."
        if snapshot_state == CONFIRMED
        else "Timestamp OSM ausente, genérico ou inválido; created_at e 'OSM_atual' não são aceitos."
    )
    _add_dataset_criterion(result, profile, "osm_snapshot_or_query_timestamp", scientific, snapshot_state, observed=snapshot, source=snapshot_source, reason=snapshot_reason)

    clip_mapping = clip if isinstance(clip, Mapping) else {}
    relation_value = _first(
        metadata,
        (
            ("boundary_relation_id",),
            ("osm_relation_id",),
            ("osm_boundary", "relation_id"),
            ("clip", "boundary_relation_id"),
            ("clip", "osm_relation_id"),
            ("clip", "osm_boundary", "relation_id"),
        ),
    )
    relation_id = _valid_relation_id(relation_value)
    result.boundary_relation_id = relation_id or ""
    if result.clip_mode == "place":
        relation_state = CONFIRMED if relation_id else (NOT_PROVEN if relation_value in (None, "") else INCOMPARABLE)
        relation_reason = "Relação OSM do limite registrada." if relation_id else "Recorte place sem relation id OSM válido."
        relation_required = scientific
    else:
        relation_state = CONFIRMED
        relation_reason = "Relation id não se aplica obrigatoriamente a bbox/radius."
        relation_required = False
    _add_dataset_criterion(result, profile, "boundary_relation_identity", relation_required, relation_state, observed=relation_value, source=result.metadata_path, reason=relation_reason)

    geometry_value = _first(
        metadata,
        (("boundary_geometry_sha256",), ("geometry_sha256",), ("clip", "boundary_geometry_sha256"), ("clip", "geometry_sha256")),
    )
    geometry_hash = _valid_sha256(geometry_value)
    result.boundary_geometry_sha256 = geometry_hash or ""
    identity_value = _first(
        metadata,
        (("boundary_identity_sha256",), ("clip", "boundary_identity_sha256")),
    )
    declared_identity_hash = _valid_sha256(identity_value)
    identity_declared = identity_value not in (None, "")
    geometry_declared = geometry_value not in (None, "")
    identity_hash: str | None = None
    identity_observed: Any = identity_value or geometry_value

    if result.clip_mode in {"bbox", "radius"}:
        # Para recortes paramétricos a identidade é verificável localmente. A
        # declaração do metadata nunca substitui o valor recomputado e qualquer
        # divergência deve fechar o gate.
        recomputed_identity = (
            _clip_parameter_identity(clip_mapping) if clip_state == CONFIRMED else None
        )
        identity_hash = recomputed_identity
        identity_observed = {
            "declared": identity_value,
            "recomputed": recomputed_identity,
        }
        if recomputed_identity is None:
            identity_state = INCOMPARABLE if clip_state == INCOMPARABLE else NOT_PROVEN
            identity_reason = "Não foi possível recomputar a identidade do recorte."
        elif identity_declared and declared_identity_hash is None:
            identity_state = INCOMPARABLE
            identity_reason = "Identidade declarada do recorte não é um SHA-256 válido."
        elif declared_identity_hash is not None and declared_identity_hash != recomputed_identity:
            identity_state = INCOMPARABLE
            identity_reason = "Identidade declarada diverge dos parâmetros exatos do recorte."
        elif declared_identity_hash is not None:
            identity_state = CONFIRMED
            identity_reason = "Identidade declarada coincide com a identidade recomputada do recorte."
        else:
            identity_state = CONFIRMED
            identity_reason = "Identidade derivada deterministicamente dos parâmetros exatos do recorte."
    elif result.clip_mode == "place":
        # Em recortes administrativos, boundary_identity representa o hash da
        # geometria normalizada. Quando ambos são declarados, devem coincidir.
        identity_hash = geometry_hash or declared_identity_hash
        identity_observed = {
            "declared": identity_value,
            "geometry": geometry_value,
        }
        if identity_declared and declared_identity_hash is None:
            identity_state = INCOMPARABLE
            identity_reason = "Identidade declarada do recorte não é um SHA-256 válido."
        elif geometry_declared and geometry_hash is None:
            identity_state = INCOMPARABLE
            identity_reason = "Hash declarado da geometria não é um SHA-256 válido."
        elif (
            declared_identity_hash is not None
            and geometry_hash is not None
            and declared_identity_hash != geometry_hash
        ):
            identity_state = INCOMPARABLE
            identity_reason = "Identidade declarada diverge do hash da geometria normalizada."
        elif declared_identity_hash is not None and geometry_hash is not None:
            identity_state = CONFIRMED
            identity_reason = "Identidade do recorte coincide com o hash da geometria normalizada."
        elif declared_identity_hash is not None:
            identity_state = CONFIRMED
            identity_reason = "Identidade SHA-256 explícita do recorte registrada."
        elif geometry_hash is not None:
            identity_state = CONFIRMED
            identity_reason = "Identidade do recorte herdada do hash da geometria normalizada."
        else:
            identity_state = NOT_PROVEN
            identity_reason = "Identidade verificável do recorte ausente."
    else:
        identity_hash = declared_identity_hash or geometry_hash
        if identity_declared and declared_identity_hash is None:
            identity_state = INCOMPARABLE
            identity_reason = "Identidade declarada do recorte não é um SHA-256 válido."
        elif geometry_declared and geometry_hash is None:
            identity_state = INCOMPARABLE
            identity_reason = "Hash declarado da geometria não é um SHA-256 válido."
        elif identity_hash is not None:
            identity_state = INCOMPARABLE
            identity_reason = "Identidade declarada sem modo de recorte válido para verificá-la."
        else:
            identity_state = NOT_PROVEN
            identity_reason = "Identidade verificável do recorte ausente."

    result.boundary_identity_sha256 = identity_hash or ""
    _add_dataset_criterion(
        result,
        profile,
        "boundary_identity_hash",
        scientific,
        identity_state,
        observed=identity_observed,
        source=result.metadata_path,
        reason=identity_reason,
    )

    network_for_path = result.network_type or filename_network or "drive"
    raw_path = Path(f"data/graphs/{dataset}_{network_for_path}_raw.graphml")
    clean_path = Path(f"data/graphs/{dataset}_{network_for_path}_clean.graphml")
    result.raw_graph_path = raw_path.as_posix()
    result.clean_graph_path = clean_path.as_posix()
    raw_state, raw_reason = _graph_file_validity(raw_path)
    clean_state, clean_reason = _graph_file_validity(clean_path)
    _add_dataset_criterion(result, profile, "raw_graph_presence_and_format", True, raw_state, observed=result.raw_graph_path, source=result.raw_graph_path, reason=raw_reason)
    _add_dataset_criterion(result, profile, "clean_graph_presence_and_format", True, clean_state, observed=result.clean_graph_path, source=result.clean_graph_path, reason=clean_reason)

    records, provenance_state, provenance_reason = _load_provenance(dataset)
    successful = _successful_records(records, dataset)
    _add_dataset_criterion(result, profile, "provenance_source_validity", scientific, provenance_state, observed=len(successful), source=f"outputs/{dataset}/logs/cli_runs.jsonl", reason=provenance_reason)

    actual_graph_hashes: dict[str, str] = {}
    for stage, path, file_state in (("raw", raw_path, raw_state), ("clean", clean_path, clean_state)):
        actual = _sha256_file(path) if file_state == CONFIRMED else ""
        actual_graph_hashes[stage] = actual
        relative = path.as_posix()
        recorded, _record = _latest_fingerprint(successful, relative)
        if not recorded:
            recorded = _metadata_graph_hash(metadata, stage)
        if not actual:
            hash_state, hash_reason = NOT_PROVEN, "Arquivo não disponível para conferir o hash."
        elif not recorded:
            hash_state, hash_reason = NOT_PROVEN, "Nenhum SHA-256 registrado para o grafo."
        elif not _valid_sha256(recorded):
            hash_state, hash_reason = INCOMPARABLE, "Fingerprint registrado não é SHA-256 válido."
        elif actual != recorded:
            hash_state, hash_reason = INCOMPARABLE, "SHA-256 atual diverge do fingerprint registrado."
        else:
            hash_state, hash_reason = CONFIRMED, "SHA-256 atual coincide com a proveniência."
        if stage == "raw":
            result.raw_graph_sha256 = actual
        else:
            result.clean_graph_sha256 = actual
        _add_dataset_criterion(result, profile, f"{stage}_graph_hash_verification", scientific, hash_state, observed=actual, source=relative, reason=hash_reason)

    relevant_records: list[Mapping[str, Any]] = []
    artifact_validity_states: list[str] = []
    artifact_provenance_states: list[str] = []
    for relative_artifact in required_artifacts:
        artifact_path = Path("outputs") / dataset / relative_artifact
        validity_state, validity_reason = _artifact_validity(artifact_path)
        artifact_validity_states.append(validity_state)
        if validity_state == CONFIRMED:
            result.valid_artifacts += 1
        _add_dataset_criterion(
            result,
            profile,
            f"required_artifact:{relative_artifact}",
            True,
            validity_state,
            observed=artifact_path.as_posix(),
            source=artifact_path.as_posix(),
            reason=validity_reason,
        )

        actual_hash = _sha256_file(artifact_path) if validity_state == CONFIRMED else ""
        recorded_hash, producer = _latest_fingerprint(successful, artifact_path.as_posix())
        if not actual_hash:
            artifact_provenance_state, artifact_provenance_reason = NOT_PROVEN, "Artefato indisponível para validar proveniência."
        elif not recorded_hash:
            artifact_provenance_state, artifact_provenance_reason = NOT_PROVEN, "Artefato não possui fingerprint de uma execução bem-sucedida."
        elif not _valid_sha256(recorded_hash):
            artifact_provenance_state, artifact_provenance_reason = INCOMPARABLE, "Fingerprint do artefato não é SHA-256 válido."
        elif actual_hash != recorded_hash:
            artifact_provenance_state, artifact_provenance_reason = INCOMPARABLE, "Artefato foi alterado após a execução registrada."
        else:
            artifact_provenance_state, artifact_provenance_reason = CONFIRMED, "Artefato coincide com o SHA-256 da execução produtora."
            result.provenance_covered_artifacts += 1
            if producer is not None:
                relevant_records.append(producer)
        artifact_provenance_states.append(artifact_provenance_state)
        _add_dataset_criterion(
            result,
            profile,
            f"artifact_provenance:{relative_artifact}",
            scientific,
            artifact_provenance_state,
            observed=actual_hash,
            source=f"outputs/{dataset}/logs/cli_runs.jsonl",
            reason=artifact_provenance_reason,
        )

    relevant = _deduplicate_records(relevant_records)
    git_signature, git_state, git_reason = _git_evidence(relevant)
    result.git_signature = git_signature
    _add_dataset_criterion(result, profile, "git_commit_dirty_and_diff_hash", scientific, git_state, observed=git_signature, source=f"outputs/{dataset}/logs/cli_runs.jsonl", reason=git_reason)

    protocol_hash, protocol_state, seed_hash, seed_state, argv_state, protocol_reason = _protocol_evidence(relevant)
    result.protocol_signature = protocol_hash
    result.seed_signature = seed_hash
    _add_dataset_criterion(result, profile, "executed_argv", scientific, argv_state, observed=len(relevant), source=f"outputs/{dataset}/logs/cli_runs.jsonl", reason=protocol_reason)
    _add_dataset_criterion(result, profile, "resolved_configuration", scientific, protocol_state, observed=protocol_hash, source=f"outputs/{dataset}/logs/cli_runs.jsonl", reason=protocol_reason)
    _add_dataset_criterion(result, profile, "explicit_seeds", scientific, seed_state, observed=seed_hash, source=f"outputs/{dataset}/logs/cli_runs.jsonl", reason=protocol_reason)

    validity_matrix_state = INCOMPARABLE if INCOMPARABLE in artifact_validity_states else (NOT_PROVEN if NOT_PROVEN in artifact_validity_states else CONFIRMED)
    provenance_matrix_state = INCOMPARABLE if INCOMPARABLE in artifact_provenance_states else (NOT_PROVEN if NOT_PROVEN in artifact_provenance_states else CONFIRMED)
    result.artifact_matrix_state = provenance_matrix_state if scientific else validity_matrix_state
    result.state = _aggregate_state(result.criteria)
    return result


def _pair_equivalence(
    profile: str,
    dataset_a: str,
    dataset_b: str,
    name: str,
    value_a: Any,
    value_b: Any,
    required: bool,
) -> dict[str, Any]:
    if value_a in (None, "") or value_b in (None, ""):
        state, reason = NOT_PROVEN, "Valor ausente em pelo menos um dataset."
    elif value_a != value_b:
        state, reason = INCOMPARABLE, "Valores explicitamente divergentes."
    else:
        state, reason = CONFIRMED, "Valores comprovados e equivalentes."
    return _criterion(
        profile,
        "pair",
        dataset_a,
        name,
        required,
        state,
        dataset_b=dataset_b,
        observed_a=value_a,
        observed_b=value_b,
        reason=reason,
    )


def _audit_pair(
    a: _DatasetEvidence,
    b: _DatasetEvidence,
    profile: str,
    snapshot_policy: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scientific = profile == SCIENTIFIC_PROFILE
    rows = [
        _criterion(profile, "pair", a.dataset, "dataset_a_eligibility", True, a.state, dataset_b=b.dataset, observed_a=a.state, reason="Estado agregado do primeiro dataset."),
        _criterion(profile, "pair", a.dataset, "dataset_b_eligibility", True, b.state, dataset_b=b.dataset, observed_b=b.state, reason="Estado agregado do segundo dataset."),
        _pair_equivalence(profile, a.dataset, b.dataset, "network_type_equivalence", a.network_type, b.network_type, True),
        _pair_equivalence(profile, a.dataset, b.dataset, "simplify_equivalence", a.simplify, b.simplify, True),
        _pair_equivalence(profile, a.dataset, b.dataset, "clip_mode_equivalence", a.clip_mode, b.clip_mode, True),
        _pair_equivalence(profile, a.dataset, b.dataset, "git_state_equivalence", a.git_signature, b.git_signature, scientific),
        _pair_equivalence(profile, a.dataset, b.dataset, "resolved_protocol_equivalence", a.protocol_signature, b.protocol_signature, scientific),
        _pair_equivalence(profile, a.dataset, b.dataset, "seed_protocol_equivalence", a.seed_signature, b.seed_signature, scientific),
        _pair_equivalence(profile, a.dataset, b.dataset, "artifact_matrix_equivalence", a.artifact_matrix_state, b.artifact_matrix_state, True),
    ]

    if snapshot_policy == "same":
        rows.append(_pair_equivalence(profile, a.dataset, b.dataset, "osm_snapshot_equivalence", a.snapshot, b.snapshot, scientific))
    else:
        if a.snapshot and b.snapshot:
            snapshot_state, snapshot_reason = CONFIRMED, "Snapshots documentados; igualdade não é exigida no modo longitudinal."
        else:
            snapshot_state, snapshot_reason = NOT_PROVEN, "Snapshot ausente em pelo menos um dataset."
        rows.append(
            _criterion(
                profile,
                "pair",
                a.dataset,
                "osm_snapshot_documentation",
                scientific,
                snapshot_state,
                dataset_b=b.dataset,
                observed_a=a.snapshot,
                observed_b=b.snapshot,
                reason=snapshot_reason,
            )
        )

    same_geographic_family = YEAR_SUFFIX.sub("", a.dataset) == YEAR_SUFFIX.sub("", b.dataset)
    if not a.boundary_identity_sha256 or not b.boundary_identity_sha256:
        boundary_state, boundary_reason = NOT_PROVEN, "Identidade do recorte ausente em pelo menos um dataset."
    elif same_geographic_family and a.boundary_identity_sha256 != b.boundary_identity_sha256:
        boundary_state, boundary_reason = INCOMPARABLE, "A mesma família geográfica usa identidades de recorte diferentes."
    else:
        boundary_state = CONFIRMED
        boundary_reason = "Identidades geométricas documentadas; limites distintos são esperados entre cidades." if not same_geographic_family else "Geometria do limite preservada na série."
    rows.append(
        _criterion(
            profile,
            "pair",
            a.dataset,
            "boundary_identity_provenance",
            scientific,
            boundary_state,
            dataset_b=b.dataset,
            observed_a=a.boundary_identity_sha256,
            observed_b=b.boundary_identity_sha256,
            reason=boundary_reason,
        )
    )

    state = _aggregate_state(rows)
    counts = _state_counts(rows)
    failing = [row["criterion"] for row in rows if row["required_in_profile"] == "sim" and row["state"] != CONFIRMED]
    summary = {
        "profile": profile,
        "dataset_a": a.dataset,
        "dataset_b": b.dataset,
        "state": state,
        "required_criteria": counts["required"],
        "confirmed_required_criteria": counts["confirmed"],
        "not_proven_required_criteria": counts["not_proven"],
        "incomparable_required_criteria": counts["incomparable"],
        "snapshot_policy": snapshot_policy,
        "network_type_a": a.network_type,
        "network_type_b": b.network_type,
        "snapshot_a": a.snapshot,
        "snapshot_b": b.snapshot,
        "reason": "Todos os critérios obrigatórios foram comprovados." if not failing else "Critérios pendentes: " + ";".join(failing),
    }
    return rows, summary


def _dataset_summary(evidence: _DatasetEvidence, profile: str) -> dict[str, Any]:
    counts = _state_counts(evidence.criteria)
    return {
        "profile": profile,
        "dataset": evidence.dataset,
        "state": evidence.state,
        "required_criteria": counts["required"],
        "confirmed_required_criteria": counts["confirmed"],
        "not_proven_required_criteria": counts["not_proven"],
        "incomparable_required_criteria": counts["incomparable"],
        "metadata_path": evidence.metadata_path,
        "network_type": evidence.network_type,
        "simplify": _display(evidence.simplify),
        "clip_mode": evidence.clip_mode,
        "osm_snapshot_timestamp": evidence.snapshot,
        "boundary_relation_id": evidence.boundary_relation_id,
        "boundary_geometry_sha256": evidence.boundary_geometry_sha256,
        "boundary_identity_sha256": evidence.boundary_identity_sha256,
        "raw_graph_path": evidence.raw_graph_path,
        "raw_graph_sha256": evidence.raw_graph_sha256,
        "clean_graph_path": evidence.clean_graph_path,
        "clean_graph_sha256": evidence.clean_graph_sha256,
        "git_signature": evidence.git_signature,
        "protocol_signature": evidence.protocol_signature,
        "seed_signature": evidence.seed_signature,
        "required_artifacts": evidence.required_artifacts,
        "valid_required_artifacts": evidence.valid_artifacts,
        "provenance_covered_artifacts": evidence.provenance_covered_artifacts,
        "artifact_matrix_state": evidence.artifact_matrix_state,
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: Path,
    profile: str,
    snapshot_policy: str,
    artifacts: Sequence[str],
    dataset_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    criteria: Sequence[Mapping[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8") as stream:
        stream.write("=== Auditoria Científica de Comparabilidade ===\n\n")
        stream.write(f"Perfil: {profile}\n")
        stream.write(f"Política temporal: {snapshot_policy}\n")
        stream.write("Estados possíveis: confirmada, nao_comprovada, incomparavel.\n")
        stream.write("O perfil científico é fail-closed: ausência de evidência nunca é convertida em confirmação.\n")
        if profile == EXPLORATORY_PROFILE:
            stream.write("ATENÇÃO: confirmação neste arquivo significa somente homogeneidade exploratória mínima, não comparabilidade científica.\n")
        stream.write("created_at, mtime e rótulos como OSM_atual não provam o snapshot consultado.\n\n")

        stream.write("Matriz de artefatos obrigatórios\n")
        for artifact in artifacts:
            stream.write(f"- {artifact}\n")

        stream.write("\nResumo por dataset\n")
        for row in dataset_rows:
            stream.write(
                f"- {row['dataset']}: {row['state']} | obrigatórios={row['required_criteria']} | "
                f"não comprovados={row['not_proven_required_criteria']} | incompatíveis={row['incomparable_required_criteria']} | "
                f"artefatos válidos={row['valid_required_artifacts']}/{row['required_artifacts']} | "
                f"artefatos com proveniência={row['provenance_covered_artifacts']}/{row['required_artifacts']}.\n"
            )

        stream.write("\nResumo por par\n")
        if not pair_rows:
            stream.write("- Nenhum par: forneça ao menos dois datasets para comparação cruzada.\n")
        for row in pair_rows:
            stream.write(f"- {row['dataset_a']} x {row['dataset_b']}: {row['state']} | {row['reason']}\n")

        stream.write("\nCritérios não confirmados\n")
        pending = [row for row in criteria if row["required_in_profile"] == "sim" and row["state"] != CONFIRMED]
        if not pending:
            stream.write("- Nenhum.\n")
        for row in pending:
            target = row["dataset_a"] + (f" x {row['dataset_b']}" if row["dataset_b"] else "")
            stream.write(f"- [{row['state']}] {target} | {row['criterion']}: {row['reason']}\n")

        stream.write("\nInterpretação e limites\n")
        stream.write("- confirmada exige todos os critérios obrigatórios do perfil; não é sinônimo de validade externa ou causal.\n")
        stream.write("- nao_comprovada indica evidência ausente/insuficiente, não equivalência presumida.\n")
        stream.write("- incomparavel indica contradição, conteúdo inválido, hash divergente ou protocolo explicitamente diferente.\n")
        stream.write("- Hash de geometria identifica o recorte; entre cidades ele deve ser documentado, não necessariamente igual.\n")
        stream.write("- No modo temporal 'same', snapshots diferentes tornam o par incomparável; use 'documented' apenas para desenho longitudinal explícito.\n")
        stream.write("- A equivalência de configuração exclui identificadores e caminhos específicos do dataset, preservando parâmetros analíticos e sementes.\n")


def auditar_comparabilidade_cientifica(
    datasets: Sequence[str],
    output_dir: str = "outputs/comparisons",
    perfil: str = SCIENTIFIC_PROFILE,
    required_artifacts: Sequence[str] | None = None,
    snapshot_policy: str = "same",
) -> dict[str, Any]:
    """Audit comparability without treating missing evidence as equivalence.

    ``snapshot_policy='same'`` is the cross-sectional default. Use
    ``'documented'`` only when different, explicit snapshots are the intended
    longitudinal treatment. The exploratory profile is intentionally emitted
    under separate filenames and must not be presented as scientific proof.
    """
    if perfil not in ALLOWED_PROFILES:
        raise ValueError(f"perfil deve ser um de: {', '.join(sorted(ALLOWED_PROFILES))}.")
    if snapshot_policy not in {"same", "documented"}:
        raise ValueError("snapshot_policy deve ser 'same' ou 'documented'.")

    unique_datasets: list[str] = []
    for value in datasets:
        dataset = str(value).strip()
        if not SAFE_DATASET.fullmatch(dataset):
            raise ValueError(f"Dataset inválido ou inseguro: {value}")
        if dataset not in unique_datasets:
            unique_datasets.append(dataset)
    if not unique_datasets:
        raise ValueError("Informe pelo menos um dataset.")

    artifacts = _required_artifact_paths(perfil, required_artifacts)
    evidence = [_audit_dataset(dataset, perfil, artifacts) for dataset in unique_datasets]
    dataset_rows = [_dataset_summary(item, perfil) for item in evidence]
    criteria_rows = [row for item in evidence for row in item.criteria]

    pair_rows: list[dict[str, Any]] = []
    for a, b in combinations(evidence, 2):
        pair_criteria, pair_summary = _audit_pair(a, b, perfil, snapshot_policy)
        criteria_rows.extend(pair_criteria)
        pair_rows.append(pair_summary)

    prefix = "scientific_comparability" if perfil == SCIENTIFIC_PROFILE else "exploratory_comparability"
    output_root = Path(output_dir)
    criteria_csv = output_root / f"{prefix}_criteria.csv"
    datasets_csv = output_root / f"{prefix}_datasets.csv"
    pairs_csv = output_root / f"{prefix}_pairs.csv"
    report_txt = output_root / f"{prefix}_report.txt"
    _write_csv(criteria_csv, criteria_rows, CRITERIA_FIELDS)
    _write_csv(datasets_csv, dataset_rows, DATASET_FIELDS)
    _write_csv(pairs_csv, pair_rows, PAIR_FIELDS)
    _write_report(report_txt, perfil, snapshot_policy, artifacts, dataset_rows, pair_rows, criteria_rows)

    overall_rows = pair_rows if pair_rows else dataset_rows
    overall_state = INCOMPARABLE if any(row["state"] == INCOMPARABLE for row in overall_rows) else (
        NOT_PROVEN if any(row["state"] == NOT_PROVEN for row in overall_rows) else CONFIRMED
    )
    return {
        "profile": perfil,
        "state": overall_state,
        "criteria_csv": str(criteria_csv),
        "datasets_csv": str(datasets_csv),
        "pairs_csv": str(pairs_csv),
        "report_txt": str(report_txt),
        "dataset_rows": dataset_rows,
        "pair_rows": pair_rows,
        "required_artifacts": list(artifacts),
    }


__all__ = [
    "CONFIRMED",
    "INCOMPARABLE",
    "NOT_PROVEN",
    "auditar_comparabilidade_cientifica",
]
