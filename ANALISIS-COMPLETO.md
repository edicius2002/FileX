# FileX — Análisis completo del ecosistema de conversión de archivos

> ### Qué es este documento, si llegas de fuera
>
> **El estudio de campo del que salió FileX.** 22 proyectos de conversión de ficheros
> clonados, **leídos a nivel de código y ejecutados** contra un corpus de casos patológicos,
> con el veredicto por repositorio: licencia, arquitectura, seguridad, qué se le puede
> copiar y qué no. La conclusión —dónde está el hueco y si merece la pena construir— vive en
> [`HUECOS.md`](HUECOS.md); qué es FileX, en [`README.md`](README.md).
>
> Sirve a quien quiera **decidir si construir, adoptar o descartar** en este espacio, y a
> quien quiera evaluar esos 22 proyectos sin repetir el trabajo.
>
> **Convención:** el repositorio marca cada afirmación **MEDIDO** o **PENDIENTE**. **Este
> documento es anterior a que esa disciplina se aplicara de forma sistemática**, así que
> muchas de sus cifras van sin marca; lo que las respalda es la regla de la nota de abajo
> —nada sale de un README ni de metadatos de GitHub—. **Para las cifras vigentes y marcadas,
> con su `n` y su informe de origen, ve a [`BENCHMARKS.md`](BENCHMARKS.md).**
>
> **Dos cosas que este documento nombra y que NO están en el repositorio publicado:**
> `repos/` (los 22 clones de terceros, en `.gitignore`: conservan sus propias licencias y no
> se redistribuyen) y los entornos virtuales `.venv-*` de la máquina de referencia.
>
> **No se ha actualizado con las mediciones posteriores al 21/08/2026.** Donde una cifra de
> aquí y una de `bench/` no coincidan, **manda la de `bench/`**.

**Fecha:** 19 de agosto de 2026
**Alcance:** 22 repositorios clonados y auditados a nivel de código, ejecutados en la máquina real
**Hardware:** RTX 3060 12 GB (compute capability 8.6, driver 572.61) · Windows 10 · 12 núcleos · Docker 29.4.3 + WSL2 · Python 3.11.9

> Todas las cifras proceden de código clonado o de comandos ejecutados en esta máquina. **Ninguna procede de README ni de metadatos de GitHub.** Donde ambos discrepaban, se indica explícitamente.
>
> **Revisado el 21 de agosto de 2026.** Cinco afirmaciones de este documento quedaron desmentidas por mediciones posteriores y **están corregidas en su sitio, diciendo qué se creía y qué se midió**: el multiplicador del grafo (§1, §3.4), las marcas de OCR de dificultad 2 y 3 (§5.5), OCRmyPDF como preprocesador (§2.2, §4.2), la licencia de `modelcontextprotocol/servers` (§3.2, §4.3) y «la lista blanca hay que diseñarla desde cero» (§6.3). **Ninguna cifra original se ha borrado.**

---

## 1. Resumen ejecutivo

El ecosistema está **partido en dos mitades que nadie ha unido**:

- Los **orquestadores de conversión** con tracción (Stirling-PDF 89,9k ⭐, ConvertX 18,5k, VERT 15,4k) **no usan la GPU, no exponen MCP y no encadenan conversiones**.
- Los **motores de IA documental** (Docling, MinerU, Surya, Marker, faster-whisper) **son GPU-nativos pero no convierten un MP4 ni redimensionan un PNG**.

### Los cinco diferenciadores, reevaluados tras ejecutar

> La lista original de cuatro huecos se formó con **metadatos de GitHub y lectura de código**. La fase de ejecución la desmintió parcialmente: **dos se debilitaron, uno hubo que reformularlo, y el más fuerte no estaba en la lista**. El detalle completo, con la separación entre lo medido y lo pendiente, está en **`HUECOS.md`**.

| # | Diferenciador | Evidencia | Estado |
|---:|---|---|---|
| **1** | **Verificación obligatoria de la salida** | **8 fallos independientes en 7 proyectos**: un `.avif` que es PNG entregado con estado "Done"; pérdida silenciosa de pista de audio en **los dos** competidores; degradación 16→8 bits sin avisar; cadena vacía con `isError: false`; **y un PNG perfecto sin una sola letra** (`resvg`) | ✅ **Medido. El más fuerte** · ⚠️ **con su frontera medida: el octavo NO lo atrapa el contrato de cuatro puntos** (§5.5) · ✅ **la regla I9 sí lo atrapa, 6/6** · ⚠️ **pero `resvg` era una FAMILIA de cinco miembros y uno sigue descubierto** (§5.5) |
| **2** | Grafo con **coste por arista** | 0 de 7 orquestadores hacen búsqueda de camino. ConvertX elige mal el motor (`png→jpg` acaba en ffmpeg teniendo vips disponible) | ✅ Medido en su parte de **selección** · ❌ **el multi-salto, REFUTADO al ejecutarlo** (ver abajo) · ✅ **la tasa de aristas nominales, MEDIDA: 50,5 % global, pero 3,0 % en el estrato PDF** (§3.4) · ✅ **y acotada: el 18,8 % de ese 50,5 % era invocación → 41,0 % real, con 3 226 aristas de ganancia automática** (§3.4) |
| **3** | MCP **multi-modal en un solo servidor** | Los servidores no coexisten (`mcp~=1.8.0` frente a `mcp>=2.0.0`). ~2 400× de diferencia en tokens entre patrones | ✅ Medido · ✅ **caso binario resuelto (20/08)** · ✅ **saturación del catálogo resuelta (21/08) y REFUTADA: 27 herramientas eligieron mejor que 8** |
| **4** | NVENC en vídeo | Ningún orquestador lo usa. **8,39× en HEVC**, n=9. Pero se pasa un 8–11 % del bitrate pedido | ✅ Medido · ⏳ **rendimiento en lote sin probar** |
| **5** | OCR en GPU | Todos lo hacen en CPU. Resuelto con Docling + RapidOCR `backend="torch"`, **coste de infraestructura cero** | ⚠️ **Degradado: ya no es foso** · 🔁 **reabierto: las marcas de d2/d3 eran un artefacto del arnés** (§5.5) |

**Los tres criterios de juicio:** ¿nadie lo hace? ¿es barato? ¿lo nota el usuario? **Solo el nº 1 cumple los tres.** El OCR es replicable en una tarde, el patrón MCP ya lo implementa bien IBM, NVENC solo importa en lote, y el grafo amplía alcance sin garantizar corrección.

> **Corrección al diferenciador nº 2 — MEDIDA el 21/08/2026 (`bench/fidelidad-caminos.md`, 69 caminos ejecutados).** Se daba por «real, pero reformulado». **Los datos refutan el multi-salto:**
>
> | Categoría | Multi-salto (n=47) | 1 salto (n=22) |
> |---|---:|---:|
> | ÍNTEGRO | 10,6 % | 50,0 % |
> | PÉRDIDA INEVITABLE | 21,3 % | 4,5 % |
> | DEGRADADO | 38,3 % | 22,7 % |
> | **DESTRUIDO** | **17,0 %** | 9,1 % |
> | FALLO | 12,8 % | 13,6 % |
>
> **Aceptable: 31,9 % en multi-salto frente a 54,5 % en un salto.** Y el 2,93× se deshace en cuatro pasos: **(1)** con los motores instalados aquí cae a **1,93×**; **(2)** de los 128 426 pares nuevos solo **610 (0,48 %)** son plausibles → la ganancia honesta es **+32,7 %, no +193 %**; **(3)** **820 de los 1 599 pares «pedidos» tienen PDF como único intermedio** —el multi-salto aquí es «pásalo por PDF»—; **(4)** `epub→png`, `epub→docx` y `tex→docx` **no se pueden ejecutar**. El estrato que mejor puntúa (documento→imagen, 7/8) **aprueba solo porque el destino es una imagen y perder el texto es «inevitable» por definición**: funciona mejor donde menos sirve.
>
> **Lo que se sostiene es la selección correcta con coste explícito**, que arregla por construcción el bug de despacho de ConvertX y se cobra en el primer salto. El multi-salto era la propina; ahora sabemos que la propina es **pequeña y arriesgada**. *(`HUECOS.md` §2 ya lo sospechaba sin datos —«el número lo sobrevende»—: la sospecha era correcta y ahora está medida.)*

**El argumento de FileX**, en consecuencia, no es *"convierte más cosas más rápido"* —discutible y en parte replicable— sino:

> **Es el único que garantiza que lo que te entrega es lo que pediste.**

### Qué queda pendiente de medir

