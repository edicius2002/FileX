# MANIFIESTO — `bench/salidas-mcp-cabos/`

Informe que consume estas salidas: **`bench/mcp-cabos-sueltos.md`** (confirmado con
`grep -rl "salidas-mcp-cabos/" bench/*.md`; también se cita, sin generar nada nuevo, en
`bench/consolidacion-21ago.md`, `bench/consolidacion-2-21ago.md` y
`bench/consolidacion-3-21ago.md` — las tres son cierres de jornada que ya listaban este
directorio como cerrado por su autor).

**Total en disco: 75 ficheros, 193 497 B (~189 KiB).**

Fecha de generación: 21/08/2026. Máquina: Windows 10 Home, 12 núcleos, Python 3.11.9, Node
v22.23.2, WSL2 (Ubuntu, Python 3.14.4), sin GPU.

---

## 0. PENDIENTE / NO REPRODUCIBLE DESDE ESTE ENTORNO (WSL) — léase antes de re-ejecutar nada

Este directorio cierra **cinco cabos** distintos y **ninguno de los cinco** se puede
relanzar tal cual desde este *worktree* de WSL. Los motivos, verificados uno a uno en esta
misma máquina (no deducidos):

1. **Los venvs del SDK de Python que usan los cabos 1, 2 y 4 ya no existen.** `CLAUDE.md` §2
   los lista entre los **borrados** el 31/08/2026: `.venv-mcp-sdk-1x`, `.venv-mcp-sdk-2x`
   (cabos 1 y 2, las dos eras del protocolo MCP) y `.venv-mcp-vam` (cabo 4, el servidor
   `video-audio-mcp`). Verificado aquí: `ls -d .venv-mcp-sdk-* .venv-mcp-vam` no encuentra
   nada en este *worktree*.
2. **Los cabos 1 y 2 dependen de una sesión real de `claude` CLI** (`claude -p … --mcp-config
   … --strict-mcp-config`, `claude mcp list`) contra un `.mcp.json` **de proyecto** editado a
   propósito. Eso exige aprobación interactiva de un servidor nuevo (§1.6 del informe) y no
   es algo que un script por sí solo reproduzca sin un humano delante.
3. **Los cabos 4 y 5 tienen la raíz `D:/Work/research/FileX` y `taskkill /F /T /PID`
   escritos literalmente en el código** (`RAIZ = Path("D:/Work/research/FileX")` en
   `cabo4_deadlock.py`, `cabo4_ffmpeg_control.py`, `cabo4_secuencia.py`,
   `cabo4_srv_stdin.py`, `cabo5_envenenamiento.py`, `cabo5_inspect.py`, `cabo5_toctou.py`).
   `taskkill` no existe en Linux, y el mecanismo del cabo 5 (bloqueo obligatorio de Windows
   sobre un fichero abierto) **no existe en POSIX** — es justo lo que el propio cabo mide
   como distinto entre plataformas (§5.2 del informe).
4. **Los repos externos que clasifican/ejercitan cabo 3 y cabo 4 no están clonados en este
   *worktree*** (`repos/` está vacío aquí y en `.gitignore`): `repos/mcp-refs/image-worker-mcp`
   (cabo 3) y `repos/mcp-refs/video-audio-mcp` (cabo 4, referenciado como valor por defecto de
   `sys.argv[1]` en `cabo4_clasificar.py`).
5. **`cabo5_linux.py` es la única pieza con lógica puramente POSIX**, pero su función
   `main()` la lanza con `subprocess.run(["wsl", "-e", "bash", "-lc", guion()], …)` — es decir,
   está pensada para ejecutarse **desde Python de Windows**, que invoca el lanzador `wsl.exe`
   para entrar en esta misma WSL. Dentro de WSL no existe el binario `wsl`, así que el script
   tal cual falla aquí con `FileNotFoundError`. El *guion* bash que construye (heredoc
   `guion()`, líneas 40-102) **sí es código POSIX puro** y en principio podría extraerse y
   ejecutarse directamente con `bash -c` en este mismo WSL sin pasar por el lanzador — pero
   eso sería escribir una variante nueva, no reproducir el fichero tal como está, así que se
   declara PENDIENTE y no se ha intentado.

