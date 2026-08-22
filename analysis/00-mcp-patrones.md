# Patrones MCP: qué hacen bien y mal las referencias existentes

Analizado sobre `markitdown-mcp` (Microsoft, oficial), `docling-mcp` (IBM, 709 ⭐) y `kordoc` (1.7k ⭐, CLI+MCP en un binario).

> **Estado: AL DÍA (21/08/2026, 03:30).** Aplicadas las correcciones **4 y 5 de `RESULTADOS-MCP.md` §12** —la regla 1 reescrita sobre el caso binario medido y `cleanup_memory()` degradado de modelo a antipatrón— **y las de la tabla de 12 de `bench/mcp-cabos-sueltos.md` §6** que tocan a este documento (nº 1, 2, 3, 5, 6, 7, 9, 10 y 11), más lo medido en `bench/saturacion-herramientas.md`. Cada corrección va marcada en su sitio con **lo que se creía** y **lo que se midió**.
>
> **Las dos que más cambian el diseño:**
>
> 1. **Las anotaciones `readOnlyHint`/`destructiveHint` NO llegan al modelo** en Claude Code 2.1.238: solo cruzan `description` e `inputSchema`. La advertencia va en la descripción; **la defensa, en el núcleo** (regla 2).
> 2. **`-y` es necesario y NO suficiente** contra el deadlock de ffmpeg: con `stdin` heredado cuelga **2 de 5**; con `stdin=DEVNULL`, **0 de 5**. Resultado **causal medido A/B** dentro de una sesión MCP real (regla 6).

## El error de diseño: devolver el contenido

`markitdown-mcp` es el MCP de conversión más difundido y expone **una sola herramienta**:

```python
@mcp.tool()
async def convert_to_markdown(uri: str) -> str:
    """Convert a resource described by an http:, https:, file: or data: URI to markdown"""
    return MarkItDown(...).convert_uri(uri).markdown
```

Devuelve **el documento entero como string**, es decir, directamente al contexto del modelo. Un PDF de 200 páginas son decenas de miles de tokens inyectados de golpe.

> **Corrección MEDIDA (20/08/2026).** Este documento afirmaba aquí: *«Y para salidas binarias — un MP4, un PNG — el patrón sencillamente no existe.»* **Es falso.** `image-worker-mcp` devuelve la imagen entera con un booleano (`outputImage: true`), **como base64 dentro de un string JSON en un `TextContent`** — invisible para una regla escrita sobre tipos de contenido del protocolo. La misma conversión pasa de **71 a 6.218 tokens (×87)**. Se creyó lo contrario porque se leyó el ecosistema buscando `ImageContent`/`BlobResourceContents`, y el patrón no viaja por ahí. Evidencia: `bench/mcp-refs-multimedia.md` §9.3 y `RESULTADOS-MCP.md` §3.

## El patrón correcto: devolver un asa (*handle*)

`docling-mcp` lo resuelve bien: convierte, **guarda en una caché local** y devuelve una **clave**, no el contenido:

```python
@mcp.tool(
    title="Convert document into Docling document",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
def convert_document_into_docling_document(source: str) -> ConversionOutput:
    converter = get_converter()
    result = converter.convert_document(source)
    cleanup_memory()      # NO libera VRAM: es un gc.collect() — ver regla 4
    return result         # -> {document_key, ya_estaba_en_cache}
```

Además: herramienta aparte `is_document_in_local_cache()` para evitar reconversiones, y `ToolAnnotations(readOnlyHint/destructiveHint)` para que el cliente MCP sepa qué operaciones son seguras.

## Reglas que FileX debe seguir

1. **Devolver ruta + metadatos, nunca el contenido convertido.** `{ruta_salida, formato, bytes, duración_ms, motor_usado, camino_recorrido}`. Y con tres precisiones que hicieron falta tras medir el caso binario (`bench/mcp-refs-multimedia.md` §9.3):
   - **«Contenido» incluye el binario en cualquier codificación**: `ImageContent`/`AudioContent`, `BlobResourceContents`, y **también base64 embebido en un `TextContent` o en un campo JSON**, que es la forma en que aparece de verdad en el ecosistema.
   - **El criterio operativo es el tamaño de la respuesta, no su tipo.** Toda respuesta debe caber en **≤200 tokens** salvo `inspect`. Si lo supera, es un fallo de diseño, con independencia del tipo de contenido. Un revisor que audite buscando `ImageContent` **no detecta el antipatrón**; los tokens sí lo delatan.
   - **No hay excepción por tamaño para las imágenes.** Se evaluó explícitamente: a **0,93 tokens/byte** el umbral de rentabilidad está en **1-2 KB**, por debajo de un icono. Una miniatura de 10 KB cuesta **132×** su ruta. **La firma de las herramientas de FileX no cambia.**
   - **Precisión MEDIDA (21/08/2026, `bench/mcp-cabos-sueltos.md` §1.3):** los 0,93 tok/B son el coste del **base64 dentro de texto**. Un **`ImageContent` nativo** a través del cliente real cuesta **por píxel, no por byte**: **~2.814 tokens** medidos para `tipico.png` (42.855 B, 1920×1080), frente a los ~39.855 del base64 encubierto y los **32-72 del asa**. La predicción `w×h/750` da 2.765: coincide. **La conclusión no cambia, se refuerza:** el `ImageContent` nativo es ×14 más barato que el antipatrón y aun así **×39 a ×88 más caro que devolver la ruta**. Y el criterio operativo sigue siendo **tokens de respuesta**, porque es lo único que captura las dos vías.
