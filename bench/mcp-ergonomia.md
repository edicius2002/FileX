# Ergonomía MCP medida: `markitdown-mcp` frente a `docling-mcp`

**Qué se probó y por qué.** `analysis/00-mcp-patrones.md` estableció *leyendo el código* que `markitdown-mcp`
devuelve el documento entero como cadena y que `docling-mcp` devuelve una clave de caché. Este carril
comprueba ese análisis **ejecutando ambos servidores de verdad**, por stdio, con un cliente MCP real, y
midiendo lo único que importa para un agente: **cuántos tokens entran en su contexto**, qué mensaje ve
cuando algo falla, cuánto tarda la primera llamada frente a las siguientes, y qué rutas acepta.

Todo lo que sigue son cifras medidas en esta máquina, no estimaciones.

- Fecha: 2026-08-19. Windows 10, Python 3.11.9, RTX 3060 12 GB.
- Contador de tokens: `tiktoken`, codificación `o200k_base`, aplicada al **texto que el cliente MCP
  inyecta en el contexto del modelo** (los bloques `content` de la respuesta de la herramienta).
- Arnés: `bench/salidas-mcp/mcp_probe.py` (cliente MCP genérico) + specs JSON reproducibles.
- Resultados crudos: `bench/salidas-mcp/res_*.json`; `stderr` de cada servidor en `bench/salidas-mcp/stderr_*.log`.

---

## 1. Instalación y configuración: la que funciona, y lo que costó

### 1.1 El primer hallazgo es de integración: los dos servidores **no caben en el mismo entorno**

| Servidor | Versión | Exige |
|---|---|---|
| `markitdown-mcp` | 0.0.1a4 (PyPI) | `mcp~=1.8.0`, `markitdown[all]>=0.1.1,<0.2.0` |
| `docling-mcp` | 3.1.0 (clon local, `f954859`) | `mcp[cli]>=2.0.0,<3.0.0`, `docling-slim[service-client]~=2.92` |

`mcp~=1.8.0` y `mcp>=2.0.0` son incompatibles. **No hay un `pip install` que instale ambos servidores en
un mismo venv.** Hubo que crear dos entornos, y eso no es una anécdota local: es el coste real de
integrar dos MCP de conversión en la misma máquina, y es un argumento a favor de que FileX se entregue
como **un solo binario/servidor** en vez de como una constelación de servidores por motor.

Efecto colateral visible en el protocolo: `markitdown-mcp` negocia `protocolVersion 2024-11-05` y
`docling-mcp` `2025-11-25`. Dos servidores de conversión en el mismo cliente hablan **dos versiones
distintas del protocolo**.

### 1.2 Entornos creados

```bash
# A) markitdown-mcp -> venv propio, aislado (mcp 1.8.x)
py -3.11 -m venv .venv-mcp-md
.venv-mcp-md/Scripts/python.exe -m pip install markitdown-mcp tiktoken
# -> markitdown-mcp 0.0.1a4, markitdown 0.1.7, mcp 1.8.1, pdfminer.six 20260107

# B) docling-mcp -> dentro de .venv-ai, SIN romper torch/CUDA
#    Se instala con --no-deps y se añaden a mano solo las piezas que faltaban.
.venv-ai/Scripts/python.exe -m pip install "mcp[cli]>=2.0.0,<3.0.0" python-dotenv tiktoken
.venv-ai/Scripts/python.exe -m pip install --no-deps ./repos/ai-engines/docling-mcp
```

`--no-deps` es deliberado: la dependencia declarada `docling-slim[service-client]~=2.92` habría podido
tocar `docling-slim`/`docling-core`, ya presentes y funcionando. Con la instalación manual, `pip` solo
añadió paquetes nuevos (`mcp`, `mcp-types`, `starlette`, `uvicorn`, `httpx2`, `pyjwt`, `cryptography`…)
y **no degradó nada**.

Verificación posterior obligatoria: **`torch.cuda.is_available() -> True`, `torch 2.6.0+cu124`. El venv
de IA sigue intacto.**

### 1.3 `D:\Work\research\FileX\.mcp.json` — ámbito de proyecto, exactamente esto

```json
{
  "mcpServers": {
    "markitdown": {
      "type": "stdio",
      "command": "D:\\Work\\research\\FileX\\.venv-mcp-md\\Scripts\\markitdown-mcp.exe",
      "args": [],
      "env": { "MARKITDOWN_ENABLE_PLUGINS": "false" }
    },
    "docling": {
      "type": "stdio",
      "command": "D:\\Work\\research\\FileX\\.venv-ai\\Scripts\\docling-mcp-server.exe",
      "args": ["--transport", "stdio", "conversion"],
      "env": {
        "DOCLING_MCP_CONVERSION_MODE": "local",
        "DOCLING_MCP_DO_OCR": "false",
        "DOCLING_MCP_DO_TABLE_STRUCTURE": "true",
        "DOCLING_MCP_KEEP_IMAGES": "false"
      }
    }
  }
}
```

