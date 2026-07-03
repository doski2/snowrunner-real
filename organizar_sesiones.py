"""Mueve JSON de sesion a telemetria/sesiones/<vehiculo>/ y actualiza calibracion.json.

  python organizar_sesiones.py          # dry-run
  python organizar_sesiones.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CALIBRACION_PATH = os.path.join(ROOT, "datos", "indices", "calibracion.json")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from camiones.registry import VEHICLES  # noqa: E402
from telemetria import (  # noqa: E402
    ARCHIVE_SESSION_SUBDIR,
    TELEMETRY_DIR,
    iter_session_json_paths,
    load_session,
    session_subdir_for_vehicle,
    vehicle_id_from_session_name,
)


def _vehicle_for_json(path: str) -> str:
    try:
        session = load_session(path)
        vid = (session.meta.vehicle_id or "").strip()
        if vid:
            return vid
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    sid = os.path.basename(path).removesuffix(".json")
    return vehicle_id_from_session_name(sid) or "_sin_clasificar"


def plan_moves() -> list[tuple[str, str]]:
    moves: list[tuple[str, str]] = []
    for path in iter_session_json_paths(include_archived=True):
        parent = os.path.basename(os.path.dirname(path))
        if parent != os.path.basename(TELEMETRY_DIR):
            continue
        vid = _vehicle_for_json(path)
        dest = os.path.join(session_subdir_for_vehicle(vid), os.path.basename(path))
        if os.path.normcase(path) != os.path.normcase(dest):
            moves.append((path, dest))
    return moves


def ensure_vehicle_dirs() -> None:
    for vid in VEHICLES:
        os.makedirs(session_subdir_for_vehicle(vid), exist_ok=True)
    os.makedirs(os.path.join(TELEMETRY_DIR, ARCHIVE_SESSION_SUBDIR), exist_ok=True)


def update_calibracion_paths() -> int:
    if not os.path.isfile(CALIBRACION_PATH):
        return 0
    with open(CALIBRACION_PATH, encoding="utf-8") as f:
        cal = json.load(f)
    updated = 0
    for entry in cal.get("sessions", []):
        sf = (entry.get("session_file") or "").replace("/", os.sep)
        if not sf:
            continue
        base = os.path.basename(sf)
        vid = (entry.get("vehicle_id") or "").strip()
        if not vid:
            vid = vehicle_id_from_session_name(base.removesuffix(".json"))
        if not vid:
            continue
        new_rel = os.path.join("telemetria", "sesiones", vid, base)
        if sf != new_rel:
            entry["session_file"] = new_rel
            updated += 1
    if updated:
        with open(CALIBRACION_PATH, "w", encoding="utf-8") as f:
            json.dump(cal, f, indent=2, ensure_ascii=False)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Organizar sesiones CE por vehiculo")
    parser.add_argument("--apply", action="store_true", help="Ejecutar movimientos y actualizar indice")
    args = parser.parse_args()

    ensure_vehicle_dirs()
    moves = plan_moves()
    if not moves:
        print("Nada que mover (ya organizado o sin JSON en raiz).")
    else:
        print(f"Movimientos planificados: {len(moves)}")
        for src, dest in moves:
            print(f"  {os.path.relpath(src, ROOT)}")
            print(f"    -> {os.path.relpath(dest, ROOT)}")
        if args.apply:
            for src, dest in moves:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if os.path.isfile(dest):
                    print(f"  omitido (dest existe): {dest}")
                    continue
                shutil.move(src, dest)
            print("Movidos.")

    if args.apply:
        n = update_calibracion_paths()
        print(f"calibracion.json: {n} rutas session_file actualizadas")
    else:
        print("\nDry-run. Usa --apply para mover y actualizar calibracion.json")

    # Resumen
    by_vehicle: dict[str, int] = {}
    for p in iter_session_json_paths(include_archived=True):
        parent = os.path.basename(os.path.dirname(p))
        key = parent if parent != os.path.basename(TELEMETRY_DIR) else "(raiz)"
        by_vehicle[key] = by_vehicle.get(key, 0) + 1
    print("\nSesiones en disco:")
    for k in sorted(by_vehicle):
        print(f"  {k}: {by_vehicle[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
