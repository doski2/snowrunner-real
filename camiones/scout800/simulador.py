"""
Simulador International Scout 800 — AAT-6V 4.0, 33\" HS I, diff siempre.

Calibrar S8_MUD_* con CE s8_f2_barro_hs.
"""

from __future__ import annotations

from dataclasses import replace

from sim.core import SURFACES, SurfaceConfig, VehicleConfig, run_sim, sample_at, time_to_kmh

# wheels_scout_highway — JAT HS I (catalogo)
TIRE_HS_I: dict[str, float | bool] = {
    "body": 0.7,
    "asphalt": 2.0,
    "substance": 0.3,
    "ignore_ice": False,
}

TIRES: dict[str, dict[str, float | bool]] = {
    "highway_hs_i": TIRE_HS_I,
}

S8_MUD_IMMERSION_RATE = 0.45
S8_MUD_RESIST_MULT = 1.35

from camiones.scout800.engines import ENGINE_AAT6V_REAL, ENGINE_AAT6V_STOCK

VEHICLE_STOCK = VehicleConfig(
    "Scout 800 stock",
    2800.0,
    72.0,
    TIRE_HS_I,
    "highway_hs_i",
    diff_lock=True,
    drive_layout="4wd",
)
VEHICLE_REAL = VehicleConfig(
    "Scout 800 realista",
    2350.0,
    72.0,
    TIRE_HS_I,
    "highway_hs_i",
    diff_lock=True,
    drive_layout="4wd",
    mud_immersion_rate=S8_MUD_IMMERSION_RATE,
    mud_resist_mult=S8_MUD_RESIST_MULT,
)


def make_vehicle(tire_name: str = "highway_hs_i", **kwargs) -> VehicleConfig:
    base = kwargs.pop("base", VEHICLE_REAL)
    tire = TIRES.get(tire_name, TIRE_HS_I)
    return replace(base, tire=dict(tire), tire_name=tire_name, **kwargs)


def run_asphalt_accel(engine=ENGINE_AAT6V_REAL, duration_s: float = 80.0):
    surface = next(s for s in SURFACES if s.kind == "asphalt")
    return run_sim(VEHICLE_REAL, engine, surface, duration_s)


if __name__ == "__main__":
    surface = SurfaceConfig("Asfalto", "asphalt")
    for label, eng in (("stock", ENGINE_AAT6V_STOCK), ("real", ENGINE_AAT6V_REAL)):
        series = run_sim(VEHICLE_REAL, eng, surface, 80.0)
        t60 = time_to_kmh(series, 60.0)
        print(f"--- S800 {label} HS I asfalto ---")
        print(f"  v30={sample_at(series, 30):.1f} km/h  v60={sample_at(series, 60):.1f}  t0-60={t60}s")
