# El corpus `d5`: el suelo de 100 ppp, un patológico que sí discrimina, y por qué el «efecto del rasterizador» no era del rasterizador

> **⚠ ETIQUETA DE COMPARABILIDAD — añadida el 23/08 por `bench/phys-multimotor.md` §6.**
> Las cifras de **Tesseract** de **§2.2-§2.4, §3.1-§3.3, §5.1, §6.1, §6.2 y la columna A de §4** (~266 celdas) se midieron sobre rásteres de `magick -density N`
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

**Encargo G3.** Construir los tres corpus que `bench/k-por-motor.md` §9 deja como
pendientes: **B19** (un sustituto de `patologico_escaneado`, que no discrimina),
**B15** (un original de 60–80 ppp nativos, para probar el suelo de 100 de la regla) y
**B12** (degradación realista: sombra de encuadernación, curvatura y transparencia del
papel).

**Máquina:** Windows 10, 12 hilos, Python 3.11.9, ImageMagick 7.1.2 Q16-HDRI,
Ghostscript 10.07, Tesseract 5.5.0. **Fecha:** 2026-08-22, 10:45–12:40.
**GPU: NO se ha usado y NO se ha tomado el lock.** Todo lo de este informe es CPU:
`magick` para generar y `tesseract` para validar.
**Salidas:** `bench/salidas-corpus-d5/` (+ `MANIFIESTO.md` y `tablas.md`).
**Corpus nuevo:** `corpus/pdf/{escaneado,patologico,realista}_d5*.pdf`,
`corpus/pdf/MANIFIESTO-d5.md`, `corpus/pdf/REFERENCIA-d5.txt`.

**Evaluador: `bench/salidas-corpus-d4/ocr_eval_d4.py`, copiado byte a byte** a
`bench/salidas-corpus-d5/ocr_eval_d4.py` (`sha256`
`350354b261aef60b018b196204648c4c27effc0683f93a4fbcb5f2d551a30d82`, idéntico al
original), invocado con `rid="d4"`. **`bench/scripts/ocr_eval.py` no se ha abierto ni
tocado**: es ciego a las tildes. Toda cifra de este informe es **CER con acentos**.

**No se publica ni un milisegundo**, así que no hay testigos de ruido: lo que se mide
es CER, que es determinista y se comprobó reproduciendo celdas entre tandas (§7.1).

---

## 0. Veredicto, primero

1. **MEDIDO — los tres corpus existen y discriminan. Doce PDF, 610 caracteres de
   referencia, ppp nativos verificados leyendo el PDF.** En las **90 celdas** de la
   tanda de validación (15 documentos × 3 `--psm` × 2 idiomas) **no hay una sola celda
   a 0,00 %**. El mínimo absoluto del corpus nuevo es **0,17 %** y los tres canónicos
   se mueven entre **10,07 y 59,56 %**. Es lo contrario de `patologico_escaneado`, que
   daba **88 celdas de 99 a cero**. *(§6)*
2. **MEDIDO, y es el resultado principal — el suelo de 100 ppp de la regla vigente es
   ARITMÉTICAMENTE INALCANZABLE por debajo de 80 ppp nativos, y eso cuesta 16,78
   puntos de CER.** `ppp_ocr = min(max(n, 100), n × 1,25)` aplica el suelo **antes**
   del techo: para `n ≤ 80` el techo `n × 1,25` queda por debajo de 100 y lo anula.
   Sobre `escaneado_d5b` (60 ppp nativos) la regla ordena **75 ppp** → **25,50 %**,
   cuando rasterizar a los **100** del suelo da **8,72 %**. *(§2.2)*
3. **MEDIDO — y donde el suelo SÍ actúa, tampoco ayuda.** El único régimen en que el
   suelo decide es `80 < n < 100`, y en él `escaneado_d5a` (90 ppp nativos) empeora:
   **1,17 % a ppp nativos frente a 2,68 % a los 100 que impone el suelo**. El óptimo
   real de los cuatro documentos está en **125 ppp**, no en 100. *(§2.3)*
4. **MEDIDO, y es el hallazgo que más corrige a otro informe — el «efecto del
   rasterizador» de 33 puntos de `bench/k-por-motor.md` §6.2 NO es del rasterizador:
   es del `pHYs` del PNG.** Los dos PNG tienen el **mismo `sha256` de píxeles crudos**.
   Escribirle al PNG de ImageMagick `-units PixelsPerInch -density N` **sin tocar un
   solo píxel** reproduce la cifra de Ghostscript **en las 16 celdas, a la centésima**.
   Sobre `escaneado_d4` con `psm 3` son **33,22 puntos** (84,56 → 51,34). *(§4)*
5. **MEDIDO — la iluminación no uniforme es la patología más potente de las cinco
   (74,67 puntos) y es INSERVIBLE para construir un corpus.** Barrida en 7 puntos da
   un **interruptor**, no un gradiente: 5,20 → 5,03 → **72,82** en un escalón de
   4 puntos de gris, y luego **no es monótona** (79,36 / 82,21 / 78,36 / 54,87). *(§3.2)*
6. **MEDIDO — el POLVO sí es gradual, y es lo que sostiene la escalera de B19**:
   5,20 / 4,70 / 16,28 / 25,00 / 32,05 / 56,04 al subir `-attenuate` del ruido de
   impulso de 0,045 a 0,35. *(§3.3)*
7. **MEDIDO — dos perillas de degradación no valen nada y una VA AL REVÉS**, igual que
   en `d4`: quitar las rayas de sensor mueve **1,34 puntos** y **bajar el ruido
   gaussiano EMPEORA 2,52**. La segunda reproduce el hallazgo contraintuitivo de
   `bench/corpus-d4.md` §3 sobre otro documento y otra degradación. *(§3.1)*