**Lo único de este directorio con una ruta de reproducción plausible sin Windows** es el
cabo 3 (`iwm_npm_install.log` / `iwm_vitest.log`): usa Node/`npm`/`vitest`, que sí corren en
Linux (`node` 24.19.0 y `npm` 11.17.0 están disponibles en este WSL), y la ruta impresa
dentro del propio log (`D:/Work/research/FileX/repos/mcp-refs/image-worker-mcp`) es de
Windows solo porque así se generó, no porque el comando lo exija. **Pero el repositorio no
está clonado aquí**, así que sigue siendo PENDIENTE por falta del clon, no por
incompatibilidad de plataforma — la distinción importa porque es la única de las cinco donde
un agente de Linux con el repo clonado sí podría reproducir el hallazgo de fondo (117
tests, 0 fallos).

---

## 1. `.mcp.json` — copia de seguridad, no una salida generada

| Fichero | sha256 | Bytes | Qué es |
|---|---|---:|---|
| `mcp.json.bak` | `4f1628c8cd508fee3e78b89c2683368e8adea5ebff57f5d488c2e511765b153d` | 643 | Copia de `.mcp.json` **antes** de añadirle el servidor de prueba del cabo 1. Restaurada al terminar (`cabo1_escribir_mcpjson.py restore`); `git status` de `.mcp.json` quedó limpio. No hay "orden que la reproduce": es un respaldo puntual, no un artefacto derivado. |

---

## 2. Cabo 1 — `mcp 2.0.0` contra clientes reales

Requiere: `.venv-mcp-sdk-2x` (**borrado**) + una sesión de `claude` CLI con aprobación
interactiva del servidor.

| Fichero | sha256 | Bytes | Orden que lo reproduce (en la máquina de Windows del proyecto) |
|---|---|---:|---|
| `cabo1_srv_2x.py` | `0d0e9f9b180d12d72a5977b111f2284f28a1ec48631d540f4fd7678ea7ed184d` | 6 330 | Servidor MCP mínimo (5 herramientas, 1 recurso, 1 prompt) sobre `mcp 2.0.0`. Se lanza como servidor `stdio` desde `.mcp.json` |
| `cabo1_escribir_mcpjson.py` | `bfeea30e0ea6ddc50972dbe2e1304b1174f19f4f3126389a608e8d766d421045` | 1 438 | `.venv-mcp-sdk-2x/Scripts/python.exe cabo1_escribir_mcpjson.py add` (da de alta el servidor en `.mcp.json` de proyecto) / `… restore` (lo quita, usando `mcp.json.bak`) |
| `cabo1_solo.mcp.json` | `bc23373f6fe89431771340ebc513fd851bf46afc14ae2f6ea9866a19fd15dfeb` | 477 | Config mínima de proyecto usada con `claude -p … --mcp-config bench/salidas-mcp-cabos/cabo1_solo.mcp.json --strict-mcp-config` |
| `cabo1_srv_log.jsonl` | `0a1f05575305017030d346a2910caebfa7a987230b2fd442db216bda9143b6f3` | 11 198 | La radiografía que el propio servidor escribe de cada llamada del cliente real (protocolo negociado, `client_capabilities`, roots, `request_meta`) durante la sesión de `claude` de abajo |
| `cabo1_claude_run1.json` | `8947088ecd577a2a4b56985871bc08c6e082d8515b749f0cfae21da2a7af28e6` | 3 345 | `claude -p "<prompt de la 1.ª ronda>" --mcp-config bench/salidas-mcp-cabos/cabo1_solo.mcp.json --strict-mcp-config --output-format json` |
| `cabo1_claude_run1.err` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `stderr` de esa misma sesión (vacío) |
| `cabo1_claude_run2.json` | `6e50387b3181918e7e6f605b72250d138afdd3b36465c4eacc89fe450a8bf317` | 9 044 | Idem, 2.ª ronda — preguntó al modelo qué ve de anotaciones/`_meta`/`outputSchema` (§1.2 del informe) |
| `cabo1_claude_run2.err` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | `stderr` de la 2.ª ronda (vacío) |
| `cabo1_claude_run3.json` | `54bad61ea30369ae1225006e81b3d11fa476b8dd49726d3b546e79bec123365c` | 2 348 | Idem, 3.ª ronda — `filex_imagen(corpus/imagen/tipico.png)`, la que confirma que el modelo ve la imagen de verdad |
| `cabo1_permisos.json` | `20a6473e357b0ff2eebf46ad879260a7c87dce6cbbbd67729299404b16666804` | 2 639 | Sesión de `claude` que invoca `filex_radiografia` (marcada `readOnlyHint=true`) bajo el modo de permisos por defecto, para comprobar si la anotación cambia algo (no cambia) |
| `cabo1_ab_imagen.json` | `f9cb751422736eb44be751665ae2cabc67cc53108845e7f45ecab2ea73117598` | 1 972 | Sesión de `claude` con el mismo *prompt* que `cabo1_ab_texto.json` pero pidiendo `filex_imagen`, para el A/B de `cache_creation_input_tokens` de §1.3 |
| `cabo1_ab_texto.json` | `11853c4bc2a064b843437e5228090e55f4092f298d0aeb6f605f6e5bac6ab5e2` | 1 929 | Idem, pidiendo `filex_estructurada` (texto de 58 B) en vez de la imagen |
| `cabo1_smoke_stderr.txt` | `2c5d30c5cf1ee461e773a94eb518841f714b8020d2a7743aa8bc2e8b2f24583f` | 2 823 | `stderr` de una sesión de humo previa (incluye el *timeout* de 30 s de `markitdown`/`docling` contra el comprobador de salud, nota de §1.6) |
| `cabo1_claude_mcp_list.txt` | `e139a821f13cece90abb24cef3fbbb4d1c1474034f2ef020ee8bf094a54ab363` | 563 | `claude mcp list > bench/salidas-mcp-cabos/cabo1_claude_mcp_list.txt` (muestra `filex-cabo1: … ⏸ Pending approval`) |

