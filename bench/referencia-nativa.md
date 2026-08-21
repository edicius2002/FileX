# Referencia nativa de FileX — el patrón oro

**Qué es esto.** La salida que producen los motores nativos (`ffmpeg`, `magick`, `gswin64c`) invocados directamente sobre el corpus, medida objetivamente. Sirve para dos cosas: (1) dar una vara de medir a la evaluación de SnapOtter y ConvertX — decir «su salida es peor» solo es una afirmación medible si existe un «mejor» caracterizado; y (2) fijar las reglas de regresión que FileX tendrá que pasar.

- Salidas: `bench/salidas-referencia/` (53 ficheros derivados + 5 logs)
- Datos crudos: `bench/salidas-referencia/referencia.json` (100 KB; 20 entradas de corpus, 53 de salida, 39 órdenes exactas, 46 reglas, 17 pérdidas catalogadas)
- Informe: este fichero

**Motores.** ffmpeg N-121159 (x264, x265, libvpx-vp9, libopus, libmp3lame, libwebp, libaom, SVT-AV1) · ImageMagick 7.1.2-21 Q16-HDRI (libwebp 1.6.0, libheif 1.21.2 para AVIF) · Ghostscript 10.07.0. **Ausentes:** vips, LibreOffice, Pandoc, Tesseract, qpdf, Calibre, Inkscape.

**Restricciones respetadas.** Solo CPU, máximo 4 hilos (`-threads 4` / `-limit thread 4`), sin NVENC ni CUDA.

> **Sobre los tiempos: no hay ninguno.** La máquina compartía carga con otros agentes, así que cualquier duración sería ruido. Todo lo que sigue es calidad, que es determinista y no se contamina con la carga. Ningún número de este documento es temporal.

---

## 1. Los seis hallazgos que importan

### 1.1 `ffmpeg -i entrada.mkv salida.mp4` pierde la segunda pista de audio, en silencio

Es el fallo más probable de cualquier conversor generalista, porque es el comportamiento **por defecto** del motor más usado. ffmpeg sin `-map` aplica su selección automática: un stream de vídeo y **uno solo** de audio.

| Salida | Orden | Pistas de audio | md5 del PCM por pista |
|---|---|---|---|
| origen `patologico_2pistas.mkv` | — | **2** | `11388652f7b6…` / `538142b9d691…` |
| `2pistas_mkv-to-DEFAULT.mp4` | `ffmpeg -i in.mkv -c:v libx264 … out.mp4` | **1** ❌ | `1f3967eef23f…` |
| `2pistas_mkv-to-MAP0.mp4` | `+ -map 0` | **2** ✅ | `1f3967eef23f…` / `0b086770279e…` |
| `2pistas_mkv-to-COPY.mp4` | `-map 0 -c copy` | **2** ✅ | idénticos al origen |

Las dos pistas del origen tienen contenido **distinto** (md5 del PCM diferente), así que la pérdida es real y detectable, no una duplicación inocua. MP4 admite perfectamente varias pistas de audio: **esto no es una limitación de formato, es un fallo de uso del motor.** El grafo de conversión debe modelar la arista MKV→MP4 con la restricción `-map 0`, no con la invocación ingenua.

### 1.2 Un TIFF de 16 bits **no** tiene por qué perder profundidad al pasar a PNG

Contrariamente a lo que sugiere la pregunta, ImageMagick conserva los 16 bits **por defecto**:

| Salida | Profundidad | Colores únicos | RMSE vs origen | Bytes |
|---|---|---|---|---|
| `patologico_16bit.tif` (origen) | 16 | 11 935 622 | — | 72 001 016 |
| `16bit_tif-to-default.png` | **16** | **11 935 622** | **0** (idéntico) | 61 849 791 |
| `16bit_tif-to-d8.png` (forzado) | 8 | 2 116 571 | 0,00112 (PSNR 59,0 dB) | 18 943 503 |
| `16bit_tif-to.jpg` q85 | 8 | 612 123 | 0,01721 (PSNR 35,3 dB) | 1 571 956 |
| `16bit_tif-to.webp` q80 | 8 | 386 041 | 0,01829 (PSNR 34,8 dB) | 647 580 |

Consecuencia para la evaluación: **si un competidor entrega un PNG de 8 bits desde este TIFF, eso es un fallo del motor, no una pérdida inevitable**, y el coste está cuantificado (PSNR 59,0 dB; se descartan 9,8 millones de tonos distinguibles). El PNG de 8 bits es la salida correcta solo si el usuario la pidió.

### 1.3 AVIF con pérdida degrada el canal alfa; WebP con pérdida **no**

Medido aislando el canal alfa y comparándolo con el del origen:

| Salida | PSNR del canal alfa | ¿alfa exacto? |
|---|---|---|
| `alpha_png-to.png8.png` | ∞ | sí |
| `alpha_png-to.webp` (q80, con pérdida) | **∞** | **sí** |
| `alpha_png-to.avif` (q50) | **46,0 dB** | **no** |
| `tipico_png-to.avif` (alfa 100 % opaco) | 71,4 dB | no — `min(alfa)` cae a 0,9939 |

El último caso es el más revelador: AVIF toma un canal alfa **completamente opaco** y lo devuelve con valores 0,9939–0,9998. Una comprobación ingenua de «¿el alfa sigue ahí?» pasa, pero el alfa ya no es exactamente 1,0. WebP, en cambio, comprime el RGB con pérdida y deja el plano alfa intacto bit a bit.

### 1.4 ImageMagick aplana la transparencia sobre **negro**, no sobre blanco

| Fichero | Píxel (0,0), zona 100 % transparente en el origen |
|---|---|
| `alpha.png` | `srgba(0,0,0,0)` |
| `alpha_png-to.jpg` (por defecto) | `srgb(0,0,0)` ← **negro** |
| `alpha_png-to-flat.jpg` (`-background white -alpha remove`) | `srgb(255,255,255)` |

Que JPEG pierda el alfa es inevitable. Que el fondo salga negro **no lo es**: es una decisión del motor, y casi nunca es la que espera el usuario. Es una distinción que el grafo debe registrar: la arista `→JPEG` tiene un parámetro obligatorio (color de fondo), no solo un coste.

### 1.5 El alfa «trivial» falsea las comprobaciones

`tipico.png` se declara con canal alfa (`srgba`, 16 bits), pero su alfa es **enteramente opaco** (min = max = 1,0). Al convertir a WebP el canal desaparece — y eso **no es una pérdida**. Una regla de regresión que exija «si la entrada tiene alfa, la salida debe tener alfa» generaría un falso positivo aquí.

La regla correcta usa la **no trivialidad**: exigir la conservación del alfa solo si `min(canal alfa) < 1,0`. En el corpus solo `alpha.png` lo cumple.

### 1.6 Ghostscript conserva el texto en PDF→PDF; rasterizar lo destruye

| Fichero | Páginas | Texto extraíble | Caracteres | sha256 del texto |
|---|---|---|---|---|
| `tipico_texto.pdf` (origen) | 1 | sí | 180 | `be5a29a812723da8…` |
| `tipico_texto_pdf-to-gs.pdf` (`pdfwrite`) | 1 | sí | 180 | **`be5a29a812723da8…`** (idéntico) |
| `tipico_texto_rasterizado.pdf` (PDF→PNG→PDF) | 1 | **no** | 0 | — |
| `trivial.pdf`, `patologico_escaneado.pdf`, `escaneado_d1/d2/d3.pdf` | 1 | no | 0 | — (son ráster puro) |

Trampa detectada: **`txtwrite` emite basura de 1–3 caracteres en PDF que no tienen texto real.** `alpha_png-to.pdf` devuelve `"FX"` (2 caracteres) sin contener ninguna capa de texto. El umbral de «tiene texto» debe ser ≥ 10 caracteres imprimibles, no `> 0`.

Segunda trampa: el texto del origen ya sale mal extraído (`acentos aeiou n \x91`) porque el PDF usa fuentes base-14 sin `ToUnicode` limpio para la «ñ». **La referencia es la salida de `txtwrite` sobre el origen, no una cadena ideal.** Comparar contra lo que «debería decir» produciría fallos falsos en todos los motores.

---

## 2. Caracterización de las salidas

Todos los campos (dimensiones, profundidad, espacio de color, alfa, pistas, duración, bitrate, tamaño, texto extraíble, hashes) están en `referencia.json`. Aquí van los extractos con carga de decisión.

### 2.1 Imagen

| Salida | Geometría | Prof. | Alfa | Colores | PSNR RGB | Bytes |
|---|---|---|---|---|---|---|
| `tipico_png-to.webp` q80 | 1920×1080 | 8 | no (era trivial) | 2 130 | 48,69 dB | 13 516 |
| `tipico_png-to.avif` q50 | 1920×1080 | 12 | sí (degradado) | 5 510 | 46,72 dB | **1 595** |
| `tipico_png-to.jpg` q85 | 1920×1080 | 8 | no | 2 024 | 48,70 dB | 40 963 |
| `alpha_png-to.webp` q80 | 200×200 | 8 | **sí, exacto** | 1 447 | 43,87 dB* | 2 496 |
| `alpha_png-to.avif` q50 | 200×200 | 8 | sí, degradado | 815 | 38,78 dB* | **1 670** |
| `alpha_png-to.jpg` q85 | 200×200 | 8 | no (fondo negro) | 3 135 | — | 4 643 |
| `alpha_png-to.png8.png` | 200×200 | 8 | sí, exacto | 210 | ∞ | 2 780 |
| `trivial_png-to.webp` q80 | 64×64 | 8 | no | **2** ❌ | 51,95 dB | 94 |
| `trivial_png-to-lossless.webp` | 64×64 | 8 | no | **1** ✅ | ∞ | **42** |
| `tipico_jpg-to.png` | 1920×1080 | 8 | no | 1 605 | ∞ | 32 622 |
| `tipico_webp-to.png` | 1920×1080 | 8 | no | 2 318 | ∞ | 64 232 |
| `tipico_webp-to.jpg` q85 | 1920×1080 | 8 | no | 3 491 | 48,42 dB | 42 748 |

