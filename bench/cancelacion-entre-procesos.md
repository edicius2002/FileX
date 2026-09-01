# La cancelación deja de ser de proceso, y el andamiaje del hilo deja de ser una disciplina

**Agente T.** Tres pendientes: **N10** (`bench/cancelacion-y-servicio.md` §4.1,
*«es de PROCESO»*), **N11** (ídem §4.3, *«`olvidar_hilo()` […] es una disciplina
que hay que recordar»*) y **N13** (`bench/cerrojo-de-maquina.md` §6.5 y §6.6,
los dos huecos POSIX del cerrojo).

Salidas: `bench/salidas-cancelacion-procesos/` (`MANIFIESTO.md`,
`n10_medidas.json`, `sonda_afinidad.json`, `sonda_posix.json`,
`arnes_procesos.py`, `sonda_afinidad.py`, `sonda_posix.py`, `logs/`).
Pruebas: `pruebas/test_cancelacion_procesos.py` (15) y
`pruebas/test_cerrojo_unico.py::DeteccionYAfinidad` (4). Arnés de proceso hijo:
`pruebas/hijo_de_trabajo.py`.

> **Tanda etiquetada `SUCIA`** — la sesión de escritorio remoto está activa a
> propósito (`CLAUDE.md` §3), y además había otro agente (**U**) trabajando en la
> máquina. Testigos de la tanda publicada: deriva **1,086** (14,22 → 15,45 ms,
> sin deriva) y nivel **38,16 → 34,47 ms**. Medianas de **n = 9** en lo de
> proceso y **n = 200** en los microcostes. **Sin GPU y sin contenedores.**

---

## 0. Resumen en seis líneas

| | Antes | Después | |
|---|---:|---:|---|
| Cancelar un trabajo de OTRO proceso | **21 835,4 ms**, y termina `completed` | **456,8 ms**, y termina `cancelled` | ×47,8 — MEDIDO |
| `motor_detenido` desde otro proceso | **`false` 9 de 9** | **`true` 9 de 9** | MEDIDO |
| Un `working` cuyo dueño murió | **sigue `working`, 9 de 9** | **`failed` / `proceso_dueno_muerto`, 9 de 9** | MEDIDO |
| Coste en el camino normal | — | **643,0 µs** por trabajo + **50,0 µs cada 200 ms** | MEDIDO |
| `olvidar_hilo()` a mano en `servicio.py` | **2 sitios** | **0** (y una prueba de AST lo impide) | MEDIDO |
| Barrer el candado en POSIX | PENDIENTE | **decidido que NO: ×1,77 más lento y abre una carrera** | MEDIDO |

Y el precio, que se paga entero: **tocar `filex/invocacion.py` caduca el sondeo
de los cinco motores y el grafo cae de 210 aristas `real` a 57** (§6). Está
avisado, aceptado y **no se ha resondeado**.

---

## 1. N10 — qué había, dicho con precisión

C34 dejó su alcance escrito y era exacto en lo que decía:

> *«Es de PROCESO. El registro vive en la memoria de un `filex`. Cancelar un
> trabajo leído del disco desde otro proceso no alcanza su `Popen`, y la
> respuesta lo dice en vez de fingirlo: `motor_detenido: false`.»*

**Lo que NO era exacto es la frase de al lado.** La respuesta decía además *«la
cancelación queda anotada, el motor no se toca»*, y **no quedaba anotada en
ninguna parte** — MEDIDO leyendo el código y confirmado por el
comportamiento: `Trabajos.get` construye un `Trabajo` **nuevo** al leerlo del
disco y **no lo guarda en `self._t`**, así que el `t.cancelar.set()` de
`job(..., "cancelar")` marcaba un objeto que se tiraba al volver de la función.
Es la trampa 25 en versión de mensaje: **un campo honesto (`motor_detenido:
false`) al lado de una promesa falsa**, y la promesa es la parte que un lector
se cree.

