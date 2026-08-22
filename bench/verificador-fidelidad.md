# El verificador de FileX, hasta la fidelidad: `min(alfa)` sin `magick` y las reglas que exigen píxeles

**Fecha:** 21 de agosto de 2026
**Objeto:** cerrar los cuatro PENDIENTE de `bench/coste-verificacion.md` §1.4 — `min(alfa)` en proceso, las reglas de fidelidad de `referencia.json`, el umbral de `txtwrite` y los dos puntos ciegos del §7.
**Entregables:** este informe, `bench/scripts/verificador.py` extendido y los datos crudos en `bench/salidas-verificacion-fidelidad/`.

> Cada afirmación va marcada **MEDIDO** o **PENDIENTE**.
> Nada de lo que había se ha reescrito: son 1.542 líneas **añadidas** y 10 sustituidas (firmas de función y CLI). El contrato de los cuatro puntos sigue byte a byte donde estaba.

---

## 0. Las seis líneas que importan

1. **`min(alfa)` no necesita decodificar la imagen: necesita decodificar *el canal alfa*.** **MEDIDO.** En proceso, el peor caso imaginable —un PNG de 1920×1080 **RGBA de 16 bits enteramente opaco**, que obliga a recorrerlo entero— cuesta **66,0 ms** frente a los **734,6 ms** de `magick -format "%[fx:minima.a]"` que documentó `coste-verificacion.md`, y frente a los **376 ms** que da esa misma orden remedida hoy. El caso mejor (transparencia real en las primeras filas) cuesta **0,23 ms**: **×226**.
2. **En 7 de los 12 casos medidos no se lee un solo píxel.** **MEDIDO.** Un PNG sin `tRNS` ni canal alfa, un JPEG, un WebP con pérdida sin `ALPH`, un TIFF sin `ExtraSamples`: la cabecera lo decide, en **0,05–0,17 ms**, hasta **×13.569** frente a `magick`.
3. **Cubrir WebP costó un decodificador VP8L completo: 437 líneas.** **MEDIDO.** El plano alfa de un WebP con pérdida va codificado como una imagen sin pérdida VP8L (Huffman + caché de color + referencias hacia atrás + cuatro transformaciones). No hay atajo. AVIF, TIFF comprimido y GIF **devuelven «no evaluable»**, con el motivo escrito.
4. **La fidelidad cuesta 1.100 veces más que el contrato y hay que sacarla del camino caliente.** **MEDIDO.** Las 53 salidas: **28.858 ms** de fidelidad frente a **26,1 ms** de contrato. Sobre las 39 órdenes del patrón oro, la fidelidad es el **38,5 %** del coste de convertir; el contrato sigue siendo el **0,032 %**.
5. **Los dos puntos ciegos están cerrados, y uno de ellos gratis.** **MEDIDO.** `alpha_png-to.jpg` aplanado sobre negro se detecta con **una** invocación de `magick` que lee **un píxel** (25,9 ms). La paleta genérica de `trivial_mp4-to-naive.gif` se detecta **en proceso, en 0,18 ms**, porque una paleta genérica es una rejilla regular y una calculada sobre el clip no lo es.
6. **Sigue habiendo 0 falsos positivos sobre las 53 salidas del patrón oro**, con los dos motores y en las tres configuraciones de alfa. **MEDIDO.** Y ahora, sin `min(alfa)`, **11 de las 53 se declaran `ok_parcial`** en vez de aprobadas: el verificador dice cuándo no sabe.

---

## 1. `min(alfa)` en proceso — el caso caro, resuelto

`min(alfa)` es **el único dato del contrato que exige decodificar píxeles**. Lo necesita la regla I2 y con ella la trampa nº 1 del proyecto: `corpus/imagen/tipico.png` **declara** canal alfa y es **enteramente opaco**, así que exigir que se conserve sería un falso positivo. El prototipo lo esquivaba inyectándolo desde la caracterización de la entrada.

### 1.1 Cómo: dos observaciones que cambian el coste de orden

**(a) El canal alfa se puede reconstruir sin tocar R, G y B.**
Los filtros de PNG (RFC 2083 §6) operan **byte a byte con desplazamiento `bpp`**: el byte *i* de una fila solo depende de bytes con **el mismo residuo módulo `bpp`** en esa fila y en la anterior. Por tanto el carril del alfa —1 de cada 4 bytes en RGBA de 8 bits, 2 de cada 8 en RGBA de 16— se desfiltra **por separado**, con Paeth incluido. Para `tipico.png` eso es leer 4,1 MB de carril en vez de 16,6 MB de píxel.

**(b) «Esta fila es 100 % opaca» se decide sin reconstruir nada.**
Si la fila anterior es toda `0xFF`, el carril alfa **filtrado** de una fila opaca tiene una forma fija que depende solo del tipo de filtro:

| filtro | primer byte | resto | por qué |
|---|---|---|---|
| 0 None | `0xFF` | `0xFF` | `recon = filt` |
| 1 Sub | `0xFF` | `0x00` | `recon = filt + izq` |
| 2 Up | `0x00` | `0x00` | `recon = filt + arriba` |
| 3 Average | `0x80` | `0x00` | `recon = filt + (izq+arriba)>>1` |
| 4 Paeth | `0x00` | `0x00` | el predictor de Paeth con `a=b=c=255` da 255 |

*(en la primera fila, con la «anterior» a ceros, la tabla es `(255,255) / (255,0) / (255,255) / (255,128) / (255,0)`)*

La comprobación es **`lane[0] == b0 and lane[1:] == bytes([resto])*(n-1)`**: dos comparaciones de bytes en C, no un bucle en Python. Es **exacta**, no heurística: el patrón se cumple si y solo si la fila es opaca. En cuanto falla —hay alfa real— se baja al carril lento con la fila anterior conocida (`0xFF`), se reconstruye de verdad y se **corta en el primer píxel no opaco**.

El resultado es que el coste del peor caso es prácticamente **el de descomprimir**: el suelo de `zlib` sobre los 16,6 MB de `tipico.png` es **47,2 ms** de los **66,0 ms** totales (**72 %**). No queda mucho que optimizar sin salir de Python.

### 1.2 Qué formatos cubre — **MEDIDO**

