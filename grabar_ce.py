"""Graba telemetria Havok sin Cheat Engine. Ctrl+C para parar.

Ejecutar:
  python grabar_ce.py --probe
  python grabar_ce.py --live --import --auto --compare --index
  grabar_telemetria.bat
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
CE_DIR = os.path.join(ROOT, "cheat_engine")
sys.path.insert(0, ROOT)
sys.path.insert(0, CE_DIR)

import memoria_havok as mh  # noqa: E402
from ctypes import windll  # noqa: E402
from datos.map_detect import format_map_line, resolve_map_context  # noqa: E402

kernel32 = windll.kernel32
TERRAIN_LABELS = {
    "hard": "asfalto/firme",
    "mud": "barro",
    "soft": "intermedio",
    "snow": "nieve",
    "ice": "hielo",
    "mixed": "mixto (ruedas distintas)",
    "unknown": "?",
}

LOAD_LABELS = {
    "vacio": "vacio",
    "cargado": "carga en bastidor",
    "trailer_vacio": "remolque vacio",
    "trailer_cargado": "remolque con carga",
}


def run_import(
    protocol: str,
    csv_path: str,
    compare: bool,
    auto_protocol: bool,
    *,
    map_name: str = "",
    location: str = "CE Havok log",
    clima: str = "",
    hora_juego: str = "",
    baseline_tag: str = "",
    do_index: bool = False,
) -> int:
    cmd = [sys.executable, os.path.join(ROOT, "importar_ce_csv.py"), csv_path]
    if auto_protocol:
        cmd.append("--auto")
    else:
        cmd.extend(["--protocol", protocol])
    if map_name:
        cmd.extend(["--map", map_name])
    if location:
        cmd.extend(["--location", location])
    if clima:
        cmd.extend(["--clima", clima])
    if hora_juego:
        cmd.extend(["--hora-juego", hora_juego])
    if baseline_tag:
        cmd.extend(["--baseline", baseline_tag])
    if compare:
        cmd.append("--compare")
    if do_index:
        cmd.append("--index")
    return subprocess.call(cmd)


def load_csv_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_protocol(args: argparse.Namespace, sample: dict) -> str:
    if not args.auto:
        return args.protocol
    from camiones.registry import vehicle_id_from_ce
    from telemetria import load_detection_from_sample, resolve_auto_protocol

    game_id = sample.get("vehicle_id") or ""
    vehicle_id = vehicle_id_from_ce(game_id) or "ck1500"
    load_det = load_detection_from_sample(sample, vehicle_id)
    proto, msg = resolve_auto_protocol(
        game_id,
        sample.get("surface_wheel") or "",
        sample.get("wheel_grip"),
        sample.get("terrain_kind") or "",
        sample.get("contact_avg"),
        load_detection=load_det,
    )
    print(f"Auto (inicio): {msg}")
    return proto


def print_terrain_sample(sample: dict, prefix: str = "") -> None:
    kind = sample.get("terrain_kind") or sample.get("surface_wheel") or "?"
    label = TERRAIN_LABELS.get(kind, kind)
    print(
        f"{prefix}terreno CE: {kind} ({label}) | grip {sample.get('wheel_grip') or '?'} "
        f"| surf {sample.get('surface_avg') or '?'} | contact {sample.get('contact_avg') or '?'}"
    )
    deform = (sample.get("surface_deform_avg") or "").strip()
    if deform:
        print(f"{prefix}  deform={deform} contactΔ={sample.get('contact_min')}-{sample.get('contact_max')}")
    grade = (sample.get("mud_grade_label") or "").strip()
    if grade:
        print(f"{prefix}  mud_grade={sample.get('mud_grade')} ({grade})")
    if sample.get("wheel_kinds"):
        print(f"{prefix}  ruedas: {sample.get('wheel_kinds')}")


def print_load_sample(sample: dict, prefix: str = "") -> None:
    hint = sample.get("load_hint") or "vacio"
    label = LOAD_LABELS.get(hint, hint)
    trailer = sample.get("trailer_id") or ""
    cargo = sample.get("cargo_mass_kg") or sample.get("payload_kg") or "0"
    total = sample.get("total_mass_kg") or "?"
    empty = sample.get("empty_mass_kg") or "?"
    line = (
        f"{prefix}carga: {hint} ({label}) | payload ~{cargo} kg "
        f"| Havok {total} kg (vacio XML {empty} kg)"
    )
    if trailer:
        tm = sample.get("trailer_mass_kg") or "?"
        line += f" | remolque {trailer} ({tm} kg)"
    types = sample.get("cargo_types") or ""
    if types:
        line += f" | tipos {types}"
    path_type = sample.get("path_cargo_type") or ""
    if path_type:
        line += f" | registry {path_type}"
    slots = sample.get("packed_cargo_slots") or ""
    if slots:
        line += f" | slots {slots}"
    print(line)


def summarize_terrain_rows(rows: list[dict]) -> Counter:
    return Counter((r.get("terrain_kind") or "?").strip() for r in rows)


def summarize_load_rows(rows: list[dict]) -> Counter:
    return Counter((r.get("load_hint") or "vacio").strip() for r in rows)


def format_live_line(t_elapsed: float, sample: dict) -> str:
    """Una linea compacta para monitor en consola (--live)."""
    kind = (sample.get("terrain_kind") or sample.get("surface_wheel") or "?").strip()
    speed = sample.get("speed_kmh")
    speed_s = f"{float(speed):.1f}" if speed not in (None, "") else "?"
    grip = sample.get("wheel_grip") or "?"
    contact = sample.get("contact_avg") or "?"
    load_h = sample.get("load_hint") or "vacio"
    mass = sample.get("total_mass_kg") or "?"
    if sample.get("mass_estimated"):
        mass = f"~{mass}"
    vid = (sample.get("vehicle_id") or "?").replace("international_", "int_")
    parts = [
        f"[{t_elapsed:6.1f}s]",
        f"{speed_s} km/h",
        f"ce={kind}",
    ]
    parts.extend([f"grip={grip}", f"contact={contact}"])
    deform = (sample.get("surface_deform_avg") or "").strip()
    if deform:
        parts.append(f"deform={deform}")
    mg = (sample.get("mud_grade_label") or "").strip()
    if mg:
        parts.append(f"mud={mg}")
    grip_min = sample.get("grip_min")
    grip_max = sample.get("grip_max")
    if grip_min and grip_max and grip_min != grip_max:
        parts.append(f"gripΔ={grip_min}-{grip_max}")
    contact_min = sample.get("contact_min")
    contact_max = sample.get("contact_max")
    if contact_min and contact_max and contact_min != contact_max:
        parts.append(f"contactΔ={contact_min}-{contact_max}")
    wk = sample.get("wheel_kinds") or ""
    if wk and (kind == "mixed" or sample.get("wheel_disagreement")):
        parts.append(f"ruedas={wk}")
    parts.extend([load_h, f"{mass} kg", vid])
    yaw = sample.get("yaw_rate_deg_s")
    if yaw not in (None, ""):
        try:
            if abs(float(yaw)) >= 0.5:
                parts.append(f"yaw={float(yaw):.1f} deg/s")
        except ValueError:
            pass
    turn_r = sample.get("turn_radius_m")
    if turn_r not in (None, ""):
        try:
            tr = float(turn_r)
            if tr > 0:
                parts.append(f"R={tr:.0f}m")
        except ValueError:
            pass
    pos_y = sample.get("pos_y")
    if pos_y not in (None, ""):
        try:
            parts.append(f"pos_y={float(pos_y):.3f}")
        except ValueError:
            pass
    fuel = sample.get("fuel_pct")
    if fuel not in (None, ""):
        parts.append(f"fuel={fuel}%")
    rate = sample.get("fuel_rate_pct_min")
    if rate not in (None, ""):
        try:
            if float(rate) > 0.05:
                parts.append(f"fuel_rate={rate}%/min")
        except ValueError:
            pass
    diff = sample.get("diff_lock_live")
    if diff not in (None, ""):
        parts.append(f"diff={diff}")
    lg = sample.get("low_gear_live")
    if lg not in (None, ""):
        parts.append(f"L={lg}")
    thr = sample.get("throttle")
    if thr not in (None, ""):
        parts.append(f"thr={thr}")
    return " | ".join(parts)


def _sample_float(sample: dict, key: str) -> float | None:
    raw = sample.get(key)
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


# Havok suaviza +0x2EC/+0x2FC; avisar solo cambios claros (no ruido de 0.001).
CONTACT_DRIFT_EPS = 0.03
GRIP_DRIFT_EPS = 0.03


def summarize_mud_grade_rows(rows: list[dict]) -> Counter:
    return Counter((r.get("mud_grade_label") or "—").strip() for r in rows)


def print_catalog_xml_note(game_id: str) -> None:
    from camiones.registry import vehicle_id_from_ce
    from datos.catalog_lookup import setup_xml_from_catalog

    vid = vehicle_id_from_ce(game_id or "")
    if not vid:
        return
    setup = setup_xml_from_catalog(vid)
    if not setup:
        return
    print("  refs XML stock (§2.5 → session_context.setup al importar):")
    keys = (
        "suspension_strength_front_xml",
        "suspension_strength_rear_xml",
        "suspension_damping_front_xml",
        "suspension_height_front_xml",
        "steer_speed_xml",
        "default_gearbox_xml",
        "engine_responsiveness_xml",
    )
    for key in keys:
        if key in setup:
            print(f"    {key}: {setup[key]}")
    print("  (Strength/Damping/Height no hay offset CE — pos_y arriba es runtime Havok)")


def _cargo_mass_kg(sample: dict) -> float:
    raw = sample.get("cargo_mass_kg") or sample.get("payload_kg") or 0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grabar telemetria SnowRunner leyendo memoria (sin Cheat Engine)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0,
        help="Segundos a grabar (0 = hasta Ctrl+C)",
    )
    parser.add_argument("--interval", type=float, default=0.5, help="Intervalo entre muestras (s)")
    parser.add_argument(
        "--output", default="", help="CSV de salida (default: Documents/.../telemetria_ce_log.csv)"
    )
    parser.add_argument(
        "--import", dest="do_import", action="store_true", help="Importar al terminar"
    )
    parser.add_argument(
        "--protocol",
        default="f2_barro_offroad",
        help="Protocolo para importar (ignorado con --auto al importar)",
    )
    parser.add_argument(
        "--auto",
        dest="auto",
        action="store_true",
        default=None,
        help="Detectar camion/terreno al importar (default con --import)",
    )
    parser.add_argument(
        "--no-auto",
        dest="auto",
        action="store_false",
        help="Usar --protocol fijo al importar",
    )
    parser.add_argument("--compare", action="store_true", help="Comparar con sim tras importar")
    parser.add_argument("--map", default="", help="Nombre del mapa (auto si vacio)")
    parser.add_argument(
        "--auto-map",
        action="store_true",
        default=None,
        help="Detectar mapa desde log/memoria (default si --map vacio)",
    )
    parser.add_argument("--location", default="", help="Ruta / tramo GPS")
    parser.add_argument("--clima", default="", help="Clima Fase 7")
    parser.add_argument("--hora-juego", default="", dest="hora_juego", help="Hora in-game")
    parser.add_argument("--baseline", default="", dest="baseline_tag", help="Tag baseline")
    parser.add_argument(
        "--index",
        action="store_true",
        help="Indexar en calibracion.json tras importar",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Mostrar linea de telemetria en consola mientras graba",
    )
    parser.add_argument(
        "--live-interval",
        type=float,
        default=2.0,
        dest="live_interval",
        help="Segundos entre lineas --live (default 2)",
    )
    parser.add_argument("--probe", action="store_true", help="Solo comprobar lectura y salir")
    args = parser.parse_args()
    if args.auto_map is None:
        args.auto_map = not bool(args.map.strip())
    if args.auto is None:
        args.auto = bool(args.do_import)

    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner.exe no esta corriendo (o sin permiso de lectura).")
        print("Abre el juego, entra al MAPA conduciendo, y reintenta.")
        return 1

    h, base, pid = opened
    samples_written = 0
    protocol = args.protocol
    log_path = args.output or mh.resolve_log_path()
    session_map_name = args.map.strip()
    session_location = args.location.strip() or "CE Havok log"
    session_map_ctx = None

    def _resolve_session_map() -> None:
        nonlocal session_map_name, session_location, session_map_ctx
        if not args.map.strip() and not args.auto_map:
            session_location = args.location.strip() or "CE Havok log"
            session_map_ctx = None
            return
        ctx = resolve_map_context(
            map_arg=args.map,
            location_arg=args.location,
            process_handle=h if args.auto_map else None,
            sample=sample,
        )
        session_map_ctx = ctx
        if ctx.map_name:
            session_map_name = ctx.map_name
        if ctx.location_note:
            session_location = ctx.location_note

    try:
        sample = mh.read_active_sample(h, base)
        if args.probe:
            if sample:
                print(f"OK PID={pid} base=0x{base:X}")
                for k in (
                    "vehicle_id",
                    "speed_kmh",
                    "fuel_pct",
                    "terrain_kind",
                    "surface_wheel",
                    "wheel_grip",
                    "surface_avg",
                    "contact_avg",
                    "surface_deform_avg",
                    "mud_grade",
                    "mud_grade_label",
                    "load_hint",
                    "trailer_id",
                    "cargo_mass_kg",
                    "total_mass_kg",
                    "empty_mass_kg",
                    "payload_kg",
                    "trailer_mass_kg",
                    "packed_cargo_slots",
                    "path_cargo_type",
                    "frame_addon",
                    "yaw_rate_deg_s",
                    "turn_radius_m",
                    "chain",
                    "terrain_hint",
                    "pos_x",
                    "pos_z",
                ):
                    print(f"  {k}: {sample.get(k)}")
                print_terrain_sample(sample, prefix="  ")
                print_load_sample(sample, prefix="  ")
                _resolve_session_map()
                if session_map_ctx:
                    px = sample.get("pos_x")
                    pz = sample.get("pos_z")
                    print(f"  {format_map_line(session_map_ctx, pos_x=px, pos_z=pz)}")
                    if session_location:
                        print(f"  ubicacion: {session_location}")
                mh.write_status(f"grabar_ce probe OK km/h={sample['speed_kmh']}")
                return 0
            print("Sin vehiculo activo. Entra al mapa conduciendo (no menu/garaje).")
            return 1

        if not sample:
            print("Esperando vehiculo en mapa (conduce; Ctrl+C para cancelar)...")
            wait_start = time.monotonic()
            last_msg = 0.0
            while sample is None:
                time.sleep(1.0)
                sample = mh.read_active_sample(h, base)
                elapsed = time.monotonic() - wait_start
                if elapsed > 120:
                    print("Timeout 120 s sin vehiculo.")
                    return 1
                if elapsed - last_msg >= 5:
                    print("  ... aun sin datos (menu/garaje = singleton 0)")
                    last_msg = elapsed

        log_path = args.output or mh.resolve_log_path()
        if args.auto:
            try:
                protocol = resolve_protocol(args, sample)
            except ValueError as e:
                print(f"Error auto-deteccion: {e}")
                return 1

        print(f"Grabando -> {log_path}")
        _resolve_session_map()
        print(f"  vehiculo: {sample.get('vehicle_id')} | {sample.get('speed_kmh')} km/h")
        if session_map_ctx:
            px = sample.get("pos_x")
            pz = sample.get("pos_z")
            print(f"  {format_map_line(session_map_ctx, pos_x=px, pos_z=pz)}")
            if session_location:
                print(f"  ubicacion: {session_location}")
        print_terrain_sample(sample, prefix="  ")
        print_load_sample(sample, prefix="  ")
        print_catalog_xml_note(sample.get("vehicle_id") or "")
        if sample.get("pos_x") is not None:
            print(
                f"  pos mundo: x={sample.get('pos_x', 0):.1f} "
                f"y={sample.get('pos_y', 0):.1f} z={sample.get('pos_z', 0):.1f}"
            )
        if args.auto:
            print("  protocolo: auto al importar (comparacion por tramos mud/hard)")
        else:
            print(f"  protocolo: {protocol}")
        if args.duration:
            print(f"  duracion: {args.duration}s")
        else:
            print("  Ctrl+C para parar")
        if args.auto:
            print("  Conduce ruta mixta: cambios de terreno se muestran en consola")
        if args.live:
            print(
                f"  LIVE: linea cada {args.live_interval}s "
                "(velocidad, terreno CE, grip/contact; Havok suaviza contacto)"
            )

        t0 = time.monotonic()
        mh._FUEL_RATE_TRACKER.reset()
        last_map_resolve = t0
        last_vehicle_id = ""
        last_terrain_kind = (sample.get("terrain_kind") or "").strip()
        last_mud_grade = (sample.get("mud_grade_label") or "").strip()
        last_load_hint = (sample.get("load_hint") or "vacio").strip()
        last_contact = _sample_float(sample, "contact_avg")
        last_grip = _sample_float(sample, "wheel_grip")
        header_written = False
        next_sample = t0
        last_live_print = -args.live_interval if args.live else 0.0

        with open(log_path, "w", encoding="utf-8", newline="") as f:
            while True:
                now = time.monotonic()
                if args.duration and now - t0 >= args.duration:
                    break

                if now >= next_sample:
                    row_sample = mh.read_active_sample(h, base)
                    if row_sample:
                        t_elapsed = now - t0
                        mh.enrich_drive_fields(h, base, row_sample, t_s=t_elapsed)
                        if now - last_map_resolve >= 60:
                            _resolve_session_map()
                            last_map_resolve = now
                        row_sample["map_name"] = session_map_name
                        row_sample["level_id"] = (
                            session_map_ctx.level_id if session_map_ctx else ""
                        )
                        event = ""
                        vid = row_sample.get("vehicle_id") or ""
                        if vid and last_vehicle_id and vid != last_vehicle_id:
                            event = "vehicle_change"
                            print(f"Cambio camion: {last_vehicle_id} -> {vid}")
                        if vid:
                            last_vehicle_id = vid

                        kind = (row_sample.get("terrain_kind") or "").strip()
                        if kind and kind != last_terrain_kind:
                            t_elapsed = now - t0
                            label = TERRAIN_LABELS.get(kind, kind)
                            wk = row_sample.get("wheel_kinds") or ""
                            extra_wk = f" [{wk}]" if wk else ""
                            print(
                                f"  [{t_elapsed:5.1f}s] terreno -> {kind} ({label}){extra_wk} "
                                f"grip={row_sample.get('wheel_grip')} "
                                f"contact={row_sample.get('contact_avg')} "
                                f"mud={row_sample.get('mud_grade_label') or '?'}"
                            )
                            last_terrain_kind = kind
                            last_contact = _sample_float(row_sample, "contact_avg")
                            last_grip = _sample_float(row_sample, "wheel_grip")

                        contact = _sample_float(row_sample, "contact_avg")
                        grip = _sample_float(row_sample, "wheel_grip")
                        if (
                            kind == last_terrain_kind
                            and contact is not None
                            and last_contact is not None
                            and abs(contact - last_contact) >= CONTACT_DRIFT_EPS
                        ):
                            t_elapsed = now - t0
                            cmin = row_sample.get("contact_min") or "?"
                            cmax = row_sample.get("contact_max") or "?"
                            print(
                                f"  [{t_elapsed:5.1f}s] contacto -> {contact:.3f} "
                                f"(antes {last_contact:.3f}) ruedas {cmin}-{cmax}"
                            )
                            last_contact = contact
                        elif contact is not None:
                            last_contact = contact

                        if (
                            kind == last_terrain_kind
                            and grip is not None
                            and last_grip is not None
                            and abs(grip - last_grip) >= GRIP_DRIFT_EPS
                        ):
                            t_elapsed = now - t0
                            print(
                                f"  [{t_elapsed:5.1f}s] grip -> {grip:.3f} "
                                f"(antes {last_grip:.3f})"
                            )
                            last_grip = grip
                        elif grip is not None:
                            last_grip = grip

                        mud = (row_sample.get("mud_grade_label") or "").strip()
                        if mud and mud != last_mud_grade and kind == last_terrain_kind:
                            t_elapsed = now - t0
                            print(
                                f"  [{t_elapsed:5.1f}s] mud_grade -> {mud} "
                                f"(g={row_sample.get('mud_grade')})"
                            )
                            last_mud_grade = mud
                        elif mud:
                            last_mud_grade = mud

                        load_hint = (row_sample.get("load_hint") or "vacio").strip()
                        if load_hint != last_load_hint:
                            t_elapsed = now - t0
                            label = LOAD_LABELS.get(load_hint, load_hint)
                            extra = ""
                            if row_sample.get("trailer_id"):
                                extra = f" remolque={row_sample.get('trailer_id')}"
                            elif _cargo_mass_kg(row_sample) > 0:
                                extra = f" ~{row_sample.get('cargo_mass_kg') or row_sample.get('payload_kg')} kg"
                            print(f"  [{t_elapsed:5.1f}s] carga -> {load_hint} ({label}){extra}")
                            last_load_hint = load_hint

                        if not header_written:
                            f.write(mh.CSV_HEADER)
                            header_written = True
                            mh.write_status(f"OK logging -> {log_path}")

                        f.write(mh.format_csv_row(now - t0, row_sample, event))
                        f.flush()
                        samples_written += 1

                        if args.live:
                            t_elapsed = now - t0
                            if t_elapsed - last_live_print >= args.live_interval:
                                print(format_live_line(t_elapsed, row_sample), flush=True)
                                last_live_print = t_elapsed

                    next_sample += args.interval

                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nParado por usuario.")
    finally:
        kernel32.CloseHandle(h)

    print(f"Muestras grabadas: {samples_written}")
    if samples_written == 0:
        print("CSV vacio — no hubo datos Havok durante la sesion.")
        return 1

    log_path = args.output or mh.resolve_log_path()
    rows = load_csv_rows(log_path)
    counts = summarize_terrain_rows(rows)
    if counts:
        print("\nResumen terreno CE en sesion:")
        for kind, n in counts.most_common():
            label = TERRAIN_LABELS.get(kind, kind)
            pct = 100.0 * n / len(rows)
            print(f"  {kind:8} ({label:16}) {n:4}  {pct:5.1f}%")
    mud_counts = summarize_mud_grade_rows(rows)
    if any(k != "—" for k in mud_counts):
        print("\nResumen mud_grade CE en sesion:")
        for label, n in mud_counts.most_common():
            pct = 100.0 * n / len(rows)
            print(f"  {label:16} {n:4}  {pct:5.1f}%")

    load_counts = summarize_load_rows(rows)
    if load_counts:
        print("\nResumen carga en sesion:")
        for hint, n in load_counts.most_common():
            label = LOAD_LABELS.get(hint, hint)
            pct = 100.0 * n / len(rows)
            print(f"  {hint:16} ({label:22}) {n:4} muestras ({pct:.0f}%)")

    if args.do_import and samples_written > 0:
        return run_import(
            protocol,
            log_path,
            args.compare,
            auto_protocol=args.auto,
            map_name=args.map.strip(),
            location=session_location,
            clima=args.clima,
            hora_juego=args.hora_juego,
            baseline_tag=args.baseline_tag,
            do_index=args.index,
        )
    if args.auto:
        print(f'Importar: python importar_ce_csv.py "{log_path}" --auto --compare')
    else:
        print(f'Importar: python importar_ce_csv.py "{log_path}" --protocol {protocol} --compare')
    return 0


if __name__ == "__main__":
    sys.exit(main())
