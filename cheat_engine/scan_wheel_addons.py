"""Neumaticos montados del vehiculo activo (lectura CE en vivo).

Fuente principal: TRUCK_WHEEL_MODEL [veh+200]
  - +0x140: wheels_scout2 / wheels_medium_double (tipo XML)
  - +0x124: fragmento nombre UI ("... AT I" = allterrain, "... OS I" = offroad)

Uso:
  python cheat_engine/scan_wheel_addons.py
  python cheat_engine/scan_wheel_addons.py --save offroad_ck1500
  python cheat_engine/scan_wheel_addons.py --diff offroad_ck1500 allterrain_ck1500
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
    tires = mh.read_mounted_tires(h, veh)
    return {
        "speed_kmh": sample.get("speed_kmh"),
        "veh": sample["veh"],
        **tires,
    }


def _load_snap(path: str) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Leer neumaticos montados del vehiculo activo")
    parser.add_argument("--save", metavar="NAME", help="Guardar JSON en cheat_engine/wheel_addon_snaps/")
    parser.add_argument("--diff", nargs=2, metavar=("A", "B"), help="Comparar dos snapshots guardados")
    args = parser.parse_args()

    snap_dir = os.path.join(os.path.dirname(__file__), "wheel_addon_snaps")
    os.makedirs(snap_dir, exist_ok=True)

    if args.diff:
        pa = os.path.join(snap_dir, f"{args.diff[0]}.json")
        pb = os.path.join(snap_dir, f"{args.diff[1]}.json")
        try:
            a = _load_snap(pa)
            b = _load_snap(pb)
        except FileNotFoundError as exc:
            print(f"No existe snapshot: {exc.filename}")
            print(f"Carpeta: {snap_dir}")
            print("Guarda antes con: python cheat_engine/scan_wheel_addons.py --save <nombre>")
            return 1
        print(f"Diff {args.diff[0]} vs {args.diff[1]}:")
        for key in (
            "vehicle_id",
            "wheel_type_xml",
            "tire_label_raw",
            "tire_kind",
            "tire_mixed",
            "wheel_count",
        ):
            print(f"  {key}: {a.get(key)!r} -> {b.get(key)!r}")
        ids_a = set(a.get("tire_game_ids") or [])
        ids_b = set(b.get("tire_game_ids") or [])
        only_a = sorted(ids_a - ids_b)
        only_b = sorted(ids_b - ids_a)
        if only_a:
            print(f"  solo en A: {only_a}")
        if only_b:
            print(f"  solo en B: {only_b}")
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

    print(f"PID={pid} veh={data['veh']} id={data['vehicle_id']} km/h={data['speed_kmh']}")
    print(f"  ruedas TRUCK_WHEEL_MODEL: {data.get('wheel_count')}")
    if data.get("wheel_type_xml"):
        print(f"  wheel_type_xml: {data.get('wheel_type_xml')}")
    if data.get("tire_label_raw"):
        print(f"  tire_label_raw: {data.get('tire_label_raw')!r}")
    print(f"  tire_kind (CE): {data.get('tire_kind')}")
    if data.get("tire_mixed"):
        print("  aviso: varios tipos detectados — revisar tire_hits")
    ids = data.get("tire_game_ids") or []
    if ids:
        print(f"  tire_game_ids ({len(ids)}):")
        for gid in ids:
            print(f"    - {gid}  [{mh.classify_tire_kind(gid)}]")
    else:
        print("  tire_game_ids: (ninguno)")

    hits = data.get("tire_hits") or []
    if hits:
        print("  fuentes:")
        for row in hits[:12]:
            label = row.get("label_raw")
            extra = f" label={label!r}" if label else ""
            print(f"    {row.get('game_id')} [{row.get('tire_kind')}] <- {row.get('source')}{extra}")

    if args.save:
        path = os.path.join(snap_dir, f"{args.save}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nGuardado: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
