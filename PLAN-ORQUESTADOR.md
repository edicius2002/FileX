# FileX — Plan del orquestador

**Documento de traspaso.** Escrito para que una sesión sin contexto previo pueda leerlo y ponerse a construir de inmediato. Fecha: 19 de agosto de 2026.

> Si vienes de cero: lee las secciones 1, 2 y 3, y empieza por el hito 1 de la sección 7. El resto es referencia que consultarás sobre la marcha.

---

## 1. Qué es FileX y qué se decidió

**FileX** es un conversor universal de archivos, local-first, que se entrega como **servidor MCP + CLI + watcher de carpetas + API HTTP local**, sobre Windows con Docker/WSL2, aprovechando una **RTX 3060 de 12 GB**.

Cubre 12 categorías: ofimática↔PDF, markup, operaciones PDF, ebooks, imágenes normales y especiales, vídeo, audio, documento→texto para LLM, OCR, datos tabulares, y audio/vídeo→texto.

Se auditaron 22 repositorios a nivel de código y se ejecutaron en la máquina real. La conclusión que gobierna todo este plan:

> **Código de transmute, contenedor de gotenberg, patrones de SnapOtter, tabla de motores de ConvertX. Ningún repositorio sirve entero — por eso el núcleo se escribe de cero.**

El núcleo propio es exactamente lo que **nadie del ecosistema tiene**: un grafo de conversión con búsqueda de camino, una capa MCP pensada para agentes, uso real de la GPU, y verificación obligatoria de la salida.

### Los diferenciadores

> ⚠️ **Esta lista fue reevaluada.** Tras la fase de ejecución, dos huecos se debilitaron, uno hubo que reformularlo, y **apareció uno más fuerte que no estaba aquí: la verificación obligatoria de la salida**. La versión vigente, con la separación entre lo medido y lo pendiente, está en **`HUECOS.md`**. La tabla siguiente se conserva porque el **orden de construcción de la §7 no cambia** — el hito 3 ya era el contrato de verificación.

| # | Hueco | Evidencia medida | Coste |
|---|---|---|---|
| 1 | Grafo multi-salto | 0 de 7 orquestadores hacen búsqueda de camino. **2,93×** de cobertura (152 584 → 447 398 pares) con los mismos motores | Bajo |
| 2 | NVENC en vídeo | Ningún orquestador lo usa. **8,4×** en HEVC, 2,7–3,0× en H.264 | Muy bajo |
| 3 | MCP para agentes | El techo del sector en conversión invocable son **84 ⭐** (`video-audio-mcp`), que devuelve prosa sin metadatos y con `isError:false` siempre. **~2 400×** de diferencia en tokens entre patrones | Medio |
| 4 | OCR en GPU | Todos lo hacen en CPU. Resuelto: Docling + RapidOCR `backend="torch"`, **coste de infraestructura cero** | Bajo |

---

## 2. Estado del entorno (verificado, no asumir)

**Hardware:** RTX 3060 12 288 MiB, **compute capability 8.6**, driver 572.61 · 12 núcleos · Windows 10.

**Instalado nativamente:** `ffmpeg` N-121159 (con `--enable-gpl --enable-libx264 --enable-libx265 --enable-cuda-llvm`), `magick` (ImageMagick 7.1.2 Q16-HDRI), `gswin64c` (Ghostscript 10.07), Node 22.23.2, Go 1.22.5, CUDA toolkit 11.2, Docker 29.4.3, WSL2 (Ubuntu), Python 3.11.9.

**NO instalado:** vips, LibreOffice, Pandoc, Tesseract, qpdf, Calibre, Inkscape, DuckDB, uv, bun, cargo. **Y no hay gestor de paquetes** (ni winget, ni choco, ni scoop) — por eso lo que falte va en contenedor, no instalado a mano.

**Entornos virtuales del proyecto:**