Medido extremo a extremo con **procesos de verdad** (M1, `sin_canal`):

| | |
|---|---:|
| Desde `job(…, "cancelar")` hasta que el trabajo termina | **21 835,4 ms** (20 579,6 – 28 099,2) |
| Estado final | **`completed` 9 de 9** |
| `motor_detenido` | **`false` 9 de 9** |

Es decir: **se pedía cancelar y salía la conversión hecha**, igual que antes de
C34 pero desde fuera. Y los 21 835,4 ms **reproducen los 21 741,8 ms que N-a
midió para la conversión sin cancelar** con un 0,4 % de diferencia, en otra
tanda y por otra ruta: la cancelación entre procesos no restaba nada.

## 2. N10 — la solución: un canal de mando **y** una detección

### 2.1 El mando

Un fichero `<job_id>.cancelar` en el directorio de trabajos, que ya es el sitio
donde las cuatro superficies se ven entre sí. Quien cancela lo escribe; el
proceso dueño lo atiende con **un vigilante por proceso** —un `scandir` cada
`INTERVALO_MANDO = 0,2 s`, no un hilo por conversión— y llama al `cancelar_hilo`
de C34, que ya sabe matar el árbol y el contenedor. **El mando no reimplementa
la cancelación: la hace alcanzable desde fuera del proceso.**

El hilo del vigilante **nace con el primer trabajo y muere con el último**, y la
decisión de morir se toma bajo el mismo cerrojo con el que se decide nacer: sin
esa línea habría una ventana en la que un trabajo se registra contra un
vigilante que ya estaba saliendo.

### 2.2 La detección, que es la mitad que se olvida

*«Un mecanismo que solo alcanza a quien coopera resuelve la mitad»* (trampa 33,
y la lección de N-b y de P). **Aquí la mitad que falta es un `job_id` cuyo
proceso dueño murió sin limpiar**: no hay nadie que atienda el mando.

La respuesta es el hueco para el que P construyó `filex/cerrojo.py` y lo dejó
escrito en su docstring: **un trabajo retiene un candado mientras vive**, y el
candado de rango de bytes **lo suelta el sistema operativo** cuando el proceso
muere. Así que «candado libre + el disco dice `working`» es un huérfano, **y lo
es sin consultar un solo PID**, que es lo que la trampa 31 declara imposible de
automatizar en esta máquina. `cerrojo.dueno()` da además el PID y el instante
**para el log**, nunca como base de la decisión —comprobado en
`test_el_dueno_se_puede_saber_sin_preguntar_por_ningun_PID`—.

M2, con el hijo muerto por `taskkill /F /T` con el motor en vuelo:

| | Sin detección | Con detección |
|---|---|---|
| `job(job_id)` responde | **`working`, 9 de 9** | **`failed`, 9 de 9** |
| `motivo` | — | **`proceso_dueno_muerto`, 9 de 9** |
| ¿Cambia solo con el tiempo? | **NO, 9 de 9 a los 5 s** | — |
| Coste de la respuesta | 9,66 ms | **20,74 ms** |

**Un `working` eterno es peor que un `failed`**: hace esperar para siempre a las
cuatro superficies y al modelo. Y se mira en las **dos** acciones, no solo al
cancelar: preguntar por el estado es donde más se pregunta.

### 2.3 Lo que cuesta que la detección no mienta

**El trabajo no existe para el resto del mundo hasta que tiene su candado.**
`Trabajos.nuevo()` escribe `working` en el disco antes de que arranque el hilo,
y un trabajo `working` sin candado es **un falso huérfano**: otro proceso lo
declararía muerto estando recién nacido. `Servicio._arrancar` espera —con
tope— a que el candado esté tomado antes de devolver el asa. Es la misma
familia que la ventana entre `Popen()` y el registro que C34 cerró:
**una detección con una ventana no es una detección, es un falso positivo con
horario.**

### 2.4 Y el candado se toma DENTRO del hilo, por una razón medida

