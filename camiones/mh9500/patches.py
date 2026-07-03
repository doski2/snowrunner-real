"""Parches XML GMC MH9500."""

from __future__ import annotations

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/gmc_9500.xml": [
        ('FuelCapacity="240"', 'FuelCapacity="220"'),
        ('Responsiveness="0.25"', 'Responsiveness="0.18"'),
        ('CenterOfMassOffset="(-1.5; 0; 0)"', 'CenterOfMassOffset="(-1.5; -0.2; 0)"'),
        ('Mass="4000"', 'Mass="3800"'),
        (
            'Mass="1500"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
            'Mass="1850"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
        ),
        (
            'Mass="1500"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
            'Mass="1850"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
        ),
    ],
    "[media]/classes/engines/e_us_truck_old_gmc9500.xml": [
        ('FuelConsumption="7.5"', 'FuelConsumption="4.2"'),
        ('Torque="140000"', 'Torque="95000"'),
        ('EngineResponsiveness="0.035"', 'EngineResponsiveness="0.022"'),
    ],
    "[media]/classes/suspensions/s_gmc9500.xml": [
        (
            '<Suspension Damping="0.3" Height="0.2" Strength="0.04" WheelType="front"',
            '<Suspension Damping="0.3" Height="0.2" Strength="0.055" WheelType="front"',
        ),
    ],
    "[media]/classes/wheels/wheels_medium_double.xml": [
        (
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="Highway" SubstanceFriction="0.4"/>',
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="Highway" SubstanceFriction="0.5"/>',
        ),
    ],
}
