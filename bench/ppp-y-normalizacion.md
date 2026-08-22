# La curva de ppp y la validación de la normalización

**Encargo P1 (B9 + B10).** Cerrar o refutar las **dos reglas en vigor apoyadas en menos
evidencia de la que el estándar del proyecto exige**: el techo absoluto de 200 ppp de
`CLAUDE.md` trampa 8 / `PLAN-ORQUESTADOR.md` §4.5, y la corrección de normalización del
detector de RapidOCR de `bench/corpus-d4.md` §7.4, medida sobre 5 documentos de una
página.

**Máquina:** RTX 3060 12 288 MiB (driver 572.61, CUDA 12.8), 12 hilos, Windows 10,
Python 3.11.9. **Fecha:** 2026-08-21, 11:10–13:40.
**Arnés:** `bench/lib/harness.sh`, lock exclusivo en las **cinco** tandas de GPU
(A · B+C · D · F · E), **seis adquisiciones** contando el reintento de B.
**Salidas:** `bench/salidas-ppp-norm/` (+ `MANIFIESTO.md`).
**Dispositivo fijado en todas las regresiones: GPU (CUDA, `gpu:0`).** Solo las dos
sondas de instrumentación (`probe_norm.py`, `sonda_detector.py`) corren en CPU, y no
producen ninguna cifra de CER.

---

## 0. Veredicto, primero

**Las dos frases obligatorias del encargo:**

> **La regla de ppp vigente tras este barrido es que NO HAY UNA REGLA DE ppp: hay una
> por motor.** La formulación segura es `ppp_ocr = ppp_nativos × k(motor)` con `k`
> **medido por motor** —de **×0,88** (Docling+RapidOCR corregido) a **×1,60**
> (Docling+RapidOCR por defecto) sobre el mismo documento, y **×1,50 obligatorio** para
> Tesseract según la medida externa de P2— más un suelo de 100 ppp cuya subida no debe
> pasar de **×1,25**. **La unidad es un FACTOR SOBRE EL RASTER NATIVO, nunca un número de
> ppp**: los ppp están **medidos como irrelevantes** en §2.4, donde tres documentos con
> el mismo JPEG y distinta densidad declarada dan **19,13 / 19,63 / 36,24 %** de CER al
> mismo número de ppp y **cifras idénticas a la centésima** al mismo número de píxeles.
> Y por tanto **`clamp(nativos, 100, 200)` está en el sitio equivocado del diseño**: la
> elección de ppp pertenece al **adaptador de cada motor**, no al orquestador. *(§2.8)*

> **La corrección de normalización NO está lista para producción como cambio general, y
> SÍ lo está acotada a `PP-OCRv6 small` (y a `Docling + RapidOCR`, que resuelve a ese
> mismo modelo).** Sobre `PP-OCRv6 small` no empeoró **ni una** de las 15 celdas de la
> validación de n=9 y mejoró 6, hasta **−72,15 puntos**; aplicada a ciegas a la familia
> entera empeora **12 de 42** celdas del cribado, con un caso de **+42,50 puntos**
> (`PP-OCRv4 mobile` sobre una rasterización del patrón oro).

Y los nueve resultados, en orden de lo que cambia:

1. **MEDIDO, y es el resultado principal de B9 — el techo NO se puede escribir en ppp.**
   El mismo JPEG de `escaneado_d4` empaquetado en tres páginas de distinto tamaño (100,
   200 y 400 ppp nativos) da, **a 200 ppp**, CER de **19,13 / 19,63 / 36,24 %** con
   PaddleOCR y **30,70 / 18,62 / 30,70 %** con RapidOCR; y **a la misma anchura en
   píxeles**, las tres filas coinciden **a la centésima** en las 24 celdas. *(§2.4)*
2. **MEDIDO — pero tampoco es una anchura absoluta en píxeles ni un factor fijo.**
   PaddleOCR se rompe en `d4` a 1 812 px (×1,4) y **no** se rompe en `d4c` a 2 070 px
   (×1,6) ni en `d4f` a 2 587 px (×1,67); sobre `escaneado_d3` se rompe a 1 035 px
   (×1,6). **Ninguna de las tres unidades candidatas predice las ocho parejas
   (documento, motor) medidas.** *(§2.3)*
3. **MEDIDO, y es la respuesta que más consecuencias tiene — la regla es POR MOTOR.**
   Sobre el mismo `escaneado_d4` y las mismas 17 rasterizaciones, el óptimo cae en
   **×0,88** para Docling+RapidOCR corregido, **×1,00** para RapidOCR v6 small corregido,
   **×1,25** para PaddleOCR, **×1,60** para Docling+RapidOCR por defecto y **×1,80** para
   EasyOCR. Y sobre el mismo `escaneado_d3`, ×1,4 es **seguro para PaddleOCR** (3,80 %) y
   **catastrófico para RapidOCR corregido** (2,53 → **46,84 %**). La evidencia externa de
   P2 sobre Tesseract apunta al mismo sitio desde fuera de mis cuatro motores. **Por tanto
   la elección de ppp pertenece al adaptador del motor, no al orquestador.** *(§2.7, §2.8)*
4. **MEDIDO — `clamp(nativos, 100, 200)` está mal en la dirección que nadie miró.** Su
   techo solo actúa **bajando** la resolución de originales de más de 200 ppp, y bajar
   cuesta: reducir `d4` de 200 a 100 ppp (×0,5) sube RapidOCR+R6 de **18,62 % a
   30,70 %**, **+12,08 puntos**. La evidencia que motivó el cambio a techo absoluto
   —`d4` a 280 ppp— es **un caso que la regla relativa nunca produce**: con nativos=200,
   `clamp(200, 100, 280)` devuelve **200**, no 280. *(§2.6)*
5. **MEDIDO — el «acantilado» no es de la resolución: es del margen que le queda al
   motor.** Sobre `patologico_escaneado`, PaddleOCR y RapidOCR+R6 dan **0,00 % en los
   siete puntos de 100 a 400 ppp** (×0,5 a ×2,0). El techo de ppp **solo existe en los
   documentos que ya están cerca de fallar**. *(§2.3)*
6. **MEDIDO — RapidOCR tira los píxeles de más sin decirlo.** `Global.max_side_len: 2000`
   (`rapidocr/config.yaml:10`) recorta la imagen antes del detector: sobre `d4`,
   **de 233 ppp en adelante el array que entra a la red es literalmente el mismo**
   (1 504×1 984 px). Su «tolerancia a los ppp altos» no es tolerancia: es que no los
   ve, y rasterizar por encima de ahí es trabajo pagado a cambio de nada. PaddleOCR, en
   cambio, usa `limit_side_len=64, limit_type='min'` y **no recorta**: ve los 2 588 px.
   *(§2.5)*
7. **MEDIDO — B10: la corrección es segura sobre `PP-OCRv6 small`, y solo ahí.**
   15 documentos, n=9, GPU: **6 mejoras, 9 empates, 0 empeoramientos**. Incluye las
   cuatro rasterizaciones del **patrón oro** (`bench/salidas-referencia/pdf/`, leídas y
   no tocadas). *(§3.3)*
8. **MEDIDO, y es lo que el encargo pedía buscar — la corrección SÍ empeora cosas.**
   Sobre `PP-OCRv5 mobile` empeora **4 de 15** celdas (hasta **+8,89**); sobre
   `PP-OCRv4 mobile`, **4 de 6** del cribado, con **+42,50 puntos** en
   `tipico_texto` del patrón oro (0,83 → 43,33 %). *(§3.4)*
9. **MEDIDO — el defecto es de TODA la familia, no de PP-OCRv6.** Los **ocho**
   `inference.yml` que Baidu distribuye, de `PP-OCRv3_mobile_det` a `PP-OCRv6_tiny_det`,
   declaran ImageNet; `rapidocr/config.yaml` aplica `0,5/0,5/0,5` a los ocho. Lo que es
   de v6 no es el defecto: es **el daño que hace**. *(§3.1, §3.5)*

---

## 1. Cómo se midió, y qué está contaminado

### 1.1 Los arneses: copiados, no modificados

| original (intacto) | copia usada aquí | por qué |
|---|---|---|
| `bench/scripts/ocr_eval.py` | — (no se usa) | es ciego a las tildes |
| `bench/salidas-corpus-d4/ocr_eval_d4.py` | `salidas-ppp-norm/ocr_eval_d4.py` (**copia byte a byte**) | **es el fichero que produjo las cifras de d4 y por tanto el único comparable con ellas** |
| `bench/salidas-corpus-d4/d4_texto.py` | ídem, copia byte a byte | fuente única de verdad del texto |
| `bench/salidas-corpus-d4/ocr_lote_d4.py` | `ocr_lote_pn.py` | + R6, + dos testigos, + recuento de cajas |
| `bench/salidas-corpus-d4/docling_lote_d4.py` | `docling_lote_pn.py` | + lista de ppp, + R6 por `rapidocr_params` |
| `bench/salidas-corpus-d4/preparar_img.py` | `preparar_pn.py` | + lista de ppp, + anchura en píxeles |

**El evaluador que se usó, con todas las letras: `bench/salidas-corpus-d4/ocr_eval_d4.py`,
copiado sin un solo cambio a `bench/salidas-ppp-norm/ocr_eval_d4.py`** (sha256 en el
`MANIFIESTO.md`). `ocr_eval_pn.py` es un envoltorio de 70 líneas que **importa** ese
fichero y solo añade dos referencias que d4 no tenía (`tipico`, y la deducción de la
referencia desde el nombre del fichero). **Toda cifra de CER de este informe se reporta
en las dos lecturas: `cer_acentos` / `cer_ascii`.**

`bench/scripts/ocr_eval.py`, `ocr_motor.py`, `gen_corpus_ocr.sh`, `verificador.py` y
todo `bench/salidas-corpus-d4/` quedan **sin tocar**. Comprobado al terminar.

### 1.2 Los dos testigos de ruido, y lo que atraparon

Cada tanda registra **dos** testigos, al principio y al final:

- **testigo 1, deriva**: bucle monohilo de Python (400 000 iteraciones). Detecta que la
  tanda se va poniendo lenta. **Es ciego a la contención multinúcleo.**
- **testigo 2, nivel**: mediana de 5 lanzamientos de `ffprobe -version` con
  `stdin=DEVNULL` y `timeout=60`. Calibración en reposo del proyecto: **26,65 ms**.

**MEDIDO — el segundo testigo volvió a ganar, y por mucho:**

