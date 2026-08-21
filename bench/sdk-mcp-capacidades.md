# Capacidades reales del SDK Python de MCP: *roots*, *tasks*/progreso e `ImageContent`

**Ejecución medida contra tres ramas del SDK instaladas en venvs nuevos.**
Fecha: 20 de agosto de 2026. Máquina: Windows 10 Home 19045, Python 3.11.9. Sin GPU.

Venvs creados para este informe (ninguno de los prohibidos fue tocado):
`.venv-mcp-sdk-18` (`mcp==1.8.1`), `.venv-mcp-sdk-1x` (`mcp==1.29.0`), `.venv-mcp-sdk-2x` (`mcp==2.0.0`).

Código y datos crudos: `bench/salidas-sdk-mcp/`.
Método: servidores y clientes MCP mínimos escritos para este informe, lanzados por stdio. El código
del SDK se ha leído **solo** donde la ejecución no daba la respuesta.

> **Convención del proyecto.** Cada afirmación va marcada **MEDIDO** (hay una salida literal en
> `bench/salidas-sdk-mcp/*.json` o `*.txt` que la respalda) o **PENDIENTE** (no se ha ejecutado).

---

## 0. Resumen ejecutivo

| Pregunta que bloqueaba una decisión | Respuesta medida |
|---|---|
| ¿Existe `session.list_roots()` en el servidor Python? | **Sí, en las tres ramas.** Pero en `mcp 2.0.0` sobre el protocolo **2026-07-28** revienta con `NoBackChannelError`. **MEDIDO** |
| ¿Llega `notifications/roots/list_changed`? | **Sí en 1.x y en 2.0.0-era-clásica. NO llega en 2.0.0 sobre 2026-07-28.** En 1.x **no hay decorador**: hay que registrar el handler a mano. **MEDIDO** |
| ¿Se pueden **intersecar** los roots? | **Sí, sin fricción: la API devuelve una lista y no toca nada.** Nada empuja a sustituir; sustituir es una decisión del programador, no del SDK. **MEDIDO** |
| ¿Qué pasa sin soporte de roots del cliente? | `McpError(-32600, 'List roots not supported')` **capturable**, la sesión sigue viva. Idéntico al `-32600` que escribió el servidor de Node. **MEDIDO** |
| **¿Es R13 implementable?** | **Sí. Con `mcp>=1.9.4` por el camino clásico; con `mcp==2.0.0` solo vía `MCPServer` + `Resolve(ListRoots)`.** Ver §2.6 |
| ¿Existe Tasks (SEP-1686) en el SDK? | **En `1.23.0`–`1.29.0` sí, como `experimental`, y funciona entero. En `2.0.0` está ELIMINADO.** El propio SDK dice que *«tasks (SEP-1686) fueron retiradas de la especificación»*. **MEDIDO** |
| ¿El progreso mantiene viva una llamada larga? | **NO.** Con 30 progresos entregados, la llamada venció igual en el plazo exacto. El plazo es absoluto (`anyio.fail_after`), el progreso no lo empuja. **MEDIDO** |
| **¿Hay que construir el `job_id`?** | **Sí, entero.** No hay nada en el protocolo estable en lo que apoyarse. Ver §3.6 |
| ¿Acepta `ImageContent` base64 puro? | **Sí. Y también el prefijo `data:`, y basura, y la cadena vacía.** El SDK **no valida base64 en ninguna rama**: `data: str` y nada más. **MEDIDO** |

---

## 1. Tabla de versiones: SDK → protocolo → capacidades

### 1.1 Las tres ramas medidas en ejecución

| SDK | `LATEST_PROTOCOL_VERSION` | Protocolo negociado consigo mismo | API de servidor | roots | progreso | Tasks SEP-1686 |
|---|---|---|---|---|---|---|
| `mcp 1.8.1` | `2024-11-05` | **2024-11-05** | `Server` (decoradores) + `FastMCP` | `session.list_roots()` **sí** | **cliente NO puede pedirlo** | no existe |
| `mcp 1.29.0` | `2025-11-25` | **2025-11-25** | `Server` (decoradores) + `FastMCP` | `session.list_roots()` **sí** | `call_tool(progress_callback=…)` **sí** | **sí, `experimental`, deprecado** |
| `mcp 2.0.0` | `2026-07-28` | **2026-07-28** | `Server` (handlers por constructor) + `MCPServer` | `session.list_roots()` **existe pero muere** en la era moderna | `ctx.session.report_progress()` **sí** | **eliminado** |

**MEDIDO** (`interop_*.json`, `r_129_*.json`, `r_200_*.json`).

En `mcp 2.0.0` los tipos ya no viven en `mcp/types.py`: se importan del paquete **`mcp_types` 2.0.0**,
una dependencia aparte. `mcp.types` es un reexportador. **MEDIDO**

### 1.2 En qué versión aparece cada cosa (acotado sobre las ruedas, sin instalar)

Script: `bench/salidas-sdk-mcp/sondear_wheels.py` (descarga con `pip download --no-deps` e
inspecciona el `.whl` como ZIP).

| Versión | Protocolo | `progress_callback` en `call_tool` | Capacidad `roots` declarada **solo** si hay callback | Tasks experimentales |
|---|---|---|---|---|
| 1.8.1 | 2024-11-05 | **no** | **no** (la declara siempre) | no |
| 1.9.0 | 2025-03-26 | **sí** | **no** | no |
| 1.9.4 | 2025-03-26 | sí | **sí** | no |
| 1.12.4 / 1.16.0 / 1.20.0 | 2025-06-18 | sí | sí | no |
| 1.21.0 / 1.22.0 | 2025-06-18 | sí | sí | no |
| **1.23.0** | 2025-06-18 | sí | sí | **sí** ← aquí entran |
| 1.24.0 … 1.28.1 | 2025-11-25 | sí | sí | sí |
| 1.29.0 | 2025-11-25 | sí | sí | sí (**deprecado**) |
| 2.0.0 | 2026-07-28 | sí (`progress_callback`) | sí | **no, eliminado** |