| Ruta | Contenido |
|---|---|
| `.venv-ai/` | torch **2.6.0+cu124** (CUDA: True), docling 2.120.3, faster-whisper 1.2.1, rapidocr 3.9.2, easyocr 1.7.2, onnxruntime-gpu **1.22.0** |
| `.venv-paddle/` | PaddleOCR con su propio runtime CUDA (3,73 GB, aislado a propósito) |
| `.venv-mcp-md/` | markitdown-mcp (aislado: su `mcp~=1.8.0` es incompatible con el `mcp>=2.0.0` de docling) |

**Contenedores levantados:**

| Servicio | Puerto | Credenciales |
|---|---|---|
| SnapOtter | 1349 | `admin` / **`<CONTRASENA-REDACTADA>`** (cambiada: devolvía `403 MUST_CHANGE_PASSWORD` en toda la API) |
| ConvertX | 3100 | sin login |
| Gotenberg 8.36 | 3200 | sin auth |

**Restricción importante:** la VM de Docker tiene **2 vCPU y 1,9 GiB de RAM**, por decisión deliberada del usuario en su `.wslconfig` (documentada con comentarios). **No la cambies.** Consecuencia: los tiempos medidos dentro de Docker solo valen para comparar contenedores entre sí, nunca contra los nativos.

**GPU compartida:** hay una sesión de escritorio remoto activa (Chrome Remote Desktop + AnyDesk). El motor 3D nunca baja del 10 % y llega a picos del 50 %. **NVENC y NVDEC sí están libres.** VRAM realmente disponible: **~8,7 GB de los 12**.

---

## 3. La regla de las cuatro fuentes, desarrollada

### 3.1 Código → **transmute** (`repos/orchestrators/transmute/`, MIT)

Es el **único orquestador con licencia permisiva y arquitectura sana**. De aquí sale el esqueleto del registro.

#### Qué copiar literalmente

| Fichero | Líneas | Qué aporta |
|---|---:|---|
| `backend/registry/registry.py` | 303 | Auto-descubrimiento por reflexión sobre subclases, con `can_register()` |
| `backend/converters/converter_interface.py` | 113 | El contrato base de todo conversor |
| `backend/compressors/compressor_interface.py` | 107 | Comprimir no es convertir: mantener la separación |
| `backend/core/media_types.py` | — | Normalización y alias de tipos MIME |

El patrón de descubrimiento, que es el corazón:

```python
for _name, obj in inspect.getmembers(converters, inspect.isclass):
    if issubclass(obj, ConverterInterface) and obj is not ConverterInterface:
        if skip_unregisterable and not obj.can_register():
            continue          # el binario no está instalado: no se registra
        self.register_converter(obj)
```

**Por qué `can_register()` no es opcional en esta máquina:** solo hay 4 de los ~12 motores del ecosistema instalados. Sin auto-exclusión, FileX no arranca; con ella, arranca con capacidades reducidas y lo dice.

La interfaz a adoptar (`converter_interface.py:15-113`):

```python
class ConverterInterface:
    supported_input_formats: set = set()
    supported_output_formats: set = set()

    def __init__(self, input_file, output_dir, input_type, output_type): ...
    def can_convert(self) -> bool: ...
    @classmethod
    def can_register(cls) -> bool: ...          # ¿está el binario disponible?
    @classmethod
    def get_formats_compatible_with(cls, format_type) -> set: ...
    @classmethod
    def get_quality_options(cls) -> set: ...
    def convert(self, overwrite=True, quality=None) -> list[str]: ...
```

#### Qué adaptar

- **`_get_preferred_converter()`** (`registry.py:209`) resuelve la preferencia entre motores solapados con una lista explícita. **Sustituirlo por el coste de arista del grafo** (sección 4.1): el motor lo elige Dijkstra, no una tabla de preferencias a mano.
- El registro devuelve *un conversor*; FileX necesita que devuelva *un camino*. Es el cambio estructural principal.

#### Qué portar después (adaptadores de nicho que nadie más tiene)

En `backend/converters/`, y son la razón por la que transmute abre **categorías** aunque solo aporte +0,95 % de pares:

| Fichero | Categoría exclusiva |
|---|---|
| `fonttools_convert.py` | Fuentes tipográficas, matriz completa 4×4 (ttf/otf/woff/woff2) |
| `pysubs2_convert.py` | Subtítulos, 6×6, con manejo de FPS de MicroDVD |
| `pandas_convert.py` | Tabulares, 23→17 con `parquet`/`feather`/`orc`/`sqlite`/`dta`/`sav`/`xpt` |
| `email_convert.py` | Correo: `eml`/`msg` → 10 salidas |
| `ezdxf_convert.py`, `pkcs7_convert.py`, `tgs_convert.py`, `drawio_convert.py`, `archive_convert.py`, `cbz_convert.py` | Nichos varios |

#### Qué NO copiar

Su frontend, su capa k8s y su modelo de colas orientado a web. FileX es local-first.

---

### 3.2 Contenedor → **gotenberg** (MIT, ya levantado en `localhost:3200`)

**No reimplementes ofimática→PDF.** Gotenberg lo resuelve mejor y te ahorra instalar LibreOffice en Windows sin gestor de paquetes.

- **132 extensiones de LibreOffice** declaradas en `repos/orchestrators/gotenberg/pkg/modules/libreoffice/api/api.go`, frente a las 41 de ConvertX. 55 son exclusivas (StarOffice, Lotus, Visio, iWork, plantillas OpenDocument).
- **Mantiene LibreOffice residente** en lugar de arrancarlo por petición — que es justo lo que recomiendan las mediciones de arranque en frío.
- Verificado con el corpus: CSV con BOM → PDF y HTML → PDF, ambos correctos.

**Avisos verificados:**

- Declara **8 perfiles PDF/A pero solo 4 son producibles**; `pdfcpu`, `qpdf`, `pdftk` y `exiftool` llevan `// Convert is not available in this implementation`. No confíes en su catálogo: sondea.
- Su lista de extensiones lleva un `// FIXME: don't care` de sus propios autores y una errata de años (`.fopd` junto a `.fodp`, `api.go:839,842`). Al importarla, **filtra**.
- **Sin autenticación por defecto** sobre un endpoint que evalúa JavaScript arbitrario y hace de proxy SSRF. En localhost es asumible; no lo expongas.
- Arranca lento en WSL2: el `--libreoffice-start-timeout` por defecto de 20 s se queda corto (tarda 21,5 s). Usa **90 s** y `--libreoffice-auto-start=true`. Ya está así en `docker/`.

**Además, cópiale tres patrones de seguridad** (son los mejores del conjunto):

1. **Renombrado a UUID**: el nombre de fichero del usuario **nunca llega a `argv`**. Esto mata de raíz la clase entera de bugs de inyección.
2. **Muerte por grupo de procesos** con `Setpgid`: un motor colgado no deja huérfanos.
3. **Pool con semáforo y cola acotada**, no troceado por lotes.

---

### 3.3 Patrones → **SnapOtter** (`repos/orchestrators/SnapOtter/`, AGPL + CLA — **no copiar código**)

SnapOtter ya construyó el híbrido núcleo + sidecar Python al que llega este plan por su cuenta. Es la validación independiente más fuerte del diseño. **Copia los patrones leyendo, nunca las líneas**: su AGPL contamina y su CLA cede derechos a una empresa competidora.

#### Patrones a adoptar

| Patrón | Dónde leerlo |
|---|---|
| **Sidecar Python persistente** con proceso vivo, no arranque por invocación | `packages/ai/src/bridge.ts:280` (`PythonDispatcher`) |
| **Respaldo a proceso efímero** si el dispatcher muere | `bridge.ts:648` (`runPerRequest`), lógica en `896-919` |
| **IPC por NDJSON en stdin/stdout, con los binarios FUERA de la tubería** — solo viajan rutas | `ocr-runtime-dispatcher.ts:87` (límite duro de 64 KB por petición) |
| **Rotación sin cortar peticiones en vuelo**: `beginDrain()` cierra stdin solo con la cola vacía, y el candidato nuevo pasa un smoke test real antes de que el viejo drene | `ocr-runtime-dispatcher.ts` |
| **Aislar el proceso de IA** porque torch/CUDA reservan enorme espacio virtual | comentario en `apps/api/src/lib/env.ts:70` |
| **Corte de circuito**: 5 caídas en 60 s → desactivar permanentemente | `bridge.ts` |
| **`-dSAFER` universal** en Ghostscript | — |

