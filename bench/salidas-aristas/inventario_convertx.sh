#!/bin/sh
for b in soffice libreoffice pandoc ebook-convert vips vipsheader qpdf inkscape resvg magick convert ffmpeg gs assimp dasel potrace vtracer dvisvgm xelatex msgconvert cjxl djxl heif-enc python3 tesseract; do
  p=$(command -v "$b" 2>/dev/null)
  if [ -n "$p" ]; then echo "$b -> $p"; else echo "$b -> NO"; fi
done
echo "--- version ---"
cat /etc/os-release 2>/dev/null | head -2
