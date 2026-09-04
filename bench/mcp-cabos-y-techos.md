# Cabos de MCP y techos declarados — `C36`, `C28`, `C16`

**worker2, carril CPU/Docker, ronda 14** · rama `cpu/mcp-cabos-y-techos` ·
salidas en `bench/salidas-mcp-cabos-techos/`

Dos encargos distintos en un informe, y conviene separarlos desde el título:

- **`C36`** son **cabos de MCP** que se cierran **midiendo**: tres de los cinco
  pendientes vivos de `hito4-mcp.md` §13 (ítems 5, 6 y 2), más la
  **instrumentación** del que no se puede forzar (ítem 3) y la declaración
  expresa del que queda fuera (ítem 1).
- **`C28`** y **`C16`** son **techos ya medidos por dos rutas independientes**.
  Aquí no se vuelve a medir nada: se escribe **qué queda exactamente fuera,
  cuánto costaría pasar del techo y con qué fuente de ficheros, y la afirmación
  exacta que se puede publicar hoy**. La decisión de cerrar las filas es del
  maestro.

**Las cinco frases que resumen el informe:**

1. **`session.list_roots()` —la vía por la que FileX pregunta los roots— está
   DEPRECADA en el protocolo 2026-07-28, y el servidor de FileX ya emite hoy el
   aviso: 1 `MCPDeprecationWarning` al construirse, contra 0 del control sin el
   manejador de roots — MEDIDO.**
2. **Un fallo transitorio de `roots/list` dejaba la sesión denegada PARA
   SIEMPRE: `sin_acceso = True` sellado con `_resuelto = True`, y el reintento
   del cliente no volvía a preguntar (1 llamada, no 2) — MEDIDO y ARREGLADO.**
   Es la trampa 43 —*separar «no se puede» de «no está»*— dentro de un módulo
   que ya la citaba.
3. **La regla de subsunción de `PLAN-ORQUESTADOR.md` §4.4 tiene dos conjuntos y
   sólo uno es automatizable, y el precio está medido:** contra el único
   catálogo con respuesta conocida —las 27 herramientas de `video-audio-mcp`, de
   las que `RESULTADOS-MCP.md` §4 declara 13 casos particulares de 2— el
   predicado estricto atrapa **2 de 13** y el relajado **13 de 13 con 1 falso
   positivo irreducible**. FileX da **0 con las dos variantes**.
4. **Mi propio arnés midió su doble en vez de a FileX, y la corrección invierte
   la respuesta:** con un `roots/list` que no cede el bucle de eventos, dos
   herramientas concurrentes daban **1** ida y vuelta; con un punto de
   suspensión donde un `roots/list` real lo tendría, dan **2 de 2**. La caché de
   roots **no es segura en la primera llamada concurrente**.
5. **La partición de los 56 destinos inescribibles que publica la trampa 72 de
   `CLAUDE.md` suma 42, no 56** — le faltan tres clases (8 sin clasificar, 4 de
   vips, 2 `AVERROR_INVALIDDATA`). La partición completa, de ocho clases, está en
   `firmas-cierre.md` §4.4 y sí suma 56. Es la trampa 48 sobre otro recuento.

---

## 0. Cómo se midió, y con qué máquina

| | |
|---|---|
| **Intérprete** | `D:\Work\research\FileX\.venv-mcp-filex\Scripts\python.exe`, **3.11.9, win32**. Es el único venv con `mcp>=2.0.0` (trampa 14) |
| **SDK** | `mcp 2.0.0`, `mcp-types 2.0.0` |
| **Entorno** | Docker levantado (`docker info` → `29.4.3`) |
| **Estado de la máquina** | **NO despejada**: hay otro worker en el carril GPU trabajando en paralelo. Ninguna cifra de este informe es un TIEMPO — son recuentos y veredictos deterministas, insensibles a la contención (trampa 101 declarada, no sorteada) |
| **Corpus** | `git lfs checkout` hecho; `corpus/imagen/tipico.png` = **42 855 B**, no 130 (trampas 34 y 107: se comprueba el TAMAÑO, y la sonda lo publica en su JSON) |
| **Lock de GPU** | **NO tomado**. Nada de esto usa la tarjeta |

---

## 1. `C36` ítem 2 — qué le pasa a `roots` en el protocolo 2026-07-28

`hito4-mcp.md` §13 lo dejó escrito como *«R13 entera depende de ello. No lo he
investigado»*. Se investiga **ejecutando el SDK instalado**, no leyendo la
especificación: lo que sólo se lea queda `PENDIENTE` y se dice cuál es
(trampa 111).

**Sonda:** `bench/salidas-mcp-cabos-techos/sonda_protocolo.py` →
`protocolo.json`.

### 1.1 Lo MEDIDO

| Celda | Resultado |
|---|---|
| `KNOWN_PROTOCOL_VERSIONS` | `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25`, **`2026-07-28`** (5) |
| `LATEST_PROTOCOL_VERSION` | **`2026-07-28`** |
| `SUPPORTED_PROTOCOL_VERSIONS` | las cinco |
| `ServerSession.list_roots.__deprecated__` | **`"The roots capability is deprecated as of 2026-07-28 (SEP-2577)."`** |
| **Avisos al construir el servidor de FileX** | **1**, `MCPDeprecationWarning`, con ese texto exacto |
| **Control negativo: `Server(...)` sin `on_roots_list_changed`** | **0 avisos** |
| Capacidades que declara el servidor de FileX | `tools` (`list_changed: false`), `experimental`, `extensions`. Ni `resources` ni `prompts` — como estaba medido |
| `ListRoots` (marcador de *resolver*) | **existe y NO está deprecado** |
| Campos de `ClientCapabilities` | `elicitation`, `experimental`, `extensions`, **`roots`**, `sampling`, `tasks` |

**La atribución es limpia porque la sonda lleva su refutación dentro**
(trampa 111): el aviso lo dispara `on_roots_list_changed`, y se demuestra
construyendo el mismo `Server` sin ese manejador, que emite **0**.

**La respuesta a la pregunta del pendiente, con la traza delante:** a `roots`
**no le sustituye una capacidad nueva — se le retira el canal**. Lo que cambia
es el *transporte* de la pregunta, y lo dice el propio SDK en el docstring de
`mcp/server/mcpserver/resolve.py`, que la sonda guarda entero en
`protocolo.json`:

> *«The transport follows the negotiated protocol: **>= 2026-07-28 batches the
> requests into an `InputRequiredResult` and resumes when the client retries
> with `input_responses`/`request_state`**; <= 2025-11-25 sends each standalone
> server-to-client request mid-call. […] **Resolver bodies may re-run on every
> round**»*

Es decir: la vía que FileX usa hoy —una petición `roots/list` del servidor al
cliente **a media llamada**— es exactamente la que 2026-07-28 deja de tener. Lo
que queda en su sitio es el *resolver* `Annotated[T, Resolve(fn)]` que devuelve
`ListRoots()`, y cuyo cuerpo **puede volver a ejecutarse en cada ronda** — que
es, literalmente, el ítem 6 de este mismo encargo. **Los dos pendientes de §13
son el mismo mecanismo visto desde dos lados**, y ninguno de los dos lo decía.

### 1.2 Lo PENDIENTE, dicho por su nombre

- **Qué dice SEP-2577.** No lo he leído: no hay red en esta sesión y el texto de
  la SEP no está en el árbol. Todo lo de arriba sale de **ejecutar el SDK**, que
  es una implementación de la especificación, no la especificación.
- **Cuándo dejará Claude Code de negociar `2025-11-25`.** `hito4-mcp.md` mide
  que hoy negocia esa versión. No he vuelto a comprobarlo en esta sesión, así
  que lo heredo marcado como heredado.
- **Si `roots` se retira o sólo se deprecia.** Sigue siendo campo de
  `ClientCapabilities` en `mcp-types 2.0.0` y `ListRoots` no está deprecado: eso
  es compatible con «deprecado pero vivo» y con «vivo sólo para versiones
  viejas». El SDK no lo distingue por sí solo.

### 1.3 Hallazgo lateral, y no es pequeño: **Tasks**

`PLAN-ORQUESTADOR.md` §5.3 justifica construir el asa `job_id` entera con esta
premisa: *«Tasks (SEP-1686) **fue eliminado de la especificación**, así que el
asa hay que construirla entera»*. Contra el SDK instalado — MEDIDO:

- **`ServerCapabilities` tiene el campo `tasks`**, y `ClientCapabilities`
  también.
- `mcp_types` exporta **30 tipos** de tarea: `Task`, `TaskStatus`,
  `CreateTaskResult`, `GetTaskRequest`, `GetTaskResult`, `CancelTaskRequest`,
  `ListTasksRequest`, `TaskMetadata`, `TaskStatusNotification`…
- **`TaskStatus` = `working | input_required | completed | failed | cancelled`** —
  cuatro de los cinco estados son exactamente los que la herramienta `job` de
  FileX inventó a mano.
- **Ninguno de los cinco tipos sondeados está marcado deprecado** (`Task`,
  `CreateTaskResult`, `GetTaskRequest`, `CancelTaskRequest`,
  `ListTasksRequest`: los cinco `False`).
- **Y el matiz que evita convertir esto en una refutación alegre:** los siete
  docstrings sondeados dicen, uniformemente, **«(2025-11-25 only)»**.

**Lo que esto sí permite afirmar (MEDIDO):** en `mcp 2.0.0`, la superficie de
Tasks existe entera, sin deprecar, y acotada por su propia documentación a
`2025-11-25` — **que es justo la versión que Claude Code negocia hoy**. **Lo que
NO permite afirmar:** que §5.3 se equivoque. Su frase es probablemente correcta
**para 2026-07-28** y engañosa para el presente.

**PENDIENTE, y propongo fila nueva:** medir si un `convert` largo se puede
entregar como `Task` nativo contra Claude Code 2.1.238 en vez de con el
`job_id` propio, y qué costaría en catálogo. No cabía en este encargo y no lo he
tocado.

---

## 2. `C36` ítem 6 — idempotencia real ante `Resolve(ListRoots)` doble

El pendiente de §13: *«El cuerpo está escrito idempotente hasta la línea de
roots, pero **no se ha ejercitado un cliente que lo dispare**: Claude Code usa
hoy la vía clásica»*.

**Arnés:** `bench/salidas-mcp-cabos-techos/sonda_idempotencia.py` →
`idempotencia.json` (y `idempotencia_antes.json`, la misma sonda antes del
arreglo de M3). Recupera el manejador **real** que `filex.mcp.construir()`
registró en `Server._request_handlers["tools/call"]` y lo invoca con el modelo
de parámetros que el propio `HandlerEntry` declara: es el camino de producción,
no una copia (trampa 109).

### 2.1 M0 — el pendiente atribuye la causa a medias

| Celda | Resultado |
|---|---|
| Maquinaria de `Resolve` en `mcp.server.lowlevel` | **ninguna**: `Resolve`, `ListRoots`, `Elicit`, `Sample` → **0 de 4** |
| La misma en `mcp.server.mcpserver.resolve` | **4 de 4** |
| ¿Puede FileX sufrir hoy la doble ejecución? | **NO** |

**El hecho de §13 es cierto y la causa está incompleta.** No es sólo que *el
cliente* use la vía clásica: **FileX construye su servidor con
`mcp.server.lowlevel.Server`, y la maquinaria de `Resolve` vive en
`mcp.server.mcpserver`**, que FileX no usa. Aunque mañana Claude Code negociara
2026-07-28, el cuerpo de FileX **seguiría sin poder** re-ejecutarse por esta vía:
lo que le pasaría es otra cosa —que `session.list_roots()` está deprecado (§1)—.
Es la trampa 58: *el hecho no implica la causa*, y quien hubiera esperado a un
cliente nuevo habría esperado a la mitad equivocada del sistema.

### 2.2 M1/M2 — la caché, y por qué el orden del cuerpo es la pieza que aguanta

Dos llamadas idénticas a `convert`, misma sesión:

| Magnitud | Valor |
|---|---|
| `roots/list` pedidos | **1** |
| `job_id` devueltos | **2, distintos** (`20ef99338f41`, `abee12ff3de3`) |
| trabajos registrados | **2** |

**La caché de roots cumple** (1 pregunta por sesión, no una por herramienta): es
la primera vez que R13 se comprueba por ejecución y no por lectura. **Y el cuerpo
más allá de la línea de roots NO es idempotente**, ni pretende serlo: dos
llamadas gastan dos `job_id` y lanzan dos conversiones al mismo destino. Eso es
correcto para dos llamadas normales, y es exactamente por lo que **la posición
de `asegurar()` como primera sentencia del manejador es carga estructural y no
estilo**: bastaría moverla una línea por debajo de `Trabajos.nuevo()` para que
una re-ejecución filtrara un `job_id` por ronda. Hoy está bien puesta —
comprobado en el código que se ejecuta, no en el comentario que lo dice.

