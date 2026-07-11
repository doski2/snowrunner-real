"""Banco de pruebas en vivo — gas, RPM y aceleracion (calibracion CE).

Independiente de grabar_telemetria.bat: valida offsets aqui antes de integrar
en el flujo de grabacion.

Uso:
  .\\banco_pruebas.bat --gui
  .\\banco_pruebas.bat
  .\\banco_pruebas.bat --scout
  python cheat_engine/banco_drive.py --gui
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import tkinter as tk
from collections import deque
from tkinter import scrolledtext, ttk

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import memoria_havok as mh  # noqa: E402

from calibrar_drive import (  # noqa: E402
    _vehicle_ptr_from_sample,
    rank_throttle_deltas_for_debug,
    read_live_field,
    scan_throttle_rpm_maps,
)
from pedal_hunt import (  # noqa: E402
    KeySweepStats,
    MemKey,
    attach_targets,
    capture_pedal_map,
    ce_guide_for_row,
    describe_targets,
    diff_pedal_maps,
    dump_bases_cli,
    format_sweep_row,
    hunt_near_target,
    rank_pedal_sweep,
    read_at,
    record_pedal_sweep,
    save_sweep_report,
    sweep_report_to_jsonable,
)

BAR_WIDTH = 24
RPM_BAR_MAX = 3000.0
TRACK_WINDOW_S = 5.0
STUCK_CAL_SAMPLES = 15

# Candidatos a pedal (vehicle+760 suele ser demanda motor, no input jugador)
WATCH_SPECS: list[dict[str, str]] = [
    {"base": "vehicle", "offset": "+0x760", "tag": "v760"},
    {"base": "vehicle", "offset": "+0x75C", "tag": "v75c"},
    {"base": "vehicle", "offset": "+0x754", "tag": "v754"},
    {"base": "vehicle", "offset": "+0x758", "tag": "v758"},
    {"base": "vehicle", "offset": "+0x764", "tag": "v764"},
    {"base": "drive_logic", "offset": "+0x060", "tag": "dl60"},
    {"base": "drive_logic", "offset": "+0x030", "tag": "dl30"},
    {"base": "drive_logic", "offset": "+0x034", "tag": "dl34"},
]


def _parse_f(raw: object) -> float | None:
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def format_bar(value: float | None, *, width: int = BAR_WIDTH) -> str:
    if value is None:
        return "[" + "?" * width + "]"
    v = max(0.0, min(1.0, value))
    filled = int(round(v * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def format_rpm_bar(rpm: float | None, *, width: int = 16, rpm_max: float = RPM_BAR_MAX) -> str:
    if rpm is None:
        return "[" + "?" * width + "]"
    v = max(0.0, min(1.0, rpm / rpm_max))
    filled = int(round(v * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def compute_accel_kmh_s(
    speed_kmh: float | None, t_s: float, last: tuple[float, float] | None
) -> tuple[float | None, tuple[float, float] | None]:
    if speed_kmh is None or last is None:
        return None, (t_s, speed_kmh) if speed_kmh is not None else last
    t0, s0 = last
    dt = t_s - t0
    if dt < 0.05:
        return None, last
    return (speed_kmh - s0) / dt, (t_s, speed_kmh)


def throttle_label(thr: float | None) -> str:
    if thr is None:
        return "sin lectura"
    if thr <= 0.05:
        return "gas SUELTO"
    if thr >= 0.85:
        return "gas FONDO"
    if thr >= 0.35:
        return "acelerando"
    return "gas parcial"


def read_watch_fields(
    h: int, base: int, *, veh_ptr: int | None
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for spec in WATCH_SPECS:
        tag = spec["tag"]
        out[tag] = read_live_field(h, base, spec, veh_ptr=veh_ptr)
    return out


class FieldTracker:
    """Rango min-max por campo en ventana temporal (detectar que responde al pedal)."""

    def __init__(self, window_s: float = TRACK_WINDOW_S) -> None:
        self.window_s = window_s
        self._hist: dict[str, deque[tuple[float, float]]] = {}

    def push(self, t_s: float, values: dict[str, float | None]) -> None:
        for tag, v in values.items():
            if v is None:
                continue
            q = self._hist.setdefault(tag, deque())
            q.append((t_s, v))
            while q and t_s - q[0][0] > self.window_s:
                q.popleft()

    def range(self, tag: str) -> float:
        q = self._hist.get(tag)
        if not q:
            return 0.0
        vals = [v for _, v in q]
        return max(vals) - min(vals)

    def current(self, tag: str) -> float | None:
        q = self._hist.get(tag)
        if not q:
            return None
        return q[-1][1]

    def best_tag(self, *, min_range: float = 0.08) -> str | None:
        best: tuple[float, str] | None = None
        for tag in self._hist:
            r = self.range(tag)
            if r < min_range:
                continue
            if best is None or r > best[0]:
                best = (r, tag)
        return best[1] if best else None


def format_watch_line(values: dict[str, float | None], tracker: FieldTracker) -> str:
    parts: list[str] = []
    for spec in WATCH_SPECS[:6]:
        tag = spec["tag"]
        v = values.get(tag)
        if v is None:
            continue
        r = tracker.range(tag)
        mark = "*" if tracker.best_tag() == tag and r >= 0.08 else ""
        parts.append(f"{tag}={v:.3f}{mark}")
    return "watch: " + " ".join(parts) if parts else ""


def cal_offset_stuck(
    thr: float | None, speed: float | None, stuck_count: int, *, cal_label: str = "CAL"
) -> tuple[bool, str]:
    if thr is None:
        return False, ""
    if thr > 0.92 and stuck_count >= STUCK_CAL_SAMPLES:
        return True, (
            f"{cal_label} pegado ~1.0 — probable demanda motor, no pedal. "
            "Mira watch * o --scout"
        )
    if thr > 0.92 and (speed or 0) < 2.0:
        return True, f"{cal_label} ~1.0 parado — offset incorrecto en marcha"
    return False, ""


def format_banco_line(
    *,
    t_s: float,
    thr_cal: float | None,
    thr_pedal: float | None,
    pedal_tag: str,
    cal_bad: bool,
    rpm: float | None,
    speed_kmh: float | None,
    accel_kmh_s: float | None,
    warn: str = "",
) -> str:
    thr_show = thr_pedal if (cal_bad and thr_pedal is not None) else thr_cal
    thr_s = f"{thr_show:.3f}" if thr_show is not None else "  ?  "
    rpm_s = f"{int(rpm):4d}" if rpm is not None else "   ?"
    spd_s = f"{speed_kmh:5.1f}" if speed_kmh is not None else "    ?"
    acc_s = f"{accel_kmh_s:+5.1f}" if accel_kmh_s is not None else "   ?"
    state = throttle_label(thr_show)

    if cal_bad and thr_pedal is not None:
        cal_s = f"{thr_cal:.3f}" if thr_cal is not None else "?"
        prefix = f"CAL={cal_s} ! | pedal? {pedal_tag} "
    else:
        prefix = "thr "

    line = (
        f"{t_s:6.1f}s | {prefix}{format_bar(thr_show)} {thr_s} | "
        f"rpm {format_rpm_bar(rpm)} {rpm_s} | "
        f"{spd_s} km/h | a={acc_s} km/h/s | {state}"
    )
    if warn:
        line += f" | ** {warn} **"
    return line


def _offset_label(spec: dict | None) -> str:
    if not spec:
        return "(sin calibrar)"
    return f"{spec.get('base', '?')}{spec.get('offset', '?')}"


def _clamp01(v: float | None) -> float:
    if v is None:
        return 0.0
    return max(0.0, min(1.0, v))


def _read_thr_cal(
    h: int,
    base: int,
    sample: dict,
    thr_spec: dict | None,
    veh_ptr: int,
) -> float | None:
    thr = _parse_f(sample.get("throttle"))
    if thr is None and thr_spec:
        thr = read_live_field(h, base, thr_spec, veh_ptr=veh_ptr)
    return thr


class PedalRow:
    """Una fila de la ventana: etiqueta + barra + valor + rango 5s."""

    def __init__(
        self,
        parent: tk.Widget,
        row: int,
        tag: str,
        title: str,
        *,
        is_cal: bool = False,
    ) -> None:
        self.tag = tag
        self.is_cal = is_cal
        bg = "#2b2b2b"
        fg = "#e8e8e8"
        self.frame = tk.Frame(parent, bg=bg)
        self.frame.grid(row=row, column=0, sticky="ew", padx=8, pady=3)
        self.lbl = tk.Label(
            self.frame,
            text=title,
            width=28,
            anchor="w",
            bg=bg,
            fg="#ffaa44" if is_cal else fg,
            font=("Consolas", 9),
        )
        self.lbl.grid(row=0, column=0, sticky="w")
        style = ttk.Style()
        style.configure(
            f"Pedal{tag}.Horizontal.TProgressbar",
            troughcolor="#1a1a1a",
            background="#44cc66" if not is_cal else "#6688cc",
            thickness=18,
        )
        self.bar = ttk.Progressbar(
            self.frame,
            style=f"Pedal{tag}.Horizontal.TProgressbar",
            orient="horizontal",
            length=220,
            mode="determinate",
            maximum=100,
        )
        self.bar.grid(row=0, column=1, padx=(6, 6))
        self.val = tk.Label(
            self.frame, text="?.???", width=7, anchor="e", bg=bg, fg=fg, font=("Consolas", 10, "bold")
        )
        self.val.grid(row=0, column=2)
        self.rng = tk.Label(
            self.frame, text="d5s=?.???", width=9, anchor="e", bg=bg, fg="#888888", font=("Consolas", 8)
        )
        self.rng.grid(row=0, column=3)

    def update(self, value: float | None, delta5: float, *, active: bool, bad: bool) -> None:
        if value is None:
            self.bar["value"] = 0
            self.val.config(text="  ?   ")
            self.rng.config(text="d5s=  ?  ")
            return
        self.bar["value"] = _clamp01(value) * 100.0
        self.val.config(text=f"{value:5.3f}")
        self.rng.config(text=f"d5s={delta5:.3f}")
        if bad:
            self.lbl.config(fg="#ff5555")
            self.bar.configure(style=f"Pedal{self.tag}.Horizontal.TProgressbar")
        elif active:
            self.lbl.config(fg="#55ff88")
        elif self.is_cal:
            self.lbl.config(fg="#ffaa44")
        else:
            self.lbl.config(fg="#e8e8e8")


class PedalWindow:
    """Ventana pedal: CAL + busqueda dinamica (mando / TRUCK_CONTROL)."""

    HUNT_SLOTS = 10

    def __init__(
        self,
        h: int,
        base: int,
        *,
        veh_ptr: int,
        veh_id: str,
        thr_spec: dict | None,
        interval_ms: int = 100,
    ) -> None:
        self.h = h
        self.base = base
        self.veh_ptr = veh_ptr
        self.thr_spec = thr_spec
        self.interval_ms = interval_ms
        self.tracker = FieldTracker()
        self.stuck_hi_count = 0
        self.t0 = time.monotonic()
        self._running = True
        self.ref_snap: dict | None = None
        self.hunt_meta: dict[str, dict | None] = {}
        self.hunt_live = True
        self.last_hunt_scan = 0.0

        self.root = tk.Tk()
        self.root.title("Banco pedal CE")
        self.root.geometry("560x620")
        self.root.configure(bg="#2b2b2b")
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        hdr = tk.Label(
            self.root,
            text=f"Pedal / mando  —  {veh_id}",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 11, "bold"),
        )
        hdr.pack(pady=(8, 2))

        ctrl = tk.Frame(self.root, bg="#2b2b2b")
        ctrl.pack(fill="x", padx=8, pady=4)
        tk.Label(ctrl, text="Objetivo %", bg="#2b2b2b", fg="#ccc", font=("Segoe UI", 9)).pack(
            side="left"
        )
        self.target_pct = tk.DoubleVar(value=25.0)
        tk.Spinbox(
            ctrl,
            from_=0,
            to=100,
            increment=5,
            width=5,
            textvariable=self.target_pct,
            font=("Consolas", 10),
        ).pack(side="left", padx=4)
        tk.Button(ctrl, text="Ref gas 0%", command=self._capture_ref, font=("Segoe UI", 8)).pack(
            side="left", padx=4
        )
        tk.Button(ctrl, text="Delta vs ref", command=self._run_delta_hunt, font=("Segoe UI", 8)).pack(
            side="left", padx=2
        )
        tk.Button(ctrl, text="Bases", command=self._show_bases, font=("Segoe UI", 8)).pack(
            side="left", padx=2
        )
        tk.Button(ctrl, text="Guia CE", command=self._show_ce_guide, font=("Segoe UI", 8)).pack(
            side="left", padx=2
        )
        self.live_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            ctrl,
            text="Vivo ~obj%",
            variable=self.live_var,
            bg="#2b2b2b",
            fg="#ccc",
            selectcolor="#444",
            activebackground="#2b2b2b",
            font=("Segoe UI", 8),
        ).pack(side="left", padx=6)

        sub = tk.Label(
            self.root,
            text="Escaneo profundo: TRUCK_CONTROL + hijos tc+0xNN + drive_logic + vehicle",
            bg="#2b2b2b",
            fg="#888888",
            font=("Segoe UI", 8),
        )
        sub.pack(pady=(0, 4))

        body = tk.Frame(self.root, bg="#2b2b2b")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)

        self.rows: dict[str, PedalRow] = {}
        cal_title = f"CAL {_offset_label(thr_spec)}"
        self.rows["__cal__"] = PedalRow(body, 0, "__cal__", cal_title, is_cal=True)

        tk.Label(
            body,
            text="— candidatos cerca del % mando o delta vs ref —",
            bg="#2b2b2b",
            fg="#666666",
            font=("Segoe UI", 8),
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(6, 2))

        self.hunt_rows: dict[str, PedalRow] = {}
        for i in range(self.HUNT_SLOTS):
            tag = f"hunt{i}"
            self.hunt_rows[tag] = PedalRow(body, i + 2, tag, "—")
            self.hunt_meta[tag] = None

        self.state_lbl = tk.Label(
            self.root,
            text="Pon mando al % objetivo o Ref 0% luego Delta",
            bg="#1e1e1e",
            fg="#55ff88",
            font=("Consolas", 11, "bold"),
            pady=8,
        )
        self.state_lbl.pack(fill="x", side="bottom")
        self.warn_lbl = tk.Label(
            self.root,
            text="vehicle+760 suele ser motor, no mando",
            bg="#2b2b2b",
            fg="#ff8888",
            font=("Segoe UI", 8),
            wraplength=520,
        )
        self.warn_lbl.pack(pady=(0, 6))

        self.root.after(self.interval_ms, self._tick)

    def _capture_ref(self) -> None:
        self.ref_snap = capture_pedal_map(self.h, self.base, self.veh_ptr)
        self.state_lbl.config(text="REF 0% guardada — sube mando al % y pulsa Delta", fg="#ffaa44")

    def _run_delta_hunt(self) -> None:
        if not self.ref_snap:
            self.state_lbl.config(text="Primero: Ref gas 0%", fg="#ff5555")
            return
        now = capture_pedal_map(self.h, self.base, self.veh_ptr)
        target = float(self.target_pct.get()) / 100.0
        results = diff_pedal_maps(self.ref_snap, now, target_delta=target, min_delta=0.03)
        if not results:
            self.state_lbl.config(
                text=f"Sin delta ~{target:.0%} — mira Bases; prueba hijos tc+0xNN", fg="#ff5555"
            )
            return
        attach_targets(results, self.h, self.base, self.veh_ptr)
        self._apply_hunt_results(results)
        self.state_lbl.config(
            text=f"Delta ~{target:.0%}: {len(results)} candidatos (el que marca * varió)",
            fg="#55ff88",
        )

    def _apply_hunt_results(self, results: list[dict]) -> None:
        for i in range(self.HUNT_SLOTS):
            tag = f"hunt{i}"
            if i < len(results):
                r = results[i]
                title = f"{r['base']}+0x{r['offset']:03X} {r['kind']}"
                self.hunt_rows[tag].lbl.config(text=title)
                self.hunt_meta[tag] = r
            else:
                self.hunt_rows[tag].lbl.config(text="—")
                self.hunt_meta[tag] = None

    def _maybe_live_hunt(self, t_s: float) -> None:
        if not self.live_var.get():
            return
        if t_s - self.last_hunt_scan < 0.45:
            return
        self.last_hunt_scan = t_s
        target = float(self.target_pct.get()) / 100.0
        if target < 0.02:
            return
        results = hunt_near_target(
            self.h, self.base, self.veh_ptr, target, tolerance=0.09, limit=self.HUNT_SLOTS
        )
        if results:
            attach_targets(results, self.h, self.base, self.veh_ptr)
            self._apply_hunt_results(results)

    def _show_bases(self) -> None:
        lines = describe_targets(self.h, self.base, self.veh_ptr)
        win = tk.Toplevel(self.root)
        win.title("Bases escaneo pedal")
        win.geometry("520x320")
        win.configure(bg="#2b2b2b")
        txt = scrolledtext.ScrolledText(
            win, wrap="word", font=("Consolas", 9), bg="#1a1a1a", fg="#cccccc"
        )
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("end", "TRUCK_CONTROL + punteros hijos (cada +8 en 0..0x200)\n\n")
        txt.insert("end", "\n".join(lines))
        txt.insert("end", "\n\nPrioridad: tc+XXX antes que vehicle+760 (motor).\n")
        txt.config(state="disabled")

    def _show_ce_guide(self) -> None:
        row = None
        for meta in self.hunt_meta.values():
            if meta:
                row = meta
                break
        if not row:
            self.state_lbl.config(text="Sin candidato — Ref 0% + Delta primero", fg="#ff5555")
            return
        attach_targets([row], self.h, self.base, self.veh_ptr)
        guide = ce_guide_for_row(row)
        win = tk.Toplevel(self.root)
        win.title("Guia Cheat Engine")
        win.geometry("500x280")
        win.configure(bg="#2b2b2b")
        txt = scrolledtext.ScrolledText(
            win, wrap="word", font=("Consolas", 9), bg="#1a1a1a", fg="#aaffaa"
        )
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("end", guide)
        txt.config(state="disabled")

    def _read_hunt_value(self, meta: dict) -> float | None:
        if "value" in meta and "delta" not in meta:
            return read_at(self.h, self.base, self.veh_ptr, meta["base"], meta["offset"])
        if "delta" in meta:
            return read_at(self.h, self.base, self.veh_ptr, meta["base"], meta["offset"])
        return None

    def _on_close(self) -> None:
        self._running = False
        self.root.destroy()

    def _tick(self) -> None:
        if not self._running:
            return
        try:
            self._poll()
        except Exception as exc:
            self.state_lbl.config(text=f"Error lectura: {exc}", fg="#ff5555")
        if self._running:
            self.root.after(self.interval_ms, self._tick)

    def _poll(self) -> None:
        t_s = time.monotonic() - self.t0
        sample = mh.read_active_sample(self.h, self.base)
        if not sample:
            self.state_lbl.config(text="Sin vehiculo", fg="#ffaa44")
            return

        self.veh_ptr = _vehicle_ptr_from_sample(sample) or self.veh_ptr
        mh.enrich_drive_fields(self.h, self.base, sample, t_s=t_s)

        thr_cal = _read_thr_cal(self.h, self.base, sample, self.thr_spec, self.veh_ptr)

        self._maybe_live_hunt(t_s)

        if thr_cal is not None:
            self.tracker.push(t_s, {"__cal__": thr_cal})

        if thr_cal is not None and thr_cal > 0.92:
            self.stuck_hi_count += 1
        else:
            self.stuck_hi_count = 0

        speed = _parse_f(sample.get("speed_kmh"))
        cal_bad, warn = cal_offset_stuck(
            thr_cal, speed, self.stuck_hi_count, cal_label=_offset_label(self.thr_spec)
        )

        d5_cal = self.tracker.range("__cal__")
        self.rows["__cal__"].update(thr_cal, d5_cal, active=False, bad=cal_bad)

        best_tag: str | None = None
        best_range = 0.0
        for tag, meta in self.hunt_meta.items():
            if not meta:
                self.hunt_rows[tag].update(None, 0.0, active=False, bad=False)
                continue
            val = self._read_hunt_value(meta)
            self.tracker.push(t_s, {tag: val})
            d5 = self.tracker.range(tag)
            if d5 > best_range:
                best_range = d5
                best_tag = tag
            target = float(self.target_pct.get()) / 100.0
            self.hunt_rows[tag].update(
                val, d5, active=(tag == best_tag and d5 >= 0.05), bad=False
            )
            if val is not None and abs(val - target) < 0.1:
                self.hunt_rows[tag].val.config(fg="#55ff88")

        show_thr = thr_cal
        if cal_bad and best_tag:
            show_thr = self.tracker.current(best_tag)
        state = throttle_label(show_thr)
        spd = f"{speed:.1f}" if speed is not None else "?"
        tgt = float(self.target_pct.get())
        self.state_lbl.config(
            text=f"{state.upper()}  |  {spd} km/h  |  obj {tgt:.0f}%",
            fg="#55ff88",
        )
        extra = warn or ""
        if cal_bad:
            extra = (extra + " ").strip() + " Usa Ref 0% + Delta con mando al %."
        self.warn_lbl.config(text=extra.strip() or "vehicle+760 = motor; busca en TRUCK_CONTROL")

    def run(self) -> None:
        self.root.mainloop()


def run_gui(*, interval_ms: int = 100) -> int:
    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo — entra al mapa conduciendo.")
        return 1

    h, base, _pid = opened
    ref = mh.load_offsets_reference()
    thr_spec = (ref.get("drive_runtime") or {}).get("candidates", {}).get("throttle_f32")

    try:
        sample = mh.read_active_sample(h, base)
        if not sample:
            print("Sin vehiculo activo.")
            return 1
        veh_ptr = _vehicle_ptr_from_sample(sample)
        veh_id = sample.get("vehicle_id") or "?"
        app = PedalWindow(
            h,
            base,
            veh_ptr=veh_ptr,
            veh_id=veh_id,
            thr_spec=thr_spec,
            interval_ms=interval_ms,
        )
        app.run()
        return 0
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)


def run_scout(h: int, base: int, veh_ptr: int) -> int:
    print("\n=== SCOUT pedal (gas off vs gas fondo) ===")
    print("Motor ON, quieto. Mismo camion que en juego.\n")
    input("1/2 — SUELTA el gas. ENTER...")
    off_thr, _ = scan_throttle_rpm_maps(h, base, veh_ptr=veh_ptr)
    input("2/2 — Gas A FONDO (freno/pared). ENTER...")
    full_thr, _ = scan_throttle_rpm_maps(h, base, veh_ptr=veh_ptr)

    print("\nTop deltas (bloques vehicle + drive_logic):")
    rows = rank_throttle_deltas_for_debug(off_thr, full_thr, limit=15)
    if not rows:
        print("  (ningun float 0..1 cambio >0.01)")
    for delta, key, v0, v1 in rows:
        base_name, off = key
        print(f"  {base_name}+0x{off:03X}: {v0} -> {v1}  (d={delta:+.4f})")

    watch_off = read_watch_fields(h, base, veh_ptr=veh_ptr)
    print("\nWatch list (gas FONDO ahora):")
    for spec in WATCH_SPECS:
        tag = spec["tag"]
        v0 = off_thr.get((spec["base"], mh._parse_hex_offset(spec["offset"]) or -1))
        v1 = watch_off.get(tag)
        if v0 is not None or v1 is not None:
            print(f"  {tag} {spec['base']}{spec['offset']}: off_scan={v0}  ahora={v1}")

    print(
        "\nSi v760~1.0 en ambos pero otro campo cambia, ese es el pedal real.\n"
        "Aplica con: python cheat_engine/calibrar_drive.py --from-snaps gas_off_live gas_full_live --apply"
    )
    return 0


def run_auto_hunt(
    *,
    countdown_s: float = 3.0,
    sweep_duration_s: float = 5.0,
    interval_s: float = 0.08,
    save_path: str | None = None,
) -> int:
    """Graba memoria mientras alternas gas 0%% y 100%% — sin pulsar nada en consola."""
    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo — entra al mapa conduciendo.")
        return 1

    h, base, pid = opened
    snaps_dir = os.path.join(os.path.dirname(__file__), "drive_snaps")
    if save_path is None:
        save_path = os.path.join(snaps_dir, "pedal_sweep_latest.json")

    try:
        sample = mh.read_active_sample(h, base)
        if not sample:
            print("Sin vehiculo activo.")
            return 1
        veh_ptr = _vehicle_ptr_from_sample(sample)
        veh_id = sample.get("vehicle_id") or "?"

        print("=== AUTO-HUNT pedal (sin tocar consola durante grabacion) ===")
        print(f"PID={pid}  vehiculo={veh_id}  veh_ptr={veh_ptr:#x}")
        print(
            f"Escaneo profundo TRUCK_CONTROL + hijos + drive_logic + vehicle\n"
            f"Duracion grabacion: {sweep_duration_s:.0f}s  |  intervalo: {interval_s:.2f}s"
        )
        print("\nINSTRUCCIONES:")
        print("  1. Alt+Tab al juego ANTES de que termine la cuenta atras")
        print("  2. Motor ON, quieto (freno / pared)")
        print("  3. Alterna gas SUELTO y gas FONDO varias veces hasta que pare\n")

        for i in range(int(countdown_s), 0, -1):
            print(f"  ... {i} — cambia al juego", flush=True)
            time.sleep(1.0)
        extra = countdown_s - int(countdown_s)
        if extra > 0.05:
            time.sleep(extra)

        print("\n>>> GRABANDO — alterna 0%% y 100%% ahora <<<", flush=True)

        def _progress(elapsed: float, n: int) -> None:
            pct = min(100, int(100 * elapsed / sweep_duration_s))
            bar = "#" * (pct // 5) + "." * (20 - pct // 5)
            print(f"\r  [{bar}] {elapsed:4.1f}s / {sweep_duration_s:.0f}s  muestras={n}", end="", flush=True)

        stats, n_samples = record_pedal_sweep(
            h,
            base,
            veh_ptr,
            duration_s=sweep_duration_s,
            interval_s=interval_s,
            progress_cb=_progress,
        )
        print("\n\nAnalizando...", flush=True)

        rows = rank_pedal_sweep(stats, limit=20)
        attach_targets(rows, h, base, veh_ptr)

        motor_rows: list[dict] = []
        for key, st in stats.items():
            label, off, kind = key
            if label == "vehicle" and off == 0x760 and st.span >= 0.2:
                motor_rows.append(
                    {
                        "key": key,
                        "base": label,
                        "offset": off,
                        "kind": kind,
                        "vmin": st.vmin,
                        "vmax": st.vmax,
                        "span": st.span,
                        "score": 0.0,
                        "n_low": st.n_low,
                        "n_high": st.n_high,
                    }
                )

        payload = sweep_report_to_jsonable(
            rows,
            veh_id=veh_id,
            duration_s=sweep_duration_s,
            n_samples=n_samples,
            rejected_motor=motor_rows[:3],
        )
        save_sweep_report(save_path, payload)

        print(f"\n=== TOP candidatos pedal ({len(rows)} validos) ===")
        if not rows:
            print("  Ninguno paso filtro (span>=0.35 y visto ~0 y ~1).")
            print("  Repite mas rapido 0%% <-> 100%% o alarga --sweep-duration 8")
            print("\nMayores spans (aunque no pasen filtro):")
            fallback: list[tuple[float, MemKey, KeySweepStats]] = [
                (st.span, k, st) for k, st in stats.items() if st.span >= 0.15
            ]
            fallback.sort(key=lambda x: -x[0])
            for span, key, st in fallback[:12]:
                label, off, kind = key
                print(
                    f"  {label}+0x{off:03X} ({kind}) "
                    f"min={st.vmin:.3f} max={st.vmax:.3f} span={span:.3f} "
                    f"low={st.n_low} high={st.n_high}"
                )
        else:
            for i, row in enumerate(rows[:15], 1):
                mark = " *" if i == 1 else ""
                print(f"  {i:2d}. {format_sweep_row(row)}{mark}")

            top = rows[0]
            print(f"\nMejor candidato: {top['base']}+0x{top['offset']:03X} ({top['kind']})")
            print(ce_guide_for_row(top))

        if motor_rows:
            m = motor_rows[0]
            print(
                f"\n(Referencia motor) vehicle+0x760: "
                f"min={m['vmin']:.3f} max={m['vmax']:.3f} — suele ser demanda, no mando."
            )

        print(f"\nInforme guardado: {save_path}")
        return 0 if rows else 1
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)


def run_banco(*, interval: float = 0.1, duration: float | None = None, scout: bool = False) -> int:
    opened = mh.open_snowrunner()
    if not opened:
        print("SnowRunner no corriendo — entra al mapa conduciendo.")
        return 1

    h, base, pid = opened
    ref = mh.load_offsets_reference()
    cands = (ref.get("drive_runtime") or {}).get("candidates") or {}
    thr_spec = cands.get("throttle_f32")
    rpm_spec = cands.get("engine_rpm_f32")

    try:
        sample = mh.read_active_sample(h, base)
        if not sample:
            print("Sin vehiculo activo.")
            return 1

        veh_ptr = _vehicle_ptr_from_sample(sample)
        veh_id = sample.get("vehicle_id") or "?"
        chain = sample.get("chain") or "?"

        if scout:
            return run_scout(h, base, veh_ptr)

        print("=== Banco pruebas DRIVE (gas / RPM / aceleracion) ===")
        print(f"PID={pid}  vehiculo={veh_id}  chain={chain}  veh={sample.get('veh')}")
        print(f"throttle CAL: {_offset_label(thr_spec)}")
        print(f"rpm:          {_offset_label(rpm_spec)}")
        print(f"intervalo={interval:.2f}s — Ctrl+C salir | --scout para buscar offset pedal")
        print(
            "NOTA: vehicle+760 a menudo = demanda motor (1.0 al ralenti), no el pedal.\n"
            "      Pisa/suelta gas: el campo con * en watch es el que mas varia.\n"
        )

        mh._FUEL_RATE_TRACKER.reset()
        t0 = time.monotonic()
        last_speed: tuple[float, float] | None = None
        tracker = FieldTracker()
        stuck_hi_count = 0
        last_watch_print = 0.0
        persistent_warn = ""

        while True:
            t_s = time.monotonic() - t0
            if duration is not None and t_s >= duration:
                break

            sample = mh.read_active_sample(h, base)
            if not sample:
                print(f"{t_s:6.1f}s | sin vehiculo")
                time.sleep(interval)
                continue

            veh_ptr = _vehicle_ptr_from_sample(sample) or veh_ptr
            mh.enrich_drive_fields(h, base, sample, t_s=t_s)

            thr_cal = _read_thr_cal(h, base, sample, thr_spec, veh_ptr)

            rpm = _parse_f(sample.get("engine_rpm"))
            if rpm is None and rpm_spec:
                rpm = read_live_field(h, base, rpm_spec, veh_ptr=veh_ptr)

            speed = _parse_f(sample.get("speed_kmh"))
            accel, last_speed = compute_accel_kmh_s(speed, t_s, last_speed)

            watch = read_watch_fields(h, base, veh_ptr=veh_ptr)
            tracker.push(t_s, watch)

            if thr_cal is not None and thr_cal > 0.92:
                stuck_hi_count += 1
            else:
                stuck_hi_count = 0

            cal_bad, warn = cal_offset_stuck(
                thr_cal, speed, stuck_hi_count, cal_label=_offset_label(thr_spec)
            )
            best = tracker.best_tag()
            thr_pedal = tracker.current(best) if best else None

            line = format_banco_line(
                t_s=t_s,
                thr_cal=thr_cal,
                thr_pedal=thr_pedal,
                pedal_tag=best or "?",
                cal_bad=cal_bad,
                rpm=rpm,
                speed_kmh=speed,
                accel_kmh_s=accel,
                warn=warn if warn != persistent_warn else "",
            )
            print(line, flush=True)
            if warn:
                persistent_warn = warn

            if t_s - last_watch_print >= 0.5:
                wl = format_watch_line(watch, tracker)
                if wl:
                    print(f"         {wl}", flush=True)
                last_watch_print = t_s

            time.sleep(interval)

        return 0
    except KeyboardInterrupt:
        print("\nBanco detenido.")
        try:
            if tracker.best_tag():
                bt = tracker.best_tag()
                print(
                    f"Sugerencia: campo mas activo en {TRACK_WINDOW_S:.0f}s = "
                    f"{bt} (range={tracker.range(bt):.3f})"
                )
        except NameError:
            pass
        return 0
    finally:
        from ctypes import windll

        windll.kernel32.CloseHandle(h)


def main() -> int:
    parser = argparse.ArgumentParser(description="Banco en vivo gas/RPM/aceleracion")
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--duration", type=float, default=None, metavar="SEC")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Ventana solo pedal (barras en vivo)",
    )
    parser.add_argument(
        "--dump-bases",
        action="store_true",
        help="Listar bloques TRUCK_CONTROL/hijos y salir",
    )
    parser.add_argument(
        "--scout",
        action="store_true",
        help="Buscar offset pedal (gas off / gas fondo, una vez)",
    )
    parser.add_argument(
        "--auto-hunt",
        action="store_true",
        help="Graba 5s mientras alternas gas 0%% y 100%% (sin ENTER)",
    )
    parser.add_argument(
        "--countdown",
        type=float,
        default=3.0,
        metavar="SEC",
        help="Cuenta atras antes de grabar (default 3)",
    )
    parser.add_argument(
        "--sweep-duration",
        type=float,
        default=5.0,
        metavar="SEC",
        help="Segundos de grabacion (default 5)",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        metavar="PATH",
        help="JSON informe (default drive_snaps/pedal_sweep_latest.json)",
    )
    args = parser.parse_args()

    if args.auto_hunt:
        return run_auto_hunt(
            countdown_s=args.countdown,
            sweep_duration_s=args.sweep_duration,
            interval_s=max(0.05, args.interval),
            save_path=args.save,
        )

    if args.dump_bases:
        opened = mh.open_snowrunner()
        if not opened:
            print("SnowRunner no corriendo")
            return 1
        h, base, _ = opened
        try:
            sample = mh.read_active_sample(h, base)
            veh_ptr = _vehicle_ptr_from_sample(sample or {})
            dump_bases_cli(h, base, veh_ptr)
            return 0
        finally:
            from ctypes import windll

            windll.kernel32.CloseHandle(h)

    if args.gui:
        ms = max(50, int(args.interval * 1000))
        return run_gui(interval_ms=ms)
    if args.interval < 0.05:
        print("interval minimo 0.05 s")
        return 1
    return run_banco(interval=args.interval, duration=args.duration, scout=args.scout)


if __name__ == "__main__":
    raise SystemExit(main())