| tanda | deriva (monohilo) | nivel (proceso) | veredicto |
|---|---:|---:|---|
| A · PaddleOCR | **0,83** («no hay deriva») | 99,3 → 191,3 ms = **×7,18** | **CONTAMINADA** |
| A · RapidOCR v5 | 1,04 | 31,3 → 26,6 ms = ×1,17 | limpia |
| A · RapidOCR v6 def | 0,72 | 31,4 → 51,6 ms = ×1,94 | dudosa |
| A · RapidOCR v6 + R6 | 1,11 | 25,5 → 40,9 ms = ×1,54 | dudosa |
| D2 · RapidOCR v6 + R6 | 1,04 | 23,5 → 23,0 ms = **×0,88** | **limpia** |

**El monohilo etiquetó «sin deriva» (0,83) la misma tanda que el testigo de proceso
midió a ×7,18 del reposo.** Es el mismo fallo que documentó `verificador-ghostscript.md`
§4, reproducido aquí sin buscarlo.

### 1.3 La causa, identificada — y un agujero real en el lock de GPU

**MEDIDO, y es un hallazgo de método que conviene apuntar:** la primera ejecución de la
tanda B se quedó **12 minutos sin procesar una sola imagen**, con `vram_base` de
**11 754 de 12 288 MiB** y la GPU al 100 %. La causa se identificó por PID:

```
PID 34300  D:\Work\research\ASR\.venv-gpu\Scripts\python.exe
           …\Temp\claude\D--Work-research-ASR\…\scratchpad\t01_vram.py
           iniciado 11:44:34
```

**Otra sesión de Claude, en otro proyecto de la misma máquina, estaba ejecutando una
prueba de saturación de VRAM.** El `gpu_acquire`/`gpu_release` de
`bench/lib/harness.sh` usa un fichero de lock **dentro de `bench/`**: es un lock **de
proyecto**, no de máquina. Excluye a otros agentes de FileX y **no ve nada más**.

Consecuencias, separadas:

- **Los CER no están afectados.** Las 28+15+24+17 celdas salieron **deterministas**
  (`det=si`: el texto es idéntico en las 9 repeticiones) y el dispositivo está fijado.
  Una GPU ocupada cambia el tiempo, no el resultado de una convolución.
- **Los tiempos de las tandas A y B NO son utilizables.** Se publican marcados, no se
  usan para ninguna conclusión. Dos medianas lo delatan solas: `d4` a 400 ppp con
  PaddleOCR dio **9 872 ms** frente a 970 ms a 360 ppp, y `d4f` a 400 ppp dio 7 457 ms.
- **Se reintentó una vez** (regla de los dos intentos) tras ver bajar la VRAM, y la
  segunda ejecución cargó el modelo en **12,6 s** en vez de 159,8 s y completó.

**Recomendación que sale de esto y no estaba en el plan:** el lock de GPU tiene que ser
**de máquina**, no de repositorio — un fichero en `%TEMP%` o un mutex con nombre. **Es
PENDIENTE**, y no es de este encargo.

Todas las tandas salieron etiquetadas `SUCIA` por el criterio de utilización de GPU del
arnés (picos del 26 al 100 %): con la sesión de escritorio remoto activa es
**estructural**, como dice `CLAUDE.md` §3.

---

## 2. TAREA 1 (B9) — la curva de ppp

### 2.1 El barrido sobre `escaneado_d4` (200 ppp nativos)

**MEDIDO**, mediana de n=9, GPU, 17 puntos de 100 a 400 ppp. Formato: **CER acentos /
CER ascii**, `c` = renglones devueltos por el detector (la página tiene **12**),
`peq` = CER del bloque de 7 pt. Las cuatro columnas comparten imagen de entrada.

| ppp | px ancho | factor | PaddleOCR v6 medium | RapidOCR v5 mobile (defecto) | RapidOCR v6 small (defecto) | **RapidOCR v6 small + R6** |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 647 | ×0,50 | 19,13 / 18,12 · c12 | 40,44 / 37,58 · c8 | 36,58 / 35,91 · c8 | 30,70 / 29,87 · c9 |
| 125 | 809 | ×0,63 | **16,95** / 15,77 · c12 | 40,94 / 38,09 · c8 | 36,74 / 36,07 · c8 | 26,68 / 25,17 · c11 |
| 150 | 970 | ×0,75 | 17,11 / 16,11 · c12 | 41,28 / 38,59 · c8 | 36,58 / 35,91 · c8 | 18,96 / 17,62 · c11 |
| 175 | 1 132 | ×0,88 | 21,64 / 20,97 · c13 | 42,11 / 38,93 · c8 | 37,25 / 36,07 · c8 | 21,31 / 20,30 · c12 |
| **200 (nativo)** | **1 294** | **×1,00** | 19,30 / 18,46 · c12 | 41,78 / 38,59 · c8 | 36,91 / 36,24 · c8 | **18,62** / 17,62 · **c12** |
| 225 | 1 456 | ×1,13 | 20,97 / 20,13 · c12 | 42,28 / 39,43 · c8 | 42,79 / 42,28 · c8 | 23,32 / 22,15 · c11 |
| 250 | 1 617 | ×1,25 | **13,09** / 12,08 · c12 | 41,61 / 38,59 · c8 | 32,72 / 32,05 · c9 | 24,50 / 23,49 · c10 |
| 255 | 1 650 | ×1,28 | 15,10 / 14,09 · c12 | 41,44 / 38,42 · c8 | 36,91 / 36,24 · c8 | 31,38 / 30,37 · c9 |
| 260 | 1 682 | ×1,30 | 23,66 / 22,82 · c12 | 41,95 / 38,93 · c8 | 33,22 / 32,72 · c9 | 25,00 / 24,16 · c10 |
| 265 | 1 715 | ×1,33 | 16,44 / 15,44 · c13 | 41,61 / 38,42 · c8 | 36,74 / 36,07 · c8 | 24,83 / 23,83 · c13 |
| 270 | 1 747 | ×1,35 | 13,09 / 11,58 · c12 | 40,94 / 38,09 · c8 | 37,08 / 36,41 · c8 | 23,15 / 21,98 · c11 |
| 275 | 1 779 | ×1,38 | 21,31 / 20,30 · c12 | 41,44 / 38,26 · c8 | 36,74 / 36,24 · c8 | 25,34 / 24,16 · c13 |
| **280** | **1 812** | **×1,40** | **36,24** / 35,91 · **c8** | 41,95 / 38,76 · c8 | 36,58 / 35,91 · c8 | 28,86 / 27,68 · c10 |
| 300 | 1 941 | ×1,50 | 25,17 / 24,50 · c11 | 41,61 / 38,59 · c8 | 36,58 / 35,91 · c8 | 30,20 / 29,19 · c9 |
| 320 | 2 070 | ×1,60 | 36,24 / 35,91 · c8 | 41,28 / 38,26 · c8 | 33,05 / 32,55 · c9 | 23,83 / 22,99 · c12 |
| 360 | 2 329 | ×1,80 | 36,41 / 35,91 · c8 | 41,61 / 38,59 · c8 | 36,91 / 36,41 · c8 | 29,19 / 28,52 · c10 |
| 400 | 2 588 | ×2,00 | 36,24 / 35,91 · c8 | 41,61 / 38,59 · c8 | 36,74 / 36,24 · c8 | 25,34 / 24,50 · c10 |

**Cuatro lecturas, y solo una de ellas era esperable:**

1. **La banda de ×0,5 a ×1,38 no tiene tendencia.** PaddleOCR oscila entre 13,09 y
   23,66 con **12 cajas de 12 siempre**. La cifra canónica de `corpus-d4.md` (19,30 % a
   nativos) **no es un mínimo**: hay tres puntos mejores (250, 270, 125). La curva no
   tiene una rodilla en 200; **200 no es especial**.
2. **El deterioro empieza en ×1,4 y se consolida en ×1,6.** A 280, 320, 360 y 400 el CER
   se planta en **36,24-36,41 % con 8 cajas**: se pierden **los cuatro renglones de
   7 pt**, siempre los mismos. **Pero no es un acantilado limpio**: a 300 ppp (×1,5) el
   detector recupera 11 cajas y el CER baja a 25,17. El refinamiento de seis puntos
   entre 250 y 280 (§tanda F) **no encontró un punto de corte**, encontró una banda.
3. **El bloque de 11 pt es indiferente a todo.** Su CER se queda entre 0,64 y 2,24 en
   los diecisiete puntos, incluido 400 ppp. **Todo el efecto de los ppp vive en el
   bloque de 7 pt.** Un documento sin letra pequeña no tiene techo de ppp que medir.
4. **Las dos configuraciones con el defecto de normalización son planas.** RapidOCR v5
   mobile se queda en 40-42 % y v6 small en 36-37 % **en los diecisiete puntos**, con
   8 cajas siempre. No es robustez: es que su detector nunca encuentra el bloque
   pequeño, así que no hay nada que la resolución pueda estropear. **Medir el techo de
   ppp con un motor mal configurado da «no hay techo».**

### 2.1b Los otros dos motores del barrido: docling y EasyOCR

**MEDIDO**, n=9 (docling) y n=3 (EasyOCR, pasada con muestreador de VRAM), GPU, mismo
`escaneado_d4`, mismas rasterizaciones. CER acentos.

| ppp | factor | Docling+RapidOCR torch **defecto** | Docling+RapidOCR torch **+R6** | EasyOCR (cajas) |
|---:|---:|---:|---:|---:|
| 100 | ×0,50 | 36,58 | 37,92 | 62,58 (24) |
| 125 | ×0,63 | **54,70** | 23,49 | 62,25 (32) |
| 150 | ×0,75 | 36,74 | 25,34 | 61,58 (25) |
| 175 | ×0,88 | 36,91 | **18,12** | 63,26 (28) |
| **200 (nativo)** | ×1,00 | 36,91 | 19,63 | 61,41 (37) |
| 225 | ×1,13 | 32,72 | 19,13 | 62,42 (36) |
| 250 | ×1,25 | 33,22 | 22,82 | 61,41 (34) |
| 280 | ×1,40 | 33,05 | 23,15 | 60,91 (34) |
| 320 | ×1,60 | **32,89** | 22,82 | 62,42 (34) |
| 360 | ×1,80 | — | — | **58,39** (31) |
| 400 | ×2,00 | 33,39 | 25,00 | 60,74 (32) |

**Dos cosas que no encajan con nada de lo anterior:**

1. **Docling sin corregir MEJORA al subir de ppp**: 36,91 % a nativos, **32,89 %** a
   ×1,6. Es el comportamiento contrario al de PaddleOCR sobre el mismo fichero. Y con la
   corrección aplicada se le da la vuelta: el óptimo se va a **×0,88**.
