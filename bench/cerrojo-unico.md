# El primitivo único — y «de máquina» deja de ser un título prestado

**Agente P · 27 de agosto de 2026 · máquina de siempre (Windows 10 Home 19045, Python 3.11.9, Git Bash)**
**Encargo:** la mudanza del punto 12.6 de `bench/cerrojo-de-maquina.md`, más sus pendientes **1** (b1) y **4** (b4).
**Ficheros tocados:** `filex/cerrojo.py` (nuevo, 400 líneas), `filex/nucleo.py` (+96 / −119), `pruebas/test_cerrojo_unico.py` (nuevo, 11 pruebas) y este informe.
**Salidas y logs:** `bench/salidas-cerrojo-unico/`.
**No se usó la GPU.** El encargo no la necesita; `nvidia-smi` no se llamó ni una vez.
**Otro agente (Q) trabajaba en la misma máquina.** Todas las comparaciones de tiempo son **dentro de la misma tanda**, y donde no lo son se dice.

---

## 0. Lo que hay que saber, en seis líneas

1. **El pendiente 1 de N-b está REFUTADO, no resuelto: la vía que daba por imposible funciona — MEDIDO.** *«Un mutex con nombre en `Global\` sería lo correcto y exige el privilegio `SeCreateGlobalPrivilege`, que un proceso interactivo sin elevar no tiene.»* Pues **este proceso no lo tiene y lo crea igual**: token de **integridad media**, `BUILTIN\Administradores` marcado **«Grupo usado solo para denegar»**, y `whoami /priv` lista **un solo privilegio, `SeChangeNotifyPrivilege`**. `CreateMutexW("Global\…")` devuelve handle con `GetLastError = 0`.
2. **Y no me lo creí: el objeto está donde dice estar.** `NtOpenMutant` sobre la ruta absoluta `\BaseNamedObjects\<sello>` abre con `NTSTATUS=0`, y el control negativo con un nombre inventado da `0xC0000034`. Es R7 aplicado a mi propio resultado.
3. **La parte que de verdad costaba estaba escondida dentro de la vía buena.** El mutex `Global\` con descriptor **por defecto** es de máquina en el NOMBRE y **de usuario en el ACCESO**: su DACL medida es `(A;;0x1f0001;;;<el usuario>)(A;;0x1f0001;;;BA)(A;;0x1f0001;;;SY)` — **«Everyone» no está**. Otro usuario habría recibido `ERROR_ACCESS_DENIED` y un código escrito con prisa lo llama «no hay infraestructura» y **degrada a cerrojo de usuario justo en el único caso que el mutex venía a cubrir**. Se crea con SDDL explícito, y `ACCESS_DENIED` se trata como **ocupado**, nunca como degradación.
4. **WSL2 no se cierra, y el motivo que se daba era falso — MEDIDO en las dos direcciones y con control positivo.** Se decía que *«el `/tmp` de Ubuntu es otro sistema de ficheros»*. Pero **el `%TEMP%` de Windows SÍ se ve desde WSL2** por `/mnt/c` (9p/drvfs): el fichero es el mismo. Lo que no viaja es **el candado**. Y no es que `flock` no funcione ahí: **dos procesos de WSL2 sí se excluyen entre ellos sobre ese mismísimo fichero**.
5. **b4 reproducido y cerrado, y `realpath` no era la respuesta.** Un **enlace duro** daba **DOS DUEÑOS del mismo fichero**, y un enlace duro **no tiene destino que resolver**: los dos nombres son igual de reales. Lo cierra la identidad de NTFS (`st_dev`+`st_ino`), que igualó los tres alias.
6. **Cuesta 41,7 µs más que el cerrojo de N-b, y esos 41,7 µs no se pueden ver en el total.** El total por conversión es **1 169,7 µs, el 0,319 %** de una conversión de 367,0 ms de la misma tanda. **Lo añadido está por debajo del ruido entre configuraciones**, y por eso se publica medido pieza a pieza y no por diferencia — §5.2.

---

## 1. La mudanza: `filex/cerrojo.py`

N-b lo dejó dicho: *«`_tomar_candado`/`_soltar_candado` son 40 líneas y no dependen de nada de `filex`: extraerlas es una mudanza, no un diseño»*. Lo es, y por eso lo único que hay que justificar es **la forma de la API**, porque tiene que servir a tres consumidores y hoy solo hay uno conectado.

**El módulo no importa nada de `filex`, y eso es una prueba, no una intención**
(`ApiDelModulo::test_el_modulo_no_depende_de_nada_de_filex`). El motivo es el
tercer consumidor: los arneses `.py` de `bench/` no son la aplicación, y si
`cerrojo` arrastrara `filex`, la fila **C38** de `lock-de-maquina.md` —*«0 de 15
arneses `.py` toman el lock»*— seguiría cerrada por otro motivo distinto.

### 1.1 La API, y qué trozo es de quién

```python
class Candado:
    def __init__(self, nombre, *, metadatos="")
    def tomar(self, espera=0.0) -> bool      # `espera` en segundos, con tope SIEMPRE
    def soltar(self)
    tomado: bool                              # ya tomado
    aviso: str                                # degradación declarada, nunca silenciosa
    dueno: str | None                         # "pid\tepoch\tqué"
    def __enter__/__exit__

