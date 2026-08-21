# Fidelidad de los caminos multi-salto — la medida que faltaba

**Qué contesta este documento.** `HUECOS.md` §2 y `ANALISIS-COMPLETO.md` §1 dejan abierto el único hueco que el proyecto se reprocha a sí mismo:

> «**Qué fracción de los 447 398 caminos produce una salida aceptable. Nunca se midió.** El 2,93× es alcanzabilidad, no fidelidad.»

Aquí se mide. Se reconstruye el grafo con **los motores que existen en esta máquina**, se ejecutan **69 caminos reales** sobre el corpus, se clasifica cada salida contra las reglas de regresión y las 17 pérdidas catalogadas de `bench/salidas-referencia/referencia.json`, y se propone una función de coste calibrada con esas medidas.

Toda afirmación va marcada **[MEDIDO]** o **[PENDIENTE]**.

- Datos crudos: `bench/salidas-fidelidad/clasificado.json` (69 caminos, cada paso con orden exacta, rc, ms y caracterización completa de la salida)
- Instrumentos: `bench/salidas-fidelidad/_grafo.py`, `_entradas.py`, `_sonda.py`, `_caminos.py`, `_clasifica.py` (reproducibles)
- Salidas conservadas: `bench/salidas-fidelidad/salidas/` (2,6 MB tras podar; ver §7)

---

## 0. Correcciones del entorno encontradas por el camino

Dos cosas cambiaron respecto al enunciado. Una es un **cambio de estado real que provoqué yo** (relanzar Docker); la otra es un **matiz técnico** que al principio interpreté mal y que dejo verificado con el binario en la mano. Se documentan porque cambian lo que es alcanzable.

| Afirmación de partida | Lo que había | Consecuencia |
|---|---|---|
| «Contenedores levantados: Gotenberg 8.36 en `localhost:3200`…» | **Docker Desktop estaba parado** al empezar. `docker ps` fallaba con `npipe:////./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified` y `localhost:3200` rechazaba la conexión | **CAMBIO DE ESTADO QUE PROVOQUÉ YO:** relancé Docker Desktop (`Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"`). Los cinco contenedores (`filex-gotenberg8`, `filex-convertx`, `filex-snapotter`, `-pg`, `-redis`) volvieron solos y Gotenberg respondió `{"status":"up"}` con chromium y libreoffice arriba. **Quedan levantados.** No cerré nada. **[MEDIDO]** |
| «**NO instalado:** … Tesseract …» | **`PLAN-ORQUESTADOR.md:40` es correcto y no hay que tocarlo: no hay Tesseract invocable.** El motor de OCR que usé viene **compilado dentro de Ghostscript**. Ver §0.1 | Los dispositivos `ocr`, `hocr` y `pdfocr24` de Ghostscript 10.07 funcionan **sin binario externo**, aunque necesitan datos de idioma. Esto abre *aristas de reparación* que el grafo no contemplaba. **[MEDIDO]** |
| Ghostscript entendido como «PDF → PDF/imagen» | Ghostscript 10.07 declara además **`docxwrite`** (PDF → DOCX), `xpswrite`, `psdrgb`, `pclm` y los tres de OCR | Hay una arista `pdf → docx` nativa, sin LibreOffice ni pandoc. **[MEDIDO]** |

### 0.1 De dónde sale el OCR: está dentro de Ghostscript, no en el sistema

Al medir escribí que «Tesseract sí está instalado». **Era una inferencia a partir de un directorio, no una comprobación, y estaba mal planteada.** Verificado ahora con el binario delante:

| Comprobación | Resultado |
|---|---|
| `where.exe tesseract` | **no lo encuentra**: Tesseract **no está en el PATH** y por tanto **no es invocable** |
| `$env:TESSDATA_PREFIX`, y las variantes `Machine` y `User` | **vacías**: la variable **no está definida** en el sistema |
| `strings gsdll64.dll` (27,7 MB, Ghostscript 10.07) | **122 apariciones de `tesseract`, 9 de `leptonica`**, con rutas de compilación `ghostpdl-10.07.0\tesseract\src\api\baseapi.cpp`, `hocrrenderer.cpp`, `ccmain\control.cpp` |
| `find "C:\Program Files\gs" -iname "*traineddata*"` | **cero resultados**: Ghostscript trae el motor, **no los datos de idioma** |
| `gswin64c -sDEVICE=ocr` **sin** `TESSDATA_PREFIX` | **falla**: `Error opening data file ./eng.traineddata` → `Tesseract couldn't load any languages!` |
| `.traineddata` presentes en la máquina | `C:\Program Files\Tesseract-OCR\tessdata` (`eng`, `osd`) y `C:\Program Files\PDFgear\tessdata` (16 idiomas). Ninguno de los dos lo puso este proyecto |

**Lo que de verdad pasa. [MEDIDO]** Ghostscript 10.x **empaqueta Tesseract y Leptonica como bibliotecas compiladas dentro de `gsdll64.dll`**. Por eso `gswin64c -h` lista `ocr`, `hocr`, `pdfocr8/24/32`, y por eso mis aristas de reparación funcionan: **no invocan ningún binario `tesseract`**, invocan un dispositivo de salida de Ghostscript. Existe un `tesseract.exe` en el disco (`C:\Program Files\Tesseract-OCR\tesseract.exe`, 86 152 B, instalación ajena a este proyecto), pero **no está en el PATH y no interviene en nada de lo que ejecuté**.

**Consecuencias, en orden de importancia:**

1. **`PLAN-ORQUESTADOR.md:40` no necesita corrección.** «NO instalado: … Tesseract…» es cierto en el único sentido que importa: no hay binario invocable. **Escribir lo contrario induciría a error a quien intente usarlo desde otra herramienta** — en particular **OCRmyPDF, que necesita el binario `tesseract` de verdad y no puede aprovechar el que Ghostscript lleva compilado dentro**. Mi redacción anterior contradecía ese supuesto y era incorrecta.
2. **El hallazgo bien formulado es más fuerte que el que escribí:** FileX tiene una vía de OCR **sin instalar ningún motor nativo más**, porque viene dentro de un binario que el proyecto ya usa. Encaja con la restricción de no instalar motores a mano en Windows.
3. **Pero no es «OCR gratis y sin nada», y conviene no venderlo así.** El motor viene; **los datos de idioma no**. En una máquina limpia, `-sDEVICE=ocr` fallaría igual que falló aquí sin `TESSDATA_PREFIX`. Que funcione en esta máquina es **un accidente**: dos programas ajenos (Tesseract-OCR y PDFgear) dejaron `.traineddata` en el disco. Para que FileX lo use de forma reproducible hay que **distribuir el `eng.traineddata`** (Apache-2.0; ~4 MB en `tessdata_fast`, ~15 MB en `tessdata_best`) y **fijar `TESSDATA_PREFIX` desde el propio orquestador**, que es exactamente lo que hace mi ejecutor (`_caminos.py`: `ENV_GS = dict(os.environ, TESSDATA_PREFIX=...)`).

