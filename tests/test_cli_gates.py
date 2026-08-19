from __future__ import annotations

import sys
import unittest
from unittest.mock import Mock, patch

from ic.cli import _main, main


class CliGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recorder = Mock()

    def test_scientific_comparison_not_proven_exits_nonzero(self) -> None:
        result = {
            "state": "nao_comprovada",
            "criteria_csv": "criteria.csv",
            "datasets_csv": "datasets.csv",
            "pairs_csv": "pairs.csv",
            "report_txt": "report.txt",
        }
        argv = ["ic", "comparison-audit", "alpha", "beta"]
        with (
            patch.object(sys, "argv", argv),
            patch("ic.cli.auditar_comparabilidade_cientifica", return_value=result),
            self.assertRaises(SystemExit) as raised,
        ):
            _main(self.recorder)

        self.assertEqual(raised.exception.code, 1)

    def test_failed_artifact_integrity_exits_nonzero(self) -> None:
        result = {
            "scope": "structural",
            "overall_status": "FAIL",
            "safe_to_use": False,
            "audit_csv": "audit.csv",
            "report_txt": "report.txt",
        }
        argv = ["ic", "artifact-integrity", "--city", "demo", "--stages", "structural"]
        with (
            patch.object(sys, "argv", argv),
            patch("ic.cli.auditar_integridade_artefatos", return_value=result) as audit,
            self.assertRaises(SystemExit) as raised,
        ):
            _main(self.recorder)

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(audit.call_args.kwargs["dataset"], "demo")

    def test_manifest_can_supply_dataset_without_city(self) -> None:
        result = {
            "scope": "manifesto",
            "overall_status": "PASS",
            "safe_to_use": True,
            "audit_csv": "audit.csv",
            "report_txt": "report.txt",
        }
        argv = ["ic", "artifact-integrity", "--manifest", "manifest.json"]
        with (
            patch.object(sys, "argv", argv),
            patch("ic.cli.auditar_integridade_artefatos", return_value=result) as audit,
        ):
            _main(self.recorder)

        self.assertIsNone(audit.call_args.kwargs["dataset"])
        self.assertEqual(audit.call_args.kwargs["manifest"], "manifest.json")

    def test_main_records_nonzero_gate_as_failure(self) -> None:
        recorder = Mock()
        failure = SystemExit(1)
        with (
            patch("ic.cli.begin_cli_run", return_value=recorder),
            patch("ic.cli._main", side_effect=failure),
            self.assertRaises(SystemExit),
        ):
            main()

        recorder.finish.assert_called_once_with("failure", failure)

    def test_provenance_failure_does_not_hide_original_error(self) -> None:
        recorder = Mock()
        recorder.finish.side_effect = OSError("disk full")
        original = ValueError("analysis failed")
        with (
            patch("ic.cli.begin_cli_run", return_value=recorder),
            patch("ic.cli._main", side_effect=original),
            self.assertRaises(ValueError) as raised,
        ):
            main()

        self.assertIs(raised.exception, original)
        self.assertTrue(any("proveniência" in note for note in raised.exception.__notes__))


if __name__ == "__main__":
    unittest.main()