def esta_libre(nombre) -> bool
def dueno(nombre) -> str | None
def directorio() -> str
def fichero(nombre) -> str
```

| Consumidor | Qué usa | Qué le hacía falta y no estaba |
|---|---|---|
| **1. Destinos de conversión** (hoy, `filex/nucleo.py`) | `Candado(clave).tomar()` — sin espera | nada: es el caso para el que N-b lo escribió |
| **2. Cancelación entre procesos** (ronda siguiente) | **`esta_libre()`** y **`dueno()`** | Lo que necesita no es excluir: es **saber si el dueño sigue vivo sin preguntarle a nadie por su PID**, que es justo lo que la **trampa 31** declara imposible en esta máquina. Un trabajo retiene su candado mientras vive y `esta_libre()` responde por él |
| **3. El lock de GPU en Python** (fila C38) | **`tomar(espera=900)`** | **Espera con tope.** Es lo único que piden los arneses y no piden los otros dos; por eso `espera` es un parámetro y no un modo. Y **el tope es obligatorio**: un lock que espera sin tope es el defecto 2 del lock viejo |

**Y una decisión de la API que sale de una medida de N-b, no de gusto:** los
metadatos siguen en el fichero y en el offset `1<<30`, porque eso es lo que
permite **leer quién lo tiene mientras está tomado**. `dueno()` comprueba
primero que esté ocupado de verdad —un `taskkill` deja el fichero con su carga
aunque el candado ya esté libre— así que **el fichero puede mentir y el candado
no**, y la función devuelve `None` en cuanto está libre.

### 1.2 Se toman los DOS primitivos, y no es redundancia

| | mutex `Global\` | candado de fichero |
|---|---|---|
| Cruza de **usuario** | **sí** | no (`%TEMP%` es por usuario) |
| Cruza a **WSL2** | no | **no** (§3) |
| Funciona en **POSIX** | no existe | sí (`fcntl.flock`) |
| Deja ver **quién lo tiene** | **no** — no hay API de dueño, MEDIDO | sí (`pid`, epoch, qué) |
| Lo suelta el sistema al morir el dueño | **sí** (`WAIT_ABANDONED`, 9,7 µs) | sí (551,9 µs, N-b) |
| Coste | **18,1 µs** | ~950 µs |

Ninguno de los dos cubre al otro. Y hay un tercer motivo que no es técnico sino
de despliegue: **el candado de fichero es lo que ya está desplegado**. Un
`filex` con solo el mutex y otro con solo el fichero **no se verían**. Por 18,1
µs, se toman los dos.

---

## 2. b1 — que «de máquina» sea verdad

### 2.1 La sonda que refuta el pendiente — **MEDIDO** (`logs/sonda_maquina.log`)

Primero, quién sondea, porque el resultado no vale nada sin esto:

```
usuario = DESKTOP-P9A9UP0\krato      elevado = False
Etiqueta obligatoria\Nivel obligatorio MEDIO
BUILTIN\Administradores        -> Grupo usado solo para denegar
NT AUTHORITY\Cuenta local y miembro del grupo de administradores -> solo para denegar
whoami /priv -> SeChangeNotifyPrivilege  (y ninguno más)
```

**No hay `SeCreateGlobalPrivilege` en el token, ni elevación, ni administrador
efectivo.** Y aun así:

```
== 1. Local\ frente a Global\ ==
  Local\         creado=True  GetLastError=0
  Global\        creado=True  GetLastError=0
