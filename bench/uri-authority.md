# N37 — la *authority* de un `file://`: no se perdía, se sustituía

**worker7 · carril CPU · ronda 17 · 04/09/2026 · rama `cpu/uri-authority`**

> **Decisión: se RECHAZA un URI con *authority* de red, no se traduce a UNC.**
> Las dos políticas cierran exactamente las mismas fugas y no rompen ninguna
> raíz legítima —empatan en la tabla de candidatos, 4 y 4—, así que la decisión
> no la puede tomar la detección: la toma el precio. Y el precio de admitir UNC
> está medido y es una regresión conocida — **el cerrojo de destinos da DOS
> DUEÑOS del mismo fichero cuando el destino todavía no existe**, que es el caso
> normal de un conversor y es la trampa 26 por un alias nuevo.
>
> Con una excepción que **no** es una concesión: `localhost`, que RFC 8089 §2
> declara equivalente a la *authority* vacía. Rechazarla también —el candidato
> «severo»— rompía **2 de las 4 raíces legítimas** de la tabla. Es la trampa 51:
> el umbral más duro no es el más seguro.

---

## 0. Qué se pedía y qué se entrega

| | |
|---|---|
| **Fila** | N37 (más los dos pendientes que worker5 dejó escritos en `bench/raices-mixtas.md` y nadie había registrado) |
| **Entrega** | La decisión con número detrás, el arreglo, y la demostración de que **no se deshizo N34 ni N35** |
| **Ficheros propios** | `filex/mcp.py`, `pruebas/test_hito4.py` |
| **Ficheros ajenos tocados** | **`filex/confinamiento.py`** — declarado en §5.1, es de la ronda de ayer |
| **Salidas** | `bench/salidas-uri-authority/` con su `MANIFIESTO.md` |

---

## 1. La fuga, reproducida y con sus RAMAS — MEDIDO

`_uri_a_ruta` hacía `urlparse(uri)` y usaba **sólo `p.path`**. `p.netloc` —la
*authority*— se tiraba al suelo sin mirarlo.

Lo que eso produce no es «se pierde la raíz». Es peor, y es lo que hace a esta
fila distinta de las dos anteriores de la misma familia: **la raíz se
SUSTITUYE por otra**, porque `os.path.abspath` completa una ruta sin unidad con
la unidad del proceso.

`sonda_uri.py` enumera **las tres ramas** del predicado y prueba un caso de cada
una (trampa 118, que nació justo al lado: worker5 desmontó una rama de un `or`
y publicó una conclusión falsa sobre la rama que no probó). Sobre el código de
`2498f4b` (`sonda_uri_antes.json`):

| URI declarado por el cliente | Rama | Raíz efectiva que sale | ¿Confina? |
|---|---|---|---|
| `file:///D:/Work/research/FileX` | R2 letra-unidad | `d:\work\research\filex` | sí, correcto |
| `file://servidor/recurso` | R3 sin-letra | **`d:\recurso`** | **sí — nadie la declaró** |
| `file://servidor/recurso/sub` | R3 sin-letra | **`d:\recurso\sub`** | **sí** |
| `file://///servidor/recurso` | R3 sin-letra | `\\\servidor\recurso` | sí, y no es ni UNC válida |
| `file:///recurso` | R3 sin-letra | **`d:\recurso`** | **sí** |
| `file://` | R3 sin-letra | **el `cwd` del servidor** | **sí** |
| `file:///` | R3 sin-letra | `d:\` | no: N35 la poda |
| `http://…`, `""` | R1 no-file | — | se ignora |

### 1.0 Y una TERCERA puerta al mismo `cwd`, que encontró enumerar las ramas *después* del arreglo

Con el rechazo de la *authority* ya escrito y sus pruebas en verde, volví a
pasar la lista de ramas — y apareció un residuo que ninguna de las dos primeras
vueltas había tocado:

```
file:///D:  ->  'D:'   ->  abspath = D:\Work\research\FileX\.claude\worktrees\agent-…
file:///C:  ->  'C:'   ->  abspath = C:\
```

