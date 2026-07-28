"""
Simulador KRS 58 Bandit — 8x8 OFFROAD, LAZ 6 T60, 51\" UHD I.

Referencia: diff Always, traccion 8x8 (AWD en sim), bastidor en F3.
"""

from __future__ import annotations

from dataclasses import replace

from sim.core import (
    ENGINE_STOCK,
    HIGHWAY_SUBSTANCE_CK1500_MOD,
    EngineConfig,
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

BANDIT_MUD_IMMERSION_RATE = 0.52
BANDIT_MUD_RESIST_MULT = 1.12

ENGINE_STOCK_BANDIT_LAZ = replace(
    ENGINE_STOCK,
    name="LAZ 6 T60 stock",
    torque=130000,
    fuel_consumption=4.5,
    responsiveness=0.040,
    max_delta_ang_vel=0.01,
)

ENGINE_REAL_BANDIT_LAZ = replace(
    ENGINE_STOCK_BANDIT_LAZ,
    name="LAZ 6 T60 realista Bandit",
    torque=88500,
    fuel_consumption=3.1,
    responsiveness=0.028,
)

BANDIT_ENGINE_XML_LAZ = "ru_truck_old_engine_0"
BANDIT_ENGINE_XML_T195 = "ru_truck_old_engine_1"
BANDIT_ENGINE_XML_IMZ6 = "ru_truck_old_engine_2"
BANDIT_ENGINE_XML_TA240 = "ru_truck_old_engine_3"

ENGINE_STOCK_BANDIT_T195 = replace(
    ENGINE_STOCK_BANDIT_LAZ,
    name="LAZ 6 T195 stock",
    torque=140000,
    fuel_consumption=5.5,
)
ENGINE_REAL_BANDIT_T195 = replace(
    ENGINE_REAL_BANDIT_LAZ,
    name="LAZ 6 T195 realista Bandit",
    torque=95300,
    fuel_consumption=3.7,
)

ENGINE_STOCK_BANDIT_IMZ6 = replace(
    ENGINE_STOCK_BANDIT_LAZ,
    name="IMZ-6 210 stock",
    torque=160000,
    fuel_consumption=6.0,
)
ENGINE_REAL_BANDIT_IMZ6 = replace(
    ENGINE_REAL_BANDIT_LAZ,
    name="IMZ-6 210 realista Bandit",
    torque=108900,
    fuel_consumption=4.1,
)

ENGINE_STOCK_BANDIT_TA240 = replace(
    ENGINE_STOCK_BANDIT_LAZ,
    name="LAZ 6 TA240 stock",
    torque=185000,
    fuel_consumption=7.5,
)
ENGINE_REAL_BANDIT_TA240 = replace(
    ENGINE_REAL_BANDIT_LAZ,
    name="LAZ 6 TA240 realista Bandit",
    torque=125900,
    fuel_consumption=5.1,
)

VEHICLE_STOCK = VehicleConfig(
    "Bandit stock",
    7014,
    150,
    TIRES["highway"],
    "highway",
    num_wheels=8,
    diff_lock=True,
    drive_layout="awd",
)
VEHICLE_REAL = VehicleConfig(
    "Bandit realista",
    7600,
    135,
    TIRES["highway"],
    "highway",
    num_wheels=8,
    diff_lock=True,
    drive_layout="awd",
    mud_immersion_rate=BANDIT_MUD_IMMERSION_RATE,
    mud_resist_mult=BANDIT_MUD_RESIST_MULT,
)

LOAD_FRAME_FULL = 5050


def engine_for_bandit(engine_id: str, engine_name_xml: str = "") -> EngineConfig:
    xml = (engine_name_xml or "").strip()
    stock = engine_id == "bandit_stock"
    if xml == BANDIT_ENGINE_XML_T195 or engine_id == "bandit_t195":
        return ENGINE_STOCK_BANDIT_T195 if stock else ENGINE_REAL_BANDIT_T195
    if xml == BANDIT_ENGINE_XML_IMZ6 or engine_id == "bandit_imz6":
        return ENGINE_STOCK_BANDIT_IMZ6 if stock else ENGINE_REAL_BANDIT_IMZ6
    if xml == BANDIT_ENGINE_XML_TA240 or engine_id == "bandit_ta240":
        return ENGINE_STOCK_BANDIT_TA240 if stock else ENGINE_REAL_BANDIT_TA240
    if stock:
        return ENGINE_STOCK_BANDIT_LAZ
    return ENGINE_REAL_BANDIT_LAZ


def _with_bandit_mud_cal(veh: VehicleConfig) -> VehicleConfig:
    if (
        veh.diff_lock
        and veh.drive_layout in ("awd", "4wd")
        and veh.mud_immersion_rate == 1.0
        and veh.mud_resist_mult == 1.0
    ):
        return replace(
            veh,
            mud_immersion_rate=BANDIT_MUD_IMMERSION_RATE,
            mud_resist_mult=BANDIT_MUD_RESIST_MULT,
        )
    return veh


def make_vehicle(tire_name: str, **kwargs) -> VehicleConfig:
    base = kwargs.pop("base", VEHICLE_REAL)
    tire_key = tire_name if tire_name in TIRES else "highway"
    return _with_bandit_mud_cal(
        replace(base, tire=TIRES[tire_key], tire_name=tire_key, **kwargs)
    )


def main() -> None:
    mud = SurfaceConfig("Barro", "mud", viscosity=4.0)
    asphalt = SurfaceConfig("Asfalto", "asphalt")
    eng = ENGINE_REAL_BANDIT_LAZ
    veh = make_vehicle("highway")

    print("=== KRS 58 Bandit — mod realista ===\n")
    print(f"Masa stock/real: {VEHICLE_STOCK.mass_kg} / {VEHICLE_REAL.mass_kg} kg")
    print(
        f"LAZ 6 T60 stock/real: {ENGINE_STOCK_BANDIT_LAZ.torque} / "
        f"{ENGINE_REAL_BANDIT_LAZ.torque} Ncm"
    )
    print(f"UHD I substance mod: {TIRES['highway']['substance']}\n")

    accel = run_sim(veh, eng, asphalt, 90.0)
    t097 = time_to_kmh(accel.speeds_kmh, accel.times, 97.0)
    print("--- Asfalto 51\" UHD I + diff (bandit_f1_asfalto) ---")
    print(f"  0-97 km/h: {t097}s | v60: {round(sample_at(accel, 60.0), 1)} km/h\n")

    crawl = run_sim(veh, eng, mud, 120.0, low_gear=True)
    print("--- Barro marcha baja (bandit_f2_barro_uhd) ---")
    print(
        f"  v30={sample_at(crawl, 30.0):.1f} vmax={max(crawl.speeds_kmh):.1f} km/h"
    )

    loaded = replace(VEHICLE_REAL, cargo_mass_kg=LOAD_FRAME_FULL)
    s_load = run_sim(make_vehicle("highway", base=loaded), eng, mud, 120.0, low_gear=True)
    print(
        f"\n--- Bastidor cargado barro (bandit_f3_carga) ---\n"
        f"  v30={sample_at(s_load, 30.0):.1f} vmax={max(s_load.speeds_kmh):.1f} km/h"
    )


if __name__ == "__main__":
    main()
