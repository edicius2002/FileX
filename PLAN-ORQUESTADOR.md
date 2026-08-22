# FileX — Plan del orquestador

**Documento de traspaso.** Escrito para que una sesión sin contexto previo pueda leerlo y ponerse a construir de inmediato. Fecha: 19 de agosto de 2026. **Revisión de las 03:30 del 21/08** — integrados `bench/verificador-fidelidad.md`, `bench/mcp-cabos-sueltos.md`, `bench/saturacion-herramientas.md` y `bench/ocr-ppp-nativos.md` en §4.2, §4.4, §4.5, §4.6, §5.1, §5.3, §6 y el hito 6 (`bench/consolidacion-21ago.md`).

> **Revisión de las 10:00 del 21/08** — integrados `bench/verificador-ghostscript.md`, `bench/aristas-nominales.md` y `bench/corpus-d4.md` en §4.1, §4.2, §4.5, §4.6, §5, §6, §7 (hitos 1 y 6), §8 y §9. Detalle en `bench/consolidacion-2-21ago.md`. **Tres cosas cambian el diseño y no solo la documentación:**
>
> 1. **El contrato gana un quinto punto** —«¿escribió el motor fuera de lo declarado?»— y el confinamiento pasa a ser **un directorio de trabajo desechable**, no solo una ruta validada (§4.2, §4.6 R18).
> 2. ~~**El techo de la regla de ppp pasa de relativo (×1,4) a ABSOLUTO (200)**~~ — **REFUTADO a las 14:00. Ver abajo.**
> 3. **La normalización del detector de RapidOCR se fija a mano** (seis números): vale **72,2 puntos de CER** y con ella **un solo motor cubre el corpus entero y funciona en CPU** (§4.5, hito 6). **Matizado a las 14:00: solo es segura sobre `PP-OCRv6 small`.**

> **Última revisión: 21 de agosto de 2026, 14:00** — integrados `bench/ppp-y-normalizacion.md`, `bench/invocacion-aristas.md` y `bench/contrato-quinto-punto.md` en §4.1, §4.2, §4.5, §4.6, §5, §6, §7 (hitos 1, 3 y 6) y §9. Detalle en `bench/consolidacion-3-21ago.md`. **Cuatro cosas cambian el diseño, y la primera CORRIGE a la revisión anterior:**
>
> 1. **NO HAY UNA REGLA GLOBAL DE ppp: hay una por motor, y por tanto la elección BAJA AL ADAPTADOR DE CADA MOTOR** (§4.5). Los ppp **no son la unidad** —24 celdas lo demuestran— y **las dos versiones anteriores de esta regla, la relativa y la absoluta, están refutadas**. Hoy está escrita en el sitio equivocado del diseño.
> 2. **R18 deja de ser higiene y pasa a ser REQUISITO DE COSTE** (§4.6): el punto 5 cuesta **+11,0 % del contrato** con directorio desechable y **×8,6 el contrato entero** sin él.
> 3. **El punto 5 es el primero del contrato que NO es verificable a posteriori** (§4.2): sin censo, **49 de las 53 salidas del patrón oro bajan a `ok_parcial`**. **La verificación tiene que vivir dentro de la conversión.**
> 4. **«Verificar en proceso siempre gana» tiene dos regímenes** (§4.2, §5): cierto para **cabeceras** (145×) y **falso para píxeles** — `magick` gana **×20,5** a 1,8 Mpx, con el cruce en ~0,1 Mpx.
>
> **Y una consecuencia de producto que ahora se puede escribir:** **FileX puede ofrecer un 10,2 % más de aristas que ConvertX con exactamente los mismos motores y sin pedirle nada al usuario** (§4.1).

> Si vienes de cero: lee las secciones 1, 2 y 3, y empieza por el hito 1 de la sección 7. El resto es referencia que consultarás sobre la marcha.

---

## 1. Qué es FileX y qué se decidió

**FileX** es un conversor universal de archivos, local-first, que se entrega como **servidor MCP + CLI + watcher de carpetas + API HTTP local**, sobre Windows con Docker/WSL2, aprovechando una **RTX 3060 de 12 GB**.

Cubre 12 categorías: ofimática↔PDF, markup, operaciones PDF, ebooks, imágenes normales y especiales, vídeo, audio, documento→texto para LLM, OCR, datos tabulares, y audio/vídeo→texto.

Se auditaron 22 repositorios a nivel de código y se ejecutaron en la máquina real. La conclusión que gobierna todo este plan:

> **Código de transmute, contenedor de gotenberg, patrones de SnapOtter, tabla de motores de ConvertX. Ningún repositorio sirve entero — por eso el núcleo se escribe de cero.**

El núcleo propio es exactamente lo que **nadie del ecosistema tiene**: un grafo de conversión con búsqueda de camino, una capa MCP pensada para agentes, uso real de la GPU, y verificación obligatoria de la salida.

### Los diferenciadores

> ⚠️ **Esta lista fue reevaluada dos veces.** Tras la fase de ejecución, dos huecos se debilitaron, uno hubo que reformularlo, y **apareció uno más fuerte que no estaba aquí: la verificación obligatoria de la salida**. Tras la segunda tanda de mediciones (21/08/2026) **el multi-salto quedó refutado como titular** y el OCR **se reabrió**. La versión vigente, con la separación entre lo medido y lo pendiente, está en **`HUECOS.md`**. La tabla siguiente se conserva porque el **orden de construcción de la §7 no cambia** — el hito 3 ya era el contrato de verificación, y ahora hay más razones para que sea así.

| # | Hueco | Evidencia medida | Coste |
|---|---|---|---|
| 1 | ~~Grafo multi-salto~~ → **selección correcta con coste explícito** | 0 de 7 orquestadores hacen búsqueda de camino. ~~**2,93×** de cobertura~~ **REFUTADO al ejecutarlo:** con los motores instalados el multiplicador es **1,93×**, la ganancia honesta **+32,7 %** (610 pares plausibles) y solo el **31,9 %** de los caminos multi-salto da una salida aceptable frente al 54,5 % de un salto. `bench/fidelidad-caminos.md` | Bajo |
| 2 | NVENC en vídeo | Ningún orquestador lo usa. **8,4×** en HEVC, 2,7–3,0× en H.264 | Muy bajo |
| 3 | MCP para agentes | El techo del sector en conversión invocable son **84 ⭐** (`video-audio-mcp`), que devuelve prosa sin metadatos y con `isError:false` siempre. **~2 400×** de diferencia en tokens entre patrones | Medio |
| 4 | OCR en GPU | Todos lo hacen en CPU. Resuelto: Docling + RapidOCR `backend="torch"`, **coste de infraestructura cero** | Bajo |

---

## 2. Estado del entorno (verificado, no asumir)

**Hardware:** RTX 3060 12 288 MiB, **compute capability 8.6**, driver 572.61 · 12 núcleos · Windows 10.

**Instalado nativamente:** `ffmpeg` N-121159 (con `--enable-gpl --enable-libx264 --enable-libx265 --enable-cuda-llvm`), `magick` (ImageMagick 7.1.2 Q16-HDRI), `gswin64c` (Ghostscript 10.07), Node 22.23.2, Go 1.22.5, CUDA toolkit 11.2, Docker 29.4.3, WSL2 (Ubuntu), Python 3.11.9.

**NO instalado:** vips, LibreOffice, Pandoc, Tesseract, qpdf, Calibre, Inkscape, DuckDB, uv, bun, cargo. **Y no hay gestor de paquetes** (ni winget, ni choco, ni scoop) — por eso lo que falte va en contenedor, no instalado a mano.

**Precisión sobre Tesseract — MEDIDA (21/08/2026).** La línea de arriba es **imprecisa en la letra y correcta en el efecto**, y conviene saber las tres cosas por separado:

1. **Existe un `C:\Program Files\Tesseract-OCR\tesseract.exe`** (86 152 B, instalación ajena a este proyecto) **pero no está en el PATH** (`where.exe tesseract` no lo encuentra) y su `tessdata` solo tiene `eng` y `osd`. **No es invocable: a efectos de FileX, no está.**
2. **Ghostscript 10.07 lleva Tesseract y Leptonica compilados dentro de `gsdll64.dll`** — 122 apariciones de `tesseract` y 9 de `leptonica` en el binario, con rutas de compilación `ghostpdl-10.07.0\tesseract\src\…`. Por eso `gswin64c` ofrece `-sDEVICE=ocr`, `hocr` y `pdfocr8/24/32` **sin invocar ningún binario externo**.
3. **Pero no lleva los datos de idioma:** cero `.traineddata` bajo `C:\Program Files\gs`, y el dispositivo **falla sin `TESSDATA_PREFIX`** con `Tesseract couldn't load any languages!`. Que funcione hoy en esta máquina es un accidente: dos programas ajenos (Tesseract-OCR y PDFgear) dejaron `.traineddata` en el disco.

> **FileX obtiene el motor de OCR gratis dentro de un binario que ya usa, pero debe distribuir `eng.traineddata`** (Apache-2.0; ~4 MB en `tessdata_fast`) **y `spa` si quiere castellano, y fijar `TESSDATA_PREFIX` desde el propio orquestador.** No es coste cero, pero es mucho menos que exigir Tesseract instalado, y encaja con la regla de no instalar motores a mano en Windows.
>
> **Dos avisos:** el idioma se elige con `-sOCRLanguage=` (con `-d` falla), y **OCRmyPDF no puede aprovechar el embebido** — necesita el binario `tesseract` de verdad. Evidencia: `bench/fidelidad-caminos.md` §0.1.

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

> **Salvedad a respetar, ahora MEDIDA:** los 447 398 pares alcanzables son un límite superior, no una promesa de fidelidad. Un camino de 3 saltos que rasteriza y destruye el texto debe puntuar peor que "no se puede".
>
> **Las cifras que hay que llevar a la implementación** (`bench/fidelidad-caminos.md`, 69 caminos ejecutados): con los motores instalados aquí el multiplicador es **1,93×**, no 2,93×; de los 128 426 pares nuevos solo **610 (0,48 %)** son plausibles; **820 de los 1 599 pares «pedidos» tienen PDF como único intermedio**; y **solo el 31,9 % de los caminos multi-salto da una salida aceptable**, frente al 54,5 % de un salto. **El valor del grafo se cobra en el primer salto —elegir bien el motor—, no en la cadena.**
>
> **Regla derivada:** el multi-salto se ofrece, pero **con el coste explícito y el motivo del rechazo**; y las **aristas de reparación** (OCR sobre lo ya rasterizado) valen más que la mayoría de los caminos nuevos. *(El «99,0 % del texto recuperado» de aquel informe **no se reproduce**: reejecutado da **94,7 %** con espacios normalizados y **97,1 %** ignorándolos. **No se declara refutado, sino NO REPRODUCIDO**, porque `fidelidad-caminos.md` no publica sus ppp, su idioma de OCR ni su fórmula de similitud — `bench/verificador-ghostscript.md` §5.7. El orden de magnitud correcto es **94-97 %**, y la mayor parte de la pérdida son **espacios, no letras**.)*

> ### La tasa de aristas nominales, MEDIDA — y lo que le hace al grafo (`bench/aristas-nominales.md`, 21/08/2026)
>
> **El 50,5 % de las aristas declaradas que se han podido verificar NO EXISTE**, IC 95 % [48,2–53,0] sobre **62 487 aristas (45,1 % de la población)**. Sobre la población entera: **cota inferior 22,8 %, central 48,6 %, superior 77,5 %**. **Y el 50,5 % es explícitamente una cota inferior**, por tres sesgos declarados.
>
> **Pero la tasa NO es uniforme —factor 18— y esto es lo que hay que llevar a la implementación:**
>
> | Estrato | Nominal | Lectura |
> |---|---:|---|
> | `ffmpeg` cruzando familias | **76,9 %** | declarar `473 × 202` es declarar que un `.aptx` se convierte en `.gif` |
> | `ffmpeg` misma familia | 28,8 % | |
> | `imagemagick` misma familia | **4,2 %** | imagen contra imagen: **la tabla es casi verdad** |
> | **aristas que tocan PDF** (el intermedio del multi-salto) | **3,0 %** [1,0–8,5] | **el estrato que el grafo usa de verdad es el más sólido** |
>
> **Los dos hechos van juntos o la cifra engaña.** `fidelidad-caminos.md` §1.3 midió que 820 de los 1 599 pares «pedidos» tienen PDF como único intermedio; **si una arista hacia PDF fuera nominal se caería media tesis, y no lo son**. El «pásalo por PDF» **es el único trozo del grafo cuyas aristas se sostienen al ejecutarlas**.
>
> **Tres consecuencias directas para el grafo:**
>
> 1. **Sondear el mapa de capacidades al arrancar, no leer tablas.** El censo de **1 104 semiaristas** cuesta **9 min 35 s en frío** y **decide el 45 % de la población de aristas**, porque las aristas son cuadráticas y las semiaristas lineales. **Con ese censo desaparece el término «+50 por arista nominal» que `fidelidad-caminos.md` §5.2 proponía**: para las semiaristas ya no hay que adivinar. Queda el **∞ para lo refutado** y una penalización solo para el residuo de composición.
> 2. **El nodo no puede ser el formato y la arista no puede ser el par.** La arista mínima viable es **`(origen, destino, motor, parametrización, build)`** — ver trampa 14 de §6.
> 3. **`imagen → pdf` necesita densidad explícita, siempre.** Once de las doce degradaciones del estrato PDF son la misma regla del patrón oro: `P7 · 1 px → 1 pt: página absurda (1920 × 1080 pt = 677 × 381 mm)`. **No es un caso raro: es el comportamiento por defecto de toda esa familia de aristas.**
>
> **Y los 20 formatos crudos sin cabecera** (`rgb`, `rgba`, `yuv`, `cmyk`, `gray`, `bayer`…) son el **16,2 % de lo que ImageMagick declara leer y no lee** — falla con `must specify image size` porque la geometría **no está en el fichero** y ConvertX invoca sin `-size`. **O FileX guarda la geometría fuera del fichero y la pasa, o esos 20 formatos se borran del catálogo declarado.** Declararlos y no poder cumplirlos es exactamente el **fallo silencioso** de `saturacion-herramientas.md` §8, y por eso la cobertura declarada es un requisito de seguridad (§4.4).

> ### El 50,5 % tiene cota: **el 18,8 % es invocación, no capacidad** — MEDIDO (`bench/invocacion-aristas.md`, 21/08 14:00)
>
> Se reintentaron **las 34 + 37 semiaristas muertas y las 118 aristas nominales** de la muestra —**censo de los fallos**, no muestra nueva— con una política de invocación declarada **antes** de medir y **con el mismo juez**, para no medir el juez en vez de la invocación.
>
> **Con los mismos motores, el mismo build y el mismo corpus, la tasa nominal baja de 50,5 % a 41,0 %:** 5 930 aristas de 31 533 sí existen y lo que fallaba era la orden. IC 95 % [16,8 – 21,3].
>
> | Categoría | Aristas | % del 50,5 % | Qué significa para el producto |
> |---|---:|---:|---|
> | **Con bandera** | **3 226** | **10,2 %** | **ganancia automática: no hay que pedirle nada al usuario** |
> | Con parámetro del usuario | 2 704 | 8,6 % | exige un canal de metadatos |
> | Irrecuperable | 25 603 | **81,2 %** | no hay pista compatible, o el codificador no está compilado |
>
> **Lo que hay que llevar a la implementación, en orden de rendimiento:**
>
> 1. **`-frames:v 1 -update 1` cuando el destino es una imagen única y la entrada tiene varios fotogramas.** Recupera **13 de las 27** aristas del residuo. El `Error opening output files: Invalid argument` tenía **dos causas** que la instrumentación anterior no separaba.
> 2. **`imagen → pdf` necesita densidad AJUSTADA A LA PÁGINA, no una densidad fija.** `-density 150` quita la marca P7 y **sigue produciendo un A3 y medio** (325,1 × 182,9 mm). **Calculando la densidad para que la imagen quepa en la página objetivo: 210,0 × 118,1 mm y 7 de 7 ÍNTEGRO. Las 6 de 6 degradaciones P7 desaparecen.**
> 3. **Los 20 crudos exigen CUATRO datos, no uno:** geometría, **profundidad**, canales y entrelazado. **17 de 20 reviven**, pero *(trampa 23 de `CLAUDE.md`)* releer con `-depth 8` un crudo Q16-HDRI **entrega la geometría correcta y píxeles basura, y pasa los cuatro puntos del contrato**. **Las tres salidas posibles siguen siendo: pedirlos al usuario, guardarlos en un sidecar cuando el propio FileX escribió el fichero, o borrarlos del catálogo.**
> 4. **El techo de 256 px de ICO:** `-resize 256x256> -define icon:auto-resize=…` recupera 7 aristas. **ConvertX ya tiene el caso especial en `ffmpeg.ts:702` y no en `imagemagick.ts`.**
>
> **Y tres reglas de sondeo que salen de errores del propio informe, cada una con su corrección:**
>
> - **Todo sondeo de capacidades tiene que emparejar ESCRITOR y LECTOR del mismo motor.** `ffmpeg -i x m.rgb` usa el muxer `rawvideo`, que **ignora la extensión y vuelca el `pix_fmt` de la entrada**: el fichero llamado `m.rgb` no contiene RGB, y el mapa que salga estará medido contra ficheros que no son lo que dicen ser.
> - **«Fuerza lo que sondees» necesita una excepción.** Con el muxer `image2`, forzar el códec «por defecto» declarado (`mjpeg`) **escribe un JPEG dentro de un `.ppm`** — peor que no forzar nada. **La formulación que sobrevive: fuerza el muxer, el mapeo de pistas y las restricciones del codificador; NO fuerces el códec cuando el muxer lo deduce bien de la extensión.**
> - **Cuando el vocabulario de firmas no cubre el destino, hace falta un tercero.** Un control con `magick identify` y `ffprobe` **eliminó 4 de 32 «recuperaciones»** (ffmpeg escribiendo **Sun Raster** dentro de `.im24`; un `.mp4` «H.265» **sin una sola pista de vídeo**). **Mientras el vocabulario no crezca (C14), una arista fuera de él no se puede declarar viva, solo «sin refutar».**
>
> **Lo que impide inflar la cifra, y pesa tanto como la cifra:** **69 de las 118 aristas nominales (58,5 %) son «el muxer no admite ninguna pista que la entrada tenga»** —declaraciones sin sentido, no órdenes mal escritas— y **19 de las 33 semiaristas de salida muertas de ffmpeg son codificadores no compilados**, que es **build**. Esto último **confirma la sexta dimensión de la arista**: `build` decide 19 casos y `parametrización` otros 8. **Un catálogo que no lleve las dos miente en cuanto cambias de máquina.**
>
> **Y la superficie documental sale reforzada, por un camino independiente:** censo completo de Ghostscript (**9 de 9 reales**) y de Gotenberg/Chromium (**25 de 25 reales**), con un total de **3,1 % nominal** [0,9 – 10,7] sobre 136 aristas. **Coincide con el 3,0 % del estrato PDF medido con otros motores y otro protocolo. Si FileX tiene que elegir dónde prometer, es aquí.**