| Pendiente | Afecta a | Especificado en |
|---|---|---|
| ~~Fracción de los 447 398 caminos con fidelidad aceptable~~ · **RESUELTO 21/08: 31,9 % en multi-salto** | Difer. 2 | `bench/fidelidad-caminos.md` |
| ~~Cuántas de las 138 501 aristas del grafo son **nominales**~~ · **RESUELTO 21/08: el 50,5 % de las verificables NO existe**, IC 95 % [48,2–53,0]. **Pero la tasa no es uniforme (factor 18) y el estrato PDF —el que usa el multi-salto— sale al 3,0 %** | Difer. 2 | **`bench/aristas-nominales.md`** |
| **El 54,78 % de aristas indeterminadas**: exige un corpus de 445 formatos que ningún motor local escribe (corpus FATE de ffmpeg). Es lo único que convierte el escenario central (48,6 %) en un número medido | Difer. 2 | ídem §7, §11 |
| ~~**Cuánto de ese 50,5 % se recupera con una invocación mejor**~~ · **RESUELTO 21/08 (14:00): el 18,8 %** [16,8–21,3]. **La tasa baja a 41,0 % con los mismos motores y el mismo build**, y **3 226 aristas (10,2 %) son ganancia automática sin pedirle nada al usuario**. Lo que **no** se puede prometer es el 81,2 % irrecuperable | Difer. 2 | **`bench/invocacion-aristas.md`** |
| ~~**Las 140 aristas de Ghostscript y Gotenberg**~~ · **RESUELTO: 3,1 % nominal** [0,9–10,7], con **censo completo** de Ghostscript (9/9 reales) y Gotenberg/Chromium (25/25). **Coincide con el 3,0 % del estrato PDF por un camino independiente** | Difer. 2 | ídem §8 |
| ~~**`qpdf` y `tesseract`, los dos `no_evaluable` que quedaban**~~ · **RESUELTO: 8 líneas de Dockerfile, 28,1 s, +50 MB.** qpdf 12.4.0 resuelve 7 de 7 operaciones; Tesseract 5.5.0 **trae `spa`** | Difer. 1 | ídem §9 |
| **La profundidad de los crudos de terceros.** Lo medido son ficheros que escribió el propio ImageMagick a 16 bits; uno de 8 bits **daría basura con la misma bandera**. La categoría «recuperable con un parámetro» exige **cuatro** datos, no uno | Difer. 2 | ídem §11 |
| ~~Qué devuelve un MCP tras convertir un **binario**~~ · **RESUELTO 20/08** | Difer. 3 | `RESULTADOS-MCP.md` §3 |
| ~~Si 27 herramientas saturan la **elección** del modelo~~ · **RESUELTO 21/08, y EN CONTRA de la hipótesis: 540 ejecuciones, 27 herramientas acertaron 100 %/98 % y 8 acertaron 85 %/77 %.** El objetivo de 4 se sostiene **solo por coste** | Difer. 3 | `bench/saturacion-herramientas.md` |
| **Riesgo nuevo, en dirección contraria: un catálogo escueto produce fallos silenciosos (15–17 %)** — la cobertura declarada de `convert` pasa a ser requisito de seguridad | Difer. 3 | ídem §3.5 y §7.2 |
| Rendimiento NVENC en lote sobre una carpeta real | Difer. 4 | — |
| ~~**OCRmyPDF como preprocesador**~~ · **RESUELTO 20/08: descartado, y destapó un artefacto del arnés** | Difer. 5 | `bench/ocrmypdf.md` |
| ~~**Repetir la fase 2 de OCR rasterizando a los ppp nativos**~~ · **RESUELTO 21/08: tabla canónica, 296 celdas, 4 motores** | Difer. 5 | **`bench/ocr-ppp-nativos.md`** |
| ~~**Construir un `escaneado_d4`**~~ · **RESUELTO 21/08: existe, cumple los cuatro criterios y el de éxito declarado antes de medir** (19,30 / 36,91 / 41,78 / 61,41 %). Y **la laguna de las tildes queda medida**: 155 caracteres de error ocultos en 28 celdas | Difer. 5 | **`bench/corpus-d4.md`** |
| ~~**Aislar la asimetría de PaddleOCR**~~ · **RESUELTO 21/08, y no era ninguna de las tres candidatas: era que RapidOCR normaliza el PP-OCRv6 con `mean=std=0,5` cuando el modelo declara ImageNet.** 72,2 puntos de CER por seis números | Difer. 5 | ídem §7 |
| ~~**Validar esa corrección fuera del corpus `d4`**~~ · **RESUELTO 21/08 (14:00): 0 regresiones en 15 documentos sobre `PP-OCRv6 small` — y 12 de 42 celdas PEORES si se aplica a la familia entera**, con +42,50 puntos en `PP-OCRv4 mobile` sobre un documento limpio del patrón oro. **Entra como tabla por checkpoint, no como ajuste global** | Difer. 5 | **`bench/ppp-y-normalizacion.md`** §3 |
| ~~**Barrer la curva de ppp sobre `d4`**~~ · **RESUELTO 21/08 (14:00), y el techo absoluto queda REFUTADO igual que el relativo: NO HAY UNA REGLA GLOBAL DE ppp, hay una por motor.** Los ppp **no son la unidad** (24 celdas), y la elección **baja al adaptador de cada motor** | Difer. 5 | ídem §2 |
| **Caracterizar el `k` de cada motor sobre más de un documento.** Que *haya* un `k` por motor está apoyado por tres documentos; **el VALOR de cada `k` es una estimación de un punto** (todos salen de `escaneado_d4`) | Difer. 5 | ídem §8 |
| ~~**Validar la regla `P9`**~~ · **RESUELTO 21/08 (14:00) y REFUTADA:** 8,3 % de sensibilidad sobre 32 capas OCR reales y 36 % de falsos positivos. **Sustituto medido, 16/16: el acuerdo entre dos pasadas de OCR con idiomas distintos** | Difer. 1 | **`bench/contrato-quinto-punto.md`** §6 |
| ~~**Implementar el quinto punto del contrato y la regla de fidelidad de `resvg`**~~ · **RESUELTOS los dos.** Punto 5: **+11,0 % del contrato con R18, ×8,6 sin él, 0 falsos positivos**. I9: **6/6**, con coste real **32–2 454 ms** en vez de los 26 estimados | Difer. 1 | ídem §2, §4 |
| **El miembro de la familia que sigue descubierto**: audio con un canal silenciado hacia un destino **con pérdida**. La cobertura depende del destino, no del fallo | Difer. 1 | ídem §5 |
| Reintento de Surya por `llamacpp` o VRAM configurable | Difer. 5 | `ESTADO-Y-REPARTO.md` §3.B |
| MinerU con el extra `[vlm]` | Difer. 5 | `ESTADO-Y-REPARTO.md` §3.B |
| ~~Coste real de implementar el contrato de verificación~~ · **RESUELTO 21/08: 1.503 líneas, 0,032 % del tiempo de convertir** | Difer. 1 | `bench/coste-verificacion.md` |
| ~~El mínimo del canal alfa en proceso~~ · **RESUELTO 21/08: 66,0 ms en el peor caso, y en 7 de 12 casos no lee un píxel.** La **fidelidad** cuesta ×1.100 el contrato y va **fuera del camino caliente** | Difer. 1 | **`bench/verificador-fidelidad.md`** |
| ~~`min(alfa)` de TIFF comprimido, GIF y PNG entrelazado; reglas V2 y V5~~ · **RESUELTO 21/08: cubiertos, 36 de 36 contra `magick`, 0 falsos positivos.** Coste real ×2,9 y ×3,6 sobre lo estimado. **Y V2 no era barata: sube la suite de fidelidad un +60,6 %** | Difer. 1 | **`bench/verificador-ghostscript.md`** |

**Cobertura de la ejecución:** de los 9 motores de IA clonados, **6 se ejecutaron y 3 no** (surya no arranca; marker y MinerU nunca se intentaron). ~~De los 6 repos de referencias MCP, ninguno se ejecutó.~~ **Actualizado el 20/08: los 6 se ejecutaron por el protocolo** — 90 componentes catalogados con veredicto y `fichero:línea` en `analysis/00-mcp-componentes.md`, resultados en `RESULTADOS-MCP.md`.

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
| OCRmyPDF | 34 500 | MPL-2.0 | 41 102 | 0 | — | ❌ **Descartado como preprocesador (MEDIDO)**; quizá como empaquetador de PDF/A |
| faster-whisper | 24 992 | **MIT** | 4 027 | 5 | **4 525 MiB** (large-v3) | ✅ **Adoptar tal cual** |
| surya | 21 294 | Apache-2.0 | 13 541 | 15 | ❌ sin dato | ⏳ solo se probó su backend por defecto; **tiene 4** |
| docling-serve | 1 745 | MIT | 11 032 | 0 | — | Patrón de sidecar |
| docling-mcp | 709 | MIT | 6 976 | 2 | — | ✅ Referencia MCP |

