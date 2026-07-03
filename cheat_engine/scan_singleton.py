"""Brute-force busca singleton TRUCK_CONTROL en .data del exe."""

from __future__ import annotations

import ctypes
import struct
import subprocess
import sys
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32
PROCESS = 0x0410


def rb(h, a: int, n: int) -> bytes | None:
    buf = (ctypes.c_char * n)()
    ok = kernel32.ReadProcessMemory(h, ctypes.c_void_p(a), buf, n, ctypes.byref(ctypes.c_size_t()))
    return bytes(buf) if ok else None


def ru(h, a: int) -> int | None:
    b = rb(h, a, 8)
    return struct.unpack("<Q", b)[0] if b else None


def rf(h, a: int) -> float | None:
    b = rb(h, a, 4)
    if not b:
        return None
    v = struct.unpack("<f", b)[0]
    if v != v or abs(v) > 1e6:
        return None
    return v


def rs(h, a: int) -> str:
    b = rb(h, a, 64)
    if not b:
        return ""
    e = b.find(b"\x00")
    return b[: e if e >= 0 else 64].decode("utf-8", errors="replace")


def valid_chain(h, base: int, off: int) -> dict | None:
    sing = ru(h, base + off)
    if not sing or sing < 0x10000:
        return None
    for veh_off, tag in ((8, "TC8"), (0x20, "DL20"), (0x10, "+10"), (0x18, "+18")):
        veh = ru(h, sing + veh_off)
        if not veh or veh < 0x10000:
            continue
        for rb_off in range(0x580, 0x640, 8):
            rb_ptr = ru(h, veh + rb_off)
            if not rb_ptr or rb_ptr < 0x10000:
                continue
            vx = rf(h, rb_ptr + 0x230)
            vz = rf(h, rb_ptr + 0x238)
            if vx is None or vz is None:
                continue
            spd = (vx * vx + vz * vz) ** 0.5 * 3.6
            if spd > 250:
                continue
            vid = ""
            for id_off in range(0xC80, 0xD40, 8):
                s = rs(h, veh + id_off)
                if s.startswith(("s_", "international_")) and len(s) < 48 and "/" not in s:
                    vid = s
                    break
                p = ru(h, veh + id_off)
                if p:
                    s2 = rs(h, p)
                    if s2.startswith(("s_", "international_")) and len(s2) < 48:
                        vid = s2
                        break
            if not vid:
                continue
            if ".xml" in vid or "\\" in vid or len(vid) > 40:
                continue
            return {
                "off": off,
                "tag": tag,
                "veh_off": veh_off,
                "rb_off": rb_off,
                "vid": vid,
                "kmh": round(spd, 2),
                "vx": round(vx, 3),
                "sing": sing,
                "veh": veh,
            }
    return None


def main() -> int:
    out = subprocess.check_output(
        ["tasklist", "/FI", "IMAGENAME eq SnowRunner.exe", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    pid = int(out.split('","')[1].strip('"'))
    h = kernel32.OpenProcess(PROCESS, False, pid)
    if not h:
        print("no access")
        return 1
    try:
        psapi = ctypes.windll.psapi
        import ctypes as ct

        class MODULEINFO(ct.Structure):
            _fields_ = [
                ("lpBaseOfDll", ct.c_void_p),
                ("SizeOfImage", wintypes.DWORD),
                ("EntryPoint", ct.c_void_p),
            ]

        hmods = (ct.c_void_p * 8)()
        cb = wintypes.DWORD()
        psapi.EnumProcessModulesEx(h, ct.byref(hmods), ct.sizeof(hmods), ct.byref(cb), 3)
        base = ct.cast(hmods[0], ct.c_void_p).value or 0
        info = MODULEINFO()
        psapi.GetModuleInformation(h, ct.c_void_p(base), ct.byref(info), ct.sizeof(info))
        img = info.SizeOfImage
        print(f"base={base:#x} size={img:#x}")

        hits: list[dict] = []
        # scan .data-ish region (typical 0x2800000 - end)
        start = 0x2700000
        end = min(img, 0x3200000)
        chunk_sz = 0x200000
        for cs in range(start, end, chunk_sz):
            chunk = rb(h, base + cs, min(chunk_sz, end - cs))
            if not chunk:
                continue
            for i in range(0, len(chunk) - 8, 8):
                off = cs + i
                r = valid_chain(h, base, off)
                if r:
                    hits.append(r)

        hits.sort(key=lambda x: -x["kmh"])
        print(f"hits: {len(hits)}")
        for r in hits[:15]:
            print(
                f"  TRUCK_OFF=0x{r['off']:X} {r['tag']} veh+{r['veh_off']:X} "
                f"rb+{r['rb_off']:X} {r['vid']} {r['kmh']} km/h"
            )
        if not hits:
            print(
                "Ninguna cadena valida — probablemente menu/garaje o offsets internos cambiaron mucho"
            )
    finally:
        kernel32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
