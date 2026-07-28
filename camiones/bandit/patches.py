"""Parches XML KRS 58 Bandit (LAZ 6 T60, 51\" UHD I, 8x8 diff Always)."""

from __future__ import annotations

# Stock ~7014 kg. Mod **7600 kg** (cerca SR!NFO 7861).
# Motor e_ru_truck_old.xml compartido (Bandit, Actaeon, ZiKZ 566A, ...).
# Neumatico UHD I: wheels_medium_double_front.xml / highway_1.

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/_dlc/dlc_2_2/classes/trucks/krs_58_bandit.xml": [
        ('FuelCapacity="150"', 'FuelCapacity="135"'),
        ('Responsiveness="0.55"', 'Responsiveness="0.18"'),
        (
            'ImpactType="Truck"\r\n\t\t\tMass="4120"\r\n\t\t\tNetSync="pv"',
            'ImpactType="Truck"\r\n\t\t\tMass="4320"\r\n\t\t\tNetSync="pv"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\tMass="3100"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\tMass="3280"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
        ),
    ],
    "[media]/classes/engines/e_ru_truck_old.xml": [
        (
            'FuelConsumption="4.5"\r\n\t\tName="ru_truck_old_engine_0"\r\n\t\tTorque="130000"',
            'FuelConsumption="3.1"\r\n\t\tName="ru_truck_old_engine_0"\r\n\t\tTorque="88500"',
        ),
        (
            'FuelConsumption="5.5"\r\n\t\tName="ru_truck_old_engine_1"\r\n\t\tTorque="140000"',
            'FuelConsumption="3.7"\r\n\t\tName="ru_truck_old_engine_1"\r\n\t\tTorque="95300"',
        ),
        (
            'FuelConsumption="6.0"\r\n\t\tName="ru_truck_old_engine_2"\r\n\t\tTorque="160000"',
            'FuelConsumption="4.1"\r\n\t\tName="ru_truck_old_engine_2"\r\n\t\tTorque="108900"',
        ),
        (
            'FuelConsumption="7.5"\r\n\t\tName="ru_truck_old_engine_3"\r\n\t\tTorque="185000"',
            'FuelConsumption="5.1"\r\n\t\tName="ru_truck_old_engine_3"\r\n\t\tTorque="125900"',
        ),
    ],
    "[media]/classes/wheels/wheels_medium_double_front.xml": [
        (
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="Highway" SubstanceFriction="0.4" />',
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="Highway" SubstanceFriction="0.5" />',
        ),
    ],
}
