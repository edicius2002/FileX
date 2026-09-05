# Los nueve lectores de TIFF y GIF pasan de CERO líneas de cuerpo ejecutadas a enteros — y hay tres defectos y dos refutaciones propias

**Rama:** `cob/tiffgif` · **Fecha:** 2026-09-05 · **Todo MEDIDO salvo lo marcado PENDIENTE.**

Salidas: `bench/salidas-cobertura-tiffgif/` · Pruebas: `pruebas/test_cob_tiffgif.py`
· Fixtures: `pruebas/fixtures_cob_tiffgif.py`

---

## 0. El titular, que no es un porcentaje

En la cobertura base del proyecto, los nueve lectores de TIFF y GIF escritos a
mano de `filex/verificador.py` tenían **exactamente una línea ejecutada cada
uno: la del `def`**, que se ejecuta al importar el módulo. **Los nueve cuerpos
estaban a cero.** Las 517 pruebas de la suite entraban en el fichero y no
pisaban ninguno.

| Función | Línea | Cuerpo, base | Cuerpo, ahora |
|---|---|---|---|
| `_alfa_min_tiff` | 2844 | **0 de 81** | 81 de 81 |
| `_tiff` | 997 | **0 de 45** | 45 de 45 |
| `_alfa_min_gif` | 3026 | **0 de 44** | 44 de 44 |
| `_lzw_gif_usa` | 2698 | **0 de 36** | 36 de 36 |
| `_gif_bloques` | 2983 | **0 de 35** | 35 de 35 |
| `_gif` | 954 | **0 de 34** | 34 de 34 |
| `_lzw_tiff` | 2658 | **0 de 33** | 33 de 33 |
| `_tiff_ifd0` | 2775 | **0 de 29** | 29 de 29 |
| `_tiff_descomprimir` | 2811 | **0 de 9** | 9 de 9 |
| **TOTAL del carril** | | **0 de 346** | **346 de 346** |

Y **61 líneas más** de `verificador.py` que la base daba por no ejecutadas caen
de paso, porque están en el camino: `alfa_minimo` (18), `_packbits` (13),
`_tiff_min_fila_16` (11), `_desfiltrar_carril` (9), `_rep` (5),
`_tiff_min_fila_8` (3) y `sondear_en_proceso` (2). **407 líneas en total.**

Dos números que **no** se publican como conclusión y por qué:

* el `percent_covered` global del JSON (**9 %**) es el de una tanda de **un solo
  módulo de pruebas**, no el del proyecto. No se ejecutó la suite completa a
  propósito (§4 de este informe);
* **ningún tiempo absoluto** (§3 de `CLAUDE.md`). Los 74 veredictos son
  deterministas: tres pasadas seguidas, `OK` las tres.

---

## 1. Por qué este cubo importa más que su tamaño

`filex/verificador.py` trae **dos descodificadores LZW propios**, y no son
intercambiables: TIFF empaqueta MSB primero y sube el ancho de código **un
código antes de agotarlo** (*early change*, TIFF6 §13); GIF empaqueta LSB
primero y sube el ancho justo al agotarlo. El propio comentario del fichero lo
dice: *«usar uno por el otro no da error: da bytes plausibles y equivocados, que
es la peor clase de fallo para un verificador»*.

Lo que sale de ahí es `alfa_min`, y `alfa_min` decide si una conversión conservó
el canal alfa. **La trampa 1 del proyecto —el «alfa trivial»— vive exactamente
en este cubo**: un fichero puede *declarar* alfa y ser enteramente opaco, y el
único que puede separarlos es este código.

---

## 2. Los fixtures van como CÓDIGO, y los tres testigos que no pueden ir así

**Nada nuevo en `corpus/`.** Sería Git LFS —cuota de 1 GB/mes (trampa 103)— y
arrastraría la trampa 34 (un worktree nuevo trae punteros de 130 B). Y los casos
que hacen falta no los escribe ningún motor a petición: TIFF planar, 16 bits
big-endian, `Predictor 3`, `SampleFormat` de coma flotante, `RowsPerStrip = 0`,
`BitsPerSample` con cuenta cero, IFD con tipos que el lector no empaqueta, GIF
con índice transparente **declarado y no usado**. `fixtures_cob_tiffgif.py`
emite los bytes con `struct`, sin un solo subproceso.