**Limitaciones del OCR embebido, medidas. [MEDIDO]**

- El idioma se elige con **`-sOCRLanguage=`**, no con `-dOCRLanguage=` (esto último devuelve `Invalid value for option …, use -sNAME= to define string constants`).
- **El idioma disponible depende por completo del `tessdata` externo al que apuntes, no de Ghostscript.** Con el `tessdata` de Tesseract-OCR (solo `eng` y `osd`), `-sOCRLanguage=deu` falla con `Error opening data file … deu.traineddata`. Apuntando al de PDFgear (16 idiomas), `-sOCRLanguage=spa` funciona y devuelve los 82 bytes correctos del PDF escaneado.
- **Todo lo que este informe mide de OCR está hecho en `eng`**, sobre un escaneado de prueba cuyo texto castellano no lleva tildes. **[PENDIENTE]** la calidad del OCR embebido en castellano con tildes, su comportamiento sobre los tres escaneados degradados (`escaneado_d1/d2/d3.pdf`), y si `tessdata_fast` frente a `tessdata_best` mueve la similitud del 99,0 % medida en I1.

---

---

## 1. El grafo real de esta máquina

### 1.1 Reproducción de la cifra publicada

Primero se reprodujo el cálculo original para poder compararlo. Se parsearon los `properties.from` / `properties.to` de los 20 adaptadores de ConvertX y se hizo BFS por capas.

| | Publicado en `00-matriz-formatos.md` | Reproducido aquí | Desvío |
|---|---:|---:|---:|
| Pares a 1 salto | 152 584 | **152 478** | −0,07 % |
| Pares a ≤3 saltos | 447 398 | **446 006** | −0,31 % |
| Multiplicador | 2,93× | **2,93×** | — |

**[MEDIDO]** La cifra del proyecto es correcta y reproducible. El desvío se explica por los bucles `formato → mismo formato`: contándolos todos salen 152 849 aristas, sin contarlos 152 478, y la cifra publicada (152 584) cae en medio. No es un error material.

### 1.2 El mismo grafo, solo con los motores instalados

**Qué hay en el PATH, comprobado con `Get-Command` y no heredado del enunciado. [MEDIDO]** Presentes: `ffmpeg` (`D:\utils\ffmpeg\bin`), `magick` (`C:\Program Files\ImageMagick-7.1.2-Q16-HDRI`), `gswin64c` (`C:\Program Files\gs\gs10.07.0\bin`), `node`, `go`. Ausentes: `pandoc`, `soffice`, `libreoffice`, `vips`, `qpdf`, `ebook-convert`, `inkscape`, `xelatex`, `tesseract`. Coincide con `PLAN-ORQUESTADOR.md` §2 en los nueve casos.

De los 20 adaptadores de la tabla, en esta máquina existen **dos** (`ffmpeg`, `imagemagick`). Se añaden dos motores que ConvertX no tiene pero esta máquina sí: **Ghostscript** (entradas PDF/PS/EPS; salidas derivadas de su lista real de dispositivos) y **Gotenberg** (LibreOffice con sus 132 extensiones declaradas → PDF; Chromium HTML/Markdown → PDF/PNG/JPEG/WebP). ImageMagick se sondeó con `magick -list format` en vez de fiarse de la tabla: **246 formatos de lectura y 183 de escritura reales** en esta build, frente a los 245/183 declarados por ConvertX — la tabla de ConvertX es fiel aquí. **[MEDIDO]**

| Grafo | Nodos | Aristas dirigidas | 1 salto | ≤2 saltos | ≤3 saltos | Multiplicador |
|---|---:|---:|---:|---:|---:|---:|
| **Declarado** (20 adaptadores) | 1 022 | 152 478 | 152 478 | 388 912 | 446 006 | **2,93×** |
| **Instalado** (ffmpeg, IM, gs, Gotenberg) | 852 | 138 501 | 138 501 | 250 264 | 266 927 | **1,93×** |

**[MEDIDO] El primer trozo de aire: con lo que hay instalado, el multiplicador cae de 2,93× a 1,93×.** Se conserva el 91 % de la cobertura de 1 salto (porque ffmpeg e ImageMagick ya son el 75 % de los formatos) pero solo el **43,8 %** de la ganancia multi-salto (128 426 pares nuevos frente a los 293 528 declarados), porque los saltos intermedios interesantes los daban los motores ausentes (pandoc, calibre, libreoffice nativo, vips, inkscape).

### 1.3 Cuánto de esos caminos nuevos es sustantivo y cuánto es ruido

Los 138 501 → 266 927 significan **128 426 pares nuevos** que solo aparecen a 2-3 saltos. Para separar lo sustantivo del ruido hacen falta dos filtros, y ninguno de los dos es invención mía: los dos salen de código de terceros.

**Filtro 1 — ¿alguien pide ese formato?** Se toma el catálogo por modalidad de SnapOtter (`packages/shared/src/modality.ts`: `IMAGE_INPUTS`, `VIDEO_INPUTS`, `AUDIO_INPUTS`, `SUBTITLE_INPUTS`, `DOCUMENT_INPUTS`, `FILE_INPUTS`), **86 formatos** que un producto real declara como su superficie de entrada. Sirve además de asignación de familia gratis.

**Filtro 2 — ¿el destino puede llevar lo que trae el origen?** `documento → audio` es alcanzable en el grafo y no significa nada: un `.docx` no tiene forma de onda. Se declara plausible una pareja de familias solo si el destino puede representar algo del origen (documento→{documento, imagen, datos}, imagen→{imagen, documento}, datos→{datos, documento, imagen}, vídeo→{vídeo, imagen, audio, documento}, audio→{audio}, subtítulo→{subtítulo, documento, datos}).

| | Pares |
|---|---:|
| Pares nuevos a ≥2 saltos (grafo instalado) | **128 426** |
| …con ambos extremos en el catálogo de 86 formatos pedidos | 1 599 |
| …y además con una pareja de familias plausible | **610** |
| **Fracción del multi-salto que sobrevive a los dos filtros** | **0,48 %** |

**[MEDIDO]** El reparto de los 1 599 «pedidos» enseña por qué hace falta el segundo filtro: `documento→audio` 154, `imagen→audio` 198, `documento→vídeo` 201, `imagen→subtítulo` 54, `audio→documento` 44. Son **947 de 1 599 (59 %) pares semánticamente vacíos** que el grafo alcanza porque ffmpeg declara `png` como demuxer y `mp3`, `srt` y `ass` como muxers.

Y la comparación honesta, midiendo lo mismo a un salto y a varios:

| Sobre los 7 310 pares entre formatos que se piden | Pares |
|---|---:|
| Alcanzables a 1 salto | 3 335 (1 868 plausibles) |
| Alcanzables solo a 2-3 saltos | 1 599 (**610** plausibles) |
| Inalcanzables incluso a 3 saltos | 2 376 |

