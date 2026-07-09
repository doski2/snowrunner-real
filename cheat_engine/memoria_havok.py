"""Lectura Havok de SnowRunner sin Cheat Engine (offsets validados 2026-06)."""

from __future__ import annotations

import ctypes
import math
import os
import re
import struct
import subprocess
import sys
from ctypes import wintypes
from typing import Any

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Si camiones.registry no importa (p. ej. scan_cargo sin PYTHONPATH)
_FALLBACK_EMPTY_MASS_KG: dict[str, float] = {
    "s_fleetstar_f2070a": 6650.0,
    "international_fleetstar_f2070a": 6650.0,
    "s_chevrolet_kodiakc70": 7900.0,
    "s_chevrolet_kodiakC70": 7900.0,
    "chevrolet_kodiakc70": 7900.0,
    "s_gmc_9500": 7500.0,
    "s_gmc9500": 7500.0,
    "s_chevrolet_ck1500": 1750.0,
    "s_khan_39_marshall": 1780.0,
    "khan_39_marshall": 1780.0,
    "s_tatra_t813": 14571.0,
    "tatra_t813": 14571.0,
}

kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

MODULE = "SnowRunner.exe"
TRUCK_CONTROL_OFF = 0x2A8EDD8  # RTTI TRUCK_CONTROL — build 2026-06-25 (antes 0x2A876A8)
DRIVE_LOGIC_OFF = 0x2A8EDC8  # validado mismo build (antes 0x2E5DA08)
OFF_VEH_TRUCK = 0x8
OFF_VEH_DRIVE = 0x20
OFF_RB = 0x5D0
OFF_VX = 0x230
OFF_VY = 0x234
OFF_VZ = 0x238
OFF_YAW = 0x244  # hkpMotion angular velocity Y (rad/s) — giro en plano

# Giro util para correlacionar con carga (Fase 3)
MIN_TURN_SPEED_KMH = 3.0
MIN_YAW_RAD_S = 0.02
OFF_POS_X = 0x1A0  # hkTransform mundo X
OFF_POS_Y = 0x1A4
OFF_POS_Z = 0x1A8
OFF_ID = 0xD10
OFF_ADDON = 0x48
OFF_FUEL = 0x568
OFF_FUEL_MAX = 0x570
OFF_WHEELS_BEGIN = 0x200
OFF_WHEELS_END = 0x208
# TRUCK_WHEEL_MODEL — calibrado wheel_snaps 2026-06 (MH9500 + Fleetstar asfalto_fs)
OFF_WHEEL_GRIP = 0x2FC  # ~1.0 asfalto MH, ~0.2 asfalto FS UHD, ~0.01 barro
OFF_WHEEL_SURFACE = 0x2B4  # ~+0.81 asfalto MH; en FS suele ser deformacion (~-0.9)
OFF_WHEEL_CONTACT = 0x2EC  # firmeza sustancia: ~0.80 asfalto, ~0.55 barro (ambos camiones)
OFF_WHEEL_LABEL = 0x124  # nombre UI parcial: "... AT I" / "... OS I" (scout, jun-2026)
OFF_WHEEL_TYPE_XML = 0x140  # tipo rueda XML inline: wheels_scout2, wheels_medium_double, ...
OFF_WHEEL_TYPE_SCAN_START = 0x120
OFF_WHEEL_TYPE_SCAN_END = 0x190

OFF_RB_MOTION_PTR = 0xB8  # hkpRigidBody -> hkpMotion*
OFF_MOTION_INV_MASS = 0xA4  # 1/masa (kg); Fleetstar vacio ~1/6947

PAYLOAD_TARE_KG = 400.0  # combustible/aditivos sobre masa XML vacia
PAYLOAD_LOAD_THRESHOLD_KG = 300.0
TRAILER_PAYLOAD_TARE_KG = 100.0
# Bastidor Fleetstar sideboard: hasta ~2 slots; tope para filtrar lecturas CE corruptas
MAX_FRAME_PAYLOAD_KG = 6500.0
MAX_SANE_CSV_PAYLOAD_KG = 8000.0
DEFAULT_PACKED_SLOT_KG = 1200.0

OFF_ATTACH_MANAGER = 0x078  # manager addons / enganche (experimental)
OFF_ATTACH_CARGO_SUB = 0x030  # slots BoneCargo_* (plataforma lateral / bastidor)
OFF_LOAD_REGISTRY = 0x060  # registro runtime carga empaquetada (no confundir con +1E8 vector end)
OFF_CARGO_ENTRY_TYPE = 0x0D0  # tipo cargo en entrada load registry
OFF_ADDON_PHYS_BEGIN = 0x1E0  # std::vector — cuerpos Havok de addons/carga (mappings.md)
OFF_ADDON_PHYS_END = 0x1E8
OFF_CARGO_MANAGER = 0x1E8  # legacy alias del fin del vector +1E0
OFF_SIM_ISLAND = 0x128  # hkpRigidBody -> hkpSimulationIsland*
OFF_ISLAND_BODIES = 0x60  # puntero a array de hkpRigidBody*
OFF_ISLAND_COUNT = 0x68  # entero: nº de piezas (mappings.md; no es end del vector)
_ATTACH_CARGO_SUB_OFFS = (0x030, 0x028, 0x038, 0x040, 0x048)
_ISLAND_CARGO_MASS_MIN_KG = 450.0  # por debajo: ruedas / piezas pequeñas
_LOAD_LATCH_MAX_MISS = 80  # ~40 s a 0,5 s antes de soltar cargado
_VEH_LOAD_LATCH: dict[int, dict[str, Any]] = {}
_LOAD_REGISTRY_CHAINS: tuple[tuple[int, ...], ...] = (
    (0x060, 0x090, 0x058, 0x170),
    (0x060, 0x088, 0x058, 0x170),
    (0x060, 0x090, 0x050, 0x170),
    (0x060, 0x090, 0x058, 0x168),
)

TRAILER_ID_TOKENS = (
    "trailer",
    "semi",
    "lowboy",
    "flatbed",
    "sideboard",
    "fuel_tank",
    "logging",
    "maintenance",
    "service_body",
)
CARGO_ID_TOKENS = (
    "plank",
    "brick",
    "metal_roll",
    "metal_plank",
    "spare",
    "concrete",
    "container",
    "pipe",
    "wood",
    "block",
    "crate",
    "cargo",
    "log_",
    "logs",
)
_LOAD_IGNORE_ID_TOKENS = (
    "fence",
    "cdt",
    "ru17",
    ".tga",
    "transfer",
    "wheel",
    "chain",
    "uhd",
    "offroad",
    "highway",
    "allterrain",
)

CSV_HEADER = (
    "t_s,speed_kmh,vel_x,vel_y,vel_z,ang_yaw,pos_y,fuel_pct,"
    "vehicle_id,surface_wheel,wheel_grip,terrain_hint,event,chain,"
    "terrain_kind,terrain_map,pos_x,pos_z,surface_avg,contact_avg,grip_min,grip_max,"
    "surface_deform_avg,contact_min,contact_max,mud_grade,mud_grade_label,"
    "load_hint,trailer_id,cargo_mass_kg,total_mass_kg,empty_mass_kg,payload_kg,"
    "trailer_mass_kg,truck_mass_kg,attached_cargo_mass_kg,yaw_rate_deg_s,turn_radius_m,"
    "packed_cargo_slots,path_cargo_type,frame_addon,"
    "diff_lock_live,awd_live,low_gear_live,throttle,engine_rpm,fuel_rate_pct_min,"
    "map_name,level_id\n"
)

BASE_DIR = os.path.join(os.path.expanduser("~"), "Documents", "My Games", "SnowRunner", "base")
LOG_PRIMARY = os.path.join(BASE_DIR, "telemetria_ce_log.csv")
LOG_FALLBACK = os.path.join(os.path.dirname(__file__), "telemetria_ce_log.csv")
STATUS_PATH = os.path.join(BASE_DIR, "telemetria_ce_status.txt")


def turn_metrics_from_yaw(speed_kmh: float, yaw_rate_rad_s: float) -> dict[str, float | str]:
    """Velocidad de giro y radio desde angular_velocity_y Havok (+0x244).

    ang_yaw / yaw_rate_rad_s: rad/s en eje Y (positivo = girar a la derecha en mundo).
    turn_radius_m: v/|omega| solo si hay giro claro (util vs payload en analisis).
    """
    yaw_deg_s = yaw_rate_rad_s * 180.0 / math.pi
    turn_radius_m: float | str = ""
    if speed_kmh >= MIN_TURN_SPEED_KMH and abs(yaw_rate_rad_s) >= MIN_YAW_RAD_S:
        speed_ms = speed_kmh / 3.6
        turn_radius_m = round(speed_ms / abs(yaw_rate_rad_s), 1)
    return {
        "yaw_rate_rad_s": yaw_rate_rad_s,
        "yaw_rate_deg_s": round(yaw_deg_s, 2),
        "turn_radius_m": turn_radius_m,
    }


def enrich_turn_fields(sample: dict[str, Any]) -> dict[str, Any]:
    """Anade yaw_rate_deg_s y turn_radius_m a una muestra con ang_yaw y speed_kmh."""
    try:
        speed = float(sample.get("speed_kmh", 0) or 0)
        yaw = float(sample.get("ang_yaw", 0) or 0)
    except (TypeError, ValueError):
        return sample
    metrics = turn_metrics_from_yaw(speed, yaw)
    out = dict(sample)
    out.update(metrics)
    return out


def resolve_log_path() -> str:
    for path in (LOG_PRIMARY, LOG_FALLBACK):
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError:
                continue
        try:
            with open(path, "a", encoding="utf-8"):
                pass
            return path
        except OSError:
            continue
    return LOG_PRIMARY


def _iter_ptr_vector(h: int, begin: int, end: int, *, max_count: int = 32) -> list[int]:
    """Elementos de un std::vector de punteros (begin/end en bytes del objeto)."""
    if not begin or not end or end <= begin:
        return []
    count = (end - begin) // 8
    if count <= 0 or count > max_count:
        return []
    out: list[int] = []
    for i in range(count):
        p = read_u64(h, begin + i * 8)
        if p and p > 0x10000:
            out.append(p)
    return out


