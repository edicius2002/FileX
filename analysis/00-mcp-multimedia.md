# MCP para salidas binarias: cuatro precedentes leídos, y qué le pasa a las reglas de FileX

Las reglas MCP de FileX (`analysis/00-mcp-patrones.md`, medidas en `bench/mcp-ergonomia.md`) salen **todas de
servidores documentales, donde la salida es texto**: markitdown-mcp devuelve 85 259 tokens por un PDF de 60
páginas, docling-mcp devuelve un asa de 36. Factor 2 368×.

Este documento comprueba esas reglas contra el **caso binario**, donde el problema cambia de naturaleza: un MP4
convertido **no cabe en el contexto ni queriendo**. `tests/sample.mp4` de video-audio-mcp pesa 10 498 677 bytes;
en base64 son ~14 M de caracteres, del orden de **millones de tokens** — dos órdenes de magnitud por encima de
cualquier ventana. El asa deja de ser una optimización y pasa a ser la única opción física.

**Método.** Lectura de código, sin ejecutar nada. Cada afirmación lleva `fichero:línea`. Donde estimo, lo digo.
Los recuentos de tokens de catálogo de este documento son **estimaciones por caracteres** (nombre + firma +
docstring ÷ 4), no medidas con `tiktoken`, y son cotas inferiores: el catálogo MCP real añade el envoltorio JSON
Schema. Las cifras de markitdown-mcp/docling-mcp que se citan como contraste sí están medidas en
`bench/mcp-ergonomia.md`.

Repos leídos (todos MIT, clonados en `repos/mcp-refs/`):

| Repo | Último commit del clon | Lenguaje | Tamaño del núcleo |
|---|---|---|---|
| `video-audio-mcp` | `905549b` 2025-05-24 | Python | `server.py` 1 649 líneas |
| `ffmpeg-mcp-lite` | `622af39` 2026-05-08 | Python | 9 ficheros, 470 líneas |
| `image-worker-mcp` | `029db7d` 2025-07-24 | TypeScript | `src/` 10 ficheros |
| `markitdown_mcp_server` | `5cf1f29` 2025-12-21 | Python | 162 líneas |
| `kordoc` | `657d300` 2026-08-17 | TypeScript | solo `src/utils.ts` + call sites |

---

## A) `video-audio-mcp` — 27 herramientas planas, cero anotaciones, y el error viaja como éxito

Un solo fichero, `server.py`, 1 649 líneas. `main.py` es un `print("Hello from video-edit-mcp!")` de 6 líneas
(`main.py:1-6`) y no tiene nada que ver con el servidor: el entrypoint real es `server.py:1649-1650`
(`if __name__ == "__main__": mcp.run()`).

### A.1 Las 27 herramientas

Confirmado: `grep -c "@mcp.tool" server.py` → **27**. Ninguna otra decoración.

| # | Herramienta | Línea | Qué hace |
|---:|---|---:|---|
| 1 | `health_check` | `server.py:14` | Devuelve `"Server is healthy!"`. Literalmente una constante. |
| 2 | `extract_audio_from_video` | `server.py:19` | Extrae la pista de audio a `output_audio_path` con `acodec` dado (por defecto `mp3`). |
| 3 | `trim_video` | `server.py:43` | Recorta entre `start_time` y `end_time`; intenta `c='copy'` y cae a recodificación. |
| 4 | `convert_audio_properties` | `server.py:77` | Formato + bitrate + sample rate + canales en una sola llamada. |
| 5 | `convert_video_properties` | `server.py:114` | Formato + resolución + códecs + bitrates + fps + 4 parámetros de audio (11 argumentos). |
| 6 | `change_aspect_ratio` | `server.py:158` | Cambia la relación de aspecto con `pad` o `crop`; detecta si ya coincide. |
| 7 | `convert_audio_format` | `server.py:247` | Solo el contenedor/formato de audio. |
| 8 | `set_audio_bitrate` | `server.py:268` | Solo bitrate de un fichero de audio. |
| 9 | `set_audio_sample_rate` | `server.py:289` | Solo sample rate. |
| 10 | `set_audio_channels` | `server.py:310` | Solo número de canales. |
| 11 | `convert_video_format` | `server.py:351` | Contenedor de vídeo; primero `vcodec/acodec='copy'`, fallback recodificar. |
| 12 | `set_video_resolution` | `server.py:365` | `scale=WxH` o `scale=-2:H`, copiando audio. |
| 13 | `set_video_codec` | `server.py:386` | Solo el códec de vídeo. |
| 14 | `set_video_bitrate` | `server.py:400` | Solo el bitrate de vídeo. |
| 15 | `set_video_frame_rate` | `server.py:414` | Solo los fps. |
| 16 | `set_video_audio_track_codec` | `server.py:428` | Códec de la pista de audio dentro de un vídeo. |
| 17 | `set_video_audio_track_bitrate` | `server.py:442` | Bitrate de esa pista. |
| 18 | `set_video_audio_track_sample_rate` | `server.py:456` | Sample rate de esa pista. |
| 19 | `set_video_audio_track_channels` | `server.py:470` | Canales de esa pista. |
| 20 | `add_subtitles` | `server.py:486` | Quema un SRT con estilo ASS opcional (`font_style: dict`). |
| 21 | `add_text_overlay` | `server.py:569` | Rótulos de texto con temporización (`text_elements: list[dict]`). |
| 22 | `add_image_overlay` | `server.py:666` | Marca de agua / logo con posición y opacidad. |
| 23 | `concatenate_videos` | `server.py:776` | Concatena N vídeos; con exactamente 2, transición `xfade` de 37 tipos. |
| 24 | `change_video_speed` | `server.py:1036` | `setpts` + cadena de `atempo` para factores fuera de 0,5–2,0. |
| 25 | `remove_silence` | `server.py:1103` | `silencedetect` + re-corte de los segmentos con sonido. |
| 26 | `add_b_roll` | `server.py:1349` | Superpone clips de B-roll sobre el vídeo principal. |
| 27 | `add_basic_transitions` | `server.py:1574` | `fade_in` / `fade_out` de duración dada. |

Herramientas 11–19 comparten un único helper, `_run_ffmpeg_with_fallback` (`server.py:332-348`), que no está
decorado: **nueve herramientas MCP distintas son nueve líneas de diccionario sobre la misma función**. Ejemplo
completo, `server.py:386-397`:

```python
primary_kwargs = {'vcodec': video_codec, 'acodec': 'copy'}
fallback_kwargs = {'vcodec': video_codec}
return _run_ffmpeg_with_fallback(input_video_path, output_video_path, primary_kwargs, fallback_kwargs)
```

Eso es exactamente la regla 5 de `bench/mcp-ergonomia.md` («cuatro o cinco herramientas, con nombres cortos y
dominios distintos») violada al máximo: cinco nombres empiezan por `set_video_audio_track_…` y compiten entre sí
en el espacio de decisión del modelo, cuando podrían ser un parámetro de `convert_video_properties`, que ya
existe (`server.py:114`) y ya los cubre todos.

**Coste de catálogo estimado:** nombres + firmas + docstrings suman **14 443 caracteres ≈ 3 610 tokens**, antes
del envoltorio JSON Schema. Con el envoltorio, es razonable esperar cifras del orden de los **5 280 tokens
medidos** de docling-mcp con sus 19 herramientas, o por encima. La herramienta más cara con diferencia es
`concatenate_videos` (**1 935 caracteres ≈ 480 tokens de docstring**, `server.py:778-812`), porque enumera los 37
efectos `xfade` uno por uno en el texto de la descripción — y **los vuelve a enumerar** en el `set` de validación
(`server.py:825-836`) y una tercera vez en el mensaje de error (`server.py:838`).

### A.2 LA PREGUNTA CENTRAL: qué devuelve al modelo tras convertir un vídeo

**Devuelve una frase en prosa que contiene la ruta de salida. Nunca el contenido, nunca base64, nunca metadatos
estructurados.** Todas las herramientas están anotadas `-> str` y todos los caminos de retorno son cadenas.

Casos verbatim:

```python
# server.py:33
return f"Audio extracted successfully to {output_audio_path}"

# server.py:59 y 67 — la frase cambia según el camino interno tomado
return f"Video trimmed successfully (codec copy) to {output_video_path}"
return f"Video trimmed successfully (re-encoded) to {output_video_path}"

# server.py:336 y 340 — el helper compartido ni siquiera nombra el fichero de entrada
return f"Operation successful (primary method) and saved to {output_path}"
return f"Operation successful (fallback method) and saved to {output_path}"

# server.py:1213
return f"Silent segments removed. Output saved to {output_media_path}"
```

**Esto es el patrón de asa, y llegaron a él por necesidad, no por diseño.** Es la confirmación más fuerte que
hay del caso binario: el MCP de conversión multimedia más ambicioso del ecosistema (27 herramientas) **nunca se
planteó devolver el vídeo**, porque no es posible. La regla 1 de FileX («la respuesta por defecto de `convert`
es un asa») no necesita defenderse aquí: es lo único que se puede hacer.

Pero el asa está **mal construida**, y en tres sentidos concretos:

1. **Es prosa, no un objeto.** El agente tiene que extraer la ruta de una frase en inglés que además **cambia de
   redacción según el camino interno** («codec copy» / «re-encoded» / «primary method» / «fallback method»).
   Los propios tests del repo demuestran la fragilidad: `tests/test_video_functions.py:143` asserta
   `"Video trimmed successfully" in result` — matching de substring sobre prosa. Y en ffmpeg-mcp-lite el mismo
   antipatrón obliga a `Path(result.split(": ")[1])` (`tests/test_convert.py:22`): *parsear la ruta partiendo el
   mensaje por dos puntos*. Si un test tiene que hacer eso, un agente también.
2. **No hay ni un metadato.** Ni bytes, ni duración, ni resolución del resultado, ni códec efectivo, ni tiempo
   empleado, ni si se copió o se recodificó de forma legible por máquina. El agente que quiera saber si el
   resultado es válido tiene que llamar a otra herramienta... que no existe: **no hay `probe`/`info` en las 27**.
   Contraste directo con `ffmpeg-mcp-lite`, que sí tiene `ffmpeg_get_info` (§B).
3. **No hay progreso.** `Context` de FastMCP se importa en `server.py:2` y **no se usa en ninguna línea del
   fichero** (grep: única aparición). Tampoco hay timeout: cada `.run(capture_stdout=True, capture_stderr=True)`
   es bloqueante y sin límite. Una recodificación H.265 de una hora bloquea la llamada MCP entera, sin señal
   alguna, hasta que el cliente se rinda.

### A.3 Agrupación: plana, y la agrupación que existe es documentación, no protocolo

Las 27 están registradas en el espacio de nombres global de un `FastMCP("VideoAudioServer")` (`server.py:10`).
En el fuente hay comentarios de sección — `# --- Granular Audio Property Tools ---` (`server.py:245`),
`# --- Granular Video Property Tools ---` (`:330`), `# --- Phase 3: Overlays and Basic Enhancements ---` (`:483`),
`# --- Phase 4 ---` (`:773`), `# --- Phase 6: B-Roll and Basic Transitions ---` (`:1221`) — y el README las
agrupa en cuatro categorías para humanos (`README.md:25`, `:36`, `:47`, `:54`).

**Nada de eso llega al protocolo.** No hay grupos cargables como el argumento posicional `conversion` de
docling-mcp (que en `bench/mcp-ergonomia.md` §3.2 recortó el catálogo un 83 %). El cliente recibe las 27 o
ninguna. Los prefijos de nombre (`set_video_*`, `set_audio_*`, `add_*`) son el único agrupamiento que el modelo
ve, y agrupan por *verbo*, no por dominio.

### A.4 Anotaciones: **cero**

`grep -n "annotations\|readOnlyHint\|destructiveHint\|openWorldHint\|ToolAnnotations\|title=" server.py` no
devuelve **ninguna línea**. Los 27 decoradores son `@mcp.tool()` desnudos.

Consecuencia concreta: `health_check` (`server.py:14`), que es puramente de solo lectura y no toca el disco, es
indistinguible para el cliente de `add_b_roll` (`server.py:1349`), que crea directorios temporales, ejecuta
ffmpeg y **sobrescribe la ruta de salida que el modelo eligió**. Un cliente que auto-apruebe herramientas marcadas
como solo lectura no puede clasificar ninguna de las 27. Es la regla 6 sin cumplir en absoluto.

### A.5 Rutas: el modelo elige, sin confinamiento y sin normalización

