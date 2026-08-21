#!/usr/bin/env bash
# FASE 3 (preparacion): saca los PDF preprocesados de WSL y los rasteriza a 200 ppp
# en escala de grises, EXACTAMENTE como se hizo con las imagenes de la fase 2
# (bench/salidas-fase2/img/*.png = PDF original renderizado a 200 ppp, 1294 px de ancho).
# Asi la unica variable frente a la marca a batir es el preprocesado de OCRmyPDF.
set -u
W="/mnt/d/Work/research/FileX/bench/salidas-ocrmypdf"
mkdir -p "$W/pdf" "$W/img"
cp "$HOME"/ocrx/out/*.pdf "$W/pdf/" 2>/dev/null

# controles de la fase 4: el PDF ORIGINAL, sin tocar, a distintos ppp
mkdir -p "$W/pdf/ctrl"
for d in patologico_escaneado escaneado_d1 escaneado_d2 escaneado_d3; do
  cp "$HOME/ocrx/corpus/$d.pdf" "$W/pdf/ctrl/orig__$d.pdf"
done
ls -1 "$W/pdf" | wc -l
echo "PDFs copiados a $W/pdf"
