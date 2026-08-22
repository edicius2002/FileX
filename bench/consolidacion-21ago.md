# Consolidación documental del 21 de agosto — qué decía cada maestro y qué dice ahora

**Agente D1.** 21 de agosto de 2026, 03:30–04:30. **Sin GPU, sin mediciones nuevas: este informe no mide nada, reconcilia.**

**Fuentes integradas** (los cuatro informes que estaban sin volcar en ningún documento maestro):

| Hora | Informe | Qué aporta |
|---|---|---|
| 02:44 | `bench/verificador-fidelidad.md` | `min(alfa)` en proceso, las 11 reglas de fidelidad, y la separación en **tres grupos** |
| 02:48 | `bench/mcp-cabos-sueltos.md` | Los cinco cabos de `RESULTADOS-MCP.md` §13, con su tabla de **12 correcciones** en §6 |
| 02:49 | `bench/saturacion-herramientas.md` | **540 ejecuciones**: el catálogo grande **no** degrada la elección |
| 03:07 | `bench/ocr-ppp-nativos.md` | **La tabla canónica de OCR**, la regla de ppp y la VRAM por resolución |

**Regla que gobernó el trabajo:** ni una cifra inventada. Cada número movido a un maestro está **literalmente** en uno de los cuatro informes y se cita con fichero y sección. Donde dos documentos se contradicen, **no se elige: se escribe la contradicción y se señalan los dos sitios** (§4).

---

## 1. La tabla de cambios

### 1.1 `HUECOS.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | Dos revisiones (19/08 y 21/08 00:32) | **Tercera revisión (21/08, 03:30)**, con el resumen de qué cierra cada informe | los cuatro |
| **§1 · «Lo que sigue PENDIENTE»** | *«`min(alfa)` … el cálculo en proceso está sin escribir»*, **734,6 ms** con `magick`; *«las reglas que exigen comparar píxeles … cuestan lo que la conversión»* | **CERRADOS los dos.** `min(alfa)` en proceso: **66,0 ms** en el peor caso (PNG 1920×1080 RGBA16 opaco) frente a **376,3 ms** de `magick` remedido; **0,23 ms** en el mejor; **en 7 de 12 casos no lee un solo píxel** (0,05–0,17 ms, hasta ×13.569). Se **conserva** la cifra vieja como lo que se creyó y se marca que **376 ms es la vigente** | `verificador-fidelidad.md` §0.1, §0.2, §1.3 |
| §1 (nuevo) | — | **La separación en tres grupos** con su coste: A contrato 0,37 ms / 0,032 %; B caracterización de la entrada, cacheada por hash; C fidelidad **×1.106 el contrato** y **38,5 % de convertir → fuera del camino caliente** | ídem §2.2, §3.1 |
| §1 (nuevo) | — | Los **dos puntos ciegos cerrados**: aplanado sobre negro (I3, **25,9 ms**, un píxel) y paleta genérica del GIF (V9, **0,18 ms en proceso**) | ídem §5.4 |
| §1 (nuevo) | — | El umbral de `txtwrite` **≥10** con su caso: `alpha_png-to.pdf` devuelve `'FX'`; con `>0` se declararía «conserva texto» **1 de 9 PDF (11 %)**. Coste 179,3 ms de mediana = **485× el contrato** | ídem §4 |
| §1 (nuevo) | — | Prototipo revalidado: **3.035 líneas**, **5/5 fallos atrapados**, **0 falsos positivos en seis configuraciones**, y **11 de 53 pasan a `ok_parcial`** sin `min(alfa)` | ídem §5.1, §5.2 |
| §1 · PENDIENTE (lista nueva) | — | TIFF comprimido/GIF (120-180 líneas), Adam7 (~40), V2 y V5, VP8L escala mal, OCR de Ghostscript, los 7 `no_evaluable`. **Y un hueco nuevo que no es de píxeles:** una entrada **envenenada en sitio** produce salida coherente con `returncode 0` y **el contrato la aprueba** | ídem §7 + `mcp-cabos-sueltos.md` §5.6 |
| **§3 · «Si 27 herramientas saturan la elección. SIGUE PENDIENTE»** | Pendiente: *«el análisis es estructural, no conductual»* | **RESUELTO, y en contra de la hipótesis.** 27 herramientas: **100 %/98 %** de acierto permisivo y **0 %/2 %** de trampas; 8 herramientas: **85 %/77 %** y **15 %/17 %**. p < 0,001 en los dos modelos. **El objetivo de 4 se sostiene SOLO por coste** | `saturacion-herramientas.md` §3.2, §6 |
| §3 (nuevo) | — | **El catálogo se paga ×2,0–2,6 por petición**: los ≤1.200 tokens son **≈2.400–3.100 reales** | ídem §3.6, §7.1 |
| §3 (nuevo) | — | **Riesgo nuevo en dirección contraria:** un catálogo escueto produce **fallos silenciosos** (15–17 %) → **la cobertura declarada de `convert` es requisito de seguridad** | ídem §3.5, §7.2 |
| §3 · pregunta 6 | «0,93 tokens por byte» como cifra única | **Precisada:** 0,93 tok/B es el **base64 dentro de texto**; el **`ImageContent` nativo cuesta por píxel** (**2.814 tok** medidos para 1920×1080). La conclusión no cambia | `mcp-cabos-sueltos.md` §1.3 |
| **§5 · tabla de CER** | Tres motores con las columnas de d2 y d3 **tachadas** | **Tabla canónica de cuatro motores a ppp nativos**, con la distancia de edición en caracteres. Aceleración y VRAM se separan en su propia tabla | `ocr-ppp-nativos.md` §3 |
| §5 · el aviso de `gpu-fase2.md` | *«las cuatro columnas de d2 y d3 no son válidas»* | **Matizado en dos sentidos medidos:** (a) **en d2 el artefacto es CERO** para PaddleOCR y EasyOCR y 1,3 pp para RapidOCR — **las cifras de d2 eran correctas, y el 43,0 % de EasyOCR es un fallo real**; (b) **en d3 el artefacto es de un solo motor** — los **73,4 pp son todos de PaddleOCR**, y para RapidOCR (**−11,4**) y Docling+RapidOCR torch (**−17,7**) los 200 ppp eran **su mejor resultado** | ídem §4 |
| §5 · «RapidOCR mejor caso 53,2 %» | 53,2 % | **65,8 % a 200 ppp**, sin deskew. El 53,2 % de `ocrmypdf.md` incluía `magick -deskew 40%` | ídem §8 |
| §5 · «es límite de modelo, v5 mobile frente a medium» | Afirmado, con la nota de que v5/v6 estaba sin conciliar | **Discrepancia CERRADA** (Paddle corre **PP-OCRv6 medium**: acierta `ocrmypdf.md`, se equivoca `gpu-fase2.md`) **y explicación PARCIALMENTE REFUTADA**: docling+torch corre **PP-OCRv6 small** y **tampoco resuelve d3**. Los tres candidatos que quedan, PENDIENTES | ídem §6 |
| §5 · la regla de ppp | *«leer los ppp reales y no sobremuestrear»* | **Con su número:** `clamp(nativos, 100, nativos × 1,4)`. **Acantilado entre ×1,4 y ×1,6: 72 puntos de CER.** **Suelo 100** porque a 75 ppp RapidOCR se rompe en d2 (44,3 %) | ídem §9 R1 |
| §5 · aviso de VRAM | PaddleOCR 12 025 MiB a 600 ppp | **Ampliado:** **EasyOCR 11 877 MiB a solo 300 ppp**, a 411 MiB de agotar la tarjeta, con una página. Tabla por motor **y por resolución**. **RapidOCR: +0 MiB** | ídem §7.2 |
| §5 · PENDIENTE | «Repetir la fase 2 a ppp nativos» | **RESUELTO.** Entran en su lugar: **construir `escaneado_d4`**, **aislar la asimetría de PaddleOCR**, **el corpus sin tildes y el evaluador que las normaliza fuera**, y **`-deskew` × techo ×1,4** | ídem §8, §10 |
| Índice de evidencia | 12 filas | **+4 filas**: los cuatro informes nuevos | — |

