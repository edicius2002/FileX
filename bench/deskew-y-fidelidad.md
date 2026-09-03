# B8 — `-deskew 40%` sobre la familia d4, y dos cierres de la ronda 8 (C18, B8-a)

worker1, carril GPU, `edicius2002/filex-gpu`. Continuación tras un cuelgue de máquina a
mitad de tanda (ver `ENCARGO-R8b.md`): el trabajo de la sesión anterior — 20 rásteres,
la tanda de Tesseract completa — se commiteó primero, sin repetir nada, en `95c9fc4`.
Esta sesión añade la tanda de RapidOCR que faltaba y cierra `C18` y una parte de `B8(a)`.

**Todo MEDIDO salvo donde se indica `PENDIENTE`.**

- Datos crudos: `bench/salidas-deskew-y-fidelidad/json/{b8_tesseract,b8_rapidocr,c18_repro_i1}.json`
- Instrumentos: `raster_b8.py`, `b8_tesseract.py`, `b8_rapidocr.py`, `c18_repro_i1.py`
  (todos reproducibles, ver `MANIFIESTO.md`)
- Salidas de texto: `bench/salidas-deskew-y-fidelidad/texto/`

---

## 1. `-deskew 40%` × Tesseract × RapidOCR sobre `escaneado_d4*`

### 1.1 La tabla completa (200/280 ppp, base/deskew, dos motores)

| documento | ppp | Tesseract base | Tesseract deskew | Δ tess | RapidOCR base | RapidOCR deskew | Δ rapid |
|---|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d4` | 200 | 51,3 | **100,0** | +48,7 | 18,6 | 19,5 | +0,9 |
| `escaneado_d4` | 280 | 91,6 | **100,0** | +8,4 | 28,9 | **18,5** | **−10,4** |
| `escaneado_d4a` | 200 | 0,2 | 0,2 | 0,0 | 7,4 | **0,2** | **−7,2** |
| `escaneado_d4a` | 280 | 0,2 | 0,3 | +0,1 | 0,3 | 0,3 | 0,0 |
| `escaneado_d4b` | 200 | 0,5 | 0,2 | −0,3 | 0,3 | 0,3 | 0,0 |
| `escaneado_d4b` | 280 | 0,2 | 0,2 | 0,0 | 0,3 | 0,3 | 0,0 |
| `escaneado_d4c` | 200 | 1,8 | **100,0** | +98,2 | 1,2 | 0,7 | −0,5 |
| `escaneado_d4c` | 280 | 1,7 | **100,0** | +98,3 | 9,6 | 8,1 | −1,5 |
| `escaneado_d4e` (*) | 200 | 100,0 | 100,0 | 0,0 | 77,5 | **49,7** | **−27,8** |
| `escaneado_d4e` (*) | 280 | 100,0 | 100,0 | 0,0 | 88,6 | **52,9** | **−35,7** |

(*) `escaneado_d4e` ya sale a 100,0 % CER en base con los dos motores tratándose de Tesseract,
y a 77,5–88,6 % con RapidOCR: su Δ de Tesseract es **efecto suelo, no evidencia de
neutralidad** (aviso ya señalado antes de esta sesión). Con RapidOCR, en cambio, la base
**no** está en el suelo (77,5/88,6, no 100,0), así que su Δ negativo grande **sí** es
comparable: es la mejora más grande de toda la tabla.

n=3 por celda en las dos tandas, **determinismo 100 % (20/20 Tesseract, 20/20 RapidOCR)**,
`rc` registrado por celda. La tanda de RapidOCR salió etiquetada **`limpia`** (testigo
monohilo: deriva ×0,66; testigo de proceso: nivel ×1,20 sobre el umbral de referencia),
165,7 s, lock de GPU tomado y liberado para toda la tanda.

### 1.2 Lo que cambia con el segundo motor

**`-deskew 40%` es catastrófico solo en Tesseract, y solo en 3 de las 10 celdas no-suelo.**
Con RapidOCR, sobre las mismas 20 imágenes, **`-deskew` nunca produce silencio ni una
subida a 100 %**: en 8 de 10 pares no-`d4e` el efecto es nulo o pequeño (±10,4 puntos como
máximo, casi siempre bajo 1 punto), y en `d4e` **mejora** de forma grande y consistente
(−27,8 y −35,7). Esto confirma la trampa 78 tal y como la anticipaba el encargo: *«un
umbral/hallazgo calibrado con un solo motor describe a ese motor»*. **El hallazgo correcto
no es "`-deskew` destruye la lectura", es "`-deskew` + `Tesseract --psm 3` destruyen la
lectura en 3 de 10 casos, y en el resto son neutrales o irrelevantes"**. Con RapidOCR el
signo predominante es el contrario: ayuda.

No se puede separar todavía si el efecto es de `--psm 3` en particular (frente a otros
`--psm` de Tesseract) — eso sigue sin barrerse aquí y coincide con lo que ya avisaba
`psm-y-rasterizador.md`: la interacción `--psm`×preprocesado no es del todo transferible.
**PENDIENTE** si se quiere afinar más allá de «es cosa de Tesseract, no del preprocesado en
general».

### 1.3 El `pHYs`: descartado como mecanismo — MEDIDO

El aviso del encargo era concreto: si `-deskew` cambia lo que `magick` declara en el
`pHYs`, y ese metadato es justo el que mueve a Tesseract hasta 47 puntos (trampa 29), el
hallazgo cambiaría de nombre. Comprobado con `magick identify -format "density=%x,%y
units=%U"` sobre pares base/deskew de `d4`, `d4c` y `d4e` a 200 ppp:

```
escaneado_d4__ppp200__base.png    -> density=78.74,78.74  (= 200 px/in)
escaneado_d4__ppp200__deskew.png  -> density=78.74,78.74  (= 200 px/in)
escaneado_d4c__ppp200__deskew.png -> density=78.74,78.74
escaneado_d4e__ppp200__deskew.png -> density=78.74,78.74
```

**El valor declarado es idéntico, bit a bit, entre base y deskew, y es el nominal
verdadero** (`raster_b8.py` ya lo fuerza explícitamente con `-units PixelsPerInch -density
N` después del `-deskew`, como pedía el encargo). `-deskew 40% +repage` rota y agranda el
lienzo (`escaneado_d4` pasa de 1294×1716 a 1413×1804 a 200 ppp) pero **no resamplea la
escala de píxel**, así que el `pHYs` sigue siendo cierto tras el giro. **Se descarta el
`pHYs` como mecanismo de las tres celdas catastróficas**: la causa está en otra parte —
probablemente el análisis de maquetación de `--psm 3` sobre un lienzo mayor con bordes en
blanco nuevos por la rotación — y **eso sí queda PENDIENTE** de aislar.

---

## 2. B8 parte (a) — R1 sobre PDF que no son «una imagen a página completa»

### 2.1 Qué es R1, citado

`R1` en este contexto **no** es la lista blanca de raíces de las reglas de diseño (§5 de
`CLAUDE.md`). Es la regla de resolución de OCR de `bench/ocr-ppp-nativos.md` §9:

```
R1 — Leer los ppp nativos, no suponerlos. Techo de x1,4.
ppp_nativos = ancho_imagen_px / (ancho_pagina_pt / 72)
ppp_ocr     = clamp(ppp_nativos, 100, ppp_nativos * 1.4)
```

Y el propio §9 ya declara, en su lista de PENDIENTES, los casos que no cubre: **«páginas
con varias imágenes, imágenes que no ocupan la página entera, PDF con texto vectorial
mezclado con escaneo, y PDF sin ninguna imagen incrustada»**. `B8(a)` es medir qué pasa en
esos casos.

### 2.2 Censo del corpus — MEDIDO

Con `pypdfium2.PdfDocument(...).get_objects()` sobre los 23 PDF de `corpus/pdf/`:

| categoría | cuántos | ejemplos |
|---|---:|---|
| una sola imagen, a página completa | **21** | todos los `escaneado_*`, `patologico_*`, `realista_*`, y `trivial.pdf` |
| sin ninguna imagen (solo texto vectorial) | **1** | `tipico_texto.pdf` (4 objetos de texto, 0 de imagen) |
| varias imágenes / imagen parcial / texto+escaneo mezclados | **0** | — |

