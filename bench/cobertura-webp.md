# Cobertura del decodificador WebP/VP8L de `verificador.py` — carril `cob/webp`

**Rama `cob/webp`. 05/09/2026.** Pruebas en `pruebas/test_cob_webp.py` (44) y
fixtures en `pruebas/fixtures_cob_webp.py`. Salidas y arneses en
`bench/salidas-cobertura-webp/`.

**No se tocó una línea de `filex/`.** `git status -- filex/` limpio al terminar
y después de las 40 mutaciones del control de discriminación, que se revierten
con `git checkout -- filex/verificador.py` y **nunca** con `git stash push`
(trampa 119). Las 232 aristas selladas siguen vivas.

**Intérprete, entorno y estado (trampas 94 y 101):** `.venv-mcp-filex\Scripts\
python.exe`, CPython **3.11.9 win32**. Sin GPU, sin Docker, sin lock. **No se
lanzó la suite completa**: había cinco workers más en la máquina y seis suites a
la vez son justo la carga que pone roja `test_cancelacion_procesos` sin que
nadie toque el código (trampas 101 y 123). Todo lo de aquí es
`python -m unittest pruebas.test_cob_webp`.

---

## 0. El titular, y la mitad incómoda

**Las siete funciones del encargo pasan de 272 líneas sin ejecutar a 3 — MEDIDO.**
Las cuatro que el encargo señalaba como «cuerpo entero sin ejecutar ni una vez»
(`_leer_codigo_huffman`, `_leer_simbolo`, `leer`, `ojear`) quedan **a cero**.

| Función | Sin ejecutar en la base | Quedan | |
|---|---:|---:|---|
| `_vp8l_flujo` — el flujo de bits VP8L entero | 148 | **2** | ambas inalcanzables o de coste desproporcionado, §6 |
| `_alfa_min_webp` | 74 | **1** | código muerto, §6 |
| `_leer_codigo_huffman` | 18 | **0** | |
| `_webp` | 14 | **0** | |
| `_leer_simbolo` | 7 | **0** | |
| `leer` | 7 | **0** | |
| `ojear` | 4 | **0** | |
| **Total del encargo** | **272** | **3** | |

**Y la mitad incómoda, que va delante y no en las conclusiones: 310 de esas
líneas ya las había ejecutado `cob/png`.** El reparto del maestro metió
`_predice`, `_selecciona`, `_clamp_full`, `_clamp_half` y `_distancia_plano` en
el cubo PNG creyéndolos predictores de PNG —son de VP8L— y al cubrirlos ese
carril arrastró consigo medio decodificador WebP. La ganancia honesta es la que
se mide **contra la unión**, no contra la base:

| | líneas |
|---|---:|
| `filex/verificador.py` sin ejecutar en la base del maestro (517 pruebas) | 2 133 de 3 259 |
| de esas, las ejecuta `cob/png` (rama `cob/png`, commit `67ec9f7`) | 698 |
| **quedan sin ejecutar tras `cob/png`** | **1 435** |
| **de esas, las ejecuta `cob/webp` — ganancia NETA de este carril** | **138** |
| solape declarado con `cob/png` | 310 |
| ganancia bruta sobre la base sola, si `cob/png` no existiera | 448 |

Reproducible: `python bench/salidas-cobertura-webp/ganancia.py`
(`ganancia.json`). La proyección del fichero es **aritmética, no medida** —unión
de conjuntos de líneas, sin relanzar la suite—: 32,62 % en la base → **55,97 %**
con `cob/png` → **60,20 %** con los dos.

**Dónde están mis 138, y por qué no son residuo.** Las tres piezas que
`cob/png` no tocó son enteras mías, y las tres son ramas de decodificación real,
no de error:

| Función | Quedaban tras `cob/png` | Mías | Qué son |
|---|---:|---:|---|
| `_alph_desfiltrar` | 25 | **25** | los cuatro filtros espaciales del trozo `ALPH` |
| `_webp` | 14 | **14** | el lector de trozos RIFF (`VP8X`, `VP8 `, `VP8L`, `ALPH`, `ANMF`) |
| `_vp8l_flujo` | 52 | **50** | ALPH crudo, caché de color, paleta, referencias hacia atrás, errores |
| `_alfa_min_webp` | 39 | **38** | las siete negativas con motivo |
| `_vp8l_decodificar` | 4 | **4** | firma y versión |
| `_huff_tabla`, `_leer_longitudes`, `_leer_codigo_huffman`, `_leer_simbolo`, `leer` | 7 | **7** | guardas del Huffman |

Su §7.4 lo había anticipado casi exacto —*«le queda `_vp8l_flujo` 52 líneas,
`_alfa_min_webp` 39 … otro carril»*—: este es ese carril, y cierra 138 de esas
141.

---

## 1. Lo que este carril añade que no es cobertura

La cobertura es la única métrica del proyecto que se puede subir sin medir nada.
Aquí hay tres cosas que no son cobertura, y son el motivo de que el carril valga
algo.

1. **Un árbitro externo, y no un `assertTrue`.** Las cifras que esperan las
   pruebas salen de **libwebp 1.6.0** a través de `magick`, no de FileX. Se
   comparan tres cosas por fixture: el mínimo, la posición del primer píxel
   transparente y **el `sha256` del plano entero** (§3).
2. **Dos defectos MEDIDOS**, uno de ellos cerrando un `PENDIENTE` ajeno (§4, §5).
3. **40 mutaciones de una línea, 40 en rojo** (§2) — y las **6 primeras que
   salieron verdes** apuntaron a un hueco real de las pruebas, no a mutantes
   equivalentes.

---

## 2. Control de discriminación: 40 mutaciones, 40 rojas

**Exigencia del encargo: rompe una línea y comprueba que la prueba se pone
roja.** `bench/salidas-cobertura-webp/discriminacion.py` aplica **una** sustitución
textual sobre `filex/verificador.py`, corre el módulo, anota qué pruebas caen y
restaura con `git checkout --`. Lleva dentro un **control de identidad** (trampa
119): comprueba por `sha256` que el fichero cambió en el disco antes de correr, y
que volvió al original después. Resultado en `discriminacion.json`.

**40 mutaciones, 40 ROJAS, 0 sin detectar.**

Cubren las 14 funciones del decodificador: máscara de `leer` y de `ojear`,
`saltar`, consumo de `_leer_simbolo`, código canónico e inversión de bits de
`_huff_tabla`, `ncod` y símbolo simple de `_leer_codigo_huffman`, repetición de
`_leer_longitudes`, bits extra de `_prefijo`, tabla de `_distancia_plano`,
`_med2`, `_selecciona`, tres modos de `_predice`, orden de canales, caché de
color, referencia hacia atrás y su guarda, las cuatro transformaciones de
`_vp8l_flujo`, la imagen meta-Huffman, el alfabeto con caché, el orden RGBA de
salida, el plano alfa del `ALPH`, tres de `_alph_desfiltrar` y tres de
`_alfa_min_webp`.

### 2.1 Las seis que salieron verdes la primera vez, y qué enseñaron

**El plano alfa NO basta para juzgar un decodificador sin pérdida — MEDIDO.**
En la primera pasada, **6 de 40 mutaciones no ponían nada rojo**, y cinco de las
seis eran la misma cosa: **tocaban sólo R, G o B**.

| Mutación | Por qué no se veía |
|---|---|
| transformación 0, predicción de la primera fila (`px[i-1] ^ 1`) | cambia el bit bajo del azul |
| transformación 1, color cruzado (`>> 5` → `>> 4`) | el color cruzado **sólo** toca R y B, por definición |
| transformación 2, restar verde (`+ verde` → `- verde`) | ídem |
| transformación 3, paleta sin empaquetar (`pal[k-1]`) | los 24 colores del fixture tienen el mismo alfa |
| suma acumulada de la paleta | ídem |
| `_webp`, bandera de alfa de `VP8X` (`& 0x10` → `& 0x20`) | con un `ALPH` delante, la otra rama vuelve a poner `tiene_alfa` |

