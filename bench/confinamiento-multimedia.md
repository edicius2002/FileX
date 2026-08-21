# Confinamiento de los tres MCP de multimedia, TOCTOU en Linux y coste de la validación en Python

**Cierre de los tres pendientes de la línea de seguridad.** Ejecución medida.
Fecha: 20 de agosto de 2026. Máquina: Windows 10 Home 19045, 12 núcleos, Python 3.11.9,
Node v22.23.2, npm 10.9.8, ffmpeg N-121159. WSL2 (Ubuntu) para la parte 2. Sin GPU.

Cliente MCP = `.venv-mcp-md/Scripts/python.exe` (mcp 1.8.1 + tiktoken).
Arnés = `bench/scripts/mcp_probe_bin.py` (**no modificado**).
Datos crudos: `bench/salidas-confinamiento-mm/`.

> **Convención del proyecto.** Cada afirmación va marcada **MEDIDO** (hay una salida literal en
> `salidas/*.json` que la respalda) o **PENDIENTE** (no se ha ejecutado; queda abierto).

Este informe **no reescribe** las 15 reglas R1-R15 de `bench/mcp-refs-confinamiento.md` §8 (fichero de
otro agente). La §6 de aquí propone qué añaden o corrigen estos resultados a esas reglas.

---

## 0. Resumen ejecutivo

| Pregunta | Respuesta medida |
|---|---|
| ¿Confina la ENTRADA alguno de los tres MCP de multimedia? | **Ninguno de los tres. Cero.** Los tres leyeron ficheros por ruta absoluta y por travesía `..` fuera de la raíz. **MEDIDO** |
| ¿Confina la SALIDA alguno? | **Solo `ffmpeg-mcp-lite`, y solo en 5 de sus 8 herramientas.** `convert/compress/trim/audio/frames` no tienen parámetro de salida y escriben forzosamente en `FFMPEG_OUTPUT_DIR`. `merge` y `subtitles` aceptan `output_path` arbitrario: fuga confirmada. `video-audio-mcp` e `image-worker-mcp` no confinan la salida en ninguna herramienta. **MEDIDO** |
| ¿Se cumple la predicción de la lectura de código («caen los tres»)? | **Sí, sin matices en la entrada.** La única resistencia es la salida forzada de 5/8 herramientas de `ffmpeg-mcp-lite`, que no es un confinamiento de seguridad sino la ausencia de un parámetro. **MEDIDO** |
| ¿Escritura arbitraria fuera de la raíz? | **Sí, demostrada en los tres**, incluida escritura a `C:\Windows\Temp` con `ffmpeg-mcp-lite` e `image-worker-mcp`. **MEDIDO** |
| ¿El vector ADS (`fichero:oculto`) se filtra? | **No en ninguno**: el flujo alternativo llega al motor en los tres. En `image-worker-mcp` los bytes del ADS entraron al buffer del proceso (`readFileSync` tuvo éxito). **MEDIDO** |
| ¿Oráculo de existencia? | **`ffmpeg-mcp-lite` e `image-worker-mcp`, sí, sobre todo el disco** (mensajes distintos para «existe» y «no existe»). `video-audio-mcp` lo tiene también pero enterrado bajo 1,5 KB de banner de ffmpeg. **MEDIDO** |
| ¿Se gana la carrera TOCTOU en Linux/WSL? | **No: 0 fugas en 102 400 intentos.** Pero la hipótesis de la duty cycle se confirma: el atacante coloca el enlace con ~98 % de éxito (vs 21 % en Windows). No se gana porque `realpath` rechaza el enlace antes de leer, no por accidente del SO. **MEDIDO (§3).** |
| ¿Cuánto cuesta validar una ruta en Python y qué topes imponer? | `realpath` es **superlineal**: ~6 000 componentes = **5–16 s** (DoS de una sola llamada). Topes: **≤4 096 chars, ≤64 componentes, ≤16 enlaces**, impuestos **antes** de `realpath`. **MEDIDO (§4-5).** |

**Titular de la parte 1:** frente a la referencia oficial `filesystem` (que denegó 28 de 29 vectores),
los tres MCP de multimedia **no tienen frontera ninguna en la entrada** y **escriben ficheros fuera de
cualquier raíz**. Como estos servidores **escriben y lanzan procesos**, el fallo no es solo lectura
hacia el contexto: es **escritura arbitraria en el disco del anfitrión**. **MEDIDO.**

---

## 1. Montaje

### 1.1 Servidores y lanzamiento

| Servidor | Lenguaje | Herramientas | `tokens_catalogo` | Lanzamiento |
|---|---|---:|---:|---|
| `ffmpeg-mcp-lite` | Python | **8** | **2 322** | `python -m ffmpeg_mcp_lite`, venv propio `.venv-mm-ffmpeg` (mcp 1.13), `PYTHONPATH=…/src`, `FFMPEG_OUTPUT_DIR=<RAIZ>` |
| `video-audio-mcp` | Python | **27** | **7 964** | `python server.py`, venv propio `.venv-mm-vamcp` (mcp 1.29 + ffmpeg-python 0.2.0) |
| `image-worker-mcp` | TypeScript | **2** | **1 177** (v0.0.6) | `npx -y @boomlinkai/image-worker-mcp`, `S3_BUCKET=dummy` |