#### Sus renuncias, que son tu ventaja

- **OCR bloqueado en CPU por diseño**: `ocr-runtime-dispatcher.ts:1028-1040`, `validateReadinessResult()` **lanza excepción** si `result.device !== "cpu"`.
- **No gestiona la VRAM en absoluto**: cero consultas proactivas de memoria de GPU en todo el repo. Las cinco coincidencias son *regex de detección de OOM*. `nvidia-smi` solo para leer el nombre de la tarjeta.
- **Recarga los pesos en cada llamada**: `packages/ai/python/dispatcher.py:290` ejecuta `exec(code, module_globals)` sobre un espacio de nombres nuevo. Solo sobrevive la caché de imports.
- Sus topes de memoria son de RAM del cgroup y **se desactivan en anfitriones con GPU** (`hq-memory-gate.ts:32`).
- Su runtime de OCR **no reinicia** tras fallo, sin backoff ni contador. **No repliques esto por omisión.**

→ **FileX necesita lo que SnapOtter no tiene: un registro LRU de modelos acotado por bytes de VRAM y con TTL de inactividad.** Con ~8,7 GB reales compartidos con el escritorio, no es un lujo.

---

### 3.4 Tabla de motores → **ConvertX** (`repos/orchestrators/ConvertX/src/converters/`, AGPL — **solo datos, no código**)

Sus tablas de formatos son **conocimiento acumulado, no código**: qué binario cubre qué familia. Eso sí es reutilizable.

**Los 20 motores del consenso del sector:**
`inkscape`, `libjxl`, `resvg`, `vips`, `libheif`, `xelatex`, `calibre`, `dasel`, `libreoffice`, `pandoc`, `msgconvert`, `dvisvgm`, `imagemagick`, `graphicsmagick`, `assimp`, `ffmpeg`, `potrace`, `vtracer`, `vcf`, `markitdown`.

**Cómo extraerlas:** parsear `export const properties = {...}` de cada `src/converters/*.ts`. **Sin límite de longitud en el identificador** — una primera extracción con `{1,12}` perdía 7 dialectos largos de pandoc (`markdown_strict`, `jats_articleauthoring`…). Cifras canónicas: **896 formatos de entrada, 503 de salida.**

| Motor | Entradas | Salidas | Exclusivas | Sin él se pierde |
|---|---:|---:|---:|---|
| ffmpeg | 473 | 202 | **422** | todo el audio y el vídeo |
| imagemagick | 245 | 183 | 78 | imagen heredada |
| graphicsmagick | 167 | 130 | 29 | metadatos y variantes TIFF |
| vips | 45 | 23 | 17 | imagen científica |
| libreoffice | 41 | 22 | 29 | ofimática heredada |
| pandoc | 40 | 58 | 31 | markup académico |
| calibre | 26 | 20 | 16 | ebooks y cómic |

**ffmpeg + ImageMagick cubren el 75 % de las entradas.** Por eso el hito 1 empieza por esos dos.

**Corrige su tabla al importarla** — se equivoca en las dos direcciones:

- **Promete lo que no cumple**: su `png→avif` con ImageMagick entrega un **PNG renombrado** con estado "Done" (bytes mágicos `89 50 4E 47`). Su `dasel` está roto (sintaxis v1 contra binario v2): **todas** sus conversiones de datos son inalcanzables pese a estar declaradas.
- **Oculta lo que sí sabe**: no declara `xlsx`/`xls`/`ods`/`ppt`/`odp` porque `libreoffice.ts` solo registra la familia `text:` (líneas 6 y 51), pero forzado por API usa `calc_pdf_Export` y produce un PDF correcto.

**Y no copies su despacho.** `main.ts:213-229`: el `break` rompe solo el bucle interno, así que gana el **último** conversor que coincide, no el primero. Para `png→jpg` gana ffmpeg sobre vips e ImageMagick. Es el bug que el grafo elimina por construcción.

