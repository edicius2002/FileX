# Segunda consolidación del 21 de agosto — qué decía cada maestro y qué dice ahora

**Agente D2.** 21 de agosto de 2026, 10:00. **Sin GPU, sin mediciones nuevas: este informe no mide nada, reconcilia.** Continúa donde lo dejó `bench/consolidacion-21ago.md` (agente D1), que cerró antes que otros tres agentes y **cuyo trabajo estos corrigen en dos puntos**.

**Fuentes integradas** — los tres informes que quedaron fuera de la primera pasada:

| Hora | Informe | Qué aporta |
|---|---|---|
| 09:10 | `bench/corpus-d4.md` (G1) | **`escaneado_d4`** y **la causa real de la asimetría de PaddleOCR**; el techo absoluto de ppp; dos refutaciones CPU/GPU |
| 09:20 | `bench/aristas-nominales.md` (E1) | **El 50,5 %** de aristas nominales (cierra el hueco 2); el **quinto punto del contrato**; el caso de `resvg`; 5 de los 7 `no_evaluable` |
| 09:40 | `bench/verificador-ghostscript.md` (V1) | **El OCR sin GPU**; `min(alfa)` de TIFF/GIF/Adam7; V2 y su coste; `P9`; **el segundo testigo de ruido** |

**Regla que gobernó el trabajo, la misma que la primera pasada:** ni una cifra inventada. Cada número movido a un maestro está **literalmente** en uno de los tres informes y se cita con fichero y sección. Donde dos documentos se contradicen, **no se elige: se escribe la contradicción y se señalan los dos sitios** (§3).

---

## 0. Lo que hay que leer si solo se leen diez líneas

1. **El contrato de cuatro puntos —el argumento nº 1 del proyecto— tiene por primera vez un caso que no atrapa.** `resvg 0.46.0` devuelve `rc=0`, un PNG válido, con la geometría exacta pedida y **sin una sola letra**. Es el **octavo** fallo del catálogo de `HUECOS.md` §1 y el primero cualitativamente distinto. **Está escrito como refutación, no como nota al pie.**
2. **Y el contrato gana un quinto punto:** hay motores que **escriben fuera del destino** (`ffmpeg -i x out.mpd` deja 528 KB de segmentos DASH en el `cwd`). El confinamiento pasa a ser **un directorio de trabajo desechable**, no solo una ruta validada.
3. **El hueco 2 se cierra con cifra: 50,5 %** de aristas declaradas verificables que no existen — **pero el estrato que el multi-salto usa de verdad sale al 3,0 %**, y los dos hechos van juntos o la cifra engaña.
4. **La ventaja de PaddleOCR era un defecto de RapidOCR:** seis números de normalización valen **72,2 puntos de CER**. Con ellos, **un solo motor cubre el corpus entero y funciona en CPU**.
5. **Se corrige a D1:** el techo `×1,4` que escribió en `PLAN-ORQUESTADOR.md` §4.5 hace **16,9 puntos de daño** sobre un original de 200 ppp. Pasa a **absoluto (200)**, y **PENDIENTE de barrer la curva**.

---

## 1. La tabla de cambios

### 1.1 `HUECOS.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | Tres revisiones (19/08, 21/08 00:32, 21/08 03:30) | **Cuarta revisión (21/08, 10:00)**, con las tres cosas que cambian de estatus | los tres |
| Resumen del reordenamiento | Difer. 1 «el más fuerte» · Difer. 2 «multi-salto refutado» | **+ «con su frontera medida: el contrato no atrapa el octavo fallo»** · **+ «reforzada: 50,5 % global pero 3,0 % en el estrato PDF»** | `aristas-nominales.md` §8.2, §0, §6 |
| **§1 · tabla de fallos** | **7** fallos en **6** proyectos | **8 fallos en 7 proyectos**: entra `resvg 0.46.0` con **0,00 % de tinta en la banda de texto** frente al 14,02 % de Inkscape y el 15,07 % de `magick` | ídem §8.2 |
| **§1 (bloque nuevo)** | — | **«El octavo es el primero que el contrato NO atrapa»**, con la tabla de los tres rasterizadores, la frontera (*el contrato juzga la declaración; el contenido que desaparece necesita fidelidad*) y la regla que lo atraparía, con su coste estimado (~26 ms del grupo C). **PENDIENTE** | ídem |
| **§1 (bloque nuevo)** | — | **«El quinto punto del contrato: hay motores que escriben fuera del destino»**, con las tres órdenes reproducidas, los tres corolarios y el enlace a R18 | ídem §5.2 |
| §1 · prototipo | **3.035 líneas**, 5/5 fallos, 0 FP | **3.859 líneas** (+824), **0 FP en las seis configuraciones y 12/12 fallos**. + la cobertura nueva de `min(alfa)` (36/36 contra `magick`), **el atajo de fila opaca como condición y no optimización**, y **el fallo preexistente de la coordenada byte/píxel que hacía que I3 leyera otro píxel** | `verificador-ghostscript.md` §1, §2, §3, §6 |
| §1 · coste del grupo C | Fidelidad **28.858 ms**, 38,5 % de convertir | **46.332 ms (+60,6 %)**, **61,9 %** de convertir; **16.592 ms son solo V2**. **V2 necesita su propio interruptor** | ídem §2.2 |
| **§1 · PENDIENTE** | 6 abiertos (TIFF/GIF, Adam7, V2/V5, VP8L, OCR de gs, los 7 `no_evaluable`, entrada envenenada) | **Cuatro cerrados**, con el coste real (**×2,9 y ×3,6 sobre lo estimado**) y **5 de 7 `no_evaluable` cerrados** (quedan `qpdf` y `tesseract`). **+8 nuevos**: quinto punto, regla de fidelidad del texto rasterizado, interruptor de V2, validar `P9`, `ocr: true` en el `pedido`, vocabulario de firmas (24 nombres → **12 % de destinos evaluables**), `D3/D6/D7`, el `txtwrite` vacío no reproducido, y los parámetros de I1 | ídem §7 + `aristas-nominales.md` §8, §11.3 |
| **§2 · PENDIENTE «cuántas de las 138.501 aristas son nominales»** | *«sondearlas todas es la medición que cerraría el hueco del todo»* | **CERRADO.** **50,5 %** [48,2–53,0] sobre 62.487 aristas (45,1 % de la población); escenarios **22,8 / 48,6 / 77,5 %**; **cota inferior declarada**; el método (censo de 1.104 semiaristas en 9 min 35 s + muestra n=498); **la tasa por estrato, factor 18**; y **el estrato PDF al 3,0 %** con su lectura: **refuerza `fidelidad-caminos.md`, no lo contradice** | `aristas-nominales.md` §0, §4, §5, §6 |
| §2 (nuevo) | — | **Los 12 DEGRADADO del estrato PDF son once veces la regla P7**: `imagen → pdf` funciona y **nadie declara la densidad**. Es el **defecto** de esa familia de aristas, no un caso raro | ídem §6 |
| §2 (nuevo) | — | **La unidad del grafo cambia**, con cuatro medidas independientes → **`(origen, destino, motor, parametrización, build)`** | ídem §9.2 |
| **§2 · punto 4 («`epub→png` no se puede ejecutar»)** | Gotenberg declara `.epub` y LibreOffice no lo importa | **Corregido: es una arista nominal DE UN MOTOR, no del grafo.** LibreOffice falla también en Linux (`rc=1`); **Calibre la hace bien** (26.817 B, centinela y tabla). **Obliga a revisar el criterio de aceptación del hito 1** | ídem §8.1 |
| §2 (nuevo) | «las aristas de reparación recuperan el **99,0 %** del texto» | **NO REPRODUCIDO** (no refutado): **94,7 %** con espacios normalizados, **97,1 %** ignorándolos. El orden de magnitud correcto es **94-97 %**, y la pérdida es **espacios, no letras**. **PENDIENTE** de que se publiquen los parámetros de I1 | `verificador-ghostscript.md` §5.7 |
| **§5 · la asimetría de PaddleOCR** | «Los tres candidatos que quedan, todos PENDIENTES: tamaño, idioma del reconocedor, idioma del detector» | **RESUELTA, y no era ninguna de las tres.** Tabla de las tres refutaciones + **la causa (normalización `mean=std=0,5` frente a ImageNet)** + el A/B de cinco filas + **el recuento de cajas (1 de 3 → 3 de 3)** + las cuatro consecuencias + el `LangRec.CH` que FileX usa hoy | `corpus-d4.md` §7 |
| **§5 · la regla de ppp** | Techo **×1,4** con acantilado de 72 puntos | **+ bloque «el techo relativo no se transfiere»**: sobre `d4` (200 ppp nativos) el ×1,4 **empeora a PaddleOCR 16,9 puntos**. Propuesta **`clamp(nativos, 100, 200)`**, marcada **PENDIENTE de barrer la curva**. + la confirmación de R1 desde el quinto motor (**rampa**, no acantilado, en d3) | ídem §8 + `verificador-ghostscript.md` §5.3 |
| **§5 · el OCR de Ghostscript** | «Vía que FileX obtiene casi gratis» — sin ejercitar | **EJERCITADO**, con su tabla de CER (0,0 / 0,0 / 0,0 / **165,8 %**), las cinco lecturas (VRAM 0, carga en frío 122 ms, **alucina en vez de callarse**, el tiempo como señal), **la arista de reparación de dos saltos**, **el `OK` sobre una alucinación** con `P9`, y los dos costes de integración (`osd` revienta con `0xC0000005`; 2-4 MB por idioma) | `verificador-ghostscript.md` §5 |
| §5 (nuevo) | — | **La laguna del castellano, medida**: `spa` **1,9 %**, `eng` **9,2 % leído / 15,5 % real** → el evaluador **subestima un 41 % relativo** | ídem §5.5 |
| **§5 (nuevo)** | — | **El corpus `d4`**: la tabla de siete filas, los cuatro criterios uno a uno, **las dos decisiones de diseño reutilizables** (cuatro tamaños de letra · **610 caracteres frente a 79**), el criterio (b) medido con **12 de 12 cajas y 19,30 % de CER**, lo que `d4` **no** resuelve, y **que quitar ruido empeora** | `corpus-d4.md` §2, §4, §5 |
| **§5 (nuevo)** | — | **Las dos refutaciones CPU/GPU**, con la advertencia de que **las medianas de CPU son cota superior** (sonda de carga a `-1` en 11 tandas, dos agentes midiendo en paralelo) | ídem §9, §12 |
| §5 · PENDIENTE | 10 abiertos | **Cinco cerrados** (d4, la asimetría, las tildes por dos vías, el gs en castellano, la fase 2 a nativos). **+6 nuevos**: validar la normalización fuera del corpus, barrer la curva de ppp, `-deskew` × techo, la heurística de degradación con sus dos señales candidatas, degradación realista, EasyOCR sin caso útil | los tres |
| Índice de evidencia | 16 filas | **+3**: los tres informes nuevos con sus salidas | — |