**Pero hay una cosa que un constructor propio NO puede validar: el DIALECTO.**
Un codificador propio y un descodificador propio que compartan el mismo error
del *early change* se dan la razón el uno al otro y la prueba sale verde. Es la
trampa 116 en su forma exacta. Por eso hay **tres testigos externos** de
ImageMagick empotrados en base64, con su `sha256` comprobado antes de usarlos y
su orden de reproducción declarada (`MANIFIESTO.md`):

* **`l32.tiff`** (692 B) — su flujo LZW son **510 B y llega a códigos de 10
  bits**, así que ejercita el cambio de ancho, que es donde vive el dialecto.
  `_lzw_tiff` lo descodifica **byte a byte igual** que el gemelo sin comprimir
  `n32.tiff`, 448 de 448.
* **`tr2.gif`** (49 B) — transparencia real escrita por otro programa.

Se eligió el fichero **más pequeño que cruza a 10 bits** midiendo, no a ojo: a
32×14 el flujo llega a 10 bits (692 B); a 48×24 llega a 11 (1 514 B). Se publica
el pequeño.

Dos avisos del propio `CLAUDE.md` que se respetaron al generarlos: `+noise
Gaussian` **exige `-seed`** o el fixture no se reproduce (trampa 22), y `magick`
escribe **paleta por defecto con ≤256 colores** (trampa 30) — por eso el testigo
de TIFF va con `-alpha off -depth 8` y el de GIF se comprueba, no se supone.

**Los dos codificadores LZW del fixture están DERIVADOS del descodificador que
miden, y eso se dice.** El ancho de código del descodificador va siempre **una
entrada por detrás** del codificador (el codificador añade la entrada antes de
escribir el código siguiente; el descodificador la añade después de leerlo), así
que la condición de subida no es la misma a los dos lados. Derivarla vale para
**cobertura** y **no vale como prueba de corrección**: eso lo hacen los testigos.
La ida y vuelta se comprueba hasta **120 000 bytes** aleatorios, que cruza los
cuatro anchos y dispara el `ClearCode` por diccionario lleno.

---

## 3. La regla que hace que esto valga algo: 25 controles de discriminación

**La cobertura es la única métrica de este proyecto que se puede subir sin medir
nada.** Un `try: f(x) except: pass` sube el porcentaje y no afirma nada.

Por eso **25 de las 74 pruebas son controles positivos**: cargan una copia de
`filex/verificador.py` con **UNA línea cambiada** y exigen que la misma
comprobación se ponga **ROJA**. Si pasa con el código roto, la prueba falla con
`NO DISCRIMINA`.

**El mutante se construye en memoria.** No se toca `filex/` en el disco: estas
funciones están dentro del cierre de llamadas de `verificar()`, así que
cualquier edición caducaría las 232 aristas selladas (trampa 32). Al terminar,
`git status` sobre `filex/` está **limpio**, y hay una prueba que lo comprueba.

Tres controles sobre el propio mutante, y los tres los ha pagado ya el
repositorio:

* **IDENTIDAD** — el texto viejo aparece **exactamente una vez** (si no, la
  mutación no está anclada) y la fuente mutada es **distinta** de la original.
  Es la trampa 119 en su forma de A/B: `git stash push <fichero>` sobre un
  fichero ya commiteado **no hace nada, devuelve 0 y no avisa**, y el A/B sale
  verde comparando el código consigo mismo.
* **COMPILACIÓN** — la fuente mutada **compila** (trampa 60: una fuente que no
  compila hace pasar cualquier `assertNotEqual`).
* **ALCANCE** — se acepta como discriminación un `AssertionError` (la
  comprobación llegó a juzgar un valor) **o** cualquier otra excepción **cuya
  traza pase por el mutante** (la línea cambiada se ejecutó). Lo que **no** se
  acepta es una excepción que no toca el mutante: sería un fallo del arnés
  disfrazado de detección (trampa 38). Y ese filtro es lo que cierra la trampa
  109: si una comprobación se parase en una guarda anterior, la línea mutada no
  aparecería en la traza.

### La pregunta que el arnés contesta con una medida, no con un argumento