| Formato | Vía | ¿Exacto? | Nota |
|---|---|---|---|
| PNG sin alfa ni `tRNS` (ct 0/2/3) | cabecera | sí | no se lee un solo píxel |
| PNG RGBA / gris+alfa, 8 y 16 bits | carril alfa | **sí** | carril rápido + corte temprano |
| PNG de paleta con `tRNS`, 8 bits | tabla `translate` sobre los índices | **sí** | `bytes.translate` + `min` en C |
| PNG de paleta con `tRNS`, 1/2/4 bits | tabla sobre el byte empaquetado | **sí** | se enmascaran los bits de relleno de la última celda |
| PNG con `tRNS` de color clave (ct 0/2) | — | **NO EVALUABLE** | no hay canal alfa: exige comparar el valor de cada píxel |
| PNG entrelazado (Adam7) | — | **NO EVALUABLE** | no implementado |
| WebP con pérdida sin `ALPH` | cabecera | sí | no hay alfa |
| WebP sin pérdida (VP8L) con `alpha_is_used=0` | cabecera VP8L | sí | el codificador pone ese bit a 0 solo si todos los alfa valen 255 |
| WebP con `ALPH`, compresión 0 | plano crudo + desfiltrado | **sí** | filtros ninguno/horizontal/vertical/gradiente |
| WebP con `ALPH`, compresión 1 | **decodificador VP8L** | **sí** | el plano alfa va en el canal verde de una imagen VP8L |
| WebP sin pérdida (VP8L) con alfa | **decodificador VP8L** | **sí** | ARGB completo |
| WebP animado | — | **NO EVALUABLE** | no implementado |
| JPEG, BMP | definición del formato | sí | no admiten alfa |
| TIFF sin `ExtraSamples` | `SamplesPerPixel` | sí | |
| TIFF con `ExtraSamples` | — | **NO EVALUABLE** | exige descomprimir las bandas y deshacer el predictor |
| AVIF / HEIF | — | **NO EVALUABLE** | el plano alfa es un flujo AV1/HEVC: decodificador de vídeo completo |
| GIF | — | **NO EVALUABLE** (con cota) | el GCE **declara** un índice transparente; saber si se **usa** exige descomprimir el LZW |

**«No evaluable» es una respuesta, no un fallo.** Se devuelve con `evaluable: false` y `motivo`, se propaga a la `cobertura` del punto 4 y convierte el veredicto en `ok_parcial`. Un verificador que devolviera `alfa_min = 1.0` («no vi transparencia») donde en realidad no supo mirar repetiría el fallo de `markitdown-mcp`.

Del GIF se devuelve además `cota_alfa_min: 0.0` como información, **pero no como medida**: «declara» no es «tiene».

### 1.3 Coste — **MEDIDO** (mediana de n=9, etiqueta `limpia`)

| Caso | Fichero | En proceso | `magick` | Factor | Vía |
|---|---:|---:|---:|---:|---|
| PNG 1920×1080 RGBA16 OPACO (peor caso) | `tipico.png` (42.855 B) | **66,03 ms** | 376,3 ms | **x5,8** | carril alfa (2 de cada 8 bytes) |
| PNG 200×200 paleta+tRNS con alfa real (mejor caso) | `alpha.png` (2.780 B) | **0,23 ms** | 47,5 ms | **x226,1** | paleta+tRNS |
| PNG 4000×3000 RGB16 sin alfa | `16bit_tif-to-d16.png` (59,0 MB) | **0,09 ms** | 1.194,1 ms | **x13.569** | cabecera |
| PNG 64×64 paleta 1 bit sin alfa | `trivial.png` (316 B) | **0,15 ms** | 39,1 ms | **x289,5** | cabecera |
| PNG 200×200 paleta+tRNS (salida) | `alpha_png-to.png8.png` (2.780 B) | **0,21 ms** | 48,0 ms | **x211,5** | paleta+tRNS |
| WebP con pérdida sin alfa | `tipico.webp` (12.796 B) | **0,10 ms** | 208,1 ms | **x1.945** | cabecera |
| WebP con pérdida + ALPH sin pérdida (VP8L) | `alpha_png-to.webp` (2.496 B) | **8,01 ms** | 44,3 ms | **x5,4** | ALPH comprimido sin pérdida (VP8L) |
| WebP sin pérdida (VP8L) sin alfa | `trivial_png-to-lossless.webp` (42 B) | **0,13 ms** | 36,1 ms | **x340,9** | cabecera VP8L (alpha_is_used=0) |
| JPEG (el formato no admite alfa) | `tipico_png-to.jpg` (40.963 B) | **0,07 ms** | 194,4 ms | **x4.861** | el formato no admite alfa |
| AVIF con alfa (no evaluable en proceso) | `alpha_png-to.avif` (1.670 B) | **0,05 ms** | 53,4 ms | **x620,7** | **NO EVALUABLE** |
| TIFF 16 bits sin alfa | `patologico_16bit.tif` (68,7 MB) | **0,17 ms** | 797,8 ms | **x6.282** | ExtraSamples/SamplesPerPixel |
| GIF con transparencia declarada | `trivial_mp4-to-palette.gif` (595,6 KB) | **0,08 ms** | 1.772,8 ms | **x23.326** | bloque de control gráfico |

| Fichero | `min(alfa)` en proceso | `magick %[fx:minima.a]` | Verdad de `referencia.json` |
|---|---|---|---|
| `tipico.png` | 1,00 | `1` | `alfa_min_max` = `1 / 1` → **coincide** |
| `alpha.png` | 0,00 | `0` | `alfa_min_max` = `0 / 1` → **coincide** |
| `16bit_tif-to-d16.png` | 1,00 | `2.7431e+303` | sin alfa: 1,0 |
| `trivial.png` | 1,00 | `2.7431e+303` | sin alfa: 1,0 |
| `alpha_png-to.png8.png` | 0,00 | `0` | `alfa_min_max` = `0 / 1` → **coincide** |
| `tipico.webp` | 1,00 | `2.7431e+303` | sin alfa: 1,0 |
| `alpha_png-to.webp` | 0,00 | `0` | `alfa_min_max` = `0 / 1` → **coincide** |
| `trivial_png-to-lossless.webp` | 1,00 | `2.7431e+303` | sin alfa: 1,0 |
| `tipico_png-to.jpg` | 1,00 | `2.7431e+303` | sin alfa: 1,0 |
| `alpha_png-to.avif` | **no evaluable** | `0` | `alfa_min_max` = `0 / 1` → **se declara no evaluable** |
| `patologico_16bit.tif` | 1,00 | `2.7431e+303` | sin alfa: 1,0 |
| `trivial_mp4-to-palette.gif` | **no evaluable** | `100000000000000000000000000000000000000000000000000000000000` | se declara no evaluable |

Notas:

- **Los 734,6 ms de `coste-verificacion.md` §1.4 no son reproducibles hoy tal cual**: la misma orden da 376 ms en esta sesión. La familia de órdenes equivalentes va de 369 ms (`-alpha extract -format "%[fx:minima]"`) a 1.309 ms (`identify -verbose`), n=9. Se reportan las dos cifras y se calcula el factor contra la remedida, que es la conservadora.
- **`magick` da `2.7431e+303` cuando no hay canal alfa** (su representación Q16-HDRI de «sin alfa»), y **`1e59` sobre un GIF**. No es un valor utilizable sin postproceso; el lector en proceso devuelve `1.0` con `tiene_alfa: false`.
- El valor calculado en proceso **coincide con `referencia.json` en los 8 casos con verdad de referencia** (`alfa_min_max`), incluidos `alpha.png` = 0 y `tipico.png` = 1.
- El decodificador VP8L se validó además contra siete WebP generados a propósito con `-define webp:lossless=true`, `-quality 60`, `webp:alpha-compression=0`, `webp:alpha-filtering=2` y dimensiones impares (137×91): **min(alfa) idéntico a `magick` en los siete**.
- La tabla `kCodeToPlane` de VP8L (120 códigos de plano) **no se copió: se genera** ordenando los desplazamientos `(dx, dy)` por distancia euclídea. Coincide con la de libwebp en las 120 entradas — comprobado.

### 1.4 Dónde ponerlo: una vez por **entrada**, nunca por salida — **MEDIDO**

Calcular `min(alfa)` de la entrada para las 53 salidas cuesta **320,9 ms**, y solo 11 de las 53 lo pagan. Pero solo hay **dos entradas** de imagen con alfa en el corpus, y producen 11 salidas entre las dos:

| Entrada | Salidas que produce | Coste una vez | Coste pagado por salida |
|---|---:|---:|---:|
| `tipico.png` (1920×1080 RGBA16, opaco) | 5 | 66,0 ms | 5 × 66,0 ms |
| `alpha.png` (200×200 paleta+tRNS) | 6 | 0,23 ms | 6 × 0,23 ms |
| **total** | **11** | **66,3 ms** | **320,9 ms** |

**Cachear por hash de contenido divide el coste por 4,8.** Es exactamente la recomendación nº 3 del §4 de `coste-verificacion.md`, ahora con la cifra: el `min(alfa)` en proceso **no** pertenece al camino caliente por salida; pertenece a la caracterización de la entrada.

Por eso `sondear()` **nunca** lo calcula por defecto. Hay que pedirlo: `--alfa` en la CLI, `alfa=True` en `verificar()`.

---

## 2. Las reglas de fidelidad

`referencia.json` define **46 reglas de regresión**. El contrato de `PLAN-ORQUESTADOR.md` §4.2 más el punto 4 cubría las que se deciden con cabeceras. Las que faltaban son las que exigen **comparar píxeles o muestras**.

### 2.1 Qué se implementó

| Regla | Qué comprueba | Cómo | Severidad |
|---|---|---|---|
| **I3** | el aplanado de un alfa no trivial va sobre **blanco**, no sobre negro | `min(alfa)` **en proceso** localiza el primer píxel 100 % transparente de la entrada; **una** invocación de `magick` lee ese píxel en la salida | aviso |
| **I6** | conversión sin pérdida declarada → píxeles idénticos | `magick compare -metric RMSE` == 0 | fallo |
| **I7** | conversión con pérdida → PSNR ≥ 40 dB | `magick compare -metric PSNR` | aviso |
| **I8** | grafismo a un destino que admite sin pérdida | origen de paleta + destino WebP/AVIF con pérdida (en proceso) | aviso |
| **V6** | remux sin recodificar → hash **por píxel** idéntico | md5 de la última columna de `ffmpeg -f framemd5` | fallo si se pidió `-c copy` |
| **V8** | recodificación → PSNR de luminancia ≥ 40 dB | `ffmpeg -lavfi psnr` | aviso |
| **V9** | la paleta del GIF se calcula sobre el clip | **en proceso**: ¿es la tabla de color una rejilla regular? | aviso |
| **A4** | cadena sin pérdida → PCM idéntico bit a bit | `ffmpeg -f md5 -c:a pcm_s16le` | fallo |
| **A5** | extraer audio con `-c:a copy` → PCM idéntico | igual, contra la pista embebida | aviso |
| **P2** | PDF → PDF conserva el texto | sha256 del texto de `gs -sDEVICE=txtwrite` | fallo |
| **P6** | «tiene texto» = **≥ 10 caracteres**, no > 0 | recuento sobre `txtwrite` | informativo |

**No se usa `-metric SSIM`.** En esta build (`ImageMagick 7.1.2-21 Q16-HDRI`) devuelve **0 para imágenes idénticas**: se comporta como disimilitud, no como similitud. Solo PSNR y RMSE. **MEDIDO.**

**No se mira el tamaño del fichero en ninguna regla.** El GIF de paleta genérica pesa un 35 % *menos* que el bueno (395 KB frente a 610 KB) precisamente porque descarta color. V9 mira la paleta, no los bytes.

### 2.2 Coste individual — **MEDIDO** (mediana n≥9, `limpia`)

| Regla | Caso medido | Mediana | Frente al contrato (0,37 ms) | Sonda |
|---|---|---:|---:|---|
| I3 | color del aplanado: `magick` leyendo **un píxel** (JPEG 200×200) | **25,93 ms** | x70 | `magick` |
| I6 | RMSE, PNG de paleta 200×200 | **33,47 ms** | x90 | `magick` |
| I6 | RMSE, TIFF de 72 MB frente a PNG de 61 MB (4000×3000, 16 bits) | **1.405,00 ms** | x3797 | `magick` |
| I7 | PSNR, 1920×1080 | **306,91 ms** | x829 | `magick` |
| I7 | PSNR sobre blanco, 200×200 (dos composiciones en la misma orden) | **39,39 ms** | x106 | `magick` |
| V9 | **paleta del GIF, EN PROCESO** | **0,18 ms** | x0,48 | **en proceso** |
| V6 | `framemd5` de trivial.mp4 (540 KB, 90 fotogramas) | **129,18 ms** | x349 | `ffmpeg` |
| V6 | `framemd5` de tipico.mp4 (16 MB, 600 fotogramas) | **3.052,32 ms** | x8250 | `ffmpeg` |
| V8 | PSNR de vídeo 640×360 (trivial → webm) | **121,34 ms** | x328 | `ffmpeg` |
| V8 | PSNR de vídeo 1920×1080 (tipico → webm), n=5 | **1.753,62 ms** | x4740 | `ffmpeg` |
| A4 | md5 del PCM (WAV de 706 KB, 8 s) | **51,09 ms** | x138 | `ffmpeg` |
| A4 | md5 del PCM (FLAC de 104 KB, 8 s) | **37,65 ms** | x102 | `ffmpeg` |
| A5 | md5 del PCM de la pista de un MP4 de 16 MB | **55,46 ms** | x150 | `ffmpeg` |
| P6 | `txtwrite` sobre un PDF de texto (3 KB) | **174,80 ms** | x472 | `gs` |
| P6 | `txtwrite` sobre un PDF rasterizado (6 KB) | **199,64 ms** | x540 | `gs` |
| P6 | `txtwrite` sobre un PDF escaneado (8,5 MB) | **316,02 ms** | x854 | `gs` |
| **CONTRATO** | **los cuatro puntos, en proceso (referencia)** | **0,37 ms** | x1 | - |

