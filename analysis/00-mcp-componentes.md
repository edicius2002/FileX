# 00 — Componentes MCP: qué se lleva FileX, de dónde, y en qué estado

**Consolidación de `analysis/00-mcp-filesystem.md` (56 KB) y `analysis/00-mcp-multimedia.md` (90 KB)**, más lo que
ya estaba fijado en `analysis/00-mcp-patrones.md`, `analysis/kordoc-y-mcps-menores.md` y `bench/mcp-ergonomia.md`.
Cierra la fase 1 de `PRUEBAS-MCP-REFS.md` §5.

Los dos análisis de origen son 146 KB de prosa. Este documento es lo que se lee al construir: **una fila por pieza
concreta, con su cita, su licencia y su veredicto.** No repite el razonamiento — está en los originales, y cada fila
apunta a la sección que lo sostiene.

**Método.** Síntesis y lectura. Nada ejecutado, nada instalado, sin GPU. He verificado en el código fuente de
`repos/mcp-refs/` una muestra de las citas de mayor valor (las 12 marcadas con ✔ en la tabla maestra); el resto se
traslada tal como lo dejaron los análisis de origen, conservando sus marcas `[no verificado]`. Donde he encontrado
que un análisis de origen se equivoca, no lo he suavizado: está en §3.

**Las cuatro etiquetas de veredicto**, y se usan exactamente así:

| Etiqueta | Significa |
|---|---|
| **COPIAR TAL CUAL** | Licencia permisiva y encaja sin adaptación. Incluye patrones de diseño de coste cero, donde «copiar» es adoptar la decisión, no el texto |
| **ADAPTAR** | La idea sirve, el código hay que reescribirlo. La fila **dice qué hay que cambiar** |
| **SOLO REFERENCIA** | Se lee y se reimplementa, nunca se copia — por licencia, por lenguaje, o porque el comportamiento concreto es discutible |
| **DESCARTAR** | Con el motivo, para que nadie lo reconsidere |

**Aviso de licencia que corrige a todo el proyecto: `modelcontextprotocol/servers` no es MIT a secas.** Ver §3.1.
En la columna de licencia aparece como `MIT/Apache-2.0 (transición)`.

---

## 1. Tabla maestra: componente → repo → veredicto

Rutas relativas a `repos/mcp-refs/`, salvo la fila marcada `ai-engines`. ✔ = cita verificada por mí en el código.

### 1.A Confinamiento del sistema de ficheros — `servers/src/filesystem`

Es la respuesta a la pregunta 4 de §2, y la corrección de `PLAN-ORQUESTADOR.md` §4.6.

| Componente | Repo | Fichero:línea | Licencia | Veredicto | Coste de adopción | Qué resuelve en FileX |
|---|---|---|---|---|---|---|
| `isPathWithinAllowedDirectories` — predicado de contención puro, sin E/S | `servers` | `filesystem/path-validation.ts:11-86` | MIT/Apache-2.0 (transición) | **ADAPTAR** | ~4 h | El núcleo de la lista blanca de raíces. **Cambiar:** `startsWith(dir+sep)` → `PurePath.is_relative_to`; `path.resolve` → `os.path.abspath` (**no** `Path.resolve()`, que sigue enlaces); añadir `os.path.normcase` para cerrar el hueco de mayúsculas de Windows |
| `+ path.sep` contra la vulnerabilidad de prefijo ✔ | `servers` | `filesystem/path-validation.ts:84` | MIT/Apache-2.0 | **COPIAR TAL CUAL** | 1 línea | Que `/home/u/proyecto_backup` no caiga dentro de `/home/u/proyecto`. Test que lo fija: `__tests__/path-validation.test.ts:63` |
| Rechazo de bytes nulos en ruta y en allowlist | `servers` | `filesystem/path-validation.ts:23-25`, `:47-49` | MIT/Apache-2.0 | **COPIAR TAL CUAL** | 2 líneas | Truncamiento `foo.txt\x00.png` |
| Allowlist vacía = denegar todo | `servers` | `filesystem/path-validation.ts:18-20` | MIT/Apache-2.0 | **COPIAR TAL CUAL** | 1 línea | Fail-closed. Un fallo de configuración no abre el disco |
| Disciplina «predicado léxico ANTES de tocar el disco» ✔ | `servers` | `filesystem/lib.ts:107-111` | MIT/Apache-2.0 | **COPIAR TAL CUAL** | cero (decisión) | Acota el oráculo de existencia al interior de la allowlist: para lo de fuera, el disco no se consulta nunca |
| Doble validación: ruta pedida **y** ruta real ✔ | `servers` | `filesystem/lib.ts:108` y `:118` | MIT/Apache-2.0 | **COPIAR TAL CUAL** | cero (patrón) | Enlaces simbólicos que apuntan fuera, incluidas cadenas anidadas |
| Devolver siempre la ruta canónica al llamante ✔ | `servers` | `filesystem/lib.ts:121` | MIT/Apache-2.0 | **COPIAR TAL CUAL** | cero (patrón) | Que ninguna capa posterior —ni el subproceso ffmpeg— vuelva a ver la ruta que escribió el modelo |
| Rama ENOENT → validar el **directorio padre real** | `servers` | `filesystem/lib.ts:122-137` | MIT/Apache-2.0 | **ADAPTAR** | ~2 h | Imprescindible para ficheros de **salida**, que por definición no existen. **Cambiar:** `os.path.realpath(p, strict=True)` (con `strict=False` se pierde la rama entera) |
| Guardar en la allowlist la forma original **y** la resuelta ✔ | `servers` | `filesystem/index.ts:41-67` | MIT/Apache-2.0 | **ADAPTAR** | ~2 h | Sin esto, una raíz enlazada (macOS `/tmp`→`/private/tmp`, o cualquier symlink de conveniencia) deniega todo. **Cambiar:** solo la traducción a Python |
| Filtrado de raíces inaccesibles + abortar si no queda ninguna | `servers` | `filesystem/index.ts:70-88` | MIT/Apache-2.0 | **ADAPTAR** | ~1 h | Fail-closed al arrancar |
| `expandHome` (`~`, `~/…`) | `servers` | `filesystem/path-utils.ts:119-124` | MIT/Apache-2.0 | **ADAPTAR** | 15 min | **Cambiar:** `os.path.expanduser` de Python también expande `~usuario`, cosa que la referencia **no** hace. Lo conservador es no permitirlo |
| Manejo de raíz de unidad Windows (único punto case-insensitive) | `servers` | `filesystem/path-validation.ts:77-82` | MIT/Apache-2.0 | **ADAPTAR** | ~1 h | **Cambiar:** generalizar con `normcase` en vez de tratar solo la letra de unidad |
| Escritura con flag `'wx'` + `rename` atómico | `servers` | `filesystem/lib.ts:161-185` | MIT/Apache-2.0 | **ADAPTAR** | ~3 h | No escribir a través de un enlace preexistente. **Cambiar:** `os.open(O_EXCL)` + `os.replace`, y el temporal **al staging privado**, no junto al destino |
| Casos de test de TOCTOU, como catálogo de huecos a cerrar | `servers` | `filesystem/__tests__/path-validation.test.ts:679`, `:784`, `:932` | MIT/Apache-2.0 | **COPIAR TAL CUAL** (los casos, no el código) | ~4 h portar los casos | Son los tres agujeros que la propia referencia demuestra y no tapa. FileX los cierra con `O_NOFOLLOW` y `dir_fd`, que Node no tiene y Python sí |
| `getFileStats` | `servers` | `filesystem/lib.ts:144-155` | MIT/Apache-2.0 | **ADAPTAR** | 30 min | Chequeo de tamaño previo a convertir. Trivial (`os.stat`) |
| Resolución de rutas relativas contra cada raíz permitida | `servers` | `filesystem/lib.ts:76-96` | MIT/Apache-2.0 | **SOLO REFERENCIA** | — | Comportamiento discutible: elige «la primera raíz que encaje», ambiguo con varias raíces. **FileX exige rutas absolutas y rechaza las relativas** |
| `normalizePath` (WSL, `/c/…`, UNC, comillas envolventes) | `servers` | `filesystem/path-utils.ts:39-112` | MIT/Apache-2.0 | **SOLO REFERENCIA** | — | Casi todo son parches para que `fs` de Node funcione dentro de WSL. Portar solo UNC y letra de unidad si FileX soporta Windows |
| `list_allowed_directories` como herramienta | `servers` | `filesystem/index.ts:702-717` | MIT/Apache-2.0 | **SOLO REFERENCIA** | — | Decisión de política: publicar las raíces al modelo es cómodo y es divulgación. Decidir aparte, no heredar |
| `searchFilesWithValidation` | `servers` | `filesystem/lib.ts:374-415` | MIT/Apache-2.0 | **SOLO REFERENCIA** | — | El patrón «validar cada entrada durante el recorrido» (`:390`) es bueno; le falta límite de profundidad y de resultados, y silencia errores (`:407-409`) |
| Mensajes de error detallados (4 variantes distinguibles) | `servers` | `filesystem/lib.ts:110`, `:119`, `:131`, `:135` | MIT/Apache-2.0 | **DESCARTAR** | — | Oráculo de existencia + fuga de la allowlist completa + **fuga de rutas de fuera del sandbox** (`:119` imprime `realPath`, que por definición está fuera). Un solo mensaje opaco constante; el detalle a stderr |
| `read_multiple_files`: serializa el error **por ruta** en vez de propagarlo | `servers` | `filesystem/index.ts:345` | MIT/Apache-2.0 | **DESCARTAR** | — | Convierte el oráculo en una consulta por lotes: un `tools/call` con N rutas = N respuestas del oráculo |
| Temporales creados junto al fichero destino | `servers` | `filesystem/lib.ts:171`, `:269` | MIT/Apache-2.0 | **DESCARTAR** | — | Si el proceso muere queda basura en el directorio del usuario. FileX produce ficheros grandes con procesos que pueden morir: staging propio con limpieza garantizada |
| `read_media_file` — MIME deducido de la **extensión** | `servers` | `filesystem/index.ts:280-295` | MIT/Apache-2.0 | **DESCARTAR** | — | Antipatrón para un conversor: el tipo determina qué motor se invoca, y la extensión la escribe el agente. Ver `isHeif` en §1.F |
| `convertToWindowsPath` (`/c/…`, `/mnt/c/…`) | `servers` | `filesystem/path-utils.ts:9-32` | MIT/Apache-2.0 | **DESCARTAR** | — | Complejidad sin beneficio salvo que FileX acepte rutas estilo WSL del LLM. Superficie de bugs |
| `applyFileEdits` (edición por coincidencia de texto), `tailFile`/`headFile` | `servers` | `filesystem/lib.ts:194-282`, `:285-372` | MIT/Apache-2.0 | **DESCARTAR** | — | Un conversor no edita ficheros por texto ni pagina líneas |

