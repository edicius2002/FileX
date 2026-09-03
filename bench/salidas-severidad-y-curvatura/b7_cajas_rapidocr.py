# -*- coding: utf-8 -*-
"""B7 (ronda 12) -- el proxy sin verdad conocida que quedaba PENDIENTE de la
ronda 10: cajas del detector de RapidOCR, como denominador en vez de
`bytes_referencia` (que en produccion no se conoce).

Reutiliza el enganche de `TextDetector.__call__` (misma tecnica que
`bench/salidas-presupuesto-vram/n31_fases_child.py`, ronda 11) sobre los 20
rasteres YA generados en la ronda 8 (`bench/salidas-deskew-y-fidelidad/img/`,
familia d4, 200/280 ppp, base/deskew) -- no genera nada nuevo, no toca el
corpus.

Un solo proceso, sin reiniciar entre imagenes: aqui NO se mide VRAM (eso ya se
midio en N31 y se sabe que el asignador no libera memoria), se miden cajas y
bytes de salida, que son deterministas independientemente del estado del
asignador.

uso: D:\Work\research\FileX\.venv-ai\Scripts\python.exe b7_cajas_rapidocr.py
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
IMG = os.path.join(ROOT, "bench", "salidas-deskew-y-fidelidad", "img")
JS = os.path.join(AQUI, "json")
os.makedirs(JS, exist_ok=True)

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
CELDAS = [(doc, ppp, deskew) for doc in DOCS for ppp in (200, 280) for deskew in (False, True)]


def build():
    import torch
    tl = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.isdir(tl):
        os.add_dll_directory(tl)
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    from rapidocr.ch_ppocr_det.main import TextDetector

    reg = {}
    _orig = TextDetector.__call__

    def _hook(self, img, *a, **kw):
        r = _orig(self, img, *a, **kw)
        h, w = img.shape[:2]
        boxes = r.boxes
        n = 0 if boxes is None else len(boxes)
        area = 0.0
        if boxes is not None:
            for b in boxes:
                x = b[:, 0]
                y = b[:, 1]
                area += 0.5 * abs(sum(x[i] * y[(i + 1) % len(x)] - x[(i + 1) % len(x)] * y[i]
                                      for i in range(len(x))))
        reg["n_cajas"] = n
        reg["area_cajas_px"] = round(float(area), 1)
        reg["area_pagina_px"] = h * w
        reg["area_cajas_pct"] = round(100.0 * area / (h * w), 3) if h * w else 0.0
        reg["red_px"] = [int(w), int(h)]
        return r

    TextDetector.__call__ = _hook

    kw = {"EngineConfig.onnxruntime.use_cuda": True,
          "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
          "Det.engine_type": EngineType.ONNXRUNTIME, "Cls.engine_type": EngineType.ONNXRUNTIME,
          "Rec.engine_type": EngineType.ONNXRUNTIME, "Det.lang_type": LangDet("ch"),
          "Rec.lang_type": LangRec("ch"), "Det.ocr_version": OCRVersion("PP-OCRv6"),
          "Rec.ocr_version": OCRVersion("PP-OCRv6"), "Det.model_type": ModelType("small"),
          "Rec.model_type": ModelType("small")}
    kw.update(R6)
    x = RapidOCR(params=kw)
    return x, reg


def main():
    lock = gpu.Lock("B7-cajas-rapidocr")
    with lock:
        lector, reg = build()
        filas = []
        for doc, ppp, deskew in CELDAS:
            nom = f"{doc}__ppp{ppp}__{'deskew' if deskew else 'base'}"
            path = os.path.join(IMG, nom + ".png")
            reg.clear()
            r = lector(path)
            texto = " ".join(r.txts) if r and r.txts else ""
            ev = evaluar(texto, "acentos", REF)
            fila = {"doc": doc, "ppp": ppp, "deskew": deskew,
                    "bytes": len(texto.encode("utf-8")), "cer_pct": ev["cer_pct"],
                    **reg}
            filas.append(fila)
            print(json.dumps(fila, ensure_ascii=False, default=float))

    json.dump(filas, open(os.path.join(JS, "b7_cajas_rapidocr.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2, default=float)
    print(f"\n-> {JS}/b7_cajas_rapidocr.json ({len(filas)} celdas)")


if __name__ == "__main__":
    main()
