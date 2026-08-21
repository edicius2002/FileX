# FileX — Análisis completo del ecosistema de conversión de archivos

**Fecha:** 19 de agosto de 2026
**Alcance:** 22 repositorios clonados y auditados a nivel de código, ejecutados en la máquina real
**Hardware:** RTX 3060 12 GB (compute capability 8.6, driver 572.61) · Windows 10 · 12 núcleos · Docker 29.4.3 + WSL2 · Python 3.11.9

> Todas las cifras proceden de código clonado o de comandos ejecutados en esta máquina. **Ninguna procede de README ni de metadatos de GitHub.** Donde ambos discrepaban, se indica explícitamente.

---

## 1. Resumen ejecutivo

El ecosistema está **partido en dos mitades que nadie ha unido**:

- Los **orquestadores de conversión** con tracción (Stirling-PDF 89,9k ⭐, ConvertX 18,5k, VERT 15,4k) **no usan la GPU, no exponen MCP y no encadenan conversiones**.
- Los **motores de IA documental** (Docling, MinerU, Surya, Marker, faster-whisper) **son GPU-nativos pero no convierten un MP4 ni redimensionan un PNG**.

### Los cinco diferenciadores, reevaluados tras ejecutar

> La lista original de cuatro huecos se formó con **metadatos de GitHub y lectura de código**. La fase de ejecución la desmintió parcialmente: **dos se debilitaron, uno hubo que reformularlo, y el más fuerte no estaba en la lista**. El detalle completo, con la separación entre lo medido y lo pendiente, está en **`HUECOS.md`**.

| # | Diferenciador | Evidencia | Estado |
|---:|---|---|---|
| **1** | **Verificación obligatoria de la salida** | **7 fallos independientes en 6 proyectos**: un `.avif` que es PNG entregado con estado "Done"; pérdida silenciosa de pista de audio en **los dos** competidores; degradación 16→8 bits sin avisar; cadena vacía con `isError: false` | ✅ **Medido. El más fuerte** |
| **2** | Grafo con **coste por arista** | 0 de 7 orquestadores hacen búsqueda de camino. ConvertX elige mal el motor (`png→jpg` acaba en ffmpeg teniendo vips disponible) | ✅ Medido · ⏳ **el 2,93× es alcanzabilidad, no fidelidad: sin medir** |
| **3** | MCP **multi-modal en un solo servidor** | Los servidores no coexisten (`mcp~=1.8.0` frente a `mcp>=2.0.0`). ~2 400× de diferencia en tokens entre patrones | ✅ Medido · ⏳ **solo sobre MCP documentales; el caso binario sin probar** |
| **4** | NVENC en vídeo | Ningún orquestador lo usa. **8,39× en HEVC**, n=9. Pero se pasa un 8–11 % del bitrate pedido | ✅ Medido · ⏳ **rendimiento en lote sin probar** |
| **5** | OCR en GPU | Todos lo hacen en CPU. Resuelto con Docling + RapidOCR `backend="torch"`, **coste de infraestructura cero** | ⚠️ **Degradado: ya no es foso** · ⏳ falta OCRmyPDF como preprocesador |

**Los tres criterios de juicio:** ¿nadie lo hace? ¿es barato? ¿lo nota el usuario? **Solo el nº 1 cumple los tres.** El OCR es replicable en una tarde, el patrón MCP ya lo implementa bien IBM, NVENC solo importa en lote, y el grafo amplía alcance sin garantizar corrección.

**El argumento de FileX**, en consecuencia, no es *"convierte más cosas más rápido"* —discutible y en parte replicable— sino:

> **Es el único que garantiza que lo que te entrega es lo que pediste.**

### Qué queda pendiente de medir

| Pendiente | Afecta a | Especificado en |
|---|---|---|
| Fracción de los 447 398 caminos con fidelidad aceptable | Difer. 2 | — |
| ~~Qué devuelve un MCP tras convertir un **binario**~~ · **RESUELTO 20/08** | Difer. 3 | `RESULTADOS-MCP.md` §3 |
| Si 27 herramientas saturan la **elección** del modelo · *sigue pendiente: el catálogo está medido (7.964 tok), el comportamiento no* | Difer. 3 | `RESULTADOS-MCP.md` §13 |
| Rendimiento NVENC en lote sobre una carpeta real | Difer. 4 | — |
| **OCRmyPDF como preprocesador** — único candidato para la dificultad 3 | Difer. 5 | `AGENTES-PRUEBAS-PENDIENTES.md` |
| Reintento de Surya por `llamacpp` o VRAM configurable | Difer. 5 | `AGENTES-PRUEBAS-PENDIENTES.md` |
| MinerU con el extra `[vlm]` | Difer. 5 | `AGENTES-PRUEBAS-PENDIENTES.md` |
| Coste real de implementar el contrato de verificación | Difer. 1 | `PLAN-ORQUESTADOR.md` §7, hito 3 |

**Cobertura de la ejecución:** de los 9 motores de IA clonados, **6 se ejecutaron y 3 no** (surya no arranca; marker y MinerU nunca se intentaron). De los 6 repos de referencias MCP, **ninguno se ejecutó** y solo uno se analizó a fondo.

**Decisión de arquitectura:** híbrido asimétrico. Núcleo propio (grafo + registro + **verificación** + MCP) desde cero, reutilizando todo lo demás. Python con sidecar separado desde el día 1.

---

## 2. Tabla maestra de los 22 repositorios

### 2.1 Orquestadores — candidatos a base

| Repo | ⭐ | Licencia | Lenguaje | Líneas | GPU | MCP | Multi-salto | Commits/30d | Veredicto |
|---|---:|---|---|---:|---|---|---|---:|---|
| Stirling-PDF | 89 900 | MIT con 10 exclusiones | Java | 570 828 | ❌ | 💰 de pago | ❌ | 100+ | No (solo PDF, Java) |
| ConvertX | 18 517 | AGPL-3.0 | TS | 5 960 | ❌ | ❌ | ❌ | 8 | No (AGPL + despacho roto) |
| VERT | 15 380 | AGPL-3.0 | Svelte | 10 614 | ❌ imposible | ❌ | ❌ | 1 | No (moribundo) |
| gotenberg | 12 886 | **MIT** | Go | 38 436 | ❌ | ❌ | ❌ | activo | **Dependencia**, no base |
| SnapOtter | 2 226 | AGPL + comercial + CLA | TS | 522 719 | ✅ parcial | ❌ | ❌ | 100+ | No (licencia + ritmo) |
| transmute | 1 298 | **MIT** | Python | 50 682 | ❌ | ❌ | ❌ | 15 | ✅ **Única base viable** |
| morphos | 1 300 | MIT | Go | 4 025 | ❌ | ❌ | ❌ | 0 | No (abandonado + RCE) |

### 2.2 Motores de IA

| Repo | ⭐ | Licencia | Líneas | Ficheros CUDA | VRAM medida | Rol en FileX |
|---|---:|---|---:|---:|---:|---|
| markitdown | 174 667 | MIT | 12 807 | 0 | — | Ruta rápida doc→Markdown |
| MinerU | 77 989 | Apache + términos | 71 556 | 15 | sin probar | Aplazar a v2 |
| docling | 65 198 | **MIT** | 121 131 | 37 | **910 MiB** | ✅ **Motor documental** |
| marker | 38 861 | Apache-2.0 | 16 467 | 7 | sin probar | ⏳ **el bloqueo era diagnóstico erróneo**: su backend es parámetro público |
| OCRmyPDF | 34 500 | MPL-2.0 | 41 102 | 0 | — | Referencia de preprocesado |
| faster-whisper | 24 992 | **MIT** | 4 027 | 5 | **4 525 MiB** (large-v3) | ✅ **Adoptar tal cual** |
| surya | 21 294 | Apache-2.0 | 13 541 | 15 | ❌ sin dato | ⏳ solo se probó su backend por defecto; **tiene 4** |
| docling-serve | 1 745 | MIT | 11 032 | 0 | — | Patrón de sidecar |
| docling-mcp | 709 | MIT | 6 976 | 2 | — | ✅ Referencia MCP |

