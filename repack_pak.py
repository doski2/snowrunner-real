"""
Reempaqueta initial.pak con parches de vehiculos realistas (CK1500, GMC MH9500).

Solo sustituye entradas concretas del ZIP; copia el resto byte a byte.
Preserva tail Saber (1768 bytes) y rutas con backslash.
"""

from __future__ import annotations

import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from camiones.registry import default_vehicle_ids, merge_patches

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# --- Rutas -----------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))
STEAM_PAK_DIR = os.path.join(
    r"C:\Program Files (x86)\Steam\steamapps\common\SnowRunner",
    "preload",
    "paks",
    "client",
)
PAK_OUT = os.path.join(ROOT, "initial.pak")
BACKUP = os.path.join(ROOT, "initial.pak.bak")
SEVEN_ZIP = r"C:\Program Files\7-Zip\7z.exe"

# --- Parches activos -------------------------------------------------------

_ACTIVE_VEHICLE_IDS: list[str] = default_vehicle_ids()


def set_active_vehicles(vehicle_ids: list[str]) -> None:
    global PATCHES
    _ACTIVE_VEHICLE_IDS[:] = vehicle_ids
    PATCHES = merge_patches(vehicle_ids)


PATCHES: dict[str, list[tuple[str, str]]] = merge_patches(_ACTIVE_VEHICLE_IDS)

# --- Constantes ZIP --------------------------------------------------------

SIG_LOCAL = 0x04034B50
LOCAL_HDR = 30
CD_HDR = 46
EOCD_SIZE = 22


@dataclass(frozen=True)
class EntryStats:
    crc: int
    comp_size: int
    uncomp_size: int


# --- Utilidades ZIP --------------------------------------------------------


def split_zip_tail(raw: bytes) -> tuple[bytes, bytes]:
    idx = raw.rfind(b"PK\x05\x06")
    if idx < 0:
        raise RuntimeError("EOCD no encontrado en .pak")
    end = idx + EOCD_SIZE
    return raw[:end], raw[end:]


def pak_path(name: str) -> bytes:
    """SnowRunner guarda rutas con backslash en cabeceras ZIP."""
    return name.replace("/", "\\").encode("utf-8")


