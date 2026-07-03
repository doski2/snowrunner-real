"""Ruedas del vehiculo activo (TRUCK_WHEEL_MODEL) — sustancia/contacto y mud_grade.

Uso calibracion TERR (PENDIENTES.md):
  1. Parada quieto 30 s -> python scan_wheel_substance.py --save tierra_seca
  2. Otra parada            -> python scan_wheel_substance.py --save barro_ligero
  3. Solo cambios           -> python scan_wheel_substance.py --diff tierra_seca barro_ligero

--diff imprime resumen terrain_kind/mud_grade y solo offsets clave (+2FC/+2EC/+2B4).
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import memoria_havok as mh  # noqa: E402

WHEEL_VTABLE_ABS = 0x7FF67DC03610
OFF_WHEELS_BEGIN = 0x200
OFF_WHEELS_END = 0x208
SCAN_END = 0x400

# Offsets Havok calibrados — lo que discrimina terreno en classify_*
KEY_WHEEL_OFFSETS = ("+2FC", "+2EC", "+2B4")
TERRAIN_SUMMARY_KEYS = (
    "terrain_kind",
    "wheel_grip",
    "contact_avg",
    "surface_deform_avg",
    "contact_min",
    "contact_max",
    "grip_min",
    "grip_max",
    "mud_grade",
    "mud_grade_label",
    "wheel_kinds",
)


def read_u64(h: int, addr: int) -> int | None:
    b = mh.read_bytes(h, addr, 8)
    return struct.unpack("<Q", b)[0] if b else None


def wheel_pointers(h: int, veh: int) -> list[int]:
    begin = read_u64(h, veh + OFF_WHEELS_BEGIN)
    end = read_u64(h, veh + OFF_WHEELS_END)
    if not begin or not end or end < begin:
        return []
    count = (end - begin) // 8
    if count <= 0 or count > 16:
        return []
    out: list[int] = []
    for i in range(count):
        p = read_u64(h, begin + i * 8)
        if p and p > 0x10000:
            out.append(p)
    return out


def scan_wheel_object(h: int, wheel: int) -> dict:
    vt = read_u64(h, wheel)
    floats: list[dict] = []
    for off in range(0, SCAN_END, 4):
        v = mh.read_f32(h, wheel + off)
        if v is None or v == 0.0 or not (-50 < v < 50):
            continue
        floats.append({"off": f"+{off:03X}", "f": round(v, 4)})
    return {"wheel": hex(wheel), "vtable": hex(vt) if vt else "0", "floats": floats}


def terrain_summary_from_terrain(terrain: dict) -> dict[str, str]:
    return {k: str(terrain.get(k, "") or "") for k in TERRAIN_SUMMARY_KEYS}


def snapshot(h: int, base: int) -> dict:
    sample = mh.read_active_sample(h, base)
    if not sample:
        return {"error": "sin vehiculo activo (mapa conduciendo)"}
    veh = int(sample["veh"], 16)
    wheels = wheel_pointers(h, veh)
    terrain = mh.read_wheel_terrain(h, veh, vel_y=sample.get("vel_y"))
    return {
        "vehicle_id": sample.get("vehicle_id"),
        "speed_kmh": sample.get("speed_kmh"),
        "pos_x": sample.get("pos_x"),
        "pos_z": sample.get("pos_z"),
        "veh": sample["veh"],
        "wheel_count": len(wheels),
        "terrain": terrain_summary_from_terrain(terrain),
        "wheels": [scan_wheel_object(h, w) for w in wheels],
    }


def infer_terrain_from_snapshot(data: dict) -> dict[str, str]:
    """Reconstruye terrain si el JSON es antiguo (solo floats por rueda)."""
    if data.get("terrain"):
        return data["terrain"]
    grips: list[float] = []
    contacts: list[float] = []
    deforms: list[float] = []
    for ww in data.get("wheels") or []:
        f = {x["off"]: x["f"] for x in ww.get("floats", [])}
        if "+2FC" in f:
            grips.append(f["+2FC"])
        if "+2EC" in f:
            contacts.append(f["+2EC"])
        if "+2B4" in f:
            deforms.append(f["+2B4"])
    if not grips:
        return {}
    surfaces = [
        mh._effective_surface(b, c)
        for b, c in zip(deforms or contacts, contacts or deforms)
    ]
    if not surfaces:
        surfaces = deforms or contacts
    terrain = mh.classify_terrain_from_wheels(grips, surfaces)
    terrain.update(
        mh._terrain_grade_fields(
            terrain.get("terrain_kind", ""),
            grips,
            contacts,
            deforms,
        )
    )
    return terrain_summary_from_terrain(terrain)


def diff_terrain_summary(a: dict, b: dict) -> list[tuple[str, str, str]]:
    """Campos de terreno que cambian entre dos snapshots."""
    ta = infer_terrain_from_snapshot(a)
    tb = infer_terrain_from_snapshot(b)
    changes: list[tuple[str, str, str]] = []
    for key in TERRAIN_SUMMARY_KEYS:
        va = (ta.get(key) or "").strip()
        vb = (tb.get(key) or "").strip()
        if va != vb:
            changes.append((key, va, vb))
    return changes


def diff_snapshots(
    a: dict,
    b: dict,
    *,
    key_offsets: tuple[str, ...] = KEY_WHEEL_OFFSETS,
    min_delta: float = 0.01,
) -> list[dict]:
    """Offsets float que cambian (por defecto solo +2FC/+2EC/+2B4)."""
    changes: list[dict] = []
    wa, wb = a.get("wheels", []), b.get("wheels", [])
    for i, (ra, rb) in enumerate(zip(wa, wb)):
        fa = {x["off"]: x["f"] for x in ra.get("floats", [])}
        fb = {x["off"]: x["f"] for x in rb.get("floats", [])}
        offs = sorted(set(fa) | set(fb))
        if key_offsets:
            offs = [off for off in offs if off in key_offsets]
        for off in offs:
            va, vb = fa.get(off), fb.get(off)
            if va is None and vb is None:
                continue
            if va is None or vb is None or abs(vb - va) > min_delta:
                changes.append(
                    {
                        "wheel": i,
                        "off": off,
                        "a": va,
                        "b": vb,
                        "delta": round((vb or 0) - (va or 0), 4) if va is not None and vb is not None else None,
                    }
                )
    changes.sort(key=lambda x: -(abs(x["delta"]) if x["delta"] is not None else 999))
    return changes


def print_terrain_block(terrain: dict, *, prefix: str = "  ") -> None:
    if not terrain:
        return
    print(
        f"{prefix}terrain_kind={terrain.get('terrain_kind')} "
        f"mud_grade={terrain.get('mud_grade')} ({terrain.get('mud_grade_label')})"
    )
    print(
        f"{prefix}grip={terrain.get('wheel_grip')} "
        f"contact={terrain.get('contact_avg')} "
        f"deform={terrain.get('surface_deform_avg')}"
    )
    if terrain.get("wheel_kinds"):
        print(f"{prefix}wheel_kinds={terrain.get('wheel_kinds')}")


def _load_snap(snap_dir: str, name: str) -> dict:
    path = os.path.join(snap_dir, f"{name}.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Escanear terreno por rueda (TRUCK_WHEEL_MODEL)")
    parser.add_argument("--save", metavar="NAME", help="Guardar JSON en cheat_engine/wheel_snaps/")
    parser.add_argument("--diff", nargs=2, metavar=("A", "B"), help="Comparar dos snapshots (solo cambios)")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Con --diff: todos los floats, no solo +2FC/+2EC/+2B4",
    )
    parser.add_argument("--vtable", default=hex(WHEEL_VTABLE_ABS), help="Vtable TRUCK_WHEEL_MODEL")
    args = parser.parse_args()

    snap_dir = os.path.join(os.path.dirname(__file__), "wheel_snaps")
    os.makedirs(snap_dir, exist_ok=True)

    if args.diff:
        try:
            sa = _load_snap(snap_dir, args.diff[0])
            sb = _load_snap(snap_dir, args.diff[1])
        except FileNotFoundError as exc:
            print(f"No existe snapshot: {exc.filename}")
            print(f"Carpeta: {snap_dir}")
            print("Guarda antes con: python cheat_engine/scan_wheel_substance.py --save <nombre>")
            return 1

        print(f"Diff {args.diff[0]} vs {args.diff[1]} ({sa.get('vehicle_id')} -> {sb.get('vehicle_id')})")
        terrain_changes = diff_terrain_summary(sa, sb)
        if terrain_changes:
            print("\nCambios terreno (solo lo distinto):")
            for key, va, vb in terrain_changes:
                print(f"  {key}: {va!r} -> {vb!r}")
        else:
            print("\nSin cambios en terrain_kind / mud_grade / medias.")

        key_offs: tuple[str, ...] = () if args.full else KEY_WHEEL_OFFSETS
        float_changes = diff_snapshots(sa, sb, key_offsets=key_offs)
        if float_changes:
            label = "todos los floats" if args.full else "offsets clave"
            print(f"\nCambios por rueda ({label}):")
            for row in float_changes:
                da = row["a"]
                db = row["b"]
                d = row["delta"]
                if d is not None:
                    print(f"  rueda {row['wheel']} {row['off']}: {da} -> {db} (d={d})")
                else:
                    print(f"  rueda {row['wheel']} {row['off']}: {da!r} -> {db!r}")
        elif not terrain_changes:
            print("Sin cambios detectados.")
        return 0

    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo")
        return 1
    h, base, pid = opened
    try:
        data = snapshot(h, base)
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)

    if "error" in data:
        print(data["error"])
        return 1

    expected_vt = int(args.vtable, 16)
    print(f"PID={pid} veh={data['veh']} id={data['vehicle_id']} km/h={data['speed_kmh']}")
    if data.get("pos_x") is not None:
        print(f"  pos=({data.get('pos_x')}, {data.get('pos_z')})")
    print_terrain_block(data.get("terrain") or {})
    print(f"  ruedas: {data['wheel_count']}")

    if args.save:
        path = os.path.join(snap_dir, f"{args.save}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nGuardado: {path}")
        print("Otro terreno y: python cheat_engine/scan_wheel_substance.py --diff <este> <otro>")
    else:
        print("Tip: --save <nombre> en cada parada TERR; --diff A B ve solo cambios")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
