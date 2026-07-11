"""Tests banco_drive (formato y aceleracion)."""

from __future__ import annotations

import unittest

from cheat_engine.banco_drive import (
    FieldTracker,
    _clamp01,
    compute_accel_kmh_s,
    format_bar,
    format_banco_line,
    throttle_label,
)


class TestBancoDrive(unittest.TestCase):
    def test_format_bar_empty(self) -> None:
        self.assertEqual(format_bar(0.0), "[" + "." * 24 + "]")
        self.assertEqual(format_bar(1.0), "[" + "#" * 24 + "]")

    def test_accel(self) -> None:
        a, last = compute_accel_kmh_s(10.0, 1.0, None)
        self.assertIsNone(a)
        self.assertEqual(last, (1.0, 10.0))
        a, _ = compute_accel_kmh_s(20.0, 2.0, (1.0, 10.0))
        self.assertAlmostEqual(a or 0, 10.0)

    def test_throttle_label(self) -> None:
        self.assertEqual(throttle_label(0.0), "gas SUELTO")
        self.assertEqual(throttle_label(0.95), "gas FONDO")
        self.assertEqual(throttle_label(0.5), "acelerando")

    def test_field_tracker(self) -> None:
        tr = FieldTracker(window_s=10.0)
        tr.push(1.0, {"v75c": 0.0})
        tr.push(2.0, {"v75c": 0.4})
        self.assertAlmostEqual(tr.range("v75c"), 0.4)
        self.assertEqual(tr.best_tag(), "v75c")

    def test_format_line(self) -> None:
        line = format_banco_line(
            t_s=1.5,
            thr_cal=1.0,
            thr_pedal=0.42,
            pedal_tag="v75c",
            cal_bad=True,
            rpm=1200.0,
            speed_kmh=15.0,
            accel_kmh_s=3.2,
        )
        self.assertIn("0.420", line)
        self.assertIn("1200", line)
        self.assertIn("acelerando", line)


class TestClamp(unittest.TestCase):
    def test_clamp(self) -> None:
        self.assertEqual(_clamp01(1.5), 1.0)
        self.assertEqual(_clamp01(None), 0.0)


if __name__ == "__main__":
    unittest.main()
