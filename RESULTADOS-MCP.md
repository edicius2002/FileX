# FileX — Resultados de las pruebas sobre `repos/mcp-refs/`

**Fecha:** 20 de agosto de 2026
**Estado:** categoría cerrada. Fase 1 (lectura) y fase 2 (ejecución) completadas.

> Este documento **sustituye a `PRUEBAS-MCP-REFS.md`**, que era la especificación de lo pendiente. Aquí están las respuestas.
>
> Cada afirmación va marcada **MEDIDO** (hay dato en `bench/salidas-mcp-refs/`) o **PENDIENTE** (no se ha comprobado). Donde el resultado contradice a un documento del proyecto, se dice y se señala el documento.
>
> **Nota de trazabilidad.** Los tres informes citan `PRUEBAS-MCP-REFS.md §X` allí donde corrigen una afirmación suya. Esas citas son históricas y su referente está en el commit inicial: `git show 23b8d3c:PRUEBAS-MCP-REFS.md`. Las correcciones a ese documento están recogidas en §12.7 y en `analysis/00-mcp-componentes.md` §3.6.

---

## 0. Qué se hizo

Seis repositorios, tres carriles de trabajo, tres informes:

| Carril | Qué | Entregable |
|---|---|---|
| **Consolidación** | Los 146 KB de `00-mcp-filesystem.md` y `00-mcp-multimedia.md` reducidos a una tabla por pieza | `analysis/00-mcp-componentes.md` |
| **Multimedia** | `video-audio-mcp`, `ffmpeg-mcp-lite`, `image-worker-mcp` ejecutados contra el corpus | `bench/mcp-refs-multimedia.md` |
| **Confinamiento** | `servers/src/filesystem` y `kordoc` atacados y medidos | `bench/mcp-refs-confinamiento.md` |

**Arnés:** `bench/scripts/mcp_probe_bin.py`, derivado de `bench/salidas-mcp/mcp_probe.py` (que se conserva intacto como evidencia de lo medido en la fase documental). Mide arranque en frío, coste de catálogo en tokens, y por llamada: latencia, `isError`, y el desglose de la respuesta en texto / binario / bytes, con un veredicto de patrón.

**Validación cruzada del arnés (MEDIDO):** sondeando `markitdown-mcp` con `corpus/pdf/tipico_texto.pdf` devuelve **56 tokens**, la misma cifra registrada en `bench/mcp-ergonomia.md` §2.1 en la fase anterior. Las cifras nuevas son comparables con las viejas.

---

## 1. La respuesta corta

> **El asa gana, y ahora está medido en binario.** Cuesta **32-72 tokens, con independencia del tamaño del fichero**: un MP4 de 15,5 MB devuelve 32 tokens, igual que un PNG de 316 bytes.
>
> **Pero el patrón contrario existe y nadie lo estaba vigilando.** `image-worker-mcp` devuelve la imagen entera con un booleano, **como base64 dentro de un `TextContent`** — invisible para cualquier regla escrita sobre tipos de contenido del protocolo.
>
> **Y la referencia oficial de confinamiento resiste**: 28 de 29 vectores denegados. Su virtud es un detalle de orden que se copia en una línea; sus fallos se arreglan en otra.

---

## 2. Las seis preguntas transversales, respondidas

### Pregunta 1 — ¿Qué se devuelve tras convertir un binario? · **CERRADA**

**MEDIDO.** Ninguno de los tres emite `ImageContent`, `AudioContent` ni `BlobResourceContents`. Los tres devuelven texto con una ruta.

**El asa es barata y constante:**

| Entrada | Servidor | Respuesta |
|---|---|---:|
| `tipico.mp4` — 15,5 MB | `video-audio-mcp` | **32 tokens** |
| `tipico.mp4` — 15,5 MB | `ffmpeg-mcp-lite` | **34 tokens** |
| `trivial.png` — 316 B | `image-worker-mcp` | **72 tokens** |

Cinco órdenes de magnitud de variación en la entrada producen **×2,25** en el coste de la respuesta, y esa variación se debe a la longitud de la ruta, no al fichero. **Es la propiedad que hace viable el diseño de FileX.**

### Pregunta 2 — ¿Cuántas herramientas saturan al modelo? · **RESPONDIDA A MEDIAS**

