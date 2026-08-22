# `--psm`, rasterizador y ppp: los tres parámetros que Tesseract no deduce

**Encargo B17 · B18 · B14 (G2).** `bench/k-por-motor.md` §9 dejó tres pendientes
abiertos sobre Tesseract, y los tres salían del mismo sitio: **M1 midió que hay dos
variables que pesan más que el `k` —el `--psm` (42,78 puntos) y el rasterizador
(33,22)— y las midió con una sonda de n=1 y cuatro `--psm`.** Este informe las barre
como se barrió el `k`.

**Máquina:** RTX 3060 12 288 MiB, 12 hilos, Windows 10, Python 3.11.9.
**Fecha:** 2026-08-22, 15:30–20:10.
**GPU: NO se usó y NO se tomó el lock.** Tesseract corre en CPU y los dos
rasterizadores (`magick`, `gswin64c`) también. Esta tanda no tocó la tarjeta en ningún
momento, deliberadamente, para no bloquear a los otros cuatro agentes activos.

**Motor:** Tesseract **5.5.0.20241111** (leptonica 1.85.0) **nativo de Windows**,
`C:\Program Files\Tesseract-OCR\tesseract.exe` — que **no está en el PATH**.
**Datos de idioma:** `C:\Program Files\PDFgear\tessdata` vía `TESSDATA_PREFIX`, 16
idiomas incluido `spa`. **Los puso PDFgear, no este proyecto**: se leen, no se instala
nada. Idioma por **lista blanca** (`{spa, eng}`), comprobada contra `--list-langs`
(`CLAUDE.md` trampa 18).

**Evaluador: `bench/salidas-corpus-d4/ocr_eval_d4.py`, copiado byte a byte** a
`bench/salidas-psm/ocr_eval_d4.py` (`sha256` en el `MANIFIESTO.md`, verificado idéntico
al original y al de M1). Es el **acentuado**; `bench/scripts/ocr_eval.py` **no se ha
abierto ni usado**: es ciego a las tildes. Todo el CER que se publica aquí es la lectura
**acentos**; la lectura `ascii` está en `json/resumen.json`.

**547 celdas, mediana de n=9, las 547 deterministas y las 547 con `rc = 0`** — tras
reintentar una vez las cinco que se cayeron con `0xC0000142` a mitad de tanda, que **no
eran una medida sino un proceso que no arrancó** (§6.1).

---

## 0. Veredicto, primero

Las tres preguntas del encargo, contestadas con todas las letras:

> **1 — MEDIDO: el `--psm` es del PAR (motor, documento), igual que el `k`.**
> Con la resolución declarada y a `k` = ×1,00, el `--psm` óptimo es **`psm 6` en `d2`,
> `psm 11/12` en `d4` y `psm 3/4` en `d4c` y `d4f`**: **tres respuestas distintas en
> cuatro documentos discriminantes, y ningún `--psm` gana en todos.** *(§2)*

> **2 — MEDIDO, y es el resultado principal: `--psm` y `k` NO son separables.**
> **En los cuatro documentos el `--psm` ganador cambia a lo largo del eje `k`** (de 2 a
> 4 conjuntos ganadores distintos por documento), y **en los cuatro el `k` óptimo cambia
> según el `--psm`**. La interacción se lleva del **13,7 % al 41,2 %** de
> la varianza del CER dentro de un documento. **La regla del adaptador que hoy está en
> `CLAUDE.md` trampa 8 y en `PLAN-ORQUESTADOR.md` §5 está incompleta: fija `k` por
> motor y deja `--psm` al defecto, y el óptimo de uno depende del otro.** *(§3)*
>
> **Con una autolimitación que también está MEDIDA y que va en mi contra** *(§3.5)*:
> **elegir el `--psm` a ×1,00 y optimizar el `k` después llega a la MISMA pareja** que
> barrer las 55 celdas (3,003 los dos, sobre los tres documentos discriminantes). **Lo
> que la interacción rompe no es el procedimiento, es la TRANSFERIBILIDAD:** el ×0,75
> de `psm 11` no vale para `psm 3` (×0,875) ni para `psm 6` (×0,625), y **ninguno de
> los dos números significa nada sin el otro al lado.**

> **3 — MEDIDO, y REFUTA una conclusión de este proyecto: los 33,22 puntos del
> «rasterizador» NO son del rasterizador.** Las ocho variantes de rasterizado dan
> **exactamente los mismos píxeles** —42 pares comparados sobre 6 documentos, **RMSE
> 0,0000 y `md5` idéntico del ráster crudo en los 42**—. Lo que difiere es **el trozo
> `pHYs` de la cabecera del PNG**: ImageMagick lo escribe con **`unidad = 0`**, que
> **no declara resolución**, y Ghostscript con `unidad = 1` = 200 ppp reales. Tesseract,
> sin resolución válida, **se inventa una** (`Estimating resolution as 403`) y con ella
> cambia el análisis de maquetación. **Forzar la resolución verdadera reproduce la
> salida de Ghostscript byte a byte en 126 de 126 celdas.** *(§4)*
>
> *(**G3 llegó al mismo mecanismo por su cuenta, con otro corpus y en paralelo.** Los
> dos hallazgos son independientes y coinciden; lo que este informe añade son las 42
> comparaciones de píxeles que descartan al rasterizador y el barrido de la resolución
> declarada con los píxeles fijos, §4.5.)*

> **4 — MEDIDO, y refuta el punto de partida de B14: los 32,10 puntos que le costaba a
> Tesseract leer `escaneado_d2` a sus 100 ppp nativos no eran de los ppp.** A **100 ppp
> nativos**, `--psm 6` da **0,00 % de CER**. El `--psm 3` por defecto da 30,38 %. **La
> «curva de ppp» que motivaba B14 era una curva de `--psm` mal leída.** *(§5)*

Y un quinto, que es de método y corrige la receta que el propio proyecto acaba de
adoptar:

> **5 — MEDIDO: un arrepentimiento calculado sobre documentos que el motor NO LEE premia
> al modo más callado, y aquí llegó a invertir el resultado.** Con los seis documentos
> dentro, el defecto `psm 3` sale **el mejor de los doce modos** (regret 12,43); con los
> dos que nadie lee fuera, sale **el cuarto** (18,29) y `psm 11` pasa a **3,77**. La
> causa es que en esos dos el óptimo es un modo que devuelve **dos bytes**: el silencio
> puntúa y la alucinación penaliza 88 puntos. **`k-por-motor.md` §5 estableció «fija `k`
> por mínimo arrepentimiento sobre ≥4 documentos»; hay que añadirle «que el motor
> lea».** *(§6.3)*

Y la consecuencia de diseño, que es la que se lleva al orquestador:

> **El adaptador de Tesseract tiene TRES parámetros que el motor no puede deducir, no
> uno: `--psm`, `k` y la resolución declarada en la cabecera del ráster.** Los tres
> interactúan, los tres son del par y **el tercero es gratis, no está en ningún
> inventario y vale hasta 33,22 puntos.**

---

## 1. Cómo se midió

### 1.1 El diseño

| | |
|---|---|
| documentos | `escaneado_d2` (100 ppp nativos, ref. 79 car.), `escaneado_d3` (100, 79), **`escaneado_d4` (200, 610 — el ancla de M1)**, `escaneado_d4c` (200, 610), `escaneado_d4e` (200, 610), `escaneado_d4f` (240, 610) |
| `--psm` | **los 12 implementados**: 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. **El `psm 2` no existe**: Tesseract lo documenta como *«not implemented»* y está fuera de la lista blanca del arnés |
| `k` | ×0,50 ×0,625 ×0,75 ×0,875 **×1,00** ×1,125 ×1,25 ×1,40 ×1,50 ×1,60 ×1,80 — **los once de M1**, para que las tablas sean comparables celda a celda |
| rasterizadores | **ocho variantes** (§4.1) |
| resolución declarada | sin declarar, 70, 100, 150, 200, 300, 400 ppp — **con los píxeles fijos** |
| celdas | **547**, mediana de **n=9** |

**`patologico_escaneado` NO se usa.** M1 lo midió con 88 celdas a cero y lo declaró
inútil para barrer (`k-por-motor.md` §7.3). Se sustituye por `escaneado_d2` y
`escaneado_d4e`, que sí están en la zona de degradación.

**No se sobremuestreó nada por error** (`CLAUDE.md` trampa 6): los ppp nativos se leen
de la imagen incrustada de cada PDF con `pypdfium2` y el factor se aplica sobre ellos.
`d2` y `d3` tienen **100** ppp nativos y su ×1,00 son **100 ppp**, no 200.

**Y se informa también en píxeles** (`CLAUDE.md` trampa 8: *los ppp no son la unidad*).
Las 133 rasterizaciones llevan su geometría y sus Mpx en `json/geometria_psm.json` y en
el `MANIFIESTO.md`.

### 1.2 Las tandas

