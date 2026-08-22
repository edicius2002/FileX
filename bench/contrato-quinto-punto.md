# El quinto punto del contrato, la regla que atrapa a `resvg`, y una señal que no servía

**Encargo P3** — C9 (implementar y medir el **quinto punto** del contrato y la regla **R18**),
C10 (la regla de fidelidad del **texto rasterizado**), C11 (**validar `P9`** y añadir `ocr: true`
al pedido) y C12 (**interruptor de V2**).

**Fecha:** 21 de agosto de 2026.
**Máquina:** Windows 10, 12 núcleos, Python 3.11.9, ffmpeg/ffprobe N-121159, ImageMagick
7.1.2-21 Q16-HDRI, Ghostscript 10.07. **Sin GPU y sin pedir su lock** (lo tenía P1).
**Sin dependencias nuevas:** `bench/scripts/verificador.py` sigue siendo biblioteca estándar
de Python y nada más.
**Salidas:** `bench/salidas-quinto-punto/` (355 KB, todo texto, con `MANIFIESTO.md`).

> Cada afirmación va marcada **MEDIDO** o **PENDIENTE**.
> **Otros dos agentes corrían en paralelo**, uno de ellos midiendo en CPU. Todas las medidas
> llevan **los dos testigos de ruido**; el de lanzamiento de proceso llegó a marcar **×94** y
> a **agotar 60 s en `ffprobe -version`**. Ver §9.

---

## 0. Las tres frases obligatorias, y seis más

1. **El punto 5 cuesta 0,047 ms y SÍ entra en el camino caliente — pero solo con R18.**
   **MEDIDO.** El contrato pasa de **0,4254 ms a 0,4722 ms** (**+11,0 %**) cuando el motor
   trabaja en un directorio desechable y basta censar **después**. Sobre un directorio
   compartido de 1 000 ficheros, censar antes y después cuesta **3,66 ms**: **×8,6 el contrato
   entero**. **R18 no es una comodidad de higiene: es lo que mantiene el punto 5 en el camino
   caliente.** *(§2)*
2. **Falsos positivos que añade el punto 5 sobre las 53 salidas del patrón oro: CERO.**
   **MEDIDO.** Reejecutando las **39 órdenes** del patrón oro en directorio desechable (36 son
   de motor; 3 son de Python), el punto 5 no emite **ni un aviso ni un fallo**, y **ninguna de
   las 36 produce más de un fichero**. Lo que sí añade es honestidad: **sin censo, 49 de las 53
   bajan de `ok` a `ok_parcial`**, porque el punto 5 **no se puede evaluar a posteriori**.
   *(§3)*
3. **`resvg` NO es un caso aislado: es la punta de una familia con al menos cinco miembros, y
   uno de ellos sigue sin cubrir después de añadir I9.** **MEDIDO.** SVG→PNG sin fuentes, vídeo
   con envase correcto y todo negro, PDF de texto rasterizado, CSV→JSON que pierde una columna
   y **audio estéreo con un canal silenciado a un destino con pérdida**. El último **no lo
   atrapa nada**: ni los cinco puntos del contrato ni ninguna de las 15 reglas de fidelidad.
   *(§5)*
4. **I9 atrapa a `resvg` a la primera y no marca a Inkscape: 6 de 6.** **MEDIDO.** 0,00 % de
   tinta frente a 20,01 % (Inkscape) y 23,61 % (`magick`). El margen no es estrecho: es
   binario.
5. **Y I9 cuesta 40 ms sobre 400×200 y 2 454 ms sobre 1920×960.** **MEDIDO.** La estimación del
   encargo («del orden de los 26 ms del grupo C») valía para el caso de juguete y **por ×94
   para el caso real**. El **99,6 %** del coste es leer píxeles; analizar el SVG cuesta
   **0,14 ms**. *(§4)*
6. **Y ahí se refuta una constante del proyecto.** **MEDIDO.** «Verificar en proceso, no con
   subprocesos» **no se transfiere a leer píxeles de un raster grande**: `magick` hace la misma
   medida en **138 ms** donde el lector en proceso tarda **2 834**. El punto de cruce está en
   ~0,1 Mpx. *(§4.3)*
7. **`P9` está refutada como está calibrada.** **MEDIDO.** Contra **32 capas OCR reales**
   detecta **1 de 12 alucinaciones (8,3 %)**, y contra **14 capas de texto legítimo evaluables**
   marca **5 falsos positivos (36 %)**. Los 5 puntos con los que se calibró eran el único sitio
   donde funcionaba. **Hay un sustituto que separa los 16 casos sin un error:** el **acuerdo
   entre dos pasadas de OCR con idiomas distintos**. *(§6)*
8. **`gs -sDEVICE=txtwrite` devolvía vacío el 1,1–4,8 % de las veces, y no era Ghostscript:
   era la tubería.** **MEDIDO, 430 ejecuciones guardadas por cada ruta.** Es la observación que
   `verificador-ghostscript.md` §5.9 no consiguió reproducir en 20 intentos. Por tubería:
   **6 vacíos de 430**. Por fichero temporal: **0 de 430**, al mismo coste. De esa sonda
   cuelgan P2 (severidad **fallo**), P5, P6 y P9. **Corregido.** *(§8)*
9. **El interruptor de V2 ahorra el 46,3 % de la suite de fidelidad** (70 693 → 37 947 ms sobre
   las 53 salidas) **sin cambiar ni un aviso**, y sube los `ok_parcial` de 8 a 13, que es lo
   correcto: apagar una regla reduce cobertura, no aprueba. *(§7)*

---

## 1. Qué se implementó

`bench/scripts/verificador.py` queda en **4 185 líneas**, sin una sola dependencia externa.

| Bloque nuevo | Líneas | De código |
|---|---:|---:|
| **Punto 5** (`censar_dir`, `censar`, `mtime_dir`, `punto5_escritura`, tabla de destinos multifichero, patrones `%d`) | **176** | 126 |
| **I9 — acceso al dato** (`svg_textos` con `xml.etree`, `_desfiltrar_fila`, `png_tinta_cajas`, `_leer_plte`, `_lum_png`) | **265** | 228 |
| **I9 — la regla** (`fidelidad_vectorial`, `es_svg`) | **81** | 77 |
| **P9** (`senal_alucinacion` + la regla + la rama `ocr` de P5) | **29** + ~20 | 21 |
| **`_gs_texto` por fichero temporal** (la corrección del §8) | **36** | 33 |
| Interruptor de V2, CLI (`--censo`, `--censar`, `--sin-v2`) y ayuda | ~60 | ~50 |

*(Nota de trazabilidad: `verificador-ghostscript.md` §6 publica 3 859 líneas como estado final
de V1. Los bloques de arriba suman ~640 líneas añadidas y el total actual es 4 185, lo que
implica un punto de partida de ~3 530. **No he podido reproducir la cifra de 3 859** y lo dejo
anotado. Los tamaños de bloque sí están medidos sobre el fichero actual.)*