**MEDIDO:** el coste. **PENDIENTE:** el efecto en la elección del modelo, que sigue sin medirse en todo el proyecto. El análisis de las 27 herramientas es **estructural, no conductual**, y así está marcado.

### Pregunta 3 — ¿Cómo se agrupa el dominio? · **CERRADA, con ganador**

**MEDIDO.** `ffmpeg-mcp-lite` cubre el mismo dominio con **8 herramientas en 2.322 tokens** frente a las **27 en 7.964** de `video-audio-mcp`. Un fichero por herramienta bajo `tools/`, registro explícito en un `server.py` de 29 líneas, agrupado **por intención del usuario** (convertir, comprimir, recortar, extraer, unir) y no por parámetro de ffmpeg. **Es la forma que FileX necesita.**

La separación `services/` frente a `tools/` de `image-worker-mcp` **no era lo que parecía**: `services/` son backends de subida a la nube, no lógica de conversión.

### Pregunta 4 — ¿Cómo se confina el sistema de ficheros? · **CERRADA** — ver §5

### Pregunta 5 — ¿Qué mensaje de error llega al modelo? · **CERRADA, y el resultado es unánime y malo** — ver §6

### Pregunta 6 — ¿Se puede devolver una imagen como contenido? · **CERRADA: no hay umbral que valga la pena**

Era la única sin precedente en la lectura de código, y el motivo del encargo. **MEDIDO: 0,93 tokens por byte de salida** (media de tres muestras: 0,887 · 0,903 · 0,999).

| Tamaño | Coste si se inyecta | % de una ventana de 200 K |
|---|---:|---:|
| 1 KB (icono) | ~950 tok | 0,5 % |
| 10 KB (PNG pequeño) | ~9.500 tok | 4,8 % |
| 100 KB (JPEG normal) | ~95.000 tok | **48 %** |
| 15,5 MB (`tipico.mp4`) | ~14.400.000 tok | **×72 la ventana entera** |

**El punto de rentabilidad está en 1-2 KB** — por debajo del tamaño de un icono. Una miniatura de 10 KB cuesta **132 veces** más que devolver su ruta.

> **No existe el «salvo imágenes por debajo de N KB». La firma de las herramientas de FileX no cambia.**

---

## 3. El hallazgo principal: CONTENIDO ENCUBIERTO

`image-worker-mcp` tiene un parámetro que ningún MCP documental tenía (`src/tools/sharp.ts:56`):

```ts
outputImage: z.boolean().optional().default(false)
  .describe("Whether to include the base64-encoded image in the output response"),
```

Y la respuesta se construye así (`sharp.ts:262-283`):

```ts
return { content: [{ type: 'text', text: JSON.stringify({
    ...(this.args.outputImage ? { image: outputBase64 } : {}),
    format, width, height, size, savedTo, source }, null, 2) }] };
```

**El binario no viaja como `ImageContent`. Viaja como base64 dentro de un string JSON dentro de un `TextContent`.**

| Entrada | Salida | `outputImage=false` | `outputImage=true` | Multiplicador |
|---|---:|---:|---:|---:|
| `trivial.png` (316 B) | 1.214 B | 72 tok | **1.213 tok** | ×16,8 |
| `tipico.jpg` → webp | 3.564 B | 72 tok | **3.218 tok** | ×44,7 |
| `tipico.jpg` → png | 7.008 B | 71 tok | **6.218 tok** | **×87,6** |

### Por qué esto importa más que el número

El arnés clasificó estas respuestas como `PROSA` y —en un caso— como **`ASA`**, el patrón que FileX considera *correcto*, porque el JSON incluye un campo `savedTo` con una ruta. `tokens_binario` y `bytes_binario` salieron **0**, que es lo correcto según el protocolo. Solo `tokens_texto = 6.218` delataba lo ocurrido.

> **Una respuesta de 6.218 tokens con una imagen entera dentro se etiquetó como el patrón bueno.**

**Consecuencia para FileX (MEDIDO):** un revisor —humano o automático— que audite un MCP buscando `ImageContent` **no detecta este antipatrón**. La regla debe redactarse sobre **tokens de respuesta**, que es lo observable y lo que se paga, no sobre tipos de contenido del protocolo.

*(El arnés se corrigió el 20/08 a las 22:03: `_base64_dentro_del_texto()` detecta rachas de base64 ≥512 caracteres dentro de texto y las contabiliza aparte. Es posterior a todas las mediciones de este documento y no afecta a ninguna cifra.)*

