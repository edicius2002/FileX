#!/usr/bin/env bash
# FASE 2: ¿cabe el OCR en GPU encima del perfil de fase 1?
# whisper large-v3 residente + docling con OCR en CUDA + NVENC 1080p, a la vez.
set -u
cd /d/Work/research/FileX
source bench/lib/harness.sh
trap - EXIT INT TERM
PY=".venv-ai/Scripts/python.exe"
FF="/d/utils/ffmpeg/bin/ffmpeg"
LOG="bench/logs/fase2_coexistencia.log"
: > "$LOG"

vram(){ nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' '; }

echo "0 · linea base: $(vram) MiB" | tee -a "$LOG"

# muestreador de fondo
( while :; do vram; sleep 0.25; done ) > /tmp/_coex2.txt &
SAMP=$!

RESIDENTE_SEG=150 $PY bench/scripts/ia_whisper.py large-v3 residente > /tmp/_whis2.txt 2>&1 &
WPID=$!
for _ in $(seq 120); do grep -q RESIDENTE_LISTO /tmp/_whis2.txt 2>/dev/null && break; sleep 1; done
echo "1 · + whisper large-v3 residente: $(vram) MiB" | tee -a "$LOG"

SONDA_ORT=1 FORZAR_ORT_CUDA=1 REPS=3 $PY bench/scripts/ocr_docling.py cuda rapidocr onnxruntime coex_ocrgpu \
  > /tmp/_doc2.txt 2>&1 &
DPID=$!
sleep 12
echo "2 · + docling OCR-GPU en marcha: $(vram) MiB" | tee -a "$LOG"

$FF -v error -y -i corpus/video/tipico.mp4 -c:v h264_nvenc -preset p7 -b:v 5M -c:a copy \
   bench/salidas-fase2/coex_nvenc.mp4 >/dev/null 2>&1
echo "3 · + NVENC 1080p terminado (rc=$?): $(vram) MiB" | tee -a "$LOG"

wait $DPID; DRC=$?
kill $SAMP 2>/dev/null; wait $SAMP 2>/dev/null
PICO=$(sort -n /tmp/_coex2.txt | tail -1)
echo "PICO TOTAL: $PICO MiB   (libre restante: $((12288-PICO)) MiB)  docling_rc=$DRC" | tee -a "$LOG"
grep -E "sesion_ort|convert" /tmp/_doc2.txt | tr -d '\0' | tee -a "$LOG"
wait $WPID 2>/dev/null
rm -f /tmp/_coex2.txt
echo "4 · tras liberar todo: $(vram) MiB" | tee -a "$LOG"