def read_wheel_pointers(h: int, veh: int) -> list[int]:
    begin = read_u64(h, veh + OFF_WHEELS_BEGIN)
    end = read_u64(h, veh + OFF_WHEELS_END)
    return _iter_ptr_vector(h, begin, end, max_count=16)


def _effective_surface(surface_b4: float, contact_ec: float) -> float:
    """
    Sustancia bajo la rueda para clasificar.

    MH9500: +0x2B4 ~+0.8 asfalto / ~-0.15 barro.
    Fleetstar: +0x2B4 suele quedar muy negativo; +0x2EC discrimina (~0.80 vs ~0.55).
    """
    if surface_b4 > 0.25:
        return surface_b4
    return contact_ec


def _classify_wheel_contact(
    grip: float,
    surface: float,
    *,
    deform: float | None = None,
) -> str:
    """Clasifica una rueda: hard | mud | soft | snow | ice.

  Calibrado asfalto/barro (2026-06) + nieve Alaska (deform +0x2B4 alto, grip bajo).
  """
    if grip < 0.06 and surface > 0.68:
        return "ice"
    if (
        deform is not None
        and deform > 0.55
        and grip < 0.45
        and surface > 0.55
    ):
        return "snow"
    if (grip > 0.45 and surface > 0.30) or (surface > 0.68 and grip > 0.12):
        return "hard"
    if grip < 0.25 or (surface < 0.62 and grip < 0.40):
        return "mud"
    return "soft"


def _resolve_dominant_kind(kinds: list[str]) -> tuple[str, str, bool]:
    """
    Etiqueta de sesion por mayoria de ruedas.

    Returns (terrain_kind, surface_wheel, wheel_disagreement).
    mixed solo si no hay mayoria simple (>50%%).
    """
    if not kinds:
        return "unknown", "", False
    from collections import Counter

    counts = Counter(kinds)
    if len(counts) == 1:
        k = kinds[0]
        return k, k, False
    top, top_n = counts.most_common(1)[0]
    if top_n > len(kinds) / 2:
        return top, top, len(counts) > 1
    return "mixed", "mixed", True


def classify_mud_grade(
    terrain_kind: str,
    grip_avg: float,
    contact_avg: float,
    deform_avg: float,
    *,
    vel_y: float | None = None,
) -> tuple[int, str]:
    """Grado barro/superficie (provisional — calibrar con scan_wheel_substance).

    0 dry_hard | 1 soft_dirt | 2 mud_light | 3 mud_deep | 4 water_ford
    | 5 snow | 6 ice
    """
    kind = (terrain_kind or "").strip().lower()
    if kind == "snow":
        return (5, "snow_loose") if grip_avg < 0.15 else (5, "snow_packed")
    if kind == "ice":
        return 6, "ice"
    if kind == "hard":
        return 0, "dry_hard"
    if kind == "soft":
        return 1, "soft_dirt"
    if kind not in ("mud", "mixed"):
        return 0, "dry_hard"

    vy = vel_y if vel_y is not None else 0.0
    if vy < -0.35 and contact_avg >= 0.48:
        return 4, "water_ford"

    if grip_avg < 0.05 and contact_avg < 0.42:
        return 3, "mud_deep"
    if deform_avg < -0.10 and grip_avg < 0.12:
        return 3, "mud_deep"
    if grip_avg < 0.25 and contact_avg < 0.52:
        return 2, "mud_light"
    if grip_avg < 0.40:
        return 2, "mud_light"
    return 1, "soft_dirt"


def _terrain_grade_fields(
    terrain_kind: str,
    grips: list[float],
    contacts: list[float],
    deforms: list[float],
    *,
    vel_y: float | None = None,
) -> dict[str, str]:
    if not grips:
        return {
            "surface_deform_avg": "",
            "contact_min": "",
            "contact_max": "",
            "mud_grade": "",
            "mud_grade_label": "",
        }
    grip_avg = sum(grips) / len(grips)
    contact_avg = sum(contacts) / len(contacts) if contacts else 0.0
    deform_avg = sum(deforms) / len(deforms) if deforms else 0.0
    grade, label = classify_mud_grade(
        terrain_kind, grip_avg, contact_avg, deform_avg, vel_y=vel_y
    )
    out: dict[str, str] = {
        "mud_grade": str(grade),
        "mud_grade_label": label,
    }
    if deforms:
        out["surface_deform_avg"] = f"{deform_avg:.4f}"
    else:
        out["surface_deform_avg"] = ""
    if contacts:
        out["contact_min"] = f"{min(contacts):.3f}"
        out["contact_max"] = f"{max(contacts):.3f}"
    else:
        out["contact_min"] = ""
        out["contact_max"] = ""
    return out


def classify_terrain_from_wheels(
    grips: list[float],
    surfaces: list[float],
    *,
    deforms: list[float] | None = None,
) -> dict[str, Any]:
    """
    Terreno dominante desde contacto Havok por rueda.

    Por rueda: grip +0x2FC, sustancia efectiva desde +0x2B4 o +0x2EC (Fleetstar).
    No lee el mapa .pak: es lo que el motor resuelve bajo cada rueda en ese instante.
    En tramos mixtos (ruedas en terrenos distintos) devuelve terrain_kind=mixed.
    """
    if not grips:
        return {
            "surface_wheel": "",
            "wheel_grip": "",
            "terrain_kind": "unknown",
            "surface_avg": "",
            "contact_avg": "",
            "grip_min": "",
            "grip_max": "",
            "wheel_kinds": "",
        }

    kinds = [
        _classify_wheel_contact(
            g,
            surfaces[i] if i < len(surfaces) else 0.0,
            deform=(deforms[i] if deforms and i < len(deforms) else None),
        )
        for i, g in enumerate(grips)
    ]
    grip_avg = sum(grips) / len(grips)
    surf_avg = sum(surfaces) / len(surfaces) if surfaces else 0.0
    terrain_kind, surface_wheel, wheel_disagreement = _resolve_dominant_kind(kinds)

    return {
        "surface_wheel": surface_wheel,
        "wheel_grip": f"{grip_avg:.3f}",
        "terrain_kind": terrain_kind,
        "surface_avg": f"{surf_avg:.3f}",
        "contact_avg": "",
        "grip_min": f"{min(grips):.3f}",
        "grip_max": f"{max(grips):.3f}",
        "wheel_kinds": "|".join(kinds),
        "wheel_disagreement": wheel_disagreement,
    }


def classify_surface_wheel(grip_avg: float, surface_avg: float) -> str:
    """Compat: superficie bajo ruedas (media). Preferir classify_terrain_from_wheels."""
    return classify_terrain_from_wheels([grip_avg], [surface_avg])["surface_wheel"]


def read_wheel_terrain(h: int, veh: int, *, vel_y: float | None = None) -> dict[str, Any]:
    """Lectura detallada de contacto por rueda."""
    wheels = read_wheel_pointers(h, veh)
    grips: list[float] = []
    surfaces: list[float] = []
    contacts: list[float] = []
    deforms: list[float] = []
    for w in wheels:
        g = read_f32(h, w + OFF_WHEEL_GRIP)
        sb = read_f32(h, w + OFF_WHEEL_SURFACE)
        ec = read_f32(h, w + OFF_WHEEL_CONTACT)
        if g is not None:
            grips.append(g)
        if sb is not None:
            deforms.append(sb)
        if sb is not None and ec is not None:
            surfaces.append(_effective_surface(sb, ec))
            contacts.append(ec)
        elif sb is not None:
            surfaces.append(sb)
        elif ec is not None:
            surfaces.append(ec)
            contacts.append(ec)
    result = classify_terrain_from_wheels(grips, surfaces, deforms=deforms or None)
    if contacts:
        result["contact_avg"] = f"{sum(contacts) / len(contacts):.3f}"
    result.update(
        _terrain_grade_fields(
            result.get("terrain_kind", ""),
            grips,
            contacts,
            deforms,
            vel_y=vel_y,
        )
    )
    return result


def read_wheel_surface(h: int, veh: int) -> tuple[str, str]:
    """Devuelve (surface_wheel, wheel_grip_str). Vacio si no hay ruedas."""
    data = read_wheel_terrain(h, veh)
    return data.get("surface_wheel", ""), data.get("wheel_grip", "")


def _vehicle_world_xz(h: int, veh: int) -> tuple[float, float] | None:
    rb = read_u64(h, veh + OFF_RB)
    if not rb or rb < 0x10000:
        return None
    px = read_f32(h, rb + OFF_POS_X)
    pz = read_f32(h, rb + OFF_POS_Z)
    if px is None or pz is None:
        return None
    return px, pz


