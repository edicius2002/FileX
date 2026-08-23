# El `k` por motor, caracterizado sobre cuatro documentos

> **⚠ ETIQUETA DE COMPARABILIDAD — añadida el 23/08 por `bench/phys-multimotor.md` §6.**
> Las cifras de **Tesseract** de **§2.1, §3, §4.1, §4.3, §5, §6.1 (filas `magick`) y §6.2** — todo el eje Tesseract se midieron sobre rásteres de `magick -density N`
> **sin `-units PixelsPerInch`**, es decir con el `pHYs` a `unidad=0`. Tesseract entonces
> **se inventa la resolución** y con ella cambia su análisis de maquetación: sobre `escaneado_d4`
> con `psm 3` eso vale **33,22 puntos** (84,56 % sin declarar contra 51,34 % declarando el
> verdadero), y hasta **47,15** en el conjunto.
> 
> **Las comparaciones DENTRO de este informe se sostienen** —todas sus celdas comparten
> cabecera, igual que el criterio de `CLAUDE.md` §3 para los milisegundos—. **Lo que NO vale
> es cruzarlas con PaddleOCR, RapidOCR o EasyOCR**, que son **inmunes al `pHYs`** (0,00 puntos,
> 18 de 18 filas): sería comparar un motor mal alimentado con tres bien alimentados.
> 
> **Un `k` o un `--psm` de aquí no se transfiere sin declarar los tres: `(psm, k, pHYs)`.**

**Encargo B13 (M1).** `bench/ppp-y-normalizacion.md` §8 lo dejó escrito como *«el
pendiente de más valor que abre este informe»*: la regla de ppp que hoy está en
`CLAUDE.md` trampa 8 y en `PLAN-ORQUESTADOR.md` §5 usa un `k` **por motor**, y **los
siete valores de ese `k` salen todos de un solo documento**, `escaneado_d4`. Antes de
cablearlo en el adaptador de cada motor había que barrer al menos `escaneado_d3`,
`escaneado_d4c` y `patologico_escaneado` con las siete configuraciones.

**Máquina:** RTX 3060 12 288 MiB (driver 572.61, CUDA 12.8), 12 hilos, Windows 10,
Python 3.11.9. **Fecha:** 2026-08-22, 08:05–10:05.
**Arnés:** `bench/lib/harness.sh`, lock exclusivo en las **siete** adquisiciones de GPU
(A · B · D · E · C · G · H). Las tres de Tesseract (F, I y la sonda) son de CPU y no lo
toman.
**Salidas:** `bench/salidas-k-motor/` (+ `MANIFIESTO.md`).
**Dispositivo fijado en toda regresión: GPU (`cuda`, `gpu:0`)** salvo Tesseract, que
**no tiene GPU** y va en CPU declarado. **396 celdas, mediana de n=9, las 396
deterministas** (`det=si`: el texto es idéntico en las nueve repeticiones).
**Evaluador: `bench/salidas-corpus-d4/ocr_eval_d4.py`, copiado byte a byte** a
`bench/salidas-k-motor/ocr_eval_d4.py`, con el envoltorio `ocr_eval_km.py` (copia de
`ocr_eval_pn.py` de P1). **`bench/scripts/ocr_eval.py` no se ha tocado**, y no se
usa: es ciego a las tildes. Toda cifra va en las dos lecturas, `acentos / ascii`.

---

## 0. Veredicto, primero

La pregunta del encargo era una sola. Ésta es la respuesta, con todas las letras:

> **MEDIDO — el `k` óptimo es una propiedad del PAR (motor, documento), no del motor.**
> Repartiendo la varianza de `log2(k*)` entre sus tres fuentes sobre las 27 parejas
> discriminantes: **el motor explica el 23,2 %, el documento el 0,1 % y la
> interacción motor × documento el 76,7 %.** La interacción es justo lo que la regla
> vigente supone que no existe. Y en las **nueve** configuraciones medidas, el óptimo
> **no coincide en los cuatro documentos ni una sola vez**: fijar el motor baja la
> dispersión del óptimo de **×3,46 a ×2,07** (medias geométricas de los rangos), pero
> **no la cierra**. *(§2)*

Y la segunda mitad, que es la que decide qué se hace con la regla:

> **MEDIDO — pero eso NO tumba la regla, le cambia el fundamento.** Lo que está
> refutado no es *«hay un `k` por motor»*, es *«el `k` de `d4` es el `k` del motor»*:
> **el `k` óptimo de `escaneado_d4` es el mejor `k` fijo sobre los cuatro documentos
> solo en 3 de las 9 configuraciones.** En cambio, un `k` **ajustado sobre los cuatro
> documentos** deja un arrepentimiento de **0,34 a 2,81 puntos de CER en las 9 de 9**.
> **La diferencia entre una regla que funciona y una que no, no es el motor: es
> cuántos documentos se usaron para fijar el número.** *(§4)*

Los nueve resultados, en orden de lo que cambian:

1. **MEDIDO, y es el resultado principal — la interacción domina.** Varianza de
   `log2(k*)`: motor **23,2 %**, documento **0,1 %**, interacción **76,7 %**. *(§2.2)*
2. **MEDIDO — el óptimo no coincide en ninguna de las nueve configuraciones.** Ni
   siquiera en las dos que FileX enviaría a producción: PaddleOCR v6 medium cae en
   **×1,00** sobre `d3` y `d4c` y en **×1,25** sobre `d4`; RapidOCR v6 small + R6 cae
   en **×1,25**, **×0,75** y **×1,00** sobre los mismos tres. *(§2.1)*
3. **MEDIDO — el `k` de `d4` es el mejor `k` fijo solo en 3 de 9.** Sobrevive en
   PaddleOCR (×1,25), RapidOCR v6 small + R6 (×1,00) y Docling+R6 (×0,875). Falla en
   las otras seis. *(§4.1)*
4. **MEDIDO, y es una corrección directa a una línea de la regla vigente.**
   `ppp-y-normalizacion.md` §2.8 redondea el ×0,88 de Docling+R6 a **×1,00** «porque
   está dentro del ruido». **No lo está: ese redondeo cuesta 3,30 puntos de media y
   7,72 puntos en `escaneado_d4c`** (0,67 % → 8,39 %). *(§4.2)*
5. **MEDIDO, y es el peor caso de todos — el `k = 1,50` de Tesseract es el peor
   valor posible de los once del barrido.** Con `--psm 11` su arrepentimiento medio
   es de **176,31 puntos** frente a **2,51** del mejor `k` fijo (×0,75); con
   `--psm 3`, **4,99** frente a **0,34** (×0,875). El número venía de **P2, n=1, otro
   documento (`escaneado_d2`) y otro rasterizador**. *(§4.3)*
6. **MEDIDO — y el `--psm` de Tesseract pesa MÁS que cualquier `k`.** Sobre los
   **mismos píxeles** de `escaneado_d4`, `--psm 3` da **84,56 %** y `--psm 11` da
   **41,78 %**: **42,78 puntos por un parámetro que ni la regla ni el inventario
   mencionan**, frente a los ~19 puntos que mueve el barrido entero de `k`. *(§6.1)*
