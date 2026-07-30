# Método — modificar solo archivos del juego (`initial.pak`)

**Enfoque del proyecto (jul 2026):** trabajar **únicamente** sobre los XML que ya existen dentro del
`.pak` del juego. El simulador Python **orienta** el diseño; la prueba final es **en juego** tras
instalar el `.pak`. CE y API quedan **archivados** (`CE-ARCHIVADO.md`).

---

## Qué modificamos y qué no

| Sí (nuestro alcance)                          | No (archivado / fuera de alcance)     |
| --------------------------------------------- | ------------------------------------- |
| XML en `initial.pak` del cliente              | API HTTP / proyecto hermano           |
| `camiones/<id>/patches.py`                    | **Cheat Engine / `grabar_ce.py`**     |
| Motor, masa, neumáticos, suspensión, depósito | `importar_ce_csv`, MAE por telemetría |
| `Responsiveness`, `Torque`, `MaxDeltaAngVel`  | Mapas `.pak` de zona                  |
| Neumáticos `wheels_*.xml`                     | Masas globales `cargo_*.xml`          |

---

## Rutas del juego

| Ubicación              | Ruta                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------ |
| **Steam (instalar)**   | `C:\Program Files (x86)\Steam\steamapps\common\SnowRunner\preload\paks\client\initial.pak` |
| **Backup fábrica**     | `snowrunner real\initial.pak.bak`                                                          |
| **Mod generado**       | `snowrunner real\initial.pak`                                                              |
| **Parches fuente**     | `camiones/<vehicle_id>/patches.py`                                                         |
| **Registro vehículos** | `camiones/registry.py`                                                                     |

Dentro del ZIP, las entradas usan **backslash**: `[media]\classes\trucks\chevrolet_ck1500.xml`. En
`patches.py` usamos la forma con `/`: `[media]/classes/trucks/chevrolet_ck1500.xml`.

---

## Flujo de trabajo

```powershell
```

**No usar** `7z u` sobre el `.pak` completo: corrompe el tail Saber (1768 bytes). Usar siempre
`repack_pak.py` vía `apply_mod.py`.

---

## Por fase — qué XML toca cada una

| Fase                 | Archivos típicos en `.pak`                                                   | Doc                                               |
| -------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------- |
| **1** Motor + chasis | `classes/trucks/*.xml`, `classes/engines/*.xml`, `classes/suspensions/*.xml` | `FASE-1.md`                                       |
| **2** Neumáticos     | `classes/wheels/wheels_*.xml`                                                | `FASE-2.md`                                       |
| **3** Carga (masa)   | Solo chasis (ya Fase 1); **no** `cargo_*.xml`                                | `FASE-3.md`                                       |
| **4** Terreno        | Solo neumático (Fase 2); terreno = mapa                                      | `FASE-4.md`                                       |
| **5** Telemetría HUD | —                                                                            | `FASE-5.md` **archivado**                         |
| **6** CE Havok       | —                                                                            | `FASE-6.md` **archivado** — ver `CE-ARCHIVADO.md` |
| **7** Clima          | — (no editable en camión)                                                    | `FASE-7.md`                                       |
| **8** Remolques      | F3 en juego; no `trailers/*.xml` globales                                    | `FASE-8.md` **archivado** (sin inventario)        |

Detalle por camión: `camiones/<id>/FASES.md`.

---

## Vehículos registrados

| ID          | XML camión                           | Parches                         |
| ----------- | ------------------------------------ | ------------------------------- |
| `ck1500`    | `chevrolet_ck1500.xml`               | `camiones/ck1500/patches.py`    |
| `mh9500`    | `gmc_9500.xml`                       | `camiones/mh9500/patches.py`    |
| `fleetstar` | `international_fleetstar_f2070a.xml` | `camiones/fleetstar/patches.py` |
| `marshall`  | `khan_39_marshall.xml`               | `camiones/marshall/patches.py`  |
| `kodiak`    | `chevrolet_kodiakc70.xml`            | `camiones/kodiak/patches.py`    |
| `scout800`  | `international_scout_800.xml`        | `camiones/scout800/patches.py`  |
| `t813`      | `tatra_t813.xml`                     | `camiones/t813/patches.py`      |
| `bandit`    | `krs_58_bandit.xml`                  | `camiones/bandit/patches.py`    |

```powershell
```

---

## Herramientas del repo (rol)

| Herramienta                      | Rol respecto al `.pak`                |
| -------------------------------- | ------------------------------------- |
| `apply_mod.py` / `repack_pak.py` | **Escribe** el mod                    |
| `verify_pak.py`                  | **Comprueba** valores en el `.pak`    |
| `auditar_pak_catalogo.py`        | Indexa XML del backup (referencia)    |
| `camiones/*/simulador.py`        | Orientación antes/después             |
| ~~`grabar_ce.py`~~               | **Archivado** — ver `CE-ARCHIVADO.md` |

---

## Criterio de éxito

1. `verify_pak.py` OK para el camión activo.
2. Simulador coherente con la intención del parche (tendencias).
3. En juego: comportamiento creíble tras instalar el `.pak` en Steam.

Si en juego no cuadra: ajustar **XML** en `patches.py` y repetir `apply_mod.py`.

---

*Documento central — enlazado desde `FASE-1.md` … `FASE-8.md`.*
