"""CLI: aplica mod realista a uno o varios vehiculos."""

from __future__ import annotations

import argparse

from repack_pak import apply_mod, set_active_vehicles
from camiones.registry import VEHICLES


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplicar mod SnowRunner realista")
    parser.add_argument(
        "--vehicle",
        action="append",
        dest="vehicles",
        metavar="ID",
        help=f"ID vehiculo ({', '.join(VEHICLES)}). Repetible. Default: todos",
    )
    parser.add_argument("--list", action="store_true", help="Listar vehiculos")
    parser.add_argument(
        "--refresh-backup",
        action="store_true",
        help="Tras update Steam: copiar initial.pak oficial al backup y reparchear",
    )
    args = parser.parse_args()

    if args.list:
        for v in VEHICLES.values():
            print(f"  {v.id:<10} {v.label:<22} {v.xml_file}  ({v.notes})")
        return

    ids = args.vehicles or list(VEHICLES)
    set_active_vehicles(ids)
    print(f"Vehiculos: {', '.join(ids)}")
    apply_mod(refresh=args.refresh_backup)


if __name__ == "__main__":
    main()
