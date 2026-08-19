from __future__ import annotations

import csv
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import networkx as nx

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.centrality import calcular_centralidades
from ic.structural_bottlenecks import _edge_rows as _build_structural_edge_rows
from ic.vulnerability_index import (
    _build_edge_rows as _build_vulnerability_edge_rows,
    _edge_key,
    _load_complete_edge_betweenness,
)


class EdgeCentralityContractTests(unittest.TestCase):
    def _graph(self) -> nx.MultiDiGraph:
        graph = nx.MultiDiGraph()
        for node in range(4):
            graph.add_node(node, x=float(node), y=float(node))
        graph.add_edge(0, 1, length=10.0, highway="residential")
        graph.add_edge(1, 2, length=20.0, highway="primary")
        graph.add_edge(2, 3, length=30.0, highway="secondary")
        return graph

    def _write_edge_centralities(
        self,
        root: Path,
        rows: list[tuple[object, object, object]],
        city_id: str = "fixture",
    ) -> Path:
        path = root / "outputs" / city_id / "metrics" / "edge_centralities.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["u", "v", "edge_betweenness"])
            writer.writerows(rows)
        return path

    def test_centrality_exports_all_edges_separately_from_top_ranking(self) -> None:
        graph = self._graph()
        with tempfile.TemporaryDirectory() as tmp, patch("ic.centrality.load_graphml", return_value=graph):
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                result = calcular_centralidades(
                    "fixture",
                    top_k=1,
                    k_betweenness=4,
                    k_edge_betweenness=4,
                    k_closeness=4,
                )
                with open(result["edge_centralities_csv"], newline="", encoding="utf-8") as f:
                    all_edges = list(csv.DictReader(f))
                with open(result["top_edges_csv"], newline="", encoding="utf-8") as f:
                    top_edges = list(csv.DictReader(f))
            finally:
                os.chdir(previous)

        self.assertEqual(len(all_edges), 3)
        self.assertEqual(len(top_edges), 1)
        self.assertEqual(
            {_edge_key(row["u"], row["v"]) for row in all_edges},
            {("0", "1"), ("1", "2"), ("2", "3")},
        )

    def test_complete_loader_requires_file(self) -> None:
        graph = nx.path_graph(3)
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                with self.assertRaisesRegex(FileNotFoundError, "edge_centralities.csv"):
                    _load_complete_edge_betweenness("fixture", graph)
            finally:
                os.chdir(previous)

    def test_complete_loader_rejects_incomplete_graph_coverage(self) -> None:
        graph = nx.path_graph(3)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_edge_centralities(root, [(0, 1, 0.5)])
            previous = Path.cwd()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(ValueError, "Cobertura incompleta"):
                    _load_complete_edge_betweenness("fixture", graph)
            finally:
                os.chdir(previous)

    def test_complete_loader_returns_every_edge_score(self) -> None:
        graph = nx.path_graph(3)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_edge_centralities(root, [(1, 0, 0.25), (1, 2, 0.75)])
            previous = Path.cwd()
            os.chdir(root)
            try:
                scores = _load_complete_edge_betweenness("fixture", graph)
            finally:
                os.chdir(previous)

        self.assertEqual(scores, {("0", "1"): 0.25, ("1", "2"): 0.75})

    def test_scientific_consumers_require_complete_edge_centralities(self) -> None:
        graph = nx.path_graph(3)
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                with self.assertRaisesRegex(FileNotFoundError, "edge_centralities.csv"):
                    _build_vulnerability_edge_rows("fixture", graph, set())
                with self.assertRaisesRegex(FileNotFoundError, "edge_centralities.csv"):
                    _build_structural_edge_rows("fixture", graph, list(nx.bridges(graph)))
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