### 2.3 M3 — el fallo, y es un fallo de verdad

Se hace fallar **una** vez a `roots/list` (que es lo que haría un canal de vuelta
caído, un `NoBackChannelError`, o el aborto que 2026-07-28 introduce), con el
servidor arrancado **sin `--raiz`**:

| | **Antes** (`idempotencia_antes.json`) | **Después** |
|---|---|---|
| `roots/list` tras el fallo | 1 | 1 |
| `sin_acceso` | `true` | `true` |
| `_resuelto` | **`true`** | **`false`** |
| **`roots/list` en el reintento del cliente** | **1 — no vuelve a preguntar** | **2** |
| Respuesta del reintento | `{"error": "ruta no accesible"}` | el `inspect` completo |
| `sin_acceso` tras el reintento | **`true` — para siempre** | **`false`** |

**Un fallo transitorio quedaba sellado como una denegación permanente de toda la
sesión.** El `except Exception` de `asegurar()` no distinguía *«el cliente no
tiene roots»* —legítimo, es el caso de `--raiz` sola— de *«no se pudo
preguntar»*, y detrás ponía `_resuelto = True`. Es la **trampa 43** —*toda
detección por excepción necesita separar «no se puede» de «no está»*— reaparecida
en un módulo cuyo propio comentario ya nombraba la primera mitad del problema.

**Y el modo de fallo es del peor tipo:** la respuesta es el mensaje opaco de R1/R4,
que es *correcto de cara al usuario* y por eso **indistinguible de una
denegación legítima** para quien depura. Nadie lo habría visto sin provocarlo.

**El arreglo no clasifica excepciones, porque no son clasificables**: se limita a
**no sellar el resultado en la única esquina donde volver a preguntar puede
cambiar la respuesta** — falló la pregunta *y* no queda ninguna raíz efectiva:

```python
self._resuelto = not (fallo and not efectivas)
```

Coste: una ida y vuelta más por llamada, y sólo en la sesión que ya estaba
denegada. El contrapunto está medido y también es prueba: **con `--raiz` puesta,
un fallo del cliente SÍ se sella** (1 llamada, no 2), porque la respuesta ya es
buena y repreguntar no la cambiaría.

Tres pruebas nuevas en `pruebas/test_hito4.py` (`RootsCacheYFallo`):
`test_los_roots_se_preguntan_UNA_vez_por_sesion`,
`test_un_fallo_al_preguntar_NO_deja_la_sesion_denegada_para_siempre`,
`test_un_fallo_CON_raiz_de_servidor_si_se_sella`.

### 2.4 M4 — mi arnés midió a mi arnés, y la corrección invierte el signo

Primera versión, dos herramientas lanzadas a la vez con la caché fría:
**1 `roots/list`**. Parecía un resultado — la caché aguanta la concurrencia.

**Era falso, y lo delató la celda que registra si la condición se dio.** Mi
`list_roots` falso era un `async def` **sin un solo `await` dentro**, así que no
devuelve el control al bucle de eventos: las dos corrutinas se ejecutaron **en
serie**, y el `entradas_simultaneas_en_roots_list` que añadí para comprobarlo
valía **1**. Es la trampa 38: *registra si la condición que dices reproducir se
dio, no sólo el resultado*.

Con un punto de suspensión donde un `roots/list` real —una ida y vuelta por el
cable— lo tendría:

| Variante del doble | `roots/list` | entradas simultáneas | las dos responden |
|---|---|---|---|
| **sin ceder el bucle** *(control negativo del arnés)* | 1 | **1** | sí |
| **cediendo** | **2** | **2** | sí |

**La caché de roots no es segura en la primera llamada concurrente:** el
`threading.Lock` de `asegurar()` se suelta **antes** del `await`, así que N
herramientas que entren a la vez con la caché fría hacen **N** idas y vuelta.
No es un fallo de corrección —el cálculo es idempotente y las dos llamadas dan
lo mismo— pero **contradice lo que «cacheada por sesión» hace creer**, y el
coste es lineal en el número de herramientas que el modelo dispare en paralelo.

**No lo he arreglado, a propósito**: el arreglo natural es sostener el candado a
través del `await`, y eso es cambiar un `threading.Lock` por uno de `anyio` en un
módulo que ahora mismo no tiene esa dependencia importada, con el riesgo de
convertir una ida y vuelta de más en un interbloqueo. **Lo dejo medido y
propuesto como fila nueva**, que es más barato que un arreglo sin medir.

---

## 3. `C36` ítem 5 — la prueba de subsunción automática

`PLAN-ORQUESTADOR.md` §4.4: *«si el esquema de la herramienta A es un
**subconjunto estricto** del de B **con la misma semántica**, A sobra»*.

**La regla tiene dos conjuntos y sólo el primero es automatizable.** Todo lo que
sigue mide **cuánto vale ese medio predicado**, porque un comprobador que sólo
se ejecutara sobre el catálogo de FileX —cinco herramientas cuyos nombres de
parámetro son **disjuntos salvo `formato_destino`**— devolvería **0 siempre**,
con el comprobador puesto y con el comprobador roto (trampas 60 y 109).

**Comprobador:** `bench/salidas-mcp-cabos-techos/subsuncion.py` →
`subsuncion.json`.

### 3.1 El predicado, y la condición que nadie escribe

`A ⊑ B` si:

0. **`props(A) ≠ ∅`.** Una herramienta sin parámetros no es un caso particular
   de nada. Sin esta línea, `health_check` sale subsumida **por las 26
   restantes** de `video-audio-mcp` — MEDIDO.
1. **`props(A) ⊆ props(B)`, con el mismo tipo.**
2. **`req(B) ⊆ props(A)`.** Si `B` exige un parámetro que `A` ni siquiera tiene,
   quien llamara a `A` no sabría con qué rellenarlo.
3. **Estricto**: con esquemas idénticos no hay «A sobra», hay un empate.

### 3.2 El control positivo: las 27 de `video-audio-mcp`

`RESULTADOS-MCP.md` §4 midió que **13 de las 27 son casos particulares de 2**
(`convert_video_properties` y `convert_audio_properties`). El catálogo se
reconstruye **por AST del fuente** —FastMCP deriva el esquema de las anotaciones
de tipo— porque `.venv-mm-vamcp` se borró en la limpieza del 31/08 y el servidor
ya no se puede arrancar.

