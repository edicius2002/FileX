# Licencias: qué se puede reutilizar y bajo qué escenario

## Principio que sostiene toda la arquitectura
**Invocar un binario como proceso separado no contamina.** Enlazar una librería GPL dentro de tu programa obliga a publicar tu programa como GPL; ejecutar `ffmpeg entrada.mp4 salida.webm` como proceso externo, no. Por eso todos los conversores serios del ecosistema son orquestadores de procesos, y por eso FileX debe serlo también: preserva todas las opciones de negocio sin coste técnico.

Confirmado en el código: ConvertX usa `execFile` de `node:child_process` en todos sus adaptadores, con argumentos como array (sin shell). Es el patrón correcto y además inmune a inyección.

## Los repositorios clonados

| Repo | Licencia | ¿Copiar su código? |
|---|---|---|
| **transmute** | **MIT** | ✅ Sin restricciones |
| **gotenberg** | **MIT** | ✅ Sin restricciones |
| **morphos** | MIT | ✅ Sin restricciones |
| **markitdown** | MIT | ✅ Sin restricciones |
| **docling** / `-mcp` / `-serve` | MIT | ✅ Sin restricciones |
| **faster-whisper** | MIT | ✅ Sin restricciones |
| **kordoc** | MIT | ✅ Sin restricciones |
| **modelcontextprotocol/servers** | **MIT/Apache-2.0 (transición)** | ✅ Sin restricciones de fondo, **con obligaciones de Apache-2.0** — ver nota |
| **marker**, **surya** | Apache-2.0 | ✅ Con aviso de patentes y atribución |
| **MinerU** | Apache-2.0 + términos | ✅ Atribuir si es servicio online |
| **OCRmyPDF** | MPL-2.0 | ⚠️ Copyleft por fichero: publicar los ficheros MPL modificados |
| **ConvertX** | AGPL-3.0 | ❌ Contamina incluso ofreciéndolo por red |
| **VERT** | AGPL-3.0 | ❌ Igual |
| **SnapOtter** | AGPL-3.0 + `packages/enterprise` propietario + CLA | ❌ Igual, y alimenta a un competidor comercial |
| **Stirling-PDF** | MIT **con 10 directorios excluidos** | ⚠️ El núcleo sí; `app/proprietary/` (donde vive su MCP) requiere suscripción de pago |

### Nota sobre `modelcontextprotocol/servers` — corrección **MEDIDA** (20/08/2026)

**Se creía MIT.** Todo el proyecto lo daba por MIT, y es el repo del que más piezas se propone copiar
(el confinamiento completo de `src/filesystem`, ~1.000 líneas de tests). **Su `LICENSE` dice otra cosa**
(`repos/mcp-refs/servers/LICENSE:1-5`, verificado):

> *«The MCP project is undergoing a licensing transition from the MIT License to the Apache License,
> Version 2.0»* — el código nuevo es Apache-2.0; **las contribuciones cuyo autor no consintió el
> relicenciamiento siguen bajo MIT**; la documentación (no especificaciones) es CC-BY-4.0.

Sus `package.json` no declaran licencia: `"license": "SEE LICENSE IN LICENSE"`.

**Qué cambia y qué no:**

- **No invalida ningún veredicto de reutilización.** Apache-2.0 es permisiva y sirve igual que MIT.
- **Sí cambia las obligaciones.** Apache-2.0 exige **preservar los avisos, marcar los ficheros
  modificados y propagar el `NOTICE`**; MIT solo exige el aviso de copyright. Como la licencia efectiva
  **por fichero es ambigua**, lo seguro es tratar todo lo tomado de `servers/` como Apache-2.0, cuyas
  obligaciones son un superconjunto de las de MIT.

Detalle en `analysis/00-mcp-componentes.md` §3.1 y `RESULTADOS-MCP.md` §12.

## Los motores externos (binarios, no código)

| Motor | Licencia | Efecto al invocarlo como proceso |
|---|---|---|
| FFmpeg (build GPL con x264/x265) | GPL | Ninguno sobre FileX. Distribuir el binario sí arrastra la GPL de ese binario. |
| ImageMagick | Estilo Apache | Sin problema |
| libvips | LGPL-2.1 | Sin problema (y menos aún como proceso) |
| LibreOffice | MPL-2.0 | Sin problema |
| Pandoc | GPL-2.0 | Ninguno como proceso |
| Calibre | GPL-3.0 | Ninguno como proceso |
| Tesseract | Apache-2.0 | Sin problema |
| Ghostscript | AGPL | ⚠️ El más agresivo. Como proceso separado sigue siendo seguro, pero **evitar redistribuirlo**; hay licencia comercial de Artifex. |
| qpdf | Apache-2.0 | Sin problema |

Nota verificada: tu ffmpeg está compilado con `--enable-gpl --enable-libx264 --enable-libx265`, es decir, es un binario **GPL**. Basta con no empotrarlo y no redistribuirlo como parte de FileX (o documentar su licencia si se empaqueta).

## Recomendación según escenario

**Uso personal o proyecto abierto:** irrelevante. Usar lo que sea, incluido código AGPL.

**Posible comercialización futura:** partir de **transmute (MIT)**, apoyarse en Docling, Marker, Surya, faster-whisper y MarkItDown (MIT/Apache), invocar todos los motores como procesos y **no copiar una sola línea de ConvertX, VERT o SnapOtter**. De ellos se pueden tomar ideas y tablas de formatos —que no son código— pero no implementación.

Este camino no cuesta más trabajo que el otro. Es la razón por la que conviene decidirlo ahora y no después.
