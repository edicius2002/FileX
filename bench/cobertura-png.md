# Cobertura del decodificador PNG a mano de `verificador.py` — carril `cob/png`

**Rama `cob/png`. 05/09/2026.** Salidas y manifiesto en
`bench/salidas-cobertura-png/`. Pruebas en `pruebas/test_cob_png.py`, fixtures y
oráculo en `pruebas/fixtures_cob_png.py`. **No se tocó una línea de `filex/`**
(`git status` limpio; `sha256` de `filex/verificador.py` sin mover:
`fc0385500de90f1f8b09cbf10a0eef6a565032163d79732b2bcdc2076779b415`), así que las
232 aristas selladas siguen vivas.

---

## 0. El titular no es un porcentaje

**Once funciones del encargo pasaron de tener cuerpo entero o casi entero sin
ejecutar a estar ejecutadas y JUZGADAS — MEDIDO.** Las cuatro que el encargo
señalaba como «cuerpo entero sin ejecutar ni una vez» son las cuatro primeras:

| Función | Líneas sin ejecutar antes | Ahora ejecutadas | Quedan |
|---|---:|---:|---:|
| `_predice` (los 14 predictores VP8L) | 33 | **33** | 0 |
| `_alfa_min_png_adam7.rellenar` | 12 | **10** | 2 |
| `_leer_plte` | 11 | **11** | 0 |
| `_paeth` | 5 | **5** | 0 |
| `_alfa_min_png` | 106 | **106** | 0 |
| `_alfa_min_png_adam7` (sin `rellenar`) | 94 | **94** | 0 |
| `_rep` | 6 | **6** | 0 |
| `_clamp_half` | 7 | **7** | 0 |
| `_clamp_full` | 5 | **5** | 0 |
| `_selecciona` | 5 | **5** | 0 |
| `_distancia_plano` | 5 | **5** | 0 |
| **Total del encargo** | **289** | **287** | **2** |

Las **2 que quedan** son `verificador.py:1981-1982`, el `except zlib.error: pass`
de `rellenar`, y **no son un hueco de las pruebas: son código muerto en este
build** — §5.

De propina, **el módulo arrastró consigo el decodificador VP8L entero**, que no
estaba en el encargo: `_vp8l_flujo` 96 de 148, `_alfa_min_webp` 35 de 74,
`_huff_tabla` 25 de 27, `_BitsLSB` completa, `png_tinta_cajas` 56 de 71.

**Ganancia total, MEDIDA como intersección** (líneas que la base del maestro tenía
en `missing_lines` y que este módulo, **por sí solo**, ejecuta):

| | |
|---|---:|
| Base (suite completa, 517 pruebas), `filex/verificador.py` | 1 126 / 3 259 = **32,62 %** |
| Sólo `pruebas.test_cob_png` (54 pruebas) | 913 / 3 259 = **26,10 %** |
| **Líneas ganadas** | **698** |
| Suelo, sin ImageMagick nativo (runner de Linux) | **453** — 245 dependen de `magick` |
| Proyección del total de `filex/` | 4 230/7 213 = 58,64 % → **4 928/7 213 = 68,32 %** |

La proyección es **aritmética, no medida**: no se lanzó la suite completa (había
cinco workers más en la máquina; trampas 101 y 123). Lo medido son las 698
líneas de la intersección.

**El suelo de 453 importa y hay que declararlo** (trampa 94): la clase
`Vp8lDeVerdad` escribe un WebP sin pérdida con `magick`, y en un entorno sin
motores se salta con motivo. Las 245 líneas que sólo se alcanzan con ella son
las del decodificador VP8L completo.

---

## 1. Por qué esto no es cobertura de mentira

La cobertura es la única métrica de este proyecto que se puede subir sin medir
nada. **Ninguna prueba de este módulo se limita a llamar.** Hay dos defensas, y
las dos tienen número.

### 1.1 Un oráculo independiente, no un `assertTrue`

`pruebas/fixtures_cob_png.py` trae un **segundo decodificador PNG**, escrito de
cero: reconstruye la imagen COMPLETA con el algoritmo de libro (RFC 2083 §6,
desfiltrado por `bpp` sobre la fila entera) y saca el alfa de los píxeles ya
reconstruidos. `verificador.py` hace lo contrario: extrae **uno de cada `bpp`
bytes** —el carril del alfa— y lo desfiltra por su cuenta, que es rápido, sutil
y correcto, y donde un error de bit **no lanza excepción: devuelve un número**.