---

## 4. Arquitectura del núcleo

### 4.1 Grafo de conversión — la pieza central

- **Nodos** = formatos. **Aristas** = `(motor, coste)`.
- **Coste** = combinación de tiempo estimado, pérdida de fidelidad, y si preserva texto/alfa/pistas. **No solo conectividad.**
- **Dijkstra** elige el camino.

Resuelve tres cosas de una vez: el multi-salto, la prioridad correcta entre motores solapados (el bug de ConvertX), y un mensaje explicable de "por qué no se puede" — valioso cuando quien pregunta es un agente.

**Calibrar el coste con datos reales** de `bench/salidas-referencia/referencia.json`: 46 reglas de regresión y **17 pérdidas catalogadas**, que distinguen *pérdida inevitable* (el alfa al pasar a JPEG) de *fallo del motor*. Esa distinción **es** la función de coste.

> **Salvedad a respetar:** los 447 398 pares alcanzables son un límite superior, no una promesa de fidelidad. Un camino de 3 saltos que rasteriza y destruye el texto debe puntuar peor que "no se puede".

### 4.2 Contrato de verificación post-conversión — **no negociable**

Después de **cada** conversión, comprobar:

1. **Firma real del fichero** (bytes mágicos), no la extensión.
2. **Flujos esperados frente a obtenidos** (`ffprobe`): número de pistas de vídeo, audio y subtítulos.
3. **Propiedades declaradas frente a medidas**: dimensiones, profundidad de bits, canal alfa, ppp, bitrate, duración.

Los tres fallos más graves encontrados en los competidores —el `.avif` que era PNG, la pista de audio perdida, y las degradaciones de bits/ppp/bitrate— **los habría atrapado los tres**.

**Corolario contraintuitivo:** *un recurso alternativo sin verificación es peor que no tenerlo*, porque convierte un fallo honesto en uno silencioso. Es literalmente lo que le pasa a ImageMagick dentro de ConvertX: emite un *warning* con código de salida 0 y devuelve el formato origen.

### 4.3 Registro y sondeo de capacidades

- Registro por reflexión con `can_register()` (de transmute).
- **Sondear en ejecución, nunca deducir del binario.** `av1_nvenc` aparece en `ffmpeg -encoders` y falla con `No capable devices found`, porque Ampere tiene decodificador AV1 pero no codificador. Sondear una vez, cachear el resultado, y degradar solo a CPU.

### 4.4 Capa MCP

- **Generada desde el registro**, no escrita a mano — patrón del `McpToolCatalog` de Stirling-PDF, que escanea sus endpoints y los publica como herramientas. Un motor nuevo aparece como herramienta sin tocar la capa MCP.
- **Devolver ruta + metadatos, nunca contenido**: `{ruta_salida, formato, bytes, duración_ms, motor_usado, camino_recorrido}`.
- **Pocas herramientas**: `convert`, `inspect`, `list_targets`, `batch`. Anotadas con `readOnlyHint` / `destructiveHint`.
- **Caché idempotente por hash de contenido + parámetros.**
- **Presupuesta la capa MCP como trabajo comparable a la CLI**, no como un envoltorio: en kordoc, `mcp.ts` (1 177 líneas) pesa casi lo mismo que `cli.ts` (1 205), y no por duplicar lógica sino por los esquemas descritos para el modelo, el saneado de rutas y la clasificación de errores.

### 4.5 Sidecar de IA

```
filex (CLI / MCP / watcher / API)      <- Python, proceso único y persistente
  |
  +-- registro + grafo de conversión   <- el núcleo propio
  |
  +-- motores externos                 <- subproceso sin shell: ffmpeg, magick, soffice...
  |
  +-- sidecar IA                       <- proceso Python aparte, modelos en VRAM
        docling + RapidOCR(torch) / faster-whisper
```

