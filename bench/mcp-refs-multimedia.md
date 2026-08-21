# MCP de multimedia: qué devuelve un servidor MCP tras convertir un fichero binario

**Agente F.** Medido el 2026-08-20 sobre Windows 10, 12 núcleos, Python 3.11.9, Node v22.23.2,
`ffmpeg` N-121159, ImageMagick 7.1.2 Q16-HDRI. Sin GPU.

Arnés: `bench/scripts/mcp_probe_bin.py` (no modificado). Datos crudos, specs, logs de `stderr` y
ficheros convertidos en `bench/salidas-mcp-refs/multimedia/`.

Todas las afirmaciones van marcadas **MEDIDO** o **PENDIENTE**.

---

## 0. La pregunta y la respuesta en tres líneas

Las reglas MCP de FileX («devolver asa, nunca contenido») salen de medir MCP **documentales**, donde
la salida es texto. Nunca se habían validado contra el caso **binario**. Se han sondeado los tres
MCP de multimedia de referencia.

> **Respuesta (MEDIDO):** ninguno de los tres devuelve el binario como `ImageContent` /
> `AudioContent` / `BlobResourceContents`. Los tres devuelven **texto con una ruta**. Pero
> `image-worker-mcp` **sí puede devolver la imagen entera**, y lo hace **como base64 dentro de un
> string JSON en un `TextContent`** — un patrón que la regla actual de FileX, escrita en términos de
> «contenido», **no prohíbe explícitamente y por tanto no cubre**. Con un solo booleano
> (`outputImage: true`) la misma conversión pasa de **71 a 6.218 tokens: ×87**.

La regla «nunca contenido» **se sostiene**, pero estaba mal redactada: hay que prohibir el binario
**en cualquier codificación, incluida base64 dentro de texto**, no solo en los tipos de contenido
binarios del protocolo. Detalle en §3 y §8.

---

## 1. Qué se instaló, dónde y cuánto ocupó

| Servidor | Entorno creado | Tamaño | Paquetes | Resultado |
|---|---|---:|---:|---|
| `video-audio-mcp` | `.venv-mcp-vam/` | **158 MB** | 78 | Arranca **MEDIDO** |
| `ffmpeg-mcp-lite` | `.venv-mcp-lite/` | **107 MB** | 42 | Arranca **tras fijar `mcp<2`** **MEDIDO** |
| `image-worker-mcp` | caché `npx` (`_npx/b831e9358f6afc5d`) | **64,5 MB** (6.991 ficheros) | v0.0.6 | Arranca **solo con credenciales S3 falsas** **MEDIDO** |

**Coste total de las tres integraciones: 330 MB.** El más barato es el de npm (64,5 MB, sin venv, sin
compilar nada: `npx -y @boomlinkai/image-worker-mcp` y funciona), pese a arrastrar `sharp` y
`libheif-js` nativos. Los dos venvs de Python pesan **4 veces más** que él.

No se tocó ningún venv preexistente (`.venv-ai`, `.venv-paddle`, `.venv-mcp-md`, `.venv-marker`).
Ningún fichero de `repos/`, `corpus/`, `analysis/` ni de la raíz fue modificado.

### 1.1 Fallo de integración nº 1 — `ffmpeg-mcp-lite` no arranca recién instalado (MEDIDO)

`repos/mcp-refs/ffmpeg-mcp-lite/pyproject.toml:28` declara la dependencia como:

```toml
dependencies = ["mcp>=1.0.0"]
```

Un `pip install` limpio resuelve hoy a **`mcp 2.0.0`**, y `mcp` 2.x **eliminó `mcp.server.fastmcp`**.
El servidor muere al importar, antes de atender nada:

```
File "…/ffmpeg-mcp-lite/src/ffmpeg_mcp_lite/server.py", line 3, in <module>
    from mcp.server.fastmcp import FastMCP
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Un límite inferior sin techo (`>=1.0.0`) sobre un paquete que ya ha roto compatibilidad mayor.
**El paquete tal y como está publicado no arranca.** Se resolvió con `pip install "mcp<2"` →
`mcp 1.29.0` (instalación en el venv, sin tocar el código del clon).

> **Lección para FileX (MEDIDO):** fijar techo mayor en las dependencias del SDK MCP
> (`mcp~=1.29`, no `mcp>=1.0`). Esto **confirma** lo que `bench/mcp-ergonomia.md:463` ya avisaba
> sobre el renombrado de API entre `mcp` 1.x y 2.x; aquí se ve el coste aguas abajo: un repo de
> terceros que deja de arrancar sin que nadie toque su código.

### 1.2 Fallo de integración nº 2 — `image-worker-mcp` exige S3 para redimensionar en local (MEDIDO)

`src/server.ts:18` construye el servicio de subida **en el constructor y sin condición**:

```ts
this.uploadService = UploadServiceFactory.create();
```

`src/services/factory.ts:10-20` valida entonces el esquema de S3 con Zod. Sin `S3_BUCKET` el
proceso **aborta antes de abrir el transporte stdio**:

```
McpError: MCP error -32602: S3 configuration validation failed: S3_BUCKET: Required
```

`resize_image` es 100 % local y offline (Sharp) y no tiene nada que ver con S3, pero **no se puede
usar sin configurar un almacenamiento en la nube**. Se sorteó con credenciales falsas
(`S3_BUCKET=filex-dummy-no-existe`, …): construir el cliente de S3 no hace ninguna llamada de red.

> **Lección para FileX (MEDIDO):** las capacidades opcionales se construyen **perezosamente**, en la
> primera llamada a la herramienta que las necesita, nunca en el arranque del servidor. Un fallo de
> configuración de una capacidad no usada no puede impedir el arranque de todas las demás.

### 1.3 Incompatibilidad de clientes, ya conocida y reconfirmada (MEDIDO)

`mcp 2.0.0` como **cliente** tampoco vale para el arnés: falla con `MCPError: Connection closed`.
Se usa **un único cliente sonda** (`.venv-mcp-vam`, `mcp 1.29.0`) contra los tres servidores; el
servidor de cada uno corre en su propio intérprete. Confirma la regla del proyecto: **un venv por
servidor**, y el cliente no tiene por qué compartir venv con el servidor (van por stdio, son
procesos distintos).

---

## 2. Tabla comparativa de catálogos (Fase 1, MEDIDO)

| Servidor | Herr. | `tokens_catalogo` | tok/herr. | Anotadas | `outputSchema` | Arranque en frío |
|---|---:|---:|---:|---:|---:|---:|
| **`video-audio-mcp`** | **27** | **7.964** | 295 | **0** | 27 | 1.202 ms |
| `ffmpeg-mcp-lite` | 8 | 2.322 | 290 | **0** | 8 | 6.689 ms (1.ª) / **817 ms** (en caliente) |
| `image-worker-mcp` | 2 | 1.177 | **589** | **0** | 0 | 2.620 ms |
| *`docling-mcp`* (ya medido) | *19* | *5.280* | *278* | *sí* | — | *~6.000 ms* |
| *`docling-mcp --conversion`* | *3* | *880* | *293* | *sí* | — | *1.800 ms* |
| *`markitdown-mcp`* (ya medido) | *1* | *79* | *79* | *0* | *0* | *3.413 ms* |

### 2.1 El techo del sector: 7.964 tokens

**`video-audio-mcp` cuesta 7.964 tokens de suelo fijo, un 51 % más que docling-mcp (5.280)** y
**×101 markitdown**. Es el catálogo más caro medido en todo el proyecto. Ese coste se paga en cada
petición, antes de llamar a nada.

Para dimensionarlo: 7.964 tokens son **~4 % de una ventana de 200 K** consumidos permanentemente por
un solo servidor que no ha hecho todavía ningún trabajo.

### 2.2 Hallazgo que matiza la regla nº 5 de FileX: el coste **no** es proporcional al nº de herramientas

El coste por herramienta va de **79 tokens** (`markitdown.convert_to_markdown`) a **875 tokens**
(`image-worker.resize_image`) — un factor **×11**. `resize_image`, **ella sola**, cuesta **casi lo
mismo que las 3 herramientas del grupo `conversion` de docling juntas** (875 vs 880), y **11 veces
más que el catálogo entero de markitdown**.

La causa es la **superficie de parámetros**, no el número de herramientas: `resize_image` declara
**25 parámetros, los 25 con descripción en lenguaje natural** (MEDIDO). `upload_image`, con 9
parámetros, cuesta 299 tokens. El coste sigue a los parámetros descritos, no a la herramienta.

> **Matiz (MEDIDO):** «pocas herramientas» es una métrica incompleta. Lo que se paga es
> **superficie de esquema total**. Una herramienta `convert()` de FileX con 20 parámetros
> documentados costaría más que las cuatro herramientas previstas con 4 parámetros cada una.
> El presupuesto debe fijarse en **tokens de catálogo**, no en número de herramientas.

### 2.3 Cero anotaciones en los tres (MEDIDO)

**Ninguno** de los tres servidores declara `readOnlyHint` ni `destructiveHint`. Ninguno.
Sumando lo ya medido: de los cinco MCP de conversión sondeados en el proyecto, **solo `docling-mcp`
anota**. Los 27 tools de `video-audio-mcp` escriben ficheros y sobrescriben sin avisar, y el cliente
no tiene forma protocolaria de saberlo.

Esto **confirma** la regla 2 de `analysis/00-mcp-patrones.md`, pero con una lectura incómoda: anotar
es una práctica **minoritaria** (1 de 5). Si FileX anota, será una ventaja diferencial real, no una
alineación con la norma.

`video-audio-mcp` y `ffmpeg-mcp-lite` **sí** declaran `outputSchema` en todas sus herramientas — pero
no por diseño: lo genera FastMCP automáticamente a partir del `-> str` de la firma. El esquema
resultante es, **comprobado uno a uno en los 35 y sin una sola excepción** (normalizando el `title`,
que solo repite el nombre de la herramienta):

```json
{"properties":{"result":{"title":"Result","type":"string"}},
 "required":["result"],"title":"…Output","type":"object"}
