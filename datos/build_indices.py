"""Genera indices/manifest.json del mod.

  python datos/build_indices.py
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
MANIFEST_PATH = os.path.join(INDICES, "manifest.json")

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
        "version": 2,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "mod_commit": _git_short_commit(),
        "empty_mass_kg": dict(EMPTY_MASS_KG),
        "vehicles_mod": vehicles_mod,
        "pak": {
            "backup": _file_info(BACKUP),
            "mod_out": _file_info(PAK_OUT),
        },
        "paths": {
            "catalogo": os.path.join(DATOS, "catalogo"),
        },
    }


def write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generar manifest.json del mod")
    args = parser.parse_args(argv)

    manifest = build_manifest()
    write_json(MANIFEST_PATH, manifest)
    print(f"manifest: {MANIFEST_PATH}")
    print(f"  mod_commit: {manifest.get('mod_commit') or '(sin git)'}")
    pak = manifest.get("pak", {}).get("backup") or {}
    if pak:
        print(f"  initial.pak.bak: {pak.get('size_bytes', 0) // 1024 // 1024} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