**Cambios de firma, para quien invoque el verificador:**

| Qué | Antes | Ahora |
|---|---|---|
| `verificar(...)` | 4 puntos | acepta **`censo=`** y ejecuta 5 puntos. Sin `censo`, `cobertura["5_escritura"] = False` |
| `cobertura` del contrato | 5 claves | **6**: se añade `5_escritura` |
| `pedido["params"]["ocr"]` | no existía | si vale `true`, **P5 invierte la exigencia** (la salida DEBE traer texto) y **P9 sube de `aviso` a `fallo`** |
| `verificar_fidelidad(...)` | 13 reglas | **15**: se añaden **I9** y **P9** |
| CLI | — | `--censo F.json`, `--censar DIR...`, `--sin-v2` |
| `_gs_texto` | `-sOutputFile=-` (tubería) | fichero temporal, borrado en `finally` |

> **Aviso para P2:** sus cifras salen de una **copia congelada** anterior a todo esto. Lo que
> cambia respecto a esa copia es: (a) la sexta clave de cobertura, que **baja a `ok_parcial`**
> cualquier verificación hecha sin censo; (b) dos reglas nuevas de fidelidad; (c) `_gs_texto`,
> que ahora es determinista. **Ningún veredicto de fallo/aviso del patrón oro cambia** (§3.3).

---

## 2. C9 — cuánto cuesta el punto 5, y qué compra R18

### 2.1 Las tres implementaciones — **MEDIDO** (mediana n=15, `limpia`)

Datos: `coste_p5.json`.

| Entradas en el directorio | `censar_dir` (1 `scandir`) | censo **antes+después** | `mtime` del directorio (1 `stat`) |
|---:|---:|---:|---:|
| 1 | **0,0347 ms** | 0,0491 ms | 0,0224 ms |
| 2 | 0,0284 ms | 0,0530 ms | 0,0164 ms |
| 10 | 0,0366 ms | 0,1242 ms | 0,0153 ms |
| 100 | 0,1509 ms | 0,2938 ms | 0,0189 ms |
| 1 000 | **1,5480 ms** | **2,7809 ms** | **0,0163 ms** |

**El censo crece con el número de entradas; el `mtime` no.** Pero el `mtime` **no sirve como
punto 5**: dice *que* algo cambió, no *qué*, y en un directorio donde acaba de aparecer el
fichero de salida siempre cambia. Es un disparador barato para directorios que **no** deberían
tocarse (por ejemplo el `cwd` del orquestador), no un sustituto.

### 2.2 El contrato completo — **MEDIDO** (mediana n=15, `limpia`)

| Configuración | Mediana | Frente al contrato de 4 puntos |
|---|---:|---:|
| **Contrato SIN punto 5** (referencia) | **0,4254 ms** | ×1 |
| + punto 5 con el censo ya hecho (solo la lógica) | 0,4767 ms | ×1,12 |
| **+ punto 5 COMPLETO con R18** (directorio desechable: solo se censa DESPUÉS) | **0,4722 ms** | **×1,11** |
| + punto 5 completo **sin R18**, directorio de 2 ficheros | 0,5138 ms | ×1,21 |
| + punto 5 completo **sin R18**, directorio de 1 000 ficheros | **3,6614 ms** | **×8,6** |
| *(aislada)* `punto5_escritura`, 0 ficheros nuevos | 0,0314 ms | — |
| *(aislada)* `punto5_escritura`, 1 fichero nuevo | 0,0366 ms | — |

**La respuesta a la pregunta del encargo, con su número:**

> **El punto 5 cuesta 0,047 ms sobre el contrato, un +11,0 %, y entra en el camino caliente:
> el contrato pasa del 0,032 % al 0,036 % de convertir.** Y ese número **depende de R18**: sin
> directorio de trabajo desechable, sobre un directorio real de 1 000 ficheros, el punto 5
> cuesta **3,24 ms**, que es **×7,6 el contrato de cuatro puntos** y lo saca del camino
> caliente. **MEDIDO.**

**La lógica del punto 5 es gratis (0,031–0,037 ms). Lo caro es el censo, y R18 lo divide por dos
y lo acota a un directorio que solo contiene lo que acaba de escribirse.** Es el mismo patrón
que lleva tres informes seguidos: fabricar el acceso al dato es el coste.

### 2.3 Qué comprueba, exactamente

| Regla | Qué mira | Severidad |
|---|---|---|
| **N5** | ficheros nuevos **fuera** del directorio de destino cuyos **bytes superan** a los del fichero entregado → *el contenido se fue a otro sitio* | **fallo** |
| **N6** | ficheros nuevos fuera del destino con **menos** bytes que el entregado → *suciedad, no pérdida de contenido* | aviso |
| **N7** | ficheros nuevos **en** el destino además del declarado. **Informativo** si el destino es multifichero por naturaleza (`mpd`, `m3u8`, `html`, `shtml`, `ismv`, `vtt`), si el pedido lleva `multifichero: true`, o si el nombre declarado es un **patrón `printf`** (`salida_%03d.png`); **aviso** en cualquier otro caso | informativo / aviso |
| **N8** | ficheros que ya existían y el motor **modificó** | aviso |
| **N9** | qué fracción de los bytes escritos lleva el fichero entregado | **informativo, siempre** |

**Las dos decisiones que salieron de los datos y no de la especificación:**

1. **El disparador es la UBICACIÓN, no el tamaño.** N9 parecía el detector obvio del caso DASH
   (`.mpd` de 1 234 B frente a 528 KB de segmentos = 0,2 %). Pero **un manifiesto HLS legítimo
   también lleva el 0,0 % de los bytes** (114 B de `.m3u8` frente a 248 KB de segmentos, medido
   en §3.2). Si N9 fuera el disparador, **toda salida en streaming sería un fallo**. El reparto
   de bytes solo decide la **severidad** de una fuga ya detectada por ubicación.
2. **Declarar `multifichero: true` NO autoriza a escribir en el `cwd`.** Medido: la orden DASH
   con `multifichero: true` en el pedido **sigue dando N5 fallo**, porque sus segmentos no están
   junto al manifiesto sino en el directorio de trabajo. Es la diferencia entre «esta salida son
   varios ficheros» y «este motor escribe donde le da la gana».

---

## 3. C9 — ¿atrapa lo que tiene que atrapar y calla con lo demás?

### 3.1 Los dos casos reproducidos por E1 — **MEDIDO**

Datos: `fuga.json`. Motor con `cwd` = directorio de trabajo, salida a `DEST/`.