**Notas de montaje, todas MEDIDO:**
- **Un venv por servidor Python.** `mcp>=2.0.0` (que pip resuelve por defecto) **elimina
  `mcp.server.fastmcp`** y rompe ambos servidores con `ModuleNotFoundError: No module named
  'mcp.server.fastmcp'`. Hubo que fijar `mcp<2` en los dos venvs. Confirma la advertencia del encargo.
- **`image-worker-mcp` muere al arrancar sin credenciales de nube.** Su constructor llama a
  `UploadServiceFactory.create()`, que hace `S3EnvConfigSchema.parse({S3_BUCKET: …})` con
  `z.string().min(1)`. Sin `S3_BUCKET` en el entorno, lanza `McpError` y el proceso no llega a servir
  `resize_image`. Basta `S3_BUCKET=dummy` (las claves AWS son opcionales) para que arranque. Es el
  fallo que `analysis/00-mcp-componentes.md` fila 105 predijo: *«el servidor muere al arrancar aunque el
  usuario solo quisiera redimensionar»*. **MEDIDO.**
- **`video-audio-mcp` cuelga la sesión si el destino de salida ya existe.** Usa `ffmpeg-python`
  `.run()` **sin `overwrite_output=True`**, así que ffmpeg no recibe `-y`, pregunta `Overwrite? [y/N]`
  y **lee de la tubería JSON-RPC heredada como stdin**. Para evitarlo, **todos los destinos de salida
  de las pruebas fueron rutas frescas e inexistentes**, borradas antes de cada corrida. Con esa
  disciplina no se colgó ni una vez y no quedó ningún ffmpeg huérfano (verificado con `tasklist`).
  `ffmpeg-mcp-lite` **sí** pasa `-y` en todas sus herramientas, así que no tiene este problema.

### 1.2 El árbol de pruebas

`bench/salidas-confinamiento-mm/sandbox/`:

```
raiz/                 <- RAÍZ DECLARADA (para ffmpeg-mcp-lite = FFMPEG_OUTPUT_DIR;
  video.mp4              los otros dos no aceptan ninguna raíz)
  video2.mp4
  entrada.png
  entrada.png:oculto  <- ADS: "ADS_OCULTO_MM_777"
  subs.srt
fuera/                <- HERMANA, FUERA de la raíz, pero DENTRO de mi sandbox
  secreto.txt            (así demuestro escritura fuera de la raíz sin tocar nada del usuario)
  secreto.txt:oculto  <- ADS: "ADS_OCULTO_FUERA_888"
  secreto.png
  video_fuera.mp4
```

Todos los ficheros señuelo están **dentro de mi sandbox**. Para probar la **escritura fuera de la raíz
declarada** se apuntó a `sandbox/fuera/` (fuera de la raíz que ve el servidor, dentro de mi sandbox) y,
en dos casos, a `C:\Windows\Temp\filex_no_debe_existir_*` (carpeta temporal del sistema, **borrada por
el arnés al terminar** — verificado que no queda). No se escribió, modificó ni borró nada del usuario.
Generación de specs: `bench/salidas-confinamiento-mm/gen_specs_mm.py` (con `json.dump`, no heredocs).

---

## 2. Tabla de ataques por servidor

Abreviaturas: `«R»` = `…\sandbox\raiz` (raíz declarada), `«F»` = `…\sandbox\fuera` (fuera de la raíz).
**Lectura y escritura van separadas.** Todos los mensajes son cita literal de `salidas/*.json`.

### 2.1 `ffmpeg-mcp-lite` (8 herramientas)

**LECTURA (entrada) — vía `ffmpeg_get_info`, que es `ffprobe`, solo lectura y falla rápido:**

| # | Vector | Petición | Resultado | Mensaje literal al modelo | Veredicto |
|---|---|---|---|---|---|
| FF-L0 | Control: dentro de la raíz | `ffmpeg_get_info «R»\video.mp4` | **OK** | JSON con metadatos (`format_name`, `duration`…) | Correcto |
| FF-L1 | **Absoluta fuera de la raíz** | `ffmpeg_get_info «F»\video_fuera.mp4` | **CONCEDIDO** | JSON completo con `"file": "…\fuera\video_fuera.mp4"`, `isError=false` | **FUGA.** Lee metadatos de un fichero fuera de la raíz |
| FF-L2 | **Travesía `..`** | `ffmpeg_get_info «R»\..\fuera\video_fuera.mp4` | **CONCEDIDO** | idéntico a FF-L1 | **FUGA.** `Path(...).resolve()` normaliza el `..` pero **no compara contra ninguna raíz** |
| FF-L3 | Fichero real del sistema (existe, no media) | `ffmpeg_get_info C:\Windows\win.ini` | **DENEGADO por formato** | `Error executing tool ffmpeg_get_info: ffprobe failed:` | La ruta **se alcanzó** (existe); ffprobe no la parsea. No es una denegación de confinamiento |
| FF-L4 | Fichero inexistente fuera | `ffmpeg_get_info C:\Windows\no_existe_jamas.ini` | **DENEGADO** | `Error executing tool ffmpeg_get_info: File not found: C:\Windows\no_existe_jamas.ini` | **ORÁCULO.** Mensaje distinto de FF-L3 ⇒ distingue existe/no-existe sobre todo el disco, y **eco de la ruta** |
| FF-L5 | **ADS dentro de la raíz** | `ffmpeg_get_info «R»\entrada.png:oculto` | **alcanzado** | `ffprobe failed:` (no `File not found`) | **HUECO.** `Path(...:oculto).exists()` = `True`; el flujo alternativo llega a ffprobe. No se filtra el `:` |

