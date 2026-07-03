"""Parches XML KHAN 39 Marshall (Kr 104, 45\" TM II, suspensión reptadora)."""

from __future__ import annotations

# Substance TM II: 2.4 -> 1.7 (plantilla ScoutMudtires = 1.6)
# Responsiveness: 0.6 -> 0.04 (arcade -> scout realista)
# Masa: 1500 -> 1780 kg (UAZ-3151 / TREKOL ~1700-2100 kg)

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/khan_39_marshall.xml": [
        ('Responsiveness="0.6"', 'Responsiveness="0.04"'),
        (
            'ImpactType="Truck"\r\n\t\t\tMass="800"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
            'ImpactType="Truck"\r\n\t\t\tMass="900"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
        ),
        (
            '<Body Mass="700" CenterOfMassOffset="(0.0; -0.35; 0)" ModelFrame="BoneWeighter_cdt">',
            '<Body Mass="880" CenterOfMassOffset="(0.0; -0.35; 0)" ModelFrame="BoneWeighter_cdt">',
        ),
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