def _distance_xz(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _id_looks_like_trailer(game_id: str) -> bool:
    low = game_id.lower()
    return any(tok in low for tok in TRAILER_ID_TOKENS)


def _id_looks_like_cargo(game_id: str) -> bool:
    low = game_id.lower()
    if any(tok in low for tok in _LOAD_IGNORE_ID_TOKENS):
        return False
    if any(tok in low for tok in TRAILER_ID_TOKENS):
        return False
    if low.startswith("cargo_"):
        return True
    return any(tok in low for tok in CARGO_ID_TOKENS)


def _is_ascii_game_id(s: str) -> bool:
    if not s or len(s) > 63:
        return False
    return all(c.isascii() and (c.isalnum() or c in "_-") for c in s)


def _read_named_string(h: int, addr: int, str_off: int) -> str:
    """Lee string inline o via puntero en addr+str_off."""
    inline = read_cstring(h, addr + str_off)
    if _is_ascii_game_id(inline):
        return inline
    ptr = read_u64(h, addr + str_off)
    if ptr and 0x10000 < ptr < 0x7FFFFFFFFFFF:
        via = read_cstring(h, ptr)
        if _is_ascii_game_id(via):
            return via
    return ""


def _bone_cargo_label(h: int, slot: int) -> str:
    """BoneCargo_N_cdt en slot empaquetado (inline +0 o puntero +0/+70)."""
    if not slot or slot < 0x10000:
        return ""
    for str_off in (0x000, 0x070, 0x008, 0x010, 0x078):
        label = _read_named_string(h, slot, str_off)
        if label.startswith("BoneCargo_") and label.endswith("_cdt"):
            return label
    return ""


def _scan_frame_addon_name(h: int, root: int, *, max_nodes: int = 400) -> str:
    seen: set[int] = set()
    stack = [root]
    while stack and len(seen) < max_nodes:
        addr = stack.pop()
        if addr in seen or not addr or addr < 0x10000:
            continue
        seen.add(addr)
        for off in range(0, 0x180, 8):
            ptr = read_u64(h, addr + off)
            for src in (addr + off, ptr or 0):
                if not src or src < 0x10000:
                    continue
                name = read_cstring(h, src)
                if not name or len(name) > 80:
                    continue
                low = name.lower()
                if "frame_addon_sideboard" in low or name == "trucks_addons_frame_addon_sideboard_2":
                    return name
            if ptr and 0x10000 < ptr < 0x7FFFFFFFFFFF and ptr not in seen:
                stack.append(ptr)
    return ""


def _scan_bone_cargo_labels(h: int, root: int, *, max_nodes: int = 600) -> list[str]:
    seen: set[int] = set()
    stack = [root]
    found: set[str] = set()
    while stack and len(seen) < max_nodes:
        addr = stack.pop()
        if addr in seen or not addr or addr < 0x10000:
            continue
        seen.add(addr)
        for off in range(0, 0x180, 8):
            ptr = read_u64(h, addr + off)
            for src in (addr + off, ptr or 0):
                if not src or src < 0x10000:
                    continue
                bone = read_cstring(h, src)
                if bone and bone.startswith("BoneCargo_") and bone.endswith("_cdt"):
                    found.add(bone)
            if ptr and 0x10000 < ptr < 0x7FFFFFFFFFFF and ptr not in seen:
                stack.append(ptr)
    return sorted(found)


def _bone_cargo_from_sub(h: int, sub: int) -> list[str]:
    bones: list[str] = []
    for slot_off in (0x090, 0x0E8, 0x140, 0x198, 0x1F0, 0x048, 0x0A0):
        slot = read_u64(h, sub + slot_off)
        if not slot or slot < 0x10000:
            continue
        name = _bone_cargo_label(h, slot)
        if name:
            bones.append(name)
    bones.extend(_scan_bone_cargo_labels(h, sub))
    return bones


def _scan_load_registry_cargo_types(h: int, veh: int, *, max_nodes: int = 96) -> list[str]:
    root = read_u64(h, veh + OFF_LOAD_REGISTRY)
    if not root:
        return []
    seen: set[int] = set()
    stack = [root]
    found: list[str] = []

    def _push(addr: int) -> None:
        if addr and 0x10000 < addr < 0x7FFFFFFFFFFF and addr not in seen:
            stack.append(addr)

    while stack and len(seen) < max_nodes:
        addr = stack.pop()
        if addr in seen:
            continue
        seen.add(addr)
        name = _read_named_string(h, addr, OFF_CARGO_ENTRY_TYPE)
        if name.startswith("cargo_") and ".xml" not in name and "\\" not in name:
            if name not in found:
                found.append(name)
        for off in range(0, 0x1A0, 8):
            _push(read_u64(h, addr + off) or 0)
    return found


def _iter_island_rigid_bodies(h: int, veh: int) -> list[int]:
    """Piezas Havok del camión (chasis, ruedas, carga empaquetada) vía simulation island."""
    rb = read_u64(h, veh + OFF_RB)
    if not rb:
        return []
    island = read_u64(h, rb + OFF_SIM_ISLAND)
    if not island:
        return []
    begin = read_u64(h, island + OFF_ISLAND_BODIES)
    if not begin:
        return []
    count = read_u32(h, island + OFF_ISLAND_COUNT)
    if count is None or count <= 0 or count > 64:
        end = read_u64(h, island + OFF_ISLAND_COUNT)
        if not end or end <= begin:
            return []
        count = (end - begin) // 8
    if count <= 0 or count > 64:
        return []
    bodies: list[int] = []
    for i in range(count):
        p = read_u64(h, begin + i * 8)
        if p and p > 0x10000:
            bodies.append(p)
    return bodies


def _cargo_mass_from_island(
    h: int,
    veh: int,
    *,
    truck_ref: float | None,
    veh_rb: int,
) -> float:
    """Suma masas de cuerpos de carga en el simulation island (estable en marcha)."""
    bodies = _iter_island_rigid_bodies(h, veh)
    if not bodies:
        return 0.0
    ref = truck_ref or 0.0
    total = 0.0
    for body in bodies:
        if body == veh_rb:
            continue
        mass = read_body_mass_kg(h, body)
        if mass is None or mass < _ISLAND_CARGO_MASS_MIN_KG or mass > 15_000:
            continue
        if ref and abs(mass - ref) < 500:
            continue
        total += mass
    return total


def _apply_load_latch(veh: int, result: dict[str, Any]) -> dict[str, Any]:
    """Mantiene cargado entre lecturas cuando Havok solo expone slots/masa un frame."""
    slot = int(result.get("packed_cargo_slots") or 0)
    path = (result.get("path_cargo_type") or "").strip()
    bones = (result.get("packed_cargo_bones") or "").strip()
    attached = 0.0
    raw_att = (result.get("attached_cargo_mass_kg") or "").strip()
    if raw_att:
        try:
            attached = float(raw_att)
        except ValueError:
            attached = 0.0
    cargo = 0.0
    try:
        cargo = float(result.get("cargo_mass_kg") or 0)
    except (TypeError, ValueError):
        cargo = 0.0
    hint = (result.get("load_hint") or "vacio").strip()
    trailer = (result.get("trailer_id") or "").strip()

    loaded_now = (
        hint in ("cargado", "trailer_cargado")
        or slot > 0
        or bool(path)
        or bool(bones)
        or attached > PAYLOAD_LOAD_THRESHOLD_KG
        or cargo > PAYLOAD_LOAD_THRESHOLD_KG
    )

    state = _VEH_LOAD_LATCH.get(veh, {})
    if loaded_now:
        state = {
            "hint": hint if trailer else "cargado",
            "cargo_kg": max(cargo, attached, float(state.get("cargo_kg") or 0)),
            "slots": max(slot, int(state.get("slots") or 0)),
            "path": path or state.get("path") or "",
            "bones": bones or state.get("bones") or "",
            "frame": result.get("frame_addon") or state.get("frame") or "",
            "miss": 0,
        }
        _VEH_LOAD_LATCH[veh] = state
        return result

    if state.get("hint") != "cargado" or trailer:
        return result

    miss = int(state.get("miss") or 0) + 1
    state["miss"] = miss
    if miss > _LOAD_LATCH_MAX_MISS:
        _VEH_LOAD_LATCH.pop(veh, None)
        return result

    _VEH_LOAD_LATCH[veh] = state
    out = dict(result)
    out["load_hint"] = "cargado"
    latched_kg = max(float(state.get("cargo_kg") or 0), DEFAULT_PACKED_SLOT_KG)
    if latched_kg > float(out.get("cargo_mass_kg") or 0):
        out["cargo_mass_kg"] = f"{latched_kg:.0f}"
    slots = int(state.get("slots") or 0)
    if slots and not (out.get("packed_cargo_slots") or "").strip():
        out["packed_cargo_slots"] = str(slots)
    if state.get("path") and not (out.get("path_cargo_type") or "").strip():
        out["path_cargo_type"] = state["path"]
    if state.get("bones") and not (out.get("packed_cargo_bones") or "").strip():
        out["packed_cargo_bones"] = state["bones"]
    if state.get("frame") and not (out.get("frame_addon") or "").strip():
        out["frame_addon"] = state["frame"]
    empty_raw = (out.get("empty_mass_kg") or "").strip()
    if empty_raw and latched_kg > 0:
        try:
            empty = float(empty_raw)
            total = max(float(out.get("total_mass_kg") or 0), empty + latched_kg)
            out["total_mass_kg"] = f"{total:.0f}"
            out["mass_estimated"] = True
        except ValueError:
            pass
    return out


def _packed_cargo_from_attach(h: int, veh: int) -> tuple[int, list[str], str]:
    """
    Carga empaquetada en addon de bastidor (p. ej. plataforma lateral).

    attach+078 -> varios +030; si sub es null en marcha, escaneo strings en addon/attach.
    """
    bones: set[str] = set()
    frame_addon = ""
    attach = read_u64(h, veh + OFF_ATTACH_MANAGER)
    addon = read_u64(h, veh + OFF_ADDON)

    if attach:
        frame_addon = _scan_frame_addon_name(h, attach)
        for sub_off in _ATTACH_CARGO_SUB_OFFS:
            sub = read_u64(h, attach + sub_off)
            if not sub:
                continue
            for name in _bone_cargo_from_sub(h, sub):
                bones.add(name)
        for name in _scan_bone_cargo_labels(h, attach):
            bones.add(name)

    if addon:
        if not frame_addon:
            frame_addon = _scan_frame_addon_name(h, addon)
        for name in _scan_bone_cargo_labels(h, addon):
            bones.add(name)

    bone_list = sorted(bones)
    return len(bone_list), bone_list, frame_addon


def _cargo_mass_from_physics_ptrs(
    h: int,
    ptrs: list[int],
    *,
    my_id: str,
    veh_addr: int,
    truck_mass: float | None,
) -> float:
    """Suma masa Havok de piezas de carga en un vector de punteros (addons/carga)."""
    total = 0.0
    truck_ref = truck_mass or 0.0
    seen: set[int] = {veh_addr}
    for ptr in ptrs:
        if ptr in seen:
            continue
        seen.add(ptr)
        game_id = read_vehicle_id(h, ptr)
        if game_id == my_id:
            continue
        if game_id and _id_looks_like_trailer(game_id):
            continue
        if game_id and any(tok in game_id.lower() for tok in _LOAD_IGNORE_ID_TOKENS):
            continue
        low = (game_id or "").lower()
        if "wheel" in low or "tire" in low or "suspension" in low:
            continue
        mass = read_body_mass_kg(h, ptr)
        if mass is None or mass < 150 or mass > 15_000:
            continue
        if truck_ref and abs(mass - truck_ref) < 80:
            continue
        is_cargo = bool(game_id and _id_looks_like_cargo(game_id))
        if not is_cargo and game_id and game_id.startswith("s_"):
            continue
        if is_cargo or (not game_id and 400 <= mass <= 8000) or (
            game_id and 400 <= mass <= 8000 and "addon" not in low
        ):
            total += mass
    return total


def _cargo_mass_from_addon_physics(
    h: int,
    veh: int,
    *,
    my_id: str,
    truck_mass: float | None,
) -> float:
    """Carga en bastidor: vector Master Addons Physics [VehObj+1E0..+1E8]."""
    begin = read_u64(h, veh + OFF_ADDON_PHYS_BEGIN)
    end = read_u64(h, veh + OFF_ADDON_PHYS_END)
    ptrs = _iter_ptr_vector(h, begin, end, max_count=24)
    return _cargo_mass_from_physics_ptrs(
        h, ptrs, my_id=my_id, veh_addr=veh, truck_mass=truck_mass
    )


def _cargo_type_on_load_path(h: int, veh: int) -> str:
    """
    Tipo de carga empaquetada en registro runtime (veh+060).

    Prueba varias cadenas de punteros (Fleetstar sideboard, build jun-2026).
    """
    root = read_u64(h, veh + OFF_LOAD_REGISTRY)
    if not root:
        return ""
    for chain in _LOAD_REGISTRY_CHAINS:
        node: int | None = root
        for off in chain:
            node = read_u64(h, node + off) if node else None
            if not node:
                break
        if not node:
            continue
        name = _read_named_string(h, node, OFF_CARGO_ENTRY_TYPE)
        if name.startswith("cargo_") and ".xml" not in name and "\\" not in name:
            return name
    return ""


def _effective_packed_slots(packed_slots: int, packed_bones: list[str]) -> int:
    """Slots BoneCargo activos (punteros directos o labels encontrados en DFS)."""
    if packed_slots > 0:
        return packed_slots
    return len(packed_bones)


def read_body_mass_kg(h: int, body_addr: int) -> float | None:
    """Masa Havok (kg) desde objeto con rigid body en +0x5D0."""
    rb = read_u64(h, body_addr + OFF_RB)
    if not rb or rb < 0x10000:
        return None
    motion = read_u64(h, rb + OFF_RB_MOTION_PTR)
    if not motion or motion < 0x10000:
        return None
    inv = read_f32(h, motion + OFF_MOTION_INV_MASS)
    if inv is None or abs(inv) < 1e-7 or abs(inv) > 0.05:
        return None
    mass = 1.0 / inv
    if mass < 200 or mass > 200_000:
        return None
    return mass


def read_total_mass_kg(h: int, veh: int) -> float | None:
    """Masa total del camion en Havok (kg)."""
    return read_body_mass_kg(h, veh)


def payload_from_masses(
    truck_mass_kg: float,
    empty_mass_kg: float,
    *,
    trailer_mass_kg: float | None = None,
    trailer_tare_kg: float = 0.0,
    tare_kg: float = PAYLOAD_TARE_KG,
) -> dict[str, float]:
    """Carga util (kg) = masa Havok - masa vacia XML/sim - tara operativa."""
    truck_raw = max(0.0, truck_mass_kg - empty_mass_kg)
    truck_payload = max(0.0, truck_raw - tare_kg)
    trailer_payload = 0.0
    if trailer_mass_kg is not None and trailer_tare_kg > 0:
        trailer_payload = max(0.0, trailer_mass_kg - trailer_tare_kg - TRAILER_PAYLOAD_TARE_KG)
    return {
        "payload_kg": truck_payload + trailer_payload,
        "truck_payload_kg": truck_payload,
        "trailer_payload_kg": trailer_payload,
    }


def _ensure_project_root_on_path() -> None:
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)


