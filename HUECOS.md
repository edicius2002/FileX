# FileX — Los huecos competitivos, reevaluados

**Fecha:** 19 de agosto de 2026 · **revisado el 21 de agosto de 2026 (00:32, 03:30, 10:00 y 14:00)**
**Estado:** revisión crítica tras la fase de ejecución

> Este documento sustituye la lista original de cuatro huecos. Aquella se formó con **metadatos de GitHub y lectura de código**; la fase de ejecución la desmintió parcialmente. Dos huecos se debilitaron, uno hubo que reformularlo, y **el diferenciador más fuerte no estaba en la lista**.
>
> **Segunda revisión (21/08/2026, 00:32), con tres mediciones nuevas.** El diferenciador nº 1 sale **confirmado y con su coste medido**, pero con la implementación cambiada y un cuarto punto de contrato (§1). El nº 2 pasa de «reformulado» a **refutado en su parte multi-salto** (§2). Y el nº 5 **se reabre**, porque las cifras que lo cerraban eran un artefacto del arnés (§5).
>
> **Tercera revisión (21/08/2026, 03:30), con cuatro informes más** — `bench/verificador-fidelidad.md`, `bench/mcp-cabos-sueltos.md`, `bench/saturacion-herramientas.md` y `bench/ocr-ppp-nativos.md`. **Se cierran cuatro pendientes de este documento** y **uno se resuelve en contra de la hipótesis**: el §1 pierde sus dos PENDIENTE de píxeles (`min(alfa)` cuesta 66,0 ms en el peor caso, y la fidelidad es ×1.100 el contrato, así que va fuera del camino caliente); el §3 cierra la saturación del catálogo con 540 ejecuciones y **27 herramientas eligieron mejor que 8**; y el §5 estrena **tabla canónica de OCR** y **matiza el aviso de `gpu-fase2.md` en dos sentidos medidos**. Detalle en `bench/consolidacion-21ago.md`.
>
> **Cuarta revisión (21/08/2026, 10:00), con tres informes más** — `bench/verificador-ghostscript.md`, `bench/aristas-nominales.md` y `bench/corpus-d4.md`. **Tres cosas cambian de estatus, y la primera toca el argumento central del documento:**
> - **El §1 gana su octavo fallo de verificación, y es el primero que el contrato de cuatro puntos NO atrapa** (`resvg` devuelve un PNG perfecto y sin una sola letra). Aparece además un **quinto punto de contrato**: hay motores que escriben **fuera** del destino.
> - **El §2 cierra su último PENDIENTE con una cifra:** el **50,5 %** de las aristas declaradas verificables no existe, IC 95 % [48,2–53,0] — **pero la tasa no es uniforme (factor 18)** y el estrato que el multi-salto usa de verdad, el que toca PDF, sale al **3,0 %**. Los dos hechos van juntos.
> - **El §5 cierra tres pendientes de golpe:** existe `escaneado_d4`, la asimetría de PaddleOCR **tenía causa y no era ninguna de las tres candidatas** (era un defecto de normalización de RapidOCR), y el OCR de Ghostscript en CPU está ejercitado. Detalle en `bench/consolidacion-2-21ago.md`.
>
> **Quinta revisión (21/08/2026, 14:00), con tres informes más** — `bench/ppp-y-normalizacion.md` (P1), `bench/invocacion-aristas.md` (P2) y `bench/contrato-quinto-punto.md` (P3). **Esta pasada CORRIGE a la anterior en tres sitios, y hay que leerlo así, no como una ampliación:**
> - **La regla de ppp del §5 estaba mal en sus DOS versiones.** Ni techo relativo ×1,4 ni techo absoluto 200: **no hay una regla global de ppp, hay una por motor**, y por tanto la elección **pertenece al adaptador del motor, no al orquestador**. Los ppp **no son la unidad**: el mismo mapa de bits en tres páginas distintas da 19,13 / 19,63 / 36,24 % **a los mismos ppp** y coincide **a la centésima** a los mismos píxeles.
> - **El §1 gana la regla que atrapa a `resvg` —I9, 6/6— y descubre que `resvg` no era un caso aislado sino una familia de al menos cinco miembros**, uno de los cuales **sigue sin cubrir**. Y **el quinto punto del contrato está implementado y medido**: +11,0 % del contrato, 0 falsos positivos, **pero solo con R18**.
> - **El §2 deja de ser «el 50,5 % no existe»: el 18,8 % de ese 50,5 % es INVOCACIÓN, no capacidad.** Con los mismos motores y el mismo build la tasa baja a **41,0 %**, y **3 226 aristas (el 10,2 %) son ganancia automática para FileX**.
>
> **Y dos autorrefutaciones más, de las que este repositorio presume:** `P9` —la señal contra la alucinación de OCR que se escribió en la revisión anterior— **está validada y tirada** (8,3 % de sensibilidad), con sustituto medido; y **«verificar en proceso siempre gana» es falso para píxeles**. Detalle en `bench/consolidacion-3-21ago.md`.
>
> Cada afirmación va marcada como **MEDIDO** (hay dato en `bench/`) o **PENDIENTE** (no se ha comprobado).

---

## Resumen del reordenamiento

| Nuevo # | Anterior # | Diferenciador | Veredicto |
|---:|---:|---|---|
| **1** | — | **Verificación obligatoria de la salida** | **Nuevo. El más fuerte de todos — ahora con su coste MEDIDO.** Y con su **frontera** medida: el contrato de cuatro puntos **no atrapaba el octavo fallo**; **la regla I9 sí lo atrapa (6/6), pero la familia tiene cinco miembros y uno sigue descubierto** (§1) |
| **2** | 1 | Grafo con coste por arista | **El multi-salto, REFUTADO con datos.** Sobrevive la selección con coste explícito — **reforzada:** el **50,5 %** de las aristas declaradas no existe, pero el estrato PDF que el multi-salto usa sale al **3,0 %**. **Y acotada por arriba: el 18,8 % de ese 50,5 % es invocación, no capacidad → la tasa real es 41,0 %, y 3 226 aristas son ganancia automática** |
| **3** | 3 | MCP multi-modal en un solo servidor | Real, mucho más estrecho de lo dicho |
| **4** | 2 | NVENC en vídeo | Real, pero solo importa en lote |
| **5** | 4 | OCR en GPU | Degradado: ya no es foso, es higiene. **Reabierto: las marcas de d2/d3 eran un artefacto del arnés** |

**Los tres criterios** con que se juzga cada uno: ¿nadie lo hace? ¿es barato? ¿lo nota el usuario? **Solo el nº 1 cumple los tres.**

---

## 1 · Verificación obligatoria de la salida — **el hueco real**

No estaba en la lista original porque **solo aparece al ejecutar**. Leyendo código no se ve.

### Evidencia — toda MEDIDA

| Fallo observado | En quién | Cómo se verificó |
|---|---|---|
| `.avif` que en realidad es un **PNG**, entregado con estado "Done" | ConvertX | Bytes mágicos `89 50 4E 47`; 42 855 B frente a los 3 137 B del AVIF real |
| **Pierde una pista de audio**, en silencio | **ConvertX y SnapOtter** | `ffprobe`: 2 pistas de origen → 1 de salida, éxito reportado |
| Degrada 16 → 8 bits **sin avisar ni ofrecer parámetro** | SnapOtter | Comparación contra la referencia nativa, que sí conserva los 16 bits |
| PDF→imagen a **72 ppp fijos**; audio a **64 kbps** pidiendo 192 | ConvertX | Inspección de las salidas |
| `dasel` roto: conversiones **declaradas e inalcanzables** | ConvertX | Sintaxis v1 contra binario v2 |
| Cadena vacía con **`isError: false`** ante un PDF escaneado | markitdown-mcp | El agente concluye que el documento está vacío |
| Afirma usar la GPU **mientras corre en CPU** | onnxruntime-gpu 1.29.0 | `get_device()` devuelve `'GPU'`; las sesiones son CPU |
| **PNG válido, geometría exacta y SIN UNA SOLA LETRA** al rasterizar un SVG con texto | **resvg 0.46.0** (imagen de ConvertX) | Tinta en la banda de texto: **0,00 %** frente al 14,02 % de Inkscape y el 15,07 % de `magick`. `rc=0` (`bench/aristas-nominales.md` §8.2) |

**Es sistémico, no anecdótico.** **Ocho** fallos independientes, en **siete** proyectos distintos, todos del mismo tipo: **el software declara éxito sobre un resultado incorrecto**.

> ### Y el primero de la lista deja de ser anécdota de un competidor: **reproducido 22 veces con `magick`** — MEDIDO el 22/08 (`bench/firmas-contrato.md` §7.1)
>
> `magick corpus/imagen/tipico.png -auto-orient salida.group4` devuelve **rc=0** y entrega **un PNG de 313 bytes con firma PNG**. Igual con otros 21 destinos que ImageMagick y GraphicsMagick declaran saber escribir (`b c g k m o r y p7 preview clipboard data flif group4 histogram inline msl mvg null pocketmod sparse vid`). **Es el fallo nº 1 de esta tabla, producido por un motor de primera línea, 22 veces en la misma sesión.**
>
> | | Contrato de 5 puntos, vocabulario **viejo** | Vocabulario **nuevo, solo por firma** | Con la regla **G6** |
> |---|---:|---:|---:|
> | Detectados de 22 | **0** (los 22 salen `ok_parcial`) | **0** (los 22 salen `ok_parcial`) | **22** (los 22 salen `aviso`) |
>
> **La columna del medio es la importante, porque refuta la hipótesis obvia: ampliar el vocabulario de firmas NO atrapa este caso.** Para atrapar `.group4` por firma habría que saber qué firma esperar de `.group4`, y `.group4` son datos CCITT crudos: **no tiene ninguna**. Los otros 21 ni siquiera son formatos de fichero: son pseudoformatos de ImageMagick.
>
> **Lo que sí lo atrapa no necesita saber nada del destino — G6: la salida tiene la MISMA firma que la entrada y no era eso lo que se pedía.** Se dispara cuando (a) la extensión de destino no está en la tabla, (b) la firma de la salida es un formato reconocido y (c) coincide con la de la entrada, con otra extensión. **Cuesta 0: las dos firmas ya están calculadas.** Severidad `aviso`, no `fallo`: prueba que es sospechoso, no que sea incorrecto. Sobre las 53 del patrón oro **no se dispara ni una vez**; sobre 345 salidas legítimas se dispara **exactamente en los 12 casos en los que ImageMagick entrega un PNG**.
>
> **Y la consecuencia de catálogo, que es donde de verdad se arregla: esas 22 aristas son nominales y hay que BORRARLAS de la cobertura declarada, no verificarlas mejor.**

> ### El octavo es cualitativamente distinto: **es el primero que el contrato de cuatro puntos NO atrapa** — MEDIDO (`bench/aristas-nominales.md` §8.2)
>
> Los siete anteriores caen con el contrato. Este no. **`resvg 0.46.0` rasteriza `e1.svg` —dos bloques de texto, uno *sans* y uno *serif*, más figuras— y entrega:**
>
> | | resvg 0.46.0 | Inkscape | `magick` (Windows) |
> |---|---:|---:|---:|
> | Código de salida | **0** | 0 | 0 |
> | Firma real | PNG | PNG | PNG |
> | Geometría | **400×200, la pedida** | 400×200 | 400×200 |
> | **Tinta en la banda de texto** (`y = 155…205`) | **0,00 %** | **14,02 %** | **15,07 %** |
> | Tinta total | 8,78 % | 13,38 % | 13,39 % |
>
> **Firma correcta · flujos correctos · propiedades declaradas coherentes · pedido = obtenido. Los cuatro puntos lo aprueban.** Lo único que delata el fallo está en `stderr` —`No match for '"DejaVu Sans", sans-serif' font-family`— y **el contenedor tiene 153 fuentes instaladas** (`fc-list | wc -l`): no es un problema de fuentes, es que ese build no resuelve familias.
>
> **Por qué esto no es una nota al pie.** El contrato de cuatro puntos es el argumento nº 1 de este documento y el diferenciador nº 1 del proyecto. Aquí queda **acotado con precisión**: el contrato responde *«¿me entregaste lo que pedí?»* leyendo **la declaración** de la salida, y hay una clase de fallo —**el contenido que desaparece sin dejar rastro en ninguna propiedad declarada**— que solo se ve **comparando la salida con la entrada**, es decir, en el **grupo C de fidelidad**, no en el contrato.
>
> **La regla que lo atraparía, con su coste estimado:** *si el origen SVG contiene elementos `<text>`, la salida rasterizada debe tener tinta donde estaban*. Es una comparación de tinta por banda, **del orden de los 26 ms** que `bench/verificador-fidelidad.md` mide para el grupo C. ~~**PENDIENTE de implementar.**~~ **IMPLEMENTADA Y MEDIDA el 21/08 a las 14:00 — y la estimación de 26 ms se quedaba corta ×94. Ver el bloque «La regla I9» más abajo.**
>
> **Y la lección general, que es la valiosa:** *el contrato acota el fallo declarativo; el fallo semántico necesita fidelidad.* **Refutar una conclusión propia es el resultado más valioso que se puede traer**, y este refuta —parcialmente y con su frontera medida— la frase «los cuatro puntos atrapan los fallos del sector». Atrapan los siete que el sector comete **por declarar de más**; no atrapan el que comete **por entregar de menos en silencio**.

> ### La regla I9 existe, discrimina 6/6, y `resvg` resulta ser la punta de una FAMILIA — MEDIDO (`bench/contrato-quinto-punto.md` §4, §5)
>
> **I9:** *si el SVG de origen contiene elementos `<text>` con contenido, la salida rasterizada debe tener tinta donde estaban.* Dos mitades, las dos en proceso y sin dependencias: `xml.etree` saca cada `<text>` con su `x`, `y`, `font-size` y `text-anchor` y le estima una caja **deliberadamente estrecha** —de `y − 0,75 em` a `y + 0,20 em`, y de `x` a `x + 0,50 em × n`, con `n ≤ 24`—; un lector de PNG en proceso cuenta qué fracción de píxeles de cada caja se aleja del **fondo real de la caja** (la luminancia más frecuente) en más de 64 de 255. *(La caja es estrecha a propósito: una generosa daría **falsos negativos**, con tinta ajena tapando la ausencia de letras.)* Umbrales: **`fallo` por debajo del 0,5 % de tinta**, `aviso` por debajo del 2 %.
>
> | Caso | `<text>` | Tinta en la peor caja | Veredicto |
> |---|---:|---:|---|
> | **Inkscape 1.x** | 2 | **20,01 %** | `ok` |
> | **`resvg` 0.46.0** | 2 | **0,00 %** | **`fallo`: TEXTO PERDIDO** |
> | **`magick` 7.1.2** | 2 | **23,61 %** | `ok` |
> | control: SVG **sin** `<text>` | 0 | — | `ok_parcial`, «la regla no aplica» |
> | control: texto de **2 caracteres** | 1 | 21,49 % | `ok` |
> | control: `text-anchor="middle"` | 1 | 18,26 % | `ok` |
>
> **El margen no es estrecho: es binario, 0,00 % frente a 18–24 %.** Sobre las 53 salidas del patrón oro **I9 no se evalúa ni una vez** (ninguna tiene SVG de entrada) y **no añade ni un aviso**.
>
> **Su coste, que es donde la estimación falló: 32–59 ms a 400×200 y 2 454 ms a 1920×960.** «Del orden de 26 ms» valía para el caso de juguete y se queda corta **×94** en un raster de 1,8 Mpx. **El 99,6 % del coste es leer píxeles; analizar el SVG cuesta 0,14–0,21 ms** — cuarta medida seguida de la misma constante (53 % → 61 % → 70 % → **99,6 %**: *la lógica de la regla nunca es el coste*).
>
> **No cubre:** PNG entrelazado (devuelve `evaluable: false` con su motivo) ni destinos que no sean PNG. **Un `svg → pdf` con el mismo fallo de fuentes no se detecta hoy. PENDIENTE.**
>
> #### Y `resvg` no era un caso aislado: **la familia tiene al menos cinco miembros en cinco modalidades**
>
> | # | Miembro | Contrato (5 puntos) | Fidelidad | ¿Quién lo atrapa? |
> |---|---|---|---|---|
> | 1 | **SVG con `<text>` → PNG sin fuentes** (`resvg`, real) | `ok_parcial` | **`fallo`** | **I9** |
> | 2 | **Vídeo con duración, geometría y códec correctos y TODO NEGRO** | `ok_parcial` | `aviso` | **V8**, y solo como aviso: **5,39 dB** de PSNR |
> | 3 | **PDF con texto → PDF rasterizado** (del propio patrón oro) | `ok_parcial` | **`fallo`** | **P2** (105 → 0 caracteres) |
> | 4 | **CSV → JSON que pierde una columna** | **`fallo`** | `ok_parcial` | **el CONTRATO** (D4) |
> | 5 | **Audio estéreo con un canal SILENCIADO, destino con pérdida** | `ok_parcial` | `ok` | **NADIE** |
> | 5b | el **mismo** fallo hacia FLAC (sin pérdida) | `ok_parcial` | **`fallo`** | **A4** (el PCM no coincide) |
>
> **El acotamiento que escribió la consolidación anterior —«el contrato juzga la declaración; el contenido que desaparece necesita fidelidad»— resulta CORRECTO, y ahora tiene formulación precisa:** *el contrato atrapa al miembro cuyo contenido perdido está **declarado en metadatos** —filas, cabecera de un CSV, pistas, páginas— porque la sonda ya los lee para los puntos 2, 3 y 4; necesita fidelidad cuando el contenido **solo existe como píxeles o como muestras**.* **La pregunta se planteó como posible excusa y la medición la confirmó como arquitectura**, con dos pruebas: el precio es de **tres órdenes de magnitud** (0,43 ms el contrato frente a 32–2 454 ms de I9), y **el miembro cuyo contenido sí está declarado —el CSV— lo atrapa el contrato y no la fidelidad**. La frontera cae exactamente donde el criterio dice.
>
> **El miembro que sigue sin cubrir, tras añadir I9: PENDIENTE.** Un canal de audio silenciado hacia un destino **con pérdida**. El contrato ve 2 canales, la frecuencia y la duración correctas; A4/A5 no aplican porque no hay PCM que comparar. **La cobertura depende del destino, no del fallo.** Propuesta sin medir: comparar la **energía por canal** con `ffmpeg -af astats` (sonda externa, grupo C).
>
> **Y hay un sexto candidato, encontrado por otro agente y por otro camino** (`bench/invocacion-aristas.md` §4.1): este ImageMagick es **Q16-HDRI y escribe los crudos a 16 bits por canal**; releer un `.rgb` con `-depth 8` **no falla**, consume la mitad del fichero, entrega **la geometría exacta pedida** y **píxeles basura**. **Pasa los cuatro puntos.** **Dos vías independientes llegando al mismo patrón** es lo que convierte esto de anécdota en clase de fallo.
>
> **Una nota de severidad que va con la tabla:** el vídeo enteramente negro sale como **aviso** y no como fallo, porque V8 está calibrada para «recodificación con pérdida». **5,39 dB no es una recodificación agresiva: es otra imagen.** **PENDIENTE:** un suelo duro de PSNR para V8, como el de 20 dB que I7 ya tiene.
>
> **Y una hipótesis descartada, que también es resultado:** se esperaba que `gs pdfwrite` perdiera las anotaciones `/Annots` de un PDF. **No las pierde.**

### El contrato tiene cuatro puntos, no tres — corrección MEDIDA

`PLAN-ORQUESTADOR.md` §4.2 comprobaba firma real, flujos, y **propiedades declaradas frente a medidas**. **Falta un cuarto punto: propiedades PEDIDAS frente a obtenidas.**

Lo que lo obligó: `image-worker-mcp` entregó un **WebP válido**, con propiedades coherentes consigo mismas, que era la imagen **redimensionada sin que nadie lo pidiera** — 1920×1080 → 800×450 con barras negras de 75 px, y un PNG de 64×64 **ampliado ×9,75**. **Ese caso pasa los tres puntos originales.** «No te pedí que redimensionaras» es una condición distinta de «el fichero es coherente consigo mismo».

> **Y la regla que va con él: ninguna transformación no solicitada se aplica por defecto.** La causa en el código es literalmente un valor por omisión (`sharp.ts:157-170`: sin `width` ni `height` no se omite el redimensionado, se aplican `DEFAULT_WIDTH=800`, `DEFAULT_HEIGHT=600` y `fit='contain'`).

