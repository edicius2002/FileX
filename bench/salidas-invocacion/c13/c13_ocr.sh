#!/bin/sh
# P2 / C13 - OCR con tesseract a ppp NATIVOS (regla R1 de CLAUDE.md sec.4 trampa 6).
# La primera pasada rasterizo todo a 150 ppp, que sobremuestrea d2 y d3 (100 nativos)
# y submuestrea patologico y d4 (200). Aqui cada documento va a los suyos.
set -u
cd /w || exit 1
R=/w/out2
mkdir -p "$R"
T=/w/res_ocr.tsv
: > "$T"
for par in "patologico_escaneado 200" "escaneado_d1 150" "escaneado_d2 100" \
           "escaneado_d3 100" "escaneado_d4 200"; do
  d=$(echo "$par" | cut -d' ' -f1)
  p=$(echo "$par" | cut -d' ' -f2)
  [ -f "/w/in/$d.pdf" ] || continue
  gs -dNOPAUSE -dBATCH -dQUIET -sDEVICE=png16m -r"$p" -dFirstPage=1 -dLastPage=1 \
     -sOutputFile="$R/$d.png" "/w/in/$d.pdf" </dev/null >/dev/null 2>&1
  t0=$(date +%s%N)
  tesseract "$R/$d.png" "$R/$d" -l spa txt </dev/null >/dev/null 2>&1
  rc=$?
  t1=$(date +%s%N)
  by=-1; [ -f "$R/$d.txt" ] && by=$(stat -c %s "$R/$d.txt")
  printf '%s\t%s\t%s\t%s\t%s\n' "$d" "$p" "$rc" "$by" "$(( (t1-t0)/1000000 ))" >> "$T"
  echo "  $d ${p}ppp rc=$rc bytes=$by $(( (t1-t0)/1000000 ))ms"
done