---

## 4. Catálogos: lo que cuesta un servidor antes de hacer nada

**MEDIDO** con `tiktoken`/`o200k_base`:

| Servidor | Herr. | `tokens_catalogo` | tok/herr. | Anotadas | Arranque en frío |
|---|---:|---:|---:|---:|---:|
| **`video-audio-mcp`** | **27** | **7.964** | 295 | **0** | 1.202 ms |
| `kordoc` | 15 | 7.759 | 517 | **0** | — |
| *`docling-mcp`* (ya medido) | *19* | *5.280* | *278* | *sí* | *~6.000 ms* |
| `servers/filesystem` | 14 | 3.360 | 240 | **14/14** | — |
| `ffmpeg-mcp-lite` | 8 | 2.322 | 290 | **0** | 6.689 / **817** ms |
| `image-worker-mcp` | 2 | 1.177 | **589** | **0** | 2.620 ms |
| *`docling-mcp --conversion`* | *3* | *880* | *293* | *sí* | *1.800 ms* |
| *`markitdown-mcp`* (ya medido) | *1* | *79* | *79* | *0* | *3.413 ms* |

**El techo del sector son 7.964 tokens** — un 51 % más que docling-mcp y ×101 markitdown. Es ~4 % de una ventana de 200 K consumidos permanentemente por un servidor que aún no ha hecho nada.

### Lo que matiza la regla de «pocas herramientas»

**MEDIDO: el coste por herramienta varía ×11**, de 79 tokens (`markitdown.convert_to_markdown`) a **875** (`image-worker.resize_image`). Esa herramienta, **ella sola**, cuesta casi lo mismo que las tres del grupo `conversion` de docling juntas (875 frente a 880).

La causa es la **superficie de parámetros**, no el número de herramientas: `resize_image` declara **25 parámetros, los 25 con descripción**.

> Las cuatro herramientas previstas para FileX (`convert`, `inspect`, `list_targets`, `batch`) pueden costar **300 o 3.500 tokens** según cómo se declaren sus parámetros. **El presupuesto se fija en tokens de catálogo, no en número de herramientas.** Propuesta: ≤1.200 tokens para las cuatro.

### Dos datos incómodos

- **Cero anotaciones en los tres servidores de multimedia.** De los cinco MCP de conversión sondeados en todo el proyecto, **solo docling anota**. Si FileX anota, es una ventaja diferencial real, no una alineación con la norma.
- **`outputSchema` presente no significa contrato de salida.** `video-audio-mcp` y `ffmpeg-mcp-lite` los declaran en las 35 herramientas, pero los genera FastMCP a partir del `-> str` de la firma. Comprobados **uno a uno los 35, sin una sola excepción**, todos dicen lo mismo: *«devuelve una cadena»*. Ni formato, ni ruta, ni si hubo error. **Coste de catálogo sin información.**

### Subsunción: el 39,7 % del catálogo sobra

**MEDIDO.** De las 27 herramientas de `video-audio-mcp`, **13 son casos particulares de 2**. Cinco nombres empiezan por `set_video_audio_track_…` y compiten en el espacio de decisión del modelo cuando `convert_video_properties` (`server.py:114`) ya los cubre todos.

Tres herramientas describen sus argumentos como *«Args listed in PRD»* o *«previous messages»* — documentos que el modelo no puede ver.

> **Prueba automática propuesta para FileX:** si el esquema de la herramienta A es un subconjunto estricto del de B con la misma semántica, A sobra.

---

## 5. Confinamiento: la referencia oficial resiste

### El resultado

**MEDIDO. 28 de 29 vectores denegados** contra `servers/src/filesystem`: los 8 de travesía relativa, los 6 de ruta absoluta, los 3 de prefijo engañoso y los 4 de symlink/junction.

**El único concedido: flujos de datos alternativos.** `«raíz»\dentro.txt:oculto` devolvió `ADS_OCULTO_DENTRO_777` con `isError=false`. Son **bytes distintos de los del fichero que se validó**, dentro de la raíz permitida. En un conversor eso significa convertir algo que no es lo que el usuario cree.

