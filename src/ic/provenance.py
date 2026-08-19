from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import shlex
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

import yaml

from .io_utils import resolve_dataset_id

try:  # pragma: no cover - indisponível apenas no Windows
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


SCHEMA_VERSION = "1.0"
_CHUNK_SIZE = 1024 * 1024
_APPEND_LOCK = threading.Lock()
_PACKAGE_DISTRIBUTIONS = (
    "ic-redes-complexas",
    "osmnx",
    "networkx",
    "folium",
    "pandas",
    "numpy",
    "matplotlib",
    "pyyaml",
    "scipy",
)
_INPUT_SUFFIXES = {".graphml", ".json", ".yaml", ".yml"}


@dataclass(frozen=True)
class _FileState:
    size_bytes: int
    mtime_ns: int
    ctime_ns: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _utc_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_safe(item) for item in sorted(value, key=str)]
    if callable(value):
        module = getattr(value, "__module__", "")
        name = getattr(value, "__qualname__", getattr(value, "__name__", type(value).__name__))
        return f"{module}.{name}" if module else name
    return str(value)


def _parsed_arguments(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        raw = dict(value)
    elif hasattr(value, "__dict__"):
        raw = vars(value)
    else:
        raise TypeError("set_parsed_args espera argparse.Namespace ou Mapping.")
    return {str(key): _json_safe(item) for key, item in raw.items()}


def _runtime_environment() -> dict[str, Any]:
    packages: dict[str, str | None] = {}
    for distribution in _PACKAGE_DISTRIBUTIONS:
        try:
            packages[distribution] = importlib_metadata.version(distribution)
        except importlib_metadata.PackageNotFoundError:
            packages[distribution] = None

    return {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "platform": platform.platform(),
        },
        "packages": packages,
    }


def _run_git(cwd: Path, *arguments: str) -> bytes | None:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if completed.returncode == 0 else None


def _decode_git(value: bytes | None) -> str | None:
    if value is None:
        return None
    decoded = value.decode("utf-8", errors="replace").strip()
    return decoded or None


def _git_state(cwd: Path) -> dict[str, Any]:
    root_value = _decode_git(_run_git(cwd, "rev-parse", "--show-toplevel"))
    if root_value is None:
        return {
            "repository_root": None,
            "commit": None,
            "branch": None,
            "dirty": None,
            "diff_sha256": None,
        }

    root = Path(root_value).resolve()
    commit = _decode_git(_run_git(root, "rev-parse", "HEAD"))
    branch = _decode_git(_run_git(root, "symbolic-ref", "--short", "-q", "HEAD"))
    status = _run_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all") or b""
    diff = _run_git(root, "diff", "--binary", "HEAD", "--") or b""
    untracked = _run_git(root, "ls-files", "--others", "--exclude-standard", "-z") or b""

    # O status integra arquivos não rastreados ao identificador mesmo quando o
    # `git diff HEAD` não os inclui. O conteúdo rastreado continua representado
    # integralmente pelo diff binário.
    digest = hashlib.sha256()
    digest.update(b"git-status\0")
    digest.update(status)
    digest.update(b"\0git-diff\0")
    digest.update(diff)
    digest.update(b"\0untracked-content\0")
    for raw_relative in sorted(item for item in untracked.split(b"\0") if item):
        relative = raw_relative.decode("utf-8", errors="surrogateescape")
        path = root / relative
        digest.update(len(raw_relative).to_bytes(8, "big"))
        digest.update(raw_relative)
        try:
            stat = path.lstat()
            digest.update(stat.st_mode.to_bytes(8, "big", signed=False))
            if path.is_symlink():
                payload = os.readlink(path).encode("utf-8", errors="surrogateescape")
                digest.update(len(payload).to_bytes(8, "big"))
                digest.update(payload)
            elif path.is_file():
                digest.update(stat.st_size.to_bytes(16, "big", signed=False))
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(_CHUNK_SIZE), b""):
                        digest.update(chunk)
            else:
                digest.update(b"non-regular")
        except OSError as exc:
            digest.update(f"unreadable:{type(exc).__name__}".encode("ascii"))

    return {
        "repository_root": str(root),
        "commit": commit,
        "branch": branch,
        "dirty": bool(status),
        "diff_sha256": digest.hexdigest(),
    }