### 2.3 Referencias MCP

| Repo | ⭐ | Líneas | Herramientas | GPU | Aporte |
|---|---:|---:|---:|---|---|
| servers (oficial) | 89 685 | 14 957 | — | ❌ | **Confinamiento de rutas listo para portar** (28/29 vectores denegados). Ningún conversor entre ellas. Licencia: **MIT/Apache-2.0 en transición**, ver §3.2 |
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
| **modelcontextprotocol/servers** | **MIT/Apache-2.0 (transición)** | ✅ Sin restricciones de fondo · ⚠️ **obligaciones de Apache-2.0** — ver nota |
| marker, surya | Apache-2.0 | ✅ Con atribución. ⚠️ Los *pesos* se licencian aparte |
| MinerU | Apache + términos | ✅ Umbrales de 100 M usuarios / 20 M USD irrelevantes; atribuir si es servicio online |
| OCRmyPDF | MPL-2.0 | ⚠️ Copyleft por fichero |
| ConvertX, VERT | AGPL-3.0 | ❌ Contamina incluso ofreciéndolo por red |
| SnapOtter | AGPL + `packages/enterprise` propietario + CLA irrevocable | ❌ Y alimentaría a un competidor comercial |
| Stirling-PDF | MIT con 10 directorios excluidos | ⚠️ El núcleo sí; **su MCP requiere suscripción** |

> **Corrección MEDIDA (21/08/2026): `modelcontextprotocol/servers` NO es MIT.** Todo el proyecto lo daba por MIT, y es el repo del que más piezas se propone copiar (el confinamiento completo de `src/filesystem`). Su `LICENSE` empieza: *«The MCP project is undergoing a licensing transition from the MIT License to the Apache License, Version 2.0»* — el código nuevo es Apache-2.0 y **las contribuciones cuyo autor no consintió el relicenciamiento siguen bajo MIT**. Sus `package.json` dicen `"license": "SEE LICENSE IN LICENSE"`.
>
> **No invalida ningún veredicto de reutilización.** Pero **Apache-2.0 obliga a preservar los avisos, marcar los ficheros modificados y adjuntar el `NOTICE`**, cosa que MIT no exige igual. Como la licencia efectiva por fichero es ambigua, **lo seguro es tratar todo lo tomado de `servers/` como Apache-2.0**, cuyas obligaciones son un superconjunto de las de MIT. Detalle en `analysis/00-licencias.md` y `analysis/00-mcp-componentes.md` §3.1.

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

> **Y estas cifras ya tienen su factor de descuento MEDIDO (21/08/2026, `bench/aristas-nominales.md`).** Son **cobertura declarada**, no capacidad. Al ejecutarla: **el 16,3 % de las salidas que ffmpeg declara escribir no las escribe** (33 de 202) y **el 2,2 % de las de ImageMagick** (4 de 183); **el 16,2 % de los formatos que ImageMagick declara leer no los lee** (26 de 160 materializables) **y son ficheros que acaba de escribir él mismo** — autoinconsistencia del mismo binario, en la misma sesión y el mismo directorio. **De los 473 formatos de entrada declarados por ffmpeg, 17 el binario ni los reconoce por nombre, y diez de esos diecisiete son dispositivos de captura de Linux** (`alsa`, `pulse`, `x11grab`, `v4l2`…): ConvertX los declara como «formatos de entrada» porque copió la salida de `ffmpeg -formats` sin filtrar. **Detalle y la cifra global en §3.4.**

### 3.4 El cálculo que justifica el grafo

| Estrategia | Pares alcanzables |
|---|---:|
| **Un salto** — ConvertX, transmute, SnapOtter, todos | 152 584 |
| **Grafo dirigido, hasta 3 saltos** | **447 398** |
| **Conversiones nuevas que hoy no puede hacer nadie** | **294 814** |

**Multiplicador: 2,93× con exactamente los mismos motores.**

| Conversión | Hoy | Con grafo | **Ejecutado (21/08)** |
|---|---|---|---|
| `epub → png` | ❌ imposible | ✅ 2 saltos | ⚠️ **con LibreOffice no** (HTTP 500 con tres EPUB) · **con Calibre SÍ (21/08, 10:00)**: `ebook-convert epub → pdf` da `rc=0`, 26 817 B, centinela y tabla intactos. **No es una arista muerta: es un fallo de selección de motor** |
| `docx → webp` | ❌ imposible | ✅ 2 saltos | ✅ **funciona** |
| `tex → docx` | ❌ imposible | ✅ 2 saltos | ❌ **inalcanzable en Windows**: no hay Pandoc ni XeLaTeX. **Dentro del contenedor sí**: Pandoc dio 8/8 `rc=0` |
| `cbz → pdf` | ✅ ya directo | igual | — |

> **Salvedad honesta:** 447 398 es un límite superior de *alcanzabilidad*, no una promesa de fidelidad. Encadenar degrada: pasar por un formato rasterizado destruye el texto seleccionable, y algunos pares declarados son nominales. Por eso el grafo necesita **coste por arista** (velocidad, pérdida de calidad, si preserva texto), no solo conectividad.
>
> **La salvedad se quedó corta — MEDIDO el 21/08/2026** (`bench/fidelidad-caminos.md`). La cifra de este apartado es **correcta y reproducible** (recalculada: 152 478 → 446 006, desvío −0,3 %), pero al ejecutarla se cae por tres sitios: **con los motores instalados aquí el multiplicador es 1,93×**; de los 128 426 pares nuevos solo **610 (0,48 %)** son plausibles (**+32,7 %, no +193 %**); y **solo el 31,9 % de los caminos multi-salto ejecutados da una salida aceptable**. Además, **cuatro aristas declaradas quedaron refutadas por ejecución**: `epub→pdf`, `txt→png`, `pdf→txt` (152 MB de píxeles enumerados desde un PDF de 3 KB) y `mp4→pdf` (no terminó en 240 s y dejó un hijo `ffmpeg` colgando al supervisor). **Una arista declarada por el catálogo de un motor no es una arista.**
>
> ### Y esa frase ya tiene su cifra — MEDIDO el 21/08/2026 (`bench/aristas-nominales.md`)
>
> **El 50,5 % de las aristas declaradas que se han podido verificar NO EXISTE**, IC 95 % **[48,2 % – 53,0 %]**, sobre las **62 487 aristas (45,1 % de la población de 138 501)** con veredicto de ejecución. **Declarado explícitamente como cota inferior**, por tres sesgos que su propio informe escribe. Sobre la población entera: **cota inferior 22,8 %, central 48,6 %, superior 77,5 %**.
>
> **No hizo falta sondear las 138 501, y ese es el resultado metodológico:** las aristas son cuadráticas (`entradas × salidas`) y las **semiaristas** lineales (`entradas + salidas`). **El censo de 1 104 semiaristas cuesta 9 min 35 s y decide el 45 % de la población** — **22 235 aristas (16,05 %) quedan refutadas sin ejecutar ni una de ellas.**
>
> **Pero la tasa no es uniforme, y los dos hechos hay que citarlos juntos o la cifra engaña:**
>
> | Estrato | Nominal | IC 95 % |
> |---|---:|---|
> | `ffmpeg` **cruzando** familias | **76,9 %** | [67,3 – 84,4] |
> | `ffmpeg` misma familia | 28,8 % | [21,2 – 37,9] |
> | `imagemagick` distinta familia | 5,1 % | [1,7 – 13,9] |
> | `imagemagick` **misma** familia | **4,2 %** | [2,3 – 7,6] |
> | **aristas que tocan PDF** (n=100) | **3,0 %** | **[1,0 – 8,5]** |
>
> **Factor 18 entre el peor estrato y el mejor**, y **no es que ffmpeg sea peor**: es que su producto cartesiano cruza modalidades y el de ImageMagick no. Declarar `473 × 202` es declarar que un `.aptx` se convierte en `.gif`.
>
> **Y el estrato prioritario —PDF como intermedio, el que sostiene el multi-salto— sale al 3,0 %.** `bench/fidelidad-caminos.md` midió que 820 de los 1 599 pares «pedidos» tienen PDF como único intermedio: **si una arista hacia PDF fuera nominal se caería media tesis, y no lo son.** **Las aristas que el multi-salto usa de verdad sí existen** — eso **refuerza** aquel informe en vez de contradecirlo.
>
> **Tres hallazgos laterales que cambian la unidad del grafo:** `epub→pdf` es **real con Calibre y nominal con LibreOffice**; `png→ico` es **real por ffmpeg y nominal por ImageMagick**; `svg→png` es **real en Windows y nominal en Debian**. **La arista mínima viable es `(origen, destino, motor, parametrización, build)`.** Y **20 de los 26 formatos que ImageMagick declara leer y no lee son crudos sin cabecera** (`rgb`, `yuv`, `cmyk`…): la geometría **no está en el fichero** y ConvertX invoca sin `-size`. **O se guarda la geometría fuera del fichero, o esos 20 se borran del catálogo declarado.**

