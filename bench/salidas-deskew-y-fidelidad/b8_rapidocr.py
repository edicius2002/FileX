#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B8(b) -- RapidOCR v6 small + R6 sobre los 20 rasteres de raster_b8.py.
Toma el lock de GPU para toda la tanda (un solo proceso, VRAM inmune a
recortar -- trampa 29/67) y lo suelta al final.

uso: python b8_rapidocr.py [--reps 3]
"""
import argparse
import json
import os
import statistics
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

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d4"))
from d4_texto import BLOQUES  # noqa: E402
REF = [linea for bloque in BLOQUES.values() for linea in bloque]
sys.path.insert(0, ROOT)
from filex import gpu  # noqa: E402

R6 = {"Det.mean": [.485, .456, .406], "Det.std": [.229, .224, .225], "Det.thresh": .2,
      "Det.box_thresh": .45, "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000}

DOCS = ["escaneado_d4", "escaneado_d4a", "escaneado_d4b", "escaneado_d4c", "escaneado_d4e"]
# Descendente por Mpx (280 antes que 200) dentro de cada documento -- trampa 67,
# aunque RapidOCR sea inmune, se mantiene la disciplina.
CELDAS = [(doc, ppp, deskew) for doc in DOCS for ppp in (280, 200) for deskew in (True, False)]


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


def build():
    import torch
    tl = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.isdir(tl):
        os.add_dll_directory(tl)
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    kw = {"EngineConfig.onnxruntime.use_cuda": True,
          "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
          "Det.engine_type": EngineType.ONNXRUNTIME, "Cls.engine_type": EngineType.ONNXRUNTIME,
          "Rec.engine_type": EngineType.ONNXRUNTIME, "Det.lang_type": LangDet("ch"),
          "Rec.lang_type": LangRec("ch"), "Det.ocr_version": OCRVersion("PP-OCRv6"),
          "Rec.ocr_version": OCRVersion("PP-OCRv6"), "Det.model_type": ModelType("small"),
          "Rec.model_type": ModelType("small")}
    kw.update(R6)
    x = RapidOCR(params=kw)
    return lambda p: (lambda r: " ".join(r.txts) if r and r.txts else "")(x(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    lock = gpu.Lock("B8-rapidocr")
    with lock as lk:
        leer = build()
        mono_ini = testigo_mono()
        proc_ini = testigo_proceso()
        rows = []
        t0 = time.time()
        for doc, ppp, deskew in CELDAS:
            nom = f"{doc}__ppp{ppp}__{'deskew' if deskew else 'base'}"
            path = os.path.join(IMG, nom + ".png")
            textos, cers, rcs = [], [], []
            for _ in range(args.reps):
                try:
                    texto = leer(path)
                    rc = 0
                except Exception as ex:
                    texto = ""
                    rc = f"{type(ex).__name__}: {str(ex)[:150]}"
                textos.append(texto)
                rcs.append(rc)
                ev = evaluar(texto, "acentos", REF)
                cers.append(ev["cer_pct"])
            texto = textos[-1]
            open(os.path.join(TXT, "rapidocr__" + nom + ".txt"), "w",
                 encoding="utf-8").write(texto)
            row = {"motor": "rapidocr-v6-r6", "doc": doc, "ppp": ppp, "deskew": deskew,
                   "n": args.reps, "determinista": len(set(textos)) == 1,
                   "cer_pct": cers[-1], "cer_reps": cers, "rc_reps": rcs}
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
        mono_fin = testigo_mono()
        proc_fin = testigo_proceso()
    ruido = {"mono_ini": mono_ini, "mono_fin": mono_fin,
             "deriva": round(mono_fin / max(mono_ini, .01), 2),
             "proc_ini": proc_ini, "proc_fin": proc_fin,
             "nivel": round(max(proc_ini, proc_fin) / 26.65, 2)}
    out = {"motor": "rapidocr-v6-r6", "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(os.path.join(JS, "b8_rapidocr.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
