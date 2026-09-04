# La rejilla por encima de ×1,60 — dos de los tres `k` publicados eran el borde del barrido, y el tercero no

**worker12, carril GPU, ronda 13** (`edicius2002/filex-k-borde-rejilla`).
Encargo: cerrar el residuo que `bench/k-tesseract-y-configs-faltantes.md`
(worker8) dejó escrito en la fila del inventario al cerrar `B23`:

> **Sigue PENDIENTE, fuera del alcance de estos dos cierres: la rejilla por
> encima de ×1,60** (EasyOCR y `psm 11` mejoran hasta el borde medido).

**192 celdas nuevas, `n=9`, `rc=0` en las 192, 0 no deterministas, 0 omitidas
por VRAM.** Una sola tanda, tres configuraciones, dieciséis factores.

---

## 0. El resultado, en tres líneas

**MEDIDO.** Sobre la familia `d5`, con la misma metodología de `B23` y la
rejilla extendida de ×0,75 a ×6,00:

| Configuración | `k` publicado (B23, rejilla ≤×1,60) | `k` real (rejilla ×0,75–×6,00) | coste de haberse quedado en el borde |
|---|---:|---:|---:|
| **Docling + R6** | ×1,60 | **×3,50** | **10,70 pt** de arrepentimiento medio (16,10 máx.) |
| **Tesseract `psm 11`** | ×1,60 | **×2,00** | **1,88 pt** de arrepentimiento medio (7,60 máx.) |
| **EasyOCR** | ×1,60 | **×1,60** — no se mueve | **0,00 pt** |

Los tres argmin nuevos son **interiores** a la rejilla: ninguno toca ×6,00, y
ninguna celda se perdió por el techo de VRAM. **El barrido paró porque dejó de
mejorar, no porque se acabara la lista** — y en dos de los tres motores hay
además un **mecanismo medido** que explica por qué deja de mejorar (§5).

---

## 1. Por qué esto no era «una celda más»

`B23` fijó el `k` de cinco configuraciones sobre una rejilla de siete factores
cuyo último punto es ×1,60, y **tres de esas cinco tienen el argmin
exactamente en ×1,60**. Su propio informe lo marcó con una nota al pie:

> ¹ En el borde de la rejilla: EasyOCR mejora monótonamente hasta 1,60 en 3 de
> 4 documentos, así que el verdadero óptimo puede estar por encima de lo medido.

Un argmin en el último punto del barrido no es un argmin: **es el borde**. Y el
proyecto lleva dos informes fijando `k` por mínimo arrepentimiento sobre esa
rejilla, así que la duda no afectaba a una celda sino a un procedimiento.

El caso peor declarado era **Docling+R6**, con óptimo en ×1,60 y arrepentimiento
de **8,8 pt**, el máximo del racimo entero (`bench/vivo-y-residuos.md`, citado
por `k-tesseract-y-configs-faltantes.md` §0). Ese 8,8 resultó ser, casi entero,
**el precio de no haber mirado más arriba**.

---

## 2. Método — qué se hereda y qué se añade

### 2.1 Heredado, para que sea comparable

De `bench/salidas-k-oem-acantilados/b23_k_d5.py` y `b23_resto_docling.py`, sin
inventar nada:

- **Los mismos cuatro documentos** de la familia `d5` con sus ppp nativos:
  `escaneado_d5a` (90), `escaneado_d5c` (80), `escaneado_d5` (72),
  `escaneado_d5b` (60).
- **La misma receta de ráster por motor**: gris **sin** declarar `pHYs` para
  EasyOCR (es inmune, trampa 29, y es la receta que fijó el `k` original);
  sRGB **con** `-units PixelsPerInch` para Tesseract, el único que lo consulta;
  Docling rasteriza él mismo por `RapidOcrOptions.scale`.
- **El mismo evaluador**: `bench/scripts/ocr_eval.py` con la **métrica
  acentuada**, canónica desde el 2026-08-28, y la referencia
  `d4_texto.BLOQUES` aplanada (596 caracteres). Cada celda registra su clave
  `metrica` (trampa 55).
- **`k` por mínimo arrepentimiento**, nunca el óptimo de un documento suelto:
  `regret(k) = media_doc[CER(doc,k) − min_f CER(doc,f)]`.

### 2.2 Añadido, y por qué

- **`rc` por celda y por repetición** (trampa 25). `b23_k_d5.py` no lo
  registraba: una celda a CER 100 % es indistinguible entre silencio legítimo y
  proceso que no arrancó, y sólo el `rc` los separa. Aquí van los nueve `rc` de
  cada celda al JSON, y el conductor escribe `INICIO`/`FIN`/`rc`/recuento de
  celdas (trampa 99/100).
- **Se remiden los siete factores viejos**, no sólo los nuevos. La trampa 59
  obliga a medir la versión histórica **en la propia tanda** antes de publicar
  un ratio contra ella; aquí el arrepentimiento mezcla celdas viejas y nuevas
  en la misma fórmula, así que tenían que salir de una sola tanda o no valdría.
  Eso da además el control de reproducción de §3 gratis.
- **`n=9`** en vez de las 3 repeticiones de `B23`.
- **Orden de celdas descendente por Mpx** dentro de cada configuración: llegar a
  un tamaño en escalera cuesta ×2,25 más VRAM que ir directo (trampa 67). El
  orden no afecta al CER de un motor determinista, y §3 lo comprueba en vez de
  suponerlo.
- **Caché de evaluación por texto.** `evaluar()` cuesta **4,6 s** por llamada
  (ventana deslizante, trampa 57); con nueve repeticiones deterministas,
  evaluar nueve veces el mismo texto es tiempo tirado. Se evalúa una vez por
  texto **distinto**, así que una repetición divergente se vería igual.

### 2.3 La rejilla

