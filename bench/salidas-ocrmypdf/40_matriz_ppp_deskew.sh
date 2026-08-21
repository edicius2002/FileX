#!/usr/bin/env bash
# FASE 4: aislar la causa. La fase 3 sugiere que la ganancia en d3 NO viene del
# preprocesado de OCRmyPDF sino de (a) los ppp de rasterizacion y (b) un deskew
# de verdad. Aqui se cruzan las dos variables y se anade el JPEG incrustado
# original (sin re-rasterizar en absoluto) como suelo de referencia.
set -u
MAGICK="/c/Program Files/ImageMagick-7.1.2-Q16-HDRI/magick"
WU="/d/Work/research/FileX/bench/salidas-ocrmypdf"
WW="D:/Work/research/FileX/bench/salidas-ocrmypdf"
CU="/d/Work/research/FileX/corpus/pdf"
CW="D:/Work/research/FileX/corpus/pdf"
mkdir -p "$WU/img2"
dim(){ "$MAGICK" identify -format '%wx%h' "$1" 2>/dev/null; }

# --- matriz ppp x deskew sobre el PDF ORIGINAL ---
for d in escaneado_d1 escaneado_d2 escaneado_d3 patologico_escaneado; do
  for ppp in 75 100 125 150 175 200 250 300; do
    o="$WW/img2/m_ppp${ppp}__$d.png"
    "$MAGICK" -density "$ppp" "$CW/$d.pdf[0]" -colorspace Gray -alpha remove \
        -background white -flatten "$o" 2>/dev/null
    od="$WW/img2/m_ppp${ppp}_ds__$d.png"
    "$MAGICK" -density "$ppp" "$CW/$d.pdf[0]" -colorspace Gray -alpha remove \
        -background white -flatten -deskew 40% +repage "$od" 2>/dev/null
    printf '%-34s %-12s  +deskew %-12s\n' "ppp${ppp} $d" "$(dim "$o")" "$(dim "$od")"
  done
done

# --- suelo absoluto: el JPEG/PNG incrustado tal cual, SIN re-rasterizar ---
for d in escaneado_d1 escaneado_d2 escaneado_d3 patologico_escaneado; do
  "$MAGICK" "$CW/$d.pdf[0]" -define pdf:use-cropbox=true null: 2>/dev/null
  # extraccion real del stream de imagen con pdfimages (WSL)
  :
done
echo "--- extrayendo imagenes incrustadas con pdfimages (WSL) ---"
wsl.exe -- bash -c 'set -u; O=/mnt/d/Work/research/FileX/bench/salidas-ocrmypdf/img2; for d in escaneado_d1 escaneado_d2 escaneado_d3 patologico_escaneado; do pdfimages -png -f 1 -l 1 "$HOME/ocrx/corpus/$d.pdf" "$O/nat__$d" 2>/dev/null; done; ls -1 $O/nat__* 2>/dev/null'
for f in "$WU"/img2/nat__*; do printf '%-34s %s\n' "$(basename "$f")" "$(dim "$WW/img2/$(basename "$f")")"; done
echo "total img2: $(ls -1 "$WU"/img2/*.png 2>/dev/null | wc -l)"
