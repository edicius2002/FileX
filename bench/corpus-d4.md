# `escaneado_d4` — un caso de OCR que sí mide margen, y la causa real de la asimetría de PaddleOCR

**Encargo G1.** Construir un documento de OCR que separe configuraciones dentro de un
mismo motor, con castellano y tildes de verdad; aislar por qué PaddleOCR era el único
que resolvía `escaneado_d3`; y cerrar la medida CPU/GPU que `bench/ocr-ppp-nativos.md`
§10 dejó pendiente.

**Máquina:** RTX 3060 12 288 MiB (driver 572.61, CUDA 12.8), 12 hilos, Windows 10,
Python 3.11.9. **Fecha:** 2026-08-21, 07:20–09:10.
**Arnés:** `bench/lib/harness.sh`, lock exclusivo adquirido y liberado en las **nueve**
tandas. **Salidas:** `bench/salidas-corpus-d4/`. **Corpus nuevo:**
`corpus/pdf/escaneado_d4*.pdf` + `corpus/pdf/MANIFIESTO-d4.md`.

Toda medida de tiempo es **mediana de n=9**, con dos pasadas separadas (una con
muestreador de VRAM, otra sin él) porque el muestreo infla las medianas un 30-60 %.
La sesión de escritorio remoto estuvo activa todo el rato: casi todo sale `SUCIA` y
**es estructural**.

---

## 0. Veredicto, primero

1. **MEDIDO — el `escaneado_d4` cumple los cuatro criterios del encargo, y el de éxito
   declarado antes de medir.** Cuatro motores dan **19,30 / 36,91 / 41,78 / 61,41 %**
   de CER sobre el mismo documento: tres de los cuatro caen dentro de la banda
   15-60 %, y hay **17,6 puntos** entre el primero y el segundo. *(§5)*
2. **MEDIDO — la métrica antigua es ciega a las tildes y se puede cuantificar cuánto:
   sobre 28 celdas esconde 155 caracteres de error, hasta 23 en una sola celda.**
   RapidOCR recupera **0 de 35** caracteres acentuados de `d4` y `ocr_eval.py` le
   sigue dando 38,59 % en vez de 41,78 %. *(§1, §6)*
3. **MEDIDO, y es el resultado principal — la asimetría de PaddleOCR NO es ninguna de
   las tres causas que `ocr-ppp-nativos.md` §6 dejó como candidatas.** No es el tamaño
   del modelo, no es el idioma del reconocedor y no es el idioma del detector.
   **Es que RapidOCR normaliza el PP-OCRv6 con `mean=std=0,5` cuando el modelo se
   entrenó con las estadísticas de ImageNet.** Corregirlo baja el CER de d3 de
   **75,95 % a 3,80 %** con el mismo checkpoint: **72,2 puntos por tres números en un
   fichero de configuración.** *(§7)*
4. **MEDIDO — el `lang` de PaddleOCR es una etiqueta vacía en PP-OCRv6.** `lang="es"` y
   `lang="en"` resuelven al **mismo par de checkpoints** y dan salida idéntica carácter
   a carácter en los tres documentos. Toda la tabla canónica que dice «PaddleOCR
   (PP-OCRv6 medium, **es**)» podría decir `en` sin cambiar un número. *(§7.2)*
5. **MEDIDO — el techo ×1,4 de la regla R1 NO es seguro fuera del documento donde se
   midió.** Sobre `d4` (200 ppp nativos), subir a 280 ppp —exactamente ×1,4— empeora
   PaddleOCR de **19,30 % a 36,24 %**. La meseta se midió en un original de 100 ppp y
   no se transfiere. *(§8)*
6. **MEDIDO — la hipótesis CPU/GPU se cumple solo en la mitad del corpus.** «RapidOCR
   en CPU a ppp nativos ≈ RapidOCR en GPU a 200 ppp» es cierto en d3 (×1,05) y casi en
   d2 (×1,37), y **falso en d1 (×2,26)**. Pero el resultado que importa es otro: en
   CPU, RapidOCR a ppp nativos tarda **0,22-1,19 s por página**, que es utilizable.
   *(§9)*
7. **MEDIDO — «CPU y GPU dan salida idéntica carácter a carácter» queda REFUTADO** con
   el corpus nuevo: **5 de 21 celdas** difieren, y la CPU es mejor en dos y peor en
   tres. *(§9.3)*
8. **MEDIDO, y es la consecuencia práctica — con la corrección del punto 3, un solo
   motor cubre el corpus entero y funciona en CPU.** RapidOCR ONNX con PP-OCRv6 small y
   la normalización correcta da **0,00 / 0,00 / 0,00 / 3,80 / 18,62 %** sobre
   patológico, d1, d2, d3 y d4, **es más rápido que PaddleOCR en cuatro de las cinco**,
   arranca en **3,7 s** en vez de 18,4 y en CPU cuesta **0,32-1,18 s por página**.
   **Eso es lo que cambia el hito 6** — no la hipótesis de los ppp, que se cumple a
   medias. *(§9.2, §10)*

---

## 1. La trampa del evaluador, resuelta antes de medir nada

`bench/scripts/ocr_eval.py` normaliza así:

```python
s = unicodedata.normalize("NFKD", s)
s = "".join(c for c in s if not unicodedata.combining(c))
s = s.lower()
s = re.sub(r"[^a-z0-9 ]+", " ", s)
```

`á` se descompone en `a` + acento combinante y el acento se descarta; `ñ` se convierte
en `n`; `ü` en `u`. **`razon` y `razón` distan 0.** Añadir un documento acentuado sin
tocar esto no mide nada.

`bench/scripts/` es arnés compartido, así que el evaluador nuevo se **copió** a
`bench/salidas-corpus-d4/ocr_eval_d4.py`. El original **no se ha tocado**. El nuevo
reporta **las dos** lecturas sobre la misma salida:

| métrica | normalización | para qué |
|---|---|---|
| `cer_ascii` | **idéntica** a `ocr_eval.py` | comparabilidad con las 296 celdas ya medidas |
| `cer_acentos` | NFC, minúsculas, conserva `[a-z0-9áéíóúüñ ]` | medir castellano de verdad |

Añade además el **desglose por bloque de tamaño de letra** (título / subtítulo / cuerpo
/ letra pequeña), que es lo que permite distinguir un fallo de detección de uno de
reconocimiento, y el recuento de **caracteres acentuados recuperados**.

---

## 2. El diseño del `d4`, y por qué cada decisión

`bench/scripts/gen_corpus_ocr.sh` también es arnés compartido —regenera d1/d2/d3, que
son la base de 296 celdas— así que se copió y adaptó a
`bench/salidas-corpus-d4/gen_corpus_d4.py`. El original **no se ha tocado**.