7. **MEDIDO, y cierra el pendiente 7 de `bench/invocacion-aristas.md` §11.** La
   asimetría entre *«el Tesseract externo devuelve 0 bytes en `d3`»* y *«el Tesseract
   embebido en Ghostscript alucina 165,8 %»* **tiene una causa suficiente medida: el
   modo de segmentación de página.** Sobre el mismo PNG de `d3`, `--psm 3` y `--psm 4`
   devuelven **0 bytes** y `--psm 6` y `--psm 11` devuelven **113,92 % y 188,61 %** de
   CER. Silencio y alucinación son **el mismo motor con distinto `--psm`**. *(§6.1)*
8. **MEDIDO, y es un aviso de método para todo el proyecto — el RASTERIZADOR es una
   variable oculta que vale 33 puntos.** Sobre `escaneado_d4` a 200 ppp, con
   **exactamente la misma geometría (1 294×1 716) y la misma profundidad (8 bits,
   escala de grises)**, Tesseract da **84,56 %** desde ImageMagick y **51,34 %** desde
   Ghostscript. Ese 51,34 % **reproduce el 51,15 % de P2 con 0,19 puntos de
   diferencia**: el desacuerdo entre mi columna y la suya **no era del motor, era del
   rasterizador**. Y sobre `d3` y `d4c` los dos rasterizadores dan **cifras
   idénticas**: el efecto también es del par. *(§6.2)*
9. **MEDIDO — el asignador de VRAM de PaddleOCR y de EasyOCR no devuelve un solo
   MiB.** Un folio de 4,40 Mpx dejó a PaddleOCR clavado en **11 498 MiB** y a EasyOCR
   en **11 327**, y **las nueve y las veinticuatro lecturas siguientes dieron el mismo
   número al MiB**, bloqueando incluso imágenes de 1,4 Mpx. **Reiniciar el proceso lo
   arregla; esperar, no.** *(§6.3)*

Y el control que hace comparable todo lo anterior:

> **MEDIDO — las 72 celdas de `escaneado_d4` que P1 publicó se reproducen las 72,
> exactas a la centésima**, otro día, otra tanda, otras siete configuraciones
> reconstruidas desde cero y **sin el `Global.model_root_dir` que usó P1** (`repro_p1.py`,
> `json/repro_p1.json`). Las cifras absolutas de tandas distintas no son comparables
> **en tiempo**; en **CER, con el dispositivo fijado y `det=si`, sí lo son**, y esto lo
> demuestra celda a celda.

---

## 1. Cómo se midió

### 1.1 El diseño, y por qué la rejilla es de FACTORES

`ppp-y-normalizacion.md` §2.4 dejó medido que **los ppp no son la unidad**: el mismo
JPEG empaquetado en páginas de 100/200/400 ppp da CER de 19,13 / 19,63 / 36,24 % **a
los mismos ppp** y coincide **a la centésima a los mismos píxeles** en 24 celdas. Por
eso aquí el barrido se hace en **factores sobre el raster nativo**, que es la unidad
en la que está escrito el `k`, y se registran además los ppp y los píxeles.

| | |
|---|---|
| documentos | `escaneado_d3` (100 ppp nativos), `escaneado_d4c` (200), `patologico_escaneado` (200), **`escaneado_d4` (200, el ancla)** |
| factores | ×0,50 ×0,625 ×0,75 ×0,875 **×1,00** ×1,125 ×1,25 ×1,40 ×1,50 ×1,60 ×1,80 — **once** |
| configuraciones | las **siete** de `ppp-y-normalizacion.md` §2.7 + **dos de Tesseract** (`--psm 3` y `--psm 11`) |
| celdas | **396**, mediana de **n=9**, **396 deterministas** |

**`escaneado_d4` se volvió a medir entero** en vez de citar a P1, para que las cuatro
columnas salgan de la misma tanda y el contraste no dependa de comparar entre tandas.
El precio son 44 celdas de más; el retorno es el control de reproducción de §1.4.

**No se sobremuestreó nada por error** (`CLAUDE.md` trampa 6): los ppp nativos se leen
de la imagen incrustada de cada PDF con `pypdfium2` y el factor se aplica sobre ellos.
`escaneado_d3` tiene **100** ppp nativos y su ×1,00 son **100 ppp**, no 200.

### 1.2 Los arneses: copiados, y qué se les cambió

| original (intacto) | copia usada aquí | qué cambia |
|---|---|---|
| `bench/scripts/ocr_eval.py` | — **no se usa** | es ciego a las tildes |
| `bench/salidas-corpus-d4/ocr_eval_d4.py` | `salidas-k-motor/ocr_eval_d4.py` (**copia byte a byte**) | **es el fichero que produjo las cifras de `d4` y de P1, y por tanto el único comparable con ellas** |
| `bench/salidas-corpus-d4/d4_texto.py` | ídem, copia byte a byte | fuente única de verdad del texto |
| `bench/salidas-ppp-norm/ocr_eval_pn.py` | `ocr_eval_km.py` (copia byte a byte) | envoltorio que importa el anterior |
| `bench/salidas-ppp-norm/preparar_pn.py` | `preparar_km.py` | rejilla de **factores**, Mpx y **tope de lado en píxeles** |
| `bench/salidas-ppp-norm/ocr_lote_pn.py` | `ocr_lote_km.py` | **testigo con tope** + **guardia de VRAM** |
| `bench/salidas-ppp-norm/docling_lote_pn.py` | `docling_lote_km.py` | ídem + modo `f<factores>` |
| — | `tess_lote_km.py` | nuevo: Tesseract nativo, CPU |

**Cuál es el evaluador, con todas las letras: `bench/salidas-corpus-d4/ocr_eval_d4.py`,
copiado sin un solo cambio** (`sha256` en el `MANIFIESTO.md`). Es la **primera** de las
dos copias acentuadas que existían y la única cuyas cifras son comparables con las de
`corpus-d4.md` y `ppp-y-normalizacion.md`. La otra
(`bench/salidas-verificador-gs/ocr_eval_tildes.py`) **no se ha usado**.

Los dos cambios del arnés están en `parche_km.py`, que los aplica sobre las copias y
los deja escritos:

1. **Testigo de proceso CON TOPE de 20 s.** `CLAUDE.md` §3: *«un testigo que puede
   tumbar la medición no es un testigo»*. El de P1 lanza cinco `ffprobe` con
   `timeout=60` cada uno, es decir hasta **300 s por invocación** — que es exactamente
   lo que le pasó a P3 (×94,6). El de aquí lleva un presupuesto total de 20 s,
   devuelve el tope y marca `testigo_topado`. **No se agotó ni una vez.**
2. **Guardia de VRAM por imagen**, una consulta por celda y no por repetición.
   Disparó, y lo que descubrió está en §6.3.

### 1.3 Los dos testigos de ruido

Cada tanda registra los dos, al principio y al final: bucle monohilo (**deriva dentro**
de la tanda) y mediana de cinco `ffprobe -version` (**nivel** de carga de la máquina,
calibración en reposo del proyecto 26,65 ms).

