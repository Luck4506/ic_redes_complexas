from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

import networkx as nx

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.community_resilience import _community_lcc_stats


class CommunityResilienceRegressionTests(unittest.TestCase):
    def test_weighted_lcc_can_differ_from_lcc_by_community_count(self) -> None:
        graph = nx.Graph()
        graph.add_node("small_a", size=1)
        graph.add_node("small_b", size=1)
        graph.add_edge("small_a", "small_b")
        graph.add_node("large", size=100)

        lcc_communities, components, lcc_weighted_fraction = _community_lcc_stats(graph)

        self.assertEqual(lcc_communities, 2)
        self.assertEqual(components, 2)
        self.assertAlmostEqual(lcc_weighted_fraction, 100 / 102)


if __name__ == "__main__":
    unittest.main()
