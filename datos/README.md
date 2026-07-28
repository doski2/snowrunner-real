# Base de datos del juego — convenciones

Índice único del mod SnowRunner realista. Ver
[PLAN-BASE-DATOS-JUEGO.md](../docs/PLAN-BASE-DATOS-JUEGO.md).

**Producto del mod:** cambios XML en `initial.pak` vía `camiones/*/patches.py` — ver
[METODO-PAK.md](../docs/METODO-PAK.md). CE archivado: [CE-ARCHIVADO.md](../docs/CE-ARCHIVADO.md).

## Capas

| Carpeta                     | Capa   | Contenido                                     |
| --------------------------- | ------ | --------------------------------------------- |
| `raw/`                      | A      | CSV Havok archivados, copias de `LegacyLog`   |
| `catalogo/`                 | B      | XML indexado desde `initial.pak.bak`          |
| `comunidad/`                | B′     | SR!NFO, USDS, SnowRunner Extras (CSV→JSON)    |
| `indices/`                  | C+D    | `manifest.json`, `calibracion.json`           |
| `../telemetria/sesiones/`   | C      | Sesiones CE *(histórico, archivado)*          |

Flujo activo: **catálogo → parches/sim → `.pak`**. CE archivado.

## Comandos habituales

```powershell
```

~~`grabar_telemetria.bat` / `importar_ce_csv.py`~~ — archivados (`CE-ARCHIVADO.md`).

## Metadatos de sesión (`session_context`) — *histórico CE*

Cada JSON en `telemetria/sesiones/` *(archivado)* incluía en `meta.session_context`:

| Campo             | Obligatorio   | Ejemplo                                                  |
| ----------------- | ------------- | -------------------------------------------------------- |
| `build_juego`     | sí            | Steam jun-2026                                           |
| `mod_commit`      | sí            | hash git o fecha `apply_mod`                             |
| `map`             | sí            | Michigan                                                 |
| `location_note`   | sí            | TM II barro norte garaje                                 |
| `clima`           | Fase 7        | seco / lluvia / noche                                    |
| `hora_juego`      | Fase 7        | 14:30                                                    |
| `baseline_tag`    | probes        | `baseline_mod_v1`                                        |
| `setup`           | recomendado   | motor, caja, neumático, diff, remolque + refs XML §2.5   |
| `capture_tool`    | auto          | `grabar_ce.py` *(archivado)*                             |

~~Importar CE~~ — ver `CE-ARCHIVADO.md`.

## Nombres de archivo

- CSV archivados: `raw/ce_csv/YYYY-MM-DD_<protocolo>.csv`
- Catálogo: `catalogo/{trucks,engines,wheels,gearboxes,suspensions,trailers}.json`
- Sesiones: `telemetria/sesiones/<vehicle_id>/ce_<protocolo>_<timestamp>.json`

## Calidad

1. Descartar sesiones con `terrain_kind` vacío en >50 % muestras.
2. Un cambio XML por experimento; anotar `baseline_tag` distinto.
3. Tras update Steam: `python datos/build_indices.py` + `python apply_mod.py --refresh-backup`.
