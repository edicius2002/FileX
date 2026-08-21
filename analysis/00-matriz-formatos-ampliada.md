# Matriz de formatos ampliada — transmute, SnapOtter y gotenberg frente a ConvertX

Continuación de `00-matriz-formatos.md`. Todas las cifras salen de parsear el código fuente, no los README. Método por motor:

| Repositorio | Qué se parseó |
|---|---|
| transmute | AST de Python sobre `backend/converters/*.py`: atributos de clase `supported_input_formats` / `supported_output_formats` de las 22 clases que heredan de `ConverterInterface`, resolviendo referencias (`video_formats \| audio_formats`, `set(_map.keys())`, `_ALL_FORMATS`). Cero casos irresolubles. |
| SnapOtter | `apps/api/src/lib/file-validation.ts` (`SUPPORTED_INPUT_FORMATS`, `RAW_EXTENSIONS`), `packages/image-engine/src/utils/mime.ts` (`EXT_TO_MIME`), `packages/shared/src/modality.ts` (listas de entrada por modalidad), enums `z.enum([...])` de las 30 rutas de herramienta que declaran formato de salida, y `packages/shared/src/conversion-presets.ts`. |
| gotenberg | `pkg/modules/libreoffice/api/api.go` (`func (a *Api) Extensions()`), rutas `Path: "/forms/..."` de cada módulo y sus `MandatoryPaths`, e implementaciones de `Convert` de cada motor PDF. |
| ConvertX | Re-extracción propia de `properties.from` / `properties.to` para poder cruzar conjuntos concretos (ver salvedad al final). |

Las comparaciones se hacen **tras normalizar alias** con la tabla `core/media_types.py` de transmute (`jpg→jpeg`, `tif→tiff`, `htm→html`, `yml→yaml`, `latex→tex`, `ps→eps`, `mpg→mpeg`, `j2k/j2c/jpc/jpx/jpf→jp2`, `tgz→tar.gz`…). Sin normalizar, las diferencias se inflan con falsos exclusivos.

---

## 1. Cobertura por motor

### transmute — 22 clases conversoras

| Conversor | Clase | Entradas | Salidas | Entradas exclusivas dentro de transmute |
|---|---|---:|---:|---:|
| ffmpeg | `FFmpegConverter` | 34 | 30 | 29 |
| pillow | `PillowConverter` | 37 | 31 | 12 |
| pymupdf | `PyMuPDFConverter` | 26 | 22 | 0 |
| pandas | `PandasConverter` | 23 | 17 | 22 |
| pypandoc | `PyPandocConverter` | 16 | 17 | 13 |
| calibre | `CalibreConverter` | 13 | 9 | 5 |
| inkscape | `VectorConverter` | 10 | 8 | 7 |
| cbz | `CBZConverter` | 9 | 2 | 0 |
| libreoffice | `LibreOfficeConverter` | 9 | 8 | 9 |
| archive | `ArchiveConverter` | 8 | 7 | 5 |
| mesh_render | `MeshRenderConverter` | 6 | 3 | 0 |
| ocrmypdf | `OCRmyPDFConverter` | 6 | 1 | 0 |
| pdf2docx | `PDF2DOCXConverter` | 6 | 1 | 0 |
| pysubs2 | `PySubs2Converter` | 6 | 6 | 6 |
| rename | `RenameConverter` | 6 | 6 | 0 |
| trimesh | `TrimeshConverter` | 6 | 5 | 0 |
| fonttools | `FonttoolsConverter` | 4 | 4 | 4 |
| email | `EmailConverter` | 2 | 10 | 2 |
| drawio | `DrawioConverter` | 1 | 4 | 1 |
| ezdxf | `EzdxfConverter` | 1 | 3 | 1 |
| pkcs7 | `PKCS7Converter` | 1 | 0 | 1 |
| tgs | `TGSConverter` | 1 | 5 | 1 |

**Totales transmute: 164 formatos de entrada únicos, 131 de salida, 166 formatos distintos en total.**