*No se ha tocado ninguna configuración global (`~/.claude.json`) ni de usuario.* La verificación de que
esta configuración funciona se hizo levantando ambos servidores por stdio **con exactamente ese
`command`/`args`/`env`/`cwd`** desde el arnés, y completando `initialize` + `tools/list` + llamadas
reales; los resultados están en `bench/salidas-mcp/res_*.json`.

Tres detalles de configuración que no son obvios y cuestan una tarde cada uno:

1. **`docling-mcp` por defecto NO funciona en local.** `conversion_mode` vale `remote` y
   `fallback_to_local` vale `false`: recién instalado intenta hablar con una API *docling-serve* que
   nadie ha levantado. Sin `DOCLING_MCP_CONVERSION_MODE=local` el servidor arranca perfectamente y
   **falla en la primera conversión**. Un servidor MCP cuyo modo por defecto exige infraestructura
   externa es un servidor que la mayoría de la gente probará una vez y desinstalará.
2. **`docling-mcp` transporta por `streamable-http` por defecto**; para un cliente MCP local hay que
   pedir `--transport stdio` explícitamente.
3. **El argumento posicional `conversion`** limita los grupos de herramientas cargados. Sin él se cargan
   `conversion`, `generation` y `manipulation`: 19 herramientas. El coste de esa decisión está medido
   en §3.

`markitdown-mcp`, en cambio, no necesita nada: stdio es su modo por defecto y no hay configuración que
acertar. Su ergonomía de instalación es claramente superior; el problema aparece después.

---

## 2. El coste en contexto — la pregunta central

Mismo documento, mismo disco, misma máquina. La columna que importa es **tokens al modelo**.

### 2.1 Documento pequeño — `corpus/pdf/tipico_texto.pdf` (1 página, 137 caracteres)

| Llamada | Herramienta | ms | **Tokens al modelo** |
|---|---|---|---|
| markitdown | `convert_to_markdown(file:///…)` | 117 | **56** (el documento entero) |
| docling | `convert_document_into_docling_document(path)` | 21 446 | **32** (`{from_cache, document_key}`) |
| docling | `export_docling_document_to_markdown(key)` | 46 | **80** (el documento, si se pide) |

Con un documento minúsculo el patrón de asa **no gana**: 32 tokens de asa frente a 56 de contenido, y si
el agente acaba pidiendo el contenido paga 32 + 80 = 112. Esto es honesto y hay que decirlo: **el asa
tiene un coste fijo que no se amortiza en documentos triviales.**

### 2.2 Documento grande — `bench/salidas-mcp/grande_60p.pdf`

Generado con Ghostscript concatenando 60 veces una página densa de texto
(`gswin64c -sDEVICE=pdfwrite`): **60 páginas, 409 620 caracteres de capa de texto, 58 KB**.

| Llamada | Herramienta | ms | **Tokens al modelo** |
|---|---|---|---|
| markitdown, 1.ª vez | `convert_to_markdown` | 18 698 | **85 259** |
| markitdown, 2.ª vez | `convert_to_markdown` | 18 184 | **85 259** (no hay caché: se reconvierte y se re-inyecta) |
| docling, 1.ª vez | `convert_document_into_docling_document` | 23 301 | **36** |
| docling, 2.ª vez | idéntico | 370 | **36** (`from_cache: true`) |
| docling, opt-in | `export_docling_document_to_markdown(key)` | 56 | **85 473** |
| docling, opt-in acotado | `export_…(key, max_size=4000)` | 35 | **871** |
| docling, estructura | `get_overview_of_document_anchors(key)` | 5 | **2 347** |
| docling, búsqueda | `search_for_text_in_document_anchors(key, "contexto")` | 7 | **556** |
| docling, un ítem | `get_text_of_document_item_at_anchor(key, "#/texts/2")` | 5 | **20** |

> ### La cifra
> **85 259 tokens frente a 36 tokens por la misma conversión del mismo PDF: un factor de 2 368×.**
> Con markitdown, convertir 60 páginas consume el **42,6 % de una ventana de contexto de 200 K**.
> A 1 421 tokens por página, un PDF de 200 páginas son **≈ 284 000 tokens: no cabe en ninguna ventana
> de 200 K**, y la herramienta lo intentará igualmente.

Y lo decisivo no es solo el tamaño, es **quién decide**. Con markitdown el agente no puede *no* pagar:
el contenido llega antes de que sepa si lo necesita. Con el asa, los 85 473 tokens del volcado completo
siguen disponibles — pero como **opción explícita**, y con tres alternativas más baratas al lado
(2 347 / 871 / 556 / 20 tokens) para las preguntas que casi siempre son las reales.

### 2.3 Coste de una tarea completa, con el catálogo incluido

Tarea: *«convierte este PDF de 60 páginas y dime dónde se menciona "contexto"»*.

| Camino | Catálogo | Conversión | Consulta | **Total** |
|---|---|---|---|---|
| markitdown | 79 | 85 259 | 0 (ya está todo dentro) | **85 338** |
| docling, grupos por defecto (19 tools) | 5 280 | 36 | 2 347 + 556 + 20 | **8 239** |
| docling, solo `conversion` + `manipulation` | ~2 300 | 36 | 2 923 | **~5 259** |