### 1.2 `PLAN-ORQUESTADOR.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | «Última revisión 21/08 03:30» | **21/08 10:00**, con **las tres cosas que cambian el diseño y no solo la documentación** enumeradas arriba del todo | — |
| **§4.1** | El multi-salto refutado, con sus cuatro pasos | **+ «La tasa de aristas nominales, MEDIDA, y lo que le hace al grafo»**: el 50,5 %, la tabla por estrato, y **tres consecuencias directas** — sondear al arrancar (**el término «+50» de la función de coste desaparece**), la arista de cinco campos, y `imagen→pdf` con densidad explícita. **+ los 20 crudos sin cabecera**: o se pasa la geometría o se borran del catálogo | `aristas-nominales.md` §4-§6, §9 |
| §4.1 | «las aristas de reparación: 99,0 % del texto» | **+ que ese 99,0 % NO se reproduce** (94,7 / 97,1 %) y por qué no se declara refutado | `verificador-ghostscript.md` §5.7 |
| **§4.2** | Contrato de **cuatro** puntos | **CINCO puntos.** Punto 5: *«nada fuera de lo declarado»*, con su sección propia, la tabla de las tres órdenes, y el enlace a **R18**. **+ el bloque de `resvg`**, que pasa los cinco y acota el contrato: *el contrato juzga la declaración; el contenido que desaparece necesita fidelidad* | `aristas-nominales.md` §5.2, §8.2 |
| §4.2 · tres grupos | Prototipo 3.035 líneas; grupo C al 38,5 % | **+ actualización**: 3.859 líneas; **el 70 % de lo añadido vuelve a ser «fabricar el acceso al dato»** (53 % → 61 % → **70 %**, tercer informe seguido); **el grupo C pasa al 61,9 % y V2 necesita interruptor**; y **la corrección byte/píxel que afectaba al veredicto de I3** | `verificador-ghostscript.md` §1.5, §2.2, §6 |
| **§4.5 · regla de ppp** | `clamp(nativos, 100, nativos × 1,4)` | **`clamp(nativos, 100, 200)` — techo ABSOLUTO**, con la tabla de la refutación, la explicación (**decide el tamaño en píxeles que llega al detector, no el factor**) y el **PENDIENTE explícito** de barrer la curva | `corpus-d4.md` §8 |
| **§4.5 · R3 (selección de motor)** | «degradación severa → PaddleOCR» | **REVISADA: pierde su motivo.** + la sección **«Fijar la normalización del detector de RapidOCR»** con el bloque de código, el A/B, el recuento de cajas y la regla general; + la tabla nueva de selección; + **los cocientes CPU/GPU por motor**; + **«CPU y GPU no dan la misma salida»** | ídem §7, §9, §10 |
| **§4.6** | «las **17** reglas» | **18.** **R18: directorio de trabajo propio y desechable por conversión**, con su evidencia | `aristas-nominales.md` §5.2, §9.7 |
| **§5 (tabla de reglas)** | 1 fila de ppp | **La de ppp reescrita a techo absoluto + 4 filas nuevas**: normalización de RapidOCR · **lista blanca de idiomas de OCR** (`osd` revienta con `0xC0000005` sin devolver error) · comprobar que el motor no escribió fuera · no presuponer que CPU y GPU coinciden | los tres |
| **§6 (trampas)** | 12 | **14.** **13 · el testigo de ruido monohilo es ciego a la contención multinúcleo** (×6,8 etiquetado `limpia`), con la calibración en reposo. **14 · un catálogo de aristas sin el `build` como dimensión miente en alguna máquina** | `verificador-ghostscript.md` §4 · `aristas-nominales.md` §9.2 |
| **§7 · hito 1** | Criterio reescrito porque `epub→png` y `epub→docx` eran inalcanzables | **Revisado otra vez, con la tabla LibreOffice/Calibre.** **Criterio nuevo y es el que discrimina: resuelve `epub→pdf` eligiendo Calibre y NO LibreOffice, y dice por qué.** `tex→docx` sigue inalcanzable en Windows y **alcanzable en el contenedor** | `aristas-nominales.md` §8.1 |
| §7 · hito 1 «objetivo mejor» | «cuando exista el sidecar de OCR» | **«Y ya no hace falta esperar al sidecar»**, con la tabla de 1 salto frente a 2 saltos y **las tres precisiones**: la arista de un salto **no existe**, d3 no se resuelve, y **hoy la arista es utilizable pero NO verificable**. + el coste de distribución de los `.traineddata` | `verificador-ghostscript.md` §5.6, §5.1 |
| **§7 · hito 6** | Aviso de VRAM y «el criterio ya se cumple en 3 de 4» | **+ «lo que este hito cambia tras el 21/08»**, con tres puntos: **la GPU deja de ser requisito**, **hay una segunda vía sin tarjeta**, y **el criterio necesita un caso nuevo (`d4`, donde nadie baja del 18,62 %)**. + el presupuesto de VRAM sobre la familia d4 | `corpus-d4.md` §9, §10, §9.5 · `verificador-ghostscript.md` §5.4 |
| **§8 · corpus** | 4 escaneados | **+ la familia `escaneado_d4{,a,b,c,e,f}`** con su tabla de para-qué-sirve-cada-uno, **las dos decisiones de diseño**, la trampa de la reproducibilidad (`-seed` sí, `SOURCE_DATE_EPOCH` no) y la de «quitar ruido empeora». **+ quinta trampa de diseño de pruebas** (el umbral de P6 no protege contra alucinaciones). **+ los dos testigos de ruido** | `corpus-d4.md` §2, §3, §12 · `verificador-ghostscript.md` §4, §5.8 |
| §9 (referencias) | 24 filas | **+3**: los tres informes, con cuándo consultarlos | — |

