# El cuarto punto del contrato tenía cubiertos los dos tercios que no detectan nada

**Carril `cob/contrato`.** Objetivo: `filex/verificador.py`, las funciones
`punto4_pedido`, `sondear_subproceso` y `main`, con **187 líneas sin ejecutar**
en las 517 pruebas de la suite.

Entrega: `pruebas/test_cob_contrato.py` (**91 pruebas**),
`bench/salidas-cobertura-contrato/` (manifiesto, cobertura, control de
discriminación y la sonda de la única rama que queda).

**No se ha tocado `filex/`.** Los defectos van como caso mínimo, no como
parche: las tres funciones están dentro del cierre de llamadas de `verificar()`
y cualquier edición caducaría las 232 aristas selladas.

---

## 1. El titular: qué ramas pasaron de sin ejecutar a ejecutadas — MEDIDO

**`punto4_pedido` estaba al 81 % de sus líneas y las 52 que faltaban eran, casi
sin excepción, las que EMITEN UN HALLAZGO.** El punto que `CLAUDE.md` §5
describe como aquel *«sin el cual un redimensionado no solicitado pasa los
otros tres»* tenía ejecutadas sus guardas, sus lecturas de sonda y sus caminos
de salida limpia; **ninguna de sus detecciones**.

Las 21 detecciones que se ejecutan ahora y no se ejecutaban, más las dos ramas
de NO-hallazgo que las hacen creíbles:

| Regla | Severidad | Qué atrapa |
|---|---|---|
| **I1/V7** | fallo | redimensionado NO SOLICITADO (el fallo de image-worker-mcp) |
| **I1** | fallo | dimensiones distintas de las **pedidas** |
| **I1** | aviso | cambia la relación de aspecto: indicio de barras añadidas |
| **P4** | fallo | ppp distinto del pedido |
| **P4** | fallo | PDF→imagen: la resolución no corresponde al ppp pedido |
| **I4** | fallo | degradación de profundidad ni pedida ni inevitable |
| **I5** | informativo | reducción de profundidad inevitable por el techo del destino |
| *(la rama `pass`)* | — | profundidad pedida explícitamente: no es hallazgo |
| **A6** | aviso | profundidad de bits INFLADA sin información nueva |
| **I2** | fallo | se pierde un alfa NO TRIVIAL en un destino que lo admite |
| **I2** | informativo | el destino no admite alfa: pérdida inevitable |
| **I2** | informativo | `min(alfa)` sin calcular: la regla **no es evaluable** |
| **A1/V1** | fallo | la duración cambia más de la tolerancia |
| *(`solo_audio`)* | — | comparar PISTA contra PISTA en vez de contra el contenedor |
| **A3** | informativo | Opus fuerza 48 kHz |
| **A3** | fallo | frecuencia de muestreo alterada sin pedirlo |
| **A2** | fallo | número de canales alterado sin pedirlo |
| **—** | fallo / aviso | bitrate de audio muy lejos (>50 %) / lejos (>15 %) del pedido |
| **P7** | fallo | la caja de página no corresponde a la densidad pedida |
| **P7** | aviso | 1 px → 1 pt: página absurda |
| **P1** | fallo | cambia el número de páginas |
| **D1** | fallo | cambia el número de filas lógicas |
| **D4** | fallo / aviso | cambia la cabecera / BOM UTF-8 sin pedirlo |

Y en `sondear_subproceso` —la vía cara, la que el proyecto evita a propósito
porque *«con subprocesos, en el 38 % de los casos verificar cuesta más que
convertir»*— **no se ejecutaba prácticamente nada**: ni el sondeo de AV, ni el
de imagen, ni el de PDF, ni sus tres caminos de error, ni las tres respuestas
del ternario que convierte la unidad de resolución.

### Las cifras, con su instrumento declarado

| Ámbito | Base (517 pruebas) | Unión con este fichero | Δ |
|---|---:|---:|---:|
| `punto4_pedido`, líneas que faltaban | 52 | **0** | −52 |
| `main`, líneas que faltaban | 55 | **0** | −55 |
| `sondear_subproceso`, líneas que faltaban | 80 | **2** | −78 |
| **Total del encargo** | **187** | **2** | **−185** |
| `punto4_pedido`, ramas sin recorrer | 57 | **0** | −57 |
| `main`, ramas sin recorrer | 22 | **0** | −22 |
| `sondear_subproceso`, ramas sin recorrer | 24 | **1** | −23 |
| `verificador.py`, líneas de sentencia | 1 126 / 3 259 (34,6 %) | **1 518 / 3 259 (46,6 %)** | +392 |
| `verificador.py`, ramas sin recorrer | 1 164 | **964** | −200 |
| `filex/`, líneas de sentencia | 4 230 / 7 213 (58,6 %) | **4 622 / 7 213 (64,1 %)** | +392 |