### 1.2 `PLAN-ORQUESTADOR.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | Fecha 19/08 | **Última revisión 21/08 03:30**, con la lista de secciones tocadas | — |
| **§4.2** | Cuatro puntos del contrato y su coste (0,372 ms / 145×) | **+ «El contrato son tres grupos, no dos»**: A/B/C con su coste; `min(alfa)` **66,0 ms** peor caso y **÷4,8** si se cachea por entrada; **sin grupo B el punto 4 devuelve `ok_parcial`, no aprueba**; formatos «no evaluable»; **74 líneas (4,8 %) de excepciones** | `verificador-fidelidad.md` §1-§3, §6 |
| §4.2 (nuevo) | — | **Un hueco del contrato que no se cierra con un quinto punto:** entrada envenenada en sitio → salida coherente + `returncode 0`. **La defensa es hashear la entrada en el staging** | `mcp-cabos-sueltos.md` §5.6 |
| **§4.4** | «Anotadas con `readOnlyHint`/`destructiveHint`» | **+ lo que eso compra hoy: nada del lado del modelo.** Solo cruzan `description` e `inputSchema`; **no cruzan** anotaciones, `title`, `_meta`, `outputSchema` ni `icons`, **y no cambian el permiso** | ídem §1.2 |
| §4.4 (nuevo) | Presupuesto ≤1.200 tokens | **+ ×2,0–2,6 por petición** (tabla de los dos modelos), **+ cada parámetro con `description`** (0 de 193 en las referencias), **+ la cobertura como requisito de seguridad** con sus cuatro consecuencias, **+ que no hay degradación por catálogo grande** | `saturacion-herramientas.md` §3.5, §3.6, §5.4, §7 |
| **§4.5** | Presupuesto de VRAM por motor | **+ presupuesto por motor Y por resolución** (tabla), **+ la regla de ppp con techo y suelo**, **+ `OcrOptions.scale` explícito** (defecto 3,0 → **216 ppp fijos**), **+ extraer sin rasterizar**, **+ selección de motor por caso (R3)** | `ocr-ppp-nativos.md` §7.2, §9 |
| **§4.6 · R7** | «Resolver enlaces en cada llamada» | **+ `O_NOFOLLOW` + `dir_fd` en Linux**, y que **en Windows no existen** — complemento, **nunca sustituto del staging** | `mcp-cabos-sueltos.md` §5.5 |
| **§4.6 · R8** | «La ventana dura minutos» (supuesto) | **Ventana MEDIDA: 99,6 % de la conversión**; **el vector correcto es escribir EN SITIO**, no sustituir; **precio 0,1 %-19,6 %**; **staging inmediatamente después de validar** | ídem §5.1-§5.3 |
| **§4.6 · R8 (excepción)** | Sin excepciones | **EXCEPCIÓN EXPLÍCITA PARA `inspect`**, con la tabla: sobre 122 MB el staging cuesta **1,32×** la operación; punto de cruce **~90-100 MB**. **La salida correcta es leer metadatos en proceso** | ídem §5.4 |
| **§4.6 · R13** | «Implementable; `Resolve(ListRoots)` aborta» | **IMPLEMENTADA**: ocho líneas, 4 configuraciones + cliente real. **Cachear los roots por sesión es trabajo del servidor** | ídem §2 |
| **§5 (tabla de reglas)** | Una fila de ppp | **Tres filas**: `clamp` con techo y suelo · **fijar `OcrOptions.scale` siempre** · **VRAM por motor y por resolución** | `ocr-ppp-nativos.md` §9 |
| **§5.1** | «El orden importa» como nota | **Resultado causal A/B**: `stdin` heredado **2/5**, `stdin=DEVNULL` **0/5**, con `-y` en todas partes y rutas nuevas. **La tubería que lo dispara es la del JSON-RPC.** Alcance **6 de 26** + AST. **`taskkill /F /T` no alcanza al nieto** | `mcp-cabos-sueltos.md` §4.3, §4.4 |
| **§5.3** | «**PENDIENTE:** medir `mcp 2.0.0` contra clientes reales» | **MEDIDO. Claude Code 2.1.238 negocia `2025-11-25`, no `2026-07-28`**: `list_roots()` funciona, `Resolve` usa la vía clásica y **el cuerpo NO corre dos veces**. La idempotencia **sigue siendo necesaria, ya no urgente**. **+ el `⏸ Pending approval` que un `filex init` no puede evitar** | ídem §1.1, §1.5, §1.6 |
| **§6 · trampa 10** | «Rasterizar a ppp fijos es un error de medición» | **+ matiz para no sobrecorregir:** el artefacto **no afecta por igual**; «a ppp nativos siempre es mejor» **es falso como regla general**; lo que siempre es cierto es más rápido (×1,48–3,13) y más barato en VRAM | `ocr-ppp-nativos.md` §4, §7.3 |
| **Hito 6** | Aviso de VRAM de PaddleOCR | **+ EasyOCR a 300 ppp**, **+ que el criterio «distancia de edición 0» ya se cumple en 3 de 4 documentos** y lo que no se cumple es d3 | ídem §7.2, §3 |
| **§9 (referencias)** | 20 filas | **+4**: `ocr-ppp-nativos.md` como **la referencia buena de OCR**, `verificador-fidelidad.md`, `saturacion-herramientas.md`, `mcp-cabos-sueltos.md`. Y `00-mcp-patrones.md` pasa a **«al día»** | — |