**MEDIDO.** Umbrales exactos: `progress_callback` **desde 1.9.0**; el arreglo de la capacidad `roots`
**entre 1.9.0 y 1.9.4**; Tasks **desde 1.23.0**; Tasks eliminadas **en 2.0.0**.

### 1.3 El fallo de `1.8.1` que explica la medición de Node

`mcp 1.8.1` declara la capacidad `roots` **siempre**, haya callback o no
(`client/session.py:118-124`, con un `# TODO` de los propios autores admitiéndolo). Consecuencia
medida en `r_181_sin_roots.json`:

```
t_roots_cap  -> {"roots": true, "roots.listChanged": true, ...}       <- MIENTE
t_roots      -> McpError(-32600, "List roots not supported")          <- la verdad
```

`check_client_capability()` devuelve **`true`** y la llamada real falla acto seguido. **MEDIDO.**

**Esto cierra un cabo suelto de `bench/mcp-refs-confinamiento.md` §1.1**: el
`Failed to request initial roots from client: MCP error -32600: List roots not supported` que el
servidor de Node escribió a stderr **no era un fallo del servidor de Node, era un falso positivo del
cliente del arnés** (`.venv-mcp-md`, `mcp 1.8.1`). El servidor preguntó porque el cliente había dicho
que sabía responder. Con `mcp>=1.9.4` el cliente ya no lo declara y el servidor **ni siquiera
pregunta**. **MEDIDO.**

### 1.4 Interoperabilidad entre procesos (cliente en un venv, servidor en otro)

Es la restricción que de verdad hereda FileX: FileX entrega un **servidor**; el cliente trae **su
propia** versión del SDK. Matriz completa, `t_ping` real en cada celda (`interop_*.json`):

| ↓ cliente \ servidor → | srv `1.8.1` | srv `1.29.0` | srv `2.0.0` |
|---|---|---|---|
| cli `1.8.1` | 2024-11-05 ✔ | 2024-11-05 ✔ | **2024-11-05 ✔** |
| cli `1.29.0` | 2024-11-05 ✔ | 2025-11-25 ✔ | **2025-11-25 ✔** |
| cli `2.0.0` | **✘ el servidor MUERE** | 2025-11-25 ✔ | 2026-07-28 ✔ |

**MEDIDO.** Dos lecturas, ambas importantes para FileX:

1. **Un servidor sobre `mcp 2.0.0` es compatible hacia atrás con clientes viejos.** Negocia
   2024-11-05 con un cliente 1.8.1 y 2025-11-25 con uno 1.29.0, y las herramientas responden.
   Construir sobre 2.0.0 **no** deja fuera a los clientes antiguos.
2. **Un servidor sobre `mcp 1.8.x` muere ante un cliente `2.0.0`.** El cliente moderno sondea
   `server/discover` antes del handshake; el servidor 1.8.1 no conoce el método, el `ValidationError`
   de pydantic contra la unión de peticiones **no está capturado**, el proceso cae y el cliente ve
   `MCPError(-32000, 'Connection closed')`. Traza literal en `stderr_interop_cli200_srv18.txt`:

   ```
   ListToolsRequest.method
     Input should be 'tools/list' [type=literal_error, input_value='server/discover', input_type=str]
   ```

   **No es una degradación elegante: es la caída del proceso servidor.** **MEDIDO.**

> Esto **refuerza** el dato ya conocido de que `mcp~=1.8.0` y `mcp>=2.0.0` no coexisten en un venv,
> pero lo desplaza: el problema de FileX no es empaquetar las dos, es que **fijar la rama vieja es
> una bomba de relojería**. `mcp~=1.8.0` está descartada para FileX por incompatibilidad hacia
> delante, no solo por falta de capacidades.

---

## 2. `roots` — veredicto sobre R13

Código: `srv_1x.py` / `cli_1x.py`, `srv_2x.py` / `cli_2x.py`, `srv_2x_resolve.py` / `cli_2x_resolve.py`.

### 2.1 ¿Existe la API? ¿Qué firma?

**Sí, en las tres ramas. MEDIDO** (leído en el SDK instalado y ejercitado en ejecución):

```python
# mcp 1.8.1  — mcp/server/session.py:258
async def list_roots(self) -> types.ListRootsResult

# mcp 1.29.0 — mcp/server/session.py:362
async def list_roots(self) -> types.ListRootsResult

# mcp 2.0.0  — mcp/server/session.py:317   (decorada @deprecated)
@deprecated("The roots capability is deprecated as of 2026-07-28 (SEP-2577).",
            category=MCPDeprecationWarning)
async def list_roots(self) -> types.ListRootsResult
    # Raises: NoBackChannelError
```

Se llama desde dentro de un handler de herramienta: `server.request_context.session.list_roots()`.
`ListRootsResult.roots` es una lista de `Root(uri, name)`, con `uri` en forma `file:///D:/…`.
**MEDIDO** (`r_129_con_roots.json`, paso `t_roots`).

**No hay hook `oninitialized` en el SDK Python.** La referencia TS pide los roots en `oninitialized`
(`servers/src/filesystem/index.ts`); en Python **no existe ese punto de enganche** en el `Server` de
bajo nivel: `InitializedNotification` solo mueve una máquina de estados interna
(`mcp/server/session.py:211`). Consecuencia de diseño para FileX: **los roots se piden de forma
perezosa, en la primera llamada que los necesite**, no al arrancar. **MEDIDO.**

### 2.2 La notificación de cambio

**En 1.x llega, pero no hay decorador.** El `Server` de bajo nivel expone `@server.list_tools()`,
`@server.call_tool()`, `@server.progress_notification()`… y **ninguno** para
`notifications/roots/list_changed`. Hay que escribir en el mapa a mano:

```python
server.notification_handlers[types.RootsListChangedNotification] = on_roots_changed
```

Funciona. Traza literal del servidor (`stderr_129_con_roots.txt`):

