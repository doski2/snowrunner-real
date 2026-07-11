"""Busqueda de offset pedal (mando / teclado) en memoria CE.

El input del jugador suele estar en TRUCK_CONTROL (singleton o hijos), no en
vehicle+760 (demanda motor). Escanea f32 0..1, f32 0..100 y u8 0..255.
"""

from __future__ import annotations

import os
import sys
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(__file__))
import memoria_havok as mh  # noqa: E402

MemKey = tuple[str, int, str]  # label, offset, kind

# Rangos por tipo de bloque
SCAN_END: dict[str, int] = {
    "truck_control": 0x800,
    "drive_logic": 0x400,
    "vehicle": 0xC00,
    "child": 0x600,
}


@dataclass(frozen=True)
class ScanTarget:
    """Bloque de memoria a escanear (singleton o puntero hijo)."""

    label: str
    ptr: int
    scan_end: int
    parent: str = ""
    parent_off: int = 0


def _valid_ptr(ptr: int | None) -> bool:
    return bool(ptr and ptr > 0x10000)


def enumerate_scan_targets(h: int, base: int, veh_ptr: int) -> list[ScanTarget]:
    """TRUCK_CONTROL + punteros hijos (+0x8, +0x10...) + DRIVE_LOGIC + vehicle."""
    targets: list[ScanTarget] = []
    seen: set[int] = set()

    def add(
        label: str,
        ptr: int,
        scan_end: int,
        *,
        parent: str = "",
        parent_off: int = 0,
    ) -> None:
        if not _valid_ptr(ptr) or ptr in seen:
            return
        seen.add(ptr)
        targets.append(
            ScanTarget(
                label=label,
                ptr=ptr,
                scan_end=scan_end,
                parent=parent,
                parent_off=parent_off,
            )
        )

    tc = mh.read_u64(h, base + mh.TRUCK_CONTROL_OFF)
    if _valid_ptr(tc):
        add("truck_control", tc, SCAN_END["truck_control"])
        for off in range(0, 0x200, 8):
            child = mh.read_u64(h, tc + off)
            if not _valid_ptr(child):
                continue
            if off == mh.OFF_VEH_TRUCK:
                lbl = "tc+008→vehicle"
            else:
                lbl = f"tc+{off:03X}"
            add(lbl, child, SCAN_END["child"], parent="truck_control", parent_off=off)

    dl, dl_veh, _ = mh.resolve_drive_logic(h, base)
    if _valid_ptr(dl):
        add("drive_logic", dl, SCAN_END["drive_logic"])
        for off in range(0, 0x80, 8):
            child = mh.read_u64(h, dl + off)
            if not _valid_ptr(child):
                continue
            if off == mh.OFF_VEH_DRIVE:
                lbl = "dl+020→vehicle"
            else:
                lbl = f"dl+{off:03X}"
            add(lbl, child, SCAN_END["child"], parent="drive_logic", parent_off=off)

    if _valid_ptr(veh_ptr):
        add("vehicle", veh_ptr, SCAN_END["vehicle"])
    elif _valid_ptr(dl_veh):
        add("vehicle", dl_veh, SCAN_END["vehicle"])

    return targets


def get_scan_bases(h: int, base: int, veh_ptr: int) -> dict[str, int]:
    """Compat: label → ptr (ultimo gana si hay duplicados de label)."""
    return {t.label: t.ptr for t in enumerate_scan_targets(h, base, veh_ptr)}


def describe_targets(h: int, base: int, veh_ptr: int) -> list[str]:
    lines: list[str] = []
    for t in enumerate_scan_targets(h, base, veh_ptr):
        extra = ""
        if t.parent:
            extra = f"  (desde {t.parent}+0x{t.parent_off:03X})"
        lines.append(f"  {t.label:18} ptr={t.ptr:#x}  scan=0x0..0x{t.scan_end:X}{extra}")
    return lines


