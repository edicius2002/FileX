# El vocabulario de firmas del contrato: qué es deuda nuestra y qué es propiedad de los formatos

**Encargo F1** — C14 de `ESTADO-Y-REPARTO.md` §3.C, abierto por `bench/aristas-nominales.md` §11.3:
*«el punto 1 del contrato solo fue evaluable en el 12 % de los destinos de una muestra de 498 aristas;
ampliar el vocabulario de firmas del verificador (hoy 24 nombres) es trabajo pendiente»*.

**Fecha:** 21 de agosto de 2026.
**Máquina:** Windows 10, 12 núcleos, Python 3.11.9, ffmpeg N-121159, ImageMagick 7.1.2-21 Q16-HDRI,
Ghostscript 10.07, contenedor `filex-convertx` (Debian forky/sid) con sus 20 motores.
**Sin GPU y sin pedir su lock. Sin dependencias nuevas:** `bench/scripts/verificador.py` sigue siendo
biblioteca estándar de Python y nada más — no hay `file` ni `libmagic` en este Windows y la tabla se
ha construido ejecutando los motores, no leyendo especificaciones.
**Salidas:** `bench/salidas-firmas/` (1,9 MB, **todo texto**, con `MANIFIESTO.md`).

> Cada afirmación va marcada **MEDIDO** o **PENDIENTE**.
> **Otros dos agentes corrían en paralelo.** Las cifras relativas dentro de cada tanda son sólidas;
> los **milisegundos absolutos no son comparables con los de otros informes** y se dice dónde importa.
> Todas las tandas de coste llevan **los dos testigos de ruido**, con tope propio en el de proceso.

---

## 0. Las tres frases obligatorias, y seis más

1. **La fracción de destinos reales con el punto 1 del contrato evaluable sube del 12,4 % al 54,2 %**
   sobre la misma muestra de 498 aristas de E1, reejecutada entera con las mismas semillas y la misma
   invocación. Sobre las 598 (498 + 100 del estrato PDF), del 18,9 % al 58,0 %; y sobre las 386 que sí
   entregan un fichero, del 16,1 % al 69,9 %. **MEDIDO.** *(§5.1)*
2. **Falsos positivos que añade sobre las 53 salidas del patrón oro: CERO**, con los dos motores, y con
   los mismos 3 avisos en proceso y 4 con subprocesos que publicaron los tres informes anteriores del
   verificador. Los 5 fallos documentados siguen atrapados y se añaden **6 fallos fabricados nuevos**
   que el vocabulario viejo no veía. **MEDIDO.** *(§6.1)*
3. **Del 88 % que no se evaluaba (436 de 498), el 47,9 % era deuda nuestra —firmas que existen y no
   teníamos— y el 17,2 % es propiedad de los formatos: no hay marcador que reconocer.** Queda un 9,2 %
   de deuda abierta y un 25,7 % en el que no hay fichero que juzgar porque la arista falla antes.
   **Descontando esas 112, el reparto es 64,5 % deuda nuestra frente a 23,1 % propiedad del formato.**
   **MEDIDO.** *(§5.3)*
4. **La distinción no es teórica: 90 de los 381 formatos con veredicto (23,6 %) NO TIENEN marcador**, y
   se ha medido, no deducido — escribiéndolos dos o tres veces con contenidos distintos y comprobando
   que no comparten ni un byte en posición fija. Píxeles crudos, fax CCITT, PCM crudo y markup en
   fragmento. **MEDIDO.** *(§2, §3)*
5. **Y un marcador no identifica un formato: el 67,4 % de los que lo tienen lo COMPARTEN.** Quince
   formatos empiezan por `PK\x03\x04` y otros quince por `<?xml`. Decir «es un ZIP» es verdad; decir
   «es un DOCX» exige abrir el ZIP. **MEDIDO.** *(§3.3)*
6. **El fallo emblemático del proyecto se reproduce con un motor real y 22 destinos a la vez:**
   `magick x.png y.group4` devuelve **rc=0** y entrega **un PNG**. Igual con `.null`, `.mvg`, `.msl`,
   `.data`, `.vid`, `.flif`… **Ni el vocabulario viejo ni el nuevo lo atrapan por firma**, porque para
   eso habría que saber qué firma esperar de `.group4` y `.group4` no tiene ninguna. Lo atrapa una
   regla que no necesita saberlo —**G6: la salida tiene la misma firma que la entrada**— que cuesta 0 y
   pasa de **0/22 a 22/22**. **MEDIDO.** *(§7.1)*
7. **La respuesta a la pregunta de diseño es que NO basta con los puntos 2-5, y por una razón
   estructural: la sonda del contrato lee CABECERAS, y un formato sin marcador tampoco tiene cabecera.**
   Sobre un `.rgb` el verificador declaraba `1_firma`, `3_propiedades` y `4_pedido` **cubiertos** habiendo
   medido cero. Corregido: ahora dice que no puede. **MEDIDO.** *(§7.2)*
8. **El coste no se mueve.** `firma_real` sobre PNG, JPEG, MP4, PDF y FLAC: **0,047–0,065 ms**, igual
   que con 24 nombres. La única vía cara es el ZIP, que abre el directorio central para separar
   docx/xlsx/pptx/epub/odt: **0,255 ms, y solo la pagan los ZIP**. **MEDIDO.** *(§6.3)*
9. **Y dos fallos del propio verificador encontrados al medir, los dos corregidos:** `csv.Error` **no es
   subclase de `ValueError`**, así que el «TXT» de 156 MB de ImageMagick **tumbaba el proceso**; y un
   `.html` se clasificaba como CSV y disparaba `D2 número de campos no constante` —el falso positivo que
   `bench/contrato-quinto-punto.md` §3.1 llamó *«un falso positivo que acierta por casualidad»*—.
   **MEDIDO.** *(§8)*

---

## 1. El universo: qué destinos hay que verificar de verdad

`analysis/00-matriz-formatos.md` publica **896 formatos de entrada y 503 de salida** declarados por los
20 adaptadores de ConvertX. Reextraídos con el mismo parser que usó E1 (`_formatos.py`, que reproduce
exactamente ffmpeg 473/202 e ImageMagick 245/183) salen **895 y 502**. **La diferencia de uno en cada
columna no se ha localizado y se declara**; todo lo que sigue usa 502, que es la cifra que este informe
puede reproducir. **MEDIDO.**

Los que hay que verificar son **los 502 de salida**: el punto 1 juzga lo que se entrega.

**Los tres proxies de demanda**, porque priorizar por orden alfabético habría sido gastar el trabajo
donde no se pide nada:

| Proxy | Qué es | Tamaño |
|---|---|---:|
| **Patrón oro** | las extensiones de destino de las 39 órdenes de `bench/salidas-referencia/referencia.json` | **17** |
| **SnapOtter** | el catálogo de entrada de `repos/orchestrators/SnapOtter/.../modality.ts` | **86** |
| **Consenso del sector** | cuántos de los 20 adaptadores declaran ese formato como salida | 1–8 |

Los 17 del patrón oro (`pdf png jpg webp mp4 mp3 flac wav csv gif avif m4a opus json mkv webm tif`)
son los que un producto sirve todos los días, y **el vocabulario viejo ya los cubría**. La pregunta de
C14 no es sobre ellos: es sobre los otros 485.

---

## 2. El método: sondear en ejecución, no deducir

**No hay `file` ni `libmagic` en este Windows, y leer una tabla de bytes mágicos de un manual sería
exactamente lo que este repositorio lleva refutando desde el principio** —`av1_nvenc` aparece listado y
no funciona—. Así que la tabla se ha construido ejecutando:

> **Cada formato de salida se escribe DOS O TRES VECES con contenidos deliberadamente distintos y se
> mira en qué posiciones de los 64 primeros bytes coinciden TODAS las muestras.**
>
> - hay posiciones estables → el formato tiene marcador;
> - no hay ninguna → el formato **no tiene marcador**, y eso es una respuesta, no una laguna.

**Cobertura del censo — MEDIDO:**

| Motor | Dónde | Destinos declarados | Escritos |
|---|---|---:|---:|
| ffmpeg | Windows | 202 | 157 |
| ImageMagick | Windows | 183 | 174 |
| Ghostscript | Windows | 18 dispositivos mapeados | 17 |
| graphicsmagick, vips, pandoc, inkscape, potrace, assimp, dasel, libjxl, libheif, vtracer, resvg, dvisvgm, libreoffice, calibre | contenedor `filex-convertx` | 162 exclusivos | — |
| **Total de los 502** | | **502** | **423 (84,3 %)** |

Los **79 restantes** no los escribe ningún motor de esta máquina ni del contenedor. **No se rellenan
con una suposición: se declaran.** Casi todos son formatos que E1 ya había refutado por otra vía
(`302`, `ac4`, `avs3`, `dnxhd`, `dts`, `dv`, `gsm`, `gxf`, `h261`, `h263`, `mlp`, `thd`…: `Encoder not
found` o `received no packets`).

### 2.1 Las tres respuestas, no dos

| Categoría | Qué significa | Qué hace el contrato |
|---|---|---|
| **1 · Evaluable y lo evaluamos** | hay marcador y está en la tabla | evalúa el punto 1 |
| **2 · Evaluable y NO lo evaluamos** | hay marcador y falta la entrada | **deuda**: hay que cerrarla |
| **3 · No evaluable por naturaleza** | no hay marcador que reconocer | **NO APLICA**, y se dice así |

**«No aplica» y «no lo sé» no son lo mismo, y el verificador no las distinguía.** Hasta hoy
`cobertura["1_firma"]` valía `True` **incondicionalmente**: declaraba el punto 1 cubierto en el 100 %
de los ficheros mientras E1 medía que solo era evaluable en el 12 % de los destinos. **Es el mismo fallo
de `markitdown-mcp` que este repositorio lleva citando desde el principio, dentro de su propio
verificador.** Corregido: `cobertura["1_firma"]` es `True` si se evaluó **o si el formato no tiene
marcador**, y `False` si simplemente no está en la tabla.

### 2.2 Dos falsos positivos del método, pagados y corregidos

**Refutar el propio arnés antes de publicar es parte del método.** El primer censo dio dos clases de
«marcador» que no lo eran:

| # | Síntoma | Causa | Corrección |
|---|---|---|---|
| 1 | los formatos de **PCM crudo** (`sb`, `ub`, `sw`, `uw`, `al`, `ul`, `pcm`, `dfpwm`, `g722`, `sbc`, `msbc`, `latm`, `loas`) salían con un prefijo común de **64 bytes** | las dos semillas de audio eran **dos senos de fase 0**, y la pista de audio de los dos vídeos era **el mismo seno de 440 Hz**. El «marcador» era la señal | tres audios distintos (seno 440 Hz, **ruido blanco**, seno 110 Hz) y una pista de audio distinta en cada vídeo |
| 2 | `info` (ruta completa), `shtml` (`<map name="…`), `uil`, `pdb` salían con prefijos largos | esos formatos **estampan el nombre o la ruta del fichero** en la cabecera, y mis dos muestras se llamaban parecido | cada muestra se escribe en **un directorio distinto y con un nombre distinto** (`d0/v7.x` y `x1/w7919.x`) |

Con la corrección, los 13 formatos de PCM crudo pasan de «tienen marcador de 64 bytes» a **«no tienen
ni uno»**, que es la verdad. **MEDIDO.**

### 2.3 El control de tres semillas sobre pandoc — la refutación más limpia del informe

Las dos semillas de markdown del censo **empiezan las dos por un título**. Los 64 destinos de pandoc
heredaban esa estructura y aparecían con prefijos de 2 a 5 bytes (`==`, `=====`, `{#`,
`\begin{frame}{`, `<section id="`…) que parecían marcadores.

Se añadió **una tercera semilla que empieza por prosa llana** y se repitieron los 64 (`_cont_pandoc3.py`):

> **42 de los 64 destinos de pandoc pierden el prefijo ENTERO. MEDIDO.**
> `asciidoc`, `commonmark`, `context`, `djot`, `docbook`, `docbook4`, `docbook5`, `dokuwiki`, `gfm`,
> `haddock`, **`html`, `html4`, `html5`**, `jats` (los cuatro), `jira`, `latex`, `man`, `markdown` (los
> cuatro), `markua`, `mediawiki`, `ms`, `muse`, `opml`, `org`, `plain`, `rst`, `tei`, `textile`,
> `typst`, `xwiki`, `zimwiki`, `biblatex`, `bibtex`.

Los 22 que **sí** conservan prefijo con tres semillas son los que van dentro de un envase o llevan
preámbulo fijo: `docx`, `epub`, `epub2`, `epub3`, `odt`, `pptx`, `pdf`, `rtf`, `json`, `csljson`,
`ipynb`, `icml`, `fb2`, `opendocument`, `chunkedhtml`, `htmlz`, `beamer`, `revealjs`, `s5`, `slidy`,
`slideous`, `dzslides`, `texinfo`.

**La lección, y vale para todo el censo:** *un prefijo común entre dos muestras no es un marcador hasta
que se ha probado con una muestra que rompa la estructura compartida.* Sin la tercera semilla, este
informe habría declarado 42 formatos de markup «evaluables» y habría metido 42 entradas inútiles —y
peligrosas— en la tabla.

### 2.4 Lo que el método no puede decidir, declarado

| Límite | Cuántos | Por qué |
|---|---:|---|
| **Un solo escritor por formato** | la mayoría | un prefijo estable puede ser del **formato** o del **escritor**. `# ImageMagick pixel enumeration`, `# File produced by OpenAsset…`, `solid AssimpScene`, `; FBX 7.5.0 project file`, `GIMP Palette` son banners del motor. Con un solo escritor no se pueden separar: **21 formatos quedan declarados indeterminados por esto** |
| **El motor escribió otra cosa** | **22** | `magick x.png y.group4` entrega un PNG. La muestra describe al motor, no al formato (§7.1) |
| **Marcador más allá del byte 512** | 4 | `pict` lo tiene en el 522, `pcd` en el 0x800. La sonda lee 512 bytes de una vez y no los ve |
| **No escribible** | 79 | ningún motor local ni del contenedor lo produce |

---

## 3. El censo: los 502 destinos en las tres categorías

**MEDIDO** (`categorias.json`, `_categorias.py`):

| Categoría | Vocabulario **viejo** (24 nombres) | Vocabulario **nuevo** |
|---|---:|---:|
| **1 · Evaluable y lo evaluamos** | **33 (6,6 %)** | **298 (59,4 %)** |
| **2 · Evaluable y NO lo evaluamos (deuda)** | 262 (52,2 %) | **12 (2,4 %)** |
| **3 · No evaluable por naturaleza** | 90 (17,9 %) | **106 (21,1 %)** |
| — · Indeterminado (declarado, no rellenado) | 117 (23,3 %) | 86 (17,1 %) |

Y el reparto que responde a la pregunta del encargo, **sobre los 469 destinos que el vocabulario viejo
no evaluaba**:

| | Destinos | % |
|---|---:|---:|
| **Era deuda nuestra, y está cerrada** | **265** | **56,5 %** |
| **Es propiedad de los formatos: no hay marcador** | **106** | **22,6 %** |
| Sigue siendo deuda | 12 | 2,6 % |
| Indeterminado | 86 | 18,3 % |

> **Sobre los 381 formatos con veredicto de marcador: 291 lo tienen (76,4 %) y 90 no (23,6 %).**
> **MEDIDO.** Casi uno de cada cuatro formatos de salida que ConvertX declara **no puede tener el punto
> 1 del contrato, y no por culpa nuestra.**

### 3.1 Los 90 sin marcador, por familia

| Familia | Ejemplos | Por qué no hay marcador |
|---|---|---|
| **Píxeles crudos** (20+) | `rgb rgba bgr bgra cmyk cmyka gray graya yuv ycbcr uyvy pal map mono bayer` | el fichero **son los píxeles**. La geometría va fuera. Son los mismos 20 que E1 §4.2 encontró que **ImageMagick no puede releer aunque acaba de escribirlos** |
| **Fax CCITT** | `g3 g4 fax` | datos de compresión crudos, sin contenedor |
| **PCM crudo** | `sb ub sw uw al ul pcm dfpwm g722 sbc msbc latm loas` | muestras y nada más |
| **Markup en fragmento** | `md rst org textile typst latex man ms docbook jats tei mediawiki gfm commonmark…` | texto plano. **MEDIDO con tres semillas** (§2.3) |
| **Cabecera de campos sin constante** | `tga icb vda vst art wbmp otb palm pix rgf hrz strimg mtv` | los primeros bytes son valores, no constantes. *(TGA 2.0 lleva `TRUEVISION-XFILE` **al final** y es opcional: sería otra sonda)* |
| **Colisión de nombre** | `avs` | la misma extensión son **tres formatos**: la imagen AVS X de ImageMagick, el vídeo Argonaut de ffmpeg y un guion de AviSynth. **Ninguna firma puede decidir cuál se pidió** |

### 3.2 Los 12 que siguen en deuda, con su motivo

**Ninguno es un olvido: cada uno tiene una razón medida para no estar en la tabla.**

| Formato | Adaptadores | Motivo |
|---|---:|---|
| `pct`, `pict` | 2 | el marcador de PICT está en el **byte 522** y la sonda lee 512 |
| `pcd`, `pcds` | 2 | `PCD_IPI` está en el **byte 0x800**; los primeros 2 KB son relleno `0xFF` — y ese relleno **casa con el sincronismo de trama de audio MPEG**, así que hoy un `.pcd` se clasifica como `mpegaudio` |
| `3ds` | 1 | su marcador son **dos bytes, `MM`**, que chocan con el `MM\x00*` de TIFF. Añadirlo compraría un formato y arriesgaría todos los TIFF |
| `a64`, `apm`, `aptx`, `aptxhd`, `rso`, `rb` | 1 | marcadores de 2 a 6 bytes de formatos con **un solo adaptador**: mucho riesgo de colisión por muy poca demanda |
| `fbxa` | 1 | el prefijo es `; FBX 7.5.0 project file`, un **banner de escritor** con número de versión dentro |

### 3.3 El matiz que hay que decir aunque no lo pidiera el encargo: un marcador no identifica un formato

**MEDIDO: de los 291 formatos con marcador, 196 (67,4 %) comparten sus cuatro primeros bytes con al
menos otro formato.** Hay **51 grupos**. Los mayores:

| Marcador | n | Formatos |
|---|---:|---|
| `PK\x03\x04` | 15 | `docx docm dotx dotm epub epub2 epub3 kepub.epub odt ott odg pptx htmlz txtz 3mf` |
| `<?xml` | 15 | `svg msvg rsvg svgz collada dae fodt fb2 fxg gimppath htm mpd ttml assxml xml` |
| `%!PS-Adobe` | 10 | `ps ps2 ps3 postscript eps eps2 eps3 epsf epsi epi` |
| `\x89PNG` | 8 | `png png8 png00 png24 png32 png48 png64 apng` |
| `\x00\x00\x00\x20ftyp` | 8 | `mp4 m4a m4b m4v f4v psp h264.mp4 av1.mp4` |
| `Y\xa6j\x95` | 7 | `ras sun sunras rs im1 im8 im24` |
| `\x1aE\xdf\xa3` | 6 | `mkv webm av1.mkv h264.mkv h265.mkv h266.mkv` |

**Consecuencia de diseño:** el vocabulario del punto 1 tiene **dos niveles**, y mezclarlos es inflar la
cifra.

- **Nivel de formato**: `firma == "png"` decide que un `.png` es un PNG.
- **Nivel de familia**: para `.csv`, `.md`, `.html`, `.xml`, `.json`, `.txt`… lo comprobable es *«esto
  es texto»* o *«esto es XML»*, no *«esto es CSV y no TSV»*. **28 extensiones** están marcadas así
  (`EXT_FAMILIA`) y el verificador lo dice con un hallazgo `G5 informativo`.

Y hay una excepción cara que sí compensa: **`PK\x03\x04` se desambigua abriendo el ZIP**. La segunda
pasada lee el miembro `mimetype` sin comprimir (byte 38) para ODF y EPUB, y los nombres de los miembros
(`word/`, `xl/`, `ppt/`) para OOXML. Cuesta **0,255 ms** y **solo la pagan los ZIP** (§6.3). Sin ella,
`docx`, `xlsx`, `pptx`, `epub`, `odt`, `ods` y `odp` —siete formatos de máxima demanda— serían
indistinguibles entre sí.

---

## 4. El vocabulario ampliado

**MEDIDO** (`vocabulario.json`):

| | Antes | Ahora |
|---|---:|---:|
| **Nombres de firma** que `firma_real` puede devolver | **24** | **147** |
| Entradas de bytes mágicos en `FIRMAS` | 14 | **116** |
| Marcas `ftyp` de la familia ISO-BMFF | 14 | **39** |
| **Extensiones en `EXT_A_FIRMAS`** | 26 | **338** |
| Extensiones declaradas **sin marcador** (`EXT_SIN_FIRMA`) | — | **112** |
| Extensiones de comprobación de **familia** (`EXT_FAMILIA`) | — | 28 |

### 4.1 Qué se añadió, y de dónde sale cada cosa

- **La tabla `FIRMAS`** pasa de 14 a 116 entradas `(desplazamiento, bytes, nombre)`. **Todas salen del
  censo**, con la cabecera real de al menos dos escrituras del formato guardada en
  `firmas_censo_local.json` / `firmas_censo_contenedor.json`.
- **Marcadores que no están en el byte 0**: `ftyp` (4), ` EMF` (40), la versión de XWD (4), y
  **`BOOKMOBI` en el byte 60** para MOBI/AZW3 — donde el prefijo aparente (`Unknown…`) es el **título
  del libro** que estampa Calibre, no un marcador.
- **Cuatro predicados en vez de literales**, porque el marcador es un conjunto y no una constante:
  la familia **PNM** (`P1`..`P7`, `PF`/`Pf`), **PCX** (`0x0A` + versión + codificación + bits),
  **MPEG-TS** (0x47 cada 188 bytes, y 0x47 en el byte 4 para M2TS) y **audio MPEG frente a ADTS**
  (los dos empiezan por `FF Ex`; los bits de capa valen `00` en ADTS y nunca en MPEG-1/2 audio).