---

## 3. Cabo 2 — El patrón condicional de roots

Requiere los mismos dos SDK de Python de las dos eras de protocolo (2025-11-25 /
2026-07-28) que el cabo 1 — **ambos venvs borrados**.

| Fichero | sha256 | Bytes | Orden que lo reproduce |
|---|---|---:|---|
| `cabo2_roots.py` | `b4cec7c604abe778ceb74160f3e11e21906998fe4957dbd392b65d8e14d7c94b` | 4 621 | **El entregable del cabo**: `roots_o_nada()` + `raices_efectivas()`. No genera salida por sí solo; lo importa `cabo2_srv.py` |
| `cabo2_srv.py` | `26e0a0a4524bb36da14ab5ffd2fa68bc6fccebdca42f284411f9d7e580d9e73b` | 2 780 | Servidor de contraste con `t_dura` / `t_condicional` / `t_cuerpo`, importando `cabo2_roots.py`. Se lanza una vez por cada combinación (era de protocolo × SDK) |
| `cabo2_cli.py` | `2a050a87db189def850f724404a23e1d34d6c8932076b59ad4c5ad914e2ec8f6` | 3 704 | Cliente Python que ejercita `cabo2_srv.py` con y sin declarar `roots`, en las dos eras: `<venv-era>/Scripts/python.exe cabo2_cli.py --era <legacy\|auto> --roots <si\|no>` (firma exacta reconstruida del informe; el arnés no se conserva con un `--help` documentado) |
| `cabo2_resultados.json` | `427a9300fd73c50b8ad12ee42336746a0c75475fbab84ef1e178e8eec4814c26` | 8 261 | Agregado de las 4 combinaciones (2 eras × roots sí/no) con tiempos y veredictos |
| `cabo2_stderr_auto_conroots.txt` | `2e272f64c4506f5012c0cb9cc40740d019cb11cbbcf2f474e57d458352ae7d8a` | 462 | `stderr` de `cabo2_srv.py` bajo el SDK "auto" (protocolo 2026-07-28) con el cliente declarando roots |
| `cabo2_stderr_auto_sinroots.txt` | `72920c1562a0268359b8deda789e44528869fb7529d94bc9cb2756b36fb43c78` | 235 | Idem, sin roots |
| `cabo2_stderr_legacy_conroots.txt` | `fe2640dcc3d7591c6d302176ac5b7073c304cd743d085ab0393705265303f9be` | 403 | Idem, SDK "legacy" (protocolo 2025-11-25), con roots |
| `cabo2_stderr_legacy_sinroots.txt` | `ea4d4a45a09eb01e7600974b35aac972fc7adba4105aaa96ed8fe13643f950fb` | 235 | Idem, sin roots |

