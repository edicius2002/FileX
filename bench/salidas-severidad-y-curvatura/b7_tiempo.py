#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B7 -- el TIEMPO como segunda senal candidata de severidad, dentro de UNA
sola tanda (las cifras absolutas de tandas distintas no son comparables; las
relativas dentro de una tanda, si). Reutiliza los 20 rasteres YA generados en
la ronda 8 (`bench/salidas-deskew-y-fidelidad/img/`, familia d4, 200/280 ppp,
base/deskew) -- no genera nada nuevo, no toca el corpus.

Dos testigos de ruido (deriva + nivel de carga), como exige `bench/lib/harness.sh`.

uso: python b7_tiempo.py [--reps 3]
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMG = os.path.join(ROOT, "bench", "salidas-deskew-y-fidelidad", "img")
AQUI = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(AQUI, "json")
os.makedirs(JS, exist_ok=True)

TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"

DOCS = ["escaneado_d4", "escaneado_d4a", "escaneado_d4b", "escaneado_d4c", "escaneado_d4e"]
CELDAS = [(doc, ppp, deskew) for doc in DOCS for ppp in (200, 280) for deskew in (False, True)]


def testigo_mono(n=400000):
    t = time.perf_counter()
    z = 0
    for i in range(n):
        z += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope_s=20.0):
    vals = []
    t_ini = time.perf_counter()
    for _ in range(n):
        restante = tope_s - (time.perf_counter() - t_ini)
        if restante <= 0.5:
            return round(tope_s * 1000, 2)
        t = time.perf_counter()
        try:
            subprocess.run(["ffprobe", "-v", "quiet", "-version"], stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=restante)
        except Exception:
            return round(tope_s * 1000, 2)
        vals.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(vals), 2) if vals else round(tope_s * 1000, 2)


def leer_con_tiempo(path):
    out = os.path.join(AQUI, "tmp_tess_tiempo")
    t0 = time.perf_counter()
    r = subprocess.run([TESS, path, out, "-l", "spa", "--psm", "3"],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=20,
                       env={**os.environ, "TESSDATA_PREFIX": TESSDATA})
    ms = (time.perf_counter() - t0) * 1000
    return ms, r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    mono_ini = testigo_mono()
    proc_ini = testigo_proceso()

    filas = []
    for doc, ppp, deskew in CELDAS:
        nom = f"{doc}__ppp{ppp}__{'deskew' if deskew else 'base'}"
        path = os.path.join(IMG, nom + ".png")
        tiempos = []
        for _ in range(args.reps):
            ms, rc = leer_con_tiempo(path)
            tiempos.append(ms)
        fila = {"doc": doc, "ppp": ppp, "deskew": deskew, "n": args.reps,
                "ms_mediana": round(statistics.median(tiempos), 1), "ms_reps": [round(x, 1) for x in tiempos]}
        filas.append(fila)
        print(json.dumps(fila, ensure_ascii=False))

    mono_fin = testigo_mono()
    proc_fin = testigo_proceso()
    ruido = {"mono_ini": mono_ini, "mono_fin": mono_fin,
             "deriva": round(mono_fin / max(mono_ini, .01), 2),
             "proc_ini": proc_ini, "proc_fin": proc_fin,
             "nivel": round(max(proc_ini, proc_fin) / 26.65, 2)}

    base = min(f["ms_mediana"] for f in filas)
    for f in filas:
        f["razon_vs_mas_rapida"] = round(f["ms_mediana"] / base, 2)

    out = {"motor": "tesseract-psm3-spa", "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel"] > 2 else "limpia",
           "rows": filas}
    json.dump(out, open(os.path.join(JS, "b7_tiempo.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)
    print(json.dumps(ruido, ensure_ascii=False))
    print(f"etiqueta_ruido={out['etiqueta_ruido']}")


if __name__ == "__main__":
    main()