Dos detalles del modelo de datos de transmute que ConvertX no tiene:
- Trata los perfiles de PDF como formatos de primera clase: `pdf/a`, `pdf/e`, `pdf/ua`, `pdf/vt`, `pdf/x` son entradas independientes (y `pdf/a` también salida, producida por `ocrmypdf`). ConvertX solo conoce `pdf`.
- `PKCS7Converter` declara `supported_output_formats = set()` a propósito: el formato de salida de un `.p7m` se descubre al desenvolver la firma. Es el único conversor con salida dinámica y rompe cualquier matriz estática.

### SnapOtter

El README anuncia por paquete, pero **`media-engine` y `doc-engine` no declaran ninguna tabla de formatos**: son envoltorios delgados de ffmpeg / LibreOffice / pandoc / Ghostscript / qpdf / pdfcpu. `media-engine/src/encoders.ts` solo mapea 7 objetivos de códec (`h264, hevc, av1, vp9, aac, opus, mp3`); `doc-engine/src/libreoffice.ts` pasa el string `--convert-to` que le da quien llama. Los formatos reales viven en los enums Zod de `apps/api/src/routes/tools/*.ts` y en `packages/shared/src/modality.ts`.

| Sub-sistema | Entradas | Salidas | Dónde se declara |
|---|---:|---:|---|
| Imagen (gate de la API) | 27 identificadores, uno de ellos `raw` = 23 extensiones RAW → **49 familias** | **17** | `file-validation.ts` / `routes/tools/convert.ts` |
| Imagen (tabla de extensiones, con alias) | 65 | — | `image-engine/src/utils/mime.ts` |
| Vídeo | 15 | 5 (`mp4 mov webm avi mkv`) | `modality.ts` / `convert-video.ts` |
| Audio | 11 | 5 (`mp3 wav ogg flac m4a`) | `modality.ts` / `convert-audio.ts` |
| Subtítulos | 3 (`srt vtt ass`) | 2 (`srt vtt`) | `modality.ts` / `auto-subtitles.ts` |
| Documento | 15 | `docx odt rtf txt` + `pptx odp` + `xlsx ods csv` + `pdf html md` | `modality.ts` / `convert-*.ts`, `epub-convert.ts` |
| Ficheros | 6 (`csv json xml yaml yml zip`) | — | `modality.ts` |

**Totales SnapOtter: 106 formatos de entrada, 46 de salida** (contando extensiones distintas tras normalizar alias). El catálogo de pares nombrados (`CONVERSION_PRESETS`) son **83 conversiones** concretas: 22 formatos de origen, 19 de destino.

### gotenberg

| Módulo | Entradas | Salidas | Nota |
|---|---:|---|---|
| libreoffice | **132 extensiones** (`Api.Extensions()`) | PDF | Única ruta de conversión de formato real |
| chromium | HTML + `.md` + URL | PDF, y capturas `png` / `jpeg` / `webp` | 6 rutas |
| pdfengines | solo `.pdf` (15 rutas, todas `MandatoryPaths([]string{".pdf"})`) | PDF | merge, split, flatten, optimize, convert, metadata, bookmarks, encrypt, embed, watermark, stamp, rotate, factur-x |
| pdfcpu / qpdf / pdftk / exiftool | solo `.pdf` | PDF | Manipulación, no conversión de formato |

**Totales gotenberg: 130 formatos de entrada (normalizados), 4 de salida (`pdf`, `png`, `jpeg`, `webp`).** No es un conversor universal: es un embudo a PDF con 132 bocas.

---

## 2. Lo que cubre transmute y ConvertX NO

**57 formatos de entrada y 37 de salida.** Agrupados:

| Categoría | Entradas que faltan en ConvertX | Salidas que faltan en ConvertX |
|---|---|---|
| Hojas de cálculo | `xls`, `xlsx`, `ods` | `xlsx`, `ods` |
| Presentaciones | `ppt`, `odp`, `pot`, `potx`, `pps`, `ppsx`, `pptm` | `ppt`, `odp` |
| Tabulares / científicos | `parquet`, `feather`, `orc`, `sqlite`, `dta`, `sav`, `xpt`, `fwf`, `jsonl` | `parquet`, `feather`, `orc`, `sqlite`, `jsonl` |
| Configuración | `ini`, `env`, `toon` | `ini`, `env`, `toon` |
| Fuentes tipográficas | `woff`, `woff2` | `ttf`, `otf`, `woff`, `woff2` |
| Archivos comprimidos | `7z`, `rar`, `tar`, `tar.gz`, `tar.bz2`, `tar.xz`, `tar.zst` | los mismos + `zip` |
| Cómic | — | `cbz`, `cbr`, `cb7` |
| Ebook | `azw3`, `kepub` | `kepub` |
| Perfiles PDF | `pdf/a`, `pdf/e`, `pdf/ua`, `pdf/vt`, `pdf/x` | `pdf/a` |
| Correo | `eml` | — |
| Nichos sueltos | `p7m`, `tgs`, `drawio`, `key`, `vsdx`, `cdr`, `cdt`, `adoc`, `mpl` | `mka`, `off` |
| Imagen (Pillow) | `blp`, `dib`, `icns`, `flc`, `fli`, `oga` | `blp`, `dib`, `icns`, `mpo`, `msp` |

### El hallazgo más incómodo: ConvertX no tiene hojas de cálculo

Cruzando adaptador por adaptador:

- **`xlsx`, `xls`, `ods`: cero adaptadores de ConvertX los declaran, ni de entrada ni de salida.** Su adaptador `libreoffice.ts` solo registra la familia de procesador de textos (`doc`, `docx`, `odt`, `rtf`, `wpd`…) pese a que el binario LibreOffice que invoca sí convierte hojas de cálculo. Es una limitación de la tabla, no del motor.
- `ppt` y `odp`: tampoco están. `pptx` aparece únicamente como entrada de `markitdown` y salida de `pandoc`.
- `zip` aparece solo como entrada de `vips` (para pirámides DZI); `7z`, `rar`, `tar` no existen.
- `cbz`, `cbr`, `cb7`: solo entradas de `calibre`, nunca salidas.
- `ttf` / `otf` solo son entradas de ImageMagick/GraphicsMagick (para *renderizar* texto, no para convertir la fuente); nunca salidas. `woff` / `woff2` no existen.
- `eml` solo es salida de `msgconvert`; no se puede leer un `.eml`.
- `parquet`, `feather`, `orc`, `sqlite`, `dta`, `sav`, `xpt`, `fwf`, `jsonl`, `ini`, `env`, `toon`, `p7m`, `tgs`, `drawio`, `kepub`: inexistentes.

---

## 3. Lo que cubre ConvertX y transmute NO

**778 entradas y 397 salidas.** No hay sorpresa en el reparto: es casi todo `ffmpeg`, `imagemagick`, `graphicsmagick`, `assimp` y `vips`. Los 34 formatos de ffmpeg que declara transmute son un subconjunto curado y verificado a mano (con `_decode_only_formats` para `fli`, `flc`, `oma`, `aa3` y comentarios explicando por qué se excluyen `ogg` y `amr`) frente a los 473 que declara ConvertX volcando la tabla completa del binario.

Esa es la diferencia de filosofía y conviene tenerla clara antes de fusionar matrices:

- ConvertX declara **lo que el binario dice que soporta**. Máxima cobertura nominal, fiabilidad no verificada por par.
- transmute declara **lo que ellos han probado que funciona**, con exclusiones comentadas. 164 entradas, pero cada una con intención.

Al construir la matriz de FileX, importar los 893 de ConvertX sin coste por arista replica su problema: pares declarados que fallan en ejecución.

---

## 4. Lo que cubre SnapOtter y ConvertX NO

**Solo 13 entradas y 4 salidas**, y de esas, únicamente **5 entradas y 0 salidas** no las cubre tampoco transmute:

- Entradas nuevas frente a ConvertX: `fit`, `gpr`, `m2ts`, `md`, `mts`, `odp`, `ods`, `ogv`, `ppt`, `ptx`, `ts`, `xls`, `xlsx`
- Entradas que no cubren ni ConvertX ni transmute: **`fit`** (alias FITS), **`gpr`** (GoPro RAW), **`m2ts`** y **`mts`** (AVCHD), **`ptx`** (Pentax RAW)
- Salidas nuevas frente a ConvertX: `odp`, `ods`, `xlsx`, `zip` — todas ya presentes en transmute
- Salidas nuevas frente a ConvertX + transmute: **ninguna**

### El README de SnapOtter frente a su código

> "Supports 55+ input formats (including 23 camera RAW formats) and 17 output formats"

| Afirmación | Veredicto | Evidencia |
|---|---|---|
| 23 formatos RAW de cámara | ✅ **Exacto** | `RAW_EXTENSIONS` en `apps/api/src/lib/file-validation.ts` tiene exactamente 23 entradas: `dng cr2 cr3 nef nrw arw orf rw2 raf pef 3fr iiq srw x3f rwl gpr fff mrw mef kdc dcr erf ptx` |
| 17 formatos de salida | ✅ **Exacto, pero no en el motor** | El `z.enum` de `apps/api/src/routes/tools/convert.ts` tiene 17. Pero el tipo `OutputFormat` de `packages/image-engine/src/types.ts` solo declara **13**; los 4 restantes (`psd`, `ppm`, `eps`, `tga`) los añade la capa API con codificadores CLI externos (`format-encoders.ts` + ImageMagick). El paquete `image-engine` por sí solo no hace 17. |
| 55+ formatos de entrada | ⚠️ **Depende de qué se cuente** | El *gate* real que decide si un fichero se acepta (`SUPPORTED_INPUT_FORMATS`) tiene **27 identificadores**, uno de los cuales (`raw`) agrupa las 23 extensiones RAW → **49 familias de formato**. La tabla de extensiones `EXT_TO_MIME` tiene **65 claves**, pero incluye alias del mismo formato (`jpg`/`jpeg`, `tif`/`tiff`, `j2k`/`j2c`/`jpc`/`jpf`/`jpx`, `fit`/`fts`/`fits`, `epsf`/`eps`, `svgz`/`svg`). "55+" es defendible contando extensiones, no contando formatos distintos: ahí son 49. |

Detalle menor: `packages/image-engine/src/formats/detect.ts` detecta `cin` (Cineon) como formato propio, pero la validación de la API mapea la misma firma mágica a `dpx`, así que `cin` nunca aparece como formato aceptado por su nombre.

**Consecuencia para FileX: SnapOtter aporta ~0 cobertura nueva.** Sus 23 RAW son 21 que ConvertX ya declara vía ffmpeg/ImageMagick, más `gpr` y `ptx`. Lo que sí aporta —y no se ve en una matriz de formatos— es la *arquitectura*: decodificación RAW/PSD/EXR/HDR delegada a CLI externo con límites de píxeles y `AbortSignal`, y saneado de SVG contra SSRF. Eso es lo que hay que mirar de SnapOtter, no su matriz.

---

## 5. Lo que aporta gotenberg

**69 entradas que ConvertX no tiene, 55 que no tiene ninguno de los otros tres.** Todo el bloque son formatos ofimáticos heredados que el filtro de importación de LibreOffice acepta y que la tabla de ConvertX omitió:

`123` `bib` `cgm` `cmx` `dbf` `fodg` `fodp` `fods` `fopd` `ltx` `met` `mml` `numbers` `odd` `odg` `odm` `otg` `oth` `otp` `ots` `potm` `ppsm` `pub` `pxl` `sda` `sdc` `sdd` `sgl` `slk` `smf` `stc` `std` `svm` `sxc` `sxd` `sxg` `sxi` `sxm` `uof` `uop` `uos` `uot` `vdx` `vor` `vsd` `vsdm` `wb2` `wk1` `wks` `xlsb` `xlsm` `xlt` `xltm` `xltx` `xlw`

Es decir: StarOffice (`sd*`, `s[tx]*`), Lotus (`123`, `wk1`, `wks`), MS Works/Publisher (`wps`, `pub`), Visio (`vsd`, `vdx`, `vsdm`), Apple iWork (`numbers`, `pages`, `key`), UOF chino (`uof`, `uop`, `uos`, `uot`), plantillas OpenDocument (`ot*`), plantillas Excel (`xlt*`) y OpenDocument Flat XML (`fod*`).