El oráculo **no importa nada de `filex.verificador`, ni `_paeth`**. Si lo
hiciera, un error del sujeto se cancelaría con el mismo error del oráculo.

Y el constructor de fixtures se validó con un **tercero**: `magick identify` lee
los **44 de 44** PNG generados con la geometría declarada (`_humo.py`). Sin ese
control, un constructor roto haría que todo el carril midiera su propio error.

### 1.2 Control de discriminación: 29 mutaciones, una por función

`bench/salidas-cobertura-png/discriminacion.py` **rompe una línea de
`filex/verificador.py` y exige que el módulo se ponga ROJO**. Resultado
MEDIDO (`discriminacion.json`), con el control sin mutar en verde (54 pruebas,
`rc=0`):

| | |
|---|---:|
| Mutaciones | 29 |
| Aplicadas (fragmento único **y** la fuente compila) | **29** |
| **Ponen el módulo en rojo** | **26** |
| Verdes con explicación medida (mutantes equivalentes) | 3 |
| Verdes **sin** explicar | **0** |

Muestra de lo que cada mutación destapa:

| id | línea rota | pruebas rojas |
|---|---|---:|
| M01 | `_paeth`: se invierte el desempate `b`/`c` | 9 |
| M05 | `_pixel_en_byte`: `return k` → `return 0` (el fallo del ×4 en la coordenada x) | 3 |
| M07 | tabla de la paleta empaquetada: `min` → `max` | 3 |
| M08 | los bits de relleno de la última celda se cuentan como píxeles | 1 |
| M09 | el carril del alfa se lee un canal desplazado | 13 |
| M10 | al salir del atajo, la fila previa se toma por ceros en vez de 0xFF | 7 |
| M11b | el atajo de fila opaca mira **sólo el primer byte** | 8 |
| M12 | `_ADAM7`: se cambia el paso de la pasada 5 | 14 |
| M13 | Adam7: `xpaso` por `ypaso` al mapear a coordenadas reales | 5 |
| M14b | `rellenar`: al acabarse los IDAT devuelve `True` en vez de `len(buf) >= n` | 1 |
| M14c | `rellenar`: cada bloque aporta un byte menos | 15 |
| M15 | Adam7, pareja hi/lo de 16 bits: `min(lo)` → `max(lo)` | 1 |
| M16 | `_leer_plte`: la paleta se trocea desde el byte 1 | 1 |
| M17 | `_predice` modo 3: devuelve `TL` en vez de `TR` | 2 |
| M19 | `_selecciona`: se invierte el veredicto | 2 |
| M20 | `_clamp_full`: satura en 254 en vez de 255 | 2 |
| M22 | `_distancia_plano`: `cod - 121` | 1 |
| M23 | `_codigo_a_plano`: se invierte el desempate del orden de la tabla | 2 |
| M25 | normalización final de 16 bits | 3 |

Las 29 en `discriminacion.json`. El arnés cumple las trampas del proyecto: **no
usa `git stash push`** (trampa 119 — sobre un fichero commiteado no hace nada y
devuelve 0), guarda los bytes originales y los reescribe, **comprueba el
`sha256` antes y después de cada celda** (trampa 38: registrar que la condición
se dio), y **comprueba que la fuente mutada COMPILA** (trampa 60: un
`SyntaxError` regalaría una discriminación falsa).

### 1.3 Los tres mutantes equivalentes, con su razón medida

Publicar «26 de 29» sin explicar los tres verdes sería la trampa 122 —un motivo
que es una constante—. Los tres son **equivalentes**: cambian el texto y no el
comportamiento.

- **M04 — `_desfiltrar_carril` filtro 4, se intercambian `a` y `b` en la llamada
  a `_paeth`.** **`_paeth` es SIMÉTRICO en sus dos primeros argumentos: 0
  asimetrías en los 8 355 840 tercetos con `a<b`, comprobado exhaustivamente**
  (`_paeth_simetria.py`). No puede cambiar un solo píxel. *Y la primera versión
  del módulo tampoco lo habría visto por otro motivo, que sí era un hueco: con
  un alfa casi opaco los vecinos valen todos 0xFF y `paeth` es simétrico
  también ahí. Se añadió `test_un_alfa_que_varia_EN_LAS_DOS_DIRECCIONES`, que
  ejercita el caso general; M04 sigue verde, ahora por la razón buena.*
