# FileX — Resultados de las pruebas sobre `repos/mcp-refs/`

**Fecha:** 20 de agosto de 2026 · **revisado el 21 de agosto de 2026 (03:30)**
**Estado:** categoría cerrada. Fase 1 (lectura) y fase 2 (ejecución) completadas. **Fase 3 (cabos y conducta) integrada:** `bench/mcp-cabos-sueltos.md` y `bench/saturacion-herramientas.md` cierran **5 de los 6 pendientes de §13** y añaden §9.4 y §12.1.

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

### Pregunta 2 — ¿Cuántas herramientas saturan al modelo? · **CERRADA el 21/08/2026, y la respuesta es «ninguna, en este rango»**

**MEDIDO** con **540 ejecuciones independientes** (`bench/saturacion-herramientas.md`): Haiku 4.5 ×10 repeticiones y Sonnet 4.5 ×5, sobre 12 tareas en cuatro estratos y tres catálogos, con `claude -p` en proceso nuevo, `--tools ""` (ninguna herramienta interna) y un servidor de sonda que sirve los catálogos **exactos** capturados de los servidores reales y **no ejecuta ffmpeg**.

| | **A · 27 herr.** (7.886 tok) | **C · 14 herr.** (4.749 tok) | **B · 8 herr.** (2.306 tok) |
|---|---:|---:|---:|
| Haiku — acierto estricto / permisivo | 93 % / **100 %** | 100 % / 100 % | 82 % / **85 %** |
| Haiku — **elección trampa** | **0 %** | 0 % | **15 %** |
| Sonnet — acierto estricto / permisivo | 90 % / **98 %** | 93 % / 93 % | 68 % / **77 %** |
| Sonnet — **elección trampa** | **2 %** | 7 % | **17 %** |

> **El catálogo de 27 no eligió peor que el de 8. Eligió mejor**, p < 0,001 en los dos modelos (Fisher exacto bilateral, acierto permisivo). Y el contraste limpio **A (27) vs C (14 = A menos las 13 subsumidas, mismo autor y mismo estilo)** no muestra diferencia una vez se quita la única tarea cuya clave de corrección era un juicio discutible del autor: **100 % vs 100 %** en los dos modelos.

**Tres consecuencias, todas MEDIDAS:**

1. **El objetivo de cuatro herramientas de FileX se sostiene, pero SOLO por coste.** El segundo argumento independiente que se buscaba —el conductual— **no existe**.
2. **El catálogo se paga en cada turno: ×2,0–2,6.** 7.886 tokens de catálogo → **≈19.000–23.600 tokens de entrada por petición** sencilla; 2.306 → ≈8.800. El intercambio típico fueron **2,1 turnos**. **El presupuesto de ≤1.200 tokens de §4 son ≈2.400–3.100 por petición.**
3. **El riesgo va en dirección contraria: un catálogo demasiado escueto produce FALLOS SILENCIOSOS.** Ver §3.5 del informe y la §13 de este documento.

**La predicción estructural más fuerte del proyecto no se cumplió.** `bench/mcp-refs-multimedia.md` §5.2 declaró `set_audio_bitrate` / `set_video_audio_track_bitrate` «el peor par» del catálogo —nombres casi idénticos, descripciones con similitud 0,88, y la equivocación no da error—. **Acertó 30 de 30**, con pista y sin ella. **La ambigüedad léxica de un catálogo es un indicador de mala higiene de interfaz, no un predictor de errores de elección**, y este informe es la evidencia de que no hay que confundir las dos cosas.

**Lo que NO demuestra, dicho por el propio informe (§6.3, §8):** nada sobre 60 o 200 herramientas, ni sobre varios servidores MCP a la vez, ni sobre modelos de otras familias o locales pequeños. Con n=120 por celda **no detecta caídas de 2-3 puntos**: «no se detectó diferencia con esta potencia» no es «no hay diferencia». Y **la temperatura no es fijable desde el CLI**: es la limitación más seria del instrumento y solo se arregla con una clave de API, que no existe en esta máquina. **PENDIENTE.**

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

#### Precisión del 21/08/2026: los 0,93 tok/B son de UNA de las dos vías — MEDIDO

`bench/mcp-cabos-sueltos.md` §1.3 midió la otra contra el cliente real. **Un `ImageContent` nativo no cuesta por byte: cuesta por píxel.**

| Vía | `tipico.png` (42.855 B, 1920×1080) |
|---|---:|
| base64 dentro de un `TextContent` (0,93 tok/B) — el **contenido encubierto** de §3 | ~39.855 tok |
| **`ImageContent` nativo (MEDIDO en A/B, `cache_creation_input_tokens`)** | **~2.814 tok** |
| asa (ruta + metadatos) | **32-72 tok** |

La predicción del modelo de coste por píxel `w×h/750` da **2.765** para 1920×1080: coincide. Y con un PNG de **1×1** el modelo recibió un marcador de error de la API de visión (`invalid_request_error: Could not process image`), **no** una cadena base64: el bloque se enrutó **como imagen**.

> **La conclusión no cambia, se refuerza en el sitio correcto.** El `ImageContent` nativo es **×14 más barato** que el antipatrón encubierto y aun así **×39 a ×88 más caro que devolver la ruta**. **Sigue sin haber umbral que justifique devolver la imagen**, y sigue siendo cierto que el criterio operativo debe ser **tokens de respuesta**: es lo único que captura las dos vías.

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

### El multiplicador que le faltaba al presupuesto: ×2,0–2,6 — MEDIDO (21/08/2026), **RE-ACOTADO el 22/08/2026**

`bench/saturacion-herramientas.md` §3.6 midió lo que cuesta de verdad un catálogo, y **no es su tamaño: es su tamaño por turno.**

| Modelo | Catálogo | `tokens_catalogo` | **Tokens de entrada por petición** | Turnos medios |
|---|---|---:|---:|---:|
| Sonnet | A (27) | 7.886 | **23.583** | 2,12 |
| Sonnet | C (14) | 4.749 | **15.734** | 2,18 |
| Sonnet | B (8) | 2.306 | **8.826** | 2,23 |
| Haiku | A (27) | 7.886 | **19.182** | 2,08 |
| Haiku | C (14) | 4.749 | **12.869** | 2,08 |
| Haiku | B (8) | 2.306 | **8.264** | 2,17 |

> **La regla de ≤1.200 tokens se confirma y se le añade la cifra que le faltaba: un catálogo de 1.200 tokens costará ≈2.400–3.100 tokens de entrada por petición sencilla.** Ese, y no 1.200, es el número que hay que comparar con el resto del presupuesto de contexto.
>
> *(Las cifras de Haiku para B están afectadas por un reparto desigual de aciertos de caché entre ejecuciones concurrentes; las de Sonnet son limpias. El recuento propio del informe da 7.886 y 2.306 frente a los 7.964 y 2.322 publicados aquí: **1 % por debajo**, por un detalle de serialización, y **la proporción entre catálogos es la misma**.)*

