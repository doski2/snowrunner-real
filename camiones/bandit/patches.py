"""Parches XML KRS 58 Bandit — solo masa (motor/neumáticos stock)."""

from __future__ import annotations

# Stock ~7014 kg. Mod **7600 kg** (cerca SR!NFO 7861).

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/_dlc/dlc_2_2/classes/trucks/krs_58_bandit.xml": [
        (
            'ImpactType="Truck"\r\n\t\t\tMass="4120"\r\n\t\t\tNetSync="pv"',
            'ImpactType="Truck"\r\n\t\t\tMass="4320"\r\n\t\t\tNetSync="pv"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\tMass="3100"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\tMass="3280"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
        ),
    ],
}
