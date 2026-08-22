# Tercera consolidación del 21 de agosto — qué decía cada maestro y qué dice ahora

**Agente D3.** 21 de agosto de 2026, 14:00. **Sin GPU, sin mediciones nuevas: este informe no mide nada, reconcilia.** Continúa donde lo dejaron `bench/consolidacion-21ago.md` (D1) y `bench/consolidacion-2-21ago.md` (D2), **y corrige a la segunda en tres sitios**.

**Fuentes integradas** — los tres informes de la tarde, ninguno volcado en ningún maestro:

| Hora | Informe | Qué aporta |
|---|---|---|
| 13:00 | `bench/contrato-quinto-punto.md` (P3) | **El quinto punto implementado y medido**, la **regla I9**, la **familia de cinco miembros**, **`P9` refutada** con sustituto, el interruptor de V2 y **un fallo del propio verificador** |
| 13:20 | `bench/invocacion-aristas.md` (P2) | **El 18,8 % del 50,5 % que era invocación**, el censo de Ghostscript y Gotenberg, y el coste de `qpdf` + `tesseract` |
| 13:40 | `bench/ppp-y-normalizacion.md` (P1) | **La refutación de las DOS reglas de ppp vigentes** y la validación por checkpoint de la normalización de RapidOCR |

**Regla que gobernó el trabajo, la misma de las dos pasadas anteriores:** ni una cifra inventada. Cada número movido a un maestro está **literalmente** en uno de los tres informes y se cita con fichero y sección. Donde dos documentos se contradicen, **no se elige: se escribe la contradicción y se señalan los dos sitios** (§4).

---

## 0. Lo que hay que leer si solo se leen diez líneas

1. **Esta pasada CORRIGE a la anterior, no la amplía.** Tres de las escrituras de D2 quedan refutadas por medición. No eran errores suyos —no podía saberlo—, y **se corrigen explícitamente, diciendo de dónde sale cada corrección**.
2. **La regla de ppp estaba mal en sus DOS versiones.** Ni `clamp(nativos, 100, nativos×1,4)` ni `clamp(nativos, 100, 200)`. **Los ppp no son la unidad**, ni el factor, ni la anchura en píxeles: **la regla es POR MOTOR**, con óptimos entre ×0,50 y ×1,80 sobre el mismo documento.
3. **Y eso mueve la regla de sitio en el diseño:** si es por motor, **la elección de ppp pertenece al adaptador de cada motor, no al orquestador**. Hoy está escrita en el sitio equivocado.
4. **`P9` —que D2 escribió hace unas horas como propuesta no validada— se validó y se tiró:** 8,3 % de sensibilidad, 36 % de falsos positivos. **Hay sustituto medido, 16/16.**
5. **El quinto punto del contrato está implementado: +11,0 % del contrato. Pero solo con R18** — sin directorio desechable cuesta **×8,6 el contrato entero**. **R18 deja de ser higiene y pasa a ser requisito de coste.**
6. **Y el punto 5 es el primero del contrato que no es verificable a posteriori:** sin censo, **49 de las 53 salidas del patrón oro bajan de `ok` a `ok_parcial`**. **La verificación tiene que vivir dentro de la conversión.**
7. **El 50,5 % de aristas nominales gana su cota: el 18,8 % era invocación.** La tasa baja a **41,0 %** con los mismos motores, y **3 226 aristas (10,2 %) son ganancia automática** — la primera afirmación de producto de este proyecto que se puede escribir con número.
8. **«Verificar en proceso siempre gana» es falso para píxeles.** Cierto para cabeceras (145×), falso en cuanto hay que recorrerlos (×20,5 a favor de `magick`).

---

## 1. La tabla de cambios

### 1.1 `CLAUDE.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| **§1** | «Un fichero de salida por agente» | **+ «el lock de GPU no te protege de la máquina, solo del proyecto»**, con el caso: otra sesión de Claude en `D:\Work\research\ASR` ocupando **11 754 de 12 288 MiB** dejó una tanda **12 minutos sin procesar una imagen**. **Si la GPU va lenta y el lock está libre, mira los PID** | `ppp-y-normalizacion.md` §1.3 |
| §2 | «FileX tendría que distribuir 2–4 MB por idioma» | **Tachado para la vía de contenedor:** **8 líneas de Dockerfile, 28,1 s, +50 MB (+0,9 %)** añaden `qpdf 12.4.0` y `Tesseract 5.5.0`, **con `spa` incluido**. Solo sigue haciendo falta para el Ghostscript **nativo** de Windows | `invocacion-aristas.md` §9 |
| **§3** | «Dos testigos de ruido» con **un** caso | **Tres casos en un día** (V1 ×6,8 · P1 ×7,18 con deriva 0,83 · P3 **×94,6** con `ffprobe -version` agotando 60 s), **+ «ponle tope al propio testigo»**, **+ que las cifras absolutas de tandas distintas no son comparables** (46 332 ms frente a 70 693 sobre los mismos ficheros) | `ppp-y-normalizacion.md` §1.2 · `contrato-quinto-punto.md` §9 |
| **§4 · trampa 8** | *«Regla vigente: `clamp(nativos, 100, 200)` — techo absoluto»* | **REESCRITA ENTERA: las dos versiones anteriores están refutadas.** Con las tres candidatas caídas una a una, el experimento de las 24 celdas, el defecto del techo absoluto (solo baja, y bajar cuesta 12,08 puntos; y su evidencia era un punto que la regla anterior no producía), **la regla por motor con su `k`**, el límite global que sí queda (**VRAM**) y el mecanismo sondeado (`max_side_len: 2000`) | `ppp-y-normalizacion.md` §2 |
| §4 · trampa 17 | «Comprueba que el preprocesado que aplica el motor es el que declara el modelo» | **+ la segunda mitad, que faltaba: los OCHO `inference.yml` declaran ImageNet y RapidOCR aplica 0,5 a los ocho — el desajuste es universal, el daño no.** Corregirlo **es una hipótesis, no una solución**: 12 de 42 celdas empeoran, con **+42,50 puntos** en `PP-OCRv4 mobile` sobre un documento limpio | ídem §3.4, §3.5 |
| §4 (nuevas) | 22 trampas | **24.** **23** · Q16-HDRI: releer un crudo con `-depth 8` entrega geometría correcta y **píxeles basura**, y **pasa los cuatro puntos**. **24** · comparar gris contra referencia en color mide la pérdida del formato, no la de la invocación | `invocacion-aristas.md` §4.1, §4.2 |
| **§5** | «El contenido que desaparece necesita fidelidad» · «Verificar en proceso» · «Sondear capacidades» | **+ la formulación precisa de la frontera** (el contrato atrapa lo **declarado en metadatos**) · **+ el punto 5 no es verificable a posteriori** · **+ los dos regímenes de «en proceso»** · **+ «fuerza lo que el motor no puede deducir»** · **+ la resolución de OCR la elige el adaptador del motor** | los tres |