| Variante | parejas | herramientas que sobran | aciertos sobre las 13 | escapadas | no declaradas por el informe |
|---|---:|---:|---:|---:|---|
| **`req(B) ⊆ props(A)` exigido** | 2 | 2 | **2** | **11** | 0 |
| **relajada** | 14 | 14 | **13** | **0** | **1** (`trim_video`) |

**Por qué el estricto sólo atrapa 2:** las únicas dos que caen son
`convert_video_format` y `convert_audio_format`, porque son las únicas que
llevan `target_format` — **el parámetro obligatorio del subsumidor**. Las once
`set_*` no lo tienen, así que llamar al subsumidor exigiría inventarse un
formato de destino que nadie pidió. **El «son casos particulares» del informe es
un juicio semántico, no una relación de esquemas**, y el 2/13 lo demuestra con
número.

**Y el falso positivo del relajado no es un artefacto: es la demostración de que
la mitad semántica no se puede quitar.** `trim_video(video_path,
output_video_path, start_time, end_time)` sale subsumida por
`add_image_overlay(video_path, output_video_path, image_path, position, opacity,
start_time, end_time, width, height)`: **subconjunto estricto perfecto**. Y es
absurdo — recortar un vídeo no es un caso particular de ponerle una marca de
agua. Lo que ocurre es que **`start_time`/`end_time` significan cosas distintas
en cada una**: en `trim_video`, dónde cortar; en `add_image_overlay`, cuándo
aparece el logo. Es la forma de las trampas 70 y 73 sobre otro objeto: **el mismo
nombre en dos sitios no es el mismo dato**, y ningún esquema lo distingue.

### 3.3 El sujeto: el catálogo de FileX

**0 parejas subsumidas, con las dos variantes del predicado.** Los cinco
esquemas:

| Herramienta | propiedades | obligatorias |
|---|---|---|
| `convert` | `entrada`, `salida`, `formato_destino`, `parametros` | `entrada`, `salida` |
| `inspect` | `ruta` | `ruta` |
| `list_targets` | `formato_origen`, `formato_destino` | `formato_origen` |
| `batch` | `entradas`, `directorio_salida`, `formato_destino` | las tres |
| `job` | `job_id`, `accion` | `job_id` |

Que el 0 salga **también con el predicado relajado** es lo que lo hace decir
algo: no es una propiedad del predicado más estricto que elegí.

### 3.4 Lo que se entrega, y lo que NO se puede entregar

**Se entrega una prueba en la suite** (`pruebas/test_hito4.py`, clase
`Subsuncion`), con tres casos y **hermética** —su control positivo es sintético,
porque `repos/` está en `.gitignore` y no existe en un clon ni en el runner
(trampa 104: lo que se comprueba es lo que se versiona)—:

- `test_el_comprobador_atrapa_una_subsuncion_de_verdad` (control positivo),
- `test_el_comprobador_no_atrapa_lo_que_solo_se_PARECE` (control negativo),
- `test_el_catalogo_de_filex_no_tiene_ninguna_herramienta_que_sobre`.

**No se entrega una PUERTA, y hay que decirlo con el número delante:** con
recall 2/13 el predicado estricto deja pasar el 85 % de la redundancia real, y
con el relajado —recall 13/13— **1 de cada 14 candidatas es falsa y no hay forma
de saber cuál sin leer la semántica**. Lo defendible es **un generador de
candidatas que un humano arbitra**, no un `assert` que bloquee un PR de un
tercero. La prueba de la suite aprovecha que el catálogo de FileX da 0 en las dos
variantes: ahí el generador y la puerta coinciden, y sólo ahí.

---

## 4. `C36` ítem 3 — la emisión real de `roots/list_changed`: instrumentado, no forzado

`hito4-mcp.md` §13 y `CLAUDE.md` §5 lo dicen igual: Claude Code 2.1.238 declara
`roots.listChanged: true` —se compromete a avisar— y **observar una emisión real
sigue PENDIENTE**, porque en *headless* no hay forma de cambiar los roots a
media sesión.

**No la he fabricado, y no la voy a declarar observada.** Lo entregable es
dejar puesto el sitio donde se vería:

- `Raices.emisiones` — un contador, que hoy vale **0** y sube en cada
  `notifications/roots/list_changed`. Coste: un entero.
- `Raices.VAR_REGISTRO` = **`FILEX_MCP_REGISTRO_ROOTS`** — si nombra un fichero,
  cada emisión se anota ahí con marca de tiempo y PID. **Opt-in**: sin la
  variable no se escribe nada, y un destino imposible **no tumba el servidor**
  (las dos cosas, con prueba).

El contador vive y muere con el proceso del servidor, y una emisión real
llegaría dentro de una sesión de Claude Code que nadie observa desde dentro: por
eso el registro va a fichero y no sólo a memoria.

**Estado: `PENDIENTE`, y sigue siéndolo.** Lo que cambia es que el día que
llegue habrá dónde verlo sin volver a instrumentar. Dos pruebas nuevas:
`test_la_emision_de_roots_list_changed_queda_CONTADA` y
`test_el_registro_de_emisiones_es_opt_in_y_no_revienta`.

---

## 5. `C36` ítem 1 — queda FUERA, y se declara

**Repetir `hito4-mcp.md` §4 con otro modelo y n≥10.** No lo he intentado ni a
medias. Motivo: son ≥10 sesiones reales de cliente con dos catálogos, y no cabe
con lo demás de este encargo. **No hay ningún dato nuevo suyo en este informe**,
y su fila sigue exactamente donde estaba.

**Recuento de `C36` tras esta ronda:** de los nueve originales, dos ya estaban
cerrados (`gotenberg-y-mcp.md`), dos los cerró worker10 (`suelo-y-mcp.md` §2),
**tres los cierra este informe** (ítems 2, 5 y 6), **uno queda instrumentado y
declarado `PENDIENTE`** (ítem 3, que no se puede forzar) y **uno queda fuera**
(ítem 1).

---

## 6. `C28` — el techo, escrito con su coste

**No he vuelto a medir nada de `C28`.** Esta sección es la lectura de lo ya
medido por `firmas-cierre.md` §4.4 (el techo), `fate-y-aristas.md` §1 (worker2,
ronda 11) y `fate-completo.md` §1 (worker11, ronda 13), puesta en la forma que
pedía el encargo.

