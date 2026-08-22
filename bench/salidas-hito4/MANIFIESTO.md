# `bench/salidas-hito4/` — evidencia del hito 4 (capa MCP)

**Agente K3 · 22 de agosto de 2026 · 628 KB, todo texto.** No hay ninguna salida
binaria versionada: las conversiones de las pruebas se escriben en directorios
desechables y se borran. Los `.jsonl` son **logs**, que sí se versionan
(`CLAUDE.md` §6): son la trazabilidad de cada afirmación del informe.

**Entorno de todas las medidas:** Windows 10 Home 19045 · 12 núcleos · Python
3.11.9 · **Claude Code 2.1.239** · `mcp 2.0.0` en `.venv-mcp-filex` (venv propio;
`mcp~=1.8.0` y `mcp>=2.0.0` no coexisten) · sesión de escritorio remoto activa,
así que **todo SUCIA por estructura**. Sin GPU: nada de aquí la usa y no se tomó
el lock.

> ⚠ **El registro de motores cambió a media sesión.** Hasta las 08:58 había tres
> motores nativos (imagemagick, ghostscript, ffmpeg, **156 aristas**); a partir
> de esa hora, `filex/motor_contenedor.py` de K1 añadió LibreOffice, Pandoc y
> Calibre (**215 aristas**). **Todo lo medido entre 08:19 y 08:56 es con tres
> motores**; solo `h4_tokens_catalogo.json` (09:01) es con seis. Está dicho en
> cada fila, y la diferencia es en sí misma un resultado (§4 del informe).

---

## Arneses (se ejecutan; reproducen las cifras)

| Fichero | Qué mide | Orden exacta |
|---|---|---|
| `h4_tokens_catalogo.py` | Presupuesto de catálogo en tokens y **la curva de variantes** (qué cuesta cada regla de cobertura) | `.venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_tokens_catalogo.py` |
| `h4_arranque.py` | Arranque en frío por JSON-RPC crudo, n=9, con calentamiento | `.venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_arranque.py` |
| `h4_inspect_r8.py` | `inspect` en proceso vs staging (R8) vs `ffprobe`, n=15, **dos testigos de ruido** | `.venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_inspect_r8.py` |
| `h4_r4_latencia.py` | R4: ¿mismo mensaje **y misma latencia** para «prohibido» y «no existe»? n=201 | `.venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_r4_latencia.py` |
| `h4_ads_w9.py` | W9 (flujos alternativos) reproducido en el núcleo + el parche propuesto probado **en memoria** + regresión de las dos suites | `.venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_ads_w9.py` |
| `h4_spec_sonda.py` | Genera el `spec.json` para el **arnés compartido** `bench/scripts/mcp_probe_bin.py` (que **no se copió ni se tocó**) | ver abajo |
| `h4_cliente.py` | El experimento contra **Claude Code real**: ¿se abstiene fuera de cobertura? ¿llega el catálogo diferido? | `H4_N=3 .venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_cliente.py` |
| `h4_registrar_mcp.py` | Da de alta `filex` en la `.mcp.json` **del proyecto** | `.venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_registrar_mcp.py` |

La sonda va en dos pasos, y **el cliente es de otra era a propósito** (`mcp
1.29.0` contra un servidor `2.0.0`, que es la comprobación de §5.3):

```
.venv-mcp-filex/Scripts/python.exe bench/salidas-hito4/h4_spec_sonda.py
.venv-mcp-lite/Scripts/python.exe  bench/scripts/mcp_probe_bin.py \
    bench/salidas-hito4/h4_spec.json bench/salidas-hito4/h4_sonda.json
```

## Resultados

| Fichero | Contenido | Cifra de cabecera |
|---|---|---|
| `h4_tokens_catalogo.json` | Curva de 7 variantes de catálogo | **1.605 tok** (6 motores) · con 3 motores eran **1.503** · presupuesto declarado **1.200** |
| `h4_arranque.json` | n=9, con calentamiento | `initialize` **1.882 ms**, `tools/list` +2,3 ms |
| `h4_inspect_r8.json` | 5 ficheros × 3 rivales | `inspect` **0,21–0,59 ms** (no 0,04–0,06) |
| `h4_r4_latencia.json` | 6 celdas, n=201 | fuera-existe **6,5 µs** vs fuera-no-existe **6,4 µs** → razón **1,016** |
| `h4_ads_w9.json` | Antes / media corrección / corrección completa + regresión | lee 72 B y escribe 94 B por ADS con `veredicto: ok`; corregido, **61 pruebas en verde** |
| `h4_sonda.json` | 12 llamadas por el arnés compartido | `tokens_catalogo` **1.503** (confirma la medida propia por otra vía) |
| `h4_cliente.json` | 15 ejecuciones de `claude -p` | **15/15 aciertos**, **15/15 con catálogo diferido** |
| `h4_cli_*.jsonl` | Trazas `stream-json` de las 15 ejecuciones | son la prueba de **qué** herramienta actuó, no solo de que acertó |
| `h4_sonda_stderr.txt` | `stderr` del servidor durante la sonda | el aviso `SEP-2577` de `roots` deprecado |
| `h4_spec.json`, `h4_mcp_cliente.json` | Entradas generadas | — |
| `h4_roto.png` (110 B) | Fixture: PNG con firma válida y cuerpo basura | para el caso «el motor falla» |

## Lo que se generó y se borró

`arena-cliente/` (605 KB de copias del corpus), `tmp/`, `tmp-sonda/` y los
directorios de trabajo desechables de cada conversión. Ninguno se versiona: se
reconstruyen ejecutando los arneses de arriba.

## Lo que NO se tocó

`bench/scripts/mcp_probe_bin.py` (arnés compartido, usado tal cual con un spec
propio) · `bench/salidas-referencia/referencia.json` · `~/.claude.json` ·
`.venv-ai`, `.venv-paddle`, `.venv-mcp-md`, `.venv-marker` · `filex/nucleo.py`,
`motores.py`, `grafo.py`, `contrato.py`, `confinamiento.py` (el parche de W9 se
probó **en memoria**, no en disco) · `pruebas/test_hito1.py` · `.wslconfig`.