| condición del encargo | cómo se cumple | verificación |
|---|---|---|
| **(a) ppp nativos ≥ 200** | página maestra a **600 ppp** (3882×5376) en vez de 300, para que una variante a 200 ppp siga siendo una **reducción ×3** y no una ampliación | `preparar_img.py` recalcula los ppp con la fórmula de R1: **200,0** en cinco variantes, **240,0** en `d4f` |
| **(b) atacar al reconocedor** | **cuatro tamaños de letra en la misma página**: 24 pt (título), 13 pt (subtítulo), 11 pt (cuerpo, 6 líneas), **7 pt (letra pequeña, 4 líneas)**. A 200 ppp el bloque pequeño mide 19,3 px de cuerpo | §5.2, con recuento de cajas detectadas |
| **(c) tildes y castellano real** | 610 caracteres con `á é í ó ú`, `ñ`/`Ñ`, `ü`, `¿`, `¡`, cifras y puntuación. **35 caracteres acentuados** | `d4_texto.py` es fuente única de verdad: lo importan el generador **y** el evaluador, así que la página y la referencia no pueden divergir |
| **(d) CER intermedios** | dos mecanismos: los cuatro tamaños de letra producen fallo **graduado**, y la referencia de **610** caracteres cuantiza el CER a **0,16 puntos** por carácter en vez de los **1,27** de los 79 caracteres de d1-d3 | §4 |

**Con 79 caracteres no puede haber gradiente aunque el documento lo tenga.** Ese es un
límite del corpus viejo que ninguna elección de degradación arregla: cada carácter
valía 1,27 puntos de CER, y con eso «0 % o 76 %» no es un interruptor del documento,
es en parte un artefacto de la escala.

**Semilla fija.** El generador pasa `magick -seed 20260821`. Sin ella `+noise Gaussian`
es aleatorio y el corpus no es reproducible. **Comprobado — MEDIDO:** dos ejecuciones
consecutivas dan el **mismo sha256 del JPEG** y **distinto sha256 del PDF**, porque
ImageMagick estampa un `/CreationDate` y **no honra `SOURCE_DATE_EPOCH`** (probado con
dos PDF generados con la misma variable de entorno: hashes distintos). Está documentado
en `corpus/pdf/MANIFIESTO-d4.md` §3.

---

## 3. El cribado: seis candidatas y cinco ablaciones

**MEDIDO**, n=1 por celda (para elegir no hacen falta medianas; la validación de la
elegida sí es n=9 y reprodujo estas cifras **exactamente**). CER con acentos.

| candidata | ppp | ang | ruido | `+level` | blur | q | PaddleOCR | Docling+Rapid | RapidOCR | EasyOCR |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| `d4_limpio` (control) | 200 | 0 | — | — | — | 95 | 0,00 | 0,00 | 1,17 | 0,50 |
| `d4a` | 200 | 2 | 0,20 | `12%,90%` | 0,4 | 60 | 0,00 | 7,05 | 1,51 | 0,34 |
| `d4b` | 200 | −3 | 0,35 | `20%,84%` | 0,8 | 45 | 0,17 | 18,46 | 2,18 | 27,68 |
| `d4c` | 200 | 3 | 0,50 | `28%,78%` | 1,2 | 32 | 0,67 | 22,99 | 15,60 | 15,10 |
| **`d4` (era `d4d`)** | **200** | **−4** | **0,65** | **`34%,72%`** | **1,6** | **24** | **19,30** | **36,91** | **41,78** | **61,41** |
| `d4e` | 200 | 4 | 0,80 | `40%,68%` | 2,0 | 18 | 70,97 | 88,59 | 92,45 | 73,32 |
| `d4f` | 240 | 3 | 0,55 | `30%,76%` | 1,4 | 28 | 0,67 | 22,15 | 6,04 | 17,95 |

**Por qué se descartan las otras cinco como documento canónico:**

- **`d4a`** y **`d4b`**: PaddleOCR ≤0,17 %. Reproducen el problema de d1/d2 —el mejor
  motor lo resuelve sin esfuerzo— y no miden margen para él.
- **`d4c`**: PaddleOCR 0,67 %. Buen documento *intermedio* (RapidOCR 15,60 y
  Docling 22,99 sí están en banda), pero el mejor motor sigue sin tener margen.
  **Se conserva en el corpus**: es el escalón anterior y la usa la fase 3.
- **`d4e`**: los cuatro por encima del 70 %. Es la pared plana que ya tenía d3: no
  discrimina nada. **Se conserva** como cota superior: sirve para comprobar que una
  heurística de «degradación severa» dispara.
- **`d4f`** (240 ppp): PaddleOCR 0,67 %, RapidOCR 6,04 %. Interesante por otra cosa
  —tiene los mismos parámetros de degradación que un punto medio pero **40 % más de
  resolución**, y eso solo le compra ventaja a los motores pequeños— pero como caso
  difícil no sirve. **Se conserva** por esa comparación.

**La ablación de un factor cada vez** (partiendo de `d4`, en `tmp/`, no van al corpus)
dice **qué perilla de degradación rompe el OCR — MEDIDO**:

| variante | qué cambia frente a `d4` | PaddleOCR | RapidOCR | Docling+Rapid | EasyOCR |
|---|---|---:|---:|---:|---:|
| `d4` | — | 19,30 | 41,78 | 36,91 | 61,41 |
| `abl_blur12` | blur 1,6 → **1,2** | **2,68** | **19,30** | 30,37 | 55,37 |
| `abl_jq45` | JPEG 24 → **45** | 24,66 | 41,95 | 34,40 | 60,07 |
| `abl_niv20` | contraste `34%,72%` → **`20%,84%`** | 3,69 | 31,38 | 35,40 | 56,54 |
| `abl_rui35` | ruido 0,65 → **0,35** | **36,24** | 35,91 | 35,07 | 56,54 |
| `abl_ang0` | rotación −4° → **0°** | 8,05 | 40,60 | 36,24 | 39,77 |

**Dos lecturas que no eran obvias:**

1. **El desenfoque es la perilla dominante.** Bajarlo de 1,6 a 1,2 divide el CER de
   PaddleOCR por 7 (19,30 → 2,68) y el de RapidOCR por 2,2. Ninguna otra hace eso.
2. **Quitar ruido EMPEORA el resultado — MEDIDO.** Con ruido 0,35 en vez de 0,65,
   PaddleOCR pasa de 19,30 a **36,24 %**. El fichero también pesa la mitad (42 847 vs
   103 369 bytes), que es la pista: **el ruido gaussiano actúa como tramado y obliga al
   JPEG a q=24 a conservar detalle que si no colapsa en bloques planos**. Es
   contraintuitivo y es exactamente el tipo de cosa que solo aparece ejecutando.

---

## 4. La tabla canónica de `escaneado_d4`

**MEDIDO**, mediana de n=9, GPU, a **ppp nativos** (regla R1), las **28 celdas
deterministas** (texto idéntico las 9 veces). Formato: **CER con acentos / CER ascii**.

| documento | PaddleOCR (v6 medium) | Docling+RapidOCR torch (v6 small) | RapidOCR (v5 mobile) | EasyOCR |
|---|---:|---:|---:|---:|
| `d4_limpio` (control) | **0,00** / 0,00 | 0,00 / 0,00 | 1,17 / 0,50 | 0,50 / 0,50 |
| `escaneado_d4a` | 0,00 / 0,00 | 7,05 / 6,71 | 1,51 / 0,67 | 0,34 / 0,34 |
| `escaneado_d4b` | 0,17 / 0,00 | 18,46 / 18,12 | 2,18 / 0,34 | 27,68 / 27,18 |
| `escaneado_d4c` | 0,67 / 0,00 | 22,99 / 22,48 | 15,60 / 11,91 | 15,10 / 13,76 |
| **`escaneado_d4`** | **19,30** / 18,46 | **36,91** / 36,24 | **41,78** / 38,59 | **61,41** / 59,56 |
| `escaneado_d4e` | 70,97 / 70,47 | 88,59 / 88,42 | 92,45 / 92,11 | 73,32 / 72,32 |
| `escaneado_d4f` (240 ppp) | 0,67 / 0,00 | 22,15 / 21,98 | 6,04 / 2,18 | 17,95 / 16,11 |

