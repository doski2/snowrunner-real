"""Graba telemetria manual desde el HUD (respaldo sin Havok).

Flujo principal: grabar_telemetria.bat -> grabar_ce.py (memoria, --auto).
Usa este script si CE no lee o quieres anotar velocidad a mano cada N segundos.

Ejecutar:
  python grabar_telemetria.py --list
  python grabar_telemetria.py --protocol fs_f2_barro_uhd --map Michigan
"""

from __future__ import annotations

import argparse
import sys

from telemetria import (
    TEST_PROTOCOLS,
    TestProtocol,
    meta_from_protocol,
    record_manual_interactive,
    save_session,
)


def _print_protocols() -> None:
    print("\nProtocolos (ck1500, mh9500, fleetstar, marshall):\n")
    for i, p in enumerate(TEST_PROTOCOLS, 1):
        print(f"  {i}. [{p.id}] {p.label} ({p.vehicle_id})")
        print(f"     {p.hint}\n")


def _pick_protocol(args: argparse.Namespace) -> TestProtocol | None:
    if args.protocol:
        protocol = next((p for p in TEST_PROTOCOLS if p.id == args.protocol), None)
        if not protocol:
            print(f"Protocolo desconocido: {args.protocol}")
            return None
        return protocol

    _print_protocols()
    try:
        choice = int(input("Elige numero de protocolo: ").strip())
        return TEST_PROTOCOLS[choice - 1]
    except (ValueError, IndexError, EOFError):
        print("Protocolo invalido.")
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Grabar telemetria manual (HUD) — respaldo de grabar_ce.py"
    )
    parser.add_argument("--list", action="store_true", help="Listar protocolos y salir")
    parser.add_argument("--protocol", type=str, help="ID del protocolo (ej. mh_f2_barro_offroad)")
    parser.add_argument("--map", type=str, default="", help="Nombre del mapa (ej. Michigan)")
    parser.add_argument("--location", type=str, default="", help="Ubicacion / ruta en el mapa")
    parser.add_argument("--interval", type=float, default=5.0, help="Segundos entre muestras")
    parser.add_argument("--notes", type=str, default="", help="Notas libres")
    args = parser.parse_args(argv)

    if args.list:
        _print_protocols()
        return 0

    protocol = _pick_protocol(args)
    if not protocol:
        return 1

    print(f"\n=== GRABACION MANUAL ({protocol.vehicle_id}) ===")
    print(f"Protocolo: {protocol.id} — {protocol.label}")
    print("1. Mod aplicado: python apply_mod.py")
    print("2. Configura el camion segun el protocolo (neumaticos, diff, carga)")
    print("3. Lee velocidad del HUD cuando lo pida el script")
    print("4. Misma ruta si comparas con otra sesion")
    print("\nPreferible: grabar_telemetria.bat (Havok, mas muestras y terreno por rueda)\n")
    try:
        input("Pulsa Enter cuando estes listo en juego...")
    except EOFError:
        print("Cancelado.")
        return 1

    meta = meta_from_protocol(protocol, args.map, args.location, args.notes)
    session = record_manual_interactive(meta, interval_s=args.interval)
    if not session.samples:
        print("Sin muestras — sesion no guardada.")
        return 1

    path = save_session(session)
    print(f"\nGuardado: {path}")
    print(f"Muestras: {len(session.samples)}")
    print(f'Comparar: python comparar_telemetria.py "{path}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