| Caso | rc | Contrato de **4** puntos | Contrato de **5** puntos | Hallazgo del punto 5 |
|---|---:|---|---|---|
| `ffmpeg -i trivial.mp4 DEST/t.mpd` | 0 | `ok_parcial` | **`fallo`** | **N5 fallo:** 2 ficheros (529 261 B) fuera del destino: `chunk-stream0-00001.m4s`, `init-stream0.m4s`. N9: el `.mpd` lleva el **0,2 %** de los bytes |
| `magick trivial.png DEST/u.html` | 0 | `fallo` *(por otro motivo, ver abajo)* | `fallo` | **N6 aviso:** 1 fichero (98 B) fuera: `u_map.shtml`. **N7 informativo:** `html` es multifichero declarado, `u.png` acompaña |
| *control:* `magick … DEST/v.map` | 0 | `ok_parcial` | `ok_parcial` | ninguno. N9: 100 % |
| *control sano:* `magick … DEST/w.webp` | 0 | `ok_parcial` | `ok_parcial` | ninguno. N9: 100 % |

**Los dos casos que motivaron el encargo quedan atrapados, y con severidades distintas y
justificadas:** el DASH pierde el contenido (**fallo**), el mapa de imagen solo ensucia el
directorio de trabajo (**aviso**).

> **Y un hallazgo lateral que conviene no confundir con un acierto:** el contrato de cuatro
> puntos ya daba `fallo` a `u.html`, pero **por la razón equivocada**. La sonda no tiene
> vocabulario para HTML, lo clasifica como CSV y dispara
> `[p3 D2 fallo] numero de campos no constante`. **Es un falso positivo que acierta por
> casualidad.** Material para C14 (ampliar el vocabulario de firmas), no para el punto 5.

### 3.2 Salidas legítimamente multifichero — **MEDIDO**

El patrón oro **no tiene ni una** (§3.3), así que sin estos casos el «0 falsos positivos» no
probaría nada en la dimensión que más importa. Datos: `multi.json`.

| Caso | Ficheros en el destino | Ficheros en el trabajo | Punto 5 |
|---|---:|---:|---|
| HLS: `ffmpeg … -hls_time 1 DEST/h.m3u8` | 2 | 0 | **N7 informativo** + N9 informativo. **Sin aviso** |
| Secuencia: `ffmpeg … DEST/f%03d.png` | **20** | 0 | **ningún hallazgo.** N9: 100 % |
| Secuencia: `gs -sOutputFile=DEST/p%d.png` sobre un PDF de 2 páginas | 2 | 0 | **ningún hallazgo.** N9: 100 % |
| DASH con `multifichero: true` **en el pedido** | 1 | **2** | **N5 fallo** — declarar multifichero no autoriza a escribir en el `cwd` |

**Cero avisos y cero fallos en las tres salidas multifichero legítimas, y el fallo se mantiene
donde debe.** El trabajo real del punto 5 —distinguir «esto son varios ficheros porque el
formato lo es» de «esto se escribió donde no tocaba»— **se resuelve por ubicación más patrón
declarado, no por recuento.**

### 3.3 El patrón oro: 39 órdenes reejecutadas y 53 salidas verificadas — **MEDIDO**

**El punto 5 no se puede medir sobre ficheros que ya existen: hay que volver a convertir.**
Datos: `ordenes39.json`.

| | Resultado |
|---|---|
| Órdenes del patrón oro | 39 (**36** de motor; 3 son de Python y no se reejecutan) |
| Ejecutadas en directorio desechable con censo | **36**, todas `rc=0` |
| **Hallazgos del punto 5 de severidad `fallo` o `aviso`** | **0** |
| **Órdenes que producen más de un fichero** | **0** |
| Órdenes con patrón `%d` en la orden (`pdf.2png`, `pdf.2jpg`) | 2 — pero el PDF del corpus tiene **una** página, así que producen un fichero |

> **La respuesta a la segunda pregunta del encargo: el punto 5 añade CERO falsos positivos
> sobre el patrón oro.** Con una advertencia honesta: **el patrón oro es un test flojo para
> este punto**, porque no contiene ni una salida multifichero. La prueba de discriminación de
> verdad es la del §3.2, fabricada a propósito.

Y sobre las **53 salidas** ya existentes (`contrato53.json`), con `alfa=True`:

| Motor | Censo | ok | aviso | ok_parcial | fallo | **Falsos positivos** |
|---|---|---:|---:|---:|---:|---:|
| proceso | **sin censo** | 0 | 3 | **49** | 1 | **0** |
| proceso | censo vacío (R18 ideal) | **49** | 3 | 0 | 1 | **0** |
| subproceso | sin censo | 0 | 4 | 48 | 1 | **0** |
| subproceso | censo vacío (R18 ideal) | 48 | 4 | 0 | 1 | **0** |

Los 3 y 4 avisos son los mismos de siempre y el único `fallo` es
`2pistas_mkv-to-DEFAULT.mp4`, **cuyo veredicto esperado es `fallo`** (pierde una pista de
audio). **Idéntico a lo que publicaron `verificador-fidelidad.md` §5.2 y
`verificador-ghostscript.md` §3.1.**

**Lo que sí cambia, y es el precio del punto 5: sin censo, 49 de las 53 pasan de `ok` a
`ok_parcial`.** No es un falso positivo: es el verificador diciendo *«no puedo saber si el
motor escribió en otro sitio, porque nadie miró cuando tocaba»*. **El punto 5 es el primero del
contrato que no es verificable a posteriori**, y eso es en sí un argumento de arquitectura: la
verificación tiene que estar **dentro** de la conversión, no ser un paso que se pueda hacer
luego.

**Y los 5 fallos documentados siguen atrapados: 12 de 12** con los dos motores
(`fallos5.json`, 0 discrepancias), incluido el control 4b que sigue dando `ok`.

---

## 4. C10 — la regla I9, y el coste que refuta una constante del proyecto

### 4.1 Cómo funciona

> **I9: si el SVG de origen contiene elementos `<text>` con contenido, la salida rasterizada
> debe tener tinta donde estaban.**

Dos mitades, las dos en proceso:

1. **El origen.** `xml.etree` (biblioteca estándar) recorre el SVG, saca cada `<text>` con su
   `x`, `y`, `font-size` y `text-anchor`, y le estima una caja **deliberadamente estrecha**:
   vertical de `y − 0,75 em` a `y + 0,20 em`, horizontal de `x` a `x + 0,50 em × n`, con
   `n ≤ 24` caracteres. **Estrecha a propósito:** una caja generosa que abarcara otras figuras
   daría **falsos negativos** —tinta ajena tapando la ausencia de letras—, que es justo el
   fallo que se quiere evitar.
2. **La salida.** Un lector de píxeles de PNG en proceso (desfiltrado completo, tipos de color
   0/2/3/6, profundidades 1/2/4/8/16) cuenta, dentro de cada caja, qué fracción de píxeles se
   aleja del **fondo real de la caja** (el valor de luminancia más frecuente) en más de 64 de
   255. Definir la tinta contra el fondo real y no contra el negro hace que la regla valga
   igual para texto claro sobre oscuro.