- **M11 — `_PATRON_OPACO`, un valor más ESTRICTO.** El patrón de fila opaca es
  un **atajo**: si falla, la fila se reconstruye de verdad y el resultado es el
  mismo. Cuesta tiempo, no corrección. **El lado que sí decide es el contrario**
  —un patrón más LAXO se traga transparencia real— y ése es **M11b, que pone
  rojas 8 pruebas**.
- **M14 — `rellenar`, el tope del bucle.** El bucle decide cuándo dejar de pedir
  bloques; el veredicto lo da el `return len(buf) >= n`, que no se toca, y los
  bloques llegan en bulto. Los dos lados que sí deciden son **M14b** (el fin de
  los IDAT) y **M14c** (lo que aporta cada bloque), y los dos se ven.

**La forma de esto es la trampa 116**: el par «mutación inocua / mutación
peligrosa» sólo dice algo si se publican las dos. Una sola habría dado
«la prueba no juzga el atajo», que es falso.

### 1.4 Que las pruebas LLEGAN a lo que afirman (trampa 109)

Las pruebas de matriz llevan un contador y un `assertEqual` del número de celdas
ejecutadas al final (`self.assertEqual(vistos, 2*3*2*6)`). Una prueba que se
parara en una guarda anterior saldría con `vistos = 0` y se pondría roja — es
exactamente lo que pasó en la primera ejecución de este módulo, y por eso está.

---

## 2. Defecto D1 — un alfa de 16 bits con el byte alto a 255 se declara OPACO, y `exacto=True`

**MEDIDO.** `filex/verificador.py:1913`, rama de canal alfa real de
`_alfa_min_png` con `bps == 2`:

```python
hi, lo = rec[0], rec[1]
if min(hi) < 255:                    # <-- la guarda
    for j in range(an):
        v = (hi[j] << 8) | lo[j]
        ...
```

Si **todos** los píxeles de una fila tienen el byte alto del alfa a `0xFF`, la
fila no se mira. Consecuencia: **todo alfa entre `0xFF00` y `0xFFFE` se pierde**.

Caso mínimo (`test_D1b_el_umbral_esta_justo_en_0xFF00`): un RGBA de 16 bits de
4×2 con un píxel de alfa `0xFF00` y el resto opacos.

| alfa del píxel | oráculo | `_alfa_min_png` (no entrelazado) | `_alfa_min_png_adam7` (mismo fichero, entrelazado) |
|---:|---:|---:|---:|
| 65 279 (`0xFEFF`) | 0,996 111 | **0,996 111** | 0,996 111 |
| 65 280 (`0xFF00`) | 0,996 109 | **1,0** ← | 0,996 109 |
| 65 407 (`0xFF7F`) | 0,998 047 | **1,0** ← | 0,998 047 |
| 65 534 (`0xFFFE`) | 0,999 985 | **1,0** ← | 0,999 985 |

**La rama Adam7 del MISMO fichero lo hace bien** (`verificador.py:2050-2053`:
`if mh == 255: v = 65280 + min(lo)`). Es una asimetría entre dos caminos del
mismo módulo sobre la misma imagen, y no hace falta adjudicar quién tiene razón:
el entrelazado y el oráculo coinciden, el otro no.

**Lo que hace esto peor que un redondeo son dos cosas:**

1. **`exacto` sale `True`.** No es una duda, es una afirmación falsa. Un
   consumidor que respete el contrato (`exacto` significa «lo he recorrido
   entero») no tiene manera de saberlo.
2. **`alfa_no_trivial` pasa de `True` a `False`** (`alfa_minimo` lo calcula como
   `alfa_min < 0.999`), y con él **`primer_transparente` queda en `None`**. En
   `fidelidad_imagen`, la regla **I3** hace entonces
   `cob["I3"] = True  # la entrada no tiene zonas transparentes`: **declara la
   regla CUBIERTA sin haber mirado un solo píxel de la salida.** Es la trampa 1
   —el «alfa trivial»— fabricada por el propio verificador.

Alcance: **10 discrepancias en 212 casos** del barrido (`barrido.json`), **todas
de 16 bits y no entrelazadas**, y **0 de las de 8 bits, paleta o Adam7**.

Está clavado en `DefectosVigentes.test_D1_...` y `test_D1b_...`. **Si esas
pruebas se ponen rojas es que D1 se arregló: hay que quitarlas**, no relajarlas.
El carril tiene prohibido tocar `filex/`.