La versión obvia era tomarlo en `convert()` y soltarlo en el `finally` del hilo.
Se sondeó en ejecución antes de escribirlo (`sonda_afinidad.json`) y salió esto:

| Celda | Resultado |
|---|---|
| A — tomar y soltar en el mismo hilo | libre después: **sí** |
| B — tomar en el principal, soltar en otro hilo | libre después: **sí** |
| C — `ReleaseMutex` crudo desde otro hilo | **`False`, `ERROR_NOT_OWNER` (288)** |
| C — `WaitForSingleObject` tras `CloseHandle` | **`WAIT_OBJECT_0`** |

**Los mutex de Windows tienen afinidad de hilo, y `Candado.soltar()` desde otro
hilo funciona POR ACCIDENTE**: lo que libera el nombre es el `CloseHandle` que
viene detrás, no el `ReleaseMutex`, que falla. Desde fuera todo cuadra —celda B
dice `libre_despues: true`— y por eso es una trampa: **el día que `cerrojo.py`
cachee asas de mutex, soltar desde otro hilo dejaría de funcionar sin un solo
error**. Un mecanismo que se apoya en un efecto colateral no es un mecanismo, así
que el candado se toma y se suelta en el mismo hilo y `_arrancar` espera.

Queda documentado en `filex/cerrojo.py` y fijado por
`test_el_candado_se_suelta_bien_desde_OTRO_hilo`, que romperá **aquí** en vez de
en producción.

### 2.5 El después

| | |
|---|---:|
| Desde `job(…, "cancelar")` hasta que el trabajo termina | **456,8 ms** (415,4 – 483,1) |
| Estado final | **`cancelled` 9 de 9** |
| `motor_detenido` | **`true` 9 de 9** |
| `via` | `"entre procesos"` |

**×47,8**, y el cambio de estado importa tanto como el número: `cancelled` no es
`completed` ni `failed`. Los 456,8 ms se descomponen en la espera del vigilante
(≤ 200 ms, 100 de media), el `cancelar_hilo` de C34 (**155,13 ms** MEDIDOS por
N-a) y el cierre del trabajo —contrato abortado y borrado del desechable de
R18—.

### 2.6 Un `job_id` es una ENTRADA, y aquí compone nombres de fichero

El mando obliga a escribir un fichero cuyo nombre sale del `job_id`, que lo
escribe el modelo o el usuario. Un `job_id` con `../` sacaría el mando del
directorio. Se filtra por lista blanca (`^[0-9a-f]{6,64}$`) **antes de componer
ninguna ruta**: es el predicado léxico de R1 aplicado a un identificador.

Y de paso cierra un agujero que ya estaba, más pequeño y de la misma forma:
`Trabajos.get` hacía `os.path.join(self.dir, f"{jid}.json")` con el `jid` crudo,
así que un `job_id` con travesía convertía `job` en **un lector de JSON ajenos**
—la forma del oráculo de existencia que R4 evita, con otro nombre—. Ahora el
mismo filtro corta antes de tocar el disco. **No lo buscaba: apareció al
preguntarme de dónde venía el nombre del fichero de mando.**

## 3. N11 — la disciplina, sustituida por un mecanismo

C34 lo dejó dicho con las palabras del propio repositorio:

> *«Quien añada una tercera clase de trabajo tiene que hacer lo mismo, y eso es
> una disciplina que hay que recordar, que es justo lo que este repositorio
> evita en las invocaciones.»*

Tres piezas:

1. **`invocacion.hilo_de()`** — gestor de contexto que borra el rastro del hilo
   en su `finally`, pase lo que pase.
2. **`servicio.en_curso(trabajos, t, candado)`** — el andamiaje entero atado a un
   `with`: el rastro del hilo, el registro del mando y el candado.
3. **`Servicio._arrancar(t, cuerpo)`** — la **única puerta** que construye un
   hilo de trabajo. `convert` y `batch` entran por ella; una tercera clase de
   trabajo no puede olvidarse del andamiaje porque **no construye hilos**.