```

Es decir: *«devuelve una cadena»*. **No dice ni el formato de salida, ni la ruta, ni si hubo error.**
Es coste de catálogo sin información: un `outputSchema` presente no significa un contrato de salida.
FileX debe declarar el suyo **a mano**, con `{ruta_salida, formato, bytes, duración_ms, motor_usado}`
tipados, o no declararlo.

---

## 3. La pregunta central: qué devuelve tras convertir un binario (Fase 2, MEDIDO)

### 3.1 Tabla de resultados

`tokens_bin` = binario en tipos de contenido binarios del protocolo. `bytes_bin` = bytes
decodificados de esos tipos. Nótese que ambos son **0 en todas las filas**: el binario de
`image-worker` viaja **dentro del texto**, y por eso aparece en `tok_texto`.

| Servidor | Conversión | Patrón real | `tok_texto` | `tok_bin` | `bytes_bin` | ms | `isError` |
|---|---|---|---:|---:|---:|---:|---|
| **vam** | `health_check` | PROSA | 4 | 0 | 0 | 5 | false |
| **vam** | mp4 → mkv | **ASA** | **37** | 0 | 0 | 49 | false |
| **vam** | wav → flac | **ASA** | **37** | 0 | 0 | 79 | false |
| **vam** | wav → mp3 | **ASA** | **37** | 0 | 0 | 97 | false |
| **vam** | `tipico.mp4` (15,5 MB) → mp3 | **ASA** | **32** | 0 | 0 | 161 | false |
| **vam** | `trivial.mp4` → mp3 *(sin pista de audio)* | PROSA | **1.158** | 0 | 0 | 57 | **false ✗** |
| **vam** | mp4 → gif | *(no retorna: §4.1)* | — | — | — | **∞** | — |
| **lite** | `ffmpeg_get_info` | ASA/JSON | 153 | 0 | 0 | 54 | false |
| **lite** | mp4 → gif | **ASA** | **33** | 0 | 0 | 479 | false |
| **lite** | `tipico.mp4` (15,5 MB) → mp3 | **ASA** | **34** | 0 | 0 | 282 | false |
| **lite** | wav → flac | **ASA** | **34** | 0 | 0 | 109 | false |
| **lite** | mp4 → webm | **TIMEOUT** *(§4.2)* | 4 | 0 | 0 | **900.001** | *n/a* |
| **lite** | mp4 → mp3 *(sin pista de audio)* | ASA | 1.173 | 0 | 0 | 59 | true ✓ |
| **lite** | `ffmpeg_extract_audio` *(sin pista)* | ASA | 1.171 | 0 | 0 | 56 | true ✓ |
| **img** | jpg → png `outputImage=false` | **ASA** | **71** | 0 | 0 | 88 | false |
| **img** | jpg → webp `outputImage=false` | **ASA** | **72** | 0 | 0 | 65 | false |
| **img** | png 316 B → webp `outputImage=false` | **ASA** | **72** | 0 | 0 | 37 | false |
| **img** | png 316 B → webp **`outputImage=true`** | **CONTENIDO ENCUBIERTO** | **1.213** | 0 | 0 | 35 | false |
| **img** | jpg → webp **`outputImage=true`** | **CONTENIDO ENCUBIERTO** | **3.218** | 0 | 0 | 60 | false |
| **img** | jpg → png **`outputImage=true`** | **CONTENIDO ENCUBIERTO** | **6.218** | 0 | 0 | 81 | false |
| **img** | png → webp, **sin `outputPath`** | **CONTENIDO ENCUBIERTO** | **1.186** | 0 | 0 | 42 | false |

### 3.2 Veredicto 1 — el patrón por defecto es el asa, y es barato

**MEDIDO:** el asa cuesta entre **32 y 72 tokens**, y **no depende del tamaño del fichero**.
`tipico.mp4` (15,5 MB) devuelve **32 tokens** en vam y **34** en lite; `trivial.mp4` (552 KB)
devuelve exactamente lo mismo. **El coste del asa es constante e independiente de la entrada.**
Eso es exactamente lo que FileX quiere y ya había supuesto — ahora está medido en el caso binario.

Rango completo del asa en las 11 conversiones que la usaron: **32-72 tokens**, con una entrada que
va de **316 bytes a 15,5 MB** — cinco órdenes de magnitud de variación en la entrada, **×2,25 en el
coste de la respuesta**, y esa variación se debe solo a la longitud de la ruta y de la frase de
éxito, no al fichero. Es la propiedad que hace viable el diseño de FileX.

Es coherente con lo que decía `analysis/00-mcp-patrones.md`: «para salidas binarias el patrón
[de devolver contenido] sencillamente no existe». **Casi.** Ver el veredicto siguiente.

### 3.3 Veredicto 2 — el caso decisivo: `image-worker-mcp` sí devuelve la imagen, encubierta

`image-worker-mcp` tiene un parámetro que **ningún MCP documental tenía**
(`src/tools/sharp.ts:56`):

```ts
outputImage: z.boolean().optional().default(false)
  .describe("Whether to include the base64-encoded image in the output response"),
```

Y en `src/tools/sharp.ts:262-283` la respuesta se construye así:

```ts
return { content: [{ type: 'text', text: JSON.stringify({
    ...(this.args.outputImage ? { image: outputBase64 } : {}),
    format, width, height, size, savedTo, source }, null, 2) }] };