### 4.2 Contrato de verificación post-conversión — **no negociable**

Después de **cada** conversión, comprobar:

1. **Firma real del fichero** (bytes mágicos), no la extensión. Y el fichero de 0 bytes, que es el fallo más grave y el más barato de detectar.
2. **Flujos esperados frente a obtenidos**: número de pistas de vídeo, audio y subtítulos, **leyendo las cabeceras del contenedor en proceso**. `ffprobe` **solo como excepción documentada** — ver el aviso de abajo.
3. **Propiedades declaradas frente a medidas**: coherencia interna de la salida — dimensiones plausibles, profundidad de bits, canal alfa, ppp, bitrate, duración > 0, páginas ≥ 1, UTF-8 válido.
4. **Propiedades PEDIDAS frente a obtenidas** — **lo que no se pidió transformar debe conservarse**: geometría, relación de aspecto, ppp, profundidad, alfa, duración, frecuencia, canales, bitrate, páginas, filas.
5. **Nada fuera de lo declarado** — **MEDIDO el 21/08 (`bench/aristas-nominales.md` §5.2), y es un punto nuevo.** Listar el directorio de trabajo **antes y después** de invocar al motor: si aparecen ficheros que no son la salida declarada, o **la salida real son varios ficheros**, el contrato lo dice.

Los tres fallos más graves encontrados en los competidores —el `.avif` que era PNG, la pista de audio perdida, y las degradaciones de bits/ppp/bitrate— **los habría atrapado los tres**. **El cuarto punto atrapa uno que los tres primeros no ven, y el quinto uno que no ve ninguno de los cuatro.**

#### El punto 1 no aplica al 23,6 % de los formatos — y ahí tampoco aplican el 2 ni el 3 — MEDIDO el 22/08 (`bench/firmas-contrato.md`)

**El vocabulario de firmas pasa de 24 nombres y 26 extensiones a 147 y 338**, más una **tercera tabla de 112 extensiones declaradas SIN marcador**. Con eso el punto 1 sube del **12,4 % al 54,2 %** de los destinos de la muestra de 498 aristas de E1, con **0 falsos positivos sobre las 53 del patrón oro**.

> **Pero la conclusión que importa es la contraria a la que se buscaba: NO SE PUEDEN VERIFICAR 500 FIRMAS PORQUE NO EXISTEN 500 FIRMAS.** De **381 formatos con veredicto, 90 (23,6 %) no tienen marcador**: son datos crudos, contenedores sin cabecera o pseudoformatos. **Y donde no hay cabecera tampoco hay puntos 2 y 3, porque los tres se alimentan de lo mismo.** Para esa tercera categoría el contrato se queda con **el punto 4, el punto 5 y G6**.

**Por eso la cobertura tiene que ser honesta, y son cuatro estados, no un booleano:**

| Estado | Significa |
|---|---|
| `evaluado` | Hay marcador, se leyó y coincide |
| `familia` | La firma cae en la familia correcta pero no identifica el formato exacto |
| `no_aplica` | **El formato no tiene marcador.** No es un aprobado: es que la pregunta no se puede hacer |
| `sin_vocabulario` | El formato podría tener marcador, pero FileX no lo conoce |

> **Antes de esto, `1_firma` valía `True` en el 100 % de los ficheros mientras evaluaba el 12 %.** Un contrato que aprueba lo que no ha mirado es peor que uno que no mira.

#### La sexta comprobación, y no es un punto del contrato: **G6** — MEDIDO (ídem §7.1)

> **G6 — la salida tiene la MISMA firma que la entrada, y no era eso lo que se pedía.** Se dispara cuando (a) la extensión de destino no está en la tabla, (b) la firma de la salida es un formato reconocido y (c) coincide con la de la entrada. **Cuesta 0: las dos firmas ya están calculadas.** Severidad **`aviso`**, no `fallo`.

Es **quien atrapa el fallo emblemático del proyecto** —`magick x.png y.group4` devuelve `rc=0` y entrega un PNG—, **22 de 22, donde ni el vocabulario viejo ni el nuevo atrapan ninguno**. Sobre las 53 del patrón oro no se dispara nunca; sobre 345 salidas legítimas, solo en los 12 casos reales. **Está calibrada sobre 22 casos de un solo motor: por eso es `aviso` y no `fallo`.** Subirla exige medirla con más motores y comprobar que no marca conversiones legítimas entre formatos equivalentes (`png` → `apng`, `mkv` → `mka`).

#### Por qué hay un cuarto punto — MEDIDO

`image-worker-mcp` entregó un **WebP válido**, con propiedades coherentes consigo mismas, que era la imagen **redimensionada sin que nadie lo pidiera**: 1920×1080 → 800×450 con barras negras, y un PNG de 64×64 **ampliado ×9,75**. **Ese caso pasa los tres puntos originales** y solo cae con el cuarto.

> **«No te pedí que redimensionaras» es una condición distinta de «el fichero es coherente consigo mismo».**
>
> **Y la regla que va con él: ninguna transformación no solicitada se aplica por defecto.**

El punto 4 es **187 de las 333 líneas** de lógica del contrato en el prototipo: más que los puntos 2 y 3 juntos. **El contrato no juzga ficheros: juzga ficheros contra pedidos** — el mismo PNG de 8 bits es una conversión impecable si se pidió `-depth 8` y una degradación silenciosa si no.

#### Por qué hay un quinto punto — MEDIDO (`bench/aristas-nominales.md` §5.2)

**Hay motores que escriben fuera del destino, y no es una rareza:**

| Orden (la invocación exacta de ConvertX) | Escribe en el destino | Escribe **también** |
|---|---|---|
| `ffmpeg -i trivial.mp4 DEST/t.mpd` | `t.mpd` (**1 234 B**) | **`init-stream0.m4s` (814 B) y `chunk-stream0-00001.m4s` (528 447 B) en el `cwd`** |
| `magick trivial.png -auto-orient DEST/u.html` | `u.html` (506 B) **y `u.png` (329 B)** | **`u_map.shtml` (98 B) en el `cwd`** |

- **La arista `vídeo → mpd` entrega un manifiesto DASH válido de 1,2 KB que no lleva el contenido**: los 528 KB están en dos segmentos que se quedaron en otro directorio. **Pasa los cuatro puntos.** Categoría correcta: **DESTRUIDO**.
- **Una conversión puede producir varios ficheros.** Devolver solo el declarado entrega un documento roto. Una sonda que juzga **un** fichero no puede verlo.
- **Es también un escape de confinamiento:** un motor que escribe en el `cwd` escribe donde esté el orquestador. **Va con R18 de §4.6: directorio de trabajo propio y desechable por conversión.**

~~**Coste de implementarlo: listar un directorio antes y después. Trivial, y hoy no lo tiene nadie.**~~ **IMPLEMENTADO Y MEDIDO el 21/08 a las 14:00, y «trivial» tiene condición:**

> ### El punto 5 cuesta **+11,0 % del contrato — pero solo con R18** · MEDIDO (`bench/contrato-quinto-punto.md` §2)
>
> | Configuración | Mediana (n=15) | Frente al contrato de 4 puntos |
> |---|---:|---:|
> | **Contrato SIN punto 5** | **0,4254 ms** | ×1 |
> | **+ punto 5 con R18** (directorio desechable: solo se censa DESPUÉS) | **0,4722 ms** | **×1,11** |
> | + punto 5 **sin R18**, directorio de 1 000 ficheros | **3,6614 ms** | **×8,6** |
>
> **El contrato pasa del 0,032 % al 0,036 % de convertir. Y ese número depende de R18: sin directorio de trabajo desechable, el punto 5 sale del camino caliente.** → **R18 deja de ser higiene y pasa a ser requisito de coste (§4.6).**
>
> **La lógica del punto 5 es gratis (0,031–0,037 ms); lo caro es el censo, y R18 lo divide por dos y lo acota a un directorio que solo contiene lo que acaba de escribirse.** Cuarta medida seguida de la misma constante del proyecto: *fabricar el acceso al dato es el coste.*
>
> **Las dos decisiones que salieron de los datos y no de la especificación, y las dos hay que respetarlas al implementar:**
>
> 1. **El disparador es la UBICACIÓN, no el tamaño.** Parecía obvio detectar el DASH por el reparto de bytes (el `.mpd` lleva el 0,2 %), pero **un manifiesto HLS legítimo lleva el 0,0 %**: si el reparto fuera el disparador, **toda salida en streaming sería un fallo**. El reparto solo decide la **severidad** de una fuga ya detectada por ubicación.
> 2. **Declarar `multifichero: true` NO autoriza a escribir en el `cwd`.** La orden DASH con ese campo **sigue dando fallo**. Es la diferencia entre «esta salida son varios ficheros» y «este motor escribe donde le da la gana».
>
> **Discriminación medida:** 0 avisos en las tres salidas legítimamente multifichero (HLS, `f%03d.png` con 20 ficheros, `gs -sOutputFile=p%d.png`) y **fallo mantenido en el DASH**. **Falsos positivos sobre el patrón oro: CERO** (39 órdenes reejecutadas en directorio desechable).
>
> > ### Y el coste honesto es un cambio de naturaleza: **sin censo, 49 de las 53 salidas bajan de `ok` a `ok_parcial`**
> >
> > No es un falso positivo: es el verificador diciendo *«no puedo saber si el motor escribió en otro sitio, porque nadie miró cuando tocaba»*. **El punto 5 es el primero del contrato que NO es verificable a posteriori, y eso es un argumento de arquitectura: la verificación tiene que estar DENTRO de la conversión, no ser un paso que se pueda hacer luego.**
>
> **Y una comprobación cruzada desde otro carril:** **0 fugas en 118 aristas** ejecutadas con `cwd` desechable y listado antes/después (`bench/invocacion-aristas.md` §7.4). **No contradice el hallazgo: confirma que fuga y fallo son poblaciones disjuntas** — los dos casos de fuga tienen destinos (`mpd`, `html`) que no aparecen entre las aristas nominales, porque **no fallaban: entregaban un fichero incompleto**. Es justo por eso que el quinto punto hace falta.
>
> **Limitación declarada:** `censar_dir` **no es recursivo**. Un motor que cree un directorio y escriba dentro se contabiliza como **una** entrada nueva. Ningún caso del corpus lo hace. **PENDIENTE.**

> ### Y el caso que **ningún** punto del contrato atrapa — MEDIDO (`bench/aristas-nominales.md` §8.2)
>
> **`resvg 0.46.0` rasteriza un SVG con dos bloques de texto y devuelve `rc=0`, un PNG con firma PNG válida, de la geometría exacta pedida — y sin una sola letra:** **0,00 % de tinta en la banda de texto**, frente al 14,02 % de Inkscape y el 15,07 % de `magick`. Lo único que lo delata está en `stderr` (`No match for '"DejaVu Sans", sans-serif' font-family`) y el contenedor **tiene 153 fuentes instaladas**.
>
> **Firma correcta · flujos correctos · propiedades declaradas coherentes · pedido = obtenido · nada escrito fuera. Los cinco puntos lo aprueban.**
>
> **Esto acota el contrato con precisión y hay que construir con esa frontera delante:** el contrato juzga **la declaración** de la salida; **el contenido que desaparece sin dejar rastro en ninguna propiedad declarada solo se ve comparando la salida con la entrada — es decir, en el grupo C**. La regla que lo atraparía —*si el origen SVG contiene `<text>`, la salida rasterizada debe tener tinta donde estaban*— cuesta del orden de los 26 ms del grupo C y está ~~**PENDIENTE**~~ **IMPLEMENTADA. Y la estimación de 26 ms se quedaba corta ×94.**
>
> **No invalida el diferenciador nº 1: lo delimita.** Los siete fallos del sector que el contrato atrapa son fallos **por declarar de más**; este es un fallo **por entregar de menos en silencio**, y es material para `HUECOS.md` §1.

> ### La regla I9, implementada — y su coste refuta una constante del proyecto · MEDIDO (`bench/contrato-quinto-punto.md` §4)
>
> **Discrimina 6 de 6, y el margen es binario:** `resvg` **0,00 %** de tinta frente a **20,01 %** de Inkscape y **23,61 %** de `magick`. Los tres controles —SVG sin `<text>`, texto de 2 caracteres, `text-anchor="middle"`— no dan ni un falso positivo, y sobre las 53 salidas del patrón oro **no se evalúa ni una vez y no añade ni un aviso**.
>
> | Rasterizado | I9 completa | origen (`xml.etree`) | tinta **en proceso** | tinta **con `magick`** |
> |---|---:|---:|---:|---:|
> | 400×200 (0,08 Mpx) | **32–59 ms** | 0,13–0,21 ms | 38–56 ms | 37–42 ms |
> | 800×400 (0,32 Mpx) | **537 ms** | 0,14 ms | 452 ms | **66 ms** |
> | **1920×960 (1,84 Mpx)** | **2 454 ms** | 0,21 ms | **2 834 ms** | **138 ms** |
>
> 1. **La estimación era «del orden de los 26 ms». El coste real se queda corto ×94 en un raster de 1,8 Mpx.** *Medir en vez de estimar cambia la conclusión de dónde vive la regla.*
> 2. **El 99,6 % del coste es fabricar el acceso al dato** y el 0,4 % es la regla. Cuarta medida seguida: 53 % → 61 % → 70 % → **99,6 %**.
> 3. > **REFUTADO PARCIALMENTE: «verificar leyendo en proceso, no con subprocesos» NO se transfiere a leer PÍXELES de un raster grande.** A 0,08 Mpx los dos caminos empatan; a 0,32 Mpx `magick` gana **×6,8**; a 1,84 Mpx gana **×20,5**. **El punto de cruce está en ~0,1 Mpx.**
>    >
>    > Es el mismo fenómeno que `verificador-fidelidad.md` §7.2 anotó para el decodificador VP8L, ahora medido en otra regla y con otro formato. **La regla de diseño correcta no es «siempre en proceso»: es «en proceso para cabeceras y rasters pequeños; con la sonda externa a partir de ~0,1–0,3 Mpx».** *(La implementación entregada usa el camino en proceso **porque no añade dependencias**, y esa elección tiene un precio medido.)*
>
> **Y la frontera del contrato, que se planteó como posible excusa, queda CONFIRMADA COMO ARQUITECTURA:**
>
> > **El contrato atrapa la pérdida de contenido cuando el contenido está DECLARADO EN METADATOS** —filas, cabecera de un CSV, número de pistas, número de páginas— **porque la sonda ya los lee para los puntos 2, 3 y 4. Necesita fidelidad cuando el contenido solo existe como PÍXELES o como MUESTRAS**, porque entonces hay que decodificar.
>
> Dos medidas lo sostienen: **el precio es de tres órdenes de magnitud** (0,43 ms el contrato frente a 32–2 454 ms de I9: meterla en el camino caliente multiplicaría el contrato por 75–5 700), y **la prueba en el otro sentido** — el miembro de la familia cuyo contenido perdido *sí* está declarado, un CSV→JSON que pierde una columna, **lo atrapa el CONTRATO (regla D4), no la fidelidad**. La frontera cae exactamente donde el criterio dice.
>
> **Lo que sí hay que corregir de la formulación: el contrato no puede juzgar INTENCIÓN que el pedido no exprese.** Aparece dos veces y por dos caminos: **I9 solo puede exigir texto porque el ORIGEN lo declara (`<text>`)**, y **P5 solo puede exigir texto tras un OCR porque ahora el PEDIDO lo declara (`ocr: true`)**. **El punto 4 del contrato vale lo que valga el pedido**, y por tanto **el orquestador tiene que propagar la intención, no solo los parámetros del motor**: un `pedido` que solo lleva `{destino: "pdf"}` para una reparación por OCR es un pedido incompleto.
>
> **Y `resvg` no era un caso aislado: la familia tiene AL MENOS CINCO MIEMBROS** —SVG sin fuentes, vídeo con envase correcto y todo negro, PDF de texto rasterizado, CSV→JSON que pierde una columna, y audio con un canal silenciado—. **El contrato atrapa uno; I9 atrapa otro; y uno sigue SIN CUBRIR:** el canal silenciado hacia un destino **con pérdida** (el mismo fallo hacia FLAC sí lo atrapa A4). **La cobertura depende del destino, no del fallo. PENDIENTE**, con una propuesta sin medir: energía por canal con `ffmpeg -af astats`.
>
> **I9 no cubre PNG entrelazado ni destinos que no sean PNG:** un `svg → pdf` con el mismo fallo de fuentes **no se detecta hoy**. Devolver `evaluable: false` con el motivo es la respuesta correcta; inventar un número, no.

#### Cómo implementarlo — la decisión que decide si el diferenciador es barato o caro

**MEDIDO en `bench/coste-verificacion.md`:**

| Implementación | Coste por fichero | Ratio verificar ÷ convertir |
|---|---:|---|
| **Cabeceras leídas en proceso** | **0,372 ms** | **0,14 %-0,36 %** por categoría; **0,032 %** sobre las 39 órdenes del patrón oro |
| `ffprobe` / `magick identify` | 54,06 ms | 8,9 %-153 %; **9,6 %** sobre las 39 |

**145× más caro.** Y **en 15 de las 39 órdenes (38 %) verificar con subprocesos cuesta más que convertir** — hasta el **397 %** en `flac→wav`. **El cuello es la creación de proceso, no el disco:** sondear 204,9 MB de salidas lee **334,6 KB (0,163 %)** y un PNG de 61 MB cuesta **133 bytes**. El paralelismo no rescata la estrategia cara (techo ×1,79 con 24 hilos sobre 12 núcleos).

> **Verificar en serie, en proceso, dentro del hilo que hizo la conversión.** Sin dependencias externas: no hace falta que ffmpeg esté instalado para comprobar que un MP4 tiene dos pistas.