### 1.3 `RESULTADOS-MCP.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | «Fase 1 y 2 completadas» | **+ «Fase 3 (cabos y conducta) integrada»**, con lo que cierra | — |
| **§2 · pregunta 2** | «**RESPONDIDA A MEDIAS**. PENDIENTE el efecto en la elección» | **CERRADA**, con la tabla de 540 ejecuciones, el contraste A/C, el par «peor» que acertó **30 de 30**, y **lo que el experimento no demuestra** | `saturacion-herramientas.md` |
| **§2 · pregunta 6** | 0,93 tok/B | **+ el coste del `ImageContent` nativo por píxel** (2.814 tok) y el PNG 1×1 que devolvió error de la API de visión | `mcp-cabos-sueltos.md` §1.3 |
| **§4** | Catálogos en tokens | **+ el multiplicador ×2,0–2,6** con su tabla, **+ el tercer dato incómodo: 0 de 193 parámetros lleva `description`** | `saturacion-herramientas.md` §3.6, §5.4 |
| **§8.1** | «Reproducido end-to-end en **una**; el resto PENDIENTE» | **6 de 26**, clasificación **por AST**, **554-695 ms frente a infinito**, y el bloque nuevo **«`-y` es necesario y NO suficiente»** con el A/B | `mcp-cabos-sueltos.md` §4 |
| **§9.1** | «Anotar … ventaja diferencial real» | **MATIZADA**, con puntero a la §9.4 nueva | ídem §1.2 |
| **§9.4 (nueva)** | — | **Tabla de lo que cruza y lo que no** hasta el modelo, la denegación de permiso pese a `readOnlyHint`, y que **`structuredContent` no compra nada** | ídem §1.2, §1.4 |
| **§10 · R7, R8, R13** | R13 «PENDIENTE verificar `list_roots()`»; R8 sin excepciones | **R13 CERRADA**; **R8 con ventana, mecanismo, precio y la excepción de `inspect`**; **R7 con las primitivas POSIX y su límite en Windows** | ídem §2, §5 |
| **§12.1 (nueva)** | — | **Las 12 correcciones de `mcp-cabos-sueltos.md` §6, una a una, con dónde se aplicó cada una** | ídem §6 |
| §12 (nota) | Contradicción abierta con `00-mcp-componentes.md` §3.5 | **Se mantiene abierta** y se añade que el recuento nuevo (7.886 / 2.306) queda a **1 %** de §4: **la discrepancia con componentes es de orden de magnitud, no de tokenizador** | `saturacion-herramientas.md` §2.2 |
| **§13** | Tabla de **6 pendientes**, 5 de ellos ya cerrados | **Reescrita en dos partes: §13.1 los cinco cerrados** (con su resultado) **y §13.2 lo que sigue abierto**, incorporando la lista propia de `mcp-cabos-sueltos.md` §7 y la de `saturacion-herramientas.md` §8 | los dos |
| §14 (índice) | `00-mcp-patrones.md` «**pendiente de las correcciones de §12**» | **«al día»**, y **+3 filas** con los informes y salidas nuevos | — |

