#!/usr/bin/env bash
# Coexistencia con INFERENCIA ACTIVA simultanea (no solo modelos cargados).
cd /d/Work/research/FileX
PY="D:/Work/research/FileX/.venv-ai/Scripts/python.exe"
mem(){ nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | tr -d ' '; }
base=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits|tr -d ' ')
echo "linea_base_MiB=$base"
$PY bench/scripts/ia_whisper.py large-v3 todo   > bench/logs/act_whisper.log 2>&1 &
$PY bench/scripts/ia_docling.py cuda            > bench/logs/act_docling.log 2>&1 &
ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i corpus/video/fuente_4k.mp4 \
       -c:v h264_nvenc -preset p4 -b:v 20M -an bench/salidas-fase1/video/act_nvenc.mp4 > /dev/null 2>&1 &
pico=0; picou=0
while jobs -r | grep -q .; do
  s=$(mem); m=${s%%,*}; u=${s##*,}
  [ "${m:-0}" -gt "$pico" ] && pico=$m
  [ "${u:-0}" -gt "$picou" ] && picou=$u
  sleep 0.3
done
wait
echo "pico_MiB=$pico delta=$((pico-base)) pico_util=$picou libre_restante_MiB=$((12288-pico))"
grep -h '"evento": "transcripcion"' bench/logs/act_whisper.log | head -2
grep -h '"evento": "convert"' bench/logs/act_docling.log | head -3
echo "=== FIN ACTIVA ==="