**[MEDIDO] La ganancia real del multi-salto, medida entre pares que alguien pide y que tienen sentido, es +32,7 %, no +193 %.** Y **820 de esos 1 599 (51 %) tienen PDF como único intermedio posible** — es decir: el multi-salto de esta máquina es, casi entero, *«pásalo por PDF»*.

### 1.4 Aristas nominales: declaradas y refutadas por ejecución

El grafo declara aristas que el binario no cumple. Las que se han ejecutado y refutado:

| Arista | Motor que la declara | Qué pasa al ejecutarla |
|---|---|---|
| `epub → pdf` | Gotenberg (`.epub` está en `Api.Extensions()`) | **HTTP 500**: `LibreOffice failed to convert the document`. Probado con **tres** EPUB distintos (uno propio, `transmute/assets/samples/epub.epub` 886 KB, `docling/tests/data/epub/…` 402 KB). LibreOffice no tiene filtro de importación de EPUB: solo lo exporta. **[MEDIDO]** |
| `txt → png` | ImageMagick (`TXT` figura como `rw+`) | `magick: improper image header … ReadTXTImage/418`. El «TXT» de ImageMagick es su formato de volcado de píxeles, no texto plano. **[MEDIDO]** |
| `pdf → txt` | ImageMagick | Produce un fichero de **159 454 045 bytes** (152 MB) desde un PDF de 3 KB: es la enumeración de los 2,2 millones de píxeles de la página. Técnicamente «un .txt», semánticamente basura. 37,0 s. **[MEDIDO]** |
| `mp4 → pdf` | ImageMagick | **No terminó en 240 s.** Peor: ImageMagick delega el decodificado en `ffmpeg`, y al matar el proceso padre por *timeout* el hijo sobrevivió y mantuvo la tubería abierta, colgando al supervisor. Hubo que matar el árbol a mano. **[MEDIDO]** |

**Consecuencia dura para el diseño:** `epub → png` y `epub → docx`, los ejemplos estrella con los que `00-matriz-formatos.md`, `HUECOS.md` §2 y `PLAN-ORQUESTADOR.md` §7 justifican el grafo, **no son ejecutables en esta máquina**. El primer criterio de aceptación del hito 1 («resuelve al menos una conversión de 2 saltos: `epub→png`, `docx→webp` o `tex→docx`») solo lo pasa **`docx→webp`**; `tex→docx` es directamente inalcanzable en el grafo instalado (no hay pandoc ni xelatex). **[MEDIDO]**

---

## 2. Criterio de muestreo, declarado como sesgo

**69 caminos, 47 de ellos multi-salto (2-4 saltos) y 22 de un salto como control.** El muestreo **no es aleatorio y no pretende serlo**: está deliberadamente cargado hacia los cruces de familia y las rasterizaciones, que es donde se espera la destrucción. Los sesgos, uno por uno:

1. **Sesgo hacia el cruce de familia.** 13 de los 47 multi-salto cruzan familia (documento→imagen, imagen→documento, vídeo→imagen, vídeo→audio, tabular→imagen). En el grafo real esa proporción es mucho menor. **La muestra sobrerrepresenta los casos malos a propósito**, porque el objetivo es caracterizar el fallo, no estimar una media poblacional.
2. **Sesgo del corpus.** Se usan los 20 ficheros de `corpus/`, elegidos en su día por ser patológicos. `patologico_2pistas.mkv` tiene dos pistas de audio con PCM distinto; `alpha.png` tiene alfa no trivial; `patologico_16bit.tif` tiene 16 bits. Un corpus «normal» daría mejores resultados.
3. **Entradas fabricadas.** El corpus no tiene ofimática, así que se generaron a mano y sin dependencias (`zipfile` + XML) `entrada.docx`, `.xlsx`, `.odt`, `.epub`, `.html`, `.md`, `.rtf`, `.csv`, `.txt`, todas con el mismo párrafo centinela y la misma tabla de 4×3 (`bench/salidas-fidelidad/_entradas.py`). Son documentos **mínimos y bien formados**: no llevan estilos, imágenes, fuentes incrustadas ni notas al pie. **Un documento real se degradaría más, no menos.**
4. **Un solo fichero por par.** Cada camino se ejecuta una vez, sobre un fichero. No hay medianas ni repeticiones: los ms de la tabla son orientativos y **no** se han tomado con `bench/lib/harness.sh`, así que **no deben citarse como medida de rendimiento**. Lo que sí es determinista, y es lo que se mide aquí, es la fidelidad.
5. **Los saltos los elijo yo, no Dijkstra.** No existe todavía el orquestador; cada camino es una cadena que yo he escrito a mano imitando la que elegiría un grafo por conectividad pura. Es exactamente la comparación que interesa (conectividad frente a coste), pero conviene decirlo.

Estratos: control imagen→imagen (8), documento→imagen (8), documento→documento (11), imagen→documento (4), vídeo (7), audio (4), «el orden importa» (5), aristas nominales (4), reparación por OCR (4), parametrización del mismo par (6), controles de 1 salto (8).

---

## 3. Tabla por camino

Los ms son de una sola ejecución sobre una máquina con carga: **orientativos, no medidos con arnés**. `im` = ImageMagick, `ff` = ffmpeg, `gs` = Ghostscript, `gt-lo` / `gt-html` / `gt-md` / `gt-shot` = rutas de Gotenberg.

