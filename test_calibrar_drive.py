"""Tests calibracion drive (throttle/RPM)."""

from __future__ import annotations

import json
import os
import unittest

from cheat_engine.calibrar_drive import (
    _floats_from_snap,
    _scan_values_pass,
    pick_from_snaps,
    rank_rpm_candidates,
    rank_throttle_candidates,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
SNAP_DIR = os.path.join(ROOT, "cheat_engine", "drive_snaps")


class TestCalibrarDrive(unittest.TestCase):
    def test_scan_values_pass_t813(self) -> None:
        self.assertTrue(_scan_values_pass(0.003, 0.9697))

    def test_rank_rejects_stuck_at_one(self) -> None:
        off = {("vehicle", 0x760): 0.95}
        full = {("vehicle", 0x760): 0.98}
        self.assertEqual(rank_throttle_candidates(off, full), [])

    def test_rank_accepts_missing_off_zero_default(self) -> None:
        off: dict = {}
        full = {("vehicle", 0x760): 1.0}
        ranked = rank_throttle_candidates(off, full)
        self.assertTrue(ranked)
        self.assertEqual(ranked[0][1], ("vehicle", 0x760))

    def test_rank_prefers_vehicle_over_drive_logic(self) -> None:
        off = {("drive_logic", 0x30): 0.0, ("vehicle", 0x760): 0.0}
        full = {("drive_logic", 0x30): 1.0, ("vehicle", 0x760): 1.0}
        ranked = rank_throttle_candidates(off, full)
        self.assertEqual(ranked[0][1], ("vehicle", 0x760))

        off = {("vehicle", 0x760): 0.0}
        full = {("vehicle", 0x760): 1.0}
        ranked = rank_throttle_candidates(off, full)
        self.assertTrue(ranked)
        self.assertEqual(ranked[0][1], ("vehicle", 0x760))

    def test_rank_drive_logic_low_to_high(self) -> None:
        off = {("drive_logic", 0x030): 0.002}
        full = {("drive_logic", 0x030): 0.98}
        ranked = rank_throttle_candidates(off, full)
        self.assertTrue(ranked)
        self.assertEqual(ranked[0][1], ("drive_logic", 0x030))

    def test_gas_snaps_bandit(self) -> None:
        off_path = os.path.join(SNAP_DIR, "gas_off.json")
        full_path = os.path.join(SNAP_DIR, "gas_full.json")
        if not os.path.isfile(off_path) or not os.path.isfile(full_path):
            self.skipTest("snapshots gas_off/gas_full no presentes")
        with open(off_path, encoding="utf-8") as f:
            off = json.load(f)
        with open(full_path, encoding="utf-8") as f:
            full = json.load(f)
        thr_spec, rpm_spec = pick_from_snaps(off, full)
        self.assertIsNotNone(thr_spec)
        self.assertIsNotNone(rpm_spec)
        # Bandit: veh+760 0->1; no debe quedar veh+758 (casi fijo)
        self.assertEqual(thr_spec["base"], "vehicle")
        self.assertEqual(thr_spec["offset"].upper(), "+0X760")

    def test_rpm_bandit(self) -> None:
        off = _floats_from_snap(
            {"floats_rpm": [{"base": "vehicle", "offset": "+114", "f": 351.5}]},
            "floats_rpm",
        )
        full = _floats_from_snap(
            {"floats_rpm": [{"base": "vehicle", "offset": "+114", "f": 434.4}]},
            "floats_rpm",
        )
        ranked = rank_rpm_candidates(off, full)
        self.assertTrue(ranked)
        self.assertEqual(ranked[0][1], ("vehicle", 0x114))


if __name__ == "__main__":
    unittest.main()
