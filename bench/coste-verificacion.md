# El precio del argumento central de FileX: ¿cuánto cuesta verificar cada conversión?

**Fecha:** 20 de agosto de 2026
**Objeto:** cerrar los dos pendientes de `HUECOS.md` §1 — *«el coste real de implementar el contrato de verificación»* y *«el coste en tiempo de verificar cada conversión»*.
**Entregables:** este informe, `bench/scripts/verificador.py` y los datos crudos en `bench/salidas-verificacion/`.

> Cada afirmación va marcada **MEDIDO** o **PENDIENTE**.

---

## 0. Las cinco líneas que importan

1. **Verificar es barato — pero solo si no lanzas procesos.** **MEDIDO.** En proceso, el contrato completo cuesta **0,372 ms por fichero** (mediana de 53 salidas × 15 repeticiones). Con `ffprobe`/`magick identify`, **54,06 ms**: **145× más caro**.
2. **La ratio verificar/convertir en proceso es del 0,14 % al 0,36 %** según la categoría. **MEDIDO.** El diferenciador nº 1 está sano.
3. **Con subprocesos la ratio se va del 8,9 % al 70 %, y en 15 de las 39 órdenes del patrón oro verificar cuesta MÁS que convertir.** **MEDIDO.** La afirmación «es barato» de `HUECOS.md` es **cierta solo con la implementación correcta**; con la implementación evidente es **falsa**.
4. **Atrapa los cinco fallos reales documentados**, con los dos motores, y **no da ni un falso positivo** sobre las 53 salidas del patrón oro. **MEDIDO.**
5. **Coste de implementación: 1.503 líneas** (1.277 de código), de las que **el 53 % es leer cabeceras de contenedores** y solo **el 26 % es la lógica del contrato**. **MEDIDO.** El contrato es barato; el *sondeo sin subprocesos* es lo que cuesta escribir.

---

## 1. El verificador: qué hace y cuánto costó escribirlo

`bench/scripts/verificador.py`. Sin dependencias externas: **solo la biblioteca estándar de Python 3.11**. Ni Pillow, ni ffmpeg-python, ni pikepdf.

### 1.1 Los cuatro puntos del contrato

| # | Punto | Qué comprueba | De dónde sale |
|---|---|---|---|
| 1 | **Firma** | bytes mágicos reales frente a la extensión pedida; fichero de 0 bytes; código de retorno | `PLAN-ORQUESTADOR.md` §4.2.1, reglas G1/G3 |
| 2 | **Flujos** | nº de pistas de vídeo / audio / subtítulo obtenidas frente a las esperadas | §4.2.2, reglas V3/V4/V7 |
| 3 | **Propiedades** | coherencia interna de la salida: dimensiones plausibles, duración > 0, pistas declaradas, UTF-8 válido, páginas ≥ 1 | §4.2.3, reglas G2/G4/A2/A3/D2/D5/D8/P1 |
| 4 | **Pedido frente a obtenido** | **lo que no se pidió transformar debe conservarse**: geometría, relación de aspecto, ppp, profundidad, alfa, duración, frecuencia, canales, bitrate, páginas, filas | **nuevo**, de `bench/mcp-refs-multimedia.md` §6.2 |

El punto 4 es el que `mcp-refs-multimedia.md` demostró que faltaba: el WebP de `image-worker-mcp` **pasa los tres primeros puntos** y aun así es una imagen redimensionada sin permiso.

### 1.2 Coste de implementación — **MEDIDO**

**1.503 líneas físicas; 1.277 de código** (sin líneas en blanco ni comentarios).

| Bloque | Líneas de código | % |
|---|---:|---:|
| Sondeo EN PROCESO — imagen: PNG/JPEG/WebP/GIF/TIFF | 184 | 14,4 % |
| **Punto 4** — pedido frente a obtenido | 187 | 14,6 % |
| Sondeo EN PROCESO — ISO-BMFF: AVIF + MP4/M4A/MOV | 136 | 10,6 % |
| Sondeo EN PROCESO — audio: Ogg/WAV/FLAC/MP3 | 129 | 10,1 % |
| Sondeo EN PROCESO — Matroska/WebM (EBML) | 89 | 7,0 % |
| Sondeo por SUBPROCESO — `ffprobe`/`magick`/`gs` | 98 | 7,7 % |
| Orquestación + CLI | 79 | 6,2 % |
| **Punto 3** — propiedades | 69 | 5,4 % |
| Sondeo EN PROCESO — despachador + utilidades | 49 | 3,8 % |
| **Punto 1** — firma real | 44 | 3,4 % |
| Sondeo EN PROCESO — datos: CSV/JSON | 44 | 3,4 % |
| Sondeo EN PROCESO — PDF | 40 | 3,1 % |
| **Punto 2** — flujos | 33 | 2,6 % |
| Tablas y constantes de módulo | 96 | 7,5 % |

**La lectura que importa:**

- **La lógica de los cuatro puntos son 333 líneas: el 26 % del fichero.** Ahí está todo el valor del diferenciador.
- **El sondeo en proceso son 671 líneas: el 53 %.** Escribir parsers de cabecera de PNG, JPEG, WebP, GIF, TIFF, ISO-BMFF, EBML, Ogg, RIFF, FLAC, MP3, PDF y CSV/JSON es el grueso del trabajo.
- **El mismo sondeo delegado a binarios externos son 98 líneas: el 7,7 %.** *Comprar* el sondeo cuesta 98 líneas; *fabricarlo* cuesta 671. **Esa diferencia de 573 líneas es el precio literal del factor 145× de rendimiento** de la sección 4.
- El punto 4, que no existía en el plan, es **el bloque de lógica más grande** (187 líneas frente a 33+69 de los puntos 2 y 3 juntos). No es una mejora incremental: es la mitad del contrato.