```
[srv +  0.047s] RECIBIDA notifications/roots/list_changed: RootsListChangedNotification(
                  method='notifications/roots/list_changed', params=None, jsonrpc='2.0')
```

Y la relectura posterior devolvió la lista **nueva** (`r_129_con_roots.json`, paso
`t_roots_tras_cambio`): el cliente cambió de `raiz_srv/sub;raiz_fuera` a `raiz_srv` y el servidor lo
vio. **MEDIDO.**

**En `mcp 2.0.0` sobre 2026-07-28 la notificación NO llega.** El cliente la envía sin error, el
servidor tiene el handler registrado, y el log de eventos del servidor sale **vacío**
(`r_200_con_roots.json`, paso `t_eventos_tras_list_changed` → `{"eventos": []}`). En la misma versión
con `mode="legacy"` (protocolo 2025-11-25) **sí** llega (`r_200_legacy.json` →
`{"eventos": [{"t": 0.328, "evento": "roots/list_changed"}]}`). **MEDIDO.**

Además, pasar `on_roots_list_changed` al constructor del `Server` de 2.0.0 emite en el arranque:

```
MCPDeprecationWarning: The roots capability is deprecated as of 2026-07-28 (SEP-2577).
```

**MEDIDO** (`stderr_200_con_roots.txt`, primera línea).

### 2.3 Qué pasa cuando el cliente NO soporta roots

**Rama 1.x — error limpio y capturable, la sesión sobrevive. MEDIDO**
(`r_129_sin_roots.json`, `r_181_sin_roots.json`):

```json
{"ok": false,
 "excepcion": "mcp.shared.exceptions.McpError",
 "repr": "McpError('List roots not supported')",
 "code": -32600,
 "message": "List roots not supported"}
```

**Es el mismo `-32600` y el mismo texto que escribió el servidor de Node.** El servidor de Python
hace exactamente lo mismo que el de Node: intenta, falla, y puede seguir con su lista de argumentos.
La diferencia es que en Python **el error llega como excepción al código de FileX**, no como una línea
de log de una librería: FileX decide qué hacer con él y **no lo filtra al modelo si no quiere**.
Esto encaja con R4 (mensaje opaco): el detalle se queda en el servidor.

**Rama 2.0.0, era moderna — falla por una razón distinta y peor. MEDIDO** (`r_200_con_roots.json`),
y el cliente **sí** declaraba roots:

```json
{"ok": false,
 "excepcion": "mcp.shared.exceptions.NoBackChannelError",
 "code": -32600,
 "message": "Cannot send 'roots/list': this transport context has no back-channel for server-initiated requests."}
```

Es decir: en el protocolo 2026-07-28 **no existe canal de vuelta servidor→cliente durante una llamada
de herramienta**. `session.list_roots()` es inutilizable ahí, con soporte del cliente o sin él.

### 2.4 El camino que sí funciona en 2.0.0: `Resolve(ListRoots)`

La era moderna sustituye el canal de vuelta por **`InputRequiredResult`**: el servidor devuelve
«necesito esto» en lugar del resultado, el cliente lo resuelve y **reintenta** la llamada llevando
`input_responses` + `request_state`. `ListRootsRequest` es uno de los tres `InputRequest` posibles
(los otros dos son sampling y elicitation).

`MCPServer` lo encapsula: un parámetro `Annotated[ListRootsResult, Resolve(fn)]` cuyo resolver
devuelve el marcador `ListRoots()`. El framework traduce **solo** según el protocolo negociado
(`mcp/server/mcpserver/resolve.py`, docstring de cabecera):

> «>= 2026-07-28 batches the requests into an `InputRequiredResult` and resumes when the client
> retries […]; <= 2025-11-25 sends each standalone server-to-client request mid-call.»

**Medido en las dos eras contra el mismo servidor** (`r_2x_resolve.json`):

| modo | protocolo | `t_roots_resolve` | roots recibidos | intersección |
|---|---|---|---|---|
| `auto` | **2026-07-28** | 14,0 ms | 2 | correcta |
| `legacy` | **2025-11-25** | 12,0 ms | 2 | correcta |

**El coste de la era moderna es despreciable (14 ms vs 12 ms), pero el resolver se ejecuta DOS
veces por llamada** — una para emitir el `InputRequiredResult` y otra tras el reintento
(`stderr_2x_resolve_auto.txt`: cuatro `resolver pedir_roots()` para dos llamadas). **MEDIDO.**

> **Regla que hereda FileX de esto:** en `mcp 2.0.0`, el cuerpo de una herramienta que pida roots
> **puede ejecutarse más de una vez por llamada del modelo**. Toda herramienta de FileX que use
> `Resolve` debe ser **idempotente hasta el punto en que tiene los roots**: nada de crear ficheros,
> lanzar procesos ni consumir cuota antes de esa línea.

### 2.5 Intersecar: la API no empuja a nada

**El SDK devuelve una lista y se desentiende. MEDIDO.** No hay `applyRoots()`, no hay estado interno
que se sobreescriba, no hay nada equivalente a la línea `index.ts:181` de la referencia TS. Sustituir
la lista es una decisión que el programador toma escribiendo una asignación; intersecar cuesta el
mismo esfuerzo. **La preocupación de que «la API empuje hacia sustituir» queda refutada.**

La intersección implementada en `srv_1x.py::t_roots_interseca` (16 líneas) y medida:

```
servidor : ["D:\...\raiz_srv"]
cliente  : ["file:///D:/.../raiz_srv/sub", "file:///D:/.../raiz_fuera"]
efectiva : ["D:\...\raiz_srv\sub"]
```

`raiz_fuera` **descartada**, `raiz_srv/sub` **conservada**. El cliente solo puede **estrechar**.
Idéntico resultado en las tres configuraciones probadas (1.29 clásico, 2.0.0 moderno, 2.0.0 legacy).
**MEDIDO** (`r_129_con_roots.json`, `r_2x_resolve.json`).

La regla implementada, que es la que debe portarse:

- raíz del cliente **contenida** en una del servidor → se queda la **del cliente** (estrecha);
- raíz del cliente **más ancha** que una del servidor → se queda la **del servidor** (no amplía);
- raíz del cliente **disjunta** → se **descarta**;
- **sin roots del cliente** → lista inmutable del servidor, tal cual.

Comparación por segmentos con `os.path.normcase` en los dos lados y `+ os.sep`, que es R2 + R3 ya
medidas en `mcp-refs-confinamiento.md`. La conversión `file:///D:/…` → `D:\…` hay que escribirla a
mano (quitar la barra sobrante antes de la letra de unidad); son 6 líneas y ya están en el código.

### 2.6 Veredicto sobre R13

> **R13 es IMPLEMENTABLE. La intersección no tiene ningún obstáculo técnico.** Lo que cambia con la
> versión no es *si* se puede intersecar, sino *por qué API se piden los roots*.

**Versión mínima y forma, por rama:**

| Si FileX fija… | ¿R13? | Cómo | Riesgo |
|---|---|---|---|
| `mcp~=1.8.0` | Técnicamente sí | `session.list_roots()` | **DESCARTAR.** El servidor **muere** ante un cliente 2.0.0 (§1.4). Además el `check_client_capability` miente (§1.3) |
| **`mcp>=1.9.4,<2`** | **Sí, sin salvedades** | `session.list_roots()` + handler manual de `list_changed` | Rama que quedará obsoleta |
| **`mcp>=2.0.0`** | **Sí, pero solo por `MCPServer` + `Resolve(ListRoots)`** | `Annotated[ListRootsResult, Resolve(fn)]` | `session.list_roots()` **no sirve** en 2026-07-28; el cuerpo se ejecuta 2 veces |

**Recomendación: `mcp>=2.0.0`, con los roots pedidos por `Resolve(ListRoots)`.** Es la única
combinación que funciona en las tres eras del protocolo a la vez (medido: negocia 2024-11-05,
2025-11-25 y 2026-07-28 según el cliente, §1.4) y la única que no queda muerta cuando los clientes se
actualicen.

**Una salvedad medida que obliga a escribir código extra.** `Resolve(ListRoots)` **aborta la llamada
entera** si el cliente no declaró roots, en las dos eras (`r_2x_resolve_sin_roots.json`):

```
MCPError(-32021, "Client did not declare the roots capability required by resolver
                  '__main__:pedir_roots'", {'requiredCapabilities': {'roots': {}}})
```

**Eso es exactamente lo contrario de lo que R13 exige.** R13 dice que sin roots del cliente se sigue
con la lista inmutable del servidor; `Resolve` dice que sin roots del cliente no hay herramienta.
Por tanto FileX **no puede declarar `Resolve(ListRoots)` como dependencia dura de sus herramientas**.
La forma correcta:

```python
@server.tool()
async def convert(origen: str, destino: str, ctx: Context) -> str:
    caps = ctx.client_capabilities                  # None o ClientCapabilities
    if caps is not None and caps.roots is not None:
        roots = await pedir_roots_via_resolve(...)  # o el camino perezoso
        raices = intersecar(RAICES_INMUTABLES, roots)
    else:
        raices = RAICES_INMUTABLES                  # R13: degradar, no fallar
    ...
```

`ctx.client_capabilities` existe en `mcp 2.0.0` (`mcp/server/mcpserver/context.py:315`) y en el
servidor de bajo nivel está `session.check_client_capability()`. **MEDIDO** que ambos devuelven
`True`/la capacidad correcta en 2.0.0 (`r_200_con_roots.json`, paso `t_roots_cap`).

**PENDIENTE:** el patrón exacto para pedir roots **condicionalmente** con `MCPServer` sin que
`Resolve` sea una dependencia dura del parámetro. Lo medido dice que la vía dura no sirve; la vía
alternativa (llamar al mecanismo desde el cuerpo) no se ha ejercitado.

**PENDIENTE:** cómo se comportan los clientes reales (Claude Desktop, Claude Code, IDEs) — qué
declaran, qué roots mandan y si emiten `list_changed`. Aquí solo se ha medido cliente-Python contra
servidor-Python.

---

## 3. Tasks (SEP-1686) y progreso — la regla del `job_id`

Código: `srv_tasks_129.py` / `cli_tasks_129.py`, `prueba_progreso.py`, `srv_2x.py`, `cli_1x.py`.

### 3.1 SEP-1686 existe en `1.23.0`–`1.29.0`, y funciona entero

`server.experimental.enable_tasks()` monta la infraestructura completa y **autorregistra**
`tasks/get`, `tasks/result`, `tasks/list` y `tasks/cancel`, con `InMemoryTaskStore` por defecto y
puntos de extensión para Redis. Flujo medido de punta a punta (`r_tasks_129.json`), un trabajo de
**20 s** con un timeout de cliente de **8 s**:

| Paso | Resultado |
|---|---|
| Llamada **bloqueante** normal | `McpError('Timed out … Waited 8.0 seconds.')` a los 8 002,5 ms. **El resultado se pierde** |
| La **misma** herramienta como tarea | asa devuelta en **5,1 ms**: `taskId`, `status="working"`, `pollInterval=500` |
| Sondeo `tasks/get` | `working` → … → `completed` |
| `tasks/result` | **`"convertido en 20.0s"`, `isError=false`** — el resultado **no se pierde** |
| `tasks/cancel` sobre otra tarea | `status="cancelled"` |
| `tasks/list` | devuelve solo las tareas de la propia sesión |

Capacidad anunciada por el servidor:
`tasks: {list: {}, cancel: {}, requests: {tools: {call: {}}}}`.
La herramienta se anota `execution: {taskSupport: "optional"}`. **MEDIDO.**

**Es literalmente la regla 9.4 funcionando.** Y por eso importa tanto lo que viene ahora.

### 3.2 SEP-1686 está ELIMINADO en `mcp 2.0.0`

Aviso literal emitido por el propio SDK 1.29.0 al usar la API (`r_tasks_129.json`, campo `avisos`):