| tanda | configuración | deriva (monohilo) | nivel (proceso) | veredicto |
|---|---|---:|---:|---|
| A | PaddleOCR v6 medium | 1,07 | ×1,26 | limpia |
| A | RapidOCR v6 small + R6 | 0,96 | **×2,02** | **dudosa** |
| A | RapidOCR v6 small def. | 0,96 | ×1,37 | limpia |
| A | RapidOCR v5 mobile def. | 1,07 | ×1,19 | limpia |
| B+H | EasyOCR | 1,24 | ×1,21 | limpia |
| C | Docling defecto | 1,28 | **×2,40** | **dudosa** |
| C | Docling + R6 | 0,89 | ×1,26 | limpia |
| F | Tesseract `--psm 3` | 0,91 | ×1,31 | limpia |
| I | Tesseract `--psm 11` | 0,79 | ×1,13 | limpia |

**Dos tandas salen dudosas por el testigo de proceso (×2,02 y ×2,40) con el monohilo
diciendo 0,96 y 1,28.** Es el mismo patrón que ya documentaron `verificador-ghostscript.md`
§4 y `ppp-y-normalizacion.md` §1.2, reproducido aquí sin buscarlo: **el monohilo no ve
la contención multinúcleo.** Hay tres agentes más escribiendo código en este
repositorio ahora mismo, y eso es carga de CPU.

**Consecuencia, separada y honesta:** los **CER no están afectados** —salieron
deterministas en las 396 celdas y el dispositivo está fijado; una máquina cargada
cambia el tiempo, no el resultado de una convolución— y **los tiempos de las tandas A
y C no se usan para ninguna conclusión de este informe.** Aquí no hacía falta ninguna:
**el objeto de medida es el CER**.

Todas las tandas salen etiquetadas `SUCIA` por el criterio de utilización de GPU del
arnés (picos del 36 al 50 % con la sesión remota activa). Es **estructural**, como dice
`CLAUDE.md` §3.

**Y el lock:** libre al empezar y al terminar, comprobado. Antes de la primera tanda se
miraron los PID (`CLAUDE.md` §1): **2 728 MiB de base, todos de escritorio** —
`explorer.exe`, Steam, Epic, iCUE, NVIDIA Overlay—, **ningún `python.exe` de otro
proyecto**. Esta vez no hubo sesión ajena.

### 1.4 El control de reproducción: 72 de 72

`repro_p1.py` compara mis celdas de `escaneado_d4` con las que P1 publicó en
`ppp-y-normalizacion.md` §2.1 y §2.1b, para siete configuraciones:

| configuración | celdas comprobadas | idénticas |
|---|---:|---:|
| PaddleOCR v6 medium | 11 | **11** |
| RapidOCR v5 mobile (defecto) | 11 | **11** |
| RapidOCR v6 small (defecto) | 11 | **11** |
| RapidOCR v6 small + R6 | 11 | **11** |
| Docling+RapidOCR torch (defecto) | 9 | **9** |
| Docling+RapidOCR torch + R6 | 9 | **9** |
| EasyOCR | 10 | **10** |
| **total** | **72** | **72** |

**Cero diferencias, a la centésima.** Y con una diferencia de entorno que refuerza el
control: P1 puso los pesos de RapidOCR en `bench/salidas-ppp-norm/modelos/` vía
`Global.model_root_dir`; ese directorio **ya no existe** y aquí se usaron los que
están en `.venv-ai/Lib/site-packages/rapidocr/models/` (fecha del 19 de agosto), que
son los mismos que usó `corpus-d4.md`. **No se instaló nada en ningún venv**; RapidOCR
registró `File exists and is valid` para los cuatro modelos y no descargó ninguno.

---

## 2. La respuesta: el `k` es del par

### 2.1 Dónde cae el óptimo de cada configuración en cada documento

**MEDIDO**, n=9. Entre paréntesis, el mejor CER acentos de ese barrido.
**‡** = el óptimo no es informativo porque el motor no lee el documento (mejor
CER ≥ 50 %: elegir el mínimo entre 74,68 y 75,95 es elegir ruido).
**†** = curva plana o en el suelo (≥5 factores empatados).

| configuración | `d3` | `d4c` | `patológico` | `d4` | ¿coincide? |
|---|---|---|---|---|---|
| PaddleOCR v6 medium | **×1,00** (2,53) | **×1,00** (0,67) | todos (0,00)† | **×1,25** (13,09) | **NO** |
| RapidOCR v6 small + R6 | **×1,25** (2,53) | ×0,75/×1,125/×1,50 (0,84) | todos (0,00)† | **×1,00** (18,62) | **NO** |
| RapidOCR v6 small (defecto) | ×1,80 (49,37) | ×1,25 (24,33) | todos (0,00)† | ×1,25 (32,72) | **NO** |
| RapidOCR v5 mobile (defecto) | ×1,40 (74,68)‡ | ×1,50 (6,21) | ×1,125/×1,25 (0,00) | ×0,50 (40,44) | **NO** |
| EasyOCR (CRAFT + latin_g2) | ×0,875 (49,37) | ×1,00 (15,10) | todos (0,00)† | ×1,80 (58,39)‡ | **NO** |
| Docling+RapidOCR torch (defecto) | ×1,80 (40,51) | ×0,50 (18,62) | todos (0,00)† | ×1,125/×1,50/×1,80 (32,72) | **NO** |
| Docling+RapidOCR torch + R6 | ×0,50/×0,625 (1,27) | ×0,75 (0,50) | todos (0,00)† | ×0,875 (18,12) | **NO** |
| Tesseract 5.5.0 `--psm 3` | todos (100,00)‡† | ×1,40 (1,68) | todos (0,00)† | ×0,875 (72,48)‡ | **NO** |
| Tesseract 5.5.0 `--psm 11` | ×0,75 (68,35)‡ | ×1,60 (2,18) | todos (0,00)† | ×1,00 (41,78) | **NO** |

**Cero de nueve.** Y no es un artefacto de las configuraciones rotas: **las dos que
FileX enviaría a producción tampoco coinciden.** PaddleOCR pide ×1,00 en dos
documentos y ×1,25 en el tercero; RapidOCR+R6 pide ×1,25, ×0,75 y ×1,00 en tres
documentos distintos.

**Dispersión del óptimo, por eje** (excluido `patológico`, que no discrimina):

| eje | rangos observados | **media geométrica** |
|---|---|---:|
| **fijando el motor**, entre documentos | ×1,25 a ×3,60 | **×2,07** |
| **fijando el documento**, entre motores | ×3,20 a ×3,60 | **×3,46** |

**Fijar el motor reduce la dispersión de ×3,46 a ×2,07. No la cierra.** Queda un
factor 2 de indeterminación dentro de un mismo motor, que es exactamente lo que la
regla vigente da por inexistente.

### 2.2 La cifra que contesta la pregunta

Repartiendo la varianza de `log2(k*)` de las **27 parejas discriminantes** (9
configuraciones × 3 documentos) entre el efecto del motor (medias por fila), el del
documento (medias por columna) y el residuo:

| fuente | suma de cuadrados | **% de la varianza** |
|---|---:|---:|
| **motor** | 1,969 | **23,2 %** |
| **documento** | 0,010 | **0,1 %** |
| **interacción (motor × documento)** | 6,517 | **76,7 %** |
| total | 8,496 | 100 % |

**Tres lecturas, y las tres importan:**

1. **La interacción domina: 76,7 %.** El `k` óptimo **no es del motor ni del
   documento: es del par.** Y la interacción es precisamente el término que
   `ppp_ocr = nativos × k(motor)` supone nulo.
2. **El motor explica el 23,2 %, que no es cero.** *«Hay un `k` por motor»* **sigue en
   pie como afirmación débil**: fijar el motor explica casi una cuarta parte de la
   varianza y baja la dispersión a la mitad. Lo que no puede es determinar el valor.
3. **El documento, por sí solo, explica el 0,1 %.** Esto refuta de paso la hipótesis
   cómoda de repuesto: *«los documentos difíciles piden más píxeles»*. **No hay un
   `k` por documento tampoco.** No existe ninguna descomposición de un factor.

### 2.3 Por qué tenía que salir así — el mecanismo, ya medido

No es un resultado sorprendente en cuanto se junta con lo que ya está medido.
`ppp-y-normalizacion.md` §2.3 dejó escrito que *«el techo de ppp no es una propiedad de
la resolución: es el margen que le queda al motor»*, y §2.5 sondeó que cada motor lleva
su propio reescalado interno cableado (RapidOCR `min 736 / max 2000`; PaddleOCR
`min 64 / sin tope`). **Las dos cosas a la vez producen exactamente una interacción:**
el reescalado interno es del **motor**, y el margen es del **par**. Un `k` es el
producto de las dos.

Se ve en las tablas sin necesidad de estadística. `patologico_escaneado` da **0,00 %
en las 11 celdas de ocho de las nueve configuraciones**: donde el motor tiene margen,
el `k` **no existe** —cualquier valor de ×0,50 a ×1,80 da lo mismo—. Y en
`escaneado_d3`, donde RapidOCR+R6 está justo en el filo, el mismo motor pasa de
**2,53 % a ×1,25** a **46,84 % a ×1,40** y a **75,95 % a ×1,60**. **El `k` solo tiene
valor donde el par está cerca de fallar, y ahí es donde el documento manda.**

---

## 3. El barrido, en las cuatro columnas que importan

Las nueve tablas completas están en `bench/salidas-k-motor/tablas.md` §1. Aquí, las dos
configuraciones que FileX enviaría a producción y la que más se cita, en CER acentos.

**PaddleOCR v6 medium** (`c` = renglones devueltos por el detector)

| factor | `d3` (3 renglones) | `d4c` (12) | `patológico` (3) | `d4` (12) |
|---:|---:|---:|---:|---:|
| ×0,50 | 10,13 · c3 | 0,84 · c12 | **0,00** | 19,13 · c12 |
| ×0,625 | 10,13 · c3 | 1,17 · c12 | **0,00** | **16,95** · c12 |
| ×0,75 | 11,39 · c3 | 1,34 · c12 | **0,00** | 17,11 · c12 |
| ×0,875 | 3,80 · c3 | 0,84 · c12 | **0,00** | 21,64 · c13 |
| **×1,00** | **2,53** · c3 | **0,67** · c12 | **0,00** | 19,30 · c12 |
| ×1,125 | 7,59 · c3 | 1,01 · c12 | **0,00** | 20,97 · c12 |
| **×1,25** | 5,06 · c3 | 0,84 · c12 | **0,00** | **13,09** · c12 |
| ×1,40 | 3,80 · c3 | 1,17 · c12 | **0,00** | **36,24** · c8 |
| ×1,50 | 31,65 · c2 | 0,84 · c12 | **0,00** | 25,17 · c11 |
| ×1,60 | **75,95** · c1 | 1,01 · c12 | **0,00** | 36,24 · c8 |
| ×1,80 | 75,95 · c1 | 1,01 · c12 | **0,00** | 36,41 · c8 |

**RapidOCR v6 small + R6**

| factor | `d3` | `d4c` | `patológico` | `d4` |
|---:|---:|---:|---:|---:|
| ×0,50 | 35,44 · c3 | 10,07 · c11 | **0,00** | 30,70 · c9 |
| ×0,625 | 13,92 · c3 | 10,57 · c11 | **0,00** | 26,68 · c11 |
| ×0,75 | 22,78 · c3 | **0,84** · c12 | **0,00** | 18,96 · c11 |
| ×0,875 | 11,39 · c3 | 1,01 · c12 | **0,00** | 21,31 · c12 |
| **×1,00** | 3,80 · c3 | 1,17 · c12 | **0,00** | **18,62** · c12 |
| ×1,125 | **40,51** · c2 | **0,84** · c12 | **0,00** | 23,32 · c11 |
| ×1,25 | **2,53** · c3 | 1,01 · c12 | **0,00** | 24,50 · c10 |
| ×1,40 | **46,84** · c3 | 9,56 · c11 | **0,00** | 28,86 · c10 |
| ×1,50 | 35,44 · c2 | **0,84** · c12 | **0,00** | 30,20 · c9 |
| ×1,60 | 75,95 · c1 | 9,23 · c11 | **0,00** | 23,83 · c12 |
| ×1,80 | 45,57 · c2 | 9,56 · c11 | **0,00** | 29,19 · c10 |

**Tesseract 5.5.0 (`--psm 3`, el defecto, y `--psm 11`)** — la única columna nueva del
proyecto, y la que más se citaba con menos evidencia.

| factor | `d3` psm3 | `d3` psm11 | `d4c` psm3 | `d4c` psm11 | `d4` psm3 | `d4` psm11 |
|---:|---:|---:|---:|---:|---:|---:|
| ×0,50 | 100,00 | 73,42 | 23,99 | 15,60 | 79,03 | 47,48 |
| ×0,625 | 100,00 | 69,62 | 4,53 | 8,39 | 85,40 | 56,38 |
| ×0,75 | 100,00 | **68,35** | 3,36 | 4,36 | 87,25 | 49,66 |
| ×0,875 | 100,00 | 93,67 | 3,02 | 3,86 | **72,48** | 46,48 |
| ×1,00 | 100,00 | 188,61 | 1,85 | 2,68 | 84,56 | **41,78** |
| ×1,125 | 100,00 | 303,80 | 2,35 | 3,02 | 89,09 | 49,33 |
| ×1,25 | 100,00 | 210,13 | 2,18 | 5,03 | 85,57 | 45,30 |
| ×1,40 | 100,00 | 541,77 | **1,68** | 7,72 | 89,26 | 47,82 |
| **×1,50** | 100,00 | **756,96** | 2,35 | 8,72 | **91,78** | 51,85 |
| ×1,60 | 100,00 | 882,28 | 3,02 | **2,18** | 86,58 | 47,82 |
| ×1,80 | 100,00 | 1 194,94 | 2,85 | 5,54 | 88,93 | 56,88 |

