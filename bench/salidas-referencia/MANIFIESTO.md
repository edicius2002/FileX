# Manifiesto — salidas de referencia (patrón oro)

**Generado:** 2026-08-20  
**Ficheros:** 53  ·  **Peso:** 195.4 MB

Las **53 salidas caracterizadas** del patrón oro. Se retiran del repositorio porque
`referencia.json` documenta las **39 órdenes exactas** que las reproducen con los motores
nativos.

Lo que se conserva versionado es lo que **no** se regenera: `referencia.json` —con sus
46 reglas de regresión, 17 pérdidas catalogadas y los hashes de fotogramas— y los logs
de ejecución.

## Cómo regenerarlo

Cada fila lleva la orden que la produce. Ejecutar desde la raíz del proyecto con los
motores nativos (`ffmpeg` N-121159, ImageMagick 7.1.2 Q16-HDRI, Ghostscript 10.07).

La verificación es el `sha256` de esta tabla. Para los casos en que el contenedor no es
determinista, `referencia.json` conserva además los hashes de fotogramas de vídeo.

## Inventario

| Fichero | Bytes | sha256 | Orden exacta |
|---|---:|---|---|
| `audio/tipico_flac-to.mp3` | 193767 | `1b743f57aa2227a0…` | `ffmpeg -threads 4 -i tipico.flac -c:a libmp3lame -b:a 192k out.mp3` |
| `audio/tipico_flac-to.opus` | 116918 | `60d52cbda381137f…` | `ffmpeg -threads 4 -i tipico.flac -c:a libopus -b:a 96k out.opus` |
| `audio/tipico_flac-to.wav` | 705678 | `b5fb614afefa1581…` | `ffmpeg -threads 4 -i tipico.flac -c:a pcm_s16le out.wav` |
| `audio/tipico_mp3-to.flac` | 398105 | `bd935c4b049cf2f0…` | `ffmpeg -threads 4 -i tipico.mp3 -c:a flac out.flac` |
| `audio/tipico_mp3-to.wav` | 705678 | `bde5ea216c1ca309…` | `ffmpeg -threads 4 -i tipico.mp3 -c:a pcm_s16le out.wav` |
| `audio/tipico_mp4-audio-copy.m4a` | 177427 | `f85a028140263568…` | `ffmpeg -threads 4 -i tipico.mp4 -vn -c:a copy out.m4a` |
| `audio/tipico_mp4-audio.flac` | 1004509 | `2c3c9031c3a18f89…` | — |
| `audio/tipico_mp4-audio.mp3` | 482262 | `94018a38d384d367…` | `ffmpeg -threads 4 -i tipico.mp4 -vn -c:a libmp3lame -b:a 192k out.mp3` |
| `audio/trivial_wav-to.flac` | 104318 | `b4950a7155d749de…` | `ffmpeg -threads 4 -i trivial.wav -c:a flac out.flac` |
| `audio/trivial_wav-to.m4a` | 131397 | `965d6ebd2d6710a8…` | `ffmpeg -threads 4 -i trivial.wav -c:a aac -b:a 192k out.m4a` |
| `audio/trivial_wav-to.mp3` | 193767 | `1b743f57aa2227a0…` | `ffmpeg -threads 4 -i trivial.wav -c:a libmp3lame -b:a 192k out.mp3` |
| `audio/trivial_wav-to.opus` | 116918 | `864a9e69841216a4…` | `ffmpeg -threads 4 -i trivial.wav -c:a libopus -b:a 96k out.opus` |
| `datos/patologico_bom_csv-to-normalizado.csv` | 85 | `6d2c9d92a3aed95c…` | `csv.reader + csv.writer(lineterminator='\n'), salida UTF-8 sin BOM` |
| `datos/patologico_bom_csv-to.json` | 174 | `92f70fbbb23f8281…` | `python -c "csv.reader sobre utf-8-sig; json.dump(ensure_ascii=False)"` |
| `datos/tipico_json-to.csv` | 14 | `c2167db376424bd5…` | `json.load + csv.writer sobre items[]` |
| `imagen/16bit_tif-to-d16.png` | 61849791 | `c376b971bc9ed714…` | — |
| `imagen/16bit_tif-to-d8.png` | 18943503 | `30535107fa4f2119…` | `magick -limit thread 4 patologico_16bit.tif -depth 8 16bit_tif-to-d8.png` |
| `imagen/16bit_tif-to-default.png` | 61849791 | `232d78e04e15135d…` | `magick -limit thread 4 patologico_16bit.tif 16bit_tif-to-default.png` |
| `imagen/16bit_tif-to.jpg` | 1571956 | `0b1196c9326cc16e…` | — |
| `imagen/16bit_tif-to.webp` | 647580 | `dc117310b229bc4c…` | — |
| `imagen/alpha_png-to-flat.jpg` | 4389 | `31873cfcf4a8391a…` | `magick -limit thread 4 alpha.png -background white -alpha remove -alpha off -quality 85 alpha_png-to-flat.jpg` |
| `imagen/alpha_png-to.avif` | 1670 | `d4f22409580573a2…` | `magick -limit thread 4 alpha.png -quality 50 alpha_png-to.avif` |
| `imagen/alpha_png-to.jpg` | 4643 | `87ff6e3b3287c579…` | `magick -limit thread 4 alpha.png -quality 85 alpha_png-to.jpg` |
| `imagen/alpha_png-to.png8.png` | 2780 | `130973e73fe6d66e…` | — |
| `imagen/alpha_png-to.webp` | 2496 | `e6678b82dd9cf405…` | `magick -limit thread 4 alpha.png -quality 80 alpha_png-to.webp` |
| `imagen/tipico_jpg-to.png` | 32622 | `9de22a8b38c55c7f…` | — |
| `imagen/tipico_png-to.avif` | 1595 | `04eb85707ee966c6…` | `magick -limit thread 4 tipico.png -quality 50 tipico_png-to.avif` |
| `imagen/tipico_png-to.jpg` | 40963 | `ca6b1787a029338d…` | `magick -limit thread 4 tipico.png -quality 85 tipico_png-to.jpg` |
| `imagen/tipico_png-to.webp` | 13516 | `fc2234fdc39cb987…` | `magick -limit thread 4 tipico.png -quality 80 tipico_png-to.webp` |
| `imagen/tipico_webp-to.jpg` | 42748 | `1cae02e76a3924a9…` | — |
| `imagen/tipico_webp-to.png` | 64232 | `f5333823dfcee3cf…` | — |
| `imagen/trivial_png-to-lossless.webp` | 42 | `b36f1c8f1f13a093…` | `magick -limit thread 4 trivial.png -define webp:lossless=true trivial_png-to-lossless.webp` |
| `imagen/trivial_png-to.jpg` | 312 | `97dc772e4447f326…` | — |
| `imagen/trivial_png-to.webp` | 94 | `c7f5def4b9ff7e5a…` | `magick -limit thread 4 trivial.png -quality 80 trivial_png-to.webp` |
| `pdf/alpha_png-to.pdf` | 6111 | `49bf643acb0180af…` | — |
| `pdf/patologico_escaneado_pdf-to-p1.png` | 1908177 | `0d87f526c39ea246…` | — |
| `pdf/tipico_jpg-to.pdf` | 89885 | `746ec4cd6080828b…` | — |
| `pdf/tipico_png-to-150dpi.pdf` | 17187 | `bfb16262adc54606…` | `magick -limit thread 4 tipico.png -density 150 -units PixelsPerInch tipico_png-to-150dpi.pdf` |
| `pdf/tipico_png-to.pdf` | 17153 | `f97ebf482eadbea5…` | `magick -limit thread 4 tipico.png tipico_png-to.pdf` |
| `pdf/tipico_texto_pdf-to-gs.pdf` | 3291 | `cc1acd3d28a60202…` | `gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite -sOutputFile=out.pdf tipico_texto.pdf` |
| `pdf/tipico_texto_pdf-to-p1.jpg` | 71269 | `24720561a8e104bb…` | `gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=jpeg -dJPEGQ=85 -r150 -sOutputFile=%d.jpg tipico_texto.pdf` |
| `pdf/tipico_texto_pdf-to-p1.png` | 15804 | `cfb4324c638d6130…` | `gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=png16m -r150 -dNumRenderingThreads=4 -sOutputFile=%d.png tipico_texto.pdf` |
| `pdf/tipico_texto_pdf-to.tif` | 6533038 | `da93463e7029a1da…` | `gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=tiff24nc -r150 -sOutputFile=out.tif tipico_texto.pdf` |
| `pdf/tipico_texto_rasterizado.pdf` | 8689 | `4b8464c1f6fc81c4…` | `magick -limit thread 4 tipico_texto_pdf-to-p1.png tipico_texto_rasterizado.pdf` |
| `pdf/trivial_pdf-to-p1.png` | 4359 | `04e914f763f43612…` | — |
| `video/2pistas_mkv-to-COPY.mp4` | 4085275 | `126b8cfa3342d98b…` | `ffmpeg -threads 4 -i patologico_2pistas.mkv -map 0 -c copy out.mp4` |
| `video/2pistas_mkv-to-DEFAULT.mp4` | 3859442 | `d3b8772a56895210…` | `ffmpeg -threads 4 -i patologico_2pistas.mkv -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k out.mp4` |
| `video/2pistas_mkv-to-MAP0.mp4` | 3966842 | `7105da74af1d5d4a…` | `ffmpeg -threads 4 -i patologico_2pistas.mkv -map 0 -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k out.mp4` |
| `video/tipico_mp4-to.mkv` | 16235751 | `f4952a22a72894a6…` | `ffmpeg -threads 4 -i tipico.mp4 -map 0 -c copy out.mkv` |
| `video/tipico_mp4-to.webm` | 17014670 | `53bf36f083609323…` | `ffmpeg -threads 4 -i tipico.mp4 -c:v libvpx-vp9 -crf 33 -b:v 0 -row-mt 1 -deadline good -cpu-used 4 -c:a libopus -b:a 96k out.webm` |
| `video/trivial_mp4-to-naive.gif` | 394712 | `42b2453556472ba5…` | `ffmpeg -threads 4 -i trivial.mp4 -vf "fps=12,scale=320:-1" -loop 0 out.gif` |
| `video/trivial_mp4-to-palette.gif` | 609893 | `5d02db023b9ae041…` | `ffmpeg -threads 4 -i trivial.mp4 -vf "fps=12,scale=320:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=256[p];[b][p]paletteuse=dither=bayer" -loop 0 out.gif` |
| `video/trivial_mp4-to.webm` | 635908 | `0ffb18dc38f1c854…` | — |
