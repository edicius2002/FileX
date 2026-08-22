# Los cinco cabos sueltos de la línea MCP, cerrados

**Fecha:** 21 de agosto de 2026. Máquina: Windows 10 Home 19045, 12 núcleos, Python 3.11.9,
Node v22.23.2, WSL2 (Ubuntu, Python 3.14.4). **Sin GPU.**

Este informe cierra los cinco cabos que `RESULTADOS-MCP.md` §13 y sus tres informes dejaron
abiertos. Código y datos crudos: **`bench/salidas-mcp-cabos/`**.

> **Convención del proyecto.** Cada afirmación va marcada **MEDIDO** (hay una salida literal
> en `bench/salidas-mcp-cabos/*.json`, `*.jsonl`, `*.log` o `*.txt` que la respalda) o
> **PENDIENTE** (no se ha ejecutado). Donde el resultado contradice a un documento del
> proyecto, se dice y se señala el documento.

> **`.mcp.json`.** Se hizo copia en `bench/salidas-mcp-cabos/mcp.json.bak` antes de tocarla, se
> añadió un servidor de prueba **solo de proyecto**, y se restauró al terminar. `git status`
> la da limpia. **`~/.claude.json` no se tocó en ningún momento.**

---

## 0. Resumen ejecutivo

| Cabo | Veredicto | Lo que más cambia |
|---|---|---|
| **1 — `mcp 2.0.0` contra clientes reales** | **CERRADO. Sobrevive, y con holgura** | Claude Code negocia **2025-11-25, no 2026-07-28**. Toda la maquinaria de `NoBackChannelError` / `InputRequiredResult` **no llega a ejercitarse hoy**. Pero **las anotaciones no llegan al modelo**: solo cruzan `description` e `inputSchema` |
| **2 — El patrón condicional de roots** | **CERRADO. Escrito y demostrado en los 4 casos** | El resolver decide si pregunta: devolver el marcador `ListRoots()` dispara el `-32021`; devolver un `ListRootsResult` construido a mano lo esquiva. **Nunca aborta** |
| **3 — Suite de `image-worker-mcp`** | **CERRADO. 117 tests, 6 ficheros, 6,43 s, 0 fallos** | Sus 2 tests de HEIC **sí verifican la salida** (`sharp().metadata()`), que es justo lo que le falta a `ffmpeg-mcp-lite`. Pero **consagran en un test el antipatrón de contenido encubierto** |
| **4 — El deadlock en las otras 23** | **CERRADO, y peor de lo que se creía** | 6 de 6 representantes cuelgan con la salida preexistente. Y **`-y` no basta**: medido A/B, `stdin` heredado cuelga **2 de 5** con todas las banderas correctas; con `stdin=DEVNULL`, **0 de 5** |
| **5 — La ventana TOCTOU real** | **CERRADO. R8 CONFIRMADA, con el mecanismo corregido** | La ventana es **el 99,6 % de la conversión** (9.758 ms de 9.794 ms). El vector que funciona **no es sustituir el fichero** —lo deniegan Windows y POSIX por vías distintas— sino **escribir en sitio**, que funciona en las dos. Copiar cuesta **0,12 %** de la conversión… salvo en `inspect`, donde cuesta **1,32×** |

---

## 1. Cabo 1 — `mcp 2.0.0` contra clientes reales

`bench/sdk-mcp-capacidades.md` recomienda `mcp>=2.0.0` y su §1.4 avisa de que todo el informe
es Python contra Python. Aquí se enfrenta a **Claude Code 2.1.238**, un cliente escrito en
TypeScript sobre el SDK oficial de Node.

**Montaje.** Servidor MCP mínimo sobre `mcp 2.0.0` (`cabo1_srv_2x.py`, venv `.venv-mcp-sdk-2x`)
con cinco herramientas, un recurso y un prompt. Registra en `cabo1_srv_log.jsonl` todo lo que
puede saber del cliente. Se dio de alta en la `.mcp.json` **del proyecto** y se ejercitó con
`claude -p … --mcp-config <fichero del proyecto> --strict-mcp-config`.

### 1.1 El servidor sobrevive, y el protocolo que se negocia NO es el moderno

**MEDIDO** (`cabo1_srv_log.jsonl`, evento `llamada:filex_radiografia`):

```json
{"protocolo_negociado": "2025-11-25",
 "client_capabilities": {"elicitation": {}, "roots": {"list_changed": true}},
 "client_params": {"protocol_version": "2025-11-25",
                   "client_info": {"name": "claude-code", "title": "Claude Code",
                                   "version": "2.1.238",
                                   "description": "Anthropic's agentic coding tool",
                                   "website_url": "https://claude.com/claude-code"}},
 "request_meta": "{'progress_token': 4, 'claudecode/toolUseId': 'toolu_01GYYmsL3KyDz8r8RgVn8fn8'}",
 "sdk_mcp": "2.0.0"}
```

Cinco lecturas, todas MEDIDO:

1. **Un servidor sobre `mcp 2.0.0` habla sin fricción con el cliente real.** Cero errores,
   cero avisos de deprecación en el intercambio, las herramientas responden. **La
   recomendación de `bench/sdk-mcp-capacidades.md` §2.6 aguanta la prueba de fuego.**
2. **Se negocia `2025-11-25`, la era clásica.** Claude Code 2.1.238 va **una era por detrás**
   del `LATEST_PROTOCOL_VERSION` del SDK de Python. Esto es lo más importante del cabo, y ver
   §1.5.
3. **El cliente declara `roots` con `listChanged: true` y `elicitation: {}`.** No declara
   `sampling`. La capacidad de la que depende R13 **está ahí**.
4. **Manda un root, y es el directorio del proyecto**: `file:///D:/Work/research/FileX`
   (`llamada:filex_roots_efectivos`). La intersección con la lista inmutable del servidor
   (`D:\Work\research\FileX\corpus`) dio `INTERSECADO → ["D:\\Work\\research\\FileX\\corpus"]`:
   el cliente es **más ancho** que el servidor, así que gana el servidor. **R13 funcionando
   contra un cliente real.**
5. **Manda `progress_token` en cada llamada**, más una extensión propia
   `claudecode/toolUseId`. El canal de progreso está disponible sin pedirlo.

### 1.2 Lo que se pierde por el camino: **las anotaciones no llegan al modelo**

Es el hallazgo del cabo. Se le preguntó al propio Claude Code qué veía en su catálogo
(`cabo1_claude_run2.json`, respuesta literal guardada). **MEDIDO:**

| Lo que el servidor declara | ¿Llega al modelo? |
|---|---|
| `description` | **Sí**, literal |
| `inputSchema` (`parameters`) | **Sí**, literal |
| `annotations.readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` | **No** |
| `annotations.title` y el `title` de la herramienta | **No** |
| `_meta` (`{"filex/marca": "cabo1", …}`) | **No** |
| `outputSchema` | **No** |
| `icons` | **No** |

La prueba limpia es `filex_destructiva`, declarada `destructiveHint=true, openWorldHint=true`.
El modelo supo que era destructiva **solo porque el autor lo escribió dentro de la
descripción**. Palabras del propio cliente:

> «El caso de `filex_destructiva` lo demuestra sin ambigüedad. […] Si esa frase no estuviera en
> la descripción, para mí sería indistinguible de una herramienta de solo lectura. **Las
> anotaciones del protocolo no cruzan hasta el modelo; solo cruza la descripción.**»

**Y tampoco cambian el permiso.** Con el modo de permisos por defecto, `filex_radiografia`
—marcada `readOnlyHint=true, destructiveHint=false, idempotentHint=true, openWorldHint=false`—
fue **denegada igual** (`cabo1_permisos.json`):

```json
"permission_denials": [{"tool_name": "mcp__filex-cabo1__filex_radiografia", "tool_input": {}}]
```