| tanda | qué barre | celdas | deterministas |
|---|---|---:|---:|
| **A** | los 12 `--psm` × 6 documentos, a ×1,00, ráster `im` | 72 | 72 |
| **B** | 5 `--psm` × 11 `k` × 4 documentos, ráster **`im_ppi`** (resolución **declarada**) | 220 | 220 |
| **C** | 3 `--psm` × 11 `k` × 2 documentos, ráster **`im`** (resolución **no declarada**) | 66 | 66 |
| **D** | 3 `--psm` × 6 documentos × 7 resoluciones declaradas, **con los píxeles fijos** | 126 | 126 |
| **E** | 3 `--psm` × 11 `k` × `d4e` y `d4f`, ráster `im_ppi` | 63 | 63 |
| sonda `raster` | 8 variantes × 6 documentos, comparación de **píxeles** | 42 pares | — |
| sonda `phys` | 7 variantes × 6 documentos × 3 `--psm`, con y sin forzar ppp | 126 | — |

La tanda E son **63 y no 66** porque `escaneado_d4f` a ×1,80 daría 2 794×3 744 px y el
**tope de lado de 3 400 px** lo rechaza. El tope existe porque `ppp-y-normalizacion.md`
§7 midió que barrer hasta 400 ppp deja a PaddleOCR en 11 942 de 12 288 MiB **sin dar
error**; aquí, con Tesseract en CPU, no había riesgo de VRAM, pero el tope se dejó por
coherencia con las demás tandas del proyecto. **Está declarado, no escondido.**

### 1.3 Los dos testigos de ruido, y con tope

Cada tanda registra los dos (`CLAUDE.md` §3): bucle monohilo (**deriva dentro** de la
tanda) y mediana de cinco `ffprobe -version` (**nivel** de carga; calibración en reposo
del proyecto, 26,65 ms). **El testigo de proceso lleva tope de 20 s** y devuelve el tope
marcando `testigo_topado`. **No se agotó en ninguna de las once tandas.**

| tanda | deriva (monohilo) | nivel (proceso) | veredicto |
|---|---:|---:|---|
| A | 1,10 | ×1,61 | limpia |
| B | 1,34 | ×1,47 | limpia |
| C | 0,69 | ×1,06 | limpia |
| D 70 / 100 / 150 / 200 | 0,92 / 1,04 / 0,90 / 0,87 | ×1,02 / ×1,25 / ×1,52 / ×1,31 | limpias |
| D 300 | 1,41 | **×4,11** | **sucia** |
| D 400 (primer intento) | **0,36** | **×3,60** | **sucia — y con cinco caídas** |
| D 400 (reintento) | 0,65 | **×750,47** | **sucia — testigo TOPADO** |
| D sin declarar | 2,37 | **×12,54** | **sucia** |
| E | 0,81 | **×23,44** | **sucia** |

**Cinco tandas salen sucias por el testigo de proceso, y en tres de ellas el monohilo
decía que la máquina iba MÁS RÁPIDA** (0,36 · 0,65 · 0,81) mientras el de proceso medía
×3,60, ×750 y ×23,44. Es el **cuarto, quinto y sexto** caso del mismo patrón
(`CLAUDE.md` §3 llevaba tres), y **esta vez el monohilo no sólo se equivocó: apuntó al
revés.** Hay cuatro agentes más trabajando en este repositorio.

**Y el tope del testigo disparó por primera vez en el proyecto.** En el reintento de la
tanda D 400 el testigo de proceso final agotó los 20 s y devolvió el tope marcando
`testigo_topado = true`, en vez de colgar la medición. `CLAUDE.md` §3 lo pedía después
de que a P3 le costara un ×94,6: **la defensa funcionó, y funcionó con un nivel de carga
de ×750 sobre el reposo.** Sin tope, esa tanda habría tardado hasta 300 s sólo en el
testigo.

**Consecuencia, separada y honesta:** los **CER no están afectados** —las **547 celdas**
salieron deterministas con n=9, y el CER de Tesseract sobre un PNG fijo es una función
determinista—; **los tiempos de las tandas D 300, D 400, D sin declarar y E no se usan
para ninguna conclusión.** Aquí no hacía falta ninguno: **el objeto de medida es el
CER**. Ningún milisegundo de este informe es comparable con el de otro informe.

---

## 2. B17 — ¿el `--psm` es del motor o del par?

### 2.1 Los doce modos sobre seis documentos

**MEDIDO**, tanda A, n=9, ráster `im` a ×1,00 (CER acentos, y entre paréntesis los
bytes devueltos).

| `--psm` | `d2` | `d3` | `d4` | `d4c` | `d4e` | `d4f` |
|---|---|---|---|---|---|---|
| 1 auto+OSD | 30,38 (89) | 100,00 (**0**) | 84,56 (107) | **1,85** (610) | 100,00 (**0**) | **2,35** (610) |
| **3 auto (defecto)** | 30,38 (89) | 100,00 (**0**) | 84,56 (107) | **1,85** (610) | 100,00 (**0**) | **2,35** (610) |
| 4 columna única | 30,38 (89) | 100,00 (**0**) | 84,73 (111) | **1,85** (610) | 100,00 (**0**) | **2,35** (610) |
| 5 bloque vertical | 77,22 (54) | 198,73 (221) | 88,93 (111) | 81,04 (244) | 327,85 (2377) | 81,04 (278) |
| 6 bloque único | **0,00** (82) | 113,92 (133) | 55,70 (346) | 6,54 (586) | 190,10 (1463) | 6,04 (582) |
| 7 línea única | 100,00 (**0**) | 100,00 (**0**) | 100,00 (**0**) | 99,50 (11) | 100,00 (**0**) | 100,00 (**0**) |
| 8 palabra | 98,73 (2) | 98,73 (2) | 99,66 (3) | 99,83 (2) | 100,00 (2) | 100,00 (2) |
| 9 palabra en círculo | 98,73 (2) | 100,00 (2) | 96,48 (22) | 95,97 (25) | 99,83 (2) | 95,97 (25) |
| 10 carácter | 98,73 (2) | 98,73 (2) | 100,00 (2) | 100,00 (3) | 100,00 (2) | 100,00 (3) |
| 11 texto disperso | 13,92 (91) | 188,61 (263) | **41,78** (485) | 2,68 (625) | 119,30 (1335) | 2,68 (626) |
| 12 disperso+OSD | 13,92 (91) | 163,29 (233) | **41,78** (485) | 2,68 (625) | 109,40 (1262) | 2,68 (626) |
| 13 línea cruda | 98,73 (2) | 98,73 (2) | 99,66 (3) | 99,83 (2) | 100,00 (2) | 100,00 (2) |

**Mejor `--psm` por documento** (**‡** = argmin **no informativo**: ningún `--psm` lee
el documento, así que el mínimo elige *quién escupe menos basura*, no quién lee mejor —
es el criterio de `k-por-motor.md` §2.1):

| documento | argmin | mejor CER |
|---|---|---:|
| `d2` | **psm 6** | **0,00** |
| `d3` | psm 8 / 10 / 13 ‡ | 98,73 |
| `d4` | **psm 11 / 12** | 41,78 |
| `d4c` | **psm 1 / 3 / 4** | 1,85 |
| `d4e` | psm 9 ‡ | 99,83 |
| `d4f` | **psm 1 / 3 / 4** | 2,35 |

> **MEDIDO — el `--psm` es del par.** De los **cuatro documentos discriminantes**
> (`d2`, `d4`, `d4c`, `d4f`) salen **tres respuestas distintas**, y **ningún `--psm`
> gana en los cuatro**. `psm 3` gana en `d4c` y `d4f` y es el **peor de los tres
> candidatos** en `d4` (84,56 frente a 41,78 de `psm 11`) y en `d2` (30,38 frente a
> 0,00 de `psm 6`).

**Descomposición de la varianza del CER** en la rejilla `--psm` × documento
(mismo método de medias marginales que usó `tablas_km.py` con el `k`), en las dos
lecturas —CER crudo, donde las alucinaciones de >100 % pesan al cuadrado, y CER topado
a 100, donde un documento no leído vale lo mismo se alucine o no:

| fuente | crudo | topado a 100 |
|---|---:|---:|
| **`--psm`** | **24,9 %** | **40,1 %** |
| documento | 35,2 % | 30,9 % |
| **interacción `--psm` × documento** | **39,9 %** | **29,0 %** |

**La interacción se lleva del 29 al 40 %.** Es menos que el 76,7 % que M1 midió para el
`k`, y esa diferencia es informativa: **el `--psm` es «más del motor» que el `k`, pero
sigue sin poder fijarse sin mirar el documento.**

**Arrepentimiento por `--psm` fijo** (media de `CER(psm) − min_psm CER`), y **aquí el
recuento cambia de signo según qué documentos entren**:

| `--psm` | sobre los **seis** | sobre los **cuatro discriminantes** |
|---|---:|---:|
| **11 / 12** | 20,74 / 14,87 | **3,77 / 3,77** |
| **6** | 21,29 | **5,58** |
| **1 / 3 (defecto) / 4** | **12,43** / **12,43** / 12,46 | 18,29 / **18,29** / 18,33 |
| 5 | 101,71 | 70,56 |
| 7, 8, 9, 10, 13 | 57–59 | 85–88 |

**Y hay que decir la trampa entera, porque estuve a punto de publicar la lectura
equivocada.** Sobre los seis documentos, el defecto `psm 3` sale **el mejor de los
doce** (12,43). **Sobre los cuatro que alguien lee, sale el cuarto, con 18,29 frente a
los 3,77 de `psm 11`.** La diferencia son `d3` y `d4e`, donde **el óptimo es un modo que
devuelve dos bytes**: `psm 3` devuelve cero y le sacan 1,27 puntos, mientras `psm 11`
alucina un 188 % y se lleva **88 puntos de arrepentimiento** por documento. **Meter en
un arrepentimiento documentos que ningún modo lee no mide qué modo es mejor: mide qué
modo es más callado.** Marcados con ‡ arriba, y excluidos aquí.

> **MEDIDO — el defecto `psm 3` NO es el mejor valor fijo.** Sobre los cuatro
> documentos legibles, **`psm 11` cuesta 3,77 puntos y `psm 3` cuesta 18,29**: casi
> **cinco veces más**. Y `psm 3` cuesta **30,38 puntos en `escaneado_d2`**, donde
> `psm 6` da cero.

### 2.2 El pendiente 7 de `invocacion-aristas.md`, confirmado y ampliado

M1 dejó escrito que sobre el mismo `d3` **`psm 3/4` devuelven 0 bytes y `psm 6/11`
devuelven 113,92 % y 188,61 %**. **Se reproduce exacto a la centésima**, y la tanda A
lo amplía:

- **`d3`**: `psm 1/3/4/7` → **0 bytes**; `psm 6` → 113,92 %; `psm 12` → 163,29 %;
  `psm 11` → **188,61 %**; `psm 5` → 198,73 %.
- **`d4e`**: `psm 1/3/4/7` → **0 bytes**; `psm 12` → 109,40 %; `psm 11` → 119,30 %;
  `psm 6` → 190,10 %; `psm 5` → **327,85 %** (2 377 bytes devueltos contra una
  referencia de 596).

> **MEDIDO — silencio y alucinación son el mismo motor con distinto modo de
> segmentación, y ahora en DOS documentos, no en uno.** El pendiente 7 queda cerrado en
> lo que preguntaba: **la causa suficiente de la asimetría está identificada y es un
> solo parámetro**. Lo que sigue **PENDIENTE** es cuál usa el Tesseract embebido en
> Ghostscript, que no se ha sondeado aquí.

**Y hay una lectura de contrato que M1 no sacó.** Los 12 modos se reparten en tres
regímenes de fallo, y **los tres devuelven `rc = 0`**:

| régimen | `--psm` | qué entrega | lo atrapa |
|---|---|---|---|
| **silencio** | 1, 3, 4, 7 en `d3`/`d4e` | **0 bytes**, `rc=0` | el punto 4 del contrato (páginas pedidas ≠ obtenidas) — **si se declara que se pedía texto** |
| **cuenta atómica** | 8, 9, 10, 13 | **2–25 bytes** de basura, `rc=0` | la trampa 4 de `CLAUDE.md` (umbral ≥10 caracteres) atrapa la mitad; **`psm 9` en `d4c` devuelve 25 y la pasa** |
| **alucinación** | 5, 6, 11, 12 en `d3`/`d4e` | **hasta 2 377 bytes** contra 596 de referencia, `rc=0` | **nada del contrato.** Sólo fidelidad |

**Un `--psm` mal elegido produce las tres formas de fallar sin un solo código de error.**

---

## 3. B17 (lo importante) — `--psm` y `k` NO son separables

Ésta era la pregunta que el encargo marcaba como la más valiosa. La respuesta es que
**sí interactúan**, con tres evidencias independientes (§3.1-3.3) **y una
autolimitación medida que acota qué se puede concluir de ellas** (§3.5).

Tanda **B**: 5 `--psm` × 11 `k` × 4 documentos, **con la resolución declarada**
(ráster `im_ppi`, §4). Las cuatro rejillas completas están en
`bench/salidas-psm/tablas.md` §2; aquí, `escaneado_d4` entera:

| `--psm` | ×0,50 | ×0,625 | ×0,75 | ×0,875 | ×1,00 | ×1,125 | ×1,25 | ×1,40 | ×1,50 | ×1,60 | ×1,80 | argmin `k` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 3 | 89,60 | 84,73 | 81,88 | **50,50** | 51,34 | 86,41 | 89,60 | 91,61 | 88,76 | 71,14 | 89,26 | ×0,875 |
| 4 | 89,60 | 83,05 | 80,70 | **53,69** | 62,08 | 94,30 | 89,43 | 90,10 | 91,11 | 74,50 | 84,90 | ×0,875 |
| 6 | 48,15 | **44,80** | 66,78 | 54,19 | 55,70 | 67,95 | 60,23 | 67,79 | 54,87 | 56,88 | 77,68 | **×0,625** |
| 11 | 51,01 | 53,19 | 50,50 | **38,09** | 40,60 | 45,13 | 46,31 | 45,81 | 50,00 | 48,83 | 52,35 | ×0,875 |
| 12 | 51,01 | 53,19 | 50,50 | **38,09** | 40,60 | 45,13 | 46,31 | 45,81 | 50,00 | 48,83 | 52,35 | ×0,875 |

### 3.1 Evidencia 1 — el `--psm` ganador CAMBIA a lo largo del eje `k`

**En `escaneado_d4`, `psm 6` es el mejor de los cinco a ×0,50 y ×0,625, y `psm 11/12`
lo son de ×0,75 en adelante.** No es un empate que se rompe: a ×0,625 `psm 6` da
**44,80** y `psm 11` da **53,19**; a ×0,875 `psm 6` da 54,19 y `psm 11` da **38,09**.
**El orden se invierte, y con 8 a 16 puntos de margen a cada lado.**

Y pasa en los cuatro documentos:

| documento | conjuntos ganadores distintos a lo largo de `k` | cuáles |
|---|---:|---|
| `d2` | **3** | `{6}`, `{3,4}`, `{3,4,6}` |
| `d3` | **4** | `{6,11}`, `{12}`, `{11}`, `{3,4}` |
| `d4` | **2** | `{6}`, `{11,12}` |
| `d4c` | **2** | `{11,12}`, `{3,4}` |

**Cuatro de cuatro.** *Elegir el `--psm` a la resolución nativa y luego optimizar el `k`
es elegir en el punto equivocado de la rejilla.*

### 3.2 Evidencia 2 — el `k` óptimo CAMBIA según el `--psm`

| documento | `psm 3` | `psm 4` | `psm 6` | `psm 11` | `psm 12` | ¿coinciden? |
|---|---|---|---|---|---|---|
| `d2` | ×1,125…×1,80 | ×1,125…×1,80 | ×1,00, ×1,25…×1,80 | ×0,75, ×1,125…×1,60 | ×0,75, ×1,125…×1,60 | **NO** |
| `d3` | plano (100,00) ‡ | plano ‡ | **×0,625** | **×0,75** | **×0,625** | **NO** |
| `d4` | ×0,875 | ×0,875 | **×0,625** | ×0,875 | ×0,875 | **NO** |
| `d4c` | ×1,40 | ×1,40 | ×1,40 | **×1,60** | **×1,60** | **NO** |
| `d4f` (tanda E) | ×1,25 | — | ×1,25 | **×1,00 / ×1,60** | — | **NO** |
| `d4e` (tanda E) | plano (0 bytes) ‡ | — | ×0,625 | ×0,625 | — | (sí, pero ‡) |

**Cuatro de cuatro entre los documentos de la rejilla completa, y cinco de seis
contando la tanda E.** Y no es un empate de decimales: en `d4`, `psm 6` a su óptimo
(×0,625 → 44,80) contra `psm 6` en el óptimo de los demás (×0,875 → 54,19) son
**9,39 puntos**; en `d4f`, `psm 11` en el óptimo de `psm 3` (×1,25) da **8,72 %** contra
**2,68 %** en el suyo.

### 3.3 Evidencia 3 — la varianza

Descomposición del CER dentro de cada documento, rejilla `--psm` × `k`
(**resolución declarada**):

| documento | `--psm` | `k` | **interacción** |
|---|---:|---:|---:|
| `d2` | 7,3 % | 51,5 % | **41,2 %** |
| `d3` | 23,0 % | 38,5 % | **38,5 %** |
| `d4` | **69,2 %** | 17,1 % | **13,7 %** |
| `d4c` | 5,9 % | 76,4 % | **17,7 %** |