**El resultado es el hallazgo**: los tres casos más interesantes de la lista PENDIENTE de
R1 —varias imágenes, imagen que no cubre la página, texto vectorial mezclado con escaneo—
**no tienen ni un representante en el corpus actual**. No es que la medición fallara: es
que **no hay nada que medir con lo que existe**. Construir esos tres documentos es trabajo
de corpus nuevo (como B15/B21 en su día), no cabe en esta sesión y se declara así en vez de
forzar un barrido sobre lo que hay. **PENDIENTE**, con el motivo exacto: falta corpus.

### 2.3 El caso que sí es medible: «PDF sin ninguna imagen» — MEDIDO

`tipico_texto.pdf` sí es un representante real del cuarto caso pendiente de R1. Aplicar la
fórmula literalmente sobre él:

```python
imgs = [o for o in page.get_objects() if o.type == FPDF_PAGEOBJ_IMAGE]
# imgs == []  -- página de 595x842 pt, 4 objetos de TEXTO, 0 de imagen
ancho_imagen_px = imgs[0].get_px_size()[0]   # IndexError: list index out of range
```

`R1` **no puede ejecutarse**: `ancho_imagen_px` no existe porque no hay imagen de la que
leerlo. Con la implementación más directa (indexar la lista de imágenes), el modo de
fallo es un `IndexError` — **ruidoso, no silencioso**: no hay ningún código publicado hoy
en `filex/` que llame a esta fórmula (se buscó `ppp_nativos` y `R1` en `filex/*.py`, cero
resultados), así que no hay todavía un comportamiento en producción que corregir, pero
**si se implementa R1 alguna vez, necesita una rama explícita para «0 imágenes» antes que
la aritmética**, porque el fallo por defecto de Python en ese camino es un traceback, no un
número silenciosamente malo. Es una precisión menor pero concreta a favor de una futura
implementación: **el `IndexError` es preferible a inventar un valor**, así que no hace
falta «arreglarlo» tanto como declarar el caso aparte (ej. usar `R2` de extracción directa
del texto vectorial, que es justo la vía que sí existe para PDF sin escaneo).

---

## 3. C18 — el 99,0 % de I1 se reproduce con sus parámetros literales — MEDIDO, REFUTA `verificador-ghostscript.md` §5.7

`verificador-ghostscript.md` §5.7 declaró el 99,0 % de I1 (`fidelidad-caminos.md` línea 196)
**NO REPRODUCIDO** (94,7–97,1 % con tres lecturas propias) y atribuyó la brecha a que
*«aquel informe no publica ni los ppp de su rasterizado ni el idioma de OCR ni su fórmula
de similitud»*. **Esa premisa es falsa: los tres parámetros están en el código versionado**,
en `bench/salidas-fidelidad/_caminos.py` y `_clasifica.py`, que **no fueron leídos** antes
de reintentar la reproducción con valores supuestos.

### 3.1 Los tres parámetros, citados

- **ppp de rasterizado**: `P150 = {"dev": "png16m", "extra": ["-r150"]}` — pero **solo en
  el primer paso**. I1 son tres pasos, no uno: `("gs","png",P150) -> ("im","pdf",{}) ->
  ("gs","txt",OCR)`. El segundo paso reempaqueta el PNG en un PDF **sin ninguna bandera de
  densidad**, y el tercero (`OCR = {"dev": "ocr"}`) **no lleva `-r`**: el dispositivo `ocr`
  de Ghostscript procesa ese PDF intermedio a su resolución por defecto, no a 150.
  Aplicar «150 ppp» a un solo paso de rasterizado+OCR, como hizo la reproducción de
  `verificador-ghostscript.md`, **no es el mismo camino**.
