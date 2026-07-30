# Fase 8: Remolques — **archivado** (inventario)

**Cambio (jul 2026):** el inventario automático de remolques (`auditar_remolques.py`,
`remolques_inventario.json`) **se eliminó** del flujo activo, alineado con CE archivado y
`simular_carga` eliminado.

## Enfoque vigente

| Sí                                                           | No (eliminado / archivado)          |
| ------------------------------------------------------------ | ----------------------------------- |
| No parchear `trailers/*.xml` ni `cargo_*.xml` globales       | `auditar_remolques.py`              |
| Bastidor / semi en **prueba F3 en juego** (`FASES.md`)       | `remolques_inventario.json`         |
| Masa chasis en `patches.py` (Fase 1)                         | Matriz inventario remolques en repo |
| Sim opcional: `trailer_mass_kg` en `camiones/*/simulador.py` | FASE-8 como gate de catálogo        |

Ver **`METODO-PAK.md`**.

## Qué se eliminó

| Archivo                     | Era                                            |
| --------------------------- | ---------------------------------------------- |
| `auditar_remolques.py`      | Extraía masas/acople de 6 remolques del `.pak` |
| `remolques_inventario.json` | Salida JSON del auditor                        |
| `test_auditar_remolques.py` | Tests del auditor                              |

## Referencia rápida (stock juego, sin re-auditar)

| Remolque scout                | Masa cuerpo principal | Acople  |
| ----------------------------- | --------------------- | ------- |
| `scout_trailer_offroad_cargo` | ~800 kg               | Drawbar |
| `scout_trailer_offroad`       | ~600 kg               | Drawbar |

| Semirremolque             | Masa vacía aprox. | Acople |
| ------------------------- | ----------------- | ------ |
| `semitrailer_sideboard_5` | ~4,3 t            | Saddle |
| Atajo sim MH9500          | 2500 kg tara      | —      |

Detalle histórico de distribución CoG / `cargo_*.xml`: commits anteriores o
`datos/comunidad/srinfo_trailers.json` (comunidad, no pipeline mod).

## Validación actual

- **CK1500 / Marshall:** remolque scout en barro (F3 en `camiones/*/FASES.md`).
- **MH9500 / T813:** semi cargado en mapa, no en inventario JSON.
- Si el combo camión+remolque va demasiado bien: motor/neumáticos del **camión** (Fases 1–2), no XML

  global del remolque.

*Fase 8 archivada — inventario remolques jul 2026.*