### 1.3 `RESULTADOS-MCP.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| **§7** | El cuarto punto del contrato y el hueco de la entrada envenenada | **+ «Un QUINTO punto, medido desde otro carril»** con la tabla de las dos órdenes y la consecuencia de confinamiento. **+ «un caso que ningún punto atrapa»** (`resvg`) | `aristas-nominales.md` §5.2, §8.2 |
| **§10** | «Las **15** reglas de confinamiento» | **«…más una decimosexta medida el 21/08»**, con **R18** y la nota de que la numeración de `PLAN-ORQUESTADOR.md` §4.6 incluye además R16/R17 | ídem |
| §12 · contradicción de tokens | «sigue abierta» | **Sigue abierta, y se dice por qué el recuento nuevo no la explica**: el factor **2,2** frente a componentes no es de tokenizador ni de serialización. Se anota **qué haría falta para cerrarla** | §4 · `saturacion-herramientas.md` §2.2 · `00-mcp-componentes.md` §3.5 |
| **§13.2** | 8 pendientes | **+3**: implementar y medir el quinto punto y R18 · la regla de fidelidad del caso `resvg` · **`qpdf` y `tesseract`, los dos motores que quedan de los siete `no_evaluable`** | `aristas-nominales.md` §5.2, §8, §9.7 |
| §14 (índice) | — | **+1 fila**: `bench/aristas-nominales.md` como origen de R18 y del quinto punto | — |

### 1.4 `ANALISIS-COMPLETO.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| §1 · difer. 1 | «7 fallos en 6 proyectos» | **«8 fallos en 7 proyectos»** + **«con su frontera medida: el octavo NO lo atrapa el contrato»** | `aristas-nominales.md` §8.2 |
| §1 · difer. 2 | Multi-salto refutado | **+ «la tasa de aristas nominales, MEDIDA: 50,5 % global, pero 3,0 % en el estrato PDF»** | ídem §0, §6 |
| §1 · pendientes | 4 filas de OCR y aristas abiertas | **Cerradas 4** (aristas nominales, `d4`, la asimetría, `min(alfa)`+V2/V5) **y abiertas 7 nuevas**: el 54,78 % indeterminado, la invocación alternativa, validar la normalización, barrer la curva, validar `P9`, el quinto punto y la regla del texto rasterizado | los tres |
| **§3.3** | Matriz de cobertura declarada | **+ el factor de descuento MEDIDO**: 16,3 % de salidas de ffmpeg muertas, 2,2 % de ImageMagick, **16,2 % de entradas de ImageMagick que no lee y son ficheros que él mismo escribió**, y **10 de los 17 nombres desconocidos son dispositivos de captura de Linux** | `aristas-nominales.md` §3, §4 |
| **§3.4** | «Una arista declarada no es una arista» | **+ «esa frase ya tiene su cifra»**: el 50,5 % con su IC, el método de semiaristas, la tabla por estrato con el **3,0 % del PDF**, y los tres hallazgos que cambian la unidad del grafo. **+ `epub→png` corregido a «con Calibre SÍ»** | ídem §0, §4-§6, §8.1, §9 |
| **§5.5** | Tabla canónica de 4 motores | **+ la nota del 57,0/59,5 % deja de ser una rareza**: «CPU y GPU dan salida idéntica» **queda refutado** (5 de 21 celdas) | `corpus-d4.md` §9.3 |
| §5.5 (nuevo) | «Hace falta un `escaneado_d4`. PENDIENTE» | **RESUELTO**, con la tabla, las dos decisiones de diseño, el criterio (b) medido con recuento de cajas, y **los 155 caracteres que esconde la métrica ciega** | ídem §2, §4, §5, §6 |
| §5.5 (nuevo) | — | **La asimetría resuelta** (las tres hipótesis refutadas + la causa + el A/B) y **la elección de motor que cambia**: un solo motor cubre el corpus y funciona en CPU | ídem §7, §10 |
| §5.5 (nuevo) | — | **El techo absoluto de ppp** y **el OCR de calidad sin tarjeta** (0,0 % en tres documentos, VRAM 0, carga en frío 122 ms, **alucina en d3**) | ídem §8 · `verificador-ghostscript.md` §5 |
| §5.5 (nuevo) | — | **«El octavo fallo de verificación, y es el primero que el contrato no atrapa»**, con la tabla de los tres rasterizadores y la nota de portabilidad Windows/Debian | `aristas-nominales.md` §8.2 |
| §8 (respaldo) | 24 filas · «corpus: 20 ficheros» | **+3 informes** · **corpus: 26 ficheros**, con la familia `d4` · «15 reglas ampliadas a **18**» | — |

### 1.5 `analysis/00-matriz-formatos.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | — | **Aviso de lectura: todo el documento es cobertura DECLARADA y ahora existe su factor de descuento medido.** Se dice explícitamente que **el documento no se corrige** —sus cifras son correctas para lo que miden— y que **ya era su propio argumento**, ahora con número | `aristas-nominales.md` §0 |
| Salvedad honesta | *«aun descontando agresivamente, el margen es enorme»* | **Tachado y sustituido**: era una intuición sin número y **los dos descuentos ya están medidos** | ídem + `fidelidad-caminos.md` |
| **Sección nueva: «El descuento medido»** | — | Cinco bloques: **(1)** la fidelidad del multi-salto (1,93×, 610 pares, 51 % vía PDF, 31,9 % aceptable); **(2)** el 50,5 % con su método y **la tabla de qué le pasa a las tablas de este documento, motor a motor**; **(3)** la tasa por estrato y **el 3,0 % del PDF que salva el argumento del grafo**; **(4)** los tres ejemplos de la tabla reejecutados; **(5)** la consecuencia de diseño y el **PENDIENTE del 54,78 %** | `aristas-nominales.md` §3-§9, §11 |