- **idioma de OCR**: `ENV_GS = dict(os.environ, TESSDATA_PREFIX=r"C:\Program
  Files\Tesseract-OCR\tessdata")` — ese directorio **solo trae `eng`+`osd`** (§0.1 de
  `fidelidad-caminos.md`, ya documentado). Sin `-sOCRLanguage=`, el dispositivo usa `eng`
  por defecto. No hay que elegir entre `eng`/`spa`: **solo `eng` es posible** con ese
  `TESSDATA_PREFIX`.
- **fórmula de similitud**: `_clasifica.py:similitud()` — normaliza los dos textos con
  `_norm(s) = re.sub(r"[^0-9a-zA-Z]", "", s).lower()` (quita **todo** lo que no sea
  alfanumérico, espacios incluidos) y calcula `sum(bloque.size for bloque in
  SequenceMatcher(None, ta, tb).get_matching_blocks()) / len(ta)` — cobertura del texto
  ORIGEN dentro del destino, no un ratio simétrico y no un CER.

### 3.2 Reproducción literal — MEDIDO, n=3, determinista

`c18_repro_i1.py` ejecuta los tres pasos exactos sobre `corpus/pdf/tipico_texto.pdf`
(entrada real de I1) y aplica la fórmula exacta:

```
paso1: gswin64c -sDEVICE=png16m -r150                    (rasteriza el PDF original)
paso2: magick <png> <pdf>                                 (reempaqueta, sin flags)
paso3: gswin64c -sDEVICE=ocr  (TESSDATA_PREFIX=...\Tesseract-OCR\tessdata, sin -r)
```

Texto original (extraído con `txtwrite`, la misma vía que usa `_sonda.texto()` para PDF):

```
     FileX - documento de prueba con texto seleccionable
     Segunda linea: acentos aeiou n ˆ y simbolos % & @
     Tabla:  Col A    Col B    Col C
             1        2        3
```

Texto OCR (paso 3, idéntico bit a bit en 3/3 repeticiones — `sha256`
`8566eafd…` en las tres):

```
FileX - documento de prueba con texto seleccionable
Segunda linea: acentos aeiou n” y simbolos % & @
Tabla: ColA ColB ColG

1 2 3
```

`similitud() = 0,9896907216494846` → `f"{sim:.1%}"` = **`99.0%`** — el mismo formato de
una cifra decimal que usa `_clasifica.py` línea 111. **Coincide exactamente con la cifra
publicada**, y el error que produce la diferencia de 3 caracteres sobre 97 es **el mismo
`ColC → ColG`** que `fidelidad-caminos.md` §d ya documentaba de memoria (ahí escrito como
«`ColC` → `GolG`» — la letra que cambia es la misma, la tercera de la fila de columnas).

### 3.3 Veredicto

**C18 queda CERRADO como REPRODUCIDO, no como NO REPRODUCIDO.** El 99,0 % de I1 es
correcto y se reproduce de forma determinista con los parámetros literales del propio
código versionado del proyecto. La corrección no es sobre `fidelidad-caminos.md` —esa
cifra estaba bien—, es sobre `verificador-ghostscript.md` §5.7: su «no reproducido» nació
de reconstruir el camino a ojo (una sola rasterización a 150 ppp, con OCR aplicado
directamente y probando `eng`/`spa`) en vez de leer los tres pasos reales, que rasterizan
una vez a 150 y dejan que el paso de OCR final corra a su resolución por defecto, con
`eng` como único idioma posible. **Es la trampa 66/79 otra vez: una cifra de control
ajena se reprodujo sin comprobar primero si el camino ejecutado era el mismo que el
código real ejecuta.**

No se reescribe `verificador-ghostscript.md` en esta sesión (no es mío: es de worker2 /
otra rama de trabajo de la ronda anterior); se deja esta nota y el script reproducible
como evidencia para quien lo cierre allí.

---

## 3.4 Verificación de la ronda: suite y `ci/integridad.py`

- `ci/integridad.py`: **`Todo en orden`** (`.venv-mcp-filex`, Python 3.11.9). Se registró
  este informe en `ESTADO-Y-REPARTO.md` (comprobación `informes-registrados`, que
  inicialmente fallaba porque `bench/deskew-y-fidelidad.md` no estaba citado) y se
  corrigió el recuento de emojis de la tabla tras mover `B8` (🔴→🟡) y `C18` (🔴→🟢):
  `6 ⚫ · 12 🔴 · 11 🟡 · 88 🟢` → `6 ⚫ · 10 🔴 · 12 🟡 · 89 🟢`.