def git_worktree_state(cwd: str | os.PathLike[str] = ".") -> dict[str, Any]:
    """Return a content-sensitive Git state, including untracked files."""
    return _git_state(Path(cwd).expanduser().resolve())


def _display_path(path: Path, cwd: Path) -> str:
    try:
        return path.resolve().relative_to(cwd).as_posix()
    except (OSError, ValueError):
        return str(path.resolve())


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(path: Path, cwd: Path, *, kind: str | None = None) -> dict[str, Any] | None:
    # Uma segunda tentativa evita combinar hash e metadados de versões distintas
    # quando outro processo substitui um arquivo durante a leitura.
    last_before = None
    last_after = None
    digest = None
    try:
        for _ in range(2):
            last_before = path.stat()
            if not path.is_file():
                return None
            digest = _file_digest(path)
            last_after = path.stat()
            if (
                last_before.st_size == last_after.st_size
                and last_before.st_mtime_ns == last_after.st_mtime_ns
                and last_before.st_ctime_ns == last_after.st_ctime_ns
            ):
                break
    except OSError:
        return None

    assert last_before is not None and last_after is not None and digest is not None
    result: dict[str, Any] = {
        "path": _display_path(path, cwd),
        "sha256": digest,
        "size_bytes": last_after.st_size,
        "mtime_ns": last_after.st_mtime_ns,
        "mtime_utc": _utc_from_timestamp(last_after.st_mtime),
    }
    if kind is not None:
        result["kind"] = kind
    if (
        last_before.st_size != last_after.st_size
        or last_before.st_mtime_ns != last_after.st_mtime_ns
        or last_before.st_ctime_ns != last_after.st_ctime_ns
    ):
        result["unstable_during_read"] = True
    return result


def _resolve_path(value: str | os.PathLike[str], cwd: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return path.resolve()


def _config_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}
    return dict(loaded) if isinstance(loaded, Mapping) else {}


def _manifest_datasets(path: Path) -> list[str]:
    """Infer dataset identifiers from a manifest payload or canonical filename."""

    candidates: list[str] = []

    def add(value: Any) -> None:
        if value in (None, ""):
            return
        text = str(value).strip()
        if text and text not in candidates:
            candidates.append(text)

    if path.suffix.lower() == ".json" and path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, Mapping):
            for key in ("dataset", "dataset_id", "city_id"):
                value = payload.get(key)
                if value not in (None, ""):
                    add(value)
                    break
            if not candidates:
                datasets = payload.get("datasets")
                if isinstance(datasets, Sequence) and not isinstance(datasets, (str, bytes)):
                    for dataset in datasets:
                        add(dataset)

    if not candidates:
        match = re.match(r"(?:EXPERIMENT_)?MANIFEST_(.+?)(?:\.json|\.txt)?$", path.name)
        if match:
            add(match.group(1))
    return candidates


def _iter_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        result: list[Any] = []
        for item in value:
            result.extend(_iter_values(item))
        return result
    return [value]


def _infer_datasets(parameters: Mapping[str, Any], cwd: Path) -> list[str]:
    candidates: list[str] = []

    def add(value: Any) -> None:
        for item in _iter_values(value):
            text = str(item).strip()
            if text and text not in candidates:
                candidates.append(text)

    add(parameters.get("datasets"))
    add(parameters.get("dataset"))
    if candidates:
        # Alguns comandos multi-dataset também consomem uma referência fora da
        # lista posicional (por exemplo, ``historical-audit``). Ela precisa
        # participar tanto dos fingerprints de entrada quanto dos logs por
        # dataset.
        add(parameters.get("reference"))
        return candidates

    for manifest_value in _iter_values(parameters.get("manifest")):
        if not isinstance(manifest_value, (str, os.PathLike)) or not str(manifest_value).strip():
            continue
        try:
            manifest_path = _resolve_path(manifest_value, cwd)
        except (OSError, ValueError, TypeError):
            continue
        add(_manifest_datasets(manifest_path))
    if candidates:
        return candidates

    command = str(parameters.get("cmd") or "").strip().lower().replace("_", "-")
    city = parameters.get("city") or parameters.get("city_id")
    year = parameters.get("year")
    config_value = parameters.get("config")
    config: dict[str, Any] = {}
    if config_value not in (None, ""):
        try:
            config = _config_mapping(_resolve_path(str(config_value), cwd))
        except (OSError, ValueError):
            config = {}
    elif command == "download" and city not in (None, ""):
        candidate = cwd / "config" / f"{str(city).strip()}.yaml"
        if candidate.is_file():
            config = _config_mapping(candidate)

    if command == "download" and config:
        resolved_city = config.get("city_id") or city
        if resolved_city not in (None, ""):
            add(
                resolve_dataset_id(
                    str(resolved_city),
                    configured_dataset_id=(
                        str(config["dataset_id"])
                        if config.get("dataset_id") not in (None, "")
                        else None
                    ),
                    historical_date=(
                        str(config["historical_date"])
                        if config.get("historical_date") not in (None, "")
                        else None
                    ),
                    year=year,
                )
            )
            return candidates

    if city not in (None, ""):
        add(resolve_dataset_id(str(city), year=year))

    add(parameters.get("reference"))

    return candidates