| Id | Estrato | Cadena | Motores | Saltos | ms | Categoria | Que se perdio exactamente |
|---|---|---|---|---:|---:|---|---|
| A1 | control-imagen | `png → webp → png` | im + im | 2 | 1243 | **DEGRADADO** | profundidad 16→8 bits y png admite 16: la pierde el salto intermedio a webp (regla I4, evitable con otro intermedio) |
| A2 | control-imagen | `png → jpg → png` | im + im | 2 | 895 | **DEGRADADO** | profundidad 16→8 bits y png admite 16: la pierde el salto intermedio a jpg (regla I4) |
| A3 | control-imagen | `tif → png → tif` | im + im | 2 | 13426 | **INTEGRO** | sin perdida detectable en las sondas aplicadas |
| A4 | control-imagen | `tif → webp → png` | im + im | 2 | 19078 | **DEGRADADO** | profundidad 16→8 bits y png admite 16: la pierde el salto intermedio a webp (regla I4) |
| A5 | control-imagen | `png → webp → png` (alpha) | im + im | 2 | 95 | **DEGRADADO** | grafismo: 210 colores → 1943 (regla I8, el codificador inventa tonos); alfa no trivial conservado (min 0,000) |
| A6 | control-imagen | `png → jpg → png` (alpha) | im + im | 2 | 89 | **DESTRUIDO** | grafismo: 210 → 3135 colores; ALFA DESTRUIDO: alfa no trivial (min 0,000) y png lo admite (regla I2) |
| A7 | control-imagen | `png → avif → png → webp` | im + im + im | 3 | 4353 | **PERDIDA INEVITABLE** | profundidad 16→8 bits, inevitable en webp (regla I5) |
| A8 | control-imagen | `png → bmp → gif → png` | im + im + im | 3 | 6253 | **DEGRADADO** | profundidad 16→8 en el paso a bmp; paso intermedio por GIF: paleta de ≤256 colores por fotograma, irreversible |
| B1 | doc-a-imagen | `epub → pdf → png` | gt-lo | 2 | 2346 | **FALLO** | paso 1 (gt-lo→pdf) HTTP 500: LibreOffice no importa EPUB |
| B2 | doc-a-imagen | `docx → pdf → webp` | gt-lo + im | 2 | 5611 | **PERDIDA INEVITABLE** | capa de texto perdida: webp no puede representarla |
| B3 | doc-a-imagen | `html → pdf → png` | gt-html + gs | 2 | 13841 | **PERDIDA INEVITABLE** | capa de texto perdida: png no puede representarla |
| B4 | doc-a-imagen | `md → pdf → jpg` | gt-md + gs | 2 | 3737 | **PERDIDA INEVITABLE** | capa de texto perdida: jpg no puede representarla |
| B5 | doc-a-imagen | `csv → pdf → png` | gt-lo + gs | 2 | 12374 | **PERDIDA INEVITABLE** | capa de texto perdida: png no puede representarla |
| B6 | doc-a-imagen | `xlsx → pdf → png` | gt-lo + gs | 2 | 3372 | **PERDIDA INEVITABLE** | capa de texto perdida: png no puede representarla |
| B7 | doc-a-imagen | `rtf → pdf → png` | gt-lo + im | 2 | 2515 | **PERDIDA INEVITABLE** | capa de texto perdida: png no puede representarla |
| B8 | doc-a-imagen | `odt → pdf → jpg` | gt-lo + gs | 2 | 993 | **PERDIDA INEVITABLE** | capa de texto perdida: jpg no puede representarla |
| C1 | doc-a-doc | `epub → pdf → txt` | gt-lo | 2 | 25564 | **FALLO** | paso 1 (gt-lo→pdf) HTTP 500 |
| C2 | doc-a-doc | `docx → pdf → docx` | gt-lo + gs | 2 | 995 | **DEGRADADO** | texto alterado: similitud 87,3 %; la tabla sale en orden de COLUMNAS, no de filas |
| C3 | doc-a-doc | `docx → pdf → png → pdf` | gt-lo + gs + im | 3 | 1052 | **DESTRUIDO** | TEXTO DESTRUIDO: 380 caracteres → 0, y pdf SÍ admite capa de texto |
| C4 | doc-a-doc | `docx → pdf → png → pdf → txt` | gt-lo + gs + im + gs | 4 | 12801 | **FALLO** | el destino txt solo sirve para llevar texto y sale vacío (0 bytes): no hay conversión |
| C5 | doc-a-doc | `xlsx → pdf → docx` | gt-lo + gs | 2 | 1015 | **DEGRADADO** | texto alterado: similitud 80,8 %; tabla en orden de COLUMNAS |
| C6 | doc-a-doc | `pdf → png → pdf` | gs + im | 2 | 509 | **DESTRUIDO** | TEXTO DESTRUIDO: 104 caracteres → 0, y pdf SÍ admite capa de texto |
| C7 | doc-a-doc | `pdf → pdf → docx` | gs + gs | 2 | 6437 | **INTEGRO** | texto conservado (120 caracteres, similitud 100,0 %) |
| C8 | doc-a-doc | `html → png → pdf` | gt-shot + im | 2 | 6414 | **DESTRUIDO** | TEXTO DESTRUIDO: 392 caracteres → 0, y pdf SÍ admite capa de texto |
| C9 | doc-a-doc | `epub → pdf → docx` | gt-lo | 2 | 5188 | **FALLO** | paso 1 (gt-lo→pdf) HTTP 500 |
| D1 | imagen-a-doc | `png → pdf → txt` | im + gs | 2 | 1721 | **FALLO** | txt vacío (0 bytes). Confirma la trampa 4 al revés: aquí `txtwrite` ni siquiera emite la basura de 1-3 caracteres |
| D2 | imagen-a-doc | `tif → pdf → png` | im + gs | 2 | 22635 | **DEGRADADO** | geometría 4000×3000 → 8333×6250 (regla I1, efecto de la regla P7); profundidad 16→8 bits |
| D3 | imagen-a-doc | `jpg → pdf → pdf` | im + gs | 2 | 1041 | **INTEGRO** | sin pérdida detectable |
| D4 | imagen-a-doc | `png → pdf → png` (alpha) | im + gs | 2 | 619 | **DESTRUIDO** | geometría 200×200 → 417×417; ALFA DESTRUIDO: alfa no trivial y png lo admite |
| E1 | video-a-imagen | `mp4 → gif → png` | ff + im | 2 | 1270 | **DEGRADADO** | paso intermedio por GIF: paleta de ≤256 colores, irreversible |
| E2 | video-a-imagen | `mp4 → png → webp` | ff + im | 2 | 1212 | **PERDIDA INEVITABLE** | audio perdido: webp no lo admite |
| E3 | video-a-video | `mkv → mp4 → mkv` (`-c copy`) | ff + ff | 2 | 271 | **DESTRUIDO** | PISTAS DESTRUIDAS: 2 → 1 y mkv admite varias (pérdida 12 del catálogo) |
| E4 | video-a-video | `mkv → mp4 → mkv` (recodifica) | ff + ff | 2 | 8206 | **DESTRUIDO** | PISTAS DESTRUIDAS: 2 → 1 |
| E5 | video-a-video | `mkv → webm → mp4` | ff + ff | 2 | 25198 | **DESTRUIDO** | PISTAS DESTRUIDAS: 2 → 1; frecuencia 44 100 → 48 000 Hz arrastrada desde Opus |
| E6 | video-a-video | `mp4 → gif → mp4` | ff + ff | 2 | 1273 | **DEGRADADO** | paso intermedio por GIF: paleta irreversible |
| E7 | video-a-audio | `mp4 → mp3 → wav` | ff + ff | 2 | 336 | **DEGRADADO** | PCM `d0bd638ebac7` → `7e78a82b153c`: generación con pérdida evitable (ver J1) |
| F1 | audio | `flac → wav → mp3` | ff + ff | 2 | 278 | **PERDIDA INEVITABLE** | destino mp3 es con pérdida: recodificar es inevitable |
| F2 | audio | `flac → opus → wav` | ff + ff | 2 | 609 | **DEGRADADO** | PCM distinto con destino sin pérdida; frecuencia 44 100 → 48 000 Hz |
| F3 | audio | `mp3 → flac → wav` | ff + ff | 2 | 196 | **DEGRADADO** | PCM `f5ddaa6410d8` → `984b4619d1c3`: ffmpeg infló el flac a 24 bits |
| F4 | audio | `wav → mp3 → flac` | ff + ff | 2 | 260 | **DEGRADADO** | PCM `b1cdfb164f23` → `4d267a0c553e`: generación con pérdida sobre destino sin pérdida (ver J2) |
| G1 | orden | `tif → png` | im | 1 | 6769 | **INTEGRO** | sin pérdida (16 bits conservados) |
| G2 | orden | `tif → jpg → png` | im + im | 2 | 19181 | **DEGRADADO** | mismo destino que G1 vía JPEG: profundidad 16→8 |
| G3 | orden | `pdf → txt` (txtwrite) | gs | 1 | 186 | **INTEGRO** | texto conservado (104 caracteres, similitud 100,0 %) |
| G4 | orden | `pdf → png → pdf → txt` | gs + im + gs | 3 | 1493 | **FALLO** | mismo destino que G3 vía PNG: 0 bytes |
| G5 | orden | `mkv → mp4` (`-map 0 -c copy`) | ff | 1 | 94 | **INTEGRO** | 2 pistas conservadas |
| H1 | nominal | `mp4 → pdf` | im | 1 | 145884 | **FALLO** | no terminó en 240 s; el delegado ffmpeg sobrevivió al *kill* |
| H2 | nominal | `txt → png` | im | 1 | 100 | **FALLO** | `improper image header … ReadTXTImage/418` |
| H3 | nominal | `png → webp` | ff | 1 | 2284 | **PERDIDA INEVITABLE** | ffmpeg como conversor de imagen funciona; 16→8 bits inevitable en webp |
| H4 | nominal | `pdf → txt` | im | 1 | 37005 | **DESTRUIDO** | 152 MB de volcado de píxeles desde un PDF de 3 KB |
| I1 | reparacion | `pdf → png → pdf → txt` (OCR) | gs + im + gs | 3 | 2143 | **INTEGRO** | texto **recuperado** tras rasterizar: similitud 99,0 % |
| I2 | reparacion | `docx → pdf → png → pdf` (+OCR) | gt-lo + gs + im + gs | 4 | 3318 | **DEGRADADO** | texto recuperado al 87,8 % sobre un documento totalmente rasterizado |
| I3 | parametro | `png → webp` (lossy q80) | im | 1 | 38 | **DEGRADADO** | grafismo de 1 color → 2 colores; 94 bytes |
| I4 | parametro | `png → webp` (lossless) | im | 1 | 65 | **INTEGRO** | 1 color, **42 bytes**: más pequeño *y* exacto |
| I5 | parametro | `png → pdf` (sin densidad) | im | 1 | 444 | **DEGRADADO** | caja de página de 677 mm de ancho (regla P7) |
| I6 | parametro | `png → pdf` (`-density 150`) | im | 1 | 397 | **INTEGRO** | caja de página correcta |
| I7 | parametro | `png → jpg` (por defecto) | im | 1 | 1445 | **DEGRADADO** | aplanado sobre negro; 210 → 3135 colores |
| I8 | parametro | `png → jpg` (`-background white`) | im | 1 | 90 | **DEGRADADO** | aplanado sobre blanco; 210 → 3067 colores |
| J1 | control-1salto | `mp4 → wav` | ff | 1 | 2548 | **INTEGRO** | PCM idéntico `d0bd638ebac7` |
| J2 | control-1salto | `wav → flac` | ff | 1 | 167 | **INTEGRO** | PCM idéntico `b1cdfb164f23` |
| J3 | control-1salto | `docx → pdf` | gt-lo | 1 | 799 | **INTEGRO** | texto conservado 380 caracteres, similitud 100,0 % |
| J4 | control-1salto | `pdf → pdf` | gs | 1 | 278 | **INTEGRO** | texto conservado, similitud 100,0 % |
| J5 | control-1salto | `pdf → docx` | gs | 1 | 796 | **INTEGRO** | texto conservado, similitud 100,0 % |
| J6 | doc-a-doc | `xlsx → pdf → txt` | gt-lo + gs | 2 | 3784 | **DEGRADADO** | texto alterado: similitud 92,3 % |
| J7 | doc-a-doc | `csv → pdf → docx` | gt-lo + gs | 2 | 3048 | **DEGRADADO** | similitud 83,2 %; tabla en orden de COLUMNAS |
| J8 | orden | `pdf escaneado → txt` (txtwrite) | gs | 1 | 673 | **FALLO** | 0 bytes: no hay capa de texto que extraer |
| J9 | orden | `pdf escaneado → txt` (**ocr**) | gs | 1 | 804 | **INTEGRO** | 71 caracteres correctos: la misma arista, otro dispositivo |
| J10 | reparacion | `pdf escaneado → docx` | gs | 1 | 589 | **DESTRUIDO** | docx de 9 837 bytes **sin una sola línea** del documento (solo metadatos) |
| J11 | reparacion | `pdf escaneado → pdf(OCR) → docx` | gs + gs | 2 | 4216 | **INTEGRO** | el camino de 2 saltos **gana** al de 1: el docx sí lleva el texto |
| J12 | control-1salto | `mp4 → gif` | ff | 1 | 1727 | **DEGRADADO** | audio perdido (inevitable en gif); 1920×1080 → 320×180 (pedido) |