**`hilo_de` NO limpia al entrar, y es una decisión, no un olvido.** Sería la
simetría bonita y abriría una carrera real: entre `Thread.start()` y la primera
línea del hilo cabe un `job(..., "cancelar")` que marque el `ident` recién
nacido, y un borrado de cortesía a la entrada se tragaría esa cancelación. El
reciclaje de `ident` solo ocurre cuando el hilo anterior ya **murió**, y para
entonces su `finally` ya pasó por aquí. Lo prueba
`test_hilo_de_NO_limpia_al_entrar`.

### Las pruebas que fallan si alguien se olvida — sobre el AST, no sobre el comportamiento

`pruebas/test_cancelacion_procesos.py::ElAndamiajeEsUnMecanismo`:

* **`threading.Thread(` en `servicio.py` solo puede aparecer en dos funciones**,
  `_arrancar` (los trabajos) y `_arrancar_vigilante` (el canal). Un tercer sitio
  es una clase de trabajo que se saltó el andamiaje.
* **Toda función que llame a `self.trabajos.nuevo(` tiene que llamar también a
  `self._arrancar(`.** Crear un trabajo y no lanzarlo por ahí es el olvido.
* **`olvidar_hilo` ya no se LLAMA a mano** en `servicio.py`.

La tercera me pilló a mí: la escribí buscando la cadena `"olvidar_hilo()"` en el
texto y **la encontró dentro de un comentario que explicaba que ya no se
llamaba**. Un buscador de texto no distingue una llamada de una mención. Está
reescrita sobre el AST, con el motivo apuntado en su docstring.

## 4. N13 — POSIX, medido en WSL2 y sobre ext4

Los dos pendientes tienen respuesta, y son respuestas distintas.

> **Dónde se midió, porque importa:** dentro de WSL2 y sobre **`/tmp` de Ubuntu,
> que es ext4**. No sobre `/mnt/d`, que es drvfs: medir el candado ahí sería
> medir el puente y no POSIX. Y el candado **no cruza** entre Windows y WSL2 —
> MEDIDO por P con control positivo—, así que estas cifras describen un FileX
> desplegado en Linux, no esta máquina.

### 4.1 §6.5 — la detección: existe, cuesta ×182 y es tuerta

Tres candidatos, cada uno con su control (`sonda_posix.json`):

| Vía | ¿Ve al tercero que solo hace `open()`? | Coste |
|---|---|---:|
| `os.replace(p, p)` | **NO** (y en Windows sí: `WinError 32`) | 20,4 µs |
| `fcntl.flock(LOCK_EX\|LOCK_NB)` | **NO** — sí ve al que también hace `flock` | 22,7 / 13,3 µs |
| barrido de `/proc/*/fd` | **SÍ**, y sin falso positivo | **3 679,8 µs** |

**La frase de §6.5 era exacta**: en POSIX `os.replace(p,p)` no detecta nada.
Y `flock` **es exclusión, no detección** — ve al cooperativo y no al tercero,
que es justo la mitad que faltaba.

Queda `/proc/*/fd`, que sí funciona y trae dos números que hay que decir juntos:
**×182 la detección de Windows** (3 679,8 µs frente a 20,2 µs) y **47 procesos
denegados** de 563 descriptores recorridos — los de **otro usuario**. Sin root,
esta vía es ciega exactamente en el caso multiusuario que el mutex `Global\\` de
P vino a cubrir.

**Decisión: se ofrece, no se activa.** `cerrojo.abierto_por_un_tercero(ruta)` es
la primitiva —Windows por `os.replace`, POSIX por `False`, y `barrido_proc=True`
para quien quiera pagar los 3,7 ms (≈ **1 % de una conversión**)—. **No se
conecta a `nucleo.py`**, y no por prudencia: `filex/nucleo.py` es de otro agente
en esta ronda. Lo que se entrega es el número y la primitiva, no la decisión.