El procedimiento literal del carril es *«rompe una línea del fichero, comprueba
que la prueba se pone roja, deshaz con `git checkout --`»*. Aquí se `exec`uta la
fuente mutada en un módulo nuevo. **Que las dos cosas sean lo mismo es una
afirmación**, y en este repositorio las afirmaciones se miden:
`test_el_mutante_en_memoria_equivale_a_editar_el_FICHERO` escribe la misma
fuente mutada en un **fichero de verdad**, lo **importa** con `importlib` como
cualquier módulo, y comprueba que los dos caminos dan **exactamente el mismo
diccionario** sobre el mismo TIFF, y que los dos **difieren del código sano**.

### Las mutaciones, una por comprobación

| Función | Línea cambiada | Qué rompe |
|---|---|---|
| `_lzw_tiff` | `prox + 1 >= (1 << ancho)` → `prox >= …` | convierte el *early change* de TIFF en el ancho de GIF |
| `_lzw_tiff` | `del dic[258:]` → `del dic[4096:]` | el `ClearCode` no vacía el diccionario |
| `_lzw_tiff` | `ent = prev + prev[:1]` → `ent = prev` | el caso KwKwK pierde una letra |
| `_lzw_gif_usa` | `prox >= (1 << ancho)` → `prox + 1 >= …` | el dialecto de GIF pasa a ser el de TIFF |
| `_lzw_gif_usa` | `mcs + 1` → `mcs + 2` tras el `ClearCode` | ancho de código equivocado tras el Clear |
| `_lzw_gif_usa` | `leidos >= tope` → `leidos >= tope * 10**9` | el corte por tope deja de cortar |
| `_gif` | `be=False` → `be=True` en el descriptor de pantalla | ancho y alto al revés |
| `_gif` | `2 ** ((c[4] & 0x07) + 1) if c[4] & 0x80 else 0` → sin el `else` | paleta declarada donde no la hay |
| `_gif` | `if desc[8] & 0x80:` → `& 0x00` | no salta la tabla LOCAL de color |
| `_gif_bloques` | `i += 3 * n_local` → `i += n_local` | salta la tabla local por entradas, no por bytes |
| `_tiff` | `be = cab[:2] == b"MM"` → `b"II"` | endianness invertida |
| `_tiff` | `round(campos[282][0] * 2.54)` → `/ 2.54` | centímetros mal convertidos a ppp |
| `_tiff` | `n_img < 64` → `n_img < 128` | el tope de IFD deja de topar |
| `_tiff` | `if tam > 4:` → `if tam > 4000:` | no va a buscar el valor externo |
| `_tiff` | `d["canales"] in (2, 4)` → `in (2,)` | RGBA deja de declarar alfa |
| `_tiff_ifd0` | `if etiq not in _TIFF_ETIQ_ALFA:` → `if etiq in …` | filtra al revés |
| `_tiff_descomprimir` | PackBits → `_lzw_tiff` | dialecto cruzado |
| `_alfa_min_tiff` | `(spp - 1) * ancho_m` → `0 * ancho_m` | **lee el carril del ROJO en vez del del ALFA** |
| `_alfa_min_tiff` | `mn < tope and not exacto` → sólo `mn == 0` | la cota deja de cortar |
| `_alfa_min_tiff` | `mn in (0, tope)` → `mn == 0` | un opaco deja de declararse exacto |
| `_alfa_min_tiff` | `if 322 in c or 323 in c:` → `if False:` | el caso de teselas deja de detectarse |
| `_tiff_min_fila_16` | `min(lo)` → `max(lo)` | el atajo del byte alto saturado |
| `_alfa_min_gif` | `if not (gce and gce["transparente"]):` → `if not gce:` | confunde «hay GCE» con «declara transparencia» |
| `_alfa_min_gif` | la guarda de «no cubre el lienzo» → `if False:` | pierde la transparencia de borde |
| `_alfa_min_gif` | `n_img >= 1` → `n_img >= 99` | pierde la nota del GIF animado |

**La mutación estrella es la de `_alfa_min_tiff`**: cambiar `(spp - 1)` por `0`
hace que la función lea el carril del **rojo** en vez del del **alfa**. No lanza,
no avisa: **devuelve otro número**, y ese número es el veredicto del punto 1 del
contrato. Es exactamente el modo de fallo que preocupa en este cubo, y la matriz
de 64 celdas lo caza.

---