**Tener unidad no es ser absoluta.** `D:` es en Windows una ruta *relativa a la
unidad*, y `abspath` la completa con **el directorio actual de esa unidad**. Mi
primera guarda (`splitdrive(ruta)[0].endswith(":")`) la aceptaba porque unidad
tiene. El caso hermano es el que lo deja claro: `file:///C:` daba `C:\` **sólo
porque el directorio actual de `C:` era su raíz**, es decir, el confinamiento
dependía de un estado del proceso que nadie había declarado.

Se cierra con `os.path.isabs`, que es lo que separa `D:` de `D:\`. Lo anoto con
su orden porque la lección es de método y no de código: **la enumeración de
ramas hay que repetirla DESPUÉS del arreglo**, porque el arreglo cambia las
ramas. Es la trampa 118 aplicada a mi propio trabajo, y es el tercer sitio
distinto por el que se llegaba al mismo `cwd` —`file://`, la raíz `""` y
`file:///D:`— cada uno por un mecanismo diferente.

### 1.1 El caso caro, con rutas que existen

No es un ejemplo de laboratorio. Un cliente que declare la raíz UNC de un NAS:

```
URI declarado : file://nas-de-la-empresa/Work
_uri_a_ruta   : '\Work'
raíz efectiva : ['d:\work']
   puede_leer(D:/Work/research/FileX/CLAUDE.md) = True
   puede_leer(D:/Work/research/ASR)             = True   <- otro proyecto
   puede_leer(D:/Work)                          = True
```

El cliente pidió un recurso de red y obtuvo **`D:\Work` entero**, con el árbol
de investigación de otro proyecto dentro.

### 1.2 Y la *authority* no era decorativa: dos URI distintos daban la misma raíz

```
file://servidor/recurso -> ['d:\recurso']
file:///recurso         -> ['d:\recurso']
IDÉNTICAS: True
```

Dos URI que denotan cosas distintas —un recurso remoto y una ruta local—
colapsaban en el mismo confinamiento. Ésa es la prueba directa de que el campo
descartado llevaba información.

### 1.3 La fuga no está acotada por el servidor

`Raices._interseca` empieza con `if not servidor: return list(cliente)`. Es
decir: **sin `--raiz`, las raíces del cliente pasan enteras**, sin intersección
que las recorte. El caso por defecto es el que menos protección tiene.

---

## 2. Qué emiten los clientes DE VERDAD — MEDIDO, no deducido

`CLAUDE.md` §5: *sondear capacidades en ejecución, no deducirlas*. La decisión
depende de si la forma con *authority* es una rareza o el camino normal.

### 2.1 El cliente real

`srv_sonda_roots.py` —copia adaptada del arnés de worker4, como manda §1— pide
`roots/list` (que es una petición **servidor → cliente**) y registra la
respuesta literal. Contra **Claude Code 2.1.260**, protocolo `2025-11-25`:

```
capacidades del cliente : {"roots": {"listChanged": true}, "elicitation": {}}
respuesta a roots/list  : file:///D:/Work/research/FileX/.claude/.../salidas-uri-authority
```

**Authority vacía y forma canónica.** El caso normal del cliente que este
proyecto usa **no se ve afectado por ninguna de las políticas candidatas**, y
eso es dato: quita de la mesa el argumento de «rechazar rompería a los
clientes».

### 2.2 Los productores, en los dos runtimes que importan

Lo que no pude observar es a Claude Code con un `cwd` UNC (no hay recurso UNC
montado como raíz de sesión). Lo que sí se puede medir es **el productor que ese
cliente usa por dentro**, y el del otro tipo de cliente:

| Runtime | Ruta de entrada | URI emitido | *authority* |
|---|---|---|---|
| Node 22.23.2 `pathToFileURL` | `\\servidor\recurso` | `file://servidor/recurso` | `servidor` |
| Node 22.23.2 `pathToFileURL` | `D:\Work\research\FileX` | `file:///D:/Work/research/FileX` | *(vacía)* |
| Python 3.11 `Path.as_uri()` | `\\servidor\recurso` | `file://servidor/recurso/` | `servidor` |
| Python 3.11 `Path.as_uri()` | `D:\Work\research\FileX` | `file:///D:/Work/research/FileX` | *(vacía)* |

**Los dos productores reales emiten exactamente la forma que FileX traducía
mal.** No es un caso rebuscado: es lo que sale por defecto de una ruta UNC, y es
lo que RFC 8089 da por canónico.

### 2.3 Un hallazgo que decide la excepción: los dos runtimes DISCREPAN en `localhost`

| | `new URL("file://localhost/D:/Work").host` | `urlparse(...).netloc` |
|---|---|---|
| Node | `""` — lo normaliza él solo | — |
| Python | — | `"localhost"` |

Node aplica el WHATWG URL Standard y borra `localhost`; Python lo entrega tal
cual. **Sin una excepción explícita, el mismo root legítimo funcionaría desde un
cliente Node y fallaría desde uno Python.** Eso no se puede deducir de la norma:
hay que ejecutar los dos.