### 1.B Superficie del protocolo MCP — `servers/src/everything`, `filesystem`, `fetch`

FileX solo contempla `tools`. Esto es lo que el protocolo ya ofrece y no se está usando.

| Componente | Repo | Fichero:línea | Licencia | Veredicto | Coste de adopción | Qué resuelve en FileX |
|---|---|---|---|---|---|---|
| Negociación de **roots** (init + `notifications/roots/list_changed` + fail-closed si no hay ninguna) | `servers` | `filesystem/index.ts:723-773` | MIT/Apache-2.0 | **ADAPTAR** | ~1 día | La allowlist se alimenta del cliente, sin configuración manual. **Es protocolo, no invención** — justo lo que `PLAN-ORQUESTADOR.md:266-271` da por inventar. Verificar `session.list_roots()` en el SDK Python **[no verificado]** |
| `getValidRootDirectories` — validación de cada root (`file://`, `~`, `realpath`, descartes a stderr) | `servers` | `filesystem/roots-utils.ts:13-77` | MIT/Apache-2.0 | **ADAPTAR** | ~4 h | **Cambiar la política:** la referencia **reemplaza** la allowlist del servidor (`index.ts:181`); FileX debe **intersecar** con una allowlist de servidor inmutable, porque escribe ficheros y lanza procesos |
| Anotaciones de herramienta (`readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint`) | `servers` | `filesystem/index.ts:370,400,425,629`; `everything/tools/gzip-file-as-resource.ts:50-55` | MIT/Apache-2.0 | **COPIAR TAL CUAL** | ~30 min | Coste cero, valor inmediato: el cliente decide cuándo pedir confirmación. **Los cuatro repos de conversión tienen cero anotaciones** (§2, pregunta 3) |
| `resource_link` + recurso de sesión como salida de una herramienta ✔ | `servers` | `everything/tools/gzip-file-as-resource.ts:94-121`; `everything/resources/session.ts:32-80` | MIT/Apache-2.0 | **ADAPTAR** | ~1 día | Devolver la salida sin que el cliente adivine cómo leerla. **Cambiar — y es crítico:** el `outputType:"resource"` mete `compressedBuffer.toString("base64")` **entero** en el resultado (`:96`, `:113-119`). Para un MP4 eso es inviable. En FileX: `resource_link` sí, `resource` con blob **solo por debajo de un cap explícito**. Ver §3.4 |
| Progress notifications (`progressToken` del `_meta`) | `servers` | `everything/tools/trigger-long-running-operation.ts:50-64` | MIT/Apache-2.0 | **ADAPTAR** | ~4 h | Una conversión con OCR o una recodificación H.265 tarda minutos. Sin progreso el cliente no distingue «trabajando» de «colgado». **Ninguno de los cuatro repos de conversión tiene progreso** |
| Elicitation (preguntar al **usuario**, no al modelo; `accept`/`decline`/`cancel`) | `servers` | `everything/tools/trigger-elicitation-request.ts:56`, `:184`, `:213`, `:218` | MIT/Apache-2.0 | **ADAPTAR** | ~1 día | Contraseña de PDF, confirmación de sobrescritura, «esto usa la GPU 8 min, ¿sigo?». Es el punto de consentimiento humano que a un conversor con escritura le falta |
| `structuredContent` + `outputSchema` | `servers` | `everything/docs/features.md:19` | CC-BY-4.0 (documentación) | **ADAPTAR** | ~4 h | El asa como objeto tipado, no como prosa que el modelo tiene que parsear. Respeta la regla 4 de `bench/mcp-ergonomia.md`: **un solo canal**, nunca `content` y `structuredContent` con la misma carga |
| Logging estructurado con nivel controlado por el cliente | `servers` | `everything/docs/features.md:53-57`; `everything/server/roots.ts:47-54` | CC-BY-4.0 / MIT-Apache | **ADAPTAR** | ~3 h | Enviar «qué motor eligió el orquestador y por qué cayó a un fallback» al cliente, en vez de a stderr. Encaja con la regla 15 (silencio en stderr) |
| `fetchSafely` — límite de bytes **real**, no de cabecera, + timeout con `AbortController` | `servers` | `everything/tools/gzip-file-as-resource.ts:180-248` | MIT/Apache-2.0 | **ADAPTAR** | ~4 h | Si FileX acepta URLs. El comentario de `:200-201` es el punto: `content-length` sirve para abortar pronto, pero hay que contar los bytes leídos. **Añadir lo que le falta:** bloqueo de rangos privados y **re-validación en cada redirección** |
| `validateDataURI` — allowlist de esquema y de dominio | `servers` | `everything/tools/gzip-file-as-resource.ts:135-168` | MIT/Apache-2.0 | **ADAPTAR** | ~2 h | Ídem. **Cambiar:** allowlist vacía = todo permitido es elección de demo; en FileX vacía = nada permitido |
| `fetch` — robots.txt con Protego + UA distinto para fetch autónomo y manual | `servers` | `fetch/src/mcp_server_fetch/server.py:23-24`, `:66-108` | MIT/Apache-2.0 | **SOLO REFERENCIA** | — | Buen patrón conceptual: «hay humano en el bucle → otra política». No hace falta salvo que FileX descargue por su cuenta |
| Tasks (SEP-1686): `taskId`, polling, `tasks.cancel` | `servers` | `everything/docs/features.md:59-105`; `everything/server/index.ts:65-73` | CC-BY-4.0 / MIT-Apache | **SOLO REFERENCIA** | — | Alternativa estructurada al progreso para trabajos de minutos. Es reciente: **[no verificado]** el soporte en el SDK Python. No comprometerse antes de comprobarlo |
| Aviso de seguridad al bindear fuera de localhost | `ai-engines` | `markitdown/packages/markitdown-mcp/src/markitdown_mcp/__main__.py:117-128` | MIT | **COPIAR TAL CUAL** | 10 min | Si FileX ofrece transporte HTTP. Es lo único que el markitdown oficial hace y nadie más: avisar de que no hay autenticación y el servidor lee con los privilegios del usuario |
| `fetch` — todo lo demás (SSRF, sin límite de bytes, sin filtro de esquema, redirecciones sin revalidar) | `servers` | `fetch/src/mcp_server_fetch/server.py` completo | MIT/Apache-2.0 | **DESCARTAR** | — | **La referencia oficial admite el SSRF en su propio README** (`fetch/README.md:12`). `response.text` materializa el cuerpo entero antes de truncar; la petición de robots.txt es el primer disparo del SSRF y va sin timeout |
| Sampling (el servidor pide inferencia al cliente) | `servers` | `everything/docs/features.md:27` | CC-BY-4.0 | **DESCARTAR** | — | Coste no acotado y sin caso de uso claro en un conversor |
| Resource subscriptions, prompts guiados, completions | `servers` | `everything/docs/features.md:32-51` | CC-BY-4.0 | **DESCARTAR** | — | Fuera de alcance del hito 4. El watcher del hito 7 cubre la parte útil de las suscripciones sin protocolo |

### 1.C Estructura del servidor y tamaño del catálogo

Es la respuesta a las preguntas 2 y 3 de §2.