**MEDIDO en `bench/coste-verificacion.md`:** el punto 4 es **187 de las 333 líneas** de lógica del contrato —el bloque más grande, más que los puntos 2 y 3 juntos— y es **lo único** que atrapa ese fallo. No es una mejora incremental: es la mitad del contrato.

### Y un quinto: **hay motores que escriben fuera del destino** — MEDIDO (`bench/aristas-nominales.md` §5.2)

Reproducido de forma controlada, con la invocación exacta de ConvertX:

| Orden | Escribe en el destino | Escribe **también** |
|---|---|---|
| `ffmpeg -i trivial.mp4 DEST/t.mpd` | `t.mpd` (**1 234 B**) | **`init-stream0.m4s` (814 B) y `chunk-stream0-00001.m4s` (528 447 B) en el DIRECTORIO DE TRABAJO** |
| `magick trivial.png -auto-orient DEST/u.html` | `u.html` (506 B) **y `u.png` (329 B)** | **`u_map.shtml` (98 B) en el DIRECTORIO DE TRABAJO** |
| `magick trivial.png -auto-orient DEST/u.map` | `u.map` (4 102 B) | — |

Tres consecuencias, en orden de gravedad:

1. **La arista `vídeo → mpd` entrega un `.mpd` de 1,2 KB inútil**: los 528 KB de vídeo se quedaron en otro directorio. **Pasa los cuatro puntos del contrato** —firma correcta, manifiesto DASH válido— y no lleva el contenido. Categoría correcta: **DESTRUIDO**. *(El propio arnés de `aristas-nominales.md` la contó como ÍNTEGRO, porque solo miraba la ruta de destino: es una autocrítica de aquella medición y otra razón por la que su 50,5 % es cota inferior.)*
2. **Una salida puede ser varios ficheros.** `magick … out.html` produce **dos** en el destino. Devolver solo el declarado entrega un documento roto, y la sonda que juzga **un** fichero no puede verlo.
3. **Es un escape de confinamiento, no una rareza estética.** Un motor que escribe en el `cwd` escribe donde esté el orquestador, no donde esté el trabajo.

> **Quinto punto del contrato: «¿el motor escribió algo fuera de lo declarado?»** Se implementa listando el directorio de trabajo antes y después — **trivial**, y hoy no lo tiene nadie. Va con la contrapartida de diseño de `PLAN-ORQUESTADOR.md` §4.6: **el confinamiento tiene que ser un directorio de trabajo propio y desechable por conversión, no solo una ruta de salida validada.**

#### El quinto punto, IMPLEMENTADO Y MEDIDO — `bench/contrato-quinto-punto.md` §2, §3 (21/08/2026, 14:00)

**Cuesta 0,047 ms — el +11,0 % del contrato — y SÍ entra en el camino caliente, pero solo con R18. MEDIDO** (mediana n=15):

| Configuración | Mediana | Frente al contrato de 4 puntos |
|---|---:|---:|
| **Contrato SIN punto 5** (referencia) | **0,4254 ms** | ×1 |
| **+ punto 5 completo CON R18** (directorio desechable: solo se censa después) | **0,4722 ms** | **×1,11** |
| + punto 5 **sin R18**, directorio de 2 ficheros | 0,5138 ms | ×1,21 |
| + punto 5 **sin R18**, directorio de **1 000 ficheros** | **3,6614 ms** | **×8,6** |

> **El contrato pasa del 0,032 % al 0,036 % de convertir. Y ese número depende de R18: sin directorio de trabajo desechable, sobre un directorio real de 1 000 ficheros, el punto 5 cuesta 3,24 ms —×7,6 el contrato de cuatro puntos— y lo saca del camino caliente.**
>
> **R18 deja de ser higiene y pasa a ser requisito de coste.** Es lo que reordena su prioridad en `PLAN-ORQUESTADOR.md` §4.6.

**La lógica del punto 5 es gratis (0,031–0,037 ms); lo caro es el censo.** Cuarta vez que se mide lo mismo: *fabricar el acceso al dato es el coste.*

**Qué comprueba, y las dos decisiones que salieron de los datos y no de la especificación:**

| Regla | Qué mira | Severidad |
|---|---|---|
| **N5** | ficheros nuevos **fuera** del destino cuyos bytes **superan** a los del entregado → *el contenido se fue a otro sitio* | **fallo** |
| **N6** | ficheros nuevos fuera del destino con **menos** bytes → suciedad, no pérdida | aviso |
| **N7** | ficheros nuevos **en** el destino además del declarado. **Informativo** si el destino es multifichero por naturaleza (`mpd`, `m3u8`, `html`…), si el pedido lleva `multifichero: true`, o si el nombre es un patrón `printf`; aviso si no | informativo / aviso |
| **N8** | ficheros que ya existían y el motor **modificó** | aviso |
| **N9** | qué fracción de los bytes escritos lleva el fichero entregado | informativo |

1. **El disparador es la UBICACIÓN, no el tamaño.** N9 parecía el detector obvio del caso DASH (1 234 B de `.mpd` frente a 528 KB = 0,2 %), pero **un manifiesto HLS legítimo también lleva el 0,0 % de los bytes** (114 B frente a 248 KB). Si N9 fuera el disparador, **toda salida en streaming sería un fallo.** El reparto de bytes solo decide la **severidad** de una fuga ya detectada por ubicación.
2. **Declarar `multifichero: true` NO autoriza a escribir en el `cwd`.** La orden DASH con ese campo en el pedido **sigue dando N5 fallo**, porque sus segmentos no están junto al manifiesto. Es la diferencia entre «esta salida son varios ficheros» y «este motor escribe donde le da la gana».

**Discriminación, MEDIDA sobre casos fabricados a propósito** (el patrón oro no tiene ni una salida multifichero): **0 avisos y 0 fallos** en los tres legítimos —HLS, `ffmpeg … f%03d.png` con 20 ficheros, `gs -sOutputFile=p%d.png`— y **fallo mantenido en el DASH**.

**Falsos positivos que añade sobre el patrón oro: CERO.** Reejecutando **las 39 órdenes** (36 de motor; 3 son de Python) en directorio desechable con censo: **0 hallazgos de severidad `fallo` o `aviso`**, y **ninguna de las 36 produce más de un fichero**.

> ### Y su coste honesto es un cambio de naturaleza, no de precio: **sin censo, 49 de las 53 salidas bajan de `ok` a `ok_parcial`**
>
> No es un falso positivo: es el verificador diciendo *«no puedo saber si el motor escribió en otro sitio, porque nadie miró cuando tocaba»*. **El punto 5 es el primero del contrato que NO es verificable a posteriori**, y eso es en sí un argumento de arquitectura: **la verificación tiene que vivir dentro de la conversión, no ser un paso que se pueda hacer luego.**
>
> **Los 5 fallos documentados siguen atrapados: 12 de 12** con los dos motores, y el único `fallo` sobre el patrón oro sigue siendo `2pistas_mkv-to-DEFAULT.mp4`, **cuyo veredicto esperado es `fallo`**.

**Comprobación cruzada desde otro carril — MEDIDO (`bench/invocacion-aristas.md` §7.4): 0 de 118 aristas escribieron fuera del destino declarado.** **No contradice el hallazgo original: confirma que era específico.** Los dos casos de fuga tienen destinos —`mpd`, `html`— que **no aparecen entre las 118 aristas nominales de la muestra**, porque esas dos aristas no fallaban: entregaban un fichero incompleto. **Fuga y fallo son poblaciones disjuntas**, y eso es justo por lo que el quinto punto hace falta: ni los cuatro puntos ni el juez de aristas nominales las ven.

### Por qué es el más fuerte

- **Nadie lo hace.** Ninguno de los seis orquestadores verifica su salida.
- **Es barato** — confirmado, pero **la justificación que se daba aquí era la implementación cara**. Ver abajo.
- **Lo nota el usuario.** Hoy recibe ficheros corruptos que su herramienta le dice que están bien. Los otros cuatro huecos son mejoras de rendimiento o de alcance; este es corrección.

### Corolario contraintuitivo — MEDIDO

**Un recurso alternativo sin verificación es peor que no tenerlo.** ImageMagick dentro de ConvertX emite un *warning* con código de salida 0 y devuelve el formato origen: convierte un fallo honesto en uno silencioso. Con `vips`, el mismo caso **falla limpiamente**.

### Los dos pendientes, CERRADOS — `bench/coste-verificacion.md`

Este documento decía: *«Es barato. Firma real del fichero, `ffprobe` de flujos, y comparación de propiedades declaradas contra medidas.»* **La afirmación se confirma; la justificación que la acompañaba se refuta.**

**1 · Coste en tiempo — MEDIDO.** Depende por completo de *cómo* se implemente:

| Implementación | Coste por fichero | Ratio verificar ÷ convertir |
|---|---:|---|
| **Leyendo cabeceras en proceso** | **0,372 ms** | **0,14 %-0,36 %** por categoría; **0,032 %** sobre las 39 órdenes del patrón oro |
| Con `ffprobe` / `magick identify` | 54,06 ms | 8,9 %-153 %; **9,6 %** sobre las 39 |

**145× más caro.** Y peor: **en 15 de las 39 órdenes (38 %) verificar con subprocesos cuesta más que convertir**, hasta el **397 %** en `flac→wav`. El patrón es nítido: cuanto más barata la conversión —un remux, un cambio de contenedor— peor la ratio, y esas son las conversiones más frecuentes. El paralelismo no lo salva (techo ×1,79 con 24 hilos), porque **el cuello es la creación de proceso, no el disco ni la CPU**: sondear las 53 salidas del patrón oro (204,9 MB) lee **334,6 KB, el 0,163 %**, y un PNG de 61 MB cuesta **133 bytes**.

> El temor de este documento —*«un `ffprobe` por salida no es gratis en lote»*— era **correcto y ahora está cuantificado**: 53 salidas cuestan **26,1 ms en proceso** frente a **6.740 ms** con subprocesos. Lo que hay que cambiar no es la ambición, es la frase «(`ffprobe`)» de `PLAN-ORQUESTADOR.md` §4.2.

**2 · Coste de implementación — MEDIDO, y es el dato que nadie había pagado.** El prototipo son **1.503 líneas sin dependencias**, de las que **333 son el contrato** (el 26 %) y **671 son leer cabeceras** (el 53 %). Atrapa **los 5 fallos documentados** y da **0 falsos positivos sobre 53 salidas correctas**.

**Pero el 0 % no fue gratis: la primera versión, escrita literalmente desde la especificación, dio 9-10 falsos positivos (17-19 %).** Hicieron falta **~85 líneas de excepciones justificadas por datos** —tolerancia por trama de códec, techo de profundidad por formato de destino, ppp en píxeles/cm de `magick identify`, bitrate como petición y no como contrato— **y ninguna es deducible del contrato escrito**. Salieron todas de ejecutar contra el patrón oro. Es la parte que no se ve leyendo la especificación, y es parte inseparable del contrato.

**Conclusión: una semana de trabajo, no un trimestre.** El diferenciador nº 1 está sano y es defendible con números.

### Los dos pendientes de píxeles, CERRADOS — `bench/verificador-fidelidad.md` (21/08/2026, 02:44)

Este documento decía: *«el mínimo del canal alfa … el cálculo en proceso está sin escribir»* y *«las reglas que exigen comparar píxeles … cuestan lo que la conversión»*. **Los dos están medidos, y el resultado separa lo barato de lo caro con una frontera nítida.**

**1 · `min(alfa)` en proceso — MEDIDO** (`verificador-fidelidad.md` §0.1, §0.2, §1.3):

| Caso | En proceso | `magick` | Factor |
|---|---:|---:|---:|
| **Peor caso** — PNG 1920×1080 RGBA16 **enteramente opaco** (`tipico.png`), que obliga a recorrerlo entero | **66,0 ms** | 376,3 ms (remedida hoy) | ×5,8 |
| Mejor caso — `alpha.png`, transparencia real en la primera fila | **0,23 ms** | 47,5 ms | ×226 |
| PNG 4000×3000 RGB16 **sin alfa** (59,0 MB) — la decide la cabecera | **0,09 ms** | 1.194,1 ms | **×13.569** |

- **En 7 de los 12 casos medidos no se lee un solo píxel** (0,05–0,17 ms): la cabecera basta. **MEDIDO.**
- **Los 734,6 ms que citaba este documento no son reproducibles hoy tal cual**: la misma orden de `magick` da **376 ms** en la sesión de la medición nueva, y la familia de órdenes equivalentes va de 369 ms a 1.309 ms (`verificador-fidelidad.md` §1.3, nota). El informe calcula sus factores contra la remedida, que es la conservadora. **La cifra vieja se conserva aquí como lo que se creyó; la vigente es 376,3 ms.**
- **Dónde vive: una vez por *entrada*, cacheado por hash, nunca por salida.** Calcularlo para las 53 salidas cuesta 320,9 ms; calcularlo por entrada, **66,3 ms** — **÷4,8** (§1.4).
- **Qué queda fuera:** AVIF/HEIF, TIFF comprimido, GIF, PNG entrelazado (Adam7), PNG con `tRNS` de color clave y WebP animado devuelven **«no evaluable» con su motivo**, no un `1.0` cómodo (§1.2). Cubrir WebP costó **un decodificador VP8L completo: 437 líneas**, el 28 % de lo añadido.

**2 · Las reglas de fidelidad — MEDIDO, y la sospecha de este documento era correcta.** Se implementaron **11** (I3, I6, I7, I8, V6, V8, V9, A4, A5, P2, P6). Sobre las 53 salidas del patrón oro: **28.858 ms de fidelidad frente a 26,1 ms de contrato — ×1.106**, y **el 38,5 % del coste de convertir** frente al 0,032 % del contrato (§2.2, §3.1).

> **La consecuencia de diseño es la separación en tres grupos, no en dos** (`verificador-fidelidad.md` §3):
>
> | Grupo | Cuándo corre | Coste | Frente a convertir |
> |---|---|---:|---:|
> | **A — Contrato** | siempre, en serie, en el hilo de la conversión | **0,37 ms** | **0,032 %** |
> | **B — Caracterización de la entrada** (`min(alfa)`) | una vez por entrada, cacheado por hash | 0,05–66,0 ms | 0,089 % |
> | **C — Fidelidad** | bajo demanda o en la suite de regresión; **nunca en un lote** | 207 ms/salida | **38,5 %** |
>
> **La fidelidad va fuera del camino caliente.** Meterla en la misma función que el contrato es lo que convertiría el diferenciador nº 1 en el mayor problema de rendimiento de FileX.

**3 · Dos puntos ciegos cerrados, y uno gratis — MEDIDO** (§5.4):

- `alpha_png-to.jpg` **aplanado sobre negro**: el lector de alfa devuelve la coordenada del primer píxel 100 % transparente y **una sola** invocación de `magick` lee ese píxel en la salida — **25,9 ms**. Discrimina la conversión mala de la buena del propio patrón oro.
- `trivial_mp4-to-naive.gif` con **paleta genérica**: se detecta **en proceso, en 0,18 ms**, porque una paleta genérica es una rejilla regular (8×8×4) y una calculada sobre el clip no lo es. *(Limitación honesta: solo detecta rejillas regulares.)*

**4 · El umbral de `txtwrite` (≥10 caracteres), confirmado con su caso — MEDIDO** (§4). Sobre 9 PDF: `alpha_png-to.pdf` devuelve `'FX'` —2 caracteres— sin una letra de texto real. Con umbral `>0` se declararía «conserva texto» **1 de 9 (11 %)**; con `≥10`, cero errores. Coste 172,2–297,4 ms (mediana 179,3), **485× el contrato completo**: por eso P6 vive en el grupo C y el contrato usa `b"/Font" in datos` como indicio barato.

**5 · El prototipo, revalidado — MEDIDO** (§5.1, §5.2, §6). **3.035 líneas** (1.542 añadidas sobre las 1.503 originales), biblioteca estándar y nada más. **5/5 fallos documentados atrapados** con los dos motores, y **0 falsos positivos sobre las 53 salidas en seis configuraciones** (2 motores × 3 modos de `min(alfa)`). Sin `min(alfa)`, **11 de las 53 pasan a `ok_parcial`** en vez de aprobar: el verificador dice cuándo no sabe.

> **Actualización del 21/08 a las 09:40 — MEDIDO (`bench/verificador-ghostscript.md` §2, §3, §6).** El prototipo pasa a **3.859 líneas** (+824 netas), sigue sin una sola dependencia, y **sigue con 0 falsos positivos en las seis configuraciones y 12 de 12 fallos atrapados** (los 5 documentados × 2 motores + 2 controles). Tres cosas que hay que llevarse:
>
> - **`min(alfa)` cubre ahora TIFF comprimido (LZW/Deflate/PackBits, predictor, planar, 8 y 16 bits), GIF y PNG entrelazado Adam7**, y coincide con `magick` en **36 de 36** ficheros comparables. **AVIF/HEIF sigue diciendo «no evaluable» a propósito.**
> - **El atajo de «fila opaca» no es una optimización: es la condición para que la cobertura merezca la pena.** Sin él, el TIFF 1920×1080 RGBA16 opaco costaba **479 ms** frente a los 329 de `magick`, y el PNG Adam7 equivalente **1 208 ms** frente a 452. Con él: **80,7 ms** y **66,3 ms** — ×4,1 y ×6,8 **a favor**. *«En proceso siempre gana» habría dejado de ser cierto en tres casos.*
> - **Se destapó un fallo preexistente y no era cosmético:** en PNG de paleta de 1/2/4 bits, la coordenada del primer píxel transparente devolvía el índice del **byte**, no el del **píxel** — con 2 bits por píxel, `(12,8)` se publicaba como `(3,8)`. Esa coordenada es la que **la regla I3** pasa a `magick` para comprobar sobre qué color se aplanó la salida: **I3 leía otro píxel y su veredicto era una casualidad.** No lo vio nadie porque `alpha.png`, la única entrada con alfa del corpus, es de 8 bits. **Corregido.**
>
> **Y el coste de las reglas nuevas cambia el presupuesto del grupo C:** **V2 (`-count_frames`) sube la suite de fidelidad un +60,6 %** —de 28 858 a **46 332 ms** sobre las 53 salidas, de los que **16 592 ms son solo V2**—, porque `-count_frames` **decodifica el vídeo entero** (3 482 ms sobre un MP4 de 16 MB, ×10 240 el contrato). El grupo C pasa de costar el 38,5 % de convertir al **61,9 %**. **V2 necesita su propio interruptor dentro del grupo C**: en una suite nocturna sí; en un «verifica esta conversión» sobre un vídeo de dos horas, no. Y la alternativa barata —creer `nb_frames`— es justo la que la regla prohíbe. **V5** (etiquetas de idioma y título) cuesta 1 289 ms y **el corpus no tiene con qué ejercitarla**: dice «la entrada no trae etiquetas» en **12 de las 22 veces** que se evalúa.

> **La constante que se repite: entre el 5 y el 7 % del código son excepciones justificadas por datos.** 85 líneas (6,7 %) en el contrato original, **74 líneas (4,8 %)** en la fidelidad. Ninguna se deduce de `referencia.json`: todas salieron de ejecutar contra el patrón oro.

