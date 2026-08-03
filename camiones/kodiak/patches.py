"""Parches XML Chevrolet Kodiak C70 — solo masa (motor/neumáticos stock)."""

from __future__ import annotations

# Mod **8150 kg** (SR!NFO ~8201).

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/chevrolet_kodiakc70.xml": [
        (
            'ImpactType="Truck"\r\n\t\t\tMass="4500"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
            'ImpactType="Truck"\r\n\t\t\tMass="4750"\r\n\t\t\tModelFrame="BoneChassis_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\tMass="1500"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\tMass="1693"\r\n\t\t\t\tModelFrame="BoneCabin_cdt"',
        ),
        (
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1500"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
            'ImpactType="Truck"\r\n\t\t\t\t\tMass="1693"\r\n\t\t\t\t\tModelFrame="BoneCabinRagdoll_cdt"',
        ),
    ],
}
