# Docling — `docling-project/docling` (más `-mcp` y `-serve`)
65.2k estrellas · **MIT** · Python · 121k líneas · IBM · 37 ficheros con CUDA

**Veredicto: el motor de IA documental recomendado para FileX. El mejor equilibrio calidad/licencia/ergonomía del conjunto.**

Convierte documentos a Markdown y JSON con modelos de análisis de maquetación, no con heurísticas. Detecta tablas, orden de lectura y estructura.

**GPU bien resuelta.** `docling/datamodel/accelerator_options.py` expone un enum `AcceleratorDevice` con `AUTO`, `CPU`, `CUDA`, `cuda:N`, `MPS` y `XPU`, más `cuda_use_flash_attention2` y control de `num_threads`. Es la abstracción de dispositivo más limpia de todos los motores analizados: **copiar este modelo en FileX**.

**Ecosistema completo bajo MIT**, cosa rara:
- `docling-serve` (1.7k estrellas): el motor como servicio HTTP, el patrón exacto del sidecar persistente.
- `docling-mcp` (709 estrellas): **la mejor referencia MCP del sector** (ver `00-mcp-patrones.md`). Devuelve claves de caché en vez de contenido, anota las herramientas con `readOnlyHint` y `destructiveHint`, y libera memoria con `cleanup_memory()`.
- Además `docling-core`, `docling-parse`, `docling-eval` y `docling.rs` (port a Rust, 39 estrellas: inmaduro, pero señal de por dónde va el proyecto).

**Para la 3060:** cabe de sobra en 12 GB, y `cuda_use_flash_attention2` es aprovechable en Ampere.