### 2.4 El consumidor de referencia es más estricto que FileX

`fileURLToPath` de Node, sobre las formas que FileX aceptaba:

| URI | Node | FileX (antes) |
|---|---|---|
| `file:///recurso` | **error**: `File URL path must be absolute` | `D:\recurso` |
| `file://` | **error** | el `cwd` |
| `file:///` | **error** | `D:\` |
| `file://servidor/recurso` | `\\servidor\recurso` (UNC de verdad) | `D:\recurso` |

Las tres que Node rechaza, FileX las convertía en rutas locales inventadas. En
la cuarta, Node hace lo correcto y FileX hacía lo peligroso.

---

## 3. La tabla de candidatos — trampa 51

*Antes de elegir, tabula qué atrapa y qué rompe cada valor candidato.*
`tabla_candidatos.py` implementa los cuatro como funciones puras y los evalúa
contra la **misma** batería, midiendo **qué concede** cada raíz resultante y no
sólo qué cadena sale (trampa 70).

| Candidato | Fugas atrapadas | Legítimas intactas | Legítimas rotas |
|---|---|---|---|
| **C1 ignorar la authority (HOY)** | 1 de 4 | 4 de 4 | 0 |
| **C2 rechazar TODA authority** | 3 de 4 | 2 de 4 | **2** |
| **C3 rechazar salvo `localhost`** | **4 de 4** | **4 de 4** | **0** |
| **C4 traducir a UNC** | **4 de 4** | **4 de 4** | **0** |

- **C2 es el candidato «severo», y es una regresión con mejor pinta.** Rompe
  `file://localhost/D:/Work` y `file://LOCALHOST/D:/Work`, que RFC 8089 §2
  declara idénticos a `file:///D:/Work`. Es literalmente el enunciado de la
  trampa 51.
- **C3 y C4 empatan.** Ninguna detección los separa. Por eso la decisión tiene
  que salir de otro sitio, y ese sitio es §4.

---

## 4. Por qué se RECHAZA y no se traduce a UNC — el número que decide

Aquí no vale «UNC no está medido, así que no». **Sí se podía medir**:
`sonda_unc.json` encuentra recurso UNC accesible en esta máquina
(`\\localhost\D$`, 48 entradas), así que C4 se sondeó de verdad.

### 4.1 C4 funciona — y eso no basta

`sonda_c4_unc.json`, con la raíz `\\localhost\D$\Work\research\FileX`:

```
construye              : True      lectura: ['\\localhost\d$\work\research\filex']
resolver (dentro)      : OK
resolver (fuera)       : Denegado: ruta no accesible
```

Confina, concede dentro y deniega fuera. Si la pregunta fuese «¿se puede?», la
respuesta sería que sí.

### 4.2 Pero el alias NO se colapsa, y eso el proyecto ya lo ha pagado

```
realpath de la UNC     : \\localhost\D$\Work\research\FileX
realpath de la LOCAL   : D:\Work\research\FileX
realpath las iguala    : False
mismo objeto NTFS      : True   (st_dev=553714096, st_ino=10414574138295902)
```

**Mismo objeto, dos nombres, y `realpath` no los junta.** Es la trampa 33 sobre
otro recurso —allí era el nombre corto 8.3, y daba *dos dueños del mismo
fichero*—. Consecuencia inmediata, medida: una raíz local **deniega** la forma
UNC del mismo fichero y una raíz UNC **deniega** la local; `_interseca` devuelve
`[]` en las dos direcciones.

### 4.3 Y donde muerde es en el cerrojo, en el caso NORMAL

`filex/nucleo.py::_clave_destino` **ya nombra la UNC** en su docstring, entre
los alias que la clave léxica no cierra, y su defensa —`_identidad_destino`, con
`st_dev`+`st_ino`— lleva escrita al lado la condición que la limita: *«sólo se
puede consultar si el fichero EXISTE… en el caso normal el destino todavía no
está»*.

`sonda_alias_destino.json`, **con control positivo**:

| Situación | Claves léxicas | Clave de identidad | Claves compartidas |
|---|---|---|---|
| **Destino que NO existe** (caso normal) | distintas | `null` en las dos | **0 → DOS DUEÑOS** |
| Destino que SÍ existe *(control)* | distintas | **idénticas** (`id:553714096:1970324837519158`) | 1 |