def _lookup_empty_mass_kg(game_id: str) -> float | None:
    _ensure_project_root_on_path()
    try:
        from camiones.registry import empty_mass_kg, vehicle_id_from_ce

        value = empty_mass_kg(vehicle_id_from_ce(game_id))
        if value is not None:
            return value
    except ImportError:
        pass
    return _FALLBACK_EMPTY_MASS_KG.get(game_id)


def _lookup_trailer_tare_kg(trailer_id: str) -> float:
    _ensure_project_root_on_path()
    try:
        from camiones.registry import trailer_tare_kg

        return trailer_tare_kg(trailer_id)
    except ImportError:
        low = trailer_id.lower()
        if "semi" in low or "sideboard" in low:
            return 2500.0
        if "scout" in low:
            return 800.0
        return 1500.0


def _attached_cargo_mass_kg(
    h: int,
    graph: list[tuple[str, str, int]],
    *,
    my_id: str,
    veh_addr: int,
    trailer_addr: int,
    truck_mass: float | None,
) -> float:
    """Suma masas Havok de piezas de carga (cuerpos separados del chasis)."""
    total = 0.0
    used: set[int] = {veh_addr, trailer_addr}
    truck_ref = truck_mass or 0.0
    for _path, game_id, addr in graph:
        if addr in used or game_id == my_id:
            continue
        if _id_looks_like_trailer(game_id):
            continue
        if any(tok in game_id.lower() for tok in _LOAD_IGNORE_ID_TOKENS):
            continue
        low = game_id.lower()
        if "wheel" in low or "tire" in low or "suspension" in low:
            continue
        mass = read_body_mass_kg(h, addr)
        if mass is None or mass < 150 or mass > 15_000:
            continue
        if truck_ref and abs(mass - truck_ref) < 80:
            continue
        if _id_looks_like_cargo(game_id) or (400 <= mass <= 8000 and "+048" in _path):
            total += mass
            used.add(addr)
    return total


def _estimate_cargo_mass_kg(cargo_ids: list[str]) -> float:
    """Masa aproximada desde nombres de instancia Havok (catalogo sim)."""
    total = 0.0
    for cid in cargo_ids:
        low = cid.lower()
        if "metal_plank" in low or "metal_planks" in low:
            total += 2500
        elif "brick" in low:
            total += 1000
        elif "metal_roll" in low:
            total += 1000
        elif "spare_parts_special" in low or "service_spare_parts_special" in low:
            total += 1200
        elif "spare" in low or "service_spare" in low:
            total += 1200
        elif "concrete" in low:
            total += 3000
        elif "container" in low:
            total += 1500
        elif "pipe" in low:
            total += 2250
        elif "wood" in low or "plank" in low:
            total += 500
        elif "log" in low:
            total += 1000
        else:
            total += 800
    return total


def _is_sane_truck_mass(mass: float | None, empty_mass: float | None) -> bool:
    """Filtra masas Havok corruptas (punteros leidos como kg)."""
    if mass is None or empty_mass is None:
        return False
    if mass < empty_mass * 0.92:
        return False
    if mass > empty_mass + MAX_FRAME_PAYLOAD_KG + 800:
        return False
    return True


def _frame_payload_from_packed(packed_slots: int, path_cargo_type: str) -> float:
    """Carga util en bastidor desde slots BoneCargo o tipo en load registry."""
    if packed_slots <= 0 and not path_cargo_type:
        return 0.0
    slots = packed_slots if packed_slots > 0 else 1
    per_slot = (
        _estimate_cargo_mass_kg([path_cargo_type])
        if path_cargo_type
        else DEFAULT_PACKED_SLOT_KG
    )
    return min(slots * per_slot, MAX_FRAME_PAYLOAD_KG)


def _payload_from_cargo_ids(cargo_ids: list[str]) -> float:
    """Estima carga desde IDs del grafo; ignora placeholders y acota el total."""
    filtered = [
        cid
        for cid in cargo_ids
        if not cid.startswith("packed_slots_x") and _id_looks_like_cargo(cid)
    ]
    if not filtered:
        return 0.0
    return min(_estimate_cargo_mass_kg(filtered), MAX_FRAME_PAYLOAD_KG)


def _truck_payload_signal(
    *,
    trailer_id: str,
    truck_payload_kg: float,
    frame_payload_kg: float,
    path_cargo_type: str,
    packed_slots: int,
) -> float:
    """Senal de carga util en camion (sin remolque) para load_hint."""
    signal = truck_payload_kg
    if not trailer_id:
        if frame_payload_kg > 0:
            signal = max(signal, frame_payload_kg)
        elif packed_slots > 0 or path_cargo_type:
            signal = max(signal, PAYLOAD_LOAD_THRESHOLD_KG + 1.0)
    return signal


def _load_hint_from_payload(
    *,
    trailer_id: str,
    truck_payload_kg: float,
    trailer_payload_kg: float,
    threshold_kg: float = PAYLOAD_LOAD_THRESHOLD_KG,
) -> str:
    if trailer_id:
        if truck_payload_kg > threshold_kg or trailer_payload_kg > threshold_kg:
            return "trailer_cargado"
        return "trailer_vacio"
    if truck_payload_kg > threshold_kg:
        return "cargado"
    return "vacio"


def _walk_vehicle_graph(
    h: int,
    roots: list[tuple[int, str]],
    *,
    max_depth: int = 3,
) -> list[tuple[str, str, int]]:
    """Recorre punteros desde raices. Devuelve (path, game_id, addr)."""
    seen: set[int] = set()
    hits: list[tuple[str, str, int]] = []

    def visit(addr: int, path: str, depth: int) -> None:
        if depth > max_depth or addr in seen or not addr or addr < 0x10000:
            return
        seen.add(addr)
        game_id = read_vehicle_id(h, addr)
        if game_id.startswith("s_"):
            hits.append((path, game_id, addr))
        limit = 0x380 if depth == 0 else 0x1A0
        for off in range(0, limit, 8):
            child = read_u64(h, addr + off)
            if child and 0x10000 < child < 0x7FFFFFFFFFFF and child not in seen:
                visit(child, f"{path}+{off:03X}", depth + 1)

    for root, label in roots:
        if root:
            visit(root, label, 0)
    return hits