== 2. exclusion entre DOS PROCESOS ==
  hijo dice: {'tomado': True, 'wait': 0, 'pid': 27292}
  el padre espera con timeout 0 -> 0x102 (WAIT_TIMEOUT: EXCLUYE) en 25.6 us
== 3. dueno muerto por taskkill /F ==
  taskkill rc=0; el siguiente espera -> 0x80 (WAIT_ABANDONED: el SISTEMA lo suelta) en 9.7 us
== 5. coste ==
  mutex crear+wait+release+close: mediana 7.0 us  p90 7.5 us
```

La fila 3 es la que decide, igual que decidió para N-b: **`WAIT_ABANDONED`
significa que el dueño murió sin soltarlo y el sistema nos lo entrega**. No hay
que escribir recuperación de huérfanos, ni preguntar por un PID —trampa 31—, ni
esperar 900 s. Es la misma virtud que el candado de rango de bytes, por otro
mecanismo.

**No sé por qué funciona sin el privilegio, y lo digo:** la doctrina dice que
`Global\` lo exige. Lo que sé es lo que he medido en esta máquina. Por eso el
código **degrada con aviso** si algún día falla en otra, y nunca en silencio
(trampa 13).

### 2.2 «Que funcione» no es «que esté ahí» — **MEDIDO** (`logs/sonda_namespace.log`)

Un handle no prueba dónde vive el objeto, y creerse el handle es exactamente el
error de la trampa 13 (`get_device()` diciendo `'GPU'` desde la CPU). Dos
comprobaciones independientes:

```
== A. Local\S y Global\S VIVOS A LA VEZ ==
  Local\  handle=True err=0
  Global\ handle=True err=0 (objeto NUEVO)      <- no ERROR_ALREADY_EXISTS
  -> son objetos DISTINTOS: True
== B2. abrirlo por ruta absoluta del namespace ==
  \BaseNamedObjects\filex-ns-32812              -> ABRE      NTSTATUS=0x00000000
  \Sessions\1\BaseNamedObjects\filex-ns-32812   -> ABRE      NTSTATUS=0x00000000
  \BaseNamedObjects\filex-ns-32812-NO-EXISTE    -> no abre   NTSTATUS=0xc0000034
```

La segunda fila de B2 no es contradicción: es que **`Local\` y `Global\` se
crearon con el mismo sello**, así que hay un objeto en cada directorio — que es
justo lo que A dice. Y la tercera fila es el control negativo que hace que la
primera signifique algo.

*(La **enumeración** de `\BaseNamedObjects` falló y se deja como falló: primer
intento, 0 objetos y ningún error, por no declarar `argtypes` —`BOOLEAN` de NT
es de un byte—; segundo, `NTSTATUS=0x00000105`. **Dos intentos y parar.** El
veredicto no la necesita.)*

### 2.3 La trampa dentro de la vía buena: el DACL — **MEDIDO** (`logs/sonda_dacl.log`)

Aquí es donde esto se habría publicado mal. El mutex `Global\` con descriptor
**por defecto**:

```
D:(A;;0x1f0001;;;S-1-5-21-…-1001)(A;;0x1f0001;;;BA)(A;;0x1f0001;;;SY)
  -> lo puede abrir CUALQUIER usuario (WD/BU en la DACL): False
