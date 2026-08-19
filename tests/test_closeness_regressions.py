from __future__ import annotations

import unittest

import networkx as nx

from ic.centrality import approximate_closeness_centrality


class ClosenessRegressionTests(unittest.TestCase):
    def test_all_landmarks_match_networkx_on_disconnected_graph(self) -> None:
        graph = nx.Graph([(0, 1), (1, 2), (3, 4)])

        approximate = approximate_closeness_centrality(graph, samples=99)
        exact = nx.closeness_centrality(graph)

        for node in graph:
            self.assertAlmostEqual(approximate[node], exact[node])

    def test_isolated_node_is_zero_instead_of_dividing_by_empty_sample(self) -> None:
        graph = nx.Graph([(0, 1)])
        graph.add_node(2)

        result = approximate_closeness_centrality(graph, samples=99)

        self.assertEqual(result[2], 0.0)
        self.assertAlmostEqual(result[0], 0.5)
        self.assertAlmostEqual(result[1], 0.5)


if __name__ == "__main__":
    unittest.main()
