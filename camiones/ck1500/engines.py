"""Motores CK1500 — XML en juego vs nombre UI."""

from __future__ import annotations

from sim.core import ENGINE_I6, ENGINE_STOCK, EngineConfig

# Mejora de taller "AAT-8V 5,2 Custom" (Black River)
AAT8V_ENGINE_XML = "us_scout_old_engine_ck1500"
AAT8V_UI_LABEL = "AAT-8V 5.2 Custom"


def engine_for_ck1500(engine_id: str, engine_name_xml: str = "") -> EngineConfig:
    """Sim/CE: AAT-8V comparte XML con el I6 mod del proyecto (initial.pak)."""
    xml = (engine_name_xml or "").strip()
    if engine_id in ("aat8v", "i6") or xml == AAT8V_ENGINE_XML:
        return ENGINE_I6
    return ENGINE_STOCK
