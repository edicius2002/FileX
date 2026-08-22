#!/usr/bin/env bash
# G1 / cierre — regla 3 del encargo: comprobar que .venv-ai sigue con torch CUDA.
# (`pip install surya-ocr` ya lo degrado a +cpu una vez sin dar ningun error.)
set -u
R="/d/Work/research/FileX"
echo "=== .venv-ai ==="
"$R/.venv-ai/Scripts/python.exe" -c "
import torch, importlib.metadata as md
print('torch          ', torch.__version__)
print('cuda disponible', torch.cuda.is_available())
print('dispositivo    ', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')
for p in ('rapidocr','easyocr','docling','onnxruntime','onnxruntime-gpu','pypdfium2'):
    try: print(f'{p:16s}', md.version(p))
    except Exception: print(f'{p:16s} (no instalado)')
"
echo "=== .venv-paddle ==="
"$R/.venv-paddle/Scripts/python.exe" -c "
import paddle, importlib.metadata as md
print('paddle         ', paddle.__version__)
print('compilado cuda ', paddle.device.is_compiled_with_cuda())
print('n dispositivos ', paddle.device.cuda.device_count())
print('paddleocr      ', md.version('paddleocr'))
"
echo "=== lock de GPU ==="
[ -f "$R/bench/.gpu.lock" ] && echo "OCUPADO: $(cat "$R/bench/.gpu.lock")" || echo "libre (correcto)"
echo "=== GPU ==="
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader
echo "=== disco de salidas-ocr-ppp ==="
du -sh "$R/bench/salidas-ocr-ppp"/* 2>/dev/null | sort -h