### 1.4 `ANALISIS-COMPLETO.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| §1 · tabla de diferenciadores | Difer. 3: «⏳ el efecto de un catálogo grande sobre la elección» | **«✅ saturación resuelta (21/08) y REFUTADA: 27 herramientas eligieron mejor que 8»** | `saturacion-herramientas.md` §6 |
| §1 · «Qué queda pendiente de medir» | 11 filas, 4 de ellas ya resueltas | **Actualizada**: se cierran la saturación, la repetición de la fase 2 y `min(alfa)`; **entran** el riesgo de fallos silenciosos, el `d4`, la asimetría de PaddleOCR y los pendientes de fidelidad. Los punteros a `AGENTES-PRUEBAS-PENDIENTES.md` pasan a `ESTADO-Y-REPARTO.md` | los cuatro |
| **§5.5 · tabla de OCR** | Tres motores con **las dos columnas de CER tachadas** | **Tabla canónica de cuatro motores a ppp nativos**; aceleración y VRAM en tabla aparte, con el aviso de que **la VRAM ya no vale como presupuesto**. **+ nota de que el 57,0 % de EasyOCR era su lectura de CPU y el 59,5 % la de GPU** | `ocr-ppp-nativos.md` §3, §2 |
| §5.5 · la corrección | «Las cifras publicadas miden un ×2 de interpolación» | **+ la tabla de artefacto por motor** y los dos matices (d2 cero, d3 un solo motor), **+ «a ppp nativos siempre es mejor» es falso como regla general** | ídem §4 |
| §5.5 · asimetría | «RapidOCR mejor caso 53,2 %, límite de modelo v5 mobile» | **65,8 %**, y **explicación parcialmente refutada** (hay un v6 en el lado que falla) | ídem §6, §8 |
| §5.5 · consecuencia | «Leer los ppp y no sobremuestrear» | **+ el `clamp` con techo ×1,4 y suelo 100**, con el acantilado de 72 puntos | ídem §9 |
| §5.5 · VRAM | PaddleOCR 12 025 MiB a 600 ppp | **+ EasyOCR 11 877 MiB a 300 ppp** y **el presupuesto por motor Y por resolución** (el +2 079 MiB subestima casi 5×) | ídem §7.2 |
| §5.5 (nuevo) | — | **El corpus ya no mide dificultad: mide selección de motor.** Hace falta un `d4`. **PENDIENTE** | ídem §8 |