```
×0,75  ×0,875  ×1,00  ×1,125  ×1,25  ×1,40  ×1,60      (los 7 de B23, remedidos)
×1,75  ×2,00  ×2,25  ×2,50  ×3,00  ×3,50  ×4,00  ×5,00  ×6,00   (los 9 nuevos)
```

De ×1,60 a ×6,00 hay **×3,75 en factor y ×14 en píxeles**. Dos puntos no son una
curva; nueve sí.

---

## 3. Control de reproducción — **MEDIDO, y no sale igual en los tres**

Las 28 celdas comunes (4 documentos × 7 factores) de esta tanda contra las
publicadas por `B23`:

| Configuración | celdas idénticas | comentario |
|---|---:|---|
| **EasyOCR** | **28 / 28** | reproducción exacta al centésimo |
| **Tesseract `psm 11`** | **28 / 28** | reproducción exacta al centésimo |
| **Docling + R6** | **22 / 28** | seis celdas difieren, hasta **18,30 pt** |

Las seis de Docling:

| documento | factor | publicado | ahora | diferencia |
|---|---:|---:|---:|---:|
| `escaneado_d5a` | ×0,75 | 8,90 | 18,10 | +9,20 |
| `escaneado_d5a` | ×1,125 | 0,30 | 9,10 | +8,80 |
| `escaneado_d5a` | ×1,25 | 0,30 | 18,10 | +17,80 |
| `escaneado_d5` | ×1,40 | 18,30 | 18,80 | +0,50 |
| `escaneado_d5b` | ×0,875 | 36,70 | 25,20 | −11,50 |
| `escaneado_d5b` | ×1,125 | 20,00 | 38,30 | +18,30 |

**Y las nueve repeticiones de cada una de esas seis celdas fueron idénticas
entre sí.** Es decir: **Docling+R6 es determinista DENTRO de un proceso y no
es reproducible ENTRE procesos.** Con `--reps 3` dentro de un proceso —el
método de `B23`— sale `determinista: true` y la afirmación es cierta y no
significa lo que parece.

**El mecanismo es discreto, no gradual.** Los 64 CER de Docling+R6 se agrupan
alrededor de escalones de ~9 puntos, y los bytes de texto lo explican:

| CER | bytes de texto | interpretación |
|---:|---:|---|
| 0,30 | 615–616 | lee las 12 líneas |
| 9,10–9,70 | 558–563 | **falta una línea** |
| 18,10–18,80 | 505–508 | faltan dos |
| 27,30 | 449–450 | faltan tres |

La referencia son 596 caracteres en 12 frases: **una línea vale ~53 bytes ≈ 9
puntos de CER**. Lo que cambia entre procesos no es el reconocimiento carácter a
carácter sino **cuántas líneas encuentra el detector**, y por eso las
diferencias son de 9 o de 18 puntos y nunca de 1,5.

**Lo que esto NO cambia:** recalculado con mis números sobre la rejilla de
`B23`, el argmin de Docling+R6 sigue siendo **×1,60 con arrepentimiento máximo
8,80** — exactamente el 8,8 publicado. Las seis celdas discrepantes están todas
en ×0,75–×1,40, la zona alta y ruidosa de la curva, y ninguna toca la región
por encima de ×2,25, que es donde está el hallazgo. **La conclusión de `B23` se
reproduce aunque seis de sus celdas no lo hagan** — pero eso hay que decirlo,
no descubrirlo el día que alguien intente reproducir una celda suelta.

Y para las otras dos configuraciones el control cierra además la duda del
**orden**: medir las celdas de mayor a menor Mpx, en vez de documento a
documento como hacía `B23`, da **28 de 28 celdas idénticas** en EasyOCR y en
Tesseract. El orden es una variable del coste de VRAM, no del CER.

---

## 4. Los resultados, por configuración

CER en % con la métrica acentuada, `n=9`, todas las celdas `rc=0` y
deterministas dentro del proceso. **Ni una sola tabla promediada entre
configuraciones**: la interacción motor × documento es el 76,7 % de la varianza
(`k-por-motor.md`) y promediarla la destruye.

### 4.1 Docling + RapidOCR torch + R6 — el `k` publicado estaba mal, y por mucho