## 4. Cómo se midió, con las CUATRO declaraciones (trampas 94 y 101)

* **Intérprete:** `.venv-mcp-filex/Scripts/python.exe`, **Windows**, 3.11.9. Es
  el del repositorio principal invocado por ruta absoluta: el worktree no tiene
  venvs (medido: 0), y se comprobó que `filex.__file__` apunta **a este
  worktree** antes de empezar.
* **Entorno:** sin GPU, sin lock de GPU, sin Docker, sin motores externos en
  tiempo de prueba, sin red, **sin `corpus/`**. `coverage` 7.16.0 desde
  `PYTHONPATH`, **no instalado en ningún `.venv-*`** (§1).
* **Qué quedó fuera:** **la suite completa NO se ejecutó, a propósito.** Había
  cinco carriles más trabajando en la máquina; seis suites a la vez fabrican la
  carga bajo la que `test_cancelacion_procesos` se pone roja sin que nadie toque
  el código (trampas 101 y 123). Por eso **el porcentaje global de `filex/` de
  este informe no es comparable con el 55,1 % de la base**: lo que se publica es
  el **delta por función**, que sí lo es porque se calcula línea a línea contra
  el JSON base. **PENDIENTE: la cifra global la tiene que rehacer quien pueda
  correr la suite entera con la máquina tranquila.**
* **Estado de la máquina:** con otros carriles activos. No se publica ni un
  tiempo; los 74 veredictos son deterministas y se comprobó con **tres pasadas**.

El corpus llegó como **punteros de LFS** (`corpus/imagen/tipico.png` a **130 B**
en vez de 42 855) y se arregló con `git lfs checkout` antes de nada — trampa 34,
por costumbre, aunque ninguna prueba de este carril lo lea.

---

## 5. Lo que la matriz de 64 celdas demuestra

`AlfaTiff.test_matriz` construye **el mismo canal alfa** en 64 ficheros: 2
profundidades (8 y 16 bits) × 4 compresiones (sin comprimir, LZW, Deflate,
PackBits) × 2 `PlanarConfiguration` × 2 predictores × 2 endianness. **Las 64
tienen que devolver el mismo `alfa_min` normalizado y el mismo
`primer_transparente`.**

Es la única forma de que un error de carril, de zancada o de orden de bytes no
se confunda con «el fichero era así»: **el mismo alfa por caminos de código
distintos tiene que dar el mismo número.** La fracción del alfa se construye
igual a 8 y a 16 bits a propósito, así que las dos profundidades se comparan
entre sí y no sólo consigo mismas.

Y el mismo resultado se reprodujo por fuera con **12 variantes generadas con
`magick`** (las cuatro compresiones, las dos endianness, 16 bits con predictor 2,
`-interlace plane`, `-define tiff:rows-per-strip=1`): las 12 dan `alfa_min =
0,443137…` con `exacto=False` y **0,0 con `exacto=True`**, y ese 0,443137 es
`113/255`, el mínimo de la **primera fila con alfa < 1**. Ese contraste está
ahora fijado en `test_llega_por_alfa_minimo`: **`alfa_minimo` por defecto
devuelve una COTA, no el mínimo**, y lo declara con `exacto: False`.

---

## 6. Defectos encontrados

Ninguno se ha parcheado: el carril no toca `filex/`. Van con su caso mínimo y
con su prueba, que hoy fija el comportamiento **actual**.

### D1 — `_gif_bloques` revienta sobre un GIF truncado donde `_gif` sobrevive, y lo que se pierde es el MOTIVO

**MEDIDO.** Barriendo **los 32 cortes** de un GIF mínimo de 44 B, desde la
cabecera completa (13 B) hasta el fichero entero:

* **`_gif`** (la sonda del punto 1) devuelve un recuento en **los 32**. Sus
  guardas `if len(desc) < 9: break` y los dos `if not s` lo sostienen.
* **`_gif_bloques`** revienta a partir del corte que deja el descriptor de
  imagen a medias: `struct.unpack_from("<HHHH", datos, i + 1)` sin comprobar
  longitud → `struct.error`, y más adelante `IndexError` dentro de los
  sub-bloques.
* **`_alfa_min_gif` NO lo atrapa**: itera el generador **fuera** de su `try`, que
  sólo envuelve la llamada a `_lzw_gif_usa`.