**Entrada.** Se valida existencia con `os.path.exists()` en 8 sitios (`server.py:514`, `:516`, `:592`, `:689`,
`:691`, `:842`, `:1050`, `:1117`, `:1353`, `:1383`, `:1586`) y **en las otras 19 herramientas ni eso**: se pasa
la cadena directa a `ffmpeg.input()` y se atrapa `FileNotFoundError` después. No hay `realpath`, no hay raíz
permitida, no hay allowlist de extensiones, no hay noción de proyecto. Cualquier ruta absoluta del disco vale.

**Salida.** Peor: **el modelo elige libremente dónde escribir**. `output_video_path` / `output_audio_path` /
`output_media_path` son parámetros obligatorios en 25 de las 27 herramientas y **nunca se validan**: no se
comprueba que el directorio exista, no se comprueba que no se esté sobrescribiendo algo, no se resuelve la ruta.
Es escritura arbitraria en el sistema de ficheros gobernada por un parámetro que escribe el agente.

**Bug adicional, inferido del código (no ejecutado):** las llamadas vía `ffmpeg-python` `.run()` **no pasan
`overwrite_output=True`**, y el flag `-y` solo aparece en los siete `subprocess` crudos de
`concatenate_videos`/`add_b_roll` (`server.py:898`, `:915`, `:956`, `:1001`, `:1022`, `:1434`, `:1547`). Con
`stdin` no interactivo, ffmpeg responde «Not overwriting - exiting» ante un fichero existente. Es decir: **repetir
la misma conversión a la misma ruta debería fallar**, y el fallo llegará al modelo con la forma descrita en A.6.

**Temporales.** `tempfile.mkdtemp()` en `server.py:859`, `:977`, `:1367`, con `shutil.rmtree` en `:970`, `:1033`,
`:1561`. La limpieza está en `finally` en los tres casos, correcto.

### A.6 Errores: **sí, devuelve el `stderr` crudo de ffmpeg — y con `isError: false`**

Este es el hallazgo más grave del repo, y es peor que cualquier cosa medida en `bench/mcp-ergonomia.md` §4.

**Primero: el stderr crudo se reenvía.** El patrón se repite en las 27 herramientas:

```python
# server.py:35-36
except ffmpeg.Error as e:
    error_message = e.stderr.decode('utf8') if e.stderr else str(e)
    return f"Error extracting audio: {error_message}"
```

`e.stderr` de ffmpeg es el volcado completo: banner de versión, lista de `configuration:` con ~50 flags de
compilación, versiones de todas las libav*, y luego el error real. Son típicamente 1,5–3 KB, del orden de
500–1 000 tokens por fallo. Y `_run_ffmpeg_with_fallback` (`server.py:344`) devuelve **los dos volcados
concatenados en una sola cadena**:

```python
return f"Error. Primary method failed: {err_primary_msg}. Fallback method also failed: {err_fallback_msg}"
```

Nueve de las 27 herramientas pasan por ahí. Un fallo de `set_video_codec` inyecta **dos banners completos de
ffmpeg** en el contexto del agente. El mismo patrón de doble volcado está en `trim_video` (`server.py:70`),
`change_aspect_ratio` (`:233`), `add_subtitles` (`:558`), `add_text_overlay` (`:655`), `add_image_overlay`
(`:763`) y `add_basic_transitions` (`:1635`).

**Segundo, y peor: ningún error es un error.** Todas las herramientas atrapan `Exception` y **devuelven una
cadena**. Ninguna excepción escapa nunca. En FastMCP, `isError` se marca cuando la excepción propaga; aquí
jamás propaga. **El resultado MCP de una conversión fallida es `isError: false` y una cadena que empieza por
`"Error: "`.** Es la regla 9 de `bench/mcp-ergonomia.md` («un fallo es un fallo: prohibido el éxito vacío»)
violada de forma sistemática y en las 27 herramientas — no un caso patológico como el PDF escaneado de
markitdown, sino el comportamiento por defecto para todo fallo del servidor.

Para un agente esto significa que la única forma de distinguir éxito de fracaso es **leer prosa en inglés y
buscar la palabra «Error»**. Es exactamente lo que hacen sus propios tests
(`tests/test_video_functions.py:134`, `:143`, `:156`…). Y hay una trampa: el mensaje de éxito de
`remove_silence` cuando *no* encuentra silencios es *`"No significant silences detected (or file is entirely
silent/loud). Original media copied to …"`* (`server.py:1150`) — un éxito que en realidad es «no hice nada»,
imposible de distinguir programáticamente de un éxito real.

**Lo único bueno.** Un mensaje sí tiene la forma correcta, `server.py:838`:

```python
return f"Error: Invalid transition_effect '{transition_effect}'. Valid options: {', '.join(sorted(valid_transitions))}"
```

Nombra la causa y **enumera las alternativas válidas**, que es el patrón que `bench/mcp-ergonomia.md` §4.1
señaló como modélico. Coste: los 37 nombres son ~150 tokens, ya presentes en la docstring. Es la idea correcta
con el vocabulario equivocado (debería ser un `Literal[...]` en la firma, no una validación en tiempo de
ejecución).

### A.7 Sí tiene tests, y el enunciado de esta tarea decía que no

`tests/test_video_functions.py`, **763 líneas, 29 funciones `test_*`**. Importa las funciones directamente del
módulo (`tests/test_video_functions.py:12-41`), no a través del protocolo MCP: **prueba el núcleo, no el
contrato MCP**. Genera sus propios ficheros con `ffmpeg -f lavfi` en `setup_broll_test_environment()`
(`:69-86`).

La mayoría de asserts es la pareja «substring en la prosa + `os.path.exists()`»
(`:134-135`, `:143-144`, `:156-157`…), que solo comprueba que se creó *un* fichero. **Pero los tests de las
herramientas complejas sí verifican el resultado**: `test_trim_video_with_duration_check` (`:471-495`) usa
`ffmpeg.probe` y asserta `abs(duration1 - 5.0) < 0.1`; `test_add_b_roll` (`:530`, `:553`, `:582`) y
`test_add_basic_transitions` (`:628`, `:639`) comprueban que la duración del resultado coincide con la esperada;
`test_concatenate_videos` (`:680-700`) valida `dur1 + dur2 - transition_duration`. **Esa es la forma correcta de
verificar una conversión binaria** y es más profunda que lo que hace ffmpeg-mcp-lite (§B.2).

Lastre: el fichero referencia `SAMPLE_VIDEO_2 = "sample2.mp4"` (`:45`) que **no existe en el repo** (`tests/`
solo contiene `sample.mp4`, `sample.png`, `sample_files/`), y `teardown_module` (`:114-118`) tiene el
`shutil.rmtree` comentado: la suite deja basura.

---

## B) `ffmpeg-mcp-lite` — la estructura correcta, el contrato equivocado

470 líneas de `src/`, 8 herramientas, 9 ficheros. Es lo que `video-audio-mcp` debería haber sido.

### B.1 Cómo trocea el dominio, y por qué es lo que FileX necesita

Un fichero por herramienta bajo `tools/`, y un `server.py` de 29 líneas que solo importa y registra
(`src/ffmpeg_mcp_lite/server.py:5-24`):

```python
from .tools.info import ffmpeg_get_info
from .tools.convert import ffmpeg_convert
...
mcp = FastMCP("ffmpeg-mcp")
mcp.tool()(ffmpeg_get_info)
mcp.tool()(ffmpeg_convert)
...
```

Detalle que importa: **las funciones no llevan decorador**. Se definen como `async def` normales en su módulo y
se registran por aplicación explícita en `server.py:17-24`. Eso es la separación núcleo/superficie que
`analysis/00-mcp-patrones.md` atribuye a kordoc, conseguida con dos líneas de disciplina en vez de con una
arquitectura: los módulos de `tools/` **no importan `mcp`**, solo `..config`. Se pueden usar desde una CLI, desde
un test o desde otra superficie sin tocar nada. Y de hecho los tests hacen exactamente eso
(`tests/test_convert.py:7`, `tests/test_info.py:8`).

Las 8 herramientas: `ffmpeg_get_info` (`tools/info.py:11`), `ffmpeg_convert` (`tools/convert.py:10`),
`ffmpeg_compress` (`tools/compress.py:10`), `ffmpeg_trim` (`tools/trim.py:10`), `ffmpeg_extract_audio`
(`tools/audio.py:10`), `ffmpeg_merge` (`tools/merge.py:11`), `ffmpeg_extract_frames` (`tools/frames.py:10`),
`ffmpeg_add_subtitles` (`tools/subtitles.py:40`).

**Contraste directo con las 27 planas de A.** Catálogo estimado: **3 245 caracteres ≈ 811 tokens** frente a
≈ 3 610 de video-audio-mcp. Es **4,5× más barato** cubriendo el 80 % del mismo dominio, porque agrupa por
*intención del usuario* (convertir, comprimir, recortar, extraer, unir) en vez de por *parámetro de ffmpeg*
(bitrate, sample rate, canales, fps). Todos los `set_*_bitrate`/`set_*_sample_rate`/`set_*_channels` de A
desaparecen dentro de argumentos opcionales de `ffmpeg_convert` (`tools/convert.py:10-16`) y `ffmpeg_compress`.

Además usa `Literal` para acotar el espacio de valores en la propia firma —
`quality: Literal["low","medium","high"]` y los 9 presets de x264 (`tools/compress.py:12-14`),
`audio_format: Literal["mp3","aac","wav","flac","ogg","opus"]` (`tools/audio.py:12`),
`format: Literal["jpg","png","bmp","webp"]` (`tools/frames.py:14`). Eso se convierte en un `enum` de JSON Schema:
el modelo no puede equivocarse y **no hace falta un mensaje de error que enumere alternativas**, porque el
catálogo ya las enumeró. Es la solución estructural al problema que A resuelve con `server.py:838`.

**Cuál se parece más a lo que necesita FileX: éste, sin discusión.** La forma `tools/<dominio>.py` +
`server.py` de registro + `config.py` es exactamente el troceado que el objetivo de FileX (`convert`, `inspect`,
`list_targets`, `batch`, ≈ 1 000 tokens de catálogo) requiere, y 811 tokens estimados para 8 herramientas
demuestran que el presupuesto es realista.

El propio repo documenta de dónde salió la estructura: `RESEARCH.md:150-334` es un estudio comparativo de cinco
MCP de ffmpeg antes de escribir una línea, con convención de nombres prefijados `ffmpeg_*` justificada en
`RESEARCH.md` §5.2 y prioridad P0/P1 por herramienta en §5.3. `TODO.md:36-44` tiene la tabla
herramienta → entrada → salida. Es el único de los cuatro repos que decidió su superficie antes de escribirla.

### B.2 `tests/`: qué verifican exactamente

Un fichero por herramienta, 8 ficheros, **~31 tests** (el `SKILL.md:178` dice 31, `TODO.md` dice 26).

**Lo que está muy bien hecho — el `conftest.py`, y es lo copiable.** `tests/conftest.py:17-40` genera el material
de prueba **con ffmpeg, en un `TemporaryDirectory`, en tiempo de test**:

```python
cmd = ["ffmpeg", "-f","lavfi", "-i","testsrc=duration=2:size=320x240:rate=30",
       "-f","lavfi", "-i","sine=frequency=440:duration=2",
       "-c:v","libx264", "-c:a","aac", "-y", str(output_path)]
result = subprocess.run(cmd, capture_output=True)
if result.returncode != 0:
    pytest.skip("FFmpeg not available or failed to create test video")
```

Tres decisiones correctas de golpe: **cero binarios versionados** en el repo (video-audio-mcp versiona un
`sample.mp4` de 10 MB), **propiedades conocidas** (320×240, 2 s, 440 Hz) contra las que se puede assertar de
verdad, y **`pytest.skip` en vez de fallo** si no hay ffmpeg, con lo que la suite es honesta en CI sin
dependencias.

**Qué verifican de verdad — respuesta matizada:**

| Tipo de assert | Dónde | Profundidad |
|---|---|---|
| Substring de la prosa de éxito | `test_convert.py:20`, `test_compress.py:19`, `test_trim.py`, `test_audio.py`, `test_merge.py:20`, `test_subtitles.py:35` | Superficial: solo confirma que no hubo excepción |
| Convención del nombre de salida | `test_convert.py:21` (`"_converted.mkv" in result`), `test_compress.py:20`, `test_merge.py:21`, `test_subtitles.py:36` | Fija el contrato de nombrado |
| **Existencia real del fichero** | `test_convert.py:22-23`, `test_merge.py:35`, `test_subtitles.py:68`, `test_frames.py:31`, `:41`, `:51`, `:61` | Sí comprueba la salida |
| **Contenido/propiedades del resultado** | **solo `test_info.py:15-29`**: parsea el JSON y asserta `width == 320`, `height == 240`, `duration is not None`, `codec_type` | Es el único que mira *dentro* |
| Errores esperados (`pytest.raises`) | `test_convert.py:41`, `test_info.py:46`, `:54`, `test_frames.py:67`, `:74`, `test_merge.py:41`, `:48`, `test_compress.py:39`, `test_subtitles.py:74`, `:81` | **10 de ~31 tests**, casi un tercio |
| Formato de salida por extensión | `test_frames.py:45-61` (jpg/png/webp, vía `glob`) | Comprueba que el códec pedido se aplicó, indirectamente |