def ce_guide_for_row(row: dict[str, Any], *, exe_base_note: str = "SnowRunner.exe") -> str:
    """Pasos Cheat Engine para validar un candidato a mano."""
    label = row["base"]
    off = row["offset"]
    kind = row.get("kind", "f32")
    addr = ""
    for t in row.get("_targets") or []:
        if t.label == label:
            addr = f"{t.ptr + off:#x}"
            break
    addr_line = f"  Direccion live: {addr}" if addr else "  (pulsa Bases para ver punteros)"
    return (
        f"Candidato: {label}+0x{off:03X} ({kind})\n"
        f"{addr_line}\n\n"
        "En Cheat Engine:\n"
        f"  1. Memory View → Goto address (arriba)\n"
        f"  2. Tipo: {'Float' if kind == 'f32' else 'Byte'} — mando 0% vs 25%\n"
        "  3. Click derecho → Find out what WRITES to this address\n"
        "  4. Mueve solo el gas del mando: si escribe aqui, es el pedal.\n\n"
        f"  RTTI: [{exe_base_note}] buscar TRUCK_CONTROL / combine@\n"
        "  Doc: github.com/FindMuck/SnowRunner_Noclip mappings.md"
    )


def _norm_f32(v: float) -> float | None:
    if v != v or abs(v) > 1e6:
        return None
    if -0.02 <= v <= 1.05:
        return max(0.0, min(1.0, v))
    if 1.05 < v <= 100.0:
        return max(0.0, min(1.0, v / 100.0))
    return None


def _norm_u8(u: int) -> float | None:
    if u < 0 or u > 255:
        return None
    return u / 255.0


def _ptr_for_label(targets: list[ScanTarget], label: str) -> int | None:
    for t in targets:
        if t.label == label:
            return t.ptr
    return None


def read_at(h: int, base: int, veh_ptr: int, base_name: str, offset: int) -> float | None:
    targets = enumerate_scan_targets(h, base, veh_ptr)
    ptr = _ptr_for_label(targets, base_name)
    if not ptr:
        return None
    v = mh.read_f32(h, ptr + offset)
    if v is not None:
        n = _norm_f32(v)
        if n is not None:
            return n
    u = mh.read_u8(h, ptr + offset)
    if u is not None:
        return _norm_u8(u)
    return None


def capture_pedal_map(h: int, base: int, veh_ptr: int) -> dict[MemKey, float]:
    """Snapshot normalizado 0..1 en todos los bloques (incl. hijos de TC/DL)."""
    snap: dict[MemKey, float] = {}
    for t in enumerate_scan_targets(h, base, veh_ptr):
        for off in range(0, t.scan_end, 4):
            v = mh.read_f32(h, t.ptr + off)
            n = _norm_f32(v) if v is not None else None
            if n is not None:
                snap[(t.label, off, "f32")] = n
            u = mh.read_u8(h, t.ptr + off)
            nu = _norm_u8(u) if u is not None else None
            if nu is not None and nu > 0.001:
                snap[(t.label, off, "u8")] = nu
    return snap