2. **Anotar cada herramienta** con `readOnlyHint`/`destructiveHint`. Convertir crea ficheros; sobrescribir destruye. El cliente debe poder distinguirlo. **De 5 servidores de conversión sondeados solo docling anota**: hacerlo es ventaja diferencial, no alineación con la norma.

   > **Corrección MEDIDA (21/08/2026, `bench/mcp-cabos-sueltos.md` §1.2).** Este documento presentaba anotar como *«una ventaja diferencial real»* sin matiz. **Medido contra Claude Code 2.1.238 —el cliente real más probable— anotar no produce ninguna diferencia observable.** De lo que declara el servidor, al modelo **solo le cruzan `description` e `inputSchema`**. **No cruzan** `annotations.readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint`, ni `annotations.title`, ni el `title` de la herramienta, ni `_meta`, ni `outputSchema`, ni `icons`. **Y tampoco cambian el permiso:** una herramienta marcada `readOnlyHint=true, destructiveHint=false` fue **denegada igual** con el modo de permisos por defecto.
   >
   > La prueba limpia fue una herramienta declarada `destructiveHint=true`: **el modelo supo que era destructiva solo porque el autor lo escribió dentro de la descripción**. En palabras del propio cliente: *«Las anotaciones del protocolo no cruzan hasta el modelo; solo cruza la descripción.»*
   >
   > **La regla se mantiene** —es barata, es correcta según la especificación y otros clientes pueden usarla— **pero NO puede ser el sitio donde vive una advertencia de seguridad. La advertencia va en la `description`; la defensa, en el núcleo** (regla R10 de `RESULTADOS-MCP.md` §10).
   >
   > **Y `structuredContent` tampoco compra nada del lado del modelo:** una herramienta con `structured_output=True` y un `outputSchema` real entregó una línea de texto indistinguible de un `TextContent` con el mismo JSON serializado a mano, **sin el `outputSchema` a la vista**. Confirma por otra vía el dato incómodo de `RESULTADOS-MCP.md` §4.
3. **Caché idempotente por hash del contenido + parámetros.** Si el agente pide dos veces lo mismo, la segunda es gratis. `docling-mcp` lo hace por clave de documento; con hash es más robusto.
4. **Liberar los modelos GPU tras el trabajo**, o el sidecar acapara los 12 GB de la 3060 indefinidamente. **Corrección MEDIDA:** este documento citaba `cleanup_memory()` de docling-mcp como el modelo a seguir. `bench/mcp-ergonomia.md` regla 14 midió que **es solo un `gc.collect()`: no libera VRAM ni mantiene el motor caliente** — lo peor de ambos mundos, porque además reinstancia `LocalDocumentConverter()` en cada llamada (~2 s). **Se copia la intención, no la implementación:** lo que hace falta es el registro LRU acotado por bytes de VRAM con TTL de `PLAN-ORQUESTADOR.md` §4.5, con liberación explícita del modelo.
5. **Poco catálogo, medido en tokens — no «pocas herramientas».** markitdown expone 1 (insuficiente), docling-mcp más de 10. Para FileX: `convert`, `inspect`, `list_targets`, `batch` — cuatro, y la mitad son de solo lectura. **Pero el número no es el presupuesto: el coste por herramienta varía ×11** (79 tokens en `markitdown.convert_to_markdown`, **875** en `image-worker.resize_image`, que declara 25 parámetros descritos). **El presupuesto se fija en tokens de catálogo: ≤1.200 para las cuatro** (`RESULTADOS-MCP.md` §4).

   > **Corrección MEDIDA (21/08/2026, `bench/saturacion-herramientas.md`), y va en contra de lo que decía esta regla.** Este documento afirmaba que docling-mcp con «más de 10» herramientas *«empieza a saturar la selección del modelo»*. **Es una hipótesis, y con 540 ejecuciones no se sostiene:** el catálogo de **27** herramientas acertó **100 %/98 %** (Haiku/Sonnet, acierto permisivo) frente al **85 %/77 %** del de **8**, con **0 %/2 %** de elecciones trampa frente al **15 %/17 %**. **El catálogo grande eligió mejor, no peor** (p < 0,001 en los dos modelos). Quitar la redundancia tampoco mejoró nada: A (27) vs C (14, las mismas menos las 13 subsumidas) da **100 % vs 100 %**.
   >
   > **Lo que sí se paga, y peor de lo que se creía: el catálogo viaja en CADA turno, con un multiplicador de ×2,0–2,6.** Un catálogo de 7.886 tokens costó **≈19.000–23.600 tokens de entrada por petición**; el intercambio típico fueron **2,1 turnos**. **Los ≤1.200 tokens del presupuesto son ≈2.400–3.100 por petición**, y ese es el número que hay que comparar con la ventana.
   >
   > **La regla sobrevive, con su justificación cambiada: se exponen pocas herramientas por COSTE, no porque el modelo se sature.**