### 2.3 Referencias MCP

| Repo | ⭐ | Líneas | Herramientas | GPU | Aporte |
|---|---:|---:|---:|---|---|
| servers (oficial) | 89 685 | 14 957 | — | ❌ | Guía de estilo. **Ningún conversor entre ellas** |
| kordoc | 1 748 | 65 463 | 16 | ❌ | ✅ **CLI + MCP en un binario** |
| markitdown_mcp_server | 86 | 162 | **0** | ❌ | ⚠️ **No es un servidor de herramientas**: solo expone 2 prompts. `tools/list` responde `-32601 Method not found` |
| video-audio-mcp | 84 | 2 494 | — | ❌ | FFmpeg vía MCP |
| ffmpeg-mcp-lite | 26 | 1 204 | — | ❌ | Convertir, comprimir, recortar |
| image-worker-mcp | 18 | 3 400 | — | ❌ | sharp |

**Techo del sector MCP en conversión invocable: 84 estrellas** (`video-audio-mcp`), frente a los 174 667 de MarkItDown.

> **Corrección validada empíricamente.** `markitdown_mcp_server` (86 ⭐) figuraba antes como "el MCP de conversión más popular del mundo" con 1 herramienta. Ejecutándolo por el protocolo, declara solo la capacidad `prompts` y **`tools/list` devuelve `-32601 Method not found`**: no es comparable con servidores de herramientas. Además se identifica como `"example" v0.1.0` (el nombre real nunca llega al cliente) y lanza `os.system("notify-send ...")` al arrancar, que falla en Windows.

---

## 3. Comparativas transversales

### 3.1 GPU: quién acelera y quién no

| Repo | Ficheros con CUDA/NVENC | ¿Acelera de verdad? |
|---|---:|---|
| Stirling-PDF | 0 | ❌ 571k líneas de Java sin una llamada |
| ConvertX, transmute, gotenberg, morphos | 0 | ❌ |
| VERT | 0 | ❌ imposible por diseño (WASM) |
| markitdown | 0 | ❌ no lo necesita |
| OCRmyPDF | 0 | ❌ Tesseract es CPU |
| SnapOtter | 46 | ⚠️ sí, **salvo OCR, bloqueado en CPU adrede** |
| docling | 37 | ✅ maquetación y tablas (su OCR venía en CPU) |
| MinerU / surya | 15 / 15 | ✅ (surya inutilizable en la práctica) |
| marker | 7 | ✅ (bloqueado) |
| faster-whisper | 5 | ✅ |

### 3.2 Licencias: qué se puede reutilizar

| Repo | Licencia | ¿Copiar su código? |
|---|---|---|
| transmute, gotenberg, morphos, markitdown, docling (+mcp/serve), faster-whisper, kordoc | MIT | ✅ Sin restricciones |
| marker, surya | Apache-2.0 | ✅ Con atribución. ⚠️ Los *pesos* se licencian aparte |
| MinerU | Apache + términos | ✅ Umbrales de 100 M usuarios / 20 M USD irrelevantes; atribuir si es servicio online |
| OCRmyPDF | MPL-2.0 | ⚠️ Copyleft por fichero |
| ConvertX, VERT | AGPL-3.0 | ❌ Contamina incluso ofreciéndolo por red |
| SnapOtter | AGPL + `packages/enterprise` propietario + CLA irrevocable | ❌ Y alimentaría a un competidor comercial |
| Stirling-PDF | MIT con 10 directorios excluidos | ⚠️ El núcleo sí; **su MCP requiere suscripción** |

**Principio que sostiene la arquitectura:** invocar un binario como proceso separado **no contamina**; enlazar una librería GPL sí. Por eso todos los conversores serios son orquestadores de procesos, y por eso FileX debe serlo: preserva todas las opciones de negocio sin coste técnico.

Motores externos: FFmpeg-GPL, Pandoc y Calibre son GPL, sin efecto como proceso separado. **Ghostscript (AGPL) es el más agresivo: seguro como proceso, pero conviene no redistribuirlo.**

### 3.3 Matriz de formatos, extraída del código

| Motor | Entradas | Salidas | Exclusivas | Sin él se pierde |
|---|---:|---:|---:|---|
| ffmpeg | 473 | 202 | **422** | todo el audio y el vídeo |
| imagemagick | 245 | 183 | 78 | formatos de imagen heredados |
| graphicsmagick | 167 | 130 | 29 | metadatos y variantes TIFF |
| vips | 45 | 23 | 17 | imagen científica y microscopía |
| libreoffice | 41 | 22 | 29 | ofimática heredada (doc, abw, cwk) |
| pandoc | 40 | 58 | 31 | markup académico y bibliografías |
| calibre | 26 | 20 | 16 | ebooks y cómic (azw4, cbr, djvu) |

**Totales canónicos: 896 formatos de entrada, 503 de salida.**
**ffmpeg + ImageMagick cubren 675 de 896 entradas: el 75 %.** El "1000+ formatos" del marketing son, en esencia, dos binarios.

Ampliando a las cuatro fuentes (ConvertX, transmute, SnapOtter, gotenberg): **1 002 entradas, 528 salidas, 1 118 formatos distintos**.

> **Nota metodológica.** Una primera extracción dio 893/496 porque la expresión regular limitaba los identificadores a 12 caracteres y descartaba 7 dialectos largos de pandoc (`markdown_strict`, `jats_articleauthoring`…). Las cifras de este documento son las de la extracción sin límite, confirmadas por una segunda extracción independiente vía AST.

### 3.4 El cálculo que justifica el grafo

| Estrategia | Pares alcanzables |
|---|---:|
| **Un salto** — ConvertX, transmute, SnapOtter, todos | 152 584 |
| **Grafo dirigido, hasta 3 saltos** | **447 398** |
| **Conversiones nuevas que hoy no puede hacer nadie** | **294 814** |

**Multiplicador: 2,93× con exactamente los mismos motores.**

| Conversión | Hoy | Con grafo |
|---|---|---|
| `epub → png` | ❌ imposible | ✅ 2 saltos |
| `docx → webp` | ❌ imposible | ✅ 2 saltos |
| `tex → docx` | ❌ imposible | ✅ 2 saltos |
| `cbz → pdf` | ✅ ya directo | igual |

> **Salvedad honesta:** 447 398 es un límite superior de *alcanzabilidad*, no una promesa de fidelidad. Encadenar degrada: pasar por un formato rasterizado destruye el texto seleccionable, y algunos pares declarados son nominales. Por eso el grafo necesita **coste por arista** (velocidad, pérdida de calidad, si preserva texto), no solo conectividad.

---

## 4. Hallazgos por repositorio

## 4.1 Orquestadores

### ConvertX · 18,5k ⭐ · AGPL-3.0 · TypeScript/Bun

**Defecto de despacho confirmado** (`src/converters/main.ts:213-229`):

```js
for (converterName in properties) {          // bucle EXTERNO
  for (const key in converterObj.properties.from) {
    if (from.includes(fileType) && to.includes(convertTo)) {
      converterFunc = converterObj.converter;
      break;                                  // rompe SOLO el interno
    }
  }
}                                             // el externo nunca se corta
```

