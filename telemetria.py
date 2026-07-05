"""
Telemetria SnowRunner — Fase 5-6.

SnowRunner no publica telemetria (SimHub, API, UDP). Este modulo:
  1. Protocolos de prueba (ck1500, mh9500, fleetstar, marshall, kodiak)
  2. Grabacion manual HUD o import CSV Havok (grabar_ce.py)
  3. Comparacion juego vs sim (por tramo mud/hard)
  4. Lectura de game.log (errores mod, no fisica)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone

from sim.core import (
    ENGINE_I6,
    ENGINE_STOCK,
    LOAD_SCENARIOS,
    SURFACES,
    TIRES,
    VEHICLE_I6,
    EngineConfig,
    LoadScenario,
    SurfaceConfig,
    VehicleConfig,
    apply_load,
    run_sim,
    sample_at,
    total_mass_kg,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
TELEMETRY_DIR = os.path.join(ROOT, "telemetria", "sesiones")
ARCHIVE_SESSION_SUBDIR = "_archivo"
TELEMETRY_RESULTS_JSON = os.path.join(ROOT, "telemetria_comparacion.json")

# ce_<prefix>_... -> carpeta bajo telemetria/sesiones/
_SESSION_PREFIX_VEHICLE: dict[str, str] = {
    "fs": "fleetstar",
    "kd": "kodiak",
    "km": "marshall",
    "mh": "mh9500",
    "ck": "ck1500",
    "f1": "ck1500",
    "f2": "ck1500",
    "f3": "ck1500",
    "s8": "scout800",
}


def vehicle_id_from_session_name(session_id: str) -> str:
    """Infiere vehicle_id desde el id de sesion (ce_fs_..., ce_km_..., ce_f2_...)."""
    name = os.path.basename(session_id).removesuffix(".json")
    if not name.startswith("ce_"):
        return ""
    prefix = name[3:].split("_", 1)[0]
    return _SESSION_PREFIX_VEHICLE.get(prefix, "")


def session_subdir_for_vehicle(vehicle_id: str) -> str:
    vid = (vehicle_id or "").strip() or "_sin_clasificar"
    return os.path.join(TELEMETRY_DIR, vid)


def default_session_path(session: TelemetrySession) -> str:
    vid = (session.meta.vehicle_id or "").strip()
    if not vid:
        vid = vehicle_id_from_session_name(session.meta.id) or "_sin_clasificar"
    out_dir = session_subdir_for_vehicle(vid)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{session.meta.id}.json")


def iter_session_json_paths(*, include_archived: bool = False) -> list[str]:
    """Lista JSON de sesion: subcarpetas por vehiculo + raiz (legacy)."""
    if not os.path.isdir(TELEMETRY_DIR):
        return []
    paths: list[str] = []
    for name in sorted(os.listdir(TELEMETRY_DIR)):
        full = os.path.join(TELEMETRY_DIR, name)
        if os.path.isfile(full) and name.endswith(".json"):
            paths.append(full)
            continue
        if not os.path.isdir(full):
            continue
        if name == ARCHIVE_SESSION_SUBDIR and not include_archived:
            continue
        for fn in sorted(os.listdir(full)):
            if fn.endswith(".json"):
                paths.append(os.path.join(full, fn))
    return paths


def resolve_session_path(name_or_path: str) -> str | None:
    """Resuelve ruta absoluta por path, basename o session id."""
    if not name_or_path:
        return None
    if os.path.isfile(name_or_path):
        return os.path.abspath(name_or_path)
    base = os.path.basename(name_or_path)
    if not base.endswith(".json"):
        base = f"{base}.json"
    for path in iter_session_json_paths(include_archived=True):
        if os.path.basename(path) == base:
            return path
    legacy = os.path.join(TELEMETRY_DIR, base)
    if os.path.isfile(legacy):
        return legacy
    return None

SNOWRUNNER_LOGS = os.path.join(
    os.path.expanduser("~"),
    "Documents",
    "My Games",
    "SnowRunner",
    "base",
    "logs",
)

BINEDITOR_GUIDES = os.path.join(
    r"C:\Program Files (x86)\Steam\steamapps\common\SnowRunner",
    "Sources",
    "BinEditor",
    "Guides",
)


@dataclass
class TelemetrySample:
    t_s: float
    speed_kmh: float
    note: str = ""
    terrain_kind: str = ""  # hard | mud | soft | snow | ice | mixed | unknown (CE por rueda)
    terrain_map: str = ""  # legacy (blend mapa); ya no se rellena — usar terrain_kind + mud_grade


# Segmentos CE: duracion minima para comparar con sim
MIN_SEGMENT_DURATION_S = 12.0
MIN_SEGMENT_SAMPLES = 8


@dataclass
class SessionMeta:
    """Metadatos de una sesion en juego."""

    id: str
    created_utc: str
    map_name: str
    location_note: str
    surface_kind: str
    surface_label: str
    mod_applied: bool
    engine_id: str
    tire: str
    diff_lock: bool
    low_gear: bool
    load_scenario_id: str
    protocol_id: str
    duration_s: float
    notes: str = ""
    vehicle_id: str = "ck1500"
    session_context: dict = field(default_factory=dict)


@dataclass
class TelemetrySession:
    meta: SessionMeta
    samples: list[TelemetrySample] = field(default_factory=list)


@dataclass(frozen=True)
class TestProtocol:
    id: str
    label: str
    phase: int
    surface_kind: str
    surface_label: str
    tire: str
    diff_lock: bool
    low_gear: bool
    load_scenario_id: str
    mod_applied: bool
    engine_id: str
    duration_s: float
    hint: str
    vehicle_id: str = "ck1500"


TEST_PROTOCOLS: tuple[TestProtocol, ...] = (
    TestProtocol(
        "f1_asfalto_i6",
        "Fase 1 — aceleracion asfalto (mod I6)",
        1,
        "asphalt",
        "Asfalto",
        "highway",
        False,
        False,
        "vacio",
        True,
        "i6",
        60.0,
        "Carretera recta; anotar velocidad cada 5 s a fondo.",
    ),
    TestProtocol(
        "f1_asfalto_aat8v",
        "Fase 1 — asfalto AAT-8V 5.2 (solo motor, resto stock)",
        1,
        "asphalt",
        "Asfalto",
        "highway",
        False,
        False,
        "vacio",
        True,
        "aat8v",
        60.0,
        "CK1500: AAT-8V instalado; highway 31 stock; sin diff/caja/remolque; WOT ~60 s.",
    ),
    TestProtocol(
        "f2_barro_highway",
        "Fase 2 — barro ligero highway stock",
        2,
        "mud",
        "Barro",
        "highway",
        False,
        True,
        "vacio",
        True,
        "i6",
        45.0,
        "Mismo tramo barro; marcha baja; ¿avanza o 0 km/h?",
    ),
    TestProtocol(
        "f2_barro_offroad",
        "Fase 2 — barro offroad + diff lock",
        2,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "vacio",
        True,
        "i6",
        45.0,
        "Mismo tramo que f2_barro_highway.",
    ),
    TestProtocol(
        "f3_carga_barro",
        "Fase 3 — barro con remolque + vigas",
        3,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "trailer_metal_planks",
        True,
        "i6",
        60.0,
        "Remolque scout + 2 slots metal; repetir ruta vacio vs cargado.",
    ),
    TestProtocol(
        "f4_nieve_highway",
        "Fase 4 — nieve highway stock",
        4,
        "snow",
        "Nieve",
        "highway",
        False,
        False,
        "vacio",
        True,
        "i6",
        45.0,
        "Nieve suelta Alaska; ¿demasiado facil vs K10 real?",
    ),
    TestProtocol(
        "f4_hielo_cadenas",
        "Fase 4 — hielo con cadenas",
        4,
        "ice",
        "Hielo",
        "chains",
        False,
        False,
        "vacio",
        True,
        "i6",
        30.0,
        "Tramo helado; cadenas instaladas.",
    ),
    TestProtocol(
        "mh_f1_asfalto",
        "MH9500 F1 — asfalto diesel realista",
        1,
        "asphalt",
        "Asfalto",
        "highway",
        False,
        False,
        "vacio",
        True,
        "mh_real",
        60.0,
        "RWD stock; aceleracion a fondo.",
        "mh9500",
    ),
    TestProtocol(
        "mh_f2_barro_highway",
        "MH9500 F2 — barro highway RWD",
        2,
        "mud",
        "Barro",
        "highway",
        False,
        True,
        "vacio",
        True,
        "mh_real",
        45.0,
        "Sin AWD; esperar atasco o avance minimo.",
        "mh9500",
    ),
    TestProtocol(
        "mh_f2_barro_offroad",
        "MH9500 F2 — barro offroad AWD+diff",
        2,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "vacio",
        True,
        "mh_real",
        45.0,
        "Transfer AWD + diff lock instalados.",
        "mh9500",
    ),
    TestProtocol(
        "mh_f3_semi",
        "MH9500 F3 — semi cargado barro",
        3,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "semi_cargado",
        True,
        "mh_real",
        60.0,
        "Semirremolque ~12 t carga util.",
        "mh9500",
    ),
    TestProtocol(
        "fs_f1_asfalto",
        "Fleetstar F1 — asfalto Si-6V AWD",
        1,
        "asphalt",
        "Asfalto",
        "highway",
        True,
        False,
        "vacio",
        True,
        "fs_real",
        60.0,
        "42 UHD I; AWD+diff; aceleracion a fondo.",
        "fleetstar",
    ),
    TestProtocol(
        "fs_f2_barro_uhd",
        "Fleetstar F2 — barro 42 UHD I + AWD + diff",
        2,
        "mud",
        "Barro",
        "highway",
        True,
        True,
        "vacio",
        True,
        "fs_real",
        60.0,
        "Tu setup actual; marcha reducida; crawl lento esperado.",
        "fleetstar",
    ),
    TestProtocol(
        "fs_f2_barro_offroad",
        "Fleetstar F2 — barro offroad AWD+diff",
        2,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "vacio",
        True,
        "fs_real",
        60.0,
        "Cuando instales neumaticos UOD/UAD.",
        "fleetstar",
    ),
    TestProtocol(
        "fs_f3_carga",
        "Fleetstar F3 — bastidor cargado barro",
        3,
        "mud",
        "Barro",
        "highway",
        True,
        True,
        "frame_cargado",
        True,
        "fs_real",
        60.0,
        "Bastidor con carga util; UHD+AWD.",
        "fleetstar",
    ),
    TestProtocol(
        "kd_f1_asfalto",
        "Kodiak F1 — asfalto Si-6V AWD",
        1,
        "asphalt",
        "Asfalto",
        "highway",
        True,
        False,
        "vacio",
        True,
        "kd_real",
        60.0,
        "39\" UHD I; AWD+diff; 4 ruedas.",
        "kodiak",
    ),
    TestProtocol(
        "kd_f2_barro_uhd",
        "Kodiak F2 — barro 39\" UHD I + AWD + diff",
        2,
        "mud",
        "Barro",
        "highway",
        True,
        True,
        "vacio",
        True,
        "kd_real",
        60.0,
        "39\" UHD I; marcha L; calibrar KD_MUD_* con CE.",
        "kodiak",
    ),
    TestProtocol(
        "kd_f3_carga",
        "Kodiak F3 — bastidor cargado barro",
        3,
        "mud",
        "Barro",
        "highway",
        True,
        True,
        "frame_cargado",
        True,
        "kd_real",
        60.0,
        "Bastidor con carga util; 39\" UHD+AWD.",
        "kodiak",
    ),
    TestProtocol(
        "km_f1_asfalto",
        "Marshall F1 — asfalto Kr 135-T + TM II",
        1,
        "asphalt",
        "Asfalto",
        "mudtires",
        True,
        False,
        "vacio",
        True,
        "km_kr135",
        60.0,
        "45 TM II; AWD+diff; aceleracion a fondo.",
        "marshall",
    ),
    TestProtocol(
        "km_f2_barro_tm2",
        "Marshall F2 — barro 45 TM II + diff + reptadora",
        2,
        "mud",
        "Barro",
        "mudtires",
        True,
        True,
        "vacio",
        True,
        "km_kr135",
        60.0,
        "Tu setup; marcha reducida; calibrar KM_MUD_* con CE.",
        "marshall",
    ),
    TestProtocol(
        "km_f2_barro_profundo",
        "Marshall F2 — barro profundo TM II",
        2,
        "mud",
        "Barro profundo",
        "mudtires",
        True,
        True,
        "vacio",
        True,
        "km_kr135",
        60.0,
        "Tint oscuro / rutas ocultas; mismo tramo que km_f2_barro_tm2.",
        "marshall",
    ),
    TestProtocol(
        "km_f3_carga",
        "Marshall F3 — remolque scout cargado barro",
        3,
        "mud",
        "Barro",
        "mudtires",
        True,
        True,
        "trailer_metal_planks",
        True,
        "km_kr135",
        60.0,
        "Remolque scout + carga; TM II + diff.",
        "marshall",
    ),
    TestProtocol(
        "s8_f1_asfalto_aat6v",
        "Scout 800 F1 — asfalto AAT-6V + 33 HS I",
        1,
        "asphalt",
        "Asfalto",
        "highway_hs_i",
        True,
        False,
        "vacio",
        True,
        "aat6v",
        60.0,
        "Solo motor AAT-6V y HS I; diff siempre; WOT recto.",
        "scout800",
    ),
    TestProtocol(
        "s8_f2_barro_hs",
        "Scout 800 F2 — barro 33 HS I + diff",
        2,
        "mud",
        "Barro",
        "highway_hs_i",
        True,
        True,
        "vacio",
        True,
        "aat6v",
        45.0,
        "Mismo tramo barro; marcha L; calibrar S8_MUD_*.",
        "scout800",
    ),
    TestProtocol(
        "s8_f3_carga_barro",
        "Scout 800 F3 — remolque scout cargado barro",
        3,
        "mud",
        "Barro",
        "highway_hs_i",
        True,
        True,
        "trailer_metal_planks",
        True,
        "aat6v",
        60.0,
        "Remolque scout + vigas; HS I.",
        "scout800",
    ),
    TestProtocol(
        "f7_barro_dia",
        "Fase 7 — barro mediodia (misma ruta F2)",
        7,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "vacio",
        True,
        "i6",
        45.0,
        "Anotar hora juego; comparar con f7_barro_noche.",
    ),
    TestProtocol(
        "f7_barro_noche",
        "Fase 7 — barro noche (misma ruta)",
        7,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "vacio",
        True,
        "i6",
        45.0,
        "Misma linea que f7_barro_dia; lluvia visual no deberia cambiar fisica.",
    ),
    TestProtocol(
        "mh_f7_barro_dia",
        "MH9500 F7 — barro mediodia",
        7,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "vacio",
        True,
        "mh_real",
        45.0,
        "AWD+diff; misma ruta que mh_f7_barro_noche.",
        "mh9500",
    ),
    TestProtocol(
        "mh_f7_barro_noche",
        "MH9500 F7 — barro noche",
        7,
        "mud",
        "Barro",
        "offroad",
        True,
        True,
        "vacio",
        True,
        "mh_real",
        45.0,
        "Comparar v30 con mh_f7_barro_dia.",
        "mh9500",
    ),
)


# Protocolo CE por defecto al grabar (--auto): barro offroad / UHD segun camion
DEFAULT_MUD_PROTOCOL: dict[str, str] = {
    "ck1500": "f2_barro_offroad",
    "mh9500": "mh_f2_barro_offroad",
    "fleetstar": "fs_f2_barro_uhd",
    "marshall": "km_f2_barro_tm2",
    "kodiak": "kd_f2_barro_uhd",
    "scout800": "s8_f2_barro_hs",
}
DEFAULT_ASPHALT_PROTOCOL: dict[str, str] = {
    "ck1500": "f1_asfalto_i6",
    "mh9500": "mh_f1_asfalto",
    "fleetstar": "fs_f1_asfalto",
    "marshall": "km_f1_asfalto",
    "kodiak": "kd_f1_asfalto",
    "scout800": "s8_f1_asfalto_aat6v",
}
DEFAULT_LOADED_MUD_PROTOCOL: dict[str, str] = {
    "ck1500": "f3_carga_barro",
    "mh9500": "mh_f3_semi",
    "fleetstar": "fs_f3_carga",
    "marshall": "km_f3_carga",
    "kodiak": "kd_f3_carga",
    "scout800": "s8_f3_carga_barro",
}
DEFAULT_SNOW_PROTOCOL: dict[str, str] = {
    "ck1500": "f4_nieve_highway",
}
DEFAULT_ICE_PROTOCOL: dict[str, str] = {
    "ck1500": "f4_hielo_cadenas",
}

PAYLOAD_LOAD_THRESHOLD_KG = 300.0

# Meta de sesion desde terrain_kind CE (no desde protocolo fijo)
TERRAIN_KIND_SURFACE: dict[str, tuple[str, str]] = {
    "hard": ("asphalt", "Asfalto/firme"),
    "mud": ("mud", "Barro"),
    "soft": ("dirt", "Intermedio"),
    "snow": ("snow", "Nieve"),
    "ice": ("ice", "Hielo"),
    "mixed": ("mixed", "Mixto"),
    "unknown": ("unknown", "Desconocido"),
}


def dominant_terrain_kind_from_rows(rows: list[dict]) -> str:
    from collections import Counter

    kinds = Counter((r.get("terrain_kind") or "").strip().lower() for r in rows)
    kinds.pop("", None)
    return kinds.most_common(1)[0][0] if kinds else ""


def surface_meta_from_terrain_kind(terrain_kind: str) -> tuple[str, str]:
    return TERRAIN_KIND_SURFACE.get(
        (terrain_kind or "").strip().lower(),
        ("unknown", "Desconocido"),
    )


def _ce_bool_majority(rows: list[dict], field: str) -> bool | None:
    from collections import Counter

    votes: list[bool] = []
    for row in rows[-80:]:
        raw = (row.get(field) or "").strip().lower()
        if raw in ("1", "true", "on", "yes"):
            votes.append(True)
        elif raw in ("0", "false", "off", "no", "?"):
            votes.append(False)
    if not votes:
        return None
    return Counter(votes).most_common(1)[0][0]


def setup_hints_from_ce_rows(rows: list[dict]) -> dict[str, object]:
    """Traction / carga inferidos del CSV (auto-detectado en grabacion)."""
    hints: dict[str, object] = {"ce_auto_detected": True}
    diff = _ce_bool_majority(rows, "diff_lock_live")
    if diff is not None:
        hints["diff_lock"] = diff
    low = _ce_bool_majority(rows, "low_gear_live")
    if low is not None:
        hints["low_gear"] = low
    awd = _ce_bool_majority(rows, "awd_live")
    if awd is not None:
        hints["awd_live"] = awd
    loads = [r.get("load_hint", "").strip() for r in rows if r.get("load_hint")]
    if loads:
        from collections import Counter

        hints["load_hint_ce"] = Counter(loads).most_common(1)[0][0]
    return hints


@dataclass(frozen=True)
class LoadDetection:
    """Carga inferida desde columnas CE (load_hint, payload_kg)."""

    load_hint: str
    payload_kg: float
    loaded: bool
    load_scenario_id: str

    def summary(self) -> str:
        if not self.loaded:
            return "vacio"
        extra = f" ~{self.payload_kg:.0f} kg" if self.payload_kg > 0 else ""
        return f"{self.load_hint}{extra} -> {self.load_scenario_id}"


def load_scenario_for_vehicle(vehicle_id: str, load_hint: str, *, loaded: bool) -> str:
    if not loaded:
        return "vacio"
    if vehicle_id == "fleetstar":
        return "frame_cargado"
    if vehicle_id == "kodiak":
        return "frame_cargado"
    if vehicle_id == "mh9500":
        return "semi_cargado"
    if vehicle_id == "ck1500":
        return "trailer_metal_planks"
    if vehicle_id == "scout800":
        return "trailer_metal_planks"
    if vehicle_id == "marshall":
        return "trailer_metal_planks"
    return "vacio"


def is_loaded_session(meta: SessionMeta) -> bool:
    return bool(meta.load_scenario_id and meta.load_scenario_id != "vacio")


def detect_load_from_ce_rows(rows: list[dict], vehicle_id: str) -> LoadDetection:
    """Mayoria de load_hint / payload en el CSV."""
    from collections import Counter

    hints = Counter((r.get("load_hint") or "vacio").strip() for r in rows)
    dominant_hint = hints.most_common(1)[0][0] if hints else "vacio"

    payloads: list[float] = []
    for row in rows:
        for key in ("payload_kg", "cargo_mass_kg"):
            raw = (row.get(key) or "").strip()
            if not raw:
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            if 0 < value <= PAYLOAD_LOAD_THRESHOLD_KG * 30:
                payloads.append(value)

    payload_kg = sum(payloads) / len(payloads) if payloads else 0.0
    max_payload = max(payloads) if payloads else 0.0
    loaded_rows = sum(1 for h in hints if h in ("cargado", "trailer_cargado"))
    packed_rows = sum(
        1
        for r in rows
        if int((r.get("packed_cargo_slots") or "0").strip() or 0) > 0
    )
    path_rows = sum(
        1
        for r in rows
        if (r.get("path_cargo_type") or "").strip().startswith("cargo_")
    )
    loaded = (
        dominant_hint in ("cargado", "trailer_cargado")
        or max_payload > PAYLOAD_LOAD_THRESHOLD_KG
        or (rows and loaded_rows > len(rows) * 0.25)
        or (rows and packed_rows > len(rows) * 0.25)
        or (rows and path_rows > len(rows) * 0.25)
    )
    scenario = load_scenario_for_vehicle(vehicle_id, dominant_hint, loaded=loaded)
    return LoadDetection(dominant_hint, payload_kg, loaded, scenario)


def load_detection_from_sample(sample: dict, vehicle_id: str) -> LoadDetection:
    hint = (sample.get("load_hint") or "vacio").strip()
    payload = 0.0
    for key in ("payload_kg", "cargo_mass_kg"):
        try:
            payload = max(payload, float((sample.get(key) or "0").strip() or 0))
        except ValueError:
            pass
    loaded = hint in ("cargado", "trailer_cargado") or payload > PAYLOAD_LOAD_THRESHOLD_KG
    scenario = load_scenario_for_vehicle(vehicle_id, hint, loaded=loaded)
    return LoadDetection(hint, payload, loaded, scenario)


def _parse_grip(grip: str | float | None) -> float | None:
    if grip is None or grip == "":
        return None
    try:
        return float(grip)
    except (TypeError, ValueError):
        return None


def classify_surface_kind(
    surface_wheel: str,
    wheel_grip: str | float | None = None,
    terrain_kind: str = "",
    contact_avg: str | float | None = None,
) -> str:
    """mud | hard | soft | snow | ice | mixed | unknown — para elegir protocolo CE."""
    tk = (terrain_kind or "").strip().lower()
    if tk in ("mud", "hard", "soft", "mixed", "snow", "ice"):
        if tk == "soft":
            grip = _parse_grip(wheel_grip)
            contact = _parse_grip(contact_avg)
            if contact is not None and contact > 0.68:
                return "hard"
            return "mud" if grip is not None and grip < 0.25 else "hard"
        if tk == "mixed":
            grip = _parse_grip(wheel_grip)
            contact = _parse_grip(contact_avg)
            if contact is not None and contact > 0.68:
                return "hard"
            return "mud" if grip is not None and grip < 0.35 else "hard"
        return tk
    sw = (surface_wheel or "").strip().lower()
    if sw == "mud":
        return "mud"
    if sw == "hard":
        return "hard"
    grip = _parse_grip(wheel_grip)
    if sw == "mixed" and grip is not None:
        if grip < 0.12:
            return "mud"
        if grip > 0.5:
            return "hard"
    if grip is not None:
        if grip < 0.12:
            return "mud"
        if grip > 0.5:
            return "hard"
    return "unknown"


def resolve_auto_protocol(
    game_id: str,
    surface_wheel: str = "",
    wheel_grip: str | float | None = None,
    terrain_kind: str = "",
    contact_avg: str | float | None = None,
    *,
    load_detection: LoadDetection | None = None,
) -> tuple[str, str]:
    """
    Detecta protocolo TEST_PROTOCOLS segun camion activo, superficie y carga.
    Devuelve (protocol_id, mensaje para consola).
    """
    from camiones.registry import VEHICLES, vehicle_id_from_ce

    vid = vehicle_id_from_ce(game_id)
    if not vid:
        known = ", ".join(f"{v.ce_id} ({v.label})" for v in VEHICLES.values())
        raise ValueError(
            f"Camion no registrado: {game_id!r}. Conduce un vehiculo del mod. "
            f"IDs conocidos: {known}"
        )

    surface = classify_surface_kind(surface_wheel, wheel_grip, terrain_kind, contact_avg)
    label = VEHICLES[vid].label
    loaded = load_detection.loaded if load_detection else False

    if surface == "mud":
        if loaded:
            proto = DEFAULT_LOADED_MUD_PROTOCOL[vid]
            detail = f"barro + carga ({load_detection.summary() if load_detection else 'cargado'})"
        else:
            proto = DEFAULT_MUD_PROTOCOL[vid]
            detail = f"barro vacio (surface={surface_wheel or 'grip bajo'})"
    elif surface == "hard":
        proto = DEFAULT_ASPHALT_PROTOCOL[vid]
        if loaded:
            detail = f"firme + carga util (sim {load_detection.load_scenario_id if load_detection else 'cargado'})"
        else:
            detail = f"firme vacio (surface={surface_wheel or 'grip alto'})"
    elif surface == "snow":
        proto = DEFAULT_SNOW_PROTOCOL.get(vid, DEFAULT_MUD_PROTOCOL[vid])
        detail = f"nieve (terrain_kind=snow, grip={wheel_grip or '?'})"
    elif surface == "ice":
        proto = DEFAULT_ICE_PROTOCOL.get(vid, DEFAULT_MUD_PROTOCOL[vid])
        detail = f"hielo (terrain_kind=ice, grip={wheel_grip or '?'})"
    else:
        if loaded:
            proto = DEFAULT_LOADED_MUD_PROTOCOL[vid]
            detail = f"superficie ambigua; barro cargado por defecto ({load_detection.summary() if load_detection else ''})"
        else:
            proto = DEFAULT_MUD_PROTOCOL[vid]
            detail = (
                f"superficie ambigua ({surface_wheel or 'sin dato'}); "
                f"usando protocolo barro vacio por defecto"
            )

    p = next((x for x in TEST_PROTOCOLS if x.id == proto), None)
    if not p:
        raise ValueError(
            f"protocolo {proto!r} no definido en TEST_PROTOCOLS (vehiculo {vid!r})"
        )
    pname = p.label
    return proto, f"{label} | {detail} -> {proto} ({pname})"


def resolve_protocol_from_ce_rows(
    rows: list[dict],
) -> tuple[str, str, dict[str, int], LoadDetection]:
    """
    Protocolo meta para importar CSV CE: vehiculo + terreno dominante + carga.
    Sesiones mixtas: el protocolo meta sigue al terreno mas frecuente; la comparacion
    por tramos usa compare_session_by_terrain().
    """
    from collections import Counter

    from camiones.registry import vehicle_id_from_ce

    ids = [r.get("vehicle_id", "").strip() for r in rows if r.get("vehicle_id", "").strip()]
    game_id = Counter(ids).most_common(1)[0][0] if ids else ""
    if not game_id:
        raise ValueError("CSV sin vehicle_id — conduce en mapa con el mod activo")

    vehicle_id = vehicle_id_from_ce(game_id) or "ck1500"
    load_det = detect_load_from_ce_rows(rows, vehicle_id)

    kinds = Counter((r.get("terrain_kind") or "").strip().lower() for r in rows)
    kinds.pop("", None)
    terrain_kind = kinds.most_common(1)[0][0] if kinds else ""

    contacts = [_parse_grip(r.get("contact_avg")) for r in rows]
    contacts_ok = [c for c in contacts if c is not None]

    sample_row = rows[0] if rows else {}
    if terrain_kind:
        subset = [r for r in rows if (r.get("terrain_kind") or "").strip().lower() == terrain_kind]
        if subset:
            sample_row = subset[len(subset) // 2]

    proto, msg = resolve_auto_protocol(
        game_id,
        sample_row.get("surface_wheel") or "",
        sample_row.get("wheel_grip"),
        terrain_kind or sample_row.get("terrain_kind") or "",
        sample_row.get("contact_avg")
        or (f"{sum(contacts_ok) / len(contacts_ok):.3f}" if contacts_ok else None),
        load_detection=load_det,
    )
    kind_counts = dict(kinds)
    if terrain_kind:
        msg += f" | terreno dominante: {terrain_kind} ({kinds[terrain_kind]}/{len(rows)} muestras)"
        if len(kinds) > 1:
            mix = ", ".join(f"{k}={v}" for k, v in sorted(kinds.items()))
            msg += f" | mixto: {mix}"
    if load_det.loaded:
        msg += f" | carga: {load_det.summary()}"
    elif load_det.payload_kg > 0:
        msg += f" | payload bajo ({load_det.payload_kg:.0f} kg) -> vacio"
    return proto, msg, kind_counts, load_det


def parse_note_field(note: str, key: str) -> str:
    for part in (note or "").split(";"):
        part = part.strip()
        prefix = f"{key}="
        if part.startswith(prefix):
            return part[len(prefix) :].strip()
    return ""


def sample_terrain_kind(sample: TelemetrySample) -> str:
    if sample.terrain_kind:
        return sample.terrain_kind.strip().lower()
    kind = parse_note_field(sample.note, "kind")
    if kind:
        return kind.lower()
    surface = parse_note_field(sample.note, "surface")
    if surface:
        return surface.lower()
    return "unknown"


def sample_terrain_for_tramos(sample: TelemetrySample) -> str:
    """Terreno para segmentar tramos. Fuente de verdad: CE (Havok bajo rueda)."""
    return sample_terrain_kind(sample)


def sample_mud_grade(sample: TelemetrySample) -> str:
    return parse_note_field(sample.note, "mud_grade").strip().lower()


def sample_grip(sample: TelemetrySample) -> float | None:
    raw = parse_note_field(sample.note, "grip")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def compare_kind_for_terrain(terrain_kind: str, samples: list[TelemetrySample]) -> str | None:
    """Terreno CE -> mud | hard para elegir protocolo sim. None = no comparar."""
    kind = terrain_kind.lower()
    if kind == "mud":
        return "mud"
    if kind == "hard":
        return "hard"
    if kind == "soft":
        grips = [g for s in samples if (g := sample_grip(s)) is not None]
        avg = sum(grips) / len(grips) if grips else 0.2
        return "mud" if avg < 0.25 else "hard"
    return None


def protocol_for_compare_kind(
    vehicle_id: str,
    compare_kind: str,
    *,
    loaded: bool = False,
) -> str:
    if compare_kind == "mud":
        if loaded:
            return DEFAULT_LOADED_MUD_PROTOCOL[vehicle_id]
        return DEFAULT_MUD_PROTOCOL[vehicle_id]
    return DEFAULT_ASPHALT_PROTOCOL[vehicle_id]


def meta_with_protocol(base: SessionMeta, protocol_id: str) -> SessionMeta:
    protocol = next((p for p in TEST_PROTOCOLS if p.id == protocol_id), None)
    if not protocol:
        raise ValueError(f"protocolo desconocido: {protocol_id}")
    return replace(
        base,
        protocol_id=protocol.id,
        surface_kind=protocol.surface_kind,
        surface_label=protocol.surface_label,
        mod_applied=protocol.mod_applied,
        engine_id=protocol.engine_id,
        tire=protocol.tire,
        diff_lock=protocol.diff_lock,
        low_gear=protocol.low_gear,
        load_scenario_id=protocol.load_scenario_id,
    )


@dataclass(frozen=True)
class TerrainSegment:
    terrain_kind: str
    compare_kind: str
    protocol_id: str
    t_start: float
    t_end: float
    samples: tuple[TelemetrySample, ...]


def split_session_by_terrain(
    session: TelemetrySession,
    min_duration_s: float = MIN_SEGMENT_DURATION_S,
    min_samples: int = MIN_SEGMENT_SAMPLES,
) -> tuple[list[TerrainSegment], list[dict]]:
    """Parte una sesion en tramos homogeneos por terrain_kind."""
    segments: list[TerrainSegment] = []
    skipped: list[dict] = []
    if not session.samples:
        return segments, skipped

    def flush(buf: list[TelemetrySample], raw_kind: str) -> None:
        if not buf:
            return
        t_start, t_end = buf[0].t_s, buf[-1].t_s
        duration = t_end - t_start
        compare_kind = compare_kind_for_terrain(raw_kind, buf)
        base_info = {
            "terrain_kind": raw_kind,
            "t_start": round(t_start, 1),
            "t_end": round(t_end, 1),
            "duration_s": round(duration, 1),
            "sample_count": len(buf),
        }
        if compare_kind is None:
            skipped.append({**base_info, "reason": "mixed/unknown — sin protocolo unico"})
            return
        if duration < min_duration_s or len(buf) < min_samples:
            skipped.append(
                {
                    **base_info,
                    "reason": f"tramo corto (min {min_duration_s}s y {min_samples} muestras)",
                }
            )
            return
        try:
            protocol_id = protocol_for_compare_kind(
                session.meta.vehicle_id,
                compare_kind,
                loaded=is_loaded_session(session.meta),
            )
        except KeyError:
            skipped.append(
                {**base_info, "reason": f"vehiculo {session.meta.vehicle_id!r} sin protocolo"}
            )
            return
        segments.append(
            TerrainSegment(
                terrain_kind=raw_kind,
                compare_kind=compare_kind,
                protocol_id=protocol_id,
                t_start=t_start,
                t_end=t_end,
                samples=tuple(buf),
            )
        )

    buf: list[TelemetrySample] = []
    current_kind = sample_terrain_for_tramos(session.samples[0])
    for sample in session.samples:
        kind = sample_terrain_for_tramos(sample)
        if kind != current_kind and buf:
            flush(buf, current_kind)
            buf = []
            current_kind = kind
        buf.append(sample)
        current_kind = kind
    flush(buf, current_kind)
    return segments, skipped


def compare_samples_to_sim(
    samples: list[TelemetrySample],
    meta: SessionMeta,
    *,
    t_origin: float = 0.0,
) -> dict:
    """Compara muestras con sim; tiempos rebasados a t_origin (inicio del tramo)."""
    if not samples:
        return {"sample_count": 0, "mae_kmh": 0.0, "rows": []}

    surface = _surface_for_kind(meta.surface_kind, meta.surface_label)
    vehicle = build_vehicle_for_session(meta)
    engine = _engine_for_session(meta)
    t_end = max(s.t_s for s in samples)
    duration = max(5.0, t_end - t_origin + 2.0)
    series = run_sim(vehicle, engine, surface, duration, low_gear=meta.low_gear)

    rows: list[dict] = []
    for sample in samples:
        t_rel = sample.t_s - t_origin
        sim_v = round(sim_speed_at(series, t_rel), 1)
        rows.append(
            {
                "t_s": round(t_rel, 1),
                "game_kmh": sample.speed_kmh,
                "sim_kmh": sim_v,
                "delta_kmh": round(sample.speed_kmh - sim_v, 1),
                "note": sample.note,
            }
        )

    deltas = [r["delta_kmh"] for r in rows]
    mae = round(sum(abs(d) for d in deltas) / len(deltas), 1) if deltas else 0.0
    seg_duration = t_end - t_origin
    game_v30 = next((r["game_kmh"] for r in rows if r["t_s"] >= min(30.0, seg_duration - 1)), None)
    sim_v30 = round(sim_speed_at(series, min(30.0, seg_duration)), 1) if seg_duration >= 8 else None

    return {
        "sample_count": len(rows),
        "mae_kmh": mae,
        "game_v30_kmh": game_v30,
        "sim_v30_kmh": sim_v30,
        "sim_v_end_kmh": round(
            series.speeds_kmh[min(len(series.speeds_kmh) - 1, int(seg_duration * 2))], 1
        ),
        "rows": rows,
        "total_mass_kg": total_mass_kg(vehicle),
        "tire": meta.tire,
        "diff_lock": meta.diff_lock,
        "load": meta.load_scenario_id,
        "surface": meta.surface_label,
    }


def compare_session_by_terrain(session: TelemetrySession) -> dict:
    """
    Opcion C: comparacion por tramos de terreno homogeneo.
    Sesiones largas mixtas -> un MAE por tramo mud/hard con el protocolo adecuado.
    """
    whole = compare_session_to_sim(session)
    segments, skipped = split_session_by_terrain(session)
    segment_comparisons: list[dict] = []

    for seg in segments:
        seg_meta = meta_with_protocol(session.meta, seg.protocol_id)
        if is_loaded_session(session.meta):
            seg_meta = replace(seg_meta, load_scenario_id=session.meta.load_scenario_id)
        cmp = compare_samples_to_sim(list(seg.samples), seg_meta, t_origin=seg.t_start)
        segment_comparisons.append(
            {
                "terrain_kind": seg.terrain_kind,
                "compare_kind": seg.compare_kind,
                "protocol_id": seg.protocol_id,
                "t_start": seg.t_start,
                "t_end": seg.t_end,
                "duration_s": round(seg.t_end - seg.t_start, 1),
                **cmp,
            }
        )

    kind_counts: dict[str, int] = {}
    mud_grade_counts: dict[str, int] = {}
    for s in session.samples:
        k = sample_terrain_kind(s)
        kind_counts[k] = kind_counts.get(k, 0) + 1
        mg = sample_mud_grade(s)
        if mg:
            mud_grade_counts[mg] = mud_grade_counts.get(mg, 0) + 1

    return {
        "session_id": session.meta.id,
        "vehicle_id": session.meta.vehicle_id,
        "protocol_id_whole": session.meta.protocol_id,
        "whole_session": whole,
        "terrain_sample_counts": kind_counts,
        "mud_grade_sample_counts": mud_grade_counts,
        "segments": segment_comparisons,
        "skipped_segments": skipped,
    }


def _engine_for_id(engine_id: str) -> EngineConfig:
    if engine_id == "mh_real":
        from camiones.mh9500.simulador import ENGINE_REAL_MH

        return ENGINE_REAL_MH
    if engine_id == "mh_stock":
        from camiones.mh9500.simulador import ENGINE_STOCK_MH

        return ENGINE_STOCK_MH
    if engine_id == "fs_real":
        from camiones.fleetstar.simulador import ENGINE_REAL_FS

        return ENGINE_REAL_FS
    if engine_id == "fs_real_2100":
        from camiones.fleetstar.simulador import ENGINE_REAL_FS_2100

        return ENGINE_REAL_FS_2100
    if engine_id == "fs_stock":
        from camiones.fleetstar.simulador import ENGINE_STOCK_FS

        return ENGINE_STOCK_FS
    if engine_id == "kd_real":
        from camiones.fleetstar.simulador import ENGINE_REAL_FS

        return ENGINE_REAL_FS
    if engine_id == "kd_real_2100":
        from camiones.fleetstar.simulador import ENGINE_REAL_FS_2100

        return ENGINE_REAL_FS_2100
    if engine_id == "kd_stock":
        from camiones.fleetstar.simulador import ENGINE_STOCK_FS

        return ENGINE_STOCK_FS
    if engine_id == "km_kr104":
        from camiones.marshall.simulador import ENGINE_REAL_KM

        return ENGINE_REAL_KM
    if engine_id == "km_kr135":
        from camiones.marshall.simulador import ENGINE_REAL_KM_135

        return ENGINE_REAL_KM_135
    if engine_id == "km_stock":
        from camiones.marshall.simulador import ENGINE_STOCK_KM

        return ENGINE_STOCK_KM
    if engine_id == "aat8v":
        from camiones.ck1500.engines import engine_for_ck1500

        return engine_for_ck1500(engine_id)
    if engine_id in ("aat6v", "s8_real", "s8_stock"):
        from camiones.scout800.engines import engine_for_scout800

        return engine_for_scout800(engine_id)
    return ENGINE_I6 if engine_id == "i6" else ENGINE_STOCK


def _engine_name_xml_from_meta(meta: SessionMeta) -> str:
    setup = (meta.session_context or {}).get("setup") or {}
    return str(setup.get("engine_name_xml") or "").strip()


def _engine_for_session(meta: SessionMeta) -> EngineConfig:
    if meta.vehicle_id == "fleetstar":
        from camiones.fleetstar.simulador import engine_for_fleetstar

        return engine_for_fleetstar(meta.engine_id, _engine_name_xml_from_meta(meta))
    if meta.vehicle_id == "kodiak":
        from camiones.fleetstar.simulador import engine_for_fleetstar

        eid = meta.engine_id
        if eid == "kd_real":
            eid = "fs_real"
        elif eid == "kd_real_2100":
            eid = "fs_real_2100"
        elif eid == "kd_stock":
            eid = "fs_stock"
        return engine_for_fleetstar(eid, _engine_name_xml_from_meta(meta))
    if meta.vehicle_id == "ck1500":
        from camiones.ck1500.engines import engine_for_ck1500

        return engine_for_ck1500(meta.engine_id, _engine_name_xml_from_meta(meta))
    if meta.vehicle_id == "scout800":
        from camiones.scout800.engines import engine_for_scout800

        return engine_for_scout800(meta.engine_id, _engine_name_xml_from_meta(meta))
    if meta.vehicle_id == "marshall":
        from camiones.marshall.simulador import engine_for_marshall

        return engine_for_marshall(meta.engine_id, _engine_name_xml_from_meta(meta))
    return _engine_for_id(meta.engine_id)


def _surface_for_kind(kind: str, label: str) -> SurfaceConfig:
    for s in SURFACES:
        if s.kind == kind and s.name == label:
            return s
    for s in SURFACES:
        if s.kind == kind:
            return s
    raise ValueError(f"superficie desconocida: {kind!r}")


def _load_for_id(load_id: str) -> LoadScenario:
    for s in LOAD_SCENARIOS:
        if s.id == load_id:
            return s
    raise ValueError(f"escenario carga desconocido: {load_id!r}")


def build_vehicle_for_session(meta: SessionMeta) -> VehicleConfig:
    if meta.vehicle_id == "mh9500":
        from camiones.mh9500.simulador import TIRES as MH_TIRES, make_vehicle

        tire_key = meta.tire if meta.tire in MH_TIRES else "highway"
        layout = "awd" if meta.diff_lock else "rwd"
        base = make_vehicle(tire_key, diff_lock=meta.diff_lock, drive_layout=layout)
        return apply_load(base, _load_for_id(meta.load_scenario_id))
    if meta.vehicle_id == "fleetstar":
        from camiones.fleetstar.simulador import TIRES as FS_TIRES, make_vehicle

        tire_key = meta.tire if meta.tire in FS_TIRES else "highway"
        layout = "awd" if meta.diff_lock else "rwd"
        base = make_vehicle(tire_key, diff_lock=meta.diff_lock, drive_layout=layout)
        return apply_load(base, _load_for_id(meta.load_scenario_id))
    if meta.vehicle_id == "kodiak":
        from camiones.kodiak.simulador import TIRES as KD_TIRES, make_vehicle

        tire_key = meta.tire if meta.tire in KD_TIRES else "highway"
        layout = "awd" if meta.diff_lock else "rwd"
        base = make_vehicle(tire_key, diff_lock=meta.diff_lock, drive_layout=layout)
        return apply_load(base, _load_for_id(meta.load_scenario_id))
    if meta.vehicle_id == "marshall":
        from camiones.marshall.simulador import TIRES as KM_TIRES, make_vehicle

        tire_key = meta.tire if meta.tire in KM_TIRES else "mudtires"
        base = make_vehicle(tire_key, diff_lock=meta.diff_lock, drive_layout="4wd")
        return apply_load(base, _load_for_id(meta.load_scenario_id))
    if meta.vehicle_id == "scout800":
        from camiones.scout800.simulador import TIRES as S8_TIRES, make_vehicle

        tire_key = meta.tire if meta.tire in S8_TIRES else "highway_hs_i"
        base = make_vehicle(tire_key, diff_lock=True, drive_layout="4wd")
        return apply_load(base, _load_for_id(meta.load_scenario_id))
    base = replace(
        VEHICLE_I6,
        tire=TIRES[meta.tire],
        tire_name=meta.tire,
        diff_lock=meta.diff_lock,
    )
    return apply_load(base, _load_for_id(meta.load_scenario_id))


def meta_from_protocol(
    protocol: TestProtocol,
    map_name: str = "",
    location_note: str = "",
    notes: str = "",
    session_context: dict | None = None,
) -> SessionMeta:
    from datos.session_context import build_session_context, setup_from_protocol

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ctx = session_context or build_session_context(
        map_name=map_name,
        location_note=location_note,
        capture_tool="telemetria.py",
        setup=setup_from_protocol(protocol),
    )
    return SessionMeta(
        id=f"{protocol.id}_{ts}",
        created_utc=datetime.now(timezone.utc).isoformat(),
        map_name=map_name,
        location_note=location_note,
        surface_kind=protocol.surface_kind,
        surface_label=protocol.surface_label,
        mod_applied=protocol.mod_applied,
        engine_id=protocol.engine_id,
        vehicle_id=protocol.vehicle_id,
        tire=protocol.tire,
        diff_lock=protocol.diff_lock,
        low_gear=protocol.low_gear,
        load_scenario_id=protocol.load_scenario_id,
        protocol_id=protocol.id,
        duration_s=protocol.duration_s,
        notes=notes,
        session_context=ctx,
    )


def session_to_dict(session: TelemetrySession) -> dict:
    return {
        "meta": asdict(session.meta),
        "samples": [asdict(s) for s in session.samples],
    }


def session_from_dict(data: dict) -> TelemetrySession:
    samples = []
    for s in data["samples"]:
        sample = TelemetrySample(**s)
        if not sample.terrain_kind and sample.note:
            tk = parse_note_field(sample.note, "kind") or parse_note_field(sample.note, "surface")
            if tk:
                sample = replace(sample, terrain_kind=tk)
        samples.append(sample)
    meta_raw = dict(data["meta"])
    meta_raw.setdefault("session_context", {})
    return TelemetrySession(meta=SessionMeta(**meta_raw), samples=samples)


def save_session(session: TelemetrySession, path: str | None = None) -> str:
    os.makedirs(TELEMETRY_DIR, exist_ok=True)
    out = path or default_session_path(session)
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(session_to_dict(session), f, indent=2, ensure_ascii=False)
    return out


def load_session(path: str) -> TelemetrySession:
    with open(path, encoding="utf-8") as f:
        return session_from_dict(json.load(f))


def list_sessions(*, include_archived: bool = False) -> list[str]:
    return iter_session_json_paths(include_archived=include_archived)


def sim_speed_at(series, t_s: float) -> float:
    return sample_at(series, t_s)


def compare_session_to_sim(session: TelemetrySession) -> dict:
    """Compara muestras del juego con prediccion del simulador."""
    meta = session.meta
    surface = _surface_for_kind(meta.surface_kind, meta.surface_label)
    vehicle = build_vehicle_for_session(meta)
    engine = _engine_for_session(meta)
    duration = max(meta.duration_s, max((s.t_s for s in session.samples), default=0.0) + 1.0)
    series = run_sim(vehicle, engine, surface, duration, low_gear=meta.low_gear)

    rows: list[dict] = []
    for sample in session.samples:
        sim_v = round(sim_speed_at(series, sample.t_s), 1)
        rows.append(
            {
                "t_s": sample.t_s,
                "game_kmh": sample.speed_kmh,
                "sim_kmh": sim_v,
                "delta_kmh": round(sample.speed_kmh - sim_v, 1),
                "note": sample.note,
            }
        )

    deltas = [r["delta_kmh"] for r in rows]
    mae = round(sum(abs(d) for d in deltas) / len(deltas), 1) if deltas else 0.0
    game_v30 = next((r["game_kmh"] for r in rows if r["t_s"] >= 28), None)
    sim_v30 = round(sim_speed_at(series, 30.0), 1)

    return {
        "session_id": meta.id,
        "protocol_id": meta.protocol_id,
        "surface": meta.surface_label,
        "tire": meta.tire,
        "diff_lock": meta.diff_lock,
        "load": meta.load_scenario_id,
        "total_mass_kg": total_mass_kg(vehicle),
        "sample_count": len(rows),
        "mae_kmh": mae,
        "game_v30_kmh": game_v30,
        "sim_v30_kmh": sim_v30,
        "sim_v_end_kmh": round(series.speeds_kmh[-1], 1),
        "rows": rows,
    }


def scan_game_logs(max_lines: int = 80) -> dict:
    """Lee tail de logs de SnowRunner (errores mod, no telemetria fisica)."""
    result: dict = {"log_dir": SNOWRUNNER_LOGS, "files": [], "errors": [], "warnings": []}
    if not os.path.isdir(SNOWRUNNER_LOGS):
        result["missing"] = True
        return result
    for name in ("LegacyLog.txt", "game.log", "Game.log"):
        path = os.path.join(SNOWRUNNER_LOGS, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = lines[-max_lines:]
        result["files"].append({"name": name, "lines": len(lines), "tail": tail})
        for line in tail:
            low = line.lower()
            if "error" in low or "failed" in low:
                result["errors"].append(line.strip())
            elif "warning" in low or "warn" in low:
                result["warnings"].append(line.strip())
    return result


def list_bineditor_guides() -> list[str]:
    if not os.path.isdir(BINEDITOR_GUIDES):
        return []
    return sorted(f for f in os.listdir(BINEDITOR_GUIDES) if not f.startswith("~$"))


def record_manual_interactive(
    meta: SessionMeta,
    interval_s: float = 5.0,
) -> TelemetrySession:
    """Graba velocidad del HUD cada interval_s segundos."""
    session = TelemetrySession(meta=meta)
    print(f"\nSesion: {meta.id}")
    print(f"Protocolo: {meta.protocol_id} | {meta.surface_label} | {meta.tire}")
    print(f"Intervalo {interval_s}s — Enter sin numero = pausa; 'q' = terminar\n")

    t0 = time.monotonic()
    next_t = 0.0
    while True:
        elapsed = time.monotonic() - t0
        if elapsed >= meta.duration_s:
            break
        if elapsed < next_t:
            time.sleep(0.1)
            continue
        prompt = f"[{elapsed:5.1f}s] velocidad km/h (HUD): "
        try:
            raw = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if raw.lower() in ("q", "quit", "fin"):
            break
        if not raw:
            next_t += interval_s
            continue
        try:
            speed = float(raw.replace(",", "."))
        except ValueError:
            print("  Numero invalido, reintenta.")
            continue
        note = ""
        if speed <= 0.5:
            extra = input("  ¿Atascado? (s/n): ").strip().lower()
            if extra in ("s", "si", "y", "yes"):
                note = "stuck"
        session.samples.append(TelemetrySample(round(elapsed, 1), speed, note))
        next_t += interval_s

    return session


def export_comparison_report(sessions: list[TelemetrySession]) -> dict:
    comparisons = [compare_session_by_terrain(s) for s in sessions]
    logs = scan_game_logs()
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "comparisons": comparisons,
        "game_logs": {
            "dir": logs.get("log_dir"),
            "missing": logs.get("missing", False),
            "error_count": len(logs.get("errors", [])),
            "warning_count": len(logs.get("warnings", [])),
            "recent_errors": logs.get("errors", [])[-10:],
        },
        "bineditor_guides": list_bineditor_guides(),
    }