### 1.6 `CLAUDE.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| §2 · entorno | Contenedores y matices | **+ `spa.traineddata` existe por casualidad** (lo puso PDFgear) **+ el inventario de `filex-convertx`**: trae 6 de los 7 motores que faltan en Windows; **ausentes `qpdf` y `tesseract`** | `verificador-ghostscript.md` §5.1 · `aristas-nominales.md` §8 |
| **§3 · «Cómo se mide aquí»** | «Medir con ruido no es medir» | **+ una regla, no un párrafo: «Dos testigos de ruido, siempre: uno mide deriva, el otro nivel»**, con el ×6,8 etiquetado `limpia` | `verificador-ghostscript.md` §4 |
| §4 · trampas | 14 | **22**, renumeradas. Medición: **+8** (techo relativo que no se transfiere), **+9** (79 caracteres no dan gradiente), **+10** (`ocr_eval.py` ciego a tildes), **+11** (CPU ≠ GPU). Entorno: **+17** (motor y modelo de proyectos distintos), **+18** (`osd` revienta gs). Herramienta: **+21** (motores que escriben en el `cwd`), **+22** (`-seed` sí, `SOURCE_DATE_EPOCH` no) | los tres |
| §5 · reglas de diseño | «Verificar la salida siempre» con cuatro puntos | **Quinto punto** en la misma frase · **+ la frontera del contrato** (`resvg`) · **+ el directorio de trabajo desechable** | `aristas-nominales.md` §5.2, §8.2 |

### 1.7 `ESTADO-Y-REPARTO.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | Fecha 03:30 | **+ bloque «cuatro agentes han cerrado»** con la tabla de los cinco informes, qué falta por lanzar (**G2 y M1**) y el aviso de que **§5 y §6 cambian y hay que pegar la versión nueva** | — |
| §1 · informes | 10 filas | **+5** con los informes de la mañana y las dos consolidaciones | — |
| §2.2 · lo refutado | 7 filas | **11.** La de RapidOCR pasa de «parcialmente refutada» a **refutada del todo con causa**; **+5**: CPU≠GPU, el techo ×1,4, el contrato acotado por `resvg`, `epub→pdf` como nominal de un motor, y **el testigo de ruido del propio proyecto** | los tres |
| §2.3 · punto 1 | `clamp(…, nativos × 1,4)` | **`clamp(…, 200)`, techo absoluto**, con el porqué y el PENDIENTE | `corpus-d4.md` §8 |
| §2.4 | «El hallazgo incómodo, y el que motiva a G1» | **RESUELTO**, con las cuatro consecuencias y **el pendiente que deja abierto (A7: qué métrica es la canónica)** | ídem §1, §5, §6 |
| **§3 · inventario** | A1-A5, B1-B8, C1-C8 | **Reescrito.** Cerrados: **A1-A4, B1, B2, C1, C2, C3 y 5 de 7 de C8**. Abiertos: **A5 (el commit) + A7 nuevo**, **B3-B8 + B9-B12 nuevos**, **C4-C7 + C9-C18 nuevos**. Cada uno con 🔴/🟡/✅ y su origen | los tres |
| **§4 · reparto** | Tres oleadas por hacer | **Oleada 1 CERRADA**, oleada 2 con **solo E1 cerrado**, **aviso para quien lance G2 (el listón ha subido)** y **oleada 3 partida en «prioridad alta porque cambia diseño» y «prioridad normal»** | — |
| **§5 · contexto compartido** | Corpus de 4 escaneados · tabla canónica de 4 motores · `clamp(…, ×1,4)` | **Reescrito**: **+ la familia `d4`** con su para-qué · **tabla canónica de 6 filas** con las tres advertencias (el `es` vacío, gs alucina, la columna d4 es con acentos) · **el bloque de la normalización con los seis números** · **el techo absoluto** · **el bloque CPU vs GPU** · **la VRAM sobre d4** · **el aviso del evaluador ciego con las dos copias ya escritas** · **los dos testigos de ruido y el `powershell` con ruta absoluta** | los tres |
| §9 | «solo dos cosas cambiarían una decisión de diseño» | **Revisada:** las dos se midieron, **pero el cambio de diseño más grande vino de un subproducto que no estaba en el inventario**. Y **lo único con prioridad real antes de construir es ejecutar el commit** | — |
| §10 · referencias | — | **+4 filas** | — |

---

## 2. Los tres puntos que cambian el DISEÑO de FileX, no solo su documentación

*(El resto de esta consolidación es reconciliación de texto. Estos tres son código que hay que escribir distinto.)*

### 2.1 El quinto punto del contrato, y el directorio desechable

**Qué se creía:** que validar la ruta de salida bastaba, y que verificar la salida era verificar **el fichero de salida**.

**Qué se midió** (`bench/aristas-nominales.md` §5.2, reproducido de forma controlada con la invocación exacta de ConvertX):

| Orden | Escribe en el destino | Escribe **también** |
|---|---|---|
| `ffmpeg -i trivial.mp4 DEST/t.mpd` | `t.mpd` (**1 234 B**) | **`init-stream0.m4s` (814 B) y `chunk-stream0-00001.m4s` (528 447 B) en el `cwd`** |
| `magick trivial.png -auto-orient DEST/u.html` | `u.html` (506 B) **y `u.png` (329 B)** | **`u_map.shtml` (98 B) en el `cwd`** |
| `magick trivial.png -auto-orient DEST/u.map` | `u.map` (4 102 B) | — |

**Lo descubrió `git status`:** aparecieron **33 ficheros que nadie había pedido en la raíz del repositorio**.

**Qué hay que construir distinto — tres cosas:**

1. **Un quinto punto de contrato:** listar el directorio de trabajo **antes y después** de invocar al motor. Si aparece algo que no es la salida declarada, el contrato lo dice. **Coste: listar un directorio dos veces.**
2. **R18 en el confinamiento:** un **directorio de trabajo propio y desechable por conversión**, con el `cwd` del hijo dentro. **R8 y R16 asumen que el motor escribe donde se le dice, y estos dos no.** Validar la ruta de salida no cubre lo que el motor escriba en su `cwd`.
3. **La salida de una conversión puede ser varios ficheros.** `magick … out.html` entrega un HTML **y el PNG al que apunta**. Devolver solo el declarado entrega un documento roto, y una sonda que juzga **un** fichero no puede verlo.

**Y el corolario que hay que escribir con la misma franqueza:** la arista `vídeo → mpd` **pasa los cuatro puntos del contrato** —firma correcta, manifiesto DASH válido, propiedades coherentes, pedido = obtenido— y **no lleva el contenido**. El propio arnés de E1 la contó como ÍNTEGRO. **Es otra razón por la que su 50,5 % es una cota inferior.**

> **Y va con su hermano mayor, que es el hallazgo más incómodo de la jornada:** `resvg 0.46.0` devuelve `rc=0`, un PNG válido, de la geometría exacta pedida, y **sin una sola letra** — **pasa los cinco puntos**. **El contrato juzga la declaración de la salida; el contenido que desaparece sin dejar rastro en ninguna propiedad declarada solo se ve comparando la salida con la entrada, es decir, en el grupo C de fidelidad.** Eso **acota** el diferenciador nº 1 con precisión y no lo invalida: los siete fallos del sector que el contrato atrapa son fallos **por declarar de más**; este es un fallo **por entregar de menos en silencio**. Está escrito así en `HUECOS.md` §1 y en `PLAN-ORQUESTADOR.md` §4.2, que es donde se lee al construir.

### 2.2 El techo de ppp pasa de relativo a absoluto — **y esto corrige a la consolidación anterior**

**Qué escribió D1** hace seis horas, en `PLAN-ORQUESTADOR.md` §4.5 y en la tabla de reglas de §5:

```
ppp_ocr = clamp(ppp_nativos, 100, ppp_nativos × 1,4)
```

**Qué midió G1 después** (`bench/corpus-d4.md` §8), sobre `escaneado_d4`, que es de **200 ppp nativos** — el primer documento del corpus que permite probar el techo desde otro punto de partida:

| motor | `d4` a 200 ppp (nativo) | `d4` a **280 ppp (= ×1,4)** | efecto del techo |
|---|---:|---:|---|
| PaddleOCR PP-OCRv6 medium | **19,30 %** | **36,24 %** | **+16,9 puntos, PEOR** |
| RapidOCR PP-OCRv6 small corregido | **18,62 %** | 28,86 % | **+10,2 puntos, peor** |
| RapidOCR PP-OCRv5 mobile (defecto) | 41,78 % | 41,95 % | +0,2, indiferente |

**El techo relativo era un artefacto de que todo el corpus viejo fuera de 100–200 ppp.** Lo que decide **no es el factor sobre el nativo sino el tamaño en píxeles que llega al detector**: `d3` a ×1,4 son 907 px de ancho; `d4` a ×1,4 son **1 812**. Son regímenes distintos y no hay razón para que compartan multiplicador.

**Regla vigente:**

```
ppp_ocr = clamp(ppp_nativos, 100, 200)      # techo ABSOLUTO
```

**Por qué es defendible:** d2 y d3 (100 nativos) toleran hasta 140; `d4` (200 nativos) se degrada ya a 280; el patológico (200 nativos) siempre fue el mejor caso. **Un techo absoluto de 200 no viola ninguna medida existente y el relativo ×1,4 sí.** El suelo de 100 se mantiene sin cambios.

> **Marcado PENDIENTE en los cuatro sitios donde aparece, y hay que respetarlo: no se ha barrido la curva de ppp sobre `d4`.** Faltan los puntos entre 200 y 280 y por encima de 280. **Hasta que se barra, `clamp(nativos, 100, 200)` es la propuesta mejor apoyada, no una regla medida.** Es el pendiente **B9** de `ESTADO-Y-REPARTO.md` §3.

**Y el acantilado sigue existiendo, pero cambia de dueño:** con el OCR de Ghostscript, un quinto motor completamente distinto, **en d3 sobremuestrear es monótonamente catastrófico —una rampa de 105 % a 834 %, no un acantilado— y en d1 y d2 la curva es plana en 0,0 % de 100 a 300 ppp.** **El acantilado ×1,4/×1,6 es de PaddleOCR, no de la resolución; el suelo de 75 ppp es de todos.**

### 2.3 La corrección de normalización de RapidOCR

**Qué se creía**, en tres versiones sucesivas y todas equivocadas: *«es límite de modelo, PP-OCRv5 mobile frente al medium de Paddle»* (`HUECOS.md`) → *«no es la generación del backbone; quedan tres candidatos: tamaño, idioma del reconocedor, idioma del detector»* (`ocr-ppp-nativos.md` §6) → **ninguno de los tres**.

**Las tres hipótesis, refutadas una a una — MEDIDO** (`bench/corpus-d4.md` §7):

- **El tamaño:** el **mismo** checkpoint nominal (PP-OCRv6 small) da **3,80 % en PaddleOCR y 75,95 % en RapidOCR** sobre d3. **72,2 puntos con los mismos pesos.** Y no es monótona: en RapidOCR, `tiny` (43,04) es **mejor** que `small` (75,95).
- **El idioma del reconocedor:** en PP-OCRv6, `lang="es"` y `lang="en"` **resuelven al mismo par de checkpoints** (`paddleocr 3.7.0`, `_pipelines/ocr.py:318`) y dan **salida idéntica carácter a carácter**. *La etiqueta «PP-OCRv6 medium, `es`» de la tabla canónica es correcta pero engañosa: el `es` no hace nada.*
- **El idioma del detector:** en v6 hay **un solo detector, `multi`**. La variable solo existe en v4, y ahí mueve mucho **sin dirección**.

**La causa:**

> **RapidOCR 3.9.2 normaliza el PP-OCRv6 con `mean=std=0,5` cuando el `inference.yml` que Baidu distribuye JUNTO AL MODELO declara las estadísticas de ImageNet.**

| configuración (mismo checkpoint, PP-OCRv6 small) | d3 | d4c | d4 |
|---|---:|---:|---:|
| defecto de RapidOCR | **75,95** | 29,36 | 36,91 |
| **solo** post-proceso de PaddleX | 75,95 | 32,21 | 36,58 |
| **solo** `mean`/`std` de ImageNet (RGB) | **11,39** | 1,01 | 20,13 |
| **solo** `mean`/`std` de ImageNet (BGR) | **8,86** | 1,01 | 18,79 |
| **normalización + post-proceso** | **3,80** | **1,17** | **18,62** |
| *(referencia: PaddleOCR con el mismo v6 small)* | *3,80* | *1,01* | *19,80* |

**La normalización sola vale 64,6 puntos. El post-proceso solo vale 0,0. Los dos juntos reproducen la cifra de PaddleOCR exactamente.** Y el recuento de cajas lo convierte en medida: **el detector pasa de encontrar 1 renglón de 3 a 3 de 3** en d3, y de 8 de 12 a 12 de 12 en d4. **No es que lea mal: es que no ve.**

**Qué hay que construir distinto:**

```python
params = {
    "Det.mean": [0.485, 0.456, 0.406],
    "Det.std":  [0.229, 0.224, 0.225],
    "Det.thresh": 0.2,
    "Det.box_thresh": 0.45,
    "Det.unclip_ratio": 1.4,
    "Det.max_candidates": 3000,
}
```

**Y la consecuencia para el hito 6, que es la que hay que escribir:** con esa corrección, **RapidOCR ONNX cubre el corpus entero** — `0,00 / 0,00 / 0,00 / 3,80 / 18,62 %` sobre patológico, d1, d2, d3 y `escaneado_d4` —, **gana a PaddleOCR en cuatro de las cinco filas, arranca en 3,7 s en vez de 18,4 y funciona en CPU** (0,32–1,18 s/página). **La regla «degradación severa → cambiar a PaddleOCR» pierde su motivo: la diferencia que la justificaba era el defecto de configuración, no el motor.** *La excepción es d3, donde PaddleOCR gana por **1,27 puntos — un carácter sobre 79**. No es base para una regla de conmutación.*

**Tres cosas más que van con esto:**

- **Docling hereda el defecto** —construye RapidOCR con los parámetros por defecto— y **es corregible desde fuera, sin parchear el paquete**.
- **`bench/scripts/ocr_motor.py` fija `LangRec.CH`:** la línea base del proyecto **lee castellano con un reconocedor de chino**, que cuesta **19,0 puntos en d3 y 23,7 en d4** frente al latino. *(No explica la asimetría —dentro de RapidOCR, `ch`→`latin` mueve 1,3 puntos en d3— pero es un defecto real y barato de arreglar.)*
- **La regla general, que vale más que el parche:** *cuando el motor y el modelo vienen de proyectos distintos, hay que comprobar que el preprocesado que aplica el motor es el que declara el fichero de configuración del modelo.* Es el mismo tipo de fallo que `onnxruntime-gpu` cayendo a CPU en silencio: **nada da error, solo empeora.**

**PENDIENTE, y está marcado en los cinco sitios:** validar la corrección **fuera del corpus `d4`**, contra el patrón oro. Está medida sobre 5 documentos de una página cada uno.

---

## 3. Contradicciones: se escriben, no se resuelven