**La interacción nunca baja del 13,7 % y llega al 41,2 %.** Y las dos primeras columnas
dicen algo que conviene no pasar por alto: **cuál de los dos parámetros domina es
distinto en cada documento.** En `d4` manda el `--psm` (69,2 %); en `d4c` manda el `k`
(76,4 %); en `d2` manda el `k` (51,5 %) con el `--psm` en un 7,3 %. **No hay un
«parámetro grande» y otro «pequeño»: hay un par.**

### 3.4 Lo que cuesta: la elección conjunta

Arrepentimiento medio sobre los documentos, con el oráculo por documento
(`d2` 0,00 · `d3` 68,35 ‡ · `d4` 38,09 · `d4c` 1,68). **Se dan las dos poblaciones**,
por lo que enseñó §6.3:

| procedimiento | los **cuatro** | los **tres discriminantes** |
|---|---|---|
| **conjunto** — barrer las 55 celdas | `psm 11` + `×0,75` → **4,405** | `psm 11` + `×0,875` → **3,003** |
| **separable** — elegir `--psm` a ×1,00 y luego su mejor `k` | `psm 6` + `×0,625` → **4,853** | `psm 11` + `×0,875` → **3,003** |
| el defecto del motor con el `k` de M1 | `psm 3` + `×0,875` → **11,710** | `psm 3` + `×0,875` → **5,063** |
| el defecto puro | `psm 3` + `×1,00` → **19,558** | `psm 3` + `×1,00` → **14,600** |

**Y el propio `k` óptimo del par se mueve al cambiar la población:** `psm 11` pide
×0,75 con `d3` dentro y **×0,875** sin él. Otra vez lo de §6.3.

### 3.5 Y aquí hay que refutarse a uno mismo: el procedimiento separable NO pierde

**MEDIDO, y va en contra de lo que este informe defiende.** Sobre los tres documentos
discriminantes, **el procedimiento separable llega EXACTAMENTE a la misma pareja que el
barrido conjunto** (`psm 11` + ×0,875, arrepentimiento 3,003 los dos). Y sobre los
cuatro, pierde **0,448 puntos**. **Es decir: elegir el `--psm` a ×1,00 y optimizar el
`k` después habría funcionado en esta población.**

**Entonces, ¿qué queda de §3.1–3.3?** Queda esto, y hay que separarlo con cuidado:

1. **Lo que está MEDIDO y no se cae:** el óptimo de cada eje depende del otro (4 de 4
   documentos en los dos sentidos) y la interacción se lleva del 13,7 al 41,2 % de la
   varianza. **Los hechos no cambian.**
2. **Lo que NO se sostiene:** *«hay que barrer la rejilla conjunta o se pierde CER»*.
   **Sobre esta población no se pierde.** Lo escribo porque lo medí, no porque me
   convenga.
3. **Lo que sí se sostiene, y es lo que va a la regla:** un `k` **no es transferible
   entre `--psm`**, y un `--psm` **no es transferible entre `k`**. El ×0,75 que M1
   publicó para `psm 11` **no vale para `psm 3`** (que pide ×0,875) ni para `psm 6`
   (×0,625), y el modo ganador a ×0,625 sobre `d4` **no es el ganador a ×0,875**.
   **Cablear un `k` por motor obliga a cablear también su `--psm` y a publicarlos
   juntos** — no porque barrer por separado dé peor resultado, sino porque **ninguno de
   los dos números significa nada sin el otro.**
4. **Y hay un aviso operativo que sí depende de la interacción:** el procedimiento
   separable **sondea el `--psm` a ×1,00**, y ×1,00 no es el mejor `k` de ninguno de los
   cinco modos en `d4` ni en `d4c`. **Funciona aquí por suerte de la población**, y la
   suerte cambia: con `d3` dentro elige `psm 6` en vez de `psm 11`. **Un procedimiento
   que acierta por la población que le tocó no es un procedimiento robusto**, y ésa es
   toda la diferencia entre las dos columnas de la tabla.

### 3.6 El mismo barrido con la resolución NO declarada (tanda C)

Se repitió la rejilla con el ráster `im` de M1, sobre `d3` y `d4`. **La interacción
sigue ahí, pero los números cambian**:

| documento | ráster | `--psm` | `k` | interacción |
|---|---|---:|---:|---:|
| `d4` | `im` (sin declarar) | **84,2 %** | 8,3 % | 7,4 % |
| `d4` | `im_ppi` (declarada) | 69,2 % | 17,1 % | **13,7 %** |
| `d3` | `im` (sin declarar) | 22,5 % | 39,9 % | 37,6 % |
| `d3` | `im_ppi` (declarada) | 23,0 % | 38,5 % | 38,5 % |

**Sobre `d4`, no declarar la resolución infla el peso aparente del `--psm` del 69,2 al
84,2 % y hunde el del `k` del 17,1 al 8,3 %.** Es decir: **la conclusión «el `--psm`
pesa mucho más que el `k`» estaba amplificada por el metadato roto** (§4), y aun así
sobrevive.

**Y hay una corrección concreta:** el `k` óptimo de `psm 11` sobre `d4` **se mueve de
×1,00 a ×0,875** en cuanto la resolución se declara, y el CER baja de **41,78 a
38,09**.

**Reproducción del `k` de M1, y sale bien.** Los `k` de mínimo arrepentimiento por
`--psm` que salen de mi tanda B —**`psm 3` → ×0,875** y **`psm 11` → ×0,75**— son
**exactamente los dos que M1 publicó** en `k-por-motor.md` §5, con otro conjunto de
documentos (yo uso `d2`, M1 usa `patologico_escaneado`) y con el metadato corregido.
**Los `k` de M1 para Tesseract se confirman; lo que cambia es que no se pueden publicar
sin su `--psm` al lado, cosa que M1 ya hacía.**

---

## 4. B18 — el rasterizador NO vale 33 puntos. La cabecera del PNG, sí

### 4.1 Ocho variantes, los mismos píxeles

**MEDIDO.** Se rasterizaron los seis documentos con ocho caminos distintos, elegidos
para separar renderer, conversión a gris y antialias:

| variante | orden |
|---|---|
| `im` | `magick -density D x.pdf[0] -colorspace Gray -alpha remove -background white -flatten` — **la del corpus, la de P1 y la de M1** |
| `im_ppi` | la misma **+ `-units PixelsPerInch -density D`** |
| `im_sincs` | la misma **sin** `-colorspace Gray` |
| `gs` | `gswin64c -sDEVICE=pnggray -rD` — **la de P2 y la de la vía de contenedor** |
| `gs_aa1` / `gs_aa4` | `gs` con `-dTextAlphaBits`/`-dGraphicsAlphaBits` a 1 y a 4 |
| `gs16m_im` | `gs -sDEVICE=png16m` (RGB) **+** `magick -colorspace Gray` |
| `gs16m_im601` / `gs16m_im709` | ídem con `-grayscale Rec601Luma` / `Rec709Luma` |

**Resultado: los 42 pares comparados (6 documentos × 7 variantes contra `im`) son
IDÉNTICOS PÍXEL A PÍXEL.** `frac_px_iguales = 1,000000`, **RMSE = 0,0000** y **el `md5`
del ráster crudo (`magick … -depth 8 gray:-`) es el mismo en las ocho variantes**.
Media, desviación, número de niveles usados, energía de gradiente y fracción de tinta:
idénticos a la cuarta cifra.

**No hay remuestreo distinto, ni umbralizado, ni gamma, ni antialias.** Y tiene una
explicación que el propio `magick -list delegate` confirma: **ImageMagick no tiene
rasterizador de PDF — delega en Ghostscript.** Las «dos» rasterizaciones eran **el mismo
Ghostscript** las dos veces.

### 4.2 Lo que sí difiere: el trozo `pHYs`

| variante | `pHYs` | lectura |
|---|---|---|
| `im`, `im_sincs` | `x=200 y=200 unidad=0` | **SIN UNIDAD — el PNG no declara resolución.** El valor 200 es una relación de aspecto, no una densidad |
| `im_ppi`, `gs`, `gs16m_im`, `gs_aa1`, `gs_aa4` | `x=7874 y=7874 unidad=1` | 7 874 px/m = **200,00 ppp** |

Y el mecanismo, **sondeado en ejecución** por el `stderr` del propio motor, no deducido
del código:

```
$ tesseract im__k1000__escaneado_d4.png stdout -l spa --psm 3
Estimating resolution as 403 | Detected 36 diacritics      ← 107 bytes, CER 84,56 %

$ tesseract gs__k1000__escaneado_d4.png stdout -l spa --psm 3
Detected 51 diacritics                                     ← 359 bytes, CER 51,34 %
```

**Tesseract, sin resolución válida, se inventa 403 ppp sobre un ráster que tiene 200**,
y con esa cifra alimenta el análisis de maquetación.

### 4.3 La prueba de causalidad, simétrica y byte a byte

No basta con que correlacione. Se cambió la variable:

| invocación | `md5` de los píxeles | `md5` del texto | bytes | CER |
|---|---|---|---:|---:|
| `im` tal cual | `7db12c6f…` | `e60db8d4…` | 107 | **84,56** |
| `im` **`-c user_defined_dpi=200`** | `7db12c6f…` | **`9fa2544d…`** | 385 | **51,34** |
| `gs` tal cual | `7db12c6f…` | **`9fa2544d…`** | 385 | **51,34** |
| `gs` **`-c user_defined_dpi=70`** | `7db12c6f…` | **`e60db8d4…`** | 107 | **84,56** |
| `im_ppi` (`magick` con `-units PixelsPerInch`) | `7db12c6f…` | **`9fa2544d…`** | 385 | **51,34** |

**La equivalencia va en los dos sentidos y es byte a byte.** Se puede convertir
ImageMagick en Ghostscript y Ghostscript en ImageMagick **sin tocar un solo píxel**,
sólo con el metadato. Y **`im_ppi` es ImageMagick, y cae siempre del lado de
Ghostscript**.

**Censo completo** (`sonda_phys.py`, 6 documentos × 7 variantes × 3 `--psm` = 126
celdas): **forzando la resolución verdadera, las 126 celdas reproducen la salida de
Ghostscript. 126 de 126.**

Y las clases de equivalencia de la salida, sin forzar nada, **parten exactamente por la
unidad del `pHYs` y nunca por el rasterizador**:

| documento | `--psm` | clases |
|---|---|---|
| `d4` | 3 | `{im, im_sincs}` ‖ `{im_ppi, gs, gs16m_im, gs_aa1, gs_aa4}` |
| `d4` | 11 | `{im, im_sincs}` ‖ `{im_ppi, gs, gs16m_im, gs_aa1, gs_aa4}` |
| `d3` | 11 | `{im, im_sincs}` ‖ `{im_ppi, gs, gs16m_im, gs_aa1, gs_aa4}` |
| **las otras 15** | 3, 6, 11 | **una sola clase: las siete variantes coinciden** |

> **MEDIDO — REFUTADO `k-por-motor.md` §6.2 en su atribución.** *«El rasterizador vale
> 33 puntos»* es falso: **vale cero**. Los 33,22 puntos son **la resolución declarada en
> la cabecera del PNG**, y la variante culpable no es «ImageMagick» sino **una
> invocación de ImageMagick a la que le falta `-units PixelsPerInch`**. La cifra de M1
> es correcta; su nombre, no. *(Y esto se cruzó con G3, que llegó al mismo mecanismo por
> su cuenta y con otro corpus: dos agentes, dos rutas, la misma cabecera.)*

### 4.4 Un detalle mecánico que ordena todo lo demás

**`--psm 6` no cambia NUNCA con la resolución** — 0 de 11 celdas en `d4`, 0 de 11 en
`d3`, y en el `stderr` **no aparece ni una vez la línea `Estimating resolution`**. Los
que sí cambian son `psm 1/3/4/11/12`, que son exactamente **los que ejecutan análisis
de maquetación**. `psm 6` («un solo bloque uniforme») se lo salta.

> **La resolución declarada sólo entra donde entra el análisis de maquetación.** Eso
> explica la forma de todo lo anterior: es un tercer parámetro que **interactúa con el
> `--psm`**, no una propiedad global de la imagen.

### 4.5 Declarar NO es gratis siempre — barrido de la resolución con los píxeles fijos

Tanda **D**: los mismos PNG de `im` a ×1,00, y siete resoluciones declaradas.

**La columna en negrita es la resolución VERDADERA de ese ráster.** `=` significa
idéntico a «sin declarar», a la centésima.

| documento (ppp reales) | `--psm` | sin declarar | 70 | 100 | 150 | 200 | 300 | 400 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `d2` (**100**) | 3 / 6 / 11 | 30,38 / 0,00 / 13,92 | = | **=** | = | = | = | = |
| `d3` (**100**) | 3 / 6 | 100,00 / 113,92 | = | **=** | = | = | = | = |
| `d3` (**100**) | 11 | 188,61 | = | **183,54** | = | = | 189,87 | 187,34 |
| `d4` (**200**) | **3** | **84,56** | = | **98,49** | 51,34 | **51,34** | = | = |
| `d4` (**200**) | 6 | 55,70 | = | = | = | **=** | = | = |
| `d4` (**200**) | 11 | 41,78 | = | 43,79 | 40,60 | **40,60** | 41,61 | = |
| `d4c` (**200**) | 3 | 1,85 | = | **11,24** | = | **=** | **7,72** | = |
| `d4c` (**200**) | 6 | 6,54 | = | = | = | **=** | = | = |
| `d4c` (**200**) | 11 | 2,68 | = | 3,36 | = | **=** | **10,07** | = |
| `d4e` (**200**) | 3 / 6 | 100,00 / 190,10 | = | = | = | **=** | = | = |
| `d4e` (**200**) | 11 | 119,30 | = | 123,83 | 118,96 | **=** | 120,13 | 121,81 |
| `d4f` (**240**) | 3 / 6 | 2,35 / 6,04 | = | = | = | = | = | = |
| `d4f` (**240**) | 11 | 2,68 | = | 2,85 | = | = | = | = |

*(Los 240 ppp reales de `d4f` no están en la rejilla; la sonda de §4.3 los midió aparte
con `im_ppi` a 239,98 y salen **idénticos** a no declarar en los tres `--psm`.)*

**Tres recuentos, y son tres reglas distintas:**

1. **Declarar el valor VERDADERO nunca empeora: 3 mejor, 12 igual, 0 peor** de las 15
   celdas medibles. Y cuando mejora, mejora mucho: `d4` con `psm 3` pasa de **84,56 a
   51,34**; `d4` con `psm 11`, de 41,78 a 40,60; `d3` con `psm 11`, de 188,61 a 183,54.
2. **Declarar un valor FALSO sí empeora: 5 mejor, 77 igual, 11 peor** de las 93 celdas
   con un valor distinto del verdadero. Y los peores son grandes: `d4c` con `psm 3` a
   100 ppp pasa de **1,85 a 11,24** (×6,1), `d4c` con `psm 11` a 300 ppp de **2,68 a
   10,07** (×3,8), `d4` con `psm 3` a 100 ppp de 84,56 a **98,49**.
3. **Pero sobre un ráster REMUESTREADO el signo se pierde.** Comparando la tanda C
   (sin declarar) con la B (declarando los ppp de renderizado) sobre `d3` y `d4`:

   | | mejor | igual | peor |
   |---|---:|---:|---:|
   | a `k` = **×1,00** (ráster a ppp nativos) | **3** | 3 | **0** |
   | a `k` ≠ ×1,00 (ráster remuestreado) | 12 | 33 | **15** |

   **A ppp nativos declarar gana o empata siempre; sobre un ráster remuestreado es un
   empate estadístico**, y el mayor movimiento en contra —`d4`, `psm 3`, ×0,50: 79,03
   sin declarar contra 89,60 declarando— es de **10,57 puntos**, un tercio de los 33,22
   que se ganan en el caso nativo.

> **MEDIDO — la recomendación, con su matiz:** **declara la resolución VERDADERA del
> ráster en su cabecera, y no declares ninguna otra.** Los tres recuentos dicen lo
> mismo desde tres sitios: el valor verdadero no empeora nunca (0 de 15), un valor
> falso empeora en 11 de 93, y el beneficio se concentra donde el ráster está a ppp
> nativos, que es justo el caso que la regla R1 produce casi siempre.
> Y las otras dos razones no dependen de la medida:
> **(a)** es **gratis** —una bandera en la orden de rasterizado, cero cómputo—;
> **(b)** es lo único que hace **transferibles** las tablas de `k` entre informes, que
> es exactamente el problema que M1 detectó y le atribuyó al rasterizador.
> **Con qué rasterizar da IGUAL —está medido que da exactamente igual—; lo que no da
> igual es que el fichero diga la verdad sobre sí mismo.**
>
> **Y la contrapartida, que no se puede omitir: el estimador de Tesseract a veces
> acierta mejor que la verdad.** No declarar no es «el caso malo»: es «el caso que no
> controlas». Lo que se compra declarando no es sólo CER, es **determinismo**.

*(Este apartado contrasta el matiz que G3 aportó —«en `realista_d5e` con `psm 3`,
declarar la densidad empeora 15,44 puntos»— y lo confirma **con una precisión que lo
acota**: en mis celdas los empeoramientos aparecen (a) al declarar un valor falso y
(b) sobre rásteres remuestreados; **a ppp nativos y con el valor verdadero, 0 de 15**.
No sé a qué ppp está `realista_d5e` ni si su ráster estaba remuestreado, así que **no
afirmo que sean el mismo caso**: dejo las dos condiciones medidas y la comprobación
cruzada como **PENDIENTE**.)*

### 4.6 Lo que esto le añade al contrato de FileX

Es un miembro nuevo de la familia del punto 4 del contrato (*propiedades pedidas frente
a obtenidas*), y no lo atrapa ninguno de los cinco puntos actuales:

> `magick -density 200 x.pdf[0] … out.png` devuelve **`rc = 0`**, un PNG **válido**, con
> la **geometría exacta** (1 294×1 716), la **profundidad exacta** (8 bits) y el
> **espacio de color exacto** (gris). **Pasa los cinco puntos del contrato.** Y entrega
> un fichero que **declara no saber a qué resolución está**, lo que le cuesta 33,22
> puntos de CER al motor siguiente.

**La propuesta, concreta:** cuando la salida de una conversión sea la **entrada de otro
motor**, el punto 4 tiene que comparar también **los metadatos que el motor siguiente va
a leer**, no sólo los que el usuario pidió. Para un ráster que va a OCR eso es
exactamente **un campo**: la unidad del `pHYs`. Comprobarlo cuesta **leer 9 bytes de la
cabecera** — el régimen «en proceso» de `coste-verificacion.md`, no el de la sonda
externa.

---

## 5. B14 — la curva de ppp de Tesseract, con el `--psm` fijado

### 5.1 El punto de partida de B14 estaba mal leído

`CLAUDE.md` §5 dice: *«es lo que le pasa hoy a Tesseract, al que R1 le asigna 100 ppp
sobre `escaneado_d2` y le cuesta 32,10 puntos»*. Con el `--psm` barrido:

| `escaneado_d2`, resolución declarada | ×1,00 = **100 ppp nativos** | ×1,50 = 150 ppp |
|---|---:|---:|
| `psm 3` (defecto) | **30,38** | **0,00** |
| `psm 4` | 30,38 | 0,00 |
| **`psm 6`** | **0,00** | **0,00** |
| `psm 11` / `12` | 13,92 | 34,18 |

> **MEDIDO — REFUTADO el enunciado de B14.** A **sus 100 ppp nativos**, con `--psm 6`,
> Tesseract lee `escaneado_d2` **perfecto: 0,00 % de CER**. **Los 32,10 puntos no eran
> de los ppp: eran del `--psm`.** La observación *«0,00 % a 150 ppp frente a 32,10 % a
> sus 100 nativos»* es cierta **y sólo con `psm 3`**; con `psm 6` el documento se lee a
> cero en **siete de los once factores**, incluido el nativo.
>
> Y el reproche que la regla se hacía a sí misma —*«una constante global hace que cada
> motor nuevo herede los ppp que le convenían a otro»*— **se queda corto**: aquí no
> hubo herencia de ppp, hubo **un `--psm` que nadie eligió**.

### 5.2 La curva no es monótona, y el punto nativo es un bache

`escaneado_d2` con `psm 3`, resolución declarada, los once factores:

| `k` | ×0,50 | ×0,625 | ×0,75 | ×0,875 | **×1,00** | ×1,125 | ×1,25 | ×1,40 | ×1,50 | ×1,60 | ×1,80 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ppp | 50 | 62 | 75 | 88 | **100** | 112 | 125 | 140 | 150 | 160 | 180 |
| CER | 16,46 | 1,27 | 1,27 | 1,27 | **30,38** | **0,00** | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |

**El ×1,00 es un máximo local, con 1,27 % a su izquierda y 0,00 % a su derecha.** Un
salto de 30 puntos que aparece y desaparece **en un 12,5 % de resolución**. Es
determinista (n=9). **Ninguna regla de la forma `clamp` puede describir esto**, y
explica por qué medir `k` con un solo punto por documento da tan mal resultado.

**Y no es un artefacto del metadato:** la tanda A, con el ráster `im` **sin declarar
resolución**, da el mismo 30,38 % en ese punto (`d2`, `psm 3`, ×1,00). Las tres tandas
—A, B y D— coinciden a la centésima en esa celda. **El bache es del par (documento,
`--psm`), no de la cabecera.**

### 5.3 La curva, documento a documento

**MEDIDO**, tandas B y E, resolución declarada, CER acentos. El argmin de `k` **por
`--psm`**, y el CER que alcanza:

| documento (nativos) | `psm 3` | `psm 6` | `psm 11` |
|---|---|---|---|
| `d2` (100) | ×1,125…×1,80 → **0,00** | ×1,00, ×1,25…×1,80 → **0,00** | ×0,75 → 2,53 |
| `d3` (100) | plano, 100,00 ‡ | ×0,625 → 70,89 ‡ | ×0,75 → 68,35 ‡ |
| `d4` (200) | ×0,875 → 50,50 | ×0,625 → **44,80** | ×0,875 → **38,09** |
| `d4c` (200) | ×1,40 → **1,68** | ×1,40 → 6,04 | ×1,60 → 2,18 |
| `d4e` (200) | **plano: 0 bytes en los ONCE** ‡ | ×0,625 → 71,31 ‡ | ×0,625 → 71,64 ‡ |
| `d4f` (240) | ×1,25 → **1,51** | ×1,25 → 5,87 | ×1,00 / ×1,60 → 2,68 |

> **MEDIDO — no hay una curva de ppp de Tesseract: hay una por `--psm` y por
> documento.** El argmin de `k` recorre de **×0,625 a ×1,80** dentro del mismo motor y
> **no coincide entre `--psm` en tres de los cuatro documentos** (§3.2). **B14 queda
> cerrado con la respuesta contraria a la que buscaba: la pregunta «¿cuál es el `k` de
> Tesseract?» está mal planteada mientras el `--psm` no esté fijado.**

**Y el `k` de mínimo arrepentimiento, que es lo que sí se puede cablear:**

| `--psm` | mejor `k` (4 docs) | regret | mejor `k` (3 discriminantes) | regret | `k` de M1 |
|---|---:|---:|---:|---:|---:|
| `psm 3` | **×0,875** | 0,695 | **×0,875** | 0,927 | ×0,875 ✅ |
| `psm 4` | ×0,875 | 0,695 | ×0,875 | 0,927 | — |
| `psm 6` | **×0,625** | 1,450 | **×0,625** | 1,933 | — |
| `psm 11` | ×0,75 | 3,647 | **×0,875** | **1,993** | ×0,75 |
| `psm 12` | ×0,75 | 4,598 | ×0,875 | 1,993 | — |

**El `k` de M1 para `psm 3` se confirma exacto con otra población de documentos y con
el metadato corregido: ×0,875.** El de `psm 11` **se reproduce (×0,75) con la población
que incluye `d3`, y se mueve a ×0,875 sin él** — y `d3` está marcado ‡ porque nadie lo
lee. **La recomendación es ×0,875 para `psm 11`**, con la salvedad declarada.
Y se añade uno que no existía: **`psm 6` → ×0,625**, el modo que gana en `d2` y a `k`
bajo en `d4`.

**Los cuatro documentos discriminantes dan cuatro argmin distintos para el MISMO
`--psm 3`:** ×1,125 (`d2`), ×0,875 (`d4`), ×1,25 (`d4f`) y ×1,40 (`d4c`). **Un factor
1,6 de indeterminación dentro de un solo modo de segmentación.**

### 5.4 `d4e` y `d4f`: el silencio no se cura subiendo ppp

**MEDIDO**, tanda E, 11 factores, resolución declarada.

`escaneado_d4e` (200 ppp nativos, el más degradado de la familia):

| `--psm` | ×0,50 | ×0,625 | ×0,75 | ×0,875 | ×1,00 | ×1,125 | ×1,25 | ×1,40 | ×1,50 | ×1,60 | ×1,80 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 100,00 | 100,00 | 100,00 | 100,00 | 100,00 | 100,00 | 100,00 | 100,00 | 100,00 | 100,00 | 100,00 |
| 6 | 80,54 | **71,31** | 96,14 | 179,87 | 190,10 | 168,62 | 348,32 | 290,77 | 467,79 | 545,64 | 572,65 |
| 11 | 72,65 | **71,64** | 116,28 | 258,39 | 119,30 | 180,37 | 243,96 | 211,74 | 583,22 | 618,96 | 555,54 |

> **MEDIDO — `--psm 3` devuelve CERO BYTES en los once factores, de 100 a 360 ppp.**
> Ninguna resolución rescata el modo por defecto sobre este documento. Y los otros dos
> modos no lo rescatan tampoco: lo convierten en una **rampa de alucinación** que llega
> a **572,65 %** (3 411 bytes contra 596 de referencia). **Subir ppp no cura el
> silencio; lo cambia por ruido.** Es el mismo acantilado que M1 documentó en `d3` y
> aquí aparece en un documento con referencia de 610 caracteres, donde **no puede ser
> un artefacto de cuantización**.

`escaneado_d4f` (240 ppp nativos, 1 552×2 080 — el único con otra geometría):