Incluso pagando 5 280 tokens de catálogo inflado, el patrón de asa sale **10× más barato en la tarea
completa**, y 2 368× más barato en la llamada de conversión.

### 2.4 Trampa medida: contenido duplicado (`content` + `structuredContent`)

`docling-mcp` declara `outputSchema`, así que devuelve la misma carga **dos veces**: como texto JSON en
`content` y como objeto en `structured_content`.

| Llamada | `content` | `structured_content` |
|---|---|---|
| `export_docling_document_to_markdown` (60 pág.) | 85 473 tok | 85 469 tok |
| `convert_document_into_docling_document` | 32 tok | 28 tok |

Con asas de 32 tokens da igual. **Con un volcado de 85 K tokens, un cliente que reenvíe ambos campos
cuesta 170 942 tokens por una sola llamada.** Es un multiplicador ×2 silencioso que solo aparece cuando
la herramienta devuelve contenido — otra razón para que la respuesta por defecto sea un asa.

### 2.5 Caché

`docling-mcp` calcula la clave como SHA-256 de **(digest del contenido del fichero + extensión + opciones
de conversión + versiones de `docling`/`docling-mcp`)**, truncado a 32 hex (`docling_cache.py`). Medido:
la misma conversión pedida por ruta absoluta con `\`, por ruta absoluta con `/` y por ruta **relativa**
devolvió las tres veces `625d787afbe5be78327a19eb04aa375d` con `from_cache: true`. **La caché es por
contenido, no por ruta** — exactamente la regla 3 del análisis, y está bien hecha.

Su límite: `local_document_cache` es un `dict` en memoria del proceso. **El asa muere cuando muere el
servidor.** No hay persistencia en disco (el `_cache/` en disco solo lo usa `save_docling_document`).

`markitdown-mcp` no tiene caché de ningún tipo: 18,7 s y 85 259 tokens la primera vez, 18,2 s y 85 259
tokens la segunda.

---

## 3. Inventario de herramientas

### 3.1 `markitdown-mcp`: 1 herramienta, 79 tokens de catálogo, **cero anotaciones**

```
name:        convert_to_markdown
description: "Convert a resource described by an http:, https:, file: or data: URI to markdown"
inputSchema: { uri: string }   (required)
annotations: {}      <-- vacío
outputSchema: null
prompts: 0   resources: 0
```

Una sola herramienta es barata (79 tokens) e imposible de elegir mal, pero **no dice nada de sí misma**:
sin `readOnlyHint`, sin `destructiveHint`, sin `openWorldHint`. El cliente no puede saber que esta
herramienta **abre conexiones de red arbitrarias** (acepta `http:`/`https:`, ver §6) ni que **lee
cualquier fichero del disco**. Un cliente que auto-aprueba herramientas marcadas como de solo lectura no
tiene forma de clasificarla.

Insuficiente también por lo que no ofrece: no hay forma de pedir un rango de páginas, un recorte, un
resumen ni metadatos. La única operación disponible es «tráelo todo».

### 3.2 `docling-mcp`: 19 herramientas por defecto, **5 280 tokens de catálogo**, bien anotadas

| Herramienta | `readOnlyHint` | `destructiveHint` | tokens |
|---|---|---|---|
| `is_document_in_local_cache` | ✅ true | false | 171 |
| `convert_document_into_docling_document` | false | false | 315 |
| `convert_directory_files_into_docling_document` | false | false | 392 |
| `create_new_docling_document` | false | false | 224 |
| `export_docling_document_to_markdown` | ✅ true | false | 270 |
| `save_docling_document` | false | false | 234 |
| `page_thumbnail` | ✅ true | false | 211 |
| `add_title_to_docling_document` | false | false | 248 |
| `add_section_heading_to_docling_document` | false | false | 321 |
| `add_paragraph_to_docling_document` | false | false | 237 |
| `open_list_in_docling_document` | false | false | 223 |
| `close_list_in_docling_document` | false | false | 212 |
| `add_list_items_to_list_in_docling_document` | false | false | 391 |
| `add_table_in_html_format_to_docling_document` | false | false | 485 |
| `get_overview_of_document_anchors` | ✅ true | false | 216 |
| `search_for_text_in_document_anchors` | ✅ true | false | 290 |
| `get_text_of_document_item_at_anchor` | ✅ true | false | 251 |
| `update_text_of_document_item_at_anchor` | false | **true** | 307 |
| `delete_document_items_at_anchors` | false | **true** | 280 |

**6 de 19 son de solo lectura; 2 están marcadas como destructivas.** Las anotaciones existen y son
correctas: esto es lo que hay que copiar. Además expone **7 prompts** (`generate_docling_document_from_pdf`,
`convert_and_summarize`, `convert_directory_and_list`, `author_structured_document`, `convert_and_rewrite`,
`review_and_edit_document`, `find_and_replace_in_document`) y 0 recursos.

**¿Satura la selección del modelo?** Sí, y se puede cuantificar:

| Configuración | Herramientas | Tokens de catálogo | Arranque |
|---|---|---|---|
| Por defecto (`conversion`+`generation`+`manipulation`) | 19 | **5 280** | 6,0 s |
| `--transport stdio conversion` | 3 | **880** | 1,8 s |

5 280 tokens es el **suelo fijo de cada conversación**, se use el servidor o no, y para una tarea de
*conversión* 13 de esas 19 herramientas son de **autoría de documentos** (`add_title`, `open_list`,
`close_list`, `add_list_items`, `add_table_in_html_format`…). El problema no es solo el gasto: es que
`add_paragraph_to_docling_document`, `add_section_heading_to_docling_document` y
`update_text_of_document_item_at_anchor` compiten entre sí en el espacio de decisión del modelo, y once
de ellas comparten el mismo sufijo `…_docling_document`. Nombres largos, casi idénticos y con un dominio
distinto al de la tarea: eso es exactamente lo que degrada la selección de herramienta.

**Reducir a `conversion` recorta el catálogo un 83 % (5 280 → 880) y el arranque un 70 % (6,0 → 1,8 s).**
Por eso el `.mcp.json` de §1.3 lo hace.

---

## 4. Comportamiento ante errores: qué mensaje ve exactamente el modelo

La auditoría (`analysis/00-seguridad.md`) avisaba de que el `stderr` crudo de un motor acaba en el
contexto del agente y puede dirigir su siguiente acción. Aquí está medido, verbatim.

### 4.1 `markitdown-mcp`

| Caso | `isError` | tok | Mensaje literal recibido por el modelo |
|---|---|---|---|
| Fichero inexistente | true | 42 | `Error executing tool convert_to_markdown: [Errno 2] No such file or directory: 'D:\Work\research\FileX\corpus\pdf\no_existe_jamas.pdf'` |
| Formato no soportado (`.mkv`) | true | 31 | `Error executing tool convert_to_markdown: Could not convert stream to Markdown. No converter attempted a conversion, suggesting that the filetype is simply not supported.` |
| Esquema de URI inválido | true | 26 | `Error executing tool convert_to_markdown: Unsupported URI scheme: D. Supported schemes are: file:, data:, http:, https:` |
| **PDF escaneado sin capa de texto** | **false** | **0** | *(cadena vacía)* |
| URL HTTP inalcanzable | true | 92 | `…HTTPConnectionPool(host='127.0.0.1', port=9): Max retries exceeded… [WinError 10061] No se puede establecer una conexi<0xF3>n ya que el equipo de destino deneg<0xF3> expresamente…` |

**Lo bueno:** no hay trazas de pila. Son mensajes de una línea, y el de esquema de URI es *modélico*:
dice qué falló **y enumera las alternativas válidas**. Un agente se corrige con eso en un intento.

**Lo grave, y es el peor comportamiento medido en todo el carril:**

> `patologico_escaneado.pdf` (8,5 MB, escaneado, sin capa de texto) devuelve **cadena vacía con
> `isError: false`**. Lo mismo con `escaneado_d1.pdf`. **El modelo recibe un éxito y un documento
> vacío, y concluye que el PDF no tiene contenido.** No es un error que el agente pueda reintentar:
> es una respuesta falsa. Cualquier agente encadenando pasos («resume este PDF») producirá una
> alucinación o un «el documento está vacío» rotundamente falso.

Un fallo silencioso es peor que un fallo ruidoso, porque el ruidoso al menos se puede enrutar a OCR.

**Lo feo:** los mensajes filtran **rutas absolutas completas del sistema de ficheros** y el mensaje de
error del SO **traducido al idioma del sistema, con la codificación rota** (`conexi<0xF3>n`). Un agente
que intente razonar sobre ese texto está leyendo mojibake en un idioma que puede no ser el suyo.

### 4.2 `docling-mcp`

| Caso | `isError` | tok | Mensaje literal recibido por el modelo |
|---|---|---|---|
| Fichero inexistente | true | 61 | `Error executing tool convert_document_into_docling_document: Conversion failed for: no_existe_jamas.pdf with status: failure. Errors: [Errno 2] No such file or directory: 'D:\Work\research\FileX\corpus\pdf\no_existe_jamas.pdf'` |
| **Formato no soportado (`.mkv`)** | true | 37 | ``Error executing tool …: whisper is not installed. Please install it via `pip install openai-whisper` or do `uv sync --extra asr`.`` |
| **Clave de caché inválida** | true | 69 | `Error executing tool export_docling_document_to_markdown: document-key: clave-que-no-existe is not found. Existing document-keys are: 625d787afbe5be78327a19eb04aa375d, 774796ed6faa5995b5b3f4a1ed88cf1a` |
| Ancla fuera de rango | true | 16 | `Error executing tool get_text_of_document_item_at_anchor: list index out of range` |
| URI `file://` | true | 42 | `…Unsupported URL scheme: 'file'. Only http:// and https:// are supported.` |
| Extensión no permitida (`win.ini`) | true | 30 | `…Conversion failed for: win.ini with status: skipped. Errors: File format not allowed: win.ini` |
| URL de red bloqueada | true | 40 | `…Errors: URL is not allowed: http://127.0.0.1:9/nada` |