**Cinco falsos negativos** que deniegan rutas legítimas: minúsculas, prefijo `\\?\`, nombre corto 8.3, `/d/…` y `/mnt/d/…`. Los dos últimos destapan que `convertToWindowsPath` y `normalizePath` son **código muerto** — `validatePath` decide `isAbsolute` antes de llamarlos.

### El oráculo de existencia: refutado fuera, confirmado dentro

**MEDIDO.** Fuera de la raíz, «existe pero prohibido» y «no existe» dan el **mismo mensaje palabra por palabra** y la misma latencia (1,4 frente a 1,9 ms). `D:\Windows\win.ini` (que no existe en esta máquina) devuelve un mensaje idéntico al de `C:\Windows\win.ini` (que sí existe). **Cero bits de información nueva.**

La razón es de diseño, y es lo mejor que tiene la referencia (`lib.ts:107-111`):

```js
// Security: Check if path is within allowed directories before any file operations
const isAllowed = isPathWithinAllowedDirectories(normalizedRequested, allowedDirectories);
```

**El predicado es léxico y corre antes de tocar el disco.** Si la ruta cae fuera, el servidor jamás le pregunta al sistema de ficheros, así que no puede filtrar lo que no sabe.

**Dentro** de la raíz sí es un oráculo: contenido / `ENOENT` / `Parent directory does not exist` / `EISDIR` son cuatro respuestas distinguibles. Para `filesystem` da igual —`list_directory` ya lo da gratis—; **para FileX puede no dar igual**, porque no expone listado y el error se convertiría en el listado.

Esto **refuta parcialmente** `analysis/00-mcp-filesystem.md` §A.4, que lo daba por oráculo sin matiz.

### Lo que sí filtra

1. **La lista blanca completa**, en los tres mensajes de denegación (`lib.ts:110,119,131`).
2. **La ruta resuelta de fuera del sandbox** cuando hay un enlace: `… symlink target outside allowed directories: C:\Windows\win.ini not in «raíz»`. El agente aprende **geografía del disco del anfitrión** que jamás pidió. Es la peor de las tres y la más fácil de arreglar.
3. **Amplificación por lotes:** `read_multiple_files` con 6 rutas devolvió `isError=false` y **seis** mensajes de denegación con la lista blanca repetida seis veces — **419 tokens para no decir nada**.

### TOCTOU: no reproducido

**MEDIDO, y corrige al análisis de código:**

- **Vector del encargo refutado.** Un enlace creado *después* de arrancar el servidor se detecta: `realpath` corre en **cada llamada**. Lo que se resuelve al arrancar es la lista blanca, y por usabilidad, no por seguridad.
- **La carrera real: 0 fugas en 52.800 llamadas**, y tampoco con la ventana ensanchada a propósito (`UV_THREADPOOL_SIZE=1`, 96 en vuelo). No es «solo gana forzándolo»: no gana.
- **Los tests del propio repo que "demuestran" la carrera no llaman a `validatePath`** — usan el predicado léxico y leen la ruta original. Es el motivo por el que la lectura de código creyó lo contrario.

**PENDIENTE en Linux.** En Windows el 79 % de los `symlink` del atacante fallaron por bloqueo de fichero, lo que sesga el resultado a favor del servidor.

### `kordoc`: el mismo problema resuelto al revés

**MEDIDO.** Es un **oráculo completo sobre todo el disco**: (b) y (c) dan mensajes distintos incluso fuera de `KORDOC_ROOT`, porque `safePath` hace `realpathSync` **antes** de `assertWithinRoot` — el orden inverso al de `filesystem`.

> Las dos implementaciones existen, el experimento las enfrentó, y **el orden es la única diferencia**.

### Y el hallazgo más transferible: CLI y MCP divergen en seguridad

**MEDIDO.** `KORDOC_ROOT` **solo lo aplica la superficie MCP**. `src/cli.ts` no importa `safePath` ni `assertWithinRoot`, y la CLI leyó un fichero completamente fuera de la raíz con `exit=0`.

**FileX va a tener cuatro superficies** — CLI, MCP, watcher y API HTTP — sobre el mismo núcleo. Y el watcher sigue rutas de origen externo, así que está tan expuesto como el MCP.

De paso, esto **mata una estimación optimista**: la cifra de que «la capa MCP cuesta como la CLI porque comparten núcleo» salía de kordoc, y aquí **no lo comparten**.

---

## 6. Errores: qué mensaje llega al modelo

**MEDIDO. El resultado es unánime y malo.**

| Antipatrón | Dónde | Coste |
|---|---|---|
| `stderr` crudo de ffmpeg reenviado al modelo | `ffmpeg-mcp-lite`, `video-audio-mcp` | 884-1.228 tokens, casi todo banner de compilación |
| **`isError: false` en todos los fallos** | `video-audio-mcp`, los 4 casos | El agente solo distingue éxito de fracaso buscando la palabra «Error» dentro de una frase |
| El error nombra el comando que lo instala | `kordoc` (3 sitios), `docling-mcp` | Dirige la siguiente acción del agente |

### La mejor lección del carril, y es positiva

**MEDIDO:** el mejor error de todo el proyecto lo produce el `enum` de Zod de `image-worker-mcp`: **108 tokens que enumeran los 4 formatos válidos**, frente a los **1.228 tokens** de `ffmpeg-mcp-lite` para el mismo fallo, que no dicen cuáles se aceptan.

Confirma por segunda vez y en otro ecosistema la regla de `mcp-ergonomia.md` §4.1: **el error debe enumerar las alternativas válidas.**

Y la forma a copiar para el resto es `describeError` de kordoc (`src/mcp.ts:84-100`): mapa **código de error → frase fija y accionable, sin la ruta**, con el código viajando **dentro** de la excepción.

> **Aviso:** sus mensajes están escritos **en coreano**, y su `classifyError` (`utils.ts:166-181`) clasifica comparando subcadenas coreanas del mensaje en vez de mirar `err.code`. **Se copia la forma, no el contenido**, y el código va dentro de la excepción, no deducido del texto.

---

## 7. Lo que amplía el contrato de verificación

**MEDIDO, y es lo que más cambia el plan.** 14 de 15 salidas pasaron la verificación de bytes mágicos. Pero `image-worker-mcp` mintió sobre otra cosa: al pedirle **solo un cambio de formato**, redimensionó en silencio.

| Entrada | Original | Lienzo entregado | **Contenido real** | Qué pasó |
|---|---|---|---|---|
| `tipico.jpg` | 1920×1080 | 800×600 | **800×450** | reducido ×2,4 **+ barras negras** de 75 px |
| `trivial.png` | 64×64 | 800×600 | **624×600** | **ampliado ×9,75** + barras laterales |

La respuesta dice `"width": 800, "height": 600`. Eso es **el lienzo**, no la imagen. Causa: `sharp.ts:157-170` — si no se pasan `width` ni `height`, no se omite el redimensionado; se aplican `DEFAULT_WIDTH=800`, `DEFAULT_HEIGHT=600` y `fit='contain'`.

**Un fichero de 316 bytes y 64×64 se devolvió como 1.214 bytes y 800×600, con el 40 % de la superficie en barras negras, presentado como una conversión de formato correcta.**

> El contrato de `PLAN-ORQUESTADOR.md` §4.2 comprueba firma real, flujos esperados, y **propiedades declaradas frente a medidas**. Este caso **pasa los tres**: el WebP es un WebP válido y sus propiedades declaradas coinciden con lo entregado.
>
> **Falta un cuarto punto: propiedades pedidas frente a obtenidas.** «No te pedí que redimensionaras» es una condición distinta de «el fichero es coherente consigo mismo». Y ninguna transformación no solicitada puede aplicarse por defecto.

También quedó **un fichero de 0 bytes permanente** (`vam_dead.gif`) que un verificador basado en `exists()` habría dado por bueno.

---

## 8. Dos fallos operativos y las reglas que salen de ellos

### 8.1 `video-audio-mcp` bloquea la sesión MCP entera

**MEDIDO.** En la conversión más común que existe —cambio de formato con reencodificación— ffmpeg hereda la tubería JSON-RPC como `stdin` y se queda esperando a que alguien conteste `Overwrite? [y/N]`.

**1,4 s con `-y`. Infinito sin él.**

El desglose por vía de invocación (verificado en el código):

| Vía | Invocaciones | `-y` / `overwrite_output()` |
|---|---:|---|
| `ffmpeg-python` | 32 | **0** |
| `subprocess` directo | 7 | **7** (`:898, :915, :956, :1001, :1022, :1434, :1547`) |

De las 27 herramientas: 1 no toca ffmpeg, **24 usan solo `ffmpeg-python`** (15 en su cuerpo + 9 delegando en `_run_ffmpeg_with_fallback`) y 2 son mixtas. Reproducido end-to-end en **una**; el resto es el mismo mecanismo, marcado **PENDIENTE**.

> **El mismo fichero sabe pasar `-y` en una vía y se le olvida en la otra.** No es que sus autores ignoraran el problema: lo resolvieron en un sitio y lo olvidaron en otro.
>
> **Regla nueva:** todo subproceso corre con **`stdin=DEVNULL`**, con las banderas no interactivas (`-y`, `-nostdin`), con timeout del lado del servidor, y matando el **árbol** de procesos. **El orden importa: `stdin=DEVNULL` primero, las banderas después** — una disciplina que hay que recordar en cada punto de invocación no es una defensa; hay que cerrarla en la construcción del proceso, donde ninguna vía pueda saltársela.

`ffmpeg-mcp-lite`, por su parte, dejó procesos `ffmpeg` huérfanos vivos **13 minutos** después de que su servidor muriera.

### 8.2 El «éxito huérfano»

**MEDIDO.** `ffmpeg_convert(… "webm")` sobre un clip de **5 segundos** superó los 900 s del timeout. El modelo recibió `TimeoutError` (4 tokens, sin `isError`). **Pero la conversión terminó bien**: en disco quedó un WebM VP9 válido de 559.046 B, con la duración y la geometría exactas.

El trabajo estaba hecho y el modelo no podía saberlo. Un agente reintentaría y repetiría cómputo ya realizado.

> **Regla nueva:** toda operación que pueda superar el timeout del cliente devuelve un **`job_id` inmediatamente**, no bloquea. Es un modo de fallo que el patrón de asa resuelve, pero **solo si el asa se entrega al empezar, no al terminar**. Con un `convert()` bloqueante, FileX heredaría este fallo tal cual.

---

## 9. Las reglas, revisadas

### 9.1 Confirmadas

| Regla | Evidencia nueva |
|---|---|
| Devolver ruta + metadatos, nunca contenido | El asa cuesta 32-72 tok e **independiente del tamaño**; inyectar cuesta **0,93 tok/byte** |
| Anotar `readOnlyHint` / `destructiveHint` | **0 de 3** anotan. Solo docling, de 5 servidores sondeados |
| `isError: true` de verdad | `video-audio-mcp` da `false` en los 4 fallos, con ~1.000 tokens de basura |
| Nunca filtrar `stderr` crudo | Reproducido en 2 de 3 |
| **Verificación obligatoria de salida** | Un WebP **válido** que era una imagen ampliada ×9,75 con barras negras |
| El error enumera las alternativas válidas | 108 tok (enum de Zod) frente a 1.228 tok para el mismo fallo |

### 9.2 Matizadas

**(a) «Pocas herramientas» → «poco catálogo, medido en tokens».** El coste por herramienta varía ×11. El presupuesto se fija en tokens.

**(b) «Nunca contenido» → «nunca binario en ninguna codificación, incluida base64 dentro de texto».** Ver §3.

**(c) El arranque en frío importa aún menos de lo que se creía.** 27 herramientas arrancan en 1,2 s; `ffmpeg-mcp-lite` en 0,82 s en caliente. **No correlaciona con el tamaño del catálogo, sino con lo que el servidor importa.** Un FileX que delegue en ffmpeg e ImageMagick nativos arrancará en ~1 s.

**(d) El oráculo de existencia de la referencia oficial** es solo interior a la lista blanca, no general.

### 9.3 Refutada

`analysis/00-mcp-patrones.md` afirma literalmente:

> «Y para salidas binarias — un MP4, un PNG — el patrón sencillamente no existe.»

**Es falso.** Existe, está publicado en npm, y está a un booleano de distancia. Ver §3.

**Reescritura propuesta de la regla 1:**

1. **Devolver ruta + metadatos, nunca el contenido convertido.** «Contenido» incluye el binario **en cualquier codificación**: `ImageContent`/`AudioContent`, `BlobResourceContents`, y **también base64 embebido en un `TextContent` o en un campo JSON**, que es la forma en que aparece de verdad en el ecosistema.
2. **El criterio operativo es el tamaño de la respuesta, no su tipo.** Toda respuesta debe caber en **≤200 tokens** salvo `inspect`. Si supera ese presupuesto, es un fallo de diseño, con independencia del tipo de contenido.
3. **No hay excepción por tamaño para las imágenes.** Se evaluó explícitamente. A 0,93 tok/byte el umbral está en 1-2 KB.

---

## 10. Las 15 reglas de confinamiento

**Esta lista sustituye a `PLAN-ORQUESTADOR.md` §4.6.** El detalle y la evidencia de cada una están en `bench/mcp-refs-confinamiento.md` §8.

| # | Regla | Evidencia |
|---|---|---|
| **R1** | **Predicado léxico antes de tocar el disco. Sin excepciones** | Es lo único que separa a `filesystem` (no es oráculo fuera) de `kordoc` (enumera el disco) |
| R2 | Comparar por **segmentos**, nunca por prefijo de cadena | `permitido_secreto` denegado con raíz `permitido`, gracias al `+ path.sep` |
| R3 | Aplicar `normcase`; rechazar raíces que normalicen a la raíz de una unidad | 5 falsos negativos medidos en Windows |
| **R4** | **Un mensaje opaco y constante** para denegado y no-existe: sin ruta, sin ruta resuelta, sin lista blanca | Tres fugas distintas medidas. **Y mantener la equivalencia en la latencia** |
| R5 | La misma opacidad **por elemento** en las operaciones por lotes | 6 rutas → 6 mensajes → 419 tokens |
| R6 | Denegar por defecto; ninguna raíz accesible = no arrancar | `kordoc` sin `KORDOC_ROOT` no confina nada |
| R7 | Resolver enlaces **en cada llamada** y validar la ruta resuelta | El vector del encargo quedó refutado por esto |
| R8 | Copiar la entrada a un **staging privado** tras validarla; al motor externo solo la ruta del staging | La ventana de FileX son **minutos** y quien lee es otro proceso que no conoce la lista blanca |
| R9 | Raíz de lectura ≠ raíz de escritura; no sobrescribir en silencio | Una sola lista para las 14 herramientas; `write_file` destruyó el fichero y su ADS |
| **R10** | **La validación vive en el núcleo, no en la superficie** | La CLI de kordoc ignora `KORDOC_ROOT`. FileX tiene cuatro superficies |
| R11 | El tipo real se decide por **contenido**, no por extensión | En un conversor la extensión **elige el motor** |
| R12 | Normalizar el nombre de salida; prohibir ADS, nombres reservados, puntos y espacios finales | **W9 concedió acceso a un ADS.** Renombrar a nombre opaco en el staging cierra además la inyección de opciones |
| R13 | Los *roots* del cliente se **intersecan** con la lista del servidor, no la reemplazan | `index.ts:181` sustituye. **PENDIENTE:** verificar `list_roots()` en el SDK Python |
| R14 | El error nombra la **capacidad** que falta, nunca el **comando** que la instala | kordoc responde con su propia CLI; docling con `pip install` |
| R15 | Describir `path` como si el modelo no supiera nada | Las 14 herramientas declaran `"path": {"type":"string"}` sin descripción |

---

## 11. Qué se lleva FileX

**90 componentes catalogados** en `analysis/00-mcp-componentes.md`, con `fichero:línea`:

| Veredicto | Filas |
|---|---:|
| COPIAR TAL CUAL | 22 |
| ADAPTAR | 27 |
| SOLO REFERENCIA | 11 |
| DESCARTAR | 30 |

Por repo: `servers` 40 · `ffmpeg-mcp-lite` 15 · `image-worker-mcp` 12 · `kordoc` 9 · `video-audio-mcp` 4 · `markitdown_mcp_server` 3.

### Los tres de mayor valor

1. **El confinamiento completo de `filesystem`** — `path-validation.ts:11-86` + `lib.ts:99-140` + `index.ts:41-88`, con ~1.000 líneas de tests. Porte a Python de ~1 día que sustituye a un diseño desde cero.
2. **`describeError` de kordoc** (`src/mcp.ts:84-100`) — la única pieza del carril que reconoce que el modelo necesita un texto distinto del que necesita una persona.
3. **La estructura `tools/<dominio>.py` de `ffmpeg-mcp-lite`** — 8 herramientas en 2.322 tokens frente a 27 en 7.964 cubriendo el mismo dominio.

Y su `tests/` sigue siendo una plantilla válida, aunque **la afirmación de que era el único con suite de pruebas es falsa**: `video-audio-mcp/tests/test_video_functions.py` tiene 763 líneas y 29 tests.

---

## 12. Correcciones a los documentos maestros

Las tres primeras afectan a decisiones, no a redacción. **Ninguna está aplicada todavía.**

| # | Qué | Dónde hay que corregirlo |
|---|---|---|
| 1 | **`modelcontextprotocol/servers` NO es MIT.** Su `LICENSE` declara transición MIT→Apache-2.0; las contribuciones sin consentimiento siguen bajo MIT. **Apache-2.0 obliga a preservar avisos y adjuntar `NOTICE`** | `ANALISIS-COMPLETO.md`, `analysis/00-licencias.md` (ni lo lista), `analysis/00-mcp-filesystem.md` |
| 2 | **La lista blanca de raíces NO «hay que inventarla»** — desmentido dos veces y aún sin corregir en el documento que se lee al implementar. La corrección es **parcial**: el mensaje opaco y todo lo relativo a procesos externos y contenido hostil sí es trabajo propio | `PLAN-ORQUESTADOR.md` §4.6 → sustituir por las 15 reglas de §10 |
| 3 | **El contrato de verificación necesita un cuarto punto**: propiedades **pedidas** frente a obtenidas | `PLAN-ORQUESTADOR.md` §4.2, `HUECOS.md` §1 |
| 4 | **La regla 1 de patrones está mal redactada** (§9.3) | `analysis/00-mcp-patrones.md` |
| 5 | **`cleanup_memory()` de docling-mcp se cita como modélico** y `bench/mcp-ergonomia.md` regla 14 ya midió que es un `gc.collect()` que no libera VRAM | `analysis/00-mcp-patrones.md` |
| 6 | **§4.4 se contradice consigo mismo**: «un motor nuevo = una herramienta» frente a «cuatro herramientas». Lo primero es el mecanismo que produce las 27 planas de `video-audio-mcp`. Resolución propuesta: del registro se generan los **`enum`**, no las herramientas | `PLAN-ORQUESTADOR.md` §4.4 |
| 7 | Erratas menores: `ffmpeg-mcp-lite` tiene 8 herramientas (no 6); no es el único con tests | este documento las recoge ya corregidas |

---

## 13. Lo que queda pendiente

| Pendiente | Por qué importa |
|---|---|
| **El efecto de un catálogo grande sobre la *elección* del modelo** | Se midió el coste en tokens, nunca el comportamiento. Sigue sin medirse en todo el proyecto |
| **Repetir la fase B del TOCTOU en Linux/WSL** | En Windows el 79 % de los intentos del atacante falló por bloqueo de fichero |
| **Verificar `list_roots()` en el SDK Python de MCP** | Bloqueante del diseño de *roots* (R13) |
| **Medir la ventana TOCTOU real de FileX** | Entre validar y que ffmpeg termine de leer pasan minutos (R8) |
| La suite de `image-worker-mcp` | Requiere `npm install` completo |
| El coste de la validación en Python sobre rutas de 1.000 componentes | — |

---

## 14. Índice de la evidencia

| Ruta | Contenido |
|---|---|
| `analysis/00-mcp-componentes.md` | 90 componentes → veredicto, con `fichero:línea` |
| `bench/mcp-refs-multimedia.md` | Catálogos, caso binario, solapamiento, errores, verificación de salidas |
| `bench/mcp-refs-confinamiento.md` | Ataques, oráculo, TOCTOU, kordoc, y las 15 reglas con su evidencia |
| `bench/salidas-mcp-refs/multimedia/` | Specs, JSON de resultados, salidas convertidas |
| `bench/salidas-mcp-refs/confinamiento/` | Sandbox, 7 bloques de pruebas, logs de la carrera |
| `bench/scripts/mcp_probe_bin.py` | El arnés del caso binario |
| `bench/salidas-mcp/mcp_probe.py` | El arnés documental, intacto |
| `bench/mcp-ergonomia.md` | La fase documental previa: markitdown-mcp y docling-mcp, 16 reglas |
| `analysis/00-mcp-filesystem.md`, `00-mcp-multimedia.md` | Los análisis de código de origen (146 KB) |
| `analysis/00-mcp-patrones.md` | Reglas MCP vigentes — **pendiente de las correcciones de §12** |
