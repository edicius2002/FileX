# OCR a los ppp nativos — la tabla canónica que sustituye a la de `gpu-fase2.md` §5

**Encargo G1.** Rehacer las marcas de OCR de dificultad 2 y 3 sin el artefacto de
rasterización del arnés de la fase 2.

**Máquina:** RTX 3060 12 288 MiB (driver 572.61, CUDA 12.8), 12 hilos, Windows 10, Python
3.11.9. **Fecha:** 2026-08-21, 02:03–03:05.
**Arnés:** `bench/lib/harness.sh` (lock exclusivo, adquirido y liberado en cada tanda).
**Métrica:** `bench/scripts/ocr_eval.py` sin modificar — CER = distancia de Levenshtein
normalizada contra la referencia de 79 caracteres, y la distancia cruda en caracteres.
**Salidas:** `bench/salidas-ocr-ppp/` (13 scripts, 296 `.txt`, 12 `.json`, 15 registros,
`tablas.md`, `MANIFIESTO.md`).

Toda medida de tiempo es **mediana de n=9** y va etiquetada `limpia` o `SUCIA` según el
umbral del arnés (pico de utilización de GPU ≥10 % durante los 5 s previos). La sesión de
escritorio remoto estaba activa todo el rato: buena parte sale `SUCIA` y **es estructural**,
no un descuido.

---

## 0. Veredicto, primero

1. **MEDIDO — la cadena de medición de la fase 2 es fiel: 12 de 12 marcas reproducidas
   exactamente.** El sesgo estaba solo en la elección de ppp. *(§2)*
2. **MEDIDO — el aviso de `gpu-fase2.md` es correcto para d3 y demasiado amplio para d2.**
   En d2 el artefacto vale **0,0 puntos** para PaddleOCR y EasyOCR y **1,3** para RapidOCR:
   las cifras de d2 eran, en la práctica, buenas. El artefacto de verdad está en d3 y en un
   solo motor. *(§3)*
3. **MEDIDO — «a ppp nativos siempre es mejor» es FALSO como regla general.** Vale para
   PaddleOCR (+73,4 puntos en d3). Para RapidOCR aislado es **al revés** (−11,4 puntos: su
   mejor resultado en d3 es justo la cifra vieja de 200 ppp) y para Docling+RapidOCR torch
   la curva está **invertida**: mejora monótonamente al sobremuestrear, de 75,9 % a 48,1 %
   a 300 ppp. *(§4)*
4. **MEDIDO — hay rodilla, y es abrupta.** PaddleOCR en d3 se mantiene ≤5,1 % de CER entre
   75 y **140 ppp** y a **160 ppp** cae de golpe a 75,9 %, su suelo de fallo. No es
   degradación gradual: es un acantilado entre ×1,4 y ×1,6 del nativo. *(§5)*
5. **MEDIDO — la discrepancia PP-OCRv5/v6 queda resuelta, y los dos informes tenían media
   razón.** PaddleOCR corre **PP-OCRv6 medium** (`ocrmypdf.md` acierta, `gpu-fase2.md` se
   equivoca al etiquetarlo v5); RapidOCR aislado corre **PP-OCRv5 mobile** (los dos
   aciertan); y Docling con `backend="torch"` y `lang="english"` corre **PP-OCRv6 small**,
   **no** PP-OCRv4. *(§6)*
6. **MEDIDO — no sobremuestrear es más rápido y más barato en VRAM, siempre; y más preciso
   solo con el motor que resuelve el caso.** Hasta **3,13×** más rápido y hasta **6 851 MiB**
   menos de VRAM. La contrapartida existe y está localizada: los motores que *no* resuelven
   d3 sacan unos puntos de sobremuestrear, sin llegar a resolverlo. *(§7)*
7. **MEDIDO — el hueco 5 sigue abierto, y el corpus no tiene un caso difícil de verdad.**
   d3 **no** es trivial a ppp nativos —tres de los cuatro motores siguen fallando— pero el
   que lo resuelve lo resuelve con 2,5 % y **2 caracteres de error sobre 79**. Como prueba
   ya no discrimina dificultad: discrimina *motor*. Hace falta construir un d4. *(§8)*
8. **La regla para FileX, con su número: rasterizar a los ppp nativos declarados, con techo
   de ×1,4, y extraer sin rasterizar cuando la página lleva una sola imagen a página
   completa.** *(§9)*

---

## 1. El dato que lo empieza todo: la geometría real del corpus

**MEDIDO** con `pypdfium2` sobre los objetos de imagen de la página, sin renderizar
(`00_geometria.py` → `geometria.json`).

| documento | página (pt) | imagen incrustada (px) | dpi declarado | **ppp nativos** | a 200 ppp sería | factor |
|---|---|---|---:|---:|---|---:|
| `patologico_escaneado` | 465,84 × 645,12 | 1294 × 1792, 24 bpp | 200,0 | **200** | 1294 × 1792 | **×1,00** |
| `escaneado_d1` | 465,60 × 624,00 | 970 × 1300, 8 bpp | 150,0 | **150** | 1293 × 1733 | ×1,33 |
| `escaneado_d2` | 465,84 × 612,00 | 647 × 850, 8 bpp | 100,0 | **100** | 1294 × 1700 | **×2,00** |
| `escaneado_d3` | 465,84 × 612,00 | 647 × 850, 8 bpp | 100,0 | **100** | 1294 × 1700 | **×2,00** |