El control positivo es lo que hace útil la fila de arriba: sin él, un «no
coinciden» no distingue *el alias no se cierra* de *la sonda no mira lo que
cree*.

**Por eso se rechaza.** Admitir raíces UNC exige cerrar antes esa mitad del
cerrojo — es otra fila, no un efecto colateral de ésta. Y como C3 y C4 empatan
en detección, **C4 no compra nada a cambio de esa deuda**.

### 4.4 Y rechazar es monótono

`_dentro` es un OR sobre las raíces. Descartar un URI sólo puede **quitar** un
término, nunca conceder. Es el mismo argumento estructural (a) con el que N35
sostuvo su poda, y vale igual aquí.

---

## 5. Los otros dos pendientes de worker5

### 5.1 La raíz `""` confinaba en el `cwd` — CERRADO *(y toca fichero ajeno)*

```
Confinamiento(['']) -> lectura = ['d:\work\research\filex\.claude\worktrees\agent-a146f8a533c52cb89']
   concede el cwd: True
```

Es **la misma familia que N37**: `abspath("")` convierte «nada» en «aquí», así
que lo declarado y lo efectivo dejan de coincidir. Y llega por la CLI, que pasa
`--raiz` tal cual: una variable de entorno vacía en un script basta.

> **Declaración obligada:** el arreglo va en **`filex/confinamiento.py`**, que es
> de la ronda de ayer y no es mi fichero. Son dos añadidos, los dos aditivos:
> `_preparar` poda la raíz vacía —tres líneas, misma disciplina que N35— y se
> añade el método `_podadas`, que **no cambia ninguna decisión**: sólo dice qué
> se descartó. Ninguno toca `resolver`, `_dentro` ni `_lexico_ok`.

Separar «no declaré» de «declaré algo que no confina» es la trampa 43, y aquí
las dos acaban a propósito en el mismo sitio: `ValueError` de R6, sin acceso.

### 5.2 La poda de N35 era MUDA — CERRADO

N35 acertó al podar en vez de invalidar el conjunto, pero lo hace en silencio:
nadie se entera de qué raíces se cayeron. Y como R4 obliga a un mensaje opaco,
el operador ve la consecuencia (`ruta no accesible`) y nunca la causa. Es la
trampa 44 por omisión — el comportamiento es correcto y no hay dónde verlo.

Ahora se registra por el canal que ya existía (`FILEX_MCP_REGISTRO_ROOTS`), con
**las dos causas separadas**, que es la trampa 25: desde fuera se parecen.

```
…  root_descartado  motivo=uri_no_traducible  uri=file://servidor/recurso  pid=…
…  root_descartado  motivo=raiz_no_confina    raiz=C:\                     pid=…
```

Si nadie declara la variable, no se escribe nada y no cuesta nada. Y un
registrador que tumba el servidor no es un registrador: el `except OSError` es
el mismo criterio que ya usaba `invalidar()`.

---

## 6. El riesgo dominante: demostrar que N34 y N35 siguen VIVOS

Ésta es la tercera ronda seguida sobre la lista blanca. N34 cerró una fuga que
**abría de más**, N35 la que **cerraba de más**, y las dos vivían en el mismo
`except`. Que la suite pase no demuestra nada: lo que hay que demostrar es que
las pruebas de aquellos arreglos **siguen siendo discriminantes**.

`ab_discriminan.py` monta cada versión del código en una **copia** del árbol
—el árbol vivo no se toca (trampa 84)—, revierte con `git show <commit>:<fichero>`
—nunca con `git stash push`, que sobre un fichero ya commiteado devuelve 0 y no
hace nada (**trampa 119**, de ayer)— y **comprueba la identidad antes de creerse
una celda**.

### 6.1 Control de identidad: las versiones contrastan

| Fichero @ versión | `sha` actual | `sha` vieja | ¿Distintas? |
|---|---|---|---|
| `filex/mcp.py` @ antes_de_N37 (`2498f4b`) | `f493bbfadd50d81e` | `4b89ae49e2fd3c56` | sí |
| `filex/mcp.py` @ antes_de_N34 (`82cf1f3`) | `f493bbfadd50d81e` | `2f15c7b9f383014b` | sí |
| `filex/mcp.py` @ antes_de_N35 (`a4dc3f3`) | `f493bbfadd50d81e` | `471f4c06bfa18843` | sí |
| `filex/confinamiento.py` @ antes_de_N37 | `040364bcc3ee9024` | `42056ea259ccc2f1` | sí |
| `filex/confinamiento.py` @ antes_de_N35 | `040364bcc3ee9024` | `1a9e8fb20dc5262b` | sí |