- **Registro LRU de modelos acotado por bytes de VRAM + TTL de inactividad.** Es lo que SnapOtter no tiene y FileX no puede no tener.
- **Presupuesto real: ~8,7 GB.** Picos de inferencia medidos: whisper `large-v3` 4 525 MiB, `distil-large-v3` 1 847, docling 910, RapidOCR-GPU +1 344, NVENC 4K 743. Perfil completo conviviendo: **7 702 MiB de pico, 4 586 libres**. **No caben dos `large-v3`.**

### 4.6 Seguridad — lo que hay que inventar

**Ninguno de los seis orquestadores recibe una ruta del sistema de ficheros**: todos reciben una subida HTTP. **FileX recibirá rutas arbitrarias de un LLM.** No hay de dónde copiar esto:

- **Lista blanca de raíces, denegar por defecto.** Resolución canónica (`realpath`) antes de decidir.
- **Error indistinguible** entre "prohibido" y "no existe", para no ser un oráculo de existencia.
- **Nunca devolver `stderr` crudo al modelo.** Observado en vivo: docling-mcp respondió `pip install openai-whisper` al agente. El error de un motor puede dirigir la siguiente acción del agente.
- **`policy.xml` propio de ImageMagick.** Ninguno de los seis lo distribuye, y dos lo *debilitan* por `sed`. Es el vector clásico.
- **Límites que no valgan cero.** El fallo dominante del sector no es "faltan límites" sino "los límites existen con default 0". Timeout por conversión, tope de memoria, tamaño de entrada y salida, número de páginas o fotogramas.

---

## 5. Reglas no negociables, con su evidencia

| Regla | Por qué |
|---|---|
| Invocar motores como **proceso separado, sin shell**, con argumentos en array | Sin contaminación GPL y sin inyección. morphos usa `bash -c` + `fmt.Sprintf` y tiene RCE |
| **Verificar la salida siempre** | El `.avif` que era PNG |
| **Sondear capacidades, no deducirlas** | `av1_nvenc` listado y no funcional |
| **`torch.cuda.is_available()` en cada arranque del sidecar** | `pip install surya-ocr` degradó torch a `+cpu` **sin un solo error** |
| **`session.get_providers()`, no `get_device()`** | onnxruntime devuelve `'GPU'` mientras corre en CPU |
| **`-map 0` explícito en ffmpeg** | Por defecto descarta la segunda pista de audio, en silencio. Los dos competidores caen en ello |
| **Filtrar por `language_probability`** | Whisper alucinó `Thanks for watching!` sobre un tono puro (0,35 frente a 0,91–0,97 en voz real) |
| **`distil-large-v3` ≤30 s, `large-v3` por encima** | distil empata (WER 0,00 %) en clips cortos, pero da 4,4–4,6 % de WER en 308 s por las costuras de las ventanas de 30 s |
| **HEVC es donde la GPU se paga** | 8,4× frente a 2,7× en H.264 |
| **Contabilizar el desvío de bitrate de NVENC** | Entrega un 8–11 % más de bits de los pedidos, frente al +1 % de x264 |
| **No usar la tubería GPU completa** | `-hwaccel cuda -hwaccel_output_format cuda` da −13 % a +3 %, y **−34 % con escalado** |

---

## 6. Trampas conocidas (ya se cayó en ellas; no repetir)

1. **Medir con ruido no es medir.** Una tanda NVENC que coincidió con una descarga dio mediana de 14 513 ms frente a los 1 973 reales: **error de 7,4×**. Usa `bench/lib/harness.sh`, que toma medianas de n≥9, registra el estado de la GPU antes y después, y etiqueta cada medición como `limpia` o `SUCIA`.
2. **Windows Defender infla el primer arranque** de un binario recién compilado (41 → 110 ms). Calienta antes de medir.
3. **Surya 0.22.1 no sirve**: ya no es un modelo en proceso, lanza un contenedor `vllm/vllm-openai:v0.20.1` que reserva el 85 % de la VRAM (10,4 GB de los 9,7 libres) y se cuelga sin excepción. **Marker hereda el bloqueo.**
4. **`onnxruntime-gpu` 1.29.0 exige CUDA 13** y cae a CPU en silencio mientras afirma lo contrario. Usa **1.22.0**.
5. **docling 2.120.3 tiene un bug**: rellena `EngineConfig.paddle.use_cuda` y `.torch.use_cuda` pero **olvida `.onnxruntime.use_cuda`**, que es el backend por defecto. Otra razón para usar `backend="torch"`.
6. **Los dos servidores MCP de referencia no caben en un venv** (`mcp~=1.8.0` frente a `mcp>=2.0.0`). Por eso hay tres entornos separados.
7. **`magick compare -metric SSIM` devuelve 0 para imágenes idénticas** en esta build: se comporta como disimilitud. Usa PSNR y RMSE.
8. **Clonar en Windows necesita `git -c core.longpaths=true`** para algunos repos (gotenberg falló por un fichero de prueba en sueco).

