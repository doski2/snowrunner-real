"""Parches XML Tatra T813 (KZGT-8, JAT MSH I 50\", 8x8)."""

from __future__ import annotations

# Stock ~14020 kg (chasis 13000 + bastidor 1000). Mod ~14600 kg.
# Motor e_ru_special.xml compartido (Tatra / ZiKZ / otros HEAVY special).
# Neumatico MSH I: wheels_superheavy_mudtires.xml (50\" superheavy).

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/_dlc/dlc_4/classes/trucks/tatra_t813.xml": [
        ('FuelCapacity="380"', 'FuelCapacity="340"'),
        ('Responsiveness="0.2"', 'Responsiveness="0.14"'),
        (
            'CenterOfMassOffset="(-2.2; -0.5; 0)"',
            'CenterOfMassOffset="(-2.2; -0.55; 0)"',
        ),
        ('Mass="13000"', 'Mass="13500"'),
        (
            'Mass="1000"\r\n\t\t\t\tModelFrame="BoneAddonAttachment_cdt"',
            'Mass="1050"\r\n\t\t\t\tModelFrame="BoneAddonAttachment_cdt"',
        ),
    ],
    "[media]/classes/engines/e_ru_special.xml": [
        ('EngineResponsiveness="0.045"', 'EngineResponsiveness="0.032"'),
        (
            'FuelConsumption="9.0"\r\n\t\tName="ru_special_engine_0"\r\n\t\tTorque="205000"',
            'FuelConsumption="6.2"\r\n\t\tName="ru_special_engine_0"\r\n\t\tTorque="140000"',
        ),
        (
            'FuelConsumption="10.0"\r\n\t\tName="ru_special_engine_1"\r\n\t\tTorque="230000"',
            'FuelConsumption="6.8"\r\n\t\tName="ru_special_engine_1"\r\n\t\tTorque="157000"',
        ),
        (
            'FuelConsumption="11.5"\r\n\t\tName="ru_special_engine_2"\r\n\t\tTorque="260000"',
            'FuelConsumption="7.8"\r\n\t\tName="ru_special_engine_2"\r\n\t\tTorque="177000"',
        ),
    ],
    "[media]/_dlc/dlc_11/classes/wheels/wheels_superheavy_mudtires.xml": [
        (
            'Name="JAT MSH I">\r\n\t\t\t<WheelFriction _template="Mudtires" BodyFriction="1.6" BodyFrictionAsphalt="0.6" SubstanceFriction="3"/>',
            'Name="JAT MSH I">\r\n\t\t\t<WheelFriction _template="Mudtires" BodyFriction="1.6" BodyFrictionAsphalt="0.6" SubstanceFriction="2.2"/>',
        ),
    ],
}
