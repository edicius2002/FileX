# El `pHYs` fuera de Tesseract: PaddleOCR, RapidOCR y EasyOCR son inmunes

**Encargo B19 (G4).** `bench/psm-y-rasterizador.md` §6.5 y §9 cerraron con este
pendiente, y `bench/corpus-d5.md` §4.1 lo dejó como lo primero que había que
comprobar:

> *«No se midió el efecto del `pHYs` sobre PaddleOCR, RapidOCR ni EasyOCR. Si vale 33
> puntos en Tesseract, hay que comprobar si vale algo en los demás — y todo el corpus
> de este proyecto está rasterizado con la variante `im`, es decir, sin declarar
> resolución.»*

**Máquina:** RTX 3060 12 288 MiB (driver 572.61), 12 hilos, Windows 10, Python 3.11.9.
**Fecha:** 2026-08-23, 06:30–07:50.
**Dispositivo, fijado y declarado** (`CLAUDE.md` trampa 11): los tres motores GPU, en
**`cuda`**, con el **lock de GPU tomado** (`G4-B19-phys-multimotor`, `G4-B19-via-color`,
`G4-B19-canales2`). Tesseract, en **CPU**; su tanda **no tomó el lock** a propósito,
para no bloquear al agente que trabaja en `filex/`.

**Motores.** PaddleOCR 3.7.0 / paddlepaddle-gpu 3.2.0 (`PP-OCRv6_medium_det` +
`_rec`, defectos del paquete) en `.venv-paddle`; RapidOCR 3.9.2 (`PP-OCRv6 small`,
ONNX Runtime GPU 1.22.0, **con la corrección R6**) y EasyOCR 1.7.2 (CRAFT +
`latin_g2`, torch 2.6.0+cu124) en `.venv-ai`; Tesseract 5.5.0.20241111 nativo de
Windows con el `tessdata` de PDFgear vía `TESSDATA_PREFIX`, idioma por lista blanca
(`CLAUDE.md` trampa 18). **No se instaló nada en ningún venv.**

**Evaluador — declarado, como pide el encargo.** `bench/scripts/ocr_eval.py`
**no se ha abierto ni usado**: es ciego a las tildes (`CLAUDE.md` trampa 10). Se usa
`bench/salidas-corpus-d4/ocr_eval_d4.py` **copiado byte a byte** a
`bench/salidas-phys-multi/ocr_eval_d4.py`
(`sha256 350354b261aef60b018b196204648c4c27effc0683f93a4fbcb5f2d551a30d82`), junto con
`d4_texto.py` (`sha256 fa4b8d5d74980b29f0e640911c42ea07e59ca3910f364bd599407cb79c3cf011`).
**La lectura que se publica aquí es `cer_acentos_pct`**: normalización NFC, minúsculas,
se conserva `[a-z0-9áéíóúüñ ]`. La lectura `ascii` —idéntica a la de `ocr_eval.py`—
está en el JSON de las 462 celdas. El envoltorio `ocr_eval_pm.py` **no reimplementa
nada**: solo añade un mapa **cerrado** documento → referencia, en vez del
`ref_de_nombre` que decide por la subcadena `"d4"` y que ya produjo un 94,94 % espurio.

**462 celdas con mediana de n=9, las 462 deterministas, 0 fallidas**, más tres sondas
de n=1 declaradas como sondas.

---

## 0. Veredicto, primero

> **1 — MEDIDO: los tres motores son INMUNES al `pHYs`, y no es una deducción: es que
> ninguno lo consulta.** En las **300 celdas** de la rejilla principal (3 motores × 2
> vías × 50 rásteres), **las 18 filas (motor × documento) producen UN SOLO `md5` de
> texto de salida**. No «CER parecido»: **la misma cadena de bytes**, con el `pHYs`
> puesto a `unidad=0`, quitado del todo, o declarando 70, 100, 150, 200, 240, 250, 300
> y 400 ppp sobre los **mismos IDAT**. **Recorrido de CER: 0,00 puntos en las 36 filas
> (motor × vía × documento).** *(§3)*

> **2 — MEDIDO, sondeado en ejecución y no deducido: el metadato les llega delante y
> no lo miran.** RapidOCR y EasyOCR abren el PNG con PIL, que **sí parsea el `pHYs`** y
> lo deja en `img.info['dpi']` (unidad=1) o `img.info['aspect']` (unidad=0). Un
> diccionario espía sobre ese `.info` registra que los dos motores lo consultan **cinco
> veces por imagen** —`interlace`, `exif` (×2), `Raw profile type exif`,
> `XML:com.adobe.xmp`— y **ni una sola vez `dpi` ni `aspect`**. PaddleOCR no llega ni a
> eso: lee los bytes con `open('rb')` y decodifica con `cv2.imdecode`, y el
> decodificador de OpenCV **no tiene ningún canal de salida para el `pHYs`**. *(§2)*

> **3 — MEDIDO, y es el control que hace válido lo anterior: los MISMOS ficheros SÍ
> mueven a Tesseract.** 150 celdas, `rc = 0` en las 150. **10 de las 18 filas
> (documento × `--psm`) cambian**, con un recorrido de hasta **47,15 puntos**
> (`escaneado_d4`, `psm 3`), y el paso de «sin declarar» a «resolución verdadera»
> vale **33,22 puntos** — **el número de G2, reproducido a la centésima sobre ficheros
> generados por otra ruta.** *(§4)*

> **4 — La consecuencia, sin rodeos: NINGUNA tabla de CER de Tesseract del proyecto es
> comparable con una de PaddleOCR, RapidOCR o EasyOCR si no declara el `pHYs` de su
> ráster** — y **la inmensa mayoría no lo declara**, porque todo el corpus está
> rasterizado con `magick -density N`, que escribe `unidad=0`. La lista de secciones
> afectadas, con sus cifras, está en §6. *(§6)*

Y dos que no venían en el encargo, uno de ellos **refutando el marco con el que
empecé**:

> **5 — MEDIDO, y REFUTA mi propia premisa de que «la vía de entrada da igual».** Sobre
> los 50 rásteres del corpus, en **escala de grises**, `ruta` y `array` dan el mismo
> `md5` en **150 de 150 pares**. Pero eso es un **artefacto del corpus**: en gris
> R=G=B y un intercambio RGB/BGR es invisible. Con un ráster **en color**, la vía deja
> de ser neutra en **dos de los tres motores**: RapidOCR pierde **12,58 puntos** por la
> ruta si el PNG está en **modo paleta**, y EasyOCR **nunca** coincide consigo mismo
> entre ruta y array (3,36 puntos), porque construye su entrada de forma distinta en
> cada rama. PaddleOCR es el único con 0,00. *(§5)*

> **6 — MEDIDO: `pHYs` con `unidad=0` y `pHYs` ausente son EXACTAMENTE lo mismo para
> Tesseract — 18 de 18 filas con `md5` idéntico.** Nadie los había separado; el
> proyecto hablaba de «no declara resolución» sin distinguir «no lo dice» de «no está».
> **No son distintos, y ahora está medido.** *(§4.2)*

---

## 1. Cómo se midió

### 1.1 El diseño, y la decisión que lo hace interpretable

| | |
|---|---|
| documentos | `escaneado_d3` (100 ppp nativos, ref. **79 car.** ‡), `escaneado_d4` (200, 610), `escaneado_d4c` (200, 610), `escaneado_d4e` (200, 610), `escaneado_d4f` (**240**, 610) |
| factores `k` | ×1,00 en los cinco **+ ×1,25 sobre `escaneado_d4`** (ráster remuestreado, 250 ppp) |
| variantes de cabecera | `sin` (lo que escribe `magick`: `pHYs unidad=0`), `ninguno` (**trozo `pHYs` eliminado**), y `unidad=1` a **70, 100, 150, 200, 300, 400** ppp **más el valor VERDADERO** de cada ráster (240 en `d4f`, 250 en `d4`×1,25) |
| vías de entrada | **`ruta`** (el motor abre el fichero) y **`array`** (`cv2.imread(..., IMREAD_COLOR)`, ndarray BGR) |
| motores | PaddleOCR, RapidOCR, EasyOCR **en `cuda`** · Tesseract **en CPU**, `--psm 3`, `6` y `11` |
| celdas | **300** (rejilla GPU) + **150** (control Tesseract) + **12** (tanda E, color) = **462**, mediana de **n=9** |

**‡ `escaneado_d3` lleva la referencia de 79 caracteres** y cuantiza a **1,27 puntos
por carácter** (`CLAUDE.md` trampa 9). Está dentro porque es el documento que más
discrimina de todo el proyecto para RapidOCR y PaddleOCR (recorre de 2,53 a 75,95 a
lo largo de `k`), y **toda conclusión que dependiera solo de él iría marcada**. No
hace falta: **los otros cuatro llevan la referencia de 610 caracteres**, que cuantiza
a 0,16, y dan el mismo resultado.

**La decisión de diseño: las variantes se generan por CIRUGÍA DE BYTES, no
re-rasterizando.** `preparar_pm.py` rasteriza **una vez** por (documento, factor) con
la orden del corpus —`magick -density N x.pdf[0] -colorspace Gray -alpha remove
-background white -flatten`— y después reescribe **solo el trozo `pHYs`**, recalculando
el CRC y dejando los IDAT intactos. Así la identidad de los píxeles **no es una medida,
es constructiva**, y aun así se comprueba: **50 de 50 ficheros con el `md5` de los IDAT
idéntico al base**, y **6 de 6 raíces con un solo `md5` del array decodificado** por
los tres caminos (`cv2` color, `cv2` gris, PIL). *(`sonda_pixeles_pm.py`,
`json/sonda_pixeles.json`.)*

Es la diferencia con el método de G2, que movía la resolución con la bandera
`-c user_defined_dpi=N` de Tesseract: **aquí la variable es el fichero**, que es lo que
un motor cualquiera puede leer, y no una bandera que solo Tesseract tiene.

### 1.2 Qué escribe cada variante, comprobado leyéndolo de vuelta

| variante | `pHYs` en el fichero | `magick identify %x,%y %U` | `PIL.Image.open(...).info` |
|---|---|---|---|
| `sin` (la del corpus) | `x=200 y=200 unidad=0` | `200,200 Undefined` | **`aspect: (200, 200)`** — *no* `dpi` |
| `ninguno` | — (trozo ausente) | `72,72 Undefined` | *nada* |
| `p0200` | `x=7874 y=7874 unidad=1` | `78,74 PixelsPerCentimeter` | **`dpi: (199.9996, 199.9996)`** |
| `p0400` | `x=15748 unidad=1` | `157,48 PixelsPerCentimeter` | `dpi: (399.9992, 399.9992)` |

**El valor 200 que `magick` mete con `unidad=0` es una relación de aspecto, no una
densidad** — y PIL lo clasifica correctamente como `aspect`. Esto cierra el mecanismo
que G2 describió: el fichero **lleva el número**, pero **declara no saber en qué
unidad está**.

### 1.3 Testigos de ruido, con tope, y VRAM

Los dos de `CLAUDE.md` §3, con **tope de 20 s** al testigo de proceso. **No se topó en
ninguna de las trece tandas.**

| tanda | deriva (monohilo) | nivel (proceso) | VRAM base → pico | veredicto |
|---|---:|---:|---|---|
| A — Tesseract (CPU) | 0,89 | **×1,09** | — | **limpia** |
| paddleocr ruta / array | 1,03 / 0,99 | ×1,03 / ×0,98 | 3 261→3 530 / 3 275→3 546 | limpias |
| easyocr array | 1,04 | ×1,54 | 3 453→3 633 | limpia |
| easyocr ruta | 0,96 | **×6,29** | 3 293→3 540 | **sucia** |
| rapidocr ruta / array | 1,03 / 0,97 | **×39,90 / ×32,57** | 3 583→3 800 / 3 452→3 637 | **sucias** |
| E — color (6 tandas) | 0,90–1,37 | ×0,93–×2,97 | 3 425→3 852 | limpias |

