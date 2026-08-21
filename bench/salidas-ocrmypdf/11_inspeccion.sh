#!/usr/bin/env bash
set -u
echo "=== ERROR EXACTO DE --remove-background (d3) ==="
tail -30 "$HOME/ocrx/logs/rmbg__escaneado_d3.log"
echo
echo "=== SIDECARS DE d3 (OCRmyPDF como motor) ==="
for f in "$HOME"/ocrx/out/*__escaneado_d3.txt; do
  echo "--- $(basename "$f")"; sed -e 's/^/    /' "$f"
done
echo
echo "=== SIDECAR base de cada documento ==="
for d in patologico_escaneado escaneado_d1 escaneado_d2; do
  echo "--- base__$d"; sed -e 's/^/    /' "$HOME/ocrx/out/base__$d.txt"
done