Umbrales: **`fallo` por debajo del 0,5 % de tinta**, `aviso` por debajo del 2 %.
No cubierto: PNG entrelazado (devuelve `evaluable: false` con el motivo) y destinos que no sean
PNG. **Decirlo es la respuesta correcta; inventar un número no.**

### 4.2 ¿Discrimina? 6 de 6 — **MEDIDO**

Datos: `i9.json`. Los tres primeros son los rasterizados reales de `bench/salidas-aristas/`.

| Caso | `<text>` | Tinta en la peor caja | Veredicto |
|---|---:|---:|---|
| **Inkscape 1.x** (contenedor) | 2 | **20,01 %** | `ok` |
| **`resvg` 0.46.0** (contenedor) | 2 | **0,00 %** | **`fallo`: TEXTO PERDIDO** |
| **`magick` 7.1.2** (Windows) | 2 | **23,61 %** | `ok` |
| control: SVG **sin** `<text>` → PNG | 0 | — | `ok_parcial`, «la regla no aplica» |
| control: texto de **2 caracteres** (`Ab`) | 1 | 21,49 % | `ok` |
| control: `text-anchor="middle"`, texto largo | 1 | 18,26 % | `ok` |

**El margen no es estrecho, es binario: 0,00 % frente a 18–24 %.** Y los controles cubren los
dos modos en que la estimación de caja podría fallar —un texto tan corto que la caja se quede
sin sitio, y un anclaje que no sea `start`—; ninguno da falso positivo.

**Sobre las 53 salidas del patrón oro, I9 no se evalúa ni una vez** (ninguna tiene un SVG como
entrada) y **no añade ni un aviso**: los 8 avisos de fidelidad siguen siendo exactamente los
mismos ocho (§7).

### 4.3 El coste — y aquí hay que refutar algo — **MEDIDO** (mediana n=9)

| Rasterizado | I9 completa | origen (`xml.etree`) | salida (tinta, **en proceso**) | salida (tinta, **con `magick`**) |
|---|---:|---:|---:|---:|
| 400×200 (Inkscape) | **48,96 ms** | 0,187 ms | 42,68 ms | 42,40 ms |
| 400×200 (`resvg`) | 59,18 ms | 0,208 ms | 55,78 ms | 37,23 ms |
| 400×200 (`magick`) | 31,90 ms | 0,134 ms | 38,43 ms | 39,03 ms |
| **800×400** | **536,96 ms** | 0,137 ms | 452,11 ms | **66,22 ms** |
| **1920×960** | **2 453,65 ms** | 0,210 ms | **2 833,77 ms** | **138,39 ms** |

**Tres lecturas, y la tercera contradice una regla de diseño del proyecto:**

1. **La estimación del encargo era «del orden de los 26 ms del grupo C». El coste real es
   32–59 ms sobre 400×200 y 2 454 ms sobre 1920×960.** Vale para el caso de juguete y se queda
   corta por **×94** en un raster de 1,8 Mpx. **Medir en vez de estimar cambia la conclusión de
   dónde vive la regla.**
2. **El 99,6 % del coste es fabricar el acceso al dato** (leer píxeles) y el **0,4 %** es la
   regla (analizar el SVG cuesta 0,14–0,21 ms). Es la cuarta medida seguida de la misma
   constante del proyecto: **53 %** en el prototipo, **61 %** en la extensión de fidelidad,
   **70 %** en la de V1, **99,6 %** aquí. La lógica de la regla nunca es el coste.
3. **REFUTADO PARCIALMENTE: «verificar leyendo cabeceras en proceso, no con subprocesos» no se
   transfiere a leer PÍXELES de un raster grande.** A 400×200 los dos caminos empatan
   (38–56 ms en proceso, 37–42 ms con `magick`); a 800×400 `magick` gana **×6,8**; a 1920×960
   gana **×20,5**. El punto de cruce está en **~0,1 Mpx**. Es exactamente el mismo fenómeno que
   `verificador-fidelidad.md` §7.2 anotó para el decodificador VP8L («por debajo de ~0,3 Mpx
   gana a `magick`; por encima pierde»), ahora medido en otra regla y con otro formato. **La
   regla de diseño correcta no es "siempre en proceso": es "en proceso para cabeceras y para
   rasters pequeños; con la sonda externa a partir de ~0,1–0,3 Mpx".** La implementación
   entregada usa el camino en proceso **porque no añade dependencias**, y esa elección tiene un
   precio medido.

### 4.4 ¿Dónde vive I9? Y la pregunta de arquitectura de D2

D2 acotó así el hallazgo de E1: *«el contrato juzga la declaración; el contenido que desaparece
necesita fidelidad»*. El encargo pedía decir si eso se sostiene tras implementarlo o si es una
excusa. **Se sostiene, y ahora con un criterio en vez de con una intuición:**

> **El contrato atrapa la pérdida de contenido cuando el contenido está DECLARADO en
> metadatos** —número de filas, cabecera de un CSV, número de pistas, número de páginas—
> **porque la sonda ya los lee para los puntos 2, 3 y 4. Necesita fidelidad cuando el contenido
> solo existe como píxeles o como muestras**, porque entonces hay que decodificar.

Y eso **no es una excusa**, por dos medidas:

- **El precio es de tres órdenes de magnitud.** El contrato cuesta 0,43 ms; I9 cuesta 32 ms en
  el mejor caso y 2 454 ms en un raster de 1,8 Mpx. Meter I9 en el camino caliente multiplicaría
  el contrato por **75–5 700**.
- **La prueba en el otro sentido está medida en §5:** el miembro de la familia cuyo contenido
  perdido *sí* está declarado en metadatos —CSV→JSON que pierde una columna— **lo atrapa el
  contrato** (regla D4), no la fidelidad. La frontera no es arbitraria: cae exactamente donde
  el criterio dice.

**Lo que sí hay que corregir de la formulación de D2** es que el contrato no puede juzgar
*intención* que el pedido no exprese. Aparece dos veces en este informe y por dos caminos
distintos: I9 solo puede exigir texto porque el **origen** lo declara (`<text>`), y P5 solo
puede exigir texto tras un OCR porque ahora el **pedido** lo declara (`ocr: true`). **El punto 4
del contrato es tan bueno como lo que el pedido diga**, y ese es el mismo hueco que C11 cierra.

---

## 5. C10 — ¿es `resvg` un caso aislado o una familia?

**Es una familia.** Se fabricó un miembro por modalidad —«el envase es correcto y el contenido
no está»— y se anotó qué lo atrapa. Datos: `familia.json`.

