#!/usr/bin/env bash
# FASE 1-A.4: calidad CPU vs GPU a igual bitrate objetivo (VMAF + PSNR + SSIM).
cd /d/Work/research/FileX
source bench/lib/harness.sh
gpu_acquire "fase1-calidad" || exit 1

OUT=bench/salidas-fase1/video/calidad
mkdir -p "$OUT"
REF=corpus/video/tipico.mp4
REF4K=corpus/video/fuente_4k.mp4

metricas(){ # $1=distorsionado $2=referencia $3=etiqueta
  local d="$1" r="$2" lbl="$3"
  local br size vmaf psnr ssim
  size=$(stat -c %s "$d")
  br=$(ffprobe -v error -select_streams v:0 -show_entries format=bit_rate -of csv=p=0 "$d")
  ffmpeg -v error -i "$d" -i "$r" -lavfi "[0:v][1:v]libvmaf=n_threads=12:log_fmt=json:log_path=$OUT/_v.json" -f null - 2>/dev/null
  vmaf=$(python -c "import json;d=json.load(open(r'$OUT/_v.json'));print('%.2f'%d['pooled_metrics']['vmaf']['mean'])" 2>/dev/null)
  psnr=$(ffmpeg -v info -i "$d" -i "$r" -lavfi "[0:v][1:v]psnr" -f null - 2>&1 | grep -o 'average:[0-9.]*' | head -1 | cut -d: -f2)
  ssim=$(ffmpeg -v info -i "$d" -i "$r" -lavfi "[0:v][1:v]ssim" -f null - 2>&1 | grep -o 'All:[0-9.]*' | head -1 | cut -d: -f2)
  printf '%-34s bitrate_real:%9s bps  tam:%9s B  VMAF:%7s  PSNR:%7s dB  SSIM:%8s\n' "$lbl" "$br" "$size" "$vmaf" "$psnr" "$ssim"
}

echo "############ CALIDAD H.264 1080p, mismo bitrate objetivo ############"
for B in 2M 5M 10M; do
  ffmpeg -y -v error -i $REF -c:v libx264    -preset medium -b:v $B -an $OUT/x264_$B.mp4
  ffmpeg -y -v error -i $REF -c:v h264_nvenc -preset p4     -b:v $B -an $OUT/nvenc_$B.mp4
  ffmpeg -y -v error -i $REF -c:v h264_nvenc -preset p7     -b:v $B -an $OUT/nvencp7_$B.mp4
  metricas $OUT/x264_$B.mp4     $REF "H264 CPU  x264 medium  @$B"
  metricas $OUT/nvenc_$B.mp4    $REF "H264 GPU  nvenc p4     @$B"
  metricas $OUT/nvencp7_$B.mp4  $REF "H264 GPU  nvenc p7     @$B"
  echo
done

echo "############ CALIDAD HEVC 1080p ############"
for B in 3M 6M; do
  ffmpeg -y -v error -i $REF -c:v libx265    -preset medium -b:v $B -an $OUT/x265_$B.mp4
  ffmpeg -y -v error -i $REF -c:v hevc_nvenc -preset p4     -b:v $B -an $OUT/hevcnvenc_$B.mp4
  ffmpeg -y -v error -i $REF -c:v hevc_nvenc -preset p7     -b:v $B -an $OUT/hevcnvencp7_$B.mp4
  metricas $OUT/x265_$B.mp4        $REF "HEVC CPU  x265 medium  @$B"
  metricas $OUT/hevcnvenc_$B.mp4   $REF "HEVC GPU  nvenc p4     @$B"
  metricas $OUT/hevcnvencp7_$B.mp4 $REF "HEVC GPU  nvenc p7     @$B"
  echo
done

echo "############ CALIDAD H.264 4K @20M ############"
ffmpeg -y -v error -i $REF4K -c:v libx264    -preset medium -b:v 20M -an $OUT/x264_4k.mp4
ffmpeg -y -v error -i $REF4K -c:v h264_nvenc -preset p4     -b:v 20M -an $OUT/nvenc_4k.mp4
metricas $OUT/x264_4k.mp4  $REF4K "H264 4K CPU x264 medium @20M"
metricas $OUT/nvenc_4k.mp4 $REF4K "H264 4K GPU nvenc p4    @20M"

rm -f $OUT/_v.json
echo "=== FIN CALIDAD ==="
gpu_release