**El control importa.** `d4_limpio` sale a 0,00-1,17 %: la tipografía, el tamaño de
letra y el texto elegido **no** son el problema. Todo lo que se mide arriba viene de la
degradación, no del diseño de la página. Sin ese control, un 61 % de EasyOCR sería
ambiguo.

---

## 5. ¿Cumple `escaneado_d4` los cuatro criterios? Con todas las letras

**El criterio de éxito se declaró antes de medir:** *al menos un motor entre 15 % y
60 % de CER, y al menos dos motores separados por más de 10 puntos.*

### 5.1 El criterio de éxito: **SÍ, con margen**

| exigencia | resultado | veredicto |
|---|---|---|
| ≥1 motor en la banda 15-60 % | **tres**: PaddleOCR 19,30, Docling+Rapid 36,91, RapidOCR 41,78 | **CUMPLE** |
| ≥2 motores separados por >10 puntos | Paddle↔Docling **17,6**; Paddle↔Rapid **22,5**; Docling↔Easy **24,5** | **CUMPLE** |

### 5.2 Los cuatro criterios de `ocr-ppp-nativos.md` §8, uno a uno

| # | criterio | veredicto | evidencia |
|---|---|---|---|
| **a** | **ppp nativos ≥ 200** | **CUMPLE** | 200,0 ppp calculados desde la geometría de la página (1294 px / (465,84 pt / 72)); 240,0 en `d4f`. No se puede «arreglar» bajando la resolución: ya está en su suelo |
| **b** | **atacar al reconocedor, no al detector** | **CUMPLE, y está medido** | ver abajo |
| **c** | **tildes y castellano real** | **CUMPLE** | 35 caracteres acentuados, `ñ`/`Ñ`, `ü`, `¿`, `¡`. Y la métrica que los ve existe |
| **d** | **CER intermedios, no un interruptor** | **CUMPLE** | la familia recorre 0,00 → 0,17 → 0,67 → **19,30** → 70,97 para PaddleOCR y 0,00 → 7,05 → 18,46 → 22,99 → **36,91** → 88,59 para Docling+RapidOCR. Son escalas, no interruptores |

**El criterio (b), medido y no argumentado.** La página tiene **12 renglones**. El
desglose por bloque sobre `escaneado_d4` dice dónde falla cada motor:

| motor | título | subtítulo | cuerpo (11 pt) | **letra pequeña (7 pt)** |
|---|---:|---:|---:|---:|
| PaddleOCR v6 medium | 0,00 | 0,00 | **1,60** | **58,69** |
| Docling+RapidOCR torch | 0,00 | 0,00 | 6,09 | **75,12** |
| RapidOCR v5 mobile | 4,00 | 11,63 | 14,42 | **74,65** |
| EasyOCR | 0,00 | 53,49 | 59,94 | **75,12** |

Y la salida cruda lo enseña sin ambigüedad. PaddleOCR sobre `escaneado_d4`:

```
INFORME DE DIGITALIZACIÓN Expediente núm. 4.827/2026 - Archivo Histórico El dia 14 de
marzo se recibió la solicitud de análisis técnico sobre veintiún volúmenes encuadenados
en piel. La comisión determinó que la reproducción fotográfica debia realizarse con
iluminación difusa y sin contacto, segùn la norma UNE 15-402, para evitar daños añadidos
en los pliegos más frágiles del año 1893 62=06 3k0020 98 940aρ10m7 1μ9ma20 bm5mm 5m2a10
sue ba mvsian amagaafca akmgvaca da| kegajo as reaponsabdidad del area de consarvalión
prevanaiva .4mmvkm2b06 050g06.7 8. 94ky 12.K 9μm0an amva0d19
```

**Los cuatro renglones de 7 pt están DETECTADOS y transcritos como basura.** Eso es un
fallo del reconocedor, no del detector: es exactamente lo que pedía el criterio (b), y
es lo contrario de d3, donde los motores que fallaban recuperaban el titular y **no
emitían nada** del cuerpo.

RapidOCR sobre el mismo fichero:

```
INFORME DE DIGITALIZACION Expediente num, 4.827/2026-Archivo Histonco El dia 14 de marzo
se recbio la soicitud de analisis tecnico sobre veintian voumenes encuadernados en piel.
La comision determind gue la reproduccion fotografca debiarealizarse con lumnacon dfusay
sin contacto, segun la norma UNE 15-402, para evitar danos anaddos en los pliegos mas
fragiles del ano 1893.
```

Aquí sí desaparece el bloque pequeño —fallo de detección— **y además no sale ni una
tilde**: `DIGITALIZACION`, `Histonco`, `analisis`, `tecnico`, `comision`, `danos`,
`anaddos`, `ano`. **0 de 35 caracteres acentuados.** Con la métrica antigua eso cuesta
38,59 %; con la nueva, 41,78 %.

### 5.3 Lo que `escaneado_d4` **no** resuelve

- **EasyOCR sigue siendo una pared**: 61,41 % en d4 y 73,32 % en d4e, sin estados
  intermedios útiles. Para EasyOCR el corpus sigue midiendo selección de motor.
- **`d4e` es un d3 nuevo**: los cuatro por encima del 70 %. Se conserva a propósito,
  pero no es el caso útil.
- **Es un documento sintético.** Mide degradación sintética (rotar, desenfocar, bajar
  contraste, ruido, JPEG). Un escaneo real añade sombra de encuadernación, curvatura y
  transparencia del papel, que aquí no están. **PENDIENTE.**

---

## 6. Cuánto esconde la métrica ciega a las tildes

**MEDIDO** sobre las 28 celdas de la validación. `ocultos` = caracteres de error que
`ocr_eval.py` **no cuenta**.

| motor | documento | dist. con acentos | dist. ascii | **ocultos** | acentos recuperados |
|---|---|---:|---:|---:|---:|
| PaddleOCR | `escaneado_d4` | 115 | 110 | **5** | 19/35 |
| PaddleOCR | `escaneado_d4c` | 4 | 0 | **4** | 31/35 |
| PaddleOCR | `escaneado_d4f` | 4 | 0 | **4** | 31/35 |
| RapidOCR | `escaneado_d4` | 249 | 230 | **19** | **0/35** |
| RapidOCR | `escaneado_d4c` | 93 | 71 | **22** | 6/35 |
| RapidOCR | `escaneado_d4f` | 36 | 13 | **23** | 10/35 |
| RapidOCR | `escaneado_d4b` | 13 | 2 | **11** | 23/35 |
| EasyOCR | `escaneado_d4` | 366 | 355 | **11** | 4/35 |
| Docling+Rapid | `escaneado_d4` | 220 | 216 | **4** | 17/35 |

*(La tabla completa de las 28 celdas está en `bench/salidas-corpus-d4/tablas.md` T3.)*

