# B7 y B20 — una heurística de degradación severa, y el residuo de B12

worker1, carril GPU, ronda 10, `edicius2002/filex-gpu`. Rama al día con `main`
(`8ec82ed`), ronda 8 fusionada. **Todo MEDIDO salvo donde se marca `INFERIDO` o
`PENDIENTE`.**

- Datos crudos: `bench/salidas-severidad-y-curvatura/json/*.json`
- Instrumentos: `b7_heuristica.py`, `b7_tiempo.py`, `b8_psm_sweep_deskew.py`,
  `repro_abl_r5_sinonda.py`, `b20_psm_sweep.py` (todos reproducibles, ver
  `MANIFIESTO.md`)

---

## 1 · B7 — la heurística de degradación severa

### 1.1 El dataset: nada nuevo, dos fuentes ya medidas combinadas

No se repite ninguna celda. `b7_heuristica.py` combina:

- **72 celdas** de `bench/psm-y-rasterizador.md` §2.1 (n=9, deterministas): 12
  `--psm` de Tesseract × 6 documentos (`d2`, `d3`, `d4`, `d4c`, `d4e`, `d4f`),
  con CER y bytes de cada celda ya publicados. Esta tabla **ya contiene**, con
  `rc=0` en las tres, las tres patologías de la trampa 25: silencio (0 B),
  cuenta atómica (2-25 B) y alucinación (hasta 2 377 B).
- **40 celdas propias** de la ronda 8 (`b8_tesseract.json` + `b8_rapidocr.json`):
  la familia `d4` (200/280 ppp, base/deskew) con **dos motores** sobre **los
  mismos 20 rásteres** — la variable de motor que este encargo pide.

112 celdas en total, referencia conocida por documento (79 caracteres para
`d2`/`d3`, 610 para la familia `d4`, trampa 9).

### 1.2 La señal candidata

```
razon = bytes_salida / bytes_referencia
```

No usa nada interno del motor: sirve igual para Tesseract (con `--psm` de
salida) y para RapidOCR (que no tiene `--psm`). Se calibra aquí contra la
referencia **conocida** — la misma práctica que ya usó este proyecto para R1,
R6 y `k` antes de convertirlos en regla de adaptador (calibrar con verdad
conocida, y resolver el proxy sin verdad conocida como un problema aparte,
ver §1.5).

### 1.3 ¿Existe el umbral? — MEDIDO: sí, y son DOS, con hueco limpio

Antes de elegir un valor, se tabula qué separa cada corte (trampa 51). Con las
112 celdas ordenadas por `razon`:

| clase | n | rango de `razon` |
|---|---:|---|
| **SILENCIO** (0 B) | 19 | `0,000` |
| **ATÓMICA** (2-25 B, CER≥90) | 25 | `0,003 – 0,041` |
| — **hueco limpio** — | 0 | `0,041 – 0,118` (anchura 0,077) |
| **NORMAL/DEGRADADO** | 60 | `0,118 – 1,152` |
| — **hueco limpio** — | 0 | `1,152 – 1,683` (anchura 0,531) |
| **ALUCINACIÓN** | 8 | `1,683 – 3,897` |

**Los dos huecos SÍ existen** y ninguno de los 112 puntos cae dentro de
ninguno de los dos: no hace falta elegir un valor «generoso», cualquier corte
dentro de `[0,041 ; 0,118]` y dentro de `[1,152 ; 1,683]` separa exactamente
las mismas celdas. Ejemplo de regla: `razon < 0,08` o `razon > 1,4` → marcar
para reintento con otro motor.

### 1.4 Lo que la señal NO separa — MEDIDO, y es la mitad honesta

Dentro de la banda «NORMAL/DEGRADADO» (0,118 a 1,152) el CER va de **0,00 % a
91,60 %**. La señal está construida sobre CANTIDAD de salida, no sobre su
CORRECCIÓN, y eso es exactamente lo que se puede esperar de un conteo de
bytes: `d4` con `psm 1/3/4` da 107 B (17,5 % de la referencia) con 84,56 % de
CER — una lectura mala mala pero de longitud «plausible», indistinguible por
esta señal de una lectura excelente de 610 B. **La señal cierra dos de las
tres patologías del R3 original (inanición y alucinación) y es ciega a la
tercera (contenido incorrecto de longitud plausible).**

### 1.5 Variar el MOTOR rompe el hallazgo — MEDIDO (trampa 78, otra vez)