> ### Y el 50,5 % tiene ahora su cota por arriba: **el 18,8 % era invocación, no capacidad** — MEDIDO el 21/08 a las 14:00 (`bench/invocacion-aristas.md`)
>
> Se reintentaron **las 34 + 37 semiaristas muertas y las 118 aristas nominales** de la muestra —un **censo de los fallos**, no una muestra nueva— con una política de invocación declarada **antes** de medir y **con el mismo juez**, para no medir el juez en vez de la invocación.
>
> **Con los mismos motores, el mismo build y el mismo corpus, la tasa nominal baja de 50,5 % a 41,0 %.** IC 95 % [16,8 – 21,3].
>
> | Categoría | Aristas | % del 50,5 % |
> |---|---:|---:|
> | **Recuperable con bandera — ganancia automática** | **3 226** | **10,2 %** |
> | Recuperable con un parámetro del usuario | 2 704 | 8,6 % |
> | **Irrecuperable** | **25 603** | **81,2 %** |
>
> > **La afirmación de producto que sale de aquí, con su acotamiento pegado: FileX puede ofrecer un 10,2 % más de aristas que ConvertX con exactamente los mismos motores y sin pedirle nada al usuario. Lo que no se puede prometer es el otro 81,2 %.**
>
> **Y lo que impide inflar la cifra pesa tanto como la cifra:** **69 de las 118 aristas nominales (58,5 %) son «el muxer no admite ninguna pista que la entrada tenga»** —declaraciones sin sentido, no órdenes mal escritas—, y **19 de las 33 semiaristas de salida muertas de ffmpeg son codificadores no compilados**, que es **build**. Eso último **confirma la quinta dimensión de la arista desde otro lado**: el `build` decide 19 casos y la `parametrización` otros 8.
>
> **El gradiente se invierte respecto al de la tasa nominal, y es informativo:** donde ConvertX fallaba **poco** fallaba **por invocación** (ImageMagick misma familia: **80,0 % recuperable**) y donde fallaba **mucho** fallaba **por capacidad** (ffmpeg cruzando familias: **17,1 %**). **Leer mal es un problema de invocación; escribir lo que el binario no sabe codificar es un problema de build.**
>
> **Lo que más rinde:** `-frames:v 1 -update 1` recupera **13 de las 27** aristas del residuo; **17 de los 20 crudos reviven** —pero exigen **cuatro** datos externos, no uno—; y **`imagen → pdf` con la densidad ajustada a la página hace desaparecer las 6 de 6 degradaciones P7**, entregando un A4 exacto en vez de los 677 × 381 mm de ConvertX.
>
> **Y la superficie documental sale reforzada por un camino independiente: censo COMPLETO de Ghostscript (9 de 9 reales) y de Gotenberg/Chromium (25 de 25 reales), con 3,1 % nominal [0,9 – 10,7] sobre 136 aristas — que coincide con el 3,0 % del estrato PDF medido con otros motores y otro protocolo. Dos medidas independientes que dan lo mismo. Si FileX tiene que elegir dónde prometer, es aquí.**

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
- ~~Su valor no es el OCR sino **todo lo que lo rodea**: rotación automática, corrección de inclinación, eliminación de ruido…~~ **REFUTADO al ejecutarlo (20/08/2026, `bench/ocrmypdf.md`).** Ese preprocesado, en la versión 16.13.0, **no existe o no hace nada**:
  - `--remove-background` lanza **`NotImplementedError`** (rc=15). La bandera sigue anunciada en `--help`.
  - `--deskew` es **inerte**: delega en `tesseract --psm 2`, que devuelve `Deskew angle: 0.0000` **incluso sobre una página girada 5° exactos**.
  - `--clean-final` corre con los filtros útiles desactivados; activarlos **destruye** la página (d2 pasa de 30,4 % a 100 % de CER).
  - `--rotate-pages` es correcto pero solo múltiplos de 90°, y **triplica el tiempo** para decidir «no change».
  - Comprobado **pixel a pixel**: la salida de `--deskew`, `--clean-final` y `--rotate-pages` es **bit a bit idéntica** a no usarlas.
- **Y atravesarlo degrada:** RapidOCR sobre `escaneado_d2` pasa de **1,3 % a 44,3 % de CER** solo por el ciclo rasterizar→JPEG q95→Ghostscript→PDF/A. **Su pasada no es neutra.**
- **Como motor: CER del 100 % en la dificultad 3** (sidecar vacío), como se esperaba.
- **Lo que sí hace bien y nadie más hace:** PDF → **PDF/A-2b con capa de texto buscable**, con `--skip-text` y sidecar `.txt`. Si FileX necesita emitir PDF *buscables* —no solo texto extraído—, es la herramienta. Coste: **502 MB de cierre de dependencias**, WSL o contenedor, **~434 ms de arranque por documento** (no tiene modo servidor) y un aviso permanente de Ghostscript en `stderr` que hay que filtrar. **En ese papel no toca el hueco 5.**
- **No puede aprovechar el Tesseract embebido en Ghostscript**: necesita el binario `tesseract` de verdad.
- MPL-2.0 es copyleft *por fichero*: combinable con código propietario publicando solo los ficheros MPL modificados.

> **Aviso de trazabilidad:** `analysis/OCRmyPDF.md` sigue diciendo que *«su preprocesado de imagen es la referencia a imitar»* y que es *«la ruta por defecto para PDF escaneado»*. **Esa ficha es anterior a la ejecución y queda sustituida por lo de arriba y por `bench/ocrmypdf.md`.**

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

### modelcontextprotocol/servers · 89,7k ⭐ · **MIT/Apache-2.0 (transición)**

Implementaciones oficiales de referencia. **No hay ni un servidor de conversión de ficheros entre ellas.**

- **Licencia corregida (MEDIDO):** no es MIT a secas. Su `LICENSE` declara la transición MIT→Apache-2.0 y las contribuciones no relicenciadas siguen bajo MIT; los `package.json` remiten al fichero. **Tratar todo lo copiado como Apache-2.0** (preservar avisos, marcar modificaciones, adjuntar `NOTICE`). Ver §3.2.
- **Su `src/filesystem` es la pieza de más valor de todo el carril MCP:** **28 de 29 vectores de ataque denegados**, con ~1.000 líneas de tests. El único concedido fue un flujo de datos alternativo (ADS). Su virtud es un detalle de orden —el predicado léxico corre **antes** de tocar el disco— que se copia en una línea. Es lo que sustituye a «la lista blanca hay que inventarla» de `PLAN-ORQUESTADOR.md` §4.6.

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

**La tabla canónica de CER, MEDIDA a ppp nativos** — `bench/ocr-ppp-nativos.md` §3 (21/08/2026, 296 celdas, todas deterministas). **Sustituye a la de `bench/gpu-fase2.md` §5.** Entre paréntesis, la distancia de edición en caracteres sobre 79.

| Motor (backbone real) | `patologico` (200 ppp) | `d1` (150) | `d2` (100) | `d3` (100) |
|---|---:|---:|---:|---:|
| **PaddleOCR** (PP-OCRv6 **medium**, `es`) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) | **2,5 % (2)** |
| **Docling + RapidOCR `backend="torch"`** (PP-OCRv6 **small**) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) | 75,9 % (60) |
| **RapidOCR** aislado (PP-OCRv5 **mobile**, ONNX) | 1,3 % (1) | 0,0 % (0) | 0,0 % (0) | 77,2 % (61) |
| **EasyOCR** (CRAFT + `latin_g2`) | 0,0 % (0) | 0,0 % (0) | **43,0 % (34)** | 54,4 % (43) |

Aceleración y VRAM de la fase 2, **que siguen valiendo como aceleración pero NO como presupuesto** (ver el aviso de VRAM al final de esta sección):

| Motor | Aceleración GPU | VRAM (fase 2, medida a 200 ppp) |
|---|---:|---:|
| **RapidOCR `backend=torch`** | 3,5–4,2× | +1 344 MiB |
| PaddleOCR | 8,9–11,7× | +1 486 MiB |
| EasyOCR | 12,4–17,0× | +2 079 MiB |

*(Las cifras de CER que esta tabla tenía tachadas —1,3 % / 65,8 % / 0,0 % / 75,9 % / 43,0 % / 57,0 %— eran de `bench/gpu-fase2.md`, medidas rasterizando todo a 200 ppp. El 57,0 % de EasyOCR en d3 era su lectura **de CPU**; su lectura de GPU fue 59,5 %, y `ocr-ppp-nativos.md` §2 la reproduce exactamente: **EasyOCR no es determinista entre CPU y GPU** sobre d3, como ya anotaba `gpu-fase2.md` §3.)*