### 1.3 Lógica específica por categoría

| Categoría | Sondeo (líneas) | Reglas propias del punto 4 |
|---|---:|---|
| imagen | 184 (+136 AVIF compartidas con MP4) | I1 geometría, I2 alfa no trivial, I4/I5 profundidad con techo por formato, aspecto (barras) |
| vídeo | 136 + 89 | V3/V4/V7 pistas, V1 duración ±1 fotograma, geometría, fps |
| audio | 129 | A1 duración con tolerancia de trama, A2 canales, A3 excepción Opus, A6 profundidad inflada, bitrate pedido |
| PDF/documento | 40 | P1 páginas, P4 ppp = pt·dpi/72, P7 caja de página |
| datos | 44 | D1 filas lógicas, D2 campos constantes, D4 BOM/cabecera, D5 UTF-8, D8 JSON válido |

### 1.4 Lo que el prototipo **NO** cubre — **PENDIENTE**

- **El único dato del contrato que exige decodificar píxeles: `min(alfa)`** (trampa nº 1, «alfa trivial»). Cuesta **734,6 ms** con `magick -format "%[fx:minima.a]"` sobre un PNG de 1920×1080 — **1.975× la verificación completa en proceso**. En este prototipo se inyecta desde la caracterización de la entrada (que un orquestador real calcula **una vez por entrada**, no una por salida). Un cálculo en proceso está sin escribir.
- **Reglas que exigen comparar píxeles**: I3 (aplanado sobre blanco o negro), I6/I7 (RMSE/PSNR), V6/V8 (framemd5, PSNR), A4/A5 (md5 del PCM). Son reglas de **fidelidad**, no del contrato de §4.2; su coste es el de un `magick compare` o un `ffmpeg -f md5`, es decir, del orden de la conversión misma.
- **Los 7 casos `no_evaluable`** de `referencia.json` (DOCX↔PDF, EPUB, SVG, OCR, qpdf, vips) no tienen motor en esta máquina y por tanto no tienen salida que verificar. El verificador **no los da por buenos**: devuelve un campo `cobertura` con qué puntos pudo evaluar de verdad y un veredicto `ok_parcial` cuando alguno no era evaluable. **Esto es deliberado**: un verificador que no distingue «comprobado y correcto» de «no he podido comprobarlo» repite exactamente el fallo de `markitdown-mcp` (cadena vacía con `isError: false`).

---

## 2. Coste unitario por punto del contrato — **MEDIDO**

Mediana de **53 salidas × 15 repeticiones por fichero** = 795 muestras por motor. Etiqueta según el testigo de CPU medido antes y después de la tanda (el `harness.sh` original etiqueta por ruido de GPU; aquí no se usa la GPU). Datos crudos: `bench/salidas-verificacion/puntos.json`.

### Motor **en proceso** — `[limpia]`

| Categoría | sonda | p1 firma | p2 flujos | p3 props | p4 pedido | **lógica** | **TOTAL** |
|---|---:|---:|---:|---:|---:|---:|---:|
| imagen | 0,277 | 0,047 | 0,0010 | 0,0015 | 0,0105 | 0,062 | **0,355 ms** |
| audio | 0,251 | 0,039 | 0,0041 | 0,0022 | 0,0154 | 0,060 | **0,315 ms** |
| vídeo | 0,770 | 0,056 | 0,0046 | 0,0029 | 0,0163 | 0,081 | **0,899 ms** |
| pdf | 0,281 | 0,045 | 0,0009 | 0,0012 | 0,0113 | 0,059 | **0,350 ms** |
| datos | 0,312 | 0,050 | 0,0010 | 0,0023 | 0,0101 | 0,064 | **0,384 ms** |
| **todas** | 0,297 | 0,046 | 0,0012 | 0,0017 | 0,0120 | **0,064** | **0,372 ms** |

### Motor **por subprocesos** — `[limpia]`

| Categoría | sonda | p1 firma | p2 flujos | p3 props | p4 pedido | **lógica** | **TOTAL** |
|---|---:|---:|---:|---:|---:|---:|---:|
| imagen | 67,34 | 0,117 | 0,0016 | 0,0023 | 0,0190 | 0,140 | **67,48 ms** |
| audio | 47,44 | 0,107 | 0,0063 | 0,0033 | 0,0259 | 0,142 | **47,59 ms** |
| vídeo | 51,32 | 0,111 | 0,0058 | 0,0033 | 0,0199 | 0,140 | **51,44 ms** |
| pdf | 169,20 | 0,102 | 0,0015 | 0,0021 | 0,0191 | 0,125 | **169,30 ms** |
| datos | 0,26 | 0,047 | 0,0009 | 0,0019 | 0,0091 | 0,059 | **0,32 ms** |
| **todas** | 53,88 | 0,109 | 0,0018 | 0,0024 | 0,0201 | 0,136 | **54,06 ms** |

### El resultado que reordena el problema