> **Qué cambia en las reglas.** `RESULTADOS-MCP.md` §9.1 mantiene «anotar `readOnlyHint` /
> `destructiveHint`» como regla confirmada, con el argumento de que **0 de 3** servidores de
> multimedia anotan y que anotar sería «una ventaja diferencial real». **Eso hay que matizarlo:
> medido contra el cliente real más probable, anotar no produce ninguna diferencia observable —
> ni en lo que ve el modelo, ni en el permiso.** La regla sigue valiendo (es barata, es
> correcta según la especificación, y otros clientes pueden usarla), pero **no puede ser el
> sitio donde vive una advertencia de seguridad**. Lo que el modelo lee es la `description`; lo
> que impide una operación prohibida es el núcleo (R10).

### 1.3 `ImageContent` sí es un canal distinto — y cuesta por píxel, no por byte

**MEDIDO.** `filex_imagen` devuelve un `ImageContent` nativo. Dos observaciones:

- Con un PNG de **1×1**, el modelo recibió un marcador de error de la API de visión
  (`invalid_request_error: Could not process image`) — **no** una cadena base64. El bloque se
  enrutó **como imagen**, y falló por ser demasiado pequeña.
- Con `corpus/imagen/tipico.png` (**42.855 B, 1920×1080**), el modelo **vio la imagen**:
  describió el degradado azul→amarillo y el texto «FileX test» (`cabo1_claude_run3.json`).

**El coste, medido en A/B con el mismo prompt** (`cabo1_ab_imagen.json` /
`cabo1_ab_texto.json`, `usage.cache_creation_input_tokens`):

| Llamada | `cache_creation_input_tokens` |
|---|---:|
| `filex_imagen(tipico.png)` | **12.016** |
| `filex_estructurada` (texto de 58 B) | **9.202** |
| **diferencia atribuible al `ImageContent`** | **≈ 2.814 tokens** |

La predicción por el modelo de coste por píxel `w×h/750` da **2.765** para 1920×1080. Coincide.

> **Esto matiza una cifra viva de `RESULTADOS-MCP.md` §2 (pregunta 6).** Los **0,93 tokens por
> byte** allí medidos son el coste del **base64 dentro de texto** — el patrón de *contenido
> encubierto* de §3. Para el **`ImageContent` nativo a través de un cliente real** el coste no
> depende de los bytes sino de los píxeles:
>
> | Vía | `tipico.png` (42.855 B, 1920×1080) |
> |---|---:|
> | base64 dentro de `TextContent` (0,93 tok/B) | ~39.855 tok |
> | **`ImageContent` nativo (medido)** | **~2.814 tok** |
> | asa (ruta + metadatos) | **32-72 tok** |
>
> **La conclusión no cambia, se refuerza en el sitio correcto.** El `ImageContent` nativo es
> ×14 más barato que el antipatrón encubierto, y aun así **×39 a ×88 más caro que devolver la
> ruta**. Sigue sin haber umbral que justifique devolver la imagen. Y sigue siendo cierto que
> el criterio operativo debe ser **tokens de respuesta**: es lo único que captura las dos vías.

### 1.4 `structuredContent` no compra nada del lado del modelo

**MEDIDO.** `filex_estructurada` declara `structured_output=True` y un `outputSchema` real. Lo
que llegó al modelo fue una línea de texto:

```json
{"formato":"png","ancho":1,"alto":1,"ruta":"D:/tmp/x.png"}
```

Indistinguible de un `TextContent` con el mismo JSON serializado a mano, y sin el
`outputSchema` a la vista. **Confirma por otra vía el «dato incómodo» de `RESULTADOS-MCP.md`
§4:** `outputSchema` presente no significa contrato de salida útil; aquí ni siquiera llega.

### 1.5 Las dos consecuencias operativas del protocolo `2025-11-25`

**MEDIDO, y desactiva —por ahora— el riesgo principal de `mcp 2.0.0`:**

1. **`session.list_roots()` funciona** contra Claude Code, porque en `2025-11-25` sí hay canal
   de vuelta. El `NoBackChannelError` de `sdk-mcp-capacidades.md` §2.3 es real, pero **hoy no
   se dispara con este cliente**.
2. **`Resolve(ListRoots)` usa la vía clásica** (petición servidor→cliente a mitad de llamada),
   no `InputRequiredResult`. Es decir: **el cuerpo de la herramienta NO se ejecuta dos veces**
   con este cliente. La regla de idempotencia de `sdk-mcp-capacidades.md` §2.4 sigue siendo
   necesaria —el cliente se actualizará— pero **no es urgente**.

> **La recomendación queda reforzada, no debilitada:** construir sobre `mcp>=2.0.0` es lo
> correcto **precisamente porque** negocia hacia abajo. FileX se escribe una vez y funciona en
> las tres eras. Lo que hay que quitar del plan es la urgencia: el código de
> `Resolve(ListRoots)` hay que escribirlo, pero el camino que hoy se ejercita es el clásico.

### 1.6 Un detalle operativo que FileX va a sufrir al distribuirse

**MEDIDO** (`cabo1_claude_mcp_list.txt`). Al añadir el servidor a `.mcp.json`, `claude mcp list`
respondió:

```
filex-cabo1: … - ⏸ Pending approval (run `claude` to approve)
```

**Cualquier cambio en la `.mcp.json` del proyecto vuelve a poner el servidor en «pendiente de
aprobación»**, y la aprobación es interactiva. Para FileX significa que un `filex init` que
escriba la `.mcp.json` **no deja el servidor conectado**: hace falta un paso humano. Conviene
decirlo en la documentación de instalación en vez de que lo descubra el usuario.

*(En la misma ejecución, los dos servidores preexistentes —`markitdown` y `docling`— fallaron
el health-check con `connection timed out after 30000ms`. Se comprobaron a mano y arrancan; el
timeout de 30 s del comprobador es corto para ellos. No afecta a este cabo.)*

### 1.7 Lo que este cabo NO cerró — **dos de ellos, cerrados el 22/08 en `bench/mcp-cabos-2.md`**

> **`resources` / `prompts` («cero lecturas, no se pidió»): CERRADO, y el matiz importa.** El **cliente sí** los enumera —`resources/list` y `prompts/list`, n=1 cada uno, justo después de `tools/list`—; no era que no preguntara, es que no se le había pedido al modelo que los usara. **Pero el MODELO no los ve**: responde «NINGUNO». **Declararlos es coste sin retorno** (§3 de aquel informe).
>
> **`notifications/roots/list_changed`: capacidad MEDIDA.** Claude Code 2.1.238 declara `roots.listChanged: true` en su `initialize`, así que FileX puede **cachear los roots por sesión e invalidar con la notificación**. *Observar una emisión real* sigue PENDIENTE (§2 de aquel informe).

- **PENDIENTE:** si Claude Code emite `notifications/roots/list_changed`. No hay forma de
  cambiar los roots a mitad de una sesión headless.
- **PENDIENTE:** si Claude Code expone recursos (`resources/list`) y prompts (`prompts/list`)
  al modelo. El servidor los declara y registró **cero** lecturas, pero tampoco se le pidió
  que los usara.
- **Observación con reserva:** en esta versión las herramientas MCP le llegaron al modelo
  **diferidas** (solo el nombre; descripción y esquema hasta una búsqueda explícita). Si eso es
  el comportamiento general, el «coste de catálogo» de `RESULTADOS-MCP.md` §4 **no se paga por
  adelantado** en este cliente. Es una observación de una sola sesión y depende de la
  configuración; **marcada PENDIENTE** de una medición dedicada.

---

## 2. Cabo 2 — El patrón condicional de roots

`bench/sdk-mcp-capacidades.md` §2.6 dejó **PENDIENTE** el patrón exacto: `Resolve(ListRoots)`
como dependencia dura **aborta la llamada entera** con `-32021` si el cliente no declara roots,
que es lo contrario de lo que exige **R13**.

### 2.1 Dónde está la palanca

Leído en `mcp/server/mcpserver/resolve.py:568-575` del SDK instalado:

```python
if _is_marker(result):            # ListRoots() / Elicit() / Sample()
    outcome = await _fulfil(result, wire_key, res)   # <- aquí, y SOLO aquí, corre
else:                                                #    _require_capability -> -32021
    outcome = _accepted(result)   # <- un valor plano se acepta sin comprobar nada
```

**El resolver decide si pregunta.** Y el resolver puede recibir el `Context`. Ese es el patrón
que faltaba, y son **ocho líneas** (`cabo2_roots.py`):

```python
def roots_o_nada(ctx: Context) -> ListRoots | ListRootsResult:
    """Pide los roots SOLO si el cliente declaro la capacidad; si no, devuelve vacio."""
    caps = getattr(ctx, "client_capabilities", None)
    if caps is not None and getattr(caps, "roots", None) is not None:
        return ListRoots()              # marcador -> el framework lo cumple por el transporte
    return ListRootsResult(roots=[])    # valor plano -> ni marcador, ni -32021, ni aborto

RootsOpcionales = Annotated[ListRootsResult, Resolve(roots_o_nada)]
```

La herramienta lo consume igual que la versión dura:

```python
@server.tool()
def convert(roots: RootsOpcionales, ctx: Context) -> str:
    raices = raices_efectivas(RAICES_INMUTABLES, roots)   # interseca, o degrada
```

### 2.2 Demostrado en los cuatro casos

`cabo2_srv.py` expone tres herramientas idénticas salvo en cómo piden los roots, y `cabo2_cli.py`
las ejercita en las dos eras × (cliente con roots / sin roots). **MEDIDO**
(`cabo2_resultados.json`):

| Protocolo | Cliente declara roots | `t_dura` (dependencia dura) | `t_condicional` (el patrón nuevo) | `t_cuerpo` (`session.list_roots()`) | `t_ping_final` |
|---|---|---|---|---|---|
| **2026-07-28** | **sí** | ✔ INTERSECADO (343 ms) | ✔ INTERSECADO (7 ms) | ✘ `NoBackChannelError` | ✔ pong |
| **2026-07-28** | **no** | ✘ **`MCPError(-32021)` — aborta** (2 ms) | ✔ **DEGRADADO** (8 ms) | ✔ DEGRADADO (3 ms) | ✔ pong |
| **2025-11-25** | **sí** | ✔ INTERSECADO (11 ms) | ✔ INTERSECADO (4 ms) | ✔ INTERSECADO (4 ms) | ✔ pong |
| **2025-11-25** | **no** | ✘ **`MCPError(-32021)` — aborta** (3 ms) | ✔ **DEGRADADO** (5 ms) | ✔ DEGRADADO (2 ms) | ✔ pong |

El error literal de la vía dura, en las dos eras:

```
MCPError(-32021, "Client did not declare the roots capability required by resolver
                  '__main__:pedir_roots_duro'", {'requiredCapabilities': {'roots': {}}})
```

Y la intersección, idéntica en las cuatro configuraciones:

```
servidor : ["…\salidas-mcp-cabos\raiz_srv"]
cliente  : ["file:///…/raiz_srv/sub", "file:///…/raiz_fuera"]
efectiva : ["…\salidas-mcp-cabos\raiz_srv\sub"]      <- raiz_fuera descartada
```

Sin roots del cliente: `efectiva == ["…\raiz_srv"]`, la lista inmutable del servidor **intacta**.
Eso es R13 literal.

**Y funciona contra el cliente real**, no solo contra el de Python: §1.1, paso
`llamada:filex_roots_efectivos`, con Claude Code mandando su root de proyecto.

### 2.3 Tres cosas que hay que saber al portarlo

**MEDIDO, todo en `cabo2_resultados.json` y los `cabo2_stderr_*.txt`:**

1. **`t_cuerpo` confirma §2.3 de `sdk-mcp-capacidades.md`**: en 2026-07-28,
   `ctx.session.list_roots()` muere con `NoBackChannelError` incluso con el cliente
   declarando roots. **No es alternativa al resolver en la era moderna.** En 2025-11-25 sí
   funciona.
2. **La sesión sobrevive siempre.** `t_ping_final` respondió `pong` en las cuatro
   configuraciones, incluidas las dos en que `t_dura` abortó. El `-32021` mata la llamada, no
   el proceso — al contrario que el `ValidationError` de `mcp 1.8.x` ante un cliente 2.0.0.
3. **El resolver corre una vez por herramienta que lo pida, no una por sesión.** En
   2025-11-25 con roots, el cliente respondió **3 veces** a `roots/list` para 3 llamadas; en
   2026-07-28, **2 veces** para las 2 llamadas que llegaron a preguntar. Si FileX pide roots en
   `convert`, `inspect` y `batch`, cada llamada paga su viaje de ida y vuelta. **Cachearlos por
   sesión, invalidando con `list_changed`, es trabajo propio del servidor.**

### 2.4 Un detalle de diseño: cliente con roots pero lista vacía

La implementación trata **«el cliente declara la capacidad pero manda cero roots»** como
`DEGRADADO`, no como «intersección vacía → no se permite nada». Es una decisión, no una
medición: la alternativa (denegar todo) convertiría un cliente mal configurado en un servidor
inútil. Queda explícita en `cabo2_roots.py::raices_efectivas` para que se pueda revisar.

> **Veredicto: R13 pasa de IMPLEMENTABLE a IMPLEMENTADA.** El «PENDIENTE» de
> `bench/sdk-mcp-capacidades.md` §2.6 y el de `RESULTADOS-MCP.md` §10 (fila R13) quedan
> cerrados. El código de referencia es `bench/salidas-mcp-cabos/cabo2_roots.py`, 120 líneas
> con comentarios.

---

## 3. Cabo 3 — La suite de `image-worker-mcp`

`bench/mcp-refs-multimedia.md` §8.1 la dejó sin ejecutar por el `npm install`.

### 3.1 Lo que costó ponerla en marcha

**MEDIDO** (`iwm_npm_install.log`):

- `npm install` **falla de entrada**: `@rushstack/eslint-config@3.7.0` pide
  `eslint ^6 || ^7 || ^8` y el proyecto fija `eslint 9.25.1`. `ERESOLVE`. El repo se publica
  con `pnpm-lock.yaml`, y npm no perdona lo que pnpm sí.
- Con `--legacy-peer-deps`: **702 paquetes, 2 minutos, 177,3 MB en 22.880 ficheros.** Dentro de
  `repos/`, que está en `.gitignore`.

### 3.2 La suite

**MEDIDO** (`iwm_vitest.log`): **117 tests en 6 ficheros, 6,43 s, `6 passed / 117 passed`,
cero fallos.**

| Fichero | Tests | Qué prueba |
|---|---:|---|
| `tests/services/gcloud.test.ts` | 27 | subida a Google Cloud Storage, **todo con mocks** |
| `tests/services/cloudflare.test.ts` | 24 | subida a R2, **todo con mocks** |
| `tests/services/s3.test.ts` | 24 | subida a S3, **todo con mocks** |
| `tests/utils.test.ts` | 18 | validadores puros, **sin mocks** |
| `tests/tools/sharp.test.ts` | **13** | la conversión de verdad — **aquí están los 2 de HEIC** |
| `tests/tools/upload.test.ts` | 11 | orquestación, **8 `vi.mock`** |

> **El primer dato es de reparto, y es el interesante:** **75 de 117 tests (64 %) prueban las
> tres nubes**, que `RESULTADOS-MCP.md` §2 ya identificó como «backends de subida, no lógica de
> conversión». **Solo 13 tests prueban la conversión de imágenes**, que es lo único que a FileX
> le importa de este repo. Un `Test Files 6 passed` verde dice mucho menos de lo que parece.

### 3.3 Los dos tests de HEIC: el mejor criterio de aserción del carril

El fixture es `tests/assets/image1.heic`, **2.994.394 B**, un binario comprometido en el repo.
Los dos tests **desactivan los mocks** (`vi.doUnmock('sharp')`, `vi.doUnmock('libheif-js')`,
`vi.resetModules()`) y descodifican el HEIC de verdad: **1.977 ms** y **1.461 ms**.