Tres problemas concretos, cada uno con su lección:

1. **El mensaje del `.mkv` es una instrucción accionable y equivocada.** El agente no lee «este formato
   no se soporta»; lee ``pip install openai-whisper``. Es literalmente el escenario que advertía la
   auditoría: **el `stderr` de un motor interno se convierte en la siguiente acción del agente.** Un
   agente con permiso de shell instalará un paquete de 2 GB para convertir un vídeo que el servidor
   nunca iba a convertir. FileX debe **traducir** los errores del motor, nunca reenviarlos.

2. **Una clave de caché inválida devuelve la lista de TODAS las claves vivas del proceso.** El servidor
   es un proceso persistente y compartido: esa lista contiene asas de documentos convertidos en otras
   tareas — y con esas claves, `export_docling_document_to_markdown` los vuelca enteros. **Un mensaje de
   error es un canal de enumeración entre contextos.** El impulso de ser útil («aquí tienes las claves
   válidas») se convierte en fuga de datos en cuanto el proceso deja de ser de un solo usuario y una
   sola tarea.

3. **`list index out of range`** es una excepción de Python en crudo, 16 tokens, sin nombre de
   herramienta útil, sin el rango válido, sin nada que permita corregirse. El agente solo puede
   adivinar.

### 4.3 Lo que sí llega y lo que no: `stderr`

