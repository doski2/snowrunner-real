# SnowRunner — Tatra T813 (mod realista)

Metodología general: `docs/FASE-1.md` … `docs/FASE-8.md`.

---

## Tu setup actual

| Pieza | En juego | XML |
|-------|----------|-----|
| Motor | **KZGT-8 490** | `ru_special_engine_1` (230 k Ncm stock) |
| Neumáticos | **JAT MSH I 50"** | `wheels_superheavy_mudtires` / tire `JAT MSH I` |
| Tracción | 8×8 AWD + diff lock instalado | stock HEAVY |
| Carga F3 | Semirremolque barro | escenario `semi_cargado` |

---

## Qué hace el mod

| Parámetro | Stock | Mod |
|-----------|-------|-----|
| Masa total | ~14021 kg | **14571 kg** |
| `Responsiveness` | 0.2 | **0.14** |
| Depósito | 380 L | **340 L** |
| MSH I `SubstanceFriction` | 3.0 | **2.2** |
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

| Fase | Protocolo | Notas |
|------|-----------|-------|
| F1 | `t813_f1_asfalto` | KZGT + MSH I + diff; WOT recto |
| F2 | `t813_f2_barro_msh` | Barro marcha baja; calibrar `T813_MUD_*` |
| F3 | `t813_f3_carga` | Semi cargado barro |

```powershell
python grabar_ce.py --probe
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare
```

CE ID: `s_tatra_t813` · Masa vacía mod: **14571 kg**

---

## Pendiente

- Confirmar `engine_name_xml` con probe tras montar KZGT-8 490.
- Calibrar `T813_MUD_IMMERSION_RATE` / `T813_MUD_RESIST_MULT` con CE F2.
- F3: verificar payload semi con `grabar_telemetria.bat cargo`.