> ### ⚠️ Re-acotado: ese ×2,0–2,6 es del **régimen ansioso**, y el despliegue real de FileX no está en él — MEDIDO (`bench/mcp-cabos-2.md` §4)
>
> Las cifras de arriba se midieron con `--tools ""` y pocas herramientas. **En una sesión normal de Claude Code, donde el servidor de FileX convive con las ~15 herramientas internas, el catálogo llega DIFERIDO: solo los nombres.**
>
> Dos catálogos con **los mismos 6 nombres y esquemas** y descripciones que difieren en ~3.300 tokens:
>
> | Condición | Herramientas internas | Catálogo | **Total de entrada (tok)** |
> |---|---|---|---:|
> | `pmin_pesado_deftools` | **sí** (sesión real) | pesado | **26.941** |
> | `pmin_ligero_deftools` | **sí** (sesión real) | ligero | **26.941** |
> | `pmin_pesado_notools` | no (`--tools ""`) | pesado | 11.188 |
> | `pmin_ligero_notools` | no (`--tools ""`) | ligero | 7.890 |
>
> **26.941 = 26.941.** Las ~3.300 tokens de descripciones **no llegan al contexto**. Y el modelo lo dice con todas las letras: *«el system-reminder indica explícitamente que "Their schemas are NOT loaded", así que solo veo los nombres»*. Con `--tools ""` sí pega la descripción pesada entera.
>
> **Tres matices para no sobre-corregir:**
> - **El coste no es cero.** Los **nombres** sí se inyectan en cada turno, y hay un `tools/list` por sesión. Lo que sale del camino caliente es el **cuerpo** —descripciones y esquemas—, que es justo lo que medía el presupuesto. **El ≤ 1.200 tokens sigue valiendo como higiene de NOMBRES**, no como multiplicador por turno.
> - **Es comportamiento de UNA versión** (Claude Code 2.1.238) y depende del número **total** de herramientas de la sesión, no solo de las de FileX. Con **40** herramientas y `--tools ""` el catálogo ya sale **truncado**, no diferido. **La carga ansiosa es un régimen de catálogo pequeño.** Si alguien conectara solo FileX con `--tools ""`, volvería a él: **el diseño no debe apostar todo a la diferición**.
> - **La otra cara no cambia:** un catálogo demasiado escueto produce **fallos silenciosos (15–17 %)**. La diferición abarata el catálogo grande; **no** rehabilita recortar la cobertura de `convert`.

### El tercer dato incómodo, y es nuevo: **0 de 193 parámetros lleva descripción** — MEDIDO

`bench/saturacion-herramientas.md` §5.4, determinista y sin modelo: de los **102 parámetros de `video-audio-mcp`, los 63 de su versión reducida y los 28 de `ffmpeg-mcp-lite`, ninguno lleva `description` en su JSON Schema.** Solo un `title` autogenerado (`"input_audio_path"` → `"Input Audio Path"`), que no añade nada. **FastMCP deriva el esquema de las anotaciones de tipo y deja toda la semántica en la prosa del docstring.**

Eso convierte un defecto parcial en total: `add_b_roll` declara como obligatorio un `array` de `object` con `additionalProperties: true` **sin una sola clave**, y su descripción dice *«Args listed in previous messages»*. **Entre esquema y descripción, la información disponible para construir la llamada es cero.**

> **Para FileX es innegociable: cada parámetro lleva su `description` en el esquema** (`Field(description=…)` o equivalente), incluidos los `enum` generados desde el registro.

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

> ### Un QUINTO punto, medido desde otro carril el 21/08 (`bench/aristas-nominales.md` §5.2)
>
> **Hay motores que escriben fuera del destino, y uno de ellos escribe en el `cwd` del proceso.** Reproducido de forma controlada con la invocación exacta de ConvertX:
>
> | Orden | Escribe en el destino | Escribe **también** |
> |---|---|---|
> | `ffmpeg -i trivial.mp4 DEST/t.mpd` | `t.mpd` (**1 234 B**) | **`init-stream0.m4s` (814 B) y `chunk-stream0-00001.m4s` (528 447 B) en el DIRECTORIO DE TRABAJO** |
> | `magick trivial.png -auto-orient DEST/u.html` | `u.html` (506 B) **y `u.png` (329 B)** | **`u_map.shtml` (98 B) en el DIRECTORIO DE TRABAJO** |
>
> **La arista `vídeo → mpd` entrega un manifiesto DASH válido de 1,2 KB que no lleva el contenido y pasa los cuatro puntos del contrato.** Y **una salida puede ser varios ficheros**: devolver solo el declarado entrega un documento roto, y una sonda que juzga **un** fichero no puede verlo.
>
> **Quinto punto: «¿el motor escribió algo fuera de lo declarado?»** Se implementa listando el directorio de trabajo antes y después. **Y tiene consecuencia de confinamiento, no solo de verificación:** `RESULTADOS-MCP.md` §10 (R8, R16) y `PLAN-ORQUESTADOR.md` §4.6 diseñan el staging **asumiendo que el motor escribe donde se le dice**. Estos dos no. → **regla R18: directorio de trabajo propio y desechable por conversión** (§10).

> ### El quinto punto, IMPLEMENTADO Y MEDIDO el 21/08 a las 14:00 (`bench/contrato-quinto-punto.md` §2, §3)
>
> **Cuesta 0,047 ms — el +11,0 % del contrato, que pasa del 0,032 % al 0,036 % de convertir— y entra en el camino caliente. Pero solo con R18:** sin directorio de trabajo desechable, sobre un directorio real de **1 000 ficheros**, censar antes y después cuesta **3,66 ms, ×8,6 el contrato entero**. **Eso convierte R18 de higiene en requisito de coste** (§10).
>
> **Falsos positivos sobre el patrón oro: CERO** (39 órdenes reejecutadas en directorio desechable). **Y 0 avisos en las tres salidas legítimamente multifichero** —HLS, dos secuencias `%d`—, con el **fallo mantenido en el DASH incluso declarando `multifichero: true` en el pedido**, porque sus segmentos van al `cwd` y no junto al manifiesto. **Declarar que una salida son varios ficheros no autoriza a escribir donde sea.**
>
> **El disparador es la UBICACIÓN, no el reparto de bytes:** un manifiesto HLS legítimo lleva **el 0,0 % de los bytes** igual que el `.mpd` roto, así que un detector por tamaño **marcaría toda salida en streaming como fallo**. El reparto solo decide la **severidad**.
>
> > **Y su coste honesto es un cambio de naturaleza, no de precio: sin censo, 49 de las 53 salidas bajan de `ok` a `ok_parcial`.** No es un falso positivo: **el punto 5 es el primero del contrato que NO es verificable a posteriori**, y eso es un argumento de arquitectura — **la verificación tiene que vivir dentro de la conversión.**
>
> **Comprobación cruzada, desde el carril de las aristas: 0 fugas en 118 aristas** con `cwd` desechable y listado antes/después (`bench/invocacion-aristas.md` §7.4). **No refuta el hallazgo: confirma que era específico.** Los dos casos de fuga tienen destinos —`mpd`, `html`— que **no aparecen entre las aristas nominales de aquella muestra**, porque no fallaban: **entregaban un fichero incompleto**. **Fuga y fallo son poblaciones disjuntas**, y por eso ni los cuatro puntos ni el juez de aristas las ven.