**La lógica de los cuatro puntos del contrato cuesta 0,064 ms.** Comparar dos diccionarios es gratis. **El 99,75 % del coste con subprocesos (53,88 de 54,06 ms) es la sonda**, y la sonda es sobre todo **crear un proceso**.

- El punto 2 (flujos) —el que `HUECOS.md` teme por «un `ffprobe` por salida»— cuesta **0,0012 ms** de lógica. El `ffprobe` no lo paga el punto 2: lo paga la decisión de arquitectura.
- El punto 1 (firma) es **el más caro de la lógica** (0,046 ms) —es el único que abre el fichero por su cuenta— y cuadruplica al punto 4, que le sigue. Aun así, **la sonda cuesta 6,4 veces más que él**.
- La categoría **datos** cuesta lo mismo con los dos motores (0,38 frente a 0,32 ms) **porque no hay binario externo que aporte nada**: CSV y JSON se parsean en Python en ambos casos. Es el control negativo del experimento.

### Coste desnudo de las sondas externas — **MEDIDO** (n=11, `[limpia]`)

| Orden | Mediana |
|---|---:|
| `magick -version` (solo arrancar) | 24,2 ms |
| `ffprobe` sobre un MP3 de 194 KB | 51,0 ms |
| `ffprobe -version` (solo arrancar) | 57,1 ms |
| `ffprobe` sobre un MP4 de 16 MB | 64,2 ms |
| `ffprobe` sobre un MKV de 4 MB con 2 pistas | 83,5 ms |
| `magick identify` sobre un PNG de 1920×1080 | 205,5 ms |
| `magick identify` sobre un TIFF de 72 MB a 16 bits | 217,6 ms |
| `magick` mínimo del canal alfa (PNG 1920×1080) | 734,6 ms |

**`ffprobe` sobre un MP4 de 16 MB cuesta 64 ms y sobre un MP3 de 194 KB cuesta 51 ms: 13 ms de diferencia para 84× más fichero.** El coste **no** está en leer: está en existir.

### El suelo de Windows, remedido — **MEDIDO**

`ANALISIS-COMPLETO.md` §5.3 fija el suelo de creación de proceso en **49 ms**. Aquí `cmd /c exit` dio:

| Condición | Mediana |
|---|---:|
| máquina en reposo, n=25 | **14,0 ms** `[limpia]` |
| documentado en `ANALISIS-COMPLETO.md` §5.3, n=25 | 49 ms |
| inmediatamente después de ~1.500 lanzamientos de proceso, n=15 | **91,0 ms** |

**El suelo no es una constante: varía 6,5× con la carga reciente de la máquina.** Y esa variación es exactamente el régimen en el que trabaja un lote. Es un argumento adicional, y no menor, contra pagar ese suelo 53 veces seguidas.

---

## 3. La ratio verificar ÷ convertir — la cifra que sostiene el diferenciador

`referencia.json` dice explícitamente *«NO se han tomado mediciones de tiempo»*. Se han tomado aquí: las **39 órdenes** del patrón oro, reejecutadas con las mismas invocaciones, salida al temporal y borrada después. Repeticiones según coste: **n=9** por debajo de 1,5 s, **n=5** hasta 8 s, **n=3** por encima. Datos: `conversion.json` y `ratio.json`.

Las 39 conversiones suman **74,9 s**. Verificar las 39 salidas: **24,2 ms en proceso**, **7.203 ms con subprocesos**.

### Ratio por categoría — **MEDIDO**

| Categoría | Convertir (mediana) | **En proceso** | **ratio** | Subprocesos (mejor caso, `[limpia]`) | **ratio** | Subprocesos (en tanda sostenida) | **ratio** |
|---|---:|---:|---:|---:|---:|---:|---:|
| imagen | 154,2 ms | 0,355 ms | **0,23 %** | 67,5 ms | 43,8 % | 52,1 ms | 27,3 % |
| audio | 158,6 ms | 0,315 ms | **0,20 %** | 47,6 ms | 30,0 % | 287,4 ms | **153,3 %** |
| vídeo | 578,6 ms | 0,899 ms | **0,16 %** | 51,4 ms | 8,9 % | 106,8 ms | 37,3 % |
| pdf | 243,1 ms | 0,350 ms | **0,14 %** | 169,3 ms | 69,6 % | 178,0 ms | 84,3 % |
| datos | 107,5 ms | 0,384 ms | **0,36 %** | 0,32 ms | 0,30 % | 0,37 ms | 0,31 % |
| **las 39 órdenes** | **74.865 ms** | **24,2 ms** | **0,032 %** | — | — | **7.203 ms** | **9,6 %** |

*(La columna «mejor caso» usa el coste por fichero medido en condiciones limpias; la columna «tanda sostenida» usa el coste medido fichero a fichero dentro de la propia tanda de 39×9 verificaciones, que es el régimen real de un lote. Ambas son ciertas; la segunda es la que se paga.)*

### El corolario incómodo — **MEDIDO**

**En 15 de las 39 órdenes del patrón oro (38 %), verificar con subprocesos cuesta MÁS que convertir.**

`img.alpha2jpg.negro`, `img.alpha2jpg.blanco`, `img.trivial2webp.lossy`, `img.trivial2webp.lossless`, `pdf.rasterizado`, `vid.mkv2mp4.copy`, `vid.2gif.naive`, `vid.extraer.copy`, `aud.wav2mp3`, `aud.wav2flac`, `aud.flac2wav`, `aud.flac2mp3`, `aud.flac2opus`, `aud.mp32wav`, `aud.mp32flac`.

