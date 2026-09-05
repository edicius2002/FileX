# Los siete defectos medidos de `verificador.py`, arreglados en una sola tanda — y las 172 aristas que eso caduca

Carril `fix/verificador`, partiendo de `integra/cobertura` (`4333278`).
**No es una ronda de investigación:** los siete defectos venían localizados,
reproducidos y con prueba que los fijaba, de `bench/cobertura-png.md`,
`bench/cobertura-tiffgif.md`, `bench/cobertura-webp.md` y
`bench/cobertura-fidelidad.md`. Este informe dice qué se arregló, qué prueba se
puso **roja antes** y **verde después** de cada arreglo, cuánto cuesta en
huella, y qué queda PENDIENTE.

**Declaraciones de la medida** (trampas 94 y 101): intérprete
`.venv-mcp-filex\Scripts\python.exe`, **win32, 3.11.9**; sin Docker levantado y
sin GPU (ninguno de los siete lo necesita); **no se lanzó la suite entera** —hay
otro carril en la máquina— sino los siete módulos afectados; el corpus estaba en
punteros de LFS al abrir el *worktree* (**130 B**, trampa 34) y se resolvió con
`git lfs checkout` antes de medir nada (`42 855 B`).

---

## 0. Titular

**Los siete están arreglados y MEDIDOS.** Seis viven dentro del cierre de
llamadas de `verificar()` y **mueven el componente `contrato` de la huella**, lo
que degrada **las 172 aristas selladas de golpe**: era el diseño del carril —un
resondeo en vez de seis—. El séptimo (V5) queda **fuera del cierre y no mueve la
huella**, y eso **no se deduce, se mide**: la fuente de partida con *sólo* el
arreglo 7 aplicado da la misma huella que la fuente de partida.

| | antes | después |
|---|---|---|
| `huella.de_alcance(verificador.py)` | `fe41b4d52413299c` | **`80791e4b492afc94`** |
| nombres en el cierre del contrato | 123 | 123 |
| componentes movidos | — | **`contrato` en los 5 ficheros; `motor` e `invocacion`, ninguno** |
| aristas `sin_sondear` | 0 de 172 | **172 de 172** |
| `pruebas/test_sondeo.py` | `48 tests, OK` | **`48 tests, 6 failures`** — esperado |

Y **la revalidación que el carril anterior no pudo hacer, hecha**: el A/B contra
el patrón oro —completo, con el remapeo por nombre base de la trampa 89— da
**0 veredictos movidos de 38 órdenes** y **0 ficheros movidos de 94**.

---

## 1. Los siete, con su rojo y su verde

**Regla del encargo, cumplida:** cada arreglo tiene al menos una prueba que
estaba roja antes de aplicarlo. Las pruebas no se borraron: se les **dio la
vuelta**, conservando el caso mínimo que reprodujo cada defecto, porque ése es
justo el caso que tiene que seguir vigilándolo.

Registro completo en `bench/salidas-fix-verificador/rojo_antes.txt` (antes) y
`verde_despues.txt` (después), producidos los dos por
`bench/salidas-fix-verificador/correr_modulos.py`.

