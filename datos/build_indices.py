"""Genera indices/manifest.json y calibracion.json (esqueleto).

  python datos/build_indices.py
  python datos/build_indices.py --calibracion-only
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(ROOT, "datos")
INDICES = os.path.join(DATOS, "indices")
OFFSETS_PATH = os.path.join(ROOT, "cheat_engine", "offsets_referencia.json")
MANIFEST_PATH = os.path.join(INDICES, "manifest.json")
CALIBRACION_PATH = os.path.join(INDICES, "calibracion.json")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from camiones.registry import EMPTY_MASS_KG, VEHICLES  # noqa: E402
from repack_pak import BACKUP, PAK_OUT  # noqa: E402


def _git_short_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _file_info(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    st = os.stat(path)
    return {
        "path": os.path.abspath(path),
        "size_bytes": st.st_size,
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
    }


def build_manifest() -> dict:
    offsets: dict = {}
    if os.path.isfile(OFFSETS_PATH):
        with open(OFFSETS_PATH, encoding="utf-8") as f:
            offsets = json.load(f)

    vehicles_mod = {}
    for vid, mod in VEHICLES.items():
        vehicles_mod[vid] = {
            "label": mod.label,
            "game_id": mod.game_id,
            "ce_id": mod.ce_id,
            "xml_file": mod.xml_file,
            "sim_module": mod.sim_module,
            "empty_mass_kg": EMPTY_MASS_KG.get(vid),
            "notes": mod.notes,
        }

    return {
        "version": 1,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "mod_commit": _git_short_commit(),
        "game_version": offsets.get("game_version", ""),
        "offsets_source": offsets.get("source", ""),
        "singletons": offsets.get("singletons", {}),
        "empty_mass_kg": dict(EMPTY_MASS_KG),
        "vehicles_mod": vehicles_mod,
        "pak": {
            "backup": _file_info(BACKUP),
            "mod_out": _file_info(PAK_OUT),
        },
        "paths": {
            "telemetry_sessions": os.path.join(ROOT, "telemetria", "sesiones"),
            "catalogo": os.path.join(DATOS, "catalogo"),
            "ce_log_primary": os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "My Games",
                "SnowRunner",
                "base",
                "telemetria_ce_log.csv",
            ),
        },
    }


def ensure_calibracion() -> dict:
    if os.path.isfile(CALIBRACION_PATH):
        with open(CALIBRACION_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if "sessions" in data:
            return data
    return {
        "version": 1,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "sessions": [],
        "notes": "Append via indexar_sesion.py (oleada 2). MAE barro objetivo < 15 km/h.",
    }


def write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generar manifest.json y calibracion.json")
    parser.add_argument(
        "--calibracion-only",
        action="store_true",
        help="Solo crear/validar calibracion.json",
    )
    args = parser.parse_args(argv)

    if not args.calibracion_only:
        manifest = build_manifest()
        write_json(MANIFEST_PATH, manifest)
        print(f"manifest: {MANIFEST_PATH}")
        print(f"  build: {manifest.get('game_version', '?')}")
        print(f"  mod_commit: {manifest.get('mod_commit') or '(sin git)'}")
        pak = manifest.get("pak", {}).get("backup") or {}
        if pak:
            print(f"  initial.pak.bak: {pak.get('size_bytes', 0) // 1024 // 1024} MB")

    cal = ensure_calibracion()
    cal["updated_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(CALIBRACION_PATH, cal)
    print(f"calibracion: {CALIBRACION_PATH} ({len(cal.get('sessions', []))} sesiones)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