**La unidad es la LÍNEA DE SENTENCIA ejecutada, y hay que decirlo** (trampa 55):
el «32,6 %» y el «55,1 %» del encargo son el `percent_covered` de `coverage`
**con `--branch`**, que promedia líneas y ramas y es otra métrica. La primera
medida de este carril se tomó **sin** `--branch` y daba un 37,9 % que no era
comparable con nada; se rehízo con el mismo instrumento que la base (trampa 59:
*mide también la versión histórica en tu tanda*, y aquí «versión» es el
instrumento).

De las 392 líneas ganadas, **185 son del encargo y 207 son arrastre** —
`_alfa_min_png` (67), `fidelidad_video` (26), `_png_meta` (22), `alfa_minimo`
(16), `_datos`, `_imprimir`, `_ffmpeg_framemd5`, `_png_filas` (11 cada uno)…—,
que se declaran aparte porque nadie las pidió y no se han calibrado.

---

## 2. Lo que hace que esto valga algo: 49 mutaciones, 49 discriminan — MEDIDO

**La cobertura es la única métrica de este proyecto que se puede subir sin medir
nada.** Un `try: f(x) except: pass` sube el porcentaje y no afirma nada. Por eso
cada prueba se calibró **rompiendo una línea de la función objetivo y
comprobando que se pone roja**. El arnés está versionado
(`bench/salidas-cobertura-contrato/mutaciones.py`) y su tabla completa —qué
pruebas cayeron con cada mutación— en `discriminacion.json`.

Resultado: **49 mutaciones, 49 DISCRIMINAN**, y `filex/verificador.py` queda
limpio al terminar (el arnés lo comprueba por `sha256` antes y después de cada
celda y devuelve `rc=1` si no).

Tres precauciones que el arnés lleva dentro, y las tres estaban ya pagadas:

- **Trampa 119.** Se revierte con `git checkout -- filex/verificador.py`, nunca
  con `git stash push <fichero>`: sobre un fichero commiteado el stash no hace
  nada, devuelve 0 sin aviso y las pruebas corren contra el código **nuevo**,
  con la pinta exacta de *«mis pruebas pasan con el arreglo y sin él»*.
- **Trampa 60.** Se comprueba que la fuente mutada **compila** antes de
  ejecutarla: una mutación que rompe la sintaxis pone rojo el módulo entero y
  esa celda no dice nada sobre la línea.
- **Control de identidad.** Si el patrón de sustitución no casa exactamente una
  vez, la celda se marca `AMBIGUA` y **no cuenta**. En la primera pasada,
  `d["n_subtitulo"] += 1` salió tres veces en el fichero —las otras dos en las
  sondas en proceso— y la celda no medía nada.

### Lo que el control encontró: dos de mis pruebas eran VACUAS

Ese es el resultado que justifica el arnés, y **es una refutación de mi propio
trabajo**. Dos pruebas pasaban con la línea rota y sin ella:

- **M30 — `test_una_sonda_con_error_no_produce_ni_un_hallazgo`.** Comprobaba que
  una sonda con `error` no produce hallazgos, pasándole **dos sondas
  idénticas**: no había hallazgo que suprimir, así que la guarda podía estar o
  no estar. Arreglada dándole a la sonda rota una geometría distinta (que sin la
  guarda produce `I1/V7 fallo`) y añadiendo el **control positivo**: la misma
  sonda **sin** el campo `error` sí dispara.
- **M32 — `test_alfa_min_exacto_recorre_la_imagen_entera`.** Sobre
  `corpus/imagen/alpha.png` la bandera `--exacto` **no cambia nada**, porque el
  código hace `exacto or mn == 0`: si el mínimo es 0 no puede haber nada menor y
  el corte temprano no le quita exactitud. Arreglada con un **gradiente** de
  alfa, donde la bandera cambia el **valor** y no sólo la etiqueta: sin ella,
  `alfa_min = 0,984` leyendo 2 filas; con ella, `alfa_min = 0,0` leyendo 64.

