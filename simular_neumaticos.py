"""Informe comparativo: parche global vs solo CK1500 (Fase 2 neumaticos).

Ejecutar:
  python simular_neumaticos.py
  python -m unittest camiones.ck1500.test_simulacion_neumaticos -v
"""

from __future__ import annotations

import json

from camiones.ck1500.test_simulacion_neumaticos import export_tire_study
from sim.core import TIRE_RESULTS_JSON


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===\n")


def main() -> int:
    data = export_tire_study()
    with open(TIRE_RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _print_section("ALCANCE: solo CK1500 vs global")
    s = data["summary"]
    print(
        f"Parche solo CK1500 - cambios en CK1500:     {len(s['ck1500_only_changes_on_ck1500'])} celdas"
    )
    print(
        f"Parche solo CK1500 - cambios en Scout gen.: {len(s['ck1500_only_changes_on_generic'])} celdas"
    )
    print(
        f"Plantilla global - cambios en Scout gen.:   {len(s['global_template_changes_on_generic'])} celdas"
    )
    print(
        f"Plantilla global - cambios en CK1500:       {len(s['global_template_changes_on_ck1500'])} celdas"
    )
    print(
        f"Buff global - cambios en CK1500:            {len(s['global_buff_changes_on_ck1500'])} celdas"
    )
    print(
        f"Buff global - cambios en Scout gen.:        {len(s['global_buff_changes_on_generic'])} celdas"
    )

    _print_section("BARRO + HIGHWAY (v30 km/h a 30 s)")
    print(f"{'Plan':<18} {'CK1500':>8} {'Scout gen.':>12} {'sub CK':>8} {'sub gen':>8}")
    print("-" * 58)
    for plan in ("factory", "ck1500_only", "global_template", "global_buff"):
        ck = next(
            r
            for r in data["highlight_mud_highway"]
            if r["plan_id"] == plan and r["scout_id"] == "ck1500"
        )
        gen = next(
            r
            for r in data["highlight_mud_highway"]
            if r["plan_id"] == plan and r["scout_id"] == "scout_generic"
        )
        print(
            f"{plan:<18} {ck['v30_kmh']:>8.1f} {gen['v30_kmh']:>12.1f} "
            f"{ck['substance']:>8.2f} {gen['substance']:>8.2f}"
        )

    _print_section("DELTAS CON mu > 0 (muestra)")
    for plan_key in ("ck1500_only", "global_template", "global_buff"):
        rows = data["nonzero_deltas"][plan_key]
        print(f"\n--- {plan_key} ({len(rows)} celdas) ---")
        for r in rows[:8]:
            print(
                f"  {r['scout']:<14} {r['tire']:<10} {r['surface']:<14} "
                f"v30 {r['base_v30']:>5} -> {r['target_v30']:>5}  "
                f"mu {r['base_mu']:.3f} -> {r['target_mu']:.3f}"
            )
        if len(rows) > 8:
            print(f"  ... +{len(rows) - 8} mas")

    _print_section("CONCLUSION")
    print(
        "  - Solo CK1500: solo cambia highway del CK1500; otros Scouts y tipos intactos.\n"
        "  - Plantilla global: afecta highway de Scouts genericos; CK1500 mantiene override 0.4.\n"
        "  - Buff global: cambia offroad/mudtires/chains en TODOS los Scouts.\n"
        "  - En barro, highway puede seguir a 0 km/h en sim (MUD_RESIST); mirar delta_mu y probar en juego."
    )
    print(f"\nGuardado: {TIRE_RESULTS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