| # | Miembro | Contrato (5 puntos) | Fidelidad | ¿Quién lo atrapa? |
|---|---|---|---|---|
| 1 | **SVG con `<text>` → PNG sin fuentes** (`resvg`, real) | `ok_parcial` | **`fallo`** | **I9** (la regla nueva) |
| 1c | *control:* el mismo SVG con Inkscape | `ok_parcial` | `ok` | nadie — **correcto** |
| 2 | **Vídeo con duración, geometría y códec correctos y TODO NEGRO** | `ok_parcial` | `aviso` | **V8**, y solo como **aviso**: 5,39 dB de PSNR |
| 3 | **PDF con texto → PDF rasterizado** (del propio patrón oro) | `ok_parcial` | **`fallo`** | **P2** (105 → 0 caracteres) |
| 4 | **CSV → JSON que pierde una columna** | **`fallo`** | `ok_parcial` | **el CONTRATO** (D4: cabecera `['id','nombre','notas']` → `['id','nombre']`) |
| 4b | *control:* CSV → JSON que pierde una fila | **`fallo`** | — | **el CONTRATO** (D1) |
| 5 | **Audio estéreo con el canal derecho SILENCIADO, destino con pérdida** | `ok_parcial` | `ok` | **NADIE** |
| 5b | el **mismo** fallo a un destino **sin pérdida** (FLAC) | `ok_parcial` | **`fallo`** | **A4** (el PCM no coincide) |
| 5c | *control:* el mismo estéreo sin silenciar nada | `ok_parcial` | `ok` | nadie — **correcto** |
| 6 | PDF con anotación `/Annots` → `gs pdfwrite` | `ok_parcial` | `ok` | *no es miembro*: **`gs` conserva la anotación** |

**Cinco conclusiones:**

1. **La familia existe y tiene al menos cinco miembros en cinco modalidades distintas**
   (vectorial, vídeo, PDF, datos tabulares, audio). `resvg` no es una rareza de un rasterizador:
   es la instancia más visible de un patrón.
2. **Tras añadir I9 sigue habiendo un miembro descubierto, y es nuevo:** un canal de audio
   silenciado hacia un destino **con pérdida**. El contrato ve 2 canales, la frecuencia correcta
   y la duración correcta; A4/A5 no aplican porque el destino es con pérdida y no hay PCM que
   comparar. **La cobertura depende del destino, no del fallo:** el mismo error a FLAC lo atrapa
   A4. Queda como **PENDIENTE** con una propuesta obvia y sin medir: comparar la **energía por
   canal** de entrada y salida (`ffmpeg -af astats`, una sonda externa, grupo C).
3. **El contrato solo atrapa al miembro cuyo contenido perdido está declarado en metadatos**
   (§4.4). Uno de cinco.
4. **La severidad importa tanto como la detección.** El vídeo enteramente negro sale como
   **aviso**, no como fallo, porque V8 está calibrada para «recodificación con pérdida». Un
   PSNR de **5,39 dB** no es una recodificación agresiva: es otra imagen. **PENDIENTE:** un
   suelo duro de PSNR por debajo del cual V8 debería ser `fallo` (el precedente existe: I7 ya
   lleva un suelo de 20 dB por esa misma razón).
5. **Un candidato no se materializó y hay que decirlo:** se esperaba que `gs pdfwrite` perdiera
   las anotaciones de un PDF. **No las pierde** (`/Annots` presente en entrada y en salida).
   Una hipótesis descartada es un resultado.

---

## 6. C11 — `P9` refutada, y un sustituto que sí separa

### 6.1 El corpus de validación

`P9` («longitud media de token ≥ 3,0 y menos del 50 % de tokens de una sola letra») estaba
calibrada sobre **5 puntos** y declarada no validada. Se validó contra:

- **32 capas OCR reales**, producidas con `gs -sDEVICE=pdfocr8`: 8 documentos
  (`patologico_escaneado`, `d1`, `d2`, `d3`, `d4`, `d4c`, `d4e`, `d4f`) × 2 idiomas
  (`spa`, `eng`) × 2 resoluciones (nativa y el doble). Sobremuestrear ×2 es **la forma barata de
  fabricar alucinaciones de verdad**, y funciona: `verificador-ghostscript.md` §5.3 ya había
  medido que en d3 el CER sube monótonamente con los ppp.
- **19 capas de texto legítimo**: 8 reales del repositorio (corpus, `gs pdfwrite`, Inkscape,
  Calibre, Pandoc, LibreOffice DOCX/ODT/XLSX) y **10 fabricadas cortas**, que son donde P9 puede
  dar falso positivo (una tabla, una fórmula, iniciales, una factura, un titular…). Se
  fabricaron con un escritor de PDF de 30 líneas en biblioteca estándar, porque en esta máquina
  no hay ningún motor de autoría.

Datos: `p9.json` y `texto/*.txt` (el texto de las 32 capas, para poder reanalizarlas sin volver
a pasar el OCR).

### 6.2 El veredicto: `P9` no sirve — **MEDIDO**

**Verdad de referencia para las capas OCR: CER con tildes > 50 % = ruido.**

| | Ruido (CER > 50 %) | Bueno (CER ≤ 50 %) |
|---|---:|---:|
| P9 dice «alucinación» | **1** | 0 |
| P9 dice «ok» | **11** | 20 |

**Sensibilidad: 1 de 12 = 8,3 %.** El único caso que detecta es exactamente aquel sobre el que
se calibró (`escaneado_d3`, `spa`, 100 ppp). **Los 11 que se le escapan:**

| Documento | idioma | ppp | CER | long. media | % 1 letra |
|---|---|---:|---:|---:|---:|
| `escaneado_d3` | spa | 200 | **588,9 %** | 3,14 | 26,2 % |
| `escaneado_d3` | eng | 100 | 366,7 % | 3,74 | 5,4 % |
| `escaneado_d3` | eng | 200 | **1 375,3 %** | 4,06 | 8,5 % |
| `escaneado_d4` | spa | 200 / 400 | 56,9 / 80,8 % | 4,03 / 5,89 | 26,9 / 21,1 % |
| `escaneado_d4` | eng | 200 / 400 | 62,0 / 82,5 % | 4,04 / 4,57 | 21,1 / 17,4 % |
| `escaneado_d4e` | spa | 200 / 400 | 138,4 / 403,0 % | 4,97 / 4,40 | 21,9 / 25,9 % |
| `escaneado_d4e` | eng | 200 / 400 | 433,6 / **1 354,3 %** | 5,61 / 4,39 | 4,1 / 5,8 % |

**Por qué falla, y es una lección sobre la señal, no sobre el umbral:** P9 supone que alucinar
produce **ruido corto**. A resoluciones altas Ghostscript alucina **palabras largas y
plausibles** (longitud media 4,4–5,6, por encima de la del texto legítimo del propio corpus),
y a veces **muchísimas**: `escaneado_d4e` a 400 ppp con `eng` devuelve **7 130 caracteres** de
invención. **Los tokens de una letra son un modo de alucinación, no *la* alucinación.**