**ESCRITURA (salida):**

| # | Vector | Petición | Resultado | Mensaje literal | Veredicto |
|---|---|---|---|---|---|
| FF-E1 | Salida sin parámetro (confinada) | `ffmpeg_convert «R»\video.mp4 → mp3` | **CONFINADA a la raíz** | `Converted successfully: …\raiz\video_converted.mp3` | **Correcto por ausencia de parámetro.** `convert` no deja elegir destino; cae en `FFMPEG_OUTPUT_DIR`. Igual en `compress/trim/audio/frames` (5 de 8) |
| FF-E2 | **`output_path` arbitrario fuera** | `ffmpeg_merge [«R»\video.mp4, «R»\video2.mp4] → «F»\merged_LEAK.mp4` | **CONCEDIDO** | `Merged 2 files successfully: …\fuera\merged_LEAK.mp4` | **FUGA declarada (`merge.py:38-39`), CONFIRMADA.** Fichero de 26 411 bytes escrito fuera de la raíz |
| FF-E3 | **Escritura a `C:\Windows\Temp`** | `ffmpeg_merge […] → C:\Windows\Temp\filex_no_debe_existir_merge.mp4` | **CONCEDIDO** | `Merged 2 files successfully: C:\Windows\Temp\…` | **Escritura arbitraria en el sistema.** Confirmada en disco y luego borrada |
| FF-E4 | `output_path` arbitrario (subtitles) | `ffmpeg_add_subtitles «R»\video.mp4 → «F»\subbed_LEAK.mp4` | **Ruta aceptada; ffmpeg falló** | `ffmpeg add subtitles failed: <banner ffmpeg…>` | **El `output_path` se aceptó sin comprobación** (fuga `subtitles.py:72-73`). El fallo es del filtro `subtitles` de ffmpeg al escapar el `:` de la ruta en Windows, **no** del confinamiento |

**Veredicto `ffmpeg-mcp-lite`:** entrada **sin confinar** (FF-L1, FF-L2), oráculo de existencia sobre
todo el disco (FF-L4 vs FF-L3), ADS no filtrado (FF-L5), salida confinada solo por **ausencia de
parámetro** en 5/8 y **fugada** en `merge` (confirmada) y `subtitles` (ruta aceptada). **MEDIDO.**

### 2.2 `image-worker-mcp` (2 herramientas, TypeScript)

`resize_image` lee `imagePath` con `fs.readFileSync` tras pasarlo por `normalizeFilePath` (que **solo
des-escapa caracteres de shell, no es una función de seguridad**) y escribe `outputPath` con `sharp`.
**No importa el módulo `path` de Node en ningún punto de `src/`.**

| # | Dir. | Vector | Petición | Resultado | Mensaje literal | Veredicto |
|---|---|---|---|---|---|---|
| IW-1 | R+W | Control dentro | `resize_image imagePath=«R»\entrada.png → «R»\iw_control_out.png` | **OK** | `{"format":"png","savedTo":"…\raiz\iw_control_out.png","source":"file"}` | Correcto |
| IW-2 | **R+W** | **Fuera de la raíz** | `imagePath=«F»\secreto.png → «F»\iw_read_LEAK.png` | **CONCEDIDO** | `{…"savedTo":"…\fuera\iw_read_LEAK.png"}` | **FUGA doble:** lee imagen fuera y escribe fuera |
| IW-3 | **R** | **Fichero real del sistema** | `imagePath=C:\Windows\win.ini` | **LEÍDO** | `Error processing image: Input buffer contains unsupported image format` | **FUGA.** `readFileSync` **tuvo éxito** (los bytes de `win.ini` entraron al buffer); solo falla `sharp` después. La lectura arbitraria ocurrió |
| IW-4 | R | Inexistente (oráculo) | `imagePath=C:\Windows\no_existe_jamas.png` | **DENEGADO** | `MCP error -32602: Failed to read image from path: C:\Windows\no_existe_jamas.png. ENOENT: no such file or directory, open 'C:\Windows\no_existe_jamas.png'` | **ORÁCULO** + eco doble de la ruta |
| IW-5 | **W** | Escritura fuera | `imagePath=«R»\entrada.png → «F»\iw_write_LEAK.png` | **CONCEDIDO** | `{…"savedTo":"…\fuera\iw_write_LEAK.png"}` | **FUGA.** Escritura fuera de la raíz |
| IW-6 | **R+W** | Travesía `..` | `imagePath=«R»\..\fuera\secreto.png → «F»\iw_trav_LEAK.png` | **CONCEDIDO** | `{…"savedTo":"…\fuera\iw_trav_LEAK.png"}` | **FUGA.** Travesía en lectura y escritura |
| IW-7 | R | **ADS dentro de la raíz** | `imagePath=«R»\entrada.png:oculto` | **LEÍDO** | `Error processing image: Input buffer contains unsupported image format` | **HUECO.** `readFileSync` leyó el flujo alternativo (`ADS_OCULTO_MM_777`); solo falla `sharp` |
| IW-8 | **W** | Escritura a `C:\Windows\Temp` | `imagePath=«R»\entrada.png → C:\Windows\Temp\filex_no_debe_existir_iw.png` | **CONCEDIDO** | `{…"savedTo":"C:\Windows\Temp\…"}` | **Escritura arbitraria en el sistema.** Confirmada y borrada |

