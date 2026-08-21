#!/usr/bin/env bash
# Rasteriza a 200 ppp / escala de grises todos los PDF de salidas-ocrmypdf/pdf
# (y los controles de ppp de la fase 4) usando el mismo ImageMagick que genero el corpus.
# OJO: magick.exe es un binario de Windows -> hay que pasarle rutas D:/..., no /d/...
set -u
MAGICK="/c/Program Files/ImageMagick-7.1.2-Q16-HDRI/magick"
WU="/d/Work/research/FileX/bench/salidas-ocrmypdf"   # para bash
WW="D:/Work/research/FileX/bench/salidas-ocrmypdf"   # para magick.exe
mkdir -p "$WU/img"

ras(){ # $1=pdf(W) $2=ppp $3=destino(W)
  "$MAGICK" -density "$2" "$1[0]" -colorspace Gray -alpha remove -background white -flatten "$3" 2>&1 | head -3
}
dim(){ "$MAGICK" identify -format '%wx%h' "$1" 2>/dev/null; }

for p in "$WU"/pdf/*.pdf; do
  b=$(basename "$p" .pdf)
  ras "$WW/pdf/$b.pdf" 200 "$WW/img/$b.png"
  printf '%-42s %s\n' "$b" "$(dim "$WW/img/$b.png")"
done

# --- controles fase 4: PDF ORIGINAL a varios ppp (aisla la re-rasterizacion) ---
for d in patologico_escaneado escaneado_d1 escaneado_d2 escaneado_d3; do
  for ppp in 100 150 200 300 400 600; do
    ras "$WW/pdf/ctrl/orig__$d.pdf" "$ppp" "$WW/img/ctrlppp${ppp}__$d.png"
    printf '%-42s %s\n' "ctrlppp${ppp}__$d" "$(dim "$WW/img/ctrlppp${ppp}__$d.png")"
  done
done

# --- control extra: deskew "barato" solo con ImageMagick, sin OCRmyPDF, a 200 ppp ---
for d in patologico_escaneado escaneado_d1 escaneado_d2 escaneado_d3; do
  "$MAGICK" -density 200 "$WW/pdf/ctrl/orig__$d.pdf[0]" -colorspace Gray -alpha remove \
     -background white -flatten -deskew 40% +repage "$WW/img/ctrlmagickdeskew__$d.png" 2>&1 | head -3
  printf '%-42s %s\n' "ctrlmagickdeskew__$d" "$(dim "$WW/img/ctrlmagickdeskew__$d.png")"
done
echo "total imagenes: $(ls -1 "$WU"/img/*.png 2>/dev/null | wc -l)"
