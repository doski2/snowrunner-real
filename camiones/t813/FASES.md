# SnowRunner — Tatra T813 (mod realista)

Metodología: `docs/METODO-PAK.md`, `docs/FASE-1.md` … `docs/FASE-4.md`.

| Campo          | Valor                        |
| -------------- | ---------------------------- |
| ID mod         | `t813`                       |
| ID juego       | `tatra_t813`                 |
| DLC            | `dlc_4`                      |
| Tipo           | HEAVY 8×8                    |
| Masa vacía mod | **14000 kg**                 |
| Parches        | `camiones/t813/patches.py`   |
| Simulador      | `camiones/t813/simulador.py` |

---

## Setup en juego (referencia)

| Pieza      | En juego              | XML / socket                                |
| ---------- | --------------------- | ------------------------------------------- |
| Motor      | **KZGT-8 490**        | `ru_special_engine_1` en `e_ru_special.xml` |
| Neumáticos | **JAT MSH I 50"**     | `wheels_superheavy_mudtires` / `JAT MSH I`  |
| Tracción   | 8×8 + diff instalado  | stock HEAVY                                 |
| Carga F3   | Semirremolque barro   | escenario sim `semi_cargado`                |

**Compartido:** `e_ru_special.xml` (Tatra, ZiKZ, otros HEAVY special).
`wheels_superheavy_mudtires.xml` (otros 8×8).

---

## Referencia real

### Prototipo