\* PSNR del RGB compuesto sobre blanco. Todas las geometrías se conservan exactamente; el espacio de color se mantiene en sRGB en todos los casos.

**`trivial.png` merece atención.** Es 64×64 de un solo color (1 color único, paleta de 1 bit). Con WebP con pérdida sale a 94 B y **2 colores** — el codificador inventa un tono. Con `webp:lossless=true` sale a **42 B y 1 color**: más pequeño *y* exacto. Aplicar codificación con pérdida a grafismo o a imágenes de paleta es simplemente una elección mala, no un compromiso.

### 2.2 PDF

| Salida | Páginas | MediaBox / píxeles | Texto | Bytes |
|---|---|---|---|---|
| `tipico_texto_pdf-to-p1.png` (gs, 150 dpi) | 1 | 1240×1754 px | destruido (esperado) | 15 804 |
| `tipico_texto_pdf-to-p1.jpg` (gs, 150 dpi, q85) | 1 | 1240×1754 px | destruido | 71 269 |
| `tipico_texto_pdf-to.tif` (gs `tiff24nc`) | 1 | 1240×1754 px | destruido | **6 533 038** |
| `tipico_texto_pdf-to-gs.pdf` (`pdfwrite`) | 1 | 595×842 pt | **conservado, idéntico** | 3 291 |
| `patologico_escaneado_pdf-to-p1.png` | 1 | 970×1344 px | n/a (origen sin texto) | 1 908 177 |
| `trivial_pdf-to-p1.png` | 1 | 833×625 px | n/a | 4 359 |
| `tipico_png-to.pdf` | 1 | **1920×1080 pt** = 677×381 mm | — | 17 153 |
| `tipico_png-to-150dpi.pdf` | 1 | 922×518 pt = 325×183 mm | — | 17 187 |

Dos observaciones con consecuencias:

**La resolución sale bien.** 595 pt × 150/72 = 1239,6 → 1240 px. La relación `px = pt · dpi / 72` se cumple en las tres rasterizaciones y sirve de regla comprobable (P4).

**El TIFF de Ghostscript sale sin comprimir** (`%[compression] = None`): 6,5 MB frente a los 15 KB del PNG del mismo contenido. Factor ~413. `tiff24nc` no aplica LZW ni ZIP. Cualquier conversor que use este dispositivo sin más entrega ficheros absurdos.

**Imagen→PDF sin densidad declarada produce páginas ridículas.** ImageMagick mapea 1 px → 1 pt, así que 1920×1080 px se convierte en una página de 677×381 mm. Es corregible (`-density 150 -units PixelsPerInch` → 325×183 mm), luego es un fallo de uso, no una limitación.

### 2.3 Vídeo

| Salida | Contenedor | Duración | V | A | Fotogramas | PSNR (y) | Bytes |
|---|---|---|---|---|---|---|---|
| `tipico.mp4` (origen) | mp4 | 20,000 s | 1 | 1 | 600 | — | 16 246 490 |
| `tipico_mp4-to.webm` (VP9 crf33 + Opus 96k) | webm | 20,023 s | 1 | 1 | **600** | 46,15 dB | 17 014 670 |
| `tipico_mp4-to.mkv` (`-c copy`) | matroska | 20,023 s | 1 | 1 | **600** | ∞ | 16 235 751 |
| `patologico_2pistas.mkv` (origen) | matroska | 10,023 s | 1 | **2** | 300 | — | 4 079 196 |
| `2pistas_mkv-to-DEFAULT.mp4` | mp4 | 10,033 s | 1 | **1** ❌ | 300 | 45,58 dB | 3 859 442 |
| `2pistas_mkv-to-MAP0.mp4` | mp4 | 10,033 s | 1 | **2** ✅ | 300 | 45,58 dB | 3 966 842 |
| `2pistas_mkv-to-COPY.mp4` | mp4 | 10,031 s | 1 | **2** ✅ | 300 | ∞ | 4 085 275 |
| `trivial_mp4-to.webm` (VP9 crf33) | webm | 5,000 s | 1 | 0 | **120** | **29,63 dB** | 635 908 |
| `trivial_mp4-to-palette.gif` | gif | 5,000 s | 1 | 0 | 60 (12 fps) | — | **609 893** |
| `trivial_mp4-to-naive.gif` | gif | 5,000 s | 1 | 0 | 60 (12 fps) | — | **394 712** |