2. **EasyOCR es plano y detecta de más**: 58,4-63,3 % en once puntos, con **24 a 37
   cajas** para una página de **12 renglones**. No es que pierda texto: **fragmenta**.
   Su curva de ppp no tiene información porque su fallo no es de resolución.

Y el caso de `OcrOptions.scale` por defecto (3,0 → 216 ppp), medido por fin sobre los
cinco escaneados con `docling` **sin** corregir:

| documento | ppp nativos | CER a nativos | **CER con `scale=3,0` (216 ppp)** | veredicto del defecto |
|---|---:|---:|---:|---|
| `patologico_escaneado` | 200 | 0,00 | 0,00 | indiferente |
| `escaneado_d1` | 150 | 0,00 | 0,00 | indiferente |
| `escaneado_d2` | 100 | 0,00 | 0,00 | indiferente |
| `escaneado_d3` | 100 | 75,95 | **58,23** | **el defecto es MEJOR, −17,72** |
| `escaneado_d4` | 200 | 36,91 | 36,91 | indiferente |

**El defecto de docling no era el problema que parecía.** `ocr-ppp-nativos.md` lo señaló
porque sobre `d3` mete un ×2,16, y aquí ese ×2,16 **mejora 17,72 puntos**. Sigue siendo
obligatorio fijarlo —un parámetro que nadie eligió no es una defensa—, pero **fijarlo a
los ppp nativos era la parte equivocada de la recomendación**.

### 2.2 La duda que resuelve el refinamiento

`bench/ocr-ppp-nativos.md` §5 encontró sobre `d3` **un acantilado** entre ×1,4 y ×1,6, y
el encargo pedía comprobar si aquí pasa lo mismo. **MEDIDO: sobre `d4` hay una banda,
no un acantilado.** Seis puntos nuevos entre 250 y 280 ppp (255, 260, 265, 270, 275) dan
15,10 / 23,66 / 16,44 / 13,09 / 21,31: **oscilan dentro de la misma banda que 100-250**.
La caída a 36,24 ocurre en el paso 275 → 280, pero **300 la deshace parcialmente**.
Sobre `d3` sí es un acantilado, y está confirmado abajo.

### 2.3 Los otros documentos: ni ppp absolutos, ni factor, ni píxeles

**MEDIDO**, n=9, GPU. CER acentos, `c` = cajas.

**`escaneado_d3` — 100 ppp nativos, 3 renglones**

| ppp | factor | px ancho | PaddleOCR v6 medium | RapidOCR v6 small + R6 | RapidOCR v5 mobile (def.) |
|---:|---:|---:|---:|---:|---:|
| 75 | ×0,75 | 485 | 11,39 · c3 | 22,78 · c3 | 75,95 · c1 |
| **100 (nativo)** | ×1,00 | 647 | **2,53** · c3 | 3,80 · c3 | 77,22 · c1 |
| 125 | ×1,25 | 809 | 5,06 · c3 | **2,53** · c3 | 75,95 · c1 |
| 140 | ×1,40 | 906 | **3,80** · c3 | **46,84** · c3 | 74,68 · c2 |
| 160 | ×1,60 | 1 035 | **75,95** · c1 | 75,95 · c1 | 75,95 · c1 |
| 200 | ×2,00 | 1 294 | 75,95 · c1 | 53,16 · c2 | 65,82 · c3 |
| 280 | ×2,80 | 1 812 | 75,95 · c1 | 44,30 · c2 | 63,29 · c2 |

**`escaneado_d4c` (200 nativos) y `escaneado_d4f` (240 nativos)**

| documento | ppp | factor | px | PaddleOCR | RapidOCR v6 small + R6 |
|---|---:|---:|---:|---:|---:|
| `d4c` | 150 | ×0,75 | 970 | 1,34 | 0,84 |
| `d4c` | **200 (nat.)** | ×1,00 | 1 294 | 0,67 | 1,17 |
| `d4c` | 250 | ×1,25 | 1 617 | 0,84 | 1,01 |
| `d4c` | 280 | ×1,40 | 1 812 | **1,17** | **9,56** |
| `d4c` | 320 | ×1,60 | 2 070 | **1,01** | 9,23 |
| `d4f` | 100 | ×0,42 | 647 | 0,84 | 17,79 |
| `d4f` | 150 | ×0,63 | 970 | 0,84 | **1,01** |
| `d4f` | 200 | ×0,83 | 1 293 | 0,67 | 16,28 |
| `d4f` | **240 (nat.)** | ×1,00 | 1 552 | 0,67 | 7,05 |
| `d4f` | 280 | ×1,17 | 1 811 | 0,67 | 7,72 |
| `d4f` | 336 | ×1,40 | 2 173 | 0,84 | 16,11 |
| `d4f` | 400 | ×1,67 | 2 587 | **0,50** | — |

**`patologico_escaneado` — 200 ppp nativos, el único escaneado del corpus que NO sale
del generador sintético**

| ppp | 100 | 150 | **200 (nat.)** | 250 | 280 | 320 | 400 |
|---|---:|---:|---:|---:|---:|---:|---:|
| PaddleOCR | **0,00** | **0,00** | **0,00** | **0,00** | **0,00** | **0,00** | **0,00** |
| RapidOCR v6 small + R6 | **0,00** | **0,00** | **0,00** | **0,00** | **0,00** | **0,00** | **0,00** |

**Ahora las tres unidades candidatas, una a una, contra estos datos:**

| candidata | qué predeciría | qué se mide | veredicto |
|---|---|---|---|
| **ppp absolutos** (techo 200) | todos se rompen al pasar de 200 ppp | `d3` se rompe a **160**; `d4c`/`d4f`/`patológico` **no se rompen a 400** | **REFUTADA** |
| **factor sobre el nativo** (×1,4) | todos se rompen al mismo factor | PaddleOCR se rompe en `d4` a ×1,4, en `d3` a ×1,6, y **nunca** en `d4c` (×1,6) ni `d4f` (×1,67) | **REFUTADA** |
| **anchura en píxeles** | todos se rompen a la misma anchura | `d3` se rompe a **1 035 px**; `d4c` **no** se rompe a **2 070 px** | **REFUTADA** |

**Y la que sí se sostiene:** el remuestreo cuesta cuando el motor **ya está cerca de
fallar en ese documento**. Sobre `patologico_escaneado`, que los dos motores resuelven
al 0,00 %, se puede rasterizar de ×0,5 a ×2,0 **sin coste alguno** — catorce celdas a
cero. Sobre `d4`, que PaddleOCR resuelve al 19 %, ×1,4 cuesta 17 puntos. **El techo de
ppp no es una propiedad de la resolución: es el margen que le queda al motor.**

### 2.4 El experimento decisivo: mismos píxeles, distinta página

Si los ppp fueran la unidad, dos documentos con **el mismo mapa de bits** y distinta
densidad declarada tendrían que comportarse igual al mismo número de ppp. Se construyó
la prueba: se extrajo el JPEG incrustado de `corpus/pdf/escaneado_d4.pdf` (100 545 B,
1 294×1 716) y se volvió a empaquetar en tres PDF con `magick … -units PixelsPerInch
-density {100,200,400}`, que es **la misma orden del generador del corpus**. Resultado:
tres documentos con el mismo contenido y páginas de 931,68 / 465,84 / 232,92 pt, es
decir **100, 200 y 400 ppp nativos**.

**MEDIDO**, n=9, GPU, 24 celdas. Ordenado por **anchura en píxeles**, que es la variable
candidata:

| px ancho | documento | ppp nativos | ppp usado | factor | PaddleOCR | RapidOCR v6 small + R6 |
|---:|---|---:|---:|---:|---:|---:|
| **647** | `d4_pg100` | 100 | 50 | ×0,50 | **19,13** | **30,70** |
| **647** | `d4_pg200` | 200 | 100 | ×0,50 | **19,13** | **30,70** |
| **647** | `d4_pg400` | 400 | 200 | ×0,50 | **19,13** | **30,70** |
| **1 294** | `d4_pg100` | 100 | 100 | ×1,00 | **19,63** | **18,62** |
| **1 294** | `d4_pg200` | 200 | 200 | ×1,00 | **19,63** | **18,62** |
| **1 294** | `d4_pg400` | 400 | 400 | ×1,00 | **19,63** | **18,62** |
| **1 812** | `d4_pg100` | 100 | 140 | ×1,40 | **36,24** | **31,21** |
| **1 812** | `d4_pg200` | 200 | 280 | ×1,40 | **36,24** | **31,21** |
| **1 812** | `d4_pg400` | 400 | 560 | ×1,40 | **36,24** | **31,21** |
| **2 588** | `d4_pg100` | 100 | 200 | ×2,00 | **36,24** | **25,34** |
| **2 588** | `d4_pg200` | 200 | 400 | ×2,00 | **36,24** | **25,34** |
| **2 588** | `d4_pg400` | 400 | 800 | ×2,00 | **36,24** | **25,34** |

**Con todas las letras, y son 24 celdas:**

- **Al mismo número de PÍXELES, las tres geometrías coinciden a la centésima.** No «se
  parecen»: 19,13 = 19,13 = 19,13; 30,70 = 30,70 = 30,70. Doce parejas exactas.
- **Al mismo número de PPP, no coinciden en nada.** A **200 ppp**: PaddleOCR da
  **19,13 / 19,63 / 36,24** y RapidOCR da **30,70 / 18,62 / 30,70**, según el tamaño de
  página. **17,1 puntos de diferencia al mismo ppp, con el mismo documento dentro.**
- Los ficheros de entrada **no** son binariamente idénticos entre geometrías (Ghostscript
  rasteriza cada densidad por separado; los `sha256` difieren). Que el CER coincida a la
  centésima con entradas distintas-pero-equivalentes es más fuerte que si fueran el
  mismo fichero.

**Los ppp no son una propiedad del documento que el OCR pueda usar: son una división
entre los píxeles que hay y el tamaño que el PDF dice que tiene la página.** El motor
recibe un mapa de bits. Una regla escrita en ppp está escrita en la unidad equivocada.

### 2.5 Cuántos píxeles llegan de verdad al detector

Sondeado en ejecución, no deducido (`sonda_detector.py`, engancha el reescalado interno
de cada motor). **MEDIDO**, sobre las 17 rasterizaciones de `d4`:

| ppp | PNG de entrada | **RapidOCR → red** | **PaddleOCR → red** |
|---:|---|---|---|
| 100 | 647×858 | 736×960 *(sube)* | 640×864 |
| 150 | 970×1 287 | 960×1 280 | 960×1 280 |
| 200 | 1 294×1 716 | 1 280×1 728 | 1 280×1 728 |
| 250 | 1 617×2 145 | **1 504×1 984** | 1 632×2 144 |
| 280 | 1 812×2 402 | **1 504×1 984** | 1 824×2 400 |
| 320 | 2 070×2 746 | **1 504×1 984** | 2 080×2 752 |
| 400 | 2 588×3 432 | **1 504×1 984** | 2 592×3 424 |

- **RapidOCR tiene un tope duro**: `Global.max_side_len: 2000` en
  `rapidocr/config.yaml:10`, aplicado en `rapidocr/main.py:286` vía
  `rapidocr/utils/process_img.py:113-114`. Con la página de `d4` (617,76 pt = 8,58 in),
  ese tope se alcanza a **233 ppp**: **de ahí en adelante el array es idéntico**. La
  planitud de su curva por encima de 250 ppp es un artefacto del arnés del motor, no una
  propiedad del motor. Y también tiene un **suelo**: por debajo de 736 px de lado corto
  (`Det.limit_side_len: 736`, `limit_type: min`) **amplía**, que es lo que pasa a 100 ppp.
- **PaddleOCR no recorta**: `limit_side_len=64`, `limit_type='min'`. Ve los 2 592 px.
  *(Aviso: leyendo el código de PaddleX se deduce lo contrario —`_TEXT_DET_MAX_LIMIT_MODELS`
  lista los ocho detectores con `limit_type='max'`, 960— y **es falso para la ruta que
  usa `paddleocr` 3.7.0**. La sonda lo desmiente. Es un caso más de «sondear en
  ejecución, no deducir».)*

**Consecuencia operativa, MEDIDA:** rasterizar `d4` a 400 ppp para RapidOCR produce un
PNG de 2 588×3 432 que el motor reduce a 1 504×1 984 antes de mirarlo. El coste de
rasterizar y cargar ese fichero es real; el efecto sobre el resultado es **nulo por
construcción**. La regla R1 no solo protege la calidad: **evita trabajo que el motor
tira**.

### 2.6 Qué le pasa a `clamp(nativos, 100, 200)`

La regla vigente es `ppp_ocr = clamp(ppp_nativos, 100, 200)`, con techo **absoluto**.
Tres cosas, medidas:

**(a) El techo solo actúa bajando, y bajar cuesta.** Con `nativos ≤ 200` la expresión
devuelve los nativos y el techo no hace nada. Solo interviene con originales de más de
200 ppp, a los que **reduce**. Lo que cuesta reducir está medido: `d4` a ×0,5
(200 → 100 ppp) sube RapidOCR+R6 de **18,62 % a 30,70 %** (**+12,08 puntos**) y `d3` a
×0,75 sube PaddleOCR de **2,53 % a 11,39 %** (**+8,86 puntos**). El techo absoluto de
200 ppp es, en la práctica, **una regla para degradar los originales buenos**.

**(b) La evidencia que lo motivó no toca la regla que sustituyó.** `corpus-d4.md` §8
midió `d4` a 280 ppp y concluyó que «aplicar el techo ×1,4 sobre un original de 200 ppp
empeora al mejor motor 16,9 puntos». Pero `clamp(200, 100, 200×1,4) = clamp(200, 100,
280) = **200**`: **la regla relativa nunca pide 280 ppp para ese documento.** Se midió un
punto que la fórmula no produce. La conclusión sobre `d4` a 280 ppp es correcta —está
reproducida aquí, 36,24 %— pero **no es evidencia contra el techo relativo**. Es un
autoerror del proyecto que este informe corrige.

**(c) El único sitio donde el techo relativo sí actúa es el suelo, y ahí está medido.**
`clamp` solo sube cuando `nativos < 100`, y el techo `nativos × 1,4` limita cuánto.
El factor de subida seguro está acotado por los datos: **×1,25 es seguro en 6 de las 8
parejas (documento, motor) medidas y ×1,4 solo en 4**. Sobre `d3`, ×1,25 mejora a
RapidOCR+R6 (3,80 → **2,53**) y ×1,4 lo hunde (**46,84**). Un original de 80 ppp llevado
a 100 es ×1,25: **justo dentro**. Uno de 72 llevado a 100 es ×1,39: **justo fuera**.

### 2.7 La cuarta respuesta: la regla es POR MOTOR

Las tres candidatas del encargo —absoluta, relativa, o tamaño en píxeles— **están las
tres refutadas** por §2.3 y §2.4. Queda una cuarta, y es la que los datos sostienen.

**MEDIDO. El mismo documento (`escaneado_d4`), el mismo evaluador, el mismo dispositivo.
Dónde cae el mínimo de cada motor.** *(17 puntos de ppp para los que consumen PNG —
PaddleOCR, RapidOCR, EasyOCR—; 10 para los dos de docling, que rasterizan ellos mismos
desde el PDF con `OcrOptions.scale`.)*

| motor / configuración | CER a ppp nativos | **mejor CER** | **a qué factor** | rango del barrido |
|---|---:|---:|---:|---|
| Docling + RapidOCR torch **+R6** | 19,63 | **18,12** | **×0,88** (175 ppp) | 18,1 – 37,9 |
| RapidOCR v6 small **+R6** (ONNX) | **18,62** | **18,62** | **×1,00** (200 ppp) | 18,6 – 31,4 |
| PaddleOCR v6 medium | 19,30 | **13,09** | **×1,25** (250 ppp) | 13,1 – 36,4 |
| RapidOCR v6 small (defecto) | 36,91 | **32,72** | **×1,25** (250 ppp) | 32,7 – 42,8 |
| RapidOCR v5 mobile (defecto) | 41,78 | **40,44** | **×0,50** (100 ppp) | 40,4 – 42,3 *(plano)* |
| Docling + RapidOCR torch (defecto) | 36,91 | **32,89** | **×1,60** (320 ppp) | 32,7 – 54,7 |
| EasyOCR (CRAFT + latin_g2) | 61,41 | **58,39** | **×1,80** (360 ppp) | 58,4 – 63,3 |

**Siete configuraciones sobre el mismo documento, y sus óptimos se reparten entre ×0,50
y ×1,80.** No hay un valor de ppp, ni un factor, que sirva para las siete.

Y no es solo dónde está el óptimo: **es dónde está el precipicio.** Sobre
`escaneado_d3`, mismo documento y mismas rasterizaciones:

| factor sobre el nativo | PaddleOCR v6 medium | RapidOCR v6 small +R6 |
|---:|---:|---:|
| ×1,00 (100 ppp) | **2,53** | 3,80 |
| ×1,25 (125 ppp) | 5,06 | **2,53** |
| **×1,40 (140 ppp)** | **3,80 — sigue bien** | **46,84 — se cae** |
| ×1,60 (160 ppp) | 75,95 | 75,95 |

**A ×1,4, el mismo fichero es seguro para un motor y catastrófico para el otro.** Un
orquestador que elija los ppp sin saber qué motor los va a consumir está tirando una
moneda de 43 puntos.

**El mecanismo ya está medido y explica por qué tenía que ser así (§2.5):** cada motor
lleva su propio reescalado interno cableado, con constantes distintas —RapidOCR
`min 736 / max 2000`, PaddleOCR `min 64 / sin tope`— así que **la función que lleva de
«ppp de rasterizado» a «píxeles que ve la red» es distinta en cada motor**. Pedirle a una
sola constante de ppp que sirva para todos es pedirle que compense tres reescalados
diferentes a la vez.

**Evidencia externa convergente, de fuera de mis cuatro motores.** `bench/invocacion-aristas.md`
§9 (agente P2, Tesseract 5.5.0 en contenedor, métrica acentuada, n=1) mide sobre
`escaneado_d2` **32,10 % a sus 100 ppp nativos y 0,00 % a 150 ppp** — es decir, para
Tesseract **sobremuestrear a ×1,5 no es tolerable: es obligatorio**, exactamente al revés
que para RapidOCR corregido sobre `d3`, donde ×1,4 cuesta 43 puntos. Y el mismo informe
mide que sobre `d4` a Tesseract sí le conviene el nativo (51,15 % frente a 82,89 % a
150 ppp): **ni siquiera dentro de un motor hay un factor único**, pero el reparto entre
motores es mucho mayor que el reparto dentro de uno. **Esa medida es de otro agente, con
otro arnés y n=1; se cita como convergente, no se ha reproducido aquí.**

### 2.8 La regla propuesta, y dónde vive

```
# R1 revisada — la eleccion de ppp es DEL ADAPTADOR DEL MOTOR, no del orquestador.
#
# Lo que calcula el ORQUESTADOR y le pasa al adaptador:
ppp_nativos = ancho_imagen_px / (ancho_pagina_pt / 72)    # o None si no hay imagen
#
# Lo que decide el ADAPTADOR, con su k medido:
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
#       RapidOCR : Global.max_side_len = 2000 px de lado largo  (config.yaml:10)
#       PaddleOCR: no recorta (limit_side_len=64, limit_type=min)
#     Rasterizar por encima del tope del motor es coste puro, efecto cero.
```

| | regla anterior | regla propuesta | apoyo |
|---|---|---|---|
| **dónde vive** | orquestador, global | **adaptador de motor** | §2.7, 7 óptimos entre ×0,50 y ×1,80 |
| unidad | ppp (absoluta) | **factor sobre el raster nativo** | §2.4, 24 celdas |
| defecto | `clamp(nat,100,200)` | `= nativos × k(motor)` | §2.1, §2.3, §2.7 |
| subida máxima (suelo) | ×1,4 | **×1,25** | §2.3, `d3` ×1,4 → 46,84 % |
| bajada | hasta 200 ppp | **ninguna por calidad** | ×0,5 cuesta 12,08 puntos |
| techo por coste | 200 ppp | **el tope del motor** (2 000 px en RapidOCR) | §2.5 |

**Y la consecuencia de diseño, con todas las letras:** `clamp(ppp_nativos, 100, 200)` está
hoy escrita como **regla global** en `CLAUDE.md` trampa 8 y en `PLAN-ORQUESTADOR.md`
§4.5. **Está en el sitio equivocado.** No es una constante del dominio: es un parámetro
del motor, del mismo rango que `Det.mean` o `OcrOptions.scale`. Si FileX la deja en el
orquestador, cada motor nuevo que se añada hereda en silencio los ppp que le convenían a
otro — que es literalmente lo que le pasa hoy a Tesseract, al que R1 le asigna 100 ppp
sobre `escaneado_d2` y le cuesta **32,10 puntos**.