- `pytest pruebas/ -q`: **452 passed, 3 skipped, 127 subtests, 2 failed** en 366,1 s
  (`.venv-mcp-filex`, Windows, Python 3.11.9). **Los 2 fallos no son míos y son de
  contención, no de código — MEDIDO**: durante la tanda la CPU estaba al **94-96 %**
  (worker2 corriendo `C25` en paralelo en el carril CPU) y `git status --porcelain --
  filex/ pruebas/` confirma **cero cambios míos** en esos directorios esta sesión.
  Repetidos en aislado con la CPU ya más tranquila, **los dos pasan** (`2 passed in
  12,11 s`): `test_cancelacion.py::ContenedorReal::test_cancelar_mata_el_contenedor_y_no_solo_el_cliente`
  y `test_cancelacion_procesos.py::DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra`.
  **Esto AMPLÍA la trampa 101**: aquella midió exactamente `test_cancelacion_procesos`
  fallando 2/2 bajo contención (544 s frente a 160, CPU ~50 %) y limpio en tres pasadas
  repetidas; hoy, con CPU aún más alta (94-96 %), **el mismo patrón alcanza también a
  `test_cancelacion.py`**, que no estaba entre los afectados de aquella medida. No se
  toca ninguna aserción: son pruebas de cancelación con esperas por reloj de pared, y
  bajo contención esas esperas expiran. **No relacionado con el trabajo de esta
  sesión** (`bench/`, `ESTADO-Y-REPARTO.md`, `.gitignore`).

## 4. Estado de la máquina y las cuatro declaraciones

- **Intérprete**: `.venv-mcp-filex` (Windows, Python 3.11.9) para todo lo que toca
  `filex.gpu`; `.venv-ai` (Windows, Python, torch 2.6.0+cu124, CUDA disponible) para
  RapidOCR, porque `rapidocr`/`torch` no están en `.venv-mcp-filex`. Tesseract y
  Ghostscript se invocan como binarios nativos, sin venv.
- **Entorno**: GPU limpia al empezar (lock libre, 9 161 MiB libres de 12 288, línea base
  de escritorio ~2 955–3 061 MiB, consistente con lo documentado). La tanda de RapidOCR
  tomó y liberó el lock (`gpu.Lock("B8-rapidocr")`) para sus 20 celdas y salió etiquetada
  `limpia`. **Docker no se usó en esta sesión** (ninguno de los tres bloques necesita
  contenedor). Al terminar, el lock lo tiene otro proceso (`dueno: "prueba-c38"`, VRAM en
  línea base ~3 061 MiB) — no es mío, es compatible con el trabajo de lock del carril
  paralelo mencionado en el encargo (C38/N30).
- **Qué quedó fuera**: el barrido de `--psm` sobre las tres celdas catastróficas (§1.2,
  PENDIENTE); los tres sub-casos de R1 sin representante en el corpus (§2.2, PENDIENTE,
  motivo: falta corpus, no falta medición); reescribir la corrección de C18 dentro de
  `verificador-ghostscript.md` (no es mi fichero).
- **No se tocó** ningún fichero de worker2 (`verificador.py`, `motores.py`, `api.py`,
  `nucleo.py`, `huella.py`, `sondeo.py`, `verificador-ghostscript.md`).

## 5. Ficheros de esta sesión

- `bench/salidas-deskew-y-fidelidad/b8_rapidocr.py` — ejecutado, `json/b8_rapidocr.json`,
  `texto/rapidocr__*.txt` (20 ficheros).
- `bench/salidas-deskew-y-fidelidad/c18_repro_i1.py` — nuevo, `json/c18_repro_i1.json`.
- `bench/deskew-y-fidelidad.md` — este informe.

**Commiteado en `edicius2002/filex-gpu`. No se ha empujado ni abierto PR.**