**Ningún fotograma perdido en ninguna conversión.** 600→600, 300→300, 120→120. Los GIF pasan a 60 porque se pidió 12 fps explícitamente.

**El GIF ingenuo pesa un 35 % menos que el bueno.** El de paleta adaptada (`palettegen`/`paletteuse`) ocupa 610 KB; el que usa la paleta genérica de ffmpeg, 395 KB. **Menor tamaño no implica mejor conversión** — el ingenuo es más pequeño precisamente porque tira color. Cualquier evaluación que ordene por tamaño premiaría al peor.

**`trivial.mp4` cae a 29,6 dB de PSNR en VP9.** Es contenido sintético con bordes duros, que VP9 castiga a crf 33. Un umbral de PSNR ≥ 40 dB es razonable para fotografía y **no** para sintético; la regla V8 lo recoge como aviso, no como fallo.

**Detalle que romperá las pruebas si se ignora:** en MKV y WebM, `ffprobe` devuelve `nb_frames`, `duration` y `bit_rate` **vacíos por pista**. Hay que contar con `-count_frames` y leer la duración del contenedor. Además, `ffprobe -count_frames` sobre WebM con Opus escupe `Error parsing Opus packet header` por stderr sin que eso afecte al resultado: no debe interpretarse como fallo de conversión.

**Y otro:** el remux MP4→MKV cambia la base de tiempos (1/15360 → 1/1000), así que el `framemd5` **completo** difiere aunque los píxeles sean idénticos. Comparando solo la columna del hash por fotograma:

```
tipico.mp4         6b48c50b0440bb586707990b8c81c199
tipico_mp4-to.mkv  6b48c50b0440bb586707990b8c81c199   ← idéntico
patologico_2pistas.mkv    acb2518c6349917fa87facf3a0ad430d
2pistas_mkv-to-COPY.mp4   acb2518c6349917fa87facf3a0ad430d   ← idéntico
2pistas_mkv-to-MAP0.mp4   883fd8c87f7db24431d3381e6dd66ae8   ← recodificado
```

### 2.4 Audio

| Salida | Códec | Canales | Frec. | Duración | md5 del PCM | Bytes |
|---|---|---|---|---|---|---|
| `trivial.wav` (origen) | pcm_s16le | 1 | 44 100 | 8,000 s | `b1cdfb164f23…` | 705 678 |
| `trivial_wav-to.flac` | flac 16 | 1 | 44 100 | 8,000 s | **`b1cdfb164f23…`** | 104 318 |
| `tipico.flac` (origen) | flac 16 | 1 | 44 100 | 8,000 s | `b1cdfb164f23…` | 104 318 |
| `tipico_flac-to.wav` | pcm_s16le | 1 | 44 100 | 8,000 s | **`b1cdfb164f23…`** | 705 678 |
| `trivial_wav-to.mp3` 192k | mp3 | 1 | 44 100 | 8,000 s | `18272a43dc9f…` | 193 767 |
| `trivial_wav-to.opus` 96k | opus | 1 | **48 000** | **8,0065 s** | `45bb8b2dc681…` | 116 918 |
| `trivial_wav-to.m4a` 192k | aac | 1 | 44 100 | 8,000 s | `f5808b8f9505…` | 131 397 |
| `tipico.mp3` (origen) | mp3 | 1 | 44 100 | 8,000 s | `f5ddaa6410d8…` | 64 591 |
| `tipico_mp3-to.wav` | pcm_s16le | 1 | 44 100 | 8,000 s | **`f5ddaa6410d8…`** | 705 678 |
| `tipico_mp3-to.flac` | **flac 24 (s32)** | 1 | 44 100 | 8,000 s | `984b4619d1c3…` | **398 105** |
| `tipico_mp4-audio-copy.m4a` (`-c:a copy`) | aac | 1 | 44 100 | 20,000 s | **`d0bd638ebac7…`** (= pista del mp4) | 177 427 |
| `tipico_mp4-audio.mp3` 192k | mp3 | 1 | 44 100 | 20,016 s | `7e78a82b153c…` | 482 262 |

**La cadena sin pérdida es exacta.** WAV↔FLAC comparte md5 del PCM (`b1cdfb164f23…`) en las dos direcciones. Es la comprobación más limpia del conjunto y debe ser una prueba de regresión dura.

