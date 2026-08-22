# -*- coding: utf-8 -*-
"""P1 / B9 — cuantos PIXELES llegan de verdad al detector.

La pregunta del encargo («¿el limite es absoluto, relativo o de tamaño en pixeles?»)
no se puede contestar leyendo la documentacion: hay que sondear en ejecucion, que es
la regla del proyecto. Este script engancha la funcion de reescalado interna de cada
motor y anota el array EXACTO que entra a la red, para cada rasterizacion del barrido.

No pide GPU (todo en CPU, sin lock): solo se instrumenta el preprocesado.

uso: python sonda_detector.py <rapidocr|paddleocr> <imgdir> <glob>
"""
import glob as _glob
import json
import os
import sys

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-ppp-norm")
sys.path.insert(0, BASE)
sys.stdout.reconfigure(encoding="utf-8")

motor = sys.argv[1]
IMG = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "img")
GLOB = sys.argv[3] if len(sys.argv) > 3 else "*.png"
rutas = sorted(_glob.glob(os.path.join(IMG, GLOB)))
out = {}

if motor == "rapidocr":
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import (EngineType, LangDet, LangRec, ModelType, OCRVersion,
                          RapidOCR)
    from rapidocr.ch_ppocr_det import utils as _u

    reg = []
    _orig = _u.DetPreProcess.resize

    def _hook(self, img):
        h, w = img.shape[:2]
        r = _orig(self, img)
        reg.append({"entrada_px": [w, h],
                    "a_la_red_px": ([int(r.shape[1]), int(r.shape[0])]
                                    if r is not None else None),
                    "limit_side_len": self.limit_side_len,
                    "limit_type": self.limit_type})
        return r

    _u.DetPreProcess.resize = _hook
    lector = RapidOCR(params={
        "EngineConfig.onnxruntime.use_cuda": False,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": LangDet("ch"), "Rec.lang_type": LangRec("ch"),
        "Det.ocr_version": OCRVersion("PP-OCRv6"),
        "Rec.ocr_version": OCRVersion("PP-OCRv6"),
        "Det.model_type": ModelType("small"), "Rec.model_type": ModelType("small"),
        "Global.model_root_dir": os.path.join(BASE, "modelos")})
    for ruta in rutas:
        reg.clear()
        lector(ruta)
        n = os.path.splitext(os.path.basename(ruta))[0]
        out[n] = reg[0] if reg else None
        print(f"{n:36s} {out[n]}")

elif motor == "paddleocr":
    from paddleocr import PaddleOCR
    from paddlex.inference.models.text_detection import processors as _p

    reg = []
    _orig = _p.DetResizeForTest.resize_image_type0

    def _hook(self, img, limit_side_len, limit_type, max_side_limit=None):
        h, w = img.shape[:2]
        r, ratio = _orig(self, img, limit_side_len, limit_type, max_side_limit)
        reg.append({"entrada_px": [w, h],
                    "a_la_red_px": ([int(r.shape[1]), int(r.shape[0])]
                                    if r is not None else None),
                    "limit_side_len": limit_side_len or self.limit_side_len,
                    "limit_type": limit_type or self.limit_type,
                    "max_side_limit": max_side_limit})
        return r, ratio

    _p.DetResizeForTest.resize_image_type0 = _hook
    lector = PaddleOCR(device="cpu", use_doc_orientation_classify=False,
                       use_doc_unwarping=False, use_textline_orientation=False)
    for ruta in rutas:
        reg.clear()
        lector.predict(ruta)
        n = os.path.splitext(os.path.basename(ruta))[0]
        out[n] = reg[0] if reg else None
        print(f"{n:36s} {out[n]}")
else:
    raise SystemExit("motor?")

json.dump(out, open(os.path.join(BASE, "json", f"sonda_detector_{motor}.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=2)