> **Actualización del 21/08 a las 14:00 — MEDIDO (`bench/contrato-quinto-punto.md` §1, §3.3, §7).** El prototipo pasa a **4 185 líneas**, sin una sola dependencia externa. **Siguen 0 falsos positivos en las cuatro configuraciones y 12/12 fallos atrapados.** Bloques nuevos: punto 5 (**176 líneas**), I9 (**346**, de las que 265 son fabricar el acceso al dato), P9 (**49**), `_gs_texto` por fichero temporal (**36**) y el interruptor de V2 más la CLI (~60).
>
> *(Nota de trazabilidad que hay que conservar, y ya va por partida doble: **(a)** `verificador-ghostscript.md` §6 publicó **3 859 líneas** como estado final; los bloques nuevos suman ~640 y el total que midió P3 es 4 185, lo que implica un punto de partida de **~3 530**. **La cifra de 3 859 no se ha podido reproducir** y su propio informe lo deja anotado. **(b)** Al consolidar a las 14:10, `bench/scripts/verificador.py` tiene **4 567 líneas**, no 4 185: **hay otro agente editándolo en paralelo** —hay un `bench/salidas-firmas/` escribiéndose y sin informe, y ampliar el vocabulario de firmas (C14) se toca ahí—. **Las 4 185 son la medida de P3 sobre el fichero que él dejó, y así se citan; el recuento vivo del fichero no es comparable hasta que ese agente cierre.** Ninguna de las dos discrepancias afecta a una conclusión: **las dos rompen la trazabilidad del recuento entre informes, y por eso se escriben.**)*
>
> **Cambios de firma, para quien invoque el verificador:** `verificar(...)` acepta **`censo=`** y ejecuta 5 puntos (sin `censo`, `cobertura["5_escritura"] = False`); `cobertura` pasa de 5 a **6 claves**; `pedido["params"]["ocr"]` **existe y cambia el veredicto** (P5 invierte la exigencia, P9 sube de `aviso` a `fallo`); `verificar_fidelidad(...)` pasa de 13 a **15 reglas**; y la CLI gana `--censo`, `--censar` y `--sin-v2`.
>
> **El interruptor de V2 (C12), implementado y medido: ahorra el 46,3 % de la suite** (70 693 → **37 947 ms** sobre las 53 salidas) **sin cambiar ni un aviso** —los 8 siguen siendo exactamente los mismos ocho de los dos informes anteriores, e I9 y P9 tampoco añaden ninguno— **y sube los `ok_parcial` de 8 a 13**, que es lo correcto: **apagar una regla reduce cobertura, no aprueba**. Recomendación con su número: **V2 encendida en la suite de regresión** (33 s de más sobre 53 ficheros son irrelevantes en CI) y **apagada por defecto** en un «verifica esta conversión» sobre un vídeo largo, donde `-count_frames` decodifica el archivo entero.
>
> *(**Salvedad obligatoria al leer estos milisegundos:** V1 midió la misma suite sobre los mismos ficheros en **46 332 ms** y esta tanda da **70 693 ms**, con dos agentes más trabajando. **Las cifras absolutas de las dos sesiones no son comparables; las relativas dentro de cada una, sí.** V1 midió V2 como el 36 % de la suite y aquí sale el 46,3 %: **la conclusión se refuerza en la misma dirección** —cuanto más cargada está la máquina, más castiga la regla que decodifica el vídeo entero—, pero el número absoluto no se puede citar solo.)*

> ### Un fallo del propio verificador, reproducido y corregido — MEDIDO (`bench/contrato-quinto-punto.md` §8)
>
> **Es la observación que `verificador-ghostscript.md` §5.9 no consiguió reproducir en 20 intentos**, y no estaba en ningún encargo: salió sola, dos veces, mientras se medía otra cosa.
>
> | Ruta de la sonda `_gs_texto` | Vacíos | n | Tasa | Valores distintos | Mediana |
> |---|---:|---:|---:|---|---:|
> | **tubería** (`-sOutputFile=-` + `capture_output`) | **6** | 430 | **1,40 %** | `[0, 105/107]` | 294,2 ms |
> | **fichero temporal** | **0** | 430 | **0,00 %** | `[105]` | 286,7 ms |
>
> **No era Ghostscript: era la captura por tubería.** Contando una tanda intermedia que se sobrescribió al reejecutar el script, **18 vacíos de 680 frente a 0 de 680**, con una tasa que llegó al **4,80 %**. Nunca devolvía texto parcial: **o los 105 caracteres o cero**. **Y hay un segundo defecto silencioso de la misma ruta:** por tubería el recuento es **107** caracteres y por fichero **105** — la traducción de fin de línea del modo texto añade dos.
>
> **Por qué importa: de `_gs_texto` cuelgan P2 (severidad `fallo`), P5, P6 y P9.** Un 4,8 % de silencios convierte «el PDF conserva el texto» en un fallo aleatorio, y **P2 compara `sha256`**, así que ese ±2 no es cosmético. **Corregido: la sonda escribe a fichero temporal y lo borra en `finally`, al mismo coste.**
>
> **La lección de método llega por tercera vez, con una novedad:** *la sonda no es la verdad, es otra medida con sus propios defectos* —como `magick` devolviendo `2.7431e+303` para «sin alfa» o `SSIM = 0` para imágenes idénticas—. **Esta vez el defecto era del propio verificador.**

### Lo que sigue PENDIENTE

De los siete de `verificador-fidelidad.md` §7, los que tocan a este hueco. **Cuatro se cerraron el 21/08 a las 09:40** (`bench/verificador-ghostscript.md` §7):

- ~~**`min(alfa)` de TIFF comprimido y GIF** (estimación: 120-180 líneas) y **PNG entrelazado** (~40).~~ **CERRADOS.** Coste real: **438 líneas** para TIFF+GIF+LZW y **144** para Adam7 — **×2,9 y ×3,6 sobre la estimación**, y la diferencia entera está en lo que no se ve desde fuera (el predictor, el planar, los 16 bits, el barrido correcto de bloques del GIF y los atajos sin los que la cobertura no compensaba). **AVIF/HEIF sigue fuera de discusión por decisión, no por falta de trabajo.**
- ~~**Las reglas V2 y V5**, que el informe llama baratas.~~ **IMPLEMENTADAS, y V2 no era barata:** cuesta el **36 % de la suite de fidelidad** (ver arriba). Discriminan **5 de 5** en fallos fabricados, incluida la excepción de «se pidió cambiar el fps».
- **El decodificador VP8L escala mal**: un WebP sin pérdida de 1920×1080 *con* alfa costaría del orden de 2,3 s en Python puro. Hoy el atajo de `alpha_is_used` y el corte temprano lo hacen teórico.
- ~~**OCR con el Tesseract embebido de Ghostscript.**~~ **EJERCITADO — ver §5.**
- **Los 7 casos `no_evaluable` de `referencia.json`**: **5 de 7 CERRADOS** el 21/08 dentro del contenedor `filex-convertx`, que trae 6 de los 7 motores que faltan en Windows (`bench/aristas-nominales.md` §8). **Siguen abiertos dos, y son los mismos dos binarios que no está en ninguna imagen levantada: `qpdf` (PDF linealizado/cifrado, `rc=127`) y `tesseract`** (el OCR se cubre por la vía de Ghostscript, §5). **El coste de integración real es dos motores, no siete.**
- **Un hueco nuevo, y no es de píxeles:** una entrada **envenenada en sitio** durante la conversión produce una salida internamente coherente y `returncode 0`, y **los cuatro puntos del contrato la dan por buena** (`bench/mcp-cabos-sueltos.md` §5.6). La defensa no es un quinto punto: es **hacer el hash de la entrada en el staging y no volver a mirar el original**.

**Y lo que abren los informes del 21/08 a las 09:40 — cuatro de ellos CERRADOS a las 14:00:**

- ~~**Implementar el quinto punto** y la **regla de fidelidad del texto rasterizado**.~~ **CERRADOS los dos** (`bench/contrato-quinto-punto.md`): el punto 5 cuesta **+11,0 % del contrato con R18** y **0 falsos positivos**; I9 discrimina **6/6** y su coste real es **32–59 ms a 400×200 y 2 454 ms a 1920×960**, no 26 ms. **Los dos, arriba.**
- ~~**V2 necesita su propio interruptor.**~~ **CERRADO:** `--sin-v2`, **−46,3 % de la suite, 0 avisos cambiados**, `ok_parcial` de 8 a 13.
- ~~**Validar `P9`.**~~ **CERRADO, Y REFUTADA — ver el bloque de §5.** Sustituto medido: **el acuerdo entre dos pasadas de OCR con idiomas distintos, 16/16 sin error**.
- ~~**Añadir `ocr: true` al `pedido`.**~~ **IMPLEMENTADO.** Con `ocr: true`, **P5 invierte la exigencia** (la salida DEBE traer capa de texto: si no, `P5 fallo`) y **P9 sube de `aviso` a `fallo`**. La consecuencia va más allá del verificador: **el orquestador tiene que propagar la INTENCIÓN, no solo los parámetros del motor.** Un `pedido` que solo lleva `{destino: "pdf"}` para una reparación por OCR **es un pedido incompleto**, y ahora se nota. *El punto 4 del contrato vale lo que valga el pedido.*
- ~~**Un `txtwrite` que devolvió 0 caracteres una vez**, no reproducido en 20 intentos.~~ **REPRODUCIDO, LOCALIZADO Y CORREGIDO — ver arriba.** Era la tubería, no Ghostscript.
- **Ampliar el vocabulario de firmas del verificador.** Hoy son **24 nombres**, y eso hace que el punto 1 del contrato sea evaluable **solo en el 12 % de los destinos** de una muestra de 498 aristas (`bench/aristas-nominales.md` §11.3). **Confirmado con dos casos nuevos:** la sonda clasifica un `.html` y un `.svg` **como CSV**, y con el HTML **el contrato acierta por casualidad** con un `[p3 D2 fallo] numero de campos no constante` que no tiene nada que ver (`contrato-quinto-punto.md` §3.1). Y desde fuera: **cuando el vocabulario no cubre el destino, «arista viva» no es una medición, es una suposición** — un control con `magick identify` y `ffprobe` como terceros **eliminó 4 de 32 recuperaciones** (`invocacion-aristas.md` §7.3). Si FileX declara 500 formatos de salida, tiene que poder verificar 500 firmas — **o declarar menos**.
- **`D3/D6/D7`** (contenido exacto de los campos de datos) siguen sin implementar.
- **Los parámetros de rasterizado y la fórmula de similitud de I1** en `bench/fidelidad-caminos.md`, sin los cuales su 99,0 % no se puede cerrar (§2). **Sigue NO REPRODUCIDO, no refutado.**

**Y lo que abre esta pasada (21/08, 14:00) — `bench/contrato-quinto-punto.md` §10:**

- **El miembro descubierto de la familia:** audio con un canal silenciado hacia un destino **con pérdida**. Propuesta sin medir: energía por canal con `ffmpeg -af astats`.
- **Un suelo duro de PSNR para V8.** Un vídeo enteramente negro sale con **5,39 dB** y severidad `aviso`. I7 ya tiene un suelo de 20 dB por la misma razón.
- **Validar el sustituto de `P9`** —el acuerdo entre idiomas— **fuera de Ghostscript** y sobre vocabulario que un reconocedor inglés no comparta. Son **16 pares y un solo motor**, y dos idiomas del mismo motor podrían acordar en su propio error.
- **Decidir si `P9` se retira o se sustituye.** Hoy sigue en el código, marcada **no fiable**.
- **I9 solo cubre PNG**, y no cubre PNG entrelazado ni destinos PDF.
- **El punto de cruce «en proceso / `magick`»** está medido en tres tamaños (0,08 / 0,32 / 1,84 Mpx). **La curva fina y el umbral exacto, sin medir.**
- **El punto 5 no cubre subdirectorios:** `censar_dir` no es recursivo, así que un motor que cree un directorio y escriba dentro cuenta como **una** entrada nueva. Ningún caso del corpus lo hace; **queda declarado**.
- **El patrón oro no tiene ni una salida multifichero**, así que el «0 falsos positivos» del punto 5 se apoya en los cuatro casos fabricados. **Ampliarlo con una salida HLS y una secuencia `%d`** cerraría el hueco.
- **La discrepancia de recuento de líneas** (3 859 publicadas frente a ~3 530 implícitas).

### Base ya disponible — MEDIDA

`bench/salidas-referencia/referencia.json`: **46 reglas de regresión**, 53 salidas caracterizadas, 39 órdenes reproducibles y **17 pérdidas catalogadas** que distinguen *pérdida inevitable* de *fallo del motor*. Es el patrón oro contra el que verificar.

---

## 2 · Grafo con coste por arista — **el multi-salto, REFUTADO**; sobrevive la selección con coste

### Lo MEDIDO

- **0 de 7 orquestadores implementan búsqueda de camino.** Barrido de `dijkstra|shortest.?path|conversion.?graph|multi.?hop|find.?path` sobre los siete árboles: cero coincidencias reales.
- **152 584 → 447 398 pares** alcanzables con hasta 3 saltos: **2,93×** con los mismos motores. Calculado sobre las tablas reales de los 20 adaptadores. **La cifra es correcta y reproducible** (recalculada: 152 478 → 446 006, desvío −0,3 %), **pero es alcanzabilidad declarada, no capacidad instalada ni fidelidad** — ver abajo.
- ~~`epub→png`, `docx→webp` y `tex→docx` son **imposibles hoy** y salen en 2 saltos.~~ **REFUTADO al ejecutarlo:** de los tres, solo `docx→webp` es alcanzable en esta máquina.
- El único indicio de que la necesidad existe está resuelto **a mano dentro de un adaptador**: `transmute/backend/converters/libreoffice_convert.py:333` — *"Image output via PDF intermediary"*.
- **ConvertX elige mal el motor**: en `png→jpg` gana ffmpeg teniendo vips, ImageMagick y GraphicsMagick disponibles, por un `break` que solo rompe el bucle interno (`main.ts:213-229`).

### Lo que era PENDIENTE, ahora MEDIDO — y desmiente la cifra

Este documento decía: *«qué fracción de los 447 398 caminos produce una salida aceptable. Nunca se midió»*, y sospechaba, sin datos, que **el número lo sobrevende**. **La sospecha era correcta y ahora está medida.** `bench/fidelidad-caminos.md` ejecutó **69 caminos reales** (47 multi-salto, 22 de un salto como control) y clasificó cada salida contra las reglas de regresión y las 17 pérdidas catalogadas del patrón oro:

| Categoría | Multi-salto (n=47) | 1 salto (n=22) |
|---|---:|---:|
| ÍNTEGRO | 10,6 % | 50,0 % |
| PÉRDIDA INEVITABLE | 21,3 % | 4,5 % |
| DEGRADADO | 38,3 % | 22,7 % |
| **DESTRUIDO** | **17,0 %** | 9,1 % |
| FALLO | 12,8 % | 13,6 % |

> **Aceptable (íntegro + pérdida inevitable): 31,9 % en multi-salto frente al 54,5 % de un salto.** Casi uno de cada tres caminos multi-salto destruye el contenido o no produce nada.
>
> *(La muestra está sesgada a propósito hacia los cruces de familia y las rasterizaciones — describe el fallo, no estima una media poblacional. El sesgo está declarado en `bench/fidelidad-caminos.md` §2.)*

**Y el 2,93× se deshace en cuatro pasos, todos MEDIDOS:**

1. **Con los motores realmente instalados aquí cae a 1,93×** (138 501 → 266 927 pares). Un tercio del multiplicador se evapora antes de convertir nada: los saltos intermedios interesantes los daban pandoc, calibre, LibreOffice nativo, vips e inkscape, que no están.
2. **De los 128 426 pares nuevos, solo 610 (0,48 %) son plausibles** — es decir, con ambos extremos en el catálogo de formatos que un producto real declara pedir y con una pareja de familias que signifique algo. **La ganancia honesta es +32,7 %, no +193 %.** El 59 % de los pares «pedidos» que el grafo gana son cosas como `docx→mp3` e `imagen→srt`.
3. **820 de los 1 599 pares «pedidos» (51 %) tienen PDF como único intermedio posible.** El multi-salto de esta máquina es, casi entero, *«pásalo por PDF»* — el caso que `transmute/backend/converters/libreoffice_convert.py:333` resolvió a mano hace años.
4. **`epub→png`, `epub→docx` y `tex→docx` no se pueden ejecutar.** Gotenberg declara `.epub` pero **LibreOffice no lo importa** (HTTP 500 con tres EPUB distintos), y `tex→docx` es inalcanzable sin Pandoc ni XeLaTeX. Eran los ejemplos estrella de la tesis.
   > **Corregido el 21/08 — MEDIDO (`bench/aristas-nominales.md` §8.1).** **`epub→pdf` NO es una arista nominal del grafo: es una arista nominal *de un motor*.** El fallo es de **LibreOffice**, no de Gotenberg: se reproduce con otro build, en otro sistema operativo, invocando `soffice --headless --convert-to pdf` directamente (**`rc=1`, sin salida**). LibreOffice **exporta** EPUB y no lo **importa**. **Y Calibre la hace bien**: `ebook-convert entrada.epub c_epub.pdf` → **`rc=0`, PDF de 26 817 B, 565 caracteres recuperados, centinela `FILEXSENTINELA7743` y la tabla `AX-1` presentes**, 7 045 ms. ConvertX **tiene** adaptador de Calibre (`calibre.ts`, 26 entradas / 20 salidas).
   >
   > **Lo que falla no es el grafo: es la selección de motor** — el bug conocido de `ConvertX/src/converters/main.ts:213-229`. **Refuerza la reformulación de este §2** («lo que se sostiene es la selección correcta con coste explícito») y **obliga a revisar el criterio de aceptación del hito 1** de `PLAN-ORQUESTADOR.md` §7, que se reescribió dando estos dos ejemplos por muertos. Los otros dos siguen como estaban: `tex→docx` sigue sin Pandoc ni XeLaTeX en Windows.

**El detalle más incómodo:** el estrato que mejor puntúa —documento→imagen, 7 de 8 aceptables— **aprueba solo porque el destino es una imagen y perder el texto es «inevitable» por definición**. `xlsx → pdf → png` es un aprobado formal y una hoja de cálculo que ya no se puede sumar. **El multi-salto funciona mejor justo donde menos sirve.**

### La reformulación honesta, ahora reforzada

Nuestra propia evidencia golpea la tesis original desde otro lado: **ConvertX ya "alcanza" conversiones que entrega falsas**. Si el sector falla en producir correctamente lo que ya declara, ampliar el alcance ataca el problema equivocado.

**Lo que se sostiene del grafo es la selección correcta con coste explícito** — que arregla por construcción el bug de despacho de ConvertX, y que se cobra **en el primer salto**. Las 17 pérdidas catalogadas de `referencia.json`, con su distinción *inevitable / fallo del motor*, **son literalmente la tabla de pesos** de la función de coste (`bench/fidelidad-caminos.md` §5).

> **El multi-salto era «la propina». Ahora sabemos que la propina es pequeña (610 pares) y arriesgada (31,9 % de acierto).** Merece existir en el motor —cuesta poco, y con él vienen las **aristas de reparación por OCR**, que recuperan el 99,0 % del texto de un PDF ya rasterizado— pero **no como titular**. Es una consecuencia de tener bien modelado el coste, no la tesis.

### La tasa de aristas nominales, CERRADA con su cifra — `bench/aristas-nominales.md` (21/08/2026)

Este documento decía: *«sondearlas todas es la medición que cerraría el hueco del todo»*. **No hizo falta sondearlas todas, y ese es el resultado metodológico:** las aristas son cuadráticas (`entradas × salidas`) y las **semiaristas** son lineales (`entradas + salidas`). El censo de las **1 104 semiaristas** cabe en **9 min 35 s** y decide por sí solo el 45 % de la población; el resto se estima con una muestra aleatoria estratificada de **498 aristas ejecutadas y verificadas** (más 100 del estrato PDF).

> ### **El 50,5 % de las aristas declaradas que se han podido verificar NO EXISTE.**
> **IC 95 % [48,2 % – 53,0 %]**, sobre las **62 487 aristas (45,1 % de la población)** con veredicto de ejecución. **MEDIDO.**

| | Aristas | % de las 138 501 | Cómo se sabe |
|---|---:|---:|---|
| **Refutadas por ejecución de una semiarista** | **22 235** | **16,05 %** | **Censo**, no muestra: 1 104 sondas |
| Con las dos semiaristas vivas → muestreadas | 40 252 | 29,06 % | n=498; **23,1 %** nominales [19,6–27,0] |
| Indeterminadas (no se pudo fabricar el origen) | 75 874 | 54,78 % | **Sin veredicto; se declara, no se rellena** |
| Ghostscript / Gotenberg (tratadas aparte) | 140 | 0,10 % | |

Sobre la población **entera**, con el supuesto escrito en cada escenario: **cota inferior 22,8 %** (las indeterminadas son todas reales) · **central 48,6 %** (se comportan como las verificadas de su propio motor) · cota superior 77,5 %.

**El 50,5 % es explícitamente una COTA INFERIOR**, por tres sesgos que su propio informe declara: las semiaristas de entrada se probaron con ficheros **que escribió el propio motor** (el mejor caso posible); el criterio «la firma no es la del formato pedido» **solo fue evaluable en 62 de 498 aristas (12 %)**; y el criterio de vaciado **no detecta** las salidas que escriben fuera del destino (§1, quinto punto).