### 3.1 Los cuatro hallazgos con más carga

**a) El texto puede sobrevivir *corrompido*, y un centinela no lo detecta. [MEDIDO]** En C2 (`docx → pdf → docx`) el párrafo llega, pero `docxwrite` se come las ligaduras: *fidelidad* → *fdelidad*, *multisalto* → *multsalto*, *fichero* → *fchero*, *cantidad* → *cantdad*, y `AX-1` → `AX1`. Similitud carácter a carácter: **87,3 %**. Mi centinela `FILEXSENTINELA7743` sobrevivió intacto (no contiene «fi», «ti» ni guiones) y habría dado un falso aprobado. **La comprobación correcta es de cobertura de caracteres, no de presencia de una marca.**

**b) La tabla se convierte en una lista de columnas. [MEDIDO]** En C2, C5 y J7 el texto de la tabla sale en orden de columnas (`codigo AX1 BX2 CX3 cantdad 128 256 512 unidad kg kg kg`) en vez de por filas. La estructura tabular —que es *toda* la información de una tabla— desaparece aunque no falte ni un carácter. Es el caso «tabla convertida en imagen» del enunciado, pero peor, porque el resultado *parece* texto correcto.

**c) `-c copy` no basta para conservar las pistas. [MEDIDO]** E3 usó `ffmpeg -i in.mkv -c copy out.mp4` y aun así perdió la segunda pista de audio: la selección automática de flujos de ffmpeg actúa **antes** que el códec. Solo `-map 0` la salva (G5). Refuerza el hallazgo 1.1 de `referencia-nativa.md` y lo endurece: la restricción de la arista MKV→MP4 no es «no recodifiques», es `-map 0`.

