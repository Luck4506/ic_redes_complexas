from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import networkx as nx

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.node_resilience import testar_resiliencia_vertices
from ic.random_resilience_stats import (
    _aggregate_rows,
    _auc_rows,
    _normalized_auc,
    _resolve_attack_seeds,
)
from ic.resilience import testar_resiliencia


class RandomResilienceStatisticsTests(unittest.TestCase):
    def test_master_seed_generates_thirty_unique_reproducible_attack_seeds(self) -> None:
        first = _resolve_attack_seeds(None, 30, 123)
        second = _resolve_attack_seeds(None, 30, 123)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 30)
        self.assertEqual(len(set(first)), 30)

    def test_explicit_seeds_and_repetitions_are_mutually_exclusive(self) -> None:
        with self.assertRaisesRegex(ValueError, "não ambos"):
            _resolve_attack_seeds([1, 2], 30, 42)

    def test_aggregate_adds_bootstrap_interval_and_distribution_statistics(self) -> None:
        rows = []
        for seed, lcc in [(10, 0.8), (20, 1.0), (30, 0.9)]:
            rows.append(
                {
                    "step_index": 1,
                    "attack_seed": seed,
                    "removed_fraction": 0.1,
                    "lcc_fraction": lcc,
                    "num_components": 2,
                    "efficiency_topological_retained": lcc - 0.1,
                    "efficiency_length_retained": lcc - 0.05,
                }
            )

        aggregate = _aggregate_rows(rows, bootstrap_resamples=500, bootstrap_seed=7)[0]

        self.assertAlmostEqual(aggregate["lcc_fraction_mean"], 0.9)
        self.assertAlmostEqual(aggregate["lcc_fraction_median"], 0.9)
        self.assertGreater(aggregate["lcc_fraction_std"], 0)
        self.assertGreater(aggregate["lcc_fraction_sem"], 0)
        self.assertLessEqual(aggregate["lcc_fraction_ci95_bootstrap_low"], 0.9)
        self.assertGreaterEqual(aggregate["lcc_fraction_ci95_bootstrap_high"], 0.9)
        self.assertEqual(aggregate["uncertainty_available"], "yes")
        self.assertEqual(aggregate["meets_recommended_runs"], "no")

    def test_single_run_does_not_report_zero_as_estimated_uncertainty(self) -> None:
        row = {
            "step_index": 0,
            "removed_fraction": 0.0,
            "lcc_fraction": 1.0,
            "num_components": 1,
            "efficiency_topological_retained": 1.0,
            "efficiency_length_retained": 1.0,
        }

        aggregate = _aggregate_rows([row], bootstrap_resamples=100)[0]

        self.assertEqual(aggregate["lcc_fraction_std"], "")
        self.assertEqual(aggregate["lcc_fraction_ci95_bootstrap_low"], "")
        self.assertEqual(aggregate["uncertainty_available"], "no")

    def test_auc_is_normalized_over_observed_fraction(self) -> None:
        rows = [
            {"removed_fraction": 0.0, "lcc_fraction": 1.0},
            {"removed_fraction": 0.5, "lcc_fraction": 0.5},
            {"removed_fraction": 1.0, "lcc_fraction": 0.0},
        ]

        self.assertAlmostEqual(_normalized_auc(rows, "lcc_fraction"), 0.5)

    def test_auc_summary_has_bootstrap_interval_across_runs(self) -> None:
        rows = []
        for attack_seed, final_value in [(1, 0.4), (2, 0.6), (3, 0.8)]:
            for step, (fraction, lcc) in enumerate([(0.0, 1.0), (0.1, final_value)]):
                rows.append(
                    {
                        "step_index": step,
                        "attack_seed": attack_seed,
                        "evaluation_seed": 99,
                        "removed_fraction": fraction,
                        "lcc_fraction": lcc,
                        "efficiency_topological_retained": lcc,
                        "efficiency_length_retained": lcc,
                    }
                )

        summaries = [row for row in _auc_rows(rows, 500, 3) if row["row_type"] == "summary"]

        self.assertEqual(len(summaries), 3)
        self.assertTrue(all(row["runs"] == 3 for row in summaries))
        self.assertTrue(all(row["ci95_bootstrap_low"] != "" for row in summaries))

    @staticmethod
    def _road_graph() -> nx.MultiDiGraph:
        graph = nx.MultiDiGraph()
        for node in range(5):
            graph.add_node(node, x=float(node), y=float(node))
        for node in range(4):
            graph.add_edge(node, node + 1, length=10.0)
            graph.add_edge(node + 1, node, length=10.0)
        return graph

    def test_edge_attack_seed_is_independent_from_evaluation_seed(self) -> None:
        seen_seeds: list[int] = []

        def fake_efficiency(_graph, samples=20, seed=42, weight=None):
            del samples, weight
            seen_seeds.append(seed)
            return 1.0

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "ic.resilience.load_graphml", return_value=self._road_graph()
        ), patch("ic.resilience.approximate_global_efficiency", side_effect=fake_efficiency):
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                testar_resiliencia(
                    "demo",
                    strategy="random",
                    max_fraction=0.25,
                    steps=2,
                    seed=7,
                    evaluation_seed=99,
                )
            finally:
                os.chdir(previous)

        self.assertTrue(seen_seeds)
        self.assertEqual(set(seen_seeds), {99})

    def test_node_attack_seed_is_independent_from_evaluation_seed(self) -> None:
        seen_seeds: list[int] = []

        def fake_efficiency(_graph, _original_nodes, _samples, seed, **_kwargs):
            seen_seeds.append(seed)
            return 1.0

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "ic.node_resilience.load_graphml", return_value=self._road_graph()
        ), patch("ic.node_resilience._efficiency_on_original_nodes", side_effect=fake_efficiency):
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                testar_resiliencia_vertices(
                    "demo",
                    strategy="random",
                    max_fraction=0.25,
                    steps=2,
                    seed=7,
                    evaluation_seed=99,
                )
            finally:
                os.chdir(previous)

        self.assertTrue(seen_seeds)
        self.assertEqual(set(seen_seeds), {99})


if __name__ == "__main__":
    unittest.main()
