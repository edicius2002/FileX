#!/usr/bin/env bash
# FASE 1-B, pregunta central: cuantos motores caben a la vez en la VRAM libre.
# surya queda fuera (su ruta GPU exige un servidor vLLM en Docker, ver informe),
# asi que se mide whisper + docling + una transcodificacion NVENC simultanea,
# que es el escenario real del sidecar de FileX.
cd /d/Work/research/FileX
PY="D:/Work/research/FileX/.venv-ai/Scripts/python.exe"
export RESIDENTE_SEG=110
mem(){ nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' '; }
esperar(){ for i in $(seq 1 150); do grep -q RESIDENTE_LISTO "$1" 2>/dev/null && return 0; sleep 2; done; return 1; }

base=$(mem); echo "0_linea_base_MiB=$base"

$PY bench/scripts/ia_whisper.py large-v3 residente > bench/logs/coex_whisper.log 2>&1 &
esperar bench/logs/coex_whisper.log || echo "AVISO: whisper no anuncio RESIDENTE_LISTO"
w=$(mem); echo "1_whisper_large-v3_MiB=$w delta=$((w-base))"

$PY bench/scripts/ia_docling.py cuda residente > bench/logs/coex_docling.log 2>&1 &
esperar bench/logs/coex_docling.log || echo "AVISO: docling no anuncio RESIDENTE_LISTO"
d=$(mem); echo "2_whisper+docling_MiB=$d delta_docling=$((d-w)) delta_total=$((d-base))"

$PY bench/scripts/ia_whisper.py distil-large-v3 residente > bench/logs/coex_distil.log 2>&1 &
esperar bench/logs/coex_distil.log || echo "AVISO: distil no anuncio RESIDENTE_LISTO"
t=$(mem); echo "3_whisper+docling+distil_MiB=$t delta_distil=$((t-d)) delta_total=$((t-base))"

# ahora, con los tres modelos residentes, una transcodificacion NVENC 4K encima
echo "4_lanzando NVENC 4K con los tres modelos residentes"
ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i corpus/video/fuente_4k.mp4 \
       -c:v h264_nvenc -preset p4 -b:v 20M -an bench/salidas-fase1/video/coex_nvenc.mp4 &
FF=$!
pico=0
for i in $(seq 1 80); do m=$(mem); [ "${m:-0}" -gt "$pico" ] && pico=$m; sleep 0.5; done
wait $FF; rcff=$?
echo "5_pico_con_todo_MiB=$pico delta_sobre_base=$((pico-base)) libre_restante_MiB=$((12288-pico)) nvenc_rc=$rcff"
wait
echo "6_estado_final_MiB=$(mem)"
echo "=== FIN COEXISTENCIA ==="
