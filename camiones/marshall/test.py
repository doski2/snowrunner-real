"""
Tests parches y simulador KHAN 39 Marshall.

Ejecutar:
  python -m unittest camiones.marshall.test -v
  python -m camiones.marshall.simulador
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from camiones.marshall import simulador as sim_km
from camiones.marshall.patches import PATCHES as MARSHALL_PATCHES
from camiones.registry import EMPTY_MASS_KG, VEHICLES, merge_patches, vehicle_id_from_ce
from sim.core import SurfaceConfig

ENGINE_REAL_KM = sim_km.ENGINE_REAL_KM
ENGINE_STOCK_KM = sim_km.ENGINE_STOCK_KM
KM_MUD_IMMERSION_RATE = sim_km.KM_MUD_IMMERSION_RATE
KM_MUD_RESIST_MULT = sim_km.KM_MUD_RESIST_MULT
LOAD_TRAILER_CARGO = sim_km.LOAD_TRAILER_CARGO
LOAD_TRAILER_MASS = sim_km.LOAD_TRAILER_MASS
TIRES = sim_km.TIRES
VEHICLE_REAL = sim_km.VEHICLE_REAL
VEHICLE_STOCK = sim_km.VEHICLE_STOCK
make_vehicle = sim_km.make_vehicle
run_sim = sim_km.run_sim
sample_at = sim_km.sample_at

MUD = SurfaceConfig("Barro", "mud", viscosity=4.0)


class TestMarshallRegistry(unittest.TestCase):
    def test_vehicle_registered(self) -> None:
        self.assertIn("marshall", VEHICLES)
        self.assertEqual(VEHICLES["marshall"].xml_file, "khan_39_marshall.xml")
        self.assertEqual(VEHICLES["marshall"].ce_id, "s_khan_39_marshall")

    def test_empty_mass_for_ce(self) -> None:
        self.assertEqual(EMPTY_MASS_KG["marshall"], 1780.0)
        self.assertEqual(VEHICLE_REAL.mass_kg, EMPTY_MASS_KG["marshall"])

    def test_ce_id_alias(self) -> None:
        self.assertEqual(vehicle_id_from_ce("s_khan_39_marshall"), "marshall")
        self.assertEqual(vehicle_id_from_ce("khan_39_marshall"), "marshall")

    def test_merge_includes_marshall_files(self) -> None:
        merged = merge_patches(["marshall"])
        self.assertIn("[media]/classes/trucks/khan_39_marshall.xml", merged)
        self.assertIn("[media]/classes/wheels/wheels_scout_yar_871.xml", merged)


class TestMarshallPatches(unittest.TestCase):
    def test_responsiveness_reduced(self) -> None:
        pairs = MARSHALL_PATCHES["[media]/classes/trucks/khan_39_marshall.xml"]
        self.assertTrue(any('Responsiveness="0.04"' in new for _old, new in pairs))

    def test_tm2_substance_nerfed(self) -> None:
        pairs = MARSHALL_PATCHES["[media]/classes/wheels/wheels_scout_yar_871.xml"]
        self.assertTrue(any('SubstanceFriction="1.7"' in new for _old, new in pairs))


class TestMarshallSim(unittest.TestCase):
    def test_real_heavier_than_stock(self) -> None:
        self.assertGreater(VEHICLE_REAL.mass_kg, VEHICLE_STOCK.mass_kg)

    def test_mudtires_substance_mod(self) -> None:
        self.assertEqual(TIRES["mudtires"]["substance"], 1.7)

    def test_awd_diff_stock(self) -> None:
        self.assertTrue(VEHICLE_REAL.diff_lock)
        self.assertEqual(VEHICLE_REAL.drive_layout, "4wd")

    def test_real_tm2_has_mud_cal(self) -> None:
        self.assertEqual(VEHICLE_REAL.mud_immersion_rate, KM_MUD_IMMERSION_RATE)
        self.assertEqual(VEHICLE_REAL.mud_resist_mult, KM_MUD_RESIST_MULT)

    def test_make_vehicle_applies_mud_cal_on_4wd_base(self) -> None:
        base = replace(VEHICLE_REAL, mud_immersion_rate=1.0, mud_resist_mult=1.0)
        veh = make_vehicle("offroad", base=base)
        self.assertEqual(veh.tire_name, "offroad")
        self.assertEqual(veh.mud_immersion_rate, KM_MUD_IMMERSION_RATE)
        self.assertEqual(veh.mud_resist_mult, KM_MUD_RESIST_MULT)

    def test_engine_for_marshall_xml_name(self) -> None:
        eng135 = sim_km.engine_for_marshall("km_kr135", "ru_scout_old_engine_1")
        self.assertEqual(eng135.torque, sim_km.ENGINE_REAL_KM_135.torque)
        eng104 = sim_km.engine_for_marshall("km_kr104", "ru_scout_old_engine_0")
        self.assertEqual(eng104.torque, ENGINE_REAL_KM.torque)
        self.assertGreater(
            sim_km.engine_for_marshall("km_kr135").torque,
            sim_km.engine_for_marshall("km_kr104").torque,
        )

    def test_real_slower_than_stock_mud(self) -> None:
        a = run_sim(VEHICLE_STOCK, ENGINE_STOCK_KM, MUD, 60.0, low_gear=True)
        b = run_sim(VEHICLE_REAL, ENGINE_REAL_KM, MUD, 60.0, low_gear=True)
        self.assertGreater(max(a.speeds_kmh), max(b.speeds_kmh))

    def test_deep_mud_not_infinite_speed(self) -> None:
        deep = SurfaceConfig("Barro profundo", "deep_mud", viscosity=4.0, water_depth=0.4)
        v30 = sample_at(
            run_sim(VEHICLE_REAL, ENGINE_REAL_KM, deep, 90.0, low_gear=True),
            30.0,
        )
        self.assertLess(v30, 45.0)

    def test_loaded_slower(self) -> None:
        loaded = replace(
            VEHICLE_REAL,
            trailer_mass_kg=LOAD_TRAILER_MASS,
            trailer_cargo_mass_kg=LOAD_TRAILER_CARGO,
        )
        self.assertGreater(
            max(run_sim(VEHICLE_REAL, ENGINE_REAL_KM, MUD, 90.0, low_gear=True).speeds_kmh),
            max(run_sim(loaded, ENGINE_REAL_KM, MUD, 90.0, low_gear=True).speeds_kmh),
        )


if __name__ == "__main__":
    unittest.main()
