from __future__ import annotations

import os
import unittest
from collections import Counter
from pathlib import Path
import sys

import networkx as nx
import numpy as np

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ic.metric_graphs import approximate_global_efficiency, simple_undirected_min_length_graph
from ic.community_resilience import _build_community_graph
from ic.intra_community_resilience import _normalized_auc, _simulate_community
from ic.centrality import approximate_closeness_centrality
from ic.functional_relations import spearman_correlation
from ic.comparison_protocol import _bbox_area_km2
from ic.node_resilience import _efficiency_on_original_nodes
from ic.historical_quality import _historical_status, _way_ids_from_edge
from ic.random_resilience_stats import _aggregate_rows
from ic.vulnerability_index import _minmax
from ic.structural_bottlenecks import _component_sizes_after_node_removal, _impact_from_sizes
from ic.route_redundancy import _summarize
from ic.spatial_multiscale import _build_grid
from ic.spatial_robustness import _cell_incident_edges, _cell_internal_edges
from ic.road_hierarchy import _road_class
from ic.urban_morphology import _classify_pattern, _entropy
from ic.od_efficiency import _percentile, _summarize as _summarize_od
from ic.city_similarity import _cosine_similarity, _standardize_matrix
from ic.subcenters import _polycentricity, _percentile as _subcenter_percentile
from ic.urban_barriers import _is_cardinal_neighbor, _percentile as _barrier_percentile, _possible_neighbor_pairs
from ic.network_scale_profile import _coefficient_variation, _stability_score


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

    def test_approximate_closeness_is_exact_when_all_nodes_are_landmarks(self) -> None:
        G = nx.path_graph(5)

        approximate = approximate_closeness_centrality(G, samples=10)
        exact = nx.closeness_centrality(G)

        for node in G.nodes():
            self.assertAlmostEqual(approximate[node], exact[node])

    def test_spearman_correlation_detects_monotonic_relation(self) -> None:
        self.assertAlmostEqual(spearman_correlation([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman_correlation([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)

    def test_bbox_area_is_positive(self) -> None:
        area = _bbox_area_km2({"mode": "bbox", "north": -22.7, "south": -23.0, "east": -46.8, "west": -47.1})
        self.assertIsNotNone(area)
        self.assertGreater(area, 0)

    def test_recorded_place_area_is_used(self) -> None:
        area = _bbox_area_km2({"mode": "place", "area_km2": 123.45})
        self.assertEqual(area, 123.45)

    def test_node_removal_efficiency_uses_original_node_denominator(self) -> None:
        G = nx.path_graph(3)
        sources = [0, 1, 2]
        initial = _efficiency_on_original_nodes(G, original_nodes=3, samples=10, seed=42, sampled_original_nodes=sources)
        G.remove_node(2)
        after = _efficiency_on_original_nodes(G, original_nodes=3, samples=10, seed=42, sampled_original_nodes=sources)

        self.assertAlmostEqual(initial, 5 / 6)
        self.assertAlmostEqual(after, 1 / 3)

    def test_historical_way_ids_parse_scalar_and_list(self) -> None:
        self.assertEqual(_way_ids_from_edge({"osmid": "123"}), {"123"})
        self.assertEqual(_way_ids_from_edge({"osmid": "[123, 456]"}), {"123", "456"})

    def test_low_historical_coverage_is_not_reliable(self) -> None:
        status, _reason = _historical_status(
            reference_coverage=0.25,
            mapped_way_ratio=0.90,
            dropped=0,
            is_reference=False,
        )
        self.assertEqual(status, "nao_confiavel")

    def test_random_resilience_aggregate_rows(self) -> None:
        rows = [
            {
                "step_index": 0,
                "removed_fraction": "0.0",
                "lcc_fraction": "1.0",
                "num_components": "1",
                "efficiency_topological_retained": "1.0",
                "efficiency_length_retained": "1.0",
            },
            {
                "step_index": 0,
                "removed_fraction": "0.0",
                "lcc_fraction": "0.8",
                "num_components": "2",
                "efficiency_topological_retained": "0.6",
                "efficiency_length_retained": "0.7",
            },
        ]

        aggregate = _aggregate_rows(rows)

        self.assertEqual(aggregate[0]["runs"], 2)
        self.assertAlmostEqual(aggregate[0]["lcc_fraction_mean"], 0.9)
        self.assertGreater(aggregate[0]["lcc_fraction_std"], 0.0)

    def test_vulnerability_minmax_normalizes_values(self) -> None:
        values = _minmax({"a": 10.0, "b": 20.0, "c": 30.0})

        self.assertEqual(values["a"], 0.0)
        self.assertEqual(values["c"], 1.0)
        self.assertAlmostEqual(values["b"], 0.5)

    def test_structural_bottleneck_impact_counts_detached_nodes(self) -> None:
        G = nx.path_graph(5)

        sizes = _component_sizes_after_node_removal(G, 2)
        impact = _impact_from_sizes(sizes, original_nodes_after_removal=4)

        self.assertEqual(sizes, [2, 2])
        self.assertEqual(impact["components_after_removal"], 2)
        self.assertEqual(impact["detached_nodes_after_removal"], 2)
        self.assertAlmostEqual(impact["detached_fraction_after_removal"], 0.5)

    def test_route_redundancy_summary_rates(self) -> None:
        rows = [
            {"alternative_exists": 1, "reasonable_alternative": 1, "alternative_ratio": 1.2, "detour_distance_m": 100.0},
            {"alternative_exists": 1, "reasonable_alternative": 0, "alternative_ratio": 1.8, "detour_distance_m": 400.0},
            {"alternative_exists": 0, "reasonable_alternative": 0, "alternative_ratio": 0.0, "detour_distance_m": 0.0},
        ]

        summary = _summarize(rows, threshold=1.5)

        self.assertEqual(summary["sampled_pairs"], 3)
        self.assertAlmostEqual(summary["alternative_rate"], 2 / 3)
        self.assertAlmostEqual(summary["reasonable_alternative_rate"], 1 / 3)
        self.assertAlmostEqual(summary["disconnected_after_block_rate"], 1 / 3)
        self.assertAlmostEqual(summary["alternative_ratio_mean"], 1.5)

    def test_spatial_grid_assigns_nodes_to_cells(self) -> None:
        G = nx.Graph()
        G.add_node("a", y=-22.90, x=-47.10)
        G.add_node("b", y=-22.901, x=-47.101)
        G.add_node("c", y=-22.92, x=-47.12)

        cells, node_to_cell = _build_grid(G, cell_size_m=1000)

        self.assertEqual(set(node_to_cell), {"a", "b", "c"})
        self.assertGreaterEqual(len(cells), 2)
        self.assertEqual(sum(len(cell["nodes"]) for cell in cells.values()), 3)

    def test_spatial_robustness_edge_modes(self) -> None:
        G = nx.path_graph(["a", "b", "c", "d"])

        internal = _cell_internal_edges(G, ["b", "c"])
        incident = _cell_incident_edges(G, ["b", "c"])

        self.assertEqual(internal, {("b", "c")})
        self.assertEqual(incident, {("a", "b"), ("b", "c"), ("c", "d")})

    def test_road_hierarchy_collapses_link_classes(self) -> None:
        self.assertEqual(_road_class("primary_link"), "primary")
        self.assertEqual(_road_class("secondary"), "secondary")
        self.assertEqual(_road_class("not_a_standard_class"), "other")

    def test_urban_morphology_classifies_grid_pattern(self) -> None:
        label, _reason = _classify_pattern(
            node_count=40,
            edge_count=55,
            degree_mean=2.8,
            largest_component_fraction=0.95,
            entropy=0.55,
            dominance=0.30,
            orthogonal_share=0.70,
            mean_segment_length=65.0,
        )

        self.assertEqual(label, "gradeada")
        self.assertAlmostEqual(_entropy(Counter({0: 10})), 0.0)

    def test_od_efficiency_summary_metrics(self) -> None:
        rows = [
            {"route_distance_m": 1000.0, "direct_distance_m": 800.0, "hops": 10, "circuity_ratio": 1.25, "route_efficiency": 0.8, "approx_speed_kmh": 24.0},
            {"route_distance_m": 6000.0, "direct_distance_m": 3000.0, "hops": 40, "circuity_ratio": 2.0, "route_efficiency": 0.5, "approx_speed_kmh": 15.0},
        ]

        summary = {row["metric"]: row["value"] for row in _summarize_od(rows, requested_pairs=2, attempts=3)}

        self.assertEqual(summary["sampled_pairs"], 2)
        self.assertEqual(summary["sampling_attempts"], 3)
        self.assertAlmostEqual(summary["route_distance_m_mean"], 3500.0)
        self.assertAlmostEqual(summary["accessibility_within_5km_rate"], 0.5)
        self.assertAlmostEqual(summary["high_detour_rate_circuity_gt_1_75"], 0.5)
        self.assertAlmostEqual(_percentile([1.0, 3.0], 0.5), 2.0)

    def test_city_similarity_standardizes_and_cosine_diagonal(self) -> None:
        matrix = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]])

        standardized, _means, _stds = _standardize_matrix(matrix)
        similarity = _cosine_similarity(standardized)

        self.assertEqual(standardized.shape, matrix.shape)
        self.assertAlmostEqual(float(np.mean(standardized[:, 0])), 0.0)
        self.assertAlmostEqual(similarity[0, 0], 1.0)
        self.assertLess(similarity[0, 2], 0.0)

    def test_subcenter_polycentricity_detects_dominance(self) -> None:
        balanced = _polycentricity([{"subcenter_score": 1.0}, {"subcenter_score": 1.0}, {"subcenter_score": 1.0}])
        dominant = _polycentricity([{"subcenter_score": 10.0}, {"subcenter_score": 1.0}, {"subcenter_score": 1.0}])

        self.assertGreater(balanced["polycentricity_index"], dominant["polycentricity_index"])
        self.assertLess(balanced["monocentricity_index"], dominant["monocentricity_index"])
        self.assertAlmostEqual(_subcenter_percentile([1.0, 3.0], 0.5), 2.0)

    def test_urban_barriers_detects_cardinal_neighbor_pairs(self) -> None:
        cells = {
            "a": {"row": 0, "col": 0, "nodes": ["n1"]},
            "b": {"row": 0, "col": 1, "nodes": ["n2"]},
            "c": {"row": 1, "col": 1, "nodes": ["n3"]},
            "d": {"row": 2, "col": 2, "nodes": ["n4"]},
        }

        pairs = _possible_neighbor_pairs(cells)

        self.assertIn(("a", "b"), pairs)
        self.assertIn(("b", "c"), pairs)
        self.assertNotIn(("a", "c"), pairs)
        self.assertTrue(_is_cardinal_neighbor(cells["a"], cells["b"]))
        self.assertFalse(_is_cardinal_neighbor(cells["a"], cells["c"]))
        self.assertAlmostEqual(_barrier_percentile([10.0, 30.0], 0.5), 20.0)

    def test_network_scale_stability_penalizes_variation(self) -> None:
        stable = [1.0, 1.0, 1.0, 1.0]
        unstable = [1.0, 2.0, 4.0, 8.0]

        self.assertAlmostEqual(_coefficient_variation(stable), 0.0)
        self.assertEqual(_stability_score(stable), 1.0)
        self.assertLess(_stability_score(unstable), _stability_score(stable))


if __name__ == "__main__":
    unittest.main()