Y **las tres versiones compilan** en todas las celdas (trampa 60: una prueba de
AST —o cualquier A/B— puede salir verde porque la fuente no compila).

### 6.2 Las diez celdas — 10 de 10 cumplen

| Versión del código | Pruebas | Se exige | Salió | `failed` | Clase del error |
|---|---|---|---|---|---|
| ACTUAL | N37 (mías) | verde | **verde** | 0 | — |
| ACTUAL | N34 | verde | **verde** | 0 | — |
| ACTUAL | N35 por MCP | verde | **verde** | 0 | — |
| ACTUAL | N35 en el núcleo | verde | **verde** | 0 | — |
| antes_de_N37 | N37 (mías) | **rojo** | **rojo** | 17 | aserción |
| antes_de_N34 | N34 | **rojo** | **rojo** | 3 | `AssertionError` |
| antes_de_N35 | N35 por MCP | **rojo** | **rojo** | 3 | `AssertionError` |
| antes_de_N35 | N35 en el núcleo | **rojo** | **rojo** | 7 | `AssertionError`, `ValueError` |
| antes_de_N37 | N34 | verde | **verde** | 0 | — |
| antes_de_N37 | N35 por MCP | verde | **verde** | 0 | — |

Las tres cosas que hay que leer aquí:

1. **Mis pruebas no son vacuas**: **17 fallos** contra el código de antes. Sin
   esta celda, un «13 passed» no distingue una prueba que blinda de una que
   decora — y ése es exactamente el resultado que la trampa 119 fabrica cuando
   el revert no revierte.
2. **N34 y N35 siguen discriminando**, y **por sus aserciones**, no por un error
   de carga (trampa 25: un rojo hay que saber de qué es). Los tests que caen son
   exactamente los que documentan aquellos arreglos:
   `test_un_fallo_no_sella_NADA_ni_con_raices_de_servidor`,
   `test_una_raiz_que_no_confina_es_SIN_ACCESO_no_sin_confinamiento`,
   `test_un_root_que_no_confina_NO_le_quita_al_cliente_los_que_si`,
   `test_y_el_confinamiento_que_queda_sigue_DENEGANDO_lo_de_fuera`,
   `test_una_raiz_que_no_confina_NO_se_lleva_por_delante_a_las_demas`.
3. **El control cruzado**, que es el que cierra la pregunta del encargo: sobre
   `antes_de_N37` —mi código de partida, sin mi cambio— N34 y N35 salen
   **verdes**. Así que los rojos de las filas 6-8 los produce revertir *aquellos*
   arreglos, y no el mío.

### 6.3 Y una prueba nueva vigila explícitamente que no se deshaga N35

`test_y_el_root_de_red_NO_le_quita_al_cliente_los_que_si_valen`: con
`["file://servidor/recurso", <directorio legítimo>]`, el legítimo sobrevive
—`sin_acceso = False`, confinamiento con una sola raíz— **y** la ruta local que
el root de red producía antes queda denegada. Si rechazar la *authority* se
llevara por delante la lista blanca entera, sería N35 reabierto por otra puerta.

---

## 7. El coste — trampa 28

*Denegar por lista blanca cuesta 9,4 µs y «existe pero no» 193,3 µs (×20,6), e
igualar por arriba convierte el rechazo en un amplificador de DoS.* Así que la
pregunta no es cuánto cuesta el arreglo, sino **si mete trabajo en el camino de
denegación**.

**No lo mete, y se mide en vez de afirmarse.** `_uri_a_ruta` corre una vez por
root y **una sola vez por sesión** (`asegurar` se sella con `_resuelto`), y
`Confinamiento.resolver` —el camino que la trampa 28 mide— no cambia una línea.

Medido **pareado en la misma tanda** (trampas 59 y 79), con la versión vieja
sacada del blob de `2498f4b` y ejecutada tal cual, no reescrita de memoria.
Tres tandas, porque una diferencia pequeña dentro de una tanda no es una medida
(trampa 36) y lo que se publica es el **signo conservado**:

| Batería de `_uri_a_ruta` | t1 | t2 | t3 | Lectura |
|---|---|---|---|---|
| ratio nuevo/viejo, URI **aceptados** | 1,065 | 1,321 | 1,215 | algo más caro, sobre 3-4 µs |
| ratio nuevo/viejo, URI **rechazados** | **0,846** | **0,978** | **0,920** | **más BARATO en las 3** |

