# Manifiesto — material retirado de `salidas-competidores`

**Generado:** 2026-08-20  
**Ficheros retirados:** 36  ·  **Peso liberado:** 110.5 MB

Esta carpeta es **evidencia forense irreproducible**: los contenedores de ConvertX y
SnapOtter cambian de versión, así que sus fallos no se regeneran. Por eso se conserva,
y por eso la poda ha sido conservadora: **no se ha retirado ninguna prueba**, solo
material redundante.

## Qué se retiró y por qué

**Repeticiones idénticas.** Los ficheros `__r1`/`__r2`/`__r3` con el mismo `sha256` que
el original. Su contenido informativo es «la conversión es determinista», y eso lo
demuestra el hash de esta tabla igual de bien que cuatro copias del mismo fichero.

**Los PNG de 16 bits.** El fallo medido es que SnapOtter *degrada 16 → 8 bits sin*
*avisar ni ofrecer parámetro*. Ese dato vive en la **cabecera IHDR**, no en los píxeles.
Se conservan en `evidencia-16bit/`:

- `*.cabecera.bin` — los primeros 8 KB: firma PNG + IHDR completo
- `*.identify.txt` — la caracterización de `magick identify -verbose`

| Fichero | Bytes | Ancho×Alto | **Profundidad declarada** | sha256 |
|---|---:|---|---:|---|
| `img-16bit2png__convertx.png` | 69945559 | 4000×3000 | **16 bits** | `d8293d19d0dba948…` |
| `img-16bit2png__snapotter.png` | 31720555 | 4000×3000 | **8 bits** | `be747a50e3d26b74…` |

## Inventario completo de lo retirado