Las **20 celdas de RapidOCR caen las 20 en la banda NORMAL/DEGRADADO**
(`razon` 0,120 a 1,056), **con CER de 0,2 % a 88,6 %**. Es decir: **la señal
nunca dispara para RapidOCR en este dataset**, ni siquiera en su peor caso
(`escaneado_d4e`, 49,7-88,6 % de CER) — porque RapidOCR, a diferencia de
Tesseract, **nunca produce silencio ni cuenta atómica ni alucinación en esta
familia**: cuando lee mal, produce un texto de longitud parecida a la
correcta pero equivocado. **La heurística calibrada sobre las patologías de
Tesseract es ciega al modo de fallo de RapidOCR entero.** Es la misma forma
que el hallazgo de `-deskew` en la ronda 8: una señal calibrada con un solo
motor describe a ese motor.

**Consecuencia de diseño:** esta señal sirve como **red de seguridad barata**
(atrapa inanición y alucinación en cualquier motor que las produzca, a coste
de una resta y una división) pero **no sustituye** a una señal de calidad de
contenido — el R3 original («cómo detectar degradación severa para disparar
el segundo motor») sigue sin una respuesta que cubra el caso de RapidOCR, y
sigue **PENDIENTE**.

### 1.6 El proxy sin verdad conocida — PENDIENTE, declarado y no fingido

`bytes_referencia` aquí es conocido porque el corpus es de calibración. En
producción no hay referencia. La familia de proxys que ya tiene precedente en
el proyecto es «cajas detectadas» (`corpus-d4.md` §7.6, `cajas-rapidocr.md`):
número/área de cajas que devuelve el propio detector, estable en ~12 cajas y
~20 % de área de página en los documentos legibles de esta familia. **No se
ha probado aquí** si sustituir `bytes_referencia` por una función de las
cajas detectadas conserva los dos huecos de §1.3 — es la mitad de ingeniería
que falta antes de llevar esto a un adaptador, y se declara así en vez de
suponerlo.

### 1.7 El tiempo como señal candidata — MEDIDO: no se sostiene en esta vía

Se midió el tiempo de Tesseract (`--psm 3`) sobre los 20 rásteres de la
familia `d4` de la ronda 8, en una sola tanda (n=5 por celda, dos testigos de
ruido: deriva ×1,00, nivel ×1,45 sobre el umbral de referencia — etiquetada
`limpia`, aunque la CPU rondaba 75-83 % por el carril CPU en paralelo).

**El signo no es el esperable, y es inconsistente.** De las 4 celdas
catastróficas de la ronda 8 (silencio con `-deskew`), **3 de 4 son MÁS
RÁPIDAS que su par sin deskear**, no más lentas:

| documento | ppp | base (ms, mediana n=5) | deskew=silencio (ms, mediana n=5) | razón deskew/base |
|---|---:|---:|---:|---:|
| `escaneado_d4` | 200 | 466,0 | 304,6 | **0,65** |
| `escaneado_d4` | 280 | 587,4 | 628,9 | 1,07 |
| `escaneado_d4c` | 200 | 534,8 | 327,4 | **0,61** |
| `escaneado_d4c` | 280 | 1173,8 | 834,7 | **0,71** |
| `escaneado_d4e` | 200 | 880,8 (silencio) | 287,3 (silencio) | **0,33** |
| `escaneado_d4e` | 280 | 1665,2 (silencio) | 579,0 (silencio) | **0,35** |

**Tesseract no tarda más en fallar: tarda MENOS** — parece rendirse antes
cuando el análisis de maquetación no encuentra nada que segmentar, el efecto
contrario al `d3`/`d2` ×4,5 citado en el encargo. **Esa cifra es de
Ghostscript (`-sDEVICE=ocr`), un camino de código distinto** (motor
compilado dentro de `gsdll64.dll`, sin el mismo analizador de página que el
binario `tesseract.exe`): no se refuta, **no se transfiere**. Y hay un
segundo problema, más de fondo: la variación DENTRO de una misma celda llega
a ×2,3 (`escaneado_d4b`@280 base: 656-1517 ms en 5 repeticiones) con la CPU
compartida — **el tiempo, en esta máquina y ahora mismo, no tiene el suelo de
ruido necesario para ser una señal fiable**, ni siquiera como razón dentro de
la tanda. **Se descarta el tiempo como señal de severidad para este
adaptador.**

### 1.8 Regla propuesta para B7

```
razon = bytes_salida / bytes_esperados   (bytes_esperados: PENDIENTE de definir
                                           sin verdad conocida, ver §1.6)
severo_por_cantidad = razon < 0.08 or razon > 1.4
```

**Esto es necesario pero no suficiente**: atrapa inanición y alucinación en
cualquier motor (§1.3), es ciego a contenido incorrecto de longitud plausible
y en particular al modo de fallo entero de RapidOCR (§1.5), y depende de un
proxy de `bytes_esperados` que no está resuelto (§1.6). El tiempo no aporta
nada aquí (§1.7).

