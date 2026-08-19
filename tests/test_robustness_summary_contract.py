from __future__ import annotations

import csv
import os
from pathlib import Path
import sys
import tempfile
import unittest

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.robustness_summary import (
    MODALITIES,
    STRATEGIES,
    _summarize,
    gerar_sintese_robustez,
)


class RobustnessSummaryContractTests(unittest.TestCase):
    @staticmethod
    def _write_curve(path: Path, modality: str, include_weighted_lcc: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for fraction, retained in [(0.0, 1.0), (0.1, 0.8)]:
            row = {
                "removed_fraction": fraction,
                "lcc_fraction": retained,
                "lcc_communities_fraction": retained,
                "lcc_weighted_fraction": retained,
                "efficiency_topological_retained": retained,
                "efficiency_length_retained": retained,
            }
            if not include_weighted_lcc:
                row.pop("lcc_weighted_fraction")
                row["lcc_nodes_fraction"] = retained
            rows.append(row)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def _write_complete_matrix(self, root: Path, dataset: str = "demo") -> None:
        for modality, definition in MODALITIES.items():
            prefix = definition["prefix"]
            for strategy in STRATEGIES:
                self._write_curve(
                    root / f"outputs/{dataset}/metrics/{prefix}_curve_{strategy}.csv",
                    modality,
                )

    def test_custom_output_directory_isolates_city_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_complete_matrix(root)
            previous = Path.cwd()
            os.chdir(root)
            try:
                result = gerar_sintese_robustez(
                    ["demo"],
                    output_dir="isolated",
                    checkpoints=[0.05],
                    thresholds=[0.90],
                )
            finally:
                os.chdir(previous)

            self.assertFalse((root / "outputs/demo/metrics/robustness_summary.csv").exists())
            self.assertTrue((root / "isolated/datasets/demo/metrics/robustness_summary.csv").exists())
            self.assertEqual(result["city_output_root"], "isolated/datasets")

    def test_one_percent_checkpoint_still_generates_loss_figures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_complete_matrix(root)
            previous = Path.cwd()
            os.chdir(root)
            try:
                result = gerar_sintese_robustez(
                    ["demo"],
                    output_dir="isolated",
                    checkpoints=[0.01],
                    thresholds=[0.90],
                )
            finally:
                os.chdir(previous)

            self.assertTrue(Path(root / result["comparison_losses_plot"]).is_file())
            self.assertTrue(
                Path(root / result["city_outputs"]["demo"]["losses_plot"]).is_file()
            )

    def test_incomplete_matrix_fails_closed_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_curve(root / "outputs/demo/metrics/resilience_curve_random.csv", "edge")
            previous = Path.cwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(RuntimeError, "Matriz de curvas incompleta"):
                    gerar_sintese_robustez(["demo"], output_dir="isolated")
            finally:
                os.chdir(previous)

    def test_legacy_incorrect_community_curve_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_complete_matrix(root)
            legacy_path = root / "outputs/demo/metrics/community_resilience_curve_random.csv"
            self._write_curve(legacy_path, "community", include_weighted_lcc=False)
            previous = Path.cwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(RuntimeError, "lcc_weighted_fraction"):
                    gerar_sintese_robustez(["demo"], output_dir="isolated")
            finally:
                os.chdir(previous)

    def test_curve_without_zero_baseline_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_complete_matrix(root)
            path = root / "outputs/demo/metrics/resilience_curve_targeted.csv"
            rows = [
                {
                    "removed_fraction": 0.01,
                    "lcc_fraction": 1.0,
                    "lcc_communities_fraction": 1.0,
                    "lcc_weighted_fraction": 1.0,
                    "efficiency_topological_retained": 1.0,
                    "efficiency_length_retained": 1.0,
                },
                {
                    "removed_fraction": 0.1,
                    "lcc_fraction": 0.8,
                    "lcc_communities_fraction": 0.8,
                    "lcc_weighted_fraction": 0.8,
                    "efficiency_topological_retained": 0.8,
                    "efficiency_length_retained": 0.8,
                },
            ]
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            previous = Path.cwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(RuntimeError, "removed_fraction=0"):
                    gerar_sintese_robustez(["demo"], output_dir="isolated")
            finally:
                os.chdir(previous)

    def test_single_curve_marks_uncertainty_as_not_estimated(self) -> None:
        curves = {
            ("demo", "edge", "targeted"): [[
                {
                    "removed_fraction": "0.0",
                    "lcc_fraction": "1.0",
                    "efficiency_topological_retained": "1.0",
                    "efficiency_length_retained": "1.0",
                },
                {
                    "removed_fraction": "0.1",
                    "lcc_fraction": "0.8",
                    "efficiency_topological_retained": "0.7",
                    "efficiency_length_retained": "0.75",
                },
            ]]
        }

        rows = _summarize(curves, {"edge": 0.1}, [0.05], [0.9])

        self.assertTrue(rows)
        self.assertTrue(all(row["uncertainty_status"] == "not_estimated" for row in rows))
        self.assertTrue(all(row["auc_normalized_std"] == "" for row in rows))


if __name__ == "__main__":
    unittest.main()