**Y hay que decir lo que se ve:** las cifras de más de 100 % **no son un error de la
tabla**. Son alucinación: con `--psm 11` sobre un `d3` sobremuestreado, Tesseract
devuelve **más caracteres equivocados que caracteres tiene la referencia**, hasta
**1 194,94 %** a ×1,80. **La curva de `k` de Tesseract en `d3` no tiene un óptimo: tiene
una rampa hacia la alucinación**, y el `k = 1,50` cablado hoy está a mitad de rampa.

---

## 4. Lo que cuesta equivocarse de `k`

La tabla de óptimos se puede leer torcida: que dos óptimos no coincidan no dice cuánto
cuesta la equivocación. La medida que lo dice es el **arrepentimiento**:

```
regret(motor, k) = media_documentos[ CER(motor, doc, k) - min_f CER(motor, doc, f) ]
```

Es decir, **cuántos puntos de CER se pierden por usar un `k` fijo en vez de acertar el
mejor `k` de cada documento**.

### 4.1 La tabla central del encargo

**MEDIDO**, n=9, cuatro documentos. `k*` de `d4` es lo que midió P1 (el argmin sobre
`escaneado_d4`); `k` de la regla es lo que `ppp-y-normalizacion.md` §2.8 y `CLAUDE.md`
trampa 8 **cablean de verdad**, que no siempre es lo mismo.

| configuración | mejor `k` fijo | regret medio | regret máx | `k*` de `d4` | su regret | `k` de la regla | su regret | regret de ×1,00 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PaddleOCR v6 medium | **×1,25** | **0,67** | 2,53 | ×1,25 | **0,67** ✅ | ×1,25 | **0,67** ✅ | 1,55 |
| RapidOCR v6 small + R6 | **×1,00** | **0,40** | 1,27 | ×1,00 | **0,40** ✅ | ×1,00 | **0,40** ✅ | 0,40 |
| Docling+RapidOCR torch + R6 | **×0,875** | **0,36** | 1,26 | ×0,875 | **0,36** ✅ | ×1,00 | **3,30** ❌ | 3,30 |
| Tesseract `--psm 3` | **×0,875** | **0,34** | 1,34 | ×1,50 | **4,99** ❌ | ×1,50 | **4,99** ❌ | 3,06 |
| RapidOCR v5 mobile (defecto) | **×1,50** | **0,93** | 1,27 | ×0,50 | **3,40** ❌ | — | — | 3,63 |
| Docling+RapidOCR torch (defecto) | **×1,80** | **1,17** | 4,70 | ×1,60 | **3,46** ❌ | — | — | 11,00 |
| EasyOCR | **×1,00** | **2,02** | 5,06 | ×1,80 | **3,18** ❌ | ×1,00 | **2,02** ✅ | 2,02 |
| Tesseract `--psm 11` | **×0,75** | **2,51** | 7,88 | ×1,50 | **176,31** ❌ | ×1,50 | **176,31** ❌ | 30,19 |
| RapidOCR v6 small (defecto) | **×1,80** | **2,81** | 7,05 | ×1,25 | **6,65** ❌ | — | — | 8,95 |

**Cuatro conclusiones, en orden de consecuencias:**

1. **El `k` de `d4` es el mejor `k` fijo en 3 de 9.** PaddleOCR, RapidOCR v6 small + R6
   y Docling+R6 sobreviven; las otras seis no. **La regla vigente acierta en un tercio
   de los casos que ella misma cubre.**
2. **Pero un `k` fijo ajustado sobre los cuatro documentos funciona en las 9 de 9**,
   con arrepentimientos de **0,34 a 2,81 puntos**. Excluyendo `patológico`, que aporta
   0,00 a todo, el rango sube a **0,45 – 3,75** — sigue siendo pequeño.
3. **Por tanto: lo refutado no es la forma de la regla, es la calidad del ajuste.**
   `ppp_ocr = nativos × k(motor)` **sigue siendo una aproximación operativa
   razonable**; lo que no es defendible es fijar `k` con un documento. **Y el propio
   P1 lo escribió como pendiente: éste es el informe que le da la razón.**
4. **Y hay un aviso escondido en la última columna.** `k = 1,00` para todos los motores
   —es decir, **no tener regla**— da arrepentimientos de 0,40 a 30,19. **Para
   PaddleOCR y RapidOCR+R6 la regla compra 0,88 y 0,00 puntos**; para Docling por
   defecto compra **9,83** y para Tesseract `--psm 11`, **27,68**. **El `k` es
   irrelevante en los motores que ya funcionan y decisivo en los que no** — que es
   exactamente lo que predice §2.3.

### 4.2 La corrección concreta a una línea de la regla vigente

`ppp-y-normalizacion.md` §2.8 escribe, en el bloque de código que define la regla:

```
#     Docling+RapidOCR torch + R6 .... k = 1,00   (el 0,88 medido esta dentro del ruido)
```

**MEDIDO: no está dentro del ruido.**

| documento | `k = 0,875` (lo medido) | `k = 1,00` (lo cableado) | coste del redondeo |
|---|---:|---:|---:|
| `escaneado_d3` | 2,53 | 5,06 | **+2,53** |
| `escaneado_d4c` | **0,67** | **8,39** | **+7,72** |
| `patologico_escaneado` | 0,00 | 0,00 | 0,00 |
| `escaneado_d4` | 18,12 | 19,63 | +1,51 |
| **media** | | | **+3,30** |

**Redondear ×0,875 a ×1,00 multiplica por 12,5 el CER de `escaneado_d4c`.** No es una
diferencia de ruido: es la diferencia entre leer el documento y no leerlo.

### 4.3 Tesseract: el `k` peor apoyado del proyecto era también el peor valor

`CLAUDE.md` trampa 8 dice **«×1,50 Tesseract (n=1, P2)»**. Ese ×1,50 sale de
`bench/invocacion-aristas.md` §9: **un punto, sobre `escaneado_d2`, con Tesseract en
contenedor y rasterizando con Ghostscript**. Barrido sobre cuatro documentos y once
factores:

| `--psm` | mejor `k` fijo | su regret | `k = 1,50` | su regret | dónde duele |
|---|---:|---:|---:|---:|---|
| `3` (defecto) | **×0,875** | **0,34** | ×1,50 | **4,99** | `d4`: 72,48 → **91,78** (+19,30) |
| `11` | **×0,75** | **2,51** | ×1,50 | **176,31** | `d3`: 68,35 → **756,96** (+688,61) |

**Con `--psm 11`, ×1,50 es literalmente el peor de los once factores del barrido.**
Y con `--psm 3` también está entre los peores.

**Matiz obligatorio, y no es menor:** mi Tesseract es el **nativo de Windows**
(`C:\Program Files\Tesseract-OCR`, v5.5.0.20241111, leptonica 1.85.0) con los datos de
idioma de `C:\Program Files\PDFgear\tessdata`, y **rasterizo con ImageMagick**; P2 usó
el de un contenedor Debian con `tesseract-ocr-spa` y **rasterizó con Ghostscript**.
§6.2 mide que esa segunda diferencia vale **33 puntos** en `d4`. **Aun así, el
resultado se sostiene**: la comparación de `k` es **interna a mi tanda**, con el mismo
binario, los mismos datos de idioma y las mismas imágenes en las 44 celdas.

---

## 5. La regla propuesta, y dónde vive

