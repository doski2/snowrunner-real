"""Parches XML International Fleetstar F2070A."""

from __future__ import annotations

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/international_fleetstar_f2070a.xml": [
        ('FuelCapacity="240"', 'FuelCapacity="210"'),
        ('Responsiveness="0.1"', 'Responsiveness="0.085"'),
        (
            'ImpactType="Truck"\r\n\t\t\tMass="3500"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
            'ImpactType="Truck"\r\n\t\t\tMass="3650"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\tMass="1500"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\tMass="1620"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1300"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1380"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
        ),
    ],
    "[media]/classes/engines/e_us_truck_old.xml": [
        ('EngineResponsiveness="0.035"', 'EngineResponsiveness="0.024"'),
        (
            'FuelConsumption="5.5"\r\n\t\tName="us_truck_old_engine_0"\r\n\t\tTorque="135000"',
            'FuelConsumption="3.6"\r\n\t\tName="us_truck_old_engine_0"\r\n\t\tTorque="92000"',
        ),
        (
            'FuelConsumption="6.0"\r\n\t\tName="us_truck_old_engine_1"\r\n\t\tTorque="145000"',
            'FuelConsumption="3.9"\r\n\t\tName="us_truck_old_engine_1"\r\n\t\tTorque="99000"',
        ),
    ],
    "[media]/classes/suspensions/s_fleetstar_f2070a.xml": [
        (
            'Height="0.05"\r\n\t\t\tStrength="0.05"\r\n\t\t\tSuspensionMin="-0.3"\r\n\t\t\tWheelType="front"',
            'Height="0.05"\r\n\t\t\tStrength="0.058"\r\n\t\t\tSuspensionMin="-0.3"\r\n\t\t\tWheelType="front"',
        ),
        (
            'Height="0.1"\r\n\t\t\tStrength="0.08"\r\n\t\t\tSuspensionMin="-0.2"\r\n\t\t\tWheelType="rear"',
            'Height="0.1"\r\n\t\t\tStrength="0.092"\r\n\t\t\tSuspensionMin="-0.2"\r\n\t\t\tWheelType="rear"',
        ),
    ],
    "[media]/classes/wheels/wheels_medium_double.xml": [
        (
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="Highway" SubstanceFriction="0.4"/>',
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="Highway" SubstanceFriction="0.5"/>',
        ),
    ],
}
