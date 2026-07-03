"""Estado de carga del vehiculo activo (remolque + cargo en bastidor).

Calibracion:
  python cheat_engine/scan_cargo.py --save vacio
  # engancha remolque o carga bastidor
  python cheat_engine/scan_cargo.py --save cargado
  python cheat_engine/scan_cargo.py --diff vacio cargado
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import memoria_havok as mh  # noqa: E402


def snapshot(h: int, base: int) -> dict:
    sample = mh.read_active_sample(h, base)
    if not sample:
        return {"error": "sin vehiculo activo (mapa conduciendo)"}
    veh = int(sample["veh"], 16)
    load = mh.read_vehicle_load(h, veh)
    return {
        "vehicle_id": sample.get("vehicle_id"),
        "speed_kmh": sample.get("speed_kmh"),
        "veh": sample["veh"],
        **load,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Leer carga/remolque del vehiculo activo")
    parser.add_argument("--save", metavar="NAME", help="Guardar JSON en cheat_engine/load_snaps/")
    parser.add_argument("--diff", nargs=2, metavar=("A", "B"), help="Comparar dos snapshots")
    args = parser.parse_args()

    snap_dir = os.path.join(os.path.dirname(__file__), "load_snaps")
    os.makedirs(snap_dir, exist_ok=True)

    if args.diff:
        pa = os.path.join(snap_dir, f"{args.diff[0]}.json")
        pb = os.path.join(snap_dir, f"{args.diff[1]}.json")
        with open(pa, encoding="utf-8") as f:
            a = json.load(f)
        with open(pb, encoding="utf-8") as f:
            b = json.load(f)
        print(f"Diff {args.diff[0]} vs {args.diff[1]}:")
        for key in (
            "load_hint",
            "trailer_id",
            "cargo_mass_kg",
            "payload_kg",
            "total_mass_kg",
            "empty_mass_kg",
            "trailer_mass_kg",
            "cargo_types",
        ):
            print(f"  {key}: {a.get(key)!r} -> {b.get(key)!r}")
        return 0

    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo")
        return 1
    h, base, pid = opened
    try:
        data = snapshot(h, base)
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)

    if "error" in data:
        print(data["error"])
        return 1

    print(f"PID={pid} id={data['vehicle_id']} km/h={data['speed_kmh']}")
    print(f"  load_hint: {data.get('load_hint')}")
    print(f"  trailer_id: {data.get('trailer_id') or '-'}")
    print(f"  total_mass_kg: {data.get('total_mass_kg') or '-'}")
    print(f"  empty_mass_kg: {data.get('empty_mass_kg') or '-'}")
    print(f"  payload_kg: {data.get('payload_kg') or '-'}")
    print(f"  cargo_mass_kg: {data.get('cargo_mass_kg')}")
    print(f"  trailer_mass_kg: {data.get('trailer_mass_kg') or '-'}")
    print(f"  cargo_types: {data.get('cargo_types') or '-'}")
    if data.get("packed_cargo_slots"):
        print(f"  packed_slots: {data.get('packed_cargo_slots')} ({data.get('packed_cargo_bones') or '-'})")
    if data.get("frame_addon"):
        print(f"  frame_addon: {data.get('frame_addon')}")
    if data.get("packed_cargo_bones"):
        print(f"  packed_cargo_bones: {data.get('packed_cargo_bones')}")
    if data.get("attached_cargo_mass_kg"):
        print(f"  attached_cargo_mass_kg: {data.get('attached_cargo_mass_kg')}")

    if args.save:
        path = os.path.join(snap_dir, f"{args.save}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nGuardado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
