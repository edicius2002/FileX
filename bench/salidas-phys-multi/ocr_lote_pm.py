# -*- coding: utf-8 -*-
"""G4 / B19 — arnes del barrido `pHYs` × VIA DE ENTRADA × motor.

COPIA ADAPTADA de `bench/salidas-k-motor/ocr_lote_km.py` (M1). El original NO se toca:
es de otro agente y es la trazabilidad de 396 celdas.

Que cambia frente al de M1, y por que
-------------------------------------
1. **Eje nuevo: la VIA DE ENTRADA.** M1 pasaba siempre la RUTA. Aqui `VIA=ruta` hace
   lo mismo y `VIA=array` decodifica el PNG con `cv2.imread(..., IMREAD_COLOR)` y le
   entrega al motor un `numpy.ndarray` BGR. Los tres motores aceptan las dos cosas
   (easyocr/utils.py:735-770, rapidocr/utils/load_image.py:32-58,
   paddlex/inference/common/reader/image_reader.py:51-56). FileX va a usar las dos:
   la ruta hoy, el array en cuanto el sidecar decodifique una vez.
   Con `VIA=array` el `pHYs` NO PUEDE llegar al motor —lo consume el arnes—, asi que
   esa columna es a la vez medida y CONTROL: siete entradas identicas bit a bit.
2. **El eje del metadato son variantes de CABECERA sobre los MISMOS IDAT**
   (`preparar_pm.py`), no rasterizados distintos.
3. **Referencia EXPLICITA por documento** (`ocr_eval_pm.py`), no deducida del nombre.
4. Se registra el `md5` del texto de salida de cada celda: comparar CER es comparar
   un resumen; comparar `md5` es comparar la salida. `CLAUDE.md` trampa 25 pide
   separar «no arranco» de «no leyo»; en proceso no hay `rc`, asi que se registran
   la EXCEPCION, los bytes y el `md5` — un 0 bytes con excepcion y un 0 bytes sin
   ella son celdas distintas y salen distintas en el JSON.

uso: python ocr_lote_pm.py <rapidocr|paddleocr|easyocr> <cpu|cuda> <glob>
env: REPS(9) VIA(ruta|array) SUFIJO IMGDIR SIN_MUESTREO VRAM_TOPE
"""
import glob as _glob
import hashlib
import json
import os
import statistics
import subprocess
import sys
import threading
import time

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-phys-multi")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
OUT = os.path.join(BASE, "texto")
JSN = os.path.join(BASE, "json")
sys.path.insert(0, BASE)
from ocr_eval_pm import evaluar, ref_de_doc  # noqa: E402

os.makedirs(OUT, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
patron = sys.argv[3] if len(sys.argv) > 3 else "*.png"
REPS = int(os.environ.get("REPS", "9"))
VIA = os.environ.get("VIA", "ruta")
gpu = dispositivo == "cuda"
etiqueta = f"{motor}_{dispositivo}_{VIA}" + os.environ.get("SUFIJO", "")

FFPROBE = r"D:\utils\ffmpeg\bin\ffprobe.exe"
if not os.path.exists(FFPROBE):
    FFPROBE = "ffprobe"

R6 = {"Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225],
      "Det.thresh": 0.2, "Det.box_thresh": 0.45, "Det.unclip_ratio": 1.4,
      "Det.max_candidates": 3000}


# ---------------------------------------------------------------- testigos de ruido
def vram():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0])
    except Exception:
        return -1


def util():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0])
    except Exception:
        return -1


def testigo_monohilo(n=400000):
    """TESTIGO 1 — DERIVA dentro de la tanda. Ciego a la contencion multinucleo."""
    t = time.perf_counter()
    s = 0
    for i in range(n):
        s += i * i
    return round((time.perf_counter() - t) * 1000, 2)


TOPADO = {"si": False}


