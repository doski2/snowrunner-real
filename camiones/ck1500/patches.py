"""Parches XML Chevrolet CK1500."""

from __future__ import annotations

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/chevrolet_ck1500.xml": [
        ('FuelCapacity="80"', 'FuelCapacity="76"'),
        ('CenterOfMassOffset="(-0.1; -0.15; 0)"', 'CenterOfMassOffset="(-0.1; -0.20; 0)"'),
        ('Mass="1150"', 'Mass="900"'),
        ('Mass="1050"', 'Mass="850"'),
    ],
    "[media]/classes/engines/e_us_scout_old_ck1500.xml": [
        ('FuelConsumption="3.3"', 'FuelConsumption="1.5"'),
        ('Torque="62000"', 'Torque="40000"'),
        ('MaxDeltaAngVel="10"', 'MaxDeltaAngVel="0.015"'),
        ('EngineResponsiveness="0.4"', 'EngineResponsiveness="0.28"'),
    ],
    "[media]/classes/suspensions/s_chevrolet_ck1500.xml": [
        (
            '<Suspension Damping=".2" Height="0.065" Strength="0.035" WheelType="front"',
            '<Suspension Damping=".2" Height="0.065" Strength="0.045" WheelType="front"',
        ),
    ],
    "[media]/classes/wheels/wheels_scout1.xml": [
        (
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="ScoutHighway" SubstanceFriction="0.4"/>',
            'Name="highway_1">\r\n\t\t\t<WheelFriction _template="ScoutHighway" SubstanceFriction="0.5"/>',
        ),
    ],
}
