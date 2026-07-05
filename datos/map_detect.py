"""Deteccion de mapa SnowRunner para metadatos de sesion CE.

Fuentes (en orden):
  1. --map explicito del usuario
  2. game.log / LegacyLog.txt (ultimo level_id cargado)
  3. Memoria del proceso (cadena level_us_XX_XX)
  4. Vacio + aviso (no adivinar Michigan)
"""

from __future__ import annotations

import argparse
import ctypes
import os
import re
import sys
from dataclasses import dataclass
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SNOWRUNNER_LOG_DIRS = [
    os.path.join(os.path.expanduser("~"), "Documents", "My Games", "SnowRunner", "base", "logs"),
    os.path.join(os.path.expanduser("~"), "Documents", "My Games", "SnowRunner", "base"),
    os.path.join(
        r"C:\Program Files (x86)\Steam\steamapps\common\SnowRunner",
        "Sources",
        "Bin",
        "logs",
    ),
]

LEVEL_ID_RE = re.compile(r"\b(level_(?:us|ru|dlc)_[0-9a-z_]+)\b", re.IGNORECASE)
MAP_CODE_RE = re.compile(r"\b(US|RU)_([0-9]{2})_([0-9]{2})(?:_[A-Z0-9_]+)?\b")

# level_id interno -> metadatos de sesion (Saber / MapRunner)
MAP_BY_LEVEL_ID: dict[str, dict[str, str]] = {
    "level_us_01_01": {
        "region": "Michigan",
        "map_name": "Black River",
        "location_default": "Black River partida libre",
    },
    "level_us_01_02": {
        "region": "Michigan",
        "map_name": "Smithville Dam",
        "location_default": "Smithville Dam partida libre",
    },
    "level_us_02_01": {
        "region": "Alaska",
        "map_name": "North Port",
        "location_default": "North Port partida libre",
    },
    "level_us_02_02": {
        "region": "Alaska",
        "map_name": "Mountain River",
        "location_default": "Mountain River partida libre",
    },
    "level_us_02_03": {
        "region": "Alaska",
        "map_name": "White Valley",
        "location_default": "White Valley partida libre",
    },
    "level_us_02_04": {
        "region": "Alaska",
        "map_name": "Pedro Bay",
        "location_default": "Pedro Bay partida libre",
    },
    "level_ru_02_01": {
        "region": "Taymyr",
        "map_name": "Drowned Lands",
        "location_default": "Drowned Lands partida libre",
    },
    "level_ru_02_02": {
        "region": "Taymyr",
        "map_name": "Quarry",
        "location_default": "Quarry partida libre",
    },
    "level_ru_02_03": {
        "region": "Taymyr",
        "map_name": "Amur",
        "location_default": "Amur partida libre",
    },
}

# Codigo MapRunner US_01_01 -> level_us_01_01
MAP_CODE_TO_LEVEL: dict[str, str] = {
    "US_01_01": "level_us_01_01",
    "US_01_02": "level_us_01_02",
    "US_02_01": "level_us_02_01",
    "US_02_02": "level_us_02_02",
    "US_02_03": "level_us_02_03",
    "US_02_04": "level_us_02_04",
    "RU_02_01": "level_ru_02_01",
    "RU_02_02": "level_ru_02_02",
    "RU_02_03": "level_ru_02_03",
}

LEVEL_SEARCH_ORDER = list(MAP_BY_LEVEL_ID.keys())

# Bbox mundo Havok (pos_x, pos_z) — calibrar con grabar_ce.py --probe
MAP_POSITION_BOUNDS: dict[str, dict[str, float]] = {
    # 600+ muestras CE Michigan Black River (garaje + rutas)
    "level_us_01_01": {"x_min": -700.0, "x_max": 480.0, "z_min": -750.0, "z_max": 350.0},
    # North Port Alaska — probes 2026-07 (garaje/puerto + rutas)
    "level_us_02_01": {"x_min": 100.0, "x_max": 1100.0, "z_min": -650.0, "z_max": 250.0},
}

ALASKA_TERRAIN_KINDS = frozenset({"snow", "ice"})

SKY_REGION_HINT: dict[str, str] = {
    "sky_us_01": "level_us_01_01",
    "sky_us_02": "level_us_02_01",
    "sky_ru_02": "level_ru_02_01",
}


class _MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.c_uint32),
        ("_partition", ctypes.c_uint16),
        ("_align", ctypes.c_uint16),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.c_uint32),
        ("Protect", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
    ]


_READABLE_PROTECT = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}
_MEM_COMMIT = 0x1000