Las cinco primeras se cierran con **`RGBA_LIBWEBP`**, una segunda tabla de
`sha256` del **RGBA entero** que decodifica libwebp de los seis fixtures sin
pérdida sanos. La sexta se cierra con un fixture nuevo —`envolver_vp8x()`, un
`RIFF/WEBP` con `VP8X` y un `VP8 ` de relleno **sin** `ALPH`— que es el único
montaje donde esa bandera decide sola.

**La regla que queda: cuando midas un decodificador por una PROYECCIÓN de su
salida, enumera qué transformaciones del formato son invisibles en esa
proyección.** Es la trampa 53 sobre otro eje: allí una regla de fidelidad sólo
actuaba según el destino; aquí un juicio sólo actúa según el canal que miras. Y
es lo que separa «40 mutaciones detectadas» de «34 detectadas y seis que nadie
habría vuelto a mirar».

---

## 3. Cruce con libwebp

**MEDIDO y reproducible:** `python bench/salidas-cobertura-webp/cruce_libwebp.py`
sobre los 13 fixtures más los cuatro filtros del `ALPH` (`cruce-libwebp.json`).

| | iguales | distintos | no aplica |
|---|---:|---:|---:|
| **plano alfa** (`magick f -alpha extract -depth 8 gray:-`) | **15** | 1 | 1 (animado) |
| **RGBA entero** (`magick f -depth 8 RGBA:-`) | **6** | 1 | 10 (con pérdida) |

El único distinto en las dos filas es `DEFECTO_MODO13`, que es el fixture del
defecto del §4 y está ahí para eso.

**El barrido que lo encontró fue mayor, y esos ficheros no se versionan** (§6 de
`CLAUDE.md`): 31 WebP escritos por `magick` en un directorio de trabajo dieron
**31 de 31 planos alfa idénticos**, y el cruce del **RGBA** sobre sus 25 VP8L dio
**24 de 25** — el que falló fue el que destapó el defecto. **Y el plano alfa de
ese fichero coincidía**, así que el cruce que se habría hecho por defecto no lo
habría visto nunca: es la observación que acabó en §2.1.

### 3.1 El árbitro se comprueba antes de acusar

Cuando `ex/x1.webp` salió con **2 604 de 16 384 bytes distintos**, todas las
diferencias eran de **±1 o ±2 en R, G y B sobre píxeles con alfa ≠ 0**, que es
exactamente la pinta de que `magick` esté des-premultiplicando al escribir
`RGBA:-`. **Descartar el instrumento antes de culpar al sujeto** (trampas 36 y
111) costó un tercer árbitro: se decodificó el **PNG de origen** con `zlib` puro
—sin `magick` y sin FileX—, y como la conversión era *sin pérdida*, el WebP tiene
que reproducirlo al byte. Resultado: **`magick` coincide con el PNG en 0 de
16 384 bytes de diferencia y FileX difiere en 2 604**. El instrumento queda
exonerado con número, no con un argumento.

### 3.2 La mutación del ALPH: el árbitro sigue siendo externo

`magick` sólo escribe el filtro que su heurística elige (0 y 1 en esta máquina),
así que los filtros 2 y 3 de `_alph_desfiltrar` no se alcanzan con ningún fichero
que él quiera escribir. Se alcanzan **mutando cuatro bits** de la cabecera del
trozo `ALPH` de un fichero cuyo plano escribió libwebp, y **el árbitro no cambia**:
`magick` vuelve a leer el fichero mutado y aplica el mismo desfiltrado. Los
cuatro filtros dan **plano idéntico al de libwebp, 4 de 4**.