def _input_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return "config"
    if suffix == ".graphml":
        return "graphml"
    if suffix == ".json":
        return "metadata"
    return "input"


def _discover_inputs(
    cwd: Path,
    parameters: Mapping[str, Any],
    datasets: Sequence[str],
) -> list[dict[str, Any]]:
    candidates: set[Path] = set()
    manifest_candidates: set[Path] = set()

    for key, value in parameters.items():
        key_lower = key.lower()
        is_manifest = "manifest" in key_lower
        if not is_manifest and not any(
            token in key_lower for token in ("config", "metadata", "graph", "input")
        ):
            continue
        for item in _iter_values(value):
            if not isinstance(item, (str, os.PathLike)) or str(item).strip() == "":
                continue
            try:
                path = _resolve_path(item, cwd)
            except (OSError, ValueError, TypeError):
                continue
            if path.is_file() and (is_manifest or path.suffix.lower() in _INPUT_SUFFIXES):
                candidates.add(path)
                if is_manifest:
                    manifest_candidates.add(path)

    identifiers = {str(dataset) for dataset in datasets}
    city = parameters.get("city") or parameters.get("city_id")
    if city not in (None, ""):
        identifiers.add(str(city))
    for dataset in tuple(identifiers):
        identifiers.add(re.sub(r"_\d{4}(?:-\d{2}-\d{2})?$", "", dataset))

    config_dir = cwd / "config"
    if config_dir.is_dir():
        for pattern in ("*.yaml", "*.yml"):
            for path in config_dir.rglob(pattern):
                if path.stem in identifiers:
                    candidates.add(path.resolve())
                    continue
                configured_id = _config_mapping(path).get("dataset_id") or _config_mapping(path).get("city_id")
                if configured_id is not None and str(configured_id) in identifiers:
                    candidates.add(path.resolve())

    network_type = parameters.get("network_type")
    if network_type in (None, ""):
        for config_path in sorted(candidates):
            if config_path.suffix.lower() not in {".yaml", ".yml"}:
                continue
            configured_network = _config_mapping(config_path).get("network_type")
            if configured_network not in (None, ""):
                network_type = configured_network
                break
    network_type = str(network_type or "drive")

    for dataset in datasets:
        for stage in ("raw", "clean"):
            graph = cwd / "data" / "graphs" / f"{dataset}_{network_type}_{stage}.graphml"
            if graph.is_file():
                candidates.add(graph.resolve())
            metadata = cwd / "data" / "metadata" / f"{dataset}_{network_type}_{stage}.json"
            if metadata.is_file():
                candidates.add(metadata.resolve())

    fingerprints = []
    for path in sorted(candidates, key=lambda item: _display_path(item, cwd)):
        kind = "manifest" if path in manifest_candidates else _input_kind(path)
        fingerprint = _fingerprint(path, cwd, kind=kind)
        if fingerprint is not None:
            fingerprints.append(fingerprint)
    return fingerprints