- Gana el **último** conversor que coincide, no el primero. El comentario "Prioritize Inkscape for EMF files" del propio código es inoperante: el orden del registro actúa como **prioridad inversa**.
- Consecuencia medida: en `png→jpg` coinciden vips (#4), ImageMagick (#13), GraphicsMagick (#14) y ffmpeg (#16) — **gana ffmpeg**, el peor de los cuatro para imagen fija.
- `converterName` es la variable del `for...in`: al terminar vale la última clave del registro. **El log reporta casi siempre `markitDown`**, sea cual sea el motor real.
- **Sin encadenamiento**: búsquedas de `chain|graph|bfs|intermediate` dan cero resultados reales.

**En ejecución (96 invocaciones reales):**

- **Entrega ficheros falsos con estado "Done".** `png→avif` produce un `.avif` cuyos bytes mágicos son `89 50 4E 47` — **es un PNG**, 42 855 B frente a los 3 137 B del AVIF real. El error de ImageMagick (`no encode delegate for AVIF`) es un *warning* con código de salida 0 y el motor cae al formato origen. Con `vips` sí falla honestamente.
- **`dasel` está roto**: se invoca con sintaxis v1 (`--file`) contra un binario v2. **Todas** sus conversiones de datos son inalcanzables. Adaptador declarado, contado en la matriz, muerto en ejecución.
- **Degradaciones silenciosas**: PDF→imagen a **72 ppp fijos**, audio a **64 kbps** cuando se piden 192, GIF sin control de fps ni ancho, imagen→PDF con página de 1920×1080 pt (68 cm).
- Pierde una pista de audio del MKV, en silencio.
- **Su mejor resultado**: conserva los 16 bits del TIFF, donde SnapOtter degrada a 8.
- **Hojas de cálculo**: no declara `xlsx`/`xls`/`ods`/`ppt`/`odp` — cero apariciones en sus 20 adaptadores; `libreoffice.ts` solo registra la familia `text:` (líneas 6 y 51). **Pero el motor sí sabe**: forzado por API usa `calc_pdf_Export` y produce un PDF con texto seleccionable correcto. **El catálogo esconde una función existente**, y su interfaz web nunca la ofrece.
- Cobertura: **15/19**.

**Lo aprovechable:** el mapa de 20 motores (inkscape, libjxl, resvg, vips, libheif, xelatex, calibre, dasel, libreoffice, pandoc, msgconvert, dvisvgm, imagemagick, graphicsmagick, assimp, ffmpeg, potrace, vtracer, vcf, markitdown), sus matrices `from`/`to`, y el patrón `execFile` sin shell.

---

### SnapOtter · 2,2k ⭐ · AGPL + comercial + CLA · TypeScript

El competidor directo real: creado el 2026-03-29, 100+ commits/mes, 200+ herramientas en 5 modalidades, CUDA, REST y pipelines.

**Arquitectura — la parte valiosa.** Ya usa el híbrido núcleo-TS + sidecar-Python que se proponía para FileX. Es la validación independiente más fuerte del diseño.

- **Corrección a un análisis previo:** `bridge.ts:280` define `PythonDispatcher`, que **es persistente**. El `spawn` por petición está en `runPerRequest` (`bridge.ts:648`) y es la ruta de **respaldo** — el código lo dice: *"Try persistent dispatcher first"* y *"Fall back to per-request spawning"* (`bridge.ts:896-919`). Cuatro rutas de ejecución, tres persistentes.
- La asimetría real es **venv mutable compartido frente a runtime inmutable firmado**, y explica `venv-lock.ts`: pip reescribiendo un `.so` mientras un trabajo lo tiene abierto revienta el sidecar.
- **IPC**: NDJSON por stdin/stdout. **Los binarios nunca pasan por la tubería** — se intercambian por disco y el protocolo solo lleva rutas. Límite duro de 64 KB por petición (`ocr-runtime-dispatcher.ts:87`) que lo hace estructuralmente imposible.
- `GenerationLease` no arbitra proceso ni GPU, sino **la generación del runtime en disco**, para que el instalador no borre un árbol que un proceso vivo usa. Es flock del kernel más fichero-latido cada 5 s.
- Peticiones en vuelo durante rotación: `beginDrain()` cierra stdin solo con la cola vacía, y el candidato nuevo pasa un smoke test real antes de que el viejo drene.

**No gestiona la VRAM en absoluto:**

- Cero consultas proactivas de memoria de GPU. Las cinco coincidencias son **regex de detección de errores** (`/out of memory|cudaerrormemoryallocation|bad_alloc/i` en `bridge.ts:99` y `background-removal.ts:33`). `nvidia-smi` solo se usa para leer el nombre de la tarjeta (`gpu.py:18`).
- `dispatcher.py:290` ejecuta cada petición con `exec(code, module_globals)` sobre un espacio de nombres **nuevo**: solo sobrevive la caché de imports, **los pesos se recargan en cada llamada**.
- Sus gates de memoria son de RAM del cgroup y **se desactivan en anfitriones con GPU** (`hq-memory-gate.ts:32`).

**Renuncias deliberadas:**

- **OCR bloqueado en CPU por diseño**: `validateReadinessResult` (`ocr-runtime-dispatcher.ts:1028-1040`) **lanza excepción** si `result.device !== "cpu"`.
- Transcripción con faster-whisper (`cuda`+`float16` / `cpu`+`int8`), pero **solo empaqueta `faster-whisper-small`** para no inflar la imagen Docker.
- Su runtime de OCR **no reinicia** tras fallo — sin backoff ni contador de crashes, al contrario que `bridge.ts` (5 crashes en 60 s → desactivado permanentemente).

**Cobertura:** aporta **~0 nueva**. Solo 5 entradas nuevas frente a ConvertX+transmute (`fit`, `gpr`, `m2ts`, `mts`, `ptx`) y **cero salidas nuevas**. Sus "23 RAW" son 21 que ffmpeg e ImageMagick ya declaran. `media-engine` y `doc-engine` no declaran tabla alguna.

**En ejecución:**

- `403 MUST_CHANGE_PASSWORD` bloqueaba **toda** su API — la razón por la que un intento anterior no pudo convertir nada.
- Cobertura **18/19**. CSV patológico **impecable**: conserva coma en campo, comillas escapadas, UTF-8 y salto embebido, y **consume el BOM** (clave `id`, no `\ufeffid`), que es lo que más se falla.
- **Degrada el TIFF de 16→8 bits sin avisar** y sin parámetro para evitarlo.
- Pierde una pista de audio del MKV, igual que ConvertX.
- PDF→imagen a 150 ppp (4,3× más píxeles que ConvertX). Respeta los 192 kbps pedidos.
- Arranque: `initdb` interrumpido dejó el rol creado pero no la base de datos, y **el `pg_isready` que recomienda su propia documentación no lo detecta** — `depends_on: service_healthy` daba luz verde a una BD inservible.
- **No trae `torch` instalado**: sin CUDA por mucho que se pase `--gpus all`. No existe imagen GPU separada; una sola imagen autodetecta.

**Licencia:** AGPL-3.0 salvo `packages/enterprise/` (comercial), con **CLA irrevocable** que concede a la empresa el derecho a redistribuir la contribución *"under any license, including the commercial license we sell"*.

---

### Stirling-PDF · 89,9k ⭐ · MIT con 10 exclusiones · Java

- **Corrección a los metadatos de GitHub**, que reportan `NOASSERTION` y ninguna señal de MCP. Ambas cosas son engañosas.
- El `LICENSE` raíz es MIT seguido de *"Portions of this software are licensed as follows"*, con **10 directorios excluidos**. `app/proprietary/LICENSE` es la "Stirling PDF User License": *"Production use is only permitted with a valid Stirling PDF User License."*
- **Sí tiene servidor MCP completo**, y vive en `app/proprietary/` → **de pago**: `McpToolCatalog`, `McpOperationExecutor`, `DescribeOperationTool`, `McpApiKeyAuthFilter`, `McpConfigValidator`, `McpSecurityConfig`.
- **La idea que merece copiarse:** `McpToolCatalog` no declara herramientas a mano — escanea los beans `RequestMappingHandlerMapping` de Spring y convierte los endpoints REST en herramientas MCP. Solo POST/PUT; GET y DELETE excluidos. Ámbito `mcp.tools.write` y listas de permitidos/bloqueados.
- **El líder del mercado ya monetiza el ángulo MCP.** No es que nadie lo pensara: es que quien lo pensó lo está vendiendo.
- **Cero GPU en 571k líneas de Java.**
- Seguridad: CORS comodín con credenciales y CSRF desactivado por defecto. Y `ProcessExecutor.applicationProperties` es un **campo estático inicializado vacío sin ningún setter en todo el árbol** → toda la configuración de semáforos y timeouts de `settings.yml` se ignora en silencio.

---

### transmute · 1,3k ⭐ · MIT · Python

**La única base viable: licencia permisiva y arquitectura sana.**

- **Registro por auto-descubrimiento** (`registry/registry.py`), no imports hardcodeados:

```python
for _name, obj in inspect.getmembers(converters, inspect.isclass):
    if issubclass(obj, ConverterInterface) and obj is not ConverterInterface:
        if skip_unregisterable and not obj.can_register():
            continue          # el binario no está instalado: no se registra
        self.register_converter(obj)
```

- **`can_register()`**: un conversor cuyo binario falta se auto-excluye. Degradación elegante en vez de fallo en ejecución. Con solo 4 de los ~12 motores presentes en esta máquina, no es un detalle: es requisito.
- **`_get_preferred_converter()`** (`registry.py:209`): resolución **explícita** de preferencia cuando varios motores cubren el mismo par — exactamente lo que ConvertX resuelve por accidente y mal.
- **Un solo salto**, igual que todos: `get_converter_for_conversion(input, output)` devuelve un conversor o nada.
- **El único indicio de encadenamiento de todo el ecosistema**: `converters/libreoffice_convert.py:333` — `# Image output via PDF intermediary`. Resuelto a mano dentro de un adaptador, nunca generalizado.
- **24 conversores con nichos que nadie más tiene**: `fonttools` (fuentes, matriz completa 4×4 ttf/otf/woff/woff2), `pysubs2` (subtítulos, 6×6 con manejo de FPS de MicroDVD), `pandas` (tabulares, 23→17 con `parquet`/`feather`/`orc`/`sqlite`/`dta`/`sav`/`xpt`), `email` (eml/msg → 10 salidas), `ezdxf`, `pkcs7`, `tgs`, `drawio`, `archive`, `cbz`.
- Aporta solo **+0,95 % de pares nuevos**, pero abre **categorías** — que en un grafo valen más que 40 000 pares más de ffmpeg.
- Seguridad: `validate_safe_path` (resolución canónica + raíces permitidas + nombre hexadecimal) es el mejor patrón de confinamiento del conjunto.
- Sin GPU, sin MCP, sin CLI, sin watcher.

---

### gotenberg · 12,9k ⭐ · MIT · Go

- Módulos independientes en `pkg/modules/`: `api`, `chromium`, `exiftool`, `libreoffice`, `pdfcpu`, `pdfengines`, `pdftk`, `prometheus`, `qpdf`, `webhook`. Métricas y asincronía son ciudadanos de primera clase, no añadidos.
- **Mantiene LibreOffice residente** en vez de arrancarlo por petición.
- **La mejor fuente para LibreOffice: 132 extensiones frente a las 41 de ConvertX**, con 55 exclusivas (StarOffice, Lotus, Visio, iWork, UOF, plantillas OpenDocument). Su lista lleva un `// FIXME: don't care` de sus autores y una errata de años: `.fopd` junto a `.fodp`.
- **Declara 8 perfiles PDF/A pero solo 4 son producibles**; `pdfcpu`, `qpdf`, `pdftk` y `exiftool` llevan los cuatro `// Convert is not available in this implementation.`
- **Seguridad — lo mejor del conjunto**: renombrado a UUID (**el nombre del usuario nunca llega a `argv`**, lo que mata la clase entera de bugs de morphos), muerte por grupo de procesos con `Setpgid`, y pool con semáforo y cola acotada.
- **Crítico**: sin autenticación por defecto sobre un endpoint que evalúa JavaScript arbitrario y hace de proxy SSRF con cabeceras controladas.
- Incidencias reales: el clonado con `--depth 1` falló por el límite de rutas de Windows (fichero de prueba en sueco); y devolvía 503 en la ruta LibreOffice por `--libreoffice-start-timeout` de 20 s, que WSL2 supera en frío (21,5 s).
- Verificado con el corpus: CSV con BOM → PDF y HTML → PDF, ambos correctos.

---

### VERT · 15,4k ⭐ · AGPL-3.0 · Svelte

- Convierte **en el navegador** con `@ffmpeg/ffmpeg` (ffmpeg.wasm), `@imagemagick/magick-wasm` y `vert-wasm`.
- **GPU imposible por diseño**: WASM no accede a NVENC ni CUDA.
- Sin LibreOffice ni Calibre: ofimática y ebooks fuera del alcance de WASM.
- 1 commit en 30 días: efectivamente parado.
- **Lección**: local-first no exige el navegador. Un binario nativo da la misma privacidad sin renunciar a la GPU.

---

### morphos · 1,3k ⭐ · MIT · Go

**Inyección de comandos crítica**, verificada en `pkg/files/documents/docx.go:126-130` y `pdf.go:324-328`:

```go
cmdStr := "libreoffice --headless --convert-to pdf:writer_pdf_Export --outdir %s %q"
cmd := exec.Command("bash", "-c", fmt.Sprintf(cmdStr, "/tmp", docxFilename))
```

- Cadena completa: `r.FormFile()` → `fileHeader.Filename` (lo controla quien sube) → `filepath.Base()` → `bash -c`.
- El **`%q` de Go escapa `"` y `\` pero deja pasar `$` y las comillas invertidas**, y bash las expande dentro de comillas dobles. `filepath.Base` quita directorios pero no toca esos caracteres.
- La travesía de directorios sí está bloqueada, pero **por la stdlib de Go, no por código del proyecto** — defensa accidental que cubre medio problema.
- **Abandonado desde 2024-11: no hay mantenedor a quien reportarlo.**

---

## 4.2 Motores de IA

### markitdown · 174,7k ⭐ · MIT

- El repo con más estrellas del ecosistema y el más malinterpretado: **solo convierte *a* Markdown, en un único sentido**. No produce PDF, DOCX ni imágenes. 12,8k líneas: es una capa fina, no un motor.
- **Sin GPU**: extrae texto ya presente. Ante un PDF escaneado no sirve.
- Su `markitdown-mcp` (oficial de Microsoft) expone **una sola herramienta**:

```python
@mcp.tool()
async def convert_to_markdown(uri: str) -> str:
    return MarkItDown(...).convert_uri(uri).markdown
```

- **Medido**: devuelve **85 259–96 419 tokens** para un PDF de 60 páginas (la horquilla es por tokenizador) = **42,6 % de una ventana de 200 K**. A 1 421 tokens/página, **un PDF de 200 páginas no cabe en ninguna ventana de 200 K**.
- `annotations: {}` **vacías** en una herramienta que lee cualquier fichero del disco y abre HTTP arbitrario.
- **Ante un PDF escaneado devuelve cadena vacía con `isError: false`** → el agente concluye que el documento está vacío. El peor tipo de fallo: silencioso y creíble.
- **Sin confinamiento de rutas**: devolvió `C:\Windows\win.ini` por travesía `../../../../` y por ruta absoluta. Intenta cualquier URL http (SSRF). Coherente con su código: `convert_uri(uri)` sin una sola validación.
- Arranque en frío 2,3 s → 55 ms en caliente. 875 issues abiertas.

---

### docling · 65,2k ⭐ · MIT · IBM

- **La abstracción de dispositivo más limpia del conjunto** (`datamodel/accelerator_options.py`): enum `AcceleratorDevice` con `AUTO`, `CPU`, `CUDA`, `cuda:N`, `MPS`, `XPU`, más `cuda_use_flash_attention2` y control de `num_threads`. **Copiar este modelo en FileX.**
- **Medido**: 910 MiB de VRAM. Recuperó el PDF escaneado del corpus —sin capa de texto, inclinado 1,7°, con ruido— con **3 de 3 frases exactas y distancia de edición 0**.
- **Su OCR venía en CPU** (onnxruntime sin proveedor CUDA); solo maquetación y tablas iban a GPU.
- **Bug 2.120.3**: rellena `EngineConfig.paddle.use_cuda` y `EngineConfig.torch.use_cuda` pero **olvida `EngineConfig.onnxruntime.use_cuda`**, que es justo el backend por defecto. Aun con la CUDA EP funcional, seguía haciendo OCR en CPU.
- **La solución al hueco 4**: con RapidOCR y `backend="torch"` hace **OCR en GPU reutilizando el torch ya instalado** — sin `onnxruntime-gpu`, sin `paddlepaddle-gpu`, sin ruedas de runtime CUDA. 3,1× frente a todo-CPU, +1 555 MiB, salida idéntica carácter a carácter.
- GPU en maquetación: **5,6–6,4× en caliente**. Medirlo en frío llevaba a la conclusión contraria.
- Ecosistema completo bajo MIT, cosa rara: `docling-serve` (1,7k, motor como servicio), `docling-mcp` (709), `docling-core`, `docling-parse`, `docling-eval`, y `docling.rs` (port a Rust, 39 ⭐, inmaduro pero revelador).

---

### docling-mcp · 709 ⭐ · MIT

**La mejor referencia MCP del sector**, y también la fuente de tres hallazgos serios.

- Devuelve **clave de caché, no contenido**, con `cleanup_memory()` tras convertir y `ToolAnnotations(readOnlyHint/destructiveHint)` correctas (6 de 19 solo lectura, 2 destructivas).
- **La cifra central: 36 tokens de asa frente a 85 259 del volcado de markitdown = ~2 400×.**
- **Honestidad necesaria**: en documento pequeño el asa **pierde** (32 tokens frente a 56). El asa tiene coste fijo. La regla correcta no es "siempre asa" sino "asa por encima de un umbral". Sobre la misma asa: estructura 2 347 tokens, búsqueda dirigida 556, un ítem 20, recorte 871.
- **Devuelve la misma carga en `content` *y* `structured_content`** (85 473 + 85 469 tokens): un cliente que reenvíe ambos paga el doble.
- **19 herramientas y 5 280 tokens de suelo fijo** por defecto, con once nombres acabados en `…_docling_document`. Limitándolo al grupo `conversion`: **880 tokens y 3 herramientas (−83 %)**, y el arranque baja de 6,0 a 1,8 s.
- **Una clave de caché inválida devuelve la lista completa de claves vivas del proceso** — y con esas claves se vuelca cualquier documento de otra tarea. Fuga de información entre tareas. **Hay mantenedor activo (IBM): reportable.**
- **Ante un `.mkv` responde al modelo `pip install openai-whisper`**: el `stderr` del motor convertido literalmente en la siguiente acción del agente.
- Instancia `LocalDocumentConverter()` **en cada llamada** (~2 s de reconstrucción del pipeline) y su `cleanup_memory()` es solo `gc.collect()`: no libera VRAM ni mantiene el motor caliente. Lo peor de ambos mundos.
- No funciona en local recién instalado: `conversion_mode=remote`, `fallback_to_local=false`.
- **`mcp>=2.0.0` frente al `mcp~=1.8.0` de markitdown: los dos servidores no caben en el mismo entorno virtual**, y negocian versiones distintas del protocolo (2025-11-25 frente a 2024-11-05).
- Rutas: **convenciones exactamente opuestas a markitdown** — lo único que markitdown acepta (`file://`) es lo único que docling rechaza. Docling sí bloquea URLs http.

---

### surya · 21,3k ⭐ · Apache-2.0

- **Ya no es un modelo PyTorch en proceso.** `surya/inference/backends/vllm.py:1`: *"vllm backend: spawns the vllm/vllm-openai docker image with MTP=2"*. `settings.py:96`: `VLLM_DOCKER_IMAGE = "vllm/vllm-openai:v0.20.1"`. `settings.py:104`: `VLLM_GPU_MEMORY_UTILIZATION = 0.85` → **10 445 MiB reservados de los ~9 700 libres**.
- Se cuelga sin excepción ni traza. **VRAM: sin dato.**
- **`pip install surya-ocr` degradó torch de `2.6.0+cu124` a `2.13.0+cpu` sin un solo error.** Todo habría corrido en CPU en silencio.
- Su `VLLM_DTYPE = "bfloat16"` exige compute capability ≥ 8.0 (`settings.py:100-102`); la 3060 es 8.6 y cumpliría, si arrancase.

### marker · 38,9k ⭐ · Apache-2.0

- Hereda el bloqueo: fija surya 0.22.x y `torch>=2.7.0`. Descartado tras leer sus metadatos, sin instalarlo.

---

### faster-whisper · 25k ⭐ · MIT

- 4k líneas: envoltorio delgado y bien hecho sobre CTranslate2.
- **VRAM medida**: `large-v3` **4 525 MiB de pico de inferencia** (no los 3 082 cargado — hay que presupuestar por el pico); `distil-large-v3` 1 847 MiB.
- **`distil-large-v3` empata con `large-v3` (WER 0,00 %)** en clips de 11 s, incluso con ruido blanco añadido y en banda telefónica de 8 kHz.
- **Pero en 308 s produce 4,4–4,6 % de WER**: duplica y se salta fragmentos en las costuras de las ventanas de 30 s, devolviendo 29 arranques de frase donde había 28. `large-v3` clava 28/28 en ambas condiciones.
- **Regla para FileX: `distil-large-v3` hasta 30 s, `large-v3` por encima.** Ahorra 2 678 MiB en el caso corto sin perder nada.
- **Alucina sobre audio sin voz**: devolvió `Thanks for watching!` sobre un tono puro. El delator es `language_probability`: **0,35–0,37 en audio no hablado frente a 0,91–0,97 en voz real**. Sin ese filtro, FileX generaría subtítulos inventados.
- Transcribió voz real sin un solo error.

---

### MinerU · 78k ⭐ · Apache-2.0 con términos adicionales

- El `NOASSERTION` de GitHub resuelto leyendo `LICENSE.md`: Apache-2.0 más tres términos — licencia comercial obligatoria solo por encima de **100 millones de usuarios activos mensuales o 20 millones de USD de ingresos mensuales** (irrelevante), **atribución obligatoria** si se ofrece un servicio online, y terminación automática si se incumple.
- **Riesgo legal descartado. El inconveniente real es el peso**: 71,6k líneas y una pila de modelos pesada frente a Docling (modular, con `docling-serve` listo) o Marker (16,5k líneas).
- **Recomendación: no incluirlo en la primera versión.** Reservarlo como motor de máxima calidad para documentos científicos.

---

### OCRmyPDF · 34,5k ⭐ · MPL-2.0

- **Cero CUDA en 41k líneas**: delega en Tesseract, CPU pura.
- Su valor no es el OCR sino **todo lo que lo rodea**: rotación automática, corrección de inclinación, eliminación de ruido, optimización del PDF resultante y preservación del original. Es justo el preprocesado que exige el caso patológico del corpus.
- MPL-2.0 es copyleft *por fichero*: combinable con código propietario publicando solo los ficheros MPL modificados.

---

## 4.3 Referencias MCP

### kordoc · 1,7k ⭐ · MIT

- **La forma exacta de FileX**: `src/cli.ts` (1 205 líneas) y `src/mcp.ts` (1 177) en la misma base de código, ambos importando el núcleo compartido desde `./index.js`.
- **La capa MCP no duplica lógica.** Su volumen son tres cosas que la CLI no necesita: 87 declaraciones de esquema zod (cada parámetro descrito en lenguaje natural, porque quien lee es un modelo), saneado de rutas (`realpathSync`, `isAbsolute`) y clasificación de errores (`sanitizeError`, `classifyError`, `KordocError`).
- **Estimación para FileX: presupuestar la capa MCP como trabajo comparable al de la CLI**, no como un envoltorio de una tarde.

### Los cuatro MCP de conversión existentes

| Repo | ⭐ | Líneas | Qué hace |
|---|---:|---:|---|
| `KorigamiK/markitdown_mcp_server` | 86 | 162 | ⚠️ Servidor de **prompts**, no de herramientas |
| `misbahsy/video-audio-mcp` | 84 | 2 494 | FFmpeg vía MCP, sin GPU |
| `kevinwatt/ffmpeg-mcp-lite` | 26 | 1 204 | Convertir, comprimir, recortar, subtítulos |
| `BoomLinkAi/image-worker-mcp` | 18 | 3 400 | Redimensionar y optimizar con sharp |

**Ninguno usa GPU. Ninguno pasa de 3 400 líneas.** Compárese con los 174 667 ⭐ de MarkItDown: la demanda de conversión es enorme y la oferta vía MCP es testimonial.

### modelcontextprotocol/servers · 89,7k ⭐

Implementaciones oficiales de referencia. **No hay ni un servidor de conversión de ficheros entre ellas.**

---

## 5. Mediciones en la máquina real

### 5.1 NVENC — medianas de 9 ejecuciones en entorno tranquilo

| Caso | CPU | GPU | Aceleración |
|---|---:|---:|---:|
| **1080p HEVC** `medium` vs `p4` | 16 598 ms | 1 978 ms | **8,39×** |
| 1080p H.264, transcode real vídeo+audio | 5 248 ms | 1 762 ms | 2,98× |
| 1080p H.264 `medium` vs `p4` | 5 407 ms | 1 973 ms | 2,74× |
| 4K H.264 `medium` vs `p4` | 11 427 ms | 4 286 ms | 2,67× |
| 720p patológico, 2 pistas de audio | 1 358 ms | 628 ms | 2,16× |

- **`av1_nvenc` falla con `No capable devices found`** pese a aparecer en `ffmpeg -encoders`: Ampere tiene decodificador AV1 (`av1_cuvid`) pero **no codificador**. → **Sondear capacidades en ejecución, nunca deducirlas del binario.**
- **HEVC es donde la GPU se paga sola**: `hevc_nvenc` cuesta lo mismo que `h264_nvenc`, mientras `libx265` es 3× más lento que `libx264`.
- **La tubería GPU completa no sirve**: `-hwaccel cuda -hwaccel_output_format cuda` da entre −13 % y +3 % (dentro del ruido), y **con escalado es un 34 % peor**.

### 5.2 El coste que casi nadie mide: NVENC no respeta el bitrate

| Codificador | Objetivo | Bitrate real | Desvío | VMAF |
|---|---:|---:|---:|---:|
| libx264 medium | 2M | 2 026 | +1,3 % | 89,70 |
| h264_nvenc p4 | 2M | 2 214 | **+10,7 %** | 88,71 |
| h264_nvenc p7 | 2M | 2 161 | +8,0 % | 89,22 |
| libx264 medium | 10M | 10 023 | +0,2 % | 98,87 |
| h264_nvenc p4 | 10M | 10 785 | **+7,9 %** | 98,55 |

La pérdida de calidad es mínima (<1 punto de VMAF), pero **el fichero sale un 8–11 % más grande de lo pedido**. Si el usuario dice "comprime a 2 Mbps", eso importa: **el grafo debe contabilizarlo como coste de arista**.

### 5.3 Arranque en frío — 25 ejecuciones tras calentamiento

| Proceso | Tiempo | Sobre el suelo |
|---|---:|---:|
| `cmd /c exit` (suelo de Windows) | 49 ms | — |
| Go, binario compilado | **41 ms** | ~0 |
| Python, intérprete desnudo | 60 ms | +19 ms |
| Node.js | 74 ms | +33 ms |
| Python + stdlib | 85 ms | +44 ms |
| `ffmpeg -version` (solo arrancar) | 61 ms | +20 ms |
| `magick` con un PNG 64×64 | 73 ms | +32 ms |

**Interpretación que corrige la intuición habitual:**

1. En Windows, crear un proceso cuesta **~49 ms haga lo que haga**. Es el suelo, independiente del lenguaje.
2. Elegir Go en vez de Python ahorra **~44 ms** por invocación. Real, pero modesto.
3. **Cualquier conversión arranca además un motor externo**: ffmpeg cuesta 61 ms solo en existir.
4. **Para el servidor MCP el arranque en frío es irrelevante**: el proceso arranca una vez y permanece vivo.

→ El lenguaje del núcleo controla ~40 ms de una invocación de 100–160 ms, **y solo en la CLI**. El argumento "Rust por el arranque" queda muy debilitado.

*(Nota metodológica: sin calentamiento, Windows Defender inflaba el binario Go recién compilado de 41 a 110 ms. Y una primera tanda NVENC que coincidió con una descarga dio una mediana de 14 513 ms frente a los 1 973 reales: **error de 7,4×**. Medir con ruido no es medir.)*

### 5.4 Presupuesto de VRAM — RTX 3060, 12 288 MiB

| Componente | Pico de inferencia |
|---|---:|
| faster-whisper `large-v3` (fp16) | 4 525 MiB |
| faster-whisper `distil-large-v3` | 1 847 MiB |
| docling (maquetación y tablas) | 910 MiB |
| RapidOCR en GPU | +1 344 MiB |
| NVENC 4K | 743 MiB |
| NVENC 1080p | 209 MiB |

- **Disponible para FileX: ~8,7 GB** (el escritorio ocupa ~2,5 GB de forma permanente).
- Perfil completo conviviendo (whisper `large-v3` + docling con OCR-GPU + NVENC): **pico de 7 702 MiB, 4 586 libres**, sin degradación del OCR.
- **No caben dos `large-v3`** (9,1 GB). Con inferencia concurrente, whisper baja de 2,8× a 2,3× tiempo real: degrada, no falla.

### 5.5 OCR en GPU — los tres candidatos

| Motor | Aceleración GPU | VRAM | CER dificultad 2 | CER dificultad 3 |
|---|---:|---:|---:|---:|
| **RapidOCR `backend=torch`** | 3,5–4,2× | +1 344 MiB | 1,3 % | 65,8 % |
| PaddleOCR | 8,9–11,7× | +1 486 MiB | **0,0 %** | 75,9 % |
| EasyOCR | 12,4–17,0× | +2 079 MiB | 43,0 % | 57,0 % |

- **Los múltiplos grandes engañan.** RapidOCR "solo" gana 3,5× porque **su ruta CPU ya es la más rápida** (763 ms frente a los 6 660 ms de EasyOCR). Mejor-CPU contra mejor-GPU, la ganancia real es **3,9×, no 17×**.
- **Elección: RapidOCR con `backend="torch"`** — coste de infraestructura GPU **cero** y salida idéntica a la de CPU. PaddleOCR queda como ruta opcional de máxima precisión (3,73 GB, venv aislado, 24,8 s de carga). **EasyOCR descartado**: peor precisión y **no determinista entre CPU y GPU** en entradas degradadas.
- **En la dificultad 3 fallan los tres** (57–76 % de CER). El OCR acelerado resuelve documentos degradados, no destruidos.

### 5.6 MCP — el coste en contexto

| Métrica | markitdown-mcp | docling-mcp |
|---|---:|---:|
| Tokens devueltos (PDF de 60 páginas) | **85 259** | **36** |
| Porcentaje de una ventana de 200 K | 42,6 % | 0,02 % |
| Documento pequeño | 56 | 32 |
| Herramientas expuestas | 1 (79 tokens) | 19 (5 280 tokens) |
| Herramientas con el grupo `conversion` | — | 3 (880 tokens) |
| Arranque en frío → caliente | 2,3 s → 55 ms | 13,3 s → 2,0 s |
| Anotaciones `readOnly`/`destructive` | ❌ vacías | ✅ 6 y 2 |
| Confina rutas | ❌ devolvió `win.ini` | ⚠️ solo por formato |
| Bloquea URLs http | ❌ SSRF | ✅ |

### 5.7 Cara a cara: SnapOtter frente a ConvertX (96 conversiones reales)

| Prueba | SnapOtter | ConvertX |
|---|---|---|
| Cobertura de la matriz | **18/19** | 15/19 |
| `png→avif` | ✅ AVIF real, 3 137 B | ❌ **PNG renombrado, 42 855 B** |
| MKV con 2 pistas de audio | ❌ pierde una, en silencio | ❌ pierde una, en silencio |
| TIFF 16 bits, 72 MB | ❌ degrada a 8 bits sin avisar | ✅ **conserva los 16 bits** |
| CSV con BOM y comillas | ✅ impecable, consume el BOM | ❌ imposible: `dasel` roto |
| Hojas de cálculo | ✅ sí | ⚠️ funciona, pero no lo ofrece |
| PDF→imagen | ✅ 150 ppp | ⚠️ 72 ppp fijos |
| Audio a 192 kbps | ✅ respeta lo pedido | ❌ entrega 64 kbps |
| OOM con 72 MB | ✅ aguantó | ✅ aguantó |

> **Advertencia sobre los tiempos:** la VM de Docker tiene **2 vCPU y 1,9 GiB** (decisión deliberada del usuario en su `.wslconfig`). Los tiempos **solo valen para comparar un competidor con el otro**, nunca contra los nativos. La dispersión llega a **9,2×** en la misma conversión y el arranque en frío domina hasta **53×**, así que toda diferencia menor de ~2× es ruido.

### 5.8 Referencia nativa — el patrón oro

39 conversiones con ffmpeg, ImageMagick y Ghostscript nativos, con **46 reglas de regresión** y **17 pérdidas catalogadas** en `bench/salidas-referencia/referencia.json`.

- **`ffmpeg -i entrada.mkv salida.mp4` descarta la segunda pista de audio en silencio.** Con `-map 0` salen las dos; con `-map 0 -c copy`, bit a bit idénticas. **MP4 admite varias pistas: es fallo de uso, no del formato.** Los dos competidores caen exactamente en él.
- **El TIFF de 16 bits NO pierde profundidad al pasar a PNG**: ImageMagick conserva los 16 bits, RMSE 0, los 11 935 622 colores únicos intactos. Un competidor que entregue 8 bits comete un fallo cuantificable (PSNR 59,0 dB, 9,8 millones de tonos descartados).
- **AVIF con pérdida degrada el canal alfa** (46,0 dB) y convierte un alfa 100 % opaco en 0,9939–0,9998; **WebP con pérdida lo deja exacto**.
- **ImageMagick aplana la transparencia sobre negro**, no sobre blanco. Que JPEG pierda el alfa es inevitable; que el fondo salga negro no lo es.
- Ghostscript `pdfwrite` conserva el texto con sha256 idéntico; rasterizar lo destruye (180 → 0 caracteres).

**Cuatro trampas de diseño de pruebas, tan valiosas como los resultados:**

1. **El "alfa trivial" falsea la prueba.** `tipico.png` declara canal alfa pero es enteramente opaco. La regla correcta solo exige conservación si `min(alfa) < 1,0`.
2. **Menor tamaño ≠ mejor conversión.** El GIF con paleta genérica pesa un 35 % **menos** que el bueno.
3. **Opus fuerza 48 kHz** y convierte 8,000 s en 8,0065 s: toda tolerancia por debajo de ±10 ms marca como fallo una conversión correcta.
4. **`txtwrite` emite basura de 1–3 caracteres** en PDF sin texto real: el umbral debe ser ≥10 caracteres, no >0.

*(Aviso de instrumentación: `magick compare -metric SSIM` devuelve **0 para imágenes idénticas** en esta build — se comporta como disimilitud. Todas las cifras se apoyan en PSNR y RMSE.)*

---

## 6. Auditoría de seguridad

### 6.1 Comparativa por dimensión

| Repo | Sin shell | Saneado de rutas | Límites de recursos | Aislamiento | `policy.xml` propio | Auth por defecto |
|---|---|---|---|---|---|---|
| gotenberg | ✅ | ✅ **UUID** | ✅ pool + cola | ✅ `Setpgid` | ❌ | ❌ **crítico** |
| transmute | ✅ | ✅ `validate_safe_path` | ⚠️ | ⚠️ | ❌ | ⚠️ |
| ConvertX | ✅ `execFile` | ⚠️ | ⚠️ lotes, default 0 | ❌ | ❌ | ⚠️ |
| SnapOtter | ✅ | ⚠️ | ⚠️ 6 topes con default 0 | ✅ `-dSAFER` | ❌ **lo debilita** | ✅ |
| Stirling-PDF | ✅ | ⚠️ | ❌ **config ignorada** | ⚠️ | ❌ **lo debilita** | ❌ **crítico** |
| morphos | ❌ **`bash -c`** | ⚠️ accidental | ❌ | ❌ | ❌ | ❌ |

### 6.2 Los tres patrones sistémicos

1. **La invocación sin shell está resuelta; la configuración de ImageMagick no la aprueba nadie.** Cinco de seis usan array de argumentos, pero **ninguno distribuye un `policy.xml` propio**, y dos (Stirling-PDF y SnapOtter) **lo debilitan por `sed`** reabriendo PDF/PS/EPS hacia el delegado Ghostscript, sin añadir límites a cambio.
2. **El fallo dominante no es "faltan límites" sino "los límites existen y valen cero".** SnapOtter: seis topes con default `0`. ConvertX: `MAX_CONVERT_PROCESS=0` documentado como "unlimited". Stirling-PDF: campo estático sin setter → toda la configuración se ignora en silencio. **Un límite que parece configurado y no lo está es peor que no tenerlo.**
3. **Lo que ya resolvieron bien vale más que sus fallos.** 16 patrones a copiar, encabezados por el renombrado a UUID de gotenberg.

### 6.3 Lo que FileX tiene que inventar

**Ninguno de los seis recibe una ruta del sistema de ficheros**: todos reciben una subida HTTP y escriben ellos el fichero. **FileX recibirá rutas arbitrarias de un LLM.** La lista blanca de raíces —denegar por defecto, resolución canónica, y error indistinguible entre "prohibido" y "no existe" para no ser un oráculo de existencia— hay que diseñarla desde cero.

**Tres hallazgos cambian de gravedad con un llamante no humano:**

- Que el llamante elija motor pasa de rareza a **vector directo**.
- La sobrescritura deja de ser trivial: **un agente que reintenta es el caso normal**.
- Las trazas de pila dejan de ser solo fuga de información: **el `stderr` crudo entra en el contexto del agente y puede dirigir su siguiente acción**. Observado en vivo: docling-mcp respondió `pip install openai-whisper` al modelo.

---

## 7. Decisión de arquitectura

### 7.1 Desde cero o sobre una base

**Híbrido asimétrico: núcleo propio, todo lo demás reutilizado.**

| Candidato | Por qué no como base |
|---|---|
| SnapOtter | AGPL + CLA + `packages/enterprise` propietario. 100+ commits/mes hacen insostenible un fork en solitario. Es UI-first; FileX es agent-first |
| ConvertX | AGPL. Y su despacho es justo lo que hay que rehacer |
| Stirling-PDF | Solo PDF, Java, MCP de pago |
| VERT / morphos | Parados o abandonados |
| gotenberg | No es un conversor universal: es una dependencia excelente |
| **transmute** | **El único viable (MIT), pero es una API web sin CLI, sin MCP, sin watcher y sin GPU** |

De transmute se toma su **núcleo conceptual**, probado y permisivo: el registro por reflexión con `can_register()`, la `ConverterInterface`, y los adaptadores de nicho. Lo que hay que escribir de cero es precisamente lo que **nadie tiene**.

### 7.2 Lenguaje: Python primero, con el sidecar desde el día 1

```
filex (CLI / MCP / watcher / API)      <- Python, proceso único y persistente
  |
  +-- registro + grafo de conversión   <- el núcleo propio
  |
  +-- motores externos                 <- execFile: ffmpeg, magick, soffice, pandoc...
  |
  +-- sidecar IA                       <- proceso Python aparte, modelos en VRAM
        docling + RapidOCR(torch) / faster-whisper
```

1. **El ecosistema que importa es Python**: Docling, RapidOCR, faster-whisper, PyMuPDF, Pillow, DuckDB. Todo el hueco 4 vive ahí.
2. **La base reutilizable (transmute) ya es Python** y es MIT.
3. **El sidecar separado no es opcional en ningún lenguaje**: SnapOtter lo aisla porque *"torch/CUDA reserve huge virtual space"*.
4. **La deuda es acotada**: si molesta el arranque de la CLI, se reescribe el despachador —unos cientos de líneas— en Go, dejando intactos sidecar y adaptadores.

*De los siete orquestadores analizados, **ninguno** es Rust (dos Go, dos TypeScript, uno Python, uno Java, uno Svelte): reutilizar código y elegir Rust tiran en direcciones opuestas.*

### 7.3 Reglas de diseño derivadas de la evidencia

| Regla | Evidencia |
|---|---|
| **Grafo dirigido con coste por arista** y Dijkstra | 2,93× de cobertura; resuelve de paso el bug de prioridad de ConvertX |
| **Contrato de verificación obligatorio tras cada conversión** | Habría atrapado el `.avif`-que-era-PNG, la pista perdida y las degradaciones de bits/ppp/bitrate |
| **Un recurso alternativo sin verificación es peor que no tenerlo** | Convierte un fallo honesto en uno silencioso: literalmente lo que le pasa a ImageMagick dentro de ConvertX |
| **Registro por reflexión con `can_register()`** | Solo 4 de ~12 motores presentes en esta máquina |
| **Sondear capacidades en ejecución, no deducirlas** | `av1_nvenc` aparece listado y no funciona |
| **Verificar `torch.cuda.is_available()` en cada arranque** | `pip install surya-ocr` tumbó CUDA sin un solo error |
| **Comprobar `session.get_providers()`, no `get_device()`** | onnxruntime dice `'GPU'` mientras corre en CPU |
| **Catálogo MCP generado desde el registro** | Patrón de `McpToolCatalog` de Stirling-PDF |
| **MCP devuelve ruta y metadatos, nunca contenido** | ~2 400× de diferencia en tokens |
| **Pocas herramientas MCP, bien nombradas** | 19 herramientas = 5 280 tokens de suelo; 3 = 880 |
| **Registro LRU de modelos acotado por VRAM + TTL** | SnapOtter no gestiona VRAM en absoluto |
| **Filtrar por `language_probability`** | Whisper alucina `Thanks for watching!` sobre un tono puro |
| **Lista blanca de raíces, denegar por defecto** | Ninguno de los seis lo resuelve; markitdown devolvió `win.ini` |
| **Distinguir pérdida inevitable de fallo del motor** | 17 pérdidas catalogadas en la referencia nativa |

### 7.4 Orden de construcción

1. **Registro, grafo y CLI** con FFmpeg e ImageMagick — **75 % de la cobertura de formatos con dos motores**.
2. **NVENC** con sondeo de capacidades y degradación a CPU. 8,4× en HEVC, coste casi nulo.
3. **Contrato de verificación post-conversión.** Sin él, todo lo anterior puede mentir.
4. **Capa MCP generada desde el registro**, devolviendo ruta y metadatos.
5. **Gotenberg en Docker** para ofimática→PDF, evitando instalar LibreOffice en Windows.
6. **Sidecar IA**: faster-whisper (`distil` ≤30 s, `large-v3` por encima) y Docling con RapidOCR en `backend="torch"`.
7. **Watcher y API HTTP local**, superficies delgadas sobre el mismo núcleo.

Los pasos 1 y 2 ya superan en cobertura y velocidad a todo lo analizado, salvo en OCR y ofimática.

---

## 8. Material de respaldo

| Ruta | Contenido |
|---|---|
| `informe-filex.html` | Informe navegable (publicado como Artifact) |
| **`RESULTADOS-MCP.md`** | **Resultados de los 6 repos de `mcp-refs/`** (sustituye a `PRUEBAS-MCP-REFS.md`): el caso binario, los catálogos medidos, las 15 reglas de confinamiento, y **7 correcciones a este documento y a `PLAN-ORQUESTADOR.md`** |
| `analysis/00-mcp-componentes.md` | 90 componentes MCP → veredicto, con `fichero:línea` |
| `bench/mcp-refs-multimedia.md` | El caso binario ejecutado: qué devuelve un MCP tras convertir |
| `bench/mcp-refs-confinamiento.md` | Ataques de ruta, oráculo de existencia, TOCTOU, y las 15 reglas |
| `analysis/` | 24 documentos: uno por repositorio más 6 transversales |
| `analysis/00-seguridad.md` | Auditoría de los 6 orquestadores (911 líneas) |
| `analysis/00-sidecar-protocolo.md` | Disección del sidecar de SnapOtter (425 líneas) |
| `analysis/00-matriz-formatos.md` y `-ampliada.md` | Matrices extraídas del código |
| `analysis/00-hueco-multisalto.md` | El cálculo del grafo |
| `analysis/00-mcp-patrones.md`, `00-gpu.md`, `00-licencias.md`, `00-decision-filex.md` | Transversales |
| `bench/results.md` | Arranque en frío y primeras mediciones |
| `bench/gpu-fase1.md` | NVENC, VRAM, whisper, docling |
| `bench/gpu-fase2.md` | Los tres motores de OCR y el umbral de whisper |
| `bench/competidores.md` | Cara a cara, 96 conversiones |
| `bench/referencia-nativa.md` | Patrón oro y 46 reglas de regresión |
| `bench/mcp-ergonomia.md` | Coste en contexto y 16 reglas MCP |
| `bench/docker.md` | Entorno de los competidores |
| `bench/lib/harness.sh` | Arnés de medición con lock de GPU y etiquetado limpia/SUCIA |
| `repos/` | 22 repositorios clonados (2,2 GB) |
| `corpus/` | 20 ficheros de prueba, incluidas 3 variantes duras de OCR |
| `.venv-ai/`, `.venv-paddle/`, `.venv-mcp-md/` | Entornos CUDA funcionales |
| `docker/` | Compose de SnapOtter (CPU y GPU), ConvertX y gotenberg |
| `.mcp.json` | Configuración MCP **de proyecto** (no global) |

---

## 9. Cambios de estado en la máquina

- **Contraseña de SnapOtter cambiada** de `admin` a `<CONTRASENA-REDACTADA>`. Era obligatorio: devolvía `403 MUST_CHANGE_PASSWORD` en toda su API.
- Cinco contenedores Docker levantados: SnapOtter (1349), ConvertX (3100), Gotenberg (3200), más Postgres y Redis de SnapOtter.
- Tres entornos virtuales creados en el proyecto. Ninguna instalación global.
- `.mcp.json` de proyecto creado. **La configuración global de Claude Code no se tocó** (0 menciones).
- Consumo de disco: ~2,2 GB de repos, ~20,6 GB de imágenes Docker (en **C:**, no en D:), ~10 GB de entornos y modelos.
