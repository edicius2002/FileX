#!/usr/bin/env bash
# Velocidad de OCRmyPDF dentro de WSL, sobre el FS NATIVO (~/ocrx), n=9, mediana.
# Tambien mide el mismo trabajo sobre /mnt/d para cuantificar la trampa conocida.
set -u
B="$HOME/ocrx"; T="$B/vel"; mkdir -p "$T"
N=${N:-9}

med(){ printf '%s\n' "$@" | sort -n | awk '{a[NR]=$1} END{print (NR%2)?a[(NR+1)/2]:int((a[NR/2]+a[NR/2+1])/2)}'; }

corre(){ # $1=etiqueta $2=entrada $3...=banderas
  local et="$1" in="$2"; shift 2
  local ts=() i s e
  for i in $(seq "$N"); do
    s=$(date +%s%N)
    ocrmypdf -l spa "$@" "$in" "$T/o.pdf" >/dev/null 2>&1
    e=$(date +%s%N); ts+=( $(( (e-s)/1000000 )) )
    rm -f "$T/o.pdf"
  done
  local sorted; sorted=$(printf '%s\n' "${ts[@]}" | sort -n)
  printf '%-42s mediana:%7s ms  n=%s  rango:%s-%s\n' "$et" "$(med "${ts[@]}")" "$N" \
     "$(echo "$sorted"|head -1)" "$(echo "$sorted"|tail -1)"
}

echo "=== FRIO vs CALIENTE (primera invocacion tras purgar cache de pagina) ==="
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || echo "(sin sudo: no se pudo purgar cache; el 'frio' sera aproximado)"
s=$(date +%s%N); ocrmypdf -l spa --force-ocr "$B/corpus/escaneado_d3.pdf" "$T/f.pdf" >/dev/null 2>&1; e=$(date +%s%N)
echo "frio    (d3, --force-ocr): $(( (e-s)/1000000 )) ms"
s=$(date +%s%N); ocrmypdf -l spa --force-ocr "$B/corpus/escaneado_d3.pdf" "$T/f.pdf" >/dev/null 2>&1; e=$(date +%s%N)
echo "caliente(d3, --force-ocr): $(( (e-s)/1000000 )) ms"
echo "coste fijo del arranque (--version, sin trabajo):"
s=$(date +%s%N); ocrmypdf --version >/dev/null 2>&1; e=$(date +%s%N)
echo "  ocrmypdf --version: $(( (e-s)/1000000 )) ms"
echo

echo "=== FS NATIVO DE WSL (~/ocrx) ==="
corre "d3 base (--force-ocr)"        "$B/corpus/escaneado_d3.pdf" --force-ocr
corre "d3 --deskew"                  "$B/corpus/escaneado_d3.pdf" --force-ocr --deskew
corre "d3 --clean-final"             "$B/corpus/escaneado_d3.pdf" --force-ocr --clean-final
corre "d3 --rotate-pages"            "$B/corpus/escaneado_d3.pdf" --force-ocr --rotate-pages
corre "d3 --oversample 300"          "$B/corpus/escaneado_d3.pdf" --force-ocr --oversample 300
corre "d3 todo (deskew+clean+rotate)" "$B/corpus/escaneado_d3.pdf" --force-ocr --deskew --clean-final --rotate-pages
corre "patologico base"              "$B/corpus/patologico_escaneado.pdf" --force-ocr
corre "tipico_texto --skip-text"     "$B/corpus/tipico_texto.pdf" --skip-text
echo

echo "=== MISMO TRABAJO SOBRE /mnt/d (la trampa conocida) ==="
corre "d3 base sobre /mnt/d" "/mnt/d/Work/research/FileX/corpus/pdf/escaneado_d3.pdf" --force-ocr
corre "patologico sobre /mnt/d" "/mnt/d/Work/research/FileX/corpus/pdf/patologico_escaneado.pdf" --force-ocr
