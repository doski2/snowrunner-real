"""Calibracion y verificacion de gas (throttle) y RPM para telemetria CE.

Uso:
  python cheat_engine/calibrar_drive.py --interactive
  python cheat_engine/calibrar_drive.py --from-snaps gas_off gas_full
  python cheat_engine/calibrar_drive.py --verify
  grabar_telemetria.bat drive_cal
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import memoria_havok as mh  # noqa: E402

SNAP_DIR = os.path.join(os.path.dirname(__file__), "drive_snaps")

FieldKey = tuple[str, int]
ThrottleCandidate = tuple[float, FieldKey, float, float]
RpmCandidate = tuple[float, FieldKey, float, float]


def _vehicle_ptr_from_sample(sample: dict[str, Any] | None) -> int:
    if not sample:
        return 0
    raw = sample.get("veh") or ""
    try:
        ptr = int(str(raw), 16)
    except (TypeError, ValueError):
        return 0
    return ptr if ptr > 0x10000 else 0


def _scan_values_pass(v0: float, v1: float) -> bool:
    return v0 <= 0.15 and v1 >= 0.75 and (v1 - v0) >= 0.45


def _offset_key(base: str, offset: str | int) -> FieldKey:
    off = mh._parse_hex_offset(offset)
    if off is None:
        raise ValueError(f"offset invalido: {offset!r}")
    return base, off


def _offset_fmt(key: FieldKey) -> str:
    base, off = key
    return f"{base}+0x{off:03X}"


def _spec_dict(base: str, offset: int) -> dict[str, str]:
    return {"base": base, "offset": f"+0x{offset:03X}"}


def _floats_from_snap(snap: dict, field: str) -> dict[FieldKey, float]:
    out: dict[FieldKey, float] = {}
    for row in snap.get(field, []):
        key = _offset_key(row["base"], row["offset"])
        out[key] = float(row["f"])
    return out


def resolve_scan_bases(h: int, base: int) -> list[tuple[str, int, str]]:
    """Bases de memoria para escanear gas/RPM (TRUCK_CONTROL primero)."""
    bases: list[tuple[str, int, str]] = []
    seen: set[int] = set()

    dl, dl_veh, chain = mh.resolve_drive_logic(h, base)
    if dl:
        bases.append(("drive_logic", dl, chain or "DRIVE_LOGIC"))

    act_veh, act_tag = mh.read_active_vehicle(h, base)
    if act_veh and act_veh not in seen:
        bases.append(("vehicle", act_veh, act_tag))
        seen.add(act_veh)

    singleton = mh.read_u64(h, base + mh.TRUCK_CONTROL_OFF)
    if singleton:
        tc_veh = mh.read_u64(h, singleton + mh.OFF_VEH_TRUCK)
        if tc_veh and tc_veh not in seen:
            bases.append(("vehicle", tc_veh, "TRUCK_CONTROL"))
            seen.add(tc_veh)

    if dl_veh and dl_veh not in seen:
        bases.append(("vehicle_dl", dl_veh, "DRIVE_LOGIC+veh"))
        seen.add(dl_veh)

    return bases


def _normalize_throttle_key(key: FieldKey) -> FieldKey:
    base, off = key
    if base == "vehicle_dl":
        return ("vehicle", off)
    return key


def scan_throttle_rpm_maps(
    h: int, base: int, *, veh_ptr: int | None = None
) -> tuple[dict[FieldKey, float], dict[FieldKey, float]]:
    """Barrido f32 en drive_logic + vehiculo activo (mismo ptr que telemetria)."""
    discover = (mh.load_offsets_reference().get("drive_runtime") or {}).get("discover") or {}
    dl_rng = discover.get("drive_logic", ["0x0", "0x400"])
    veh_rng = discover.get("vehicle", ["0x0", "0xC00"])
    dl_start = mh._parse_hex_offset(dl_rng[0]) or 0
    dl_end = mh._parse_hex_offset(dl_rng[1]) or 0x400
    veh_start = mh._parse_hex_offset(veh_rng[0]) or 0
    veh_end = mh._parse_hex_offset(veh_rng[1]) or 0xC00

    throttle: dict[FieldKey, float] = {}
    rpm: dict[FieldKey, float] = {}

    def store_float(key: FieldKey, v: float) -> None:
        if 0.0 <= v <= 1.05:
            throttle[key] = round(v, 4)
        elif 1.05 < v <= 100.0:
            throttle[key] = round(v / 100.0, 4)
        elif 100.0 <= v <= 8000.0:
            rpm[key] = round(v, 1)

    def scan(label: str, ptr: int, start: int, end: int) -> None:
        if not ptr:
            return
        for off in range(start, end, 4):
            v = mh.read_f32(h, ptr + off)
            if v is None or v != v:
                continue
            if abs(v) < 1e-6:
                store_float((label, off), 0.0)
                continue
            store_float((label, off), v)

    dl, _, _ = mh.resolve_drive_logic(h, base)
    if dl:
        scan("drive_logic", dl, dl_start, dl_end)

    veh = veh_ptr or 0
    if not veh:
        veh, _ = mh.read_active_vehicle(h, base)
    if veh:
        scan("vehicle", veh, veh_start, veh_end)

    return throttle, rpm


def _rank_throttle_strict(
    off_map: dict[FieldKey, float], full_map: dict[FieldKey, float]
) -> list[ThrottleCandidate]:
    ranked: list[ThrottleCandidate] = []
    keys = set(off_map) | set(full_map)
    for key in keys:
        v0 = off_map.get(key, 0.0)
        v1 = full_map.get(key)
        if v1 is None:
            continue
        if v0 > 0.25 or v1 < 0.65:
            continue
        delta = v1 - v0
        if delta < 0.45:
            continue
        score = delta + max(0.0, 0.2 - v0) + (v1 - 0.7)
        if key[0] == "vehicle":
            score += 0.15
        ranked.append((score, key, v0, v1))
    ranked.sort(key=lambda x: -x[0])
    return ranked


def _rank_throttle_relaxed(
    off_map: dict[FieldKey, float], full_map: dict[FieldKey, float]
) -> list[ThrottleCandidate]:
    ranked: list[ThrottleCandidate] = []
    for key in set(off_map) & set(full_map):
        v0, v1 = off_map[key], full_map[key]
        if min(v0, v1) > 0.92:
            continue
        delta = v1 - v0
        if delta < 0.2:
            continue
        if v1 < 0.45 and delta < 0.35:
            continue
        score = delta + max(0.0, 0.3 - v0) + max(0.0, v1 - 0.5)
        if key[0] == "vehicle":
            score += 0.2
        ranked.append((score, key, v0, v1))
    ranked.sort(key=lambda x: -x[0])
    return ranked


def _rank_throttle_delta(
    off_map: dict[FieldKey, float], full_map: dict[FieldKey, float]
) -> list[ThrottleCandidate]:
    ranked: list[ThrottleCandidate] = []
    for key in set(off_map) & set(full_map):
        v0, v1 = off_map[key], full_map[key]
        if min(v0, v1) > 0.95:
            continue
        delta = v1 - v0
        if delta < 0.08:
            continue
        score = delta
        if key[0] == "vehicle":
            score += 0.05
        ranked.append((score, key, v0, v1))
    ranked.sort(key=lambda x: -x[0])
    return ranked


def rank_throttle_candidates(
    off_map: dict[FieldKey, float], full_map: dict[FieldKey, float]
) -> list[ThrottleCandidate]:
    for ranker in (_rank_throttle_strict, _rank_throttle_relaxed, _rank_throttle_delta):
        ranked = ranker(off_map, full_map)
        if ranked:
            return ranked
    return []


def rank_throttle_deltas_for_debug(
    off_map: dict[FieldKey, float], full_map: dict[FieldKey, float], *, limit: int = 12
) -> list[tuple[float, FieldKey, float, float]]:
    rows: list[tuple[float, FieldKey, float, float]] = []
    for key in set(off_map) & set(full_map):
        v0, v1 = off_map[key], full_map[key]
        rows.append((v1 - v0, key, v0, v1))
    rows.sort(key=lambda x: -x[0])
    return rows[:limit]


def rank_rpm_candidates(
    off_map: dict[FieldKey, float], full_map: dict[FieldKey, float]
) -> list[RpmCandidate]:
    ranked: list[RpmCandidate] = []
    keys = set(off_map) & set(full_map)
    for key in keys:
        v0, v1 = off_map[key], full_map[key]
        delta = v1 - v0
        if delta < 25.0:
            continue
        if v0 < 40.0 or v1 < 80.0:
            continue
        score = delta
        ranked.append((score, key, v0, v1))
    ranked.sort(key=lambda x: -x[0])
    return ranked


def pick_from_snaps(off_snap: dict, full_snap: dict) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    thr = rank_throttle_candidates(
        _floats_from_snap(off_snap, "floats_throttle"),
        _floats_from_snap(full_snap, "floats_throttle"),
    )
    rpm = rank_rpm_candidates(
        _floats_from_snap(off_snap, "floats_rpm"),
        _floats_from_snap(full_snap, "floats_rpm"),
    )
    thr_spec = _spec_dict(*_normalize_throttle_key(thr[0][1])) if thr else None
    rpm_spec = _spec_dict(*rpm[0][1]) if rpm else None
    return thr_spec, rpm_spec


def read_live_field(
    h: int, base: int, spec: dict[str, str], *, veh_ptr: int | None = None
) -> float | None:
    base_name = spec.get("base", "vehicle")
    off = mh._parse_hex_offset(spec.get("offset"))
    kind = spec.get("kind", "f32")
    if off is None:
        return None
    ptr = mh.resolve_field_base_ptr(h, base, base_name, veh_ptr=veh_ptr)
    if not ptr:
        return None
    if kind == "u8":
        u = mh.read_u8(h, ptr + off)
        return (u / 255.0) if u is not None else None
    return mh.read_f32(h, ptr + off)


def _poll_live_field(
    h: int,
    base: int,
    spec: dict[str, str],
    *,
    veh_ptr: int | None,
    kind: str,
    duration: float = 3.0,
    interval: float = 0.12,
) -> float | None:
    end = time.monotonic() + duration
    vals: list[float] = []
    while time.monotonic() < end:
        v = read_live_field(h, base, spec, veh_ptr=veh_ptr)
        if v is not None:
            vals.append(v)
        time.sleep(interval)
    if not vals:
        return None
    return min(vals) if kind == "min" else max(vals)


def _spec_from_key(key: FieldKey) -> dict[str, str]:
    base, off = _normalize_throttle_key(key)
    return _spec_dict(base, off)


def verify_throttle_rpm(
    h: int,
    base: int,
    thr_spec: dict[str, str],
    rpm_spec: dict[str, str] | None,
    *,
    interactive: bool = True,
    poll: bool = False,
    veh_ptr: int | None = None,
) -> tuple[bool, str]:
    """Comprueba gas suelto bajo y gas a fondo alto (y rpm sube)."""
    use_poll = poll or interactive

    if interactive:
        input(
            "\n>>> PASO 3 — SUELTA el gas (suelta el del paso 2). "
            "Pie del freno. Pulsa ENTER cuando este suelto..."
        )
    elif not use_poll:
        print("Leyendo gas SUELTO (debes tener el pedal sin pisar)...")
        time.sleep(1.0)

    if use_poll:
        print("  Midiendo gas suelto (3 s)...")
        v_off = _poll_live_field(
            h, base, thr_spec, veh_ptr=veh_ptr, kind="min", duration=3.0
        )
        rpm_off = (
            _poll_live_field(h, base, rpm_spec, veh_ptr=veh_ptr, kind="min", duration=1.5)
            if rpm_spec
            else None
        )
    else:
        v_off = read_live_field(h, base, thr_spec, veh_ptr=veh_ptr)
        rpm_off = read_live_field(h, base, rpm_spec, veh_ptr=veh_ptr) if rpm_spec else None

    if interactive:
        input(">>> Gas A FONDO (freno o pared). Pulsa ENTER...")
    elif not use_poll:
        print("Leyendo gas A FONDO...")
        time.sleep(1.0)

    if use_poll:
        print("  Midiendo gas a fondo (3 s)...")
        v_full = _poll_live_field(
            h, base, thr_spec, veh_ptr=veh_ptr, kind="max", duration=3.0
        )
        rpm_full = (
            _poll_live_field(h, base, rpm_spec, veh_ptr=veh_ptr, kind="max", duration=1.5)
            if rpm_spec
            else None
        )
    else:
        v_full = read_live_field(h, base, thr_spec, veh_ptr=veh_ptr)
        rpm_full = read_live_field(h, base, rpm_spec, veh_ptr=veh_ptr) if rpm_spec else None

    lines = [
        f"  throttle {_offset_fmt(_offset_key(thr_spec['base'], thr_spec['offset']))}: "
        f"off={v_off} full={v_full}",
    ]
    if rpm_spec:
        lines.append(
            f"  rpm {_offset_fmt(_offset_key(rpm_spec['base'], rpm_spec['offset']))}: "
            f"off={rpm_off} full={rpm_full}"
        )

    ok_thr = (
        v_off is not None
        and v_full is not None
        and v_off <= 0.15
        and v_full >= 0.75
        and (v_full - v_off) >= 0.45
    )
    ok_rpm = True
    if rpm_spec and rpm_off is not None and rpm_full is not None:
        ok_rpm = rpm_full - rpm_off >= 25.0

    ok = ok_thr and ok_rpm
    detail = "\n".join(lines)
    if ok:
        return True, detail + "\n  OK verificacion gas/RPM."
    return False, detail + "\n  FALLO verificacion — offset incorrecto o pedal no cambiado."


def apply_candidates(
    thr_spec: dict[str, str] | None,
    rpm_spec: dict[str, str] | None,
    *,
    vehicle_id: str = "",
    snap_note: str = "",
) -> str:
    ref = mh.load_offsets_reference()
    drive = dict(ref.get("drive_runtime") or {})
    cands = dict(drive.get("candidates") or {})
    if thr_spec:
        cands["throttle_f32"] = thr_spec
    if rpm_spec:
        cands["engine_rpm_f32"] = rpm_spec
    drive["candidates"] = cands
    drive["status"] = (
        f"throttle+rpm calibrados {time.strftime('%Y-%m-%d')} "
        f"veh={vehicle_id or '?'}"
    )
    if snap_note:
        drive["calibration_snaps"] = {
            **(drive.get("calibration_snaps") or {}),
            "note": snap_note,
        }
    ref["drive_runtime"] = drive
    return mh.save_offsets_reference(ref)


def _load_snap(name: str) -> dict:
    path = os.path.join(SNAP_DIR, f"{name}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_snap(name: str, data: dict) -> str:
    os.makedirs(SNAP_DIR, exist_ok=True)
    path = os.path.join(SNAP_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def interactive_calibrate() -> int:
    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo — entra al mapa conduciendo.")
        return 1
    h, base, pid = opened
    try:
        sample = mh.read_active_sample(h, base)
        if not sample:
            print("Sin vehiculo activo.")
            return 1
        veh_id = sample.get("vehicle_id") or "?"
        chain = sample.get("chain") or "?"
        veh_ptr = _vehicle_ptr_from_sample(sample)
        print(f"PID={pid} vehiculo={veh_id} chain={chain} veh={sample.get('veh')} speed={sample.get('speed_kmh')} km/h")
        scan_bases = resolve_scan_bases(h, base)
        print("Bases escaneo:", ", ".join(f"{lbl}={hex(ptr)} ({tag})" for lbl, ptr, tag in scan_bases))
        if veh_ptr:
            print(f"Telemetria usa veh={hex(veh_ptr)} para throttle/RPM")
        print("\n=== Calibracion gas + RPM ===")
        print("Mismo camion, quieto (~0 km/h), motor ON.")
        print("IMPORTANTE: paso 1 = pie del freno SIN gas; paso 2 = gas A FONDO.\n")

        input("Paso 1/3 — SUELTA el gas. Pulsa ENTER...")
        off_thr, off_rpm = scan_throttle_rpm_maps(h, base, veh_ptr=veh_ptr)
        off_path = _save_snap(
            "gas_off_live",
            {
                "vehicle_id": veh_id,
                "speed_kmh": sample.get("speed_kmh"),
                "floats_throttle": [
                    {"base": k[0], "offset": f"+{k[1]:03X}", "f": v} for k, v in off_thr.items()
                ],
                "floats_rpm": [
                    {"base": k[0], "offset": f"+{k[1]:03X}", "f": v} for k, v in off_rpm.items()
                ],
            },
        )
        print(f"  Guardado {off_path} ({len(off_thr)} floats gas, {len(off_rpm)} rpm)")

        input("\nPaso 2/3 — Gas A FONDO (freno/pared). Pulsa ENTER...")
        full_thr, full_rpm = scan_throttle_rpm_maps(h, base, veh_ptr=veh_ptr)
        full_path = _save_snap(
            "gas_full_live",
            {
                "vehicle_id": veh_id,
                "speed_kmh": mh.read_active_sample(h, base).get("speed_kmh"),
                "floats_throttle": [
                    {"base": k[0], "offset": f"+{k[1]:03X}", "f": v} for k, v in full_thr.items()
                ],
                "floats_rpm": [
                    {"base": k[0], "offset": f"+{k[1]:03X}", "f": v} for k, v in full_rpm.items()
                ],
            },
        )
        print(f"  Guardado {full_path}")

        thr_ranked = rank_throttle_candidates(off_thr, full_thr)
        rpm_ranked = rank_rpm_candidates(off_rpm, full_rpm)
        if not thr_ranked:
            print("\nNo hay candidato throttle valido (gas off alto o full bajo).")
            print("Comprueba: paso 1 sin gas, paso 2 gas a fondo (freno/pared).")
            veh_off = {k: v for k, v in off_thr.items() if k[0] == "vehicle"}
            veh_full = {k: v for k, v in full_thr.items() if k[0] == "vehicle"}
            if not veh_off and not veh_full:
                print("AVISO: ningun float en bloque vehicle — revisa TRUCK_CONTROL / probe.")
            print("\nTop deltas (todos los bloques):")
            for delta, key, v0, v1 in rank_throttle_deltas_for_debug(off_thr, full_thr):
                print(f"  {_offset_fmt(key)}: {v0} -> {v1}  (d={delta:+.4f})")
            print("\nCandidatos gas off (muestra):")
            for row in list(off_thr.items())[:10]:
                print(f"  {row}")
            print("Candidatos gas full (muestra):")
            for row in list(full_thr.items())[:10]:
                print(f"  {row}")
            return 1

        print("\nCandidatos throttle (top 5):")
        for score, key, v0, v1 in thr_ranked[:5]:
            print(f"  {_offset_fmt(key)}: {v0} -> {v1}  (score {score:.2f})")

        thr_spec = _spec_from_key(thr_ranked[0][1])
        rpm_spec = _spec_dict(*rpm_ranked[0][1]) if rpm_ranked else None
        if rpm_ranked:
            print("\nCandidatos rpm (top 3):")
            for score, key, v0, v1 in rpm_ranked[:3]:
                print(f"  {_offset_fmt(key)}: {v0} -> {v1}  (score {score:.0f})")

        for attempt, cand in enumerate(thr_ranked[:5], start=1):
            thr_spec = _spec_from_key(cand[1])
            rpm_spec = _spec_dict(*rpm_ranked[0][1]) if rpm_ranked else None
            v0_scan, v1_scan = cand[2], cand[3]
            print(f"\n--- Intento {attempt}: throttle {_offset_fmt(cand[1])} ---")
            print(f"  Escaneo: {v0_scan} -> {v1_scan}")

            if _scan_values_pass(v0_scan, v1_scan):
                apply_candidates(
                    thr_spec,
                    rpm_spec,
                    vehicle_id=veh_id,
                    snap_note=(
                        f"live {veh_id} scan {_offset_fmt(cand[1])} "
                        f"{v0_scan}->{v1_scan}"
                    ),
                )
                print("  OK por escaneo (pasos 1-2). Verificacion en vivo opcional...")
                ok, msg = verify_throttle_rpm(
                    h,
                    base,
                    thr_spec,
                    rpm_spec,
                    interactive=True,
                    poll=True,
                    veh_ptr=veh_ptr,
                )
                print(msg)
                if ok:
                    print(f"\nOffsets guardados en offsets_referencia.json")
                    print(f"  throttle_f32: {thr_spec}")
                    if rpm_spec:
                        print(f"  engine_rpm_f32: {rpm_spec}")
                    return 0
                if _scan_values_pass(v0_scan, v1_scan) and (v1_scan - v0_scan) >= 0.5:
                    print(
                        "\n  Verificacion en vivo ambigua, pero escaneo fuerte — "
                        "offsets guardados."
                    )
                    print(f"  throttle_f32: {thr_spec}")
                    if rpm_spec:
                        print(f"  engine_rpm_f32: {rpm_spec}")
                    return 0
                print("  Escaneo OK pero verificacion en vivo no cuadra; probando otro...")
                continue

            apply_candidates(
                thr_spec,
                rpm_spec,
                vehicle_id=veh_id,
                snap_note=f"live {veh_id} off->full throttle {_offset_fmt(cand[1])}",
            )
            ok, msg = verify_throttle_rpm(
                h,
                base,
                thr_spec,
                rpm_spec,
                interactive=True,
                poll=True,
                veh_ptr=veh_ptr,
            )
            print(msg)
            if ok:
                print(f"\nOffsets guardados en offsets_referencia.json")
                print(f"  throttle_f32: {thr_spec}")
                if rpm_spec:
                    print(f"  engine_rpm_f32: {rpm_spec}")
                return 0
            print("Probando siguiente candidato...\n")

        print("\nNingun candidato paso verificacion. Repite drive_cal en otro sitio quieto.")
        return 1
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)


def preflight_check(h: int, base: int) -> tuple[bool, str]:
    """Comprobacion rapida sin prompts: offsets presentes y throttle no pegado a 1.0 parado."""
    ref = mh.load_offsets_reference()
    cands = (ref.get("drive_runtime") or {}).get("candidates") or {}
    thr_spec = cands.get("throttle_f32")
    rpm_spec = cands.get("engine_rpm_f32")
    if not thr_spec:
        return False, "throttle_f32 sin calibrar — ejecuta: .\\grabar_telemetria.bat drive_cal"

    sample = mh.read_active_sample(h, base) or {}
    veh_ptr = _vehicle_ptr_from_sample(sample)
    speed = float(sample.get("speed_kmh") or 0.0)
    thr = read_live_field(h, base, thr_spec, veh_ptr=veh_ptr)
    rpm = read_live_field(h, base, rpm_spec, veh_ptr=veh_ptr) if rpm_spec else None

    lines = [
        f"  throttle {_offset_fmt(_offset_key(thr_spec['base'], thr_spec['offset']))}: {thr}",
    ]
    if rpm_spec:
        lines.append(
            f"  rpm {_offset_fmt(_offset_key(rpm_spec['base'], rpm_spec['offset']))}: {rpm}"
        )
    lines.append(f"  speed_kmh={speed:.1f}")

    if thr is None:
        return False, "\n".join(lines) + "\n  FALLO: no se lee throttle (offset invalido?)."

    if speed < 2.0 and thr > 0.5:
        return (
            False,
            "\n".join(lines)
            + "\n  FALLO: throttle alto parado — offset incorrecto para este camion.",
        )

    return True, "\n".join(lines) + "\n  OK preflight gas/RPM."


def preflight_only() -> int:
    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo")
        return 1
    h, base, _ = opened
    try:
        ok, msg = preflight_check(h, base)
        print(msg)
        return 0 if ok else 1
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)


def verify_only() -> int:
    ref = mh.load_offsets_reference()
    cands = (ref.get("drive_runtime") or {}).get("candidates") or {}
    thr_spec = cands.get("throttle_f32")
    rpm_spec = cands.get("engine_rpm_f32")
    if not thr_spec:
        print("throttle_f32 sin calibrar — ejecuta: grabar_telemetria.bat drive_cal")
        return 1

    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo")
        return 1
    h, base, _ = opened
    try:
        sample = mh.read_active_sample(h, base) or {}
        veh_ptr = _vehicle_ptr_from_sample(sample)
        ok, msg = verify_throttle_rpm(
            h,
            base,
            thr_spec,
            rpm_spec,
            interactive=True,
            poll=True,
            veh_ptr=veh_ptr,
        )
        print(msg)
        return 0 if ok else 1
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)


def from_snaps(name_off: str, name_full: str, *, apply: bool, verify_live: bool) -> int:
    off_snap = _load_snap(name_off)
    full_snap = _load_snap(name_full)
    if off_snap.get("vehicle_id") != full_snap.get("vehicle_id"):
        print(
            f"AVISO: vehiculos distintos {off_snap.get('vehicle_id')} vs {full_snap.get('vehicle_id')}"
        )
    thr_ranked = rank_throttle_candidates(
        _floats_from_snap(off_snap, "floats_throttle"),
        _floats_from_snap(full_snap, "floats_throttle"),
    )
    rpm_ranked = rank_rpm_candidates(
        _floats_from_snap(off_snap, "floats_rpm"),
        _floats_from_snap(full_snap, "floats_rpm"),
    )
    if not thr_ranked:
        print("Sin candidato throttle en snapshots.")
        return 1
    print("Throttle candidatos:")
    for row in thr_ranked[:5]:
        print(f"  {_offset_fmt(row[1])}: {row[2]} -> {row[3]}")
    thr_spec = _spec_from_key(thr_ranked[0][1])
    rpm_spec = _spec_dict(*rpm_ranked[0][1]) if rpm_ranked else None
    if rpm_ranked:
        print("RPM:", _offset_fmt(rpm_ranked[0][1]), rpm_ranked[0][2], "->", rpm_ranked[0][3])

    if apply:
        path = apply_candidates(
            thr_spec,
            rpm_spec,
            vehicle_id=str(off_snap.get("vehicle_id") or ""),
            snap_note=f"from {name_off}/{name_full}",
        )
        print(f"Guardado {path}")
    if verify_live:
        return verify_only()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrar y verificar throttle/RPM CE")
    parser.add_argument("--interactive", action="store_true", help="Flujo guiado en juego")
    parser.add_argument("--verify", action="store_true", help="Verificar offsets (gas off/full interactivo)")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Comprobacion rapida sin prompts (grabacion)",
    )
    parser.add_argument(
        "--from-snaps",
        nargs=2,
        metavar=("OFF", "FULL"),
        help="Analizar snapshots drive_snaps/ (sin juego)",
    )
    parser.add_argument("--apply", action="store_true", help="Con --from-snaps: escribir offsets")
    parser.add_argument(
        "--verify-live",
        action="store_true",
        help="Con --from-snaps --apply: verificar en juego despues",
    )
    args = parser.parse_args()

    if args.preflight:
        return preflight_only()
    if args.verify:
        return verify_only()
    if args.from_snaps:
        return from_snaps(args.from_snaps[0], args.from_snaps[1], apply=args.apply, verify_live=args.verify_live)
    if args.interactive or len(sys.argv) == 1:
        return interactive_calibrate()
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