### 3.3 El escritor a mano lleva su control positivo

Las ramas de error no se alcanzan con un fichero que libwebp acepte escribir, así
que `fixtures_cob_webp.py` trae un escritor de flujos VP8L (`Bits`,
`codigo_simple`, `codigo_dos_de_un_bit`, `vp8l_solido`). **Para que un «falla como
se esperaba» signifique algo hay que demostrar antes que el escritor produce VP8L
de verdad** (trampas 81 y 91): `vp8l_solido()` genera un flujo **válido** y
`magick` lo lee **exactamente igual que FileX y que el color pedido**, en 3 de 3
geometrías (`4x3`, `1x1`, `7x5`). Es el control positivo, y sin él las diez
pruebas de `RamasDeError` no se distinguirían de «mi generador escribe basura».

---

## 4. Defecto D-W1 — el predictor 13 de VP8L, y el cierre del `PENDIENTE` de `cob/png`

**El defecto lo encontró `cob/png` (su D2) y lo dejó a medias, con honestidad:**
la divergencia con la especificación estaba medida y **su alcance sobre ficheros
reales no**, porque el modo 13 no salía en ninguna de sus nueve imágenes. **Aquí
se cierra, y con la explicación de por qué a ellos no les salió.**

### 4.1 El mecanismo, reproducido

`libwebp` define `AddSubtractComponentHalf(a,b) = Clip255(a + (a-b)/2)` con la
división entera de C, que **trunca hacia cero**; `_clamp_half` usa `//`, que
redondea hacia `-inf`. Difieren en 1 cuando `a-b` es **negativo e impar**.

Caso mínimo propio (equivalente al suyo, con otro canal):

```
L = T = 0x00000064   (azul 100)      TL = 0x00000067   (azul 103)
promedio = 100 ;  100 - 103 = -3
Python  -3 // 2 = -2  ->  FileX  0x00000062  (98)
C       -3 /  2 = -1  ->  spec   0x00000063  (99)
```

Diferencial completo, 20 000 vecindades ARGB al azar × 14 modos contra la
especificación reescrita de cero: **el modo 13 discrepa en 12 434 de 20 000; los
otros trece, 0 de 20 000**. Reproduce su 2 460/4 000 y confirma la atribución.

### 4.2 El alcance sobre ficheros reales — MEDIDO, y era su PENDIENTE

`bench/salidas-cobertura-webp/alcance_modo13.py`, 50 imágenes escritas por este
mismo `magick`, resultados en `alcance-modo13.json`:

| Régimen | n | disparan el modo 13 | mueven `alfa_min` |
|---|---:|---:|---:|
| **alfa con textura** (banda estrecha, 24×24) | 40 | **11** | **10** |
| **alfa plano** (la receta de `cob/png`) | 10 | **3** | **0** |

**Tres cosas, y la tercera es la que explica su resultado nulo:**

1. **El modo 13 SÍ aparece en ficheros escritos por este `magick`: 14 de 50.**
   Su *«ninguna de las nueve»* es una propiedad de sus nueve imágenes, no del
   codificador. Es el tercer sesgo de `CLAUDE.md` §3 —el de la **semilla**—:
   midieron una propiedad del FORMATO con una sola familia de entrada.
2. **El defecto llega al número publicado: 10 de 40 mueven `alfa_min`**, con un
   recorrido de **1 a 7 niveles de alfa**. Sobre `DEFECTO_MODO13` (el fixture,
   1 748 B), y en el **mismo píxel (20,18)**, libwebp mide **60** y FileX publica
   **53**.
3. **La atribución es limpia: 0 de las 40 mueven `alfa_min` sin usar el modo
   13.** El único predictor divergente es el único responsable.

