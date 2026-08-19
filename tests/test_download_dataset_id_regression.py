from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import networkx as nx

from ic.download import download_from_config


@contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class DownloadDatasetIdRegressionTests(unittest.TestCase):
    def test_null_dataset_id_falls_back_to_city_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory, _working_directory(Path(directory)):
            config = Path("config/demo.yaml")
            config.parent.mkdir(parents=True)
            config.write_text(
                """city_id: demo
dataset_id: null
clip_mode: bbox
bbox:
  north: -22.1
  south: -22.5
  east: -46.8
  west: -47.2
""",
                encoding="utf-8",
            )
            graph = nx.MultiDiGraph(crs="EPSG:4326")
            graph.add_edge(1, 2)

            with (
                patch("ic.download._download_graph_from_bbox", return_value=graph),
                patch("ic.download._configure_overpass", return_value="effective-live"),
                patch(
                    "ic.download._utc_now_iso",
                    side_effect=[
                        "2026-08-18T12:00:00.000000Z",
                        "2026-08-18T12:00:01.000000Z",
                    ],
                ),
                patch("ic.download.now_iso", return_value="2026-08-18T09:00:01"),
                patch("ic.download._osmnx_version", return_value="2.0-test"),
                patch("ic.download.save_graphml") as save_graphml,
                patch("ic.download.save_json") as save_json,
            ):
                result = download_from_config(config.as_posix())

            self.assertEqual(result["dataset_id"], "demo")
            self.assertEqual(result["resolved_config"]["dataset_id"], "demo")
            self.assertEqual(result["graph_path"], "data/graphs/demo_drive_raw.graphml")
            self.assertEqual(result["meta_path"], "data/metadata/demo_drive_raw.json")
            save_graphml.assert_called_once_with(
                graph, "data/graphs/demo_drive_raw.graphml"
            )
            self.assertEqual(save_json.call_args.args[0], "data/metadata/demo_drive_raw.json")


if __name__ == "__main__":
    unittest.main()