> ### Y un caso que **ningún** punto del contrato atrapa — MEDIDO (`bench/aristas-nominales.md` §8.2)
>
> **`resvg 0.46.0` devuelve `rc=0`, un PNG de firma válida y geometría exacta, y sin una sola letra** al rasterizar un SVG con dos bloques de texto: **0,00 % de tinta en la banda de texto** frente al 14,02 % de Inkscape y el 15,07 % de `magick`. Lo único que lo delata está en `stderr`. **Es el octavo fallo de verificación del catálogo de `HUECOS.md` §1 y el primero que el contrato no atrapa:** el contrato juzga la **declaración** de la salida, y **el contenido que desaparece sin dejar rastro en ninguna propiedad declarada solo se ve comparando la salida con la entrada** — es decir, en la fidelidad, no en el contrato. **Delimita el diferenciador nº 1; no lo invalida.**
>
> **Actualización del 21/08 a las 14:00 (`bench/contrato-quinto-punto.md` §4, §5): la regla que lo atrapa existe y `resvg` NO era un caso aislado.**
>
> - **I9** —*si el SVG de origen tiene `<text>`, la salida rasterizada debe tener tinta donde estaban*— **discrimina 6 de 6 con margen binario**: 0,00 % frente a 20,01 % (Inkscape) y 23,61 % (`magick`), sin un falso positivo en tres controles. **Pero cuesta 32–59 ms a 400×200 y 2 454 ms a 1920×960: la estimación de «del orden de 26 ms» se quedaba corta ×94, y confirma que la regla vive en el grupo C y no en el contrato.**
> - **La familia tiene al menos cinco miembros** en cinco modalidades: SVG sin fuentes, vídeo con envase correcto y todo negro (**5,39 dB**, y solo `aviso`), PDF de texto rasterizado, CSV→JSON que pierde una columna, y audio con un canal silenciado. **El contrato atrapa uno, I9 otro, y uno sigue sin cubrir**: el canal silenciado hacia un destino **con pérdida** (el mismo fallo hacia FLAC sí lo atrapa A4). **PENDIENTE.**
> - **Y el acotamiento que este documento escribió queda CONFIRMADO, con formulación precisa:** *el contrato atrapa la pérdida cuando el contenido perdido está **declarado en metadatos**, porque la sonda ya los lee para los puntos 2, 3 y 4; necesita fidelidad cuando el contenido solo existe como **píxeles o muestras**.* La prueba en el otro sentido está medida: **el miembro cuyo contenido sí está declarado —el CSV— lo atrapa el CONTRATO, no la fidelidad.** **Se planteó como posible excusa y la medición lo confirmó como arquitectura.**
> - **Un sexto candidato, por un camino independiente** (`bench/invocacion-aristas.md` §4.1): este ImageMagick es **Q16-HDRI y escribe los crudos a 16 bits/canal**; releerlos con `-depth 8` **no falla**, entrega la geometría correcta y **píxeles basura**, y **pasa los cuatro puntos**. **Dos vías independientes llegando al mismo patrón.**

> **Y un hueco del contrato que los cuatro puntos NO cubren — MEDIDO el 21/08 (`bench/mcp-cabos-sueltos.md` §5.2 y §5.6).** Si un tercero **escribe en sitio** sobre la entrada mientras el motor la lee, ffmpeg produce una salida **internamente coherente** y devuelve **`returncode 0`**: la ruta sigue siendo la validada, el inodo también, `realpath` sigue dando lo mismo, **y los bytes son otros**. Un verificador que compruebe «es un MP4 válido con la duración esperada» lo da por bueno. **Es el mismo tipo de fallo que el WebP ampliado ×9,75 de §7, y refuerza el mismo punto: la coherencia interna de la salida no prueba que la entrada fuera la que se validó.** La defensa **no es un quinto punto de verificación**: es **hacer el hash de la entrada en el staging (R8) y no volver a mirar el original**.

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

De las 27 herramientas: 1 no toca ffmpeg, **24 usan solo `ffmpeg-python`** (15 en su cuerpo + 9 delegando en `_run_ffmpeg_with_fallback`) y 2 son mixtas. ~~Reproducido end-to-end en **una**; el resto es el mismo mecanismo, marcado **PENDIENTE**.~~ **Actualizado el 21/08/2026 (`bench/mcp-cabos-sueltos.md` §4): reproducido en 6 de las 26 que tocan ffmpeg**, y la clasificación de las 27 pasa de recuento manual a **AST reproducible** (`cabo4_clasificar.py`, que confirma **cero `overwrite_output()` y cero `stdin=` en todo el fichero**). El contraste es de tres órdenes de magnitud: **554-695 ms si la ruta de salida es nueva, infinito si ya existe.** ~~Las 20 restantes quedan cubiertas por la clasificación, **no por ejecución**: eso sigue siendo PENDIENTE.~~ **CERRADO el 22/08/2026 (`bench/mcp-cabos-2.md` §1): 26 de 26 por EJECUCIÓN, cero excepciones.** Las 20 restantes se ejecutaron una a una con la salida preexistente y timeout duro de 18 s: **18 colgaron directamente y 3 respondieron en <105 ms con la basura intacta** — fallos *tempranos* por entradas mías, no defensas del código. Corregida la causa (fuente sin pista de audio en dos; `target_format="mkv"`, que ffmpeg no conoce —el nombre válido es `matroska`— en la tercera), **las tres cuelgan también**. **Y el matiz que delimita dónde el `_run_ffmpeg_with_fallback` lo enmascara: convierte el deadlock en error SOLO cuando ffmpeg falla antes de llegar al muxer.** En cuanto el formato es válido y el grafo escribe, el deadlock reaparece.

> **El mismo fichero sabe pasar `-y` en una vía y se le olvida en la otra.** No es que sus autores ignoraran el problema: lo resolvieron en un sitio y lo olvidaron en otro.
>
> **Regla nueva:** todo subproceso corre con **`stdin=DEVNULL`**, con las banderas no interactivas (`-y`, `-nostdin`), con timeout del lado del servidor, y matando el **árbol** de procesos. **El orden importa: `stdin=DEVNULL` primero, las banderas después** — una disciplina que hay que recordar en cada punto de invocación no es una defensa; hay que cerrarla en la construcción del proceso, donde ninguna vía pueda saltársela.

#### La nota de orden es un RESULTADO CAUSAL MEDIDO: `-y` es necesario y **NO suficiente** (21/08/2026)

`bench/mcp-cabos-sueltos.md` §4.3. La rama de `subprocess` de `concatenate_videos` pasa `-y` en sus 7 invocaciones y **aun así se colgó 2 de 3 veces**, sobre una ruta temporal recién creada que **no existía**: el prompt de sobrescritura no podía ser la causa. El A/B decisivo, **dentro de una sesión MCP real**, con dos herramientas idénticas salvo en una línea, `-y` en todas partes y rutas de salida nuevas:

| Herramienta | Diferencia | Colgadas |
|---|---|---:|
| `conv_heredado` | `stdin` **no se toca** → hereda la tubería JSON-RPC | **2/5** |
| `conv_devnull` | **`stdin=subprocess.DEVNULL`** | **0/5** |

**Y la variable que lo dispara es más estrecha de lo que parecía: no es «una tubería», es la tubería que el servidor MCP está leyendo a la vez.** Fuera de MCP, con tuberías mudas, 0 de 15 secuencias colgaron. **El hijo y el bucle de lectura del servidor compiten por el mismo descriptor.**

> **Cambia el estatus de la regla: `stdin=DEVNULL` no es «además de» las banderas, es LA defensa; las banderas son higiene.** Una revisión que se conforme con «¿lleva `-y`?» da por bueno un código que cuelga la sesión el 40 % de las veces. Y **`-nostdin` tampoco basta por sí solo**: empata con `-y` en los controles, pero es **otra bandera que hay que acordarse de poner en cada punto de invocación**. `stdin=DEVNULL` en el constructor del proceso no se puede olvidar, **porque no hay puntos de invocación: hay uno**.

**Y matar el árbol no siempre alcanza al nieto — MEDIDO:** un `ffmpeg.exe` sobrevivió a un `taskkill /F /T` sobre el servidor y hubo que matarlo por inventario. **FileX necesita inventario explícito de los procesos que lanza** (job object en Windows, grupo de procesos en POSIX), no confiar en la relación padre-hijo.

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
| Devolver ruta + metadatos, nunca contenido | El asa cuesta 32-72 tok e **independiente del tamaño**; inyectar cuesta **0,93 tok/byte** en base64 dentro de texto y **~2.814 tok** por `ImageContent` nativo de 1920×1080 (§2, pregunta 6) |
| Anotar `readOnlyHint` / `destructiveHint` — **MATIZADA el 21/08** | **0 de 3** anotan. Solo docling, de 5 servidores sondeados. **Pero MEDIDO contra Claude Code 2.1.238: las anotaciones NO llegan al modelo ni cambian el permiso** (§9.4). La regla sigue valiendo; **la advertencia de seguridad va en la `description` y la defensa en el núcleo (R10)** |
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

*(Aplicada en `analysis/00-mcp-patrones.md` el 20/08 y ampliada el 21/08 con el coste por píxel del `ImageContent` nativo.)*

### 9.4 Lo que el cliente real NO le pasa al modelo — MEDIDO el 21/08/2026

`bench/mcp-cabos-sueltos.md` §1.2, preguntándole al propio Claude Code 2.1.238 qué veía en su catálogo:

| Lo que el servidor declara | ¿Llega al modelo? |
|---|---|
| `description` | **Sí**, literal |
| `inputSchema` (`parameters`) | **Sí**, literal |
| `annotations.readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` | **No** |
| `annotations.title` y el `title` de la herramienta | **No** |
| `_meta` | **No** |
| `outputSchema` | **No** |
| `icons` | **No** |
| **Los `resources` y los `prompts` declarados** | **No** — MEDIDO el 22/08 |

La prueba limpia es una herramienta declarada `destructiveHint=true`: **el modelo supo que era destructiva solo porque el autor lo escribió dentro de la descripción.** En palabras del propio cliente: *«Las anotaciones del protocolo no cruzan hasta el modelo; solo cruza la descripción.»* Y **tampoco cambian el permiso**: una herramienta `readOnlyHint=true, destructiveHint=false` fue **denegada igual** con el modo de permisos por defecto.

Esto confirma por otra vía el dato incómodo de §4: **`structuredContent` tampoco compra nada del lado del modelo.** Una herramienta con `structured_output=True` y un `outputSchema` real entregó una línea de texto indistinguible de un `TextContent` con el mismo JSON serializado a mano, **y sin el `outputSchema` a la vista**.

> **Qué cambia:** la regla de anotar sigue siendo correcta y barata, y otros clientes pueden usarla. **Pero no puede ser el sitio donde vive una advertencia de seguridad.** Lo que el modelo lee es la `description`; lo que impide una operación prohibida es el núcleo (R10).

#### La lista crece: los **recursos** y los **prompts** tampoco cruzan — MEDIDO el 22/08/2026

`bench/mcp-cabos-2.md` §3, con un servidor de sonda que declara `capabilities.resources` y `capabilities.prompts`, **un recurso** (`filex://probe/nota`) y **un prompt** (`filex_probe_prompt`), y registra toda lectura. **Hay que separar dos hechos:**

1. **El CLIENTE sí los enumera.** Cada sesión muestra `resources/list` (n=1) y `prompts/list` (n=1) justo después de `tools/list`. Esto **actualiza** la observación de `mcp-cabos-sueltos.md` §1.7 («registró cero lecturas»): *no era que el cliente no preguntara; es que no se le había pedido al modelo que los usara*.
2. **Pero el MODELO no los ve.** En las dos condiciones —con y sin herramientas internas— la respuesta literal fue **«NINGUNO — no veo recursos MCP ni prompts MCP disponibles en mi contexto actual»**.

> **Declarar recursos y prompts es COSTE SIN RETORNO**, exactamente como las anotaciones. **FileX no gasta catálogo en ellos** con Claude Code como cliente objetivo. Si algún día quiere ofrecer datos «tirados por el servidor», tendrá que hacerlo **como herramienta**, que es el único canal que el modelo ve.

---

## 10. Las 15 reglas de confinamiento, **más una decimosexta medida el 21/08**

**Esta lista sustituye a `PLAN-ORQUESTADOR.md` §4.6.** El detalle y la evidencia de cada una están en `bench/mcp-refs-confinamiento.md` §8. *(La numeración R16/R17/R18 de `PLAN-ORQUESTADOR.md` §4.6 incluye además las dos de `bench/confinamiento-multimedia.md` §6; aquí se añade solo la nueva.)*