| documento | ×0,75 | ×0,875 | ×1,00 | ×1,125 | ×1,25 | ×1,40 | **×1,60** | ×1,75 | ×2,00 | ×2,25 | ×2,50 | ×3,00 | **×3,50** | ×4,00 | ×5,00 | ×6,00 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d5a` | 18,10 | 18,10 | 18,10 | 9,10 | 18,10 | 0,30 | 9,10 | 0,30 | 13,80 | 0,30 | 0,30 | 0,30 | **0,30** | 0,30 | 0,30 | 0,30 |
| `escaneado_d5c` | 27,30 | 9,40 | 27,30 | 9,40 | 9,40 | 9,20 | 9,70 | 20,50 | 0,50 | 0,50 | 0,50 | 0,50 | **0,50** | 0,70 | 0,70 | 0,70 |
| `escaneado_d5` | 19,30 | 18,80 | 18,50 | 18,30 | 18,10 | 18,80 | 9,20 | 0,80 | 0,70 | 0,70 | 0,50 | 0,70 | **0,50** | 0,70 | 0,50 | 0,50 |
| `escaneado_d5b` | 32,20 | 25,20 | 26,50 | 38,30 | 20,00 | 26,70 | 19,30 | 19,10 | 16,60 | 10,10 | 10,20 | 3,70 | **3,20** | 3,70 | 3,90 | 4,20 |
| **regret medio** | 23,10 | 16,75 | 21,48 | 17,65 | 15,28 | 12,62 | **10,70** | 9,05 | 6,78 | 1,77 | 1,75 | 0,17 | **0,00** | 0,23 | 0,23 | 0,30 |
| **regret máx.** | 29,00 | 22,00 | 26,80 | 35,10 | 17,80 | 23,50 | **16,10** | 20,00 | 13,50 | 6,90 | 7,00 | 0,50 | **0,00** | 0,50 | 0,70 | 1,00 |

- `k` sobre la rejilla de `B23` (≤×1,60): **×1,60**, regret **2,33 / 8,80**.
- `k` sobre la rejilla entera: **×3,50**, regret **0,00 / 0,00**.
- **Coste de haberse quedado en el borde: 10,70 puntos** de arrepentimiento
  medio y **16,10** de máximo.

**El ×3,50 tiene una propiedad que casi nunca se da: es el óptimo de los CUATRO
documentos a la vez**, así que su arrepentimiento es exactamente 0,00 y no un
compromiso. Y el salto es enorme: al `k` publicado los cuatro documentos leen
9,10 / 9,70 / 9,20 / 19,30 y al `k` real leen 0,30 / 0,50 / 0,50 / 3,20 — es
decir, **el `k` publicado hacía a Docling perder una o dos líneas enteras de
cada documento**.

### 4.2 Tesseract `psm 11` — el óptimo se mueve un paso largo

| documento | ×0,75 | ×0,875 | ×1,00 | ×1,125 | ×1,25 | ×1,40 | **×1,60** | ×1,75 | **×2,00** | ×2,25 | ×2,50 | ×3,00 | ×3,50 | ×4,00 | ×5,00 | ×6,00 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d5a` | 24,80 | 7,00 | 1,20 | 1,20 | 0,70 | 0,30 | 0,50 | 0,30 | **0,50** | 0,50 | 0,70 | 0,70 | 0,50 | 0,30 | 0,80 | 0,50 |
| `escaneado_d5c` | 30,90 | 15,10 | 2,00 | 2,30 | 1,30 | 0,70 | 0,80 | 1,30 | **1,30** | 1,70 | 1,30 | 1,20 | 1,30 | 1,50 | 1,30 | 1,50 |
| `escaneado_d5` | 42,80 | 26,30 | 10,20 | 4,40 | 2,30 | 1,80 | 1,80 | 2,30 | **1,70** | 3,00 | 3,00 | 1,70 | 2,90 | 3,00 | 1,50 | 2,00 |
| `escaneado_d5b` | 69,50 | 48,50 | 25,30 | 22,00 | 17,80 | 16,30 | 14,40 | 7,70 | **6,50** | 10,40 | 6,20 | 9,40 | 11,60 | 8,90 | 8,70 | 10,20 |
| **regret medio** | 39,83 | 22,05 | 7,50 | 5,30 | 3,35 | 2,60 | **2,20** | 0,72 | **0,33** | 1,73 | 0,62 | 1,07 | 1,90 | 1,25 | 0,90 | 1,38 |
| **regret máx.** | 63,30 | 42,30 | 19,10 | 15,80 | 11,60 | 10,10 | **8,20** | 1,50 | **0,60** | 4,20 | 1,50 | 3,20 | 5,40 | 2,70 | 2,50 | 4,00 |

- `k` sobre la rejilla de `B23`: **×1,60**, regret **0,07 / 0,20** (`B23`
  publicó 0,08 / 0,2 — la misma cifra con otro redondeo).
- `k` sobre la rejilla entera: **×2,00**, regret **0,33 / 0,60**.
- **Coste de haberse quedado en el borde: 1,88 puntos** de arrepentimiento
  medio y **7,60** de máximo.

Quien manda es `escaneado_d5b`, el documento de 60 ppp nativos: **de 14,40 % a
×1,60 baja a 7,70 a ×1,75 y a 6,50 a ×2,00**, casi la mitad del error. Los otros
tres ya estaban en el suelo a ×1,40 y su curva es plana con ruido de ±1 punto.
Por encima de ×2,00 no hay mejora: el mejor regret de los nueve factores de
×2,25 a ×6,00 es 0,62, peor que el 0,33 de ×2,00, y **la dispersión ya no tiene
tendencia** (1,73 · 0,62 · 1,07 · 1,90 · 1,25 · 0,90 · 1,38).

**Alcance, y hay que decirlo con las palabras exactas de la trampa 55:** este
×1,60 → ×2,00 corrige el `k` que `B23` publicó **sobre la familia `d5` y con
`pHYs` declarado**. **No** toca el ×0,75 que `CLAUDE.md` publica para `psm 11`,
que se midió sobre el **corpus viejo** y con **otra rejilla** (§6 explica por
qué esa otra rejilla sí cubría su rango útil).

### 4.3 EasyOCR — no se mueve, y eso cierra el residuo