**Veredicto `image-worker-mcp`: cero confinamiento en ninguna dirección.** Lee cualquier ruta (incluidos
`win.ini` y flujos ADS, con los bytes realmente cargados en el proceso), escribe cualquier ruta
(incluido `C:\Windows\Temp`), y es oráculo de existencia con eco de la ruta. **MEDIDO.**

### 2.3 `video-audio-mcp` (27 herramientas)

Ninguna herramienta valida rutas: pasan `video_path`/`output_..._path` directos a `ffmpeg-python`.
Todas reencodifican salvo `health_check`, así que las lecturas se probaron con entradas no-media
(fallo rápido) y la escritura con un destino fresco. **Todas devuelven el error como cadena con
`isError=false`** (el antipatrón de `analysis/00-mcp-componentes.md` fila 144).

| # | Dir. | Vector | Petición | Resultado | Mensaje literal (recorte) | Veredicto |
|---|---|---|---|---|---|---|
| VA-0 | — | Control | `health_check` | **OK** | `Server is healthy!` | Correcto |
| VA-1 | R | Fichero del sistema (existe) | `extract_audio_from_video video_path=C:\Windows\win.ini → «F»\va_sys_out.mp3` | **alcanzado** | `Error extracting audio: ffmpeg version N-121159… <1,5 KB de banner>`, `isError=false` | **FUGA.** ffmpeg **abrió** `win.ini` (no lo denegó); falla por no ser media. Sin confinamiento |
| VA-2 | R | Inexistente | `video_path=C:\no_existe_jamas_xyz.mp4` | **DENEGADO** | mismo volcado de ffmpeg (`No such file`, enterrado al final), `isError=false` | Oráculo, pero **enterrado** bajo el banner: el modelo no puede distinguirlo de VA-1 sin leer 1,5 KB |
| VA-3 | **R** | **Travesía `..` fuera** | `video_path=«R»\..\fuera\video_fuera.mp4 → «F»\va_trav_out.mp3` | **CONCEDIDO (leído)** | volcado de ffmpeg (abrió el fichero, sin pista de audio), `isError=false` | **FUGA.** ffmpeg abrió y decodificó un fichero fuera de la raíz vía travesía |
| VA-4 | **W** | **Escritura fuera** | `video_path=«R»\video.mp4 → «F»\va_write_LEAK.mp3` | **CONCEDIDO** | `Audio extracted successfully to …\fuera\va_write_LEAK.mp3` | **FUGA.** mp3 de 8 897 bytes escrito fuera de la raíz |
| VA-5 | R | **ADS dentro de la raíz** | `video_path=«R»\entrada.png:oculto` | **alcanzado** | volcado de ffmpeg, `isError=false` | El `:oculto` llegó a ffmpeg (no filtrado) |

**Veredicto `video-audio-mcp`: cero confinamiento en ninguna dirección.** Entrada y salida arbitrarias;
escritura fuera de la raíz confirmada (VA-4); el oráculo existe pero está sepultado bajo el banner de
ffmpeg que reenvía crudo en cada fallo. **MEDIDO.**

---

## 2.4 El veredicto sobre la predicción de la lectura de código

`analysis/00-mcp-componentes.md` §5 (fila 4) predecía: *«`../../` y rutas absolutas… la lectura predice
que los tres caen»*. **Confirmado, y con más detalle del que la lectura afirmaba:**

- **La entrada cae en los tres, sin una sola excepción.** Ruta absoluta y travesía `..` leyeron ficheros
  fuera de la raíz en `ffmpeg-mcp-lite`, `video-audio-mcp` e `image-worker-mcp`. **MEDIDO.**
- **La escritura cae en los tres.** Fichero escrito fuera de la raíz confirmado en disco en los tres
  (merge → `«F»`, resize → `«F»`, extract_audio → `«F»`), y en dos de ellos también a `C:\Windows\Temp`.
  Es el punto que la lectura no había ejecutado y que **importa más que en un MCP documental**: aquí el
  fallo de confinamiento es **escritura arbitraria**, no solo lectura hacia el contexto. **MEDIDO.**
- **La única «resistencia» —la salida forzada de 5/8 herramientas de `ffmpeg-mcp-lite`— no es un
  confinamiento.** Es la ausencia de un parámetro `output_path`. En cuanto una herramienta lo tiene
  (`merge`, `subtitles`), la ruta arbitraria se acepta. Frente a la referencia `filesystem`, que
  **valida también el destino** de escritura y movimiento (`bench/mcp-refs-confinamiento.md` §2.5), los
  tres de multimedia no validan el destino en absoluto.
- **El ADS, único vector que concedió acceso contra la referencia oficial (W9), aquí no se filtra en
  ninguno.** Diferencia: en `filesystem` W9 devolvió el *contenido* del ADS; aquí el flujo alternativo
  llega al motor (ffprobe/ffmpeg/sharp) y, salvo que fuera media válida, se rechaza — pero **en
  `image-worker-mcp` los bytes del ADS sí entraron al buffer del proceso** (`readFileSync` con éxito).
  El `:` no se filtra en ninguno de los tres. **MEDIDO.**

**Contraste con la referencia oficial (todo MEDIDO):**

