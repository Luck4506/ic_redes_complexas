from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from ic.cli import main
from ic.provenance import _append_jsonl, begin_cli_run


def _jsonl_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class ProvenanceIntegrationRegressionTests(unittest.TestCase):
    def test_manifest_only_integrity_infers_dataset_and_fingerprints_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            manifest = root / "outputs/demo/EXPERIMENT_MANIFEST_demo.json"
            manifest.parent.mkdir(parents=True)
            payload = b'{"schema_version":"2.0","city_id":"demo","outputs":[]}\n'
            manifest.write_bytes(payload)

            recorder = begin_cli_run(
                ["ic", "artifact-integrity", "--manifest", str(manifest)],
                cwd=root,
            )
            recorder.set_parsed_args(
                {
                    "cmd": "artifact-integrity",
                    "city": None,
                    "year": None,
                    "manifest": str(manifest),
                    "output_root": "outputs",
                }
            )
            record = recorder.finish("success")

            self.assertEqual(record["datasets"], ["demo"])
            manifest_input = next(
                item for item in record["inputs"] if item["path"].endswith(manifest.name)
            )
            self.assertEqual(manifest_input["kind"], "manifest")
            self.assertEqual(manifest_input["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertTrue((root / "outputs/demo/logs/cli_runs.jsonl").is_file())

    def test_partial_multilog_failure_reuses_the_exact_pending_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            recorder = begin_cli_run(["ic", "structural", "--city", "demo"], cwd=root)
            recorder.set_parsed_args({"cmd": "structural", "city": "demo", "year": None})
            dataset_log = root / "outputs/demo/logs/cli_runs.jsonl"
            failed_once = False

            def flaky_append(path: Path, record: dict) -> None:
                nonlocal failed_once
                if path == dataset_log and not failed_once:
                    failed_once = True
                    raise OSError("simulated dataset log failure")
                _append_jsonl(path, record)

            with patch("ic.provenance._append_jsonl", side_effect=flaky_append):
                with self.assertRaises(OSError):
                    recorder.finish("success")
                retried = recorder.finish("failure", ValueError("must be ignored on retry"))

            global_rows = _jsonl_rows(root / "outputs/experiments/cli_runs.jsonl")
            dataset_rows = _jsonl_rows(dataset_log)
            self.assertEqual(len(global_rows), 1)
            self.assertEqual(len(dataset_rows), 1)
            self.assertEqual(global_rows[0], dataset_rows[0])
            self.assertEqual(retried, global_rows[0])
            self.assertEqual(retried["status"], "success")
            self.assertIsNone(retried["error"])

    def test_invalid_argparse_value_is_persisted_with_useful_message(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            stderr = io.StringIO()
            try:
                os.chdir(root)
                with (
                    patch.object(
                        sys,
                        "argv",
                        ["ic", "structural", "--city", "demo", "--samples", "bad"],
                    ),
                    redirect_stderr(stderr),
                    self.assertRaises(SystemExit) as raised,
                ):
                    main()
                row = _jsonl_rows(root / "outputs/experiments/cli_runs.jsonl")[-1]
            finally:
                os.chdir(original_cwd)

        expected = "argument --samples: invalid int value: 'bad'"
        self.assertEqual(raised.exception.code, 2)
        self.assertIn(expected, stderr.getvalue())
        self.assertEqual(row["status"], "failure")
        self.assertEqual(row["command"], "structural")
        self.assertEqual(row["error"]["message"], expected)
        self.assertEqual(row["error"]["system_exit_message"], "2")
        self.assertEqual(row["error"]["exit_code"], 2)


if __name__ == "__main__":
    unittest.main()
