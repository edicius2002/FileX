# La ventana entre la detección y el `move` — y el remedio que proponía el pendiente era el caro

**Agente Y · 2026-08-28 · fila N12**
Ficheros: `filex/nucleo.py`, `pruebas/test_cerrojo.py`, `bench/salidas-ventana/`.

---

## 0. Lo que hay que saber, en seis líneas

1. **La ventana existe y NO es de microsegundos: son 681,4 µs de mediana** (n=15,
   testigos limpios; recorrido 451,6–1 148,2 µs entre celdas). Es **×34 la propia
   detección**, que cuesta 20,2 µs sobre un destino ausente.
2. **Reproducida entre procesos de verdad: 12 de 12 celdas** con
   `la_ventana_se_abrio = true` acaban con FileX devolviendo `ok` sobre el
   fichero de otro. Y **sin ningún gancho de sincronización, 5 de 40**: la
   ventana no la fabrica el arnés.
3. **El remedio que proponía `bench/cerrojo-de-maquina.md` §6.3 —`FILE_SHARE_NONE`
   por `ctypes`— funciona y es el caro.** Con esa asa abierta el tercero hace
   **0 aberturas en 12 393 intentos**… **y mi propio `os.replace` también falla
   con `WinError 5`**. Quedarse el asa obliga a escribir a través de ella, es
   decir a convertir un `rename` en una copia entera.
4. **Lo que cierra la ventana es no tenerla: `os.replace` en lugar de
   `shutil.move`.** Sobre el mismo estado, `shutil.move` **PISA** (4 014 B →
   13 516 B) y `os.replace` **se niega** dejando el fichero intacto. La detección
   y la acción pasan a ser **la misma llamada del sistema**.
5. **No cuesta: PAGA.** Sobre un destino que ya existe, `mover_a_destino` cuesta
   **556,5 µs** frente a los **10 041,1 µs** de `shutil.move`: **×18,0 más
   rápido**, porque el `shutil.move` de antes caía a `copy2`. Cruzando volúmenes
   cuesta **+712,3 µs** (+7,7 %), el 0,18 % de una conversión.
6. **Y hay un efecto lateral que no esperaba y que es el hallazgo secundario:**
   con el `move` seguro, **FileX protege al tercero aunque la detección esté
   apagada**. Una prueba del reparto anterior se puso roja por eso y hubo que
   apagar las **dos** variables para seguir reproduciendo el fallo histórico.

Suite: **256 passed, 6 skipped** *(base 251 + 6; +4 de `VentanaAntesDelMove` y
+1 de `TerceroQueNoCoopera`. **Cero movimientos en las 251 anteriores**, salvo
una que se puso roja y se actualizó — y el motivo es el hallazgo de §7)*.

**Y con el tiempo que sobró, N16 — solo medición, sin tocar
`filex/verificador.py`:** el punto ciego de A7 a bitrate bajo **se cierra
entero**, pero no con la señal que proponía el pendiente. La ventaja cruzada
—`corr(Rsal,Lent) − corr(Rsal,Rent)`— **no separa** (hueco −0,7983); el término
simple **`corr(Rsal, Rent)` sí**, en las **nueve** tasas, con una meseta de
umbral de **0,008 a 0,13** en la que atrapa **27 de 27 con 0 falsos positivos de
45**, frente a las **9 de 27** que atrapa A7 hoy. Cuesta **183,1 ms** donde A7
gasta ya **364,0**. Detalle en §8 bis.

---

## 1. De dónde sale la fila, y qué decía exactamente

`bench/cerrojo-de-maquina.md` §6, punto 3:

> **La detección es un INSTANTE, no una vigilancia.** Entre el `os.replace(p,p)`
> y el `shutil.move` hay una ventana. Se ha hecho lo más estrecha que se puede
> —son las dos líneas siguientes— pero no es cero, y quien llegue dentro de esa
> ventana pisa igual. **Cerrarlo del todo exigiría abrir el destino con
> `FILE_SHARE_NONE` y escribir a través de ese handle**, que en Python no se
> puede sin `ctypes` y `msvcrt.open_osfhandle`. **PENDIENTE, declarado.**

Dos agentes la tuvieron asignada y ninguno llegó. El encargo pedía **medir antes
de arreglar**, y avisaba de que podía encogerse al medirla, como N4 y N5. **No se
ha encogido: se ha ensanchado.** Lo que sí se ha caído es el remedio propuesto.

---

## 2. La ventana existe, y dura 681,4 µs — **MEDIDO**

`bench/salidas-ventana/medir_ventana.py --modo A`. Sin tercero y sin gancho:
solo dos relojes, uno cuando la detección final retorna y otro cuando el
movimiento termina. n=15 por tanda, testigos limpios en las dos.