**Respuesta honesta a la pregunta:** para las conversiones **no comprueban la salida, solo que existe y que no
hubo excepción**. Ninguna llama a `ffprobe` sobre el resultado para verificar que el MKV es un MKV, que la escala
`160:120` se aplicó (`test_convert.py:33-35` solo mira la prosa), o que la compresión redujo algo. En eso
`video-audio-mcp` (§A.7) es **más profundo**: sus tests de b-roll y transiciones sí verifican duraciones con
`ffprobe`.

**Pero hay un test que vale por varios**, y es el detalle que revela una suite escrita por alguien que se comió
el bug — `tests/test_frames.py:10-20`:

```python
@pytest.fixture
def patched_output_dir(temp_dir, monkeypatch):
    """Patches the live config instance held by frames.py rather than reassigning
    config.config — the module imported the instance at load time, so reassignment
    would not affect it."""
    from ffmpeg_mcp_lite.tools import frames as frames_mod
    monkeypatch.setattr(frames_mod.config, "output_dir", temp_dir)
```

El resto de tests hace `monkeypatch.setenv(...)` + `config.config = config.Config()`
(`test_convert.py:13-16`), que **no funciona** para `frames.py` porque ese módulo hizo
`from ..config import config` y capturó la instancia. Es el tipo de trampa de configuración global que FileX
va a tener idéntica el día que tenga un singleton de motor caliente (regla 14).

**Como plantilla para FileX, el veredicto:** copiar `conftest.py` tal cual (generación de fixtures sintéticos con
el propio motor + `skip` si falta), copiar la disciplina de un fichero de test por herramienta, y **añadir lo que
falta**: un assert de propiedades del artefacto de salida vía `ffprobe`/`identify` en toda conversión, no solo en
`info`. Sin eso, la suite no distingue «convirtió» de «escribió un fichero de 0 bytes».

### B.3 `config.py`: 23 líneas, correcto en su alcance y con un agujero grande

```python
# src/ffmpeg_mcp_lite/config.py:10-21
self.ffmpeg_path  = os.environ.get("FFMPEG_PATH",  "ffmpeg")
self.ffprobe_path = os.environ.get("FFPROBE_PATH", "ffprobe")
self.output_dir   = Path(os.environ.get("FFMPEG_OUTPUT_DIR", "~/Downloads")).expanduser()

def ensure_output_dir(self) -> Path:
    self.output_dir.mkdir(parents=True, exist_ok=True)
    return self.output_dir

config = Config()      # config.py:23 — singleton de módulo
```

**Rutas de binarios:** parametrizadas y usadas siempre a través del config (`config.ffmpeg_path` en
`convert.py:39`, `compress.py:45`, `trim.py:42`, `audio.py:45`, `merge.py:54`, `frames.py:46`,
`subtitles.py:86`; `config.ffprobe_path` en `info.py:28` y `frames.py:57`). Nunca se invoca `"ffmpeg"` literal
desde una herramienta. Documentado en `README.md:409-411`.

**Directorio de salida: la mejor idea del repo.** Existe un directorio de salida configurado, y **el modelo no
puede elegir dónde escribir** en 5 de las 8 herramientas: el nombre se deriva del de entrada.

```python
# convert.py:35-36
output_dir  = config.ensure_output_dir()
output_path = output_dir / f"{path.stem}_converted.{output_format}"
```

Igual en `compress.py:41-42` (`_compressed.mp4`), `trim.py:38-39` (`_trimmed{suffix}`), `audio.py:31-32`,
`frames.py:39-40` (`{stem}_frames/`). Esto es **la mitad de la regla 12** implementada de forma barata: la
escritura está confinada a una raíz declarada por configuración, y el nombrado es determinista y predecible.

**Pero el confinamiento tiene dos fugas y es unidireccional:**

- **`ffmpeg_merge` y `ffmpeg_add_subtitles` aceptan `output_path` arbitrario** del modelo
  (`merge.py:38-39`, `subtitles.py:72-73`): `Path(output_path).expanduser().resolve()` y a escribir. Dos de ocho
  herramientas escapan del confinamiento por completo.
- **La entrada no está confinada en absoluto.** El patrón `Path(file_path).expanduser().resolve()` +
  `exists()` + `is_file()` se repite en las 8 (`convert.py:29-33`, `info.py:21-25`, `compress.py:27-31`,
  `trim.py:32-36`, `audio.py:25-29`, `merge.py:30-35`, `frames.py:32-36`, `subtitles.py:59-69`). `resolve()`
  **normaliza** (es el equivalente a `realpath`) pero **no compara contra ninguna raíz**. Cualquier fichero del
  disco vale, exactamente como los dos servidores documentales medidos en `bench/mcp-ergonomia.md` §6.1.

**Límites y timeouts: no existen.** `grep -rn "timeout\|wait_for\|max_\|limit\|MAX" src/` → **cero resultados**.
No hay `asyncio.wait_for` alrededor de ninguno de los 9 subprocesos, no hay tamaño máximo de entrada, no hay
duración máxima. `ffmpeg_compress` con `preset="veryslow"` sobre un fichero de 4 GB corre indefinidamente.
El `asyncio.create_subprocess_exec` (`convert.py:56-61` y equivalentes) al menos **no bloquea el bucle de
eventos** — el servidor sigue atendiendo otras peticiones —, lo cual es correcto y es más de lo que hace
`video-audio-mcp`, pero la llamada individual no tiene salida.

**Anotaciones: cero.** `mcp.tool()(fn)` desnudo en `server.py:17-24`. `ffmpeg_get_info` es de solo lectura pura
(`info.py:27-34` solo llama a `ffprobe`) y **no está marcada `readOnlyHint`**, que es justo la anotación que más
valor daría en este catálogo.

### B.4 Qué devuelve al modelo

Lo mismo que A —**prosa con la ruta**— pero mejor en dos casos y peor en uno.

```python
# convert.py:66
return f"Converted successfully: {output_path}"
# trim.py:67
return f"Trimmed successfully: {output_path}"
# audio.py:67
return f"Audio extracted successfully: {output_path}"
# subtitles.py:107
return f"Subtitles added successfully: {out_path}"
# merge.py:73
return f"Merged {len(paths)} files successfully: {out_path}"
```

**Los dos aciertos:**

1. **`ffmpeg_compress` devuelve métricas** (`compress.py:71-81`), y son las métricas correctas:

```python
original_size   = path.stat().st_size
compressed_size = output_path.stat().st_size
reduction = (1 - compressed_size / original_size) * 100
return (f"Compressed successfully: {output_path}\n"
        f"Original: {original_size/1024/1024:.2f} MB\n"
        f"Compressed: {compressed_size/1024/1024:.2f} MB\n"
        f"Reduction: {reduction:.1f}%")
```

   Es la única herramienta de los cuatro repos que le dice al modelo **si la operación consiguió su objetivo**.
   Coste: ~40 tokens. Sigue siendo prosa multilínea que hay que parsear, pero el *contenido* es exactamente el
   asa enriquecida que la regla 1 de FileX pide (`{ruta_salida, bytes, ...}`).

2. **`ffmpeg_get_info` devuelve JSON**, y **filtrado** (`info.py:46-88`): coge la salida de `ffprobe -show_format
   -show_streams` y **se queda con 4 campos de formato y 3–7 por stream** en vez de reenviarla entera. La salida
   cruda de ffprobe de un MP4 típico son varios miles de tokens (decenas de campos por stream, `disposition`,
   `tags`, `side_data_list`); este recorte la deja en unos cientos. **Es la regla 3 aplicada al caso binario**:
   lectura acotada por defecto en vez de volcado. El comentario del autor lo dice
   (`info.py:48`: `# Extract key information for a cleaner response`).

**El error:** `ffmpeg_extract_frames` devuelve `f"Extracted {frame_count} frames to: {output_dir}"`
(`frames.py:92`). Un directorio con N ficheros y **ninguna lista, ningún patrón de nombre, ninguna ruta de
ejemplo**. El modelo sabe que hay 60 frames y dónde está la carpeta, pero no sabe que se llaman
`frame_0001.jpg` — eso está en `frames.py:42` y nunca sale del servidor. Para usarlos tiene que adivinar o
listar el directorio con otra herramienta.

### B.5 Errores: `raise` con el `stderr` crudo dentro

Aquí ffmpeg-mcp-lite hace **una cosa bien y una mal**, y son la misma línea.

```python
# convert.py:63-64
if proc.returncode != 0:
    raise RuntimeError(f"ffmpeg convert failed: {stderr.decode()}")
```

Idéntico en `compress.py:68-69`, `trim.py:64-65`, `audio.py:64-65`, `merge.py:70-71`, `frames.py:86-87` y `:69-70`,
`subtitles.py:104-105`, `info.py:43-44`.

**Lo bien:** `raise`, no `return`. La excepción propaga hasta FastMCP, que produce **`isError: true`**. Un fallo
es un fallo. Frente a las 27 herramientas de video-audio-mcp que devuelven `isError: false` con la palabra
«Error» dentro de una frase, esto es correcto y es lo que FileX debe hacer (regla 9).

**Lo mal:** dentro va `stderr.decode()` **entero**. Mismo problema que A.6 — banner de ffmpeg, `configuration:`
con 50 flags, versiones de libav — solo que ahora bien etiquetado como error. Y la validación previa sí tiene
mensajes limpios y cortos:

```python
raise FileNotFoundError(f"File not found: {file_path}")            # convert.py:31
raise ValueError("Cannot specify both end_time and duration. Use one or the other.")  # trim.py:28
raise ValueError("Must specify either interval or count.")          # frames.py:30
raise ValueError("Need at least 2 files to merge")                  # merge.py:25
```

Todos por debajo de 20 tokens, nombran la causa, y los de exclusión mutua **dicen qué hacer**. Es la forma
correcta. El problema es que el error *interesante* —por qué ffmpeg no pudo— es justo el que llega en crudo.

Nota de contraste: `.claude/skills/mcp-builder/SKILL.md:175` marca como cumplida la casilla
«**Actionable error messages**». El código dice otra cosa. Es un recordatorio útil de que una checklist de
calidad MCP no sirve si nadie mira qué texto ve el modelo.

---

## C) `image-worker-mcp` — el caso donde el asa NO era obligatoria, y aun así lo hacen mal

### C.1 `services/` frente a `tools/`: la separación existe pero **no es la que parecía**

**`services/` no contiene lógica de conversión. Son backends de subida a nube.** `BaseUploadService` es una
abstracta con un solo método `upload(buffer, filename, args)` (`src/services/types.ts:49-57`), implementada por
`S3UploadService` (`src/services/s3.ts:20-142`), `CloudflareUploadService` (`src/services/cloudflare.ts:18-138`)
y `GCloudUploadService` (`src/services/gcloud.ts:15-110`), seleccionadas por un Factory con validación zod de
variables de entorno (`src/services/factory.ts:8-43` y `:46-71`).

La costura es **asimétrica**:

- **`upload_image` sí tiene inyección de dependencia real:** `new UploadTool(args, this.uploadService).exec()`
  (`src/server.ts:33`); el servicio se construye una vez en el constructor (`src/server.ts:18`) y la herramienta
  solo lo recibe (`src/tools/upload.ts:60-67`) e invoca (`:129`). Testeable con un doble.
- **`resize_image` no tiene costura ninguna.** Toda la conversión vive en `class ImageProcessor`
  (`src/tools/sharp.ts:60-315`), en el **mismo fichero** que el esquema zod (`:11-56`) y el adaptador
  (`:317-320`), y devuelve directamente un `CallToolResult` del SDK MCP (`:264`, importado en `:4`).

