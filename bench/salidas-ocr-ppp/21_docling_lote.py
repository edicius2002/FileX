# -*- coding: utf-8 -*-
"""G1 / paso 2b — docling + RapidOCR backend="torch" (la ruta que el plan de FileX
da por buena) sobre los PDF ORIGINALES, variando los ppp de rasterizacion.

Aqui no vale pasarle PNG ya rasterizados: docling rasteriza el PDF por su cuenta y
el parametro que decide a cuantos ppp lo hace es `OcrOptions.scale`, cuyo valor por
defecto es 3.0 -> 72 x 3 = 216 ppp. Ese es el numero que hay que auditar, porque es
lo que FileX heredaria sin tocar nada.

Lleva una SONDA que registra el tamano en pixeles del array que llega de verdad al
motor de OCR. Sin ella, "ppp" es una suposicion sobre el valor de un parametro; con
ella es una medida.

uso: python 21_docling_lote.py <cpu|cuda> <backend> <ppp[,ppp...]|defecto> [docs]
env: REPS (por defecto 9)
"""
import json
import os
import statistics
import subprocess
import sys
import threading
import time

RAIZ = r"D:\Work\research\FileX"
C = os.path.join(RAIZ, r"corpus\pdf")
OUT = os.path.join(RAIZ, r"bench\salidas-ocr-ppp\texto")
JSN = os.path.join(RAIZ, r"bench\salidas-ocr-ppp\json")
sys.path.insert(0, os.path.join(RAIZ, r"bench\scripts"))
from ocr_eval import evaluar  # noqa: E402