_TIRE_KIND_PRIORITY = ("chain", "mudtires", "offroad", "allterrain", "uhd", "highway")


def _id_looks_like_wheel_addon(game_id: str, vehicle_id: str = "") -> bool:
    """Instancia Havok de neumatico/rueda montada (no chasis ni carga)."""
    if not game_id or game_id == vehicle_id:
        return False
    if _id_looks_like_trailer(game_id) or _id_looks_like_cargo(game_id):
        return False
    low = game_id.lower()
    if not low.startswith("s_"):
        return False
    if "suspension" in low or "engine" in low or "gearbox" in low:
        return False
    if "wheel" in low or "tire" in low:
        return True
    tire_tokens = ("offroad", "allterrain", "highway", "mudtire", "mud_tire", "chain", "uhd")
    if "scout" in low and any(tok in low for tok in tire_tokens):
        return True
    if any(tok in low for tok in tire_tokens):
        if any(tok in low for tok in ("medium", "heavy", "superheavy", "double", "single", "scout")):
            return True
    return False


def classify_tire_kind(game_id: str) -> str:
    """Clave sim (offroad, highway, allterrain, mudtires, chain, uhd)."""
    low = (game_id or "").lower()
    if "chain" in low:
        return "chain"
    if "mudtire" in low or "mud_tire" in low:
        return "mudtires"
    if "offroad" in low:
        return "offroad"
    if "allterrain" in low or "all_terrain" in low:
        return "allterrain"
    if "uhd" in low:
        return "uhd"
    if "highway" in low:
        return "highway"
    return "unknown"


def _string_looks_like_wheel_label(name: str) -> bool:
    if not name or len(name) > 80:
        return False
    low = name.lower()
    if low.startswith("wheels_"):
        return True
    if low.startswith("s_") and _id_looks_like_wheel_addon(name):
        return True
    if any(low.startswith(p) for p in ("offroad_", "highway_", "allterrain_", "mudtires_")):
        return True
    if low.startswith("wheels_"):
        return True
    return False


_WHEEL_UI_MARKERS: tuple[tuple[str, str], ...] = (
    ("OS I", "offroad"),
    ("OS II", "offroad"),
    ("AT I", "allterrain"),
    ("AT II", "allterrain"),
    ("UHD", "uhd"),
    ("MUD", "mudtires"),
    ("CHAIN", "chain"),
    ("HIGHWAY", "highway"),
    ("MS I", "highway"),
)


def _tire_kind_from_ui_text(text: str) -> str:
    upper = (text or "").upper()
    for marker, kind in _WHEEL_UI_MARKERS:
        if marker in upper:
            return kind
    return "unknown"


def _normalize_wheel_type_xml(raw: str) -> str:
    if raw.startswith("heels_"):
        return "w" + raw
    return raw


def _read_wheel_type_xml(h: int, wheel: int) -> str:
    """Tipo de rueda XML en TRUCK_WHEEL_MODEL (p. ej. wheels_scout2 @ ~+13F)."""
    for off in (OFF_WHEEL_TYPE_XML, OFF_WHEEL_TYPE_XML - 1, OFF_WHEEL_TYPE_XML - 2):
        inline = read_cstring(h, wheel + off, max_len=64)
        if inline.startswith("wheels_"):
            return inline.split("\x00", 1)[0]
        if inline.startswith("heels_"):
            return _normalize_wheel_type_xml(inline.split("\x00", 1)[0])
    ptr = read_u64(h, wheel + OFF_WHEEL_TYPE_XML)
    if ptr and 0x10000 < ptr < 0x7FFFFFFFFFFF:
        via = read_cstring(h, ptr, max_len=64)
        if via.startswith("wheels_"):
            return via.split("\x00", 1)[0]
    blob = read_bytes(
        h,
        wheel + OFF_WHEEL_TYPE_SCAN_START,
        OFF_WHEEL_TYPE_SCAN_END - OFF_WHEEL_TYPE_SCAN_START,
    )
    if blob:
        match = re.search(rb"wheels_[a-z0-9_]+", blob)
        if not match:
            match = re.search(rb"heels_[a-z0-9_]+", blob)
        if match:
            return _normalize_wheel_type_xml(match.group(0).decode("ascii", errors="ignore"))
    return ""


def _read_wheel_model_tire_info(h: int, wheel: int) -> dict[str, str]:
    """Lee tipo XML y pista de neumatico desde TRUCK_WHEEL_MODEL."""
    wheel_type = _read_wheel_type_xml(h, wheel)
    label_raw = read_cstring(h, wheel + OFF_WHEEL_LABEL, max_len=48).strip()
    blob = read_bytes(
        h,
        wheel + OFF_WHEEL_TYPE_SCAN_START,
        OFF_WHEEL_TYPE_SCAN_END - OFF_WHEEL_TYPE_SCAN_START,
    )
    scan_text = ""
    if blob:
        scan_text = blob.decode("latin-1", errors="ignore")
    tire_kind = _tire_kind_from_ui_text(f"{label_raw} {scan_text}")
    if tire_kind == "unknown" and wheel_type:
        tire_kind = classify_tire_kind(wheel_type)
    return {
        "wheel_type_xml": wheel_type,
        "label_raw": label_raw,
        "tire_kind_hint": tire_kind,
    }


def _collect_wheel_model_hits(h: int, veh: int) -> list[dict[str, Any]]:
    """Neumatico desde TRUCK_WHEEL_MODEL [veh+200] — fuente principal scouts jun-2026."""
    hits: list[dict[str, Any]] = []
    for i, wheel in enumerate(read_wheel_pointers(h, veh)):
        info = _read_wheel_model_tire_info(h, wheel)
        wheel_type = info.get("wheel_type_xml") or ""
        label = info.get("label_raw") or ""
        kind = info.get("tire_kind_hint") or "unknown"
        if wheel_type:
            hits.append(
                {
                    "game_id": wheel_type,
                    "tire_kind": kind if kind != "unknown" else classify_tire_kind(wheel_type),
                    "source": f"wheel_model:{i}",
                    "addr": hex(wheel),
                    "label_raw": label,
                    "wheel_type_xml": wheel_type,
                }
            )
        elif kind != "unknown":
            hits.append(
                {
                    "game_id": label or f"wheel_ui_marker_{kind}",
                    "tire_kind": kind,
                    "source": f"wheel_model:{i}",
                    "addr": hex(wheel),
                    "label_raw": label,
                }
            )
    return hits


def _scan_wheel_addon_strings(h: int, root: int, *, max_nodes: int = 500) -> list[str]:
    """Busca etiquetas de neumatico/rueda en arbol addon/attach."""
    seen: set[int] = set()
    stack = [root]
    found: set[str] = set()
    while stack and len(seen) < max_nodes:
        addr = stack.pop()
        if addr in seen or not addr or addr < 0x10000:
            continue
        seen.add(addr)
        for off in range(0, 0x180, 8):
            ptr = read_u64(h, addr + off)
            for src in (addr + off, ptr or 0):
                if not src or src < 0x10000:
                    continue
                label = read_cstring(h, src, max_len=80)
                if _string_looks_like_wheel_label(label):
                    found.add(label)
            if ptr and 0x10000 < ptr < 0x7FFFFFFFFFFF and ptr not in seen:
                stack.append(ptr)
    return sorted(found)


def _collect_wheel_addon_hits(h: int, veh: int, vehicle_id: str) -> list[dict[str, Any]]:
    """IDs de neumatico desde grafo, vector addons y simulation island."""
    hits: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def add(game_id: str, source: str, addr: int = 0) -> None:
        gid = (game_id or "").strip()
        if not gid or gid in seen_ids:
            return
        if not (
            _id_looks_like_wheel_addon(gid, vehicle_id)
            or _string_looks_like_wheel_label(gid)
        ):
            return
        seen_ids.add(gid)
        hits.append(
            {
                "game_id": gid,
                "tire_kind": classify_tire_kind(gid),
                "source": source,
                "addr": hex(addr) if addr else "",
            }
        )

    roots: list[tuple[int, str]] = [(veh, "veh")]
    addon = read_u64(h, veh + OFF_ADDON)
    if addon:
        roots.append((addon, "addon"))
    attach = read_u64(h, veh + OFF_ATTACH_MANAGER)
    if attach:
        roots.append((attach, "attach"))

    for path, game_id, addr in _walk_vehicle_graph(h, roots):
        add(game_id, f"graph:{path}", addr)

    begin = read_u64(h, veh + OFF_ADDON_PHYS_BEGIN)
    end = read_u64(h, veh + OFF_ADDON_PHYS_END)
    for ptr in _iter_ptr_vector(h, begin, end, max_count=32):
        add(read_vehicle_id(h, ptr), "addon_phys", ptr)

    for body in _iter_island_rigid_bodies(h, veh):
        add(read_vehicle_id(h, body), "island", body)

    for label, root in (("addon", addon), ("attach", attach)):
        if not root:
            continue
        for label_str in _scan_wheel_addon_strings(h, root):
            add(label_str, f"strings:{label}")

    return hits


def _consensus_tire_kind(hits: list[dict[str, Any]]) -> tuple[str, bool]:
    from collections import Counter

    kinds = [h["tire_kind"] for h in hits if h.get("tire_kind") and h["tire_kind"] != "unknown"]
    if not kinds:
        return "unknown", False
    counts = Counter(kinds)
    top, top_n = counts.most_common(1)[0]
    if len(counts) == 1:
        return top, False
    if top_n > len(kinds) / 2:
        return top, len(counts) > 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], _TIRE_KIND_PRIORITY.index(kv[0]) if kv[0] in _TIRE_KIND_PRIORITY else 99))
    return ordered[0][0], True