> **Y esa nota deja de ser una rareza de una celda — MEDIDO el 21/08 (`bench/corpus-d4.md` §9.3).** La frase de `gpu-fase2.md` §2 —**«CPU y GPU dan salida idéntica carácter a carácter»**, citada en este proyecto para decir que la GPU no cambia el resultado— **queda REFUTADA**: sobre **21 celdas comparables, 5 difieren**, y **la CPU es mejor en dos y peor en tres**.
>
> | motor | celdas | **distintas** | mayor discrepancia |
> |---|---:|---:|---|
> | RapidOCR | 9 | **1** | `d3` a 200 ppp: **65,82 % (GPU) vs 70,89 % (CPU)** |
> | PaddleOCR | 9 | **1** | `d4`: 19,30 % (GPU) vs 19,63 % (CPU) |
> | EasyOCR | 3 | **3** | `d3` a 200 ppp: 59,49 % (GPU) vs **56,96 % (CPU)** |
>
> **La conclusión matizada, que es la útil:** *la salida coincide mientras el documento es fácil; en la zona de degradación donde el motor duda, el dispositivo cambia el resultado, y puede cambiarlo en cualquier dirección.* **Para FileX: no se puede validar en CPU y desplegar en GPU dando por hecho el mismo resultado, y toda prueba de regresión de OCR tiene que fijar el dispositivo.** *(Matiz honesto de su informe: EasyOCR difiere en la salida de `d3` a 100 ppp aunque el CER coincida — es una permutación del texto, no un cambio de calidad.)*

- **Los múltiplos grandes engañan.** RapidOCR "solo" gana 3,5× porque **su ruta CPU ya es la más rápida** (763 ms frente a los 6 660 ms de EasyOCR). Mejor-CPU contra mejor-GPU, la ganancia real es **3,9×, no 17×**.
- **Elección: RapidOCR con `backend="torch"`** — coste de infraestructura GPU **cero** y salida idéntica a la de CPU. PaddleOCR queda como ruta opcional de máxima precisión (3,73 GB, venv aislado, 24,8 s de carga). **EasyOCR descartado**: peor precisión y **no determinista entre CPU y GPU** en entradas degradadas.
- ~~**En la dificultad 3 fallan los tres** (57–76 % de CER).~~ **FALSO. Corregido el 21/08/2026.**

#### La corrección: las marcas de dificultad 2 y 3 son un artefacto del arnés — **MEDIDO**

**Qué se creía:** que d3 rompía a los tres motores y que el OCR acelerado *«resuelve documentos degradados, no destruidos»*.

**Qué se midió** (`bench/ocrmypdf.md` §3.4, confirmado tres veces de forma independiente): `corpus/pdf/escaneado_d2.pdf` y `escaneado_d3.pdf` llevan una imagen incrustada de **647×850 px sobre una página de 465,84×612 pt = 100 ppp nativos**; `patologico_escaneado.pdf` es de **200 ppp nativos** (1294×1792 sobre 465,84×645,12 pt). **El arnés de la fase 2 rasterizaba todo a 200 ppp.** Para el patológico era correcto; **para d2 y d3 es interpolar ×2**, y ese ×2 convierte el grano JPEG q25 en manchas del tamaño de un trazo.

> **Las cifras publicadas no miden los motores: miden un ×2 de interpolación.** A ppp nativos, **PaddleOCR resuelve la dificultad 3 con 2,5 % de CER** — dos errores de un carácter sobre 79. Con la imagen incrustada extraída sin rasterizar, igual.

La cadena de medición era **fiel**: el control `ctrlppp200` reproduce las marcas antiguas **exactamente, 4 de 4** — y `ocr-ppp-nativos.md` §2 lo reconfirma con **12 de 12** marcas reproducidas. El sesgo estaba localizado en la elección de ppp, no en el instrumento. **Las cifras de `bench/gpu-fase2.md` se conservan tal cual, con un aviso** que las marca como no válidas para medir capacidad de motores.

#### El aviso hay que matizarlo en dos sentidos, los dos MEDIDOS (`bench/ocr-ppp-nativos.md` §4)

**Artefacto = CER a 200 ppp − CER a ppp nativos.** Positivo = la cifra vieja exageraba el error.

| Motor | d2 (nativo 100) | **d3 (nativo 100)** | d1 (150) | patológico (200) |
|---|---:|---:|---:|---:|
| **PaddleOCR** | **0,0 pp** | **+73,4 pp** | 0,0 pp | 0,0 pp |
| **RapidOCR** | +1,3 pp | **−11,4 pp** | 0,0 pp | 0,0 pp |
| **EasyOCR** | **0,0 pp** | +5,1 pp | 0,0 pp | 0,0 pp |
| **Docling+RapidOCR torch** | 0,0 pp | **−17,7 pp** | 0,0 pp | 0,0 pp |

1. **En d2 no había nada que corregir.** El artefacto es **cero** para PaddleOCR y EasyOCR y 1,3 puntos —un carácter— para RapidOCR. **Las cifras de d2 publicadas eran correctas, y el 43,0 % de EasyOCR es un fallo real del motor**, no del arnés: sigue ahí a ppp nativos y con la imagen extraída.
2. **En d3 el artefacto es de UN SOLO motor.** Los 73,4 puntos son **todos de PaddleOCR**. Para **RapidOCR** y **Docling+RapidOCR torch**, la cifra vieja de 200 ppp era **su mejor resultado, no el peor**. Por eso **«a ppp nativos siempre es mejor» es falso como regla general**: lo que es cierto siempre es que es **más rápido** (×1,48 a ×3,13) y **más barato en VRAM** (hasta 6 851 MiB menos).

**Una asimetría que sí es real, con su número corregido:** **RapidOCR no resuelve d3 a ninguna resolución**, pero su mejor caso es **65,8 % a 200 ppp**, no 53,2 % — el 53,2 % de `bench/ocrmypdf.md` incluía `magick -deskew 40%`, que el barrido nuevo no aplica en ninguna celda. **Y la explicación «PP-OCRv5 *mobile* frente al *medium* de Paddle» queda parcialmente refutada:** Docling+RapidOCR torch corre **PP-OCRv6 *small*** —la misma generación que PaddleOCR— **y tampoco resuelve d3**. Hay un v6 en el lado que falla. El límite existe y es grande (2,5 % frente a 39–77 %), pero **no es la generación del backbone**; los candidatos que quedan —tamaño del modelo, idioma del reconocedor, idioma del detector— están **PENDIENTES** de aislar.

**Consecuencia de diseño, y no es la que se anticipaba:** no es «añadir una etapa de preprocesado» sino **leer los ppp de la imagen incrustada y no sobremuestrear**, con la regla medida `ppp_ocr = clamp(ppp_nativos, 100, ppp_nativos × 1,4)` — **techo ×1,4 porque entre ×1,4 y ×1,6 se pierden 72 puntos de CER**, y **suelo 100 porque a 75 ppp RapidOCR se rompe en d2** (44,3 %). Es **una decisión, no una etapa**, y cuesta *menos* CPU y VRAM. `magick -deskew 40%` entra como red de seguridad, no como fuente de la ganancia. **El hueco 5 se reabre** — ver `HUECOS.md` §5.

**Aviso colateral de VRAM, ampliado — MEDIDO** (`ocr-ppp-nativos.md` §7.2): **PaddleOCR picó a 12 025 de 12 288 MiB** con imágenes a 600 ppp, y **EasyOCR a 11 877 MiB con imágenes a solo 300 ppp**, a 411 MiB de agotar la tarjeta, sobre un documento de **una página**. **El presupuesto del sidecar hay que fijarlo por motor Y por resolución de entrada**: el «+2 079 MiB» de la fase 2 subestima el peor caso de EasyOCR casi **5×**. **RapidOCR es el único insensible a los ppp** (+0 MiB entre la imagen extraída y 300 ppp).

**Y el corpus dejó de medir lo que se creía — MEDIDO** (`ocr-ppp-nativos.md` §8): tenía **tres documentos que todos resuelven al 0,0 %** y uno que para PaddleOCR era **un interruptor** (2,5 % o 75,9 %, casi sin estados intermedios) y para los otros tres una pared plana. **Ya no medía dificultad: medía selección de motor.** ~~Hace falta construir un `escaneado_d4`.~~ **RESUELTO el 21/08 — ver abajo.**

#### `escaneado_d4`: el corpus que sí mide margen — MEDIDO (`bench/corpus-d4.md`, 21/08/2026)

**Criterio de éxito declarado ANTES de medir:** *al menos un motor entre 15 % y 60 % de CER, y al menos dos separados por más de 10 puntos.* **Mediana de n=9, ppp nativos, 28 celdas deterministas. Formato: CER con acentos / CER ascii.**

