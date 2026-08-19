from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from ic.artifact_integrity import PASS, audit_artifact_integrity
from ic.final_report import _write_experiment_manifest


class FinalManifestTests(unittest.TestCase):
    def test_manifest_hashes_inputs_and_outputs_and_records_actual_command(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            try:
                os.chdir(root)
                graph = root / "data/graphs/demo_drive_clean.graphml"
                artifact = root / "outputs/demo/metrics/result.csv"
                graph.parent.mkdir(parents=True)
                artifact.parent.mkdir(parents=True)
                graph_payload = b'<?xml version="1.0"?><graphml><graph id="demo"/></graphml>'
                graph.write_bytes(graph_payload)
                artifact.write_bytes(b"metric,value\nnodes,3\n")

                path = _write_experiment_manifest("demo", "outputs/demo", ["outputs/demo/metrics/result.csv"])
                payload = json.loads(Path(path).read_text(encoding="utf-8"))
            finally:
                os.chdir(original_cwd)

        self.assertEqual(payload["schema_version"], "2.0")
        self.assertEqual(payload["actual_report_argv"], list(__import__("sys").argv))
        self.assertEqual(payload["inputs"][0]["sha256"], hashlib.sha256(graph_payload).hexdigest())
        self.assertEqual(
            payload["outputs"][0]["sha256"],
            hashlib.sha256(b"metric,value\nnodes,3\n").hexdigest(),
        )

    def test_provenance_append_does_not_invalidate_new_manifest(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            try:
                os.chdir(root)
                graph = root / "data/graphs/demo_drive_clean.graphml"
                artifact = root / "outputs/demo/metrics/result.csv"
                log = root / "outputs/demo/logs/cli_runs.jsonl"
                graph.parent.mkdir(parents=True)
                artifact.parent.mkdir(parents=True)
                log.parent.mkdir(parents=True)
                graph.write_bytes(b'<?xml version="1.0"?><graphml><graph id="demo"/></graphml>')
                artifact.write_bytes(b"metric,value\nnodes,3\n")
                log.write_text('{"run_id":"before","command":"structural"}\n', encoding="utf-8")

                manifest_path = _write_experiment_manifest(
                    "demo",
                    "outputs/demo",
                    ["outputs/demo/metrics/result.csv", "outputs/demo/logs/cli_runs.jsonl"],
                )
                payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
                log.write_text(
                    log.read_text(encoding="utf-8")
                    + '{"run_id":"report-finish","command":"report"}\n',
                    encoding="utf-8",
                )

                audit = audit_artifact_integrity(
                    manifest=manifest_path,
                    project_root=root,
                    output_root=root / "outputs",
                    stages=[],
                    write_outputs=False,
                )
            finally:
                os.chdir(original_cwd)

        self.assertFalse(any(item["path"].endswith("cli_runs.jsonl") for item in payload["outputs"]))
        self.assertEqual(audit["status"], PASS)


if __name__ == "__main__":
    unittest.main()