os.makedirs(OUT, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

# onnxruntime-gpu en Windows necesita las DLL de CUDA que trae torch (ver gpu-fase2 §A.2)
import torch  # noqa: E402
_tl = os.path.join(os.path.dirname(torch.__file__), "lib")
if os.path.isdir(_tl):
    os.add_dll_directory(_tl)

dispositivo = sys.argv[1] if len(sys.argv) > 1 else "cuda"
backend = sys.argv[2] if len(sys.argv) > 2 else "torch"
ppps = sys.argv[3] if len(sys.argv) > 3 else "defecto"
DOCS = (sys.argv[4] if len(sys.argv) > 4 else
        "patologico_escaneado,escaneado_d1,escaneado_d2,escaneado_d3").split(",")
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
            v = vram()
            if v > self.pico:
                self.pico = v
            u = util()
            if u > self.pico_util:
                self.pico_util = u
            time.sleep(0.1)


quiet = 0
for _ in range(5):
    quiet = max(quiet, util())
    time.sleep(1)
base_vram = vram()
flag = "limpia" if quiet < 10 else f"SUCIA(pico {quiet}%)"

# ---------------------------------------------------------------- SONDA
# Registra el tamano real del array que entra al motor de OCR. rapidocr expone
# RapidOCR.__call__; se envuelve antes de construir el convertidor.
SONDA = {"tam": []}
try:
    from rapidocr import RapidOCR as _RO
    _orig_call = _RO.__call__

    def _sonda_call(self, img, *a, **k):
        try:
            sh = getattr(img, "shape", None)
            if sh is not None:
                SONDA["tam"].append((int(sh[1]), int(sh[0])))
        except Exception:
            pass
        return _orig_call(self, img, *a, **k)

    _RO.__call__ = _sonda_call
    SONDA["activa"] = True
except Exception as ex:
    SONDA["activa"] = False
    SONDA["error"] = f"{type(ex).__name__}: {ex}"

from docling.datamodel.base_models import InputFormat  # noqa: E402
from docling.datamodel.pipeline_options import (  # noqa: E402
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption  # noqa: E402

# --- fase 3: que backbone PP-OCR resuelve docling para este (lang, backend) ---
info_modelo = {}
try:
    from docling.models.stages.ocr.rapid_ocr_model import (
        _RAPIDOCR_MODEL_TYPE, _RAPIDOCR_V4V5_MODEL_TYPE, _resolve_rapidocr)
    spec = _resolve_rapidocr("english", backend)
    info_modelo = {
        "lang_pedido": "english",
        "lang_resuelto": spec.rapidocr_lang_token,
        "ppocr_version": str(getattr(spec.ppocr_version, "value", spec.ppocr_version)),
        "model_type_v6": _RAPIDOCR_MODEL_TYPE,
        "model_type_v4v5": _RAPIDOCR_V4V5_MODEL_TYPE,
    }
except Exception as ex:
    info_modelo = {"error": f"{type(ex).__name__}: {ex}"}

lista_ppp = [None] if ppps == "defecto" else [int(x) for x in ppps.split(",")]

cab = {"dispositivo": dispositivo, "backend": backend, "docs": DOCS,
       "ppp": ppps, "reps": REPS, "vram_base_MiB": base_vram,
       "quietud_pct": quiet, "flag": flag, "torch": torch.__version__,
       "torch_cuda": torch.cuda.is_available(), "modelo": info_modelo}
print(json.dumps(cab, ensure_ascii=False), flush=True)

mu = Muestreador()
mu.start()
res = {}

for ppp in lista_ppp:
    po = PdfPipelineOptions()
    po.accelerator_options = AcceleratorOptions(
        num_threads=8,
        device=AcceleratorDevice.CUDA if gpu else AcceleratorDevice.CPU)
    po.do_ocr = True
    po.do_table_structure = False
    oo = RapidOcrOptions(lang=["english"], backend=backend, force_full_page_ocr=True)
    if ppp is not None:
        oo.scale = ppp / 72.0
    po.ocr_options = oo
    escala = oo.scale
    ppp_efectivo = round(escala * 72, 1)
    etiq_ppp = "defecto" if ppp is None else str(ppp)

    t0 = time.time()
    conv = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po)})
    constr = round(time.time() - t0, 2)

    for d in DOCS:
        ruta = os.path.join(C, d + ".pdf")
        if not os.path.exists(ruta):
            continue
        clave = f"ppp{etiq_ppp}__{d}"
        pico_ini = mu.pico
        SONDA["tam"] = []
        try:
            r = conv.convert(ruta)
            texto = r.document.export_to_markdown()
        except Exception as ex:
            res[clave] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
            print(f"{clave:34s} ERROR {type(ex).__name__}: {str(ex)[:80]}", flush=True)
            continue
        tam_real = SONDA["tam"][0] if SONDA["tam"] else None
        ts, textos = [], set()
        for _ in range(REPS):
            t = time.time()
            texto = conv.convert(ruta).document.export_to_markdown()
            ts.append((time.time() - t) * 1000)
            textos.add(texto)
        s = sorted(ts)
        ev = evaluar(texto)
        etiqueta = f"docling_{backend}_{dispositivo}"
        open(os.path.join(OUT, f"{etiqueta}__{clave}.txt"), "w",
             encoding="utf-8").write(texto)
        res[clave] = {
            "ppp_param": ppp, "escala": round(escala, 4),
            "ppp_efectivo_param": ppp_efectivo,
            "px_reales_al_motor": tam_real,
            "cer_pct": ev["cer_pct"], "dist_global": ev["dist_global"],
            "frases_exactas": ev["frases_exactas"], "chars": ev["chars_salida"],
            "normalizada": ev["normalizada"],
            "ms_mediana": round(statistics.median(s), 1),
            "ms_min": round(s[0], 1), "ms_max": round(s[-1], 1), "n": len(s),
            "determinista": len(textos) == 1,
            "constructor_s": constr,
            "vram_pico_MiB": mu.pico, "vram_delta_MiB": mu.pico - pico_ini,
        }
        print(f"{clave:34s} escala={escala:.3f} (~{ppp_efectivo:.0f}ppp) "
              f"px_motor={tam_real}  CER={ev['cer_pct']:6.1f}%  "
              f"dist={ev['dist_global']:4d}  {statistics.median(s):8.1f} ms",
              flush=True)

mu.vivo = False
mu.join(timeout=2)
fin = {"evento": "fin", "vram_pico_MiB": mu.pico, "vram_base_MiB": base_vram,
       "coste_propio_MiB": mu.pico - base_vram, "pico_util_pct": mu.pico_util,
       "sonda_activa": SONDA.get("activa")}
print(json.dumps(fin, ensure_ascii=False), flush=True)
suf = os.environ.get("SUFIJO", "")
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"docling_{backend}_{dispositivo}{suf}__cer.json"),
               "w", encoding="utf-8"), ensure_ascii=False, indent=2)