8. **MEDIDO — las tres degradaciones «realistas» de B12 están en el píxel, con control
   de cero.** Sombra de encuadernación: cociente de luminancia izquierda/derecha
   **0,87 / 0,82 / 0,79 / 0,78** frente a **0,99** de `escaneado_d4`. Curvatura:
   residuo **1,9 / 3,2 / 6,0 / 7,3 px** tras quitar el giro, frente a **0,4 px** del
   control generado con `onda = 0` y **todo lo demás idéntico**. Transparencia: la
   zona en blanco del maestro baja de 1,00 a **0,92 / 0,86 / 0,80 / 0,74**. *(§5)*
9. **MEDIDO — la referencia es la misma que la de `escaneado_d4`, a propósito.** 610
   caracteres, 35 acentuados, cuatro bloques de tamaño de letra. Los doce documentos
   nuevos son comparables **celda a celda** con las 396 de `bench/k-por-motor.md` y las
   28 de `bench/corpus-d4.md`. *(§1)*

---

## 1. El diseño, y la decisión que más importa: **no cambiar el texto**

`bench/k-por-motor.md` §9 dice que el `k` está ajustado sobre cuatro documentos, que
comparten geometría de página y que tres salen del mismo generador. La tentación es
arreglarlo cambiándolo todo. **Sería un error**: si cambian a la vez el texto, la
maqueta y la degradación, ninguna diferencia de CER es atribuible.

Lo que falta en el corpus **no es texto**: es **resolución** (B15), **patología**
(B19) y **degradación física** (B12). Así que el texto se deja fijo:

| se hereda de `d4`, sin cambiar | se cambia |
|---|---|
| la cadena de referencia: **610 caracteres**, 35 acentuados, `ñ`/`Ñ`, `ü`, `¿`, `¡` | los **ppp nativos** (60/72/80/90 en B15) |
| los **cuatro bloques** de tamaño de letra | los **tamaños de letra** de B15 (26/18/13/9 pt en vez de 24/13/11/7) |
| la página maestra a 600 ppp, 3882×5376 | las **recetas de degradación** (tres nuevas) |
| el evaluador `ocr_eval_d4.py` con `rid="d4"` | — |

`bench/salidas-corpus-d5/d5_texto.py` **importa** `BLOQUES` de `d4_texto.py` y sólo
reasigna fuentes y posiciones, así que la referencia **no puede** divergir: es
literalmente el mismo objeto. Verificado: **610 caracteres, 35 acentuados**.

**Por qué B15 necesita tamaños de letra distintos.** En `escaneado_d4`, a 200 ppp, los
cuatro bloques miden de em **66,7 / 36,1 / 30,6 / 19,4 px**, y el gradiente medido cae
entre los 30,6 px (CER 1,6–14 %) y los 19,4 px (58,7–75,1 %). El punto de ruptura de
este corpus está, por tanto, **entre ~20 y ~31 px de em**. A 72 ppp, 1 pt = 1 px: con
los tamaños de `d4` los cuatro bloques medirían 24/13/11/7 px, **los cuatro por debajo
del punto de ruptura**, y el documento sería una pared — el mismo defecto de
`patologico_escaneado` visto por el otro lado. Con 26/18/13/9 pt miden 26/18/13/9 px:
uno encima, uno justo en el punto y dos debajo. **Eso es un gradiente por
construcción**, y deja sitio para que la subida a 90 ppp (lo que la regla produce)
mueva algo.

---

## 2. B15 — el suelo de 100 ppp, probado por primera vez

### 2.1 Los cuatro puntos no son arbitrarios: son los cuatro regímenes de la regla

La regla vigente (`CLAUDE.md` trampa 8) es
`ppp_ocr = min(max(n, 100), n × 1,25) × k(motor)`. Antes de medir nada, **la
aritmética ya dice algo que nadie había escrito**:

| `n` (ppp nativos) | `max(n,100)` | `n × 1,25` | `min(...)` | ¿quién manda? |
|---:|---:|---:|---:|---|
| **60** | 100 | **75** | **75** | el techo ×1,25. **El suelo no actúa** |
| **72** | 100 | **90** | **90** | el techo ×1,25. **El suelo no actúa** |
| **80** | 100 | 100 | **100** | **empatan** |
| **90** | 100 | 112,5 | **100** | el suelo. **Único régimen en que decide** |

> **El suelo de 100 ppp sólo puede actuar en la franja `80 < n < 100`.** Por debajo de
> 80 el techo ×1,25 queda por debajo del suelo y lo anula, porque el `min` se aplica
> después del `max`. **Es una consecuencia del ORDEN de los operadores, no una
> decisión.**

Los cuatro documentos de B15 caen uno en cada régimen. **ppp nativos verificados
leyendo el PDF con `pypdfium2`** (ancho en px de la imagen incrustada ÷ ancho de página
en pulgadas), no declarados a mano: **60,0 / 72,0 / 80,0 / 90,0**.

### 2.2 El barrido: 64 celdas, y cuánto cuesta el orden de los operadores

**MEDIDO.** Tesseract, `spa`, rasterizador ImageMagick, CER con acentos.
La columna **negrita** es la que produce la regla vigente.

**`--psm 3`**

