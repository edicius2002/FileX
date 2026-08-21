#!/usr/bin/env bash
# FASE 2-A: matriz de configuraciones de OCR de docling.
# Cada corrida: REPS=9 conversiones en caliente por documento (mediana dentro del
# proceso, para no medir el arranque de Python) y peak_vram sobre el proceso entero.
set -u
cd /d/Work/research/FileX
source bench/lib/harness.sh
trap - EXIT INT TERM     # el lock lo gestiona el agente, no cada script
PY=".venv-ai/Scripts/python.exe"
export REPS=9

corrida(){  # etiqueta dispositivo motor backend [entorno extra]
  local et="$1" dev="$2" mot="$3" back="$4"
  echo "=================== $et ==================="
  echo "gpu_antes: $(gpu_state)  quiet_peak: $(gpu_quiet_check)%"
  peak_vram $PY bench/scripts/ocr_docling.py "$dev" "$mot" "$back" "$et"
  echo "gpu_despues: $(gpu_state)"
  $PY -c "
import json,sys
d=json.load(open(r'bench/salidas-fase2/${et}__resumen.json',encoding='utf-8'))
for x in d['docs']:
    print('  ', x['archivo'], x.get('segundos'), 's  rango', x.get('rango'), ' chars', x.get('chars'), x.get('error',''))
print('  torch_pico:', d['fin'].get('torch_max_reserved_MiB'), 'MiB')
"
}

case "${1:-todo}" in
  cpu)      FORZAR_ORT_CUDA=0 corrida docling_cpu           cpu  rapidocr onnxruntime ;;
  ocrcpu)   FORZAR_ORT_CUDA=0 corrida docling_cuda_ocrcpu   cuda rapidocr onnxruntime ;;
  ocrgpu)   FORZAR_ORT_CUDA=1 corrida docling_cuda_ocrgpu   cuda rapidocr onnxruntime ;;
  torch)    FORZAR_ORT_CUDA=0 corrida docling_cuda_torch    cuda rapidocr torch ;;
  torchcpu) FORZAR_ORT_CUDA=0 corrida docling_cpu_torch     cpu  rapidocr torch ;;
  easygpu)  corrida docling_easyocr_gpu  cuda easyocr onnxruntime ;;
  easycpu)  corrida docling_easyocr_cpu  cpu  easyocr onnxruntime ;;
  todo)
    FORZAR_ORT_CUDA=0 corrida docling_cpu         cpu  rapidocr onnxruntime
    FORZAR_ORT_CUDA=0 corrida docling_cuda_ocrcpu cuda rapidocr onnxruntime
    FORZAR_ORT_CUDA=1 corrida docling_cuda_ocrgpu cuda rapidocr onnxruntime
    ;;
esac
