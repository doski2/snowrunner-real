# SnowRunner — Fase 7: Entorno, clima y tiempo

Continuación de Fases 1–6. Responde las preguntas de `personal.txt`: ¿afecta la lluvia al barro? ¿conviene posponer rutas si llueve? ¿la noche enfría el barro y lo deja más seco?

**Objetivo Fase 7:** separar **lo que el juego simula** de **lo que parece** (lluvia visual, ciclo día/noche) y definir reglas prácticas para el mod realista.

---

## Estado

| Tarea | Estado |
|-------|--------|
| Documentar clima dinámico vs física | Hecho |
| Documentar wetness / humedad de mapa (Fase 4 ampliada) | Hecho |
| Documentar ciclo día/noche y presets | Hecho |
| Deformación persistente (surcos) | Hecho |
| Protocolos telemetría día vs noche | Hecho (`f7_*`, `mh_f7_*`) |
| **Cheat Engine** día vs noche | Pendiente |
| Simulador con clima dinámico | **No** — fuera de alcance (ver abajo) |
| Prueba en juego mismo tramo día/noche | Pendiente (tú) |

---

## Respuesta corta (para jugar con el mod)

| Pregunta | Respuesta |
|----------|-----------|
| ¿La lluvia dinámica empeora el barro? | **No** — es sobre todo visual/sonora |
| ¿Debo posponer una ruta si llueve? | **No por lluvia**; sí si el tramo ya está destrozado (surcos) o es barro profundo con MH9500 cargado |
| ¿La noche seca el barro por temperatura? | **No** — no hay simulación térmica del terreno |
| ¿Es mejor de noche el barro? | **No por física**; puede parecer distinto por luz y visibilidad |
| ¿Qué sí empeora el barro? | Zonas **wetness** del mapa, **tint** oscuro, **barro oculto** (extrusion), **más peso**, **repetir la misma ruta** |

---

## Clima dinámico (lluvia, nieve, nubes)

SnowRunner **sí tiene** clima dinámico: lluvia, nieve, distintos niveles de nubosidad y claridad. Mejora atmósfera y efectos visuales.

En el **Q&A de lanzamiento** (Focus / Saber), a la pregunta *«Does the weather affect gameplay?»* la respuesta oficial fue: **no hay planes de que el clima afecte al gameplay** — es decir, la lluvia que ves **no cambia** en tiempo real la viscosidad del barro bajo las ruedas.

| Elemento | ¿Afecta física? | Notas |
|----------|-----------------|-------|
| Lluvia cayendo | **No** (dinámica) | Partículas + sonido ambiente |
| Nieve cayendo | **No** (dinámica) | Igual |
| Nubes / claridad | **No** | Iluminación y cielo |
| Zona del mapa pintada **wetness** | **Sí** | Humedad **estática** del autor del mapa |
| Barro oculto + `Extrudes To Wetness` | **Sí** | Barro enterrado más líquido cuando la humedad del mapa lo activa |