### 1.5 `analysis/00-mcp-patrones.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | «Las correcciones 4 y 5 de §12 están aplicadas» | **«AL DÍA»**, con las 12 de `mcp-cabos-sueltos.md` §6 (las nueve que le tocan: 1, 2, 3, 5, 6, 7, 9, 10 y 11) y **las dos que más cambian el diseño destacadas** | `mcp-cabos-sueltos.md` §6 |
| **Regla 1** | «0,93 tokens/byte, umbral 1-2 KB» | **+ el `ImageContent` nativo cuesta por píxel** (2.814 tok, predicción `w×h/750` = 2.765). **×14 más barato que el encubierto y ×39-88 más caro que la ruta** | ídem §1.3 |
| **Regla 2** | «Anotar … es ventaja diferencial» | **Corregida:** las anotaciones **no llegan al modelo ni cambian el permiso**; tabla de lo que cruza; **la advertencia va en la `description` y la defensa en el núcleo**. **+ `structuredContent` tampoco compra nada** | ídem §1.2, §1.4 |
| **Regla 5** | «docling-mcp con más de 10 herramientas **empieza a saturar la selección**» | **Corregida y refutada con 540 ejecuciones:** 27 acertó **100 %/98 %**, 8 acertó **85 %/77 %**. **La regla sobrevive con su justificación cambiada: pocas herramientas por COSTE**, con el multiplicador ×2,0–2,6 | `saturacion-herramientas.md` §3, §6 |
| **Regla 6 (nueva)** | — | **`stdin=DEVNULL` en la construcción del proceso, y es LA defensa**: A/B **2/5 frente a 0/5** con `-y` en todas partes. **+ el inventario de procesos, porque `taskkill /F /T` no alcanzó al nieto** | `mcp-cabos-sueltos.md` §4.3, §4.4 |
| **Regla 7 (nueva)** | — | **La cobertura declarada es requisito de seguridad**: fallos silenciosos 15–17 %, `list_targets` como mecanismo, `convert` que falla explícito, descripciones que declaran límites, **`description` en cada parámetro** (0 de 193), y la **prueba de abstención** | `saturacion-herramientas.md` §3.5, §5.4, §7.2 |
| Sección nueva | — | **«El antipatrón de contenido encubierto está PROTEGIDO POR TESTS»**: 117 tests / 6,43 s / 0 fallos, **75 de 117 (64 %) prueban las nubes y solo 13 la conversión**, el prefijo `data:image/…;base64,`, el criterio de aserción a copiar (`sharp.test.ts:369-380`) y **el fallo que ni él atrapa** (`fs.writeFileSync` mockeado) | `mcp-cabos-sueltos.md` §3 |

### 1.6 `AGENTES-PRUEBAS-PENDIENTES.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | Documento de traspaso vigente | **⛔ SUPERADO por `ESTADO-Y-REPARTO.md`**, con las tres cosas que hay que saber, dónde está cada pieza vigente, y **qué de él sigue siendo útil** (las fichas técnicas de cada motor). **No se reescribe el resto** | `ocr-ppp-nativos.md` §3, §8 |
| §1 · la justificación | «en d3 **fallaron los tres motores**: 65,8 / 75,9 / 57,0 %» | **Tachado y marcado FALSO**, con el motivo (×2 de interpolación) y el dato que lo sustituye (**PaddleOCR 2,5 %**) | ídem |

---

## 2. Lo que este trabajo cierra, en cifras

| | Antes | Ahora |
|---|---|---|
| Pendientes de `RESULTADOS-MCP.md` §13 | 6 abiertos | **1 abierto de los originales** (symlinks en Linux) + 6 nuevos que abrieron los informes |
| Pendientes de píxeles de `HUECOS.md` §1 | 2 abiertos | **0** (y 6 nuevos, todos acotados y con estimación de coste) |
| Preguntas transversales de `RESULTADOS-MCP.md` §2 | 5 cerradas de 6 | **6 de 6** |
| `analysis/00-mcp-patrones.md` | «pendiente de las correcciones de §12» **desde el 20/08** | **al día**, con 2 reglas nuevas |
| Tabla de OCR vigente | `gpu-fase2.md` §5, con dos columnas tachadas | **`ocr-ppp-nativos.md` §3**, 4 motores, 296 celdas deterministas |

**Tres tesis del proyecto quedaron refutadas por estos informes, y las tres están ya en los maestros:**

1. **«Un catálogo de 27 herramientas satura la elección»** → 27 eligió **mejor** que 8 (540 ejecuciones, dos modelos).
2. **«`-y` basta contra el deadlock de ffmpeg»** → `stdin` heredado cuelga **2/5** con `-y` en todas partes.
3. **«El vector TOCTOU es sustituir el fichero»** → no funciona **en ninguna** de las dos plataformas; el que funciona es **escribir en sitio**.

---

## 3. Lo que se decidió NO tocar, y por qué