### 1.2 `HUECOS.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | Cuatro revisiones | **Quinta revisión (21/08, 14:00)**, escrita **como corrección en tres sitios, no como ampliación**, con las dos autorrefutaciones destacadas | los tres |
| Resumen del reordenamiento | Difer. 1 «no atrapa el octavo fallo» · Difer. 2 «50,5 %» | **+ «I9 sí lo atrapa (6/6), pero la familia tiene cinco miembros y uno sigue descubierto»** · **+ «el 18,8 % era invocación → 41,0 %, y 3 226 aristas son ganancia automática»** | `contrato-quinto-punto.md` §4, §5 · `invocacion-aristas.md` §0 |
| **§1 · el caso `resvg`** | «La regla que lo atraparía… **PENDIENTE de implementar**» | **IMPLEMENTADA**, con bloque propio: cómo funciona (caja **deliberadamente estrecha** para evitar falsos negativos), **6/6 con margen binario**, **su coste real 32–2 454 ms (la estimación fallaba ×94)**, y lo que no cubre | `contrato-quinto-punto.md` §4 |
| **§1 (bloque nuevo)** | — | **La FAMILIA de `resvg`: cinco miembros en cinco modalidades**, con quién atrapa a cada uno, **el que sigue sin cubrir**, **la confirmación del acotamiento de D2 como arquitectura**, **el sexto candidato encontrado por P2 de forma independiente**, la nota de severidad de V8 (5,39 dB) y la hipótesis descartada de `gs pdfwrite` | ídem §5 |
| **§1 · quinto punto** | «Se implementa listando el directorio antes y después — **trivial**» | **MEDIDO: +0,047 ms = +11,0 %… y ×8,6 sin R18.** Con la tabla de coste, las cinco reglas N5-N9, **las dos decisiones que salieron de los datos** (ubicación y no tamaño; `multifichero: true` no autoriza el `cwd`), la discriminación sobre casos fabricados, **los 0 falsos positivos** y **los 49 de 53 que bajan a `ok_parcial`** | ídem §2, §3 |
| §1 · prototipo | 3.859 líneas | **4 185 líneas**, con el desglose por bloque, **los cambios de firma**, **el interruptor de V2 (−46,3 %)** y **la nota de trazabilidad**: las 3 859 publicadas **no se han podido reproducir** (implican ~3 530 de partida) | ídem §1, §7 |
| **§1 (bloque nuevo)** | «Un `txtwrite` que devolvió 0 caracteres una vez, **no reproducido en 20 intentos**» | **REPRODUCIDO, LOCALIZADO Y CORREGIDO: era la tubería, no Ghostscript.** 6 vacíos de 430 frente a 0 de 430, al mismo coste, más el ±2 del fin de línea. **De esa sonda cuelgan P2 (`fallo`), P5, P6 y P9** | ídem §8 |
| §1 · PENDIENTE | 8 abiertos de la pasada anterior | **Cinco cerrados** (quinto punto, I9, V2, `P9`, `ocr: true`, `txtwrite`) **+ 9 nuevos** con su coste | ídem §10 |
| **§2 (bloque nuevo)** | «**Cuánto se recupera con una invocación mejor** … el pendiente de más valor» | **CERRADO: el 18,8 %** [16,8–21,3], con la tabla de tres categorías, **la afirmación de producto con su acotamiento**, **lo que impide inflarla** (58,5 % son declaraciones sin sentido; 19 de 33 son build), el gradiente invertido, lo que más rinde, y **las tres autocríticas de su autor** | `invocacion-aristas.md` §0, §3-§7 |
| **§2 (bloque nuevo)** | «**Las 140 aristas de Ghostscript y Gotenberg** sin muestrear» | **CERRADO: 3,1 %** [0,9–10,7], con **censo completo** de gs (9/9) y Gotenberg/Chromium (25/25), **la coincidencia con el 3,0 % del estrato PDF por un camino independiente**, y el sesgo declarado (72 de 102 sin semilla) | ídem §8 |
| **§2 (bloque nuevo)** | — | **`qpdf` y `tesseract` dejan de ser pendiente**, con el coste medido y **el contraste de los dos modos de fallo opuestos del mismo motor** (0 bytes frente a alucinación al 165,8 %), más **`escaneado_d2` refutando la regla de ppp para Tesseract** | ídem §9 |
| §2 · PENDIENTE | 4 abiertos | **Dos cerrados**, **+7 nuevos** (crudos de terceros, `bayer`, las 4 que resistieron, el coste de la invocación cuidada…). **Y el 54,78 % ha empeorado un poco:** 2 868 aristas pasan de «muerta» a «sin veredicto» | ídem §11 |
| **§5 · la regla de ppp** | *«`clamp(nativos, 100, 200)` — techo absoluto, PENDIENTE de barrer la curva»* | **BARRIDA, Y EL TECHO ABSOLUTO REFUTADO TAMBIÉN.** Bloque nuevo con: las tres candidatas caídas, **el experimento de las 24 celdas**, **los dos defectos propios del techo absoluto**, **la tabla de siete óptimos**, el precipicio de ×1,4 en `d3`, **el mecanismo sondeado y el error de deducirlo**, **la regla vigente en código**, **la consecuencia de arquitectura**, **el límite de VRAM** y tres precisiones menores | `ppp-y-normalizacion.md` §2 |
| **§5 · la normalización** | «**PENDIENTE:** validar fuera de este corpus» | **VALIDADA, con su lado malo**: 0 regresiones sobre `PP-OCRv6 small` (15 documentos, n=9) **y 12 de 42 celdas peores en la familia**, con los tres casos peores nombrados. **+ el mecanismo con fichero y línea para reportar aguas arriba**, **+ que el defecto es de los ocho modelos**, **+ docling 7/7 sin coste**, **+ la comprobación de que la corrección llegó** | ídem §3 |
| **§5 (bloque nuevo)** | — | **B11 cambia de contenido: no es «añadir R6», es «cambiar a `PP-OCRv6 small` Y añadir R6»**, con el saldo declarado **7 mejor, 2 igual, 2 peor** y la nota de que las dos regresiones son del cambio de checkpoint | ídem §4 |
| **§5 · `P9`** | «Propuesta calibrada sobre 5 puntos, PENDIENTE de validar» | **VALIDADA Y REFUTADA**, con la matriz de confusión, **por qué falla** (alucinar produce palabras largas y plausibles, no ruido corto), los falsos positivos nombrados, el margen real corregido (41,4 % en vez de 33,3 %), y **el sustituto con su tabla de 16/16 y su precio** | `contrato-quinto-punto.md` §6 |
| §5 · PENDIENTE | 13 abiertos | **Dos cerrados (B9, B10)**, **+8 nuevos**, entre ellos **el `k` por motor sobre más de un documento, señalado como el de más valor** | `ppp-y-normalizacion.md` §8 |
| Índice de evidencia | 19 filas | **+3**: los tres informes con sus salidas | — |

### 1.3 `PLAN-ORQUESTADOR.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | «Última revisión 10:00», con **tres** cosas que cambian el diseño | **La de las 10:00 pasa a histórica con su punto 2 tachado**, y entra **«Última revisión 14:00» con CUATRO**, la primera de las cuales corrige a la anterior. **+ la afirmación de producto del 10,2 %** | los tres |
| **§4.1 (bloque nuevo)** | El 50,5 % y sus tres consecuencias | **+ «el 50,5 % tiene cota: el 18,8 % es invocación»**, con la tabla de categorías, **las cuatro cosas que hay que llevar a la implementación en orden de rendimiento**, **las tres reglas de sondeo que salen de errores propios**, lo que impide inflarlo, y **la superficie documental al 3,1 %** | `invocacion-aristas.md` §0, §3-§10 |
| **§4.2 · quinto punto** | «Coste: listar un directorio antes y después. **Trivial**» | **Tachado y medido**, con la tabla de las cuatro configuraciones, **R18 como requisito de coste**, las dos decisiones de los datos, la discriminación, **los 49 de 53 a `ok_parcial`**, **la comprobación cruzada de las 0 fugas en 118 aristas** y **la limitación de subdirectorios** | `contrato-quinto-punto.md` §2, §3 |
| **§4.2 · caso `resvg`** | «La regla que lo atraparía cuesta del orden de 26 ms y está **PENDIENTE**» | **IMPLEMENTADA**, con la tabla de coste por tamaño y las tres lecturas — la tercera es **la refutación de «verificar en proceso» para píxeles**, con el punto de cruce. **+ la frontera confirmada como arquitectura con sus dos pruebas**, **+ que el contrato no puede juzgar intención que el pedido no exprese**, **+ la familia de cinco miembros** | ídem §4, §5 |
| §4.2 · prototipo | 3.859 líneas | **4 185**, con el interruptor de V2 y su salvedad de comparabilidad, los cambios de firma, y **el fallo de `_gs_texto` corregido** | ídem §1, §7, §8 |
| **§4.5 · regla de ppp** | `clamp(nativos, 100, 200)` en bloque de código | **Bloque de código REESCRITO** con la regla por motor y su tabla de `k`, más un bloque nuevo de refutación: las tres candidatas, el experimento decisivo, los siete óptimos, el precipicio, **el mecanismo sondeado en ejecución y el error de deducirlo**, **la consecuencia de arquitectura**, **el límite de VRAM** y tres precisiones. **El bloque del techo absoluto se conserva marcado como histórico** | `ppp-y-normalizacion.md` §2 |
| §4.5 · `OcrOptions.scale` | «Fijarlo siempre, explícitamente **a los ppp nativos**» | **+ matiz medido: su defecto es indiferente en 4 de 5 escaneados y MEJOR en `d3` (−17,72 puntos).** Fijarlo sigue siendo obligatorio; **«a los ppp nativos» era la parte equivocada** | ídem §2.1b |
| **§4.5 · normalización** | «**PENDIENTE:** validar fuera de este corpus» | **VALIDADA con condición**, con la tabla de los tres casos peores, **las tres lecturas**, **la tabla `NORMALIZACION_DETECTOR` por checkpoint**, docling 7/7, la comprobación de que llegó, y el mecanismo con fichero y línea | ídem §3 |
| §4.5 · B11 | «Un defecto de configuración que FileX arrastra hoy» | **+ el parche con su contenido NUEVO y su saldo declarado (7/2/2)**, marcado **propuesto, no aplicado** | ídem §4 |
| **§4.6 · R18** | Directorio desechable, declarado | **+ «⚠ NO ES HIGIENE: ES REQUISITO DE COSTE»**, con las dos cifras. **R18 es lo que hace viable el quinto punto, no un acompañamiento suyo** | `contrato-quinto-punto.md` §2.2 |
| **§5 (tabla de reglas)** | Fila de ppp con techo absoluto · fila de normalización | **La de ppp reescrita a regla por motor** · **la de normalización acotada a `PP-OCRv6 small`** · **la de «verificar en proceso» partida en dos regímenes** · **+5 filas nuevas**: límite de ppp por VRAM · fuerza lo que el motor no deduce · `-frames:v 1 -update 1` · densidad ajustada a página · emparejar escritor y lector | los tres |
| **§6 (trampas)** | 14 | **17.** **15** · el lock de GPU es de proyecto, no de máquina. **16** · el testigo de ruido necesita su propio tope, y las cifras absolutas de tandas distintas no son comparables. **17** · Q16-HDRI y la referencia ideal degradada. *(Y la 14 gana la confirmación desde otro carril: el `build` decide 19 casos y la parametrización 8.)* | los tres |
| §7 · hito 1 | «Hoy la arista es utilizable pero **no verificable**» | **Actualizado a medias:** `ocr: true` implementado, **pero `P9` refutada**; **el sustituto la hace verificable con un coste que el camino caliente no paga**. **+ `qpdf` y `tesseract` con su coste**, **+ el contraste de los dos modos de fallo del mismo motor**, **+ `escaneado_d2` refutando R1 para Tesseract** | `contrato-quinto-punto.md` §6 · `invocacion-aristas.md` §9 |
| **§7 · hito 3** | Criterio de aceptación de cinco fallos | **+3 añadidos:** el punto 5 tiene que correr **dentro** de la conversión · **el patrón oro es un test flojo para él** y hay que ampliarlo · **el caso de `resvg` entra en la suite de regresión, nunca en el camino caliente** | ídem §3.3, §4 |
| §7 · hito 6 | Presupuesto de VRAM y las tres cosas del 21/08 | **+3 más**: el presupuesto tiene que llevar el `k` dentro · la ruta recomendada gana su condición por checkpoint · **el registro LRU necesita `k` por motor**, porque la resolución que cada motor pide **ya no es la misma** | `ppp-y-normalizacion.md` §7, §3 |
| §8 · trampas de pruebas | 5 | **6.** La 5 pasa de «propuesta calibrada sobre 5 puntos» a **REFUTADA con su sustituto**; la **6 es nueva**: *una regla puede ser correcta y su SONDA estar rota* | `contrato-quinto-punto.md` §6, §8 |
| §9 (referencias) | 27 filas | **+3**, y **`ocr-ppp-nativos.md` pierde el «es la referencia buena»**: su §9 (R1) queda marcada como **SUPERADA** | — |

