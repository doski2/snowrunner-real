"""Monitor en vivo del pedal (mando / volante) vs demanda motor.

SnowRunner no expone DirectInput al exterior; leemos memoria en TRUCK_CONTROL
y hijos (input 0..1) frente a vehicle+0x760 (torque filtrado).

Uso:
  python cheat_engine/pedal_monitor.py
  python cheat_engine/banco_drive.py --mando
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memoria_havok as mh  # noqa: E402
from banco_drive import (  # noqa: E402
    FieldTracker,
    _offset_label,
    _parse_f,
    _vehicle_ptr_from_sample,
    format_bar,
    throttle_label,
)
from calibrar_drive import read_live_field  # noqa: E402
from pedal_hunt import load_sweep_watch_specs  # noqa: E402


def _clear_console() -> None:
    os.system("cls" if os.name == "nt" else "clear")


from throttle_resolver import per_vehicle_specs, resolve_throttle_input_spec  # noqa: E402


def _throttle_specs(h: int, base: int, veh_ptr: int, veh_id: str) -> tuple[dict[str, str], dict[str, str], str]:
    ref = mh.load_offsets_reference()
    drive_ref = ref.get("drive_runtime") or {}
    cands = mh._normalized_drive_candidates(drive_ref.get("candidates") or {})
    inp, src = resolve_throttle_input_spec(
        h,
        base,
        veh_ptr,
        veh_id,
        global_spec=cands.get("throttle_input") or cands.get("throttle_f32"),
        per_vehicle=per_vehicle_specs(drive_ref),
    )
    mot = cands.get("throttle_motor_f32") or dict(mh.DEFAULT_THROTTLE_MOTOR_SPEC)
    return dict(inp or {}), dict(mot), src


def _read_spec(
    h: int,
    base: int,
    veh_ptr: int,
    spec: dict[str, str],
    sample: dict,
    sample_key: str,
) -> float | None:
    v = _parse_f(sample.get(sample_key))
    if v is not None:
        return v
    if spec:
        return read_live_field(h, base, spec, veh_ptr=veh_ptr)
    return None


def _spec_label(spec: dict[str, str], fallback: str) -> str:
    if not spec:
        return fallback
    return _offset_label(spec)


def _watch_rows(
    h: int,
    base: int,
    veh_ptr: int,
    specs: list[dict[str, str]],
    tracker: FieldTracker,
    t_s: float,
) -> list[tuple[str, float | None, float, bool]]:
    rows: list[tuple[str, float | None, float, bool]] = []
    best_tag = ""
    best_span = 0.0
    spans: dict[str, float] = {}
    for i, spec in enumerate(specs):
        tag = f"w{i}"
        val = read_live_field(h, base, spec, veh_ptr=veh_ptr)
        tracker.push(t_s, {tag: val})
        span = tracker.range(tag)
        spans[tag] = span
        if span > best_span:
            best_span = span
            best_tag = tag
        label = f"{spec.get('base', '?')}{spec.get('offset', '?')} {spec.get('kind', 'f32')}"
        rows.append((label, val, span, False))
    for i, tag in enumerate(spans):
        if tag == best_tag and spans[tag] >= 0.08:
            label, val, span, _ = rows[i]
            rows[i] = (label, val, span, True)
    return rows


def run_console_monitor(*, interval: float = 0.12, duration: float | None = None) -> int:
    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo — entra al mapa conduciendo.")
        return 1

    h, base, pid = opened
    watch_specs = load_sweep_watch_specs(limit=6)
    filtered_watch: list[dict[str, str]] = []

    tracker = FieldTracker(window_s=5.0)
    t0 = time.monotonic()
    stuck_motor = 0

    try:
        sample = mh.read_active_sample(h, base)
        if not sample:
            print("Sin vehiculo activo.")
            return 1
        veh_ptr = _vehicle_ptr_from_sample(sample) or 0
        veh_id = sample.get("vehicle_id") or "?"
        inp_spec, mot_spec, thr_src = _throttle_specs(h, base, veh_ptr, veh_id)

        print("Monitor mando — Ctrl+C salir")
        print("Alterna gas SUELTO / PARCIAL / FONDO; IN = controles juego (TRUCK_CONTROL).\n")
        time.sleep(0.5)

        while True:
            t_s = time.monotonic() - t0
            if duration is not None and t_s >= duration:
                break

            sample = mh.read_active_sample(h, base)
            if not sample:
                _clear_console()
                print("Sin vehiculo...")
                time.sleep(interval)
                continue

            veh_ptr = _vehicle_ptr_from_sample(sample) or veh_ptr
            inp_spec, mot_spec, thr_src = _throttle_specs(h, base, veh_ptr, veh_id)
            if not filtered_watch:
                inp_key = (inp_spec.get("base"), inp_spec.get("offset"), inp_spec.get("kind"))
                filtered_watch = [
                    s
                    for s in watch_specs
                    if (s.get("base"), s.get("offset"), s.get("kind")) != inp_key
                ]
            mh.enrich_drive_fields(h, base, sample, t_s=t_s)

            thr_in = _read_spec(h, base, veh_ptr, inp_spec, sample, "throttle_input")
            thr_mot = _read_spec(h, base, veh_ptr, mot_spec, sample, "throttle_motor")
            rpm = _parse_f(sample.get("engine_rpm"))
            speed = _parse_f(sample.get("speed_kmh"))

            tracker.push(t_s, {"__in__": thr_in, "__mot__": thr_mot})
            d_in = tracker.range("__in__")
            d_mot = tracker.range("__mot__")

            if thr_mot is not None and thr_mot > 0.92 and (speed or 0) < 2:
                stuck_motor += 1
            else:
                stuck_motor = 0

            watch = _watch_rows(h, base, veh_ptr, filtered_watch, tracker, t_s)

            _clear_console()
            print("=== MONITOR MANDO / GAS (memoria CE) ===")
            print(f"PID={pid}  veh={veh_id}  src={thr_src}  {t_s:6.1f}s  {speed or 0:.1f} km/h")
            if not inp_spec:
                print(
                    "\n  !! Sin offset IN para este camion."
                    "\n     Ejecuta: .\\banco_auto_pedal.bat  luego  --from-sweep --apply"
                )
            print()
            print("  PEDAL (input jugador)     MOTOR (demanda filtrada)")
            print("  ---------------------     ------------------------")

            in_bar = format_bar(thr_in if thr_in is not None else 0.0)
            mot_bar = format_bar(thr_mot if thr_mot is not None else 0.0)
            in_s = f"{thr_in:.3f}" if thr_in is not None else "  ? "
            mot_s = f"{thr_mot:.3f}" if thr_mot is not None else "  ? "
            print(
                f"  IN  {_spec_label(inp_spec, 'sin calibrar'):22} "
                f"{in_bar} {in_s}  var5s={d_in:.2f}"
            )
            print(
                f"  MOT {_spec_label(mot_spec, 'vehicle+0x760'):22} "
                f"{mot_bar} {mot_s}  var5s={d_mot:.2f}"
            )
            if rpm is not None:
                print(f"  RPM vehicle+0x114              {rpm:7.0f}")

            if watch:
                print("\n  Otros candidatos (barrido auto-hunt):")
                for label, val, span, star in watch:
                    mark = " *" if star else "  "
                    vb = format_bar(val if val is not None else 0.0)
                    vs = f"{val:.3f}" if val is not None else "  ? "
                    print(f"  {mark} {label:28} {vb} {vs}  var5s={span:.2f}")

            state = throttle_label(thr_in)
            print(f"\n  Estado: {state.upper()}")
            if stuck_motor > 8 and d_in < 0.1:
                print(
                    "\n  !! MOT ~1.0 fijo y IN no varia — recalibra input:"
                    "\n     .\\banco_auto_pedal.bat"
                    "\n     python cheat_engine/calibrar_drive.py --from-sweep --apply"
                )
            elif d_in >= 0.15:
                print("  OK: IN responde al mando/teclado.")
            else:
                print("  Pisa/suelta gas — mira que fila marca * (var5s sube).")

            time.sleep(interval)
        return 0
    except KeyboardInterrupt:
        print("\nFin monitor.")
        return 0
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Monitor pedal mando vs motor")
    parser.add_argument("--interval", type=float, default=0.12)
    parser.add_argument("--duration", type=float, default=None)
    args = parser.parse_args()
    return run_console_monitor(interval=args.interval, duration=args.duration)


if __name__ == "__main__":
    raise SystemExit(main())
