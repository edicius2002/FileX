# `Tasks` (SEP-1686) contra el `job_id` propio — qué existe de verdad en `mcp 2.0.0`

**Fila `C48`.** worker4, carril CPU, ronda 15, 04/09/2026.
Salidas y arneses en `bench/salidas-tasks-protocolo/`.

**Encargo:** `bench/mcp-cabos-y-techos.md` §8 (worker2) midió que *«`Tasks` existe entero
y sin deprecar en `mcp 2.0.0`»* mientras `PLAN-ORQUESTADOR.md` §5.3 lo da por eliminado.
Si el protocolo trae el mecanismo, el `job_id` de FileX **puede ser una reimplementación**.

---

## 0. El resultado en cuatro líneas

1. **`PLAN-ORQUESTADOR.md` §5.3 tiene razón en lo que decide, y su origen se reproduce
   entero — MEDIDO.** El mecanismo de Tasks **no existe** en `mcp 2.0.0`: cero
   `enable_tasks`, cero `TaskStore`, cero módulos `experimental`.
2. **El hallazgo de worker2 estaba ya escrito —y declarado sin valor— en el informe que
   creía refutar.** `bench/sdk-mcp-capacidades.md` §3.2 dice literalmente: *«están los
   tipos y no está el mecanismo; un `hasattr(types,'CreateTaskResult')` da `True` en 2.0.0
   y no significa nada»*.
3. **Pero §5.3 acierta el hecho y yerra la causa (trampa 58), y hay un hecho nuevo que
   ninguno de los dos midió:** el mecanismo **se puede reconstruir a mano** sobre
   `mcp 2.0.0` — `tasks/get`, `tasks/list` y `tasks/cancel` **servidos de punta a punta**,
   `rc=0`. Lo que lo mata no es el SDK: es el **cliente**.
4. **Claude Code 2.1.260 NO declara la capacidad `tasks` — MEDIDO contra el cliente real.**
   Declara `roots` y `elicitation`, y nada más. Un `Task` nativo sería **código muerto**.

**Recomendación, con el número delante: mantener el `job_id` propio.** Migrar ahorra
**153 tokens de catálogo (9,27 %)** y compra una superficie que **0 de 1 clientes medidos**
puede usar; y la mitad cara —persistencia en disco, matar el árbol de procesos, TTL— **hay
que escribirla igual**, porque la CLI, el watcher y la API no hablan MCP.

---

## 1. Qué dice §5.3, y por qué lo dice — el origen, REPRODUCIDO

Antes de llamar falsa una afirmación ajena hay que reproducir su medida y sondear su
mecanismo (trampa 58). El texto vigente es:

> **Tasks (SEP-1686) fue ELIMINADO de la especificación** — el propio SDK lo avisa. Existió
> en `1.23.0`-`1.29.0` y funcionaba entero; ya no está.

El origen es **`bench/sdk-mcp-capacidades.md` §3.1 y §3.2**, y no es una lectura de la
especificación: es un aviso que el propio SDK 1.29.0 emitió al usar la API
(`r_tasks_129.json`, campo `avisos`):

```
DeprecationWarning: The experimental tasks API is deprecated and will be removed in mcp 2.0:
tasks (SEP-1686) were removed from the MCP specification and are expected to return as a
separate MCP extension.
```

§3.2 acompañó el aviso con cuatro comprobaciones sobre el paquete instalado. **Las cuatro se
reproducen hoy sobre `mcp 2.0.0` — MEDIDO** (`sonda_tasks.json`, sección `S2_mecanismo`):

| Comprobación de §3.2 | Hoy | Cómo |
|---|---|---|
| `mcp/client/experimental/` | `ModuleNotFoundError` | `importlib.import_module` |
| `mcp/server/experimental/` | `ModuleNotFoundError` | ídem |
| `mcp/shared/experimental/tasks/` | `ModuleNotFoundError` | ídem |
| `grep -rn "tasks/" mcp/ --include=*.py` | **1 línea**, y es un *docstring* (`mcp/server/extension.py:59`) | `grep` |

Y **tres comprobaciones más que §3.2 no hizo**, todas MEDIDAS, todas en la misma dirección:

- `grep -rn "enable_tasks\|TaskStore\|task_store" mcp/` → **0 líneas**.
- `Server.experimental` → `False`; `Server.enable_tasks` → `False`.
- `[a for a in dir(Server) if "task" in a.lower()]` → **`[]`**, lista vacía.

**Veredicto sobre §5.3: el hecho que decide —no hay mecanismo— es cierto y se sostiene.**
No es un texto caducado por dejadez.

---

## 2. Qué es `Tasks` exactamente, sondeado en ejecución

Sonda: `bench/salidas-tasks-protocolo/sonda_tasks.py` → `sonda_tasks.json`.
Entorno: `mcp 2.0.0`, `mcp-types 2.0.0`, Python **3.11.9 win32**, `.venv-mcp-filex`.

### 2.1 La pieza que separa las dos lecturas: `Tasks` es de UNA era

`mcp_types 2.0.0` trae **dos** módulos de era, y los tipos de tarea viven en uno solo
— **MEDIDO** (`S4_por_era`):

| | `_v2025_11_25` | `_v2026_07_28` |
|---|---:|---:|
| Tipos con `Task` en el nombre | **18** | **0** |
| `ServerCapabilities.tasks` es campo declarado | **sí** | **no** |
| `ClientCapabilities.tasks` es campo declarado | **sí** | **no** |
| Campo nuevo de la era | — | **`extensions`** (SEP-2133) |

`LATEST_PROTOCOL_VERSION` = **`2026-07-28`**; `DEFAULT_NEGOTIATED_VERSION` = `2025-03-26`.

**Aquí está el malentendido, y es un malentendido honesto.** `mcp.types` no reexporta una
era: reexporta el módulo **agregado** `mcp_types._types`, que es la **unión** de las dos.
Sobre el agregado, `ServerCapabilities.model_fields` contiene `tasks` **y** `extensions`
a la vez — un estado que ninguna era real tiene. Los **30** tipos que worker2 contó salen de
ahí. **MEDIDO.**

### 2.2 «Ninguno está deprecado» no es evidencia — y hay control positivo

worker2 sondeó cinco tipos y ninguno traía marca de deprecación. Es verdad, y no significa
lo que parece, por dos motivos MEDIDOS:

1. **El SDK sí marca lo que quiere marcar.** Control positivo del mismo arnés (`S6_control`):
   `ServerSession.list_roots.__deprecated__` → **`True`**. Donde el SDK retira algo de la
   **API**, lo marca. Los tipos de tarea no son API retirada: son **tipos de cable de una
   era anterior**, que se conservan para poder hablarla.
2. **Los propios docstrings lo dicen, y worker2 los cita:** *«(2025-11-25 only)»* en 4 de los
   5 sondeados. El quinto, `TaskStatus`, ni siquiera es una clase:
   `typing.Literal['working','input_required','completed','failed','cancelled']`. **Preguntar
   si un `Literal` está deprecado no tiene respuesta.**

**Lo que sí es un hallazgo real de worker2, y se confirma:** cuatro de los cinco estados de
`TaskStatus` son exactamente los que `job` inventó a mano. El **quinto, `input_required`, no
existe en `job`** — y es el único que un `convert` podría llegar a necesitar (una
elicitación a mitad de conversión). Queda anotado en §7.

### 2.3 Qué negocia Claude Code HOY — el cliente real, no el SDK

worker2 midió `2025-11-25` contra **Claude Code 2.1.238**. El cliente de esta máquina hoy es
**2.1.260**, 22 versiones más tarde, así que la medida podía estar caducada. **Se repitió.**

Arnés: `srv_sonda_initialize.py` — un servidor MCP de **JSON-RPC crudo, sin el SDK a
propósito**: con el SDK por medio se mide el SDK, no el cliente. Lanzado por un `claude -p`
real con `--mcp-config` y `--strict-mcp-config`, tope de 240 s **dentro de la orden**.

**Resultado — MEDIDO** (`r_cliente_2_1_260.jsonl`, la sesión completa son 6 líneas):

```json
{"method":"initialize","params":{
  "protocolVersion":"2025-11-25",
  "capabilities":{"roots":{"listChanged":true},"elicitation":{}},
  "clientInfo":{"name":"claude-code","version":"2.1.260"}}}
```

