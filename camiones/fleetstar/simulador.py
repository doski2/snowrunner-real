"""
Simulador International Fleetstar F2070A — 6 ruedas, Si-6V/1900.

Config de referencia en juego: 42\" UHD I (highway), AWD + diff lock.

Nota: `run_sim` usa constantes globales de `sim.core` (radio rueda, torque scale).
La calibracion por camion pesado va en `FS_MUD_*` sobre `VehicleConfig`.
"""

from __future__ import annotations

from dataclasses import replace

from sim.core import (
    ENGINE_STOCK,
    EngineConfig,
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

# Calibracion CE fs_f2_barro_uhd 2026-06 (~2–3 km/h crawl en barro)
FS_MUD_IMMERSION_RATE = 0.58
FS_MUD_RESIST_MULT = 1.08
ENGINE_STOCK_FS = replace(
    ENGINE_STOCK,
    name="Si-6V/1900 stock",
    torque=135000,
    fuel_consumption=5.5,
    responsiveness=0.035,
    max_delta_ang_vel=0.01,
)

ENGINE_REAL_FS = replace(
    ENGINE_STOCK_FS,
    name="Si-6V/1900 realista Fleetstar",
    torque=92000,
    fuel_consumption=3.6,
    responsiveness=0.024,
)

# Si-6V/2100T (us_truck_old_engine_1): mismo ratio de nerfeo que 1900 (92/135 ≈ 0,681)
ENGINE_STOCK_FS_2100 = replace(
    ENGINE_STOCK_FS,
    name="Si-6V/2100T stock",
    torque=145000,
    fuel_consumption=6.0,
)

ENGINE_REAL_FS_2100 = replace(
    ENGINE_STOCK_FS_2100,
    name="Si-6V/2100T realista Fleetstar",
    torque=99000,
    fuel_consumption=3.9,
    responsiveness=0.024,
)

FS_ENGINE_XML_1900 = "us_truck_old_engine_0"
FS_ENGINE_XML_2100 = "us_truck_old_engine_1"


def engine_for_fleetstar(engine_id: str, engine_name_xml: str = "") -> EngineConfig:
    """Motor sim/CE: protocolo fs_real o engine_name_xml del catalogo en sesion."""
    xml = (engine_name_xml or "").strip()
    use_2100 = engine_id == "fs_real_2100" or xml == FS_ENGINE_XML_2100
    if engine_id == "fs_stock":
        return ENGINE_STOCK_FS_2100 if use_2100 else ENGINE_STOCK_FS
    if use_2100:
        return ENGINE_REAL_FS_2100
    return ENGINE_REAL_FS

VEHICLE_STOCK = VehicleConfig(
    "Fleetstar stock",
    6300,
    240,
    TIRES["highway"],
    "highway",
    num_wheels=6,
    drive_layout="rwd",
)
VEHICLE_REAL = VehicleConfig(
    "Fleetstar realista",
    6650,
    210,
    TIRES["highway"],
    "highway",
    num_wheels=6,
    drive_layout="rwd",
)
VEHICLE_REAL_AWD = replace(VEHICLE_REAL, drive_layout="awd", diff_lock=True)
VEHICLE_REAL_AWD_HIGHWAY = replace(
    VEHICLE_REAL_AWD,
    tire=TIRES["highway"],
    tire_name="highway",
    mud_immersion_rate=FS_MUD_IMMERSION_RATE,
    mud_resist_mult=FS_MUD_RESIST_MULT,
)
VEHICLE_REAL_OFFROAD = replace(
    VEHICLE_REAL_AWD,
    tire=TIRES["offroad"],
    tire_name="offroad",
    mud_immersion_rate=FS_MUD_IMMERSION_RATE,
    mud_resist_mult=FS_MUD_RESIST_MULT,
)

LOAD_FRAME_EMPTY = 1800
LOAD_FRAME_FULL = 8000


def _with_fs_mud_cal(veh: VehicleConfig) -> VehicleConfig:
    """AWD+diff sin calibracion explicita hereda FS_MUD_* (telemetria / make_vehicle)."""
    if (
        veh.diff_lock
        and veh.drive_layout == "awd"
        and veh.mud_immersion_rate == 1.0
        and veh.mud_resist_mult == 1.0
    ):
        return replace(
            veh,
            mud_immersion_rate=FS_MUD_IMMERSION_RATE,
            mud_resist_mult=FS_MUD_RESIST_MULT,
        )
    return veh


def make_vehicle(tire_name: str, **kwargs) -> VehicleConfig:
    base = kwargs.pop("base", VEHICLE_REAL)
    return _with_fs_mud_cal(
        replace(base, tire=TIRES[tire_name], tire_name=tire_name, **kwargs)
    )

def run_fs_matrix() -> list[dict]:
    rows: list[dict] = []
    configs = [
        ("stock highway RWD", VEHICLE_STOCK, ENGINE_STOCK_FS),
        ("real highway RWD", VEHICLE_REAL, ENGINE_REAL_FS),
        ("real UHD+AWD+diff barro", VEHICLE_REAL_AWD_HIGHWAY, ENGINE_REAL_FS),
        ("real offroad AWD+diff", VEHICLE_REAL_OFFROAD, ENGINE_REAL_FS),
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
    setup = VEHICLE_REAL_AWD_HIGHWAY
    mud = SurfaceConfig("Barro", "mud", viscosity=4.0)

    print("=== Fleetstar F2070A — mod realista ===\n")
    print(f"Masa stock/real: {VEHICLE_STOCK.mass_kg} / {VEHICLE_REAL.mass_kg} kg | 6 ruedas")
    print(
        f"Si-6V/1900 stock/real: {ENGINE_STOCK_FS.torque} / {ENGINE_REAL_FS.torque} Ncm"
    )
    print(
        f"Si-6V/2100T stock/real: {ENGINE_STOCK_FS_2100.torque} / {ENGINE_REAL_FS_2100.torque} Ncm\n"
    )

    print("--- Asfalto UHD + AWD + diff (fs_f1_asfalto) ---")
    for label, eng in (
        ("Si-6V/1900", ENGINE_REAL_FS),
        ("Si-6V/2100T", ENGINE_REAL_FS_2100),
    ):
        a = run_sim(setup, eng, SurfaceConfig("Asfalto", "asphalt"), 90.0)
        t097 = time_to_kmh(a.speeds_kmh, a.times, 97.0)
        print(f"  {label:<14} 0-97 km/h: {t097}s | v60: {round(sample_at(a, 60.0), 1)} km/h")
    print()

    print("--- Barro marcha baja ---")
    for label, veh in (
        ("UHD I + AWD + diff", VEHICLE_REAL_AWD_HIGHWAY),
        ("offroad + AWD + diff", VEHICLE_REAL_OFFROAD),
    ):
        s = run_sim(veh, ENGINE_REAL_FS, mud, 120.0, low_gear=True)
        print(f"  {label:<22} v30={sample_at(s, 30.0):.1f} vmax={max(s.speeds_kmh):.1f} km/h")

    loaded = replace(
        VEHICLE_REAL_AWD_HIGHWAY,
        cargo_mass_kg=LOAD_FRAME_FULL,
    )
    s_load = run_sim(loaded, ENGINE_REAL_FS, mud, 120.0, low_gear=True)
    print(
        f"\n--- Bastidor cargado (~{LOAD_FRAME_FULL} kg util) barro UHD ---\n"
        f"  v30={sample_at(s_load, 30.0):.1f} vmax={max(s_load.speeds_kmh):.1f} km/h"
    )

if __name__ == "__main__":
    main()