### 1.4 `RESULTADOS-MCP.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| **§7** | El quinto punto, declarado | **Implementado y medido**, con su coste con y sin R18, la discriminación, **el disparador por ubicación y no por reparto de bytes**, **los 49 de 53 a `ok_parcial`**, y **la comprobación cruzada de las 0 fugas en 118 aristas** con su lectura (**fuga y fallo son poblaciones disjuntas**) | `contrato-quinto-punto.md` §2, §3 · `invocacion-aristas.md` §7.4 |
| §7 · caso `resvg` | «El primero que el contrato no atrapa» | **+ I9 lo atrapa 6/6, con su coste real** · **+ la familia de cinco miembros y el que sigue descubierto** · **+ el acotamiento confirmado con su formulación precisa** · **+ el sexto candidato de los crudos Q16-HDRI** | ídem §4, §5 · `invocacion-aristas.md` §4.1 |
| **§10 · R18** | Directorio desechable | **+ «⚠ NO ES HIGIENE: ES REQUISITO DE COSTE»**, con las dos cifras | `contrato-quinto-punto.md` §2.2 |
| §12 · contradicción de tokens | «Sigue abierta» (revisión de las 10:00) | **Sigue abierta, y se dice explícitamente que ninguno de los tres informes de esta pasada la toca** — miden ppp, invocación y contrato. **Las cifras vigentes siguen siendo las de §4** | §4 · `00-mcp-componentes.md` §3.5 |
| **§13.2** | 11 pendientes | **Tres cerrados** (quinto punto + R18, la regla de `resvg`, `qpdf`+`tesseract`) **y +5 nuevos**: el miembro descubierto, validar el sustituto de `P9` a escala, ampliar el patrón oro con una salida multifichero, y el punto de cruce para píxeles | `contrato-quinto-punto.md` §10 · `invocacion-aristas.md` §9 |
| §14 (índice) | 15 filas | **+3**: los dos informes nuevos que le tocan y sus salidas | — |

### 1.5 `ANALISIS-COMPLETO.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| §1 · difer. 1 | «El octavo NO lo atrapa el contrato» | **+ «I9 sí lo atrapa, 6/6» + «pero era una FAMILIA de cinco miembros y uno sigue descubierto»** | `contrato-quinto-punto.md` §4, §5 |
| §1 · difer. 2 | «50,5 % global, 3,0 % en el estrato PDF» | **+ «el 18,8 % era invocación → 41,0 % real, con 3 226 aristas de ganancia automática»** | `invocacion-aristas.md` §0 |
| §1 · pendientes | 7 abiertos de OCR y contrato | **Siete cerrados** (invocación, gs+Gotenberg, `qpdf`+`tesseract`, la normalización, la curva de ppp, `P9`, el quinto punto + I9) **y tres abiertos nuevos** (el `k` por motor, la profundidad de los crudos de terceros, el miembro descubierto) | los tres |
| **§3.4 (bloque nuevo)** | El 50,5 % con su método y su tabla por estrato | **+ «el 50,5 % tiene ahora su cota por arriba»**, con las tres categorías, **la afirmación de producto**, lo que impide inflarla, el gradiente invertido, lo que más rinde, y **el censo documental que coincide con el 3,0 % por un camino independiente** | `invocacion-aristas.md` §0, §3-§8 |
| **§5.5 · ppp** | «Propuesta `clamp(nativos, 100, 200)`, PENDIENTE de barrer» | **+ bloque nuevo: al barrer la curva cayó también el techo absoluto.** Las tres candidatas, el experimento decisivo, los siete óptimos, el mecanismo sondeado, **la consecuencia de arquitectura** y el límite de VRAM | `ppp-y-normalizacion.md` §2 |
| **§5.5 (bloque nuevo)** | — | **La normalización validada con su lado malo**, con la tabla de casos peores y la lectura de que **el desajuste es universal y el daño no** | ídem §3 |
| **§5.5 · `resvg`** | «PENDIENTE la regla que lo atraparía» | **+ dos bloques nuevos**: **I9 con sus dos sorpresas** (el coste ×94 y la familia), con la refutación de «en proceso siempre gana» dentro; **y el quinto punto implementado**, con los 49 de 53 a `ok_parcial` | `contrato-quinto-punto.md` §2-§5 |
| §8 (respaldo) | 27 filas | **+3**: los tres informes con lo que aporta cada uno | — |

### 1.6 `analysis/00-matriz-formatos.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Aviso de lectura | «El descuento medido: 50,5 %» | **+ «el descuento tiene a su vez su propia recuperación»**, con la instrucción de **citar los tres números juntos** (50,5 declarado · 41,0 con invocación cuidada · 3,0-3,1 en el estrato documental) **o cualquiera engaña** | `invocacion-aristas.md` §0 |
| **§6 (sección nueva)** | — | **«Y el descuento tiene su propia recuperación»**: las tres categorías; **qué le pasa exactamente a las cuatro filas de su propia tabla de §2** (21 de 33 semiaristas de salida **no son invocación en absoluto**, y tres de las de ImageMagick **no son destinos de conversión sino extractores de propiedad**); **los 20 crudos con sus CUATRO datos** y **el sesgo de que las semillas las escribió el propio ImageMagick a 16 bits**; y **`imagen → pdf` con densidad ajustada a página** | ídem §3-§7 |
| **§6.1 (nueva)** | — | **El censo completo de Ghostscript y Gotenberg al 3,1 %**, con la coincidencia independiente con su propio §3, `epub → pdf` reproducido por tercera vez, y el sesgo de las 72 extensiones sin semilla | ídem §8 |
| **§6.2 (nueva)** | — | **Lo que esto cambia en cómo se cita el documento**: los dos números de «una tabla declarada no es una capacidad», **la promesa concreta de 3 226 aristas**, la sexta dimensión confirmada, y **la condición de método del sondeo** (emparejar escritor y lector) | ídem §7.1, §10 |