| # | Defecto | Prueba que se puso ROJA antes | celdas rojas | Después |
|---|---|---|---:|---|
| 1 | alfa de 16 bits entre `0xFF00` y `0xFFFE` dado por opaco, con `exacto=True` | `test_cob_png.DefectosVigentes.test_D1_…SE_VE` y `…test_D1b_el_umbral_que_estaba_en_0xFF00_ya_no_esta` | 3 + 1 | verde |
| 2 | `_gif_bloques` revienta sobre un GIF truncado; `_alfa_min_gif` itera el generador fuera de su `try` | `test_cob_tiffgif.TruncadosGifDefecto` × 4 (`…sobrevive_a_los_mismos_cortes…`, `…ahora_da_un_MOTIVO`, `…publica_ese_mismo_motivo`, `…ningun_corte_deja_escapar…`) | 1+1+1+11 | verde |
| 3 | `_lzw_gif_usa` no valida `mcs` | `test_cob_tiffgif.LzwGif.test_un_mcs_fuera_de_rango_es_un_error_DECLARADO` | 6 | verde |
| 4 | `esperado` no es tope exacto en PackBits | `test_cob_tiffgif.Ifd0YDescompresion.test_descomprimir` | 1 | verde |
| 5 | el predictor 13 divide con `//` donde C trunca hacia cero | `test_cob_png.…test_D2_el_predictor_13_divide_COMO_C`, `…PredictoresVp8l.test_los_catorce_modos_coinciden_con_libwebp`, `test_cob_webp.Predictores.test_el_modo_13_YA_coincide…`, `…DefectosMedidos.test_el_predictor_13_redondea_COMO_libwebp`, `…test_el_predictor_13_ya_no_mueve_el_alfa_min_publicado` | 1 + **1 808** + 1 + 1 + 1 | verde |
| 6 | un WebP animado de N fotogramas se cuenta como N+1 | `test_cob_webp.DefectosMedidos.test_el_webp_animado_cuenta_sus_fotogramas_y_no_uno_mas` | 1 | verde |
| 7 | V5 empareja las pistas por POSICIÓN | `test_cob_fidelidad.FidelidadVideoMotor.test_V5_REORDENAR_las_pistas_ya_NO_le_parece_una_perdida` y `…test_V5_empareja_por_TIPO_y_no_por_posicion` | 1 + 1 (error) | verde |

Recuento de módulos, antes → después:

```
test_cob_png       54 tests  FAILED (failures=1813)  ->  OK
test_cob_tiffgif   75 tests  FAILED (failures=9, errors=12)  ->  OK
test_cob_webp      45 tests  FAILED (failures=4)  ->  OK
test_cob_fidelidad 129 tests FAILED (failures=1, errors=1)  ->  OK
test_contrato_v    19 tests  OK  ->  OK
test_a7_ciego       6 tests  OK  ->  OK
test_sondeo        48 tests  OK  ->  FAILED (failures=6)   <- esperado, §3
```

---

## 2. Qué se cambió, y por qué esa forma y no otra

### 2.1 Defecto 1 — la guarda no era 255, era el mínimo corriente

`_alfa_min_png`, rama de 16 bits, decía `if min(hi) < 255:` y se saltaba la fila
entera cuando todos los bytes altos valían `0xFF`. **El encargo pedía no
inventar una tercera semántica**, y no se ha inventado: la rama Adam7 del mismo
módulo ya acertaba (`if mh == 255: v = 65280 + min(lo)`), y lo que se ha hecho
es que la no entrelazada **coincida con ella**.

La forma elegida es una guarda de una expresión, y es **exacta en las dos
direcciones**:

```python
if min(hi) <= mn_pareja >> 8:
```

Un píxel con `hi > mn_pareja >> 8` cumple `hi << 8 > mn_pareja` y **no puede
bajar el mínimo**, así que saltarse la fila no pierde nada; y con el mínimo
corriente todavía en `0xFFFF` la guarda vale 255, es decir la fila se mira
siempre. Conserva el atajo de rendimiento que el `< 255` buscaba —de hecho lo
aprieta según baja el mínimo— sin conservar el agujero.

**No se toca `primer_transparente`.** El defecto D3 de `cobertura-png.md` —que
las dos vías no significan lo mismo con ese campo— **no está en el encargo**, su
propio informe declara que *«no se adjudica cuál es la buena»*, y su prueba
(`test_D3_las_dos_vias_no_dicen_lo_mismo_de_primer_transparente`) sigue en pie y
**sigue verde**: la fila que usa tiene `min(hi) = 234 < 255`, así que entraba al
bucle antes y entra ahora.

**Demostración de que los dos caminos coinciden — MEDIDO**
(`bench/salidas-fix-verificador/sonda_png16.py`, barrido de 26 alfas de 16 bits
que cruza el umbral, cinco filtros PNG, con `F.referencia` de oráculo). La misma
sonda contra el código de partida es el **control** (trampa 119: se interroga al
sujeto por su `sha256`, no al mandato que creíamos que lo cambiaba):

