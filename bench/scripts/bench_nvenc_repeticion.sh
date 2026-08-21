#!/usr/bin/env bash
# Repeticion de las mediciones de la seccion 1 en entorno tranquilo.
# La primera tanda coincidio con la descarga/instalacion de PyTorch (2,5 GB)
# y produjo rangos absurdos (2100-22061 ms). Esta tanda se hace con la maquina
# sin instalaciones en curso. N=9.
cd /d/Work/research/FileX
source bench/lib/harness.sh
gpu_acquire "fase1-nvenc-rep" || exit 1
OUT=bench/salidas-fase1/video; N=9
S1=corpus/video/tipico.mp4; S4=corpus/video/fuente_4k.mp4
echo "gpu_state: $(gpu_state)"
measure "REP 1080p CPU libx264 medium"    $N -- ffmpeg -y -v error -i $S1 -c:v libx264 -preset medium -b:v 5M -an $OUT/r_1080_x264.mp4
measure "REP 1080p GPU h264_nvenc p4"     $N -- ffmpeg -y -v error -i $S1 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/r_1080_nvenc.mp4
measure "REP 4K    CPU libx264 medium"    $N -- ffmpeg -y -v error -i $S4 -c:v libx264 -preset medium -b:v 20M -an $OUT/r_4k_x264.mp4
measure "REP 4K    GPU h264_nvenc p4"     $N -- ffmpeg -y -v error -i $S4 -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/r_4k_nvenc.mp4
measure "REP 1080p CPU libx265 medium"    $N -- ffmpeg -y -v error -i $S1 -c:v libx265 -preset medium -b:v 3M -an $OUT/r_1080_x265.mp4
measure "REP 1080p GPU hevc_nvenc p4"     $N -- ffmpeg -y -v error -i $S1 -c:v hevc_nvenc -preset p4 -b:v 3M -an $OUT/r_1080_hevcnvenc.mp4
measure "REP 4K->1080p decCPU+scaleCPU"   $N -- ffmpeg -y -v error -i $S4 -vf scale=1920:1080 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/r_4k1080_cpu.mp4
measure "REP 4K->1080p todo GPU"          $N -- ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $S4 -vf scale_cuda=1920:1080 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/r_4k1080_gpu.mp4
measure "REP 4K decCPU+encGPU"            $N -- ffmpeg -y -v error -i $S4 -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/r_4k_deccpu.mp4
measure "REP 4K decGPU+encGPU"            $N -- ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $S4 -c:v h264_nvenc -preset p4 -b:v 20M -an $OUT/r_4k_decgpu.mp4
measure "REP 1080p decCPU+encGPU"         $N -- ffmpeg -y -v error -i $S1 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/r_1080_deccpu.mp4
measure "REP 1080p decGPU+encGPU"         $N -- ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $S1 -c:v h264_nvenc -preset p4 -b:v 5M -an $OUT/r_1080_decgpu.mp4
# transcodificacion completa con audio (caso real de conversor)
measure "REP 1080p completo CPU (v+a)"    $N -- ffmpeg -y -v error -i $S1 -c:v libx264 -preset medium -b:v 5M -c:a aac -b:a 128k $OUT/r_full_cpu.mp4
measure "REP 1080p completo GPU (v+a)"    $N -- ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i $S1 -c:v h264_nvenc -preset p4 -b:v 5M -c:a aac -b:a 128k $OUT/r_full_gpu.mp4
# patologico: 2 pistas de audio, mkv 720p
measure "REP patologico 2 pistas CPU"     $N -- ffmpeg -y -v error -i corpus/video/patologico_2pistas.mkv -map 0 -c:v libx264 -preset medium -b:v 3M -c:a aac $OUT/r_pat_cpu.mkv
measure "REP patologico 2 pistas GPU"     $N -- ffmpeg -y -v error -hwaccel cuda -hwaccel_output_format cuda -i corpus/video/patologico_2pistas.mkv -map 0 -c:v h264_nvenc -preset p4 -b:v 3M -c:a aac $OUT/r_pat_gpu.mkv
echo "gpu_state final: $(gpu_state)"
echo "=== FIN REPETICION ==="
gpu_release