```
DeprecationWarning: The experimental tasks API is deprecated and will be removed in mcp 2.0:
tasks (SEP-1686) were removed from the MCP specification and are expected to return as a
separate MCP extension.
```

Verificado en el paquete instalado de `mcp 2.0.0`:

- `mcp/client/experimental/` — **no existe**;
- `mcp/server/experimental/` — **no existe**;
- `mcp/shared/experimental/tasks/` — **no existe**;
- `grep -rn "tasks/" mcp/ --include=*.py` → **una sola línea**, y es un *docstring*:
  `mcp/server/extension.py:59: """A new request method an extension serves, e.g. `tasks/get`."""`

**MEDIDO.** Matiz que hay que conocer: **los tipos siguen existiendo** (`CreateTaskResult`, `Task`,
`GetTaskRequest`, `ServerTasksCapability`… los 30) porque viven en el paquete `mcp_types` 2.0.0 y
`mcp.types` los reexporta. **Están los tipos y no está el mecanismo.** Un `hasattr(types,
'CreateTaskResult')` da `True` en 2.0.0 y **no significa nada**. **MEDIDO.**

El camino de vuelta anunciado es SEP-2133 (`Extension` + `MethodBinding`), y el ejemplo que el propio
SDK pone de método de extensión es `tasks/get`. **PENDIENTE:** si esa extensión llega y cuándo.

### 3.3 El progreso NO mantiene viva una llamada larga

Es la pregunta que decidía si el progreso podía sustituir al `job_id`. **La respuesta es no, en las
dos ramas.**

**`mcp 1.29.0`** (`r_129_slow.json`), trabajo de **60 s** con progreso cada segundo:

| Fase | Timeout | Resultado |
|---|---|---|
| A | 90 s | **OK a los 60 666 ms**, 60 notificaciones de progreso recibidas |
| B | **20 s** | **`McpError('Timed out … Waited 20.0 seconds.')` a los 20 027,9 ms**, con **19 progresos ya entregados** |

**`mcp 2.0.0`, era moderna 2026-07-28** (`r_progreso_2x_auto.json`), trabajo de **30 s**:

| Fase | Timeout | Resultado |
|---|---|---|
| A | 45 s | **OK a los 30 291,7 ms**, **30** notificaciones recibidas |
| B | **10 s** | **`MCPError(-32001, "Request 'tools/call' timed out")` a los 10 013,9 ms**, con **9 progresos ya entregados** |

**El progreso llegaba, se estaba entregando en ese mismo instante, y el plazo venció igual.** La causa
está en el código: `mcp/shared/session.py:291` usa `anyio.fail_after(timeout)`, un **plazo absoluto**
armado antes de enviar la petición; ninguna notificación entrante lo rearma. **MEDIDO + leído.**

Tras el vencimiento, en las dos ramas:

- **la sesión sobrevive** — el `t_ping` siguiente respondió en 3,5 ms (1.29) y 5,0 ms (2.0.0);
- **el servidor sigue trabajando** en la llamada abandonada — a `t=+99,6 s` seguía emitiendo el paso
  19/60 de un trabajo que el cliente ya había dado por muerto (`r_129_slow.json`);
- **no hay ninguna forma de recuperar el resultado.** En 2.0.0 se comprobó explícitamente:
  `metodos_client_con_task_o_resume: []`. **MEDIDO.**

> **Es el fallo de `bench/mcp-refs-multimedia.md` §9.4 reproducido en Python, en 20 líneas, sin
> ffmpeg.** El trabajo se completa, el disco queda bien, y el modelo recibe un timeout. El progreso
> **no lo arregla**: solo hace que el modelo vea cómo avanza algo que va a perder igualmente.

### 3.4 Para qué SÍ sirve el progreso

Para lo único que dice el nombre: que el cliente distinga «trabajando» de «colgado» **dentro** del
plazo, y para que la interfaz muestre una barra. Es **cosmética valiosa, no un mecanismo de control
de vida**. Vale la pena implementarlo, pero **no** cuenta como respuesta a 9.4.

Detalles de implementación medidos:

- **`mcp 1.8.1`: el cliente NO PUEDE pedir progreso.**
  `TypeError("ClientSession.call_tool() got an unexpected keyword argument 'progress_callback'")`.
  **MEDIDO** (`r_181_slow.json`). Sin `progressToken` en el `_meta`, el servidor no tiene a qué emitir.
- **`mcp>=1.9.0`**: `call_tool(..., progress_callback=cb)` y el SDK usa el `request_id` como
  `progressToken`. En el servidor, `ctx.session.send_progress_notification(progress_token=…)` con el
  token sacado de `ctx.meta.progressToken`. **MEDIDO**.
- **`mcp 2.0.0`, era moderna: el patrón de 1.x deja de funcionar en silencio.** `ctx.meta` **no trae
  `progressToken`** — trae las claves nuevas `io.modelcontextprotocol/protocolVersion`,
  `…/clientInfo`, `…/clientCapabilities`. Un servidor portado tal cual mide `progress_token=None`,
  no emite nada, y **no da ningún error**: el cliente simplemente recibe **cero** progresos
  (medido: primera pasada, `n_progresos: 0` en las dos fases). La API correcta es
  **`ctx.session.report_progress(progress, total, message)`**, que no necesita token y es *no-op* si
  el llamante no pidió progreso. Con ella, 30/30 notificaciones. **MEDIDO** — este fallo se cometió y
  se corrigió durante la medición; los dos resultados están en el histórico de `srv_2x.py`.
- En 2.0.0, el progreso **cliente→servidor** está deprecado (SEP-2577); el **servidor→cliente**, que
  es el que le importa a FileX, sigue vivo. **MEDIDO** (aviso literal en `mcp/client/client.py:530`).

### 3.5 Entonces, ¿el protocolo resuelve el `job_id`?

> **NO. FileX tiene que construirlo entero.** **MEDIDO.**

El razonamiento, cerrado:

1. El **progreso** no evita el timeout ni recupera el resultado (§3.3). Descartado como alternativa.
2. **Tasks (SEP-1686)** resolvía el problema de verdad (§3.1) pero **fue retirado de la
   especificación** y **eliminado del SDK en 2.0.0** (§3.2). Apoyarse en él obliga a fijar
   `mcp>=1.23,<2` — es decir, a renunciar al protocolo 2026-07-28 y a quedarse en una API que sus
   propios autores marcan como deprecada y ya borrada en la versión siguiente.
3. La **extensión SEP-2133** que traería las tareas de vuelta **no existe todavía**.

### 3.6 Qué tiene que construir FileX, y con qué forma

**Recomendación concreta para el hito 4: `job_id` propio en el nivel de la herramienta, no del
protocolo, con TRES herramientas y un `job_id` devuelto al empezar.**

```
convert(origen, destino, formato, …)  ->  { "job_id": "…", "estado": "en_curso",
                                            "sondear_en_ms": 1000 }        <- SIEMPRE, ~30 tokens
job_status(job_id)                    ->  { "estado": "en_curso"|"hecho"|"error"|"cancelado",
                                            "avance": 0.42, "mensaje": "…" }
job_result(job_id)                    ->  { "ruta": "…", "bytes": …, "duracion_s": … }  (R1 de patrones)
job_cancel(job_id)                    ->  { "estado": "cancelado" }
```

**Las decisiones concretas, cada una con su razón medida:**

1. **El asa se entrega SIEMPRE al empezar, nunca al terminar, y nunca condicionada a un booleano.**
   Es la única forma en que 9.4 no se hereda. La medición de `run_task` da la cifra a igualar:
   **5,1 ms hasta el asa** para un trabajo de 20 s (§3.1).
2. **Sin bifurcación «rápido bloquea / lento devuelve asa».** No se puede saber de antemano: en la
   medición original un clip de **5 segundos** superó **900 s**. Una firma, un comportamiento.
3. **Herramientas separadas, no un `job_id` opcional en la respuesta de `convert`.** El catálogo
   cuesta tokens (`mcp-refs-multimedia.md` §2.1: el techo del sector son 7.964), pero tres
   herramientas de esquema mínimo son ~200 tokens (**estimación, PENDIENTE de medir**) y **el modelo
   no tiene que adivinar** si lo que recibió es un resultado o un asa.
4. **Copiar la forma del `Task` de SEP-1686 aunque no se use el mecanismo**: `estado` con el mismo
   vocabulario (`working`/`completed`/`failed`/`cancelled`), un `pollInterval` que el servidor
   sugiere, y un **TTL**. Si la extensión SEP-2133 llega, migrar es cambiar el transporte y no el
   modelo de datos. `run_task` devolvió `pollInterval=500`; para conversiones de minutos, **1.000 ms
   es un punto de partida más razonable** — **PENDIENTE** medir el coste en tokens del sondeo.
5. **El estado del trabajo vive fuera del proceso de la sesión.** El fallo de 9.4 es que el trabajo se
   completó y nadie pudo saberlo: si el `job_id` solo vive en memoria del servidor MCP, una caída o
   una reconexión del cliente reproduce el fallo exacto que se está intentando arreglar. Un fichero
   JSON por trabajo en el directorio de estado de FileX basta y sirve además a la CLI, al watcher y a
   la API HTTP — los cuatro frentes ven el mismo trabajo. **Esto es lo que justifica el `job_id`
   propio frente a Tasks incluso si Tasks volviera**: `InMemoryTaskStore` es de la sesión; el asa de
   FileX tiene que sobrevivir a la sesión.
6. **`job_cancel` debe matar el árbol de procesos**, no solo marcar el estado — es R de
   `mcp-refs-multimedia.md` §9.5 (`ffmpeg-mcp-lite` dejó huérfanos vivos 13 minutos).
7. **El progreso se implementa además, no en vez.** `ctx.session.report_progress()` en 2.0.0 durante
   la ventana en que `convert` aún no ha devuelto, y `job_status` para todo lo demás.

**Coste estimado:** el `TaskStore` + `run_task` del SDK 1.29 son ~600 líneas incluyendo el
almacén, la cola de mensajes y el ámbito por sesión. La versión de FileX es más pequeña porque no
necesita elicitation ni sampling dentro del trabajo, pero **sí** necesita persistencia en disco, que
el SDK no trae. **PENDIENTE:** estimación firme.

---

## 4. `ImageContent` — qué acepta el SDK

Código: `prueba_imagecontent.py`, más el ida y vuelta real por stdio en `srv_1x.py::t_img`.

### 4.1 Resultado: el SDK no valida base64. En ninguna rama.

Idéntico en `1.8.1`, `1.29.0` y `2.0.0` (`r_imagecontent_*.json`):

| Caso | Construcción | Ida y vuelta por el alambre | Error literal |
|---|---|---|---|
| base64 puro (96 car.) | **acepta** | intacto | — |
| **`data:image/png;base64,…`** (118 car.) | **acepta** | **intacto** | — |
| `"esto no es base64 !!!! @@@@"` | **acepta** | intacto | — |
| cadena vacía `""` | **acepta** | intacto | — |
| padding `=` eliminado | **acepta** | intacto | — |
| base64 con `\n` en medio | **acepta** | intacto | — |
| `bytes` en vez de `str` | **rechaza** | — | `Input should be a valid string, unable to parse raw data as a unicode string [type=string_unicode]` |
| `int` | **rechaza** | — | `Input should be a valid string [type=string_type, input_value=12345, input_type=int]` |
| `None` | **rechaza** | — | `Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]` |

**El único validador es el tipo `str` de pydantic.** El campo está declarado así, sin anotaciones ni
validadores, en las tres ramas:

```python
class ImageContent(BaseModel):        # 1.8.1 / 1.29.0
    type: Literal["image"]
    data: str                          # """The base64-encoded image data."""
    mimeType: str
```
```python
class ImageContent(MCPModel):         # 2.0.0 (mcp_types._types)
    type: Literal["image"] = "image"
    data: str
    mime_type: str                     # <- ATENCIÓN: snake_case en 2.0.0
```