- **Refinamiento de envases**: RIFF (webp/wav/avi/rmid), FORM (aiff), ISO-BMFF (39 marcas),
  **ZIP** (epub/odt/ods/odp/odg/docx/xlsx/pptx) y CFB/OLE.
- **Refinamiento de texto**: `%!PS`, `{\rtf`, `#EXTM3U`, `WEBVTT`, `[Script Info]`, `YUV4MPEG2`,
  `;FFMETADATA`, `/* XPM */`, `#define `, y el prólogo XML con su elemento raíz para separar
  `svg` de `html` de `xml`.

### 4.2 Las excepciones justificadas por datos

`bench/verificador-fidelidad.md` §6 mide que **entre el 5 y el 7 % de un verificador son excepciones que
no se deducen de la especificación**: 85 líneas la primera vez, 74 la segunda. **Aquí la constante
reaparece con otra cara**: no son umbrales mal calibrados, son **entradas de la tabla que hubo que
quitar o corregir porque marcaban como fallo una salida legítima**. No se cuentan en líneas —cada una es
una línea— pero **ninguna se deduce de una especificación: las seis salieron de ejecutar**.

| # | Entrada retirada o corregida | Qué la delató |
|---|---|---|
| 1 | `.obu` esperaba `flujo_es` (código de arranque Annex-B) | un AV1 OBU **no es Annex-B**: empieza por `12 00 0a`. Salida legítima de ffmpeg marcada `fallo`. Sustituido por un marcador `av1obu` medido en 3 muestras |
| 2 | `.y4m` esperaba `y4m` y no se detectaba | `YUV4MPEG2` estaba solo en la rama de **texto**, a la que no se llega porque el cuerpo del Y4M es binario. Movido a la tabla de mágicos binarios |
| 3 | `.avs` esperaba `flujo_es` | la misma extensión son **tres formatos distintos** en tres motores. Movido a `EXT_SIN_FIRMA` con ese motivo escrito |
| 4 | JBIG **detrás** de ICO en la tabla | comparten `00 00 01 00` y el de JBIG es más largo. Reordenado: un ICO válido no puede declarar 0 imágenes |
| 5 | `.html`, `.xml`, `.txt` con firma estricta | pandoc emite **fragmentos** sin prólogo: `<h2 …`. Aceptan la familia de texto y se marcan como comprobación de familia |
| 6 | `.csv`/`.json` mantienen `{"texto"}` | es la comprobación que ya tenían y **sigue atrapando un binario en un destino textual** |

Las tres primeras las encontró `_valida_tabla.py` **escribiendo los 385 destinos locales y pasando el
punto 1 sobre cada salida legítima** (§6.2). No se deducen leyendo nada.

### 4.3 Lo que ve quien invoca el verificador

La CLI no cambia de firma. Lo que cambia es que **ahora dice qué pudo hacer con el punto 1**:

```
python bench/scripts/verificador.py --salida z.rgb --entrada corpus/imagen/tipico.png --destino rgb
```
```
CONTRATO (grupo A)     AVISO      z.rgb
  [p1 G4 informativo] el formato no tiene marcador (pixeles crudos sin cabecera):
                      el punto 1 NO APLICA a .rgb
  [p1 G6 aviso] la salida tiene la MISMA firma que la entrada (png) y se pidio .rgb:
                el motor no reconocio la extension y conservo el formato de origen
  punto 1: no_aplica
  cobertura: PARCIAL (sin cubrir: 4_alfa, 5_escritura)
```

`verificar()` devuelve una clave nueva, **`punto1`**, con cuatro valores —`evaluado`, `familia`,
`no_aplica`, `sin_vocabulario`— y `punto1_estado(ruta)` la calcula suelta. **Es la respuesta a la
pregunta de E1 y por eso se publica aparte del veredicto:** cobertura y veredicto son cosas distintas.

---

## 5. La métrica honesta: la misma muestra de E1, reejecutada

La métrica que pide el encargo no es «cuántas firmas conozco»: es **qué fracción de los destinos reales
pasa de "no evaluable" a "evaluado"**. Para que la cifra sea comparable con el 12 % de E1 hay que medir
sobre **la misma muestra**: sus 498 aristas generales más las 100 del estrato PDF, con la misma semilla
aleatoria, la misma invocación de ConvertX y las mismas semillas de entrada.

`bench/salidas-aristas/` se ha leído y **no se ha tocado**. Su `pool/` estaba borrado —711 MB,
regenerable— así que `_remuestra.py` rehace las 188 semillas de entrada con la **misma procedencia** que
E1 registró en `semi_entrada.json`, en un directorio desechable propio. **Las 598 aristas se han vuelto
a convertir de verdad**, no se ha reinterpretado el JSON: hacía falta para saber si el vocabulario nuevo
marca como fallo alguna salida legítima.

**El control de que la reejecución es la misma medida — MEDIDO:** pasando el **verificador congelado de
E1** sobre las salidas nuevas, el punto 1 sale evaluable en **62 de 498 = 12,4 %**, que es
**exactamente** lo que publicó `aristas-nominales.md` §2. En el estrato PDF sale 50 frente a sus 51
(una arista de diferencia). **La reejecución reproduce el punto de partida.**

### 5.1 La cifra

**MEDIDO** (`remuestra.json`, `resumen_remuestra.json`):

| | Estrato **general** (n=498) | Estrato **PDF** (n=100) | Unión (n=598) |
|---|---:|---:|---:|
| **E1, tal y como lo publicó** | **12,4 %** | 51,0 % | 18,9 % |
| Vocabulario viejo, reejecutado | 12,4 % | 50,0 % | 18,7 % |
| **Vocabulario NUEVO** | **54,2 %** | **77,0 %** | **58,0 %** |
| — el formato no tiene marcador: **NO APLICA** | 15,3 % | 12,0 % | 14,7 % |
| — sigue sin vocabulario: **deuda** | 8,0 % | 8,0 % | 8,0 % |
| — no hay fichero que juzgar (la arista falla) | 22,5 % | 3,0 % | 19,2 % |

> ### **El punto 1 del contrato pasa del 12,4 % al 54,2 % de los destinos reales.** **MEDIDO.**
>
> Y sobre las **386 aristas del estrato general que sí produjeron un fichero** —que es donde la pregunta
> tiene sentido— pasa del **16,1 % al 69,9 %**.

**La otra mitad de la cifra, y es la que hace que el 54,2 % no sea un techo escondido:** de lo que no se
evalúa, **el 15,3 % es porque el formato no tiene marcador**, y ahí el verificador ya no calla: dice
`G4 informativo · el punto 1 NO APLICA`. Sumando lo evaluado y lo que no aplica, **el punto 1 tiene una
respuesta motivada en el 69,5 % de los destinos**, frente al 12,4 % de antes.

### 5.2 Ninguna de las 598 salidas legítimas se marca como fallo — **MEDIDO**

| | Vocabulario viejo | Vocabulario nuevo |
|---|---:|---:|
| Aristas en las que el punto 1 dispara `fallo` | **1** | **0** |
| …de ellas, aristas que E1 contó como **reales** | 0 | **0** |

**Cero falsos positivos sobre la muestra entera.** Y hay que contar también la pérdida, porque es real:

> **El vocabulario nuevo PIERDE la única detección que tenía el viejo, y la pierde por ser más honesto.**
> Es `epsi → group4`: E1 la marcó DESTRUIDO porque su tabla suponía que `.group4` debía ser un TIFF y
> obtuvo texto. **Esa suposición es falsa, y se ha comprobado ejecutando:** `magick x.png GROUP4:y.dat`
> escribe **datos CCITT crudos de 326 bytes, sin cabecera**, no un TIFF. Con `.group4` correctamente
> declarado **sin marcador**, el punto 1 dice «no aplica» y la detección desaparece.
>
> **La recupera G6** (§7.1): la salida de `epsi → group4` es **PostScript de 13 MB**, exactamente la
> firma de la entrada.