Y una **corrección de mí mismo, encontrada por mi propia prueba**: la primera
versión trataba cualquier `OSError` como «ocupado», así que un destino que
**todavía no existe** —que es el caso normal de un conversor— salía `FileNotFound`
→ **ocupado siempre**. `FileNotFoundError` va aparte, igual que en la versión de
N-b. La prueba `test_un_fichero_que_no_existe_no_revienta` existe por eso.

### 4.2 §6.6 — el barrido: **no compensa**, y el argumento se invierte

La carrera se reprodujo **sin depender de ningún tiempo**, porque en POSIX un
fichero desenlazado sigue vivo mientras alguien lo tenga abierto y el siguiente
`open` crea otro inodo:

| | B cree tenerlo | C cree tenerlo | |
|---|---|---|---|
| barriendo, sin verificar | **sí** | **sí** | **DOS DUEÑOS** |
| barriendo y verificando el inodo tras tomar | no | sí | un dueño |

Cerrar la carrera cuesta **3,0 µs en cada toma**, incluidas las que no barren
nada. Y el motivo que justifica barrer en Windows —N-b midió que sin el `remove`
el ciclo es **×2,3 más lento**— **se invierte en ext4**:

| Ciclo completo (abrir, bloquear, truncar, escribir, soltar) | Mediana (n=200) |
|---|---:|
| con barrido | **16,8 µs** |
| sin barrido | **9,5 µs** |

**Barrer es ×1,77 MÁS LENTO.** Se pagarían 7,3 µs por ciclo más 3,0 µs por toma,
y una carrera nueva, **para ahorrar ~120 B por nombre distinto**.

**El pendiente §6.6 se cierra como decisión medida, no como deuda**: en POSIX no
se barre porque no compensa, no porque falte hacerlo. Y la lección general es
más ancha que el caso: **un argumento de rendimiento medido en una familia de
sistemas de ficheros no se extrapola a la otra ni con el signo.**

## 5. Lo que esto **NO** cubre — sin adornos

1. **La latencia tiene un suelo de `INTERVALO_MANDO` (0,2 s).** El canal es de
   sondeo, no de notificación. Un canal con nombre (mailslot en Windows, FIFO en
   POSIX) bajaría el suelo a la latencia del IPC, a cambio de dos
   implementaciones y de un descriptor por proceso. **No se ha hecho: 456,8 ms
   frente a 21 835,4 no lo justificaba, y el suelo es la parte pequeña del
   número.** PENDIENTE, con la alternativa nombrada.
2. **El mando lo puede escribir cualquiera que sepa escribir en el directorio de
   trabajos.** Es el mismo nivel de confianza que los propios JSON de trabajo,
   que ya viven ahí y ya llevan el estado; en Windows ese directorio es
   `%TEMP%`, que es **por usuario**. Un despliegue multiusuario necesitaría
   permisos explícitos en el directorio. **Declarado, no cerrado.**
3. **La detección declara huérfano a un trabajo que corriera SIN candado.** Si
   `_tomar_candado` falla —directorio de candados no escribible y mutex no
   disponible a la vez—, el trabajo corre igual y `convert` devuelve
   `aviso_cerrojo`, **pero otro proceso lo verá como huérfano**. No se degrada
   en silencio (trampa 13), pero el aviso lo recibe quien lanza, no quien
   pregunta. **PENDIENTE**: llevaría el aviso al JSON del trabajo.
4. **Queda una ventana mínima en el nacimiento.** `Trabajos.nuevo()` escribe
   `working` antes de que el hilo tome el candado, y `_arrancar` la reduce a lo
   que tarde la toma (**374,0 µs**) con tope, pero no es cero. Quien mirase el
   directorio de trabajos en ese instante —sin conocer el `job_id`, que aún no
   se ha devuelto— podría ver un falso huérfano.
5. **`cerrojo.abierto_por_un_tercero` no está conectada a nada.** Es una
   primitiva con su número, y su consumidor natural
   (`nucleo.destino_ocupado_por_un_tercero`) es de otro reparto en esta ronda.
