#!/usr/bin/env bash
# Cobertura de `filex/verificador.py` bajo SOLO el modulo del carril cob/png.
# Se ejecuta desde la raiz del worktree. No lanza la suite completa (hay otros
# workers en la maquina; trampas 101 y 123).
#
#   PY=<python.exe> PYLIBS=<dir con coverage> bash bench/salidas-cobertura-png/medir.sh
#
# `coverage` 7.16.0 se carga por PYTHONPATH y NO se instala en ningun .venv-*
# (regla §1 de CLAUDE.md).
set -eu
: "${PY:=/d/Work/research/FileX/.venv-mcp-filex/Scripts/python.exe}"
: "${PYLIBS:=C:\\Users\\krato\\AppData\\Local\\Temp\\claude\\D--Work-research-FileX\\fcb9a491-62eb-4b09-aa76-a7875fa0ab8d\\scratchpad\\pylibs}"
export PYTHONPATH="$PYLIBS"
export COVERAGE_FILE=bench/salidas-cobertura-png/.coverage
rm -f "$COVERAGE_FILE"
"$PY" -m coverage run --branch --source=filex -m unittest pruebas.test_cob_png
"$PY" -m coverage json -o bench/salidas-cobertura-png/cobertura.json \
      --include='filex/verificador.py'
"$PY" -m coverage report --include='filex/verificador.py'
rm -f "$COVERAGE_FILE"