- **Negocia `2025-11-25`** — reproduce a worker2 22 versiones después. La medida no estaba
  caducada.
- **`tasks` NO está entre las capacidades del cliente.** Declara `roots` y `elicitation`.
  **Éste es el negativo que decide la fila.** Por SEP-1686, un cliente que no declara `tasks`
  no sondea tareas: no llamaría nunca a `tasks/get`.
- **El servidor declaró `tasks` a propósito** (`{"list":{},"cancel":{},"requests":{"tools":{"call":{}}}}`)
  **y el cliente lo toleró**: siguió con `notifications/initialized` y `tools/list`.
  Declararlo es **inofensivo e inútil**.

### 2.4 Qué pasa si el cliente no lo soporta — y un modo de fallo que no esperaba

La celda B ofrece la era **nueva**: el servidor responde `protocolVersion: 2026-07-28` a un
cliente que pidió `2025-11-25` (`cfg_sonda_2026.json` → `r_cliente_2026.jsonl`).

**El cliente ABANDONA EN SILENCIO — MEDIDO.** La sesión se queda en 4 líneas: llega el
`initialize`, se responde, y **no llega `notifications/initialized` ni `tools/list`**. No hay
error por pantalla, y **`claude -p` contesta `LISTO` igual**: el usuario obtiene una respuesta
normal y **cero herramientas**, sin que nada se queje.

Refuerza la conclusión de §5.3 —*construir sobre `mcp>=2.0.0` es correcto porque negocia
hacia abajo*— y le pone el precio del error: **el castigo por negociar hacia arriba no es un
error, es la desaparición muda del servidor.** Es la forma de la trampa 25 sobre el
protocolo: dos causas distintas (servidor caído / servidor descartado) con la misma pinta.

---

## 3. ¿Se puede entregar un `convert` largo como `Task` nativo?

**Sí en el servidor, no en el cliente. Y el «no» manda.**

### 3.1 En el servidor: el mecanismo se reconstruye a mano — MEDIDO de punta a punta

Esto es un hecho **nuevo**: `sdk-mcp-capacidades.md` §3.2 midió que el mecanismo no está,
pero no midió si se puede rehacer. Se ha medido, ejecutando.

`sonda_viabilidad_codigo.json`:

- El registro de métodos del `Server` de bajo nivel es **abierto**:
  `add_request_handler(method: str, params_type: type, handler)`.
  De serie sólo trae `ping` y `server/discover`.
- Los cuatro métodos del SEP **se registran** con los tipos de parámetros de la era
  2025-11-25 (`GetTaskRequestParams`, `GetTaskPayloadRequestParams`,
  `PaginatedRequestParams`, `CancelTaskRequestParams`).
- Los tipos **validan**: `Task` exige `taskId`, `status`, `createdAt`, `lastUpdatedAt`,
  `pollInterval`, `ttl`.

*(Primer intento fallido y declarado: llamé a `add_request_handler` con dos argumentos y dio
`TypeError`. La firma pide tres. Segundo intento, correcto.)*

**Y «registrable» no es «servido», así que se sirvió** — `srv_tasks_20.py` (servidor
`mcp 2.0.0` con los manejadores a mano) contra `cli_tasks_20.py` (cliente JSON-RPC crudo),
tope de 30 s dentro del arnés:

| Método | Respuesta | |
|---|---|---|
| `initialize` | `protocolVersion: 2025-11-25` | ok |
| `tools/list` | 1 herramienta | ok |
| `tasks/get` | `{taskId:"t-42", status:"working", pollInterval:1000, ttl:60000}` | **ok** |
| `tasks/list` | 1 tarea | **ok** |
| `tasks/cancel` | `{taskId:"t-42", status:"cancelled"}` | **ok** |

`rc=0` del servidor, `stderr` vacío. **MEDIDO.**

### 3.2 El agujero que lo hace inservible aunque funcione

**El servidor sirve `tasks/*` y no los ANUNCIA — MEDIDO.** El `initialize` de ese mismo
servidor devuelve:

```json
"capabilities": {"experimental": {}, "tools": {"listChanged": false}}
```

`create_initialization_options()` deriva las capacidades de los manejadores que el SDK
conoce, y **`tasks` no está entre ellos**: sobre un `Server` pelado emite
`{"experimental":{}, "extensions":{}}`. Habría que **pisar** las capacidades a mano para que
un cliente pudiera descubrirlas.

