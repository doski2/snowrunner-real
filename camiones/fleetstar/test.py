"""
Tests parches y simulador Fleetstar F2070A.

Ejecutar:
  python -m unittest camiones.fleetstar.test -v
  python -m camiones.fleetstar.simulador
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from camiones.fleetstar import simulador as sim_fs
from camiones.fleetstar.patches import PATCHES as FLEETSTAR_PATCHES
from camiones.registry import EMPTY_MASS_KG, VEHICLES, merge_patches, vehicle_id_from_ce
from sim.core import SurfaceConfig

ENGINE_REAL_FS = sim_fs.ENGINE_REAL_FS
ENGINE_REAL_FS_2100 = sim_fs.ENGINE_REAL_FS_2100
ENGINE_STOCK_FS = sim_fs.ENGINE_STOCK_FS
FS_MUD_IMMERSION_RATE = sim_fs.FS_MUD_IMMERSION_RATE
FS_MUD_RESIST_MULT = sim_fs.FS_MUD_RESIST_MULT
LOAD_FRAME_FULL = sim_fs.LOAD_FRAME_FULL
TIRES = sim_fs.TIRES
VEHICLE_REAL = sim_fs.VEHICLE_REAL
VEHICLE_REAL_AWD = sim_fs.VEHICLE_REAL_AWD
VEHICLE_REAL_AWD_HIGHWAY = sim_fs.VEHICLE_REAL_AWD_HIGHWAY
VEHICLE_REAL_OFFROAD = sim_fs.VEHICLE_REAL_OFFROAD
VEHICLE_STOCK = sim_fs.VEHICLE_STOCK
make_vehicle = sim_fs.make_vehicle
run_sim = sim_fs.run_sim
sample_at = sim_fs.sample_at

MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)


class TestFleetstarPatches(unittest.TestCase):
    def test_vehicle_registered(self) -> None:
        self.assertIn("fleetstar", VEHICLES)
        self.assertEqual(VEHICLES["fleetstar"].xml_file, "international_fleetstar_f2070a.xml")
        self.assertEqual(VEHICLES["fleetstar"].ce_id, "s_fleetstar_f2070a")

    def test_ce_id_aliases(self) -> None:
        self.assertEqual(vehicle_id_from_ce("s_fleetstar_f2070a"), "fleetstar")
        self.assertEqual(vehicle_id_from_ce("international_fleetstar_f2070a"), "fleetstar")

    def test_empty_mass_for_ce(self) -> None:
        self.assertEqual(EMPTY_MASS_KG["fleetstar"], 6650.0)
        self.assertEqual(VEHICLE_REAL.mass_kg, EMPTY_MASS_KG["fleetstar"])

    def test_merge_includes_fleetstar_files(self) -> None:
        merged = merge_patches(["fleetstar"])
        self.assertIn("[media]/classes/trucks/international_fleetstar_f2070a.xml", merged)
        self.assertIn("[media]/classes/engines/e_us_truck_old.xml", merged)
        self.assertIn("[media]/classes/wheels/wheels_medium_double.xml", merged)

    def test_engine_torque_reduced(self) -> None:
        pairs = FLEETSTAR_PATCHES["[media]/classes/engines/e_us_truck_old.xml"]
        block = next(p for p in pairs if "us_truck_old_engine_0" in p[0])
        self.assertIn('Torque="92000"', block[1])

    def test_engine_2100_torque_reduced(self) -> None:
        pairs = FLEETSTAR_PATCHES["[media]/classes/engines/e_us_truck_old.xml"]
        block = next(p for p in pairs if "us_truck_old_engine_1" in p[0])
        self.assertIn('Torque="99000"', block[1])
        self.assertIn('FuelConsumption="3.9"', block[1])


class TestFleetstarSim(unittest.TestCase):
    def test_six_wheels(self) -> None:
        self.assertEqual(VEHICLE_REAL.num_wheels, 6)

    def test_real_heavier_than_stock(self) -> None:
        self.assertGreater(VEHICLE_REAL.mass_kg, VEHICLE_STOCK.mass_kg)

    def test_highway_substance_mod(self) -> None:
        self.assertEqual(TIRES["highway"]["substance"], 0.5)

    def test_awd_highway_setup_has_mud_cal(self) -> None:
        self.assertTrue(VEHICLE_REAL_AWD_HIGHWAY.diff_lock)
        self.assertEqual(VEHICLE_REAL_AWD_HIGHWAY.drive_layout, "awd")
        self.assertEqual(VEHICLE_REAL_AWD_HIGHWAY.mud_immersion_rate, FS_MUD_IMMERSION_RATE)
        self.assertEqual(VEHICLE_REAL_AWD_HIGHWAY.mud_resist_mult, FS_MUD_RESIST_MULT)

    def test_make_vehicle_applies_mud_cal_on_awd_base(self) -> None:
        veh = make_vehicle("offroad", base=VEHICLE_REAL_AWD)
        self.assertEqual(veh.tire_name, "offroad")
        self.assertEqual(veh.mud_immersion_rate, FS_MUD_IMMERSION_RATE)
        self.assertEqual(veh.mud_resist_mult, FS_MUD_RESIST_MULT)

    def test_stock_faster_than_real_asphalt(self) -> None:
        asphalt = SurfaceConfig("Asfalto", "asphalt")
        a = run_sim(VEHICLE_STOCK, ENGINE_STOCK_FS, asphalt, 50.0)
        b = run_sim(VEHICLE_REAL, ENGINE_REAL_FS, asphalt, 50.0)
        self.assertGreater(a.speeds_kmh[-1], b.speeds_kmh[-1])

    def test_offroad_faster_than_uhd_mud(self) -> None:
        uhd = run_sim(VEHICLE_REAL_AWD_HIGHWAY, ENGINE_REAL_FS, MUD, 120.0, low_gear=True)
        oroad = run_sim(VEHICLE_REAL_OFFROAD, ENGINE_REAL_FS, MUD, 120.0, low_gear=True)
        self.assertGreater(max(oroad.speeds_kmh), max(uhd.speeds_kmh))

    def test_uhd_mud_crawl_slow(self) -> None:
        v30 = sample_at(
            run_sim(VEHICLE_REAL_AWD_HIGHWAY, ENGINE_REAL_FS, MUD, 60.0, low_gear=True),
            30.0,
        )
        self.assertLess(v30, 8.0)
        self.assertGreater(v30, 0.0)

    def test_loaded_slower(self) -> None:
        empty = VEHICLE_REAL_AWD_HIGHWAY
        loaded = replace(empty, cargo_mass_kg=6000)
        self.assertGreater(
            max(run_sim(empty, ENGINE_REAL_FS, MUD, 120.0, low_gear=True).speeds_kmh),
            max(run_sim(loaded, ENGINE_REAL_FS, MUD, 120.0, low_gear=True).speeds_kmh),
        )

    def test_frame_full_load_stalls_uhd(self) -> None:
        loaded = replace(VEHICLE_REAL_AWD_HIGHWAY, cargo_mass_kg=LOAD_FRAME_FULL)
        v30 = sample_at(
            run_sim(loaded, ENGINE_REAL_FS, MUD, 60.0, low_gear=True),
            30.0,
        )
        self.assertLess(v30, 1.0)

    def test_2100_stronger_than_1900_asphalt(self) -> None:
        asphalt = SurfaceConfig("Asfalto", "asphalt")
        a = run_sim(VEHICLE_REAL_AWD_HIGHWAY, ENGINE_REAL_FS, asphalt, 60.0)
        b = run_sim(VEHICLE_REAL_AWD_HIGHWAY, ENGINE_REAL_FS_2100, asphalt, 60.0)
        self.assertGreater(b.speeds_kmh[-1], a.speeds_kmh[-1])

    def test_engine_for_fleetstar_xml_name(self) -> None:
        eng = sim_fs.engine_for_fleetstar("fs_real", "us_truck_old_engine_1")
        self.assertEqual(eng.torque, ENGINE_REAL_FS_2100.torque)
        self.assertEqual(
            sim_fs.engine_for_fleetstar("fs_real", "us_truck_old_engine_0").torque,
            ENGINE_REAL_FS.torque,
        )


if __name__ == "__main__":
    unittest.main()