def _dos_datetime(dt: tuple[int, int, int, int, int, int]) -> tuple[int, int]:
    dos_time = (dt[3] << 11) | (dt[4] << 5) | (dt[5] // 2)
    dos_date = ((dt[0] - 1980) << 9) | (dt[1] << 5) | dt[2]
    return dos_time, dos_date


def _local_extra_offset(info: zipfile.ZipInfo) -> int:
    return LOCAL_HDR + len(pak_path(info.filename)) + len(info.extra)


def _local_total_size(info: zipfile.ZipInfo, comp_size: int) -> int:
    return _local_extra_offset(info) + comp_size


def _deflate_raw(data: bytes) -> bytes:
    obj = zlib.compressobj(9, zlib.DEFLATED, -15)
    return obj.compress(data) + obj.flush()


def _build_local_record(info: zipfile.ZipInfo, data: bytes) -> tuple[bytes, EntryStats]:
    name_b = pak_path(info.filename)
    extra = info.extra
    if info.compress_type == zipfile.ZIP_STORED:
        payload = data
    else:
        payload = _deflate_raw(data)
    stats = EntryStats(zlib.crc32(data) & 0xFFFFFFFF, len(payload), len(data))
    dos_time, dos_date = _dos_datetime(info.date_time)
    header = struct.pack(
        "<IHHHHHIIIHH",
        SIG_LOCAL,
        20,
        info.flag_bits,
        info.compress_type,
        dos_time,
        dos_date,
        stats.crc,
        stats.comp_size,
        stats.uncomp_size,
        len(name_b),
        len(extra),
    )
    return header + name_b + extra + payload, stats


def _parse_cd_records(raw_zip: bytes) -> list[bytes]:
    eocd_pos = raw_zip.rfind(b"PK\x05\x06")
    records: list[bytes] = []
    pos = 0
    while True:
        p = raw_zip.find(b"PK\x01\x02", pos)
        if p < 0 or p >= eocd_pos:
            break
        name_len, extra_len, comment_len = struct.unpack_from("<HHH", raw_zip, p + 28)
        records.append(raw_zip[p : p + CD_HDR + name_len + extra_len + comment_len])
        pos = p + 1
    return records


def _patch_cd_record(record: bytes, offset: int, stats: EntryStats) -> bytes:
    buf = bytearray(record)
    struct.pack_into("<I", buf, 16, stats.crc)
    struct.pack_into("<I", buf, 20, stats.comp_size)
    struct.pack_into("<I", buf, 24, stats.uncomp_size)
    struct.pack_into("<I", buf, 42, offset)
    return bytes(buf)


def rebuild_zip(raw_zip: bytes, replacements: dict[str, bytes]) -> bytes:
    cd_templates = _parse_cd_records(raw_zip)
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zin:
        infos = zin.infolist()
        if len(infos) != len(cd_templates):
            raise RuntimeError("CD / ZipInfo count mismatch")

        parts: list[bytes] = []
        cd_out: list[bytes] = []
        offset = 0

        for info, cd_tpl in zip(infos, cd_templates):
            if info.filename in replacements:
                blob, stats = _build_local_record(info, replacements[info.filename])
            else:
                start = info.header_offset
                blob = raw_zip[start : start + _local_total_size(info, info.compress_size)]
                stats = EntryStats(info.CRC, info.compress_size, info.file_size)

            parts.append(blob)
            cd_out.append(_patch_cd_record(cd_tpl, offset, stats))
            offset += len(blob)

        body = b"".join(parts)
        cd = b"".join(cd_out)
        eocd_pos = raw_zip.rfind(b"PK\x05\x06")
        eocd = bytearray(raw_zip[eocd_pos : eocd_pos + EOCD_SIZE])
        struct.pack_into("<I", eocd, 12, len(cd))
        struct.pack_into("<I", eocd, 16, len(body))
        return body + cd + bytes(eocd)


# --- Parches XML -----------------------------------------------------------


def patch_bytes(data: bytes, rules: Iterable[tuple[str, str]]) -> bytes:
    text = data.decode("utf-8")
    for old, new in rules:
        if old in text:
            text = text.replace(old, new, 1)
        elif new not in text:
            raise ValueError(f"Patron no encontrado: {old!r}")
    return text.encode("utf-8")


def load_replacements(zip_bytes: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        return {arc: patch_bytes(zf.read(arc), rules) for arc, rules in PATCHES.items()}


def build_mod_pak(factory_raw: bytes) -> tuple[bytes, dict[str, bytes]]:
    zip_bytes, tail = split_zip_tail(factory_raw)
    replacements = load_replacements(zip_bytes)
    return rebuild_zip(zip_bytes, replacements) + tail, replacements


# --- Verificacion ----------------------------------------------------------


def _check_cd_unchanged(orig_zip: bytes, new_zip: bytes) -> None:
    for old, new in zip(_parse_cd_records(orig_zip), _parse_cd_records(new_zip)):
        if old[:16] != new[:16] or old[28:42] != new[28:42] or old[46:] != new[46:]:
            raise RuntimeError("Metadatos CD alterados en entrada no parcheada")


def _run_7zip_test(pak_bytes: bytes) -> None:
    if not os.path.isfile(SEVEN_ZIP):
        return
    with tempfile.NamedTemporaryFile(suffix=".pak", delete=False) as tmp:
        tmp.write(pak_bytes)
        path = tmp.name
    try:
        r = subprocess.run([SEVEN_ZIP, "t", path], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"7z test fallo:\n{r.stdout}\n{r.stderr}")
    finally:
        os.unlink(path)


def verify(factory_raw: bytes, mod_raw: bytes, replacements: dict[str, bytes]) -> None:
    orig_zip, orig_tail = split_zip_tail(factory_raw)
    new_zip, new_tail = split_zip_tail(mod_raw)

    if new_tail != orig_tail:
        raise RuntimeError(f"Tail distinto: {len(new_tail)} vs {len(orig_tail)} bytes")

    with zipfile.ZipFile(io.BytesIO(orig_zip)) as zo, zipfile.ZipFile(io.BytesIO(new_zip)) as zm:
        names = zo.namelist()
        if names != zm.namelist():
            raise RuntimeError("Lista de entradas ZIP distinta")
        changed = [n for n in names if zo.getinfo(n).CRC != zm.getinfo(n).CRC]
        if set(changed) != set(replacements):
            raise RuntimeError(f"CRC inesperados: {changed}")

        for arc, rules in PATCHES.items():
            text = zm.read(arc).decode("utf-8")
            if not text:
                raise RuntimeError(f"Entrada vacia: {arc}")
            for _, new in rules:
                if new not in text:
                    raise RuntimeError(f"Falta {new!r} en {arc}")

    _check_cd_unchanged(orig_zip, new_zip)
    _run_7zip_test(mod_raw)

    print(f"Entradas: {len(names)} (orden identico)")
    print(f"Modificados: {len(changed)}")
    for name in changed:
        print(f"  {name}")
    print(f"ZIP: {len(orig_zip)} -> {len(new_zip)} ({len(new_zip) - len(orig_zip):+d} bytes)")
    print(f"Tail: {len(new_tail)} bytes preservado")
    if os.path.isfile(SEVEN_ZIP):
        print("7-Zip test: OK")


# --- CLI -------------------------------------------------------------------


def find_factory_pak() -> str | None:
    for name in ("initial.pak", "2initial.pak"):
        path = os.path.join(STEAM_PAK_DIR, name)
        if os.path.isfile(path):
            return path
    return None


def steam_pak_is_newer_than_backup() -> tuple[bool, str]:
    """True si Steam tiene un initial.pak mas reciente/grande que el backup local."""
    steam = find_factory_pak()
    if not steam or not os.path.isfile(BACKUP):
        return False, ""
    ss = os.stat(steam)
    bs = os.stat(BACKUP)
    if ss.st_size != bs.st_size or ss.st_mtime > bs.st_mtime + 1:
        return True, (
            f"Steam initial.pak ({ss.st_size} B, {ss.st_mtime:.0f}) "
            f"!= backup ({bs.st_size} B, {bs.st_mtime:.0f})"
        )
    return False, ""


def refresh_backup_from_steam() -> str:
    steam = find_factory_pak()
    if not steam:
        raise FileNotFoundError(f"No se encontro initial.pak en {STEAM_PAK_DIR}")
    if os.path.isfile(BACKUP):
        stamp = datetime.fromtimestamp(os.stat(BACKUP).st_mtime).strftime("%Y%m%d")
        archived = BACKUP + f".pre_update_{stamp}"
        if not os.path.isfile(archived):
            shutil.copy2(BACKUP, archived)
            print(f"Backup anterior archivado: {archived}")
    shutil.copy2(steam, BACKUP)
    print(f"Backup actualizado desde Steam: {steam}")
    return BACKUP


def load_factory_bytes(*, refresh: bool = False) -> bytes:
    if refresh:
        refresh_backup_from_steam()
    elif steam_pak_is_newer_than_backup()[0]:
        print(
            "AVISO: initial.pak de Steam es distinto al backup local.\n"
            "  Tras una actualizacion del juego ejecuta: python apply_mod.py --refresh-backup"
        )
    if os.path.isfile(BACKUP):
        with open(BACKUP, "rb") as f:
            return f.read()
    steam = find_factory_pak()
    if not steam:
        raise FileNotFoundError(f"Sin backup ({BACKUP}) ni Steam en {STEAM_PAK_DIR}")
    shutil.copy2(steam, BACKUP)
    with open(BACKUP, "rb") as f:
        return f.read()


def write_pak(data: bytes) -> str:
    try:
        with open(PAK_OUT, "wb") as f:
            f.write(data)
        return PAK_OUT
    except PermissionError:
        fallback = os.path.join(ROOT, "initial_fixed.pak")
        with open(fallback, "wb") as f:
            f.write(data)
        print(f"AVISO: {PAK_OUT} en uso -> {fallback}")
        return fallback


def print_patches() -> None:
    print(f"\n=== Cambios mod ({', '.join(_ACTIVE_VEHICLE_IDS)}) ===")
    for arc, rules in PATCHES.items():
        print(f"\n{arc.rsplit('/', 1)[-1]}:")
        for old, new in rules:
            print(f"  {old} -> {new}")


def apply_mod(*, refresh: bool = False) -> str:
    """Lee fabrica, parchea XML, reempaqueta y verifica."""
    factory = load_factory_bytes(refresh=refresh)
    mod_raw, replacements = build_mod_pak(factory)
    out_path = write_pak(mod_raw)
    verify(factory, mod_raw, replacements)
    print_patches()
    print(f"\nBackup fabrica: {BACKUP}")
    print(f"Salida: {out_path}")
    return out_path


def diagnose_patches(pak_path: str | None = None) -> int:
    """Comprueba que los patrones de parche existen en un initial.pak."""
    path = pak_path or find_factory_pak() or BACKUP
    if not path or not os.path.isfile(path):
        print(f"No encontrado: {path}")
        return 1
    with open(path, "rb") as f:
        zip_bytes, tail = split_zip_tail(f.read())
    print(f"{path} | zip={len(zip_bytes)} tail={len(tail)}")
    failures = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = set(zf.namelist())
        for arc, rules in PATCHES.items():
            short = arc.rsplit("/", 1)[-1]
            if arc not in names:
                print(f"  MISSING {arc}")
                failures += 1
                continue
            text = zf.read(arc).decode("utf-8")
            for i, (old, new) in enumerate(rules, 1):
                if old in text or new in text:
                    print(f"  OK   [{short}] {i}")
                else:
                    print(f"  FAIL [{short}] {i}: {old[:60]!r}")
                    failures += 1
    return 1 if failures else 0


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Reempaquetar initial.pak con mod realista")
    parser.add_argument(
        "--refresh-backup",
        action="store_true",
        help="Copiar initial.pak de Steam al backup antes de parchear",
    )
    parser.add_argument(
        "--diag", metavar="PAK", nargs="?", const="", help="Diagnosticar patrones en Steam/backup"
    )
    args = parser.parse_args()

    if args.diag is not None:
        path = args.diag or find_factory_pak() or BACKUP
        sys.exit(diagnose_patches(path))

    apply_mod(refresh=args.refresh_backup)
    print("\nOK")


if __name__ == "__main__":
    main()