| | `filesystem` (ref. oficial) | `ffmpeg-mcp-lite` | `video-audio-mcp` | `image-worker-mcp` |
|---|---|---|---|---|
| Travesía `..` (lectura) | ❌ denegada (8 variantes) | ✅ **leída** | ✅ **leída** | ✅ **leída** |
| Ruta absoluta arbitraria (lectura) | ❌ denegada | ✅ **leída** | ✅ **abierta por ffmpeg** | ✅ **leída (bytes al buffer)** |
| Escritura fuera de la raíz | ❌ denegada (valida destino) | ✅ **`merge`/`subtitles`** | ✅ **todas** | ✅ **todas** |
| Escritura a `C:\Windows\Temp` | ❌ | ✅ | ✅ (no probada, misma clase) | ✅ |
| Concepto de raíz | sí, denegar por defecto | **solo salida por defecto** | **ninguno** | **ninguno** |
| Oráculo de existencia | no fuera de la raíz | **sí, todo el disco** | sí (enterrado) | **sí, todo el disco** |
| ADS (`:oculto`) | concede el contenido (W9) | llega a ffprobe | llega a ffmpeg | **bytes al buffer** |

---

## 3. TOCTOU en Linux/WSL

Repetición de la fase B de `bench/mcp-refs-confinamiento.md` §4.3 en **WSL2, Ubuntu 26.04 LTS**, kernel
`6.18.x-microsoft-standard-WSL2`, **Node v24.19.0** dentro de WSL (ya presente), cliente MCP en un venv
Python propio de WSL con `mcp`. **Sandbox en ext4 NATIVO** bajo `$HOME` (confirmado con `df -T`), **no**
en `/mnt/d` — clave, porque en DrvFs el `unlink` no es POSIX puro y sesgaría igual que Windows.
Diseño reutilizado del `toctou_probe.py` de Windows (3 hilos atacantes alternando `race.txt` entre
fichero benigno y enlace a `…/prohibido/secreto.txt` con la marca `SECRETO_PROHIBIDO_ABCDEF`, mientras
el cliente dispara `read_text_file` concurrente). Datos: `salidas-confinamiento-mm/toctou-linux/`.

### 3.1 Métricas por fase (MEDIDO)

| Fase | Llamadas | s | Swaps atac. | err_symlink | Benignas | Denegadas | ENOENT | Vacías | **Fugas** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Calibración B (200×16) | 3 200 | 6,2 | 10 502 | 440 | 410 | 110 | 2 609 | 71 | **0** |
| Grande B (3 200×16) | 51 200 | 108 | 234 868 | 4 699 | 20 195 | 7 531 | 16 558 | 6 910 | **0** |
| Grande B2 (500×96, `UV_THREADPOOL_SIZE=1`) | 48 000 | 76 | 141 847 | 4 512 | 21 224 | 8 063 | 13 330 | 5 381 | **0** |

**Total agregado: 102 400 llamadas, 0 fugas.**

### 3.2 Duty cycle del atacante — Linux vs el 21 % de Windows

**La hipótesis del encargo SE CONFIRMA. MEDIDO.** En Windows el 79 % de los `os.symlink` del atacante
fallaba con `[WinError 183]` porque el `os.remove` previo no podía borrar un fichero que el servidor
tenía abierto → solo ~21 % de duty cycle. **En Linux/ext4, `unlink` sobre fichero abierto siempre
funciona: el atacante coloca el enlace con ~98 % de éxito** (`err_symlink` = 4 699/234 868 ≈ **2 %**, y
esos fallos son `[Errno 17] File exists` por carrera *entre* los 3 hilos atacantes, **no** bloqueos del
servidor). Visto desde el servidor: **14,7 %–16,8 %** de las lecturas resolvieron al enlace malicioso
(condicionado a las que resolvieron a *algún* fichero, ~27 %). La ventana se tocó masivamente:
7 531 + 8 063 denegaciones son cada una una lectura que pilló el enlace ya colocado.

### 3.3 Veredicto: **la carrera NO se gana en Linux tampoco — y esta vez por el motivo bueno**

**MEDIDO: 0 fugas en 102 400 intentos**, ni con la ventana ensanchada (B2). Pero **la causa es distinta
a la de Windows y esto es lo importante:**

- En **Windows** no se ganó en parte por un **accidente del SO** (el bloqueo de fichero abierto le negaba
  al atacante el 79 % de sus intentos). Ese accidente **no existe en POSIX**.
- En **Linux** el atacante **sí domina el fichero** (~98 % duty cycle) y aun así no hubo fuga, porque
  **`validatePath` resuelve `realpath()` y RECHAZA el enlace que apunta fuera de la allowlist antes de
  leer**, y el `readFile` posterior abre la **ruta canónica ya validada**. Las miles de denegaciones
  prueban que la ventana entre `realpath` y `readFile` se cruza constantemente; la coincidencia exacta
  que hace falta para fugar (validar viendo el fichero benigno → swap al enlace → `readFile` sigue el
  enlace) no ocurrió ni una vez.

Denegación típica en Linux (**MEDIDO**, cita literal):

```
Access denied - symlink target outside allowed directories: /home/…/toctou_sandbox/prohibido/secreto.txt not in /home/…/toctou_sandbox/permitido
```

