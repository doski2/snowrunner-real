"""Traccion, diferencial, marcha y tasa de combustible (CE en vivo).

Calibracion offsets (build jun-2026):
  1. Mapa, quieto: python cheat_engine/scan_drive_state.py --discover
  2. Diff OFF -> --save diff_off
  3. Diff ON  -> --save diff_on
  4. python cheat_engine/scan_drive_state.py --diff diff_off diff_on
  5. Anotar offset en cheat_engine/offsets_referencia.json -> drive_runtime.candidates

Uso rapido:
  python cheat_engine/scan_drive_state.py
  python cheat_engine/scan_drive_state.py --watch 30
  grabar_telemetria.bat drive
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import memoria_havok as mh  # noqa: E402


def snapshot(h: int, base: int) -> dict:
    sample = mh.read_active_sample(h, base)
    if not sample:
        return {"error": "sin vehiculo activo (mapa conduciendo)"}
    veh = int(sample["veh"], 16)
    drive = mh.read_drive_state(h, base, veh)
    mh.update_fuel_rate(sample, 0.0)
    return {
        "vehicle_id": sample.get("vehicle_id"),
        "speed_kmh": sample.get("speed_kmh"),
        "fuel_pct": sample.get("fuel_pct"),
        "veh": sample["veh"],
        **drive,
    }


def _print_snapshot(data: dict) -> None:
    print(f"id={data.get('vehicle_id')} km/h={data.get('speed_kmh')} fuel={data.get('fuel_pct') or '-'}%")
    cat = data.get("diff_lock_catalog") or "-"
    print(f"  catalog diff: {cat}  awd_mod_xml={data.get('gearbox_awd_modifier_xml') or '-'}")
    print(f"  live diff={data.get('diff_lock_live') or '?'} awd={data.get('awd_live') or '?'} "
          f"L={data.get('low_gear_live') or '?'} throttle={data.get('throttle') or '?'} "
          f"rpm={data.get('engine_rpm') or '?'}")
    if data.get("fuel_rate_pct_min"):
        print(f"  fuel_rate={data['fuel_rate_pct_min']} %/min")


def _compare_discover_snaps(a: dict, b: dict, label_a: str, label_b: str) -> None:
    print(f"Diff discover {label_a} vs {label_b}:")
    print(f"  vehicle: {a.get('vehicle_id')} vs {b.get('vehicle_id')}")
    if a.get("vehicle_id") != b.get("vehicle_id"):
        print("  AVISO: vehiculos distintos — repite los 3 snaps con el mismo camion")
    ua = {(r["base"], r["offset"]): r["u8"] for r in a.get("flags_u8", [])}
    ub = {(r["base"], r["offset"]): r["u8"] for r in b.get("flags_u8", [])}
    u8chg = [(k, ua[k], ub[k]) for k in ua if k in ub and ua[k] != ub[k]]
    print(f"  u8 changed: {len(u8chg)}")
    for k, v0, v1 in u8chg[:25]:
        print(f"    {k[0]}{k[1]}: {v0} -> {v1}")
    if len(u8chg) > 25:
        print(f"    ... +{len(u8chg) - 25} mas")
    fa = {(r["base"], r["offset"]): r["f"] for r in a.get("floats_throttle", [])}
    fb = {(r["base"], r["offset"]): r["f"] for r in b.get("floats_throttle", [])}
    fchg = [(k, fa[k], fb[k]) for k in fa if k in fb and abs(fa[k] - fb[k]) > 0.01]
    fchg.sort(key=lambda x: -abs(x[1] - x[2]))
    print(f"  float throttle changed (>0.01): {len(fchg)}")
    for k, v0, v1 in fchg[:10]:
        print(f"    {k[0]}{k[1]}: {v0} -> {v1}")
    ra = {(r["base"], r["offset"]): r["f"] for r in a.get("floats_rpm", [])}
    rb = {(r["base"], r["offset"]): r["f"] for r in b.get("floats_rpm", [])}
    rchg = [(k, ra[k], rb[k]) for k in ra if k in rb and abs(ra[k] - rb[k]) > 5]
    print(f"  rpm changed (>5): {len(rchg)}")
    for k, v0, v1 in rchg[:5]:
        print(f"    {k[0]}{k[1]}: {v0} -> {v1}")


def _print_discover(data: dict) -> None:
    print(f"Discover {data.get('vehicle_id')} @ {data.get('speed_kmh')} km/h "
          f"fuel={data.get('fuel_pct') or '-'}% chain={data.get('drive_chain')}")
    print("\n-- flags u8 (0/1) — togglear diff/L y repetir --discover --")
    for row in data.get("flags_u8", [])[:25]:
        print(f"  {row['base']}{row['offset']} = {row['u8']}")
    if len(data.get("flags_u8", [])) > 25:
        print(f"  ... +{len(data['flags_u8']) - 25} mas")
    print("\n-- floats throttle 0..1 --")
    for row in data.get("floats_throttle", [])[:15]:
        print(f"  {row['base']}{row['offset']} = {row['f']}")
    print("\n-- floats rpm 100..8000 --")
    for row in data.get("floats_rpm", [])[:15]:
        print(f"  {row['base']}{row['offset']} = {row['f']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Traccion/diff/marcha CE + fuel rate")
    parser.add_argument("--save", metavar="NAME", help="Guardar en cheat_engine/drive_snaps/")
    parser.add_argument("--diff", nargs=2, metavar=("A", "B"), help="Comparar snapshots")
    parser.add_argument("--discover", action="store_true", help="Listar candidatos u8/float")
    parser.add_argument("--watch", type=float, metavar="SEC", help="Poll cada 0.5s N segundos")
    args = parser.parse_args()

    snap_dir = os.path.join(os.path.dirname(__file__), "drive_snaps")
    os.makedirs(snap_dir, exist_ok=True)

    if args.diff:
        pa = os.path.join(snap_dir, f"{args.diff[0]}.json")
        pb = os.path.join(snap_dir, f"{args.diff[1]}.json")
        with open(pa, encoding="utf-8") as f:
            a = json.load(f)
        with open(pb, encoding="utf-8") as f:
            b = json.load(f)
        if a.get("flags_u8") or b.get("flags_u8"):
            _compare_discover_snaps(a, b, args.diff[0], args.diff[1])
        else:
            print(f"Diff {args.diff[0]} vs {args.diff[1]}:")
            for key in (
                "diff_lock_live",
                "awd_live",
                "low_gear_live",
                "throttle",
                "engine_rpm",
                "fuel_pct",
                "diff_lock_catalog",
            ):
                print(f"  {key}: {a.get(key)!r} -> {b.get(key)!r}")
        return 0

    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo")
        return 1
    h, base, pid = opened
    try:
        if args.discover:
            data = mh.discover_drive_candidates(h, base)
            _print_discover(data)
            if args.save:
                path = os.path.join(snap_dir, f"{args.save}.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                print(f"\nGuardado: {path}")
            return 0

        if args.watch:
            mh._FUEL_RATE_TRACKER.reset()
            t0 = time.monotonic()
            print(f"Watch {args.watch:.0f}s (PID={pid}) — diff/L/gas; fuel_rate en %/min")
            while time.monotonic() - t0 < args.watch:
                sample = mh.read_active_sample(h, base)
                if not sample:
                    print("  sin vehiculo")
                    time.sleep(0.5)
                    continue
                t_el = time.monotonic() - t0
                mh.enrich_drive_fields(h, base, sample, t_s=t_el)
                _print_snapshot(sample)
                time.sleep(0.5)
            return 0

        data = snapshot(h, base)
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)

    if "error" in data:
        print(data["error"])
        return 1

    print(f"PID={pid}")
    _print_snapshot(data)
    ref = mh.load_offsets_reference()
    cands = (ref.get("drive_runtime") or {}).get("candidates") or {}
    thr = cands.get("throttle_f32")
    rpm = cands.get("engine_rpm_f32")
    live_missing = not any(data.get(k) for k in ("diff_lock_live", "awd_live", "low_gear_live"))
    if thr:
        print(f"\nthrottle_f32: {thr['base']}{thr['offset']}")
    else:
        print("\nthrottle_f32 sin calibrar — .\\grabar_telemetria.bat drive_cal")
    if rpm:
        print(f"engine_rpm_f32: {rpm['base']}{rpm['offset']}")
    if live_missing:
        print("diff/L/AWD live sin calibrar — drive_snap + drive_diff (ver README)")

    if args.save:
        path = os.path.join(snap_dir, f"{args.save}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nGuardado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