En stdio, el `stderr` del servidor va al log del cliente, no al contexto del modelo. Pero su volumen
indica lo cerca que se está del desastre si algún envoltorio lo captura:

| Servidor | `stderr` de una sesión |
|---|---|
| `markitdown-mcp` | **1,3 KB** (un `warning` de pydantic + una línea por petición) |
| `docling-mcp` | **105 KB / 302 líneas** para 22 llamadas |

`docling-mcp` emite a nivel INFO, **en cada creación de convertidor**, un volcado de una sola línea de
~6 KB con el `repr()` completo de `PdfPipelineOptions` (todos los `model_spec`, `repo_id`, `torch_dtype`,
rutas de modelos…). Son ~1 700 tokens de basura por conversión si alguna vez ese canal toca el contexto.

---

## 5. Arranque en frío frente a llamadas en caliente

Medido con procesos nuevos: 3 arranques de `markitdown-mcp`, 3 de `docling-mcp` (handshake) y 2 de
`docling-mcp` convirtiendo (con el lock de GPU adquirido y liberado).

### 5.1 Levantar el servidor (spawn → `initialize` completo)

| Servidor | n=3 | Mediana | `spawn` | `handshake` |
|---|---|---|---|---|
| `markitdown-mcp` | 2 109 / 2 198 / 2 467 ms | **2 198 ms** | 9–17 ms | 2 094–2 450 ms |
| `docling-mcp` (19 tools) | 6 050 / 6 049 / 5 703 ms | **6 049 ms** | 13–15 ms | 5 688–6 036 ms |
| `docling-mcp` (3 tools) | — | **1 762 ms** | — | — |

`tools/list` es gratis en ambos (2,3 ms y 6,4 ms).

### 5.2 Primera llamada frente a las siguientes, dentro del mismo proceso

| Servidor | 1.ª llamada | 2.ª | 3.ª | Penalización de la 1.ª |
|---|---|---|---|---|
| `markitdown-mcp` (PDF de 1 pág.) | 91 / 74 / 87 ms | 55 / 54 / 64 ms | 54 / 54 / 58 ms | **≈ +25 ms** |
| `docling-mcp` (3 PDFs distintos) | 7 213 / 6 998 ms | 2 300 / 1 981 ms | 2 099 / 1 968 ms | **≈ +5 100 ms** |

Un dato adicional: la **primerísima** conversión de la sesión, con la caché de página del SO fría, costó
**21 446 ms** (`res_docling.json`). El rango real del arranque en frío de docling va de 7 s (SO caliente)
a 21 s (SO frío).

### 5.3 Qué confirma y qué refuta

**Confirma la conclusión.** Tiempo hasta la primera respuesta útil desde cero:

- `markitdown-mcp`: 2,20 s + 0,09 s = **≈ 2,3 s**, y luego **55 ms** por llamada.
- `docling-mcp`: 6,05 s + 7,21 s = **≈ 13,3 s** (hasta 28 s con el SO frío), y luego **2,0 s** por llamada.

En un servidor MCP persistente eso se paga **una vez por sesión** y se amortiza a cero: a la décima
conversión el arranque en frío de docling representa el 40 % del total; a la centésima, el 6 %. **Para
un servidor persistente el arranque en frío deja de importar, y la conclusión previa se sostiene.**

**Refuta un supuesto — y este es un hallazgo que el análisis de código no vio.** El estado estacionario
de docling **no es tan barato como debería**: 2,0 s por conversión de un PDF de una página. Contando
en `stderr`, 3 conversiones producen **3 × `Creating DocumentConverter` y 3 × `Initializing pipeline`**.
La causa está en `conversion.py`:

```python
converter = get_converter()          # devuelve LocalDocumentConverter() NUEVO en cada llamada
result = converter.convert_document(source)
cleanup_memory()                     # -> gc.collect(), nada más
```