```

**El creador, los administradores y el sistema. «Everyone» no está.** Un mutex
así es de máquina en el nombre y de usuario en el acceso: el segundo usuario
recibiría `ERROR_ACCESS_DENIED` al crearlo. Y esta máquina **no lo habría
notado nunca**, porque todos los agentes corren como `krato` — es la trampa de
la semilla (`CLAUDE.md` §3) con otra cara: *cuando midas una propiedad de la
solución, varía el actor; si no, estás midiendo tu actor*.

Con descriptor explícito `D:(A;;0x1F0001;;;WD)` sale lo que hacía falta, y se
crea sin error:

```
creado=True err=0
SDDL: …D:(A;;0x1f0001;;;WD)
```

**Y el corolario va en el código, no en el informe:** `ERROR_ACCESS_DENIED` al
crear el mutex se trata como **ocupado**, no como «no disponible». Si existe un
objeto con ese nombre al que no tenemos acceso, es que **lo tiene otro**.
Degradar ahí sería abrir el agujero exactamente donde el mutex hace falta.
Negarse cuesta un reintento; es la misma elección que hicieron N-b con la
detección y L1 con `GPU_GUARD=abortar`.

### 2.4 La prueba de que esto cierra b1

`test_dos_directorios_de_candados_distintos_siguen_excluyendose`. **Dos procesos
con `FILEX_CERROJO_DIR` distinto es la simulación honesta de dos usuarios de
Windows**, porque lo que hace que `%TEMP%` no sea de máquina es precisamente que
cada usuario tiene el suyo. Con `FILEX_CERROJO_MUTEX=0` —es decir, con el
cerrojo de N-b exactamente— falla:

```
FAILED CerrojoDeMaquina::test_dos_directorios_de_candados_distintos_siguen_excluyendose
E  AssertionError: True is not false : DOS DUEÑOS: el candado sigue siendo de
   usuario, no de maquina — el segundo entro con otro directorio de candados
1 failed, 10 passed
```

---

## 3. WSL2: no se cierra, y el motivo que se daba era falso — **MEDIDO**

Era el límite 2 de `cerrojo-de-maquina.md` §6 y el aviso de `lock-de-maquina.md`,
y estaba **deducido**: *«el `/tmp` de Ubuntu es otro sistema de ficheros»*. La
deducción no aguanta el primer vistazo, porque **el `%TEMP%` de Windows se ve
desde WSL2**:

```
C:\ on /mnt/c type 9p (rw,…,aname=drvfs;path=C:\;…)
ve %TEMP%: si
```

Así que la pregunta no era si el fichero se ve —se ve, es el mismo—, sino si el
**candado** sobre él se respeta a través del puente (`logs/sonda_wsl.log`):

| Escena | Resultado |
|---|---|
| 1. Windows toma `msvcrt.locking` → WSL2 intenta `flock` | **`TOMADO`** — no excluye |
| 2. WSL2 toma `flock` → Windows intenta `msvcrt.locking` | **lo toma igual** — no excluye |
| 3. **Control:** WSL2 toma `flock` → **otro proceso de WSL2** intenta | **`BLOQUEADO 11 Resource temporarily unavailable`** |

**La escena 3 es la que hace concluyente a las otras dos.** Sin ella, «no
excluye» podría querer decir que `flock` no funciona sobre 9p en absoluto, que
es una explicación distinta con otra consecuencia. Funciona: **lo que no cruza
el puente es el candado, no el fichero.**

El mutex tampoco cruza: WSL2 es una VM y no comparte el namespace de objetos del
kernel de Windows. **PENDIENTE, y ahora con mecanismo identificado.** Lo que sí
cruzaría es algo que no viva en el sistema de ficheros ni en el kernel de
Windows —un puerto o un servicio—, y eso ya no es «una mudanza».

---

## 4. b4 — el enlace que daba dos dueños

### 4.1 Reproducido, con los tres alias que Windows da — **MEDIDO** (`logs/sonda_enlaces.log`)

```
real : …\filex-enlaces-6knq2hxi\real\salida.webp
ident: (1105906800, 211387707509988680)

-- enlace duro (mklink /H)
   MISMA CLAVE (lexica) : False      MISMA IDENTIDAD NTFS : True
   reserva real=True alias=True  -> DOS DUENOS: True