Así que la cadena completa tiene tres eslabones y **fallan dos**:

| Eslabón | Estado |
|---|---|
| Servir `tasks/*` | **funciona** (medido) |
| Anunciar la capacidad | **hay que pisarlo a mano** (medido: no se emite) |
| Que el cliente la pida | **no ocurre** — 2.1.260 no declara `tasks` (medido) |

### 3.3 Y la era de destino lo borra en silencio

`ServerCapabilities` de `_v2026_07_28` **no tiene campo `tasks`**, y construirla con `tasks`
**se acepta y el campo se descarta sin avisar** (`V5_era_2026`:
`"ACEPTADO (campo ignorado o extra)"`). El día que Claude Code pase de era, un servidor que
anunciara tareas **dejaría de anunciarlas sin un solo error**. La vía de vuelta declarada por
el SDK es SEP-2133 (`extensions`, campo nuevo de esa era). **PENDIENTE:** si llega y cuándo.

---

## 4. El coste, con el número

### 4.1 Catálogo — MEDIDO, tres escenarios en la MISMA tanda

Método idéntico al canónico de `bench/salidas-hito4/h4_tokens_catalogo.py`:
`tiktoken`/`o200k_base` sobre el catálogo serializado **como viaja por el cable**
(`model_dump(exclude_none=True, by_alias=True)`). Determinista, sin modelo: no hay ruido que
declarar. Arnés: `coste_catalogo_tasks.py` → `coste_catalogo_tasks.json`.

| Escenario | Herramientas | Tokens | Δ |
|---|---:|---:|---:|
| **E0 — hoy** (`job` incluida) | 5 | **1 650** | — |
| **E1 — migrar** (se retira `job`) | 4 | **1 497** | **−153 (−9,27 %)** |
| **E2 — soportar los dos** (`job` + `execution.taskSupport` en `convert` y `batch`) | 5 | **1 672** | **+22 (+1,33 %)** |

Desglose de E0: `convert` 669 · `batch` 375 · `list_targets` 322 · `job` **153** ·
`inspect` 129. Control aislado (trampa 36: se mide el trozo, no la diferencia entre dos
totales que lo contienen): `"execution": {"taskSupport": "optional"}` = **10 tokens**.

**Salvedad obligada (trampa 59).** El encargo cita **1 605 tokens con 215 aristas**
(`bench/gotenberg-y-mcp.md`), y mi E0 da **1 650**. **La diferencia está atribuida, no
excusada:** mi registro tiene **232 aristas, 34 orígenes, 34 destinos, 6 motores** frente a
215/30/29/6. El catálogo genera sus `enum` del registro, así que **+17 aristas → +45 tokens**
(≈ 2,6 tokens por arista). No es una discrepancia de método, y los tres escenarios de arriba
son **de la misma tanda**, así que los deltas (−153, +22) sí son comparables entre sí.

*(De propina, y no es de esta fila: el presupuesto de **≤1 200 tokens** de `CLAUDE.md` §5
está superado en 450 y **crece con el registro**. No es constante.)*

### 4.2 Código

Lo que habría que escribir sobre `mcp 2.0.0`, todo MEDIDO como viable en §3.1:

1. Cuatro manejadores (`tasks/get`, `tasks/result`, `tasks/list`, `tasks/cancel`).
2. Un almacén de tareas con TTL.
3. **Pisar las capacidades** para anunciar `tasks`, que el SDK no emite.
4. Una rama por era: en `2026-07-28` nada de esto existe y se descarta en silencio (§3.3).

**Y lo que NO se ahorra, que es la mitad cara.** §5.3 pide además que *«el estado del trabajo
se persista en disco, no en memoria de la sesión»*, y que *«`job_cancel` mate el árbol de
procesos»*, y que **los cuatro frentes vean el mismo trabajo**. `Tasks` sustituye el
**transporte** del asa, no el almacén: la CLI, el watcher y la API **no hablan MCP**, así que
el JSON por trabajo en disco hay que escribirlo igual. **Migrar no borra una pieza; añade
una.**

### 4.3 Dependencias — la línea que lo permitiría (trampa 80)