| Componente | Repo | Fichero:línea | Licencia | Veredicto | Coste de adopción | Qué resuelve en FileX |
|---|---|---|---|---|---|---|
| Troceado `tools/<dominio>.py` + `server.py` que **solo registra** + `config.py` ✔ | `ffmpeg-mcp-lite` | `src/ffmpeg_mcp_lite/server.py:1-29` | MIT | **COPIAR TAL CUAL** | ~2 h | La forma exacta que FileX necesita. 8 herramientas ≈ 811 tokens de catálogo estimados, dentro del presupuesto de ≈1 000 de la regla 5 |
| Funciones de herramienta **sin decorador**, registradas aparte ✔ | `ffmpeg-mcp-lite` | `src/ffmpeg_mcp_lite/server.py:17-24` + `tools/*.py` (no importan `mcp`) | MIT | **COPIAR TAL CUAL** | cero (disciplina) | La separación núcleo/superficie que `00-mcp-patrones.md` atribuye a la arquitectura de kordoc, conseguida con dos líneas. El núcleo lo usan la CLI, el watcher, la API y los tests sin tocar nada |
| `Literal[...]` en la firma en vez de validar en tiempo de ejecución | `ffmpeg-mcp-lite` | `tools/compress.py:12-14`, `tools/audio.py:12`, `tools/frames.py:14` | MIT | **COPIAR TAL CUAL** | ~1 h | Se convierte en `enum` de JSON Schema: el modelo no puede equivocarse y **el mensaje de error que enumera alternativas sobra**, porque el catálogo ya las enumeró |
| `config.py` — rutas de binarios por variable de entorno, nunca `"ffmpeg"` literal en una herramienta ✔ | `ffmpeg-mcp-lite` | `src/ffmpeg_mcp_lite/config.py:10-21` | MIT | **ADAPTAR** | ~2 h | Parametrización de motores. **Añadir lo que no tiene:** timeouts, tamaño máximo de entrada, tope de duración. `grep timeout\|max_\|limit` sobre su `src/` → **0 resultados** |
| Salida confinada a un directorio configurado + nombre derivado de la entrada | `ffmpeg-mcp-lite` | `config.py:13-21` + `tools/convert.py:35-36` | MIT | **ADAPTAR** | ~4 h | **El modelo no elige dónde escribir.** Es media regla 12 gratis. **Cambiar:** cerrar las dos fugas (`tools/merge.py:38-39` y `tools/subtitles.py:72-73` aceptan `output_path` arbitrario) y **añadir el confinamiento de entrada**, que no existe: `resolve()` normaliza pero no compara contra ninguna raíz |
| `_run_ffmpeg_with_fallback` — intento primario y degradación | `video-audio-mcp` | `server.py:332-348` | MIT | **ADAPTAR** | ~2 h | La degradación automática (copiar códec → recodificar) es correcta y FileX la necesita. **Cambiar:** comunicarla con un **código de aviso estructurado**, no cambiando la palabra «primary» por «fallback» en una frase (`:336`/`:340`) |
| Factory + Strategy para backends intercambiables | `image-worker-mcp` | `src/services/types.ts:49-57`, `src/services/factory.ts:8-71` | MIT | **SOLO REFERENCIA** | — | Aplicable al registro de motores de FileX, pero en TypeScript y con un fallo de arranque (fila siguiente). El registro por reflexión de transmute (`PLAN-ORQUESTADOR.md` §4.3) ya cubre esto mejor |
| Singleton de módulo `config = Config()` capturado por `from ..config import config` | `ffmpeg-mcp-lite` | `src/ffmpeg_mcp_lite/config.py:23` | MIT | **SOLO REFERENCIA** | — | Es una **trampa documentada**: reasignar `config.config` no afecta a los módulos que ya capturaron la instancia. FileX tendrá el problema idéntico con el singleton de motor caliente (regla 14). Ver el fixture de §1.F |
| `RESEARCH.md`: decidir la superficie de herramientas **antes** de escribirla | `ffmpeg-mcp-lite` | `RESEARCH.md:150-334` (comparativa de 5 MCP de ffmpeg, prioridad P0/P1 en §5.3) | MIT | **SOLO REFERENCIA** | — | Práctica, no código. Es el único de los seis repos que lo hizo, y se nota en el resultado |
| **27 herramientas planas, una por parámetro de ffmpeg** | `video-audio-mcp` | `server.py` completo (grep `@mcp.tool` = 27 ✔) | MIT | **DESCARTAR** | — | Regla 5 violada al máximo. **Nueve de las 27 son tres líneas de diccionario sobre el mismo helper** (`server.py:332-348`), y cinco nombres empiezan por `set_video_audio_track_…`. Todas caben en argumentos opcionales de 3 herramientas |
| Construir los servicios en el **constructor** del servidor | `image-worker-mcp` | `src/server.ts:18` | MIT | **DESCARTAR** | — | Si faltan credenciales de nube el servidor **muere al arrancar** aunque el usuario solo quisiera redimensionar, y `bin/image-worker-mcp.mjs:12` se traga el error con `.catch(() => process.exit(1))`. Un conversor no muere por una capacidad que nadie pidió |
| Servidor de solo **prompts**, sin herramientas | `markitdown_mcp_server` | `server.py:48`, `:53` (no hay `@app.list_tools()` en 153 líneas) | MIT | **DESCARTAR** | — | **No es automatizable**: una herramienta la elige el modelo, un prompt lo invoca la persona. Un agente que consulte `tools/list` no ve nada (`-32601 Method not found`, verificado en ejecución) |
| `os.system("notify-send …")` al arrancar | `markitdown_mcp_server` | `__init__.py:8` | MIT | **DESCARTAR** | — | Un servidor stdio no ejecuta comandos de escritorio al arrancar. Falla en Windows |
| `ls` que lista cualquier directorio del disco, tres veces en la misma cadena | `markitdown_mcp_server` | `server.py:87-136` (agrupado `:111-115`, sin extensión `:116-117`, numerado `:120-122`) | MIT | **DESCARTAR** | — | Máximo coste en tokens por mínimo valor, y sin confinamiento |

### 1.D Contrato de salida — qué se devuelve tras convertir

Es la respuesta a las preguntas 1 y 6 de §2.

| Componente | Repo | Fichero:línea | Licencia | Veredicto | Coste de adopción | Qué resuelve en FileX |
|---|---|---|---|---|---|---|
| Recorte del `ffprobe` a los campos que importan ✔ | `ffmpeg-mcp-lite` | `tools/info.py:46-88` (comentario `# Extract key information for a cleaner response`, `:48`) | MIT | **COPIAR TAL CUAL** | ~2 h | La regla 3 (lectura acotada) aplicada al caso binario: de miles de tokens de `ffprobe` crudo a unos cientos. 4 campos de formato y 3–7 por stream. **Es el `inspect` de FileX, ya escrito** |
| Respuesta como **objeto estructurado** (`format`, `width`, `height`, `size`, `savedTo`, `source`) | `image-worker-mcp` | `src/tools/sharp.ts:278-297` | MIT | **ADAPTAR** | ~3 h | Es el único de los cuatro que no devuelve prosa, y los campos son los correctos. **Cambiar:** sacar el base64 del JSON (fila más abajo) y añadir `duration_ms`, `motor_usado`, `camino_recorrido`, `warnings[]` — los campos que `PLAN-ORQUESTADOR.md` §4.4 exige |
| Métricas de resultado en la respuesta (original / comprimido / % de reducción) | `ffmpeg-mcp-lite` | `tools/compress.py:71-81` | MIT | **ADAPTAR** | ~1 h | **La única herramienta de los cuatro repos que le dice al modelo si la operación consiguió su objetivo**, y cuesta ~40 tokens. **Cambiar:** emitirlo como objeto, no como prosa multilínea |
| Extracción de fotogramas como **proyección** de un binario | `ffmpeg-mcp-lite` | `tools/frames.py:10-92` | MIT | **ADAPTAR** | ~3 h | Un vídeo de 10 min se «lee» como 10 imágenes: lo más cerca que un modelo puede estar de ver el contenido. **Cambiar:** la respuesta dice cuántos frames y dónde, pero **no el patrón de nombres** (`frame_%04d.jpg` está en `frames.py:42` y nunca sale del servidor, `:92`). El modelo tiene que adivinar o listar el directorio |
| Asa como **frase en prosa** con la ruta dentro | `video-audio-mcp`, `ffmpeg-mcp-lite` | `video-audio-mcp/server.py:33`, `:59`, `:67`, `:336`, `:340`; `ffmpeg-mcp-lite/tools/convert.py:66` | MIT | **DESCARTAR** | — | Los tres repos llegaron al asa **por necesidad física**, y la construyeron mal. La redacción **cambia según el camino interno** («codec copy» / «re-encoded» / «primary» / «fallback»). Sus propios tests lo demuestran: `ffmpeg-mcp-lite/tests/test_convert.py:22` hace `Path(result.split(": ")[1])` — **parsear la ruta partiendo el mensaje por dos puntos.** Si un test tiene que hacer eso, un agente también |
| base64 completo dentro de un JSON de texto, indentado con `null, 2` | `image-worker-mcp` | `src/tools/sharp.ts:278-297` + `src/utils.ts:63-65` | MIT | **DESCARTAR** | — | **El peor de los dos mundos**: el modelo paga el coste en tokens de la imagen y no obtiene la capacidad multimodal, porque el prefijo `data:` que antepone `bufferToBase64` hace la cadena **inválida** para el campo `data` de un `ImageContent` MCP |
| `base64Image` como **parámetro de entrada** | `image-worker-mcp` | `src/tools/sharp.ts:22-26`, `src/tools/upload.ts:14-56` | MIT | **DESCARTAR** | — | El binario no cruza el canal MCP en **ninguna** dirección. Aceptarlo de entrada cuesta lo mismo que devolverlo |
| **Devolver una imagen al modelo como `ImageContent`** | ninguno | `grep "type: 'image'"` sobre `image-worker-mcp/src/` → **0 resultados** ✔ | — | **DESCARTAR como precedente** | — | **No hay precedente. Es un contraejemplo, no una referencia.** FileX escribe esta regla desde cero: `ImageContent` real, cap en bytes en constantes (no un booleano que decide el modelo, `sharp.ts:50`), y por encima del cap → asa con dimensiones + `thumbnail` explícito |
| **Umbral de bytes para decidir contenido frente a asa** | ninguno | `image-worker-mcp/src/constants.ts` son 11 líneas y no tiene ningún cap | — | **DESCARTAR como precedente** | — | Hueco confirmado: ningún repo de los seis tiene un límite de tamaño de salida. Trabajo propio de FileX |

### 1.E Errores y avisos — qué mensaje llega al modelo

Es la respuesta a la pregunta 5 de §2.