def read_mounted_tires(h: int, veh: int) -> dict[str, Any]:
    """Neumaticos montados en runtime (lectura CE, no protocolo de grabacion)."""
    vehicle_id = read_vehicle_id(h, veh)
    wheel_ptrs = read_wheel_pointers(h, veh)
    hits = _collect_wheel_model_hits(h, veh)
    if not hits:
        hits = _collect_wheel_addon_hits(h, veh, vehicle_id)
    else:
        hits.extend(_collect_wheel_addon_hits(h, veh, vehicle_id))
    tire_kind, mixed = _consensus_tire_kind(hits)
    game_ids: list[str] = []
    for row in hits:
        gid = row.get("game_id") or ""
        if gid and gid not in game_ids:
            game_ids.append(gid)
    wheel_types = [
        h.get("wheel_type_xml") or h.get("game_id", "")
        for h in hits
        if str(h.get("source", "")).startswith("wheel_model")
        and str(h.get("wheel_type_xml") or h.get("game_id", "")).startswith("wheels_")
    ]
    wheel_type_xml = wheel_types[0] if wheel_types else ""
    labels = [h.get("label_raw", "") for h in hits if h.get("label_raw")]
    return {
        "vehicle_id": vehicle_id,
        "wheel_count": len(wheel_ptrs),
        "wheel_type_xml": wheel_type_xml,
        "tire_label_raw": labels[0] if labels else "",
        "tire_kind": tire_kind,
        "tire_mixed": mixed,
        "tire_game_ids": game_ids,
        "tire_hits": hits,
    }


def read_vehicle_load(h: int, veh: int) -> dict[str, Any]:
    """
    Estado de carga en runtime (experimental).

    - Remolque: otro vehiculo Havok con rigid body a <=22 m del camion.
    - Carga en bastidor: slots BoneCargo_* bajo attach+030 (sideboard / plataforma).
    - Carga por grafo: instancias s_* / cargo_* enlazadas al vehiculo.
    """
    my_id = read_vehicle_id(h, veh)
    origin = _vehicle_world_xz(h, veh)
    roots: list[tuple[int, str]] = [(veh, "veh")]
    addon = read_u64(h, veh + OFF_ADDON)
    if addon:
        roots.append((addon, "addon"))
    attach = read_u64(h, veh + OFF_ATTACH_MANAGER)
    if attach:
        roots.append((attach, "attach"))

    graph = _walk_vehicle_graph(h, roots)
    trailer_id = ""
    trailer_addr = 0
    trailer_dist = 999.0
    cargo_ids: list[str] = []

    for path, game_id, addr in graph:
        if game_id == my_id:
            continue
        if "+1E8" in path:
            continue
        if _id_looks_like_trailer(game_id) and origin:
            other = _vehicle_world_xz(h, addr)
            if other:
                dist = _distance_xz(origin, other)
                if dist <= 22.0 and dist < trailer_dist:
                    trailer_id = game_id
                    trailer_addr = addr
                    trailer_dist = dist
        if _id_looks_like_cargo(game_id) and game_id not in cargo_ids:
            cargo_ids.append(game_id)

    packed_slots, packed_bones, frame_addon = _packed_cargo_from_attach(h, veh)
    slot_count = _effective_packed_slots(packed_slots, packed_bones)
    path_types = _scan_load_registry_cargo_types(h, veh)
    path_cargo_type = path_types[0] if path_types else _cargo_type_on_load_path(h, veh)
    if path_cargo_type and path_cargo_type not in cargo_ids:
        cargo_ids.append(path_cargo_type)
    for extra_type in path_types[1:]:
        if extra_type not in cargo_ids:
            cargo_ids.append(extra_type)
    if slot_count and not path_cargo_type:
        cargo_ids.append(f"packed_slots_x{slot_count}")

    truck_mass = read_total_mass_kg(h, veh)
    empty_mass = _lookup_empty_mass_kg(my_id)
    sane_truck_mass = (
        truck_mass if _is_sane_truck_mass(truck_mass, empty_mass) else None
    )
    truck_ref = sane_truck_mass if sane_truck_mass is not None else truck_mass
    veh_rb = read_u64(h, veh + OFF_RB) or 0
    attached_cargo = 0.0
    if truck_ref is not None:
        attached_cargo = _attached_cargo_mass_kg(
            h,
            graph,
            my_id=my_id,
            veh_addr=veh,
            trailer_addr=trailer_addr,
            truck_mass=truck_ref,
        )
        attached_cargo = max(
            attached_cargo,
            _cargo_mass_from_addon_physics(
                h, veh, my_id=my_id, truck_mass=truck_ref
            ),
            _cargo_mass_from_island(
                h, veh, truck_ref=truck_ref, veh_rb=veh_rb
            ),
        )
    effective_truck_mass = (sane_truck_mass or 0.0) + attached_cargo
    trailer_mass = read_body_mass_kg(h, trailer_addr) if trailer_addr else None
    trailer_tare = _lookup_trailer_tare_kg(trailer_id) if trailer_id else 0.0

    if sane_truck_mass is not None and empty_mass is not None:
        masses = payload_from_masses(
            effective_truck_mass,
            empty_mass,
            trailer_mass_kg=trailer_mass,
            trailer_tare_kg=trailer_tare,
        )
        payload_kg = masses["payload_kg"]
        truck_payload_kg = masses["truck_payload_kg"]
        trailer_payload_kg = masses["trailer_payload_kg"]
    else:
        payload_kg = 0.0
        truck_payload_kg = 0.0
        trailer_payload_kg = 0.0

    frame_payload_kg = _frame_payload_from_packed(slot_count, path_cargo_type)
    if slot_count > 0 and frame_payload_kg <= 0:
        frame_payload_kg = min(
            slot_count * DEFAULT_PACKED_SLOT_KG, MAX_FRAME_PAYLOAD_KG
        )
    if frame_addon and slot_count > 0 and frame_payload_kg <= 0:
        frame_payload_kg = min(
            slot_count * DEFAULT_PACKED_SLOT_KG, MAX_FRAME_PAYLOAD_KG
        )
    graph_payload_kg = _payload_from_cargo_ids(cargo_ids) if not trailer_id else 0.0
    if attached_cargo > PAYLOAD_LOAD_THRESHOLD_KG:
        truck_payload_kg = max(truck_payload_kg, attached_cargo)
    effective_payload = min(
        max(payload_kg, truck_payload_kg, frame_payload_kg, graph_payload_kg),
        MAX_FRAME_PAYLOAD_KG + trailer_payload_kg,
    )
    hint_truck = _truck_payload_signal(
        trailer_id=trailer_id,
        truck_payload_kg=truck_payload_kg,
        frame_payload_kg=frame_payload_kg,
        path_cargo_type=path_cargo_type,
        packed_slots=slot_count,
    )
    hint_trailer = trailer_payload_kg
    if trailer_id and graph_payload_kg > 0:
        hint_trailer = max(hint_trailer, graph_payload_kg)
    load_hint = _load_hint_from_payload(
        trailer_id=trailer_id,
        truck_payload_kg=hint_truck,
        trailer_payload_kg=hint_trailer,
    )

    def _fmt_kg(v: float | None) -> str:
        return f"{v:.0f}" if v is not None else ""

    mass_estimated = False
    if sane_truck_mass is not None:
        total_display: float | None = effective_truck_mass
        if frame_payload_kg and empty_mass is not None:
            total_display = max(total_display or 0.0, empty_mass + frame_payload_kg)
        if attached_cargo > 0 and empty_mass is not None:
            est = empty_mass + attached_cargo
            if (total_display or 0) < est - 50:
                total_display = est
                if sane_truck_mass <= (empty_mass or 0) + PAYLOAD_TARE_KG + 100:
                    mass_estimated = True
    elif empty_mass is not None:
        extra = max(attached_cargo, frame_payload_kg)
        total_display = empty_mass + extra
        mass_estimated = True
    else:
        total_display = None

    result = {
        "load_hint": load_hint,
        "trailer_id": trailer_id,
        "cargo_mass_kg": f"{effective_payload:.0f}" if effective_payload else "0",
        "payload_kg": f"{payload_kg:.0f}" if payload_kg else "0",
        "total_mass_kg": _fmt_kg(total_display),
        "truck_mass_kg": _fmt_kg(sane_truck_mass if sane_truck_mass is not None else truck_mass),
        "mass_estimated": mass_estimated,
        "attached_cargo_mass_kg": _fmt_kg(attached_cargo) if attached_cargo else "",
        "empty_mass_kg": _fmt_kg(empty_mass),
        "trailer_mass_kg": _fmt_kg(trailer_mass),
        "cargo_types": "|".join(cargo_ids),
        "packed_cargo_slots": str(slot_count) if slot_count else "",
        "packed_cargo_bones": "|".join(packed_bones),
        "path_cargo_type": path_cargo_type,
        "frame_addon": frame_addon,
    }
    return _apply_load_latch(veh, result)


def terrain_hint(speed_kmh: float, vel_y: float) -> str:
    """Aproximacion de terreno. Con marcha reducida (2-16 km/h) no distingue asfalto/barro."""
    if speed_kmh < 2:
        return "idle"
    if speed_kmh > 28:
        return "hard_fast"  # automatico o tramo rapido
    if speed_kmh < 16 and vel_y < -0.12:
        return "crawl_deep"  # avance lento + hundimiento
    if speed_kmh < 16:
        return "crawl"  # marcha reducida tipica (10-15 km/h); superficie no deducible
    return "cruise"  # 16-28 km/h