*Antes de proponer nada hay que escribir la línea de `pyproject.toml` o de `CLAUDE.md` que lo
permitiría; si no existe, lo que se mide es una decisión de arquitectura.*

**Aquí no hace falta ninguna línea nueva, y está comprobado:**

- `pyproject.toml` declara **`dependencies = []`**. Literalmente cero.
- `filex/mcp.py` importa `mcp` **de forma perezosa, dentro de `construir()`**
  (`import mcp.types as t`, línea 546), no en la cabecera del módulo. La superficie MCP es
  opcional por construcción.
- Los tipos de tarea **no son un paquete aparte**: `mcp-types==2.0.0` es dependencia
  **fijada** de `mcp` (`Requires-Dist`), así que llegan con él.

**Conclusión de la trampa 80: la propuesta es escribible sin tocar `pyproject.toml`.** No es
una decisión de arquitectura disfrazada de medida. *(Lo cual, si acaso, hace más honesto el
«no»: no rechazo Tasks porque no quepa, lo rechazo porque no sirve.)*

---

## 5. La recomendación, con el número delante

> ### **Mantener el `job_id` propio. No migrar, y no soportar los dos todavía.**

| Opción | Qué cuesta | Qué compra | |
|---|---|---|---|
| **Mantener `job`** | 153 tokens (9,27 % del catálogo) | Funciona en las tres eras y en las cuatro superficies | ✅ |
| **Migrar a `Task` nativo** | **−153 tokens**, y 4 manejadores + almacén + capacidades pisadas | **Nada hoy**: 0 de 1 clientes medidos declara `tasks` | ❌ |
| **Soportar los dos** | **+22 tokens (+1,33 %)** y todo el código de arriba | Una ruta que **0 clientes** ejercitan | ❌ *todavía* |

**El número que decide no es el de tokens: es el `0` de `capabilities`.** Ahorrar 153 tokens
retirando `job` deja a FileX sin asa para trabajos largos frente al único cliente medido, que
es exactamente el fallo que §5.2 documenta con evidencia (un clip de 5 s que superó los 900 s
de timeout y perdió un resultado que estaba hecho en disco).

**Lo que sí se conserva de SEP-1686, y ya está hecho: el VOCABULARIO.** §5.3 lo prescribió y
`job` lo cumple en 4 de 5 estados. Es la decisión barata y correcta: copiar la forma sin
depender del mecanismo.

**Cuándo volver a mirarlo.** Cuando un cliente declare `tasks` en su `initialize`. **La
comprobación cuesta una ejecución de ~7 s** y está escrita:

```sh
claude -p "Responde solo con la palabra LISTO." \
  --mcp-config bench/salidas-tasks-protocolo/cfg_sonda.json --strict-mcp-config --max-turns 1
```

y se lee el `capabilities` del `initialize` en el `.jsonl`. **No hace falta tocar `filex/`
para vigilarlo.**

---

## 6. Qué queda refutado, y de quién

**De worker2 (`bench/mcp-cabos-y-techos.md` §8.4), parcialmente:**

- *«`Tasks` existe **entero** y sin deprecar en `mcp 2.0.0`»* → **la palabra «entero» es
  falsa.** Existen los **tipos de cable de una era**; el **mecanismo** da 0 en las siete
  comprobaciones de §1. Y worker2 tuvo el matiz delante —citó los docstrings
  *«(2025-11-25 only)»*— y no lo llevó hasta el final.
- *«ninguno de los cinco sondeados está deprecado»* → **cierto y sin valor probatorio**,
  con control positivo: el SDK **sí** marca `ServerSession.list_roots` como deprecado. Y uno
  de los cinco es un `typing.Literal`.
- **worker2 hizo lo correcto al no llamarlo refutación** («el matiz que impide llamarlo
  refutación»). La fila `C48` se abrió bien; lo que sobraba era la palabra «entero».

**De `PLAN-ORQUESTADOR.md` §5.3 — el hecho aguanta, la causa se queda corta (trampa 58):**

- *«fue eliminado de la especificación»* es **cierto para `2026-07-28`** y **falso para
  `2025-11-25`**, que es **justo la era que Claude Code negocia**. El texto no declara su era,
  y por eso worker2 pudo leerlo como falso sin equivocarse del todo.