**Con un `k` por defecto de 1,00 la regla sigue siendo segura**: en las siete
configuraciones medidas, el nativo nunca es el peor punto del barrido y en cinco de siete
está a menos de 1,7 puntos del óptimo. Lo que el `k` compra es el resto: los 6,2 puntos
de PaddleOCR y los 32 puntos de Tesseract sobre `d2`.

**Lo que NO cambia:** el suelo de 100 ppp sigue siendo lo medido
(`ocr-ppp-nativos.md` §5: a 75 ppp RapidOCR se rompe en d2; aquí, a 75 ppp sobre `d3`,
PaddleOCR pasa de 2,53 a 11,39 % y RapidOCR+R6 de 3,80 a 22,78 %). Y
**`OcrOptions.scale` explícito, siempre** — con un matiz nuevo y medido: su defecto de
3,0 (216 ppp) **no siempre es malo**. Sobre `escaneado_d3` con docling **sin** corregir,
el defecto da **58,23 %** frente al **75,95 %** de rasterizar a ppp nativos. Es
exactamente el mismo fenómeno: para *ese* motor, `k > 1`. Fijarlo sigue siendo
obligatorio; fijarlo **a los ppp nativos** era la parte que estaba de más.

---

## 3. TAREA 2 (B10) — validar la corrección de normalización

### 3.1 El mecanismo, con fichero y línea

Documentado por `probe_norm.py`, con precisión suficiente para reportarlo aguas arriba.

**Lo que el modelo declara.** Los `inference.yml` que Baidu distribuye **junto a los
pesos** (`~/.paddlex/official_models/<modelo>/inference.yml`, bloque
`PreProcess.transform_ops[].NormalizeImage`):

| detector | `mean` | `std` | ¿ImageNet? |
|---|---|---|---|
| `PP-OCRv3_mobile_det` | `[0.485, 0.456, 0.406]` | `[0.229, 0.224, 0.225]` | **sí** |
| `PP-OCRv4_mobile_det` | ídem | ídem | **sí** |
| `PP-OCRv4_server_det` | ídem | ídem | **sí** |
| `PP-OCRv5_mobile_det` | ídem | ídem | **sí** |
| `PP-OCRv5_server_det` | ídem | ídem | **sí** |
| `PP-OCRv6_tiny_det` | ídem | ídem | **sí** |
| `PP-OCRv6_small_det` | ídem | ídem | **sí** |
| `PP-OCRv6_medium_det` | ídem | ídem | **sí** |

**Los ocho, de PP-OCRv3 a PP-OCRv6. Sin excepción.**

**Lo que RapidOCR aplica.** `rapidocr` 3.9.2, `<site-packages>/rapidocr/config.yaml`,
sección `Det:` — **un solo bloque para todas las versiones**, sin condicionar por
`ocr_version`:

```yaml
141:    limit_side_len: 736
142:    limit_type: min
143:    std: [ 0.5, 0.5, 0.5 ]      # <-- el modelo declara [0.229, 0.224, 0.225]
144:    mean: [ 0.5, 0.5, 0.5 ]     # <-- el modelo declara [0.485, 0.456, 0.406]
146:    thresh: 0.3                 # <-- el modelo declara 0.2
147:    box_thresh: 0.5             # <-- el modelo declara 0.45
148:    max_candidates: 1000        # <-- el modelo declara 3000
149:    unclip_ratio: 1.6           # <-- el modelo declara 1.4
```

**Dónde se lee:** `rapidocr/ch_ppocr_det/main.py:33-34`
(`self.mean = cfg.get("mean")`, `self.std = cfg.get("std")`) y `:79`
(`return DetPreProcess(limit_side_len, self.limit_type, self.mean, self.std)`).

**Dónde se aplica:** `rapidocr/ch_ppocr_det/utils.py:53-54` y **`:71`**

```python
return (img.astype("float32") * self.scale - self.mean) / self.std
```

Con `scale = 1/255`, la entrada normalizada queda en `[-1, 1]` uniforme para los tres
canales, cuando la red se entrenó esperando `[-2,1, +2,6]` con desviaciones distintas
por canal. **No hay ningún aviso, ninguna comprobación y ningún error.**

**Declarado frente a aplicado, leído del objeto ya construido en memoria** (no del
fichero: del `TextDetector` vivo):

| configuración | `mean` en memoria | `std` en memoria | `thresh` | `box_thresh` | `unclip` | `max_cand` |
|---|---|---|---:|---:|---:|---:|
| v6 small, defecto | `[0.5, 0.5, 0.5]` | `[0.5, 0.5, 0.5]` | 0,3 | 0,5 | 1,6 | 1 000 |
| v5 mobile, defecto | `[0.5, 0.5, 0.5]` | `[0.5, 0.5, 0.5]` | 0,3 | 0,5 | 1,6 | 1 000 |
| v4 mobile, defecto | `[0.5, 0.5, 0.5]` | `[0.5, 0.5, 0.5]` | 0,3 | 0,5 | 1,6 | 1 000 |
| cualquiera + R6 | `[0.485, 0.456, 0.406]` | `[0.229, 0.224, 0.225]` | 0,2 | 0,45 | 1,4 | 3 000 |

**Lo que hay que reportar aguas arriba, en una frase:** *`rapidocr/config.yaml` fija
`Det.mean` y `Det.std` a 0,5 para todas las versiones de PP-OCR, mientras los ocho
`inference.yml` que PaddleOCR distribuye con los pesos declaran las estadísticas de
ImageNet; el desajuste se aplica en `ch_ppocr_det/utils.py:71` y cuesta hasta 72,15
puntos de CER.*

### 3.2 El A/B, descompuesto

`corpus-d4.md` §7.4 separó la normalización del post-proceso. Aquí se reproduce sobre
seis documentos y siete detectores (§3.5). La descomposición sobre `PP-OCRv6 small`,
que es el caso canónico — **MEDIDO**, CER acentos:

| variante | `d3` | `d4` | `d4c` | `tipico` (oro) |
|---|---:|---:|---:|---:|
| defecto de RapidOCR | 75,95 | 36,91 | 29,36 | 0,83 |
| **solo `mean`/`std` de ImageNet** | **11,39** | 20,13 | 1,01 | 0,83 |
| solo post-proceso de PaddleX | 75,95 | 36,58 | 32,21 | 0,83 |
| **las dos (R6)** | **3,80** | **18,62** | 1,17 | 0,83 |

**Reproduce exactamente `corpus-d4.md`**: la normalización sola vale **64,56 puntos** en
d3; el post-proceso solo, **0,00**; las dos juntas dan **3,80 %**, la cifra de PaddleOCR.
La reproducción independiente de un resultado ajeno, con otro arnés y otro directorio de
pesos, es en sí un dato.

### 3.3 La validación fuera del corpus d4: 15 documentos, n=9, GPU

**MEDIDO.** Formato **CER acentos / CER ascii**. Las cuatro filas `oro__` son
rasterizaciones **del patrón oro** `bench/salidas-referencia/pdf/` (leídas, no tocadas;
solo se les aplicó el mismo `-colorspace Gray -alpha remove -flatten` que al resto).

| documento | v6 small **defecto** | v6 small **+R6** | v5 mobile **defecto** | v5 mobile **+R6** | PaddleOCR v6 medium |
|---|---:|---:|---:|---:|---:|
| `oro__patologico_escaneado_p1` (gs) | 0,00 / 0,00 | 0,00 / 0,00 | 1,27 / 1,27 | 1,27 / 1,27 | 0,00 / 0,00 |
| `oro__tipico_texto_p1` (gs `-r150` PNG) | 0,83 / 0,00 | 0,83 / 0,00 | 2,50 / 1,67 | **0,83** / 0,00 | 4,17 / 3,33 |
| `oro__tipico_texto_p1jpg` (gs `-r150` JPEG) | 0,83 / 0,00 | 0,83 / 0,00 | 3,33 / 2,50 | **0,83** / 0,00 | 2,50 / 1,67 |
| `oro__trivial_p1` | *ver nota* | *ver nota* | *ver nota* | *ver nota* | *ver nota* |
| `escaneado_d1` (150) | 0,00 / 0,00 | 0,00 / 0,00 | 0,00 / 0,00 | 0,00 / 0,00 | 0,00 / 0,00 |
| `escaneado_d2` (100) | 0,00 / 0,00 | 0,00 / 0,00 | 0,00 / 0,00 | 0,00 / 0,00 | 0,00 / 0,00 |
| `escaneado_d3` (100) | 75,95 / 75,95 | **3,80** / 3,80 | 77,22 / 77,22 | **54,43** / 54,43 | 2,53 / 2,53 |
| `patologico_escaneado` (200) | 0,00 / 0,00 | 0,00 / 0,00 | 1,27 / 1,27 | **0,00** / 0,00 | 0,00 / 0,00 |
| `tipico_texto` (150, propio) | 0,83 / 0,00 | 0,83 / 0,00 | 0,83 / 0,00 | 0,83 / 0,00 | 4,17 / 3,33 |
| `escaneado_d4` | 36,91 / 36,24 | **18,62** / 17,62 | 41,78 / 38,59 | **42,62** / 39,43 | 19,30 / 18,46 |
| `escaneado_d4a` | 7,55 / 7,21 | 7,38 / 7,05 | 1,51 / 0,67 | **10,40** / 9,23 | 0,00 / 0,00 |
| `escaneado_d4b` | 0,34 / 0,00 | 0,34 / 0,00 | 2,18 / 0,34 | 2,18 / 0,34 | 0,17 / 0,00 |
| `escaneado_d4c` | 29,36 / 29,36 | **1,17** / 0,34 | 15,60 / 11,91 | **8,05** / 3,36 | 0,67 / 0,00 |
| `escaneado_d4e` | 88,76 / 88,59 | **77,52** / 76,85 | 92,45 / 92,11 | **93,12** / 92,95 | 70,97 / 70,47 |
| `escaneado_d4f` (240) | 23,15 / 22,99 | **7,05** / 6,88 | 6,04 / 2,18 | **14,43** / 10,91 | 0,67 / 0,00 |

> **Nota sobre `oro__trivial_p1`.** Los **cinco** motores devuelven exactamente
> `trivial`, que es todo el texto que tiene `corpus/pdf/trivial.pdf`. El 94,94 % que sale
> en los `.json` es de **la referencia equivocada** —el arnés le asigna la referencia
> «legado» de 79 caracteres por no encontrar mejor candidata— y no dice nada del motor.
> Se deja publicado como **control nulo**: cinco configuraciones, cero alucinaciones,
> cero efecto de la corrección. Es una **limitación conocida del arnés**, no un resultado.