Es la trampa 109 en las dos: una prueba que no llega a la aserción que la
justifica, o que llega por un camino donde el sujeto no puede fallar. Y es la
116 leída al revés: **el control positivo de un arnés de discriminación es el
sujeto CON el defecto**, y aquí el defecto lo puse yo al escribir la prueba.

Una tercera celda, **M08**, fue un falso «no discrimina» **del arnés**: la
mutación cambiaba el *mensaje* del hallazgo y esperaba que cayeran tres pruebas,
pero sólo una afirma sobre el mensaje. Se partió en M08a (mensaje, 1 prueba) y
M08b (apagar la rama, 3 pruebas). **Una mutación mide una cosa**; agrupar dos
efectos en una celda produce un rojo que no es del fichero de pruebas.

---

## 3. Defectos y observaciones, con su caso mínimo

Ninguno se ha parcheado: §1 del `CLAUDE.md` de este carril lo prohíbe.

### O1 — El `--destino` pedido NO participa en el punto 1 — MEDIDO

`punto1_firma` compara la firma real contra
`os.path.splitext(salida)[1]`, **la extensión del fichero de salida**, y nunca
contra `pedido["destino"]`. Pedir un WEBP y entregar un PNG llamado `.png` no
produce ni un hallazgo:

```sh
python -m filex.verificador --salida corpus/imagen/tipico.png \
    --entrada corpus/imagen/tipico.png --destino webp --json
# veredicto: ok_parcial ; 0 hallazgos de severidad fallo ; punto1: evaluado
```

**No es explotable en producción** y hay que decirlo así: FileX construye la
ruta de salida **con** la extensión del destino, así que las dos coinciden
siempre y el caso degenera en el `mentira.webp` que el punto 1 sí atrapa con
`G3 fallo`. Lo que la medida dice es que **desde el CLI las dos pueden diferir y
nadie avisa**: el `--destino` sólo mueve *tolerancias* (el techo de
`PROF_MAX`, `SIN_ALFA`, el caso `gif`). Queda fijado por
`test_el_destino_PEDIDO_no_participa_en_el_punto_1`, que documenta el
comportamiento actual y se pondrá roja el día que cambie.

### O2 — `n_imagenes` cuenta LÍNEAS de `identify`, no imágenes — MEDIDO

`sondear_subproceso` hace `d["n_imagenes"] = len(lineas)` sobre la salida de
`magick identify -format "…%U\n"`. Basta con que **un campo del formato
contenga un salto de línea** para inflar el recuento. Sobre un FITS de **una
sola imagen**, `%U` devuelve `"Undefined\r\nFITS"`, la salida tiene **3 líneas**
y la sonda declara **`n_imagenes: 3`**.

```sh
magick corpus/imagen/trivial.png /tmp/x.fits
python -c "from filex import verificador as V; print(V.sondear_subproceso('/tmp/x.fits')['n_imagenes'])"
# 3
```

**Es latente:** `n_imagenes` no lo consume hoy ningún punto del contrato (se
asigna en NUEVE sitios de `filex/` y no se lee en ninguno — comprobado, no
supuesto), así que no contamina un
solo veredicto publicado. Se anota porque el día que una regla lo use, el dato
es falso para cualquier formato cuyo `identify` emita más de una línea. Está en
`ppp-inalcanzable.json`, campo `n_imagenes_distinto_de_1`.

### O3 — La ayuda del CLI promete `exacto=false` y no siempre es así — MEDIDO

`--alfa-min` documenta que sin `--exacto` *«se corta en el primer píxel no opaco
y se marca exacto=false»*. Sobre `alpha.png` sale **`exacto=true`** sin la
bandera. **El código tiene razón y la ayuda describe el caso general**: con
`mn == 0` no puede existir un valor menor, así que el corte temprano da el
mínimo verdadero. Es la trampa 44 en su forma benigna —el campo es honesto y la
prosa de al lado promete algo más estrecho—, y aparece aquí porque fue lo que
delató la prueba vacua M32.

### O4 — Dos destinos nuevos para G6, encontrados de paso — MEDIDO

Buscando un formato de imagen con alfa no evaluable: **`magick x.png y.heic` y
`magick x.png y.heif` devuelven `rc=0` y entregan un PNG.** Es el fallo
emblemático del proyecto —`magick x.png y.group4`, `firmas-contrato.md` §5— con
dos destinos que aquella lista de 22 no tenía. `G6` los atraparía por el mismo
mecanismo (misma firma que la entrada y no era eso lo que se pedía). Y de la
misma tanda: **`.jxl` se escribe bien y su firma se reconoce (`jxl`), pero
`CAT_POR_FIRMA` no la tiene, así que la sonda devuelve
`categoria: "desconocida"`** y el fichero cae por el `else` de datos. Ninguna de
las dos cosas es de este carril; quedan como PENDIENTE para quien lleve firmas.