def find_pid(name: str = MODULE) -> int | None:
    out = subprocess.check_output(
        ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    for line in out.splitlines():
        if name.lower() in line.lower():
            parts = [p.strip('"') for p in line.split('","')]
            if parts:
                try:
                    return int(parts[1])
                except ValueError:
                    pass
    return None


def get_module_base(pid: int, module: str = MODULE) -> int | None:
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return None
    try:
        hmods = (ctypes.c_void_p * 1024)()
        cb = wintypes.DWORD()
        if not psapi.EnumProcessModulesEx(
            h, ctypes.byref(hmods), ctypes.sizeof(hmods), ctypes.byref(cb), 0x03
        ):
            return None
        count = cb.value // ctypes.sizeof(ctypes.c_void_p)
        buf = ctypes.create_unicode_buffer(260)
        for i in range(count):
            base_val = ctypes.cast(hmods[i], ctypes.c_void_p).value or 0
            if not base_val:
                continue
            psapi.GetModuleBaseNameW(h, ctypes.c_void_p(base_val), buf, 260)
            if buf.value.lower() == module.lower():
                return base_val
    finally:
        kernel32.CloseHandle(h)
    return None


def read_bytes(h: int, addr: int, size: int) -> bytes | None:
    buf = (ctypes.c_char * size)()
    read = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(read))
    if not ok or read.value != size:
        return None
    return bytes(buf)


def read_u64(h: int, addr: int) -> int | None:
    b = read_bytes(h, addr, 8)
    return struct.unpack("<Q", b)[0] if b else None


def read_u32(h: int, addr: int) -> int | None:
    b = read_bytes(h, addr, 4)
    return struct.unpack("<I", b)[0] if b else None


def read_u8(h: int, addr: int) -> int | None:
    b = read_bytes(h, addr, 1)
    return b[0] if b else None


def read_f32(h: int, addr: int) -> float | None:
    b = read_bytes(h, addr, 4)
    return struct.unpack("<f", b)[0] if b else None


def read_cstring(h: int, addr: int, max_len: int = 64) -> str:
    b = read_bytes(h, addr, max_len)
    if not b:
        return ""
    end = b.find(b"\x00")
    if end >= 0:
        b = b[:end]
    return b.decode("utf-8", errors="replace")


def read_vehicle_id(h: int, veh: int) -> str:
    """ID interno del juego (p. ej. s_chevrolet_ck1500). Puntero o string inline en +D10."""

    def ok(s: str) -> bool:
        return bool(s) and s.startswith("s_") and len(s) < 64

    id_ptr = read_u64(h, veh + OFF_ID)
    if id_ptr and 0x10000 < id_ptr < 0x7FFFFFFFFFFF:
        via_ptr = read_cstring(h, id_ptr)
        if ok(via_ptr):
            return via_ptr

    inline = read_cstring(h, veh + OFF_ID)
    if ok(inline):
        return inline

    for off in (0xD50, 0xCE8, 0xCF8):
        s = read_cstring(h, veh + off)
        if ok(s):
            return s
    return ""


def read_fuel_pct(h: int, veh: int) -> str:
    for addon_off in (OFF_ADDON, 0x58, 0x70):
        addon = read_u64(h, veh + addon_off)
        if not addon or addon < 0x10000:
            continue
        current = read_f32(h, addon + OFF_FUEL)
        maximum = read_f32(h, addon + OFF_FUEL_MAX)
        if current is None or maximum is None or maximum <= 0 or maximum > 5000:
            continue
        pct = (current / maximum) * 100
        if 0 <= pct <= 100:
            return f"{pct:.1f}"
    return ""


_OFFSETS_REF_CACHE: dict[str, Any] | None = None


def load_offsets_reference() -> dict[str, Any]:
    global _OFFSETS_REF_CACHE
    if _OFFSETS_REF_CACHE is not None:
        return _OFFSETS_REF_CACHE
    path = os.path.join(os.path.dirname(__file__), "offsets_referencia.json")
    try:
        with open(path, encoding="utf-8") as f:
            import json

            _OFFSETS_REF_CACHE = json.load(f)
    except OSError:
        _OFFSETS_REF_CACHE = {}
    return _OFFSETS_REF_CACHE