- **`bench/gpu-fase2.md`** — es un informe de `bench/`, y su aviso de cabecera es de otro carril. **El matiz en dos sentidos se ha escrito en `HUECOS.md` §5 y `ANALISIS-COMPLETO.md` §5.5**, que son los documentos que se leen al decidir. El aviso de `gpu-fase2.md` **no es incorrecto**: es demasiado amplio en d2 y demasiado poco específico en d3, y así queda dicho en los maestros, con el puntero a `ocr-ppp-nativos.md` §4.
- **`analysis/00-mcp-componentes.md`** — su §3.5 sigue citando ≈3.610 / ≈811 tokens frente a los 7.964 / 2.322 medidos. **No es fichero de este encargo** y la contradicción ya estaba declarada en `RESULTADOS-MCP.md` §12; se le ha añadido que el recuento nuevo confirma la magnitud de §4.
- **`bench/scripts/verificador.py`, `corpus/` y los informes de `bench/`** — de otros agentes en vuelo (V1, G1, E1). Leídos, no escritos.
- **El cuerpo de `AGENTES-PRUEBAS-PENDIENTES.md`** — el encargo pedía marcarlo, no reescribirlo. Sus fichas de motor siguen siendo útiles y su historia intelectual vale más entera que corregida.

---

## 4. Contradicciones detectadas: se escriben, no se resuelven

**Ninguna de las cuatro se ha resuelto eligiendo un lado.** Dos estaban ya cerradas por los propios informes y se recogen como tales; dos siguen abiertas.