def testigo_proceso(n=5, tope_s=20.0):
    """TESTIGO 2 — NIVEL de carga de la maquina, CON TOPE de 20 s (CLAUDE.md §3:
    un testigo que puede tumbar la medicion no es un testigo)."""
    ms = []
    t_ini = time.perf_counter()
    for _ in range(n):
        restante = tope_s - (time.perf_counter() - t_ini)
        if restante <= 0.5:
            TOPADO["si"] = True
            return round(tope_s * 1000, 2)
        t = time.perf_counter()
        try:
            subprocess.run([FFPROBE, "-v", "quiet", "-version"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=restante)
        except Exception:
            TOPADO["si"] = True
            return round(tope_s * 1000, 2)
        ms.append((time.perf_counter() - t) * 1000)
    if not ms:
        TOPADO["si"] = True
        return round(tope_s * 1000, 2)
    return round(statistics.median(ms), 2)


VRAM_TOPE = int(os.environ.get("VRAM_TOPE", "11300"))


class Muestreador(threading.Thread):
    def __init__(self, activo=True):
        super().__init__(daemon=True)
        self.pico = 0
        self.pico_util = 0
        self.vivo = activo

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
mono_ini = testigo_monohilo()
proc_ini = testigo_proceso()
SIN_MUESTREO = os.environ.get("SIN_MUESTREO") == "1"

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
        "Det.lang_type": LangDet(os.environ.get("RO_LANGDET", "ch")),
        "Rec.lang_type": LangRec(os.environ.get("RO_LANGREC", "ch")),
        "Det.ocr_version": OCRVersion(os.environ.get("RO_VER", "PP-OCRv6")),
        "Rec.ocr_version": OCRVersion(os.environ.get("RO_VER", "PP-OCRv6")),
        "Det.model_type": ModelType(os.environ.get("RO_TIPO", "small")),
        "Rec.model_type": ModelType(os.environ.get("RO_TIPO", "small")),
    }
    if os.environ.get("RO_NORM", "1") == "1":
        params.update(R6)
    lector = RapidOCR(params=params)
    td = getattr(lector, "text_det", None)
    modelos["det_efectivo"] = {"mean": str(getattr(td, "mean", "?")),
                               "std": str(getattr(td, "std", "?")),
                               "limit_side_len": getattr(td, "limit_side_len", "?"),
                               "limit_type": getattr(td, "limit_type", "?")}
    modelos["config"] = {k: str(getattr(v, "value", v)) for k, v in params.items()
                         if k.startswith(("Det.", "Rec."))}

    def leer(x):
        r = lector(x)
        return " ".join(r.txts) if r and r.txts else ""

    def cajas(x):
        r = lector(x)
        try:
            return 0 if r is None or r.boxes is None else len(r.boxes)
        except Exception:
            return -1

elif motor == "paddleocr":
    import paddle
    from paddleocr import PaddleOCR
    kw = {"device": "gpu:0" if gpu else "cpu",
          "use_doc_orientation_classify": False,
          "use_doc_unwarping": False, "use_textline_orientation": True}
    lector = PaddleOCR(**kw)
    modelos["paddle"] = paddle.__version__
    modelos["kwargs"] = {k: str(v) for k, v in kw.items()}
    try:
        modelos["params"] = {k: str(v) for k, v in dict(lector._params).items()
                             if "model_name" in k or "lang" in k}
    except Exception:
        pass
    _ultimo = {"n": -1}

    def leer(x):
        out = []
        n = 0
        for p in lector.predict(x):
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            t = d.get("rec_texts", [])
            out.extend(t)
            n += len(t)
        _ultimo["n"] = n
        return " ".join(out)

    def cajas(x):
        leer(x)
        return _ultimo["n"]

elif motor == "easyocr":
    import easyocr
    import torch
    lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)
    modelos["torch"] = torch.__version__
    modelos["torch_cuda"] = str(torch.cuda.is_available())

    def leer(x):
        return " ".join(lector.readtext(x, detail=0, paragraph=False))

    def cajas(x):
        return len(lector.readtext(x, detail=0, paragraph=False))

else:
    raise SystemExit(f"motor desconocido: {motor}")

carga = round(time.time() - t0, 2)
tras_carga = vram()
flag = "limpia" if quiet < 10 else f"SUCIA(pico {quiet}%)"
cab = {"etiqueta": etiqueta, "motor": motor, "dispositivo": dispositivo, "via": VIA,
       "patron": patron, "imgdir": IMG, "carga_frio_s": carga,
       "vram_base_MiB": base_vram, "vram_tras_carga_MiB": tras_carga,
       "quietud_pct": quiet, "flag": flag, "modelos": modelos, "reps": REPS,
       "testigo_monohilo_ini_ms": mono_ini, "testigo_proceso_ini_ms": proc_ini,
       "muestreo_vram": not SIN_MUESTREO}
print(json.dumps(cab, ensure_ascii=False), flush=True)

import cv2  # noqa: E402  (despues del motor: paddle y torch cargan su propio cv2)
import numpy as np  # noqa: E402

rutas = sorted(_glob.glob(os.path.join(IMG, patron)))
res = {}
mu = Muestreador(activo=not SIN_MUESTREO)
mu.pico = tras_carga
if not SIN_MUESTREO:
    mu.start()