| sujeto | `sha256[:12]` | plano = oráculo | entrelazado = oráculo | las dos vías coinciden | `exacto=True` |
|---|---|---:|---:|---:|---:|
| `4333278` (partida) | `6008ea33f358` | **10 de 26** | 26 de 26 | 10 de 26 | **26 de 26** |
| árbol de trabajo | `9e91ae3bf763` | **26 de 26** | 26 de 26 | **26 de 26** | 26 de 26 |

Las **16 discrepancias** del control son exactamente las 16 celdas por encima de
`0xFF00`, y **las 16 se publicaban con `exacto=True`**: no era una duda, era una
afirmación falsa. Con el arreglo, `primer_transparente` también coincide en las
26.

### 2.2 Defecto 2 — el generador para donde se le acaban los datos, y su llamador tiene red

Dos mitades, y hacen falta las dos:

* **`_gif_bloques`** lleva ahora tres guardas de longitud —la etiqueta de la
  extensión, los 9 bytes de geometría+banderas del descriptor de imagen, y el
  byte `mcs` tras la tabla local—, así que **para** en vez de lanzar, que es lo
  que ya hacía `_gif` con sus `if len(desc) < 9: break`.
* **`_alfa_min_gif`** itera el generador **dentro** de un `try` (un `while True`
  con `next()` acotado), y si algún día vuelve a lanzar, lo que llega al
  contrato es *«bloques del GIF ilegibles: …»* y no el volcado de una excepción.

Sobre los **32 cortes** del GIF mínimo del fixture: el código de partida
reventaba con `struct.error` e `IndexError`; ahora **0 cortes lanzan** por
`_gif_bloques` y **0 por `_alfa_min_gif`**, y el corte que dejaba el descriptor
a medias devuelve `evaluable=False` con motivo **`"GIF sin bloques de imagen"`**
—una de las frases que la función sabe escribir—.

### 2.3 Defecto 3 — el rango sale del formato, no de la implementación

`_lzw_gif_usa` valida `2 <= mcs <= 8`, que es lo que fija GIF89a, y lanza
`ValueError("mcs de GIF fuera del rango 2..8 del formato: %d")`. Sigue siendo
`ValueError`, así que `_alfa_min_gif` lo captura igual y el contrato ve el mismo
campo: **lo que cambia es el mensaje**, que antes era `bytes must be in
range(0, 256)` —un error de la implementación disfrazado de error del formato—.

**El rango se eligió con censo, no de memoria — MEDIDO**: los GIF del árbol
(corpus + `bench/`) suman **180 bloques de imagen y los 180 declaran `mcs = 8`**,
ninguno otro valor. Los fixtures del carril usan 2, 4, 7 y 8. No hay un solo
fichero en el repositorio al que la validación le cierre la puerta.

### 2.4 Defecto 4 — `esperado` es un tope en las cinco compresiones

Una línea en `_packbits`: `del out[n:]` antes de devolver. El bucle evalúa
`len(out) < n` **antes** de volcar un literal de hasta 128 bytes, así que la
salida se pasaba (28 bytes pidiendo 17) mientras las compresiones 1, 5, 8 y
32946 lo respetaban al byte. La prueba comprueba ahora **la longitud exacta y el
contenido** de los 17 primeros bytes en las cinco.

### 2.5 Defecto 5 — truncar hacia cero, con aritmética entera

`_clamp_half` usaba `//`, que trunca hacia `-infinito`; libwebp usa la división
entera de C, que trunca hacia **cero**. La forma escrita evita la coma flotante
(`int(d/2)` truncaría bien pero pasa por `float`):

```python
d = av - ((c >> desp) & 0xFF)
x = av + (d // 2 if d >= 0 else -((-d) // 2))
```

**El árbitro es libwebp, no este carril**, y en tres niveles a la vez:
`F.clamp_half_ref` / `_ref_predice` (la especificación reescrita en los
fixtures), el barrido de los **catorce** modos sobre 14 semillas ARGB
—`test_los_catorce_modos_coinciden_con_libwebp`, que pasa de **1 808 celdas
rojas a 0**—, y el `sha256` del RGBA entero que `magick` decodifica del fixture
`DEFECTO_MODO13`: **2 304 bytes, `abdc1591415f…`, que ahora es el de los dos**.
En ese fichero, y en el mismo píxel (20,18), `alfa_min` pasa de **53/255 a
60/255**, que es lo que mide libwebp.