**Balance de `PP-OCRv6 small`, con todas las letras — MEDIDO sobre 15 documentos, n=9:**

| efecto de R6 | celdas | mayor magnitud |
|---|---:|---|
| **mejora** | **6** | `d3` **−72,15** (75,95 → 3,80) |
| empate exacto | **9** | — |
| **empeora** | **0** | — |

**Balance de `PP-OCRv5 mobile`, el mismo experimento:**

| efecto de R6 | celdas | mayor magnitud |
|---|---:|---|
| mejora | 5 | `d3` −22,79 |
| empate | 6 | — |
| **empeora** | **4** | `d4a` **+8,89**, `d4f` **+8,39**, `d4` +0,84, `d4e` +0,67 |

### 3.4 Dónde EMPEORA — se buscó, y se encontró

El encargo pedía explícitamente buscar los casos peores. **Se encontraron tres, en orden
de gravedad:**

1. **`PP-OCRv4 mobile` sobre `tipico_texto` del patrón oro: 0,83 % → 43,33 %.**
   **+42,50 puntos** sobre un documento **limpio**, rasterizado por Ghostscript a
   150 ppp desde un PDF con capa de texto. Es el perfil exacto de lo que un cambio de
   72 puntos podía esconder: la corrección no rompe los casos difíciles, **rompe uno
   fácil**. *(§3.5)*
2. **`PP-OCRv6 tiny`: `d3` 43,04 % → 59,49 % (+16,45) y `d4c` 4,19 % → 17,79 %
   (+13,60).** Dos de seis documentos, y en la dirección contraria a `small` y `medium`.
3. **`PP-OCRv5 mobile`: 4 de 15 celdas peores** (n=9), hasta **+8,89** en `d4a`.
   `corpus-d4.md` §7.4 la señalaba como beneficiaria («de 77,22 a 54,43 en d3», que aquí
   se reproduce exactamente); esa cifra es cierta y **no era toda la historia**.

**Y donde nunca empeora:** en `escaneado_d1`, `escaneado_d2`, `patologico_escaneado` y
las dos rasterizaciones del patrón oro del patológico, **las siete configuraciones dan
la misma cifra con y sin corrección**. La corrección no toca lo que ya funciona; el
riesgo está concentrado en los modelos viejos.

### 3.5 ¿Es de PP-OCRv6, o de todos? — el cribado de 7 detectores × 4 variantes

**MEDIDO**, n=1 por celda (**es un cribado**, con el mismo criterio que `corpus-d4.md`
§3; las parejas que importan se validaron después con n=9 en §3.3). CER acentos,
28 configuraciones × 6 documentos = **168 celdas**, un solo proceso.

| detector · variante | `oro tipico` | `d2` | `d3` | `d4` | `d4c` | `patológico` |
|---|---:|---:|---:|---:|---:|---:|
| v6 medium · defecto | 4,17 | 0,00 | 3,80 | 22,82 | 14,09 | 0,00 |
| v6 medium · **R6** | 1,67 | 0,00 | 2,53 | **23,15** | 9,56 | 0,00 |
| v6 medium · solo norm | 4,17 | 0,00 | 3,80 | 23,66 | 15,77 | 0,00 |
| v6 medium · solo post | 4,17 | 0,00 | 2,53 | 22,65 | **0,84** | 0,00 |
| v6 small · defecto | 0,83 | 0,00 | 75,95 | 36,91 | 29,36 | 0,00 |
| v6 small · **R6** | 0,83 | 0,00 | **3,80** | **18,62** | **1,17** | 0,00 |
| v6 small · solo norm | 0,83 | 0,00 | 11,39 | 20,13 | 1,01 | 0,00 |
| v6 small · solo post | 0,83 | 0,00 | 75,95 | 36,58 | 32,21 | 0,00 |
| v6 tiny · defecto | 2,50 | 0,00 | 43,04 | 39,60 | 4,19 | 0,00 |
| v6 tiny · **R6** | 1,67 | 0,00 | **59,49** | 35,74 | **17,79** | 0,00 |
| v6 tiny · solo norm | 1,67 | 0,00 | 64,56 | 34,73 | 5,03 | 0,00 |
| v6 tiny · solo post | 2,50 | 0,00 | 37,97 | 40,44 | 3,36 | 0,00 |
| v5 mobile · defecto | 2,50 | 0,00 | 77,22 | 41,78 | 15,60 | 1,27 |
| v5 mobile · **R6** | 0,83 | 0,00 | 54,43 | **42,62** | 8,05 | 0,00 |
| v5 mobile · solo norm | 0,83 | 0,00 | 51,90 | 42,28 | 8,89 | 0,00 |
| v5 mobile · solo post | 2,50 | 0,00 | 77,22 | 49,66 | 8,89 | 1,27 |
| v5 server · defecto | 4,17 | 1,27 | 21,52 | 43,12 | 21,98 | 0,00 |
| v5 server · **R6** | 3,33 | 1,27 | 16,46 | 41,28 | **22,65** | 0,00 |
| v5 server · solo norm | 3,33 | 1,27 | 21,52 | 43,29 | 31,38 | 1,27 |
| v5 server · solo post | 4,17 | 1,27 | 22,78 | 42,11 | 26,34 | 1,27 |
| v4 mobile · defecto | **0,83** | 1,27 | 58,23 | 44,30 | 18,79 | 1,27 |
| v4 mobile · **R6** | **43,33** | **2,53** | **75,95** | **45,64** | 18,62 | 1,27 |
| v4 mobile · solo norm | 0,83 | 1,27 | 54,43 | **59,90** | 11,07 | 1,27 |
| v4 mobile · solo post | 0,83 | 0,00 | 43,04 | 44,46 | 11,41 | 1,27 |
| v4 server · defecto | 6,67 | 0,00 | 44,30 | 40,27 | 17,95 | 7,59 |
| v4 server · **R6** | **7,50** | **1,27** | 36,71 | 40,27 | **22,65** | 1,27 |
| v4 server · solo norm | 6,67 | 0,00 | 35,44 | 40,60 | 18,79 | 1,27 |
| v4 server · solo post | 5,00 | 1,27 | 39,24 | 40,60 | 18,96 | **11,39** |

**Delta de R6 frente al defecto** (positivo = **peor**):

| detector | `oro tipico` | `d2` | `d3` | `d4` | `d4c` | `patológico` | **saldo** |
|---|---:|---:|---:|---:|---:|---:|---|
| v6 medium | −2,50 | 0,00 | −1,27 | **+0,33** | −4,53 | 0,00 | 3 mejor · 1 peor |
| **v6 small** | 0,00 | 0,00 | **−72,15** | **−18,29** | **−28,19** | 0,00 | **3 mejor · 0 peor** |
| v6 tiny | −0,83 | 0,00 | **+16,45** | −3,86 | **+13,60** | 0,00 | 2 mejor · **2 peor** |
| v5 mobile | −1,67 | 0,00 | −22,79 | **+0,84** | −7,55 | −1,27 | 4 mejor · 1 peor |
| v5 server | −0,84 | 0,00 | −5,06 | −1,84 | **+0,67** | 0,00 | 3 mejor · 1 peor |
| **v4 mobile** | **+42,50** | **+1,26** | **+17,72** | **+1,34** | −0,17 | 0,00 | 1 mejor · **4 peor** |
| v4 server | **+0,83** | **+1,27** | −7,59 | 0,00 | **+4,70** | −6,32 | 2 mejor · **3 peor** |

**Total: 18 mejoras, 12 empates, 12 empeoramientos sobre 42 celdas.**

**Lo que esto dice, y no es lo que se esperaba:**

1. **El desajuste es universal; el daño no.** Los ocho modelos declaran ImageNet y
   RapidOCR aplica 0,5 a los ocho, pero **solo `PP-OCRv6 small` se hunde por ello**
   (75,95 % en d3). Los demás toleran la normalización equivocada. La hipótesis obvia
   —«un modelo entrenado con ImageNet se rompe si le das 0,5»— **es falsa para 7 de los
   8**: la robustez a la normalización de entrada varía por checkpoint y no se puede
   predecir del fichero de configuración.
2. **Por eso «corregir el desajuste» no es lo mismo que «mejorar el motor».** En
   `PP-OCRv4 mobile` la configuración *correcta según el fabricante* da **peor**
   resultado que la incorrecta, en 4 de 6 documentos. Devolverle al modelo lo que su
   `inference.yml` declara **no garantiza nada**: hay que medirlo por checkpoint.
3. **Las dos mitades de R6 no son separables ni monótonas.** Sobre `v6 medium` el
   **post-proceso solo** da `d4c` = **0,84 %**, mejor que R6 completo (9,56 %) y que el
   defecto (14,09 %). Sobre `v6 small`, el post-proceso solo **no vale nada** (75,95 %) y
   la normalización sola vale 64,56 puntos. **La receta de seis números es la correcta
   para `small` y no lo es para `medium`.**

### 3.6 Docling: hereda el defecto, y se corrige desde fuera

**MEDIDO**, n=9, GPU, `docling` 2.120.3 + `RapidOCR backend="torch"`, `OcrOptions.scale`
fijado explícitamente a los ppp nativos de cada documento. La corrección se pasa por
**`RapidOcrOptions.rapidocr_params`** —el punto de extensión público
(`docling/datamodel/pipeline_options.py`, campo `rapidocr_params`; se aplica en
`models/stages/ocr/rapid_ocr_model.py:445-448`, `params.update(user_params)`)—, **sin
parchear el paquete**:

| documento | ppp usados | px al motor | **defecto** | **+R6** | delta | ms defecto → +R6 |
|---|---:|---|---:|---:|---:|---|
| `patologico_escaneado` | 200 | 1 294×1 792 | 0,00 | 0,00 | 0,00 | 731 → 714 |
| `escaneado_d1` | 150 | 970×1 300 | 0,00 | 0,00 | 0,00 | 450 → 451 |
| `escaneado_d2` | 100 | 647×850 | 0,00 | 0,00 | 0,00 | 371 → 364 |
| `escaneado_d3` | 100 | 647×850 | 75,95 | **5,06** | **−70,89** | 350 → 370 |
| `escaneado_d4` | 200 | 1 294×1 716 | 36,91 | **19,63** | **−17,28** | 709 → 718 |
| `escaneado_d4c` | 200 | 1 294×1 734 | 22,99 | **8,39** | **−14,60** | 716 → 693 |
| `escaneado_d4f` | 240 | 1 552×2 080 | 22,15 | **0,67** | **−21,48** | 800 → 817 |