> ### Y la refutación parcial, que es lo que impide que la cifra engañe: **la tasa NO es uniforme, factor 18**
>
> | Estrato | N (marco) | n | **Nominal** | IC 95 % |
> |---|---:|---:|---:|---|
> | `ffmpeg` · **distinta** familia | 7 414 | 91 | **76,9 %** | [67,3 – 84,4] |
> | `ffmpeg` · misma familia | 8 985 | 111 | 28,8 % | [21,2 – 37,9] |
> | `imagemagick` · distinta familia | 4 760 | 59 | 5,1 % | [1,7 – 13,9] |
> | `imagemagick` · **misma** familia | 19 093 | 237 | **4,2 %** | [2,3 – 7,6] |
>
> **No es que ffmpeg sea peor: es que su producto cartesiano cruza modalidades y el de ImageMagick no.** Declarar `473 × 202` es declarar que se puede convertir un `.aptx` en un `.gif`.
>
> ### **Y el estrato prioritario —PDF como intermedio— sale al 3,0 %** [1,0 – 8,5], sobre 100 aristas
>
> `bench/fidelidad-caminos.md` §1.3 midió que **820 de los 1 599 pares «pedidos» (51 %) tienen PDF como único intermedio posible**: si una arista hacia PDF fuera nominal, se caería media tesis. **No lo son.** Categorías del estrato: ÍNTEGRO 85 · DEGRADADO 12 · DESTRUIDO 1 · FALLO 2.
>
> **Las aristas que el multi-salto usa de verdad SÍ existen. Eso REFUERZA `fidelidad-caminos.md`, no lo contradice:** el «pásalo por PDF» que aquel informe llamaba *«un caso especial resuelto a mano hace años»* es también **el único trozo del grafo cuyas aristas se sostienen al ejecutarlas**. **Los dos hechos —el 50,5 % global y el 3,0 % del estrato útil— hay que citarlos juntos o la cifra miente.**

**Los 12 DEGRADADO del estrato PDF son once veces la misma regla:** `P7 · 1 px → 1 pt: página absurda (1920 × 1080 pt = 677 × 381 mm)`, en `png→pdf`, `jpeg→pdf`, `gif87→pdf`, `group4→pdf`… **`imagen → pdf` de ImageMagick existe y funciona; lo que está mal es que nadie declara la densidad.** No es un caso raro: es **el comportamiento por defecto de toda esa familia de aristas.**

**Y hay un hallazgo que cambia la unidad del grafo, con cuatro medidas independientes:**

| Medida | La misma arista es… |
|---|---|
| `epub→pdf` | **real con Calibre** (26 817 B, centinela y tabla intactos) y **nominal con LibreOffice** (`rc=1`) |
| `png→ico` | **real por ffmpeg** (tiene caso especial en `ffmpeg.ts:702`) y **nominal por ImageMagick** (`width or height exceeds limit`, techo de 256 px, sin caso especial en `imagemagick.ts`) |
| `svg→png` | **real en el ImageMagick de Windows** y **nominal en el de Debian** del contenedor (`rc=1`) |
| Los 20 crudos sin cabecera (`rgb`, `yuv`, `cmyk`…) | **irrecuperables con la invocación de ConvertX** (que no pasa `-size`) y **triviales con ella** |

> **La arista mínima viable no es el par de formatos: es `(origen, destino, motor, parametrización, build)`.** Cualquier tabla de aristas que no lleve el *build* como dimensión **está mintiendo en alguna máquina**.

### Cuánto del 50,5 % es invocación y no capacidad — CERRADO · `bench/invocacion-aristas.md` (21/08/2026, 14:00)

Este documento señalaba como *«la pregunta que decide si FileX puede prometer más aristas que ConvertX con los mismos motores»*. **Se midió reintentando, una a una, las 34 + 37 semiaristas muertas y las 118 aristas nominales de la muestra —un censo de los fallos, no una muestra nueva— con una política de invocación (`P2-INV`) declarada ANTES de medir, y con el mismo juez.**

> ### **El 18,8 % del 50,5 % es invocación, no capacidad.** IC 95 % [16,8 – 21,3]. **MEDIDO.**
> Con los **mismos motores, el mismo build y el mismo corpus**, la tasa nominal baja de **50,5 % a 41,0 %**: **5 930 aristas de las 31 533** que se declararon inexistentes sí existen, y lo que fallaba era la orden.

| Categoría | Qué significa | Aristas | % del 50,5 % |
|---|---|---:|---:|
| **1 · Recuperable con bandera** | la arista existe y ConvertX la llama mal. **Ganancia automática** | **3 226** | **10,2 %** |
| **2 · Recuperable con un parámetro del usuario** | existe, pero el dato **no está en el fichero**. No es automática | **2 704** | 8,6 % |
| **3 · Irrecuperable** | no hay pista compatible, o el codificador no está compilado | **25 603** | **81,2 %** |

> **La afirmación de producto que sale de aquí, con su acotamiento pegado:** **FileX puede ofrecer un 10,2 % más de aristas que ConvertX con exactamente los mismos motores instalados y sin pedirle nada al usuario** (+3 226), y **un 18,8 % si existe un canal para los metadatos** (+5 930). **Lo que NO se puede prometer es el otro 81,2 %.** La tesis del §2 sobrevive casi intacta; lo que cambia es que **ahora tiene una cota, y la cota es del producto, no del sector**.

**Y lo que impide inflar la cifra pesa tanto como la cifra — MEDIDO:**

- **69 de las 118 aristas nominales (58,5 %) son «el muxer no admite ninguna pista que la entrada tenga»**: `hevc → opus`, `gif → caf`, `tta → gif`, `flac → fits`. **Son declaraciones sin sentido, no órdenes mal escritas.** Ninguna invocación arregla convertir un `.aptx` en un `.gif`, porque no hay nada que convertir.
- **19 de las 33 semiaristas de salida muertas de ffmpeg son codificadores no compilados** (`ac4`, `dts`, `gsm`, `speex`, `vc1`…). **Eso es build, no invocación** — y confirma que la arista mínima viable necesita el `build` como dimensión.
- La regla negativa que hace honesta la medida: **si el muxer solo admite un tipo de pista que la entrada no tiene, la arista es irrecuperable y NO se fabrica la pista que falta.**

**Dónde se recupera, y el gradiente se invierte — MEDIDO:**

| | Muertas | **Revividas** | |
|---|---:|---:|---:|
| Semiaristas de **entrada** | 34 | **22** | **64,7 %** |
| Semiaristas de **salida** | 37 | **8** | 21,6 % |
| Aristas que eso devuelve al marco | | **4 627** | censo, sin error muestral |

**Leer mal es un problema de invocación; escribir lo que el binario no sabe codificar es un problema de build.** Y en el residuo de 118, **donde ConvertX fallaba poco fallaba por invocación** (ImageMagick misma familia: 80,0 % recuperable) **y donde fallaba mucho fallaba por capacidad** (ffmpeg cruzando familias: 17,1 %). **Es exactamente el orden contrario al de la tasa nominal.**

**Lo que más rinde, en orden:**

1. **`-frames:v 1 -update 1` es la bandera con mejor relación coste/beneficio del proyecto: recupera 13 de las 27 aristas del residuo.** El «`Error opening output files: Invalid argument`» que aparecía 69 veces tenía **dos causas distintas** que la instrumentación anterior no separaba: casi siempre es incompatibilidad de modalidad (irrecuperable), pero en **13 casos** es que **el destino es una imagen única y la entrada tiene varios fotogramas**. Dos banderas lo arreglan.
2. **17 de los 20 formatos crudos sin cabecera reviven** — pero hacen falta **cuatro** datos externos, no uno: geometría, **profundidad**, canales y entrelazado. *(Ver la trampa 23 de `CLAUDE.md`: releer con `-depth 8` entrega geometría correcta y píxeles basura.)* `ftxt` no revive (RMSE 0,652 contra el original), `map` exige un fichero de paleta aparte y `bgro` **revienta con `0xC0000005`** porque el escritor emite 6 bytes por píxel para un formato de 4 canales. **`bayer`/`bayera` se cuentan como recuperados pero su recuperación está SUPUESTA, no demostrada** (≈366 aristas, 0,2 puntos).
3. **`imagen → pdf` con `-density`: las 6 de 6 degradaciones P7 desaparecen.** *(Aviso de contabilidad: esto **no** entra en el 18,8 %, porque una degradación no es una arista nominal — ya contaban como reales. Aquí se mide **calidad, no cantidad**.)* ConvertX entrega una página de **677,3 × 381,0 mm**; con `-density 150` sale 325,1 × 182,9 (aún un A3 y medio); **la variante que hay que implementar es la que calcula la densidad para que la imagen quepa en la página objetivo: 210,0 × 118,1 mm, A4 exacto, 7 de 7 ÍNTEGRO.**
4. **El techo de 256 px del formato ICO:** `-resize 256x256> -define icon:auto-resize=…` recupera 7 aristas. **ConvertX ya tiene el caso especial en `ffmpeg.ts:702` y no lo tiene en `imagemagick.ts`.**

**Tres autocríticas del propio informe que cambian una recomendación cada una:**

- **La autoconsistencia de un sondeo exige que el escritor y el lector sean el mismo motor.** `ffmpeg -i x m.rgb` usa el muxer `rawvideo`, que **ignora la extensión y vuelca el `pix_fmt` de la entrada**: el fichero llamado `m.rgb` no contiene RGB. **Si FileX sondea el mapa de capacidades al arrancar, tiene que emparejarlos.**
- **Forzar el códec por defecto del muxer es PEOR que no forzar nada** con `image2` (escribe un JPEG dentro de un `.ppm`). *«Sondear en ejecución, no deducir» sigue siendo correcto, pero **un valor que el motor declara «por defecto» no es una capacidad: es un valor por defecto**, y el motor puede tener mejor lógica que él.*
- **El control antifalso positivo eliminó 4 de 32 recuperaciones** (`ogg → im24` y `wtv → im1` escribían **Sun Raster**; `tta → h265.mp4` entregaba un MP4 **sin una sola pista de vídeo**). **Sin ese control la cifra habría salido 19,8 % en vez de 18,8 %.**

### El censo de Ghostscript y Gotenberg — CERRADO, y coincide con el estrato PDF por un camino independiente

**MEDIDO** (`bench/invocacion-aristas.md` §8). Son el **0,10 %** de la población y **toda** la superficie documental del grafo:

| Motor | Aristas | Evaluadas | **Nominales** | Tasa |
|---|---:|---:|---:|---:|
| **ghostscript** | 9 | **9 (censo completo)** | **0** | **0,0 %** |
| **gotenberg-chromium** | 25 | **25 (censo completo)** | **0** | **0,0 %** |
| gotenberg-lo | 102 | 30 | **2** | 6,7 % |
| **Total** | **136** | 64 | **2** | **3,1 %** [0,9 – 10,7] |

> **La superficie documental es la más sólida que se ha medido en este proyecto: 3,1 % nominal, frente al 23,1 % del marco general y al 50,5 % global. Y coincide con el 3,0 % del estrato PDF por un camino completamente distinto, con otros motores y otro protocolo.** Dos medidas independientes que dan lo mismo. **Si FileX tiene que elegir dónde prometer, es aquí.**

Las dos nominales son `epub → pdf` y `dbf → pdf`, las dos con **HTTP 500 de LibreOffice**. **`epub → pdf` se reproduce por tercera vez y por un tercer camino** —falla con LibreOffice dentro de ConvertX (`rc=1`), falla vía Gotenberg (HTTP 500) y **funciona con Calibre**—: no es una arista nominal del grafo, **es una arista nominal de un motor**. **Y el sesgo hay que decirlo entero: 72 de las 102 extensiones de LibreOffice no se pudieron materializar** —son los formatos propietarios heredados que LibreOffice lee y no escribe—, así que **ese 3,1 % es también una cota inferior. PENDIENTE.**

### `qpdf` y `tesseract` dejan de ser un pendiente — MEDIDO (`bench/invocacion-aristas.md` §9)

**Ocho líneas de Dockerfile, 28,1 s de construcción y +50 MB (+0,9 %) sobre la imagen de ConvertX.** `qpdf 12.4.0` resuelve **7 de 7 operaciones** (`--linearize`, `--encrypt`, `--decrypt`, `--check`, `--json`, `--split-pages`, fusión), todas `rc=0` en 117–1 068 ms. `Tesseract 5.5.0` + Leptonica 1.86.0, **con `spa` incluido** vía `tesseract-ocr-spa`: **eso resuelve la nota de `CLAUDE.md` §2 sobre distribuir 2–4 MB de `tessdata` por idioma a mano**, al menos para la vía de contenedor.

> **El coste de integración real de los 7 casos `no_evaluable` de `referencia.json` queda medido: dos motores, 50 MB, 28 segundos. No es un argumento contra añadirlos: es un argumento a favor.**

**Y un contraste que merece quedar escrito, porque es material para la heurística de degradación (B7):**

| Documento | ppp nativos | Tesseract 5.5.0 **externo** | gs `-sDEVICE=ocr` (Tesseract **embebido**) |
|---|---:|---:|---:|
| `patologico_escaneado` | 200 | **0,00 %** | **0,0 %** |
| `escaneado_d1` | 150 | **0,00 %** | **0,0 %** |
| `escaneado_d2` | 100 | **32,10 %** *(0,00 % a 150 ppp)* | **0,0 %** |
| `escaneado_d3` | 100 | **100,00 % — devuelve 0 bytes** | **165,8 % — alucina** |
| `escaneado_d4` | 200 | 51,15 % *(82,89 % a 150 ppp)* | — |

> **El Tesseract externo falla en `d3` devolviendo un fichero de 0 bytes; el embebido en Ghostscript falla en el mismo documento ALUCINANDO al 165,8 %. Mismo motor nominal, dos modos de fallo opuestos según el envoltorio** — la diferencia tiene que estar en el preprocesado que aplica cada uno. **Un motor que devuelve 0 bytes y otro que devuelve más texto que la referencia son la misma señal de fallo vista desde dos lados. PENDIENTE** de aislar la causa.
>
> **Y `escaneado_d2` refuta la regla de ppp para Tesseract, con n=1: 0,00 % a 150 ppp frente a 32,10 % a sus 100 nativos.** A este motor **sobremuestrear no le es tolerable: le es obligatorio**. Es evidencia convergente, desde fuera de los cuatro motores neuronales, de que **la regla de ppp es por motor** (§5). *(En `d4`, en cambio, el nativo le conviene: 51,15 % frente a 82,89 %. **Ni siquiera dentro de un motor hay un factor único**, pero el reparto entre motores es mucho mayor que dentro de uno.)* **51,15 % deja a Tesseract el peor de los cinco motores sobre `d4`**, con una ventaja decisiva: **VRAM 0 y va en el mismo contenedor que el resto.**

### Lo que sigue PENDIENTE

- **Si esas conversiones se piden de verdad.** El catálogo de SnapOtter es un proxy de demanda, no demanda medida. *(Una arista nominal en un formato que nadie pide no cuesta nada; una en `png→ico`, sí.)*
- **El 54,78 % indeterminado.** Exige un corpus de los 445 formatos que **ningún motor local escribe** — por definición, no se pueden fabricar aquí. La vía realista es el corpus FATE de ffmpeg (~1 GB) o los bancos de muestras de cada formato. **Es lo único que convierte el escenario central (48,6 %) en un número medido.** **Y ha empeorado un poco: al revivir semiaristas de entrada, 2 868 aristas pasan de «muerta» a «sin veredicto»** — están contadas como nominales en la cifra conservadora y **podrían ser recuperaciones adicionales**.
- ~~**Cuánto de ese 50,5 % se recupera con una invocación mejor.**~~ **CERRADO: el 18,8 %** [16,8–21,3], del que **10,2 % es ganancia automática**. Ver arriba.
- ~~**Las 140 aristas de Ghostscript y Gotenberg** sin muestrear.~~ **CERRADAS: 3,1 % nominal** [0,9–10,7], con censo completo de Ghostscript (9/9 reales) y de Gotenberg/Chromium (25/25 reales). Ver arriba.
- **La profundidad de los crudos de terceros.** Todo lo medido son ficheros que escribió el propio ImageMagick a **16 bits**. Un `.rgb` de 8 bits de otra procedencia **daría basura con la misma bandera**, y no se sabe cuánta gente lo tiene a 8 bits. **Eso hace la categoría 2 más cara de lo que parece: FileX no necesita «un dato», necesita cuatro, y que sean los del fichero real.**
- **Las 4 semiaristas de salida que resistieron el barrido** (`amv`, `gxf`, `mlp`, `thd`) y las **11 aristas del residuo con `received no packets`**. Dos intentos gastados en cada una.
- **`bayer` y `bayera`** no tienen referencia ideal para un mosaico CFA: su recuperación está **supuesta**.
- **Si estas aristas se piden.** Sigue abierto lo de siempre: de las 27 recuperadas del residuo, **las de la familia `ico` son las únicas que un producto real sirve todos los días**.
- **El coste en tiempo de `P2-INV` frente a la invocación de ConvertX.** Sondear el muxer y el codificador añade **dos lanzamientos de proceso por arista**, cacheables, pero **no cuantificados**.

### Y una nota sobre el 99,0 % de las aristas de reparación — **NO REPRODUCIDO**, no refutado

Este documento cita, más abajo, que las aristas de reparación por OCR **«recuperan el 99,0 % del texto de un PDF ya rasterizado»** (`bench/fidelidad-caminos.md`, camino I1). Reejecutado el 21/08 (`bench/verificador-ghostscript.md` §5.7): **94,7 %** con espacios normalizados y **97,1 %** ignorándolos, con `eng`; 94,7 % y 96,2 % con `spa`. **No llega al 99,0 % con ninguna de las tres lecturas.**

**No se declara refutado, se declara NO REPRODUCIDO**, y por un motivo concreto: aquel informe **no publica ni los ppp de su rasterizado, ni el idioma de OCR, ni su fórmula de similitud**. Lo que sí queda **MEDIDO** es que el orden de magnitud correcto es **94-97 %**, y que **la mayor parte de la pérdida son espacios, no letras** (`Col A` → `ColA`, `FileX` → `Filex`) — lo cual, si se confirma, hace la cifra *mejor* para recuperar contenido y *peor* para reproducir maquetación.

---

## 3 · MCP multi-modal en un solo servidor — real, mucho más estrecho

### Se degradó dos veces durante la investigación

**Primera:** afirmé que ningún conversor grande expone MCP. **Falso.** Stirling-PDF (89,9k ⭐) tiene un servidor MCP completo en `app/proprietary/`, con catálogo autodescubierto, ejecutor, autenticación por clave de API y configuración de seguridad. **Está detrás de una suscripción de pago** — MEDIDO leyendo su `LICENSE` y su árbol.

**Segunda:** el patrón de asa no es un hallazgo de FileX. **docling-mcp ya lo implementa bien**, con anotaciones `readOnlyHint`/`destructiveHint` correctas y liberación de memoria. Es de IBM y es MIT.

### Lo que SÍ sobrevive — MEDIDO

**Los servidores no coexisten.** `markitdown-mcp` pide `mcp~=1.8.0` y `docling-mcp` pide `mcp>=2.0.0`; negocian versiones distintas del protocolo (2024-11-05 frente a 2025-11-25). **Hubo que darle un entorno virtual a cada uno.**

> **Matizado MEDIDO (`bench/sdk-mcp-capacidades.md` §5.1):** hay **tres** eras de protocolo, no dos — `mcp 2.0.0` negocia **2026-07-28**. Y la incompatibilidad **es asimétrica**: un servidor sobre 2.0.0 habla con clientes 1.8.1 y 1.29.0 sin problema; **un servidor 1.8.x muere ante un cliente 2.0.0** (caída de proceso, no error de protocolo). El aislamiento por venv sigue siendo necesario para los servidores de terceros; **para el servidor de FileX la restricción es `mcp>=2.0.0`.**

Quien quiera cubrir documentos, vídeo, audio e imágenes acaba con **cuatro servidores incompatibles**, y los tres de multimedia tienen 84, 26 y 18 estrellas.

**El hueco no es "falta un MCP". Es "faltaría uno que cubra todas las modalidades a la vez".**

### Cifras de apoyo — MEDIDAS

- **85 259 tokens frente a 36** para el mismo PDF de 60 páginas: **~2 400×**. El volcado ocupa el 42,6 % de una ventana de 200 K.
- **19 herramientas = 5 280 tokens de suelo fijo**; limitando al grupo `conversion`, 880 tokens y 3 herramientas (−83 %).
- En documento pequeño **el asa pierde** (32 frente a 56 tokens): tiene coste fijo.

### Lo PENDIENTE — y no es menor

**Todas las mediciones vienen de MCP documentales, donde la salida es texto. El caso binario no se ha probado.**

