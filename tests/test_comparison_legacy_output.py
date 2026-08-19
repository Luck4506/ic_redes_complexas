from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

from ic.cli import _main
from ic.comparison_protocol import LEGACY_FIELDS, write_legacy_comparison_csv


@contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class ComparisonLegacyOutputTests(unittest.TestCase):
    def test_legacy_schema_is_preserved_but_comparable_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory, _working_directory(Path(directory)):
            metadata = Path("data/metadata/demo_drive_raw.json")
            metadata.parent.mkdir(parents=True)
            metadata.write_text(
                json.dumps(
                    {
                        "historical_date": "2020-01-01",
                        "nodes": 10,
                        "edges": 12,
                        "clip": {
                            "mode": "bbox",
                            "north": -22.0,
                            "south": -22.1,
                            "east": -47.0,
                            "west": -47.1,
                        },
                    }
                ),
                encoding="utf-8",
            )
            metrics = Path("outputs/demo/metrics")
            metrics.mkdir(parents=True)
            for name in (
                "structural_metrics.csv",
                "node_centralities.csv",
                "functional_topology_correlations.csv",
                "approximation_validation.csv",
            ):
                (metrics / name).write_text("metric,value\n", encoding="utf-8")

            result = {
                "state": "confirmada",
                "datasets_csv": "outputs/comparisons/scientific_comparability_datasets.csv",
                "dataset_rows": [
                    {
                        "dataset": "demo",
                        "metadata_path": metadata.as_posix(),
                        "network_type": "drive",
                    }
                ],
            }
            legacy = write_legacy_comparison_csv(
                ["demo"], result, "outputs/comparisons/legacy.csv"
            )

            with Path(legacy["path"]).open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                self.assertEqual(tuple(reader.fieldnames or ()), LEGACY_FIELDS)
            self.assertEqual(rows[0]["historical_date"], "2020-01-01")
            self.assertEqual(rows[0]["raw_nodes"], "10")
            self.assertEqual(rows[0]["required_outputs_complete"], "sim")
            self.assertEqual(rows[0]["comparison_status"], "comparavel")
            self.assertEqual(legacy["scientific_state"], "confirmada")

    def test_cli_output_uses_legacy_writer_and_keeps_scientific_state(self) -> None:
        result = {
            "state": "confirmada",
            "criteria_csv": "criteria.csv",
            "datasets_csv": "datasets.csv",
            "pairs_csv": "pairs.csv",
            "report_txt": "report.txt",
            "dataset_rows": [{"dataset": "demo", "state": "confirmada"}],
        }
        recorder = Mock()
        argv = ["ic", "comparison-audit", "demo", "--output", "legacy.csv"]
        with (
            patch.object(sys, "argv", argv),
            patch("ic.cli.auditar_comparabilidade_cientifica", return_value=result),
            patch("ic.cli.write_legacy_comparison_csv") as legacy_writer,
        ):
            _main(recorder)

        legacy_writer.assert_called_once_with(["demo"], result, "legacy.csv")


if __name__ == "__main__":
    unittest.main()
