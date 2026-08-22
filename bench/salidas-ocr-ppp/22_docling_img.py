# -*- coding: utf-8 -*-
"""G1 / paso 2c — la celda que falta de docling: la via "imagen extraida".

Docling rasteriza el PDF por su cuenta, asi que la via B (imagen incrustada sin
rasterizar) no se puede expresar como un valor de `scale`. Se expresa entrando por
`InputFormat.IMAGE` con el PNG ya extraido y `scale=1.0`, que hace que el array que
llega al motor sea pixel a pixel el del JPEG incrustado. La SONDA lo comprueba: si el
tamano que registra no coincide con el del PNG, esta celda no vale y se dice.

uso: python 22_docling_img.py <cpu|cuda> <backend>
env: REPS
"""
import glob
import json
import os
import statistics
import subprocess
import sys
import threading
import time

RAIZ = r"D:\Work\research\FileX"
IMG = os.path.join(RAIZ, r"bench\salidas-ocr-ppp\img")
OUT = os.path.join(RAIZ, r"bench\salidas-ocr-ppp\texto")
JSN = os.path.join(RAIZ, r"bench\salidas-ocr-ppp\json")
sys.path.insert(0, os.path.join(RAIZ, r"bench\scripts"))
from ocr_eval import evaluar  # noqa: E402

import torch  # noqa: E402
_tl = os.path.join(os.path.dirname(torch.__file__), "lib")
if os.path.isdir(_tl):
    os.add_dll_directory(_tl)

dispositivo = sys.argv[1] if len(sys.argv) > 1 else "cuda"
backend = sys.argv[2] if len(sys.argv) > 2 else "torch"
REPS = int(os.environ.get("REPS", "9"))
gpu = dispositivo == "cuda"


def vram():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True).stdout.strip().splitlines()[0])
    except Exception:
        return -1


def util():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True).stdout.strip().splitlines()[0])
    except Exception:
        return -1


class Muestreador(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.pico = 0
        self.pico_util = 0
        self.vivo = True

    def run(self):
        while self.vivo:
            self.pico = max(self.pico, vram())
            self.pico_util = max(self.pico_util, util())
            time.sleep(0.1)


quiet = 0
for _ in range(5):
    quiet = max(quiet, util())
    time.sleep(1)
base_vram = vram()
flag = "limpia" if quiet < 10 else f"SUCIA(pico {quiet}%)"

SONDA = {"tam": [], "activa": False}
try:
    from rapidocr import RapidOCR as _RO
    _orig = _RO.__call__

    def _sonda(self, img, *a, **k):
        sh = getattr(img, "shape", None)
        if sh is not None:
            SONDA["tam"].append((int(sh[1]), int(sh[0])))
        return _orig(self, img, *a, **k)

    _RO.__call__ = _sonda
    SONDA["activa"] = True
except Exception as ex:
    SONDA["error"] = f"{type(ex).__name__}: {ex}"

from PIL import Image  # noqa: E402
from docling.datamodel.base_models import InputFormat  # noqa: E402
from docling.datamodel.pipeline_options import (  # noqa: E402
    AcceleratorDevice, AcceleratorOptions, PdfPipelineOptions, RapidOcrOptions)
from docling.document_converter import (  # noqa: E402
    DocumentConverter, ImageFormatOption)

po = PdfPipelineOptions()
po.accelerator_options = AcceleratorOptions(
    num_threads=8, device=AcceleratorDevice.CUDA if gpu else AcceleratorDevice.CPU)
po.do_ocr = True
po.do_table_structure = False
oo = RapidOcrOptions(lang=["english"], backend=backend, force_full_page_ocr=True)
oo.scale = 1.0                      # 1 px de la imagen = 1 px al motor
po.ocr_options = oo
conv = DocumentConverter(
    format_options={InputFormat.IMAGE: ImageFormatOption(pipeline_options=po)})

cab = {"dispositivo": dispositivo, "backend": backend, "escala": 1.0,
       "via": "imagen incrustada extraida (InputFormat.IMAGE)",
       "reps": REPS, "vram_base_MiB": base_vram, "quietud_pct": quiet, "flag": flag}
print(json.dumps(cab, ensure_ascii=False), flush=True)

mu = Muestreador()
mu.start()
res = {}
for ruta in sorted(glob.glob(os.path.join(IMG, "ext*__*.png"))):
    nom = os.path.splitext(os.path.basename(ruta))[0]
    px_png = Image.open(ruta).size
    SONDA["tam"] = []
    pico_ini = mu.pico
    try:
        texto = conv.convert(ruta).document.export_to_markdown()
    except Exception as ex:
        res[nom] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
        print(f"{nom:34s} ERROR {type(ex).__name__}: {str(ex)[:90]}", flush=True)
        continue
    tam_real = SONDA["tam"][0] if SONDA["tam"] else None
    ts = []
    for _ in range(REPS):
        t = time.time()
        texto = conv.convert(ruta).document.export_to_markdown()
        ts.append((time.time() - t) * 1000)
    s = sorted(ts)
    ev = evaluar(texto)
    etiqueta = f"doclingimg_{backend}_{dispositivo}"
    open(os.path.join(OUT, f"{etiqueta}__{nom}.txt"), "w",
         encoding="utf-8").write(texto)
    res[nom] = {"px_png": list(px_png), "px_reales_al_motor": tam_real,
                "sin_reescalado": (tam_real == tuple(px_png)) if tam_real else None,
                "cer_pct": ev["cer_pct"], "dist_global": ev["dist_global"],
                "frases_exactas": ev["frases_exactas"],
                "normalizada": ev["normalizada"],
                "ms_mediana": round(statistics.median(s), 1),
                "ms_min": round(s[0], 1), "ms_max": round(s[-1], 1), "n": len(s),
                "vram_pico_MiB": mu.pico, "vram_delta_MiB": mu.pico - pico_ini}
    print(f"{nom:34s} png={px_png} motor={tam_real} "
          f"{'OK' if tam_real == tuple(px_png) else 'REESCALADO!'}  "
          f"CER={ev['cer_pct']:6.1f}%  dist={ev['dist_global']:4d}  "
          f"{statistics.median(s):8.1f} ms", flush=True)

mu.vivo = False
mu.join(timeout=2)
fin = {"evento": "fin", "vram_pico_MiB": mu.pico, "vram_base_MiB": base_vram,
       "coste_propio_MiB": mu.pico - base_vram, "pico_util_pct": mu.pico_util,
       "sonda_activa": SONDA["activa"]}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"doclingimg_{backend}_{dispositivo}__cer.json"),
               "w", encoding="utf-8"), ensure_ascii=False, indent=2)
