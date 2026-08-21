#!/usr/bin/env bash
# Inventario del entorno WSL para la prueba de OCRmyPDF.
set -u
echo "=== VERSIONES ==="
lsb_release -ds
echo "ocrmypdf   $(ocrmypdf --version)"
tesseract --version 2>&1 | head -2
echo "unpaper    $(unpaper --version 2>&1 | head -1)"
echo "ghostscript $(gs --version)"
echo "pngquant   $(pngquant --version 2>&1 | head -1)"
echo "nproc=$(nproc)"
free -m | head -2
echo
echo "=== IDIOMAS TESSERACT ==="
tesseract --list-langs 2>&1
echo
echo "=== TAMANO INSTALADO (dpkg, KB) ==="
dpkg-query -W -f='${Installed-Size} ${Package}\n' \
  ocrmypdf tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa tesseract-ocr-osd \
  unpaper pngquant ghostscript libtesseract5 python3-pikepdf python3-img2pdf 2>/dev/null \
  | sort -rn | awk '{s+=$1; printf "%8d KB  %s\n",$1,$2} END{printf "TOTAL %d KB = %.1f MB\n", s, s/1024}'
echo
echo "=== CORPUS EN FS NATIVO DE WSL ==="
for f in "$HOME"/ocrx/corpus/*.pdf; do
  printf '%-28s %8s B  ' "$(basename "$f")" "$(stat -c%s "$f")"
  pdfinfo "$f" 2>/dev/null | awk -F: '/^Pages|^Page size/{gsub(/^ +/,"",$2); printf "%s=%s ", $1, $2}'
  echo
done
