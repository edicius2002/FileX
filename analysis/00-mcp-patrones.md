# Patrones MCP: qué hacen bien y mal las referencias existentes

Analizado sobre `markitdown-mcp` (Microsoft, oficial), `docling-mcp` (IBM, 709 ⭐) y `kordoc` (1.7k ⭐, CLI+MCP en un binario).

## El error de diseño: devolver el contenido

`markitdown-mcp` es el MCP de conversión más difundido y expone **una sola herramienta**:

```python
@mcp.tool()
async def convert_to_markdown(uri: str) -> str:
    """Convert a resource described by an http:, https:, file: or data: URI to markdown"""
    return MarkItDown(...).convert_uri(uri).markdown
```

Devuelve **el documento entero como string**, es decir, directamente al contexto del modelo. Un PDF de 200 páginas son decenas de miles de tokens inyectados de golpe. Y para salidas binarias — un MP4, un PNG — el patrón sencillamente no existe.

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
    cleanup_memory()      # libera los modelos tras convertir
    return result         # -> {document_key, ya_estaba_en_cache}
```

Además: herramienta aparte `is_document_in_local_cache()` para evitar reconversiones, y `ToolAnnotations(readOnlyHint/destructiveHint)` para que el cliente MCP sepa qué operaciones son seguras.

## Reglas que FileX debe seguir

1. **Devolver ruta + metadatos, nunca contenido.** `{ruta_salida, formato, bytes, duración_ms, motor_usado, camino_recorrido}`. El agente decide después si quiere leer el fichero.
2. **Anotar cada herramienta** con `readOnlyHint`/`destructiveHint`. Convertir crea ficheros; sobrescribir destruye. El cliente debe poder distinguirlo.
3. **Caché idempotente por hash del contenido + parámetros.** Si el agente pide dos veces lo mismo, la segunda es gratis. `docling-mcp` lo hace por clave de documento; con hash es más robusto.
4. **Liberar los modelos GPU tras el trabajo** (`cleanup_memory()`), o el sidecar acapara los 12 GB de la 3060 indefinidamente.
5. **Pocas herramientas, bien nombradas.** markitdown expone 1 (insuficiente), docling-mcp más de 10 entre conversión y generación (empieza a saturar la selección del modelo). Para FileX: `convert`, `inspect`, `list_targets`, `batch` — cuatro, y la mitad son de solo lectura.

## kordoc: la forma que debe tener FileX

`chrisryugj/kordoc` (MIT) tiene `src/cli.ts` (1205 líneas) y `src/mcp.ts` (1177 líneas) **en la misma base de código**: un binario, dos superficies. Es exactamente la forma de entrega elegida para FileX.

### Cuánto cuesta de verdad la capa MCP
Las dos superficies pesan casi lo mismo. **Pero no porque la MCP duplique lógica**: `mcp.ts` importa el núcleo compartido (`parse`, `detectFormat`, `blocksToMarkdown`, `compare`, `extractFormFields`… desde `./index.js`). Su volumen se reparte en tres cosas que la CLI no necesita:

1. **87 declaraciones de esquema zod** — cada parámetro tipado y *descrito en lenguaje natural*, porque quien lee la descripción es un modelo.
2. **Saneado de rutas** — `realpathSync`, `resolve`, `isAbsolute`, comprobaciones de existencia. Un agente puede pedir cualquier ruta; la CLI la escribe una persona.
3. **Clasificación de errores** — `sanitizeError`, `classifyError`, `KordocError`: convertir excepciones en mensajes que el modelo pueda usar para corregirse.

**Estimación para FileX:** presupuestar la capa MCP como un trabajo comparable al de la CLI, no como un envoltorio de una tarde. Lo que se reutiliza es el núcleo; lo que hay que escribir es el contrato con el modelo y el aislamiento del sistema de ficheros.
