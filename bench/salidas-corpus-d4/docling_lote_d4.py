# -*- coding: utf-8 -*-
"""G1 / docling + RapidOCR sobre los PDF, con `OcrOptions.scale` SIEMPRE explicito.

COPIA ADAPTADA de bench/salidas-ocr-ppp/21_docling_lote.py. El original no se toca.

Cambios: metrica doble (con y sin acentos), `lang` configurable, y la escala se
calcula por documento a partir de sus ppp NATIVOS (regla R1) en vez de fijarse a
mano; el defecto de docling (scale=3.0 -> 216 ppp) solo se usa si se pide
explicitamente con ppp='defecto', y entonces se etiqueta como tal.

uso: python docling_lote_d4.py <cpu|cuda> <backend> <ppp|nativo|defecto> <doc,doc,...>
env: REPS(9) SUFIJO DL_LANG(english) SIN_MUESTREO
"""
import json
import os
import statistics
import subprocess
import sys
import threading
import time

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-corpus-d4")
C = os.path.join(RAIZ, r"corpus\pdf")
TMP = os.path.join(BASE, "tmp")
OUT = os.path.join(BASE, "texto")
JSN = os.path.join(BASE, "json")
sys.path.insert(0, BASE)
from ocr_eval_d4 import evaluar  # noqa: E402

os.makedirs(OUT, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

import torch  # noqa: E402
_tl = os.path.join(os.path.dirname(torch.__file__), "lib")
if os.path.isdir(_tl):
    os.add_dll_directory(_tl)

dispositivo = sys.argv[1] if len(sys.argv) > 1 else "cuda"
backend = sys.argv[2] if len(sys.argv) > 2 else "torch"
modo_ppp = sys.argv[3] if len(sys.argv) > 3 else "nativo"
DOCS = (sys.argv[4] if len(sys.argv) > 4 else "escaneado_d4d").split(",")
REPS = int(os.environ.get("REPS", "9"))
LANG = os.environ.get("DL_LANG", "english")
gpu = dispositivo == "cuda"
SIN_MUESTREO = os.environ.get("SIN_MUESTREO") == "1"


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
    def __init__(self, activo=True):
        super().__init__(daemon=True)
        self.pico = 0
        self.pico_util = 0
        self.vivo = activo
        self.activo = activo

    def run(self):
        while self.vivo:
            v = vram()
            if v > self.pico:
                self.pico = v
            u = util()
            if u > self.pico_util:
                self.pico_util = u
            time.sleep(0.1)


def ppp_nativos(ruta):
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(ruta)
    p = d[0]
    w_pt, _h = p.get_size()
    mejor = 0
    for obj in p.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)):
        try:
            m = obj.get_metadata()
            mejor = max(mejor, m.width)
        except Exception:
            pass
    d.close()
    return round(mejor / (w_pt / 72.0), 1) if mejor else None


quiet = 0
for _ in range(5):
    quiet = max(quiet, util())
    time.sleep(1)
base_vram = vram()
flag = "limpia" if quiet < 10 else f"SUCIA(pico {quiet}%)"

# --- SONDA: tamaño real del array que entra al motor. Sin ella "ppp" es una
# suposicion sobre un parametro; con ella es una medida. ---
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
    AcceleratorDevice, AcceleratorOptions, PdfPipelineOptions, RapidOcrOptions)
from docling.document_converter import DocumentConverter, PdfFormatOption  # noqa: E402

info_modelo = {}
try:
    from docling.models.stages.ocr.rapid_ocr_model import (
        _RAPIDOCR_MODEL_TYPE, _RAPIDOCR_V4V5_MODEL_TYPE, _resolve_rapidocr)
    spec = _resolve_rapidocr(LANG, backend)
    info_modelo = {"lang_pedido": LANG,
                   "lang_resuelto": str(spec.rapidocr_lang_token),
                   "ppocr_version": str(getattr(spec.ppocr_version, "value",
                                                spec.ppocr_version)),
                   "model_type_v6": _RAPIDOCR_MODEL_TYPE,
                   "model_type_v4v5": _RAPIDOCR_V4V5_MODEL_TYPE}
except Exception as ex:
    info_modelo = {"error": f"{type(ex).__name__}: {ex}"}

etiqueta = f"docling_{backend}_{dispositivo}" + os.environ.get("SUFIJO", "")
cab = {"etiqueta": etiqueta, "dispositivo": dispositivo, "backend": backend,
       "lang": LANG, "docs": DOCS, "modo_ppp": modo_ppp, "reps": REPS,
       "vram_base_MiB": base_vram, "quietud_pct": quiet, "flag": flag,
       "torch": torch.__version__, "torch_cuda": torch.cuda.is_available(),
       "modelo": info_modelo, "muestreo_vram": not SIN_MUESTREO}
