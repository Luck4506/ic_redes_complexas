from __future__ import annotations

import hashlib
import json
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


def _graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(crs="EPSG:4326")
    graph.add_edge(1, 2)
    return graph


class _ScalarId:
    def __init__(self, value: int) -> None:
        self._value = value

    def item(self) -> int:
        return self._value


class _Geometry:
    is_empty = False

    def __init__(self, wkb: bytes) -> None:
        self.wkb = wkb

    def normalize(self) -> "_Geometry":
        return self


class _Area:
    def __init__(self, value: float) -> None:
        self._value = value

    def sum(self) -> float:
        return self._value


class _GeometrySeries:
    def __init__(self, geometries: list[_Geometry], area: float) -> None:
        self._geometries = geometries
        self.area = _Area(area)

    def __iter__(self):
        return iter(self._geometries)


class _PlaceFrame:
    columns = ("osm_type", "osm_id", "geometry")
    index = (0,)
    crs = "EPSG:4326"

    def __init__(self, geometry: _Geometry, osm_id: int, area: float) -> None:
        self.geometry = _GeometrySeries([geometry], area)
        self._columns = {
            "osm_type": ["relation"],
            "osm_id": [_ScalarId(osm_id)],
        }

    def __getitem__(self, key: str):
        return self._columns[key]


