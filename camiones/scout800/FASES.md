# International Scout 800 — Fases y calibracion CE

**ID:** `scout800` · CE: `s_international_scout_800` · Masa mod objetivo **2350 kg**

## Setup de referencia (tu camioneta)

| Pieza | Juego | XML |
|-------|-------|-----|
| Motor | AAT-6V 4.0 | `us_scout_old_engine_0` (`e_us_scout_old.xml`) |
| Neumatico | 33\" HS I | `wheels_scout_highway` / JAT HS I |
| Diff | Siempre activo | `DiffLockType="Always"` en truck |
| Caja | Stock | `g_scout_default` |

**No** reutilizar sesiones CK1500: otra masa, otro motor, diff distinto.

## Estado mod XML

| Archivo | Cambio | Estado |
|---------|--------|--------|
| `international_scout_800.xml` | Responsiveness 0.04; masa 1600+750 | Aplicado (placeholder) |
| `e_us_scout_old.xml` motor_0 | Nerfeo AAT-6V | **Pendiente** F1 CE |
| `wheels_scout_highway.xml` | HS I barro | **Pendiente** F2 CE |

## Protocolos CE

| Fase | Protocolo | Que grabar |
|------|-----------|------------|
| F1 | `s8_f1_asfalto_aat6v` | Asfalto WOT ~60 s; solo motor+HS I |
| F2 | `s8_f2_barro_hs` | Mismo tramo barro Michigan; diff+L |
| F3 | `s8_f3_carga_barro` | Remolque scout + vigas |

```powershell
.\grabar_telemetria.bat motor_scout
python importar_ce_csv.py --protocol s8_f1_asfalto_aat6v --compare --index
```

## Orden recomendado

1. Cerrar **CK-F1** (CK1500 activo en proyecto).
2. `motor_scout` → indexar `s8_f1_asfalto_aat6v`.
3. F2 barro → ajustar `S8_MUD_*` en `simulador.py`.
4. F3 cuando enganches remolque.
