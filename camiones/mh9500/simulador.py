"""
Simulador GMC MH9500 — highway 6x4 (RWD stock).

Config de referencia en juego: offroad + AWD + diff lock en barro.

Nota: `run_sim` usa constantes globales de `sim.core` (radio rueda, torque scale).
La calibracion por camion pesado va en `MH_MUD_*` sobre `VehicleConfig` (offroad AWD+diff).
"""

from __future__ import annotations

from dataclasses import replace

from sim.core import (
    ENGINE_STOCK,
    HIGHWAY_SUBSTANCE_CK1500_MOD,
    SURFACES,
    SurfaceConfig,
    VehicleConfig,
    run_sim,
    sample_at,
    time_to_kmh,
)

TIRES_FACTORY: dict[str, dict[str, float | bool]] = {
    "highway": {"body": 0.8, "asphalt": 2.0, "substance": 0.4, "ignore_ice": False},
    "offroad": {"body": 2.0, "asphalt": 1.0, "substance": 1.2, "ignore_ice": False},
    "allterrain": {"body": 1.0, "asphalt": 1.0, "substance": 1.0, "ignore_ice": False},
    "mudtires": {"body": 3.0, "asphalt": 0.5, "substance": 1.6, "ignore_ice": False},
    "chains": {"body": 2.0, "asphalt": 0.9, "substance": 1.1, "ignore_ice": True},
}
TIRES: dict[str, dict[str, float | bool]] = {n: dict(p) for n, p in TIRES_FACTORY.items()}
TIRES["highway"]["substance"] = HIGHWAY_SUBSTANCE_CK1500_MOD

# Calibracion CE mh_f2_barro_offroad 2026-06 (~5.5 km/h sostenido en barro)
MH_MUD_IMMERSION_RATE = 0.44
MH_MUD_RESIST_MULT = 1.33

ENGINE_STOCK_MH = replace(
    ENGINE_STOCK,
    name="GMC9500 stock",
    torque=140000,
    fuel_consumption=7.5,
    responsiveness=0.035,
    max_delta_ang_vel=0.01,
)

ENGINE_REAL_MH = replace(
    ENGINE_STOCK_MH,
    name="Diesel realista MH9500",
    torque=95000,
    fuel_consumption=4.2,
    responsiveness=0.022,
)

VEHICLE_STOCK = VehicleConfig(
    "MH9500 stock",
    7000,
    240,
    TIRES["highway"],
    "highway",
    num_wheels=6,
    drive_layout="rwd",
)
VEHICLE_REAL = VehicleConfig(
    "MH9500 realista",
    7500,
    220,
    TIRES["highway"],
    "highway",
    num_wheels=6,
    drive_layout="rwd",
)
VEHICLE_REAL_AWD = replace(VEHICLE_REAL, drive_layout="awd", diff_lock=True)

LOAD_SEMI_EMPTY = 2500
LOAD_SEMI_FULL = 12000


def _with_mh_mud_cal(veh: VehicleConfig) -> VehicleConfig:
    """Offroad AWD+diff sin calibracion explicita hereda MH_MUD_* (telemetria / make_vehicle)."""
    if (
        veh.diff_lock
        and veh.drive_layout == "awd"
        and veh.tire_name == "offroad"
        and veh.mud_immersion_rate == 1.0
        and veh.mud_resist_mult == 1.0
    ):
        return replace(
            veh,
            mud_immersion_rate=MH_MUD_IMMERSION_RATE,
            mud_resist_mult=MH_MUD_RESIST_MULT,
        )
    return veh


def make_vehicle(tire_name: str, **kwargs) -> VehicleConfig:
    base = kwargs.pop("base", VEHICLE_REAL)
    return _with_mh_mud_cal(
        replace(base, tire=TIRES[tire_name], tire_name=tire_name, **kwargs)
    )


VEHICLE_REAL_OFFROAD = make_vehicle("offroad", base=VEHICLE_REAL_AWD)


def run_mh_matrix() -> list[dict]:
    rows: list[dict] = []
    configs = [
        ("stock highway RWD", VEHICLE_STOCK, ENGINE_STOCK_MH),
        ("real highway RWD", VEHICLE_REAL, ENGINE_REAL_MH),
        ("real offroad AWD+diff", VEHICLE_REAL_OFFROAD, ENGINE_REAL_MH),
        (
            "real cargado 12t",
            replace(
                VEHICLE_REAL_OFFROAD,
                trailer_mass_kg=LOAD_SEMI_EMPTY,
                trailer_cargo_mass_kg=LOAD_SEMI_FULL,
            ),
            ENGINE_REAL_MH,
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
    accel = run_sim(VEHICLE_REAL, ENGINE_REAL_MH, SurfaceConfig("Asfalto", "asphalt"), 90.0)
    t097 = time_to_kmh(accel.speeds_kmh, accel.times, 97.0)
    t097_str = f"{t097}s" if t097 is not None else "n/a (no alcanza 97 en sim)"

    print("=== GMC MH9500 — mod realista ===\n")
    print(f"Masa stock/real: {VEHICLE_STOCK.mass_kg} / {VEHICLE_REAL.mass_kg} kg | 6 ruedas")
    print(f"Motor stock/real torque: {ENGINE_STOCK_MH.torque} / {ENGINE_REAL_MH.torque} Ncm\n")

    print("--- Asfalto highway RWD (mh_f1_asfalto) ---")
    print(f"  0-97 km/h: {t097_str} | v60: {round(sample_at(accel, 60.0), 1)} km/h\n")

    print("--- Barro marcha baja (mh_f2_barro_offroad) ---")
    for label, veh in (
        ("highway RWD", VEHICLE_REAL),
        ("offroad AWD+diff", VEHICLE_REAL_OFFROAD),
    ):
        s = run_sim(veh, ENGINE_REAL_MH, mud, 120.0, low_gear=True)
        print(
            f"  {label:<18} v30={sample_at(s, 30.0):.1f} "
            f"vmax={max(s.speeds_kmh):.1f} km/h"
        )

    loaded = replace(
        VEHICLE_REAL_OFFROAD,
        trailer_mass_kg=LOAD_SEMI_EMPTY,
        trailer_cargo_mass_kg=LOAD_SEMI_FULL,
    )
    s_load = run_sim(loaded, ENGINE_REAL_MH, mud, 120.0, low_gear=True)
    print(
        f"\n--- Semi cargado (~{LOAD_SEMI_FULL} kg util) barro offroad (mh_f3_semi) ---\n"
        f"  v30={sample_at(s_load, 30.0):.1f} vmax={max(s_load.speeds_kmh):.1f} km/h"
    )


if __name__ == "__main__":
    main()