**Si se quiere ampliar la matriz de LibreOffice, la lista de gotenberg es la fuente correcta: 132 extensiones frente a las 41 de ConvertX.**

### README/constantes de gotenberg frente a su código

`pkg/gotenberg/pdfengine.go` declara **8 perfiles PDF/A** como constantes públicas: `PDF/A-1a`, `PDF/A-1b`, `PDF/A-2a`, `PDF/A-2b`, `PDF/A-2u`, `PDF/A-3a`, `PDF/A-3b`, `PDF/A-3u`, más `PdfUa`.

Pero **solo 4 son producibles**. El único motor cuyo `Convert` no devuelve error es `LibreOfficePdfEngine`, y su implementación (`libreoffice/api/libreoffice.go:405-415`) solo mapea tres casos:

```go
case gotenberg.PdfA1b: args = append(args, "--export", "SelectPdfVersion=1", ...)
case gotenberg.PdfA2b: args = append(args, "--export", "SelectPdfVersion=2", ...)
case gotenberg.PdfA3b: args = append(args, "--export", "SelectPdfVersion=3", ...)
```

más `PdfUa` por separado. `pdfcpu`, `qpdf`, `pdftk` y `exiftool` tienen los cuatro el mismo comentario: `// Convert is not available in this implementation.` **Los perfiles `-1a`, `-2a`, `-2u`, `-3a`, `-3u` están declarados en la API y son inalcanzables**; piden un `ErrPdfFormatNotSupported`.

Dos detalles más de la misma función `Extensions()`:
- Lleva un `// FIXME: don't care, take all on the route level?` encima: la lista está copiada a mano de los filtros de LibreOffice y sus propios autores no confían en ella.
- Contiene `.fopd` **y** `.fodp`. `.fodp` es OpenDocument Presentation Flat XML; `.fopd` no es ningún formato: es una errata que lleva años en la lista.

---

## 6. Recuento actualizado de formatos únicos

| Conjunto | Entradas | Salidas | Formatos distintos (entrada ∪ salida) |
|---|---:|---:|---:|
| ConvertX solo | 885 | 491 | 1 011 |
| + transmute | 942 | 528 | 1 057 |
| + SnapOtter | 947 | 528 | 1 062 |
| + gotenberg | **1 002** | **528** | **1 118** |

Aportación marginal de cada fuente sobre las anteriores, en formatos de entrada:

| Fuente | Entradas nuevas | Salidas nuevas |
|---|---:|---:|
| ConvertX (base) | 885 | 491 |
| transmute | +57 | +37 |
| SnapOtter | +5 | +0 |
| gotenberg | +55 | +0 |

Entradas **exclusivas** de cada fuente (que ninguna de las otras tres declara):

| Fuente | Exclusivas |
|---|---:|
| ConvertX | 715 |
| gotenberg | 55 |
| transmute | 41 |
| SnapOtter | 5 |

### A nivel de pares (origen → destino), un salto

| Fuente | Pares distintos |
|---|---:|
| ConvertX | 152 584 |
| transmute | 3 370 |
| Pares de transmute que ConvertX no tiene | **1 445** |
| Unión ConvertX + transmute | 154 029 |

transmute añade un **+0,95 %** de pares. La cifra es minúscula y **es exactamente el argumento del informe anterior**: la cobertura no se gana sumando adaptadores, se gana encadenando. Lo que transmute aporta no es volumen, es *categorías nuevas* — y una categoría nueva vale más en el grafo que 40 000 pares más de ffmpeg, porque abre un nodo que antes no existía.

*(Los 3 370 pares de transmute son una cota superior: `PyMuPDFConverter.can_convert()` restringe las entradas de imagen a salida `pdf` únicamente, y `RenameConverter` solo permite los 6 pares de su `_RENAME_MAP`. El resto de conversores hacen comprobación simple de pertenencia, así que el producto cartesiano es buena aproximación para 20 de los 22.)*

