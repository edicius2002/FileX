#!/usr/bin/env bash
# Conductor unico y desprendido: recorre las tres configuraciones GPU de B23
# EN SERIE, reiniciando el proceso Python entre cada una (el asignador de VRAM
# no devuelve memoria). Cada script toma y suelta filex.gpu.Lock por su cuenta.
set -u
D="/mnt/d/Work/research/FileX/.ccb/workspaces/worker1"
PYAI="/mnt/d/Work/research/FileX/.venv-ai/Scripts/python.exe"
PYPD="/mnt/d/Work/research/FileX/.venv-paddle/Scripts/python.exe"
LOG="$D/bench/salidas-k-oem-acantilados/logs/conductor_b23.progreso.log"
: > "$LOG"
echo "INICIO $(date)" >> "$LOG"

echo "INICIO rapidocr-r6 $(date)" >> "$LOG"
WSLENV= PYTHONUTF8=1 PYTHONIOENCODING=utf-8 "$PYAI" \
  "$D/bench/salidas-k-oem-acantilados/b23_k_d5.py" rapidocr-r6 --reps 3 \
  > "$D/bench/salidas-k-oem-acantilados/logs/b23_rapidocr-r6.jsonl" \
  2> "$D/bench/salidas-k-oem-acantilados/logs/b23_rapidocr-r6.err.log"
echo "FIN rapidocr-r6 rc=$? $(date)" >> "$LOG"

echo "INICIO paddleocr $(date)" >> "$LOG"
WSLENV= PYTHONUTF8=1 PYTHONIOENCODING=utf-8 "$PYPD" \
  "$D/bench/salidas-k-oem-acantilados/b23_k_d5.py" paddleocr --reps 3 \
  > "$D/bench/salidas-k-oem-acantilados/logs/b23_paddleocr.jsonl" \
  2> "$D/bench/salidas-k-oem-acantilados/logs/b23_paddleocr.err.log"
echo "FIN paddleocr rc=$? $(date)" >> "$LOG"

echo "INICIO easyocr $(date)" >> "$LOG"
WSLENV= PYTHONUTF8=1 PYTHONIOENCODING=utf-8 "$PYAI" \
  "$D/bench/salidas-k-oem-acantilados/b23_k_d5.py" easyocr --reps 3 \
  > "$D/bench/salidas-k-oem-acantilados/logs/b23_easyocr.jsonl" \
  2> "$D/bench/salidas-k-oem-acantilados/logs/b23_easyocr.err.log"
echo "FIN easyocr rc=$? $(date)" >> "$LOG"

echo "FIN CONDUCTOR $(date)" >> "$LOG"
