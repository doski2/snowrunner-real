"""
Tests Fase 3: peso, carga y remolque CK1500.

Ejecutar:
  python -m unittest camiones.ck1500.test_simulacion_carga -v
  python simular_carga.py
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace

from sim.core import (
    CARGO_CATALOG,
    CARGO_TEST_SURFACES,
    ENGINE_I6,
    LOAD_SCENARIOS,
    SCOUT_TRAILER_OFFROAD_CARGO_KG,
    TIRES,
    VEHICLE_I6,
    SurfaceConfig,
    VehicleConfig,
    apply_load,
    run_cargo_matrix,
    run_sim,
    sample_at,
    summarize_cargo_vs_empty,
    total_mass_kg,
)

MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)
ASPHALT = SurfaceConfig("Asfalto", "asphalt")


def _offroad_diff() -> VehicleConfig:
    """Offroad + diff lock con perfil de friccion coherente (tire + tire_name)."""
    return replace(
        VEHICLE_I6,
        tire=TIRES["offroad"],
        tire_name="offroad",
        diff_lock=True,
    )


def export_cargo_study() -> dict:
    matrix = run_cargo_matrix()
    summary = summarize_cargo_vs_empty(matrix)
    catalog = [
        {"id": c.id, "label": c.label, "slots": c.slots, "mass_kg": c.mass_kg}
        for c in CARGO_CATALOG
    ]
    scenarios = [
        {
            "id": s.id,
            "label": s.label,
            "addon_kg": s.addon_mass_kg,
            "cargo_kg": s.cargo_mass_kg,
            "trailer_kg": s.trailer_mass_kg,
            "trailer_cargo_kg": s.trailer_cargo_mass_kg,
        }
        for s in LOAD_SCENARIOS
    ]
    highlights = [
        r
        for r in matrix
        if r.scenario_id in ("vacio", "trailer_metal_planks", "mision_pesada")
        and r.tire == "offroad"
        and r.diff_lock
        and r.surface in ("Barro", "Asfalto", "Cuesta 12%")
    ]
    return {
        "catalog": catalog,
        "scenarios": scenarios,
        "matrix": [r.__dict__ for r in matrix],
        "summary": summary,
        "highlights": [r.__dict__ for r in highlights],
    }


class TestTotalMass(unittest.TestCase):
    def test_vacio_is_chassis_only(self) -> None:
        veh = apply_load(VEHICLE_I6, LOAD_SCENARIOS[0])
        self.assertEqual(total_mass_kg(veh), 1750)

    def test_mision_pesada_total(self) -> None:
        scenario = next(s for s in LOAD_SCENARIOS if s.id == "mision_pesada")
        veh = apply_load(VEHICLE_I6, scenario)
        expected = 1750 + 220 + SCOUT_TRAILER_OFFROAD_CARGO_KG + 2500
        self.assertEqual(total_mass_kg(veh), expected)


class TestCargoPhysics(unittest.TestCase):
    def test_heavier_slower_on_asphalt(self) -> None:
        empty = apply_load(_offroad_diff(), LOAD_SCENARIOS[0])
        loaded = apply_load(
            _offroad_diff(),
            next(s for s in LOAD_SCENARIOS if s.id == "mision_pesada"),
        )
        s_empty = run_sim(empty, ENGINE_I6, ASPHALT, 45.0)
        s_loaded = run_sim(loaded, ENGINE_I6, ASPHALT, 45.0)
        self.assertGreater(sample_at(s_empty, 30.0), sample_at(s_loaded, 30.0))

    def test_trailer_reduces_barro_speed(self) -> None:
        base = _offroad_diff()
        empty = apply_load(base, LOAD_SCENARIOS[0])
        trailer = apply_load(
            base, next(s for s in LOAD_SCENARIOS if s.id == "trailer_metal_planks")
        )
        v_empty = sample_at(run_sim(empty, ENGINE_I6, MUD, 60.0, low_gear=True), 30.0)
        v_trailer = sample_at(run_sim(trailer, ENGINE_I6, MUD, 60.0, low_gear=True), 30.0)
        self.assertGreater(v_empty, v_trailer)

    def test_more_mass_improves_traction_cap_not_speed_in_mud(self) -> None:
        """Mas peso sube limite de traccion pero tambien resistencia al barro."""
        base = _offroad_diff()
        light = apply_load(base, LOAD_SCENARIOS[0])
        heavy = apply_load(base, next(s for s in LOAD_SCENARIOS if s.id == "trailer_bricks"))
        s_light = run_sim(light, ENGINE_I6, MUD, 60.0, low_gear=True)
        s_heavy = run_sim(heavy, ENGINE_I6, MUD, 60.0, low_gear=True)
        self.assertGreater(s_light.state.traction_used, 0)
        self.assertGreaterEqual(s_light.speeds_kmh[-1], s_heavy.speeds_kmh[-1])


class TestCargoMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = run_cargo_matrix()
        cls.summary = summarize_cargo_vs_empty(cls.matrix)

    def test_matrix_size(self) -> None:
        n_scenarios = len(LOAD_SCENARIOS)
        n_tires = 2
        n_surfaces = len(CARGO_TEST_SURFACES)
        self.assertEqual(len(self.matrix), n_scenarios * n_tires * n_surfaces)

    def test_deltas_present_for_loaded_scenarios(self) -> None:
        self.assertGreater(len(self.summary["deltas"]), 0)
        ids = {d["scenario"] for d in self.summary["deltas"]}
        self.assertIn("mision_pesada", ids)

    def test_mision_pesada_slower_than_vacio_barro(self) -> None:
        row = next(
            d
            for d in self.summary["deltas"]
            if d["scenario"] == "mision_pesada"
            and d["surface"] == "Barro"
            and d["tire"] == "offroad"
            and d["diff_lock"]
        )
        self.assertLess(row["delta_v30"], 0)


class TestExport(unittest.TestCase):
    def test_export_json_roundtrip(self) -> None:
        data = export_cargo_study()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "simulacion_carga.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            with open(out, encoding="utf-8") as f:
                loaded = json.load(f)
        self.assertIn("matrix", loaded)
        self.assertGreater(len(loaded["highlights"]), 0)
        self.assertEqual(len(loaded["matrix"]), len(data["matrix"]))


if __name__ == "__main__":
    unittest.main()