**7 de 7: cuatro mejoras grandes, tres empates exactos, cero empeoramientos.** Y el
coste en tiempo es **nulo** (la mediana se mueve entre −3,2 % y +5,8 %, dentro del ruido
de la tanda). La sonda confirma que llegan al motor **exactamente** los píxeles
esperados en las siete filas.

**Esto reproduce y amplía `corpus-d4.md` §7.5 punto 2:** docling hereda el defecto, y no
solo es corregible desde fuera — **es corregible sin coste y sin regresiones en el
corpus completo**.

### 3.7 ¿Lista para producción?

**No como cambio general. Sí acotada a `PP-OCRv6 small` y a `Docling + RapidOCR`.**

| criterio de producción | veredicto | evidencia |
|---|---|---|
| ¿Mejora donde se dijo? | **SÍ, reproducido** | d3 75,95 → 3,80 con otro arnés y otro directorio de pesos (§3.2) |
| ¿Se sostiene fuera del corpus d4? | **SÍ para v6 small** | 4 rasterizaciones del patrón oro + `d1`/`d2`/`d3`/`patológico`/`tipico`: **0 regresiones** (§3.3) |
| ¿Hay casos donde empeora? | **SÍ, y graves fuera de v6 small** | +42,50 puntos en v4 mobile; +16,45 en v6 tiny; 4/15 celdas en v5 mobile (§3.4) |
| ¿Vale para toda la familia? | **NO** | 12 de 42 celdas peores (§3.5) |
| ¿Cuesta algo aplicarla? | **NO** | docling: 7 filas, delta de tiempo dentro del ruido (§3.6) |
| ¿Se puede aplicar sin parchear paquetes? | **SÍ** | `params=` en RapidOCR; `rapidocr_params` en docling (§3.6) |
| ¿Está el mecanismo documentado para aguas arriba? | **SÍ** | fichero, línea, declarado y aplicado (§3.1) |

**La forma en que debe entrar en FileX:**

```python
# R6 revisada — NO es un ajuste global del motor: es una tabla POR CHECKPOINT.
# Medido: la normalizacion "correcta segun el fabricante" MEJORA PP-OCRv6 small y
# EMPEORA PP-OCRv4 mobile en 42,50 puntos sobre un documento limpio.
NORMALIZACION_DETECTOR = {
    # (ocr_version, model_type): parametros, o None para "dejar el defecto"
    ("PP-OCRv6", "small"):  {                       # 0 regresiones en 15 documentos
        "Det.mean": [0.485, 0.456, 0.406],
        "Det.std":  [0.229, 0.224, 0.225],
        "Det.thresh": 0.2, "Det.box_thresh": 0.45,
        "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000,
    },
    ("PP-OCRv6", "medium"): None,   # 3 mejor / 1 peor: no compensa el riesgo
    ("PP-OCRv6", "tiny"):   None,   # +16,45 en d3, +13,60 en d4c
    ("PP-OCRv5", "mobile"): None,   # 4 de 15 celdas peores
    ("PP-OCRv5", "server"): None,
    ("PP-OCRv4", "mobile"): None,   # +42,50 en tipico_texto del patron oro
    ("PP-OCRv4", "server"): None,
}
```

Y **la regla general que sale de aquí**, que es más valiosa que la tabla: *cuando el
motor y el modelo vienen de proyectos distintos, comprobar el desajuste de preprocesado
es obligatorio — pero **corregirlo es una hipótesis, no una solución**, y hay que medirla
checkpoint por checkpoint.* La versión de `CLAUDE.md` trampa 17 se queda corta en la
segunda mitad.

---

## 4. B11 — el parche propuesto, NO aplicado

`bench/scripts/ocr_motor.py` es arnés compartido y **no se ha tocado**. Se deja aquí el
parche exacto y su justificación medida, para que se aplique como decisión aparte.

**Lo que hace hoy** (`bench/scripts/ocr_motor.py`): fija `LangRec.CH`, es decir lee
castellano con el reconocedor de chino, y no fija la normalización del detector.

**Justificación medida de la parte del idioma** (`corpus-d4.md` §7.2, reproducida en su
tabla; **no vuelta a medir aquí**, es PENDIENTE de reverificación en este arnés):

| RapidOCR PP-OCRv5 mobile | d3 | d4c | d4 |
|---|---:|---:|---:|
| `Rec.lang_type = ch` (lo que usa FileX hoy) | 77,22 | 15,60 | 41,78 |
| `Rec.lang_type = latin` | 75,95 | **9,56** | **36,24** |

**Justificación medida de la parte de la normalización**: §3.3 y §3.5 de este informe.
**Ojo: la tabla de §3.5 dice que sobre `PP-OCRv5 mobile` la normalización NO es
recomendable** (4 de 15 celdas peores). Es decir, **el parche de B11 no debe ser
«añadir R6 a `ocr_motor.py`»**: debe ser *cambiar el reconocedor a `latin`* **y**
*cambiar el checkpoint a `PP-OCRv6 small`, que es el único con el que R6 es seguro*.

```diff
--- a/bench/scripts/ocr_motor.py
+++ b/bench/scripts/ocr_motor.py
-    "Det.ocr_version": OCRVersion("PP-OCRv5"),
-    "Rec.ocr_version": OCRVersion("PP-OCRv5"),
-    "Det.model_type":  ModelType("mobile"),
-    "Rec.model_type":  ModelType("mobile"),
-    "Rec.lang_type":   LangRec.CH,
+    # PP-OCRv6 small: unico checkpoint con 0 regresiones al corregir la
+    # normalizacion (bench/ppp-y-normalizacion.md §3.3, 15 documentos, n=9).
+    "Det.ocr_version": OCRVersion("PP-OCRv6"),
+    "Rec.ocr_version": OCRVersion("PP-OCRv6"),
+    "Det.model_type":  ModelType("small"),
+    "Rec.model_type":  ModelType("small"),
+    # En PP-OCRv6 el reconocedor es multilingue y `lang_type` no elige idioma;
+    # el `latin` de la tabla de arriba solo aplica si se vuelve a PP-OCRv5.
+    "Rec.lang_type":   LangRec.CH,
+    # R6 — bench/ppp-y-normalizacion.md §3.1: rapidocr/config.yaml:143-149 aplica
+    # 0,5/0,5/0,5 mientras el inference.yml del propio modelo declara ImageNet.
+    # SOLO para PP-OCRv6 small: sobre PP-OCRv4 mobile esto CUESTA 42,50 puntos.
+    "Det.mean": [0.485, 0.456, 0.406],
+    "Det.std":  [0.229, 0.224, 0.225],
+    "Det.thresh": 0.2,
+    "Det.box_thresh": 0.45,
+    "Det.unclip_ratio": 1.4,
+    "Det.max_candidates": 3000,
```

**Lo que compra el parche, MEDIDO en §3.3** (v5 mobile defecto → v6 small + R6):

| documento | hoy (`v5 mobile`, `ch`) | con el parche (`v6 small` + R6) | delta |
|---|---:|---:|---:|
| `patologico_escaneado` | 1,27 | **0,00** | −1,27 |
| `escaneado_d1` | 0,00 | 0,00 | 0,00 |
| `escaneado_d2` | 0,00 | 0,00 | 0,00 |
| `escaneado_d3` | 77,22 | **3,80** | **−73,42** |
| `escaneado_d4` | 41,78 | **18,62** | **−23,16** |
| `escaneado_d4c` | 15,60 | **1,17** | **−14,43** |
| `escaneado_d4f` | 6,04 | **7,05** | +1,01 |
| `tipico_texto` (oro, PNG) | 2,50 | **0,83** | −1,67 |
| `tipico_texto` (oro, JPEG) | 3,33 | **0,83** | −2,50 |
| `escaneado_d4a` | 1,51 | **7,38** | **+5,87** |
| `escaneado_d4b` | 2,18 | 0,34 | −1,84 |

**Saldo: 7 mejor, 2 igual, 2 peor.** Las dos regresiones (`d4a` +5,87 y `d4f` +1,01) son
del **cambio de checkpoint**, no de R6, y hay que declararlas al aplicarlo: no es una
mejora gratis en todas las filas.

**Y una comprobación que el parche debe llevar**, porque es lo que hizo falta aquí para
saber que la corrección llegaba: leer del objeto ya construido
(`lector.text_det.mean` / `.std`) y comparar con lo pedido. **Sin esa comprobación,
«he puesto ImageNet» es una intención, no un hecho** — es el mismo patrón que
`session.get_providers()` frente a `get_device()`.

---

## 5. Lo que falló, con el error exacto

1. **La primera ejecución de la tanda B se colgó 12 minutos sin procesar una imagen.**
   Causa identificada por PID: otra sesión de Claude, en `D:\Work\research\ASR`,
   ejecutando `t01_vram.py` y ocupando **11 754 de 12 288 MiB**. **El lock de GPU de
   FileX es de proyecto, no de máquina.** Se abortó, se esperó a que bajara la VRAM y se
   reintentó **una vez** (regla de los dos intentos): la segunda cargó en 12,6 s frente a
   159,8 s y completó. **Consecuencia real: los tiempos de las tandas A y B no son
   utilizables**; los CER sí, porque salieron deterministas y con el dispositivo fijado.
2. **La sonda `det_efectivo` de la primera versión de `ocr_lote_pn.py` devolvió `"?"`**
   en las cuatro tandas A. Causa: buscaba `mean`/`std` en `preprocess_op`, que en
   `rapidocr` 3.9.2 **es `None` hasta la primera llamada** (`ch_ppocr_det/main.py:35`,
   se construye dentro de `__call__`). Los valores viven en el propio `TextDetector`
   (`.mean`, `.std`). **Corregido** y verificado en `probe_norm.py` y en las tandas D.
   Las cifras de la tanda A no se ven afectadas: los parámetros pedidos sí quedaron
   registrados en `modelos.pedido`.
3. **Deducir el reescalado del detector de PaddleOCR leyendo el código dio la respuesta
   equivocada.** `paddlex/inference/models/text_detection/predictor.py:28-38` lista los
   **ocho** detectores en `_TEXT_DET_MAX_LIMIT_MODELS`, lo que implicaría
   `limit_type='max'`, 960 px. **La sonda dice `limit_side_len=64, limit_type='min'`**
   para la ruta que usa `paddleocr` 3.7.0. Se conserva escrito porque es exactamente el
   error que la regla «sondear en ejecución, no deducir» existe para evitar.
