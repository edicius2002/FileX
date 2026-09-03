#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""C18 -- reproduce el camino I1 de bench/fidelidad-caminos.md con sus
PARAMETROS LITERALES, leidos de bench/salidas-fidelidad/_caminos.py y
_clasifica.py (no adivinados): ppp=150 SOLO en el primer rasterizado,
TESSDATA_PREFIX apuntando al tessdata de Tesseract-OCR (solo eng+osd,
luego el idioma de OCR es eng por defecto, sin -sOCRLanguage=), y la
formula de similitud exacta de _clasifica.py:similitud() (_norm quita
TODO lo que no sea alfanumerico -- incluidos los espacios -- antes de
comparar con difflib.SequenceMatcher).

I1 = ("gs","png",P150) -> ("im","pdf",{}) -> ("gs","txt",OCR) sobre
corpus/pdf/tipico_texto.pdf. Ninguno de los tres pasos fija resolucion
en el paso final de OCR: el -r150 solo se aplica al PRIMER rasterizado.

uso: python c18_repro_i1.py [--reps 3]
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, "bench", "salidas-deskew-y-fidelidad")
JS = os.path.join(BASE, "json")
os.makedirs(JS, exist_ok=True)

GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
SRC = os.path.join(ROOT, "corpus", "pdf", "tipico_texto.pdf")
# Literal de bench/salidas-fidelidad/_caminos.py:26 -- solo eng+osd disponibles ahi.
TESSDATA = r"C:\Program Files\Tesseract-OCR\tessdata"
ENV_GS = {**os.environ, "TESSDATA_PREFIX": TESSDATA}


def _norm(s):
    # Literal de bench/salidas-fidelidad/_clasifica.py:36-37
    return re.sub(r"[^0-9a-zA-Z]", "", s).lower()


def similitud(a, b):
    # Literal de bench/salidas-fidelidad/_clasifica.py:39-52
    ta, tb = _norm(a), _norm(b)
    if not ta:
        return None
    m = difflib.SequenceMatcher(None, ta, tb)
    return sum(bl.size for bl in m.get_matching_blocks()) / len(ta)


def run(cmd, **kw):
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=60, **kw)


def texto_original(pdf):
    # Literal de bench/salidas-fidelidad/_sonda.py:78-86 (rama pdf/ps/eps)
    sal = pdf + ".txtwrite.txt"
    r = run([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
             "-sDEVICE=txtwrite", "-sOutputFile=" + sal, pdf])
    if r.returncode != 0 or not os.path.exists(sal):
        raise RuntimeError(f"txtwrite rc={r.returncode}: {r.stderr[:300]}")
    s = open(sal, encoding="utf-8", errors="replace").read()
    os.remove(sal)
    return s


def celda(tmpdir, i):
    p1 = os.path.join(tmpdir, f"paso1_{i}.png")
    p2 = os.path.join(tmpdir, f"paso2_{i}.pdf")
    p3 = os.path.join(tmpdir, f"paso3_{i}.txt")

    r1 = run([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
              "-sDEVICE=png16m", "-r150", "-sOutputFile=" + p1, SRC])
    if r1.returncode:
        return {"rc_paso1": r1.returncode}

    r2 = run([MAGICK, p1, p2])
    if r2.returncode:
        return {"rc_paso1": 0, "rc_paso2": r2.returncode}

    r3 = run([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
              "-sDEVICE=ocr", "-sOutputFile=" + p3, p2], env=ENV_GS)
    if r3.returncode or not os.path.exists(p3):
        return {"rc_paso1": 0, "rc_paso2": 0, "rc_paso3": r3.returncode}

    texto = open(p3, encoding="utf-8", errors="replace").read()
    return {"rc_paso1": 0, "rc_paso2": 0, "rc_paso3": 0,
            "texto": texto, "sha256_paso3": hashlib.sha256(texto.encode()).hexdigest(),
            "bytes_paso3": len(texto.encode())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--tmpdir", default=os.path.join(BASE, "_tmp_c18"))
    args = ap.parse_args()
    os.makedirs(args.tmpdir, exist_ok=True)

    original = texto_original(SRC)
    filas = []
    for i in range(args.reps):
        filas.append(celda(args.tmpdir, i))

    hashes = {f.get("sha256_paso3") for f in filas}
    determinista = len(hashes) == 1 and None not in hashes
    ultimo = filas[-1]
    sim = similitud(original, ultimo["texto"]) if ultimo.get("texto") is not None else None

    out = {
        "camino": "I1 (pdf con texto -> png 150ppp -> pdf sin flags -> txt OCR eng)",
        "entrada": os.path.basename(SRC),
        "parametros_literales": {
            "ppp_rasterizado_paso1": 150,
            "ppp_paso_ocr_final": "sin -r explicito (por defecto del dispositivo ocr)",
            "idioma_ocr": "eng (TESSDATA_PREFIX solo trae eng+osd, sin -sOCRLanguage=)",
            "formula_similitud": "sum(matching_blocks)/len(_norm(original)); "
                                  "_norm quita todo salvo [0-9a-zA-Z] y pasa a minusculas",
        },
        "reps": args.reps,
        "determinista": determinista,
        "texto_original": original,
        "texto_ocr": ultimo.get("texto"),
        "similitud": sim,
        "similitud_fmt_1dp": f"{sim:.1%}" if sim is not None else None,
        "afirmacion_original": "99,0% (bench/fidelidad-caminos.md linea 196)",
        "afirmacion_verificador_ghostscript": "94,7-97,1% NO REPRODUCIDO (bench/verificador-ghostscript.md §5.7)",
        "veredicto": "REPRODUCIDO" if sim is not None and round(sim, 3) == round(0.9896907216494846, 3) else "REVISAR",
        "filas_crudas": filas,
    }
    json.dump(out, open(os.path.join(JS, "c18_repro_i1.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)
    resumen = {k: v for k, v in out.items() if k not in ("filas_crudas", "texto_original", "texto_ocr")}
    print(json.dumps(resumen, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