---

## 2 · B20 — el residuo de B12: la ablación con un tercer `--psm`, y el límite del instrumento

### 2.1 La ablación, con `psm 6` añadido — MEDIDO, reproducción bit a bit

`corpus-d5.md` §5.1 mide `realista_d5` (onda=20) contra `abl_r5_sinonda`
(mismos parámetros, onda=0) sólo con `psm 3` y `psm 11`. Reproducido aquí
`abl_r5_sinonda` importando `gen_corpus_d5.py` sin tocarlo (JPEG intermedio
**idéntico bit a bit**, `sha256` `64b3a792…`, el PDF difiere sólo por el
`/CreationDate` que estampa `magick`, trampa 22) y añadido `psm 6` — la
tercera clase real de comportamiento de Tesseract (`k-oem-acantilados.md`
§B24: auto-layout≡3, bloque único=6, disperso≡11):

| `--psm` | `realista_d5` (onda 20) | `abl_r5_sinonda` (onda 0) | Δ (quitar la onda) |
|---|---:|---:|---:|
| 3 (auto-layout) | 31,71 | 89,77 | **+58,06** (empeora) |
| **6 (bloque único, nuevo)** | 30,03 | 43,96 | **+13,93** (empeora) |
| 11 (disperso) | 27,01 | 21,14 | **−5,87** (mejora) |

Los valores de `psm 3` y `psm 11` **reproducen exactos** los publicados
(31,71/89,77 y 27,01/21,14): la tanda es fiable.

**El «sale al revés» NO es exclusivo de `psm 3`: lo comparten 2 de las 3
clases reales.** `psm 6`, una clase de comportamiento distinta (siempre peor
que las otras dos, `k-oem-acantilados.md`), **también empeora** al quitar la
curvatura, aunque menos (+13,93 frente a +58,06). Sólo `psm 11` (texto
disperso) mejora. **La formulación correcta no es «es cosa de `psm 3`»: es
«en 2 de las 3 clases reales, quitar la curvatura empeora la lectura, y sólo
la clase de texto disperso se benefícia»** — más matizado que ambas lecturas
extremas («es del documento» o «es sólo de un `--psm`»).

### 2.2 El límite del instrumento — MEDIDO por derivación, no por cita

`corpus-d5.md` §5 dice que la sonda de curvatura «satura por encima de ~3,5°
de giro y con polvo ≥0,35», y que eso es del INSTRUMENTO, no del objeto —
correcto, y aquí se verifica el mecanismo con los parámetros exactos del
propio código en vez de repetir la cifra aproximada.

`sonda_degradacion.py` busca el desplazamiento entre franjas verticales con
`for lag in range(-60, 61)`: una ventana de búsqueda de **±60 px**, sobre
franjas separadas `xs = [120 … 1020]`, un recorrido horizontal de **900 px**.
El propio comentario del código ya medía «a −4° y 900 px de recorrido son
63 px» de desplazamiento lineal por el giro — por encima de la ventana. El
ángulo exacto en el que el desplazamiento por GIRO (no por curvatura) iguala
la ventana de búsqueda es:

```
θ_saturación = arctan(60 / 900) ≈ 3,81°
```

**Esto no es una medida del objeto: es el punto donde la ventana de búsqueda
del instrumento deja de contener la respuesta**, derivado de sus propios
parámetros (`±60`, recorrido `900`). Afina el «~3,5°» ya publicado (que era
una cita aproximada) a un valor exacto y explica POR QUÉ ese es el límite,
no sólo QUE lo es. El límite de polvo (≥0,35, «la correlación se engancha a
la iluminación, no al renglón») es un fallo de robustez frente a ruido de la
misma sonda, cualitativo, y no se remide aquí — se mantiene como estaba,
etiquetado como límite del instrumento.

### 2.3 Qué es del objeto y qué es del instrumento, declarado celda a celda

| documento | columna «curvatura (residuo)» | qué es |
|---|---|---|
| `realista_d5{,a,b,e}` | 1,9 – 7,3 px | **del objeto** — dentro de la ventana (giros de −0,52° a −2,14°, ≪ 3,81°) |
| `abl_r5_sinonda` (control) | 0,4 px | **del objeto** — confirma que sin onda no hay curvatura falsa |
| `patologico_d5` (polvo 0,35) | — | **del instrumento** — la correlación se engancha al ruido, no al renglón |
| `escaneado_d4` (±4°) | — | **del instrumento** — 4° > 3,81°, el giro por sí solo excede la ventana de búsqueda |

**Ninguna fila de `patologico_*` ni `escaneado_d4` en esa columna es medida**,
tal y como ya declaraba `corpus-d5.md` — aquí queda además **por qué**, no
sólo que sea así.