---

## 7. Los nichos que solo cubre transmute

Cuatro categorías donde transmute es la **única** de las cuatro fuentes con soporte real, con los formatos concretos.

### 7.1 Fuentes tipográficas — `fonttools_convert.py`

`FonttoolsConverter`, sobre `fontTools.ttLib` con `Cu2QuPen` / `Qu2CuPen`.

- **Entradas (4):** `ttf`, `otf`, `woff`, `woff2`
- **Salidas (4):** `ttf`, `otf`, `woff`, `woff2`
- Matriz completa bidireccional: 12 pares. Tres tipos de operación distintos según el par: re-envoltorio sin tocar contornos (TTF/OTF ↔ WOFF/WOFF2), conversión de contornos cuadráticos ↔ cúbicos (TTF ↔ OTF) y re-compresión (WOFF ↔ WOFF2).
- **En ConvertX:** `ttf` y `otf` existen solo como *entradas* de ImageMagick/GraphicsMagick, y para renderizar una muestra de texto a imagen, no para convertir la fuente. `woff` y `woff2` no aparecen en ningún adaptador. **Cobertura real de ConvertX: cero.**
- Es una categoría entera con demanda web evidente (subsetting y conversión a WOFF2 es tarea rutinaria de frontend) y con dependencia pura de Python, sin binario externo.

### 7.2 Subtítulos — `pysubs2_convert.py`

`PySubs2Converter`, sobre `pysubs2`.

- **Entradas (6) = Salidas (6):** `ass`, `ssa`, `srt`, `sub` (MicroDVD), `mpl` (MPL2), `vtt`
- Matriz completa bidireccional: 30 pares.
- Maneja el problema real del formato: MicroDVD trabaja en fotogramas, no en tiempo, así que necesita FPS. Hay un `_default_microdvd_fps = 24` y captura de `UnknownFPSError`. Ese matiz no cabe en una matriz de formatos y es justo lo que hay que modelar como opción por arista.
- **En ConvertX:** `srt`, `vtt`, `ass`, `ssa`, `sub` existen dentro de la tabla de ffmpeg (entrada y salida), y `microdvd`, `sami`, `smi`, `lrc` como entradas; `ttml` como salida. Es decir, ConvertX *puede* hacer srt↔vtt, pero como efecto colateral de ffmpeg, sin control de FPS ni de estilos ASS. `mpl` (MPL2) no está en ConvertX.
- El valor de transmute aquí no es la cobertura de formatos sino el **motor especializado**: pysubs2 preserva estilos y tiempos de forma que ffmpeg no.

### 7.3 Tabulares y datos — `pandas_convert.py`

`PandasConverter`. Es el segundo conversor más ancho de transmute por número de exclusivas (22 de sus 23 entradas no las cubre ningún otro conversor de transmute).

- **Entradas (23):** `csv`, `tsv`, `fwf`, `json`, `jsonl`, `xml`, `yaml`, `toml`, `ini`, `env`, `toon`, `html`, `xls`, `xlsx`, `ods`, `parquet`, `feather`, `orc`, `sqlite`, `dta` (Stata), `sav` (SPSS), `xpt` (SAS), `vcf`
- **Salidas (17):** `csv`, `tsv`, `json`, `jsonl`, `xml`, `yaml`, `toml`, `ini`, `env`, `toon`, `html`, `xlsx`, `ods`, `parquet`, `feather`, `orc`, `sqlite`
- **En ConvertX:** el adaptador `dasel` cubre `yaml`/`toml`/`json`/`xml`/`csv` (5 entradas, 4 salidas) y ya está. **Nada de lo columnar (`parquet`, `feather`, `orc`), nada de bases de datos (`sqlite`), nada de estadística (`dta`, `sav`, `xpt`), nada de hoja de cálculo (`xls`, `xlsx`, `ods`), nada de configuración (`ini`, `env`), nada de `jsonl` ni `fwf`.**
- Los seis formatos exclusivos que más justifican integrarlo: `parquet` y `feather` (interoperabilidad con el mundo de datos), `sqlite` (una tabla es un fichero de datos como cualquier otro), y `dta`/`sav`/`xpt` (Stata, SPSS y SAS — el trío de software estadístico propietario cuyos usuarios no tienen forma libre de exportar).
- Asimetría a documentar: `dta`, `sav`, `xpt`, `fwf`, `xls` y `vcf` son **solo lectura**. Se puede leer un `.sav` de SPSS y sacarlo a Parquet, no al revés.

