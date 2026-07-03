"""Registro central de vehiculos y utilidades de parches .pak."""

from __future__ import annotations

from dataclasses import dataclass

from camiones.ck1500.patches import PATCHES as CK1500_PATCHES
from camiones.fleetstar.patches import PATCHES as FLEETSTAR_PATCHES
from camiones.kodiak.patches import PATCHES as KODIAK_PATCHES
from camiones.marshall.patches import PATCHES as MARSHALL_PATCHES
from camiones.mh9500.patches import PATCHES as MH9500_PATCHES
from camiones.scout800.patches import PATCHES as SCOUT800_PATCHES

PatchRules = dict[str, list[tuple[str, str]]]

__all__ = [
    "CK1500_PATCHES",
    "EMPTY_MASS_KG",
    "FLEETSTAR_PATCHES",
    "KODIAK_PATCHES",
    "MARSHALL_PATCHES",
    "MH9500_PATCHES",
    "SCOUT800_PATCHES",
    "PatchRules",
    "VEHICLES",
    "VehicleMod",
    "default_vehicle_ids",
    "empty_mass_kg",
    "merge_patches",
    "trailer_tare_kg",
    "vehicle_id_from_ce",
]


@dataclass(frozen=True)
class VehicleMod:
    id: str
    label: str
    game_id: str
    xml_file: str
    patches: PatchRules
    sim_module: str
    ce_id: str
    notes: str = ""


VEHICLES: dict[str, VehicleMod] = {
    "ck1500": VehicleMod(
        id="ck1500",
        label="Chevrolet CK1500",
        game_id="s_chevrolet_ck1500",
        xml_file="chevrolet_ck1500.xml",
        patches=CK1500_PATCHES,
        sim_module="sim.core",
        ce_id="s_chevrolet_ck1500",
        notes="Scout 4x4 K10 ~1971",
    ),
    "mh9500": VehicleMod(
        id="mh9500",
        label="GMC MH9500",
        game_id="s_gmc_9500",
        xml_file="gmc_9500.xml",
        patches=MH9500_PATCHES,
        sim_module="camiones.mh9500.simulador",
        ce_id="s_gmc_9500",
        notes="Highway 6x4 diesel Class 8",
    ),
    "fleetstar": VehicleMod(
        id="fleetstar",
        label="Fleetstar F2070A",
        game_id="international_fleetstar_f2070a",
        xml_file="international_fleetstar_f2070a.xml",
        patches=FLEETSTAR_PATCHES,
        sim_module="camiones.fleetstar.simulador",
        ce_id="s_fleetstar_f2070a",
        notes="Heavy 6x4; Si-6V/1900; 42 UHD I",
    ),
    "marshall": VehicleMod(
        id="marshall",
        label="KHAN 39 Marshall",
        game_id="khan_39_marshall",
        xml_file="khan_39_marshall.xml",
        patches=MARSHALL_PATCHES,
        sim_module="camiones.marshall.simulador",
        ce_id="s_khan_39_marshall",
        notes="Scout UAZ/TREKOL; Kr 104; 45 TM II; AWD+diff",
    ),
    "kodiak": VehicleMod(
        id="kodiak",
        label="Chevrolet Kodiak C70",
        game_id="chevrolet_kodiakc70",
        xml_file="chevrolet_kodiakc70.xml",
        patches=KODIAK_PATCHES,
        sim_module="camiones.kodiak.simulador",
        ce_id="s_chevrolet_kodiakc70",
        notes="HEAVY_DUTY 4x4; Si-6V; 39\" UHD I; ~7900 kg mod",
    ),
    "scout800": VehicleMod(
        id="scout800",
        label="International Scout 800",
        game_id="international_scout_800",
        xml_file="international_scout_800.xml",
        patches=SCOUT800_PATCHES,
        sim_module="camiones.scout800.simulador",
        ce_id="s_international_scout_800",
        notes="Scout 4x4 ~1960s; AAT-6V; diff Always; HS I 33\"",
    ),
}


def merge_patches(vehicle_ids: list[str]) -> PatchRules:
    merged: PatchRules = {}
    for vid in vehicle_ids:
        if vid not in VEHICLES:
            raise KeyError(f"Vehiculo desconocido: {vid!r}. Opciones: {list(VEHICLES)}")
        for arc, rules in VEHICLES[vid].patches.items():
            if arc in merged:
                merged[arc].extend(rules)
            else:
                merged[arc] = list(rules)
    return merged


def default_vehicle_ids() -> list[str]:
    return list(VEHICLES)


# Alias vistos en memoria Havok (builds distintas)
_CE_ID_ALIASES: dict[str, str] = {
    "s_gmc9500": "mh9500",
    "gmc_9500": "mh9500",
    "s_international_fleetstar_f2070a": "fleetstar",
    "s_fleetstar_f2070a": "fleetstar",
    "international_fleetstar_f2070a": "fleetstar",
    "khan_39_marshall": "marshall",
    "s_chevrolet_ck1500": "ck1500",
    "chevrolet_ck1500": "ck1500",
    "s_chevrolet_kodiakc70": "kodiak",
    "s_chevrolet_kodiakC70": "kodiak",
    "chevrolet_kodiakc70": "kodiak",
    "s_international_scout_800": "scout800",
    "international_scout_800": "scout800",
}


def vehicle_id_from_ce(game_id: str) -> str | None:
    """ID interno del juego (CE) -> id del mod (ck1500, mh9500, fleetstar, marshall)."""
    gid = (game_id or "").strip()
    if not gid:
        return None
    if gid in _CE_ID_ALIASES:
        return _CE_ID_ALIASES[gid]
    for vid, v in VEHICLES.items():
        if gid == v.ce_id or gid == v.game_id:
            return vid
    return None


# Masa vacia del mod (suma XML / sim) — baseline para payload desde Havok
EMPTY_MASS_KG: dict[str, float] = {
    "ck1500": 1750.0,
    "mh9500": 7500.0,
    "fleetstar": 6650.0,
    "marshall": 1780.0,
    "kodiak": 7900.0,
    "scout800": 2350.0,
}


def empty_mass_kg(vehicle_id: str | None) -> float | None:
    if not vehicle_id:
        return None
    return EMPTY_MASS_KG.get(vehicle_id)


def trailer_tare_kg(trailer_id: str) -> float:
    """Masa vacia estimada del remolque (catalogo sim)."""
    low = (trailer_id or "").lower()
    if any(tok in low for tok in ("semi", "sideboard", "lowboy", "logging")):
        return 2500.0
    if "fuel_tank" in low:
        return 1200.0
    if any(tok in low for tok in ("scout", "small", "caravan")):
        return 800.0
    return 1500.0