**d) La rasterización tiene marcha atrás, y cuesta un 1 % de los caracteres. [MEDIDO]** I1 (`pdf → png → pdf → txt` con `-sDEVICE=ocr`) recupera **99,0 %** del texto de un PDF que había sido reducido a píxeles; el mismo camino sin OCR (G4) devuelve 0 bytes. En I2 la recuperación sobre un documento ofimático completo baja al **87,8 %**. El OCR comete errores tipo `ColC` → `GolG`. Quien hace ese trabajo es el **dispositivo `ocr` de Ghostscript, con Tesseract compilado dentro de `gsdll64.dll`** (§0.1): no hay ninguna llamada a un binario externo en ninguno de los caminos de este informe. Es decir: **«destruido» no siempre es terminal, pero repararlo cuesta y hay que saber cuánto.**

---

## 4. El reparto

**Aviso previo: esto es una muestra sesgada a propósito hacia los casos malos (§2), no un censo.** Los porcentajes describen esta muestra; no son una estimación de la población de 128 426 caminos.

| Categoría | Multi-salto (n=47) | 1 salto (n=22) | Total (n=69) |
|---|---:|---:|---:|
| **ÍNTEGRO** | 5 — **10,6 %** | 11 — 50,0 % | 16 — 23,2 % |
| **PÉRDIDA INEVITABLE** | 10 — **21,3 %** | 1 — 4,5 % | 11 — 15,9 % |
| **DEGRADADO** | 18 — **38,3 %** | 5 — 22,7 % | 23 — 33,3 % |
| **DESTRUIDO** | 8 — **17,0 %** | 2 — 9,1 % | 10 — 14,5 % |
| **FALLO** | 6 — **12,8 %** | 3 — 13,6 % | 9 — 13,0 % |

**La respuesta a la pregunta que abría el documento. [MEDIDO]**
Si «aceptable» = ÍNTEGRO + PÉRDIDA INEVITABLE (la salida conserva lo esencial, o lo que falta no cabía en el destino):

> **Multi-salto: 31,9 % aceptable. Un salto: 54,5 % aceptable.**
> **El 29,8 % de los caminos multi-salto (14 de 47) o destruyen el contenido o no producen nada.**

Por número de saltos, sobre esta muestra: 2 saltos → 32,5 % aceptable (13/40); 3 saltos → 40 % (2/5, n muy pequeño); 4 saltos → 0 % (0/2).

Por estrato, lo que más discrimina:

| Estrato | Aceptable | Comentario |
|---|---|---|
| `doc-a-imagen` (8) | 7/8 | Sale bien **por definición**: el destino es una imagen y por tanto perder el texto es inevitable. Ver §6. |
| `doc-a-doc` (11) | 1/11 | El peor estrato con diferencia: 3 FALLO, 3 DESTRUIDO, 4 DEGRADADO |
| `video-a-video` (4) | 0/4 | Las pistas se pierden en todos los casos sin `-map 0` |
| `audio` (4) | 1/4 | Tres cadenas meten una generación con pérdida evitable |
| `control-imagen` (8) | 2/8 | Incluso el control «debería salir bien» sale mal: el intermedio de 8 bits tira la profundidad |
| `reparacion` (4) | 2/4 | El OCR salva caminos que sin él serían DESTRUIDO |

---

## 5. La función de coste propuesta

### 5.1 El error de modelo que hay que evitar primero

Las medidas dicen tres cosas que **rompen el modelo ingenuo de «coste por par de formatos»**:

1. **El coste depende del fichero, no solo del par.** J8 y J9 son la misma arista `pdf → txt` con el mismo motor: uno da 0 bytes y otro el texto correcto. La diferencia no está en los formatos, está en si *ese* PDF tiene capa de texto. **[MEDIDO]**
2. **El coste depende de los parámetros, no solo del motor.** I3/I4 (webp con y sin pérdida: 94 B/2 colores frente a 42 B/1 color), I5/I6 (página de 677 mm frente a 325 mm), I7/I8 (aplanado sobre negro frente a blanco), E3/G5 (`-c copy` frente a `-map 0 -c copy`). En los cuatro pares, la conectividad ve **una** arista. **[MEDIDO]**
3. **El coste depende del destino final, no solo del salto.** Perder el texto al pasar a PNG es inevitable si el usuario pidió PNG (B3-B8), y es destrucción si el usuario pidió PDF (C3, C6, C8). El mismo salto, el mismo motor, la misma pérdida física: distinta categoría. **[MEDIDO]**

Por eso la propuesta **no es una etiqueta de peso en la arista**. Es esto:

> **Nodo del grafo = (formato, vector de capacidades vivas).** Arista = (motor, parametrización). El coste de la arista se evalúa contra el **contrato de la petición**, que se calcula una vez por consulta.

El vector de capacidades es pequeño (texto, estructura tabular, alfa no trivial, nº de pistas, profundidad >8 bits, exactitud de muestra) — media docena de bits — así que el grafo producto sigue siendo diminuto y Dijkstra sigue funcionando sin cambios.

### 5.2 Las tres dimensiones

**Dimensión 1 — Pérdida semántica (S).** Lo que el usuario reconocería como «ya no es mi fichero». Discreta, cara, y evaluada **contra el contrato**:

```
contrato C = capacidades_medidas(fichero_origen)  ∩  capacidades(formato_destino)
```

`capacidades_medidas` se obtiene con las sondas de §3 sobre el fichero real (texto ≥10 caracteres imprimibles — regla P6; alfa con `min(alfa) < 0,999` — regla I2 y trampa 1; `ffprobe` para las pistas). `capacidades(formato)` es una tabla estática de 20 líneas.

| Capacidad destruida (estando en el contrato) | Peso | Calibrado con |
|---|---:|---|
| Capa de texto | **1000** | C3, C6, C8, G4, J10: 380/104/392 → 0 caracteres |
| Estructura tabular | **1000** | C2, C5, J7: la tabla sale en columnas |
| Pistas de audio (por pista perdida) | **1000** | E3, E4, E5: 2 → 1 |
| Alfa no trivial | **300** | A6, D4 |
| Texto que llega alterado | **1000 · (1 − similitud)** | C2 87,3 % → 127; I2 87,8 % → 122; I1 99,0 % → 10; J6 92,3 % → 77 |

Si un salto **añade** una capacidad que el destino admite y que el origen tiene en forma inaccesible (OCR sobre píxeles), no se resta coste: se marca la capacidad como viva en el estado del nodo, y quien paga es el camino que llega sin ella (ver la penalización terminal, §5.4).

**Dimensión 2 — Degradación métrica (D).** Lo que se puede medir con un número y el usuario puede no notar. Aditiva y barata:

| Degradación | Coste | Calibrado con |
|---|---:|---|
| Profundidad de bits perdida siendo el destino capaz (regla I4) | 40 | A1, A2, A4, A8, G2, D2: 16 → 8 bits |
| Geometría alterada sin pedirlo (regla I1) | 40 | D2 (4000×3000 → 8333×6250), D4 (200 → 417) |
| Caja de página absurda por no declarar densidad (regla P7) | 25 | I5: 677 mm frente a los 325 mm de I6 |
| Pérdida de fidelidad con pérdida: `máx(0; 55 − PSNR) · 1,5` | 0…40 | JPEG q85 = 48,7 dB → 9; VP9 crf33 sobre sintético = 29,6 dB → 38 (referencia) |
| Colores inventados sobre grafismo (regla I8) | 30 | I3 (1 → 2 colores) frente a I4 (exacto y más pequeño) |
| Frecuencia de muestreo cambiada | 25 | F2, E5: 44 100 → 48 000 Hz (Opus, trampa 3) |
| Generación con pérdida introducida con destino sin pérdida | 60 | E7, F2, F3, F4: PCM distinto del origen |
| Paleta de ≤256 colores en un intermedio | 60 | A8, E1, E6: paso por GIF |

**Dimensión 3 — Riesgo operativo y coste (T).** Deliberadamente pequeña: **el tiempo nunca debe poder compensar una pérdida.**

| Término | Valor | Calibrado con |
|---|---:|---|
| Tiempo | `log10(1 + ms/100)` → 0…4 | H1: 145 884 ms → 3,2; G5: 94 ms → 0,3 |
| Arista **nominal** (declarada por una tabla, nunca ejecutada con éxito aquí) | **+50** | Toda arista sin una ejecución verificada |
| Arista **refutada** (ejecutada y fallida) | **∞** | `epub→pdf`, `txt→png`, `mp4→pdf` |
| Arista cuyo delegado escapa al *timeout* | **+200** | H1: ffmpeg sobrevive al *kill* de ImageMagick |

**Coste total de la arista:** `c = S + D + T`.

### 5.3 El umbral que hace que «destruido» puntúe peor que «no se puede»

```
UMBRAL_RECHAZO = 500
```

Si el camino más barato cuesta ≥ 500, la respuesta correcta es **«no se puede, y este es el motivo»**, no un fichero. Como cualquier destrucción de una capacidad contratada vale ≥1000, la propiedad que pide `PLAN-ORQUESTADOR.md` §4.1 —*«un camino de 3 saltos que rasteriza y destruye el texto debe puntuar peor que "no se puede"»*— **se cumple por construcción**, no por ajuste fino. Y como las degradaciones métricas suman como mucho ~250 en el peor camino medido, **ninguna acumulación de degradaciones puede cruzar el umbral por accidente**: la separación entre las dos escalas es deliberada.

### 5.4 Penalización terminal

Al llegar al destino, se cobra una vez:

```
penal_final = Σ_{p ∈ K(destino) ∩ recuperable(origen)}  w_p · [la salida no lleva p]
```

donde `recuperable(origen)` incluye lo que el origen tiene aunque sea de forma inaccesible (texto como píxeles en un escaneado). Esto es lo que hace que un camino **más largo** pueda ganar: J11 paga dos saltos y un OCR, pero no paga los 1000 de «docx sin texto» que sí paga J10.

### 5.5 Cuatro pares donde esta función elige distinto que la conectividad

**Ejemplo 1 — `patologico_escaneado.pdf → docx`: gana el camino de 2 saltos. [MEDIDO]**

| Camino | Conectividad | Coste propuesto | Resultado real |
|---|---|---|---|
| `pdf → docx` (`docxwrite`), 1 salto, 589 ms | **elegido** (menos saltos) | S = 1000 (texto recuperable ausente) + T 0,8 = **1000,8** | DOCX de 9 837 B **sin una línea** del documento |
| `pdf → pdf(pdfocr24) → docx`, 2 saltos, 4 216 ms | descartado | S ≈ 0 + D 0 + T 1,6 = **1,6** | DOCX con el texto: `DOCUMENTO ESCANEADO / Texto que solo existe como pixeles / Debe recuperarse con OCR` |

La conectividad pura entrega un documento vacío que parece correcto. La función de coste elige el camino siete veces más lento y es el único que sirve.

**Ejemplo 2 — `pdf escaneado → txt`: misma arista, mismo motor, decisión opuesta. [MEDIDO]**

| Camino | Conectividad | Coste propuesto | Resultado real |
|---|---|---|---|
| `gs -sDEVICE=txtwrite`, 673 ms | indistinguible | S = 1000 + T 0,8 = **1000,8** | **0 bytes** |
| `gs -sDEVICE=ocr`, 804 ms | indistinguible | S ≈ 0 + T 0,9 = **0,9** | 71 caracteres correctos |

Un grafo con coste por par de formatos **no puede expresar esta diferencia**: es la misma arista. Solo un coste evaluado sobre las capacidades medidas del fichero de entrada la ve. Es el argumento más fuerte a favor de nodo = (formato, capacidades).

**Ejemplo 3 — `docx → pdf`: la respuesta correcta es negarse. [MEDIDO]**

| Camino | Conectividad | Coste propuesto | Resultado real |
|---|---|---|---|
| `docx → pdf` (Gotenberg), 1 salto, 799 ms | elegido | S 0 + T 0,9 = **0,9** | texto 380 caracteres, similitud 100 % |
| `docx → pdf → png → pdf`, 3 saltos, 1 052 ms | **alcanzable, y ConvertX lo serviría si el directo faltara** | S = 1000 (texto) + 1000 (tabla) + T 1,0 = **2001** | PDF de 11 818 B con **0 caracteres** |

Si Gotenberg está caído —cosa que pasó durante esta misma sesión— la conectividad degrada silenciosamente al camino de 3 saltos y entrega un PDF que parece un PDF. Con el umbral de 500, FileX responde *«no hay camino que conserve el texto de un DOCX a PDF con los motores disponibles; el único camino alcanzable lo rasteriza»*. Ese mensaje **es** el diferenciador nº 1 (verificación) aplicado al nº 2.

**Ejemplo 4 — `mkv (2 pistas) → mp4`: la conectividad ve una arista donde hay dos. [MEDIDO]**

| Parametrización | Conectividad | Coste propuesto | Resultado real |
|---|---|---|---|
| `ffmpeg -i in.mkv -c copy out.mp4` | **una sola arista `mkv→mp4`** | S = 1000 (una pista perdida) + T 0,4 = **1000,4** | 1 pista de audio |
| `ffmpeg -i in.mkv -map 0 -c copy out.mp4`, 94 ms | ídem | S 0 + T 0,3 = **0,3** | 2 pistas, `framemd5` idéntico |

Este es exactamente el bug de ConvertX (`main.ts:213-229`) generalizado: no es solo que elija mal el motor, es que **el modelo de datos no tiene sitio donde guardar la diferencia entre dos invocaciones del mismo motor**. Modelar la arista como `(motor, parametrización, coste)` lo arregla por construcción.

