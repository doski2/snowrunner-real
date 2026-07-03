"""Parches XML Chevrolet Kodiak C70 (Si-6V, 39\" UHD I, 4x4)."""

from __future__ import annotations

# Stock catalogo: ~7513 kg, fuel 200 L, Responsiveness 0.15
# Mod: +~5 % masa, menos arcade; motor/ruedas comparten familia Fleetstar (e_us_truck_old)

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/chevrolet_kodiakc70.xml": [
        ('FuelCapacity="200"', 'FuelCapacity="175"'),
        ('Responsiveness="0.15"', 'Responsiveness="0.11"'),
        (
            'ImpactType="Truck"\r\n\t\t\tMass="4500"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
            'ImpactType="Truck"\r\n\t\t\tMass="4690"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\tMass="1500"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\tMass="1605"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1500"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1605"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
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
    "[media]/classes/suspensions/s_chevrolet_kodiakC70.xml": [
        (
            'Height="0.15" Strength="0.05" WheelType="front" BrokenSuspensionMax="0.1" SuspensionMin="-0.25"',
            'Height="0.15" Strength="0.058" WheelType="front" BrokenSuspensionMax="0.1" SuspensionMin="-0.25"',
        ),
        (
            'Height="0.15" Strength="0.08" WheelType="rear" BrokenSuspensionMax="0.1" SuspensionMin="-0.25"',
            'Height="0.15" Strength="0.092" WheelType="rear" BrokenSuspensionMax="0.1" SuspensionMin="-0.25"',
        ),
    ],
    "[media]/classes/wheels/wheels_medium_double.xml": [
        (
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="Highway" SubstanceFriction="0.4"/>',
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="Highway" SubstanceFriction="0.5"/>',
        ),
    ],
}
