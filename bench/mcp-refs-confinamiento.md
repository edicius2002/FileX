# Confinamiento del sistema de ficheros y mensaje de error al modelo

**Ejecución medida de `servers/src/filesystem` (referencia oficial del protocolo MCP) y de `kordoc`.**
Fecha: 20 de agosto de 2026. Máquina: Windows 10 Home 19045, 12 núcleos, Node v22.23.2, npm 10.9.8,
cliente MCP = `.venv-mcp-md/Scripts/python.exe` (mcp 1.8.1 + tiktoken). Sin GPU.

Datos crudos: `bench/salidas-mcp-refs/confinamiento/`.
Arnés: `bench/scripts/mcp_probe_bin.py` (**no modificado**) + una variante propia declarada en §1.4.

> **Convención del proyecto.** Cada afirmación va marcada **MEDIDO** (hay una salida literal en
> `salidas/*.json` que la respalda) o **PENDIENTE** (no se ha ejecutado; queda abierto).

---

## 0. Resumen ejecutivo

| Pregunta abierta | Respuesta medida |
|---|---|
| ¿Para `filesystem` la travesía de directorios? | **Sí, los 11 vectores de travesía y ruta absoluta.** Cero escapes. **MEDIDO** |
| ¿Es `filesystem` un oráculo de existencia? | **Fuera de la raíz, NO** — (b) y (c) dan el mismo mensaje palabra por palabra. **Dentro** de la raíz, **SÍ**. El análisis de código lo daba por confirmado sin matiz: se **refuta parcialmente**. **MEDIDO** |
| ¿Filtra la lista blanca completa? | **Sí, en los tres mensajes de denegación.** Y además filtra la ruta **resuelta fuera del sandbox** cuando hay un enlace. **MEDIDO** |
| ¿Se reproduce el TOCTOU? | **No, en 52 800 intentos por la superficie MCP real**, ni con la ventana ensanchada artificialmente. Los tests del propio repo que "demuestran" la carrera **no pasan por `validatePath`**. **MEDIDO** — ver §4 |
| ¿Huecos específicos de Windows? | **Ninguno que conceda acceso.** Cinco **falsos negativos** que deniegan rutas legítimas (minúsculas, `\\?\`, 8.3, `/d/…`, `/mnt/d/…`). Un caso que **sí concede**: los flujos de datos alternativos (ADS) dentro de la raíz. **MEDIDO** |
| ¿Es `kordoc` un oráculo de existencia? | **Sí, y sin matices**: (b) y (c) dan mensajes distintos incluso fuera de `KORDOC_ROOT`. Es **peor** que `filesystem` en este punto exacto. **MEDIDO** |
| ¿Divergen la CLI y el MCP de `kordoc`? | **Sí, y en seguridad**: `KORDOC_ROOT` **solo lo aplica la superficie MCP**. La CLI lee fuera de la raíz sin objetar. **MEDIDO** |

---

## 1. Qué se instaló y cómo se lanzó cada servidor

### 1.1 `@modelcontextprotocol/server-filesystem`

**No se construyó desde el clon.** Se usó el paquete publicado, que es lo que instalaría un usuario real.

```sh
npx -y @modelcontextprotocol/server-filesystem <RAÍZ_PERMITIDA>
```

- Versión instalada por npx: **2026.7.10** (`_npx/a3241bba59c344f5/node_modules/@modelcontextprotocol/server-filesystem/package.json`). **MEDIDO**
- El clon local (`repos/mcp-refs/servers`, git `599dafc`) declara `"version": "0.6.3"` en
  `src/filesystem/package.json` — número interno del subpaquete, no la versión publicada. **MEDIDO**
- **El `dist/` publicado y el `lib.ts` del clon coinciden literalmente** en los cuatro mensajes de
  error de `validatePath` (`dist/lib.js:67,75,88,93` ↔ `lib.ts:110,119,131,135`), así que las citas
  `fichero:línea` del análisis de código son válidas sobre lo ejecutado. **MEDIDO**
- Identidad que anuncia por protocolo: `name="secure-filesystem-server"`, `version="0.2.0"`,
  `protocolVersion="2024-11-05"`, `instructions=null`. **MEDIDO** (`salidas/01_ataques.json`)
- Arranque en frío (spawn → `initialize` completo): **6 305,6 ms** la primera vez
  (843,5 spawn + 5 462,1 handshake, más 1 792,8 ms de `tools/list`); **2 921,9 ms** con la caché de
  npx caliente. **MEDIDO**
- Catálogo: **14 herramientas, 3 360 tokens, 14/14 anotadas.** Sin `prompts` ni `resources`
  (`McpError: Method not found` en ambos). **MEDIDO**

`stderr` completo al arrancar, en **todos** los lanzamientos (`salidas/stderr_fs_*.txt`):

```
Secure MCP Filesystem Server running on stdio
Failed to request initial roots from client: MCP error -32600: List roots not supported
```

El cliente del arnés no declara la capacidad `roots`; el servidor lo intenta igualmente, falla, **lo
escribe a stderr y sigue** con la lista blanca de argumentos. El modelo nunca ve ese mensaje. **MEDIDO**

Único fallo de arranque encontrado (con `--help`, que interpreta como directorio):

```
Warning: Cannot access directory D:\Work\research\FileX\--help, skipping
Error: None of the specified directories are accessible
```

**MEDIDO** — es fail-closed: sin ninguna raíz accesible, aborta.

### 1.2 `kordoc`

```sh
npx -y -p kordoc@4.9.0 kordoc-mcp          # servidor MCP por stdio
npx -y -p kordoc@4.9.0 kordoc --silent <f> # CLI
```

- Versión **4.9.0**, la misma del clon `repos/mcp-refs/kordoc/package.json`. **MEDIDO**
- Identidad: `name="kordoc"`, `version="4.9.0"`, `protocolVersion="2024-11-05"`, `instructions=null`. **MEDIDO**
- Arranque en frío: **5 537,4 ms** la primera vez; **2 483,3 ms** en caliente. **MEDIDO**
- Catálogo: **15 herramientas, 7 759 tokens, 0 anotadas.** **MEDIDO**
- Entorno común de las pruebas: `KORDOC_OFFLINE=1` (mata la descarga de modelos de OCR, que si no
  intentaría bajar ~18 MB de huggingface). En §5 se aprovecha para provocar un error real.
- `stderr` al arrancar: `[kordoc-mcp] 제한 모드: offline` (una línea). **MEDIDO**

Para la CLI se invocó el `dist/cli.js` de la caché de npx directamente con `node`, para no pagar el
arranque de `npx` en cada llamada:
`node C:/Users/krato/AppData/Local/npm-cache/_npx/f8f6ac61187f28ad/node_modules/kordoc/dist/cli.js`.

### 1.3 El árbol de pruebas

`bench/salidas-mcp-refs/confinamiento/sandbox/`:

```
permitido/            <- ÚNICA raíz declarada en la lista blanca
  dentro.txt          "CONTENIDO PERMITIDO OK 12345"
  dentro.txt:oculto   ADS: "ADS_OCULTO_DENTRO_777"
  sub/anidado.txt     "SUBCARPETA PERMITIDA OK"
prohibido/            <- hermana, NO declarada
  secreto.txt         "SECRETO_PROHIBIDO_ABCDEF contenido que el modelo no debe ver"
  secreto.txt:oculto  ADS: "ADS_OCULTO_PROHIBIDO_888"
permitido_secreto/    <- hermana con PREFIJO COMÚN, NO declarada
  trampa.txt          "PREFIJO_ENGANYOSO_XYZ …"
kordoc/               <- entradas para §5 (ok.pdf, truncado.pdf, falso.pdf, vacio.docx, …)
../senuelo_fuera.txt  <- señuelo fuera del sandbox, dentro del directorio de salidas
```

Los enlaces simbólicos y la unión (*junction*) se crearon y se borraron por prueba; el árbol se
entrega **sin enlaces** para que sea portable. Comandos exactos para recrearlos, todos sin privilegios
de administrador porque el Modo Desarrollador de Windows está activo en esta máquina
(`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock\AllowDevelopmentWithoutDevLicense = 1`,
**MEDIDO**):

```bat
cd sandbox\permitido
mklink    link_interno.txt sub\anidado.txt
mklink    link_fuera.txt   ..\prohibido\secreto.txt
mklink    link_win.txt     C:\Windows\win.ini
mklink /J junc_fuera       ..\prohibido
```

Los ADS se crearon con PowerShell: `Set-Content -Path … -Stream 'oculto' -Value …`.

### 1.4 Ficheros generados y la variante del arnés

| Fichero | Qué es |
|---|---|
| `confinamiento/gen_specs.py` | Genera los spec de `filesystem` (ataques, escritura, symlinks previos). Se usa un script y no *heredocs* porque las rutas Windows con `\` se destrozan al escaparse en sh |
| `confinamiento/gen_specs_kordoc.py` | Ídem para kordoc |
| `confinamiento/toctou_probe.py` | **VARIANTE declarada del arnés.** `bench/scripts/mcp_probe_bin.py` ejecuta los pasos en serie y no permite mutar el disco *entre* la validación y la lectura, ni lanzar llamadas concurrentes. Ambas cosas son imprescindibles para §4. El arnés original **no se ha tocado** |
| `salidas/01_ataques.json` … `06_83.json` | Salidas crudas del arnés |
| `salidas/07_kordoc_cli_vs_mcp.txt` | Transcripción literal de la comparación CLI ↔ MCP |
| `salidas/stderr_*.txt` | Copia no ignorada por git de los `logs/*.log` |

Reproducción:

```sh
PY=D:/Work/research/FileX/.venv-mcp-md/Scripts/python.exe
cd bench/salidas-mcp-refs/confinamiento
$PY gen_specs.py && $PY gen_specs_kordoc.py
$PY ../../scripts/mcp_probe_bin.py specs/01_ataques.json          salidas/01_ataques.json
$PY ../../scripts/mcp_probe_bin.py specs/02_escritura.json        salidas/02_escritura.json
$PY ../../scripts/mcp_probe_bin.py specs/03_symlinks_previos.json salidas/03_symlinks_previos.json
$PY ../../scripts/mcp_probe_bin.py specs/04_kordoc_errores.json   salidas/04b_kordoc_errores.json
$PY ../../scripts/mcp_probe_bin.py specs/05_kordoc_root.json      salidas/05_kordoc_root.json
$PY ../../scripts/mcp_probe_bin.py specs/06_83.json               salidas/06_83.json
$PY toctou_probe.py salidas/04_toctou.json          # A,C,B,B2 — ~50 s
```

### 1.5 Licencias — corrección

**`servers` NO es MIT.** `repos/mcp-refs/servers/LICENSE` abre así (**MEDIDO**, cita literal):

> *The MCP project is undergoing a licensing transition from the MIT License to the Apache License,
> Version 2.0 ("Apache-2.0"). All new code and specification contributions to the project are licensed
> under Apache-2.0. […] Contributions made by authors who originally licensed their work under the MIT
> License and who have not yet granted explicit permission to relicense remain licensed under the MIT
> License.*

y `src/filesystem/package.json` declara `"license": "SEE LICENSE IN LICENSE"` — **no** `"MIT"`.
En todo este informe se escribe **MIT/Apache-2.0 (transición)**. Consecuencia práctica para FileX:
copiar código de `filesystem` obliga a **preservar los avisos de copyright y de licencia y a adjuntar
un `NOTICE`** (Apache-2.0 §4), cosa que MIT no exigía. Es una obligación real, no un tecnicismo:
afecta al empaquetado de FileX.

**`kordoc` sí es MIT** (`repos/mcp-refs/kordoc/LICENSE`: `MIT License / Copyright (c) 2026 chrisryugj`). **MEDIDO**

---

## 2. Tabla de ataques contra `servers/src/filesystem`

Raíz declarada, en todos los casos salvo los de la §2.4:

```
D:\Work\research\FileX\bench\salidas-mcp-refs\confinamiento\sandbox\permitido
```

En las tablas se abrevia esa raíz como `«P»` y su padre `…\sandbox` como `«S»`; los mensajes
literales sí llevan la ruta entera cuando aporta algo. `list_allowed_directories` devuelve, sin que
nadie lo pregunte:

```
Allowed directories:
D:\Work\research\FileX\bench\salidas-mcp-refs\confinamiento\sandbox\permitido
```

**MEDIDO.** Es deliberado (`index.ts:702`): la referencia **publica** su lista blanca al modelo.

### 2.1 Controles y travesía

| # | Vector | Petición exacta (`read_text_file` salvo nota) | Resultado | Mensaje literal al modelo | Veredicto |
|---|---|---|---|---|---|
| A1 | Control: existe y está dentro | `«P»\dentro.txt` | **CONCEDIDO** | `CONTENIDO PERMITIDO OK 12345` | Correcto |
| A2 | Control: subcarpeta | `«P»\sub\anidado.txt` | **CONCEDIDO** | `SUBCARPETA PERMITIDA OK` | Correcto |
| T1 | Travesía relativa, `\` | `..\prohibido\secreto.txt` | **DENEGADO** | `Access denied - path outside allowed directories: «S»\prohibido\secreto.txt not in «P»` | **Para el ataque.** Nótese que la ruta relativa se resuelve contra la raíz permitida (`lib.ts:76-96`) y luego se deniega |
| T2 | Travesía relativa, `/` | `../prohibido/secreto.txt` | **DENEGADO** | idéntico a T1 | Para |
| T3 | Absoluta con `..` intercalado | `«P»\..\prohibido\secreto.txt` | **DENEGADO** | idéntico a T1 | Para |
| T4 | Cadena larga relativa | `..\..\..\..\..\..\..\..\Windows\win.ini` | **DENEGADO** | `Access denied - path outside allowed directories: D:\Windows\win.ini not in «P»` | Para |
| T5 | Cadena larga absoluta | `«P»\..\..\..\..\..\..\..\..\Windows\win.ini` | **DENEGADO** | idéntico a T4 | Para |
| T6 | Señuelo fuera del sandbox | `..\..\senuelo_fuera.txt` | **DENEGADO** | `Access denied - path outside allowed directories: …\confinamiento\senuelo_fuera.txt not in «P»` | Para |

**Contraste obligatorio con `bench/mcp-ergonomia.md` §6.1:** ahí se midió que `..\..\` **funciona en
markitdown-mcp y en docling-mcp**, y que markitdown llegó a devolver el contenido de `C:\Windows\win.ini`.
Aquí **ninguna de las ocho variantes de travesía pasa**. **MEDIDO.**

### 2.2 Ruta absoluta fuera de la raíz

| # | Vector | Petición | Resultado | Mensaje literal | Veredicto |
|---|---|---|---|---|---|
| R1 | Absoluta a fichero real del sistema | `C:\Windows\win.ini` | **DENEGADO** | `Access denied - path outside allowed directories: C:\Windows\win.ini not in «P»` | Para. **No se pudo leer `win.ini` por ningún vector** |
| R2 | Absoluta a unidad sin ese árbol | `D:\Windows\win.ini` | **DENEGADO** | `Access denied - path outside allowed directories: D:\Windows\win.ini not in «P»` | Para. **Idéntico a R1 aunque `D:\Windows` no existe** — ver §3 |
| R3 | Absoluta al señuelo | `…\confinamiento\senuelo_fuera.txt` | **DENEGADO** | `Access denied - path outside allowed directories: …\senuelo_fuera.txt not in «P»` | Para |
| X2 | Otra herramienta, misma frontera | `get_file_info` sobre `«S»\prohibido\secreto.txt` | **DENEGADO** | mismo mensaje | Para |
| X3 | Árbol sobre el padre de la raíz | `directory_tree` sobre `«S»` | **DENEGADO** | `Access denied - path outside allowed directories: «S» not in «P»` | Para |
| X5 | Ruta binaria | `read_media_file` sobre `«S»\prohibido\secreto.txt` | **DENEGADO** | mismo mensaje | Para. **Las 14 herramientas comparten `validatePath`** |

### 2.3 Prefijo engañoso — el clásico `startsWith` sin separador

| # | Vector | Petición | Resultado | Mensaje literal | Veredicto |
|---|---|---|---|---|---|
| P1 | Hermano con prefijo común | `«S»\permitido_secreto\trampa.txt` | **DENEGADO** | `Access denied - path outside allowed directories: «S»\permitido_secreto\trampa.txt not in «P»` | **Para.** Es el `+ path.sep` de `path-validation.ts:84` haciendo su trabajo |
| P2 | Listar el hermano | `list_directory` sobre `«S»\permitido_secreto` | **DENEGADO** | mismo mensaje sin el fichero | Para |
| P3 | Misma ruta por concatenación literal | `«P»_secreto\trampa.txt` | **DENEGADO** | mismo mensaje que P1 | Para |

**Este es el vector que un `path.startswith(raiz)` ingenuo en Python concedería.** La referencia lo
para porque compara `normalizedPath.startsWith(normalizedDir + path.sep)`. **MEDIDO.**

### 2.4 Peculiaridades de Windows

Aquí es donde la referencia, pensada sobre todo para POSIX, se rompe — pero se rompe **hacia el lado
seguro** en todos los casos salvo uno.

| # | Vector | Petición | Resultado | Mensaje literal | Veredicto |
|---|---|---|---|---|---|
| W1 | **Mayús/minús: todo en minúsculas** | `d:\work\research\filex\…\permitido\dentro.txt` | **DENEGADO** | `Access denied - path outside allowed directories: d:\work\research\filex\…\dentro.txt not in D:\Work\…\permitido` | **FALSO NEGATIVO.** Deniega una ruta legítima. Windows es case-insensitive; `path-validation.ts:66,84` compara case-sensitive |
| W2 | Solo la unidad en minúscula | `d:\Work\…\permitido\dentro.txt` | **CONCEDIDO** | `CONTENIDO PERMITIDO OK 12345` | Correcto — `path-utils.ts:98-100` capitaliza **solo** la letra de unidad. Es el único punto donde se normaliza el caso |
| W3 | Barras normales, dentro | `D:/Work/…/permitido/dentro.txt` | **CONCEDIDO** | contenido | Correcto |
| W4 | Barras normales, fuera | `D:/Work/…/prohibido/secreto.txt` | **DENEGADO** | `…: «S»\prohibido\secreto.txt not in «P»` (normalizado a `\`) | Para |
| W5 | **Prefijo `\\?\`, dentro de la raíz** | `\\?\D:\Work\…\permitido\dentro.txt` | **DENEGADO** | `Access denied - path outside allowed directories: \\?\D:\Work\…\dentro.txt not in D:\Work\…\permitido` | **FALSO NEGATIVO.** El `\\?\` cae en la rama UNC de `path-utils.ts:66-78` y sobrevive a la normalización, así que ya no empieza por `D:\` |
| W6 | Prefijo `\\?\`, fuera | `\\?\D:\…\prohibido\secreto.txt` | **DENEGADO** | análogo | Para |
| W7 | **`\\?\` + `..`** (Win32 **no** normaliza `..` tras `\\?\`) | `\\?\D:\…\permitido\..\prohibido\secreto.txt` | **DENEGADO** | `…: \\?\D:\…\prohibido\secreto.txt not in «P»` | **Para**, porque `path.normalize` de Node **sí** colapsa el `..` aunque Win32 no lo haría. El colapso léxico previo salva el caso |
| W8 | Espacio de dispositivos `\\.\` | `\\.\D:\…\prohibido\secreto.txt` | **DENEGADO** | `…: \\.\D:\…\prohibido\secreto.txt not in «P»` | Para |
| W9 | **ADS dentro de la raíz** | `«P»\dentro.txt:oculto` | **CONCEDIDO** | `ADS_OCULTO_DENTRO_777` | **HUECO REAL.** El flujo alternativo se lee. La ruta pasa el prefijo (`…\permitido\dentro.txt:oculto` empieza por `…\permitido\`) y `realpath` de Node lo acepta. **Los bytes devueltos NO son los del fichero validado** |
| W10 | ADS sobre fichero prohibido | `«S»\prohibido\secreto.txt:oculto` | **DENEGADO** | `…: «S»\prohibido\secreto.txt:oculto not in «P»` | Para — el fichero base ya está fuera, así que el ADS no sirve de escape |
| W11 | Punto final (Win32 lo recorta) | `«P»\dentro.txt.` | **DENEGADO** | `ENOENT: no such file or directory, open '«P»\dentro.txt.'` | Node no aplica el recorte de Win32. Sin escape, pero es un **oráculo dentro de la raíz** (§3) |
| W12 | Espacio final | `«P»\dentro.txt ` | **DENEGADO** | `ENOENT: … open '«P»\dentro.txt '` | Ídem |
| W13 | Nombre reservado `NUL` | `«P»\NUL` | **DENEGADO** | `ENOENT: … open '«P»\NUL'` | Node no abre el dispositivo. **Cero filtros de nombres reservados en el código**: aquí funciona por accidente de la capa de Node |
| W14 | Nombre reservado `CON` | `«P»\CON` | **DENEGADO** | `ENOENT: … open '«P»\CON'` | Ídem |
| W15 | **Byte nulo (truncamiento)** | `«P»\dentro.txt\x00.png` | **DENEGADO** | `Access denied - path outside allowed directories: «P»\dentro.txt\x00.png not in «P»` | **Para**, por el rechazo explícito de `path-validation.ts:23-25`. Tardó **1 128,7 ms** frente a los ~2 ms del resto: el byte nulo atraviesa el JSON-RPC y algo lo digiere despacio |
| W16 | Ruta relativa a la unidad | `D:..\prohibido\secreto.txt` | **DENEGADO** | `…: «S»\prohibido\secreto.txt not in «P»` | Para |
| W17 | **Ruta entre comillas** | `"«S»\prohibido\secreto.txt"` | **DENEGADO** | `Parent directory does not exist: «P»\"D:\Work\…\sandbox\prohibido` | Para, pero delata un **bug de orden**: `normalizePath` quita las comillas (`path-utils.ts:41`) pero `validatePath` decide `path.isAbsolute` **antes** (`lib.ts:101`), así que la ruta se trata como relativa y se pega a la raíz |
| W18 | Espacio inicial | ` «S»\prohibido\secreto.txt` | **DENEGADO** | `Parent directory does not exist: «P»\ D:\Work\…\prohibido` | Mismo bug de orden que W17 |
| W19 | **Estilo Git-Bash `/d/…`, dentro de la raíz** | `/d/Work/…/permitido/dentro.txt` | **DENEGADO** | `Access denied - path outside allowed directories: D:\d\Work\…\permitido\dentro.txt not in «P»` | **FALSO NEGATIVO y código muerto.** `convertToWindowsPath` (`path-utils.ts:19-23`) convertiría `/d/…` → `D:\…`, pero **nunca se ejecuta**: `path.isAbsolute('/d/…')` es `true` en win32, así que `lib.ts:102` hace `path.resolve` primero y produce `D:\d\Work\…` |
| W20 | `/d/…` fuera de la raíz | `/d/Work/…/prohibido/secreto.txt` | **DENEGADO** | `…: D:\d\Work\…\prohibido\secreto.txt not in «P»` | Para (por el mismo accidente) |
| W21 | Estilo WSL `/mnt/d/…` | `/mnt/d/Work/…/prohibido/secreto.txt` | **DENEGADO** | `…: D:\mnt\d\Work\…\secreto.txt not in «P»` | Para. El "soporte WSL" de `path-utils.ts:11-15` es igualmente inalcanzable desde `validatePath` |
| W22 | Barra final sobre directorio | `«P»\sub\` | **DENEGADO** | `EISDIR: illegal operation on a directory, read` | Sin escape, pero **revela que es un directorio** |
| W23 | **Nombre corto 8.3 de la propia raíz** | raíz `C:\Program Files`; petición `list_directory` sobre `C:\PROGRA~1` | **DENEGADO** | `Access denied - path outside allowed directories: C:\PROGRA~1 not in C:\Program Files` | **FALSO NEGATIVO.** El nombre corto existe (`dir /x C:\` → `PROGRA~1  Program Files`) y apunta al mismo directorio, pero el filtro **léxico** corta antes de que `realpath` pueda canonizarlo |
| W24 | 8.3 + subdirectorio | `C:\PROGRA~1\Common Files` | **DENEGADO** | análogo | Falso negativo |
| W25 | 8.3 + travesía fuera | `C:\PROGRA~1\..\Windows` | **DENEGADO** | `…: C:\Windows not in C:\Program Files` | Para |

> **Nota sobre W23-W25.** En la unidad `D:` de esta máquina la **generación de nombres 8.3 está
> desactivada** (`dir /x` no muestra alias para ninguno de los directorios del sandbox; `fsutil
> 8dot3name query D:` devuelve `Acceso denegado`). Por eso el vector 8.3 se midió con raíz
> `C:\Program Files`, **solo lectura y sin crear ningún señuelo fuera del sandbox**: la única
> herramienta usada fue `list_directory`. **MEDIDO** (`salidas/06_83.json`).

**Balance de Windows: ningún vector concedió acceso fuera de la raíz. MEDIDO.** Lo que hay son cinco
falsos negativos (W1, W5, W19, W21, W23) y un hueco de contenido dentro de la raíz (W9, ADS). Para
FileX los cinco falsos negativos son **fallos funcionales serios**: un agente que escriba
`d:\proyecto\informe.pdf` en minúsculas recibiría "acceso denegado" a un fichero suyo, y no tendría
forma de adivinar por qué.

### 2.5 Escritura (`salidas/02_escritura.json`)

Todos los destinos de escritura están **dentro del sandbox**; no se escribió, modificó ni borró nada
fuera de él.

| # | Vector | Petición | Resultado | Mensaje literal | Veredicto |
|---|---|---|---|---|---|
| E1 | Control | `write_file` → `«P»\escrito_por_mcp.txt` | **CONCEDIDO** | `Successfully wrote to «P»\escrito_por_mcp.txt` | Correcto |
| E2 | Escritura fuera de la raíz | `write_file` → `«S»\prohibido\escrito_fuera.txt` | **DENEGADO** | `Access denied - path outside allowed directories: «S»\prohibido\escrito_fuera.txt not in «P»` | Para |
| E3 | Escritura por travesía | `write_file` → `..\prohibido\escrito_travesia.txt` | **DENEGADO** | análogo | Para |
| E4 | Crear directorio fuera | `create_directory` → `«S»\prohibido\dir_nuevo` | **DENEGADO** | análogo | Para |
| E5 | Mover de dentro a fuera | `move_file` dentro → `«S»\prohibido\movido.txt` | **DENEGADO** | análogo (valida **también el destino**) | Para |
| E6 | **Sobrescritura silenciosa** | `write_file` → `«P»\dentro.txt` (ya existía) | **CONCEDIDO** | `Successfully wrote to «P»\dentro.txt` | **PROBLEMA PARA FileX.** Destruyó el contenido original sin aviso ni confirmación (`lib.ts:167-180`) |
| E7 | Verificación de E6 | `read_text_file` `«P»\dentro.txt` | **CONCEDIDO** | `SOBRESCRITO SIN AVISAR` | Confirma E6 |

**Efecto colateral medido en E6:** la escritura atómica (fichero temporal + `rename`) **destruyó el
flujo de datos alternativo** `dentro.txt:oculto`, que después de E6 ya no existía. **MEDIDO.** Para un
conversor eso significa que "sobrescribir el fichero" puede perder metadatos NTFS que el usuario ni
sabía que tenía (marca de zona de Internet, por ejemplo).

### 2.6 Enlaces simbólicos y uniones creados **antes** del arranque (`salidas/03_symlinks_previos.json`)

| # | Vector | Petición | Resultado | Mensaje literal | Veredicto |
|---|---|---|---|---|---|
| S1 | **Control**: enlace dentro → dentro | `«P»\link_interno.txt` → `sub/anidado.txt` | **CONCEDIDO** | `SUBCARPETA PERMITIDA OK` | Correcto: un enlace legítimo dentro de la raíz funciona |
| S2 | Enlace de fichero dentro → fuera | `«P»\link_fuera.txt` → `../prohibido/secreto.txt` | **DENEGADO** | `Access denied - symlink target outside allowed directories: «S»\prohibido\secreto.txt not in «P»` | Para. **Y filtra la ruta resuelta, que está fuera del sandbox** |
| S3 | **Unión de directorio** dentro → fuera | `«P»\junc_fuera\secreto.txt` (junction a `..\prohibido`) | **DENEGADO** | mismo mensaje | Para. `fs.realpath` de Node resuelve *junctions* de Windows |
| S4 | Enlace a fichero real del sistema | `«P»\link_win.txt` → `C:\Windows\win.ini` | **DENEGADO** | `Access denied - symlink target outside allowed directories: C:\Windows\win.ini not in «P»` | Para |
| S5 | Qué ve el modelo al listar | `list_directory` sobre `«P»` | **CONCEDIDO** | `[FILE] dentro.txt` · `[FILE] junc_fuera` · `[FILE] link_fuera.txt` · `[FILE] link_interno.txt` · `[FILE] link_win.txt` · `[DIR] sub` | **La unión de directorio se etiqueta `[FILE]`.** El listado miente sobre la naturaleza de las entradas |

---

## 3. El oráculo de existencia — veredicto

La pregunta de `PLAN-ORQUESTADOR.md` §4.6 es si un agente puede **mapear el disco** preguntando. Se
compararon los tres casos exigidos, palabra por palabra (`salidas/01_ataques.json`, pasos
`A_control_dentro`, `B_existe_fuera`, `C_noexiste_fuera`).

### 3.1 Los tres casos enfrentados

**(a) Existe y está DENTRO de la raíz** — `«P»\dentro.txt`

```
CONTENIDO PERMITIDO OK 12345
```
`isError=false`, 5,4 ms.

**(b) EXISTE pero está FUERA de la raíz** — `«S»\prohibido\secreto.txt`

```
Access denied - path outside allowed directories: D:\Work\research\FileX\bench\salidas-mcp-refs\confinamiento\sandbox\prohibido\secreto.txt not in D:\Work\research\FileX\bench\salidas-mcp-refs\confinamiento\sandbox\permitido
```
`isError=true`, 1,4 ms.

**(c) NO existe y está FUERA de la raíz** — `«S»\prohibido\no_existe_jamas.txt`

```
Access denied - path outside allowed directories: D:\Work\research\FileX\bench\salidas-mcp-refs\confinamiento\sandbox\prohibido\no_existe_jamas.txt not in D:\Work\research\FileX\bench\salidas-mcp-refs\confinamiento\sandbox\permitido
```
`isError=true`, 1,9 ms.

### 3.2 Veredicto: **(b) y (c) son indistinguibles. Fuera de la raíz NO es un oráculo.**

**MEDIDO.** Misma plantilla, mismo `isError`, misma latencia dentro del ruido (1,4 vs 1,9 ms; el
control dentro de la raíz tarda 3-5 ms porque **sí** toca el disco). La única diferencia entre los dos
mensajes es la ruta que el propio atacante escribió: **cero bits de información nueva**.

Un tercer caso lo confirma: `D:\no_existe_esta_unidad_dir\x.txt` (ni el directorio existe) devuelve la
misma plantilla, y `D:\Windows\win.ini` (`D:\Windows` **no** existe en esta máquina) devuelve un mensaje
**palabra por palabra idéntico** al de `C:\Windows\win.ini` (que sí existe). **MEDIDO.**

**La razón es de diseño, y es lo mejor que tiene la referencia:** el predicado puramente léxico
`isPathWithinAllowedDirectories` se evalúa **antes de tocar el disco** (`lib.ts:107-111`, comentario
`// Security: Check if path is within allowed directories before any file operations`). Si la ruta cae
fuera, el servidor **jamás llega a preguntarle al sistema de ficheros**, así que no puede filtrar lo
que no sabe.

**Esto refuta parcialmente `analysis/00-mcp-filesystem.md` §A.4**, que afirmaba sin matiz que el
servidor «distingue explícitamente "prohibido" de "no existe"». El propio análisis ya acotaba el
oráculo al interior de la lista blanca en su punto 1; la ejecución confirma **esa** lectura y desmiente
la afirmación general del encabezado.

### 3.3 Pero **dentro** de la raíz sí es un oráculo, y filtra dos cosas más

**Oráculo interior** (`salidas/01_ataques.json`, pasos `A_noexiste_dentro`, `A_noexiste_dir_dentro`):

| Situación dentro de la raíz | Mensaje |
|---|---|
| Existe | el contenido |
| No existe, el padre sí | `ENOENT: no such file or directory, open '«P»\no_existe.txt'` |
| El directorio padre no existe | `Parent directory does not exist: «P»\no_existe_dir` |
| Es un directorio | `EISDIR: illegal operation on a directory, read` |

Cuatro respuestas distinguibles ⇒ **un agente puede mapear el árbol completo dentro de la lista
blanca.** Para `filesystem` da igual, porque `list_directory` y `directory_tree` ya lo dan gratis. Para
FileX **puede no dar igual**: si la raíz de lectura es el disco entero del usuario y FileX no expone un
listado, el error se convierte en el listado.

**Fuga 1 — la lista blanca completa.** Los tres mensajes de denegación terminan en
`not in ${allowedDirectories.join(', ')}` (`lib.ts:110,119,131`). **MEDIDO** en todas las filas de §2.
Aquí es inocuo porque `list_allowed_directories` ya la publica; en FileX, si la política de raíces es
sensible (rutas de otro inquilino, de otro usuario), **es una fuga**.

**Fuga 2 — rutas de FUERA del sandbox.** El mensaje de enlace imprime `realPath`, que **por definición
está fuera de la lista blanca** (`lib.ts:119`):

```
Access denied - symlink target outside allowed directories: C:\Windows\win.ini not in «P»
```

**MEDIDO** (S4). El agente aprende **dónde apunta el enlace**, es decir, aprende geografía del disco
del anfitrión que jamás pidió. Es la peor de las tres filtraciones y la más fácil de arreglar.

**Amplificador de sondeo.** `read_multiple_files` **no propaga la excepción**: la serializa por ruta
(`index.ts:345`). Una sola llamada con 6 rutas devolvió `isError=false` y **seis** respuestas del
mensaje de denegación, con la lista blanca repetida seis veces — **419 tokens** para no decir nada.
**MEDIDO** (`X1_multi`).

---

## 4. TOCTOU con enlaces simbólicos: qué se reprodujo y qué no

Hay que separar tres cosas que el análisis de código mezclaba.

### 4.1 Vector 4 del encargo — enlace creado **después** de arrancar el servidor: **REFUTADO**

La hipótesis era: como `index.ts:51-54` resuelve los enlaces **al arrancar**, un enlace creado después
podría colarse. **No es así.** `salidas/04_toctou.json`, fase `A_post_arranque`:

| Paso | Resultado |
|---|---|
| Control previo `«P»\race.txt` | `FICHERO REGULAR BENIGNO` — `isError=false` |
| Se crea `«P»\link_post.txt` → `«S»\prohibido\secreto.txt` **con el servidor ya arrancado** | `os.symlink` OK |
| Lectura del enlace | **DENEGADO**: `Access denied - symlink target outside allowed directories: «S»\prohibido\secreto.txt not in «P»` |
| Se crea el **enlace de directorio** `«P»\dlink_post` → `«S»\prohibido` | OK |
| Lectura `«P»\dlink_post\secreto.txt` | **DENEGADO**, mismo mensaje |

**MEDIDO.** La razón: `fs.realpath` se ejecuta **en cada llamada** a `validatePath` (`lib.ts:116`), no
una sola vez al arrancar. Lo que se resuelve al arrancar es solo la **lista blanca**, y por un motivo
de usabilidad (`/tmp` → `/private/tmp` en macOS, `index.ts:41-44`), no de seguridad.

### 4.2 Travesía por el directorio **padre** (test `path-validation.test.ts:784`): **REFUTADO**

Fase `C_padre_enlazado`: se lee `«P»\d1\f.txt` con éxito, se borra el directorio `d1` y se sustituye
por un **enlace de directorio a `prohibido`**, y se vuelve a preguntar.

| Petición tras el cambiazo | Respuesta |
|---|---|
| `«P»\d1\secreto.txt` | **DENEGADO**: `Access denied - symlink target outside allowed directories: «S»\prohibido\secreto.txt not in «P»` |
| `«P»\d1\f.txt` (la ruta **ya validada** antes) | **DENEGADO**: `Parent directory does not exist: «P»\d1` |

**MEDIDO.** `realpath` resuelve la ruta completa componente a componente, así que el padre enlazado se
detecta igual que el fichero enlazado.

### 4.3 La carrera real, por la superficie MCP: **NO REPRODUCIDA**

Diseño (fase `B_carrera_normal` de `toctou_probe.py`): tres hilos alternan `«P»\race.txt` entre
fichero regular benigno y enlace simbólico a `«S»\prohibido\secreto.txt`, mientras el cliente MCP
dispara `read_text_file` sobre esa ruta en tandas concurrentes. Se busca la marca
`SECRETO_PROHIBIDO_ABCDEF` en cualquier respuesta.

| Métrica | `B_carrera_normal` (por defecto) | `B2_carrera_ventana_ensanchada` (`UV_THREADPOOL_SIZE=1`, 96 en vuelo) |
|---|---|---|
| Llamadas | 24 000 en 23,4 s | 28 800 en 24,5 s |
| Intercambios del atacante | 16 063 | 15 474 |
| Lecturas benignas | 9 659 | 15 564 |
| **Denegadas por enlace** | **2 964 (12,4 %)** | **1 836 (6,4 %)** |
| ENOENT (pillado entre borrado y creación) | 5 807 | 7 765 |
| Respuestas vacías / otros (`EBUSY`, `EPERM`, `EBADF` en `realpath`) | 2 298 / 3 272 | 1 644 / 1 991 |
| **Fugas del secreto** | **0** | **0** |

**MEDIDO: 0 fugas en 52 800 llamadas.**

**Qué significa la distinción entre las dos filas.** `B2` **no es** "la misma prueba con más
paciencia": se fuerza el pool de hilos de libuv a **un solo hilo** con 96 peticiones en vuelo, para que
la cola separe el `fs.realpath` de `validatePath` del `fs.readFile` posterior y **la ventana se
ensanche artificialmente** en órdenes de magnitud. **Ni siquiera así se ganó la carrera.** Es decir:
**el resultado no es "no la gané con la ventana normal pero sí con la ensanchada"** — que sería un
resultado teórico interesante y prácticamente irrelevante. Es **no la gané en ninguna de las dos**.

**Por qué no se gana, medido y no supuesto.** Dos causas, ambas visibles en las cifras:

1. **`validatePath` devuelve `realPath`, no la ruta pedida** (`lib.ts:121`). El `fs.readFile` posterior
   abre la ruta **ya canonizada**. Para ganar hay que sustituir el fichero **en su ubicación
   canónica** en la ventana exacta, no basta con enlazar en cualquier punto del camino.
2. **Windows bloquea el fichero abierto.** El 79 % de los intentos de `os.symlink` del atacante
   fallaron con `[WinError 183] No se puede crear un archivo que ya existe` porque el `os.remove`
   previo no pudo borrar un fichero que el servidor tenía abierto. Las muestras `EBUSY`, `EPERM` y
   `EBADF` en `realpath` que devolvió el servidor son la otra cara de lo mismo. **En POSIX, donde
   `unlink` de un fichero abierto siempre funciona, el resultado podría ser distinto — PENDIENTE.**

### 4.4 Lo que sí demuestran los tests del propio repo — y lo que no

Se ejecutó la suite del clon (`npm install` + `npx vitest run` en
`repos/mcp-refs/servers/src/filesystem`). Los tres tests que el análisis citaba como prueba del agujero
**pasan en esta máquina**: **MEDIDO**

```
✓ demonstrates symlink race condition allows writing outside allowed directories  70ms
✓ should prevent race condition between validatePath and file operation            9ms
✓ demonstrates race condition in read operations                                  11ms
```

**Pero hay que leer lo que hacen.** El cuerpo de `demonstrates race condition in read operations`
(`__tests__/path-validation.test.ts:932-962`) es:

```ts
expect(isPathWithinAllowedDirectories(legitFile, allowed)).toBe(true);  // "paso 1"
await fs.unlink(legitFile);
await fs.symlink(secretFile, legitFile);
const content = await fs.readFile(legitFile, 'utf-8');                   // "paso 3"
expect(content).toBe('SECRET CONTENT');
```

**No llama a `validatePath` en ningún momento.** Llama al **predicado léxico** y luego lee la ruta
original. Es una demostración del **patrón** en abstracto — "si validas léxicamente y luego abres por
ruta, pierdes" —, no una explotación del servidor tal y como está montado, que sí llama a `realpath` y
sí opera sobre la ruta canónica.

**Veredicto honesto: el TOCTOU es real como clase de fallo y la propia referencia lo documenta, pero
NO se ha conseguido explotar contra la superficie MCP en Windows, ni con la ventana ensanchada.**
Marcar esto como "confirmado explotable" habría sido copiar el análisis de código en vez de medirlo.
**PENDIENTE:** repetir la fase B en Linux/WSL, donde `unlink` sobre fichero abierto no falla y la duty
cycle del atacante subiría del 21 % a ~100 %.

### 4.5 Un fallo de la suite en Windows, de propina

En una de las dos ejecuciones completas la suite dio **1 fallo de 152**; en otra, 5 (el resto son
inestables por temporización de procesos). El fallo reproducible es:

```
FAIL  __tests__/path-validation.test.ts > Overlapping allowed directories > handles root directory as allowed
AssertionError: expected true to be false
   __tests__/path-validation.test.ts:243
   expect(isPathWithinAllowedDirectories('D:\\other', ['/'])).toBe(false);
```

**MEDIDO.** Con el proceso corriendo desde la unidad `D:`, `path.resolve('/')` da `D:\`, así que
`D:\other` **cae dentro** de una lista blanca declarada como `/`. La referencia cree que una raíz `/`
no cruza unidades en Windows; **en esta máquina sí las cruza**. Lectura para FileX: **una raíz que
normaliza a la raíz de una unidad concede la unidad entera**, y hay que rechazarla explícitamente en la
configuración.

---

## 5. `kordoc`: qué mensaje de error llega al modelo

Servidor lanzado con `KORDOC_OFFLINE=1` (`salidas/04b_kordoc_errores.json`). Todos los mensajes están
**en coreano**: son cadenas literales de `src/mcp.ts` y `src/utils.ts`. Se dan tal cual, con
traducción entre corchetes.

### 5.1 Tabla de errores

| # | Entrada mala | Mensaje literal al modelo (`isError=true` salvo nota) | ¿Accionable? | ¿Filtra algo que no debería? |
|---|---|---|---|---|
| K0 | **Control**: `ok.pdf` (PDF válido) | `[포맷: PDF \| 페이지: 1]` + markdown. `isError=false` | — | — |
| K1 | Fichero inexistente | `오류: 파일을 찾을 수 없습니다: D:\Work\…\sandbox\kordoc\no_existe.pdf` [no se encuentra el fichero: `<ruta>`] | **Sí** — el modelo sabe que debe corregir la ruta | **Sí: la ruta absoluta completa.** Y es el oráculo de §5.2 |
| K2 | Extensión no soportada (`.ini`) | `오류: 지원하지 않는 확장자입니다: .ini (허용: .hwp, .hwpx, .hml, .pdf, .xls, .xlsx, .docx, .png, .jpg, .jpeg, .webp)` [extensión no soportada: `.ini` (permitidas: …)] | **Sí, ejemplar** — dice qué falló **y enumera lo que sí vale**, que es exactamente lo que el modelo necesita para reintentar | **No filtra la ruta.** Filtra la lista de extensiones, que es información pública y útil |
| K3 | Texto plano con extensión `.pdf` | `지원하지 않는 파일 형식입니다: D:\Work\…\falso.pdf` [formato de fichero no soportado: `<ruta>`] | **Parcial** — dice que el formato no vale, pero no que la **extensión miente** sobre el contenido, que es el diagnóstico útil | **Sí: la ruta absoluta** |
| K4 | PDF truncado a 1 200 bytes | `파싱 실패 (pdf): 문서 처리 중 오류가 발생했습니다` [fallo de análisis (pdf): se produjo un error al procesar el documento] | **NO.** Es el mensaje genérico de `sanitizeError` (`utils.ts:36`). El modelo no puede hacer nada con él salvo reintentar | **No filtra nada.** Es el precio pagado por la opacidad |
| K5 | ZIP válido sin estructura OOXML (`vacio.docx`) | `파싱 실패 (hwpx): HWPX에서 섹션 파일을 찾을 수 없습니다` [fallo (hwpx): no se encuentra el fichero de sección en el HWPX] | **Parcial** — es específico, pero **atribuye el fallo al formato equivocado**: se pidió un `.docx` y el error habla de HWPX | No |
| K6 | Ruta de un **directorio** | `오류: 지원하지 않는 확장자입니다:  (허용: …)` [extensión no soportada: `` (permitidas: …)] | **NO** — el modelo pasó un directorio y se le dice que la extensión vacía no vale. El diagnóstico correcto ("eso es un directorio") no aparece | No |
| K7 | PNG con OCR bloqueado por `KORDOC_OFFLINE` | `파싱 실패 (image): 폐쇄망 모드(KORDOC_OFFLINE)에서 차단됨: PP-OCRv5 mobile det 모델 다운로드 — 온라인 PC에서 \`kordoc models --export <디렉토리>\` 로 내보낸 뒤 이 PC에서 \`kordoc models --import <디렉토리>\` 하거나, KORDOC_MODEL_CACHE 로 모델 캐시 경로를 지정하세요` | **Sí, demasiado** — ver §5.3 | **Instrucciones de instalación dirigidas al agente** |
| K8 | Travesía relativa a `win.ini` | `오류: 파일을 찾을 수 없습니다: D:\Work\Windows\win.ini` | Sí | **Sí: la ruta resuelta.** Sin `KORDOC_ROOT` **no hay confinamiento**; falló solo porque el número de `..` no daba |
| K9 | Absoluta a `C:\Windows\win.ini` **sin `KORDOC_ROOT`** | `오류: 지원하지 않는 확장자입니다: .ini (허용: …)` | Sí | **Rechazo por EXTENSIÓN, no por ruta.** Es exactamente el fallo que `bench/mcp-ergonomia.md` §6.1 documentó en docling-mcp: cambia la extensión del objetivo y la protección desaparece |
| K10 | Fichero fuera del árbol, **sin `KORDOC_ROOT`** | `오류: 지원하지 않는 확장자입니다: .txt (허용: …)` | Sí | Ídem. **Sin `KORDOC_ROOT`, kordoc lee cualquier `.pdf`/`.docx`/… de cualquier punto del disco** — comprobado por CLI en §6 |
| K11 | Ruta vacía | `MCP error -32602: Input validation error: Invalid arguments for tool parse_document: String must contain at least 1 character(s) at file_path` | **Sí, ejemplar** — error de **protocolo**, no de aplicación. Lo genera zod (`z.string().min(1)`) antes de que corra una línea de kordoc | No |
| K12 | `parse_table` sin `table_index` | `MCP error -32602: … Invalid arguments for tool parse_table: Required at table_index` | **Sí, ejemplar** — nombra el parámetro que falta | No |
| K13 | `detect_format` sobre `falso.pdf` | `D:\Work\…\falso.pdf: unknown` — `isError=false` | **Sí** — detección real por *magic bytes*, no por extensión | La ruta |

### 5.2 kordoc **SÍ es un oráculo de existencia** (`salidas/05_kordoc_root.json`)

Con `KORDOC_ROOT` apuntando a `…\sandbox\kordoc`, los tres casos del §3 dan:

| Caso | Mensaje literal |
|---|---|
| **(a)** existe y **dentro** | markdown del documento, `isError=false` |
| **(b)** **existe** y **fuera** | `오류: 허용된 작업 디렉토리(KORDOC_ROOT) 밖의 경로입니다: D:\Work\…\sandbox\prohibido\secreto.txt` [ruta fuera del directorio de trabajo permitido: `<ruta>`] |
| **(c)** **no existe** y **fuera** | `오류: 파일을 찾을 수 없습니다: D:\Work\…\sandbox\prohibido\no_existe_jamas.txt` [no se encuentra el fichero: `<ruta>`] |

**(b) y (c) son mensajes DISTINTOS. MEDIDO. kordoc es un oráculo de existencia completo sobre todo el
disco.** Un agente puede enumerar el sistema de ficheros del anfitrión preguntando por rutas y mirando
cuál de las dos frases recibe. Confirmado con `C:\Windows\win.ini` → mensaje (b) y
`C:\Windows\no_existe.pdf` → mensaje (c). **MEDIDO.**

**La causa es el orden de las comprobaciones**, y es exactamente el inverso del de `filesystem`
(`src/mcp.ts:38-54`, función `safePath`):

```ts
const resolved = resolve(filePath)
try { real = realpathSync(resolved) }            // ← E/S PRIMERO
catch (err) {
  if (err?.code === "ENOENT") throw new KordocError(`파일을 찾을 수 없습니다: ${resolved}`)
  …
}
assertWithinRoot(real)                            // ← confinamiento DESPUÉS
```

`realpathSync` toca el disco **antes** de que `assertWithinRoot` (`src/shared/offline.ts:68-74`) tenga
ocasión de decir nada. `filesystem` hace justo lo contrario (`lib.ts:107-111`) y por eso **no** es
oráculo fuera de la raíz. **Es la diferencia de diseño más importante que encontró esta ejecución.**

Otros dos resultados de `kordoc` bajo `KORDOC_ROOT`, ambos **MEDIDO**:

- **Mayúsculas/minúsculas: kordoc acierta donde `filesystem` falla.** `d:\work\research\filex\…\ok.pdf`
  **funciona** (`R_case`, `isError=false`), porque `isWithinRoot` usa `path.relative`
  (`offline.ts:58-62`), que en win32 compara sin distinguir mayúsculas. Compárese con W1 de §2.4.
- **El enlace hacia fuera se deniega, pero filtra la ruta resuelta**, igual que `filesystem`:
  `허용된 작업 디렉토리(KORDOC_ROOT) 밖의 경로입니다: «S»\prohibido\secreto.txt` para una petición
  sobre `…\kordoc\link_fuera.pdf`.

### 5.3 K7 y el antipatrón de docling-mcp

`bench/mcp-ergonomia.md` documentó que docling-mcp respondió `pip install openai-whisper` al agente.
kordoc hace **lo mismo en forma, pero mejor en sustancia**:

| | docling-mcp | kordoc (K7) |
|---|---|---|
| Origen del texto | `stderr` crudo del motor, propagado sin filtrar | `KordocError` deliberado, escrito a mano en `src/shared/offline.ts:39-41` |
| Qué dirige | `pip install …` — modifica el entorno de Python del anfitrión | `kordoc models --export/--import`, o la variable `KORDOC_MODEL_CACHE` — su propia CLI |
| Superficie que abre | un gestor de paquetes con red | ninguna nueva; con `KORDOC_OFFLINE=1` la red ya está cortada |

**Sigue siendo un mensaje que puede dirigir la siguiente acción del agente**, y por eso importa: si
FileX escribe "instala X para convertir Y", un agente con acceso a shell **lo intentará**. La regla que
sale de aquí no es "no digas nunca qué falta", sino **"el error nombra la capacidad que falta, nunca el
comando que la instala"**.

### 5.4 Catálogo y esquemas zod

| | `filesystem` | `kordoc` |
|---|---|---|
| Herramientas | 14 | 15 |
| **`tokens_catalogo`** | **3 360** | **7 759** |
| Media por herramienta | 240 | 517 |
| Anotadas (`readOnlyHint`, …) | **14 / 14** | **0 / 15** |

**MEDIDO.** Coste por herramienta, los extremos:

```
filesystem:  list_allowed_directories 173 · get_file_info 192 · read_media_file 362
kordoc:      parse_form 132 · detect_format 139 · parse_document 729 · fill_form 763
             generate_document 3 092   <-- una sola herramienta cuesta casi el catálogo entero de filesystem
```

**Descripción MALA — `filesystem`, el parámetro `path`:**

```json
"path": { "type": "string" }
```

**Cero descripción en el parámetro más importante y más atacable de todo el servidor**, en las 14
herramientas. El modelo no sabe si debe mandar ruta absoluta o relativa, con `/` o con `\`, ni contra
qué se resuelve una relativa (spoiler: contra cada raíz permitida por turno, `lib.ts:76-96`). En
cambio `head` y `tail`, que son adorno, **sí** llevan descripción. Es la asimetría al revés. **MEDIDO.**
Recuérdese que `bench/mcp-ergonomia.md` §6 midió que markitdown y docling exigen **formatos de ruta
opuestos e incompatibles**: sin descripción del parámetro, el agente lo tiene que adivinar.

**Descripción BUENA — `kordoc`, `parse_table`:**

```json
"table_index": { "type": "integer", "minimum": 0,
                 "description": "추출할 테이블 인덱스 (0부터 시작)" }   // índice de tabla (empieza en 0)
```

Tipo entero, cota inferior, y el "empieza en 0" dicho **dos veces**, en la descripción del parámetro y
en la de la herramienta. Y la cota **la hace cumplir el protocolo**: omitirlo produjo
`MCP error -32602: … Required at table_index` (K12). **MEDIDO.**

**Descripción BUENA — `kordoc`, `parse_pages`:**

```json
"file_path": { "type": "string", "minLength": 1, "description": "파싱할 문서 파일의 절대 경로" },
"pages":     { "type": "string", "minLength": 1, "description": "페이지 범위 (예: '1-3', '1,3,5-7')" }
```

Dice **"ruta absoluta"** — lo que `filesystem` no dice nunca — y da **dos ejemplos de sintaxis**. Es la
diferencia entre un parámetro que el modelo acierta a la primera y uno que agota reintentos.

**Descripción MALA — `kordoc`, `generate_document`:** 3 092 tokens en una sola declaración, el 40 % del
catálogo. Un modelo paga ese peaje en **cada** turno aunque nunca la use. **MEDIDO.**

---

## 6. CLI frente a MCP en `kordoc`: **sí divergen, y una divergencia es de seguridad**

`src/cli.ts` (1 205 líneas) y `src/mcp.ts` (1 177) fueron la base de la estimación de que "la capa MCP
de FileX cuesta como la CLI". Ejecutadas la una contra la otra sobre las mismas entradas
(`salidas/07_kordoc_cli_vs_mcp.txt`), comparten el **núcleo de análisis** pero **no la capa de
validación ni la de errores**.

| Entrada | CLI (`kordoc --silent <f>`) | MCP (`parse_document`) | ¿Divergen? |
|---|---|---|---|
| `ok.pdf` | markdown a stdout, **sin cabecera**, `exit=0` | **`[포맷: PDF \| 페이지: 1]` + el mismo markdown**, `isError=false` | **Sí, en metadatos.** El MCP añade una cabecera de formato/páginas que la CLI no emite |
| `no_existe.pdf` | `[kordoc] ERROR: no_existe.pdf — 문서 처리 중 오류가 발생했습니다` [genérico], `exit=1` | `오류: 파일을 찾을 수 없습니다: <ruta absoluta>` [específico] | **Sí, y mucho.** La CLI da el mensaje **opaco** y solo el nombre base; el MCP da el mensaje **específico** y la **ruta absoluta**. Es al revés de lo que uno esperaría |
| `noformato.ini` | ` FAIL / → 지원하지 않는 파일 형식입니다.` [formato no soportado] — rechazo **tras leer** los magic bytes | `오류: 지원하지 않는 확장자입니다: .ini (허용: …)` — rechazo **por extensión, antes de abrir** | **Sí: distinto mecanismo y distinto momento.** Solo el MCP pasa por `safePath` |
| `falso.pdf` | `지원하지 않는 파일 형식입니다.` **sin ruta** | `지원하지 않는 파일 형식입니다: <ruta absoluta>` **con ruta** | **Sí**, en lo que filtra |
| `truncado.pdf` | `문서 처리 중 오류가 발생했습니다` + **`Warning: Indexing all PDF objects` en STDOUT** | `파싱 실패 (pdf): 문서 처리 중 오류가 발생했습니다`; el stderr del servidor solo contiene la línea de arranque | **Sí.** La CLI **mezcla ruido del motor pdfjs con la salida útil**; el MCP no lo dejó ver |
| `vacio.docx` | `HWPX에서 섹션 파일을 찾을 수 없습니다` | `파싱 실패 (hwpx): ` + el mismo texto | Solo el prefijo |
| `imagen.png` (OCR bloqueado) | el mismo texto largo de K7 | el mismo texto | **No.** Ese error sí es común |
| `--format json` sobre `truncado.pdf` | `{"success": false, "fileType": "pdf", "error": "문서 처리 중 오류가 발생했습니다", "code": "PARSE_ERROR"}` | **no hay `structuredContent`**: el MCP devuelve prosa | **Sí.** La CLI ofrece un **código de error legible por máquina** (`classifyError`) que la superficie MCP **no expone** |

### 6.1 La divergencia grave: `KORDOC_ROOT` **no lo aplica la CLI**

```sh
$ KORDOC_OFFLINE=1 KORDOC_ROOT=…/sandbox/kordoc \
    node dist/cli.js --silent D:/Work/research/FileX/corpus/pdf/tipico_texto.pdf
FileX - documento de prueba con texto seleccionable
…
exit=0
```

**MEDIDO.** El fichero está **completamente fuera** de `KORDOC_ROOT` y la CLI lo convierte sin
objetar. El mismo fichero por MCP habría dado
`허용된 작업 디렉토리(KORDOC_ROOT) 밖의 경로입니다`.

La causa es estructural y se ve en un `grep`: `src/cli.ts` importa de `utils.js` únicamente
`VERSION, toArrayBuffer, sanitizeError, classifyError` (`src/cli.ts:12`). **No importa `safePath`, ni
`safeOutputPath`, ni `assertWithinRoot`, ni `describeError`.** Esas cuatro funciones viven en
`src/mcp.ts:38`, `:57`, y `src/shared/offline.ts:68`, y **solo** la capa MCP las llama. **MEDIDO.**

**Aviso directo para FileX.** Esto es exactamente el modo de fallo que `PRUEBAS-MCP-REFS.md` §3.6 pedía
comprobar, y la respuesta es la peor posible: **el núcleo compartido es el de conversión, no el de
seguridad.** Si FileX pone la validación de rutas en la capa MCP, la CLI y el watcher quedan sin ella;
y el watcher, que sigue rutas que llegan de fuera, es tan expuesto como el MCP. **La validación va en
el núcleo, y las tres superficies la atraviesan obligatoriamente.**

---

## 7. Qué se lleva FileX, pieza por pieza

Licencias: `servers` = **MIT/Apache-2.0 (transición)**, con obligación de preservar avisos y adjuntar
`NOTICE` para todo lo que sea Apache-2.0 (§1.5). `kordoc` = **MIT**. Copiar es viable en ambos casos;
en `servers` **hay trabajo de licenciamiento asociado**, no solo un pegado.

FileX es **Python**; `filesystem` y `kordoc` son **TypeScript**. La columna "¿se porta?" separa lo que
es lógica pura de lo que depende de la capa de Node.

### 7.1 De `servers/src/filesystem`

| Pieza | `fichero:línea` | Veredicto | ¿Se porta a Python? |
|---|---|---|---|
| **Predicado léxico de contención** (tipos, byte nulo, lista vacía = denegar, normalización, comparación) | `path-validation.ts:11-86` | **COPIAR TAL CUAL** (traducido) | **Sí, 1:1.** Es lógica pura sin E/S. `path.normalize`→`os.path.normpath`, `path.resolve`→**`os.path.abspath`** (nunca `Path.resolve()`, que resuelve enlaces), `path.sep`→`os.sep` |
| **El `+ path.sep`** que cierra el fallo de prefijo | `path-validation.ts:84` | **COPIAR TAL CUAL** | **Sí.** `PurePath(p).is_relative_to(PurePath(d))` o `commonpath`; nunca `str.startswith(raiz)` a secas. Medido en P1/P2/P3 (§2.3) |
| **Rechazo del byte nulo antes de tocar el disco** | `path-validation.ts:23-25,47-49` | **COPIAR TAL CUAL** | **Sí.** `'\x00' in p`. Medido en W15 |
| **Lista blanca vacía = denegar todo** | `path-validation.ts:18-20` | **COPIAR TAL CUAL** | Sí |
| **Orden: predicado léxico ANTES de cualquier E/S** | `lib.ts:107-111` | **COPIAR TAL CUAL — la pieza más valiosa de las 1 501 líneas** | **Sí, es una decisión de orden, no de API.** Es lo único que impide ser oráculo fuera de la raíz (§3.2) |
| **Segunda validación sobre `realpath` y devolver la ruta canónica** | `lib.ts:116-121` | **ADAPTAR** | Sí, con `os.path.realpath(p, strict=True)`. **Python puede mejorarlo**: `os.open(..., O_NOFOLLOW)` y `dir_fd=` no existen en Node |
| **Rama ENOENT: validar el directorio padre real** | `lib.ts:122-137` | **ADAPTAR** | Sí. **`strict=True` es obligatorio**: con el `strict=False` por defecto de `os.path.realpath` no hay `FileNotFoundError` y esta rama desaparece |
| **Guardar original **y** resuelta en la lista blanca** | `index.ts:41-44,51-67` | **COPIAR TAL CUAL** | Sí. Resuelve el falso negativo `/tmp`→`/private/tmp`; en Windows el equivalente son las uniones de directorio en la propia raíz |
| **Fail-closed al arrancar sin ninguna raíz accesible** | `index.ts:85-88` | **COPIAR TAL CUAL** | Sí. Medido en §1.1 (`Error: None of the specified directories are accessible`) |
| **Negociación de *roots* del protocolo MCP** | `roots-utils.ts:52-77`, `index.ts:748-773` | **ADAPTAR — no reemplazar, INTERSECAR** | **Parcial.** El concepto es de protocolo; `fileURLToPath` hay que reescribirlo (`file:///C:/…` lleva barra de más). La referencia **reemplaza** la lista del servidor (`index.ts:181`); FileX, que escribe y lanza procesos, debe **intersecar** con una lista inmutable |
| **Anotaciones en las 14 herramientas** | `index.ts:370,400,425,629` | **COPIAR TAL CUAL** | Sí, coste cero. 14/14 anotadas, medido. Valores reales: lecturas `{readOnlyHint:true, openWorldHint:false}`; `write_file` y `move_file` `{readOnlyHint:false, destructiveHint:true}` |
| **Escritura exclusiva `'wx'` + `rename` atómico** | `lib.ts:161-185` | **ADAPTAR** | Sí: `os.open(..., O_CREAT\|O_EXCL)` y `os.replace`. **Pero no sirve para un binario externo** que abre la ruta por su cuenta (§8, R8). Y **destruye los ADS** del destino (medido en E6) |
| **Los cuatro mensajes de error** | `lib.ts:110,119,131,135` | **DESCARTAR** | Filtran la lista blanca completa y, en el caso del enlace, **la ruta resuelta fuera del sandbox** (§3.3). Medido |
| **`read_multiple_files` serializando el error por ruta** | `index.ts:345` | **DESCARTAR** | Amplifica el oráculo ×N con `isError=false`. Medido en X1 |
| **`read_media_file` deduciendo el MIME por extensión** | `index.ts:281-295` | **DESCARTAR** | Para un conversor, la extensión decide qué motor corre. Hace falta *sniffing* real. Contraste medido: `detect_format` de kordoc devolvió `unknown` para un `.pdf` falso (K13) |
| **`normalizePath` completo** (WSL, `/c/…`, comillas) | `path-utils.ts:39-112` | **DESCARTAR** | **Es código muerto en la ruta de validación**, medido en W17/W18/W19/W21: `validatePath` decide `isAbsolute` antes de llamarlo. Complejidad sin beneficio y superficie de bugs |
| **Comparación sensible a mayúsculas en Windows** | `path-validation.ts:66,84` | **DESCARTAR y arreglar** | Falso negativo medido en W1/W23. Python lo arregla gratis con `os.path.normcase` (identidad en POSIX) |
| **Una sola lista blanca para leer y escribir** | `lib.ts:99` | **DESCARTAR** | Un conversor necesita raíz de lectura ≠ raíz de escritura |
| **Sobrescritura silenciosa** | `lib.ts:167-180` | **DESCARTAR** | Medido en E6/E7: destruyó el fichero original sin aviso |
| **`__tests__/path-validation.test.ts`** (997 líneas) | todo el fichero | **SOLO REFERENCIA — pero léase el cuerpo, no el nombre** | Es el mejor catálogo de casos límite disponible. **Pero los tests de "carrera" no llaman a `validatePath`** (§4.4), y `handles root directory as allowed` **falla en Windows** (§4.5) |

### 7.2 De `kordoc`

| Pieza | `fichero:línea` | Veredicto | ¿Se porta? |
|---|---|---|---|
| **`sanitizeError`: si no es un error propio, mensaje constante** | `utils.ts:34-37` | **COPIAR TAL CUAL — la forma** | Sí, trivial. La disciplina es: **una clase de excepción propia cuyos mensajes están escritos a mano y son publicables; todo lo demás se colapsa a una constante.** Medido: nada de pdfjs, jszip ni xmldom llegó al modelo |
| **`KordocError` como marca de "publicable"** | `utils.ts:23-28` | **COPIAR TAL CUAL** | Sí. El comentario de `utils.ts:21` es la clave: se distingue por `instanceof`, **sin listas blancas de patrones sobre el texto** |
| **`classifyError`: excepción → código enumerado** | `utils.ts:166-181` | **ADAPTAR** | Sí, pero **no la implementación**: clasifica haciendo `msg.includes("암호화")` sobre texto coreano, que es frágil y no traducible. FileX debe llevar el **código dentro de la excepción**, no deducirlo del mensaje |
| **`describeError`: mapa `errno` → texto accionable** | `mcp.ts:84-100` | **ADAPTAR — se copia LA FORMA, no el contenido** | Sí. La forma es: (1) errores propios, tal cual; (2) `ENOENT/EACCES/EPERM/EISDIR/ENOTDIR/ENOSPC` → **frase fija por código, sin la ruta**; (3) el resto → genérico + código de clase. **El texto de kordoc está en coreano y es suyo**; FileX escribe el suyo |
| **La ruta en `safePath`** | `mcp.ts:45-46` | **DESCARTAR** | Interpola la ruta absoluta en el mensaje. Medido en K1/K3/K8 |
| **El ORDEN de `safePath`: `realpath` antes de `assertWithinRoot`** | `mcp.ts:40-50` | **DESCARTAR — es el antipatrón** | **Es la causa medida de que kordoc sea oráculo de existencia sobre todo el disco** (§5.2). Hágase al revés: como `lib.ts:107-111` |
| **`isWithinRoot` con `path.relative` en vez de prefijo** | `shared/offline.ts:58-62` | **COPIAR TAL CUAL** | Sí: `os.path.relpath` + comprobar que no empieza por `..`, o `is_relative_to`. **Acierta las mayúsculas en Windows donde `filesystem` falla** (medido: R_case ✓ frente a W1 ✗) |
| **Raíz inexistente ⇒ bloquear todo** | `shared/offline.ts:49-54` | **COPIAR TAL CUAL** | Sí. Fail-closed explícito, con el comentario que lo justifica |
| **La ruta en `assertWithinRoot`** | `shared/offline.ts:72` | **DESCARTAR** | Filtra `realPath`, que está fuera de la raíz. Mismo fallo que `lib.ts:119`. Medido en `R_symlink` |
| **`assertNetworkAllowed`: una única puerta de salida a red** | `shared/offline.ts:37-42` | **COPIAR TAL CUAL** | Sí. Un solo punto que hay que atravesar para hablar con el exterior, con la instrucción explícita de no meter host ni URL en el mensaje al usuario (`offline.ts:35`). FileX lo necesita el día que acepte URLs |
| **`isPathTraversal` para entradas de ZIP** | `utils.ts:43-48` | **COPIAR TAL CUAL** | Sí. Zip-slip en OOXML/ODF: byte nulo, `..` por segmentos, absoluta, letra de unidad |
| **`precheckZipSize`: leer el *central directory* antes de descomprimir** | `utils.ts:78-122` | **COPIAR TAL CUAL** | Sí. Tope de tamaño **sin comprimir** (256 MB) y de número de entradas (500) **antes** de tocar nada |
| **`stripDtd`: quitar el `DOCTYPE` antes de parsear XML** | `utils.ts:131-133` | **COPIAR TAL CUAL** | Sí. XXE y *billion laughs* en SVG/ODF/OOXML. En Python, `defusedxml` |
| **`sanitizeHref`: lista blanca de esquemas** | `utils.ts:136-143` | **COPIAR TAL CUAL** | Sí |
| **`capResponseText`: tope de 200 000 caracteres con instrucción de paginar** | `mcp.ts:103-108` | **COPIAR TAL CUAL** | Sí, y es **la respuesta directa** a los 85 259 tokens que markitdown devolvió en `bench/mcp-ergonomia.md`. El texto de corte **dice qué herramienta usar** para leer el resto |
| **`MAX_FILE_SIZE` / `MAX_METADATA_FILE_SIZE`** | `mcp.ts:35,111` | **ADAPTAR** | Sí, dos topes distintos según lo que se vaya a hacer con el fichero |
| **Los 87 esquemas zod con `.describe()`** | `mcp.ts:158-169` y siguientes | **ADAPTAR** | El **patrón** sí: `minLength`, `minimum`, ejemplos de sintaxis, "ruta absoluta" dicho explícitamente, y **la validación la hace el protocolo** (`-32602` medido en K11/K12). El **volumen** no: 7 759 tokens y `generate_document` con 3 092 |
| **Cero anotaciones en las 15 herramientas** | `mcp.ts:154+` | **DESCARTAR** | 0/15 medido. `filesystem` hace 14/14 gratis |
| **La CLI sin `safePath`** | `cli.ts:12` | **DESCARTAR — es el aviso, no la pieza** | La validación debe estar en el núcleo, no en una superficie (§6.1) |

---

## 8. Las reglas de confinamiento que FileX debe implementar

Esta sección sustituye a `PLAN-ORQUESTADOR.md` §4.6. Cada regla lleva su evidencia **medida aquí**.

### R1 — El predicado léxico se evalúa **antes** de tocar el disco. Sin excepciones.

Normalizar sintácticamente (sin resolver enlaces), comprobar contención, y solo entonces llamar al
sistema de ficheros. **MEDIDO:** es lo único que separa a `filesystem` (no es oráculo fuera de la raíz,
§3.2) de `kordoc` (oráculo completo sobre todo el disco, §5.2). Las dos implementaciones existen, el
experimento las enfrentó, y el orden es la única diferencia.
Referencia a portar: `lib.ts:107-111`.

### R2 — Comparar por **segmentos**, nunca por prefijo de cadena.

`os.path.normcase` en ambos lados, y `PurePath.is_relative_to` o `startswith(raiz + os.sep)`.
**MEDIDO:** P1/P2/P3 — `…\permitido_secreto\trampa.txt` denegado con la raíz `…\permitido`, gracias al
`+ path.sep` de `path-validation.ts:84`. Un `startswith` sin separador lo habría concedido.

### R3 — Aplicar `normcase`: en Windows, ignorar mayúsculas y unificar separadores.

**MEDIDO:** W1 y W23 — `filesystem` **deniega rutas legítimas** escritas en minúsculas o con nombre
corto 8.3, porque compara sensible al caso salvo la letra de unidad. `kordoc` acierta (`R_case`) porque
usa `path.relative`. En Python `os.path.normcase` es la identidad en POSIX, así que se aplica siempre.
Además: **rechazar en la configuración cualquier raíz que normalice a la raíz de una unidad** — medido
en §4.5, `D:\other` cae dentro de una lista blanca declarada como `/`.

### R4 — **Un único mensaje opaco y constante** para todo lo que se deniega o no se encuentra.

Sin la ruta pedida, sin la ruta resuelta, sin la lista blanca. El detalle va al log del servidor
(stderr), nunca a la respuesta MCP. **MEDIDO, tres evidencias distintas:**
- `filesystem` filtra la lista blanca completa en los tres mensajes de denegación (§3.3, todas las
  filas de §2);
- `filesystem` filtra **la ruta resuelta que está fuera del sandbox** cuando hay un enlace
  (`… symlink target outside allowed directories: C:\Windows\win.ini …`, S4);
- `kordoc` distingue (b) de (c) y por tanto **enumera el disco** (§5.2).

Corolario medido: **la equivalencia hay que mantenerla también en la latencia.** Aquí salió gratis
porque el corte léxico no toca el disco (1,4 vs 1,9 ms fuera de la raíz, frente a 3-5 ms dentro); si
FileX hace E/S antes de denegar, el reloj se convierte en el oráculo.

### R5 — La misma opacidad **por elemento** en las operaciones por lotes.

**MEDIDO:** `read_multiple_files` con 6 rutas devolvió `isError=false` y **seis** mensajes de
denegación con la lista blanca repetida seis veces, 419 tokens (`index.ts:345`, paso X1). Una llamada,
seis respuestas del oráculo.

### R6 — Denegar por defecto: lista blanca vacía = nada; ninguna raíz accesible = no arrancar.

**MEDIDO:** `path-validation.ts:18-20` y el `Error: None of the specified directories are accessible`
de §1.1. `kordoc` hace lo contrario: **sin `KORDOC_ROOT` no hay confinamiento ninguno**, y su única
defensa es la lista de extensiones — el mismo fallo que `bench/mcp-ergonomia.md` §6.1 documentó en
docling-mcp (K9, K10).

### R7 — Resolver enlaces **en cada llamada**, y validar la ruta resuelta; operar sobre la canónica.

**MEDIDO:** el vector 4 del encargo queda **refutado** (§4.1): un enlace de fichero, un enlace de
directorio y una unión creados **después** del arranque se detectan los tres. Lo que se resuelve al
arrancar es la lista blanca, y por usabilidad (`index.ts:41-44`), no por seguridad.
Corolario: **guardar en la lista blanca la forma original y la resuelta** cuando difieran, o se
producen falsos negativos totales.

### R8 — Copiar la entrada a un *staging* privado tras validarla, y pasar al motor externo **solo** la ruta del staging.

**MEDIDO como límite de lo demostrado, no como demostración:** la carrera TOCTOU **no se ganó** en
52 800 intentos contra `filesystem`, ni con la ventana ensanchada (§4.3). Pero eso mide una ventana de
microsegundos entre `realpath` y `readFile` **dentro del mismo proceso**. En FileX la ventana entre
validar y que ffmpeg o LibreOffice terminen de leer son **minutos**, y quien lee es **otro proceso que
no sabe nada de la lista blanca**. La mitigación de la referencia (`'wx'` + `rename`, `lib.ts:161-185`)
no se puede aplicar a un binario externo. Copiar al staging reduce la ventana a la de la copia y
**el binario externo nunca ve una ruta que el agente controle**.
Además, Python permite lo que Node no: `os.open(..., O_NOFOLLOW)`, `dir_fd=`, y mantener el descriptor
abierto comprobando `st_dev`/`st_ino`. **PENDIENTE:** verificar la ventana real en FileX y repetir la
fase B en Linux, donde `unlink` sobre fichero abierto no falla (en Windows falló el 79 % de los
intentos del atacante y eso sesga el resultado a favor del servidor).

### R9 — Raíz de **lectura** ≠ raíz de **escritura**, y no sobrescribir en silencio.

**MEDIDO:** `filesystem` usa **una sola** lista para las 14 herramientas (`lib.ts:99`), así que el
modelo puede escribir encima de cualquier cosa que pueda leer; y E6/E7 confirman que
`write_file` destruyó `dentro.txt` sin aviso — **y de paso destruyó su flujo de datos alternativo**.
FileX: escritura por defecto a un staging propio, no-clobber, sufijo automático o *elicitation*.

### R10 — La validación vive en el **núcleo**, no en la superficie MCP.

**MEDIDO:** la evidencia más contundente de todo el informe. `KORDOC_ROOT` **solo lo aplica
`src/mcp.ts`**; `src/cli.ts:12` ni siquiera importa `safePath` ni `assertWithinRoot`, y la CLI leyó un
fichero completamente fuera de la raíz con `exit=0` (§6.1). FileX tiene **tres** superficies (MCP, CLI,
watcher, más la API HTTP): si la validación cuelga de una, las otras tres están abiertas. Y el watcher
sigue rutas de origen externo, así que es tan expuesto como el MCP.

### R11 — El tipo real se decide por **contenido**, no por extensión.

**MEDIDO:** `detect_format` de kordoc devolvió `unknown` para un fichero de texto llamado `falso.pdf`
(K13), mientras `read_media_file` de `filesystem` deduce el MIME de la extensión (`index.ts:281-295`).
Para un conversor la extensión **elige el motor**, así que mentir sobre ella es elegir el motor.
Discrepancia entre magia y extensión = rechazo o aviso explícito.

### R12 — Normalizar el nombre del fichero de salida y prohibir las trampas de Windows.

**MEDIDO como ausencia:** `filesystem` no tiene **ni un solo** filtro de nombres reservados
(`CON`, `NUL`, `AUX`, `PRN`, `COM1-9`, `LPT1-9`), de puntos o espacios finales, ni de flujos alternativos.
W11-W14 fallan por accidente de la capa de Node, no por diseño. **Y W9 concedió acceso**: leer
`«P»\dentro.txt:oculto` devolvió `ADS_OCULTO_DENTRO_777`, es decir, **bytes distintos de los del
fichero que se validó**, dentro de la raíz permitida. En un conversor eso significa convertir algo que
no es lo que el usuario cree. Regla: rechazar `:` en el componente final, rechazar puntos y espacios
finales, rechazar nombres reservados, y **renombrar a un nombre opaco en el staging** antes de invocar
al motor (que además cierra la inyección de opciones: un fichero llamado `--outdir=…` pasa cualquier
validación de rutas y es una opción para el binario).

### R13 — Los *roots* del cliente se **intersecan** con la lista del servidor, no la reemplazan.

**MEDIDO parcialmente:** el servidor pide los roots al cliente en `oninitialized`, y al no soportarlos
el arnés escribió `Failed to request initial roots from client: MCP error -32600` **a stderr** y
continuó con la lista de argumentos (§1.1). El mecanismo es de protocolo y hay que usarlo. Pero
`index.ts:181` **sustituye** la lista del servidor por la del cliente. FileX escribe ficheros y lanza
procesos: si el modelo de amenaza incluye un cliente comprometido o una inyección de instrucciones que
manipule su configuración, aceptar la sustitución amplía la superficie. **Intersecar.**
**PENDIENTE:** verificar que el SDK Python expone `list_roots()` y la notificación `list_changed`.

### R14 — El error nombra la **capacidad** que falta, nunca el **comando** que la instala.

**MEDIDO:** K7 — kordoc responde al agente con `kordoc models --export <dir>` / `--import <dir>` /
`KORDOC_MODEL_CACHE`. Es mucho mejor que el `pip install openai-whisper` de docling-mcp (es un
`KordocError` deliberado, no `stderr` crudo, y apunta a su propia CLI en vez de a un gestor de
paquetes), pero **sigue siendo un mensaje que dirige la siguiente acción del agente**. Y la forma que
sí hay que copiar es la de `describeError` (`mcp.ts:84-100`): mapa **código de error → frase fija y
accionable, sin la ruta**, con el código viajando **dentro** de la excepción — no deducido del texto
como hace `classifyError` (`utils.ts:166-181`), que compara subcadenas coreanas y se rompe en cuanto se
traduce.

### R15 — Describir el parámetro `path` como si el modelo no supiera nada. Porque no lo sabe.

**MEDIDO:** las 14 herramientas de `filesystem` declaran `"path": {"type": "string"}` — **sin
descripción**, mientras `head` y `tail` sí la llevan. `kordoc` dice `"파싱할 문서 파일의 절대 경로"`
("ruta **absoluta** del fichero a analizar") y añade `minLength: 1`, que el protocolo hace cumplir
(`-32602`, K11). Y `bench/mcp-ergonomia.md` §6 ya midió que markitdown y docling exigen formatos de
ruta **mutuamente incompatibles**. FileX debe decir en la descripción: absoluta o relativa, contra qué
se resuelve una relativa, qué separadores acepta, y **que existe una lista blanca** — sin enumerarla.
Coste ~30 tokens; el ahorro es un reintento fallido por sesión.

---

## 9. Contraste final: `filesystem` frente a los MCP documentales ya medidos

| | `markitdown-mcp` | `docling-mcp` | **`filesystem`** | `kordoc` (con `KORDOC_ROOT`) |
|---|---|---|---|---|
| Fuente | `bench/mcp-ergonomia.md` §6 | ídem | **este informe** | este informe |
| `..\..\` | ✅ funciona | ✅ funciona | ❌ **denegado (8 variantes)** | ❌ denegado |
| Ruta absoluta arbitraria | ✅ devuelve `C:\Windows\win.ini` | ✅ convierte cualquier `.md`/`.pdf` del disco | ❌ **denegado** | ❌ denegado |
| Concepto de raíz permitida | ninguno | ninguno | **sí, denegar por defecto** | sí, pero **solo en la capa MCP** |
| Defensa efectiva | ninguna | filtro de **extensiones** (cambia la extensión y desaparece) | **contención de rutas real** | contención real + extensiones |
| ¿Oráculo de existencia? | irrelevante, lo lee todo | irrelevante | **no fuera de la raíz; sí dentro** | **sí, en todo el disco** |
| Anotaciones de herramienta | 0/1 | bien anotadas | **14/14** | **0/15** |
| `tokens_catalogo` | 79 | 5 280 | **3 360** | **7 759** |

**Lo que `filesystem` hace bien y ellos no** — todo **MEDIDO**: (1) existe una lista blanca y se
deniega por defecto; (2) el predicado es **léxico y previo a la E/S**, lo que además elimina el oráculo
fuera de la raíz; (3) compara por segmentos y no por prefijo; (4) resuelve enlaces **en cada llamada**
y valida la ruta resuelta; (5) **las 14 herramientas comparten el mismo validador**, así que no hay una
puerta trasera por herramienta; (6) valida **también el destino** de las operaciones de escritura y
movimiento.

**Lo que hace mal**: filtra la lista blanca y las rutas resueltas de fuera del sandbox en cada
denegación, es oráculo dentro de la raíz, amplifica el sondeo en las operaciones por lotes, usa una
sola lista para leer y escribir, sobrescribe en silencio, deduce el MIME de la extensión, deniega
rutas legítimas en Windows por cinco motivos distintos, y **concede la lectura de flujos de datos
alternativos**.

**PENDIENTE, y en este orden:** (1) repetir la fase B del TOCTOU en Linux/WSL; (2) verificar
`list_roots()` en el SDK Python de MCP; (3) medir el coste real de la validación en Python sobre rutas
de 1 000 componentes; (4) medir el efecto de las anotaciones sobre la **elección** del modelo, que
sigue sin medirse en todo el proyecto.