| # | Qué choca | Los dos sitios | Estado |
|---|---|---|---|
| 1 | **PaddleOCR: ¿PP-OCRv5 o PP-OCRv6?** | `bench/ocrmypdf.md` §3.4 dice **v6 medium** · `bench/gpu-fase2.md` §5 etiqueta **v5** | **CERRADA por `ocr-ppp-nativos.md` §6**, por inspección de `C:\Users\krato\.paddlex\official_models\` y de los parámetros del objeto en caliente: **v6 medium**. `ocrmypdf.md` acierta, `gpu-fase2.md` se equivoca |
| 2 | **Docling con `backend="torch"`: ¿PP-OCRv4 o PP-OCRv6 small?** | `bench/ocrmypdf.md` §3.4 dice que **cae a v4** · `bench/ocr-ppp-nativos.md` §6 mide **v6 small** | **CERRADA a favor de `ocr-ppp-nativos.md`**, con la matriz backend × idioma: docling resuelve **primero por idioma**; v4 solo aparece con `torch` **y** un idioma fuera del conjunto v6. **Queda anotado que `ocrmypdf.md` §3.4 propaga un error** |
| 3 | **EasyOCR en d3: ¿57,0 % o 59,5 %?** | `bench/gpu-fase2.md` §3 (tabla) y su aviso de cabecera citan **57,0 %** · `bench/ocr-ppp-nativos.md` §2 reproduce **59,5 %** y lo marca ✔ | **No es un choque: son dos medidas distintas de la misma casilla.** 57,0 % es la lectura **de CPU** y 59,5 % la **de GPU** — `gpu-fase2.md` §3 ya documenta que **EasyOCR no es determinista entre CPU y GPU sobre d3**. **Anotado en `ANALISIS-COMPLETO.md` §5.5**, porque las tablas de los maestros arrastraban el 57,0 % sin decir de dónde salía |
| 4 | **Tokens de catálogo: ¿7.964/2.322, 7.886/2.306, o ≈3.610/≈811?** | `RESULTADOS-MCP.md` §4 mide **7.964 / 2.322** · `saturacion-herramientas.md` §2.2 recuenta **7.886 / 2.306** · `analysis/00-mcp-componentes.md` §3.5 estima **≈3.610 / ≈811** | **Parcialmente cerrada.** La diferencia entre las dos primeras es **1 %, por serialización**, y la proporción es idéntica: **irrelevante**. La tercera es de **orden de magnitud** y **sigue abierta**: mide otra cosa o con otro tokenizador. **Las cifras vigentes son las de `RESULTADOS-MCP.md` §4.** El fichero es de otro carril y no se ha tocado |

**Y una tensión que no es contradicción pero conviene no perder:** `ocr-ppp-nativos.md` §0.3 refuta explícitamente una frase que este proyecto había empezado a dar por buena —«a ppp nativos siempre es mejor»— **incluyendo la del propio encargo que lo generó** («una decisión sin contrapartidas»). La contrapartida existe, está acotada, y su propio informe la escribe: **la decisión es correcta; el argumento «sin contrapartidas» no lo es.** Eso está trasladado literalmente a `PLAN-ORQUESTADOR.md` §6 (trampa 10) y a `HUECOS.md` §5.

---

## 5. El commit — preparado, **NO ejecutado**

**No se ha hecho `git add` ni `git commit`.** Lo que sigue es la lista para ejecutarlo.

### 5.1 Aviso previo: el árbol ha cambiado mientras corría este agente

`git status` al empezar declaraba 11 modificados y 8 sin versionar. **Ahora hay más, porque G1, V1 y E1 están trabajando en paralelo.** La lista de abajo **incluye solo lo que es de este encargo y lo que está terminado**; lo de los otros agentes se deja fuera **a propósito**, para que cada uno cierre el suyo.

### 5.2 Qué INCLUIR

**Documentos maestros (los cinco que toca este agente, más los que ya venían modificados de la tanda anterior):**

```
ANALISIS-COMPLETO.md
HUECOS.md
PLAN-ORQUESTADOR.md
RESULTADOS-MCP.md
AGENTES-PRUEBAS-PENDIENTES.md
ESTADO-Y-REPARTO.md            (sin versionar; es el documento que sustituye al anterior)
analysis/00-licencias.md
analysis/00-mcp-componentes.md
analysis/00-mcp-filesystem.md
analysis/00-mcp-patrones.md
analysis/OCRmyPDF.md
bench/gpu-fase2.md
```

**Los cuatro informes nuevos y este:**

```
bench/verificador-fidelidad.md
bench/mcp-cabos-sueltos.md
bench/saturacion-herramientas.md
bench/ocr-ppp-nativos.md
bench/consolidacion-21ago.md
```

**Los cuatro directorios de salidas — enteros. Son 100 % texto y pesan 1,7 MB:**

| Directorio | Ficheros | Tamaño | Composición |
|---|---:|---:|---|
| `bench/salidas-mcp-cabos/` | 75 | 191 KB | `.py`, `.json`, `.jsonl`, `.log`, `.txt`, `mcp.json.bak` |
| `bench/salidas-ocr-ppp/` | 341 | 334 KB | 296 `.txt` de OCR, 12 `.json`, 15 registros, `tablas.md`, `MANIFIESTO.md` |
| `bench/salidas-saturacion/` | 26 | 1.038 KB | arnés, catálogos, `grid_*.jsonl` (420 y 214 KB) y puntuaciones |
| `bench/salidas-verificacion-fidelidad/` | 13 | 143 KB | `medir_fid.py` y los 6 pares `.json`/`.txt` que son la fuente de cada sección |

**Inventario por extensión de los cuatro juntos: 337 `.txt` · 45 `.json` · 31 `.py` · 19 `.log` · 8 `.md` · 6 `.jsonl` · 6 `.sh` · 2 `.err` · 1 `.bak`. Cero binarios. Total 1,7 MB.**

> **Por qué entra todo:** es exactamente lo que `CLAUDE.md` §6 manda versionar —los `.md`, los scripts, los `.json` de resultados y **los logs**—. Los dos ficheros grandes (`grid_haiku.jsonl` 420 KB y `grid_sonnet.jsonl` 214 KB) son **los datos crudos de las 540 ejecuciones, una línea por ejecución con su secuencia de herramientas y argumentos**: son la trazabilidad entera del informe que refuta la tesis de saturación, y son texto.
>
> **Y los cuatro informes ya hicieron la limpieza que les tocaba**, cada uno documentada: `salidas-ocr-ppp` retiró **41,0 MiB de PNG** y dejó su `MANIFIESTO.md`; `salidas-mcp-cabos` borró **515 MB** de directorios de trabajo y quedó en 338 KB; el `node_modules` de `image-worker-mcp` (**177,3 MB**) se quedó dentro de `repos/`, que está en `.gitignore`.

### 5.3 Qué EXCLUIR

| Qué | Por qué |
|---|---|
| **`bench/.gpu.lock`** | Estado de ejecución, no evidencia. **Nunca se versiona**, y ahora mismo puede estar tomado por otro agente. **Añadirlo a `.gitignore`** |
| **`bench/salidas-corpus-d4/`, `corpus/pdf/escaneado_d4*.pdf`** (6 ficheros, 85-149 KB) | **Trabajo en curso del agente G1.** Además, `corpus/**/*.pdf` va por **Git LFS** (`.gitattributes`): hay que asegurarse de que LFS los toma antes de commitear, y eso lo decide quien los generó, con su `MANIFIESTO.md` |
| **`bench/salidas-verificador-gs/`** y los cambios de `bench/scripts/verificador.py` | **Trabajo en curso del agente V1**, que es el único que toca ese fichero. *(Nota: `verificador.py` sale como modificado desde antes, por las 1.542 líneas de `verificador-fidelidad.md`; si V1 no ha terminado, conviene esperar a que cierre en vez de partir su trabajo en dos commits.)* |
| **`bench/salidas-aristas/`** | **Trabajo en curso del agente E1** |
| **`chunk-stream0-00001.m4s`, `chunk-stream1-00001.m4s`, `init-stream0.m4s`, `init-stream1.m4s`** (2-5 KB) | **Basura ajena al proyecto** en la raíz del repositorio: fragmentos DASH, probablemente de una descarga del navegador. **No commitear.** Borrar o ignorar |
| **`o0478_map.shtml`, `o0479_map.shtml`** (0 KB) | Ídem: ficheros de 0 bytes ajenos al repositorio, en la raíz |
| Cualquier salida binaria regenerable | `CLAUDE.md` §6. El repositorio ya pagó una vez **986 MB de pack, 99,9 % binario** |

### 5.4 Orden propuesta

```bash
git add ANALISIS-COMPLETO.md HUECOS.md PLAN-ORQUESTADOR.md RESULTADOS-MCP.md \
        AGENTES-PRUEBAS-PENDIENTES.md ESTADO-Y-REPARTO.md \
        analysis/00-licencias.md analysis/00-mcp-componentes.md \
        analysis/00-mcp-filesystem.md analysis/00-mcp-patrones.md analysis/OCRmyPDF.md \
        bench/gpu-fase2.md \
        bench/verificador-fidelidad.md bench/mcp-cabos-sueltos.md \
        bench/saturacion-herramientas.md bench/ocr-ppp-nativos.md \
        bench/consolidacion-21ago.md \
        bench/salidas-mcp-cabos/ bench/salidas-ocr-ppp/ \
        bench/salidas-saturacion/ bench/salidas-verificacion-fidelidad/

