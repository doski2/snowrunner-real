"""Escanea offsets internos del vehiculo (rb, id, fuel) en SnowRunner."""

from __future__ import annotations

import ctypes
import struct
import subprocess
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32
TRUCK_CONTROL_OFF = 0x2A8EDD8


def find_pid() -> int | None:
    out = subprocess.check_output(
        ["tasklist", "/FI", "IMAGENAME eq SnowRunner.exe", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    for line in out.splitlines():
        if "SnowRunner" in line:
            return int(line.split('","')[1].strip('"'))
    return None


def rq(h, a: int) -> int:
    b = (ctypes.c_char * 8)()
    kernel32.ReadProcessMemory(h, ctypes.c_void_p(a), b, 8, ctypes.byref(ctypes.c_size_t()))
    return struct.unpack("<Q", b)[0]


def rf(h, a: int) -> float | None:
    b = (ctypes.c_char * 4)()
    if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(a), b, 4, ctypes.byref(ctypes.c_size_t())):
        return None
    return struct.unpack("<f", b)[0]


def rs(h, a: int, n: int = 64) -> str:
    b = (ctypes.c_char * n)()
    kernel32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(ctypes.c_size_t()))
    end = bytes(b).find(b"\x00")
    raw = bytes(b)[: end if end >= 0 else n]
    return raw.decode("utf-8", errors="replace")


def main() -> int:
    pid = find_pid()
    if not pid:
        print("SnowRunner no corriendo")
        return 1
    h = kernel32.OpenProcess(0x0410, False, pid)
    if not h:
        print("sin acceso al proceso")
        return 1
    try:
        psapi = ctypes.windll.psapi
        hmods = (ctypes.c_void_p * 1024)()
        cb = wintypes.DWORD()
        psapi.EnumProcessModulesEx(
            h, ctypes.byref(hmods), ctypes.sizeof(hmods), ctypes.byref(cb), 3
        )
        base = ctypes.cast(hmods[0], ctypes.c_void_p).value or 0

        sing = rq(h, base + TRUCK_CONTROL_OFF)
        veh = rq(h, sing + 8) if sing else 0
        print(f"base={base:#x} sing={sing:#x} veh={veh:#x}")

        print("\n-- rb candidates (veh+off -> hkpRigidBody, vel +230/+238) --")
        hits = []
        for off in range(0x500, 0x700, 8):
            p = rq(h, veh + off)
            if not (0x10000 < p < 0x7FFFFFFFFFFF):
                continue
            vx, vz = rf(h, p + 0x230), rf(h, p + 0x238)
            if vx is None or vz is None:
                continue
            hits.append((off, p, vx, vz, (vx * vx + vz * vz) ** 0.5 * 3.6))
        hits.sort(key=lambda x: -(abs(x[2]) + abs(x[3])))
        for off, p, vx, vz, kmh in hits[:10]:
            print(f"  +{off:03X} rb={p:#x} vx={vx:.4f} vz={vz:.4f} kmh={kmh:.2f}")

        print("\n-- id candidates (s_*) --")
        for off in range(0xC00, 0xD80, 8):
            p = rq(h, veh + off)
            if 0x10000 < p < 0x7FFFFFFFFFFF:
                s = rs(h, p)
                if s.startswith("s_"):
                    print(f"  ptr +{off:03X} -> {s}")
            s2 = rs(h, veh + off)
            if s2.startswith("s_"):
                print(f"  inline +{off:03X} -> {s2}")

        print("\n-- fuel candidates (addon+568/570) --")
        for off in range(0x40, 0x90, 8):
            addon = rq(h, veh + off)
            if not (0x10000 < addon < 0x7FFFFFFFFFFF):
                continue
            c, m = rf(h, addon + 0x568), rf(h, addon + 0x570)
            if c is not None and m is not None and 0 < m < 5000 and 0 <= c <= m:
                print(f"  addon +{off:02X} fuel {c:.1f}/{m:.1f} = {c / m * 100:.0f}%")
    finally:
        kernel32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
