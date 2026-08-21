# -*- coding: utf-8 -*-
"""FASE 3: pasa por RapidOCR / PaddleOCR las imagenes producidas por OCRmyPDF
(y los controles de re-rasterizacion de la fase 4) y mide CER contra la referencia.

Reutiliza EXACTAMENTE la configuracion de motor de bench/scripts/ocr_motor.py y la
metrica de bench/scripts/ocr_eval.py, para que las cifras sean comparables con las
marcas de la fase 2. No instala nada: solo usa los venv existentes.

uso:  python 30_ocr_cadena.py <rapidocr|paddleocr> <cpu|cuda> [patron]
env:  REPS (repeticiones para la medicion de velocidad, por defecto 9)
"""
import glob
import json
import os
import statistics
import subprocess
import sys
import time

RAIZ = r"D:\Work\research\FileX"
IMG = os.environ.get("IMGDIR", os.path.join(RAIZ, r"bench\salidas-ocrmypdf\img"))
OUT = os.path.join(RAIZ, r"bench\salidas-ocrmypdf\texto")
sys.path.insert(0, os.path.join(RAIZ, r"bench\scripts"))
from ocr_eval import evaluar  # noqa: E402  (metrica comun del proyecto)

os.makedirs(OUT, exist_ok=True)
motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
patron = sys.argv[3] if len(sys.argv) > 3 else "*.png"
REPS = int(os.environ.get("REPS", "9"))
gpu = dispositivo == "cuda"
etiqueta = f"{motor}_{dispositivo}" + os.environ.get("SUFIJO", "")


def vram():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True).stdout.strip().splitlines()[0])
    except Exception:
        return -1


base_vram = vram()
t0 = time.time()

if motor == "rapidocr":
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    params = {
        "EngineConfig.onnxruntime.use_cuda": gpu,
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": LangDet.CH,
        "Rec.lang_type": LangRec.CH,
        "Det.ocr_version": OCRVersion.PPOCRV5,
        "Rec.ocr_version": OCRVersion.PPOCRV5,
        "Det.model_type": ModelType.MOBILE,
        "Rec.model_type": ModelType.MOBILE,
    }
    lector = RapidOCR(params=params)

    def leer(ruta):
        r = lector(ruta)
        return " ".join(r.txts) if r and r.txts else ""

elif motor == "paddleocr":
    import paddle  # noqa: F401
    from paddleocr import PaddleOCR
    lector = PaddleOCR(lang="es", device="gpu:0" if gpu else "cpu",
                       use_doc_orientation_classify=False,
                       use_doc_unwarping=False,
                       use_textline_orientation=True)

    def leer(ruta):
        r = lector.predict(ruta)
        out = []
        for p in r:
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            out.extend(d.get("rec_texts", []))
        return " ".join(out)
else:
    raise SystemExit(f"motor desconocido: {motor}")

carga_frio = round(time.time() - t0, 2)
print(json.dumps({"etiqueta": etiqueta, "carga_s": carga_frio,
                  "vram_base_MiB": base_vram, "vram_tras_carga_MiB": vram()},
                 ensure_ascii=False), flush=True)

rutas = sorted(glob.glob(os.path.join(IMG, patron)))
res = {}
pico = vram()
for ruta in rutas:
    nom = os.path.splitext(os.path.basename(ruta))[0]
    try:
        texto = leer(ruta)
    except Exception as ex:
        res[nom] = {"error": f"{type(ex).__name__}: {ex}"}
        print(f"{nom:44s} ERROR {type(ex).__name__}", flush=True)
        continue
    v = vram()
    pico = max(pico, v)
    open(os.path.join(OUT, f"{etiqueta}__{nom}.txt"), "w", encoding="utf-8").write(texto)
    ev = evaluar(texto)
    res[nom] = {"cer_pct": ev["cer_pct"], "dist_global": ev["dist_global"],
                "frases_exactas": ev["frases_exactas"], "chars": ev["chars_salida"],
                "normalizada": ev["normalizada"]}
    print(f"{nom:44s} CER={ev['cer_pct']:6.1f}%  dist={ev['dist_global']:4d}  "
          f"frases={ev['frases_exactas']}/3", flush=True)

json.dump({"motor": motor, "dispositivo": dispositivo, "carga_frio_s": carga_frio,
           "vram_base_MiB": base_vram, "vram_pico_MiB": pico, "res": res},
          open(os.path.join(OUT, f"{etiqueta}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps({"evento": "fin", "vram_pico_MiB": pico,
                  "coste_propio_MiB": pico - base_vram}, ensure_ascii=False))