### O5 — La regla `solo_audio` se salva hoy por 0,02 ms — MEDIDO

El comentario del código explica que comparar el contenedor de salida contra la
pista de entrada daba un falso fallo de 23 ms en `tipico.mp4`. Medido hoy: el
desvío contenedor↔pista es de **23,2000 ms** y la tolerancia que
`_tolerancia_audio` deriva de la trama de AAC del **origen** (1024 muestras a
44 100 Hz) es de **23,2200 ms**. **Margen: 0,0200 ms.**

O sea: el caso que motivó la regla `solo_audio` **también lo absorbería hoy la
tolerancia de trama**, y por veinte microsegundos. No es un argumento para
quitar la regla —es exactamente al revés: **cualquier fuente con otra frecuencia
de muestreo o con una trama más corta rompe ese margen**, y entonces sólo queda
la comparación pista a pista—. Se anota porque un margen de 0,02 ms sobre una
tolerancia de 23 ms es una coincidencia, no un diseño, y quien mida la regla con
este fichero puede concluir que no hace falta.

---

## 4. Lo que sigue sin cubrir, y por qué

### 4.1 Las dos líneas: el `except` del ppp (3320-3321) — MEDIDO, y no por falta de pruebas

Son el `except (ValueError, IndexError)` del cálculo de `ppp` en
`sondear_subproceso`. La única palanca para entrar es que el `%x` de
`magick identify` no sea parseable como `float`, porque el `-format` es fijo en
el código y este carril no toca `filex/`.

Barrido de **22 formatos** (`sonda_ppp.py` → `ppp-inalcanzable.json`):

| Clase | n | Formatos |
|---|---:|---|
| `%U` = `Undefined` → `ppp = None` | 17 | png tga pbm pgm ppm xpm ico gif webp sgi miff dds xbm jpg hdr pam avif |
| `%U` = `PixelsPerCentimeter` → ×2,54 | 1 | bmp |
| `%U` = `PixelsPerInch` → tal cual | 2 | tif pcx |
| `identify` **falla** (no llega a la rama) | 1 | psd |
| `%x` no parseable | **0** | — |

**Las tres respuestas del ternario sí se ejercitan** (bmp, tif, gif), y **cero
de los 21 formatos que llegan a la rama** producen un `%x` no numérico.

Y una corrección **de mi propia sonda**, que es la trampa 25 otra vez: la
primera pasada declaró *«1 formato con `%x` no parseable»* y era **PSD**, donde
`identify` devuelve `rc=1` y **la rama del ppp ni siquiera se alcanza** —
`sondear_subproceso` sale antes por `if rc != 0 or not out.strip()`. *«No
parseable»* y *«no hubo salida»* se escriben igual; el `rc` es lo único que las
separa, y ahora la sonda las clasifica aparte con el campo
`alcanza_la_rama_del_ppp`.

**Lo que esto NO demuestra:** que la rama sea inalcanzable. Demuestra que **no
la alcanza ninguno de los 22 formatos probados que esta build de ImageMagick
sabe escribir**, que es una afirmación más pequeña y con su `n` publicado.
**PENDIENTE:** alcanzarla exigiría un fichero que haga que `identify` devuelva
`rc=0` con un `%x` no numérico, o cambiar el `-format`, que es tocar `filex/`.

### 4.2 La rama de `sondear_subproceso` que queda: `if len(lin) >= 5` — PENDIENTE

Un PDF en el que Ghostscript devuelva el número de páginas **y menos de cinco
líneas**, es decir con `pdfpagecount` bien y `MediaBox` mal o ausente. No se ha
construido: fabricar ese PDF exige un `MediaBox` que `runpdfbegin` acepte y
`{=} forall` no imprima, y no encontré la forma sin ensayo y error largo. El
caso de PDF roto que sí está cubierto entra por el `except`, no por aquí.

### 4.3 Lo que este carril NO midió, a propósito

- **El coste de `sondear_subproceso` frente a la sonda en proceso.** Está
  medido ya (`CLAUDE.md` §5: 0,032 % en proceso frente al 38 % de los casos en
  que verificar cuesta más que convertir) y **no se rehace en una máquina con
  seis agentes trabajando**: §3 dice que las cifras absolutas de tandas
  distintas no son comparables, y aquí ni siquiera lo serían dentro de la tanda.
  **No se publica ni un tiempo en este informe.**
