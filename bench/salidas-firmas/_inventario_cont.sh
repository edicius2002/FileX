#!/bin/sh
for t in magick convert gm ffmpeg gs vips pandoc soffice ebook-convert inkscape resvg cjxl djxl heif-enc potrace vtracer dasel assimp dvisvgm xelatex msgconvert python3 qpdf tesseract; do
  p=$(command -v "$t" 2>/dev/null)
  if [ -n "$p" ]; then echo "$t OK $p"; else echo "$t - -"; fi
done