6. **La cancelación entre procesos sigue sin ser síncrona, y no lo finge.** Con
   el dueño vivo se espera hasta `ESPERA_MANDO = 3 s` a ver el efecto; si no
   llega, la respuesta dice *«orden dejada en el disco; el proceso dueño vive y
   la atenderá, pero no lo ha hecho todavía»* con `motor_detenido: false`.
   **9 de 9 llegaron dentro del tope**, pero el tope es lo que se promete.
7. **No hay inventario de huérfanos de MOTOR**, que es el pendiente 5 de C34 y
   sigue igual: aquí se cierra el trabajo, no se persigue un `ffmpeg` que haya
   sobrevivido al árbol.

## 6. El impacto sobre el sondeo — se paga entero

`filex/invocacion.py` gana `hilo_de()`, y el componente `invocacion` de la
huella es **el AST del fichero entero**. MEDIDO, antes y después
(`logs/sondeo_antes.log`, `logs/sondeo_despues.log`):

| | Antes | Después |
|---|---|---|
| Aristas | `real` **210**, `nominal` 5 | `real` **57**, `nominal` 3, `sin_sondear` **155** |
| Motores caducados | ninguno | **los cinco**, todos por `invocacion` |

Es el mecanismo del commit `13181f6` funcionando como se diseñó: el fichero que
decide el `rc` de toda arista cambió, y las medidas que dependían de él dicen que
ya no valen en vez de aparentar que sí. **No se ha resondeado y no se ha tocado
`filex/huella.py` ni el campo `huella` de ningún `filex/sondeo/*.json`**, según
el encargo: el orquestador resondea una sola vez al final de la ronda siguiente.

`filex/servicio.py` y `filex/cerrojo.py` **no son componentes de la huella**
(solo lo son `motor`, `invocacion` y el cierre de `verificar()`), así que sus
cambios no caducan nada — comprobado en el diagnóstico, donde el único
componente que aparece es `invocacion`.

## 7. La suite

| | |
|---|---|
| Antes | `194 passed, 6 skipped` |
| Después | **`212 passed, 6 skipped, 1 failed`** |

**El único rojo es el esperado**, y se deja rojo a propósito:
`pruebas/test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`,
que dice exactamente lo que ha pasado: *«el código que decide estas aristas
cambió después de sondearlas: hay que RESONDEAR»*. Ningún fichero de otro agente
se ha tocado y ninguna otra prueba se ha movido.

Movimiento, prueba a prueba:

* **+15** `pruebas/test_cancelacion_procesos.py` (fichero nuevo).
* **+4** `pruebas/test_cerrojo_unico.py::DeteccionYAfinidad` (fichero mío).
* **1 renombrada, sin cambio de cuenta**:
  `test_cancelacion.py::CancelarPorElServicio::test_cancelar_un_trabajo_de_otro_proceso_lo_dice_en_vez_de_fingir`
  → `…::test_sin_canal_lo_dice_en_vez_de_fingir`. Afirmaba el límite que N10
  cierra; ahora afirma la **vía degradada** (`FILEX_MANDO=0`), que sigue siendo
  honesta. Es mi fichero.
* **−1 verde, +1 rojo**: la del sellado, arriba.

### Que fallen sin el arreglo — comprobado, no supuesto

Con el canal apagado en toda la tanda (`FILEX_MANDO=0`), las nuevas dan
**`4 failed, 1 passed`**:

```
FAILED …::CancelarEntreProcesos::test_cancelar_alcanza_al_motor_de_otro_proceso
FAILED …::CancelarEntreProcesos::test_el_candado_del_trabajo_se_suelta_al_terminar
FAILED …::CancelarEntreProcesos::test_el_dueno_se_puede_saber_sin_preguntar_por_ningun_PID
FAILED …::DuenoMuerto::test_un_working_sin_dueno_vivo_se_detecta_y_se_cierra
```