### 6.1 Qué son los 56, y una corrección de recuento

Los **56** son los destinos que el censo de firmas marcó `0_indeterminado` con el
motivo *«no se pudo escribir con ningún motor disponible»* — de ahí que no haya
muestra con la que censar su marcador. Salen del reparto de los 86 indeterminados
de `firmas-cierre.md` §4.1: **86 = 56 + 17 + 13**.

**Y aquí hay una corrección que hay que publicar.** La trampa 72 de `CLAUDE.md`
resume el reparto de esos 56 por `rc` en **cinco** clases:

> *«**11** `AVERROR_ENCODER_NOT_FOUND`, **3** `AVERROR_EXPERIMENTAL`, **18**
> `EINVAL`, **8** que no son formatos sino volcados de metadatos, y **2** en los
> que el motor escribe un directorio»*

**11 + 3 + 18 + 8 + 2 = 42, no 56.** La partición completa está en
`firmas-cierre.md` §4.4 y tiene **ocho** clases:

| Clase por `rc` | n |
|---|---:|
| `EINVAL (-22)` — el codificador está y la invocación no cumplía | **18** |
| `AVERROR_ENCODER_NOT_FOUND` — esta build no lo trae | **11** |
| «metadato, no formato» — volcado que sólo existe si la entrada lo trae | **8** |
| **sin clasificar** (`rc=1` de ImageMagick, `stderr` truncado a 400 car.) | **8** |
| **el motor no lo sabe escribir** (`dzi`, `nia`, `nii`, `pml`: vips) | **4** |
| `AVERROR_EXPERIMENTAL` — basta `-strict -2` | **3** |
| `rc=0` y sin fichero — el motor escribe un **directorio** | **2** |
| **`AVERROR_INVALIDDATA`** (`dv`, `flm`) | **2** |
| | **56** |

Las tres que la trampa 72 omite son las **8 sin clasificar**, las **4 de vips** y
las **2 `INVALIDDATA`**. Es la **trampa 48** otra vez —*un recuento correcto no
prueba un contenido correcto*— con el agravante de que aquí el recuento **ni
siquiera cuadra**, y nadie lo sumó en un mes. Propongo el texto corregido en §8.

### 6.2 (a) Qué queda exactamente fuera del techo

**El techo son 15**, y `firmas-cierre.md` §4.4 dice cuáles y por qué sólo ésos:

> *«**FATE cerraría, como mucho, 15 de 56** (los 11 sin codificador + los 4 que
> el motor dice que no sabe escribir) **y ni siquiera bien**: FATE es un corpus
> de ficheros para **decodificar**, y lo que el censo necesita es una muestra
> **escrita**»*

Los 15: `ac4 avs3 bit c2 cavs cvg dzi evc lbc nia nii oma pml rcv vc1`.

**Los 41 restantes = 56 − 15**, y **no son un bloque homogéneo de trabajo sin
tocar**: 18 `EINVAL` + 8 metadatos + 8 sin clasificar + 3 `EXPERIMENTAL` +
2 directorio + 2 `INVALIDDATA`. Su estado real, tras la ronda 11:

| Sub-bloque | n | Estado |
|---|---:|---|
| Invocación (`EINVAL`+`EXPERIMENTAL`+`INVALIDDATA`) | 23 | **6 escritas** en `firmas-cierre.md` + **14 de 17** escritas por worker2 con dos semillas y prefijo estable = **20 cerradas**; **2** (`js`, `sup`) **reclasificadas** a «sin encoder en esta build» —o sea, **se mudan al bloque de los 15**—; **1** (`chk`) exige otro paradigma de invocación (fragmentar la salida), no una bandera |
| «metadato, no formato» | 8 | **No son destinos de conversión.** Y worker2 movió **4** de los sin clasificar aquí: el bucket real es **12**, no 8 |
| Sin clasificar | 8 | **Cerradas con `stderr` completo**: 4 al bucket de metadato, 1 delegado que no admite la variante (`jpt`), **3 con hallazgo nuevo** — GraphicsMagick falla en silencio total e ImageMagick devuelve `rc=0` sin escribir un byte |
| Directorio | 2 | Un cambio de arnés, sin medir |

**Consecuencia incómoda, y es la que hay que llevar a la fila:** el techo
publicado —15/56— **está desactualizado respecto a su propio refinamiento**, y lo
declara el propio worker2 en `fate-y-aristas.md` §3: *«no se ha reconstruido la
tabla de `firmas-cierre.md` §4.4 con ellos»*. Con `js` y `sup` mudados, el bloque
«otro motor u otra build» es de **17**, no de 15. **Nadie ha recompuesto la
partición, y por eso la fila sigue diciendo 15/56.**

### 6.3 (b) Cuánto costaría pasar del techo, y con qué fuente

**Para los 15 (los que FATE podría tocar): FATE ya está bajado y no basta.**
`fate-completo.md` §1.3 los cierra uno a uno: **5 con lectura real confirmada**
(`oma`, `vc1` vivos y `evc` muerto de rebote de C16; `cavs` y `rcv` vivos) y
**10 sin fichero real aprovechable** (5 no encontrados —`ac4`, `avs3`, `c2`,
`cvg`, `lbc`—, 1 colisión de extensión declarada —`bit`, cuyos 231 `.bit` en
FATE son HEVC/VVC/MP3 de conformidad—, 4 fuera del dominio de FATE —`dzi`, `nia`,
`nii`, `pml`, que son formatos de vips y no códecs—).

**Y el techo no se mueve ni con esas 5**, por la razón que ya estaba escrita:
confirman que el códec de **LECTURA** existe, no que ffmpeg pueda **ESCRIBIR**
ese destino. La única fuente que cerraría los 15 de verdad es la otra mitad de la
frase de §4.4: **«compilar ffmpeg con más codificadores»** —o traer otra build—.
**Coste: no medido, y no lo mido aquí.** Es la única deuda de `C28` que sigue
pidiendo una descarga o una compilación.

**Para los 41: ninguna fuente de ficheros los cierra, por construcción.** Sus
precios están tasados en `firmas-cierre.md` §4.4 y son de máquina, no de red:

| Remedio | n | Precio escrito |
|---|---:|---|
| invocación correcta | 23 | **minutos de ffmpeg, 0 bytes de red** — 20 ya escritas |
| entrada con el metadato dentro | 8 | construir una entrada con perfil ICC/IPTC/EXIF: **minutos** |
| tratar el destino como directorio | 2 | **un cambio de arnés** |
| mirar el `stderr` completo | 8 | **volver a correr esas 8** — ya hecho |

