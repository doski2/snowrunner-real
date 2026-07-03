"""Lee cadena TRUCK_CONTROL de SnowRunner sin Cheat Engine (diagnostico)."""

from __future__ import annotations

import ctypes
import struct
import sys
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

TRUCK_CONTROL_OFF = 0x2A8EDD8  # RTTI TRUCK_CONTROL — build 2026-06-25
DRIVE_LOGIC_OFF = 0x2A8EDC8
SPAWN_ARRAY_OFF = 0x2E6FC40
OFF_VEH_TRUCK = 0x8
OFF_VEH_DRIVE = 0x20
OFF_SPAWN_VEH0 = 0x40
OFF_SPAWN_VEH_STEP = 0x8
OFF_RB = 0x5D0
OFF_VX = 0x230
OFF_VZ = 0x238
OFF_ID = 0xD10
OFF_ADDON = 0x48
OFF_FUEL = 0x568


class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", ctypes.c_void_p),
        ("SizeOfImage", wintypes.DWORD),
        ("EntryPoint", ctypes.c_void_p),
    ]


def find_pid(name: str) -> int | None:
    import subprocess

    out = subprocess.check_output(
        ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
        text=True,
        errors="replace",
    )
    for line in out.splitlines():
        if name.lower() in line.lower():
            parts = [p.strip('"') for p in line.split('","')]
            if parts:
                try:
                    return int(parts[1])
                except ValueError:
                    pass
    return None


def get_module_base(pid: int, module: str = "SnowRunner.exe") -> int | None:
    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        return None
    try:
        hmods = (ctypes.c_void_p * 1024)()
        cb = wintypes.DWORD()
        if not psapi.EnumProcessModulesEx(
            h, ctypes.byref(hmods), ctypes.sizeof(hmods), ctypes.byref(cb), 0x03
        ):
            return None
        count = cb.value // ctypes.sizeof(ctypes.c_void_p)
        buf = ctypes.create_unicode_buffer(260)
        for i in range(count):
            base_val = ctypes.cast(hmods[i], ctypes.c_void_p).value or 0
            if not base_val:
                continue
            psapi.GetModuleBaseNameW(h, ctypes.c_void_p(base_val), buf, 260)
            if buf.value.lower() == module.lower():
                return base_val
    finally:
        kernel32.CloseHandle(h)
    return None


def read_bytes(h, addr: int, size: int) -> bytes | None:
    buf = (ctypes.c_char * size)()
    read = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(read))
    if not ok or read.value != size:
        return None
    return bytes(buf)


def read_u64(h, addr: int) -> int | None:
    b = read_bytes(h, addr, 8)
    return struct.unpack("<Q", b)[0] if b else None


def read_f32(h, addr: int) -> float | None:
    b = read_bytes(h, addr, 4)
    return struct.unpack("<f", b)[0] if b else None


def read_cstring(h, addr: int, max_len: int = 64) -> str:
    b = read_bytes(h, addr, max_len)
    if not b:
        return ""
    end = b.find(b"\x00")
    if end >= 0:
        b = b[:end]
    return b.decode("utf-8", errors="replace")


def read_vehicle_id(h: int, veh: int) -> str:
    def ok(s: str) -> bool:
        return bool(s) and s.startswith("s_") and len(s) < 64

    id_ptr = read_u64(h, veh + OFF_ID)
    if id_ptr and 0x10000 < id_ptr < 0x7FFFFFFFFFFF:
        via_ptr = read_cstring(h, id_ptr)
        if ok(via_ptr):
            return via_ptr
    inline = read_cstring(h, veh + OFF_ID)
    if ok(inline):
        return inline
    for off in (0xD50, 0xCE8, 0xCF8):
        s = read_cstring(h, veh + off)
        if ok(s):
            return s
    return ""


