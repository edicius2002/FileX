#!/usr/bin/env bash
# H2 — sonda de NVENC EN EJECUCIÓN. No deduce nada del listado de `ffmpeg -encoders`.
# Toma el lock de GPU del arnés compartido y lo suelta al salir.
set -u
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$AQUI/../lib/harness.sh"

DES="$AQUI/desechable"
mkdir -p "$DES"
cd "$DES" || exit 1

echo "=== R21: censo ANTES ==="
ls -A | sed 's/^/  /' ; echo "  (total $(ls -A | wc -l))"

gpu_acquire "H2-sonda-nvenc" || { echo "[H2] no pude tomar el lock"; exit 1; }
echo "[H2] lock tomado. VRAM libre: $(gpu_libre_mib) MiB"

probar(){
  local etiqueta="$1"; shift
  echo "--- $etiqueta ---"
  timeout 90 "$@" > "salida_$etiqueta.log" 2>&1
  local rc=$?
  echo "rc=$rc"
  tail -6 "salida_$etiqueta.log" | sed 's/^/    /'
}

echo
echo "=== A. ¿ffmpeg acepta el argv? (-h encoder=) ==="
ffmpeg -hide_banner -h encoder=av1_nvenc 2>&1 | head -6 | sed 's/^/  /'

echo
echo "=== B. Codificar de verdad ==="
probar av1_nvenc  ffmpeg -hide_banner -nostdin -y -f lavfi -i testsrc=size=320x240:rate=25 -frames:v 25 -c:v av1_nvenc  -f matroska sal_av1_nvenc.mkv
ls -l sal_av1_nvenc.mkv 2>&1 | sed 's/^/    /'
probar hevc_nvenc ffmpeg -hide_banner -nostdin -y -f lavfi -i testsrc=size=320x240:rate=25 -frames:v 25 -c:v hevc_nvenc -f matroska sal_hevc_nvenc.mkv
ls -l sal_hevc_nvenc.mkv 2>&1 | sed 's/^/    /'
probar h264_nvenc ffmpeg -hide_banner -nostdin -y -f lavfi -i testsrc=size=320x240:rate=25 -frames:v 25 -c:v h264_nvenc -f matroska sal_h264_nvenc.mkv
ls -l sal_h264_nvenc.mkv 2>&1 | sed 's/^/    /'
probar libsvtav1  ffmpeg -hide_banner -nostdin -y -f lavfi -i testsrc=size=320x240:rate=25 -frames:v 25 -c:v libsvtav1  -f matroska sal_libsvtav1.mkv
ls -l sal_libsvtav1.mkv 2>&1 | sed 's/^/    /'

echo
echo "=== C. ¿En qué MOMENTO falla av1_nvenc? — traza completa ==="
sed -n '1,80p' salida_av1_nvenc.log | sed 's/^/  /'

gpu_release
echo
echo "=== R21: censo DESPUES ==="
ls -A | sed 's/^/  /' ; echo "  (total $(ls -A | wc -l))"