### 3.1 Las tres que quedaban abiertas de la pasada anterior

| # | Qué choca | Los dos sitios | Estado tras esta pasada |
|---|---|---|---|
| 1 | **EasyOCR en d3: ¿57,0 % o 59,5 %?** | `bench/gpu-fase2.md` §3 dice **57,0 %** · `bench/ocr-ppp-nativos.md` §2 reproduce **59,5 %** | **Sigue siendo lo que D1 dijo —dos medidas de la misma casilla, CPU y GPU— pero ahora se sabe que NO es una rareza de una celda.** `bench/corpus-d4.md` §9.3 mide **5 de 21 celdas con salida distinta entre CPU y GPU**, y **la CPU es mejor en dos y peor en tres**. La frase de `gpu-fase2.md` §2 —«CPU y GPU dan salida idéntica carácter a carácter»— **queda refutada**, y con ella la lectura cómoda de que la GPU no cambia el resultado. **Matizado donde aparece**: `ANALISIS-COMPLETO.md` §5.5, `PLAN-ORQUESTADOR.md` §4.5 y §5, `CLAUDE.md` §4 trampa 11 |
| 2 | **Tokens de catálogo: ¿7.964/2.322, 7.886/2.306, o ≈3.610/≈811?** | `RESULTADOS-MCP.md` §4 · `saturacion-herramientas.md` §2.2 · `analysis/00-mcp-componentes.md` §3.5 | **SIGUE ABIERTA, y ninguno de los tres informes de esta pasada la toca.** El recuento nuevo (7.886/2.306) queda a **1 %** de §4 y **no explica el factor 2,2** frente a componentes. **Las cifras vigentes son las de `RESULTADOS-MCP.md` §4.** Cerrarla exige rehacer el conteo de `00-mcp-componentes.md` §3.5 con `tiktoken`/`o200k_base` sobre el catálogo serializado — **anotado en §12 de `RESULTADOS-MCP.md`; el fichero es de otro carril** |
| 3 | **El 99,0 % de similitud de I1** | `bench/fidelidad-caminos.md` §3 dice **99,0 %** · `bench/verificador-ghostscript.md` §5.7 obtiene **94,7 %** (espacios normalizados) o **97,1 %** (ignorándolos) | **NO REPRODUCIDO, y se mantiene esa prudencia: V1 no lo declara refutado** porque `fidelidad-caminos.md` **no publica ni los ppp de su rasterizado, ni el idioma de OCR, ni su fórmula de similitud**. Lo que sí queda MEDIDO es que **el orden de magnitud correcto es 94-97 %** y que **la mayor parte de la pérdida son espacios, no letras** (`Col A` → `ColA`, `FileX` → `Filex`). **Escrito así en `HUECOS.md` §2 y `PLAN-ORQUESTADOR.md` §4.1**, con el pendiente C18: publicar los parámetros de I1 |

### 3.2 Y una corrección de un informe a otro del mismo día, que no es contradicción sino secuencia

| Qué | Quién lo escribió | Quién lo corrige |
|---|---|---|
| `clamp(nativos, 100, nativos × 1,4)` en `PLAN-ORQUESTADOR.md` §4.5 y §5 | **D1**, a las 04:30, correctamente a partir de `ocr-ppp-nativos.md` §9 | **G1**, a las 09:10, con `escaneado_d4`, que no existía cuando D1 escribió. **D1 no podía saberlo, y la regla que escribió era la mejor apoyada por lo medido entonces** |
| «El corpus ya no mide dificultad, mide selección de motor» como PENDIENTE en cuatro maestros | **D1** | **G1**, que lo cierra construyendo `d4` |
| «Los tres candidatos que quedan, PENDIENTES de aislar» | **D1**, fielmente desde `ocr-ppp-nativos.md` §6 | **G1**, que refuta los tres y encuentra el cuarto |
| «Cuántas de las 138.501 aristas son nominales» como pendiente del hueco 2 | **D1** | **E1**, con el 50,5 % |
| El prototipo del verificador «3.035 líneas» en tres maestros | **D1** | **V1**, que lo deja en **3.859** |

**Ninguna de estas cinco es un error de D1.** Son el efecto de que cuatro agentes corrieran en paralelo y tres terminaran después. **Se documentan aquí para que la traza quede completa**, y en cada maestro se ha conservado la cifra vieja tachada o entre paréntesis, no borrada.

---

## 4. Lo que este trabajo cierra, en cifras

| | Antes de esta pasada | Ahora |
|---|---|---|
| Fallos de verificación del catálogo de `HUECOS.md` §1 | **7**, en 6 proyectos, **todos atrapados por el contrato** | **8**, en 7 proyectos, **y el octavo NO lo atrapa** |
| Puntos del contrato de verificación | **4** | **5** |
| Reglas de confinamiento de `PLAN-ORQUESTADOR.md` §4.6 | 17 | **18** |
| Pendientes del hueco 2 | 2 abiertos («si se piden» y «cuántas son nominales») | **1** — el otro cerrado con 50,5 % · **+4 nuevos**, todos acotados |
| Pendientes de píxeles / verificador de `HUECOS.md` §1 | 6 abiertos | **4 cerrados**, **8 nuevos** con su coste |
| Pendientes del hueco 5 | 10 abiertos | **5 cerrados**, 6 nuevos |
| Casos `no_evaluable` de `referencia.json` | 7 | **2** (`qpdf`, `tesseract`) |
| Prototipo `verificador.py` | 3.035 líneas | **3.859** |
| PDF del corpus de OCR | 4 (`patologico`, `d1`, `d2`, `d3`) | **10** (+ los seis de la familia `d4`) |
| Trampas de `CLAUDE.md` §4 | 14 | **22** |

**Seis tesis del proyecto quedaron refutadas o acotadas por estos tres informes, y las seis están ya en los maestros:**

1. **«Los cuatro puntos del contrato atrapan los fallos del sector»** → **acotada**: el octavo no.
2. **«RapidOCR falla en d3 por ser un modelo peor»** → **refutada del todo**: era un defecto de normalización, y con la corrección **gana a PaddleOCR en cuatro de cinco documentos**.
3. **«El techo ×1,4 de la regla de ppp»** → **refutado parcialmente**: empeora 16,9 puntos sobre un original de 200 ppp.
4. **«CPU y GPU dan salida idéntica carácter a carácter»** → **refutada**: 5 de 21 celdas.
5. **«`epub→pdf` es el mejor ejemplo de arista nominal del proyecto»** → **refutada como universal**: es nominal **de un motor**, y Calibre la hace bien.
6. **«El testigo de ruido del proyecto detecta las tandas sucias»** → **refutada**: es ciego a la contención multinúcleo.

> **Y la sexta tiene una coda que conviene no perder, porque ocurrió el mismo día:** las medianas de CPU de `bench/corpus-d4.md` §9 se tomaron **con otros dos agentes midiendo en CPU en paralelo**, y **su sonda de carga devolvió `-1` en las 11 tandas** (`FileNotFoundError: [WinError 2]` — `powershell` sin ruta absoluta bajo Git Bash). **G1 las declara cota superior del coste de CPU y no las repitió**, por no volver a tomar el lock. **Es exactamente el punto ciego que V1 acaba de describir, ocurriendo en la misma jornada y en otro agente.** Está escrito así en `HUECOS.md` §5 y la regla está en `CLAUDE.md` §3: **dos testigos, uno de deriva y otro de nivel, y hay que llevar los dos.**

---

## 5. El commit — preparado, **NO ejecutado**

