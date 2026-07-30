"""Compara masa/torque del mod (patches + registry) vs referencia documentada."""

from __future__ import annotations

import re
from dataclasses import dataclass

from camiones.registry import EMPTY_MASS_KG, VEHICLES

# Referencia histórica / TE (kg vacío) — ver camiones/*/FASES.md
REFERENCIA_KG: dict[str, tuple[float, float | None, str]] = {
    # (objetivo kg, te_kg opcional, nota)
    "ck1500": (1750, 1750, "K10 ~1971"),
    "marshall": (2030, 2380, "UAZ-469 TE"),
    "scout800": (2100, 2000, "Scout 800 ~1800–2200"),
    "bandit": (7600, 12000, "KrAZ TE ~11–13 t (6×6)"),
    "fleetstar": (7400, 8200, "F2070 civil ~8200"),
    "kodiak": (8150, None, "SR!NFO 8201; Class 7"),
    "mh9500": (8200, None, "SR!NFO 8438; Class 8"),
    "t813": (14000, 13800, "Tatra 813 TE"),
}

TORQUE_MOD: dict[str, tuple[str, int, int]] = {
    "bandit": ("ru_truck_old_engine_0", 130000, 88500),
    "fleetstar": ("us_truck_old_engine_0", 135000, 92000),
    "kodiak": ("us_truck_old_engine_0", 135000, 92000),
    "mh9500": ("gmc9500", 140000, 95000),
    "t813": ("ru_special_engine_1", 230000, 157000),
    "ck1500": ("us_scout_old_engine_ck1500", 62000, 40000),
    "marshall": ("ru_scout_old_engine_0", 30000, 28000),
    "scout800": ("us_scout_old_engine_0", 35000, 32000),
}


@dataclass
class MassRow:
    vid: str
    registry_kg: float
    patch_sum_kg: float | None
    ref_obj_kg: float
    ref_te_kg: float | None
    delta_pct: float | None


def patch_truck_mass_sum(vehicle_id: str) -> float | None:
    patches = VEHICLES[vehicle_id].patches
    total = 0.0
    found = False
    for arc, rules in patches.items():
        if "/trucks/" not in arc:
            continue
        for _old, new in rules:
            for m in re.findall(r'(?<!<Body )Mass="(\d+)"', new):
                total += int(m)
                found = True
            for m in re.findall(r'<Body Mass="(\d+)"', new):
                total += int(m)
                found = True
    return total if found else None


def main() -> None:
    print("=== Masa vacía: registry vs patches vs referencia ===\n")
    for vid in VEHICLES:
        reg = EMPTY_MASS_KG.get(vid)
        ps = patch_truck_mass_sum(vid)
        ref = REFERENCIA_KG.get(vid)
        if not ref or reg is None:
            continue
        obj, te, note = ref
        delta = ((reg - obj) / obj * 100) if obj else None
        te_str = f"{te:.0f}" if te else "-"
        ps_str = f"{ps:.0f}" if ps else "-"
        mismatch = ""
        if ps and abs(ps - reg) > 50:
            mismatch = f"  WARN registry!=patches ({ps:.0f} vs {reg:.0f})"
        print(
            f"{vid:10} registry={reg:.0f}  patches~{ps_str}  "
            f"obj={obj:.0f}  TE={te_str}  ({note}){mismatch}"
        )

    print("\n=== Torque motor principal (Ncm) ===\n")
    for vid, (name, stock, mod) in TORQUE_MOD.items():
        ratio = mod / stock * 100
        print(f"{vid:10} {name}: {stock} -> {mod} ({ratio:.0f}%)")


if __name__ == "__main__":
    main()
