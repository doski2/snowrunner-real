"""
Tests parches y simulador GMC MH9500.

Ejecutar:
  python -m unittest camiones.mh9500.test -v
  python -m camiones.mh9500.simulador
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from camiones.mh9500 import simulador as sim_mh
from camiones.mh9500.patches import PATCHES as MH9500_PATCHES
from camiones.registry import EMPTY_MASS_KG, VEHICLES, merge_patches, vehicle_id_from_ce
from sim.core import SurfaceConfig

ENGINE_REAL_MH = sim_mh.ENGINE_REAL_MH
ENGINE_STOCK_MH = sim_mh.ENGINE_STOCK_MH
MH_MUD_IMMERSION_RATE = sim_mh.MH_MUD_IMMERSION_RATE
MH_MUD_RESIST_MULT = sim_mh.MH_MUD_RESIST_MULT
TIRES = sim_mh.TIRES
VEHICLE_REAL = sim_mh.VEHICLE_REAL
VEHICLE_REAL_AWD = sim_mh.VEHICLE_REAL_AWD
VEHICLE_REAL_OFFROAD = sim_mh.VEHICLE_REAL_OFFROAD
VEHICLE_STOCK = sim_mh.VEHICLE_STOCK
make_vehicle = sim_mh.make_vehicle
run_sim = sim_mh.run_sim
sample_at = sim_mh.sample_at

MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)


class TestMh9500Patches(unittest.TestCase):
    def test_vehicle_registered(self) -> None:
        self.assertIn("mh9500", VEHICLES)
        self.assertEqual(VEHICLES["mh9500"].xml_file, "gmc_9500.xml")
        self.assertEqual(VEHICLES["mh9500"].ce_id, "s_gmc_9500")

    def test_ce_id_aliases(self) -> None:
        self.assertEqual(vehicle_id_from_ce("s_gmc_9500"), "mh9500")
        self.assertEqual(vehicle_id_from_ce("s_gmc9500"), "mh9500")

    def test_empty_mass_for_ce(self) -> None:
        self.assertEqual(EMPTY_MASS_KG["mh9500"], 8200.0)
        self.assertEqual(VEHICLE_REAL.mass_kg, EMPTY_MASS_KG["mh9500"])

    def test_merge_includes_gmc_truck_only(self) -> None:
        merged = merge_patches(["mh9500"])
        self.assertIn("[media]/classes/trucks/gmc_9500.xml", merged)
        self.assertEqual(len(merged), 1)

    def test_mass_patches_on_truck_xml(self) -> None:
        pairs = MH9500_PATCHES["[media]/classes/trucks/gmc_9500.xml"]
        self.assertTrue(any('Mass="4000"' in new for _old, new in pairs))
        self.assertTrue(any('Mass="2100"' in new for _old, new in pairs))


class TestMh9500Sim(unittest.TestCase):
    def test_six_wheels_rwd(self) -> None:
        self.assertEqual(VEHICLE_REAL.num_wheels, 6)
        self.assertEqual(VEHICLE_REAL.drive_layout, "rwd")

    def test_real_heavier_than_stock(self) -> None:
        self.assertGreater(VEHICLE_REAL.mass_kg, VEHICLE_STOCK.mass_kg)

    def test_highway_substance_mod(self) -> None:
        self.assertEqual(TIRES["highway"]["substance"], 0.5)

    def test_offroad_setup_has_mud_cal(self) -> None:
        self.assertTrue(VEHICLE_REAL_OFFROAD.diff_lock)
        self.assertEqual(VEHICLE_REAL_OFFROAD.drive_layout, "awd")
        self.assertEqual(VEHICLE_REAL_OFFROAD.tire_name, "offroad")
        self.assertEqual(VEHICLE_REAL_OFFROAD.mud_immersion_rate, MH_MUD_IMMERSION_RATE)
        self.assertEqual(VEHICLE_REAL_OFFROAD.mud_resist_mult, MH_MUD_RESIST_MULT)

    def test_make_vehicle_applies_mud_cal_on_offroad_awd(self) -> None:
        veh = make_vehicle("offroad", base=VEHICLE_REAL_AWD)
        self.assertEqual(veh.mud_immersion_rate, MH_MUD_IMMERSION_RATE)
        self.assertEqual(veh.mud_resist_mult, MH_MUD_RESIST_MULT)

    def test_make_vehicle_highway_awd_no_mud_cal(self) -> None:
        veh = make_vehicle("highway", base=VEHICLE_REAL_AWD)
        self.assertEqual(veh.mud_immersion_rate, 1.0)
        self.assertEqual(veh.mud_resist_mult, 1.0)

    def test_stock_faster_than_real_asphalt(self) -> None:
        asphalt = SurfaceConfig("Asfalto", "asphalt")
        a = run_sim(VEHICLE_STOCK, ENGINE_STOCK_MH, asphalt, 50.0)
        b = run_sim(VEHICLE_REAL, ENGINE_REAL_MH, asphalt, 50.0)
        self.assertGreater(a.speeds_kmh[-1], b.speeds_kmh[-1])

    def test_offroad_better_than_highway_mud(self) -> None:
        hw = run_sim(VEHICLE_REAL, ENGINE_REAL_MH, MUD, 120.0, low_gear=True)
        oroad = run_sim(VEHICLE_REAL_OFFROAD, ENGINE_REAL_MH, MUD, 120.0, low_gear=True)
        self.assertEqual(max(hw.speeds_kmh), 0.0)
        self.assertGreater(max(oroad.speeds_kmh), 0.0)

    def test_offroad_mud_crawl_slow(self) -> None:
        v30 = sample_at(
            run_sim(VEHICLE_REAL_OFFROAD, ENGINE_REAL_MH, MUD, 60.0, low_gear=True),
            30.0,
        )
        self.assertLess(v30, 8.0)
        self.assertGreater(v30, 0.0)


if __name__ == "__main__":
    unittest.main()
