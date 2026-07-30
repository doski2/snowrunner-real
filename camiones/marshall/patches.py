"""Parches XML KHAN 39 Marshall (Kr 104, 45\" TM II, suspensión reptadora)."""

from __future__ import annotations

# Substance TM II: 2.4 -> 1.7 (plantilla ScoutMudtires = 1.6)
# Responsiveness: 0.6 -> 0.04 (arcade -> scout realista)
# Masa mod **2030 kg** (SR!NFO ~2029; por debajo UAZ TE 2380).

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/khan_39_marshall.xml": [
        ('Responsiveness="0.6"', 'Responsiveness="0.04"'),
        (
            'ImpactType="Truck"\r\n\t\t\tMass="900"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
            'ImpactType="Truck"\r\n\t\t\tMass="1000"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
        ),
        (
            '<Body Mass="880" CenterOfMassOffset="(0.0; -0.35; 0)" ModelFrame="BoneWeighter_cdt">',
            '<Body Mass="1030" CenterOfMassOffset="(0.0; -0.35; 0)" ModelFrame="BoneWeighter_cdt">',
        ),
    ],
    "[media]/classes/engines/e_ru_scout_old.xml": [
        (
            'FuelConsumption="0.6"\r\n\t\tName="ru_scout_old_engine_0"\r\n\t\tTorque="30000"',
            'FuelConsumption="0.75"\r\n\t\tName="ru_scout_old_engine_0"\r\n\t\tTorque="28000"',
        ),
        ('EngineResponsiveness="0.04"', 'EngineResponsiveness="0.035"'),
        (
            'FuelConsumption="1.1"\r\n\t\tName="ru_scout_old_engine_1"\r\n\t\tTorque="40000"',
            'FuelConsumption="1.35"\r\n\t\tName="ru_scout_old_engine_1"\r\n\t\tTorque="37333"',
        ),
        ('EngineResponsiveness="0.09"', 'EngineResponsiveness="0.08"'),
    ],
    "[media]/classes/wheels/wheels_scout_yar_871.xml": [
        (
            '<WheelFriction _template="Mudtires" SubstanceFriction="2.4" />',
            '<WheelFriction _template="Mudtires" SubstanceFriction="1.7" />',
        ),
        (
            '<WheelFriction _template="Mudtires" BodyFriction="2.4" />',
            '<WheelFriction _template="Mudtires" BodyFriction="2.0" />',
        ),
    ],
}