-- enlace simbolico (mklink)
   MISMA CLAVE (lexica) : False      MISMA IDENTIDAD NTFS : True
   reserva real=True alias=True  -> DOS DUENOS: True
-- union de directorio (mklink /J)
   MISMA CLAVE (lexica) : True       MISMA IDENTIDAD NTFS : True
   reserva real=True alias=False -> DOS DUENOS: False
```

Dos cosas que no esperaba:

- **El enlace simbólico se pudo crear sin elevar** en esta máquina (modo
  desarrollador). Lo tenía apuntado como «puede que no se pueda, y eso también
  sería un resultado»; se pudo.
- **La unión de directorio ya estaba cerrada** por el `realpath` del directorio
  de N-b. Su arreglo hace más de lo que él le atribuyó: no solo el nombre corto
  8.3.

### 4.2 Por qué `realpath` de la ruta entera **no** era la respuesta

Es la solución que el propio informe de N-b señalaba como «más fuerte», y **no
habría cerrado el caso principal**: un **enlace duro no tiene destino que
resolver**. Los dos nombres son entradas de directorio igual de reales sobre el
mismo registro MFT, y `realpath` devuelve cada uno tal cual. Lo único que los
iguala es el **identificador de fichero de NTFS**, que `os.stat` ya trae:
`st_dev` + `st_ino` **coincidieron en los tres alias**, incluido el duro.

### 4.3 El cierre, y el riesgo que N-b tenía razón en temer

N-b no resolvió la ruta entera por un motivo bueno y explícito: *«el destino
puede no existir al reservar y sí existir al soltar, y una clave que se mueve
entre las dos llamadas deja el candado tomado para siempre»*. **Ese riesgo es
real y la identidad NTFS lo tiene entero**, porque solo existe cuando existe el
fichero — o sea, aparece **exactamente** entre el `reservar` y el `soltar` de
una conversión que funciona.

Se cierra sin renunciar a nada: **se guarda lo que se reservó en vez de volver a
deducirlo.** La reserva anota sus claves en `_RESERVAS` bajo la clave léxica
—que sí es estable— y `_soltar_destino` suelta **esas**, no las que salgan de
mirar otra vez el disco. Con eso la clave de identidad puede aparecer, cambiar o
desaparecer sin consecuencias.

La prueba que fija esa regresión es
`test_un_destino_que_nace_entre_reservar_y_soltar_se_suelta_igual`: reservar un
destino que no existe, **crearlo** —que es lo que hace el motor—, soltar, y
volver a reservar. Con un `soltar` que recalculase, la segunda reserva fallaría
para siempre.

**Y hay una segunda vuelta atrás que hace falta y no es obvia:** ahora se toman
**dos** candados, así que un rechazo por el segundo tiene que soltar el primero.
Sin eso, un choque por identidad dejaría la clave léxica bloqueada hasta que
muriese el proceso.

### 4.4 Lo que b4 sigue sin cubrir

Un **enlace colgante** —un símbolico a un fichero que aún no existe— no tiene
identidad que consultar, así que dos conversiones, una al enlace y otra al
destino inexistente, siguen dando dos claves. Es un caso más raro todavía que el
que cierro. **PENDIENTE, declarado.**

---

## 5. Lo que cuesta — **MEDIDO**, n = 20 000 por celda, todo en la MISMA tanda

`coste_cerrojo_unico.py` → `coste.json`, `logs/coste_cerrojo_unico.log`.
**Testigos:** deriva monohilo **0,93**; testigo de proceso **32,4 → 37,3 ms**,
sin agotar el tope de 20 s → **`limpia`**. *(Con la sesión remota activa y con
el agente Q trabajando: el testigo no ve contención en esta tanda.)*

| Configuración de `reservar+soltar` | mediana | p90 |
|---|---:|---:|
| **`maquina` (mutex + identidad) — LO NUEVO** | **1 113,3 µs** | 1 486,9 |
| `maquina` **sin mutex** = el cerrojo de N-b | 1 049,4 µs | 1 385,2 |
| `maquina` **sin identidad** | 1 039,0 µs | 1 333,0 |
| `proceso` (el hito 7) | 353,4 µs | 492,7 |
| `ninguno` | 361,7 µs | 491,7 |

| Trozo, medido aislado | mediana |
|---|---:|
| **el mutex `Global\` entero** (crear + wait + release + close) | **18,1 µs** |
| clave léxica (`realpath` del directorio, de N-b) | 153,5 µs |
| **identidad NTFS, destino que NO existe** (el caso normal) | **23,6 µs** |
| identidad NTFS, destino que sí existe | 35,2 µs |
| detección, destino que no existe (el caso normal) | 28,2 µs |
| detección, destino que sí existe | 179,2 µs |
| **conversión `png→webp` completa** (n=11) | **367,0 ms** |

**Total por conversión** = reserva (1 113,3) + 2 detecciones (2 × 28,2) =
**1 169,7 µs**, el **0,319 %** de una conversión de la misma tanda.
**Lo que añade esta ronda: 18,1 + 23,6 = 41,7 µs, el 0,011 %.**

### 5.1 La salvedad obligatoria contra los 976,6 µs de N-b

**No son comparables y no los comparo.** N-b midió en otra tanda, otro día, con
otros agentes en la máquina; `CLAUDE.md` §3 lo dice sin ambigüedad. Lo que sí es
comparable es la columna «sin mutex» de **mi** tabla, que es su código medido
aquí dentro: **1 049,4 µs**.

### 5.2 Y una autocorrección: el coste añadido **no se puede ver por diferencia**

Esta es la parte que casi publico mal. Las tres tandas del mismo arnés dieron:

| | tanda 1 | tanda 2 | tanda 3 |
|---|---:|---:|---:|
| **LO NUEVO** | 1 053,5 | **978,3** | 1 113,3 |
| **sin mutex** (N-b) | 1 094,9 | 1 038,0 | **1 049,4** |
| ¿el nuevo es más caro? | **no (−41)** | **no (−60)** | sí (+64) |

**En dos de las tres tandas lo nuevo sale MÁS BARATO que lo viejo, y eso es
imposible**: hace todo lo que hacía el viejo y además dos cosas. Lo que dice la
tabla no es que el mutex sea gratis: dice que **el ruido entre configuraciones
de la misma tanda (±70 µs) es mayor que lo que se quiere medir (41,7 µs)**.

**Por eso el coste se publica pieza a pieza y no por diferencia.** Es la trampa
de medición del proyecto —«las relativas dentro de una tanda, sí»— llevada un
paso más allá: **dentro de una tanda también hay un suelo, y por debajo de él
una diferencia no es una medida.** Si hubiera publicado la tanda 2 tendría un
titular precioso y falso: *«la exclusión de máquina sale gratis y encima paga»*.

---

## 6. Lo que este cerrojo **NO** cubre

Los límites 3 a 7 de `cerrojo-de-maquina.md` §6 **siguen en pie tal cual** (la
ventana entre detección y `move`; POSIX sin detección y sin barrido; que no
protege el fichero después de escrito). A ellos:

1. **WSL2 sigue abierto**, ahora con mecanismo medido (§3): ninguno de los dos
   primitivos cruza, y no es por el sistema de ficheros. **PENDIENTE.**
2. **Dos usuarios de Windows no se han probado ENTRE SÍ.** Esta máquina tiene un
   usuario. Lo que está medido es que el objeto vive en `\BaseNamedObjects`, que
   su DACL admite a `WD` y que **dos directorios de candados distintos ya no se
   escapan**, que es el mecanismo exacto por el que fallaba. **Que un segundo
   usuario real lo respete es PENDIENTE**, y no lo llamo medido.
3. **Un enlace COLGANTE sigue dando dos claves** (§4.4).
4. **El mutex no dice quién lo tiene** — MEDIDO: no hay API de dueño, solo
   `OpenMutexW`, que dice si existe. Los metadatos siguen viniendo del fichero,
   así que **si algún día se quitara el candado de fichero se perdería media
   trampa 31**.
5. **La detección sigue sin distinguir un LECTOR de un ESCRITOR** (§5.1 de N-b).
   No la he tocado.
6. **El lock de GPU sigue sin usar esto.** La API ya tiene `espera` para él,
   pero **`bench/lib/harness.sh` es de L1 y no lo toco**, y además su lock es un
   `noclobber` sobre un fichero de texto: **es incompatible con un candado de
   rango de bytes**, así que conectarlos exige cambiar el `harness.sh` para que
   los `.sh` y los `.py` usen el mismo primitivo. **PENDIENTE, y no es una
   mudanza: es un cambio en código compartido por 47 ficheros.**
7. **La cancelación entre procesos tampoco está conectada.** La API la
   contempla (`esta_libre`, `dueno`); nada más.

---

## 7. Que el 99 % no se rompe — **MEDIDO**

| Comprobación | Resultado |
|---|---|
| **La suite entera, antes** | `175 passed, 6 skipped, **1 failed**` (75,54 s) |
| **La suite entera, después** | `186 passed, 6 skipped, **1 failed**` (75,65 s) |
| El rojo | **el mismo**, `test_sondeo.py::SelladoDelDisco::test_ningun_motor_disponible_tiene_el_sondeo_caducado`, con **la misma lista de cinco motores por el componente `invocacion`** — que es de N-a, no mío |
| Movimientos en las 175 anteriores | **cero** |
| `test_cerrojo.py` (11, de N-b) + `test_hito7.py` (42) | **53 passed** tras la mudanza |
| La huella del sondeo | **no caducó ninguna arista nueva**: los caducados siguen siendo los cinco de `invocacion` |
| R21 | desechables listados antes y después en los dos arneses que crean ficheros; `git status` no muestra un solo fichero suelto en la raíz |

**No he roto ninguna prueba de un fichero que no sea mío.**

---

## 8. Las pruebas, y cuál falla sin qué

`pruebas/test_cerrojo_unico.py`, **11 pruebas, 1,7 s**. Fichero nuevo y no
tocado el de N-b, para que la integración vea un diff aditivo.

| Clase | Qué cierra |
|---|---|
| `CerrojoDeMaquina` | b1: dos directorios de candados distintos, dueño muerto, metadatos, y el tope de `espera` |
| `EnlaceComoDestino` | b4: enlace duro en un proceso y **entre procesos**, y la regresión del destino que nace entre reservar y soltar |
| `ApiDelModulo` | que `cerrojo` no dependa de `filex`, el gestor de contexto, y la reentrada |

**Que fallan por el fallo que dicen cubrir**, en la misma tanda y sin tocar
`git` — el mismo truco del `FILEX_CERROJO_DESTINO` de N-b:

```
FILEX_CERROJO_MUTEX=0      -> 1 failed, 10 passed   (b1)
FILEX_CERROJO_IDENTIDAD=0  -> 2 failed,  9 passed   (b4, las dos)
sin ninguna de las dos     -> 11 passed
```

---

## 9. Propuestas para `CLAUDE.md` — **NO APLICADAS**

La última trampa aplicada es la **32**; N-b propuso la **33** y la **34**, que
sigo suponiendo pendientes de aplicar. Estas serían la **35** y la **36**.

> **35. Un handle no prueba dónde vive el objeto, y el permiso que falta puede estar en el DESCRIPTOR y no en el privilegio — MEDIDO** (`bench/cerrojo-unico.md` §2). Un mutex con nombre en `Global\` **se crea en esta máquina desde un token de integridad media, con `BUILTIN\Administradores` marcado «solo para denegar» y con `SeChangeNotifyPrivilege` como único privilegio**, lo que **refuta** que haga falta `SeCreateGlobalPrivilege` para tenerlo. Se verificó donde vive, no se dedujo: `NtOpenMutant` sobre `\BaseNamedObjects\<sello>` abre con `NTSTATUS=0` y un nombre inventado da `0xC0000034`. **Y la trampa de verdad está dentro de la vía buena:** con descriptor **por defecto** la DACL es `(el usuario)(BA)(SY)` y **«Everyone» no está**, así que el objeto es global en el NOMBRE y de usuario en el ACCESO — otro usuario recibiría `ERROR_ACCESS_DENIED`, que un código con prisa llama «no hay infraestructura» y **degrada justo en el caso que el mutex venía a cubrir**. Se crea con SDDL explícito (`D:(A;;0x1F0001;;;WD)`) y **`ACCESS_DENIED` se trata como OCUPADO, nunca como degradación**. Cuesta **18,1 µs**. Corolario general: **cuando midas una propiedad de una solución, varía el ACTOR; si no, estás midiendo tu actor** — con un solo usuario en la máquina, el DACL malo habría pasado inadvertido para siempre.

> **36. Dentro de una tanda también hay un suelo, y por debajo de él una diferencia no es una medida — MEDIDO** (ídem §5.2). El proyecto ya sabe que *«las cifras absolutas de tandas distintas no son comparables; las relativas dentro de una tanda, sí»*. **La segunda mitad tiene un límite:** midiendo `reservar+soltar` con y sin una mitad que aisladamente cuesta **41,7 µs**, **en 2 de 3 tandas la versión que hace MÁS trabajo salió MÁS BARATA** (−41 y −60 µs), porque el ruido entre configuraciones de la misma tanda es de **±70 µs**. Publicar la diferencia habría dado el titular *«la exclusión de máquina sale gratis y encima paga»*, que es falso. **Mide el trozo aislado, no la diferencia entre dos totales que lo contienen** — y si solo puedes medir por diferencia, **repite la tanda y mira si el signo se conserva**. Aquí no se conservaba. Y un tercer aviso del mismo sitio: **una explicación plausible no es un mecanismo.** *«El candado no cruza a WSL2 porque el `/tmp` de Ubuntu es otro sistema de ficheros»* era falso —el `%TEMP%` de Windows **se ve** desde `/mnt/c` y es el mismo fichero—; lo que no cruza es el candado, y hace falta un **control positivo** (dos procesos de WSL2 sí se excluyen entre ellos sobre ese mismo fichero) para que un «no excluye» signifique algo.

**Y un cambio en la trampa 26 y en el §1**, que han vuelto a quedarse cortos:
donde N-b propuso *«sigue siendo de usuario, no de máquina»*, ahora es **de
máquina y de usuario en Windows (mutex `Global\` con DACL explícita), y sigue
sin cruzar a WSL2 — lo que no cruza es el candado, no el fichero**.

---

## 10. Lo que abre este informe

| # | Pendiente | Dónde |
|---|---|---|
| 1 | **WSL2.** Ninguno de los dos primitivos cruza, y ya se sabe por qué. Lo que cruzaría no vive en el sistema de ficheros | §3 |
| 2 | **Dos usuarios de Windows reales**, que aquí no hay | §6.2 |
| 3 | **Conectar el lock de GPU (C38)**: la API ya tiene `espera`, pero exige tocar `bench/lib/harness.sh`, que es de L1 y lo usan 47 ficheros — y su `noclobber` es incompatible con un candado de rango de bytes | §6.6 |
| 4 | **Conectar la cancelación entre procesos** a `esta_libre`/`dueno` | §6.7 |
| 5 | **Un enlace COLGANTE** sigue dando dos claves | §4.4 |
| 6 | **La ventana entre la detección y el `move`** (b2 de N-b): no se abrió, por orden de prioridad | — |

---

## 11. Ficheros

| Fichero | Qué es |
|---|---|
| `filex/cerrojo.py` | El primitivo, mudado y ampliado. Los dos mecanismos y la API de los tres consumidores |
| `filex/nucleo.py` | +96 / −119: delega en `cerrojo`, y añade `_identidad_destino`, `_claves_destino` y `_RESERVAS` |
| `pruebas/test_cerrojo_unico.py` | 11 pruebas, las de proceso con `subprocess` |
| `bench/salidas-cerrojo-unico/` | Las cinco sondas, el arnés de coste, sus `.json` y sus logs |
| `bench/salidas-cerrojo-unico/MANIFIESTO.md` | Cómo se reproduce todo, incluida la sonda que falló |