**Tres tandas salen sucias por el testigo de proceso, y la causa está identificada:
corrieron a la vez que el control de Tesseract, que ocupó un núcleo durante 25
minutos.** Es una decisión mía, deliberada, para no encadenar dos horas de tandas.

**Consecuencia, separada y honesta:** **los CER no están afectados** —las 462 celdas
salieron **deterministas** con n=9 y la salida de estos motores sobre un PNG fijo y un
dispositivo fijo es una función determinista— y **ningún milisegundo de este informe
se usa para ninguna conclusión**. El objeto de medida es el `md5` del texto.

**VRAM: pico de 3 852 MiB sobre una base de 3 261–3 599.** Los rásteres van de 2,22 a
3,47 Mpx y **nunca se acercaron al tope de 11 300 MiB**, así que el problema del
asignador que no devuelve memoria (`k-por-motor.md` §6.3) **no llegó a aparecer**. Se
usó **un proceso por (motor, vía)** de todos modos, por disciplina.

---

## 2. Sonda 1 — ¿LEE el motor el `pHYs`? Sondeado en ejecución

G3 supuso que *«reciben arrays de numpy y no deberían verlo»*. **La premisa es falsa**:
en `bench/scripts/ocr_motor.py` y en `bench/salidas-k-motor/ocr_lote_km.py` los tres
motores reciben **la ruta**, y la abren ellos. Así que la pregunta es real, y se
contesta instrumentando, no leyendo el código: se envuelven `builtins.open`,
`cv2.imread`, `cv2.imdecode`, `PIL.Image.open` y `skimage.io.imread`, y **el `.info` de
la imagen de PIL se sustituye por un diccionario espía que registra toda consulta de
clave**. *(`sonda_lectura_pm.py`, `json/sonda_lectura_*.json`.)*

**MEDIDO**, `escaneado_d4` a ×1,00, variantes `sin` (unidad=0) y `p0400` (unidad=1):

| motor | quién decodifica | ¿el `pHYs` llega a estar disponible? | claves de `info` que consulta el motor | ¿consulta `dpi`/`aspect`? | `md5` de la salida |
|---|---|---|---|---|---|
| **RapidOCR** | `open('rb')` → **`PIL.Image.open`** | **SÍ** (`aspect` / `dpi`) | `interlace`, `exif`, `exif`, `Raw profile type exif`, `XML:com.adobe.xmp` | **NO** | idéntico en las dos |
| **EasyOCR** | `open('rb')` → **`cv2.imread(flag 0)`** *y además* **`skimage.io.imread`** (→ PIL) | **SÍ** (`aspect` / `dpi`) | las mismas cinco | **NO** | idéntico en las dos |
| **PaddleOCR** | `open('rb')` → **`cv2.imdecode`** | **NO** — OpenCV no expone el `pHYs` por ningún sitio | *(no usa PIL)* | **NO** | idéntico en las dos |

> **MEDIDO — la respuesta a «¿lo lee?» es NO en los tres, y por dos mecanismos
> distintos.** PaddleOCR **no puede** leerlo: su decodificador lo descarta. RapidOCR y
> EasyOCR **podrían** —lo tienen en un diccionario que además abren cinco veces por
> imagen— y **no lo miran**. La distinción importa: la inmunidad de PaddleOCR es
> estructural; la de los otros dos es **una decisión de su código, que una versión
> futura puede cambiar**.

**Y la API tampoco ofrece la puerta de atrás.** Las cinco firmas
—`Reader.readtext`, `Reader.__init__`, `RapidOCR.__call__`, `PaddleOCR.predict`,
`PaddleOCR.__init__`— se inspeccionaron buscando `dpi|density|ppi|resolution|scale`:
**cero coincidencias en las cinco.** Ninguno de los tres tiene el equivalente de
`-c user_defined_dpi` de Tesseract. **A estos motores la resolución no se les puede
decir ni queriendo.**

**Un detalle que no buscaba y que es un coste medible:** **EasyOCR decodifica el
fichero DOS VECES** cuando recibe una ruta — `cv2.imread(path, IMREAD_GRAYSCALE)` para
`img_cv_grey` y `skimage.io.imread(path)` (que va a PIL) para `img`. Sobre un folio de
2,2 Mpx eso es un decodificado de PNG entero tirado a la basura por imagen.
**Cuantificarlo es PENDIENTE** (no se midió: los tiempos de esta tanda no son de fiar,
§1.3).

---

## 3. La rejilla — ¿CAMBIA el resultado? No, en 300 celdas

**MEDIDO**, n=9, `cuda`, CER acentos. Cada fila son las 8 o 9 variantes de cabecera
sobre **los mismos IDAT**. `md5 únicos` es el número de textos de salida distintos;
`recorrido` es `max − min` del CER.

| motor | vía | documento | variantes | **`md5` únicos** | **recorrido CER** | CER (idéntico en todas) |
|---|---|---|---:|---:|---:|---:|
| paddleocr | ruta / array | `escaneado_d3` ‡ | 8 | **1** / **1** | **0,00** | 2,53 |
| paddleocr | ruta / array | `escaneado_d4` | 8 | **1** / **1** | **0,00** | 19,30 |
| paddleocr | ruta / array | `escaneado_d4` ×1,25 | 9 | **1** / **1** | **0,00** | 13,09 |
| paddleocr | ruta / array | `escaneado_d4c` | 8 | **1** / **1** | **0,00** | 0,67 |
| paddleocr | ruta / array | `escaneado_d4e` | 8 | **1** / **1** | **0,00** | 70,97 |
| paddleocr | ruta / array | `escaneado_d4f` | 9 | **1** / **1** | **0,00** | 0,67 |
| rapidocr | ruta / array | `escaneado_d3` ‡ | 8 | **1** / **1** | **0,00** | 3,80 |
| rapidocr | ruta / array | `escaneado_d4` | 8 | **1** / **1** | **0,00** | 18,62 |
| rapidocr | ruta / array | `escaneado_d4` ×1,25 | 9 | **1** / **1** | **0,00** | 24,50 |
| rapidocr | ruta / array | `escaneado_d4c` | 8 | **1** / **1** | **0,00** | 1,17 |
| rapidocr | ruta / array | `escaneado_d4e` | 8 | **1** / **1** | **0,00** | 77,52 |
| rapidocr | ruta / array | `escaneado_d4f` | 9 | **1** / **1** | **0,00** | 7,05 |
| easyocr | ruta / array | `escaneado_d3` ‡ | 8 | **1** / **1** | **0,00** | 54,43 |
| easyocr | ruta / array | `escaneado_d4` | 8 | **1** / **1** | **0,00** | 61,41 |
| easyocr | ruta / array | `escaneado_d4` ×1,25 | 9 | **1** / **1** | **0,00** | 61,41 |
| easyocr | ruta / array | `escaneado_d4c` | 8 | **1** / **1** | **0,00** | 15,10 |
| easyocr | ruta / array | `escaneado_d4e` | 8 | **1** / **1** | **0,00** | 73,32 |
| easyocr | ruta / array | `escaneado_d4f` | 9 | **1** / **1** | **0,00** | 17,95 |

