"""
Tests Fase 2: parche global de neumaticos vs solo CK1500.

Ejecutar:
  python -m unittest camiones.ck1500.test_simulacion_neumaticos -v
  python simular_neumaticos.py
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from sim.core import (
    HIGHWAY_SUBSTANCE_CK1500_MOD,
    PATCH_CK1500_HIGHWAY,
    PATCH_FACTORY,
    SCOUT_VEHICLES,
    TIRES,
    SurfaceConfig,
    build_scout_vehicle,
    compare_patch_delta,
    run_tire_patch_matrix,
    sim_v30,
    summarize_ck1500_vs_global,
    surface_mu,
    tire_catalog_for_plan,
)

MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)
ASPHALT = SurfaceConfig("Asfalto", "asphalt")


class TestTirePatchMatrix(unittest.TestCase):
    """Matriz completa: 4 planes x 2 scouts x 5 neumaticos x 5 superficies."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = run_tire_patch_matrix()
        cls.summary = summarize_ck1500_vs_global(cls.matrix)

    def test_matrix_size(self) -> None:
        # 4 planes x 2 scouts x 5 tires x 5 surfaces
        self.assertEqual(len(self.matrix), 4 * 2 * 5 * 5)

    def test_factory_ck1500_vs_generic_highway_substance(self) -> None:
        factory = [c for c in self.matrix if c.plan_id == "factory" and c.tire_type == "highway"]
        ck = next(c for c in factory if c.scout_id == "ck1500" and c.surface == "Barro")
        gen = next(c for c in factory if c.scout_id == "scout_generic" and c.surface == "Barro")
        self.assertEqual(ck.substance, 0.4)
        self.assertEqual(gen.substance, 0.2)

    def test_mod_tires_highway_substance(self) -> None:
        self.assertEqual(TIRES["highway"]["substance"], HIGHWAY_SUBSTANCE_CK1500_MOD)

    def test_ck1500_only_affects_ck1500_not_generic(self) -> None:
        gen_changes = self.summary["ck1500_only_changes_on_generic"]
        ck_changes = self.summary["ck1500_only_changes_on_ck1500"]
        self.assertEqual(len(gen_changes), 0, gen_changes)
        self.assertGreater(len(ck_changes), 0)
        highway_mud = next(
            r for r in ck_changes if r["tire"] == "highway" and r["surface"] == "Barro"
        )
        self.assertEqual(highway_mud["target_substance"], 0.5)
        self.assertEqual(highway_mud["base_substance"], 0.4)

    def test_ck1500_only_offroad_unchanged_on_both_scouts(self) -> None:
        deltas = compare_patch_delta(self.matrix, "factory", "ck1500_only")
        for scout in ("ck1500", "scout_generic"):
            off_mud = next(
                d
                for d in deltas
                if d["scout"] == scout and d["tire"] == "offroad" and d["surface"] == "Barro"
            )
            self.assertEqual(off_mud["delta_v30"], 0.0)
            self.assertEqual(off_mud["delta_substance"], 0.0)

    def test_global_template_changes_generic_highway_not_ck1500_override(self) -> None:
        deltas = compare_patch_delta(self.matrix, "factory", "global_template")
        gen_hw = next(
            d
            for d in deltas
            if d["scout"] == "scout_generic" and d["tire"] == "highway" and d["surface"] == "Barro"
        )
        ck_hw = next(
            d
            for d in deltas
            if d["scout"] == "ck1500" and d["tire"] == "highway" and d["surface"] == "Barro"
        )
        self.assertEqual(gen_hw["target_substance"], 0.35)
        self.assertGreater(gen_hw["delta_mu"], 0.0)
        self.assertEqual(ck_hw["target_substance"], 0.4)
        self.assertEqual(ck_hw["delta_substance"], 0.0)

    def test_global_buff_changes_all_tire_types_on_both_scouts(self) -> None:
        deltas = compare_patch_delta(self.matrix, "factory", "global_buff")
        for scout in ("ck1500", "scout_generic"):
            for tire in ("offroad", "mudtires", "chains"):
                row = next(
                    d
                    for d in deltas
                    if d["scout"] == scout and d["tire"] == tire and d["surface"] == "Barro"
                )
                self.assertGreater(row["delta_substance"], 0.0, f"{scout}/{tire}")

    def test_global_buff_more_cells_changed_than_ck1500_only(self) -> None:
        ck_only = compare_patch_delta(self.matrix, "factory", "ck1500_only")
        global_buf = compare_patch_delta(self.matrix, "factory", "global_buff")
        nonzero_ck = sum(
            1 for r in ck_only if r["delta_v30"] or r["delta_mu"] or r["delta_substance"]
        )
        nonzero_gl = sum(
            1 for r in global_buf if r["delta_v30"] or r["delta_mu"] or r["delta_substance"]
        )
        self.assertGreater(nonzero_gl, nonzero_ck)

    def test_tire_ranking_preserved_under_global_buff(self) -> None:
        """highway <= offroad <= mudtires en barro debe mantenerse tras buff global."""
        for plan in ("factory", "global_buff"):
            vals = {}
            for tire in ("highway", "offroad", "mudtires"):
                cell = next(
                    c
                    for c in self.matrix
                    if c.plan_id == plan
                    and c.scout_id == "ck1500"
                    and c.tire_type == tire
                    and c.surface == "Barro"
                )
                vals[tire] = cell.v30_kmh
            self.assertLessEqual(vals["highway"], vals["offroad"])
            self.assertLessEqual(vals["offroad"], vals["mudtires"])