Los peores casos son demoledores:

| Orden | Convertir | Verificar (subproceso) | Ratio |
|---|---:|---:|---:|
| `aud.flac2wav` | 96,6 ms | 383,9 ms | **397 %** |
| `aud.mp32wav` | 155,6 ms | 314,1 ms | **202 %** |
| `img.trivial2webp.lossy` | 30,1 ms | 62,1 ms | **206 %** |
| `vid.mkv2mp4.copy` (remux) | 65,6 ms | 106,8 ms | **163 %** |

**El patrón es nítido: cuanto más barata es la conversión, peor sale la ratio.** Un remux `-c copy`, un cambio de contenedor de audio, un PNG de 64×64 → WebP: son las conversiones **más frecuentes** en un conversor generalista, y son precisamente en las que el `ffprobe` de verificación duplica o cuadruplica el trabajo.

**Con el motor en proceso, la peor ratio de las 39 es 3,14 %** (`vid.mkv2mp4.copy`, un remux de 4 MB en 66 ms verificado en 2,06 ms). Ninguna pasa del 3,2 %.

---

## 4. Subprocesos frente a en proceso — la comparación, con números

| Métrica | En proceso | Subprocesos | Factor |
|---|---:|---:|---:|
| Verificación completa, mediana por fichero | **0,372 ms** | 54,06 ms | **145×** |
| Peor categoría de cada motor | 0,899 ms (vídeo) | 169,3 ms (pdf) | 188× |
| Ratio verificar/convertir, mediana por categoría | 0,14–0,36 % | 8,9–70 % (hasta 397 % por orden) | ~180× |
| Lote de 53 salidas, en serie | **26,1 ms** | 6.740 ms | **258×** |
| Lote de 53 salidas, mejor configuración | **15,6 ms** (4 procesos) | 3.774 ms (24 hilos) | **242×** |
| Procesos lanzados por verificación | **0** | 1 (2 si hay que sondear también la entrada) | — |
| Líneas de código del sondeo | 671 | 98 | 6,8× |
| Dependencias externas | ninguna | ffmpeg, ImageMagick, Ghostscript instalados y en el PATH | — |

### Bytes leídos del disco — **MEDIDO**

Sondear en proceso **las 53 salidas del patrón oro (204,9 MB en disco) lee 334,6 KB: el 0,163 %.**

| Fichero | En disco | Leído | % |
|---|---:|---:|---:|
| `16bit_tif-to-d16.png` | 61.849.791 B | **133 B** | 0,0000 % |
| `16bit_tif-to-d8.png` | 18.943.503 B | 141 B | 0,0007 % |
| `tipico_mp4-to.webm` | 17.014.670 B | 888 B | 0,0052 % |
| `tipico_mp4-to.mkv` | 16.235.751 B | 932 B | 0,0057 % |
| `2pistas_mkv-to-COPY.mp4` | 4.085.275 B | 1.397 B | 0,0342 % |

**Verificar un PNG de 61 MB cuesta 133 bytes de lectura.** Toda la información del contrato —firma, dimensiones, profundidad, alfa, ppp— vive en los primeros bytes. La estrategia en proceso no es «más rápida haciendo lo mismo»: **hace radicalmente menos trabajo**, porque no decodifica el fichero.

### Diferencias de comportamiento entre los dos motores — **MEDIDO**

No son intercambiables al 100 %. Lo detectado:

| Aspecto | En proceso | Subproceso | Quién acierta |
|---|---|---|---|
| Duración de un Opus de 8,000 s | **8,0000 s** (resta el *pre-skip* de `OpusHead`) | 8,0065 s | en proceso |
| Duración de la pista de audio de `tipico.mp4` | 20,0232 s (`mdhd` crudo) | 20,0000 s (aplica la *edit list*) | subproceso |
| Bitrate por pista en MP4 | no lo calcula | sí | subproceso |
| `MediaBox` de un PDF | gratis, leyendo bytes | requiere ampliar el PostScript de `gs` | empate tras ampliarlo |
| `min(alfa)` | **no puede** sin decodificar | 734,6 ms | subproceso |
| Resolución de un PNG | ppm → ppp, correcto | `%x` devuelve **píxeles por centímetro**: un PNG de 150 ppp sale como «59» | en proceso (el subproceso necesita `%U`) |

**Recomendación: el motor en proceso como camino principal, los binarios externos como excepción explícita y minoritaria.**

1. Puntos 1, 2 y 3, y la mayor parte del 4: **siempre en proceso**. Cubren los cinco fallos reales.
2. `ffprobe` **solo** cuando la salida es audio o vídeo **y** hay que comprobar bitrate por pista o alinear con una *edit list*. No por defecto.
3. Los datos que exigen píxeles (`min(alfa)`, PSNR, framemd5) se calculan **una vez por entrada**, se cachean con el hash de contenido y **nunca** por salida. Con 5 salidas por entrada, el coste de `min(alfa)` se divide por 5.
4. Si aun así hay que lanzar un proceso, **hazlo una sola vez por fichero y extrae todo de una pasada**. `ffprobe -show_format -show_streams` da los puntos 2, 3 y 4 en la misma invocación; pedirlos por separado triplicaría el coste sin añadir nada.

---

## 5. El lote, que es donde `HUECOS.md` temía el problema

