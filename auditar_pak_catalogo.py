"""Auditoria Capa B: indexar XML de initial.pak.bak en datos/catalogo/.

Ejecutar:
  python auditar_pak_catalogo.py
  python auditar_pak_catalogo.py --pak ruta\\initial.pak.bak --only trucks engines
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import zipfile
from typing import Any

from camiones.registry import VEHICLES
from repack_pak import BACKUP, split_zip_tail

ROOT = os.path.dirname(os.path.abspath(__file__))
CATALOGO_DIR = os.path.join(ROOT, "datos", "catalogo")

MAIN_TRUCK_RE = re.compile(r"\[media\]/classes/trucks/[^/]+\.xml$")
MASS_RE = re.compile(r'Mass="([0-9.]+)"')
COG_RE = re.compile(r'CenterOfMassOffset="\(([^"]+)\)"')
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


def _attr(text: str, name: str, *, after: str = "") -> str:
    chunk = text
    if after:
        pos = text.find(after)
        if pos >= 0:
            chunk = text[pos : pos + 4000]
    m = re.search(rf'\b{name}="([^"]*)"', chunk)
    return m.group(1) if m else ""


def _attrs_block(text: str, tag: str, *, scope: str = "") -> dict[str, str]:
    chunk = text
    if scope:
        pos = text.find(scope)
        if pos >= 0:
            chunk = text[pos:]
    m = re.search(rf"<{tag}\b([^>]*)>", chunk, re.DOTALL)
    if not m:
        return {}
    return dict(ATTR_RE.findall(m.group(1)))


def _all_engine_blocks(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in re.finditer(r"<Engine\b([^>]*?)(?:>(.*?)</Engine>|/>)", text, re.DOTALL):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        name = attrs.get("Name") or attrs.get("_template") or ""
        block = m.group(0)
        out.append((name, block))
    return out


def _template_defaults(text: str, template_name: str) -> dict[str, str]:
    m = re.search(rf"<{re.escape(template_name)}\b([^/>]*)/?>", text)
    if m:
        return dict(ATTR_RE.findall(m.group(1)))
    m = re.search(rf'\b_template="{re.escape(template_name)}"([^/>]*)/?>', text)
    if m:
        return dict(ATTR_RE.findall(m.group(1)))
    return {}


def _engine_parse_text(text: str) -> str:
    if "<EngineVariants>" in text:
        return text[text.find("<EngineVariants>") :]
    if "</_templates>" in text:
        return text[text.rfind("</_templates>") :]
    return text


def _float(val: str | None) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def parse_truck_xml(text: str, pak_path: str) -> dict[str, Any]:
    short = pak_path.rsplit("/", 1)[-1]
    truck_id = short.removesuffix(".xml")
    masses = [float(x) for x in MASS_RE.findall(text)]
    cogs = COG_RE.findall(text)
    td = _attrs_block(text, "TruckData", scope="<Truck>")
    wheels = _attrs_block(text, "Wheels", scope="<Truck>")
    engine_sock = _attrs_block(text, "EngineSocket", scope="<Truck>")
    gearbox_sock = _attrs_block(text, "GearboxSocket", scope="<Truck>")
    mod_id = next((v.id for v in VEHICLES.values() if v.xml_file == short), "")
    return {
        "id": truck_id,
        "pak_path": pak_path,
        "mod_vehicle_id": mod_id,
        "truck_type": td.get("TruckType", ""),
        "fuel_capacity": _float(td.get("FuelCapacity")),
        "responsiveness": _float(td.get("Responsiveness")),
        "steer_speed": _float(td.get("SteerSpeed")),
        "back_steer_speed": _float(td.get("BackSteerSpeed")),
        "diff_lock_type": td.get("DiffLockType", ""),
        "default_engine": engine_sock.get("Default", ""),
        "engine_socket_type": engine_sock.get("Type", ""),
        "default_gearbox": gearbox_sock.get("Default", ""),
        "gearbox_socket_type": gearbox_sock.get("Type", ""),
        "default_suspension": _attr(text, "Default", after="<SuspensionSocket"),
        "default_tire": wheels.get("DefaultTire", ""),
        "default_wheel_type": wheels.get("DefaultWheelType", ""),
        "mass_all_bodies_kg": round(sum(masses), 1) if masses else 0.0,
        "mass_largest_body_kg": max(masses) if masses else 0.0,
        "mass_parts_kg": masses,
        "center_of_mass_offsets": cogs,
        "wheel_count": text.count("<Wheel "),
    }


def parse_engine_xml(text: str, pak_path: str) -> list[dict[str, Any]]:
    short = pak_path.rsplit("/", 1)[-1]
    file_id = short.removesuffix(".xml")
    section = _engine_parse_text(text)
    variants: list[dict[str, Any]] = []
    for name, block in _all_engine_blocks(section):
        tmpl = _attr(block, "_template")
        inherited = _template_defaults(text, tmpl) if tmpl else {}
        head = re.search(r"<Engine\b([^>]*?)(?:>|/>)", block)
        direct = dict(ATTR_RE.findall(head.group(1))) if head else {}
        merged = {**inherited, **direct}
        if not name and not merged.get("Torque"):
            continue
        variants.append(
            {
                "name": name or file_id,
                "file_id": file_id,
                "pak_path": pak_path,
                "torque": _float(merged.get("Torque")),
                "max_delta_ang_vel": _float(merged.get("MaxDeltaAngVel")),
                "engine_responsiveness": _float(merged.get("EngineResponsiveness")),
                "fuel_consumption": _float(merged.get("FuelConsumption")),
                "brakes_delay": _float(merged.get("BrakesDelay")),
                "damage_capacity": _float(merged.get("DamageCapacity")),
                "critical_damage_threshold": _float(merged.get("CriticalDamageThreshold")),
                "_template": tmpl,
            }
        )
    if not variants:
        variants.append({"name": file_id, "file_id": file_id, "pak_path": pak_path})
    return variants


def parse_wheel_xml(text: str, pak_path: str) -> dict[str, Any]:
    short = pak_path.rsplit("/", 1)[-1]
    wheel_set_id = short.removesuffix(".xml")
    tires: list[dict[str, Any]] = []
    for tag in ("Wheel", "TruckTire"):
        for m in re.finditer(rf"<{tag}\b([^>]*)>(.*?)</{tag}>", text, re.DOTALL):
            wattrs = dict(ATTR_RE.findall(m.group(1)))
            inner = m.group(2)
            fr = re.search(r"<WheelFriction\b([^/>]*)/?>", inner)
            fattrs = dict(ATTR_RE.findall(fr.group(1))) if fr else {}
            fname = wattrs.get("Name", "")
            if not fname:
                continue
            tires.append(
                {
                    "name": fname,
                    "radius": _float(wattrs.get("Radius")),
                    "mass_kg": _float(wattrs.get("Mass")),
                    "substance_friction": _float(fattrs.get("SubstanceFriction")),
                    "body_friction": _float(fattrs.get("BodyFriction")),
                    "template": fattrs.get("_template", ""),
                }
            )
    tw = _attrs_block(text, "TruckWheels")
    return {
        "id": wheel_set_id,
        "pak_path": pak_path,
        "radius_default": _float(tw.get("Radius")),
        "width_default": _float(tw.get("Width")),
        "tires": tires,
    }


def parse_gearbox_xml(text: str, pak_path: str) -> list[dict[str, Any]]:
    short = pak_path.rsplit("/", 1)[-1]
    file_id = short.removesuffix(".xml")
    out: list[dict[str, Any]] = []
    for m in re.finditer(r"<Gearbox\b([^>]*)>(.*?)</Gearbox>", text, re.DOTALL):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        block = m.group(2)
        gears = []
        for gm in re.finditer(r"<(?:Gear|ReverseGear|HighGear)\b([^/>]*)/?>", block):
            gattrs = dict(ATTR_RE.findall(gm.group(1)))
            tag = gm.group(0).split(None, 1)[0].lstrip("<")
            gears.append(
                {
                    "kind": tag,
                    "ang_vel": _float(gattrs.get("AngVel")),
                    "fuel_modifier": _float(gattrs.get("FuelModifier")),
                }
            )
        params = {}
        pm = re.search(r"<GearboxParams\b([^/>]*)/?>", block)
        if pm:
            params = dict(ATTR_RE.findall(pm.group(1)))
        name = attrs.get("Name") or file_id
        out.append(
            {
                "name": name,
                "file_id": file_id,
                "pak_path": pak_path,
                "awd_consumption_modifier": _float(attrs.get("AWDConsumptionModifier")),
                "fuel_consumption": _float(attrs.get("FuelConsumption")),
                "gears": gears,
                "is_lower_gear_exists": params.get("IsLowerGearExists", ""),
                "is_high_gear_exists": params.get("IsHighGearExists", ""),
            }
        )
    return out


def parse_suspension_xml(text: str, pak_path: str) -> dict[str, Any]:
    short = pak_path.rsplit("/", 1)[-1]
    sid = short.removesuffix(".xml")
    suspensions: list[dict[str, Any]] = []
    for m in re.finditer(r"<Suspension\b([^/>]*)/?>", text):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        suspensions.append(
            {
                "wheel_type": attrs.get("WheelType", ""),
                "strength": _float(attrs.get("Strength")),
                "damping": _float(attrs.get("Damping")),
                "height": _float(attrs.get("Height")),
                "suspension_min": _float(attrs.get("SuspensionMin")),
            }
        )
    return {"id": sid, "pak_path": pak_path, "suspensions": suspensions}


def _open_pak(pak_path: str) -> zipfile.ZipFile:
    with open(pak_path, "rb") as f:
        zip_bytes, _ = split_zip_tail(f.read())
    return zipfile.ZipFile(io.BytesIO(zip_bytes))


def _paths_by_kind(names: set[str], kind: str) -> list[str]:
    if kind == "trucks":
        return sorted(n for n in names if MAIN_TRUCK_RE.match(n))
    if kind == "engines":
        return sorted(n for n in names if "/classes/engines/" in n and n.endswith(".xml"))
    if kind == "wheels":
        return sorted(n for n in names if "/classes/wheels/" in n and n.endswith(".xml"))
    if kind == "gearboxes":
        return sorted(n for n in names if "/classes/gearboxes/" in n and n.endswith(".xml"))
    if kind == "suspensions":
        return sorted(n for n in names if "/classes/suspensions/" in n and n.endswith(".xml"))
    return []


def build_catalog(pak_path: str = BACKUP, kinds: list[str] | None = None) -> dict[str, Any]:
    if not os.path.isfile(pak_path):
        raise FileNotFoundError(f"No existe el .pak de backup: {pak_path}")

    want = kinds or ["trucks", "engines", "wheels", "gearboxes", "suspensions"]
    with _open_pak(pak_path) as zf:
        names = set(zf.namelist())
        trucks: dict[str, dict] = {}
        engines: dict[str, dict] = {}
        wheels: dict[str, dict] = {}
        gearboxes: dict[str, dict] = {}
        suspensions: dict[str, dict] = {}

        if "trucks" in want:
            for arc in _paths_by_kind(names, "trucks"):
                text = zf.read(arc).decode("utf-8")
                entry = parse_truck_xml(text, arc)
                trucks[entry["id"]] = entry

        if "engines" in want:
            for arc in _paths_by_kind(names, "engines"):
                text = zf.read(arc).decode("utf-8")
                for eng in parse_engine_xml(text, arc):
                    key = f"{eng['file_id']}::{eng['name']}"
                    engines[key] = eng

        if "wheels" in want:
            for arc in _paths_by_kind(names, "wheels"):
                text = zf.read(arc).decode("utf-8")
                entry = parse_wheel_xml(text, arc)
                if entry["tires"]:
                    wheels[entry["id"]] = entry

        if "gearboxes" in want:
            for arc in _paths_by_kind(names, "gearboxes"):
                text = zf.read(arc).decode("utf-8")
                for gb in parse_gearbox_xml(text, arc):
                    key = f"{gb['file_id']}::{gb['name']}"
                    gearboxes[key] = gb

        if "suspensions" in want:
            for arc in _paths_by_kind(names, "suspensions"):
                text = zf.read(arc).decode("utf-8")
                entry = parse_suspension_xml(text, arc)
                if entry["suspensions"]:
                    suspensions[entry["id"]] = entry

    return {
        "source": os.path.abspath(pak_path),
        "counts": {
            "trucks": len(trucks),
            "engines": len(engines),
            "wheels": len(wheels),
            "gearboxes": len(gearboxes),
            "suspensions": len(suspensions),
        },
        "trucks": trucks,
        "engines": engines,
        "wheels": wheels,
        "gearboxes": gearboxes,
        "suspensions": suspensions,
    }


def write_catalog_files(catalog: dict[str, Any], out_dir: str = CATALOGO_DIR) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    meta = {
        "source": catalog["source"],
        "counts": catalog["counts"],
    }
    for key in ("trucks", "engines", "wheels", "gearboxes", "suspensions"):
        path = os.path.join(out_dir, f"{key}.json")
        payload = {**meta, key: catalog[key]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Indexar XML de initial.pak.bak en datos/catalogo/")
    parser.add_argument("--pak", default=BACKUP, help=f"Ruta al .pak (default: {BACKUP})")
    parser.add_argument(
        "--only",
        nargs="+",
        choices=["trucks", "engines", "wheels", "gearboxes", "suspensions"],
        help="Solo extraer tipos indicados",
    )
    parser.add_argument("--out", default=CATALOGO_DIR, help="Carpeta datos/catalogo/")
    args = parser.parse_args(argv)

    try:
        catalog = build_catalog(args.pak, kinds=args.only)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    paths = write_catalog_files(catalog, args.out)
    c = catalog["counts"]
    print(
        f"Catalogo: {c['trucks']} camiones, {c['engines']} motores, "
        f"{c['wheels']} juegos rueda, {c['gearboxes']} cajas, {c['suspensions']} suspensiones"
    )
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
