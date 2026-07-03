"""Tests Scout 800 registry + sim."""

from __future__ import annotations

import unittest

from camiones.registry import VEHICLES, merge_patches, vehicle_id_from_ce
from camiones.scout800.engines import AAT6V_ENGINE_XML, engine_for_scout800
from camiones.scout800.simulador import ENGINE_AAT6V_REAL, VEHICLE_REAL


class TestScout800(unittest.TestCase):
    def test_registry_entry(self) -> None:
        mod = VEHICLES["scout800"]
        self.assertEqual(mod.ce_id, "s_international_scout_800")
        self.assertEqual(vehicle_id_from_ce("s_international_scout_800"), "scout800")

    def test_patches_include_truck_xml(self) -> None:
        merged = merge_patches(["scout800"])
        self.assertIn("[media]/classes/trucks/international_scout_800.xml", merged)

    def test_aat6v_engine(self) -> None:
        self.assertIs(engine_for_scout800("aat6v"), ENGINE_AAT6V_REAL)
        self.assertIs(engine_for_scout800("aat6v", AAT6V_ENGINE_XML), ENGINE_AAT6V_REAL)

    def test_vehicle_diff_always(self) -> None:
        self.assertTrue(VEHICLE_REAL.diff_lock)
        self.assertEqual(VEHICLE_REAL.mass_kg, 2350.0)
