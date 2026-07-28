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


def _print_probe(data: dict) -> None:
    print(f"vehicle_id={data.get('vehicle_id')} veh={data.get('veh')}")
    print(f"  empty_mass_kg: {data.get('empty_mass_kg')}")
    print(f"  truck_mass_havok_kg: {data.get('truck_mass_havok_kg')} (sane={data.get('truck_mass_sane')})")
    chain = data.get("mass_chain") or {}
    if chain:
        print(
            f"  mass_chain: rb_5d0={chain.get('veh_rb_5d0') or '-'} "
            f"rb_5c8={chain.get('veh_rb_5c8') or '-'} "
            f"mass_5d0={chain.get('mass_kg_5d0')} mass_5c8={chain.get('mass_kg_5c8')}"
        )
        if chain.get("inv_mass_5d0") is not None:
            print(f"    inv_mass_5d0={chain.get('inv_mass_5d0')}")
        inv0 = chain.get("inv_mass_5d0") == 0.0
        sane = data.get("truck_mass_sane")
        if inv0 and not sane:
            print(
                "  AVISO: inv_mass=0 parado - Havok no expone masa. "
                "Mueve el camion o acelera un poco y repite --probe."
            )
    e1 = data.get("expected_loaded_1x_kg")
    e2 = data.get("expected_loaded_2x_kg")
    if e1 is not None and e2 is not None:
        print(
            f"  esperado repuesto 1.2t: 1x ~{e1:.0f} kg | 2x ~{e2:.0f} kg total "
            f"(mod vacio {data.get('empty_mass_kg')})"
        )
    print(f"  attach: {data.get('attach') or '-'}  addon: {data.get('addon') or '-'}")
    print(f"  load_registry: {data.get('load_registry') or '-'}")
    print(f"  frame_addon: {data.get('frame_addon') or '-'}")
    print(f"  packed_slots: {data.get('packed_cargo_slots')}  bones: {data.get('packed_cargo_bones')}")
    print(f"  path_cargo_type: {data.get('path_cargo_type') or '-'}")
    hits = data.get("cargo_string_hits") or []
    if hits:
        print(f"  cargo_string_hits: {' | '.join(hits[:12])}")
        if len(hits) > 12:
            print(f"    ... +{len(hits) - 12} mas")
    elif not data.get("path_cargo_type") and not data.get("packed_cargo_slots"):
        print(
            "  AVISO: sin BoneCargo ni cargo_* en memoria - "
            "calibracion actual = Fleetstar+sideboard; Bandit puede usar otro addon/ruta."
        )
    reg = data.get("registry_cargo_types") or []
    print(f"  registry_types: {'|'.join(reg) if reg else '-'}")
    subs = data.get("attach_cargo_subs") or []
    if subs:
        print("  attach cargo subs:")
        for sub in subs:
            bones = sub.get("bones") or []
            bone_txt = "|".join(bones) if bones else "-"
            print(f"    {sub['off']} -> {sub['ptr']} bones={bone_txt}")
    addon_phys = data.get("addon_phys") or []
    if addon_phys:
        print("  addon_phys vector (+1E0):")
        for entry in addon_phys:
            print(
                f"    {entry['ptr']} mass={entry.get('mass_kg')} id={entry.get('id') or '-'}"
            )
    graph = data.get("cargo_graph_hits") or []
    if graph:
        print("  cargo en grafo veh/addon/attach:")
        for hit in graph:
            print(f"    {hit['path']} id={hit['id']} addr={hit['addr']}")
    island = data.get("island_cargo_candidates") or []
    if island:
        print(
            f"  island cargo candidates ({len(island)}), "
            f"sum={data.get('island_cargo_mass_kg')} kg:"
        )
        for entry in island:
            print(
                f"    {entry['rb']} mass={entry['mass_kg']} id={entry.get('id') or '-'}"
            )
    elif data.get("island_bodies"):
        print(
            f"  simulation island ({len(data.get('island_bodies') or [])} cuerpos, "
            f"cargo_sum={data.get('island_cargo_mass_kg')} kg)"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Leer carga/remolque del vehiculo activo")
    parser.add_argument("--save", metavar="NAME", help="Guardar JSON en cheat_engine/load_snaps/")
    parser.add_argument("--diff", nargs=2, metavar=("A", "B"), help="Comparar dos snapshots")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Diagnostico: island, BoneCargo, load registry, grafo cargo",
    )
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
        if args.probe:
            sample = mh.read_active_sample(h, base)
            if not sample:
                print("sin vehiculo activo (mapa conduciendo)")
                return 1
            veh = int(sample["veh"], 16)
            probe = mh.probe_vehicle_load(h, veh)
            probe["speed_kmh"] = sample.get("speed_kmh")
            data = probe
        else:
            data = snapshot(h, base)
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)

    if "error" in data:
        print(data["error"])
        return 1

    if args.probe:
        print(f"PID={pid} km/h={data.get('speed_kmh')}")
        _print_probe(data)
        if args.save:
            path = os.path.join(snap_dir, f"{args.save}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"\nGuardado: {path}")
        return 0

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