| # | Regla | Evidencia |
|---|---|---|
| **R1** | **Predicado léxico antes de tocar el disco. Sin excepciones** | Es lo único que separa a `filesystem` (no es oráculo fuera) de `kordoc` (enumera el disco) |
| R2 | Comparar por **segmentos**, nunca por prefijo de cadena | `permitido_secreto` denegado con raíz `permitido`, gracias al `+ path.sep` |
| R3 | Aplicar `normcase`; rechazar raíces que normalicen a la raíz de una unidad | 5 falsos negativos medidos en Windows |
| **R4** | **Un mensaje opaco y constante** para denegado y no-existe: sin ruta, sin ruta resuelta, sin lista blanca | Tres fugas distintas medidas. **Y mantener la equivalencia en la latencia** |
| R5 | La misma opacidad **por elemento** en las operaciones por lotes | 6 rutas → 6 mensajes → 419 tokens |
| R6 | Denegar por defecto; ninguna raíz accesible = no arrancar | `kordoc` sin `KORDOC_ROOT` no confina nada |
| R7 | Resolver enlaces **en cada llamada** y validar la ruta resuelta. **En Linux, además, `O_NOFOLLOW` + `dir_fd` segmento a segmento** | El vector del encargo quedó refutado por esto. **MEDIDO (21/08):** en Windows **no existen** `O_NOFOLLOW`, `O_PATH`, `dir_fd` ni `/proc/self/fd`. Complemento de la validación, **nunca sustituto del staging** |
| R8 | Copiar la entrada a un **staging privado** tras validarla, **inmediatamente**; al motor externo solo la ruta del staging. **Excepción explícita: `inspect`, que además queda exento de R18** | **MEDIDO (21/08):** la ventana es el **99,6 % de la conversión**; el vector que funciona **no es sustituir sino escribir en sitio**; el precio es **0,1 %-19,6 %**. **Y la excepción, con número (22/08, `bench/mcp-cabos-2.md` §5.2-5.3):** el `inspect` en proceso cuesta **0,04–0,06 ms** y el staging que R8 le impondría, de **1,7 ms (1 MB) a 166 ms (256 MB)** — de **30× a más de 3.000× la operación, a cambio de cero seguridad**, porque una lectura de cabeceras en proceso nunca entrega la ruta a un lector ajeno. **El cruce copia == `ffprobe` no es una constante: `cruce_MB ≈ ffprobe_ms × copia_MBps / 1000`**, y con `ffprobe` ≈ 57 ms sale entre **~70 MB** (disco contendido a 1,2 GB/s) y **~95 MB** (holgado a 1,6 GB/s). El **1,32×** de `cabo5` era el extremo rápido de esa misma fórmula |
| R9 | Raíz de lectura ≠ raíz de escritura; no sobrescribir en silencio | Una sola lista para las 14 herramientas; `write_file` destruyó el fichero y su ADS |
| **R10** | **La validación vive en el núcleo, no en la superficie** | La CLI de kordoc ignora `KORDOC_ROOT`. FileX tiene cuatro superficies |
| R11 | El tipo real se decide por **contenido**, no por extensión | En un conversor la extensión **elige el motor** |
| R12 | Normalizar el nombre de salida; prohibir ADS, nombres reservados, puntos y espacios finales | **W9 concedió acceso a un ADS.** Renombrar a nombre opaco en el staging cierra además la inyección de opciones |
| R13 | Los *roots* del cliente se **intersecan** con la lista del servidor, no la reemplazan | `index.ts:181` sustituye. ~~**PENDIENTE:** verificar `list_roots()` en el SDK Python~~ **CERRADA el 21/08: IMPLEMENTADA**, ocho líneas (`cabo2_roots.py`), demostrada en 4 configuraciones y contra el cliente real. **Y el 22/08 se añade la capacidad que faltaba para cachearlos:** Claude Code 2.1.238 declara `roots.listChanged: true` en su `initialize` (`bench/mcp-cabos-2.md` §2), es decir **se compromete a avisar cuando su lista de roots cambie**. FileX puede cachear los roots por sesión e invalidar con `notifications/roots/list_changed` en vez de llamar a `roots/list` en cada operación. **Observar una emisión real sigue PENDIENTE** —en headless no hay forma de cambiar los roots a media sesión—, pero para el diseño basta: si el cliente nunca emite, la caché no se invalida hasta el fin de sesión, que es el comportamiento correcto por defecto |
| R14 | El error nombra la **capacidad** que falta, nunca el **comando** que la instala | kordoc responde con su propia CLI; docling con `pip install` |
| R15 | Describir `path` como si el modelo no supiera nada | Las 14 herramientas declaran `"path": {"type":"string"}` sin descripción |
| **R18** | **Exento para `inspect`, que no escribe nada y por tanto no tiene censo que hacer.** Para todo lo demás: **un directorio de trabajo propio y DESECHABLE por conversión, con el `cwd` del hijo dentro. Validar la ruta de salida no basta.** Listarlo al terminar, comparar con lo declarado, recoger lo que sí es salida y borrarlo entero. **⚠ Y NO ES HIGIENE: ES REQUISITO DE COSTE — MEDIDO el 21/08 a las 14:00.** Con R18 el punto 5 cuesta **+11,0 %** del contrato; **sin él, sobre un directorio de 1 000 ficheros, ×8,6 el contrato entero** (`bench/contrato-quinto-punto.md` §2.2). **R18 es lo que hace viable el quinto punto** | **MEDIDO el 21/08** (`bench/aristas-nominales.md` §5.2). **`ffmpeg -i x out.mpd` deja 528 KB de segmentos DASH en el `cwd`** y entrega 1,2 KB inútiles; **`magick … out.html` produce dos ficheros en el destino y un tercero en el `cwd`**. Aparecieron como **33 ficheros no pedidos en la raíz del repositorio**. **R8 y R16 asumen que el motor escribe donde se le dice: estos dos no** |

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

> **Precisado el 21/08 con la suite de `image-worker-mcp` ya ejecutada (`bench/mcp-cabos-sueltos.md` §3): no hay un ganador, hay que coger un eje de cada uno.**
>
> - **De `ffmpeg-mcp-lite`, la ESTRUCTURA:** fixtures sintéticas con `lavfi` (`conftest.py:17-61`), `skip` por entorno (`:37-38`), un `test_*.py` por herramienta, y **cero binarios comprometidos en el repo**. Se mantiene el **COPIAR TAL CUAL**.
> - **De `image-worker-mcp`, el CRITERIO DE ASERCIÓN, y ahora hay un ejemplar concreto que copiar** (`tests/tools/sharp.test.ts:369-380`): el test **abre el fichero escrito** y afirma `format`, `width` y `height` reales. En `ffmpeg-mcp-lite`, `test_convert.py:20-23` se conforma con `exists()` más una subcadena de éxito — **un fichero de 0 bytes pasaría**.
> - **Y su reparto:** 117 tests en 6,43 s frente a 32 en 53,19 s es sobre todo que **104 de los 117 no tocan disco ni códecs**. **La gran mayoría rápidos y aislados, unos pocos de integración lenta con ficheros reales** es la forma correcta, y es la única de las dos suites que la tiene. *(Con una salvedad: en `image-worker-mcp` `fs.writeFileSync` está **mockeado** y el test escribe el búfer él mismo, así que **un fallo en cómo la herramienta escribe en disco no lo atraparía**. Para FileX la aserción debe correr sobre **el fichero que escribió el código bajo prueba**.)*
> - **Dato de gobierno, no de calidad:** **75 de los 117 tests (64 %) prueban las tres nubes** —backends de subida, no lógica de conversión— y **solo 13 prueban la conversión de imágenes**. Un `117 passed` verde dice mucho menos de lo que parece.

---

## 12. Correcciones a los documentos maestros

Las tres primeras afectan a decisiones, no a redacción. **Las siete están APLICADAS desde el 21/08/2026** (salvo las partes que dependen de ficheros que no son de este carril; se dice cuáles).