@dataclass(frozen=True)
class MapDetectResult:
    level_id: str = ""
    region: str = ""
    map_name: str = ""
    location_note: str = ""
    source: str = ""  # manual | game_log | memory | unknown

    @property
    def ok(self) -> bool:
        return bool(self.map_name)


def _meta_for_level(level_id: str) -> dict[str, str]:
    key = level_id.lower()
    return MAP_BY_LEVEL_ID.get(key, {})


def _result_from_level(level_id: str, source: str) -> MapDetectResult:
    meta = _meta_for_level(level_id)
    if not meta:
        return MapDetectResult(level_id=level_id, source=source)
    return MapDetectResult(
        level_id=level_id.lower(),
        region=meta["region"],
        map_name=meta["map_name"],
        location_note=meta["location_default"],
        source=source,
    )


def _parse_level_from_text(text: str) -> str:
    """Ultima mencion de level_id o codigo US_XX_XX en un bloque de texto."""
    level_id = ""
    for m in LEVEL_ID_RE.finditer(text):
        level_id = m.group(1).lower()
    if level_id:
        return level_id
    code = ""
    for m in MAP_CODE_RE.finditer(text):
        code = f"{m.group(1).upper()}_{m.group(2)}_{m.group(3)}"
    if code:
        return MAP_CODE_TO_LEVEL.get(code, "")
    return ""


def _log_file_candidates() -> list[str]:
    names = ("LegacyLog.txt", "game.log", "Game.log", "log.txt")
    paths: list[str] = []
    seen: set[str] = set()
    for log_dir in SNOWRUNNER_LOG_DIRS:
        if not os.path.isdir(log_dir):
            continue
        for name in names:
            path = os.path.join(log_dir, name)
            if os.path.isfile(path) and path not in seen:
                seen.add(path)
                paths.append(path)
    return sorted(paths, key=lambda p: os.path.getmtime(p), reverse=True)


def _point_in_bounds(x: float, z: float, box: dict[str, float]) -> bool:
    return box["x_min"] <= x <= box["x_max"] and box["z_min"] <= z <= box["z_max"]


def _terrain_kind_counts(
    rows: list[dict[str, Any]] | None,
    sample: dict[str, Any] | None,
) -> dict[str, int]:
    from collections import Counter

    kinds: Counter[str] = Counter()
    if rows:
        for row in rows:
            k = (row.get("terrain_kind") or "").strip().lower()
            if k:
                kinds[k] += 1
    elif sample:
        k = (sample.get("terrain_kind") or "").strip().lower()
        if k:
            kinds[k] = 1
    return dict(kinds)


def detect_from_csv_map_columns(rows: list[dict[str, Any]]) -> MapDetectResult:
    """Mapa grabado en CSV al iniciar sesion (sky + pos con juego abierto)."""
    if not rows:
        return MapDetectResult(source="csv_map:skip")
    from collections import Counter

    names = [(r.get("map_name") or "").strip() for r in rows]
    names = [n for n in names if n]
    levels = [(r.get("level_id") or "").strip() for r in rows]
    levels = [lv for lv in levels if lv]
    if not names and not levels:
        return MapDetectResult(source="csv_map:miss")
    level_id = Counter(levels).most_common(1)[0][0] if levels else ""
    if level_id:
        res = _result_from_level(level_id, "csv_map")
        if res.ok:
            return res
    if names:
        name = Counter(names).most_common(1)[0][0]
        for lid, meta in MAP_BY_LEVEL_ID.items():
            if name.lower() == meta["map_name"].lower():
                return MapDetectResult(
                    level_id=lid,
                    region=meta["region"],
                    map_name=meta["map_name"],
                    location_note=meta["location_default"],
                    source="csv_map",
                )
        return MapDetectResult(
            map_name=name,
            location_note=f"{name} partida libre",
            source="csv_map",
        )
    return MapDetectResult(source="csv_map:miss")


