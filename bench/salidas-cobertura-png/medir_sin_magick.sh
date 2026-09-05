#!/usr/bin/env bash
# SUELO de la ganancia: la misma medida SIN la clase `Vp8lDeVerdad`, que es la
# unica que necesita ImageMagick nativo y por tanto la unica que un runner de
# Linux sin motores se salta (trampa 94: el recuento de una suite declara
# interprete, entorno y que quedo fuera).
set -eu
: "${PY:=/d/Work/research/FileX/.venv-mcp-filex/Scripts/python.exe}"
: "${PYLIBS:=C:\\Users\\krato\\AppData\\Local\\Temp\\claude\\D--Work-research-FileX\\fcb9a491-62eb-4b09-aa76-a7875fa0ab8d\\scratchpad\\pylibs}"
export PYTHONPATH="$PYLIBS"
export COVERAGE_FILE=bench/salidas-cobertura-png/.coverage-sin-magick
rm -f "$COVERAGE_FILE"
"$PY" -m coverage run --branch --source=filex -m unittest \
  pruebas.test_cob_png.AlfaCanalReal \
  pruebas.test_cob_png.SinMecanismoDeAlfa \
  pruebas.test_cob_png.AtajoDeFilaOpaca \
  pruebas.test_cob_png.Paleta \
  pruebas.test_cob_png.Exactitud \
  pruebas.test_cob_png.CaminosDeError \
  pruebas.test_cob_png.Adam7Geometria \
  pruebas.test_cob_png.LeerPaleta \
  pruebas.test_cob_png.Paeth \
  pruebas.test_cob_png.PredictoresVp8l \
  pruebas.test_cob_png.DefectosVigentes
"$PY" -m coverage json -o bench/salidas-cobertura-png/cobertura-sin-magick.json \
      --include='filex/verificador.py'
rm -f "$COVERAGE_FILE"