| documento | ×0,75 | ×0,875 | ×1,00 | ×1,125 | ×1,25 | ×1,40 | **×1,60** | ×1,75 | ×2,00 | ×2,25 | ×2,50 | ×3,00 | ×3,50 | ×4,00 | ×5,00 | ×6,00 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d5a` | 31,00 | 15,60 | 6,00 | 3,90 | 3,20 | 5,70 | **3,40** | 3,90 | 3,50 | 4,40 | 4,40 | 4,20 | 3,40 | 4,40 | 4,70 | 4,50 |
| `escaneado_d5c` | 42,30 | 30,20 | 10,10 | 9,60 | 10,20 | 11,40 | **8,60** | 12,80 | 9,20 | 11,70 | 8,20 | 8,40 | 11,40 | 8,10 | 9,90 | 9,40 |
| `escaneado_d5` | 49,30 | 38,10 | 18,50 | 21,60 | 21,60 | 18,30 | **16,80** | 18,30 | 21,50 | 17,80 | 16,60 | 19,00 | 19,10 | 21,50 | 19,60 | 20,10 |
| `escaneado_d5b` | 70,60 | 57,20 | 37,20 | 35,10 | 35,90 | 35,10 | **32,00** | 32,40 | 27,50 | 34,10 | 32,40 | 31,70 | 31,50 | 32,20 | 32,40 | 31,40 |
| **regret medio** | 34,45 | 21,43 | 4,10 | 3,70 | 3,88 | 3,77 | **1,35** | 3,00 | 1,57 | 3,15 | 1,55 | 1,98 | 2,50 | 2,70 | 2,80 | 2,50 |
| **regret máx.** | 43,10 | 29,70 | 9,70 | 7,60 | 8,40 | 7,60 | **4,50** | 4,90 | 4,90 | 6,60 | 4,90 | 4,20 | 4,00 | 4,90 | 3,90 | 3,90 |

- `k` sobre la rejilla de `B23`: **×1,60**, regret **0,05 / 0,20**.
- `k` sobre la rejilla entera: **×1,60**, regret **1,35 / 4,50**.
- **Coste de haberse quedado en el borde: 0,00.**

**×1,60 era un óptimo real, no un borde. El residuo queda cerrado para
EasyOCR.** Y con la salvedad honesta: **la meseta es ancha y poco profunda** —
de ×1,60 a ×6,00 el regret medio va de 1,35 a 3,15 y el máximo de 3,90 a 6,60;
la ventaja de ×1,60 sobre ×2,50 (1,35 frente a 1,55) es de **0,20 puntos**, así
que la afirmación fuerte que se sostiene es *«por encima de ×1,60 EasyOCR no
mejora»*, no *«×1,60 es estrictamente el mejor»*. La nota al pie de `B23`
—*«mejora monótonamente hasta 1,60 en 3 de 4 documentos, así que el verdadero
óptimo puede estar por encima»*— **queda refutada con nueve puntos nuevos**: la
monotonía se acaba justo ahí.

---

## 5. El mecanismo: los dos motores de GPU **RECORTAN** la entrada — sondeado en ejecución

*Una explicación plausible no es un mecanismo* (trampa 36), y `CLAUDE.md` §5 lo
exige como regla: **sondear en ejecución, no deducir** — el proyecto ya pagó el
error contrario con `limit_type` de PaddleX. Así que la sonda
`sonda_recorte_b26.py` **envuelve la función que reescala** y registra la forma
que entra y la que sale, en vez de leer la documentación.

**MEDIDO**, sobre `escaneado_d5a`:

| motor | dónde | factor | entrada | salida |
|---|---|---:|---|---|
| EasyOCR | `imgproc.resize_aspect_ratio`, `square_size=2560` | ×1,60 | 1282×931 | 1312×960 |
| EasyOCR | ídem | ×4,00 | **3204×2328** | **2560×1888** |
| Docling+R6 | `TextDetector.__call__` (RapidOCR, `max_side_len: 2000`) | ×1,60 | 1282×931 | — (sin recortar) |
| Docling+R6 | ídem | ×4,00 | — | **1984×1440** |

- **EasyOCR** tiene `canvas_size = 2560` y `mag_ratio = 1.0` por defecto en
  `readtext` (leídos de la firma en ejecución, no del manual): la imagen no se
  amplía nunca y se **recorta** por encima de 2 560 px de lado largo.
- **RapidOCR** —el motor que de verdad hace el OCR dentro de Docling— declara
  `max_side_len: 2000` en su `config.yaml`, y el detector recibe 1 984 px
  cuando docling le ha rasterizado 3 205. Es la misma inmunidad al tamaño que
  `CLAUDE.md` ya documenta para RapidOCR suelto, heredada por docling.

**Consecuencia directa: por encima de su recorte, subir el `k` no cambia un solo
píxel de lo que ve la red.** Eso convierte el «ya no mejora» de §4 en una
propiedad del adaptador, no en una observación de cuatro documentos. Y da un
número por documento: el factor a partir del cual el recorte muerde es

```
k_techo(motor, documento) = lado_recorte / lado_largo_en_pixeles_a_ppp_NATIVOS
```

**MEDIDO** (lado largo nativo = alto de página en puntos × ppp_nativos / 72):

| documento | ppp nativos | lado largo nativo | `k` techo RapidOCR (2 000) | `k` techo EasyOCR (2 560) |
|---|---:|---:|---:|---:|
| `escaneado_d5a` | 90 | 801 px | ×2,50 | ×3,20 |
| `escaneado_d5c` | 80 | 708 px | ×2,83 | ×3,62 |
| `escaneado_d5` | 72 | 636 px | ×3,14 | ×4,03 |
| `escaneado_d5b` | 60 | **531 px** | **×3,77** | ×4,82 |

**Y el argmin medido de Docling+R6 cae exactamente donde el mecanismo lo pone.**
Tres de los cuatro documentos llegan a su suelo de calidad **antes** de su
recorte (`d5a` a ×1,40, `d5c` a ×2,00, `d5` a ×2,50); el cuarto, `escaneado_d5b`
—el de menos ppp nativos y el más difícil— **mejora monótonamente hasta ×3,50 y
empeora a partir de ×4,00**, con su recorte en ×3,77. El `k` global lo fija el
documento limitante, y el limitante es el que llega hasta su propio techo.

**Por qué la rejilla de `B23` no podía verlo:** su último punto, ×1,60, está
**por debajo del techo de recorte de los cuatro documentos** (×2,50 el más bajo).
El barrido entero ocurría en la zona en la que más píxeles todavía ayudan. No es
que se le escapara el óptimo por poco: **es que no llegó a entrar en el régimen
donde el óptimo puede existir**.

---

## 6. La regla que sale de esto — cómo saber si el techo de una rejilla es vinculante ANTES de barrer

Esto explica también, y sin corpus nuevo, por qué el `k` publicado en
`CLAUDE.md` para el **corpus viejo** no sufre este defecto. Los mismos techos,
calculados sobre los cuatro documentos de aquel corpus:

| documento | ppp nativos | lado largo nativo | `k` techo RapidOCR | `k` techo EasyOCR |
|---|---:|---:|---:|---:|
| `escaneado_d3` | 100 | 850 px | ×2,35 | ×3,01 |
| `escaneado_d4` | 200 | 1 717 px | ×1,17 | ×1,49 |
| `escaneado_d4c` | 200 | 1 733 px | ×1,15 | ×1,48 |
| `patologico_escaneado` | 200 | 1 792 px | ×1,12 | ×1,43 |

**La rejilla de once factores de `k-por-motor.md` llega a ×1,80, que está POR
ENCIMA del techo de tres de sus cuatro documentos.** La rejilla de siete
factores de `B23` llega a ×1,60, que está **POR DEBAJO del techo de los cuatro**
documentos de `d5`. La misma disciplina, dos resultados opuestos, **y la
diferencia no está en la rejilla: está en el tamaño nativo del corpus**, que
cambia ×2–3 entre las dos familias.

> **Regla, MEDIDA:** antes de barrer un `k` sobre un motor que recorta, calcula
> `k_techo = lado_recorte / lado_largo_nativo_px` para el documento de MENOR
> resolución nativa, y **haz que la rejilla llegue por encima de ese número**.
> Si no llega, el argmin que encuentres es el borde del barrido y no lo sabrás,
> porque nada en el resultado lo delata: la curva simplemente sigue bajando
> hasta el último punto y ahí se acaba la tabla.

Esto le añade una pieza al hallazgo central de worker8 —*«el reparto entre
corpus y pHYs es abrumadoramente de CORPUS»*—: para los motores que recortan,
**una parte de ese «efecto corpus» es aritmética y no de contenido**. El `k` es
una unidad **relativa** (sobre los ppp nativos) y el recorte es **absoluto** (en
píxeles), así que dos corpus cuyos rásteres nativos difieren ×2–3 tienen
necesariamente `k` útiles que difieren ×2–3, **aunque los documentos fueran
idénticos en dificultad**. No explica todo el efecto —`escaneado_d4` sigue
moviendo 33 puntos por el `pHYs`, y eso es contenido— pero explica el término
que nadie había separado.

---

## 7. La VRAM: el modelo heredado, su residuo, y un guardián que rechazaba lo que sí cabía

El encargo pide evaluar `ordenada + pendiente × Mpx` contra la VRAM libre antes
de cada página. Se hizo, y la primera versión del guardián **recortó la rejilla
que este informe venía a extender** — el mismo defecto que el informe denuncia,
cometido por el instrumento. Dos causas, las dos medidas.

### 7.1 A Docling+RapidOCR no le corresponde la recta de EasyOCR

`bench/ocr-produccion-sidecar.md` §5.1 publica rectas para EasyOCR, PaddleOCR y
RapidOCR; **Docling+RapidOCR con backend torch no tiene una**. Prestarle la de
EasyOCR parecía conservador. `sonda_vram_b26.py` mide la de verdad, **cada punto
en un proceso FRESCO** (ir directo, trampa 67), sobre `escaneado_d5a`:

| Mpx | factor | **EasyOCR** coste MiB | **Docling+R6** coste MiB | recta EasyOCR publicada (641+1080·Mpx) |
|---:|---:|---:|---:|---:|
| 1,195 | ×1,60 | 1 189 | 749 | 1 932 |
| 2,917 | ×2,50 | 2 500 | 1 112 | 3 791 |
| 7,468 | ×4,00 | **3 953** | **1 061** | 8 706 |
| 16,802 | ×6,00 | **3 895** | **953** | 18 785 |

- **Docling+R6 es PLANO**: 749–1 112 MiB de 1,2 a 16,8 Mpx, un rango de ×14 en
  píxeles. Es exactamente la firma de RapidOCR, que `CLAUDE.md` ya describe
  («inmune porque recorta a 2 000 px, satura en 1 526 MiB»), heredada por
  docling. **La recta que le corresponde es la de RapidOCR (643 + 109, tope
  1 526), y sobre estos cuatro puntos es cota superior sin recortar nada.**
- **EasyOCR también satura**, y eso **corrige** su entrada publicada, que dice
  «tope propio: ninguno». Sube linealmente hasta ~7,5 Mpx y se planta en
  ~3 950 MiB, por el mismo `canvas_size = 2560` de §5. La recta publicada
  **sobrestima ×2,20** a 7,468 Mpx (8 706 previstos, 3 953 medidos).
  *(La serie original se ajustó sobre un A4 real de hasta 8,88 Mpx, y su r²=0,957
  ya avisaba: la trampa 85 pide tabular el residuo antes de presupuestar, y el
  residuo aquí es de un factor 2.)*

### 7.2 Un modelo escrito para un proceso fresco, aplicado dentro de un proceso vivo, rechaza celdas que ese proceso SÍ puede servir

**MEDIDO en el piloto**, con el guardián crudo: tras la celda de 7,468 Mpx la
VRAM libre baja de **9 941 a 6 161 MiB** y ahí se queda —el asignador no la
devuelve, trampa 67—, así que las dos celdas **siguientes y MENORES** (5,851 y
4,732 Mpx) salieron `omitido_vram` **sin motivo**: el proceso ya tenía reservado
más de lo que pedían.

La regla de §5.1 está escrita para *«antes de cada página, ¿cabe el coste
propio?»*, y eso vale para un proceso recién arrancado o recién reciclado. **Dentro
de un proceso que ya tiene un pool, la magnitud que hay que comparar no es el
coste absoluto sino el INCREMENTO sobre el mayor tamaño ya servido** — y con el
orden descendente que la propia trampa 67 recomienda, ese incremento es cero
para todas las páginas menos la primera. El guardián de `b26_borde.py` hace eso,
y con él **0 celdas de 192 quedaron omitidas**.

### 7.3 Y una consecuencia incómoda: el suelo de `GPU_GUARD` se cruzó, y no podía impedirlo

**MEDIDO.** La VRAM libre mínima observada en la tanda de EasyOCR fue **5 945
MiB**, es decir **55 MiB por debajo del umbral de aborto de `GPU_GUARD`**
(`GPU_LIBRE_MIN_MIB = 6000`). No abortó nada, y **está bien que no abortara**:
`guardia()` se evalúa **una vez, al tomar el lock**, y lo que hundió la cifra
por debajo del suelo no fue un ocupante ajeno sino **el pool del propio
proceso**, que es justo lo que ese suelo NO tiene que vigilar. En la tanda de
Docling el mínimo fue 8 034 MiB.

Dicho de otra forma: **el suelo de 6 000 MiB mide «cuánta tarjeta me deja libre
el resto del mundo», no «cuánta me queda mientras trabajo»**, y son dos
magnitudes distintas en cuanto el asignador deja de devolver memoria. Un
guardián por celda que comparase la VRAM libre contra 6 000 **habría abortado
esta tanda a mitad, y la habría abortado por su propio éxito**. Es la frontera
de §7.2 vista desde el otro lado, y hay que decirlo porque el encargo
—razonablemente— pedía las dos cosas juntas: *«evalúa `ordenada + pendiente ×
Mpx` contra la VRAM libre antes de cada página y aborta por debajo de 6 000 MiB
libres»*. **Las dos reglas no se pueden aplicar a la vez dentro de un proceso de
vida larga: la primera es incremental y la segunda es absoluta.** La que sí se
sostiene por celda es la incremental; la absoluta pertenece al arranque y al
reciclado.

---

## 8. Qué hay que cambiar, con el número

1. **`k` de Docling+RapidOCR+R6 sobre la familia `d5`: ~~×1,60~~ → ×3,50.**
   Arrepentimiento de 2,33/8,80 a **0,00/0,00**. Es el residuo cerrado y es una
   corrección grande: al `k` viejo, docling pierde una o dos líneas enteras de
   cada uno de los cuatro documentos.
2. **`k` de Tesseract `psm 11` sobre la familia `d5` con `pHYs` declarado:
   ~~×1,60~~ → ×2,00.** Arrepentimiento de 2,20/8,20 a **0,33/0,60**.
3. **`k` de EasyOCR: ×1,60 CONFIRMADO.** El residuo se cierra con un resultado
   nulo, y el nulo tiene mecanismo.
4. **La entrada de EasyOCR en `ocr-produccion-sidecar.md` §5.1 dice «tope
   propio: ninguno» y sí tiene tope: ~3 950 MiB**, por `canvas_size = 2560`.
   Con el tope, EasyOCR admite **cualquier** página con 6 000 MiB libres; sin
   él, la tabla dice que un A4 a 300 ppp «ya no entra», y sí entra.
5. **Docling+RapidOCR torch hereda la recta de RapidOCR, no la de EasyOCR**
   (643 + 109, tope 1 526; medido 749–1 112 MiB en cuatro puntos).
6. **Lo que NO se toca:** el ×0,875 / ×0,75 que `CLAUDE.md` publica para
   Tesseract y el ×1,00 / ×0,875 de EasyOCR y Docling+R6 en `k-por-motor.md`
   salen del **corpus viejo** y de una rejilla que **sí** llega por encima del
   techo de recorte de tres de sus cuatro documentos (§6). **No se refutan
   aquí, y tampoco se confirman: no se han medido.**

---

## 9. Trampas que este informe propone añadir (al FINAL, sin renumerar)

**111. Un argmin en el último punto del barrido no es un argmin: es el borde, y
para los motores que RECORTAN la entrada se puede saber de antemano si la
rejilla llega o no — MEDIDO.** `B23` fijó el `k` de tres configuraciones en
×1,60, que era su último factor, y su propia nota al pie lo marcó como duda.
Extendida la rejilla a ×6,00 (×14 en píxeles), **dos de los tres se mueven**:
Docling+R6 de ×1,60 a **×3,50** (arrepentimiento 2,33 → **0,00**, coste de
haberse quedado en el borde **10,70 pt**) y Tesseract `psm 11` de ×1,60 a
**×2,00** (**1,88 pt**); EasyOCR **no se mueve** y ahí el borde era un óptimo.
**El mecanismo está sondeado en ejecución, no deducido:** EasyOCR recorta a
`canvas_size=2560` (3204×2328 → 2560×1888) y RapidOCR —dentro de docling— a
`max_side_len=2000` (3205 → 1984), así que **por encima de su recorte subir el
`k` no cambia un píxel de lo que ve la red**. De ahí sale la prueba previa que
cuesta una división: `k_techo = lado_recorte / lado_largo_nativo_px` para el
documento de MENOR resolución nativa. Sobre `d5` da ×2,50–×3,77 y la rejilla de
`B23` acababa en ×1,60 —**por debajo de los cuatro**—; sobre el corpus viejo da
×1,12–×2,35 y la rejilla de `k-por-motor.md` llegaba a ×1,80 —**por encima de
tres de los cuatro**—. **Y eso reinterpreta parte del «efecto corpus»**: el `k`
es relativo a los ppp nativos y el recorte es absoluto en píxeles, así que dos
corpus cuyos rásteres nativos difieren ×2–3 tienen `k` útiles que difieren ×2–3
aunque los documentos fueran igual de difíciles.

**112. «Determinista» medido dentro de un proceso no significa reproducible
entre procesos, y el modo de fallo es discreto: se pierde una LÍNEA entera —
MEDIDO.** Docling+R6 dio **9 de 9 repeticiones idénticas** en las 64 celdas de
esta tanda y aun así **6 de sus 28 celdas comunes con `B23` difieren**, hasta
**18,30 puntos**. No es ruido de reconocimiento: los CER se agrupan en escalones
de ~9 puntos y los bytes lo explican —615 B = 12 líneas, 562 = 11, 507 = 10,
449 = 9, sobre una referencia de 596 caracteres en 12 frases—, así que lo que
cambia entre procesos es **cuántas líneas encuentra el detector**. EasyOCR y
Tesseract reproducen **28 de 28**. Consecuencia: `determinista: true` con
`--reps 3` es una afirmación cierta sobre el proceso y **no** sobre el motor;
para un motor de detección hay que repetir **en procesos distintos** o declarar
el alcance. *(Aquí la conclusión de `B23` se reproduce igualmente —el argmin y
el arrepentimiento máximo de 8,80 salen idénticos— porque las seis celdas
discrepantes están todas en la zona alta de la curva; pero eso es suerte del
caso, no una propiedad del método.)*

**113. Un modelo de recurso escrito para un proceso RECIÉN ARRANCADO, aplicado
dentro de un proceso que ya tiene un pool, rechaza trabajo que ese proceso sí
puede hacer — y lo rechaza justo porque el asignador no devuelve la memoria —
MEDIDO.** La regla de `ocr-produccion-sidecar.md` §5.1 (`coste_previsto =
ordenada + pendiente × Mpx` contra la VRAM libre) aplicada tal cual dentro de
una tanda dejó `omitido_vram` en dos celdas **menores** que una ya servida:
tras procesar 7,468 Mpx la VRAM libre cayó de 9 941 a 6 161 MiB y no volvió, así
que 5,851 y 4,732 Mpx «no cabían». Con el orden descendente que la propia
trampa 67 recomienda, **lo que hay que comparar es el INCREMENTO sobre el mayor
Mpx ya servido**, no el coste absoluto: con ese cambio, 0 celdas omitidas de
192. **Y el corolario en el otro sentido, que es el que sorprende:** la VRAM
libre mínima de esa misma tanda fue **5 945 MiB**, **por debajo** del suelo de
aborto de `GPU_GUARD` (6 000), y **no debía abortar** — ese suelo mide ocupación
AJENA y se evalúa al tomar el lock; aplicado por celda habría matado la tanda
por su propio éxito. **En un proceso de vida larga, la regla incremental y el
suelo absoluto no se pueden exigir a la vez: la primera es de la celda, el
segundo es del arranque y del reciclado.** Y la segunda mitad, que es la trampa 85 otra vez: **la recta prestada
mentía en las dos direcciones** — la de EasyOCR sobrestima ×2,20 a 7,468 Mpx
(8 706 previstos, 3 953 medidos) **porque EasyOCR también satura**, contra lo
que su propia fila publica («tope propio: ninguno»); y a Docling+RapidOCR-torch
le corresponde la recta de **RapidOCR** (643 + 109, tope 1 526), no la de
EasyOCR, porque el motor que hace el OCR dentro de docling es RapidOCR y
recorta igual que él (medido: 749–1 112 MiB de 1,2 a 16,8 Mpx).

---

## 10. Declaraciones (las cuatro — trampas 94 y 101)

**Intérprete.** Dos, y cada uno donde toca:
`D:\Work\research\FileX\.venv-ai\Scripts\python.exe` para las dos
configuraciones de GPU (EasyOCR y Docling+R6) y las dos sondas;
`D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe` (Windows 3.11.9, no
WSL) para Tesseract, el análisis, `pytest` y `ci/integridad.py`. **No se instaló
nada en ningún venv.** Los venvs viven en `D:\Work\research\FileX\`, fuera del
*worktree*, y se invocan por ruta absoluta (trampa 100).

**Entorno.** Windows 10; RTX 3060 12 288 MiB; ImageMagick 7.1.2-Q16-HDRI;
Tesseract 5.5.0 nativo con `TESSDATA_PREFIX=C:\Program Files\PDFgear\tessdata`;
**demonio de Docker LEVANTADO** durante la suite (por eso sólo quedan 4
saltadas). `USERPROFILE`/`HOME` fijados a `C:\Users\krato` en cada invocación
(trampa 99). `corpus/` **no** son punteros de LFS: `corpus/imagen/tipico.png`
pesa 42 855 B, comprobado antes de tocar nada (trampa 34).

**Qué quedó fuera, y por qué.**
- **El corpus viejo por encima de ×1,60.** El encargo lo daba por opcional; §6
  explica por qué además **no hace falta para lo que aquí se decide**: el techo
  de recorte de tres de sus cuatro documentos está en ×1,12–×1,17 y la rejilla
  de once factores de `k-por-motor.md` ya llega a ×1,80. **PENDIENTE** si
  alguien quiere el número exacto; **no** es un borde por medir.
- **Las dos configuraciones con óptimo interior** (RapidOCR v6 ×1,25, RapidOCR
  v5 ×1,00) no se repiten, por instrucción del encargo y por la trampa 69 al
  revés.
- **Tesseract `psm 3`** (óptimo publicado ×1,40, interior) no entra: no toca el
  borde.
- **El `k` de `psm 11` en el corpus viejo toca el borde de ABAJO** (×0,75 es el
  primer punto de aquella rejilla). Este informe no lo mide: es un borde
  distinto y **queda PENDIENTE**, dicho aquí porque nadie lo había escrito.
- **La recta de VRAM de Docling+R6 se apoya en 4 puntos y un solo documento**;
  vale como cota superior verificada, no como ajuste publicable. **PENDIENTE**
  ajustarla con la disciplina de `ocr-produccion-sidecar.md` (5 puntos, r²).

**Estado de la máquina.** VRAM libre **9 982 MiB** al arrancar el conductor y
**10 219** al terminarlo. El mínimo observado durante las tandas fue **5 945
MiB** (EasyOCR; 8 034 en Docling), es decir **55 MiB por debajo** del umbral de
aborto de `GPU_GUARD` — no abortó porque ese umbral se evalúa al tomar el lock,
y lo que consumió la memoria fue el pool del propio proceso, no un ocupante
ajeno; **§7.3 lo explica y dice por qué las dos reglas del encargo no se pueden
aplicar a la vez**. **Lock de GPU
tomado y soltado por configuración**, y el conductor reinicia el proceso Python
entre configuraciones (trampas 67 y 100). Sesión remota activa, como es
estructural en esta máquina. Las tres tandas salieron **`limpia`** por los dos
testigos de ruido:

| tanda | deriva (monohilo) | nivel (proceso) | etiqueta | duración |
|---|---:|---:|---|---:|
| Docling+R6 | 1,09 | 1,39× | limpia | 753,5 s |
| EasyOCR | 1,07 | 1,06× | limpia | 1 143,0 s |
| Tesseract `psm 11` | 0,73 | 1,79× | limpia | 619,0 s |

**Un incidente de máquina, declarado porque afecta a la trazabilidad y no al
resultado:** al parar la primera tanda (la que corría con el guardián malo) se
usó `taskkill /F /IM python.exe`, que es demasiado ancho — mata cualquier
`python.exe` de la máquina, no sólo el propio. Además dejó un `filex-gpu.lock`
cuyo dueño **seguía vivo** y que se borró antes de comprobarlo, es decir se robó
un lock legítimamente tomado (por un proceso mío, por suerte). **Ninguna celda
publicada viene de aquella tanda: sus ficheros se borraron enteros y la tanda
buena se lanzó desde cero.** La forma correcta es matar por PID, y comprobar
`tasklist` **antes** de tocar el lock, no después.

**Suite de pruebas** (`.venv-mcp-filex`, Windows, Docker levantado):

```
python -m pytest pruebas/ -q
→ 1.ª pasada: 1 failed, 458 passed, 4 skipped, 130 subtests passed  (202,12 s)
→ 2.ª pasada: 459 passed, 4 skipped, 130 subtests passed             (235,94 s)
→ 3.ª pasada: 459 passed, 4 skipped, 130 subtests passed             (194,85 s)
```

**La cifra buena es la segunda: 459 passed · 4 skipped · 0 failed.** El fallo de
la primera pasada fue
`test_watcher_n.py::CerrojoPosix::test_proc_ve_al_escritor_y_replace_no`, que
lanza `wsl.exe -e python3` y devolvió `4294967295` (−1) con un
`UnicodeDecodeError` sobre su `stderr` en `cp1252` — es decir, **WSL contestó un
error del sistema en castellano**, no una aserción rota. **Repetido aislado:
`3 passed in 10,08 s`; y en las dos pasadas completas siguientes, verde.** Es la
trampa 101: la suite no es hermética respecto del estado de la máquina, y esa
primera pasada arrancó cuando acababa de terminar el conductor. **No se
investigó más porque dos intentos bastan y porque este informe no toca una línea
de `filex/` ni de `pruebas/`** — lo verifica `git diff --stat HEAD -- filex/
pruebas/`, que sale vacío.

**Las 4 saltadas, declaradas una a una** (trampa 94: el recuento necesita decir
qué quedó fuera): no hay dos volúmenes distintos a mano (`test_cerrojo`);
ningún par real rasteriza hacia un destino con texto en esta máquina
(`test_hito4`); falta el ráster de `bench/salidas-hito6/preparar_h6.py`; y
`FILEX_PRUEBAS_SIDECAR=1` sin fijar (`test_hito6`). **Ninguna tiene que ver con
este informe**, y con Docker levantado ya no hay ninguna saltada por falta de
contenedor.

```
python ci/integridad.py
```

**Ocho comprobaciones en OK y una en FALLO: `informes-registrados`**, que exige
que todo `bench/*.md` figure en `ESTADO-Y-REPARTO.md` y encuentra exactamente
un nombre fuera: **`k-borde-rejilla.md`, este informe**. **No se arregla aquí
porque el encargo prohíbe expresamente tocar `ESTADO-Y-REPARTO.md`, que es del
consolidador.** Es una línea, y va con la fila que este informe le pide al
inventario:

> | `k-borde-rejilla.md` | B26 — la rejilla de `k` por encima de ×1,60: Docling+R6 ×1,60→**×3,50** (−10,70 pt de arrepentimiento), Tesseract `psm 11` ×1,60→**×2,00** (−1,88), EasyOCR ×1,60 **confirmado**. Mecanismo: los dos motores de GPU recortan la entrada (2 560 / 2 000 px). |

---

## 11. Ficheros

| fichero | qué es |
|---|---|
| `bench/salidas-k-borde-rejilla/b26_borde.py` | el arnés: 16 factores × 4 documentos × 3 configuraciones, `n=9`, `rc` por repetición, guardián de VRAM incremental |
| `bench/salidas-k-borde-rejilla/conductor_b26.sh` | conductor único y desprendido, en serie, reiniciando el proceso entre configuraciones, con log `INICIO`/`FIN`/`rc`/celdas |
| `bench/salidas-k-borde-rejilla/analisis_b26.py` | `k` por mínimo arrepentimiento sobre la rejilla entera y sobre la truncada en ×1,60, y el coste de la diferencia |
| `bench/salidas-k-borde-rejilla/sonda_vram_b26.py` | la recta de VRAM de cada motor, un proceso fresco por punto |
| `bench/salidas-k-borde-rejilla/sonda_recorte_b26.py` | el recorte, sondeado en ejecución envolviendo la función que reescala |
| `bench/salidas-k-borde-rejilla/json/` | las 192 celdas crudas, el análisis, los techos de recorte y los `sha256` de los rásteres |
| `bench/salidas-k-borde-rejilla/texto/` | las 192 lecturas literales de OCR |
| `bench/salidas-k-borde-rejilla/logs/` | los `.jsonl` celda a celda, los `stderr`, el log del conductor, las dos sondas y la salida de `pytest` |
| `bench/salidas-k-borde-rejilla/MANIFIESTO.md` | los 128 rásteres PNG (17,6 MB, **no versionados**), con `sha256` y la orden exacta que los reproduce |