**MP3→WAV también conserva el PCM exacto** (`f5ddaa6410d8…`): la conversión con pérdida→sin pérdida no degrada nada más, simplemente no recupera nada. Coste: 64 KB → 706 KB, ×10,9 sin ninguna información añadida.

**MP3→FLAC infla la profundidad a 24 bits.** ffmpeg ve que el MP3 decodifica a coma flotante y elige `s32`/24 bits: 398 105 B frente a los ~104 000 B que ocuparía un FLAC de 16 bits del mismo contenido. Cuadruplica el fichero sin añadir un solo bit de información — el origen con pérdida no tiene más de 16 bits efectivos. El md5 «distinto» de esa fila es un artefacto de mi medición (trunco a s16 para comparar), no una corrupción: el número de muestras es idéntico (705 600 en los tres ficheros).

**Opus obliga a 48 kHz y añade pre-skip.** 44 100 → 48 000 Hz y 8,000 → 8,0065 s, siempre. Cualquier tolerancia de duración por debajo de ±10 ms marcará Opus como fallo incorrectamente.

**Extraer audio sin recodificar es exacto.** `-c:a copy` produce un md5 del PCM idéntico al de la pista embebida en el MP4 (`d0bd638ebac7…`). Recodificar a MP3 lo cambia por necesidad y además alarga la duración a 20,0156 s (padding del codificador).

### 2.5 Datos

No hay motor nativo de datos entre los instalados: ni ffmpeg, ni ImageMagick, ni Ghostscript tocan CSV o JSON. Para producir la referencia usé la **biblioteca estándar de Python 3.11 como instrumento de medida**, no como motor candidato — su módulo `csv` implementa RFC 4180 y sirve de árbitro.

`patologico_bom.csv` (88 B) contiene exactamente:

| id | nombre | notas |
|---|---|---|
| `1` | `Pérez, Juan` (coma dentro del campo) | `dijo "hola" y se fue` (comillas escapadas `""`) |
| `2` | `Ñandú` (no ASCII) | `salto\nde linea` (salto embebido) |

Más un BOM UTF-8 al principio. **4 saltos de línea físicos, 3 filas lógicas, 3 campos en cada una.**

Referencias producidas:

| Salida | Bytes | BOM | Filas | Campos | sha256 de valores |
|---|---|---|---|---|---|
| `patologico_bom_csv-to.json` | 174 | no | 2 objetos | 3 claves | canónico `d12fe2bd6be14ef3…` |
| `patologico_bom_csv-to-normalizado.csv` | 85 | **no** | 3 | [3,3,3] | **`cf4cc37f35c9c045…`** (= origen) |
| `tipico_json-to.csv` | 14 | no | 3 | [2,2,2] | `9557e2309839572b…` |

El sha256 de valores del CSV normalizado **coincide con el del origen**: la ida y vuelta es semánticamente exacta aunque los bytes difieran (se descarta el BOM). Ese hash es el criterio de igualdad, no el hash del fichero.

Los tres modos de fallo que este fichero está diseñado para provocar:

1. **Partir por coma sin respetar comillas** → `[3, 4, 3]` campos en lugar de `[3, 3, 3]`.
2. **Leer con `utf-8` en vez de `utf-8-sig`** → la primera clave del JSON sale como `"﻿id"` en vez de `"id"`.
3. **Contar líneas físicas** → 4 filas en vez de 3, partiendo `salto\nde linea` en dos.

---

## 3. Criterio de «conversión correcta» por categoría

Estas son las reglas de regresión. Cada una está escrita como una comprobación ejecutable con una severidad. `referencia.json → reglas_regresion` las trae en forma estructurada (46 en total).

### Generales (aplican a todo)

| id | Regla | Comprobación | Severidad |
|---|---|---|---|
| G1 | La salida existe, pesa > 0 y el motor devuelve 0 | `getsize > 0 and rc == 0` | fallo |
| G2 | La salida se abre sin errores con la sonda de su categoría | `ffprobe -v error` / `magick identify` / `gswin64c` sin stderr | fallo |
| G3 | El formato real coincide con la extensión pedida | `identify %m` o `ffprobe format_name` | fallo |
| G4 | No es un marcador de posición ni una página de error | colores únicos > 1 salvo que la entrada también lo sea | fallo |

### Imagen

