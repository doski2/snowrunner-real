"""Parches XML Chevrolet CK1500 — solo masa (motor/neumáticos stock)."""

from __future__ import annotations

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/chevrolet_ck1500.xml": [
        ('Mass="1150"', 'Mass="900"'),
        ('Mass="1050"', 'Mass="850"'),
    ],
}