**Lo que esto significa para FileX y para R8.** El resultado **refuerza** R8 pero **cambia su
fundamento**. La referencia oficial resiste la carrera en POSIX **porque opera sobre la ruta canónica
dentro del mismo proceso** — una ventana de microsegundos. En FileX la ventana entre validar y que
**ffmpeg, LibreOffice o sharp** terminen de leer son **segundos o minutos**, y **quien abre el fichero
es otro proceso que no vuelve a llamar a `realpath` ni conoce la allowlist** (lo hemos visto en la §2:
los tres MCP de multimedia pasan la ruta cruda del modelo directamente al binario externo). La defensa
del proceso único no se traslada. Por eso **R8 (copiar la entrada a un staging privado y pasar al motor
externo solo la ruta del staging) sigue siendo necesaria**, no porque la carrera intra-proceso se gane
—no se gana en ninguno de los dos SO— sino porque **el motor externo es un segundo TOCTOU con una
ventana de minutos que ninguna validación de rutas cubre**. **MEDIDO como límite, no como demostración
de fuga.**

**PENDIENTE:** no se probó reducir la agresividad del atacante (el `ENOENT` domina 30–50 %; menos churn
podría estabilizar el enlace y estrechar el hueco benigno→enlace), ni una versión antigua del servidor
sin el rechazo por `realpath`.

---

## 4. Coste de la validación de rutas en Python

Banco: `bench/salidas-confinamiento-mm/py-validacion/bench_validacion.py`; datos crudos en
`resultados.json` / `resultados.txt`. Python 3.11.9, disco `D:` NTFS, mediana de varias repeticiones.
**Todo MEDIDO.**

### 4.1 Coste por operación frente al nº de componentes

Rutas sintéticas inexistentes `C:/comp/comp/…`. Tiempo mediano por llamada:

| N comp | len (chars) | `normcase` | `normpath` | `abspath` | **`realpath`** | `is_relative_to` | `startswith` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 52 | 1,26 µs | 0,78 µs | 1,94 µs | **1,35 ms** | 23,8 µs | 0,25 µs |
| 100 | 502 | 6,18 µs | 3,43 µs | 8,17 µs | **53,0 ms** | 74,0 µs | 0,26 µs |
| 1 000 | 5 002 | 41,1 µs | 28,1 µs | 79,9 µs | **1,266 s** | 362,7 µs | 0,31 µs |
| 10 000 | 50 002 | 648,6 µs | 328,7 µs | 734,8 µs | (colapso, ver ↓) | 3,70 ms | 0,34 µs |

- **`normcase`/`normpath`/`abspath` son lineales y despreciables** (µs incluso a 10 000 componentes).
- **`is_relative_to` es lineal pero ~10× más caro** que `normpath` (construye `PurePath` y trocea).
- **`startswith` es constante, ~0,3 µs**, sea cual sea el tamaño. Es la línea base barata.
- **`realpath` es claramente SUPERLINEAL** (24×–39× por década): es 1 syscall por componente sobre ruta
  inexistente. Confirmado en `ntpath.py`: `_getfinalpathname_nonstrict` recorre la ruta componente a
  componente, 2 syscalls por iteración y un `join` que reconstruye una cadena cada vez más larga
  (O(N) syscalls, O(N²) trabajo de cadenas).
- El "abaratamiento" a 10 000 componentes **no es una mejora**: la ruta supera el límite de 32 767
  caracteres de Windows, `_getfinalpathname` falla con `ERROR_INVALID_NAME` y **`realpath` devuelve la
  ruta SIN RESOLVER**. Por encima de ~32 768 chars la validación es rápida pero **no valida nada** — el
  peor de los dos mundos.

### 4.2 El mapa del DoS: barrido fino de `realpath`

| N comp | len | `realpath` bajo `C:/` | µs/componente |
|---:|---:|---:|---:|
| 8 (fichero real existente) | — | **132–202 µs** (línea base) | — |
| 50 | 252 | **6,2 ms** | 124 |
| 100 | 502 | **31,3 ms** | 313 |
| 200 | 1 002 | 93 ms | 465 |
| 1 000 | 5 002 | **252 ms** | 252 |
| 4 000 | 20 002 | **3,61 s** | 902 |
| **6 000** | 30 002 | **7,64 s (16,0 s en otra corrida)** | 1 273 |
| ≥8 000 | ≥40 002 | ~1 ms → *no resuelve* (pasa el límite de 32 767 chars) | — |

**El ataque concreto: ~6 000 componentes cortos (justo por debajo de 32 767 chars) → 5–16 segundos de
CPU/IO por UNA sola llamada MCP.** Un agente hostil manda una ruta así y bloquea el proceso.

### 4.3 Los `..` NO son un vector de DoS

`normpath` colapsa los `..` en **tiempo lineal y barato** antes de tocar el disco. 100 000 `..`
(300 KB de ruta) = **2,20 ms** en `normpath`; y `realpath` se mantiene **casi constante (~0,3 ms)** con
`..` intercalados, porque `realpath` llama a `normpath` primero y `a/..` se colapsa a 2 componentes
antes de la E/S. **El peligro no son los `..` (eso es corrección, no coste), son los componentes que
NO se colapsan.** **MEDIDO.**

### 4.4 Cadena de enlaces simbólicos encadenados — hay un límite del SO, pero Python lo ignora

Cadena `l_K → l_{K-1} → … → objetivo_real`. `os.symlink` funcionó (Modo Desarrollador activo); se
crearon **300 enlaces sin un fallo**, limpiados al terminar.