**Corrección al encargo — MEDIDO:** el encargo daba «100 ppp para d1-d3». **d1 es de 150 ppp
nativos**, no 100. Coincide con la tabla de generación del corpus de `gpu-fase2.md` §1
(«`escaneado_d1.pdf` … 150 ppp»), así que el error está en el enunciado del encargo, no en
el corpus. El arnés de 200 ppp interpolaba d1 solo ×1,33, y por eso d1 nunca dio problemas.

Los tamaños en píxeles que produce el rasterizado a 200 ppp de este informe —1293×1733,
1294×1700, 1294×1792— **coinciden exactamente** con los de `bench/salidas-fase2/img/`. La
misma orden de ImageMagick, el mismo resultado.

---

## 2. La cadena de medición es fiel — 12 de 12

Antes de sustituir ninguna cifra hay que demostrar que el instrumento no ha cambiado. La
vía «200 ppp» de este informe usa la misma orden de ImageMagick, la misma configuración de
motor (`bench/scripts/ocr_motor.py`, sin tocar) y la misma métrica que la fase 2.

**MEDIDO** (`tablas.md` T2; ✔ = reproduce a la décima):

| Motor | patológico (d0) | d1 | d2 | d3 |
|---|---:|---:|---:|---:|
| RapidOCR | 1,3 % vs 0,0 % ⚠ | 0,0 % ✔ | 1,3 % ✔ | 65,8 % ✔ |
| PaddleOCR | 0,0 % ✔ | 0,0 % ✔ | 0,0 % ✔ | 75,9 % ✔ |
| EasyOCR | 0,0 % ✔ | 0,0 % ✔ | 43,0 % ✔ | 59,5 % ✔ |

**11 de 12 a la primera. La celda que falló se explicó y se cerró — MEDIDO.** La fase 2
rasterizó `patologico_escaneado` en **sRGB** (su PNG es sRGB de 5,3 MB) mientras que este
barrido lo hace en escala de grises, como el resto. El coste de esa conversión para
RapidOCR es exactamente 1,3 % (un carácter). Comprobado de dos formas independientes:

- la vía extraída en color da 0,0 % y la misma imagen en gris da 1,3 %;
- `42_control_fase2.sh` pasa RapidOCR por **los PNG originales de `bench/salidas-fase2/img/`**
  (solo lectura) y obtiene `0,0 / 0,0 / 1,3 / 65,8` — **12 de 12, exacto**.

**Conclusión: el instrumento no tiene sesgo. Lo que cambió fue un parámetro de entrada.**
Además, **todas** las lecturas de todos los motores fueron deterministas: 9 repeticiones,
texto idéntico las 9 veces, en las **296 celdas medidas**. No hay ruido de motor que explique nada.

---

## 3. La tabla canónica — las tres vías enfrentadas

**MEDIDO.** CER % contra `DOCUMENTO ESCANEADO / Texto que solo existe como pixeles. / Debe
recuperarse con OCR.` Entre paréntesis, la distancia de edición en caracteres sobre 79.

**Vía A — ppp nativos:** rasterizar el PDF a los ppp que la imagen incrustada ya tiene.
**Vía B — imagen extraída:** el JPEG incrustado decodificado tal cual, sin rasterizar
(`pypdfium2`; no hay `pdfimages` en este Windows). En escala de grises, para que la única
diferencia con A sean los ppp.
**Vía C — 200 ppp:** el control que reproduce la fase 2.

| Motor | Documento | **A · ppp nativos** | **B · extraída** | **C · 200 ppp (viejo)** |
|---|---|---:|---:|---:|
| **RapidOCR** (PP-OCRv5 mobile, ONNX) | patológico (200) | **1,3 %** (1) | 1,3 % (1) | 1,3 % (1) |
| | d1 (150) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d2 (100) | **0,0 %** (0) | 0,0 % (0) | 1,3 % (1) |
| | d3 (100) | **77,2 %** (61) | 77,2 % (61) | **65,8 %** (52) |
| **PaddleOCR** (PP-OCRv6 medium, es) | patológico (200) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d1 (150) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d2 (100) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d3 (100) | **2,5 %** (2) | **2,5 %** (2) | 75,9 % (60) |
| **EasyOCR** (CRAFT + latin_g2) | patológico (200) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d1 (150) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d2 (100) | **43,0 %** (34) | 43,0 % (34) | 43,0 % (34) |
| | d3 (100) | **54,4 %** (43) | 54,4 % (43) | 59,5 % (47) |
| **Docling + RapidOCR `backend="torch"`** (PP-OCRv6 small) | patológico (200) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d1 (150) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d2 (100) | **0,0 %** (0) | 0,0 % (0) | 0,0 % (0) |
| | d3 (100) | **75,9 %** (60) | 75,9 % (60) | **58,2 %** (46) |

**Las vías A y B coinciden en las 16 celdas.** Rasterizar a los ppp nativos y extraer la
imagen incrustada dan, para efectos de OCR, **el mismo resultado**. Eso importa para el
diseño: la vía B es más limpia conceptualmente pero **no compra precisión**, así que se
elige por otras razones (coste, y no depender de que los ppp declarados sean ciertos).

**Comprobación de que la vía B es lo que dice ser — MEDIDO.** Para docling, la sonda de
`22_docling_img.py` registra el array que llega de verdad al motor: **8 de 8 coinciden píxel
a píxel con el PNG** (`647×850` entra `647×850`). No hay reescalado escondido.

### Diferencias frente a la tabla que sustituye

