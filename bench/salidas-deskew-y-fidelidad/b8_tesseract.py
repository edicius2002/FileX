#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B8(b) -- Tesseract 5, psm 3, spa, sobre los 20 rasteres de raster_b8.py.
CPU pura: no toma el lock de GPU. Es el motor sensible al pHYs (trampa 29),
por eso es el segundo motor del barrido -- el contraste con RapidOCR (inmune)
es lo que decide si -deskew interactua con el pHYs declarado.

uso: python b8_tesseract.py [--reps 3]
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, "bench", "salidas-deskew-y-fidelidad")
IMG = os.path.join(BASE, "img")
JS = os.path.join(BASE, "json")
TXT = os.path.join(BASE, "texto")
os.makedirs(JS, exist_ok=True)
os.makedirs(TXT, exist_ok=True)

TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d4"))
from d4_texto import BLOQUES  # noqa: E402
REF = [linea for bloque in BLOQUES.values() for linea in bloque]

DOCS = ["escaneado_d4", "escaneado_d4a", "escaneado_d4b", "escaneado_d4c", "escaneado_d4e"]
CELDAS = [(doc, ppp, deskew) for doc in DOCS for ppp in (200, 280) for deskew in (False, True)]


def leer(path):
    out = os.path.join(BASE, "img", "tmp_b8_tess")
    r = subprocess.run([TESS, path, out, "-l", "spa", "--psm", "3"],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=20,
                       env={**os.environ, "TESSDATA_PREFIX": TESSDATA})
    if r.returncode == 0 and os.path.exists(out + ".txt"):
        return open(out + ".txt", encoding="utf-8", errors="replace").read(), 0
    return "", r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    rows = []
    t0 = time.time()
    for doc, ppp, deskew in CELDAS:
        nom = f"{doc}__ppp{ppp}__{'deskew' if deskew else 'base'}"
        path = os.path.join(IMG, nom + ".png")
        textos, cers, rcs = [], [], []
        for _ in range(args.reps):
            texto, rc = leer(path)
            textos.append(texto)
            rcs.append(rc)
            ev = evaluar(texto, "acentos", REF)
            cers.append(ev["cer_pct"])
        texto = textos[-1]
        open(os.path.join(TXT, "tesseract__" + nom + ".txt"), "w",
             encoding="utf-8").write(texto)
        row = {"motor": "tesseract-psm3-spa", "doc": doc, "ppp": ppp, "deskew": deskew,
               "n": args.reps, "determinista": len(set(textos)) == 1,
               "cer_pct": cers[-1], "cer_reps": cers, "rc_reps": rcs}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    out = {"motor": "tesseract-psm3-spa", "rows": rows,
           "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(os.path.join(JS, "b8_tesseract.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