[Tatra 813](https://truck-encyclopedia.com/coldwar/czech/tatra-813.php) (KOLOS) — camión
checoslovaco
**8×8** de uso militar y civil. Prototipo en **1960**; desarrollo oficial desde **1964**; serie
desde
**marzo 1967** hasta el **T815** (**1982**). ~**11 751** unidades en variantes 4×4, 6×6 y 8×8.
Chasis tubular Tatra (tubo central + semiejes oscilantes), **7** diferenciales interejes, ejes
delanteros desconectables, inflado central de neumáticos en versiones militares.

En SnowRunner: motor taller **KZGT-8** y neumático **JAT MSH I** son nombres de juego/DLC, no la
ficha del motor real **T930 V12**.

### Ficha histórica ([Truck Encyclopedia](https://truck-encyclopedia.com/coldwar/czech/tatra-813.php))

| Campo               | Valor real (8×8 KOLOS)                                         |
| ------------------- | -------------------------------------------------------------- |
| Motor               | Tatra **T930** V12 diésel 17,64 L, refrigerado por aire        |
| Potencia            | **190–270 hp** (258–199 kW según versión)                      |
| Torque              | **990 Nm** a 1300 rpm                                          |
| Masa en vacío       | **13 800 kg**                                                  |
| Masa bruta          | **22 000 kg**                                                  |
| Carga útil          | **7 500 kg** (plataforma) / tractor hasta ~65–100 t remolque   |
| Dimensiones         | 8800 × 2500 × 2780 mm                                          |
| Transmisión         | 5+1 + reductor 2 etapas → **20** marchas adelante, **4** atrás |
| Vel. máx.           | **80+ km/h** (carretera)                                       |
| Consumo / autonomía | ~44 L/100 km; ~650 km carretera; ~300/150 km on/off road       |
| Depósito juego      | 380 L (mod **340 L**) — encaja con autonomía larga real        |

Capacidades off-road citadas en desarrollo: zanja **1,5 m**, obstáculo vertical **60 cm**, pendiente
**30°**. Opcional militar: cabrestante (**98 kN** máx., cable 60 m).

### Ficha comunidad (SR!NFO)

| Campo            | Valor                |
| ---------------- | -------------------- |
| Masa vacía       | **15811 kg**         |
| Torque stock/max | 205k / 260k Ncm      |
| Depósito         | 380 L                |
| Tracción         | 8×8, diff Switchable |

SR!NFO infla masa respecto al **13,8 t** histórico; el mod (**14,6 t**) queda entre catálogo y
SR!NFO, más cerca del vacío real con equipamiento de juego.

### XML stock vs mod

| Parámetro                    | Real (ref.)   | Catálogo `.pak` | Mod          |
| ---------------------------- | ------------- | --------------- | ------------ |
| Masa                         | **13 800 kg** | ~14021 kg       | **14000 kg** |
| Motor (nombre juego)         | T930 V12      | KZGT 230k Ncm   | **157k Ncm** |
| MSH I `SubstanceFriction`    | —             | 3.0             | **2.2**      |

Mod: masa y torque entre stock XML y SR!NFO; nerfeo ~68 % en motor KZGT (unidades Ncm del juego, no
Nm del T930).

```powershell
```

---

## Qué hace el mod (stock → realista)

| Parámetro                     | Stock      | Mod              | Fase   |
| ----------------------------- | ---------- | ---------------- | ------ |
| Masa total                    | ~14021 kg  | **14000 kg**     | 1 / 3  |
| Depósito                      | 380 L      | **340 L**        | 1      |
| KZGT (`ru_special_engine_1`)  | 230000 Ncm | **157000 Ncm**   | 1      |
| MSH I `SubstanceFriction`     | 3.0        | **2.2**          | 2 / 4  |

**No se toca:** suspensión, caja, diff lock, geometría de ruedas.

---

## Archivos XML parcheados

| Archivo en `initial.pak`                                            | Cambios                           |
| ------------------------------------------------------------------- | --------------------------------- |
| `[media]/_dlc/dlc_4/classes/trucks/tatra_t813.xml`                  | Masa, depósito                    |
| `[media]/classes/engines/e_ru_special.xml`                          | Torque y consumo KZGT (y otros)   |
| `[media]/_dlc/dlc_11/classes/wheels/wheels_superheavy_mudtires.xml` | `JAT MSH I` → `SubstanceFriction` |

---

## Fases de prueba (en juego)

Anotar sensación y km/h del HUD. El sim orienta; la prueba final es en mapa.

### F1 — Asfalto

| Condición  | Valor                                      |
| ---------- | ------------------------------------------ |
| Mapa       | Carretera recta                            |
| Motor      | KZGT-8 490                                 |
| Neumático  | JAT MSH I 50"                              |
| Diff       | ON                                         |
| Carga      | Vacío (14000 kg)                           |
| Conducción | WOT, **marcha alta**, ~60 s recto          |

**Cierre:** aceleración contenida vs stock; no “cohete” en recta.

### F2 — Barro MSH I

| Condición  | Valor                               |
| ---------- | ----------------------------------- |
| Mapa       | Barro Michigan o North Port         |
| Neumático  | JAT MSH I 50"                       |
| Diff       | ON                                  |
| Carga      | Vacío                               |
| Conducción | Marcha **L**, gas sostenido 30–60 s |

**Cierre:** crawl lento pero avanza. Si no cuadra → `T813_MUD_*` en sim y/o `SubstanceFriction`.

### F3 — Semi cargado

| Condición | Valor                         |
| --------- | ----------------------------- |
| Carga     | Semirremolque barro           |
| Resto     | Igual que F2                  |

**Cierre:** peso se nota; avance muy lento o casi inmóvil según carga.

---

## Referencia simulador

```powershell
```

Constantes barro: `T813_MUD_IMMERSION_RATE = 0.48`, `T813_MUD_RESIST_MULT = 1.18`.

---

## Aplicar y validar

```powershell
```

Copiar `initial.pak` → `...\SnowRunner\preload\paks\client\`

| Paso            | Qué comprueba                       |
| --------------- | ----------------------------------- |
| `verify_pak.py` | Valores XML dentro del `.pak`       |
| `simulador`     | Tendencias F1/F2/F3                 |
| Prueba en juego | Sensación + km/h HUD por fase       |

---

## Pendiente

| ID      | Fase   | Estado   | Notas                    |
| ------- | ------ | -------- | ------------------------ |
| T813-F1 | 1      | [ ]      | Asfalto WOT marcha alta  |
| T813-F2 | 2      | [ ]      | Barro marcha baja        |
| T813-F3 | 3      | [ ]      | Semi cargado barro       |

---

## Comentarios

```text
```

---

*Última revisión: 2026-07-29 — Truck Encyclopedia + Referencia real.*
