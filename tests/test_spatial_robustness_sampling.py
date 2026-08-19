from __future__ import annotations

import unittest

from ic.spatial_robustness import _select_efficiency_cell_ids


class SpatialRobustnessSamplingTests(unittest.TestCase):
    def test_selection_is_seeded_and_independent_of_lcc_ranking(self) -> None:
        rows = [
            {
                "cell_id": f"c{index}",
                "removed_edges": 1,
                "lcc_fraction_drop": 1.0 - index / 10.0,
            }
            for index in range(10)
        ]

        first = _select_efficiency_cell_ids(rows, limit=4, seed=42)
        reordered = _select_efficiency_cell_ids(list(reversed(rows)), limit=4, seed=42)

        self.assertEqual(first, reordered)
        self.assertEqual(len(first), 4)
        self.assertNotEqual(first, {"c0", "c1", "c2", "c3"})

    def test_all_eligible_cells_are_selected_when_limit_is_sufficient(self) -> None:
        rows = [
            {"cell_id": "a", "removed_edges": 1},
            {"cell_id": "b", "removed_edges": 0},
            {"cell_id": "c", "removed_edges": 2},
        ]

        self.assertEqual(_select_efficiency_cell_ids(rows, limit=10, seed=7), {"a", "c"})


if __name__ == "__main__":
    unittest.main()