**La quinta pasa sin el arreglo y hay que decirlo**:
`test_el_mando_se_borra_al_terminar_el_trabajo` comprueba que no queda basura, y
sin canal no se escribe nada que pueda quedarse. Es una prueba de higiene, no de
capacidad.

**Y las de N10 lanzan procesos de verdad** (`pruebas/hijo_de_trabajo.py`). Dos
`Servicio` en el mismo intérprete comparten el registro de `filex.invocacion` y
habrían dado verde sin que existiera canal ninguno: es la trampa 38 —*«un arnés
que espera la carrera equivocada sale verde»*— y es el error que más fácil habría
sido cometer aquí.

## 8. Lo que cuesta en el camino normal — trozo a trozo

**Medido el trozo aislado, no la diferencia entre dos totales** (trampa 36:
dentro de una tanda hay un suelo de ±70 µs). n = 200:

| Trozo | Mediana | Cuándo se paga |
|---|---:|---|
| tomar el candado del trabajo | **374,0 µs** | una vez por trabajo |
| soltarlo | **269,0 µs** | una vez por trabajo |
| un tick del vigilante (`scandir`) | **50,0 µs** | cada 200 ms mientras haya trabajos |
| escribir el mando | **393,0 µs** | solo al cancelar |
| borrar el mando | **184,0 µs** | una vez por trabajo |

**643,0 µs por trabajo** en el candado y 184,0 en la limpieza — el **0,23 %** de
una conversión de 366 ms, y el **0,004 %** de la de 21,8 s que usa el arnés. El
vigilante son **50 µs cada 200 ms**, es decir el **0,025 % de un núcleo**, y solo
mientras hay algo que vigilar: el hilo no existe cuando no hay trabajos.

Y una asimetría que no esperaba, en el coste de **preguntar si el dueño vive**
(M4, n = 200):

| `cerrojo.esta_libre` | Mediana |
|---|---:|
| candado **libre** (respuesta `True`) | **618,0 µs** |
| candado **ocupado** (respuesta `False`) | **168,0 µs** |

**Preguntar por un trabajo vivo es 3,7× más barato que preguntar por uno
muerto**, porque «ocupado» lo corta el mutex en 7 µs mientras que «libre» hace
el ciclo entero de fichero —crear, truncar, escribir metadatos, desbloquear y
barrer—. Es la trampa 28 en otro sitio y **con el signo al revés**: allí la
denegación era la barata; aquí lo caro es la respuesta que dice «sí». No es
explotable —el que pregunta es el propio FileX y ya conoce el `job_id`—, pero
cualquiera que ponga `esta_libre` en un bucle debe saber cuál de las dos ramas
está midiendo.

## 9. Ficheros tocados

| Fichero | Qué |
|---|---|
| `filex/invocacion.py` | `hilo_de()` y `import contextlib`. **Caduca el sondeo.** |
| `filex/servicio.py` | El canal de mando, el vigilante, `en_curso`, `_arrancar`, la detección en `job()`, el filtro del `job_id`. |
| `filex/cerrojo.py` | `abierto_por_un_tercero()` y los MEDIDOS de N13 y de la afinidad de hilo en el encabezado. |
| `pruebas/test_cancelacion.py` | Una prueba renombrada a la vía degradada. |
| `pruebas/test_cancelacion_procesos.py` | Nuevo, 15 pruebas. |
| `pruebas/test_cerrojo_unico.py` | `DeteccionYAfinidad`, 4 pruebas. |
| `pruebas/hijo_de_trabajo.py` | Nuevo. Un `filex` de verdad para lo que es entre procesos. |
| `bench/salidas-cancelacion-procesos/` | Nuevo. Arnés, dos sondas, medidas, logs y `MANIFIESTO.md`. |