**Coste de escribirlo, para presupuestarlo bien:** el prototipo son **1.503 líneas** (333 del contrato, 671 de leer cabeceras), **0 falsos positivos sobre 53 salidas** y atrapa **los 5 fallos documentados**. Pero **la primera versión, escrita literalmente desde esta especificación, dio 9-10 falsos positivos (17-19 %)**; hicieron falta **~85 líneas de excepciones justificadas por datos** que no se deducen de ningún contrato. Ver la trampa 9 de §6.

**Corolario contraintuitivo:** *un recurso alternativo sin verificación es peor que no tenerlo*, porque convierte un fallo honesto en uno silencioso. Es literalmente lo que le pasa a ImageMagick dentro de ConvertX: emite un *warning* con código de salida 0 y devuelve el formato origen.

**Y su reverso:** el verificador debe distinguir «comprobado y correcto» de «no he podido comprobarlo». Un veredicto de cobertura parcial, no un `ok` cómodo — si no, se repite el fallo de `markitdown-mcp` (cadena vacía con `isError: false`).

#### El contrato son tres grupos, no dos — MEDIDO (`bench/verificador-fidelidad.md`, 21/08/2026)

El prototipo llegó hasta la fidelidad y **la frontera de coste salió nítida**. Hay que respetarla en la implementación:

| Grupo | Cuándo corre | Qué incluye | Coste por fichero | Frente a convertir |
|---|---|---|---:|---:|
| **A — Contrato** | **siempre**, en serie, en el hilo que hizo la conversión | los puntos 1-4 de arriba + V9 (paleta del GIF, que cuesta 0,18 ms) | **0,37 ms** | **0,032 %** |
| **B — Caracterización de la entrada** | **una vez por entrada**, cacheada por hash de contenido | `min(alfa)` en proceso | 0,05–66,0 ms | 0,089 % |
| **C — Fidelidad** | **bajo demanda** o en la suite de regresión. **Nunca en un lote** | I3, I6, I7, I8, V6, V8, A4, A5, P2, P6 | 207 ms | **38,5 %** |

- **`min(alfa)` ya no necesita `magick`.** En proceso cuesta **66,0 ms en el peor caso** —un PNG 1920×1080 RGBA16 enteramente opaco, que obliga a recorrerlo entero— frente a los **376,3 ms** de `magick` remedidos hoy; **0,23 ms** en el caso bueno; y **en 7 de 12 casos no lee un solo píxel** porque lo decide la cabecera. *(Los 734,6 ms que citaba `bench/coste-verificacion.md` §1.4 no son reproducibles hoy tal cual: la misma orden da 376 ms. Se conservan las dos cifras.)*
- **Va en la caracterización de la entrada, jamás por salida:** por entrada cuesta 66,3 ms sobre el corpus; pagado por salida, 320,9 ms. **÷4,8.**
- **Cuando el grupo B no está, el punto 4 devuelve `ok_parcial` con `4_alfa: false`. No aprueba por defecto.** Sin `min(alfa)`, **11 de las 53 salidas del patrón oro** pasan a `ok_parcial`; con él, cobertura completa y **0 falsos positivos en seis configuraciones**.
- **La fidelidad cuesta ×1.106 el contrato** (28.858 ms frente a 26,1 ms sobre las 53 salidas). **El contrato responde «¿me entregaste lo que pedí?»; la fidelidad, «¿cuánto se parece a lo que había?». Meterlas en la misma función es el error que convertiría el diferenciador nº 1 en el mayor problema de rendimiento de FileX.**
- **Formatos que devuelven «no evaluable» con su motivo** (y no un `1.0` cómodo): AVIF/HEIF, TIFF comprimido, GIF, PNG entrelazado, PNG con `tRNS` de color clave y WebP animado. Cubrir WebP costó **un decodificador VP8L completo, 437 líneas**.
- **Coste de escribirlo, actualizado:** 3.035 líneas en total (1.542 añadidas), sin dependencias. De lo añadido, **74 líneas (4,8 %) son excepciones justificadas por datos**, la misma proporción que las 85 (6,7 %) del contrato original. **Entre el 5 y el 7 % de un verificador es la lista de casos en los que la especificación miente**, y no se deduce leyéndola.

> **Actualización del 21/08 a las 09:40 — MEDIDO (`bench/verificador-ghostscript.md`).** El prototipo pasa a **3.859 líneas** (+824 netas, sin dependencias), con **0 falsos positivos en las seis configuraciones y 12/12 fallos atrapados**. Tres cosas que cambian el presupuesto de la implementación:
>
> - **`min(alfa)` cubre ya TIFF comprimido, GIF y PNG entrelazado Adam7**, con **36 de 36** coincidencias contra `magick`. **Las estimaciones se quedaron cortas ×2,9 y ×3,6** (438 líneas reales para TIFF+GIF+LZW frente a 120-180 estimadas; 144 para Adam7 frente a 40). **El 70 % de lo añadido (582 de 824 líneas) vuelve a ser «fabricar el acceso al dato»** — tercer informe seguido que mide lo mismo (53 %, 61 %, 70 %). **La lógica de la regla nunca es el coste.**
> - **El atajo de «fila opaca» es la condición para que la cobertura merezca la pena, no una optimización.** Sin él, tres casos habrían quedado **más lentos que `magick`**. *Ampliar la cobertura de un verificador puede empeorarlo, y la única forma de saberlo es medir el peor caso.*
> - **V2 (`-count_frames`) sube la suite de fidelidad +60,6 %** (28 858 → **46 332 ms** sobre las 53 salidas; **16 592 ms son solo V2**), porque decodifica el vídeo entero. **El grupo C pasa del 38,5 % al 61,9 % del coste de convertir.** → **V2 necesita su propio interruptor dentro del grupo C.** En una suite de regresión nocturna sí; en un «verifica esta conversión» sobre un vídeo de dos horas, no. La alternativa barata —creer `nb_frames`— es la que la regla prohíbe expresamente.
>
> **Y un fallo preexistente corregido que afecta a un veredicto, no a la cosmética:** en PNG de paleta de 1/2/4 bits la coordenada del primer píxel transparente devolvía el índice del **byte**, no del **píxel**. Es la coordenada que **la regla I3** usa para leer un píxel de la salida: **I3 leía otro píxel.** No lo vio nadie porque la única entrada con alfa del corpus es de 8 bits, donde byte e índice coinciden.

> **Actualización del 21/08 a las 14:00 — MEDIDO (`bench/contrato-quinto-punto.md`).** El prototipo pasa a **4 185 líneas**, sin dependencias, con **0 falsos positivos en las cuatro configuraciones y 12/12 fallos atrapados**. Tres cosas para el presupuesto:
>
> - **V2 gana su interruptor (`--sin-v2`) y ahorra el 46,3 % de la suite de fidelidad** (70 693 → 37 947 ms) **sin cambiar ni un aviso**, subiendo los `ok_parcial` de 8 a 13 — *apagar una regla reduce cobertura, no aprueba*. **V2 encendida en la suite de regresión; apagada por defecto en un «verifica esta conversión» sobre un vídeo largo.** *(Las cifras absolutas de esta tanda **no** son comparables con las de V1 —46 332 ms allí, 70 693 aquí, sobre los mismos ficheros, con dos agentes más trabajando—; la conclusión relativa se refuerza en la misma dirección.)*
> - **El contrato cambia de firma:** `verificar(...)` acepta **`censo=`**, `cobertura` pasa a **6 claves** con `5_escritura`, `verificar_fidelidad(...)` pasa de 13 a **15 reglas** (I9 y P9), y `pedido["params"]["ocr"]` **cambia el veredicto**. **Sin `censo`, toda verificación baja a `ok_parcial`.**
> - **Y se corrigió un fallo del propio verificador que afectaba a una regla de severidad `fallo`:** `_gs_texto` leía por tubería y devolvía **vacío 6 de 430 veces** (0 de 430 leyendo por fichero temporal, **al mismo coste**), además de contar **107** caracteres en vez de 105 por la traducción de fin de línea. De esa sonda cuelgan **P2 (`fallo`), P5, P6 y P9**, y P2 compara `sha256`. **Es la observación que `verificador-ghostscript.md` §5.9 no consiguió reproducir en 20 intentos.** *La sonda no es la verdad, es otra medida con sus propios defectos — y esta vez el defecto era nuestro.*

> **Un hueco nuevo del contrato, y no se cierra con un quinto punto — MEDIDO (`bench/mcp-cabos-sueltos.md` §5.2 y §5.6).** Una entrada **envenenada en sitio** mientras el motor la lee produce una salida **internamente coherente** y **`returncode 0`**: los cuatro puntos la dan por buena. **La defensa es hacer el hash de la entrada en el staging (R8) y no volver a mirar el original.**

### 4.3 Registro y sondeo de capacidades

- Registro por reflexión con `can_register()` (de transmute).
- **Sondear en ejecución, nunca deducir del binario.** `av1_nvenc` aparece en `ffmpeg -encoders` y falla con `No capable devices found`, porque Ampere tiene decodificador AV1 pero no codificador. Sondear una vez, cachear el resultado, y degradar solo a CPU.

### 4.4 Capa MCP

> **Contradicción resuelta (21/08/2026).** Este apartado decía a la vez «catálogo generado desde el registro: **un motor nuevo aparece como herramienta**» y «**pocas herramientas**: `convert`, `inspect`, `list_targets`, `batch`». **Son incompatibles:** lo primero es exactamente el mecanismo que produce las **27 herramientas planas** de `video-audio-mcp`. **Resolución:** del registro se generan **los `enum` de los parámetros, no las herramientas.**

- **Del registro se generan los esquemas, no el número de herramientas.** Los `Literal`/`enum` de formatos de origen y destino, la lista de motores disponibles y la matriz de conversión salen del registro; **las cuatro herramientas se escriben a mano**. Un motor nuevo aparece como **un valor más en un `enum`**, no como una herramienta — lo que satisface el criterio de aceptación del hito 4 («añadir un motor no toca la capa MCP») sin inflar el catálogo. Ventaja de propina: con el `enum` en la firma, **el mensaje de error que enumera alternativas sobra** (`ffmpeg-mcp-lite` lo hace así).
- **Devolver ruta + metadatos, nunca contenido**: `{ruta_salida, formato, bytes, duración_ms, motor_usado, camino_recorrido}`. «Contenido» incluye el binario **en cualquier codificación**, base64 dentro de un `TextContent` incluido — ver `analysis/00-mcp-patrones.md` regla 1.
- **Cuatro herramientas**: `convert`, `inspect`, `list_targets`, `batch`. Anotadas con `readOnlyHint` / `destructiveHint` — **pero sabiendo lo que eso compra hoy, que es nada del lado del modelo:**

  > **MEDIDO (`bench/mcp-cabos-sueltos.md` §1.2), contra Claude Code 2.1.238:** de lo que declara el servidor, al modelo **solo le cruzan `description` e `inputSchema`**. **No cruzan** `annotations.readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint`, ni `annotations.title`, ni el `title` de la herramienta, ni `_meta`, ni `outputSchema`, ni `icons`. Y **tampoco cambian el permiso**: una herramienta marcada `readOnlyHint=true` fue denegada igual con el modo de permisos por defecto.
  >
  > **La regla sigue valiendo** —es barata, es correcta según la especificación, y otros clientes pueden usarla— **pero no puede ser el sitio donde vive una advertencia de seguridad. Lo que el modelo lee es la `description`; lo que impide una operación prohibida es el núcleo (R10).**

- **El presupuesto se fija en tokens de catálogo, no en número de herramientas — MEDIDO.** El coste por herramienta varía **×11** (79 tokens en `markitdown.convert_to_markdown`, **875** en `image-worker.resize_image`, que declara 25 parámetros descritos): depende de la **superficie de parámetros**, no del número. Las cuatro herramientas de FileX pueden costar 300 o 3.500 tokens según cómo se declaren. **Presupuesto: ≤1.200 tokens para las cuatro.** El techo del sector son 7.964 (`video-audio-mcp`, 27 herramientas), ~4 % de una ventana de 200 K gastados antes de hacer nada.
- ~~**El catálogo se paga en CADA TURNO: ×2,0–2,6**~~ **— RE-ACOTADO el 22/08 (`bench/mcp-cabos-2.md` §4): ese multiplicador es del RÉGIMEN ANSIOSO, y el despliegue real de FileX no está en él.** Las 540 ejecuciones de `saturacion-herramientas.md` §3.6 corrieron con `--tools ""` y pocas herramientas. **En una sesión normal de Claude Code, donde el servidor de FileX convive con las ~15 herramientas internas, el catálogo llega DIFERIDO: solo los nombres.** Dos catálogos con los mismos 6 nombres y esquemas y ~3.300 tokens de diferencia en descripciones dieron **26.941 = 26.941 tokens** de entrada, y el modelo lo dice literalmente: *«solo veo los nombres de las herramientas deferred, no sus descripciones»*.

  > **Tres matices para no sobre-corregir.** **(1) El coste no es cero:** los **nombres** se inyectan en cada turno y hay un `tools/list` por sesión; lo que sale del camino caliente es el **cuerpo**. **El ≤1.200 tokens sigue vivo, pero como higiene de NOMBRES, no como multiplicador por turno.** **(2) Es comportamiento de UNA versión** (2.1.238) **y depende del total de herramientas de la sesión**, no de las de FileX: con `--tools ""` y pocas vuelve el régimen ansioso, y con **40** el catálogo sale **truncado**. **El diseño no debe apostar todo a la diferición.** **(3) La otra cara no cambia:** un catálogo demasiado escueto produce **15–17 % de fallos silenciosos**. La diferición abarata el catálogo grande; **no** rehabilita recortar la cobertura de `convert`.
- **NO gastes catálogo en `resources` ni en `prompts` — MEDIDO** (ídem §3). El cliente **sí** los enumera (`resources/list` y `prompts/list`, n=1 cada uno, justo después de `tools/list`), **pero el modelo no los ve**: preguntado, responde **«NINGUNO»**. Es el mismo patrón que las anotaciones. **El único canal que llega al modelo es la herramienta.** *(Esto actualiza la observación de `mcp-cabos-sueltos.md` §1.7 de «cero lecturas»: el cliente preguntaba; nadie le había pedido al modelo que los usara.)*
- **Los roots se cachean por sesión y se invalidan con `notifications/roots/list_changed` — capacidad MEDIDA** (ídem §2). Claude Code 2.1.238 declara `roots.listChanged: true` en su `initialize`, es decir **se compromete a avisar**. Así FileX no llama a `roots/list` en cada operación. **Observar una emisión real sigue PENDIENTE** (en headless no hay forma de cambiar los roots a media sesión); si nunca llegara, la caché no se invalida hasta el fin de sesión, que es el comportamiento correcto por defecto.
- **`inspect` es la excepción a R8 y a R18**, y con número: en proceso cuesta **0,04–0,06 ms** frente a los **1,7–166 ms** del staging que R8 le impondría, **de 30× a más de 3.000× la operación a cambio de cero seguridad**. No entrega la ruta a ningún motor externo y no escribe nada (ídem §5.3).
- **Cada parámetro lleva su `description` en el esquema. Sin excepción — MEDIDO.** **0 de 193 parámetros** de los tres catálogos de referencia la lleva (§5.4): FastMCP deriva el esquema de las anotaciones de tipo y deja la semántica en la prosa del docstring. Es lo que produce casos como `add_b_roll`, con un `array of object` sin una sola clave declarada y una descripción que remite a «mensajes anteriores»: **entre esquema y descripción, la información para construir la llamada es cero.** Con `enum` generados desde el registro, FileX no se lo puede permitir.
- **La cobertura declarada es un requisito de SEGURIDAD, no de comodidad — MEDIDO y contraintuitivo.** El fallo no es de exceso de herramientas, es de defecto: **cuando el catálogo no cubre lo que se pide, el modelo no se abstiene — llama a la más parecida y declara éxito con un dato falso.** Ocurrió en el **15–17 %** de las peticiones con el catálogo de 8 (`saturacion-herramientas.md` §3.5 y §7.2, regla 3). En consecuencia:
  - **`list_targets` es el mecanismo de seguridad**, no una comodidad: es la única herramienta que puede decir, en tiempo de ejecución y sin inventar, qué conversiones existen. Debe ser la respuesta canónica a «¿puedo hacer X?».
  - **`convert` falla explícitamente** ante una combinación no soportada, nombrando la alternativa. **El silencio es el modo de fallo peligroso, no el error.**
  - **La descripción de `convert` declara sus límites**, no solo sus capacidades. Ninguno de los tres servidores de referencia describe lo que *no* hace.
  - **Prueba de regresión recomendada:** un conjunto de peticiones **fuera** de la cobertura de FileX **cuyo criterio de acierto es la abstención**. Es la única que detecta este modo de fallo, y el arnés de `bench/salidas-saturacion/` la ejecuta tal cual.
- **Lo que NO hay que presupuestar: una degradación de la elección por catálogo grande. No existe — MEDIDO.** Con 540 ejecuciones y dos modelos, 27 herramientas acertaron **100 %/98 %** (permisivo) frente al **85 %/77 %** de 8, con **0 %/2 %** de elecciones trampa frente al **15 %/17 %**. **El objetivo de cuatro herramientas se mantiene, pero su justificación es solo el coste.**
- **Prueba automática contra la subsunción:** si el esquema de la herramienta A es un subconjunto estricto del de B con la misma semántica, A sobra. En `video-audio-mcp`, **13 de 27 herramientas son casos particulares de 2**.
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

#### El presupuesto de VRAM se fija por motor **Y por resolución** — MEDIDO (`bench/ocr-ppp-nativos.md` §7.2)

| Motor | pico con la imagen extraída / a ppp nativos | **pico a 300 ppp** | crecimiento por sobremuestrear |
|---|---:|---:|---:|
| **RapidOCR** (ONNX) | 3 424 MiB | 3 424 MiB | **+0 MiB** |
| **PaddleOCR** | 3 762 MiB | 7 442 MiB | +3 680 MiB |
| **EasyOCR** | 5 026 MiB | **11 877 MiB** | **+6 851 MiB** |
| **Docling + RapidOCR torch** | — | 2 820 MiB | (coste propio +1 985 MiB) |

