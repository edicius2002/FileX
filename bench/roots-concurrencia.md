# N34 — la caché de raíces en concurrencia: la decisión, con la tabla delante

**Ronda 15, carril CPU, worker3.** Cierra la fila **N34**, que
`bench/mcp-cabos-y-techos.md` §2.4 (worker2, ronda 14) dejó **medida y sin
decidir**.

**Decisión: SERIALIZAR** —candidato **D**: candado asíncrono sostenido a través
del `await`, y **ningún resultado nacido de un fallo se sella**—. Cuesta
**0,5 µs de mediana en el camino caliente**, que es el mismo que costaba antes
porque el camino caliente **no llega a tocar el candado nuevo**, y **no empeora
el caso que daba miedo** (un cliente que no contesta). Con eso, N herramientas
concurrentes pasan de **N idas y vuelta a 1** y el estado final de la sesión
deja de depender del orden de terminación.

**Y por el camino salieron dos fallos que no son de concurrencia y viven en la
misma función, uno de ellos una fuga total del confinamiento.** Los tres están
arreglados en `filex/mcp.py`, con tres pruebas que **fallan 3 de 3 contra el
código anterior**.

| Marca | Qué |
|---|---|
| **MEDIDO** | Todo lo de §1 a §5, con `bench/salidas-roots-concurrencia/carrera_{antes,despues}.json` |
| **PENDIENTE** | La latencia REAL de un `roots/list` por el cable (§6.1) y las raíces mixtas (§4.3) |

**Entorno de la medida:** `.venv-mcp-filex\Scripts\python.exe`, **3.11.9
win32**, `mcp` **2.0.0**, resolución de `perf_counter` **1e-07 s** (trampa 62:
se le pregunta al instrumento antes de cronometrar). Máquina **no despejada**:
hay otro worker en el mismo carril — CPU al **42 %**, **424 procesos**, **12
`python` vivos** al arrancar la suite.

---

## 0. Lo que se hereda, y lo que hacía falta añadirle

§2.4 mide que **dos herramientas que entran a la vez con la caché fría producen
2 `roots/list`, no 1**, porque el `threading.Lock` de `asegurar()` se suelta
antes del `await`. Y lo deja sin arreglar **a propósito**, con este argumento:

> *«No es un fallo de corrección —el cálculo es idempotente y las dos llamadas
> dan lo mismo— pero contradice lo que "cacheada por sesión" hace creer»*.

**La pregunta que decide la fila no es cuántas idas y vueltas hay: es si las dos
llamadas pueden dar lo mismo SIEMPRE.** Y desde el arreglo de M3 —de la misma
ronda, que dejó de sellar un fallo transitorio— **no pueden**: dos llamadas
concurrentes pueden recibir respuestas distintas del mismo cliente, y entonces
lo que queda escrito en la sesión lo decide **cuál termina la última**.

## 1. El arnés, y su control (trampa 114, escrita ayer por worker2)

`bench/salidas-roots-concurrencia/sonda_carrera.py` es una copia propia —§1 de
`CLAUDE.md`: un fichero de salida por agente— con el mismo doble de sesión y su
punto de suspensión donde un `roots/list` real tendría la ida y vuelta.

**Control del arnés, N0 — MEDIDO:**

| Doble | `roots/list` | entradas simultáneas | las dos responden |
|---|---|---|---|
| **sin ceder el bucle** *(control negativo)* | 1 | **1** | sí |
| **cediendo** | **2** | **2** | sí |

Reproduce §2.4 exactamente. Y aquí aparece el primer hallazgo, que es **del
arnés y contra mí mismo**:

> ### 1.1 El control negativo dejó de discriminar en cuanto arreglé el objeto
>
> Con el arreglo puesto, las dos celdas de N0 dan **1 y 1**: el par
> «cede / no cede» ya no demuestra que hubiera solape, porque el objeto ya no
> produce dos idas y vueltas ni aunque lo haya. El arnés seguía imprimiendo su
> veredicto y ese veredicto pasó a ser **`el_arnes_mide_concurrencia: false`**
> sobre un arnés que funcionaba perfectamente.
>
> Es la **trampa 65** —*cuando una prueba que documenta un fallo antiguo se
> pone verde sola, pregúntate qué defensa la está tapando*— aplicada al
> **control de un arnés** en vez de a una prueba. **El remedio es conservar el
> sujeto con el defecto:** la sonda trae `A_Historico`, que reimplementa el
> `asegurar` de antes de N34, y N0 corre sobre él. Con eso el control vuelve a
> discriminar **de forma permanente**, y de propina la tabla de candidatos
> tiene su fila de referencia después del arreglo:
>
> | Sujeto, doble cediendo | `roots/list` | simultáneas |
> |---|---|---|
> | `A_historico` | **2** | 2 |
> | producción (hoy) | **1** | 1 |

## 2. La tabla de candidatos — MEDIDO (trampa 51)

Cuatro candidatos, medidos **sobre el código de antes** (tanda
`carrera_antes.json`), cada uno como subclase de la clase de producción
inyectada antes de `construir()`, así que el camino ejercitado sigue siendo
`on_call_tool → gestor.asegurar` (trampa 109).

| Candidato | `roots/list` con N=1/2/4/8 | ¿el orden cambia el estado final? | ¿sella un confinamiento más ancho que la intersección? | caché caliente (mediana) | con un `roots/list` que no vuelve |
|---|---|---|---|---|---|
| **A — hoy** (aceptar la carrera) | **1 / 2 / 4 / 8** | **SÍ** | **SÍ** | 0,4 µs | 2 peticiones colgadas, 0 responden |
| **B — serializar** | 1 / 1 / 1 / 1 | no | **SÍ** | 0,6 µs | 1 colgada, 0 responden |
| **C — primer sellador gana** (sin serializar) | 1 / 2 / 4 / 8 | no | **SÍ** | 0,5 µs | 2 colgadas, 0 responden |
| **D — serializar + no sellar fallos** | **1 / 1 / 1 / 1** | **no** | **no** | **0,4 µs** | 1 colgada, 0 responden |

**Tiempo de pared con N=8**: A **64,33 ms**, B **57,03**, C **60,20**,
D **64,30**. Las cuatro están dentro del ruido de la tanda: **serializar no
cuesta tiempo de pared**, porque lo que antes eran 8 peticiones **en paralelo**
pasa a ser 1 petición que las otras 7 esperan, y las 8 pagaban ya esa latencia.
*(La celda `D` con N=1 dio 134,2 ms, el arranque de la tanda; se declara y no se
usa — trampa 36: por debajo del suelo de ruido una diferencia no es una
medida.)*

**Ganador: D.** B y C cierran cada uno la mitad del problema; sólo D cierra las
dos, y **cuesta lo mismo**.

### 2.1 Lo que un candado sostenido durante un `await` NO rompe — MEDIDO

Era el riesgo que el encargo señalaba, y se midió en vez de razonarlo. Con un
`roots/list` que **no vuelve nunca** (retardo de 30 s, tope de 1 s):

| | peticiones colgadas | herramientas que responden |
|---|---|---|
| sin candado (A) | 2 | **0** |
| con candado (D) | 1 | **0** |

**Serializar no empeora el caso del cliente mudo**: no responde nadie ni con
candado ni sin él. Lo único que cambia es que hay **una** petición colgada en
vez de N, que es estrictamente mejor. Y el camino **caliente** —el 99 % de las
llamadas, con la caché resuelta— **sale antes de tocar el candado nuevo**: la
primera guarda sigue siendo el `threading.Lock` de siempre. La medida
(0,4 frente a 0,4 µs) lo confirma, pero el argumento que la sostiene es
estructural, no del reloj.

## 3. El hallazgo que decide la fila: la carrera SÍ diverge — MEDIDO

Dos llamadas concurrentes, el mismo par de respuestas (una responde con una
raíz, la otra falla), y **sólo cambia cuál termina antes**:

| Orden de terminación | estado final `sin_acceso` | `_resuelto` | confinamiento |
|---|---|---|---|
| gana el fallo | **False** | True | la raíz |
| gana la respuesta | **True** | False | **ninguno** |