- ~~**Qué devuelve un MCP tras convertir un vídeo.**~~ **RESUELTO (20/08/2026).** Los tres precedentes se ejecutaron. El asa cuesta **32-72 tokens con independencia del tamaño** (15,5 MB → 32 tokens). Pero `image-worker-mcp` **sí devuelve la imagen entera**, como base64 dentro de un `TextContent` — un patrón que la regla de FileX no cubría. Ver `RESULTADOS-MCP.md` §3.
- ~~**Si 27 herramientas saturan la elección del modelo.** **SIGUE PENDIENTE.**~~ **RESUELTO el 21/08/2026 con 540 ejecuciones — y EN CONTRA de la hipótesis.** Ver el bloque siguiente.
- ~~**Si una imagen puede devolverse como contenido.**~~ **RESUELTO: no hay umbral que valga la pena.** A **0,93 tokens por byte**, el punto de rentabilidad está en 1-2 KB. Una miniatura de 10 KB cuesta 132× su ruta. La firma de las herramientas de FileX no cambia.
  - **Precisión MEDIDA (`bench/mcp-cabos-sueltos.md` §1.3):** los 0,93 tok/B son el coste del **base64 dentro de texto**. Un `ImageContent` **nativo** a través del cliente real cuesta **por píxel, no por byte**: **2.814 tokens medidos** para `tipico.png` (42.855 B, 1920×1080), frente a los ~39.855 del base64 encubierto y a los **32-72 del asa**. **La conclusión no cambia, se refuerza:** el `ImageContent` nativo es ×14 más barato que el antipatrón y aun así **×39 a ×88 más caro que devolver la ruta**.

### La saturación del catálogo, MEDIDA — `bench/saturacion-herramientas.md` (21/08/2026, 02:49)

**540 ejecuciones independientes** (Haiku 4.5 ×10 reps y Sonnet 4.5 ×5 reps, sobre 12 tareas y 3 catálogos), con `claude -p` en proceso nuevo, `--tools ""` y un servidor MCP de sonda que sirve los catálogos reales sin ejecutar ffmpeg.

| | **A · 27 herr.** (7.886 tok) | **C · 14 herr.** (4.749 tok) | **B · 8 herr.** (2.306 tok) |
|---|---:|---:|---:|
| Haiku — acierto permisivo | **100 %** | 100 % | **85 %** |
| Haiku — elección trampa | **0 %** | 0 % | **15 %** |
| Sonnet — acierto permisivo | **98 %** | 93 % | **77 %** |
| Sonnet — elección trampa | **2 %** | 7 % | **17 %** |

> **MEDIDO: el catálogo de 27 no eligió peor que el de 8. Eligió mejor**, con p < 0,001 en los dos modelos (Fisher exacto bilateral). El estrato de control acertó **100 %** en los tres catálogos y los dos modelos.
>
> **Y la redundancia tampoco degrada.** El contraste limpio A (27) vs **C (14 = A menos las 13 subsumidas, mismo autor y mismo estilo)** no muestra diferencia una vez se quita la única tarea cuya clave de corrección era un juicio discutible del propio autor: **100 % vs 100 %** en los dos modelos.
>
> **Y la predicción estructural más fuerte del proyecto falló.** El par `set_audio_bitrate` / `set_video_audio_track_bitrate`, que `bench/mcp-refs-multimedia.md` §5.2 declaró «el peor» del catálogo, acertó **30 de 30**.

**Qué cambia para FileX — tres cosas:**

1. **El objetivo de cuatro herramientas se sostiene, pero SOLO por coste.** El segundo argumento independiente que se buscaba —«un catálogo grande hace elegir peor»— **no existe**. **MEDIDO.**
2. **El coste está peor de lo que se creía: el catálogo se paga en cada turno, ×2,0–2,6.** Un catálogo de 7.886 tokens cuesta ≈23.600 tokens de entrada por petición sencilla; uno de 2.306, ≈8.800. **El presupuesto de ≤1.200 tokens de las cuatro herramientas de FileX son en realidad ≈2.400–3.100 tokens por petición.** Ese, y no 1.200, es el número que hay que comparar con el resto de la ventana (§3.6 del informe).
3. **Aparece un riesgo nuevo, y va en dirección contraria a la intuición: un catálogo demasiado escueto produce FALLOS SILENCIOSOS.** Cuando el catálogo no cubre lo que se pide, el modelo **no se abstiene: llama a la herramienta más parecida y declara éxito con un dato falso** — **15–17 % de las peticiones** con el catálogo de 8. Ejemplo literal medido: «*se ha creado con el audio re-codificado en AAC, reduciendo el bitrate desde los 320 kbps originales*», cuando los 96 kbps pedidos **no se aplicaron** y no hubo error.

> **Eso convierte la cobertura declarada de `convert` en un requisito de seguridad, no de comodidad.** `list_targets` deja de ser una comodidad y pasa a ser el mecanismo que permite responder «¿puedo hacer X?» sin inventar; `convert` debe **fallar explícitamente** ante una combinación no soportada; y su descripción debe **declarar sus límites**, no solo sus capacidades — ninguno de los tres servidores de referencia describe lo que *no* hace, y ahí es exactamente donde se producen los fallos silenciosos.

**El hallazgo colateral que hay que aplicar sí o sí:** **0 de 193 parámetros** de los tres catálogos de referencia lleva `description` en su JSON Schema (§5.4). FastMCP deriva el esquema de las anotaciones de tipo y deja toda la semántica en la prosa del docstring. Para FileX, cuya `convert` tendrá `enum` generados desde el registro, **cada parámetro debe llevar su `description` en el esquema**.

**Lo que este experimento NO demuestra, dicho por él mismo (§6.3):** nada sobre 60 o 200 herramientas, ni sobre varios servidores MCP a la vez, ni sobre modelos de otras familias o locales pequeños; y con n=120 por celda **no detecta caídas de 2-3 puntos**. La temperatura **no es fijable** desde el CLI: es la limitación más seria del instrumento. **PENDIENTE.**

Ver `RESULTADOS-MCP.md`.

---

## 4 · NVENC en vídeo — real, pero solo importa en lote

### Lo MEDIDO (medianas de n=9)

- **0 de 7 orquestadores lo usan**, ni siquiera los que ya integran FFmpeg.
- **HEVC: 8,39×** (16 598 → 1 978 ms). H.264: **2,74–2,98×**. 4K: 2,67×.
- `hevc_nvenc` cuesta lo mismo que `h264_nvenc`, mientras `libx265` es 3× más lento que `libx264`: **por eso HEVC es donde la GPU se paga**.
- `av1_nvenc` **falla con `No capable devices found`** pese a aparecer en `ffmpeg -encoders`: Ampere no tiene codificador AV1.

### Lo que lo acota — también MEDIDO

- **NVENC se pasa un 8–11 % del bitrate pedido** (2 214 kbps cuando se piden 2 000), frente al +1,3 % de x264.
- **La tubería GPU completa no aporta nada**: −13 % a +3 %, y **−34 % con escalado**.
- Para una conversión suelta, 16 s frente a 2 s **no cambia el comportamiento de nadie**.

### Lo PENDIENTE

- **Rendimiento en lote sobre una carpeta real** — que es el único caso donde esto decide algo. Nunca se probó.

**Es real y baratísimo, pero no es por lo que alguien elegiría FileX.**

---

## 5 · OCR en GPU — degradado: ya no es foso · **reabierto por un artefacto de medición**

### Por qué se debilitó

Se formuló cuando parecía exigir Surya, gestión de VRAM y sidecar dedicado. **Se resolvió con un parámetro de una librería MIT que ya estaba instalada**: Docling + RapidOCR con `backend="torch"`, reutilizando el torch existente. **Coste de infraestructura GPU: cero.**

Si un ajuste de configuración cierra el hueco, **no es una ventaja defendible**: cualquiera lo replica en una tarde.

### Lo MEDIDO — la tabla canónica

**Sustituye a la de `bench/gpu-fase2.md` §5.** Fuente: **`bench/ocr-ppp-nativos.md` §3** (21/08/2026, 03:07) — CER % **a ppp nativos**, contra una referencia de 79 caracteres, con la distancia de edición en caracteres entre paréntesis. 296 celdas medidas, **las 296 deterministas** (9 repeticiones, texto idéntico las 9 veces).

| Motor (backbone real) | `patologico` (200 ppp) | `d1` (150) | `d2` (100) | `d3` (100) |
|---|---:|---:|---:|---:|
| **PaddleOCR** (PP-OCRv6 **medium**, `es`) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) | **2,5 % (2)** |
| **Docling + RapidOCR `backend="torch"`** (PP-OCRv6 **small**) | 0,0 % (0) | 0,0 % (0) | 0,0 % (0) | 75,9 % (60) |
| **RapidOCR** aislado (PP-OCRv5 **mobile**, ONNX) | 1,3 % (1) | 0,0 % (0) | 0,0 % (0) | 77,2 % (61) |
| **EasyOCR** (CRAFT + `latin_g2`) | 0,0 % (0) | 0,0 % (0) | **43,0 % (34)** | 54,4 % (43) |

**Rasterizar a ppp nativos y extraer la imagen incrustada sin rasterizar dan el mismo CER en las 16 celdas — MEDIDO.** Extraer no compra precisión: se elige porque es más barato (221 ms frente a 465 ms en el patológico) y porque **no depende de que la cabecera declare la verdad**.

Aceleración y VRAM de la fase 2 siguen valiendo, **pero el presupuesto de VRAM no**: ver el aviso al final de esta sección.

| Motor | Aceleración GPU (fase 2) | VRAM (fase 2, a 200 ppp) |
|---|---:|---:|
| RapidOCR `backend=torch` | 3,5–4,2× | +1 344 MiB |
| PaddleOCR | 8,9–11,7× | +1 486 MiB |
| EasyOCR | 12,4–17,0× | +2 079 MiB |

Dos matices que lo encogen más:

- **La ganancia real es 3,9×** comparando el mejor CPU (RapidOCR, 763 ms) contra el mejor GPU, no los 17× de titular. Un motor lento que se acelera mucho sigue siendo lento.
- ~~**En la dificultad 3 fallan los tres.**~~ **FALSO — corregido el 21/08/2026.**

### La corrección que reabre el hueco 5 — MEDIDA, y no por donde se esperaba

**Qué se creía:** que d3 rompía a los tres motores (57-76 % de CER) y que el OCR acelerado *«hace más rápido el caso fácil, no resuelve el difícil»*.

**Qué se midió** (`bench/ocrmypdf.md` §3.4, confirmado tres veces de forma independiente): `corpus/pdf/escaneado_d2.pdf` y `escaneado_d3.pdf` llevan una imagen incrustada de **647×850 px sobre una página de 465,84×612 pt = 100 ppp nativos**, y **el arnés de la fase 2 rasterizaba a 200 ppp**. Para `patologico_escaneado.pdf` (200 ppp nativos) eso era correcto; para d2 y d3 es **interpolar ×2**, que convierte el grano JPEG q25 en manchas del tamaño de un trazo. **Las marcas publicadas no miden los motores: miden un ×2 de interpolación.**

**A ppp nativos, PaddleOCR resuelve d3 con 2,5 % de CER** — dos errores de un carácter sobre 79. El documento «que nadie resolvía» estaba resuelto.

**Por qué cambió:** el corpus se generó a 100 ppp *a propósito*, como parte de la degradación (§1 de `gpu-fase2.md`), y el arnés fijó 200 ppp como constante para todos los documentos. Nadie cruzó las dos cosas. El control `ctrlppp200` reproduce las marcas antiguas **exactamente, 4 de 4**: la cadena de medición era fiel, el sesgo estaba en la elección de ppp.

#### El aviso de `gpu-fase2.md` hay que matizarlo en dos sentidos, los dos MEDIDOS

`bench/ocr-ppp-nativos.md` §4 mide el artefacto motor por motor (**artefacto = CER a 200 ppp − CER a ppp nativos**; positivo = la cifra vieja exageraba el error):

| Motor | d2 (nativo 100) | **d3 (nativo 100)** | d1 (150) | patológico (200) |
|---|---:|---:|---:|---:|
| **PaddleOCR** | **0,0 pp** | **+73,4 pp** | 0,0 pp | 0,0 pp |
| **RapidOCR** | +1,3 pp | **−11,4 pp** | 0,0 pp | 0,0 pp |
| **EasyOCR** | **0,0 pp** | +5,1 pp | 0,0 pp | 0,0 pp |
| **Docling+RapidOCR torch** | 0,0 pp | **−17,7 pp** | 0,0 pp | 0,0 pp |

1. **El aviso es demasiado amplio en d2.** Dice que «las cuatro columnas de CER de d2 y d3 no son válidas». **Medido: en d2 el artefacto es CERO para PaddleOCR y para EasyOCR, y 1,3 puntos —un carácter— para RapidOCR. Las cifras de d2 publicadas eran correctas.** En particular, **el 43,0 % de EasyOCR en d2 es un fallo real del motor**: no lo causaba el arnés y sigue ahí a ppp nativos y con la imagen extraída.
2. **El aviso se queda corto al decir «los motores»: en d3 el artefacto es de UN SOLO motor.** **Los 73,4 puntos son todos de PaddleOCR.** Para **RapidOCR** y para **Docling+RapidOCR torch**, la cifra vieja de 200 ppp era **su MEJOR resultado, no el peor**: corregir los ppp los **empeora** 11,4 y 17,7 puntos. Y para EasyOCR el artefacto son 5,1 puntos sobre un fallo del 54 %, es decir, irrelevante.

> **La frase correcta es:** *las marcas de d3 no miden la capacidad de los motores frente a un documento degradado porque una de ellas —la de PaddleOCR— está dominada por un ×2 de interpolación; las otras tres medían un fallo que era real y sigue siéndolo.*
>
> Y por tanto **«a ppp nativos siempre es mejor» es FALSO como regla general — MEDIDO** (`ocr-ppp-nativos.md` §0.3). Vale para PaddleOCR (+73,4 pp). Para RapidOCR aislado es al revés, y **Docling+RapidOCR torch tiene la curva invertida**: mejora monótonamente al sobremuestrear, de 75,9 % a **39,2 % en su mejor punto (175 ppp)** y 48,1 % a 300. Nunca resuelve el documento. La contrapartida existe, está acotada, y mueve a esos motores **entre ilegible e ilegible**.

**Una asimetría entre motores que sí es real y sobrevive:** **RapidOCR no resuelve d3 a ninguna resolución.** El sentido se confirma y **el número se corrige — MEDIDO**: su mejor caso es **65,8 % a 200 ppp**, no 53,2 %. El 53,2 % de `bench/ocrmypdf.md` incluía `magick -deskew 40%`, que `ocr-ppp-nativos.md` no aplica en ninguna celda de su barrido de 12 resoluciones más las dos vías de extracción.

**Y la explicación «es límite de modelo, PP-OCRv5 *mobile* frente al *medium* de Paddle» queda PARCIALMENTE REFUTADA — MEDIDO** (`ocr-ppp-nativos.md` §6). La discrepancia entre informes está **resuelta por inspección de los paquetes instalados y del código que elige el checkpoint**: `bench/ocrmypdf.md` §3.4 acierta y `bench/gpu-fase2.md` §5 se equivoca — **PaddleOCR corre PP-OCRv6 medium**, no v5. Pero eso no salva la explicación:

- **Docling + RapidOCR `backend="torch"` corre PP-OCRv6 *small*** —el mismo backbone de generación que PaddleOCR— **y tampoco resuelve d3** (75,9 % a ppp nativos). Hay un v6 **en el lado que falla**.
- *(De paso, `ocrmypdf.md` §3.4 contiene una imprecisión propia que conviene no propagar: dice que el `backend="torch"` de docling cae a PP-OCRv4. Medido, no: docling 2.120.3 resuelve **primero por idioma y solo después por backend**, y PP-OCRv4 solo aparece con `torch` **y** un idioma fuera del conjunto PP-OCRv6, como `latin`.)*

**El límite existe y es grande —2,5 % frente a 39–77 %— pero no es «v5 contra v6».** ~~Los tres candidatos que quedan, todos **PENDIENTES** de aislar: el **tamaño** del modelo, el **idioma del reconocedor** y el **idioma del detector**.~~

### La asimetría de PaddleOCR, RESUELTA — y no era ninguna de las tres · `bench/corpus-d4.md` §7 (21/08/2026)

**Las tres hipótesis quedan refutadas una a una, MEDIDAS:**

| Hipótesis | Veredicto | Evidencia |
|---|---|---|
| **(1) El tamaño del modelo** | **REFUTADA** | El **mismo** checkpoint nominal (PP-OCRv6 **small**) da **3,80 %** en PaddleOCR y **75,95 %** en RapidOCR sobre d3: **72,2 puntos con los mismos pesos.** Y no es monótona: en RapidOCR, `tiny` (43,04) es **mejor** que `small` (75,95) |
| **(2) El idioma del reconocedor** | **VACÍA en PP-OCRv6** | `_get_ocr_model_names` (`paddleocr 3.7.0`, `_pipelines/ocr.py:318`) devuelve **el mismo par de checkpoints** para cualquier idioma del conjunto v6. **`lang="es"` y `lang="en"` dan salida idéntica carácter a carácter** en los tres documentos. *La etiqueta «PP-OCRv6 medium, `es`» de la tabla canónica es correcta pero engañosa: el `es` no hace nada* |
| **(3) El idioma del detector** | **VACÍA en v5/v6** | En PP-OCRv6 el detector es **`multi`, uno solo**. En PP-OCRv5 el catálogo de RapidOCR solo trae `ch_PP-OCRv5_det_*`. La variable **solo existe en v4**, y ahí cambia mucho **sin dirección** (`multi` es el mejor en d3 y el peor en d4) |

> ### La causa real: **RapidOCR normaliza el PP-OCRv6 con `mean=std=0,5` cuando el `inference.yml` que Baidu distribuye CON el modelo declara las estadísticas de ImageNet.** **MEDIDO.**
>
> | | PaddleX (`~/.paddlex/…/PP-OCRv6_small_det/inference.yml`) | RapidOCR (`rapidocr/config.yaml`) |
> |---|---|---|
> | `mean` | **`[0,485, 0,456, 0,406]`** (ImageNet) | **`[0,5, 0,5, 0,5]`** |
> | `std` | **`[0,229, 0,224, 0,225]`** (ImageNet) | **`[0,5, 0,5, 0,5]`** |
> | `thresh` / `box_thresh` / `unclip_ratio` / `max_candidates` | 0,2 / 0,45 / 1,4 / 3000 | 0,3 / 0,5 / 1,6 / 1000 |
>
> **El A/B causal, mismo checkpoint (PP-OCRv6 small) en las cinco filas:**
>
> | configuración | d3 | d4c | d4 |
> |---|---:|---:|---:|
> | defecto de RapidOCR | **75,95** | 29,36 | 36,91 |
> | **solo** post-proceso de PaddleX | 75,95 | 32,21 | 36,58 |
> | **solo** `mean`/`std` de ImageNet (RGB) | **11,39** | 1,01 | 20,13 |
> | **solo** `mean`/`std` de ImageNet (BGR) | **8,86** | 1,01 | 18,79 |
> | **normalización + post-proceso** | **3,80** | **1,17** | **18,62** |
> | *(referencia: PaddleOCR con el mismo v6 small)* | *3,80* | *1,01* | *19,80* |
>
> **La normalización sola vale 64,6 puntos de CER (75,95 → 11,39). El post-proceso solo vale 0,0. Los dos juntos reproducen la cifra de PaddleOCR exactamente: 3,80 %.**
>
> **Y el recuento de cajas convierte el argumento en medida:** el detector de RapidOCR con el defecto encuentra **1 renglón de 3** en d3 y **8 de 12** en d4; con la normalización de PaddleX, **3 de 3 y 12 de 12**. **No es que lea mal: es que no ve.**

**Cuatro consecuencias, y la tercera es la que cambia el plan:**