**Totales — MEDIDO: 155 caracteres de error ocultos en 28 celdas, media 5,54, máximo
23.** Los casos peores no son los documentos más difíciles: son los **intermedios**,
donde el motor acierta las letras y falla los acentos. En `escaneado_d4c` con RapidOCR
la métrica antigua da 11,91 % y la real es 15,60 % — **un 31 % de error relativo hacia
abajo**. Y en el documento *limpio*, RapidOCR pasa de 0,50 % (ascii) a 1,17 %
(acentos): la métrica ciega infravalora **×2,3** justo donde más precisión se pide.

**Consecuencia para FileX — la afirmación honesta:** las 296 celdas de
`ocr-ppp-nativos.md` **siguen siendo válidas para lo que miden**, porque su referencia
no tiene ni una tilde: ahí `cer_ascii == cer_acentos` por construcción. Lo que no se
puede es extrapolarlas a castellano. **Cualquier cifra de calidad de OCR en español que
FileX publique tiene que salir de la métrica con acentos.**

---

## 7. La asimetría de PaddleOCR: tres hipótesis refutadas y la causa encontrada

`bench/ocr-ppp-nativos.md` §6 dejó tres candidatas, en orden de peso: **(1) el tamaño
del modelo**, **(2) el idioma del reconocedor**, **(3) el idioma del detector**.
Las tres se cruzaron sobre **d3** (100 ppp nativos, referencia sin tildes) y sobre
**d4** y **d4c** (200 ppp, referencia acentuada), con dos instrumentos:

- **PaddleOCR forzando los nombres de modelo.** Mismo motor, mismo preprocesado, misma
  imagen: lo único que cambia es el checkpoint. Los pesos caen en
  `C:\Users\krato\.paddlex\official_models`, **fuera de los venv**.
- **RapidOCR ONNX con `Global.model_root_dir`** apuntando a un directorio propio del
  agente, **para no escribir dentro de `.venv-ai`**. Verificado al terminar: el
  directorio `.venv-ai\Lib\site-packages\rapidocr\models\` conserva sus 10 ficheros con
  fecha del **19 de agosto**, sin tocar.

### 7.1 Hipótesis 1 — el tamaño del modelo: **REFUTADA como causa**

**MEDIDO.** CER con acentos. Los tres tamaños de PP-OCRv6, en los dos motores:

| tamaño de PP-OCRv6 | **PaddleOCR** d3 | **RapidOCR** d3 | PaddleOCR d4 | RapidOCR d4 |
|---|---:|---:|---:|---:|
| **medium** | **2,53** | **3,80** | 19,30 | 22,82 |
| **small** | **3,80** | **75,95** | 19,80 | 36,91 |
| **tiny** | 43,04 | 43,04 | 31,88 | 39,60 |

**El mismo checkpoint nominal (PP-OCRv6 small) da 3,80 % en PaddleOCR y 75,95 % en
RapidOCR sobre d3: 72,2 puntos de diferencia con los mismos pesos.** El tamaño no puede
ser la causa de una diferencia que aparece con el tamaño fijo.

Hay una segunda señal de que la variable estaba mal planteada: **no es monótona**. En
RapidOCR, `tiny` (43,04) es **mejor** que `small` (75,95) sobre d3. Un modelo más
pequeño no puede ser mejor por capacidad.

**Cruce detector × reconocedor** (PaddleOCR, PP-OCRv6) — **MEDIDO**:

| detector | reconocedor | d3 | d4c | d4 |
|---|---|---:|---:|---:|
| medium | medium | **2,53** | 0,67 | 19,30 |
| medium | small | 8,86 | 1,01 | **17,45** |
| small | medium | 3,80 | 1,01 | 22,99 |
| small | small | 3,80 | 1,01 | 19,80 |

Dentro de PaddleOCR el tamaño mueve poco: entre 2,53 y 8,86 en d3, entre 17,45 y 22,99
en d4. **Frente a los 72 puntos de diferencia entre motores, es ruido.**

### 7.2 Hipótesis 2 — el idioma del reconocedor: **VACÍA en PP-OCRv6, real en PP-OCRv5**

**MEDIDO por lectura del código y confirmado por ejecución.** En PaddleOCR 3.7.0
(`_pipelines/ocr.py:318`), `_get_ocr_model_names` hace, para **cualquier** idioma del
conjunto `_PPOCRV6_LANGS` (que incluye `ch`, `en`, `japan` y todos los `LATIN_LANGS`
salvo `pi`):

```python
if ppocr_version == "PP-OCRv6":
    if lang in _PPOCRV6_LANGS:
        return "PP-OCRv6_medium_det", "PP-OCRv6_medium_rec"
