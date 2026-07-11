"""Importa TODAS las hojas comunitarias (Google Sheets) a datos/comunidad/*.json.

Fuentes:
  - USDS (Vlad Vulcan): trucks, engines, gearboxes, tires, cargo, trailers, addons...
  - SR!NFO: trucks, engines, gearboxes, wheels, addons, trailers, cargo, colors
  - SnowRunner Extras: truck list, addons, tires, DLC, missions...

Uso:
  python datos/importar_comunidad.py
  python datos/importar_comunidad.py --fetch
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "datos", "raw", "comunidad")
OUT_DIR = os.path.join(ROOT, "datos", "comunidad")

USDS_ID = "1_dNNE91snTCbY34YhWtG6mAK-GyCBTx4sIa9Ik9_Kjs"
SRINFO_ID = "1TPla-u2zxpzFMhpxzymhwzxDU_x85Y_1SxylgRPonH0"
EXTRAS_ID = "13e5VlopEefAsh5N9G1a9HFKpxxORTHPnzJC7CC6Blvw"

# sheet_name → config
SHEET_CATALOG: list[dict[str, Any]] = [
    # --- USDS ---
    *[
        {"book": "usds", "id": f"usds_{k}", "sheet": s, "parser": "table", "title": f"USDS — {s}"}
        for k, s in [
            ("trucks", "Trucks"),
            ("trucks_ru", "Trucks (RU)"),
            ("trucks_region", "Trucks per Region"),
            ("tires", "Tires"),
            ("engines", "Engines"),
            ("gearboxes", "Gearboxes"),
            ("cargo", "Cargo"),
            ("trailers", "Trailers"),
            ("addons", "Addons"),
            ("trucks2", "Trucks2"),
        ]
    ],
    # --- SR!NFO ---
    {"book": "srinfo", "id": "srinfo_trucks", "sheet": "Trucks", "parser": "table", "title": "SR!NFO — Trucks"},
    {"book": "srinfo", "id": "srinfo_engines", "sheet": "Engines", "parser": "table", "title": "SR!NFO — Engines"},
    {"book": "srinfo", "id": "srinfo_gearboxes", "sheet": "Gearboxes", "parser": "table", "title": "SR!NFO — Gearboxes"},
    {"book": "srinfo", "id": "srinfo_wheels", "sheet": "Wheels", "parser": "wheels", "title": "SR!NFO — Wheels"},
    {"book": "srinfo", "id": "srinfo_addons", "sheet": "Addons", "parser": "table", "title": "SR!NFO — Addons"},
    {"book": "srinfo", "id": "srinfo_trailers", "sheet": "Trailers", "parser": "table", "title": "SR!NFO — Trailers"},
    {"book": "srinfo", "id": "srinfo_cargo", "sheet": "Cargo", "parser": "cargo", "title": "SR!NFO — Cargo"},
    {"book": "srinfo", "id": "srinfo_colors", "sheet": "Color Codes", "parser": "truck_colors", "title": "SR!NFO — Color Codes"},
    # --- SnowRunner Extras ---
    *[
        {"book": "extras", "id": f"extras_{k}", "sheet": s, "parser": p, "title": f"SnowRunner Extras — {s}"}
        for k, s, p in [
            ("truck_list", "Truck List", "table"),
            ("addons", "Addons", "table"),
            ("addons2", "Addons 2", "table"),
            ("gearboxes", "Gearboxes", "table"),
            ("tires", "Tires", "table"),
            ("trailers_winches", "Trailers & Winches", "table"),
            ("cargo", "Cargo", "table"),
            ("vehicles_find", "Vehicles To Find", "table"),
            ("missions", "Missions and Payments", "table"),
            ("dlc_trucks", "DLC Trucks", "table"),
            ("dlc_releases", "DLC Releases", "table"),
            ("addon_colors", "Addon Color Matching", "addon_colors"),
            ("gas_tanks", "Gas Tank Volumes", "table"),
            ("jat_issues", "JAT Issue List", "table"),
            ("engines_wip", "Engines (WIP)", "table"),
        ]
    ],
]

BOOK_META = {
    "usds": {
        "spreadsheet_id": USDS_ID,
        "name": "USDS (Vlad Vulcan)",
        "url": f"https://docs.google.com/spreadsheets/d/{USDS_ID}/edit",
    },
    "srinfo": {
        "spreadsheet_id": SRINFO_ID,
        "name": "SR!NFO",
        "url": f"https://docs.google.com/spreadsheets/d/{SRINFO_ID}/edit",
    },
    "extras": {
        "spreadsheet_id": EXTRAS_ID,
        "name": "SnowRunner Extras",
        "url": f"https://docs.google.com/spreadsheets/d/{EXTRAS_ID}/edit",
    },
}


def _csv_name(entry: dict[str, Any]) -> str:
    return f"{entry['id']}.csv"


def _export_url(book: str, sheet: str) -> str:
    sid = BOOK_META[book]["spreadsheet_id"]
    q = urllib.parse.quote(sheet)
    return f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={q}"


def _sheet_url(book: str, sheet: str) -> str:
    return f"{BOOK_META[book]['url']}?gid=auto&sheet={urllib.parse.quote(sheet)}"


def _parse_num(raw: str | None) -> int | float | None:
    if raw is None:
        return None
    s = str(raw).strip().replace("\u00a0", " ").replace(" ", "")
    if not s or s in ("-", "—", "N/A", "n/a"):
        return None
    s = s.replace(",", ".").lstrip("$€")
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return None


def _parse_slots(raw: str | None) -> str | int | None:
    if not raw:
        return None
    s = raw.strip()
    if s in ("L", "M", "S"):
        return s
    n = _parse_num(s)
    return int(n) if n is not None else s


def _read_csv(path: str) -> list[list[str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def _clean_header(cell: str) -> str:
    s = cell.strip().replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    # USDS row0: "English ... Make and Model" → keep tail label
    if "Make and Model" in s and s.index("Make and Model") > 0:
        s = s[s.index("Make and Model") :]
    return s[:120] if s else "col"


def _row_fill_count(row: list[str]) -> int:
    return sum(1 for c in row if c.strip())


def _is_banner_row(row: list[str]) -> bool:
    if not row:
        return True
    first = (row[0] or "").strip()
    if not first:
        return _row_fill_count(row) <= 1
    low = first.lower()
    if "last updated" in low or "season " in low and _row_fill_count(row) <= 2:
        return True
    if low.startswith("support my work") or low.startswith("english season"):
        return True
    if "ko-fi.com" in low or "paypal" in low:
        return True
    return False


def parse_table(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Tabla genérica: detecta cabecera y filas de datos."""
    if not rows:
        return []
    header_idx = 0
    for i, row in enumerate(rows[:20]):
        if _is_banner_row(row):
            continue
        if _row_fill_count(row) >= 3:
            header_idx = i
            break
    headers = [_clean_header(c) for c in rows[header_idx]]
    # dedupe headers
    seen: dict[str, int] = {}
    uniq: list[str] = []
    for h in headers:
        base = h or "col"
        n = seen.get(base, 0)
        seen[base] = n + 1
        uniq.append(base if n == 0 else f"{base}_{n}")
    out: list[dict[str, Any]] = []
    for row in rows[header_idx + 1 :]:
        if _row_fill_count(row) < 1:
            continue
        if _is_banner_row(row):
            continue
        item: dict[str, Any] = {}
        for i, key in enumerate(uniq):
            val = row[i].strip() if i < len(row) else ""
            if not val:
                continue
            item[key] = val
        if item:
            out.append(item)
    return out