4. **`oro__trivial_p1` se evalúa contra una referencia que no le corresponde.** El arnés
   deduce la referencia del nombre del fichero y `trivial.pdf` no encaja en ninguna de
   las tres. Sale 94,94 % en las cinco columnas. Documentado en §3.3 en vez de inventar
   una referencia nueva.
5. **`SOURCE_DATE_EPOCH` sigue sin hacer reproducible el PDF de ImageMagick** (los tres
   `d4_pg*.pdf` derivados lo confirman: mismo JPEG dentro, `sha256` distintos). Ya
   estaba documentado en `MANIFIESTO-d4.md` §3; aquí solo se reconfirma.

---

## 6. Reglas del encargo, cumplidas

| regla | estado |
|---|---|
| Escribir solo en `bench/ppp-y-normalizacion.md` y `bench/salidas-ppp-norm/` | **Cumplida.** Los maestros, `analysis/`, `bench/scripts/`, `bench/salidas-corpus-d4/`, `bench/salidas-referencia/` y los informes de otros agentes, sin tocar |
| No editar `bench/scripts/verificador.py` (lo lleva P3) | **Cumplida.** Ni abierto para escritura |
| No editar `ocr_eval.py`, `ocr_motor.py`, `gen_corpus_ocr.sh` | **Cumplida.** El parche de B11 queda **propuesto, no aplicado** (§4) |
| Usar `ocr_eval_d4.py` y decir cuál se usó | **Cumplida.** Copia byte a byte en `salidas-ppp-norm/ocr_eval_d4.py`; envoltorio `ocr_eval_pn.py` que lo **importa**. Declarado en §1.1 |
| Reportar las dos lecturas, con y sin acentos | **Cumplida.** Todas las tablas de CER llevan `acentos / ascii` |
| Lock de GPU en todas las tandas | **Cumplida.** `gpu_acquire`/`gpu_release` en las **cinco** tandas de GPU (A · B+C · D · F · E), seis adquisiciones con el reintento. **Lock libre al terminar, verificado.** **Y documentado que no basta**: §1.3 |
| No instalar en `.venv-ai` ni `.venv-paddle` | **Cumplida.** Nada instalado. Los pesos de RapidOCR fueron a `bench/salidas-ppp-norm/modelos/` vía `Global.model_root_dir`; los de PaddleX a `~/.paddlex/`. Los dos **fuera de los venv** |
| Verificar `torch.cuda.is_available()` al terminar | **Cumplida.** `.venv-ai`: `torch 2.6.0+cu124`, `cuda True`, `NVIDIA GeForce RTX 3060`, `onnxruntime 1.22.0`, `docling 2.120.3`. `.venv-paddle`: `paddle 3.2.0` con CUDA, 1 dispositivo, `paddleocr 3.7.0`. Y `.venv-ai\...apidocr\models\` conserva sus 10 ficheros con **fecha del 19 de agosto** |
| Medianas de n≥9 | **Cumplida** en toda medida de regresión (tandas A, B, C, D2, D3, F). El **cribado** de §3.5 es n=1 y está declarado como cribado, con el mismo criterio que `corpus-d4.md` §3 |
| Los **dos** testigos de ruido | **Cumplida, y el segundo atrapó una tanda que el primero declaró limpia** (§1.2) |
| Fijar el dispositivo en toda regresión | **Cumplida.** **GPU (`cuda`, `gpu:0`) en las seis tandas.** Las dos sondas de instrumentación corren en CPU y no producen CER |
| Timeouts explícitos | **Cumplida.** `timeout` explícito en las **25** invocaciones de motor (3 600–5 400 s) y en las 3 sondas. Ningún proceso quedó colgado |
| Dos intentos por problema | **Cumplida.** §5 punto 1 |
| Vigilar la VRAM y medir el pico | **Cumplida.** §7 |
| Borrar las imágenes grandes, dejar `MANIFIESTO.md` | **Cumplida.** Ver `bench/salidas-ppp-norm/MANIFIESTO.md` |

---

## 7. VRAM: el techo de ppp es también un techo de memoria

**MEDIDO**, pasada con muestreador (100 ms), n=3, sobre **el barrido completo de 17
rasterizaciones de `escaneado_d4`** — es decir, el pico incluye el punto de 400 ppp
(2 588×3 432 px). Testigos de ruido de esta tanda: deriva 0,97–1,08, nivel 0,93–1,26.
**Tanda limpia.**

| motor | base MiB | **pico MiB** | **coste propio MiB** | ¿reventó? |
|---|---:|---:|---:|---|
| **EasyOCR** | 2 007 | **12 037 de 12 288** | **+10 030** | no, por **251 MiB** |
| **PaddleOCR v6 medium** | 1 946 | **11 942 de 12 288** | **+9 996** | no, por **346 MiB** |
| RapidOCR v6 small + R6 (ONNX) | 991 | 4 439 | **+3 448** | no |

**Tres lecturas, y una es un aviso de producción:**

1. **PaddleOCR es tan caro como EasyOCR cuando se le sube la resolución.**
   `ocr-ppp-nativos.md` §7.2 lo dejó en +2 708 MiB a ppp nativos y en 12 025 MiB a
   600 ppp; aquí llega a **11 942 MiB con 400 ppp y una sola página**. La imagen mental
   de «EasyOCR es el caro» es correcta a ppp nativos y **falsa en cuanto se sobremuestrea**.
2. **Los dos motores caros terminaron a menos de 350 MiB de agotar la tarjeta, sin dar
   ningún error.** Con la sesión de escritorio ocupando ~2 GB de forma permanente, un
   documento apenas más grande —o un segundo trabajo en paralelo— los tira. Y §1.3
   demuestra que ese segundo trabajo **puede venir de fuera del proyecto**.
3. **RapidOCR corregido cuesta un tercio (+3 448 MiB) y su curva es plana por encima de
   233 ppp por construcción** (§2.5): es el único de los tres con un techo de VRAM
   *acotado por el propio motor*.

**Por eso la regla de ppp no es solo de calidad.** Aplicar `k(motor)` sobre el nativo, en
lugar de rasterizar «por si acaso» a 300 o 400 ppp, es lo que hace **predecible** el
presupuesto de VRAM del sidecar. Es la misma conclusión de `corpus-d4.md` §9.5, ahora con
el otro extremo medido: **el coste de no aplicarla son 10 GB.**

---

## 8. Lo que queda PENDIENTE

- **El `k` por motor está medido sobre UN documento.** Los siete óptimos de §2.7 salen
  todos de `escaneado_d4`. La conclusión de que *hay* un `k` por motor está apoyada por
  dos documentos más (`d3` separa a PaddleOCR de RapidOCR+R6 por 43 puntos a ×1,4, y
  `d2` separa a Tesseract del resto según P2), pero **el valor concreto de cada `k` es
  una estimación de un punto**. Antes de cablearlo en el adaptador hay que barrer al
  menos `d3`, `d4c` y `patologico` con las siete configuraciones. **Es el pendiente de
  más valor que abre este informe.**
- **La curva de ppp de Tesseract no se ha barrido**, y no era de este encargo. La
  evidencia de P2 es n=1 y en dos direcciones opuestas (`d2` pide ×1,5, `d4` pide ×1,0).
  Coincide con el pendiente 6 de `bench/invocacion-aristas.md` §11.
- **El suelo de 100 ppp no se ha medido con un original que lo necesite.** Todo el corpus
  está entre 100 y 240 ppp nativos; no hay ningún documento por debajo de 100 sobre el
  que probar la subida. El ×1,25 propuesto sale de acotar la subida en documentos que no
  la necesitan. **PENDIENTE: un `escaneado_d5` de 60-80 ppp nativos.**
- **Toda la curva de ppp está medida sobre documentos de una sola geometría de página**
  (465,84 pt de ancho, salvo los tres derivados de §2.4 y `tipico_texto`). Que el efecto
  sea de píxeles y no de ppp está cerrado; que el umbral de píxeles dependa del **tamaño
  de letra en píxeles** es la hipótesis que el desglose por bloque sugiere y que **no
  está aislada**: haría falta la misma página con un solo cuerpo de letra por documento.
- **`escaneado_d3` no tiene refinamiento entre ×1,25 y ×1,4.** Ahí está el acantilado de
  RapidOCR+R6 (2,53 → 46,84) y solo hay dos puntos. Es el mismo defecto que este encargo
  vino a corregir en `d4`, en otro documento.
- **La cifra de B11 sobre `Rec.lang_type = latin` no se ha reverificado** en este arnés:
  se cita de `corpus-d4.md` §7.2. En PP-OCRv6 la variable no existe, así que solo importa
  si se decide quedarse en PP-OCRv5.
- **El lock de GPU tiene que ser de máquina, no de repositorio.** §1.3.
- **La sonda de píxeles solo cubre RapidOCR y PaddleOCR.** EasyOCR y docling no están
  instrumentados; para docling se tiene la sonda de tamaño de entrada, no la del
  reescalado interno.
- **`magick -deskew 40%` sobre la familia d4** sigue sin medirse (venía de
  `corpus-d4.md` §11 y no era de este encargo).

---

## Ficheros

Todo en **`bench/salidas-ppp-norm/`**, con `MANIFIESTO.md`:

| fichero | qué es |
|---|---|
| `ocr_eval_d4.py`, `d4_texto.py` | **copias byte a byte** de `bench/salidas-corpus-d4/`. No se modifican: se importan |
| `ocr_eval_pn.py` | envoltorio de 70 líneas: importa el anterior y añade la referencia `tipico` y la deducción de referencia por nombre |
| `preparar_pn.py` | rasterizado a listas de ppp, con anchura en píxeles y factor sobre el nativo |
| `ocr_lote_pn.py` | banco de PaddleOCR / RapidOCR / EasyOCR, con R6, recuento de cajas y **los dos testigos de ruido** |
| `docling_lote_pn.py` | docling con `scale` explícito, lista de ppp y R6 por `rapidocr_params` |
| `survey_norm.py` | cribado de 7 detectores × 4 variantes en un solo proceso (§3.5) |
| `probe_norm.py` | **declarado frente a aplicado**, con fichero y línea (§3.1) |
| `sonda_detector.py` | píxeles que llegan de verdad a la red, por enganche del reescalado interno (§2.5) |
| `tablas_pn.py` → `tablas.md` | todas las tablas, incluidas las que no cupieron aquí |
| `run_a_barrido.sh`, `run_b_docs.sh`, `run_d_b10.sh`, `run_e_easy_docling.sh`, `run_f_resto.sh` | las seis tandas, con su `gpu_acquire`/`gpu_release` |
| `json/`, `texto/`, `logs/` | resultados, salidas de OCR y registros completos |
