"""Tests deteccion de mapa (sin SnowRunner en ejecucion)."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from datos import map_detect
from datos.map_detect import (
    MapDetectResult,
    detect_from_csv_map_columns,
    detect_from_game_logs,
    detect_from_position,
    detect_from_position_smart,
    format_map_line,
    resolve_map_context,
)


class TestMapDetect(unittest.TestCase):
    def test_parse_black_river_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = os.path.join(tmp, "logs")
            os.makedirs(log_dir)
            path = os.path.join(log_dir, "game.log")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Loading zone level_us_01_01\n")
                f.write("some other noise\n")
            with mock.patch.object(map_detect, "SNOWRUNNER_LOG_DIRS", [log_dir]):
                hit = detect_from_game_logs()
            self.assertEqual(hit.map_name, "Black River")
            self.assertEqual(hit.region, "Michigan")
            self.assertEqual(hit.level_id, "level_us_01_01")

    def test_parse_north_port_map_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = os.path.join(tmp, "logs")
            os.makedirs(log_dir)
            path = os.path.join(log_dir, "LegacyLog.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("travel to US_02_01_PORT garage\n")
            with mock.patch.object(map_detect, "SNOWRUNNER_LOG_DIRS", [log_dir]):
                hit = detect_from_game_logs()
            self.assertEqual(hit.map_name, "North Port")
            self.assertEqual(hit.region, "Alaska")

    def test_manual_override(self) -> None:
        hit = resolve_map_context(map_arg="North Port", location_arg="garaje upgrades")
        self.assertEqual(hit.map_name, "North Port")
        self.assertEqual(hit.location_note, "garaje upgrades")
        self.assertEqual(hit.source, "manual")

    def test_unknown_without_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(map_detect, "SNOWRUNNER_LOG_DIRS", [tmp]):
                hit = resolve_map_context()
            self.assertFalse(hit.ok)
            self.assertIn("?", format_map_line(hit))

    def test_position_north_port(self) -> None:
        hit = detect_from_position(722.37, -213.18)
        self.assertEqual(hit.map_name, "North Port")
        self.assertEqual(hit.region, "Alaska")
        self.assertEqual(hit.source, "position")

    def test_snow_overrides_michigan_bbox(self) -> None:
        hit = detect_from_position_smart(
            285.77,
            -331.53,
            terrain_kinds={"snow": 8, "mud": 50},
        )
        self.assertEqual(hit.map_name, "North Port")
        self.assertEqual(hit.source, "terrain")

    def test_game_log_prefers_newest_file(self) -> None:
        import time

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = os.path.join(tmp, "logs")
            os.makedirs(log_dir)
            old_path = os.path.join(log_dir, "game.log")
            new_path = os.path.join(log_dir, "LegacyLog.txt")
            with open(old_path, "w", encoding="utf-8") as f:
                f.write("Loading zone level_us_01_01\n")
            time.sleep(0.05)
            with open(new_path, "w", encoding="utf-8") as f:
                f.write("Loading zone level_us_02_01\n")
            with mock.patch.object(map_detect, "SNOWRUNNER_LOG_DIRS", [log_dir]):
                hit = detect_from_game_logs()
            self.assertEqual(hit.map_name, "North Port")
            self.assertIn("LegacyLog", hit.source)

    def test_position_outside_bounds_skips_sky_scan(self) -> None:
        with mock.patch.object(map_detect, "detect_from_sky_memory") as sky_mock:
            hit = detect_from_position_smart(2000.0, 2000.0, process_handle=123)
        self.assertFalse(hit.ok)
        self.assertEqual(hit.source, "position:miss")
        sky_mock.assert_not_called()

    def test_resolve_map_context_single_sky_scan_on_position_miss(self) -> None:
        sky_result = MapDetectResult(
            level_id="level_ru_02_01",
            region="Taymyr",
            map_name="Drowned Lands",
            location_note="Drowned Lands partida libre",
            source="sky",
        )
        with mock.patch.object(map_detect, "detect_from_game_logs", return_value=MapDetectResult(source="game_log:missing")):
            with mock.patch.object(map_detect, "detect_from_sky_memory", return_value=sky_result) as sky_mock:
                hit = resolve_map_context(
                    process_handle=123,
                    sample={"pos_x": 2000.0, "pos_z": 2000.0, "terrain_kind": "mud"},
                )
        self.assertEqual(hit.map_name, "Drowned Lands")
        sky_mock.assert_called_once_with(123)

    def test_csv_map_columns(self) -> None:
        rows = [{"map_name": "North Port", "level_id": "level_us_02_01"}] * 5
        hit = detect_from_csv_map_columns(rows)
        self.assertEqual(hit.map_name, "North Port")
        self.assertEqual(hit.source, "csv_map")

    def test_position_black_river(self) -> None:
        hit = detect_from_position(408.0, -611.0)
        self.assertEqual(hit.map_name, "Black River")
        self.assertIn(hit.source, ("position", "position+overlap"))

    def test_position_outside_known(self) -> None:
        hit = detect_from_position(2000.0, 2000.0)
        self.assertFalse(hit.ok)

    def test_format_ok(self) -> None:
        line = format_map_line(
            MapDetectResult(
                map_name="North Port",
                region="Alaska",
                level_id="level_us_02_01",
                source="memory",
            )
        )
        self.assertIn("North Port", line)
        self.assertIn("Alaska", line)


if __name__ == "__main__":
    unittest.main()