---

## 7. Plan de construcción

### Hito 1 — Registro, grafo y CLI

**Qué:** portar el registro de transmute, construir el grafo dirigido con coste por arista, y una CLI `filex entrada.x salida.y` con autodetección de camino. Motores: **ffmpeg e ImageMagick** (75 % de la cobertura de formatos).

**Aceptación:**
- Convierte al menos un fichero de cada categoría del corpus.
- **Resuelve al menos una conversión de 2 saltos** que ningún competidor puede hacer (`epub→png`, `docx→webp` o `tex→docx`).
- Un motor cuyo binario falta se auto-excluye y la CLI lo informa, en lugar de fallar.
- Cuando no hay camino, explica **por qué**.

### Hito 2 — NVENC con sondeo y degradación

**Aceptación:** `hevc_nvenc` se usa por defecto cuando el destino es HEVC; `av1_nvenc` se sondea, falla, y degrada a `libsvtav1` **sin intervención**. El desvío de bitrate queda registrado en los metadatos de salida.

### Hito 3 — Contrato de verificación

**Qué:** verificación post-conversión de firma, flujos y propiedades. **Antes que MCP**: sin esto, todo lo anterior puede mentir.

**Aceptación:** reproducir los tres fallos de los competidores contra FileX y que **los tres se detecten**: entregar un PNG con extensión `.avif`, perder una pista de audio, y degradar 16 bits a 8.

### Hito 4 — Capa MCP

**Aceptación:** el catálogo se genera desde el registro (añadir un motor no toca la capa MCP); las herramientas devuelven ruta y metadatos; un error de motor llega al modelo como mensaje accionable, **nunca como `stderr` crudo**; y una ruta fuera de la lista blanca se rechaza sin revelar si el fichero existe.

### Hito 5 — Gotenberg para ofimática

**Aceptación:** `docx/xlsx/pptx/odt → pdf` vía contenedor, con las 132 extensiones importadas y filtradas. Degrada con un mensaje claro si el contenedor no está levantado.

### Hito 6 — Sidecar de IA

**Qué:** proceso Python persistente con registro LRU por VRAM y TTL. faster-whisper (`distil` ≤30 s, `large-v3` por encima) y Docling con RapidOCR en `backend="torch"`.

**Aceptación:** los modelos se descargan por inactividad y el pico de VRAM no supera los ~8,7 GB con dos modelos residentes más NVENC. El OCR del PDF escaneado del corpus se recupera con distancia de edición 0.

### Hito 7 — Watcher y API HTTP local

A esas alturas son superficies delgadas sobre el mismo núcleo.

> **Los hitos 1 y 2 ya superan en cobertura y velocidad a todo lo analizado**, salvo en OCR y ofimática.

---

## 8. Cómo verificar

**Corpus:** `corpus/` — 20 ficheros en 5 categorías, con los casos patológicos que separan implementaciones:

| Fichero | Qué prueba |
|---|---|
| `video/patologico_2pistas.mkv` | 2 pistas de audio con contenido distinto (md5 del PCM diferente) |
| `imagen/patologico_16bit.tif` | 4000×3000 a 16 bits, 72 MB. Profundidad de color y memoria |
| `datos/patologico_bom.csv` | BOM UTF-8, comas en campo, comillas escapadas, salto embebido |
| `pdf/patologico_escaneado.pdf` | Sin capa de texto, inclinado 1,7°, con ruido. OCR puro |
| `pdf/escaneado_d1/d2/d3.pdf` | Degradación progresiva (150→100 ppp, 3-5°, JPEG q60→q25) |
| `pdf/tipico_texto.pdf` | Con capa de texto: contraste para decidir OCR frente a extracción |