**Y por qué a ellos les salió inofensivo, que es el hallazgo de verdad:** con el
alfa **plano**, el modo 13 se usa —3 de 10— y **no mueve `alfa_min` ni una vez**,
porque el error vive en los canales donde hay textura y el canal alfa es
constante. **El daño de un defecto de predictor depende del canal que se
publique, no de si el predictor se usa.** Es la trampa 53 otra vez: no basta con
que el fallo ocurra; hay que probarlo contra la magnitud que el contrato mira.

**No está arreglado, y no se arregla aquí**: `_clamp_half` está dentro del cierre
de llamadas de `verificar()` y tocarlo caduca las 232 aristas.
`test_DEFECTO_el_predictor_13_*` fija el valor **equivocado de hoy** con el
correcto escrito al lado; el día que se arregle, se pondrán rojas, que es lo que
se quiere (trampa 44).

---

## 5. Defecto D-W2 — un WebP animado de N fotogramas se cuenta como N+1

**MEDIDO, y es nuevo.** `_webp` inicializa `d["n_imagenes"] = 1` y la rama
`ANMF` hace `d.get("n_imagenes", 0) + 1`, así que el recuento arranca en 1 en vez
de en 0.

| fichero | trozos `ANMF` reales | `magick identify` | `sondear_en_proceso` |
|---|---:|---:|---:|
| `ANIMADO` (fixture, 200 B) | 2 | 2 | **3** |
| animado de tres fotogramas | 3 | 3 | **4** |

La regla es `N+1` para todo `N`. `n_imagenes` es una **propiedad declarada** que
el punto 3 del contrato compara entre entrada y salida, así que una conversión de
animado a animado que conserve los fotogramas se juzga con los dos lados
inflados en 1 —se compensa— y una que mezcle animado con no animado, no. **No se
ha medido el daño sobre un veredicto real: eso queda PENDIENTE** (§6).

---

## 6. Lo que queda sin ejecutar, y por qué

**Tres líneas de las 272.** Ninguna es un hueco de las pruebas.

| Línea | Qué es | Por qué |
|---|---|---|
| `2169` | `return … "VP8L sin plano alfa"` | **Código muerto.** `_vp8l_decodificar(plano_alfa=False)` devuelve siempre `(w, h, bytearray)`, así que `isinstance(argb, (bytes, bytearray))` no puede ser falso y `alfas` no puede ser `None`. |
| `2453` | `raise … "transformacion VP8L %d desconocida"` | **Código muerto.** El tipo se lee con `br.leer(2)`, que devuelve 0..3, y las cuatro ramas están cubiertas (`0/1` predictor y color cruzado, `2` restar verde, `3` paleta). El `else` es inalcanzable por construcción. |
| `2478` | `raise … "presupuesto de tablas Huffman agotado"` | **Alcanzable, pero desproporcionado.** `_PRESUPUESTO_TABLAS = 4 << 20` y una tabla vale `2^maxl`, así que hacen falta **128 códigos Huffman de profundidad 15** —26 grupos meta-Huffman de cinco códigos cada uno—, construidos bit a bit. Es un guarda anti-DoS y el fixture que lo dispara sería él mismo del tamaño del ataque. **PENDIENTE.** |

**Dos guardas más se cubren a nivel de unidad y hay que decir que lo son**, no
rutas del flujo de bits: `leer(0)` y `_huff_tabla` con longitud > 15. Se
enumeraron **los 22 puntos** donde el decodificador llama a `leer()` y todos piden
`k ≥ 1` (las constantes lo son; `nbits = 2 + 2*leer(3) ≥ 2`; el `extra` de
`_prefijo` sólo se calcula para `sim ≥ 4`, donde vale ≥ 1). Y ninguna longitud
mayor de 15 puede llegar a `_huff_tabla`: las del alfabeto de longitudes se leen
con `leer(3)` (≤ 7) y las del código principal salen de símbolos `cl < 16`. Las
pruebas fijan el **contrato del guarda**, y el informe dice que hoy no se
alcanzan. *(`ojear(0)` **sí** es ruta normal: un código Huffman de un solo símbolo
tiene `maxl == 0` y VP8L no consume ni un bit para leerlo.)*

