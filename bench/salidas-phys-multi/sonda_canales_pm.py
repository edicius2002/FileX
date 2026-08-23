# -*- coding: utf-8 -*-
"""G4 / B19 — SONDA 3: por que `ruta` y `array` NO coinciden en color.

La tanda E midio que sobre un raster EN COLOR la via cambia la salida en dos de los
tres motores. Esta sonda separa las dos causas candidatas cambiando la variable, en
vez de deducirla del codigo:

  * ORDEN DE CANALES — `easyocr.utils.reformat_input` entrega al detector un array
    RGB cuando recibe una ruta (`imgproc.loadImage` usa `skimage.io.imread`) y el
    array TAL CUAL cuando recibe un ndarray, que documenta como BGR. Si la causa es
    esa, pasar el mismo fichero como array **RGB** tiene que reproducir la salida de
    la ruta byte a byte.
  * MODO PALETA — `rapidocr.utils.load_image.LoadImage.img_to_ndarray` solo trata el
    modo "1"; un PNG de paleta (`mode == "P"`) sale de `np.array(img)` como matriz de
    INDICES 2-D, y `convert_img` la convierte a BGR como si fuera gris. Si la causa
    es esa, el PNG truecolor tiene que coincidir con el array y el de paleta no.

uso: python sonda_canales_pm.py <easyocr|rapidocr|paddleocr> <cpu|cuda> <png> [png...]
"""
import hashlib
import json
import os
import sys

import cv2
import numpy as np

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-phys-multi")
JSN = os.path.join(BASE, "json")
sys.path.insert(0, BASE)
from ocr_eval_pm import evaluar  # noqa: E402

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
pngs = sys.argv[3:]
gpu = dispositivo == "cuda"

if motor == "rapidocr":
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    lector = RapidOCR(params={
        "EngineConfig.onnxruntime.use_cuda": gpu,
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": LangDet.CH, "Rec.lang_type": LangRec.CH,
        "Det.ocr_version": OCRVersion("PP-OCRv6"),
        "Rec.ocr_version": OCRVersion("PP-OCRv6"),
        "Det.model_type": ModelType("small"), "Rec.model_type": ModelType("small"),
        "Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225],
        "Det.thresh": 0.2, "Det.box_thresh": 0.45, "Det.unclip_ratio": 1.4,
        "Det.max_candidates": 3000})

    def leer(x):
        r = lector(x)
        return " ".join(r.txts) if r and r.txts else ""

elif motor == "paddleocr":
    from paddleocr import PaddleOCR
    lector = PaddleOCR(device="gpu:0" if gpu else "cpu",
                       use_doc_orientation_classify=False,
                       use_doc_unwarping=False, use_textline_orientation=True)

    def leer(x):
        out = []
        for p in lector.predict(x):
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            out.extend(d.get("rec_texts", []))
        return " ".join(out)

else:
    import easyocr
    lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)

    def leer(x):
        return " ".join(lector.readtext(x, detail=0, paragraph=False))


def h(t):
    return hashlib.md5(t.encode("utf-8")).hexdigest()


res = {}
for p in pngs:
    nom = os.path.basename(p)
    bgr = cv2.imread(p, cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gris = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    entradas = {"ruta": p, "array_bgr": bgr, "array_rgb": rgb, "array_gris": gris}
    fila = {}
    for etq, ent in entradas.items():
        try:
            t = leer(ent)
            fila[etq] = {"chars": len(t), "md5": h(t), "error": None,
                         "cer_acentos_pct": evaluar(t, "d4")["cer_acentos_pct"]}
        except Exception as ex:
            fila[etq] = {"chars": 0, "md5": None, "cer_acentos_pct": None,
                         "error": f"{type(ex).__name__}: {str(ex)[:150]}"}
    fila["_md5_array_bgr"] = hashlib.md5(
        np.ascontiguousarray(bgr).tobytes()).hexdigest()
    fila["iguales_a_ruta"] = [k for k in ("array_bgr", "array_rgb", "array_gris")
                              if fila[k]["md5"] == fila["ruta"]["md5"]]
    res[nom] = fila
    print(f"--- {nom} ---")
    for k in ("ruta", "array_bgr", "array_rgb", "array_gris"):
        c = fila[k]["cer_acentos_pct"]
        print(f"   {k:11s} CER={('%.2f' % c) if c is not None else '  -  ':>7s} "
              f"chars={fila[k]['chars']:5d} md5={str(fila[k]['md5'])[:10]} "
              f"{fila[k]['error'] or ''}")
    print(f"   iguales a `ruta`: {fila['iguales_a_ruta']}")
    sys.stdout.flush()

dst = os.path.join(JSN, f"sonda_canales_{motor}_{dispositivo}.json")
json.dump({"motor": motor, "dispositivo": dispositivo, "res": res},
          open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"-> {dst}")
