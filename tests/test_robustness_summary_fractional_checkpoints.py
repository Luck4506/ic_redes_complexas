from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from ic.robustness_summary import (  # noqa: E402
    _curve_contract_errors,
    _percentage_field_label,
    _summarize,
    _write_html,
)


class RobustnessSummaryFractionalCheckpointTests(unittest.TestCase):
    @staticmethod
    def _summary_rows(checkpoints: list[float]) -> list[dict[str, object]]:
        curves = {
            ("demo", "edge", "targeted"): [[
                {
                    "removed_fraction": 0.0,
                    "lcc_fraction": 1.0,
                    "efficiency_topological_retained": 1.0,
                    "efficiency_length_retained": 1.0,
                },
                {
                    "removed_fraction": 0.1,
                    "lcc_fraction": 0.0,
                    "efficiency_topological_retained": 0.0,
                    "efficiency_length_retained": 0.0,
                },
            ]]
        }
        return _summarize(curves, {"edge": 0.1}, checkpoints, [0.9])

    def test_fractional_percentages_have_distinct_fields(self) -> None:
        checkpoints = [0.011, 0.014, 0.05]
        lcc = next(
            row for row in self._summary_rows(checkpoints) if row["metric"] == "lcc"
        )

        self.assertEqual(_percentage_field_label(0.01), "1pct")
        self.assertEqual(_percentage_field_label(0.05), "5pct")
        self.assertEqual(_percentage_field_label(0.10), "10pct")
        self.assertEqual(_percentage_field_label(0.15), "15pct")
        self.assertEqual(_percentage_field_label(0.011), "1p1pct")
        self.assertEqual(_percentage_field_label(0.014), "1p4pct")

        self.assertAlmostEqual(float(lcc["loss_at_1p1pct_mean"]), 0.11)
        self.assertAlmostEqual(float(lcc["loss_at_1p4pct_mean"]), 0.14)
        self.assertAlmostEqual(float(lcc["loss_at_5pct_mean"]), 0.5)
        self.assertEqual(lcc["checkpoint_1p1pct_actual_fraction"], 0.011)
        self.assertEqual(lcc["checkpoint_1p4pct_actual_fraction"], 0.014)

    def test_html_uses_only_the_requested_checkpoint_columns(self) -> None:
        checkpoints = [0.011, 0.014, 0.05]
        rows = self._summary_rows(checkpoints)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "summary.html"
            _write_html(
                output,
                rows,
                root / "auc.png",
                root / "losses.png",
                checkpoints,
            )
            content = output.read_text(encoding="utf-8")

        self.assertIn("<th>Perda 1,1%</th>", content)
        self.assertIn("<th>Perda 1,4%</th>", content)
        self.assertIn("<th>Perda 5%</th>", content)
        self.assertNotIn("<th>Perda 10%</th>", content)
        self.assertNotIn("<th>Perda 15%</th>", content)
        self.assertIn("<td>0.1100</td>", content)
        self.assertIn("<td>0.1400</td>", content)
        self.assertIn("<td>0.5000</td>", content)

    def test_disconnected_community_baseline_is_valid_for_absolute_lcc(self) -> None:
        curves = {
            ("demo", "community", "targeted"): [[
                {
                    "removed_fraction": 0.0,
                    "lcc_weighted_fraction": 0.5,
                    "lcc_communities_fraction": 0.5,
                    "efficiency_topological_retained": 1.0,
                    "efficiency_length_retained": 1.0,
                },
                {
                    "removed_fraction": 0.1,
                    "lcc_weighted_fraction": 0.3,
                    "lcc_communities_fraction": 0.3,
                    "efficiency_topological_retained": 0.6,
                    "efficiency_length_retained": 0.7,
                },
            ]]
        }

        self.assertEqual(_curve_contract_errors(curves), [])
        rows = _summarize(curves, {"community": 0.1}, [0.05], [0.9])
        absolute_lcc_rows = [
            row for row in rows if row["metric"] in {"lcc", "lcc_communities"}
        ]
        self.assertEqual(len(absolute_lcc_rows), 2)
        self.assertTrue(
            all(
                abs(float(row["loss_at_5pct_mean"]) - 0.1) < 1e-12
                for row in absolute_lcc_rows
            )
        )

    def test_unit_baseline_remains_required_for_retained_and_clean_lcc(self) -> None:
        invalid_community = {
            ("demo", "community", "targeted"): [[
                {
                    "removed_fraction": 0.0,
                    "lcc_weighted_fraction": 0.5,
                    "lcc_communities_fraction": 0.5,
                    "efficiency_topological_retained": 0.9,
                    "efficiency_length_retained": 1.0,
                },
                {
                    "removed_fraction": 0.1,
                    "lcc_weighted_fraction": 0.3,
                    "lcc_communities_fraction": 0.3,
                    "efficiency_topological_retained": 0.6,
                    "efficiency_length_retained": 0.7,
                },
            ]]
        }
        invalid_edge = {
            ("demo", "edge", "targeted"): [[
                {
                    "removed_fraction": 0.0,
                    "lcc_fraction": 0.9,
                    "efficiency_topological_retained": 1.0,
                    "efficiency_length_retained": 1.0,
                },
                {
                    "removed_fraction": 0.1,
                    "lcc_fraction": 0.7,
                    "efficiency_topological_retained": 0.8,
                    "efficiency_length_retained": 0.8,
                },
            ]]
        }

        community_errors = _curve_contract_errors(invalid_community)
        edge_errors = _curve_contract_errors(invalid_edge)
        self.assertTrue(
            any("efficiency_topological_retained deve iniciar em 1" in error for error in community_errors)
        )
        self.assertTrue(any("lcc_fraction deve iniciar em 1" in error for error in edge_errors))


if __name__ == "__main__":
    unittest.main()