### 1.7 `ESTADO-Y-REPARTO.md`

| Sección | Qué decía | Qué dice ahora | Fuente |
|---|---|---|---|
| Cabecera | «Cuatro agentes han cerrado» (10:00) | **+ bloque «tres agentes más han cerrado, y CORRIGEN a los anteriores» (14:00)**, con las **cuatro cosas que hay que saber antes de lanzar nada**, empezando por **⚠️ el bloque de ppp de §5 está reescrito** | los tres |
| §1 · informes | 15 filas | **+4** con los tres informes de la tarde y esta consolidación | — |
| §2.2 · lo refutado | 11 filas | **18.** **+7**: el techo absoluto de ppp, `P9`, «en proceso siempre gana» para píxeles, el lock de GPU, «`resvg` es un caso aislado», «corregir la normalización mejora el motor» (acotada) y «el 50,5 % es el sector» (acotada) | los tres |
| §2.3 · punto 1 | `clamp(…, 200)`, techo absoluto | **La regla por motor, con su `k`, el techo de coste, el límite de VRAM y el matiz de `OcrOptions.scale`** | `ppp-y-normalizacion.md` §2 |
| **§3 · inventario** | A5/A7 · B3-B12 · C4-C18 | **Cerrados: A8 (nuevo), B9, B10, C9, C10, C11, C12, C13, C15, C17.** **B11 REDEFINIDO.** **Nuevos: B13-B16 y C19-C26.** Cada uno con su cifra de cierre o su motivo | los tres |
| **§4 · reparto** | Oleada 3 «por hacer» | **Oleada 3 EJECUTADA Y CERRADA** (con la nota de que el testigo de proceso notó los tres en paralelo) y **Oleada 4 nueva**, con B13 en cabeza y **A5 dentro de la prioridad alta** | — |
| **§5 · contexto compartido** | Bloque de ppp con techo absoluto · normalización sin condición · dos testigos | **Bloque de ppp REESCRITO ENTERO** (las dos refutaciones, el experimento, la regla por motor, los topes internos sondeados, el límite de VRAM) · **la normalización con su condición por checkpoint** · **+ el lock de GPU que es de proyecto** · **+ los tres casos de testigo y el tope** · **+ el estado del verificador al 14:00** · **+ los dos regímenes de «en proceso»** | los tres |
| §9 | «Las tres cosas que cambian diseño» | **Son otras cuatro, con una de las tres anteriores refutada.** **+ el patrón con cuatro casos: lo que más ha movido el diseño no estaba en la lista de lo que se iba a medir.** **+ el commit con su cifra actualizada (siete agentes, 44 entradas)** | — |
| §10 · referencias | 18 filas | **+4**, con **dos avisos de superación**: la regla de ppp de `ocr-ppp-nativos.md` y el techo absoluto de `corpus-d4.md` §8 | — |

---

## 2. Lo que esta tanda cambia en el DISEÑO de FileX, no en su documentación

*(El resto de esta consolidación es reconciliación de texto. Estos cuatro son código que hay que escribir distinto.)*

### 2.1 La regla de ppp baja del orquestador al adaptador de cada motor

**Qué se creía, en dos versiones sucesivas y las dos escritas de buena fe:** que existía una regla global de ppp, primero relativa (`clamp(nativos, 100, nativos×1,4)`, D1) y luego absoluta (`clamp(nativos, 100, 200)`, D2).

**Qué se midió** (`bench/ppp-y-normalizacion.md` §2, 17 puntos de ppp × 7 configuraciones, mediana de n=9, GPU, dispositivo fijado):

| candidata | qué predeciría | qué se mide | veredicto |
|---|---|---|---|
| **ppp absolutos** (techo 200) | todos se rompen al pasar de 200 | `d3` se rompe a **160**; `d4c`, `d4f` y `patológico` **no se rompen a 400** | **REFUTADA** |
| **factor sobre el nativo** (×1,4) | todos se rompen al mismo factor | PaddleOCR se rompe en `d4` a ×1,4, en `d3` a ×1,6 y **nunca** en `d4c` (×1,6) ni `d4f` (×1,67) | **REFUTADA** |
| **anchura en píxeles** | todos se rompen a la misma anchura | `d3` se rompe a **1 035 px**; `d4c` **no** se rompe a **2 070 px** | **REFUTADA** |

**El experimento que lo decide, y son 24 celdas:** el **mismo JPEG** de `escaneado_d4` reempaquetado en tres páginas de 100, 200 y 400 ppp nativos —con la misma orden del generador del corpus— da, **a los mismos 200 ppp**, CER de **19,13 / 19,63 / 36,24 %** con PaddleOCR y **30,70 / 18,62 / 30,70 %** con RapidOCR; **a los mismos píxeles, las tres filas coinciden a la centésima**, doce parejas exactas. **17,1 puntos de diferencia al mismo ppp, con el mismo documento dentro.**

> **Los ppp no son una propiedad del documento que el OCR pueda usar: son una división entre los píxeles que hay y el tamaño que el PDF dice que tiene la página. Una regla escrita en ppp está escrita en la unidad equivocada.**

**Y la respuesta es la cuarta candidata: la regla es POR MOTOR.** Siete configuraciones sobre el mismo documento con óptimos entre **×0,50 y ×1,80**. Y no es solo el óptimo, **es el precipicio**: sobre `escaneado_d3`, **a ×1,4 el mismo fichero es seguro para PaddleOCR (3,80 %) y catastrófico para RapidOCR+R6 (2,53 → 46,84 %)**.

**El mecanismo, sondeado en ejecución y no deducido:** cada motor lleva su reescalado cableado con constantes propias. `Global.max_side_len: 2000` (`rapidocr/config.yaml:10`) hace que **por encima de 233 ppp RapidOCR reciba el array literalmente idéntico**; PaddleOCR no recorta. **Deducirlo del código de PaddleX daba lo contrario** —los ocho detectores aparecen con `limit_type='max'`, 960 px— **y su propio informe lo publica como error cometido**. Es la regla de la casa *«sondear capacidades en ejecución, no deducirlas»* confirmada una vez más, y esta vez el error se conserva escrito.

> ### **Qué hay que construir distinto: la elección de ppp pertenece al ADAPTADOR DE CADA MOTOR, no al orquestador.**
> El orquestador calcula `ppp_nativos` y lo pasa; cada adaptador aplica su `k`. **Hoy `clamp(...)` está escrita como regla global en `CLAUDE.md` y en `PLAN-ORQUESTADOR.md` §4.5: está en el sitio equivocado del diseño.** No es una constante del dominio, es **un parámetro del motor, del mismo rango que `Det.mean` o `OcrOptions.scale`**. **Si se queda en el orquestador, cada motor nuevo hereda en silencio los ppp que le convenían a otro** — que es literalmente lo que le pasa hoy a Tesseract, al que R1 le asigna 100 ppp sobre `escaneado_d2` y **le cuesta 32,10 puntos**.

**Y el defecto propio del techo absoluto, que es el detalle que lo remata:** su techo **solo actúa bajando**, y bajar cuesta **12,08 puntos** (`d4` de 200 a 100 ppp: RapidOCR+R6 de 18,62 % a 30,70 %). **Además, la evidencia que lo motivó —`d4` a 280 ppp— es un caso que la regla relativa nunca produce**, porque `clamp(200, 100, 280)` devuelve 200. **El techo absoluto se escribió para arreglar un problema que la regla anterior no podía causar**, y eso queda escrito como autoerror del proyecto.

**Lo que sí queda como regla global, y es de presupuesto y no de precisión:** hay que poner **algún** límite, porque barrer hasta 400 ppp **con una sola página** llevó a **PaddleOCR a 11 942** y a **EasyOCR a 12 037 de 12 288 MiB, sin dar error**. **El límite existe por VRAM aunque no exista por calidad.**

**Evidencia externa convergente, desde fuera de los cuatro motores neuronales:** `bench/invocacion-aristas.md` §9 midió que **`escaneado_d2` refuta R1 para Tesseract** — **0,00 % a 150 ppp frente a 32,10 % a sus 100 nativos**: a Tesseract sobremuestrear **no le es tolerable, le es obligatorio**. *(Es n=1, con otro arnés, y se cita como convergente, no como reproducción.)*

### 2.2 R18 deja de ser higiene y pasa a ser requisito de coste

**Qué se creía:** que el directorio de trabajo desechable era buena práctica de confinamiento y que el quinto punto costaba «listar un directorio dos veces, trivial».

**Qué se midió** (`bench/contrato-quinto-punto.md` §2.2, mediana n=15):