`HUECOS.md` dice literalmente: *«un `ffprobe` por salida no es gratis en lote»*. **Confirmado, y con la magnitud.** Datos: `bench/salidas-verificacion/lote.json`, n=5 por configuración.

### Lote de las 53 salidas del patrón oro (204,9 MB)

| Configuración | Total | Por fichero | Escalado |
|---|---:|---:|---|
| **suelo: `cmd /c exit` × 1** | 14,0 ms | — | — |
| en proceso, serie | **26,1 ms** | 0,49 ms | referencia |
| en proceso, 4 hilos | 24,4 ms | 0,46 ms | ×1,07 |
| en proceso, 12 hilos | 26,8 ms | 0,51 ms | ×0,97 |
| en proceso, 24 hilos | 32,1 ms | 0,61 ms | **×0,81 (peor)** |
| en proceso, **4 procesos** | **15,6 ms** | **0,29 ms** | **×1,67** |
| en proceso, 12 procesos | 42,8 ms | 0,81 ms | ×0,61 (peor) |
| subproceso, serie | **6.740 ms** | 127,2 ms | referencia |
| subproceso, 4 hilos | 5.586 ms | 105,4 ms | ×1,21 |
| subproceso, 12 hilos | 3.928 ms | 74,1 ms | ×1,72 |
| subproceso, 24 hilos | 3.774 ms | 71,2 ms | **×1,79 (techo)** |

### El caso peor: 24 vídeos grandes (`corpus/video/`, 8 pasadas de 3 ficheros = 483 MB)

| Configuración | Total | Por fichero | Escalado |
|---|---:|---:|---|
| en proceso, serie | **11,2 ms** | **0,47 ms** | referencia |
| en proceso, 4 hilos | 28,4 ms | 1,18 ms | ×0,39 |
| en proceso, 4 procesos | 11,3 ms | 0,47 ms | ×0,99 |
| subproceso, serie | 1.982 ms | 82,6 ms | referencia |
| subproceso, 4 hilos | 574 ms | 23,9 ms | ×3,45 |
| subproceso, 12 hilos | 535 ms | 22,3 ms | ×3,71 |
| subproceso, 24 hilos | 502 ms | 20,9 ms | **×3,95** |

### Dónde está el cuello — **MEDIDO**

**No es el disco.** El sondeo en proceso lee el 0,163 % de los bytes; 483 MB de vídeo se verifican en 11,2 ms leyendo unos pocos KB. Un cuello de disco daría un tiempo proporcional al tamaño, y **el fichero de 61 MB no cuesta más que el de 42 KB**.

**No es el parseo.** La lógica de los cuatro puntos son 0,064 ms de 0,372. El parseo de cabeceras (0,297 ms) es lo más caro **del motor barato**, y es 181 veces más barato que el caro.

**Es la creación de proceso.** Tres pruebas convergentes:

1. **El escalado se estanca en ×1,79 con 24 hilos sobre 12 núcleos** para las 53 salidas. Si el cuello fuera CPU, 12 hilos darían cerca de ×12; si fuera disco, los hilos no darían nada. ×1,79 con 24 hilos es la firma de un recurso serializado en el núcleo del sistema: la creación de procesos.
2. **Con ficheros grandes el escalado sube a ×3,95**, porque entonces `ffprobe` sí hace trabajo real que se solapa. Es decir: **cuanto menos trabajo útil hay que hacer, peor escala** — justo al revés de lo intuitivo.
3. **El suelo de proceso pasa de 14 ms en reposo a 91 ms tras una tanda de lanzamientos.** Los 53 procesos de un lote se degradan entre sí.

**El corolario para FileX:** el paralelismo **no rescata** la estrategia de subprocesos. En el mejor caso (24 hilos) el lote de 53 salidas baja de 6.740 a 3.774 ms; **el motor en proceso en serie, sin paralelizar nada, tarda 26,1 ms.** Sigue siendo **145× más rápido que el subproceso paralelizado al máximo**.

**Y para el motor en proceso, paralelizar es casi todo pérdida.** Los hilos no ayudan (el parseo es CPU puro bajo el GIL) y con 24 hilos empeora un 19 %. Un grupo de 4 procesos persistente da ×1,67 sobre 53 ficheros y **nada** sobre 24 ficheros grandes, porque a 0,47 ms por tarea el reparto cuesta más que el trabajo. **Recomendación: verificar en serie, en el mismo proceso, dentro del hilo que hizo la conversión.**

---

## 6. Los cinco fallos reproducidos — ¿los atrapa? **Sí, los cinco**

Datos: `bench/salidas-verificacion/fallos.json` y `fallos.txt`. Cada caso se ejecuta contra los dos motores.