| documento | ppp nat | 60 | 72 | **75** | 80 | **90** | **100** | 125 | 150 | 200 | 300 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d5b` | 60 | 28,69 | — | **25,50** | — | 12,75 | 8,72 | **6,88** | 7,89 | 9,90 | 9,56 |
| `escaneado_d5` | 72 | — | 10,07 | 7,55 | — | **2,35** | 3,02 | 2,35 | **2,18** | 2,68 | 2,52 |
| `escaneado_d5c` | 80 | — | — | 12,92 | 2,52 | 2,01 | **1,34** | **0,84** | **0,84** | **0,84** | 1,51 |
| `escaneado_d5a` | 90 | — | — | 25,00 | — | 1,17 | **2,68** | **0,50** | 0,67 | 0,67 | 0,67 |

**`--psm 11`**

| documento | ppp nat | 60 | 72 | **75** | 80 | **90** | **100** | 125 | 150 | 200 | 300 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `escaneado_d5b` | 60 | 25,34 | — | **17,79** | — | 13,76 | 8,56 | 8,56 | **6,21** | 9,40 | 8,72 |
| `escaneado_d5` | 72 | — | 10,23 | 7,21 | — | **2,35** | 1,85 | **1,85** | 2,52 | 2,85 | 2,35 |
| `escaneado_d5c` | 80 | — | — | 12,08 | 2,01 | 2,35 | **1,34** | **0,84** | 1,01 | 1,34 | 1,17 |
| `escaneado_d5a` | 90 | — | — | 11,58 | — | 1,17 | **1,51** | **0,50** | 0,67 | 0,84 | 0,67 |

**Con todas las letras:**

- **Sobre un original de 60 ppp la regla vigente deja 16,78 puntos de CER sobre la
  mesa** (`psm 3`: 25,50 % a los 75 ppp que ordena, 8,72 % a los 100 del suelo). Con
  `psm 11`, 9,23 puntos. **Y no es que el suelo esté mal puesto: es que la fórmula le
  impide actuar.**
- **Reordenar los operadores lo arregla y no cuesta casi nada.** Con
  `ppp_ocr = max(min(n × 1,25, techo), 100)` —el suelo el último— los cuatro
  documentos irían a 100/100/100/100 ppp:

  | documento | regla vigente | reordenada | ganancia `psm 3` | ganancia `psm 11` |
  |---|---|---|---:|---:|
  | `escaneado_d5b` (60) | 75 ppp → 25,50 | **100 ppp → 8,72** | **+16,78** | **+9,23** |
  | `escaneado_d5` (72) | 90 ppp → 2,35 | 100 ppp → 3,02 | −0,67 | +0,50 |
  | `escaneado_d5c` (80) | 100 ppp → 1,34 | 100 ppp → 1,34 | 0,00 | 0,00 |
  | `escaneado_d5a` (90) | 100 ppp → 2,68 | 100 ppp → 2,68 | 0,00 | 0,00 |

  **Gana hasta 16,78 puntos y pierde como mucho 0,67.** *(PENDIENTE de comprobar con
  los otros ocho motores: aquí sólo hay Tesseract, y el `--psm` ya mueve más que
  muchos `k`.)*
- **Bajar sigue costando siempre, y aquí cuesta más que en `d4`.** `escaneado_d5a` de
  90 a 75 ppp: **1,17 → 25,00 %** (`psm 3`), **23,83 puntos**. `escaneado_d5c` de 80 a
  75: **2,52 → 12,92 %**. En `d4` bajar de 200 a 100 costaba 12,08; a estas
  resoluciones **la misma reducción relativa cuesta el doble**. Es coherente: a 60–90
  ppp cada píxel que se quita sale de una `x` que ya mide 5–7 px.

### 2.3 El suelo, donde sí decide, **no ayuda**

`escaneado_d5a` es el único documento del proyecto en el régimen `80 < n < 100`, que es
el único en que el suelo decide algo. Y ahí:

| `escaneado_d5a` (90 ppp nativos) | `psm 3` | `psm 11` |
|---|---:|---:|
| a **ppp nativos** (90) | **1,17** | **1,17** |
| a **100 ppp** (lo que impone el suelo) | 2,68 | 1,51 |
| a 125 ppp | **0,50** | **0,50** |

**El suelo empeora 1,51 puntos con `psm 3` y 0,34 con `psm 11` frente a no hacer
nada**, y el óptimo real está en 125. La lectura honesta es doble y las dos partes
importan:

> **El suelo de 100 no puede actuar donde habría pagado (n ≤ 80) y donde actúa no
> paga (80 < n < 100).** El número que los cuatro documentos señalan **no es 100: es
> ~125**, que sobre estos cuatro es el mejor o empata en 6 de las 8 columnas.
> **PENDIENTE**: 125 sale de un solo motor y de cuatro documentos que comparten
> generador. No es una constante para producción; es la siguiente hipótesis a barrer.

### 2.4 El control dice que esto es resolución, no ruido

`d5_limpio` es la misma página a 72 ppp **sin ninguna degradación** (sin giro, sin
desenfoque, sin `+level`, sin ruido, JPEG 95). **MEDIDO: 6,21 % de CER** (`psm 3`,
`spa`), con bloques 0,00 / 0,00 / 0,00 / **30,99**.

De los 10,07 % que da `escaneado_d5`, **6,21 son de la resolución sola** y 3,86 de la
degradación. **Sin este control, todo el §2 sería ambiguo.**

---

## 3. B19 — un patológico que sí discrimina, y dos perillas que no sirven

`patologico_escaneado` da **0,00 % en 88 de 99 celdas** (`bench/k-por-motor.md`). Un
documento que todos los motores resuelven perfectamente no mide nada. Lo que sigue es
el proceso completo, incluidos los dos intentos que fallaron.

### 3.1 La ablación: cuál de las cinco patologías de escáner rompe el OCR

Partiendo de la primera candidata que salió pared (92,62 % con `psm 3`), se apaga una
patología cada vez. **MEDIDO**, `spa`, ImageMagick, CER con acentos:

| variante | qué cambia | `psm 3` | `psm 11` | Δ `psm 11` |
|---|---|---:|---:|---:|
| *(base)* | — | 92,62 | 86,41 | — |
| `abl_p5b_ilum` | iluminación 58/68 → **85/90** | **17,28** | **11,74** | **−74,67** |
| `abl_p5b_imp02` | polvo 0,10 → **0,02** | 42,45 | 35,40 | **−51,01** |
| `abl_p5b_niv12` | contraste `24%,80%` → `12%,90%` | 82,89 | 66,28 | −20,13 |
| `abl_p5b_blur06` | desenfoque 1,0 → 0,6 | 66,61 | 71,31 | −15,10 |
| `abl_p5b_jq60` | JPEG 40 → 60 | 100,00 | 77,85 | −8,56 |
| `abl_p5b_sinray` | **sin** rayas de sensor | 92,62 | 87,75 | **+1,34** |
| `abl_p5b_rui10` | ruido gaussiano 0,25 → 0,10 | 100,00 | 88,93 | **+2,52** |

**Tres lecturas:**

1. **La iluminación no uniforme es la patología dominante: 74,67 puntos.** Ninguna otra
   se le acerca.
2. **Las rayas de sensor no valen nada: 1,34 puntos.** Es la patología que más «se ve»
   en una miniatura y la que menos mide. **Se conservan en la receta** porque cuestan
   cero y hacen el documento más creíble, pero **no son una variable**.
3. **Quitar ruido gaussiano EMPEORA: +2,52 puntos**, y el fichero encoge de 174 KB a
   156 KB. Es exactamente el mecanismo que `bench/corpus-d4.md` §3 midió sobre otro
   documento y otra degradación: **el ruido actúa como tramado y obliga al JPEG a
   conservar detalle que si no colapsa en bloques planos.** Segunda confirmación
   independiente.

### 3.2 Primer intento de escalera: la iluminación. **FALLÓ, y ese fallo es el hallazgo**

Si la iluminación vale 74,67 puntos, parece la perilla obvia para construir una
escalera. Se barrió en 7 puntos con el polvo fijo en 0,045. **MEDIDO:**

| viñeta/lámpara | `psm 3` | `psm 11` |
|---|---:|---:|
| 78/85 | 5,20 | 3,69 |
| 74/81 | 5,03 | 4,36 |
| **70/78** | **72,82** | **60,07** |
| 66/74 | 79,36 | 46,48 |
| 62/71 | 82,21 | 37,25 |
| 56/66 | 78,36 | 64,43 |
| 50/61 | 54,87 | 38,93 |

> **La iluminación no produce un gradiente: produce un INTERRUPTOR.** De 5,03 % a
> 72,82 % en un escalón de **4 puntos de gris**, y después **no es monótona**: más
> oscuro llega a ser mejor (54,87 % con 50/61 frente a 82,21 % con 62/71).

**Es lo esperable, y por eso vale como regla y no como anécdota:** con umbral global
tipo Otsu, la iluminación no degrada el trazo, **mueve el histograma entero** hasta que
la binarización colapsa de golpe. **La patología más potente es la que peor sirve para
construir corpus**, y las dos cosas tienen la misma causa.

*(Y explica de paso por qué la iluminación no uniforme es la patología que más se
menciona en la literatura de escaneado y la que peor se estudia con CER medio: sobre un
documento entero es binaria.)*

### 3.3 Segundo intento: el polvo. **Ésta sí**

Iluminación **fija** en 78/85 —el lado bueno del acantilado, donde sigue siendo una
patología visible pero no un interruptor— y el polvo como única variable. **MEDIDO:**

| `-attenuate` del impulso | `psm 3` | `psm 11` | va al corpus como |
|---|---:|---:|---|
| 0,045 | 5,20 | 3,69 | — |
| 0,080 | 4,70 | 5,87 | — |
| **0,120** | **16,28** | **10,74** | `patologico_d5a` |
| 0,180 | 25,00 | 18,12 | — |
| **0,250** | **32,05** | **14,60** | `patologico_d5b` |
| **0,350** | **56,04** | **31,88** | **`patologico_d5`** (canónico) |
| **0,500** | 49,33 | 53,02 | `patologico_d5e` (cota superior) |

Monótona en `psm 3` de 0,08 a 0,35 y con **51 puntos de recorrido**. El polvo borra
trazo de forma probabilística, que es justo lo que un gradiente necesita.

**El canónico es `patologico_d5` (polvo 0,35).** Cumple el criterio de éxito que `d4`
declaró antes de medir, traducido a las configuraciones que aquí hay:

| exigencia | resultado | veredicto |
|---|---|---|
| ≥1 configuración en la banda 15–60 % | **seis de seis**: 56,04 / 36,74 / 31,88 / 59,56 / 43,12 / 38,42 | **CUMPLE** |
| ≥2 configuraciones separadas por >10 puntos | `psm 3 eng` ↔ `psm 11 spa`: **27,68** | **CUMPLE** |
| ninguna configuración a 0,00 % | mínimo **31,88 %** | **CUMPLE** |

**`patologico_d5e` (polvo 0,50) NO es más difícil que el canónico con `psm 3`**
(49,33 frente a 56,04) y sí lo es con `psm 11` (53,02 frente a 31,88). Se conserva
como cota superior declarada, pero **el orden de dificultad depende del `--psm`**: otra
vez el par.

---

## 4. El «efecto del rasterizador», desmontado

Esto no estaba en el encargo. Salió de una comprobación de rutina y **corrige una cifra
publicada**, así que va entero.

`bench/k-por-motor.md` §6.2 mide que **el rasterizador vale 33 puntos de CER** en
Tesseract: *«misma geometría (1294×1716) y misma profundidad: Tesseract da 84,56 %
desde ImageMagick y 51,34 % desde Ghostscript»*. Al reproducirlo, **las dos cifras
salieron exactamente iguales** — 84,56 y 51,34, a la centésima, con otro arnés y otro
agente. Buen control.

Pero al comparar los dos PNG apareció algo que no encajaba:

```
magick_ppp200__escaneado_d4.png   sha256 de los píxeles crudos: 94cfdbda…
gs_ppp200__escaneado_d4.png       sha256 de los píxeles crudos: 94cfdbda…
```

**Los píxeles son idénticos bit a bit.** Si los píxeles son idénticos, la diferencia no
puede estar en ellos. Lo que sí difiere es la cabecera:

| | densidad declarada | unidades |
|---|---|---|
| ImageMagick | 200 | **`Undefined`** |
| Ghostscript | 78,74 | **`PixelsPerCentimeter`** (= 200 ppp) |

**El A/B mínimo — MEDIDO.** `A` = el PNG de ImageMagick tal cual. `B` = **el mismo
PNG** con `-units PixelsPerInch -density N`, sin tocar un píxel. `C` = el de
Ghostscript.

| documento | psm | A ImageMagick | **B ImageMagick + dpi** | C Ghostscript | ¿B = C? | ¿píxeles idénticos? | A − C |
|---|---:|---:|---:|---:|---|---|---:|
| `escaneado_d4` | 3 | 84,56 | **51,34** | 51,34 | **sí** | **sí** | **+33,22** |
| `escaneado_d4` | 11 | 41,78 | 40,60 | 40,60 | **sí** | **sí** | +1,18 |
| `realista_d5b` | 3 | 37,92 | 23,66 | 23,66 | **sí** | **sí** | +14,26 |
| `realista_d5e` | 3 | 74,83 | 90,27 | 90,27 | **sí** | **sí** | **−15,44** |
| `realista_d5` | 11 | 27,01 | 18,29 | 18,29 | **sí** | **sí** | +8,72 |
| `realista_d5` | 3 | 31,71 | 25,17 | 25,17 | **sí** | **sí** | +6,54 |
| `patologico_d5` | 3 | 56,04 | 54,53 | 54,53 | **sí** | **sí** | +1,51 |
| `patologico_d5` | 11 | 31,88 | 32,55 | 32,55 | **sí** | **sí** | −0,67 |
| `patologico_d5b` | 3 | 32,05 | 31,04 | 31,04 | **sí** | **sí** | +1,01 |
| `patologico_d5b` | 11 | 14,60 | 12,75 | 12,75 | **sí** | **sí** | +1,85 |
| `escaneado_d5` | 3 y 11 | 10,07 / 10,23 | 10,07 / 10,23 | 10,07 / 10,23 | **sí** | **sí** | **0,00** |
| `escaneado_d5b` | 3 y 11 | 28,69 / 25,34 | 28,69 / 25,34 | 28,69 / 25,34 | **sí** | **sí** | **0,00** |

**16 de 16 celdas: `B = C` exactamente, y los píxeles idénticos en las tres columnas.**

**Y el mecanismo, sondeado en ejecución y no deducido.** El `stderr` de Tesseract sobre
el mismo raster de 200 ppp:

```
A (unidades Undefined):        Estimating resolution as 403
                               Detected 36 diacritics