**Veredicto: no está bien hecha para lo que FileX quiere.** No existe una capa `core/` de imagen. `ImageProcessor`
mezcla I/O (`fs.readFileSync` en `sharp.ts:78`, `fs.writeFileSync` en `:254`, `fetch` vía `utils.ts:94-127`),
decodificación, transformación y **serialización de la respuesta MCP** (`:278-297`). Está bien organizada
*internamente* por métodos privados —`getInputBuffer` (`:68-94`), `validateAndInitializeSharp` (`:101-152`),
`applyResize` (`:154-180`), `applyTransformations` (`:182-218`), `formatOutput` (`:220-248`), `saveToFile`
(`:250-262`), orquestados en `exec()` (`:264-314`)— pero el núcleo **no es extraíble sin arrastrar el SDK MCP**.

La lección para FileX es al revés de lo esperado: **la separación limpia de este repo es la de la nube
(Strategy + Factory), no la de la conversión**. Y la separación que sí funciona para el caso de FileX es la de
`ffmpeg-mcp-lite` (§B.1), conseguida sin arquitectura: funciones puras en `tools/` que no importan `mcp`.

Herramientas: **solo 2**, registradas en `src/server.ts:27-35` con esquemas zod como *raw shape*
(`resizeImageSchema` en `tools/sharp.ts:11-56`, `uploadImageSchema` en `tools/upload.ts:14-56`).
**Anotaciones: cero** — usa la sobrecarga legacy `server.tool(name, description, schema, cb)` del SDK 1.11.4
(`package.json:43`), no `registerTool()`, que es la API que admite `annotations`. `resize_image` escribe en disco
arbitrario y `upload_image` hace red saliente: `destructiveHint` y `openWorldHint` deberían valer `true` y no
existen.

Bug de contrato detectado por lectura: `uploadImageSchema` **no expone `service`** pese a que `UploadImageArgs`
lo declara (`src/services/types.ts:39`) y el `Readme.md:82` documenta un ejemplo pasándolo. El modelo lo envía y
el esquema lo descarta en silencio.

### C.2 `libheif-js.d.ts` y HEIC

**Por qué hace falta:** `sharp` 0.34.1 (`package.json:48`) en sus builds prebuilt no trae libheif por la licencia
HEVC, así que HEIC hay que decodificarlo aparte. Se usa `libheif-js@^1.18.2` (`package.json:46`) importado desde
el subpath WASM: `import libheif from 'libheif-js/wasm-bundle'` (`src/tools/sharp.ts:5`). El bundle WASM lleva el
binario embebido y evita dependencias nativas — coherente con la promesa «No system dependencies»
(`Readme.md:185`).

**Qué es el `.d.ts`:** el paquete no publica tipados para ese subpath, así que `src/libheif-js.d.ts:1-11` es un
shim de módulo ambiente con **solo lo que el código usa** — `HeifDecoder.decode()` y `HeifImage` con
`get_width/get_height/display`. El propio fichero admite que es parcial (`libheif-js.d.ts:7`:
`// Add other exports from libheif-js if needed`) y `display` no declara tipo de retorno (`:5`).

**El camino HEIC en `tools/sharp.ts` y lo que hay que copiar:**

```ts
// sharp.ts:96-99 — detección por magic bytes, NO por extensión
private isHeif(buffer: Buffer): boolean {
  const signature = buffer.toString('ascii', 4, 12);
  return ['ftypheic','ftypheix','ftyphevc','ftyphevx','ftypmif1','ftypmsf1'].some(s => signature.includes(s));
}
```

Sniffing del box `ftyp` de ISO-BMFF en offset 4..12: robusto frente a extensiones mentirosas, que es exactamente
el problema de un servidor donde el nombre del fichero lo escribe un agente. **Esto es copiable tal cual.**

El puente a `sharp` es vía píxeles crudos (`sharp.ts:102-141`): `decoder.decode()` (`:105`), `display()` envuelto
en promesa sobre un `Uint8ClampedArray(w*h*4)` (`:113-121`), y luego
`sharp(pixelBuffer, { raw: { width, height, channels: 4 } })` (`:129-135`), con el `channels: 4` **hardcodeado y
el comentario admitiendo la suposición** (`:133`: `// Assuming RGBA, common for HEIF decoders`).

**Dos defectos que FileX debe evitar:** solo procesa `decodedImages[0]` (`sharp.ts:110`), ignorando bursts y Live
Photos — que es precisamente lo que un HEIC de iPhone suele contener. Y al fijar a mano `this.inputFormat =
'heic'` (`:127`), si el modelo no pasa `format` explícito el `outputFormat` cae a `'heic'` (`:221`), que no
matchea ningún `case` del switch (`:226-243`) y lanza `Unsupported output format: heic` (`:244-245`):
**convertir un HEIC sin especificar formato de salida siempre falla**. Los dos tests de integración con un
`.heic` real (`tests/tools/sharp.test.ts:280-390` y `:392-470`) lo esquivan porque ambos pasan `format`
explícito (`:336`, `:430`). Mismo bug latente con `gif` y `tiff`, que están en `SUPPORTED_INPUT_FORMATS`
(`constants.ts:1`) pero no en `SUPPORTED_OUTPUT_FORMATS` (`:2`).

### C.3 El caso especial: **una imagen SÍ podría devolverse al modelo. Este repo lo hace mal.**

Esta era la pregunta interesante del carril, porque los modelos ven imágenes: aquí el asa **no** sería
obligatoria. Respuesta corta: **el repo devuelve base64 dentro de un JSON de texto, nunca un bloque
`ImageContent` de MCP, y sin ningún límite de tamaño.**

```ts
// src/tools/sharp.ts:278-297
return {
  content: [
    { type: 'text',
      text: JSON.stringify({
        ...(this.args.outputImage ? { image: outputBase64 } : {}),
        format: outputFormat,
        width: finalMetadata.width,
        height: finalMetadata.height,
        size: outputBuffer.length,
        savedTo: this.args.outputPath || null,
        source: this.args.imagePath ? 'file' : this.args.imageUrl ? 'url' : 'base64',
      }, null, 2) },
  ],
};
```

**Es a la vez el mejor y el peor resultado de los cuatro repos.**

Lo mejor: **es el único que devuelve un objeto estructurado y no prosa.** `format`, `width`, `height`, `size`,
`savedTo` — eso es literalmente el asa que la regla 1 de FileX especifica (`{ruta_salida, formato, bytes, …}`),
y cuesta unos 40 tokens. Ningún otro de los cuatro llega ahí.

Lo peor, y son tres cosas:

1. **No es `ImageContent`.** `grep type: 'image'` sobre `src/` → cero resultados. `bufferToBase64`
   (`src/utils.ts:63-65`) antepone `data:${mimeType};base64,`, prefijo que hace la cadena **inválida** para el
   campo `data` de un `ImageContent` MCP (que exige base64 puro): señal de que emitir un bloque de imagen nunca
   se contempló. El `mimeType` correcto y el buffer están disponibles en `sharp.ts:272`; construir
   `{type:'image', data, mimeType}` habría sido trivial. **El modelo recibe una tira de base64 como texto plano:
   paga el coste en tokens de la imagen y no obtiene la capacidad multimodal.** Es el peor de los dos mundos.
   El contrato está fijado por los tests: `tests/tools/sharp.test.ts:364` asserta
   `resultContent.image.startsWith('data:image/jpeg;base64,')`.
2. **No hay límite de tamaño. Ninguno, en ninguna parte.** Verificado en negativo: no hay `maxSize`, ni umbral en
   bytes, ni comparación contra `outputBuffer.length` (su único uso es informativo, `sharp.ts:288`), ni truncado,
   ni fallback «si pesa más de X, devuelve solo la ruta». `constants.ts` son 11 líneas y no contiene ningún cap
   (§C.5). El único freno es el booleano `outputImage`, con default seguro `false` (`sharp.ts:50`): un
   interruptor todo-o-nada que **decide el modelo**. Si lo pone a `true` sobre un PNG de 5 MB, se serializa el
   100 % del base64 —**además indentado con `null, 2`** (`sharp.ts:293`)— y se manda por stdio. Sin corte, sin
   error, sin aviso.
3. Lo único que en la práctica mantiene pequeña la salida es un accidente: los defaults `DEFAULT_WIDTH = 800` /
   `DEFAULT_HEIGHT = 600` (`constants.ts:5-6`) aplicados en `sharp.ts:164-165`. Y ni eso es fiable: si el modelo
   pasa solo `width`, `height` queda `undefined` (`sharp.ts:159-162`) y el default no aplica.

**Conclusión para FileX: el caso «devolver la imagen al modelo» sigue sin precedente resuelto.** Este repo no es
la referencia que se buscaba; es el contraejemplo. La regla que sale de aquí es propia y hay que escribirla:
*devolver `ImageContent` de verdad, solo bajo un cap de bytes explícito, y por encima del cap devolver el asa con
las dimensiones* — porque un thumbnail de 800×600 en JPEG q80 son ~60 KB ≈ 80 KB de base64, del orden de 20–30 K
tokens, que ya es caro; y una foto de iPhone sin redimensionar son millones.

### C.4 Rutas: sin confinamiento, y `upload_image` es un primitivo de exfiltración

**No hay raíz, ni allowlist, ni sandbox, ni `realpath`, ni `path.resolve`.** El módulo `path` de Node **ni
siquiera se importa** en `src/`; la única aparición de `path.join` es `error.path.join('.')` de zod
(`factory.ts:62`).

```ts
// sharp.ts:75-78 — lectura arbitraria
const normalizedPath = normalizeFilePath(this.args.imagePath);
inputBuffer = fs.readFileSync(normalizedPath);

// sharp.ts:250-254 — escritura arbitraria elegida por el modelo, sin guard de sobrescritura
const normalizedOutputPath = normalizeFilePath(this.args.outputPath);
fs.writeFileSync(normalizedOutputPath, outputBuffer);
```