**Y en el otro lado, falsos positivos.** De las 19 capas legítimas, 14 tienen ≥ 8 tokens (por
debajo P9 se declara no aplicable). De esas 14, **P9 marca 5 = 36 %**:

| Texto legítimo | tokens | long. media | % 1 letra | P9 |
|---|---:|---:|---:|---|
| `Col A  Col B  Col C / 1 2 3 / 4 5 6` | 12 | 1,50 | 75,0 % | **falso positivo** |
| `f(x) = a x^2 + b x + c / y = m x + n` | 15 | 1,33 | 86,7 % | **falso positivo** |
| `J. R. R. T. y C. S. L. / Ed. 3.a, vol. II` | 12 | 2,33 | 8,3 % | **falso positivo** |
| `a b c d e f g h i j k l` | 12 | 1,00 | 100,0 % | **falso positivo** |
| `Anexo B / Ref. 4/9 / pag. 2 de 3` | 8 | 2,62 | 37,5 % | **falso positivo** |
| *(los 8 documentos reales: corpus, gs, Inkscape, Calibre, Pandoc, LibreOffice ×3)* | 8–77 | 3,62–7,25 | 3,9–41,4 % | ok |

> **P9, tal y como está calibrada, queda REFUTADA. MEDIDO.** 8,3 % de sensibilidad sobre 32
> capas OCR reales y 36 % de falsos positivos sobre las capas legítimas donde se pronuncia.
> **Los 5 puntos de calibración eran el único sitio donde funcionaba.** Se deja implementada
> —con severidad `aviso` cuando no se pidió OCR y `fallo` cuando sí— **y marcada en el código
> como no fiable**, porque su especificidad sobre capas OCR sí es del 100 % (0 falsos positivos
> sobre 20 capas buenas): sirve como *aviso*, nunca como *criterio*.

**Nota sobre el control que fijó el margen:** V1 usó `corpus/pdf/tipico_texto.pdf` como el caso
legítimo más difícil y midió 4,04 de longitud media y **33,3 %** de tokens de una letra. Con la
sonda corregida del §8 el mismo fichero da **3,62 y 41,4 %**. **El margen entre «legítimo» y
«ruido» que P9 tenía (33,3 % → 61,8 %) era todavía más estrecho de lo que parecía: 41,4 % →
61,8 %.**

### 6.3 El sustituto: **acuerdo entre dos idiomas de OCR** — **MEDIDO**

Si el motor **reconoce**, dos pasadas con reconocedores distintos entregan casi lo mismo; si
**inventa**, cada una inventa una cosa distinta. Similitud con `difflib.SequenceMatcher`
(biblioteca estándar) entre la salida `spa` y la `eng` del mismo documento y resolución:

| Documento | ppp | acuerdo `spa`/`eng` | CER `spa` | verdad |
|---|---:|---:|---:|---|
| `patologico_escaneado` | 200 / 400 | **1,000** / **1,000** | 0,0 % | bueno |
| `escaneado_d1` | 150 / 300 | **1,000** / **1,000** | 0,0 % | bueno |
| `escaneado_d2` | 100 / 200 | 0,981 / 0,975 | 1,2 % | bueno |
| `escaneado_d4c` | 200 / 400 | 0,891 / **0,887** | 7,2 / 8,0 % | bueno |
| `escaneado_d4f` | 240 / 480 | 0,904 / 0,892 | 7,0 / 9,2 % | bueno |
| `escaneado_d4` | 200 / 400 | 0,577 / **0,700** | 56,9 / 80,8 % | **ruido** |
| `escaneado_d3` | 100 / 200 | 0,197 / 0,165 | 97,5 / 588,9 % | **ruido** |
| `escaneado_d4e` | 200 / 400 | 0,130 / 0,064 | 138,4 / 403,0 % | **ruido** |

**Separación perfecta: 16 de 16.** El peor caso bueno da **0,887** y el mejor caso malo da
**0,700**. Con umbral **0,80** no hay ni un error, y la banda vacía entre 0,700 y 0,887 es de
0,19 puntos — **cuatro veces el margen que tenía P9**.

**Su precio, dicho con todas las letras: cuesta una segunda pasada de OCR.** Sobre estos
documentos son 240–1 100 ms más (`verificador-ghostscript.md` §5.4). Eso lo pone claramente en
el grupo C, y solo para la arista de reparación. **PENDIENTE:** validarlo fuera de Ghostscript
(dos idiomas del mismo motor podrían acordar en su propio error) y sobre documentos con
vocabulario que `eng` no comparta.

### 6.4 `ocr: true` en el pedido — el cambio de firma

`referencia.json` P5 dice *«un PDF escaneado sin capa de texto sigue sin tenerla tras convertir:
no es un fallo salvo que se pidiera OCR»*, y hasta ahora **el pedido no llevaba ese dato**.
Implementado:

| `params.ocr` | Entrada sin texto, salida sin texto | Entrada sin texto, salida **con** texto |
|---|---|---|
| ausente / `false` | `P5 informativo`: no se exige texto | `P5 informativo` + **`P9 aviso`** si el texto es sospechoso |
| **`true`** | **`P5 fallo`**: se pidió OCR y no hay capa de texto | `P5 informativo` + **`P9 fallo`** si el texto es sospechoso |

**Lo que implica para quien invoque el verificador:** el orquestador tiene que **propagar la
intención**, no solo los parámetros del motor. Un `pedido` que solo lleva `{destino: "pdf"}`
para una reparación por OCR **es un pedido incompleto**, y el verificador ahora lo nota. Es la
misma conclusión que el §4.4: **el punto 4 del contrato vale lo que valga el pedido.**

---

## 7. C12 — el interruptor de V2

Implementado como `verificador.v2(False)` y `--sin-v2`. **Con el interruptor apagado, V2 se
declara NO CUBIERTA**, nunca aprobada. Suite completa sobre las 53 salidas del patrón oro,
`v2.json`:

| Suite de fidelidad (15 reglas) | Total | de eso, V2 | `ok` | `aviso` | `ok_parcial` | avisos |
|---|---:|---:|---:|---:|---:|---:|
| **con V2** | **70 692,6 ms** | **23 936,1 ms** | 37 | 8 | 8 | **8** |
| **sin V2** | **37 947,4 ms** | 0 | 32 | 8 | **13** | **8** |
| diferencia | **−32 745,2 ms** = **−46,3 %** | | | | +5 | **0** |

**Tres lecturas:**

1. **El interruptor ahorra el 46,3 % de la suite.** V1 midió V2 como el 36 % de la suite
   (+60,6 %); aquí sale el 46,3 % (equivalente a **+86,3 %** sobre la suite sin V2). **Los
   valores absolutos NO son comparables entre las dos sesiones** —la de V1 dio 46 332 ms y esta
   70 693 ms sobre las mismas 53 salidas, con dos agentes más trabajando (§9)—, pero **la
   conclusión se refuerza en la misma dirección**: cuanto más cargada está la máquina, más
   castiga la regla que decodifica el vídeo entero.
