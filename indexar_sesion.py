"""Indexa sesiones CE importadas en datos/indices/calibracion.json.

  python indexar_sesion.py telemetria/sesiones/ce_....json
  python indexar_sesion.py --all
  python indexar_sesion.py --all --reindex
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = os.path.dirname(os.path.abspath(__file__))
CALIBRACION_PATH = os.path.join(ROOT, "datos", "indices", "calibracion.json")
TELEMETRY_DIR = os.path.join(ROOT, "telemetria", "sesiones")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from telemetria import (  # noqa: E402
    TelemetrySession,
    compare_session_by_terrain,
    iter_session_json_paths,
    list_sessions,
    load_session,
)


def load_calibracion() -> dict[str, Any]:
    if os.path.isfile(CALIBRACION_PATH):
        with open(CALIBRACION_PATH, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("sessions", [])
        return data
    return {
        "version": 1,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "sessions": [],
        "notes": "Append via indexar_sesion.py (oleada 2). MAE barro objetivo < 15 km/h.",
    }


def save_calibracion(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CALIBRACION_PATH), exist_ok=True)
    data["updated_utc"] = datetime.now(timezone.utc).isoformat()
    with open(CALIBRACION_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _ctx_fields(meta) -> dict[str, Any]:
    ctx = dict(meta.session_context or {})
    setup = dict(ctx.get("setup") or {})
    return {
        "map": meta.map_name or ctx.get("map", ""),
        "location_note": meta.location_note or ctx.get("location_note", ""),
        "baseline_tag": ctx.get("baseline_tag", ""),
        "clima": ctx.get("clima", ""),
        "hora_juego": ctx.get("hora_juego", ""),
        "build": ctx.get("build_juego", ""),
        "mod_commit": ctx.get("mod_commit", ""),
        "setup": setup,
        "session_context": ctx,
    }


def _segment_summary(seg: dict) -> dict[str, Any]:
    return {
        "terrain_kind": seg.get("terrain_kind"),
        "compare_kind": seg.get("compare_kind"),
        "protocol_id": seg.get("protocol_id"),
        "t_start": seg.get("t_start"),
        "t_end": seg.get("t_end"),
        "duration_s": seg.get("duration_s"),
        "mae_kmh": seg.get("mae_kmh"),
        "game_v30_kmh": seg.get("game_v30_kmh"),
        "sim_v30_kmh": seg.get("sim_v30_kmh"),
        "sample_count": seg.get("sample_count"),
    }


def build_entries_from_session(
    session: TelemetrySession,
    *,
    session_file: str = "",
) -> list[dict[str, Any]]:
    """Filas session + segment para calibracion.json."""
    if not session.samples:
        return []

    report = compare_session_by_terrain(session)
    meta = session.meta
    common = {
        "session_id": meta.id,
        "session_file": session_file,
        "vehicle_id": meta.vehicle_id,
        **_ctx_fields(meta),
        "indexed_utc": datetime.now(timezone.utc).isoformat(),
    }
    whole = report.get("whole_session") or {}
    segments_raw = report.get("segments") or []
    terrain_counts = report.get("terrain_sample_counts") or {}
    mud_grade_counts = report.get("mud_grade_sample_counts") or {}

    session_entry: dict[str, Any] = {
        **common,
        "entry_type": "session",
        "protocol_id": report.get("protocol_id_whole") or meta.protocol_id,
        "terrain_counts": terrain_counts,
        "mud_grade_counts": mud_grade_counts,
        "whole_mae_kmh": whole.get("mae_kmh"),
        "game_v30_kmh": whole.get("game_v30_kmh"),
        "sim_v30_kmh": whole.get("sim_v30_kmh"),
        "sample_count": whole.get("sample_count", len(session.samples)),
        "duration_s": round(meta.duration_s, 1),
        "segments": [_segment_summary(s) for s in segments_raw],
        "skipped_segments": report.get("skipped_segments") or [],
    }

    entries: list[dict[str, Any]] = [session_entry]

    seen_seg: set[str] = set()
    for seg in segments_raw:
        t_start = seg.get("t_start", 0)
        kind = seg.get("terrain_kind") or "unknown"
        seg_key = f"{meta.id}__{kind}_{int(float(t_start))}"
        if seg_key in seen_seg:
            continue
        seen_seg.add(seg_key)
        mae = seg.get("mae_kmh")
        entries.append(
            {
                **common,
                "entry_type": "segment",
                "segment_id": seg_key,
                "protocol_id": seg.get("protocol_id") or meta.protocol_id,
                "terrain_kind": kind,
                "compare_kind": seg.get("compare_kind"),
                "t_start": seg.get("t_start"),
                "t_end": seg.get("t_end"),
                "duration_s": seg.get("duration_s"),
                "mae_kmh": mae,
                "whole_mae_kmh": mae,
                "game_v30_kmh": seg.get("game_v30_kmh"),
                "sim_v30_kmh": seg.get("sim_v30_kmh"),
                "sample_count": seg.get("sample_count"),
            }
        )

    return entries


def _entry_key(entry: dict[str, Any]) -> str:
    if entry.get("entry_type") == "segment":
        return str(entry.get("segment_id") or entry.get("session_id"))
    return str(entry.get("session_id"))


def remove_session_entries(cal: dict[str, Any], session_id: str) -> int:
    before = len(cal.get("sessions", []))
    cal["sessions"] = [
        e for e in cal.get("sessions", []) if e.get("session_id") != session_id
    ]
    return before - len(cal["sessions"])


def session_is_indexed(cal: dict[str, Any], session_id: str) -> bool:
    return any(
        e.get("session_id") == session_id and e.get("entry_type") == "session"
        for e in cal.get("sessions", [])
    )


def merge_entries(
    cal: dict[str, Any],
    new_entries: list[dict[str, Any]],
    *,
    reindex: bool = False,
) -> tuple[int, int]:
    """Inserta entradas; devuelve (añadidas, reemplazadas)."""
    if not new_entries:
        return 0, 0

    session_id = new_entries[0].get("session_id", "")
    replaced = 0
    if reindex and session_id:
        replaced = remove_session_entries(cal, session_id)

    existing_keys = {_entry_key(e) for e in cal.get("sessions", [])}
    added = 0
    for entry in new_entries:
        key = _entry_key(entry)
        if key in existing_keys and not reindex:
            continue
        if key in existing_keys and reindex:
            cal["sessions"] = [e for e in cal["sessions"] if _entry_key(e) != key]
        cal.setdefault("sessions", []).append(entry)
        existing_keys.add(key)
        added += 1
    return added, replaced


def index_session_path(
    path: str,
    cal: dict[str, Any] | None = None,
    *,
    reindex: bool = False,
    dry_run: bool = False,
) -> tuple[list[dict[str, Any]], int, int]:
    session = load_session(path)
    rel = os.path.relpath(path, ROOT)
    entries = build_entries_from_session(session, session_file=rel)
    if not entries:
        return [], 0, 0

    if dry_run:
        return entries, len(entries), 0

    if cal is None:
        cal = load_calibracion()

    if session_is_indexed(cal, session.meta.id) and not reindex:
        return entries, 0, 0

    added, replaced = merge_entries(cal, entries, reindex=reindex or session_is_indexed(cal, session.meta.id))
    return entries, added, replaced


def index_all_sessions(*, reindex: bool = False, dry_run: bool = False) -> int:
    paths = list_sessions()
    if not paths:
        print("No hay JSON en telemetria/sesiones/")
        return 1

    cal = None if dry_run else load_calibracion()
    total_added = 0
    total_replaced = 0
    indexed = 0
    skipped = 0

    for path in paths:
        entries, added, replaced = index_session_path(path, cal, reindex=reindex, dry_run=dry_run)
        if not entries:
            print(f"  omitido (sin muestras): {os.path.basename(path)}")
            continue
        if added == 0 and not dry_run and not reindex:
            skipped += 1
            continue
        indexed += 1
        total_added += added
        total_replaced += replaced
        sid = entries[0].get("session_id", "?")
        n_seg = sum(1 for e in entries if e.get("entry_type") == "segment")
        print(f"  {sid}: +{added} filas ({n_seg} tramos)")

    if not dry_run and cal is not None:
        save_calibracion(cal)
        print(
            f"\nCalibracion: {CALIBRACION_PATH} "
            f"({len(cal.get('sessions', []))} filas; +{total_added} nuevas, {total_replaced} reemplazadas)"
        )
    elif dry_run:
        print(f"\n(dry-run) {indexed} sesiones, {total_added} filas potenciales")

    if skipped:
        print(f"  ({skipped} ya indexadas — usa --reindex para actualizar)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Indexar sesiones CE en calibracion.json")
    parser.add_argument("session_json", nargs="?", help="Ruta a JSON de sesion importada")
    parser.add_argument("--all", action="store_true", help="Indexar todos los JSON en telemetria/sesiones/")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Reemplazar filas existentes de la(s) sesion(es)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Mostrar filas sin escribir")
    args = parser.parse_args(argv)

    if args.all:
        return index_all_sessions(reindex=args.reindex, dry_run=args.dry_run)

    if not args.session_json:
        parser.print_help()
        return 1

    path = args.session_json
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    if not os.path.isfile(path):
        print(f"No encontrado: {path}")
        return 1

    cal = None if args.dry_run else load_calibracion()
    entries, added, replaced = index_session_path(path, cal, reindex=args.reindex, dry_run=args.dry_run)
    if not entries:
        print("Sesion sin muestras validas.")
        return 1

    if args.dry_run:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
        return 0

    if cal is not None:
        save_calibracion(cal)
    sid = entries[0].get("session_id")
    n_seg = sum(1 for e in entries if e.get("entry_type") == "segment")
    if added == 0 and not args.reindex:
        print(f"Ya indexada: {sid} (usa --reindex)")
        return 0
    print(f"Indexado {sid}: +{added} filas ({n_seg} tramos, {replaced} reemplazadas)")
    print(f"  -> {CALIBRACION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