**Uniendo las dos vías: 18 de 18 filas (motor × documento) tienen UN SOLO `md5`.**
Y **`ruta` frente a `array`, celda a celda: 150 pares, 0 con `md5` distinto.**

**Se mide el `md5`, no el CER, y no es un capricho.** El CER es un resumen y dos textos
distintos pueden dar el mismo número — en §5 hay un caso: EasyOCR devuelve 396 y 399
caracteres con **el mismo 61,41 % de CER** y `md5` distintos. **Decir «el `pHYs` no
mueve el CER» sería una afirmación más débil que la que se puede hacer: no mueve un
solo byte.**

**Control de reproducción, y sale limpio.** Estas cifras **reproducen a la centésima**
las de `bench/k-por-motor.md` medidas hace un día por otro agente, con otro arnés y
otra tanda: PaddleOCR `d3` 2,53 · `d4` 19,30 · `d4` ×1,25 **13,09** · `d4c` 0,67 ·
`d4e` 70,97; RapidOCR+R6 `d3` 3,80 · `d4` **18,62** · `d4e` 77,52 · `d4f` 7,05;
EasyOCR `d4c` **15,10**. **Si mi tanda no reprodujera esas cifras, el problema sería
mío.**

**Y una corroboración accidental de la trampa 11.** La sonda de lectura de RapidOCR se
corrió también en **CPU**: mismo fichero, **mismo CER (18,62 %)** y **`md5` distinto**
(`b3af5308` en CPU, `ef754402` en `cuda`), con 542 y 543 caracteres. *CPU y GPU no dan
la misma salida* sigue siendo verdad, y aquí el CER lo habría escondido.

---

## 4. El control — los mismos ficheros SÍ mueven a Tesseract

Sin este apartado, «los tres motores GPU no se mueven» no significa nada: podría ser
que mis ficheros no llevaran el efecto. **150 celdas**, n=9, CPU, **`rc = 0` en las
150**, **150 deterministas**, testigos **limpios** (deriva 0,89, nivel ×1,09).

### 4.1 `escaneado_d4` a ×1,00 — la fila donde vive el hallazgo de G2

**MEDIDO.** En negrita, la resolución **verdadera** del ráster (200 ppp).

| `--psm` | `sin` | `ninguno` | 70 | 100 | 150 | **200** | 300 | 400 | `md5` únicos | recorrido |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **3** | 84,56 | 84,56 | 84,56 | **98,49** | 51,34 | **51,34** | 84,56 | 84,56 | 4 | **47,15** |
| 6 | 55,70 | 55,70 | 55,70 | 55,70 | 55,70 | **55,70** | 55,70 | 55,70 | **1** | **0,00** |
| 11 | 41,78 | 41,78 | 41,78 | 43,79 | 40,60 | **40,60** | 41,61 | 41,78 | 4 | 3,19 |

Y el mecanismo, leído del `stderr` del propio motor (no deducido): con `sin`,
`ninguno` y `70` declarados, Tesseract imprime **`Estimating resolution as 403`** sobre
un ráster de 200 ppp y detecta **36 diacríticos**; con 150 y 200 declarados no estima
nada y detecta **51**.

> **MEDIDO — el 33,22 de G2, reproducido por otra ruta.** `sin declarar` → `verdadero`
> sobre `escaneado_d4` con `psm 3`: **84,56 → 51,34 = 33,22 puntos**, exacto. G2 lo
> obtuvo con la bandera `-c user_defined_dpi=200`; aquí sale **cambiando nueve bytes
> de la cabecera del PNG**. Dos mecanismos de entrega, el mismo número.

### 4.2 El recuento de las 18 filas, y dos cosas nuevas

| | |
|---|---:|
| filas (documento × `--psm`) que **cambian** con la cabecera | **10 de 18** |
| filas con `--psm 6` que cambian | **0 de 6** |
| celdas distintas de `sin` (de las 132 no-`sin`) | **32** por `md5` — pero **31** por CER: 10 mejor, 101 igual, 21 peor |
| recorrido máximo | **47,15** (`escaneado_d4`, `psm 3`) |

**Y ahí hay una celda que separa las dos métricas:** de las 132, **32 devuelven un
texto distinto del de `sin` y solo 31 devuelven un CER distinto**. Una cambia el texto
y no la cifra. **Es la misma razón por la que en §3 se cuenta el `md5` y no el CER.**

**`psm 6` no cambia NUNCA: 0 de 6 filas, 50 celdas con un solo `md5`.** Reproduce el
matiz de G2 (*«el metadato solo entra donde entra el análisis de maquetación»*) sobre
un corpus distinto y con el metadato en el fichero en vez de en una bandera.

> **NUEVO — MEDIDO: `pHYs unidad=0` y `pHYs` AUSENTE son la misma cosa.** En **18 de
> 18** filas el `md5` de `ninguno` es idéntico al de `sin`. El proyecto venía diciendo
> «no declara resolución» sin separar «lo dice y no dice en qué unidad» de «no lo
> dice». **Son indistinguibles para Tesseract, y ahora está medido, no supuesto.**