**Lo que salva al producto es el `except (OSError, struct.error, IndexError,
ValueError, zlib.error)` de `alfa_minimo`, dos capas más arriba.** Así que esto
**no es un fallo de superficie: es una pérdida de MOTIVO.** `_alfa_min_gif` está
escrito para explicar por qué no puede —«no es un GIF», «GIF sin bloques de
imagen», «LZW del fotograma 1 ilegible: …»— y en este camino lo que llega al
contrato es el volcado de la excepción. En este proyecto **el mensaje es parte
del contrato**, no decoración: un verificador que no distingue «comprobado» de
«no he podido comprobarlo» repite el fallo que el propio repositorio documenta de
markitdown-mcp.

Está fijado en `TruncadosGifDefecto`, con las tres capas medidas por separado
(revienta / no lo atrapa / el despachador sí, y con qué motivo). **Y la prueba
se pondrá roja el día que alguien lo arregle**, con el mensaje que dice qué hacer.

### D2 — `_lzw_gif_usa` no valida `mcs`, que viene de un byte del fichero

**MEDIDO.** `mcs` sale del descriptor de imagen sin comprobar. Con `mcs ≥ 9`,
`[bytes([i]) for i in range(1 << mcs)]` lanza `ValueError: bytes must be in
range(0, 256)` en la primera línea útil.

Por el camino del contrato el comportamiento es **correcto**: `_alfa_min_gif` lo
captura y devuelve `evaluable=False` con motivo *«LZW del fotograma 1 ilegible:
ValueError: …»* y `cota_alfa_min = 0.0`. Cualquier otro llamador recibe la
excepción. Hoy sólo hay uno. Fijado en
`test_mcs_mayor_que_8_lanza_ValueError_y_alfa_min_gif_lo_ATRAPA`.

### D3 — `esperado` significa dos cosas distintas dentro de `_tiff_descomprimir`

**MEDIDO.** En las compresiones 1, 5, 8 y 32946 el parámetro `esperado` es un
**tope exacto**: la salida mide exactamente eso. En **PackBits (32773) no lo
es**: el bucle evalúa `len(out) < n` **antes** de volcar un literal de hasta 128
bytes, así que la salida **se pasa** (medido: 28 bytes pidiendo 17).

No hace daño hoy —el carril del alfa rebana por filas y lo que sobra queda al
final— pero un llamador que lo tome por un tope se lleva una sorpresa, y el
nombre del parámetro invita a tomarlo por un tope. Fijado con la cota real:
se pasa **como mucho un literal completo**.

### D4 — el `raise` de `_tiff_descomprimir` es inalcanzable desde `_alfa_min_tiff`

**MEDIDO.** `_alfa_min_tiff` filtra antes con `_TIFF_COMPR_OK`, que contiene
**exactamente** los cinco códigos que la función sabe tratar (comprobado como
igualdad de conjuntos, no leyendo). Que la guarda y la tabla no puedan separarse
es bueno; que nadie ejecutara nunca el `raise` significaba que **un sexto código
añadido a la tabla sin añadirlo a la función habría salido por una excepción sin
capturar**. Ahora se ejercita como unidad, y la igualdad de conjuntos está
fijada.

### D0 (observación) — la sonda declara alfa en TODO GIF

**MEDIDO.** `_gif` pone `"tiene_alfa": True` como **constante del diccionario
inicial**, sin mirar el fichero. No es un error del lector —en GIF el canal alfa
es una propiedad del formato— pero significa que **el punto 3 del contrato no
puede separar un GIF opaco de uno transparente por la sonda**. Medido sobre
cuatro ficheros que la sonda **no** puede separar y el carril del alfa **sí**:

| GIF | `_gif.tiene_alfa` | `alfa_minimo(exacto=True)` |
|---|---|---|
| opaco, sin GCE | `True` | 1,0 |
| GCE con la bandera de transparencia a 0 | `True` | 1,0 |
| índice transparente **declarado y NO usado** | `True` | 1,0 |
| índice transparente **declarado y usado** | `True` | **0,0** |

La tercera fila es la trampa 1 en el formato donde más duele. **PENDIENTE para
quien lleve las reglas del contrato:** decidir si el punto 3 debe consultar
`alfa_minimo` para GIF o si la constante es deliberada; aquí sólo queda el
número.