**La lectura:** salvo V9, **cada regla de fidelidad cuesta entre 70 y 8.200 veces el contrato completo**. La única que se paga sin pensarlo es V9, porque es la única que no lanza un proceso.

### 2.3 Las excepciones justificadas por datos

`coste-verificacion.md` §7 avisaba: la primera versión del contrato, escrita desde la especificación, dio **9-10 falsos positivos (17-19 %)**. Con las reglas de fidelidad ha pasado lo mismo. Estas son las seis correcciones que hicieron falta, cada una con el dato que la motiva:

| # | Falso positivo | Causa | Corrección | Líneas |
|---|---|---|---|---|
| 1 | `alpha_png-to-flat.jpg` da **1,9 dB** de PSNR | se comparaba un RGBA contra un RGB: los píxeles transparentes de la entrada no tienen color definido | componer **los dos lados sobre blanco** cuando uno tiene alfa y el otro no. Reproduce las cifras del patrón oro: AVIF 38,78 dB y WebP 43,87 dB, exactas | 12 |
| 2 | `alpha_png-to-flat.jpg`, ya compuesto, da **35,5 dB** < 40 | el umbral de 40 dB de I7 está calibrado **«para fotografía»** (nota de la propia regla); `alpha.png` es un grafismo de 210 colores con bordes duros | si el origen es **de paleta** (indicio exacto y en proceso: `color type 3` del PNG), la caída se declara `informativo` con el motivo. **Con suelo de 20 dB**: `alpha_png-to.jpg` da 0,70 dB porque está aplanado sobre negro, y eso **sí** es un hallazgo | 8 |
| 3 | `16bit_tif-to.jpg` da **35,3 dB** y `16bit_tif-to.webp` **34,8 dB** | una entrada de 16 bits cuantizada a 8 tiene un techo de PSNR que no depende del motor: el propio PNG de 8 bits, conversión impecable, se queda en 59,0 dB | excepción si la profundidad de origen > 8 bits y el PSNR ≥ 30 dB | 3 |
| 4 | `alpha_png-to.avif` da **39,8 dB** < 40 | `referencia.json` → `perdidas`: *«AVIF comprime el plano alfa con pérdida… incluso un alfa 100 % opaco se degrada a 71,4 dB»* | excepción para AVIF/HEIF cuando la entrada tiene alfa | 3 |
| 5 | `tipico_mp3-to.flac`: **A4 fallo**, el PCM no coincide | ffmpeg escribe el FLAC a **24 bits** (regla A6, «profundidad inflada»). Medido: `tipico.mp3` → `f5ddaa64…` en s16; su FLAC → `984b4619…`. La información se conserva; lo que cambia es el redondeo al medir | si el destino es sin pérdida **y** su profundidad supera la efectiva del origen (16 si el origen es con pérdida), baja a `aviso` con esa explicación | 12 |
| 6 | `tipico_mp4-to.mkv`: **A4 fallo** en un remux `-c copy` | la *edit list* de MP4 recorta el retardo del codificador AAC y **Matroska no puede expresarla** | cuando se declaró `copia`, se comprueba **exactamente**: se vuelca el PCM de los dos y se mira si uno es sufijo del otro. **Medido: `b[2048:] == a` byte a byte — 512 muestras de *priming*, ni una más.** Pasa a `informativo` con el número de muestras | 30 |

Y dos correcciones de despacho, no de umbral:

| # | Síntoma | Corrección | Líneas |
|---|---|---|---|
| 7 | **V9 no se ejecutaba nunca**: un GIF es categoría `imagen` para la sonda, y V9 se despachaba por categoría | despachar V9 por el **destino** (`gif`), no por la categoría de la salida | 3 |
| 8 | `tipico_texto_pdf-to-p1.jpg` marcaba I3 como «no cubierta» | un PDF no tiene canal alfa que aplanar: I3 solo aplica si la **entrada** es una imagen | 3 |

**Suma: 74 líneas de excepciones justificadas por datos.** Ninguna es deducible leyendo `referencia.json`; **todas** salieron de ejecutar contra el patrón oro. Es el mismo porcentaje que en el contrato: **el 4,8 % de las 1.542 líneas añadidas**, para bajar de 6 falsos positivos a 0.

---

## 3. La separación contrato / fidelidad

Este es el entregable de diseño. La propuesta es de **tres** grupos, no de dos, porque `min(alfa)` no encaja en ninguno de los dos.

### 3.1 Los tres grupos

| Grupo | Cuándo corre | Qué incluye | Coste por fichero | Ratio frente a convertir |
|---|---|---|---:|---:|
| **A — Contrato** | **siempre**, en serie, en el mismo hilo que hizo la conversión | puntos 1-4 de §4.2 + «pedido frente a obtenido»; V9 (paleta del GIF) | **0,37 ms** | **0,032 %** (las 39 órdenes) |
| **B — Caracterización de la entrada** | **una vez por entrada**, cacheada por hash de contenido | `min(alfa)` en proceso | **0,23–66,0 ms** por entrada con alfa; **0,05–0,14 ms** si no lo tiene | 0,089 % |
| **C — Fidelidad** | **bajo demanda** o en la **suite de regresión**, nunca en el lote interactivo | I3, I6, I7, I8, V6, V8, A4, A5, P2, P6 | **207 ms** (mediana de las 39 salidas evaluables) | **38,5 %** |

Sobre las **53 salidas del patrón oro** completas:

| Grupo | Total | Frente al contrato | Frente a convertir (74,9 s) |
|---|---:|---:|---:|
| A — Contrato, en proceso, en serie | **26,1 ms** | ×1 | **0,032 %** |
| A + V9 (solo los 2 GIF) | **26,5 ms** | ×1,01 | 0,035 % |
| B — `min(alfa)`, cacheado por entrada | **66,3 ms** | ×2,5 | 0,089 % |
| B — `min(alfa)`, pagado por salida (lo que **no** hay que hacer) | 320,9 ms | ×12,3 | 0,43 % |
| **C — Fidelidad completa** | **28.858 ms** | **×1.106** | **38,5 %** |

### 3.2 Cómo se invoca cada grupo — reproducible sin leer el código

Los tres grupos son tres invocaciones distintas de `bench/scripts/verificador.py`, y **cada uno devuelve su propio veredicto y su propia cobertura**. `python verificador.py --help` los describe.

**Grupo A — contrato.** Es el modo por defecto: no hay bandera que activarlo.

```
python bench/scripts/verificador.py \
    --salida bench/salidas-referencia/imagen/alpha_png-to.jpg \
    --entrada corpus/imagen/alpha.png --destino jpg
```
```
CONTRATO (grupo A)     OK_PARCIAL bench/salidas-referencia/imagen/alpha_png-to.jpg
  [p4 I2 informativo] se descarta el canal alfa y min(alfa) de la entrada no
                      esta calculado: la regla I2 no es evaluable
  cobertura: PARCIAL (sin cubrir: 4_alfa)
  ms: {'total': 0.62, 'logica': 0.06}
```

Veredicto: `ok` / `aviso` / **`ok_parcial`** / `fallo`. Aquí sale `ok_parcial` **a propósito**: sin el grupo B no se sabe si el alfa de la entrada era trivial, y eso no se da por bueno.

**Grupo B — caracterización de la entrada.** Dos formas: el dato suelto, o integrado en el contrato con `--alfa`.

```
python bench/scripts/verificador.py --alfa-min corpus/imagen/alpha.png
```
```json
{"formato": "png", "evaluable": true, "exacto": true, "tiene_alfa": true,
 "alfa_min": 0.0, "primer_transparente": [0, 0], "filas_leidas": 1,
 "via": "paleta+tRNS", "ms": 0.236, "alfa_no_trivial": true}
```

```
python bench/scripts/verificador.py --salida … --entrada … --destino jpg --alfa
```
```
CONTRATO (grupo A)     OK         …/alpha_png-to.jpg
  [p4 I2 informativo] jpg no admite alfa: perdida inevitable
  cobertura: completa
  ms: {'alfa': 0.295, 'total': 0.924, 'logica': 0.073}
```

Con `--alfa` el veredicto sube de `ok_parcial` a **`ok`** y la cobertura pasa a completa: la regla I2 ya es evaluable. Añade 0,30 ms sobre `alpha.png` y 66 ms sobre `tipico.png`. `--exacto` (solo con `--alfa-min`) fuerza el recorrido completo para dar el mínimo exacto en vez de cortar en el primer píxel no opaco.

**Grupo C — fidelidad.** `--fidelidad` ejecuta A y C e imprime **los dos bloques**; `--solo-fidelidad` ejecuta solo C.

```
python bench/scripts/verificador.py \
    --salida bench/salidas-referencia/imagen/alpha_png-to.jpg \
    --entrada corpus/imagen/alpha.png --destino jpg --alfa --fidelidad
```
```
CONTRATO (grupo A)     OK         …/alpha_png-to.jpg
  [p4 I2 informativo] jpg no admite alfa: perdida inevitable
  cobertura: completa
  ms: {'alfa': 0.295, 'total': 0.924, 'logica': 0.073}

FIDELIDAD (grupo C)    AVISO      …/alpha_png-to.jpg
  [pF I3 aviso] APLANADO SOBRE NEGRO: el pixel (0,0), 100 % transparente en la
                entrada, sale negro  esperado=srgb(255,255,255) obtenido=srgb(0,0,0)
  [pF I7 aviso] PSNR por debajo del umbral (sobre blanco)  esperado=>= 40,0 dB
                obtenido=0,704711
  cobertura: completa
  ms: {'I3': 33.235, 'I7': 36.136, 'total': 69.903}
```

Y el GIF, con el pedido real (`escala` y `fps` **sí** se pidieron, así que el contrato no protesta por el reescalado):

```
python bench/scripts/verificador.py \
    --salida bench/salidas-referencia/video/trivial_mp4-to-naive.gif \
    --entrada corpus/video/trivial.mp4 --destino gif \
    --params '{"escala":320,"fps":12}' --solo-fidelidad
```
```
FIDELIDAD (grupo C)    AVISO      …/trivial_mp4-to-naive.gif
  [pF V9 aviso] PALETA GENERICA: la tabla de color es una rejilla regular
                (8x8x4), no se calculo sobre el clip
  cobertura: completa
  ms: {'V9': 0.146, 'total': 1.239}
```

**Los dos veredictos están separados a propósito y no se mezclan.** En el primer ejemplo el contrato dice `OK` —la conversión entregó exactamente lo que se pidió: un JPEG de 200×200, y JPEG no admite alfa— y la fidelidad dice `AVISO` —lo entregó aplanado sobre negro—. Son dos preguntas distintas: *«¿me entregaste lo que pedí?»* y *«¿cuánto se parece a lo que había?»*. Colapsarlas en un solo veredicto obligaría a pagar el grupo C para poder responder la primera.

Lo que **sí** es común: el **código de salida es 1 si cualquiera de los dos grupos da `fallo`**, para que sirva en una suite de regresión.

Para un lote, `--lote trabajos.json` respeta `--alfa` y `--fidelidad` y vuelca todo en JSON; es lo que usa `bench/salidas-verificacion-fidelidad/medir_fid.py`.

*(Cabo corregido tras la revisión: `--fidelidad` **sí** ejecutaba el grupo C, pero el impresor de texto plano solo volcaba los hallazgos del contrato y el bloque C únicamente aparecía con `--json`. Ahora se imprimen los dos bloques siempre, cada uno con su veredicto, su cobertura y sus tiempos; y `--help` documenta los tres grupos con un ejemplo por grupo.)*

### 3.3 La regla de decisión

