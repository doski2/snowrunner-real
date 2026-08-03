"""Parches XML International Fleetstar F2070A — solo masa (motor/neumáticos stock)."""

from __future__ import annotations

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/international_fleetstar_f2070a.xml": [
        (
            'ImpactType="Truck"\r\n\t\t\tMass="3650"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
            'ImpactType="Truck"\r\n\t\t\tMass="4160"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\tMass="1620"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\tMass="1730"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1380"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1510"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
        ),
    ],
}