---

## 6. Veredicto sobre el diferenciador nº 2

`HUECOS.md` §2 sospecha que el número lo sobrevende. **Los datos lo confirman, y con margen.** Con todas las letras:

**El 2,93× es una cifra de marketing. La propina real existe, es pequeña, y es casi entera «pásalo por PDF».**

Lo que sostiene esa frase, todo **[MEDIDO]**:

1. **De 2,93× a 1,93×** en cuanto se exigen motores instalados en vez de tablas declaradas. Un tercio del multiplicador se evapora antes de convertir un solo fichero.
2. **De 128 426 caminos nuevos a 610** (0,48 %) al exigir que ambos extremos sean formatos que un producto real declara pedir y que la pareja de familias tenga sentido. El 59 % de los pares «pedidos» que el grafo gana son cosas como `docx → mp3` e `imagen → srt`.
3. **La ganancia honesta es +32,7 %, no +193 %.** 1 868 pares plausibles a un salto, 610 más a dos o tres.
4. **De los 1 599 pares nuevos entre formatos pedidos, 820 (51 %) tienen PDF como único intermedio posible.** «Grafo de conversión con Dijkstra» describe, en esta máquina, un caso especial resuelto a mano hace años dentro de `transmute/backend/converters/libreoffice_convert.py:333` (*"Image output via PDF intermediary"*).
5. **Ejecutados, solo el 31,9 % de los caminos multi-salto de la muestra da una salida aceptable**, frente al 54,5 % de los de un salto. **Casi uno de cada tres destruye el contenido o no produce nada.**
6. **Los dos ejemplos estrella de la tesis no se pueden ejecutar aquí.** `epub→png` y `epub→docx` mueren en la arista `epub→pdf`, que Gotenberg declara y LibreOffice no implementa. `tex→docx` es inalcanzable. De los tres criterios de aceptación del hito 1, se cumple **uno**.
7. **Y el caso más incómodo:** el estrato que mejor puntúa (`doc-a-imagen`, 7 de 8 aceptables) lo hace porque el destino es una imagen y perder el texto es «inevitable» por definición. Es decir: **el multi-salto funciona mejor justo donde el resultado es menos útil.** `xlsx → pdf → png` es un aprobado formal y una hoja de cálculo que ya no se puede sumar.

### Lo que sí se sostiene, y es lo que hay que construir

La reformulación de `HUECOS.md` §2 —*«lo que se sostiene del grafo es la selección correcta con coste explícito; el multi-salto es la propina, no la tesis»*— sale **reforzada** de esta medición, y ahora con instrumentos:

- Los cuatro ejemplos de §5.5 **no son casos de multi-salto**. Tres de ellos comparan dos invocaciones de un solo salto (J8/J9, E3/G5, I3/I4, I5/I6, I7/I8). El valor está en **elegir bien**, y eso se cobra en el primer salto.
- Las **17 pérdidas catalogadas** de `referencia.json` no son una anécdota: son literalmente la tabla de pesos de §5.2. La distinción *inevitable/fallo del motor* es la función de coste.
- El multi-salto merece existir en el motor —cuesta poco y desbloquea 610 pares reales más las **aristas de reparación** por OCR, que son el hallazgo más útil de este informe— pero **no como titular**. Como consecuencia de tener bien modelado el coste.

**Recomendación concreta para el hito 1:** sustituir el criterio de aceptación «resuelve `epub→png`, `docx→webp` o `tex→docx`» por «**resuelve `pdf escaneado → docx` conservando el texto, y explica por qué rechaza `docx → pdf` cuando el único camino disponible rasteriza**». El primero es alcanzabilidad; el segundo demuestra las dos cosas que el proyecto defiende de verdad. **[PENDIENTE de decisión]**

---

## 7. Qué queda en disco, y qué falta por medir

`bench/salidas-fidelidad/` — **3,0 MB** en total (2,6 MB de salidas) tras podar (se borraron los 18 ficheros de más de 1 MB y los 14 de más de 150 KB; sus medidas están íntegras en `clasificado.json`).

| Ruta | Qué es |
|---|---|
| `clasificado.json` | Los 69 caminos con orden exacta, rc, ms, caracterización de cada paso, categoría y motivos |
| `resultados.json` | Lo mismo sin clasificar (salida cruda del ejecutor) |
| `grafo-resumen.json`, `grafo-popular.json` | Las cifras de §1 |
| `_grafo.py`, `_entradas.py`, `_sonda.py`, `_caminos.py`, `_clasifica.py` | Instrumentos reproducibles |
| `entradas/` | Las 9 entradas fabricadas (28 KB) |
| `salidas/` | 125 salidas conservadas. Las que sostienen un hallazgo: `C2_p2.docx` (ligaduras perdidas), `C5_p2.docx` y `J7_p2.docx` (tabla en columnas), `C3_p3.pdf` y `C6_p2.pdf` (texto a 0), `J8_p1.txt` (0 bytes) frente a `J9_p1.txt` (OCR), `J10_p1.docx` frente a `J11_p2.docx` (el camino largo gana), `I1_p3.txt` e `I2_p4.pdf` (reparación por OCR), `I3_p1.webp` (94 B) frente a `I4_p1.webp` (42 B), `H4_p1.RECORTE.txt` (900 B del volcado de 152 MB) |

### Lo que este informe NO ha medido — **[PENDIENTE]**

1. **Si esas conversiones se piden.** Sigue abierto lo que ya señalaba `HUECOS.md` §2. El catálogo de SnapOtter es un proxy de demanda, no demanda medida.
2. **La tasa de aristas nominales del grafo.** Se han refutado 4 por ejecución. Cuántas de las 138 501 son nominales es desconocido; sondearlas todas es un trabajo de días y sería la medición que de verdad cierra el hueco.
3. **Documentos reales.** Las entradas ofimáticas son mínimas y sin estilos. Con estilos, imágenes incrustadas y fuentes, la similitud de C2/C5/J7 bajaría.
4. **Tiempos con arnés.** Los ms de §3 son de una ejecución con carga. Si el coste T pasa a importar, hay que rehacerlos con `bench/lib/harness.sh` (medianas de n≥9).
5. **Los pesos de §5.2 no están validados contra usuarios.** Están calibrados para que la separación entre destrucción semántica (≥1000) y degradación métrica (≤250) sea inequívoca, y para que el umbral de 500 caiga limpio en medio. Es una elección de diseño defendible, no un resultado experimental.
6. **Dispositivos de Ghostscript sin probar:** `hocr`, `pdfocr8`, `pdfocr32`, `xpswrite`, `psdrgb`, `pclm`. Sí se han ejecutado `ocr` (I1, J9) y `pdfocr24` (I2, J11).
7. **La dependencia de datos de idioma del OCR embebido está medida, su calidad no** (§0.1): todo el OCR de este informe se hizo con `-sOCRLanguage=eng` sobre un escaneado sin tildes.