Y verifican la salida **abriéndola** (`tests/tools/sharp.test.ts:369-380`):

```ts
const writtenBuffer = nodeFs.readFileSync(outputJpegPath);
const metadata = await sharpActual(writtenBuffer).metadata();
expect(metadata.format).toBe('jpeg');
expect(metadata.width).toBe(60);
expect(metadata.height).toBe(40);
```

Y el segundo hace lo mismo **descodificando el base64 de la respuesta**:

```ts
const outputBuffer = Buffer.from(base64Data, 'base64');
const metadata = await sharpActual(outputBuffer).metadata();
expect(metadata.format).toBe('png');
```

> **Esto es exactamente el criterio que `bench/mcp-refs-multimedia.md` §8.1 pedía y que a
> `ffmpeg-mcp-lite` le falta.** Allí `test_convert.py:20-23` se conforma con
> `"Converted successfully" in result` y `output_path.exists()`, y **un fichero de 0 bytes
> pasaría**. Aquí no pasa: el test abre el fichero escrito y afirma formato y geometría reales.

### 3.4 El contraste con `ffmpeg-mcp-lite/tests/`, que es la plantilla candidata

**MEDIDO** (esta ejecución frente a la de `mcp-refs-multimedia.md` §8.1):

| | `ffmpeg-mcp-lite` | `image-worker-mcp` |
|---|---|---|
| Tests | 32 (**29 pasan, 3 fallan**) | **117 (117 pasan)** |
| Duración | **53,19 s** | **6,43 s** |
| Ficheros de prueba | **sintéticos con `lavfi`**, cero binarios en el repo | **un HEIC de 2,99 MB comprometido** |
| Aserción típica | `exists()` + subcadena de éxito | **abre la salida y afirma formato y geometría** |
| Aislamiento | proceso real de ffmpeg | `vi.mock` de `fs` y `sharp`, **desactivados a mano** en los 2 de integración |
| `skip` por entorno | **sí** (`pytest.skip` si falta ffmpeg) | **no** |

> **Veredicto para la suite de FileX: no hay un ganador, hay que coger un eje de cada uno.**
>
> - **De `ffmpeg-mcp-lite`, la ESTRUCTURA:** fixtures sintéticas (`conftest.py:17-61`), `skip`
>   por entorno (`:37-38`), un `test_*.py` por herramienta. Se mantiene el veredicto **COPIAR
>   TAL CUAL** de `mcp-refs-multimedia.md` §8.
> - **De `image-worker-mcp`, el CRITERIO DE ASERCIÓN:** todo test termina abriendo la salida y
>   afirmando sus propiedades reales. Se mantiene el «corrige el criterio de aserción», y
>   **ahora hay un ejemplar concreto que copiar** (`sharp.test.ts:369-380`), no solo la idea.
> - **Y su velocidad viene de mockear.** 117 tests en 6,4 s frente a 32 en 53,2 s es sobre todo
>   que 104 de los 117 no tocan disco ni códecs. Ese reparto —**la gran mayoría rápidos y
>   aislados, unos pocos de integración lenta con ficheros reales**— es la forma correcta, y es
>   la única de las dos suites que lo tiene.

### 3.5 Tres cosas que la suite delata del código, y que no salían de la lectura

**MEDIDO:**

1. **El antipatrón de contenido encubierto está PROTEGIDO POR TESTS.** Los dos tests de HEIC
   afirman `resultContent.image.startsWith('data:image/jpeg;base64,')`. Es decir: devolver la
   imagen entera dentro del texto **no es un descuido, es comportamiento contratado**, y
   cualquiera que lo quite rompe la suite. Refuerza `RESULTADOS-MCP.md` §3: el patrón está
   publicado, vivo y defendido.
2. **Matiz de forma sobre §3 de `RESULTADOS-MCP.md`:** el base64 no viaja crudo, viaja con
   prefijo **`data:image/…;base64,`**. Una regla de detección escrita sobre «rachas de base64»
   lo pilla igual (el detector `_base64_dentro_del_texto()` del arnés busca rachas ≥512), pero
   conviene saber la forma exacta.
3. **La verificación de los tests es de la respuesta y del búfer, no del camino de escritura.**
   `fs.writeFileSync` está mockeado; el test captura el búfer, **lo escribe él mismo** y luego
   lo lee. Un fallo en cómo la herramienta escribe en disco **no lo atraparía**. Para FileX,
   cuya doctrina es que la salida en disco es el producto, la aserción tiene que correr sobre
   **el fichero que escribió el código bajo prueba**, no sobre un búfer reescrito por el test.

---

## 4. Cabo 4 — El deadlock en las otras 23 — **ALCANCE CERRADO el 22/08/2026**

> **Las 20 que aquí quedaron «cubiertas por la clasificación, no por ejecución» se ejecutaron** (`bench/mcp-cabos-2.md` §1): **26 de 26 cuelgan, cero excepciones.** De la primera pasada, 18 colgaron directamente y 3 respondieron en <105 ms con la salida basura **intacta** — fallos *tempranos* por entradas del arnés, no defensas del código: dos por una fuente sin pista de audio y una por `target_format="mkv"`, que ffmpeg no conoce (el nombre válido es `matroska`). Corregida la causa, **las tres cuelgan**. **Y el matiz que delimita el enmascaramiento: `_run_ffmpeg_with_fallback` convierte el deadlock en error SOLO cuando ffmpeg falla antes de llegar al muxer.**

`bench/mcp-refs-multimedia.md` §4.1 reprodujo el bloqueo end-to-end en **una** de las 27
herramientas y dejó las otras 23 en **PENDIENTE**.

### 4.1 Método: agrupar y probar un representante — y por qué es legítimo

**Se agrupó y se probó por grupos, no una por una.** La justificación tiene dos patas, y la
primera es exhaustiva:

**(a) La clasificación de las 27 es exhaustiva y automática, no muestral.**
`cabo4_clasificar.py` recorre el **AST** de `server.py` (no `grep`), localiza los 27
`@mcp.tool()`, y para cada uno cuenta las invocaciones alcanzables **siguiendo también los
helpers de módulo que llama**. Resultado (`cabo4_clasificacion.json`), que **reproduce
exactamente** el recuento manual de `mcp-refs-multimedia.md` §4.1:

| Grupo | n | Mecanismo | `overwrite_output()` | `-y` | `stdin=` |
|---|---:|---|---:|---:|---:|
| **G1** — vía `_run_ffmpeg_with_fallback` (`server.py:332-348`) | **9** | ffmpeg-python, 2 `.run()` por llamada | **0** | 0 | **0** |
| **G2** — ffmpeg-python en el cuerpo | **15** | 1 a 6 `.run()` según la herramienta | **0** | 0 | **0** |
| **G3** — mixtas (`concatenate_videos`, `add_b_roll`) | **2** | ffmpeg-python **y** `subprocess` | **0** | **7** | **0** |
| **G4** — no toca ffmpeg (`health_check`) | **1** | — | — | — | — |

**Cero `overwrite_output()` en todo el fichero. Cero `stdin=` en todo el fichero.** Las 27 están
cubiertas por la clasificación; lo que se muestrea es solo la *ejecución*.

**(b) La condición de disparo es una propiedad del estado del disco, no de la herramienta.**
Todas las invocaciones de G1, G2 y la rama ffmpeg-python de G3 construyen el proceso igual: sin
`overwrite_output()` y sin fijar `stdin`. Lo único que las diferencia es *qué* ffmpeg ejecutan.
Por eso basta con probar un representante por grupo **en las dos condiciones** —salida
preexistente y salida nueva— para aislar la variable.

**Diseño defensivo del arnés** (`cabo4_deadlock.py`, regla 4 del encargo): JSON-RPC crudo por
stdio sin SDK; lector de `stdout` en hilo **demonio** con cola; **timeout duro por llamada**;
`taskkill /F /T /PID` sobre el **árbol** al vencer; **una sesión nueva por caso**; e inventario
de `ffmpeg.exe` antes y después de cada caso para detectar huérfanos.