El camino de rechazo se abarata porque corta antes: no llega al `unquote` ni al
`normpath`. Es la dirección buena de la trampa 28.

Y el control de que el otro camino no se movió, en esta máquina y esta tanda:

| `Confinamiento.resolver` | t1 | t2 | t3 |
|---|---|---|---|
| `prohibido` (corta en R1) | 10,80 µs | 6,3 | 5,9 |
| `no_existe` (paga `realpath`) | 222,21 µs | 152,8 | 146,8 |
| **ratio** | **20,58×** | 24,25× | 24,99× |

El ×20,58 **reproduce el ×20,6 que publicó la trampa 28**, lo que es un control
de que el instrumento mide lo que dice. *(Las cifras absolutas de tandas
distintas no son comparables — §3 de `CLAUDE.md`; el ratio sí.)*

La traza nueva, medida **aislada** y no por diferencia entre dos totales
(trampa 36): `_podadas` cuesta **10,2 µs**, una vez por sesión MCP.

---

## 8. La suite — las CUATRO declaraciones

Trampas 94 y 101: un recuento sin sus cuatro declaraciones no dice qué se
ejecutó.

| Declaración | Valor |
|---|---|
| **1. Intérprete** | `.venv-mcp-filex\Scripts\python.exe` — **Python 3.11.9, win32** |
| **2. Entorno** | **Docker 29.4.3 levantado** (`docker info` responde) |
| **3. Qué quedó fuera** | *(ver el recuento abajo)* |
| **4. Estado de la máquina** | **NO despejada: otro agente trabajando en documentación**, declarado por el encargo y no comprobado por mí |

### 8.1 Y DOS tandas se descartaron antes de la buena — trampa 84

*«Mientras haya una tanda corriendo, el código que mide y el que se mide no se
tocan.»* La incumplí **dos veces**, las dos por el mismo motivo —seguir puliendo
mientras la suite corría de fondo— y las dos tandas se tiran enteras. No es
ceremonia: lo que hace daño no es la corrida que muere, es la que **sigue
devolviendo un número** de una versión que ya no existe.

Lo que dieron, y por qué se citan igual (son informativas, no la medida):

| Tanda | Resultado | Estado |
|---|---|---|
| 1ª (contaminada) | 1 failed · 512 passed · 3 skipped · 195 subtests · **296,65 s** | descartada |
| 2ª (contaminada) | **0 failed** · 513 passed · 3 skipped · 195 subtests · **199,18 s** | descartada |
| 3ª (limpia) | *§8.2* | **la que cuenta** |

Y de propina traen un dato bueno: el único fallo de la 1ª fue
`test_cancelacion_procesos.py::DuenoMuerto::test_sin_deteccion_el_trabajo_se_queda_working_para_siempre`,
y en la 2ª —con casi el mismo código y la máquina más tranquila, 199 s frente a
297— **no reapareció**. Es la trampa 101 otra vez: ese módulo es sensible al
estado de la máquina. El control de que no es mío está en §8.3.

### 8.2 El recuento

```
514 passed · 3 skipped · 0 failed · 198 subtests · 191,81 s
```

con `.venv-mcp-filex\Scripts\python.exe -m pytest pruebas -q`, **Python 3.11.9
win32**, **Docker 29.4.3 levantado**, y la máquina **no despejada**.

**Qué quedó fuera, y por qué.** Con la traza de `pytest -rs` delante, que es lo
único que vale (trampa 111: *un motivo se escribe con la traza del sujeto
delante, o se deja en `PENDIENTE`*):

| Salto | Motivo, literal de la traza |
|---|---|
| `test_hito4.py:221` | `ningún par real rasteriza hacia un destino con texto en esta máquina — ver bench/aristas-documentales-cierre.md §9` |
| `test_hito6.py:186` | `falta el ráster (bench/salidas-hito6/preparar_h6.py)` |
| `test_hito6.py:697` | `necesita la tarjeta: FILEX_PRUEBAS_SIDECAR=1` |

> **Corrección de este mismo informe, y es la trampa 111 en mi propio texto.**
> La primera versión de esta tabla daba como tercer salto *«falta `FILEX_PY_OCR`
> con el intérprete del venv de OCR»*, y es **FALSO**: lo saqué de un `grep` de
> `skipTest` sobre el código fuente —el sitio de al lado— en vez de la salida de
> `pytest -rs`. El salto real es de `test_hito4.py:221`, un módulo distinto del
> que nombré. Los dos que sí acerté los cité además con la línea equivocada (189
> y 693 en vez de 186 y 697), que es la señal de que no estaba leyendo la traza.
> Ninguno de los tres es nuevo ni mío, así que el recuento no se mueve — pero el
> motivo escrito sí, y era el tipo de dato que nadie vuelve a comprobar.

