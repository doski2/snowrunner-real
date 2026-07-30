"""Parches XML International Scout 800 (AAT-6V, diff siempre)."""

from __future__ import annotations

# Masa mod **2100 kg** (Scout real ~1800–2200).
# Motor AAT-6V: e_us_scout_old.xml (compartido con otros scouts US; no CK1500 dedicado).

PATCHES: dict[str, list[tuple[str, str]]] = {
    "[media]/classes/trucks/international_scout_800.xml": [
        ('Responsiveness="0.6"', 'Responsiveness="0.04"'),
        ('Mass="1900"', 'Mass="1500"'),
        ('Mass="900"', 'Mass="600"'),
    ],
    "[media]/classes/engines/e_us_scout_old.xml": [
        (
            'FuelConsumption="1.3"\r\n\t\tName="us_scout_old_engine_0"\r\n\t\tTorque="35000"',
            'FuelConsumption="1.1"\r\n\t\tName="us_scout_old_engine_0"\r\n\t\tTorque="32000"',
        ),
        ('EngineResponsiveness="0.25"', 'EngineResponsiveness="0.22"'),
        ('MaxDeltaAngVel="0.01"', 'MaxDeltaAngVel="0.012"'),
    ],
}