---

## 4. Cabo 3 — La suite de `image-worker-mcp`

Requiere `repos/mcp-refs/image-worker-mcp` clonado (no está en este *worktree*: `repos/`
vacío y en `.gitignore`). Node/`npm` **sí** están disponibles en este WSL (`node` 24.19.0,
`npm` 11.17.0, frente al Node 22.23.2 nativo de Windows con el que se generó originalmente
— versión distinta, mecanismo idéntico).

| Fichero | sha256 | Bytes | Orden que lo reproduce |
|---|---|---:|---|
| `iwm_npm_install.log` | `4f05d614726db14b14ddcde787d140054f90366f8c1c207ef5d9fbba55b18ff0` | 1 182 | `cd repos/mcp-refs/image-worker-mcp && npm install --legacy-peer-deps` (un `npm install` liso falla con `ERESOLVE` porque el repo se publica con `pnpm-lock.yaml` — ver §3.1 del informe) |
| `iwm_vitest.log` | `2b01156b76262484368ed79b1c7935b5556c5af0f37bc91a3af6a06bb2440b2c` | 21 910 | `npx vitest run` dentro del mismo repo (registra `RUN v3.2.7`, 6 ficheros / 117 tests / `EXIT=0` al final del log) |

---

## 5. Cabo 4 — El deadlock en las otras 23 herramientas de `video-audio-mcp`

Requiere `repos/mcp-refs/video-audio-mcp` clonado (no está aquí), `.venv-mcp-vam`
(**borrado**), `ffmpeg.exe` y `taskkill` de Windows — los 6 scripts `.py` de este cabo
tienen `RAIZ = Path("D:/Work/research/FileX")` y llamadas a `taskkill /F /T /PID` escritas
en el código, no como parámetro.

