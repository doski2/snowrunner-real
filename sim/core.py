"""
Simulador SnowRunner CK1500 — modelo completo.

Capas de fisica (Saber + aproximaciones Havok):
  motor, caja, neumaticos, terreno, wheel slip, barro deformable,
  agua, diferencial 4x4 abierto/bloqueado, dano al motor.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, replace

# --- Constantes fisicas ----------------------------------------------------

WHEEL_RADIUS = 0.38
VEL_PER_ANGVEL = 1.85
NUM_WHEELS = 4
G = 9.81
TORQUE_SCALE = 0.028
FUEL_UNIT_SCALE = 0.0011
IDLE_FUEL_FRAC = 0.09  # ralenti motor encendido (~9 % del consumo a pleno gas)
ANGVEL_RAMP = 120.0
DT = 0.02

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_JSON = os.path.join(ROOT, "simulacion_resultados.json")
CARGO_RESULTS_JSON = os.path.join(ROOT, "simulacion_carga.json")
TERRAIN_RESULTS_JSON = os.path.join(ROOT, "simulacion_terreno.json")
TIRE_RESULTS_JSON = os.path.join(ROOT, "simulacion_neumaticos.json")

MUD_RESIST_COEF = {
    "highway": 11.0,
    "offroad": 3.8,
    "allterrain": 4.5,
    "mudtires": 2.2,
    "chains": 4.0,
}

HIGHWAY_SUBSTANCE_GENERIC = 0.2
HIGHWAY_SUBSTANCE_CK1500_FACTORY = 0.4
HIGHWAY_SUBSTANCE_CK1500_MOD = 0.5

TIRES_FACTORY: dict[str, dict[str, float | bool]] = {
    "highway": {"body": 0.8, "asphalt": 2.0, "substance": 0.4, "ignore_ice": False},
    "offroad": {"body": 2.0, "asphalt": 1.0, "substance": 1.2, "ignore_ice": False},
    "allterrain": {"body": 1.0, "asphalt": 1.0, "substance": 1.0, "ignore_ice": False},
    "mudtires": {"body": 3.0, "asphalt": 0.5, "substance": 1.6, "ignore_ice": False},
    "chains": {"body": 2.0, "asphalt": 0.9, "substance": 1.1, "ignore_ice": True},
}

TIRES: dict[str, dict[str, float | bool]] = {
    name: dict(profile) for name, profile in TIRES_FACTORY.items()
}
TIRES["highway"]["substance"] = HIGHWAY_SUBSTANCE_CK1500_MOD

# --- Configuracion vehiculo / motor ----------------------------------------


@dataclass(frozen=True)
class Gear:
    ang_vel: float
    fuel_mod: float


@dataclass(frozen=True)
class GearboxConfig:
    fuel_consumption: float = 1.8
    awd_modifier: float = 1.1
    low_gear_ang_vel: float = 1.5
    gears: tuple[Gear, ...] = (
        Gear(3, 1.7),
        Gear(6, 1.5),
        Gear(8, 1.3),
        Gear(14, 1.0),
        Gear(20, 0.9),
    )


GEARBOX = GearboxConfig()


@dataclass
class EngineConfig:
    name: str
    torque: float
    fuel_consumption: float
    responsiveness: float
    max_delta_ang_vel: float
    damage_capacity: float = 100.0
    critical_threshold: float = 0.6
    damaged_min_torque_mult: float = 1.0
    damaged_max_torque_mult: float = 0.6
    damaged_consumption_modifier: float = 1.8
    damage_pct: float = 0.0


@dataclass
class VehicleConfig:
    label: str
    mass_kg: float
    fuel_capacity_l: float
    tire: dict = field(default_factory=lambda: TIRES["highway"].copy())
    tire_name: str = "highway"
    diff_lock: bool = False
    snorkel: bool = False
    addon_mass_kg: float = 0.0
    cargo_mass_kg: float = 0.0
    trailer_mass_kg: float = 0.0
    trailer_cargo_mass_kg: float = 0.0
    num_wheels: int = 4
    drive_layout: str = "4wd"  # 4wd | rwd | awd
    mud_immersion_rate: float = 1.0  # <1 = hunde menos (camiones pesados)
    mud_resist_mult: float = 1.0  # <1 = menos resistencia barro


def total_mass_kg(vehicle: VehicleConfig) -> float:
    return (
        vehicle.mass_kg
        + vehicle.addon_mass_kg
        + vehicle.cargo_mass_kg
        + vehicle.trailer_mass_kg
        + vehicle.trailer_cargo_mass_kg
    )


TRAILER_ROLL_COEF = 0.018
TRAILER_HITCH_DRAG = 0.004


@dataclass
class SurfaceConfig:
    name: str
    kind: str  # asphalt | dirt | gravel | mud | snow | ice | water | deep_mud
    grade_pct: float = 0.0
    viscosity: float = 0.0
    water_depth: float = 0.0


@dataclass
class SimState:
    throttle_filt: float = 0.0
    wheel_ang_vel: float = 0.0
    ground_speed: float = 0.0
    gear_idx: int = 0
    fuel_used: float = 0.0
    mud_immersion: float = 0.0
    slip_ratio: float = 0.0
    traction_used: float = 0.0


@dataclass
class SimSeries:
    times: list[float]
    speeds_kmh: list[float]
    slips: list[float]
    immersions: list[float]
    state: SimState


ENGINE_STOCK = EngineConfig("CK1500 exclusivo", 62000, 3.3, 0.4, 10.0)
ENGINE_I6 = EngineConfig("250/292 I6", 40000, 1.5, 0.28, 0.015)
VEHICLE_I6 = VehicleConfig("Realista I6", 1750, 76, TIRES["highway"], "highway")

SURFACES = [
    SurfaceConfig("Asfalto", "asphalt"),
    SurfaceConfig("Tierra", "dirt", viscosity=3.0),
    SurfaceConfig("Grava", "gravel"),
    SurfaceConfig("Barro", "mud", viscosity=4.0),
    SurfaceConfig("Barro profundo", "deep_mud", viscosity=4.0, water_depth=0.4),
    SurfaceConfig("Nieve", "snow", viscosity=2.0),
    SurfaceConfig("Hielo", "ice"),
    SurfaceConfig("Agua poco prof.", "water", water_depth=0.35),
    SurfaceConfig("Agua profunda", "water", water_depth=0.75),
]

CONFIGS: list[tuple[VehicleConfig, EngineConfig]] = [
    (VehicleConfig("Juego original", 2200, 80, TIRES["highway"], "highway"), ENGINE_STOCK),
    (VEHICLE_I6, ENGINE_I6),
    (VehicleConfig("Realista I6 offroad", 1750, 76, TIRES["offroad"], "offroad"), ENGINE_I6),
    (
        VehicleConfig(
            "Realista I6 + diff lock", 1750, 76, TIRES["offroad"], "offroad", diff_lock=True
        ),
        ENGINE_I6,
    ),
    (
        VehicleConfig("Realista I6 danado", 1750, 76, TIRES["offroad"], "offroad", diff_lock=True),
        replace(ENGINE_I6, damage_pct=0.75),
    ),
]


def make_vehicle(tire_name: str, **kwargs) -> VehicleConfig:
    return VehicleConfig("test", 1750, 76, TIRES[tire_name], tire_name, **kwargs)


# --- Parches de neumaticos (Fase 2) ----------------------------------------


@dataclass(frozen=True)
class ScoutVehicle:
    """Contexto Scout: el CK1500 usa highway_1 (substance 0.4); el resto plantilla 0.2."""

    id: str
    label: str
    highway_substance: float


SCOUT_VEHICLES = (
    ScoutVehicle("ck1500", "Chevrolet CK1500", HIGHWAY_SUBSTANCE_CK1500_FACTORY),
    ScoutVehicle("scout_generic", "Scout generico", HIGHWAY_SUBSTANCE_GENERIC),
)


@dataclass(frozen=True)
class TirePatchPlan:
    """Describe un escenario de parche XML."""

    id: str
    label: str
    # Parche global _templates/trucks.xml: tipo -> deltas de friccion
    global_by_type: dict[str, dict[str, float | bool]]
    # Parche solo wheels_scout1 highway_1 (CK1500 default)
    ck1500_highway_delta: dict[str, float | bool]


PATCH_FACTORY = TirePatchPlan("factory", "Fabrica", {}, {})

# Fase 2 opcion B: solo highway_1 del CK1500
PATCH_CK1500_HIGHWAY = TirePatchPlan(
    "ck1500_only",
    "Solo CK1500 highway_1 (+0.1 vs fabrica)",
    {},
    {"substance": HIGHWAY_SUBSTANCE_CK1500_MOD},
)

# Fase 2 opcion C: plantilla ScoutHighway (generic 0.2 -> 0.35); override CK1500 se mantiene
PATCH_GLOBAL_TEMPLATE = TirePatchPlan(
    "global_template",
    "Plantilla ScoutHighway global",
    {"highway": {"substance": 0.35}},
    {},
)

# Buff global estilo comunidad: +20% substance en todos los tipos
PATCH_GLOBAL_BUFF = TirePatchPlan(
    "global_buff",
    "Buff global todos los tipos (+20% substance)",
    {
        "highway": {"substance": HIGHWAY_SUBSTANCE_GENERIC * 1.2},
        "offroad": {"substance": 1.2 * 1.2},
        "allterrain": {"substance": 1.0 * 1.2},
        "mudtires": {"substance": 1.6 * 1.2},
        "chains": {"substance": 1.1 * 1.2},
    },
    {},
)

TIRE_PATCH_PLANS = (
    PATCH_FACTORY,
    PATCH_CK1500_HIGHWAY,
    PATCH_GLOBAL_TEMPLATE,
    PATCH_GLOBAL_BUFF,
)

TIRE_TEST_SURFACES = (
    SurfaceConfig("Asfalto", "asphalt"),
    SurfaceConfig("Barro", "mud", viscosity=4.0),
    SurfaceConfig("Nieve", "snow", viscosity=2.0),
    SurfaceConfig("Hielo", "ice"),
    SurfaceConfig("Agua poco prof.", "water", water_depth=0.35),
)

TIRE_TYPES_TEST = ("highway", "offroad", "allterrain", "mudtires", "chains")


def _copy_tire_catalog() -> dict[str, dict[str, float | bool]]:
    return {name: dict(profile) for name, profile in TIRES_FACTORY.items()}


def apply_global_tire_patch(
    catalog: dict[str, dict[str, float | bool]],
    deltas_by_type: dict[str, dict[str, float | bool]],
) -> dict[str, dict[str, float | bool]]:
    out = {name: dict(profile) for name, profile in catalog.items()}
    for tire_type, deltas in deltas_by_type.items():
        if tire_type in out:
            out[tire_type].update(deltas)
    return out


def _highway_substance(scout: ScoutVehicle, plan: TirePatchPlan) -> float:
    sub = scout.highway_substance
    tpl = plan.global_by_type.get("highway", {})
    if scout.id == "scout_generic" and "substance" in tpl:
        sub = float(tpl["substance"])
    if scout.id == "ck1500" and "substance" in plan.ck1500_highway_delta:
        sub = float(plan.ck1500_highway_delta["substance"])
    return sub


def build_scout_vehicle(
    scout: ScoutVehicle,
    tire_type: str,
    catalog: dict[str, dict[str, float | bool]],
    plan: TirePatchPlan,
    **kwargs,
) -> VehicleConfig:
    profile = dict(catalog[tire_type])
    if tire_type == "highway":
        profile["substance"] = _highway_substance(scout, plan)
    return VehicleConfig(scout.label, 1750, 76, profile, tire_type, **kwargs)


def tire_catalog_for_plan(plan: TirePatchPlan) -> dict[str, dict[str, float | bool]]:
    return apply_global_tire_patch(TIRES_FACTORY, plan.global_by_type)


def sim_v30(
    vehicle: VehicleConfig,
    surface: SurfaceConfig,
    engine: EngineConfig = ENGINE_I6,
    duration_s: float = 45.0,
) -> float:
    return round(sample_at(run_sim(vehicle, engine, surface, duration_s), 30.0), 2)


@dataclass
class TirePatchCell:
    plan_id: str
    scout_id: str
    tire_type: str
    surface: str
    v30_kmh: float
    mu: float
    substance: float


def run_tire_patch_matrix(
    plans: tuple[TirePatchPlan, ...] = TIRE_PATCH_PLANS,
    scouts: tuple[ScoutVehicle, ...] = SCOUT_VEHICLES,
    tire_types: tuple[str, ...] = TIRE_TYPES_TEST,
    surfaces: tuple[SurfaceConfig, ...] = TIRE_TEST_SURFACES,
) -> list[TirePatchCell]:
    rows: list[TirePatchCell] = []
    for plan in plans:
        catalog = tire_catalog_for_plan(plan)
        for scout in scouts:
            for tire_type in tire_types:
                veh = build_scout_vehicle(scout, tire_type, catalog, plan)
                prof = veh.tire
                for surface in surfaces:
                    immersion = 0.2 if surface.kind in ("mud", "deep_mud", "water") else 0.0
                    rows.append(
                        TirePatchCell(
                            plan_id=plan.id,
                            scout_id=scout.id,
                            tire_type=tire_type,
                            surface=surface.name,
                            v30_kmh=sim_v30(veh, surface),
                            mu=round(surface_mu(prof, surface, immersion), 3),
                            substance=prof["substance"],
                        )
                    )
    return rows


def compare_patch_delta(
    matrix: list[TirePatchCell],
    base_plan: str,
    target_plan: str,
) -> list[dict]:
    """Diferencia target - base por celda (mismo scout, neumatico, superficie)."""
    index = {(c.scout_id, c.tire_type, c.surface): c for c in matrix if c.plan_id == base_plan}
    diffs: list[dict] = []
    for cell in matrix:
        if cell.plan_id != target_plan:
            continue
        key = (cell.scout_id, cell.tire_type, cell.surface)
        base = index.get(key)
        if not base:
            continue
        diffs.append(
            {
                "scout": cell.scout_id,
                "tire": cell.tire_type,
                "surface": cell.surface,
                "base_v30": base.v30_kmh,
                "target_v30": cell.v30_kmh,
                "delta_v30": round(cell.v30_kmh - base.v30_kmh, 2),
                "base_mu": base.mu,
                "target_mu": cell.mu,
                "delta_mu": round(cell.mu - base.mu, 3),
                "base_substance": base.substance,
                "target_substance": cell.substance,
                "delta_substance": round(cell.substance - base.substance, 3),
            }
        )
    return diffs


def summarize_ck1500_vs_global(matrix: list[TirePatchCell]) -> dict:
    """Resumen: que cambia solo en CK1500 vs que cambia en todos los Scouts."""
    ck_only = compare_patch_delta(matrix, "factory", "ck1500_only")
    global_tpl = compare_patch_delta(matrix, "factory", "global_template")
    global_buf = compare_patch_delta(matrix, "factory", "global_buff")

    def _nonzero(rows: list[dict], scout: str) -> list[dict]:
        return [
            r
            for r in rows
            if r["scout"] == scout
            and (r["delta_v30"] != 0 or r["delta_mu"] != 0 or r["delta_substance"] != 0)
        ]

    return {
        "ck1500_only_changes_on_ck1500": _nonzero(ck_only, "ck1500"),
        "ck1500_only_changes_on_generic": _nonzero(ck_only, "scout_generic"),
        "global_template_changes_on_ck1500": _nonzero(global_tpl, "ck1500"),
        "global_template_changes_on_generic": _nonzero(global_tpl, "scout_generic"),
        "global_buff_changes_on_ck1500": _nonzero(global_buf, "ck1500"),
        "global_buff_changes_on_generic": _nonzero(global_buf, "scout_generic"),
    }


def sample_at(series: SimSeries, seconds: float) -> float:
    idx = min(len(series.speeds_kmh) - 1, int(seconds / DT))
    return series.speeds_kmh[idx]


def sample_slip(series: SimSeries, seconds: float) -> float:
    idx = min(len(series.slips) - 1, int(seconds / DT))
    return series.slips[idx]


def sample_immersion(series: SimSeries, seconds: float) -> float:
    idx = min(len(series.immersions) - 1, int(seconds / DT))
    return series.immersions[idx]


# --- Fisica ----------------------------------------------------------------


def surface_mu(tire: dict, surface: SurfaceConfig, immersion: float) -> float:
    if surface.kind == "asphalt":
        return tire["asphalt"]
    if surface.kind == "ice":
        return 0.08 if not tire.get("ignore_ice") else 0.85
    if surface.kind == "gravel":
        return tire["body"] * 0.85
    if surface.kind in ("mud", "deep_mud", "snow", "water"):
        mu = tire["substance"]
        if surface.kind == "snow" and tire.get("ignore_ice"):
            mu = max(mu, 1.0)
        if surface.viscosity > 0:
            mu *= max(0.08, 1.0 - (surface.viscosity - 2.0) * 0.1)
        mu *= max(0.15, 1.0 - immersion * 0.7)
        if surface.kind == "water":
            mu *= max(0.05, 1.0 - surface.water_depth * 1.2)
        if surface.kind == "deep_mud":
            mu *= 0.65
        return mu
    return tire["body"]


def _damage_lerp(engine: EngineConfig) -> float:
    span = max(0.001, 1.0 - engine.critical_threshold)
    return (engine.damage_pct - engine.critical_threshold) / span


def engine_torque_mult(engine: EngineConfig) -> float:
    if engine.damage_pct <= engine.critical_threshold:
        return 1.0
    t = _damage_lerp(engine)
    lo, hi = engine.damaged_min_torque_mult, engine.damaged_max_torque_mult
    return lo + (hi - lo) * t


def engine_fuel_mult(engine: EngineConfig) -> float:
    if engine.damage_pct <= engine.critical_threshold:
        return 1.0
    t = _damage_lerp(engine)
    return 1.0 + (engine.damaged_consumption_modifier - 1.0) * t


def pick_gear(wheel_ang_vel: float, low_gear: bool) -> tuple[int, float]:
    if low_gear:
        return -1, GEARBOX.low_gear_ang_vel
    for i, g in enumerate(GEARBOX.gears):
        if wheel_ang_vel < g.ang_vel * 0.9:
            return i, g.ang_vel
    last = GEARBOX.gears[-1]
    return len(GEARBOX.gears) - 1, last.ang_vel


def diff_efficiency(vehicle: VehicleConfig, surface: SurfaceConfig, wheel_mu: list[float]) -> float:
    if vehicle.diff_lock:
        return 1.0
    if vehicle.drive_layout == "rwd" and vehicle.num_wheels >= 6:
        rear = wheel_mu[2:]
        worst, best = min(rear), max(rear)
        if best < 0.01:
            return 0.2
        return 0.25 + 0.4 * (worst / best)
    if surface.kind in ("asphalt", "gravel", "dirt"):
        return 0.92
    worst, best = min(wheel_mu), max(wheel_mu)
    if best < 0.01:
        return 0.25
    return 0.3 + 0.45 * (worst / best)


def wheel_mu_per_axle(
    tire: dict, surface: SurfaceConfig, immersion: float, vehicle: VehicleConfig | None = None
) -> list[float]:
    base = surface_mu(tire, surface, immersion)
    n = vehicle.num_wheels if vehicle else NUM_WHEELS
    if n == 6:
        if surface.kind in ("mud", "deep_mud", "water"):
            profile = [base * 0.7, base * 0.7, base * 1.02, base * 0.88, base * 0.82, base * 0.95]
        else:
            profile = [base * 0.95, base * 0.95, base * 1.02, base * 0.98, base * 0.92, base * 0.98]
        return profile
    if surface.kind in ("mud", "deep_mud", "water"):
        return [base * 1.05, base * 0.85, base * 0.75, base * 0.95]
    return [base] * NUM_WHEELS


def _traction_mu(vehicle: VehicleConfig, wheel_mus: list[float]) -> float:
    if vehicle.num_wheels >= 6 and vehicle.drive_layout == "rwd":
        rear = wheel_mus[2:]
        return sum(rear) / len(rear)
    return sum(wheel_mus) / len(wheel_mus)


def slip_traction_factor(slip: float, surface: SurfaceConfig) -> float:
    """Un poco de patinaje ayuda a encontrar grip en barro/nieve."""
    if surface.kind not in ("mud", "deep_mud", "snow", "water"):
        return 1.0 if slip < 0.15 else max(0.6, 1.0 - slip * 0.5)
    if slip < 0.05:
        return 0.7
    if slip < 0.35:
        return 1.0 + slip * 0.6
    if slip < 0.7:
        return 1.15 - (slip - 0.35) * 0.4
    return max(0.25, 0.9 - slip * 0.5)


def update_mud_immersion(
    state: SimState,
    surface: SurfaceConfig,
    slip: float,
    v: float,
    dt: float,
    immersion_rate: float = 1.0,
    tire_name: str = "highway",
    diff_lock: bool = False,
) -> None:
    if surface.kind not in ("mud", "deep_mud", "water"):
        if state.mud_immersion > 0:
            state.mud_immersion = max(0.0, state.mud_immersion - dt * 0.04)
        return
    base = surface.water_depth
    rate = immersion_rate
    heavy_crawl = (
        rate < 1.0 and surface.kind in ("mud", "deep_mud") and (tire_name != "highway" or diff_lock)
    )
    imm_cap = (0.36 + 0.30 * rate) if heavy_crawl else 1.0

    if slip > 0.25 and v < 2.0:
        gain = dt * 0.018 * (1.0 + surface.viscosity / 5.0) * rate
        if heavy_crawl:
            gain *= max(0.05, 1.0 - state.mud_immersion / imm_cap)
        state.mud_immersion += gain
    elif v < 0.5:
        state.mud_immersion += dt * 0.008 * (surface.viscosity / 4.0) * rate
    elif v > 4.5 and slip < 0.2 and rate >= 0.85:
        state.mud_immersion -= dt * 0.025
    elif 2.0 <= v <= 4.5 and slip < 0.25 and rate >= 0.85:
        state.mud_immersion -= dt * 0.012
    # Class 8 + offroad: crawl sostenido sin despegarse del barro
    if heavy_crawl and 0.5 <= v <= 2.5:
        crawl_floor = base + 0.10 + 0.32 * (1.0 - rate)
        target = min(imm_cap, crawl_floor + min(0.12, slip * 0.12))
        if state.mud_immersion < target:
            state.mud_immersion += dt * 0.035 * (1.0 - rate * 0.45)
    state.mud_immersion = max(base, min(imm_cap, state.mud_immersion))


def step(
    state: SimState,
    vehicle: VehicleConfig,
    engine: EngineConfig,
    surface: SurfaceConfig,
    throttle: float,
    low_gear: bool,
    dt: float,
) -> tuple[float, float]:
    alpha = 1.0 - math.exp(-engine.responsiveness * 6.0 * dt)
    state.throttle_filt += alpha * (throttle - state.throttle_filt)

    engine_torque = engine.torque * state.throttle_filt * engine_torque_mult(engine)

    if surface.kind == "water" and surface.water_depth > 0.55 and not vehicle.snorkel:
        engine_torque *= max(0.1, 1.0 - surface.water_depth * 0.9)
    elif surface.kind == "water" and vehicle.snorkel:
        engine_torque *= 0.85

    gear_idx, gear_ang_vel = pick_gear(state.wheel_ang_vel, low_gear)
    state.gear_idx = gear_idx

    target_spin = gear_ang_vel * state.throttle_filt
    max_change = engine.max_delta_ang_vel * ANGVEL_RAMP * dt
    delta = max(-max_change, min(max_change, target_spin - state.wheel_ang_vel))
    state.wheel_ang_vel = max(0.0, state.wheel_ang_vel + delta)

    wheel_speed = state.wheel_ang_vel * VEL_PER_ANGVEL
    v = state.ground_speed

    wheel_mus = wheel_mu_per_axle(vehicle.tire, surface, state.mud_immersion, vehicle)
    if surface.kind == "water" and vehicle.snorkel:
        wheel_mus = [m * 3.2 for m in wheel_mus]
    mu_avg = _traction_mu(vehicle, wheel_mus)
    diff_eff = diff_efficiency(vehicle, surface, wheel_mus)

    slip = max(0.0, wheel_speed - v) / max(wheel_speed, 0.3)
    state.slip_ratio = slip
    slip_factor = slip_traction_factor(slip, surface)

    mass = total_mass_kg(vehicle)
    normal = mass * G * 0.85
    drive_raw = engine_torque * TORQUE_SCALE / WHEEL_RADIUS
    traction_limit = mu_avg * normal * slip_factor
    if surface.kind in ("mud", "deep_mud", "snow") and not vehicle.diff_lock:
        drive_cap = drive_raw * diff_eff
    elif vehicle.drive_layout == "rwd" and not vehicle.diff_lock:
        drive_cap = drive_raw * diff_eff
    else:
        drive_cap = drive_raw
    drive_force = min(drive_cap, traction_limit)
    state.traction_used = drive_force

    grade = mass * G * math.sin(math.atan(surface.grade_pct / 100))
    roll = mass * G * 0.012
    sink = (state.mud_immersion**1.4) * mass * G * 0.11
    if surface.kind == "deep_mud":
        sink += 0.08 * mass * G * state.mud_immersion
    if surface.kind == "water" and vehicle.snorkel:
        sink *= 0.3

    update_mud_immersion(
        state,
        surface,
        slip,
        v,
        dt,
        vehicle.mud_immersion_rate,
        vehicle.tire_name,
        vehicle.diff_lock,
    )

    net = drive_force - roll - grade - sink
    if vehicle.trailer_mass_kg > 0:
        trailer_mass = vehicle.trailer_mass_kg + vehicle.trailer_cargo_mass_kg
        roll += trailer_mass * G * TRAILER_ROLL_COEF
        net -= trailer_mass * G * TRAILER_HITCH_DRAG * (1.0 + v * 0.15)
    if surface.kind in ("mud", "deep_mud", "water"):
        mud_k = MUD_RESIST_COEF.get(vehicle.tire_name, 6.0) * vehicle.mud_resist_mult
        if surface.kind == "water" and vehicle.snorkel:
            mud_k *= 0.28
        depth = 1.0 + state.mud_immersion * 1.5
        if surface.kind == "deep_mud":
            depth *= 1.6
        net -= mass * mud_k * depth * (0.08 + v * 0.35) / 10.0
    if slip > 0.75 and surface.kind in ("asphalt", "gravel", "dirt"):
        net -= drive_raw * 0.2 * (slip - 0.75)

    net -= 0.42 * v * abs(v)

    v_new = max(0.0, v + (net / mass) * dt)
    if surface.kind == "ice":
        v_new = min(v_new, mu_avg * 8.0)
    if surface.kind in ("mud", "deep_mud") and state.mud_immersion > 0.55:
        v_new = min(v_new, mu_avg * (8.0 if vehicle.diff_lock else 5.5))

    coupling = min(1.0, drive_force / max(drive_raw, 1.0) + 0.15)
    target_wav = v_new / VEL_PER_ANGVEL
    state.wheel_ang_vel += coupling * 3.5 * dt * (target_wav - state.wheel_ang_vel)
    state.wheel_ang_vel = max(0.0, state.wheel_ang_vel)
    state.ground_speed = v_new

    gear_fuel_mod = GEARBOX.gears[gear_idx].fuel_mod if gear_idx >= 0 else 1.8
    if vehicle.diff_lock:
        gear_fuel_mod *= GEARBOX.awd_modifier
    fuel_mult = engine_fuel_mult(engine)
    slip_fuel = 1.0 + slip * 0.35
    fuel_line = (
        engine.fuel_consumption
        * GEARBOX.fuel_consumption
        * gear_fuel_mod
        * FUEL_UNIT_SCALE
        * fuel_mult
        * dt
    )
    throttle = max(0.0, min(1.0, state.throttle_filt))
    # Ralenti base + gas (incl. patinaje parado: throttle alto, v bajo)
    rev_boost = 1.0
    if v < 0.5 and throttle > 0.05:
        rev_boost = 1.0 + min(1.5, throttle * slip * 2.0)
    drive_frac = throttle * slip_fuel * rev_boost
    state.fuel_used += fuel_line * (IDLE_FUEL_FRAC + drive_frac * (1.0 - IDLE_FUEL_FRAC))

    return v_new, engine_torque


def run_sim(
    vehicle: VehicleConfig,
    engine: EngineConfig,
    surface: SurfaceConfig,
    duration_s: float = 60.0,
    low_gear: bool = False,
    dt: float = DT,
) -> SimSeries:
    state = SimState()
    if surface.kind in ("mud", "deep_mud"):
        state.mud_immersion = max(surface.water_depth, 0.08 if surface.kind == "mud" else 0.35)
    elif surface.kind == "water":
        state.mud_immersion = surface.water_depth * (0.45 if vehicle.snorkel else 1.0)

    times, speeds, slips, immersions = [], [], [], []
    steps = int(duration_s / dt)
    throttle_until = min(50.0, duration_s * 0.85)

    for i in range(steps):
        t = i * dt
        throttle = 1.0 if t < throttle_until else 0.0
        step(state, vehicle, engine, surface, throttle, low_gear, dt)
        times.append(t)
        speeds.append(state.ground_speed * 3.6)
        slips.append(state.slip_ratio)
        immersions.append(state.mud_immersion)

    return SimSeries(times, speeds, slips, immersions, state)


def time_to_kmh(speeds: list[float], times: list[float], target: float) -> float | None:
    for i, speed in enumerate(speeds):
        if speed < target:
            continue
        if i == 0:
            return round(times[0], 1)
        prev_s, prev_t = speeds[i - 1], times[i - 1]
        frac = (target - prev_s) / (speed - prev_s) if speed != prev_s else 1.0
        return round(prev_t + frac * (times[i] - prev_t), 1)
    return None


# --- Informes --------------------------------------------------------------


def run_tire_matrix(engine: EngineConfig = ENGINE_I6) -> list[dict]:
    rows: list[dict] = []
    veh = replace(VEHICLE_I6)
    for tire_name, tire in TIRES.items():
        veh.tire, veh.tire_name = tire, tire_name
        for surface in SURFACES:
            series = run_sim(veh, engine, surface, 45.0)
            rows.append(
                {
                    "tire": tire_name,
                    "surface": surface.name,
                    "v30_kmh": round(sample_at(series, 30.0), 1),
                    "slip30": round(sample_slip(series, 30.0), 2),
                    "immersion30": round(sample_immersion(series, 30.0), 2),
                }
            )
    return rows


def run_scenarios(engine: EngineConfig = ENGINE_I6) -> list[dict]:
    cases = [
        (
            "Barro highway sin diff",
            make_vehicle("highway"),
            SurfaceConfig("Barro", "mud", viscosity=4.0),
            True,
        ),
        (
            "Barro offroad sin diff",
            make_vehicle("offroad"),
            SurfaceConfig("Barro", "mud", viscosity=4.0),
            True,
        ),
        (
            "Barro offroad CON diff",
            make_vehicle("offroad", diff_lock=True),
            SurfaceConfig("Barro", "mud", viscosity=4.0),
            True,
        ),
        (
            "Barro prof. mudtires+diff",
            make_vehicle("mudtires", diff_lock=True),
            SurfaceConfig("Barro profundo", "deep_mud", viscosity=4.0, water_depth=0.4),
            True,
        ),
        (
            "Agua profunda sin snorkel",
            make_vehicle("offroad"),
            SurfaceConfig("Agua profunda", "water", water_depth=0.75),
            True,
        ),
        (
            "Agua profunda con snorkel",
            make_vehicle("offroad", snorkel=True),
            SurfaceConfig("Agua profunda", "water", water_depth=0.75),
            True,
        ),
    ]
    out: list[dict] = []
    for label, veh, surface, low_gear in cases:
        series = run_sim(veh, engine, surface, 60.0, low_gear=low_gear)
        out.append(
            {
                "label": label,
                "v30": round(sample_at(series, 30.0), 1),
                "v60": round(series.speeds_kmh[-1], 1),
                "max_slip": round(max(series.slips), 2),
                "max_immersion": round(max(series.immersions), 2),
                "fuel_l": round(series.state.fuel_used, 2),
            }
        )
    return out


def run_damage_test() -> dict:
    surface = SurfaceConfig("Tierra", "dirt", viscosity=3.0)
    veh = make_vehicle("offroad", diff_lock=True)
    ok = run_sim(veh, ENGINE_I6, surface, 40.0)
    bad = run_sim(veh, replace(ENGINE_I6, damage_pct=0.8), surface, 40.0)
    eng_bad = replace(ENGINE_I6, damage_pct=0.8)
    return {
        "motor_sano_v60": round(ok.speeds_kmh[-1], 1),
        "motor_danado_v60": round(bad.speeds_kmh[-1], 1),
        "motor_danado_fuel": round(bad.state.fuel_used, 2),
        "torque_mult_danado": round(engine_torque_mult(eng_bad), 2),
    }


# --- Carga y remolque (Fase 3) ---------------------------------------------


@dataclass(frozen=True)
class CargoItem:
    """Masa por unidad de carga (XML trucks/cargo/*.xml)."""

    id: str
    label: str
    slots: int
    mass_kg: float


CARGO_CATALOG: tuple[CargoItem, ...] = (
    CargoItem("wooden_planks_1", "Tablones madera (1 slot)", 1, 500),
    CargoItem("bricks_1", "Ladrillos (1 slot)", 1, 1000),
    CargoItem("metal_roll_1", "Rollo metal (1 slot)", 1, 1000),
    CargoItem("spare_parts_1", "Repuestos (1 slot)", 1, 1200),
    CargoItem("concrete_blocks_1", "Bloques hormigon (1 slot)", 1, 3000),
    CargoItem("metal_planks_2", "Vigas metal (2 slots)", 2, 2500),
    CargoItem("pipes_medium_2", "Tuberias medianas (2 slots)", 2, 2250),
    CargoItem("container_small_2", "Contenedor pequeno (2 slots)", 2, 1500),
    CargoItem("concrete_slab_2", "Losas hormigon (2 slots)", 2, 3000),
)

SCOUT_TRAILER_OFFROAD_CARGO_KG = 800
CK1500_ADDONS_TYPICAL_KG = 220  # rooftop trunk 200 + snorkel 20


@dataclass(frozen=True)
class LoadScenario:
    id: str
    label: str
    addon_mass_kg: float = 0.0
    cargo_mass_kg: float = 0.0
    trailer_mass_kg: float = 0.0
    trailer_cargo_mass_kg: float = 0.0


LOAD_SCENARIOS: tuple[LoadScenario, ...] = (
    LoadScenario("vacio", "Vacio"),
    LoadScenario("addons", "Addons tipicos (portaequipajes+snorkel)", CK1500_ADDONS_TYPICAL_KG),
    LoadScenario(
        "trailer_vacio", "Remolque scout vacio", trailer_mass_kg=SCOUT_TRAILER_OFFROAD_CARGO_KG
    ),
    LoadScenario(
        "trailer_bricks",
        "Remolque + ladrillos (1 slot)",
        trailer_mass_kg=SCOUT_TRAILER_OFFROAD_CARGO_KG,
        trailer_cargo_mass_kg=1000,
    ),
    LoadScenario(
        "trailer_spare_parts",
        "Remolque + repuestos (1 slot)",
        trailer_mass_kg=SCOUT_TRAILER_OFFROAD_CARGO_KG,
        trailer_cargo_mass_kg=1200,
    ),
    LoadScenario(
        "trailer_metal_planks",
        "Remolque + vigas metal (2 slots)",
        trailer_mass_kg=SCOUT_TRAILER_OFFROAD_CARGO_KG,
        trailer_cargo_mass_kg=2500,
    ),
    LoadScenario(
        "mision_pesada",
        "Mision pesada (addons + remolque + vigas)",
        CK1500_ADDONS_TYPICAL_KG,
        trailer_mass_kg=SCOUT_TRAILER_OFFROAD_CARGO_KG,
        trailer_cargo_mass_kg=2500,
    ),
    LoadScenario("semi_vacio", "Semirremolque vacio", trailer_mass_kg=2500),
    LoadScenario(
        "semi_cargado",
        "Semirremolque cargado (~12 t)",
        trailer_mass_kg=2500,
        trailer_cargo_mass_kg=12000,
    ),
    LoadScenario("semi_sideboard_vacio", "Semi sideboard vacio (~4.3 t)", trailer_mass_kg=4300),
    LoadScenario(
        "semi_sideboard_cargado",
        "Semi sideboard + 12 t util",
        trailer_mass_kg=4300,
        trailer_cargo_mass_kg=12000,
    ),
    LoadScenario("frame_cargado", "Bastidor Fleetstar + 6 t util", cargo_mass_kg=6000),
)

CARGO_TEST_SURFACES = (
    SurfaceConfig("Asfalto", "asphalt"),
    SurfaceConfig("Tierra", "dirt", viscosity=3.0),
    SurfaceConfig("Barro", "mud", viscosity=4.0),
    SurfaceConfig("Barro profundo", "deep_mud", viscosity=4.0, water_depth=0.4),
    SurfaceConfig("Cuesta 12%", "dirt", grade_pct=12.0, viscosity=3.0),
)


def apply_load(base: VehicleConfig, scenario: LoadScenario) -> VehicleConfig:
    return replace(
        base,
        label=f"{base.label} — {scenario.label}",
        addon_mass_kg=scenario.addon_mass_kg,
        cargo_mass_kg=scenario.cargo_mass_kg,
        trailer_mass_kg=scenario.trailer_mass_kg,
        trailer_cargo_mass_kg=scenario.trailer_cargo_mass_kg,
    )


@dataclass
class CargoSimCell:
    scenario_id: str
    scenario_label: str
    total_mass_kg: float
    tire: str
    diff_lock: bool
    surface: str
    v30_kmh: float
    v60_kmh: float
    max_slip: float
    max_immersion: float


def run_cargo_matrix(
    base: VehicleConfig | None = None,
    engine: EngineConfig = ENGINE_I6,
    scenarios: tuple[LoadScenario, ...] = LOAD_SCENARIOS,
    surfaces: tuple[SurfaceConfig, ...] = CARGO_TEST_SURFACES,
    tire_configs: tuple[tuple[str, bool], ...] = (("highway", False), ("offroad", True)),
    duration_s: float = 60.0,
) -> list[CargoSimCell]:
    chassis = base or VEHICLE_I6
    rows: list[CargoSimCell] = []
    for scenario in scenarios:
        for tire_name, diff_lock in tire_configs:
            veh = apply_load(
                replace(chassis, tire=TIRES[tire_name], tire_name=tire_name, diff_lock=diff_lock),
                scenario,
            )
            total = total_mass_kg(veh)
            for surface in surfaces:
                series = run_sim(
                    veh, engine, surface, duration_s, low_gear=surface.kind in ("mud", "deep_mud")
                )
                rows.append(
                    CargoSimCell(
                        scenario_id=scenario.id,
                        scenario_label=scenario.label,
                        total_mass_kg=total,
                        tire=tire_name,
                        diff_lock=diff_lock,
                        surface=surface.name,
                        v30_kmh=round(sample_at(series, 30.0), 1),
                        v60_kmh=round(series.speeds_kmh[-1], 1),
                        max_slip=round(max(series.slips), 2),
                        max_immersion=round(max(series.immersions), 2),
                    )
                )
    return rows


def summarize_cargo_vs_empty(matrix: list[CargoSimCell]) -> dict:
    """Compara cada escenario cargado contra vacio (misma superficie/neumatico)."""
    empty = {(r.tire, r.diff_lock, r.surface): r for r in matrix if r.scenario_id == "vacio"}
    deltas: list[dict] = []
    for row in matrix:
        if row.scenario_id == "vacio":
            continue
        base = empty.get((row.tire, row.diff_lock, row.surface))
        if not base:
            continue
        deltas.append(
            {
                "scenario": row.scenario_id,
                "tire": row.tire,
                "diff_lock": row.diff_lock,
                "surface": row.surface,
                "total_mass_kg": row.total_mass_kg,
                "empty_v30": base.v30_kmh,
                "loaded_v30": row.v30_kmh,
                "delta_v30": round(row.v30_kmh - base.v30_kmh, 1),
                "empty_v60": base.v60_kmh,
                "loaded_v60": row.v60_kmh,
                "delta_v60": round(row.v60_kmh - base.v60_kmh, 1),
            }
        )
    return {"deltas": deltas}


# --- Terreno (Fase 4) -------------------------------------------------------


@dataclass(frozen=True)
class TerrainGameFactors:
    """Como SnowRunner modela cada tipo (motor Saber + mapa)."""

    extrudable: bool
    uses_substance_friction: bool
    map_layers: str
    patchable_per_truck: bool


@dataclass(frozen=True)
class RealSpeedBand:
    """Rango historico K10 4x4 ~1971 (km/h sostenidos, barro = marcha baja)."""

    stock_min: float
    stock_max: float
    equipped_min: float
    equipped_max: float
    equipped_note: str


TERRAIN_GAME: dict[str, TerrainGameFactors] = {
    "asphalt": TerrainGameFactors(False, False, "Superficie rigida", False),
    "dirt": TerrainGameFactors(True, False, "Viscosidad base + tint + humedad", False),
    "gravel": TerrainGameFactors(True, False, "BodyFriction neumatico", False),
    "mud": TerrainGameFactors(True, True, "SubstanceFriction + deformacion", False),
    "deep_mud": TerrainGameFactors(True, True, "Substance + extrusion + humedad", False),
    "snow": TerrainGameFactors(True, True, "Profundidad nieve + substance", False),
    "ice": TerrainGameFactors(False, False, "Friccion baja; cadenas ignoran hielo", False),
    "water": TerrainGameFactors(True, True, "Profundidad + flujo + snorkel", False),
}

# Clave = SurfaceConfig.name
REAL_K10_BANDS: dict[str, RealSpeedBand] = {
    "Asfalto": RealSpeedBand(70, 110, 70, 110, "Carretera / firme"),
    "Tierra": RealSpeedBand(35, 65, 45, 75, "Camino rural compactado"),
    "Grava": RealSpeedBand(25, 55, 35, 65, "Ripio / shoulder"),
    "Barro": RealSpeedBand(5, 15, 15, 40, "Barro ligero-medio; stock bias-ply"),
    "Barro profundo": RealSpeedBand(0, 5, 5, 20, "Atasco probable sin preparacion"),
    "Nieve": RealSpeedBand(10, 30, 25, 50, "Nieve suelta; M&S o cadenas"),
    "Hielo": RealSpeedBand(5, 15, 20, 40, "Cadenas o neumatico M&S"),
    "Agua poco prof.": RealSpeedBand(5, 20, 10, 25, "Vado; sin snorkel limitado"),
    "Agua profunda": RealSpeedBand(0, 5, 0, 10, "Inundacion; snorkel o vado corto"),
}

TERRAIN_AUDIT_TIRES: tuple[tuple[str, bool], ...] = (
    ("highway", False),
    ("offroad", True),
    ("mudtires", True),
    ("chains", False),
)


@dataclass
class TerrainAuditCell:
    surface: str
    kind: str
    tire: str
    diff_lock: bool
    v30_kmh: float
    v45_kmh: float
    start_mu: float
    realism: str
    real_band: str
    game_factors: str


def _terrain_realism_verdict(
    surface_name: str,
    tire: str,
    v30: float,
    surface_kind: str = "",
) -> tuple[str, str]:
    band = REAL_K10_BANDS.get(surface_name)
    if not band:
        return "n/a", "—"
    lo, hi = (
        (band.stock_min, band.stock_max)
        if tire == "highway"
        else (band.equipped_min, band.equipped_max)
    )
    band_txt = f"{lo:.0f}–{hi:.0f} km/h"
    if surface_kind in ("asphalt", "dirt", "gravel") and v30 >= 40:
        return "ok", f"firme (>{lo:.0f} esperado)"
    if lo <= v30 <= hi:
        return "ok", band_txt
    if v30 < lo:
        return "game_harder", band_txt
    return "game_softer", band_txt


def run_terrain_audit(
    surfaces: tuple[SurfaceConfig, ...] | None = None,
    engine: EngineConfig = ENGINE_I6,
    vehicle_base: VehicleConfig | None = None,
    tire_configs: tuple[tuple[str, bool], ...] = TERRAIN_AUDIT_TIRES,
    duration_s: float = 45.0,
) -> list[TerrainAuditCell]:
    base = vehicle_base or VEHICLE_I6
    surf_list = surfaces or tuple(SURFACES)
    rows: list[TerrainAuditCell] = []
    for surface in surf_list:
        gf = TERRAIN_GAME.get(surface.kind)
        gf_txt = gf.map_layers if gf else surface.kind
        low = surface.kind in ("mud", "deep_mud")
        for tire_name, diff_lock in tire_configs:
            if surface.kind == "ice" and tire_name not in ("highway", "chains"):
                continue
            if surface.kind != "ice" and tire_name == "chains":
                continue
            veh = replace(
                base,
                tire=TIRES[tire_name],
                tire_name=tire_name,
                diff_lock=diff_lock,
            )
            series = run_sim(veh, engine, surface, duration_s, low_gear=low)
            v30 = round(sample_at(series, 30.0), 1)
            start_mu = round(surface_mu(veh.tire, surface, series.immersions[0]), 3)
            realism, band_txt = _terrain_realism_verdict(surface.name, tire_name, v30, surface.kind)
            rows.append(
                TerrainAuditCell(
                    surface=surface.name,
                    kind=surface.kind,
                    tire=tire_name,
                    diff_lock=diff_lock,
                    v30_kmh=v30,
                    v45_kmh=round(series.speeds_kmh[-1], 1),
                    start_mu=start_mu,
                    realism=realism,
                    real_band=band_txt,
                    game_factors=gf_txt,
                )
            )
    return rows


def summarize_terrain_audit(cells: list[TerrainAuditCell]) -> dict:
    by_verdict: dict[str, int] = {}
    gaps: list[dict] = []
    highlights: list[dict] = []
    for c in cells:
        by_verdict[c.realism] = by_verdict.get(c.realism, 0) + 1
        row = {
            "surface": c.surface,
            "tire": c.tire,
            "diff_lock": c.diff_lock,
            "v30_kmh": c.v30_kmh,
            "realism": c.realism,
            "real_band": c.real_band,
        }
        if c.realism in ("game_harder", "game_softer"):
            gaps.append(row)
        if c.tire in ("highway", "offroad") and c.surface in (
            "Barro",
            "Asfalto",
            "Nieve",
            "Hielo",
            "Tierra",
        ):
            highlights.append(row)
    return {
        "by_verdict": by_verdict,
        "gaps": gaps,
        "highlights": highlights,
        "patchable_terrain_xml": False,
        "ck1500_terrain_patches": [],
    }


def run_config_comparison(surface: SurfaceConfig | None = None) -> list[dict]:
    sf = surface or SurfaceConfig("Asfalto", "asphalt")
    rows: list[dict] = []
    for veh, eng in CONFIGS:
        series = run_sim(veh, eng, sf, 80.0)
        rows.append(
            {
                "vehicle": veh.label,
                "engine": eng.name,
                "t097_s": time_to_kmh(series.speeds_kmh, series.times, 97.0),
                "v60_kmh": round(sample_at(series, 60.0), 1),
            }
        )
    return rows


def print_report(results: dict, accel_series: SimSeries, t097_i6: float | None) -> None:
    print("=== MATRIZ NEUMATICO x TERRENO (v30, slip, immersion) ===\n")
    for tire in TIRES:
        print(f"\n--- {tire} ---")
        for row in results["matrix"]:
            if row["tire"] != tire:
                continue
            print(
                f"  {row['surface']:<18} {row['v30_kmh']:>6} km/h  "
                f"slip={row['slip30']:.2f}  hund={row['immersion30']:.2f}"
            )

    print("\n=== COMPARATIVA CONFIGS (asfalto, highway) ===\n")
    print(f"{'Vehiculo':<28} {'Motor':<18} {'0-97':>8} {'v60':>8}")
    print("-" * 66)
    for row in results["configs"]:
        row_t097 = row["t097_s"]
        t097_s = f"{row_t097}s" if row_t097 is not None else "—"
        print(f"{row['vehicle']:<28} {row['engine']:<18} {t097_s:>8} {row['v60_kmh']:>7} km/h")

    print("\n=== ESCENARIOS AVANZADOS (60s, marcha baja) ===\n")
    print(f"{'Escenario':<30} {'v30':>6} {'v60':>6} {'slip':>6} {'hund':>6} {'fuel':>6}")
    print("-" * 68)
    for s in results["scenarios"]:
        print(
            f"{s['label']:<30} {s['v30']:>5} {s['v60']:>5} "
            f"{s['max_slip']:>6} {s['max_immersion']:>6} {s['fuel_l']:>6}"
        )

    adv = results["advanced"][0]
    print("\n=== DANO MOTOR (tierra, offroad+diff) ===")
    print(f"  Sano v60: {adv['motor_sano_v60']} km/h | Danado v60: {adv['motor_danado_v60']} km/h")
    print(
        f"  Torque mult danado: {adv['torque_mult_danado']} | Fuel extra: {adv['motor_danado_fuel']} L"
    )

    print("\n=== ACELERACION I6 REALISTA (asfalto, highway) ===")
    print(f"  0-97 km/h: {t097_i6}s  |  v60: {round(sample_at(accel_series, 60.0), 1)} km/h")
    print(f"\nGuardado: {RESULTS_JSON}")


def main() -> None:
    accel = run_sim(VEHICLE_I6, ENGINE_I6, SurfaceConfig("Asfalto", "asphalt"), 80.0)
    t097 = time_to_kmh(accel.speeds_kmh, accel.times, 97.0)

    results = {
        "matrix": run_tire_matrix(),
        "configs": run_config_comparison(),
        "scenarios": run_scenarios(),
        "advanced": [run_damage_test()],
        "accel_097_s": t097,
    }

    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print_report(results, accel, t097)


if __name__ == "__main__":
    main()