| K enlaces | `realpath(strict=False)` | ¿resuelve? | `realpath(strict=True)` | `open()` |
|---:|---:|---|---|---|
| 1–**31** | 0,9–3,4 ms | SÍ | ok | **ok** |
| **32** | 5,3 ms | **SÍ** | **OSError winerror 1921** | **OSError errno 22** |
| 120 | 12,1 ms | SÍ | winerror 1921 | errno 22 |
| **300** | **17,1 ms** | SÍ | winerror 1921 | errno 22 |

**El SO aguanta 31 enlaces encadenados y falla en el nº 32** (`ERROR_CANT_RESOLVE_FILENAME`). Pero
**`os.path.realpath(strict=False)` de Python NO tiene ningún límite de profundidad**: siguió resolviendo
cadenas de 300 enlaces (~35–88 µs/enlace, memoria O(K)), **validando rutas que `open()` rechaza
siempre**. Es una **discrepancia validación/uso**: FileX daría por buena una ruta inutilizable, y la
profundidad (y el coste) los elige el atacante. `strict=True` **sí** respeta el límite del SO y lanza
`OSError`. **MEDIDO.**

### 4.5 Longitud pura frente a nº de componentes

A **igual longitud total** (50 002 chars), el coste **léxico** apenas cambia entre 10 000 componentes y
1 solo componente (`normpath` 392 µs vs 253 µs): **el coste léxico depende de la longitud en caracteres,
no del reparto.** El **nº de componentes solo dispara `realpath`**. Por eso hacen falta **dos topes
distintos**: uno de longitud y otro de nº de componentes. **MEDIDO.**

---

## 5. Topes recomendados para FileX

Los tres topes se imponen **ANTES de cualquier llamada que toque disco** (`realpath`/`stat`/`open`),
sobre la cadena cruda del agente, con coste puramente léxico. **Rechazar una ruta hostil cuesta
~0,16 µs** (medido), frente a los **hasta 16 s** que cuesta dejarla llegar a `realpath`: factor ~10⁸.

| Tope | Valor recomendado | Justificación medida |
|---|---|---|
| **(a) Longitud máxima de ruta** | **4 096 caracteres** | El peor caso de `realpath` vive entre 20 000 y 32 767 chars (3,6–16 s); por encima de 32 768 el SO deja de resolver y `realpath` **devuelve sin validar**. 4 096 deja margen enorme sobre cualquier ruta real (`MAX_PATH` = 260) y acota el coste léxico peor caso en ~30 µs |
| **(b) Nº máximo de componentes** | **64 segmentos** | `realpath` es ~1 syscall/componente y superlineal: 50→6 ms, 100→31 ms, 500→159 ms, 6 000→7,6–16 s. Con 64 el peor caso es ~8–10 ms (orden de la línea base real, 0,2 ms) y 3 órdenes por debajo de la zona de congelación. Contar segmentos **tras `normpath`** (que colapsa los `..` gratis) o contar separadores en crudo |
| **(c) Profundidad máx. de resolución de enlaces** | **16 enlaces** | El SO falla en el 32; `realpath(strict=False)` **no para** (resolvió 300). 16 queda bajo el límite real, garantiza que lo que FileX valida el SO lo puede abrir, y acota el coste en ~1,5 ms. Ninguna instalación legítima encadena >2–3 enlaces. Impónlo tú con un bucle `os.readlink`/`os.lstat` con contador ≤16, **o** usa `realpath(strict=True)` y trata `winerror 1921` como rechazo |

**Reglas de implementación derivadas (todo MEDIDO):**
1. **Orden obligatorio:** `len()` → contar separadores → `normpath` (µs, colapsa `..`) → **volver a
   contar componentes** → contención léxica → **solo entonces** `realpath`. Nunca `realpath` primero.
2. **En el camino caliente, contención con `startswith` normalizado, no `is_relative_to`:** 0,3 µs
   constante frente a 24–74 µs (y 3,7 ms en el caso hostil). Obligatorio `os.path.normcase` en ambos
   lados y añadir `os.sep` al prefijo del directorio base.
3. **Impón la profundidad de enlaces tú mismo**; no confíes en que `realpath(strict=False)` pare.
4. **`realpath(strict=False)` sobre rutas inexistentes devuelve una ruta ADIVINADA** (prefijo resuelto
   + cola sin resolver). Para escritura, resuelve el **directorio padre existente** y valida la
   contención de ese padre, no la ruta completa inexistente.
5. Los `..` no necesitan tope propio (100 000 `..` = 2,2 ms); basta `normpath` + contención posterior.

---

## 6. Qué añade o corrige esto a las reglas R1-R15

*(Propuesto aquí; **no** se toca `bench/mcp-refs-confinamiento.md`, que es de otro agente.)*
Ninguna de las 15 reglas se **refuta**; tres se **refuerzan con evidencia nueva** y hay **dos reglas
nuevas** que los MCP de multimedia hacen imprescindibles y que R1-R15 no cubrían.

### Refuerzos a reglas existentes

- **R6 (denegar por defecto; ninguna raíz ⇒ no arrancar) — reforzada por el peor caso posible.** Los
  tres MCP de multimedia son la demostración de lo contrario a R6: `video-audio-mcp` e `image-worker-mcp`
  **no tienen concepto de raíz**, y `ffmpeg-mcp-lite` solo tiene una raíz de **salida por defecto** que
  `merge`/`subtitles` saltan. Resultado medido: lectura y **escritura arbitrarias**, incluida escritura
  a `C:\Windows\Temp`. R6 debe leerse como: *sin raíz de lectura y raíz de escritura configuradas, el
  motor no se registra.*