| Fichero | sha256 | Bytes | Orden que lo reproduce |
|---|---|---:|---|
| `cabo4_clasificar.py` | `4ec104eb34282ee3e6b535f2aa7d40c32e6a50621b6b507928392a9bc6d3bdaf` | 4 575 | `python cabo4_clasificar.py [ruta/a/server.py] [salida.json]` — recorre el AST de `server.py` de `video-audio-mcp`; por defecto usa `D:/Work/research/FileX/repos/mcp-refs/video-audio-mcp/server.py` |
| `cabo4_clasificacion.json` | `8e6021087fa384dc2c7af87ee910f4bc17779551323519d72885a3cbb9a6da39` | 10 041 | `python cabo4_clasificar.py` (con los valores por defecto) → clasificación exhaustiva de las 27 `@mcp.tool()` en G1/G2/G3/G4 |
| `cabo4_deadlock.py` | `957295eb4eb057f880831f8f57968548b3a2ed93fb54fb2b85dbe55af754cc97` | 9 286 | `.venv-mcp-vam/Scripts/python.exe cabo4_deadlock.py` — arnés JSON-RPC crudo por stdio, sin SDK, timeout duro por llamada, `taskkill /F /T /PID` sobre el árbol, inventario de `ffmpeg.exe` antes/después |
| `cabo4_resultados.json` | `48da01f9183f1ef47a8e0152fcad603a9eee6b0ab51cd3dcd4219688930e50a9` | 5 447 | Salida de la ejecución anterior: 9 casos (6 deadlocks, timeout 40 s) |
| `cabo4_stderr_G1_set_video_resolution_control.txt` … `cabo4_stderr_G4_health_check.txt` (14 ficheros, todos 577 B) | ver el fichero | 577 c/u | `stderr` de cada caso individual de la tabla de `cabo4_resultados.json` (uno por herramienta/condición: G1 ×4, G2 ×5, G3 ×4, G4 ×1) |
| `cabo4_g3_repeticiones.py` | `74cebe21746310120bee5d518883fab58d97314ce2da66964505ecf9ab28f5c5` | 802 | `.venv-mcp-vam/Scripts/python.exe cabo4_g3_repeticiones.py` — repite `concatenate_videos` (2 vídeos, rama `subprocess`) 3 veces seguidas, importando `cabo4_deadlock` |
| `cabo4_g3_repeticiones.json` | `214e0399609d795e32e657d1ffa87d90ada95266a17e769c445783865b7c9472` | 1 862 | Salida: DEADLOCK/RESPONDE/DEADLOCK (intermitencia 2 de 3) |
| `cabo4_stderr_G3_concat2_rep1.txt` / `rep2.txt` / `rep3.txt` | ver el fichero | 577 c/u | `stderr` de cada una de esas 3 repeticiones |
| `cabo4_g3_diagnostico.py` | `6cd7588d8f473988807d0f8d02d87d99bd6e887eaf7c867418e32ba343113ee5` | 2 974 | `.venv-mcp-vam/Scripts/python.exe cabo4_g3_diagnostico.py` — fotografía el árbol de procesos cada 10 s durante 71 s mientras se reproduce el colgado de `concatenate_videos` |
| `cabo4_g3_diagnostico.json` | `3795d691369196486613d767b7e338ceb128c7894a5dfedf1d2b360e6df01526` | 3 814 | Salida de esa fotografía (el `ffmpeg -i …norm_0.mp4` colgado con `-y` puesto) |
| `cabo4_stderr_G3_diagnostico.txt` | `db4866083482f6d2914dc186ee7411b98e58c6975272d3f2adc6e8d13ecef074` | 577 | `stderr` de esa sesión |
| `cabo4_ffmpeg_control.py` | `b301263b54d5464f348f4280c0235244d716e1f22490038ca23f463e5e48f944` | 4 428 | `python cabo4_ffmpeg_control.py` — Control 1: `ffmpeg` suelto (sin MCP), 5 repeticiones × 5 combinaciones de `-y`/`-nostdin`/`stdin` |
| `cabo4_ffmpeg_control.json` | `c3cc59a2c6844d101f8ce13099a4bd65b181eca952bd8184ccf740faaac65972` | 3 612 | Salida de ese control |
| `cabo4_secuencia.py` | `68f5385ab165ce45abe8498ca8d7ef5b68ac0b102bc4092c0e1882b0a22b49be` | 3 360 | `python cabo4_secuencia.py` — Control 2: la secuencia completa de `concatenate_videos` fuera de MCP, 5 repeticiones × 2 modos de `stdin` |
| `cabo4_secuencia.json` | `a8424c49cd187bf8357a9ea3e00ffe018adc053c2698a9d52041003c4e5399bd` | 4 924 | Salida de ese control (0/10 colgadas) |
| `cabo4_srv_stdin.py` | `5c8e982c173ebb3a2f6a943d303b281cdec685e93986cdb6440dfc46f958b285` | 2 927 | Servidor MCP mínimo con dos herramientas (`conv_heredado` / `conv_devnull`) para el Control 3, **el A/B decisivo dentro de una sesión MCP real** |
| `cabo4_stdin_ab.py` | `b6c90e51a8236a4955cbf3d18c01c2c258fa86fc5f70ee8f9b6d9ee953be70aa` | 2 755 | `.venv-mcp-vam/Scripts/python.exe cabo4_stdin_ab.py` — lanza `cabo4_srv_stdin.py` y ejercita las dos herramientas 5 veces cada una |
| `cabo4_stdin_ab.json` | `ab1f096528595f1f96ba78d03929a18deaad00f0b224b2a9ab94d5d16cfbb550` | 1 308 | Salida: `conv_heredado` 2/5 colgadas, `conv_devnull` 0/5 |
| `cabo4_stderr_conv_heredado_0.txt` … `_4.txt` (5 ficheros, 577 B c/u) | ver el fichero | 577 c/u | `stderr` de cada una de las 5 repeticiones de `conv_heredado` |
| `cabo4_stderr_conv_devnull_0.txt` … `_4.txt` (5 ficheros, 577 B c/u) | ver el fichero | 577 c/u | `stderr` de cada una de las 5 repeticiones de `conv_devnull` |

