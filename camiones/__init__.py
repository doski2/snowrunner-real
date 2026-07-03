"""Paquete por camion: parches, simulador, tests y scripts en cada subcarpeta."""

from camiones.registry import (
    CK1500_PATCHES,
    FLEETSTAR_PATCHES,
    KODIAK_PATCHES,
    MARSHALL_PATCHES,
    MH9500_PATCHES,
    VEHICLES,
    PatchRules,
    VehicleMod,
    default_vehicle_ids,
    merge_patches,
)

__all__ = [
    "CK1500_PATCHES",
    "FLEETSTAR_PATCHES",
    "KODIAK_PATCHES",
    "MARSHALL_PATCHES",
    "MH9500_PATCHES",
    "VEHICLES",
    "PatchRules",
    "VehicleMod",
    "default_vehicle_ids",
    "merge_patches",
]
