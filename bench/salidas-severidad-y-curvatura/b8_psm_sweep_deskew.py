#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cierra el PENDIENTE de la ronda 8 (bench/deskew-y-fidelidad.md S1.2): las
tres celdas catastroficas eran Tesseract `--psm 3`. Aqui se barren tambien
`--psm 6` y `--psm 11` -- las otras dos clases reales de comportamiento
(`bench/k-oem-acantilados.md` SB24) -- sobre las 4 celdas de la familia `d4`
que -deskew deja en 0 bytes con psm 3, reusando los rasteres YA generados en
la ronda 8 (bench/salidas-deskew-y-fidelidad/img/, no genera nada nuevo).

uso: python b8_psm_sweep_deskew.py
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMG = os.path.join(ROOT, "bench", "salidas-deskew-y-fidelidad", "img")
AQUI = os.path.dirname(os.path.abspath(__file__))
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d4"))
from d4_texto import BLOQUES  # noqa: E402
REF = [linea for bloque in BLOQUES.values() for linea in bloque]

CELDAS = [("escaneado_d4", 200, True), ("escaneado_d4", 280, True),
          ("escaneado_d4c", 200, True), ("escaneado_d4c", 280, True)]
PSMS = [3, 6, 11]


def leer(path, psm):
    out = os.path.join(AQUI, "tmp_psm")
    r = subprocess.run([TESS, path, out, "-l", "spa", "--psm", str(psm)],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=20,
                       env={**os.environ, "TESSDATA_PREFIX": TESSDATA})
    if r.returncode == 0 and os.path.exists(out + ".txt"):
        return open(out + ".txt", encoding="utf-8", errors="replace").read(), 0
    return "", r.returncode


def main():
    filas = []
    for doc, ppp, deskew in CELDAS:
        nom = f"{doc}__ppp{ppp}__deskew"
        path = os.path.join(IMG, nom + ".png")
        for psm in PSMS:
            texto, rc = leer(path, psm)
            ev = evaluar(texto, "acentos", REF)
            fila = {"doc": doc, "ppp": ppp, "psm": psm, "rc": rc,
                    "bytes": len(texto.encode("utf-8")), "cer_pct": ev["cer_pct"]}
            filas.append(fila)
            print(json.dumps(fila, ensure_ascii=False))

    js = os.path.join(AQUI, "json")
    os.makedirs(js, exist_ok=True)
    json.dump(filas, open(os.path.join(js, "b8_psm_sweep_deskew.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