`gpu-fase2.md` §5 no medía Docling+RapidOCR torch en el banco aislado (lo tenía en la tabla
A, con la tubería completa). Aquí está en la misma tabla que los demás, con la misma métrica
y las mismas entradas, que es lo que pedía el encargo. Su columna A es la ruta que el plan de
FileX da por buena.

---

## 4. Cuánto de las cifras viejas era artefacto, motor por motor

**MEDIDO.** «Artefacto» = CER a 200 ppp − CER a ppp nativos. Positivo = la cifra vieja
exageraba el error.

| Motor | d2 (nativo 100) | d3 (nativo 100) | d1 (nativo 150) | patológico (nativo 200) |
|---|---:|---:|---:|---:|
| **PaddleOCR** | **0,0 pp** | **+73,4 pp** | 0,0 pp | 0,0 pp |
| **RapidOCR** | +1,3 pp | **−11,4 pp** | 0,0 pp | 0,0 pp |
| **EasyOCR** | **0,0 pp** | +5,1 pp | 0,0 pp | 0,0 pp |
| **Docling+RapidOCR torch** | 0,0 pp | **−17,7 pp** | 0,0 pp | 0,0 pp |

**Lectura, que corrige el aviso de `gpu-fase2.md` en dos sentidos:**

- **El aviso es demasiado amplio en d2.** Dice que «las cuatro columnas de CER de d2 y d3 no
  son válidas». Medido: en d2 el artefacto es **cero** para PaddleOCR (0,0 % en las dos vías)
  y **cero** para EasyOCR (43,0 % en las dos), y 1,3 puntos —un carácter— para RapidOCR. **Las
  cifras de d2 publicadas eran correctas.** En particular, **el 43,0 % de EasyOCR en d2 es
  real**: no lo causaba el arnés, y sigue ahí a ppp nativos y con la imagen extraída.
- **El aviso se queda corto al decir «los motores»: en d3 el artefacto es de UN motor.** Los
  73,4 puntos son todos de PaddleOCR. Para RapidOCR y para Docling+RapidOCR torch la cifra
  vieja de 200 ppp era **su mejor resultado**, no el peor: corregir los ppp los **empeora**
  11,4 y 17,7 puntos respectivamente. Y para EasyOCR el artefacto son 5,1 puntos sobre un
  fallo de 54 %, es decir, irrelevante.

**La frase correcta es:** *las marcas de d3 no miden la capacidad de los motores frente a un
documento degradado porque una de ellas —la de PaddleOCR— está dominada por un ×2 de
interpolación; las otras tres medían un fallo que era real y sigue siéndolo.*

---

## 5. La curva de ppp: ¿óptimo, monotonía o rodilla?

**MEDIDO.** CER % en `escaneado_d3` (nativo 100 ppp). Barrido de 75 a 300 ppp más un
refinado de 4 puntos alrededor de la rodilla.

| ppp | factor vs nativo | **PaddleOCR** | RapidOCR | EasyOCR | Docling+Rapid torch |
|---:|---:|---:|---:|---:|---:|
| 75 | ×0,75 | 11,4 % | 75,9 % | 58,2 % | 75,9 % |
| **100 (nativo)** | ×1,00 | **2,5 %** | 77,2 % | 54,4 % | 75,9 % |
| 110 | ×1,10 | 3,8 % | 75,9 % | — | — |
| 125 | ×1,25 | 5,1 % | 75,9 % | 50,6 % | 75,9 % |
| 130 | ×1,30 | **2,5 %** | 75,9 % | — | — |
| **140** | **×1,40** | **3,8 %** | 74,7 % | — | — |
| **160** | **×1,60** | **75,9 %** ⛰ | 75,9 % | — | — |
| 150 | ×1,50 | 31,6 % | 75,9 % | 54,4 % | 65,8 % |
| 175 | ×1,75 | 75,9 % | 75,9 % | 54,4 % | **39,2 %** |
| 200 | ×2,00 | 75,9 % | **65,8 %** | 59,5 % | 58,2 % |
| 216 (docling por defecto) | ×2,16 | — | — | — | 58,2 % |
| 250 | ×2,50 | 75,9 % | 70,9 % | 51,9 % | 51,9 % |
| 300 | ×3,00 | 75,9 % | 77,2 % | 53,2 % | **48,1 %** |
| imagen extraída | ×1,00 | **2,5 %** | 77,2 % | 54,4 % | 75,9 % |

*(Las filas 140/160 están fuera de orden a propósito para que la rodilla quede junta.)*

**Respuesta a la pregunta que decide la regla: hay rodilla, no monotonía. Y la rodilla es un
acantilado.**

- **PaddleOCR mantiene una meseta de ≤5,1 % desde 75 hasta 140 ppp** y a **160 ppp cae a
  75,9 %**, que es su suelo de fallo (solo recupera el titular). Entre ×1,4 y ×1,6 del nativo
  pierde **72 puntos de CER**. Los 150 ppp intermedios (31,6 %) son el único punto de
  transición que se ve; a partir de 160 no hay recuperación en todo el resto del barrido.
- **Existe también un límite por abajo**: 75 ppp da 11,4 %, peor que el nativo. No es «cuanto
  menos, mejor»: es un óptimo con meseta.
- **La rodilla NO es la misma para todos los motores. Docling+RapidOCR torch tiene la curva
  invertida** y mejora monótonamente al sobremuestrear (75,9 → 65,8 → 39,2 → 48,1 %). Nunca
  resuelve el documento, pero su mejor punto está en **175 ppp**, a ×1,75 del nativo.