**No se ha hecho `git add` ni `git commit`.** Esto **sustituye** a `bench/consolidacion-21ago.md` §5.2-§5.5, cuya lista se quedó corta: entonces faltaban tres informes y sus salidas.

### 5.1 Estado real del árbol (`git status --short`, 21/08 10:00)

**14 modificados · 24 sin versionar** (contando este informe). Los ficheros sueltos de basura que D1 anotó (`chunk-stream0-*.m4s`, `o0478_map.shtml`…) **ya no están en la raíz**: eran la fuga del §5.2 de `aristas-nominales.md` y su autor los retiró tras reproducirla de forma controlada en `bench/salidas-aristas/fuga/`.

### 5.2 Qué INCLUIR

**Maestros y análisis (14 ficheros):**

```
ANALISIS-COMPLETO.md   CLAUDE.md   HUECOS.md   PLAN-ORQUESTADOR.md   RESULTADOS-MCP.md
AGENTES-PRUEBAS-PENDIENTES.md      ESTADO-Y-REPARTO.md
analysis/00-licencias.md           analysis/00-matriz-formatos.md
analysis/00-mcp-componentes.md     analysis/00-mcp-filesystem.md
analysis/00-mcp-patrones.md        analysis/OCRmyPDF.md
bench/gpu-fase2.md
```

**Los siete informes nuevos y las dos consolidaciones:**

```
bench/verificador-fidelidad.md     bench/mcp-cabos-sueltos.md
bench/saturacion-herramientas.md   bench/ocr-ppp-nativos.md
bench/corpus-d4.md                 bench/aristas-nominales.md
bench/verificador-ghostscript.md
bench/consolidacion-21ago.md       bench/consolidacion-2-21ago.md
```

**El código:** `bench/scripts/verificador.py` (3.035 → **3.859 líneas**, +824, sin dependencias nuevas). **Ya no hay motivo para esperar: V1 ha cerrado.**

**El corpus nuevo — por Git LFS:**

```
corpus/pdf/escaneado_d4.pdf   escaneado_d4a.pdf   escaneado_d4b.pdf
corpus/pdf/escaneado_d4c.pdf  escaneado_d4e.pdf   escaneado_d4f.pdf
corpus/pdf/MANIFIESTO-d4.md
```

> **`.gitattributes` ya cubre `corpus/**/*.pdf filter=lfs`**, así que se toman solos **si `git lfs` está instalado y el filtro activo**. **Compruébalo antes de commitear** con `git lfs status` o `git check-attr filter -- corpus/pdf/escaneado_d4.pdf`: si el filtro no está activo, entran **703 KB de binario crudo** al pack. Son 6 ficheros de **86-152 KB** (703 KB en total), con `sha256` y orden exacta en `MANIFIESTO-d4.md`.

**Los siete directorios de salidas — su parte de TEXTO:**

| Directorio | Ficheros | Tamaño | Nota |
|---|---:|---:|---|
| `bench/salidas-mcp-cabos/` | 75 | 191 KB | ya listado por D1 |
| `bench/salidas-ocr-ppp/` | 341 | 334 KB | ídem |
| `bench/salidas-saturacion/` | 26 | 1 038 KB | ídem; los dos `.jsonl` grandes son las 540 ejecuciones |
| `bench/salidas-verificacion-fidelidad/` | 13 | 143 KB | ídem |
| **`bench/salidas-corpus-d4/`** | **504** | **1 109 KB** | 100 % texto: `.py`, `.json`, `.txt`, `.log`, `MANIFIESTO.md` |
| **`bench/salidas-verificador-gs/`** | **47** | **316 KB** | 100 % texto (las 48 binarias, 21,6 MB, **ya borradas por su autor** con `sha256`) |
| **`bench/salidas-aristas/`** | **98** | **1 217 KB** | **texto salvo 32 ficheros binarios — ver §5.3** |

**Inventario por extensión de los tres directorios nuevos: 356 `.txt` · 109 `.json` · 86 `.log` · 38 `.py` · 11 `.sh` · 7 `.md` · 1 `.tsv` · 1 `.jsonl` · 1 `.csv`.**

### 5.3 Qué EXCLUIR

| Qué | Por qué |
|---|---|
| **Los 32 binarios de `bench/salidas-aristas/`** — ~440 KB en `c8/in/`, `c8/out/**` y `fuga/{t.mpd, u.map, u.png}`: `.pdf`, `.docx`, `.epub`, `.azw3`, `.mobi`, `.odt`, `.rtf`, `.xlsx`, `.png`, `.jpg`, `.webp`, `.mpd`, `.map`. *(Los `.html` y `.shtml` de `fuga/` SÍ entran: son texto, y son la prueba literal de la fuga.)* | `CLAUDE.md` §6: **no se versionan salidas binarias regenerables.** **`bench/salidas-aristas/MANIFIESTO.md` las cubre todas** con nombre, `sha256`, tamaño y la orden exacta (`c8_prepara.py`, más la línea de `c8/resultado.tsv` con su id). **Su autor ya retiró `v.tif`, 16,6 MB, por el mismo criterio.** Añádelas a `.gitignore` siguiendo el patrón que ya usa el fichero para `salidas-fase1/2/fidelidad`: excluir el directorio y **volver a incluir el `MANIFIESTO.md`, los `.json`, los `.py`, los `.sh`, los `.md` y los logs** |
| **`bench/.gpu.lock`** | Estado de ejecución, no evidencia. **Nunca se versiona.** Añadirlo a `.gitignore` |
| **`bench/salidas-mcp-cabos-2/`, `bench/motores-restantes.md`, `bench/salidas-motores-restantes/`** | **No existen: M1 y G2 no se han lanzado.** Si aparecen antes del commit, son de otro agente |
| Cualquier salida binaria regenerable | `CLAUDE.md` §6. El repositorio ya pagó una vez **986 MB de pack, 99,9 % binario** |

### 5.4 Orden propuesta

```bash
# 0) Comprobar que LFS va a tomar los PDF del corpus. Si esto no dice "lfs", PARA.
git check-attr filter -- corpus/pdf/escaneado_d4.pdf

# 1) .gitignore: el lock y los binarios de salidas-aristas, con sus negaciones
#    (mismo patrón que ya usa el fichero para salidas-fase1/2/fidelidad)

git add ANALISIS-COMPLETO.md CLAUDE.md HUECOS.md PLAN-ORQUESTADOR.md RESULTADOS-MCP.md \
        AGENTES-PRUEBAS-PENDIENTES.md ESTADO-Y-REPARTO.md .gitignore \
        analysis/00-licencias.md analysis/00-matriz-formatos.md \
        analysis/00-mcp-componentes.md analysis/00-mcp-filesystem.md \
        analysis/00-mcp-patrones.md analysis/OCRmyPDF.md \
        bench/gpu-fase2.md bench/scripts/verificador.py \
        bench/verificador-fidelidad.md bench/mcp-cabos-sueltos.md \
        bench/saturacion-herramientas.md bench/ocr-ppp-nativos.md \
        bench/corpus-d4.md bench/aristas-nominales.md \
        bench/verificador-ghostscript.md \
        bench/consolidacion-21ago.md bench/consolidacion-2-21ago.md \
        bench/salidas-mcp-cabos/ bench/salidas-ocr-ppp/ \
        bench/salidas-saturacion/ bench/salidas-verificacion-fidelidad/ \
        bench/salidas-corpus-d4/ bench/salidas-verificador-gs/ bench/salidas-aristas/ \
        corpus/pdf/escaneado_d4.pdf corpus/pdf/escaneado_d4a.pdf \
        corpus/pdf/escaneado_d4b.pdf corpus/pdf/escaneado_d4c.pdf \
        corpus/pdf/escaneado_d4e.pdf corpus/pdf/escaneado_d4f.pdf \
        corpus/pdf/MANIFIESTO-d4.md

git status --short          # que no entre nada de agentes sin lanzar
git diff --cached --stat    # que no entre ningun binario fuera de LFS
git lfs status              # que los 6 PDF salgan como LFS objects
```