Lo que queda de verdad sin hacer en los 41 son **3 celdas**: `chk` (otro
paradigma de invocación) y las **2** del bucket de directorio. Todo lo demás está
cerrado o reclasificado.

**Coste de FATE, para el registro:** `D:\Work\research\fate-suite`, **2 529
ficheros, 1 345 840 190 B, 303 subdirectorios**, fuera del repositorio por §6.
**El tiempo y el ancho de banda de la descarga NO están registrados en ningún
sitio del repositorio** — lo he buscado en los 15 ficheros que citan
`fate-suite`. Es un hueco de trazabilidad menor, pero conviene decirlo antes de
que alguien cite un coste que nadie midió.

### 6.4 (c) La afirmación que se puede publicar hoy, redactada para pegar

> **`C28` — techo declarado con su coste.** De los **56** destinos que el censo
> de firmas dio por inescribibles, **FATE cierra como mucho 15, y de hecho
> cierra 0**: el corpus aporta capacidad de **lectura** y lo que el censo
> necesita es una muestra **escrita**. Con FATE ya en disco (2 529 ficheros,
> 1 345 840 190 B) los 15 tienen dato directo uno a uno —**5 con lectura real,
> 10 sin fichero aprovechable**— y **el techo no se mueve**. Los **41
> restantes no son un problema de ficheros y no los cierra ninguna descarga**:
> son 23 de invocación (**20 ya escritas**, 0 bytes de red), 8 volcados de
> metadatos que **no son destinos de conversión**, 8 de `stderr` truncado (**ya
> resueltas**) y 2 en las que el motor escribe un directorio. **Sin hacer quedan
> tres celdas** —`chk` y las dos de directorio— y **una sola deuda que pide
> recurso externo: una build de ffmpeg con más codificadores, cuyo coste no está
> medido.** *(Y dos avisos de recuento: la partición de la trampa 72 suma 42, no
> 56 —la completa, de ocho clases, está en `firmas-cierre.md` §4.4—; y el techo
> «15» no incorpora el refinamiento de la ronda 11, que muda `js` y `sup` a esa
> clase y la deja en 17.)*

---

## 7. `C16` — el techo, escrito con su coste

Tampoco he vuelto a medir nada. Fuentes: `aristas-nominales.md` §0/§4.2/§7 (los
445 y los tres escenarios), `fate-y-aristas.md` §2 (n=69) y `fate-completo.md`
§2 (n=95).

### 7.1 De dónde salen el 54,78 % y los 445

Las **75 874 aristas indeterminadas** son el **54,78 %** de las 138 501 del
grafo, y lo son porque **su formato de ORIGEN es uno de los 445 que ningún motor
local sabe ESCRIBIR** (`semi_entrada.json`, `estado == "no_materializable"`:
**359 de ffmpeg + 86 de ImageMagick**). Sin poder fabricar un fichero de ese
formato, la semiarista de entrada nunca se pudo probar.

Los tres escenarios de `aristas-nominales.md` §0:

| Escenario | Supuesto | Nominales | % |
|---|---|---:|---:|
| **A — cota inferior** | las 75 874 son **todas reales** | 31 530 | **22,8 %** |
| **B — central** | se comportan como las verificadas **de su motor** | 67 345 | **48,6 %** |
| **C — cota superior** | son todas nominales | 107 404 | **77,5 %** |

### 7.2 (a) Qué queda exactamente fuera

**350 formatos** (445 − 95) **sin un solo fichero real conocido en FATE.**

Lo cubierto son **95 de 445 (21,3 %)**: 69 de worker2 —emparejados por
subdirectorio de FATE con el mismo nombre— más 26 alias de worker11, cada uno
verificado con `ffprobe` **sin forzar formato** antes de usarlo, para no repetir
la colisión de nombre de las trampas 70/73. Por motor: **92 ffmpeg + 3
ImageMagick** (`heif`, `heic`, `3gp`).

| Nivel | n | criterio | resultado |
|---|---:|---|---|
| **Semiarista de entrada** | 95 orígenes | `rc==0 && bytes>0`, basta 1 destino vivo de `["mkv","wav","png"]` (`["png"]` en IM), tope 25 s | **91 VIVA = 95,8 %** |
| **Arista** (origen × destino) | 546 pares | el mismo, **NO** el contrato de 5 puntos | **365 buenas = 66,85 %** |

Las 4 muertas: `evc` (MPEG-5 EVC), `imf` (emparejamiento dudoso, declarado),
`asf_o` (falla en los tres destinos con *«Invalid data found»*) y `3gp` (sin
pista de vídeo).

**El sesgo, textual y sin diluir** (`fate-y-aristas.md` §2.2): *«Es un sesgo de
COBERTURA, no una muestra aleatoria: FATE organiza sus subdirectorios por
decodificador, y los formatos que tienen nombre propio en FATE tienden a ser los
que alguna vez motivaron un caso de prueba dedicado — es decir, formatos con
implementación más madura y más probada»*. Al doblar la `n`, el sesgo **se
confirma en vez de diluirse**: los 24 alias de ffmpeg son mayoritariamente
formatos de videojuegos antiguos (Interplay, Delphine, Bethsoft, Westwood…), la
misma categoría.

**Y el número se mueve al ampliar, y se publica movido**: 97,1 % (n=69) →
**95,8 %** (n=95). Sigue muy por encima del 48,6 % de Escenario B.

### 7.3 (b) Cuánto costaría pasar del techo, y con qué fuente

**Vía 1 — más alias dentro de FATE.** El *fuzzy-match* de worker11 encontró 26
alias sobre 376 candidatos: **tasa de acierto del método, 6,9 %**. Extrapolando
—y `fate-completo.md` §2.5 lo declara **proyección, no medición**— saldrían
**~24 alias más** con el mismo esfuerzo sobre los 350. Eso llevaría la cobertura
de 95 a ~119 de 445 (**~27 %**) y **no cierra nada**: el resto de los 350 no
tiene fichero en FATE porque FATE no los tiene, y para 4 de ellos está
diagnosticado por qué (`dzi`, `nia`, `nii`, `pml` **no son códecs de
audio/vídeo**: FATE es el corpus de conformidad de ffmpeg y no tiene ni un
fichero de esos tipos entre sus 2 529).

