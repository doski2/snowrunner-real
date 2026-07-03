"""Parches XML International Scout 800 (AAT-6V, diff siempre).

Pendiente calibracion CE (s8_f1_*). No toca e_us_scout_old.xml (motor compartido).
"""

from __future__ import annotations

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/international_scout_800.xml": [
        ('Responsiveness="0.6"', 'Responsiveness="0.04"'),
        ('Mass="1900"', 'Mass="1600"'),
        ('Mass="900"', 'Mass="750"'),
    ],
}