**Ninguno de U** (`filex/watcher.py`, `filex/trabajo.py`, `filex/nucleo.py`,
`pruebas/test_hito7.py`, `pruebas/test_cerrojo.py`), ninguno de los prohibidos
(`filex/huella.py`, `filex/sondeo.py`, `filex/sondeo/*.json`,
`pruebas/test_sondeo.py`, `filex/mcp.py`, `filex/api.py`,
`filex/motor_contenedor.py`, `filex/motores.py`, `filex/verificador.py`) y
ningún documento maestro.

---

## 10. Trampas propuestas — **NO APLICADAS**

Van numeradas desde la 40 y **no se han escrito en `CLAUDE.md`**, según el
encargo. Las cinco son de esta ronda y todas MEDIDAS.

**40. Un mutex con nombre de Windows tiene AFINIDAD DE HILO, y soltarlo desde
otro hilo funciona por accidente — MEDIDO**
(`bench/salidas-cancelacion-procesos/sonda_afinidad.json`). `ReleaseMutex` desde
un hilo que no es el dueño devuelve `False` con `ERROR_NOT_OWNER` (288); lo que
deja el nombre libre es el `CloseHandle` que viene detrás. Visto desde fuera todo
cuadra —`esta_libre()` dice `True` después, y una prueba de comportamiento pasa—
y por eso es una trampa: **el día que `filex/cerrojo.py` cachee asas de mutex,
soltar desde otro hilo dejaría de funcionar sin un solo error**. Corolario
general, que es el que vale: **cuando una prueba de comportamiento pasa, sondea
también el mecanismo; «funciona» y «funciona por lo que crees» son dos
afirmaciones distintas.**

**41. Un argumento de rendimiento medido en una familia de sistemas de ficheros
no se extrapola a la otra, ni con el signo — MEDIDO** (`sonda_posix.json`,
WSL2/ext4). En Windows, barrer el fichero de candado hace el ciclo **×2,3 más
rápido** (MEDIDO por N-b) porque el `open` siguiente se ahorra el `ftruncate`. En
ext4 el mismo barrido es **×1,77 más LENTO** (16,8 µs frente a 9,5), **y encima
abre la carrera del inodo desenlazado**, que da **dos dueños del mismo candado**
de forma determinista y cuesta 3,0 µs por toma cerrar. El pendiente §6.6 de
`cerrojo-de-maquina.md` no era una deuda: era una decisión que nadie había
medido.

**42. Una prueba estructural que busca TEXTO no distingue una llamada de una
mención — MEDIDO en mi propia cara.** `assertNotIn("olvidar_hilo()", fuente)`
falló contra **un comentario que explicaba que ya no se llamaba**. Las pruebas
de forma se hacen sobre el **AST**, que es lo que ya hacía `test_sondeo.py` y lo
que hace `huella.py`. Es la trampa 25 en versión de arnés: dos cosas distintas
con la misma pinta.

**43. `os.replace(p, p)` como detección dice «ocupado» cuando el fichero NO
EXISTE, que es el caso normal de un conversor — MEDIDO.** Lanza
`FileNotFoundError`, que es un `OSError`, así que un `except OSError: return
True` escrito con prisa convierte la detección en un «no» permanente sobre todo
destino nuevo. `nucleo.py` ya lo trataba aparte; la copia nueva no, y lo
encontró su propia prueba antes que ninguna conversión. **Toda detección por
excepción necesita separar «no se puede» de «no está».**

**44. Un campo honesto al lado de una nota falsa se lee como una respuesta
honesta — MEDIDO.** `job(…, "cancelar")` sobre un trabajo de otro proceso
devolvía `motor_detenido: false` (verdad) y *«la cancelación queda anotada»*
(falso: `Trabajos.get` construía un `Trabajo` nuevo que no guardaba en el
registro, así que el `Event` se marcaba sobre un objeto que se tiraba). El campo
booleano estaba bien y **nadie lo habría discutido**; la prosa de al lado
prometía algo que no ocurría. **Las notas para el modelo son parte del contrato y
caducan igual que el código: cuando cambie lo que hace una rama, relee lo que
dice.**
