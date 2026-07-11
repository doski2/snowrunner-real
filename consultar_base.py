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
COMUNIDAD = os.path.join(DATOS, "comunidad")
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
    com = _load_json(os.path.join(COMUNIDAD, "fuentes.json"))
    if com:
        t = com.get("totals", {})
        print(
            f"\nComunidad: {t.get('sheets', 0)} hojas, "
            f"{t.get('records', 0)} registros (USDS + SR!NFO + Extras)"
        )
    return 0


def cmd_comunidad(_: argparse.Namespace) -> int:
    fuentes = _load_json(os.path.join(COMUNIDAD, "fuentes.json"))
    if not fuentes:
        print("Sin datos/comunidad — ejecuta: python datos/importar_comunidad.py --fetch")
        return 1
    print(f"Actualizado: {fuentes.get('updated_utc', '?')}")
    totals = fuentes.get("totals", {})
    print(f"Hojas: {totals.get('sheets', '?')}  |  Registros: {totals.get('records', '?')}")
    print("\nLibros:")
    for bid, meta in (fuentes.get("books") or {}).items():
        print(f"  {bid}: {meta.get('name')}")
        print(f"    {meta.get('url')}")
    print("\nTop hojas:")
    counts = sorted((fuentes.get("counts") or {}).items(), key=lambda x: -x[1])[:12]
    for k, n in counts:
        print(f"  {k}: {n}")
    print("\nReimportar: python datos/importar_comunidad.py --fetch")
    return 0


def cmd_buscar(args: argparse.Namespace) -> int:
    """Busca en combined_*.json y hojas sueltas."""
    q = (args.query or "").strip().lower()
    if not q:
        print("Uso: consultar_base.py buscar <texto>")
        return 1
    topics = args.topic.split(",") if args.topic else [
        "trucks", "engines", "gearboxes", "cargo", "trailers", "addons", "tires"
    ]
    hits: list[str] = []
    for topic in topics:
        data = _load_json(os.path.join(COMUNIDAD, f"combined_{topic.strip()}.json"))
        if not data:
            continue
        for it in data.get("items", []):
            blob = json.dumps(it, ensure_ascii=False).lower()
            if q in blob:
                src = it.get("_source", topic)
                # primer campo legible
                label = next((str(v) for v in it.values() if isinstance(v, str) and v), "?")
                hits.append(f"[{topic}/{src}] {label[:80]}")
                if len(hits) >= args.limit:
                    break
        if len(hits) >= args.limit:
            break
    if not hits:
        print(f"Sin coincidencias para '{args.query}'")
        return 1
    for line in hits:
        print(f"  {line}")
    return 0


def cmd_cargo(args: argparse.Namespace) -> int:
    data = _load_json(os.path.join(COMUNIDAD, "cargo.json"))
    if not data:
        print("Falta cargo.json — python datos/importar_comunidad.py --fetch")
        return 1
    items = data.get("items", [])
    q = (args.query or "").strip().lower()
    if not q:
        print(f"Cargo SR!NFO ({len(items)} tipos). Busca: consultar_base.py cargo <texto>")
        return 0
    hits = []
    for it in items:
        blob = " ".join(
            [
                it.get("label", ""),
                " ".join(it.get("internal_names") or []),
                it.get("notes", ""),
            ]
        ).lower()
        if q in blob:
            hits.append(it)
    if not hits:
        print(f"Sin coincidencias para '{args.query}'")
        return 1
    for it in hits[: args.limit]:
        names = ", ".join(it.get("internal_names") or []) or "?"
        print(
            f"  {it.get('label')}: slots={it.get('slots')} "
            f"packed={it.get('packed_mass_kg')} kg  xml={names}"
        )
        if it.get("notes"):
            print(f"    nota: {it['notes']}")
    if len(hits) > args.limit:
        print(f"  ... +{len(hits) - args.limit} mas")
    return 0


def cmd_wheel(args: argparse.Namespace) -> int:
    data = _load_json(os.path.join(COMUNIDAD, "wheels_comunidad.json"))
    if not data:
        print("Falta wheels_comunidad.json — python datos/importar_comunidad.py --fetch")
        return 1
    q = (args.query or "").strip().lower()
    items = data.get("items", [])
    if not q:
        print(f"Ruedas SR!NFO ({len(items)}). Busca: consultar_base.py wheel <nombre>")
        return 0
    for it in items:
        if q in it.get("name", "").lower():
            fr = it.get("friction") or {}
            print(f"  {it.get('name')} [{it.get('category')}]")
            print(
                f"    asphalt={fr.get('asphalt')} body={fr.get('body')} "
                f"substance={fr.get('substance')}  price={it.get('price')}"
            )
            return 0
    print(f"Rueda no encontrada: {args.query}")
    return 1


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

    p_co = sub.add_parser("comunidad", help="Fuentes SR!NFO / USDS / Extras importadas")
    p_co.set_defaults(func=cmd_comunidad)

    p_cg = sub.add_parser("cargo", help="Buscar carga por nombre o Cargo* XML")
    p_cg.add_argument("query", nargs="?", default="", help="Texto a buscar")
    p_cg.add_argument("--limit", type=int, default=12)
    p_cg.set_defaults(func=cmd_cargo)

    p_wh = sub.add_parser("wheel", help="Friccion rueda (datos SR!NFO comunidad)")
    p_wh.add_argument("query", nargs="?", default="", help="Nombre rueda ej. UHD III")
    p_wh.set_defaults(func=cmd_wheel)

    p_bs = sub.add_parser("buscar", help="Buscar en combined trucks/engines/cargo/...")
    p_bs.add_argument("query", help="Texto a buscar")
    p_bs.add_argument("--topic", help="trucks,engines,cargo,... (coma)")
    p_bs.add_argument("--limit", type=int, default=15)
    p_bs.set_defaults(func=cmd_buscar)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
