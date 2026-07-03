"""
Tests del registro central de vehiculos.

Ejecutar:
  python -m unittest camiones.test_registry -v
"""

from __future__ import annotations

import importlib
import unittest

from camiones.registry import (
    EMPTY_MASS_KG,
    VEHICLES,
    default_vehicle_ids,
    empty_mass_kg,
    merge_patches,
    trailer_tare_kg,
    vehicle_id_from_ce,
)
from sim.core import VEHICLE_I6


class TestRegistryVehicles(unittest.TestCase):
    def test_default_ids_match_registry(self) -> None:
        self.assertEqual(default_vehicle_ids(), list(VEHICLES))

    def test_each_vehicle_has_patches_and_sim(self) -> None:
        for vid, mod in VEHICLES.items():
            self.assertEqual(mod.id, vid)
            self.assertTrue(mod.patches)
            self.assertTrue(mod.xml_file.endswith(".xml"))
            importlib.import_module(mod.sim_module)

    def test_merge_all_includes_every_xml(self) -> None:
        merged = merge_patches(default_vehicle_ids())
        for mod in VEHICLES.values():
            arc = f"[media]/classes/trucks/{mod.xml_file}"
            self.assertIn(arc, merged)

    def test_merge_unknown_raises(self) -> None:
        with self.assertRaises(KeyError):
            merge_patches(["no_existe"])


class TestRegistryCeIds(unittest.TestCase):
    def test_ce_id_and_game_id_resolve(self) -> None:
        for vid, mod in VEHICLES.items():
            self.assertEqual(vehicle_id_from_ce(mod.ce_id), vid)
            self.assertEqual(vehicle_id_from_ce(mod.game_id), vid)

    def test_known_aliases(self) -> None:
        cases = {
            "s_gmc9500": "mh9500",
            "gmc_9500": "mh9500",
            "s_fleetstar_f2070a": "fleetstar",
            "international_fleetstar_f2070a": "fleetstar",
            "khan_39_marshall": "marshall",
            "s_chevrolet_kodiakc70": "kodiak",
            "chevrolet_ck1500": "ck1500",
            "s_international_scout_800": "scout800",
        }
        for game_id, expected in cases.items():
            with self.subTest(game_id=game_id):
                self.assertEqual(vehicle_id_from_ce(game_id), expected)

    def test_empty_and_unknown(self) -> None:
        self.assertIsNone(vehicle_id_from_ce(""))
        self.assertIsNone(vehicle_id_from_ce("   "))
        self.assertIsNone(vehicle_id_from_ce("truck_inventado"))


class TestRegistryMass(unittest.TestCase):
    def test_empty_mass_matches_simulators(self) -> None:
        from camiones.fleetstar.simulador import VEHICLE_REAL as FS_REAL
        from camiones.kodiak.simulador import VEHICLE_REAL as KD_REAL
        from camiones.marshall.simulador import VEHICLE_REAL as KM_REAL
        from camiones.scout800.simulador import VEHICLE_REAL as S8_REAL
        from camiones.mh9500.simulador import VEHICLE_REAL as MH_REAL

        expected = {
            "ck1500": VEHICLE_I6.mass_kg,
            "mh9500": MH_REAL.mass_kg,
            "fleetstar": FS_REAL.mass_kg,
            "marshall": KM_REAL.mass_kg,
            "kodiak": KD_REAL.mass_kg,
            "scout800": S8_REAL.mass_kg,
        }
        self.assertEqual(EMPTY_MASS_KG, expected)

    def test_empty_mass_kg_helper(self) -> None:
        self.assertEqual(empty_mass_kg("marshall"), 1780.0)
        self.assertIsNone(empty_mass_kg(None))
        self.assertIsNone(empty_mass_kg("unknown"))


class TestRegistryTrailers(unittest.TestCase):
    def test_trailer_tare_catalog(self) -> None:
        self.assertEqual(trailer_tare_kg("semi_trailer"), 2500.0)
        self.assertEqual(trailer_tare_kg("scout_small"), 800.0)
        self.assertEqual(trailer_tare_kg("heavy_fuel_tank"), 1200.0)
        self.assertEqual(trailer_tare_kg("fuel_tank_small"), 1200.0)
        self.assertEqual(trailer_tare_kg("generic"), 1500.0)


if __name__ == "__main__":
    unittest.main()
