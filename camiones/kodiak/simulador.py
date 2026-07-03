"""
Simulador Chevrolet Kodiak C70 — 4 ruedas, Si-6V, 39\" UHD I.

El Kodiak usa neumaticos 39\" (max 43\" en taller), no 42\" como Fleetstar.
Mismo XML `highway_1` en `wheels_medium_double`; la sim usa perfil `highway`.
"""

from __future__ import annotations

from dataclasses import replace

from camiones.fleetstar.simulador import (
    ENGINE_REAL_FS,
    ENGINE_REAL_FS_2100,
    ENGINE_STOCK_FS,
    ENGINE_STOCK_FS_2100,
    TIRES,
    engine_for_fleetstar,
)
from sim.core import (
    HIGHWAY_SUBSTANCE_CK1500_MOD,
    SURFACES,
    SurfaceConfig,
    VehicleConfig,
    run_sim,
    sample_at,
    time_to_kmh,
)

# Hereda substance UHD mod (0.5) via TIRES importado de fleetstar
assert TIRES["highway"]["substance"] == HIGHWAY_SUBSTANCE_CK1500_MOD

# Inicial — re-grabar kd_f2_barro_uhd para afinar
KD_MUD_IMMERSION_RATE = 0.55
KD_MUD_RESIST_MULT = 1.12

VEHICLE_STOCK = VehicleConfig(
    "Kodiak C70 stock",
    7513,
    200,
    TIRES["highway"],
    "highway",
    num_wheels=4,
    drive_layout="rwd",
)
VEHICLE_REAL = VehicleConfig(
    "Kodiak C70 realista",
    7900,
    175,
    TIRES["highway"],
    "highway",
    num_wheels=4,
    drive_layout="rwd",
    mud_immersion_rate=KD_MUD_IMMERSION_RATE,
    mud_resist_mult=KD_MUD_RESIST_MULT,
)
VEHICLE_REAL_AWD = replace(VEHICLE_REAL, drive_layout="awd", diff_lock=True)
VEHICLE_REAL_AWD_HIGHWAY = replace(
    VEHICLE_REAL_AWD,
    tire=TIRES["highway"],
    tire_name="highway",
    mud_immersion_rate=KD_MUD_IMMERSION_RATE,
    mud_resist_mult=KD_MUD_RESIST_MULT,
)
VEHICLE_REAL_OFFROAD = replace(
    VEHICLE_REAL_AWD,
    tire=TIRES["offroad"],
    tire_name="offroad",
    mud_immersion_rate=KD_MUD_IMMERSION_RATE,
    mud_resist_mult=KD_MUD_RESIST_MULT,
)

LOAD_FRAME_FULL = 6000


def _with_kd_mud_cal(veh: VehicleConfig) -> VehicleConfig:
    if (
        veh.diff_lock
        and veh.drive_layout in ("awd", "4wd")
        and veh.mud_immersion_rate == 1.0
        and veh.mud_resist_mult == 1.0
    ):
        return replace(
            veh,
            mud_immersion_rate=KD_MUD_IMMERSION_RATE,
            mud_resist_mult=KD_MUD_RESIST_MULT,
        )
    return veh


def make_vehicle(tire_name: str, **kwargs) -> VehicleConfig:
    base = kwargs.pop("base", VEHICLE_REAL)
    return _with_kd_mud_cal(
        replace(base, tire=TIRES[tire_name], tire_name=tire_name, **kwargs)
    )


def main() -> None:
    setup = VEHICLE_REAL_AWD_HIGHWAY
    mud = SurfaceConfig("Barro", "mud", viscosity=4.0)

    print("=== Chevrolet Kodiak C70 — mod realista ===\n")
    print(f"Masa stock/real: {VEHICLE_STOCK.mass_kg} / {VEHICLE_REAL.mass_kg} kg | 4 ruedas")
    print(
        f"Si-6V/1900 stock/real: {ENGINE_STOCK_FS.torque} / {ENGINE_REAL_FS.torque} Ncm"
    )
    print(
        f"Si-6V/2100T stock/real: {ENGINE_STOCK_FS_2100.torque} / {ENGINE_REAL_FS_2100.torque} Ncm\n"
    )

    print("--- Asfalto 39\" UHD + AWD + diff (kd_f1_asfalto) ---")
    for label, eng in (
        ("Si-6V/1900", ENGINE_REAL_FS),
        ("Si-6V/2100T", ENGINE_REAL_FS_2100),
    ):
        a = run_sim(setup, eng, SurfaceConfig("Asfalto", "asphalt"), 90.0)
        t097 = time_to_kmh(a.speeds_kmh, a.times, 97.0)
        print(f"  {label:<14} 0-97 km/h: {t097}s | v60: {round(sample_at(a, 60.0), 1)} km/h")
    print()

    print("--- Barro marcha baja (kd_f2_barro_uhd) — 39\" UHD, KD_MUD_* sin CE ---")
    for label, veh in (
        ("39\" UHD + AWD + diff", VEHICLE_REAL_AWD_HIGHWAY),
        ("offroad + AWD + diff", VEHICLE_REAL_OFFROAD),
    ):
        s = run_sim(veh, ENGINE_REAL_FS, mud, 120.0, low_gear=True)
        print(f"  {label:<22} v30={sample_at(s, 30.0):.1f} vmax={max(s.speeds_kmh):.1f} km/h")

    loaded = replace(VEHICLE_REAL_AWD_HIGHWAY, cargo_mass_kg=LOAD_FRAME_FULL)
    s_load = run_sim(loaded, ENGINE_REAL_FS, mud, 120.0, low_gear=True)
    print(
        f"\n--- Bastidor cargado (~{LOAD_FRAME_FULL} kg util) ---\n"
        f"  v30={sample_at(s_load, 30.0):.1f} vmax={max(s_load.speeds_kmh):.1f} km/h"
    )


if __name__ == "__main__":
    main()
