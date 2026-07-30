"""
Tests parches y simulador KRS 58 Bandit.

Ejecutar:
  python -m unittest camiones.bandit.test -v
  python -m camiones.bandit.simulador
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from camiones.bandit import simulador as sim_bandit
from camiones.bandit.patches import PATCHES as BANDIT_PATCHES
from camiones.registry import EMPTY_MASS_KG, VEHICLES, merge_patches, vehicle_id_from_ce
from sim.core import SurfaceConfig

ENGINE_REAL_BANDIT_LAZ = sim_bandit.ENGINE_REAL_BANDIT_LAZ
ENGINE_STOCK_BANDIT_LAZ = sim_bandit.ENGINE_STOCK_BANDIT_LAZ
TIRES = sim_bandit.TIRES
VEHICLE_REAL = sim_bandit.VEHICLE_REAL
VEHICLE_STOCK = sim_bandit.VEHICLE_STOCK
make_vehicle = sim_bandit.make_vehicle
run_sim = sim_bandit.run_sim

MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)
BANDIT_TRUCK_ARC = "[media]/_dlc/dlc_2_2/classes/trucks/krs_58_bandit.xml"


class TestBanditRegistry(unittest.TestCase):
    def test_vehicle_registered(self) -> None:
        self.assertIn("bandit", VEHICLES)
        self.assertEqual(VEHICLES["bandit"].xml_file, "krs_58_bandit.xml")
        self.assertEqual(VEHICLES["bandit"].ce_id, "s_krs_58_bandit")

    def test_empty_mass_for_ce(self) -> None:
        self.assertEqual(EMPTY_MASS_KG["bandit"], 7600.0)
        self.assertEqual(VEHICLE_REAL.mass_kg, EMPTY_MASS_KG["bandit"])

    def test_ce_id_alias(self) -> None:
        self.assertEqual(vehicle_id_from_ce("s_krs_58_bandit"), "bandit")
        self.assertEqual(vehicle_id_from_ce("krs_58_bandit"), "bandit")

    def test_merge_includes_bandit_files(self) -> None:
        merged = merge_patches(["bandit"])
        self.assertIn(BANDIT_TRUCK_ARC, merged)
        self.assertIn("[media]/classes/engines/e_ru_truck_old.xml", merged)
        self.assertIn("[media]/classes/wheels/wheels_medium_double_front.xml", merged)


class TestBanditPatches(unittest.TestCase):
    def test_responsiveness_reduced(self) -> None:
        pairs = BANDIT_PATCHES[BANDIT_TRUCK_ARC]
        self.assertTrue(any('Responsiveness="0.18"' in new for _old, new in pairs))

    def test_engine_template_responsiveness(self) -> None:
        pairs = BANDIT_PATCHES["[media]/classes/engines/e_ru_truck_old.xml"]
        self.assertTrue(
            any('EngineResponsiveness="0.028"' in new for _old, new in pairs)
        )

    def test_uhd_substance_nerfed(self) -> None:
        pairs = BANDIT_PATCHES[
            "[media]/classes/wheels/wheels_medium_double_front.xml"
        ]
        self.assertTrue(any('SubstanceFriction="0.5"' in new for _old, new in pairs))


class TestBanditSim(unittest.TestCase):
    def test_real_heavier_than_stock(self) -> None:
        self.assertGreater(VEHICLE_REAL.mass_kg, VEHICLE_STOCK.mass_kg)

    def test_awd_diff_stock(self) -> None:
        self.assertTrue(VEHICLE_REAL.diff_lock)
        self.assertEqual(VEHICLE_REAL.drive_layout, "awd")
        self.assertEqual(VEHICLE_REAL.num_wheels, 8)

    def test_engine_for_bandit_xml_name(self) -> None:
        laz = sim_bandit.engine_for_bandit("bandit_real", "ru_truck_old_engine_0")
        self.assertEqual(laz.torque, ENGINE_REAL_BANDIT_LAZ.torque)
        t195 = sim_bandit.engine_for_bandit("bandit_real", "ru_truck_old_engine_1")
        self.assertGreater(t195.torque, laz.torque)

    def test_real_slower_than_stock_mud(self) -> None:
        a = run_sim(VEHICLE_STOCK, ENGINE_STOCK_BANDIT_LAZ, MUD, 60.0, low_gear=True)
        b = run_sim(VEHICLE_REAL, ENGINE_REAL_BANDIT_LAZ, MUD, 60.0, low_gear=True)
        self.assertGreater(max(a.speeds_kmh), max(b.speeds_kmh))

    def test_loaded_slower(self) -> None:
        loaded = replace(VEHICLE_REAL, cargo_mass_kg=sim_bandit.LOAD_FRAME_FULL)
        self.assertGreater(
            max(run_sim(VEHICLE_REAL, ENGINE_REAL_BANDIT_LAZ, MUD, 90.0, low_gear=True).speeds_kmh),
            max(run_sim(loaded, ENGINE_REAL_BANDIT_LAZ, MUD, 90.0, low_gear=True).speeds_kmh),
        )


if __name__ == "__main__":
    unittest.main()