- Y el motivo operativo por el que FileX no puede usarlo hoy **no es el de §5.3**: no es que
  la especificación lo quitara, es que **el SDK no trae la maquinaria** *y* **el cliente no
  declara la capacidad**. Dos razones más fuertes y más comprobables que la que el plan da.

**De mí mismo, por si sirve de aviso:** entré esperando refutar §5.3 —el encargo lo sugería—
y lo que reprodujo la sonda fue el informe de hace dos semanas, palabra por palabra. **El
material que más ahorró trabajo fue `sdk-mcp-capacidades.md` §3.2, que ya había declarado
inútil la medida que yo venía a hacer.**

---

## 7. PENDIENTE, declarado

| Qué | Por qué no se cerró |
|---|---|
| **Si algún cliente declara `tasks`** | n=1 medido (Claude Code 2.1.260, no lo declara). No hay otro cliente MCP instalado en esta máquina |
| **Servir una tarea a un cliente que sí la pida** | No existe tal cliente aquí. El extremo de servidor está MEDIDO; el ciclo completo, no |
| **Si SEP-2133 (`extensions`) trae Tasks de vuelta, y cuándo** | Es futuro; `_v2026_07_28` ya tiene el campo `extensions` y ningún tipo de tarea |
| **El quinto estado, `input_required`** | `job` tiene 4 de los 5 de `TaskStatus`. Si FileX llegara a elicitar a mitad de conversión haría falta. Hoy no elicita |
| **Si `srv.run()` valida el método contra la era negociada** | Se midió que **responde** con un cliente crudo. Con un cliente estricto podría rechazarse antes de llegar al manejador |

---

## 8. Lo que propongo al maestro — no lo he escrito yo

**No he tocado `filex/`, `ESTADO-Y-REPARTO.md`, `CLAUDE.md` ni `PLAN-ORQUESTADOR.md`.**
`filex/mcp.py` es de worker3 en esta ronda y no lo he abierto más que para leerlo.

### 8.1 Texto corregido para `PLAN-ORQUESTADOR.md` §5.3, primer punto

Sustituye al *bullet* que hoy empieza por «**Tasks (SEP-1686) fue ELIMINADO…**»:

> - **Tasks (SEP-1686) no se puede usar hoy, y por DOS razones más fuertes que «lo quitaron
>   de la especificación» — MEDIDO el 04/09/2026** (`bench/tasks-protocolo.md`). **(a) El SDK
>   no trae el mecanismo:** en `mcp 2.0.0` no existen `mcp/{client,server,shared}/experimental`,
>   `grep -rn "enable_tasks\|TaskStore"` da **0 líneas** y `dir(Server)` no tiene un solo
>   atributo con `task`. **(b) El cliente no declara la capacidad:** Claude Code **2.1.260**
>   anuncia `roots` y `elicitation`, y **`tasks` no está** — un `Task` nativo sería código
>   muerto. **Lo que sí sigue existiendo son los TIPOS de cable, y sólo de la era
>   `2025-11-25`:** 18 tipos de tarea en `_v2025_11_25` y **0** en `_v2026_07_28`, donde
>   `ServerCapabilities` ya ni tiene el campo `tasks` —y construirla con él **lo descarta en
>   silencio**—. `mcp.types` reexporta el módulo **agregado** de las dos eras, así que
>   `hasattr(types, 'CreateTaskResult')` da `True` y **no significa nada**: es la unión, no la
>   era vigente. **Así que el `job_id` hay que construirlo entero:** `job_status` /
>   `job_result` / `job_cancel`, con el vocabulario de estado de SEP-1686
>   (`working`/`completed`/`failed`/`cancelled`; el quinto, `input_required`, no aplica
>   mientras FileX no elicite), un intervalo de sondeo sugerido por el servidor (~1.000 ms
>   para conversiones) y un TTL. **Y no es una reimplementación evitable:** el mecanismo **se
>   puede** rehacer a mano —los cuatro `tasks/*` se registran con `add_request_handler` y
>   **responden de punta a punta, `rc=0`**—, pero el SDK **no anuncia** la capacidad y el
>   cliente **no la pide**; y la mitad cara —persistir en disco, matar el árbol de procesos,
>   TTL— hay que escribirla igual, porque la CLI, el watcher y la API **no hablan MCP**.
>   **Coste medido de las tres salidas:** retirar `job` ahorra **153 tokens de catálogo
>   (9,27 %)**; soportar los dos cuesta **+22 (+1,33 %)**; mantenerlo cuesta 0 y es lo
>   recomendado. **Revisar cuando un cliente declare `tasks`** — la comprobación es una
>   ejecución de ~7 s y está escrita en `bench/salidas-tasks-protocolo/`.