| Tanda | mediana | mín | p90 | máx | testigos |
|---|---:|---:|---:|---:|---|
| **antes** (`shutil.move`, `FILEX_MOVE_SEGURO=0`) | **681,4 µs** | 471,4 | 996,1 | 1 148,2 | deriva 0,81 · proceso 36,6→42,4 ms · `limpia` |
| **después** (`os.replace`) | 556,6 µs | 423,7 | 811,8 | 971,6 | deriva 0,87 · proceso 38,1→41,4 ms · `limpia` |

Una tanda anterior de n=12 dio **498,0 µs**; las cifras absolutas de tandas
distintas no son comparables, así que lo que se publica es el **orden de
magnitud: medio milisegundo largo**, no microsegundos.

**Contra qué se compara.** `bench/cerrojo-de-maquina.md` §7 publica la detección
en **20,2 µs** (destino ausente) y **138,7 µs** (destino existente). Esta tanda,
con los mismos primitivos, da **26,6** y **193,4 µs**: mismo régimen, tanda algo
más cargada. **La ventana es ×34 la detección que la precede.**

### 2.1 El reloj casi se lleva por delante la medida — **MEDIDO**

La primera pasada usó `time.time_ns()`, que es lo obvio para comparar dos
procesos, y publicó una mediana de **~1,00 ms** con celdas de **exactamente 0 ns**
y de **1 000 100 ns**. No era el código: **`time.get_clock_info('time').resolution`
vale 0,015625 s en esta máquina**, es decir un tic de **15,625 ms**. Se estaba
midiendo el tamaño del tic.

Lo que sí vale, y **está sondeado en ejecución, no deducido**:
`time.perf_counter_ns()` en Windows es `QueryPerformanceCounter` **crudo** —con
`QPF = 10 000 000` medido, `perf_counter_ns() − QPC×100 = 600 ns`, que es el
tiempo entre las dos llamadas—, así que **es comparable entre procesos** aunque
la documentación solo lo garantice dentro de uno. Resolución: 100 ns.

---

## 3. El mecanismo, sondeado sin una sola carrera — **MEDIDO**

`sonda_mecanismo.py` → `sonda_mecanismo.json`. Todos los estados se construyen a
mano, como en `bench/contenedor-parar.md` §1: aquí no se gana ninguna carrera.

