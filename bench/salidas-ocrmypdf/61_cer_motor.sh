#!/usr/bin/env bash
# FASE 2: CER de OCRmyPDF *como motor* (sidecar de Tesseract), contra la referencia.
set -u
R="/d/Work/research/FileX"
S="$R/bench/salidas-ocrmypdf/sidecar"
mkdir -p "$S"
powershell.exe -NoProfile -Command "wsl -- bash -c 'cp \$HOME/ocrx/out/*.txt /mnt/d/Work/research/FileX/bench/salidas-ocrmypdf/sidecar/; cp \$HOME/ocrx/diag2/unp_*.txt /mnt/d/Work/research/FileX/bench/salidas-ocrmypdf/sidecar/ 2>/dev/null; true'" >/dev/null 2>&1
"$R/.venv-ai/Scripts/python.exe" - <<'PY'
import json, os, sys
R = r"D:\Work\research\FileX"
sys.path.insert(0, os.path.join(R, r"bench\scripts"))
from ocr_eval import evaluar
S = os.path.join(R, r"bench\salidas-ocrmypdf\sidecar")
DOCS = ["patologico_escaneado", "escaneado_d1", "escaneado_d2", "escaneado_d3"]
REC = ["base","deskew","clean","rotate","todo","os300","os400","deskew_os300","clean_os300",
       "unp_agresivo","unp_deskewup"]
print("### OCRmyPDF COMO MOTOR (Tesseract 5.5, CPU) — CER % / distancia de edicion")
print(f"{'receta':<16}" + "".join(f"{d[:16]:>22}" for d in DOCS))
tabla = {}
for r in REC:
    fila = f"{r:<16}"
    for d in DOCS:
        p = os.path.join(S, f"{r}__{d}.txt")
        if not os.path.exists(p):
            fila += f"{'(no ejecutado)':>22}"; continue
        ev = evaluar(open(p, encoding="utf-8", errors="replace").read())
        tabla[f"{r}__{d}"] = ev
        fila += f"{ev['cer_pct']:>15.1f}% /{ev['dist_global']:>4d}"
    print(fila)
print("\n(rmbg / todo_rmbg: NO EJECUTAN — NotImplementedError, ver logs/12)")
json.dump({k: {"cer_pct": v["cer_pct"], "dist_global": v["dist_global"],
               "frases_exactas": v["frases_exactas"], "texto": v["normalizada"]}
           for k, v in tabla.items()},
          open(os.path.join(S, "_cer_motor.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
PY
