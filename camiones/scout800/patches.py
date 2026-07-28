"""Parches XML International Scout 800 (AAT-6V, diff siempre)."""

from __future__ import annotations

# Masa mod **2100 kg** (Scout real ~1800–2200).

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/international_scout_800.xml": [
        ('Responsiveness="0.6"', 'Responsiveness="0.04"'),
        ('Mass="1900"', 'Mass="1500"'),
        ('Mass="900"', 'Mass="600"'),
    ],
}