Fuentes: [Launch Q&A — Focus Forums](https://forums.focus-entmt.com/topic/44986/launch-q-a), [Terrain Physics Blog](https://forums.focus-entmt.com/topic/43997/terrain-physics-blog), [Wetness — Saber Docs](https://expeditions-guides.saber.games/map_modding/creating_a_map/terrain/geometry_brushes_for_terrain/wetness/).

### Implicación para el mod

El mod CK1500 / MH9500 **no puede** hacer que «llueva más duro» ni que el barro se seque de día. Eso vive en el **mapa**, no en `initial.pak` del camión.

---

## Humedad del mapa (wetness) — lo que sí importa

En SnowRunner el barro «mojado» que **sí** penaliza no es la lluvia del cielo, sino la **máscara de wetness** que el autor pintó en el editor:

> *«The wetter the surface, the stronger the vehicle will get stuck in it, even if the mud is not painted in this area.»*  
> — [Saber — Wetness brush](https://expeditions-guides.saber.games/map_modding/creating_a_map/terrain/geometry_brushes_for_terrain/wetness/)

| Capa mapa | Efecto en barro |
|-----------|-----------------|
| **Tint** oscuro | Más viscoso (como en MudRunner) |
| **Wetness mask** | Más atasco, igual que tint |
| **Mud / Extrudes** | Profundidad y barro oculto |
| **Extrudes To Wetness** | Cuánto líquido se vuelve el barro oculto |

En **mapas de invierno**, wetness sobre asfalto/piedra puede comportarse como **hielo** (deslizamiento).

### Cómo reconocerlo en juego (sin editor)

- Suelo **brillante / oscuro** en charcos o orillas de río → suele ser wetness alta.
- Mismo «tipo» de barro en dos sitios y uno te traga mucho más → tint, wetness o extrusion distintos.
- Tramo que **empeora** cada vez que pasas → deformación persistente (ver abajo), no lluvia.

---

## Día, noche y tiempo

### Ciclo día / noche

El juego avanza el tiempo (acelerable en garaje/campamento). Los presets de iluminación están en `[media]\classes\daytimes\` del `.pak` (variantes `day__1`, `day__2`, `night`, `day_to_night`, etc.). Las variantes con sufijo **`a`** son la versión **nublada** del mismo momento del día — cambian luz y cielo, no la fórmula del barro.

| Preset (ej. US) | Momento |
|-----------------|---------|
| `night_us_*` | Noche |
| `night_to_day_us_*` | Amanecer |
| `day__1_us_*` / `day__1a_us_*` | Mañana (claro / nublado) |
| `day__2_us_*` / `day__2a_us_*` | Mediodía |
| `day__3_us_*` / `day__3a_us_*` | Tarde |
| `day_to_night_us_*` | Atardecer |

**No hay** parámetro documentado de «temperatura del barro» ni de secado nocturno. La idea real de *«por la noche baja la temperatura y el barro está más seco»* **no aplica** a la física de SnowRunner.

### Saltar la noche

Dormir hasta la mañana es **asistencia de jugabilidad** (modo estándar). No simula que el terreno se haya secado; solo cambia la hora y la luz.

### ¿Cuándo sí cambia el terreno con el tiempo?

| Mecanismo | ¿Existe? | Efecto |
|-----------|----------|--------|
| Secado térmico día/noche | **No** | — |
| Lluvia dinámica → más barro | **No** | — |
| **Deformación persistente** | **Sí** | Misma ruta → surcos más profundos, más difícil |
| Regeneración del mapa | **Sí** (lenta) | Con el tiempo el terreno puede «relajarse» en zonas poco transitadas |

La deformación persistente es lo más parecido a «el barro empeora si insisto» — pero por **pasadas repetidas**, no por el reloj o la lluvia.

---

## Reglas prácticas (CK1500 y MH9500)

### ¿Posponer una ruta?

| Situación | Recomendación |
|-----------|---------------|
| Empieza a llover | **No es obligatorio posponer** por física; decide por visibilidad/confort |
| Mismo barro tras 3–4 pasadas (surcos) | **Sí** — busca otra línea o winch; el mod no arregla surcos |
| MH9500 + semi cargado + barro | **Sí** — posponer o cambiar ruta; no es clima, es masa (Fase 3) |
| Noche en tramo nuevo difícil | Opcional posponer por **ver** el terreno**, no porque el barro esté más seco |
| Alaska / invierno, suelo mojado brillante | Cuidado **hielo** (wetness en superficies duras); cadenas ayudan (Fase 2) |

### Qué anotar en telemetría (Fase 5 + 7)

En `location_note` o notas de sesión, registrar:

1. Hora aproximada del juego (día / noche / amanecer)
2. ¿Lluvia visual? (sí/no — no debería cambiar v30)
3. ¿Primera pasada o surcos ya hechos?
4. Mismo vehículo, neumático y carga que sesiones Fase 2–3

---

## Protocolos telemetría Fase 7

Comparar **el mismo tramo** en dos condiciones de luz (sin cambiar carga ni neumático):

| ID | Vehículo | Qué validar |
|----|----------|-------------|
| `f7_barro_dia` | CK1500 | Barro mediodía, offroad + diff |
| `f7_barro_noche` | CK1500 | Misma ruta de noche |
| `mh_f7_barro_dia` | MH9500 | Barro mediodía, offroad + AWD + diff |
| `mh_f7_barro_noche` | MH9500 | Misma ruta de noche |

```powershell
python grabar_telemetria.py --list
python grabar_telemetria.py --protocol f7_barro_dia --map Michigan --location "mismo tramo F2"
python grabar_telemetria.py --protocol f7_barro_noche --map Michigan --location "mismo tramo F2 noche"
python comparar_telemetria.py telemetria/sesiones/<dia>.json telemetria/sesiones/<noche>.json
```

**Hipótesis a comprobar:** v30 día ≈ v30 noche (±ruido de conducción). Si difieren mucho, probablemente no es el «clima» sino surcos, línea distinta o carga distinta.

---

## Simulador Python

El sim (`simulador_ck1500.py`, `simulador_mh9500.py`) **no modela**:

- Lluvia dinámica
- Ciclo día/noche
- Secado térmico

Sí modela (Fase 4):

- `viscosity`, `mud_immersion`, `water_depth` como **proxy** de barro blando / húmedo / profundo
- Deformación aproximada vía `mud_immersion` que sube con patinaje

Para escenarios «barro muy húmedo» en sim puedes subir `viscosity` o `water_depth` en `SurfaceConfig` — eso calibra **zonas permanentemente húmedas** del mapa, no lluvia puntual.

```python
# Proxy de zona wetness alta (no lluvia dinámica)
SurfaceConfig("Barro charco", "mud", viscosity=6.0, water_depth=0.25)
```

Posible ampliación futura (opcional): factor `wetness: float = 1.0` en `SurfaceConfig` que multiplique resistencia en `step()` — solo si las pruebas Fase 7 muestran que necesitas rangos seco/húmedo **por zona**, no por hora.

---

## Qué puede tocar el mod (y qué no)

| Acción | ¿Viable desde mod camión? |
|--------|---------------------------|
| Neumáticos / motor / masa | **Sí** (Fases 1–3) |
| Cambiar wetness de Michigan | **No** — editor de mapas |
| Hacer que llueva más fuerte | **No** |
| Secado nocturno del barro | **No** |
| Elegir hora / dormir | **Sí** — decisión del jugador, no del mod |
| **Ralentizar el reloj del juego** | **Sí** — editando el save (no el `.pak` del camión) |

---

## Ralentizar el tiempo (reloj más lento / casi real)

Muchos jugadores notan lo mismo: **el camión va lento** (física, barro, diesel) pero **el reloj del juego corre rápido** — en poco rato real es de noche. Eso es independiente del mod CK1500/MH9500.

### Qué no hace el mod de vehículos

La velocidad del **reloj** (día/noche) **no está** en `gmc_9500.xml` ni en `initial.pak` del camión. Hay que tocar la **partida guardada** o usar **New Game+** con reglas de tiempo.

### Dónde está en el save

Ruta típica (Steam):

```
C:\Users\doski\Documents\My Games\SnowRunner\base\storage\<id_carpeta>\CompleteSave.cfg
```

Puede haber `CompleteSave1.cfg` … `CompleteSave3.cfg` (un slot por archivo). **Copia de seguridad** del `.cfg` antes de editar.

Busca en el texto (Ctrl+F):

| Campo | Función (comunidad / NG+) |
|-------|---------------------------|
| `TIME_SETTINGS` | Modo global: `0` default, `1` sin salto auto, `2` día largo, `3` noche larga, `4` solo día |
| `timeSettingsDay` | Multiplicador del **día** — **menor = día más largo** (`0.5` ≈ doble duración, `0.25` ≈ cuádruple) |
| `timeSettingsNight` | Igual para la **noche** |
| `gameTime` | Hora actual 0–23 (p. ej. `10.0` = 10:00) |
| `isAbleToSkipTime` | Debe ser `true` para saltar hora desde el mapa (tecla **T**) |

En **modo hardcore**, parte de la gente reporta que `TIME_SETTINGS` **no se lee del save**; solo `gameTime` o reglas del motor del juego. En partida normal / NG+ suele funcionar la edición.

Herramienta gráfica (opcional): [MrBoxik/SnowRunner-Save-Editor](https://github.com/MrBoxik/SnowRunner-Save-Editor) — incluye ajustes de tiempo.

### Perfiles recomendados

Empieza por **un perfil “lento”** y sube/baja según sensación. No saltes a “24 h reales = 1 día juego” de golpe.

| Perfil | `TIME_SETTINGS` | `timeSettingsDay` | `timeSettingsNight` | Efecto aproximado |
|--------|-----------------|-------------------|---------------------|-------------------|
| **Stock** | `0` | `1.0` | `1.0` | Reloj rápido (default) |
| **Lento (recomendado)** | `1` | `0.25` | `0.25` | Día y noche ~4× más largos |
| **Muy lento** | `1` | `0.1` | `0.1` | ~10× más lento |
| **Día largo, noche corta** | `2` | `0.25` | `1.0` | Más horas de luz para rutas |
| **Reloj casi parado** | `1` | `0.0` | `0.0` | El tiempo casi no avanza solo; cambias hora con **T** en el mapa |
| **Solo día** | `4` | `0.0` | `-1.0` | Sin noches (pierdes misiones que exigen noche) |

Valores de referencia: [Steam — time settings](https://steamcommunity.com/app/1465360/discussions/0/4353366080399314146/).

### ¿“Tiempo del todo real” (1 h real = 1 h en juego)?

**Técnicamente** puedes acercarte poniendo multiplicadores muy bajos (p. ej. `0.05` o menos), pero:

- SnowRunner **no fue diseñado** para eso; un contrato largo sería una sesión entera de horas reales.
- **No mejora** el barro ni el clima (Fase 7).
- Riesgo de **save corrupto o invisible** en el menú si combinas mal `TIME_SETTINGS`, `gameTime` y multiplicadores (prueba con backup).

**Recomendación práctica:** perfil **Lento** (`0.25` / `0.25`) o **Muy lento** (`0.1`). Si aún corre rápido, baja a `0.05`. Si quieres control total: `0.0` + saltos manuales con **T** en el mapa (6:00, mediodía, etc.).

### Pasos seguros

1. Cierra SnowRunner.
2. Copia `CompleteSave.cfg` → `CompleteSave.cfg.bak`.
3. Edita solo `timeSettingsDay` y `timeSettingsNight` (y `TIME_SETTINGS` a `1` si usas multiplicadores custom).
4. Comprueba que la partida **aparece** en el menú de carga.
5. Entra, mira el reloj 5–10 min reales conduciendo: ¿sigue siendo de día cuando antes ya era noche?
6. Si el save desaparece del menú, restaura el `.bak` y prueba otro combo (a veces `gameTime` entre 10–14 con ciertos `TIME_SETTINGS` da problemas — prueba `6.0` o `18.0`).

### Relación con el mod realista

| Aspecto | Reloj lento | Mod camión |
|---------|-------------|------------|
| Sensación “el juego va lento” | No cambia | **Sí** — torque, masa, ruedas |
| Noche llega antes de terminar ruta | **Mejora** con reloj lento | — |
| Barro más seco de noche | **No** | — |
| Consumo combustible por **hora juego** | Más lento el reloj → menos horas juego por minuto real | Mod ya bajó consumo XML |

Puedes usar **reloj lento + mod MH9500** sin conflicto: son capas distintas.

---

## Prueba en juego recomendada

1. Elige un barro **medio** en Michigan que ya uses en Fase 2 (marca inicio/fin).
2. Pasa **una vez** de día con CK1500 o MH9500 (config Fase 2) — anota sensación y opcionalmente `f7_barro_dia`.
3. **Sin dormir** (o avanzando solo unas horas), repite de noche — `f7_barro_noche`.
4. Dormir hasta la mañana y repetir **tercera** pasada el **mismo** día — si empeora, es **surcos**, no secado/humedad por reloj.
5. Opcional: activar lluvia visual (si el mapa la tiene) y repetir — si v30 no cambia, confirma que la lluvia es cosmética.

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `FASE-7.md` | Este documento |
| `FASE-4.md` | Terreno base (wetness, tint, extrusion) |
| `FASE-5.md` | Telemetría manual |
| `telemetria.py` | Protocolos `f7_*`, `mh_f7_*` |
| `personal.txt` | Objetivo original Fase 7 |

---

## Siguiente paso

1. **Reloj:** backup del save → probar `timeSettingsDay` / `timeSettingsNight` en `0.25` (perfil Lento arriba).
2. Una comparación día/noche en el **mismo** tramo (protocolos `f7_*` o `mh_f7_*`).
3. Si día ≈ noche → cierra Fase 7 para física; enfócate en surcos y elección de ruta.
4. Si quieres barro «más real por charco», en sim usa `viscosity`/`water_depth` altos para esa **zona**, no esperes lluvia dinámica.

---

## Validación con telemetría (Fases 5–6)

| | |
|--|--|
| **Protocolos** | `f7_barro_dia`, `f7_barro_noche`, `mh_f7_barro_dia`, `mh_f7_barro_noche` — **mismo tramo** |
| **Parámetros diseño** | Ninguno en mod vehículo; hora en `CompleteSave.cfg` o dormir en garaje |
| **CE / HUD mide** | `speed_kmh` día vs noche — deben ser **similares** (clima no cambia física barro) |
| **Estado CE** | Pendiente |
| **Futuro CE** | Anotar hora juego y «lluvia visual sí/no» en `notes`; `vel_y` si surcos profundos |
| **Criterio** | Si noche ≠ día en velocidad → surcos acumulados, línea distinta o carga distinta — **no** el mod |

```powershell
python grabar_telemetria.py --protocol f7_barro_dia --map Michigan
python importar_ce_csv.py --protocol f7_barro_dia --compare
python importar_ce_csv.py --protocol f7_barro_noche --compare
```

Ver **`FASE-5.md`** (protocolos) y **`FASE-6.md`** (CE).

---

*Documento Fase 7 — Entorno, clima y tiempo · SnowRunner realismo histórico.*
