# SnowRunner — GMC MH9500 (mod realista, 8 fases)

Ajuste del **GMC MH9500** (`gmc_9500.xml`). Metodología: `docs/FASE-1.md` … `docs/FASE-8.md`.

---

## Estado (junio 2026)

| Fase | Tema | Estado |
|------|------|--------|
| 1–4 | Motor, neumáticos, carga semi, terreno | Hecho (XML + sim) |
| 5 | Telemetría HUD | Protocolos `mh_*` |
| 6 | Havok / CE | Pipeline listo; **re-grabar** con terreno+carga actual |
| 7–8 | Clima, remolques | Doc `docs/FASE-7.md`, `docs/FASE-8.md` |
| Prueba juego | Michigan | En curso — va bien |

Sesiones CE antiguas (`ce_mh_*` sin `contact_avg`): archivadas en `telemetria/sesiones/_archivo/`.

---

## Telemetría (Fases 5–6)

```powershell
python grabar_ce.py --probe
grabar_telemetria.bat
python importar_ce_csv.py --auto --compare
```

| ID | Cuándo | Auto si… |
|----|--------|----------|
| `mh_f1_asfalto` | Asfalto vacío | terreno `hard`, vacío |
| `mh_f2_barro_offroad` | Barro AWD+diff | terreno `mud`, vacío |
| `mh_f3_semi` | Semi cargado barro | `payload_kg` &gt; 300 o `trailer_cargado` |
| `mh_f7_barro_dia` / `noche` | Misma ruta | manual `--protocol` |

Masa vacía CE: **7500 kg**. ID juego: `s_gmc_9500` / `s_gmc9500`.

---

## Qué esperar del mod

| Situación | Comportamiento |
|-----------|----------------|
| Barro highway RWD | Atasco o ~0 km/h |
| Barro offroad + AWD + diff | Avance lento |
| Semi ~12 t en barro | Prácticamente inmóvil |

```powershell
python -m camiones.mh9500.simulador
```

---

## Aplicar

```powershell
python apply_mod.py --vehicle mh9500
python verify_pak.py
python -m unittest camiones.mh9500.test -v
```

---

## Fase 6 — memoria

| | |
|--|--|
| Singleton | `SnowRunner.exe+2A8EDD8` (build 2026-06-25) |
| Logger | `grabar_ce.py` (recomendado) o `TelemetryLogger.lua` |
| Terreno | `terrain_kind`, `contact_avg` por rueda |
| Carga | `payload_kg`; semi → escenario `semi_cargado` en auto |
| Doc | `docs/FASE-6.md`, `cheat_engine/README.md` |

---

## Checklist

1. [x] Mod + `verify_pak.py` OK
2. [ ] Barro highway RWD — atasco
3. [ ] AWD + offroad en barro
4. [ ] CE `mh_f2_barro_offroad` con `--auto`
5. [ ] Semi cargado — `mh_f3_semi` (auto si payload detectado)

---

## Comandos rápidos

```powershell
python -m camiones.mh9500.simulador
python apply_mod.py
python -m unittest camiones.mh9500.test -v
grabar_telemetria.bat
```