1. **El grupo A corre siempre.** Es el diferenciador nº 1 y sigue costando el 0,032 % de convertir. Nada de lo añadido aquí entra en él salvo V9, que cuesta 0,18 ms y cierra un punto ciego.
2. **El grupo B corre una vez por entrada, en la caracterización, y se cachea con el hash de contenido.** Nunca por salida. Si el orquestador no lo tiene, el punto 4 devuelve `ok_parcial` con `4_alfa: false` — **no** aprueba por defecto.
3. **El grupo C no corre en la conversión.** Corre:
   - en la **suite de regresión** (CI), donde 29 segundos para 53 ficheros son irrelevantes;
   - **bajo demanda explícita** del usuario («verifica la fidelidad de esta conversión»), donde el usuario ya sabe que va a esperar;
   - **nunca** en un lote de 500 ficheros.
4. **Cuando el grupo C no corre, no se finge que ha corrido.** `verificar_fidelidad()` tiene su propio veredicto y su propia `cobertura`; `verificar()` no lo invoca jamás (§3.2).

### 3.4 El argumento en una frase

**El contrato responde «¿me entregaste lo que pedí?» y cuesta el 0,032 % de convertir. La fidelidad responde «¿cuánto se parece a lo que había?» y cuesta el 38,5 %.** Son preguntas distintas con presupuestos distintos, y meterlas en la misma función es exactamente el error que convertiría el diferenciador nº 1 de FileX en su mayor problema de rendimiento.

---

## 4. El umbral de `txtwrite`

`referencia.json` regla P6: *«El umbral de "tiene texto" debe ser ≥ 10 caracteres imprimibles: `txtwrite` emite basura de 1-3 caracteres en PDF puramente rasterizados»*. Implementado y medido sobre los 9 PDF disponibles.

| PDF | Bytes | Caracteres de `txtwrite` | Muestra | ¿Texto con umbral `>0`? | ¿Con umbral `>=10`? | Coste |
|---|---:|---:|---|---|---|---:|
| `tipico_texto.pdf` | 3.219 | **105** | `FileX - documento de p` | sí | **sí**| 179,3 ms |
| `trivial.pdf` | 6.356 | **0** | `` | no | no | 172,2 ms |
| `patologico_escaneado.pdf` | 8.555.521 | **0** | `` | no | no | 297,4 ms |
| `escaneado_d1.pdf` | 84.653 | **0** | `` | no | no | 189,9 ms |
| `alpha_png-to.pdf` | 6.111 | **2** | `FX` | sí | no | 191,3 ms |
| `tipico_png-to.pdf` | 17.153 | **0** | `` | no | no | 207,4 ms |
| `tipico_jpg-to.pdf` | 89.885 | **0** | `` | no | no | 212,5 ms |
| `tipico_texto_rasterizado.pdf` | 8.689 | **0** | `` | no | no | 181,4 ms |
| `tipico_texto_pdf-to-gs.pdf` | 3.291 | **105** | `FileX - documento de p` | sí | **sí**| 178,5 ms |

**El caso que justifica el umbral: `alpha_png-to.pdf` devuelve `'FX'` — 2 caracteres — y no tiene ni una letra de texto real.** Con un umbral de `> 0` se declararía «conserva texto» **1 de los 9 PDF (11 %)** que no lo tiene. Con `≥ 10` no hay ni un error: los dos PDF con capa de texto real dan 105 caracteres cada uno y los siete restantes dan 0 o 2. **MEDIDO.**

**Coste: 172,2–297,4 ms**, mediana 179,3 ms sobre un PDF de 3 KB — coherente con los «~180 ms» que estimaba `coste-verificacion.md`. Es **485× el contrato completo**, y por eso el contrato sigue usando `b"/Font" in datos` como indicio barato y P6 vive en el grupo C.

**Ghostscript 10.07 lleva Tesseract embebido** (`-sDEVICE=ocr`, `pdfocr8/24/32`) pero sin datos de idioma; hay `.traineddata` (`eng`, `osd`) en `C:\Program Files\Tesseract-OCR\tessdata` y haría falta `TESSDATA_PREFIX`. **No se ha ejercitado**: el OCR no es una regla de fidelidad de `referencia.json`, es una conversión, y `referencia.json` la cataloga como **`no_evaluable`**. Queda **PENDIENTE**.

---

## 5. Re-verificación completa

### 5.1 Los cinco fallos documentados siguen atrapados — **MEDIDO**

Datos: `fallos.json`, `fallos.txt`. Cada caso contra los dos motores, ahora con `alfa=True`.

| # | Fallo reproducido | Esperado | En proceso | Coste | Subproceso | Coste |
|---|---|---|---|---:|---|---:|
| 1 | PNG entregado con extensión `.avif` | fallo | **FALLO** ✔ | 71,61 ms | **FALLO** ✔ | 422,83 ms |
| 2 | pierde una pista de audio (`ffmpeg` sin `-map 0`, rc=0) | fallo | **FALLO** ✔ | 0,94 ms | **FALLO** ✔ | 86,97 ms |
| 3 | degradación de 16 a 8 bits sin pedirla | fallo | **FALLO** ✔ | 0,50 ms | **FALLO** ✔ | 465,56 ms |
| 4a | redimensionado no solicitado con barras | fallo | **FALLO** ✔ | 64,47 ms | **FALLO** ✔ | 233,48 ms |
| 4b | *control*: el mismo JPEG → PNG sin tocar la geometría | ok | **OK** ✔ | 0,42 ms | **OK** ✔ | 115,13 ms |
| 5 | fichero de 0 bytes presentado como éxito | fallo | **FALLO** ✔ | 0,78 ms | **FALLO** ✔ | 40,37 ms |

**Cero discrepancias, con los dos motores.** El caso 4b (control) sigue dando `ok`: no hay falso positivo inducido.

### 5.2 Falsos positivos sobre las 53: **0**, en seis configuraciones — **MEDIDO**

Datos: `contrato.json`. Se ejecutó el contrato completo contra las 53 salidas del patrón oro con los dos motores × tres modos de `min(alfa)`.

| Motor | Modo de `min(alfa)` | Salidas | **Falsos positivos** | Falsos negativos | `ok_parcial` | Avisos | Coste de `min(alfa)` |
|---|---|---:|---:|---:|---:|---:|---:|
| proceso | inyectado desde `referencia.json` | 53 | **0** | 0 | 0 | 3 | 0,0 ms |
| proceso | **calculado en proceso** | 53 | **0** | 0 | 0 | 3 | 320,9 ms |
| proceso | no disponible | 53 | **0** | 0 | 11 | 3 | 0,0 ms |
| subproceso | inyectado desde `referencia.json` | 53 | **0** | 0 | 0 | 4 | 0,0 ms |
| subproceso | **calculado en proceso** | 53 | **0** | 0 | 0 | 4 | 321,1 ms |
| subproceso | no disponible | 53 | **0** | 0 | 11 | 4 | 0,0 ms |