| `--psm` | ×0,50 | ×0,625 | ×0,75 | ×0,875 | ×1,00 | ×1,125 | ×1,25 | ×1,40 | ×1,50 | ×1,60 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 5,20 | 3,02 | 3,02 | 2,52 | 2,35 | 2,01 | **1,51** | 1,85 | 2,01 | 2,52 |
| 6 | 11,07 | 6,04 | 6,54 | 6,21 | 6,04 | 6,54 | **5,87** | 6,54 | 6,21 | 6,54 |
| 11 | 8,56 | 5,37 | 6,04 | 5,87 | **2,68** | 11,41 | 8,72 | 4,70 | 4,53 | **2,68** |

`d4f` es el único documento del barrido con una **curva suave y con un mínimo claro**
para `psm 3` y `psm 6` (los dos en ×1,25 = 300 ppp), y aun así **`psm 11` no coincide**:
su mínimo está en ×1,00 y ×1,60, con ×1,125 dando 11,41 % entre medias. **El ×1,80 de
`d4f` no se midió**: 2 794×3 744 px pasa el tope de lado (§1.2).

---

## 6. Lo que falló, con el error exacto

### 6.1 Cinco procesos de Tesseract que no arrancaron, y el CER no se enteró

**Error exacto: `rc = 3221225794` = `0xC0000142` (`STATUS_DLL_INIT_FAILED`).** Cinco
celdas de la tanda D 400 (`d4e` psm 6 y 11, `d4f` psm 3, 6 y 11). El proceso murió en
**3 ms** de mediana y devolvió **0 bytes**.

**Y ése es el problema, no el fallo.** Cero bytes es exactamente lo que devuelve
Tesseract cuando **legítimamente** no lee nada: en este mismo informe hay **69 celdas
con 0 bytes y `rc = 0`** (los once factores de `psm 3` sobre `d4e`, por ejemplo).
**El CER las puntúa a las 74 igual, 100,00 %.** Si el arnés no hubiera registrado `rc`,
**las cinco habrían entrado en la tabla como «declarar 400 ppp silencia el motor»** —
que es la conclusión que estuve a punto de escribir, y es falsa: el reintento da 2,35 /
6,04 / 2,68 sobre `d4f`, **idéntico a no declarar**.

> **Trampa nueva, y es de la familia de la 18 de `CLAUDE.md`** (*`-sOCRLanguage=osd`
> revienta Ghostscript con `0xC0000005` y no devuelve código de error*): **un motor de
> OCR que se cae devuelve lo mismo que un motor de OCR que no encuentra texto.** La
> métrica no puede distinguirlos. **Hay que registrar el código de retorno en cada
> celda y contarlo aparte**, o se publican caídas como resultados.

**Causa probable, declarada como tal:** `0xC0000142` es un fallo de inicialización de
proceso, no un error de Tesseract; la tanda D 400 corrió con el testigo de proceso a
**×3,60** y la anterior a ×12,54, con cuatro agentes más activos. **Reintentado una vez**
(§6.4). Regla de los dos intentos: consumido uno.

### 6.2 Casi atribuyo al `pHYs` un efecto que era una caída

Directamente ligado al anterior: la primera lectura de la tabla D decía *«declarar 400
ppp sobre `d4f` lleva los tres `--psm` de 2,35 % a silencio total, y eso es el 99,8 % de
la varianza del documento»*. **Era mentira**: eran las cinco caídas. **Lo atrapó mirar
`rc`, no mirar el CER.**

### 6.3 El argmin sin marcar es una trampa — y casi me come el resultado principal

En la tanda A, el mejor `--psm` de `d3` sale `psm 8/10/13` con 98,73 %, y el de `d4e`
sale `psm 9` con 99,83 %. **No son buenos modos: son los que devuelven 2 bytes.** Con
una referencia de 79 caracteres, escupir dos caracteres puntúa mejor que escupir
doscientos equivocados. **Está marcado con ‡ en todas las tablas** y esos dos
documentos quedan fuera de toda conclusión sobre «cuál es el mejor `--psm`». Es la
misma marca que M1 tuvo que poner en `k-por-motor.md` §2.1.

**Y no era cosmético.** Con los seis documentos dentro, el arrepentimiento decía que
**el defecto `psm 3` era el mejor de los doce modos** (12,43). Con los dos ‡ fuera,
`psm 3` pasa a **18,29** y `psm 11` a **3,77**: **la conclusión se invierte** (§2.1).
La causa es que en `d3` y `d4e` el oráculo es un modo que devuelve **dos bytes**, de
modo que **el silencio puntúa y la alucinación penaliza 88 puntos** — nada de lo cual
mide qué modo lee mejor. **Un arrepentimiento sobre una población que incluye
documentos ilegibles no es un arrepentimiento: es un premio a la timidez.** Es la misma
lección que a M1 le costó excluir `patologico_escaneado`, y aquí llegó a cambiar el
signo del resultado.

### 6.4 El reintento, y el tope del testigo disparando por primera vez

**La tanda D 400 se repitió entera, una vez.** Resultado: **18 de 18 celdas, las 18
deterministas y las 18 con `rc = 0`.** Las cinco caídas no se reproducen y las cifras
que dejan **no tienen nada de particular**: `d4f` a 400 ppp declarados da 2,35 / 6,04 /
2,68, exactamente lo mismo que no declarar. **La caída era de la máquina, no del
parámetro.**

Y el reintento dejó el otro dato: **el testigo de proceso agotó su tope de 20 s**
(`testigo_topado = true`, nivel ×750 sobre el reposo). **Es la primera vez que ese tope
dispara en el proyecto**, y es la prueba de que la regla de `CLAUDE.md` §3 —*«ponle tope
al propio testigo: un testigo que puede tumbar la medición no es un testigo»*— estaba
bien puesta: sin él, esa tanda habría gastado hasta 300 s midiendo el ruido.

**Regla de los dos intentos: consumido uno, no hizo falta el segundo.**

### 6.5 Lo que no se midió

- **No se sondeó qué `--psm` usa el Tesseract embebido en Ghostscript.** Es lo único
  que cerraría del todo el pendiente 7 de `invocacion-aristas.md`, y sigue **PENDIENTE**.
- **No se midió el Tesseract del contenedor** (`filex-c13`, Debian, `tesseract-ocr-spa`).
  Todo esto es el nativo de Windows con el `tessdata` de PDFgear.
- **No se barrió el `--oem`** (motor LSTM / legacy / combinado), que es el otro
  parámetro estructural de Tesseract y que aquí quedó al defecto en las 547 celdas.
- **No se midió el efecto del `pHYs` sobre PaddleOCR, RapidOCR ni EasyOCR.** Si vale
  33 puntos en Tesseract, hay que comprobar si vale algo en los demás — y **todo el
  corpus de este proyecto está rasterizado con la variante `im`, es decir, sin declarar
  resolución.**

---

## 7. Qué cambia en la regla del adaptador

**Lo que NO cambia:** la unidad sigue siendo un **factor sobre el ráster nativo**; la
elección sigue viviendo en el **adaptador del motor**; el `k` sigue fijándose por
**mínimo arrepentimiento sobre ≥4 documentos** y publicándose **con su
arrepentimiento**, como estableció M1.

**Lo que cambia:**

```
# R1 revisada por B17/B18/B14 — el adaptador de Tesseract tiene TRES parametros,
# no uno, y los tres van juntos porque interactuan (bench/psm-y-rasterizador.md §3).
#
# 1) EL RASTER TIENE QUE DECLARAR SU RESOLUCION VERDADERA. Gratis, hasta 33,22 puntos.
#    magick:      ... -units PixelsPerInch -density <ppp>     <-- IMPRESCINDIBLE
#    ghostscript: -sDEVICE=pnggray -r<ppp>                    <-- ya lo hace solo
#    Con que rasterizar da EXACTAMENTE IGUAL: los 42 pares medidos son identicos
#    pixel a pixel. Lo que no da igual es el chunk pHYs.
#    El valor tiene que ser el REAL: declarar uno falso empeora en 11 de 93 celdas
#    y multiplica por 6 el CER de escaneado_d4c. Declarar el verdadero: 0 de 15.
#    VERIFICAR: pHYs presente, unidad=1 y valor == ppp de renderizado. Son 9 bytes
#    de cabecera, leidos en proceso.
#
# 2) EL `--psm` NO PUEDE QUEDAR AL DEFECTO, y es del PAR (motor, documento).
#    K_PSM = {                      # k de minimo arrepentimiento DENTRO de cada psm,
#        "psm3":  (0.875, 0.93),    #   3 documentos DISCRIMINANTES (d2, d4, d4c),
#        "psm4":  (0.875, 0.93),    #   resolucion declarada. Con d3 dentro cambia
#        "psm6":  (0.625, 1.93),    #   el de psm11 a x0.75 (bench/... §6.3).
#        "psm11": (0.875, 1.99),    # <- psm6 es el que lee escaneado_d2 a CERO
#        "psm12": (0.875, 1.99),
#    }
#    Mejor par fijo: (psm 11, x0.875), arrepentimiento 3.00.
#    El defecto puro (psm 3, x1.00) tiene arrepentimiento 10.38.
#    Y el arrepentimiento se publica CON la poblacion sobre la que se midio y CON
#    los documentos ilegibles EXCLUIDOS: incluirlos premia al modo mas callado y
#    llego a invertir cual es el mejor `--psm` de los doce.
#
# 3) UN `k` SIN SU `--psm` NO SIGNIFICA NADA, Y AL REVES TAMPOCO.
#    - El psm ganador cambia con k en 4 de 4 documentos.
#    - El k optimo cambia con el psm en 4 de 4 documentos.
#    - La interaccion se lleva del 13,7 % al 41,2 % de la varianza del CER.
#    Por tanto: publicar SIEMPRE la terna (psm, k, resolucion_declarada). Un numero
#    de esa terna medido con otro valor de los otros dos NO es transferible.
#
# 4) Y SI EL DOCUMENTO SE PUEDE PROBAR DOS VECES, PRUEBALO.
#    psm 3 y psm 6 cuestan ~0,5 s cada uno en CPU sobre un folio de 2,2 Mpx y sus
#    fallos son DISJUNTOS: psm 3 devuelve 0 bytes donde psm 6 devuelve 113 %, y
#    psm 6 lee a 0,00 % donde psm 3 da 30,38 %. Un segundo intento con otro psm es
#    la mejor relacion coste/beneficio que hay en este adaptador — y el criterio
#    para quedarse con uno u otro NO puede ser rc=0: los dos devuelven rc=0.
```