### 2.6 Defecto 6 — los fotogramas se cuentan aparte

`_webp` arrancaba `n_imagenes` en 1 y sumaba uno por cada `ANMF`. Ahora hay un
contador local `anmf` que arranca en 0, y `n_imagenes` sólo se sobrescribe si
hubo alguno: `if anmf: d["n_imagenes"] = anmf`. Así el recuento **no depende del
orden de los trozos** —la línea `d["n_imagenes"] = 1` de la rama `VP8X`, que
existía para lo mismo, sobraba y se ha quitado—, y un WebP fijo sigue diciendo 1.
La prueba nueva `test_un_webp_sin_ANMF_sigue_declarando_un_fotograma` cubre ese
otro lado sobre **cinco** fixtures, con un control de la premisa
(`assertNotIn(b"ANMF", datos)`) para que la celda no pueda pasar por vacía.

### 2.7 Defecto 7 — V5 empareja por tipo, y ESTA VEZ se revalidó contra el patrón oro

`fidelidad_video` hacía `y = ts[i] if i < len(ts) else None`. La función nueva
`_emparejar_por_tipo(te, ts)` devuelve una lista paralela a `te` emparejando por
**(tipo de pista, orden dentro de su tipo)**, con `None` donde la salida no
tiene con quién.

**El carril anterior no lo arregló por un motivo explícito de alcance**, no de
dificultad: *«no puedo revalidarlo contra el patrón oro desde este worktree,
porque `bench/salidas-referencia/` sólo trae `MANIFIESTO.md` y
`referencia.json`»* (trampa 89). **Eso se cierra aquí, con el remedio que la
propia trampa prescribe** —`referencia.json` guarda la ruta absoluta de cada
salida y se remapea por nombre base—, y en dos niveles:

* `bench/salidas-fix-verificador/revalidar_v5.py`: A/B del emparejamiento viejo
  contra el nuevo sobre las **39 órdenes** del patrón oro, con **una sola**
  lectura de `ffprobe` por fichero, dentro de la misma tanda. **38 de 39
  mapean** (la que falta, `pdf.rasterizado`, tiene por entrada un intermedio que
  no está en `corpus/`). De ellas: 9 con destino donde V5 no se evalúa, 23 en
  las que la entrada no trae ninguna etiqueta —V5 se declara `informativo` sin
  discriminar, con los dos emparejamientos—, y **6 evaluadas de verdad**.
  **Cambian 0 de 6.**
* `bench/salidas-fix-verificador/ab_contrato_oro.py`: `verificar()` **entero**,
  las dos versiones del módulo en la misma tanda sobre las mismas
  (entrada, salida). **38 evaluadas, 0 veredictos movidos.**

**Y aquí va la mitad incómoda, porque un resultado nulo necesita saber por qué
es nulo** (trampa 56): de las 6 filas evaluadas, **0 son un reordenamiento de
verdad** —mismo multiconjunto de tipos, distinto orden—. Dos tienen listas de
tipos distintas, pero es que la salida tiene *menos* pistas
(`["video","audio"] → ["audio"]`), no otras. Así que la revalidación demuestra
**que el arreglo no rompe nada del patrón oro**, que es exactamente lo que
faltaba para poder tocar una regla de severidad `aviso`; **no** demuestra que
actúe allí, y no puede: FileX invoca `ffmpeg` con `-map 0` explícito por regla de
diseño, así que sus propias conversiones conservan el orden. Quien ejercita el
reordenamiento es el caso mínimo con `ffmpeg` de verdad
(`test_V5_REORDENAR_las_pistas_ya_NO_le_parece_una_perdida`), que lleva dentro su
control de premisa: **el orden de tipos cambió y ninguna etiqueta desapareció**.

---

## 3. La huella y las 172 aristas — MEDIDO

Instrumento: `bench/salidas-fix-verificador/huella_estado.py`, salidas en
`huella_antes.json` y `huella_despues.json`.