| Fichero | Bytes | sha256 | Motivo |
|---|---:|---|---|
| `convertx/aud-flac2mp3__convertx__r1.mp3` | 64592 | `0f719e97f224e628…` | repeticion identica a aud-flac2mp3__convertx.mp3 |
| `convertx/aud-flac2mp3__convertx__r2.mp3` | 64592 | `0f719e97f224e628…` | repeticion identica a aud-flac2mp3__convertx.mp3 |
| `convertx/aud-flac2mp3__convertx__r3.mp3` | 64592 | `0f719e97f224e628…` | repeticion identica a aud-flac2mp3__convertx.mp3 |
| `convertx/img-16bit2png__convertx.png` | 69945559 | `d8293d19d0dba948…` | sustituido por cabecera + identify en evidencia-16bit/ |
| `convertx/img-jpg2png__convertx__r3.png` | 32622 | `2e2124b335874449…` | repeticion identica a img-jpg2png__convertx__r2.png |
| `convertx/img-png2webp__convertx__r1.webp` | 13194 | `6d5d6625fc22917d…` | repeticion identica a img-png2webp__convertx.webp |
| `convertx/img-png2webp__convertx__r2.webp` | 13194 | `6d5d6625fc22917d…` | repeticion identica a img-png2webp__convertx.webp |
| `convertx/img-png2webp__convertx__r3.webp` | 13194 | `6d5d6625fc22917d…` | repeticion identica a img-png2webp__convertx.webp |
| `convertx/img2pdf__convertx__r2.pdf` | 17125 | `cddd89ad03d34ff9…` | repeticion identica a img2pdf__convertx__r1.pdf |
| `convertx/pdf2png__convertx__r1.png` | 16169 | `d996d5dae8ace9ec…` | repeticion identica a pdf2png__convertx.png |
| `convertx/pdf2png__convertx__r2.png` | 16169 | `d996d5dae8ace9ec…` | repeticion identica a pdf2png__convertx.png |
| `convertx/pdf2png__convertx__r3.png` | 16169 | `d996d5dae8ace9ec…` | repeticion identica a pdf2png__convertx.png |
| `convertx/vid-audio__convertx__r1.mp3` | 160826 | `ec06e0304a3f21f7…` | repeticion identica a vid-audio__convertx.mp3 |
| `convertx/vid-audio__convertx__r2.mp3` | 160826 | `ec06e0304a3f21f7…` | repeticion identica a vid-audio__convertx.mp3 |
| `convertx/vid-audio__convertx__r3.mp3` | 160826 | `ec06e0304a3f21f7…` | repeticion identica a vid-audio__convertx.mp3 |
| `convertx/vid2gif__convertx__r1.gif` | 2290244 | `03f07fa28389cb57…` | repeticion identica a vid2gif__convertx.gif |
| `convertx/vid2gif__convertx__r2.gif` | 2290244 | `03f07fa28389cb57…` | repeticion identica a vid2gif__convertx.gif |
| `convertx/vid2gif__convertx__r3.gif` | 2290244 | `03f07fa28389cb57…` | repeticion identica a vid2gif__convertx.gif |
| `snapotter/aud-flac2mp3__snapotter__r1.mp3` | 193768 | `f689fb90700e88fb…` | repeticion identica a aud-flac2mp3__snapotter.mp3 |
| `snapotter/aud-flac2mp3__snapotter__r2.mp3` | 193768 | `f689fb90700e88fb…` | repeticion identica a aud-flac2mp3__snapotter.mp3 |
| `snapotter/aud-flac2mp3__snapotter__r3.mp3` | 193768 | `f689fb90700e88fb…` | repeticion identica a aud-flac2mp3__snapotter.mp3 |
| `snapotter/img-16bit2png__snapotter.png` | 31720555 | `be747a50e3d26b74…` | sustituido por cabecera + identify en evidencia-16bit/ |
| `snapotter/img-jpg2png__snapotter__r1.png` | 52774 | `c6853cab2bad0b30…` | repeticion identica a img-jpg2png__snapotter.png |
| `snapotter/img-jpg2png__snapotter__r2.png` | 52774 | `c6853cab2bad0b30…` | repeticion identica a img-jpg2png__snapotter.png |
| `snapotter/img-jpg2png__snapotter__r3.png` | 52774 | `c6853cab2bad0b30…` | repeticion identica a img-jpg2png__snapotter.png |
| `snapotter/img-png2webp__snapotter__r1.webp` | 14166 | `5b1a48a56f1e0815…` | repeticion identica a img-png2webp__snapotter.webp |
| `snapotter/img-png2webp__snapotter__r2.webp` | 14166 | `5b1a48a56f1e0815…` | repeticion identica a img-png2webp__snapotter.webp |
| `snapotter/img-png2webp__snapotter__r3.webp` | 14166 | `5b1a48a56f1e0815…` | repeticion identica a img-png2webp__snapotter.webp |
| `snapotter/pdf2png__snapotter__r2.zip` | 27713 | `6af6fd46a4811d24…` | repeticion identica a pdf2png__snapotter__r1.zip |
| `snapotter/pdf2png__snapotter__r3.zip` | 27713 | `6af6fd46a4811d24…` | repeticion identica a pdf2png__snapotter__r1.zip |
| `snapotter/vid-audio__snapotter__r1.mp3` | 482263 | `a5612c552f53a28e…` | repeticion identica a vid-audio__snapotter.mp3 |
| `snapotter/vid-audio__snapotter__r2.mp3` | 482263 | `a5612c552f53a28e…` | repeticion identica a vid-audio__snapotter.mp3 |
| `snapotter/vid-audio__snapotter__r3.mp3` | 482263 | `a5612c552f53a28e…` | repeticion identica a vid-audio__snapotter.mp3 |
| `snapotter/vid2gif__snapotter__r2.gif` | 1420106 | `517c7a8ae5b7ad36…` | repeticion identica a vid2gif__snapotter.gif |
| `snapotter/vid2gif__snapotter__r3.gif` | 1420106 | `517c7a8ae5b7ad36…` | repeticion identica a vid2gif__snapotter.gif |
| `snapotter/vid2gif__snapotter__r4.gif` | 1420106 | `517c7a8ae5b7ad36…` | repeticion identica a vid2gif__snapotter.gif |
