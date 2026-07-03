"""Tests grabar_telemetria.py (sin juego)."""

from __future__ import annotations

import argparse
import unittest

from grabar_telemetria import _pick_protocol


class TestGrabarTelemetria(unittest.TestCase):
    def test_pick_protocol_by_id(self) -> None:
        args = argparse.Namespace(protocol="km_f2_barro_tm2")
        p = _pick_protocol(args)
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p.vehicle_id, "marshall")

    def test_pick_protocol_unknown(self) -> None:
        args = argparse.Namespace(protocol="no_existe")
        self.assertIsNone(_pick_protocol(args))


if __name__ == "__main__":
    unittest.main()