- **Las reglas de fidelidad de audio y vídeo.** El CLI las expone
  (`--fidelidad`, `--solo-fidelidad`) y lo que se ejercita aquí es su
  **cableado**, con ficheros de datos y `--sin-v2`. Las reglas en sí son de otro
  carril y «cuestan lo que convertir».
- **La regla V10 (bitrate de vídeo).** Sus 52 líneas ya estaban cubiertas por
  `pruebas/test_bitrate_y_lock.py`; sus 7 ramas parciales también quedan
  cerradas en la unión.

---

## 5. Cómo están escritas las pruebas

Tres decisiones que responden a avisos explícitos del encargo:

**Antes de juzgar una magnitud, comprobar que la sonda la publica** (trampa 86).
La clase `CensoDeClaves` corre primero y fija por escrito el resultado, que
reproduce la trampa y **la amplía**:

> Ni `sondear_en_proceso` ni `sondear_subproceso` publican el `bitrate_bps` de
> una pista de **vídeo** — reproducido, 2 de 2. Y dentro de un contenedor, el
> `bitrate_bps` de la pista de **audio** lo publica **sólo el subproceso**
> (`ffprobe` da 69 187 en `tipico.mp4`; la sonda en proceso, nada).

Esa segunda mitad es la que explica por qué la rama de «bitrate pedido» del
punto 4 estaba sin ejecutar: **es inalcanzable con el motor por defecto salvo
sobre un fichero de audio suelto.** Las dos piezas del encargo —`punto4_pedido`
y `sondear_subproceso`— se tocan justo ahí, y
`test_con_sonda_REAL_por_subproceso_la_rama_se_alcanza` lo recorre con una sonda
de verdad, no con un dict mutado.

**Las sondas sintéticas salen de un sondeo real, copiado y mutado.** Mutar el
dict de salida *es* lo que hace una conversión mala: entregar un fichero cuyas
propiedades no son las pedidas. Lo que no se hace es inventarse la forma del
dict.

**Cada prueba de `punto4_pedido` afirma sobre el `esperado`/`obtenido` concreto**
que sólo esa rama produce, y el helper `unico()` exige que la rama buscada haya
emitido **exactamente un** hallazgo con esa regla y esa severidad. Un
`assertTrue(hallazgos)` no distingue la rama que se dice cubrir de otra que
disparó de paso. Y `CuartoPuntoEnProduccion` recorre además la puerta real,
`verificar()`, hasta el veredicto y la cobertura.

**Quince de las 91 pruebas son controles negativos**: el mismo fallo que deja de
serlo cuando el pedido lo explica (redimensionado pedido, canales pedidos, BOM
pedido, profundidad pedida), la misma bajada de bits que cambia de severidad
según el destino, el alfa **trivial** que no es hallazgo (trampa 1), la cabecera
reordenada que no es cabecera perdida, la caja de página correcta. Sin ellos,
una regla que dispare siempre pasaría por una regla que compara.

---

## 6. Higiene

- **`filex/` no se ha tocado**: `git status -- filex/` limpio antes, durante y
  después de las 49 mutaciones, comprobado por `sha256` en cada celda.
- **Corpus**: el worktree traía los 39 ficheros como **punteros de LFS** de
  130 B (trampa 34) y se materializaron con `git lfs checkout` **antes** de
  medir nada. Los guardas de las pruebas comprueban el **tamaño**, no la
  existencia, porque `os.path.exists` devuelve `True` para un puntero
  (trampa 107).
- **Directorio desechable por prueba** (R18/trampa 21): `tempfile.mkdtemp` +
  `addCleanup`, y las que invocan un motor listan el directorio antes y después.
- **Topes dentro de la orden** (trampa 52): los dos `ffmpeg` que este fichero
  lanza llevan `-t 1` **en el `argv`**, no sólo el `timeout` del cliente.
- **`stdin=DEVNULL`** en todas las invocaciones.
- **No se usó la GPU ni se tomó su lock.** No se ejecutó la suite completa: seis
  agentes a la vez fabrican la carga que pone roja `test_cancelacion_procesos`
  sin que nadie toque el código (trampas 101 y 123).
- El interruptor `v2()` es **de módulo**, así que `CliFidelidad` lo restaura en
  `addCleanup`: una prueba que deja apagado un interruptor global contamina a la
  siguiente.
