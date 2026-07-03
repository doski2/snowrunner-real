"""Tests de auditar_pak_catalogo (sin .pak)."""

from __future__ import annotations

import unittest

from auditar_pak_catalogo import (
    parse_engine_xml,
    parse_gearbox_xml,
    parse_suspension_xml,
    parse_truck_xml,
    parse_wheel_xml,
)

TRUCK_SAMPLE = """
<Truck>
  <TruckData FuelCapacity="80" Responsiveness="0.7" SteerSpeed="0.03" TruckType="SCOUT">
    <EngineSocket Default="e_test" Type="engines" />
    <GearboxSocket Default="g_test" Type="gearboxes" />
    <SuspensionSocket Default="susp_test" Type="susp" />
    <Wheels DefaultTire="highway_1" DefaultWheelType="wheels_scout1" />
  </TruckData>
  <Body Mass="900" CenterOfMassOffset="(0; -0.2; 0)" />
  <Body Mass="850" />
</Truck>
"""

ENGINE_SAMPLE = """
<_templates>
  <Engine>
    <USTruckOldEngine BrakesDelay="0.5" MaxDeltaAngVel="0.01" EngineResponsiveness="0.035" />
  </Engine>
</_templates>
<EngineVariants>
  <Engine _template="USTruckOldEngine" Name="us_truck_test" Torque="140000" FuelConsumption="7.5" />
</EngineVariants>
"""

WHEEL_SAMPLE = """
<WheelSet>
  <Wheel Name="highway_1">
    <WheelFriction _template="ScoutHighway" SubstanceFriction="0.4"/>
  </Wheel>
</WheelSet>
"""

GEARBOX_SAMPLE = """
<GearboxVariants>
  <Gearbox Name="g_test" AWDConsumptionModifier="1.1" FuelConsumption="2.0">
    <Gear AngVel="0.9" FuelModifier="1.8" />
    <HighGear AngVel="3.0" FuelModifier="1.5" />
    <GameData><GearboxParams IsLowerGearExists="true" IsHighGearExists="true" /></GameData>
  </Gearbox>
</GearboxVariants>
"""

SUSP_SAMPLE = """
<SuspensionSet>
  <Suspension WheelType="front" Strength="0.045" Damping="0.2" Height="0.065" />
</SuspensionSet>
"""


class TestAuditarPakCatalogo(unittest.TestCase):
    def test_parse_truck_xml(self) -> None:
        t = parse_truck_xml(TRUCK_SAMPLE, "[media]/classes/trucks/chevrolet_ck1500.xml")
        self.assertEqual(t["id"], "chevrolet_ck1500")
        self.assertEqual(t["fuel_capacity"], 80.0)
        self.assertEqual(t["default_engine"], "e_test")
        self.assertEqual(t["engine_socket_type"], "engines")
        self.assertEqual(t["default_gearbox"], "g_test")
        self.assertEqual(t["gearbox_socket_type"], "gearboxes")
        self.assertEqual(t["mass_all_bodies_kg"], 1750.0)
        self.assertEqual(t["default_tire"], "highway_1")

    def test_parse_engine_xml_inherits_template(self) -> None:
        variants = parse_engine_xml(ENGINE_SAMPLE, "[media]/classes/engines/e_test.xml")
        self.assertEqual(len(variants), 1)
        eng = variants[0]
        self.assertEqual(eng["name"], "us_truck_test")
        self.assertEqual(eng["brakes_delay"], 0.5)
        self.assertEqual(eng["max_delta_ang_vel"], 0.01)
        self.assertEqual(eng["torque"], 140000.0)

    def test_parse_wheel_xml(self) -> None:
        w = parse_wheel_xml(WHEEL_SAMPLE, "[media]/classes/wheels/wheels_scout1.xml")
        self.assertEqual(w["id"], "wheels_scout1")
        self.assertEqual(len(w["tires"]), 1)
        self.assertEqual(w["tires"][0]["substance_friction"], 0.4)

    def test_parse_gearbox_xml(self) -> None:
        gbs = parse_gearbox_xml(GEARBOX_SAMPLE, "[media]/classes/gearboxes/g_test.xml")
        self.assertEqual(gbs[0]["name"], "g_test")
        self.assertEqual(gbs[0]["is_lower_gear_exists"], "true")
        self.assertEqual(len(gbs[0]["gears"]), 2)

    def test_parse_suspension_xml(self) -> None:
        s = parse_suspension_xml(SUSP_SAMPLE, "[media]/classes/suspensions/s_test.xml")
        self.assertEqual(s["suspensions"][0]["strength"], 0.045)


if __name__ == "__main__":
    unittest.main()