---

## 7. Dos refutaciones de hipótesis propias

Refutar algo propio es el resultado más valioso que se puede traer aquí, así que
van con nombre.

### R1 — el atajo de fila opaca de `_alfa_min_tiff` es EXACTO **y NEUTRO**: no se puede discriminar por la salida

**Hipótesis mía, falsa.** Escribí que romper `op_a` en la rama del predictor 2
haría que «el veredicto CAMBIE». **No cambia.** Medido:

* romper `op_a` hace que las filas opacas dejen de saltarse, pero
  `_tiff_min_fila_8` las des-predice con el filtro `Sub` y devuelve **el mismo
  255**;
* `filas_leidas` **tampoco** se mueve, porque se incrementa **antes** del atajo.

El atajo es exacto y **su defecto es invisible por la salida**: lo único que
cambia es el tiempo, y §3 prohíbe publicar tiempos. Las líneas están **cubiertas**
y **no discriminadas**, y eso queda escrito. La comprobación de alfa trivial se
ancló entonces a la regla que **sí** es observable —`r["exacto"] = exacto or mn
in (0, tope)`: un opaco tiene `mn == tope` y por eso se declara exacto aunque se
pidiera la versión corta— y con esa mutación discrimina.

### R2 — el diccionario rancio de `_lzw_gif_usa` es INVISIBLE, y el motivo es estructural

**Intento mío de discriminar `del dic[fin + 1:]`, refutado y convertido en
resultado.** No se puede por la salida de `_lzw_gif_usa`, y no por falta de
imaginación: **la función contesta una pregunta de PERTENENCIA**, y toda entrada
del diccionario se construye con literales que el descodificador **ya emitió
antes**, así que una entrada rancia no puede introducir ningún índice que no se
hubiera visto ya.

Está medido en
`test_clear_a_mitad_el_diccionario_rancio_es_INVISIBLE`: con el diccionario sin
vaciar, el descodificador emite **bytes distintos** y la respuesta de pertenencia
es **la misma en los 16 índices**. Leído por el otro lado, es una propiedad de
**robustez** de esta API que nadie había escrito. La rama del `ClearCode` se
discrimina entonces por su **otra** línea, el ancho de código.

---

## 8. Lo que queda PENDIENTE

1. **La cifra global de cobertura de `filex/`.** Este informe publica el delta
   por función, que es exacto; el porcentaje global exige la suite completa con
   la máquina tranquila, y eso no se hizo (§4).
2. **D1, D2, D3 y D0** siguen abiertos por diseño del carril (`filex/` no se
   toca). Los cuatro tienen prueba que fija el comportamiento actual y que se
   pondrá roja al arreglarlos, con el mensaje que lo explica.
3. **La cobertura de RAMA no se ha medido**, sólo la de sentencia
   (`branch_coverage: false` en el JSON). Un `if` cuya rama falsa no se toma
   cuenta como cubierto. Con 25 controles de discriminación el riesgo es bajo,
   pero **es una afirmación distinta** y no se ha medido.
4. **`_desfiltrar_carril` queda a 10 de 27** y `alfa_minimo` a 19 de 24: son de
   otros carriles (PNG y el despachador) y se tocan sólo de paso.
5. **La equivalencia mutante-en-memoria ≡ fichero editado está medida sobre UNA
   mutación**, no sobre las 25. Es la que más movía el resultado; extenderla a
   todas es barato y no se hizo.

---

## 9. Lo que este carril NO afirma

* **No afirma que estas nueve funciones sean correctas.** Afirma que 346 líneas
  que nunca se habían ejecutado se ejecutan, que 25 defectos inyectados a mano
  se detectan, y que el dialecto LZW de las dos coincide con el de ImageMagick
  sobre un flujo que cruza a 10 bits. Una función puede estar al 100 % de
  cobertura y equivocarse en un caso que nadie construyó.
* **No afirma nada sobre rendimiento.** Ni un tiempo, por §3 y porque había
  otros cinco carriles en la máquina.
* **No ha tocado `filex/`.** `git status` sobre `filex/` está limpio y hay una
  prueba (`test_no_se_ha_tocado_verificador_en_el_disco`) que lo comprueba en
  cada pasada: si alguien escribe ahí, las 232 aristas selladas caducan.