| # | Qué | Estado y dónde quedó |
|---|---|---|
| 1 | **`modelcontextprotocol/servers` NO es MIT.** Su `LICENSE` declara transición MIT→Apache-2.0; las contribuciones sin consentimiento siguen bajo MIT. **Apache-2.0 obliga a preservar avisos y adjuntar `NOTICE`** | ✅ **APLICADA.** `analysis/00-licencias.md` (fila nueva + nota; **no estaba listado**), `ANALISIS-COMPLETO.md` §2.3, §3.2 y §4.3. **Pendiente en `analysis/00-mcp-filesystem.md`**, que es análisis de origen y no se toca |
| 2 | **La lista blanca de raíces NO «hay que inventarla»** — desmentido dos veces y aún sin corregir en el documento que se lee al implementar. La corrección es **parcial**: el mensaje opaco y todo lo relativo a procesos externos y contenido hostil sí es trabajo propio | ✅ **APLICADA.** `PLAN-ORQUESTADOR.md` §4.6 sustituido por una tabla de **18 reglas** (las 15 de §10, más **R16 y R17** de `bench/confinamiento-multimedia.md` §6, más **R18** de `bench/aristas-nominales.md` §5.2), con la parcialidad explícita y la lista de lo que sigue siendo trabajo propio. También corregido `ANALISIS-COMPLETO.md` §6.3, que decía lo mismo |
| 3 | **El contrato de verificación necesita un cuarto punto**: propiedades **pedidas** frente a obtenidas | ✅ **APLICADA.** `PLAN-ORQUESTADOR.md` §4.2 (cuatro puntos + la regla «ninguna transformación no solicitada por defecto») y `HUECOS.md` §1. **Y confirmada por un tercero:** `bench/coste-verificacion.md` midió que el punto 4 son 187 de las 333 líneas del contrato y es lo único que atrapa el caso |
| 4 | **La regla 1 de patrones está mal redactada** (§9.3) | ✅ **APLICADA.** `analysis/00-mcp-patrones.md`: frase original marcada como falsa con lo que se creía y lo que se midió, y regla 1 reescrita con los tres puntos (binario en cualquier codificación · ≤200 tokens como criterio operativo · sin excepción por tamaño para imágenes) |
| 5 | **`cleanup_memory()` de docling-mcp se cita como modélico** y `bench/mcp-ergonomia.md` regla 14 ya midió que es un `gc.collect()` que no libera VRAM | ✅ **APLICADA.** `analysis/00-mcp-patrones.md` regla 4 y el comentario del bloque de código |
| 6 | **§4.4 se contradice consigo mismo**: «un motor nuevo = una herramienta» frente a «cuatro herramientas». Lo primero es el mecanismo que produce las 27 planas de `video-audio-mcp`. Resolución propuesta: del registro se generan los **`enum`**, no las herramientas | ✅ **APLICADA.** `PLAN-ORQUESTADOR.md` §4.4, con el presupuesto medido (**coste por herramienta ×11**, de 79 a 875 tokens; **≤1.200 tokens para las cuatro**). También en `ANALISIS-COMPLETO.md` §7.3 y §7.4 |
| 7 | Erratas menores: `ffmpeg-mcp-lite` tiene 8 herramientas (no 6); no es el único con tests | ✅ **APLICADA.** Este documento las recoge ya corregidas; ningún documento maestro repetía las erratas |

**Cinco correcciones más, de otros carriles, aplicadas en la misma pasada** (no salen de este documento, pero tocan los mismos ficheros y por eso constan aquí):

| Qué | Dónde |
|---|---|
| **El diferenciador nº 2 pasa de «reformulado» a REFUTADO** en su parte multi-salto (`bench/fidelidad-caminos.md`) | `HUECOS.md` §2, `ANALISIS-COMPLETO.md` §1 y §3.4, `PLAN-ORQUESTADOR.md` §1, §4.1 y §7 |
| **Quitar «(`ffprobe`)» del contrato**: verificar en proceso cuesta 145× menos (`bench/coste-verificacion.md`) | `PLAN-ORQUESTADOR.md` §4.2 y §6, `HUECOS.md` §1 |
| **Las marcas de OCR de d2/d3 son un artefacto del arnés** (`bench/ocrmypdf.md`) | Aviso en `bench/gpu-fase2.md` (sin tocar sus cifras), corrección en `HUECOS.md` §5 y `ANALISIS-COMPLETO.md` §5.5, regla y trampa en `PLAN-ORQUESTADOR.md` §5 y §6 |
| **Tesseract: no invocable, pero embebido en Ghostscript sin datos de idioma** (`bench/fidelidad-caminos.md` §0.1) | `PLAN-ORQUESTADOR.md` §2, `HUECOS.md` §5 |
| **`stdin=DEVNULL`, `job_id` al empezar y `mcp>=2.0.0`** (§8 de este documento + `bench/sdk-mcp-capacidades.md`) | `PLAN-ORQUESTADOR.md` §5.1, §5.2 y §5.3 |

**Fichas de `analysis/` que estaban desfasadas — ya corregidas (21/08/2026):**

- `analysis/00-mcp-filesystem.md` — daba `servers` por MIT. Lleva ahora aviso de cabecera con la transición a Apache-2.0 y la obligación de `NOTICE`.
- `analysis/OCRmyPDF.md` — llamaba a su preprocesado «la referencia a imitar». Lleva ahora una sección de **revocación** con lo medido: su preprocesado produce salidas bit a bit idénticas, `--remove-background` lanza `NotImplementedError` y atravesar su ciclo **degrada** el CER de 1,3 % a 44,3 %.
- `analysis/00-mcp-componentes.md` — sus §2 y §3.5 estimaban el catálogo en ≈3 610 / ≈811 tokens por conteo de caracteres. Ambas remiten ahora a las cifras medidas de §4 (**7.964 / 2.322**); la proporción aguanta (3,4× en vez de 4,5×), la magnitud no.

En los tres casos se **conservó el texto original** y se añadió la corrección, para no borrar la historia intelectual: qué se creía por lectura de código, qué se midió al ejecutar, y por qué cambió.

> **Contradicción abierta, que no se ha resuelto porque toca ficheros de otro agente:** `analysis/00-mcp-componentes.md` §3.5 cita **27 herramientas ≈3.610 tokens frente a 8 ≈811**, mientras que la §4 de este documento mide **7.964 frente a 2.322** con `tiktoken`/`o200k_base`. **Las cifras vigentes son las de §4.** Las de componentes miden otra cosa (o con otro tokenizador) y su §3.5 debería remitir a §4.
>
> *(Añadido el 21/08: `bench/saturacion-herramientas.md` §2.2 recontó los mismos catálogos con el mismo tokenizador y obtuvo **7.886 y 2.306** — **1 % por debajo** de las cifras de §4, por un detalle de serialización. **La discrepancia con `00-mcp-componentes.md` no es de tokenizador ni de serialización: es de orden de magnitud, y sigue abierta.**)*
>
> *(Revisado el 21/08 a las 14:00 en la tercera pasada: **SIGUE ABIERTA, y ninguno de los tres informes de esa pasada la toca** — miden ppp, invocación de motores y el contrato de verificación. **Las cifras vigentes siguen siendo las de §4.** Lo que haría falta para cerrarla no ha cambiado.)*
>
> *(Revisado el 21/08 a las 10:00 en la segunda pasada de consolidación: **sigue abierta**. El recuento nuevo (7.886/2.306) **no explica** el factor **2,2** frente al ≈3.610/≈811 de componentes; solo confirma que las dos cifras de este documento miden lo mismo. Cerrarla exige rehacer el conteo de `00-mcp-componentes.md` §3.5 con `tiktoken`/`o200k_base` sobre el catálogo serializado, y ese fichero es de otro carril.)*

