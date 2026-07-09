"""
Simulador Tatra T813 — 8x8 HEAVY, KZGT-8, JAT MSH I 50\".

Referencia: diff instalado, traccion 8x8 (AWD en sim), semirremolque en F3.
"""

from __future__ import annotations

from dataclasses import replace

from sim.core import (
    ENGINE_STOCK,
    EngineConfig,
    SURFACES,
    SurfaceConfig,
    VehicleConfig,
    run_sim,
    sample_at,
    time_to_kmh,
)

MSH_I_SUBSTANCE_MOD = 2.2

TIRES_FACTORY: dict[str, dict[str, float | bool]] = {
    "highway": {"body": 0.8, "asphalt": 2.0, "substance": 0.4, "ignore_ice": False},
    "offroad": {"body": 2.0, "asphalt": 1.0, "substance": 1.2, "ignore_ice": False},
    "allterrain": {"body": 1.0, "asphalt": 1.0, "substance": 1.0, "ignore_ice": False},
    "mudtires": {"body": 3.0, "asphalt": 0.5, "substance": 1.6, "ignore_ice": False},
    "msh_i": {
        "body": 3.0,
        "asphalt": 0.6,
        "substance": MSH_I_SUBSTANCE_MOD,
        "ignore_ice": False,
    },
    "chains": {"body": 2.0, "asphalt": 0.9, "substance": 1.1, "ignore_ice": True},
}
TIRES: dict[str, dict[str, float | bool]] = {n: dict(p) for n, p in TIRES_FACTORY.items()}

T813_MUD_IMMERSION_RATE = 0.48
T813_MUD_RESIST_MULT = 1.18

ENGINE_STOCK_T813_KZGT = replace(
    ENGINE_STOCK,
    name="KZGT-8 stock",
    torque=230000,
    fuel_consumption=10.0,
    responsiveness=0.045,
    max_delta_ang_vel=0.01,
)

ENGINE_REAL_T813_KZGT = replace(
    ENGINE_STOCK_T813_KZGT,
    name="KZGT-8 realista T813",
    torque=157000,
    fuel_consumption=6.8,
    responsiveness=0.032,
)

T813_ENGINE_XML_KZGT = "ru_special_engine_1"
T813_ENGINE_XML_TOP = "ru_special_engine_2"

VEHICLE_STOCK = VehicleConfig(
    "T813 stock",
    14021,
    380,
    TIRES["msh_i"],
    "msh_i",
    num_wheels=8,
    diff_lock=True,
    drive_layout="awd",
)
VEHICLE_REAL = VehicleConfig(
    "T813 realista",
    14571,
    340,
    TIRES["msh_i"],
    "msh_i",
    num_wheels=8,
    diff_lock=True,
    drive_layout="awd",
    mud_immersion_rate=T813_MUD_IMMERSION_RATE,
    mud_resist_mult=T813_MUD_RESIST_MULT,
)

LOAD_SEMI_EMPTY = 2500
LOAD_SEMI_FULL = 12000


def engine_for_t813(engine_id: str, engine_name_xml: str = "") -> EngineConfig:
    xml = (engine_name_xml or "").strip()
    use_top = engine_id == "t813_kzgt_top" or xml == T813_ENGINE_XML_TOP
    if engine_id == "t813_stock":
        if use_top:
            return replace(
                ENGINE_STOCK_T813_KZGT,
                name="KZGT top stock",
                torque=260000,
                fuel_consumption=11.5,
            )
        return ENGINE_STOCK_T813_KZGT
    if use_top:
        return replace(
            ENGINE_REAL_T813_KZGT,
            name="KZGT top realista T813",
            torque=177000,
            fuel_consumption=7.8,
        )
    return ENGINE_REAL_T813_KZGT


def _with_t813_mud_cal(veh: VehicleConfig) -> VehicleConfig:
    if (
        veh.diff_lock
        and veh.drive_layout in ("awd", "4wd")
        and veh.mud_immersion_rate == 1.0
        and veh.mud_resist_mult == 1.0
    ):
        return replace(
            veh,
            mud_immersion_rate=T813_MUD_IMMERSION_RATE,
            mud_resist_mult=T813_MUD_RESIST_MULT,
        )
    return veh


def make_vehicle(tire_name: str, **kwargs) -> VehicleConfig:
    base = kwargs.pop("base", VEHICLE_REAL)
    tire_key = tire_name if tire_name in TIRES else "msh_i"
    return _with_t813_mud_cal(
        replace(base, tire=TIRES[tire_key], tire_name=tire_key, **kwargs)
    )


def main() -> None:
    mud = SurfaceConfig("Barro", "mud", viscosity=4.0)
    asphalt = SurfaceConfig("Asfalto", "asphalt")
    eng = ENGINE_REAL_T813_KZGT
    veh = make_vehicle("msh_i")

    print("=== Tatra T813 — mod realista ===\n")
    print(f"Masa stock/real: {VEHICLE_STOCK.mass_kg} / {VEHICLE_REAL.mass_kg} kg")
    print(
        f"KZGT stock/real: {ENGINE_STOCK_T813_KZGT.torque} / {ENGINE_REAL_T813_KZGT.torque} Ncm"
    )
    print(f"MSH I substance mod: {MSH_I_SUBSTANCE_MOD}\n")

    accel = run_sim(veh, eng, asphalt, 90.0)
    t097 = time_to_kmh(accel.speeds_kmh, accel.times, 97.0)
    print("--- Asfalto MSH I + diff (t813_f1_asfalto) ---")
    print(f"  0-97 km/h: {t097}s | v60: {round(sample_at(accel, 60.0), 1)} km/h\n")

    crawl = run_sim(veh, eng, mud, 120.0, low_gear=True)
    print("--- Barro marcha baja (t813_f2_barro_msh) ---")
    print(
        f"  v30={sample_at(crawl, 30.0):.1f} vmax={max(crawl.speeds_kmh):.1f} km/h"
    )

    loaded = replace(
        VEHICLE_REAL,
        trailer_mass_kg=LOAD_SEMI_EMPTY,
        trailer_cargo_mass_kg=LOAD_SEMI_FULL,
    )
    s_load = run_sim(make_vehicle("msh_i", base=loaded), eng, mud, 120.0, low_gear=True)
    print(
        f"\n--- Semi cargado barro (t813_f3_carga) ---\n"
        f"  v30={sample_at(s_load, 30.0):.1f} vmax={max(s_load.speeds_kmh):.1f} km/h"
    )


if __name__ == "__main__":
    main()