`LocalDocumentConverter` cachea su `DocumentConverter` en `self._converter`, pero **la instancia se tira
en cada llamada**, así que la caché no sirve para nada: se reconstruye el pipeline en cada conversión.
Esos ~2 s no son coste de conversión: son coste de reconstruir el motor.

Y `cleanup_memory()` **no libera los modelos de la GPU**: es un `gc.collect()`. Ni descarga los modelos
(que es lo que la lectura del código sugería) ni mantiene el motor caliente (que es lo que un servidor
persistente debería hacer). Consigue lo peor de las dos opciones: paga la reconstrucción sin recuperar
la VRAM de forma determinista.

**Lección para FileX:** «servidor persistente» solo elimina el arranque en frío si el **motor** vive en
el proceso, no solo el servidor. Un singleton a nivel de módulo, con descarga explícita por inactividad.

---

## 6. Manejo de rutas: convenciones **opuestas**, y ningún confinamiento

| Entrada | `markitdown-mcp` | `docling-mcp` |
|---|---|---|
| `D:\Work\…\tipico_texto.pdf` (absoluta Windows) | ❌ `Unsupported URI scheme: D` | ✅ convierte |
| `D:/Work/…/tipico_texto.pdf` (absoluta, `/`) | ❌ `Unsupported URI scheme: D` | ✅ convierte |
| `corpus/pdf/tipico_texto.pdf` (relativa al `cwd`) | ❌ `Unsupported URI scheme: corpus/pdf/…` | ✅ convierte (misma clave de caché) |
| `file:///D:/Work/…/tipico_texto.pdf` | ✅ convierte | ❌ `Unsupported URL scheme: 'file'. Only http:// and https:// are supported.` |
| `file:corpus/pdf/tipico_texto.pdf` (relativa con esquema) | ✅ convierte | — |
| `http://127.0.0.1:9/nada` | ⚠️ **intenta la conexión** (2 064 ms) | ✅ **bloqueada**: `URL is not allowed` |

> **Son exactamente incompatibles.** Lo único que `markitdown-mcp` acepta (`file://`) es lo único que
> `docling-mcp` rechaza, y todo lo que `docling-mcp` acepta (rutas del sistema) es lo único que
> `markitdown-mcp` rechaza. Un agente que aprende a hablar con uno **falla con el otro en la primera
> llamada**. Un formato de ruta que el agente no puede adivinar es un fallo garantizado por servidor.

### 6.1 Travesía de directorios: `..\..\` funciona, en los dos

| Prueba | `markitdown-mcp` | `docling-mcp` |
|---|---|---|
| `file:///C:/Users/krato/AppData/Local/../../../../Windows/win.ini` | ✅ **devuelve el contenido de `C:\Windows\win.ini`** | ❌ rechazado — pero **por la extensión**: `File format not allowed: win.ini` |
| `file:///C:/Windows/win.ini` (absoluta, fuera del proyecto) | ✅ **devuelve el contenido** | — |
| `D:\Work\research\FileX\analysis\00-mcp-patrones.md` (fichero arbitrario del disco) | — | ✅ **convierte sin objeción** |

**Ninguno de los dos servidores tiene noción de raíz permitida.** No hay allowlist de directorios, no
hay `realpath` contra una base, no hay concepto de proyecto. La travesía ni siquiera hace falta: la ruta
absoluta funciona directamente.

La aparente defensa de docling **no es una defensa de rutas**: es un filtro de *formatos*. Rechaza
`win.ini` porque `.ini` no es un formato de entrada conocido — y convierte alegremente cualquier `.md`,
`.pdf` o `.docx` de cualquier punto del disco. Cambia la extensión del objetivo y la protección
desaparece.

Donde docling **sí** protege de verdad es en red: bloquea `http://127.0.0.1:9/…` con `URL is not
allowed`. `markitdown-mcp` abre la conexión (2 064 ms hasta el rechazo de TCP) y devuelve el error del
socket al modelo: **una superficie de SSRF completa, gobernada por un parámetro que escribe el agente,
en una herramienta sin `openWorldHint`.**

---

## 7. Calidad de la salida (contexto, no el objeto de estudio)

Para el mismo PDF de 60 páginas: markitdown 413 759 caracteres, docling 410 293. Diferencias visibles en
el documento pequeño: markitdown conserva el maquetado tabular con espacios y emite `(cid:145)` para un
glifo no mapeado; docling aplana la tabla a una línea y escapa `&` como `&amp;`. Ninguna de las dos es
limpia. **No cambia nada de este informe**: el argumento del asa vale igual sea cual sea la calidad del
markdown, y de hecho vale *más* si la salida necesita revisión, porque el asa permite mirarla por trozos.

---

## 8. Fallos y costes de integración, reportados como tales

1. **Incompatibilidad `mcp~=1.8.0` vs `mcp>=2.0.0`**: imposible instalar ambos servidores en un venv.
   Coste: un venv extra (`.venv-mcp-md`, ~120 MB).
2. **`docling-mcp` no arranca en local sin configurar**: `conversion_mode=remote` + `fallback_to_local=false`
   por defecto. Dos variables de entorno para que funcione en una máquina sola.