### 12.1 Las doce correcciones de `bench/mcp-cabos-sueltos.md` §6 — estado

**Aplicadas el 21/08/2026 a las 03:30.** El informe de origen las dejó en una tabla; aquí queda dónde se aplicó cada una.

| # | Qué corrige | Estado y dónde |
|---|---|---|
| 1 | §9.1, «anotar `readOnlyHint`/`destructiveHint`» era una ventaja diferencial sin matiz | ✅ **APLICADA.** §9.1 (fila matizada) + **§9.4 nueva** con la tabla de lo que cruza y lo que no. También en `analysis/00-mcp-patrones.md` regla 2 y en `PLAN-ORQUESTADOR.md` §4.4 |
| 2 | §2 pregunta 6, «0,93 tokens por byte» como cifra única | ✅ **APLICADA.** §2, bloque «Precisión del 21/08»: 0,93 tok/B es el base64 dentro de texto; el `ImageContent` nativo cuesta **por píxel** (2.814 tok medidos). **La conclusión no cambia** |
| 3 | §10, fila **R13**: «PENDIENTE verificar `list_roots()`» | ✅ **APLICADA.** §10 R13 → **CERRADA/IMPLEMENTADA**; `PLAN-ORQUESTADOR.md` §4.6 R13 con el mecanismo (el resolver decide si pregunta) |
| 4 | `bench/sdk-mcp-capacidades.md` §2.6, sus dos PENDIENTE | ✅ **CERRADOS los dos** por el informe de origen. Reflejado en §13 |
| 5 | `bench/sdk-mcp-capacidades.md` §2.4, idempotencia por el doble paso de `Resolve` | ✅ **APLICADA.** `PLAN-ORQUESTADOR.md` §5.3: **sigue siendo necesaria, ya no es urgente** — Claude Code negocia 2025-11-25 y el cuerpo corre **una** vez |
| 6 | `bench/mcp-refs-multimedia.md` §8.1, suite de `image-worker-mcp` sin ejecutar | ✅ **EJECUTADA** por el informe de origen: 117 tests, 6,43 s, 0 fallos. Reflejado en §11 y §13 |
| 7 | §8.1/§11, `ffmpeg-mcp-lite/tests` como plantilla | ✅ **CONFIRMADO y ampliado.** Se copia **la estructura** de `ffmpeg-mcp-lite` y **el criterio de aserción** de `image-worker-mcp` (`sharp.test.ts:369-380`, que abre la salida y afirma formato y geometría). Ver §11 |
| 8 | §8.1, «reproducido end-to-end en una; el resto PENDIENTE» | ✅ **APLICADA.** §8.1: **6 de 26** reproducidas y clasificación de las 27 **por AST** |
| 9 | §8.1, «`stdin=DEVNULL` primero, las banderas después» era una nota de orden | ✅ **APLICADA.** §8.1, bloque nuevo: **resultado causal A/B**, 2/5 frente a 0/5. `PLAN-ORQUESTADOR.md` §5.1 |
| 10 | §10 **R8**, justificada por «sustituir la entrada mientras el motor lee» | ✅ **APLICADA.** §10 R8 y `PLAN-ORQUESTADOR.md` §4.6: **el vector correcto es escribir EN SITIO**; sustituir no funciona en ninguna de las dos plataformas |
| 11 | §10 **R8** (alcance), sin excepciones | ✅ **APLICADA.** Excepción explícita para **`inspect`** en `PLAN-ORQUESTADOR.md` §4.6, con la salida correcta: leer metadatos **en proceso** |
| 12 | §13, «repetir la fase B del TOCTOU en Linux/WSL» | ✅ **PARCIALMENTE CERRADO** para el caso de lectura por un motor externo; **sigue abierta la carrera de symlinks en Linux**, que es otra cosa. Ver §13 |

**Y una corrección más, de otro informe del mismo día:** el contrato de verificación (`PLAN-ORQUESTADOR.md` §4.2) se reorganiza en **tres grupos —contrato, caracterización de la entrada y fidelidad—** porque `bench/verificador-fidelidad.md` midió que la fidelidad cuesta **×1.106 el contrato** y el **38,5 % de convertir**. Aplicada en `PLAN-ORQUESTADOR.md` §4.2 y `HUECOS.md` §1.

---

## 13. Lo que queda pendiente

**Revisado el 21/08/2026 (03:30): de los seis pendientes que tenía esta sección, cinco están cerrados.** Se dejan aquí con su cierre, para no perder la traza, y debajo va lo que sigue realmente abierto.

### 13.1 Los cinco cerrados

| Pendiente | Cerrado por | Resultado |
|---|---|---|
| ~~El efecto de un catálogo grande sobre la **elección** del modelo~~ | `bench/saturacion-herramientas.md` | **REFUTADA la hipótesis.** 540 ejecuciones, dos modelos: 27 herramientas acertaron **100 %/98 %** y 8 acertaron **85 %/77 %**; trampas **0 %/2 %** frente a **15 %/17 %**. **El catálogo grande eligió mejor.** Ver §2, pregunta 2 |
| ~~Verificar `list_roots()` en el SDK Python~~ | `bench/mcp-cabos-sueltos.md` §2 | **R13 IMPLEMENTADA.** El patrón condicional son ocho líneas y funciona en las 4 configuraciones (2 eras × cliente con/sin roots) y contra Claude Code |
| ~~Medir la ventana TOCTOU real de FileX~~ | ídem §5.1 | **Es el 99,6 % de la conversión** (9 758 ms de 9 794 en x264). El motor abre la entrada a los **23-53 ms** y no la suelta. **R8 confirmada, con su precio: 0,1 %-19,6 %** |
| ~~Repetir la fase B del TOCTOU en Linux/WSL~~ | ídem §5.2 | **PARCIALMENTE cerrado**, y con una corrección de mecanismo: **sustituir el fichero no funciona en ninguna de las dos plataformas**, por razones opuestas; **escribir en sitio sí, en las dos**, y ffmpeg lo convierte con `returncode 0` |
| ~~La suite de `image-worker-mcp`~~ | ídem §3 | **EJECUTADA.** `npm install --legacy-peer-deps` (falla sin él: `ERESOLVE`), 702 paquetes, 177,3 MB. **117 tests, 6,43 s, 0 fallos** — pero **75 de 117 (64 %) prueban las tres nubes y solo 13 la conversión** |

### 13.2 Lo que sigue realmente abierto

