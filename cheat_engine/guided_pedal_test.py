"""Test guiado: gas suelto -> acelerar a fondo (coordina con chat)."""

from __future__ import annotations

import sys
import time

import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memoria_havok as mh  # noqa: E402
from calibrar_drive import _vehicle_ptr_from_sample, read_live_field  # noqa: E402
from pedal_hunt import (  # noqa: E402
    capture_pedal_map,
    diff_pedal_maps,
    rank_pedal_sweep,
    record_pedal_sweep,
)


def _specs() -> tuple[dict, dict]:
    ref = mh.load_offsets_reference()
    cands = mh._normalized_drive_candidates((ref.get("drive_runtime") or {}).get("candidates") or {})
    inp = cands.get("throttle_input") or {}
    mot = cands.get("throttle_motor_f32") or dict(mh.DEFAULT_THROTTLE_MOTOR_SPEC)
    return dict(inp), dict(mot)


def main() -> int:
    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo.")
        return 1

    h, base, pid = opened
    inp, mot = _specs()

    try:
        sample = mh.read_active_sample(h, base)
        if not sample:
            print("Sin vehiculo.")
            return 1
        veh_ptr = _vehicle_ptr_from_sample(sample) or 0
        veh_id = sample.get("vehicle_id") or "?"

        def read_pair() -> tuple[float | None, float | None]:
            s = mh.read_active_sample(h, base)
            vp = _vehicle_ptr_from_sample(s) or veh_ptr
            mh.enrich_drive_fields(h, base, s, t_s=0)
            vi = read_live_field(h, base, inp, veh_ptr=vp) if inp else None
            vm = read_live_field(h, base, mot, veh_ptr=vp) if mot else None
            return vi, vm

        print("=== TEST GUIADO PEDAL ===")
        print(f"PID={pid}  veh={veh_id}")
        print(f"IN  {inp.get('base')}{inp.get('offset')} {inp.get('kind')}")
        print(f"MOT {mot.get('base')}{mot.get('offset')} {mot.get('kind')}")

        if inp.get("base", "").startswith("tc+"):
            ptr_in = mh.resolve_field_base_ptr(h, base, inp["base"], veh_ptr=veh_ptr)
            if not ptr_in:
                print(
                    f"\nERROR: {inp.get('base')} no existe en este camion ({veh_id}).\n"
                    "  El offset IN esta calibrado para Bandit (KRS 58).\n"
                    "  Entra al mapa con el BANDIT y vuelve a ejecutar este test.\n"
                )
                return 2

        print()
        for i in range(12, 0, -1):
            print(
                f"Preparate: Alt+Tab al juego, MOTOR ON, FRENO. Gas SUELTO. Empieza en {i}...",
                flush=True,
            )
            time.sleep(1.0)

        print("\n>>> FASE 1: GAS SUELTO (3 s) <<<", flush=True)
        off_vals: list[tuple[float | None, float | None]] = []
        for _ in range(15):
            off_vals.append(read_pair())
            time.sleep(0.2)

        vi_off = [v for v, _ in off_vals if v is not None]
        vm_off = [v for _, v in off_vals if v is not None]
        if vi_off:
            print(f"  IN off:  min={min(vi_off):.3f}  max={max(vi_off):.3f}")
        if vm_off:
            print(f"  MOT off: min={min(vm_off):.3f}  max={max(vm_off):.3f}")

        ref_snap = capture_pedal_map(h, base, veh_ptr)
        print()
        for i in range(3, 0, -1):
            print(f">>> EN {i} PISA ACELERADOR A FONDO (mando) <<<", flush=True)
            time.sleep(1.0)

        print(">>> ACELERA A FONDO AHORA (5 s) <<<", flush=True)
        stats, _n = record_pedal_sweep(h, base, veh_ptr, duration_s=5.0, interval_s=0.1)
        full_snap = capture_pedal_map(h, base, veh_ptr)

        on_vals: list[tuple[float | None, float | None]] = []
        for _ in range(5):
            on_vals.append(read_pair())
            time.sleep(0.2)

        print("\n=== RESULTADO ===")
        vi_on = [v for v, _ in on_vals if v is not None]
        vm_on = [v for _, v in on_vals if v is not None]
        if vi_off and vi_on:
            print(
                f"IN  off~{sum(vi_off)/len(vi_off):.3f} -> on~{sum(vi_on)/len(vi_on):.3f}  "
                f"delta={max(vi_on) - min(vi_off):.3f}"
            )
        if vm_off and vm_on:
            print(
                f"MOT off~{sum(vm_off)/len(vm_off):.3f} -> on~{sum(vm_on)/len(vm_on):.3f}  "
                f"delta={max(vm_on) - min(vm_off):.3f}"
            )

        print("\nTop candidatos (barrido 5s a fondo):")
        for r in rank_pedal_sweep(stats, limit=8):
            print(
                f"  {r['base']}+0x{r['offset']:03X} {r['kind']}  "
                f"span={r['span']:.3f}  min={r['vmin']:.3f}  max={r['vmax']:.3f}"
            )

        deltas = diff_pedal_maps(ref_snap, full_snap, target_delta=0.8, min_delta=0.05)
        print(f"\nDelta memoria off->full: {len(deltas)} hits")
        for r in deltas[:8]:
            d = r.get("delta", 0)
            print(
                f"  {r['base']}+0x{r['offset']:03X} {r['kind']}  delta={d:.3f}"
            )

        if vi_off and vi_on and max(vi_on) - min(vi_off) < 0.1:
            print("\n!! IN NO VARIO — offset tc+0E8+0xC8 puede ser incorrecto para este mando.")
        elif vi_off and vi_on:
            print("\nOK: IN responde al pedal.")

        return 0
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)


if __name__ == "__main__":
    raise SystemExit(main())