- **`inyectado`**: `alfa_no_trivial` viene de `referencia.json`, como en el prototipo. Es el control: reproduce exactamente el resultado de `coste-verificacion.md` §7 (0 FP, 3 avisos en proceso y 4 con subprocesos).
- **`en_proceso`**: `alfa_no_trivial` se **calcula** con el lector nuevo. **Mismo resultado, misma cobertura completa.** El lector en proceso es intercambiable con la caracterización del patrón oro.
- **`sin_alfa`**: no se calcula ni se inyecta. **0 falsos positivos igualmente, pero 11 salidas pasan a `ok_parcial`.**

Los avisos son los mismos tres de siempre y todos legítimos: `tipico_mp4-audio.flac` (A6, profundidad inflada), `tipico_png-to.pdf` y `tipico_jpg-to.pdf` (P7, 1 px → 1 pt). El cuarto con subprocesos es el bitrate de `trivial_wav-to.m4a`.

### 5.3 Fidelidad sobre las 53: **0 fallos, 8 avisos** — **MEDIDO**

Datos: `fidelidad.json`, `fidelidad.txt`.

| Salida | Regla | Hallazgo | ¿Legítimo? |
|---|---|---|---|
| `alpha_png-to.jpg` | **I3** | «APLANADO SOBRE NEGRO: el píxel (0,0), 100 % transparente en la entrada, sale negro» | **Sí — es el punto ciego nº 1 del §7 de `coste-verificacion.md`, ahora detectado.** |
| `alpha_png-to.jpg` | **I7** | PSNR sobre blanco de **0,70 dB** | Sí — es el mismo hallazgo por otra vía: la imagen aplanada sobre negro *es* distinta. El suelo de 20 dB impide que la excusa «es un grafismo» lo tape. |
| `trivial_mp4-to-naive.gif` | **V9** | «PALETA GENÉRICA: la tabla de color es una rejilla regular (8×8×4)» | **Sí — es el punto ciego nº 2 del §7 de `coste-verificacion.md`, ahora detectado.** |
| `trivial_mp4-to.webm` | **V8** | PSNR de luminancia **29,63 dB** < 40 | Sí — nota de la propia regla V8: *«el sintético trivial.mp4 cae a 29,6 dB: los bordes duros castigan a VP9»*. Reproducido al decimal. |
| `alpha_png-to.avif` | **I8** | grafismo codificado con pérdida en un destino que admite sin pérdida | Sí — `perdidas`: *«Usar codificación con pérdida sobre grafismo es una elección mala del motor»*. |
| `alpha_png-to.webp` | **I8** | ídem | Sí — mismo caso. |
| `trivial_png-to.webp` | **I8** | ídem | Sí — nota de la regla I8: *«lossless 42 B y 1 color; lossy q80 94 B y 2 colores»*. |
| `tipico_mp3-to.flac` | **A4** | el PCM no coincide, con la profundidad inflada a 24 bits sobre un origen de 16 efectivos | Sí — regla A6. `tipico.mp3` da `f5ddaa64…`; su FLAC de 24 bits, medido en s16, da `984b4619…`. La información se conserva; cambia el redondeo al medirla. |
| `tipico_mp4-audio.flac` | **A5** | ídem, aac → FLAC de 24 bits | Sí — el mismo caso A6, que el contrato ya marca como aviso. |

**Ningún aviso es un falso positivo**: los ocho están documentados en `referencia.json` (`perdidas` o notas de regla) o son el hallazgo que se quería atrapar.

Y **14 de las 53 salen `ok_parcial` con la cobertura vacía**, que es lo correcto: a un CSV, a un MP3 con pérdida o a un PDF rasterizado desde una imagen no le aplica **ninguna** regla de fidelidad de `referencia.json`. El verificador no inventa una comprobación para poder decir «bien».

### 5.4 Los dos puntos ciegos — **CERRADOS**

**1. `alpha_png-to.jpg` aplanado sobre negro (regla I3, aviso).**

El lector de alfa en proceso devuelve, además del mínimo, **la coordenada del primer píxel 100 % transparente**: `(0, 0)` en `alpha.png`. Una sola invocación de `magick … -format "%[pixel:p{0,0}]"` lee ese píxel en la salida:

| Salida | Píxel (0,0) | Veredicto |
|---|---|---|
| `alpha_png-to.jpg` (sin `-background`) | `srgb(0,0,0)` | **aviso: APLANADO SOBRE NEGRO** |
| `alpha_png-to-flat.jpg` (con `-background white`) | `srgb(255,255,255)` | ok |

Coste: **25,9 ms**. Discrimina perfectamente entre la conversión mala y la buena del propio patrón oro. **MEDIDO.**

**2. `trivial_mp4-to-naive.gif` con paleta genérica (regla V9, aviso).**

No hace falta comparar píxeles. **Una paleta genérica es un producto cartesiano; una calculada sobre el clip no lo es.** La paleta por defecto de ffmpeg es la rejilla 8×8×4 (R y G a pasos de 36, B a pasos de 85):

| GIF | valores distintos por canal | producto | ¿== 256 colores? | Veredicto |
|---|---|---:|---|---|
| `trivial_mp4-to-naive.gif` | R 8, G 8, B 4 | **256** | **sí → rejilla** | **aviso: PALETA GENÉRICA** |
| `trivial_mp4-to-palette.gif` | R 134, G 120, B 127 | 2.042.160 | no | ok |

Coste: **0,18 ms, en proceso, leyendo `13 + 3n` bytes.** Es la comprobación más barata de todo el verificador después de la firma. **MEDIDO.**

*(Limitación honesta: el criterio detecta **rejillas regulares**. Una paleta genérica que no fuera una rejilla —por ejemplo una paleta «web-safe» recortada o una heredada de otro clip— no se detectaría. Para eso sí haría falta comparar píxeles, y sería grupo C.)*

### 5.5 La cobertura sigue siendo honesta — **MEDIDO**

Se añadió una quinta clave a `cobertura`: **`4_alfa`**. Vale `true` si (a) no hay entrada, (b) la entrada no tiene alfa —no hay nada que comprobar— o (c) `min(alfa)` se conoce, calculado o inyectado. En cualquier otro caso el veredicto `ok` se degrada a `ok_parcial`.

Las 11 salidas que caen en `ok_parcial` sin `min(alfa)` son exactamente las 11 cuya entrada declara alfa: las 5 de `tipico.png` y las 6 de `alpha.png`. **El verificador distingue «comprobado y correcto» de «no he podido comprobarlo» también en la única regla que exige píxeles.**

