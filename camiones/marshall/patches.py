"""Parches XML KHAN 39 Marshall — solo masa (motor/neumáticos stock)."""

from __future__ import annotations

# Masa mod **2030 kg** (SR!NFO ~2029; por debajo UAZ TE 2380).

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/khan_39_marshall.xml": [
        (
            'ImpactType="Truck"\r\n\t\t\tMass="900"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
            'ImpactType="Truck"\r\n\t\t\tMass="1000"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
        ),
        (
            '<Body Mass="880" CenterOfMassOffset="(0.0; -0.35; 0)" ModelFrame="BoneWeighter_cdt">',
            '<Body Mass="1030" CenterOfMassOffset="(0.0; -0.35; 0)" ModelFrame="BoneWeighter_cdt">',
        ),
    ],
}