print(json.dumps(cab, ensure_ascii=False), flush=True)

mu = Muestreador(activo=not SIN_MUESTREO)
if not SIN_MUESTREO:
    mu.start()
res = {}

for d in DOCS:
    ruta = os.path.join(C, d + ".pdf")
    if not os.path.exists(ruta):
        ruta = os.path.join(TMP, d + ".pdf")
    if not os.path.exists(ruta):
        print(f"{d}: no existe", flush=True)
        continue
    nat = ppp_nativos(ruta)
    if modo_ppp == "nativo":
        # R1: clamp(nativos, 100, nativos*1,4). Aqui no se sube, asi que = nativos.
        ppp = max(100, min(nat, nat * 1.4))
    elif modo_ppp == "defecto":
        ppp = None
    else:
        ppp = float(modo_ppp)

    po = PdfPipelineOptions()
    po.accelerator_options = AcceleratorOptions(
        num_threads=8,
        device=AcceleratorDevice.CUDA if gpu else AcceleratorDevice.CPU)
    po.do_ocr = True
    po.do_table_structure = False
    oo = RapidOcrOptions(lang=[LANG], backend=backend, force_full_page_ocr=True)
    if ppp is not None:
        oo.scale = ppp / 72.0
    po.ocr_options = oo
    escala = oo.scale
    ppp_efectivo = round(escala * 72, 1)

    t0 = time.time()
    conv = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po)})
    constr = round(time.time() - t0, 2)

    clave = f"{'nativo' if modo_ppp == 'nativo' else modo_ppp}__{d}"
    SONDA["tam"] = []
    pico_ini = mu.pico
    try:
        texto = conv.convert(ruta).document.export_to_markdown()
    except Exception as ex:
        res[clave] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
        print(f"{clave:40s} ERROR {type(ex).__name__}: {str(ex)[:80]}", flush=True)
        continue
    tam_real = SONDA["tam"][0] if SONDA["tam"] else None
    ts, textos = [], set()
    for _ in range(REPS):
        t = time.time()
        texto = conv.convert(ruta).document.export_to_markdown()
        ts.append((time.time() - t) * 1000)
        textos.add(texto)
    s = sorted(ts)
    ref = "legado" if ("d4" not in d) else "d4"
    ev = evaluar(texto, ref)
    open(os.path.join(OUT, f"{etiqueta}__{clave}.txt"), "w",
         encoding="utf-8").write(texto)
    res[clave] = {
        "referencia": ref, "ppp_nativos": nat, "escala": round(escala, 4),
        "ppp_efectivo_param": ppp_efectivo, "px_reales_al_motor": tam_real,
        "cer_acentos_pct": ev["cer_acentos_pct"], "dist_acentos": ev["dist_acentos"],
        "cer_ascii_pct": ev["cer_ascii_pct"], "dist_ascii": ev["dist_ascii"],
        "chars": ev["chars_salida"], "lineas_exactas": ev["lineas_exactas"],
        "lineas_totales": ev["lineas_totales"],
        "acentos_ref": ev["acentos_ref"], "acentos_salida": ev["acentos_salida"],
        "bloques": {k: (v or {}).get("cer_pct") for k, v in ev["bloques"].items()},
        "normalizada_acentos": ev["normalizada_acentos"],
        "ms_mediana": round(statistics.median(s), 1), "ms_min": round(s[0], 1),
        "ms_max": round(s[-1], 1), "n": len(s),
        "determinista": len(textos) == 1, "constructor_s": constr,
        "vram_pico_MiB": mu.pico, "vram_delta_MiB": mu.pico - pico_ini,
    }
    print(f"{clave:40s} nat={nat} escala={escala:.3f} (~{ppp_efectivo:.0f}ppp) "
          f"px={tam_real}  CERac={ev['cer_acentos_pct']:6.2f}%  "
          f"CERascii={ev['cer_ascii_pct']:6.2f}%  "
          f"lin={ev['lineas_exactas']}/{ev['lineas_totales']}  "
          f"bloques={res[clave]['bloques']}  {statistics.median(s):8.1f} ms",
          flush=True)

mu.vivo = False
if not SIN_MUESTREO:
    mu.join(timeout=2)
fin = {"evento": "fin", "vram_pico_MiB": mu.pico, "vram_base_MiB": base_vram,
       "coste_propio_MiB": mu.pico - base_vram, "pico_util_pct": mu.pico_util,
       "sonda_activa": SONDA.get("activa"), "muestreo_vram": not SIN_MUESTREO}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"{etiqueta}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