**Lo que NO cambia** (y conviene decirlo primero, porque es la mayor parte):

- **La unidad sigue siendo un FACTOR sobre el raster nativo, nunca un número de ppp.**
  Nada de este barrido toca esa conclusión; al contrario, la usa.
- **La elección sigue viviendo en el ADAPTADOR DEL MOTOR, no en el orquestador.** El
  motor explica el 23,2 % de la varianza; el orquestador no explica nada que el
  adaptador no pueda ver.
- **El suelo de 100 ppp y el techo de coste por el tope interno del motor** siguen como
  los dejó P1. Este encargo no los midió.

**Lo que cambia:**

```
# R1 revisada por B13 — la eleccion de ppp sigue siendo DEL ADAPTADOR DEL MOTOR.
#
# Lo que calcula el ORQUESTADOR y le pasa al adaptador:
ppp_nativos = ancho_imagen_px / (ancho_pagina_pt / 72)    # o None si no hay imagen
#
# Lo que decide el ADAPTADOR:
ppp_ocr = min(max(ppp_nativos, 100), ppp_nativos * 1.25) * k_motor
#
#   k AJUSTADO SOBRE CUATRO DOCUMENTOS (bench/k-por-motor.md §4.1), con su
#   arrepentimiento medio declarado. El `k` NO es el optimo de ningun documento:
#   es el que menos se equivoca en los cuatro. Los cuatro documentos son
#   escaneado_d3, escaneado_d4c, patologico_escaneado y escaneado_d4.
K_MOTOR = {
    "paddleocr_v6_medium":   (1.25,  0.67),   # antes 1,25 — SIN CAMBIO
    "rapidocr_v6_small_R6":  (1.00,  0.40),   # antes 1,00 — SIN CAMBIO
    "docling_rapidocr_R6":   (0.875, 0.36),   # antes 1,00 — CAMBIA: el redondeo
                                              #   costaba 7,72 puntos en d4c
    "easyocr":               (1.00,  2.02),   # antes 1,00 — SIN CAMBIO
                                              #   (el x1,80 del argmin de d4 es PEOR)
    "tesseract_psm3":        (0.875, 0.34),   # antes 1,50 — CAMBIA, y mucho
    "tesseract_psm11":       (0.75,  2.51),   # antes 1,50 — CAMBIA, y mucho
}
#
#   REGLA NUEVA, y es la que sale de este encargo:
#   un `k` medido sobre UN documento NO se cablea. La varianza de log2(k*) es
#   76,7 % de INTERACCION motor x documento: el optimo de un documento no predice
#   el de otro. Un `k` nuevo exige >= 4 documentos, y se publica con su
#   arrepentimiento medio y maximo, no con el CER del documento donde se midio.
#
#   Y el `k` NO es el parametro dominante de un adaptador. En Tesseract, el `--psm`
#   mueve 42,78 puntos sobre los mismos pixeles y el RASTERIZADOR mueve 33,22:
#   los dos pesan mas que el barrido entero de `k` (19,30). Un adaptador que fija
#   `k` y deja `--psm` y el rasterizador al azar esta optimizando lo pequeno.
```

| | regla vigente (P1) | regla propuesta | apoyo |
|---|---|---|---|
| forma | `nativos × k(motor)` | **igual** | §2.2: el motor explica el 23,2 %, no cero |
| dónde vive | adaptador del motor | **igual** | ídem |
| cómo se fija `k` | **argmin sobre 1 documento** | **mínimo arrepentimiento sobre ≥4** | §4.1: el argmin de `d4` acierta en 3 de 9 |
| qué se publica con `k` | el CER de `d4` | **el arrepentimiento medio y máximo** | §4.1 |
| `k` de Docling+R6 | 1,00 | **0,875** | §4.2: +7,72 puntos en `d4c` |
| `k` de Tesseract | 1,50 (n=1) | **0,875 (`psm 3`) / 0,75 (`psm 11`)** | §4.3: ×1,50 es el peor de once |
| lo que el adaptador fija además de `k` | — | **`--psm` y el rasterizador, explícitos** | §6.1, §6.2 |

**Y la frase que resume el cambio de fundamento:** *el `k` no es una constante del
motor que se descubre midiendo un documento; es un compromiso sobre una población de
documentos, y hay que publicarlo con el error que comete, igual que cualquier otro
ajuste.*

---

## 6. Tres hallazgos colaterales que valen más que el `k`

### 6.1 El `--psm` de Tesseract pesa más que el `k`, y explica una asimetría abierta

**MEDIDO** (`sonda_tess.py`, n=1, CPU, diagnóstico). Sobre **el mismo PNG**, a ppp
nativos:

| documento | rasterizador | `--psm 3` | `--psm 4` | `--psm 6` | `--psm 11` |
|---|---|---:|---:|---:|---:|
| `escaneado_d4` | magick | 84,56 (107 B) | 84,73 | 55,70 | **41,78** |
| `escaneado_d4` | ghostscript | **51,34** (359 B) | 62,08 | 55,70 | **40,60** |
| `escaneado_d3` | magick | **100,00 (0 B)** | **100,00 (0 B)** | **113,92** | **188,61** |
| `escaneado_d3` | ghostscript | **100,00 (0 B)** | **100,00 (0 B)** | **113,92** | **183,54** |
| `escaneado_d4c` | magick | 1,85 | 1,85 | 6,54 | 2,68 |
| `escaneado_d4c` | ghostscript | 1,85 | 1,85 | 6,54 | 2,68 |

**Dos cosas, y la segunda cierra un pendiente ajeno:**

1. **Sobre `d4`, `--psm` mueve 42,78 puntos** (84,56 → 41,78) **con los mismos
   píxeles**. El barrido entero de `k` sobre ese mismo documento mueve **19,30**
   (91,78 → 72,48). **Se estaba afinando el parámetro pequeño.**
2. **`bench/invocacion-aristas.md` §11 pendiente 7 pregunta por qué el Tesseract
   externo devuelve 0 bytes en `d3` mientras el embebido en Ghostscript alucina
   (165,8 %, `verificador-ghostscript.md`).** Aquí está **una causa suficiente,
   medida**: sobre el mismo fichero, `--psm 3`/`4` dan **0 bytes** y `--psm 6`/`11` dan
   **113,92 % y 188,61 %**. **Silencio y alucinación son el mismo motor con distinto
   modo de segmentación de página.** No es prueba de que Ghostscript use `psm 6` —eso
   sigue **PENDIENTE**—, pero deja de ser un misterio: el parámetro que produce las dos
   conductas está identificado y es uno.

**Y la consecuencia de diseño:** `--psm` **no puede quedar al defecto**. Es el mismo
argumento que `OcrOptions.scale` (`ppp-y-normalizacion.md` §2.8): *un parámetro que
nadie eligió no es una defensa*. Con el matiz medido que ya se conoce: **`--psm 11` es
mejor en `d4` y catastrófico en `d3`** — o sea, **también es del par**.

### 6.2 El rasterizador es una variable oculta que vale 33 puntos

Misma tabla. Sobre `escaneado_d4` a 200 ppp, con **`magick identify` devolviendo
`1294x1716 8 Grayscale` para los dos ficheros**:

| rasterizador | `--psm 3` | bytes devueltos |
|---|---:|---:|
| ImageMagick (`-colorspace Gray -alpha remove -flatten`) | **84,56 %** | 107 |
| Ghostscript (`-sDEVICE=pnggray -r200`) | **51,34 %** | 359 |

**33,22 puntos de diferencia con la misma geometría, la misma profundidad y el mismo
espacio de color.** Y el 51,34 % **reproduce el 51,15 % que P2 publicó** con 0,19
puntos de diferencia — es decir, **el desacuerdo entre mi columna de Tesseract y la de
P2 no era del motor: era del rasterizador**, y queda explicado.

**Pero el efecto también es del par**: sobre `escaneado_d3` y `escaneado_d4c` los dos
rasterizadores dan **cifras idénticas en los cuatro `--psm`**. **Ocho celdas idénticas
y cuatro con 33 puntos de diferencia.**

**Consecuencia:** el rasterizador **forma parte del contrato del adaptador de OCR**, no
es un detalle de implementación. Una tabla de `k` medida con un rasterizador **no es
transferible** a un adaptador que use otro. **Esto invalida transferir cualquier `k`
entre informes sin declarar el rasterizador** — incluido el ×1,50 de Tesseract, que
venía de una medida con Ghostscript.

### 6.3 El asignador de VRAM no devuelve nada, y un folio grande envenena el lote

La guardia de VRAM que se añadió al arnés (§1.2) disparó, y lo que registró es un aviso
de producción:

| motor | dónde se plantó | lecturas posteriores | celdas bloqueadas |
|---|---:|---|---:|
| PaddleOCR v6 medium | **11 498 MiB** tras un folio de 4,40 Mpx (×1,40) | **9 lecturas, las 9 con el mismo número al MiB** | 9 |
| EasyOCR | **11 327 MiB** tras un folio de 1,77 Mpx (×0,875) | **24 lecturas, las 24 con el mismo número al MiB** | 24 |

**Ni un solo MiB devuelto en 24 muestras repartidas a lo largo de minutos.** Entre las
celdas bloqueadas había imágenes de **1,4 Mpx**, que caben quince veces.

**La solución medida: reiniciar el proceso.** Las tandas D, E y H repitieron las 33
celdas **con un proceso por factor** y salieron **todas, sin una sola omisión** y con
la VRAM volviendo a ~2 800 MiB entre procesos.

**Regla que sale de aquí, y no estaba en el plan:** **el sidecar de OCR no puede ser un
proceso de vida larga que reciba documentos de tamaño arbitrario.** O procesa en orden
ascendente de tamaño, o presupuesta la VRAM por lote, o **recicla el proceso**. Con la
base de escritorio de esta máquina (2 728–2 924 MiB), **un folio de 4,4 Mpx deja el
proceso inservible para todo lo que venga detrás**. Es el complemento operativo del
aviso de `ppp-y-normalizacion.md` §7 (*«terminaron a menos de 350 MiB de agotar la
tarjeta, sin dar ningún error»*): **no es solo que casi reviente, es que no se
recupera**.

---

## 7. Lo que falló, con el error exacto

1. **La guardia de VRAM bloqueó 33 celdas de 396** (9 de PaddleOCR, 24 de EasyOCR).
   Error exacto: `OMITIDO por VRAM: 11498 > 11300 MiB` y `11327 > 11300`. **No era un
   fallo del arnés sino un hallazgo** (§6.3). **Se reintentó una vez** con un proceso
   por factor y el tope subido a 11 900 —el margen que P1 midió sin error— y **entraron
   las 33**. Regla de los dos intentos: consumido uno.
2. **Caí en la trampa 19 de `CLAUDE.md`** («los heredocs de shell se comen los
   backslashes»). Un `python - <<'PY'` que parcheaba `tablas_km.py` convirtió `\n` en
   saltos de línea reales y dejó el fichero con
   `SyntaxError: unterminated string literal (detected at line 345)`. Se arregló
   editando el fichero directamente. **La trampa está escrita y aun así se pisa: el
   aviso debería decir también «no generes CÓDIGO Python con heredocs», no solo JSON.**
3. **`patologico_escaneado` no sirve para caracterizar el `k`, y era uno de los tres
   documentos que pedía el encargo.** Da **0,00 % en las once celdas de ocho de las
   nueve configuraciones**: 88 celdas a cero. Como control nulo es útil —confirma que
   donde el motor tiene margen el `k` no existe— pero **no aporta ni un bit al valor
   del `k`**, y hubo que excluirlo de §2.2 y de §5 de `tablas.md` para que las medias
   no salieran diluidas. **Elegir documentos para medir `k` exige que estén en la zona
   de degradación.**
4. **`escaneado_d3` y `patologico_escaneado` cuantizan a 1,27 puntos por carácter**
   (referencia «legado», 79 caracteres; `CLAUDE.md` trampa 9). `escaneado_d4` y
   `escaneado_d4c` cuantizan a **0,17** (596 caracteres). **En `d3` no se puede
   distinguir el óptimo fino entre valores empatados**; los saltos grandes (2,53 →
   46,84 → 75,95) sí son reales. Está declarado en cada tabla y en `tablas.md` §4.
5. **Los tiempos de las tandas A y C no son utilizables** (testigo de proceso a ×2,02
   y ×2,40 con el monohilo diciendo «sin deriva»). No se usan: el objeto de medida es
   el CER, que salió determinista en las 396 celdas.
6. **No se midió la VRAM con muestreador.** Las nueve tandas fueron con
   `SIN_MUESTREO=1` porque el muestreador infla las medianas un 30-60 %; los picos que
   se reportan en §6.3 son los de la guardia, no los de un muestreo a 100 ms. **Los
   picos absolutos por motor siguen siendo los de `ppp-y-normalizacion.md` §7.**

---

## 8. Reglas del encargo, cumplidas