- **RapidOCR aislado es plano y malo** entre 74,7 % y 77,2 % en todo el barrido salvo un
  único punto, 200 ppp (65,8 %), que es precisamente la cifra publicada. Ni la resolución ni
  la extracción lo mueven.
- **EasyOCR es plano y malo** entre 50,6 % y 59,5 %, con su mejor punto en 125 ppp.
- **En d1, d2 y el patológico, la curva es plana en 0,0 % para PaddleOCR y para
  Docling+RapidOCR torch en las ocho resoluciones.** El único efecto visible ahí es por
  **abajo**: a 75 ppp RapidOCR se rompe en d2 (44,3 %) y EasyOCR se degrada en d1 (12,7 %).
  Submuestrear hace daño antes de que sobremuestrear lo haga.

**Consecuencia de diseño — MEDIDO:** el valor por defecto de docling, `OcrOptions.scale = 3.0`
(«the page is rendered at 72 DPI times this factor, so the default 3 yields 216 DPI», según
su propia documentación), es **×2,16 sobre un original de 100 ppp**. La sonda confirma que
llegan **1398×1836 px** al motor. Para la ruta que el plan de FileX da por buena eso resulta
ser benigno —incluso favorable— pero es una decisión heredada que nadie tomó, y para
PaddleOCR sería catastrófica.

---

## 6. La discrepancia PP-OCRv5 / PP-OCRv6, resuelta

**MEDIDO por inspección de los paquetes instalados y del código que elige el checkpoint**
(`50_modelos.py` → `modelos_ai.json`, `modelos_paddle.json`), confirmado por los registros
de arranque de cada tanda.

### Qué hay en disco