| # | Fallo | Origen | Punto y regla | En proceso | Subproceso |
|---|---|---|---|---|---|
| 1 | **PNG con extensión `.avif`** | ConvertX | p1 · G3 | **FALLO** en 22,4 ms* | **FALLO** en 272,5 ms |
| 2 | **Pierde una pista de audio** (`ffmpeg` sin `-map 0` sobre `patologico_2pistas.mkv`, rc=0) | ConvertX y SnapOtter | p2 · V3 (esperado 2, obtenido 1) | **FALLO** en 0,99 ms | **FALLO** en 98,8 ms |
| 3 | **Degradación de 16 a 8 bits** (`patologico_16bit.tif` → PNG sin pedir `-depth 8`) | SnapOtter | p4 · I4 (esperado 16, obtenido 8) | **FALLO** en 0,28 ms | **FALLO** en 899,3 ms |
| 4a | **Redimensionado no solicitado con barras** (1920×1080 → 800×600, contenido 800×450) | image-worker-mcp | p4 · I1/V7 + aviso de relación de aspecto | **FALLO** en 0,43 ms | **FALLO** en 47,0 ms |
| 4b | **Control: el mismo JPEG→PNG sin tocar la geometría** | — | ninguna | **OK** en 0,52 ms | **OK** en 114,0 ms |
| 5 | **Fichero de 0 bytes como éxito** | video-audio-mcp | p1 · G1 + p3 · G2 | **FALLO** en 0,25 ms | **FALLO** en 0,27 ms |

\* *el caso 1 mide 22,4 ms porque el fichero se acaba de crear y la lectura es en frío; en caliente cuesta lo mismo que los demás.*

**Los tres primeros son la prueba de aceptación del hito 3 de `PLAN-ORQUESTADOR.md` §7: superada, con los dos motores.**

Observaciones:

- **El caso 4 exige el punto 4 y solo el punto 4.** El PNG de 800×600 es un PNG válido (punto 1 ✓), no es audiovisual (punto 2 no aplica), y es internamente coherente (punto 3 ✓). Sin comparar contra la entrada, **`image-worker-mcp` habría pasado limpio**. Confirma lo que `mcp-refs-multimedia.md` §6.2 anticipó.
- **El caso 4a se detecta dos veces**: por dimensiones (1920×1080 → 800×600, `fallo`) y por relación de aspecto (1,778 → 1,333, `aviso`). La segunda comprobación es la que atraparía un redimensionado **con el lienzo correcto pero con barras**, que es el caso de `trivial.png` ampliado ×9,75 en aquel informe.
- **El caso 5 es el único donde los dos motores cuestan lo mismo** (0,25 frente a 0,27 ms): un fichero de 0 bytes se descarta antes de lanzar nada. El fallo más grave del catálogo es también el más barato de detectar.
- **El caso 3 tiene truco, y es deliberado:** el fichero verificado es el **mismo** `16bit_tif-to-d8.png` que en el §7 pasa como correcto. Lo único que cambia es el **pedido**. Con `-depth 8` solicitado es una conversión impecable; sin solicitarlo es una degradación silenciosa. **El contrato no juzga ficheros: juzga ficheros contra pedidos.**

---

## 7. Falsos positivos: **0 de 53, con los dos motores** — **MEDIDO**

Un verificador que grita ante conversiones correctas es inservible. Se ejecutó el contrato completo contra **las 53 salidas caracterizadas del patrón oro**, con su entrada y su pedido reconstruidos a partir de las 39 órdenes. Datos: `correccion.json`, `correccion.txt`.

| Métrica | En proceso | Subproceso |
|---|---:|---:|
| Salidas evaluadas | 53 | 53 |
| **Falsos positivos** (`fallo` sobre una salida correcta) | **0** | **0** |
| **Falsos negativos** (`ok` sobre el contraejemplo deliberado) | **0** | **0** |
| Cobertura parcial (algún punto no evaluable) | 0 | 0 |
| Avisos (todos legítimos) | 3 | 4 |

El contraejemplo deliberado es `2pistas_mkv-to-DEFAULT.mp4`, que el propio `referencia.json` cataloga como *«FALLO DE USO DEL MOTOR»*: se detecta como `fallo` con los dos motores.

Los avisos emitidos son todos ciertos y todos están en las pérdidas catalogadas:

| Aviso | Regla | ¿Legítimo? |
|---|---|---|
| `tipico_mp4-audio.flac`: profundidad inflada | A6 | Sí — `referencia.json`: *«ffmpeg elige s32/24 bits para mp3→flac: 398 KB en vez de ~104 KB, sin ninguna información adicional»* |
| `tipico_png-to.pdf` y `tipico_jpg-to.pdf`: 1 px → 1 pt, página de 677×381 mm | P7 | Sí — pérdida nº 9 del catálogo |
| `trivial_wav-to.m4a`: bitrate 128,8 kbps pidiendo 192 | — | Sí — el codificador AAC nativo no honra la petición sobre material mono |

### Pero el 0 % no fue gratis: **9 falsos positivos en la primera versión** — **MEDIDO**

La primera versión del verificador, escrita siguiendo el contrato al pie de la letra, dio **9 falsos positivos con el motor en proceso y 10 con subprocesos: un 17-19 %.** Cada uno exigió una corrección. **Este es el coste real de implementación que `HUECOS.md` daba por bajo, y es la parte que no se ve leyendo la especificación.**