2. **No cambia ni un aviso: los 8 son exactamente los mismos ocho de los dos informes
   anteriores** (`tipico_mp3-to.flac` A4, `tipico_mp4-audio.flac` A5, `alpha_png-to.avif` I8,
   `alpha_png-to.jpg` I3+I7, `alpha_png-to.webp` I8, `trivial_png-to.webp` I8,
   `trivial_mp4-to-naive.gif` V9, `trivial_mp4-to.webm` V8). **I9 y P9 tampoco añaden ninguno.**
3. **Los `ok_parcial` suben de 8 a 13.** Son las 5 salidas de vídeo donde V2 era la única regla
   que aportaba cobertura. **Apagar una regla no debe convertirla en un aprobado**, y no lo
   hace.

**Recomendación, con su número:** V2 **encendida** en la suite de regresión (33 s de más sobre
53 ficheros son irrelevantes en CI) y **apagada** por defecto en un «verifica la fidelidad de
esta conversión» pedido por un usuario sobre un vídeo largo, donde `-count_frames` decodifica el
archivo entero.

---

## 8. Un fallo del propio verificador, reproducido y corregido

**Esto no estaba en el encargo. Salió solo, dos veces, mientras se medía otra cosa.**

`verificador-ghostscript.md` §5.9 anotó que **una vez** `txtwrite` devolvió 0 caracteres en vez
de 75, y que **no se reprodujo en 20 intentos**. Aquí volvió a aparecer: una capa OCR de
`escaneado_d4f` y dos PDF fabricados salieron vacíos en tandas distintas. Se midió con n grande
separando las dos hipótesis (`txtvacio.json`, `txtvacio2.json`):

| Tanda | Ruta | Vacíos | n | Tasa | Valores distintos | Mediana |
|---|---|---:|---:|---:|---|---:|
| `txtvacio.json` (3 PDF × 60) | **tubería** | **2** | 180 | 1,11 % | `[0, …]` | — |
| `txtvacio.json` | fichero | **0** | 180 | 0,00 % | — | — |
| `txtvacio2.json` | **tubería** (`-sOutputFile=-` + `capture_output`) | **4** | 250 | **1,60 %** | `[0, 107]` | 294,2 ms |
| `txtvacio2.json` | **fichero temporal** | **0** | 250 | 0,00 % | `[105]` | 286,7 ms |
| `txtvacio2.json` | **la sonda ya corregida** | **0** | 250 | 0,00 % | `[105]` | 292,9 ms |
| *(tanda intermedia, **sobrescrita**)* | tubería | **12** | 250 | **4,80 %** | `[0, 105]` | 184,9 ms |
| *(la misma tanda)* | fichero | **0** | 250 | 0,00 % | `[105]` | 184,6 ms |

**No es Ghostscript: es la captura por tubería.** En los datos que quedan guardados,
**6 vacíos de 430 por tubería (1,40 %) y 0 de 430 por fichero**; contando la tanda intermedia
que se sobrescribió al reejecutar el script —y que solo consta en el registro de ejecución—,
**18 de 680 frente a 0 de 680**. El coste es el mismo (184,6 frente a 184,9 ms en la misma
tanda). Nunca devolvía texto parcial: o los 105 caracteres o cero.

**Y hay un segundo defecto, silencioso, de la misma ruta:** por tubería el recuento es **107**
caracteres y por fichero **105**. La traducción de fin de línea del modo texto añade dos.
**P6 compara contra un umbral y P2 compara `sha256`**, así que ese ±2 no es cosmético.

**Por qué importa:** de `_gs_texto` cuelgan **P2 (severidad `fallo`)**, P5, P6 y ahora P9. Un
4,8 % de silencios convierte «el PDF conserva el texto» en un fallo aleatorio. **Corregido: la
sonda escribe a un fichero temporal y lo borra en `finally`.**

> La lección de método es la de siempre en este repositorio y aquí llega por tercera vez:
> **la sonda no es la verdad, es otra medida con sus propios defectos** —como `magick` devolviendo
> `2.7431e+303` para «sin alfa», `1e59` sobre un GIF, o `SSIM = 0` para imágenes idénticas.
> La novedad es que esta vez **el defecto era del propio verificador**.

---

## 9. Método y ruido

**Medianas, nunca medias.** n=15 en el coste del punto 5, n=9 en el de I9, n=250 en la sonda de
`txtwrite`. Calentamiento antes de cada tanda. **Los dos testigos de ruido** —monohilo para la
deriva dentro de la tanda, lanzamiento de proceso para el nivel de carga—, umbral del 20 % en
los dos.

**El testigo de proceso ganó su sueldo.** Con P1 en la GPU y P2 midiendo en CPU:

| Observación | Valor |
|---|---|
| Calibración en reposo del proyecto (`ffprobe -version`) | 26,5–26,8 ms |
| Calibración al empezar mis tandas | 27,4 · 28,4 · 31,5 · 32,2 · **81,9 ms** |
| Nivel máximo alcanzado durante una tanda | **×94,6** |
| **`ffprobe -version` llegó a agotar un timeout de 60 s** | y tumbó una tanda entera |

Hubo que **poner un tope al propio testigo** (20 s, devolviendo el tope y marcando `SUCIA`): un
testigo que puede tumbar la medición no es un testigo. Las tandas afectadas están etiquetadas
`SUCIA` en los `.json` con el motivo.

**Consecuencia para leer este informe:** las cifras **relativas dentro de una misma tanda** (en
proceso frente a `magick`, con V2 frente a sin V2, contrato con punto 5 frente a sin él) son
sólidas. Las **absolutas no son comparables con las de V1 ni con las de `coste-verificacion.md`**
—la suite de fidelidad da 70 693 ms aquí y 46 332 ms allí, sobre los mismos ficheros—. Donde
importa, se dice.

**No se usó la GPU ni se tomó su lock.** No se ha tocado `corpus/`, `repos/`,
`bench/salidas-referencia/referencia.json`, `bench/salidas-aristas/` (solo lectura), ningún
arnés compartido, ninguna variable de entorno del sistema, ni ningún documento maestro. La raíz
del repositorio quedó limpia.

---

## 10. Lo que este informe deja **PENDIENTE**

1. **El miembro descubierto de la familia:** audio con un canal silenciado hacia un destino con
   pérdida. Propuesta sin medir: comparar la **energía por canal** con `ffmpeg -af astats`
   (sonda externa, grupo C).
2. **El suelo duro de V8.** Un vídeo enteramente negro sale con **5,39 dB** y severidad `aviso`.
   I7 ya tiene un suelo de 20 dB por la misma razón; V8 no.
3. **Validar el acuerdo `spa`/`eng` fuera de Ghostscript** y sobre documentos con vocabulario
   que un reconocedor inglés no comparta. 16 pares, un solo motor.