### 5.3 El reparto del 88 %

E1 no pudo evaluar el punto 1 en **436 de las 498** aristas del estrato general: **el 87,6 %**. Este es
su reparto, medido una por una:

| | Aristas | % del 88 % |
|---|---:|---:|
| **Era deuda nuestra, y está cerrada** | **209** | **47,9 %** |
| **Es propiedad de los formatos: no hay marcador que reconocer** | **75** | **17,2 %** |
| Sigue siendo deuda de vocabulario | 40 | 9,2 % |
| No hay fichero que juzgar: la arista falla antes (criterio N1) | 112 | 25,7 % |

Y **quitando las 112 en las que no hay nada que mirar**, sobre las **324 aristas que sí entregaron un
fichero**:

| | Aristas | % |
|---|---:|---:|
| **Era deuda nuestra** | **209** | **64,5 %** |
| **Es propiedad de los formatos** | **75** | **23,1 %** |
| Sigue siendo deuda | 40 | 12,3 % |

> **Casi dos tercios del 88 % era laguna de nuestro vocabulario y casi una cuarta parte es una propiedad
> de los formatos.** La cifra del censo de los 502 destinos (§3) apunta en la misma dirección desde el
> otro lado: **56,5 % deuda cerrada, 22,6 % propiedad del formato.** Las dos medidas son independientes
> —una es la población declarada, la otra una muestra ejecutada— y coinciden en el orden de magnitud.

### 5.4 G6 sobre la muestra: 19 aristas más, 17 que E1 contaba como reales — **MEDIDO**

`_g6.py` rematerializa las 188 semillas de entrada, les calcula la firma con el vocabulario nuevo y
aplica el predicado de G6 a las 598 filas ya medidas (`g6.json`):

| | |
|---|---:|
| Aristas en las que G6 se dispara | **19** |
| …que E1 clasificó como **reales** (ÍNTEGRO 13 · DEGRADADO 4) | **17** |
| …que E1 ya clasificaba como nominales (DESTRUIDO) | 2 |

**Las 19 son ImageMagick devolviendo el formato de la entrada**: `pdf → pocketmod`, `pdf → inline`,
`pdf → data`, `gif → clipboard`, `gif87 → mvg`, `jpc → clipboard`, `j2k → null`, `epdf → null`,
`mat → null`, `dxt5 → data`, `avif → inline`, `mpeg → histogram`, `rsvg → data`, `ept → clipboard`,
`epi → sf3`, `fl32 → sf3`, `vda → vid`, `pcds → pcd`, `epsi → group4`.

**Dos matices honestos, y por eso G6 es `aviso` y no `fallo`:**
- **`pcds → pcd` y `vda → vid` son conversiones dentro de la misma familia** (PhotoCD y TGA): que la
  firma no cambie puede ser correcto. Un `aviso` es la severidad adecuada; un `fallo` sería un falso
  positivo.
- **`vda → vid` destapa además la colisión TGA/CUR** declarada en §10: un TGA sin comprimir empieza por
  `00 00 02 00`, igual que un cursor de Windows, y el verificador lo llama `cur`. G6 se dispara
  correctamente —las dos firmas coinciden— pero el nombre que publica está mal.

**Esto confirma la nota de `aristas-nominales.md` §11.3 —*ampliar el vocabulario solo puede subir el
50,5 %, nunca bajarlo*— y le pone número: +17 aristas del estrato general y del PDF que E1 contó como
reales y que entregan el formato de la entrada.** Lo que no se hace aquí es recalcular el 50,5 %: eso
exige rehacer la extrapolación de E1 y es su informe. **PENDIENTE.**

---

## 6. Lo que no puede romperse

### 6.1 Las 53 salidas del patrón oro: **0 falsos positivos** — **MEDIDO**

`regresion53.json`. Mismo protocolo que los tres informes anteriores: los dos motores, `alfa=True`.

| Motor | Salidas | **Falsos positivos** | Falsos negativos | Veredictos | Avisos |
|---|---:|---:|---:|---|---:|
| proceso | 53 | **0** | 0 | 49 `ok_parcial` · 3 `aviso` · 1 `fallo` | 3 |
| subproceso | 53 | **0** | 0 | 48 `ok_parcial` · 4 `aviso` · 1 `fallo` | 4 |

- Los **3 avisos en proceso** son los de siempre y todos legítimos: `tipico_mp4-audio.flac` (A6,
  profundidad inflada), `tipico_png-to.pdf` y `tipico_jpg-to.pdf` (P7, 1 px → 1 pt). El cuarto con
  subprocesos es el bitrate de `trivial_wav-to.m4a`. **Idénticos a `verificador-fidelidad.md` §5.2,
  `verificador-ghostscript.md` §3.1 y `contrato-quinto-punto.md` §3.3.**
- El único `fallo` es `2pistas_mkv-to-DEFAULT.mp4`, **cuyo veredicto esperado es `fallo`**.
- Los 49 `ok_parcial` son el precio del punto 5 sin censo, medido por P3, no de este trabajo.
- **`punto1` de las 53: `evaluado` en las 53.** Ninguna cae en «familia», «no aplica» ni «sin
  vocabulario».

**Y los fallos fabricados — MEDIDO:**

| Caso | Esperado | Vocabulario viejo | Vocabulario nuevo |
|---|---|---|---|
| **PNG entregado con extensión `.avif`** (el fallo nº 1 del catálogo) | fallo | **FALLO** ✔ | **FALLO** ✔ |
| *control*: PNG con extensión `.png` | ok | OK ✔ | OK ✔ |
| fichero de 0 bytes presentado como éxito | fallo | **FALLO** ✔ | **FALLO** ✔ |
| **PNG con extensión `.svg`** | fallo | pasaba | **FALLO** ✔ |
| **PNG con extensión `.docx`** | fallo | pasaba | **FALLO** ✔ |
| **PNG con extensión `.ico`** | fallo | pasaba | **FALLO** ✔ |
| **PNG con extensión `.eps`** | fallo | pasaba | **FALLO** ✔ |
| **PDF con extensión `.epub`** | fallo | pasaba | **FALLO** ✔ |
| **FLAC con extensión `.aiff`** | fallo | pasaba | **FALLO** ✔ |

**Seis fallos nuevos atrapados, cero regresiones.**

### 6.2 La prueba ancha: 345 salidas legítimas — **MEDIDO**

Las 53 son un listón imprescindible pero **corto: tocan 17 extensiones y la tabla nueva tiene 338**.
`_valida_tabla.py` escribe **los 385 destinos que ffmpeg e ImageMagick declaran**, con la invocación de
ConvertX, y pasa el punto 1 sobre cada salida:

| | Resultado |
|---|---|
| Destinos escritos | **345 de 385** |
| Estado del punto 1 | 253 `evaluado` · 60 `no_aplica` · 32 `sin_vocabulario` |
| **`fallo` del punto 1 sobre una salida legítima** | **0** |
| `aviso` G6 | **12** — y los 12 son ImageMagick entregando un PNG (§7.1) |

**La primera pasada de esta misma prueba dio 3 fallos** (`obu`, `y4m`, `avs`). Son las tres primeras
excepciones de §4.2. **Sin esta prueba, esos tres habrían llegado al informe como «mejora».**