| documento | PaddleOCR (v6 medium) | Docling+RapidOCR torch (v6 small) | RapidOCR (v5 mobile) | EasyOCR |
|---|---:|---:|---:|---:|
| `d4_limpio` (**control**) | **0,00** / 0,00 | 0,00 / 0,00 | 1,17 / 0,50 | 0,50 / 0,50 |
| `escaneado_d4c` | 0,67 / 0,00 | 22,99 / 22,48 | 15,60 / 11,91 | 15,10 / 13,76 |
| **`escaneado_d4`** | **19,30** / 18,46 | **36,91** / 36,24 | **41,78** / 38,59 | **61,41** / 59,56 |
| `escaneado_d4e` | 70,97 / 70,47 | 88,59 / 88,42 | 92,45 / 92,11 | 73,32 / 72,32 |

**Cumple: tres motores en la banda 15–60 % y 17,6 puntos entre el primero y el segundo.** **Y el control importa** —`d4_limpio` sale a 0,00–1,17 %—: **todo lo que se mide viene de la degradación, no del diseño de la página.**

**Dos decisiones de diseño reutilizables, y la segunda explica en parte el «interruptor» de d3:**

1. **Cuatro tamaños de letra en la misma página** — 24 / 13 / 11 / **7 pt** (19,3 px de cuerpo a 200 ppp) — para producir fallo **graduado**.
2. **Una referencia de 610 caracteres, que cuantiza el CER a 0,16 puntos por carácter frente a los 1,27 de los 79 de d1-d3.** **Con 79 caracteres no puede haber gradiente aunque el documento lo tenga.**

**Y el criterio «atacar al reconocedor, no al detector» está MEDIDO con recuento de cajas: PaddleOCR detecta 12 de 12 renglones sobre `escaneado_d4` y aun así comete 19,30 % de CER.** Los cuatro renglones de 7 pt están **detectados y transcritos como basura** (58,69 % de CER en ese bloque frente al 1,60 % del cuerpo). Es lo contrario de d3, donde los motores que fallaban recuperaban el titular y **no emitían nada** del cuerpo.

**La métrica antigua es ciega a las tildes, y ahora se sabe cuánto: 155 caracteres de error ocultos en 28 celdas, media 5,54, máximo 23.** RapidOCR **no recupera ni uno de los 35 caracteres acentuados** de `d4` y `ocr_eval.py` le da 38,59 % en vez de 41,78 %. **Las 296 celdas de `ocr-ppp-nativos.md` siguen siendo válidas para lo que miden** —su referencia no tiene una sola tilde—, **pero no se pueden extrapolar a castellano.**

#### La asimetría de PaddleOCR, RESUELTA — y no era ninguna de las tres candidatas

**MEDIDO** (`bench/corpus-d4.md` §7). Refutadas una a una: **(1) el tamaño del modelo** —el **mismo** PP-OCRv6 small da **3,80 % en PaddleOCR y 75,95 % en RapidOCR** sobre d3—; **(2) el idioma del reconocedor** —en v6, `lang="es"` y `lang="en"` resuelven al **mismo par de checkpoints** y dan salida idéntica carácter a carácter—; **(3) el idioma del detector** —en v6 hay **un solo detector, `multi`**—.

> **La causa: RapidOCR normaliza el PP-OCRv6 con `mean=std=0,5` cuando el `inference.yml` que Baidu distribuye CON el modelo declara las estadísticas de ImageNet** (`[0,485, 0,456, 0,406]` / `[0,229, 0,224, 0,225]`).
>
> **A/B causal, mismo checkpoint: la normalización sola vale 64,6 puntos de CER en d3 (75,95 → 11,39); el post-proceso solo, 0,0; los dos juntos reproducen la cifra de PaddleOCR exactamente (3,80 %).** Con recuento de cajas, el detector pasa de encontrar **1 renglón de 3 a 3 de 3**.

**Cuatro consecuencias:** la explicación «es límite de modelo, v5 mobile frente al medium» **queda superada del todo**; **Docling hereda el defecto** y es corregible desde fuera; **es la corrección más barata medida en el proyecto —seis números por 72,2 puntos de CER—**; y deja una **regla general**: *cuando el motor y el modelo vienen de proyectos distintos, hay que comprobar que el preprocesado que aplica el motor es el que declara el fichero de configuración del modelo.* Mismo tipo de fallo que `onnxruntime-gpu` cayendo a CPU en silencio: **nada da error, solo empeora.**

**Y con esa corrección, la elección de motor cambia: un solo motor cubre el corpus entero.** RapidOCR ONNX con PP-OCRv6 small da **0,00 / 0,00 / 0,00 / 3,80 / 18,62 %** sobre patológico, d1, d2, d3 y d4, **gana a PaddleOCR en cuatro de las cinco filas, arranca en 3,7 s en vez de 18,4 y funciona en CPU** (0,32–1,18 s/página, ×2,3–3,8 sobre la GPU; PaddleOCR es ×9,8–13,8, hasta 5,42 s). *La excepción es d3, donde PaddleOCR gana por **1,27 puntos — un carácter sobre 79**. No es base para una regla de conmutación.*

#### El techo de la regla de ppp pasa de relativo a absoluto — MEDIDO (`corpus-d4.md` §8)

Sobre `escaneado_d4` (**200 ppp nativos**), subir a **280 ppp (= ×1,4)** **empeora PaddleOCR de 19,30 % a 36,24 %** y a RapidOCR corregido de 18,62 % a 28,86 %. **La meseta de ×1,4 se midió sobre d3, de 100 ppp nativos, y era en parte un artefacto de que todo el corpus viejo fuera de 100–200 ppp.** Lo que decide no es el factor sino **el tamaño en píxeles que llega al detector**. Propuesta: `clamp(nativos, 100, 200)` — **techo absoluto**, que **no viola ninguna medida existente y el relativo sí. PENDIENTE de barrer la curva sobre `d4`.**

#### Y al barrer la curva cayó también el techo absoluto: **NO HAY UNA REGLA GLOBAL DE ppp** — MEDIDO (`bench/ppp-y-normalizacion.md` §2, 21/08 14:00)

**17 puntos de ppp sobre `escaneado_d4` con siete configuraciones de motor, más `d3`, `d4c`, `d4f` y `patologico_escaneado`. Mediana de n=9, GPU, dispositivo fijado. Las tres unidades candidatas caen una a una:** los **ppp absolutos** (`d3` se rompe a 160; `d4c`, `d4f` y el patológico no se rompen a 400), el **factor sobre el nativo** (PaddleOCR se rompe en `d4` a ×1,4, en `d3` a ×1,6 y **nunca** en `d4c` ni `d4f`) y la **anchura en píxeles** (`d3` se rompe a 1 035 px; `d4c` no se rompe a 2 070).

**El experimento que lo decide, 24 celdas:** el **mismo JPEG** de `escaneado_d4` reempaquetado en tres páginas de 100, 200 y 400 ppp nativos da, **a los mismos 200 ppp**, CER de **19,13 / 19,63 / 36,24 %**; **a los mismos píxeles coincide a la centésima**, doce parejas exactas.

> **Los ppp no son una propiedad del documento que el OCR pueda usar: son una división entre los píxeles que hay y el tamaño que el PDF dice que tiene la página. Una regla escrita en ppp está escrita en la unidad equivocada.**

**La respuesta es la cuarta candidata: la regla es POR MOTOR.** Siete configuraciones sobre el mismo documento dan óptimos entre **×0,50 y ×1,80** (×0,88 Docling+R6 · ×1,00 RapidOCR+R6 · ×1,25 PaddleOCR · ×1,60 Docling sin corregir · ×1,80 EasyOCR). **Y sobre `escaneado_d3`, a ×1,4, el mismo fichero es seguro para PaddleOCR (3,80 %) y catastrófico para RapidOCR+R6 (2,53 → 46,84 %).** El mecanismo está sondeado en ejecución: **`Global.max_side_len: 2000` hace que por encima de 233 ppp RapidOCR reciba el array idéntico; PaddleOCR no recorta.** *(Deducirlo del código de PaddleX daba lo contrario, y su informe lo publica como error propio: es «sondear en ejecución, no deducir» otra vez.)*

> **La consecuencia de arquitectura: la elección de ppp pertenece al ADAPTADOR DE CADA MOTOR, no al orquestador.** Es un parámetro del motor, del mismo rango que `Det.mean`. **Si se queda en el orquestador, cada motor nuevo hereda en silencio los ppp que le convenían a otro** — lo que le pasa hoy a Tesseract, al que la regla vieja le asigna 100 ppp sobre `escaneado_d2` y **le cuesta 32,10 puntos**.