6. **`stdin=DEVNULL` en la construcción del proceso. Es LA defensa, no un complemento — MEDIDO A/B (`bench/mcp-cabos-sueltos.md` §4.3).**

   Todo subproceso corre con **`stdin=DEVNULL` primero**, y **después** las banderas no interactivas (`-y`, `-nostdin`), con timeout del lado del servidor y matando el árbol de procesos.

   **`-y` es necesario y NO suficiente.** Dos herramientas MCP idénticas salvo en una línea, ejecutando la misma secuencia **con `-y` en todas partes** y sobre **rutas de salida nuevas**:

   | Herramienta | Diferencia | Colgadas |
   |---|---|---:|
   | `conv_heredado` | `stdin` no se toca → hereda la tubería JSON-RPC | **2/5** |
   | `conv_devnull` | **`stdin=subprocess.DEVNULL`** | **0/5** |

   **Y la variable que lo dispara es estrecha: no es «una tubería», es la tubería que el servidor MCP está leyendo a la vez** — fuera de MCP, con tuberías mudas, 0 de 15 secuencias colgaron. **El hijo y el bucle de lectura del servidor compiten por el mismo descriptor.**

   > Una revisión que se conforme con «¿lleva `-y`?» **da por bueno un código que cuelga la sesión el 40 % de las veces**. Y `-nostdin` es otra bandera más que hay que acordarse de poner en cada punto de invocación. **`stdin=DEVNULL` en el constructor no se puede olvidar, porque no hay puntos de invocación: hay uno.**
   >
   > **Y matar el árbol no siempre alcanza al nieto:** un `ffmpeg.exe` sobrevivió a un `taskkill /F /T` sobre el servidor. Hace falta **inventario explícito** de los procesos lanzados (job object en Windows, grupo de procesos en POSIX).

7. **La cobertura declarada es un requisito de seguridad, no de comodidad — MEDIDO (`bench/saturacion-herramientas.md` §3.5 y §7.2).**

   **Cuando el catálogo no cubre lo que se pide, el modelo no se abstiene: llama a la herramienta más parecida y declara éxito con un dato falso.** Ocurrió en el **15–17 %** de las peticiones con el catálogo de 8. Respuesta literal medida: *«se ha creado con el audio re-codificado en AAC, reduciendo el bitrate desde los 320 kbps originales»* — el dato es **falso**, los 96 kbps pedidos **no se aplicaron**, y **no hubo error**.

   - **`list_targets` es el mecanismo que evita esto**: la única herramienta que puede decir, en tiempo de ejecución y sin inventar, qué conversiones existen. Debe ser la respuesta canónica a «¿puedo hacer X?».
   - **`convert` falla explícitamente** ante una combinación no soportada, nombrando la alternativa. **El silencio es el modo de fallo peligroso, no el error.**
   - **La descripción declara los límites, no solo las capacidades.** Los tres servidores de referencia describen lo que hacen; **ninguno describe lo que no hace**, y ahí es donde se producen los fallos silenciosos.
   - **Cada parámetro lleva su `description` en el esquema.** **MEDIDO: 0 de 193 parámetros** de los tres catálogos de referencia la lleva — FastMCP deriva el esquema de las anotaciones de tipo y deja la semántica en el docstring. Es lo que produce casos como `add_b_roll`: un `array of object` sin una sola clave y una descripción que remite a «mensajes anteriores».
   - **Prueba de regresión:** un conjunto de peticiones **fuera** de la cobertura de FileX **cuyo criterio de acierto es la abstención**. Es la única que detecta este modo de fallo.