### Pendientes

1. **`_vp8l_flujo:2478`** — el presupuesto de tablas Huffman. **PENDIENTE.**
2. **El daño de D-W2 sobre un veredicto del contrato.** Se midió el recuento, no
   la consecuencia. **PENDIENTE.**
3. **El modo 13 con OTRO codificador.** Todo lo de §4.2 es `magick`/libwebp 1.6.0.
   `cwebp -m 6` u otro codificador podrían usarlo más o menos. **PENDIENTE.**
4. **Aptitud de entorno.** Medida **sólo** en esta máquina (Windows, 3.11.9). La
   trampa 104 dice que la aptitud se mide **en** el entorno, así que este módulo
   **no debe entrar en `ci/linux-apto.json` sin correrlo allí**. Lo único que se
   puede anticipar: **no lee `corpus/`** —los 13 fixtures viajan como bytes en el
   módulo— y **no invoca ningún motor externo, ni Docker, ni la GPU**, así que no
   depende de `magick` en tiempo de prueba. **PENDIENTE.**
5. **Los defectos no están arreglados**, por la prohibición de tocar `filex/`.

---

## 7. Los fixtures, y por qué no van a `corpus/`

**Trece ficheros WebP, 6 672 B en total, empotrados como literal base64 con su
`sha256` en `MANIFIESTO`.** Los escribió **libwebp 1.6.0** a través de `magick`
7.1.2 Q16-HDRI: es la disciplina de la trampa 71 —*el árbitro del triaje no puede
ser quien escribió el fichero*—. No van a `corpus/` a propósito: sería Git LFS,
con su cuota de 1 GB/mes (trampa 103) y con la trampa 34 encima (punteros de
130 B en cada worktree nuevo).

`bench/salidas-cobertura-webp/generar_fixtures.py` los reproduce desde cero y
**compara el `sha256` de cada uno contra el manifiesto, fallando si alguno se
mueve** — es la orden exacta que pide `CLAUDE.md` §6, en forma de script en vez
de prosa.

### 7.1 Un reproductor que no se ejecuta es prosa: 3 de 13 no reproducían

**MEDIDO, y por eso el script existe.** La primera versión del reproductor
copiaba las órdenes de la sesión, y al ejecutarla **3 de los 13 fixtures salieron
con otro `sha256` y otro tamaño**: `LL_META_HUFFMAN` (2 416 → 2 406 B),
`LL_PALETA_ANCHA` (728 → 742) y `DEFECTO_MODO13` (1 732 → 1 758). La causa es la
trampa 22 —*`+noise` exige `-seed`*— con una vuelta de tuerca: **el `-seed`
estaba puesto, y DETRÁS del generador, donde no surte efecto.**

```
magick -size 24x24 plasma:fractal -seed 21 …   -> distinto cada vez
magick -seed 21 -size 24x24 plasma:fractal …   -> mismo sha256 (verificado)
```

Con el `-seed` delante, los tres reproducen y semillas distintas dan resultados
distintos (control negativo). Los tres fixtures se **regeneraron** con la receta
determinista, y ahora los blobs del módulo de fixtures se escriben **desde el
propio reproductor**, para que no puedan separarse. **13 de 13 reproducen su
`sha256`.**

**La regla: un `MANIFIESTO` con la orden dentro no vale nada hasta que alguien
ejecuta la orden y compara el hash.** El proyecto ya tiene la disciplina de
publicar la orden (§6); lo que faltaba era el paso que la comprueba, y aquí falló
en **el 23 % de los ficheros**.

---

## 8. Texto propuesto para `ESTADO-Y-REPARTO.md` (lo integra el maestro)

