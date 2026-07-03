"""CLI para consultar la base de datos del juego (datos/).

  python consultar_base.py manifest
  python consultar_base.py truck --mod marshall
  python consultar_base.py engine BrakesDelay --vehicle mh9500
  python consultar_base.py mae --vehicle marshall --protocol km_f2_barro_tm2
  python consultar_base.py stats
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(ROOT, "datos")
CATALOGO = os.path.join(DATOS, "catalogo")
INDICES = os.path.join(DATOS, "indices")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from telemetria import TELEMETRY_DIR, iter_session_json_paths  # noqa: E402

from camiones.registry import VEHICLES  # noqa: E402


def _load_json(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _catalog(kind: str) -> dict:
    data = _load_json(os.path.join(CATALOGO, f"{kind}.json"))
    if not data:
        return {}
    return data.get(kind, {})


def cmd_manifest(_: argparse.Namespace) -> int:
    m = _load_json(os.path.join(INDICES, "manifest.json"))
    if not m:
        print("Falta manifest.json — ejecuta: python datos/build_indices.py")
        return 1
    print(f"Build juego: {m.get('game_version', '?')}")
    print(f"Mod commit:  {m.get('mod_commit') or '(sin git)'}")
    print(f"Actualizado: {m.get('updated_utc', '?')}")
    print("\nVehiculos mod:")
    for vid, info in sorted(m.get("vehicles_mod", {}).items()):
        mass = info.get("empty_mass_kg")
        print(f"  {vid:<10} {info.get('label', ''):<22} vacio={mass} kg  xml={info.get('xml_file')}")
    pak = m.get("pak", {}).get("backup") or {}
    if pak:
        print(f"\ninitial.pak.bak: {pak.get('size_bytes', 0) // (1024 * 1024)} MB")
    return 0


def _resolve_truck_id(args: argparse.Namespace) -> str | None:
    if args.mod:
        if args.mod not in VEHICLES:
            print(f"Vehiculo mod desconocido: {args.mod}")
            return None
        return VEHICLES[args.mod].xml_file.removesuffix(".xml")
    if args.truck_id:
        return args.truck_id
    print("Indica --mod o truck_id")
    return None


def cmd_truck(args: argparse.Namespace) -> int:
    trucks = _catalog("trucks")
    if not trucks:
        print("Falta catalogo — ejecuta: python auditar_pak_catalogo.py")
        return 1
    tid = _resolve_truck_id(args)
    if not tid:
        return 1
    t = trucks.get(tid)
    if not t:
        print(f"No en catalogo: {tid}")
        return 1
    print(f"Camion: {t['id']} ({t.get('truck_type', '')})")
    if t.get("mod_vehicle_id"):
        print(f"  mod: {t['mod_vehicle_id']}")
    print(f"  masa XML: {t.get('mass_all_bodies_kg')} kg (mayor cuerpo {t.get('mass_largest_body_kg')} kg)")
    print(f"  motor default: {t.get('default_engine')}")
    if t.get("engine_socket_type"):
        print(f"  motor Type:    {t.get('engine_socket_type')}")
    print(f"  caja default:  {t.get('default_gearbox')}")
    if t.get("gearbox_socket_type"):
        print(f"  caja Type:     {t.get('gearbox_socket_type')}")
    print(f"  ruedas:        {t.get('default_wheel_type')} / {t.get('default_tire')}")
    print(f"  SteerSpeed:    {t.get('steer_speed')}  Responsiveness: {t.get('responsiveness')}")
    print(f"  FuelCapacity:  {t.get('fuel_capacity')}")
    return 0


def _engines_for_truck(truck: dict) -> list[dict]:
    default = truck.get("default_engine") or ""
    engines = _catalog("engines")
    hits = []
    for eng in engines.values():
        if default and (eng.get("name") == default or default in eng.get("name", "")):
            hits.append(eng)
        elif default and default in eng.get("file_id", ""):
            hits.append(eng)
    return hits


def cmd_engine(args: argparse.Namespace) -> int:
    trucks = _catalog("trucks")
    if not trucks:
        print("Falta catalogo — ejecuta: python auditar_pak_catalogo.py")
        return 1

    attr = args.attribute
    if args.vehicle:
        mod = VEHICLES.get(args.vehicle)
        if not mod:
            print(f"Vehiculo mod desconocido: {args.vehicle}")
            return 1
        truck = trucks.get(mod.xml_file.removesuffix(".xml"))
        if not truck:
            print(f"Camion {mod.xml_file} no en catalogo")
            return 1
        hits = _engines_for_truck(truck)
        if not hits:
            print(f"Motor default '{truck.get('default_engine')}' no resuelto en engines.json")
            return 1
        for eng in hits:
            val = eng.get(attr.lower()) or eng.get(_snake(attr))
            print(f"{eng.get('name')} ({eng.get('file_id')}): {attr}={val}")
        return 0

    if args.name:
        engines = _catalog("engines")
        found = [e for e in engines.values() if args.name in (e.get("name", ""), e.get("file_id", ""))]
        if not found:
            print(f"Motor no encontrado: {args.name}")
            return 1
        for eng in found:
            val = eng.get(attr.lower()) or eng.get(_snake(attr))
            print(f"{eng.get('name')}: {attr}={val}")
        return 0

    print("Indica --vehicle o --name")
    return 1


def _snake(name: str) -> str:
    mapping = {
        "BrakesDelay": "brakes_delay",
        "MaxDeltaAngVel": "max_delta_ang_vel",
        "Torque": "torque",
        "FuelConsumption": "fuel_consumption",
        "EngineResponsiveness": "engine_responsiveness",
    }
    return mapping.get(name, name.lower())


def cmd_mae(args: argparse.Namespace) -> int:
    cal = _load_json(os.path.join(INDICES, "calibracion.json"))
    sessions = (cal or {}).get("sessions", [])
    if not sessions:
        # Fallback: sesiones JSON sueltas
        if os.path.isdir(TELEMETRY_DIR):
            print("calibracion.json vacio — aun no hay sesiones indexadas (oleada 2).")
            print(f"Sesiones en disco: {len(iter_session_json_paths())}")
        else:
            print("Sin sesiones. Graba: grabar_telemetria.bat")
        return 0

    filtered = sessions
    if args.vehicle:
        filtered = [s for s in filtered if s.get("vehicle_id") == args.vehicle]
    if args.protocol:
        filtered = [s for s in filtered if s.get("protocol_id") == args.protocol]
    if getattr(args, "terrain", None):
        filtered = [s for s in filtered if s.get("terrain_kind") == args.terrain]
    if getattr(args, "entry_type", None):
        filtered = [s for s in filtered if s.get("entry_type") == args.entry_type]
    if args.baseline:
        filtered = [
            s
            for s in filtered
            if (s.get("baseline_tag") or s.get("session_context", {}).get("baseline_tag")) == args.baseline
        ]

    if not filtered:
        print("Ninguna sesion coincide con los filtros.")
        return 0

    for s in filtered[-args.limit :]:
        mae = s.get("whole_mae_kmh", s.get("mae_kmh", "?"))
        sid = s.get("segment_id") or s.get("session_id", "?")
        vid = s.get("vehicle_id", "?")
        proto = s.get("protocol_id", "?")
        kind = s.get("terrain_kind")
        et = s.get("entry_type", "session")
        extra = f" [{kind}]" if kind else ""
        print(f"  {sid}: {vid} {proto} ({et}{extra}) MAE={mae} km/h")
    return 0


def cmd_stats(_: argparse.Namespace) -> int:
    counts = {}
    for kind in ("trucks", "engines", "wheels", "gearboxes", "suspensions"):
        data = _load_json(os.path.join(CATALOGO, f"{kind}.json"))
        counts[kind] = (data or {}).get("counts", {}).get(kind, 0) if data else 0
    if not any(counts.values()):
        print("Catalogo vacio — ejecuta: python auditar_pak_catalogo.py")
        return 1
    print("Catalogo XML (stock initial.pak.bak):")
    for k, n in counts.items():
        print(f"  {k}: {n}")
    cal = _load_json(os.path.join(INDICES, "calibracion.json"))
    n_cal = len((cal or {}).get("sessions", []))
    n_disk = len(iter_session_json_paths()) if os.path.isdir(TELEMETRY_DIR) else 0
    print(f"\nSesiones indexadas: {n_cal}  |  JSON en telemetria/sesiones: {n_disk}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consultar base de datos del juego")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_man = sub.add_parser("manifest", help="Resumen manifest.json")
    p_man.set_defaults(func=cmd_manifest)

    p_tr = sub.add_parser("truck", help="Ficha camion del catalogo")
    p_tr.add_argument("truck_id", nargs="?", default="", help="ID XML sin .xml")
    p_tr.add_argument("--mod", help="ID mod: ck1500, mh9500, fleetstar, marshall")
    p_tr.set_defaults(func=cmd_truck)

    p_eng = sub.add_parser("engine", help="Atributo motor (BrakesDelay, Torque, ...)")
    p_eng.add_argument("attribute", help="Nombre atributo XML")
    p_eng.add_argument("--vehicle", help="ID mod del camion")
    p_eng.add_argument("--name", help="Nombre motor en XML")
    p_eng.set_defaults(func=cmd_engine)

    p_mae = sub.add_parser("mae", help="MAE sesiones (calibracion.json)")
    p_mae.add_argument("--vehicle", help="Filtrar por vehiculo mod")
    p_mae.add_argument("--protocol", help="Filtrar por protocol_id")
    p_mae.add_argument("--baseline", help="Filtrar baseline_tag")
    p_mae.add_argument("--terrain", help="Filtrar terrain_kind (segmentos)")
    p_mae.add_argument(
        "--entry-type",
        dest="entry_type",
        choices=("session", "segment"),
        help="Filtrar fila session o segment",
    )
    p_mae.add_argument("--limit", type=int, default=5, help="Ultimas N filas")
    p_mae.set_defaults(func=cmd_mae)

    p_st = sub.add_parser("stats", help="Conteos catalogo y sesiones")
    p_st.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