| Pendiente | Por qué importa | De dónde sale |
|---|---|---|
| **La carrera de symlinks en Linux** contra `servers/filesystem` | En Windows el **79 %** de los intentos del atacante falló por bloqueo de fichero, así que la medida de Windows no concluye. **Es una carrera distinta** de la de lectura por un motor externo, que sí está cerrada | §5 · `mcp-cabos-sueltos.md` §7 |
| Las **20 herramientas de `video-audio-mcp` no ejecutadas** | La clasificación por AST las cubre; la **ejecución** no. Es exhaustividad, no duda sobre el mecanismo: 6 de 6 representantes cuelgan y el mecanismo está demostrado A/B | `mcp-cabos-sueltos.md` §4.2 |
| Si Claude Code emite **`notifications/roots/list_changed`** | Decide si FileX puede **cachear los roots por sesión** o tiene que preguntarlos en cada llamada que los pida — y el resolver corre **una vez por herramienta**, no una por sesión | ídem §1.7 |
| Si Claude Code expone **recursos y prompts** al modelo | Si no lo hace, declararlos es **coste sin retorno**. El servidor de sonda los declaró y registró **cero** lecturas, pero tampoco se le pidió que los usara | ídem §1.7 |
| Si las herramientas MCP llegan **diferidas** de forma general | **Observación de una sola sesión**, marcada PENDIENTE por su propio informe: le llegaron solo los nombres, con descripción y esquema hasta una búsqueda explícita. Si es el comportamiento general, **el coste de catálogo de §4 no se paga por adelantado** en este cliente, y el multiplicador ×2,0–2,6 de `saturacion-herramientas.md` §3.6 cambia | ídem §1.7 |
| El **punto de cruce exacto `inspect` vs staging** en otras máquinas | Aquí está en **~90-100 MB** y depende del disco. Por debajo, copiar es despreciable; por encima, R8 necesita su excepción | ídem §5.4 |
| Replicar la saturación en **dominio documental** (docling-mcp, 19 herramientas), con **API y `temperature` fija**, y con modelos de otras familias o locales pequeños | La temperatura **no es fijable desde el CLI** y es la limitación nº 1 declarada del experimento. **No hay clave de API en esta máquina** | `saturacion-herramientas.md` §8 |
| El coste de la validación en Python sobre rutas de 1.000 componentes | — | heredado |
| ~~**Implementar y medir el quinto punto del contrato y R18**~~ | **CERRADO el 21/08 a las 14:00.** **+0,047 ms (+11,0 % del contrato) con R18 y ×8,6 sin él; 0 falsos positivos sobre el patrón oro; 0 avisos en tres salidas multifichero legítimas.** **Y el hallazgo que no se esperaba: sin censo, 49 de las 53 salidas bajan a `ok_parcial`, porque el punto 5 no es verificable a posteriori** | **`contrato-quinto-punto.md` §2, §3** |
| ~~**La regla de fidelidad que atraparía el caso de `resvg`**~~ | **CERRADA: I9 discrimina 6/6** con margen binario. **Y su coste real es 32–59 ms a 400×200 y 2 454 ms a 1920×960 — la estimación de 26 ms se quedaba corta ×94.** Sigue abierto **el miembro de la familia que nada atrapa** (canal de audio silenciado hacia destino con pérdida) | **ídem §4, §5** |
| ~~**`qpdf` y `tesseract` siguen sin motor en ninguna imagen levantada**~~ | **CERRADO: 8 líneas de Dockerfile, 28,1 s, +50 MB (+0,9 %).** `qpdf 12.4.0` resuelve **7 de 7** operaciones y `Tesseract 5.5.0` **trae `spa` incluido**. **El coste de integración real de los siete `no_evaluable` era dos motores, 50 MB y 28 segundos** | **`invocacion-aristas.md` §9** |
| **El miembro descubierto de la familia de `resvg`** | Audio con **un canal silenciado hacia un destino con pérdida**: el contrato ve 2 canales y la duración correcta, y A4/A5 no aplican porque no hay PCM que comparar. **La cobertura depende del destino, no del fallo.** Propuesta sin medir: energía por canal con `ffmpeg -af astats` | **`contrato-quinto-punto.md` §5, §10** |
| **Validar el sustituto de `P9` a escala** | `P9` quedó **REFUTADA** (8,3 % de sensibilidad, 36 % de falsos positivos) y su sustituto —**el acuerdo entre dos pasadas de OCR con idiomas distintos, 16/16**— está medido sobre **16 pares y un solo motor**. **Dos idiomas del mismo motor podrían acordar en su propio error** | ídem §6 |
| **Ampliar el patrón oro con una salida multifichero** | `referencia.json` **no tiene ni una**, así que el «0 falsos positivos» del punto 5 se apoya en cuatro casos fabricados a propósito | ídem §3.3 |
| **El punto de cruce «en proceso / sonda externa» para píxeles** | Medido en tres tamaños (0,08 / 0,32 / 1,84 Mpx) y **el cruce está en ~0,1 Mpx**; la curva fina y el umbral exacto, sin medir. **Decide en qué régimen corre cada regla de fidelidad** | ídem §4.3 |

> **Un aviso operativo que no es un pendiente, pero afecta a la distribución de FileX — MEDIDO:** cualquier cambio en la `.mcp.json` del proyecto deja el servidor en **`⏸ Pending approval`**, y la aprobación es **interactiva**. Un `filex init` que escriba la `.mcp.json` **no deja el servidor conectado** (`mcp-cabos-sueltos.md` §1.6).

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
| **`bench/mcp-cabos-sueltos.md`** | **Los cinco cabos cerrados (21/08):** qué ve de verdad el cliente real, el patrón condicional de roots, la suite de `image-worker-mcp`, el A/B del deadlock y la ventana TOCTOU con sus cuatro vectores |
| **`bench/saturacion-herramientas.md`** | **540 ejecuciones (21/08):** el catálogo grande no degrada la elección, el multiplicador ×2,0–2,6, y los fallos silenciosos por falta de cobertura |
| `bench/salidas-mcp-cabos/`, `bench/salidas-saturacion/` | Arneses y datos crudos de los dos anteriores |
| **`bench/aristas-nominales.md`** | **El quinto punto del contrato y la regla R18 (21/08):** los motores que escriben fuera del destino, el caso de `resvg` que ningún punto atrapa, y el 50,5 % de aristas nominales con su método |
| **`bench/contrato-quinto-punto.md`** | **El quinto punto implementado y medido (21/08, 14:00):** su coste con y sin R18, los 0 falsos positivos, **la regla I9**, **la familia de cinco miembros**, **`P9` refutada y su sustituto**, el interruptor de V2 y **el fallo de la sonda `_gs_texto`** |
| **`bench/invocacion-aristas.md`** | **El 18,8 % del 50,5 % que era invocación (21/08, 14:00):** las tres categorías, los crudos con sus cuatro datos, el **censo completo de Ghostscript y Gotenberg al 3,1 %**, y el **coste de integrar `qpdf` y `tesseract`** |
| `bench/salidas-quinto-punto/`, `bench/salidas-invocacion/` | Arneses y datos crudos de los dos anteriores |
| `analysis/00-mcp-patrones.md` | Reglas MCP vigentes — **al día: las correcciones de §12 y §12.1 están aplicadas (21/08/2026)** |
