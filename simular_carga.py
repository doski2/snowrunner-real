"""Informe comparativo: vacio vs carga y remolque (Fase 3).

Ejecutar:
  python simular_carga.py
  python -m unittest camiones.ck1500.test_simulacion_carga -v
"""

from __future__ import annotations

import json

from camiones.ck1500.test_simulacion_carga import export_cargo_study
from sim.core import CARGO_RESULTS_JSON, VEHICLE_I6

CHASSIS_KG = VEHICLE_I6.mass_kg


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===\n")


def main() -> int:
    data = export_cargo_study()
    with open(CARGO_RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _print_section("ESCENARIOS DE CARGA (masa total)")
    print(
        f"{'ID':<22} {'Chasis':>7} {'Addon':>7} {'Carga':>7} "
        f"{'Remolque':>9} {'Carga rem.':>11} {'TOTAL':>7}"
    )
    print("-" * 84)
    for s in data["scenarios"]:
        total = (
            CHASSIS_KG
            + s["addon_kg"]
            + s["cargo_kg"]
            + s["trailer_kg"]
            + s["trailer_cargo_kg"]
        )
        print(
            f"{s['id']:<22} {CHASSIS_KG:>7.0f} {s['addon_kg']:>7.0f} {s['cargo_kg']:>7.0f} "
            f"{s['trailer_kg']:>9.0f} {s['trailer_cargo_kg']:>11.0f} {total:>7.0f}"
        )

    _print_section("CATALOGO CARGA SCOUT (XML juego)")
    print(f"{'Tipo':<32} {'slots':>5} {'kg':>6}")
    print("-" * 48)
    for c in data["catalog"]:
        print(f"{c['label']:<32} {c['slots']:>5} {c['mass_kg']:>6}")

    _print_section("HIGHLIGHTS - offroad + diff lock (v30 km/h a 30 s)")
    print(f"{'Escenario':<22} {'Superficie':<16} {'v30':>6} {'masa':>7}")
    print("-" * 56)
    for r in data["highlights"]:
        print(
            f"{r['scenario_id']:<22} {r['surface']:<16} "
            f"{r['v30_kmh']:>6.1f} {r['total_mass_kg']:>7.0f}"
        )

    _print_section("DELTAS vs VACIO (muestra barro / offroad+diff)")
    deltas = [
        d
        for d in data["summary"]["deltas"]
        if d["surface"] == "Barro" and d["tire"] == "offroad" and d["diff_lock"]
    ]
    print(f"{'Escenario':<22} {'v30 vacio':>10} {'v30 carga':>10} {'delta':>8}")
    print("-" * 54)
    for d in deltas:
        print(
            f"{d['scenario']:<22} {d['empty_v30']:>10.1f} "
            f"{d['loaded_v30']:>10.1f} {d['delta_v30']:>8.1f}"
        )

    _print_section("CONCLUSION")
    print(
        f"  - Fase 1 fijo chasis {CHASSIS_KG:.0f} kg (vs 2200 juego). Carga va en remolque scout (~800 kg vacio).\n"
        "  - 1 slot tipico = 1000-1200 kg; 2 slots = 1500-2500 kg - por encima del payload real K10 (~750 kg).\n"
        "  - Mas masa = mas traccion (peso en ruedas) pero mas hundimiento y resistencia al barro.\n"
        "  - No se parchea XML de carga: el sim orienta tendencias; validar misiones pesadas en juego."
    )
    print(f"\nGuardado: {CARGO_RESULTS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
