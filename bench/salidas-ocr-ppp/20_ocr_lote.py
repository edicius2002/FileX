# -*- coding: utf-8 -*-
"""G1 / paso 2 — banco de motores de OCR aislados sobre la matriz de imagenes.

Reutiliza la configuracion de motor de `bench/scripts/ocr_motor.py` y la metrica de
`bench/scripts/ocr_eval.py` SIN TOCARLAS, para que la via "200 ppp" reproduzca las
marcas de `bench/gpu-fase2.md` §5 y sirva de control de fidelidad de la cadena.

Lo unico que cambia respecto a la fase 2 es la imagen de entrada.

uso: python 20_ocr_lote.py <rapidocr|paddleocr|easyocr> <cpu|cuda> [glob]
env: REPS (por defecto 9), SUFIJO, IMGDIR
"""
import glob as _glob
import json
import os
import statistics
import subprocess
import sys
import threading
import time

RAIZ = r"D:\Work\research\FileX"
IMG = os.environ.get("IMGDIR", os.path.join(RAIZ, r"bench\salidas-ocr-ppp\img"))
OUT = os.path.join(RAIZ, r"bench\salidas-ocr-ppp\texto")
JSN = os.path.join(RAIZ, r"bench\salidas-ocr-ppp\json")
sys.path.insert(0, os.path.join(RAIZ, r"bench\scripts"))
from ocr_eval import evaluar  # noqa: E402

os.makedirs(OUT, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
patron = sys.argv[3] if len(sys.argv) > 3 else "*.png"
REPS = int(os.environ.get("REPS", "9"))
gpu = dispositivo == "cuda"
etiqueta = f"{motor}_{dispositivo}" + os.environ.get("SUFIJO", "")


# ------------------------------------------------------------------ VRAM
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
    """Muestrea la VRAM total de la tarjeta cada 100 ms mientras corre el lote.
    nvidia-smi da el total de la tarjeta, no el del proceso: por eso se resta la
    linea base del escritorio para obtener el 'coste propio'.

    OJO: cada muestra lanza un proceso nvidia-smi, y eso roba CPU al motor. Medido:
    infla las medianas de tiempo entre un 30 y un 60 %. Por eso hay una segunda
    pasada con SIN_MUESTREO=1 que da los tiempos buenos y renuncia al pico de VRAM.
    Una sola pasada no puede dar las dos cosas bien."""
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


# --- linea base y quietud de la GPU ANTES de cargar nada (arnes del proyecto) ---
quiet = 0
for _ in range(5):
    quiet = max(quiet, util())
    time.sleep(1)
base_vram = vram()
flag = "limpia" if quiet < 10 else f"SUCIA(pico {quiet}%)"

# Dos pasadas incompatibles: o pico de VRAM o tiempos limpios (ver Muestreador).
SIN_MUESTREO = os.environ.get("SIN_MUESTREO") == "1"

# ------------------------------------------------------------------ carga
t0 = time.time()
modelos = {}

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
    # --- fase 3: que checkpoint se cargo DE VERDAD (no la etiqueta, el fichero) ---
    for tarea in ("text_det", "text_cls", "text_rec"):
        o = getattr(lector, tarea, None)
        ses = getattr(o, "session", None)
        mi = getattr(ses, "model_info", None) or getattr(o, "model_info", None)
        if mi is not None:
            modelos[tarea] = os.path.basename(str(getattr(mi, "model_path", mi)))
        else:
            modelos[tarea] = "?"
    modelos["params_forzados"] = "PPOCRV5/MOBILE/ONNXRUNTIME (igual que bench/scripts/ocr_motor.py)"

    def leer(ruta):
        r = lector(ruta)
        return " ".join(r.txts) if r and r.txts else ""

elif motor == "paddleocr":
    import paddle
    from paddleocr import PaddleOCR
    lector = PaddleOCR(lang="es", device="gpu:0" if gpu else "cpu",
                       use_doc_orientation_classify=False,
                       use_doc_unwarping=False,
                       use_textline_orientation=True)
    modelos["paddle"] = paddle.__version__
    modelos["paddle_cudnn_aviso"] = "compilado con cuDNN 9.9, maquina 9.5 (aviso de paddle)"
    try:
        modelos["nombres_modelo"] = lector._get_ocr_model_names()
    except Exception as ex:
        modelos["nombres_modelo"] = f"ERROR {type(ex).__name__}: {ex}"
    try:
        cfg = lector._params
        modelos["params"] = {k: str(v) for k, v in dict(cfg).items()
                             if "model" in k or "lang" in k}
    except Exception:
        pass

    def leer(ruta):
        r = lector.predict(ruta)
        out = []
        for p in r:
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            out.extend(d.get("rec_texts", []))
        return " ".join(out)

elif motor == "easyocr":
    import easyocr
    import torch
    lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)
    modelos["torch"] = torch.__version__
    modelos["torch_cuda"] = str(torch.cuda.is_available())

    def leer(ruta):
        return " ".join(lector.readtext(ruta, detail=0, paragraph=False))

