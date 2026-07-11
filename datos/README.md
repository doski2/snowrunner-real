# Base de datos del juego — convenciones

Índice único del mod SnowRunner realista. Ver [PLAN-BASE-DATOS-JUEGO.md](../docs/PLAN-BASE-DATOS-JUEGO.md).

## Capas

| Carpeta                   | Capa | Contenido                                   |
|---------------------------|------|---------------------------------------------|
| `raw/`                    | A    | CSV Havok archivados, copias de `LegacyLog` |
| `catalogo/`               | B    | XML indexado desde `initial.pak.bak`        |
| `comunidad/`              | B′   | SR!NFO, USDS, SnowRunner Extras (CSV→JSON)  |
| `indices/`                | C+D  | `manifest.json`, `calibracion.json`         |
| `../telemetria/sesiones/` | C    | Sesiones CE importadas (JSON)               |

Flujo: **raw → catálogo → sesiones → parches/sim**.

## Comandos habituales

```powershell
# Regenerar índice maestro (offsets, vehículos mod, tamaño .pak)
python datos/build_indices.py

# Grabar mientras juegas (LIVE en consola, Ctrl+C, import+index)
.\grabar_telemetria.bat

# Extraer catálogo XML del backup Steam
python auditar_pak_catalogo.py

# Consultas rápidas
python consultar_base.py manifest
python consultar_base.py truck --mod marshall
python consultar_base.py engine MaxDeltaAngVel --vehicle mh9500
python consultar_base.py cargo bricks
python consultar_base.py wheel "UHD III"
python consultar_base.py buscar tatra
python consultar_base.py comunidad
python consultar_base.py mae --vehicle marshall --terrain mud --entry-type segment
python indexar_sesion.py --all

# Hojas comunitarias (Google Sheets → JSON)
python datos/importar_comunidad.py --fetch
```

## Metadatos de sesión (`session_context`)

Cada JSON en `telemetria/sesiones/` debe incluir en `meta.session_context`:

| Campo           | Obligatorio | Ejemplo                                                |
|-----------------|-------------|--------------------------------------------------------|
| `build_juego`   | sí          | Steam jun-2026                                         |
| `mod_commit`    | sí          | hash git o fecha `apply_mod`                           |
| `map`           | sí          | Michigan                                               |
| `location_note` | sí          | TM II barro norte garaje                               |
| `clima`         | Fase 7      | seco / lluvia / noche                                  |
| `hora_juego`    | Fase 7      | 14:30                                                  |
| `baseline_tag`  | probes      | `baseline_mod_v1`                                      |
| `setup`         | recomendado | motor, caja, neumático, diff, remolque + refs XML §2.5 |
| `capture_tool`  | auto        | `grabar_ce.py`                                         |

Al importar CE:

```powershell
python importar_ce_csv.py --auto --compare --map Michigan --location "partida libre" --baseline play_free_v1 --index
```

## Nombres de archivo

- CSV archivados: `raw/ce_csv/YYYY-MM-DD_<protocolo>.csv`
- Catálogo: `catalogo/{trucks,engines,wheels,gearboxes,suspensions,trailers}.json`
- Sesiones: `telemetria/sesiones/<vehicle_id>/ce_<protocolo>_<timestamp>.json`

## Calidad

1. Descartar sesiones con `terrain_kind` vacío en >50 % muestras.
2. Un cambio XML por experimento; anotar `baseline_tag` distinto.
3. Tras update Steam: `python datos/build_indices.py` + `grabar_ce.py --probe`.