| Configuración | Mediana | Frente al contrato de 4 puntos |
|---|---:|---:|
| **Contrato SIN punto 5** | **0,4254 ms** | ×1 |
| **+ punto 5 CON R18** (solo se censa después) | **0,4722 ms** | **×1,11** |
| + punto 5 **sin R18**, 2 ficheros | 0,5138 ms | ×1,21 |
| + punto 5 **sin R18**, **1 000 ficheros** | **3,6614 ms** | **×8,6** |

**La lógica del punto 5 es gratis (0,031–0,037 ms). Lo caro es el censo, y R18 lo divide por dos y lo acota a un directorio que solo contiene lo que acaba de escribirse.** Es la cuarta medida seguida de la misma constante del proyecto: *fabricar el acceso al dato es el coste, no la regla*.

> **Qué hay que construir distinto: R18 pasa de «higiene del confinamiento» a «la condición que mantiene el quinto punto en el camino caliente». Eso reordena su prioridad en `PLAN-ORQUESTADOR.md` §4.6: no es un acompañamiento del punto 5, es lo que lo hace viable.**

### 2.3 El punto 5 no es verificable a posteriori — y eso decide dónde vive la verificación

**Falsos positivos que añade sobre el patrón oro: CERO**, reejecutando las 39 órdenes en directorio desechable. **Y 0 avisos en las tres salidas legítimamente multifichero** (HLS, dos secuencias `%d`), con el **fallo mantenido en el DASH incluso declarando `multifichero: true`**, porque escribe en el `cwd`.

**Pero su coste honesto es un cambio de naturaleza, no de precio:**

> **Sin censo, 49 de las 53 salidas del patrón oro bajan de `ok` a `ok_parcial`.** No es un falso positivo: es el verificador diciendo *«no puedo saber si el motor escribió en otro sitio, porque nadie miró cuando tocaba»*. **El punto 5 es el primero del contrato que no se puede evaluar después: hay que estar mirando cuando el motor escribe.**
>
> **Qué hay que construir distinto: la verificación tiene que estar DENTRO de la conversión, no ser un paso posterior que se pueda hacer luego.** Un `verificar(ruta)` que se llame más tarde **no puede aprobar este punto, y hace bien en no aprobarlo**.

**Y dos decisiones que salieron de los datos y no de la especificación**, las dos hay que respetarlas: **el disparador es la UBICACIÓN, no el reparto de bytes** (un manifiesto HLS legítimo lleva el 0,0 % de los bytes igual que el `.mpd` roto: un detector por tamaño marcaría toda salida en streaming como fallo), y **declarar `multifichero: true` no autoriza a escribir en el `cwd`**.

### 2.4 «Verificar en proceso siempre gana» tiene dos regímenes

**Qué se creía:** una constante de diseño del proyecto, escrita en `CLAUDE.md` §5 y `PLAN-ORQUESTADOR.md` §4.2 desde `bench/coste-verificacion.md`, y apoyada en un 145×.

**Qué se midió** (`bench/contrato-quinto-punto.md` §4.3, mediana n=9), al implementar I9:

| Rasterizado | tinta **en proceso** | tinta **con `magick`** | |
|---|---:|---:|---|
| 400×200 (0,08 Mpx) | 38–56 ms | 37–42 ms | empatan |
| 800×400 (0,32 Mpx) | 452 ms | **66 ms** | ×6,8 |
| **1920×960 (1,84 Mpx)** | **2 834 ms** | **138 ms** | **×20,5** |

> **Sigue siendo cierto para cabeceras —donde es 145×— y es FALSO en cuanto hay que recorrer píxeles. El punto de cruce está en ~0,1 Mpx.**
>
> **Va con matiz, no como corrección total: la regla correcta no es «siempre en proceso», es «en proceso para cabeceras y rasters pequeños; con la sonda externa a partir de ~0,1–0,3 Mpx».**

**Es el mismo fenómeno que `verificador-fidelidad.md` §7.2 ya había anotado para el decodificador VP8L** («por debajo de ~0,3 Mpx gana a `magick`; por encima pierde»), ahora **medido en otra regla y con otro formato**: deja de ser una rareza de un decodificador y pasa a ser una frontera. *(La implementación entregada usa el camino en proceso **porque no añade dependencias**, y esa elección tiene un precio medido.)*

---

## 3. Lo que se ha refutado a sí mismo el proyecto en un día

**Esto no es una lista de errores: es el material del que este repositorio presume.** `CLAUDE.md` §3 dice que *refutar una conclusión propia es el resultado más valioso que se puede traer*, y el 21 de agosto lo hizo **seis veces, sobre sus propias escrituras de las horas anteriores**.

| # | Lo que el proyecto había escrito | Quién lo escribió | Quién lo refuta | Con qué |
|---|---|---|---|---|
| 1 | **El techo RELATIVO de ppp: `clamp(nativos, 100, nativos×1,4)`** | D1, 04:30, correctamente desde `ocr-ppp-nativos.md` §9 | **G1, 09:10** | Sobre `d4` (200 ppp nativos) el ×1,4 **empeora a PaddleOCR 16,9 puntos** |
| 2 | **El techo ABSOLUTO que lo sustituyó: `clamp(nativos, 100, 200)`** | D2, 10:00, desde `corpus-d4.md` §8 | **P1, 13:40** | **Los ppp no son la unidad** (24 celdas). Y su techo **solo baja**, lo que cuesta 12,08 puntos; **y la evidencia que lo motivó era un punto que la regla anterior no producía** |
| 3 | **`P9`: longitud media de token ≥3,0 y <50 % de tokens de una letra** | V1, 09:40, marcada como propuesta; **D2 la llevó a los maestros a las 10:00** | **P3, 13:00** | **8,3 % de sensibilidad** sobre 32 capas OCR reales y **36 % de falsos positivos** sobre 14 legítimas. **Alucinar no produce ruido corto: produce palabras largas y plausibles** |
| 4 | **«Verificar leyendo en proceso, no con subprocesos»** — constante de diseño desde `coste-verificacion.md` | El proyecto, desde el 20/08 | **P3, 13:00** | **`magick` mide lo mismo en 138 ms donde el lector en proceso tarda 2 834.** Cierta para cabeceras, **falsa para píxeles** |
| 5 | **«CPU y GPU dan la misma salida, carácter a carácter»** | `gpu-fase2.md` §2 | G1, 09:10 | **5 de 21 celdas difieren**, y la CPU es mejor en dos y peor en tres |
| 6 | **«El lock de GPU protege la medición»** | El arnés, desde siempre | **P1, 13:40** | Es un lock **de proyecto**: otra sesión de Claude en **otro repositorio de la misma máquina** ocupó 11 754 de 12 288 MiB y dejó una tanda **12 minutos parada** |

**Y hay tres más, del mismo día, que acotan en vez de refutar:**

- **«Los cuatro puntos del contrato atrapan los fallos del sector»** → **acotada**: el octavo no. *(Y a las 14:00 se acota la acotación: `resvg` **no era un caso aislado**, era **una familia de cinco miembros**; I9 atrapa uno más y **uno sigue descubierto**.)*
- **«El 50,5 % de las aristas declaradas no existe»** → **acotada**: **el 18,8 % era invocación**, no capacidad.
- **«Corregir la normalización del detector mejora el motor»** → **acotada**: **el desajuste es universal, el daño no.** Aplicarla a ciegas **empeora 12 de 42 celdas**.

**Cuatro observaciones que salen de la lista, y ninguna es cosmética:**

1. **Las refutaciones 1 y 2 son consecutivas sobre la misma regla, en el mismo día.** El proyecto escribió una regla, la refutó con un documento nuevo, escribió su sustituta, y **refutó también la sustituta nueve horas después**. **La versión que sobrevive no es la tercera constante: es el reconocimiento de que no hay constante** — y ese es un resultado de otra clase, porque **mueve la regla de sitio en la arquitectura**.
2. **La refutación 3 la produjo el propio proyecto sobre una regla que él mismo acababa de proponer.** `P9` se escribió **marcada como no validada**, se validó **con el encargo explícito de buscarle los fallos**, y se tiró. **El sistema funcionó exactamente como estaba diseñado.**
3. **La refutación 4 es la más incómoda, porque tocaba una constante de diseño y no una medida.** «En proceso siempre gana» sostenía decisiones desde tres documentos. **No cae entera: cae su alcance**, y lo que queda es más útil que lo que había —una frontera con su punto de cruce— que lo que había, que era un eslogan.
4. **La refutación 6 no es sobre el objeto de estudio: es sobre el instrumento.** Y viene acompañada de la **tercera** aparición en un día del punto ciego del testigo de ruido, y de **un fallo del propio verificador** (`_gs_texto` devolviendo vacío 6 de 430 veces por tubería). **Tres de los hallazgos del día son sobre las herramientas de medir, no sobre lo medido.** *La sonda no es la verdad, es otra medida con sus propios defectos* — y esta vez **dos de los defectos eran nuestros**.

