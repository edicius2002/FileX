#!/bin/sh
# P2 / C13 - qpdf y tesseract dentro de la imagen filex-c13. Se ejecuta ASI:
#   docker run --rm -v <SAL>/c13:/w filex-c13 sh /w/c13_dentro.sh
set -u
cd /w || exit 1
R=/w/out
mkdir -p "$R"
T=/w/res.tsv
: > "$T"

ver() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$T"; }

echo "== versiones =="
qpdf --version 2>&1 | head -1
tesseract --version 2>&1 | head -2
tesseract --list-langs 2>&1 | tr '\n' ' '
echo

t() {  # etiqueta, ficherosalida, orden...
  et="$1"; sal="$2"; shift 2
  t0=$(date +%s%N)
  "$@" </dev/null > "/w/out/$et.log" 2>&1
  rc=$?
  t1=$(date +%s%N)
  ms=$(( (t1 - t0) / 1000000 ))
  by=-1
  [ -f "$sal" ] && by=$(stat -c %s "$sal")
  ver "$et" "$rc" "$by" "$ms"
  echo "  $et rc=$rc bytes=$by ${ms}ms"
}

echo "== caso 6: qpdf =="
t qpdf_linearize   "$R/lin.pdf"  qpdf --linearize /w/in/tipico_texto.pdf "$R/lin.pdf"
t qpdf_encrypt     "$R/enc.pdf"  qpdf --encrypt "" ownerpw 256 -- /w/in/tipico_texto.pdf "$R/enc.pdf"
t qpdf_decrypt     "$R/dec.pdf"  qpdf --password=ownerpw --decrypt "$R/enc.pdf" "$R/dec.pdf"
t qpdf_check       "$R/chk.txt"  sh -c 'qpdf --check /w/in/tipico_texto.pdf > /w/out/chk.txt 2>&1'
t qpdf_json        "$R/j.json"   sh -c 'qpdf --json /w/in/tipico_texto.pdf > /w/out/j.json 2>&1'
t qpdf_split       "$R/sp-1.pdf" qpdf --split-pages /w/in/tipico_texto.pdf "$R/sp.pdf"
t qpdf_merge       "$R/mrg.pdf"  qpdf --empty --pages /w/in/tipico_texto.pdf /w/in/tipico_texto.pdf -- "$R/mrg.pdf"

echo "== caso 5: tesseract (OCR sobre PDF escaneado) =="
for d in patologico_escaneado escaneado_d1 escaneado_d2 escaneado_d3 escaneado_d4; do
  [ -f "/w/in/$d.pdf" ] || continue
  # rasterizar a ppp NATIVOS con gs (regla R1) y pasar tesseract
  t "gs_raster_$d" "$R/$d.png" gs -dNOPAUSE -dBATCH -dQUIET -sDEVICE=png16m -r150 \
      -dFirstPage=1 -dLastPage=1 -sOutputFile="$R/$d.png" "/w/in/$d.pdf"
  t "tess_txt_$d"  "$R/$d.txt"  sh -c "tesseract '$R/$d.png' '$R/$d' -l spa txt"
  t "tess_pdf_$d"  "$R/$d.pdf"  sh -c "tesseract '$R/$d.png' '$R/$d' -l spa pdf"
done
echo "== fin =="