def validate_vehicle(h, veh: int) -> dict | None:
    if not veh or veh < 0x10000:
        return None
    rb = read_u64(h, veh + OFF_RB)
    if not rb or rb < 0x10000:
        return None
    vx = read_f32(h, rb + OFF_VX)
    vz = read_f32(h, rb + OFF_VZ)
    if vx is None or vz is None:
        return None
    addon = read_u64(h, veh + OFF_ADDON)
    fuel = read_f32(h, addon + OFF_FUEL) if addon else None
    return {
        "veh": hex(veh),
        "rb": hex(rb),
        "vx": vx,
        "vz": vz,
        "km_h": round((vx * vx + vz * vz) ** 0.5 * 3.6, 2),
        "id": read_vehicle_id(h, veh),
        "fuel_l": round(fuel, 1) if fuel is not None else None,
    }


def probe_spawn_array(h, base: int) -> list[dict]:
    slot = base + SPAWN_ARRAY_OFF
    root = read_u64(h, slot)
    out = []
    if not root:
        out.append({"tag": "SPAWN_ARRAY", "slot": hex(slot), "root": "0"})
        return out
    for i in range(6):
        off = OFF_SPAWN_VEH0 + i * OFF_SPAWN_VEH_STEP
        veh = read_u64(h, root + off)
        entry = {"tag": f"SPAWN[{i}]", "off": hex(off), "veh_ptr": hex(veh) if veh else "0"}
        if veh:
            v = validate_vehicle(h, veh)
            if v:
                entry.update(v)
        out.append(entry)
    return out