### 6.3 El coste — **MEDIDO** (mediana n=9, con los dos testigos)

| Fichero | `firma_real` **viejo** | `firma_real` **nuevo** | Factor |
|---|---:|---:|---:|
| PNG 1920×1080 | 0,0586 ms | **0,0536 ms** | ×0,91 |
| JPEG | 0,0631 ms | **0,0485 ms** | ×0,77 |
| MP4 de 16 MB | 0,0701 ms | **0,0469 ms** | ×0,67 |
| PDF | 0,0504 ms | 0,0653 ms | ×1,30 |
| FLAC | 0,0445 ms | 0,0506 ms | ×1,14 |
| **DOCX (ZIP: segunda pasada)** | 0,1031 ms | **0,2550 ms** | **×2,47** |
| **Contrato completo sobre las 53** | 52,2 ms | **47,6 ms** | ×0,91 |

**La lectura:** el vocabulario ampliado **no cuesta nada** en el caso normal —las diferencias de ±30 %
sobre 0,05 ms están dentro del ruido de la tanda, que salió etiquetada `SUCIA` con nivel ×1,20—. La
única vía que sí cuesta es la **segunda pasada del ZIP**, y se paga solo cuando el fichero es un ZIP.
Sobre las 53 el contrato **no empeora**.

> **Salvedad obligatoria (CLAUDE.md §3):** estos milisegundos **no son comparables** con los 0,37 ms
> por salida de `verificador-fidelidad.md` ni con los 0,43 ms de `contrato-quinto-punto.md`. Aquí la
> suite incluye el sondeo de la entrada y había dos agentes más trabajando. **Lo comparable es la
> columna viejo frente a la columna nuevo, tomadas en la misma tanda.**

---

## 7. La pregunta de diseño: si el punto 1 no aplica, ¿basta con los puntos 2, 3, 4 y 5?

**No. Y la respuesta corta es que un formato sin marcador tampoco tiene cabecera, y la sonda del
contrato lee cabeceras.**

### 7.1 El fallo emblemático, reproducido 22 veces con un motor real — **MEDIDO**

`magick corpus/imagen/tipico.png -auto-orient salida.group4` devuelve **rc=0** y entrega **un PNG de
313 bytes con firma PNG**. Lo mismo con otros 21 destinos que ImageMagick y GraphicsMagick declaran
saber escribir:

```
b  c  g  k  m  o  r  y  p7  preview  clipboard  data  flif  group4
histogram  inline  msl  mvg  null  pocketmod  sparse  vid
```

**Es literalmente el fallo nº 1 del catálogo de `HUECOS.md` —un PNG entregado con otra extensión y
estado «Done»— producido por un motor de primera línea, 22 veces, en la misma sesión.**

| | Contrato de 5 puntos, vocabulario **viejo** | Vocabulario **nuevo, solo por firma** | Con la regla **G6** |
|---|---:|---:|---:|
| Detectados de 22 | **0** (los 22 salen `ok_parcial`) | **0** (los 22 salen `ok_parcial`) | **22** (los 22 salen `aviso`) |

**Y el resultado intermedio es el que hay que subrayar, porque refuta la hipótesis con la que empecé:
ampliar el vocabulario NO atrapa este caso.** Para atrapar `.group4` por firma haría falta saber qué
firma esperar de `.group4`, y `.group4` es datos CCITT crudos: **no tiene ninguna**. Los otros 21 ni
siquiera son formatos de fichero: son pseudoformatos de ImageMagick.

**La regla que sí lo atrapa no necesita saber nada del destino:**

> **G6 — la salida tiene la MISMA firma que la entrada y no era eso lo que se pedía.**
> Se dispara cuando (a) la extensión de destino no está en la tabla, (b) la firma de la salida es un
> nombre de formato reconocido, y (c) coincide con la firma de la entrada, con otra extensión.
> **Cuesta 0: las dos firmas ya están calculadas.** Severidad **`aviso`**, no `fallo`: prueba que es
> sospechoso, no que sea incorrecto.

Sobre las 53 del patrón oro **G6 no se dispara ni una vez** (sus 53 destinos están en la tabla) y sobre
las 345 salidas legítimas de §6.2 se dispara **exactamente en los 12 casos en los que ImageMagick
entrega un PNG**. **MEDIDO.**

**Consecuencia para el catálogo, que es donde de verdad se arregla esto:** estas 22 aristas son
nominales y **hay que borrarlas de la cobertura declarada**, no verificarlas mejor. Es la consecuencia
nº 3 de `aristas-nominales.md` §9 —*«o FileX guarda la geometría fuera del fichero, o esos formatos no
son formatos y hay que borrarlos del catálogo»*— aplicada a otra familia.

### 7.2 El punto ciego del crudo sin cabecera — **MEDIDO**

`corpus/imagen/tipico.png` reducido a 64×48 y escrito a `.rgb`:

| Medida | Valor |
|---|---|
| Bytes del `.rgb` | **18 432** = **6,00 bytes por píxel** → profundidad derivada **16 bits** (este ImageMagick es Q16-HDRI) |
| Releído con `-size 64x48 -depth 16` | **1 fichero**, RMSE frente al original **0** |
| Releído con `-size 64x48 -depth 8` | **2 ficheros** (`-0.png` y `-1.png`), RMSE **0,359972** — píxeles basura |

Dos cosas, y las dos importan:

1. **La trampa 23 de CLAUDE.md se reproduce en la mitad que dice que el resultado es basura** (RMSE
   0,36) **y hay que matizarla en la otra:** con el PNG de origen como referencia, **el contrato SÍ lo
   atrapa**, por el punto 4 (`I4 · DEGRADACIÓN DE PROFUNDIDAD no pedida ni inevitable`), porque la
   entrada es de 16 bits y la salida sale de 8. Y **`magick` escribe DOS ficheros**, que es un hallazgo
   del punto 5. **Lo que pasa los cuatro puntos es el caso en el que la referencia es el propio crudo**,
   y ahí el contrato no tiene con qué comparar: es el escenario de `bench/invocacion-aristas.md` §4.1.
2. **Y ese escenario es el que deja al descubierto el problema de verdad.** Verificando el `.rgb` en sí:

```
CONTRATO   punto1 = no_aplica
  [p1 G4 informativo] el formato no tiene marcador (pixeles crudos sin cabecera):
                      el punto 1 NO APLICA a .rgb
```

**El verificador declaraba `1_firma: True`, `3_propiedades: True` y `4_pedido: True` sobre un fichero
del que no había leído absolutamente nada**, porque la sonda no devuelve *error* con un crudo: devuelve
`categoria: "desconocida"`, y la cobertura solo miraba si había error. **Corregido**: los puntos 3 y 4
solo cuentan como cubiertos si la sonda llegó a clasificar el fichero.

> ### La respuesta, en una frase
>
> **Los formatos sin firma son exactamente aquellos en los que el contrato es más débil, y no por
> casualidad: la misma ausencia de cabecera que impide el punto 1 impide los puntos 2 y 3, porque los
> tres se alimentan de lo mismo.** Lo que queda en pie para la categoría 3 es el **punto 4** —pedido
> frente a obtenido, y solo para lo que el pedido declare—, el **punto 5** —dónde escribió el motor— y
> **G6**. Para el contenido hace falta **fidelidad**, que es la conclusión que
> `contrato-quinto-punto.md` §4.4 ya había acotado por otra puerta.