---

## 3. Defecto D2 — el predictor 13 de VP8L divide como Python y no como C

**MEDIDO.** libwebp (`dsp/lossless.c`) define
`AddSubtractComponentHalf(a, b) = Clip255(a + (a - b) / 2)` con **división entera
de C, que trunca hacia cero**. `verificador.py:2385` usa `//`, que trunca hacia
−infinito. **Difieren en 1 siempre que `a - b` sea negativo e impar.**

Caso mínimo: `L = T = 0x0A0A0A0A`, `TL = 0x0F0F0F0F`. Media = 10; `10 + (10−15)/2`
da **8** en C y **7** en Python.

```
V._clamp_half(0x0A0A0A0A, 0x0A0A0A0A, 0x0F0F0F0F)  -> 0x07070707
libwebp                                            -> 0x08080808
```

Sobre 4 000 vecindades ARGB al azar (`vp8l.json`): **modo 13, 2 460
discrepancias de 4 000; los otros trece modos, 0**. Los predictores encadenan, así
que un error de 1 se propaga a los píxeles siguientes.

**Y aquí va la parte honesta, que refuta el susto:** el alcance sobre ficheros
reales queda **PENDIENTE**. Con un espía sobre `_predice`, **nueve** imágenes
convertidas a WebP sin pérdida por `magick` usan los modos **1, 2, 5, 6, 7, 8,
10, 11 y 12** — y **el 13 ninguna vez**
(`webp_modos.json`, `webp_modos2.json`). Las nueve dan `alfa_min` idéntico al del
PNG de partida. Es decir: **la divergencia con la especificación está medida; su
aparición en un fichero escrito por este `magick` no**. Un fichero escrito por
otro codificador podría dispararla, y el modo 13 es parte del formato.

Las otras cuatro piezas VP8L del encargo **coinciden con libwebp**: `_selecciona`,
`_clamp_full`, `_med2` y `_distancia_plano` (32 de 32 celdas contra los ocho
primeros `kCodeToPlane`, y los 120 desplazamientos generados son exactamente el
conjunto de la norma y van ordenados por distancia).

---

## 4. Defectos D3 y D4, menores pero reales

**D3 — `primer_transparente` significa dos cosas distintas según el camino.**
MEDIDO. En 8 bits, en paleta y en Adam7 el campo es *«el píxel del MÍNIMO de la
primera fila que baja el mínimo»* (`rec[0].index(v)`); en 16 bits sin entrelazar
es *«el primer píxel que BAJA el mínimo corriente»*. Sobre la misma fila de
alfas, en escala:

| entrada | fila de alfas | `primer_transparente` |
|---|---|---|
| RGBA 8 bits | 254, 254, 200, 255 | **(2, 0)** — el mínimo |
| RGBA 16 bits | 65534, 65534, 60000, 65535 | **(0, 0)** — el primero |

Ninguna de las dos lecturas está documentada, y **la regla I3 lee ese píxel de
la salida con `magick`** para decidir sobre qué color se aplanó, así que no es
cosmético. *(Nota de método: no se adjudica cuál es la buena. La prueba general
del módulo sólo exige el invariante que aguanta bajo las dos lecturas —que la
coordenada apunte a un píxel que de verdad tiene alfa < tope— y la coordenada
exacta se comprueba únicamente en los fixtures con **un** píxel transparente.)*

**D4 — la única salida `evaluable=False` que no anula `alfa_min`.** MEDIDO.
`verificador.py:1803`: `return dict(r, evaluable=False, motivo="IHDR ilegible")`
se va con el `alfa_min: 1.0` del valor inicial, mientras las otras seis salidas
no evaluables de la misma función ponen `alfa_min=None`. Un consumidor que lea
`alfa_min` sin mirar `evaluable` recibe **«opaco»** de un fichero que el
verificador acaba de declarar ilegible. Hoy nadie lo lee así (I3 mira
`evaluable` primero), pero es un campo que miente y está clavado en
`test_ihdr_ilegible`.

---

## 5. Las 2 líneas que quedan del encargo son código muerto — MEDIDO

`verificador.py:1981-1982`, dentro de `rellenar`:

```python
except StopIteration:
    try:
        buf.extend(do.flush())
    except zlib.error:      # 1981
        pass                # 1982
```

