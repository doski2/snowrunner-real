"""
Tests parches y simulador Tatra T813.

Ejecutar:
  python -m unittest camiones.t813.test -v
  python -m camiones.t813.simulador
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from camiones.registry import EMPTY_MASS_KG, VEHICLES, merge_patches, vehicle_id_from_ce
from camiones.t813 import simulador as sim_t813
from camiones.t813.patches import PATCHES as T813_PATCHES
from sim.core import SurfaceConfig

ENGINE_REAL_T813_KZGT = sim_t813.ENGINE_REAL_T813_KZGT
ENGINE_STOCK_T813_KZGT = sim_t813.ENGINE_STOCK_T813_KZGT
T813_MUD_IMMERSION_RATE = sim_t813.T813_MUD_IMMERSION_RATE
T813_MUD_RESIST_MULT = sim_t813.T813_MUD_RESIST_MULT
TIRES = sim_t813.TIRES
VEHICLE_REAL = sim_t813.VEHICLE_REAL
VEHICLE_STOCK = sim_t813.VEHICLE_STOCK
make_vehicle = sim_t813.make_vehicle
run_sim = sim_t813.run_sim
sample_at = sim_t813.sample_at

MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)
T813_TRUCK_ARC = "[media]/_dlc/dlc_4/classes/trucks/tatra_t813.xml"


class TestT813Registry(unittest.TestCase):
    def test_vehicle_registered(self) -> None:
        self.assertIn("t813", VEHICLES)
        self.assertEqual(VEHICLES["t813"].xml_file, "tatra_t813.xml")
        self.assertEqual(VEHICLES["t813"].ce_id, "s_tatra_t813")

    def test_empty_mass_for_ce(self) -> None:
        self.assertEqual(EMPTY_MASS_KG["t813"], 14571.0)
        self.assertEqual(VEHICLE_REAL.mass_kg, EMPTY_MASS_KG["t813"])

    def test_ce_id_alias(self) -> None:
        self.assertEqual(vehicle_id_from_ce("s_tatra_t813"), "t813")
        self.assertEqual(vehicle_id_from_ce("tatra_t813"), "t813")

    def test_merge_includes_t813_files(self) -> None:
        merged = merge_patches(["t813"])
        self.assertIn(T813_TRUCK_ARC, merged)
        self.assertIn("[media]/classes/engines/e_ru_special.xml", merged)
        self.assertIn(
            "[media]/_dlc/dlc_11/classes/wheels/wheels_superheavy_mudtires.xml",
            merged,
        )


class TestT813Patches(unittest.TestCase):
    def test_responsiveness_reduced(self) -> None:
        pairs = T813_PATCHES[T813_TRUCK_ARC]
        self.assertTrue(any('Responsiveness="0.14"' in new for _old, new in pairs))

    def test_msh_i_substance_nerfed(self) -> None:
        pairs = T813_PATCHES[
            "[media]/_dlc/dlc_11/classes/wheels/wheels_superheavy_mudtires.xml"
        ]
        self.assertTrue(any('SubstanceFriction="2.2"' in new for _old, new in pairs))


class TestT813Sim(unittest.TestCase):
    def test_real_heavier_than_stock(self) -> None:
        self.assertGreater(VEHICLE_REAL.mass_kg, VEHICLE_STOCK.mass_kg)

    def test_msh_i_substance_mod(self) -> None:
        self.assertEqual(TIRES["msh_i"]["substance"], 2.2)

    def test_awd_diff_stock(self) -> None:
        self.assertTrue(VEHICLE_REAL.diff_lock)
        self.assertEqual(VEHICLE_REAL.drive_layout, "awd")
        self.assertEqual(VEHICLE_REAL.num_wheels, 8)

    def test_real_has_mud_cal(self) -> None:
        self.assertEqual(VEHICLE_REAL.mud_immersion_rate, T813_MUD_IMMERSION_RATE)
        self.assertEqual(VEHICLE_REAL.mud_resist_mult, T813_MUD_RESIST_MULT)

    def test_engine_for_t813_xml_name(self) -> None:
        kzgt = sim_t813.engine_for_t813("t813_kzgt", "ru_special_engine_1")
        self.assertEqual(kzgt.torque, ENGINE_REAL_T813_KZGT.torque)
        top = sim_t813.engine_for_t813("t813_kzgt", "ru_special_engine_2")
        self.assertGreater(top.torque, kzgt.torque)

    def test_real_slower_than_stock_mud(self) -> None:
        a = run_sim(VEHICLE_STOCK, ENGINE_STOCK_T813_KZGT, MUD, 60.0, low_gear=True)
        b = run_sim(VEHICLE_REAL, ENGINE_REAL_T813_KZGT, MUD, 60.0, low_gear=True)
        self.assertGreater(max(a.speeds_kmh), max(b.speeds_kmh))

    def test_loaded_slower(self) -> None:
        loaded = replace(
            VEHICLE_REAL,
            trailer_mass_kg=sim_t813.LOAD_SEMI_EMPTY,
            trailer_cargo_mass_kg=sim_t813.LOAD_SEMI_FULL,
        )
        self.assertGreater(
            max(run_sim(VEHICLE_REAL, ENGINE_REAL_T813_KZGT, MUD, 90.0, low_gear=True).speeds_kmh),
            max(run_sim(loaded, ENGINE_REAL_T813_KZGT, MUD, 90.0, low_gear=True).speeds_kmh),
        )


if __name__ == "__main__":
    unittest.main()