### 4.2 Resultado: 6 de 6 cuelgan, y los controles responden en menos de 700 ms

**MEDIDO** (`cabo4_resultados.json`, timeout 40 s):

| Caso | Grupo | Salida preexistente | Veredicto | ms |
|---|---|---|---|---:|
| `health_check` | G4 | — | RESPONDE | 11,6 |
| `set_video_resolution` | G1 | **sí** | **DEADLOCK** | >40.000 |
| `set_video_codec` | G1 | **sí** | **DEADLOCK** | >40.000 |
| `set_video_resolution` | G1 | no | RESPONDE | **694,9** |
| `convert_video_properties` | G2 | **sí** | **DEADLOCK** | >40.000 |
| `trim_video` | G2 | **sí** | **DEADLOCK** | >40.000 |
| `convert_video_properties` | G2 | no | RESPONDE | **553,6** |
| `concatenate_videos` (2 vídeos → rama `subprocess`) | G3 | **sí** | **DEADLOCK** | >40.000 |
| `concatenate_videos` (1 vídeo → rama ffmpeg-python `:851`) | G3 | **sí** | **DEADLOCK** | >40.000 |

> **El mecanismo queda confirmado y su alcance acotado: las 24 herramientas que llegan a ffmpeg
> solo por ffmpeg-python (9 de G1 + 15 de G2) cuelgan la sesión MCP entera en cuanto la ruta de
> salida ya existe.** El contraste es de tres órdenes de magnitud: 554-695 ms si la salida es
> nueva, infinito si existe.
>
> Se reprodujo end-to-end en **5 herramientas distintas** (`set_video_resolution`,
> `set_video_codec`, `convert_video_properties`, `trim_video`, `concatenate_videos`), más la
> `convert_video_format` del informe anterior: **6 de las 26 que tocan ffmpeg**. Las 20
> restantes quedan cubiertas por la clasificación exhaustiva de §4.1(a), **no por ejecución**;
> eso sigue siendo **PENDIENTE** en sentido estricto, y así se marca.

Sobre el «éxito huérfano»: en un caso (`trim_video`) sobrevivió **un `ffmpeg.exe` huérfano** al
`taskkill /F /T` del servidor; el arnés lo detectó por el inventario y lo mató aparte. Ese es el
mismo fenómeno de `RESULTADOS-MCP.md` §8.1 —los 13 minutos de `ffmpeg-mcp-lite`— y **confirma
que matar el árbol del servidor no siempre alcanza al nieto.**

### 4.3 El hallazgo que no se buscaba: **`-y` NO basta**

`concatenate_videos` con 2 vídeos toma la rama de `subprocess`, y **sus 7 invocaciones pasan
`-y`** (`server.py:891, :908, :961, :994, :1016` y las dos de xfade). Según la teoría de §4.1
no debería colgarse nunca. Se repitió el caso tres veces (`cabo4_g3_repeticiones.json`):

```
1  DEADLOCK  (60,2 s)
2  RESPONDE  ( 2,8 s)   "Videos concatenated successfully to …"
3  DEADLOCK  (60,2 s)
```

**Intermitente, 2 de 3.** El diagnóstico en caliente (`cabo4_g3_diagnostico.py`) fotografió el
árbol de procesos cada 10 s durante 71 s. El proceso colgado es, literalmente:

```
ffmpeg -i …/trivial.mp4 -vf scale=640:480 -r 24.0 -c:v libx264 -c:a aac -y
       C:\Users\krato\AppData\Local\Temp\tmp5t42s7nw\norm_0.mp4
```

**Con `-y`, y sobre una ruta temporal recién creada que no existía.** El prompt de
sobrescritura no puede ser la causa. Un clip de 5 s y 552 KB que normalmente tarda **~330 ms**
llevaba **71 s** sin terminar.

Se aislaron las variables con tres controles:

**Control 1 — una sola invocación de ffmpeg, fuera de MCP** (`cabo4_ffmpeg_control.json`,
5 repeticiones por caso, salida siempre preexistente, `stdout`/`stderr` drenados con hilos y
`stdin` **mantenido abierto y mudo**):

| Caso | Colgadas | Mediana |
|---|---:|---:|
| **sin `-y`**, `stdin` = tubería abierta | **5/5** | — |
| con `-y`, `stdin` = tubería abierta | 0/5 | 191 ms |
| con `-y -nostdin`, `stdin` = tubería | 0/5 | 184 ms |
| sin `-y`, `stdin=DEVNULL` | 0/5 | 42 ms (sale con *«Not overwriting - exiting»*) |
| con `-y`, `stdin=DEVNULL` | 0/5 | 185 ms |

*(Nota metodológica: la primera versión de este control usaba `p.wait()` sin drenar las
tuberías y colgaba en 4 de 5 casos — el bloqueo era del arnés, no de ffmpeg. La segunda usaba
`communicate()`, que **cierra `stdin`** y hacía que ffmpeg leyera EOF y decidiera solo. Se
documentan las dos porque son la trampa exacta en la que cae quien mida esto.)*

**Control 2 — la secuencia completa de `concatenate_videos`, fuera de MCP**
(`cabo4_secuencia.json`): las mismas 3 invocaciones con `-y`, 5 repeticiones, `stdin` = tubería
muda **o** `DEVNULL`. **0 de 10 secuencias colgadas en los dos modos.** Una tubería cualquiera
no basta para reproducirlo.

**Control 3 — el A/B decisivo, DENTRO de una sesión MCP real** (`cabo4_srv_stdin.py` +
`cabo4_stdin_ab.json`). Un servidor MCP mínimo escrito para esto, con dos herramientas idénticas
salvo en una línea de la construcción del proceso, ejecutando la misma secuencia con `-y` en
todas partes y rutas de salida nuevas:

| Herramienta | Diferencia | Colgadas | Detalle |
|---|---|---:|---|
| `conv_heredado` | `stdin` **no se toca** → hereda la tubería JSON-RPC | **2/5** | `norm_0` colgó a los 20,3 s y a los 27,7 s |
| `conv_devnull` | **`stdin=subprocess.DEVNULL`** | **0/5** | 5/5 completas |

> **MEDIDO, y es el resultado más transferible del cabo:**
>
> **`-y` es necesario pero NO suficiente. El `stdin` heredado cuelga procesos ffmpeg que tienen
> todas las banderas correctas y escriben sobre rutas que no existen.**
>
> Y la variable que lo dispara es más estrecha de lo que parecía: no es «una tubería», es **la
> tubería que el servidor MCP está leyendo a la vez**. Los controles 1 y 2 usan tuberías mudas y
> no cuelgan nunca; el control 3, con la tubería JSON-RPC viva, cuelga 2 de 5. El hijo y el
> bucle de lectura del servidor compiten por el mismo descriptor.
>
> **Esto convierte la nota de orden de `RESULTADOS-MCP.md` §8.1 —«el orden importa:
> `stdin=DEVNULL` primero, las banderas después»— en un resultado causal medido, y le cambia el
> estatus: no es una preferencia de estilo, es la única de las dos defensas que cierra el fallo
> entero.** Una revisión que se conforme con «¿lleva `-y`?» da por bueno un código que cuelga la
> sesión el 40 % de las veces.
>
> **Y `-nostdin` tampoco basta por sí solo.** En el control 1 empata con `-y`, pero es otra
> bandera más que hay que acordarse de poner en cada punto de invocación — que es justo lo que
> `video-audio-mcp` demuestra que no ocurre. **Solo `stdin=DEVNULL` en el constructor del
> proceso no se puede olvidar en un punto de invocación, porque no hay puntos de invocación:
> hay uno.**

### 4.4 Qué cambia en las reglas

