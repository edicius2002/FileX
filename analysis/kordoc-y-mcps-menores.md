# Referencias MCP menores — `mcp-refs/`

## kordoc — `chrisryugj/kordoc`
1.7k estrellas · MIT · TypeScript · 65.5k líneas

**La referencia estructural más cercana a FileX.** CLI (`src/cli.ts`, 1205 líneas) y servidor MCP (`src/mcp.ts`, 1177 líneas) en la misma base de código, ambos importando el mismo núcleo desde `./index.js`. Convierte documentos coreanos (HWP, HWPX, PDF, Office) a Markdown.

Su desglose permite estimar el coste de la capa MCP para FileX: 87 esquemas zod, saneado de rutas (`realpathSync`, `isAbsolute`) y clasificación de errores (`sanitizeError`, `classifyError`). Ver `00-mcp-patrones.md`.

## Los MCP de conversión existentes: el hueco cuantificado
| Repo | Estrellas | Líneas | Qué hace |
|---|---|---|---|
| `KorigamiK/markitdown_mcp_server` | 86 | 162 | ⚠️ **No expone herramientas**: solo 2 prompts. `tools/list` → `-32601 Method not found` (verificado ejecutándolo). Un agente no puede invocarlo como conversor |
| `misbahsy/video-audio-mcp` | 84 | 2494 | FFmpeg vía MCP. Sin GPU. |
| `kevinwatt/ffmpeg-mcp-lite` | 26 | 1204 | Convertir, comprimir, recortar, subtítulos. Sin GPU. |
| `BoomLinkAi/image-worker-mcp` | 18 | 3400 | Redimensionar y optimizar con sharp. |

**Ninguno usa GPU. Ninguno pasa de 3400 líneas.** El techo del sector en conversión *invocable* son **84 estrellas** (`video-audio-mcp`): los 86 de `markitdown_mcp_server` coronan un servidor de prompts, no de herramientas.

Compárese con los 174.7k de MarkItDown o los 89.9k de Stirling-PDF: la demanda de conversión es enorme y la oferta vía MCP es testimonial. Es la asimetría central de esta investigación.

## `modelcontextprotocol/servers`
89.7k estrellas · MIT · 56 ficheros con referencias MCP. Implementaciones oficiales de referencia: usar como guía de estilo del protocolo, no de conversión (no hay ningún servidor de conversión de ficheros entre ellas).
