"""
Tests Fase 4: auditoria terreno juego vs real K10.

Ejecutar:
  python -m unittest camiones.ck1500.test_simulacion_terreno -v
  python simular_terreno.py
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from sim.core import (
    REAL_K10_BANDS,
    SURFACES,
    TERRAIN_GAME,
    run_terrain_audit,
    summarize_terrain_audit,
)


def export_terrain_study() -> dict:
    cells = run_terrain_audit()
    summary = summarize_terrain_audit(cells)
    return {
        "game_factors": {
            kind: {
                "extrudable": gf.extrudable,
                "uses_substance_friction": gf.uses_substance_friction,
                "map_layers": gf.map_layers,
                "patchable_per_truck": gf.patchable_per_truck,
            }
            for kind, gf in TERRAIN_GAME.items()
        },
        "real_bands": {
            name: {
                "stock": [b.stock_min, b.stock_max],
                "equipped": [b.equipped_min, b.equipped_max],
                "note": b.equipped_note,
            }
            for name, b in REAL_K10_BANDS.items()
        },
        "surfaces": [s.name for s in SURFACES],
        "audit": [c.__dict__ for c in cells],
        "summary": summary,
    }


class TestTerrainCatalog(unittest.TestCase):
    def test_all_surfaces_have_real_band(self) -> None:
        for s in SURFACES:
            self.assertIn(s.name, REAL_K10_BANDS, s.name)

    def test_all_surface_kinds_in_game_table(self) -> None:
        for s in SURFACES:
            self.assertIn(s.kind, TERRAIN_GAME, s.kind)

    def test_terrain_not_patchable_per_truck(self) -> None:
        for gf in TERRAIN_GAME.values():
            self.assertFalse(gf.patchable_per_truck)


class TestTerrainAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cells = run_terrain_audit()
        cls.summary = summarize_terrain_audit(cls.cells)

    def test_audit_covers_all_surfaces(self) -> None:
        names = {c.surface for c in self.cells}
        for s in SURFACES:
            self.assertIn(s.name, names)

    def test_highway_stuck_in_mud(self) -> None:
        row = next(c for c in self.cells if c.surface == "Barro" and c.tire == "highway")
        self.assertLess(row.v30_kmh, 5.0)
        self.assertEqual(row.realism, "game_harder")

    def test_offroad_moves_in_mud(self) -> None:
        row = next(c for c in self.cells if c.surface == "Barro" and c.tire == "offroad")
        self.assertGreater(row.v30_kmh, 10.0)

    def test_chains_better_than_highway_on_ice(self) -> None:
        hw = next(c for c in self.cells if c.surface == "Hielo" and c.tire == "highway")
        ch = next(c for c in self.cells if c.surface == "Hielo" and c.tire == "chains")
        self.assertGreater(ch.v30_kmh, hw.v30_kmh)

    def test_asphalt_fast_highway(self) -> None:
        row = next(c for c in self.cells if c.surface == "Asfalto" and c.tire == "highway")
        self.assertGreater(row.v30_kmh, 80.0)
        self.assertEqual(row.realism, "ok")

    def test_summary_has_highlights(self) -> None:
        self.assertGreater(len(self.summary["highlights"]), 0)

    def test_no_ck1500_terrain_patches(self) -> None:
        self.assertFalse(self.summary["patchable_terrain_xml"])
        self.assertEqual(self.summary["ck1500_terrain_patches"], [])


class TestExport(unittest.TestCase):
    def test_export_json_roundtrip(self) -> None:
        data = export_terrain_study()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "simulacion_terreno.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            with open(out, encoding="utf-8") as f:
                loaded = json.load(f)
        self.assertIn("audit", loaded)
        self.assertEqual(len(loaded["audit"]), len(data["audit"]))
        self.assertIn("summary", loaded)


if __name__ == "__main__":
    unittest.main()