**Lo que sí queda como regla global es de VRAM, no de precisión:** barrer hasta 400 ppp con **una sola página** llevó a **PaddleOCR a 11 942** y a **EasyOCR a 12 037 de 12 288 MiB, sin dar error**. **El coste de no poner límite son 10 GB.**

#### La normalización de RapidOCR, validada — y con un lado malo — MEDIDO (`bench/ppp-y-normalizacion.md` §3)

**Sobre `PP-OCRv6 small`, 15 documentos y n=9 —incluidas cuatro rasterizaciones del patrón oro—: 6 mejoras, 9 empates, 0 empeoramientos**, hasta −72,15 puntos. **Docling: 7 de 7, cuatro mejoras grandes, cero regresiones y coste en tiempo nulo**, corregible desde fuera por `RapidOcrOptions.rapidocr_params`.

**Pero se buscaron los casos peores y se encontraron: 12 de 42 celdas del cribado EMPEORAN**, con **+42,50 puntos en `PP-OCRv4 mobile` sobre `tipico_texto` del patrón oro —un documento limpio—**, +16,45 y +13,60 en `PP-OCRv6 tiny`, y 4 de 15 celdas peores en `PP-OCRv5 mobile`.

> **El desajuste es universal; el daño no.** Los **ocho** `inference.yml` que Baidu distribuye, de PP-OCRv3 a PP-OCRv6, **declaran ImageNet**, y `rapidocr/config.yaml` aplica `0,5` a los ocho. **Pero solo `PP-OCRv6 small` se hunde por ello: la hipótesis obvia es falsa para 7 de los 8.** **Devolverle al modelo lo que su propio fichero de configuración declara es una hipótesis, no una solución — hay que medirla checkpoint por checkpoint**, y por eso entra en FileX **como tabla por checkpoint, no como ajuste global del motor**.

#### Y hay OCR de calidad sin tarjeta — MEDIDO (`bench/verificador-ghostscript.md` §5)

El **Tesseract embebido en Ghostscript 10.07** da **0,0 % de CER en patológico, d1 y d2 a ppp nativos con `spa`** —igual que la ruta de GPU—, con **VRAM 0** y **carga en frío de 122 ms frente a 3,4–17,3 s**. **En d3 fracasa alucinando (165,8 % de CER):** un modo de fallo **cualitativamente distinto** del de los motores GPU, que devuelven poco texto. **Para una CLI que convierte un fichero y termina, la carga en frío ES el coste**, y ahí la diferencia es de **28× a 142×** a favor de la CPU. *(Coste de distribución real: Ghostscript trae el motor pero **no los datos de idioma** — 2-4 MB por idioma.)*

#### El octavo fallo de verificación, y es el primero que el contrato no atrapa — MEDIDO

**`resvg 0.46.0` rasteriza un SVG con dos bloques de texto y devuelve `rc=0`, un PNG de firma válida y de la geometría exacta pedida, y sin una sola letra** (`bench/aristas-nominales.md` §8.2):

| Rasterizador | Bytes | Geometría | **Tinta en la banda de texto** | Tinta total | rc |
|---|---:|---|---:|---:|---:|
| Inkscape (contenedor) | 13 456 | 400×200 | **14,02 %** | 13,38 % | 0 |
| **resvg 0.46.0** | 8 973 | 400×200 | **0,00 %** | 8,78 % | **0** |
| `magick` 7.1.2 (Windows) | 8 628 | 400×200 | **15,07 %** | 13,39 % | 0 |
| `magick` (contenedor Debian) | — | — | — | — | **1** |

**Firma correcta · flujos correctos · propiedades declaradas coherentes · pedido = obtenido. Los cuatro puntos del contrato lo aprueban.** Lo único que lo delata está en `stderr` (`No match for '"DejaVu Sans", sans-serif' font-family`) — y el contenedor **tiene 153 fuentes instaladas**: no es un problema de fuentes, es que ese build no resuelve familias.

> **Esto acota el diferenciador nº 1 con precisión y no lo invalida.** El contrato juzga **la declaración** de la salida; el **contenido que desaparece sin dejar rastro en ninguna propiedad declarada** solo se ve **comparando la salida con la entrada**, es decir, en la fidelidad. ~~**PENDIENTE** la regla que lo atraparía~~ — **IMPLEMENTADA el 21/08 a las 14:00, y con dos sorpresas.**

##### La regla I9 y la familia de `resvg` — MEDIDO (`bench/contrato-quinto-punto.md` §4, §5)

**I9 discrimina 6 de 6 con margen binario:** `resvg` **0,00 %** de tinta en la banda de texto frente a **20,01 %** (Inkscape) y **23,61 %** (`magick`), sin un falso positivo en tres controles y sin añadir ni un aviso sobre las 53 salidas del patrón oro.

**Primera sorpresa: cuesta 32–59 ms a 400×200 y 2 454 ms a 1920×960. La estimación de «del orden de 26 ms» se queda corta ×94.** Y de ahí sale **una refutación de una constante de diseño del proyecto**: *«verificar en proceso, no con subprocesos»* **no se transfiere a leer PÍXELES** — `magick` hace la misma medida en **138 ms** donde el lector en proceso tarda **2 834**, y **el punto de cruce está en ~0,1 Mpx**. Sigue siendo cierto para cabeceras, donde el factor es **145× a favor del proceso**. **Son dos regímenes.**

**Segunda sorpresa: `resvg` no era un caso aislado, es una familia de al menos cinco miembros** —SVG sin fuentes, vídeo con envase correcto y todo negro (**5,39 dB**, y solo `aviso`), PDF de texto rasterizado, CSV→JSON que pierde una columna, y audio con un canal silenciado—. **El contrato atrapa uno, I9 otro, y uno sigue sin cubrir:** el canal silenciado hacia un destino **con pérdida** (el mismo fallo hacia FLAC sí lo atrapa A4). **La cobertura depende del destino, no del fallo.**

> **Y el acotamiento que el proyecto había escrito —«el contrato juzga la declaración; el contenido que desaparece necesita fidelidad»— queda CONFIRMADO, con formulación precisa:** *el contrato atrapa la pérdida cuando el contenido perdido está **declarado en metadatos** —filas, cabecera de un CSV, pistas, páginas— porque la sonda ya los lee para los puntos 2, 3 y 4; necesita fidelidad cuando el contenido **solo existe como píxeles o como muestras**.* **La pregunta se planteó como posible excusa y la medición la confirmó como arquitectura:** el precio es de **tres órdenes de magnitud**, y **el miembro cuyo contenido sí está declarado —el CSV— lo atrapa el contrato y no la fidelidad**.

**Y hay un sexto candidato, encontrado por otro agente y por otro camino** (`bench/invocacion-aristas.md` §4.1): este ImageMagick es **Q16-HDRI y escribe los crudos a 16 bits/canal**; releer un `.rgb` con `-depth 8` **no falla**, entrega **la geometría exacta pedida** y **píxeles basura**, y **pasa los cuatro puntos del contrato**. **Dos vías independientes llegando al mismo patrón** es lo que lo convierte de anécdota en clase de fallo.

##### Y el quinto punto está implementado, con un coste que reordena una prioridad — MEDIDO (ídem §2, §3)

**Cuesta 0,047 ms, el +11,0 % del contrato, y entra en el camino caliente — pero solo con R18:** sin directorio de trabajo desechable, sobre un directorio de **1 000 ficheros**, cuesta **3,66 ms, ×8,6 el contrato entero**. **R18 deja de ser higiene y pasa a ser requisito de coste.** **Falsos positivos sobre el patrón oro: cero**, con las 39 órdenes reejecutadas.

> **Y su coste honesto es un cambio de naturaleza: sin censo, 49 de las 53 salidas bajan de `ok` a `ok_parcial`.** No es un falso positivo: **el punto 5 es el primero del contrato que no es verificable a posteriori.** **La verificación tiene que vivir dentro de la conversión, no ser un paso posterior.**

**Y una nota de portabilidad que va con la tabla:** `magick svg → png` **funciona en el ImageMagick de Windows y falla (rc=1) en el de Debian del contenedor**. La misma arista, el mismo motor, la misma versión mayor: **real en una máquina y nominal en otra.**

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

**Ninguno de los seis recibe una ruta del sistema de ficheros**: todos reciben una subida HTTP y escriben ellos el fichero. **FileX recibirá rutas arbitrarias de un LLM.**