> **PRECISIÓN sobre `psm-y-rasterizador.md` §4.5, punto 1.** G2 publicó *«declarar el
> valor VERDADERO nunca empeora: 3 mejor, 12 igual, 0 peor de 15 celdas»*. Sobre mis
> **15 celdas a ppp nativos** sale **3 mejor, 12 igual, 0 peor**: **idéntico**. Pero
> con la raíz remuestreada dentro (`escaneado_d4` a ×1,25) el recuento es **3 mejor,
> 13 igual, 2 PEOR**, y los dos peores son de esa raíz: `psm 3` **85,57 → 89,60
> (+4,03)** y `psm 11` **45,30 → 46,31 (+1,01)** al declarar sus 250 ppp verdaderos.
> **No refuta a G2: confirma su punto 1 donde él lo midió y confirma su punto 3
> —«sobre un ráster remuestreado el signo se pierde»— con dos contraejemplos
> concretos.** La regla del adaptador se queda igual; su enunciado, no: **«declarar el
> verdadero no empeora nunca» solo vale a ppp nativos.**

### 4.3 Las otras filas, en corto

`escaneado_d4c`: `psm 3` recorrido **9,39** (1,85 → **11,24** declarando 100 ppp falsos,
7,72 declarando 300); `psm 11` recorrido **7,39** (2,68 → **10,07** a 300). `escaneado_d3`
`psm 11` recorrido 6,33; `escaneado_d4e` `psm 11` recorrido 4,87; `escaneado_d4f`
recorrido 0,00 y 0,17. `escaneado_d4` a ×1,25 con `psm 3`: **sin** 85,57 y **100,00**
—silencio, con `rc = 0`— declarando 100, 150 o 200.

**Todas las cifras de `d4c` reproducen las de G2 §4.5 a la centésima.**

---

## 5. Lo que SÍ mueve la vía de entrada — y refuta mi propio marco

Los 150 pares `ruta`/`array` idénticos de §3 invitan a escribir *«la vía da igual»*.
**Es falso, y el motivo es que los 50 rásteres del corpus son de ESCALA DE GRISES**,
donde R=G=B y un intercambio de canales es invisible. **Es el tercer sesgo de
`CLAUDE.md` §3 —el de semilla— aplicado a la vía en vez de al formato: sin variar la
entrada, estaba midiendo mi corpus.**

Tanda E: el mismo `escaneado_d4` a ×1,00, **teñido** (`-channel R -evaluate multiply
0.55`, `-channel B ×0.85`), en dos versiones —**paleta** (lo que `magick` escribe por
defecto) y **truecolor** (`PNG24:`)— con las cuatro entradas posibles.
**MEDIDO**, n=9 en la rejilla y n=1 en la sonda de canales (`sonda_canales_pm.py`).

| motor | fichero | `ruta` | `array` BGR | `array` RGB | `array` gris 2-D |
|---|---|---:|---:|---:|---|
| **RapidOCR** | color **paleta** | **31,71** | 19,13 | 16,95 | 24,33 |
| **RapidOCR** | color **truecolor** | **19,13** | **19,13** ✔ | 16,95 | 24,33 |
| **RapidOCR** | gris (el del corpus) | 18,62 | 18,62 ✔ | 18,62 ✔ | 18,62 ✔ |
| **EasyOCR** | color paleta | 61,41 | 58,05 | 61,41 *(`md5` distinto)* | 60,57 |
| **EasyOCR** | color truecolor | 61,41 | 58,05 | 61,41 *(`md5` distinto)* | 60,57 |
| **EasyOCR** | gris | 61,41 | 61,41 ✔ | 61,41 ✔ | 61,41 ✔ |
| **PaddleOCR** | color paleta | 10,07 | **10,07** ✔ | 8,05 | **`ValueError`** |
| **PaddleOCR** | color truecolor | 10,07 | **10,07** ✔ | 8,05 | **`ValueError`** |
| **PaddleOCR** | gris | 19,30 | 19,30 ✔ | 19,30 ✔ | **`ValueError`** |

*(✔ = `md5` del texto idéntico al de la vía `ruta`.)*

Tres hallazgos, y los tres se separan cambiando la variable, no leyendo el código:

1. **RapidOCR pierde 12,58 puntos por la ruta si el PNG está en modo PALETA**
   (31,71 frente a 19,13). Con el mismo contenido en truecolor, ruta y array coinciden
   byte a byte. **La causa es de decodificado, no de canales**:
   `rapidocr/utils/load_image.py::img_to_ndarray` solo trata `mode == "1"`, así que un
   PNG de paleta sale de `np.array(img)` como **matriz 2-D de ÍNDICES de paleta**, y
   `convert_img` la asciende a BGR como si fuera gris. **Comprobado:**
   `PIL.Image.open(color.png)` devuelve `mode P` y forma `(1716, 1294)` — dos
   dimensiones, no tres. **Y `magick` escribe PNG de paleta por defecto** en cuanto la
   imagen tiene ≤256 colores, que es exactamente el caso de un escaneado umbralizado.
2. **EasyOCR no coincide consigo mismo entre vías, ni siquiera pasándole RGB.**
   `easyocr.utils.reformat_input` construye **dos** cosas: con una ruta, `img` sale de
   `skimage.io.imread` (**RGB**) y `img_cv_grey` de `cv2.imread(..., GRAYSCALE)`; con un
   ndarray, `img` es el array tal cual (**documentado BGR**) y `img_cv_grey` sale de
   `cvtColor(BGR2GRAY)`. **Las dos ramas difieren en dos sitios a la vez**, así que
   arreglar el orden de canales acerca el resultado (61,41 = 61,41) **pero no lo
   iguala**: `md5` `af1288c1` frente a `3dfd3690`, 396 frente a 399 caracteres.
   **Es el caso que enseña por qué la medida dura es el `md5`: el CER coincide y el
   texto no.**
3. **PaddleOCR es el único consistente** —`cv2` en las dos ramas, BGR en las dos— y
   **el único que rechaza un ndarray 2-D en gris**, con
   `ValueError: not enough values to unpack (expected 3, got 2)`. Un sidecar que
   decodifique una vez en gris y reparta el array a los tres motores **se rompe en
   PaddleOCR y solo en PaddleOCR**.