**El mismo cliente, el mismo instante, dos sesiones distintas.** Eso es lo que
convierte una ineficiencia en un fallo de seguridad de sesión: una carrera
decide si la sesión queda con acceso o sin él. Con D, las dos órdenes dan el
mismo estado final (`el_orden_cambia_el_estado_final: False`).

**Y una acotación que hay que publicar porque limita el daño**: la sonda
comprueba **sobre el AST** (trampa 42) que entre la escritura de
`fx.confinamiento` y la de `sin_acceso` **no hay ningún `await`** —el único
está en el `roots/list`, arriba—, así que **otra corrutina no puede observar el
par a medias**: nunca hay una ventana de «puerta abierta y sin confinamiento»
para las corrutinas. Lo que diverge es el estado que queda **después**, no un
estado intermedio. *(Para HILOS de fondo —`convert` corre en uno— esa
atomicidad no está demostrada: **PENDIENTE**, §6.2.)*

## 4. Dos fallos que no son de concurrencia y estaban en la misma función

### 4.1 Un fallo al preguntar sellaba un confinamiento MÁS ANCHO — MEDIDO (N3)

`_interseca(servidor, [])` devuelve **la lista del servidor entera**. Así que
con `--raiz` puesta, un `roots/list` que falla no deja «ninguna raíz»: deja
**todas**, y con `efectivas` no vacía la regla de M3
—`_resuelto = not (fallo and not efectivas)`— **sellaba `True` para toda la
sesión**.

| | tras el fallo | tras el reintento |
|---|---|---|
| **antes** | `_resuelto=True`, confinamiento = **raíz del servidor** | 1 `roots/list`: **no vuelve a preguntar nunca** |
| **después** | `_resuelto=False`, confinamiento = raíz del servidor | 2 `roots/list`: **se estrecha a la raíz del cliente** |

R13 dice que los roots del cliente se **intersecan**, no se reemplazan; el
sellado fijaba lo contrario. **Es la trampa 43 un nivel más adentro de donde M3
la aplicó**: un fallo al preguntar no distingue *«el cliente no tiene roots»* de
*«el cliente tiene roots y no contestó»*, y sólo la primera justifica quedarse
con los del servidor. La condición correcta es **`_resuelto = not fallo`**.

> **Esto puso ROJA una prueba de ayer, y la prueba estaba equivocada.**
> `test_un_fallo_CON_raiz_de_servidor_si_se_sella` afirmaba *«si queda alguna
> raíz, la respuesta es buena aunque el cliente no contestara, y volver a
> preguntar no cambiaría nada»*. **Volver a preguntar sí cambia la respuesta**,
> y la prueba reescrita lo mide: el confinamiento pasa de la raíz del servidor
> a la del cliente, que es más estrecha. No se relajó la prueba: se refutó su
> premisa con la celda N3 delante, y la prueba nueva afirma la refutación.

### 4.2 Una raíz que no confina dejaba a FileX SIN CONFINAMIENTO — MEDIDO (N7)

El peor de los tres, y **no necesita ni concurrencia ni un fallo**.

`Confinamiento` lanza `ValueError` cuando ninguna raíz confina —**R3**: *«una
raíz que normaliza a la raíz de una unidad no confina nada»*—. `asegurar` lo
capturaba y ponía `confinamiento = None`, **dejando `sin_acceso = False`**
porque `efectivas` no estaba vacía. Y en el núcleo, `_resolver()` con
`confinamiento is None` **devuelve la ruta tal cual**.