| Componente | Repo | Fichero:línea | Licencia | Veredicto | Coste de adopción | Qué resuelve en FileX |
|---|---|---|---|---|---|---|
| `describeError` — tabla `errno` → frase, **solo de la superficie MCP**, y **sin la ruta** ✔ | `kordoc` | `src/mcp.ts:84-100` | MIT | **COPIAR TAL CUAL** (traduciendo los textos) | ~1 h | **La mejor pieza leída en todo el carril.** 6 entradas, ~40 tokens de código, y es el reconocimiento explícito de que el modelo necesita otro texto que la persona. La CLI importa `sanitizeError`/`classifyError` crudos; el MCP tiene su propia capa de pistas |
| `ParseWarning` + enum `WarningCode` de 17 códigos, con `NEEDS_OCR` y umbral explícito | `kordoc` | `src/types.ts:249-277`; `src/pdf/parser.ts:257-263`; `src/pdf/quality.ts:156` (`DOC_NEEDS_OCR_PAGE_RATIO = 0.3`) | MIT | **COPIAR TAL CUAL** | ~1 día | **Resuelve el éxito parcial y el «éxito vacío» (regla 9) mejor que nada medido.** En binario el éxito parcial es *más* frecuente que en texto: pista de subtítulos perdida, recodificación silenciosa, HEIC del que solo se leyó la primera imagen del burst |
| Cerrar el bucle: la **descripción del parámetro** dice qué hacer con el código de aviso | `kordoc` | `src/mcp.ts:160` («si el parseo tiene aviso `NEEDS_OCR`, reintenta con esta opción») | MIT | **COPIAR TAL CUAL** | ~30 min | Autocorrección en un intento, coste cero en ejecución. La salida emite una señal codificada y el catálogo le dice al modelo qué hacer con ella |
| `raise` en vez de `return` ante fallo del motor → `isError: true` | `ffmpeg-mcp-lite` | `tools/convert.py:63-64` (idéntico en `compress.py:68`, `trim.py:64`, `audio.py:64`, `merge.py:70`, `frames.py:86`, `subtitles.py:104`, `info.py:43`) | MIT | **COPIAR TAL CUAL** | cero (disciplina) | Regla 9. **Es el único de los cuatro que lo hace bien.** Un fallo es un fallo |
| Mensajes de validación previa: cortos, nombran la causa y dicen qué hacer | `ffmpeg-mcp-lite` | `tools/trim.py:28`, `tools/frames.py:30`, `tools/merge.py:25`, `tools/convert.py:31` | MIT | **COPIAR TAL CUAL** | cero (estilo) | Todos por debajo de 20 tokens. Los de exclusión mutua dicen la salida («usa uno u otro»). Es la forma que la regla 8 pide |
| Enumerar las alternativas válidas en el mensaje de error | `kordoc`, `video-audio-mcp` | `kordoc/src/mcp.ts:52` (extensiones permitidas); `video-audio-mcp/server.py:838` (37 efectos `xfade`) | MIT | **ADAPTAR** | ~1 h | El patrón es el correcto (regla 8). **Cambiar:** si las alternativas caben en un `Literal`, el error sobra — el catálogo ya las enumeró. Y `video-audio-mcp` enumera los 37 efectos **tres veces**: docstring (`:778-812`), validación (`:825-836`) y error (`:838`) |
| Junto a una instrucción de instalación, **una alternativa que el modelo puede ejecutar ahora** | `kordoc` | `src/render/rasterize.ts:34-36` (`format: "svg"` + `output_path`) | MIT | **ADAPTAR** | ~2 h | La única salida buena vista ante una dependencia ausente. Regla para FileX: si falta una capacidad, **el mensaje enumera los destinos que sí están disponibles**, y la instrucción de instalación —si se emite— va detrás, no delante |
| `KordocError` como marcador de tipo para el saneado | `kordoc` | `src/utils.ts:23-28` | MIT | **ADAPTAR** | ~2 h | La idea (allowlist **por tipo**, no por patrón de texto) es buena. **Cambiar:** añadir los campos `code`, `hint`, `path` en vez de meterlo todo dentro de `message`, que es lo que obliga al `classifyError` frágil de más abajo |
| `classifyError` por coincidencia de **substrings del mensaje** | `kordoc` | `src/utils.ts:166-181` | MIT | **DESCARTAR** | — | Frágil por construcción: nueve ramas sobre `err.message`, patrones en coreano, **no mira `err.code` de Node** (`ENOENT`/`EACCES`/`EISDIR` caen a `PARSE_ERROR`), y un cambio de redacción rompe la clasificación en silencio. **FileX lleva el código dentro de la excepción** |
| `sanitizeError` binario: `KordocError` verbatim / cualquier otra cosa → constante | `kordoc` | `src/utils.ts:34-37` | MIT | **DESCARTAR** | — | Los dos extremos son malos: **filtra rutas absolutas** cuando es `KordocError` (`mcp.ts:45`, `:46`, `:71`, `:120`, `:129`) y **destruye toda la información** cuando no lo es. El régimen de saneado depende de qué clase se instanció, no de qué información es segura |
| Descartar `result.code` al construir la respuesta MCP | `kordoc` | `src/mcp.ts:207` (usa `result.fileType` y `result.error`, tira `result.code`) | MIT | **DESCARTAR** | — | **La superficie de máquina expone menos estructura que la de humano**: la CLI sí emite los códigos en `--format json` (`cli.ts:176-183`). Es exactamente al revés de como debe ser |
| Reenviar el `stderr` crudo del motor | los cuatro | `video-audio-mcp/server.py:36` y `:344` (**dos volcados concatenados**, en 9 herramientas); `ffmpeg-mcp-lite/tools/convert.py:64`; `image-worker-mcp/src/tools/sharp.ts:310` | MIT | **DESCARTAR** | — | Regla 8. **Es unánime y está unánimemente mal.** Un `e.stderr` de ffmpeg es banner + `configuration:` con ~50 flags + versiones de libav: 1,5–3 KB, 500–1 000 tokens por fallo |
| Devolver el error como cadena con `isError: false` | `video-audio-mcp`, `markitdown_mcp_server` | las 27 herramientas de `video-audio-mcp`; `markitdown_mcp_server/server.py:40-41` | MIT | **DESCARTAR** | — | Regla 9 en su forma más pura. En `markitdown_mcp_server` la excepción **se inyecta donde iría el documento**, precedida de «Here is the converted document in markdown format» (`server.py:72-82`). La única forma que tiene el agente de distinguir éxito de fracaso es buscar la palabra «Error» en una frase en inglés |
| Reenviar `npm install` / `pip install` al modelo | `kordoc` | `src/index.ts:196-200`, `src/ocr/image-ocr.ts:86-89`, `src/render/rasterize.ts:34-36` | MIT | **DESCARTAR** | — | El mismo pecado que docling-mcp (`pip install openai-whisper`, medido en `bench/mcp-ergonomia.md` §4.2). El comentario de `image-ocr.ts:85` dice que el diseño **busca deliberadamente** que atraviese el saneado. Y la inconsistencia es real: cuatro `tryImport` casi idénticos, **tres lanzan `new Error` y pierden la pista, uno lanza `KordocError` y la conserva** (`ocr/engine.ts:333-336`, `ocr/pdf-ocr.ts:184-187`, `pdf/formula/pipeline.ts:310-313`) |

### 1.F Detección de formato, pruebas y utillaje

| Componente | Repo | Fichero:línea | Licencia | Veredicto | Coste de adopción | Qué resuelve en FileX |
|---|---|---|---|---|---|---|
| `isHeif` — detección por **magic bytes** del box `ftyp` de ISO-BMFF, no por extensión ✔ | `image-worker-mcp` | `src/tools/sharp.ts:96-99` | MIT | **COPIAR TAL CUAL** | 15 min | El nombre del fichero lo escribe un agente: no se puede confiar en la extensión. Seis firmas (`ftypheic`, `ftypheix`, `ftyphevc`, `ftyphevx`, `ftypmif1`, `ftypmsf1`) en offset 4..12. Es el antídoto exacto al antipatrón de `filesystem/index.ts:280-295` |
| `conftest.py` que **genera el material de prueba con el propio motor** + `pytest.skip` si falta ✔ | `ffmpeg-mcp-lite` | `tests/conftest.py:17-40` | MIT | **COPIAR TAL CUAL** | ~2 h | Tres decisiones correctas de golpe: **cero binarios versionados** (`video-audio-mcp` versiona un `sample.mp4` de 10 MB), **propiedades conocidas** contra las que assertar de verdad (320×240, 2 s, 440 Hz), y una suite honesta en CI sin dependencias |
| Un fichero de test por herramienta ✔ | `ffmpeg-mcp-lite` | `tests/test_{audio,compress,convert,frames,info,merge,subtitles,trim}.py` | MIT | **COPIAR TAL CUAL** | cero (disciplina) | Disciplina de cobertura. **~10 de ~31 tests son de error esperado (`pytest.raises`)**, casi un tercio: es la proporción a imitar |
| Fixture que hace `monkeypatch` de la **instancia viva** del config, no del módulo | `ffmpeg-mcp-lite` | `tests/test_frames.py:10-20` | MIT | **COPIAR TAL CUAL** | 15 min | Escrito por alguien que se comió el bug: `monkeypatch.setenv` + reasignar `config.config` **no funciona** para un módulo que hizo `from ..config import config`. FileX tendrá esto idéntico con el singleton de motor caliente |
| Tests que verifican **propiedades del artefacto** con `ffprobe` (duraciones, sumas de concatenación) | `video-audio-mcp` | `tests/test_video_functions.py:471-495`, `:530`, `:553`, `:582`, `:628`, `:680-700` | MIT | **ADAPTAR** | ~1 día | **Es la profundidad de assert que a `ffmpeg-mcp-lite` le falta**: allí solo `test_info.py:15-29` mira dentro del resultado. **Combinar:** el `conftest.py` de uno con los asserts del otro. Sin eso, una suite no distingue «convirtió» de «escribió un fichero de 0 bytes» |
| Shim `.d.ts` mínimo para el subpath WASM de `libheif-js` | `image-worker-mcp` | `src/libheif-js.d.ts:1-11` | MIT | **SOLO REFERENCIA** | — | FileX es Python; la técnica no aplica. Lo que sí traslada: `sharp` prebuilt **no trae libheif por la licencia HEVC**, así que HEIC necesita un decodificador aparte. Dato de planificación para la matriz de formatos |
| Puente libheif → sharp por píxeles crudos | `image-worker-mcp` | `src/tools/sharp.ts:102-141` | MIT | **SOLO REFERENCIA** | — | El `channels: 4` está **hardcodeado con el comentario admitiendo la suposición** (`:133`: `// Assuming RGBA, common for HEIF decoders`). Se lee para entender el camino, no se copia |
| Procesar solo `decodedImages[0]` de un HEIC | `image-worker-mcp` | `src/tools/sharp.ts:110` | MIT | **DESCARTAR** | — | Ignora bursts y Live Photos, que es **precisamente lo que un HEIC de iPhone suele contener**. Y hay un bug encadenado: al fijar `inputFormat = 'heic'` (`:127`), sin `format` explícito el `outputFormat` cae a `'heic'`, que no matchea ningún `case` (`:226-243`) → **convertir un HEIC sin especificar salida siempre falla** (`:244-245`) |
| Binarios de prueba versionados en el repo | `video-audio-mcp` | `tests/sample.mp4` (10 498 677 bytes) | MIT | **DESCARTAR** | — | Y encima referencia un `SAMPLE_VIDEO_2 = "sample2.mp4"` (`tests/test_video_functions.py:45`) **que no existe en el repo**, con el `shutil.rmtree` del teardown comentado (`:114-118`): la suite deja basura |
| `upload_image` — leer una ruta arbitraria y **subirla a un bucket** sin comprobar que sea una imagen | `image-worker-mcp` | `src/tools/upload.ts:69-99`, `:129` | MIT | **DESCARTAR** | — | Un `imagePath: '~/.aws/credentials'` se lee y se sube. **La lectura arbitraria en el caso texto es una fuga hacia el contexto; aquí es una fuga hacia fuera de la máquina.** Ironía a aprender: los backends de nube **sí** tienen guard de sobrescritura (`s3.ts:56-74`), y el disco local del usuario no tiene ninguno |
| `normalizeFilePath` presentado como saneado de rutas | `image-worker-mcp` | `src/utils.ts:72-89` | MIT | **DESCARTAR** | — | **No es una función de seguridad**: solo des-escapa caracteres de shell, un parche para cuando el modelo pega una ruta copiada de una terminal. En Windows **corrompe rutas legítimas con backslash**. El módulo `path` de Node ni se importa en todo `src/` |
| `fetchImageFromUrl` sin `AbortController`, sin límite de bytes, sin bloqueo de rangos privados | `image-worker-mcp` | `src/utils.ts:94-127` (`:116-117` hace `arrayBuffer()` de lo que sea) | MIT | **DESCARTAR** | — | El mismo SSRF de markitdown-mcp medido en `bench/mcp-ergonomia.md` §6, y en una herramienta también sin `openWorldHint` |