def diff_pedal_maps(
    snap_a: dict[MemKey, float],
    snap_b: dict[MemKey, float],
    *,
    target_delta: float | None = None,
    min_delta: float = 0.04,
    limit: int = 15,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = set(snap_a) & set(snap_b)
    for key in keys:
        v0, v1 = snap_a[key], snap_b[key]
        delta = v1 - v0
        if abs(delta) < min_delta:
            continue
        score = abs(delta - target_delta) if target_delta is not None else -abs(delta)
        label, off, kind = key
        tag = f"{label[:6]}{off:03X}{kind[0]}"
        rows.append(
            {
                "key": key,
                "tag": tag,
                "base": label,
                "offset": off,
                "kind": kind,
                "v0": v0,
                "v1": v1,
                "delta": delta,
                "score": score,
            }
        )
    if target_delta is not None:
        rows.sort(key=lambda r: (r["score"], -abs(r["delta"])))
    else:
        rows.sort(key=lambda r: -abs(r["delta"]))
    return rows[:limit]


def hunt_near_target(
    h: int,
    base: int,
    veh_ptr: int,
    target: float,
    *,
    tolerance: float = 0.07,
    limit: int = 12,
) -> list[dict[str, Any]]:
    snap = capture_pedal_map(h, base, veh_ptr)
    rows: list[dict[str, Any]] = []
    for key, val in snap.items():
        err = abs(val - target)
        if err > tolerance:
            continue
        label, off, kind = key
        rows.append(
            {
                "key": key,
                "tag": f"{label[:6]}{off:03X}{kind[0]}",
                "base": label,
                "offset": off,
                "kind": kind,
                "value": val,
                "err": err,
                "target": target,
            }
        )
    rows.sort(key=lambda r: r["err"])
    return rows[:limit]


def attach_targets(
    rows: list[dict[str, Any]], h: int, base: int, veh_ptr: int
) -> list[dict[str, Any]]:
    targets = enumerate_scan_targets(h, base, veh_ptr)
    for row in rows:
        row["_targets"] = targets
    return rows


def spec_from_hunt_row(row: dict[str, Any]) -> dict[str, str]:
    spec: dict[str, str] = {
        "base": row["base"],
        "offset": f"+0x{row['offset']:03X}",
        "kind": row.get("kind", "f32"),
    }
    if row["base"].startswith("tc"):
        spec["chain"] = "TRUCK_CONTROL"
    elif row["base"].startswith("dl"):
        spec["chain"] = "DRIVE_LOGIC"
    elif row["base"] == "vehicle":
        spec["chain"] = "TRUCK_CONTROL+8"
    return spec


def format_hunt_row(row: dict[str, Any]) -> str:
    if "delta" in row:
        return (
            f"{row['base']}+0x{row['offset']:03X} ({row['kind']}) "
            f"{row['v0']:.3f} -> {row['v1']:.3f}  d={row['delta']:+.3f}"
        )
    return (
        f"{row['base']}+0x{row['offset']:03X} ({row['kind']}) "
        f"= {row['value']:.3f}"
    )


LOW_THRESH = 0.12
HIGH_THRESH = 0.85
MOTOR_OFF = 0x760


@dataclass
class KeySweepStats:
    """Min/max y conteos durante barrido 0%% <-> 100%%."""

    vmin: float = 1.0
    vmax: float = 0.0
    n_samples: int = 0
    n_low: int = 0
    n_high: int = 0
    last: float = 0.0

    def push(self, value: float) -> None:
        self.n_samples += 1
        self.last = value
        if value < self.vmin:
            self.vmin = value
        if value > self.vmax:
            self.vmax = value
        if value <= LOW_THRESH:
            self.n_low += 1
        if value >= HIGH_THRESH:
            self.n_high += 1

    @property
    def span(self) -> float:
        return self.vmax - self.vmin


def update_sweep_stats(
    stats: dict[MemKey, KeySweepStats], snap: dict[MemKey, float]
) -> None:
    for key, val in snap.items():
        stats.setdefault(key, KeySweepStats()).push(val)


def _sweep_base_priority(label: str, offset: int) -> float:
    """Mayor = mejor candidato pedal (input jugador)."""
    if label.startswith("tc+") and "vehicle" not in label:
        return 3.0
    if label == "truck_control":
        return 2.5
    if label.startswith("dl+") and "vehicle" not in label:
        return 2.0
    if label == "drive_logic":
        return 1.5
    if label == "vehicle" and offset == MOTOR_OFF:
        return -2.0
    if label == "vehicle":
        return 0.5
    return 1.0


def rank_pedal_sweep(
    stats: dict[MemKey, KeySweepStats],
    *,
    min_span: float = 0.35,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Candidatos que pasaron por ~0 y ~1 durante el barrido."""
    rows: list[dict[str, Any]] = []
    for key, st in stats.items():
        span = st.span
        if span < min_span:
            continue
        if st.n_low < 1 or st.n_high < 1:
            continue
        if st.vmin > 0.25 and st.vmax < 0.55:
            continue
        label, off, kind = key
        score = span
        score += min(st.n_low, 8) * 0.02
        score += min(st.n_high, 8) * 0.02
        score += max(0.0, 0.2 - st.vmin)
        score += max(0.0, st.vmax - 0.75)
        score += _sweep_base_priority(label, off)
        if st.vmin > 0.9 and st.vmax > 0.95:
            score -= 3.0
        rows.append(
            {
                "key": key,
                "tag": f"{label[:6]}{off:03X}{kind[0]}",
                "base": label,
                "offset": off,
                "kind": kind,
                "vmin": st.vmin,
                "vmax": st.vmax,
                "span": span,
                "n_low": st.n_low,
                "n_high": st.n_high,
                "n_samples": st.n_samples,
                "last": st.last,
                "score": score,
            }
        )
    rows.sort(key=lambda r: (-r["score"], -r["span"]))
    return rows[:limit]


def record_pedal_sweep(
    h: int,
    base: int,
    veh_ptr: int,
    *,
    duration_s: float = 5.0,
    interval_s: float = 0.08,
    progress_cb: Callable[[float, int], None] | None = None,
) -> tuple[dict[MemKey, KeySweepStats], int]:
    """Muestrea memoria durante duration_s sin pedir ENTER (mando en juego)."""
    stats: dict[MemKey, KeySweepStats] = {}
    t0 = time.monotonic()
    n = 0
    while True:
        elapsed = time.monotonic() - t0
        if elapsed >= duration_s:
            break
        snap = capture_pedal_map(h, base, veh_ptr)
        update_sweep_stats(stats, snap)
        n += 1
        if progress_cb:
            progress_cb(elapsed, n)
        sleep_left = interval_s - (time.monotonic() - t0 - elapsed)
        if sleep_left > 0:
            time.sleep(sleep_left)
    return stats, n


def format_sweep_row(row: dict[str, Any]) -> str:
    return (
        f"{row['base']}+0x{row['offset']:03X} ({row['kind']}) "
        f"min={row['vmin']:.3f} max={row['vmax']:.3f} span={row['span']:.3f} "
        f"low={row['n_low']} high={row['n_high']} score={row['score']:.2f}"
    )


def sweep_report_to_jsonable(
    rows: list[dict[str, Any]],
    *,
    veh_id: str,
    duration_s: float,
    n_samples: int,
    rejected_motor: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    def row_json(r: dict[str, Any]) -> dict[str, Any]:
        return {
            "base": r["base"],
            "offset": f"+0x{r['offset']:03X}",
            "kind": r["kind"],
            "vmin": round(r["vmin"], 4),
            "vmax": round(r["vmax"], 4),
            "span": round(r["span"], 4),
            "score": round(r["score"], 3),
            "spec": spec_from_hunt_row(r),
        }

    return {
        "vehicle_id": veh_id,
        "duration_s": duration_s,
        "n_samples": n_samples,
        "candidates": [row_json(r) for r in rows],
        "rejected_motor_stuck": [row_json(r) for r in (rejected_motor or [])],
    }


def save_sweep_report(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def dump_bases_cli(h: int, base: int, veh_ptr: int) -> None:
    print("=== Bases escaneo pedal (profundo) ===")
    print(f"TRUCK_CONTROL slot: {base + mh.TRUCK_CONTROL_OFF:#x}")
    print(f"DRIVE_LOGIC slot:     {base + mh.DRIVE_LOGIC_OFF:#x}")
    for line in describe_targets(h, base, veh_ptr):
        print(line)
    print("\nPrioridad: tc+XXX (hijos) antes que vehicle+760 (motor).")