git status --short          # comprobar que NO entra nada de los otros tres agentes
git diff --cached --stat    # comprobar que no entra ningún binario
```

### 5.5 Mensaje propuesto

```
Cuatro mediciones nuevas y la consolidación de los maestros

Integra en HUECOS.md, PLAN-ORQUESTADOR.md, RESULTADOS-MCP.md,
ANALISIS-COMPLETO.md y analysis/00-mcp-patrones.md los cuatro informes
del 21 de agosto. Tres tesis del proyecto quedan refutadas.

- Saturacion del catalogo (540 ejecuciones, dos modelos): 27 herramientas
  acertaron 100 %/98 % y 8 acertaron 85 %/77 %. El catalogo grande eligio
  MEJOR. El objetivo de 4 herramientas se sostiene solo por coste, y el
  coste es peor de lo que se creia: el catalogo se paga x2,0-2,6 por
  peticion. Aparece un riesgo nuevo en direccion contraria: un catalogo
  escueto produce fallos silenciosos (15-17 %), lo que convierte la
  cobertura declarada de convert en requisito de seguridad.

- OCR a ppp nativos: tabla canonica de 4 motores, 296 celdas deterministas.
  Sustituye a la de gpu-fase2.md §5. El aviso de aquel informe se matiza
  en dos sentidos: en d2 el artefacto es cero (el 43,0 % de EasyOCR es
  real) y en d3 es de un solo motor (los 73,4 pp son todos de PaddleOCR;
  para RapidOCR y docling+torch los 200 ppp eran su MEJOR resultado).
  Regla medida: clamp(nativos, 100, nativos x 1,4), con un acantilado de
  72 puntos de CER entre x1,4 y x1,6. VRAM por motor Y por resolucion:
  EasyOCR pasa de 5 026 a 11 877 MiB entre la imagen extraida y 300 ppp.

- Verificador hasta la fidelidad: min(alfa) en proceso cuesta 66,0 ms en
  el peor caso y en 7 de 12 casos no lee un pixel. La fidelidad cuesta
  x1.106 el contrato y el 38,5 % de convertir: va fuera del camino
  caliente. El contrato queda separado en tres grupos.

- Cabos MCP: las anotaciones readOnlyHint/destructiveHint NO llegan al
  modelo (solo cruzan description e inputSchema). -y es necesario y NO
  suficiente contra el deadlock: stdin heredado cuelga 2/5, stdin=DEVNULL
  0/5. El vector TOCTOU que funciona no es sustituir el fichero sino
  escribir en sitio, en Windows y en Linux. R8 gana una excepcion
  explicita para inspect, donde el staging cuesta 1,32x la operacion.
  Claude Code negocia 2025-11-25, no 2026-07-28.

RESULTADOS-MCP.md §13 pasa de 6 pendientes a 1 de los originales;
analysis/00-mcp-patrones.md deja de estar pendiente de correcciones;
AGENTES-PRUEBAS-PENDIENTES.md queda marcado como superado por
ESTADO-Y-REPARTO.md, porque su justificacion ("en d3 fallaron los tres
motores") es falsa.

Salidas: 1,7 MB, 100 % texto, cero binarios. Los informes ya retiraron
41,0 MiB de PNG y 515 MB de directorios de trabajo, con MANIFIESTO.
```

---

## 6. Cómo verificar este informe

**Todo lo de arriba es reconciliación de texto, no medición.** La forma de comprobarlo es abrir los dos lados:

| Para comprobar | Abrir |
|---|---|
| Que ninguna cifra es inventada | Cada fila de §1 lleva la sección exacta del informe de origen |
| Que la tabla canónica es la que dice | `bench/ocr-ppp-nativos.md` §3 y `bench/salidas-ocr-ppp/tablas.md` |
| Que las 540 ejecuciones existen | `bench/salidas-saturacion/grid_haiku.jsonl` y `grid_sonnet.jsonl`, una línea por ejecución |
| Que el A/B del deadlock es causal | `bench/salidas-mcp-cabos/cabo4_stdin_ab.json` |
| Que `min(alfa)` cuesta lo que dice | `bench/salidas-verificacion-fidelidad/alfa.json` |
| Que las 12 correcciones están aplicadas | `RESULTADOS-MCP.md` §12.1, fila a fila |