3. **Renombrado de la API de `mcp` 1.x → 2.x** (`serverInfo`→`server_info`, `isError`→`is_error`,
   `structuredContent`→`structured_content`): el arnés se rompió en el primer intento contra docling y
   hubo que hacerlo agnóstico de versión. Es el mismo coste que pagará cualquier cliente que soporte
   los dos.
4. **`docling-mcp` lee `.env` del `cwd`** (`SettingsConfigDict(env_file=".env")`): un `.env` en el
   directorio de trabajo del cliente cambia silenciosamente el comportamiento del servidor.
5. Dos errores propios del arnés (rutas con `\r`/`\b` mal escapadas en un heredoc, y nombres de campo
   camelCase) se detectaron y corrigieron; las cifras publicadas provienen de ejecuciones limpias
   posteriores. Se conservan las specs y los `res_*.json` para reproducir.

---

## Las reglas de diseño MCP para FileX, con su evidencia

**1. La respuesta por defecto de `convert` es un asa, nunca el contenido.**
Devolver `{ruta_salida, formato, bytes, páginas, duración_ms, motor, camino}`.
*Evidencia:* mismo PDF de 60 páginas — **85 259 tokens** (markitdown, contenido) frente a **36 tokens**
(docling, asa). **Factor 2 368×.** El volcado consume el 42,6 % de una ventana de 200 K; a 1 421
tokens/página, 200 páginas (≈ 284 K tokens) no caben en ninguna ventana de 200 K.

**2. El asa debe ser una ruta en disco, no una clave en memoria.**
*Evidencia:* `local_document_cache` de docling-mcp es un `dict` del proceso; el asa muere con el
servidor y no la puede leer ninguna otra herramienta. Una ruta la puede abrir el `Read` del agente, otro
proceso, o el usuario. Coste idéntico: 36 tokens.

**3. Junto a `convert`, herramientas de lectura acotada; el volcado completo, siempre opt-in y con tope.**
*Evidencia medida sobre el mismo documento de 85 473 tokens:* estructura **2 347**, búsqueda dirigida
**556**, un ítem concreto **20**, recorte con `max_size=4000` **871**. La pregunta real casi nunca vale
85 K tokens. `convert` debe aceptar `max_bytes`/`max_chars` con un tope por defecto no infinito.

**4. Nunca devolver la misma carga en `content` y en `structuredContent`.**
*Evidencia:* `export_docling_document_to_markdown` devuelve 85 473 tok en `content` **y** 85 469 tok en
`structured_content`: **170 942 tokens** si el cliente reenvía ambos. Con asas de 36 tokens el riesgo
desaparece; si alguna herramienta devuelve contenido, un solo canal.

**5. Cuatro o cinco herramientas, con nombres cortos y dominios distintos.**
*Evidencia:* catálogo de docling **5 280 tokens / 19 herramientas** por defecto, con once nombres que
acaban en `…_docling_document`; limitarlo a `conversion` baja a **880 tokens / 3 herramientas** (−83 %)
y el arranque de 6,0 s a 1,8 s. markitdown, en el otro extremo, con **79 tokens / 1 herramienta**, no
ofrece ni recortar ni inspeccionar. Objetivo FileX: `convert`, `inspect`, `list_targets`, `batch` —
**≈ 1 000 tokens de catálogo**, la mitad de solo lectura.

**6. Anotar cada herramienta con `readOnlyHint`/`destructiveHint`/`openWorldHint`.**
*Evidencia:* `markitdown-mcp` devuelve `annotations: {}` para una herramienta que **lee cualquier
fichero del disco y abre conexiones HTTP arbitrarias**. `docling-mcp` marca 6 de 19 como solo lectura y
2 como destructivas, y eso es lo correcto. `openWorldHint` es obligatorio en toda herramienta que pueda
tocar la red.

**7. Caché idempotente por hash de contenido + parámetros + versión del motor.**
*Evidencia:* la clave de docling (SHA-256 de contenido + extensión + opciones + versiones) devolvió la
misma entrada por tres formas distintas de escribir la ruta, y bajó la reconversión de **23 301 ms a
370 ms**. markitdown, sin caché, repitió los mismos 18,2 s **y los mismos 85 259 tokens**. La versión
del motor debe entrar en la clave, o una actualización servirá resultados obsoletos.

**8. Traducir los errores del motor; jamás reenviar su `stderr`.**
*Evidencia:* pedir la conversión de un `.mkv` a docling-mcp devuelve al modelo
``pip install openai-whisper`` — el motor ordenando una instalación de 2 GB para un formato que el
servidor no iba a convertir. FileX debe emitir «formato de entrada no soportado por este destino;
destinos válidos: …», al estilo del mejor mensaje medido en todo el carril (markitdown: *«Unsupported
URI scheme: D. Supported schemes are: file:, data:, http:, https:»*, **26 tokens, corregible en un
intento**). Un error debe caber en ~40 tokens, nombrar la causa y enumerar las alternativas válidas.