> **MEDIDO — la vía de entrada es una variable del adaptador, y no por el `pHYs`.**
> Sobre el corpus actual vale **0,00** en 150 de 150 pares; sobre un ráster en color
> vale **12,58 puntos** (RapidOCR, paleta) y **3,36** (EasyOCR, canales). **Que la
> rejilla principal saliera plana era una propiedad de mi corpus, no de los motores**,
> y decirlo es más útil que el resultado que iba a publicar.

---

## 6. La consecuencia para el proyecto, sin rodeos

**Sí: los tres son inmunes y Tesseract no lo es. Por tanto ninguna tabla de CER de
Tesseract medida sobre un ráster `magick -density N` (sin `-units PixelsPerInch`) es
comparable con una tabla de PaddleOCR, RapidOCR o EasyOCR** — porque una depende de un
metadato que las otras ni siquiera leen. Y como **todo el corpus del proyecto está
rasterizado así**, la lista es larga.

**Tablas de Tesseract medidas sobre rásteres SIN declarar resolución** (deducido de
`bench/salidas-k-motor/preparar_km.py:64`, `bench/salidas-k-motor/sonda_tess.py:36` y
`bench/salidas-corpus-d5/tess_lote_d5.py:96`, salvo donde el informe lo declara):

| informe · sección | qué contiene | cifras que quedan marcadas |
|---|---|---|
| `bench/k-por-motor.md` **§2.1, §3, §4.1, §4.3, §5, §6.1 (filas `magick`), §6.2** | **todo el eje Tesseract del informe** — 44 celdas de barrido de `k` + la sonda de 4 `--psm` | `psm 3` ×0,875 · `psm 11` ×0,75 · d4 84,56/41,78 · arrepentimientos 0,34 / 2,51 / **176,31** |
| `bench/psm-y-rasterizador.md` **§2.1 y §2.2** (tanda A, 72 celdas) | los 12 `--psm` × 6 documentos | d2 `psm 6` 0,00 · d4 `psm 11` 41,78 · **42,78 puntos** de `--psm` · arrepentimientos 3,77 / 18,29 |
| `bench/psm-y-rasterizador.md` **§3.6** (tanda C, 66 celdas) | la descomposición de varianza «sin declarar» | d4: `--psm` 84,2 % / `k` 8,3 % / interacción 7,4 % |
| `bench/psm-y-rasterizador.md` **§4.5**, columna «sin declarar» | 6 docs × 3 `--psm` | la columna entera |
| `bench/corpus-d5.md` **§2.2, §2.3, §2.4, §3.1, §3.2, §3.3, §5.1, §6.1, §6.2** y la **columna A de §4** | **~266 celdas** del corpus d5 | el fallo aritmético de la regla de ppp (**16,78 puntos**), las escaleras de iluminación y polvo, las 90 celdas de §6.1 |
| `CLAUDE.md` trampa 8 y §5 · `PLAN-ORQUESTADOR.md` §4.5 · `ESTADO-Y-REPARTO.md` §B13/B17/B18 | **resúmenes que heredan** esas cifras | 42,78 · 33 · 84,56 · 41,78 · 176,31 · 2,51 |

**Las únicas tablas de Tesseract del proyecto con la resolución declarada** son
`psm-y-rasterizador.md` §3 (tanda B), §4.2–§4.3, §4.5 columnas 70–400 y §5.1–§5.4
(tandas B y E); `corpus-d5.md` §4 columnas B y C; `k-por-motor.md` §6.1/§6.2 filas
Ghostscript; e `invocacion-aristas.md` §9 (rasterizado con `gs`, que declara solo).

### Qué hay que hacer con esas tablas — y qué NO

**Lo que NO hay que hacer: rehacerlas.** Siguen siendo válidas *dentro de sí mismas*:
todas las celdas de una misma tabla comparten cabecera, así que las comparaciones
**relativas** (qué `--psm` gana, qué `k` gana, cuánto cuesta una patología) se
sostienen. Es el mismo criterio que `CLAUDE.md` §3 aplica a los milisegundos.

**Lo que sí hay que hacer, y cuesta una línea por informe:**

1. **Declarar el `pHYs` del ráster junto a cada `k` y cada `--psm`.** El proyecto ya
   exige publicar la terna `(psm, k, resolución declarada)` para Tesseract
   (`psm-y-rasterizador.md` §7). **Lo que este informe añade es que ese tercer elemento
   solo hace falta para Tesseract, y que para los otros tres es ruido: declararlo o no
   no cambia un byte.**
2. **Prohibir la comparación cruzada sin la etiqueta.** Una frase del tipo *«Tesseract
   da 84,56 % donde PaddleOCR da 19,30 %»* sobre `escaneado_d4` **compara un motor mal
   alimentado con uno bien alimentado**: la cifra buena de Tesseract sobre ese fichero
   es **51,34 %**, y la brecha real es de 32 puntos, no de 65.
3. **Y una que corrige una prioridad:** la regla R8 de `corpus-d5.md` §4.1 —*«el
   adaptador que entrega un ráster a un motor de OCR escribe en él la resolución en
   pulgadas»*— **estaba marcada MEDIDO sobre Tesseract y PENDIENTE en los demás.
   Queda MEDIDA en los demás, con el signo contrario: no les hace falta.** Sigue
   valiendo la pena aplicarla —es gratis y da determinismo— pero **su beneficio es de
   un motor de los cuatro**, no una regla universal del adaptador.

---

## 7. Lo que falló, y lo que no se midió

### 7.1 Lo que falló: nada de la máquina, una cosa mía

**Cero fallos de motor: 462 celdas, 0 excepciones, 0 omitidas por VRAM, `rc = 0` en las
150 de Tesseract.** No hizo falta gastar ningún intento de la regla de los dos.

**Lo que sí falló fue mi marco de partida**, y está en §5: diseñé la rejilla creyendo
que la vía `array` era un control trivial —«píxeles idénticos, entrada idéntica»— y lo
es **solo porque el corpus es gris**. Si el informe se hubiera cerrado con las 300
celdas, habría publicado *«la vía de entrada da igual»*, que es falso y cuesta 12,58
puntos en el caso peor. **Lo destapó variar la entrada, que es literalmente el tercer
sesgo que `CLAUDE.md` §3 avisa.**