**Patrón oro:** `bench/salidas-referencia/referencia.json` — 53 salidas caracterizadas, **46 reglas de regresión**, 39 órdenes exactas reproducibles, 17 pérdidas catalogadas. Úsalo como suite de regresión.

**Cuatro trampas de diseño de pruebas, ya identificadas:**

1. **El "alfa trivial"**: `tipico.png` declara canal alfa pero es enteramente opaco. La regla solo debe exigir conservación si `min(alfa) < 1,0`.
2. **Menor tamaño ≠ mejor conversión**: el GIF con paleta genérica pesa un 35 % *menos* que el bueno.
3. **Opus fuerza 48 kHz** y convierte 8,000 s en 8,0065 s: toda tolerancia por debajo de ±10 ms da falsos fallos.
4. **`txtwrite` emite 1–3 caracteres de basura** en PDF sin texto: el umbral de "conserva texto" debe ser ≥10, no >0.

**Arnés de medición:** `bench/lib/harness.sh` — `gpu_acquire` / `gpu_release` (lock exclusivo), `measure` (mediana con etiqueta limpia/SUCIA), `peak_vram`.

---

## 9. Documentos de referencia

| Ruta | Cuándo consultarlo |
|---|---|
| `ANALISIS-COMPLETO.md` | El análisis entero: 22 repos, 21 tablas comparativas |
| `informe-filex.html` | Versión navegable del informe |
| `analysis/transmute.md` | Antes de portar el registro |
| `analysis/00-sidecar-protocolo.md` | Antes de construir el sidecar (425 líneas de detalle) |
| `analysis/00-hueco-multisalto.md` | Antes de implementar el grafo |
| **`RESULTADOS-MCP.md`** | **Antes de la capa MCP (hito 4) y antes de tocar §4.6.** Resultados medidos de los 6 repos de `mcp-refs/`: el caso binario, el coste real de los catálogos, y **las 15 reglas de confinamiento que sustituyen a §4.6** |
| `analysis/00-mcp-componentes.md` | Al elegir qué pieza portar: 90 componentes → veredicto, con `fichero:línea` |
| `analysis/00-mcp-patrones.md` | Antes de la capa MCP — **pendiente de las correcciones de `RESULTADOS-MCP.md` §12** |
| `analysis/00-seguridad.md` | Antes de exponer nada (911 líneas) |
| `analysis/00-matriz-formatos.md` y `-ampliada.md` | Al poblar el grafo |
| `bench/referencia-nativa.md` | Al definir el contrato de verificación |
| `bench/gpu-fase1.md` y `gpu-fase2.md` | Al configurar GPU y sidecar |
| `bench/mcp-ergonomia.md` | 16 reglas MCP con su número medido |
| `bench/competidores.md` | Qué falla en la competencia y por qué |

---

## 10. Qué NO hacer

- **No forkear SnapOtter.** AGPL + CLA irrevocable + 100 commits/mes. Un fork en solitario es insostenible, y contribuir aguas arriba alimenta el activo comercial de una empresa.
- **No copiar una línea de ConvertX ni de VERT.** AGPL. Sus tablas de formatos sí, porque son datos.
- **No usar morphos como referencia de nada.** Abandonado desde 2024-11 y con inyección de comandos en `docx.go:126-130`.
- **No instalar motores nativos a mano en Windows.** No hay gestor de paquetes; lo que falte va en contenedor.
- **No tocar el `.wslconfig`.** Los 2 vCPU y 1,9 GiB son decisión deliberada del usuario, con sus motivos escritos en comentarios.
- **No competir con SnapOtter en su terreno.** Es UI-first y avanza a 100 commits/mes. FileX es **agent-first**: MCP, CLI y watcher. No comparten usuario.