- **EasyOCR llega a 11 877 de los 12 288 MiB de la tarjeta —a 411 MiB de agotarla— con imágenes a solo 300 ppp**, y con un documento de **una sola página**. El «EasyOCR = +2 079 MiB» de la fase 2 (medido a 200 ppp) **subestima el peor caso casi 5×**.
- **Un presupuesto expresado solo como «motor = N MiB» es falso.** La entrada del registro LRU tiene que llevar **(motor, resolución de entrada)**, o la resolución se come el presupuesto.
- **RapidOCR es el único insensible a los ppp en VRAM** (+0 MiB entre la imagen extraída y 300 ppp): su ruta ONNX trocea la página. Es el motor de elección cuando el presupuesto está apretado.
- *(Nota de comparabilidad del propio informe: la línea base del escritorio cambió durante la sesión —2 067 MiB en la tanda de la matriz, 835 MiB en la de docling—, así que la columna comparable entre motores es el **coste propio**, y el pico absoluto es lo que importa para el presupuesto de la tarjeta en ese momento.)*

#### La resolución de entrada del OCR se calcula, no se hereda — MEDIDO (`bench/ocr-ppp-nativos.md` §9)

```
# --- REGLA VIGENTE desde el 21/08 a las 14:00 ---
# La eleccion de ppp es DEL ADAPTADOR DEL MOTOR, no del orquestador.
#
# Lo que calcula el ORQUESTADOR y le pasa al adaptador:
ppp_nativos = ancho_imagen_px / (ancho_pagina_pt / 72)      # o None si no hay imagen
#
# Lo que decide el ADAPTADOR, con su k MEDIDO:
ppp_ocr = min(max(ppp_nativos, 100), ppp_nativos * 1.25) * k_motor
#
#   k medido sobre escaneado_d4 (bench/ppp-y-normalizacion.md §2.7):
#     PaddleOCR v6 medium ............ k = 1,25
#     RapidOCR v6 small + R6 ......... k = 1,00
#     Docling+RapidOCR torch + R6 .... k = 1,00   (el 0,88 medido esta dentro del ruido)
#     EasyOCR ........................ k = 1,00   (curva plana: 58,4-63,3 en 17 puntos)
#     Tesseract ...................... k = 1,50   [P2, n=1, PENDIENTE de barrer]
#
#   Suelo: subir hacia 100 ppp, NUNCA mas de x1,25 sobre el nativo.
#   Techo de CALIDAD: no existe uno global. El de cada motor esta en su k.
#   Techo de COSTE: el tope interno del motor, no 200 ppp:
#       RapidOCR : Global.max_side_len = 2000 px de lado largo (config.yaml:10)
#       PaddleOCR: no recorta (limit_side_len=64, limit_type=min)
#     Rasterizar por encima del tope del motor es coste puro, efecto cero.
```

> ### **NO HAY UNA REGLA GLOBAL DE ppp: hay una POR MOTOR** — y esto refuta las dos versiones anteriores · MEDIDO (`bench/ppp-y-normalizacion.md` §2, 21/08 14:00)
>
> **Barrido de 17 puntos de ppp sobre `escaneado_d4` con siete configuraciones de motor, más `d3`, `d4c`, `d4f` y `patologico_escaneado`. Mediana de n=9, GPU, dispositivo fijado. Las tres unidades candidatas caen:**
>
> | candidata | qué predeciría | qué se mide | veredicto |
> |---|---|---|---|
> | **ppp absolutos** (techo 200) | todos se rompen al pasar de 200 | `d3` se rompe a **160**; `d4c`, `d4f` y `patológico` **no se rompen a 400** | **REFUTADA** |
> | **factor sobre el nativo** (×1,4) | todos se rompen al mismo factor | PaddleOCR se rompe en `d4` a ×1,4, en `d3` a ×1,6 y **nunca** en `d4c` ni `d4f` | **REFUTADA** |
> | **anchura en píxeles** | todos se rompen a la misma anchura | `d3` se rompe a **1 035 px**; `d4c` **no** se rompe a **2 070 px** | **REFUTADA** |
>
> **El experimento decisivo, 24 celdas:** el **mismo JPEG** de `escaneado_d4` reempaquetado en tres páginas de 100, 200 y 400 ppp nativos da, **a los mismos 200 ppp**, CER de **19,13 / 19,63 / 36,24 %** con PaddleOCR; **a los mismos píxeles, las tres filas coinciden A LA CENTÉSIMA** en las 24 celdas, doce parejas exactas. **17,1 puntos de diferencia al mismo ppp, con el mismo documento dentro.**
>
> > **Los ppp no son una propiedad del documento que el OCR pueda usar: son una división entre los píxeles que hay y el tamaño que el PDF dice que tiene la página. Una regla escrita en ppp está escrita en la unidad equivocada.**
>
> **Siete configuraciones sobre el mismo documento, con óptimos entre ×0,50 y ×1,80:** ×0,88 Docling+RapidOCR+R6 · ×1,00 RapidOCR v6+R6 · ×1,25 PaddleOCR (13,09 % frente a 19,30 a nativos) · ×1,60 Docling sin corregir · ×1,80 EasyOCR. **Y no es solo dónde está el óptimo, es dónde está el precipicio:** sobre `escaneado_d3`, **a ×1,4 PaddleOCR sigue bien (3,80 %) y RapidOCR+R6 se cae (2,53 → 46,84 %)**. **Un orquestador que elija los ppp sin saber qué motor los va a consumir está tirando una moneda de 43 puntos.**
>
> **El mecanismo, sondeado en ejecución:** cada motor lleva su reescalado cableado con constantes propias. **`Global.max_side_len: 2000` (`rapidocr/config.yaml:10`) hace que sobre `d4`, de 233 ppp en adelante, RapidOCR reciba el array LITERALMENTE IDÉNTICO** (1 504×1 984 px) — su tolerancia a los ppp altos **no es tolerancia, es que no los ve**; **PaddleOCR no recorta** y ve los 2 588 px. **La función que lleva de «ppp de rasterizado» a «píxeles que ve la red» es distinta en cada motor.**
>
> > **Y cómo se descubrió es la regla de la casa otra vez:** leyendo el código de PaddleX se deduce **lo contrario** (`_TEXT_DET_MAX_LIMIT_MODELS` lista los ocho detectores con `limit_type='max'`, 960 px) y **es falso para la ruta que usa `paddleocr` 3.7.0**. **Sondear capacidades en ejecución, no deducirlas.**
>
> #### La consecuencia de arquitectura, y es lo que hay que cambiar en el código
>
> > **La elección de ppp pertenece al ADAPTADOR DE CADA MOTOR, no al orquestador.** No es una constante del dominio: es **un parámetro del motor, del mismo rango que `Det.mean` o `OcrOptions.scale`**. Si se queda aquí, **cada motor nuevo hereda en silencio los ppp que le convenían a otro** — que es literalmente lo que le pasa hoy a Tesseract, al que la regla vieja le asigna 100 ppp sobre `escaneado_d2` y **le cuesta 32,10 puntos** (`bench/invocacion-aristas.md` §9).
>
> **Con `k = 1,00` por defecto la regla sigue siendo segura:** en las siete configuraciones **el nativo nunca es el peor punto del barrido**, y en cinco de siete está a menos de 1,7 puntos del óptimo. **Lo que el `k` compra es el resto.**
>
> #### Lo que SÍ queda como regla global — y es de presupuesto, no de precisión
>
> **Barrer hasta 400 ppp llevó a PaddleOCR a 11 942 y a EasyOCR a 12 037 de 12 288 MiB, con UNA página y SIN DAR ERROR** (a 346 y 251 MiB de agotar la tarjeta). **Hay que poner algún límite: el límite existe por presupuesto de VRAM aunque no exista por calidad.** Y **«EasyOCR es el caro» es cierto a ppp nativos y falso en cuanto se sobremuestrea**: PaddleOCR llega al mismo sitio. **RapidOCR corregido cuesta un tercio (+3 448 MiB) y es el único con un techo de VRAM acotado por el propio motor. El coste de no aplicar la regla son 10 GB.**
>
> #### Tres precisiones que van con esto
>
> - **El «acantilado» no es de la resolución: es del margen que le queda al motor.** Sobre `patologico_escaneado`, PaddleOCR y RapidOCR+R6 dan **0,00 % en los siete puntos de 100 a 400 ppp**: catorce celdas a cero. **El techo de ppp solo existe en los documentos que ya están cerca de fallar.**
> - **Todo el efecto vive en la letra pequeña.** En `d4`, el bloque de 11 pt se queda entre 0,64 y 2,24 % en los diecisiete puntos; **el de 7 pt es el que se pierde**. **Un documento sin letra pequeña no tiene techo de ppp que medir.**
> - **Medir el techo con un motor mal configurado da «no hay techo»:** RapidOCR sin corregir es plano en los 17 puntos con 8 cajas siempre, **porque su detector nunca encuentra el bloque pequeño y no hay nada que la resolución pueda estropear**.

> ### *(Histórico, conservado: el techo pasó de RELATIVO a ABSOLUTO el 21/08 a las 10:00 — y a las 14:00 quedó refutado también)* · `bench/corpus-d4.md` §8
>
> La revisión de las 03:30 escribió aquí `clamp(nativos, 100, nativos × 1,4)`. **Sobre `escaneado_d4` (200 ppp nativos) ese techo empeora al mejor motor:**
>
> | motor | `d4` a 200 ppp (nativo) | `d4` a **280 ppp (= ×1,4)** | efecto |
> |---|---:|---:|---|
> | PaddleOCR PP-OCRv6 medium | **19,30 %** | **36,24 %** | **+16,9 puntos, PEOR** |
> | RapidOCR PP-OCRv6 small corregido | **18,62 %** | 28,86 % | +10,2, peor |
> | RapidOCR PP-OCRv5 mobile (defecto) | 41,78 % | 41,95 % | +0,2, indiferente |
>
> **La meseta de ×1,4 se midió sobre d3, un documento de 100 ppp nativos, y era en parte un artefacto de que todo el corpus viejo fuera de 100–200 ppp.** Lo que decide no es el factor sobre el nativo sino **el tamaño en píxeles que llega al detector**: `d3` a ×1,4 son 907 px de ancho, `d4` a ×1,4 son **1 812**. Son regímenes distintos.
>
> **`clamp(nativos, 100, 200)` no viola ninguna medida existente y `×1,4` sí:** d2/d3 (100 nativos) toleran hasta 140; `d4` (200) se degrada ya a 280; el patológico (200) siempre fue el mejor caso. **El suelo de 100 se mantiene: sigue siendo lo medido.**
>
> ~~**PENDIENTE explícito: no se ha barrido la curva de ppp sobre `d4`.**~~ **BARRIDA a las 14:00 — y el techo absoluto queda refutado por dos vías, las dos MEDIDAS:**
>
> - **Su techo solo actúa BAJANDO** (con `nativos ≤ 200` no hace nada), **y bajar cuesta 12,08 puntos**: `d4` de 200 a 100 ppp sube RapidOCR+R6 de 18,62 % a 30,70 %. **En la práctica es una regla para degradar los originales buenos.**
> - **La evidencia que lo motivó es un caso que la regla anterior nunca produce:** `clamp(200, 100, 200×1,4) = clamp(200, 100, 280) = **200**`. La cifra de 36,24 % a 280 ppp es correcta y está reproducida, **pero no es evidencia contra el techo relativo. El techo absoluto se escribió para arreglar un problema que la regla anterior no podía causar** — es un autoerror del proyecto, y queda escrito como tal.
>
> **El suelo sí sobrevive, con la subida máxima recortada de ×1,4 a ×1,25:** ×1,25 es seguro en **6 de las 8** parejas (documento, motor) medidas y ×1,4 solo en **4**. *(Un original de 80 ppp llevado a 100 es ×1,25: justo dentro. Uno de 72 es ×1,39: justo fuera.)*

- **El acantilado del ×1,4/×1,6 sigue siendo real, pero es de PaddleOCR, no de la resolución.** PaddleOCR se mantiene ≤5,1 % en `escaneado_d3` **de 75 a 140 ppp** y a **160 ppp cae a 75,9 %**, su suelo de fallo, sin recuperación hasta 300 ppp. **Confirmado desde un quinto motor** (`bench/verificador-ghostscript.md` §5.3, 60 celdas): con el OCR de Ghostscript, **en d3 sobremuestrear es monótonamente catastrófico** (105,1 % a 75 ppp → **834,2 %** a 300, con `spa`) — **no hay acantilado, hay una rampa** — mientras que **en d1 y d2 la curva es plana en 0,0 % de 100 a 300 ppp**.
- **Suelo 100 ppp, y ese sí es de todos:** a 75 ppp **RapidOCR se rompe en d2** (0,0 % → 44,3 %), **EasyOCR se degrada en d1** (0,0 % → 12,7 %) y el OCR de Ghostscript pasa de 0,0 % a 3,8 % en d2. **Submuestrear hace daño antes de que sobremuestrear lo haga.** No es «cuanto menos, mejor»: es un óptimo con meseta.
- **`OcrOptions.scale` de docling vale 3,0 por defecto → 216 ppp FIJOS** para cualquier documento, sea cual sea su resolución nativa. **Hay que fijarlo siempre, explícitamente:** `scale = ppp_objetivo / 72`. Sobre d3 la sonda confirma que llegan **1398×1836 px** al motor, ×2,16 del original. En este corpus resulta benigno para Docling+RapidOCR torch, **pero con PaddleOCR el equivalente sería catastrófico**, y es una constante que nadie eligió para estos documentos.
  > **Matiz MEDIDO el 21/08 a las 14:00** (`ppp-y-normalizacion.md` §2.1b): **su defecto no era el problema que parecía.** Sobre los cinco escaneados con docling **sin** corregir, `scale=3,0` es **indiferente en cuatro** y **MEJOR en `d3`: 58,23 % frente al 75,95 % de rasterizar a ppp nativos, −17,72 puntos.** **Fijarlo sigue siendo obligatorio —un parámetro que nadie eligió no es una defensa—, pero «fijarlo A LOS ppp NATIVOS» era la parte equivocada de la recomendación.** Es el mismo fenómeno de arriba: para ese motor, `k > 1`.
- **Si la página es una sola imagen a página completa, extraerla sin rasterizar** (`pypdfium2`: `page.get_objects(filter=FPDF_PAGEOBJ_IMAGE)` + `obj.get_bitmap(render=False)`; **no hace falta poppler ni `pdfimages`**). Da **el mismo CER en las 16 celdas** que rasterizar a ppp nativos, es más barato (221 ms frente a 465 ms en el patológico) y **no depende de que la cabecera diga la verdad**.
- ~~**Selección de motor por caso, no global (R3):** caso normal → Docling + RapidOCR `backend="torch"`; **degradación severa → PaddleOCR**; VRAM apretada → RapidOCR ONNX; EasyOCR, nunca.~~ **REVISADA el 21/08: la regla de conmutación pierde su motivo — ver abajo.** Lo que sobrevive intacto es **EasyOCR, nunca** (43,0 % en d2 a todas las resoluciones, 61,41 % en d4, pico de 11 877 MiB).

#### Fijar la normalización del detector de RapidOCR — **la corrección más barata del proyecto** · MEDIDO (`bench/corpus-d4.md` §7, §10)

**RapidOCR 3.9.2 normaliza el PP-OCRv6 con `mean=std=0,5` cuando el `inference.yml` que Baidu distribuye JUNTO AL MODELO declara las estadísticas de ImageNet.** Eso —y no el tamaño del modelo, ni el idioma del reconocedor, ni el del detector— era la causa de que el mismo checkpoint diera **3,80 % en PaddleOCR y 75,95 % en RapidOCR** sobre `escaneado_d3`.

```python
# Aplica a RapidOCR ONNX y a Docling+RapidOCR con la familia PP-OCRv6
params = {
    "Det.mean": [0.485, 0.456, 0.406],   # ImageNet: lo que declara el
    "Det.std":  [0.229, 0.224, 0.225],   # inference.yml del propio modelo
    "Det.thresh": 0.2,
    "Det.box_thresh": 0.45,
    "Det.unclip_ratio": 1.4,
    "Det.max_candidates": 3000,
}
```

- **A/B causal, mismo checkpoint:** la **normalización sola** vale **64,6 puntos** de CER en d3 (75,95 → 11,39); el **post-proceso solo**, **0,0**; **los dos juntos reproducen la cifra de PaddleOCR exactamente (3,80 %)**. Con `medium`, **2,53 %** — el número exacto de PaddleOCR.
- **Prueba directa, no argumento:** el detector con el defecto encuentra **1 renglón de 3** en d3 y **8 de 12** en d4; con la corrección, **3 de 3 y 12 de 12**. **No es que lea mal: es que no ve.**
- **Docling hereda el defecto** —construye RapidOCR con los parámetros por defecto— y **es corregible desde fuera, sin parchear el paquete**.
- **Seis números por 72,2 puntos de CER.**
- **Regla general que se lleva, no un parche:** *cuando el motor y el modelo vienen de proyectos distintos, hay que comprobar que el preprocesado que aplica el motor es el que declara el fichero de configuración del modelo.* Mismo tipo de fallo que `onnxruntime-gpu` cayendo a CPU en silencio: **nada da error, solo empeora.**
- ~~**PENDIENTE:** validar la corrección fuera de este corpus.~~ **VALIDADA el 21/08 a las 14:00, y con condición. Ver el bloque siguiente.**

