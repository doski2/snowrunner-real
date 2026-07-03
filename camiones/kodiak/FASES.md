# SnowRunner — Chevrolet Kodiak C70 (mod realista)

Metodología: `docs/FASE-1.md` … `docs/FASE-8.md` · Referencia cercana: `camiones/fleetstar/FASES.md`.

---

## Setup de referencia (catálogo stock, jun 2026)

| Pieza | Stock XML / taller |
|-------|---------------------|
| Motor | **Si-6V/1900** (`us_truck_old_engine_0`) — opcional **2100T** |
| Neumáticos | **39" UHD I** (`highway_1`, `wheels_medium_double`) |
| (taller) | También 39/43" UHD II–III, UAD, UOD — ver abajo |
| Tracción | **AWD** + **bloqueo diferencial** (instalar en taller) |
| Suspensión | Stock (`chevrolet_kodiakC70_suspension_default`) |
| Ruedas | **4** (no 6×4 como Fleetstar) |

**No confundir con Fleetstar:** el F2070A lleva **42"** UHD; el Kodiak solo admite **39"** (y **43"** en taller), mismo archivo de ruedas `wheels_medium_double.xml` pero otro diámetro in-game.

| Familia | Talla Kodiak | XML sim (`tire`) |
|---------|--------------|------------------|
| Highway UHD | 39" / 43" UHD I | `highway` → `highway_1` |
| Allterrain UAD | 39" / 43" UAD I | `allterrain` |
| Offroad UOD | 39" / 43" UOD I | `offroad` |

Protocolos CE actuales asumen **39" UHD I** + AWD + diff. Si conduces con **UOD**, graba con barro y revisa protocolo `offroad` en import.

---

## Qué hace el mod (sin CE aún — valores de diseño)

| Parámetro | Stock (catálogo) | Mod |
|-----------|------------------|-----|
| Masa total | ~7513 kg | **7900 kg** |
| Combustible | 200 L | **175 L** |
| Responsiveness | 0.15 | **0.11** |
| Si-6V/1900 torque | 135000 | **92000** |
| Si-6V/2100T torque | 145000 | **99000** |
| `highway_1` Substance | 0.4 | **0.5** |

Parches compartidos con familia Fleetstar: `e_us_truck_old.xml`, `wheels_medium_double.xml`.

---

## Aplicar

```powershell
python camiones/kodiak/apply_mod.py
python verify_pak.py
python -m camiones.kodiak.simulador
python -m unittest camiones.kodiak.test -v
```

Copiar `initial.pak` → `...\SnowRunner\preload\paks\client\`

---

## Fases — orden y telemetría

| Fase | Qué hacer | Protocolo |
|------|-----------|-----------|
| **1** | Asfalto vacío, AWD+diff, acelerar | `kd_f1_asfalto` |
| **2** | Barro UHD + AWD + diff, marcha L | `kd_f2_barro_uhd` |
| **3** | Bastidor / carga en barro | `kd_f3_carga` |
| **5–6** | CE + comparación sim | `grabar_telemetria.bat` |

```powershell
python grabar_ce.py --probe --map Michigan
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare --index
```

ID Havok esperado: `s_chevrolet_kodiakc70`.

---

## Sim de referencia (sin calibrar CE)

```powershell
python -m camiones.kodiak.simulador
```

`KD_MUD_IMMERSION_RATE` / `KD_MUD_RESIST_MULT` son **estimación inicial** (4 ruedas, más masa que Fleetstar). Re-grabar `kd_f2_barro_uhd` para afinar.

---

## Pendiente

- [ ] Validar parches XML con `verify_pak.py` (masas exactas en `chevrolet_kodiakc70.xml`)
- [ ] CE `kd_f1_asfalto` y `kd_f2_barro_uhd`
- [ ] Calibrar `KD_MUD_*` con telemetría
- [ ] `kd_f3_carga` con bastidor lleno (`scan_cargo.py`)