### 5.5 Mensaje propuesto

```
Siete mediciones nuevas y la consolidacion completa de los maestros

Integra en HUECOS.md, PLAN-ORQUESTADOR.md, RESULTADOS-MCP.md,
ANALISIS-COMPLETO.md, CLAUDE.md, ESTADO-Y-REPARTO.md y analysis/ los siete
informes del 21 de agosto. Seis tesis del proyecto quedan refutadas o
acotadas, y tres resultados cambian el diseno y no solo la documentacion.

CAMBIAN EL DISENO

- El contrato de verificacion gana un QUINTO punto: hay motores que escriben
  fuera del destino. `ffmpeg -i x out.mpd` deja 528 KB de segmentos DASH en
  el cwd y entrega un .mpd de 1,2 KB inutil que PASA LOS CUATRO PUNTOS;
  `magick ... out.html` produce dos ficheros en el destino y un tercero en el
  cwd. El confinamiento pasa a exigir un directorio de trabajo desechable por
  conversion (regla R18), no solo una ruta de salida validada.

- La regla de ppp cambia de techo RELATIVO a ABSOLUTO:
  clamp(nativos, 100, 200). El x1,4 empeora a PaddleOCR de 19,30 % a 36,24 %
  sobre escaneado_d4, que es de 200 ppp nativos: la meseta se midio sobre d3
  (100 ppp) y no se transfiere. PENDIENTE barrer la curva sobre d4.

- La ventaja de PaddleOCR era un defecto de RapidOCR. No es el tamano del
  modelo (el mismo PP-OCRv6 small da 3,80 % y 75,95 %), ni el idioma del
  reconocedor (en v6 `es` y `en` son el mismo checkpoint), ni el del detector
  (en v6 hay uno solo): RapidOCR normaliza con mean=std=0,5 lo que el
  inference.yml del propio modelo declara con ImageNet. La normalizacion sola
  vale 64,6 puntos de CER; con el post-proceso reproduce la cifra de
  PaddleOCR exactamente. Seis numeros por 72,2 puntos. Docling hereda el
  defecto. Con la correccion, RapidOCR ONNX cubre el corpus entero
  (0,00/0,00/0,00/3,80/18,62 %), gana a PaddleOCR en cuatro de cinco filas,
  arranca en 3,7 s en vez de 18,4 y funciona en CPU.

REFUTACIONES

- El contrato de cuatro puntos tiene su primer caso que no atrapa: resvg
  0.46.0 devuelve rc=0, un PNG valido, con la geometria exacta pedida y sin
  una sola letra (0,00 % de tinta en la banda de texto frente al 14,0 % de
  Inkscape). Es el octavo fallo de verificacion del catalogo y el primero
  cualitativamente distinto. Acota el diferenciador n.1, no lo invalida: el
  contrato juzga la declaracion; el contenido que desaparece necesita
  fidelidad.

- "CPU y GPU dan salida identica caracter a caracter": FALSO. 5 de 21 celdas
  difieren y la CPU es mejor en dos y peor en tres.

- "epub->pdf es el mejor ejemplo de arista nominal del proyecto": es nominal
  DE UN MOTOR. Falla con LibreOffice (rc=1 tambien en Linux) y funciona con
  Calibre (26 817 B, centinela y tabla intactos). Obliga a revisar el
  criterio de aceptacion del hito 1.

- El testigo de ruido del proyecto es ciego a la contencion multinucleo:
  etiqueto "limpia" una tanda que salio x6,8 sobre el mismo control. Hacen
  falta dos testigos, uno de deriva y otro de nivel.

MEDICIONES

- Aristas nominales: el 50,5 % de las aristas declaradas verificables no
  existe, IC 95 % [48,2-53,0] sobre 62 487 aristas. Declarado como cota
  inferior. Pero la tasa no es uniforme (factor 18: ffmpeg cruzando familias
  76,9 %, ImageMagick misma familia 4,2 %) y el estrato prioritario -PDF como
  intermedio- sale al 3,0 %: las aristas que el multi-salto usa de verdad si
  existen. Cierra el ultimo pendiente del hueco 2.

- Corpus escaneado_d4: cumple los cuatro criterios y el de exito declarado
  antes de medir. 19,30 / 36,91 / 41,78 / 61,41 % de CER. 200 ppp nativos,
  castellano con tildes, cuatro tamanos de letra y 610 caracteres de
  referencia, que cuantizan el CER a 0,16 puntos en vez de 1,27.

- OCR sin GPU: el Tesseract embebido en Ghostscript da 0,0 % de CER en
  patologico, d1 y d2 a ppp nativos con spa, con VRAM 0 y carga en frio de
  122 ms frente a 3,4-17,3 s. En d3 fracasa alucinando (165,8 %), que es un
  modo de fallo distinto. La arista de reparacion pdf escaneado -> docx
  funciona en 3 de 4 documentos, y es de DOS saltos: docxwrite directo
  entrega 2 caracteres de basura.

- El verificador pasa de 3 035 a 3 859 lineas, sigue con 0 falsos positivos
  y 12/12 fallos atrapados. V2 (-count_frames) sube la suite de fidelidad un
  60,6 %: necesita interruptor propio. Y se corrigio un fallo preexistente
  que hacia que la regla I3 leyera OTRO pixel en PNG de paleta <8 bits.

Corpus nuevo: corpus/pdf/escaneado_d4{,a,b,c,e,f}.pdf por Git LFS, con
MANIFIESTO-d4.md. Salidas: texto, con los binarios regenerables excluidos y
cubiertos por sus MANIFIESTO.md.
```

---

## 6. Cómo verificar este informe

**Todo lo de arriba es reconciliación de texto, no medición.** Se comprueba abriendo los dos lados:

| Para comprobar | Abrir |
|---|---|
| Que ninguna cifra es inventada | Cada fila de §1 lleva la sección exacta del informe de origen |
| Que `resvg` devuelve un PNG sin letras | `bench/aristas-nominales.md` §8.2 y `bench/salidas-aristas/c8/svg_comparacion.json` |
| Que los motores escriben fuera del destino | `bench/salidas-aristas/fuga/` — la reproducción controlada |
| Que el 50,5 % tiene método | `bench/salidas-aristas/muestra.json` (598 aristas, una por línea, con orden, rc, bytes, firma, categoría y motivo) y `escenarios.json` |
| Que la normalización vale 72,2 puntos | `bench/corpus-d4.md` §7.4 y los `.json` de `bench/salidas-corpus-d4/json/` |
| Que `d4` cumple el criterio declarado antes de medir | `bench/corpus-d4.md` §5 y `bench/salidas-corpus-d4/tablas.md` |
| Que el OCR de Ghostscript da 0,0 % sin GPU | `bench/salidas-verificador-gs/ocr_cer.json` y los `.txt` de `ocr/` |
| Que el verificador declara `OK` una alucinación | `bench/salidas-verificador-gs/senal_alucinacion.json` |
| Que el testigo monohilo falló | `bench/verificador-ghostscript.md` §4, tabla de las tres tandas |
| Qué cambió D1 y qué cambió D2 | `bench/consolidacion-21ago.md` §1 y §1 de este documento |