### 1.G Recuento

| Veredicto | Filas |
|---|---:|
| **COPIAR TAL CUAL** | 22 |
| **ADAPTAR** | 27 |
| **SOLO REFERENCIA** | 11 |
| **DESCARTAR** | 30 |
| **Total catalogado** | **90** |

Reparto por repo de origen: `servers` (filesystem + everything + fetch) **40**, `ffmpeg-mcp-lite` **15**,
`image-worker-mcp` **12**, `kordoc` **9**, `video-audio-mcp` **4**, `markitdown_mcp_server` **3**, `markitdown`
oficial de Microsoft **1**, filas compartidas por varios repos **4**, sin precedente **2**.

Dos filas de la sección 1.D («devolver la imagen como `ImageContent`» y «umbral contenido/asa») están contadas como
DESCARTAR porque el precedente se descarta, pero **son huecos, no piezas**: no hay nada que llevarse y el trabajo es
propio de FileX.

---

## 2. Las 6 preguntas transversales de `PRUEBAS-MCP-REFS.md` §4

Cada afirmación va marcada **LEÍDO** (hay dato en el análisis de código, con cita) o **PENDIENTE** (hace falta
ejecutar, y va al entregable `bench/mcp-refs-ejecucion.md`).

### Pregunta 1 — ¿Qué se devuelve tras convertir un binario?

**Respondida por la lectura. Es la pregunta que mejor ha quedado cerrada.**

- **LEÍDO** — Los tres repos multimedia devuelven **el asa, no el contenido**, y llegaron ahí **por necesidad
  física, no por diseño**: `video-audio-mcp/server.py:33` y las otras 26, `ffmpeg-mcp-lite/tools/convert.py:66`,
  `image-worker-mcp/src/tools/sharp.ts:278-297`.
- **LEÍDO** — La regla 1 de FileX **no necesita defenderse en el caso binario**: `tests/sample.mp4` son 10 498 677
  bytes → ~14 M de caracteres en base64 → millones de tokens. Dos órdenes de magnitud por encima de cualquier
  ventana. En texto el asa era una optimización de 2 368×; en binario es la única opción.
- **LEÍDO** — La regla 2 («el asa es una ruta en disco, no una clave en memoria») queda confirmada por unanimidad:
  **ninguno de los cuatro repos tiene caché de asas en memoria**, y el artefacto ya existe en disco como producto de
  la conversión. En binario el asa es gratis.
- **LEÍDO** — **Ninguno la construye bien.** Es prosa, con la redacción cambiando según el camino interno; el único
  objeto estructurado es el de `image-worker-mcp` (`sharp.ts:278-297`) y lleva base64 dentro; solo
  `ffmpeg-mcp-lite/tools/compress.py:71-81` mide algo del **fichero producido**.
- **PENDIENTE** — Medir con `tiktoken` cuántos tokens devuelve realmente cada herramienta tras convertir un vídeo
  del corpus, para comparar con los 85 259 de markitdown y los 36 de docling ya medidos.
- **PENDIENTE** — Confirmar el bug inferido de `overwrite_output`: `video-audio-mcp` no pasa `-y` en las llamadas
  vía `ffmpeg-python` y sí en los siete `subprocess` crudos (`server.py:898`, `:915`, `:956`, `:1001`, `:1022`,
  `:1434`, `:1547`). **Repetir la misma conversión a la misma ruta debería fallar.** Inferido del código, no
  ejecutado.

### Pregunta 2 — ¿Cuántas herramientas saturan al modelo?

**Respondida a medias: el coste está estimado, el efecto sobre la elección del modelo no se ha probado.**

- **LEÍDO** — El caso extremo existe y son **27 herramientas planas** (`grep @mcp.tool` = 27 ✔). Coste de catálogo
  **estimado por caracteres en ≈3 610 tokens**, frente a **≈811 de las 8 de `ffmpeg-mcp-lite`** cubriendo el 80 %
  del mismo dominio. **4,5× más barato.**
  > ⚠️ **MEDIDO después, y las estimaciones se quedaron cortas por más del doble.** `RESULTADOS-MCP.md` §4 sondeó
  > los catálogos reales con `tiktoken`/`o200k_base`: **7.964 tokens** las 27 y **2.322** las 8. La razón por la que
  > la estimación fallaba está en el propio aviso de la línea siguiente: no contaba el envoltorio JSON Schema.
  > **Las cifras vigentes son las de `RESULTADOS-MCP.md` §4.** La proporción, en cambio, aguanta: 3,4× en vez de 4,5×.
- **LEÍDO, con reserva** — Estas dos cifras son **estimaciones por caracteres (nombre + firma + docstring ÷ 4)**,
  declaradas como tales en el análisis de origen, y son **cotas inferiores**: el catálogo real añade el envoltorio
  JSON Schema. Las cifras de contraste (5 280 tokens / 19 herramientas de docling) sí están medidas.
- **LEÍDO** — La saturación no es solo de tokens: **cinco nombres empiezan por `set_video_audio_track_…`** y
  compiten en el espacio de decisión del modelo, cuando `convert_video_properties` (`server.py:114`) ya los cubre
  todos con 11 argumentos.
- **LEÍDO** — La herramienta más cara del catálogo es `concatenate_videos`: **≈480 tokens solo de docstring**
  (`server.py:778-812`), porque enumera los 37 efectos `xfade` uno a uno — y los repite dos veces más.
- **PENDIENTE, y es lo que la fase 1 no puede responder** — **El efecto en la *elección* del modelo.** Ningún dato
  de lectura dice si con 27 herramientas el modelo elige peor. Requiere ejecutar el servidor y darle tareas
  ambiguas. Es la medida que justifica o refuta el objetivo de 4 herramientas de la regla 5.
- **PENDIENTE** — Medir el catálogo real de los dos servidores con `tiktoken` para convertir las estimaciones en
  cifras.

### Pregunta 3 — ¿Cómo se agrupa el dominio?

**Respondida por la lectura, y con ganador claro.**

- **LEÍDO** — `video-audio-mcp`: **plano**. Las 27 en el espacio de nombres global de un `FastMCP` (`server.py:10`).
  Los comentarios de sección (`:245`, `:330`, `:483`, `:773`, `:1221`) y las cuatro categorías del README
  **no llegan al protocolo**: el cliente recibe las 27 o ninguna.
- **LEÍDO** — `ffmpeg-mcp-lite`: **un fichero por herramienta bajo `tools/`, registro explícito en un `server.py`
  de 29 líneas** ✔. Agrupa por **intención del usuario** (convertir, comprimir, recortar, extraer, unir), no por
  parámetro de ffmpeg. **Es la forma que FileX necesita.**
- **LEÍDO** — Ninguno de los cuatro tiene **grupos cargables** como el argumento `conversion` de docling-mcp, que en
  `bench/mcp-ergonomia.md` §3.2 recortó el catálogo un 83 % (5 280 → 880 tokens) y el arranque de 6,0 s a 1,8 s.
- **LEÍDO** — La separación `services/` frente a `tools/` de `image-worker-mcp` **no es la que parecía**:
  `services/` son backends de subida a nube, no lógica de conversión. `resize_image` no tiene costura ninguna —
  `ImageProcessor` (`sharp.ts:60-315`) mezcla E/S, decodificación, transformación y **serialización de la respuesta
  MCP** (`:278-297`), y no es extraíble sin arrastrar el SDK.
- **PENDIENTE** — Si los grupos cargables merecen la pena en FileX depende de si el catálogo real de 4 herramientas
  se acerca a los ≈1 000 tokens presupuestados. Se sabrá al medirlo.

### Pregunta 4 — ¿Cómo se confina el sistema de ficheros?

**Respondida por la lectura, y es el mayor hallazgo del carril.**

- **LEÍDO** — La lista blanca de raíces con denegación por defecto y resolución canónica **existe, está probada y es
  reutilizable**: `path-validation.ts:11-86` (86 líneas de lógica pura) + `lib.ts:99-140`, con ~1 000 líneas de
  tests. **No hay que diseñarla desde cero** (§3.2).
- **LEÍDO** — El orden importa y es copiable: **predicado léxico antes de tocar el disco** (`lib.ts:107-111` ✔),
  luego `realpath` y **segunda aplicación del predicado sobre la ruta real** (`:116`, `:118`), y **devolver la ruta
  canónica**, no la pedida (`:121`).
- **LEÍDO** — La referencia **documenta sus propios huecos como tests**: TOCTOU en lectura
  (`__tests__/path-validation.test.ts:932` — se valida `readable.txt`, se sustituye por un enlace a un fichero de
  fuera, y la lectura devuelve `SECRET CONTENT`), padres enlazados (`:784`) y escritura (`:679`). Mitiga en
  escritura con `'wx'` + `rename` atómico; **no hay mitigación equivalente para lectura**.