- **`RESULTADOS-MCP.md` §8.1 (regla nueva) y §9.5 de `mcp-refs-multimedia.md`: CONFIRMADAS y
  REFORZADAS.** El «alcance verificado» pasa de 1 herramienta a 6, y la clasificación de las 27
  pasa de recuento manual a AST reproducible.
- **Se añade la razón:** `stdin=DEVNULL` no es «además de» las banderas, es **la** defensa; las
  banderas son higiene. El orden de la regla queda justificado con un A/B.
- **`taskkill /F /T` sobre el servidor no garantiza matar al nieto.** Un `ffmpeg.exe` sobrevivió.
  FileX necesita **inventario explícito de los procesos que lanza** (job object en Windows,
  grupo de procesos en POSIX), no confiar en la relación padre-hijo.

---

## 5. Cabo 5 — La ventana TOCTOU real de FileX

**R8** («copiar la entrada a un *staging* privado antes de pasarla a un motor externo») se
justificaba así: la ventana entre validar la ruta y que ffmpeg termine de leerla son **minutos**,
y quien lee es **otro proceso que no conoce la lista blanca**. Aquí se mide.

### 5.1 La ventana: es el 99,6 % de la conversión

**Método** (`cabo5_toctou.py`): mientras ffmpeg convierte, una sonda intenta `os.replace()`
sobre la entrada cada 5 ms. Mientras el motor la tiene abierta, en Windows el renombrado falla;
el primer éxito marca la liberación. Nada toca `corpus/`: todo se copia antes a un directorio de
trabajo.

**MEDIDO** (`cabo5_toctou.json`):

| Caso | Bytes | Conversión total | El motor **abre** a los | Entrada **inmovilizada** | % de la conversión |
|---|---:|---:|---:|---:|---:|
| `trivial.png` → webp | 316 | 63,6 ms | 31,0 ms | **28,5 ms** | 44,8 % |
| `tipico.mp4` → remux (`-c copy`) | 16.246.490 | 342,7 ms | 38,5 ms | **283,2 ms** | 82,6 % |
| `tipico.mp4` → x264 CPU (`preset medium`) | 16.246.490 | **9.794,5 ms** | 25,3 ms | **9.758,1 ms** | **99,6 %** |
| `fuente_4k.mp4` → remux (`-c copy`) | 127.932.819 | 401,9 ms | 52,7 ms | **329,5 ms** | 82,0 % |
| `fuente_4k.mp4` → 720p x264 CPU | 127.932.819 | 1.893,4 ms | 23,3 ms | **1.862,8 ms** | 98,4 % |

> **La ventana es, en la práctica, la conversión entera.** El motor abre la entrada a los
> **23-53 ms** y no la suelta hasta terminar. En una conversión que dure minutos, la ventana
> dura minutos. **El orden de magnitud que R8 daba por supuesto está medido.**
>
> Y hay una **segunda ventana, previa y más peligrosa de lo que parece**: los **23-53 ms** entre
> que el proceso arranca y abre el fichero. Ahí no hay ningún bloqueo, en ningún sistema.

### 5.2 Pero el vector clásico NO funciona — y el que funciona sí

Que la entrada esté abierta mucho tiempo no dice nada por sí solo: hay que saber **qué** puede
hacer un tercero durante ese tiempo. Se probaron cuatro vectores a los 3 s de una
transcodificación x264 de `tipico.mp4` (`cabo5_envenenamiento.py`), y los mismos cuatro en
**Linux/WSL2** con un lector en streaming (`cabo5_linux.py`).

**MEDIDO. Windows** (`cabo5_envenenamiento.json`; conversión limpia de referencia:
8.136 ms, 15.450.077 B, `sha 00084f42c41d40d2`):

| Vector | ¿Permitido? | Error del sistema | ¿Cambió la salida? |
|---|---|---|---|
| (a) `os.replace(entrada, otro)` | **NO** | `PermissionError 5: Acceso denegado` | idéntica |
| (b) `os.remove(entrada)` | **NO** | `PermissionError 32: … utilizado por otro proceso` | idéntica |
| (c) **escritura EN SITIO** (`r+b`, 64 KB de ceros al 60 %) | **SÍ** | — | **`sha 5db86bacf3802092`, 15.502.924 B — DISTINTA** |
| (d) renombrar el **directorio padre** | **NO** | `PermissionError 5: Acceso denegado` | idéntica |

**MEDIDO. Linux / WSL2** (`cabo5_linux.json`, fichero de 8 MiB, lector que abre, lee la mitad,
duerme 3 s y termina de leer):

| Vector | ¿Permitido? | Qué leyó el motor |
|---|---|---|
| (a) `os.replace` | **SÍ** | `sha b16bd32b101132fd` — **el ORIGINAL** |
| (b) `os.remove` | **SÍ** | `sha b16bd32b101132fd` — **el ORIGINAL** |
| (c) **escritura EN SITIO** | **SÍ** | **`sha 1e73901850ea8117` — EL ENVENENADO** |
| (d) renombrar el directorio padre | **SÍ** | `sha b16bd32b101132fd` — **el ORIGINAL** |

> **El resultado es el mismo en los dos sistemas por dos razones opuestas, y eso es lo que le da
> fuerza.**
>
> - En **Windows**, el bloqueo obligatorio del sistema **deniega** sustituir, borrar y mover.
> - En **POSIX** las tres **se permiten**, pero el descriptor abierto del motor sigue apuntando
>   al inodo original, así que **lee lo mismo de todas formas**.
> - **En los dos, el único vector que cambia lo que el motor lee es escribir EN SITIO sobre el
>   mismo inodo.** Y en los dos funciona.
>
> **Esto corrige el mecanismo con el que estaba escrita R8, y la refuerza.** La justificación
> decía «sustituir la entrada por otra cosa mientras el motor lee»; medido, **ese vector concreto
> no funciona en ninguna de las dos plataformas durante la ventana de lectura**. Lo que funciona
> es la modificación en sitio: la ruta sigue siendo la validada, el inodo sigue siendo el
> validado, `realpath` sigue dando lo mismo, **y los bytes son otros**. Ninguna validación de
> rutas —por buena que sea— lo detecta, porque no hay nada que detectar en la ruta.
>
> **Y salió con `returncode = 0`.** ffmpeg convirtió el fichero envenenado y declaró éxito. Un
> verificador que compruebe «la salida es un MP4 válido con la duración esperada» lo da por
> bueno: la salida es coherente consigo misma. Es el mismo tipo de fallo que el WebP ampliado
> ×9,75 de `RESULTADOS-MCP.md` §7, y refuerza el mismo punto: **la coherencia interna de la
> salida no prueba que la entrada fuera la que se validó.**

**Dónde sí funciona el vector clásico:** en los **23-53 ms** anteriores a que el motor abra el
fichero (§5.1). Ahí (a) y (d) sí funcionan, en las dos plataformas. Es una ventana corta, pero
la propia R8 la cierra igual, y por eso el staging debe hacerse **inmediatamente después de
validar**, no «en algún momento antes de llamar al motor».

### 5.3 Cuánto cuesta la mitigación

**MEDIDO** (`cabo5_toctou.json`, `shutil.copyfile`, mediana de 5):

| Fichero | Bytes | Copia al staging | Velocidad |
|---|---:|---:|---:|
| `trivial.png` | 316 | **1,0 ms** | (por debajo de la resolución útil del reloj) |
| `tipico.mp4` | 16.246.490 | **10,0 ms** | 1.625 MB/s |
| `fuente_4k.mp4` | 127.932.819 | **78,6 ms** | 1.628 MB/s |

Frente a la operación:

| Operación | Coste de la operación | Copia | **Copia / operación** | Reducción de la ventana |
|---|---:|---:|---:|---:|
| `trivial.png` → webp | 63,6 ms | 1,0 ms | **1,6 %** | 28,5 ms → ~1 ms (**×28**) |
| `tipico.mp4` → x264 CPU | 9.794,5 ms | 10,0 ms | **0,10 %** | 9.758 ms → 10 ms (**×976**) |
| `tipico.mp4` → remux `-c copy` | 342,7 ms | 10,0 ms | **2,9 %** | 283 ms → 10 ms (**×28**) |
| `fuente_4k.mp4` → 720p x264 | 1.893,4 ms | 78,6 ms | **4,2 %** | 1.863 ms → 79 ms (**×24**) |
| `fuente_4k.mp4` → remux `-c copy` | 401,9 ms | 78,6 ms | **19,6 %** | 330 ms → 79 ms (**×4,2**) |