### 8.2 Fila `C48` — texto para cerrarla

> **CERRADA el 04/09/2026 por worker4** (`bench/tasks-protocolo.md`). **Se mantiene el
> `job_id` propio.** `PLAN-ORQUESTADOR.md` §5.3 acierta el hecho y se queda corto en la causa
> (trampa 58): el mecanismo de Tasks **no existe** en `mcp 2.0.0` —cero `enable_tasks`, cero
> `TaskStore`, cero módulos `experimental`—, y lo que worker2 midió son los **tipos de cable
> de la era `2025-11-25`** (18 tipos allí, **0** en `_v2026_07_28`), reexportados desde el
> módulo **agregado** de las dos eras. Su *«ninguno está deprecado»* no prueba nada, con
> control positivo: el SDK **sí** marca `ServerSession.list_roots`. **El negativo que decide
> es del CLIENTE: Claude Code 2.1.260 —22 versiones después de la medida de worker2, y
> negociando el mismo `2025-11-25`— NO declara la capacidad `tasks`**, así que un `Task`
> nativo sería código muerto. **Hecho nuevo, MEDIDO de punta a punta:** el mecanismo **sí se
> puede rehacer a mano** (los cuatro `tasks/*` registrados con `add_request_handler` responden
> con `rc=0`), pero el SDK **no anuncia** la capacidad y la mitad cara —persistencia, matar el
> árbol, TTL— hay que escribirla igual porque CLI, watcher y API no hablan MCP. **Coste:
> migrar ahorra 153 tokens (9,27 %) y no compra nada; soportar los dos cuesta +22 (+1,33 %).**
> **Sin tocar `filex/` ni `pyproject.toml`** (trampa 80: `dependencies = []`, `mcp` se importa
> perezosamente y `mcp-types` viene fijado con él). PENDIENTE: que algún cliente declare
> `tasks`, y si SEP-2133 lo devuelve.

### 8.3 Trampa nueva que propongo, si el maestro la quiere

*(Va al final, nunca en medio. Si se acepta hay que mover el número en `README.md` y en §10
de `ESTADO-Y-REPARTO.md`; no lo he hecho porque no puedo tocar esos ficheros.)*

> **116. Un cliente MCP puede DESCARTAR un servidor en silencio, y el usuario recibe una
> respuesta normal con cero herramientas — MEDIDO el 04/09** (`bench/tasks-protocolo.md`
> §2.4). Respondiendo al `initialize` con `protocolVersion: 2026-07-28` a un Claude Code
> 2.1.260 que había pedido `2025-11-25`, la sesión **se corta después del `initialize`**: no
> llega `notifications/initialized` ni `tools/list`, no hay error por pantalla, y **`claude -p`
> contesta igual de bien** — sólo que sin herramientas. Con la era correcta, la misma sonda
> completa los seis pasos. **Es la trampa 25 sobre el protocolo**: «servidor caído», «servidor
> lento» y «servidor descartado por negociación» tienen exactamente la misma pinta desde
> fuera, y sólo un registro **del lado del servidor** las separa. Corolario que amplía la regla
> ya escrita de *«construir sobre `mcp>=2.0.0` porque negocia hacia abajo»*: **el castigo por
> negociar hacia ARRIBA no es un error, es la desaparición muda del servidor** — así que un
> servidor MCP debe **hacer eco de la versión que el cliente pide**, nunca ofrecer la suya, y
> **registrar su propio `initialize`**, que es lo único que distingue las tres causas.

### 8.4 Enmienda menor a `CLAUDE.md` §5, si se quiere