| | Pregunta | Respuesta |
|---|---|---|
| **M1** | `shutil.move` sobre un destino que existe, ¿hace `rename`? | **No.** `os.rename` falla con `FileExistsError`/**`WinError 183`** y `shutil` cae a `copy2`: el destino de 4 014 B pasa a valer 1 000 B. Confirma la trampa 33. |
| **M2** | `shutil.move` con el destino **abierto por un tercero** | **PISÓ.** 4 014 B → **13 516 B**, que son los números exactos del hito 7 reproducidos por otra ruta. |
| **M3** | `os.replace(origen, destino)` en **ese mismo estado** | **Se negó**, `PermissionError` / **`WinError 5`**, y el fichero del tercero **quedó en 4 014 B**. |
| **M4** | `os.replace` de `C:` a `D:` | Falla con **`WinError 17`**, que llega como **`errno.EXDEV` (18)**. Distinguible de «ocupado», que es `EACCES` (13). |
| **M5** | `CreateFileW` con `dwShareMode = 0` | **Se consigue el asa** (`GetLastError = 0`) y **excluye al tercero por completo: 0 aberturas en 12 393 intentos**. **Pero también me excluye a mí:** con el asa abierta, `os.replace` sobre ese destino da `WinError 5` y `shutil.move` da `Errno 13`. |

**M5 es lo que refuta el pendiente.** `FILE_SHARE_NONE` no es un candado que se
pone al lado del `move`: es un candado que **impide** el `move`. Para usarlo hay
que abrir el destino al principio y **volcar el contenido a través de la asa**,
lo que (a) sustituye un `rename` por una copia siempre, y (b) crea el fichero de
destino —vacío— **antes** de saber si la conversión va a salir bien.

M3 dice que no hace falta. **`os.replace` ya es el `os.replace(p,p)` de la trampa
27 y el movimiento a la vez.** No hay «entre medias» donde colarse porque no hay
dos llamadas.

---

## 4. Reproducida entre procesos, con `la_ventana_se_abrio` por celda — **MEDIDO**

La trampa 38 dice que un arnés de carrera que no comprueba si la condición se dio
sale verde sin probar nada. Cada celda registra el reloj **del tercero** —otro
proceso— y lo compara con el intervalo `[detección, fin del movimiento]` **del
convertidor**. Eso es lo que exige el reloj común de §2.1.

Dos escenarios, porque no son el mismo fallo:

* **E1 — destino AUSENTE**, el caso normal de un conversor. La detección dice
  «libre» con razón y el tercero **crea** el fichero dentro de la ventana.
* **E2 — destino PRESENTE y libre.** La detección dice «libre» con razón y el
  tercero lo **abre** dentro de la ventana.

### 4.1 Modo B — con centinela (la carrera fabricada)

El gancho suelta al tercero justo cuando la detección ha dicho «libre». Todas
las tandas, n=12, testigos limpios.

| Tanda | `la_ventana_se_abrio` | atropellos | veredictos de FileX |
|---|---:|---:|---|
| **E2 antes** (`shutil.move`) | **12 / 12** | **12** | 12 × `ok_parcial` |
| **E2 después** (`os.replace`) | **12 / 12** | **0** | 12 × `fallo` |
| **E1 antes** | **12 / 12** | **12** | 12 × `ok_parcial` |
| **E1 después** | **12 / 12** | **0** | 12 × `fallo` |

En las cuatro tandas **la condición se dio en las 12 celdas**, así que las dos de
«después» son un cero que significa algo. Y en las de «después» el fichero del
tercero quedó **intacto en 4 014 B, con su cabecera `TTTT`**, celda a celda.

### 4.2 Modo C — martillo, sin ningún gancho (el control)

Un tercero que golpea el destino en bucle con 2 ms de pausa, sin saber nada de
FileX. n=40.

| Tanda | `la_ventana_se_abrio` | atropellos |
|---|---:|---:|
| **antes** | **5 / 40** | **5 de 5** |
| **después** | **0 / 40** | 0 |

**Las 5 de «antes» son lo que hace honesto al modo B: la ventana no la fabrica el
arnés.** El 5/40 es coherente con el reloj —la ventana ocupa ~0,68 ms de cada
~2,3 ms de ciclo del martillo, y solo cuenta si además cae fuera del instante de
la detección—.

**El 0/40 de «después» NO prueba el arreglo**, y decirlo es la mitad del trabajo:
son cero celdas en las que la condición se dio, exactamente la trampa 38. Lo que
sí dice es que **la ventana se encogió** al desaparecer el `copy2`. La prueba del
arreglo es §4.1, donde la condición se dio 12 de 12.

---

## 5. El arreglo, y lo que cuesta — **MEDIDO, trozo aislado**

`filex/nucleo.py::mover_a_destino`, llamada desde `_un_salto` en lugar de
`DirectorioDeTrabajo.recoger`:

1. `os.makedirs(dir_destino, exist_ok=True)`;
2. **`os.replace(origen, destino)`** — atómico, y es el que decide;
3. si y solo si el `errno` es **`EXDEV`**, copia a un temporal
   `.filex-<uuid>.parcial` **en el directorio de destino** y vuelve a hacer
   `os.replace` sobre él;
4. `FileNotFoundError` **se deja pasar tal cual** — «no está» no es «no se
   puede» (trampa 43), y aquí «no está» sería un fallo nuestro, no un ocupante;
5. cualquier otro `OSError` se convierte en `DestinoOcupado`, que `_un_salto`
   traduce al mismo `fallo` y al mismo motivo que ya devolvía la detección.

`FILEX_MOVE_SEGURO=0` devuelve el `shutil.move` de antes, por el mismo motivo que
existen `FILEX_CERROJO_DESTINO` y `FILEX_CERROJO_MUTEX`: medir el antes y el
después dentro de la misma tanda, y que una prueba pueda fallar por el fallo que
dice cubrir. **El defecto es el seguro**, y hay una prueba que lo comprueba en un
intérprete limpio.

### 5.1 El coste

`coste_move.py`, n = 1 500 por fila (400 al cruzar volumen), carga de 17 530 B —
el tamaño real de la salida `png→webp` del corpus. Tanda limpia: deriva **1,01**,
testigo de proceso **35,7 → 28,9 ms**. **Nada se mide por diferencia** (trampa 36):
cada fila cronometra su operación y el fichero de origen se fabrica fuera del
reloj.

| Operación | mediana | p90 |
|---|---:|---:|
| `os.replace` destino **ausente** (mismo volumen) | 312,3 µs | 403,5 |
| `os.replace` destino **existente** (mismo volumen) | 382,0 µs | 486,9 |
| `shutil.move` destino **ausente** (mismo volumen) | 365,6 µs | 509,6 |
| **`shutil.move` destino existente** (cae a `copy2`) | **10 041,1 µs** | 12 158,6 |
| `mover_a_destino` **cruzando volumen** | 9 994,4 µs | 11 826,9 |
| `shutil.move` **cruzando volumen** | 9 282,1 µs | 10 725,8 |
| **`mover_a_destino` destino ausente** (mismo volumen) | **470,5 µs** | 579,5 |
| **`mover_a_destino` destino existente** (mismo volumen) | **556,5 µs** | 725,1 |
| *control* — detección, destino ausente | 26,6 µs | 43,7 |
| *control* — detección, destino existente | 193,4 µs | 245,8 |
| *control* — `os.makedirs(exist_ok=True)` | 136,5 µs | 198,9 |

**Cómo se lee, sin restar nada:**

* **Sobrescribir un destino que ya existe: 556,5 µs frente a 10 041,1. ×18,0 a
  favor del arreglo.** No es una optimización buscada: es que el camino de antes
  copiaba 17 KB donde ahora se renombra.
* **Destino ausente: 470,5 µs**, frente a los 365,6 del `shutil.move` **más** los
  136,5 del `makedirs` que `recoger` hacía igual — es decir, **502,1 µs de
  trabajo equivalente**. La diferencia cae dentro del suelo de ±70 µs de la
  trampa 36, así que lo honesto es **«sin diferencia medible»**, no «−31,6 µs».
* **Cruzando volumen sí hay un cargo real: +712,3 µs (+7,7 %)**, que es el
  `os.replace` extra sobre el temporal. Sobre la conversión `png→webp` de 391,5 ms
  ya publicada, eso es el **0,18 %**. El cerrojo entero cuesta 1 169,7 µs
  (0,319 %); el arreglo lo sube a **~1 882 µs, el 0,48 %**, y solo cuando el
  desechable y el destino están en discos distintos.

### 5.2 Un dato del arnés que casi cuesta una publicación falsa

La primera pasada de `coste_move.py` reusaba los mismos nombres de destino entre
filas, así que a partir de la segunda **el destino ya existía** y las filas
«AUSENTE» medían el camino de «EXISTENTE»: `shutil.move` salía a **10 137,5 µs**
en un `rename` que no era tal. Titular que estuvo a punto de escribirse:
*«`os.replace` es 32× más rápido que `shutil.move`»*. Es la trampa 38 en versión
de medición: **el arnés no estaba en el estado que decía**.

---

## 6. Qué NO cubre — sin adornos

1. **El tercero que escribe y CIERRA dentro de la ventana.** `os.replace` pisa un
   destino que existe y que nadie tiene abierto — **tiene que hacerlo**, porque
   eso es exactamente sobrescribir un destino legítimo. Desde dentro del proceso
   los dos casos son indistinguibles. *(Solo `FILE_SHARE_NONE` desde el principio
   de la conversión lo taparía, al precio de §3 M5 y de crear el destino antes de
   saber si la conversión sale bien.)*
2. **POSIX.** Allí `os.replace` sobrescribe aunque el fichero esté abierto, igual
   que antes: **la detección sigue sin existir** (`cerrojo-de-maquina.md` §6.5,
   matizado por la trampa 45). Lo que POSIX **sí gana** es la **atomicidad**: ya
   no queda nunca un destino a medio escribir. **PENDIENTE de medir allí.**
3. **Un LECTOR sigue bastando para negarse.** El falso positivo de la trampa 33 no
   mejora ni empeora: es el mismo primitivo, y `WinError 5` no distingue quién
   tiene la asa ni para qué.
4. **Después de escrito.** Lo que le pase a la salida un milisegundo más tarde
   sigue sin ser de este cerrojo (punto 7 de la lista de N-b).
5. **Si el destino es un DIRECTORIO existente**, `shutil.move` metía la salida
   dentro y `os.replace` se niega. **Es un cambio de comportamiento** y negarse
   es lo correcto —nadie pidió esa ruta—, pero llega envuelto en
   `DestinoOcupado`, así que el motivo que ve el cliente dice «otro proceso tiene
   abierta esa ruta» y **es falso en ese caso**. **PENDIENTE**, y es la trampa 44:
   un mensaje que promete algo que no ha ocurrido.
6. **`DirectorioDeTrabajo.recoger` sigue existiendo y ya no lo llama nadie en
   producción.** No se ha tocado porque `filex/trabajo.py` es de otro reparto;
   quien lo herede tiene que decidir si lo borra o lo reescribe sobre
   `mover_a_destino`, porque **hoy es una función pública que pisa en silencio**.

---

## 7. La suite, prueba a prueba

**256 passed, 6 skipped** (base: 251 + 6). Las cinco pruebas nuevas son de
`pruebas/test_cerrojo.py`, que es un fichero de este reparto.

**+4 pruebas nuevas**, en `pruebas/test_cerrojo.py::VentanaAntesDelMove`:

| Prueba | Qué comprueba |
|---|---|
| `test_con_shutil_move_el_tercero_de_la_ventana_es_atropellado` | El fallo, entre dos procesos de verdad, con `FILEX_MOVE_SEGURO=0`. **Falla si el arreglo se pone y no se apaga la variable**, que es lo que la hace una prueba del fallo. |
| `test_con_os_replace_filex_se_niega_y_no_lo_toca` | El arreglo: `fallo`, motivo correcto y el fichero del tercero **intacto en 4 014 B**. **Esta es la que se pone roja si se revierte `mover_a_destino`.** |
| `test_el_move_seguro_es_el_defecto` | En un intérprete limpio sin la variable, `_move_seguro()` es `True`. |
| `test_cruzar_volumen_no_se_confunde_con_ocupado` | El camino `EXDEV`: mueve, borra el origen y **no deja el `.parcial`**. Se salta si no hay dos volúmenes a mano. |

**Comprobado que fallan sin el arreglo, no supuesto.** Con `_move_seguro()`
forzado a `False` —es decir, revirtiendo `mover_a_destino` a `shutil.move`—
la suite responde **`2 failed, 1 passed`**:
`VentanaAntesDelMove::test_con_os_replace_filex_se_niega_y_no_lo_toca` cae con
`AssertionError: True is not false` (FileX devolvió `ok`) y con él
`TerceroQueNoCoopera::test_aun_sin_deteccion_el_move_seguro_protege_al_tercero`.
`test_cruzar_volumen_no_se_confunde_con_ocupado` sigue pasando, porque el
camino `EXDEV` funciona en las dos versiones.

Las dos primeras **comprueban `la_ventana_se_abrio` antes de mirar el
resultado**, y ese campo lo produce el proceso convertidor, no el arnés padre. Sin
esa comprobación, la segunda pasaría igual si el tercero no hubiera llegado nunca.

**La prueba fabrica la ventana a propósito, y hay que decirlo:** el gancho espera
el acuse del tercero antes de seguir. La ventana real se acierta 12 de 12 veces
sin esperar a nada (§4.1), pero **una prueba de regresión no puede depender de
acertar una carrera**. La medición no lleva esa espera; la prueba sí.

**+1 prueba nueva y 1 movimiento**, en `TerceroQueNoCoopera`:

* `test_sin_deteccion_filex_pisa_el_fichero_de_un_tercero` **se puso ROJA** con el
  arreglo puesto: pedía `FILEX_CERROJO_DESTINO=proceso` y esperaba que FileX
  pisara, y **`os.replace` se niega aunque la detección esté apagada**. Se ha
  actualizado para apagar **las dos** mitades (`FILEX_MOVE_SEGURO=0`). Es mi
  fichero, así que se toca aquí.
* Y se ha añadido `test_aun_sin_deteccion_el_move_seguro_protege_al_tercero`, que
  fija ese hallazgo: **las dos mitades ya no son independientes.** La detección
  previa deja de ser la única defensa y pasa a ser **un atajo** —ahorra 250 ms de
  conversión y, cruzando volúmenes, una copia entera—. Se ha dejado por eso, no
  por redundancia.

**Ninguna prueba de un fichero ajeno se movió.**

**La huella del sondeo no se movió** — comprobado, no supuesto:
`sondeo.diagnostico()` devuelve `{"sin_huella": [], "caducados": {},
"build_distinto": []}` sobre las 215 aristas, antes y después. `nucleo.py` no
entra en ninguno de los tres componentes.

---

## 8. Lo que abre esto

1. **POSIX: medir si la atomicidad basta.** `os.replace` allí no detecta, pero
   nunca deja un destino a medias. **PENDIENTE**, y `cerrojo.abierto_por_un_tercero(...,
   barrido_proc=True)` ya existe para quien quiera pagar los 3 679,8 µs.
2. **El caso «escribe y cierra dentro de la ventana» (§6.1) no tiene defensa
   barata.** Antes de escribir una, habría que medir si ocurre alguna vez fuera
   de un arnés: es un tercero que abre, escribe y cierra un fichero en menos de
   medio milisegundo.
3. **El motivo falso del §6.5.** Separar «el destino es un directorio» de «hay un
   ocupante» cuesta un `os.path.isdir` (~30 µs) y arregla un mensaje que hoy
   miente. Es pequeño y es de este fichero.
4. **`DirectorioDeTrabajo.recoger` es código público que pisa en silencio** y ya
   no lo llama nadie. No es mío.

---

## 8 bis. N16 — el punto ciego de A7 a bitrate bajo: **la señal existe, y no es la propuesta**

*(Medición pura. **No se ha tocado `filex/verificador.py`**, que es de otro
reparto. Lo que sigue es una propuesta con sus números, no un cambio.)*

`bench/contrato-familia-resvg.md` §2.5 dejó el punto ciego medido —por debajo de
48 kb/s Opus rellena el canal mudo con una copia del otro y A7, que mira RMS por
canal, no puede opinar; a 32 kb/s falla por **1,03 dB**— y su pendiente 2 propone
*«comparar la CORRELACIÓN entre canales de entrada y salida. Sin medir.»*

`bench/salidas-ventana/a7_bitrate_bajo.py`: **90 celdas**, 5 fuentes × 9 tasas ×
2 clases, todas deterministas.

### 8bis.1 La hipótesis del pendiente se cae — **MEDIDO**

La forma natural de la propuesta es la **ventaja cruzada**: si el derecho se
perdió y Opus lo rellenó copiando el izquierdo, el derecho de la salida debería
parecerse al **izquierdo** de la entrada.

    ventaja = corr(Rsal, Lent) − corr(Rsal, Rent)

**No separa nada:** malas en `[−0,0001 , 1,0266]`, buenas en `[−1,0414 , 0,7982]`,
**hueco −0,7983**. El motivo es la trampa 50 otra vez: a tasa baja **Opus colapsa
el estéreo a mono también en la conversión buena**, así que `Rsal ≈ Lsal ≈ Lent`
en las dos clases y el término cruzado sube en las dos.

Las otras dos señales «obvias» tampoco: «¿es mono la salida?» (`RMS(L−R)` frente
a la mezcla) da **hueco −∞**, y `corr(Lsal, Rsal)` da **−0,9963**.

### 8bis.2 Lo que sí separa es el término SIMPLE — **MEDIDO**

**`corr(Rsal, Rent)` a secas**, con la salida alineada a la entrada:

| Tasa | peor MALA | mejor BUENA | hueco | A7 hoy |
|---|---:|---:|---:|---|
| 6k | +0,0029 | +0,1341 | **+0,1312** | 0 / 3 |
| 8k | +0,0059 | +0,1552 | **+0,1493** | 0 / 3 |
| 12k | +0,0054 | +0,1653 | **+0,1599** | 0 / 3 |
| 16k | +0,0048 | +0,1706 | **+0,1658** | 0 / 3 |
| 24k | +0,0069 | +0,7625 | **+0,7556** | 0 / 3 |
| 32k | +0,0009 | +0,9661 | **+0,9652** | 0 / 3 |
| 48k | +0,0048 | +0,9735 | +0,9687 | 3 / 3 |
| 64k | +0,0051 | +0,9954 | +0,9903 | 3 / 3 |
| 96k | +0,0044 | +0,9976 | +0,9932 | 3 / 3 |

**Las nueve tasas separan.** A7 hoy atrapa **9 de 27**; la señal, **27 de 27**.

**La meseta, tabulada antes de elegir el umbral** (trampa 51):

| Umbral | atrapa | falsos positivos |
|---:|---:|---:|
| < 0,002 | 15 / 27 | 0 / 45 |
| < 0,005 | 23 / 27 | 0 / 45 |
| **< 0,008 … < 0,13** | **27 / 27** | **0 / 45** |
| < 0,15 | 27 / 27 | 1 / 45 |
| < 0,20 | 27 / 27 | 4 / 45 |
| < 0,70 | 27 / 27 | 12 / 45 |

La meseta va de **0,008 a 0,13** y es plana entera. El borde de abajo está a un
pelo del peor caso malo (0,0069), así que **el valor que se propondría es 0,05**
—cerca del centro geométrico de la meseta, √(0,008 × 0,13) ≈ 0,032— y no su
borde: aquí «el borde de abajo de la meseta» de la trampa 51 dejaría **1,4 dB**
de margen y el centro deja un factor **×7**.

### 8bis.3 La tercera clase que no estaba en el enunciado

De las 90 celdas, 45 son buenas, **27 son malas que PIERDEN algo** y **18 son
malas que no pierden nada**: si los dos canales de la entrada ya eran iguales,
rellenar el derecho con una copia del izquierdo no destruye información. Contarlas
como «malas» inventaría un solape que no existe, así que se separan por
`corr(Lent,Rent) < 0,90`, que es un dato **de la entrada** y por tanto conocido
antes de juzgar la salida.

La señal toca **8 de esas 18**, y **no son falsos positivos**: son las de ≥32 kb/s,
donde el canal derecho sale de verdad mudo (**−77,75 a −300,22 dBFS**). A7 ya
atrapa 6 de las 8; las 2 que se le escapan son justo las de **32 kb/s**, es decir
**el caso que fallaba por 1,03 dB**. La señal lo cierra **sin tocar el umbral de
−80 dBFS**, que era la objeción del informe original.

### 8bis.4 El coste — **MEDIDO, trozo aislado**, sobre 8,0 s de estéreo a 48 kHz

`a7_coste_senal.py`, n=15 por fila, tanda limpia (deriva 1,09, testigo de proceso
29,9 → 30,1 ms).

| Trozo | mediana | p90 |
|---|---:|---:|
| decodificar la ENTRADA a PCM | 69,75 ms | 77,83 |
| decodificar la SALIDA a PCM | 54,60 ms | 57,27 |
| **alinear por FFT + 3 correlaciones** | **58,72 ms** | 73,04 |
| *(alinear a fuerza bruta, el del arnés)* | *1 813,69 ms* | 1 862,30 |
| *control* — `astats` de la entrada (lo que A7 hace hoy) | 102,78 ms | 108,20 |
| *control* — `astats` de la salida (lo que A7 hace hoy) | 261,26 ms | 276,84 |

**Las dos lecturas, y hay que dar las dos:**

* **Si se AÑADE** a lo que A7 hace hoy: **+183,1 ms** sobre los 364,0 que ya
  gasta, un **+50,3 %** de la regla.
* **Si SUSTITUYE** a los dos `astats` —el RMS por canal sale del mismo PCM que hay
  que decodificar igual—: **183,1 ms frente a 364,0. La mitad.** Esta es la
  propuesta.

### 8bis.5 Dos avisos, y el segundo casi tumba el resultado

1. **El único fichero estéreo del corpus es prácticamente mono.**
   `corpus/audio/habla_jfk.flac` tiene **`corr(L,R) = 0,9997`**; los otros cuatro
   son mono. **A7 nunca se ha calibrado contra un estéreo de verdad**, y las
   cuatro fuentes de canales desiguales de esta tanda hubo que fabricarlas.
   Es la trampa 50 en su forma de corpus: si no varías la entrada, mides tu
   entrada.
2. **La primera pasada concluyó que a 6 y 8 kb/s NO había señal, y era del
   arnés.** El alineamiento por barrido a **paso 8** se salta el óptimo: sobre el
   mismo par devuelve desfase 0 donde la FFT devuelve −2, y con ese desfase la
   correlación de una salida buena sube de **0,9415 a 0,9718**. Redondear el
   alineamiento **subestima solo el lado bueno**, que es justo el que fija el
   hueco: con paso 8, 6k y 8k salían solapadas (−0,0165 y −0,0191) y el titular
   iba a ser *«el punto ciego se reduce de seis tasas a dos»*. Con la alineación
   correcta **se cierra entero**. El control positivo que lo destapó está en
   `a7_coste_senal.json`.

### 8bis.6 Lo que NO se ha medido

* **Otros códecs.** Todo esto es `libopus`. Un MP3 o un AAC a tasa baja pueden
  hacer otra cosa (`joint stereo` no es lo mismo que el colapso a mono de Opus).
* **Fuentes reales de canales desiguales.** Las cuatro son fabricadas por el
  arnés; el corpus no tiene ninguna (aviso 1).
* **El canal IZQUIERDO perdido**, y las pistas más allá de la 0 — que es el
  pendiente 3 del informe original y sigue igual.
* **Qué pasa cuando el pedido cambia la energía a propósito.** A7 ya se retira en
  ese caso (`_A7_PEDIDO_MUEVE_ENERGIA`) y la señal tendría que retirarse igual.

---

## 9. Propuestas para `CLAUDE.md` — **NO APLICADAS** (van AL FINAL, nunca en medio)

> **62. La REJILLA del instrumento puede ser más gruesa que el efecto, y entonces
> lo que publicas es la rejilla — MEDIDO, dos veces en el mismo día**
> (`bench/ventana-antes-del-move.md` §2.1 y §8bis.5).
>
> * **El reloj.** `time.time_ns()` es lo obvio para comparar dos procesos y **en
>   esta máquina tiene un tic de 15,625 ms** (`time.get_clock_info('time')
>   .resolution`). Midiendo una ventana de medio milisegundo devolvió celdas de
>   **0 ns** y de **1 000 100 ns**, y la primera pasada publicó «~1 ms de
>   mediana», que era el tamaño del tic y no el de la ventana.
>   `time.perf_counter_ns()` da 100 ns y **en Windows es
>   `QueryPerformanceCounter` crudo, sin origen por proceso** —sondeado:
>   `perf_counter_ns() − QPC×100 = 600 ns` con `QPF = 10 MHz`—, así que **sí
>   sirve entre procesos** aunque la documentación solo lo garantice dentro de
>   uno.
> * **El alineamiento.** Buscar el desfase entre dos audios con un barrido a
>   **paso 8** se salta el óptimo: donde una FFT da −2 muestras, el barrido da 0,
>   y la correlación de una conversión BUENA baja de **0,9718 a 0,9415**. Como el
>   error solo aprieta el lado bueno, **fabricó un solape que no existía** y la
>   conclusión iba a ser «a 6 y 8 kb/s no hay señal».
>
> **Antes de cronometrar o de correlacionar, pregúntale a tu instrumento su
> resolución y compárala con el efecto que buscas.** `get_clock_info` la dice y
> no cuesta nada; para lo demás, mide la versión fina una vez como control
> positivo — si da otro número, la gruesa no era la misma medida.

> **63. `os.replace` no es «`os.rename` que sobrescribe»: es la DETECCIÓN y la
> ACCIÓN en una sola llamada, y por eso no deja ventana — MEDIDO** (ídem §3).
> El proyecto ya sabía que `os.replace(p, p)` es el único cerrojo real en Windows
> (trampa 27) y que `shutil.move` sobre un destino existente cae a `copy2` y pisa
> (trampa 33). **La consecuencia que faltaba es que son el mismo primitivo**: si
> el movimiento final se hace con `os.replace(origen, destino)`, el ocupante lo
> para con `WinError 5` y no hay «entre medias» donde colarse — 12 de 12 celdas
> con la ventana abierta pasaron de 12 atropellos a 0. **Y encima es ×18,0 más
> rápido** al sobrescribir, porque el camino de antes copiaba. **Cuando una
> defensa consista en «comprobar y luego actuar», busca la llamada del sistema
> que hace las dos cosas antes de escribir un candado alrededor.**

> **64. Un candado que excluye a todo el mundo te excluye a ti, y el precio no
> está en el candado sino en lo que te obliga a hacer después — MEDIDO** (ídem
> §3 M5). `CreateFileW` con `dwShareMode = 0` sobre el destino deja al tercero en
> **0 aberturas de 12 393 intentos**, que es exactamente lo que se le pedía; pero
> con esa asa abierta **`os.replace` y `shutil.move` del propio dueño fallan con
> `WinError 5`**, así que la única forma de usarla es **volcar el contenido a
> través de ella** — un `rename` convertido en copia, y un destino creado vacío
> antes de saber si la operación va a salir bien. **Un pendiente que propone un
> mecanismo lleva dentro un coste que nadie ha medido: sondéalo antes de
> heredarlo, porque puede que el remedio bueno sea otro y más barato.**

> **65. Cerrar la ventana de una defensa puede hacer redundante a la otra mitad,
> y eso se ve porque una prueba VIEJA se pone roja — MEDIDO** (ídem §7). Con el
> `move` atómico puesto, `test_sin_deteccion_filex_pisa_el_fichero_de_un_tercero`
> —que apagaba la detección para reproducir el fallo histórico— **dejó de poder
> reproducirlo**: hacen falta las **dos** variables. No era un remiendo del
> arnés: era el aviso de que la detección previa ha pasado de ser la única
> defensa a ser **un atajo** (ahorra 250 ms de conversión y, cruzando volúmenes,
> una copia entera). **Cuando una prueba que documenta un fallo antiguo se pone
> verde sola, no la relajes: pregúntate qué defensa nueva la está tapando y
> escríbelo.**

---

## 10. Ficheros

| Fichero | Qué es |
|---|---|
| `filex/nucleo.py` | `mover_a_destino`, `DestinoOcupado`, `_move_seguro`, y la llamada en `_un_salto`. |
| `pruebas/test_cerrojo.py` | `VentanaAntesDelMove` (4) + `test_aun_sin_deteccion...` (1); `TerceroQueNoCoopera` actualizada. |
| `bench/salidas-ventana/MANIFIESTO.md` | Las órdenes exactas que reproducen todo esto. |
| `bench/salidas-ventana/*.py` | N12: `tercero.py`, `sonda_mecanismo.py`, `medir_ventana.py`, `coste_move.py`. N16: `a7_bitrate_bajo.py`, `a7_coste_senal.py`. |
| `bench/salidas-ventana/*.json` · `logs/` | Las salidas. Todo texto; los binarios viven en desechables que se borran. |