## El antipatrón de contenido encubierto está PROTEGIDO POR TESTS — MEDIDO (21/08/2026)

`bench/mcp-cabos-sueltos.md` §3 ejecutó por fin la suite de `image-worker-mcp` (`npm install --legacy-peer-deps`, porque sin él falla con `ERESOLVE`; 702 paquetes, 177,3 MB): **117 tests en 6 ficheros, 6,43 s, 0 fallos.** Tres cosas que la suite delata y que no salían de leer el código:

1. **Devolver la imagen entera dentro del texto no es un descuido: es comportamiento contratado.** Los dos tests de HEIC afirman `resultContent.image.startsWith('data:image/jpeg;base64,')`. **Cualquiera que quite el antipatrón rompe la suite.** El patrón está publicado, vivo y defendido.
2. **Matiz de forma:** el base64 no viaja crudo, viaja con prefijo **`data:image/…;base64,`**. Una regla de detección escrita sobre «rachas de base64 ≥512 caracteres» lo pilla igual, pero conviene saber la forma exacta.
3. **El reparto de la suite es el dato de gobierno:** **75 de 117 tests (64 %) prueban tres backends de subida a la nube** y **solo 13 la conversión de imágenes**, que es lo único que a FileX le importa de este repo. **Un `6 passed / 117 passed` verde dice mucho menos de lo que parece.**

**Y aun así tiene el mejor criterio de aserción del carril, que es lo que hay que copiar** (`tests/tools/sharp.test.ts:369-380`): el test **abre la salida** y afirma sus propiedades reales (`sharp(buffer).metadata()` → `format`, `width`, `height`), en vez de conformarse con `exists()` más una subcadena de éxito —que es lo que hace `ffmpeg-mcp-lite`, donde **un fichero de 0 bytes pasaría**.

> **Para la suite de FileX no hay un ganador: se coge un eje de cada uno.** De `ffmpeg-mcp-lite`, **la estructura** (fixtures sintéticas con `lavfi`, `skip` por entorno, un `test_*.py` por herramienta) y **cero binarios comprometidos en el repo**. De `image-worker-mcp`, **el criterio de aserción** y el reparto correcto: **la gran mayoría rápidos y aislados, unos pocos de integración lenta con ficheros reales**.
>
> **Con una corrección que ninguno de los dos hace bien:** en `image-worker-mcp`, `fs.writeFileSync` **está mockeado** — el test captura el búfer, **lo escribe él mismo** y luego lo lee. **Un fallo en cómo la herramienta escribe en disco no lo atraparía.** Para FileX, cuya doctrina es que **la salida en disco es el producto**, la aserción tiene que correr sobre **el fichero que escribió el código bajo prueba**.

## kordoc: la forma que debe tener FileX

`chrisryugj/kordoc` (MIT) tiene `src/cli.ts` (1205 líneas) y `src/mcp.ts` (1177 líneas) **en la misma base de código**: un binario, dos superficies. Es exactamente la forma de entrega elegida para FileX.

### Cuánto cuesta de verdad la capa MCP
Las dos superficies pesan casi lo mismo. **Pero no porque la MCP duplique lógica**: `mcp.ts` importa el núcleo compartido (`parse`, `detectFormat`, `blocksToMarkdown`, `compare`, `extractFormFields`… desde `./index.js`). Su volumen se reparte en tres cosas que la CLI no necesita:

1. **87 declaraciones de esquema zod** — cada parámetro tipado y *descrito en lenguaje natural*, porque quien lee la descripción es un modelo.
2. **Saneado de rutas** — `realpathSync`, `resolve`, `isAbsolute`, comprobaciones de existencia. Un agente puede pedir cualquier ruta; la CLI la escribe una persona.
3. **Clasificación de errores** — `sanitizeError`, `classifyError`, `KordocError`: convertir excepciones en mensajes que el modelo pueda usar para corregirse.

**Estimación para FileX:** presupuestar la capa MCP como un trabajo comparable al de la CLI, no como un envoltorio de una tarde. Lo que se reutiliza es el núcleo; lo que hay que escribir es el contrato con el modelo y el aislamiento del sistema de ficheros.

> **Matiz MEDIDO (20/08/2026):** en kordoc el saneado de rutas **no** está en el núcleo compartido. `KORDOC_ROOT` solo lo aplica la superficie MCP: `src/cli.ts` no importa `safePath` ni `assertWithinRoot`, y la CLI leyó un fichero fuera de la raíz con `exit=0`. Es decir, las dos superficies **no comparten el confinamiento**. Para FileX, que tendrá cuatro (CLI, MCP, watcher, API), la regla es la R10 de `RESULTADOS-MCP.md` §10: **la validación vive en el núcleo, no en la superficie.**
