# -*- coding: utf-8 -*-
"""N31 -- proceso HIJO: una sola llamada a RapidOCR sobre UNA imagen, con la
VRAM sondeada en ejecucion (enganchando las clases reales del paquete, la
misma tecnica de `bench/salidas-ppp-norm/sonda_detector.py`) en cada fase del
pipeline:

  P0_modelo_cargado   -- tras construir RapidOCR, antes de tocar ninguna imagen
  P1_antes_decode      -- justo antes de LoadImage.__call__
  P2_tras_decode        -- justo despues (imagen ya en un array numpy, en CPU)
  P3_tras_resize        -- despues de RapidOCR.preprocess_img (el recorte a
                            <=2000 px de lado largo -- el "array que ve la red")
  P4_tras_det           -- despues de TextDetector.__call__ (la red de deteccion)
  P5_tras_crop          -- despues de RapidOCR.crop_text_regions (recortes CPU)
  P6_tras_cls           -- despues de TextClassifier.__call__
  P7_tras_rec           -- despues de TextRecognizer.__call__ (fin del pipeline)

UN solo proceso, UNA sola imagen, UNA sola llamada real (sin calentar con otra
imagen antes): es a proposito -- la pregunta es el coste de "tocar esta imagen
por primera vez en un proceso fresco", que es la metodologia ya establecida
del proyecto (ir directo, no en escalera -- trampa 67).

uso: n31_fases_child.py <ruta_png> <ruta_json_salida>
"""
import json
import os
import subprocess
import sys
import time

IMG = sys.argv[1]
OUT = sys.argv[2]


def vram_mib():
    r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits"],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=20)
    return int(r.stdout.strip().splitlines()[0])


fases = []


def marca(nombre):
    fases.append({"fase": nombre, "t": round(time.perf_counter(), 3),
                 "vram_mib": vram_mib()})


marca("P_muy_inicio")           # antes de importar torch/rapidocr -- la
                                 # misma convencion de "base_vram" que usa
                                 # bench/salidas-ocr-produccion/sidecar_op.py

import torch  # noqa: E402
os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR  # noqa: E402
from rapidocr.utils.load_image import LoadImage  # noqa: E402
from rapidocr.ch_ppocr_det.main import TextDetector  # noqa: E402
from rapidocr.ch_ppocr_cls.main import TextClassifier  # noqa: E402
from rapidocr.ch_ppocr_rec.main import TextRecognizer  # noqa: E402

marca("P_arranque_import")

# --- enganches, uno por fase, sobre las clases reales (no deducidos) --------
_orig_load = LoadImage.__call__


def _h_load(self, *a, **kw):
    marca("P1_antes_decode")
    r = _orig_load(self, *a, **kw)
    marca("P2_tras_decode")
    return r


LoadImage.__call__ = _h_load

_orig_pre = RapidOCR.preprocess_img


def _h_pre(self, *a, **kw):
    r = _orig_pre(self, *a, **kw)
    marca("P3_tras_resize")
    return r


RapidOCR.preprocess_img = _h_pre

_orig_det = TextDetector.__call__


def _h_det(self, *a, **kw):
    r = _orig_det(self, *a, **kw)
    marca("P4_tras_det")
    return r


TextDetector.__call__ = _h_det

_orig_crop = RapidOCR.crop_text_regions


def _h_crop(self, *a, **kw):
    r = _orig_crop(self, *a, **kw)
    marca("P5_tras_crop")
    return r


RapidOCR.crop_text_regions = _h_crop

_orig_cls = TextClassifier.__call__


def _h_cls(self, *a, **kw):
    r = _orig_cls(self, *a, **kw)
    marca("P6_tras_cls")
    return r


TextClassifier.__call__ = _h_cls

_orig_rec = TextRecognizer.__call__


def _h_rec(self, *a, **kw):
    r = _orig_rec(self, *a, **kw)
    marca("P7_tras_rec")
    return r


TextRecognizer.__call__ = _h_rec

# --- construccion del motor, identica a bench/salidas-ocr-produccion/sidecar_op.py
params = {
    "EngineConfig.onnxruntime.use_cuda": True,
    "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
    "Det.engine_type": EngineType.ONNXRUNTIME,
    "Cls.engine_type": EngineType.ONNXRUNTIME,
    "Rec.engine_type": EngineType.ONNXRUNTIME,
    "Det.lang_type": LangDet("ch"), "Rec.lang_type": LangRec("ch"),
    "Det.ocr_version": OCRVersion("PP-OCRv6"), "Rec.ocr_version": OCRVersion("PP-OCRv6"),
    "Det.model_type": ModelType("small"), "Rec.model_type": ModelType("small"),
    "Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225],
    "Det.thresh": 0.2, "Det.box_thresh": 0.45, "Det.unclip_ratio": 1.4,
    "Det.max_candidates": 3000,
}
lector = RapidOCR(params=params)
marca("P0_modelo_cargado")

providers = None
try:
    providers = list(lector.text_det.session.session.get_providers())
except Exception as ex:
    providers = f"{type(ex).__name__}: {ex}"

r = lector(IMG)
marca("P8_final_build_output")

resultado = {
    "img": os.path.basename(IMG),
    "providers": providers,
    "n_boxes": int(len(r.boxes)) if getattr(r, "boxes", None) is not None else 0,
    "fases": fases,
}
json.dump(resultado, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(resultado, ensure_ascii=False))