**9. Un fallo es un fallo: prohibido el éxito vacío.**
*Evidencia:* `markitdown-mcp` con un PDF escaneado devuelve **cadena vacía con `isError: false`** (0
tokens). El agente concluye que el documento está vacío. FileX debe devolver `isError: true` con
«PDF sin capa de texto; reintenta con `ocr=true`» — que además es la ruta que el carril de OCR ya tiene
medida.

**10. Los mensajes de error no enumeran el estado del servidor.**
*Evidencia:* una clave de caché inválida en docling-mcp devuelve **la lista completa de claves vivas**
(`Existing document-keys are: 625d78…, 774796…`), y con esas claves se vuelca cualquier documento
convertido en otra tarea del mismo proceso. Un asa inválida en FileX responde «asa desconocida o
caducada», y nada más.

**11. Un único formato de ruta, documentado en la propia descripción de la herramienta, y aceptar los demás.**
*Evidencia:* lo único que markitdown acepta (`file://`) es lo único que docling rechaza, y viceversa;
las rutas absolutas de Windows fallan en markitdown con `Unsupported URI scheme: D`. FileX debe aceptar
ruta absoluta, ruta relativa a la raíz del proyecto y `file://`, normalizarlas todas, y decirlo en la
descripción del parámetro.

**12. Confinar el sistema de ficheros a raíces declaradas, con `realpath` — y no confundir un filtro de
formatos con una defensa.**
*Evidencia:* `markitdown-mcp` devolvió el contenido de `C:\Windows\win.ini` **por travesía `../../../../`
y por ruta absoluta**; `docling-mcp` solo lo rechazó porque `.ini` no es un formato de entrada, y
convirtió sin objeción un `.md` arbitrario del disco. Ninguno tiene noción de raíz. FileX debe resolver
la ruta real y rechazar todo lo que quede fuera de las raíces declaradas, **antes** de mirar la
extensión.

**13. Salidas a red desactivadas por defecto, con allowlist explícita.**
*Evidencia:* `markitdown-mcp` intentó la conexión a `http://127.0.0.1:9` (2 064 ms) y devolvió el error
del socket — SSRF completo dirigido por un parámetro del agente. docling la bloqueó (`URL is not
allowed`). Copiar a docling; y si se habilita la red, marcarla con `openWorldHint`.

**14. Motor caliente en un singleton de proceso, con descarga por inactividad.**
*Evidencia:* en un servidor persistente el arranque en frío se amortiza (docling: 13,3 s la primera
respuesta, 2,0 s las siguientes; markitdown: 2,3 s y luego 55 ms) — **la conclusión previa se confirma**.
Pero docling-mcp instancia `LocalDocumentConverter()` en **cada** llamada
(3 conversiones → 3 × `Creating DocumentConverter` en `stderr`), pagando ~2 s de reconstrucción del
pipeline por conversión, mientras su `cleanup_memory()` es un `gc.collect()` que no libera la VRAM.
Lo peor de ambos mundos. FileX: el motor vive a nivel de módulo, se reutiliza, y se descarga por
temporizador explícito.

**15. Silencio en `stderr`.**
*Evidencia:* `docling-mcp` escribe **105 KB / 302 líneas** en una sesión de 22 llamadas, incluida una
línea de ~6 KB con el `repr()` completo de `PdfPipelineOptions` por cada convertidor creado; markitdown
escribe **1,3 KB**. En stdio ese canal no llega al contexto, pero cualquier envoltorio que lo capture
inyecta ~1 700 tokens de ruido por conversión. Nivel `WARNING` por defecto, `INFO` bajo bandera.

**16. Un solo servidor, no uno por motor.**
*Evidencia:* `mcp~=1.8.0` y `mcp>=2.0.0` son incompatibles: los dos servidores de referencia **no pueden
compartir entorno de Python**, y negocian versiones distintas del protocolo (2024-11-05 frente a
2025-11-25). Multiplicar servidores multiplica catálogos (79 + 5 280 tokens de suelo fijo), convenciones
de ruta y modos de fallo. La forma correcta es la de `kordoc`: un binario, dos superficies.

---

### Reproducir

```bash
# markitdown (venv A)
.venv-mcp-md/Scripts/python.exe bench/salidas-mcp/mcp_probe.py \
    bench/salidas-mcp/spec_markitdown.json bench/salidas-mcp/res_markitdown.json

# docling (venv .venv-ai) — requiere el lock de GPU
source bench/lib/harness.sh && gpu_acquire "mcp"
.venv-ai/Scripts/python.exe bench/salidas-mcp/mcp_probe.py \
    bench/salidas-mcp/spec_docling.json bench/salidas-mcp/res_docling.json
gpu_release

# PDF grande (60 páginas) a partir de una página densa
gswin64c -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=grande_60p.pdf \
         _pagina_densa.pdf _pagina_densa.pdf ... (x60)
```

Ficheros de evidencia en `bench/salidas-mcp/`: `spec_*.json` (entradas), `res_*.json` (medidas crudas,
incluida la respuesta literal de cada llamada), `stderr_*.log`, `md_grande.md` / `dl_grande.md`
(las dos salidas de 60 páginas), `grande_60p.pdf`.