| id | Regla | Comprobación | Severidad |
|---|---|---|---|
| I1 | Ancho y alto exactos salvo redimensión pedida | `%w,%h == entrada` | fallo |
| I2 | Si el alfa de entrada es **no trivial** (`min < 1,0`) y el destino lo admite (PNG/WebP/AVIF/TIFF), se conserva | `%[channels]` contiene `a` **y** `min(alfa) < 0,999` | fallo |
| I3 | Si el destino no admite alfa (JPEG), el aplanado va sobre **blanco** | píxel de zona transparente == `srgb(255,255,255)` ±2 | aviso |
| I4 | No se pierde profundidad si el destino la admite: 16 bits → PNG/TIFF de 16 bits | `%z == entrada.%z` cuando destino ∈ {PNG, TIFF} | fallo |
| I5 | 16 bits → JPEG/WebP baja a 8: **inevitable** | `%z == 8` aceptado | informativo |
| I6 | Conversión declarada sin pérdida: píxeles idénticos | `compare -metric RMSE == 0` | fallo |
| I7 | Con pérdida a q80–85 sobre fotografía: PSNR ≥ 40 dB | `compare -metric PSNR >= 40` | aviso |
| I8 | Imagen de paleta o grafismo (≤ 256 colores) va a WebP/AVIF **sin pérdida** | `salida.%k <= entrada.%k` | aviso |
| I9 | El espacio de color se conserva; no aparecen saltos a CMYK ni Gray | `%[colorspace] == entrada` | fallo |
| I10 | El número de imágenes (fotogramas/páginas) se conserva | `len(identify) == entrada` | fallo |

### PDF

| id | Regla | Comprobación | Severidad |
|---|---|---|---|
| P1 | Número de páginas exacto | `pdfpagecount == entrada` | fallo |
| P2 | PDF→PDF conserva la capa de texto íntegra | `sha256(txtwrite salida) == sha256(txtwrite entrada)` | fallo |
| P3 | PDF→imagen destruye el texto: **inevitable** | `texto_extraible == False` aceptado | informativo |
| P4 | PDF→imagen respeta el DPI pedido | `abs(px - pt·dpi/72) <= 1` | fallo |
| P5 | Un PDF escaneado sigue sin texto: no es fallo salvo que se pidiera OCR | si la entrada no tiene texto, no se exige a la salida | informativo |
| P6 | Umbral de «tiene texto» ≥ 10 caracteres imprimibles | `len(texto.strip()) >= 10` | informativo |
| P7 | Imagen→PDF con densidad declarada; 1 px → 1 pt es inaceptable | `MediaBox_pt == px · 72 / densidad` | aviso |
| P8 | PDF→TIFF usa compresión | `%[compression] != 'None'` | aviso |

### Vídeo

| id | Regla | Comprobación | Severidad |
|---|---|---|---|
| V1 | Duración dentro de ±1 fotograma (o ±50 ms si el fps es desconocido) | `abs(Δdur) <= max(1/fps, 0.05)` | fallo |
| V2 | Número de fotogramas exacto si no se cambia el fps | `ffprobe -count_frames nb_read_frames == entrada` | fallo |
| V3 | **Todas** las pistas de audio se conservan, en número y orden | `count(audio) == entrada` y los md5 del PCM siguen siendo distintos entre sí | fallo |
| V4 | Los subtítulos se conservan si el contenedor los admite | `count(subtitle) == entrada` | fallo |
| V5 | Las etiquetas de idioma y título se conservan | `stream_tags=language,title == entrada` | aviso |
| V6 | Remux sin recodificar: hash por fotograma idéntico | `md5(última columna de framemd5) == entrada` | fallo |
| V7 | Dimensiones y fps se conservan si no se pide reescalado | `width,height,r_frame_rate == entrada` | fallo |
| V8 | Recodificación a calidad por defecto: PSNR de luminancia ≥ 40 dB en contenido fotográfico | `ffmpeg -lavfi psnr → y >= 40` | aviso |
| V9 | Vídeo→GIF calcula la paleta a partir del clip | comparación visual o PSNR frente al fotograma origen | aviso |

Notas de implementación: V2 exige `-count_frames` porque MKV/WebM devuelven `nb_frames` vacío. V4 no está ejercitado: ninguna pieza del corpus lleva subtítulos. V5 tampoco discrimina: `patologico_2pistas.mkv` no trae etiquetas de idioma.

### Audio

| id | Regla | Comprobación | Severidad |
|---|---|---|---|
| A1 | Duración dentro de ±10 ms | `abs(Δdur) <= 0.010` | fallo |
| A2 | Número de canales y disposición se conservan | `channels == entrada` | fallo |
| A3 | Frecuencia de muestreo se conserva, salvo Opus (48 kHz obligatorio) | `sample_rate == entrada` ∨ (`codec == opus` ∧ `48000`) | fallo |
| A4 | Cadena sin pérdida (WAV↔FLAC↔ALAC): PCM idéntico bit a bit | `ffmpeg -f md5 -c:a pcm_s16le` == entrada | fallo |
| A5 | Extraer audio con `-c:a copy` da un PCM idéntico al embebido | `md5(PCM salida) == md5(PCM 0:a:0)` | aviso |
| A6 | La profundidad **no debe inflarse**: origen con pérdida → FLAC no sale a 24 bits | `bits_per_raw_sample <= 16` si el origen es con pérdida | aviso |
| A7 | Con pérdida → sin pérdida no recupera calidad | regla de coste para el grafo, no de corrección | informativo |