- **LEÍDO** — **FileX tiene el TOCTOU peor que la referencia.** Allí la ventana son microsegundos; en FileX, entre
  validar la ruta y que ffmpeg termine de leerla pasan **minutos**, y la lectura la hace **otro proceso que no sabe
  nada de la allowlist**. Estrategia: copiar la entrada al staging privado tras validarla y pasar al binario externo
  solo la ruta del staging.
- **LEÍDO** — De los cuatro repos de conversión, **tres no tienen confinamiento de ninguna clase**. El único que
  tiene algo es `ffmpeg-mcp-lite`, y **solo en la salida y solo en 5 de 8 herramientas**, con fuga en
  `merge.py:38-39` y `subtitles.py:72-73`; **la entrada no está confinada en ninguno de los ocho**.
- **LEÍDO** — Tres huecos de Windows que la referencia **no** cubre: comparación case-sensitive (falso negativo, no
  bypass), nombres de dispositivo reservados (`CON`, `NUL`, `AUX`, `COM1-9`, `LPT1-9` — cero apariciones en todo el
  directorio) y ADS (`fichero.txt:oculto`).
- **PENDIENTE** — Probar `../../` y rutas absolutas contra cada servidor de multimedia y contrastar con lo que hace
  `filesystem`. La lectura predice que los tres de multimedia caen; falta confirmarlo.
- **PENDIENTE, marcado ya en origen** — Que el SDK Python del MCP exponga `session.list_roots()` y la notificación
  equivalente está **[no verificado]** en los dos análisis. Es un bloqueante del diseño de roots.

### Pregunta 5 — ¿Qué mensaje de error llega al modelo?

**Respondida por la lectura, y el resultado es unánime y malo.**

- **LEÍDO** — **Los cuatro repos reenvían el `stderr` crudo del motor.** `video-audio-mcp` llega a **concatenar dos
  volcados completos de ffmpeg** en una sola cadena (`server.py:344`), en nueve herramientas. 1,5–3 KB por fallo,
  500–1 000 tokens.
- **LEÍDO** — **`video-audio-mcp` devuelve `isError: false` en todos sus fallos, siempre**, porque atrapa
  `Exception` y devuelve una cadena que empieza por «Error». Ninguna excepción propaga nunca. La única forma que
  tiene el agente de distinguir éxito de fracaso es **buscar una palabra inglesa dentro de una frase**.
- **LEÍDO** — **`ffmpeg-mcp-lite` lo hace bien en la forma** (`raise` → `isError: true`, `convert.py:63-64`) y mal
  en el contenido (`stderr.decode()` entero dentro).
- **LEÍDO** — **La mejor pieza del carril es de kordoc y es exclusiva del MCP**: `describeError` (`mcp.ts:84-100`
  ✔), tabla `errno` → frase en lenguaje natural **sin la ruta**. La CLI no la tiene. Es la confirmación práctica de
  que el modelo necesita otro texto que la persona.
- **LEÍDO** — El pecado de docling-mcp (`pip install openai-whisper`) **tiene precedente en kordoc, tres veces**
  (`index.ts:198`, `image-ocr.ts:88`, `rasterize.ts:35`), y el comentario de `image-ocr.ts:85` dice que es
  deliberado. Pero **una de las tres apunta a la solución**: `rasterize.ts:34-36` acompaña la instrucción de
  instalación con una alternativa in-band que el modelo puede ejecutar ahora mismo.
- **LEÍDO** — Los mensajes de la referencia oficial **tampoco se pueden copiar**: distinguen «prohibido» de «no
  existe» (`lib.ts:131` vs `:135`), publican la allowlist completa y filtran rutas resueltas de fuera del sandbox
  (`:119`).
- **PENDIENTE** — Los textos exactos de kordoc (§E.5 del análisis de multimedia) están **reconstruidos del código,
  con longitudes por conteo de caracteres, no medidas en ejecución**. Marcado así en origen.
- **PENDIENTE** — El volumen real en tokens de un fallo de ffmpeg reenviado (los 500–1 000 son estimación).

### Pregunta 6 — ¿Se puede devolver una imagen como contenido?

**Es la única de las seis que la lectura NO ha podido responder. No hay precedente.**

- **LEÍDO** — `image-worker-mcp` era el único candidato y **no emite `ImageContent`**: `grep "type: 'image'"` sobre
  `src/` → **0 resultados** ✔. Devuelve base64 como **texto plano dentro de un JSON**, con el prefijo
  `data:${mimeType};base64,` que `bufferToBase64` antepone (`utils.ts:63-65`) y que hace la cadena **inválida** para
  el campo `data` de un `ImageContent` MCP.
- **LEÍDO** — **El peor de los dos mundos**: el modelo paga el coste en tokens de la imagen y no obtiene la
  capacidad multimodal. El contrato está fijado por sus propios tests (`tests/tools/sharp.test.ts:364` asserta
  `startsWith('data:image/jpeg;base64,')`).
- **LEÍDO** — **No hay ningún límite de tamaño en todo el repo.** Verificado en negativo: sin `maxSize`, sin umbral
  en bytes, sin truncado, sin fallback. `constants.ts` son 11 líneas y no contiene ningún cap. El único freno es un
  booleano `outputImage` con default `false` (`sharp.ts:50`) que **decide el modelo**: puesto a `true` sobre un PNG
  de 5 MB, se serializa el 100 % del base64 —**además indentado con `null, 2`** (`:293`)— y se manda por stdio.
- **LEÍDO** — Lo único que mantiene pequeña la salida en la práctica es un accidente: los defaults
  `DEFAULT_WIDTH = 800` / `DEFAULT_HEIGHT = 600`. Y ni eso es fiable: si el modelo pasa solo `width`, `height` queda
  `undefined` y el default no aplica (`sharp.ts:159-165`).
- **PENDIENTE, y es la única medida nueva que hace falta** — **Calcular la frontera.** Un thumbnail de 800×600 JPEG
  q80 ronda los 60 KB → ~80 KB de base64 → **decenas de miles de tokens**. Incluso el caso «bueno» es caro. Hay que
  medirlo con `tiktoken` sobre imágenes reales del corpus para fijar el cap en constantes, y comparar el coste de un
  `ImageContent` real contra el de la misma imagen como bloque de imagen nativo del cliente.
- **PENDIENTE** — Confirmar en ejecución que el SDK Python acepta `ImageContent` con base64 puro y qué hace el
  cliente con él.

---

## 3. Contradicciones y correcciones

Seis. Ninguna suavizada. Las tres primeras afectan a decisiones, no a redacción.

### 3.1 `modelcontextprotocol/servers` NO es MIT — y el proyecto entero lo da por MIT

**Contradicción con `PRUEBAS-MCP-REFS.md` §2 y §3.1, con `analysis/00-mcp-filesystem.md` §0 y con
`analysis/00-licencias.md`.**

Los tres documentos afirman que la referencia oficial del protocolo es **MIT**. `PRUEBAS-MCP-REFS.md` §2 lo repite
tres veces («es MIT, y estaba a un `ls` de distancia»; «Es MIT, es la referencia oficial»). El análisis de filesystem
lo usa como fundamento de todos sus veredictos de copia.

**El fichero de licencia del clon dice otra cosa** (`repos/mcp-refs/servers/LICENSE:1-5`, verificado):

> *The MCP project is undergoing a licensing transition from the MIT License to the Apache License, Version 2.0
> ("Apache-2.0"). All new code and specification contributions to the project are licensed under Apache-2.0.
> Documentation contributions (excluding specifications) are licensed under CC-BY-4.0. Contributions for which
> relicensing consent has been obtained are licensed under Apache-2.0. Contributions made by authors who originally
> licensed their work under the MIT License and who have not yet granted explicit permission to relicense remain
> licensed under the MIT License.*

Y los `package.json` no declaran licencia: `"license": "SEE LICENSE IN LICENSE"` en la raíz, en `src/filesystem/` y
en `src/everything/` (verificado).

**Consecuencias prácticas, que son menores pero reales:**

1. **No invalida ningún veredicto de esta tabla.** Apache-2.0 es permisiva y compatible con lo que FileX quiere
   hacer, igual que MIT.
2. **Sí cambia las obligaciones.** Apache-2.0 exige conservar el aviso de licencia, marcar los ficheros modificados
   y propagar el `NOTICE` si existe; MIT solo exige el aviso de copyright. **La licencia por fichero es ambigua**
   (depende de si el autor original consintió el relicenciamiento), así que lo seguro es **tratar todo lo tomado de
   `servers/` como Apache-2.0**, cuyas obligaciones son un superconjunto de las de MIT.
3. **`analysis/00-licencias.md` no lista `modelcontextprotocol/servers` en absoluto.** Es el repo del que este
   documento propone copiar más piezas. **Hay que añadirlo a esa tabla** — no lo hago yo porque este trabajo escribe
   un solo fichero.
4. **La documentación de `everything/docs/features.md` es CC-BY-4.0**, no código. Las filas de la tabla maestra que
   citan `docs/features.md` describen capacidades del protocolo, no texto reutilizable; ninguna implica copia.

### 3.2 `PLAN-ORQUESTADOR.md` §4.6 sigue diciendo que la lista blanca «hay que inventarla», y es falso

**Contradicción viva, no corregida en el documento de destino.**

`PLAN-ORQUESTADOR.md:266-271`, bajo el epígrafe **«Seguridad — lo que hay que inventar»**, afirma: *«Ninguno de los
seis orquestadores recibe una ruta del sistema de ficheros… No hay de dónde copiar esto: lista blanca de raíces,
denegar por defecto, resolución canónica (`realpath`) antes de decidir»*. Lo mismo en `ANALISIS-COMPLETO.md:593`.

Está **desmentido dos veces** (`PRUEBAS-MCP-REFS.md` §2 y `analysis/00-mcp-filesystem.md` §0) y **sigue en pie en el
plan de construcción**, que es el documento que se lee al implementar el hito 4. La afirmación de que «ninguno de los
seis orquestadores» la resuelve es cierta y sigue siéndolo — el error es la conclusión: la referencia no estaba entre
los orquestadores, estaba en `mcp-refs/`.

