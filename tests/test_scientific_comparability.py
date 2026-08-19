from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.scientific_comparability import (
    CONFIRMED,
    INCOMPARABLE,
    NOT_PROVEN,
    auditar_comparabilidade_cientifica,
)


ARTIFACT = "metrics/structural_metrics.csv"
COMMIT = "a" * 40
DIFF_HASH = "b" * 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ScientificComparabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_cwd = Path.cwd()
        self._temporary = tempfile.TemporaryDirectory()
        os.chdir(self._temporary.name)

    def tearDown(self) -> None:
        os.chdir(self._original_cwd)
        self._temporary.cleanup()

    def _build_dataset(self, dataset: str, *, snapshot: str = "2026-06-01T00:00:00Z") -> None:
        raw = Path(f"data/graphs/{dataset}_drive_raw.graphml")
        clean = Path(f"data/graphs/{dataset}_drive_clean.graphml")
        metadata = Path(f"data/metadata/{dataset}_drive_raw.json")
        artifact = Path("outputs") / dataset / ARTIFACT
        config = Path(f"config/{dataset}.yaml")
        log = Path(f"outputs/{dataset}/logs/cli_runs.jsonl")
        for path in (raw, clean, metadata, artifact, config, log):
            path.parent.mkdir(parents=True, exist_ok=True)

        raw.write_text('<?xml version="1.0"?><graphml><graph id="raw"/></graphml>', encoding="utf-8")
        clean.write_text('<?xml version="1.0"?><graphml><graph id="clean"/></graphml>', encoding="utf-8")
        artifact.write_text("metric,value\nnodes,2\n", encoding="utf-8")
        config.write_text(f"city_id: {dataset}\nnetwork_type: drive\nsimplify: true\n", encoding="utf-8")

        relation = 1000 + sum(ord(character) for character in dataset)
        geometry_hash = hashlib.sha256(f"geometry:{dataset}".encode()).hexdigest()
        metadata.write_text(
            json.dumps(
                {
                    "city_id": dataset,
                    "dataset_id": dataset,
                    "created_at": "2026-06-02T12:00:00",
                    "network_type": "drive",
                    "simplify": True,
                    "snapshot_timestamp_utc": snapshot,
                    "clip": {
                        "mode": "place",
                        "query": f"{dataset}, Brazil",
                        "boundary_geometry_sha256": geometry_hash,
                        "boundary_identity_sha256": geometry_hash,
                        "osm_boundary": {
                            "available": True,
                            "element_type": "relation",
                            "osm_id": relation,
                            "relation_id": relation,
                        },
                    },
                    "boundary_geometry_sha256": geometry_hash,
                    "boundary_identity_sha256": geometry_hash,
                    "osm_boundary": {
                        "available": True,
                        "element_type": "relation",
                        "osm_id": relation,
                        "relation_id": relation,
                    },
                    "nodes": 2,
                    "edges": 1,
                    "crs": "epsg:4326",
                    "graph_hashes": {"raw": _sha256(raw), "clean": _sha256(clean)},
                }
            ),
            encoding="utf-8",
        )

        record = {
            "schema_version": "1.0",
            "run_id": f"run-{dataset}",
            "argv": ["ic", "structural", "--city", dataset, "--seed", "42"],
            "command": "structural",
            "command_line": f"ic structural --city {dataset} --seed 42",
            "parameters": {"cmd": "structural", "city": dataset, "samples": 30, "seed": 42},
            "status": "success",
            "datasets": [dataset],
            "git": {"commit": COMMIT, "dirty": False, "diff_sha256": DIFF_HASH},
            "inputs": [
                {"path": raw.as_posix(), "sha256": _sha256(raw)},
                {"path": clean.as_posix(), "sha256": _sha256(clean)},
                {"path": config.as_posix(), "sha256": _sha256(config)},
            ],
            "artifacts": [{"path": artifact.as_posix(), "sha256": _sha256(artifact)}],
        }
        log.write_text(json.dumps(record) + "\n", encoding="utf-8")

    def test_scientific_profile_confirms_only_complete_matching_evidence(self) -> None:
        self._build_dataset("alpha")
        self._build_dataset("beta")

        result = auditar_comparabilidade_cientifica(
            ["alpha", "beta"],
            required_artifacts=[ARTIFACT],
        )

        self.assertEqual(result["state"], CONFIRMED)
        self.assertEqual({row["state"] for row in result["dataset_rows"]}, {CONFIRMED})
        self.assertEqual(result["pair_rows"][0]["state"], CONFIRMED)
        for key in ("criteria_csv", "datasets_csv", "pairs_csv", "report_txt"):
            self.assertTrue(Path(result[key]).is_file())

        with Path(result["criteria_csv"]).open(newline="", encoding="utf-8") as stream:
            criteria = list(csv.DictReader(stream))
        self.assertTrue(criteria)
        self.assertLessEqual({row["state"] for row in criteria}, {CONFIRMED, NOT_PROVEN, INCOMPARABLE})
        self.assertFalse(any(row["state"].lower() in {"true", "false", "sim", "nao"} for row in criteria))

    def test_current_placeholder_is_not_accepted_but_exploratory_is_separate(self) -> None:
        self._build_dataset("alpha", snapshot="OSM_atual")
        self._build_dataset("beta", snapshot="OSM_atual")

        scientific = auditar_comparabilidade_cientifica(
            ["alpha", "beta"],
            required_artifacts=[ARTIFACT],
        )
        exploratory = auditar_comparabilidade_cientifica(
            ["alpha", "beta"],
            perfil="exploratorio",
            required_artifacts=[ARTIFACT],
        )

        self.assertEqual(scientific["state"], NOT_PROVEN)
        self.assertEqual(exploratory["state"], CONFIRMED)
        self.assertNotEqual(scientific["criteria_csv"], exploratory["criteria_csv"])
        self.assertIn("exploratory_comparability", exploratory["report_txt"])

        snapshot_rows = [
            row
            for row in scientific["dataset_rows"]
            if row["osm_snapshot_timestamp"]
        ]
        self.assertEqual(snapshot_rows, [])

    def test_explicit_snapshot_mismatch_makes_pair_incomparable(self) -> None:
        self._build_dataset("alpha", snapshot="2026-06-01T00:00:00Z")
        self._build_dataset("beta", snapshot="2026-06-02T00:00:00Z")

        result = auditar_comparabilidade_cientifica(
            ["alpha", "beta"],
            required_artifacts=[ARTIFACT],
        )
        longitudinal = auditar_comparabilidade_cientifica(
            ["alpha", "beta"],
            output_dir="outputs/longitudinal-comparison",
            required_artifacts=[ARTIFACT],
            snapshot_policy="documented",
        )

        self.assertEqual({row["state"] for row in result["dataset_rows"]}, {CONFIRMED})
        self.assertEqual(result["pair_rows"][0]["state"], INCOMPARABLE)
        self.assertEqual(result["state"], INCOMPARABLE)
        self.assertEqual(longitudinal["state"], CONFIRMED)

    def test_bbox_parameters_supply_boundary_identity_without_geometry_hash(self) -> None:
        for dataset in ("alpha", "beta"):
            self._build_dataset(dataset)
            metadata_path = Path(f"data/metadata/{dataset}_drive_raw.json")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["clip"] = {
                "mode": "bbox",
                "north": -22.0,
                "south": -22.5,
                "east": -46.5 + (0.1 if dataset == "beta" else 0.0),
                "west": -47.0 + (0.1 if dataset == "beta" else 0.0),
            }
            metadata.pop("boundary_geometry_sha256", None)
            metadata.pop("boundary_identity_sha256", None)
            metadata.pop("osm_boundary", None)
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        result = auditar_comparabilidade_cientifica(
            ["alpha", "beta"],
            required_artifacts=[ARTIFACT],
        )

        self.assertEqual(result["state"], CONFIRMED)
        self.assertTrue(
            all(row["boundary_identity_sha256"] for row in result["dataset_rows"])
        )

    def test_bbox_declared_identity_mismatch_is_incomparable(self) -> None:
        self._build_dataset("alpha")
        metadata_path = Path("data/metadata/alpha_drive_raw.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["clip"] = {
            "mode": "bbox",
            "north": -22.0,
            "south": -22.5,
            "east": -46.5,
            "west": -47.0,
        }
        metadata.pop("boundary_geometry_sha256", None)
        metadata["boundary_identity_sha256"] = "f" * 64
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        result = auditar_comparabilidade_cientifica(
            ["alpha"],
            required_artifacts=[ARTIFACT],
        )

        with Path(result["criteria_csv"]).open(encoding="utf-8", newline="") as handle:
            criteria_rows = list(csv.DictReader(handle))
        identity = next(
            row
            for row in criteria_rows
            if row["criterion"] == "boundary_identity_hash"
        )
        self.assertEqual(identity["state"], INCOMPARABLE)
        self.assertEqual(result["state"], INCOMPARABLE)

    def test_place_identity_must_match_geometry_hash(self) -> None:
        self._build_dataset("alpha")
        metadata_path = Path("data/metadata/alpha_drive_raw.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["boundary_identity_sha256"] = "f" * 64
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        result = auditar_comparabilidade_cientifica(
            ["alpha"],
            required_artifacts=[ARTIFACT],
        )

        with Path(result["criteria_csv"]).open(encoding="utf-8", newline="") as handle:
            criteria_rows = list(csv.DictReader(handle))
        identity = next(
            row
            for row in criteria_rows
            if row["criterion"] == "boundary_identity_hash"
        )
        self.assertEqual(identity["state"], INCOMPARABLE)
        self.assertEqual(result["state"], INCOMPARABLE)

    def test_changed_artifact_hash_is_incomparable_not_merely_missing(self) -> None:
        self._build_dataset("alpha")
        self._build_dataset("beta")
        Path("outputs/alpha/metrics/structural_metrics.csv").write_text(
            "metric,value\nnodes,999\n",
            encoding="utf-8",
        )

        result = auditar_comparabilidade_cientifica(
            ["alpha", "beta"],
            required_artifacts=[ARTIFACT],
        )

        alpha = next(row for row in result["dataset_rows"] if row["dataset"] == "alpha")
        self.assertEqual(alpha["state"], INCOMPARABLE)
        self.assertEqual(result["pair_rows"][0]["state"], INCOMPARABLE)


if __name__ == "__main__":
    unittest.main()