> **La pregunta del encargo era: «si copiar cuesta más que convertir, R8 necesita matizarse».
> Para convertir, no cuesta más: el peor caso medido es el 19,6 %, y el caso central es el
> 0,10 %.** La copia va a **1,6 GB/s**, más rápido de lo que ffmpeg lee para remuxear
> (~300 MB/s). **R8 se confirma, y su precio está medido: entre el 0,1 % y el 20 % de la
> operación, a cambio de reducir la ventana entre ×4 y ×976.**

### 5.4 Donde R8 **sí** necesita una excepción explícita: `inspect`

`inspect` no recorre el fichero: lee cabeceras. **MEDIDO** (`cabo5_inspect.json`, mediana de 5):

| Fichero | Bytes | `ffprobe` | Copia | **Copia / `inspect`** |
|---|---:|---:|---:|---:|
| `trivial.png` | 316 | 36,1 ms | 1,0 ms | 0,03 |
| `tipico.mp4` | 16.246.490 | 44,6 ms | 10,0 ms | 0,22 |
| `patologico_16bit.tif` | 72.001.016 | 70,2 ms | 45,6 ms | 0,65 |
| **`fuente_4k.mp4`** | **127.932.819** | **57,8 ms** | **76,1 ms** | **1,32** |

> **MEDIDO: para `inspect` sobre un fichero de 122 MB, copiar al staging cuesta un 32 % MÁS que
> la propia operación.** El punto de cruce está alrededor de los **90-100 MB** en esta máquina:
> `ffprobe` tarda 36-70 ms **casi con independencia del tamaño**, mientras que la copia crece
> linealmente.
>
> **Matiz propuesto para R8**, que es el único que sale de este cabo:
>
> > R8 se aplica a **toda operación que entregue la ruta a un motor externo que vaya a leer el
> > contenido**. Para `inspect`, donde el motor solo lee cabeceras y la ventana es de decenas de
> > ms, el staging **duplica el coste de la operación sin reducir la ventana en la misma
> > proporción**. La alternativa para ese camino es hacer la lectura de metadatos **en proceso**
> > —que `bench/coste-verificacion.md` ya midió **145× más barata** que invocar `ffprobe`— con lo
> > que desaparecen a la vez el motor externo, la ventana y la necesidad de staging.
>
> Nótese que esto **converge con una corrección ya aplicada**: `RESULTADOS-MCP.md` §12 quitó
> «(`ffprobe`)» del contrato de verificación por coste. Aquí se llega al mismo sitio por
> seguridad. **El camino de `inspect` no debe salir del proceso.**

### 5.5 ¿Sirven `O_NOFOLLOW`, `dir_fd=` y el descriptor abierto en vez del staging?

La nota del encargo apuntaba a que Python permite lo que Node no. **Se comprobó, y la respuesta
es NO, por dos razones independientes.**

**Razón 1 — en Windows no existen. MEDIDO** (`cabo5_toctou.json → alternativas_posix`,
Python 3.11.9, `win32`):

| Primitiva | Windows | WSL2 (Linux, Python 3.14.4) |
|---|---|---|
| `os.O_NOFOLLOW` | **no existe** | sí |
| `os.O_PATH` | **no existe** | sí |
| `os.supports_dir_fd` | **conjunto vacío** | 17 funciones (`open`, `stat`, `rename`, `unlink`…) |
| `os.supports_fd` | solo `stat` y `truncate` | amplio |
| `/proc/self/fd`, `/dev/fd` | **no existen** | sí |
| `st_dev` / `st_ino` no nulos | **sí** (`553714096` / `562949955168582`) | sí |

FileX se entrega en Windows. **La mitad del arsenal POSIX no está disponible ahí**, y una regla
de confinamiento que solo funciona en un sistema operativo no es una regla.

**Razón 2 — y esta vale también en Linux: el descriptor no cierra el vector que funciona.**
Mantener el fd abierto y comprobar `st_dev`/`st_ino` protege contra **sustituir el fichero** —
que es exactamente el vector que §5.2 midió como **inoperante en las dos plataformas**. No
protege contra **escribir en sitio**, que es el que sí funciona: el inodo es el mismo, `st_dev`
y `st_ino` no cambian, y los bytes sí.

**Razón 3 — no hay forma de entregarle un descriptor a un motor externo.** ffmpeg, LibreOffice
e ImageMagick reciben **una ruta**. En Linux se podría pasar `/proc/self/fd/N`, pero eso es
volver a abrir por ruta (y LibreOffice no lo acepta); en Windows no existe el equivalente.

> **Veredicto: las primitivas POSIX son un COMPLEMENTO de la validación, no un sustituto del
> staging.**
>
> - **Dónde sí valen:** en el momento de **validar**, para cerrar la carrera de symlinks
>   (`O_NOFOLLOW` + `dir_fd` recorriendo la ruta segmento a segmento). Ahí son mejores que
>   `realpath`. Es lo que R7 pide y en Linux se puede hacer bien.
> - **Dónde no valen:** para proteger la **lectura** que hace otro proceso. Ahí la única defensa
>   medida es **copiar los bytes a un sitio donde el atacante no llegue**, que es R8 literal.

### 5.6 Qué cambia en las reglas

| Regla | Estado tras este cabo |
|---|---|
| **R8** (staging privado) | **CONFIRMADA**, con el mecanismo corregido (escritura en sitio, no sustitución), la ventana medida (99,6 % de la conversión) y el precio medido (0,1 %-19,6 %). **Se le añade la excepción de `inspect`** (§5.4) |
| **R7** (resolver enlaces en cada llamada) | Confirmada, y **se le puede añadir** `O_NOFOLLOW` + `dir_fd` **en Linux**; en Windows no hay equivalente y hay que quedarse con `realpath` por llamada |
| Contrato de verificación (`PLAN-ORQUESTADOR.md` §4.2) | **Se le abre un hueco nuevo:** una entrada envenenada en sitio produce una salida **internamente coherente** y `returncode 0`. Los cuatro puntos del contrato la dan por buena. La defensa no es un quinto punto de verificación, es **hacer el hash de la entrada en el staging y no volver a mirar el original** |

---

## 6. Qué cambia, en una tabla

