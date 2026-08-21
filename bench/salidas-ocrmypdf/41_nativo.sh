#!/usr/bin/env bash
# Suelo de referencia: la imagen incrustada en el PDF, extraida SIN re-rasterizar.
set -u
O=/mnt/d/Work/research/FileX/bench/salidas-ocrmypdf/img2
for d in escaneado_d1 escaneado_d2 escaneado_d3 patologico_escaneado; do
  pdfimages -png -f 1 -l 1 "$HOME/ocrx/corpus/$d.pdf" "$O/nat__$d"
done
# pdfimages numera con sufijo -000; renombrar a nombre limpio
for f in "$O"/nat__*-000.png; do mv "$f" "${f%-000.png}.png"; done
ls -l "$O" | grep nat__
