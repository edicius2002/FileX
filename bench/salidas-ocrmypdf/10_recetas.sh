#!/usr/bin/env bash
# FASE 2 + FASE 3 (produccion): ejecuta OCRmyPDF con distintas recetas sobre las
# 4 variantes escaneadas del corpus y deja:
#   - out/<receta>__<doc>.txt  : sidecar de Tesseract (= OCRmyPDF como MOTOR, fase 2)
#   - out/<receta>__<doc>.pdf  : PDF preprocesado    (= OCRmyPDF como PREPROCESADOR, fase 3)
#   - logs/<receta>__<doc>.log : stderr completo
# Se ejecuta ENTERO en el FS nativo de WSL (~/ocrx), nunca en /mnt/d.
set -u
BASE="$HOME/ocrx"
IN="$BASE/corpus"; OUT="$BASE/out"; LOG="$BASE/logs"
mkdir -p "$OUT" "$LOG"

DOCS="patologico_escaneado escaneado_d1 escaneado_d2 escaneado_d3"

# receta -> banderas. --force-ocr en todas para rasterizar siempre igual y que la
# unica variable sea el preprocesado. --clean-final (no --clean) porque --clean solo
# limpia la copia que ve Tesseract; --clean-final es la que escribe la imagen
# limpia en el PDF de salida, que es lo que necesita la fase 3.
declare -A REC=(
  [base]="--force-ocr"
  [deskew]="--force-ocr --deskew"
  [clean]="--force-ocr --clean-final"
  [rmbg]="--force-ocr --remove-background"
  [rotate]="--force-ocr --rotate-pages"
  [todo]="--force-ocr --deskew --clean-final --rotate-pages"
  [todo_rmbg]="--force-ocr --deskew --clean-final --remove-background --rotate-pages"
  [os300]="--force-ocr --oversample 300"
  [os400]="--force-ocr --oversample 400"
  [deskew_os300]="--force-ocr --deskew --oversample 300"
  [clean_os300]="--force-ocr --clean-final --oversample 300"
)

ORDEN="base deskew clean rmbg rotate todo todo_rmbg os300 os400 deskew_os300 clean_os300"

printf '%-16s %-24s %-6s %8s %10s\n' receta documento estado ms chars
for r in $ORDEN; do
  flags="${REC[$r]}"
  for d in $DOCS; do
    txt="$OUT/${r}__${d}.txt"; pdf="$OUT/${r}__${d}.pdf"; lg="$LOG/${r}__${d}.log"
    s=$(date +%s%N)
    ocrmypdf -l spa $flags --sidecar "$txt" "$IN/$d.pdf" "$pdf" >"$lg" 2>&1
    rc=$?
    e=$(date +%s%N); ms=$(( (e-s)/1000000 ))
    if [ $rc -ne 0 ]; then
      printf '%-16s %-24s %-6s %8s %10s  %s\n' "$r" "$d" "ERR$rc" "$ms" "-" \
        "$(grep -iE 'error|exception|not compatible|deprecated' "$lg" | head -1 | cut -c1-110)"
      : > "$txt"
    else
      n=$(tr -d '[:space:]' < "$txt" 2>/dev/null | wc -c)
      printf '%-16s %-24s %-6s %8s %10s\n' "$r" "$d" ok "$ms" "$n"
    fi
  done
done