`mimeType` / `mime_type` es **obligatorio**, pero **la cadena vacía pasa**: `mimeType=""` viajó de ida
y vuelta sin una queja (`r_129_con_roots.json`, paso `t_img_nomime`). **MEDIDO.**

### 4.2 Respuesta a la pregunta 6 de `analysis/00-mcp-componentes.md` §2

> *«Confirmar en ejecución que el SDK Python acepta `ImageContent` con base64 puro y qué hace el
> cliente con él.»*

- **El SDK Python acepta base64 puro. MEDIDO**, ida y vuelta real por stdio con un PNG 1×1 válido.
- **El SDK Python acepta también el prefijo `data:` sin rechistar. MEDIDO.** El antipatrón de
  `image-worker-mcp` **no lo detiene el protocolo ni el SDK**: la cadena `data:image/png;base64,…`
  llega al cliente intacta en el campo `data` de un `ImageContent` bien formado, y quien la reciba
  como base64 obtendrá basura al descodificarla. **La validación tiene que hacerla FileX.**
- **Qué hace el cliente con él: PENDIENTE.** Aquí el «cliente» era un cliente Python de laboratorio
  que solo deserializa el modelo. Qué hace un cliente real —si descodifica, si valida, si lo pasa como
  bloque de imagen nativo al modelo— **no se ha medido y no se puede medir con este arnés.**

### 4.3 Lo que sí es una referencia utilizable

Los helpers `Image` del propio SDK hacen lo correcto en las dos ramas
(`mcp/server/fastmcp/utilities/types.py` en 1.29, `mcp/server/mcpserver/utilities/types.py` en 2.0.0):

```python
data = base64.b64encode(f.read()).decode()
return ImageContent(type="image", data=data, mimeType=self._mime_type)
```

**Base64 puro, sin prefijo, en las dos.** El prefijo de `image-worker-mcp` no lo induce el SDK: es un
error propio de ese proyecto. **MEDIDO** (leído en el paquete instalado).

### 4.4 Esto NO reabre la decisión de producto

`bench/mcp-refs-multimedia.md` §9.3 midió **0,93 tokens por byte** y situó el umbral de rentabilidad
en **1-2 KB**. Nada de lo medido aquí toca esa cifra: solo dice **qué permite el SDK**, no qué debe
hacer FileX. **La firma de las herramientas de FileX no cambia y no hay excepción por tamaño para las
imágenes.** Lo único que este informe añade al diseño es una **regla defensiva**:

> Si FileX llegara alguna vez a emitir un `ImageContent`, debe validar él mismo que `data` es base64
> canónico —sin prefijo `data:`, sin saltos de línea, con el padding correcto— porque **el SDK no lo
> comprueba y el cliente recibirá lo que se le mande.**

---

## 5. Restricciones de versión que hereda FileX

| Capacidad | Versión mínima | Evidencia |
|---|---|---|
| `session.list_roots()` funcional | `1.8.1` | §2.1 **MEDIDO** |
| Capacidad `roots` del cliente **fiable** (`check_client_capability` no miente) | **`1.9.4`** | §1.2, §1.3 **MEDIDO** |
| `progress_callback` en `call_tool` (lado cliente) | **`1.9.0`** | §1.2 **MEDIDO** |
| Protocolo `2025-11-25` | `1.24.0` | §1.2 **MEDIDO** |
| Tasks SEP-1686 | `1.23.0` … **`1.29.0` (última)** | §1.2, §3.1 **MEDIDO** |
| Protocolo `2026-07-28` | **`2.0.0`** | §1.1 **MEDIDO** |
| Roots en el protocolo `2026-07-28` | **`2.0.0` + `MCPServer` + `Resolve(ListRoots)`** | §2.4 **MEDIDO** |
| No morir ante un cliente `2.0.0` | **`>=1.29.0`** (probado); `1.8.1` **muere** | §1.4 **MEDIDO** |

### 5.1 Contraste con la incompatibilidad ya medida

El dato de partida era: **`mcp~=1.8.0` y `mcp>=2.0.0` no coexisten en un venv** — negocian 2024-11-05
frente a 2025-11-25, y por eso el proyecto tiene tres entornos separados.

Lo medido aquí **no lo contradice, lo agrava y lo desplaza**:

1. **La cifra era otra.** `mcp 2.0.0` no negocia 2025-11-25 sino **2026-07-28**. Hay **tres** eras de
   protocolo en juego, no dos: 2024-11-05, 2025-11-25 y 2026-07-28. **MEDIDO.**
2. **El problema real no es el venv, es la dirección de la incompatibilidad.** Un servidor sobre
   `mcp 2.0.0` habla con clientes 1.8.1 y 1.29.0 sin problema (§1.4). Un servidor sobre `mcp 1.8.x`
   **se muere** ante un cliente 2.0.0, con caída de proceso, no con un error de protocolo.
   **La compatibilidad es asimétrica y favorece a la rama nueva.**
3. **FileX no necesita convivir con las dos.** Los venvs separados existen porque `docling-mcp` y
   `markitdown-mcp` son **servidores de terceros** que FileX consume; el servidor **de FileX** es un
   proceso distinto con su propio entorno. Fijar `mcp>=2.0.0` para FileX no obliga a nada a los
   sidecars: cada uno en su venv, hablando por stdio, es exactamente el aislamiento que ya existe.

### 5.2 Restricción recomendada

```
mcp>=2.0.0
```

**Razones, todas medidas:**

- es la única rama que negocia las tres eras del protocolo según el cliente (§1.4);
- es la única en la que los roots funcionan sobre 2026-07-28 (§2.4);
- no perder Tasks no cuesta nada, porque **Tasks ya no está en la especificación** (§3.2) y FileX
  tiene que construir su `job_id` propio de todos modos (§3.6);
- fijar `<2` significaría escribir el servidor contra `session.list_roots()` y `FastMCP`, y
  **reescribir la capa de roots y la de progreso entera** cuando toque migrar (§2.4, §3.4).