1. **La explicación de este documento («es límite de modelo, v5 *mobile* frente al *medium*») y su corrección parcial de `ocr-ppp-nativos.md` §6 («no es la generación; quizá el tamaño») quedan las dos SUPERADAS.** No es ni la generación, ni el tamaño, ni el idioma: **es un defecto de configuración de RapidOCR 3.9.2 con la familia PP-OCRv6.**
2. **Docling hereda el defecto.** `Docling + RapidOCR backend="torch"` —la ruta que el plan de FileX da por buena— construye RapidOCR con los parámetros por defecto: por eso da 75,9 % en d3. **Es corregible desde fuera, sin parchear el paquete.**
3. **Es la corrección más barata medida en el proyecto: seis números por 72,2 puntos de CER.** Con ella, **RapidOCR ONNX cubre el corpus entero** — `0,00 / 0,00 / 0,00 / 3,80 / 18,62 %` sobre patológico, d1, d2, d3 y d4 —, **gana a PaddleOCR en cuatro de las cinco filas**, arranca en **3,7 s** en vez de 18,4 y **funciona en CPU**. *(La excepción es d3, donde PaddleOCR gana por **1,27 puntos** — un carácter sobre 79. No es base para una regla de conmutación.)*
4. **Deja una regla general, no un parche:** *cuando el motor y el modelo vienen de proyectos distintos, hay que comprobar que el preprocesado que aplica el motor es el que declara el fichero de configuración del modelo.* Es el mismo tipo de fallo que `onnxruntime-gpu` cayendo a CPU en silencio: **nada da error, solo empeora.**

**Un hallazgo colateral que sí afecta a lo que FileX usa hoy:** `bench/scripts/ocr_motor.py` fija **`LangRec.CH`** — la línea base del proyecto **lee castellano con un reconocedor de chino**. Con el detector fijo y PP-OCRv5, el reconocedor chino cuesta **19,0 puntos en d3 y 23,7 en d4** frente al latino (25,32 / 40,94 contra 6,33 / 17,28). **MEDIDO.** *(Pero no explica la asimetría: dentro de RapidOCR, pasar de `ch` a `latin` mueve 1,3 puntos en d3 y el fallo sigue al 76 %.)*

~~**PENDIENTE:** validar la corrección **fuera de este corpus**.~~ **VALIDADA el 21/08 a las 14:00, y con un lado malo que hay que llevar pegado — ver el bloque siguiente.**

> ### La normalización, VALIDADA — pero **solo sobre `PP-OCRv6 small`** · `bench/ppp-y-normalizacion.md` §3 (21/08/2026, 14:00)
>
> **El mecanismo, con fichero y línea, listo para reportar aguas arriba:** `rapidocr/config.yaml:143-149` fija `Det.mean` y `Det.std` a **`0,5/0,5/0,5`** (y `thresh` 0,3 · `box_thresh` 0,5 · `max_candidates` 1 000 · `unclip_ratio` 1,6) **en un solo bloque, sin condicionar por `ocr_version`**; se lee en `ch_ppocr_det/main.py:33-34` y `:79`, y se aplica en `ch_ppocr_det/utils.py:71` (`(img * scale - mean) / std`). Con `scale = 1/255` la entrada queda en `[-1, 1]` uniforme cuando la red se entrenó esperando `[-2,1, +2,6]` con desviaciones distintas por canal. **No hay aviso, ni comprobación, ni error.**
>
> **Y el defecto es de TODA la familia, no de PP-OCRv6: los OCHO `inference.yml` que Baidu distribuye —de `PP-OCRv3_mobile_det` a `PP-OCRv6_medium_det`— declaran ImageNet, y RapidOCR aplica 0,5 a los ocho. Lo que es de v6 no es el defecto: es el DAÑO que hace.**
>
> **La validación, MEDIDA sobre 15 documentos, n=9, GPU, incluidas cuatro rasterizaciones del patrón oro** (`bench/salidas-referencia/pdf/`, leídas y no tocadas):
>
> | efecto de la corrección sobre `PP-OCRv6 small` | celdas | mayor magnitud |
> |---|---:|---|
> | **mejora** | **6** | `d3` **−72,15** (75,95 → 3,80) |
> | empate exacto | **9** | — |
> | **empeora** | **0** | — |
>
> **Y lo que el encargo pedía buscar —dónde EMPEORA— se buscó y se encontró:**
>
> | Caso | Delta | Contexto |
> |---|---:|---|
> | **`PP-OCRv4 mobile` sobre `tipico_texto` del patrón oro** | **+42,50** (0,83 → **43,33 %**) | un documento **limpio**, rasterizado a 150 ppp desde un PDF con capa de texto |
> | `PP-OCRv6 tiny` sobre `d3` | **+16,45** (43,04 → 59,49) | y **+13,60** en `d4c` |
> | `PP-OCRv5 mobile` | 4 de 15 celdas peores (n=9), hasta **+8,89** | la cifra buena de `d3` (77,22 → 54,43) es cierta y **no era toda la historia** |
>
> **Cribado completo de 7 detectores × 4 variantes: 18 mejoras, 12 empates y 12 EMPEORAMIENTOS sobre 42 celdas.** Solo `PP-OCRv6 small` sale con **3 mejor / 0 peor**.
>
> **Tres lecturas, y ninguna era la esperada:**
>
> 1. **El desajuste es universal; el daño no.** Los ocho modelos declaran ImageNet y reciben 0,5, pero **solo `PP-OCRv6 small` se hunde por ello**. La hipótesis obvia —«un modelo entrenado con ImageNet se rompe si le das 0,5»— **es falsa para 7 de los 8**: la robustez a la normalización varía por checkpoint y **no se puede predecir del fichero de configuración**.
> 2. **«Corregir el desajuste» no es lo mismo que «mejorar el motor».** En `PP-OCRv4 mobile` la configuración *correcta según el fabricante* da **peor** resultado que la incorrecta en 4 de 6 documentos. **Devolverle al modelo lo que su `inference.yml` declara no garantiza nada: hay que medirlo checkpoint por checkpoint.**
> 3. **Las dos mitades no son separables ni monótonas.** Sobre `v6 medium` el **post-proceso solo** da `d4c` = **0,84 %**, mejor que la corrección completa (9,56) y que el defecto (14,09); sobre `v6 small` el post-proceso solo **no vale nada** y la normalización sola vale 64,56 puntos. **La receta de seis números es la correcta para `small` y no lo es para `medium`.**
>
> **La forma en que debe entrar en FileX es una tabla POR CHECKPOINT, no un ajuste global del motor:** `("PP-OCRv6","small")` → los seis parámetros; **todos los demás → `None`, dejar el defecto**, con el motivo medido anotado en cada línea.
>
> **Docling: 7 de 7, cuatro mejoras grandes, cero regresiones, coste en tiempo NULO.** La corrección se pasa por **`RapidOcrOptions.rapidocr_params`** —el punto de extensión público, aplicado en `models/stages/ocr/rapid_ocr_model.py:445-448`— **sin parchear el paquete**: `d3` **75,95 → 5,06** (−70,89), `d4` 36,91 → 19,63, `d4c` 22,99 → 8,39, `d4f` 22,15 → 0,67, y tres empates exactos en 0,00 %. La mediana de tiempo se mueve entre −3,2 % y +5,8 %, **dentro del ruido**.
>
> **Una comprobación que el parche debe llevar, y es la que hizo falta aquí para saber que la corrección llegaba:** leer del objeto ya construido (`lector.text_det.mean` / `.std`) y compararlo con lo pedido. **Sin eso, «he puesto ImageNet» es una intención, no un hecho** — el mismo patrón que `session.get_providers()` frente a `get_device()`.
>
> **Y una nota honesta sobre el arnés:** la sonda de la primera versión devolvió `"?"` en cuatro tandas porque buscaba `mean`/`std` en `preprocess_op`, que **es `None` hasta la primera llamada**; los valores viven en el propio `TextDetector`. Corregido y verificado.

> ### B11 cambia de contenido: no es «añadir R6» — es **cambiar de checkpoint Y añadir R6**
>
> `bench/scripts/ocr_motor.py` es arnés compartido y **no se ha tocado**: el parche queda **PROPUESTO, NO APLICADO**. Pero su contenido ya no es el que se escribió: **sobre el `PP-OCRv5 mobile` que la línea base usa hoy, la corrección de normalización NO es recomendable** (4 de 15 celdas peores). **El parche tiene que ser: pasar a `PP-OCRv6 small` —el único checkpoint con 0 regresiones— y aplicar R6 ahí.**
>
> **Saldo medido del parche completo (v5 mobile por defecto → v6 small + R6), y hay que declararlo entero: 7 mejor, 2 igual, 2 PEOR.**
>
> | documento | hoy | con el parche | delta |
> |---|---:|---:|---:|
> | `escaneado_d3` | 77,22 | **3,80** | **−73,42** |
> | `escaneado_d4` | 41,78 | **18,62** | **−23,16** |
> | `escaneado_d4c` | 15,60 | **1,17** | **−14,43** |
> | `tipico_texto` (oro, JPEG) | 3,33 | 0,83 | −2,50 |
> | `escaneado_d4a` | 1,51 | **7,38** | **+5,87** |
> | `escaneado_d4f` | 6,04 | 7,05 | +1,01 |
>
> **Las dos regresiones son del CAMBIO DE CHECKPOINT, no de R6**, y hay que declararlas al aplicarlo: **no es una mejora gratis en todas las filas.**
>
> *(Y la cifra de `Rec.lang_type = latin` que justificaba la otra mitad del parche **no se ha reverificado** en este arnés: se cita de `corpus-d4.md` §7.2. **En PP-OCRv6 la variable no existe**, así que solo importa si se decide seguir en PP-OCRv5.)*

**Y la conclusión no es la que este documento anticipaba.** Aquí se escribió: *«si el preprocesado rescata la dificultad 3, la conclusión no será "añadir OCRmyPDF" sino "añadir una etapa de preprocesado antes de cualquier OCR"»*. **No es eso, y es mejor:**

> **FileX debe leer los ppp reales de la imagen incrustada y por defecto NO sobremuestrear, o extraerla sin rasterizar.**

**La recomendación se sostiene, con un matiz medido: no es «cuanto menos, mejor». Hay óptimo con meseta, y la regla necesita suelo además de techo** (`ocr-ppp-nativos.md` §9, R1):

```
ppp_nativos = ancho_imagen_px / (ancho_pagina_pt / 72)
ppp_ocr     = clamp(ppp_nativos, 100, ppp_nativos * 1,4)
```

- **Techo ×1,4, y es un acantilado, no una pendiente — MEDIDO.** PaddleOCR mantiene ≤5,1 % de CER en d3 **desde 75 hasta 140 ppp** y a **160 ppp cae de golpe a 75,9 %**, su suelo de fallo. **Entre ×1,4 y ×1,6 se pierden 72 puntos de CER.** ×1,4 es el último punto medido dentro de la meseta.
- **Suelo 100 ppp — MEDIDO.** A 75 ppp **RapidOCR se rompe en d2** (0,0 % → 44,3 %) y **EasyOCR se degrada en d1** (0,0 % → 12,7 %). Submuestrear hace daño **antes** de que sobremuestrear lo haga.

> ### **El techo RELATIVO ×1,4 no se transfiere fuera del documento donde se midió — REFUTADO PARCIALMENTE** (`bench/corpus-d4.md` §8, 21/08/2026)
>
> El techo se justificó con una meseta medida **sobre d3, un documento de 100 ppp nativos**. Con `escaneado_d4` (**200 ppp nativos**) se puede probar por primera vez desde otro punto de partida — **MEDIDO**:
>
> | motor | `d4` a 200 ppp (nativo) | `d4` a **280 ppp (= ×1,4)** | efecto del techo |
> |---|---:|---:|---|
> | PaddleOCR PP-OCRv6 medium | **19,30 %** | **36,24 %** | **+16,9 puntos, PEOR** |
> | RapidOCR PP-OCRv6 small **corregido** | **18,62 %** | 28,86 % | **+10,2 puntos, peor** |
> | RapidOCR PP-OCRv5 mobile (defecto) | 41,78 % | 41,95 % | +0,2, indiferente |
>
> **Aplicar el techo ×1,4 sobre un original de 200 ppp empeora al mejor motor en 16,9 puntos de CER.** La meseta era una propiedad del par (documento, motor), no una constante: **lo que decide no es el factor sobre el nativo sino el tamaño en píxeles que llega al detector** — `d3` a ×1,4 son 907 px de ancho, `d4` a ×1,4 son **1 812**. Son regímenes distintos y no hay razón para que compartan multiplicador. El techo relativo era, en parte, **un artefacto de que todo el corpus viejo fuera de 100–200 ppp**.
>
> **Propuesta, y hay que leerla como lo que es — PENDIENTE de validar:**
>
> ```
> ppp_ocr = clamp(ppp_nativos, 100, 200)      # techo ABSOLUTO, no relativo
> ```
>
> **Un techo absoluto de 200 no viola ninguna medida existente y el relativo ×1,4 sí:** d2 y d3 (100 nativos) toleran hasta 140; `d4` (200 nativos) se degrada ya a 280; y el patológico, que es de 200 nativos, siempre fue el mejor caso. **El suelo de 100 se mantiene sin cambios: sigue siendo lo medido.**
>
> **PENDIENTE explícito:** **no se ha barrido la curva de ppp sobre `d4`** como se hizo sobre `d3`. Faltan los puntos entre 200 y 280 y por encima de 280. Hasta que se barra, `clamp(nativos, 100, 200)` es **la propuesta mejor apoyada, no una regla medida**.
>
> **Y hay confirmación de R1 desde un quinto motor completamente distinto** (`bench/verificador-ghostscript.md` §5.3, 60 celdas): con el OCR de Ghostscript, **en d3 sobremuestrear es monótonamente catastrófico** —de **105,1 %** a 75 ppp hasta **834,2 %** a 300, con `spa`—; **no hay acantilado, hay una rampa**. En d1 y d2, en cambio, **la curva es plana en 0,0 % de 100 a 300 ppp**. **El acantilado ×1,4/×1,6 es de PaddleOCR, no de la resolución; el suelo de 75 ppp es de todos.**

> ### Y AHORA EL TECHO ABSOLUTO TAMBIÉN QUEDA REFUTADO. **Las dos versiones de esta regla estaban mal** — `bench/ppp-y-normalizacion.md` §2 (21/08/2026, 14:00)
>
> Se barrieron **17 puntos de ppp** sobre `escaneado_d4` con siete configuraciones de motor, más `d3`, `d4c`, `d4f` y `patologico_escaneado`, con mediana de n=9, GPU y dispositivo fijado. **Las tres unidades candidatas caen una a una:**
>
> | candidata | qué predeciría | qué se mide | veredicto |
> |---|---|---|---|
> | **ppp absolutos** (techo 200) | todos se rompen al pasar de 200 ppp | `d3` se rompe a **160**; `d4c`, `d4f` y `patológico` **no se rompen a 400** | **REFUTADA** |
> | **factor sobre el nativo** (×1,4) | todos se rompen al mismo factor | PaddleOCR se rompe en `d4` a ×1,4, en `d3` a ×1,6 y **nunca** en `d4c` (×1,6) ni `d4f` (×1,67) | **REFUTADA** |
> | **anchura en píxeles** | todos se rompen a la misma anchura | `d3` se rompe a **1 035 px**; `d4c` **no** se rompe a **2 070 px** | **REFUTADA** |
>
> #### El experimento que lo decide: mismos píxeles, distinta página — 24 celdas
>
> Se extrajo el JPEG incrustado de `escaneado_d4.pdf` (100 545 B, 1 294×1 716) y se reempaquetó en **tres PDF de 100, 200 y 400 ppp nativos** con la misma orden del generador del corpus. Es decir: **el mismo mapa de bits, tres densidades declaradas.**
>
> | | PaddleOCR | RapidOCR v6 small + R6 |
> |---|---|---|
> | **A los mismos 200 ppp**, según la página | **19,13 / 19,63 / 36,24 %** | **30,70 / 18,62 / 30,70 %** |
> | **A los mismos píxeles** (647 / 1 294 / 1 812 / 2 588 px) | **coinciden a la centésima, 12 parejas exactas** | **ídem** |
>
> **17,1 puntos de diferencia al mismo número de ppp, con el mismo documento dentro.** Y los ficheros de entrada **no** son binariamente idénticos entre geometrías —Ghostscript rasteriza cada densidad por separado, los `sha256` difieren—, lo que hace la coincidencia **más** fuerte, no menos.
>
> > **Los ppp no son una propiedad del documento que el OCR pueda usar: son una división entre los píxeles que hay y el tamaño que el PDF dice que tiene la página. Una regla escrita en ppp está escrita en la unidad equivocada.**
>
> #### El defecto propio del techo absoluto, que es lo que lo remata
>
> **(a) Su techo solo actúa BAJANDO, y bajar cuesta.** Con `nativos ≤ 200` la expresión devuelve los nativos y el techo no hace nada; solo interviene con originales de más de 200 ppp, a los que **reduce**. Reducir `d4` de 200 a 100 ppp sube RapidOCR+R6 de **18,62 % a 30,70 %: +12,08 puntos**. **`clamp(nativos, 100, 200)` es, en la práctica, una regla para degradar los originales buenos.**
>
> **(b) La evidencia que lo motivó es un caso que la regla anterior nunca produce.** Se midió `d4` a 280 ppp y se concluyó que el techo ×1,4 empeoraba 16,9 puntos. Pero `clamp(200, 100, 200×1,4) = clamp(200, 100, 280) = **200**`: **la regla relativa jamás pide 280 ppp para ese documento.** La cifra de 36,24 % es correcta y está reproducida aquí, **pero no es evidencia contra el techo relativo. El techo absoluto se escribió para arreglar un problema que la regla anterior no podía causar.**
>
> #### La respuesta es la cuarta candidata: **la regla es POR MOTOR, y no existe una regla global**
>
> Mismo documento (`escaneado_d4`), mismas 17 rasterizaciones, mismo evaluador, mismo dispositivo — **dónde cae el mínimo de cada motor:**
>
> | motor / configuración | CER a ppp nativos | **mejor CER** | **a qué factor** |
> |---|---:|---:|---:|
> | Docling + RapidOCR torch **+R6** | 19,63 | **18,12** | **×0,88** |
> | RapidOCR v6 small **+R6** (ONNX) | **18,62** | **18,62** | **×1,00** |
> | PaddleOCR v6 medium | 19,30 | **13,09** | **×1,25** |
> | RapidOCR v6 small (defecto) | 36,91 | 32,72 | ×1,25 |
> | RapidOCR v5 mobile (defecto) | 41,78 | 40,44 | ×0,50 *(curva plana)* |
> | Docling + RapidOCR torch (defecto) | 36,91 | **32,89** | **×1,60** |
> | EasyOCR | 61,41 | 58,39 | **×1,80** |
>
> **Siete configuraciones sobre el mismo documento, con óptimos entre ×0,50 y ×1,80.** Y no es solo dónde está el óptimo, **es dónde está el precipicio**: sobre `escaneado_d3`, a **×1,4**, PaddleOCR sigue bien (**3,80 %**) y **RapidOCR+R6 se cae (2,53 → 46,84 %)**. **Un orquestador que elija los ppp sin saber qué motor los va a consumir está tirando una moneda de 43 puntos.**
>
> **El mecanismo está sondeado en ejecución y explica por qué tenía que ser así:** cada motor lleva su reescalado interno cableado con constantes propias. **`Global.max_side_len: 2000` (`rapidocr/config.yaml:10`, aplicado en `main.py:286` vía `utils/process_img.py:113-114`) hace que sobre `d4`, de 233 ppp en adelante, el array que entra a la red sea LITERALMENTE EL MISMO** (1 504×1 984 px): su «tolerancia a los ppp altos» no es tolerancia, **es que no los ve**, y rasterizar por encima de ahí es trabajo pagado a cambio de nada. **PaddleOCR no recorta** (`limit_side_len=64, limit_type='min'`) y ve los 2 588 px. **La función que lleva de «ppp de rasterizado» a «píxeles que ve la red» es distinta en cada motor**, así que pedirle a una sola constante que sirva para todos es pedirle que compense tres reescalados a la vez.
>
> > **Y el modo en que se descubrió es la regla de la casa confirmada otra vez:** leyendo el código de PaddleX se deduce **lo contrario** —`_TEXT_DET_MAX_LIMIT_MODELS` lista los ocho detectores con `limit_type='max'`, 960 px— y **es falso para la ruta que usa `paddleocr` 3.7.0**. La sonda lo desmiente. **Su propio informe lo deja escrito como error cometido**, porque es exactamente lo que la regla *«sondear capacidades en ejecución, no deducirlas»* existe para evitar.
>
> #### La regla vigente, y dónde vive
>
> ```
> # La eleccion de ppp es DEL ADAPTADOR DEL MOTOR, no del orquestador.
> ppp_nativos = ancho_imagen_px / (ancho_pagina_pt / 72)     # lo calcula el orquestador
> ppp_ocr     = min(max(ppp_nativos, 100), ppp_nativos * 1.25) * k_motor
> #
> #   k MEDIDO sobre escaneado_d4:
> #     PaddleOCR v6 medium ......... 1,25      RapidOCR v6 small + R6 ...... 1,00
> #     Docling+RapidOCR + R6 ....... 1,00      EasyOCR ..................... 1,00
> #     Tesseract ................... 1,50      [P2, n=1, PENDIENTE de barrer]
> #   Suelo: subir hacia 100 ppp, NUNCA mas de x1,25 sobre el nativo.
> #   Techo de CALIDAD: no existe uno global. El de cada motor esta en su k.
> #   Techo de COSTE: el tope interno del motor (RapidOCR 2 000 px), no 200 ppp.
> ```
>
> **La subida máxima baja de ×1,4 a ×1,25**, y está medida: **×1,25 es seguro en 6 de las 8 parejas (documento, motor) y ×1,4 solo en 4.** *(Un original de 80 ppp llevado a 100 es ×1,25: justo dentro. Uno de 72 es ×1,39: justo fuera.)*
>
> **Con `k = 1,00` por defecto la regla sigue siendo segura:** en las siete configuraciones medidas **el nativo nunca es el peor punto del barrido**, y en cinco de siete está a menos de 1,7 puntos del óptimo. **Lo que el `k` compra es el resto**: los 6,2 puntos de PaddleOCR y los **32 puntos de Tesseract sobre `escaneado_d2`**.
>
> #### La consecuencia de arquitectura, que es lo que hay que llevarse
>
> > **Si la regla es por motor, la elección de ppp pertenece al ADAPTADOR DE CADA MOTOR, no al orquestador.** Hoy `clamp(...)` está escrita como **regla global** en `CLAUDE.md` y en `PLAN-ORQUESTADOR.md` §4.5: **está en el sitio equivocado del diseño.** No es una constante del dominio, es un parámetro del motor, del mismo rango que `Det.mean` o `OcrOptions.scale`. **Si se queda en el orquestador, cada motor nuevo hereda en silencio los ppp que le convenían a otro** — que es literalmente lo que le pasa hoy a Tesseract.
>
> #### Lo que SÍ queda como regla global, y es de presupuesto, no de precisión — MEDIDO
>
> | motor | base MiB | **pico MiB** (barrido hasta 400 ppp, **una página**) | coste propio | ¿reventó? |
> |---|---:|---:|---:|---|
> | **EasyOCR** | 2 007 | **12 037 de 12 288** | +10 030 | no, **por 251 MiB** |
> | **PaddleOCR v6 medium** | 1 946 | **11 942 de 12 288** | +9 996 | no, **por 346 MiB** |
> | RapidOCR v6 small + R6 (ONNX) | 991 | 4 439 | +3 448 | no |
>
> **Los dos motores caros terminaron a menos de 350 MiB de agotar la tarjeta sin dar ningún error.** **Hay que poner ALGÚN límite: el límite existe por presupuesto de VRAM aunque no exista por precisión.** Y **la imagen mental de «EasyOCR es el caro» es correcta a ppp nativos y falsa en cuanto se sobremuestrea**: PaddleOCR llega al mismo sitio. **RapidOCR corregido cuesta un tercio y su curva es plana por encima de 233 ppp por construcción**: es el único con un techo de VRAM acotado por el propio motor. **El coste de no aplicar la regla son 10 GB.**
>
> #### Y tres correcciones menores que van con esto
>
> - **El «acantilado» no es de la resolución: es del margen que le queda al motor.** Sobre `patologico_escaneado`, PaddleOCR y RapidOCR+R6 dan **0,00 % en los siete puntos de 100 a 400 ppp** (×0,5 a ×2,0): **catorce celdas a cero.** **El techo de ppp solo existe en los documentos que ya están cerca de fallar.**
> - **Sobre `d4` hay una banda, no un acantilado.** Seis puntos nuevos entre 250 y 280 ppp (15,10 / 23,66 / 16,44 / 13,09 / 21,31) **oscilan dentro de la misma banda que 100-250**; la caída a 36,24 ocurre en 275 → 280 **y 300 la deshace parcialmente** (25,17 con 11 cajas). **Todo el efecto vive en el bloque de 7 pt**: el de 11 pt se queda entre 0,64 y 2,24 % en los diecisiete puntos. **Un documento sin letra pequeña no tiene techo de ppp que medir.**
> - **Medir el techo de ppp con un motor mal configurado da «no hay techo».** RapidOCR v5 mobile y v6 small **sin** corregir son planos en los 17 puntos, siempre con 8 cajas: **no es robustez, es que su detector nunca encuentra el bloque pequeño**, así que no hay nada que la resolución pueda estropear.
> - **`OcrOptions.scale` sigue siendo obligatorio fijarlo, pero «fijarlo a los ppp nativos» era la parte equivocada de la recomendación.** Su defecto de 3,0 (216 ppp) es **indiferente en cuatro de los cinco escaneados y MEJOR en `d3`: 58,23 % frente al 75,95 % de rasterizar a nativos, −17,72 puntos.** Es el mismo fenómeno: para ese motor, `k > 1`.
- **No usar el `dpi` declarado del objeto de imagen sin comprobarlo.** Aquí coincidía con el calculado en los cuatro documentos, pero el cálculo desde la geometría de la página no depende de que el productor del PDF escribiera bien la cabecera.
- **PENDIENTE:** páginas con varias imágenes, imágenes que no ocupan la página entera, PDF con texto vectorial mezclado con escaneo, y PDF sin ninguna imagen incrustada (donde no hay «ppp nativos» y hace falta otro criterio).

