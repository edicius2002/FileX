#!/usr/bin/env bash
# Diagnostico: por que --deskew / --clean-final / --rotate-pages no alteran la
# imagen de salida en d1..d3. Se re-ejecuta con -v 1 y se guarda la traza.
set -u
B="$HOME/ocrx"; D="$B/diag"; mkdir -p "$D"
for r in deskew clean rotate; do
  case $r in
    deskew) F="--deskew";;
    clean)  F="--clean-final";;
    rotate) F="--rotate-pages";;
  esac
  for d in escaneado_d3 patologico_escaneado; do
    echo "############ $r / $d ############"
    ocrmypdf -l spa --force-ocr $F -v 1 "$B/corpus/$d.pdf" "$D/${r}_${d}.pdf" 2>&1 \
      | egrep -i 'deskew|unpaper|clean|rotat|orientation|skew|confidence|angle|warn|Not eligible|image|dpi' \
      | head -25
    echo
  done
done
echo "===== unpaper directo, para ver si el binario funciona ====="
unpaper --version
echo "===== ocrmypdf --help: banderas de preprocesado disponibles ====="
ocrmypdf --help 2>&1 | egrep -A2 '\-\-rotate-pages|\-\-deskew|\-\-clean|\-\-remove-background|\-\-oversample|\-\-threshold|\-\-unpaper-args'