def _parse_hex_offset(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    s = str(raw).strip().lower()
    if not s:
        return None
    if s.startswith("+0x"):
        s = s[1:]
    if s.startswith("0x"):
        return int(s, 16)
    if s.startswith("+"):
        return int(s[1:], 16)
    return None


def resolve_drive_logic(h: int, base: int) -> tuple[int, int, str]:
    """Devuelve (drive_logic_singleton, veh, chain_tag)."""
    singleton = read_u64(h, base + DRIVE_LOGIC_OFF)
    if not singleton:
        return 0, 0, ""
    veh = read_u64(h, singleton + OFF_VEH_DRIVE)
    if veh and veh > 0x10000:
        return singleton, veh, "DRIVE_LOGIC"
    veh = read_u64(h, singleton + OFF_VEH_TRUCK)
    if veh and veh > 0x10000:
        return singleton, veh, "DRIVE_LOGIC+8"
    return singleton, 0, "DRIVE_LOGIC"


def _vehicle_mod_id(game_id: str) -> str:
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    try:
        from camiones.registry import vehicle_id_from_ce

        return vehicle_id_from_ce(game_id) or ""
    except ImportError:
        return ""


def _catalog_drive_hints(game_id: str) -> dict[str, str]:
    mod_id = _vehicle_mod_id(game_id)
    if not mod_id:
        return {}
    try:
        from datos.catalog_lookup import truck_drive_catalog_hints

        return truck_drive_catalog_hints(mod_id)
    except ImportError:
        return {}


def _read_field_at(
    h: int, base_ptr: int, offset_spec: str | int | None, *, kind: str
) -> str:
    off = _parse_hex_offset(offset_spec)
    if off is None or not base_ptr:
        return ""
    addr = base_ptr + off
    if kind == "u8":
        v = read_u8(h, addr)
        if v in (0, 1):
            return "1" if v else "0"
        return ""
    if kind == "f32":
        v = read_f32(h, addr)
    if v is None or v != v or abs(v) > 1e6:
        return ""
    if 0.0 <= v <= 1.05:
        return f"{v:.3f}"
    return f"{v:.1f}"
    return ""


def read_drive_state(h: int, base: int, veh: int | None = None) -> dict[str, Any]:
    """Estado traccion/diff/marcha en vivo (offsets en offsets_referencia.json)."""
    drive_ref = load_offsets_reference().get("drive_runtime") or {}
    candidates = drive_ref.get("candidates") or {}
    dl, dl_veh, chain = resolve_drive_logic(h, base)
    if veh is None or veh < 0x10000:
        veh = dl_veh
    game_id = read_vehicle_id(h, veh) if veh else ""
    out: dict[str, Any] = {
        "drive_chain": chain,
        "drive_logic": hex(dl) if dl else "",
        "diff_lock_catalog": "",
        "gearbox_awd_modifier_xml": "",
    }
    out.update(_catalog_drive_hints(game_id))

    bases = [("drive_logic", dl), ("vehicle", veh)]
    field_map = (
        ("diff_lock_u8", "diff_lock_live", "u8"),
        ("awd_active_u8", "awd_live", "u8"),
        ("low_gear_u8", "low_gear_live", "u8"),
        ("throttle_f32", "throttle", "f32"),
        ("engine_rpm_f32", "engine_rpm", "f32"),
    )
    for key, out_key, kind in field_map:
        spec = candidates.get(key)
        if not spec:
            out[out_key] = ""
            continue
        if isinstance(spec, dict):
            base_name = spec.get("base", "drive_logic")
            off = spec.get("offset")
            base_ptr = dl if base_name == "drive_logic" else veh
            out[out_key] = _read_field_at(h, base_ptr, off, kind=kind)
        else:
            val = ""
            for base_name, base_ptr in bases:
                if not base_ptr:
                    continue
                val = _read_field_at(h, base_ptr, spec, kind=kind)
                if val:
                    break
            out[out_key] = val
    return out


def discover_drive_candidates(
    h: int, base: int, *, max_flags: int = 40, max_floats: int = 30
) -> dict[str, Any]:
    """Lista u8 0/1 y floats 0..1 / rpm-like para calibrar offsets."""
    dl, veh, chain = resolve_drive_logic(h, base)
    sample = read_active_sample(h, base) or {}
    result: dict[str, Any] = {
        "vehicle_id": sample.get("vehicle_id", ""),
        "speed_kmh": sample.get("speed_kmh"),
        "fuel_pct": sample.get("fuel_pct", ""),
        "drive_chain": chain,
        "flags_u8": [],
        "floats_throttle": [],
        "floats_rpm": [],
    }

    def scan_flags(label: str, ptr: int, start: int, end: int) -> None:
        if not ptr:
            return
        for off in range(start, end, 4):
            v = read_u8(h, ptr + off)
            if v in (0, 1):
                result["flags_u8"].append(
                    {"base": label, "offset": f"+{off:03X}", "u8": v}
                )
            if len(result["flags_u8"]) >= max_flags:
                return

    def scan_floats(label: str, ptr: int, start: int, end: int) -> None:
        if not ptr:
            return
        for off in range(start, end, 4):
            v = read_f32(h, ptr + off)
            if v is None or v != v or abs(v) < 1e-6:
                continue
            if 0.0 <= v <= 1.05:
                result["floats_throttle"].append(
                    {"base": label, "offset": f"+{off:03X}", "f": round(v, 4)}
                )
            elif 100.0 <= v <= 8000.0:
                result["floats_rpm"].append(
                    {"base": label, "offset": f"+{off:03X}", "f": round(v, 1)}
                )
            if (
                len(result["floats_throttle"]) >= max_floats
                and len(result["floats_rpm"]) >= max_floats
            ):
                return

    discover = (load_offsets_reference().get("drive_runtime") or {}).get("discover") or {}
    dl_rng = discover.get("drive_logic", ["0x0", "0x400"])
    veh_rng = discover.get("vehicle", ["0x100", "0xA00"])
    dl_start = _parse_hex_offset(dl_rng[0]) or 0
    dl_end = _parse_hex_offset(dl_rng[1]) or 0x400
    veh_start = _parse_hex_offset(veh_rng[0]) or 0x100
    veh_end = _parse_hex_offset(veh_rng[1]) or 0xA00
    scan_flags("drive_logic", dl, dl_start, dl_end)
    scan_flags("vehicle", veh, veh_start, veh_end)
    scan_floats("drive_logic", dl, dl_start, dl_end)
    scan_floats("vehicle", veh, veh_start, veh_end)
    return result


class FuelRateTracker:
    """Deriva fuel_pct/min desde lecturas sucesivas de % tanque."""

    def __init__(self) -> None:
        self._last: tuple[float, float] | None = None

    def reset(self) -> None:
        self._last = None

    def update(self, t_s: float, fuel_pct: str) -> str:
        raw = (fuel_pct or "").strip()
        if not raw:
            return ""
        try:
            pct = float(raw)
        except ValueError:
            return ""
        if self._last is None:
            self._last = (t_s, pct)
            return ""
        dt = t_s - self._last[0]
        if dt < 0.25:
            return ""
        rate = (self._last[1] - pct) / dt * 60.0
        self._last = (t_s, pct)
        return f"{rate:.2f}"


_FUEL_RATE_TRACKER = FuelRateTracker()


def update_fuel_rate(sample: dict[str, Any], t_s: float) -> dict[str, Any]:
    sample["fuel_rate_pct_min"] = _FUEL_RATE_TRACKER.update(t_s, sample.get("fuel_pct", ""))
    return sample


def enrich_drive_fields(
    h: int, base: int, sample: dict[str, Any], *, t_s: float | None = None
) -> dict[str, Any]:
    veh_hex = sample.get("veh") or ""
    try:
        veh = int(veh_hex, 16)
    except (TypeError, ValueError):
        veh = 0
    drive = read_drive_state(h, base, veh)
    for key in (
        "diff_lock_live",
        "awd_live",
        "low_gear_live",
        "throttle",
        "engine_rpm",
        "diff_lock_catalog",
        "gearbox_awd_modifier_xml",
    ):
        if drive.get(key) not in (None, ""):
            sample[key] = drive[key]
    if t_s is not None:
        update_fuel_rate(sample, t_s)
    return sample


def probe_chain(h: int, base: int, off: int, veh_off: int, tag: str) -> dict[str, Any]:
    slot = base + off
    singleton = read_u64(h, slot)
    result: dict[str, Any] = {
        "tag": tag,
        "slot": hex(slot),
        "singleton": hex(singleton) if singleton else "0",
    }
    if not singleton:
        return result
    veh = read_u64(h, singleton + veh_off)
    result["veh"] = hex(veh) if veh else "0"
    if not veh:
        return result
    sample = read_sample_from_vehicle(h, veh, tag)
    if sample:
        result.update(sample)
    return result


def read_active_vehicle(h: int, base: int) -> tuple[int | None, str]:
    for off, veh_off, tag in (
        (TRUCK_CONTROL_OFF, OFF_VEH_TRUCK, "TRUCK_CONTROL"),
        (DRIVE_LOGIC_OFF, OFF_VEH_DRIVE, "DRIVE_LOGIC"),
    ):
        singleton = read_u64(h, base + off)
        if not singleton:
            continue
        veh = read_u64(h, singleton + veh_off)
        if veh and veh > 0x10000:
            rb = read_u64(h, veh + OFF_RB)
            if rb and rb > 0x10000 and read_f32(h, rb + OFF_VX) is not None:
                return veh, tag
    return None, ""


def read_sample_from_vehicle(
    h: int, veh: int, chain: str = "TRUCK_CONTROL"
) -> dict[str, Any] | None:
    rb = read_u64(h, veh + OFF_RB)
    if not rb or rb < 0x10000:
        return None
    vx = read_f32(h, rb + OFF_VX)
    vz = read_f32(h, rb + OFF_VZ)
    if vx is None or vz is None:
        return None
    vy = read_f32(h, rb + OFF_VY) or 0.0
    speed = (vx * vx + vz * vz) ** 0.5 * 3.6
    vehicle_id = read_vehicle_id(h, veh)
    terrain = read_wheel_terrain(h, veh, vel_y=vy)
    load = read_vehicle_load(h, veh)
    sample = {
        "veh": hex(veh),
        "rb": hex(rb),
        "vel_x": vx,
        "vel_y": vy,
        "vel_z": vz,
        "ang_yaw": read_f32(h, rb + OFF_YAW) or 0.0,
        "pos_x": read_f32(h, rb + OFF_POS_X) or 0.0,
        "pos_y": read_f32(h, rb + OFF_POS_Y) or 0.0,
        "pos_z": read_f32(h, rb + OFF_POS_Z) or 0.0,
        "speed_kmh": round(speed, 2),
        "km_h": round(speed, 2),
        "vehicle_id": vehicle_id,
        "fuel_pct": read_fuel_pct(h, veh),
        "surface_wheel": terrain.get("surface_wheel", ""),
        "wheel_grip": terrain.get("wheel_grip", ""),
        "terrain_kind": terrain.get("terrain_kind", "unknown"),
        "surface_avg": terrain.get("surface_avg", ""),
        "contact_avg": terrain.get("contact_avg", ""),
        "grip_min": terrain.get("grip_min", ""),
        "grip_max": terrain.get("grip_max", ""),
        "surface_deform_avg": terrain.get("surface_deform_avg", ""),
        "contact_min": terrain.get("contact_min", ""),
        "contact_max": terrain.get("contact_max", ""),
        "mud_grade": terrain.get("mud_grade", ""),
        "mud_grade_label": terrain.get("mud_grade_label", ""),
        "wheel_kinds": terrain.get("wheel_kinds", ""),
        "wheel_disagreement": terrain.get("wheel_disagreement", False),
        "terrain_hint": terrain_hint(speed, vy),
        "chain": chain,
        "load_hint": load.get("load_hint", "vacio"),
        "trailer_id": load.get("trailer_id", ""),
        "cargo_mass_kg": load.get("cargo_mass_kg", "0"),
        "payload_kg": load.get("payload_kg", "0"),
        "total_mass_kg": load.get("total_mass_kg", ""),
        "empty_mass_kg": load.get("empty_mass_kg", ""),
        "trailer_mass_kg": load.get("trailer_mass_kg", ""),
        "truck_mass_kg": load.get("truck_mass_kg", ""),
        "mass_estimated": load.get("mass_estimated", False),
        "attached_cargo_mass_kg": load.get("attached_cargo_mass_kg", ""),
        "cargo_types": load.get("cargo_types", ""),
        "packed_cargo_slots": load.get("packed_cargo_slots", ""),
        "packed_cargo_bones": load.get("packed_cargo_bones", ""),
        "path_cargo_type": load.get("path_cargo_type", ""),
        "frame_addon": load.get("frame_addon", ""),
    }
    return enrich_turn_fields(sample)


def read_active_sample(h: int, base: int) -> dict[str, Any] | None:
    for off, veh_off, tag in (
        (TRUCK_CONTROL_OFF, OFF_VEH_TRUCK, "TRUCK_CONTROL"),
        (DRIVE_LOGIC_OFF, OFF_VEH_DRIVE, "DRIVE_LOGIC"),
    ):
        singleton = read_u64(h, base + off)
        if not singleton:
            continue
        veh = read_u64(h, singleton + veh_off)
        if not veh:
            continue
        sample = read_sample_from_vehicle(h, veh, tag)
        if sample:
            return sample
    return None


def open_snowrunner() -> tuple[int, int, int] | None:
    """Devuelve (handle, base, pid) o None."""
    pid = find_pid()
    if not pid:
        return None
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return None
    base = get_module_base(pid)
    if not base:
        kernel32.CloseHandle(h)
        return None
    return h, base, pid


def format_csv_row(
    t_s: float,
    sample: dict[str, Any],
    event: str = "",
) -> str:
    vid = (sample.get("vehicle_id") or "").replace(",", " ").replace("\n", " ")
    return (
        f"{t_s:.2f},{sample['speed_kmh']:.2f},"
        f"{sample['vel_x']:.4f},{sample['vel_y']:.4f},{sample['vel_z']:.4f},"
        f"{sample['ang_yaw']:.4f},{sample['pos_y']:.4f},"
        f"{sample.get('fuel_pct', '')},{vid},"
        f"{sample.get('surface_wheel', '')},{sample.get('wheel_grip', '')},"
        f"{sample.get('terrain_hint', '')},{event},{sample.get('chain', '')},"
        f"{sample.get('terrain_kind', '')},{sample.get('terrain_map', '')},"
        f"{sample.get('pos_x', '')},{sample.get('pos_z', '')},"
        f"{sample.get('surface_avg', '')},{sample.get('contact_avg', '')},"
        f"{sample.get('grip_min', '')},{sample.get('grip_max', '')},"
        f"{sample.get('surface_deform_avg', '')},{sample.get('contact_min', '')},"
        f"{sample.get('contact_max', '')},{sample.get('mud_grade', '')},"
        f"{sample.get('mud_grade_label', '')},"
        f"{sample.get('load_hint', '')},{sample.get('trailer_id', '')},"
        f"{sample.get('cargo_mass_kg', '')},"
        f"{sample.get('total_mass_kg', '')},{sample.get('empty_mass_kg', '')},"
        f"{sample.get('payload_kg', '')},{sample.get('trailer_mass_kg', '')},"
        f"{sample.get('truck_mass_kg', '')},{sample.get('attached_cargo_mass_kg', '')},"
        f"{sample.get('yaw_rate_deg_s', '')},{sample.get('turn_radius_m', '')},"
        f"{sample.get('packed_cargo_slots', '')},{sample.get('path_cargo_type', '')},"
        f"{sample.get('frame_addon', '')},"
        f"{sample.get('diff_lock_live', '')},{sample.get('awd_live', '')},"
        f"{sample.get('low_gear_live', '')},{sample.get('throttle', '')},"
        f"{sample.get('engine_rpm', '')},{sample.get('fuel_rate_pct_min', '')},"
        f"{sample.get('map_name', '')},{sample.get('level_id', '')}\n"
    )


def write_status(msg: str) -> None:
    try:
        os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            from datetime import datetime

            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            f.write(msg + "\n")
    except OSError:
        pass
