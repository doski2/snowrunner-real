"""Compara sesiones de telemetria juego vs simulador (Fase 5).

Ejecutar:
  python comparar_telemetria.py
  python comparar_telemetria.py telemetria/sesiones/ce_*.json --export
  python comparar_telemetria.py --list
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from telemetria import (
    TELEMETRY_RESULTS_JSON,
    export_comparison_report,
    iter_session_json_paths,
    list_sessions,
    load_session,
    resolve_session_path,
)


def _print_segment_report(report: dict) -> None:
    print(f"\n--- {report['session_id']} ({report['vehicle_id']}) ---")
    counts = report.get("terrain_sample_counts", {})
    if counts:
        print("  Muestras por terreno:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    whole = report["whole_session"]
    print(
        f"  Sesion completa [{report.get('protocol_id_whole')}]: "
        f"MAE {whole['mae_kmh']} km/h | n={whole['sample_count']}"
    )
    if whole.get("game_v30_kmh") is not None:
        print(f"    v30 juego {whole['game_v30_kmh']} | v30 sim {whole.get('sim_v30_kmh')}")

    for seg in report.get("segments", []):
        print(
            f"\n  >> Tramo {seg['terrain_kind']} {seg['t_start']:.0f}-{seg['t_end']:.0f}s "
            f"({seg['protocol_id']}, {seg['surface']})"
        )
        print(
            f"     MAE {seg['mae_kmh']} km/h | muestras {seg['sample_count']} | "
            f"v30 juego {seg.get('game_v30_kmh')} | v30 sim {seg.get('sim_v30_kmh')}"
        )

    for sk in report.get("skipped_segments", []):
        print(f"\n  -- Omitido {sk['terrain_kind']} {sk['t_start']}-{sk['t_end']}s: {sk['reason']}")


def _print_calibration_summary(comparisons: list[dict]) -> None:
    mud_rows: list[tuple[str, str, float]] = []
    for cmp in comparisons:
        for seg in cmp.get("segments", []):
            if seg.get("compare_kind") == "mud" and seg.get("sample_count", 0) >= 12:
                mud_rows.append((cmp["session_id"], seg["protocol_id"], seg["mae_kmh"]))
    if not mud_rows:
        return
    print("\n=== RESUMEN CALIBRACION BARRO (MAE tramos mud >= 12s) ===")
    for sid, proto, mae in mud_rows:
        ok = "OK" if mae < 15.0 else "revisar"
        print(f"  {sid:<40} {proto:<22} MAE {mae:>5} km/h  [{ok}]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comparar telemetria juego vs sim")
    parser.add_argument("sessions", nargs="*", help="Rutas a JSON de sesion (vacio = todas)")
    parser.add_argument("--export", action="store_true", help="Guardar telemetria_comparacion.json")
    parser.add_argument("--list", action="store_true", help="Listar sesiones disponibles y salir")
    args = parser.parse_args(argv)

    paths = list_sessions()
    if args.list:
        if not paths:
            print("No hay sesiones en telemetria/sesiones/")
            return 1
        for path in paths:
            print(path)
        return 0

    selected = args.sessions or paths
    if not selected:
        print("No hay sesiones en telemetria/sesiones/")
        print("Graba una: grabar_telemetria.bat")
        return 1

    sessions = []
    for path in selected:
        resolved = resolve_session_path(path) if not os.path.isfile(path) else path
        if not resolved or not os.path.isfile(resolved):
            print(f"No encontrado: {path}")
            continue
        sessions.append(load_session(resolved))

    if not sessions:
        return 1

    print("=== COMPARACION JUEGO vs SIMULADOR (por tramos de terreno) ===\n")
    report = export_comparison_report(sessions)
    for cmp in report["comparisons"]:
        _print_segment_report(cmp)

    _print_calibration_summary(report["comparisons"])

    logs = report["game_logs"]
    print("\n=== GAME.LOG (errores mod, no fisica) ===")
    if logs.get("missing"):
        print(f"  Carpeta no encontrada: {logs['dir']}")
    else:
        print(f"  Errores recientes: {logs['error_count']} | Warnings: {logs['warning_count']}")
        for err in logs.get("recent_errors", []):
            print(f"    {err[:120]}")

    print("\n=== INTERPRETACION ===")
    print("  Usa MAE de tramos mud/hard (>=12s) para calibrar; ignore sesion completa si es mixta")
    print("  MAE < 15 km/h en barro: sim util")
    print("  Tramos mixed: omitidos - conducir mas tiempo en barro o firme puro")

    if args.export:
        with open(TELEMETRY_RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nExportado: {TELEMETRY_RESULTS_JSON}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