def detect_from_position_smart(
    pos_x: float | None,
    pos_z: float | None,
    *,
    terrain_kinds: dict[str, int] | None = None,
    process_handle: int = 0,
) -> MapDetectResult:
    """Posicion + nieve/hielo + cielo para desambiguar Michigan/Alaska."""
    if pos_x is None or pos_z is None:
        return MapDetectResult(source="position:skip")
    try:
        x = float(pos_x)
        z = float(pos_z)
    except (TypeError, ValueError):
        return MapDetectResult(source="position:skip")

    kinds = terrain_kinds or {}
    snow_ice = kinds.get("snow", 0) + kinds.get("ice", 0)
    in_michigan = _point_in_bounds(x, z, MAP_POSITION_BOUNDS["level_us_01_01"])
    in_alaska = _point_in_bounds(x, z, MAP_POSITION_BOUNDS["level_us_02_01"])

    if snow_ice > 0:
        return MapDetectResult(
            level_id="level_us_02_01",
            region="Alaska",
            map_name="North Port",
            location_note=MAP_BY_LEVEL_ID["level_us_02_01"]["location_default"],
            source="terrain",
        )
    if in_alaska and not in_michigan:
        return _result_from_level("level_us_02_01", "position")
    if in_michigan and not in_alaska:
        return _result_from_level("level_us_01_01", "position")
    if in_michigan and in_alaska:
        sky = detect_from_sky_memory(process_handle)
        if sky.ok and sky.region == "Alaska":
            return _result_from_level("level_us_02_01", "sky+overlap")
        return _result_from_level("level_us_01_01", "position+overlap")
    return MapDetectResult(source="position:miss")


def detect_from_position(pos_x: float | None, pos_z: float | None) -> MapDetectResult:
    """Compat: solo bbox sin desambiguar regiones."""
    return detect_from_position_smart(pos_x, pos_z)


def _scan_process_for_needles(
    process_handle: int,
    needles: list[bytes],
    *,
    max_region_bytes: int = 16 * 1024 * 1024,
) -> dict[bytes, int]:
    if not process_handle:
        return {}
    kernel32 = ctypes.windll.kernel32
    counts = {n: 0 for n in needles}
    addr = 0
    mbi = _MEMORY_BASIC_INFORMATION()
    while addr < 0x7FFFFFFFFFFF:
        if (
            kernel32.VirtualQueryEx(
                process_handle,
                ctypes.c_void_p(addr),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi),
            )
            == 0
        ):
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if (
            mbi.State == _MEM_COMMIT
            and mbi.Protect in _READABLE_PROTECT
            and 0 < size <= max_region_bytes
        ):
            chunk = (ctypes.c_char * size)()
            read = ctypes.c_size_t()
            ok = kernel32.ReadProcessMemory(
                process_handle,
                ctypes.c_void_p(base),
                chunk,
                size,
                ctypes.byref(read),
            )
            if ok and read.value:
                blob = bytes(chunk[: read.value])
                for needle in needles:
                    c = blob.count(needle)
                    if c:
                        counts[needle] += c
        addr = base + max(size, 1)
    return counts


def detect_from_sky_memory(process_handle: int) -> MapDetectResult:
    """Region activa por preset de cielo (sky_us_01 Michigan, sky_us_02 Alaska)."""
    needles = [k.encode("ascii") for k in SKY_REGION_HINT]
    counts = _scan_process_for_needles(process_handle, needles)
    if not any(counts.values()):
        return MapDetectResult(source="sky:miss")
    best = max(counts, key=counts.get)
    level_id = SKY_REGION_HINT.get(best.decode("ascii", errors="replace"), "")
    if not level_id:
        return MapDetectResult(source="sky:miss")
    return _result_from_level(level_id, "sky")


def detect_from_game_logs(*, tail_lines: int = 400) -> MapDetectResult:
    """Lee el tail de logs SnowRunner y devuelve el ultimo mapa reconocido."""
    best = ""
    best_path = ""
    for path in _log_file_candidates():
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue
        chunk = "".join(lines[-tail_lines:])
        level_id = _parse_level_from_text(chunk)
        if level_id:
            best = level_id
            best_path = path
            break
    if best:
        res = _result_from_level(best, "game_log")
        res = MapDetectResult(
            level_id=res.level_id,
            region=res.region,
            map_name=res.map_name,
            location_note=res.location_note,
            source=f"game_log:{os.path.basename(best_path)}",
        )
        return res
    return MapDetectResult(source="game_log:missing")


def _position_sample(rows: list[dict[str, Any]] | None, sample: dict[str, Any] | None) -> tuple[float | None, float | None]:
    if sample:
        px = sample.get("pos_x")
        pz = sample.get("pos_z")
        if px is not None and pz is not None:
            return px, pz
    if rows:
        xs: list[float] = []
        zs: list[float] = []
        for row in rows:
            for key_x, key_z in (("pos_x", "pos_z"),):
                raw_x = row.get(key_x)
                raw_z = row.get(key_z)
                if raw_x in (None, "") or raw_z in (None, ""):
                    continue
                try:
                    xs.append(float(raw_x))
                    zs.append(float(raw_z))
                except (TypeError, ValueError):
                    continue
        if xs:
            xs.sort()
            zs.sort()
            mid = len(xs) // 2
            return xs[mid], zs[mid]
    return None, None


