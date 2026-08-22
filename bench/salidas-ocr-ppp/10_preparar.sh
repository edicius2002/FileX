#!/usr/bin/env bash
# G1 / paso 1 — genera las entradas de las tres vias.
#
#  via A "ppp nativos"  -> raster a los ppp que la imagen incrustada ya tiene
#  via B "extraida"     -> la imagen incrustada tal cual, sin rasterizar (pypdfium2)
#  via C "200 ppp"      -> control que debe reproducir las cifras de gpu-fase2.md
#
# La rasterizacion usa EXACTAMENTE la misma orden de ImageMagick que el arnes de
# la fase 2 (`21_rasterizar_win.sh`), para que la via C sea un control fiel y no
# una reimplementacion parecida. Lo unico que cambia entre vias es -density.
set -u
MAGICK="/c/Program Files/ImageMagick-7.1.2-Q16-HDRI/magick"
RU="/d/Work/research/FileX"
RW="D:/Work/research/FileX"
IMG_U="$RU/bench/salidas-ocr-ppp/img"
IMG_W="$RW/bench/salidas-ocr-ppp/img"
mkdir -p "$IMG_U"

dim(){ "$MAGICK" identify -format '%wx%h %[colorspace]' "$1" 2>/dev/null; }

# --- barrido de ppp sobre los 4 documentos (contiene la via A y la via C) ---
echo "=== raster: barrido de ppp (misma orden magick que el arnes de fase 2) ==="
for d in patologico_escaneado escaneado_d1 escaneado_d2 escaneado_d3; do
  for ppp in 75 100 125 150 175 200 250 300; do
    o="$IMG_W/ppp${ppp}__$d.png"
    "$MAGICK" -density "$ppp" "$RW/corpus/pdf/$d.pdf[0]" -colorspace Gray \
              -alpha remove -background white -flatten "$o" 2>/dev/null
    printf '  %-38s %s\n' "ppp${ppp}__$d" "$(dim "$o")"
  done
done

# --- via B: imagen incrustada extraida sin rasterizar ---
echo
echo "=== extraccion sin rasterizar (pypdfium2; no hay pdfimages en Windows) ==="
"$RU/.venv-ai/Scripts/python.exe" "$RW/bench/salidas-ocr-ppp/11_extraer.py"

echo
echo "total imagenes: $(ls -1 "$IMG_U"/*.png 2>/dev/null | wc -l)"
du -sh "$IMG_U"
