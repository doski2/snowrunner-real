"""Parches XML GMC MH9500 — solo masa (motor/neumáticos stock)."""

from __future__ import annotations

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/gmc_9500.xml": [
        (
            'ImpactType="Truck"\r\n\t\t\tMass="3800"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
            'ImpactType="Truck"\r\n\t\t\tMass="4000"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\tMass="1850"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\tMass="2100"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1850"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="2100"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
        ),
    ],
}