4. **`P9` sigue en el código con severidad `aviso`/`fallo` y marcada como no fiable.** Decidir
   si se sustituye por el acuerdo entre idiomas o si se retira.
5. **I9 solo cubre PNG y no cubre PNG entrelazado ni destinos PDF.** Un SVG→PDF con el mismo
   fallo de fuentes no se detecta hoy (habría que rasterizar, que es grupo C sobre grupo C).
6. **El punto de cruce «en proceso / `magick`»** está medido en tres tamaños (0,08 / 0,32 /
   1,84 Mpx). La curva fina y el umbral exacto para cambiar de camino, sin medir.
7. **El punto 5 no cubre subdirectorios.** `censar_dir` no es recursivo: un motor que cree un
   directorio y escriba dentro se contabiliza como **una** entrada nueva de tamaño −1. Ningún
   caso del corpus lo hace, pero está declarado.
8. **El patrón oro no tiene ni una salida multifichero**, así que el «0 falsos positivos» del
   punto 5 se apoya en los cuatro casos fabricados del §3.2. Ampliar el patrón oro con una
   salida HLS y una secuencia `%d` cerraría el hueco.
9. **La discrepancia de líneas del §1** (3 859 publicadas frente a ~3 530 implícitas). No
   afecta a ninguna conclusión, pero rompe la trazabilidad del recuento entre informes.

---

## 11. Para quien consolide — qué cambia en los documentos maestros

**No he tocado ningún maestro.** Esto es lo que hay que llevarse, con su fuente aquí.

| Documento | Qué dice hoy | Qué hay que añadir |
|---|---|---|
| `PLAN-ORQUESTADOR.md` §4.2 | El quinto punto está **declarado** | **Implementado y medido: +0,047 ms con R18 (+11,0 % del contrato, 0,036 % de convertir); 0 falsos positivos sobre las 36 órdenes reejecutadas; atrapa los dos casos de fuga con severidades distintas** (§2, §3) |
| `PLAN-ORQUESTADOR.md` §4.6 R18 | Directorio de trabajo desechable, declarado | **R18 deja de ser higiene y pasa a ser requisito de coste: sin él el punto 5 cuesta ×8,6 el contrato sobre un directorio de 1 000 ficheros** (§2.2) |
| `PLAN-ORQUESTADOR.md` §5 (reglas de diseño) | «Verificar leyendo cabeceras en proceso, no con `ffprobe`» | **Matizar: vale para cabeceras y para rasters pequeños. Para leer PÍXELES, `magick` gana a partir de ~0,1 Mpx, y ×20,5 a 1,8 Mpx** (§4.3) |
| `PLAN-ORQUESTADOR.md` §5 | «Verificar la salida siempre» (4 puntos) | **El punto 5 es el primero que NO es verificable a posteriori: la verificación tiene que vivir dentro de la conversión** (§3.3) |
| `HUECOS.md` §1 (fallos documentados) | 7 fallos en 6 proyectos; el 8º (`resvg`) pasa los cuatro puntos | **El 8º queda atrapado por I9 (0,00 % de tinta frente a 20,01 %). Y no es aislado: la familia tiene al menos 5 miembros y uno sigue sin cubrir** (§4, §5) |
| `HUECOS.md` §1 | Prototipo: 3 859 líneas, 0 FP sobre 53 | **4 185 líneas. Siguen 0 falsos positivos en las cuatro configuraciones y 12/12 fallos atrapados. Sin censo, 49 de las 53 bajan a `ok_parcial`** (§3.3) |
| `verificador-ghostscript.md` §5.8 (P9) | Propuesta calibrada sobre 5 puntos, no validada | **REFUTADA: 8,3 % de sensibilidad sobre 32 capas OCR reales y 36 % de falsos positivos sobre las legítimas. Sustituto medido: acuerdo entre dos idiomas de OCR, 16/16** (§6) |
| `verificador-ghostscript.md` §5.9 (`txtwrite` vacío) | Observado una vez, no reproducido en 20 intentos | **REPRODUCIDO Y LOCALIZADO: 6 vacíos de 430 por tubería, 0 de 430 por fichero, al mismo coste. Corregido en `_gs_texto`** (§8) |
| `verificador-ghostscript.md` §2.2 (V2) | V2 necesita interruptor propio | **Implementado (`--sin-v2`). Ahorra el 46,3 % de la suite sin cambiar ni un aviso; los `ok_parcial` suben de 8 a 13** (§7) |
| `aristas-nominales.md` §11.3 (C14) | El vocabulario de firmas es corto | **Confirmado con un caso: la sonda clasifica un `.html` y un `.svg` como CSV. Con el HTML el contrato acierta por casualidad, con un `[p3 D2 fallo]` que no tiene nada que ver** (§3.1). **CERRADO el 22/08 (`bench/firmas-contrato.md` §8.2): `xml`, `html`, `svg`, `postscript` y `rtf` tienen ya firma y categoría propias.** |
| Metodología (todos) | Dos testigos de ruido | **El testigo de proceso necesita su propio tope: `ffprobe -version` llegó a agotar 60 s y a tumbar una tanda. Nivel máximo observado: ×94,6** (§9) |

---

## 12. Índice de datos crudos

Todo en `bench/salidas-quinto-punto/`, con su `MANIFIESTO.md` (355 KB, todo texto; los dos PNG
grandes están borrados con su `sha256` y su orden de reproducción).

| Fichero | Contenido | Sección |
|---|---|---|
| `medir_p5.py` | El banco. Copia adaptada de `medir_gs.py`, que no se toca. Once subcomandos, los dos testigos | — |
| `txtvacio2.py` | La sonda dedicada al `txtwrite` vacío: 250 × 3 rutas | §8 |
| `coste_p5.json` | Coste del punto 5 en 15 + 7 configuraciones, n=15 | §2 |
| `ordenes39.json` | Las 39 órdenes del patrón oro reejecutadas con censo | §3.3 |
| `fuga.json` | Los dos casos de E1, con veredicto de 4 y de 5 puntos | §3.1 |
| `multi.json` | Cuatro salidas legítimamente multifichero | §3.2 |
| `contrato53.json` | Las 53 salidas, 2 motores × 2 modos de censo | §3.3 |
| `fallos5.json` | Los 5 fallos documentados, 2 motores. 12/12 | §3.3 |
| `i9.json` | Discriminación de I9 (6 casos) y coste por tamaño, con `magick` al lado | §4 |
| `familia.json` | Los 10 miembros y controles de la familia | §5 |
| `p9.json` + `texto/*.txt` | 32 capas OCR reales, 19 legítimas, el acuerdo `spa`/`eng` y el texto de cada capa | §6 |
| `v2.json` | La suite de fidelidad con y sin V2, con detalle por salida | §7 |
| `txtvacio.json`, `txtvacio2.json` | 180 + 750 ejecuciones de `txtwrite` por las tres rutas | §8 |


