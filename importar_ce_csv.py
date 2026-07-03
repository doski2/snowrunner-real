"""Importa CSV Havok (grabar_ce.py / TelemetryLogger.lua) a sesion telemetria.

Ejecutar:
  python importar_ce_csv.py --auto --compare
  python importar_ce_csv.py ruta\\telemetria_ce_log.csv --protocol fs_f2_barro_uhd --compare
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone

from camiones.registry import vehicle_id_from_ce
from telemetria import (
    SessionMeta,
    TelemetrySample,
    TelemetrySession,
    TEST_PROTOCOLS,
    compare_session_by_terrain,
    parse_note_field,
    resolve_protocol_from_ce_rows,
    sample_terrain_kind,
    save_session,
)
ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CE_LOG = os.path.join(
    os.path.expanduser("~"),
    "Documents",
    "My Games",
    "SnowRunner",
    "base",
    "telemetria_ce_log.csv",
)
DEFAULT_CE_LOG_FALLBACK = os.path.join(ROOT, "cheat_engine", "telemetria_ce_log.csv")


def _yaw_note_parts(row: dict) -> list[str]:
    """Notas de giro para correlacionar velocidad angular vs carga (Fase 3)."""
    parts: list[str] = []
    yaw_deg = (row.get("yaw_rate_deg_s") or "").strip()
    if yaw_deg:
        parts.append(f"yaw_deg_s={yaw_deg}")
    else:
        ang = (row.get("ang_yaw") or "").strip()
        if ang:
            try:
                parts.append(f"yaw_deg_s={float(ang) * 180.0 / math.pi:.2f}")
            except ValueError:
                parts.append(f"yaw_rad_s={ang}")
    turn_r = (row.get("turn_radius_m") or "").strip()
    if turn_r:
        parts.append(f"turn_r={turn_r}m")
    return parts


def game_id_to_vehicle(game_id: str) -> str:
    return vehicle_id_from_ce(game_id) or ""


def suggest_protocol(vehicle_id: str, protocol_id: str) -> str | None:
    """Protocolo equivalente por vehiculo (mh_*, fs_*, km_*)."""
    if protocol_id.startswith(("mh_", "fs_", "km_", "kd_")):
        return None
    if vehicle_id == "mh9500":
        return f"mh_{protocol_id}"
    if vehicle_id == "fleetstar":
        if protocol_id == "f2_barro_offroad":
            return "fs_f2_barro_uhd"
        return f"fs_{protocol_id}"
    if vehicle_id == "kodiak":
        if protocol_id == "f2_barro_offroad":
            return "kd_f2_barro_uhd"
        if protocol_id == "f1_asfalto_i6":
            return "kd_f1_asfalto"
        if protocol_id.startswith("f3_"):
            return "kd_f3_carga"
        return f"kd_{protocol_id}"
    if vehicle_id == "marshall":
        if protocol_id == "f2_barro_offroad":
            return "km_f2_barro_tm2"
        if protocol_id == "f1_asfalto_i6":
            return "km_f1_asfalto"
        if protocol_id.startswith("f3_"):
            return "km_f3_carga"
    if vehicle_id == "scout800":
        if protocol_id == "f2_barro_offroad":
            return "s8_f2_barro_hs"
        if protocol_id in ("f1_asfalto_i6", "f1_asfalto_aat8v"):
            return "s8_f1_asfalto_aat6v"
        if protocol_id.startswith("f3_"):
            return "s8_f3_carga_barro"
    return None


def csv_vehicle_summary(rows: list[dict]) -> tuple[str, dict[str, int]]:
    """ID de juego mas frecuente en CSV y conteo de terrain_hint."""
    ids = [r.get("vehicle_id", "").strip() for r in rows if r.get("vehicle_id", "").strip()]
    terrains = [r.get("terrain_hint", "").strip() or "?" for r in rows]
    game_id = Counter(ids).most_common(1)[0][0] if ids else ""
    return game_id, dict(Counter(terrains))

def resolve_ce_log(path: str | None) -> str:
    if path:
        return path
    if os.path.isfile(DEFAULT_CE_LOG):
        return DEFAULT_CE_LOG
    if os.path.isfile(DEFAULT_CE_LOG_FALLBACK):
        return DEFAULT_CE_LOG_FALLBACK
    return DEFAULT_CE_LOG


def load_ce_csv(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def csv_to_session(
    path: str,
    protocol_id: str,
    map_name: str = "",
    location_note: str = "CE Havok log",
    rows: list[dict] | None = None,
    session_context: dict | None = None,
) -> tuple[TelemetrySession, dict[str, int], str]:
    from datos.session_context import build_session_context, setup_from_protocol

    protocol = next((p for p in TEST_PROTOCOLS if p.id == protocol_id), TEST_PROTOCOLS[0])
    data = rows if rows is not None else load_ce_csv(path)
    game_id, terrain_counts = csv_vehicle_summary(data)
    detected_vehicle = game_id_to_vehicle(game_id) if game_id else ""
    if not detected_vehicle:
        detected_vehicle = protocol.vehicle_id

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    notes = f"importado desde CE: {os.path.basename(path)}"
    if game_id:
        notes += f"; game_id={game_id}"

    ctx = session_context or build_session_context(
        map_name=map_name,
        location_note=location_note,
        capture_tool="importar_ce_csv.py",
        setup=setup_from_protocol(protocol),
    )

    meta = SessionMeta(
        id=f"ce_{protocol_id}_{ts}",
        created_utc=datetime.now(timezone.utc).isoformat(),
        map_name=map_name,
        location_note=location_note,
        surface_kind=protocol.surface_kind,
        surface_label=protocol.surface_label,
        mod_applied=protocol.mod_applied,
        engine_id=protocol.engine_id,
        tire=protocol.tire,
        diff_lock=protocol.diff_lock,
        low_gear=protocol.low_gear,
        load_scenario_id=protocol.load_scenario_id,
        protocol_id=protocol_id,
        duration_s=protocol.duration_s,
        notes=notes,
        vehicle_id=detected_vehicle,
        session_context=ctx,
    )
    samples: list[TelemetrySample] = []
    for row in data:
        try:
            t_s = float(row.get("t_s", 0) or 0)
            speed = float(row.get("speed_kmh", 0) or 0)
        except (TypeError, ValueError):
            continue
        parts: list[str] = []
        if row.get("fuel_pct"):
            parts.append(f"fuel={row['fuel_pct']}%")
        hint = (row.get("terrain_hint") or "").strip()
        if hint:
            parts.append(f"terrain={hint}")
        sw = (row.get("surface_wheel") or "").strip()
        if sw:
            parts.append(f"surface={sw}")
        tk = (row.get("terrain_kind") or "").strip().lower()
        if tk:
            parts.append(f"kind={tk}")
        wg = (row.get("wheel_grip") or "").strip()
        if wg:
            parts.append(f"grip={wg}")
        sa = (row.get("surface_avg") or "").strip()
        if sa:
            parts.append(f"surf_avg={sa}")
        ca = (row.get("contact_avg") or "").strip()
        if ca:
            parts.append(f"contact={ca}")
        df = (row.get("surface_deform_avg") or "").strip()
        if df:
            parts.append(f"deform={df}")
        mg = (row.get("mud_grade_label") or "").strip()
        if mg:
            parts.append(f"mud_grade={mg}")
        lh = (row.get("load_hint") or "").strip()
        if lh:
            parts.append(f"load={lh}")
        tid = (row.get("trailer_id") or "").strip()
        if tid:
            parts.append(f"trailer={tid}")
        cm = (row.get("cargo_mass_kg") or row.get("payload_kg") or "").strip()
        if cm and cm != "0":
            parts.append(f"cargo_kg={cm}")
        pct = (row.get("path_cargo_type") or "").strip()
        if pct:
            parts.append(f"cargo_type={pct}")
        pcs = (row.get("packed_cargo_slots") or "").strip()
        if pcs and pcs != "0":
            parts.append(f"packed_slots={pcs}")
        tm = (row.get("total_mass_kg") or "").strip()
        if tm:
            parts.append(f"mass_havok={tm}")
        px = (row.get("pos_x") or "").strip()
        pz = (row.get("pos_z") or "").strip()
        if px and pz:
            parts.append(f"pos=({px},{pz})")
        gid = (row.get("vehicle_id") or "").strip()
        if gid:
            parts.append(f"id={gid}")
        parts.extend(_yaw_note_parts(row))
        samples.append(
            TelemetrySample(
                t_s,
                speed,
                "; ".join(parts),
                terrain_kind=tk,
            )
        )
    if samples:
        meta.duration_s = max(meta.duration_s, samples[-1].t_s + 1.0)
    return TelemetrySession(meta=meta, samples=samples), terrain_counts, game_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Importar log CSV Havok (grabar_ce.py)")
    parser.add_argument("csv", nargs="?", default=None, help="Ruta al CSV")
    parser.add_argument(
        "--protocol", default="f2_barro_offroad", help="ID protocolo TEST_PROTOCOLS"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Elegir protocolo segun vehiculo y terreno dominante del CSV",
    )
    parser.add_argument("--map", default="", help="Nombre del mapa")
    parser.add_argument("--location", default="CE Havok log", help="Nota de ruta / tramo")
    parser.add_argument("--clima", default="", help="Clima (Fase 7): seco, lluvia, noche")
    parser.add_argument("--hora-juego", default="", dest="hora_juego", help="Hora in-game")
    parser.add_argument(
        "--baseline",
        default="",
        dest="baseline_tag",
        help="Tag baseline (ej. baseline_mod_v1)",
    )
    parser.add_argument("--compare", action="store_true", help="Comparar con sim tras importar")
    parser.add_argument(
        "--index",
        action="store_true",
        help="Indexar en calibracion.json tras importar (indexar_sesion.py)",
    )
    args = parser.parse_args(argv)

    csv_path = resolve_ce_log(args.csv)
    if not os.path.isfile(csv_path):
        print(f"No encontrado: {csv_path}")
        if csv_path != DEFAULT_CE_LOG_FALLBACK:
            print(f"Tampoco: {DEFAULT_CE_LOG_FALLBACK}")
        print("Graba primero: grabar_telemetria.bat  o  python grabar_ce.py --duration 60")
        return 1

    size = os.path.getsize(csv_path)
    if size == 0:
        print(f"CSV vacio (0 bytes): {csv_path}")
        print("El logger trunco el archivo al iniciar pero no grabo ninguna fila.")
        print("Causas habituales:")
        print("  - SnowRunner no en mapa conduciendo (menu/garaje = sin vehiculo)")
        print("  - Paraste antes de la primera muestra")
        print("Prueba: python grabar_ce.py --probe")
        return 1

    rows = load_ce_csv(csv_path)
    if not rows:
        print(f"CSV sin filas de datos: {csv_path}")
        return 1

    protocol_id = args.protocol
    load_det = None
    if args.auto:
        try:
            protocol_id, auto_msg, _, load_det = resolve_protocol_from_ce_rows(rows)
            print(f"Auto: {auto_msg}")
        except ValueError as e:
            print(f"Error auto: {e}")
            return 1

    from datos.catalog_lookup import setup_xml_from_catalog
    from datos.session_context import build_session_context

    protocol_for_ctx = next((p for p in TEST_PROTOCOLS if p.id == protocol_id), TEST_PROTOCOLS[0])
    game_id_preview, _ = csv_vehicle_summary(rows)
    vid_preview = vehicle_id_from_ce(game_id_preview) if game_id_preview else ""
    setup = {
        "engine_id": protocol_for_ctx.engine_id,
        "tire": protocol_for_ctx.tire,
        "diff_lock": protocol_for_ctx.diff_lock,
        "low_gear": protocol_for_ctx.low_gear,
        "load_scenario_id": protocol_for_ctx.load_scenario_id,
    }
    setup.update(setup_xml_from_catalog(vid_preview or protocol_for_ctx.vehicle_id))
    ctx = build_session_context(
        map_name=args.map,
        location_note=args.location,
        clima=args.clima,
        hora_juego=args.hora_juego,
        baseline_tag=args.baseline_tag,
        capture_tool="importar_ce_csv.py",
        setup=setup,
    )

    session, terrain_counts, game_id = csv_to_session(
        csv_path,
        protocol_id,
        args.map,
        location_note=args.location,
        rows=rows,
        session_context=ctx,
    )
    if args.auto and load_det and load_det.loaded:
        session = TelemetrySession(
            meta=replace(session.meta, load_scenario_id=load_det.load_scenario_id),
            samples=session.samples,
        )

    if not session.samples:
        print(f"\nAviso: CSV tiene {size} bytes pero ninguna fila valida (t_s/speed_kmh).")
        print(f"Revisa: {csv_path}")
        return 1

    path = save_session(session)
    print(f"Importado: {len(session.samples)} muestras")
    print(f"Guardado: {path}")

    if game_id:
        print(f"Vehiculo en CSV: {game_id} -> {session.meta.vehicle_id}")
    protocol = next((p for p in TEST_PROTOCOLS if p.id == protocol_id), None)
    if protocol and game_id and session.meta.vehicle_id != protocol.vehicle_id:
        alt = suggest_protocol(session.meta.vehicle_id, protocol_id)
        print(
            f"\nAVISO: protocolo {protocol_id} es para {protocol.vehicle_id}, "
            f"pero condujiste {session.meta.vehicle_id}."
        )
        if alt:
            print(f"  Usa: python importar_ce_csv.py --protocol {alt} --compare")

    if terrain_counts:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(terrain_counts.items()))
        print(f"Superficie velocidad (terrain_hint CSV): {parts}")

    kind_counts = Counter(sample_terrain_kind(s) for s in session.samples)
    if kind_counts:
        print(
            "Terreno Havok (terrain_kind): "
            + ", ".join(f"{k}={v}" for k, v in sorted(kind_counts.items()))
        )

    load_counts = Counter((parse_note_field(s.note, "load") or "vacio") for s in session.samples)
    load_counts.pop("", None)
    if load_counts:
        print("Carga (load_hint): " + ", ".join(f"{k}={v}" for k, v in sorted(load_counts.items())))

    surf = Counter(
        (p.split("surface=")[1].split(";")[0] if "surface=" in p else "")
        for s in session.samples
        for p in [s.note]
        if "surface=" in p
    )
    if surf:
        print(
            "Superficie rueda (surface_wheel): "
            + ", ".join(f"{k or '?'}={v}" for k, v in surf.most_common())
        )
        print(
            f"Comparacion vs sim usa superficie del protocolo: "
            f"{session.meta.surface_label} ({session.meta.surface_kind})"
        )
        if "hard_fast" not in terrain_counts and max(terrain_counts.values()) > 0:
            print(
                "  Con marcha reducida (10-15 km/h) terrain_hint suele ser "
                "'crawl' - no indica barro vs asfalto."
            )

    if args.compare and session.samples:
        report = compare_session_by_terrain(session)
        counts = report.get("terrain_sample_counts", {})
        if counts:
            print(
                "\nMuestras por terreno:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            )
        whole = report["whole_session"]
        print(f"\nSesion completa (protocolo {report['protocol_id_whole']}):")
        print(
            f"  MAE: {whole['mae_kmh']} km/h | v30 juego: {whole.get('game_v30_kmh')} | v30 sim: {whole.get('sim_v30_kmh')}"
        )
        for seg in report.get("segments", []):
            print(
                f"\n  Tramo {seg['terrain_kind']} ({seg['t_start']:.0f}-{seg['t_end']:.0f}s) "
                f"-> {seg['protocol_id']}:"
            )
            print(
                f"    MAE {seg['mae_kmh']} km/h | v30 juego {seg.get('game_v30_kmh')} "
                f"| v30 sim {seg.get('sim_v30_kmh')} | n={seg['sample_count']}"
            )
        for sk in report.get("skipped_segments", []):
            print(
                f"\n  Omitido {sk['terrain_kind']} ({sk['t_start']}-{sk['t_end']}s): {sk['reason']}"
            )

    if args.index:
        from indexar_sesion import index_session_path, load_calibracion, save_calibracion

        cal = load_calibracion()
        _, added, _ = index_session_path(path, cal, reindex=False)
        if added:
            save_calibracion(cal)
            print(f"Indexado calibracion.json: +{added} filas")
        else:
            print("Indexacion: ya existia (usa indexar_sesion.py --reindex para actualizar)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())