| # | Documento y sitio | Qué dice hoy | Qué mide este informe |
|---|---|---|---|
| 1 | `RESULTADOS-MCP.md` §9.1, fila «Anotar `readOnlyHint`/`destructiveHint`» | Regla **confirmada**; anotar sería «una ventaja diferencial real» | **MATIZAR.** Contra Claude Code 2.1.238 las anotaciones **no llegan al modelo ni cambian el permiso** (§1.2). La regla sigue siendo correcta, pero **la advertencia de seguridad tiene que ir en la `description`, y la defensa en el núcleo** |
| 2 | `RESULTADOS-MCP.md` §2 (pregunta 6): «0,93 tokens por byte» | Cifra única para «inyectar contenido» | **PRECISAR.** 0,93 tok/B es la vía **base64 dentro de texto**. La vía `ImageContent` nativo cuesta **por píxel**: 2.814 tok medidos para 1920×1080 (§1.3). La conclusión —no hay umbral— no cambia |
| 3 | `RESULTADOS-MCP.md` §10, fila **R13** | «**PENDIENTE:** verificar `list_roots()` en el SDK Python» | **CERRADA.** Patrón condicional escrito y demostrado en 4 configuraciones + contra el cliente real (§2). Código: `cabo2_roots.py` |
| 4 | `bench/sdk-mcp-capacidades.md` §2.6, los dos PENDIENTE | Patrón condicional sin escribir; clientes reales sin probar | **CERRADOS los dos** (§1 y §2) |
| 5 | `bench/sdk-mcp-capacidades.md` §2.4 (idempotencia por el doble paso de `Resolve`) | Regla obligatoria | **SIGUE SIENDO NECESARIA, PERO NO URGENTE.** Claude Code negocia 2025-11-25, donde `Resolve` usa la vía clásica y el cuerpo corre **una** vez (§1.5) |
| 6 | `bench/mcp-refs-multimedia.md` §8.1, «PENDIENTE: no se ejecutó la suite de `image-worker-mcp`» | Pendiente | **EJECUTADA.** 117 tests, 6,43 s, 0 fallos; los 2 de HEIC verifican la salida abriéndola (§3) |
| 7 | `RESULTADOS-MCP.md` §8.1 / §11: `ffmpeg-mcp-lite/tests` como plantilla | «la estructura tal cual, corrigiendo el criterio de aserción» | **CONFIRMADO, y ahora hay el ejemplar concreto** que copiar para la aserción (`sharp.test.ts:369-380`), más el reparto correcto: muchos rápidos con mocks, pocos de integración lenta (§3.4) |
| 8 | `RESULTADOS-MCP.md` §8.1: «Reproducido end-to-end en **una**; el resto PENDIENTE» | 1 de 27 | **6 de 26 reproducidas**, clasificación de las 27 por AST, y controles de las dos condiciones (§4.2) |
| 9 | `RESULTADOS-MCP.md` §8.1: «`stdin=DEVNULL` primero, las banderas después» | Nota de orden | **RESULTADO CAUSAL MEDIDO.** Con `-y` en todas partes y rutas nuevas, `stdin` heredado cuelga **2/5**; `stdin=DEVNULL`, **0/5** (§4.3). `-y` es necesario y **no suficiente** |
| 10 | `RESULTADOS-MCP.md` §10, **R8** | Justificada por «sustituir la entrada mientras el motor lee» | **CONFIRMADA con el mecanismo corregido.** Sustituir **no funciona** en Windows (bloqueo) ni en Linux (el fd sigue en el inodo viejo); **escribir en sitio sí, en las dos** (§5.2). Ventana: **99,6 %** de la conversión. Precio: **0,1 %-19,6 %** |
| 11 | `RESULTADOS-MCP.md` §10, **R8** (alcance) | Sin excepciones | **AÑADIR EXCEPCIÓN.** Para `inspect` sobre ficheros grandes el staging cuesta **1,32×** la operación (§5.4). La salida correcta es leer metadatos **en proceso**, lo que ya pedía `bench/coste-verificacion.md` por coste |
| 12 | `RESULTADOS-MCP.md` §13, «Repetir la fase B del TOCTOU en Linux/WSL» | Pendiente | **PARCIALMENTE CERRADO** para el caso de lectura por un motor externo (§5.2, `cabo5_linux.json`). **Sigue PENDIENTE** la carrera de symlinks contra `filesystem` en Linux, que es otra cosa |

---

## 7. Lo que sigue pendiente

| Pendiente | Por qué importa | De dónde sale |
|---|---|---|
| Las **20 herramientas de `video-audio-mcp` no ejecutadas** | La clasificación por AST las cubre; la ejecución no. Es exhaustividad, no duda sobre el mecanismo | §4.2 |
| Si Claude Code emite `notifications/roots/list_changed` | Decide si FileX puede cachear los roots por sesión | §1.7 |
| Si Claude Code expone **recursos y prompts** al modelo | Si no lo hace, declararlos es coste sin retorno | §1.7 |
| Si las herramientas MCP llegan **diferidas** de forma general | Cambiaría el modelo de coste de catálogo de `RESULTADOS-MCP.md` §4 | §1.7 |
| El **efecto de un catálogo grande sobre la elección** del modelo | Sigue sin medirse en todo el proyecto | heredado |
| La carrera de **symlinks en Linux** contra `servers/filesystem` | En Windows el 79 % de los intentos falló por bloqueo de fichero | heredado |
| El punto de cruce exacto **`inspect` vs staging** en otras máquinas | Aquí está en ~90-100 MB; depende del disco | §5.4 |

---

## 8. Índice de la evidencia

Todo en **`bench/salidas-mcp-cabos/`**.

| Ruta | Contenido |
|---|---|
| `mcp.json.bak` | Copia de `.mcp.json` previa a tocarla; la restauración se hizo desde aquí |
| `cabo1_srv_2x.py` | Servidor MCP sobre `mcp 2.0.0` con anotaciones, `_meta`, `ImageContent`, salida estructurada, recurso y prompt |
| `cabo1_escribir_mcpjson.py` | Alta y baja del servidor en la `.mcp.json` **del proyecto** (`add` / `restore`) |
| `cabo1_solo.mcp.json` | Config de proyecto usada con `--mcp-config --strict-mcp-config` |
| `cabo1_srv_log.jsonl` | **La radiografía del cliente real**: protocolo, `clientInfo`, capacidades, roots, `request_meta` |
| `cabo1_claude_run1..3.json`, `cabo1_permisos.json` | Sesiones de Claude Code: roots, anotaciones vistas, `ImageContent`, denegación de permiso |
| `cabo1_ab_imagen.json` / `cabo1_ab_texto.json` | A/B del coste en tokens de `ImageContent` frente a texto |
| `cabo1_claude_mcp_list.txt` | `claude mcp list` con el servidor en «⏸ Pending approval» |
| **`cabo2_roots.py`** | **El patrón condicional + la intersección R13. Es el entregable del cabo 2** |
| `cabo2_srv.py` / `cabo2_cli.py` / `cabo2_resultados.json` | Servidor de contraste (dura / condicional / cuerpo) y la matriz 2 eras × 2 clientes |
| `cabo2_stderr_*.txt` | Trazas del servidor en las cuatro configuraciones |
| `iwm_npm_install.log` / `iwm_vitest.log` | `npm install --legacy-peer-deps` (702 paquetes) y los 117 tests |
| `cabo4_clasificar.py` / `cabo4_clasificacion.json` | Clasificación **exhaustiva por AST** de las 27 herramientas |
| `cabo4_deadlock.py` / `cabo4_resultados.json` | Arnés con timeout duro y muerte del árbol; 9 casos, 6 deadlocks |
| `cabo4_g3_repeticiones.*`, `cabo4_g3_diagnostico.*` | La intermitencia 2/3 y la fotografía del árbol de procesos colgado |
| `cabo4_ffmpeg_control.*`, `cabo4_secuencia.*` | Controles a nivel de ffmpeg: `-y`, `-nostdin`, `stdin=DEVNULL` |
| **`cabo4_srv_stdin.py` / `cabo4_stdin_ab.json`** | **El A/B decisivo dentro de una sesión MCP: 2/5 frente a 0/5** |
| `cabo4_stderr_*.txt` | Trazas de cada sesión de `video-audio-mcp` |
| `cabo5_toctou.py` / `cabo5_toctou.json` | Ventana medida, coste del staging, disponibilidad de las primitivas POSIX |
| **`cabo5_envenenamiento.py` / `.json`** | **Los cuatro vectores en Windows. (c) envenena la salida con `returncode 0`** |
| **`cabo5_linux.py` / `.json`** | **Los mismos cuatro en WSL2. Mismo resultado por la razón opuesta** |
| `cabo5_inspect.py` / `cabo5_inspect.json` | El único caso en que copiar cuesta más que la operación |

**Limpieza.** Los directorios de trabajo (`cabo4_trabajo`, `cabo4_ffmpeg`, `cabo5_trabajo`,
`cabo5_env`, `cabo5_staging`) sumaban **515 MB** y **se han borrado**; el directorio de salidas
ocupa **338 KB**. El `node_modules` de `image-worker-mcp` (**177,3 MB**, 22.880 ficheros) se
conserva dentro de `repos/`, que está en `.gitignore`, para que la suite se pueda reejecutar.
