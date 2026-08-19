from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.artifact_integrity import FAIL, PASS, WARN, audit_artifact_integrity


def _write(path: Path, content: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _set_mtime(paths: list[Path], timestamp: float) -> None:
    for path in paths:
        os.utime(path, (timestamp, timestamp))


def _structural_files(output_root: Path, dataset: str = "demo") -> list[Path]:
    base = output_root / dataset
    return [
        _write(base / "metrics/structural_metrics.csv", "metric,value\nnodes,3\n"),
        _write(
            base / "metrics/degree_distribution.csv",
            "degree,count,probability\n2,3,1.0\n",
        ),
        _write(base / "figures/degree_distribution_loglog.png", b"png"),
        _write(base / "logs/structural_report.txt", "relatorio\n"),
    ]


def _find_rows(result: dict, check: str) -> list[dict[str, str]]:
    return [row for row in result["rows"] if row["check"] == check]


class ArtifactIntegrityTests(unittest.TestCase):
    def test_complete_fresh_pipeline_passes_and_writes_under_custom_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "generated"
            raw_graph = _write(root / "data/graphs/demo_drive_raw.graphml", "<graphml/>\n")
            metadata = _write(
                root / "data/metadata/demo_drive_raw.json",
                json.dumps({"dataset_id": "demo", "city_id": "demo"}),
            )
            clean_graph = _write(root / "data/graphs/demo_drive_clean.graphml", "<graphml/>\n")
            preprocess_log = _write(output_root / "demo/logs/grafo_resumo.txt", "grafo limpo\n")
            structural = _structural_files(output_root)

            _set_mtime([raw_graph, metadata], 1_000)
            _set_mtime([clean_graph, preprocess_log], 2_000)
            _set_mtime(structural, 3_000)

            result = audit_artifact_integrity(
                "demo",
                project_root=root,
                output_root=output_root,
                stages=["download", "preprocess", "structural"],
                mtime_tolerance_seconds=0,
            )

            self.assertEqual(result["status"], PASS)
            self.assertEqual(result["overall_status"], PASS)
            self.assertTrue(result["ok"])
            self.assertTrue(result["safe_to_use"])
            self.assertFalse(result["fail_closed"])
            audit_path = (
                output_root
                / "demo/metrics/artifact_integrity_audit__download--preprocess--structural.csv"
            ).resolve()
            report_path = (
                output_root
                / "demo/logs/artifact_integrity_report__download--preprocess--structural.txt"
            ).resolve()
            self.assertEqual(result["audit_csv"], str(audit_path))
            self.assertEqual(result["report_txt"], str(report_path))
            self.assertTrue(audit_path.is_file())
            self.assertTrue(report_path.is_file())

            with audit_path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[-1]["check"], "overall")
            self.assertEqual(rows[-1]["status"], PASS)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Status do escopo: PASS", report)
            self.assertIn("PASS certifica somente as etapas listadas", report)

    def test_explicit_stage_audit_does_not_overwrite_automatic_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "generated"
            clean_graph = _write(root / "data/graphs/demo_drive_clean.graphml", "<graphml/>\n")
            structural = _structural_files(output_root)
            _set_mtime([clean_graph], 1_000)
            _set_mtime(structural, 2_000)

            automatic = audit_artifact_integrity(
                "demo",
                project_root=root,
                output_root=output_root,
                mtime_tolerance_seconds=0,
            )
            canonical_path = Path(automatic["audit_csv"])
            canonical_before = canonical_path.read_bytes()

            scoped = audit_artifact_integrity(
                "demo",
                project_root=root,
                output_root=output_root,
                stages=["structural"],
                mtime_tolerance_seconds=0,
            )

            self.assertEqual(automatic["scope"], "automatico")
            self.assertFalse(automatic["scope_is_explicit"])
            self.assertEqual(scoped["scope"], "structural")
            self.assertTrue(scoped["scope_is_explicit"])
            self.assertNotEqual(automatic["audit_csv"], scoped["audit_csv"])
            self.assertIn("artifact_integrity_audit__structural.csv", scoped["audit_csv"])
            self.assertEqual(canonical_path.read_bytes(), canonical_before)

    def test_missing_schema_and_stale_outputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "generated"
            clean_graph = _write(root / "data/graphs/demo_drive_clean.graphml", "<graphml/>\n")
            structural = _structural_files(output_root)
            structural[0].write_text("name,amount\nnodes,3\n", encoding="utf-8")
            _set_mtime(structural, 1_000)
            _set_mtime([clean_graph], 2_000)

            result = audit_artifact_integrity(
                "demo",
                project_root=root,
                output_root=output_root,
                stages=["structural"],
                mtime_tolerance_seconds=0,
                write_outputs=False,
            )

            self.assertEqual(result["status"], FAIL)
            self.assertFalse(result["safe_to_use"])
            self.assertTrue(result["fail_closed"])
            self.assertTrue(
                any(row["status"] == FAIL for row in _find_rows(result, "csv_schema"))
            )
            self.assertTrue(
                any(
                    row["status"] == FAIL
                    for row in _find_rows(result, "freshness_vs_inputs")
                )
            )
            self.assertFalse(
                (output_root / "demo/metrics/artifact_integrity_audit.csv").exists()
            )
            self.assertFalse(
                (output_root / "demo/logs/artifact_integrity_report.txt").exists()
            )

    def test_manifest_sha256_is_verified_and_dataset_can_be_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "custom-output"
            artifact = _write(
                output_root / "demo/metrics/result.csv",
                "dataset,value\ndemo,1\n",
            )
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = {
                "dataset": "demo",
                "artifacts": [
                    {
                        "path": "outputs/demo/metrics/result.csv",
                        "sha256": digest,
                        "size_bytes": artifact.stat().st_size,
                    }
                ],
            }

            result = audit_artifact_integrity(
                manifest=manifest,
                project_root=root,
                output_root=output_root,
                stages=[],
                write_outputs=False,
            )

            self.assertEqual(result["dataset"], "demo")
            self.assertEqual(result["status"], PASS)
            sha_rows = _find_rows(result, "sha256")
            self.assertEqual(len(sha_rows), 1)
            self.assertEqual(sha_rows[0]["status"], PASS)
            self.assertEqual(sha_rows[0]["observed"], digest)

            manifest["artifacts"][0]["sha256"] = "0" * 64
            failed = audit_artifact_integrity(
                manifest=manifest,
                project_root=root,
                output_root=output_root,
                stages=[],
                write_outputs=False,
            )
            self.assertEqual(failed["status"], FAIL)
            self.assertEqual(_find_rows(failed, "sha256")[0]["status"], FAIL)

    def test_large_hash_is_explicitly_skipped_and_warn_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "generated"
            artifact = _write(output_root / "demo/metrics/large.bin", b"0123456789")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

            result = audit_artifact_integrity(
                manifest={
                    "dataset_id": "demo",
                    "artifacts": [
                        {"path": "outputs/demo/metrics/large.bin", "sha256": digest}
                    ],
                },
                project_root=root,
                output_root=output_root,
                stages=[],
                hash_size_limit_bytes=4,
                write_outputs=False,
            )

            self.assertEqual(result["status"], WARN)
            self.assertFalse(result["safe_to_use"])
            self.assertTrue(result["fail_closed"])
            sha_row = _find_rows(result, "sha256")[0]
            self.assertEqual(sha_row["status"], WARN)
            self.assertEqual(sha_row["observed"], "SKIPPED_SIZE_LIMIT")
            self.assertIn("10 bytes", sha_row["details"])

    def test_mixed_dataset_and_unlisted_output_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "generated"
            listed = _write(
                output_root / "demo/metrics/listed.csv",
                "dataset,value\nother,1\n",
            )
            _write(output_root / "demo/logs/unlisted.txt", "execucao antiga\n")
            manifest = {
                "dataset": "demo",
                "outputs": [
                    {
                        "path": "outputs/demo/metrics/listed.csv",
                        "size_bytes": listed.stat().st_size,
                    }
                ],
                "outputs_complete": True,
            }

            result = audit_artifact_integrity(
                manifest=manifest,
                project_root=root,
                output_root=output_root,
                stages=[],
                write_outputs=False,
            )

            self.assertEqual(result["status"], FAIL)
            self.assertEqual(
                _find_rows(result, "csv_dataset_consistency")[0]["status"],
                FAIL,
            )
            output_set = _find_rows(result, "authoritative_output_set")[0]
            self.assertEqual(output_set["status"], FAIL)
            self.assertIn("extras=1", output_set["observed"])

    def test_manifest_input_newer_than_output_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "generated"
            source = _write(root / "data/source.bin", b"source")
            artifact = _write(
                output_root / "demo/metrics/result.csv",
                "dataset,value\ndemo,1\n",
            )
            _set_mtime([artifact], 1_000)
            _set_mtime([source], 2_000)

            result = audit_artifact_integrity(
                manifest={
                    "dataset": "demo",
                    "inputs": [{"path": "data/source.bin"}],
                    "artifacts": [{"path": "outputs/demo/metrics/result.csv"}],
                },
                project_root=root,
                output_root=output_root,
                stages=[],
                mtime_tolerance_seconds=0,
                write_outputs=False,
            )

            self.assertEqual(result["status"], FAIL)
            freshness = _find_rows(result, "freshness_vs_manifest_inputs")
            self.assertEqual(len(freshness), 1)
            self.assertEqual(freshness[0]["status"], FAIL)

    def test_authoritative_manifest_does_not_count_itself_as_mixed_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "generated"
            artifact = _write(
                output_root / "demo/metrics/result.csv",
                "dataset,value\ndemo,1\n",
            )
            _set_mtime([artifact], 1_000)
            manifest_path = output_root / "demo/EXPERIMENT_MANIFEST_demo.json"
            _write(
                manifest_path,
                json.dumps(
                    {
                        "schema_version": "2.0",
                        "dataset_id": "demo",
                        "generated_at_utc": "1970-01-01T00:20:00+00:00",
                        "outputs": [{"path": "outputs/demo/metrics/result.csv"}],
                    }
                ),
            )
            _write(
                output_root / "demo/metrics/artifact_integrity_audit__structural.csv",
                "dataset,status\ndemo,PASS\n",
            )
            _write(
                output_root / "demo/logs/artifact_integrity_report__structural.txt",
                "controle da auditoria\n",
            )

            result = audit_artifact_integrity(
                manifest=manifest_path,
                project_root=root,
                output_root=output_root,
                stages=[],
                write_outputs=False,
            )

            self.assertEqual(result["status"], PASS)
            output_set = _find_rows(result, "authoritative_output_set")[0]
            self.assertEqual(output_set["status"], PASS)
            self.assertIn("extras=0", output_set["observed"])

    def test_invalid_manifest_metadata_and_csv_schema_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_root = root / "generated"
            _write(
                output_root / "demo/metrics/result.csv",
                "dataset,dataset\ndemo,demo\n",
            )

            result = audit_artifact_integrity(
                manifest={
                    "dataset": "demo",
                    "artifacts": [
                        {
                            "path": "outputs/demo/metrics/result.csv",
                            "size_bytes": "many",
                            "mtime_ns": "later",
                        }
                    ],
                },
                project_root=root,
                output_root=output_root,
                stages=[],
                write_outputs=False,
            )

            self.assertEqual(result["status"], FAIL)
            self.assertEqual(_find_rows(result, "manifest_size_format")[0]["status"], FAIL)
            self.assertEqual(_find_rows(result, "manifest_mtime_format")[0]["status"], FAIL)
            self.assertEqual(_find_rows(result, "csv_schema")[0]["status"], FAIL)


if __name__ == "__main__":
    unittest.main()
