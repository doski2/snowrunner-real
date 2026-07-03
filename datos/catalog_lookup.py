"""Referencias XML stock (catalogo Capa B) para metadatos de sesion CE."""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGO_DIR = os.path.join(ROOT, "datos", "catalogo")

# ce_id del registry -> id en suspensions.json
_SUSPENSION_SOCKET_ALIASES: dict[str, str] = {
    "s_gmc_9500": "s_gmc9500",
}


def _load_catalog(kind: str) -> dict:
    path = os.path.join(CATALOGO_DIR, f"{kind}.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get(kind, {})


def _engine_by_name(default_engine: str) -> dict | None:
    if not default_engine:
        return None
    engines = _load_catalog("engines")
    for eng in engines.values():
        name = eng.get("name") or ""
        if name == default_engine or default_engine in name:
            return eng
    return None


def _gearbox_by_name(default_gearbox: str) -> dict | None:
    if not default_gearbox:
        return None
    for gb in _load_catalog("gearboxes").values():
        if (gb.get("name") or "") == default_gearbox:
            return gb
    return None


def _gear_ang_vels(gearbox: dict) -> tuple[float | None, float | None]:
    """Primera marcha (Gear) y HighGear AngVel del XML stock."""
    first: float | None = None
    high: float | None = None
    for g in gearbox.get("gears") or []:
        kind = g.get("kind") or ""
        ang = g.get("ang_vel")
        if ang is None:
            continue
        if kind == "Gear" and first is None:
            first = float(ang)
        elif kind == "HighGear" and high is None:
            high = float(ang)
        if first is not None and high is not None:
            break
    return first, high


def _xml_bool(val: str | None) -> bool | None:
    if val is None or val == "":
        return None
    return val.lower() == "true"


def _suspension_socket_id(vehicle_mod_id: str) -> str:
    from camiones.registry import VEHICLES

    mod = VEHICLES.get(vehicle_mod_id)
    if not mod:
        return ""
    ce = mod.ce_id or ""
    return _SUSPENSION_SOCKET_ALIASES.get(ce, ce)


def _default_suspension_wheels(socket_id: str) -> tuple[dict | None, dict | None]:
    """Primera variante front/rear del archivo de suspension (stock default)."""
    if not socket_id:
        return None, None
    sus_file = _load_catalog("suspensions").get(socket_id)
    if not sus_file:
        return None, None
    front: dict | None = None
    rear: dict | None = None
    for entry in sus_file.get("suspensions", []):
        wt = entry.get("wheel_type")
        if wt == "front" and front is None:
            front = entry
        elif wt == "rear" and rear is None:
            rear = entry
        if front and rear:
            break
    return front, rear


def setup_xml_from_catalog(vehicle_mod_id: str) -> dict[str, float | str | bool]:
    """Campos XML stock para session_context.setup (initial.pak.bak, no mod parcheado).

    Incluye SteerSpeed, Responsiveness, suspensión Strength/Damping/Height,
    motor/caja default (sockets Type + variante resuelta en gearboxes.json).
    """
    if not vehicle_mod_id:
        return {}
    from camiones.registry import VEHICLES

    mod = VEHICLES.get(vehicle_mod_id)
    if not mod:
        return {}
    truck_id = mod.xml_file.removesuffix(".xml")
    truck = _load_catalog("trucks").get(truck_id)
    if not truck:
        return {}

    setup: dict[str, float | str] = {"catalog_source": "initial.pak.bak stock"}
    if truck.get("steer_speed") is not None:
        setup["steer_speed_xml"] = float(truck["steer_speed"])
    if truck.get("responsiveness") is not None:
        setup["responsiveness_xml"] = float(truck["responsiveness"])

    default_suspension = truck.get("default_suspension") or ""
    if default_suspension:
        setup["default_suspension_xml"] = default_suspension
    socket_id = _suspension_socket_id(vehicle_mod_id)
    if socket_id:
        setup["suspension_socket_xml"] = socket_id
    front, rear = _default_suspension_wheels(socket_id)
    if front and front.get("strength") is not None:
        setup["suspension_strength_front_xml"] = float(front["strength"])
    if rear and rear.get("strength") is not None:
        setup["suspension_strength_rear_xml"] = float(rear["strength"])
    if front and front.get("damping") is not None:
        setup["suspension_damping_front_xml"] = float(front["damping"])
    if rear and rear.get("damping") is not None:
        setup["suspension_damping_rear_xml"] = float(rear["damping"])
    if front and front.get("height") is not None:
        setup["suspension_height_front_xml"] = float(front["height"])
    if rear and rear.get("height") is not None:
        setup["suspension_height_rear_xml"] = float(rear["height"])

    engine_socket_type = truck.get("engine_socket_type") or ""
    if engine_socket_type:
        setup["engine_socket_type_xml"] = engine_socket_type
    default_engine = truck.get("default_engine") or ""
    if default_engine:
        setup["default_engine_xml"] = default_engine
    eng = _engine_by_name(default_engine)
    if eng and eng.get("engine_responsiveness") is not None:
        setup["engine_responsiveness_xml"] = float(eng["engine_responsiveness"])
    if eng and eng.get("name"):
        setup["engine_name_xml"] = eng["name"]

    gearbox_socket_type = truck.get("gearbox_socket_type") or ""
    if gearbox_socket_type:
        setup["gearbox_socket_type_xml"] = gearbox_socket_type
    default_gearbox = truck.get("default_gearbox") or ""
    if default_gearbox:
        setup["default_gearbox_xml"] = default_gearbox
    gb = _gearbox_by_name(default_gearbox)
    if gb:
        if gb.get("file_id"):
            setup["gearbox_file_id_xml"] = gb["file_id"]
        lower = _xml_bool(gb.get("is_lower_gear_exists"))
        if lower is not None:
            setup["gearbox_lower_gear_xml"] = lower
        high_exists = _xml_bool(gb.get("is_high_gear_exists"))
        if high_exists is not None:
            setup["gearbox_high_gear_xml"] = high_exists
        if gb.get("fuel_consumption") is not None:
            setup["gearbox_fuel_consumption_xml"] = float(gb["fuel_consumption"])
        first_ang, high_ang = _gear_ang_vels(gb)
        if first_ang is not None:
            setup["gearbox_first_gear_ang_vel_xml"] = first_ang
        if high_ang is not None:
            setup["gearbox_high_gear_ang_vel_xml"] = high_ang
    return setup


def truck_drive_catalog_hints(vehicle_mod_id: str) -> dict[str, str]:
    """Traccion/diff del XML stock (no estado runtime en marcha)."""
    if not vehicle_mod_id:
        return {}
    from camiones.registry import VEHICLES

    mod = VEHICLES.get(vehicle_mod_id)
    if not mod:
        return {}
    truck = _load_catalog("trucks").get(mod.xml_file.removesuffix(".xml"))
    if not truck:
        return {}
    hints: dict[str, str] = {}
    diff_type = (truck.get("diff_lock_type") or "").strip()
    if diff_type:
        hints["diff_lock_catalog"] = diff_type
    truck_type = (truck.get("truck_type") or "").strip()
    if truck_type:
        hints["truck_type_catalog"] = truck_type
    gb_name = truck.get("default_gearbox") or ""
    gb = _gearbox_by_name(gb_name)
    if gb:
        awd_mod = gb.get("awd_consumption_modifier")
        if awd_mod is not None:
            hints["gearbox_awd_modifier_xml"] = str(awd_mod)
        lower = _xml_bool(gb.get("is_lower_gear_exists"))
        high = _xml_bool(gb.get("is_high_gear_exists"))
        if lower is not None:
            hints["gearbox_lower_gear_xml"] = "yes" if lower else "no"
        if high is not None:
            hints["gearbox_high_gear_xml"] = "yes" if high else "no"
    return hints
