# SnowRunner — Tatra T813 (mod realista)

Metodología general: `docs/FASE-1.md` … `docs/FASE-8.md`.

---

## Tu setup actual

| Pieza      | En juego                      | XML                                             |
|------------|-------------------------------|-------------------------------------------------|
| Motor      | **KZGT-8 490**                | `ru_special_engine_1` (230 k Ncm stock)         |
| Neumáticos | **JAT MSH I 50"**             | `wheels_superheavy_mudtires` / tire `JAT MSH I` |
| Tracción   | 8×8 AWD + diff lock instalado | stock HEAVY                                     |
| Carga F3   | Semirremolque barro           | escenario `semi_cargado`                        |

---

## Qué hace el mod

| Parámetro                    | Stock      | Mod            |
|------------------------------|------------|----------------|
| Masa total                   | ~14021 kg  | **14571 kg**   |
| `Responsiveness`             | 0.2        | **0.14**       |
| Depósito                     | 380 L      | **340 L**      |
| MSH I `SubstanceFriction`    | 3.0        | **2.2**        |
| KZGT (`ru_special_engine_1`) | 230000 Ncm | **157000 Ncm** |

**Compartido:** `e_ru_special.xml` (Tatra, ZiKZ, otros HEAVY special). `wheels_superheavy_mudtires.xml` (otros 8×8).

---

## Aplicar

```powershell
python apply_mod.py --vehicle t813
python verify_pak.py
python -m camiones.t813.simulador
python -m unittest camiones.t813.test -v
```

Copiar `initial.pak` → `...\SnowRunner\preload\paks\client\`

---

## Telemetría

| Fase | Protocolo           | Estado CE                              |
|------|---------------------|----------------------------------------|
| F1   | `t813_f1_asfalto`   | Grabado crawl — **regrabar WOT** recto |
| F2   | `t813_f2_barro_msh` | **MAE ~5.1** (`20260707`)              |
| F3   | `t813_f3_carga`     | Grabado — validar semi con `cargo`     |

```powershell
python grabar_ce.py --probe
.\grabar_telemetria.bat
python importar_ce_csv.py --auto --compare --index
.\grabar_telemetria.bat drive --watch 30   # throttle + rpm en CSV desde jul-2026
```

CE ID: `s_tatra_t813` · Masa vacía mod: **14571 kg**

---

## Pendiente

- F1: asfalto recto, marcha alta, WOT ~60 s (no crawl).
- Confirmar `engine_name_xml` con probe (KZGT → `ru_special_engine_1`).
- Afinar `T813_MUD_*` si F2 en barro profundo diverge del sim.
- F3: `.\grabar_telemetria.bat cargo` quieto 30 s antes de grabar.
- Opcional: `drive_snap gas_off/gas_full` en T813 (calibrado en Bandit).
