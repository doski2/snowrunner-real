"""Motores Scout 800 — XML compartido e_us_scout_old."""

from __future__ import annotations

from sim.core import EngineConfig, ENGINE_STOCK

AAT6V_ENGINE_XML = "us_scout_old_engine_0"
AAT6V_UI_LABEL = "AAT-6V 4.0"

# Catalogo stock (e_us_scout_old.xml) — sin nerfeo global hasta cerrar s8_f1
ENGINE_AAT6V_STOCK = EngineConfig(
    "AAT-6V 4.0 stock",
    35000.0,
    1.3,
    0.25,
    0.01,
)

# Objetivo mod (tras F1 CE) — placeholder igual que stock hasta calibrar
ENGINE_AAT6V_REAL = EngineConfig(
    "AAT-6V 4.0 realista S800",
    32000.0,
    1.1,
    0.22,
    0.012,
)


def engine_for_scout800(engine_id: str, engine_name_xml: str = "") -> EngineConfig:
    xml = (engine_name_xml or "").strip()
    if engine_id in ("aat6v", "s8_real") or xml == AAT6V_ENGINE_XML:
        return ENGINE_AAT6V_REAL
    return ENGINE_AAT6V_STOCK if engine_id == "s8_stock" else ENGINE_STOCK
