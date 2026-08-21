#!/usr/bin/env bash
# Instalacion de la pila de IA en el venv del proyecto. NO usa GPU: puede correr
# en paralelo con las mediciones de NVENC.
set -x
cd /d/Work/research/FileX
PY=.venv-ai/Scripts/python.exe
$PY -m pip install -U pip setuptools wheel
$PY -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
$PY -m pip install "faster-whisper"
$PY -m pip install "docling"
$PY -m pip install "surya-ocr"
echo "=== FIN INSTALACION ==="