### Datos

| id | Regla | Comprobación | Severidad |
|---|---|---|---|
| D1 | Número de filas **lógicas** conservado (los saltos dentro de comillas no cuentan) | `len(list(csv.reader(...))) == 3` | fallo |
| D2 | Número de campos por fila constante e igual al original | `[len(f) for f in filas] == [3,3,3]` | fallo |
| D3 | Contenido íntegro, incluidos los no ASCII | `sha256(json.dumps(filas, ensure_ascii=False, sort_keys=True)) == cf4cc37f35c9c045…` | fallo |
| D4 | El BOM no se cuela en el primer nombre de campo | `cabecera[0] == 'id'`, no `'﻿id'` | fallo |
| D5 | La salida es UTF-8 válido, sin `?` ni U+FFFD sustituyendo a no ASCII | `decode('utf-8')` sin excepción y sin `�` | fallo |
| D6 | Las comillas escapadas `""` se decodifican a una y se reescapan al escribir | valor == `dijo "hola" y se fue`; el CSV reescrito contiene `""hola""` | fallo |
| D7 | El salto de línea embebido se conserva como `\n` del valor | valor == `salto\nde linea` | fallo |
| D8 | JSON→CSV / CSV→JSON: JSON válido y sin perder claves | `json.loads` sin excepción y `set(claves) == set(cabecera)` | fallo |

---

## 4. Pérdidas inevitables frente a fallos del motor

Esta es la tabla que el grafo de conversión necesita para asignar coste a cada arista. La columna **inevitable** distingue lo que el formato de destino impone de lo que el motor eligió mal.

| Conversión | Qué se pierde | ¿Inevitable? | Cuantificado |
|---|---|---|---|
| `* → JPEG` | canal alfa | **sí** | — |
| `* → JPEG` | profundidad > 8 bits | **sí** | — |
| `* → JPEG` | *el color del aplanado* | **no** | ImageMagick usa negro; lo esperable es blanco |
| `16 bits → WebP` | profundidad > 8 bits | **sí** | 11 935 622 → 386 041 colores únicos |
| `16 bits → PNG` | **nada** | — | RMSE 0. Un PNG de 8 bits aquí es un **fallo**: cuesta 59,0 dB y 9,8 M de tonos |
| `→ AVIF con pérdida` | exactitud del canal alfa | **sí** | alfa a 46,0 dB; incluso un alfa opaco baja a 71,4 dB (min 0,9939) |
| `paleta/1 bit → WebP con pérdida` | exactitud de los colores planos | **no** | `webp:lossless=true` da 42 B y 1 color; con pérdida, 94 B y 2 |
| `PDF → PNG/JPEG/TIFF` | texto, vectores, marcadores, enlaces, metadatos, capas | **sí** | 180 → 0 caracteres. Además fija la resolución |
| `PDF → PDF` (gs `pdfwrite`) | **nada del texto** | — | sha256 del texto idéntico. Perderlo aquí es un **fallo** |
| `imagen → PDF` | nada del píxel; se *gana* una caja de página arbitraria | **no** | sin densidad: 677×381 mm; a 150 dpi: 325×183 mm |
| `vídeo → GIF` | audio, color de 24 bits, suavidad temporal | **sí** | 24 fps → 12 fps, paleta ≤ 256 |
| `vídeo → GIF` | *calidad de la paleta* | **no** | genérica vs `palettegen`; la mala pesa un 35 % **menos** |
| `MKV → MP4` recodificando | fidelidad de píxel | **sí** si hay que recodificar | 45,7 dB con x264 crf 23 — evitable del todo con `-c copy` (PSNR ∞) |
| `MKV → MP4` sin `-map 0` | **todas las pistas de audio salvo la primera** | **no** | 2 → 1 pistas, con PCM distinto entre sí. Fallo de uso, no de formato |
| `* → Opus` | frecuencia original y alineación exacta | **sí** | 44 100 → 48 000 Hz; 8,000 → 8,0065 s |
| `con pérdida → sin pérdida` | nada más, pero no recupera nada | **sí** | PCM exacto (`f5ddaa64…`); 64 KB → 706 KB |
| `MP3 → FLAC` a 24 bits | *nada; se desperdicia espacio* | **no** | 398 KB en vez de ~104 KB, sin información añadida |
| remux de contenedor | nada del píxel; cambian las marcas de tiempo | — | `framemd5` completo difiere (1/15360 → 1/1000); el hash por fotograma es idéntico |
| `CSV → JSON` | los tipos: todo queda como cadena | **sí** | `"1"` y no `1` es correcto salvo que se pida inferencia |
| `CSV con BOM → *` | nada si se lee con `utf-8-sig` | **no** | con `utf-8` a secas, la clave sale como `"﻿id"`. **Fallo** |