**Vía 2 — bancos de muestras por formato, uno a uno.** Es la única nombrada en
los tres sitios donde se ha escrito (`fate-y-aristas.md` §2.5,
`aristas-nominales.md` §7, `HUECOS.md`), y **en ninguno tiene coste medido**.
Sobre 350 formatos exóticos, cada uno con su fuente distinta, es trabajo lineal
en el número de formatos sin economía de escala. **Ésa es la razón de fondo por
la que `C16` es un techo y no una tarea.**

**Vía 3 — aceptar el sesgo de cobertura como definitivo**, que es la que el
propio informe pone al lado de la 2. No cuesta nada y es lo que la afirmación de
§7.4 hace explícito.

### 7.4 (c) La afirmación que se puede publicar hoy, redactada para pegar

> **`C16` — cota inferior con su sesgo declarado, no un 54,78 % pendiente de
> medir.** De los **445** formatos que ningún motor local sabe escribir —y que
> por eso dejan **75 874 aristas (54,78 %) sin veredicto**—, **95 (21,3 %)
> tienen hoy dato con ficheros REALES de FATE**, no fabricados por el propio
> motor. Sobre esos 95: **semiarista de entrada 91/95 VIVA (95,8 %)** y
> **arista 365/546 (66,85 %)**, con criterio `rc==0 && bytes>0` — **más barato
> que el contrato de cinco puntos, y se declara**. Las dos cifras están **muy
> por encima del 48,6 % de Escenario B** y cerca del 77,5 % de Escenario C, lo
> que permite afirmar que **el 54,78 % indeterminado NO se comporta
> uniformemente como Escenario B supone**. **El sesgo es de cobertura y está
> declarado**: FATE nombra por decodificador, así que la muestra favorece a los
> formatos con soporte más maduro — y **al doblar la `n` de 69 a 95 el sesgo se
> confirmó en vez de diluirse** (los 24 alias nuevos son la misma categoría:
> videojuegos antiguos con caso de prueba dedicado). **Quedan 350 formatos sin
> un solo fichero real conocido**, y **ninguna descarga los cierra**: el mismo
> método daría ~24 alias más (proyección desde una tasa de acierto medida del
> 6,9 %, no una medición), y el resto exige **bancos de muestras formato a
> formato, cuyo coste no está medido en ningún sitio del repositorio**.

---

## 8. Lo que propongo al maestro — no lo he escrito yo en los ficheros que gobiernan

**No he tocado `ESTADO-Y-REPARTO.md` ni `CLAUDE.md`**, como pedía el encargo.
Aquí va el texto para que el maestro consolide.

### 8.1 Fila `C36`

> **TRES DE LOS CINCO RESTANTES, CERRADOS el 04/09/2026 por worker2**
> (`bench/mcp-cabos-y-techos.md`, ronda 14). **Ítem 2 — qué le pasa a `roots` en
> 2026-07-28**: MEDIDO ejecutando el SDK, no leyendo la especificación —
> `ServerSession.list_roots` está `@deprecated` con *«The roots capability is
> deprecated as of 2026-07-28 (SEP-2577)»* y **`filex.mcp.construir()` emite hoy
> ese aviso**, 1 contra **0** del control sin `on_roots_list_changed`. No hay
> capacidad sustituta: se retira el **canal** —la petición del servidor a media
> llamada— y lo que queda es el *resolver* `Resolve(ListRoots)`, cuyo transporte
> ≥2026-07-28 **batea en un `InputRequiredResult` y re-ejecuta el cuerpo en cada
> ronda**, que es literalmente el ítem 6. **Ítem 6 — idempotencia**: la caché de
> roots cumple (**1** `roots/list` por sesión, comprobado por ejecución sobre el
> manejador real de `Server._request_handlers`), y **FileX no puede sufrir hoy la
> doble ejecución por una razón que §13 no daba: el SERVIDOR** —`lowlevel` no
> exporta ninguna de las 4 piezas de `Resolve`, `mcpserver` las cuatro—, no sólo
> el cliente. Y aparece **un fallo real, ARREGLADO**: un fallo transitorio de
> `roots/list` dejaba `sin_acceso=True` sellado con `_resuelto=True`, y el
> reintento **no volvía a preguntar** (1 llamada, no 2) — sesión denegada para
> siempre, con el mensaje opaco de R1/R4 disfrazándolo de denegación legítima
> (trampa 43). **Ítem 5 — subsunción**: la regla de §4.4 tiene dos conjuntos y
> sólo el del esquema es automatizable; contra las 27 de `video-audio-mcp` (13
> casos particulares de 2) el predicado estricto atrapa **2/13** y el relajado
> **13/13 con 1 falso positivo irreducible** (`trim_video`→`add_image_overlay`,
> mismo `start_time`/`end_time` con significados distintos). **FileX: 0 parejas
> con las dos variantes**, con prueba hermética y sus dos controles. **Ítem 3
> queda instrumentado y PENDIENTE** (`Raices.emisiones` + `FILEX_MCP_REGISTRO_ROOTS`;
> no se fabrica una emisión que no ocurre) y **el ítem 1 queda fuera y
> declarado**. Quedan **dos**: repetir §4 con otro modelo y n≥10, y observar la
> emisión real.

### 8.2 Fila `C28` — el texto de §6.4, tal cual

### 8.3 Fila `C16` — el texto de §7.4, tal cual

### 8.4 Dos filas NUEVAS que propongo abrir

> **`Cxx` — la caché de roots no es segura en la primera llamada concurrente.**
> MEDIDO (`bench/mcp-cabos-y-techos.md` §2.4): el `threading.Lock` de
> `Raices.asegurar()` se suelta **antes** del `await`, así que N herramientas que
> entren a la vez con la caché fría hacen **N** `roots/list` — **2 de 2**
> medidas, con el control negativo del arnés a 1. No es un fallo de corrección;
> es un coste lineal en el paralelismo del modelo. **No arreglado a propósito**:
> el arreglo natural es sostener el candado a través del `await`, y eso cambia
> el primitivo por uno de `anyio` con riesgo de interbloqueo.

> **`Cxx` — Tasks (SEP-1686) existe entero en `mcp 2.0.0`, y `PLAN-ORQUESTADOR.md`
> §5.3 lo da por eliminado.** MEDIDO: `tasks` es campo de `ClientCapabilities` y
> de `ServerCapabilities`, `mcp_types` exporta **30** tipos de tarea, ninguno de
> los cinco sondeados está deprecado, y **`TaskStatus` =
> `working|input_required|completed|failed|cancelled`** — cuatro de los cinco
> estados son los que `job` inventó a mano. **El matiz que impide llamarlo
> refutación:** los siete docstrings sondeados dicen «(2025-11-25 only)», que es
> justo la versión que Claude Code negocia. **PENDIENTE**: medir si un `convert`
> largo se puede entregar como `Task` nativo, y qué costaría en catálogo.