`normalizeFilePath` (`src/utils.ts:72-89`) **no es una función de seguridad**: solo des-escapa caracteres de
shell (`\ ` → espacio en `:74`, y `\'`, `\"`, `` \` ``, paréntesis y llaves en `:77-86`), un parche para cuando el
modelo pega una ruta copiada de una terminal. En Windows puede corromper rutas legítimas con backslash.

Y el caso grave: `upload_image` lee la ruta que diga el modelo (`upload.ts:77-87`, `:80`) y **la sube a un bucket
de nube** (`:129`) **sin validar en ningún momento que sea una imagen** — `UploadTool.getInputBuffer`
(`upload.ts:69-99`) no llama a sharp ni mira magic bytes. Un `imagePath: '~/.aws/credentials'` se lee y se sube.
(La ruta por URL sí valida `content-type: image/*` en `utils.ts:107-113`; la ruta por fichero no valida nada.)

Ironía arquitectónica que vale como lección de diseño: **los servicios de nube sí tienen guard de sobrescritura**
(`s3.ts:56-74`, `cloudflare.ts:50-67`, `gcloud.ts:51-59`, todos con `File ... already exists. Set overwrite=true`),
y **el disco local del usuario no tiene ninguno**. `resize_image` sobrescribe en silencio.

Temporales: no se usa ninguno. Todo en memoria con Buffers; el único artefacto en disco es el `outputPath` pedido.

### C.5 Errores y `constants.ts`

**No hay ninguna función de saneado o clasificación.** `src/utils.ts` completo (128 líneas) contiene solo
validadores y helpers: `isValidInputFormat`, `isValidOutputFormat`, `isValidDimensions`, `isValidQuality`,
`getFileExtension`, `base64ToBuffer`, `bufferToBase64`, `normalizeFilePath`, `fetchImageFromUrl`. Nada de
`sanitizeError`/`classifyError`.

```ts
// sharp.ts:305-312 — dos canales mezclados
if (error instanceof McpError) { throw error; }           // → error de protocolo JSON-RPC
return { content: [{ type: 'text',
         text: `Error processing image: ${error instanceof Error ? error.message : String(error)}` }],
         isError: true };                                  // → mensaje de sharp/libvips VERBATIM
```

El mensaje de libvips llega crudo (`"VipsJpeg: Premature end of JPEG file"`, `"Input buffer contains unsupported
image format"`). No es un banner de 3 KB como el de ffmpeg —libvips es escueto— pero tampoco está traducido ni
acotado. Los mensajes construidos a mano filtran la ruta absoluta: `Failed to read image from path:
${this.args.imagePath}. ${error.message}` (`sharp.ts:80-84`), `Failed to save image to ${this.args.outputPath}:
…` (`:256-260`), y los de libheif verbatim (`:136-141`). Los servicios de nube pueden filtrar ARNs, nombres de
bucket y request IDs del SDK de AWS (`s3.ts:111-114`, `cloudflare.ts:102-105`, `gcloud.ts:85-88`).

Bug de mensaje engañoso: cualquier `ZodError` de configuración —de Cloudflare o de GCS— se reporta como
**`"S3 configuration validation failed: …"`** con el `"S3"` hardcodeado (`factory.ts:60-67`, `:65`).

`constants.ts` completo son **11 líneas**:

| Constante | Valor | Línea |
|---|---|---|
| `SUPPORTED_INPUT_FORMATS` | `['jpeg','jpg','png','webp','avif','tiff','gif','heic','heif']` | `constants.ts:1` |
| `SUPPORTED_OUTPUT_FORMATS` | `['jpeg','png','webp','avif']` | `constants.ts:2` |
| `DEFAULT_QUALITY` | `80` | `constants.ts:4` |
| `DEFAULT_WIDTH` | `800` | `constants.ts:5` |
| `DEFAULT_HEIGHT` | `600` | `constants.ts:6` |
| `SUPPORTED_UPLOAD_SERVICES` | `['s3','cloudflare','gcloud']` | `constants.ts:9` |
| `DEFAULT_UPLOAD_SERVICE` | `'s3'` | `constants.ts:10` |

**Lo que no está parametrizado y debería:** ningún cap de tamaño; ningún timeout —`fetchImageFromUrl`
(`utils.ts:94-127`) llama a `fetch(url)` **sin `AbortController`**, sin límite de bytes descargados (`:116-117`
hace `arrayBuffer()` de lo que sea) y **sin protección SSRF** (`localhost`, `169.254.169.254` no están
bloqueados: es el mismo agujero de markitdown-mcp medido en `bench/mcp-ergonomia.md` §6). El límite dimensional
`10000` está duplicado a mano en `utils.ts:24`, `:27` y `sharp.ts:28-29`; y `isValidDimensions`,
`isValidQuality` e `isValidOutputFormat` (`utils.ts:16-41`) son **código muerto en producción**, solo los llaman
los tests (`tests/utils.test.ts:29-73`). `DEFAULT_UPLOAD_SERVICE` tampoco se usa nunca: `factory.ts:9` hardcodea
`'s3'`.

Detalle operativo relevante: `UploadServiceFactory.create()` se llama en el **constructor** (`server.ts:18`), así
que **si faltan credenciales de nube el servidor muere al arrancar aunque el usuario solo quisiera
`resize_image`**, y `bin/image-worker-mcp.mjs:12` se traga el error con `.catch(() => process.exit(1))` sin
imprimir nada. Un servidor de conversión no debe morir por una capacidad que nadie pidió.

---

## D) `markitdown_mcp_server` — 162 líneas, 86 ⭐, y **cero herramientas**

El hallazgo es estructural y no lo anticipaba el enunciado.

**Este servidor no expone ninguna herramienta MCP. Expone dos *prompts*.**

```python
# src/markitdown_mcp_server/server.py:8-31
PROMPTS = {
    "md": types.Prompt(name="md",
        description="Convert document to markdown format using MarkItDown",
        arguments=[types.PromptArgument(name="file_path",
                   description="A URI to any document or file", required=True)]),
    "ls": types.Prompt(name="ls",
        description="list files in a directory",
        arguments=[types.PromptArgument(name="directory",
                   description="directory to list files", required=True)]),
}
```

Solo hay dos handlers registrados: `@app.list_prompts()` (`server.py:48`) y `@app.get_prompt()` (`server.py:53`).
**No hay `@app.list_tools()` ni `@app.call_tool()` en las 153 líneas de `server.py`.** Usa la API de bajo nivel
`Server("document-conversion-server")` (`server.py:45`), no FastMCP, así que las capacidades anunciadas en
`initialize` (`server.py:148-151`) no incluirán herramientas.

### D.1 En qué se diferencia del `markitdown-mcp` oficial de Microsoft

`repos/ai-engines/markitdown/packages/markitdown-mcp/src/markitdown_mcp/__main__.py`, 140 líneas:

| | Oficial (Microsoft) | Este (KorigamiK) |
|---|---|---|
| Superficie MCP | **1 herramienta** `convert_to_markdown(uri)` (`__main__.py:20-23`) | **0 herramientas, 2 prompts** (`server.py:8-31`) |
| API del SDK | FastMCP (`__main__.py:5`, `:17`) | `mcp.server.Server` de bajo nivel (`server.py:6`, `:45`) |
| API de markitdown | `.convert_uri(uri)` — esquemas `http:`/`https:`/`file:`/`data:` (`__main__.py:23`) | `.convert(file_path)` — **ruta del sistema**, API antigua (`server.py:37`) |
| Transportes | stdio + Streamable HTTP + SSE, con `Starlette`/`uvicorn` (`__main__.py:34-78`, `:115-134`) | solo stdio (`server.py:141`) |
| Aviso de seguridad | Sí: al bindear fuera de localhost imprime que **no hay autenticación y el servidor lee ficheros con los privilegios del usuario** (`__main__.py:117-128`) | Ninguno |
| Plugins | `MARKITDOWN_ENABLE_PLUGINS` con parseo explícito (`__main__.py:26-31`) | No existe |
| Extras | — | `ls` lista **cualquier directorio del disco** (`server.py:87-136`), y `main()` ejecuta `os.system("notify-send …")` al arrancar (`__init__.py:8`) |

Nota sobre las rutas: el de terceros usa `md.convert(file_path)`, así que **acepta rutas del sistema** —justo lo
que el oficial rechaza con `Unsupported URI scheme: D` (`bench/mcp-ergonomia.md` §6)— y probablemente por eso a
sus usuarios «les funciona» donde el oficial falla. Es la regla 11 al revés: dos servidores del mismo motor con
convenciones de ruta **incompatibles**.

### D.2 Por qué un servidor de prompts no sirve para un agente — y qué dice del mercado

La diferencia protocolaria es la que importa: **una herramienta la elige el modelo; un prompt lo invoca la
persona.** Los prompts MCP se exponen en los clientes como comandos de barra que el usuario escribe. Un agente
autónomo que reciba «convierte este PDF» y consulte `tools/list` **no verá nada**. Este servidor no es
automatizable: es una macro para un humano.

Y el resultado del prompt `md` inyecta **el documento entero** en un `PromptMessage` de rol `user`
(`server.py:72-82`):

```python
text=f"Here is the converted document in markdown format:\n{markdown_title or ''}\n{markdown_content}"
```

Los mismos 85 259 tokens medidos para un PDF de 60 páginas, con dos agravantes: entran como **mensaje de
usuario**, no como resultado de herramienta —el modelo los trata como instrucción, no como dato devuelto— y sin
posibilidad de acotar. El `ls` (`server.py:87-136`) hace algo aún más caro para lo que aporta: **lista el
directorio tres veces** en la misma cadena (agrupado por extensión en `:111-115`, sin extensión en `:116-117`, y
listado completo numerado en `:120-122`).

Manejo de errores: `convert_to_markdown` (`server.py:34-41`) atrapa `Exception` y **devuelve la excepción como
si fuera el documento**:

```python
except Exception as e:
    return None, f"Error converting document: {str(e)}"
```

El valor de retorno tiene el mismo tipo en éxito y en fallo, y aguas abajo (`server.py:70-78`) esa cadena se
inyecta como «Here is the converted document in markdown format: Error converting document: …». **El modelo
recibe un mensaje que le dice que eso es el documento.** Es la regla 9 en su forma más pura.

**Qué dice del mercado, que es la pregunta real.** Que el MCP de conversión más difundido del mundo son 162
líneas, cero herramientas, dos prompts, sin tests, sin licencia de dependencias fijada, con `os.system` en el
arranque, un `description = "Add your description here"` sin rellenar en `pyproject.toml:5` y `server_name =
"example"` en el `initialize` (`server.py:146`) — y aun así con más estrellas que el de Microsoft — significa que
**la difusión la determinan el registro (Smithery: badge en `README.md:3`, `smithery.yaml` en la raíz) y la
facilidad de instalar, no la calidad del contrato**. Para FileX es una advertencia doble: la distribución importa
tanto como el diseño, y **no hay competencia real que superar en calidad**. La barra del sector está en el suelo;
lo que no está resuelto por nadie es exactamente lo que este documento no ha podido encontrar en ningún repo:
un contrato de salida binaria estructurado, anotado, acotado y confinado.

---

## E) `kordoc` — clasificación de errores: `sanitizeError`, `classifyError`, `KordocError`

Componente único, en `src/utils.ts` (181 líneas) y sus call sites. Es el problema que docling-mcp resuelve mal
(respondió `pip install openai-whisper` ante un `.mkv`).

### E.1 `KordocError`: un marcador de tipo, no una estructura

```ts
// src/utils.ts:23-28
export class KordocError extends Error {
  constructor(message: string) { super(message); this.name = "KordocError" }
}
```

**Sin `code`, sin `hint`, sin `cause`, sin `path`.** Toda la información —incluida la pista accionable y a veces
la ruta absoluta— va como texto libre dentro de `message`. El comentario de `utils.ts:19-22` explica el
propósito: permitir que `sanitizeError` distinga **por `instanceof`**, sin matching de patrones sobre una
allowlist. Única subclase: `ZipBombError` (`src/hwpx/parser-shared.ts:20`).

El enum de códigos existe pero **vive desacoplado de la excepción**: `ErrorCode` en `src/types.ts:289-302`, doce
valores — `EMPTY_INPUT`, `UNSUPPORTED_FORMAT`, `ENCRYPTED`, `DRM_PROTECTED`, `CORRUPTED`, `DECOMPRESSION_BOMB`,
`ZIP_BOMB`, `IMAGE_BASED_PDF`, `NO_SECTIONS`, `PARSE_ERROR`, `MISSING_DEPENDENCY`, `OUTPUT_TOO_LARGE`. El código
se aloja en `ParseFailure.code?` (`types.ts:395-401`), y excepción y código solo se reúnen en el borde del
parser (`src/index.ts:129`, `:140`, `:152`, `:185`, `:207`, `:217`, `:227`, `:237`, `:247`), siempre como
`{ success:false, fileType, error: sanitizeError(err), code: classifyError(err) }`.

### E.2 `classifyError`: matching de substrings, no de tipos

```ts
// src/utils.ts:166-181
export function classifyError(err: unknown): ErrorCode {
  if (!(err instanceof Error)) return "PARSE_ERROR"
  const msg = err.message
  if (msg.includes("DRM")) return "DRM_PROTECTED"
  if (msg.includes("암호화") || msg.includes("암호로 보호")) return "ENCRYPTED"
  if (msg.includes("optional dependency")) return "MISSING_DEPENDENCY"
  if (msg.includes("Invalid string length") || msg.includes("Cannot create a string longer")) return "OUTPUT_TOO_LARGE"
  if (msg.includes("ZIP bomb") || msg.includes("ZIP 비압축 크기 초과") || msg.includes("ZIP 엔트리 수 초과")) return "ZIP_BOMB"
  if (msg.includes("bomb") || msg.includes("크기 초과") || msg.includes("압축 해제")) return "DECOMPRESSION_BOMB"
  if (msg.includes("이미지 기반")) return "IMAGE_BASED_PDF"
  if (msg.includes("섹션") && (msg.includes("찾을 수 없") || msg.includes("없음"))) return "NO_SECTIONS"
  if (msg.includes("시그니처") || msg.includes("복구할 수 없")) return "CORRUPTED"
  return "PARSE_ERROR"
}
```

Nueve ramas más fallback, todas sobre `err.message`. Puntos precisos:

- **No mira `err.code` de Node.** `ENOENT`/`EACCES`/`EISDIR` **no tienen rama** y caen a `PARSE_ERROR` (`:180`);
  el manejo de errores de fs vive aparte, en `mcp.ts:86-97`.
- El orden es deliberado y está comentado: DRM antes que cifrado (`utils.ts:169`), `ZIP_BOMB` antes que
  `DECOMPRESSION_BOMB` porque la segunda regla es más laxa.
- **Los patrones están en coreano.** La clasificación funciona porque los mensajes los escribió kordoc. Una
  excepción de librería en inglés cae casi siempre a `PARSE_ERROR`. Es frágil por construcción: un cambio de
  redacción rompe la clasificación en silencio. `tests/error-codes.test.ts:8-52` fija diez casos, que es el
  único freno.
- **`classifyError` NO adjunta hint.** Devuelve un string enum. Las pistas accionables existen pero están
  hardcodeadas en el `message` en el sitio del `throw` — p.ej. `src/hwp5/parser.ts:139` lanza
  *«documento HWP protegido por contraseña. Especifique la contraseña de apertura en la opción `password`»*,
  que **nombra el parámetro exacto de la herramienta MCP**.

### E.3 `sanitizeError`: un allowlist binario, no un scrubber

```ts
// src/utils.ts:34-37
export function sanitizeError(err: unknown): string {
  if (err instanceof KordocError) return err.message
  return "문서 처리 중 오류가 발생했습니다"       // "ocurrió un error procesando el documento"
}
```

Dos comportamientos y nada en medio: **`KordocError` → verbatim, sin recortar nada; cualquier otra cosa → se
descarta entera y se sustituye por una constante.**

- **Trazas de pila: nunca se emiten.** Solo se toca `.message`, jamás `.stack`. En todo `src/`.
- **Rutas absolutas: se eliminan solo si venían de un `Error` no-Kordoc.** Si el `KordocError` las lleva dentro,
  pasan intactas — y las lleva, por diseño: `mcp.ts:45`, `:46`, `:71`, `:120`, `:129`, `shared/offline.ts:72`.
- **`stderr` de motores: se filtra cuando alguien lo re-envuelve en `KordocError`.** Cuatro puntos confirmados:
  `hwp3/parser.ts:123-125` (mensaje crudo de `zlib.inflateRawSync`), `hwpx/parser-shared.ts:118` (crudo de
  xmldom), `hwpx/profile-io.ts:80` (crudo de `JSON.parse`), `ocr/image-ocr.ts:88` (crudo del `import("sharp")`
  fallido).
- **Secretos: no hay redacción.** El módulo `src/redact.ts` no se aplica a errores.
- Contrato fijado en `tests/security.test.ts:107-131`: un `ENOENT: … 'C:\Users\admin\secret.hwp'`, una ruta de
  `node_modules/pdfjs-dist/build/pdf.js:1234` y un `EACCES … '/home/user/.ssh/id_rsa'` **se aplastan** al
  mensaje genérico. Pero ese test cubre el caso `Error` nativo; **no cubre el `KordocError` con ruta dentro**.

### E.4 La pieza realmente valiosa: `describeError`, que es **solo del MCP**

La CLI importa `sanitizeError`/`classifyError` crudos (`src/cli.ts:12`) y no tiene capa de pistas. El MCP tiene
su propio wrapper, y es lo que hay que copiar:

```ts
// src/mcp.ts:84-100
export function describeError(err: unknown): string {
  if (err instanceof KordocError) return err.message
  const code = (err as NodeJS.ErrnoException)?.code
  if (typeof code === "string" && /^E[A-Z]+$/.test(code)) {
    const hints: Record<string, string> = {
      ENOENT: "파일 또는 디렉토리를 찾을 수 없습니다",   // no se encuentra el fichero o directorio
      EACCES: "접근 권한이 없습니다",                   // sin permiso de acceso
      EPERM:  "작업 권한이 없습니다",
      EISDIR: "파일이 아니라 디렉토리입니다",            // es un directorio, no un fichero
      ENOTDIR:"경로 중간이 디렉토리가 아닙니다",
      ENOSPC: "디스크 공간이 부족합니다",               // no queda espacio en disco
    }
    return `파일 시스템 오류 [${code}]: ${hints[code] ?? "경로와 권한을 확인하세요"}`
  }
  const cls = classifyError(err)
  return cls === "PARSE_ERROR" ? sanitizeError(err) : `문서 처리 중 오류가 발생했습니다 (${cls})`
}
```

**Esta es la única tabla código→pista del repo, y es exclusiva de la superficie MCP.** Traduce el `errno` a
lenguaje natural **sin la ruta** (`:96`), y para lo demás anexa el `ErrorCode` entre paréntesis en vez de
aplastar todo a la frase genérica; la razón está declarada en `mcp.ts:81-82`. Es el reconocimiento explícito de
que **el modelo necesita otro texto que la persona**, y es la confirmación práctica del coste de la capa MCP que
`analysis/00-mcp-patrones.md` estimó.

**La respuesta MCP es siempre `{content:[{type:"text", text}], isError: true}` — texto plano, nunca un objeto,
nunca un campo `code`.** Dos familias, ~35 sitios: `` `오류: ${describeError(err)}` `` (`mcp.ts:244-245`, `:280-281`,
`:355-356`, `:406-407`, `:466-467`, `:508-509`, `:542-543`, `:718-719`, `:777-778`, `:842-843`, `:1021-1024`,
`:1143-1146`) y `` `파싱 실패 (${result.fileType}): ${result.error}` `` (`:207`, `:389`, `:438`, `:531`, `:660`,
`:932`, `:988`).

> **Hallazgo importante:** en la segunda familia el MCP usa `result.fileType` y `result.error` pero **descarta
> `result.code`**. El `ErrorCode` estructurado (`ENCRYPTED`, `CORRUPTED`, `ZIP_BOMB`…) **nunca llega al modelo
> por la ruta de parseo fallido**. Solo llegaría vía `describeError:99`, que casi nunca se alcanza porque la
> línea 85 intercepta los `KordocError`. En la práctica **el modelo ve prosa, no códigos** — mientras que la
> CLI sí los emite estructurados en `--format json` (`cli.ts:176-183`). **La superficie de máquina expone menos
> estructura que la superficie de humano.** Es exactamente al revés de como debe ser.

### E.5 Los mensajes que ve el modelo, y el veredicto

Reconstruidos del código (longitudes por conteo de caracteres, no medidas en ejecución):

| Caso | Mensaje | ~chars | Juicio |
|---|---|---:|---|
| Fichero inexistente (`mcp.ts:43-45` → `:244`) | `오류: 파일을 찾을 수 없습니다: C:\…\보고서.hwp` | 50-70 | Corto y claro, **pero devuelve la ruta absoluta resuelta** |
| **Extensión no permitida** (`mcp.ts:52`) | `오류: 지원하지 않는 확장자입니다: .txt (허용: .hwp, .hwpx, .hml, .pdf, .xls, .xlsx, .docx, .png, .jpg, .jpeg, .webp)` | ~115 | **El mejor del sistema**: nombra la causa y **enumera las alternativas válidas** |
| Formato no soportado por magic bytes (`mcp.ts:183`) | `지원하지 않는 파일 형식입니다: C:\…\archivo.pdf` | ~40 | **No** enumera alternativas y repite la ruta. Peor que el anterior |
| Fichero corrupto (`hwp5/parser.ts:131` → `mcp.ts:207`) | `파싱 실패 (hwp): HWP 시그니처 불일치` | ~25 | Nombra la causa, **pierde el `CORRUPTED`**, no sugiere nada |
| **Documento cifrado** (`hwp5/parser.ts:139`) | `파싱 실패 (hwp): 암호로 보호된 HWP 문서입니다. password 옵션에 열기 암호를 지정하세요.` | ~60 | **El mejor end-to-end**: causa + **el parámetro exacto de la herramienta** para reintentar |
| Excepción de librería sin envolver (`index.ts:207` → `mcp.ts:389`) | `파싱 실패 (pdf): 문서 처리 중 오류가 발생했습니다` | ~30 | **Cero información.** Sobre-saneado: el modelo no puede corregirse |

**Veredicto de forma: todos por debajo de 120 caracteres, ninguno es un volcado, ninguno lleva traza de pila.**
El problema no es la verbosidad —que es el pecado de A, B y de docling-mcp— sino la **inconsistencia**: unos
enumeran alternativas, otros son opacos, y el código estructurado se tira antes de llegar al modelo.

### E.6 ¿Comete el pecado de `pip install openai-whisper`? **Sí, tres veces confirmadas**

| Sitio | Texto que llega al modelo |
|---|---|
| `src/index.ts:196-200` | `PDF 파싱에 pdfjs-dist가 필요합니다. 설치: npm install pdfjs-dist` → llega vía `mcp.ts:207/389/438` |
| `src/ocr/image-ocr.ts:86-89` | `…optional dependency 'sharp' 가 필요합니다. \`npm install sharp\` 후 다시 실행하세요. 원인: ${e.message}` → `index.ts:129` lo preserva por ser `KordocError`, y **arrastra el mensaje crudo del import fallido** |
| `src/render/rasterize.ts:34-36` | `PNG 래스터에는 sharp가 필요합니다 (npm install sharp). …format: "svg" + output_path…` → `describeError:85` verbatim → `mcp.ts:899` |

El comentario de `src/ocr/image-ocr.ts:85` es explícito: **el diseño busca deliberadamente que el `npm install`
atraviese el saneamiento**. Es la misma clase de fallo que docling-mcp.

Pero es **menos grave en forma, y una de las tres apunta a la solución**: `rasterize.ts:34-36` acompaña la
instrucción de instalación con **una alternativa in-band que el modelo sí puede ejecutar ahora mismo**
(`format: "svg"` + `output_path`). Eso es lo que docling-mcp no hace y lo que FileX debe hacer siempre: si falta
una capacidad, **el mensaje enumera los destinos que sí están disponibles**, y la instrucción de instalación —si
se emite— va detrás, no delante.

E inconsistencia real detectada: `src/ocr/engine.ts:333-336`, `src/ocr/pdf-ocr.ts:184-187` y
`src/pdf/formula/pipeline.ts:310-313` construyen el mismo texto pero lanzan **`new Error`, no `KordocError`**, así
que `sanitizeError:36` los aplasta. **Cuatro `tryImport` casi idénticos, tres pierden la pista y uno la
conserva.** El régimen de saneado depende de qué clase se instanció, no de qué información es segura.

### E.7 Extra encontrado que resuelve la regla 9 mejor que nadie: el canal de avisos

Hay un segundo mecanismo, y es la mejor respuesta que he visto al «éxito vacío» de markitdown (PDF escaneado →
cadena vacía con `isError:false`). `ParseWarning` con **17 códigos estructurados** (`src/types.ts:249-277`):
`SKIPPED_IMAGE`, `SKIPPED_OLE`, `TRUNCATED_TABLE`, `OCR_FALLBACK`, `UNSUPPORTED_ELEMENT`, `BROKEN_ZIP_RECOVERY`,
`HIDDEN_TEXT_FILTERED`, `MALFORMED_XML`, `PARTIAL_PARSE`, `LENIENT_CFB_RECOVERY`, `NEEDS_OCR`, `OCR_FAILED`,
`OCR_APPLIED`, `OCR_LOW_CONF`, `COM_EMPTY`, `DRM_COM_FALLBACK`, `PAGE_BOUNDARY_APPROXIMATE`.

```ts
// src/pdf/parser.ts:257-263
if (isImageBased && ocrDone.size === 0) {
  // OCR 미설정/실패 — 빈 출력을 무경고로 내보내지 않고 경고 + 플래그로 가시화 (v3.0)
  warnings.push({
    message: `이미지 기반 PDF (${pageCount}페이지, 텍스트 ${totalChars}자) — 텍스트 레이어가 없어 OCR이 필요합니다`,
    code: "NEEDS_OCR",
  })
}
```

El comentario dice literalmente *«no emitir salida vacía sin aviso»*. Y el aviso se cierra en la descripción del
parámetro de la herramienta MCP (`src/mcp.ts:160`): *«si el resultado del parseo tiene un aviso `NEEDS_OCR`,
reintenta con esta opción»*. **Es un bucle de autocorrección completo: la salida emite una señal codificada y el
catálogo le dice al modelo qué hacer con ella.** Hay incluso granularidad por página con cinco motivos
distinguidos (`pdf/parser.ts:269-281`: `low_text`, `high_pua`, `high_control`, `high_replacement`,
`garbled_hangul`) y un umbral explícito `DOC_NEEDS_OCR_PAGE_RATIO = 0.3` (`src/pdf/quality.ts:156`, aplicado en
`:214`).

Esto es más valioso para FileX que toda la clasificación de errores, porque cubre el caso que ni A ni B ni C
tienen: **el éxito parcial**. Una conversión de vídeo que perdió la pista de subtítulos, un PDF sin capa de
texto, un HEIC del que solo se leyó la primera imagen del burst — todos son éxitos con pérdida, y sin un canal
de avisos codificado el modelo no se entera.

---

## Tabla comparativa transversal

| | `video-audio-mcp` | `ffmpeg-mcp-lite` | `image-worker-mcp` | `markitdown_mcp_server` | `kordoc` (contexto) | *docling-mcp* (medido) |
|---|---|---|---|---|---|---|
| **Qué devuelve tras convertir** | **Prosa** con la ruta, redacción variable según camino interno (`server.py:33`, `:59`, `:67`, `:336`) | **Prosa** con la ruta (`convert.py:66`); **+ métricas** en compress (`compress.py:76-81`); **JSON filtrado** en info (`info.py:88`) | **JSON estructurado** `{format,width,height,size,savedTo}` (`sharp.ts:278-297`); **+ base64 completo si `outputImage:true`, sin cap** | **El documento entero** como `PromptMessage` de rol *user* (`server.py:72-82`) | Markdown en `content` texto | Asa (`document_key`), **36 tok** |
| **Nº de herramientas** | **27** (`server.py`, grep) — ≈3 610 tok de catálogo *estimados* | **8** (`server.py:17-24`) — ≈811 tok *estimados* | **2** (`server.ts:28-34`) | **0 herramientas / 2 prompts** (`server.py:8-31`) | 15 (`mcp.ts`) | 19 → 3 (5 280 → 880 tok, medido) |
| **Agrupación** | **Plana.** Comentarios de sección (`:245`,`:330`,`:483`) y categorías del README: documentación, no protocolo | **Un fichero por herramienta**, registro explícito en `server.py`; agrupa por intención de usuario | Plana (2) | N/A | Plana | **Grupos cargables** por argumento CLI |
| **Anotaciones** | **Cero** (grep sin resultados) | **Cero** (`mcp.tool()(fn)` desnudo) | **Cero** (API legacy `server.tool`, no `registerTool`) | N/A (sin herramientas) | **Cero** (grep en `mcp.ts`) | **6/19 `readOnlyHint`, 2 `destructiveHint`** |
| **Confinamiento de rutas** | **Ninguno.** Entrada: `os.path.exists` en 11 sitios, nada en el resto. **Salida: la elige el modelo, sin validar** (25 herramientas) | **Entrada:** `resolve()` sin raíz. **Salida: confinada** a `FFMPEG_OUTPUT_DIR` en 5/8 (`convert.py:35-36`), **fuga en `merge`/`subtitles`** (`merge.py:38-39`) | **Ninguno.** `path` ni se importa. `readFileSync`/`writeFileSync` con la cadena del modelo (`sharp.ts:78`, `:254`). `upload_image` **sube ficheros arbitrarios sin validar que sean imagen** | **Ninguno.** `ls` lista cualquier directorio (`server.py:87-136`) | `safePath` con allowlist de extensiones (`mcp.ts:43-52`) | Ninguno (filtro de formatos ≠ defensa) |
| **Manejo de errores** | **`stderr` crudo de ffmpeg**, hasta **dos volcados concatenados** (`server.py:344`); **`isError:false` SIEMPRE** (todo se atrapa y se devuelve como cadena) | **`raise` → `isError:true`** ✅, pero con `stderr.decode()` entero dentro (`convert.py:64`). Validación previa: mensajes cortos y accionables (`trim.py:28`) | `isError:true` con `error.message` de libvips verbatim (`sharp.ts:310`); `McpError` se re-lanza como error de protocolo (`:306`) | La excepción **se devuelve donde iría el documento** (`server.py:40-41`) y se inyecta como «aquí tienes el documento» | **`describeError`** con tabla errno→pista (`mcp.ts:84-100`); mensajes <120 chars, sin trazas; **tira el `ErrorCode`** (`mcp.ts:207`); **3 fugas de `npm install`** | Reenvía `pip install openai-whisper`; enumera claves de caché vivas |
| **Tiene tests** | **Sí**: 763 líneas, 29 tests; **verifica duraciones con `ffprobe`** en b-roll/transiciones/concat (`:488`, `:530`, `:680`). Fixture `sample2.mp4` **ausente** | **Sí**: 8 ficheros, ~31 tests; **`conftest.py` genera material con `ffmpeg -f lavfi`** (`:17-40`); **10 tests de error**; solo `test_info` mira dentro del resultado | Sí: `tests/` con 6 ficheros, incl. **2 de integración HEIC real** (`sharp.test.ts:280`, `:392`) | **No** | Sí (`tests/error-codes.test.ts`, `tests/security.test.ts`) | No verificado en este carril |
| **Timeout / límites** | **Ninguno.** `.run()` bloqueante; `Context` importado y no usado (`server.py:2`) | **Ninguno** (grep `timeout|max_|limit` en `src/` → 0). Al menos `create_subprocess_exec` no bloquea el bucle | **Ninguno.** `fetch()` sin `AbortController`, sin límite de bytes, **sin protección SSRF** (`utils.ts:94-127`) | Ninguno | `OUTPUT_TOO_LARGE`, `ZIP_BOMB`, `DECOMPRESSION_BOMB` en el enum | — |
| **Progreso** | No (`Context` sin usar) | No | No | No | No | No |

---

## Componente → repo → veredicto

| Componente | Repo y cita | Veredicto |
|---|---|---|
| **Troceado `tools/<dominio>.py` + `server.py` de solo registro + `config.py`** | `ffmpeg-mcp-lite/src/ffmpeg_mcp_lite/server.py:5-24` | **Copiar tal cual.** Es la forma que FileX necesita: núcleo sin decorador, registro explícito, 811 tok estimados para 8 herramientas |
| **Funciones de herramienta sin decorador, registradas aparte** | `ffmpeg-mcp-lite/server.py:17-24` + `tools/*.py` (no importan `mcp`) | **Copiar tal cual.** Da la separación núcleo/superficie de kordoc con dos líneas de disciplina |
| **`conftest.py` que genera fixtures con el propio motor + `pytest.skip`** | `ffmpeg-mcp-lite/tests/conftest.py:17-60` | **Copiar tal cual.** Cero binarios versionados, propiedades conocidas, honesto sin dependencias |
| **`Literal[...]` en la firma en vez de validar en runtime** | `ffmpeg-mcp-lite/tools/compress.py:12-14`, `audio.py:12`, `frames.py:14` | **Copiar tal cual.** Convierte «error que enumera alternativas» en «catálogo que ya las enumeró» |
| **Salida confinada a un directorio configurado + nombrado determinista** | `ffmpeg-mcp-lite/config.py:13-21` y `convert.py:35-36` | **Adaptar.** La idea es correcta; hay que **cerrar la fuga** de `merge.py:38-39` / `subtitles.py:72-73` y **añadir el confinamiento de entrada** (`resolve()` + comparación contra raíces declaradas) |
| **Recorte del `ffprobe` a los campos que importan** | `ffmpeg-mcp-lite/tools/info.py:46-88` | **Copiar tal cual.** Es la regla 3 (lectura acotada) aplicada al caso binario: de miles de tokens a cientos |
| **Métricas de resultado en la respuesta (original/comprimido/reducción)** | `ffmpeg-mcp-lite/tools/compress.py:71-81` | **Adaptar.** El contenido es el asa correcta; hay que emitirlo **como objeto, no como prosa multilínea** |
| **Detección HEIC por magic bytes `ftyp`** | `image-worker-mcp/src/tools/sharp.ts:96-99` | **Copiar tal cual.** El nombre del fichero lo escribe un agente: no se puede confiar en la extensión |
| **Shim `.d.ts` mínimo para el subpath WASM de libheif** | `image-worker-mcp/src/libheif-js.d.ts:1-11` | **Adaptar** (si FileX usa TS). Copiar la técnica; **completar** `display()` y no procesar solo `decodedImages[0]` (`sharp.ts:110`) |
| **Respuesta como objeto estructurado, no prosa** | `image-worker-mcp/src/tools/sharp.ts:278-297` (campos `format/width/height/size/savedTo`) | **Adaptar.** Los campos son los correctos; hay que **quitar el base64 del JSON de texto** y añadir `duration`, `engine`, `path_taken`, `warnings[]` |
| **Devolver la imagen al modelo como contenido** | `image-worker-mcp` — **no existe**: `type:'image'` no aparece en `src/`, y el base64 va como texto con prefijo `data:` inválido para `ImageContent` (`utils.ts:63-65`) | **Descartar como precedente.** Es un contraejemplo. FileX debe escribir esta regla desde cero: `ImageContent` real, cap de bytes explícito, y por encima del cap → asa |
| **Umbral de tamaño para decidir contenido vs. asa** | Ninguno de los cuatro repos lo tiene | **No hay precedente.** Hueco confirmado |
| **Patrón Factory + Strategy para backends intercambiables** | `image-worker-mcp/src/services/types.ts:49-57` + `factory.ts:8-71` | **Solo como referencia.** Aplicable a los motores de FileX, pero **no copiar la inicialización en el constructor** (`server.ts:18`): mata el servidor si falta un backend que nadie pidió |
| **`describeError`: tabla `errno` → frase, MCP-only, sin la ruta** | `kordoc/src/mcp.ts:84-100` | **Copiar tal cual.** Es la mejor pieza leída en todo el carril. 6 entradas, ~40 tokens de código, y reconoce que el modelo necesita otro texto que la persona |
| **`ParseWarning` + enum `WarningCode` (17 códigos) + `NEEDS_OCR`** | `kordoc/src/types.ts:249-277`, `pdf/parser.ts:257-263`, umbral en `pdf/quality.ts:156` | **Copiar tal cual.** Resuelve el éxito parcial y el «éxito vacío» (regla 9) mejor que nada medido |
| **Cerrar el bucle: la descripción del parámetro dice qué hacer con el código de aviso** | `kordoc/src/mcp.ts:160` («si hay aviso `NEEDS_OCR`, reintenta con esta opción») | **Copiar tal cual.** Autocorrección en un intento, coste cero en tiempo de ejecución |
| **`KordocError` como marcador de tipo para el saneado** | `kordoc/src/utils.ts:23-28` | **Adaptar.** La idea (allowlist por tipo, no por patrón) es buena; **añadir los campos** `code`, `hint`, `path` en vez de meterlo todo en `message` |
| **`classifyError` por substrings del mensaje** | `kordoc/src/utils.ts:166-181` | **Descartar.** Frágil por construcción: patrones en un idioma, se rompe al reescribir un mensaje, y no mira `err.code` de Node. FileX debe llevar el código **en la excepción** |
| **`sanitizeError` binario (verbatim / constante)** | `kordoc/src/utils.ts:34-37` | **Descartar.** Los dos extremos son malos: filtra rutas absolutas cuando es `KordocError` (`mcp.ts:45`) y destruye toda información cuando no lo es (`파싱 실패 (pdf): 문서 처리 중 오류…`, sin nada accionable) |
| **Enumerar alternativas válidas en el mensaje de error** | `kordoc/src/mcp.ts:52` (extensiones permitidas) y `video-audio-mcp/server.py:838` (37 efectos `xfade`) | **Adaptar.** El patrón es el correcto (regla 8), pero **preferir el enum en el esquema**: si las alternativas caben en un `Literal`, el error sobra |
| **Devolver el `stderr` crudo del motor** | `video-audio-mcp/server.py:36`, `:344` (dos volcados); `ffmpeg-mcp-lite/convert.py:64`; `image-worker-mcp/sharp.ts:310` | **Descartar. Los cuatro repos lo hacen.** Es unánime y está unánimemente mal (regla 8) |
| **Error devuelto como cadena con `isError:false`** | `video-audio-mcp` — las 27 herramientas; `markitdown_mcp_server/server.py:40-41` | **Descartar.** Regla 9. `raise` siempre, como hace `ffmpeg-mcp-lite` |
| **27 herramientas planas, una por parámetro de ffmpeg** | `video-audio-mcp/server.py` (9 de ellas son 3 líneas sobre `_run_ffmpeg_with_fallback:332`) | **Descartar.** Regla 5. Todas caben en argumentos opcionales de 3 herramientas |
| **Tests que verifican duración del artefacto con `ffprobe`** | `video-audio-mcp/tests/test_video_functions.py:488`, `:530`, `:680-700` | **Adaptar.** Es la profundidad de assert que le falta a `ffmpeg-mcp-lite`; combinar con su `conftest.py` |
| **Servidor de solo prompts, sin herramientas** | `markitdown_mcp_server/server.py:48-53` | **Descartar.** No es automatizable: un agente que consulte `tools/list` no ve nada |
| **Aviso de seguridad al bindear fuera de localhost** | `markitdown` oficial, `__main__.py:117-128` | **Copiar tal cual** si FileX ofrece transporte HTTP. Es lo único que el oficial hace y nadie más |
| **`os.system("notify-send …")` al arrancar** | `markitdown_mcp_server/__init__.py:8` | **Descartar.** Un servidor stdio no ejecuta comandos de escritorio al arrancar |

---

## Qué cambia en el caso binario

Contra las 16 reglas de `bench/mcp-ergonomia.md` y las 5 de `analysis/00-mcp-patrones.md`.

### Se confirman, y con más fuerza que en el caso documental

**Regla 1 — la respuesta por defecto es un asa.** En texto era una optimización de 2 368×; **en binario es la
única opción física**. Y la evidencia es que los tres repos multimedia llegaron ahí **sin habérselo planteado**:
video-audio-mcp devuelve la ruta en 27 herramientas, ffmpeg-mcp-lite en 8, image-worker-mcp en su JSON. Nadie
intentó devolver un MP4 porque no se puede: `tests/sample.mp4` son 10,5 MB → ~14 M caracteres base64 → millones
de tokens. **En el caso binario la regla 1 no hay que defenderla, hay que ejecutarla bien** — y ninguno de los
tres la ejecuta bien, porque el asa es prosa (§A.2) en vez de objeto.

**Regla 2 — el asa es una ruta en disco, no una clave en memoria.** Confirmada por unanimidad y sin excepciones:
ninguno de los cuatro repos tiene caché de asas en memoria. En binario la ruta es además **obligatoria por otra
razón**: el artefacto ya *existe* en disco como producto de la conversión. En texto docling tenía que elegir
entre caché y fichero; aquí no hay elección. El asa es gratis.

**Regla 5 — pocas herramientas.** Confirmada con la comparación más limpia del carril: 27 herramientas
(≈3 610 tok estimados) frente a 8 (≈811 tok) **cubriendo el mismo dominio**, porque uno agrupa por parámetro de
ffmpeg y el otro por intención del usuario. Y la evidencia de que el troceado fino es innecesario está en el
propio repo: nueve de las 27 son tres líneas sobre el mismo helper (`server.py:332-348`).

**Regla 6 — anotar las herramientas.** Confirmada por ausencia total: **los cuatro repos tienen cero
anotaciones**, incluido kordoc. En binario el argumento es *más* fuerte que en texto, porque **una conversión
binaria escribe en disco y sobrescribe sin preguntar**: `resize_image` sobrescribe en silencio
(`sharp.ts:254`, sin guard, mientras sus propios backends de nube sí lo tienen) y `ffmpeg -y` está en los 7
subprocesos de ffmpeg-mcp-lite. `destructiveHint` en una herramienta que devuelve texto es informativo; en una
que sobrescribe un fichero del usuario es la diferencia entre auto-aprobar y no.

**Regla 8 — traducir los errores del motor.** Confirmada de forma unánime y peor de lo esperado: **los cuatro
reenvían el stderr crudo**, y video-audio-mcp llega a concatenar **dos volcados completos de ffmpeg** en una
cadena (`server.py:344`) en nueve herramientas. Y la falta de accionabilidad tiene precedente en kordoc, que
reenvía `npm install` tres veces (`index.ts:198`, `image-ocr.ts:88`, `rasterize.ts:35`) — el mismo pecado que
docling-mcp. La única salida buena vista en todo el carril es `rasterize.ts:34-36`: **la instrucción de
instalación va acompañada de una alternativa que el modelo puede ejecutar ahora**.

**Regla 9 — un fallo es un fallo.** Confirmada, y la violación es más sistemática que en texto. Con markitdown
era un caso patológico (PDF escaneado → cadena vacía). En video-audio-mcp **todos los fallos, siempre, llegan
como `isError:false`** con la palabra «Error» dentro de una frase; en markitdown_mcp_server la excepción se
inyecta **donde iría el documento**, precedida de «Here is the converted document in markdown format»
(`server.py:40-41` + `:78`). El único que lo hace bien es ffmpeg-mcp-lite, con `raise` (`convert.py:64`).

**Regla 12 — confinar el sistema de ficheros.** Confirmada. Tres de cuatro no tienen confinamiento de ninguna
clase, y `image-worker-mcp` añade una vuelta de tuerca que en texto no existía: `upload_image` **lee un fichero
arbitrario del disco y lo sube a un bucket** sin comprobar que sea una imagen (`upload.ts:69-99`, `:129`). La
lectura arbitraria en texto es una fuga hacia el contexto; aquí es una fuga hacia fuera de la máquina.

**Regla 13 — red desactivada por defecto.** Confirmada: `fetchImageFromUrl` (`utils.ts:94-127`) hace `fetch(url)`
con la URL que escriba el modelo, **sin `AbortController`, sin límite de bytes y sin bloqueo de `localhost` /
`169.254.169.254`**. Es el mismo SSRF de markitdown-mcp, en una herramienta también sin `openWorldHint`.

### Hay que matizarlas

**Regla 3 — junto a `convert`, lecturas acotadas.** En texto, «lectura acotada» significaba trozos del documento
(estructura 2 347 tok, búsqueda 556, un ítem 20). **En binario el documento no se puede leer por trozos: hay que
sustituirlo por proyecciones.** Los precedentes muestran cuáles:

- **`ffprobe` filtrado** — `info.py:46-88`, de miles de tokens a cientos. El equivalente de
  `get_overview_of_document_anchors`.
- **Extracción de fotogramas** — `frames.py:10-92`. Un vídeo de 10 minutos se «lee» como 10 imágenes. Es lo más
  cerca que un modelo puede estar de ver el contenido.
- **Métricas de la operación** — `compress.py:71-81` (original / resultado / % reducción). No existe en texto:
  ahí no hay «¿funcionó?», hay «¿qué dice?».

La regla se reformula: *junto a `convert`, herramientas de **proyección** —`probe` estructurado, `thumbnail`,
`frames`, `waveform`— y el binario nunca, bajo ninguna circunstancia, se devuelve como contenido.* Y la
`max_bytes` de la regla 3 cambia de sentido: en texto acota lo que se devuelve; **en binario acota lo que se
acepta como entrada y cuánto tiempo puede correr el motor.**

**Regla 4 — no duplicar `content` y `structuredContent`.** En texto era un multiplicador ×2 con riesgo de
170 942 tokens. **En binario el riesgo desaparece del lado de la salida** (nadie va a duplicar 36 tokens de
asa), pero **reaparece agravado en la entrada**: `image-worker-mcp` acepta `base64Image` como parámetro
(`sharp.ts:22-26`, `upload.ts:14-56`), es decir **el modelo puede *enviar* el binario**, y eso cuesta lo mismo
que recibirlo. La regla se reformula: *el binario no cruza el canal MCP en ninguna dirección; ni de salida ni de
entrada.* Solo rutas.

**Regla 7 — caché idempotente por hash de contenido.** El principio se mantiene, pero **el cálculo cambia de
signo**. En texto, el hash del contenido era barato frente a la conversión. En binario, hashear un MP4 de 4 GB
cuesta segundos de I/O, y las claves de docling incluyen el digest del fichero. Y la conversión ya no es
determinista de la misma manera: ffmpeg con `-preset veryslow` y el mismo input puede producir bytes distintos
entre versiones. La regla se matiza: *clave por `(stat: tamaño + mtime + inode) + parámetros + versión del
motor`, con el hash de contenido como opción para ficheros por debajo de un umbral.* El precedente honesto es
que **ninguno de los cuatro repos tiene caché de ningún tipo**: hay que diseñarla desde cero.

**Regla 14 — motor caliente en un singleton, con descarga por inactividad.** El precedente de docling era un
pipeline de modelos que costaba 2 s reconstruir. **ffmpeg no es eso**: es un proceso externo por llamada
(`asyncio.create_subprocess_exec` en `convert.py:56`), sin estado que mantener caliente y sin VRAM que liberar.
La regla no aplica a la mitad binaria del catálogo de FileX. **Sí aplica, y con más fuerza, a lo que ffmpeg no
hace**: OCR, ASR (Whisper), superresolución — ahí sí hay modelos en GPU y ahí sí hay que mantener el singleton.
La matización: *el régimen de motor caliente es por motor, no por servidor.*

**Regla 11 — un formato de ruta.** Se confirma pero cambia de forma. En texto la incompatibilidad era de
**esquema** (`file://` frente a ruta del sistema). En binario los cuatro repos aceptan rutas del sistema sin
discusión y la incompatibilidad se traslada a **quién nombra la salida**: video-audio-mcp e image-worker-mcp
exigen que el modelo la invente; ffmpeg-mcp-lite la deriva de la entrada y la confina; y dos de sus ocho
herramientas admiten las dos cosas. **Un agente que aprende un servidor sigue fallando con el otro**, solo que
ahora en el parámetro de salida. Regla añadida para FileX: *el `output_path` es opcional; si falta, se deriva
determinísticamente dentro de la raíz de salida, y la respuesta siempre dice cuál se usó.*

### No aplican, o son nuevas

**No aplica: la tensión «documento pequeño → el asa pierde».** En texto estaba medida y era honesta: 32 tokens
de asa frente a 56 de contenido, y el asa tiene coste fijo. **En binario esa tensión no existe**, porque no hay
un tamaño de vídeo lo bastante pequeño para que devolverlo compense: el suelo de base64 de cualquier MP4
utilizable ya está tres órdenes de magnitud por encima del asa. **La única zona gris del carril binario es la
imagen**, y ahí sí hay una frontera real que calcular — y **nadie la ha calculado**: `image-worker-mcp` no tiene
ni un límite de tamaño en todo el repo (§C.3).

**No aplica: la regla del catálogo inflado como problema principal.** En texto, los 5 280 tokens de catálogo de
docling competían con una conversión de 36. En binario el catálogo sigue importando (3 610 estimados frente a
811) **pero deja de ser el coste dominante**, porque el coste dominante pasa a ser **el tiempo**: ninguno de los
cuatro repos tiene timeout, ninguno tiene progreso, y `Context` se importa sin usar (`server.py:2`). Un agente
no se queda sin contexto convirtiendo vídeo: **se queda colgado**. Es un modo de fallo que el carril documental
no tenía y que ninguna de las 16 reglas cubre.

**Reglas nuevas que solo existen en el caso binario:**

**B1. Toda conversión debe declarar un timeout y reportar progreso.** *Evidencia:* cero timeouts en los cuatro
repos (`grep timeout|wait_for|max_|limit` sobre `ffmpeg-mcp-lite/src/` → 0 resultados); `Context` de FastMCP
importado y nunca usado en `video-audio-mcp/server.py:2`; `fetch()` sin `AbortController` en
`image-worker-mcp/src/utils.ts:94-127`. Una recodificación H.265 puede durar horas y **el agente no tiene forma
de saber si el servidor está trabajando o muerto**. Como mínimo: timeout configurable con error accionable
(«excedió N s; reintenta con `preset=veryfast` o `scale` menor») y `ctx.report_progress()` sobre el `-progress`
de ffmpeg.

**B2. El asa binaria debe llevar las propiedades verificables del artefacto.** *Evidencia:* en texto, «convirtió»
y «convirtió bien» eran casi lo mismo. En binario no: un MP4 de 0 bytes, un MP4 sin pista de audio y un MP4
correcto son los tres «éxitos» indistinguibles con el contrato de A y B. Solo `compress.py:71-81` mira el
resultado. El asa de FileX debe llevar, medido **del fichero producido**, no de los parámetros pedidos:
`{ruta, bytes, formato_real, duración, resolución, códecs, warnings[]}`. Es la única forma de que el agente
pueda encadenar el siguiente paso sin llamar a `probe`.

**B3. Un canal de avisos codificado para el éxito parcial.** *Evidencia:* el `WarningCode` de kordoc
(`types.ts:249-277`, 17 códigos) resuelve en documental lo que en binario es **más frecuente**: una conversión
que perdió la pista de subtítulos, un contenedor que no admite el códec y forzó recodificación silenciosa
(`_run_ffmpeg_with_fallback` **hace exactamente eso** y lo comunica solo cambiando la palabra «primary» por
«fallback» en una frase, `server.py:336`/`:340`), un HEIC del que solo se leyó la primera imagen del burst
(`sharp.ts:110`). Sin códigos de aviso, el modelo no distingue una conversión limpia de una degradada.

**B4. La imagen es el único caso donde el contenido puede volver — y hay que ponerle un techo explícito.**
*Evidencia:* no hay precedente. `image-worker-mcp` es el único candidato y **no emite `ImageContent`**
(`grep type:'image'` → 0 en `src/`), devuelve base64 como texto plano con un prefijo `data:` que lo hace
inválido para el campo `data` de MCP (`utils.ts:63-65`), y **no tiene ningún límite de tamaño en todo el repo**.
FileX debe: emitir `ImageContent` de verdad, con un cap en bytes en `constants` (no en el criterio del modelo,
como el booleano `outputImage` de `sharp.ts:50`), y por encima del cap devolver el asa con dimensiones y
ofrecer un `thumbnail` explícito. Un thumbnail de 800×600 JPEG q80 ronda los 60 KB → ~80 KB de base64 → decenas
de miles de tokens: **incluso el caso «bueno» es caro**, así que el techo debe ser bajo y el default debe ser el
asa.