> **Corrección MEDIDA (21/08/2026).** Aquí se decía que la lista blanca de raíces «hay que diseñarla desde cero». **Es cierto para los seis orquestadores y falso para el ecosistema MCP:** `modelcontextprotocol/servers/src/filesystem` resiste **28 de 29 vectores medidos** y su porte a Python es ~1 día. **La corrección es parcial:** lo que existe ya hecho es la **contención de rutas**; siguen siendo trabajo propio de FileX **el mensaje opaco** (ninguna referencia lo hace), **el confinamiento frente a procesos externos** —que es la ventana real, de minutos, porque quien lee y escribe es ffmpeg— y **el contenido hostil**. Las **18** reglas, con su evidencia, en `PLAN-ORQUESTADOR.md` §4.6 — **la 18.ª, medida el 21/08: un directorio de trabajo desechable por conversión, porque hay motores que escriben en el `cwd` del proceso.**

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
| **Grafo dirigido con coste por arista** y Dijkstra | Resuelve el bug de prioridad de ConvertX. ~~2,93× de cobertura~~: **1,93× con los motores instalados, y solo el 31,9 % de los caminos multi-salto da salida aceptable.** El valor está en elegir bien el primer salto |
| **Contrato de verificación obligatorio tras cada conversión, con CUATRO puntos** | Habría atrapado el `.avif`-que-era-PNG, la pista perdida y las degradaciones de bits/ppp/bitrate. **El cuarto punto —pedido frente a obtenido— atrapa además el redimensionado no solicitado, que los otros tres no ven** |
| **Verificar leyendo cabeceras en proceso, no con `ffprobe`** | 0,372 ms frente a 54,06 ms: **145×**. Con subprocesos, en 15 de 39 órdenes verificar cuesta más que convertir |
| **Leer los ppp de la fuente antes de rasterizar; no sobremuestrear** | Un ×2 de interpolación llevó a PaddleOCR de 2,5 % a 75,9 % de CER, y a 12 025 MiB de VRAM |
| **`stdin=DEVNULL` + banderas no interactivas en todo subproceso** | ffmpeg sin `-y` heredó la tubería JSON-RPC y colgó la sesión MCP entera: 1,4 s con `-y`, infinito sin él |
| **Toda operación larga devuelve un `job_id` al empezar** | Un clip de 5 s superó los 900 s de timeout **con la conversión ya terminada bien en disco** |
| **Un recurso alternativo sin verificación es peor que no tenerlo** | Convierte un fallo honesto en uno silencioso: literalmente lo que le pasa a ImageMagick dentro de ConvertX |
| **Registro por reflexión con `can_register()`** | Solo 4 de ~12 motores presentes en esta máquina |
| **Sondear capacidades en ejecución, no deducirlas** | `av1_nvenc` aparece listado y no funciona |
| **Verificar `torch.cuda.is_available()` en cada arranque** | `pip install surya-ocr` tumbó CUDA sin un solo error |
| **Comprobar `session.get_providers()`, no `get_device()`** | onnxruntime dice `'GPU'` mientras corre en CPU |
| **Del registro se generan los `enum` de parámetros, NO las herramientas** | «Un motor nuevo = una herramienta» es el mecanismo que produce las **27 herramientas planas** de `video-audio-mcp` (7.964 tokens de catálogo). Las cuatro herramientas se escriben a mano |
| **MCP devuelve ruta y metadatos, nunca contenido — en ninguna codificación** | ~2 400× de diferencia en tokens. Y el binario aparece de verdad como **base64 dentro de un `TextContent`**: 71 → 6.218 tokens con un booleano |
| **Presupuesto de catálogo en TOKENS, no en número de herramientas** | El coste por herramienta varía **×11** (79 → 875) según su superficie de parámetros. Objetivo: **≤1.200 tokens** para las cuatro |
| **Registro LRU de modelos acotado por VRAM + TTL** | SnapOtter no gestiona VRAM en absoluto |
| **Filtrar por `language_probability`** | Whisper alucina `Thanks for watching!` sobre un tono puro |
| **Lista blanca de raíces, denegar por defecto** | Ninguno de los seis lo resuelve; markitdown devolvió `win.ini` |
| **Distinguir pérdida inevitable de fallo del motor** | 17 pérdidas catalogadas en la referencia nativa |

### 7.4 Orden de construcción

1. **Registro, grafo y CLI** con FFmpeg e ImageMagick — **75 % de la cobertura de formatos con dos motores**.
2. **NVENC** con sondeo de capacidades y degradación a CPU. 8,4× en HEVC, coste casi nulo.
3. **Contrato de verificación post-conversión.** Sin él, todo lo anterior puede mentir.
4. **Capa MCP de cuatro herramientas escritas a mano, con los `enum` generados desde el registro**, devolviendo ruta y metadatos.
5. **Gotenberg en Docker** para ofimática→PDF, evitando instalar LibreOffice en Windows.
6. **Sidecar IA**: faster-whisper (`distil` ≤30 s, `large-v3` por encima) y Docling con RapidOCR en `backend="torch"`.
7. **Watcher y API HTTP local**, superficies delgadas sobre el mismo núcleo.

Los pasos 1 y 2 ya superan en cobertura y velocidad a todo lo analizado, salvo en OCR y ofimática.

---

## 8. Material de respaldo

| Ruta | Contenido |
|---|---|
| `informe-filex.html` | Informe navegable (publicado como Artifact) |
| **`RESULTADOS-MCP.md`** | **Resultados de los 6 repos de `mcp-refs/`**: el caso binario, los catálogos medidos, las 15 reglas de confinamiento (**ampliadas a 18** en `PLAN-ORQUESTADOR.md` §4.6), y **7 correcciones a este documento y a `PLAN-ORQUESTADOR.md`** (estado de aplicación en su §12) |
| **`bench/coste-verificacion.md`** | El precio del diferenciador nº 1: coste medido, el 4º punto del contrato y el 17 % de falsos positivos de la primera versión |
| **`bench/fidelidad-caminos.md`** | 69 caminos multi-salto ejecutados y clasificados; la función de coste propuesta |
| **`bench/ocrmypdf.md`** | OCRmyPDF descartado como preprocesador, y el artefacto de ppp que invalida las marcas de OCR de d2/d3 |
| **`bench/sdk-mcp-capacidades.md`** | Roots, la desaparición de Tasks y la restricción `mcp>=2.0.0` |
| **`bench/confinamiento-multimedia.md`** | Los MCP de multimedia atacados: origen de las reglas R16 y R17 |
| **`bench/aristas-nominales.md`** | **El 50,5 % de aristas nominales** con su método (censo de semiaristas + muestra estratificada), el estrato PDF al 3,0 %, el **quinto punto del contrato**, el caso de `resvg` y los 5 de 7 `no_evaluable` cerrados en contenedor |
| **`bench/corpus-d4.md`** | **`escaneado_d4`**, la causa real de la asimetría de PaddleOCR, el techo absoluto de ppp y las dos refutaciones CPU/GPU |
| **`bench/verificador-ghostscript.md`** | **El OCR sin GPU de Ghostscript**, `min(alfa)` de TIFF/GIF/Adam7, V2 y su coste, `P9` contra la alucinación *(refutada después)*, y el segundo testigo de ruido |
| **`bench/ppp-y-normalizacion.md`** | **La curva de ppp barrida (17 puntos) y la refutación de las TRES unidades candidatas**; el **`k` por motor** y por qué la elección baja al adaptador; el tope interno de cada detector sondeado en ejecución; y **la validación de la normalización por checkpoint**, con sus 12 empeoramientos |
| **`bench/invocacion-aristas.md`** | **El 18,8 % del 50,5 % que era invocación** y sus tres categorías; los crudos y sus cuatro datos externos; `imagen → pdf` con densidad ajustada a página; el **censo completo de Ghostscript y Gotenberg al 3,1 %**; y el **coste de integrar `qpdf` y `tesseract`: 8 líneas, 28,1 s, +50 MB** |
| **`bench/contrato-quinto-punto.md`** | **El quinto punto implementado y medido** (+11,0 % con R18, ×8,6 sin él, y **no verificable a posteriori**); **la regla I9** y su coste real; **la familia de cinco miembros**; **`P9` refutada con su sustituto medido**; el interruptor de V2; y **el fallo de la propia sonda `_gs_texto`** |
| `analysis/00-mcp-componentes.md` | 90 componentes MCP → veredicto, con `fichero:línea` |
| `bench/mcp-refs-multimedia.md` | El caso binario ejecutado: qué devuelve un MCP tras convertir |
| `bench/mcp-refs-confinamiento.md` | Ataques de ruta, oráculo de existencia, TOCTOU, y las reglas R1-R15 (R16 y R17 en `bench/confinamiento-multimedia.md` §6; **R18 en `bench/aristas-nominales.md` §5.2**; las **18** juntas, en `PLAN-ORQUESTADOR.md` §4.6) |
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
| `corpus/` | Ficheros de prueba en 5 categorías: las 3 variantes duras de OCR (`d1`-`d3`) **más la familia `escaneado_d4{,a,b,c,e,f}`, seis PDF de 200-240 ppp nativos con castellano acentuado**, con `corpus/pdf/MANIFIESTO-d4.md` |
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
