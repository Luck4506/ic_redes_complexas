from __future__ import annotations

import os
import unittest
from pathlib import Path
import sys

import networkx as nx

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.metric_graphs import approximate_global_efficiency, simple_undirected_min_length_graph
from ic.community_resilience import _build_community_graph
from ic.intra_community_resilience import _normalized_auc, _simulate_community


class MetricPrecisionTests(unittest.TestCase):
    def test_efficiency_counts_disconnected_pairs_as_zero(self) -> None:
        G = nx.Graph()
        G.add_edges_from([(0, 1), (1, 2)])
        G.add_node(3)

        self.assertAlmostEqual(approximate_global_efficiency(G, samples=10), 5 / 12)

    def test_weighted_efficiency_uses_same_disconnected_denominator(self) -> None:
        G = nx.Graph()
        G.add_edge(0, 1, length=10.0)
        G.add_node(2)

        self.assertAlmostEqual(approximate_global_efficiency(G, samples=10, weight="length"), 0.2 / 6)

    def test_simple_graph_keeps_shortest_parallel_length(self) -> None:
        G = nx.MultiDiGraph()
        G.add_node(1, x=0, y=0)
        G.add_node(2, x=1, y=1)
        G.add_edge(1, 2, length=20.0)
        G.add_edge(2, 1, length=5.0)

        Gu = simple_undirected_min_length_graph(G)

        self.assertEqual(Gu.number_of_edges(), 1)
        self.assertEqual(Gu[1][2]["length"], 5.0)

    def test_build_community_graph_aggregates_intercommunity_edges(self) -> None:
        G = nx.Graph()
        G.add_edge("a", "b", length=10.0)
        G.add_edge("b", "c", length=20.0)
        G.add_edge("c", "d", length=30.0)
        mapping = {"a": 1, "b": 1, "c": 2, "d": 3}

        C, rows, sizes = _build_community_graph(G, mapping, min_size=1)

        self.assertEqual(C.number_of_nodes(), 3)
        self.assertEqual(C.number_of_edges(), 2)
        self.assertEqual(C[1][2]["edge_count"], 1)
        self.assertEqual(C[1][2]["total_length_m"], 20.0)
        self.assertEqual(sizes[1], 2)
        row_by_id = {row["community_id"]: row for row in rows}
        self.assertEqual(row_by_id[1]["internal_edges"], 1)

    def test_normalized_auc_for_linear_curve(self) -> None:
        records = [
            {"removed_fraction": 0.0, "lcc_fraction": 1.0},
            {"removed_fraction": 0.5, "lcc_fraction": 0.5},
            {"removed_fraction": 1.0, "lcc_fraction": 0.0},
        ]

        self.assertAlmostEqual(_normalized_auc(records, "lcc_fraction"), 0.5)

    def test_intra_community_simulation_stays_within_subgraph(self) -> None:
        G = nx.path_graph(5)
        nx.set_edge_attributes(G, 1.0, "length")

        records, summary = _simulate_community(
            community_id=7,
            G0=G,
            strategy="targeted",
            max_fraction=0.5,
            steps=3,
            k_edge=5,
            efficiency_samples=5,
            seed=42,
        )

        self.assertTrue(all(row["community_id"] == 7 for row in records))
        self.assertEqual(summary["nodes"], 5)
        self.assertEqual(summary["internal_edges"], 4)
        self.assertEqual(summary["tested_removed_edges"], 2)
        self.assertLess(summary["final_lcc_fraction"], 1.0)


if __name__ == "__main__":
    unittest.main()