### 8.5 Corrección propuesta a la trampa 72 de `CLAUDE.md`

No propongo una trampa nueva por esto: propongo **enmendar la 72**, que hoy
publica una partición que no suma. Texto sugerido para el paréntesis final:

> *(**Y el recuento de esta trampa está incompleto: las cinco clases suman 42,
> no 56.** La partición completa es de **ocho** y está en `firmas-cierre.md`
> §4.4 — faltan **8 sin clasificar**, **4 que el motor no sabe escribir**
> (vips) y **2 `AVERROR_INVALIDDATA`**. Es la trampa 48 sobre otro recuento, y
> sobrevivió un mes porque nadie sumó los sumandos que la propia trampa
> enumera.)*

### 8.6 Trampa nueva que propongo, si el maestro la quiere

> **112. Un `async def` sin un solo `await` dentro NO cede el bucle de eventos,
> así que un arnés de concurrencia escrito con dobles mide su doble y sale
> verde — MEDIDO el 04/09** (`bench/mcp-cabos-y-techos.md` §2.4). Dos
> herramientas MCP lanzadas «a la vez» contra una caché de roots fría daban
> **1** sola ida y vuelta, que es exactamente el resultado que confirmaba la
> hipótesis cómoda —*la caché aguanta la concurrencia*—. Era del arnés: el
> `list_roots` falso no tenía punto de suspensión, así que las dos corrutinas
> corrieron **en serie**. Con un `await` donde un `roots/list` real —una ida y
> vuelta por el cable— lo tendría, salen **2 de 2**, y la caché resulta **no ser
> segura en la primera llamada concurrente**. **Lo único que lo destapó fue un
> contador de entradas simultáneas dentro del propio doble**, que valía 1 donde
> la prueba necesitaba 2: es la trampa 38 —*registra si la condición que dices
> reproducir se dio*— trasladada de los procesos a las corrutinas, donde el
> punto de suspensión es invisible y **la ausencia de `await` no da ningún
> error**. **Todo arnés de concurrencia asíncrona necesita un control negativo
> sin cesión al lado: si las dos celdas dan lo mismo, la de arriba no midió
> concurrencia.**

---

## 8bis. El estado de la suite y de `ci/integridad.py`, con sus cuatro declaraciones

**`ci/integridad.py` sobre esta rama: 8 de 9 en verde.** La que falla es
`informes-registrados`, y falla **a propósito**: exige que este informe esté
citado en la tabla de §1 de `ESTADO-Y-REPARTO.md`, y el encargo prohíbe
expresamente tocar ese fichero porque hay otro worker en paralelo. **Se cierra
sola en cuanto el maestro pegue la fila de §8.1.** Las otras ocho —citas (49
vivas, 0 muertas), inventario, un-emoji-por-fila, trampas, manifiestos, secretos,
binarios, en-curso— pasan.

**La suite**, con las cuatro declaraciones que exigen las trampas 94 y 101:

| Declaración | Valor |
|---|---|
| **Intérprete** | `.venv-mcp-filex\Scripts\python.exe`, **3.11.9, win32** |
| **Entorno** | **Docker levantado** (`29.4.3`) |
| **Resultado** | **489 pruebas, 299,4 s, 2 fallos, 3 saltadas** |
| **Qué quedó fuera** | 3 saltadas, todas declaradas de antes: el ráster ausente de `salidas-hito6`, `FILEX_PRUEBAS_SIDECAR=1`, y una del catálogo sin `tiktoken` |
| **Estado de la máquina** | **NO despejada.** Otro worker en el carril GPU |

**Los dos fallos no son míos, y hay traza para decirlo** (trampa 111: *un motivo
se escribe con la traza del sujeto delante*):

1. **`test_bitrate_y_lock.test_la_guardia_no_se_repite_en_la_reentrada`** —
   `gpu.Lock("lote").tomar(espera=5)` devuelve `False`. El fichero de lock dice
   quién lo tiene: **`B3-sonda-vllm`, PID 20220, worktree
   `agent-aba8566b66697c12b`**, que es el otro worker. Es la **trampa 101 (a)
   literal**: *«No es un fallo: es C38 funcionando»*.
2. **`test_watcher_n.test_proc_ve_al_escritor_y_replace_no`** — `rc=4294967295`
   con *«Código de error: Wsl/Service/0x8007274c»*: **WSL2 no arrancó**. Estado
   de máquina, no código.

**Y el control que la trampa 101 exige antes de culpar a un cambio:** mi diff
toca **exactamente dos ficheros**, `filex/mcp.py` y `pruebas/test_hito4.py`, y
**ninguna de las dos pruebas caídas menciona `mcp` ni una vez** (`grep -c mcp` →
**0** en los dos ficheros). `pruebas/test_hito4.py` corre en **39 pruebas, 1
saltada, 0 fallos**, y `test_sondeo` pasa: **el arreglo de `filex/mcp.py` no
caduca ninguna arista**, porque `mcp.py` no entra en la huella de ningún motor.

---

## 9. Índice de la evidencia

| Fichero | Qué es |
|---|---|
| `salidas-mcp-cabos-techos/sonda_protocolo.py` → `protocolo.json` | §1. El SDK ejecutado: versiones, deprecaciones, avisos de FileX con su control negativo, capacidades, Tasks |
| `salidas-mcp-cabos-techos/subsuncion.py` → `subsuncion.json` | §3. El comprobador, el catálogo de FileX y el control positivo de las 27 de `video-audio-mcp`, con las dos variantes del predicado |
| `salidas-mcp-cabos-techos/sonda_idempotencia.py` → `idempotencia.json` | §2. M0–M4 sobre el manejador real, con el control negativo del arnés en M4 |
| `salidas-mcp-cabos-techos/idempotencia_antes.json` | §2.3. La misma sonda **antes** del arreglo: la denegación permanente, medida |
| `filex/mcp.py` | El arreglo de M3 y la instrumentación del ítem 3 |
| `pruebas/test_hito4.py` | Clases `Subsuncion` (3) y `RootsCacheYFallo` (5) |