**Es un hallazgo, no un inconveniente:** dice dónde hay que gastar el esfuerzo. Para los 90 formatos sin
marcador, invertir en vocabulario no compra nada; invertir en **pasar la geometría fuera del fichero**
(la propuesta de `aristas-nominales.md` §9.3) y en **derivar la profundidad de bytes ÷ píxeles** compra
todo.

---

## 8. Dos fallos del propio verificador, encontrados al medir

**Ninguno estaba en el encargo. Los dos salieron de ejecutar.**

### 8.1 `csv.Error` no es subclase de `ValueError` — **MEDIDO, y tumbaba el proceso**

Al reejecutar la muestra de E1, el proceso murió con:

```
File "bench/scripts/verificador.py", line 1280, in _datos
    filas = list(csv.reader(io.StringIO(texto, newline="")))
_csv.Error: field larger than field limit (131072)
```

Lo dispara una salida **real**: el «TXT» de ImageMagick, que es la enumeración de los píxeles —el mismo
que E1 §6 midió en **156 520 548 bytes desde 91 324**—. `sondear_en_proceso` captura
`(OSError, struct.error, IndexError, ValueError)` y **`_csv.Error` no está en esa jerarquía**, así que
la excepción se escapaba entera. **Un verificador que muere no es un verificador que dice «no sé».**
Corregido en los dos sitios (`_datos` devuelve el error como dato; `sondear_en_proceso` captura
`csv.Error`).

### 8.2 El `.html` que se clasificaba como CSV

`contrato-quinto-punto.md` §3.1 lo dejó anotado: *«la sonda no tiene vocabulario para HTML, lo clasifica
como CSV y dispara `[p3 D2 fallo] número de campos no constante`. Es un falso positivo que acierta por
casualidad. Material para C14.»* Cerrado: `xml`, `html`, `svg`, `postscript` y `rtf` tienen ahora firma
propia y categoría `documento`, y **no pasan por el analizador de CSV**. La familia de texto que sí es
tabular (`texto`, `im_texto`) sigue yendo a `_datos`.

---

## 9. Coste de implementación

`bench/scripts/verificador.py` pasa de **4 185 a 4 792 líneas** (+607 netas), y **sigue sin una sola
dependencia externa**.

| Bloque | Qué es |
|---|---|
| Tabla `FIRMAS` (14 → 116 entradas) y `MARCAS_FTYP` (14 → 39) | los mágicos, todos con su cabecera medida detrás |
| `_firma_zip`, `_firma_cfb`, `_firma_texto`, `MARCAS_TEXTO` | el refinamiento de envases y de texto |
| Los cuatro predicados (PNM, PCX, MPEG-TS, MPEG audio/ADTS) | marcadores que son un conjunto, no una constante |
| `EXT_A_FIRMAS` (26 → 338), `EXT_SIN_FIRMA` (112), `EXT_FAMILIA` (28) | **la parte que decide si el punto 1 dispara** |
| `punto1_estado()`, hallazgos `G4`/`G5`/`G6`, cobertura honesta de `1_firma`/`3_propiedades`/`4_pedido` | las tres respuestas en vez de dos |
| `csv.Error` en `_datos` y en `sondear_en_proceso` | §8.1 |

**Lo que se repite por cuarta vez en este verificador:** el grueso no es la lógica de la regla —el
punto 1 sigue siendo una comparación de conjuntos— sino **fabricar el acceso al dato y, sobre todo,
saber qué esperar**. Aquí la parte cara no fue el código: fueron los **423 formatos escritos dos o tres
veces** que hacen que cada línea de la tabla tenga una medida detrás.

---

## 10. Lo que este informe deja **PENDIENTE**

1. **Los 86 destinos indeterminados**: 79 que ningún motor de esta máquina escribe y 7 más donde la
   muestra describe al escritor y no al formato. Cerrarlos exige o el corpus FATE de ffmpeg (el mismo
   PENDIENTE nº 1 de `aristas-nominales.md` §11) o un segundo escritor por formato.
2. ~~**Los 12 de la deuda restante** (§3.2), cada uno con su motivo. Los dos accionables son `pict` y
   `pcd`: bastaría leer más allá del byte 512 **solo cuando la extensión lo pide**.~~ **CORREGIDO el
   03/09/2026 por worker2 (ronda 6), sobre lo que ya midió F2 el 28/08:** la puerta *«solo cuando la
   extensión lo pide»* está refutada con número — `bench/firmas-cierre.md` §2.3 mide que
   `open+read(2056)` frente a `open+read(512)` sobre los mismos 78 ficheros da **64,75 y 77,9 µs por
   fichero**, la diferencia sale **negativa** (por debajo del suelo de la tanda), y en cambio la puerta
   le costaría a `firma_real` su invariante de que la extensión NO decide la respuesta. **Se lee
   siempre** (`filex/verificador.py`, `_NCAB_LARGO = 2056`, comentario junto a la constante). Los dos
   accionables (`pict`, `pcd`) están **CERRADOS** desde el 28/08 (`pruebas/test_firmas_cierre.py::MarcadoresMasAllaDel512`).
3. ~~**`.pcd` se clasifica hoy como `mpegaudio`** porque sus 2 KB de relleno `0xFF` casan con el
   sincronismo de trama. No produce falso positivo —`.pcd` no está en la tabla— pero está declarado.~~
   **REFUTADO el 22/08 por `bench/hito3-mudanza.md` §6.2, y CERRADO el 28/08 por F2** — la cifra vieja
   se deja tachada, no se borra (trampa 44: un campo honesto al lado de una nota falsa se lee como una
   respuesta honesta). *«No produce falso positivo»* era **falso**: un `png→pcd` legítimo de este
   ImageMagick (`rc=0`, 788 480 B) daba `veredicto: FALLO`, porque la firma `mpegaudio` no se queda en
   el punto 1 — **contamina la CATEGORÍA**, y la categoría manda el fichero a la sonda de audio, que
   encuentra `duración = None` y dispara `G4` con severidad `fallo`. `.pcd` ya no está fuera de la
   tabla: tiene marcador propio en `FIRMAS_LARGAS` (byte 0x800, `PCD_IPI`) desde el 28/08, y
   `filex/verificador.py` lo verifica de nuevo el 03/09/2026 sobre un fichero real
   (`bench/pcd-y-memoria.md` §1): `veredicto: ok_parcial`, sin un solo `fallo`.
4. **La colisión TGA/CUR**: los dos empiezan por `00 00 02 00`. No hay falso positivo porque `.tga` no
   tiene marcador, pero un TGA con extensión `.cur` pasaría. **CONFIRMADO EN EJECUCIÓN el 22/08**
   (`bench/hito3-mudanza.md` §6.3: un TGA real de `magick`, entregado con extensión `.cur`, pasaba
   `evaluado` con **cero hallazgos** — indistinguible de un cursor auténtico) **y CERRADO el
   03/09/2026 por worker2 (ronda 6):** un CUR válido no puede declarar 0 imágenes (bytes 4-5), y
   `00 00 02 00 00 00` —justo lo que escribe `magick` para un TGA sin ID ni mapa de color— es ese caso
   imposible. Misma forma que el par JBIG/ICO que ya existía dos líneas más arriba en `FIRMAS`. Ahora
   `firma_real` devuelve `desconocido` para ese patrón y el punto 1 dispara `G3 fallo`
   (`bench/pcd-y-memoria.md` §2, `pruebas/test_firmas_cierre.py::TGAEntregadoComoCUR`).
5. **G6 está calibrada sobre 22 casos de un solo motor.** Es `aviso` a propósito. Subirla a `fallo`
   exige medirla sobre más motores y comprobar que no marca conversiones legítimas de formato a formato
   equivalente (`png` → `apng`, `mkv` → `mka`).