```
antes    interprete 3.11   contrato fe41b4d52413299c   123 nombres en el cierre
después  interprete 3.11   contrato 80791e4b492afc94   123 nombres en el cierre
```

| fichero de sondeo | aristas | componentes movidos | degradadas |
|---|---:|---|---:|
| `filex/sondeo/imagemagick.json` | 62 | `contrato` | 62 |
| `filex/sondeo/ffmpeg.json` | 70 | `contrato` | 70 |
| `filex/sondeo/doc_libreoffice.json` | 16 | `contrato` | 16 |
| `filex/sondeo/doc_pandoc.json` | 16 | `contrato` | 16 |
| `filex/sondeo/doc_calibre.json` | 8 | `contrato` | 8 |
| **total** | **172** | **sólo `contrato`** | **172** |

**`motor` e `invocacion` no se han movido en ninguno de los cinco**, que es la
comprobación de que el carril no ha tocado nada fuera de su sitio.

**Que el arreglo 7 no mueve la huella no se deduce de «`fidelidad_video` no está
en el cierre»: se mide** (`control_huella_v5.py`, `control_huella_v5.json`),
transplantando *sólo* ese arreglo sobre la fuente de partida:

| fuente | `de_alcance` |
|---|---|
| partida (`4333278`) | `fe41b4d52413299c` |
| partida **+ sólo el arreglo 7** | **`fe41b4d52413299c`** (no se mueve) |
| los siete | `80791e4b492afc94` |

Y la comprobación directa sobre el cierre: de las funciones tocadas,
`_alfa_min_png`, `_alfa_min_png_adam7`, `_gif_bloques`, `_alfa_min_gif`,
`_lzw_gif_usa`, `_packbits`, `_tiff_descomprimir`, `_clamp_half` y `_webp` están
**DENTRO**; `fidelidad_video`, `_emparejar_por_tipo` y `_ffprobe_etiquetas`,
**fuera**. El cierre sigue teniendo **123 nombres** antes y después: la función
nueva no ha entrado en él.

### 3.1 `test_sondeo` está en rojo, y es lo esperado

```
Ran 48 tests   FAILED (failures=6)
  test_ningun_motor_disponible_es_no_comparable_bajo_este_interprete  (5 subtests: los 5 motores)
  test_ningun_motor_disponible_tiene_el_sondeo_caducado
      AssertionError: {'imagemagick': ['contrato'], 'ffmpeg': [...], 'doc_calibre': ['contrato'], ...} != {}
```

**No lo he silenciado ni lo he escondido, y no he tocado `filex/sondeo/*.json`.**
Un cambio de huella por arreglo real es legítimo; **resellar sin resondear sería
indulgencia** (trampa 61). El resondeo de las 172 aristas exige los motores y la
máquina en serie, y lo hace el maestro.

---

## 4. Que no se ha roto nada: el A/B ancho, y por qué sale en cero

`bench/salidas-fix-verificador/ab_sonda_alfa.py` corre `sondear_en_proceso` y
`alfa_minimo` de las **dos** versiones —la de partida y la de ahora, cada una
identificada por el `sha256` de su fuente— sobre los mismos **94 ficheros**: los
41 de `corpus/` y **las 53 salidas del patrón oro, las 53 remapeadas**.

**0 ficheros cambian un solo campo.** Y el contrato entero
(`ab_contrato_oro.py`), **0 de 38 órdenes**.

**Por qué sale en cero — MEDIDO** (`censo_alcance.py`, `censo_alcance.json`).
Un cero sin mecanismo no vale nada, así que aquí está el censo de esos 94:

| camino arreglado | ficheros que podrían tocarlo | por qué no lo mueven |
|---|---:|---|
| PNG 16 bits con alfa (defecto 1) | **1** (`tipico.png`) | es el «alfa trivial» de la trampa 1: `alfa_min = 1,0`, opaco de verdad |
| GIF truncado (defecto 2) | 2 GIF, **0 truncados** | los dos están enteros |
| `mcs` fuera de rango (defecto 3) | 2 GIF, **0 fuera de rango** | los 180 bloques del árbol declaran `mcs = 8` |
| TIFF PackBits (defecto 4) | 2 TIFF, **0 en PackBits** | ninguno usa la compresión 32773 |
| predictor 13 (defecto 5) | 6 WebP, **0 usan el modo 13** | 5 resuelven por cabecera y el sexto por el `ALPH`; `_predice` no se llama ni una vez |
| WebP animado (defecto 6) | 6 WebP, **0 animados** | ninguno trae un solo trozo `ANMF` |

