"""Informe auditoria terreno: juego vs K10 real (Fase 4)."""

from __future__ import annotations

import json
import os

from sim.core import TERRAIN_RESULTS_JSON

from camiones.ck1500.test_simulacion_terreno import export_terrain_study

ROOT = os.path.dirname(os.path.abspath(__file__))


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===\n")


def main() -> None:
    data = export_terrain_study()
    with open(TERRAIN_RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _print_section("COMO MODELA SNOWRUNNER EL TERRENO")
    print("  Capas del mapa (no estan en initial.pak del camion):")
    print("  • Viscosidad base por tipo (hierba < tierra < arena)")
    print("  • Tint (mas oscuro = mas viscoso)")
    print("  • Wetness mask (humedad)")
    print("  • Extrusion oculta (barrizales, atajos dificiles)")
    print("  • Profundidad de nieve / agua pintada en editor")
    print("  Del camion solo importan BodyFriction / Asphalt / Substance (Fase 2).")

    _print_section("MATRIZ SIM I6 — v30 km/h a 30 s")
    print(
        f"{'Terreno':<18} {'Neumatico':<10} {'diff':>4} {'v30':>7} {'veredicto':<14} {'K10 real'}"
    )
    print("-" * 72)
    for r in data["audit"]:
        if r["tire"] not in ("highway", "offroad", "chains"):
            continue
        if r["surface"] == "Hielo" and r["tire"] == "offroad":
            continue
        print(
            f"{r['surface']:<18} {r['tire']:<10} {str(r['diff_lock']):>4} "
            f"{r['v30_kmh']:>7.1f} {r['realism']:<14} {r['real_band']}"
        )

    _print_section("HUECOS vs K10 REAL (game_harder / game_softer)")
    gaps = data["summary"]["gaps"]
    if not gaps:
        print("  Ninguno")
    else:
        for g in gaps:
            print(
                f"  {g['surface']:<16} {g['tire']:<10} "
                f"v30={g['v30_kmh']:>5.1f}  ({g['realism']})  banda {g['real_band']}"
            )

    _print_section("RESUMEN VEREDICTOS")
    for verdict, count in sorted(data["summary"]["by_verdict"].items()):
        print(f"  {verdict:<14} {count:>3} celdas")

    _print_section("DECISION FASE 4")
    print(
        "  • El terreno NO se parchea por vehiculo: vive en cada mapa (.pak de zona).\n"
        "  • Barro highway a 0 km/h = diseno del juego (mas duro que K10 stock en barro ligero).\n"
        "    Ya cubierto en Fase 2 (substance 0.4 -> 0.5 en highway_1).\n"
        "  • Nieve highway ~112 km/h en sim: mas rapido que K10 real en nieve suelta.\n"
        "    Aceptable como compromiso de juego; no hay XML de mapa que tocar desde mod CK1500.\n"
        "  • Barro profundo / agua profunda: atasco coherente; en real igualmente critico.\n"
        "  • Siguiente paso: validar en Michigan/Alaska las mismas superficies con mod I6."
    )
    print(f"\nGuardado: {TERRAIN_RESULTS_JSON}")


if __name__ == "__main__":
    main()