Es **una decisión, no una etapa**: no añade binario, ni dependencia, ni pasada de imagen. Cuesta **menos** CPU y **menos** VRAM que lo que se hacía. Y su efecto es de otro orden que el del preprocesado: 75,9 % → **2,5 %** de CER, frente al 20,3 % del mejor preprocesado real medido (`magick -deskew 40%`), que entra como **red de seguridad** para cuando los ppp declarados mienten, no como fuente de la ganancia.

**OCRmyPDF queda descartado como preprocesador — MEDIDO.** De las cuatro banderas que motivaban la prueba: `--remove-background` lanza `NotImplementedError`, `--deskew` es inerte (devuelve `0.0000°` **incluso sobre una página girada 5° exactos**), `--clean-final` destruye el texto si se le dan sus filtros reales, y `--rotate-pages` cuesta ×3 para decidir «no change». Comprobado pixel a pixel: **su salida es bit a bit idéntica a no usarlo**. Peor: **atravesar su ciclo degrada** — RapidOCR en d2 pasa de 1,3 % a **44,3 %** de CER solo por el viaje rasterizar→JPEG q95→Ghostscript→PDF/A. Sigue siendo interesante como **empaquetador de PDF/A con capa de texto**, que es otra cosa y no toca este hueco.

**Dato colateral para el sidecar (hito 6):** **PaddleOCR picó a 12 025 de 12 288 MiB** con imágenes a 600 ppp, a 263 MiB de agotar la tarjeta. Sobremuestrear no solo empeora la precisión: **consume la VRAM que el presupuesto del sidecar no tiene**.

> **Y el aviso se amplía — MEDIDO** (`ocr-ppp-nativos.md` §7.2): **EasyOCR llega a 11 877 de 12 288 MiB —a 411 MiB de agotar la tarjeta— con imágenes a solo 300 ppp**, la mitad de resolución, y con un documento de **una sola página**.
>
> | Motor | pico con la imagen extraída / a ppp nativos | **pico a 300 ppp** | crecimiento por sobremuestrear |
> |---|---:|---:|---:|
> | RapidOCR | 3 424 MiB | 3 424 MiB | **+0 MiB** |
> | PaddleOCR | 3 762 MiB | 7 442 MiB | +3 680 MiB |
> | EasyOCR | 5 026 MiB | **11 877 MiB** | **+6 851 MiB** |
>
> **El presupuesto de VRAM del sidecar no se puede fijar por motor: hay que fijarlo por motor Y por resolución de entrada.** El «EasyOCR = +2 079 MiB» de la fase 2 (medido a 200 ppp) **subestima el peor caso casi 5×**. Y **RapidOCR es el único insensible a los ppp en VRAM** (+0 MiB entre la imagen extraída y 300 ppp): su ruta ONNX trocea la página y no crece con ella. Es su ventaja real y no aparece en ninguna tabla anterior.

### Lo que queda

Un hueco de **producto**, no técnico: SnapOtter lo bloquea activamente (`ocr-runtime-dispatcher.ts:1033` lanza excepción si `device !== "cpu"`) y OCRmyPDF depende de Tesseract. **Nadie lo ofrece, pero cualquiera podría.**

**Y hay una vía de OCR en CPU que FileX obtiene casi gratis — MEDIDO:** **Ghostscript 10.07 lleva Tesseract y Leptonica compilados dentro de `gsdll64.dll`** (122 apariciones de `tesseract`, 9 de `leptonica`), lo que habilita `-sDEVICE=ocr`, `hocr` y `pdfocr8/24/32` **sin invocar ningún binario externo**. **Pero no trae los datos de idioma**: hay que distribuir `eng.traineddata` (y `spa`) y fijar `TESSDATA_PREFIX` desde el orquestador. Ver `PLAN-ORQUESTADOR.md` §2. **OCRmyPDF no puede aprovecharlo: necesita el binario `tesseract` de verdad.**

#### Esa vía está EJERCITADA — `bench/verificador-ghostscript.md` §5 (21/08/2026)

**CER a ppp nativos, con el mismo `bench/scripts/ocr_eval.py` que los demás motores, para que la cifra entre en la tabla canónica — MEDIDO:**

| Motor | patológico (200) | d1 (150) | d2 (100) | d3 (100) |
|---|---:|---:|---:|---:|
| **gs `-sDEVICE=ocr`, `spa` · CPU** | **0,0 %** | **0,0 %** | **0,0 %** | **165,8 %** |
| gs `-sDEVICE=ocr`, `eng` · CPU | 0,0 % | 0,0 % | 1,3 % | 245,6 % |
| gs `-sDEVICE=ocr`, `spa+eng` · CPU | 0,0 % | 0,0 % | 0,0 % | 216,5 % |

1. **En los tres documentos que la ruta de GPU resuelve, el OCR de CPU los resuelve igual: 0,0 %.** Sin tarjeta, sin venv, sin descargar un modelo. **VRAM: 0 MiB** — es una columna entera del presupuesto del sidecar que desaparece.
2. **`spa` bate a `eng` donde el documento es marginal** (en d2 `eng` confunde «solo» con «golo»); `spa+eng` empata con `spa`: **combinar no aporta**.
3. **En d3 no falla: ALUCINA.** El CER pasa de 100 % porque la salida es **más larga que la referencia y es ruido**: `'a O | o — | o a a . a | oO a ENS CANEADO EE ES'`. **Es un modo de fallo cualitativamente distinto** al de los tres motores de GPU que también fallan en d3, que devuelven **poco** texto (<30 caracteres). **Un orquestador que solo mire «¿hay texto?» clasificaría este fallo como éxito.**
4. **La carga en frío no se compara: no existe.** Los motores de GPU cuestan **3,4–17,3 s**; Ghostscript, **122 ms** (cargar `gsdll64.dll`, 27,7 MB). Para una CLI que convierte un fichero y termina, **la carga en frío ES el coste**: la diferencia es de **28× a 142×** a favor de la CPU. En bruto está en el mismo orden de magnitud que la GPU (×1,6–2,5 más lento que el mejor); **descontando el suelo de arranque, en d1 y d2 es más rápido que cualquiera** (~37 ms de OCR real en d2).
5. **El tiempo es, por sí mismo, una señal de degradación:** d3 cuesta **4,5× lo que d2** a la misma resolución (1 031 ms frente a 226 ms) porque alucinar es caro — el reconocedor emite muchas más cajas. **PENDIENTE** de calibrar.

**La arista de reparación funciona, y es de DOS saltos, no de uno — MEDIDO:**

| Documento | 1 salto: `docxwrite` directo | 2 saltos: `pdfocr8` → `docxwrite` | CER | tiempo total |
|---|---:|---:|---:|---:|
| `patologico_escaneado` | **2 chars — DESTRUIDO** | **99 chars** | **0,0 %** | 1 255 ms |
| `escaneado_d1` | **2 chars — DESTRUIDO** | 102 chars | **0,0 %** | 549 ms |
| `escaneado_d2` | **2 chars — DESTRUIDO** | 102 chars | **0,0 %** | 438 ms |
| `escaneado_d3` | **2 chars — DESTRUIDO** | 173 chars | **119,0 %** | 1 225 ms |

**Sí en 3 de los 4 documentos, con 0,0 % de CER y por debajo de 1,3 s.** El camino de un salto entrega un `.docx` **sin una sola línea del documento** —2 caracteres, por debajo del umbral P6, que es exactamente el caso para el que se calibró—. **El criterio de aceptación del hito 1 se cumple si y solo si el grafo sabe INSERTAR el paso de OCR.**

> ### Y el hallazgo incómodo: **el verificador declara `OK` la reparación alucinada** — MEDIDO (§5.8)
>
> Pasando el PDF reparado de `escaneado_d3` por el propio verificador: **`CONTRATO OK` · `FIDELIDAD OK`**, con `[P6 informativo] texto extraído: 75 caracteres imprimibles (umbral 10)` y `[P5 informativo] la entrada no tiene capa de texto: no se exige texto en la salida`. **Los 75 caracteres son ruido puro.** La cadena es **correcta regla a regla y equivocada como conjunto**:
>
> - **P5** dice *«no es un fallo salvo que se pidiera OCR»* — **y el `pedido` no lleva ese dato.**
> - **P6** exige ≥10 caracteres imprimibles, umbral calibrado contra la basura de 1-3 caracteres de `txtwrite`. **75 caracteres de ruido lo superan siete veces.**
>
> **El umbral de P6 protege contra la basura de `txtwrite`, no contra la alucinación de un OCR. Son dos fallos distintos y el proyecto solo tenía medido el primero.**
>
> **Hay señal barata que los separa, y está en proceso:**
>
> | Capa de texto | tokens | **longitud media** | **% de tokens de 1 letra** | ¿pasa P6? |
> |---|---:|---:|---:|---|
> | `patologico` (0,0 % CER) | 12 | 5,67 | **0,0 %** | sí |
> | `escaneado_d1` (0,0 %) | 12 | 5,67 | **0,0 %** | sí |
> | `escaneado_d2` (1,3 %) | 11 | 6,18 | **0,0 %** | sí |
> | **`escaneado_d3` (93,7 %)** | 34 | **2,03** | **61,8 %** | **sí** |
> | *control:* `tipico_texto.pdf`, capa **real** | 24 | 4,04 | 33,3 % | sí |
>
> **Propuesta `P9`, marcada como lo que es:** *«si se pidió OCR, la capa resultante debe tener longitud media de token ≥ 3,0 y menos del 50 % de tokens de una sola letra»*. Separa los cinco casos, **cuesta microsegundos y no lanza ningún proceso**. **Está calibrada sobre 5 puntos: es una propuesta, NO una regla validada** — el control es deliberadamente el caso difícil (un PDF con tabla llega al 33,3 %), así que **el margen entre 33,3 % y 61,8 % es todo lo que hay, y no es enorme. PENDIENTE de validar contra un corpus de capas OCR reales.**
>
> **Y la corrección que no hace falta calibrar: el `pedido` tiene que llevar `ocr: true`.** Sin ese dato P5 no puede trabajar. Es, otra vez, el punto 4 del contrato: **pedido frente a obtenido.**

> ### `P9` se validó y quedó REFUTADA — `bench/contrato-quinto-punto.md` §6 (21/08/2026, 14:00)
>
> Se validó contra **32 capas OCR reales** —8 documentos × 2 idiomas (`spa`, `eng`) × 2 resoluciones (nativa y el doble), producidas con `gs -sDEVICE=pdfocr8`; sobremuestrear ×2 es **la forma barata de fabricar alucinaciones de verdad**— y contra **19 capas de texto legítimo** (8 reales del repositorio y 10 fabricadas cortas: una tabla, una fórmula, iniciales, una factura, un titular).
>
> | Verdad de referencia: CER con tildes > 50 % = ruido | Ruido | Bueno |
> |---|---:|---:|
> | P9 dice «alucinación» | **1** | 0 |
> | P9 dice «ok» | **11** | 20 |
>
> **Sensibilidad: 1 de 12 = 8,3 %. Y el único caso que detecta es exactamente aquel sobre el que se calibró** (`escaneado_d3`, `spa`, 100 ppp). **Falsos positivos: 5 de las 14 capas legítimas donde se pronuncia = 36 %** — entre ellas `Col A Col B Col C / 1 2 3`, `f(x) = a x^2 + b x + c` y `J. R. R. T. y C. S. L.`
>
> **Por qué falla, y es una lección sobre la señal, no sobre el umbral:** P9 supone que alucinar produce **ruido corto**. A resoluciones altas Ghostscript alucina **palabras largas y plausibles** —longitud media 4,4 a 5,6, **por encima de la del texto legítimo del propio corpus**— y a veces muchísimas: `escaneado_d4e` a 400 ppp con `eng` devuelve **7 130 caracteres de invención** y **P9 no dice nada**. **Los tokens de una letra son UN modo de alucinación, no LA alucinación.**
>
> *(Y el margen era todavía más estrecho de lo que parecía: con la sonda de `_gs_texto` corregida, el control `tipico_texto.pdf` da **3,62 de longitud media y 41,4 % de tokens de una letra**, no 4,04 y 33,3 %. El margen real era **41,4 % → 61,8 %**.)*
>
> **Se deja implementada y MARCADA EN EL CÓDIGO COMO NO FIABLE**, con severidad `aviso` cuando no se pidió OCR y `fallo` cuando sí, porque su **especificidad** sobre capas OCR sí es del 100 % (0 falsos positivos sobre 20 capas buenas): **sirve como aviso, nunca como criterio.**
>
> #### El sustituto, MEDIDO y con separación perfecta: **acuerdo entre dos pasadas de OCR con idiomas distintos**
>
> *Si el motor **reconoce**, dos pasadas con reconocedores distintos entregan casi lo mismo; si **inventa**, cada una inventa una cosa distinta.* Similitud con `difflib.SequenceMatcher` (biblioteca estándar) entre la salida `spa` y la `eng` del mismo documento y resolución:
>
> | | acuerdo `spa`/`eng` | verdad |
> |---|---:|---|
> | `patologico`, `d1` | **1,000** | bueno |
> | `d2` | 0,975–0,981 | bueno |
> | `d4c`, `d4f` | **0,887**–0,904 | bueno |
> | `d4` | 0,577–**0,700** | **ruido** |
> | `d3`, `d4e` | 0,064–0,197 | **ruido** |
>
> **16 de 16 sin un error. El peor caso bueno da 0,887 y el mejor caso malo 0,700: con umbral 0,80 la banda vacía es de 0,19 puntos — cuatro veces el margen que tenía P9.**
>
> **Su precio, con todas las letras: cuesta una segunda pasada de OCR** (240–1 100 ms sobre estos documentos). Eso lo pone claramente en el **grupo C**, y solo para la arista de reparación. **Es el único que separa una reparación buena de una alucinada. PENDIENTE:** validarlo **fuera de Ghostscript** —dos idiomas del mismo motor podrían acordar en su propio error— y sobre vocabulario que `eng` no comparta.

**Dos costes de integración que hay que escribir con su número:**