**`zlib.decompressobj().flush()` no lanza `zlib.error` con este build.**
Barriendo cortes de un flujo comprimido a 1, 2, 3, 5, 8, 13, 21, 34, 55 y
`len−1` bytes, `flush()` devuelve `OK` en los diez (`_zlib_flush.py`); y cuando
el flujo está *corrupto* en vez de truncado, quien lanza es `decompress()`, que
**no** está bajo ese `try` — la excepción sube y la recoge el `except` general de
`alfa_minimo`, que devuelve `evaluable=False` con el motivo.

O sea: no hay entrada que ejecute esas dos líneas por la vía de `rellenar`. **No
se puede cubrir sin fabricar una entrada que este `zlib` no produce**, y
fabricarla con un `mock` sería cobertura sin afirmación, que es justo lo que este
carril tiene prohibido. Se declara **PENDIENTE, con la razón medida**.

*(El mismo patrón está repetido en `_png_filas` —`verificador.py:1787-1788`— y es
parte de las 4 líneas que le quedan a esa función.)*

---

## 6. Qué se cubrió, por familias

54 pruebas, 0 fallos, 0 saltadas con `magick` presente. Las principales:

- **Canal alfa real** (`ct` 4 y 6, 8 y 16 bits, entrelazado y no, los cinco
  filtros): 72 combinaciones con un solo píxel transparente + 32 con alfa al
  azar por píxel + 30 con alfa variando en las dos direcciones, todas contra el
  oráculo.
- **El «alfa trivial» de la trampa 1**: 48 celdas de imagen con canal alfa
  declarado y enteramente opaco → `alfa_min` exactamente 1,0, `exacto=True`,
  `primer_transparente=None` y **la imagen recorrida entera**.
- **Sin mecanismo de alfa** (RGB y gris sin `tRNS`): 14 celdas por la vía de
  cabecera, `filas_leidas == 0`.
- **Atajo de fila opaca**: los cinco filtros × 8/16 bits, y el caso de salir del
  atajo en las filas 0, 1, 2 y 5.
- **Paleta**: `bd` 1/2/4/8, `tRNS` corto y completo, `tRNS` enteramente opaco,
  bits de relleno de la última celda, y **la coordenada x del píxel y no del
  byte** (el fallo del ×4 que documenta `_pixel_en_byte`), con anchuras 1, 3, 7,
  8, 9 y 17 para pillar los bordes de empaquetado.
- **Adam7**: barrido de las **64** posiciones de un mosaico 8×8, un píxel
  transparente en cada una; geometrías 1×1, 1×5, 5×1, 3×2, 2×3, 7×7 y 9×9 donde
  varias pasadas quedan vacías; y paleta entrelazada de 4 bits.
- **Caminos de error**: IHDR ilegible, `tRNS` de color clave en `ct` 0 y 2, sin
  IDAT, profundidad no válida para `ct` 4/6, byte de filtro > 4, IDAT cortado a
  mitad de pasada Adam7, y el flujo partido en cinco IDAT.
- **Exactitud**: `exacto=False` corta en la fila del hueco (`filas_leidas`
  exacto), `exacto` sigue siendo `True` cuando el mínimo es 0, y el corte de
  pasada en Adam7.
- **`_leer_plte`**: paleta leída y usada para decidir la tinta, un trozo `cHRM`
  antes del PLTE, paleta ausente, flujo agotado y paleta de un solo color.
- **`_paeth`**: 17 760 tercetos contra la reescritura independiente, más los
  empates de la norma uno a uno.
- **VP8L**: los 14 modos de `_predice` contra el oráculo de libwebp (>500
  vecindades por modo), el `ValueError` de un modo inexistente, `_selecciona`,
  `_clamp_full`, `_med2`, la tabla de 120 planos y el suelo de distancia 1.
- **Integración WebP** (con `magick`): PNG → WebP sin pérdida → `alfa_minimo`,
  tres imágenes, exigiendo `via` VP8L y el mismo `alfa_min` que el PNG.

---

## 7. Pendientes

1. **`verificador.py:1981-1982`** — código muerto en este build de `zlib` (§5).
   Lo mismo en `_png_filas:1786-1787`. **PENDIENTE con razón medida.**
2. **Alcance real de D2** — el predictor 13 no aparece en 9 de 9 imágenes
   escritas por este `magick`. Haría falta un codificador que lo emita (`cwebp
   -m 6`, u otro) para saber si el defecto llega a un fichero. **PENDIENTE.**