| | regla vigente | regla propuesta | apoyo |
|---|---|---|---|
| resolución del ráster | no se menciona | **declarar la verdadera, y verificarla** | §4.3: 126 de 126; §4.5: 0 de 15 peor |
| con qué rasterizar | «declarar el rasterizador» (M1) | **da igual — está medido que da igual** | §4.1: 42 pares idénticos |
| `--psm` | no se menciona | **explícito, del par, con su `k`** | §2.1, §3 |
| `k` de Tesseract | ×0,875 (`psm 3`) / ×0,75 (`psm 11`) | ×0,875 (`3`) **·  ×0,875 (`11`)** · **×0,625 (`6`)** | §5.3 |
| población del arrepentimiento | ≥4 documentos | **≥4 documentos que el motor LEA** | §6.3: incluir ilegibles invirtió el resultado |
| qué se publica | `k` + arrepentimiento | **la terna `(psm, k, ppp declarados)`** | §3.4 |

---

## 8. Reglas del encargo, cumplidas

| regla | estado |
|---|---|
| Escribir **solo** en `bench/psm-y-rasterizador.md` y `bench/salidas-psm/**` | **Cumplida.** Ni `filex/`, ni `bench/scripts/`, ni ningún `.md` maestro, ni los directorios de otros agentes |
| No hacer `git add` ni `git commit` | **Cumplida.** Nada versionado |
| **No usar la GPU ni tomar el lock** | **Cumplida.** Todo en CPU: Tesseract, `magick` y `gswin64c`. El lock no se tocó |
| Arneses compartidos, copiados y no modificados | **Cumplida.** `ocr_eval.py`, `mcp_probe*.py` y todo `bench/salidas-corpus-d4/`, `salidas-ppp-norm/` y `salidas-k-motor/`, intactos. Las copias llevan su `sha256` |
| `bench/salidas-referencia/referencia.json` solo de lectura | **Cumplida.** Ni abierto |
| Decir **qué evaluador acentuado** se usa | **Cumplida.** `bench/salidas-corpus-d4/ocr_eval_d4.py`, copia byte a byte verificada por `sha256` |
| Reportar las dos lecturas, con y sin acentos | **Cumplida.** `json/resumen.json` lleva las 547 celdas en `acentos` y `ascii` |
| Documentos con referencia larga | **Cumplida.** Cuatro de los seis usan la referencia de 610 caracteres; `d2` y `d3` usan la de 79 y **están marcados ‡ donde cuantizan** |
| No usar `patologico_escaneado` | **Cumplida.** No se ha abierto |
| No sobremuestrear | **Cumplida.** ppp nativos leídos con `pypdfium2`; `d2`/`d3` barren desde **50 ppp** |
| Informar también en píxeles | **Cumplida.** Las 133 rasterizaciones, con píxeles y Mpx, en el `MANIFIESTO.md` |
| Medianas de n≥9 | **Cumplida** en las 547 celdas. Las dos sondas de diagnóstico son n=1 y están declaradas como sondas |
| **Los dos testigos**, con **tope al testigo** | **Cumplida.** Tope de 20 s; `testigo_topado=false` en las once tandas. **Y el de proceso volvió a atrapar tres tandas que el monohilo declaró limpias** |
| Sondear en ejecución, no deducir | **Cumplida.** El mecanismo del `pHYs` se leyó del `stderr` del motor y se probó **cambiando la variable** en los dos sentidos |
| Timeouts explícitos | **Cumplida.** `timeout` en las 11 invocaciones de tanda, `timeout=600` en cada llamada a `tesseract`, `magick` y `gs`, `stdin=DEVNULL` en todas |
| Lista blanca de idioma | **Cumplida** (`CLAUDE.md` trampa 18), y también de `--psm` |
| Dos intentos por problema | **Cumplida.** §6.1 y §6.4 |
| No generar código Python con heredocs | **Cumplida** (`CLAUDE.md` trampa 19, ampliada por M1). Los seis scripts se escribieron con la herramienta de escritura |
| Borrar los binarios, dejar `MANIFIESTO.md` | **Cumplida.** Ver `bench/salidas-psm/MANIFIESTO.md` |

---

## 9. Lo que queda PENDIENTE

- **El `--oem` no se ha tocado.** Es el otro parámetro estructural de Tesseract y las
  547 celdas lo dejan al defecto. Si el `--psm` mueve 21–42 puntos, hay que mirarlo.
- **Los seis documentos son sintéticos y comparten generador.** Es la misma limitación
  que declaró M1: `escaneado_d2` y `d3` salen de `gen_corpus_ocr.sh`, los cuatro `d4*`
  de `gen_corpus_d4.py`. **B12 (degradación realista) sigue siendo el pendiente que más
  ampliaría esta medida** — y G3 ya trae corpus nuevo.
- **El efecto del `pHYs` sólo está medido con Tesseract.** Todo el corpus del proyecto
  está rasterizado sin declarar resolución: si PaddleOCR, RapidOCR o EasyOCR miran el
  metadato, **hay tablas que rehacer**. Es barato de comprobar y no está hecho.
- **Qué `--psm` usa el Tesseract embebido en Ghostscript** sigue sin sondear.
- **La estrategia de dos intentos con `--psm` disjuntos (§7, punto 4) está propuesta y
  no medida.** Falta el criterio de selección entre las dos salidas, que no puede ser
  `rc` ni longitud a secas: `psm 5` sobre `d4e` devuelve 2 377 bytes de basura.
- **La comprobación cruzada con G3 está a medias.** G3 llegó al mismo mecanismo del
  `pHYs` por su cuenta y con otro corpus, y aporta un caso —`realista_d5e` con `psm 3`,
  donde declarar **empeora 15,44 puntos**— que mis dos condiciones acotan pero **no
  explican con certeza**: no sé a qué ppp está ese documento ni si su ráster estaba
  remuestreado. **Cerrarlo es una sola tanda y no está hecha.**
- **`escaneado_d3` no lo lee nadie**: el mejor de las 55 celdas es 68,35 %. Como
  documento de barrido de `--psm` **aporta poco**, igual que `patologico_escaneado`
  aportaba poco al `k`. **Elegir documentos para barrer un parámetro exige que estén en
  la zona de degradación de ESE parámetro, y eso no se sabe hasta después de medir.**

---

## 10. Ficheros

Todo en **`bench/salidas-psm/`**, con `MANIFIESTO.md`:

| fichero | qué es |
|---|---|
| `ocr_eval_d4.py`, `d4_texto.py` | **copias byte a byte** de `bench/salidas-corpus-d4/`. Se importan, no se modifican |
| `ocr_eval_psm.py` | copia byte a byte de `ocr_eval_km.py` (envoltorio de M1/P1) |
| `raster_psm.py` | rasterizado por factor con **nueve variantes de rasterizador** |
| `tess_psm.py` | el arnés: `--psm` como eje, `TESS_DPI` como eje, dos testigos con tope |
| `sonda_raster.py` | la comparación de **píxeles** entre variantes (§4.1) |
| `sonda_phys.py` | el censo de `pHYs`, `stderr` y clases de equivalencia (§4.2-4.3) |
| `tablas_psm.py` → `tablas.md` | las rejillas, los argmin, el arrepentimiento y las descomposiciones de varianza |
| `run_bcd.sh` | las tandas B, C y D en serie |
| `manifiesto_psm.py` → `MANIFIESTO.md` | genera el manifiesto y **borra** las 133 rasterizaciones (120,1 MB) |
| `json/`, `texto/`, `logs/` | resultados por celda (547), la salida literal de OCR de cada celda y el registro completo de las once tandas y las dos sondas |
