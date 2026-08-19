from __future__ import annotations

import unittest

import networkx as nx

from ic.metric_graphs import collapsed_physical_length_m, edge_length_m


class MetricGraphContractTests(unittest.TestCase):
    def test_physical_proxy_does_not_double_count_reciprocal_arcs(self) -> None:
        graph = nx.MultiDiGraph()
        graph.add_edge("a", "b", length=10.0)
        graph.add_edge("b", "a", length=11.0)
        graph.add_edge("a", "b", length=8.0)
        graph.add_edge("b", "c", length=5.0)

        self.assertEqual(collapsed_physical_length_m(graph), 13.0)
        self.assertEqual(sum(float(data["length"]) for *_, data in graph.edges(data=True)), 34.0)

    def test_invalid_length_fails_instead_of_inventing_one_metre(self) -> None:
        for value in (None, "", "nan", -1, 0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    edge_length_m({"length": value})

        self.assertEqual(edge_length_m({}, default=0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