### 7.4 Correo — `email_convert.py`

`EmailConverter`. El conversor con la asimetría entrada/salida más pronunciada de todo el ecosistema (2 → 10).

- **Entradas (2):** `eml`, `msg`
- **Salidas (10):** `pdf`, `docx`, `odt`, `rtf`, `html`, `md`, `rst`, `epub`, `json`, `txt`
- **En ConvertX:** el adaptador `msgconvert` hace exactamente **una** conversión: `msg` → `eml`. No puede leer un `.eml`, y no puede sacar un correo a ningún formato legible.
- Es el caso de uso de archivo/legal más obvio (exportar una bandeja a PDF o a JSON estructurado) y ConvertX no lo cubre en absoluto.

### 7.5 Y de propina, cuatro nichos más que solo tiene transmute

| Conversor | Cobertura | Comentario |
|---|---|---|
| `archive_convert.py` + `rename_converter.py` | `7z`, `rar`, `tar`, `tar.gz`, `tar.bz2`, `tar.xz`, `tar.zst`, `zip` ↔ entre sí; y `zip↔cbz`, `rar↔cbr`, `7z↔cb7` | ConvertX no tiene archivos. `RenameConverter` es elegante: reconoce que cbz *es* un zip y la conversión es cambiar la extensión, coste cero |
| `pkcs7_convert.py` | `p7m` → formato descubierto en tiempo de ejecución | Firma digital PKCS#7. Único conversor con salida no declarable |
| `ezdxf_convert.py` | `dxf` → `pdf`, `png`, `svg` | ConvertX solo tiene `dxf` como entrada de assimp (malla 3D), que es una lectura distinta del formato |
| `drawio_convert.py` / `tgs_convert.py` | `drawio` → `png`/`svg`/`pdf`/`jpeg`; `tgs` → `json`/`gif`/`webp`/`apng`/`mp4` | Diagramas y stickers de Telegram. Inexistentes en las otras tres fuentes |

---

## 8. Salvedades

1. **La re-extracción de ConvertX no cuadra al 100 % con la del informe anterior.** Aquí salen 896 entradas / 503 salidas (sin normalizar alias) frente a las 893 / 496 documentadas. **La diferencia está íntegramente en el adaptador `pandoc`** (43/65 aquí frente a 40/58 antes); el resto de los 19 adaptadores coincide exactamente. Son dialectos de pandoc con nombre compuesto (`markdown_mmd`, `markdown_phpextra`, `markdown_strict`, `commonmark_x`, `asciidoc_legacy`, `jats_archiving`, `jats_articleauthoring`, `jats_publishing`, `pandoc native`) contados de forma distinta. No cambia ninguna conclusión, pero conviene fijar una única extracción canónica antes de construir el grafo.

2. **Las cifras de gotenberg y ConvertX son declaraciones, no verificaciones.** Los 132 de gotenberg vienen con un `FIXME` de sus propios autores y contienen al menos una errata (`.fopd`). Los 473 de ffmpeg en ConvertX son el volcado de la tabla del binario.

3. **Los pares de SnapOtter no se pueden reducir a una matriz.** Su arquitectura es "una herramienta = una ruta", no "un motor = una tabla". Los 83 `CONVERSION_PRESETS` son un catálogo de SEO/UI, no la capacidad real del sistema: la ruta `/convert` acepta cualquiera de los 49 formatos de entrada hacia cualquiera de los 17 de salida (833 pares) aunque solo 27 estén nombrados como preset.

4. **No se ha ejecutado nada.** Ni contenedores, ni binarios, ni GPU. Todo es parseo estático sobre los repositorios clonados, que no se han modificado.