La línea *«El catálogo MCP llega DIFERIDO… el ≤1.200 tokens sigue valiendo como higiene de
nombres»* convive con un catálogo medido hoy en **1 650 tokens**, que **crece con el
registro** (≈2,6 tokens por arista: 215→232 aristas movieron 1 605→1 650). No propongo cambiar
la regla —es higiene, no presupuesto— pero **el número de al lado ya no es el de hoy**.

---

## 9. Índice de la evidencia

| Fichero | Qué es |
|---|---|
| `salidas-tasks-protocolo/sonda_tasks.py` / `.json` | Tipos vs mecanismo vs era. Secciones S0–S6 |
| `salidas-tasks-protocolo/srv_sonda_initialize.py` | Servidor MCP de JSON-RPC crudo que registra el `initialize` del cliente |
| `salidas-tasks-protocolo/cfg_sonda.json` → `r_cliente_2_1_260.jsonl` | Celda A: qué negocia Claude Code 2.1.260 |
| `salidas-tasks-protocolo/cfg_sonda_2026.json` → `r_cliente_2026.jsonl` | Celda B: el abandono silencioso al ofrecer `2026-07-28` |
| `salidas-tasks-protocolo/sonda_viabilidad_codigo.py` / `.json` | Si el registro de métodos es abierto y las capacidades se emiten |
| `salidas-tasks-protocolo/srv_tasks_20.py` + `cli_tasks_20.py` → `r_tasks_20.json` | `tasks/*` servido de punta a punta sobre `mcp 2.0.0` |
| `salidas-tasks-protocolo/coste_catalogo_tasks.py` / `.json` | E0/E1/E2 en tokens `o200k_base` |
| `salidas-tasks-protocolo/MANIFIESTO.md` | `sha256`, tamaño y orden exacta de cada uno |

**Evidencia ajena reproducida:** `bench/sdk-mcp-capacidades.md` §3.1, §3.2 ·
`bench/mcp-cabos-y-techos.md` §8.4 · `bench/gotenberg-y-mcp.md` (los 1 605 tokens) ·
`PLAN-ORQUESTADOR.md` §5.2, §5.3.

---

## 10. Las cuatro declaraciones del entorno

*(No corrí la suite: mi encargo es medida y diseño, y no toqué `filex/`. Declaro el entorno de
las mediciones, que es lo que hace falta para repetirlas.)*

| Declaración | Valor |
|---|---|
| **Intérprete** | `.venv-mcp-filex\Scripts\python.exe` — **3.11.9, win32** |
| **Entorno** | `mcp 2.0.0` · `mcp-types 2.0.0` · `tiktoken 0.14.0` · Claude Code **2.1.260**. Docker **no hace falta** para ninguna de estas medidas |
| **Qué quedó fuera** | La suite completa (no toqué código de producto) y lo listado en §7 |
| **Estado de la máquina** | No despejada: otros workers en la ronda 15. **Ninguna medida de aquí es de tiempo** — son deterministas (conteo de tokens, presencia de símbolos, contenido de un `initialize`), así que el ruido no las mueve. Los únicos milisegundos publicados son de traza, no de comparación |

**`ci/integridad.py` sobre esta rama: 8 de 9 en verde.** La que falla es
`informes-registrados`, y **falla a propósito**: exige que este informe esté citado en la
tabla de §1 de `ESTADO-Y-REPARTO.md`, y el encargo prohíbe expresamente tocar ese fichero.
**Se cierra sola en cuanto el maestro pegue la fila de §8.2.** Las otras ocho —citas (50
vivas, 1 ajena declarada, 0 muertas), inventario, un-emoji-por-fila, trampas (115, sin
huecos), manifiestos (**0 nuevos sin manifiesto**), secretos, binarios, en-curso— pasan.

*(Detalle de máquina, por si le pasa a otro: `ci/integridad.py` **revienta** en esta consola
sin `PYTHONIOENCODING=utf-8`, con `UnicodeEncodeError: 'charmap' codec can't encode
character '⚫'` al imprimir el `⚫` del inventario. Es del terminal `cp1252`, **no del
script**, y no es un fallo de la comprobación: es la trampa 25 en versión de consola —una
excepción que se parece muchísimo a «la comprobación está rota»—.)*

**No cito ningún commit de mi propia rama** (trampa 115): las únicas referencias de este
informe son a ficheros y a secciones de informes, que sobreviven al `--squash`.
