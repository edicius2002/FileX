# -*- coding: utf-8 -*-
"""P1 / banco de motores de OCR para el barrido de ppp (B9) y la validacion de la
correccion de normalizacion (B10).

COPIA ADAPTADA de bench/salidas-corpus-d4/ocr_lote_d4.py. El original NO se toca.

Cambios respecto al original, y por que:
  * BASE apunta a bench/salidas-ppp-norm/ (un fichero de salida por agente).
  * RO_NORM=1 aplica la correccion R6 (normalizacion ImageNet + post-proceso de
    PaddleX) que bench/corpus-d4.md §7.4 midio. Es el A/B central de B10.
  * DOS TESTIGOS DE RUIDO, no uno: un bucle monohilo de Python (mide DERIVA dentro
    de la tanda) y un lanzamiento de proceso `ffprobe -version` (mide NIVEL de carga
    de la maquina). El monohilo solo es ciego a la contencion multinucleo: con 12
    nucleos cabe en uno libre y etiqueto `limpia` una tanda que iba x6,8.
  * La referencia se deduce del nombre del fichero (ppp####__doc.png), asi que una
    misma tanda puede mezclar documentos con referencia d4, legado o tipico.

uso: python ocr_lote_pn.py <rapidocr|paddleocr|easyocr> <cpu|cuda> <glob> [ref_forzada]
env: REPS(9) SUFIJO IMGDIR SIN_MUESTREO
     RO_VER RO_TIPO RO_LANGDET RO_LANGREC RO_ROOT RO_NORM RO_EXTRA
     PD_LANG PD_DET PD_REC PD_EXTRA
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
BASE = os.path.join(RAIZ, r"bench\salidas-k-motor")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
OUT = os.path.join(BASE, "texto")
JSN = os.path.join(BASE, "json")
sys.path.insert(0, BASE)
from ocr_eval_km import evaluar, ref_de_nombre  # noqa: E402

os.makedirs(OUT, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
patron = sys.argv[3] if len(sys.argv) > 3 else "*.png"
REF_FORZADA = sys.argv[4] if len(sys.argv) > 4 else None
REPS = int(os.environ.get("REPS", "9"))
gpu = dispositivo == "cuda"
etiqueta = f"{motor}_{dispositivo}" + os.environ.get("SUFIJO", "")

FFPROBE = r"D:\utils\ffmpeg\bin\ffprobe.exe"
if not os.path.exists(FFPROBE):
    FFPROBE = "ffprobe"

# ---------------------------------------------------------------- R6, la correccion
# bench/corpus-d4.md §7.4/§10. Seis numeros: la normalizacion que declara el
# inference.yml que Baidu distribuye CON el modelo, y el post-proceso de PaddleX.
R6 = {
    "Det.mean": [0.485, 0.456, 0.406],
    "Det.std": [0.229, 0.224, 0.225],
    "Det.thresh": 0.2,
    "Det.box_thresh": 0.45,
    "Det.unclip_ratio": 1.4,
    "Det.max_candidates": 3000,
}
R6_SOLO_NORM = {"Det.mean": R6["Det.mean"], "Det.std": R6["Det.std"]}
R6_SOLO_POST = {k: v for k, v in R6.items() if k not in ("Det.mean", "Det.std")}


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
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0])
    except Exception:
        return -1


def testigo_monohilo(n=400000):
    """TESTIGO 1 — DERIVA. Bucle puro de Python en un hilo. Detecta que la tanda se
    va poniendo mas lenta. Es CIEGO a la contencion multinucleo: con 12 nucleos cabe
    en uno libre."""
    t = time.perf_counter()
    s = 0
    for i in range(n):
        s += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope_s=20.0):
    """TESTIGO 2 — NIVEL, CON TOPE. Lanzamiento de proceso; detecta la carga real de
    la maquina (planificador, E/S, contencion multinucleo), que es justo lo que el
    monohilo no ve. Calibracion en reposo del proyecto: ffprobe -version 26,5-26,8 ms.

    CAMBIO DE M1 respecto a la version de P1: TOPE DE 20 s AL TESTIGO ENTERO.
    CLAUDE.md §3 — «un testigo que puede tumbar la medicion no es un testigo»: a P3 se
    le comio un timeout de 60 s por lanzamiento (x94,6). Si se agota el presupuesto se
    devuelve el TOPE (20 000 ms) en negativo-por-convencion NO: se devuelve el tope y
    se marca el flag `testigo_topado`, que sube la tanda a SUCIA."""
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


TOPADO = {"si": False}
# Tope de VRAM: por encima de aqui no se lanza una celda mas. Medido en
# ppp-y-normalizacion.md §7: los dos motores caros terminaron a menos de 350 MiB de
# agotar la tarjeta sin dar ningun error.
VRAM_TOPE = int(os.environ.get("VRAM_TOPE", "11500"))


class Muestreador(threading.Thread):
    """Cada muestra lanza un nvidia-smi y roba CPU: infla las medianas un 30-60 %.
    Por eso hay dos pasadas (SIN_MUESTREO=1 da los tiempos buenos)."""
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
    ver = OCRVersion(os.environ.get("RO_VER", "PP-OCRv5"))
    tipo = ModelType(os.environ.get("RO_TIPO", "mobile"))
    ldet = LangDet(os.environ.get("RO_LANGDET", "ch"))
    lrec = LangRec(os.environ.get("RO_LANGREC", "ch"))
    params = {
        "EngineConfig.onnxruntime.use_cuda": gpu,
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": ldet,
        "Rec.lang_type": lrec,
        "Det.ocr_version": ver,
        "Rec.ocr_version": ver,
        "Det.model_type": tipo,
        "Rec.model_type": tipo,
    }
    if os.environ.get("RO_ROOT"):
        params["Global.model_root_dir"] = os.environ["RO_ROOT"]
    for clave, env in (("Det.model_type", "RO_TIPO_DET"), ("Rec.model_type", "RO_TIPO_REC")):
        if os.environ.get(env):
            params[clave] = ModelType(os.environ[env])
    for clave, env in (("Det.ocr_version", "RO_VER_DET"), ("Rec.ocr_version", "RO_VER_REC")):
        if os.environ.get(env):
            params[clave] = OCRVersion(os.environ[env])
    norm = os.environ.get("RO_NORM", "0")
    if norm == "1":
        params.update(R6)
    elif norm == "norm":
        params.update(R6_SOLO_NORM)
    elif norm == "post":
        params.update(R6_SOLO_POST)
    if os.environ.get("RO_EXTRA"):
        params.update(json.loads(os.environ["RO_EXTRA"]))
    lector = RapidOCR(params=params)
    import re as _re
    for tarea in ("text_det", "text_cls", "text_rec"):
        o = getattr(lector, tarea, None)
        cand = None
        for camino in (("session", "model_path"), ("model_path",),
                       ("session", "model_info"), ("model_info",), ("cfg",)):
            v = o
            for a in camino:
                v = getattr(v, a, None)
                if v is None:
                    break
            if v is not None:
                m = _re.findall(r"[^\\/'\"]+\.(?:onnx|pth)", str(v))
                if m:
                    cand = m[0]
                    break
        modelos[tarea] = cand or "?"
    modelos["R6"] = norm
    modelos["pedido"] = {k: str(getattr(v, "value", v)) for k, v in params.items()
                         if k.startswith(("Det.", "Rec.", "Global."))}
    # Lo que el detector aplica DE VERDAD, leido del objeto ya construido: sin esto
    # "he puesto mean=ImageNet" es una intencion, no una medida.
    # rapidocr/ch_ppocr_det/main.py:31-44 — TextDetector guarda mean/std/umbrales
    # como atributos propios y construye DetPreProcess con ellos en cada llamada.
    try:
        td = getattr(lector, "text_det", None)
        pp = getattr(td, "postprocess_op", None)
        modelos["det_efectivo"] = {
            "mean": str(getattr(td, "mean", "?")), "std": str(getattr(td, "std", "?")),
            "limit_side_len": getattr(td, "limit_side_len", "?"),
            "limit_type": getattr(td, "limit_type", "?"),
            "thresh": getattr(pp, "thresh", "?"),
            "box_thresh": getattr(pp, "box_thresh", "?"),
            "unclip_ratio": getattr(pp, "unclip_ratio", "?"),
            "max_candidates": getattr(pp, "max_candidates", "?"),
        }
    except Exception as ex:
        modelos["det_efectivo"] = f"{type(ex).__name__}: {ex}"

    def leer(ruta):
        r = lector(ruta)
        return " ".join(r.txts) if r and r.txts else ""

    def cajas(ruta):
        r = lector(ruta)
        try:
            return 0 if r is None or r.boxes is None else len(r.boxes)
        except Exception:
            return -1

elif motor == "paddleocr":
    import paddle
    from paddleocr import PaddleOCR
    kw = {"device": "gpu:0" if gpu else "cpu",
          "use_doc_orientation_classify": False,
          "use_doc_unwarping": False,
          "use_textline_orientation": True}
    if os.environ.get("PD_LANG"):
        kw["lang"] = os.environ["PD_LANG"]
    if os.environ.get("PD_DET"):
        kw["text_detection_model_name"] = os.environ["PD_DET"]
    if os.environ.get("PD_REC"):
        kw["text_recognition_model_name"] = os.environ["PD_REC"]
    if os.environ.get("PD_EXTRA"):
        kw.update(json.loads(os.environ["PD_EXTRA"]))
    lector = PaddleOCR(**kw)
    modelos["paddle"] = paddle.__version__
    modelos["kwargs"] = {k: str(v) for k, v in kw.items()}
    try:
        p = lector._params
        modelos["params"] = {k: str(v) for k, v in dict(p).items()
                             if "model_name" in k or "lang" in k}
    except Exception:
        pass

    _ultimo = {"n": -1}

    def leer(ruta):
        r = lector.predict(ruta)
        out = []
        n = 0
        for p in r:
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            t = d.get("rec_texts", [])
            out.extend(t)
            n += len(t)
        _ultimo["n"] = n
        return " ".join(out)

    def cajas(ruta):
        leer(ruta)
        return _ultimo["n"]

elif motor == "easyocr":
    import easyocr
    import torch
    lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)
    modelos["torch"] = torch.__version__
    modelos["torch_cuda"] = str(torch.cuda.is_available())

    def leer(ruta):
        return " ".join(lector.readtext(ruta, detail=0, paragraph=False))

    def cajas(ruta):
        return len(lector.readtext(ruta, detail=0, paragraph=False))

else:
    raise SystemExit(f"motor desconocido: {motor}")

carga = round(time.time() - t0, 2)
tras_carga = vram()
flag = "limpia" if quiet < 10 else f"SUCIA(pico {quiet}%)"
cab = {"etiqueta": etiqueta, "motor": motor, "dispositivo": dispositivo,
       "patron": patron, "imgdir": IMG, "ref_forzada": REF_FORZADA,
       "carga_frio_s": carga, "vram_base_MiB": base_vram,
       "vram_tras_carga_MiB": tras_carga, "quietud_pct": quiet, "flag": flag,
       "testigo_monohilo_ini_ms": mono_ini, "testigo_proceso_ini_ms": proc_ini,
       "modelos": modelos, "reps": REPS, "muestreo_vram": not SIN_MUESTREO}
print(json.dumps(cab, ensure_ascii=False), flush=True)

rutas = sorted(_glob.glob(os.path.join(IMG, patron)))
res = {}
mu = Muestreador(activo=not SIN_MUESTREO)
mu.pico = tras_carga
if not SIN_MUESTREO:
    mu.start()

for idx, ruta in enumerate(rutas):
    nom = os.path.splitext(os.path.basename(ruta))[0]
    ref = REF_FORZADA or ref_de_nombre(nom)
    pico_ini = mu.pico
    # GUARDIA DE VRAM — una consulta por imagen, no por repeticion.
    v_ahora = vram()
    if v_ahora > VRAM_TOPE:
        res[nom] = {"omitido_vram": v_ahora, "tope": VRAM_TOPE}
        print(f"{nom:44s} OMITIDO por VRAM: {v_ahora} > {VRAM_TOPE} MiB", flush=True)
        continue
    try:
        texto = leer(ruta)              # calentamiento, fuera de la medicion
    except Exception as ex:
        res[nom] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
        print(f"{nom:44s} ERROR {type(ex).__name__}: {str(ex)[:80]}", flush=True)
        continue
    ts, textos = [], set()
    for _ in range(REPS):
        t = time.time()
        texto = leer(ruta)
        ts.append((time.time() - t) * 1000)
        textos.add(texto)
    s = sorted(ts)
    try:
        nc = cajas(ruta)
    except Exception:
        nc = -1
    ev = evaluar(texto, ref)
    open(os.path.join(OUT, f"{etiqueta}__{nom}.txt"), "w",
         encoding="utf-8").write(texto)
    res[nom] = {
        "referencia": ref,
        "cer_acentos_pct": ev["cer_acentos_pct"], "dist_acentos": ev["dist_acentos"],
        "cer_ascii_pct": ev["cer_ascii_pct"], "dist_ascii": ev["dist_ascii"],
        "chars_ref_acentos": ev["chars_ref_acentos"],
        "chars": ev["chars_salida"],
        "lineas_exactas": ev["lineas_exactas"], "lineas_totales": ev["lineas_totales"],
        "acentos_ref": ev["acentos_ref"], "acentos_salida": ev["acentos_salida"],
        "bloques": {k: (v or {}).get("cer_pct") for k, v in ev["bloques"].items()},
        "cajas": nc,
        "normalizada_acentos": ev["normalizada_acentos"],
        "ms_mediana": round(statistics.median(s), 1),
        "ms_min": round(s[0], 1), "ms_max": round(s[-1], 1), "n": len(s),
        "determinista": len(textos) == 1,
        "vram_pico_MiB": mu.pico, "vram_delta_lote_MiB": mu.pico - pico_ini,
        "testigo_monohilo_ms": testigo_monohilo(),
    }
    bl = res[nom]["bloques"]
    print(f"{nom:44s} CERac={ev['cer_acentos_pct']:6.2f}%  "
          f"CERascii={ev['cer_ascii_pct']:6.2f}%  "
          f"lin={ev['lineas_exactas']}/{ev['lineas_totales']}  cajas={nc}  "
          f"bloques={ {k: v for k, v in bl.items()} }  "
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
       "testigo_topado": TOPADO["si"], "vram_tope_MiB": VRAM_TOPE,
       "muestreo_vram": not SIN_MUESTREO}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"{etiqueta}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