**Nota sobre los `stderr_*.txt` de 577 B:** son 21 ficheros y los 21 pesan exactamente
577 B — comprobado con `sha256sum`, y **no son el mismo contenido** (hashes distintos por
fichero): es la misma plantilla de cabecera (versión de FFmpeg/`libav*`, banner de
compilación) que `ffmpeg.exe` imprime siempre en `stderr` antes de procesar nada, y aquí no
llegó a producir salida de proceso porque el servidor MCP colgó o el caso terminó antes.

---

## 6. Cabo 5 — La ventana TOCTOU real

Requiere corpus de vídeo/imagen bajo `D:/Work/research/FileX/corpus/…` (rutas Windows
escritas en el código), `ffmpeg`/`ffprobe`, y para `cabo5_linux.py`, un intérprete de
**Windows** que a su vez invoque el lanzador `wsl.exe`.

| Fichero | sha256 | Bytes | Orden que lo reproduce |
|---|---|---:|---|
| `cabo5_toctou.py` | `914af0916ede98e38eaf13c98f6988b7f98abb90b69d7a13fcfe0266c0e01585` | 8 826 | `python cabo5_toctou.py` — sonda de `os.replace()` cada 5 ms mientras `ffmpeg` convierte 5 pares (entrada, operación); mide también el coste de copiar al *staging* y sondea `os.O_NOFOLLOW`/`os.O_PATH`/`os.supports_dir_fd` en Windows |
| `cabo5_toctou.json` | `574496c6864a206d5687c4b91a242521f53058e75e29c99f8afa81d0f42c6bba` | 3 147 | Salida: ventana por caso, coste de copia, tabla `alternativas_posix` |
| `cabo5_envenenamiento.py` | `6f1564691a3c8dda7dbbfc3a2a1bd30fbbb60143463a34641275409d16a887b5` | 4 760 | `python cabo5_envenenamiento.py` — 4 vectores (reemplazar, borrar, escribir en sitio, renombrar el directorio padre) contra `corpus/video/tipico.mp4` mientras `ffmpeg` transcodifica, a los 3 s |
| `cabo5_envenenamiento.json` | `69fcc6f99b8813762604638520d7f40f58c0150ef06290dc99ae7732c06426ba` | 1 513 | Salida: solo (c), escritura en sitio, cambia lo que `ffmpeg` lee, y con `returncode 0` |
| `cabo5_linux.py` | `c2e04b508f199d727837195f4cbf2f71407f6b4538b1d2c4638d9d24501e6df9` | 4 224 | **Desde Windows**: `python cabo5_linux.py` — construye un script bash con los mismos 4 vectores y lo ejecuta con `wsl -e bash -lc "<script>"`; el lector es un `python3` de streaming (abre, lee la mitad, duerme 3 s, termina de leer) |
| `cabo5_linux.json` | `f1b9e21e9bb49bf86b2097fc6a07f58eccdd644d9a04673b4f677c793cb9cb52` | 1 006 | Salida de esa ejecución dentro de WSL2: las 4 permitidas, solo (c) cambia lo que el lector ve |
| `cabo5_inspect.py` | `eb961167b0f845c9d89a4948f74180b28f868ff658a9ba9bce0b8c36aa57108c` | 2 514 | `python cabo5_inspect.py` — compara `ffprobe` contra la copia a *staging* (`shutil.copyfile`) sobre 4 ficheros de tamaño creciente, mediana de 5 |
| `cabo5_inspect.json` | `6d4125af8618042956216c470be97832f8b7fec24dc6d687f4de509b7bf04eaf` | 1 271 | Salida: el cruce está entre 90 y 100 MB; sobre `fuente_4k.mp4` (122 MB) copiar cuesta 1,32× lo que `ffprobe` |

---

## 7. Verificación de tamaño

**75 ficheros**, contados con `find bench/salidas-mcp-cabos -maxdepth 1 -type f | wc -l`
(excluyendo este propio `MANIFIESTO.md`), no por suma manual de las tablas de arriba —la
trampa 48 de `CLAUDE.md` es justo que un recuento manual puede cuadrar por casualidad y no
serlo—. La cifra coincide con el recuento de 75 ya publicado el 21/08/2026 en
`bench/consolidacion-21ago.md` y `bench/consolidacion-3-21ago.md`. Dos filas de muestra para
no repetir la trampa: `cabo1_srv_log.jsonl` (11 198 B) y `iwm_vitest.log` (21 910 B).
