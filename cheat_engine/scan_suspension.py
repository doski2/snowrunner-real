"""Sondeo CE suspension — buscar offsets runtime (Strength/Damping no expuestos aun).

Hipotesis (Fase 6 / mappings.md):
  - Chasis: hkpRigidBody pos_y (+0x1A4) — ya en telemetria_ce_log.csv
  - Rueda: TRUCK_WHEEL_MODEL — recorrido/compresion en floats desconocidos
  - Addon +0x1F8 / +0x210 — elementos mecanicos (pistones)

Protocolo de estudio:
  1. Mapa, camion vacio, quieto -> python scan_suspension.py --save vacio
  2. Misma postura con carga/remolque -> --save cargado
  3. Pasar baden / frenar fuerte -> --save bounce
  4. python scan_suspension.py --diff vacio cargado
  5. python scan_suspension.py --diff vacio bounce

Comparar con suspension_*_xml en catalog_lookup (§2.5).
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import memoria_havok as mh  # noqa: E402

OFF_ADDON = 0x48
OFF_MECH_ELEM_BEGIN = 0x1F8
OFF_MECH_ELEM_END = 0x200
OFF_MECH_RT_BEGIN = 0x210
OFF_MECH_RT_END = 0x218
WHEEL_SCAN_END = 0x400
MECH_RECORD_SIZE = 0x20
SCAN_FLOATS_PER_RECORD = 8


def _u64(h: int, addr: int) -> int | None:
    b = mh.read_bytes(h, addr, 8)
    return struct.unpack("<Q", b)[0] if b else None


def _vector_pointers(h: int, veh: int, begin_off: int, end_off: int, *, max_items: int = 64) -> list[int]:
    begin = _u64(h, veh + begin_off)
    end = _u64(h, veh + end_off)
    if not begin or not end or end < begin:
        return []
    count = min((end - begin) // 8, max_items)
    out: list[int] = []
    for i in range(count):
        p = _u64(h, begin + i * 8)
        if p and p > 0x10000:
            out.append(p)
    return out


def _scan_floats(h: int, base: int, size: int, *, label: str) -> list[dict]:
    floats: list[dict] = []
    for off in range(0, size, 4):
        v = mh.read_f32(h, base + off)
        if v is None or v == 0.0:
            continue
        if not (-80 < v < 80):
            continue
        floats.append({"off": f"+{off:03X}", "f": round(v, 4)})
    return [{"base": label, "floats": floats}] if floats else []


def _mech_runtime_records(h: int, addon: int, *, max_records: int = 12) -> list[dict]:
    begin = _u64(h, addon + OFF_MECH_RT_BEGIN)
    end = _u64(h, addon + OFF_MECH_RT_END)
    if not begin or not end or end < begin:
        return []
    count = min((end - begin) // MECH_RECORD_SIZE, max_records)
    rows: list[dict] = []
    for i in range(count):
        rec = begin + i * MECH_RECORD_SIZE
        vals = []
        for j in range(SCAN_FLOATS_PER_RECORD):
            v = mh.read_f32(h, rec + j * 4)
            if v is not None and v != 0.0 and -80 < v < 80:
                vals.append({"off": f"+{j * 4:03X}", "f": round(v, 4)})
        if vals:
            rows.append({"index": i, "record": hex(rec), "floats": vals})
    return rows


def snapshot(h: int, base: int) -> dict:
    sample = mh.read_active_sample(h, base)
    if not sample:
        return {"error": "sin vehiculo activo (mapa conduciendo)"}
    veh = int(sample["veh"], 16)
    wheels = mh.read_wheel_pointers(h, veh)
    addon = _u64(h, veh + OFF_ADDON)

    wheel_scans = []
    for i, w in enumerate(wheels):
        floats = _scan_floats(h, w, WHEEL_SCAN_END, label=f"wheel_{i}")
        if floats:
            wheel_scans.append({"wheel": hex(w), **floats[0]})

    addon_scans: dict = {}
    if addon:
        addon_scans = {
            "addon": hex(addon),
            "mech_elements": len(_vector_pointers(h, addon, OFF_MECH_ELEM_BEGIN, OFF_MECH_ELEM_END)),
            "mech_runtime": _mech_runtime_records(h, addon),
        }

    return {
        "vehicle_id": sample.get("vehicle_id"),
        "speed_kmh": sample.get("speed_kmh"),
        "pos_y": sample.get("pos_y"),
        "total_mass_kg": sample.get("total_mass_kg"),
        "load_hint": sample.get("load_hint"),
        "wheel_count": len(wheels),
        "wheels": wheel_scans,
        "addon": addon_scans,
        "catalog_note": "Comparar pos_y y floats con suspension_*_xml via catalog_lookup",
    }


def diff_snapshots(a: dict, b: dict) -> list[dict]:
    """Floats que cambian entre snapshots (misma rueda indice)."""
    changes: list[dict] = []
    wa = a.get("wheels") or []
    wb = b.get("wheels") or []
    for i, (ra, rb) in enumerate(zip(wa, wb)):
        fa = {x["off"]: x["f"] for x in ra.get("floats", [])}
        fb = {x["off"]: x["f"] for x in rb.get("floats", [])}
        for off in set(fa) | set(fb):
            va, vb = fa.get(off), fb.get(off)
            if va is None or vb is None:
                continue
            if abs(vb - va) > 0.001:
                changes.append(
                    {
                        "wheel": i,
                        "off": off,
                        "a": va,
                        "b": vb,
                        "delta": round(vb - va, 4),
                    }
                )
    py_a = a.get("pos_y")
    py_b = b.get("pos_y")
    if py_a is not None and py_b is not None and abs(float(py_b) - float(py_a)) > 0.001:
        changes.insert(
            0,
            {
                "wheel": "chasis",
                "off": "pos_y",
                "a": py_a,
                "b": py_b,
                "delta": round(float(py_b) - float(py_a), 4),
            },
        )
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sonar floats suspension (ruedas + addon mecanico)")
    parser.add_argument("--save", metavar="NAME", help="Guardar JSON en cheat_engine/suspension_snaps/")
    parser.add_argument("diff_names", nargs="*", help="Con --diff: NAME_A NAME_B")
    parser.add_argument("--diff", action="store_true", help="Comparar dos snapshots guardados")
    args = parser.parse_args(argv)

    snap_dir = os.path.join(os.path.dirname(__file__), "suspension_snaps")
    os.makedirs(snap_dir, exist_ok=True)

    if args.diff:
        if len(args.diff_names) != 2:
            print("Uso: python scan_suspension.py --diff vacio cargado")
            return 1
        pa = os.path.join(snap_dir, f"{args.diff_names[0]}.json")
        pb = os.path.join(snap_dir, f"{args.diff_names[1]}.json")
        with open(pa, encoding="utf-8") as f:
            sa = json.load(f)
        with open(pb, encoding="utf-8") as f:
            sb = json.load(f)
        print(f"Diff {args.diff_names[0]} -> {args.diff_names[1]} ({sa.get('vehicle_id')})")
        for row in diff_snapshots(sa, sb):
            print(
                f"  {row.get('wheel')} {row['off']}: {row['a']} -> {row['b']} (d={row['delta']})"
            )
        return 0

    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no esta corriendo.")
        return 1
    h, base, _pid = opened
    try:
        data = snapshot(h, base)
    finally:
        import ctypes

        ctypes.windll.kernel32.CloseHandle(h)

    if data.get("error"):
        print(data["error"])
        return 1

    print(f"vehiculo: {data.get('vehicle_id')}  speed={data.get('speed_kmh')} km/h")
    print(f"  pos_y={data.get('pos_y')}  masa={data.get('total_mass_kg')} kg  load={data.get('load_hint')}")
    print(f"  ruedas: {data.get('wheel_count')}")
    if data.get("addon"):
        ad = data["addon"]
        print(f"  addon {ad.get('addon')} mech_elems={ad.get('mech_elements')} runtime_rows={len(ad.get('mech_runtime', []))}")

    if args.save:
        path = os.path.join(snap_dir, f"{args.save}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Guardado: {path}")
    else:
        print("Tip: --save vacio | cargado | bounce  luego  --diff vacio cargado")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
