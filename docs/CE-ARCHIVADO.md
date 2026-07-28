# Cheat Engine / telemetría Havok — **archivado**

**Cambio de planes (jul 2026):** el flujo CE (`grabar_ce.py`, `grabar_telemetria.bat`,
`cheat_engine/`, sesiones `ce_*.json`) **queda fuera del proyecto activo**, igual que la API
hermana.

## Enfoque vigente

| Sí                                      | No (archivado)                                 |
| --------------------------------------- | ---------------------------------------------- |
| `camiones/<id>/patches.py`              | Lectura memoria Havok en vivo                  |
| `apply_mod.py` → `initial.pak`          | `grabar_telemetria.bat`                        |
| `verify_pak.py`                         | `importar_ce_csv.py` / MAE por tramos          |
| `camiones/*/simulador.py` (orientación) | Calibración offsets pedal, etc.                |
| Prueba en juego (sensación, km/h HUD)   | `comparar_telemetria.py` como gate obligatorio |

Ver **`METODO-PAK.md`**.

## Qué hacer con el código CE

La carpeta `cheat_engine/` y scripts relacionados **permanecen en el repo** como referencia
histórica. No forman parte del checklist de un camión nuevo.

| Carpeta / script                               | Estado    |
| ---------------------------------------------- | --------- |
| `cheat_engine/`                                | Archivado |
| `grabar_ce.py`, `grabar_telemetria.bat`        | Archivado |
| `importar_ce_csv.py`, `comparar_telemetria.py` | Archivado |
| `telemetria/sesiones/`                         | Histórico |
| `banco_*.bat`                                  | Archivado |

## Validación sin CE

```powershell
```

## Documentación histórica

- `docs/FASE-5.md`, `docs/FASE-6.md`
- `cheat_engine/README.md`