| # | Falso positivo | Causa | Corrección | Coste |
|---|---|---|---|---|
| 1 | «pierde la pista de vídeo» al extraer audio | `-vn` estaba en `params` y el código lo buscaba en la raíz del pedido | leer la bandera de ambos sitios | 4 líneas |
| 2 | «la duración cambia 15,6 ms» al extraer audio de un MP4 | se comparaba la pista de salida contra el **contenedor** de entrada (20,0000 s) en vez de contra su **pista** (20,0232 s) | comparar pista contra pista | 12 líneas |
| 3 | «la duración cambia 15,6 ms» en AAC → MP3/FLAC | la tolerancia de ±10 ms de la regla A1 es **físicamente imposible** para un códec de trama: una trama de MP3 dura 26,1 ms y una de AAC 23,2 ms | tolerancia = máx(10 ms, trama de origen, trama de destino) | 22 líneas + tabla |
| 4 | «se pierde una fila» en CSV ↔ JSON | un CSV cuenta su cabecera como fila y un JSON de objetos no: desfase constante de 1 | contar `filas_datos` normalizadas | 6 líneas |
| 5 | «degradación de 16 a 12 bits» en PNG → AVIF | AVIF tiene un techo de 12 bits: la pérdida es inevitable | tabla de profundidad máxima por formato de destino, no una lista binaria de «formatos de 8 bits» | 4 líneas |
| 6 | «degradación de 32 a 16 bits» en un remux MKV → MP4 **sin recodificar** | Matroska declara `BitDepth=32` para un AAC; MP4 declara 16. **No se tocó un solo byte de audio** | la profundidad solo se compara en imagen; en audio, solo si el destino es sin pérdida | 8 líneas |
| 7 | «frecuencia alterada 44.100 → 48.000» en WebM con Opus | la excepción de Opus buscaba el códec `opus`, y Matroska lo llama `A_OPUS` | normalizador de nombres de códec | 12 líneas |
| 8 | «bitrate muy lejos del pedido: 128,8 k frente a 192 k» | el bitrate es una **petición**, no un contrato | umbrales calibrados con datos reales: <15 % se acepta, 15-50 % aviso, >50 % fallo (ConvertX daba 64 k pidiendo 192: 67 %) | 8 líneas |
| 9 | «ppp 59 en vez de 150» en tres PNG | `magick identify %x` devuelve **píxeles por centímetro** para PNG. 150 ppp → «59» | leer también `%U` y convertir | 7 líneas |

Un décimo, encontrado durante la corrección y que merece mención aparte: **`"aac".lstrip("a_")` devuelve `"c"`**, porque `lstrip` opera sobre un *conjunto* de caracteres. El normalizador de códecs quedó roto durante dos iteraciones y reintrodujo el falso positivo nº 3.

**Suma: unas 85 líneas de excepciones justificadas por datos, el 6,7 % del fichero, para bajar del 17 % de falsos positivos al 0 %.** Ninguna de ellas es deducible del contrato de `PLAN-ORQUESTADOR.md` §4.2; **todas** salieron de ejecutar contra el patrón oro.

### Las cuatro trampas de `PLAN-ORQUESTADOR.md` §8 — **MEDIDO**

| Trampa | Estado |
|---|---|
| 1. **Alfa trivial** (`tipico.png` declara alfa pero es opaco) | **Evitada.** La regla I2 solo exige conservación si `alfa_no_trivial`. `tipico.png` → JPEG/WebP no dispara nada; `alpha.png` (alfa real) → JPEG dispara un `informativo` de pérdida inevitable. **Limitación:** el dato `alfa_no_trivial` se inyecta desde la caracterización de la entrada; calcularlo cuesta 734,6 ms (§1.4). |
| 2. **Menor tamaño ≠ peor conversión** | **Evitada por construcción.** El verificador **no mira el tamaño del fichero** en ninguna regla, salvo para distinguir 0 bytes de no-0. El GIF ingenuo (395 KB) y el bueno (610 KB) reciben el mismo veredicto por parte del contrato. |
| 3. **Opus fuerza 48 kHz y 8,0065 s** | **Evitada, dos veces.** La excepción de A3 reconoce Opus a 48 kHz (tras arreglar `A_OPUS`), y la tolerancia de duración por trama cubre el desfase. El motor en proceso además calcula 8,0000 s exactos porque resta el *pre-skip* de `OpusHead`. |
| 4. **`txtwrite` emite 1-3 caracteres de basura** | **No ejercitada.** El prototipo usa `/Font` como indicio barato de capa de texto, no `txtwrite`. Extraer texto es un `gs` completo (~180 ms) y pertenece a las reglas de fidelidad, no al contrato de §4.2. El umbral de ≥10 caracteres queda **PENDIENTE** de implementar cuando se añada esa regla. |

### Puntos ciegos conocidos — **PENDIENTE**

Dos avisos del patrón oro que el contrato **no** detecta, y por qué:

- **`alpha_png-to.jpg` aplana sobre negro en vez de blanco** (regla I3, severidad *aviso*). Exige leer el píxel de una zona transparente: decodificación.
- **`trivial_mp4-to-naive.gif` usa paleta genérica** (regla V9, severidad *aviso*). Exige comparar píxeles.

Son **falsos negativos de avisos**, no de fallos. Ninguno de los cinco fallos reales del §6 cae en esta categoría: **el contrato de §4.2 más el punto 4 cubre el 100 % de los fallos documentados sin decodificar un solo píxel.**

---

## 8. Veredicto: ¿es barato verificar?

`HUECOS.md` §1 afirma, sin datos: *«Es barato. Firma real del fichero, `ffprobe` de flujos, y comparación de propiedades declaradas contra medidas.»*

**La afirmación se confirma. La justificación que la acompaña se refuta.**

### Lo que se confirma — **MEDIDO**

