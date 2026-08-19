from __future__ import annotations

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import networkx as nx


os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.representation_audit import analisar_representacoes


class RepresentationAuditTests(unittest.TestCase):
    @staticmethod
    def _synthetic_graphs() -> tuple[nx.MultiDiGraph, nx.MultiDiGraph]:
        raw = nx.MultiDiGraph()
        raw.add_nodes_from(["a", "b", "c", "d", "e"])
        raw.add_edge("a", "b", length=10.0, oneway=False)
        raw.add_edge("a", "b", length=4.0, oneway=True)
        raw.add_edge("b", "a", length=7.0, oneway=False)
        raw.add_edge("b", "c", length=3.0, oneway=True)
        raw.add_edge("c", "c", length=2.0, oneway=False)
        raw.add_edge("d", "e", length=20.0, oneway=True)
        clean = raw.subgraph(["a", "b", "c"]).copy()
        return raw, clean

    def test_audit_exposes_parallel_reciprocal_and_length_collapsing(self) -> None:
        raw, clean = self._synthetic_graphs()
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                with patch(
                    "ic.representation_audit.load_graphml",
                    side_effect=[raw.copy(), clean.copy()],
                ) as mocked_load:
                    result = analisar_representacoes("cidade_teste", top_k=2, seed=11)

                self.assertEqual(
                    [call.args[0] for call in mocked_load.call_args_list],
                    [
                        "data/graphs/cidade_teste_drive_raw.graphml",
                        "data/graphs/cidade_teste_drive_clean.graphml",
                    ],
                )
                audit_path = Path(result["audit_csv"])
                sensitivity_path = Path(result["sensitivity_csv"])
                report_path = Path(result["report_txt"])
                self.assertTrue(audit_path.exists())
                self.assertTrue(sensitivity_path.exists())
                self.assertTrue(report_path.exists())

                with audit_path.open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(len(rows), 8)
                by_key = {(row["dataset_stage"], row["representation"]): row for row in rows}

                directed_raw = by_key[("raw", "multidigraph_directed")]
                self.assertEqual(int(directed_raw["nodes"]), 5)
                self.assertEqual(int(directed_raw["edges"]), 6)
                self.assertEqual(int(directed_raw["components"]), 2)
                self.assertEqual(int(directed_raw["largest_component_nodes"]), 3)
                self.assertEqual(int(directed_raw["self_loops"]), 1)
                self.assertEqual(int(directed_raw["parallel_endpoint_pairs"]), 1)
                self.assertEqual(int(directed_raw["parallel_edge_excess"]), 1)
                self.assertEqual(int(directed_raw["reciprocal_endpoint_pairs"]), 1)
                self.assertEqual(int(directed_raw["unreciprocated_endpoint_pairs"]), 2)
                self.assertEqual(int(directed_raw["oneway_edges_by_attribute"]), 3)
                self.assertAlmostEqual(float(directed_raw["directed_length_m"]), 46.0)
                self.assertAlmostEqual(float(directed_raw["physical_collapsed_length_m"]), 29.0)

                undirected_multi = by_key[("raw", "multigraph_undirected")]
                self.assertEqual(int(undirected_multi["edges"]), 6)
                self.assertEqual(int(undirected_multi["parallel_edge_excess"]), 2)
                self.assertEqual(undirected_multi["directed_length_m"], "")

                directed_min = by_key[("raw", "digraph_min_length")]
                self.assertEqual(int(directed_min["edges"]), 5)
                self.assertAlmostEqual(float(directed_min["directed_length_m"]), 36.0)

                simple = by_key[("raw", "graph_min_length")]
                self.assertEqual(int(simple["edges"]), 4)
                self.assertAlmostEqual(float(simple["total_edge_length_m"]), 29.0)

                clean_directed = by_key[("clean", "multidigraph_directed")]
                self.assertEqual(float(clean_directed["raw_to_clean_nodes_lost"]), 2.0)
                self.assertEqual(float(clean_directed["raw_to_clean_edges_lost"]), 1.0)
                self.assertAlmostEqual(float(clean_directed["raw_to_clean_directed_length_lost_m"]), 20.0)
                self.assertAlmostEqual(float(clean_directed["raw_to_clean_physical_length_lost_m"]), 20.0)

                with sensitivity_path.open(newline="", encoding="utf-8") as stream:
                    sensitivity_rows = list(csv.DictReader(stream))
                self.assertEqual(len(sensitivity_rows), 32)
                self.assertEqual(
                    {row["metric"] for row in sensitivity_rows},
                    {"degree", "betweenness_unweighted"},
                )
                self.assertIn(
                    "preprocessing_raw_to_clean",
                    {row["comparison_scope"] for row in sensitivity_rows},
                )
                self.assertTrue(all(row["top_k_effective"] for row in sensitivity_rows))

                report = report_path.read_text(encoding="utf-8")
                self.assertIn("Limitações de interpretação", report)
                self.assertIn("não deve ser apresentada como extensão física", report)
                self.assertIn("Spearman usa somente nós comuns", report)
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
