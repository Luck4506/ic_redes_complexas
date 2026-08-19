from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ic.comparison_protocol import auditar_comparabilidade


class ComparisonProtocolFacadeTests(unittest.TestCase):
    def test_legacy_entrypoint_delegates_to_fail_closed_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            expected = {
                "state": "nao_comprovada",
                "datasets_csv": f"{tmp}/scientific_comparability_datasets.csv",
                "dataset_rows": [{"dataset": "alpha", "state": "nao_comprovada"}],
                "criteria_csv": f"{tmp}/scientific_comparability_criteria.csv",
                "pairs_csv": f"{tmp}/scientific_comparability_pairs.csv",
                "report_txt": f"{tmp}/scientific_comparability_report.txt",
            }
            Path(expected["datasets_csv"]).write_text("dataset,state\nalpha,nao_comprovada\n")
            legacy_path = Path(tmp) / "legacy.csv"
            with patch(
                "ic.comparison_protocol.auditar_comparabilidade_cientifica",
                return_value=expected,
            ) as scientific_audit:
                result = auditar_comparabilidade(
                    ["alpha"],
                    output_path=str(legacy_path),
                )
            with legacy_path.open(encoding="utf-8", newline="") as handle:
                legacy_rows = list(csv.DictReader(handle))

        scientific_audit.assert_called_once_with(
            ["alpha"],
            output_dir=tmp,
            perfil="cientifico",
            snapshot_policy="same",
        )
        self.assertEqual(result["status"], "nao_comprovada")
        self.assertEqual(result["audit_csv"], str(legacy_path))
        self.assertEqual(legacy_rows[0]["dataset"], "alpha")
        self.assertEqual(legacy_rows[0]["comparison_status"], "exploratorio")
        self.assertIn("nao_comprovada", legacy_rows[0]["status_reason"])
        self.assertEqual(result["legacy_rows"], legacy_rows)
        self.assertEqual(result["rows"], expected["dataset_rows"])


if __name__ == "__main__":
    unittest.main()
