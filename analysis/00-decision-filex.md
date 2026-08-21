# Fase 3 — Decisión de arquitectura de FileX

## La pregunta central: ¿desde 0 o sobre una base?

**Respuesta: híbrido asimétrico. Desde cero el núcleo (grafo + registro + MCP), reutilizando todo lo demás.**

El razonamiento sale de los datos, no de la preferencia:

| Candidato | Por qué NO como base |
|---|---|
| SnapOtter | AGPL + CLA + `packages/enterprise` propietario. 100+ commits/mes hacen insostenible un fork en solitario. Es UI-first; FileX es agent-first. |
| ConvertX | AGPL. Y su despacho es justo lo que hay que rehacer (un salto, con bug de prioridad). |
| Stirling-PDF | Solo PDF, Java, y su MCP está bajo licencia de pago. |
| VERT / morphos | Parados o abandonados. |
| gotenberg | No es un conversor universal; es una dependencia excelente. |
| **transmute** | **El único viable (MIT), pero es una API web sin CLI, sin MCP, sin watcher y sin GPU.** |

Adoptar transmute completo obligaría a arrastrar su frontend, su capa k8s y su modelo de colas orientado a web, cuando FileX es local-first. **Lo que sí se toma de transmute es su núcleo conceptual**, que es MIT y está probado: el registro por reflexión con `can_register()`, la `ConverterInterface`, y adaptadores de nicho concretos (`fonttools`, `pysubs2`, `pandas`, `email`).

Lo que hay que escribir de cero es precisamente lo que **nadie tiene**: el grafo de conversión, la capa MCP y la ruta GPU.

## Los cuatro diferenciadores, ordenados por relación valor/coste

| # | Diferenciador | Evidencia | Coste |
|---|---|---|---|
| 1 | **Grafo multi-salto** | 2,89× cobertura (152 112 → 439 672 pares) con los mismos motores | Bajo: puramente algorítmico |
| 2 | **NVENC en vídeo** | 3,3× medido; ningún orquestador lo usa | Muy bajo: parámetros de invocación |
| 3 | **MCP agent-first** | El techo del sector en conversión invocable son 84 estrellas (`video-audio-mcp`); los 86 de `markitdown_mcp_server` son un servidor de prompts, no de herramientas | Medio: comparable a la CLI |
| 4 | **OCR en GPU** | SnapOtter lo bloquea en CPU por diseño; tu 3060 es cc 8.6 (bfloat16) | Medio-alto: sidecar Python + modelos |

## Lenguaje del núcleo: la medición cambia la respuesta

El plan planteaba tres opciones. Las mediciones de `bench/results.md` reordenan el argumento:

- El suelo de creación de proceso en Windows es **~49 ms**, independiente del lenguaje.
- Go ahorra **~44 ms** por invocación frente a Python con imports.
- Pero **cualquier conversión arranca además un motor externo**: ffmpeg cuesta 61 ms solo en existir, magick 73 ms para un PNG de 64×64.
- Y **para el servidor MCP el arranque en frío es irrelevante**: el proceso vive.

Es decir: el lenguaje del núcleo controla ~40 ms de una invocación de 100-160 ms, y solo en la CLI. **El argumento "Rust por el arranque" queda muy debilitado.** A cambio, Rust cuesta la curva más dura y ninguno de los siete orquestadores analizados está escrito en él (dos Go, dos TypeScript, uno Python, uno Java, uno Svelte): no hay nada que reutilizar.

### Recomendación: Python primero, con el sidecar desde el día 1

No es "todo Python y ya veremos". Es Python **con la frontera de proceso correcta desde el principio**:

```
filex (CLI / MCP / watcher / API)      <- Python, proceso único y persistente
  |
  +-- registro + grafo de conversión   <- el núcleo propio
  |
  +-- motores externos                 <- execFile: ffmpeg, magick, soffice, pandoc...
  |
  +-- sidecar IA                       <- proceso Python aparte, modelos en VRAM
        docling / surya / faster-whisper
```

Por qué:
1. **El ecosistema que importa es Python.** Docling, Marker, Surya, faster-whisper, PyMuPDF, Pillow, DuckDB. Todo el diferenciador 4 vive ahí; en Go o Rust se accede por IPC, con coste y sin ganancia.
2. **La base reutilizable (transmute) ya es Python** y MIT.
3. **El sidecar separado no es opcional en ningún lenguaje**: SnapOtter lo aisla porque *"torch/CUDA reserve huge virtual space"* (`apps/api/src/lib/env.ts:70`). Ese problema existe igual con un núcleo en Go.
4. **La deuda es acotada y localizada.** Si algún día molesta el arranque de la CLI, se reescribe el despachador —unos cientos de líneas— en Go, dejando intactos el sidecar y los adaptadores.

Go sigue siendo defendible si la prioridad real fuese distribuir un binario único sin dependencias. Pero eso choca con el sidecar Python, que hay que instalar de todos modos para OCR y transcripción.

## Diseño del núcleo

**Grafo de conversión.** Nodos = formatos, aristas = (motor, coste). El coste combina tiempo estimado, pérdida de fidelidad y si preserva texto. Dijkstra elige el camino. Resuelve de una vez el multi-salto, la prioridad correcta entre motores solapados (el bug de ConvertX) y el mensaje de "por qué no se puede", valioso cuando quien pregunta es un agente.

**Registro por reflexión con `can_register()`** (patrón de transmute). Con solo 4 de los ~12 motores instalados en tu máquina, arrancar con capacidades reducidas en vez de fallar no es un detalle: es requisito.

**Sondeo de capacidades en ejecución.** `av1_nvenc` aparece listado y no funciona. Las capacidades se detectan probando y se cachean, no se deducen.

**Capa MCP generada desde el registro**, como hace `McpToolCatalog` de Stirling-PDF: un motor nuevo se convierte en herramienta sin tocar la capa MCP. Herramientas devolviendo **ruta + metadatos, nunca contenido**, con `readOnlyHint`/`destructiveHint` y caché idempotente por hash.

## Orden de construcción sugerido

1. Registro + grafo + CLI con ffmpeg e ImageMagick (**76% de la cobertura de formatos con dos motores**).
2. NVENC con sondeo y degradación a CPU (3,3× medido, coste casi nulo).
3. Capa MCP generada desde el registro.
4. Gotenberg en Docker para ofimática a PDF (evita instalar LibreOffice en Windows).
5. Sidecar IA: faster-whisper `large-v3`, luego Docling, luego Surya para OCR en GPU.
6. Watcher y API HTTP local, que a esas alturas son superficies delgadas sobre el mismo núcleo.

Los pasos 1 y 2 ya superan en cobertura y velocidad a todo lo analizado, salvo en OCR y ofimática.
