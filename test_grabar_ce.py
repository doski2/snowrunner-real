"""Tests helpers de grabar_ce.py (sin SnowRunner en ejecucion)."""

from __future__ import annotations

import argparse
import tempfile
import unittest

from grabar_ce import (
    _cargo_mass_kg,
    load_csv_rows,
    resolve_protocol,
    summarize_load_rows,
    summarize_terrain_rows,
)


class TestGrabarCeHelpers(unittest.TestCase):
    def test_summarize_terrain_rows(self) -> None:
        rows = [{"terrain_kind": "mud"}, {"terrain_kind": "hard"}, {"terrain_kind": "mud"}]
        counts = summarize_terrain_rows(rows)
        self.assertEqual(counts["mud"], 2)
        self.assertEqual(counts["hard"], 1)

    def test_summarize_load_rows(self) -> None:
        rows = [{"load_hint": "vacio"}, {"load_hint": "cargado"}]
        counts = summarize_load_rows(rows)
        self.assertEqual(counts["vacio"], 1)
        self.assertEqual(counts["cargado"], 1)

    def test_cargo_mass_kg_safe(self) -> None:
        self.assertEqual(_cargo_mass_kg({"cargo_mass_kg": "1200"}), 1200.0)
        self.assertEqual(_cargo_mass_kg({"payload_kg": "500"}), 500.0)
        self.assertEqual(_cargo_mass_kg({"cargo_mass_kg": "bad"}), 0.0)

    def test_resolve_protocol_manual(self) -> None:
        args = argparse.Namespace(auto=False, protocol="fs_f1_asfalto")
        self.assertEqual(resolve_protocol(args, {}), "fs_f1_asfalto")

    def test_resolve_protocol_auto_fleetstar(self) -> None:
        args = argparse.Namespace(auto=True, protocol="ignored")
        sample = {
            "vehicle_id": "s_fleetstar_f2070a",
            "terrain_kind": "hard",
            "surface_wheel": "hard",
            "wheel_grip": "0.95",
            "contact_avg": "0.80",
            "load_hint": "vacio",
            "payload_kg": "0",
        }
        self.assertEqual(resolve_protocol(args, sample), "fs_f1_asfalto")

    def test_load_csv_rows_roundtrip(self) -> None:
        csv_text = "t_s,vehicle_id,speed_kmh\n0.0,s_gmc_9500,5.0\n"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".csv") as f:
            f.write(csv_text)
            path = f.name
        try:
            rows = load_csv_rows(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["vehicle_id"], "s_gmc_9500")
        finally:
            import os

            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