**Y un tropiezo de herramienta, declarado:** generé un parche de Python con un heredoc
de shell para editar `manifiesto_pm.py` — exactamente lo que prohíbe la trampa 19. Dos
de las tres sustituciones no aplicaron (la comilla y la barra invertida se comieron el
patrón) y hubo que rehacerlo con la herramienta de escritura. **No rompió nada porque
lo detecté al ejecutar, pero la trampa 19 vuelve a estar bien puesta.**

### 7.2 Lo que NO se midió

- **Docling.** El encargo pedía tres motores y son tres. Docling usa RapidOCR por
  dentro con `RapidOcrOptions`, así que **es esperable que herede la inmunidad —pero
  también el defecto de paleta de §5**, y **eso no está medido**. **PENDIENTE**, y es
  una tanda corta.
- **El Tesseract del contenedor** (`filex-c13`, `tesseract-ocr-spa`). Todo lo de aquí
  es el nativo de Windows. **PENDIENTE.**
- **Surya, Marker y el Tesseract embebido en Ghostscript.** `gs -sDEVICE=ocr`
  rasteriza en proceso y no hay PNG intermedio, así que **el `pHYs` no le aplica**;
  confirmarlo sondeando es **PENDIENTE**.
- **Otras versiones.** La inmunidad de RapidOCR y EasyOCR **no es estructural**: es
  código que puede cambiar. Lo medido vale para **RapidOCR 3.9.2, EasyOCR 1.7.2,
  PaddleOCR 3.7.0 / PaddleX 3.7.2** y para nada más.
- **El coste del doble decodificado de EasyOCR** (§2). Los tiempos de esta tanda no
  sirven; **PENDIENTE** con la máquina en reposo.
- **Si la vía `array` es más rápida.** Las medianas apuntan a que sí (RapidOCR 526,0 ms
  por ruta contra 401,8 por array), **pero son tandas distintas y una de ellas salió
  sucia a ×39,90: no se publica el número.** **PENDIENTE.**
- **Otros metadatos.** Solo se movió el `pHYs`. Los PNG de `magick` llevan además
  `tEXt` con `date:*` y `pdf:HiResBoundingBox`, y RapidOCR **sí consulta `exif` y
  `XML:com.adobe.xmp`** (§2). **Qué pasa si esos trozos existen es PENDIENTE**, y por
  el `exif_transpose` de RapidOCR **hay un candidato claro: una etiqueta de orientación
  EXIF dentro de un PNG.**

---

## 8. Lo que habría que añadir a `CLAUDE.md` — texto exacto, y AL FINAL

**No he tocado `CLAUDE.md`.** Si se acepta, esto va **al final de la lista de trampas**,
sin renumerar nada (`CLAUDE.md` ya lo pagó dos veces).

> **APLICADO el 23/08 por el orquestador, como las trampas 29 y 30**, no 26 y 27:
> H7 propuso a la vez otras tres con esos mismos números y habían chocado. El
> texto es el de abajo; solo cambia el número de cabecera.

```markdown
26. **El `pHYs` es una trampa de UN SOLO MOTOR: PaddleOCR, RapidOCR y EasyOCR son
    INMUNES — MEDIDO** (`bench/phys-multimotor.md`, 300 celdas GPU + 150 de control).
    Sobre los MISMOS IDAT, con el `pHYs` a `unidad=0`, ausente, o declarando 70/100/
    150/200/240/250/300/400 ppp, los tres motores devuelven **un solo `md5` de texto
    en las 18 filas (motor × documento)**: recorrido de CER **0,00**. Y no es que no
    les afecte: **no lo consultan** — sondeado en ejecución con un diccionario espía
    sobre el `.info` de PIL, que consultan cinco veces por imagen (`interlace`,
    `exif`, `XML:com.adobe.xmp`) **y ni una por `dpi` o `aspect`**; PaddleOCR ni
    siquiera usa PIL (`open('rb')` + `cv2.imdecode`). **Ninguno de los tres tiene un
    parámetro de resolución en su API.** Los mismos ficheros mueven a Tesseract hasta
    **47,15 puntos** y reproducen su 33,22 exacto. **Consecuencia: ninguna tabla de
    CER de Tesseract es comparable con una de los otros tres si no declara con qué
    `pHYs` se midió, y casi ninguna lo declara** (lista en `bench/phys-multimotor.md`
    §6). La regla R8 —«el adaptador escribe la resolución en el ráster»— sigue siendo
    buena por determinismo, **pero su beneficio es de un motor de cuatro**.
    Y un matiz que nadie había separado: **`pHYs unidad=0` y `pHYs` AUSENTE son
    idénticos para Tesseract, 18 de 18 filas**. Además, «declarar el valor verdadero
    no empeora nunca» **solo vale a ppp nativos**: sobre un ráster remuestreado a ×1,25
    declarar sus 250 ppp verdaderos cuesta **+4,03** puntos con `psm 3`.

27. **La VÍA de entrada del OCR (ruta o `ndarray`) es una variable del adaptador, y
    el corpus la esconde — MEDIDO** (`bench/phys-multimotor.md` §5). Sobre los 50
    rásteres del proyecto, todos en gris, `ruta` y `array` dan el mismo `md5` en **150
    de 150 pares**: en gris R=G=B y un intercambio RGB/BGR es invisible. Sobre un
    ráster **en color** la vía vale hasta **12,58 puntos**:
    - **RapidOCR + ruta + PNG de PALETA: 31,71 % contra 19,13 %.** `LoadImage.
      img_to_ndarray` solo trata `mode == "1"`, así que un PNG de paleta llega como
      **matriz 2-D de índices**. **Y `magick` escribe paleta por defecto con ≤256
      colores**, que es justo un escaneado umbralizado.
    - **EasyOCR nunca coincide consigo mismo entre vías** (3,36 puntos): con ruta usa
      `skimage` (**RGB**) para el detector y `cv2.imread` gris para el reconocedor;
      con `ndarray` usa el array (**BGR**) y `cvtColor`. Pasarle RGB **acerca el CER
      pero no iguala el texto** — mismo 61,41 %, `md5` distinto.
    - **PaddleOCR es el único consistente (0,00) y el único que RECHAZA un `ndarray`
      2-D en gris**, con `ValueError: not enough values to unpack (expected 3, got 2)`.
    **Un sidecar que decodifique una vez y reparta el array a los tres motores tiene
    que entregar BGR de tres canales, y no puede dar por hecho que eso equivale a
    pasar la ruta.**
```