else:
    raise SystemExit(f"motor desconocido: {motor}")

carga = round(time.time() - t0, 2)
tras_carga = vram()
cab = {"etiqueta": etiqueta, "motor": motor, "dispositivo": dispositivo,
       "carga_frio_s": carga, "vram_base_MiB": base_vram,
       "vram_tras_carga_MiB": tras_carga, "quietud_pct": quiet, "flag": flag,
       "modelos": modelos, "reps": REPS,
       "muestreo_vram": not SIN_MUESTREO}
print(json.dumps(cab, ensure_ascii=False), flush=True)

# ------------------------------------------------------------------ medicion
rutas = sorted(_glob.glob(os.path.join(IMG, patron)))
res = {}
mu = Muestreador(activo=not SIN_MUESTREO)
mu.pico = tras_carga
if not SIN_MUESTREO:
    mu.start()

for ruta in rutas:
    nom = os.path.splitext(os.path.basename(ruta))[0]
    pico_ini = mu.pico
    try:
        texto = leer(ruta)              # calentamiento, fuera de la medicion
    except Exception as ex:
        res[nom] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
        print(f"{nom:36s} ERROR {type(ex).__name__}: {str(ex)[:80]}", flush=True)
        continue
    ts, textos = [], set()
    for _ in range(REPS):
        t = time.time()
        texto = leer(ruta)
        ts.append((time.time() - t) * 1000)
        textos.add(texto)
    s = sorted(ts)
    ev = evaluar(texto)
    open(os.path.join(OUT, f"{etiqueta}__{nom}.txt"), "w",
         encoding="utf-8").write(texto)
    res[nom] = {
        "cer_pct": ev["cer_pct"], "dist_global": ev["dist_global"],
        "frases_exactas": ev["frases_exactas"], "chars": ev["chars_salida"],
        "normalizada": ev["normalizada"],
        "ms_mediana": round(statistics.median(s), 1),
        "ms_min": round(s[0], 1), "ms_max": round(s[-1], 1), "n": len(s),
        "determinista": len(textos) == 1,
        "vram_pico_MiB": mu.pico, "vram_delta_lote_MiB": mu.pico - pico_ini,
    }
    print(f"{nom:36s} CER={ev['cer_pct']:6.1f}%  dist={ev['dist_global']:4d}  "
          f"frases={ev['frases_exactas']}/3  {statistics.median(s):7.1f} ms  "
          f"det={'si' if len(textos) == 1 else 'NO'}", flush=True)

mu.vivo = False
if not SIN_MUESTREO:
    mu.join(timeout=2)
fin = {"evento": "fin", "vram_pico_MiB": mu.pico, "vram_base_MiB": base_vram,
       "coste_propio_MiB": mu.pico - base_vram, "pico_util_pct": mu.pico_util,
       "muestreo_vram": not SIN_MUESTREO,
       "aviso": ("tiempos limpios, pico de VRAM NO medido" if SIN_MUESTREO
                 else "pico de VRAM valido; los tiempos llevan el coste del muestreo")}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"{etiqueta}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