**Precisión que ninguno de los dos desmentidos hace del todo:** la corrección es **parcial, no total**.

- **Falso** que haya que inventar la lista blanca: `path-validation.ts:11-86` + `lib.ts:99-140` la resuelven, con
  ~1 000 líneas de tests.
- **Cierto** que hay que inventar el **error indistinguible entre «prohibido» y «no existe»**: la referencia oficial
  hace lo contrario, con cuatro mensajes distinguibles, la allowlist completa interpolada y las rutas de fuera del
  sandbox impresas (`lib.ts:110`, `:119`, `:131`, `:135`).
- **Cierto**, y es lo que ninguno de los dos documentos dice, que **lo genuinamente nuevo de FileX no es el
  confinamiento sino lo que hay detrás**: elegir rutas de escritura, **lanzar procesos externos** sobre ellas
  (option injection con nombres como `--outdir=/etc`, límites de recursos del hijo, aislamiento de LibreOffice y
  ghostscript) y **procesar contenido hostil** (zip bombs en `.docx`/`.xlsx`/`.epub`, zip slip, XXE en SVG/OOXML).
  De eso no hay nada que copiar en ningún repo de los seis, y es un problema distinto y más pequeño que «diseñar la
  lista blanca desde cero».

### 3.3 `00-mcp-patrones.md` presenta como modélico un `cleanup_memory()` que `bench/mcp-ergonomia.md` midió roto

**Contradicción directa entre dos documentos vigentes de FileX.**

`analysis/00-mcp-patrones.md` pone a docling-mcp como el ejemplo a seguir e incluye en el bloque de código:

```python
cleanup_memory()      # libera los modelos tras convertir
```

y lo eleva a regla: *«**4.** Liberar los modelos GPU tras el trabajo (`cleanup_memory()`), o el sidecar acapara los
12 GB de la 3060 indefinidamente.»*

`bench/mcp-ergonomia.md`, regla 14, **lo midió y dice lo contrario**: *«docling-mcp instancia
`LocalDocumentConverter()` en **cada** llamada (3 conversiones → 3 × `Creating DocumentConverter` en `stderr`),
pagando ~2 s de reconstrucción del pipeline por conversión, mientras su `cleanup_memory()` es un `gc.collect()` que
no libera la VRAM. Lo peor de ambos mundos.»*

**Resolución: manda la medida.** La regla 4 de `00-mcp-patrones.md` es correcta como **objetivo** y falsa como
**cita**: `cleanup_memory()` de docling-mcp no es la implementación de referencia, es el contraejemplo. La forma
correcta está en la regla 14 medida: motor a nivel de módulo, reutilizado, y **descarga por temporizador explícito**,
no un `gc.collect()` tras cada llamada.

Lo mismo, en menor grado, con el resto de la presentación de docling-mcp en `00-mcp-patrones.md` como «lo resuelve
bien»: su asa es un `dict` del proceso que muere con el servidor (regla 2), y una clave inválida **devuelve la lista
completa de claves vivas** (regla 10). Es el mejor de los medidos en el eje del asa y no un modelo global.

**Matiz nuevo que aporta el carril binario, y que `00-mcp-patrones.md` no puede saber:** la regla 14 **no aplica a la
mitad binaria del catálogo**. ffmpeg es un proceso externo por llamada, sin estado caliente ni VRAM que liberar.
El régimen de motor caliente es **por motor, no por servidor**: aplica a OCR, ASR y superresolución; no a ffmpeg ni
a ImageMagick.

### 3.4 Los dos análisis dan respuestas incompatibles a «cómo se devuelve la salida»

**Contradicción entre `00-mcp-filesystem.md` §B.4 y `00-mcp-multimedia.md` §"Regla 2".** No la ve ninguno de los dos,
porque cada uno leyó un carril.

- **`00-mcp-filesystem.md` §B.4** clasifica `resource_link` como *«**la respuesta correcta** para un conversor. En
  vez de devolver 40 MB en base64 dentro del `CallToolResult` (o una ruta que el cliente quizá no puede leer), se
  devuelve un enlace a un recurso»*, con prioridad **Alta**, y lo llama *«literalmente el caso de uso de FileX con
  gzip en vez de una conversión»*.
- **`00-mcp-multimedia.md`** concluye lo contrario: *«El asa debe ser una ruta en disco… Confirmada por unanimidad y
  sin excepciones»*, y como argumento añadido que en binario el artefacto **ya existe en disco**.

**El código resuelve la contradicción, y a favor del segundo.** Verificado en
`everything/tools/gzip-file-as-resource.ts:94-121`: el recurso de sesión se registra con
`const blob = compressedBuffer.toString("base64")` (`:96`), y con `outputType:"resource"` ese blob **va entero dentro
del `CallToolResult`** (`:113-119`). Es decir: el patrón que §B.4 propone para no devolver 40 MB en base64
**devuelve 40 MB en base64** en una de sus dos ramas, y en la otra (`resourceLink`) deja el blob completo en memoria
del servidor esperando a que el cliente lo lea — momento en el que lo leerá también como base64.

**Resolución para FileX:**

1. **Por defecto, y para todo artefacto binario: asa = ruta en disco.** No negociable, por el argumento físico de la
   pregunta 1.
2. **`resource_link` sí, como capa adicional y sin blob**, apuntando a un recurso que el cliente lee bajo demanda,
   **solo por debajo de un cap explícito de bytes** — y ese cap es el mismo que falta calcular en la pregunta 6.
3. **`resource` con blob embebido: nunca** para salidas binarias.

El valor de §B.4 no se pierde: lo que aporta de verdad son los **recursos de sesión** (`resources/session.ts:32-80`)
como forma de no ensuciar el disco del usuario ni obligar al LLM a elegir una ruta de escritura. Esa parte sigue en
pie y está en la tabla como **ADAPTAR**.

### 3.5 `PLAN-ORQUESTADOR.md` §4.4 se contradice consigo mismo: catálogo generado frente a cuatro herramientas

En el mismo apartado, dos viñetas:

> - **Generada desde el registro**, no escrita a mano — patrón del `McpToolCatalog` de Stirling-PDF, que escanea sus
>   endpoints y los publica como herramientas. Un motor nuevo aparece como herramienta sin tocar la capa MCP.
> - **Pocas herramientas**: `convert`, `inspect`, `list_targets`, `batch`.

**Son incompatibles tal como están escritas.** «Un motor nuevo aparece como herramienta» es exactamente el mecanismo
que produce las 27 herramientas planas de `video-audio-mcp`, y el criterio de aceptación del hito 4 («añadir un motor
no toca la capa MCP») presiona en la misma dirección. El carril binario es la evidencia de dónde acaba eso: 27
herramientas **7.964 tokens medidos** frente a 8 con **2.322** cubriendo el mismo dominio, **porque una agrupa por
parámetro del motor y la otra por intención del usuario**. (Cifras de `RESULTADOS-MCP.md` §4, medidas con `tiktoken`;
las ≈3 610 / ≈811 que se estimaron por caracteres en la fase de lectura eran cotas inferiores.)

**Resolución, y es una decisión de diseño que hay que tomar antes del hito 4:** del registro se genera **el contenido
de los esquemas** —los `Literal`/`enum` de formatos de origen y destino, la lista de motores disponibles, la matriz
de conversión—, **no el número de herramientas**. Las herramientas siguen siendo cuatro, escritas a mano; un motor
nuevo aparece como un valor más en un `enum`, no como una herramienta. Eso satisface las dos viñetas y el criterio de
aceptación del hito 4 sin violar la regla 5.

Refuerzo desde el código: `ffmpeg-mcp-lite` acota el espacio con `Literal` en la firma
(`compress.py:12-14`, `audio.py:12`, `frames.py:14`) y con eso **el mensaje de error que enumera alternativas sobra**.
Un `enum` generado desde el registro es la versión FileX de eso.

### 3.6 Errores de hecho en los documentos de origen (menores, pero no se repiten como hechos)

Verificados por mí en el clon. Ninguno cambia un veredicto.

| Documento | Dice | Es | Evidencia |
|---|---|---|---|
| `PRUEBAS-MCP-REFS.md` §3.3 | `ffmpeg-mcp-lite/tools/` tiene 6 ficheros (`audio, compress, convert, frames, info, merge`) y `tests/` 6 | **8 herramientas y 8 ficheros de test**: faltan `trim.py`/`test_trim.py` y `subtitles.py`/`test_subtitles.py` | `ls` del clon; `server.py:5-24` registra las 8 ✔ |
| `PRUEBAS-MCP-REFS.md` §3.3 | *«`tests/` … **Ninguno de los otros MCP de conversión tiene suite de pruebas.**»* | **Falso.** `video-audio-mcp/tests/test_video_functions.py` son **763 líneas y 29 tests**, e `image-worker-mcp` tiene `tests/` con 6 ficheros, incluidos **2 de integración con un `.heic` real**. El análisis de multimedia ya lo desmiente en su §A.7 («Sí tiene tests, y el enunciado de esta tarea decía que no») | `00-mcp-multimedia.md` §A.7, §B.2 |
| `PRUEBAS-MCP-REFS.md` §3.3 | Sigue siendo cierto que el `tests/` de `ffmpeg-mcp-lite` es «el activo más valioso del repo» | **Matizado.** Lo valioso es su `conftest.py`; **la profundidad de sus asserts es peor** que la de `video-audio-mcp`: solo `test_info.py:15-29` mira dentro del resultado, mientras que `video-audio-mcp` verifica duraciones con `ffprobe`. Lo copiable es la **combinación** de los dos | tabla §1.F |
| `00-mcp-multimedia.md` cabecera §B | *«470 líneas de `src/`, 8 herramientas, 9 ficheros»* | **710 líneas y 13 ficheros** en `src/` (8 herramientas = 644 líneas; + `config.py` 23, `server.py` 29, tres `__init__`/`__main__`) | `wc -l` sobre el clon ✔ |
| `00-mcp-multimedia.md` §A.5 | *«Se valida existencia con `os.path.exists()` en 8 sitios»* y a continuación **lista 11 líneas** | **11 apariciones**, repartidas en 9 herramientas. La cifra «8» del texto es un desliz; las citas son correctas | `grep -c` = 11 ✔ |
| `PRUEBAS-MCP-REFS.md` §1 y `00-mcp-multimedia.md` | Volúmenes: 2 494 / 1 204 / 3 400 líneas frente a «`server.py` 1 649» y «`src/` 470» | **No se contradicen, miden cosas distintas**: los primeros son totales de repo (verificados: 2 494, 1 204, 3 400, 1 501 ✔), los segundos son del núcleo. Conviene no mezclarlos al citar | `wc -l` ✔ |

