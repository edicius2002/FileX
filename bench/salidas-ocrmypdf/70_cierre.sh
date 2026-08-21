#!/usr/bin/env bash
# Cierre: coste real en disco (cierre de dependencias), sobrecoste de invocar WSL
# desde Windows (que es lo que pagaria FileX) y verificacion de que .venv-ai sigue intacto.
set -u
R="/d/Work/research/FileX"

echo "=== 1. COSTE EN DISCO: cierre de dependencias de apt ==="
powershell.exe -NoProfile -Command "wsl -- bash /mnt/d/Work/research/FileX/bench/salidas-ocrmypdf/71_disco.sh" 2>&1 | tr -d '\r'

echo
echo "=== 2. SOBRECOSTE DE INVOCAR WSL DESDE WINDOWS (lo que pagaria FileX) ==="
. "$R/bench/lib/harness.sh"
measure "wsl: ocrmypdf --version" 9 -- wsl.exe -- ocrmypdf --version
measure "wsl: ocrmypdf d3 (/mnt/d)" 9 -- wsl.exe -- ocrmypdf -l spa --force-ocr \
    /mnt/d/Work/research/FileX/corpus/pdf/escaneado_d3.pdf /tmp/w.pdf
measure "nativo win: magick d3 -density 100" 9 -- \
    "/c/Program Files/ImageMagick-7.1.2-Q16-HDRI/magick" -density 100 \
    "D:/Work/research/FileX/corpus/pdf/escaneado_d3.pdf[0]" -colorspace Gray \
    "D:/Work/research/FileX/bench/salidas-ocrmypdf/img2/_bench.png"
measure "nativo win: magick d3 -density 100 -deskew" 9 -- \
    "/c/Program Files/ImageMagick-7.1.2-Q16-HDRI/magick" -density 100 \
    "D:/Work/research/FileX/corpus/pdf/escaneado_d3.pdf[0]" -colorspace Gray -deskew 40% +repage \
    "D:/Work/research/FileX/bench/salidas-ocrmypdf/img2/_bench2.png"

echo
echo "=== 3. VERIFICACION DE .venv-ai (regla 3) ==="
"$R/.venv-ai/Scripts/python.exe" -c "import torch,sys;print('torch',torch.__version__);print('cuda_disponible',torch.cuda.is_available());print('dispositivo',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NINGUNO')"
echo "--- .venv-paddle ---"
"$R/.venv-paddle/Scripts/python.exe" -c "import paddle;print('paddle',paddle.__version__);print('compilado_con_cuda',paddle.device.is_compiled_with_cuda());print('gpus',paddle.device.cuda.device_count())" 2>&1 | grep -v Warning
echo "--- lock de GPU ---"
[ -f "$R/bench/.gpu.lock" ] && echo "OJO: lock aun presente: $(cat "$R/bench/.gpu.lock")" || echo "lock liberado (correcto)"
rm -f "$R/bench/salidas-ocrmypdf/img2/_bench.png" "$R/bench/salidas-ocrmypdf/img2/_bench2.png"