3. **D1, D2, D3 y D4 no están arreglados.** El carril tiene prohibido tocar
   `filex/` (las funciones están dentro del cierre de llamadas de `verificar()`
   y cualquier cambio caduca las 232 aristas selladas). Están documentados con
   caso mínimo y clavados en `DefectosVigentes`.
4. **Lo que le queda a `verificador.py` fuera del encargo**: `_vp8l_flujo` 52
   líneas, `_alfa_min_webp` 39, `png_tinta_cajas` 15, `_lum_png` 12,
   `alfa_minimo` 11 — son las ramas de ALPH crudo/filtrado, la caché de color de
   VP8L y los tipos de color que `png_tinta_cajas` no ejercita. Otro carril.
5. **Aptitud de entorno de `test_cob_png`**: medida SÓLO en esta máquina
   (Windows, 3.11.9). La trampa 104 dice que la aptitud se mide **en** el
   entorno; **no se ha medido en `ubuntu-latest`**, así que no debe entrar en
   `ci/linux-apto.json` sin correrla allí. Lo único que se puede anticipar es
   que el módulo **no lee `corpus/`** (los fixtures se construyen en memoria) y
   que la única clase dependiente del entorno está detrás de
   `skipUnless(shutil.which("magick"))`. **PENDIENTE.**

---

## 8. Texto propuesto para `ESTADO-Y-REPARTO.md` (lo integra el maestro)

> **`bench/cobertura-png.md` — carril `cob/png`, 05/09/2026.** 287 de las 289
> líneas sin ejecutar del decodificador PNG a mano de `verificador.py` quedan
> ejecutadas y juzgadas contra un oráculo independiente; **698 líneas ganadas en
> total** (453 sin ImageMagick), con **26 de 29 mutaciones de una línea poniendo
> el módulo en rojo** y las 3 restantes explicadas como mutantes equivalentes.
> **Cuatro defectos encontrados y no arreglados** (el carril no toca `filex/`):
> **D1**, un alfa de 16 bits entre `0xFF00` y `0xFFFE` se publica como
> `alfa_min = 1.0` **con `exacto = True`** y hace que la regla I3 se declare
> cubierta sin mirar la salida —la rama Adam7 del mismo fichero lo hace bien—;
> **D2**, el predictor 13 de VP8L usa `//` donde libwebp trunca hacia cero
> (2 460 de 4 000 vecindades difieren; su alcance sobre ficheros reales queda
> PENDIENTE: 0 de 9 imágenes de `magick` usan ese modo); **D3**,
> `primer_transparente` significa «el mínimo de la fila» en tres caminos y «el
> primero que baja el mínimo» en el de 16 bits; **D4**, la salida «IHDR
> ilegible» es la única no evaluable que se va con `alfa_min = 1.0`.

## 9. Texto propuesto para `CLAUDE.md` §4 (trampa nueva, al final)

> 130. **Un mutante que no pone roja la suite puede ser un hueco de la prueba o
> un MUTANTE EQUIVALENTE, y la diferencia no se supone: se mide — MEDIDO el
> 05/09** (`bench/cobertura-png.md` §1.3). De 29 mutaciones de una línea sobre
> `filex/verificador.py`, 26 pusieron el módulo en rojo y **3 no**, que es la
> pinta exacta de «estas pruebas ejecutan la función y no la juzgan». Las tres
> eran equivalentes, y cada una necesitó su propia demostración: (a)
> intercambiar `a` y `b` en la llamada a `_paeth` no puede cambiar un píxel
> porque **`_paeth` es simétrico en sus dos primeros argumentos — 0 asimetrías
> en los 8 355 840 tercetos con `a<b`**; (b) endurecer el patrón de fila opaca
> sólo pierde el atajo, y **el lado que sí decide es el contrario** —aflojarlo, y
> ésa pone rojas 8 pruebas—; (c) el tope del bucle de `rellenar` no da el
> veredicto, lo da su `return`, y las dos mutaciones que sí lo tocan se ven.
> **La forma general es la trampa 116 sobre el arnés de mutación: una mutación
> inocua sólo significa algo publicada JUNTO a la peligrosa del mismo
> mecanismo**, y un verde sin su par invita a las dos lecturas malas —tirar unas
> pruebas buenas, o escribir código para tapar un hueco que no existe (trampa
> 58)—. Y el corolario de proceso: **un mutante verde sin explicación medida es
> deuda, no ruido** — el arnés lo marca `SIN EXPLICAR` y el informe publica el
> recuento de los tres.
