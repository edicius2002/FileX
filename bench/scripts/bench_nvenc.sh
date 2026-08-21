#!/usr/bin/env bash
# FASE 1-A: NVENC extendido. Todas las mediciones bajo el arnes obligatorio.
cd /d/Work/research/FileX
source bench/lib/harness.sh
gpu_acquire "fase1-nvenc" || exit 1

OUT=bench/salidas-fase1/video
mkdir -p "$OUT"
SRC1080=corpus/video/tipico.mp4          # 1920x1080 30fps 20s (600 frames)
SRC4K=corpus/video/fuente_4k.mp4         # 3840x2160 30fps 10s (300 frames)
N=7

echo "############ CONTEXTO ############"
echo "gpu_state (used,total,util,temp): $(gpu_state)"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
echo

echo "############ 1) libx264 medium vs h264_nvenc p4 ############"
measure "1080p CPU  libx264 -preset medium"  $N -- ffmpeg -y -v error -i $SRC1080 -c:v libx264 -preset medium -b:v 5M -an $OUT/1080p_x264.mp4
measure "1080p GPU  h264_nvenc -preset p4"   $N -- ffmpeg -y -v error -i $SRC1080 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/1080p_nvenc.mp4
measure "4K    CPU  libx264 -preset medium"  $N -- ffmpeg -y -v error -i $SRC4K   -c:v libx264 -preset medium -b:v 20M -an $OUT/4k_x264.mp4
measure "4K    GPU  h264_nvenc -preset p4"   $N -- ffmpeg -y -v error -i $SRC4K   -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/4k_nvenc.mp4
echo

echo "############ 2) libx265 vs hevc_nvenc (1080p) ############"
measure "1080p CPU  libx265 -preset medium"  $N -- ffmpeg -y -v error -i $SRC1080 -c:v libx265 -preset medium -b:v 3M -an $OUT/1080p_x265.mp4
measure "1080p GPU  hevc_nvenc -preset p4"   $N -- ffmpeg -y -v error -i $SRC1080 -c:v hevc_nvenc -preset p4 -b:v 3M -an $OUT/1080p_hevcnvenc.mp4
echo

echo "############ 3) tuberia GPU completa vs decode CPU + encode GPU ############"
measure "1080p decCPU+encGPU"                $N -- ffmpeg -y -v error -i $SRC1080 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/1080p_deccpu.mp4
measure "1080p decGPU+encGPU (hwaccel cuda)" $N -- ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $SRC1080 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/1080p_decgpu.mp4
measure "4K    decCPU+encGPU"                $N -- ffmpeg -y -v error -i $SRC4K   -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/4k_deccpu.mp4
measure "4K    decGPU+encGPU (hwaccel cuda)" $N -- ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $SRC4K -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/4k_decgpu.mp4
# con escalado, donde la copia de memoria pesa mas: 4K -> 1080p
measure "4K->1080p decCPU+scaleCPU+encGPU"   $N -- ffmpeg -y -v error -i $SRC4K -vf scale=1920:1080 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/4k_a_1080_cpu.mp4
measure "4K->1080p todo GPU (scale_cuda)"    $N -- ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $SRC4K -vf scale_cuda=1920:1080 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/4k_a_1080_gpu.mp4
echo

echo "############ 5) VRAM durante transcodificacion ############"
echo "linea base (idle): $(gpu_state)"
echo -n "1080p h264_nvenc      : "; peak_vram ffmpeg -y -v error -i $SRC1080 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/vram1.mp4
echo -n "1080p hevc_nvenc      : "; peak_vram ffmpeg -y -v error -i $SRC1080 -c:v hevc_nvenc -preset p4 -b:v 3M -an $OUT/vram2.mp4
echo -n "4K    h264_nvenc      : "; peak_vram ffmpeg -y -v error -i $SRC4K -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/vram3.mp4
echo -n "4K    tuberia GPU full: "; peak_vram ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $SRC4K -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/vram4.mp4
echo -n "4K    2 nvenc en par. : "; peak_vram bash -c "ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $SRC4K -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/vram5a.mp4 & ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $SRC4K -c:v hevc_nvenc -preset p4 -b:v 20M -an $OUT/vram5b.mp4 & wait"
echo "estado final: $(gpu_state)"
echo "=== FIN BENCH NVENC ==="
gpu_release
