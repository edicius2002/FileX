# N35 — las raíces mixtas denegaban de más

**worker5, ronda 16, 04/09/2026.** Rama `nucleo/raices-mixtas`.
Salidas y arneses en [`bench/salidas-raices-mixtas/`](salidas-raices-mixtas/).

**Decisión: se PODA.** Las raíces que no confinan se descartan una a una y el
conjunto sobrevive; el `ValueError` queda para lo que R6 siempre quiso decir —
*no queda ninguna raíz*—. Elegida con una tabla de cuatro candidatos sobre dos
superficies, no con una intuición.

**Y no reabre la fuga de ayer: MEDIDO, 11 filas, 0 accesos indebidos ganados.**

---

## 0. El resumen, para quien no lea el resto

| | MEDIDO / PENDIENTE |
|---|---|
| Una raíz de unidad **no es ancha: es INERTE** — deniega los 4 objetivos, incluido uno literalmente debajo de ella | **MEDIDO** — refuta mi hipótesis de partida |
| La tabla de **lectura no decide**: B, C y E aciertan las 8 filas los tres | **MEDIDO** |
| Lo que decide es el par `(sin_acceso, confinamiento)` que llega al consumidor | **MEDIDO**, 32 celdas en 2 superficies |
| **Podar** acierta las 32; **rechazar** (hoy) deniega de más en 4; **podar sin guarda** y **aceptar** mienten en 2 | **MEDIDO** |
| El camino de **denegación no se mueve** (trampa 28) | **MEDIDO**, 3 tandas, el signo se invierte entre ellas |
| Construir con raíces mixtas cuesta **×4,9–5,9** (+13,1 a +15,9 µs), una vez | **MEDIDO**, 3 tandas |
| `_uri_a_ruta` rompe los roots UNC en forma canónica RFC 8089 | **MEDIDO** — hallazgo colateral, **PENDIENTE** |

---

## 1. El sujeto, y por qué esta fila es peligrosa

`bench/roots-concurrencia.md` §4.3 dejó la celda `N8` escrita y sin decidir:
`Confinamiento._preparar` lanzaba `ValueError` **en cuanto una** raíz no
confinaba, así que un cliente que declarase `["C:\", <un directorio legítimo>]`
perdía **también** el legítimo.

Lo que la hace peligrosa está escrito en el encargo y conviene repetirlo: **N35
es el reverso exacto de la fuga que cerró N7 ayer**. Aquélla abría de más —un
`except ValueError` convertía «ninguna raíz confina» en «sin confinamiento», y
`nucleo.py::_resolver` con `confinamiento is None` hace literalmente
`return os.path.abspath(entrada)`—; ésta cierra de más. **Y el mismo `except`
de `filex/mcp.py` tapaba las dos.**

> Arreglar «deniega de más» sin reabrir «abre de más» es todo el encargo.

---

## 2. Antes de decidir: qué es «una raíz que no confina» — MEDIDO

Sondeado en ejecución, no deducido
([`vocabulario.json`](salidas-raices-mixtas/vocabulario.json)). El predicado
real es `os.path.dirname(_norm(abspath(r))) == _norm(abspath(r))`, y la clase
que marca es más ancha de lo que su mensaje dice:

| declarada | no confina | constructor |
|---|---|---|
| `C:\`, `C:/`, `c:\`, `D:\`, `C:` (sin barra), `\\?\C:\` | **sí** | `ValueError` |
| **`\\servidor\recurso`** (raíz de recurso UNC) | **sí** | `ValueError` |
| `\\servidor\recurso\sub` | no | ok |
| un directorio normal, con barra final, con `..`, relativo | no | ok |

**La raíz de un recurso UNC también cuenta, y eso no estaba escrito en ninguna
parte.** El mensaje dice *«no puede ser la raíz de una unidad»* y el predicado
marca dos cosas.

*(Un tercer dato del mismo sitio, fuera del encargo: la raíz `""` **construye**
—`abspath("")` es el `cwd`—, así que declarar la cadena vacía confina en el
directorio de trabajo del proceso, en silencio. **PENDIENTE**.)*

---

## 3. La refutación: la raíz de unidad no es ANCHA, es INERTE — MEDIDO

Yo entré a este encargo con una hipótesis, y era falsa. Esperaba que el
candidato «aceptar `C:\` como raíz» fuera la fuga: si se admite, pensé, se lee
la unidad entera. **La primera tabla devolvió lo contrario** y hubo que
sondear el mecanismo antes de escribir una línea
([`mecanismo.json`](salidas-raices-mixtas/mecanismo.json)):

```
_norm('C:\')                                  c:\
raiz_unidad + os.sep                          c:\\        <- barra DOBLE
candidato ('c:\windows\win.ini') == raiz      False
candidato.startswith(raiz_unidad + os.sep)    False
_dentro(win.ini, [C:\])                       False
_dentro(C:\Users\publico.txt, [C:\Users])     True        <- control positivo
```

`_dentro` compara con `r + os.sep`, y la raíz de una unidad **ya termina en el
separador**, así que la concatenación da `c:\\` y no la casa ningún candidato
normalizado. Con `C:\` de única raíz se deniegan **los cuatro objetivos**,
incluido `C:\Windows\win.ini`, que está literalmente debajo.

**R3 dice exactamente lo que pasa —*«no confina nada»*— y yo lo estaba leyendo
como «confina demasiado».** La consecuencia es la que sostiene toda la
decisión: **quitar una raíz inerte no puede quitar ningún acceso, porque no
concedía ninguno.**

Y reencuadra la fuga de ayer: **N7 no la causaba la anchura de `C:\`**, la
causaba el `confinamiento = None`. El riesgo a evitar no es «dejar entrar una
raíz ancha»: es **producir el par `confinamiento is None` + `sin_acceso =
False`**.

---

## 4. La tabla de candidatos

Cuatro políticas, las cuatro medidas **en la misma tanda** (§3 de `CLAUDE.md`):

| | qué hace |
|---|---|
| **A — rechazar** | lo de hoy: una raíz que no confina invalida el conjunto |
| **B — podar** | descartar las que no confinan; la guarda R6 sigue en pie |
| **C — podar sin guarda** | igual que B pero sin R6: nunca lanza |
| **E — aceptar** | relajar R3 y admitir la raíz de unidad |

> **Trampa 116.** El candidato A no es un doble: es la reimplementación literal
> del `_preparar` de hoy, **el sujeto con el defecto conservado a propósito**.
> Sin él, tras el arreglo la tabla no tendría con qué compararse y las filas de
> «antes» habría que ir a buscarlas a otra tanda, donde ya no serían
> comparables.

### 4.1 La lectura NO decide — MEDIDO

Ocho conjuntos de raíces × cuatro objetivos reales del disco
([`candidatos.json`](salidas-raices-mixtas/candidatos.json)). `L` = lee,
`.` = deniega; los objetivos son O1 la raíz legítima, O2 un hermano no
declarado, O3 otra unidad, O4 bajo `C:\` fuera de la legítima.

| fila | A rechazar | B podar | C sin guarda | E aceptar |
|---|---|---|---|---|
| 1 sólo legítima *(control)* | `L...` OK | `L...` OK | `L...` OK | `L...` OK |
| 2 sólo raíz de unidad *(N7)* | lanza OK | lanza OK | `....` OK | `....` OK |
| **3 MIXTA, mala primero** *(N35)* | **lanza MAL** | `L...` OK | `L...` OK | `L...` OK |
| **4 MIXTA, buena primero** | **lanza MAL** | `L...` OK | `L...` OK | `L...` OK |
| 5 dos malas | lanza OK | lanza OK | `....` OK | `....` OK |
| 6 dos buenas | `L...` OK | `L...` OK | `L...` OK | `L...` OK |
| **7 MIXTA con UNC** | **lanza MAL** | `L...` OK | `L...` OK | `L...` OK |
| 8 vacía | lanza OK | lanza OK | `....` OK | lanza OK |

**A falla en las 3 filas mixtas. B, C y E aciertan las 8 los tres.** Eso es una
meseta (trampa 51), y el borde hay que buscarlo en otro eje.

> **Un defecto de mi propio arnés, corregido antes de publicar.** La primera
> versión usaba un esperado **fijo** con `O1 = True` en las ocho filas, y en
> las tres que no declaran la raíz legítima (2, 5, 8) eso es falso: allí lo
> correcto es denegar los cuatro. La columna OK/MAL salía engañosa en 3 de 8
> filas y marcaba MAL a candidatos que acertaban. **Un esperado que no depende
> de la entrada no es un esperado.**

### 4.2 Lo que decide: el par que llega al consumidor — MEDIDO

Dos superficies, porque la trampa 26 mide lo que cuesta mirar una sola
([`superficies.json`](salidas-raices-mixtas/superficies.json)). `sa` =
`sin_acceso`, `cN` = `confinamiento is None`.

**Superficie NÚCLEO** (`FileX._resolver`, la vía de CLI, watcher y API):

| fila | A | B | C | E |
|---|---|---|---|---|
| 1 control | ok | ok | ok | ok |
| 2 sólo raíz de unidad | ok | ok | ok | ok |
| **3 MIXTA** | **DENIEGA_DE_MÁS** | ok | ok | ok |
| **7 MIXTA con UNC** | **DENIEGA_DE_MÁS** | ok | ok | ok |

**Superficie MCP** (`Raices.asegurar`):

| fila | A | B | C | E |
|---|---|---|---|---|
| 1 control | ok `sa=F cN=F` | ok `sa=F cN=F` | ok `sa=F cN=F` | ok `sa=F cN=F` |
| 2 sólo raíz de unidad | ok `sa=T cN=T` | ok `sa=T cN=T` | **MIENTE** `sa=F cN=F` | **MIENTE** `sa=F cN=F` |
| **3 MIXTA** | **DENIEGA_DE_MÁS** `sa=T` | ok `sa=F cN=F` | ok | ok |
| **7 MIXTA con UNC** | **DENIEGA_DE_MÁS** `sa=T` | ok `sa=F cN=F` | ok | ok |

**Saldo sobre 32 celdas: B acierta las 8 de 8 en las dos superficies.** A
deniega de más en 4; C y E aciertan el acceso pero en la fila 2 declaran
`sin_acceso = False` teniendo **cero** acceso real — la trampa 44: un campo
honesto («el confinamiento existe») al lado de una promesa falsa («tienes
acceso»). No es fuga, pero es un consumidor al que se le miente.

> **Segundo defecto de arnés, y éste sí llegó a producir una celda falsa.** La
> fila 7 de MCP daba `ok` para el candidato A, lo que le habría hecho parecer
> mejor de lo que es. **No estaba midiendo una UNC**: mi doble de sesión
> construía la URI como `"file:///" + ruta`, que sobre `\\servidor\recurso` da
> **cinco barras** y vuelve deformada —ya no es raíz de recurso, así que
> confina— ([`unc.json`](salidas-raices-mixtas/unc.json)). Es la trampa 38/91:
> el arnés mataba a su sujeto y el resultado parecía el bueno. Corregido, A da
> `DENIEGA_DE_MÁS` en las dos superficies, que es lo coherente.

### 4.3 El eje ESCRITURA, y la forma exacta del arreglo — MEDIDO

La guarda R6 del `__init__` mira **sólo la lectura**. Al podar aparece un
camino nuevo hasta `escritura == []`
([`escritura.json`](salidas-raices-mixtas/escritura.json)):

| fila | A rechazar | **B1** podar y callar | **B2** podar y avisar |
|---|---|---|---|
| 1 ambas buenas | escr=1, suya ✓ | escr=1, suya ✓ | escr=1, suya ✓ |
| 3 escritura declarada `[]` | escr=0, deniega | escr=0, deniega | escr=0, deniega |
| **4 escritura sólo raíz de unidad** | **lanza** | **escr=0, deniega en SILENCIO** | **lanza** |
| 5 escritura MIXTA | lanza | escr=1, suya ✓ | escr=1, suya ✓ |
| 6 lectura mixta, escritura buena | lanza | escr=1, suya ✓ | escr=1, suya ✓ |

**El control que evita arreglar un problema inexistente** (trampa 58): hoy, sin
tocar nada, `Confinamiento([legit], [])` **ya construye** con `escritura=[]` y
deniega toda escritura. **El estado no es nuevo**; lo que B1 añadiría es una
vía *silenciosa* de llegar a él donde antes había un error.

Las dos deniegan la escritura, así que B2 **no atrapa ni un acceso más** — y
por eso no se elige «por seguridad», que sería la trampa 51 al revés. Se elige
porque **B1 relaja la fila 4 sin ganar nada** y B2 la conserva idéntica a hoy.
La condición separa «no declaré escritura» (`[]` o `None`: legítimo, es
solo-lectura o heredar) de «declaré escritura y ninguna confina» — la
**trampa 43** sobre otro recurso.

**Decisión: B2.**

---

## 5. La demostración de que no se reabre la fuga de ayer — MEDIDO

Es la parte que importa, y no se argumenta: se mide. La misma sonda
([`sonda_regresion.py`](salidas-raices-mixtas/sonda_regresion.py)) corrida
sobre **el código real** de antes y de después, con **la misma base de rutas**
para que las celdas sean comparables
([`comparacion.json`](salidas-raices-mixtas/comparacion.json)):

| fila | antes | después | clase |
|---|---|---|---|
| 1 sólo legítima *(control)* | ok | ok | SIN_CAMBIO |
| **2 sólo raíz de unidad — N7** | **ValueError** | **ValueError** | **SIN_CAMBIO** |
| 3 MIXTA, mala primero | ValueError | ok | RECUPERA_ACCESO |
| 4 MIXTA, buena primero | ValueError | ok | RECUPERA_ACCESO |
| 5 dos malas | ValueError | ValueError | SIN_CAMBIO |
| 6 dos buenas | ok | ok | SIN_CAMBIO |
| 7 MIXTA con UNC | ValueError | ok | RECUPERA_ACCESO |
| 8 vacía | ValueError | ValueError | SIN_CAMBIO |
| 9 escritura sólo raíz de unidad | ValueError | ValueError | SIN_CAMBIO |
| 10 escritura MIXTA | ValueError | ok | RECUPERA_ACCESO |
| 11 escritura declarada `[]` | ok | ok | SIN_CAMBIO |

**7 SIN_CAMBIO · 4 RECUPERA_ACCESO · 0 GANA_ACCESO_INDEBIDO · 0 PIERDE_ACCESO.**

Las tres cosas que había que demostrar, y dónde están:

1. **N35 cerrado** — las 4 filas mixtas recuperan su raíz legítima.
2. **N7 no reabierto** — la fila 2 sale **SIN_CAMBIO**: sigue lanzando, MCP
   sigue poniendo `sin_acceso = True` y `confinamiento = None`.
3. **Sin fuga** — el clasificador cuenta como indebido cualquier objetivo
   ganado que no sea la propia raíz declarada (O1). Salen **cero**.

Y la propiedad estructural que lo respalda, no sólo las celdas: **podar sólo
QUITA**. El conjunto efectivo es un subconjunto de lo declarado; no hay forma
de que la poda añada una raíz. Hay una prueba que lo afirma.

---

## 6. El coste, por superficie — MEDIDO

La trampa 28 obliga: *denegar por lista blanca cuesta 9,4 µs y «existe pero no»
193,3 µs —×20,6— e igualar por arriba convierte el rechazo en un amplificador
de DoS*. **Predicción registrada antes de medir:** el camino de denegación no
se mueve, porque N35 sólo toca `_preparar` y el `__init__`, que corren una vez
al construir, y no toca `resolver()` ni una línea.

Las **dos versiones se cargan en el mismo proceso y se miden intercaladas** —la
vieja extraída del blob de git del commit anterior, no reimplementada—, porque
comparar dos corridas sería comparar dos tandas (§3 y trampa 59).
Tres tandas, n=9 x 2000 repeticiones
([`coste_tanda1.json`](salidas-raices-mixtas/coste_tanda1.json),
[`coste_tanda2.json`](salidas-raices-mixtas/coste_tanda2.json),
[`coste_tanda3.json`](salidas-raices-mixtas/coste_tanda3.json)):

| caso | tanda 1 Δ | tanda 2 Δ | tanda 3 Δ | ¿supera el ruido? | veredicto |
|---|---|---|---|---|---|
| denegar, corta en R1 | +0,113 µs | **−0,149 µs** | +0,247 µs | no, en ninguna | **no se mueve** |
| denegar, «existe pero no» | +0,149 µs | +0,047 µs | **−1,031 µs** | no, en ninguna | **no se mueve** |
| permitir ruta válida | +18,96 µs | +5,23 µs | +11,55 µs | no *(ruido 225 / 97 / 75 µs)* | **no es una medida** |
| construir raíz simple | +0,118 µs | **−0,268 µs** | +0,465 µs | no, en ninguna | **no se mueve** |
| **construir MIXTA** | **+14,90 (×5,94)** | **+15,91 (×5,30)** | **+13,15 (×4,90)** | sí | **es el coste real** |

**En los cuatro primeros el signo se invierte entre tandas** —los dos caminos de
denegación cambian de signo, cada uno en una tanda distinta—, que es la firma
del ruido puro y no de un efecto (trampa 36). **En el quinto el signo se
conserva en las tres y la magnitud se mueve poco**, así que ése sí es el coste.

**Cómo hay que leer ese ×5,9, porque citado a secas engaña** (trampa 88): no es
una regresión, es que **la versión vieja abortaba en la primera raíz sin
terminar su trabajo**. El ratio compara «hacer» contra «rendirse». Son **+13 a +16 µs
una vez por construcción**, frente a los 1 169,7 µs del cerrojo de destino y
los ~484 µs del lock que el propio proyecto ya paga por conversión.

**Y lo que la trampa 28 pedía saber está limpio: el camino de denegación no
paga nada, así que el rechazo no se convierte en amplificador de DoS.**

---

## 7. Las pruebas, y la comprobación de que no son vacuas — MEDIDO

**11 pruebas en dos superficies**: 8 en `pruebas/test_hito1.py::RaicesMixtasN35`
(sobre `Confinamiento` y `FileX._resolver`) y 3 en
`pruebas/test_hito4.py::RaicesMixtasPorMCP` (sobre `Raices.asegurar`).

Un `assert` que nunca discrimina es indistinguible de uno que se cumple
(trampa 109), así que se midieron **contra el código de antes de N35**
([`pruebas_ANTES.txt`](salidas-raices-mixtas/pruebas_ANTES.txt)):

**10 de las 11 fallan** (3 failures, 7 errors). **Y las 3 que pasan en las dos
versiones son exactamente las que afirman que la fuga no se reabre:**

- `test_podar_NO_reabre_N7_sin_ninguna_raiz_util_sigue_sin_arrancar`
- `test_si_NINGUN_root_confina_se_sigue_diciendo_SIN_ACCESO`
- `test_no_declarar_escritura_sigue_siendo_legitimo`

Que una prueba de no-regresión pase antes y después **es lo que se le pide**:
afirma lo que no debe cambiar.

Además, **las 8 pruebas de N34 siguen siendo discriminantes con mi cambio
puesto**: revertido `filex/mcp.py` a `82cf1f3` (antes de ayer), **4 de 8 caen**,
incluida la de N7. Mi arreglo no las ha vuelto vacuas, que es lo que la
trampa 65 manda comprobar.

> **Dos falsos verdes propios, cazados a tiempo.**
>
> **(a)** La primera pasada de esta comprobación dio **«11 OK» sobre el código
> supuestamente revertido**, y por un momento pareció que mis pruebas no
> probaban nada. **La causa era el arnés: `git stash push` sobre un fichero ya
> commiteado NO HACE NADA, y no lo dice** — devuelve 0 y deja una lista de
> stash vacía. La condición que decía reproducir no se daba (trampa 38/91).
> Ahora se comprueba con `inspect.getsource` **antes** de creerse el resultado.
>
> **(b)** `test_declarar_escritura_y_que_ninguna_confine_es_un_ERROR` pasaba en
> las dos versiones: antes lanzaba desde `_preparar`, ahora desde la guarda
> nueva — **mismo veredicto, distinto mecanismo**, así que un `assertRaises` a
> secas no demostraba nada. Comprobando que el mensaje habla de la
> **escritura**, discrimina: de 9 fallos a 10.

---

## 8. La suite, con sus cuatro declaraciones (trampas 94 y 101)

```
500 passed · 3 skipped · 0 failed · 179 subtests · 252,62 s
```

1. **Intérprete** — `.venv-mcp-filex\Scripts\python.exe`, **win32, 3.11.9**.
   Los tests `win32` (`os.replace`, mutex `Global\`, DACL, nombres 8.3) sí
   corren.
2. **Entorno** — **Docker levantado** (29.4.3) con `filex-c13`,
   `gotenberg/gotenberg:8` y `python:3.12-slim-bookworm` presentes: el hito 5 y
   la cancelación real de contenedor **se ejecutan**. Corpus de LFS
   materializado (`corpus/imagen/tipico.png` = **42 855 B**, no un puntero).
3. **Qué quedó fuera** — los **3 saltados**, los mismos tres de la referencia y
   los tres declarados: `test_hito4.py:221` (ningún par real rasteriza hacia un
   destino con texto en esta máquina), `test_hito6.py:186` (falta el ráster de
   `preparar_h6.py`) y `test_hito6.py:697` (pide `FILEX_PRUEBAS_SIDECAR=1` y la
   tarjeta).
4. **Estado de la máquina** — **NO estaba despejada, y se comprobó en vez de
   suponerlo**: CPU al **44–47 %** con **9 procesos `python`** durante toda la
   sesión, y el testigo de nivel de la sonda de coste dio **45–48 ms** de
   mediana para lanzar un proceso. El lock de GPU estaba **libre** y no se usó
   la tarjeta. La suite tardó **252,62 s** frente a los **221,52 s** de la
   referencia (**+14 %**), consistente con esa carga.

**Contra la referencia de 489 passed · 3 skipped · 175 subtests: +11 pruebas y
+4 subtests, que son exactamente las mías** (11 tests, de los cuales 2 llevan 2
subtests cada uno). Cuadra sin residuo.

Y la huella no se movió: `test_sondeo` da **48/48**, así que ni el cambio de
`confinamiento.py` ni el docstring de `mcp.py` caducan ninguna de las aristas
selladas.

---

## 9. Lo que refuté

1. **Mi hipótesis de partida, sobre el sujeto** (§3). Entré creyendo que
   aceptar `C:\` como raíz sería la fuga —«se leería la unidad entera»— y la
   primera tabla dijo lo contrario. La raíz de unidad es **inerte**: deniega
   los cuatro objetivos, incluido uno literalmente debajo. Y eso reencuadra la
   fuga de ayer: **N7 no la producía la anchura de `C:\`, la producía el
   `confinamiento = None`.**
2. **Mi propio arnés, dos veces** (§4.1, §4.2): un esperado fijo que marcaba
   MAL a candidatos que acertaban, y un doble que deformaba las UNC y le
   regalaba al candidato A una celda `ok` que no le correspondía.
3. **Mi propia comprobación de discriminación** (§7): el `git stash` que no
   stasheaba, y una prueba que pasaba en las dos versiones por mecanismos
   distintos.

---

## 10. Lo que queda PENDIENTE

1. **`_uri_a_ruta` rompe los roots UNC en forma canónica — MEDIDO, sin
   arreglar.** `_uri_a_ruta("file://servidor/recurso")` —la forma que manda
   RFC 8089 para una UNC— devuelve **`\recurso`**: descarta la *authority*. Un
   cliente MCP que declare un recurso de red como root acaba confinado en un
   directorio **local** que nadie declaró (`<unidad del cwd>:\recurso`), y que
   además **sí** confina, así que no salta ninguna guarda. Con cuatro barras
   (`file:////servidor/recurso`) sale bien. **No es N35 y no lo he tocado**;
   necesita decidir qué formas de URI se aceptan, que es una fila propia.
2. **La raíz `""` construye** y confina en el `cwd` del proceso, en silencio
   (§2). Mismo caso: es una decisión sobre el vocabulario de entrada, no sobre
   la política de N35.
3. **La poda es silenciosa.** Hoy nadie se entera de que una raíz declarada se
   descartó. Para MCP eso es correcto —el cliente sigue teniendo acceso y no
   hay nada que arreglar—, pero un `--raiz C:\ --raiz D:\datos` en la CLI
   también poda sin decir nada. **No lo he añadido porque no lo he medido**: no
   sé si un aviso ayuda o si sólo añade ruido, y la trampa 51 dice que un
   remedio que no atrapa nada no es más seguro.
4. **Todo esto es de Windows.** En POSIX la única raíz inerte es `/`, y el caso
   UNC no existe. Las pruebas están escritas para las dos plataformas (`/` como
   raíz inerte), pero **medido, sólo está Windows**.

---

## 11. Para el maestro — texto propuesto

**No he tocado `ESTADO-Y-REPARTO.md`, `CLAUDE.md` ni `PLAN-ORQUESTADOR.md`.**

### ⚠ `ci/integridad.py` queda en 8 de 9, y el noveno es esa prohibición

```
MAL  informes-registrados   100 informes, todos citados
        raices-mixtas.md
```

`informes_registrados()` exige que **todo `bench/*.md` esté citado en
`ESTADO-Y-REPARTO.md`**, así que el informe nuevo no puede pasar la
comprobación sin editar el fichero que el encargo me prohíbe tocar. **Las otras
ocho pasan**, incluida `manifiestos` —que sólo se puso verde al commitear,
porque sale de `git ls-files` y no de `glob`: la trampa 104 funcionando—.

Con cualquiera de los tres textos de abajo pegado, queda en 9 de 9.

### Sobre la trampa 115: **no hace falta archivar esta rama**

Este informe y su `MANIFIESTO.md` citan **dos** commits, y los dos sobreviven
al `--squash`:

- **`a4dc3f3`** — la punta de `main` antes de esta rama, usada como «el código
  de antes» en la sonda de coste y en las órdenes de reproducción.
- **`82cf1f3`** — el commit de antes de ayer, para comprobar que las pruebas de
  N34 siguen siendo discriminantes.

**La primera versión citaba `aab61bb`, que está sólo en mi rama y habría muerto
en la fusión.** Se sustituyó tras comprobar que el blob de
`filex/confinamiento.py` es **el mismo** en los dos
(`db24918f8353aba6ec796973d838d19dfc470d1c`), así que la cita nueva señala
exactamente el mismo código. Es la salida que la trampa 115 recomienda —*citar
algo que sobreviva*— y aquí se podía sin perder nada, porque lo que la cita
prueba es **qué código se midió**, no un orden temporal.

### (a) Fila de la tabla de §1 — la que arregla la CI

> | 04/09 | **`bench/raices-mixtas.md`** (worker5, `nucleo/raices-mixtas`) | **`N35` cerrada PODANDO, y el reverso de la fuga de ayer queda cerrado sin reabrirla.** Una raíz que no confina se descarta ella, no invalida el conjunto: un cliente que declare `["C:\", <legítimo>]` conserva el legítimo. Elegido con **4 candidatos × 8 filas × 2 superficies** (núcleo y MCP), no con una intuición. **La demostración de que no se reabre N7 es la misma sonda sobre el código de antes y el de después, con la misma base de rutas: 11 filas, 7 SIN_CAMBIO y 4 RECUPERA_ACCESO, con CERO accesos indebidos ganados y la celda de N7 idéntica.** El camino de denegación **no paga nada** (trampa 28: el delta queda bajo el ruido y **el signo se invierte entre las dos tandas**); lo único que se mueve es construir con raíces mixtas, ×4,9–5,9 **una vez** —y ese ratio compara «hacer el trabajo» contra «abortar en el primer elemento», no una regresión—. 11 pruebas nuevas en dos superficies, **10 de las 11 rojas contra el código anterior** y las 3 que pasan en ambos son justo las de no-regresión. **Se refuta a sí mismo tres veces**, una de ellas sobre el propio sujeto: la raíz de unidad **no es ancha, es INERTE**. Trampas **118** y **119** |

### (b) La fila `N35` del inventario, que hoy está 🔴 ABIERTO

> | **N35** | *(texto actual)* … **CERRADA el 04/09/2026 por worker5** (`bench/raices-mixtas.md`): se **poda** —las raíces que no confinan se descartan una a una y el `ValueError` queda para lo que R6 siempre quiso decir, *no queda ninguna*—, elegido con 4 candidatos sobre 2 superficies. **No reabre N7: 0 accesos indebidos ganados sobre 11 filas y la celda de N7 SIN_CAMBIO.** Coste: el camino de denegación no se mueve; construir con raíces mixtas, ×4,9–5,9 una vez. Y **refuta la lectura que todos hacíamos de R3**: una raíz de unidad no confina demasiado, **no confina NADA** —`_dentro` genera una barra doble y deniega hasta lo que está literalmente debajo—, que es lo que convierte «podar» de apuesta en teorema. PENDIENTE declarado: `_uri_a_ruta` rompe los roots UNC canónicos, la raíz `""` confina en el `cwd`, y la poda es silenciosa | 🟢 **CERRADO** · `bench/raices-mixtas.md` |

### Trampa propuesta — la 118

> 118. **Una raíz que «no confina nada» puede denegarlo TODO en vez de
> permitirlo todo, y de qué lado esté decide si el arreglo es seguro — MEDIDO
> el 04/09** (`bench/raices-mixtas.md` §3). R3 dice que *«una raíz que
> normaliza a la raíz de una unidad no confina nada»*, y entré a N35 leyendo
> eso como «confina demasiado»: esperaba que admitir `C:\` abriera la unidad
> entera. Es al revés y el mecanismo es de una línea: `_dentro` compara con
> `r + os.sep`, la raíz de unidad **ya termina en separador**, y `c:\` + `\` da
> la barra **doble** `c:\\`, que no casa ningún candidato normalizado. MEDIDO
> con control positivo y negativo: con `C:\` de única raíz se deniegan los 4
> objetivos, **incluido `C:\Windows\win.ini`, que está literalmente debajo**.
> **La consecuencia decide el encargo entero**: si la raíz fuera ancha, podarla
> sería quitar acceso y habría que pensárselo; siendo inerte, podarla **no
> puede quitar nada porque no concedía nada**, y eso convierte «podar» de una
> apuesta en un teorema. Y reencuadra la fuga de la ronda anterior: **N7 no la
> causaba la anchura de `C:\`, la causaba el `confinamiento = None`** que el
> `except` ponía —`nucleo.py::_resolver` con `None` hace
> `return os.path.abspath(entrada)`—, así que el par a vigilar no es «una raíz
> ancha» sino **`confinamiento is None` con `sin_acceso = False`**. Es la
> trampa 58 sobre una regla del propio proyecto: **el hecho estaba escrito y
> bien, y yo le puse la causa al revés** — y la única razón de que no costara
> caro es que la tabla se midió antes de escribir el arreglo, no después.

### Trampa propuesta — la 119

> 119. **`git stash push <fichero>` sobre un fichero ya commiteado NO HACE
> NADA, y el arnés que revierte para comprobar que sus pruebas discriminan sale
> VERDE — MEDIDO el 04/09** (ídem §7). Para demostrar que 11 pruebas nuevas no
> eran vacuas (trampa 109) hay que correrlas contra el código de antes, y el
> gesto natural es `git stash push filex/x.py`. **Si el arreglo ya está
> commiteado no hay nada que stashear**: el mandato devuelve 0, deja la lista
> de stash **vacía**, no imprime aviso, y las pruebas corren contra el código
> **nuevo** dando **«11 OK»** — que es exactamente la pinta de *«mis pruebas
> pasan con el arreglo y sin él»*, la conclusión más alarmante posible y
> completamente falsa. Las dos lecturas que invita son las dos malas: tirar
> unas pruebas buenas, o —peor— reescribirlas hasta que «fallen». Lo que lo
> destapó fue preguntarle al módulo qué código tenía dentro
> (`inspect.getsource(Confinamiento._preparar)`), y la forma correcta de
> revertir es `git checkout <commit> -- <fichero>`. **Es la trampa 38 sobre el
> control de versiones: registra que la condición que dices reproducir SE DIO,
> y hazlo interrogando al sujeto, no al mandato que creías que lo cambiaba.**
> Corolario que amplía la 60 y la 109: **un arnés de A/B sobre dos versiones de
> un fichero necesita un control de IDENTIDAD** —comprobar que las dos
> versiones son distintas— antes de creerse una sola celda; la sonda de coste
> de este informe lo lleva dentro y aborta si no se cumple.
