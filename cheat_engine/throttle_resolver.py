"""Resuelve throttle_input por camion (controles del juego en TRUCK_CONTROL).

El offset global (tc+0E8+0xC8) solo existe en algunos camiones (Bandit).
Aqui probamos hijos tc+XXX y dl+028 con offsets habituales del barrido.
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))
import memoria_havok as mh  # noqa: E402
from pedal_hunt import enumerate_scan_targets  # noqa: E402

COMMON_U8_OFFSETS: tuple[int, ...] = (
    0x0C8,
    0x5E8,
    0x17C,
    0x0D8,
    0x0E0,
    0x108,
    0x184,
    0x100,
    0x168,
)

DL028_F32_SPEC: dict[str, str] = {
    "base": "dl+028",
    "offset": "+0x138",
    "kind": "f32",
    "chain": "DRIVE_LOGIC",
    "note": "fallback input f32",
}

_SESSION_CACHE: dict[str, dict[str, str]] = {}


def _tc_child_sort_key(label: str) -> tuple[int, str]:
    if label == "truck_control":
        return (2, label)
    if label.startswith("tc+"):
        return (0, label)
    if label.startswith("dl+"):
        return (1, label)
    return (3, label)


def _spec_readable(h: int, base: int, spec: dict[str, str], *, veh_ptr: int) -> bool:
    ptr = mh.resolve_field_base_ptr(h, base, spec.get("base", ""), veh_ptr=veh_ptr)
    if not ptr:
        return False
    off = mh._parse_hex_offset(spec.get("offset"))
    if off is None:
        return False
    kind = spec.get("kind", "f32")
    if kind == "u8":
        return mh.read_u8(h, ptr + off) is not None
    return mh.read_f32(h, ptr + off) is not None


def _make_spec(base: str, offset: int, kind: str, *, note: str = "") -> dict[str, str]:
    spec: dict[str, str] = {
        "base": base,
        "offset": f"+0x{offset:03X}",
        "kind": kind,
    }
    if base.startswith("tc"):
        spec["chain"] = "TRUCK_CONTROL"
    elif base.startswith("dl"):
        spec["chain"] = "DRIVE_LOGIC"
    elif base == "truck_control":
        spec["chain"] = "TRUCK_CONTROL"
    if note:
        spec["note"] = note
    return spec


def auto_probe_throttle_spec(h: int, base: int, veh_ptr: int) -> dict[str, str] | None:
    """Busca el primer bloque tc+XXX legible con offsets tipicos de pedal."""
    targets = enumerate_scan_targets(h, base, veh_ptr)
    ordered = sorted(targets, key=lambda t: _tc_child_sort_key(t.label))
    for t in ordered:
        if not t.label.startswith("tc+"):
            continue
        for off in COMMON_U8_OFFSETS:
            if off >= t.scan_end:
                continue
            if mh.read_u8(h, t.ptr + off) is None:
                continue
            spec = _make_spec(t.label, off, "u8", note="auto-probe tc child")
            if _spec_readable(h, base, spec, veh_ptr=veh_ptr):
                return spec
    if _spec_readable(h, base, DL028_F32_SPEC, veh_ptr=veh_ptr):
        return dict(DL028_F32_SPEC)
    return None


def per_vehicle_specs(drive_runtime: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    raw = (drive_runtime or {}).get("per_vehicle") or {}
    out: dict[str, dict[str, str]] = {}
    for veh_id, entry in raw.items():
        if isinstance(entry, dict) and entry.get("throttle_input"):
            out[str(veh_id)] = dict(entry["throttle_input"])
    return out


def resolve_throttle_input_spec(
    h: int,
    base: int,
    veh_ptr: int,
    veh_id: str,
    *,
    global_spec: dict[str, str] | None = None,
    per_vehicle: dict[str, dict[str, str]] | None = None,
    use_cache: bool = True,
) -> tuple[dict[str, str] | None, str]:
    """Devuelve (spec, source_tag) para leer input jugador 0..1."""
    vid = (veh_id or "").strip()
    if use_cache and vid and vid in _SESSION_CACHE:
        return dict(_SESSION_CACHE[vid]), "cache"

    if per_vehicle and vid and vid in per_vehicle:
        spec = dict(per_vehicle[vid])
        if _spec_readable(h, base, spec, veh_ptr=veh_ptr):
            if use_cache and vid:
                _SESSION_CACHE[vid] = spec
            return spec, "per_vehicle"

    if global_spec and _spec_readable(h, base, global_spec, veh_ptr=veh_ptr):
        if use_cache and vid:
            _SESSION_CACHE[vid] = dict(global_spec)
        return dict(global_spec), "global"

    probed = auto_probe_throttle_spec(h, base, veh_ptr)
    if probed:
        if use_cache and vid:
            _SESSION_CACHE[vid] = probed
        return probed, "auto_probe"

    return None, "none"


def clear_throttle_cache() -> None:
    _SESSION_CACHE.clear()


def save_per_vehicle_throttle(
    ref: dict[str, Any],
    vehicle_id: str,
    thr_spec: dict[str, str],
) -> dict[str, Any]:
    drive = dict(ref.get("drive_runtime") or {})
    pv = dict(drive.get("per_vehicle") or {})
    pv[vehicle_id] = {"throttle_input": dict(thr_spec)}
    drive["per_vehicle"] = pv
    ref["drive_runtime"] = drive
    return ref