> **Y el patrón que ya se puede afirmar con cuatro casos:** *lo que más ha movido el diseño de FileX no estaba en la lista de lo que se iba a medir.* La normalización del detector salió de un encargo sobre corpus; el quinto punto, de una campaña que iba a **contar** aristas; el fallo de `_gs_texto`, de un encargo sobre el contrato; y **la refutación de «en proceso siempre gana», de medir el coste de una regla de fidelidad**. **No es un fallo de planificación: es el argumento a favor de ejecutar.**

---

## 4. Contradicciones: se escriben, no se resuelven

### 4.1 Las tres que seguían abiertas de las pasadas anteriores

| # | Qué choca | Los dos sitios | Estado tras esta pasada |
|---|---|---|---|
| 1 | **EasyOCR en d3: ¿57,0 % o 59,5 %?** | `bench/gpu-fase2.md` §3 dice **57,0 %** · `bench/ocr-ppp-nativos.md` §2 reproduce **59,5 %** | **SIGUE COMO ESTABA: son la lectura de CPU y la de GPU de la misma casilla**, y desde `corpus-d4.md` §9.3 se sabe que **eso no es una rareza de una celda** (5 de 21 difieren). **Ninguno de los tres informes de esta pasada la toca.** Los tres fijaron el dispositivo, que es justo la consecuencia que la contradicción dejó escrita |
| 2 | **Tokens de catálogo: ¿7.964/2.322, 7.886/2.306, o ≈3.610/≈811?** | `RESULTADOS-MCP.md` §4 · `saturacion-herramientas.md` §2.2 · `analysis/00-mcp-componentes.md` §3.5 | **SIGUE ABIERTA, y ninguno de los tres informes de esta pasada la toca** — miden ppp, invocación de motores y el contrato de verificación. **El factor 2,2 frente a componentes sigue sin explicación.** **Las cifras vigentes son las de `RESULTADOS-MCP.md` §4.** Anotado allí; el fichero de componentes es de otro carril |
| 3 | **El 99,0 % de similitud de I1** | `bench/fidelidad-caminos.md` §3 dice **99,0 %** · `bench/verificador-ghostscript.md` §5.7 obtiene **94,7–97,1 %** | **SIGUE NO REPRODUCIDO, no refutado**, y **esta pasada no lo toca**. Se mantiene la prudencia: `fidelidad-caminos.md` **no publica ni sus ppp, ni su idioma de OCR, ni su fórmula de similitud**. Lo MEDIDO sigue siendo que el orden de magnitud correcto es **94-97 %** y que la pérdida es **espacios, no letras**. Es el pendiente C18 |

### 4.2 Las correcciones de esta pasada a la anterior — secuencia, no contradicción

| Qué | Quién lo escribió | Quién lo corrige | ¿Podía saberlo? |
|---|---|---|---|
| `clamp(nativos, 100, 200)` como techo absoluto, en cinco sitios | **D2**, a las 10:00, correctamente desde `corpus-d4.md` §8 | **P1**, a las 13:40, con un barrido de 17 puntos que no existía | **No.** Y su propio informe lo marcó **PENDIENTE de barrer la curva** en los cinco sitios: **la corrección llega por donde D2 dijo que llegaría** |
| `P9` llevada a los maestros como propuesta calibrada sobre 5 puntos | **D2**, a las 10:00, desde `verificador-ghostscript.md` §5.8 | **P3**, a las 13:00 | **No.** V1 la marcó como *«propuesta, NO una regla validada»* y D2 conservó esa marca literalmente en los cuatro sitios donde la escribió |
| «La regla de `resvg` cuesta del orden de los 26 ms del grupo C» | **D2**, desde `aristas-nominales.md` §8.2 | **P3**: **32–2 454 ms, ×94 sobre la estimación** | **No.** Era una estimación declarada como tal |
| «El coste de integración de los 7 `no_evaluable` es dos motores» | **D2**, desde `aristas-nominales.md` §8 | **P2**, que lo cuantifica: **50 MB y 28 segundos** | Es una **confirmación con número**, no una corrección |
| El prototipo del verificador «3.859 líneas» en tres maestros | **D2**, desde `verificador-ghostscript.md` §6 | **P3**, que lo deja en **4 185** — y **no consigue reproducir las 3 859** (implican ~3 530 de partida) | **La discrepancia queda anotada en `HUECOS.md` §1 como lo que es: no afecta a ninguna conclusión, pero rompe la trazabilidad del recuento entre informes.** **Y va por partida doble: al consolidar, el fichero tiene 4 567 líneas, porque hay OTRO agente editándolo** (§6.1). **Las 4 185 se citan como la medida de P3 sobre el fichero que él dejó** |

**Ninguna de estas cinco es un error de D2**, igual que ninguna de las cinco de la pasada anterior lo era de D1. **Se documentan aquí para que la traza quede completa**, y en cada maestro **la cifra vieja queda tachada o entre paréntesis, no borrada**.

### 4.3 Y una tensión nueva que conviene no perder

**`bench/invocacion-aristas.md` §7.4 mide 0 fugas en 118 aristas**, mientras `bench/aristas-nominales.md` §5.2 encontró dos fugas que motivaron el quinto punto entero. **No es una contradicción, y su propio informe lo resuelve bien:** los dos casos de fuga tienen destinos —`mpd`, `html`— que **no aparecen entre las 118 aristas nominales**, porque **esas dos aristas no fallaban: entregaban un fichero incompleto**. **Fuga y fallo son poblaciones disjuntas**, y eso **refuerza** el quinto punto en vez de debilitarlo: ni los cuatro puntos ni el juez de aristas nominales las ven.

---

## 5. Lo que este trabajo cierra, en cifras

| | Antes de esta pasada | Ahora |
|---|---|---|
| Reglas de ppp vigentes en los maestros | 1 global (`clamp(…, 200)`) | **1 por motor, en el adaptador**, con `k` medido para cinco motores |
| Miembros conocidos de la familia de `resvg` | 1 | **5** (+1 candidato por otra vía), **de los que el contrato atrapa 1, I9 atrapa 1 y 1 sigue descubierto** |
| Puntos del contrato implementados y medidos | 4 | **5** |
| Líneas del prototipo `verificador.py` | 3 859 | **4 185** |
| Reglas de fidelidad | 13 | **15** (I9 y P9) |
| Tasa de aristas nominales | 50,5 % | **41,0 % con invocación cuidada**, y **3,0-3,1 % en el estrato documental** |
| Casos `no_evaluable` de `referencia.json` | 2 (`qpdf`, `tesseract`) | **0** — con su coste medido |
| Trampas de `CLAUDE.md` §4 | 22 | **24** |
| Trampas de `PLAN-ORQUESTADOR.md` §6 | 14 | **17** |
| Reglas no negociables de `PLAN-ORQUESTADOR.md` §5 | 22 filas | **27** |
| Tesis del proyecto refutadas **por el propio proyecto** el 21/08 | 6 | **12** *(6 refutadas + 3 acotadas de la mañana, +3 refutadas de la tarde)* |

---

## 6. El commit — preparado, **NO ejecutado**

**No se ha hecho `git add` ni `git commit`.** Esto **sustituye** a `bench/consolidacion-2-21ago.md` §5.

### 6.1 Estado real del árbol (`git status --short`, 21/08 14:10)

**14 modificados · 32 sin versionar = 46 entradas** (contando este informe, que aún no aparecía al contar). **Van SIETE agentes sin commit.**

