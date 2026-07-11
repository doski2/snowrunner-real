"""
Tests del simulador CK1500 (unittest, sin dependencias extra).

Ejecutar:
  python -m unittest camiones.ck1500.test_simulacion -v
  python -m sim.core
"""

from __future__ import annotations
import unittest
from dataclasses import replace
from typing import TypeVar

from sim.core import (
    DT,
    ENGINE_I6,
    SURFACES,
    TIRES,
    VEHICLE_I6,
    CONFIGS,
    SurfaceConfig,
    diff_efficiency,
    engine_fuel_mult,
    engine_torque_mult,
    make_vehicle,
    run_config_comparison,
    run_damage_test,
    run_scenarios,
    run_sim,
    sample_at,
    surface_mu,
    time_to_kmh,
)

T = TypeVar("T")

# --- Referencia FASE-1 -------------------------------------------------------

ASPHALT = SurfaceConfig("Asfalto", "asphalt")
MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)

I6_ASPHALT_V30_KMH = 44.0
STOCK_T097_S = 14.6
DIFF_LOCK_V30_KMH = 39.9


def _require(value: T | None) -> T:
    if value is None:
        raise AssertionError("valor inesperado None")
    return value


def _by_key(rows: list[dict], field: str, value: str) -> dict:
    for row in rows:
        if row[field] == value:
            return row
    raise AssertionError(f"{field}={value!r} no encontrado")


# --- Unitarios ---------------------------------------------------------------


class TestHelpers(unittest.TestCase):
    def test_time_to_kmh_interpolates(self) -> None:
        result = time_to_kmh([0.0, 50.0, 100.0], [0.0, 1.0, 2.0], 75.0)
        self.assertEqual(result, 1.5)

    def test_time_to_kmh_none_if_not_reached(self) -> None:
        self.assertIsNone(time_to_kmh([10.0, 20.0], [0.0, 1.0], 97.0))

    def test_engine_damage_reduces_torque(self) -> None:
        healthy = replace(ENGINE_I6, damage_pct=0.0)
        damaged = replace(ENGINE_I6, damage_pct=0.8)
        self.assertEqual(engine_torque_mult(healthy), 1.0)
        self.assertAlmostEqual(engine_torque_mult(damaged), 0.8)
        self.assertGreater(engine_fuel_mult(damaged), engine_fuel_mult(healthy))

    def test_diff_lock_full_efficiency_on_mud(self) -> None:
        mus = [0.3, 0.1, 0.2, 0.15]
        open_eff = diff_efficiency(make_vehicle("offroad"), MUD, mus)
        lock_eff = diff_efficiency(make_vehicle("offroad", diff_lock=True), MUD, mus)
        self.assertLess(open_eff, 1.0)
        self.assertEqual(lock_eff, 1.0)

    def test_highway_worse_than_offroad_on_mud(self) -> None:
        mu_hw = surface_mu(TIRES["highway"], MUD, 0.2)
        mu_or = surface_mu(TIRES["offroad"], MUD, 0.2)
        self.assertLess(mu_hw, mu_or)

    def test_chains_ignore_ice(self) -> None:
        ice = SurfaceConfig("Hielo", "ice")
        self.assertLess(surface_mu(TIRES["highway"], ice, 0.0), 0.2)
        self.assertGreater(surface_mu(TIRES["chains"], ice, 0.0), 0.5)


class TestRunSim(unittest.TestCase):
    def test_series_length_matches_duration(self) -> None:
        duration = 2.0
        series = run_sim(VEHICLE_I6, ENGINE_I6, ASPHALT, duration)
        steps = int(duration / DT)
        self.assertEqual(len(series.speeds_kmh), steps)
        self.assertEqual(series.times[0], 0.0)
        self.assertAlmostEqual(series.times[-1], (steps - 1) * DT)

    def test_fuel_increases_under_throttle(self) -> None:
        series = run_sim(VEHICLE_I6, ENGINE_I6, ASPHALT, 10.0)
        self.assertGreater(series.state.fuel_used, 0.0)

    def test_speeds_non_negative_on_all_surfaces(self) -> None:
        for surface in SURFACES:
            with self.subTest(surface=surface.name):
                series = run_sim(VEHICLE_I6, ENGINE_I6, surface, 5.0)
                self.assertTrue(all(v >= 0.0 for v in series.speeds_kmh))


# --- Calibracion (regresion FASE-1) ------------------------------------------


class TestCalibration(unittest.TestCase):
    """Simulaciones costosas compartidas en setUpClass."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.asphalt = run_sim(VEHICLE_I6, ENGINE_I6, ASPHALT, 80.0)
        cls.t097_i6 = time_to_kmh(cls.asphalt.speeds_kmh, cls.asphalt.times, 97.0)
        cls.configs = run_config_comparison()
        cls.scenarios = run_scenarios()
        cls.damage = run_damage_test()

    def test_i6_asphalt_v30_calibrated(self) -> None:
        v30 = sample_at(self.asphalt, 30.0)
        self.assertAlmostEqual(v30, I6_ASPHALT_V30_KMH, delta=3.0)

    def test_i6_asphalt_not_hypercar(self) -> None:
        """Con arrastre CK1500, no alcanza 97 km/h en 80 s de WOT."""
        self.assertIsNone(self.t097_i6)

    def test_stock_faster_than_i6(self) -> None:
        stock_veh, stock_eng = CONFIGS[0]
        stock_v60 = sample_at(run_sim(stock_veh, stock_eng, ASPHALT, 80.0), 60.0)
        i6_v60 = sample_at(self.asphalt, 60.0)
        self.assertGreater(stock_v60, i6_v60)

    def test_mud_highway_stuck(self) -> None:
        series = run_sim(make_vehicle("highway"), ENGINE_I6, MUD, 45.0, low_gear=True)
        self.assertLess(sample_at(series, 30.0), 5.0)

    def test_mud_offroad_moves(self) -> None:
        v30 = sample_at(
            run_sim(make_vehicle("offroad"), ENGINE_I6, MUD, 45.0, low_gear=True),
            30.0,
        )
        self.assertGreater(v30, 10.0)
        self.assertLess(v30, 45.0)
    def test_diff_lock_faster_in_mud(self) -> None:
        no_lock = _by_key(self.scenarios, "label", "Barro offroad sin diff")
        with_lock = _by_key(self.scenarios, "label", "Barro offroad CON diff")
        self.assertGreater(with_lock["v30"], no_lock["v30"])
        self.assertAlmostEqual(with_lock["v30"], DIFF_LOCK_V30_KMH, delta=5.0)

    def test_snorkel_helps_deep_water(self) -> None:
        no_snork = _by_key(self.scenarios, "label", "Agua profunda sin snorkel")
        snork = _by_key(self.scenarios, "label", "Agua profunda con snorkel")
        self.assertLess(no_snork["v30"], 5.0)
        self.assertGreater(snork["v30"], 15.0)

    def test_damaged_engine_slower(self) -> None:
        self.assertGreater(self.damage["motor_sano_v60"], self.damage["motor_danado_v60"])
        self.assertAlmostEqual(self.damage["torque_mult_danado"], 0.8, delta=0.05)

    def test_mud_tire_ranking_on_mud(self) -> None:
        v30 = {
            tire: sample_at(
                run_sim(make_vehicle(tire), ENGINE_I6, MUD, 45.0, low_gear=True),
                30.0,
            )
            for tire in ("highway", "offroad", "mudtires")
        }
        self.assertLess(v30["highway"], v30["offroad"])
        self.assertGreater(v30["mudtires"], v30["offroad"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