---

## 3 · Si sobró tiempo — la mitad de B8: barrido de `--psm`

**Cerrado.** Las 4 celdas catastróficas de la ronda 8 (`escaneado_d4`/`d4c` ×
200/280 ppp, `-deskew`, silencio con `psm 3`) se repitieron con `psm 6` y
`psm 11` sobre los mismos rásteres: **las 12 celdas (4 documentos × 3 `--psm`)
dan 0 bytes, `rc=0`.** No es «cosa de `psm 3`»: **es Tesseract en general
sobre estos rásteres deskeados**, en las tres clases reales de
comportamiento. Cierra el `PENDIENTE` de la ronda 8 sin ambigüedad.

**No abordado — declarado, no fingido:** construir corpus para los tres
casos de R1 sin representante (varias imágenes, imagen parcial,
texto+escaneo mezclados). Sigue exactamente como quedó en la ronda 8: **21 de
23 PDF son «una sola imagen a página completa», 0 representan los otros
tres.** Es trabajo de corpus nuevo y no cupo en esta ronda.

---

## 4 · Estado de la máquina y las cuatro declaraciones

- **Intérprete**: `.venv-mcp-filex` (Windows, Python 3.11.9) para lo que
  toca `filex`/evaluación; `.venv-ai` (Windows, Python, pypdfium2, torch
  2.6.0+cu124) para `geometria()` (pypdfium2) y para regenerar
  `abl_r5_sinonda`. Ninguna parte de esta ronda tocó la GPU: `B7` y `B20`
  son CPU pura (Tesseract, ImageMagick, Ghostscript vía `gen_corpus_d5.py`) —
  **no se tomó el lock de GPU**, no hacía falta.
- **Entorno**: worker2 corría en paralelo el carril CPU de la ronda 10
  (`N9`/`C5`/`C35`/`C36`); la CPU osciló 62-96 % durante esta sesión. Se
  declara con cada medida de tiempo (§1.7); no afecta a `razon` ni al barrido
  de `--psm` (deterministas, no sensibles al reloj). Docker no se usó esta
  ronda (ningún bloque lo necesita).
  Ni `filex/verificador.py`, `filex/motores.py`, `filex/api.py`,
  `filex/nucleo.py`, `filex/huella.py`, `filex/sondeo.py` (de worker2) se
  tocaron.
- **Qué quedó fuera**: el proxy de `bytes_esperados` sin verdad conocida
  (§1.6, PENDIENTE); una señal de severidad que cubra el modo de fallo de
  RapidOCR (§1.5, PENDIENTE — sigue siendo la pregunta original de R3); el
  límite de polvo de la sonda de curvatura no se re-verificó por derivación
  (§2.2, se mantiene como estaba); construir corpus para los tres casos de
  R1 sin representante (§3, declarado, no intentado).
- **No se generó ningún `bench/salidas-*` sin `MANIFIESTO.md`** ni sin
  `git add`; los rásteres regenerables (`img/`, `tmp/` de esta sesión) van al
  `.gitignore` con el comentario que dice qué los reproduce.

## 5 · Verificación

- `ci/integridad.py`: **`Todo en orden`** (`.venv-mcp-filex`, Python 3.11.9).
  Se registró este informe y se corrigió el recuento de emojis de
  `ESTADO-Y-REPARTO.md` tras mover `B20` (🔴→🟢): `6 ⚫ · 10 🔴 · 10 🟡 · 91 🟢` →
  `6 ⚫ · 9 🔴 · 10 🟡 · 92 🟢` (`B7` se queda en 🟡, sin cambio de color).
- `pytest pruebas/ -q`: **454 passed, 3 skipped, 0 failed, 127 subtests** en
  241,3 s (`.venv-mcp-filex`, Windows, Python 3.11.9). **CPU compartida con el
  carril CPU de worker2 durante toda la corrida (75-100 %, hasta 28 procesos
  Python simultáneos)** — a diferencia de la ronda 8, esta vez **0 fallos por
  contención** (trampa 101: la contención hace más lenta la tanda, 241 s
  frente a los ~160 s de una máquina tranquila, pero no siempre produce
  fallos — sólo los hace más probables).

## 6 · Ficheros de esta sesión

Todo en `bench/salidas-severidad-y-curvatura/`, con `MANIFIESTO.md`:
`repro_abl_r5_sinonda.py`, `b20_psm_sweep.py`, `b7_heuristica.py`,
`b7_tiempo.py`, `b8_psm_sweep_deskew.py`, `json/*.json`, `texto/*.txt`.

**Commiteado en `edicius2002/filex-gpu`. No se ha empujado ni abierto PR.**
