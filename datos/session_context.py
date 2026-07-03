"""Metadatos obligatorios de sesion CE (PLAN-BASE-DATOS §2.4)."""

from __future__ import annotations

import json
import os
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(ROOT, "datos", "indices", "manifest.json")


def _manifest_build() -> str:
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f).get("game_version", "")
    except (OSError, json.JSONDecodeError):
        return ""


def _manifest_mod_commit() -> str:
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f).get("mod_commit", "")
    except (OSError, json.JSONDecodeError):
        return ""


def build_session_context(
    *,
    map_name: str = "",
    location_note: str = "",
    build_juego: str = "",
    mod_commit: str = "",
    clima: str = "",
    hora_juego: str = "",
    baseline_tag: str = "",
    capture_tool: str = "importar_ce_csv.py",
    setup: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "build_juego": build_juego or _manifest_build(),
        "mod_commit": mod_commit or _manifest_mod_commit(),
        "map": map_name,
        "location_note": location_note,
        "clima": clima,
        "hora_juego": hora_juego,
        "baseline_tag": baseline_tag,
        "capture_tool": capture_tool,
        "setup": dict(setup or {}),
    }
    if extra:
        ctx.update(extra)
    return ctx


def setup_from_protocol(protocol) -> dict[str, Any]:
    """Setup taller inferido del protocolo de prueba."""
    setup: dict[str, Any] = {
        "engine_id": protocol.engine_id,
        "tire": protocol.tire,
        "diff_lock": protocol.diff_lock,
        "low_gear": protocol.low_gear,
        "load_scenario_id": protocol.load_scenario_id,
        "gearbox": "",
        "suspension": "",
        "snorkel": False,
        "trailer": "",
    }
    if protocol.engine_id in ("aat8v", "i6"):
        from camiones.ck1500.engines import AAT8V_ENGINE_XML, AAT8V_UI_LABEL

        setup["engine_name_xml"] = AAT8V_ENGINE_XML
        if protocol.engine_id == "aat8v":
            setup["engine_ui"] = AAT8V_UI_LABEL
    if protocol.engine_id == "aat6v":
        from camiones.scout800.engines import AAT6V_ENGINE_XML, AAT6V_UI_LABEL

        setup["engine_name_xml"] = AAT6V_ENGINE_XML
        setup["engine_ui"] = AAT6V_UI_LABEL
    return setup