| Raíz que declara el cliente | `sin_acceso` | confinamiento | ¿lee otro directorio? | ¿lee **otra unidad**? |
|---|---|---|---|---|
| un directorio normal *(control)* | False | el directorio | **no** | **no** |
| **`C:\` (raíz de unidad), ANTES** | **False** | **ninguno** | **SÍ** | **SÍ (D:)** |
| `C:\` (raíz de unidad), DESPUÉS | **True** | ninguno | no | no |

Con el cliente declarando `C:\`, FileX leía un fichero de un directorio
temporal distinto **y el corpus de la unidad D:**, mientras el control con una
raíz normal denegaba los dos. **`Confinamiento.__init__` ya dice lo que había
que hacer** —*«R6: denegar por defecto. Sin ninguna raíz accesible, no se
arranca»*—: `filex/nucleo.py` deja subir el `ValueError` y **era esta
superficie la que se lo tragaba**. Comprobado, no supuesto: el núcleo construye
`Confinamiento(...)` sin `except`, así que el agujero es **exclusivo de MCP**.

Arreglo: `sin_acceso = (not efectivas) or sin_confinar`.

### 4.3 El precio del arreglo de 4.2, medido y no escondido — PENDIENTE

`Confinamiento._preparar` lanza en cuanto **una** raíz no confina, así que un
cliente que declare `["C:\", <un directorio legítimo>]` pierde **también** el
directorio legítimo:

| | `sin_acceso` | confinamiento | ¿lee su propia raíz legítima? |
|---|---|---|---|
| antes | False | **ninguno** | sí — **pero sin confinar nada, leía cualquier cosa** |
| después | **True** | ninguno | **no** |

Las dos son incorrectas y **la de después falla hacia el lado seguro**. Lo
correcto sería **descartar las raíces que no confinan y quedarse con las que
sí**, y eso vive en `filex/confinamiento.py`, que **no es mío en esta ronda**:
queda **PENDIENTE**, con la celda `N8` ya escrita para verificarlo.

## 5. La suite, con sus cuatro declaraciones (trampas 94 y 101)

**492 pruebas · 0 fallos · 3 saltadas · 236,87 s.**

1. **Intérprete:** `.venv-mcp-filex\Scripts\python.exe`, **3.11.9, win32**.
2. **Entorno:** Docker **29.4.3** levantado, **12 imágenes**. `mcp` 2.0.0.
3. **Qué quedó fuera:** las 3 saltadas están declaradas y son honestas —
   *«ningún par real rasteriza hacia un destino con texto en esta máquina»*,
   *«necesita la tarjeta: `FILEX_PRUEBAS_SIDECAR=1`»* y *«falta el ráster
   (`bench/salidas-hito6/preparar_h6.py`)»*.
4. **Estado de la máquina:** **NO despejada**. Otro worker en el mismo carril:
   **CPU 42 %**, **424 procesos**, **12 `python` vivos**. La tanda tardó
   **236,9 s** frente a los 165,3 s que `CLAUDE.md` documenta con la máquina
   tranquila: **×1,43**, del mismo orden que el ×3,4 de la trampa 101 y sin
   ningún fallo, pero **las cifras de tiempo de esta tanda no son comparables
   con las de otra**.

Y el control que exigen las trampas 60 y 109: **las tres pruebas nuevas fallan
3 de 3 contra el código anterior** (`git show HEAD:filex/mcp.py` restaurado,
suite del módulo ejecutada, las tres rojas con el mensaje de su aserción), y
pasan con el arreglo. Un `assert` que nunca se evalúa es indistinguible de uno
que se cumple.

## 6. Lo que queda PENDIENTE, dicho como pendiente

### 6.1 La latencia real de un `roots/list` por el cable

Todo lo de §2 usa un retardo **simulado de 50 ms** donde un `roots/list` real
tendría su ida y vuelta. Eso basta para lo que la fila decidía —el número de
peticiones, la divergencia y el orden de magnitud de la espera—, **pero la
espera que la serialización impone al segundo llamador es exactamente esa
latencia, y no la he medido contra un cliente real.** El instrumento existe
(`mcp.shared.memory.create_client_server_memory_streams` permite montar un par
`ClientSession`/`Server` de verdad en proceso) y daría una **cota inferior**;
la latencia contra Claude Code por `stdio` no la da ningún arnés de este
repositorio. **PENDIENTE, y no lo declaro cerrado con la cifra simulada.**

### 6.2 La atomicidad del par frente a HILOS, no a corrutinas

§3 demuestra sobre el AST que ninguna corrutina puede ver
`(confinamiento, sin_acceso)` a medias. **`convert` corre en un hilo de fondo**
y `nucleo._resolver()` lee `self.confinamiento` **dentro de ese hilo**, así que
un hilo sí puede observar la ventana entre las dos escrituras. Hoy eso sólo
puede **estrechar o ensanchar** el confinamiento de una conversión ya admitida
—cuyas rutas ya pasaron `validar()`—, pero **no lo he medido**. PENDIENTE.

### 6.3 La emisión real de `notifications/roots/list_changed`

Sigue sin observarse (heredado del hito 4). El contador `Raices.emisiones` y su
registro por fichero siguen puestos y en 0.

---

## 7. Propuesta de fila para `ESTADO-Y-REPARTO.md`

> **N34 — la caché de raíces en concurrencia. 🟢 CERRADO (ronda 15, worker3,
> `bench/roots-concurrencia.md`).** Se **serializa**: candado asíncrono
> sostenido a través del `await` y **ningún resultado nacido de un fallo se
> sella**. N herramientas concurrentes con la caché fría pasan de **N idas y
> vueltas a 1** (8 → 1 con N=8) y el estado final de la sesión deja de depender
> del orden de terminación —dos órdenes del mismo par daban `sin_acceso=False`
> con confinamiento y `sin_acceso=True` sin él—. Cuesta **0,4 µs** en el camino
> caliente, que **no llega a tocar el candado**, y **no empeora** el caso del
> cliente mudo (0 herramientas responden con candado y sin él; lo que cambia es
> 1 petición colgada en vez de N). **Y la fila destapó dos fallos que no son de
> concurrencia**: un `roots/list` fallido con `--raiz` puesta sellaba la lista
> blanca del servidor **entera**, más ancha que la intersección que exige R13; y
> el `except ValueError` de `asegurar` convertía «ninguna raíz confina» (R3) en
> **«sin confinamiento» con la puerta abierta** — un cliente que declarase `C:\`
> leía ficheros de otro directorio **y de otra unidad**. PENDIENTE: la latencia
> real de un `roots/list` por el cable (§6.1), la atomicidad frente a hilos de
> fondo (§6.2) y las raíces mixtas, que hoy deniegan de más (§4.3,
> `filex/confinamiento.py`).

## 8. Propuesta de trampa nueva (la 116)

> 116. **Un control negativo de arnés puede dejar de discriminar justo cuando
> el objeto se arregla, y el arnés sigue publicando su veredicto — MEDIDO el
> 04/09** (`bench/roots-concurrencia.md` §1.1). La trampa 114 prescribió, con
> razón, un control sin punto de suspensión al lado de todo arnés de
> concurrencia asíncrona: *si las dos celdas dan lo mismo, la de arriba no
> midió concurrencia*. **El par «cede / no cede» discrimina porque el SUJETO
> tiene el defecto.** Arreglada la caché de roots, las dos celdas pasan a dar
> **1 y 1**, el veredicto compuesto del arnés se volvió
> `el_arnes_mide_concurrencia: false` **sobre un arnés impecable**, y las dos
> lecturas posibles son las dos malas: creer que el arnés se rompió, o —peor—
> creer que ya no hace falta. **El control positivo de un arnés de carrera no es
> una variante del doble: es el SUJETO CON EL DEFECTO, conservado a propósito**
> (aquí, una subclase que reimplementa el `asegurar` anterior). Es la trampa 65
> —*cuando una prueba que documenta un fallo antiguo se pone verde sola,
> pregúntate qué defensa la está tapando*— trasladada del banco de pruebas al
> instrumento que lo mide. Y el corolario que lo hace barato: **conservar el
> sujeto viejo da además la fila de referencia de la tabla de candidatos
> después del arreglo**, que si no hay que ir a buscar a un JSON de otra tanda
> —y ahí ya no sería comparable (§3 de `CLAUDE.md`)—.

## 9. Salvedad sobre las citas de commit de esta rama

Este informe **no cita ningún hash de su propia rama**, a propósito
(trampa 115): las dos tandas se distinguen por el nombre del fichero
(`carrera_antes.json` / `carrera_despues.json`), no por un commit que el
`--squash` mataría. La orden que reproduce cada una está en el `MANIFIESTO.md`.