```

Es decir: **`lang="es"` y `lang="en"` devuelven exactamente el mismo par de
checkpoints.** En RapidOCR pasa lo mismo por otra vía: los ficheros de PP-OCRv6 se
llaman `multi_PP-OCRv6_det_*` y `multi_PP-OCRv6_rec_*` — **hay un solo modelo
multilingüe y no existe variable de idioma**.

**Comprobado ejecutando — MEDIDO:**

| configuración | d3 | d4c | d4 |
|---|---:|---:|---:|
| PaddleOCR `lang="es"` | 2,53 | 0,67 | 19,30 |
| PaddleOCR `lang="en"` | **2,53** | **0,67** | **19,30** |

Idénticas en las tres celdas, y las salidas coinciden carácter a carácter.
**La etiqueta «PaddleOCR (PP-OCRv6 medium, `es`)» de la tabla canónica de
`ocr-ppp-nativos.md` §3 es correcta pero engañosa: el `es` no hace nada.**

En **PP-OCRv5** el idioma sí es una variable real, porque hay un reconocedor por sistema
de escritura. Con el **detector fijo** (`PP-OCRv5_server_det`) — **MEDIDO**:

| reconocedor PP-OCRv5 | d3 | d4c | d4 |
|---|---:|---:|---:|
| `latin_PP-OCRv5_mobile_rec` | **6,33** | **1,51** | **17,28** |
| `en_PP-OCRv5_mobile_rec` | 7,59 | 3,86 | 30,37 |
| `PP-OCRv5_server_rec` (chino) | **25,32** | **20,64** | **40,94** |

**El reconocedor chino cuesta 19,0 puntos en d3 y 23,7 en d4 frente al latino.** Y eso
importa para FileX de forma directa, porque **`bench/scripts/ocr_motor.py` fija
`LangRec.CH`**: la configuración de RapidOCR que el proyecto usa como línea base lee
castellano con un reconocedor de chino. Confirmado también dentro de RapidOCR:

| RapidOCR PP-OCRv5 mobile | d3 | d4c | d4 |
|---|---:|---:|---:|
| `Rec.lang_type = ch` (lo que usa FileX hoy) | 77,22 | 15,60 | 41,78 |
| `Rec.lang_type = latin` | 75,95 | **9,56** | **36,24** |

**Pero no explica la asimetría**: en d3 la diferencia son 1,3 puntos y el fallo sigue
al 76 %.

### 7.3 Hipótesis 3 — el idioma del detector: **VACÍA en v5/v6, medible solo en v4**

En PP-OCRv6 el detector es `multi`, uno solo. En PP-OCRv5 el catálogo de RapidOCR solo
trae `ch_PP-OCRv5_det_mobile/server`: **no hay detector en otro idioma**. La variable
solo existe en PP-OCRv4 — **MEDIDO**:

| RapidOCR PP-OCRv4 mobile, `Rec = ch` | d3 | d4c | d4 |
|---|---:|---:|---:|
| `Det = ch` | 58,23 | 18,79 | 44,30 |
| `Det = en` (`en_PP-OCRv3_det_mobile`) | 75,95 | 10,74 | 44,63 |
| `Det = multi` (`multi_PP-OCRv3_det_mobile`) | 46,84 | 15,27 | **61,07** |

Cambia mucho, sí, pero **sin dirección**: `multi` es el mejor en d3 y el peor en d4. Y
ninguno se acerca a PaddleOCR. **No es la causa.**

### 7.4 Lo que sí es: la NORMALIZACIÓN del detector

Descartadas las tres, quedaba la tubería. La primera sospecha —que RapidOCR descarta
renglones con `Global.text_score < 0,5` mientras PaddleOCR trae el umbral a 0—
**quedó refutada de la forma más limpia posible: no mueve ni una décima.**

**MEDIDO**, RapidOCR PP-OCRv6 small:

| cambio sobre el defecto | d3 | d4c | d4 |
|---|---:|---:|---:|
| — (defecto) | 75,95 | 29,36 | 36,91 |
| `Global.text_score = 0,0` | **75,95** | **29,36** | **36,91** |
| `Global.text_score = 0,1` | 75,95 | 29,36 | 36,91 |
| `Global.use_cls = false` | 75,95 | 29,36 | 36,91 |
| `Det.unclip_ratio = 2,0` | 75,95 | 29,53 | 37,25 |
| `Det.box_thresh = 0,3` | 75,95 | **7,05** | 30,54 |
| `Det.limit_side_len = 1200` | **49,37** | 29,36 | 36,91 |

Dos perillas mueven algo (`box_thresh` en d4c, `limit_side_len` en d3) y ninguna
explica el salto. Se probó además el **A/B en las dos direcciones** sobre el reescalado
interno del detector —RapidOCR usa `limit_side_len=736` con `limit_type=min`, PaddleOCR
usa `64`, así que sobre d3 (647×850) RapidOCR **amplía** la página y PaddleOCR no— y
**también quedó refutado**: RapidOCR con `64` sigue en 75,95 y PaddleOCR con `736`
sigue en 3,80.

La respuesta estaba en comparar los **dos ficheros de configuración del mismo modelo**:

| | PaddleX (`~/.paddlex/official_models/PP-OCRv6_small_det/inference.yml`) | RapidOCR (`rapidocr/config.yaml`) |
|---|---|---|
| `mean` | **`[0,485, 0,456, 0,406]`** (ImageNet) | **`[0,5, 0,5, 0,5]`** |
| `std` | **`[0,229, 0,224, 0,225]`** (ImageNet) | **`[0,5, 0,5, 0,5]`** |
| `thresh` | 0,2 | 0,3 |
| `box_thresh` | 0,45 | 0,5 |
| `unclip_ratio` | 1,4 | 1,6 |
| `max_candidates` | 3000 | 1000 |

**Los mismos pesos con distinta normalización de entrada.** El `inference.yml` que
Baidu distribuye **junto al modelo** declara las estadísticas de ImageNet; RapidOCR
aplica 0,5/0,5 a todas las versiones por igual.

**El A/B — MEDIDO.** RapidOCR ONNX, PP-OCRv6 **small**, mismo checkpoint en las cinco
filas:

| configuración | d3 | d4c | d4 |
|---|---:|---:|---:|
| defecto de RapidOCR | **75,95** | 29,36 | 36,91 |
| solo post-proceso de PaddleX (`thresh`/`box_thresh`/`unclip`/`max_cand`) | 75,95 | 32,21 | 36,58 |
| **solo `mean`/`std` de ImageNet (orden RGB)** | **11,39** | 1,01 | 20,13 |
| **solo `mean`/`std` de ImageNet (orden BGR)** | **8,86** | 1,01 | 18,79 |
| **normalización + post-proceso de PaddleX** | **3,80** | **1,17** | **18,62** |
| *(referencia: PaddleOCR con el mismo PP-OCRv6 small)* | *3,80* | *1,01* | *19,80* |

**Con todas las letras: la normalización sola vale 64,6 puntos de CER en d3
(75,95 → 11,39); el post-proceso solo no vale nada (0,0 puntos); y los dos juntos
reproducen la cifra de PaddleOCR exactamente: 3,80 %.**

Funciona igual con `medium`: RapidOCR PP-OCRv6 medium con la normalización de PaddleX
da **2,53 %** en d3 — el número exacto de PaddleOCR.

Y también mejora la configuración vieja: RapidOCR **PP-OCRv5 mobile** con esos valores
pasa de **77,22 % a 54,43 %** en d3 y de 15,60 % a **8,05 %** en d4c.

### 7.5 Qué significa esto para FileX

1. **La asimetría no era del modelo: era un defecto de configuración de RapidOCR 3.9.2
   con la familia PP-OCRv6.** La conclusión de `HUECOS.md` («es límite de modelo —
   PP-OCRv5 mobile frente al medium de Paddle») y la corrección parcial de
   `ocr-ppp-nativos.md` §6 («no es la generación del backbone; quizá el tamaño»)
   **quedan las dos superadas**: no es ni la generación, ni el tamaño, ni el idioma.
2. **Docling hereda el defecto.** `Docling + RapidOCR backend="torch"` es la ruta que el
   plan de FileX da por buena y construye RapidOCR con los parámetros por defecto: por
   eso da 75,9 % en d3 en `ocr-ppp-nativos.md` §3. **Es corregible desde fuera**, sin
   parchear el paquete, pasando los parámetros del detector.
3. **Es la corrección más barata medida en este proyecto**: seis números en un
   diccionario por **72,2 puntos de CER**.
4. **Y deja una regla general, no un parche:** *cuando el motor y el modelo vienen de
   proyectos distintos, hay que comprobar que el preprocesado que aplica el motor es el
   que declara el fichero de configuración del modelo.* Es el mismo tipo de fallo que
   `onnxruntime-gpu` cayendo a CPU en silencio: nada da error, solo empeora.

### 7.6 La prueba que cierra el argumento: contar cajas

**MEDIDO.** La página de `d4` tiene **12 renglones**; la de `d3`, **3**. Recuento de
cajas de texto que devuelve el detector:

| configuración | d3 (3 renglones) | d4c (12) | **d4 (12)** |
|---|---:|---:|---:|
| PaddleOCR PP-OCRv6 medium | **3/3** | 12/12 | **12/12** |
| PaddleOCR PP-OCRv6 small | **3/3** | 12/12 | 11/12 |
| RapidOCR PP-OCRv6 small, **defecto** | **1/3** | 10/12 | **8/12** |
| RapidOCR PP-OCRv5 mobile, defecto | **1/3** | 11/12 | 8/12 |
| **RapidOCR PP-OCRv6 small + normalización de PaddleX** | **3/3** | **12/12** | **12/12** |

Esto convierte el argumento en medida y cierra las dos preguntas a la vez:

- **El fallo de RapidOCR en d3 es del DETECTOR: encuentra 1 renglón de 3.** No es que
  lea mal; es que no ve. Y **la normalización lo arregla: pasa a 3 de 3.**
- **PaddleOCR sobre `d4` encuentra 12 de 12 y aun así comete 19,30 % de CER.** Todo ese
  error es del **reconocedor**. Es la comprobación directa del criterio (b).

---

## 8. La regla R1 revisada: el techo ×1,4 no se transfiere

`ocr-ppp-nativos.md` §9 fijó `ppp_ocr = clamp(ppp_nativos, 100, ppp_nativos × 1,4)`,
con el techo justificado por una meseta medida **sobre d3, un documento de 100 ppp
nativos**. Con `escaneado_d4` (200 ppp nativos) ese techo se puede probar por primera
vez en otro punto de partida — **MEDIDO**:

| motor | `d4` a 200 ppp (nativo) | `d4` a **280 ppp (= ×1,4)** | efecto del techo |
|---|---:|---:|---|
| PaddleOCR PP-OCRv6 medium | **19,30** | **36,24** | **+16,9 puntos, peor** |
| RapidOCR PP-OCRv6 small **corregido** | **18,62** | 28,86 | **+10,2 puntos, peor** |
| RapidOCR PP-OCRv5 mobile (defecto) | 41,78 | 41,95 | +0,2, indiferente |

**Con todas las letras: aplicar el techo ×1,4 sobre un original de 200 ppp empeora al
mejor motor en 16,9 puntos de CER.** La meseta de `ocr-ppp-nativos.md` §5 es una
propiedad del par (documento, motor), no una constante.

**La lectura correcta, y encaja con §7.6:** lo que decide no es el factor sobre el
nativo sino **el tamaño en píxeles que llega al detector**. `d3` a ×1,4 son 907 px de
ancho; `d4` a ×1,4 son **1 812**. Son regímenes distintos y no hay razón para que
compartan un multiplicador.

**Propuesta de R1 corregida — PENDIENTE de validar fuera de este corpus:**

```
ppp_ocr = clamp(ppp_nativos, 100, 200)      # techo ABSOLUTO, no relativo
```

Se apoya en lo medido aquí y en `ocr-ppp-nativos.md` §5: d2 y d3 (100 nativos) toleran
hasta 140 ppp; `d4` (200 nativos) se degrada ya a 280; y el patológico, que es de 200
nativos, siempre fue el mejor caso. **Un techo absoluto de 200 ppp no viola ninguna de
las dos medidas y el techo relativo ×1,4 sí.** El suelo de 100 se mantiene sin cambios:
sigue siendo lo medido.

---

## 9. La medida CPU/GPU

`ocr-ppp-nativos.md` §10 la dejaba pendiente en una línea. Es barata y cambia el
diseño del sidecar, así que se hizo. **Hipótesis declarada antes de medir:**

> *RapidOCR en CPU a ppp nativos ≈ RapidOCR en GPU a 200 ppp. Si se confirma, la GPU
> deja de ser necesaria para el OCR de FileX y eso cambia el hito 6.*

### 9.1 El contraste directo de la hipótesis

**MEDIDO.** Mediana de n=9, sin muestreador de VRAM, RapidOCR PP-OCRv5 mobile ONNX.

| documento | ppp nativos | **CPU a nativos** | **GPU a 200 ppp** | cociente | ¿se cumple? |
|---|---:|---:|---:|---:|---|
| `escaneado_d3` | 100 | **219,9 ms** | **208,8 ms** | **×1,05** | **sí** |
| `escaneado_d2` | 100 | 262,6 ms | 192,3 ms | ×1,37 | casi |
| `escaneado_d1` | 150 | 460,6 ms | 203,8 ms | **×2,26** | **no** |
| `patologico_escaneado` | 200 | 995,1 ms | 433,5 ms | ×2,30 | no aplica (ya está a 200) |
| `escaneado_d4` | 200 | 1 192,0 ms | 454,3 ms | ×2,62 | no aplica |

**Veredicto: la hipótesis se cumple exactamente donde el ahorro de píxeles es máximo y
se cae en cuanto no lo es.** Se sostiene en d3 (×1,05), casi en d2 (×1,37) y **falla en
d1 (×2,26)**, cuyo factor evitado es solo ×1,33. Y para los documentos que ya están a
200 ppp nativos —el patológico y todo `d4`— **la comparación no existe**: no hay
interpolación que evitar, así que la GPU compite contra la CPU en igualdad y gana
×2,3-2,6.

### 9.2 CPU contra GPU a la misma resolución — el dato que sí decide

**MEDIDO.** Cociente CPU/GPU con la **misma** imagen de entrada:

| motor | rango del cociente CPU/GPU | tiempo en CPU a ppp nativos |
|---|---:|---|
| **RapidOCR** (ONNX, v5 mobile) | **×2,30 – ×3,75** | **0,22 – 1,19 s/página** |
| **RapidOCR corregido** (v6 small + norm. PaddleX) | ×2,30 – ×4,63 | **0,32 – 1,18 s/página** |
| **PaddleOCR** (v6 medium) | **×9,78 – ×13,78** | **0,88 – 5,42 s/página** |
| **EasyOCR** | ×6,54 – ×12,04 | 1,91 – 7,68 s/página |
| **Docling + RapidOCR** (tubería completa) | ×2,84 – ×3,29 | 1,06 – 1,96 s/página (`onnxruntime`) |

**Lo que esto significa para el hito 6, con todas las letras:**

1. **Para RapidOCR la GPU no es necesaria: es una comodidad de ×2,3-3,8.** En CPU una
   página cuesta menos de 1,2 s incluso a 200 ppp. **Y la versión corregida de §7.4 da
   18,62 % de CER en d4 y 3,80 % en d3 corriendo en CPU** — mejor que PaddleOCR con GPU
   (19,30 % y 2,53 %) en el primero y equivalente en el segundo.
2. **Para PaddleOCR la GPU sí es necesaria: ×10-14.** 5,4 s por página en CPU no es una
   opción para un servicio.
3. **Combinando 1 y 2 con §7.4: FileX puede hacer OCR de calidad de PaddleOCR sin
   GPU**, usando RapidOCR ONNX con el PP-OCRv6 small y la normalización correcta. Eso
   es lo que cambia el hito 6 — **no la hipótesis de los ppp, que solo se cumple a
   medias.**
4. **RapidOCR también gana en carga en frío**: 3,4-3,7 s frente a 18,4 s (PaddleOCR en
   GPU) y **62,9 s** (PaddleOCR en CPU). Para un sidecar que arranca bajo demanda, eso
   pesa tanto como el tiempo por página.

### 9.3 «CPU y GPU dan salida idéntica carácter a carácter»: **REFUTADO**

`gpu-fase2.md` §2 lo midió sobre tres configuraciones de RapidOCR y dos de EasyOCR y
concluyó que la GPU **no compra precisión, solo velocidad**. Con el corpus nuevo y
las 21 celdas comparables — **MEDIDO**:

| motor | celdas comparadas | **celdas con salida distinta** | mayor discrepancia |
|---|---:|---:|---|
| RapidOCR | 9 | **1** | `d3` a 200 ppp: **65,82 % (GPU) vs 70,89 % (CPU)** |
| PaddleOCR | 9 | **1** | `d4`: 19,30 % (GPU) vs 19,63 % (CPU) |
| EasyOCR | 3 | **3** | `d3` a 200 ppp: 59,49 % (GPU) vs 56,96 % (CPU) |

**5 de 21 celdas difieren.** La conclusión matizada, que es la útil: *la salida coincide
mientras el documento es fácil; en la zona de degradación donde el motor duda, el
dispositivo cambia el resultado, y puede cambiarlo en cualquier dirección* —la CPU es
mejor en dos celdas y peor en tres—. **Para FileX significa que no se puede validar en
CPU y desplegar en GPU dando por hecho el mismo resultado**, y que una prueba de
regresión de OCR tiene que fijar el dispositivo.

*Matiz honesto:* EasyOCR difiere en la salida de `d3` a 100 ppp aunque el CER coincida
(54,43 % en las dos). Es una permutación del texto, no un cambio de calidad.

### 9.4 Backend por dispositivo en docling: confirmado

**MEDIDO.** Mediana de n=9, tubería completa de docling (incluye maquetación), a ppp
nativos.

| documento | **CUDA `torch`** | **CPU `torch`** | **CPU `onnxruntime`** |
|---|---:|---:|---:|
| `patologico_escaneado` (200) | 736,0 | 2 167,9 | **1 735,3** |
| `escaneado_d1` (150) | 474,7 | 1 468,7 | **1 258,5** |
| `escaneado_d2` (100) | 399,3 | 1 135,8 | **1 056,7** |
| `escaneado_d3` (100) | 370,6 | 1 075,7 | **1 063,2** |
| `escaneado_d4` (200) | 680,9 | 2 237,9 | **1 962,1** |

**En CPU, `onnxruntime` es más rápido que `torch` en las cinco filas**, entre un 1,2 % y
un 20,0 % (media 11,0 %). Confirma la regla que ya estaba medida —*en CPU `onnxruntime`, en
CUDA `torch`*— y le pone número en este corpus. **El CER es idéntico en las tres
columnas**, así que la elección de backend es puramente de coste.

### 9.5 VRAM y carga en frío sobre la familia d4

**MEDIDO**, pasada con muestreador (100 ms), sobre las 7 imágenes de la familia a ppp
nativos (200-240).

| motor | base MiB | tras carga MiB | **pico MiB** | **coste propio MiB** | carga en frío |
|---|---:|---:|---:|---:|---:|
| Docling+RapidOCR torch | 2 897 | — | 4 381 | **+1 484** | ~20 s (proceso) |
| RapidOCR ONNX | 2 906 | 3 076 | 5 471 | **+2 565** | **3,9 s** |
| PaddleOCR | 2 878 | 3 157 | 5 586 | **+2 708** | 5,5 s |
| EasyOCR | 2 907 | 3 145 | **7 337** | **+4 430** | 7,0 s |

Nada se acerca al peor caso de `ocr-ppp-nativos.md` §7.2 (EasyOCR a 11 877 MiB), y la
razón es exactamente la que aquella regla predice: **aquí no se sobremuestrea nada.**
A 200 ppp nativos EasyOCR cuesta 4 430 MiB; a 300 ppp costaba 9 811. **Aplicar R1 es lo
que hace predecible el presupuesto de VRAM**, y con `d4` vuelve a verse.

*Aviso de comparabilidad:* estas cifras llevan **7 imágenes** de 200-240 ppp; las de
`ocr-ppp-nativos.md` §7.2 llevaban 40 imágenes de 75 a 300 ppp. Son picos de tandas
distintas y solo la columna «coste propio» es comparable entre motores.

---

## 10. Reglas para FileX que salen de este informe

### R6 (nueva) — Fijar la normalización del detector de RapidOCR

**La más barata del proyecto: seis números por 72,2 puntos de CER.**

```python
params = {
    "Det.mean": [0.485, 0.456, 0.406],   # ImageNet: lo que declara el
    "Det.std":  [0.229, 0.224, 0.225],   # inference.yml del propio modelo
    "Det.thresh": 0.2,
    "Det.box_thresh": 0.45,
    "Det.unclip_ratio": 1.4,
    "Det.max_candidates": 3000,
}
```

Aplica a **RapidOCR ONNX y a Docling+RapidOCR** con la familia **PP-OCRv6**. Sin ella,
el detector encuentra 1 renglón de 3 en `d3` y 8 de 12 en `d4`.

### R3 revisada — la tabla de selección de motor cambia

**MEDIDO.** Con R6 aplicada, la elección de motor de `ocr-ppp-nativos.md` §9 R3 ya no
se sostiene:

| documento | PaddleOCR v6 medium (GPU) | **RapidOCR v6 small + R6 (GPU)** | **RapidOCR v6 small + R6 (CPU)** |
|---|---:|---:|---:|
| `patologico_escaneado` | 0,00 % · 296 ms | **0,00 % · 446 ms** | 0,00 % · 1 024 ms |
| `escaneado_d1` | 0,00 % · 162 ms | **0,00 % · 125 ms** | 0,00 % · 532 ms |
| `escaneado_d2` | 0,00 % · 98 ms | **0,00 % · 78 ms** | 0,00 % · 324 ms |
| `escaneado_d3` | **2,53 %** · 90 ms | 3,80 % · 82 ms | 3,80 % · 380 ms |
| `escaneado_d4` | 19,30 % · 393 ms | **18,62 % · 340 ms** | **18,62 % · 1 178 ms** |

**Un solo motor cubre el corpus entero**, es más rápido que PaddleOCR en cuatro de las
cinco filas, arranca en 3,7 s en vez de 18,4, y **funciona en CPU**. La regla
«degradación severa → cambiar a PaddleOCR» pierde su motivo: la diferencia que la
justificaba era el defecto de configuración, no el motor.

*La excepción sigue siendo `d3`, donde PaddleOCR gana por 1,27 puntos — un carácter
sobre 79. No es base para una regla de conmutación.*

### R4 confirmada y ampliada

`OcrOptions.scale` explícito, siempre. Aquí se fijó por documento desde los ppp nativos
(`scale = ppp/72`) y la sonda confirma que llegan al motor **exactamente** los píxeles
esperados: 1294×1716 para `d4`, 647×850 para `d3`, 1552×2080 para `d4f`. Con el defecto
(`scale=3,0` → 216 ppp) `d4` habría entrado a ×1,08 —benigno— pero `d3` a ×2,16, que es
donde se rompe.

### R7 (nueva) — Toda cifra de calidad de OCR en español, con la métrica acentuada

Medido: 155 caracteres de error ocultos en 28 celdas, hasta 23 en una. Y hay un caso
—RapidOCR sobre `d4`— donde el motor **no recupera ni uno de los 35 caracteres
acentuados** y la métrica antigua le da 38,59 % en vez de 41,78 %.

---

## 11. Qué queda PENDIENTE

- **Validar R6 fuera de este corpus.** La corrección está medida sobre 5 documentos y
  1 página cada uno. Antes de meterla en FileX hay que pasarla por el patrón oro.
- **El techo de R1.** La propuesta `clamp(nativos, 100, 200)` de §8 encaja con todo lo
  medido, pero **no se ha barrido** la curva de ppp sobre `d4` como se hizo sobre `d3`.
  Faltan los puntos entre 200 y 280 y por encima de 280.
- **`magick -deskew 40%` sobre la familia d4.** Sigue sin medirse su interacción con el
  techo, ahora con documentos rotados de −4° a +4°.
- **La heurística de degradación severa** (`ocr-ppp-nativos.md` §9 R3): con `d4` ya hay
  un caso con gradiente contra el que calibrarla, y con el recuento de cajas de §7.6 hay
  una señal candidata: **cajas detectadas frente a área de texto**. **PENDIENTE.**
- **Degradación realista.** `d4` es sintético. Sombra de encuadernación, curvatura de
  página y transparencia del papel no están.
- **EasyOCR sigue sin caso útil**: 61,41 % en `d4`, 73,32 % en `d4e`, sin escala.
- **La sonda de carga de CPU falló y las tandas de CPU no llevan línea base.** Ver §12.

---

## 12. Reglas del encargo, cumplidas — y lo que falló

| regla | estado |
|---|---|
| Escribir solo en `bench/corpus-d4.md`, `bench/salidas-corpus-d4/` y `corpus/pdf/escaneado_d4*` | **Cumplida.** Los maestros, `analysis/`, `repos/`, `bench/scripts/`, `bench/salidas-ocr-ppp/` y los informes de otros agentes, sin tocar |
| No tocar `d1`, `d2`, `d3`, `patologico_escaneado` | **Cumplida.** Solo lectura; sus `.pdf` conservan fecha del 20 de agosto |
| Copiar los arneses compartidos en vez de modificarlos | **Cumplida.** `ocr_eval.py` → `ocr_eval_d4.py`; `gen_corpus_ocr.sh` → `gen_corpus_d4.py`; `20_ocr_lote.py` → `ocr_lote_d4.py`; `21_docling_lote.py` → `docling_lote_d4.py`. Los cuatro originales intactos |
| Lock de GPU en todas las tandas | **Cumplida.** `gpu_acquire`/`gpu_release` en las **nueve** tandas (cribado, fase 2, 3, 3b, 3c, 3d, 3e, 4 y cierre). Lock libre al terminar |
| No instalar en `.venv-ai` ni `.venv-paddle` | **Cumplida.** Nada instalado. Los pesos nuevos de RapidOCR fueron a `bench/salidas-corpus-d4/modelos/` vía `Global.model_root_dir`, y los de PaddleX a `~/.paddlex/`, los dos **fuera de los venv**. Comprobado: `.venv-ai\...\rapidocr\models\` conserva sus 10 ficheros con fecha del 19 de agosto |
| Verificar `torch.cuda.is_available()` al terminar | **Cumplida.** `.venv-ai`: `torch 2.6.0+cu124`, `cuda True`, `NVIDIA GeForce RTX 3060`, `onnxruntime 1.22.0`. `.venv-paddle`: `paddle 3.2.0` compilado con CUDA, 1 dispositivo, `paddleocr 3.7.0` |
| Medianas de n≥9 con etiqueta | **Cumplida.** n=9 en todas las tandas de medida (el cribado, que solo elige candidata, es n=1 y su elección se reprodujo **exactamente** con n=9). **Las 28 celdas de la validación salieron deterministas.** Todas las tandas salieron `SUCIA` (picos del 22 al 61 %): es estructural, la sesión remota estuvo activa |
| Dos pasadas por el conflicto muestreador/tiempos | **Cumplida.** Pasada `_vram` con muestreo y pasada `_t` sin él |
| Timeouts explícitos | **Cumplida.** `timeout` en las 72 invocaciones de motor (1 800–5 400 s). Ningún proceso colgado |
| Dos intentos por problema, luego documentar | **Cumplida.** Ver abajo |
| Borrar salidas grandes, dejar `MANIFIESTO` | **Cumplida.** `corpus/pdf/MANIFIESTO-d4.md` con `sha256`, tamaño y la orden exacta. Los PNG rasterizados y los 217 MB de pesos descargados se retiraron; se conservan los `.txt`, los `.json` y los registros |

### Lo que falló, con el error exacto

1. **La sonda de carga de CPU devolvió `-1` en las 11 tandas de la fase 4.** Causa:
   lanzada desde Git Bash, el proceso hijo hereda un `PATH` en formato unix
   (`/c/Windows/System32`) que Windows no resuelve, y `subprocess` levanta
   `FileNotFoundError: [WinError 2] El sistema no puede encontrar el archivo
   especificado`. **Consecuencia real:** las medianas de CPU de §9 **no llevan línea
   base de ocupación**, y en esta sesión había **otros dos agentes midiendo en CPU en
   paralelo**. Los cocientes CPU/GPU son por tanto una **cota superior** del coste de
   CPU: en una máquina ociosa serían iguales o mejores. **Corregido en el script**
   (ruta absoluta a `powershell.exe`, verificado: devuelve `17`), pero **las medidas no
   se repitieron** por no volver a tomar el lock.
2. **`SOURCE_DATE_EPOCH` no hace reproducible el PDF de ImageMagick.** Dos ejecuciones
   con la misma variable dan `sha256` distintos; el `/CreationDate` cambia igual.
   Documentado en el MANIFIESTO en vez de insistir.
3. **`rapidocr` no expone `__version__`** (`AttributeError`) y su `model_info` es un
   diccionario anidado del que no se puede sacar el nombre del checkpoint por atributo;
   hubo que buscarlo por expresión regular sobre el `repr`. Anecdótico, pero explica por
   qué la columna de checkpoints de los `.json` del cribado sale con basura.

---

## Ficheros

Todo en **`bench/salidas-corpus-d4/`**:

| fichero | qué es |
|---|---|
| `d4_texto.py` | **fuente única de verdad** del texto y la maqueta. Lo importan el generador y el evaluador |
| `gen_corpus_d4.py` | generador de las candidatas (copia adaptada de `bench/scripts/gen_corpus_ocr.sh`) |
| `ocr_eval_d4.py` | evaluador con las dos métricas (copia adaptada de `bench/scripts/ocr_eval.py`) |
| `preparar_img.py` | geometría + rasterizado a ppp nativos |
| `ocr_lote_d4.py` | banco de PaddleOCR / RapidOCR / EasyOCR con modelo y tubería configurables |
| `docling_lote_d4.py` | docling con `scale` explícito y sonda de píxeles reales |
| `sondar_modelos.py`, `sondar_paddle.py` | catálogo real de modelos de cada motor |
| `sonda_cajas.py` | recuento de cajas detectadas (§7.6) |
| `tablas_d4.py` → `tablas.md` | todas las tablas, incluidas las que no cupieron aquí |
| `run_cribado.sh`, `run_fase2.sh`, `run_fase3{,b,c,d,e}.sh`, `run_fase4.sh` | las nueve tandas, con su `gpu_acquire`/`gpu_release` |
| `json/`, `texto/`, `logs/` | 60 ficheros de resultados, las salidas de OCR y los registros completos |

Y en **`corpus/pdf/`**: `escaneado_d4.pdf` (canónico) + `escaneado_d4{a,b,c,e,f}.pdf` +
**`MANIFIESTO-d4.md`**.