C (PixelsPerCentimeter):       Detected 51 diacritics
```

**Tesseract no encuentra resolución válida en el `pHYs`, la estima en 403 ppp sobre un
raster que tiene 200, y con eso cambia su análisis de maquetación.** Los diacríticos
detectados pasan de 36 a 51.

### 4.1 Qué se corrige y qué queda en pie

1. **La cifra de `k-por-motor.md` §6.2 es correcta; su ATRIBUCIÓN no.** No son 33
   puntos «del rasterizador»: son 33 puntos **de escribir o no escribir la resolución
   en la cabecera del raster**. Ghostscript la escribe siempre; ImageMagick, sólo si se
   le pide.
2. **Y eso convierte un problema de comparabilidad en una regla de una línea.** Es
   gratis: `-units PixelsPerInch -density N` en el raster. **Va en el adaptador del
   motor, junto al `k`.**
3. **Pero no es «declarar siempre gana».** En `realista_d5e` con `psm 3`, declarar la
   densidad **empeora 15,44 puntos** (74,83 → 90,27). Como el `k` y como el
   dispositivo: **es del par (documento, configuración)**. Lo que no admite discusión
   es lo otro: **no declararla deja que Tesseract se invente 403 ppp**, y un número
   inventado no es una línea base.
4. **El efecto es nulo (0,00 en 8 de 8 celdas) en los cuatro documentos de bajo ppp.**
   No porque el rasterizador dé lo mismo —da lo mismo en los doce, los píxeles son
   idénticos— sino porque a 60–90 ppp la resolución estimada y la real están cerca.

> **Regla candidata para FileX (R8):** *el adaptador que entrega un raster a un motor de
> OCR escribe en él la resolución en pulgadas. Y ninguna cifra de CER se publica sin
> decir si la llevaba.* **MEDIDO sobre Tesseract; PENDIENTE en PaddleOCR, RapidOCR,
> EasyOCR y docling**, que reciben arrays y no ficheros y probablemente son inmunes —
> **lo cual es la mitad más importante de la comprobación**, porque significaría que
> las tablas de Tesseract del proyecto no son comparables con las de los demás.

---

## 5. B12 — la degradación realista, medida en el píxel

`bench/corpus-d4.md` §5.3 lo dejó escrito: *«Un escaneo real añade sombra de
encuadernación, curvatura y transparencia del papel, que aquí no están. PENDIENTE.»*

La receta `realista` añade las tres, **en el orden físico**: el reverso se transparenta
sobre el maestro (misma hoja), luego se gira y reduce, luego se comba (`-wave`, que
desplaza verticalmente en función de `x`, que es como se comba un renglón cerca del
lomo), luego se multiplica la sombra del canto interior, y al final ruido y JPEG.

**Declarar una patología sin medirla es el error que hace inútil a
`patologico_escaneado`**, así que las tres se comprueban en el píxel
(`sonda_degradacion.py`). **MEDIDO:**

| documento | sombra (lum. izq/der) | giro medido | **curvatura (residuo)** | zona blanca del maestro |
|---|---:|---:|---:|---:|
| `realista_d5a` (onda 6) | 0,8707 | −0,52° | **1,9 px** | 0,9205 |
| `realista_d5b` (onda 12) | 0,8225 | −1,07° | **3,2 px** | 0,8603 |
| **`realista_d5` (onda 20)** | **0,7877** | +1,36° | **6,0 px** | **0,7991** |
| `realista_d5e` (onda 28) | 0,7790 | −2,14° | **7,3 px** | 0,7378 |
| **`abl_r5_sinonda`** (control, onda **0**) | 0,7877 | +1,51° | **0,4 px** | 0,7991 |
| `escaneado_d4` (ninguna de las tres) | **0,9879** | — | — | 0,7201 |

- **Sombra de encuadernación: presente y monótona** (0,87 → 0,78) frente a **0,99** de
  `escaneado_d4`, que no la tiene.
- **Curvatura: presente y monótona** (1,9 → 7,3 px) **y el control lo cierra**: el
  mismo documento con `onda = 0` y **todo lo demás idéntico** (misma sombra 0,7877,
  misma zona blanca 0,7991, mismo `sha256` de configuración salvo la onda) da **0,4 px**.
- **Transparencia: presente y monótona** (0,92 → 0,74) en una zona que en el maestro es
  blanco puro.

**Dos avisos honestos sobre la sonda, y los dos son fallos que hay que declarar:**

1. **La primera versión de la sonda de curvatura no medía curvatura.** Buscaba «la fila
   más oscura» por franjas y daba **200 px de falso positivo sobre `escaneado_d4`**,
   que no está combado. Se sustituyó por correlación cruzada del perfil de tinta.
2. **La segunda tampoco, del todo: el giro también desplaza el renglón linealmente con
   `x`** (a −4° y 900 px de recorrido, 63 px). La versión válida es la tercera: **el
   residuo tras quitar la recta**. Y **sigue saturando** sobre `patologico_d5` (polvo
   0,35: la correlación se engancha a la iluminación, no al renglón) y sobre
   `escaneado_d4` (−4° se sale del rango de búsqueda de ±60 px). **Las filas de
   `patologico_*` y `escaneado_d4` de esa columna NO son medida** y por eso no están en
   la tabla.

### 5.1 La ablación de la curvatura, que sale al revés

`abl_r5_sinonda` frente a `realista_d5`, mismos parámetros salvo la onda. **MEDIDO:**

| | `psm 3` | `psm 11` |
|---|---:|---:|
| `realista_d5` (onda 20) | **31,71** | 27,01 |
| `abl_r5_sinonda` (onda 0) | **89,77** | **21,14** |

**Quitar la curvatura empeora `psm 3` en 58,06 puntos y mejora `psm 11` en 5,87.** El
`psm 3` de Tesseract vuelve a comportarse como midió `k-por-motor.md` §6.1: es
inestable sobre documentos degradados, y su cifra no se puede leer como «dificultad del
documento». **La curvatura, por sí sola, no es la perilla dominante de esta receta**;
la sombra y la transparencia sí mueven el resultado de forma monótona.

---

## 6. ¿Sirven los tres corpus? Los tres criterios del encargo, uno a uno

### 6.1 «NO da 0,00 % de CER en todas las configuraciones»

**MEDIDO.** 15 documentos × 3 `--psm` (3, 6, 11) × 2 idiomas (`spa`, `eng`), ppp
nativos, ImageMagick. **90 celdas.**

| documento | ppp nat | mín. de las 6 | máx. de las 6 | recorrido |
|---|---:|---:|---:|---:|
| `escaneado_d5b` | 60 | **25,34** | 38,09 | 12,75 |
| **`escaneado_d5`** | **72** | **10,07** | 25,17 | 15,10 |
| `escaneado_d5c` | 80 | **2,01** | 19,13 | 17,12 |
| `escaneado_d5a` | 90 | **1,17** | 12,58 | 11,41 |
| `patologico_d5a` | 200 | **10,74** | 42,95 | 32,21 |
| `patologico_d5b` | 200 | **14,60** | 44,63 | 30,03 |
| **`patologico_d5`** | **200** | **31,88** | 59,56 | 27,68 |
| `patologico_d5e` | 200 | **42,79** | 56,21 | 13,42 |
| `realista_d5a` | 200 | **0,17** | 11,24 | 11,07 |
| `realista_d5b` | 200 | **9,40** | 41,95 | 32,55 |
| **`realista_d5`** | **200** | **27,01** | 35,23 | 8,22 |
| `realista_d5e` | 200 | **36,07** | 76,85 | 40,78 |
| *(control)* `d5_limpio` | 72 | 6,21 | 22,48 | 16,27 |
| *(referencia)* `escaneado_d4` | 200 | 41,78 | 84,56 | 42,78 |
| *(referencia)* `escaneado_d4c` | 200 | 1,85 | 14,93 | 13,08 |

> **Cero celdas a 0,00 % en las 90.** El mínimo del corpus nuevo es **0,17 %**
> (`realista_d5a`, que es el escalón fácil de su familia y está para eso).
> `patologico_escaneado` daba **88 celdas de 99 a cero**. **CUMPLE.**

### 6.2 «Produce un gradiente: que los cuatro tamaños de fuente den cifras distintas»

**MEDIDO**, desglose por bloque, `psm 11`, `spa`, ppp nativos:

| documento | título (24/26 pt) | subtítulo (13/18) | cuerpo (11/13) | letra pequeña (7/9) | ¿monótono? | config. de 6 con las 4 distintas |
|---|---:|---:|---:|---:|---|---:|
| `escaneado_d5b` | 0,00 | 0,00 | 5,77 | **74,65** | **sí** | 3/6 |
| **`escaneado_d5`** | 0,00 | 0,00 | 0,64 | **45,54** | **sí** | 4/6 |
| `escaneado_d5c` | 0,00 | 0,00 | 0,32 | **10,33** | **sí** | 4/6 |
| `escaneado_d5a` | 0,00 | 0,00 | 0,00 | **5,16** | **sí** | 4/6 |
| `patologico_d5a` | 8,00 | 41,86 | 5,45 | 20,19 | no | **6/6** |
| `patologico_d5b` | 24,00 | 9,30 | 9,94 | 27,23 | no | **6/6** |
| **`patologico_d5`** | 32,00 | 32,56 | 15,38 | **69,01** | no | **6/6** |
| `patologico_d5e` | 4,00 | 58,14 | 32,05 | **74,65** | no | **6/6** |
| `realista_d5b` | 8,00 | 4,65 | 7,69 | **37,56** | no | **6/6** |
| **`realista_d5`** | 24,00 | 16,28 | 24,04 | **65,73** | no | **6/6** |
| `realista_d5e` | 32,00 | 18,60 | 36,54 | **70,89** | no | **6/6** |

**Dos familias distintas, y hay que decirlo así:**

- **B15 da un gradiente MONÓTONO en el tamaño de letra** —que es lo que se pedía— pero
  con sólo **tres** valores distintos en `spa`: el título y el subtítulo salen los dos a
  0,00. **Con `eng` sí salen los cuatro distintos** (p. ej. `escaneado_d5`, `psm 3`,
  `eng`: 4,00 / 4,65 / 7,69 / 61,03), y por eso la columna dice 4/6. **CUMPLE con
  matiz**: el gradiente es real y monótono, pero para verlo con cuatro cifras hay que
  usar una configuración que ya falle un poco en los bloques grandes.
- **B19 y B12 dan las cuatro cifras distintas en las 6 de 6 configuraciones**, pero
  **no monótonas**: el subtítulo (una sola línea de 46 caracteres, 2,17 puntos de CER
  por carácter) es ruidoso, y en `patologico_*` la viñeta castiga por posición y no por
  tamaño. **CUMPLE**, y el matiz importa: en estas dos familias el gradiente es
  **espacial** además de tipográfico.

### 6.3 «Tiene sus ppp nativos donde dijiste que los tiene»

**MEDIDO** leyendo cada PDF con `pypdfium2` (no declarado a mano):

| documento | ppp nativos leídos | px de la imagen incrustada | ancho de página |
|---|---:|---|---:|
| `escaneado_d5b` | **60,0** | 388×531 | 465,60 pt |
| `escaneado_d5` | **72,0** | 465×636 | 465,00 pt |
| `escaneado_d5c` | **80,0** | 517×708 | 465,30 pt |
| `escaneado_d5a` | **90,0** | 582×801 | 465,60 pt |
| los ocho de `patologico_d5*` y `realista_d5*` | **200,0** | 1294×1734–1782 | 465,84 pt |

**CUMPLE.** (Los cuatro de B15 tienen la página unas décimas de punto más estrecha
porque el ancho en píxeles es entero a un ppp bajo; es un efecto de redondeo de
±0,84 pt sobre 465,84 y no cambia el ppp calculado.)

---

## 7. Reproducibilidad

### 7.1 El determinismo, comprobado entre tandas — MEDIDO

No hay `n≥9` porque no se publica ni un tiempo. Lo que sí se comprobó es que **la misma
entrada da la misma salida en tandas distintas**, que es lo que hace falta para que las
cifras de arriba valgan:

| control | resultado |
|---|---|
| **5 ficheros regenerados** con los mismos parámetros en tandas distintas | **mismo `sha256` del `.jpg`** en los 5 (`patologico_d5a/b/·`, `realista_d5/e`) |
| `escaneado_d5` medido en **4 tandas** distintas | 10,07 / 10,23 las cuatro veces |
| `escaneado_d4`, `psm 3`, `spa`, ImageMagick | 84,56 en dos tandas — **y reproduce el 84,56 de `k-por-motor.md` §6.2** |
| `escaneado_d4`, `psm 3`, `spa`, Ghostscript | 51,34 — **reproduce el 51,34 de `k-por-motor.md` §6.2 a la centésima** |
| `escaneado_d4`, `psm 11`, `spa` | 41,78 — **reproduce el 41,78 de `k-por-motor.md`** |

**Tres cifras de otro agente reproducidas exactamente con otro arnés.**

### 7.2 Y una ampliación de la trampa 22 — MEDIDO

`CLAUDE.md` trampa 22 dice que el **PDF** de ImageMagick no es reproducible y el
**JPEG** sí. Se confirma, y se añade un tercer nivel: **el PNG maestro tampoco lo es**.
Su `sha256` cambió en **las ocho ejecuciones** del generador (seis valores distintos observados:
(`d7419ae9…`, `749e8859…`, `8dee94a7…`, `61c1590f…`, `0f1cce69…`, `65ac94fc…`)
mientras los JPEG derivados salían **idénticos**. Es decir: **la diferencia está en los
metadatos del PNG, no en los píxeles**.

> **La columna comprobable de un `MANIFIESTO` de ImageMagick es el `sha256` del JPEG
> intermedio. El del PNG maestro y el del PDF sirven para detectar corrupción, no para
> verificar una regeneración.**

---

## 8. Lo que NO resuelve, y lo que queda PENDIENTE

- **Todo este informe es Tesseract.** Nueve configuraciones de OCR barren estos doce
  documentos en el encargo siguiente; hasta entonces, **ninguna de las conclusiones de
  §2 sobre el suelo de 100 puede darse por buena para PaddleOCR, RapidOCR, EasyOCR ni
  docling**. Y `k-por-motor.md` ya midió que el `--psm` de Tesseract mueve 42,78 puntos:
  **el motor que valida este corpus es el más ruidoso que hay.** **PENDIENTE.**
- **El ~125 ppp de §2.3 es una hipótesis, no un número.** Sale de cuatro documentos que
  comparten generador y de un solo motor. **PENDIENTE**: barrer 100–150 con los nueve.
- **La regla R8 candidata de §4.1 está medida sólo donde el motor lee un FICHERO.**
  PaddleOCR, RapidOCR y EasyOCR reciben arrays de numpy y no deberían ver el `pHYs`.
  **Si son inmunes, la consecuencia es grande: las tablas de Tesseract del proyecto no
  son comparables con las de los demás motores salvo que se declare la densidad.**
  **PENDIENTE, y es lo primero que hay que comprobar.**
- **B19 no cubre la iluminación no uniforme como variable graduable**, porque §3.2 mide
  que no lo es. Queda cubierta como **patología presente y fija** (78/85 en los cuatro).
  Un corpus que quiera medir robustez a iluminación necesita **binarización local**
  como variable, no la iluminación como escalón. **PENDIENTE.**
- **La curvatura no es la perilla dominante de B12** (§5.1) y su ablación sale al revés
  con `psm 3`. Habría que separar las tres degradaciones realistas en tres ablaciones
  limpias, como se hizo con las cinco patológicas. **PENDIENTE.**
- **`patologico_escaneado` NO se ha tocado ni se propone borrar.** `patologico_d5*`
  ocupa su hueco funcional; qué hacer con el viejo es decisión de otro.
- **La sonda de curvatura satura** por encima de ~3,5° de giro y con polvo ≥0,35
  (§5). No sirve para auditar `escaneado_d4` ni `patologico_d5`.

---

## 9. Reglas del encargo, cumplidas — y lo que falló

| regla | estado |
|---|---|
| Escribir **sólo** en `corpus/pdf/{escaneado,patologico,realista}_d5*`, `corpus/pdf/MANIFIESTO-d5.md`, `corpus/pdf/REFERENCIA-d5.txt`, `bench/corpus-d5.md` y `bench/salidas-corpus-d5/**` | **Cumplida.** Ni `filex/`, ni `bench/scripts/`, ni ningún `.md` maestro, ni los directorios de otros agentes, ni los diez PDF que ya existían |
| No hacer `git add` ni `git commit` | **Cumplida.** Nada versionado |
| **NO tocar la GPU ni tomar el lock** | **Cumplida.** `magick` y `tesseract` son CPU; el fichero de lock no se abrió |
| Arneses compartidos, copiados y no modificados | **Cumplida.** `ocr_eval_d4.py` y `d4_texto.py` copiados **byte a byte** (`sha256` idénticos, verificado); `gen_corpus_ocr.sh`, `gen_corpus_d4.py`, `ocr_eval.py`, `mcp_probe*.py` y `referencia.json` **ni abiertos ni modificados** |
| Decir **qué evaluador acentuado** se usa | **Cumplida.** `bench/salidas-corpus-d4/ocr_eval_d4.py`, `rid="d4"`, `sha256` en la cabecera de este informe y en el `MANIFIESTO` |
| `-seed` fijo en todo `+noise` | **Cumplida.** `magick -seed 20260822` en las 4 recetas. Comprobado con 5 ficheros regenerados: mismo `sha256` de `.jpg` |
| Directorio de trabajo desechable, listado antes y después | **Cumplida.** `cwd=TMP` en **todas** las invocaciones de `magick`, `gs` y `tesseract`; el censo de la raíz del repositorio dice **«ficheros nuevos NO pedidos: ninguno»** en las **ocho** ejecuciones del generador |
| `stdin=DEVNULL` y timeouts explícitos | **Cumplida.** Los dos en el 100 % de las invocaciones (300 s para `magick`, 600 s para `tesseract` y `gs`). Ningún proceso colgado |
| Idioma de OCR por **lista blanca** (trampa 18) | **Cumplida.** `IDIOMAS = ("spa", "eng")` y `SystemExit` fuera de ella. `TESSDATA_PREFIX` a `C:\Program Files\PDFgear\tessdata` |
| Comprobar que los `.pdf` van por LFS | **Cumplida.** `git check-attr filter` dice `lfs` en los **12** |
| Dos intentos por problema, luego documentar | **Cumplida.** Ver abajo |
| Borrar los intermedios grandes, dejar `MANIFIESTO` | **Cumplida.** **157,3 MB** borrados (`img/` y `tmp/`); se conservan los `.json`, las **220 salidas de OCR** en `texto/` y los registros |
| No versionar salidas binarias regenerables | **Cumplida.** Al corpus van 12 PDF, **1,69 MB en total**, que son el producto pedido |

### Lo que falló, con el error exacto

1. **`gray210` no es un color válido en esta build de ImageMagick.**
   `magick.exe: no decode delegate for this image format 'gray210' @
   error/constitute.c/ReadImage/753`. Los nombres `grayNN` son **porcentajes (0–100)**,
   no valores 0–255. Corregido a `gray84/88/92`. Coste: una regeneración.
2. **Primer intento de escalera para B19: acantilado.** Mover iluminación y polvo a la
   vez dio 5,87 % → 91,78 % en un escalón. **Documentado como medida (§3.2) en vez de
   insistir**, y resuelto con una sola perilla al segundo intento.
3. **La sonda de curvatura falló dos veces antes de medir algo.** Primero por
   estadístico malo (argmin de la fila más oscura: 200 px de falso positivo sobre un
   documento sin curvar); después por confundir giro con curvatura. La tercera versión
   —residuo tras quitar la recta— **sí mide**, y se validó con un control generado a
   propósito (`onda = 0` → 0,4 px). **Sigue saturando** en dos casos, declarados en §5.
4. **La familia B15 no da las cuatro cifras del gradiente en `spa`**, sólo tres (título
   y subtítulo empatan a 0,00). Es una limitación real del diseño: a 72 ppp con 26 pt
   de título, el bloque grande es fácil. Se declara en §6.2 en vez de maquillarla.

---

## 10. Ficheros

Todo en **`bench/salidas-corpus-d5/`**, con `MANIFIESTO.md`:

| fichero | qué es |
|---|---|
| `d4_texto.py`, `ocr_eval_d4.py` | **copias byte a byte** de `bench/salidas-corpus-d4/`. Se importan, no se modifican |
| `d5_texto.py` | las dos maquetas (`m200` heredada de `d4`, `m72` para bajo ppp). Importa `BLOQUES` de `d4_texto` |
| `gen_corpus_d5.py` | generador: 3 recetas, 12 candidatas al corpus, 7 ablaciones, 13 puntos de barrido |
| `tess_lote_d5.py` | banco de Tesseract: rasteriza (ImageMagick o Ghostscript), OCR con lista blanca de idioma, evalúa |
| `sonda_densidad.py` | el A/B de §4: mismo PNG con y sin densidad declarada |
| `sonda_degradacion.py` | §5: sombra, curvatura (residuo) y transparencia, medidas en el píxel |
| `manifiesto_d5.py` | lee los ppp nativos del PDF, calcula `sha256` y escribe `corpus/pdf/REFERENCIA-d5.txt` |
| `tablas_d5.py` → `tablas.md` | las **siete** tablas completas, incluidas las que no caben aquí |
| `json/` | 13 ficheros de resultados: **266 celdas de OCR** en nueve tandas, mas las candidatas y las dos sondas |
| `texto/` | las **220** salidas literales de OCR |
| `logs/` | registros de las tandas de generación |

Y en **`corpus/pdf/`**: `escaneado_d5{,a,b,c}.pdf`, `patologico_d5{,a,b,e}.pdf`,
`realista_d5{,a,b,e}.pdf`, **`MANIFIESTO-d5.md`** y **`REFERENCIA-d5.txt`**.