for ruta in rutas:
    nom = os.path.splitext(os.path.basename(ruta))[0]
    raiz, variante = nom.rsplit("__", 1)
    doc = raiz.split("__")[0]
    ref = ref_de_doc(doc)
    pico_ini = mu.pico
    v_ahora = vram()
    if v_ahora > VRAM_TOPE:
        res[nom] = {"omitido_vram": v_ahora, "tope": VRAM_TOPE}
        print(f"{nom:46s} OMITIDO por VRAM: {v_ahora} > {VRAM_TOPE} MiB", flush=True)
        continue
    # ---------------------------------------------------------------- la ENTRADA
    if VIA == "array":
        arr = cv2.imread(ruta, cv2.IMREAD_COLOR)
        if arr is None:
            res[nom] = {"error": "cv2.imread devolvio None"}
            print(f"{nom:46s} ERROR cv2.imread None", flush=True)
            continue
        entrada = arr
        md5_entrada = hashlib.md5(np.ascontiguousarray(arr).tobytes()).hexdigest()
        forma = list(arr.shape)
    elif VIA == "ruta":
        entrada = ruta
        md5_entrada = hashlib.md5(open(ruta, "rb").read()).hexdigest()
        forma = None
    else:
        raise SystemExit(f"VIA desconocida: {VIA}")
    try:
        texto = leer(entrada)            # calentamiento, fuera de la medicion
        exc = None
    except Exception as ex:
        res[nom] = {"error": f"{type(ex).__name__}: {str(ex)[:250]}", "chars": 0,
                    "via": VIA, "variante": variante, "raiz": raiz, "doc": doc}
        print(f"{nom:46s} ERROR {type(ex).__name__}: {str(ex)[:80]}", flush=True)
        continue
    ts, textos = [], set()
    for _ in range(REPS):
        t = time.time()
        texto = leer(entrada)
        ts.append((time.time() - t) * 1000)
        textos.add(texto)
    s = sorted(ts)
    try:
        nc = cajas(entrada)
    except Exception:
        nc = -1
    ev = evaluar(texto, ref)
    open(os.path.join(OUT, f"{etiqueta}__{nom}.txt"), "w",
         encoding="utf-8").write(texto)
    res[nom] = {
        "doc": doc, "raiz": raiz, "variante": variante, "via": VIA,
        "referencia": ref, "excepcion": exc,
        "md5_entrada": md5_entrada, "forma_entrada": forma,
        "md5_texto": hashlib.md5(texto.encode("utf-8")).hexdigest(),
        "cer_acentos_pct": ev["cer_acentos_pct"], "dist_acentos": ev["dist_acentos"],
        "cer_ascii_pct": ev["cer_ascii_pct"], "dist_ascii": ev["dist_ascii"],
        "chars_ref_acentos": ev["chars_ref_acentos"], "chars": ev["chars_salida"],
        "lineas_exactas": ev["lineas_exactas"], "lineas_totales": ev["lineas_totales"],
        "acentos_ref": ev["acentos_ref"], "acentos_salida": ev["acentos_salida"],
        "bloques": {k: (v or {}).get("cer_pct") for k, v in ev["bloques"].items()},
        "cajas": nc,
        "ms_mediana": round(statistics.median(s), 1), "ms_min": round(s[0], 1),
        "ms_max": round(s[-1], 1), "n": len(s),
        "determinista": len(textos) == 1,
        "vram_pico_MiB": mu.pico, "vram_delta_lote_MiB": mu.pico - pico_ini,
        "testigo_monohilo_ms": testigo_monohilo(),
    }
    print(f"{nom:46s} CERac={ev['cer_acentos_pct']:7.2f}%  ch={ev['chars_salida']:5d}  "
          f"cajas={nc:4d}  md5={res[nom]['md5_texto'][:8]}  "
          f"{statistics.median(s):8.1f} ms  det={'si' if len(textos) == 1 else 'NO'}",
          flush=True)

mu.vivo = False
if not SIN_MUESTREO:
    mu.join(timeout=2)
mono_fin = testigo_monohilo()
proc_fin = testigo_proceso()
fin = {"evento": "fin", "vram_pico_MiB": mu.pico, "vram_base_MiB": base_vram,
       "coste_propio_MiB": mu.pico - base_vram, "pico_util_pct": mu.pico_util,
       "testigo_monohilo_ini_ms": mono_ini, "testigo_monohilo_fin_ms": mono_fin,
       "deriva_monohilo": round(mono_fin / max(1e-9, mono_ini), 2),
       "testigo_proceso_ini_ms": proc_ini, "testigo_proceso_fin_ms": proc_fin,
       "nivel_proceso_vs_reposo": round(max(proc_ini, proc_fin) / 26.65, 2),
       "testigo_topado": TOPADO["si"], "vram_tope_MiB": VRAM_TOPE}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"{etiqueta}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
