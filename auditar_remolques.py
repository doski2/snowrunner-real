"""Auditoria Fase 8: masa y CoG de remolques en initial.pak.bak.

Ejecutar:
  python auditar_remolques.py
  python auditar_remolques.py --pak ruta\\initial.pak.bak
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import zipfile

from camiones.registry import trailer_tare_kg
from repack_pak import BACKUP, split_zip_tail

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(ROOT, "remolques_inventario.json")

MASS_RE = re.compile(r'Mass="([0-9.]+)"')
COG_RE = re.compile(r'CenterOfMassOffset="\(([^"]+)\)"')
ATTACH_RE = re.compile(r'AttachType="([^"]+)"')

TRAILER_KEYS: tuple[str, ...] = (
    "[media]/classes/trucks/trailers/scout_trailer_offroad_cargo.xml",
    "[media]/classes/trucks/trailers/scout_trailer_offroad.xml",
    "[media]/classes/trucks/trailers/scout_trailer_oiltank.xml",
    "[media]/classes/trucks/trailers/semitrailer_flatbed_5.xml",
    "[media]/classes/trucks/trailers/semitrailer_sideboard_5.xml",
    "[media]/classes/trucks/trailers/semitrailer_oiltank.xml",
)


def audit_trailer_xml(text: str) -> dict:
    masses = [float(m) for m in MASS_RE.findall(text)]
    main = max(masses) if masses else 0.0
    cogs = COG_RE.findall(text)
    attach = ATTACH_RE.search(text)
    return {
        "mass_all_bodies_kg": round(sum(masses), 1),
        "mass_largest_body_kg": main,
        "mass_parts_kg": masses,
        "center_of_mass_offsets": cogs,
        "attach_type": attach.group(1) if attach else "Drawbar",
        "wheel_count": text.count("<Wheel "),
        "axle_count": text.count("<Axle "),
    }


def _registry_tare_for_short_name(short: str) -> float:
    """Tara estimada usada en CE/sim (`camiones.registry.trailer_tare_kg`)."""
    stem = short.removesuffix(".xml")
    return trailer_tare_kg(stem)


def load_trailers(pak_path: str = BACKUP) -> dict[str, dict]:
    if not os.path.isfile(pak_path):
        raise FileNotFoundError(f"No existe el .pak de backup: {pak_path}")

    with open(pak_path, "rb") as f:
        zip_bytes, _ = split_zip_tail(f.read())
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = set(zf.namelist())
        out: dict[str, dict] = {}
        for arc in TRAILER_KEYS:
            if arc not in names:
                base = arc.rsplit("/", 1)[-1]
                matches = [n for n in names if n.endswith(base)]
                if not matches:
                    continue
                arc = matches[0]
            short = arc.rsplit("/", 1)[-1]
            info = audit_trailer_xml(zf.read(arc).decode("utf-8"))
            info["pak_path"] = arc
            info["registry_tare_kg"] = _registry_tare_for_short_name(short)
            out[short] = info
        return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditar masas de remolques en initial.pak.bak")
    parser.add_argument("--pak", default=BACKUP, help=f"Ruta al .pak (default: {BACKUP})")
    parser.add_argument("--out", default=OUT_JSON, help=f"JSON de salida (default: {OUT_JSON})")
    args = parser.parse_args(argv)

    try:
        trailers = load_trailers(args.pak)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    payload = {"source": os.path.abspath(args.pak), "trailers": trailers}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    missing = len(TRAILER_KEYS) - len(trailers)
    print(f"Remolques auditados: {len(trailers)}/{len(TRAILER_KEYS)}")
    if missing:
        print(f"  AVISO: faltan {missing} entradas en el .pak")

    for name, info in sorted(trailers.items()):
        reg = info["registry_tare_kg"]
        drift = abs(reg - info["mass_largest_body_kg"]) > 1.0
        reg_note = f"  registry={reg:.0f}" if drift else ""
        print(
            f"  {name:<35} mayor={info['mass_largest_body_kg']:.0f} kg  "
            f"soma={info['mass_all_bodies_kg']:.0f} kg  {info['attach_type']}{reg_note}"
        )
    print(f"\nGuardado: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
