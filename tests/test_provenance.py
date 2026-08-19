from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ic.provenance import _append_jsonl, begin_cli_run, git_worktree_state


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class CliRunRecorderTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git"), "git não disponível")
    def test_git_fingerprint_changes_with_untracked_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            tracked = root / "tracked.txt"
            tracked.write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)

            untracked = root / "new_module.py"
            untracked.write_text("VALUE = 1\n", encoding="utf-8")
            first = git_worktree_state(root)["diff_sha256"]
            untracked.write_text("VALUE = 2\n", encoding="utf-8")
            second = git_worktree_state(root)["diff_sha256"]

            self.assertNotEqual(first, second)

    def test_download_dataset_is_resolved_from_historical_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config/demo.yaml"
            config.parent.mkdir(parents=True)
            config.write_text(
                "city_id: demo\nhistorical_date: 2019-02-03\nnetwork_type: drive\n",
                encoding="utf-8",
            )
            recorder = begin_cli_run(["ic", "download", "--config", "config/demo.yaml"], cwd=root)
            recorder.set_parsed_args(
                argparse.Namespace(
                    cmd="download",
                    city=None,
                    config="config/demo.yaml",
                    year=None,
                )
            )

            record = recorder.finish("success")

            self.assertEqual(record["datasets"], ["demo_2019-02-03"])
            self.assertTrue(
                (root / "outputs/demo_2019-02-03/logs/cli_runs.jsonl").is_file()
            )

    def test_download_year_uses_city_not_custom_dataset_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config/demo.yaml"
            config.parent.mkdir(parents=True)
            config.write_text(
                "city_id: demo\ndataset_id: custom\nnetwork_type: drive\n",
                encoding="utf-8",
            )
            recorder = begin_cli_run(
                ["ic", "download", "--config", "config/demo.yaml", "--year", "2020"],
                cwd=root,
            )
            recorder.set_parsed_args(
                argparse.Namespace(
                    cmd="download",
                    city=None,
                    config="config/demo.yaml",
                    year=2020,
                )
            )

            record = recorder.finish("success")

            self.assertEqual(record["datasets"], ["demo_2020"])

    def test_historical_audit_includes_reference_in_logs_and_input_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for dataset in ("demo", "demo_2019"):
                graph = root / f"data/graphs/{dataset}_drive_clean.graphml"
                metadata = root / f"data/metadata/{dataset}_drive_raw.json"
                graph.parent.mkdir(parents=True, exist_ok=True)
                metadata.parent.mkdir(parents=True, exist_ok=True)
                graph.write_text("<graphml/>", encoding="utf-8")
                metadata.write_text(
                    json.dumps(
                        {
                            "dataset_id": dataset,
                            "city_id": "demo",
                            "network_type": "drive",
                        }
                    ),
                    encoding="utf-8",
                )

            recorder = begin_cli_run(
                ["ic", "historical-audit", "--reference", "demo", "demo_2019"],
                cwd=root,
            )
            recorder.set_parsed_args(
                argparse.Namespace(
                    cmd="historical-audit",
                    reference="demo",
                    datasets=["demo_2019"],
                    output_dir="outputs/comparisons",
                )
            )

            record = recorder.finish("success")
            input_paths = {item["path"] for item in record["inputs"]}

            self.assertEqual(record["datasets"], ["demo_2019", "demo"])
            self.assertIn("data/graphs/demo_drive_clean.graphml", input_paths)
            self.assertIn("data/graphs/demo_2019_drive_clean.graphml", input_paths)
            self.assertIn("data/metadata/demo_drive_raw.json", input_paths)
            self.assertIn("data/metadata/demo_2019_drive_raw.json", input_paths)
            self.assertTrue((root / "outputs/demo/logs/cli_runs.jsonl").is_file())
            self.assertTrue((root / "outputs/demo_2019/logs/cli_runs.jsonl").is_file())

    def test_jsonl_append_is_idempotent_by_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            record = {"run_id": "same-run", "status": "success"}
            _append_jsonl(path, record)
            _append_jsonl(path, record)
            self.assertEqual(len(_read_jsonl(path)), 1)

    def test_success_records_defaults_input_and_created_artifact_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config" / "demo.yaml"
            metadata = root / "data" / "metadata" / "demo_drive_raw.json"
            graph = root / "data" / "graphs" / "demo_drive_clean.graphml"
            config.parent.mkdir(parents=True)
            metadata.parent.mkdir(parents=True)
            graph.parent.mkdir(parents=True, exist_ok=True)
            config_payload = b"city_id: demo\nnetwork_type: drive\n"
            metadata_payload = b'{"dataset": "demo"}\n'
            graph_payload = b"<graphml><graph id=\"demo\"/></graphml>\n"
            config.write_bytes(config_payload)
            metadata.write_bytes(metadata_payload)
            graph.write_bytes(graph_payload)

            recorder = begin_cli_run(
                ["ic", "structural", "--city", "demo"],
                cwd=root,
            )
            recorder.set_parsed_args(
                argparse.Namespace(
                    cmd="structural",
                    city="demo",
                    year=None,
                    samples=30,
                    seed=42,
                    config=None,
                )
            )

            artifact = root / "outputs" / "demo" / "metrics" / "result.csv"
            artifact.parent.mkdir(parents=True)
            artifact_payload = b"metric,value\nnodes,3\n"
            artifact.write_bytes(artifact_payload)
            record = recorder.finish("success")

            self.assertEqual(record["status"], "success")
            self.assertIsNone(record["error"])
            self.assertEqual(record["command"], "structural")
            self.assertEqual(record["datasets"], ["demo"])
            # Estes valores não aparecem no argv: vieram dos defaults já
            # materializados pelo argparse.Namespace.
            self.assertEqual(record["parameters"]["samples"], 30)
            self.assertEqual(record["parameters"]["seed"], 42)

            inputs = {item["path"]: item for item in record["inputs"]}
            self.assertEqual(inputs["config/demo.yaml"]["sha256"], _sha256(config_payload))
            self.assertEqual(
                inputs["data/metadata/demo_drive_raw.json"]["sha256"],
                _sha256(metadata_payload),
            )
            self.assertEqual(
                inputs["data/graphs/demo_drive_clean.graphml"]["sha256"],
                _sha256(graph_payload),
            )
            self.assertGreater(inputs["config/demo.yaml"]["mtime_ns"], 0)

            artifacts = {item["path"]: item for item in record["artifacts"]}
            self.assertEqual(artifacts["outputs/demo/metrics/result.csv"]["change"], "created")
            self.assertEqual(
                artifacts["outputs/demo/metrics/result.csv"]["sha256"],
                _sha256(artifact_payload),
            )
            self.assertFalse(any(item["path"].endswith("cli_runs.jsonl") for item in record["artifacts"]))

            global_log = root / "outputs" / "experiments" / "cli_runs.jsonl"
            dataset_log = root / "outputs" / "demo" / "logs" / "cli_runs.jsonl"
            self.assertEqual(_read_jsonl(global_log)[0]["run_id"], recorder.run_id)
            self.assertEqual(_read_jsonl(dataset_log)[0]["run_id"], recorder.run_id)
            self.assertEqual(recorder.finish("ignored")["run_id"], recorder.run_id)
            self.assertEqual(len(_read_jsonl(global_log)), 1)

    def test_failure_records_error_and_modified_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "outputs" / "demo_2021" / "metrics" / "existing.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"before")

            recorder = begin_cli_run(["ic", "resilience", "--city", "demo", "--year", "2021"], cwd=root)
            recorder.set_parsed_args(
                {
                    "cmd": "resilience",
                    "city": "demo",
                    "year": 2021,
                    "strategy": "targeted",
                    "steps": 15,
                }
            )

            changed_payload = b"after-with-more-content"
            artifact.write_bytes(changed_payload)
            record = recorder.finish("failure", ValueError("boom"))

            self.assertEqual(record["datasets"], ["demo_2021"])
            self.assertEqual(record["status"], "failure")
            self.assertEqual(record["error"]["type"], "builtins.ValueError")
            self.assertEqual(record["error"]["message"], "boom")
            self.assertGreaterEqual(record["duration_seconds"], record["execution_duration_seconds"])

            artifacts = {item["path"]: item for item in record["artifacts"]}
            changed = artifacts["outputs/demo_2021/metrics/existing.txt"]
            self.assertEqual(changed["change"], "modified")
            self.assertEqual(changed["sha256"], _sha256(changed_payload))

            dataset_log = root / "outputs" / "demo_2021" / "logs" / "cli_runs.jsonl"
            persisted = _read_jsonl(dataset_log)[0]
            self.assertEqual(persisted["status"], "failure")
            self.assertEqual(persisted["error"]["message"], "boom")


if __name__ == "__main__":
    unittest.main()