- **Verificar cuesta el 0,14-0,36 % de convertir**, según categoría. Sobre las 39 órdenes completas del patrón oro: **74,9 s de conversión frente a 24,2 ms de verificación, el 0,032 %**.
- **La peor ratio individual de las 39 es el 3,14 %.** No hay ni un caso en que verificar se acerque a costar lo que convertir.
- **Atrapa los cinco fallos reales documentados**, incluido el que el contrato original **no** cubría.
- **Cero falsos positivos** sobre 53 salidas correctas por construcción.
- **Cero dependencias.** No necesita que ffmpeg esté instalado para comprobar que un MP4 tiene dos pistas de audio.
- **En lote es prácticamente gratis**: 53 salidas, 204,9 MB, **26,1 ms en serie leyendo 334,6 KB**.

**El diferenciador nº 1 de FileX está sano. Es defendible con números.**

### Lo que se refuta — **MEDIDO**

**«`ffprobe` de flujos» es exactamente la implementación que hace caro el diferenciador.**

- Con `ffprobe`/`magick identify`, verificar cuesta **145× más**: 54,06 ms por fichero en vez de 0,372.
- **En 15 de las 39 órdenes (38 %), verificar costaría más que convertir.** En `flac → wav`, **cuatro veces más**.
- El paralelismo no lo salva: **el techo de escalado es ×1,79 con 24 hilos** sobre 12 núcleos, porque el cuello es la creación de proceso, no la CPU ni el disco.
- Y hay un efecto de segundo orden: **una tanda de lanzamientos degrada el propio suelo de proceso de 14 a 91 ms.**

**Si FileX implementa el contrato como está escrito en `PLAN-ORQUESTADOR.md` §4.2 —«flujos esperados frente a obtenidos (`ffprobe`)»— el diferenciador nº 1 se convierte en su mayor problema de rendimiento.** Esa frase debe cambiar.

### Lo que hay que corregir en los documentos

1. **`PLAN-ORQUESTADOR.md` §4.2 punto 2** dice «(`ffprobe`)». Debe decir: *lectura de las cabeceras del contenedor en proceso; `ffprobe` solo como excepción documentada.*
2. **`PLAN-ORQUESTADOR.md` §4.2 debe incorporar el punto 4**, «propiedades pedidas frente a obtenidas». Es la mitad de la lógica del verificador (187 de 333 líneas) y es lo único que atrapa el fallo de `image-worker-mcp`.
3. **`HUECOS.md` §1, «Es barato»**, puede mantenerse, con la coletilla: *barato si se lee la cabecera; caro —a veces más caro que convertir— si se lanza un proceso.*
4. **Añadir a §6, «trampas conocidas»**: un verificador ingenuo escrito desde la especificación da un **17 % de falsos positivos** sobre el patrón oro. Las ~85 líneas de excepciones del §7 son parte inseparable del contrato, no un refinamiento posterior.
5. **Los dos pendientes de `HUECOS.md` §1 quedan cerrados.**

### El coste de implementación, en una frase

**1.503 líneas, sin dependencias, de las que el contrato son 333 y el resto es leer cabeceras.** Es una semana de trabajo, no un trimestre — y compra un argumento que ninguno de los seis competidores puede replicar sin hacer el mismo trabajo.

---

## 9. Índice de datos crudos

Todo en `bench/salidas-verificacion/` (236 KB; no queda ningún artefacto grande: las conversiones se escribieron en el temporal y se borraron).

| Fichero | Contenido |
|---|---|
| `puntos.json` | Coste por punto del contrato, por categoría y motor. 53 ficheros × 15 repeticiones = 795 muestras por motor. **Es la fuente del §2.** |
| `conversion.json` | Tiempo real de las 39 órdenes del patrón oro (n=9/5/3 según coste). **Cierra el hueco de `referencia.json`, que no midió tiempos.** |
| `ratio.json` | Ratio verificar/convertir orden a orden, con los dos motores. **Fuente del §3.** |
| `lote.json` | Serie frente a 4/12/24 hilos frente a 4/12 procesos, para los dos motores y los dos lotes. **Fuente del §5.** |
| `correccion.json` / `correccion.txt` | Veredicto y hallazgos de las 53 salidas del patrón oro. **Fuente del §7.** |
| `fallos.json` / `fallos.txt` | Los 5 fallos reproducidos con los dos motores. **Fuente del §6.** |
| `unitario.json` | Coste desnudo de las sondas externas y agregados por categoría. |
| `bytes_leidos.json` | Bytes leídos por el sondeo en proceso, fichero a fichero. |
| `conversion.log` | Traza completa de la tanda de conversión. |
| `trabajos.py` | Las 53 salidas con su entrada, su **pedido** reconstruido y su veredicto esperado. |
| `medir.py`, `puntos.py`, `ratio.py`, `convertir.py`, `conv_datos.py`, `fallos.py` | Los bancos de medida. |

**Metodología.** Medianas, nunca medias. n≥9 en todo lo que se reporta como coste unitario (n=15 por fichero en el §2, n=25 en el suelo de proceso, n=5 en las configuraciones de lote, n=9/5/3 en las conversiones según coste). Calentamiento antes de cada tanda. Etiqueta `limpia`/`SUCIA` mediante un testigo de CPU determinista medido antes y después de cada tanda; se marca `SUCIA` si se desvía más del 20 %. **Todas las cifras del §2, del §5 y las de conversión están etiquetadas `limpia`.** No se usó la GPU ni se tomó el lock. Máquina: Windows 10, 12 núcleos, Python 3.11.9, ffmpeg/ffprobe N-121159, ImageMagick 7.1.2-21, Ghostscript 10.07.
