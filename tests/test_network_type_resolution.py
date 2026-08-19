from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ic.artifact_integrity import PASS, audit_artifact_integrity
from ic.io_utils import (
    dataset_graph_path,
    dataset_metadata_path,
    infer_dataset_network_type,
)


class NetworkTypeResolutionTests(unittest.TestCase):
    def test_non_drive_family_is_discovered_across_paths_and_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "data/graphs/demo_bike_raw.graphml"
            metadata = root / "data/metadata/demo_bike_raw.json"
            raw.parent.mkdir(parents=True)
            metadata.parent.mkdir(parents=True)
            raw.write_text(
                '<?xml version="1.0"?><graphml><graph id="demo"/></graphml>',
                encoding="utf-8",
            )
            metadata.write_text(
                json.dumps(
                    {
                        "dataset_id": "demo",
                        "city_id": "demo",
                        "network_type": "bike",
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(infer_dataset_network_type("demo", project_root=root), "bike")
            self.assertEqual(
                dataset_graph_path("demo", "raw", project_root=root),
                raw,
            )
            self.assertEqual(
                dataset_metadata_path("demo", project_root=root),
                metadata,
            )

            audit = audit_artifact_integrity(
                "demo",
                project_root=root,
                output_root=root / "outputs",
                stages=["download"],
                write_outputs=False,
            )

            self.assertEqual(audit["network_type"], "bike")
            self.assertEqual(audit["status"], PASS)

    def test_multiple_network_families_fail_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph_dir = root / "data/graphs"
            graph_dir.mkdir(parents=True)
            (graph_dir / "demo_drive_raw.graphml").write_text("<graphml/>", encoding="utf-8")
            (graph_dir / "demo_bike_raw.graphml").write_text("<graphml/>", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "múltiplos network_type"):
                infer_dataset_network_type("demo", project_root=root)


if __name__ == "__main__":
    unittest.main()