6. **El nivel de familia no se ha llevado al veredicto.** Hoy `G5` es `informativo` y la cobertura
   cuenta la comprobación de familia como cubierta. Una lectura más estricta las dejaría en
   `ok_parcial`, igual que discutió `verificador-ghostscript.md` §2.4 para V5.
7. **La verificación del censo dentro del contenedor** solo guardó 64 bytes de cabecera por muestra, así
   que la prueba ancha de falsos positivos (§6.2) cubre **los 385 destinos locales**, no los 162 del
   contenedor. Repetirla dentro exigiría llevar el verificador allí.
8. ~~**`_datos` lee el fichero entero en memoria.** Con el TXT de 156 MB de ImageMagick eso son 156 MB
   de RAM para contar comas. Está fuera del encargo y queda apuntado.~~ **LA CIFRA ERA FALSA — MEDIDO
   el 22/08 por `bench/hito3-mudanza.md` §6.1, y CERRADO el 03/09/2026 por worker2 (ronda 6).** No es
   ×1: era **×21,3** en la rama normal (×7,0 en la degradada), y el culpable no era el `fh.read()`
   sino `d["csv_filas"] = filas` — la lista de listas de `str`, una por CAMPO, que se quedaba dentro de
   la sonda. Sobre el TXT de 156 520 548 B de ImageMagick eran **≈1,1 GB de pico**, no 156 MB.
   **Arreglado:** ninguna regla del contrato lee las filas en sí —solo los cuatro agregados que ya
   publicaba `_datos` (`csv_n_filas`, `csv_n_campos_por_fila` para D2, `csv_cabecera`, `filas_datos`
   para D1)—, así que ahora se calculan en un solo recorrido de `csv.reader` sin materializar la lista
   completa. **MEDIDO de nuevo tras el arreglo** (`bench/pcd-y-memoria.md` §3,
   `bench/salidas-pcd-y-memoria/datos_ram.json`): el pico baja de **×21,3 a ×6,2** sobre un CSV de 32 MB
   (207 280 691 B de pico), reproducible al MiB entre corridas. La rama degradada (`csv.Error`, la del
   TXT de ImageMagick) no cambia —nunca llegó a materializar `filas`— y se queda en ×7,0-7,5.

---

## 11. Para quien consolide — qué cambia en los documentos maestros

**No he tocado ningún maestro** (los lleva D3 en paralelo). Esto es lo que hay que llevarse:

| Documento | Qué dice hoy | Qué hay que añadir | Fuente aquí |
|---|---|---|---|
| `ESTADO-Y-REPARTO.md` §3.C | **C14** abierto: «ampliar el vocabulario de firmas (hoy 24 nombres)» | **CERRADO.** 24 → 147 nombres, 26 → 338 extensiones, y una tercera tabla de 112 extensiones **sin marcador**. El punto 1 pasa del 12,4 % al 54,2 % de los destinos de la muestra de E1, con **0 falsos positivos sobre las 53** | §4, §5, §6.1 |
| `aristas-nominales.md` §9.5 | «la verificación por firma solo cubre el 12 % de los destinos… si FileX declara 500 formatos de salida tiene que poder verificar 500 firmas — o declarar menos» | **Matizar con la medida: no se pueden verificar 500 firmas porque no existen 500 firmas.** De 381 formatos con veredicto, **90 (23,6 %) no tienen marcador**. La frase correcta es *«o verifica las que existen y declara «no aplica» en las que no, o declara menos»* | §3 |
| `aristas-nominales.md` §11.3 | «ampliar el vocabulario solo puede subir el 50,5 %, nunca bajarlo» | **Sigue siendo cierto y ahora tiene número, pero no llega por donde se esperaba.** Por firma el punto 1 nuevo dispara `fallo` en **0** de las 598 (el viejo, en 1, y esa detección se pierde por ser más honestos). Quien sube la cifra es **G6: 19 aristas, 17 de ellas que E1 contó como REALES** | §5.2, §5.4 |
| `HUECOS.md` §1 (fallos documentados) | el fallo nº 1 es «un PNG entregado con extensión `.avif`» | **Reproducido con un motor de primera línea y 22 destinos a la vez:** `magick x.png y.group4` devuelve rc=0 y entrega un PNG. **Ni el vocabulario viejo ni el nuevo lo atrapan por firma**; lo atrapa G6 | §7.1 |
| `PLAN-ORQUESTADOR.md` §5 (reglas de diseño) | «Verificar la salida siempre. Firma real, flujos, propiedades declaradas, pedido frente a obtenido, y que no escribió fuera» | **Añadir el matiz medido: el punto 1 no aplica al 23,6 % de los formatos, y ahí tampoco aplican los puntos 2 y 3, porque los tres se alimentan de la cabecera.** Para la categoría 3 quedan el punto 4, el punto 5 y G6 | §7.2 |
| `PLAN-ORQUESTADOR.md` §4.2 | el contrato declara el punto 1 | **La cobertura tiene que ser honesta: `1_firma` valía `True` en el 100 % de los ficheros evaluando el 12 %.** Ahora hay cuatro estados: `evaluado` / `familia` / `no_aplica` / `sin_vocabulario` | §2.1 |
| `analysis/00-matriz-formatos.md` | «896 formatos de entrada, 503 de salida» | **La reextracción con el mismo parser de E1 da 895 y 502.** La diferencia de uno en cada columna no se ha localizado y se declara | §1 |
| `contrato-quinto-punto.md` §3.1 | «la sonda clasifica un `.html` como CSV: material para C14» | **Cerrado.** `xml`, `html`, `svg`, `postscript` y `rtf` tienen firma y categoría propias | §8.2 |
| `verificador-ghostscript.md` §5.9 / metodología | — | **Fallo nuevo del verificador: `csv.Error` no es subclase de `ValueError` y tumbaba el proceso sobre el TXT de 156 MB de ImageMagick. Corregido** | §8.1 |
| Metodología (todos) | dos testigos de ruido | **Un tercer sesgo de medición, y no es de ruido: el de la SEMILLA.** Con dos semillas de markdown que empiezan por un título, 42 formatos de pandoc parecían tener marcador; con una tercera que empieza por prosa, ninguno lo tiene | §2.3 |

---

## 12. Índice de datos crudos

En `bench/salidas-firmas/`, con su `MANIFIESTO.md`: **~2 MB, todo texto**, 17 instrumentos, 15 `.json`
de resultados y 13 logs, con la orden exacta que reproduce cada uno. Nada binario versionado: los 423
formatos escritos, las 598 aristas reejecutadas y las semillas viven en un directorio desechable
(`F1_TMP`) y se borran al terminar.

**Metodología.** Medianas, nunca medias; n=9 en todo coste unitario. Calentamiento antes de cada tanda.
**Dos testigos de ruido** —CPU monohilo para la deriva, lanzamiento de proceso para el nivel—, con
**tope de 20 s en el segundo**, umbral del 20 % en los dos. Las tandas de coste salieron `SUCIA` con
nivel ×1,20–1,31, que es lo estructural de esta máquina con la sesión remota activa y dos agentes más
trabajando. **No se ha usado la GPU ni se ha pedido su lock. No se ha tocado `corpus/`, `repos/`,
`bench/salidas-referencia/referencia.json`, `bench/salidas-aristas/` (solo lectura), ningún arnés
compartido, ninguna variable de entorno del sistema, ni ningún documento maestro. La raíz del
repositorio quedó limpia.**