def parse_cargo(rows: list[list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    start = 0
    for i, row in enumerate(rows[:5]):
        if row and row[0].strip().lower() == "cargo":
            start = i + 1
            break
    for row in rows[start:]:
        if not row or not row[0].strip():
            continue
        names = [n.strip() for n in row[4].split(",") if n.strip()] if len(row) > 4 else []
        out.append(
            {
                "label": row[0].strip(),
                "slots": _parse_slots(row[1] if len(row) > 1 else None),
                "packed_mass_kg": _parse_num(row[2] if len(row) > 2 else None),
                "unpacked_mass_kg": _parse_num(row[3] if len(row) > 3 else None),
                "internal_names": names,
                "notes": row[5].strip() if len(row) > 5 else "",
            }
        )
    return out


_WHEEL_CATEGORIES = ("Highway", "All-Terrain", "Offroad", "Mud", "Chained", "Scout", "All-terrain")


def parse_wheels(rows: list[list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    category = ""
    for row in rows:
        name = (row[0] if row else "").strip()
        if not name:
            continue
        cat_key = name if name != "All-terrain" else "All-Terrain"
        if cat_key in _WHEEL_CATEGORIES:
            category = cat_key
            continue
        if name in ("Wheel", "Friction") or name.startswith("Template"):
            continue
        out.append(
            {
                "name": name,
                "category": category,
                "friction": {
                    "asphalt": _parse_num(row[1] if len(row) > 1 else None),
                    "body": _parse_num(row[2] if len(row) > 2 else None),
                    "substance": _parse_num(row[3] if len(row) > 3 else None),
                },
                "rad_offs": _parse_num(row[4] if len(row) > 4 else None),
                "soft_force_scl": _parse_num(row[5] if len(row) > 5 else None),
                "width_single": _parse_num(row[6] if len(row) > 6 else None),
                "width_double": _parse_num(row[7] if len(row) > 7 else None),
                "weight": row[8].strip() if len(row) > 8 else "",
                "unlock_level": _parse_num(row[9] if len(row) > 9 else None),
                "price": _parse_num(row[10] if len(row) > 10 else None),
            }
        )
    return out


def parse_truck_colors(rows: list[list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    current_truck = ""
    start = 2
    for i, row in enumerate(rows[:5]):
        if row and "truck" in (row[0] or "").lower():
            start = i + 1
            break
    for row in rows[start:]:
        if not row:
            continue
        label = row[0].strip()
        if label and re.search(r"[A-Za-z]", label):
            current_truck = label
        if not current_truck:
            continue

        def _hsl(start: int) -> dict[str, int] | None:
            if len(row) <= start + 2:
                return None
            h, s, l = (_parse_num(row[start]), _parse_num(row[start + 1]), _parse_num(row[start + 2]))
            if h is None and s is None and l is None:
                return None
            return {
                "h": int(h) if h is not None else 0,
                "s": int(s) if s is not None else 0,
                "l": int(l) if l is not None else 0,
            }

        primary, secondary, tertiary = _hsl(1), _hsl(5), _hsl(9)
        if not any((primary, secondary, tertiary)):
            continue
        out.append(
            {
                "truck": current_truck,
                "variant_label": label if label != current_truck else "",
                "primary": primary,
                "secondary": secondary,
                "tertiary": tertiary,
            }
        )
    return out


def parse_addon_colors(rows: list[list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    start = 1
    for i, row in enumerate(rows[:5]):
        if row and "addon" in (row[0] or "").lower():
            start = i + 1
            break
    for row in rows[start:]:
        if not row or not row[0].strip():
            continue
        out.append(
            {
                "addon": row[0].strip(),
                "hue": _parse_num(row[1] if len(row) > 1 else None),
                "saturation": _parse_num(row[2] if len(row) > 2 else None),
                "brightness": _parse_num(row[3] if len(row) > 3 else None),
            }
        )
    return out


PARSERS: dict[str, Callable[[list[list[str]]], list[dict[str, Any]]]] = {
    "table": parse_table,
    "cargo": parse_cargo,
    "wheels": parse_wheels,
    "truck_colors": parse_truck_colors,
    "addon_colors": parse_addon_colors,
}


def _fuentes_manifest() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for entry in SHEET_CATALOG:
        book = entry["book"]
        out.append(
            {
                "id": entry["id"],
                "book": book,
                "book_name": BOOK_META[book]["name"],
                "title": entry["title"],
                "sheet": entry["sheet"],
                "csv": _csv_name(entry),
                "url": _export_url(book, entry["sheet"]),
                "parser": entry["parser"],
            }
        )
    return out


def fetch_csvs(entries: list[dict[str, Any]] | None = None) -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    for entry in entries or SHEET_CATALOG:
        path = os.path.join(RAW_DIR, _csv_name(entry))
        url = _export_url(entry["book"], entry["sheet"])
        print(f"  {entry['id']} ({entry['sheet']})...")
        urllib.request.urlretrieve(url, path)


def build_all() -> dict[str, Any]:
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    counts: dict[str, int] = {}
    combined: dict[str, list[dict[str, Any]]] = {
        "trucks": [],
        "engines": [],
        "gearboxes": [],
        "cargo": [],
        "trailers": [],
        "addons": [],
        "tires": [],
    }

    for entry in SHEET_CATALOG:
        csv_path = os.path.join(RAW_DIR, _csv_name(entry))
        rows = _read_csv(csv_path)
        parser = PARSERS[entry["parser"]]
        items = parser(rows)
        counts[entry["id"]] = len(items)

        out_name = f"{entry['id']}.json"
        payload = {
            "id": entry["id"],
            "source": BOOK_META[entry["book"]]["name"],
            "sheet": entry["sheet"],
            "updated_utc": ts,
            "items": items,
        }
        with open(os.path.join(OUT_DIR, out_name), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        # agregados por tema
        eid = entry["id"]
        if "trucks" in eid and "region" not in eid and "trucks2" not in eid:
            combined["trucks"].extend([{**it, "_source": entry["id"]} for it in items[:500]])
        elif "engines" in eid:
            combined["engines"].extend([{**it, "_source": entry["id"]} for it in items])
        elif "gearboxes" in eid:
            combined["gearboxes"].extend([{**it, "_source": entry["id"]} for it in items])
        elif eid.endswith("_cargo") or eid == "srinfo_cargo":
            combined["cargo"].extend([{**it, "_source": entry["id"]} for it in items])
        elif "trailers" in eid:
            combined["trailers"].extend([{**it, "_source": entry["id"]} for it in items])
        elif "addons" in eid and "colors" not in eid:
            combined["addons"].extend([{**it, "_source": entry["id"]} for it in items])
        elif "tires" in eid or eid == "srinfo_wheels" or eid == "usds_tires":
            combined["tires"].extend([{**it, "_source": entry["id"]} for it in items])

    # aliases legados (consultar_base.py)
    legacy_map = {
        "cargo.json": "srinfo_cargo.json",
        "wheels_comunidad.json": "srinfo_wheels.json",
        "truck_colors.json": "srinfo_colors.json",
        "addon_colors.json": "extras_addon_colors.json",
        "addons_usds.json": "usds_addons.json",
    }
    for legacy, src in legacy_map.items():
        sp = os.path.join(OUT_DIR, src)
        if os.path.isfile(sp):
            with open(sp, encoding="utf-8") as f:
                data = json.load(f)
            if legacy == "addon_colors.json":
                data = {
                    "sources": ["SnowRunner Extras"],
                    "updated_utc": ts,
                    "extras_presets": data.get("items", []),
                }
            with open(os.path.join(OUT_DIR, legacy), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    for topic, items in combined.items():
        with open(os.path.join(OUT_DIR, f"combined_{topic}.json"), "w", encoding="utf-8") as f:
            json.dump(
                {"updated_utc": ts, "topic": topic, "count": len(items), "items": items},
                f,
                indent=2,
                ensure_ascii=False,
            )

    fuentes = {
        "updated_utc": ts,
        "books": BOOK_META,
        "sources": _fuentes_manifest(),
        "counts": counts,
        "totals": {
            "sheets": len(SHEET_CATALOG),
            "records": sum(counts.values()),
        },
    }
    with open(os.path.join(OUT_DIR, "fuentes.json"), "w", encoding="utf-8") as f:
        json.dump(fuentes, f, indent=2, ensure_ascii=False)
    return fuentes


def main() -> int:
    parser = argparse.ArgumentParser(description="Importar hojas comunitarias SnowRunner (completo)")
    parser.add_argument("--fetch", action="store_true", help="Re-descargar CSV desde Google Sheets")
    args = parser.parse_args()

    if args.fetch:
        print(f"Descargando {len(SHEET_CATALOG)} hojas...")
        fetch_csvs()

    missing = [
        _csv_name(e)
        for e in SHEET_CATALOG
        if not os.path.isfile(os.path.join(RAW_DIR, _csv_name(e)))
    ]
    if missing:
        print(f"Faltan {len(missing)} CSV — ejecuta: python datos/importar_comunidad.py --fetch")
        print("  ej:", missing[0])
        return 1

    summary = build_all()
    print(f"Importado {summary['totals']['sheets']} hojas, {summary['totals']['records']} registros")
    print(f"  -> datos/comunidad/ ({len(SHEET_CATALOG)} JSON + combined_* + fuentes.json)")
    top = sorted(summary["counts"].items(), key=lambda x: -x[1])[:8]
    for k, n in top:
        print(f"     {k}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