Ese *«0 de 6 usan el modo 13»* se midió con un espía sobre `_predice`
(`espia_modo13.py`) **y lleva su control positivo dentro**, porque un cero de un
instrumento que no dispara no es un cero: sobre el fixture `DEFECTO_MODO13` el
mismo espía cuenta **modos 5, 6, 7 y 13** y devuelve `alfa_min = 0,2353` —los
60/255 de libwebp—.

Es decir: **el corpus y el patrón oro no contienen ni un fichero que ejercite
los seis caminos arreglados.** Eso explica el cero, y de paso confirma lo que
`cobertura-webp.md` §4.2 ya había dicho de su propio corpus: el daño del
predictor 13 aparece con **alfa texturado**, y hay que fabricarlo.

---

## 5. Lo que NO se ha hecho, y por qué

* **El resondeo de las 172 aristas: PENDIENTE, del maestro.** No tengo permiso
  para tocar `filex/sondeo/*.json` y no lo he tocado.
* **D3 de `cobertura-png.md`** —`primer_transparente` significa dos cosas según
  el camino— **sigue vigente y sin arreglar**: no está en el encargo, su informe
  no adjudica cuál lectura es la buena, y su prueba sigue verde.
* **D4 de `cobertura-png.md`** —la salida `evaluable=False, motivo="IHDR
  ilegible"` es la única que no anula `alfa_min`— **sigue vigente**: tampoco
  está en el encargo.
* **El reordenamiento de pistas no aparece en el patrón oro** (§2.7), así que la
  revalidación demuestra ausencia de regresión y no presencia de efecto. Si se
  quiere lo segundo sobre material del proyecto, hay que **añadir al patrón oro
  una orden que remuxee sin `-map 0`**, y eso es un cambio del patrón oro que no
  me corresponde.
* **No se ha lanzado la suite entera** (otro carril en la máquina). Los siete
  módulos afectados están en §1; la pasada íntegra la corre el maestro.

## 6. Correcciones propuestas a informes ajenos (no los he tocado)

Sus autores decidirán; el carril tiene prohibido editarlos.

* `bench/cobertura-png.md` §2 y §3, y `bench/cobertura-tiffgif.md` §6 D1/D2/D3,
  y `bench/cobertura-webp.md` §4/§5, y `bench/cobertura-fidelidad.md` §5.2:
  todos dicen *«no se ha parcheado / NO ARREGLADO»* y remiten a pruebas que
  fijan el comportamiento de hoy. **Los siete están arreglados**; conviene una
  nota al principio de cada sección apuntando aquí, y el nombre nuevo de la
  prueba que los sustituye.
* `bench/cobertura-webp.md` §4.2 escribe *«tocarlo caduca las 232 aristas»*. Los
  ficheros de sondeo de este árbol suman **172**, no 232 — probablemente cita el
  recuento del registro de aristas y no el de los sellos. Es la trampa 48 sobre
  otro número: el recuento se publica con la fuente al lado.
* `bench/cobertura-fidelidad.md` §5.2 declara el bloqueo *«no puedo revalidar
  contra el patrón oro desde este worktree»*. **El bloqueo era falso y su
  remedio estaba escrito en la trampa 89**: `referencia.json` trae la ruta
  absoluta y se remapea por nombre base. Es la trampa 95 —*«un rojo se
  investiga; un bloqueo se acepta»*— sobre otro activo.

---

## 7. Ficheros de esta tanda

Todo en `bench/salidas-fix-verificador/`, con su `MANIFIESTO.md`. Son scripts y
JSON: texto barato, que es lo que §6 de `CLAUDE.md` sí manda versionar.
