"""
Tests parches y simulador Kodiak C70.

Ejecutar:
  python -m unittest camiones.kodiak.test -v
  python -m camiones.kodiak.simulador
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from camiones.kodiak import simulador as sim_kd
from camiones.kodiak.patches import PATCHES as KODIAK_PATCHES
from camiones.registry import EMPTY_MASS_KG, VEHICLES, merge_patches, vehicle_id_from_ce
from sim.core import SurfaceConfig

ENGINE_REAL_FS = sim_kd.ENGINE_REAL_FS
KD_MUD_IMMERSION_RATE = sim_kd.KD_MUD_IMMERSION_RATE
KD_MUD_RESIST_MULT = sim_kd.KD_MUD_RESIST_MULT
LOAD_FRAME_FULL = sim_kd.LOAD_FRAME_FULL
TIRES = sim_kd.TIRES
VEHICLE_REAL = sim_kd.VEHICLE_REAL
VEHICLE_REAL_AWD_HIGHWAY = sim_kd.VEHICLE_REAL_AWD_HIGHWAY
VEHICLE_STOCK = sim_kd.VEHICLE_STOCK
make_vehicle = sim_kd.make_vehicle
run_sim = sim_kd.run_sim
sample_at = sim_kd.sample_at

MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)


class TestKodiakPatches(unittest.TestCase):
    def test_vehicle_registered(self) -> None:
        self.assertIn("kodiak", VEHICLES)
        self.assertEqual(VEHICLES["kodiak"].xml_file, "chevrolet_kodiakc70.xml")
        self.assertEqual(VEHICLES["kodiak"].ce_id, "s_chevrolet_kodiakc70")

    def test_ce_id_aliases(self) -> None:
        self.assertEqual(vehicle_id_from_ce("s_chevrolet_kodiakc70"), "kodiak")
        self.assertEqual(vehicle_id_from_ce("chevrolet_kodiakc70"), "kodiak")

    def test_empty_mass_for_ce(self) -> None:
        self.assertEqual(EMPTY_MASS_KG["kodiak"], 7900.0)
        self.assertEqual(VEHICLE_REAL.mass_kg, EMPTY_MASS_KG["kodiak"])

    def test_merge_includes_kodiak_files(self) -> None:
        merged = merge_patches(["kodiak"])
        self.assertIn("[media]/classes/trucks/chevrolet_kodiakc70.xml", merged)
        self.assertIn("[media]/classes/engines/e_us_truck_old.xml", merged)
        self.assertIn("[media]/classes/suspensions/s_chevrolet_kodiakC70.xml", merged)

    def test_engine_torque_reduced(self) -> None:
        pairs = KODIAK_PATCHES["[media]/classes/engines/e_us_truck_old.xml"]
        block = next(p for p in pairs if "us_truck_old_engine_0" in p[0])
        self.assertIn('Torque="92000"', block[1])


class TestKodiakSim(unittest.TestCase):
    def test_four_wheels(self) -> None:
        self.assertEqual(VEHICLE_REAL.num_wheels, 4)

    def test_real_heavier_than_stock(self) -> None:
        self.assertGreater(VEHICLE_REAL.mass_kg, VEHICLE_STOCK.mass_kg)

    def test_awd_highway_has_mud_cal(self) -> None:
        self.assertTrue(VEHICLE_REAL_AWD_HIGHWAY.diff_lock)
        self.assertEqual(VEHICLE_REAL_AWD_HIGHWAY.mud_immersion_rate, KD_MUD_IMMERSION_RATE)

    def test_make_vehicle_applies_mud_cal(self) -> None:
        veh = make_vehicle("offroad", base=sim_kd.VEHICLE_REAL_AWD)
        self.assertEqual(veh.mud_resist_mult, KD_MUD_RESIST_MULT)

    def test_uhd_mud_crawl_bounded(self) -> None:
        v30 = sample_at(
            run_sim(VEHICLE_REAL_AWD_HIGHWAY, ENGINE_REAL_FS, MUD, 60.0, low_gear=True),
            30.0,
        )
        self.assertGreater(v30, 0.0)
        self.assertLess(v30, 15.0)


if __name__ == "__main__":
    unittest.main()