def resolve_map_context(
    *,
    map_arg: str = "",
    location_arg: str = "",
    process_handle: int | None = None,
    rows: list[dict[str, Any]] | None = None,
    sample: dict[str, Any] | None = None,
) -> MapDetectResult:
    """Resuelve mapa/ubicacion para grabacion o importacion."""
    pos_x, pos_z = _position_sample(rows, sample)
    kind_counts = _terrain_kind_counts(rows, sample)

    if map_arg.strip():
        manual = map_arg.strip()
        for level_id, meta in MAP_BY_LEVEL_ID.items():
            if manual.lower() in (
                meta["map_name"].lower(),
                meta["region"].lower(),
                level_id,
            ):
                loc = location_arg.strip() or meta["location_default"]
                return MapDetectResult(
                    level_id=level_id,
                    region=meta["region"],
                    map_name=meta["map_name"],
                    location_note=loc,
                    source="manual",
                )
        loc = location_arg.strip() or f"{manual} partida libre"
        return MapDetectResult(
            map_name=manual,
            location_note=loc,
            source="manual",
        )

    csv_hit = detect_from_csv_map_columns(rows or [])
    if csv_hit.ok:
        loc = location_arg.strip() or csv_hit.location_note
        return MapDetectResult(
            level_id=csv_hit.level_id,
            region=csv_hit.region,
            map_name=csv_hit.map_name,
            location_note=loc,
            source=csv_hit.source,
        )

    log_hit = detect_from_game_logs()
    if log_hit.ok:
        loc = location_arg.strip() or log_hit.location_note
        return MapDetectResult(
            level_id=log_hit.level_id,
            region=log_hit.region,
            map_name=log_hit.map_name,
            location_note=loc,
            source=log_hit.source,
        )

    pos_hit = detect_from_position_smart(
        pos_x,
        pos_z,
        terrain_kinds=kind_counts,
        process_handle=process_handle or 0,
    )
    if pos_hit.ok:
        loc = location_arg.strip() or pos_hit.location_note
        return MapDetectResult(
            level_id=pos_hit.level_id,
            region=pos_hit.region,
            map_name=pos_hit.map_name,
            location_note=loc,
            source=pos_hit.source,
        )

    sky_hit = detect_from_sky_memory(process_handle or 0)
    if sky_hit.ok:
        loc = location_arg.strip() or sky_hit.location_note
        return MapDetectResult(
            level_id=sky_hit.level_id,
            region=sky_hit.region,
            map_name=sky_hit.map_name,
            location_note=loc,
            source=sky_hit.source,
        )

    loc = location_arg.strip() or "CE Havok log"
    return MapDetectResult(location_note=loc, source="unknown")


def format_map_line(result: MapDetectResult, *, pos_x: float | None = None, pos_z: float | None = None) -> str:
    if not result.ok:
        pos = ""
        if pos_x is not None and pos_z is not None:
            pos = f" pos=({pos_x:.0f},{pos_z:.0f})"
        return f"mapa: ? (no detectado{pos} — usa --map \"North Port\" o --map \"Black River\")"
    extra = f" [{result.level_id}]" if result.level_id else ""
    src = f" ({result.source})" if result.source else ""
    return f"mapa: {result.map_name}, {result.region}{extra}{src}"


def _open_snowrunner_handle() -> int:
    ce_dir = os.path.join(ROOT, "cheat_engine")
    if ce_dir not in sys.path:
        sys.path.insert(0, ce_dir)
    import memoria_havok as mh  # noqa: WPS433

    opened = mh.open_snowrunner()
    if not opened:
        return 0
    h, _, _ = opened
    return h


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detectar mapa SnowRunner activo")
    parser.add_argument("--map", default="", help="Forzar nombre de mapa")
    parser.add_argument("--location", default="", help="Nota de ubicacion")
    parser.add_argument(
        "--memory",
        action="store_true",
        help="Incluir escaneo de memoria (requiere SnowRunner en mapa)",
    )
    args = parser.parse_args(argv)

    handle = _open_snowrunner_handle() if args.memory else 0
    try:
        result = resolve_map_context(
            map_arg=args.map,
            location_arg=args.location,
            process_handle=handle,
        )
    finally:
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)

    print(format_map_line(result))
    if result.location_note:
        print(f"ubicacion: {result.location_note}")
    return 0 if result.ok or args.map else 1


if __name__ == "__main__":
    raise SystemExit(main())
