# Pendientes — validación en juego (por vehículo)

**Enfoque (jul 2026):** parches XML en `initial.pak` alineados con referencia real (TE / SR!NFO).
Sim orienta; **prueba final en mapa** (sensación, arranque, crawl en barro, carga si aplica).
CE archivado → `CE-ARCHIVADO.md`.

Metodología: `docs/METODO-PAK.md` · Fases de diseño: `docs/FASE-1.md` … `docs/FASE-4.md`.

## Reglas

1. **Un vehículo activo** a la vez.
2. Tras cambiar `patches.py`: `apply_mod.py` → copiar `initial.pak` → probar en juego.
3. Anotar en `camiones/<id>/FASES.md` → sección **Comentarios** si algo no cuadra.
4. No hay protocolo F1/F2/F3: validar el vehículo completo con la config de taller documentada en

   FASES.

## Comandos habituales

```powershell
```

Copiar `initial.pak` → `...\Steam\steamapps\common\SnowRunner\preload\paks\client\`

---

## Masas vacías aplicadas (registry + patches)

| Vehículo                | ID          | kg mod | Referencia                          |
| ----------------------- | ----------- | ------ | ----------------------------------- |
| Chevrolet CK1500        | `ck1500`    | 1750   | K10 ~1971                           |
| KHAN 39 Marshall        | `marshall`  | 2030   | SR!NFO ~2029; UAZ-469 TE 2380       |
| International Scout 800 | `scout800`  | 2100   | Scout 800 ~1800–2200                |
| KRS 58 Bandit           | `bandit`    | 7600   | SR!NFO 7861; KrAZ TE ~11–13 t       |
| International Fleetstar | `fleetstar` | 7400   | SR!NFO 7674; F2070 civil ~8200      |
| Chevrolet Kodiak C70    | `kodiak`    | 8150   | SR!NFO 8201                         |
| GMC MH9500              | `mh9500`    | 8200   | SR!NFO 8438                         |
| Tatra T813              | `t813`      | 14000  | Tatra 813 TE ~13800                 |

Torque nerfeado ~68 % en motores pesados (ver `patches.py` / FASES). Marshall y Scout 800: motor sin
parche aún.

---

## Índice rápido

| Vehículo                | ID          | Activo   | Siguiente paso                            | Doc                           |
| ----------------------- | ----------- | -------- | ----------------------------------------- | ----------------------------- |
| **KRS 58 Bandit**       | `bandit`    | **sí**   | Aplicar pak + probar sensación nueva masa | `camiones/bandit/FASES.md`    |
| Tatra T813              | `t813`      | no       | Aplicar pak (masa TE)                     | `camiones/t813/FASES.md`      |
| Fleetstar F2070A        | `fleetstar` | no       | Aplicar pak                               | `camiones/fleetstar/FASES.md` |
| KHAN 39 Marshall        | `marshall`  | no       | Aplicar pak                               | `camiones/marshall/FASES.md`  |
| Chevrolet CK1500        | `ck1500`    | no       | Sin cambio masa; revisar si hace falta    | `camiones/ck1500/FASES.md`    |
| Chevrolet Kodiak C70    | `kodiak`    | no       | Aplicar pak                               | `camiones/kodiak/FASES.md`    |
| GMC MH9500              | `mh9500`    | no       | Aplicar pak                               | `camiones/mh9500/FASES.md`    |
| International Scout 800 | `scout800`  | no       | Aplicar pak                               | `camiones/scout800/FASES.md`  |

**Motor compartido:** Fleetstar y Kodiak usan `e_us_truck_old.xml`. Calibrar motor en uno y repetir
prueba en el otro.

---

## Qué probar en juego (todos los vehículos)

- **Asfalto:** arranque WOT marcha alta — ¿aceleración creíble vs masa?
- **Barro:** neumático y suspensión de FASES, marcha baja — crawl y hundimiento.
- **Carga / remolque:** solo si el vehículo lleva bastidor, semi o remolque scout en FASES.
- **HUD:** km/h aproximados vs expectativa (sin CE; ojo humano).

Detalle por camión: `camiones/<id>/FASES.md` (config taller, neumáticos, motor).

---

## KRS 58 Bandit (`bandit`) — vehículo activo

Masa mod **7600 kg** · LAZ-740 · 47" UHD · 6×6 AWD + diff

### Comentarios

```text
```

---

## Resto de vehículos

Cada `camiones/<id>/FASES.md` tiene referencia real, parches y config de taller.
Tras `apply_mod.py`, anotar aquí o en Comentarios del FASES si algo falla.

| ID          | Masa (kg) | Doc principal                    |
| ----------- | --------- | -------------------------------- |
| `t813`      | 14000     | `camiones/t813/FASES.md`         |
| `fleetstar` | 7400      | `camiones/fleetstar/FASES.md`    |
| `marshall`  | 2030      | `camiones/marshall/FASES.md`     |
| `ck1500`    | 1750      | `camiones/ck1500/FASES.md`       |
| `kodiak`    | 8150      | `camiones/kodiak/FASES.md`       |
| `mh9500`    | 8200      | `camiones/mh9500/FASES.md`       |
| `scout800`  | 2100      | `camiones/scout800/FASES.md`     |

---

## Simulador (orientación)

Solo tocar `simulador.py` cuando la prueba en juego y el sim diverjan de forma clara.

| ID    | Mejora                    | Vehículos afectados        |
| ----- | ------------------------- | -------------------------- |
| SIM-1 | Caja `g_truck_default`    | fleetstar, kodiak, mh9500  |
| SIM-2 | `torque_shape` diesel     | Si-6V compartido           |
| SIM-3 | Par × carga               | fleetstar, kodiak          |

---

## En espera (no mezclar con vehículo activo)

| Tema              | Doc                | Retomar cuando                           |
| ----------------- | ------------------ | ---------------------------------------- |
| Clima día/noche   | `docs/FASE-7.md`   | Barro estable en 2+ camiones             |
| Remolques / hitch | `docs/FASE-8.md`   | Semi/bastidor validados en MH + Marshall |
| Catálogo `.pak`   | `datos/README.md`  | Mantenimiento                            |

---

## Histórico CE (no usar como gate)

Sesiones `telemetria/sesiones/*/ce_*.json` y `cheat_engine/` son **referencia histórica** jun-2026.
No forman parte del checklist actual. Ver `CE-ARCHIVADO.md`.

---

## Índice documentos

| Qué              | Dónde                    |
| ---------------- | ------------------------ |
| Método central   | `docs/METODO-PAK.md`     |
| CE archivado     | `docs/CE-ARCHIVADO.md`   |
| Catálogo XML     | `datos/README.md`        |
| Notas personales | `personal.txt`           |

*Última revisión: 2026-07-29 — masas TE/SR!NFO; sin protocolo F1–F3.*