**Cómo leerla para el grafo.** Las filas marcadas «inevitable = sí» son coste intrínseco de la arista: FileX debe asignarles un peso y avisar al usuario, pero no puede evitarlas. Las marcadas «no» son coste que un buen motor pone a cero — y por tanto el sitio exacto donde FileX puede ganar a SnapOtter y a ConvertX sin ser más rápido, solo siendo más correcto.

---

## 5. No evaluable con los motores presentes

No instalé nada. Estas conversiones necesitan motores ausentes y quedan explícitamente fuera de la referencia:

| Conversión | Motor necesario |
|---|---|
| DOCX/XLSX/PPTX/ODT ↔ PDF | LibreOffice (`soffice`) |
| Markdown/HTML/DOCX ↔ documento | Pandoc |
| EPUB/MOBI/AZW3 ↔ otros | Calibre (`ebook-convert`) |
| SVG → PNG/PDF con fidelidad tipográfica | Inkscape o resvg |
| PDF escaneado → PDF con capa de texto (OCR) | Tesseract u ocrmypdf |
| PDF linealizado / reparado / cifrado | qpdf |
| imagen → imagen con libvips | vips |

Sobre el OCR: `patologico_escaneado.pdf` y `escaneado_d1/d2/d3.pdf` están en el corpus justamente para eso. Lo que sí queda establecido es su **estado de partida**: los cuatro tienen **0 caracteres extraíbles**. Cuando haya un motor de OCR, ese es el punto de comparación.

Sobre qpdf: Ghostscript `pdfwrite` cubre parcialmente la recompresión de PDF (y la cubre bien: texto idéntico), pero no la linealización ni el cifrado.

---

## 6. Errores y avisos encontrados

Ninguna de las 39 conversiones falló. Los logs (`bench/salidas-referencia/logs/`) están vacíos salvo el progreso de ffmpeg. Dos avisos que **no** son fallos y que hay que saber ignorar al automatizar:

1. `[opus @ …] Error parsing Opus packet header` — lo emite `ffprobe -count_frames` sobre WebM con audio Opus. No afecta al recuento de fotogramas ni al fichero.
2. `not matching timebases found between first input: 1/16000 and second input 1/1000` — lo emite el filtro `psnr` al comparar un remux con su origen. El PSNR resultante (∞) es correcto.

Y una limitación de la herramienta de medida: **`magick compare -metric SSIM` devuelve 0 para imágenes idénticas** en esta build de ImageMagick 7.1.2, es decir, se comporta como una disimilitud, no como SSIM. No lo usé para nada. `PSNR` (120 = idéntico) y `RMSE` (0 = idéntico) sí se comportan como se espera y son los que sustentan todas las cifras de este informe.

---

## 7. Cómo usar esto

**Para evaluar a un competidor.** Cargar `referencia.json`, localizar la orden equivalente en `ordenes[]`, comparar la caracterización de su salida contra la entrada correspondiente de `salidas[]` y evaluar las reglas de `reglas_regresion` de la categoría. Una regla de severidad `fallo` que no pasa es un defecto atribuible. Una de severidad `informativo` que no pasa es una pérdida inevitable y no cuenta.

**Para las regresiones de FileX.** Las 46 reglas son ejecutables tal cual. Las de severidad `fallo` deberían bloquear la integración; las de `aviso` deberían generar un informe.

**Los invariantes más duros**, los que valen como aserciones exactas:

```
PCM sin pérdida  : b1cdfb164f2319cd862dbf24a43679e5   (trivial.wav ≡ tipico.flac)
PCM de mp3       : f5ddaa6410d81575bcdcc6b5b3a8f59b   (tipico.mp3 → wav)
PCM del mp4      : d0bd638ebac7…                      (tipico.mp4 0:a:0 ≡ m4a copiado)
texto del PDF    : be5a29a812723da8…                  (tipico_texto.pdf ≡ pdfwrite)
fotogramas mp4   : 6b48c50b0440bb586707990b8c81c199   (tipico.mp4 ≡ remux mkv)
fotogramas mkv   : acb2518c6349917fa87facf3a0ad430d   (2pistas.mkv ≡ remux mp4 copy)
valores del CSV  : cf4cc37f35c9c045…                  (origen ≡ normalizado)
pistas de audio  : patologico_2pistas.mkv = 2, y deben seguir siendo 2
16 bits          : patologico_16bit.tif → PNG debe dar %z = 16 y RMSE 0
```