> ### ⚠️ Aviso: el encargo decía «no hay ningún otro agente corriendo», y **el árbol dice que sí**
>
> Al inventariar aparecieron **dos directorios que no son de ninguno de los siete informes cerrados, con escrituras de hace minutos**:
>
> | Directorio | Ficheros | Tamaño | Última escritura | Informe `.md` |
> |---|---:|---:|---|---|
> | `bench/salidas-firmas/` | 14 | 846 KB | **14:05:51** | **no existe** |
> | `bench/salidas-mcp-cabos-2/` | 91 | 250 KB | **14:05:05** | **no existe** (sería el de M1, «sin lanzar») |
>
> **Los dos quedan EXCLUIDOS del commit**, por la misma regla con que D1 y D2 excluyeron el trabajo en vuelo de otros agentes: **no tienen informe que los explique y su autor no ha cerrado.** *(El contenido de `salidas-firmas/` sugiere un censo de firmas de formato —C14—, y el de `salidas-mcp-cabos-2/` los cabos de M1 —C4/C5—, pero **eso es inferencia mía leyendo nombres de fichero, no un dato**, y por eso no se versiona ni se documenta como cerrado.)*
>
> **Y hay una segunda señal, más dura que las fechas: `bench/scripts/verificador.py` tiene HOY 4 567 líneas, y P3 lo dejó en 4 185.** Alguien lo ha editado después de que P3 cerrara — lo que encaja con `salidas-firmas/`, porque **ampliar el vocabulario de firmas (C14) se toca justo ahí**. **Las 4 185 se citan en los maestros como lo que son: la medida de P3 sobre el fichero que él dejó.**
>
> **Consecuencia operativa, y son dos:** **(1)** comprueba `git status --short` justo antes del `git add`; si esos dos directorios han ganado su `.md`, entran, y si no, se quedan fuera y se commitean con su informe. **(2) `bench/scripts/verificador.py` está siendo editado ahora mismo: commitearlo partiría el trabajo de ese agente en dos.** **Conviene esperar a que cierre**, exactamente como D1 decidió esperar a V1.

### 6.2 Qué INCLUIR

**Maestros y análisis (14 ficheros):**

```
ANALISIS-COMPLETO.md   CLAUDE.md   HUECOS.md   PLAN-ORQUESTADOR.md   RESULTADOS-MCP.md
AGENTES-PRUEBAS-PENDIENTES.md      ESTADO-Y-REPARTO.md
analysis/00-licencias.md           analysis/00-matriz-formatos.md
analysis/00-mcp-componentes.md     analysis/00-mcp-filesystem.md
analysis/00-mcp-patrones.md        analysis/OCRmyPDF.md
bench/gpu-fase2.md
```

**Los diez informes y las tres consolidaciones:**

```
bench/verificador-fidelidad.md     bench/mcp-cabos-sueltos.md
bench/saturacion-herramientas.md   bench/ocr-ppp-nativos.md
bench/corpus-d4.md                 bench/aristas-nominales.md
bench/verificador-ghostscript.md
bench/ppp-y-normalizacion.md       bench/invocacion-aristas.md
bench/contrato-quinto-punto.md
bench/consolidacion-21ago.md       bench/consolidacion-2-21ago.md
bench/consolidacion-3-21ago.md
```

**El código:** `bench/scripts/verificador.py` (3 035 → 3 859 → **4 185 líneas** cuando P3 cerró, sin dependencias nuevas). **⚠️ Pero hoy tiene 4 567 y sigue creciendo: hay otro agente dentro. Si no ha cerrado cuando se ejecute el commit, sácalo de la lista y que entre con su informe.**

**El corpus nuevo — por Git LFS** (`git check-attr filter` responde **`filter: lfs`**, comprobado):

```
corpus/pdf/escaneado_d4.pdf   escaneado_d4a.pdf   escaneado_d4b.pdf
corpus/pdf/escaneado_d4c.pdf  escaneado_d4e.pdf   escaneado_d4f.pdf
corpus/pdf/MANIFIESTO-d4.md
```

**Los diez directorios de salidas — su parte de TEXTO:**

| Directorio | Ficheros | Tamaño | Nota |
|---|---:|---:|---|
| `bench/salidas-mcp-cabos/` | 75 | 191 KB | ya listado por D1 |
| `bench/salidas-ocr-ppp/` | 341 | 334 KB | ídem |
| `bench/salidas-saturacion/` | 26 | 1 038 KB | ídem |
| `bench/salidas-verificacion-fidelidad/` | 13 | 143 KB | ídem |
| `bench/salidas-corpus-d4/` | 504 | 1 109 KB | ya listado por D2 |
| `bench/salidas-verificador-gs/` | 47 | 316 KB | ídem |
| `bench/salidas-aristas/` | 98 | 1 217 KB | ídem — **texto salvo 32 binarios, ver §6.3** |
| **`bench/salidas-ppp-norm/`** | **414** | **1 144 KB** | 100 % texto: `.py`, `.json`, `.txt`, `.sh`, `MANIFIESTO.md`. Incluye las **296+ salidas de OCR** del barrido |
| **`bench/salidas-invocacion/`** | **112** | **1 064 KB** | 100 % texto tras podar. **Su autor borró 380 MB regenerables** (`pool/` con 225 MB de semillas, `aristas.json` de 5,8 MB, los binarios de `c13/`) y dejó `MANIFIESTO.md` con `sha256` y orden exacta |
| **`bench/salidas-quinto-punto/`** | **53** | **355 KB** | 100 % texto. **Los dos PNG grandes ya borrados**, con su `sha256` y su orden de reproducción |

> **Por qué entran los tres nuevos enteros:** es exactamente lo que `CLAUDE.md` §6 manda versionar —los `.md`, los scripts, los `.json` de resultados y **los logs**—, **y los tres hicieron su limpieza, cada una documentada**. En particular, `salidas-quinto-punto/texto/*.txt` contiene **el texto de las 32 capas OCR** de la validación de `P9`, que es lo que permite **reanalizarlas sin volver a pasar el OCR**: es trazabilidad barata de una refutación.

### 6.3 Qué EXCLUIR

| Qué | Por qué |
|---|---|
| **`bench/salidas-firmas/` y `bench/salidas-mcp-cabos-2/`** (14 + 91 ficheros, 1,1 MB) | **Trabajo en vuelo de otro agente, escrito hace minutos y SIN informe que lo explique.** Ver el aviso de §6.1. **Que cada agente cierre el suyo** |
| **Los 32 binarios de `bench/salidas-aristas/`** (~440 KB en `c8/in/`, `c8/out/**` y `fuga/`) | `CLAUDE.md` §6: **no se versionan salidas binarias regenerables.** `bench/salidas-aristas/MANIFIESTO.md` las cubre todas con nombre, `sha256`, tamaño y orden exacta. **Los `.html` y `.shtml` de `fuga/` SÍ entran: son texto y son la prueba literal de la fuga.** Añádelos a `.gitignore` con el patrón que el fichero ya usa para `salidas-fase1/2/fidelidad` (excluir el directorio, volver a incluir `MANIFIESTO.md`, `.json`, `.py`, `.sh`, `.md` y logs) |
| **`bench/.gpu.lock`** | Estado de ejecución, no evidencia. **Nunca se versiona.** Añadirlo a `.gitignore`. *(No aparece hoy en `git status`, pero puede aparecer.)* |
| Cualquier salida binaria regenerable | `CLAUDE.md` §6. El repositorio ya pagó una vez **986 MB de pack, 99,9 % binario** |

### 6.4 Orden propuesta

```bash
# 0) Comprobar que LFS va a tomar los PDF del corpus. Si esto no dice "lfs", PARA.
git check-attr filter -- corpus/pdf/escaneado_d4.pdf     # -> filter: lfs  (comprobado)

# 1) Comprobar si salidas-firmas/ y salidas-mcp-cabos-2/ han ganado su informe .md.
#    Si NO lo tienen, se quedan fuera (ver §6.1).
git status --short

# 2) .gitignore: el lock y los binarios de salidas-aristas, con sus negaciones.

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
        bench/ppp-y-normalizacion.md bench/invocacion-aristas.md \
        bench/contrato-quinto-punto.md \
        bench/consolidacion-21ago.md bench/consolidacion-2-21ago.md \
        bench/consolidacion-3-21ago.md \
        bench/salidas-mcp-cabos/ bench/salidas-ocr-ppp/ \
        bench/salidas-saturacion/ bench/salidas-verificacion-fidelidad/ \
        bench/salidas-corpus-d4/ bench/salidas-verificador-gs/ bench/salidas-aristas/ \
        bench/salidas-ppp-norm/ bench/salidas-invocacion/ bench/salidas-quinto-punto/ \
        corpus/pdf/escaneado_d4.pdf corpus/pdf/escaneado_d4a.pdf \
        corpus/pdf/escaneado_d4b.pdf corpus/pdf/escaneado_d4c.pdf \
        corpus/pdf/escaneado_d4e.pdf corpus/pdf/escaneado_d4f.pdf \
        corpus/pdf/MANIFIESTO-d4.md

git status --short          # que NO entre salidas-firmas/ ni salidas-mcp-cabos-2/
git diff --cached --stat    # que no entre ningun binario fuera de LFS
git lfs status              # que los 6 PDF salgan como LFS objects
```

### 6.5 Mensaje propuesto