class DownloadMetadataTests(unittest.TestCase):
    def test_live_bbox_is_explicitly_unfrozen_and_records_resolved_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory, _working_directory(Path(directory)):
            config_payload = (
                b"city_id: demo\n"
                b"network_type: drive\n"
                b"simplify: true\n"
                b"clip_mode: bbox\n"
                b"bbox:\n"
                b"  north: -22.1\n"
                b"  south: -22.5\n"
                b"  east: -46.8\n"
                b"  west: -47.2\n"
            )
            config_path = Path("config/demo.yaml")
            config_path.parent.mkdir()
            config_path.write_bytes(config_payload)
            graph = _graph()

            with (
                patch("ic.download._download_graph_from_bbox", return_value=graph) as download,
                patch("ic.download._configure_overpass", return_value="effective-live"),
                patch(
                    "ic.download._utc_now_iso",
                    side_effect=["2026-08-18T12:00:00.000000Z", "2026-08-18T12:00:02.000000Z"],
                ),
                patch("ic.download.now_iso", return_value="2026-08-18T09:00:02"),
                patch("ic.download._osmnx_version", return_value="2.0-test"),
                patch("ic.download.save_graphml"),
                patch("ic.download.save_json") as save_json,
            ):
                result = download_from_config(config_path.as_posix())

            metadata = save_json.call_args.args[1]
            self.assertEqual(
                metadata["query_started_at_utc"], "2026-08-18T12:00:00.000000Z"
            )
            self.assertEqual(
                metadata["query_finished_at_utc"], "2026-08-18T12:00:02.000000Z"
            )
            self.assertEqual(metadata["snapshot_mode"], "live_unfrozen")
            self.assertFalse(metadata["snapshot_frozen"])
            self.assertIsNone(metadata["snapshot_timestamp_utc"])
            self.assertIsNone(metadata["historical_date"])
            self.assertIn("não constituem um snapshot congelado", metadata["snapshot_notice"])
            self.assertEqual(metadata["network_type"], "drive")
            self.assertTrue(metadata["simplify"])
            self.assertEqual(metadata["osmnx_version"], "2.0-test")
            self.assertEqual(metadata["config_sha256"], hashlib.sha256(config_payload).hexdigest())
            self.assertEqual(metadata["config_size_bytes"], len(config_payload))
            boundary_identity = metadata["boundary_identity_sha256"]
            self.assertRegex(boundary_identity, r"^[0-9a-f]{64}$")
            self.assertEqual(metadata["boundary_identity_kind"], "canonical_clip_parameters")
            self.assertEqual(
                metadata["clip"],
                {
                    "mode": "bbox",
                    "north": -22.1,
                    "south": -22.5,
                    "east": -46.8,
                    "west": -47.2,
                    "boundary_geometry_sha256": None,
                    "boundary_geometry_hash_format": None,
                    "boundary_identity_sha256": boundary_identity,
                    "boundary_identity_kind": "canonical_clip_parameters",
                    "boundary_crs": None,
                    "osm_boundary": {
                        "available": False,
                        "element_type": None,
                        "osm_id": None,
                        "relation_id": None,
                    },
                },
            )
            self.assertEqual(metadata["resolved_config"]["dataset_id"], "demo")
            self.assertEqual(metadata["resolved_config"]["overpass"]["use_cache"], True)
            self.assertEqual(
                metadata["resolved_config"]["overpass"]["effective_settings"],
                "effective-live",
            )
            self.assertFalse(metadata["osm_boundary"]["available"])
            self.assertIsNone(metadata["boundary_geometry_sha256"])
            self.assertEqual(result["config_sha256"], metadata["config_sha256"])
            json.dumps(metadata, sort_keys=True, allow_nan=False)

            download.assert_called_once_with(
                north=-22.1,
                south=-22.5,
                east=-46.8,
                west=-47.2,
                historical_date=None,
                network_type="drive",
                simplify=True,
                retain_all=True,
                truncate_by_edge=False,
            )

    def test_historical_place_records_boundary_hash_crs_and_osm_relation(self) -> None:
        with tempfile.TemporaryDirectory() as directory, _working_directory(Path(directory)):
            config_payload = (
                b"city_id: demo\n"
                b"network_type: bike\n"
                b"simplify: false\n"
                b"historical_date: 2019-02-03\n"
                b"clip_mode: place\n"
                b"place_query: Demo, Brazil\n"
                b"overpass:\n"
                b"  use_cache: false\n"
            )
            config_path = Path("config/demo.yaml")
            config_path.parent.mkdir()
            config_path.write_bytes(config_payload)
            geometry_wkb = b"canonical-boundary-wkb"
            place_frame = _PlaceFrame(_Geometry(geometry_wkb), osm_id=987654, area=2_500_000)
            graph = _graph()
            effective_settings = (
                '[out:json][timeout:{timeout}]{maxsize}[date:"2019-02-03T00:00:00Z"]'
            )

            expected_geometry_hash = hashlib.sha256()
            expected_geometry_hash.update(len(geometry_wkb).to_bytes(8, "big"))
            expected_geometry_hash.update(geometry_wkb)

            with (
                patch("ic.download.ox.geocode_to_gdf", return_value=place_frame) as geocode,
                patch("ic.download.ox.projection.project_gdf", return_value=place_frame),
                patch(
                    "ic.download.ox.graph_from_place", return_value=graph
                ) as graph_from_place,
                patch("ic.download._configure_overpass", return_value=effective_settings),
                patch(
                    "ic.download._utc_now_iso",
                    side_effect=["2026-08-18T13:00:00.000000Z", "2026-08-18T13:00:03.000000Z"],
                ),
                patch("ic.download.now_iso", return_value="2026-08-18T10:00:03"),
                patch("ic.download._osmnx_version", return_value="2.0-test"),
                patch("ic.download.save_graphml"),
                patch("ic.download.save_json") as save_json,
            ):
                download_from_config(config_path.as_posix())

            metadata = save_json.call_args.args[1]
            self.assertEqual(metadata["snapshot_mode"], "historical")
            self.assertTrue(metadata["snapshot_frozen"])
            self.assertEqual(metadata["historical_date"], "2019-02-03")
            self.assertEqual(metadata["snapshot_timestamp_utc"], "2019-02-03T00:00:00Z")
            self.assertIsNone(metadata["snapshot_notice"])
            self.assertEqual(metadata["dataset_id"], "demo_2019-02-03")
            self.assertEqual(metadata["boundary_crs"], "EPSG:4326")
            self.assertEqual(
                metadata["boundary_geometry_sha256"],
                expected_geometry_hash.hexdigest(),
            )
            self.assertEqual(
                metadata["boundary_identity_sha256"],
                expected_geometry_hash.hexdigest(),
            )
            self.assertEqual(metadata["boundary_identity_kind"], "normalized_boundary_wkb")
            self.assertEqual(
                metadata["osm_boundary"],
                {
                    "available": True,
                    "element_type": "relation",
                    "osm_id": 987654,
                    "relation_id": 987654,
                },
            )
            self.assertEqual(metadata["clip"]["mode"], "place")
            self.assertEqual(metadata["clip"]["query"], "Demo, Brazil")
            self.assertEqual(metadata["clip"]["area_km2"], 2.5)
            self.assertEqual(metadata["resolved_config"]["historical_date"], "2019-02-03")
            self.assertEqual(
                metadata["resolved_config"]["clip"],
                {"mode": "place", "query": "Demo, Brazil"},
            )
            json.dumps(metadata, sort_keys=True, allow_nan=False)

            geocode.assert_called_once_with("Demo, Brazil")
            graph_from_place.assert_called_once_with(
                "Demo, Brazil",
                network_type="bike",
                simplify=False,
                retain_all=True,
                truncate_by_edge=False,
            )

    def test_radius_clip_is_recorded_with_normalized_numeric_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory, _working_directory(Path(directory)):
            config_payload = (
                b"city_id: demo\n"
                b"clip_mode: radius\n"
                b"center:\n"
                b"  lat: '-22.90'\n"
                b"  lon: '-47.10'\n"
                b"dist_meters: '1250'\n"
            )
            config_path = Path("config/demo.yaml")
            config_path.parent.mkdir()
            config_path.write_bytes(config_payload)
            graph = _graph()

            with (
                patch("ic.download.ox.graph_from_point", return_value=graph) as graph_from_point,
                patch("ic.download._configure_overpass", return_value="effective-live"),
                patch(
                    "ic.download._utc_now_iso",
                    side_effect=["2026-08-18T14:00:00.000000Z", "2026-08-18T14:00:01.000000Z"],
                ),
                patch("ic.download.now_iso", return_value="2026-08-18T11:00:01"),
                patch("ic.download._osmnx_version", return_value="2.0-test"),
                patch("ic.download.save_graphml"),
                patch("ic.download.save_json") as save_json,
            ):
                download_from_config(config_path.as_posix())

            metadata = save_json.call_args.args[1]
            self.assertEqual(metadata["clip"]["mode"], "radius")
            self.assertEqual(metadata["clip"]["lat"], -22.9)
            self.assertEqual(metadata["clip"]["lon"], -47.1)
            self.assertEqual(metadata["clip"]["dist_meters"], 1250.0)
            self.assertRegex(metadata["boundary_identity_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(metadata["boundary_identity_kind"], "canonical_clip_parameters")
            self.assertEqual(
                metadata["clip"]["boundary_identity_sha256"],
                metadata["boundary_identity_sha256"],
            )
            self.assertEqual(
                metadata["resolved_config"]["clip"],
                {"mode": "radius", "lat": -22.9, "lon": -47.1, "dist_meters": 1250.0},
            )
            self.assertEqual(
                metadata["resolved_config"]["center"], {"lat": -22.9, "lon": -47.1}
            )
            self.assertEqual(metadata["resolved_config"]["dist_meters"], 1250.0)
            self.assertEqual(metadata["network_type"], "drive")
            self.assertTrue(metadata["simplify"])
            self.assertFalse(metadata["osm_boundary"]["available"])

            graph_from_point.assert_called_once_with(
                (-22.9, -47.1),
                dist=1250.0,
                network_type="drive",
                simplify=True,
                retain_all=True,
                truncate_by_edge=False,
            )


if __name__ == "__main__":
    unittest.main()
