# SnowRunner — mod realista (multi-camión)

Proyecto centrado en **parches XML → `initial.pak` → Steam** con datos reales. CE y API
**archivados** (`docs/CE-ARCHIVADO.md`).

## Estructura

```text
```

## Comandos habituales

```powershell
```

Documentación: **`docs/METODO-PAK.md`** · Pendientes: **`docs/PENDIENTES.md`**.

## Añadir un camión nuevo

1. `camiones/<id>/patches.py` + registro en `registry.py`.
2. `camiones/<id>/simulador.py` si hace falta sim propio.
3. `FASES.md` al formato Bandit (XML + prueba en juego F1–F3).
