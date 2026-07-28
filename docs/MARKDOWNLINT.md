# Markdownlint — reglas del proyecto

Referencia oficial (todas las reglas, parámetros y ejemplos):
[DavidAnson/markdownlint —
Rules.md](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md)

## Configuración

| Archivo                                             | Rol                                                    |
| --------------------------------------------------- | ------------------------------------------------------ |
| [`.markdownlint.json`](../.markdownlint.json)       | Reglas para **cualquier** `.md` del repo               |
| [`.vscode/settings.json`](../.vscode/settings.json) | Lint en Cursor/VS Code (`onType`, todos los `**/*.md`) |
| [`fix_markdownlint.py`](../fix_markdownlint.py)     | Auto-corrección parcial en lote                        |

Por defecto `"default": true` → **todas** las reglas activas salvo parámetros abajo.

| Regla | Config proyecto                               | Motivo                                     |
| ----- | --------------------------------------------- | ------------------------------------------ |
| MD013 | `line_length: 100`, sin tablas/código/títulos | Prosa técnica larga                        |
| MD024 | `siblings_only: true`                         | `#### Comentarios` repetido por vehículo   |
| MD055 | `leading_and_trailing`                        | Pipe al inicio y fin de cada fila de tabla |
| MD060 | `style: aligned`                              | Columnas alineadas                         |

## MD013 — longitud de línea

Regla: [MD013 — line
length](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md#md013---line-length)

| Parámetro     | Valor en este repo                  |
| ------------- | ----------------------------------- |
| `line_length` | **100** (igual que Ruff)            |
| `code_blocks` | `false` — no partir fences          |
| `tables`      | `false` — no partir tablas          |
| `headings`    | `false` — títulos pueden ser largos |

Solo revisa **prosa** (párrafos normales). Excepción oficial: línea sin espacios tras el límite
(URLs largas) no se parte.

`fix_markdownlint.py` hace *word wrap* en párrafos > 100 caracteres. No toca listas, tablas, `>`,
encabezados ni bloques de código.

## MD036 — énfasis en lugar de título

Regla: [MD036 — emphasis used instead of a
heading](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md#md036---emphasis-used-instead-of-a-heading)

Dispara cuando un **párrafo de una sola línea** es solo texto enfatizado (`**negrita**`,
`__negrita__`, `*cursiva*`, `_cursiva_`).

| Viola MD036                        | No viola                              |
| ---------------------------------- | ------------------------------------- |
| `**Comentarios**` solo en la línea | `**Enfoque:** texto en la misma línea |
| `**Sesiones CE**`                  | `**Título.**` con puntuación final    |
| `_Otra sección_`                   | Listas `* item`                       |

`fix_markdownlint.py` convierte a encabezado ATX:

- bajo `#` → `## Título`
- bajo `##` (vehículo) → `#### Título` (evita saltos MD001 y duplicados MD024 con `siblings_only`)

Corregir a mano si el énfasis es intencional (no es sección).

## Índice de reglas (MD001–MD060)

| ID    | Alias                            | Tags        | Auto-fix script    |
| ----- | -------------------------------- | ----------- | ------------------ |
| MD001 | heading-increment                | headings    | —                  |
| MD003 | heading-style                    | headings    | —                  |
| MD004 | ul-style                         | bullet, ul  | —                  |
| MD005 | list-indent                      | bullet, ul  | —                  |
| MD007 | ul-indent                        | bullet, ul  | —                  |
| MD009 | no-trailing-spaces               | whitespace  | **sí**             |
| MD010 | no-hard-tabs                     | whitespace  | —                  |
| MD011 | no-reversed-links                | links       | —                  |
| MD012 | no-multiple-blanks               | whitespace  | **sí**             |
| MD013 | line-length                      | line_length | **sí** (prosa)     |
| MD014 | commands-show-output             | code        | —                  |
| MD018 | no-missing-space-atx             | headings    | —                  |
| MD019 | no-multiple-space-atx            | headings    | —                  |
| MD020 | no-missing-space-closed-atx      | headings    | —                  |
| MD021 | no-multiple-space-closed-atx     | headings    | —                  |
| MD022 | blanks-around-headings           | headings    | **sí**             |
| MD023 | heading-start-left               | headings    | —                  |
| MD024 | no-duplicate-heading             | headings    | config             |
| MD025 | single-title                     | headings    | —                  |
| MD026 | no-trailing-punctuation          | headings    | al convertir MD036 |
| MD027 | no-multiple-space-blockquote     | blockquote  | —                  |
| MD028 | no-blanks-blockquote             | blockquote  | —                  |
| MD029 | ol-prefix                        | ol          | —                  |
| MD030 | list-marker-space                | ol, ul      | —                  |
| MD031 | blanks-around-fences             | code        | **sí**             |
| MD032 | blanks-around-lists              | lists       | **sí**             |
| MD033 | no-inline-html                   | html        | activa             |
| MD034 | no-bare-urls                     | links       | —                  |
| MD035 | hr-style                         | hr          | —                  |
| MD036 | no-emphasis-as-heading           | emphasis    | **sí**             |
| MD037 | no-space-in-emphasis             | emphasis    | —                  |
| MD038 | no-space-in-code                 | code        | —                  |
| MD039 | no-space-in-links                | links       | —                  |
| MD040 | fenced-code-language             | code        | **sí**             |
| MD041 | first-line-heading               | headings    | —                  |
| MD042 | no-empty-links                   | links       | —                  |
| MD043 | required-headings                | headings    | —                  |
| MD044 | proper-names                     | spelling    | —                  |
| MD045 | no-alt-text                      | images      | —                  |
| MD046 | code-block-style                 | code        | —                  |
| MD047 | single-trailing-newline          | blank_lines | **sí**             |
| MD048 | code-fence-style                 | code        | —                  |
| MD049 | emphasis-style                   | emphasis    | —                  |
| MD050 | strong-style                     | emphasis    | —                  |
| MD051 | link-fragments                   | links       | —                  |
| MD052 | reference-links-images           | links       | —                  |
| MD053 | link-image-reference-definitions | links       | —                  |
| MD054 | link-image-style                 | links       | —                  |
| MD055 | table-pipe-style                 | table       | config             |
| MD056 | table-column-count               | table       | —                  |
| MD058 | blanks-around-tables             | table       | **sí**             |
| MD059 | descriptive-link-text            | links       | —                  |
| MD060 | table-column-style               | table       | **sí**             |

Nota: no existen MD002, MD015–MD017 ni MD057 en markdownlint actual.

## Comandos

```powershell
```

## Flujo recomendado

1. Escribir/editar `.md` → avisos en Cursor (extensión markdownlint).
2. `python fix_markdownlint.py` → corrige lo automático.
3. Revisar avisos restantes a mano (MD013 en prosa, MD051 fragmentos, etc.).