**Los tres precios de esa elección, para que consten:**

1. `mimeType` pasa a `mime_type`, `isError` a `is_error`, `inputSchema` a `input_schema`. Migración
   mecánica pero total. **MEDIDO.**
2. `ctx.meta` ya no trae `progressToken`: hay que usar `session.report_progress()`, y **el patrón
   viejo falla en silencio** (§3.4).
3. El cuerpo de una herramienta que pida roots se ejecuta **dos veces** por llamada (§2.4). Hay que
   escribirlas idempotentes hasta esa línea.

**PENDIENTE:** medir `mcp 2.0.0` con clientes reales antes de fijar la dependencia. Todo el §1.4 son
clientes Python de laboratorio; si Claude Desktop o Claude Code todavía sondean solo con el handshake
clásico, un servidor 2.0.0 les hablará en 2025-11-25 (medido que sabe hacerlo) y los roots irán por el
camino clásico — pero eso hay que verlo, no suponerlo.

---

## 6. Índice de código y datos

Todo en `bench/salidas-sdk-mcp/`. Cada script es autónomo y se ejecuta con el python del venv
correspondiente.

### 6.1 Bancos de pruebas

| Fichero | Qué es |
|---|---|
| `srv_1x.py` | servidor mínimo rama 1.x: `t_ping`, `t_roots`, `t_roots_cap`, `t_roots_interseca`, `t_slow`, `t_img`, `t_eventos`. Incluye el registro **a mano** del handler de `roots/list_changed` |
| `cli_1x.py` | cliente rama 1.x. `--roots` / sin `--roots`, `--roots-2` para provocar `list_changed`, `--slow` y `--slow-timeout` para la operación larga |
| `srv_2x.py` | el mismo servidor portado a `mcp 2.0.0` (handlers por constructor, `mime_type`, `report_progress`) |
| `cli_2x.py` | cliente 2.x. `--modo auto|legacy|2026-07-28` |
| `srv_2x_resolve.py` | servidor 2.x con `MCPServer` + `Resolve(ListRoots)` — **el único camino de roots que funciona en 2026-07-28** |
| `cli_2x_resolve.py` | ejercita el anterior en las dos eras. `FILEX_SIN_ROOTS_CLIENTE=1` para el caso sin soporte |
| `srv_tasks_129.py` / `cli_tasks_129.py` | SEP-1686 completo: `run_task`, sondeo, `tasks/result`, `tasks/cancel`, `tasks/list` |
| `prueba_progreso.py` | fases A (timeout largo) y B (timeout corto) sobre el mismo trabajo, contando progresos |
| `prueba_imagecontent.py` | 9 casos de `data` × construcción + ida y vuelta JSON. Corre en cualquiera de las 3 ramas |
| `interop.py` | una celda de la matriz cliente-venv × servidor-venv |
| `sondear_wheels.py` | acota en qué versión aparece cada capacidad **sin instalar**: `pip download --no-deps` + lectura del `.whl` como ZIP |

### 6.2 Datos crudos

| Fichero | Contenido |
|---|---|
| `r_129_con_roots.json` / `r_129_sin_roots.json` | roots en 1.29.0, con y sin soporte del cliente |
| `r_181_sin_roots.json` | roots en 1.8.1 — el falso positivo de `check_client_capability` |
| `r_129_slow.json` | trabajo de 60 s: progreso con timeout largo y con timeout corto |
| `r_181_slow.json` | el `TypeError` de `progress_callback` en 1.8.1 |
| `r_200_con_roots.json` | 2.0.0 era moderna: `NoBackChannelError` y `list_changed` que no llega |
| `r_200_legacy.json` | 2.0.0 con `mode="legacy"`: roots funcionando sobre 2025-11-25 |
| `r_2x_resolve.json` | `Resolve(ListRoots)` en las dos eras |
| `r_2x_resolve_sin_roots.json` | el `-32021` que aborta la llamada entera |
| `r_progreso_2x_auto.json` | progreso en 2.0.0 sobre 2026-07-28, fases A y B |
| `r_tasks_129.json` | SEP-1686 completo, con el aviso literal de retirada |
| `r_imagecontent_.venv-mcp-sdk-{18,1x,2x}.json` | los 9 casos de `data` en las tres ramas |
| `interop_cli*_srv*.json` | las 9 celdas de la matriz de §1.4 |
| `stderr_*.txt` | `stderr` de cada servidor: es donde están las trazas de `roots/list_changed`, los `MCPDeprecationWarning` y la caída del servidor 1.8.1 |
| `pip_{18,1x,2x}.log` | instalación de los tres venvs |

---

## 7. Qué queda PENDIENTE

1. **Clientes reales.** Todo el informe es Python contra Python. Qué protocolo negocian Claude
   Desktop / Claude Code / los IDEs con un servidor `mcp 2.0.0`, qué roots declaran y si emiten
   `list_changed` — sin medir. Es lo primero que hay que comprobar antes de fijar la dependencia.
2. **El patrón de roots condicional en `MCPServer`.** Medido que `Resolve(ListRoots)` como
   dependencia dura **no sirve** para R13 (aborta en vez de degradar). La alternativa no se ha
   ejercitado.
3. **Si la extensión SEP-2133 de tareas llega**, y cuándo. Cambiaría §3.6 de «construirlo entero» a
   «construirlo con un transporte migrable».
4. **`pollInterval` y el coste en tokens del sondeo.** Cada `job_status` es una llamada del modelo;
   500 ms (lo que sugiere el SDK) sería ruinoso para una conversión de minutos. Hay que medirlo.
5. **Coste real de portar a la API 2.0.0** (`mime_type`, `is_error`, `input_schema`,
   `report_progress`, handlers por constructor). Aquí solo se portó un servidor de 7 herramientas
   triviales.
6. **Qué hace un cliente real con un `ImageContent` cuyo `data` lleva el prefijo `data:`** — si lo
   descodifica como basura, si lo detecta, si lo tolera.