| regla | estado |
|---|---|
| Escribir **solo** en `bench/k-por-motor.md` y `bench/salidas-k-motor/**` | **Cumplida.** Ni `filex/`, ni `bench/scripts/verificador.py`, ni ningún `.md` maestro, ni los directorios de otros agentes |
| No hacer `git add` ni `git commit` | **Cumplida.** Nada versionado |
| Arneses compartidos, copiados y no modificados | **Cumplida.** `mcp_probe_bin.py` y `mcp_probe.py` ni abiertos; `ocr_eval.py`, `ocr_motor.py` y todo `bench/salidas-corpus-d4/` y `bench/salidas-ppp-norm/`, intactos |
| `bench/salidas-referencia/referencia.json` solo de lectura | **Cumplida.** Ni abierto |
| Decir **qué evaluador acentuado** se usa | **Cumplida.** `bench/salidas-corpus-d4/ocr_eval_d4.py`, copia byte a byte, `sha256` en el `MANIFIESTO.md`. §1.2 |
| Reportar las dos lecturas, con y sin acentos | **Cumplida.** `tablas.md` §1 lleva las 396 celdas en `acentos / ascii` |
| **Fijar el dispositivo** | **Cumplida.** GPU (`cuda`, `gpu:0`) en las siete configuraciones neuronales, declarado; Tesseract es CPU y no tiene otra |
| Lock de GPU en toda tanda que use la tarjeta | **Cumplida.** Siete adquisiciones (A · B · D · E · C · G · H), **lock libre al terminar, verificado**. Las tres de Tesseract son CPU y **no** lo toman, para no bloquear a otros |
| Mirar los PID antes de culpar al arnés | **Cumplida.** §1.3: 2 728 MiB de base, todos de escritorio, ningún `python.exe` ajeno |
| **Los dos testigos**, y con **tope al testigo** | **Cumplida.** Tope de 20 s implementado en `parche_km.py` y en `tess_lote_km.py`; `testigo_topado=false` en las nueve tandas. **Y el de proceso volvió a atrapar dos tandas que el monohilo declaró limpias** |
| Medianas de n≥9 | **Cumplida** en las 396 celdas. La única medida de n=1 es la **sonda de diagnóstico** de §6.1-6.2, declarada como sonda |
| No sobremuestrear | **Cumplida.** ppp nativos leídos del PDF con `pypdfium2`; `d3` barre desde **50 ppp**, no desde 100 |
| Informar también en píxeles | **Cumplida.** `tablas.md` §0: las 44 rasterizaciones con píxeles y Mpx |
| Tope de VRAM | **Cumplida.** `TOPE_LADO_PX=3400` al rasterizar y `VRAM_TOPE` por celda. **Disparó, y eso fue el hallazgo §6.3** |
| Sondear en ejecución, no deducir | **Cumplida.** El comportamiento del asignador y el del `--psm` **se midieron**; no se dedujo ninguno del código |
| Decir sobre qué checkpoint se aplica R6 | **Cumplida.** **`PP-OCRv6 small`, y solo ahí** (ONNX en RapidOCR, `torch` en docling vía `rapidocr_params`). Las dos columnas «defecto» son control |
| No instalar en los venv | **Cumplida.** Nada instalado. `RapidOCR` registró `File exists and is valid` para los cuatro modelos. `torch 2.6.0+cu124`, `torch.cuda.is_available() = True`, verificado en la cabecera de cada tanda de EasyOCR |
| Timeouts explícitos | **Cumplida.** `timeout 3600`–`5400` en las **27** invocaciones de motor, `timeout=600` en cada llamada a `tesseract`, `magick` y `gs`, `stdin=DEVNULL` en todas. Ningún proceso quedó colgado |
| Dos intentos por problema | **Cumplida.** §7 puntos 1 y 2 |
| Borrar los binarios, dejar `MANIFIESTO.md` | **Cumplida.** 78,7 MB borrados; `sha256`, tamaño y orden exacta de las 44 rasterizaciones en `bench/salidas-k-motor/MANIFIESTO.md` |

---

## 9. Lo que queda PENDIENTE

- **El `k` sigue ajustado sobre CUATRO documentos, y uno de ellos no discrimina.** En
  la práctica son **tres**. Es cuatro veces más evidencia que la que había, y sigue
  siendo poca para una constante de producción. **Lo que este informe fija no es el
  valor definitivo del `k`: es el método para fijarlo y el requisito de ≥4 documentos.**
- **Los cuatro documentos comparten geometría de página** (465,84 pt de ancho) **y tres
  de los cuatro salen del mismo generador sintético.** `patologico_escaneado` es el
  único que no, y es justo el que no discrimina. **B12 (degradación realista) sigue
  siendo el pendiente que más ampliaría esta medida.**
- **`escaneado_d3` sigue sin refinamiento entre ×1,25 y ×1,40** (B16). Aquí se
  confirma el acantilado de RapidOCR+R6 (2,53 → 46,84) y **se añade uno nuevo, de
  PaddleOCR entre ×1,40 y ×1,60** (3,80 → 75,95), que tampoco tiene puntos intermedios.
- **La curva de Tesseract está barrida (B14 cerrado en lo esencial), pero con UN
  rasterizador y DOS `--psm`.** §6.2 mide que el rasterizador vale 33 puntos: **la
  tabla de `k` de Tesseract habría que rehacerla con Ghostscript** para que sea
  comparable con la vía de contenedor, que es la que FileX usaría.
- **Los otros ocho `--psm` de Tesseract no se han barrido**, ni se ha sondeado cuál usa
  el Tesseract embebido en Ghostscript — que es lo que cerraría del todo el pendiente 7
  de `invocacion-aristas.md`.
- **El efecto del rasterizador solo está medido con Tesseract.** Si vale 33 puntos ahí,
  hay que comprobar si vale algo en PaddleOCR y RapidOCR, **y todo el corpus de este
  proyecto está rasterizado con ImageMagick.**
- **El reciclado de proceso del sidecar (§6.3) no está medido en coste.** Cuánto cuesta
  reiniciar PaddleOCR (carga en frío) frente a lo que ahorra en VRAM es una decisión de
  arquitectura sin cifra.
- **`k` de EasyOCR y de las dos configuraciones «defecto» de RapidOCR se publican pero
  no se recomiendan**: son motores que FileX no enviaría. Están para que la
  descomposición de varianza tenga nueve filas y no cuatro.
- **El suelo de 100 ppp sigue sin probarse con un original que lo necesite** (B15).

---

## 10. Ficheros

Todo en **`bench/salidas-k-motor/`**, con `MANIFIESTO.md`:

| fichero | qué es |
|---|---|
| `ocr_eval_d4.py`, `d4_texto.py` | **copias byte a byte** de `bench/salidas-corpus-d4/`. Se importan, no se modifican |
| `ocr_eval_km.py` | copia byte a byte de `ocr_eval_pn.py` (P1): añade la referencia `tipico` y la deducción por nombre |
| `preparar_km.py` | rasterizado por **factores**, con píxeles, Mpx y tope de lado |
| `parche_km.py` | los **tres** cambios aplicados a las copias de los arneses de P1, escritos y justificados |
| `ocr_lote_km.py`, `docling_lote_km.py` | los arneses parcheados (testigo con tope + guardia de VRAM) |
| `tess_lote_km.py` | Tesseract nativo, CPU, con lista blanca de idioma (`CLAUDE.md` trampa 18) |
| `sonda_tess.py` | la sonda de `--psm` × rasterizador de §6.1-6.2 |
| `repro_p1.py` → `json/repro_p1.json` | el control de reproducción: **72 de 72** |
| `tablas_km.py` → `tablas.md` | las nueve tablas, los óptimos, el arrepentimiento y la descomposición de varianza |
| `manifiesto_km.py` | genera el `MANIFIESTO.md` y **borra** los 78,7 MB de rasterizaciones |
| `geom.py` | lectura de ppp nativos de los cinco PDF, previa al diseño |
| `run_a_png.sh` … `run_i_tess_psm.sh` | las **nueve** tandas, con su `gpu_acquire`/`gpu_release` donde toca |
| `json/`, `texto/`, `logs/` | resultados por celda, la salida literal de OCR de cada celda (397 ficheros: `k1800__patologico_escaneado` se midió dos veces, en las tandas E y H) y el registro completo |