> ### La corrección es segura **solo sobre `PP-OCRv6 small`** — y eso la convierte en una tabla, no en un ajuste · MEDIDO (`bench/ppp-y-normalizacion.md` §3)
>
> **Validación fuera del corpus `d4`: 15 documentos, n=9, GPU, incluidas cuatro rasterizaciones del patrón oro.** Sobre `PP-OCRv6 small`: **6 mejoras, 9 empates, 0 empeoramientos**, hasta **−72,15 puntos** en `d3`.
>
> **Pero se buscaron los casos peores y se encontraron:**
>
> | Caso | Delta | Contexto |
> |---|---:|---|
> | **`PP-OCRv4 mobile` sobre `tipico_texto` del patrón oro** | **+42,50** (0,83 → **43,33 %**) | un documento **limpio**. **La corrección no rompe los casos difíciles: rompe uno fácil** |
> | `PP-OCRv6 tiny` sobre `d3` / `d4c` | **+16,45** / **+13,60** | dirección contraria a `small` y `medium` |
> | `PP-OCRv5 mobile` | 4 de 15 celdas peores | hasta +8,89 |
>
> **Cribado de 7 detectores × 4 variantes: 18 mejoras, 12 empates y 12 EMPEORAMIENTOS sobre 42 celdas.**
>
> **Tres lecturas para la implementación:**
>
> 1. **El desajuste es UNIVERSAL; el daño NO.** Los **ocho** `inference.yml` que Baidu distribuye, de PP-OCRv3 a PP-OCRv6, declaran ImageNet, y `rapidocr/config.yaml` aplica `0,5` a los ocho —**un solo bloque, sin condicionar por `ocr_version`**—. Pero **solo `PP-OCRv6 small` se hunde por ello**. La hipótesis obvia es falsa para 7 de los 8: **la robustez a la normalización varía por checkpoint y no se puede predecir del fichero de configuración.**
> 2. **«Corregir el desajuste» no es lo mismo que «mejorar el motor».** En `PP-OCRv4 mobile`, la configuración *correcta según el fabricante* da **peor** resultado en 4 de 6 documentos. **Devolverle al modelo lo que su `inference.yml` declara no garantiza nada: hay que medirlo checkpoint por checkpoint.**
> 3. **Las dos mitades no son separables ni monótonas.** Sobre `v6 medium`, el post-proceso **solo** da `d4c` = 0,84 %, **mejor que la corrección completa (9,56) y que el defecto (14,09)**. **La receta de seis números es la correcta para `small` y no lo es para `medium`.**
>
> **Cómo debe entrar en FileX — una tabla POR CHECKPOINT, con el motivo medido en cada línea:**
>
> ```python
> NORMALIZACION_DETECTOR = {
>     ("PP-OCRv6", "small"):  { ... los seis parametros ... },  # 0 regresiones en 15 docs
>     ("PP-OCRv6", "medium"): None,   # 3 mejor / 1 peor: no compensa el riesgo
>     ("PP-OCRv6", "tiny"):   None,   # +16,45 en d3, +13,60 en d4c
>     ("PP-OCRv5", "mobile"): None,   # 4 de 15 celdas peores
>     ("PP-OCRv5", "server"): None,
>     ("PP-OCRv4", "mobile"): None,   # +42,50 en tipico_texto del patron oro
>     ("PP-OCRv4", "server"): None,
> }
> ```
>
> **Docling: 7 de 7, cuatro mejoras grandes, cero regresiones y coste en tiempo NULO** (la mediana se mueve entre −3,2 % y +5,8 %, dentro del ruido). Se pasa por **`RapidOcrOptions.rapidocr_params`**, el punto de extensión público (`models/stages/ocr/rapid_ocr_model.py:445-448`), **sin parchear el paquete**: `d3` 75,95 → **5,06**, `d4f` 22,15 → **0,67**.
>
> **Una comprobación que el código debe llevar:** leer del objeto ya construido (`lector.text_det.mean` / `.std`) y compararlo con lo pedido. **Sin eso, «he puesto ImageNet» es una intención, no un hecho** — el mismo patrón que `session.get_providers()` frente a `get_device()`.
>
> **Y el mecanismo, con fichero y línea, listo para reportar aguas arriba:** `rapidocr/config.yaml:143-149` → se lee en `ch_ppocr_det/main.py:33-34,79` → se aplica en `ch_ppocr_det/utils.py:71` (`(img*scale - mean)/std`). Con `scale = 1/255` la entrada queda en `[-1,1]` uniforme cuando la red espera `[-2,1, +2,6]` con desviaciones por canal. **Sin aviso, sin comprobación y sin error.**

**Y un defecto de configuración que FileX arrastra hoy:** `bench/scripts/ocr_motor.py` fija **`LangRec.CH`** — la línea base lee castellano con un **reconocedor de chino**. Con detector fijo y PP-OCRv5, el reconocedor chino cuesta **19,0 puntos en d3 y 23,7 en d4** frente al latino. **MEDIDO.**

> **El parche (B11) queda PROPUESTO, NO APLICADO, y su contenido CAMBIA — MEDIDO** (`ppp-y-normalizacion.md` §4): **no es «añadir R6 a `ocr_motor.py`»**, porque **sobre el `PP-OCRv5 mobile` que usa hoy la corrección NO es recomendable**. Es **cambiar el checkpoint a `PP-OCRv6 small` —el único con 0 regresiones— Y aplicar R6 ahí**. **Saldo medido del parche completo: 7 mejor, 2 igual, 2 PEOR** (`d3` −73,42 · `d4` −23,16 · `d4c` −14,43, frente a `d4a` **+5,87** y `d4f` +1,01). **Las dos regresiones son del cambio de checkpoint, no de R6, y hay que declararlas: no es una mejora gratis en todas las filas.** *(Y la cifra de `Rec.lang_type = latin` **no se ha reverificado** en el arnés nuevo; en PP-OCRv6 esa variable no existe.)*

#### La tabla de selección de motor, revisada — MEDIDO (`bench/corpus-d4.md` §10)

| documento | PaddleOCR v6 medium (GPU) | **RapidOCR v6 small + normalización (GPU)** | **la misma, en CPU** |
|---|---:|---:|---:|
| `patologico_escaneado` | 0,00 % · 296 ms | **0,00 % · 446 ms** | 0,00 % · 1 024 ms |
| `escaneado_d1` | 0,00 % · 162 ms | **0,00 % · 125 ms** | 0,00 % · 532 ms |
| `escaneado_d2` | 0,00 % · 98 ms | **0,00 % · 78 ms** | 0,00 % · 324 ms |
| `escaneado_d3` | **2,53 %** · 90 ms | 3,80 % · 82 ms | 3,80 % · 380 ms |
| `escaneado_d4` | 19,30 % · 393 ms | **18,62 % · 340 ms** | **18,62 % · 1 178 ms** |

> **Un solo motor cubre el corpus entero, gana a PaddleOCR en cuatro de las cinco filas, arranca en 3,7 s en vez de 18,4 y funciona en CPU.** La regla «degradación severa → cambiar a PaddleOCR» **pierde su motivo: la diferencia que la justificaba era el defecto de configuración, no el motor.** *La excepción es d3, donde PaddleOCR gana por **1,27 puntos — un carácter sobre 79**. No es base para una regla de conmutación.*
>
> **Y en CPU el coste es utilizable:** RapidOCR es solo **×2,3–3,8** más lento que en GPU (**0,32–1,18 s/página**), mientras PaddleOCR es **×9,8–13,8** (hasta 5,42 s) y EasyOCR ×6,5–12,0. **Para RapidOCR la GPU es una comodidad; para PaddleOCR es un requisito.** *(En CPU, `onnxruntime` bate a `torch` en las cinco filas de docling, entre 1,2 % y 20,0 %, con **CER idéntico**: la elección de backend es puramente de coste.)*
>
> **Cómo detectar «degradación severa»: sigue PENDIENTE**, pero ahora hay caso con gradiente (`d4`) contra el que calibrar y **dos señales candidatas medidas** — **cajas detectadas frente a área de texto**, y **el tiempo** (en Ghostscript, d3 cuesta ×4,5 lo que d2 a la misma resolución porque alucinar emite muchas más cajas).

- **«CPU y GPU dan salida idéntica carácter a carácter» es FALSO — MEDIDO** (`corpus-d4.md` §9.3): **5 de 21 celdas difieren**, y **la CPU es mejor en dos y peor en tres**. *La salida coincide mientras el documento es fácil; en la zona de degradación donde el motor duda, el dispositivo cambia el resultado.* **Consecuencia directa: no se puede validar en CPU y desplegar en GPU dando por hecho el mismo resultado, y toda prueba de regresión de OCR tiene que fijar el dispositivo.**

### 4.6 Confinamiento del sistema de ficheros — **las 18 reglas**

> **Corrección MEDIDA (21/08/2026).** Este apartado decía que la lista blanca de raíces **«hay que inventarla»**, «no hay de dónde copiar esto». **Es falso, y estaba desmentido dos veces** (`analysis/00-mcp-componentes.md` §3.2, `RESULTADOS-MCP.md` §10). La referencia oficial `modelcontextprotocol/servers/src/filesystem` **resiste 28 de 29 vectores de ataque medidos**, con ~1.000 líneas de tests, y su porte a Python es ~1 día de trabajo.
>
> **La corrección es PARCIAL, y esta parte hay que conservarla:** lo que existe ya hecho es **la contención de rutas**. **El mensaje opaco, el confinamiento frente a procesos externos y el contenido hostil siguen siendo trabajo propio de FileX** — ninguna referencia los resuelve.

Resumen accionable. **La evidencia completa de cada regla está en `bench/mcp-refs-confinamiento.md` §8 (R1-R15), `bench/confinamiento-multimedia.md` §6 (R16-R17) y `bench/aristas-nominales.md` §5.2 (R18).** Se aplican en el orden en que están escritas, salvo R17, que corre antes que todas, y **R18, que envuelve a todas: es el directorio dentro del cual ocurre la conversión**.