class TestTirePatchScenarios(unittest.TestCase):
    """Escenarios concretos CK1500 I6."""

    def test_ck1500_highway_mud_mu_increases_with_patch(self) -> None:
        catalog = tire_catalog_for_plan(PATCH_FACTORY)
        base = build_scout_vehicle(SCOUT_VEHICLES[0], "highway", catalog, PATCH_FACTORY)
        patched = build_scout_vehicle(SCOUT_VEHICLES[0], "highway", catalog, PATCH_CK1500_HIGHWAY)
        mu_base = surface_mu(base.tire, MUD, 0.2)
        mu_patch = surface_mu(patched.tire, MUD, 0.2)
        self.assertGreater(mu_patch, mu_base)

    def test_asphalt_unchanged_by_substance_only_patch(self) -> None:
        catalog = tire_catalog_for_plan(PATCH_FACTORY)
        base = build_scout_vehicle(SCOUT_VEHICLES[0], "highway", catalog, PATCH_FACTORY)
        patched = build_scout_vehicle(SCOUT_VEHICLES[0], "highway", catalog, PATCH_CK1500_HIGHWAY)
        self.assertAlmostEqual(sim_v30(base, ASPHALT), sim_v30(patched, ASPHALT), delta=2.0)


def export_tire_study() -> dict:
    matrix = run_tire_patch_matrix()
    summary = summarize_ck1500_vs_global(matrix)
    deltas = {
        "ck1500_only": compare_patch_delta(matrix, "factory", "ck1500_only"),
        "global_template": compare_patch_delta(matrix, "factory", "global_template"),
        "global_buff": compare_patch_delta(matrix, "factory", "global_buff"),
    }
    nonzero = {
        key: [r for r in rows if r["delta_v30"] or r["delta_mu"] or r["delta_substance"]]
        for key, rows in deltas.items()
    }
    highlight = [
        {
            "plan_id": c.plan_id,
            "scout_id": c.scout_id,
            "tire_type": c.tire_type,
            "surface": c.surface,
            "v30_kmh": c.v30_kmh,
            "mu": c.mu,
            "substance": c.substance,
        }
        for c in matrix
        if c.tire_type == "highway" and c.surface == "Barro"
    ]
    return {
        "matrix_cells": len(matrix),
        "summary": summary,
        "nonzero_deltas": nonzero,
        "highlight_mud_highway": highlight,
    }


class TestExport(unittest.TestCase):
    def test_export_json_roundtrip(self) -> None:
        data = export_tire_study()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "simulacion_neumaticos.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            with open(out, encoding="utf-8") as f:
                loaded = json.load(f)
        self.assertEqual(loaded["matrix_cells"], 200)
        self.assertIn("highlight_mud_highway", loaded)
        self.assertGreater(len(loaded["nonzero_deltas"]["ck1500_only"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