> **`bench/cobertura-webp.md` — carril `cob/webp`, 05/09/2026.** Las siete
> funciones del encargo pasan de **272 líneas sin ejecutar a 3** (las tres,
> declaradas: dos son código muerto y la tercera un guarda anti-DoS que exige
> 128 códigos Huffman de profundidad 15). **La ganancia NETA, medida contra la
> unión con `cob/png`, es de 138 líneas**, y 310 son solape declarado con ese
> carril, que arrastró medio decodificador VP8L por un error del reparto: las
> tres piezas enteramente propias son `_alph_desfiltrar` (25/25), `_webp`
> (14/14) y el resto de `_vp8l_flujo` (50 de 52). **40 mutaciones de una línea,
> 40 en rojo**, y las **6 que salieron verdes en la primera pasada** destaparon
> que juzgar un decodificador sin pérdida por su plano alfa deja invisibles el
> color cruzado, el restar verde y la paleta. **Cierra el PENDIENTE 2 de
> `bench/cobertura-png.md`:** el predictor 13 **sí** aparece en ficheros escritos
> por este `magick` (14 de 50) y **mueve el `alfa_min` publicado en 10 de 40**,
> hasta 7 niveles de alfa, con 0 discrepancias atribuibles a otro modo; el
> resultado nulo de `cob/png` se explica porque con **alfa plano** el modo se usa
> y no mueve nada. **Defecto nuevo:** un WebP animado de N fotogramas se cuenta
> como **N+1**.

---

## 9. Trampas nuevas propuestas para `CLAUDE.md` (lo integra el maestro)

> **N. Juzgar un decodificador por una PROYECCIÓN de su salida deja ciegas las
> transformaciones que no tocan esa proyección, y el arnés sale verde — MEDIDO el
> 05/09** (`bench/cobertura-webp.md` §2.1). El decodificador VP8L de
> `verificador.py` se estaba juzgando por el **plano alfa**, que es lo que
> `alfa_minimo()` publica y por tanto lo que parece la magnitud correcta. **6 de
> 40 mutaciones de una línea no ponían nada rojo**, y cinco eran la misma cosa:
> el **color cruzado** y el **restar verde** de VP8L sólo tocan R y B *por
> definición del formato*, y la paleta del fixture tenía alfa constante. La sexta
> es su gemela por el otro lado: estropear la bandera de alfa de `VP8X` no se ve
> **mientras haya un trozo `ALPH`**, porque otra rama vuelve a poner el campo. Se
> cierra con una segunda tabla de verdad —el `sha256` del **RGBA entero** que
> decodifica libwebp— y con un fixture `VP8X` **sin** `ALPH`. **Antes de creerte
> un arnés de decodificador, enumera qué transformaciones del formato son
> invisibles en la magnitud que estás comparando** — y es la trampa 53 en otro
> eje: allí la cobertura de una regla dependía del destino, aquí depende del
> canal.
>
> **N+1. Un `MANIFIESTO` con la orden dentro no vale hasta que alguien la
> EJECUTA y compara el hash: aquí falló en 3 de 13 — MEDIDO el 05/09** (ídem
> §7.1). La regla §6 pide *«la orden exacta que las reproduce»* y se cumple
> escribiéndola; el paso que falta es correrla. Al hacerlo, **3 de 13 fixtures
> salieron con otro `sha256` y otro tamaño**, y la causa es la trampa 22
> —*`+noise` exige `-seed`*— con una vuelta de tuerca que la hace invisible: **el
> `-seed` estaba puesto, y DETRÁS del generador, donde ImageMagick no lo aplica**
> (`magick -size 24x24 plasma:fractal -seed 21` es aleatorio; `magick -seed 21
> -size 24x24 plasma:fractal` es determinista, verificado con dos corridas
> iguales y una semilla distinta como control negativo). Un `-seed` presente en
> el `argv` se lee como *«esto es reproducible»* y por eso nadie lo revisa.
> **Corolario de forma: que los bytes publicados se generen DESDE el
> reproductor**, no al lado, o los dos se separan sin que nada avise — es la
> misma forma que la trampa 92 (*la fuente de verdad es el módulo, no el texto*).