| # | Regla | Evidencia |
|---|---|---|
| **R17** | **Topes léxicos ANTES de `realpath`**: ≤4 096 caracteres, ≤64 componentes, ≤16 enlaces | Una ruta de ~6 000 componentes cuesta **5-16 s** en `realpath`; `realpath(strict=False)` sigue cadenas sin límite. Rechazar cuesta 0,16 µs |
| **R1** | **Predicado léxico antes de tocar el disco. Sin excepciones** | Es lo único que separa a `filesystem` (no es oráculo fuera) de `kordoc` (enumera el disco entero). **El orden es toda la diferencia** |
| R2 | Comparar por **segmentos**, nunca por prefijo de cadena | `permitido_secreto` denegado con raíz `permitido`, gracias al `+ path.sep` |
| R3 | Aplicar `normcase`; rechazar raíces que normalicen a la raíz de una unidad | 5 falsos negativos medidos en Windows (minúsculas, `\\?\`, 8.3, `/d/…`, `/mnt/d/…`) |
| **R4** | **Un mensaje opaco y constante** para denegado y no-existe: sin ruta, sin ruta resuelta, sin lista blanca. **Y equivalencia en la latencia** | Tres fugas distintas medidas. En multimedia el eco de la ruta es **unánime**: los tres MCP filtran la ruta y son oráculos. **Trabajo propio de FileX** |
| R5 | La misma opacidad **por elemento** en las operaciones por lotes | 6 rutas → 6 mensajes con la lista blanca repetida → **419 tokens para no decir nada** |
| R6 | Denegar por defecto; **sin raíz de lectura y de escritura configuradas, el motor no se registra** | `kordoc` sin `KORDOC_ROOT` no confina nada; dos de los tres MCP de multimedia **no tienen concepto de raíz** |
| R7 | Resolver enlaces **en cada llamada** y validar la ruta resuelta. **En Linux, además, `O_NOFOLLOW` + `dir_fd` recorriendo la ruta segmento a segmento**; en Windows no hay equivalente y hay que quedarse con `realpath` por llamada | El vector TOCTOU del encargo quedó refutado precisamente por esto. **MEDIDO** (`mcp-cabos-sueltos.md` §5.5): en Windows **no existen** `O_NOFOLLOW`, `O_PATH`, `dir_fd` ni `/proc/self/fd`. Son un **complemento de la validación, nunca un sustituto del staging** |
| **R8** | **Copiar la entrada a un staging privado tras validarla**; al motor externo solo la ruta del staging. **Inmediatamente después de validar**, no «en algún momento antes de llamar al motor». **Con una excepción explícita: `inspect` (ver abajo)** | La ventana que importa no es la intra-proceso (0 fugas en 155 200 intentos) sino la del **binario externo**. **Ahora MEDIDA: el 99,6 % de la conversión** (9 758 ms de 9 794 en una transcodificación x264), porque el motor abre la entrada a los **23-53 ms** y no la suelta hasta terminar. **Precio del staging: 0,10 %-19,6 %** de la operación, a cambio de reducir la ventana **×4 a ×976**. **Trabajo propio de FileX** |
| R9 | Raíz de lectura ≠ raíz de escritura, **como lista inmutable del núcleo**, no como parámetro por herramienta; no sobrescribir en silencio | `ffmpeg-mcp-lite` confina `convert` y deja `merge`/`subtitles` con `output_path` libre, en la misma base de código |
| **R10** | **La validación vive en el núcleo, no en la superficie** | La CLI de kordoc ignora `KORDOC_ROOT` y leyó fuera de la raíz con `exit=0`. **FileX tiene cuatro superficies** |
| R11 | El tipo real se decide por **contenido**, no por extensión | En un conversor la extensión **elige el motor**. Y el ADS lo elude por el otro lado: `entrada.png:oculto` llegó al motor en los tres MCP |
| R12 | Normalizar el nombre de salida; prohibir ADS, nombres reservados, puntos y espacios finales | **Un vector concedido de 29 fue un ADS.** Renombrar a nombre opaco en el staging cierra además la inyección de opciones |
| R13 | Los *roots* del cliente se **intersecan** con la lista del servidor, no la reemplazan; **sin roots del cliente se degrada a la lista inmutable, no se falla** | `index.ts:181` sustituye. **IMPLEMENTADA, no solo implementable — MEDIDO** (`mcp-cabos-sueltos.md` §2): el patrón condicional son **ocho líneas** (`bench/salidas-mcp-cabos/cabo2_roots.py`) y está demostrado en **las cuatro configuraciones** (2 eras × cliente con y sin roots) **y contra el cliente real**. La clave es que **el resolver decide si pregunta**: devolver el marcador `ListRoots()` dispara el `-32021`; devolver un `ListRootsResult` construido a mano lo esquiva y **nunca aborta**. **Cachear los roots por sesión es trabajo del servidor**: el resolver corre una vez **por herramienta que los pida**, no una por sesión |
| R14 | El error nombra la **capacidad** que falta, nunca el **comando** que la instala | kordoc responde con su propia CLI; docling con `pip install openai-whisper` |
| R15 | Describir `path` como si el modelo no supiera nada | Las 14 herramientas de la referencia declaran `"path": {"type":"string"}` sin descripción |
| **R16** | **El argumento de SALIDA es tan peligroso como el de entrada**: validar el destino contra la raíz de escritura **antes** de construir la línea de comando; escribir a un staging de salida y mover solo tras validar | Los tres MCP de multimedia escriben fuera de la raíz, incluida `C:\Windows\Temp`. **La escritura arbitraria no la comete FileX, la comete ffmpeg o sharp** |
| **R18** | **Un directorio de trabajo propio y DESECHABLE por conversión, con el `cwd` del proceso hijo dentro de él. No basta con validar la ruta de salida.** Al terminar: listar el directorio, comparar con lo declarado (punto 5 del contrato, §4.2), recoger los ficheros que sí son parte de la salida, y borrarlo entero. **⚠ NO ES HIGIENE: ES REQUISITO DE COSTE — MEDIDO el 21/08 a las 14:00.** Con R18, el punto 5 cuesta **+11,0 %** del contrato (0,4254 → 0,4722 ms) y **entra en el camino caliente**; **sin R18, sobre un directorio real de 1 000 ficheros, cuesta 3,66 ms — ×8,6 el contrato entero— y lo saca de él** (`bench/contrato-quinto-punto.md` §2.2). **Esto sube su prioridad: R18 es lo que hace viable el quinto punto, no un acompañamiento suyo** | **MEDIDO** (`bench/aristas-nominales.md` §5.2). **Hay motores que escriben fuera del destino y en el `cwd` del proceso:** `ffmpeg -i x out.mpd` deja los segmentos DASH (`init-stream0.m4s`, `chunk-stream0-00001.m4s`, **528 KB**) en el directorio de trabajo y entrega un `.mpd` de **1,2 KB inútil**; `magick … out.html` produce **dos** ficheros en el destino y un tercero (`u_map.shtml`) en el `cwd`. Aparecieron como **33 ficheros no pedidos en la raíz del repositorio**. **R8 y R16 asumen que el motor escribe donde se le dice: estos dos no** |

> **La excepción de R8, y es la única que sale medida — `inspect` (`bench/mcp-cabos-sueltos.md` §5.4).**
>
> | Fichero | Bytes | `ffprobe` | Copia | **Copia / `inspect`** |
> |---|---:|---:|---:|---:|
> | `trivial.png` | 316 | 36,1 ms | 1,0 ms | 0,03 |
> | `tipico.mp4` | 16.246.490 | 44,6 ms | 10,0 ms | 0,22 |
> | `patologico_16bit.tif` | 72.001.016 | 70,2 ms | 45,6 ms | 0,65 |
> | **`fuente_4k.mp4`** | **127.932.819** | **57,8 ms** | **76,1 ms** | **1,32** |
>
> **R8 se aplica a toda operación que entregue la ruta a un motor externo que vaya a leer el contenido.** Para `inspect`, donde el motor solo lee cabeceras y la ventana es de decenas de ms, **el staging cuesta 1,32× la propia operación** sobre un fichero de 122 MB (punto de cruce ~90-100 MB en esta máquina, y depende del disco): `ffprobe` tarda 36-70 ms **casi con independencia del tamaño**, mientras que la copia crece linealmente.
>
> **La salida correcta no es «saltarse R8 en `inspect`», es sacar `inspect` del proceso externo:** leer los metadatos **en proceso**, que `bench/coste-verificacion.md` ya midió **145× más barato**. Así desaparecen a la vez el motor externo, la ventana y la necesidad de staging. **Converge con la corrección ya aplicada en §4.2 —quitar «(`ffprobe`)» del contrato— pero por seguridad en vez de por coste.**

> **Y el mecanismo con el que estaba escrita R8 era el equivocado — MEDIDO** (`mcp-cabos-sueltos.md` §5.2). La justificación decía «sustituir la entrada por otra cosa mientras el motor lee». **Ese vector no funciona en ninguna de las dos plataformas**, y por razones **opuestas**: en Windows el bloqueo obligatorio **deniega** sustituir, borrar y mover; en POSIX las tres se permiten, pero **el descriptor abierto sigue apuntando al inodo original y el motor lee lo mismo**. **El único vector que funciona en las dos es escribir EN SITIO sobre el mismo inodo**: la ruta sigue siendo la validada, `realpath` sigue dando lo mismo, y los bytes son otros. **Ninguna validación de rutas lo detecta, porque no hay nada que detectar en la ruta.** Y ffmpeg convirtió el fichero envenenado con **`returncode 0`**.
>
> *(El vector clásico **sí** funciona en los **23-53 ms** entre que el proceso arranca y abre el fichero. Es corto, y R8 lo cierra igual — por eso el staging va inmediatamente después de validar.)*

**Lo que sigue siendo trabajo propio de FileX, y no lo cubre ninguna referencia:**

- **El mensaje opaco (R4)** y su equivalencia de latencia. Ninguno de los cinco servidores sondeados lo hace.
- **El confinamiento frente a procesos externos (R8, R16).** Todas las referencias validan para *leer ellas*; FileX valida para que **otro proceso** lea y escriba, con una ventana de minutos.
- **El contenido hostil.** **`policy.xml` propio de ImageMagick** — ninguno de los seis orquestadores lo distribuye y dos lo *debilitan* por `sed`. Es el vector clásico.
- **Límites que no valgan cero.** El fallo dominante del sector no es «faltan límites» sino «los límites existen con default 0». Timeout por conversión, tope de memoria, tamaño de entrada y de salida, número de páginas o fotogramas.
- **Nunca devolver `stderr` crudo al modelo.** Observado en vivo: docling-mcp respondió `pip install openai-whisper` al agente; `video-audio-mcp` reenvía 872-1.228 tokens de banner de compilación, **que además es un oráculo de existencia enterrado**.

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
| **La resolución de OCR la elige el ADAPTADOR DEL MOTOR: `ppp_ocr = min(max(nativos,100), nativos×1,25) × k(motor)`** | **NO HAY UNA REGLA GLOBAL DE ppp — MEDIDO el 21/08 a las 14:00** (`bench/ppp-y-normalizacion.md` §2). Las dos versiones anteriores están refutadas: ~~×1,4 relativo~~ y ~~200 absoluto~~. **Los ppp no son la unidad** (el mismo mapa de bits en tres páginas da 19,13 / 19,63 / 36,24 % **a los mismos ppp** y coincide **a la centésima** a los mismos píxeles, 24 celdas), **y tampoco lo son ni un factor fijo ni una anchura fija**. **Siete configuraciones sobre el mismo documento dan óptimos entre ×0,50 y ×1,80**, y a ×1,4 sobre `d3` el mismo fichero es **seguro para PaddleOCR (3,80 %) y catastrófico para RapidOCR+R6 (46,84 %)**. **Suelo 100, con subida máxima ×1,25** (×1,4 solo es seguro en 4 de 8 parejas). **Techo de coste: el tope interno del motor** (RapidOCR recorta a 2 000 px; por encima de 233 ppp recibe el array idéntico). Detalle en §4.5 |
| **Poner ALGÚN límite de ppp aunque no exista techo de calidad: es presupuesto de VRAM** | Barrer hasta 400 ppp con **una sola página** llevó a PaddleOCR a **11 942** y a EasyOCR a **12 037 de 12 288 MiB**, **sin dar error** (`ppp-y-normalizacion.md` §7). **El coste de no aplicar la regla son 10 GB** |
| **Fijar la normalización del detector de RapidOCR: `mean/std` de ImageNet — pero SOLO en `PP-OCRv6 small`** | **72,2 puntos de CER por seis números** sobre ese checkpoint, con **0 regresiones en 15 documentos**. **Pero aplicarla a ciegas a la familia empeora 12 de 42 celdas, con +42,50 puntos en `PP-OCRv4 mobile` sobre un documento LIMPIO del patrón oro** (`ppp-y-normalizacion.md` §3.4). **El desajuste es universal —los ocho `inference.yml` declaran ImageNet y RapidOCR aplica 0,5 a los ocho— y el daño no.** Va como **tabla por checkpoint**, no como ajuste global. Docling hereda el defecto y se corrige desde fuera, sin coste. §4.5 |
| **El idioma del OCR sale de una LISTA BLANCA, nunca de la entrada del usuario** | **`-sOCRLanguage=osd` revienta Ghostscript con `0xC0000005`** (violación de acceso) **sin devolver un código de error**. Misma familia que `av1_nvenc`, con el precio subido: aquí no hay error que capturar. **Y elegir mal el idioma cuesta 13,6 puntos de CER real y no cuesta un milisegundo** (`bench/verificador-ghostscript.md` §5.1, §5.5) |
| **G6: si la salida tiene la MISMA firma que la entrada y no era eso lo que se pedía, es sospechosa** | **Atrapa 22 de 22** el fallo emblemático (`magick x.png y.group4` → rc=0 y un PNG), **donde el vocabulario de firmas atrapa 0**, viejo o nuevo. **Cuesta 0** (las dos firmas ya están calculadas) y da **0 falsos positivos** sobre las 53 del patrón oro. Severidad `aviso`: está calibrada sobre **un solo motor** (`bench/firmas-contrato.md` §7.1) |
| **El punto 1 del contrato no aplica al 23,6 % de los formatos, y ahí tampoco aplican el 2 ni el 3** | De 381 formatos con veredicto, **90 no tienen marcador**. **No se pueden verificar 500 firmas porque no existen 500 firmas**: o se verifican las que existen y se declara `no_aplica` en las que no, o se declaran menos formatos. La cobertura va en **cuatro estados**, no en un booleano — antes `1_firma` valía `True` en el 100 % de los ficheros evaluando el **12,4 %** (ídem §2.1, §3) |
| **Comprobar que el motor no escribió fuera de lo declarado** | `ffmpeg -i x out.mpd` deja **528 KB de segmentos DASH en el `cwd`** y entrega 1,2 KB inútiles; `magick … out.html` produce **dos** ficheros en el destino. Punto 5 del contrato (§4.2) y regla **R18** (§4.6) |
| **No presuponer que CPU y GPU dan la misma salida** | **5 de 21 celdas difieren**, y la CPU es mejor en dos y peor en tres. Toda prueba de regresión de OCR **fija el dispositivo** (`bench/corpus-d4.md` §9.3) |
| **Fijar `OcrOptions.scale` en docling. Siempre, explícitamente** | Su defecto es **3,0 → 216 ppp fijos** para cualquier documento. `scale = ppp_objetivo / 72` |
| **El presupuesto de VRAM se fija por motor Y por resolución** | EasyOCR: **5 026 MiB** con la imagen extraída → **11 877 MiB a 300 ppp**, a 411 MiB de agotar la tarjeta. El «+2 079 MiB» de la fase 2 subestima casi **5×** |
| **Verificar CABECERAS en proceso, no con `ffprobe` — pero PÍXELES con la sonda externa** | 0,372 ms frente a 54,06 ms: **145×** para cabeceras, y en 15 de 39 órdenes el subproceso cuesta más que convertir. **REFUTADO PARCIALMENTE el 21/08 a las 14:00 para el otro régimen:** `magick` mide la misma tinta en **138 ms** donde el lector en proceso tarda **2 834** sobre 1920×960 (**×20,5**), y **el punto de cruce está en ~0,1 Mpx** (`bench/contrato-quinto-punto.md` §4.3). **Son dos regímenes, no una regla única** |
| **Fuerza lo que el motor no puede deducir; no fuerces lo que ya deduce bien** | Forzar el códec «por defecto» del muxer `image2` **escribe un JPEG dentro de un `.ppm`**: peor que no forzar nada. **Un valor declarado «por defecto» no es una capacidad sondeada.** Fuerza el muxer, el mapeo de pistas y las restricciones del codificador (`bench/invocacion-aristas.md` §7.2) |
| **`-frames:v 1 -update 1` cuando el destino es una imagen única** | Recupera **13 de las 27** aristas del residuo: es la bandera con mejor relación coste/beneficio medida (ídem §5.2) |
| **`imagen → pdf` con la densidad AJUSTADA A LA PÁGINA, no fija** | `-density 150` quita la marca P7 y sigue dando **un A3 y medio**; calculando la densidad para que quepa: **A4 exacto y 7 de 7 ÍNTEGRO**, con las **6 de 6 degradaciones P7 desaparecidas** (ídem §6) |
| **Todo sondeo de capacidades empareja ESCRITOR y LECTOR del mismo motor** | `ffmpeg -i x m.rgb` usa el muxer `rawvideo`, **ignora la extensión y vuelca el `pix_fmt` de la entrada**: el fichero llamado `.rgb` no contiene RGB (ídem §7.1) |
| **`stdin=DEVNULL` en todo subproceso** | Ver abajo |
| **Toda operación larga devuelve un `job_id` al empezar** | Ver abajo |
| **`mcp>=2.0.0` en el servidor de FileX** | Ver abajo |

### 5.1 `stdin=DEVNULL` en todo subproceso — **MEDIDO**

Todo subproceso corre con **`stdin=DEVNULL`**, con las **banderas no interactivas** (`-y`, `-nostdin`), con **timeout del lado del servidor** y **matando el árbol de procesos**, no solo el padre.

**El orden importa: `stdin=DEVNULL` primero, las banderas después.**

**Evidencia:** `video-audio-mcp` **cuelga la sesión MCP entera** en la conversión más común que existe — ffmpeg hereda la tubería JSON-RPC como `stdin` y se queda esperando a que alguien conteste `Overwrite? [y/N]`. **1,4 s con `-y`. Infinito sin él.**

Y el detalle que convierte esto en regla de construcción y no en disciplina: **el mismo fichero pasa `-y` en sus 7 invocaciones por `subprocess` y en ninguna de sus 32 por `ffmpeg-python`**. No es que sus autores ignorasen el problema: lo resolvieron en una vía y lo olvidaron en la otra.

> **Una disciplina que hay que recordar en cada punto de invocación no es una defensa.** Hay que cerrarla en la **construcción del proceso**, donde ninguna vía pueda saltársela.

#### `-y` es NECESARIO y **NO SUFICIENTE** — resultado causal medido A/B (`bench/mcp-cabos-sueltos.md` §4.3)

Esto deja de ser una nota de orden y pasa a ser el motivo entero de la regla. Un servidor MCP mínimo con **dos herramientas idénticas salvo en una línea**, ejecutando la misma secuencia **con `-y` en todas partes** y sobre **rutas de salida nuevas**:

| Herramienta | Diferencia | Colgadas |
|---|---|---:|
| `conv_heredado` | `stdin` **no se toca** → hereda la tubería JSON-RPC | **2/5** |
| `conv_devnull` | **`stdin=subprocess.DEVNULL`** | **0/5** |

**Y la variable que lo dispara es más estrecha de lo que parecía: no es «una tubería», es la tubería que el servidor MCP está leyendo a la vez.** Con tuberías mudas fuera de MCP, 0 de 15 secuencias colgaron; con la tubería JSON-RPC viva, 2 de 5. **El hijo y el bucle de lectura del servidor compiten por el mismo descriptor.**

> **Una revisión que se conforme con «¿lleva `-y`?» da por bueno un código que cuelga la sesión el 40 % de las veces.** Y `-nostdin` tampoco basta por sí solo: empata con `-y` en los controles, pero **es otra bandera más que hay que acordarse de poner en cada punto de invocación**. Solo `stdin=DEVNULL` en el constructor del proceso no se puede olvidar, **porque no hay puntos de invocación: hay uno.**

**Alcance del fallo, ampliado — MEDIDO:** de 1 herramienta reproducida end-to-end se pasa a **6 de las 26 que tocan ffmpeg**, con la clasificación de las 27 hecha **por AST** (reproducible, no recuento manual): **cero `overwrite_output()` y cero `stdin=` en todo el fichero**. El contraste es de tres órdenes de magnitud: **554-695 ms si la ruta de salida es nueva, infinito si ya existe.** Las 20 restantes quedan cubiertas por la clasificación, **no por ejecución**: eso sigue siendo **PENDIENTE**.

**Y matar el árbol no siempre alcanza al nieto — MEDIDO:** un `ffmpeg.exe` sobrevivió a un `taskkill /F /T` sobre el servidor. **FileX necesita inventario explícito de los procesos que lanza** (job object en Windows, grupo de procesos en POSIX), no confiar en la relación padre-hijo.

*(`ffmpeg-mcp-lite`, por su parte, dejó procesos `ffmpeg` huérfanos vivos **13 minutos** después de morir su servidor. De ahí lo de matar el árbol.)*

### 5.2 Toda operación larga devuelve un `job_id` al empezar — **MEDIDO**

**No bloquea. Nunca condicionado a un booleano, nunca bifurcando entre «rápido bloquea» y «lento devuelve asa»: una firma, un comportamiento.**

**Evidencia:** `ffmpeg_convert(… "webm")` sobre un clip de **5 segundos** superó los **900 s** del timeout del cliente. El modelo recibió `TimeoutError` **y la conversión había terminado bien**: en disco quedó un WebM VP9 válido de 559 046 B con la duración y la geometría exactas. **El trabajo estaba hecho y el modelo no podía saberlo**; un agente reintentaría y repetiría cómputo ya realizado.

Es el modo de fallo que el patrón de asa resuelve — **pero solo si el asa se entrega al empezar, no al terminar**. Con un `convert()` bloqueante, FileX hereda este fallo tal cual. Y la bifurcación tampoco vale: **no se puede saber de antemano**, como demuestra que un clip de 5 s superase los 900 s.

### 5.3 Restricción de versión del SDK: **`mcp>=2.0.0`** — **MEDIDO**

- **Tasks (SEP-1686) fue ELIMINADO de la especificación** — el propio SDK lo avisa. Existió en `1.23.0`-`1.29.0` y funcionaba entero; ya no está. **Así que el `job_id` hay que construirlo entero:** `job_status` / `job_result` / `job_cancel`, con el vocabulario de estado de SEP-1686 (`working`/`completed`/`failed`/`cancelled`), un intervalo de sondeo sugerido por el servidor (~1.000 ms para conversiones) y un TTL.
- **El estado del trabajo se persiste en disco**, no en memoria de la sesión. El fallo de origen es que **el trabajo sobrevivió a quien lo esperaba**: si el `job_id` solo vive en el proceso del servidor MCP, una caída o una reconexión reproducen exactamente el fallo que se quería arreglar. Un JSON por trabajo en el directorio de estado sirve además a la CLI, al watcher y a la API: **los cuatro frentes ven el mismo trabajo.**
- **`job_cancel` mata el árbol de procesos**, no solo marca el estado.
- **`mcp 2.0.0` negocia el protocolo `2026-07-28`** — hay **tres** eras en juego (2024-11-05, 2025-11-25, 2026-07-28), no dos. **La incompatibilidad es asimétrica:** un servidor 2.0.0 habla con clientes 1.8.1 y 1.29.0; **un servidor 1.8.x muere ante un cliente 2.0.0** (caída de proceso, no error de protocolo).
- **Los tres precios de fijar `>=2.0.0`, para que consten:** `mimeType`→`mime_type`, `isError`→`is_error`, `inputSchema`→`input_schema` (migración mecánica pero total); `ctx.meta` ya no trae `progressToken` y **el patrón viejo falla en silencio**; y el cuerpo de una herramienta que pida roots **se ejecuta dos veces** por llamada, así que hay que escribirlas idempotentes hasta esa línea.
- ~~**PENDIENTE:** medir `mcp 2.0.0` contra clientes reales.~~ **MEDIDO el 21/08/2026 (`bench/mcp-cabos-sueltos.md` §1). La restricción se mantiene, y el resultado quita urgencia a media sección:**

#### Lo que negocia el cliente real, y por qué cambia las prioridades — MEDIDO

Un servidor sobre `mcp 2.0.0` habló **sin fricción** con **Claude Code 2.1.238** (cero errores, cero avisos de deprecación). Pero lo que se negoció **no es la era moderna**:

```json
{"protocolo_negociado": "2025-11-25",
 "client_capabilities": {"elicitation": {}, "roots": {"list_changed": true}},
 "client_params": {"client_info": {"name": "claude-code", "version": "2.1.238"}}}
```

- **Claude Code negocia `2025-11-25`, no `2026-07-28`** — va **una era por detrás** del `LATEST_PROTOCOL_VERSION` del SDK de Python.
- **Consecuencia 1: `session.list_roots()` funciona.** El `NoBackChannelError` de `bench/sdk-mcp-capacidades.md` §2.3 es real, pero **hoy no se dispara con este cliente**.
- **Consecuencia 2: `Resolve(ListRoots)` usa la vía clásica**, no `InputRequiredResult`. **El cuerpo de la herramienta NO se ejecuta dos veces con este cliente.** La regla de idempotencia **sigue siendo necesaria** —el cliente se actualizará— **pero no es urgente**.
- **El cliente declara `roots` con `listChanged: true` y `elicitation: {}`** (no `sampling`), **manda un root** —el directorio del proyecto— y **manda `progress_token` en cada llamada**, más una extensión propia `claudecode/toolUseId`. El canal de progreso está disponible sin pedirlo.

> **La recomendación queda reforzada, no debilitada: construir sobre `mcp>=2.0.0` es lo correcto precisamente porque negocia hacia abajo.** FileX se escribe una vez y funciona en las tres eras. **Lo que hay que quitar del plan es la urgencia**: el código de `Resolve(ListRoots)` hay que escribirlo, pero el camino que hoy se ejercita es el clásico.

**Un detalle operativo de distribución, MEDIDO y con coste humano:** al añadir un servidor a la `.mcp.json` del proyecto, `claude mcp list` responde `⏸ Pending approval (run 'claude' to approve)`. **Cualquier cambio en la `.mcp.json` vuelve a dejar el servidor pendiente, y la aprobación es interactiva.** Un `filex init` que escriba la `.mcp.json` **no deja el servidor conectado**: hace falta un paso humano, y conviene decirlo en la documentación de instalación en vez de que lo descubra el usuario.

Detalle completo en `bench/sdk-mcp-capacidades.md` §3.6 y §5.2, y **la prueba contra el cliente real en `bench/mcp-cabos-sueltos.md` §1**.

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
9. **Un verificador escrito literalmente desde la especificación da un 17 % de falsos positivos.** La primera versión del prototipo dio **9-10 falsos positivos sobre 53 salidas correctas**: tolerancia de ±10 ms imposible para códecs de trama (una trama de MP3 dura 26,1 ms), AVIF con techo de 12 bits contado como degradación, `magick identify %x` devolviendo **píxeles por centímetro** para PNG, el bitrate tratado como contrato en vez de como petición, el desfase de una fila entre CSV y JSON… **Las ~85 líneas de excepciones no son un refinamiento posterior: son parte del contrato**, y ninguna se deduce de §4.2. *(Y una perla: `"aac".lstrip("a_")` devuelve `"c"` — `lstrip` opera sobre un conjunto de caracteres.)*
10. **Rasterizar un PDF a ppp fijos es un error de medición, no un parámetro cómodo.** El arnés de la fase 2 de OCR rasterizaba todo a 200 ppp; `escaneado_d2/d3.pdf` llevan imágenes de **100 ppp nativos**. Ese ×2 de interpolación **produjo tres cifras de CER que parecían un límite de los motores y no lo eran** (PaddleOCR en d3: 75,9 % a 200 ppp, **2,5 % a 100**). Cualquier etapa que rasterice debe leer los ppp de la fuente. Ver `bench/gpu-fase2.md` (aviso de cabecera) y `bench/ocrmypdf.md` §3.4.
    **Matiz MEDIDO el 21/08 (`bench/ocr-ppp-nativos.md` §4), y es importante para no sobrecorregir:** el artefacto **no afecta a los cuatro motores por igual**. En **d2 vale cero** para PaddleOCR y EasyOCR (el 43,0 % de EasyOCR es un fallo real), y en **d3 es de un solo motor**: los **+73,4 puntos son todos de PaddleOCR**, mientras que para RapidOCR (**−11,4**) y Docling+RapidOCR torch (**−17,7**) la cifra vieja de 200 ppp era **su mejor resultado**. **«A ppp nativos siempre es mejor» es falso como regla general**; lo que es cierto es que siempre es **más rápido** (×1,48 a ×3,13) y **más barato en VRAM** (hasta 6 851 MiB menos), y más preciso **con el motor que resuelve el caso**.
11. **`realpath` es un vector de DoS.** Una ruta de ~6 000 componentes cuesta **5-16 s**, y `realpath(strict=False)` sigue cadenas de enlaces sin límite. Topes léxicos **antes** de resolver: regla R17 de §4.6.
12. **Un subproceso hereda tu `stdin`.** ffmpeg sin `-y` sobre la tubería JSON-RPC cuelga la sesión MCP entera, para siempre. Regla §5.1.
13. **Un testigo de ruido monohilo es ciego a la contención multinúcleo.** El testigo del proyecto —un bucle determinista de Python antes y después de cada tanda— **etiquetó `limpia` una tanda que salió ×6,8 sobre el mismo control del informe anterior** (V6 `framemd5`: **879 ms frente a 129 ms**). Con 12 núcleos, un bucle monohilo **cabe en un núcleo libre y no se entera**, mientras las sondas externas van varias veces más lentas. **Hacen falta dos testigos: el monohilo mide la DERIVA dentro de la tanda; uno de lanzamiento de proceso mide el NIVEL de carga de la máquina.** Ver `CLAUDE.md` §3 y `bench/verificador-ghostscript.md` §4. *(Calibración en reposo que sale gratis: `ffprobe -version` 26,5–26,8 ms; **`gswin64c --version` 121,7 ms** — Ghostscript tarda 122 ms en cargar sus 27,7 MB de DLL antes de mirar el fichero, y ese número es el que hace justa la comparación con los motores de GPU.)*
14. **Un catálogo de aristas sin el `build` como dimensión miente en alguna máquina.** `svg→png` con `magick` es **real en Windows y nominal (rc=1) en el Debian del contenedor**; `epub→pdf` es **real con Calibre y nominal con LibreOffice**; `png→ico` es **real por ffmpeg y nominal por ImageMagick**. **La arista mínima viable es `(origen, destino, motor, parametrización, build)`** (`bench/aristas-nominales.md` §9.2). **Confirmado desde otro carril el 21/08: el `build` decide 19 de las 33 semiaristas de salida muertas de ffmpeg** —codificadores no compilados— **y la `parametrización` otras 8** (`bench/invocacion-aristas.md` §3.2).
15. **El lock de GPU del proyecto no es de máquina.** `gpu_acquire`/`gpu_release` usan un fichero **dentro de `bench/`**: excluye a otros agentes de FileX y **no ve otra sesión en el mismo equipo**. Una prueba de VRAM en `D:\Work\research\ASR` ocupando **11 754 de 12 288 MiB** dejó una tanda **12 minutos sin procesar una sola imagen** (`bench/ppp-y-normalizacion.md` §1.3). **Si la GPU va lenta y el lock está libre, mira los PID.** Que pase a ser de máquina es **PENDIENTE**.
16. **El testigo de ruido necesita su propio tope.** Con dos agentes en paralelo, `ffprobe -version` llegó a **×94,6** del reposo y a **agotar un timeout de 60 s**, tumbando una tanda entera. **Un testigo que puede tumbar la medición no es un testigo:** tope de 20 s, devolviendo el tope y marcando `SUCIA` (`bench/contrato-quinto-punto.md` §9). **Y las cifras absolutas de tandas distintas no son comparables:** la misma suite de fidelidad sobre los mismos ficheros dio 46 332 ms en una sesión y **70 693 ms** en otra.
17. **Este ImageMagick es Q16-HDRI y escribe los crudos a 16 bits/canal.** Releer un `.rgb` con `-depth 8` **no falla**: consume la mitad del fichero, entrega **la geometría exacta pedida** y **píxeles basura**, y **pasa los cuatro puntos del contrato** (`bench/invocacion-aristas.md` §4.1). Deriva la profundidad de **bytes ÷ píxeles** y elige por **RMSE**. Y **compara contra la referencia IDEAL DEGRADADA, no contra el original en color**: `gray`, `graya` y `mono` dan RMSE 0,35–0,42 contra el original y **exactamente 0** contra su referencia correcta.

---

## 7. Plan de construcción

### Hito 1 — Registro, grafo y CLI — **HECHO el 22/08/2026**

> **Estado, criterio por criterio. Tres de cuatro se demuestran contra los motores reales; el cuarto NO se puede demostrar en esta máquina y se dice.**
>
> | Criterio | Estado |
> |---|---|
> | Convierte un fichero de **cada categoría** del corpus | ✅ `alpha.png→webp`, `patologico_2pistas.mkv→mp4`, `tipico.flac→mp3`, `tipico_texto.pdf→png`. Los cuatro con contrato, tres de ellos **6/6** |
> | Un motor cuyo binario falta **se auto-excluye y se informa** | ✅ `filex motores` lista los presentes con su versión **sondeada en ejecución** y los ausentes por su capacidad |
> | Cuando **no hay camino, explica por qué** | ✅ tres motivos distintos: nadie lee el origen, nadie escribe el destino, o el destino solo se escribe desde formatos inalcanzables — **nombrándolos** |
> | Resuelve 2 saltos **y explica por qué rechaza un camino que rasteriza** | 🟡 **los 2 saltos, sí** (`pdf→png→webp`, contrato 6/6 en los dos). **El rechazo comparado, NO se puede demostrar aquí:** con ffmpeg, ImageMagick y Ghostscript **no existe ningún par de formatos donde compitan un camino que conserva el texto y otro que lo rasteriza**, porque ninguno de los tres escribe un formato con texto desde otro formato con texto salvo `pdf→pdf`. Es la misma limitación que midió `bench/fidelidad-caminos.md` §1.4. **El mecanismo está implementado y probado con un grafo sintético** (`pruebas/test_hito1.py::ElegirBien`); **la prueba de integración necesita el motor documental del hito 5** |
>
> **Lo que sí se demuestra hoy contra un competidor:** `patologico_2pistas.mkv` tiene **dos pistas de audio** y la salida tiene **dos**. ConvertX y SnapOtter entregan **una** y declaran éxito. Es `-map 0` explícito, y es el motivo de que esté en las reglas.
>
> **Y una autocorrección del propio hito, encontrada al probar:** la penalización por pérdida estaba **en la arista** («origen con pérdida y destino con pérdida») y hacía que el grafo prefiriera `mkv→flac→mp3` sobre `mkv→mp3` — un salto más, un intermedio enorme y **exactamente la misma codificación con pérdida al final**. Va por **camino**: se cuentan los saltos que ESCRIBEN con pérdida y se perdona el primero. Con prueba de regresión.
>
> **Deuda declarada:** (1) `bench/scripts/verificador.py` se **importa** desde `bench/` en vez de vivir en `filex/` — moverlo ahora rompería las citas `fichero:línea` de doce informes y del patrón oro, así que es trabajo del hito 3; (2) las aristas `sin_sondear` son 132 de 156: el sondeo real de capacidades por arista está **pendiente**, y hasta entonces cuestan +2,0 para no adelantar nunca a una medida; (3) `Ghostscript.orden` escribe **un solo fichero** y un PDF de varias páginas necesita `%d`, que es una salida multifichero y **el patrón oro no tiene ni una** (C22).

**Qué:** portar el registro de transmute, construir el grafo dirigido con coste por arista, y una CLI `filex entrada.x salida.y` con autodetección de camino. Motores: **ffmpeg e ImageMagick** (75 % de la cobertura de formatos).

**Aceptación:**
- Convierte al menos un fichero de cada categoría del corpus.
- **Resuelve `docx→webp` en 2 saltos** —el único de los tres ejemplos originales que es alcanzable en esta máquina— **y explica por qué rechaza un camino que rasteriza** cuando el destino admite texto. Lo segundo es lo que demuestra de verdad la tesis: alcanzar es fácil, elegir bien no.
- Un motor cuyo binario falta se auto-excluye y la CLI lo informa, en lugar de fallar.
- Cuando no hay camino, explica **por qué**.

> **Por qué se cambió este criterio — MEDIDO (`bench/fidelidad-caminos.md` §1.4).** Exigía «al menos una conversión de 2 saltos: `epub→png`, `docx→webp` o `tex→docx`». **Dos de los tres son inalcanzables aquí, y eso es información útil, no un fracaso:**
> - **`epub→png` y `epub→docx` mueren en la arista `epub→pdf`**: Gotenberg declara `.epub` entre sus extensiones **pero LibreOffice no tiene filtro de importación de EPUB** — solo lo exporta. HTTP 500 con **tres** EPUB distintos, incluidos los de los corpus de transmute y docling.
> - **`tex→docx` es inalcanzable sin Pandoc ni XeLaTeX**, y ninguno está instalado.
>
> **De los tres criterios se cumplía uno.** Eran, además, los ejemplos estrella con que `HUECOS.md` §2 y `analysis/00-matriz-formatos.md` justificaban el grafo: la lección es que **una arista declarada por el catálogo de un motor no es una arista** (ver también `txt→png`, `pdf→txt` y `mp4→pdf`, refutadas por ejecución).

> ### Y ese criterio hay que revisarlo otra vez — MEDIDO el 21/08 (`bench/aristas-nominales.md` §8.1)
>
> **`epub→pdf` NO es una arista muerta del grafo: es un fallo de selección de motor.**
>
> | Vía | Resultado |
> |---|---|
> | **LibreOffice** dentro de `filex-convertx` (`soffice --headless --convert-to pdf`) | **`rc=1`, sin salida** — el fallo se reproduce con **otro build y otro sistema operativo**, así que no era de Gotenberg |
> | **Calibre** dentro de `filex-convertx` (`ebook-convert entrada.epub c_epub.pdf`) | **`rc=0`, PDF de 26 817 B, 565 caracteres, centinela `FILEXSENTINELA7743` y tabla `AX-1` intactos**, 7 045 ms |
>
> **LibreOffice exporta EPUB y no lo importa. Calibre sí, y ConvertX tiene adaptador de Calibre** (`calibre.ts`, 26 entradas / 20 salidas). **Luego `epub→png` y `epub→docx` en dos saltos SON alcanzables**, y lo que falla es la elección de motor — el bug conocido de `main.ts:213-229`, que es justamente lo que el grafo con coste por arista arregla por construcción.
>
> **Criterio de aceptación revisado del hito 1, en consecuencia:**
> - **Resuelve `docx→webp` en 2 saltos** *(se mantiene)* **y explica por qué rechaza un camino que rasteriza** cuando el destino admite texto *(se mantiene: es lo que demuestra la tesis)*.
> - **Nuevo, y es el que discrimina de verdad: resuelve `epub→pdf` eligiendo Calibre y NO LibreOffice, y dice por qué.** Es el caso donde la arista existe, un motor la declara y no la cumple, y otro sí. **Requiere el contenedor `filex-convertx` levantado**, y por tanto se cumple en cuanto exista el hito 5 o un adaptador de Calibre.
> - `tex→docx` **sigue inalcanzable** en Windows sin Pandoc ni XeLaTeX; **dentro del contenedor sí** (Pandoc + xelatex están: `md→docx`, `docx→md`, `html→docx`, `docx→pdf` dieron **8/8 `rc=0`**).

**Objetivo mejor, y ya no hace falta esperar al sidecar de OCR — MEDIDO (`bench/verificador-ghostscript.md` §5.6):** *resuelve `pdf escaneado → docx` conservando el texto*. **Alcanzable hoy, sin GPU, en 3 de los 4 documentos del corpus, con 0,0 % de CER y en 438–1 255 ms.**

| Documento | 1 salto: `docxwrite` directo | 2 saltos: `pdfocr8` → `docxwrite` | CER |
|---|---:|---:|---:|
| `patologico_escaneado` | **2 caracteres — DESTRUIDO** | **99 caracteres** | **0,0 %** |
| `escaneado_d1` | **2 — DESTRUIDO** | 102 | **0,0 %** |
| `escaneado_d2` | **2 — DESTRUIDO** | 102 | **0,0 %** |
| `escaneado_d3` | **2 — DESTRUIDO** | 173 | **119,0 % (ruido)** |

**Con tres precisiones que cambian cómo se usa la respuesta:**

1. **La arista de un salto no existe.** `docxwrite` directo entrega **2 caracteres de basura**, por debajo del umbral P6 — que es exactamente el caso para el que se calibró. **Lo que existe es la de DOS saltos.** El criterio se cumple **si y solo si el grafo sabe INSERTAR el paso de OCR**, que es justo lo que `bench/fidelidad-caminos.md` §6 proponía demostrar.
2. **`escaneado_d3` no se resuelve por esta vía.** La arista de reparación en CPU cubre el caso normal, no el degradado.
3. ~~**Y hoy el verificador no sabe distinguir un caso del otro**~~ — **actualizado el 21/08 a las 14:00, y a medias:** **`ocr: true` en el `pedido` está IMPLEMENTADO**, así que P5 ya invierte la exigencia y P9 sube de `aviso` a `fallo`. **Pero `P9` quedó REFUTADA al validarla** —8,3 % de sensibilidad sobre 32 capas OCR reales— y **se deja en el código marcada como no fiable**. **El sustituto medido es el acuerdo entre dos pasadas de OCR con idiomas distintos: 16/16 sin error, con banda vacía de 0,19 puntos entre 0,700 y 0,887.** Su precio es **una segunda pasada de OCR** (240–1 100 ms), lo que lo pone en el **grupo C** y solo para la arista de reparación. **Con eso, la arista pasa a ser verificable — pero con un coste que el camino caliente no paga.** Ver §4.2 y `HUECOS.md` §5.

**Coste de distribución que va con esto:** **Ghostscript trae el motor de OCR pero no los datos de idioma.** Para la vía **nativa** de Windows, FileX tendría que distribuir **2–4 MB por idioma** (`tessdata`/`tessdata_fast`, Apache-2.0) y fijar `TESSDATA_PREFIX` **en el entorno del proceso hijo**. *(El `spa.traineddata` de esta máquina existe por casualidad: lo instaló PDFgear.)* **Para la vía de CONTENEDOR eso ya no hace falta — MEDIDO** (`bench/invocacion-aristas.md` §9): **ocho líneas de Dockerfile, 28,1 s y +50 MB (+0,9 %)** añaden `qpdf 12.4.0` y `Tesseract 5.5.0` **con `spa` incluido**, y con ello **`qpdf` resuelve 7 de 7 operaciones** y se cierran los dos últimos casos `no_evaluable` de `referencia.json`. **El coste de integración real de los siete era dos motores, 50 MB y 28 segundos.**

> **Y un contraste que hay que conocer antes de elegir el motor de OCR de esta arista — MEDIDO:** **el Tesseract 5.5.0 externo falla en `escaneado_d3` devolviendo un fichero de 0 BYTES, mientras el embebido en Ghostscript falla en el mismo documento ALUCINANDO al 165,8 %.** Mismo motor nominal, **dos modos de fallo opuestos según el envoltorio**; la diferencia tiene que estar en el preprocesado de cada uno. **Es material directo para la heurística de degradación severa: un motor que devuelve 0 bytes y otro que devuelve más texto que la referencia son la misma señal vista desde dos lados. PENDIENTE** de aislar la causa. *(Y `escaneado_d2` refuta la regla de ppp para Tesseract con n=1: **0,00 % a 150 ppp frente a 32,10 % a sus 100 nativos** — a este motor sobremuestrear le es obligatorio, no tolerable. Es la evidencia externa que sostiene el `k` por motor de §4.5.)*

### Hito 2 — NVENC con sondeo y degradación

**Aceptación:** `hevc_nvenc` se usa por defecto cuando el destino es HEVC; `av1_nvenc` se sondea, falla, y degrada a `libsvtav1` **sin intervención**. El desvío de bitrate queda registrado en los metadatos de salida.

### Hito 3 — Contrato de verificación

**Qué:** verificación post-conversión de firma, flujos y propiedades. **Antes que MCP**: sin esto, todo lo anterior puede mentir.

**Aceptación:** reproducir los tres fallos de los competidores contra FileX y que **los tres se detecten**: entregar un PNG con extensión `.avif`, perder una pista de audio, y degradar 16 bits a 8. **Más dos que el prototipo ya atrapa y el criterio original no pedía:** un **redimensionado no solicitado** (punto 4 del contrato) y un **fichero de 0 bytes entregado como éxito**. Y **cero falsos positivos sobre las 53 salidas del patrón oro** — que es la parte cara (§4.2, trampa 9 de §6).

> **Tres añadidos al criterio, MEDIDOS el 21/08 a las 14:00 (`bench/contrato-quinto-punto.md`):**
>
> 1. **El punto 5 tiene que correr DENTRO de la conversión, y el criterio debe exigirlo.** Es el primero que **no es verificable a posteriori**: sin censo, **49 de las 53 salidas bajan de `ok` a `ok_parcial`**. Un verificador que se ejecute «después» no puede aprobar este punto, y **hace bien en no aprobarlo**.
> 2. **El patrón oro es un test FLOJO para el punto 5, porque no contiene ni una salida multifichero.** El «0 falsos positivos» se apoya en cuatro casos fabricados a propósito (HLS, dos secuencias `%d`, y el DASH que sí debe fallar). **Ampliar `referencia.json` con una salida HLS y una secuencia `%d` cerraría el hueco. PENDIENTE.**
> 3. **Y el criterio debería incluir el caso de `resvg`, que ahora sí se atrapa:** I9 discrimina **6 de 6** con margen binario (0,00 % de tinta frente a 18–24 %). **Pero es grupo C, no contrato** —cuesta 32 ms en el mejor caso y **2 454 ms sobre 1,8 Mpx**—, así que **entra en la suite de regresión, nunca en el camino caliente**.

### Hito 4 — Capa MCP

**Aceptación:** **añadir un motor no toca la capa MCP** —aparece como un valor más en los `enum` generados desde el registro, **no como una herramienta nueva** (§4.4)—; el catálogo de las cuatro herramientas **cabe en ≤1.200 tokens**, medido con `tiktoken`; las respuestas devuelven ruta y metadatos y **caben en ≤200 tokens salvo `inspect`**; una conversión larga devuelve **`job_id` al empezar** (§5.2); un error de motor llega al modelo como mensaje accionable que **enumera las alternativas válidas**, nunca como `stderr` crudo; y una ruta fuera de la lista blanca se rechaza **con el mismo mensaje y la misma latencia** que una que no existe.

### Hito 5 — Gotenberg para ofimática

**Aceptación:** `docx/xlsx/pptx/odt → pdf` vía contenedor, con las 132 extensiones importadas y filtradas. Degrada con un mensaje claro si el contenedor no está levantado.

### Hito 6 — Sidecar de IA

**Qué:** proceso Python persistente con registro LRU por VRAM y TTL. faster-whisper (`distil` ≤30 s, `large-v3` por encima) y Docling con RapidOCR en `backend="torch"`.

**Aceptación:** los modelos se descargan por inactividad y el pico de VRAM no supera los ~8,7 GB con dos modelos residentes más NVENC. El OCR del PDF escaneado del corpus se recupera con distancia de edición 0.

> **Aviso de VRAM medido:** **PaddleOCR picó a 12 025 de 12 288 MiB** con imágenes a 600 ppp — a 263 MiB de agotar la tarjeta. **Y EasyOCR llega a 11 877 MiB con imágenes a solo 300 ppp, la mitad de resolución, sobre un documento de una página** (`bench/ocr-ppp-nativos.md` §7.2). **Sobremuestrear consume la VRAM que el presupuesto del sidecar no tiene**, además de empeorar la precisión (regla de ppp en §5, presupuesto por motor **y por resolución** en §4.5, trampa 10 en §6).
>
> **Y el criterio de aceptación de este hito hay que leerlo con la tabla canónica delante:** «el OCR del PDF escaneado del corpus se recupera con distancia de edición 0» **ya se cumple hoy** en `patologico_escaneado`, `d1` y `d2` con Docling+RapidOCR torch (0,0 % de CER en las ocho resoluciones). **Lo que no se cumple es d3**, y solo PaddleOCR lo resuelve (2,5 %, **2 caracteres sobre 79**). El corpus, dicho por su propio informe, **ya no mide dificultad: mide selección de motor** — ver `HUECOS.md` §5.

> ### Lo que este hito cambia tras el 21/08 — MEDIDO, y son tres cosas
>
> 1. **La GPU deja de ser un requisito para el OCR.** Con la normalización del detector corregida (§4.5), **RapidOCR ONNX con PP-OCRv6 small cubre el corpus entero**: `0,00 / 0,00 / 0,00 / 3,80 / 18,62 %` sobre patológico, d1, d2, d3 y `escaneado_d4`. **Gana a PaddleOCR en cuatro de las cinco filas, arranca en 3,7 s en vez de 18,4 y en CPU cuesta 0,32–1,18 s por página.** *(Y eso, no la hipótesis de los ppp, es lo que cambia el hito: la hipótesis «CPU a nativos ≈ GPU a 200 ppp» solo se cumple en d3 (×1,05) y casi en d2 (×1,37); **falla en d1 (×2,26)**.)*
> 2. **Hay una segunda vía sin tarjeta, y es la más barata de todas para el caso normal:** el **Tesseract embebido en Ghostscript** da **0,0 % de CER en patológico, d1 y d2 a ppp nativos con `spa`**, con **VRAM 0** y **carga en frío de 122 ms frente a 3,4–17,3 s** de los motores de GPU. **Fracasa en d3 alucinando (165,8 %)** — un modo de fallo distinto del de los motores GPU, que devuelven poco texto. **Para una CLI que convierte un fichero y termina, la carga en frío ES el coste**, y ahí la diferencia es de **28× a 142×** a favor de la CPU.
> 3. **El criterio de aceptación necesita un caso nuevo**, porque el viejo ya se cumple: **`escaneado_d4` existe** (200 ppp nativos, castellano acentuado, cuatro tamaños de letra) y ningún motor baja del **18,62 %**. **Ese es el margen de mejora que el hito 6 tiene que mover**, y es la primera vez que el proyecto tiene una cifra que no sea 0,0 % ni un interruptor.
>
> ### Y lo que cambia a las 14:00, que afecta al presupuesto de este hito
>
> 1. **El presupuesto de VRAM tiene que llevar el `k` del motor dentro, no solo la resolución.** Con **una sola página**, barrer hasta 400 ppp llevó a **PaddleOCR a 11 942** y a **EasyOCR a 12 037 de 12 288 MiB, sin dar error** — a 346 y 251 MiB de agotar la tarjeta. **RapidOCR corregido se queda en 4 439 MiB y su curva es plana por encima de 233 ppp por construcción** (recorta a 2 000 px). **Es el único de los tres con un techo de VRAM acotado por el propio motor, y esa es su segunda ventaja real.**
> 2. **La ruta recomendada gana una condición:** RapidOCR ONNX con PP-OCRv6 small **y la normalización corregida** sigue siendo la elección — **con 0 regresiones sobre 15 documentos, incluidas cuatro rasterizaciones del patrón oro** —, **pero la corrección NO se puede aplicar al resto de la familia**: empeora 12 de 42 celdas del cribado. **Va como tabla por checkpoint** (§4.5).
> 3. **El registro LRU tiene que llevar `k` por motor además de la resolución**, porque la resolución que cada motor pide para el mismo documento **ya no es la misma**.

> **Presupuesto de VRAM sobre la familia d4, a ppp nativos (200-240) — MEDIDO:** Docling+RapidOCR torch **+1 484 MiB** · RapidOCR ONNX **+2 565** · PaddleOCR **+2 708** · EasyOCR **+4 430**, con pico absoluto de 7 337 MiB. **Nada se acerca al peor caso de 11 877 MiB, y la razón es exactamente la que R1 predice: aquí no se sobremuestrea nada. Aplicar la regla de ppp es lo que hace predecible el presupuesto.** *(Aviso de comparabilidad del propio informe: 7 imágenes de 200-240 ppp frente a las 40 de 75-300 ppp de `ocr-ppp-nativos.md`; solo la columna «coste propio» es comparable entre motores.)*

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
| `pdf/escaneado_d1/d2/d3.pdf` | Degradación progresiva (150→100 ppp, 3-5°, JPEG q60→q25). **d2 y d3 son de 100 ppp nativos: rasterizarlos a más los destruye** (trampa 10) |
| **`pdf/escaneado_d4.pdf`** (canónico) **+ `d4a`, `d4b`, `d4c`, `d4e`, `d4f`** | **Añadidos el 21/08 — `bench/corpus-d4.md`, con `corpus/pdf/MANIFIESTO-d4.md`.** **200 ppp nativos** (240 en `d4f`), **castellano con tildes**, **cuatro tamaños de letra en la misma página** (24 / 13 / 11 / **7 pt**) y **610 caracteres de referencia**. Es el único documento del corpus que **mide margen de mejora** en vez de selección de motor |
| `pdf/tipico_texto.pdf` | Con capa de texto: contraste para decidir OCR frente a extracción |

**La familia `d4`, y para qué sirve cada variante — MEDIDO:**

| Fichero | ppp | PaddleOCR | Docling+Rapid | RapidOCR | EasyOCR | Para qué |
|---|---:|---:|---:|---:|---:|---|
| `escaneado_d4c` | 200 | 0,67 | 22,99 | 15,60 | 15,10 | el escalón anterior; caso intermedio |
| **`escaneado_d4`** | **200** | **19,30** | **36,91** | **41,78** | **61,41** | **el canónico.** Tres motores en la banda 15–60 % y 17,6 puntos entre el 1.º y el 2.º |
| `escaneado_d4e` | 200 | 70,97 | 88,59 | 92,45 | 73,32 | **cota superior**: los cuatro fallan. Sirve para comprobar que una heurística de «degradación severa» dispara |
| `escaneado_d4f` | 240 | 0,67 | 22,15 | 6,04 | 17,95 | mismos parámetros de degradación con **40 % más de resolución**: solo compra ventaja a los motores pequeños |

**Dos cosas del diseño de `d4` que hay que saber antes de generar otro corpus:**

- **La referencia de 610 caracteres cuantiza el CER a 0,16 puntos por carácter, frente a los 1,27 de los 79 caracteres de d1-d3.** **Con 79 caracteres no puede haber gradiente aunque el documento lo tenga** — parte del «interruptor» de d3 era un artefacto de la escala.
- **El generador fija `magick -seed 20260821`** (sin ella `+noise Gaussian` es aleatorio y el corpus no es reproducible), y aun así **el `sha256` del PDF cambia entre ejecuciones**: ImageMagick estampa un `/CreationDate` y **no honra `SOURCE_DATE_EPOCH`**. El JPEG intermedio **sí** es reproducible bit a bit. Documentado en `MANIFIESTO-d4.md` §3.

**Y una trampa nueva del corpus, medida:** **quitar ruido EMPEORA el resultado.** Con ruido gaussiano 0,35 en vez de 0,65, PaddleOCR pasa de 19,30 % a **36,24 %**, y el fichero pesa la mitad: **el ruido actúa como tramado y obliga al JPEG a q=24 a conservar detalle que si no colapsa en bloques planos.**

**Patrón oro:** `bench/salidas-referencia/referencia.json` — 53 salidas caracterizadas, **46 reglas de regresión**, 39 órdenes exactas reproducibles, 17 pérdidas catalogadas. Úsalo como suite de regresión.

**Seis trampas de diseño de pruebas, ya identificadas:**

1. **El "alfa trivial"**: `tipico.png` declara canal alfa pero es enteramente opaco. La regla solo debe exigir conservación si `min(alfa) < 1,0`.
2. **Menor tamaño ≠ mejor conversión**: el GIF con paleta genérica pesa un 35 % *menos* que el bueno.
3. **Opus fuerza 48 kHz** y convierte 8,000 s en 8,0065 s: toda tolerancia por debajo de ±10 ms da falsos fallos.
4. **`txtwrite` emite 1–3 caracteres de basura** en PDF sin texto: el umbral de "conserva texto" debe ser ≥10, no >0.
5. **Y ese umbral no protege contra una alucinación de OCR — MEDIDO** (`bench/verificador-ghostscript.md` §5.8). **75 caracteres de ruido puro lo superan siete veces** y el verificador declara `OK`. Son **dos fallos distintos** y el proyecto solo tenía medido el primero. ~~La señal que los separa —longitud media de token ≥3,0 y menos del 50 % de tokens de una letra— está calibrada sobre 5 puntos.~~ **VALIDADA Y REFUTADA el 21/08 a las 14:00** (`bench/contrato-quinto-punto.md` §6): **8,3 % de sensibilidad sobre 32 capas OCR reales y 36 % de falsos positivos sobre 14 capas legítimas.** **Los 5 puntos de calibración eran el único sitio donde funcionaba.** Falla porque supone que alucinar produce **ruido corto**, y a resoluciones altas Ghostscript alucina **palabras largas y plausibles** —longitud media 4,4 a 5,6, por encima de la del texto legítimo del corpus— y a veces **7 130 caracteres de invención**. **Sustituto medido, 16/16 sin error: el acuerdo entre dos pasadas de OCR con idiomas distintos** (bueno ≥0,887, ruido ≤0,700, umbral 0,80). Cuesta **una segunda pasada de OCR**: es grupo C.
6. **Una regla puede ser correcta y su SONDA estar rota, y eso no lo ve nadie.** `_gs_texto` devolvía vacío **6 de 430 veces por tubería y 0 de 430 por fichero temporal, al mismo coste** — y contaba 107 caracteres en vez de 105 por la traducción de fin de línea. De esa sonda cuelgan **P2 (severidad `fallo`, compara `sha256`), P5, P6 y P9**. **Es la tercera vez que este proyecto mide que la sonda no es la verdad; la novedad es que el defecto era del propio verificador.**

**Arnés de medición:** `bench/lib/harness.sh` — `gpu_acquire` / `gpu_release` (lock exclusivo), `measure` (mediana con etiqueta limpia/SUCIA), `peak_vram`. **Y desde el 21/08, DOS testigos de ruido**: el monohilo mide la **deriva** dentro de la tanda, el de lanzamiento de proceso mide el **nivel** de carga de la máquina. **El primero solo es ciego a la contención multinúcleo** — trampa 13 de §6, `CLAUDE.md` §3.

---

## 9. Documentos de referencia

| Ruta | Cuándo consultarlo |
|---|---|
| `ANALISIS-COMPLETO.md` | El análisis entero: 22 repos, 21 tablas comparativas |
| `informe-filex.html` | Versión navegable del informe |
| `analysis/transmute.md` | Antes de portar el registro |
| `analysis/00-sidecar-protocolo.md` | Antes de construir el sidecar (425 líneas de detalle) |
| `analysis/00-hueco-multisalto.md` | Antes de implementar el grafo |
| **`RESULTADOS-MCP.md`** | **Antes de la capa MCP (hito 4).** Resultados medidos de los 6 repos de `mcp-refs/`: el caso binario, el coste real de los catálogos, y el origen de las reglas de confinamiento de §4.6 |
| **`bench/coste-verificacion.md`** | **Antes del hito 3.** El coste medido del contrato, el cuarto punto, y las ~85 líneas de excepciones que evitan el 17 % de falsos positivos |
| **`bench/fidelidad-caminos.md`** | **Antes de implementar el grafo.** 69 caminos ejecutados, la fidelidad real del multi-salto y la función de coste propuesta |
| **`bench/ocr-ppp-nativos.md`** | **La tabla canónica de CER** (sustituye a `gpu-fase2.md` §5), `OcrOptions.scale`, y la VRAM por motor **y por resolución**. ⚠️ **Su regla de ppp (§9, R1) está SUPERADA por `bench/ppp-y-normalizacion.md`**: el techo ×1,4 que propone quedó refutado, igual que el absoluto que lo sustituyó |
| **`bench/ocrmypdf.md`** | El artefacto de ppp, el descarte de OCRmyPDF y la matriz ppp × deskew. *(Su §3.4 dice que docling con `backend="torch"` cae a PP-OCRv4: es inexacto, corre PP-OCRv6 small — `ocr-ppp-nativos.md` §6.)* |
| **`bench/verificador-fidelidad.md`** | **Antes del hito 3, junto con `coste-verificacion.md`.** `min(alfa)` en proceso, las 11 reglas de fidelidad, y la separación en tres grupos con su coste |
| **`bench/saturacion-herramientas.md`** | **Antes del hito 4.** 540 ejecuciones: el catálogo grande no degrada la elección, el catálogo se paga ×2,0–2,6 por petición, y **la falta de cobertura sí produce fallos silenciosos** |
| **`bench/mcp-cabos-sueltos.md`** | **Antes del hito 4 y de tocar el confinamiento.** Qué ve de verdad el cliente real, el patrón condicional de roots, el A/B del deadlock y la ventana TOCTOU medida |
| **`bench/sdk-mcp-capacidades.md`** | **Antes de fijar la dependencia `mcp`.** Roots, la desaparición de Tasks y la forma del `job_id` |
| **`bench/aristas-nominales.md`** | **Antes de poblar el grafo (hito 1) y de tocar el confinamiento.** El **50,5 %** de aristas nominales con su método y su IC, la tasa por estrato (factor 18) y el **3,0 % del estrato PDF**; el caso de `resvg` que **ningún punto del contrato atrapa**; los motores que escriben **fuera del destino**; y los 5 de 7 `no_evaluable` cerrados dentro del contenedor |
| **`bench/corpus-d4.md`** | **Antes de tocar el OCR, junto con `ocr-ppp-nativos.md`.** El corpus `d4`; la **causa real de la asimetría de PaddleOCR** (la normalización del detector de RapidOCR: 72,2 puntos por seis números); el **techo absoluto de ppp**; y las dos refutaciones CPU/GPU |
| **`bench/verificador-ghostscript.md`** | **Antes del hito 3 y del hito 1.** `min(alfa)` de TIFF/GIF/Adam7, V2 y su coste (+60,6 %), el **OCR sin GPU** de Ghostscript, la **arista de reparación de dos saltos**, `P9` contra la alucinación *(refutada después)*, y el **segundo testigo de ruido** |
| **`bench/ppp-y-normalizacion.md`** | **Antes de tocar el OCR — sustituye a `ocr-ppp-nativos.md` §9 y a `corpus-d4.md` §8 en todo lo que sea la regla de ppp.** El barrido de 17 puntos, **la refutación de las tres unidades candidatas**, el **`k` por motor** y dónde vive, el tope interno de cada detector sondeado en ejecución, la **validación de la normalización por checkpoint** (con sus 12 empeoramientos) y el **parche B11 propuesto, no aplicado** |
| **`bench/invocacion-aristas.md`** | **Antes de poblar el grafo (hito 1) y antes de prometer cobertura.** El **18,8 % del 50,5 % que es invocación**, con sus tres categorías; los crudos y sus **cuatro** datos externos; `imagen → pdf` con densidad ajustada a página; el **censo completo de Ghostscript y Gotenberg al 3,1 %**; y el **coste de integración de `qpdf` y `tesseract`: 8 líneas, 28,1 s, +50 MB** |
| **`bench/contrato-quinto-punto.md`** | **Antes del hito 3, y es el más directo de los tres.** El **quinto punto implementado y medido** (+11,0 % con R18, ×8,6 sin él), la **regla I9** con su coste real, **la familia de cinco miembros y el que sigue descubierto**, **`P9` refutada con su sustituto**, el **interruptor de V2** y **el fallo de la propia sonda `_gs_texto`** |
| `bench/mcp-refs-confinamiento.md` §8 · `bench/confinamiento-multimedia.md` §6 · `bench/aristas-nominales.md` §5.2 | La evidencia de cada una de las **18** reglas de §4.6 |
| `analysis/00-mcp-componentes.md` | Al elegir qué pieza portar: 90 componentes → veredicto, con `fichero:línea` |
| `analysis/00-mcp-patrones.md` | Antes de la capa MCP — **al día al 21/08/2026 (03:30): reglas 1, 2, 4 y 5 corregidas y dos reglas nuevas (6 y 7)** |
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