def _safe_dataset_directory(dataset: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", dataset).strip("._-")
    if not safe:
        safe = "dataset"
    if safe != dataset or len(safe) > 160:
        digest = hashlib.sha256(dataset.encode("utf-8")).hexdigest()[:10]
        safe = f"{safe[:145]}-{digest}"
    return safe


def _is_provenance_log(path: Path, cwd: Path) -> bool:
    try:
        relative = path.resolve().relative_to(cwd / "outputs")
    except (OSError, ValueError):
        return False
    return relative.name == "cli_runs.jsonl" and (
        relative.parent == Path("experiments") or relative.parent.name == "logs"
    )


def _artifact_roots(cwd: Path, parameters: Mapping[str, Any], datasets: Sequence[str]) -> set[Path]:
    roots = {cwd / "data" / "graphs", cwd / "data" / "metadata"}
    if datasets:
        roots.update(cwd / "outputs" / _safe_dataset_directory(dataset) for dataset in datasets)
        roots.add(cwd / "outputs" / "comparisons")
        roots.add(cwd / "outputs" / "experiments")
    else:
        roots.add(cwd / "outputs")

    for key, value in parameters.items():
        key_lower = key.lower().replace("-", "_")
        if key_lower not in {"output", "output_dir", "out", "out_dir"}:
            continue
        for item in _iter_values(value):
            if not isinstance(item, (str, os.PathLike)) or str(item).strip() == "":
                continue
            try:
                roots.add(_resolve_path(item, cwd))
            except (OSError, ValueError, TypeError):
                continue
    return {path.resolve() for path in roots}


def _walk_files(root: Path) -> list[Path]:
    try:
        if root.is_file():
            return [root.resolve()]
        if not root.is_dir():
            return []
        return [path.resolve() for path in root.rglob("*") if path.is_file()]
    except OSError:
        return []


def _snapshot(roots: Sequence[Path], cwd: Path) -> dict[Path, _FileState]:
    result: dict[Path, _FileState] = {}
    for root in roots:
        for path in _walk_files(root):
            if _is_provenance_log(path, cwd):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            result[path] = _FileState(stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    return result


def _changed_artifacts(
    before: Mapping[Path, _FileState],
    roots: Sequence[Path],
    cwd: Path,
) -> list[dict[str, Any]]:
    after = _snapshot(roots, cwd)
    artifacts: list[dict[str, Any]] = []
    for path in sorted(after, key=lambda item: _display_path(item, cwd)):
        previous = before.get(path)
        current = after[path]
        if previous == current:
            continue
        fingerprint = _fingerprint(path, cwd)
        if fingerprint is None:
            continue
        fingerprint["change"] = "created" if previous is None else "modified"
        artifacts.append(fingerprint)
    return artifacts


def _structured_error(error: Any) -> Any:
    if error is None:
        return None
    if isinstance(error, BaseException):
        structured: dict[str, Any] = {
            "type": f"{type(error).__module__}.{type(error).__qualname__}",
            "message": str(error),
        }
        argparse_message = getattr(error, "_ic_argparse_message", None)
        if argparse_message not in (None, ""):
            structured["message"] = str(argparse_message)
            structured["system_exit_message"] = str(error)
        if isinstance(error, SystemExit):
            structured["exit_code"] = _json_safe(error.code)
        return structured
    if isinstance(error, Mapping):
        return _json_safe(error)
    return {"type": type(error).__name__, "message": str(error)}


def _append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    payload = (
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)

    with _APPEND_LOCK:
        descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_RDWR, 0o644)
        try:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            run_id = record.get("run_id")
            if run_id not in (None, ""):
                os.lseek(descriptor, 0, os.SEEK_SET)
                existing = bytearray()
                while chunk := os.read(descriptor, _CHUNK_SIZE):
                    existing.extend(chunk)
                for line in bytes(existing).splitlines():
                    try:
                        current = json.loads(line)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    if isinstance(current, Mapping) and current.get("run_id") == run_id:
                        return
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError(f"Falha ao anexar registro de proveniência em {path}.")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


class CliRunRecorder:
    """Coleta e persiste a proveniência de uma execução da CLI.

    O chamador cria o gravador antes do parsing, passa o Namespace já resolvido
    (portanto contendo os defaults do argparse) e finaliza no bloco de sucesso
    ou de tratamento da exceção.
    """

    def __init__(
        self,
        argv: Sequence[str] | None = None,
        *,
        cwd: str | os.PathLike[str] | None = None,
    ) -> None:
        self._argv = tuple(str(item) for item in (sys.argv if argv is None else argv))
        self._cwd = Path.cwd().resolve() if cwd is None else Path(cwd).expanduser().resolve()
        self._run_id = str(uuid.uuid4())
        self._started_at = _utc_now()
        self._started_monotonic = time.monotonic()
        self._runtime = _runtime_environment()
        self._git = _git_state(self._cwd)
        self._parameters: dict[str, Any] | None = None
        self._datasets: list[str] = []
        self._inputs: list[dict[str, Any]] = []
        self._roots: tuple[Path, ...] = ()
        self._before: dict[Path, _FileState] = {}
        self._parsed_at: str | None = None
        self._parsed_monotonic: float | None = None
        self._pending_record: dict[str, Any] | None = None
        self._pending_log_paths: tuple[Path, ...] = ()
        self._finished_record: dict[str, Any] | None = None
        self._state_lock = threading.RLock()

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def cwd(self) -> Path:
        return self._cwd

    def set_parsed_args(self, args: Mapping[str, Any] | Any) -> "CliRunRecorder":
        """Registra todos os argumentos já materializados pelo parser e inicia o snapshot."""

        with self._state_lock:
            if self._finished_record is not None:
                raise RuntimeError("A execução já foi finalizada.")
            if self._parameters is not None:
                raise RuntimeError("Os argumentos da execução já foram registrados.")

            self._parameters = _parsed_arguments(args)
            self._datasets = _infer_datasets(self._parameters, self._cwd)
            self._inputs = _discover_inputs(self._cwd, self._parameters, self._datasets)
            self._roots = tuple(sorted(_artifact_roots(self._cwd, self._parameters, self._datasets)))
            self._before = _snapshot(self._roots, self._cwd)
            self._parsed_at = _utc_now()
            self._parsed_monotonic = time.monotonic()
        return self

    def finish(self, status: str, error: Any = None) -> dict[str, Any]:
        """Finaliza, grava uma linha JSON global e uma linha para cada dataset."""

        if not isinstance(status, str) or not status.strip():
            raise ValueError("status deve ser uma string não vazia.")

        with self._state_lock:
            if self._finished_record is not None:
                return self._finished_record
            if self._pending_record is not None:
                record = self._pending_record
                for path in self._pending_log_paths:
                    _append_jsonl(path, record)
                self._finished_record = record
                self._pending_record = None
                self._pending_log_paths = ()
                return record
            if self._parameters is None:
                self.set_parsed_args({})

            finished_monotonic = time.monotonic()
            finished_at = _utc_now()
            assert self._parameters is not None
            artifacts = _changed_artifacts(self._before, self._roots, self._cwd)
            command = self._parameters.get("cmd")
            if command in (None, ""):
                command = next(
                    (token for token in self._argv[1:] if token and not token.startswith("-")),
                    self._argv[0] if self._argv else None,
                )

            log_paths = [self._cwd / "outputs" / "experiments" / "cli_runs.jsonl"]
            log_paths.extend(
                self._cwd
                / "outputs"
                / _safe_dataset_directory(dataset)
                / "logs"
                / "cli_runs.jsonl"
                for dataset in self._datasets
            )

            record: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "run_id": self._run_id,
                "argv": list(self._argv),
                "command": command,
                "command_line": shlex.join(self._argv),
                "parameters": self._parameters,
                "status": status.strip(),
                "error": _structured_error(error),
                "started_at": self._started_at,
                "arguments_parsed_at": self._parsed_at,
                "finished_at": finished_at,
                "duration_seconds": round(finished_monotonic - self._started_monotonic, 9),
                "execution_duration_seconds": round(
                    finished_monotonic - (self._parsed_monotonic or self._started_monotonic), 9
                ),
                "cwd": str(self._cwd),
                "runtime": self._runtime,
                "git": self._git,
                "datasets": list(self._datasets),
                "inputs": self._inputs,
                "artifacts": artifacts,
                "logs": [_display_path(path, self._cwd) for path in log_paths],
            }

            self._pending_record = record
            self._pending_log_paths = tuple(dict.fromkeys(log_paths))
            for path in self._pending_log_paths:
                _append_jsonl(path, record)
            self._finished_record = record
            self._pending_record = None
            self._pending_log_paths = ()
            return record


def begin_cli_run(
    argv: Sequence[str] | None = None,
    *,
    cwd: str | os.PathLike[str] | None = None,
) -> CliRunRecorder:
    """Inicia um gravador de proveniência sem exigir integração com o argparse."""

    return CliRunRecorder(argv, cwd=cwd)


__all__ = ["CliRunRecorder", "SCHEMA_VERSION", "begin_cli_run", "git_worktree_state"]