def scan_vehicle_ids(h, needles: tuple[str, ...]) -> list[dict]:
    """Busca strings de ID de vehiculo en regiones legibles."""
    hits: list[dict] = []

    class MBI(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    MEM_COMMIT = 0x1000
    readable = {0x02, 0x04, 0x06, 0x20, 0x40, 0x80}
    addr = 0
    mbi = MBI()
    while addr < 0x7FFFFFFFFFFF:
        if (
            kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
            == 0
        ):
            break
        base_addr = ctypes.cast(mbi.BaseAddress, ctypes.c_void_p).value or 0
        size = mbi.RegionSize
        if (
            mbi.State == MEM_COMMIT
            and (mbi.Protect & 0xFF) in readable
            and size <= 64 * 1024 * 1024
        ):
            chunk = read_bytes(h, base_addr, min(size, 4 * 1024 * 1024))
            if chunk:
                for needle in needles:
                    nb = needle.encode("ascii")
                    start = 0
                    while True:
                        idx = chunk.find(nb, start)
                        if idx < 0:
                            break
                        abs_addr = base_addr + idx
                        hits.append({"needle": needle, "addr": hex(abs_addr)})
                        start = idx + len(nb)
                        if len(hits) >= 20:
                            return hits
        addr = base_addr + size
    return hits


def scan_qword_value(
    h, value: int, near: int | None = None, window: int = 32 * 1024 * 1024, max_hits: int = 32
) -> list[int]:
    class MBI(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    MEM_COMMIT = 0x1000
    readable = {0x02, 0x04, 0x06, 0x20, 0x40, 0x80}
    needle = struct.pack("<Q", value)
    out: list[int] = []
    addr = 0
    mbi = MBI()
    while addr < 0x7FFFFFFFFFFF and len(out) < max_hits:
        if (
            kernel32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
            == 0
        ):
            break
        base_addr = ctypes.cast(mbi.BaseAddress, ctypes.c_void_p).value or 0
        size = mbi.RegionSize
        if near is not None and (base_addr + size < near - window or base_addr > near + window):
            addr = base_addr + size
            continue
        if (
            mbi.State == MEM_COMMIT
            and (mbi.Protect & 0xFF) in readable
            and size <= 64 * 1024 * 1024
        ):
            chunk = read_bytes(h, base_addr, min(size, 4 * 1024 * 1024))
            if chunk:
                start = 0
                while len(out) < max_hits:
                    idx = chunk.find(needle, start)
                    if idx < 0:
                        break
                    out.append(base_addr + idx)
                    start = idx + 8
        addr = base_addr + size
    return out


def find_veh_from_id_ptr(h, id_str_addr: int) -> dict | None:
    """Resuelve vehiculo desde direccion del string ID (puntero o inline en +CE8)."""
    inline = validate_vehicle(h, id_str_addr - OFF_ID)
    if inline and inline.get("id"):
        inline["via"] = "inline+CE8"
        return inline

    hits = scan_qword_value(h, id_str_addr, near=id_str_addr)
    for ref_addr in hits:
        veh = ref_addr - OFF_ID
        v = validate_vehicle(h, veh)
        if v and v.get("id"):
            v["via"] = hex(ref_addr)
            return v

    for delta in range(0, 0x3000, 8):
        v = validate_vehicle(h, id_str_addr - delta)
        if v and v.get("id") and "s_" in v["id"]:
            v["via"] = f"brute-{hex(delta)}"
            return v
    return None


def probe_chain(h, base: int, off: int, veh_off: int, tag: str) -> dict:
    slot = base + off
    singleton = read_u64(h, slot)
    result = {"tag": tag, "slot": hex(slot), "singleton": hex(singleton) if singleton else "0"}
    if not singleton:
        return result
    veh = read_u64(h, singleton + veh_off)
    result["veh"] = hex(veh) if veh else "0"
    if not veh:
        return result
    v = validate_vehicle(h, veh)
    if v:
        result.update(v)
    return result


def main() -> int:
    pid = find_pid("SnowRunner.exe")
    if not pid:
        print("SnowRunner.exe no esta corriendo")
        return 1

    h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print("No puedo abrir proceso (ejecuta terminal como admin?)")
        return 1

    try:
        base = get_module_base(pid)
        if not base:
            print(f"PID {pid}: modulo SnowRunner.exe no encontrado")
            return 1

        print(f"PID={pid} base=0x{base:X}")
        for off, veh_off, tag in [
            (TRUCK_CONTROL_OFF, OFF_VEH_TRUCK, "TRUCK_CONTROL"),
            (DRIVE_LOGIC_OFF, OFF_VEH_DRIVE, "DRIVE_LOGIC"),
        ]:
            r = probe_chain(h, base, off, veh_off, tag)
            print(f"\n=== {tag} ===")
            for k, v in r.items():
                print(f"  {k}: {v}")

        print(f"\n=== SPAWN_ARRAY @ {hex(SPAWN_ARRAY_OFF)} ===")
        for entry in probe_spawn_array(h, base):
            print(" ", entry)

        print("\n=== SCAN IDs vehiculo ===")
        needles = (
            "s_chevrolet_ck1500",
            "s_gmc_9500",
            "international_fleetstar_f2070a",
            "s_tayga",
            "s_khan",
        )
        hits = scan_vehicle_ids(h, needles)
        if hits:
            for hit in hits[:10]:
                print(" ", hit)
        else:
            print("  (ningun ID encontrado — ¿estas en mapa conduciendo?)")

        print("\n=== REVERSE veh desde ID string ===")
        rev = None
        for hit in hits:
            if hit["needle"] == "s_chevrolet_ck1500":
                addr = int(hit["addr"], 16)
                rev = find_veh_from_id_ptr(h, addr)
                if rev:
                    print(" ", rev)
                    break
        if not rev:
            print("  (no se pudo resolver vehiculo desde puntero ID)")

        status_path = __import__("os").path.expanduser(
            "~/Documents/My Games/SnowRunner/base/telemetria_ce_status.txt"
        )
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            f.write(f"probe_memoria.py PID={pid} base=0x{base:X}\n")
            for off, veh_off, tag in [
                (TRUCK_CONTROL_OFF, OFF_VEH_TRUCK, "TRUCK_CONTROL"),
                (DRIVE_LOGIC_OFF, OFF_VEH_DRIVE, "DRIVE_LOGIC"),
            ]:
                r = probe_chain(h, base, off, veh_off, tag)
                f.write(
                    f"{tag}: singleton={r.get('singleton')} veh={r.get('veh', '?')} km_h={r.get('km_h', '?')}\n"
                )
            spawn = probe_spawn_array(h, base)
            f.write(f"SPAWN_ARRAY root={spawn[0].get('root', spawn[0].get('veh_ptr', '?'))}\n")
            f.write(f"ID_scan_hits={len(hits)}\n")
    finally:
        kernel32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