`verificar_fidelidad()` replica el mecanismo con su propio diccionario de cobertura, regla a regla.

---

## 6. Coste de implementación — **MEDIDO**

`git diff` sobre `bench/scripts/verificador.py`: **1.542 líneas añadidas, 10 sustituidas.** De 1.503 a 3.035 líneas. De las añadidas, **1.287 son código** (sin blancos ni comentarios).

| Bloque | Líneas | De código | % de lo añadido |
|---|---:|---:|---:|
| **Decodificador VP8L** (bits LSB, Huffman canónico, caché de color, referencias hacia atrás, 4 transformaciones, 14 predictores) | **437** | 381 | 28,3 % |
| **`min(alfa)` en PNG** (carril alfa, patrón de fila opaca, paleta+tRNS, flujo IDAT perezoso) | 281 | 220 | 18,2 % |
| **Fidelidad** (sondas externas + 11 reglas + orquestación) | 515 | 420 | 33,4 % |
| **`min(alfa)` en WebP** (ALPH, despacho VP8L, `alpha_is_used`) | 104 | 83 | 6,7 % |
| Desfiltrado ALPH, despachador de alfa, GIF, TIFF | 116 | 104 | 7,5 % |
| Integración en el contrato (`sondear`, `verificar`, cobertura `4_alfa`, regla I2) + CLI | ~89 | ~79 | 5,8 % |

**La lectura que importa:**

- **El 61 % de lo añadido (938 líneas) es leer píxeles sin decodificador externo.** Es el mismo patrón que en el prototipo original, donde el 53 % era leer cabeceras. **Fabricar el acceso al dato es siempre el grueso; la lógica de la regla es barata.**
- **Un solo formato —WebP— costó 437 líneas**, el 28 % del total, y solo porque su plano alfa va comprimido con VP8L. Es el precio literal de no devolver «no evaluable» en el formato de imagen web más común.
- **Las 11 reglas de fidelidad, con sus sondas, son 515 líneas.** La lógica pura de las reglas (sin las siete funciones de sonda externa) son unas 300.
- **74 líneas son excepciones justificadas por datos**, el **4,8 %** de lo añadido. En el prototipo original fueron 85 líneas, el 6,7 %. **La proporción se mantiene: entre el 5 y el 7 % de un verificador es la lista de casos en los que la especificación miente.**

---

## 7. Lo que sigue **PENDIENTE**

1. **`min(alfa)` de AVIF/HEIF, TIFF comprimido, GIF y PNG entrelazado.** Devuelven «no evaluable» con el motivo. AVIF exigiría un decodificador AV1 —fuera de discusión en proceso—; TIFF y GIF exigirían LZW/Deflate + predictor, que sí es abordable (estimación: 120-180 líneas); Adam7 son unas 40.
2. **El decodificador VP8L escala mal.** Un WebP sin pérdida de 1920×1080 **con** alfa tardaría del orden de 2,3 s en Python puro (medido sobre un VP8L opaco de ese tamaño **antes** de añadir el atajo de `alpha_is_used`). Por debajo de ~0,3 Mpx gana a `magick`; por encima pierde. Como el atajo cubre el caso opaco y el caso con alfa real corta pronto, el problema es teórico hoy, pero está ahí.
3. **`min(alfa)` con corte temprano no da el mínimo exacto.** Con `exacto=False` (el modo por defecto) se corta en el primer píxel no opaco y se devuelve `exacto: false`. Para la regla I2 basta —solo interesa `< 1,0`—, pero si alguna regla futura necesitara el valor exacto hay que pedir `exacto=True` y pagar el recorrido entero.
4. **V9 solo detecta rejillas regulares** (§5.4).
5. **V2** (número de fotogramas con `-count_frames`), **V5** (etiquetas de idioma y título) y **D3/D6/D7** (contenido exacto de los campos) siguen sin implementar. Las tres primeras son baratas; D3/D6/D7 ya están cubiertas de hecho por D1/D2/D4 en el corpus disponible.
6. **OCR con el Tesseract embebido de Ghostscript** (§4).
7. **Los 7 casos `no_evaluable` de `referencia.json`** (DOCX↔PDF, EPUB, SVG, OCR, qpdf, vips) siguen sin motor en esta máquina. **No se han dado por buenos**: no tienen salida que verificar.

---

## 8. Índice de datos crudos

Todo en `bench/salidas-verificacion-fidelidad/`.

| Fichero | Contenido |
|---|---|
| `medir_fid.py` | El banco de medida. Seis subcomandos: `alfa`, `contrato`, `reglas`, `fidelidad`, `texto`, `fallos`. Importa la tabla de 53 trabajos de `bench/salidas-verificacion/trabajos.py` y le añade el marcador `copia` de las tres órdenes con `-c copy`. |
| `alfa.json` / `alfa.txt` | `min(alfa)` en proceso frente a `magick`, 12 casos, mediana n=9, con el suelo de `zlib`. **Fuente del §1.** |
| `reglas.json` / `reglas.txt` | Coste unitario de cada regla de fidelidad, mediana n≥9. **Fuente del §2.2 y del §3.** |
| `fidelidad.json` / `fidelidad.txt` | Las 53 salidas por las reglas de fidelidad, con hallazgos y coste por regla. **Fuente del §5.3.** |
| `contrato.json` / `contrato.txt` | Las 53 salidas por el contrato, 2 motores × 3 modos de alfa. **Fuente del §5.2.** |
| `texto.json` / `texto.txt` | El umbral de `txtwrite` sobre 9 PDF. **Fuente del §4.** |
| `fallos.json` / `fallos.txt` | Los 5 fallos documentados, con los dos motores. **Fuente del §5.1.** |

**Metodología.** Medianas, nunca medias. n=9 en todo lo que se reporta como coste unitario (n=5 en el PSNR de vídeo 1080p, n=15 en el contrato de referencia). Calentamiento antes de cada tanda. Etiqueta `limpia`/`SUCIA` mediante un testigo de CPU determinista medido antes y después de cada tanda; se marca `SUCIA` si se desvía más del 20 %. **No se usó la GPU ni se tomó su lock** (otro agente la tenía). Máquina: Windows 10, 12 núcleos, Python 3.11.9, ffmpeg/ffprobe N-121159, ImageMagick 7.1.2-21 Q16-HDRI, Ghostscript 10.07. Sin dependencias nuevas: el verificador sigue siendo **biblioteca estándar de Python y nada más**.