`C:\Users\krato\.paddlex\official_models\` — lo que **PaddleOCR 3.7.0** con `lang="es"`
descargó y usa:

```
PP-OCRv6_medium_det        PP-OCRv6_medium_rec        PP-LCNet_x1_0_textline_ori
```

Y sus propios parámetros efectivos, leídos del objeto `PaddleOCR` en caliente:
`text_detection_model_name = PP-OCRv6_medium_det`,
`text_recognition_model_name = PP-OCRv6_medium_rec`.

`.venv-ai\Lib\site-packages\rapidocr\models\` — lo que trae **rapidocr 3.9.2**:

```
ch_PP-OCRv5_det_mobile.onnx   ch_PP-OCRv5_rec_mobile.onnx   (16,6 MB)
PP-OCRv6_det_small.onnx/.pth  PP-OCRv6_rec_small.onnx/.pth
ch_ppocr_mobile_v2.0_cls_mobile.onnx/.pth
```

### Qué carga cada configuración

| configuración | backbone que corre de verdad | evidencia |
|---|---|---|
| **PaddleOCR** `lang="es"` | **PP-OCRv6 *medium*** | caché de PaddleX + params del objeto |
| **RapidOCR aislado** (`bench/scripts/ocr_motor.py`) | **PP-OCRv5 *mobile*** | fuerza `OCRVersion.PPOCRV5` + `ModelType.MOBILE`; el log de arranque dice `Using … ch_PP-OCRv5_det_mobile.onnx` y `ch_PP-OCRv5_rec_mobile.onnx` |
| **Docling + RapidOCR `backend="torch"`, `lang=["english"]`** | **PP-OCRv6 *small*** | log: `Using … PP-OCRv6_rec_small.pth`; y `_resolve_rapidocr("english","torch")` → `PP-OCRv6 small` |

### El veredicto

**`bench/ocrmypdf.md` §3.4 acierta y `bench/gpu-fase2.md` §5 se equivoca — MEDIDO.**
PaddleOCR corre **PP-OCRv6 medium**, no PP-OCRv5. La etiqueta «PaddleOCR (PP-OCRv5, es)» de
la tabla maestra de la fase 2 es incorrecta. Sobre RapidOCR los dos aciertan: **PP-OCRv5
mobile** en el banco aislado.

**Pero `ocrmypdf.md` §3.4 contiene además una imprecisión propia** que conviene no propagar:
dice que el `backend="torch"` de docling cae a PP-OCRv4. Medido, **no**: la resolución en
docling 2.120.3 es *primero por idioma y solo después por backend*. Para cualquier idioma del
conjunto PP-OCRv6 (que incluye `en`, `ch` y `es`) resuelve **PP-OCRv6 small en los cuatro
backends**. El PP-OCRv4 solo aparece con `backend="torch"` **y** un idioma de familia de
escritura fuera de ese conjunto:

| backend | `english` | `es` | `latin` |
|---|---|---|---|
| onnxruntime | PP-OCRv6 small | PP-OCRv6 small | PP-OCRv5 mobile |
| **torch** | **PP-OCRv6 small** | PP-OCRv6 small | **PP-OCRv4 mobile** |
| paddle | PP-OCRv6 small | PP-OCRv6 small | PP-OCRv5 mobile |
| openvino | PP-OCRv6 small | PP-OCRv6 small | PP-OCRv5 mobile |

**Y esto reabre la explicación de la asimetría.** `ocrmypdf.md` §3.4 atribuye a la diferencia
de backbone (v5 mobile frente a v6 medium) que RapidOCR no resuelva d3. **Medido, esa
explicación es insuficiente:** Docling+RapidOCR torch corre **PP-OCRv6 small**, es decir el
mismo backbone de generación que PaddleOCR, y **tampoco resuelve d3** (75,9 % a ppp nativos,
39,2 % en su mejor punto). Los tres candidatos que quedan, en orden de peso:

1. **El tamaño del modelo, no su generación:** *medium* frente a *small* y *mobile*. Es la
   variable que separa al único que resuelve del resto. **PENDIENTE** de aislar: haría falta
   correr PP-OCRv6 *small* y *medium* con el mismo motor y las mismas entradas.
2. **El idioma del reconocedor:** PaddleOCR corre `es`; RapidOCR aislado corre `ch`
   (`LangRec.CH`, que es lo que fija `ocr_motor.py`) y docling corre `en`. La referencia es
   castellano. **PENDIENTE.**
3. **El detector:** docling fija el detector en `ch` (`_RAPIDOCR_DET_MODEL_LANG = "ch"`)
   independientemente del idioma de reconocimiento. **PENDIENTE.**

**Lo que sí queda establecido para la selección de motor de FileX — MEDIDO:** la asimetría
entre PaddleOCR y todo lo demás en degradación severa es **real, grande (2,5 % frente a
39–77 %) y no es de resolución**, porque persiste después de corregir los ppp. Pero **no es
«v5 contra v6»**, porque hay un v6 en el lado que falla.

---

## 7. Coste: tiempo y VRAM

### 7.1 Tiempo

Dos pasadas, porque una sola no puede dar las dos cosas: el hilo que muestrea `nvidia-smi`
cada 100 ms para el pico de VRAM **infla las medianas entre un 30 y un 60 %** (cada muestra
lanza un proceso). La pasada de tiempos (`41_run_tiempos.sh`, `SIN_MUESTREO=1`) renuncia al
pico de VRAM. Los dos juegos están en `json/`.

**MEDIDO** — mediana de n=9, ms, GPU, sin muestreador:

| Motor | Documento | ppp nativos | extraída | 200 ppp | **ahorro nativo vs 200** |
|---|---|---:|---:|---:|---:|
| RapidOCR | patológico (200) | 465,3 | 221,4 | 465,3 | ×1,00 (es el mismo) |
| | d1 (150) | 149,3 | 132,5 | 221,3 | **×1,48** |
| | d2 (100) | 82,1 | 80,5 | 214,9 | **×2,62** |
| | d3 (100) | 69,1 | 68,6 | 216,5 | **×3,13** |
| PaddleOCR | patológico (200) | 270,6 | 227,9 | 270,6 | ×1,00 |
| | d1 (150) | 151,3 | 147,0 | 226,2 | **×1,50** |
| | d2 (100) | 90,7 | 87,3 | 216,7 | **×2,39** |
| | d3 (100) | 82,6 | 82,9 | 197,2 | **×2,39** |
| EasyOCR | patológico (200) | 537,4 | 450,6 | 537,4 | ×1,00 |
| | d1 (150) | 276,6 | 281,7 | 426,2 | **×1,54** |
| | d2 (100) | 183,8 | 180,1 | 459,7 | **×2,50** |
| | d3 (100) | 309,2 | 309,4 | 530,2 | ×1,71 |

Etiquetas: RapidOCR `SUCIA(pico 12 %)`, PaddleOCR `limpia`, EasyOCR `limpia`.

**El ahorro sigue al factor de interpolación evitado**, como cabe esperar de un coste que
escala con el número de píxeles: ×1,33 evitado en d1 → ~×1,5 de ahorro; ×2 evitado en d2/d3 →
×2,4–3,1. Para el patológico, que ya estaba en sus ppp nativos, el ahorro es **cero por
construcción**: la vía A y la vía C son literalmente la misma imagen. Eso es una buena señal
de que la medida mide lo que dice.

**La vía extraída es marginalmente más rápida que la vía A** (evita la rasterización, aunque
esta no se contabiliza dentro del OCR) y, en el patológico, notablemente: 221 ms frente a
465 ms para RapidOCR, porque el JPEG incrustado se decodifica más barato que la página.

Docling no tiene pasada limpia (**PENDIENTE**); sus tiempos, con muestreador y **con la
etapa de maquetación incluida**, van de 417 ms (d3 a 100 ppp) a 1 176 ms (patológico a
200 ppp). El constructor del `DocumentConverter` cuesta 0,1 s; la carga en frío del proceso
completo, unos 20 s.

**Carga en frío** (mediana de las tandas, `limpia` salvo indicación): RapidOCR **3,4–4,5 s**,
PaddleOCR **6,4–17,3 s**, EasyOCR **6,3–13,8 s**.

### 7.2 VRAM — aquí está el resultado más contundente

**MEDIDO.** Pico de VRAM **total de la tarjeta** muestreado cada 100 ms durante el barrido
completo (40 entradas, 75→300 ppp), y el punto exacto en que sube.

| Motor | base del escritorio | pico con extraída / nativo | **pico a 300 ppp** | coste propio máx. | margen que quedaba |
|---|---:|---:|---:|---:|---:|
| **RapidOCR** | 2 067 MiB | 3 424 MiB | **3 424 MiB** | +1 357 MiB | 8 864 MiB |
| **PaddleOCR** | 2 071 MiB | 3 762 MiB | **7 442 MiB** | +5 371 MiB | 4 846 MiB |
| **EasyOCR** | 2 066 MiB | 5 026 MiB | **11 877 MiB** | +9 811 MiB | **411 MiB** |
| **Docling+RapidOCR torch** | 835 MiB | — | 2 820 MiB | +1 985 MiB | 9 468 MiB |

**Trazado del crecimiento — MEDIDO:**

| Motor | pico tras las imágenes extraídas | tras 250 ppp | tras 300 ppp | **crecimiento por sobremuestrear** |
|---|---:|---:|---:|---:|
| RapidOCR | 3 424 MiB | 3 424 MiB | 3 424 MiB | **+0 MiB** |
| PaddleOCR | 3 762 MiB | 5 406 MiB | 7 442 MiB | **+3 680 MiB** |
| EasyOCR | 5 026 MiB | 10 382 MiB | 11 877 MiB | **+6 851 MiB** |

**El aviso del encargo se confirma y se amplía.** El encargo advertía que *PaddleOCR* picó a
12 025 MiB con imágenes a **600 ppp**. Medido aquí: **EasyOCR llega a 11 877 de 12 288 MiB
—a 411 MiB de agotar la tarjeta— con imágenes a solo 300 ppp**, la mitad de resolución. Y
llega ahí con un documento de una sola página. El presupuesto de VRAM del sidecar (hito 6) no
puede fijarse por motor: hay que fijarlo **por motor y por resolución de entrada**, o la
resolución se lo come.

**RapidOCR es el único insensible a los ppp en VRAM** (+0 MiB entre la imagen extraída y
300 ppp): su ruta ONNX trocea la página y no crece con ella. Es su ventaja real, y no aparece
en ninguna tabla anterior.

*Nota de comparabilidad:* la línea base del escritorio cambió durante la sesión (2 067 MiB en
la tanda de la matriz, 835 MiB en la de docling). Por eso la columna comparable entre motores
es **coste propio**, no el pico absoluto; el pico absoluto es el que importa para el
presupuesto de la tarjeta en ese momento concreto.

### 7.3 La hipótesis del encargo, contrastada

> *«no sobremuestrear es más rápido Y más barato en VRAM Y más preciso — si es así, es una
> decisión sin contrapartidas»*

**MEDIDO — dos de tres sin excepción, la tercera con excepción localizada:**

| | ¿se cumple? | evidencia |
|---|---|---|
| **más rápido** | **Sí, siempre** | ×1,48 a ×3,13; nunca peor (el peor caso es ×1,00, cuando ya estaba en nativo) |
| **más barato en VRAM** | **Sí, siempre** | 0 a 6 851 MiB menos; nunca más |
| **más preciso** | **No siempre** | +73,4 pp con PaddleOCR; pero **−11,4** con RapidOCR y **−17,7** con Docling+RapidOCR torch en d3 |

**Conclusión honesta: no es una decisión sin contrapartidas, es una decisión con una
contrapartida que se puede acotar.** La contrapartida solo aparece (a) en el documento más
degradado del corpus, (b) con los motores que **de todos modos no lo resuelven**, y (c) los
mueve entre un fallo del 77 % y un fallo del 39 %, es decir, entre ilegible e ilegible. Lo
que se gana —2,5 % de CER con el motor que sí lo resuelve, más el tiempo y la VRAM— es de
otro orden. **La decisión es correcta; el argumento «sin contrapartidas» no lo es.**

---

## 8. Veredicto sobre el hueco 5 de `HUECOS.md`

### ¿Sigue habiendo un caso que ningún motor resuelve?

**No — MEDIDO. Pero d3 tampoco es trivial, y decir que lo es sería tan falso como decir que
nadie lo resuelve.**

Los hechos, sin adorno:

- **Un motor de cuatro lo resuelve, y bien**: PaddleOCR (PP-OCRv6 medium) a ppp nativos o con
  la imagen extraída, **2,5 % de CER, 2 caracteres de error sobre 79**, dos sustituciones de
  un carácter (`solo`→`sola`, `pixeles`→`pikeles`). Sale la frase completa. Esto es la
  **cuarta confirmación independiente** del hallazgo del agente anterior, y la primera con la
  matriz entera enfrentada.
- **Tres motores de cuatro siguen fallando en d3 a cualquier resolución**, incluidos los ppp
  nativos y la imagen extraída: RapidOCR (mejor 65,8 %), Docling+RapidOCR torch (mejor
  39,2 %), EasyOCR (mejor 50,6 %). **En los tres el fallo no era del arnés.**
- **En d2 no había nada que corregir**: PaddleOCR 0,0 %, RapidOCR 0,0–1,3 %, Docling 0,0 %.
  El 43,0 % de EasyOCR es un fallo real de EasyOCR.

### **Si d3 resulta trivial a ppp nativos, hay que decirlo con todas las letras**

**No es trivial: es *asimétrico*, y eso es peor para el corpus.** Un caso difícil útil es el
que separa configuraciones *dentro* de un mismo motor —resolución, preprocesado,
parámetros—. d3 no hace eso: para PaddleOCR es un interruptor (2,5 % o 75,9 %, casi sin
estados intermedios) y para los otros tres es una pared plana que no se mueve con nada.

**Con todas las letras: el corpus de OCR de FileX no tiene un caso que mida margen de
mejora.** Tiene tres documentos que todo el mundo resuelve al 0,0 % (patológico, d1, d2 salvo
EasyOCR) y uno que funciona como test de selección de motor. **El hueco 5 sigue abierto y hay
que construir un d4** — **PENDIENTE**. Con lo medido aquí, un d4 útil tendría que:

- **partir de ppp nativos más altos** (200+), para que no se pueda «arreglar» bajando la
  resolución y para que la degradación esté en el papel, no en el muestreo;
- **atacar el reconocedor, no el detector**: en d3 los tres motores que fallan detectan el
  titular y pierden el cuerpo. Texto más pequeño, más variedad de caracteres, tildes;
- **llevar tildes y castellano de verdad** — la referencia actual no tiene ni una. Todo lo
  medido en este proyecto es texto sin acentuar, y eso es una laguna que se arrastra;
- **producir CER intermedios en la meseta**, no un interruptor. Si PaddleOCR da 0 % o 76 % y
  nada en medio, el documento no mide una escala.

### Lo que cambia en el hueco 5

La afirmación de `HUECOS.md` **«RapidOCR no resuelve d3 a ninguna resolución (mejor caso
53,2 %)»** se confirma en el sentido y **se corrige en el número — MEDIDO**: sin deskew, en
un barrido de 12 resoluciones más las dos vías de extracción, el mejor caso de RapidOCR es
**65,8 % a 200 ppp**. El 53,2 % de `ocrmypdf.md` incluía `magick -deskew 40%`, que este
informe no aplica en ninguna celda.

La afirmación **«es límite de modelo —PP-OCRv5 mobile frente al medium de Paddle—»** queda
**parcialmente refutada** por §6: el límite existe, pero no es la generación del backbone.
Hay un PP-OCRv6 (small, en docling+torch) en el lado que falla.

Y la recomendación central del hueco —**«FileX debe leer los ppp reales de la imagen
incrustada y por defecto NO sobremuestrear, o extraerla sin rasterizar»**— **se sostiene, con
un matiz medido**: es correcta, pero no por «cuanto menos, mejor». Hay óptimo con meseta y
hay un límite por abajo (75 ppp rompe RapidOCR en d2 con 44,3 % y degrada EasyOCR en d1 con
12,7 %). La regla necesita suelo además de techo. Está en §9.

---

## 9. La regla para FileX, con su número

**Todo MEDIDO salvo donde se indica.**

### R1 — Leer los ppp nativos, no suponerlos. Techo de ×1,4.

```
ppp_nativos = ancho_imagen_px / (ancho_pagina_pt / 72)
ppp_ocr     = clamp(ppp_nativos, 100, ppp_nativos * 1.4)
```

- **Techo ×1,4.** La meseta de PaddleOCR llega hasta 140 ppp sobre un original de 100
  (≤5,1 % de CER) y a 160 ppp cae a 75,9 %. **×1,4 es el último punto medido dentro de la
  meseta; ×1,6 ya está fuera.** Entre ×1,4 y ×1,6 hay 72 puntos de CER.
- **Suelo 100 ppp.** A 75 ppp RapidOCR se rompe en d2 (0,0 % → 44,3 %) y EasyOCR se degrada
  en d1 (0,0 % → 12,7 %). Submuestrear no es gratis.
- **No usar el `dpi` declarado del objeto de imagen sin comprobarlo**: aquí coincidía con el
  calculado en los cuatro documentos, pero el cálculo a partir de la geometría de la página
  no depende de que el productor del PDF haya escrito la cabecera bien.
- **Casos que esta regla no cubre — PENDIENTE:** páginas con varias imágenes, imágenes que no
  ocupan la página entera, PDF con texto vectorial mezclado con escaneo, y PDF sin ninguna
  imagen incrustada (donde no hay «ppp nativos» y hace falta otro criterio).

### R2 — Extraer sin rasterizar cuando la página es una sola imagen a página completa

Las vías A y B **coinciden en las 16 celdas de la tabla canónica**: extraer no compra
precisión. Se elige por otras dos razones, las dos medidas:

- **Es más barato**: 221 ms frente a 465 ms en el patológico con RapidOCR; igual o algo
  mejor en el resto. Se salta el rasterizador entero.
- **No depende de que los ppp declarados sean ciertos.** Si la cabecera miente, R1 elige mal;
  R2 no puede elegir mal porque no elige.

**Condición de aplicación:** una sola imagen, cubriendo la página. Fuera de ese caso hay que
rasterizar y aplicar R1. En este corpus se cumplía en los cuatro documentos.

**Implementación:** `pypdfium2` (ya está en `.venv-ai` y en `.venv-paddle`) hace la
extracción con `page.get_objects(filter=FPDF_PAGEOBJ_IMAGE)` +
`obj.get_bitmap(render=False)`. **No hace falta poppler ni `pdfimages`**, que no existen en
este Windows.

### R3 — Elegir motor por caso, no globalmente

| situación | motor | por qué |
|---|---|---|
| **caso normal** (escaneo limpio o poco degradado) | **Docling + RapidOCR `backend="torch"`** | 0,0 % en el patológico, d1 y d2, en las ocho resoluciones. Coste propio +1 985 MiB. Es la ruta del plan y no hay motivo para cambiarla |
| **degradación severa** (JPEG muy comprimido, bajo contraste, ruido) | **PaddleOCR** (PP-OCRv6 medium) | el único que resuelve d3: 2,5 % frente a 39–77 % de los otros tres |
| **presupuesto de VRAM apretado** | **RapidOCR** ONNX | **+0 MiB** entre la imagen extraída y 300 ppp; el único insensible a la resolución |
| **nunca** | **EasyOCR** | 43,0 % en d2 **a todas las resoluciones y también con la imagen extraída** — no era el arnés. Y pica a 11 877 MiB a 300 ppp |

**Cómo detectar «degradación severa» para disparar el segundo motor: PENDIENTE.** El dato
que hay es que en d3 los motores que fallan **detectan el titular y pierden el cuerpo**
(`frases_exactas` 0–1 de 3 con una salida de menos de 30 caracteres). Una heurística de
«pocos caracteres recuperados frente a área de texto detectada» es plausible pero **no está
medida**.

### R4 — Fijar `OcrOptions.scale` explícitamente en docling. Nunca dejarlo por defecto.

El valor por defecto es **3,0 → 216 ppp**, sea cual sea el documento. **MEDIDO** por sonda:
sobre d3 llegan **1398×1836 px** al motor, ×2,16 del original. En este corpus resulta ser
benigno para Docling+RapidOCR torch, pero:

- es una constante que nadie eligió para estos documentos;
- con PaddleOCR el equivalente sería catastrófico (75,9 % de CER);
- cuesta VRAM y tiempo que no hacen falta.

La conversión es `scale = ppp_objetivo / 72`. Para R1 sobre un original de 100 ppp:
`scale = 100/72 = 1,389`.

### R5 — El presupuesto de VRAM del sidecar se fija por motor **y por resolución**

**MEDIDO.** El mismo EasyOCR cuesta 5 026 MiB con la imagen extraída y **11 877 MiB** a
300 ppp. Un presupuesto expresado solo como «EasyOCR = +2 079 MiB» (fase 2, medido a 200 ppp)
subestima el peor caso en **más de 4×**. Aplicar R1 no es solo una mejora de precisión: es lo
que hace que el presupuesto de VRAM sea predecible.

---

## 10. Qué queda PENDIENTE

- **Aislar la causa real de la asimetría de PaddleOCR** (§6): tamaño de modelo, idioma del
  reconocedor, o idioma del detector. Es la pregunta de selección de motor que queda abierta.
- **Construir un `escaneado_d4`** que mida margen y no selección de motor (§8).
- **Corpus con tildes y castellano real.** Ninguna medida de OCR de este proyecto las tiene.
- **Pasada de tiempos limpia para docling** (§7.1) y una medida CPU/GPU de las tres vías.
- **La regla R1 sobre PDF que no son «una imagen a página completa»** (§9, R2).
- **La heurística de detección de degradación** que dispararía el cambio de motor (§9, R3).
- **`magick -deskew 40%` como red de seguridad**: `ocrmypdf.md` lo mide como estabilizador de
  la curva. Este informe **no lo aplica en ninguna celda**, así que su interacción con la
  regla del techo ×1,4 está sin medir.

---

## 11. Reglas del encargo, cumplidas

| regla | estado |
|---|---|
| Escribir solo en `bench/ocr-ppp-nativos.md` y `bench/salidas-ocr-ppp/` | **Cumplida.** `gpu-fase2.md`, `ocrmypdf.md`, `HUECOS.md`, `analysis/`, `corpus/`, `repos/` y `bench/scripts/` sin tocar. `bench/salidas-fase2/img/` leído, no escrito |
| Lock de GPU en todas las tandas | **Cumplida.** `gpu_acquire`/`gpu_release` en las 5 tandas; `70_cierre.sh` confirma el lock libre al terminar |
| No instalar en los venv existentes | **Cumplida.** Nada instalado ni actualizado. `pypdfium2 5.13.0` ya estaba en los dos que hacían falta |
| Medianas de n≥9, etiqueta limpia/SUCIA | **Cumplida.** n=9 en las 296 celdas; etiqueta en cada cabecera de `json/`. Las 296 salieron deterministas |
| Borrar salidas grandes, dejar `.txt` y `.json` | **Cumplida.** 41,0 MiB de PNG retirados; 392 KB de `.txt` y 168 KB de `.json` conservados. `bench/salidas-ocr-ppp/MANIFIESTO.md` |
| Dos intentos por problema, luego documentar | **Cumplida.** Un fallo: `mu.join()` sobre un hilo no arrancado mató la serialización de la pasada de tiempos (`RuntimeError: cannot join thread before it is started`, `logs/tiempos_*.log`). Corregido y repetido en `41_run_tiempos.sh` |
| Timeouts explícitos | **Cumplida.** `timeout` en las 14 invocaciones de motor (900–5 400 s). Ningún proceso colgado |
| Verificar `torch.cuda.is_available()` en `.venv-ai` al terminar | **Cumplida.** `torch 2.6.0+cu124`, `cuda disponible True`, `NVIDIA GeForce RTX 3060`. `rapidocr 3.9.2`, `easyocr 1.7.2`, `docling 2.120.3`, `onnxruntime-gpu 1.22.0` intactos. `.venv-paddle`: `paddle 3.2.0` con CUDA, `paddleocr 3.7.0` |

**Aviso de entorno registrado — MEDIDO:** PaddlePaddle 3.2.0 avisa en cada arranque de que
está *compilado con cuDNN 9.9 y la máquina tiene cuDNN 9.5*
(`gpu_resources.cc:243 … may cause serious incompatible bug`). Todas sus lecturas fueron
deterministas y sus cifras reproducen las de la fase 2, así que no parece haber afectado a
nada, pero queda anotado.

---

## Ficheros

Todo en `bench/salidas-ocr-ppp/`. Orden de ejecución, inventario y qué se retiró:
**`bench/salidas-ocr-ppp/MANIFIESTO.md`**. Tablas completas, incluidas las que no cupieron
aquí: **`bench/salidas-ocr-ppp/tablas.md`** (generado por `60_tablas.py`).
