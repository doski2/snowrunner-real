"""Tests pedal_hunt."""

from __future__ import annotations

import unittest

from cheat_engine.pedal_hunt import (
    KeySweepStats,
    ScanTarget,
    _norm_f32,
    _norm_u8,
    _ptr_for_label,
    diff_pedal_maps,
    rank_pedal_sweep,
    spec_from_hunt_row,
    update_sweep_stats,
)


class TestPedalHunt(unittest.TestCase):
    def test_norm_f32(self) -> None:
        self.assertAlmostEqual(_norm_f32(0.25) or 0, 0.25)
        self.assertAlmostEqual(_norm_f32(25.0) or 0, 0.25)

    def test_norm_u8(self) -> None:
        self.assertAlmostEqual(_norm_u8(64) or 0, 64 / 255.0, places=2)

    def test_diff_target(self) -> None:
        a = {("tc+010", 0x100, "f32"): 0.0}
        b = {("tc+010", 0x100, "f32"): 0.25}
        rows = diff_pedal_maps(a, b, target_delta=0.25)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["delta"], 0.25)
        self.assertEqual(rows[0]["base"], "tc+010")

    def test_ptr_for_label(self) -> None:
        targets = [
            ScanTarget("truck_control", 0x10000, 0x800),
            ScanTarget("tc+008→vehicle", 0x20000, 0x600),
        ]
        self.assertEqual(_ptr_for_label(targets, "tc+008→vehicle"), 0x20000)

    def test_spec_chain(self) -> None:
        spec = spec_from_hunt_row({"base": "tc+018", "offset": 0x40, "kind": "u8"})
        self.assertEqual(spec["chain"], "TRUCK_CONTROL")
        self.assertEqual(spec["offset"], "+0x040")

    def test_sweep_rank_pedal(self) -> None:
        stats: dict = {}
        update_sweep_stats(stats, {("tc+018", 0x40, "f32"): 0.0})
        update_sweep_stats(stats, {("tc+018", 0x40, "f32"): 1.0})
        update_sweep_stats(stats, {("tc+018", 0x40, "f32"): 0.05})
        update_sweep_stats(stats, {("tc+018", 0x40, "f32"): 0.95})
        rows = rank_pedal_sweep(stats)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["base"], "tc+018")
        self.assertGreater(rows[0]["span"], 0.8)

    def test_sweep_reject_motor_stuck(self) -> None:
        stats = {("vehicle", 0x760, "f32"): KeySweepStats()}
        for _ in range(5):
            stats[("vehicle", 0x760, "f32")].push(0.98)
        stats[("vehicle", 0x760, "f32")].push(1.0)
        rows = rank_pedal_sweep(stats)
        self.assertEqual(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