---

## 9. Ficheros

Todo en **`bench/salidas-phys-multi/`**, con su `MANIFIESTO.md`. **Los 52 PNG (61,2 MB)
están borrados** y el manifiesto lleva nombre, `sha256`, `md5` de los IDAT, `pHYs`,
píxeles y **la orden exacta que los reproduce**.

| fichero | qué es |
|---|---|
| `ocr_eval_d4.py`, `d4_texto.py` | **copias byte a byte** de `bench/salidas-corpus-d4/`, con su `sha256` verificado. Se importan, no se modifican |
| `ocr_eval_pm.py` | envoltorio: mapa **cerrado** documento → referencia. No reimplementa métrica |
| `preparar_pm.py` | rasteriza una vez y genera las variantes de `pHYs` **por cirugía de bytes**, sin tocar los IDAT |
| `sonda_pixeles_pm.py` | prueba que los píxeles son idénticos y el metadato no (`cv2` color/gris y PIL) |
| `sonda_lectura_pm.py` | **la sonda del encargo**: instrumenta `open`, `cv2.imread/imdecode`, `PIL.Image.open`, `skimage.io.imread` y espía el `.info` |
| `sonda_canales_pm.py` | separa «orden de canales» de «modo paleta» con las cuatro entradas posibles |
| `ocr_lote_pm.py` | el arnés: motor × **vía** × variante, n=9, dos testigos con tope, guardia de VRAM, `md5` de entrada y de salida |
| `tess_pm.py` | el control de Tesseract sobre los mismos ficheros, con `rc` y `Estimating resolution` |
| `tablas_pm.py` → `tablas.md` | las rejillas, los `md5` únicos, los recorridos y el cotejo ruta/array |
| `run_a_tess.sh`, `run_b_gpu.sh`, `run_c_color.sh` | las tandas, con `gpu_acquire`/`gpu_release` y `timeout` explícito |
| `manifiesto_pm.py` → `MANIFIESTO.md` | genera el manifiesto y **borra** los 52 PNG |
| `json/`, `texto/`, `logs/` | las 462 celdas, la salida literal de OCR de cada una y el registro de las trece tandas y las tres sondas |

---

## 10. Reglas del encargo, cumplidas

| regla | estado |
|---|---|
| Escribir **solo** en `bench/phys-multimotor.md` y `bench/salidas-phys-multi/**` | **Cumplida.** `git status` lo confirma: no se tocó `filex/`, ni `bench/hito7-superficies.md`, ni `bench/scripts/`, ni ningún `.md` maestro |
| **`CLAUDE.md` no se edita**; el texto propuesto va **al final** | **Cumplida** (§8) |
| `bench/salidas-referencia/referencia.json` solo lectura | **Cumplida.** Ni abierto |
| Arneses compartidos copiados, no modificados | **Cumplida.** `ocr_eval.py` no se abrió; `ocr_eval_d4.py` y `d4_texto.py` copiados con `sha256` verificado; `ocr_motor.py`, `ocr_lote_km.py`, `tess_psm.py`, `raster_psm.py` **leídos y no tocados** |
| Nada instalado en los venvs | **Cumplida.** Solo se ejecutaron |
| **Lock de GPU** en todo lo que usa la tarjeta | **Cumplida.** Tres adquisiciones y tres liberaciones; la tanda de Tesseract es CPU y **no lo tomó**, a propósito |
| **Dispositivo fijado** (trampa 11) | **Cumplida.** `cuda` en los tres motores GPU, CPU en Tesseract, declarado celda a celda. Y se aporta una corroboración nueva de la trampa: mismo CER, distinto `md5`, entre CPU y GPU |
| **Registrar el `rc`** (trampa 25) | **Cumplida.** `rc` en las 150 celdas de Tesseract (150 a 0) y la excepción exacta en las 312 en proceso (0 excepciones). Las celdas de 0 bytes van con su `rc` al lado |
| Timeouts explícitos | **Cumplida.** `timeout` en las trece tandas, `timeout=600` en cada `magick`/`gs`/`tesseract`, `stdin=DEVNULL` en todas |
| Determinismo **comprobado**, no supuesto | **Cumplida.** `determinista` se calcula comparando los n=9 textos de cada celda: **462 de 462** |
| Documentos con referencia larga (trampa 9) | **Cumplida.** Cuatro de los cinco usan la de 610 caracteres; `escaneado_d3` usa la de 79 y va marcado ‡ |
| Evaluador declarado y acentuado (trampa 10) | **Cumplida** (cabecera y §1) |
| No sobremuestrear (trampa 6) | **Cumplida.** ppp nativos leídos con `pypdfium2`; ×1,00 es el nativo de cada documento. El único punto remuestreado (×1,25) está declarado como tal |
| **Sondear en ejecución, no deducir** | **Cumplida**, y es el núcleo del informe: la premisa de G3 (*«reciben arrays»*) resultó **falsa** y la conclusión (*«son inmunes»*) resultó **cierta por otro motivo** |
| Dos testigos de ruido, con tope | **Cumplida.** Tope de 20 s, `testigo_topado = false` en las trece tandas; tres tandas declaradas **sucias** con su causa |
| Dos intentos por problema | **Cumplida.** No hizo falta ninguno |
| No generar código Python con heredocs (trampa 19) | **Incumplida una vez, y declarada** (§7.1) |
| Borrar los binarios, dejar `MANIFIESTO.md` | **Cumplida.** 52 PNG, 61,2 MB borrados; quedan 1,7 MB de texto |
| No hacer `git add` ni `git commit` | **Cumplida.** Nada versionado |