```

**El binario no viaja como `ImageContent`. Viaja como base64 metido dentro de un string JSON dentro
de un `TextContent`.** Consecuencias medidas:

| Entrada | Fichero de salida | `outputImage=false` | `outputImage=true` | Multiplicador |
|---|---:|---:|---:|---:|
| `trivial.png` (316 B) | 1.214 B | 72 tok | **1.213 tok** | **×16,8** |
| `tipico.jpg` (88 KB) → webp | 3.564 B | 72 tok | **3.218 tok** | **×44,7** |
| `tipico.jpg` (88 KB) → png | 7.008 B | 71 tok | **6.218 tok** | **×87,6** |

**Relación medida: 0,887 - 0,999 tokens por byte de salida, media 0,930** sobre las tres muestras
(6.218/7.008 = 0,887 · 3.218/3.564 = 0,903 · 1.213/1.214 = 0,999). Es decir, la regla mental es
directa y no hace falta afinarla más: **cada byte del fichero convertido cuesta aproximadamente un
token.** El base64 expande ×1,33 y el tokenizador saca ~1,4 caracteres por token sobre datos
aleatorios; el producto ronda 1.

Esta es la cifra que faltaba en el proyecto. Con ella se puede responder la pregunta «¿hay un umbral
N por debajo del cual sí conviene devolver el contenido?»:

Extrapolando a 0,93 tok/byte sobre una ventana de 200 K:

| Tamaño del binario | Coste si se inyecta | % de una ventana de 200 K | ¿Viable? |
|---|---:|---:|---|
| 1 KB (icono) | ~950 tok | 0,5 % | Caro pero posible |
| 10 KB (PNG pequeño) | ~9.500 tok | 4,8 % | Una **sola** imagen se come 1/20 del contexto |
| 100 KB (JPEG normal) | ~95.000 tok | **48 %** | **Inviable** |
| 1 MB | ~950.000 tok | **475 %** | **Imposible** |
| 15,5 MB (`tipico.mp4`) | ~14.400.000 tok | **7.200 %** | **×72 la ventana entera** |

> **El MP4 convertido no cabe en el contexto ni queriendo, como se sospechaba — pero tampoco cabe
> un JPEG corriente.** El umbral en el que «devolver contenido» deja de ser absurdo está en el orden
> de **1-2 KB**, es decir, ficheros que no son imágenes útiles sino iconos.

### 3.4 Un patrón nuevo que el arnés no sabía nombrar: **CONTENIDO ENCUBIERTO**

El arnés clasificó estas respuestas como `PROSA` y `ASA`, **no** como `CONTENIDO`. No es un fallo
del arnés: su detector de binario busca `ImageContent`/`AudioContent`/`blob`, que es lo que dice el
protocolo. Aquí el binario está **dentro del texto**, así que:

- `tokens_binario_si_se_inyecta` = **0** (correcto según el protocolo)
- `bytes_binario` = **0** (correcto según el protocolo)
- `tokens_texto` = **6.218** ← **aquí está el coste real, y el arnés sí lo contó bien**

La medida de tokens es correcta; la **etiqueta** de patrón es engañosa. Peor aún: el caso
`jpg_a_png_CONTENIDO` salió clasificado como **ASA** porque el JSON incluye `savedTo` con una ruta
de Windows, y la heurística de asas busca `":\\"`. **Una respuesta de 6.218 tokens con una imagen
entera dentro se etiquetó como el patrón bueno.**

> **Consecuencia directa para FileX (MEDIDO):** un revisor —humano o automático— que audite un MCP
> buscando `ImageContent` **no detecta este antipatrón**. La regla de FileX debe redactarse sobre
> **tokens de respuesta**, que es lo observable y lo que se paga, no sobre tipos de contenido del
> protocolo. Véase §8.

### 3.5 Duplicación entre `content` y `structuredContent`

**MEDIDO:** ninguno de los tres devuelve `structuredContent`. Los tres pagan una sola vez.
`video-audio-mcp` y `ffmpeg-mcp-lite` declaran `outputSchema` autogenerado (`{"type":"string"}`)
pero no emiten el campo estructurado correspondiente. **No hay duplicación en ningún caso.**

---

## 4. Dos fallos operativos que se llevaron por delante las mediciones

### 4.1 `video-audio-mcp` **bloquea la sesión MCP** en las conversiones que reencodifican por la vía `ffmpeg-python` (MEDIDO)

Es el hallazgo más grave del informe y no estaba buscado: apareció al intentar medir mp4 → gif con
`convert_video_format`, una de las **9** herramientas que delegan en `_run_ffmpeg_with_fallback`.

**Cadena causal, cada eslabón verificado:**

1. `server.py:332-348`, `_run_ffmpeg_with_fallback()`: intenta primero `-c:v copy -c:a copy`, y si
   ffmpeg falla reintenta reencodificando **a la misma ruta de salida**. Ambos intentos van por
   `ffmpeg.input(…).output(…).run(…)`, sin `.overwrite_output()`.
2. El intento primario **ya ha creado el fichero de salida** (0 bytes) antes de fallar.
   *Verificado:* `ffmpeg -i trivial.mp4 -c:v copy -c:a copy -f gif t.gif` →
   `gif muxer supports only codec gif for type video`, y deja `t.gif` de **0 bytes**.
3. **La vía `ffmpeg-python` nunca desactiva la interactividad.** `server.py` invoca ffmpeg por **dos
   vías distintas**, y hay que separarlas (MEDIDO, recuento por herramienta):

   | Vía | Invocaciones | Herramientas | ¿Desactiva el prompt? |
   |---|---:|---:|---|
   | `ffmpeg.input(…).output(…).run()` (ffmpeg-python) | **32** | **24 en exclusiva** + 2 mixtas | **No: `overwrite_output()` = 0 usos en todo el fichero** |
   | `subprocess.run(['ffmpeg', …])` | **7** | solo 2 (`concatenate_videos`, `add_b_roll`) | **Sí: los 7 `-y` literales, uno por invocación** (`:898, :915, :956, :1001, :1022, :1434, :1547`) |

   La correspondencia es exacta: **7 llamadas por `subprocess`, 7 `-y`; 32 invocaciones por
   ffmpeg-python, 0 `overwrite_output()`.** *(Nota metodológica: el contador de invocaciones es
   `.run(`, no `ffmpeg.input(` — este último aparece 28 veces pero también como entrada de un grafo
   de filtros, así que no sirve para contar ejecuciones.)*

   De las 27 herramientas: 1 no toca ffmpeg (`health_check`), **24 usan exclusivamente
   ffmpeg-python** — 15 en su propio cuerpo y 9 delegando en `_run_ffmpeg_with_fallback`
   (`:362, :383, :397, :411, :425, :439, :453, :467, :481`) — y **2 usan ambas vías**, pasando `-y`
   *solo* en su rama de `subprocess`.

   > El matiz **refuerza** la conclusión en vez de debilitarla: **el mismo fichero sabe pasar `-y` en
   > una vía y se le olvida en la otra**. Si no se puede confiar en que cada punto de invocación
   > recuerde desactivar la interactividad dentro de un único fichero de 1.600 líneas, el problema no
   > se arregla con disciplina de argumentos: hay que cerrarlo **en el nivel del proceso**
   > (`stdin=DEVNULL`). Véase §9.5.
4. `ffmpeg-python` (`_run.py`) hace `stdin_stream = subprocess.PIPE if pipe_stdin else None`, y
   `.run()` usa `pipe_stdin=False`. **`stdin=None` significa heredado**: ffmpeg hereda el `stdin`
   del servidor MCP, que **es la tubería JSON-RPC del cliente**.
5. El reintento encuentra el fichero ya existente, pregunta `File 'X' already exists. Overwrite?
   [y/N]` y **se queda leyendo la tubería del protocolo MCP**, que nunca le va a contestar.

**Reproducción controlada** (`bench/salidas-mcp-refs/multimedia/repro/`):

| Caso | Resultado |
|---|---|
| `-f gif` **con `-y`**, stdin=tubería | termina en **1,4 s**, salida de 2.290.244 B |
| `-f gif` **sin `-y`**, stdin=tubería abierta y muda | **bloqueado >45 s** → deadlock |

**Reproducción a través del protocolo MCP** (`deadlock_vam.spec.json` + `deadlock_vam.stderr.log`):
la llamada no retorna; el timeout de 90 s del cliente salta, la sesión muere con
`anyio.BrokenResourceError`, y en disco queda `vam_dead.gif` de **0 bytes**.

**La prueba más limpia es que no hay fichero de resultados.** El arnés escribe su JSON al cerrar la
sesión, y aquí nunca llegó a cerrarla: **`deadlock_vam.json` no existe**. El `stderr` del servidor
termina exactamente así, y no vuelve a registrar nada más:

```
[21:36:41] INFO  Processing request of type  ListToolsRequest
           INFO  Processing request of type  ListPromptsRequest
           INFO  Processing request of type  ListResourcesRequest
           INFO  Processing request of type  CallToolRequest      <- entra y no sale nunca
```

> **Impacto, acotado:** «convertir a un formato que no admite copia de códecs» es *la petición de
> conversión más común que existe*, y en `video-audio-mcp` **cuelga el servidor y mata la sesión**.
> **Alcance verificado:** el mecanismo afecta a las herramientas que llegan a ffmpeg por la vía
> `ffmpeg-python` sin `overwrite_output()` — **24 de 27 en exclusiva**, más las dos mixtas en su
> rama de ffmpeg-python. Se reprodujo end-to-end en **una** de ellas (`convert_video_format`).
>
> **PENDIENTE:** no se ha reproducido el bloqueo en las otras 23; el mecanismo es común (mismo
> patrón de invocación, mismo `stdin` heredado, misma ausencia de `overwrite_output()`), pero solo
> disparan el prompt las que **escriben sobre una ruta que ya existe** — garantizado en las 9 del
> helper por su reintento, y dependiente del estado del disco en las demás.
>
> **Tres lecciones para FileX (MEDIDO):**
> 1. **`stdin` de todo subproceso a `DEVNULL`, siempre.** Un hijo que hereda el stdin del servidor
>    MCP puede bloquearse contra el protocolo o, peor, **comerse bytes del protocolo**.
> 2. **`-y` / `-nostdin` explícitos.** Nunca dejar a un subproceso la posibilidad de preguntar.
> 3. **Timeout del lado del servidor**, no solo del cliente. Aquí el timeout del cliente no salvó la
>    sesión: la rompió.

### 4.2 `ffmpeg-mcp-lite`: el «éxito huérfano» — la conversión sale bien y el modelo nunca se entera (MEDIDO)

Medición limpia, ejecución única, sin sondas solapadas:

`ffmpeg_convert(trivial.mp4, output_format="webm")` sobre un clip de **5 s a 640×480**
**no retornó en 900 s**. El arnés abortó exactamente en `900.000,8 ms` con `TimeoutError`, y el
modelo recibió eso: un timeout, 4 tokens, sin `isError` siquiera (`ok=False`, `isError=None`).

**Y sin embargo la conversión salió bien.** Poco después del abandono, ffmpeg terminó y escribió el
fichero. Verificado en disco:

```
trivial_converted.webm   559.046 B   EBML 1a 45 df a3   vp9  640x480  5,000 s
```

Un WebM **perfectamente válido**, con la geometría y la duración exactas del original.

> **El resultado existía, era correcto, y el modelo se quedó con un `TimeoutError`.** Un agente en
> esta situación reintentaría — y volvería a esperar 15 minutos para reproducir un fichero que ya
> estaba en disco. Es un modo de fallo peor que el error limpio: **desperdicia el trabajo ya hecho y
> lo repite.**

Dos causas, ambas verificadas:

1. **El códec por defecto es una trampa.** `tools/convert.py:52` solo añade `-c:v` si el modelo lo
   pide; si no, ffmpeg elige por la extensión y para `.webm` usa **VP9 en un solo hilo**. Mismo clip,
   mismo servidor: **GIF 0,48 s** frente a **WebM >900 s**. Un factor **>1.800**.
2. **No hay limpieza del árbol de procesos.** `taskkill /F /T` lo mostró literalmente —
   `el proceso con PID 26900 (proceso secundario de PID 34680)`—: al morir el cliente, el servidor
   `ffmpeg_mcp_lite` termina pero **su hijo `ffmpeg` sobrevive**. Se observó uno codificando VP9
   **13 minutos después** de que su servidor hubiera desaparecido, quemando CPU sin dueño.

> **Tres lecciones para FileX (MEDIDO):**
> 1. **Fijar el perfil de códec explícitamente.** `webm` no puede resolverse dejando elegir a
>    ffmpeg: hay que poner `-c:v libvpx-vp9 -row-mt 1 -cpu-used 4` (o VP8, o AV1 con `svt-av1`) y
>    **documentar el perfil**. Un valor por defecto 1.800 veces más lento que la alternativa no es un
>    valor por defecto, es una trampa.
> 2. **Las conversiones largas necesitan un asa asíncrona**, no una llamada bloqueante: devolver un
>    identificador de trabajo y que el modelo pregunte por su estado. Con el patrón bloqueante,
>    cualquier conversión que exceda el timeout del cliente **tira a la basura trabajo ya terminado**.
> 3. **Matar el árbol de procesos**, no el proceso.

---

## 5. Análisis de solapamiento de las 27 herramientas (Fase 3)

**Es un análisis estructural, no conductual.** No se ha ejecutado ningún experimento con un LLM
eligiendo herramientas; se comparan firmas, nombres y descripciones. **PENDIENTE:** la medida
conductual (dar la misma petición ambigua a un modelo con este catálogo y contar aciertos).

### 5.1 Subsunción estricta: el 39,7 % del catálogo es redundante (MEDIDO)

`convert_audio_properties(input, output, target_format, bitrate, sample_rate, channels)`
**contiene por completo** a estas 4:

| Herramienta subsumida | tok |
|---|---:|
| `convert_audio_format` | 234 |
| `set_audio_bitrate` | 237 |
| `set_audio_sample_rate` | 238 |
| `set_audio_channels` | 237 |
| **subtotal** | **946** |

`convert_video_properties(input, output, target_format, resolution, video_codec, video_bitrate,
frame_rate, audio_codec, audio_bitrate, audio_sample_rate, audio_channels)` **contiene por completo**
a estas 9:

| Herramienta subsumida | tok |
|---|---:|
| `convert_video_format` | 240 |
| `set_video_resolution` | 243 |
| `set_video_codec` | 244 |
| `set_video_bitrate` | 246 |
| `set_video_frame_rate` | 242 |
| `set_video_audio_track_codec` | 245 |
| `set_video_audio_track_bitrate` | 253 |
| `set_video_audio_track_sample_rate` | 257 |
| `set_video_audio_track_channels` | 247 |
| **subtotal** | **2.217** |

**Total estrictamente redundante: 13 herramientas / 3.163 tokens = 39,7 % del catálogo.**
Un catálogo equivalente en capacidad cabría en **4.801 tokens y 14 herramientas** sin perder
absolutamente nada. **MEDIDO.**

Cada una de esas 13 es un caso particular de la general con todos los demás parámetros a `None`.
No añaden capacidad: añaden **ambigüedad y coste**.

### 5.2 Ambigüedades de nombre que un modelo confundiría

Petición típica → herramientas que compiten (**análisis estructural**):

| Petición del usuario | Candidatas plausibles | Correcta | Por qué es ambiguo |
|---|---|---|---|
| «pasa este mp4 a mp3» | `extract_audio_from_video`, `convert_audio_format`, `convert_audio_properties`, `convert_video_properties(target_format='mp3')` | `extract_audio_from_video` | 3 de las 4 aceptan un `target_format='mp3'`; solo los nombres de parámetro (`input_audio_path` vs `video_path`) desambiguan, y no lo dicen las descripciones |
| «baja la resolución» | `set_video_resolution`, `convert_video_properties`, `change_aspect_ratio` | cualquiera | `change_aspect_ratio` también reescala, con `resize_mode='pad'\|'crop'` |
| «cambia el bitrate del audio del vídeo» | `set_audio_bitrate`, `set_video_audio_track_bitrate`, `convert_video_properties` | `set_video_audio_track_bitrate` | `set_audio_bitrate` **parece** la correcta y **no lo es** (opera sobre ficheros de audio, no sobre la pista de un vídeo) |
| «junta estos clips con un fundido» | `concatenate_videos(transition_effect=…)`, `add_basic_transitions` | `concatenate_videos` | ambas hacen transiciones; `add_basic_transitions` solo al principio/final de **un** vídeo |
| «mete este clip encima del vídeo» | `add_b_roll`, `add_image_overlay`, `concatenate_videos` | `add_b_roll` | los tres «insertan medios en un vídeo» |

El par **`set_audio_bitrate` / `set_video_audio_track_bitrate`** es el peor: nombres casi idénticos,
descripciones casi idénticas, y la equivocación **no da error** — produce un fichero incorrecto.

### 5.3 Tres herramientas cuya descripción apunta a documentos que el modelo no puede ver (MEDIDO)

| Herramienta | Descripción literal |
|---|---|
| `convert_video_properties` | «… **Args listed in PRD.** Returns: A status message…» |
| `change_aspect_ratio` | «… **Args listed in PRD.** Returns: A status message…» |
| `add_b_roll` | «Inserts B-roll clips into a main video as overlays. **Args listed in previous messages (docstring unchanged for brevity here)**» |

`convert_video_properties` es **la herramienta más capaz del servidor** (11 parámetros, la que
subsume a otras 9) y su documentación para el modelo es *«los argumentos están en el PRD»*.

El caso de `add_b_roll` es aún peor, porque el esquema tampoco rescata nada. Este es el
`inputSchema` real de su parámetro **obligatorio** (MEDIDO, `cat_vam.json`):

```json
"broll_clips": { "items": { "additionalProperties": true, "type": "object" },
                 "title": "Broll Clips", "type": "array" }
```

Un array de objetos arbitrarios, sin una sola clave declarada, cuya descripción remite a
«mensajes anteriores». **Entre la descripción y el esquema, la información disponible para construir
la llamada es cero.** El modelo no puede acertar; solo adivinar.

> **Lección para FileX (MEDIDO):** la descripción de una herramienta MCP es **interfaz de programa**,
> no comentario. Debe ser autosuficiente. Una prueba automática debería rechazar cualquier
> descripción que contenga «see», «PRD», «above», «previous», «TODO» o «for brevity».

### 5.4 Agrupación por dominio

| Dominio | n | Herramientas |
|---|---:|---|
| Diagnóstico | 1 | `health_check` |
| Conversión de audio | 5 | `convert_audio_properties` + **4 subsumidas** |
| Conversión de vídeo | 6 | `convert_video_properties` + **5 subsumidas** |
| Pista de audio de un vídeo | 4 | **las 4 subsumidas** `set_video_audio_track_*` |
| Extracción | 1 | `extract_audio_from_video` |
| Recorte / tiempo | 3 | `trim_video`, `change_video_speed`, `remove_silence` |
| Composición | 5 | `add_subtitles`, `add_text_overlay`, `add_image_overlay`, `add_b_roll`, `concatenate_videos` |
| Geometría | 1 | `change_aspect_ratio` |
| Transiciones | 1 | `add_basic_transitions` |

**Los tres dominios de conversión (15 herramientas, 55 % del catálogo) colapsan en 2.**

---

## 6. Verificación de las salidas en disco (bytes mágicos + `ffprobe`/`identify`)

Script: `bench/salidas-mcp-refs/multimedia/verificar_salidas.py`. Resultado completo en
`verificacion.json`.

| Fichero | Bytes | Mágico | Sonda | Veredicto |
|---|---:|---|---|---|
| `vam_trivial.mkv` | 552.079 | matroska | matroska,webm | **OK** |
| `vam_trivial.flac` | 104.318 | flac | flac | **OK** |
| `vam_wav.mp3` | 64.591 | mp3 | mp3 | **OK** |
| `vam_tipico.mp3` | 160.825 | mp3 | mp3 | **OK** |
| `img_tipico.png` / `_c.png` | 7.008 | png | png | **OK** (formato) |
| `img_tipico.webp` / `_c.webp` | 3.564 | webp | webp | **OK** (formato) |
| `img_trivial.webp` / `_c.webp` | 1.214 | webp | webp | **OK** (formato) |
| `lite/trivial_converted.gif` | 2.290.244 | gif | gif | **OK** |
| `lite/tipico_converted.mp3` | 160.825 | mp3 | mp3 | **OK** |
| `lite/trivial_converted.flac` | 104.318 | flac | flac | **OK** |
| `lite/trivial_converted.webm` | 559.046 | matroska | matroska,webm | **OK**, pero **llegó tarde** (§4.2) |
| **`vam_dead.gif`** | **0** | DESCONOCIDO | ERROR | **NO ABRE** ← residuo del deadlock §4.1 |

**Recuento final: 14 salidas correctas, 1 ilegible** (el fichero de 0 bytes que deja el deadlock de
`video-audio-mcp`).

### 6.0 Contraste directo de fidelidad (MEDIDO)

La misma pregunta —«¿lo que hay en disco es lo que se pidió?»— separa limpiamente a los servidores:

| Servidor | Entrada | Salida en disco | ¿Conserva geometría y duración? |
|---|---|---|---|
| `ffmpeg-mcp-lite` | `trivial.mp4` 640×480, 5,000 s | GIF **640×480, 5,000 s**, 120 fotogramas | **Sí, exacto** |
| `video-audio-mcp` | `trivial.wav` 8,000 s | FLAC **8,000 s**, MD5 idéntico a la referencia | **Sí, exacto** |
| `image-worker-mcp` | `tipico.jpg` **1920×1080** | PNG **800×600** (contenido 800×450 + barras) | **No** (§6.2) |

### 6.1 ¿Mintió alguno sobre el **formato**? No.

**MEDIDO:** ningún servidor entregó un fichero con extensión falsa. No se reprodujo el caso ConvertX
(PNG con extensión `.avif` y estado «Done»). Los bytes mágicos coinciden con la extensión en las
**14** salidas que se escribieron correctamente.

Verificación adicional de **contenido**, no solo de formato:

| Salida | Duración origen | Duración salida | Veredicto |
|---|---|---|---|
| `vam_tipico.mp3` | 20,000 s | 20,016 s | correcto (relleno de trama MP3) |
| `vam_trivial.flac` | 8,000 s | 8,000 s | correcto |
| `vam_wav.mp3` | 8,000 s | 8,000 s | correcto |
| `vam_trivial.mkv` | 5,000 s | 5,000 s | correcto |

`vam_trivial.flac` y `vam_wav.mp3` resultan ser **byte a byte idénticos** (mismo MD5) a
`corpus/audio/tipico.flac` y `corpus/audio/tipico.mp3`. No es un error: el corpus se generó desde
`trivial.wav` con los mismos parámetros, así que la reproducción exacta **confirma** que la
conversión es correcta y determinista.

### 6.2 Sí mintió uno, pero sobre otra cosa: `image-worker-mcp` redimensiona sin que se lo pidan (MEDIDO)

Se pidió **solo un cambio de formato** (`format: 'png'`). Se recibió, sin aviso alguno:

| Entrada | Dimensión original | Lienzo entregado | **Contenido real** | Qué pasó de verdad |
|---|---|---|---|---|
| `tipico.jpg` | **1920×1080** | 800×600 | **800×450** | reducido ×2,4 **+ barras negras** de 75 px arriba y abajo |
| `tipico.jpg` → webp | 1920×1080 | 800×600 | 800×472 | ídem |
| `trivial.png` | **64×64** | 800×600 | **624×600** | **ampliado ×9,75** + barras laterales de 96 px |

La respuesta al modelo dice `"width": 800, "height": 600`. Eso es **el lienzo**, no la imagen: el
contenido real ocupa 800×450 y el resto son **barras negras añadidas**. Verificado con
`magick identify -format '%wx%h'` frente a `magick … -trim`:
`img_tipico.png PNG 800x450 800x600+0+75` — 450 de alto, desplazado 75 px.

Causa: `src/tools/sharp.ts:157-170`. Si no se pasan `width` ni `height`, **no** se omite el
redimensionado; se aplican `DEFAULT_WIDTH=800`, `DEFAULT_HEIGHT=600` y `fit='contain'`
(`src/constants.ts:4-6`).

> Un fichero de **316 bytes y 64×64** se devolvió como **1.214 bytes y 800×600**, con el 40 % de la
> superficie en barras negras, presentado como una conversión de formato correcta. La verificación
> de FileX **no habría detectado esto** comprobando solo bytes mágicos: el WebP es un WebP válido.
>
> **Lección para FileX (MEDIDO):** la verificación de salida debe comparar **dimensiones y duración
> contra la entrada**, no solo validar el contenedor. Y ninguna transformación no solicitada puede
> aplicarse por defecto: si no se piden dimensiones, **no se redimensiona**.

---

## 7. Tabla de errores (Fase 4, MEDIDO)

Contraste con los antipatrones ya documentados: `docling-mcp` filtró `stderr` crudo (respondió
`pip install openai-whisper` a un agente) y `markitdown-mcp` devolvió cadena vacía con
`isError: false` ante un PDF escaneado.

| Servidor | Entrada mala | `isError` | tok | Mensaje que ve el modelo | Veredicto |
|---|---|---|---:|---|---|
| **vam** | fichero inexistente | **false ✗** | **884** | `Error converting audio format: ffmpeg version N-121159… configuration: --prefix=/ffbuild/prefix --pkg-config-flags…` | **PÉSIMO** |
| **vam** | formato imposible (`xyzzy`) | **false ✗** | **1.075** | ídem, banner completo de ffmpeg | **PÉSIMO** |
| **vam** | fichero truncado | **false ✗** | **929** | ídem | **PÉSIMO** |
| **vam** | mp4 sin pista de audio | **false ✗** | **1.158** | ídem | **PÉSIMO** |
| **lite** | fichero inexistente | **true ✓** | **30** | `Error executing tool ffmpeg_convert: File not found: D:/…/NO_EXISTE_12345.mp4` | **BUENO** |
| **lite** | formato imposible (`xyzzy`) | true ✓ | **1.228** | `…ffmpeg convert failed: ffmpeg version N-121159… configuration: --prefix=…` | **MALO** (fuga de stderr) |
| **lite** | fichero truncado | true ✓ | **938** | ídem | **MALO** (fuga de stderr) |
| **img** | fichero inexistente | true ✓ | **67** | `MCP error -32602: Failed to read image from path: …. ENOENT: no such file or directory` | **BUENO** |
| **img** | formato imposible (`xyzzy`) | *n/a: error de protocolo* | **108** | `Invalid enum value. Expected 'jpeg' \| 'png' \| 'webp' \| 'avif', received 'xyzzy'` | **EXCELENTE** |
| **img** | PNG truncado | true ✓ | **17** | `Error processing image: Input buffer has corrupt header: pngload_buffer: end of stream` | **EXCELENTE** |

### 7.1 `video-audio-mcp` combina los dos antipatrones a la vez

Es el peor resultado del proyecto en manejo de errores, y es **peor que cualquiera de los dos
antipatrones conocidos por separado**, porque los junta:

- **Como markitdown:** devuelve `isError: false` en un fallo, y no es un descuido de una herramienta
  suelta sino el patrón del fichero entero. **Recuento exhaustivo por herramienta (MEDIDO):** de las
  27, **17 devuelven el error como cadena en el cuerpo** (`except … : return f"Error …"`,
  `server.py:33-41` y equivalentes; entre 3 y 18 puntos de retorno de error cada una), **9 lo hacen
  a través de `_run_ffmpeg_with_fallback`** (`:342-348`, que también devuelve la cadena), y
  `health_check` no tiene camino de error. **Total: 26 de 26 herramientas con posibilidad de fallo
  devuelven el error como valor normal, y `raise` no aparece ni una sola vez en las 27.**
  **Una función que devuelve el error como valor de retorno normal nunca puede producir
  `isError: true` en FastMCP.**
- **Como docling:** el texto que devuelve es **el `stderr` crudo de ffmpeg**, 884-1.158 tokens, de
  los cuales ~800 son el banner de compilación (`--enable-libaom --enable-libaribb24 …`).

El modelo recibe **~1.000 tokens de basura marcados como éxito**. La causa real («el fichero no
tiene pista de audio», «formato desconocido») está sepultada al final del volcado.

**Cuánta de esa fuga es desperdicio, medido** (`repro/stderr_ffmpeg_tipico.txt`): el `stderr`
completo de un ffmpeg que rechaza un formato son **1.037 tokens en 20 líneas**. Las líneas que
contienen la causa son **tres, 73 tokens**:

```
[AVFormatContext @ …] Requested output format 'xyzzy' is not known.      <- 27 tokens
[out#0 @ …] Error initializing the muxer for …: Invalid argument         <- 39 tokens
Error opening output files: Invalid argument                             <-  7 tokens
```

> **El 93 % del volcado es desperdicio (964 de 1.037 tokens).** Filtrar el `stderr` de ffmpeg a las
> líneas con `Unknown` / `Invalid` / `not found` / `Requested` reduce el coste **×14** sin perder
> nada útil. Es una función de diez líneas y es obligatoria en FileX.

### 7.2 `image-worker-mcp` da la mejor lección del informe: el error accionable

```
Invalid enum value. Expected 'jpeg' | 'png' | 'webp' | 'avif', received 'xyzzy'
```

**108 tokens que contienen la lista completa de valores válidos.** El modelo puede corregirse solo,
en un turno, sin más llamadas. Sale gratis: es Zod validando el esquema antes de ejecutar nada
(1,8 ms). Compárese con los **1.228 tokens** de lite para el mismo error, que **no** dicen qué
formatos se aceptan.

Matiz honesto: llega como **error de protocolo JSON-RPC** (`-32602`), no como resultado de
herramienta, así que el arnés lo ve como excepción y `isError` queda a `None`. Para FileX es
preferible **el mismo mensaje** pero como resultado con `isError: true`, que es más fácil de tratar
para el cliente.

**Confirmación cruzada, independiente:** `bench/mcp-ergonomia.md` §4.1 ya había señalado como
*«modélico»* el único buen error de markitdown, por exactamente la misma razón —
`Unsupported URI scheme: D. Supported schemes are: file:, data:, http:, https:` (26 tokens). Dos
servidores sin ninguna relación, dos lenguajes distintos, y el mismo rasgo:

> **Un buen error de MCP no describe el fallo: enumera las salidas válidas.** Es la propiedad que
> permite al modelo corregirse en un solo turno. Medido dos veces, en 26 y en 108 tokens. Es barata
> y es la que más rendimiento da por token gastado.

---

## 8. Qué se lleva FileX de cada repo, pieza por pieza

| Pieza | Fichero:línea | Qué es | Veredicto |
|---|---|---|---|
| Fixtures sintéticas con ffmpeg | `ffmpeg-mcp-lite/tests/conftest.py:17-61` | genera vídeo y audio de prueba con `lavfi testsrc`/`sine`; **cero binarios en el repo** | **COPIAR TAL CUAL** |
| `pytest.skip` si falta ffmpeg | `ffmpeg-mcp-lite/tests/conftest.py:37-38` | la suite se salta, no falla, si el entorno no tiene ffmpeg | **COPIAR TAL CUAL** |
| Parcheo del `config` vivo | `ffmpeg-mcp-lite/tests/test_frames.py:10-20` | `monkeypatch.setattr(frames_mod.config, …)` con comentario explicando por qué reasignar `config.config` no basta | **COPIAR TAL CUAL** |
| Troceado de `tools/` por dominio | `ffmpeg-mcp-lite/src/ffmpeg_mcp_lite/tools/` | un fichero por dominio, un `test_*.py` por fichero | **COPIAR TAL CUAL** |
| Registro centralizado | `ffmpeg-mcp-lite/src/ffmpeg_mcp_lite/server.py:14-22` | `mcp.tool()(fn)` en un solo sitio; las herramientas son funciones puras sin decorador | **COPIAR TAL CUAL** (facilita probarlas sin MCP) |
| Salida de `info` recortada | `ffmpeg-mcp-lite/src/…/tools/info.py:48-88` | filtra `ffprobe` a los campos útiles: **153 tokens** en vez del JSON completo | **ADAPTAR** (añadir el hash del contenido) |
| `config.py` por variables de entorno | `ffmpeg-mcp-lite/src/…/config.py` | `FFMPEG_PATH`, `FFPROBE_PATH`, `FFMPEG_OUTPUT_DIR` | **ADAPTAR** (falta validar que el directorio es escribible) |
| Directorio de salida decidido por el servidor | `ffmpeg-mcp-lite/src/…/convert.py:41-42` | el modelo **no** elige la ruta; el servidor la deriva del nombre de entrada | **ADAPTAR** — buena idea de seguridad, pero `~/Downloads` por defecto es mala elección, y colisiona: `{stem}_converted.{ext}` sobrescribe sin avisar |
| `crf_map` nombrado | `ffmpeg-mcp-lite/src/…/compress.py:34-38` | `low/medium/high` → CRF 28/23/18, en vez de exponer CRF al modelo | **COPIAR TAL CUAL** — el modelo razona mejor con etiquetas que con números de códec |
| Escapado de rutas para `subtitles` | `ffmpeg-mcp-lite/src/…/subtitles.py:82` | **ROTO en Windows**: escapa `'` y `:` pero **no `\`** | **DESCARTAR** y reescribir (§9.1) |
| Enum Zod de formatos | `image-worker-mcp/src/tools/sharp.ts:30` + `constants.ts:1-2` | valida el formato **antes** de ejecutar y el error enumera los válidos | **COPIAR TAL CUAL** — origen del mejor error medido (§7.2) |
| Detección HEIF por firma | `image-worker-mcp/src/tools/sharp.ts:105-108` | mira los bytes 4-12 (`ftypheic`, `ftypmif1`…), **no la extensión** | **COPIAR TAL CUAL** — es la doctrina de FileX (los bytes mandan) |
| Mensajes de error de Sharp | `image-worker-mcp/src/tools/sharp.ts:288-291` | `Input buffer has corrupt header…` → **17 tokens** precisos | **COPIAR TAL CUAL** |
| `outputImage` como booleano | `image-worker-mcp/src/tools/sharp.ts:56` | inyecta base64 en el texto de respuesta | **DESCARTAR** — es el antipatrón que este informe cuantifica (§3.3) |
| Redimensionado por defecto | `image-worker-mcp/src/tools/sharp.ts:157-170`, `constants.ts:4-6` | 800×600 `contain` cuando no se piden dimensiones | **DESCARTAR** — transformación destructiva no solicitada (§6.2) |
| `normalizeFilePath` | `image-worker-mcp/src/utils.ts:72-89` | quita barras de escape de rutas al estilo shell | **SOLO REFERENCIA** — riesgo latente en Windows si un directorio lleva `\` seguido de espacio |
| Construcción del servicio en el constructor | `image-worker-mcp/src/server.ts:18` | impide arrancar sin S3 | **DESCARTAR** — antipatrón (§1.2) |
| `_run_ffmpeg_with_fallback` | `video-audio-mcp/server.py:332-348` | copiar códecs y si falla reencodificar; lo usan **9** de las 27 herramientas | **ADAPTAR** — la **idea** es buena (copiar es ×100 más rápido); la implementación **cuelga el servidor** (§4.1) porque reintenta sobre la ruta que el primer intento ya creó, por `ffmpeg-python` y sin `overwrite_output()`. Con `stdin=DEVNULL`, `-y` y **ruta temporal distinta por intento**, es correcta |
| Dos vías de invocación en un mismo fichero | `video-audio-mcp/server.py` (ffmpeg-python ×32 vs `subprocess` ×7) | `-y` solo en la vía minoritaria | **DESCARTAR** — es el argumento de §9.5: una sola forma de lanzar subprocesos, envuelta en un helper que fija `stdin`, timeout y limpieza |
| Las 27 herramientas | `video-audio-mcp/server.py` | catálogo plano de operaciones | **DESCARTAR como modelo** — 39,7 % redundante, 0 anotaciones, 7.964 tokens |
| `errores como valor de retorno` | `video-audio-mcp/server.py:33-41` | `except: return f"Error …"` | **DESCARTAR** — garantiza `isError: false` en todo fallo (§7.1) |

### 8.1 Sobre `ffmpeg-mcp-lite/tests/` como plantilla (Fase 5, MEDIDO)

**Ejecutada:** `29 pasaron, 3 fallaron` en **53,19 s** con `pytest` 9.1.1 + `pytest-asyncio` 1.4.0.

**¿Cómo genera sus ficheros de prueba?** Sintéticamente, con ffmpeg y `lavfi`
(`testsrc=duration=2:size=320x240:rate=30` + `sine=frequency=440`). **El repositorio no contiene ni
un solo binario de prueba.** Es la decisión correcta y FileX debe copiarla: hoy `corpus/` pesa
**>200 MB** (`fuente_4k.mp4` son 128 MB, `patologico_16bit.tif` 72 MB). Para la **suite** (distinta
del banco de pruebas de rendimiento) basta con generar los ficheros al vuelo.

**¿Verifica la salida o solo que no hay excepción?** **Verifica existencia, casi nunca formato.**
Es exactamente el hueco que FileX dice cubrir:

- `test_convert.py:20-23` comprueba `"Converted successfully" in result` y `output_path.exists()`.
  **Nunca comprueba que el `.mkv` sea realmente Matroska.** Un fichero de 0 bytes con el nombre
  correcto pasaría el test — y §4/§6 demuestran que los ficheros de 0 bytes **ocurren de verdad**.
- `test_convert.py:33-35` (`test_convert_with_scale`) **solo** comprueba la cadena de éxito: no mira
  el fichero, ni verifica que la escala se aplicara.
- `test_info.py:26-29` es la excepción y el modelo a seguir: afirma `width == 320` y `height == 240`,
  contenido real y no metadatos.
- `test_frames.py:30-31` comprueba `any(output_dir.glob("*.jpg"))` — existencia de **algún** fichero,
  sin contarlos ni abrirlos.

> **Qué se lleva FileX:** la **estructura** (fixtures sintéticas, un test por herramienta,
> `conftest.py` con `skip` por entorno) **tal cual**; y **corrige el criterio de aserción**: cada
> test debe terminar en `verificar_salida(ruta, formato_esperado, duracion_esperada)` con bytes
> mágicos y sonda, no en `exists()`.

**Los 3 fallos son un bug real en Windows, no del entorno:** `test_subtitles.py` completo, por
`subtitles.py:82`:

```python
sub_path_escaped = str(sub_path).replace("'", "'\\''").replace(":", "\\:")
```

Escapa la comilla y los dos puntos, pero **no la barra invertida**. libass recibe
`C\:\Users\krato\…` y se come `\U`, `\k`… El error literal es
`Unable to open C:UserskratoAppDataLocalTemptmp1jjejt4bsample.srt` — la ruta sin ninguna barra.
**`ffmpeg-mcp-lite` no puede quemar subtítulos en Windows.** El escapado correcto debe sustituir
`\` → `\\\\` **antes** que `:` → `\:`.

**PENDIENTE:** no se ejecutó la suite de `image-worker-mcp` (`tests/utils.test.ts`, `tests/tools/`,
`tests/services/`). Requiere `npm install` completo del clon (incluye `sharp` y `libheif-js`
nativos) y se prefirió no competir por CPU con las mediciones de conversión en curso. El servidor sí
se ejecutó, vía `npx @boomlinkai/image-worker-mcp` (paquete publicado, v0.0.6), que es como lo usaría
un usuario real.

---

## 9. Qué reglas quedan confirmadas, matizadas y refutadas

### 9.1 CONFIRMADAS

| Regla | Origen | Evidencia nueva (MEDIDO) |
|---|---|---|
| **Devolver ruta + metadatos, nunca contenido** | `00-mcp-patrones.md` regla 1 | El asa cuesta **32-72 tokens y es independiente del tamaño** (15,5 MB → 32 tok). Inyectar el binario cuesta **0,93 tok/byte**: un JPEG de 100 KB serían ~95.000 tokens, el **48 %** de una ventana de 200 K |
| **Anotar con `readOnlyHint`/`destructiveHint`** | regla 2 | **0 de 3** servidores anotan. De los 5 MCP de conversión sondeados en el proyecto, solo docling lo hace |
| **`isError: true` de verdad en los fallos** | `mcp-ergonomia.md` §7 | `video-audio-mcp` devuelve **`isError: false` en los 4 casos de error**, con ~1.000 tokens de basura. Es el antipatrón markitdown, ×1.000 en coste |
| **Nunca filtrar `stderr` crudo al modelo** | `mcp-ergonomia.md` §7 | Reproducido en 2 de 3 servidores: lite 938-1.228 tok, vam 884-1.158 tok, casi todo banner de compilación de ffmpeg |
| **Verificación obligatoria de salida** | diferenciador nº 1 | Quedó **1 fichero de 0 bytes** permanente (`vam_dead.gif`) que un verificador basado en `exists()` daría por bueno. Y `image-worker` entregó un WebP **válido** que era una imagen **ampliada ×9,75 con barras negras**: verificar el contenedor no basta, hay que comparar geometría y duración con la entrada |
| **El error debe enumerar las alternativas válidas** | `mcp-ergonomia.md` §4.1 | Confirmado por segunda vez y en otro ecosistema: el enum de Zod de `image-worker` produce el mejor error medido (108 tok, lista los 4 formatos válidos) frente a los 1.228 tok de lite para el mismo fallo, que **no** dicen cuáles se aceptan |

### 9.2 MATIZADAS

**(a) «Pocas herramientas, bien nombradas» → «poco catálogo, medido en tokens».**
`00-mcp-patrones.md` regla 5 cuenta herramientas. **MEDIDO:** el coste por herramienta varía **×11**
(79 → 875 tokens). `resize_image`, **una sola herramienta**, cuesta 875 tokens: más que las 3
herramientas del grupo `conversion` de docling (880 para las tres) y **11 veces el catálogo entero
de markitdown**. Las 4 herramientas previstas para FileX (`convert`, `inspect`, `list_targets`,
`batch`) pueden costar 300 o 3.500 tokens según cómo se declaren sus parámetros.
→ **La regla debe fijar un presupuesto en tokens de catálogo** (propuesta: ≤1.200 tokens para las
cuatro), no un número de herramientas.

**(b) «Nunca contenido» → «nunca binario, en ninguna codificación, incluida base64 dentro de texto».**
Ver §9.3, es el hallazgo principal.

**(c) El arranque en frío importa aún menos de lo que se creía.**
`video-audio-mcp` arranca en **1,2 s** con **27 herramientas**, y `ffmpeg-mcp-lite` en **0,82 s** en
caliente (6,7 s la primera vez, coste de importación de Python en frío). Frente a los ~6 s de
docling. **El arranque no correlaciona con el tamaño del catálogo, sino con lo que el servidor
importa** (docling carga modelos; estos solo envuelven un binario externo). Un FileX que delegue en
ffmpeg/ImageMagick nativos arrancará en ~1 s.
→ Refuerza `mcp-ergonomia.md:402`: lo caro es el **motor**, no la capa MCP.

**(d) La subsunción de herramientas es medible y es enorme.**
Dato nuevo: **39,7 % del catálogo de vam es estrictamente redundante**. No es una impresión: 13
herramientas son casos particulares de 2. Se propone una **prueba automática para FileX**: si el
esquema de la herramienta A es un subconjunto estricto del de B con la misma semántica, A sobra.

### 9.3 REFUTADA (parcialmente): «para salidas binarias el patrón de devolver contenido sencillamente no existe»

`analysis/00-mcp-patrones.md`, §«El error de diseño», afirma literalmente:

> «Y para salidas binarias — un MP4, un PNG — el patrón sencillamente no existe.»

**Es falso. MEDIDO.** `image-worker-mcp` **sí** devuelve el PNG entero, y basta con poner un booleano
a `true`. La misma llamada, mismo fichero, mismo servidor:

```
resize_image(imagePath=tipico.jpg, format='png')                     ->     71 tokens
resize_image(imagePath=tipico.jpg, format='png', outputImage=true)   ->  6.218 tokens
```

El patrón existe, está publicado en npm y **está a un booleano de distancia**.

Y lo verdaderamente incómodo: **no lo hace de la forma que la regla de FileX vigila.** No usa
`ImageContent`. Mete el base64 en un string JSON dentro de un `TextContent`. Por eso:

- el arnés lo etiquetó `PROSA` y, en un caso, **`ASA`** — el patrón que FileX considera *correcto*;
- `tokens_binario_si_se_inyecta` y `bytes_binario` salieron **0**;
- solo `tokens_texto = 6.218` delata lo que ha pasado.

> **Reescritura propuesta de la regla 1 de `analysis/00-mcp-patrones.md`:**
>
> 1. **Devolver ruta + metadatos, nunca el contenido convertido.** «Contenido» incluye el binario
>    **en cualquier codificación**: `ImageContent`/`AudioContent`, `BlobResourceContents`, y
>    **también base64 embebido en un `TextContent` o en un campo JSON**, que es la forma en que
>    aparece de verdad en el ecosistema (medido en `image-worker-mcp`).
> 2. **El criterio operativo es el tamaño de la respuesta, no su tipo.** Toda respuesta de una
>    herramienta de FileX debe caber en **≤200 tokens** salvo `inspect`. Si una respuesta supera ese
>    presupuesto, es un fallo de diseño, con independencia de qué tipo de contenido use.
> 3. **No hay excepción por tamaño para las imágenes.** Se evaluó explícitamente, que era el
>    encargo. A **0,93 tokens por byte**, el umbral de rentabilidad está en **1-2 KB**: por debajo
>    del tamaño de un icono. No existe un «salvo imágenes por debajo de N KB» que valga la pena: una
>    miniatura de 10 KB ya cuesta **~9.500 tokens**, **132 veces** más que devolver su ruta (72).
>    **La firma de las herramientas de FileX no cambia.**

### 9.4 Regla nueva: una conversión larga no puede ser una llamada bloqueante

**MEDIDO** en §4.2, y no estaba contemplado en ninguna regla previa:

> **Toda operación que pueda superar el timeout del cliente debe devolver un asa de trabajo
> (`job_id`) inmediatamente, no bloquear.**
>
> Evidencia: `ffmpeg_convert(… "webm")` sobre un clip de **5 segundos** superó los **900 s** del
> timeout del cliente. El modelo recibió `TimeoutError` (4 tokens, sin `isError`). **Pero la
> conversión terminó bien**: en disco quedó un WebM VP9 válido de 559.046 B con la duración y la
> geometría exactas. El trabajo estaba hecho y el modelo no podía saberlo; un agente reintentaría y
> repetiría 15 minutos de cómputo ya realizado.
>
> Es un modo de fallo que el patrón de asa **sí** resuelve, pero solo si el asa se entrega **al
> empezar**, no al terminar. Con `convert()` bloqueante, FileX heredaría este fallo tal cual.

### 9.5 Regla nueva que sale de este informe: aislar los subprocesos

No estaba en `00-mcp-patrones.md` ni en `mcp-ergonomia.md`. **MEDIDO** en §4:

> **Todo subproceso lanzado por el servidor MCP debe correr con `stdin=DEVNULL`, con las banderas no
> interactivas del programa (`-y`, `-nostdin`), con un timeout del lado del servidor y matando el
> **árbol** de procesos al terminar.**
>
> **El orden importa: `stdin=DEVNULL` primero, las banderas después.** `video-audio-mcp` demuestra
> por qué. El mismo fichero **sí** pasa `-y` en sus 7 llamadas por `subprocess` y **no** lo pasa en
> ninguna de sus 32 invocaciones por `ffmpeg-python` (§4.1). No es que sus autores ignoraran el
> problema: lo resolvieron en una vía y lo olvidaron en la otra. **Una disciplina que hay que
> recordar en cada punto de invocación no es una defensa**; hay que cerrarlo una vez, en la
> construcción del proceso, donde ninguna vía puede saltárselo.
>
> Evidencia: `video-audio-mcp` **cuelga la sesión MCP** en la conversión más común que existe
> (cambio de formato con reencodificación), porque ffmpeg hereda la tubería JSON-RPC como `stdin` y
> se queda esperando a que alguien le conteste `Overwrite? [y/N]`. Medido: **1,4 s con `-y`,
> infinito sin `-y`.** Y `ffmpeg-mcp-lite` deja `ffmpeg` huérfanos vivos **13 minutos** después de
> que su servidor haya muerto.

---

## 10. Índice de datos crudos

En `bench/salidas-mcp-refs/multimedia/`:

| Fichero | Contenido |
|---|---|
| `gen_specs.py` | genera todos los `*.spec.json` (con rutas Windows en barra normal) |
| `verificar_salidas.py` | verificación en disco: bytes mágicos + `ffprobe`/`magick` |
| `cat_vam.json`, `cat_lite.json`, `cat_img.json` | Fase 1, catálogos completos con esquemas |
| `conv_vam.json`, `conv_lite.json`, `conv_img.json` | Fase 2, conversiones |
| `deadlock_vam.spec.json` + `.stderr.log` | Fase 2b, bloqueo por MCP. **No hay `.json` de resultados: la sesión murió antes de poder escribirlo — esa ausencia es la evidencia** |
| `err_vam.json`, `err_lite.json`, `err_img.json` | Fase 4, errores |
| `verificacion.json` | Fase 2c, verificación de las salidas |
| `*.spec.json`, `*.stderr.log` | entradas y `stderr` de cada sondeo |
| `salidas/`, `salidas_lite/` | ficheros convertidos |
| `corrupto/` | ficheros truncados para la fase de errores |
| `repro/` | reproducción aislada del deadlock de §4.1: `t.gif` y `dead.gif` (**0 bytes**, lo que deja el intento primario y desencadena el bloqueo) y `stderr_ffmpeg_tipico.txt` (el volcado de 1.037 tokens de §7.1) |

Peso total de los datos crudos: **4,3 MB**. Se han descartado los duplicados grandes de la
reproducción (una copia del GIF y del MKV que ya están en `salidas*/`); se conservan los ficheros de
**0 bytes**, que son evidencia y no residuo.

**Este agente no modificó** `bench/scripts/mcp_probe_bin.py` ni `bench/salidas-mcp/mcp_probe.py`, y
no hizo falta ninguna variante del arnés.

**Nota de trazabilidad (MEDIDO):** todas las mediciones de este informe se tomaron con la versión del
arnés de **13.632 bytes** vigente hasta las 21:57 (último resultado escrito: `conv_lite.json`, a las
21:56:59). A las **22:03** el fichero pasó a 15.482 bytes al añadírsele `UMBRAL_B64_CHARS = 512` y
una función `_base64_dentro_del_texto()` — es decir, **exactamente el detector cuya ausencia se
argumenta en §3.4**. El cambio es posterior a la última medición y **no afecta a ninguna cifra de
este informe**; se deja constancia para que quien reproduzca los sondeos sepa que con el arnés
actual el patrón `CONTENIDO ENCUBIERTO` **ya debería detectarse solo**, y las respuestas de
`image-worker-mcp` con `outputImage=true` dejarían de etiquetarse como `PROSA`/`ASA`.