*(Esta segunda tanda limpia, la del `-rs`, da **514 passed · 3 skipped · 0
failed · 198 subtests · 193,08 s**: reproduce la de §8.2 en todo salvo 1,3 s.)*

Con Docker arriba, las 12 que se saltan sin demonio —el hito 5 entero y la
cancelación real de contenedor— **sí se ejecutaron**.

**Contra la referencia del encargo** (500 passed · 1 failed · 3 skipped · 179
subtests · 224,56 s, con la máquina tranquila): +14 passed y +19 subtests, que
son las pruebas de N37; los mismos 3 saltos; y **0 failed**. El fallo de la fila
N36 que el encargo anunciaba como posible **no apareció** en la tanda limpia —
sí lo hizo en la primera de las descartadas, lo que confirma su inestabilidad
(§8.1) más que otra cosa.

### 8.3 El control de que un rojo de cancelación no sería mío

`git diff --stat 2498f4b HEAD -- filex/ pruebas/` da **tres ficheros**:
`filex/confinamiento.py`, `filex/mcp.py`, `pruebas/test_hito4.py`. Ninguno es de
cancelación, y `git diff --name-only | grep -i cancel` no devuelve nada. La
regla de `CONTRIBUTING.md` §5 —*antes de culpar a un cambio, mira si el cambio
tocó código*— convierte «lo rompió N37» en imposible para ese módulo.

---

## 9. Lo que refuto, y lo que dejo PENDIENTE

### 9.1 Refutaciones

1. **«El caso `file://` con *authority* es rebuscado» — FALSO.** Es lo que
   emiten por defecto los **dos** productores reales para una ruta UNC (Node
   `pathToFileURL` y Python `Path.as_uri()`), y lo que RFC 8089 da por canónico.
2. **«Rechazar toda *authority* no vacía es lo seguro» — FALSO, y medido.**
   Rompe 2 de las 4 raíces legítimas de la tabla (`localhost`), y encima de
   forma **asimétrica entre runtimes**: el mismo root funcionaría desde Node y
   fallaría desde Python. Trampa 51.
3. **«El pendiente del `cwd` es sólo la raíz `""`» — INCOMPLETO.** Había una
   segunda vía que nadie había registrado y que **sí pasa por MCP**: el URI
   `file://` a secas, porque `normpath("")` devuelve `"."`. La raíz `""` sólo
   llega por CLI; `file://` llega por el protocolo.
4. **«Con la *authority* rechazada, la fuga del `cwd` está cerrada» — FALSO, y
   lo refuté yo mismo media hora después de escribirlo** (§1.0). Quedaba
   `file:///D:`, que tiene unidad y **no es absoluta**: `abspath("D:")` da el
   directorio actual de esa unidad. Tres puertas al mismo `cwd`, por tres
   mecanismos distintos. La lección de método: **la enumeración de ramas hay
   que repetirla DESPUÉS del arreglo**, porque el arreglo cambia las ramas.
5. **«C4 no se puede medir en esta máquina» — FALSO, y me lo refuté a mí
   mismo.** Mi primera reacción fue descartar C4 por falta de material; hay
   recurso UNC accesible (`\\localhost\D$`), C4 se midió, **funciona**, y se
   descarta por un motivo mucho mejor: el alias del cerrojo. Un descarte por
   «no hay con qué medirlo» habría sido la trampa 95 —aceptar un bloqueo en vez
   de investigarlo— y habría dado la respuesta correcta por la razón falsa.

### 9.2 PENDIENTE

- **Observar a un cliente real con `cwd` UNC.** Lo que está MEDIDO es el
  productor del mismo runtime (`pathToFileURL` de Node emite
  `file://servidor/recurso`); lo que **no** he observado es a Claude Code
  emitiéndolo, porque haría falta abrir una sesión con la raíz en un recurso de
  red. La inferencia es fuerte pero es una inferencia.
- **Admitir raíces UNC exige cerrar antes el alias del cerrojo de destinos**
  (§4.3). Hoy `_clave_destino` da dos dueños del mismo fichero cuando no existe.
  Es una fila propia, y ahora tiene su número.