- **`-sOCRLanguage=osd` no devuelve un error: revienta Ghostscript con `rc=3221225477` (`0xC0000005`, violación de acceso)** y el mensaje `Error: LSTM requested, but not present!!`. `osd.traineddata` existe, se carga, y no es un modelo de reconocimiento. **Regla directa: el idioma de OCR nunca puede venir de la entrada del usuario sin pasar por una lista blanca.** Es la misma familia de fallo que `av1_nvenc`, listado y no funcional — **sondear en ejecución, no deducir del catálogo**, y esta vez el precio de deducir es un proceso muerto sin código de salida.
- **`spa.traineddata` existía por casualidad**: está en `C:\Program Files\PDFgear\tessdata\` (2 294 433 B). **Lo puso PDFgear, no este proyecto.** **Ghostscript trae el motor pero no los datos**: FileX tendría que **distribuir 2–4 MB por idioma** (licencia Apache-2.0 en `tessdata`/`tessdata_fast`) y fijar `TESSDATA_PREFIX` **en el entorno del proceso hijo**, no en la máquina.

#### La laguna del castellano, medida — y el evaluador oculta 6,3 puntos

Sobre un PDF acentuado fabricado para esto (`INFORME TÉCNICO` / `La conversión se añadió en el último año.` / `Ñandú, camión, acción, pequeñez y ambigüedad.`), con los **dos** evaluadores — **MEDIDO**:

| Idioma | CER con `ocr_eval.py` (**ciego a tildes**) | **CER real (con tildes)** | Puntos que oculta | Frases exactas |
|---|---:|---:|---:|---:|
| **`spa`** | 2,0 % | **1,9 %** | −0,1 | **2 de 3** |
| **`eng`** | **9,2 %** | **15,5 %** | **+6,3** | **0 de 3** |

**`eng` transcribe `añadió` → `afiadio`, `año` → `afio`, `Ñandú` → `Nandu`: destruye sistemáticamente la eñe y todas las tildes, y `ocr_eval.py` da 9,2 % porque normaliza exactamente el error que se quiere medir — un 41 % relativo de subestimación.** **Elegir mal el idioma cuesta 13,6 puntos de CER real y no cuesta un milisegundo** (`eng` y `spa` tardan 236,5 y 225,8 ms en d2). **El idioma del reconocedor es un parámetro obligatorio, no una preferencia.** *(Límite honesto: son 3 frases y 105 caracteres, un caso, no un corpus.)*

### El corpus `escaneado_d4` existe y cumple — `bench/corpus-d4.md` (21/08/2026)

**El criterio de éxito se declaró ANTES de medir:** *al menos un motor entre 15 % y 60 % de CER, y al menos dos motores separados por más de 10 puntos.* **MEDIDO, mediana de n=9, 28 celdas deterministas, formato «CER con acentos / CER ascii»:**

| documento | PaddleOCR (v6 medium) | Docling+RapidOCR torch (v6 small) | RapidOCR (v5 mobile) | EasyOCR |
|---|---:|---:|---:|---:|
| `d4_limpio` (**control**) | **0,00** / 0,00 | 0,00 / 0,00 | 1,17 / 0,50 | 0,50 / 0,50 |
| `escaneado_d4a` | 0,00 / 0,00 | 7,05 / 6,71 | 1,51 / 0,67 | 0,34 / 0,34 |
| `escaneado_d4b` | 0,17 / 0,00 | 18,46 / 18,12 | 2,18 / 0,34 | 27,68 / 27,18 |
| `escaneado_d4c` | 0,67 / 0,00 | 22,99 / 22,48 | 15,60 / 11,91 | 15,10 / 13,76 |
| **`escaneado_d4`** | **19,30** / 18,46 | **36,91** / 36,24 | **41,78** / 38,59 | **61,41** / 59,56 |
| `escaneado_d4e` | 70,97 / 70,47 | 88,59 / 88,42 | 92,45 / 92,11 | 73,32 / 72,32 |
| `escaneado_d4f` (240 ppp) | 0,67 / 0,00 | 22,15 / 21,98 | 6,04 / 2,18 | 17,95 / 16,11 |

**Cumple los cuatro criterios y el de éxito:** tres motores en la banda 15–60 % y **17,6 puntos** entre el primero y el segundo (22,5 entre Paddle y Rapid; 24,5 entre Docling y Easy). **El control importa:** `d4_limpio` sale a 0,00–1,17 %, así que **la tipografía y el texto elegido no son el problema** — todo lo que se mide viene de la degradación.

> ### Dos decisiones de diseño del corpus que merecen quedar escritas porque son reutilizables
>
> 1. **Cuatro tamaños de letra en la misma página** — 24 pt (título), 13 pt (subtítulo), 11 pt (cuerpo, 6 líneas) y **7 pt (letra pequeña, 4 líneas)**, que a 200 ppp mide **19,3 px de cuerpo**. Eso produce fallo **graduado** en vez de interruptor.
> 2. **Una referencia de 610 caracteres, que cuantiza el CER a 0,16 puntos por carácter en vez de los 1,27 de los 79 caracteres de d1–d3.** **Con 79 caracteres no puede haber gradiente aunque el documento lo tenga**: es un límite del corpus viejo que **ninguna elección de degradación arregla**, y explica en parte por qué d3 parecía «un interruptor».
>
> **Y el criterio (b) —atacar al reconocedor, no al detector— está MEDIDO, no argumentado.** La página tiene **12 renglones**; el desglose por bloque sobre `escaneado_d4`:
>
> | motor | título | subtítulo | cuerpo (11 pt) | **letra pequeña (7 pt)** |
> |---|---:|---:|---:|---:|
> | PaddleOCR v6 medium | 0,00 | 0,00 | 1,60 | **58,69** |
> | Docling+RapidOCR torch | 0,00 | 0,00 | 6,09 | **75,12** |
> | RapidOCR v5 mobile | 4,00 | 11,63 | 14,42 | **74,65** |
> | EasyOCR | 0,00 | 53,49 | 59,94 | **75,12** |
>
> **Con recuento de cajas: PaddleOCR detecta 12 de 12 renglones y aun así comete 19,30 % de CER. Todo ese error es del RECONOCEDOR** — los cuatro renglones de 7 pt están **detectados y transcritos como basura**. Es exactamente lo contrario de d3, donde los motores que fallaban recuperaban el titular y **no emitían nada** del cuerpo.

**Lo que `d4` NO resuelve, dicho por su propio informe:** EasyOCR sigue siendo una pared (61,41 % en d4, 73,32 % en d4e, sin estados intermedios útiles); **`d4e` es un d3 nuevo** —los cuatro por encima del 70 %— y se conserva a propósito como cota superior; y **es un documento sintético**: mide rotar, desenfocar, bajar contraste, ruido y JPEG. **Sombra de encuadernación, curvatura y transparencia del papel no están. PENDIENTE.**

**Un hallazgo del cribado que solo aparece ejecutando:** **quitar ruido EMPEORA el resultado.** Con ruido gaussiano 0,35 en vez de 0,65, PaddleOCR pasa de **19,30 % a 36,24 %**, y el fichero pesa la mitad (42 847 frente a 103 369 B). **El ruido actúa como tramado y obliga al JPEG a q=24 a conservar detalle que si no colapsa en bloques planos.** *(La perilla dominante es el desenfoque: bajarlo de 1,6 a 1,2 divide el CER de PaddleOCR por 7.)*

**Cuánto esconde la métrica ciega a las tildes, con número:** **155 caracteres de error ocultos en 28 celdas, media 5,54, máximo 23.** **RapidOCR no recupera ni uno de los 35 caracteres acentuados de `d4`** y `ocr_eval.py` le da 38,59 % en vez de 41,78 %. Los casos peores **no son los documentos más difíciles: son los intermedios**, donde el motor acierta las letras y falla los acentos. **Las 296 celdas de `ocr-ppp-nativos.md` siguen siendo válidas para lo que miden** —su referencia no tiene ni una tilde, así que `cer_ascii == cer_acentos` por construcción—, **pero no se pueden extrapolar a castellano: cualquier cifra de calidad de OCR en español que FileX publique tiene que salir de la métrica con acentos.**

### CPU frente a GPU: dos refutaciones que van juntas — `bench/corpus-d4.md` §9

**(a) La hipótesis «CPU a ppp nativos ≈ GPU a 200 ppp» se cumple a medias — MEDIDO:**

| documento | ppp nativos | CPU a nativos | GPU a 200 ppp | cociente | ¿se cumple? |
|---|---:|---:|---:|---:|---|
| `escaneado_d3` | 100 | 219,9 ms | 208,8 ms | **×1,05** | **sí** |
| `escaneado_d2` | 100 | 262,6 ms | 192,3 ms | ×1,37 | casi |
| `escaneado_d1` | 150 | 460,6 ms | 203,8 ms | **×2,26** | **no** |

**Se cumple exactamente donde el ahorro de píxeles es máximo y se cae en cuanto no lo es.** Para los documentos que ya están a 200 ppp nativos la comparación **no existe**: no hay interpolación que evitar.

**Lo que sí decide, a la misma resolución:** **RapidOCR es solo ×2,3–3,8 más lento en CPU (0,22–1,19 s/página); PaddleOCR es ×9,8–13,8 (hasta 5,42 s) y EasyOCR ×6,5–12,0.** Junto con la corrección de normalización, la conclusión operativa es **más fuerte que la hipótesis original**: **FileX puede hacer OCR de calidad de PaddleOCR sin GPU**, con RapidOCR ONNX + PP-OCRv6 small + la normalización correcta. *(En CPU, `onnxruntime` bate a `torch` en las cinco filas de docling, entre 1,2 % y 20,0 %, con CER idéntico: la elección de backend es puramente de coste.)*

**(b) «CPU y GPU dan salida idéntica carácter a carácter» queda REFUTADO — MEDIDO.**

`bench/gpu-fase2.md` §2 lo midió sobre tres configuraciones de RapidOCR y dos de EasyOCR y concluyó que la GPU *«no compra precisión, solo velocidad»*. Con el corpus nuevo y **21 celdas comparables, 5 difieren**:

| motor | celdas | **distintas** | mayor discrepancia |
|---|---:|---:|---|
| RapidOCR | 9 | **1** | `d3` a 200 ppp: **65,82 % (GPU) vs 70,89 % (CPU)** |
| PaddleOCR | 9 | **1** | `d4`: 19,30 % (GPU) vs 19,63 % (CPU) |
| EasyOCR | 3 | **3** | `d3` a 200 ppp: 59,49 % (GPU) vs **56,96 % (CPU)** |

**La CPU es mejor en dos celdas y peor en tres.** La conclusión matizada: *la salida coincide mientras el documento es fácil; en la zona de degradación donde el motor duda, el dispositivo cambia el resultado, y puede cambiarlo en cualquier dirección.* **Para FileX: no se puede validar en CPU y desplegar en GPU dando por hecho el mismo resultado, y una prueba de regresión de OCR tiene que fijar el dispositivo.** *(Esta refutación ilumina de paso la discrepancia `57,0 % / 59,5 %` de EasyOCR en d3 que `bench/consolidacion-21ago.md` §4 dejó anotada: eran CPU y GPU de la misma casilla, y ahora se sabe que eso no es una rareza de una celda.)*

**Y hay una advertencia de método que va con esto y no se puede separar de ello:** las medianas de CPU de arriba se tomaron **con otros dos agentes midiendo en CPU en paralelo**, y **la sonda de carga de su arnés devolvió `-1` en las 11 tandas** (`FileNotFoundError: [WinError 2]`, `powershell` sin ruta absoluta bajo Git Bash). **Su propio informe las declara COTA SUPERIOR del coste de CPU y no las repitió.** En una máquina ociosa serían iguales o mejores. Ver `CLAUDE.md` §3: es exactamente el punto ciego que `bench/verificador-ghostscript.md` §4 describe, ocurriendo el mismo día.

### Lo PENDIENTE

- ~~**OCRmyPDF como preprocesador.**~~ **RESUELTO (20/08/2026): descartado.** Ver arriba y `bench/ocrmypdf.md`.
- ~~**Repetir la fase 2 rasterizando a los ppp nativos.**~~ **RESUELTO (21/08/2026): `bench/ocr-ppp-nativos.md`**, con los cuatro motores, 296 celdas y la tabla canónica de arriba.
- ~~**Construir un `escaneado_d4`.**~~ **RESUELTO (21/08/2026): `bench/corpus-d4.md`.** Existe `corpus/pdf/escaneado_d4.pdf` (canónico, 200 ppp nativos) + `d4a/b/c/e/f`, con `corpus/pdf/MANIFIESTO-d4.md`. **Cumple los cuatro criterios y el de éxito declarado antes de medir.**
- ~~**Aislar la causa de la asimetría de PaddleOCR.**~~ **RESUELTO, y no era ninguna de las tres candidatas: era la normalización del detector de RapidOCR.** Ver arriba.
- ~~**Ninguna medición de OCR de este proyecto lleva tildes ni castellano real.**~~ **RESUELTO por dos vías independientes**: `corpus-d4.md` §1/§6 (evaluador con las dos métricas, 155 caracteres ocultos en 28 celdas) y `verificador-ghostscript.md` §5.5 (6,3 puntos ocultos sobre `eng`). **El original `bench/scripts/ocr_eval.py` sigue intacto y sigue siendo ciego**: los dos informes copiaron el arnés en vez de modificarlo. **Queda PENDIENTE decidir si la métrica acentuada pasa a ser la canónica del proyecto.**
- ~~**Calidad del OCR embebido en Ghostscript en castellano con tildes.**~~ **RESUELTA: 1,9 % de CER real con `spa`.**
- ~~**Validar la corrección de normalización de RapidOCR fuera de este corpus**, contra el patrón oro.~~ **CERRADO: 15 documentos, n=9, 0 regresiones sobre `PP-OCRv6 small` — y 12 de 42 celdas peores si se aplica a la familia entera.** Ver arriba.
- ~~**Barrer la curva de ppp sobre `d4`** para cerrar el techo absoluto de 200.~~ **CERRADO, y el techo absoluto queda REFUTADO junto con el relativo: la regla es por motor.** Ver arriba.
- **Caracterizar el `k` de cada motor sobre más de un documento.** Los siete óptimos salen todos de `escaneado_d4`: **que *haya* un `k` por motor está apoyado por tres documentos, pero el VALOR de cada `k` es una estimación de un punto.** Antes de cablearlo en el adaptador hay que barrer al menos `d3`, `d4c` y `patologico` con las siete configuraciones. **Es el pendiente de más valor que abre esta pasada.**
- **La curva de ppp de Tesseract, sin barrer.** La evidencia es n=1 y **en dos direcciones opuestas** (`d2` pide ×1,5, `d4` pide ×1,0).
- **El suelo de 100 ppp no se ha medido con un original que lo necesite.** Todo el corpus está entre 100 y 240 ppp nativos; **el ×1,25 propuesto sale de acotar la subida en documentos que no la necesitan. PENDIENTE: un `escaneado_d5` de 60-80 ppp nativos.**
- **Toda la curva de ppp está medida sobre una sola geometría de página.** Que el efecto sea de píxeles y no de ppp está cerrado; **que el umbral de píxeles dependa del tamaño de letra EN PÍXELES es la hipótesis que sugiere el desglose por bloque y no está aislada** — haría falta la misma página con un solo cuerpo de letra por documento.
- **`escaneado_d3` no tiene refinamiento entre ×1,25 y ×1,4**, que es justo donde está el acantilado de RapidOCR+R6 (2,53 → 46,84). **Es el mismo defecto que esta pasada vino a corregir en `d4`, en otro documento.**
- **La sonda de píxeles solo cubre RapidOCR y PaddleOCR.** EasyOCR y docling no están instrumentados.
- **B11 sigue PROPUESTO, NO APLICADO**, y con su contenido cambiado: cambiar a `PP-OCRv6 small` **y** añadir R6, con saldo declarado de **7 mejor, 2 igual, 2 peor**.
- **`magick -deskew 40%` × el techo.** Sigue sin medirse su interacción con la regla de ppp, ahora con documentos rotados de −4° a +4° (la familia d4).
- **La heurística de degradación severa.** Con `d4` ya hay un caso con gradiente contra el que calibrarla, y con el recuento de cajas hay **una señal candidata: cajas detectadas frente a área de texto**. Y otra, independiente: **el tiempo** (d3 cuesta 4,5× lo que d2 a la misma resolución en Ghostscript).
- **Degradación realista** en el corpus: sombra de encuadernación, curvatura de página, transparencia del papel. `d4` es sintético.
- **EasyOCR sigue sin caso útil**: 61,41 % en `d4`, 73,32 % en `d4e`, sin escala.
- **Reintento de Surya** por `SURYA_INFERENCE_BACKEND=llamacpp` o `VLLM_GPU_MEMORY_UTILIZATION=0.5`. Solo se probó su backend por defecto.
- **MinerU con el extra `[vlm]`**, compatible con el torch instalado.

Ver `ESTADO-Y-REPARTO.md` §3. **El hallazgo de arquitectura que se buscaba existe, pero es más barato de lo previsto: elegir bien los ppp, no añadir una etapa** — y ahora hay un segundo, del mismo tipo y aún más barato: **elegir bien la normalización del detector.**

---

## Qué significa para el plan de construcción

**No cambia el orden de los hitos.** `PLAN-ORQUESTADOR.md` §7 ya sitúa el contrato de verificación en el hito 3, **antes que MCP**, precisamente porque sin él todo lo anterior puede mentir. Ese orden resulta ser el correcto por una razón más fuerte de la que se creía.

**Lo que cambia es el argumento de FileX.** No es *"convierte más cosas más rápido"* — eso es discutible y en parte replicable. Es:

> **Es el único que garantiza que lo que te entrega es lo que pediste.**

Los otros cuatro diferenciadores son apoyos de ese argumento, no el argumento.

---

## Índice de la evidencia

| Afirmación | Dónde está el dato |
|---|---|
| Los 7 fallos de verificación | `bench/competidores.md`, `bench/mcp-ergonomia.md`, `bench/gpu-fase2.md` |
| **El coste de verificar y el 4º punto del contrato** | **`bench/coste-verificacion.md`**, `bench/salidas-verificacion/` |
| Patrón oro y 46 reglas de regresión | `bench/referencia-nativa.md`, `bench/salidas-referencia/referencia.json` |
| 0 de 7 con búsqueda de camino · el 2,93× | `analysis/00-hueco-multisalto.md`, `analysis/00-matriz-formatos.md` |
| **Fidelidad real del multi-salto: 69 caminos ejecutados** | **`bench/fidelidad-caminos.md`**, `bench/salidas-fidelidad/clasificado.json` |
| **El artefacto de ppp y el descarte de OCRmyPDF** | **`bench/ocrmypdf.md`**, `bench/salidas-ocrmypdf/` |
| **La tabla canónica de OCR, la regla de ppp y la VRAM por resolución** | **`bench/ocr-ppp-nativos.md`**, `bench/salidas-ocr-ppp/` |
| **`min(alfa)` en proceso, las 11 reglas de fidelidad y los tres grupos** | **`bench/verificador-fidelidad.md`**, `bench/salidas-verificacion-fidelidad/` |
| **La saturación del catálogo: 540 ejecuciones, dos modelos** | **`bench/saturacion-herramientas.md`**, `bench/salidas-saturacion/` |
| **Los cinco cabos MCP: anotaciones, roots, deadlock y TOCTOU** | **`bench/mcp-cabos-sueltos.md`**, `bench/salidas-mcp-cabos/` |
| **El 50,5 % de aristas nominales, el estrato PDF al 3,0 %, `resvg` sin letras y los motores que escriben fuera del destino** | **`bench/aristas-nominales.md`**, `bench/salidas-aristas/` |
| **El corpus `d4`, la causa real de la asimetría de PaddleOCR y las dos refutaciones CPU/GPU** | **`bench/corpus-d4.md`**, `bench/salidas-corpus-d4/`, `corpus/pdf/MANIFIESTO-d4.md` |
| **El OCR sin GPU de Ghostscript, `min(alfa)` de TIFF/GIF/Adam7, V2/V5 y el segundo testigo de ruido** | **`bench/verificador-ghostscript.md`**, `bench/salidas-verificador-gs/` |
| **La curva de ppp (17 puntos), la refutación de las tres unidades candidatas, el `k` por motor y la validación de la normalización por checkpoint** | **`bench/ppp-y-normalizacion.md`**, `bench/salidas-ppp-norm/` |
| **El 18,8 % de invocación, los crudos con sus cuatro datos, el censo de gs+Gotenberg al 3,1 % y el coste de `qpdf`+`tesseract`** | **`bench/invocacion-aristas.md`**, `bench/salidas-invocacion/` |
| **El quinto punto implementado, la regla I9, la familia de cinco miembros, `P9` refutada con su sustituto, el interruptor de V2 y el fallo de `_gs_texto`** | **`bench/contrato-quinto-punto.md`**, `bench/salidas-quinto-punto/` |
| El bug de despacho de ConvertX | `analysis/ConvertX.md` |
| MCP de pago de Stirling-PDF | `analysis/Stirling-PDF.md` |
| 85 259 frente a 36 tokens | `bench/mcp-ergonomia.md` |
| NVENC, bitrate y tubería GPU | `bench/gpu-fase1.md` |
| Los tres motores de OCR | `bench/gpu-fase2.md` |
| Lo pendiente de OCR | `AGENTES-PRUEBAS-PENDIENTES.md` |
| Los resultados de MCP | `RESULTADOS-MCP.md` |
