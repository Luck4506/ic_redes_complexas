from __future__ import annotations

import unittest

from ic.city_similarity import THEORY_CORE_METRICS, analisar_similaridade_cidades


class CitySimilaritySafeguardTests(unittest.TestCase):
    def test_four_city_analysis_requires_explicit_exploratory_override(self) -> None:
        with self.assertRaisesRegex(ValueError, "Amostra insuficiente"):
            analisar_similaridade_cidades(["a", "b", "c", "d"])

    def test_core_profile_is_small_and_has_no_obvious_complement_pairs(self) -> None:
        self.assertLessEqual(len(THEORY_CORE_METRICS), 15)
        self.assertNotIn("unknown_surface_edges_pct", THEORY_CORE_METRICS)
        self.assertNotIn("estimated_paved_edges_pct", THEORY_CORE_METRICS)
        self.assertIn("physical_collapsed_length_km_per_km2", THEORY_CORE_METRICS)


if __name__ == "__main__":
    unittest.main()