- **R8 (staging privado antes del motor externo) — reforzada y con el fundamento corregido (ver §3.3).**
  La carrera intra-proceso no se gana **en ninguno de los dos SO** (0 fugas en 52 800 en Windows +
  102 400 en Linux), pero eso mide la ventana equivocada. La ventana que importa en FileX es la del
  **binario externo**, que los tres MCP de multimedia abren pasándole **la ruta cruda del modelo**
  (medido en §2). R8 es la única defensa para esa ventana.

- **R9 (raíz de lectura ≠ raíz de escritura; no sobrescribir en silencio) — reforzada.** `ffmpeg-mcp-lite`
  ilustra la mitad buena (`convert` confina la salida por ausencia de parámetro) y la mala en la misma
  base de código (`merge`/`subtitles` aceptan `output_path` arbitrario). La raíz de escritura debe ser
  **una lista inmutable del núcleo**, no un parámetro por herramienta.

### Reglas nuevas que el multimedia hace imprescindibles

- **R16 (nueva) — el ARGUMENTO DE SALIDA es tan peligroso como el de entrada; valida el destino contra la
  raíz de escritura ANTES de invocar el motor.** La referencia `filesystem` ya validaba el destino de
  `write_file`/`move_file`; los tres MCP de multimedia **no**, y por eso escriben fuera de la raíz. Como
  el motor externo **crea el fichero él mismo**, la escritura arbitraria no la comete FileX sino ffmpeg
  o sharp: hay que confinar el `output_path` **antes** de construir la línea de comando. Corolario
  medido: **escribir a un staging de salida propio y mover al destino final solo tras validar** (mismo
  patrón que R8, en la dirección de salida). Evidencia: FF-E2, FF-E3, IW-5, IW-8, VA-4.

- **R17 (nueva) — impón topes léxicos de longitud, nº de componentes y profundidad de enlaces ANTES de
  llamar a `realpath`.** La propia validación es un vector de DoS: una ruta de ~6 000 componentes cuesta
  **5–16 s** en `realpath` (§4.2), y `realpath(strict=False)` resuelve cadenas de enlaces **sin límite**
  validando rutas que `open()` rechaza (§4.4). Topes medidos: **≤4 096 chars, ≤64 componentes, ≤16
  enlaces** (§5), a coste de rechazo de ~0,16 µs. Esta regla es **anterior** a R1 en el orden de
  ejecución: se aplica sobre la cadena cruda, antes incluso del predicado léxico de contención.

### Matices medidos que conviene anotar en R3, R4 y R11

- **R4 (mensaje opaco y constante) — el eco de la ruta es unánime en multimedia.** `ffmpeg-mcp-lite`
  (`File not found: <ruta>`), `image-worker-mcp` (`ENOENT … open '<ruta>'`, **dos veces**) y
  `video-audio-mcp` (banner de ffmpeg de 1,5 KB) **filtran la ruta y son oráculos de existencia**. El
  caso de `video-audio-mcp` añade un matiz nuevo a R4: **reenviar el `stderr` crudo del motor no solo es
  caro (872 tokens por fallo), es un oráculo** — el "no such file" está ahí, solo que enterrado.

- **R11 (tipo por contenido, no por extensión) — el ADS lo elude por el otro lado.** Medido: el flujo
  alternativo `entrada.png:oculto` **llega al motor en los tres** y en `image-worker-mcp` sus bytes
  entran al buffer del proceso. R12 (`bench/mcp-refs-confinamiento.md`) ya pedía rechazar el `:` en el
  componente final; esto lo **confirma como imprescindible también para los motores externos**, no solo
  para el lector de ficheros.

---

## 7. Reproducción

```sh
PYFF=D:/Work/research/FileX/.venv-mm-ffmpeg/Scripts/python.exe   # mcp<2 + (nada más)
PYVA=D:/Work/research/FileX/.venv-mm-vamcp/Scripts/python.exe    # mcp<2 + ffmpeg-python
CLI=D:/Work/research/FileX/.venv-mcp-md/Scripts/python.exe       # cliente (no modificar)
cd bench/salidas-confinamiento-mm
$PYFF gen_specs_mm.py
# ffmpeg-mcp-lite e image-worker: seguros
$CLI ../scripts/mcp_probe_bin.py specs/A_ffmpeg.json        salidas/A_ffmpeg.json
$CLI ../scripts/mcp_probe_bin.py specs/C_image_worker.json  salidas/C_image_worker.json
# video-audio-mcp: SOLO con destinos de salida FRESCOS (borra fuera/va_* antes) y timeout duro
rm -f sandbox/fuera/va_*
timeout 180 $CLI ../scripts/mcp_probe_bin.py specs/B_video_audio.json salidas/B_video_audio.json
taskkill //F //IM ffmpeg.exe   # matar cualquier huérfano
# validación Python (subagente):  py-validacion/bench_validacion.py
# TOCTOU Linux (subagente, dentro de WSL):  toctou-linux/toctou_probe_linux.py
```

**Venvs creados para este trabajo** (uno por servidor, como exige el encargo): `.venv-mm-ffmpeg`,
`.venv-mm-vamcp`. No se tocó ninguno de los cuatro venvs prohibidos. No se usó la GPU.

