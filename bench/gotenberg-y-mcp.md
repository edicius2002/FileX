# C35 — Gotenberg y C36 — inventario MCP

**MEDIDO:** CPU/Docker, sin GPU. La máquina convivió con la tanda GPU de otro agente: es una tanda **SUCIA** y no publica ms como medida.

## C35

La salud de Gotenberg fue HTTP 200, con Chromium y LibreOffice `up`. Se ejecutaron las siete entradas del banco de `hito5-documental.md` contra Gotenberg y el submotor equivalente de `filex-c13`. Una celda buena exige `HTTP 200 && bytes > 0` o `rc == 0 && bytes > 0`, respectivamente. El temporal se listó vacío antes, con siete subdirectorios durante, y se borró; `docker ps -a` no dejó ningún `filex-c35-*`.

| Entrada → PDF | Gotenberg | `filex-c13` | Veredicto |
|---|---:|---:|---|
| `docx` | 200 · 17 090 B | 0 · 22 820 B | ambos buenos |
| `epub` | **500 · 0 B** | 0 · 26 817 B | sólo C13 (Calibre) |
| `html` | 200 · 27 165 B | 0 · 32 807 B | ambos buenos |
| `md` | 200 · 6 907 B | 0 · 10 368 B | ambos buenos |
| `odt` | 200 · 26 784 B | 0 · 31 976 B | ambos buenos |
| `rtf` | 200 · 20 234 B | 0 · 21 412 B | ambos buenos |
| `txt` | 200 · 16 317 B | 0 · 16 940 B | ambos buenos |

**SUPERADA:** Gotenberg cubre **6/7** y `filex-c13` cubre **7/7**. No añade conversión sobre C13; pierde `epub→pdf`, donde la petición válida devuelve HTTP 500 y Calibre en C13 produce 26 817 B. El primer intento reveló dos defectos del arnés (nombre de salida de LibreOffice y `index.html` obligatorio para Markdown); la segunda y última pasada los corrigió. EPUB mantuvo 500: es el resultado del motor, no una ausencia de entrada.

**PENDIENTE:** latencia limpia n≥9 con testigos. Gotenberg exige un servicio HTTP vivo; C13 usa contenedor efímero, red nula, `--init`, nombre único y `timeout -k 5 45` dentro. Esta tanda no convierte esa diferencia operativa en ms.

## C36

### El recuento correcto

**MEDIDO:** §13 de `hito4-mcp.md` enumera **nueve**, no ocho. Dos ya se cerraron por otra vía: W9 (commit `c2f6a59`, reproducido ahora: 2/2 pruebas ADS pasan) y `job cancelar` (C34/N10, `bench/cancelacion-y-servicio.md`). Quedan siete pendientes reales; la fila C36 que dice «ocho» está desactualizada.

| Pendiente de §13 | Estado actual |
|---|---|
| Aplicar W9 | **CERRADO**: `nombre_seguro` está en confinamiento y resolver; 2/2 ADS verdes |
| Sonnet y n≥10 | PENDIENTE |
| Sustituir `roots` 2026-07-28 | PENDIENTE de portar: `Resolve(ListRoots)` es la vía moderna, pero no puede ser dependencia dura si el cliente no declara roots |
| Cancelar el árbol | **CERRADO** por C34/N10 |
| Emisión real de `roots/list_changed` | PENDIENTE; headless sólo observó la capacidad |
| Catálogo con hito 5 completo | **MEDIDO** abajo; Gotenberg/sidecar aún no están registrados en FileX |
| Subsunción automática | PENDIENTE |
| Idempotencia ante doble `Resolve` | PENDIENTE |
| `convert` denegado que gasta `job_id` | PENDIENTE |

**MEDIDO:** el registro real cargado tiene seis motores del hito 5: 215 aristas, 30 orígenes, 29 destinos, cinco herramientas y **1 605 tokens** (`o200k_base`; sólo seis tokens son nombres). Es repetición sobre el árbol actual, no extrapolación. Gotenberg y el sidecar siguen fuera del registro de `FileX`, por lo que su curva final no se inventa.

**MEDIDO/PENDIENTE:** `bench/sdk-mcp-capacidades.md` identifica el sustituto de `session.list_roots()` en 2026-07-28: `MCPServer` + `Resolve(ListRoots)`. La vía dura aborta sin capacidad roots (`-32021`), opuesta a R13; falta ejercitar la petición condicional antes de cambiar el servidor actual.

## Verificación

- W9: `pruebas/test_hito4.py::W9_FlujosAlternativos` → **2 passed** (Python Windows `.venv-mcp-filex`).
- C35: 7 celdas; C13 7/7 buenas, Gotenberg 6/7; temporal borrado.
- C36: 1 605 tokens, seis motores, 215 aristas.
- `py_compile` de ambos arneses y `git diff --check`: pasan.

## Salidas

Ver `bench/salidas-gotenberg-mcp/MANIFIESTO.md`. No se versionaron binarios.