```
Diez mediciones y la consolidacion completa de los maestros

Integra en HUECOS.md, PLAN-ORQUESTADOR.md, RESULTADOS-MCP.md,
ANALISIS-COMPLETO.md, CLAUDE.md, ESTADO-Y-REPARTO.md y analysis/ los diez
informes del 21 de agosto. El proyecto se refuta a si mismo seis veces, y
cuatro resultados cambian el diseno y no solo la documentacion.

CAMBIAN EL DISENO

- NO HAY UNA REGLA GLOBAL DE PPP: HAY UNA POR MOTOR, y por tanto la eleccion
  de ppp baja al ADAPTADOR de cada motor. Los ppp no son la unidad: el mismo
  JPEG reempaquetado en paginas de 100/200/400 ppp da 19,13 / 19,63 / 36,24 %
  A LOS MISMOS PPP y coincide A LA CENTESIMA a los mismos pixeles (24 celdas).
  Tampoco valen un factor fijo ni una anchura fija: siete configuraciones
  sobre el mismo documento dan optimos entre x0,50 y x1,80, y a x1,4 sobre d3
  el mismo fichero es seguro para PaddleOCR (3,80 %) y catastrofico para
  RapidOCR corregido (46,84 %). Queda un limite global, pero es de VRAM:
  a 400 ppp con UNA pagina, PaddleOCR llego a 11 942 y EasyOCR a 12 037 de
  12 288 MiB sin dar error.

- R18 (directorio de trabajo desechable) deja de ser higiene y pasa a ser
  REQUISITO DE COSTE: el quinto punto del contrato cuesta +11,0 % con el y
  x8,6 el contrato entero sin el, sobre un directorio de 1 000 ficheros.

- El punto 5 es el primero del contrato que NO es verificable a posteriori:
  sin censo, 49 de las 53 salidas del patron oro bajan de ok a ok_parcial.
  La verificacion tiene que vivir DENTRO de la conversion.

- "Verificar en proceso siempre gana" tiene DOS REGIMENES: cierto para
  cabeceras (145x) y falso para pixeles (magick x20,5 a 1,8 Mpx). El punto de
  cruce esta en ~0,1 Mpx.

REFUTACIONES DEL PROYECTO SOBRE SI MISMO

- El techo relativo de ppp (x1,4) y el techo absoluto (200) que lo sustituyo:
  los dos refutados, el segundo nueve horas despues de escribirse. Su techo
  solo actua bajando (12,08 puntos de coste) y la evidencia que lo motivo era
  un punto que la regla anterior no producia: clamp(200,100,280) = 200.

- P9, la senal contra la alucinacion de OCR: 8,3 % de sensibilidad sobre 32
  capas OCR reales y 36 % de falsos positivos sobre 14 legitimas. Alucinar no
  produce ruido corto: produce palabras largas y plausibles, hasta 7 130
  caracteres de invencion. Sustituto medido, 16/16 sin error: el acuerdo entre
  dos pasadas de OCR con idiomas distintos (bueno >=0,887, ruido <=0,700).

- El lock de GPU no es de maquina, es de proyecto: otra sesion en otro
  repositorio del mismo equipo dejo una tanda 12 minutos parada con 11 754 de
  12 288 MiB ocupados.

- Y un fallo del propio verificador, reproducido: _gs_texto leia por tuberia y
  devolvia vacio 6 de 430 veces (0 de 430 por fichero, al mismo coste), ademas
  de contar 107 caracteres en vez de 105. De esa sonda cuelgan P2 (severidad
  fallo), P5, P6 y P9. Es la observacion que verificador-ghostscript.md no
  consiguio reproducir en 20 intentos.

MEDICIONES

- El 18,8 % del 50,5 % de aristas nominales era INVOCACION, no capacidad
  [IC 95 %: 16,8-21,3]. Con los mismos motores y el mismo build la tasa baja a
  41,0 %. FileX puede ofrecer 3 226 aristas mas que ConvertX (10,2 %) sin
  pedirle nada al usuario, y 5 930 con un canal de metadatos. Lo que no se
  puede prometer es el 81,2 % restante: el 58,5 % de las aristas nominales son
  declaraciones sin sentido (el muxer no admite ninguna pista que la entrada
  tenga) y 19 de las 33 semiaristas de salida muertas de ffmpeg son
  codificadores no compilados, que es build y no invocacion.

- Censo COMPLETO de Ghostscript (9/9 reales) y Gotenberg/Chromium (25/25):
  3,1 % de aristas nominales, que coincide con el 3,0 % del estrato PDF por un
  camino independiente. La superficie documental es donde el grafo se sostiene.

- qpdf y tesseract dejan de ser un pendiente: 8 lineas de Dockerfile, 28,1 s y
  +50 MB (+0,9 %). qpdf 12.4.0 resuelve 7 de 7 operaciones y tesseract-ocr-spa
  trae el castellano. Los 7 casos no_evaluable de referencia.json quedan a 0.

- La regla I9 atrapa a resvg 6 de 6 (0,00 % de tinta frente a 20,01 % de
  Inkscape), pero cuesta 32-59 ms a 400x200 y 2 454 ms a 1920x960: la
  estimacion de 26 ms se quedaba corta x94. Y resvg no era un caso aislado:
  la familia tiene cinco miembros y uno sigue sin cubrir (audio con un canal
  silenciado hacia un destino con perdida).

- La normalizacion del detector de RapidOCR queda validada SOLO sobre
  PP-OCRv6 small (0 regresiones en 15 documentos, incluidas 4 rasterizaciones
  del patron oro). Aplicada a la familia empeora 12 de 42 celdas, con +42,50
  puntos en PP-OCRv4 mobile sobre un documento LIMPIO. Los ocho inference.yml
  declaran ImageNet y rapidocr aplica 0,5 a los ocho: el desajuste es
  universal, el dano no. Entra como tabla por checkpoint.

- El verificador pasa de 3 859 a 4 185 lineas, con contrato de CINCO puntos y
  15 reglas de fidelidad, y sigue con 0 falsos positivos y 12/12 fallos
  atrapados. El interruptor --sin-v2 ahorra el 46,3 % de la suite sin cambiar
  ni un aviso.

Corpus: corpus/pdf/escaneado_d4{,a,b,c,e,f}.pdf por Git LFS, con
MANIFIESTO-d4.md. Salidas: texto, con los binarios regenerables excluidos y
cubiertos por sus MANIFIESTO.md. Los tres informes nuevos retiraron 380 MB de
semillas y dos PNG grandes antes de cerrar.
```

---

## 7. Cómo verificar este informe

**Todo lo de arriba es reconciliación de texto, no medición.** Se comprueba abriendo los dos lados:

| Para comprobar | Abrir |
|---|---|
| Que ninguna cifra es inventada | Cada fila de §1 lleva la sección exacta del informe de origen |
| Que los ppp no son la unidad | `bench/ppp-y-normalizacion.md` §2.4 y los `.json` de `bench/salidas-ppp-norm/json/` — 24 celdas, tres geometrías |
| Que los siete óptimos caen entre ×0,50 y ×1,80 | ídem §2.7 y `bench/salidas-ppp-norm/tablas.md` |
| Que RapidOCR recibe el mismo array por encima de 233 ppp | ídem §2.5 y `bench/salidas-ppp-norm/sonda_detector.py` |
| Que la corrección de normalización empeora 12 de 42 celdas | ídem §3.5 y `bench/salidas-ppp-norm/survey_norm.py` |
| Que el punto 5 cuesta lo que dice | `bench/salidas-quinto-punto/coste_p5.json` (n=15, 22 configuraciones) |
| Que I9 discrimina 6/6 y cuánto cuesta | `bench/salidas-quinto-punto/i9.json` |
| Que la familia tiene cinco miembros | `bench/salidas-quinto-punto/familia.json` (10 miembros y controles) |
| Que `P9` falla | `bench/salidas-quinto-punto/p9.json` + `texto/*.txt` — **el texto de las 32 capas está guardado, así que se puede reanalizar sin volver a pasar el OCR** |
| Que `_gs_texto` devolvía vacío | `bench/salidas-quinto-punto/txtvacio.json` y `txtvacio2.json` — 180 + 750 ejecuciones |
| Que el 18,8 % tiene método | `bench/salidas-invocacion/inventario_e1.json`, `resid_p2.json` y `final_p2.json` |
| Que el control antifalso positivo eliminó 4 de 32 | `bench/salidas-invocacion/validacion_p2.json` |
| Que `qpdf` y Tesseract caben en 8 líneas | `bench/salidas-invocacion/Dockerfile.c13` y `c13/res.tsv` |
| Qué cambió D1, qué D2 y qué D3 | `bench/consolidacion-21ago.md` §1 · `bench/consolidacion-2-21ago.md` §1 · §1 de este documento |
