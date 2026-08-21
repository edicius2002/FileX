# MarkItDown — `microsoft/markitdown`
174.7k estrellas · **MIT** · Python · 12.8k líneas · 875 issues abiertas

**Veredicto: adoptar como dependencia para la ruta rápida documento a Markdown. No es un conversor universal, pese a las estrellas.**

El repo con más estrellas del ecosistema y el más malinterpretado: **solo convierte a Markdown**, en un único sentido. No produce PDF, DOCX ni imágenes. 12.8k líneas: es una capa fina sobre otras librerías, no un motor.

**Sin GPU** (0 ficheros con CUDA): extrae texto ya presente en el fichero. Para un PDF escaneado no sirve; ahí hacen falta Surya, PaddleOCR o Tesseract.

Incluye `packages/markitdown-mcp/`, **el MCP oficial de Microsoft**, con una sola herramienta `convert_to_markdown(uri)` que devuelve el documento entero como string al contexto del modelo: el antipatrón descrito en `00-mcp-patrones.md`.

**Papel en FileX:** ruta rápida y barata para documentos con texto embebido (DOCX, PPTX, XLSX, HTML, PDF con capa de texto). Al ser MIT y ligero, se integra directamente. Para lo demás, escalar a Docling o Marker.

**Salud:** 875 issues abiertas es mucho. Microsoft lo mantiene, pero la deuda de soporte es visible.