---

## 4. Orden de adopción recomendado

Ligado a `PLAN-ORQUESTADOR.md` §7. El hito 4 es la capa MCP, pero **tres de estas piezas hay que llevárselas antes**,
porque son estructurales y reescribirlas después cuesta más.

### Antes del hito 4 — decisiones que condicionan el núcleo

| # | Qué | De dónde | Por qué ahora |
|---:|---|---|---|
| 1 | **Troceado `tools/<dominio>.py` + registro explícito, funciones sin decorador** | `ffmpeg-mcp-lite/server.py:1-29` | Es la forma del núcleo, no de la capa MCP. Adoptarlo en el **hito 1** hace que la CLI, el watcher y la API compartan las mismas funciones sin refactor. Coste ~2 h ahora; días si se pospone |
| 2 | **`isHeif` y, en general, detección por magic bytes** | `image-worker-mcp/src/tools/sharp.ts:96-99` | El **hito 3** (contrato de verificación) exige «firma real del fichero, no la extensión». Esta es la pieza literal, y también la necesita la **entrada** para elegir motor |
| 3 | **`conftest.py` con fixtures generados por el motor + un fichero de test por herramienta + asserts con `ffprobe`** | `ffmpeg-mcp-lite/tests/conftest.py:17-40` combinado con `video-audio-mcp/tests/test_video_functions.py:471-495` | El **hito 3** es «reproducir los tres fallos de los competidores y detectarlos». Sin asserts sobre propiedades del artefacto no se puede. La suite se monta antes de tener qué probar |
| 4 | **`ParseWarning` + enum de códigos de aviso** | `kordoc/src/types.ts:249-277`, `pdf/parser.ts:257-263` | El canal de avisos tiene que existir **en el núcleo** para que el hito 3 pueda emitir «convirtió, pero perdió la pista de subtítulos». Si se añade en el hito 4 hay que tocar todos los motores |

### Hito 4 — la capa MCP, en este orden

| # | Qué | De dónde | Por qué en esta posición |
|---:|---|---|---|
| 5 | **El confinamiento completo**: predicado puro, léxico-antes-que-E/S, doble validación, ruta canónica, rama ENOENT, allowlist con original y resuelta, fail-closed al arrancar | `filesystem/path-validation.ts:11-86`, `lib.ts:99-140`, `index.ts:41-88` | **Primero, y es lo primero de todo el hito.** El criterio de aceptación del hito 4 lo exige explícitamente. Es ~1 día de porte a Python, no un diseño desde cero (§3.2). Todo lo demás asume que existe |
| 6 | **Mensaje de error opaco único** + el detalle a stderr | trabajo propio; **lo contrario** de `lib.ts:110,119,131,135` | Va pegado al punto 5: si se implementa el confinamiento con los mensajes de la referencia, se hereda el oráculo. Media hora **si se hace a la vez**; una auditoría si se hace después |
| 7 | **Staging privado y copia de la entrada tras validarla** | trabajo propio; el TOCTOU está catalogado en `__tests__/path-validation.test.ts:679,784,932` | Es lo que cierra la ventana de minutos que FileX tiene y la referencia no. El binario externo nunca ve una ruta que el agente controle |
| 8 | **Las 4 herramientas con `Literal`/`enum` generados desde el registro** (§3.5) y salida confinada con nombre derivado | `ffmpeg-mcp-lite/tools/compress.py:12-14`, `config.py:13-21`, `convert.py:35-36` | Resuelve las dos viñetas contradictorias de `PLAN-ORQUESTADOR.md` §4.4. Y con `output_path` opcional: si falta, se deriva dentro de la raíz de salida y **la respuesta siempre dice cuál se usó** |
| 9 | **Asa como objeto estructurado** con `structuredContent`, incluyendo propiedades medidas **del fichero producido** | `image-worker-mcp/sharp.ts:278-297` (campos) + `ffmpeg-mcp-lite/compress.py:71-81` (métricas) + `everything/docs/features.md:19` (canal) | Un MP4 de 0 bytes, uno sin pista de audio y uno correcto son tres «éxitos» indistinguibles con el contrato de los cuatro repos. **Un solo canal**, nunca `content` y `structuredContent` con la misma carga |
| 10 | **`inspect` = `ffprobe` recortado** | `ffmpeg-mcp-lite/tools/info.py:46-88` | Es la regla 3 aplicada al binario y está prácticamente escrito. De miles de tokens a cientos |
| 11 | **`describeError` + anotaciones de herramienta** | `kordoc/src/mcp.ts:84-100`; `filesystem/index.ts:370,400,425,629` | Las dos piezas de mejor relación valor/coste del catálogo entero: ~1 h y ~30 min. Cierran el criterio de aceptación «un error de motor llega como mensaje accionable, nunca como `stderr` crudo» |
| 12 | **`raise` siempre**, con validación previa de mensajes cortos | `ffmpeg-mcp-lite/tools/convert.py:63-64`, `trim.py:28` | Disciplina, coste cero. Es lo único que tres de los cuatro repos hacen mal de forma sistemática |

### Después del hito 4 — lo que depende de medir o de otro hito

| # | Qué | Cuándo | Por qué no antes |
|---:|---|---|---|
| 13 | **Roots del protocolo**, intersecando con una allowlist de servidor inmutable | Hito 4 tardío o hito 7 | Bloqueado por un **PENDIENTE**: hay que confirmar `session.list_roots()` en el SDK Python. Hasta entonces, la allowlist se configura a mano |
| 14 | **Progress notifications y/o Tasks** | Hito 6 (sidecar), donde las conversiones pasan de segundos a minutos | En los hitos 1–4 ffmpeg e ImageMagick responden en segundos. El coste dominante pasa a ser el tiempo cuando entran OCR y ASR |
| 15 | **Elicitation** (contraseña de PDF, confirmación de sobrescritura, coste de GPU) | Hito 6 | Necesita casos reales de ambigüedad. Antes es infraestructura sin uso |
| 16 | **`ImageContent` con cap de bytes** | Tras medir la pregunta 6 | **No hay precedente y no hay cifra.** Implementarlo sin el cap medido es repetir el fallo de `image-worker-mcp` |
| 17 | **`resource_link` sin blob, bajo el mismo cap** | Tras el punto 16 | Depende de la misma medida (§3.4) |
| 18 | **`fetchSafely` + `validateDataURI` + bloqueo de rangos privados y revalidación de redirecciones** | Solo si FileX acepta URLs | La regla 13 dice red desactivada por defecto. Si no se activa, no hace falta |
| 19 | **Caché idempotente** | Hito 4 tardío | **Ningún repo de los seis tiene caché de ningún tipo**: hay que diseñarla desde cero. Y el matiz binario importa: hashear un MP4 de 4 GB cuesta segundos de E/S, así que la clave es `(tamaño + mtime + inode) + parámetros + versión del motor`, con el hash de contenido solo por debajo de un umbral — **corrige a `PLAN-ORQUESTADOR.md` §4.4 y a la regla 3 de `00-mcp-patrones.md`, que piden hash de contenido sin condición** |

### Si solo se hacen tres cosas

1. **Portar el confinamiento de `filesystem` a Python** (puntos 5, 6, 7). Es el único trabajo del carril que estaba
   presupuestado como «diseñar desde cero» y resulta ser un porte.
2. **Adoptar la estructura de `ffmpeg-mcp-lite`** (punto 1). Es la forma del proyecto entero, no solo de la capa MCP,
   y cuesta dos horas si se hace en el hito 1.
3. **Copiar `describeError` y el canal de avisos de kordoc** (puntos 4 y 11). Son las dos piezas que resuelven lo que
   los cuatro repos de conversión, sin excepción, resuelven mal.

---

## 5. Qué queda pendiente de ejecución

Resumen de los **PENDIENTE** de §2, para el entregable `bench/mcp-refs-ejecucion.md` (fase 2). Todos son Python o
Node, ligeros, **sin GPU**.

| # | Medida | Contra qué | Responde a |
|---:|---|---|---|
| 1 | Catálogo real con `tiktoken` de `video-audio-mcp` (27) y `ffmpeg-mcp-lite` (8) | Convierte las estimaciones ≈3 610 / ≈811 en cifras | Pregunta 2 |
| 2 | Tokens devueltos tras convertir un vídeo del corpus | Comparar con los 85 259 de markitdown y los 36 de docling | Pregunta 1 |
| 3 | **Efecto de 27 herramientas en la *elección* del modelo** ante tareas ambiguas | Es lo único que la lectura no puede responder | Pregunta 2 |
| 4 | `../../` y rutas absolutas contra los tres servidores de multimedia | La lectura predice que los tres caen | Pregunta 4 |
| 5 | Repetir la misma conversión a la misma ruta en `video-audio-mcp` | Confirmar el bug de `overwrite_output` inferido | Pregunta 1 |
| 6 | Coste en tokens de un `ImageContent` real frente al asa, sobre imágenes del corpus | **Fijar el cap de bytes.** No hay precedente ni cifra | Pregunta 6 |
| 7 | `session.list_roots()` y `notifications/roots/list_changed` en el SDK Python | Bloqueante del diseño de roots | Pregunta 4 |
| 8 | Soporte de Tasks (SEP-1686) en el SDK Python | Antes de comprometerse con la capacidad | §1.B |

Reglas de contención de `PRUEBAS-MCP-REFS.md` §5 que siguen vigentes para esa fase: `.mcp.json` **de proyecto**,
jamás la global; **un venv por servidor Python** (`mcp~=1.8.0` y `mcp>=2.0.0` no coexisten); no tocar `.venv-ai`,
`.venv-paddle` ni `.venv-mcp-md`.
