"""
Simulador KHAN 39 Marshall — Scout 4x4, Kr 104, 45\" TM II, 4WD+diff stock.

Referencia en juego: suspensión reptadora + mudtires_2 (wheels_scout_yar_871, Radius=1).

Nota: `run_sim` usa constantes globales de `sim.core` (radio rueda, torque scale).
La calibracion por scout va en `KM_MUD_*` sobre `VehicleConfig`.
"""

from __future__ import annotations

from dataclasses import replace

from sim.core import (
    ENGINE_STOCK,
    SURFACES,
    SurfaceConfig,
    VehicleConfig,
    run_sim,
    sample_at,
    time_to_kmh,
)

MUDTIRES_TM2_SUBSTANCE_MOD = 1.7

TIRES_FACTORY: dict[str, dict[str, float | bool]] = {
    "highway": {"body": 0.8, "asphalt": 2.0, "substance": 0.4, "ignore_ice": False},
    "offroad": {"body": 2.0, "asphalt": 1.0, "substance": 1.2, "ignore_ice": False},
    "allterrain": {"body": 1.0, "asphalt": 1.0, "substance": 1.0, "ignore_ice": False},
    "mudtires": {"body": 3.0, "asphalt": 0.5, "substance": 1.6, "ignore_ice": False},
    "chains": {"body": 2.0, "asphalt": 0.9, "substance": 1.1, "ignore_ice": True},
}
TIRES: dict[str, dict[str, float | bool]] = {n: dict(p) for n, p in TIRES_FACTORY.items()}
TIRES["mudtires"]["substance"] = MUDTIRES_TM2_SUBSTANCE_MOD

# Neumáticos 45\" — más flotación en barro (calibrar con CE km_f2_barro_tm2)
KM_MUD_IMMERSION_RATE = 0.38
# CE km_f2_barro_tm2 20260629 — crawl ~12 km/h; 0.72 daba sim ~33 km/h
KM_MUD_RESIST_MULT = 2.0

ENGINE_STOCK_KM = replace(
    ENGINE_STOCK,
    name="Kr 104 stock",
    torque=30000,
    fuel_consumption=0.6,
    responsiveness=0.04,
    max_delta_ang_vel=0.01,
)

ENGINE_REAL_KM = replace(
    ENGINE_STOCK_KM,
    name="Kr 104 realista Marshall",
    torque=28000,
    fuel_consumption=0.75,
    responsiveness=0.035,
)

VEHICLE_STOCK = VehicleConfig(
    "Marshall stock",
    1500,
    70,
    TIRES["mudtires"],
    "mudtires",
    diff_lock=True,
    drive_layout="4wd",
)
VEHICLE_REAL = VehicleConfig(
    "Marshall realista",
    1780,
    70,
    TIRES["mudtires"],
    "mudtires",
    diff_lock=True,
    drive_layout="4wd",
    mud_immersion_rate=KM_MUD_IMMERSION_RATE,
    mud_resist_mult=KM_MUD_RESIST_MULT,
)

LOAD_TRAILER_MASS = 800
LOAD_TRAILER_CARGO = 1000


def _with_km_mud_cal(veh: VehicleConfig) -> VehicleConfig:
    """4WD+diff sin calibracion explicita hereda KM_MUD_* (telemetria / make_vehicle)."""
    if (
        veh.diff_lock
        and veh.drive_layout in ("4wd", "awd")
        and veh.mud_immersion_rate == 1.0
        and veh.mud_resist_mult == 1.0
    ):
        return replace(
            veh,
            mud_immersion_rate=KM_MUD_IMMERSION_RATE,
            mud_resist_mult=KM_MUD_RESIST_MULT,
        )
    return veh


def make_vehicle(tire_name: str, **kwargs) -> VehicleConfig:
    base = kwargs.pop("base", VEHICLE_REAL)
    return _with_km_mud_cal(
        replace(base, tire=TIRES[tire_name], tire_name=tire_name, **kwargs)
    )


def run_km_matrix() -> list[dict]:
    rows: list[dict] = []
    configs = [
        ("stock TM II AWD+diff", VEHICLE_STOCK, ENGINE_STOCK_KM),
        ("real TM II AWD+diff", VEHICLE_REAL, ENGINE_REAL_KM),
        (
            "real + remolque scout",
            replace(
                VEHICLE_REAL,
                trailer_mass_kg=LOAD_TRAILER_MASS,
                trailer_cargo_mass_kg=LOAD_TRAILER_CARGO,
            ),
            ENGINE_REAL_KM,
        ),
    ]
    for label, veh, eng in configs:
        for surface in SURFACES:
            low = surface.kind in ("mud", "deep_mud")
            series = run_sim(veh, eng, surface, 60.0, low_gear=low)
            rows.append(
                {
                    "config": label,
                    "surface": surface.name,
                    "v30": round(sample_at(series, 30.0), 1),
                    "v60": round(series.speeds_kmh[-1], 1),
                }
            )
    return rows


def main() -> None:
    mud = SurfaceConfig("Barro", "mud", viscosity=4.0)
    deep = SurfaceConfig("Barro profundo", "deep_mud", viscosity=4.0, water_depth=0.4)
    asphalt = SurfaceConfig("Asfalto", "asphalt")
    accel = run_sim(VEHICLE_REAL, ENGINE_REAL_KM, asphalt, 90.0)
    t097 = time_to_kmh(accel.speeds_kmh, accel.times, 97.0)

    print("=== KHAN 39 Marshall — mod realista ===\n")
    print(f"Masa stock/real: {VEHICLE_STOCK.mass_kg} / {VEHICLE_REAL.mass_kg} kg")
    print(f"Kr 104 stock/real: {ENGINE_STOCK_KM.torque} / {ENGINE_REAL_KM.torque} Ncm")
    print(f"TM II substance mod: {MUDTIRES_TM2_SUBSTANCE_MOD}\n")

    print("--- Asfalto TM II + diff (km_f1_asfalto) ---")
    print(f"  0-97 km/h: {t097}s | v60: {round(sample_at(accel, 60.0), 1)} km/h\n")

    print("--- Barro marcha baja (km_f2_barro_tm2) ---")
    for label, surf in (("barro", mud), ("barro profundo", deep)):
        s = run_sim(VEHICLE_REAL, ENGINE_REAL_KM, surf, 120.0, low_gear=True)
        print(
            f"  {label:<18} v30={sample_at(s, 30.0):.1f} "
            f"vmax={max(s.speeds_kmh):.1f} km/h"
        )

    loaded = replace(
        VEHICLE_REAL,
        trailer_mass_kg=LOAD_TRAILER_MASS,
        trailer_cargo_mass_kg=LOAD_TRAILER_CARGO,
    )
    s_load = run_sim(loaded, ENGINE_REAL_KM, mud, 120.0, low_gear=True)
    print(
        f"\n--- Remolque scout (~{LOAD_TRAILER_MASS + LOAD_TRAILER_CARGO} kg) barro (km_f3_carga) ---\n"
        f"  v30={sample_at(s_load, 30.0):.1f} vmax={max(s_load.speeds_kmh):.1f} km/h"
    )


if __name__ == "__main__":
    main()