- **La *authority* con usuario o puerto** (`file://user@host/p`,
  `file://host:445/p`) cae hoy en el rechazo general por no ser `localhost`, que
  es el lado seguro, pero no la he medido caso a caso.
- **`file://localhost` en POSIX** no se ha medido: la rama de la unidad es de
  Windows y en Linux la función devuelve el `path` tal cual. La prueba se salta
  ahí a propósito, declarándolo.
- **Un `Confinamiento` construido con raíces UNC sigue siendo posible por CLI.**
  N37 cierra la vía MCP; `--raiz \\servidor\recurso\sub` no está cerrado, y con
  §4.3 medido hay ahora un motivo escrito para decidir si debe estarlo.

---

## 10. Texto propuesto *(no he tocado `ESTADO-Y-REPARTO.md`, `CLAUDE.md` ni `PLAN-ORQUESTADOR.md`)*

### 10.1 Para `ESTADO-Y-REPARTO.md` §1 — el informe

```
| `bench/uri-authority.md` | N37: la authority de un `file://` se rechaza en vez de traducirse a UNC; cerrados también el `cwd` y la poda muda | worker7 |
```

### 10.2 Para la fila N37 del inventario

```
🟢 N37 — `_uri_a_ruta` descartaba la authority: la raíz no se perdía, se
SUSTITUÍA por una ruta local (`file://nas/Work` -> `D:\Work` entero). Se
rechaza (salvo `localhost`, RFC 8089 §2) en vez de traducir a UNC: las dos
empatan en la tabla de candidatos y admitir UNC da DOS DUEÑOS del mismo destino
en el cerrojo cuando el fichero aún no existe. Cerrados de paso los otros dos
pendientes de worker5: la raíz `""` confinaba en el `cwd` y la poda de N35 era
muda. `bench/uri-authority.md`.
```

### 10.3 Trampa propuesta — iría al FINAL, como la **120**

> **120. Un campo descartado al analizar sintácticamente no «se pierde»: puede
> SUSTITUIR el valor por otro, y entonces el fallo abre en vez de cerrar —
> MEDIDO el 04/09** (`bench/uri-authority.md`). `_uri_a_ruta` tiraba el
> `netloc` de un `file://` y se quedaba con el `path`. Lo que uno espera de un
> campo ignorado es perder acceso; lo que pasaba es lo contrario:
> `file://servidor/recurso` daba `\recurso`, y `os.path.abspath` lo completa
> con **la unidad del proceso**, así que el confinamiento acababa en
> `D:\recurso` — una lista blanca que nadie declaró. El caso caro estaba a un
> nombre de distancia: `file://nas-de-la-empresa/Work` concedía `D:\Work`
> entero, con otro proyecto dentro; y dos URI que denotan cosas distintas
> —`file://servidor/recurso` y `file:///recurso`— colapsaban en **la misma
> raíz**, que es la prueba de que el campo llevaba información. **Y no es una
> forma rebuscada: los DOS productores reales la emiten** (`pathToFileURL` de
> Node y `Path.as_uri()` de Python dan `file://servidor/recurso` para una ruta
> UNC) mientras el consumidor del mismo runtime —`fileURLToPath`— **rechaza con
> error las tres formas que FileX aceptaba y traducía a rutas inventadas**.
> Dos corolarios que sólo aparecen ejecutando: **(a)** la norma tiene una
> *authority* que significa «ninguna» —`localhost`, RFC 8089 §2— y **los
> runtimes discrepan al tratarla**: Node la normaliza a vacía y Python la
> entrega como `netloc`, así que rechazarlas todas rompe el mismo root según
> quién lo emita (2 de 4 legítimas en la tabla de candidatos: la trampa 51 otra
> vez). **(b)** La política buena no se elige por detección —rechazar y
> traducir a UNC atrapan las mismas 4 fugas y no rompen ninguna legítima— sino
> por lo que arrastra: admitir UNC mete un **alias** en el confinamiento que
> `realpath` no colapsa (`st_dev`+`st_ino` idénticos, rutas distintas), y el
> cerrojo de destinos da entonces **DOS DUEÑOS del mismo fichero justo cuando
> el destino todavía no existe**, que es el caso normal de un conversor y es la
> trampa 26 por una puerta nueva. **Cuando descartes un campo al analizar una
> entrada, pregunta qué valor OCUPA su sitio** — y si la respuesta la pone el
> entorno del proceso (`abspath`, el `cwd`, la unidad actual), lo que tienes no
> es una pérdida sino una sustitución silenciosa.
