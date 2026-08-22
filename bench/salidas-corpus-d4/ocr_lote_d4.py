# -*- coding: utf-8 -*-
"""G1 / banco de motores de OCR sobre la matriz de imagenes, con las DOS metricas
(con y sin acentos) y con los parametros de modelo CONFIGURABLES, que es lo que
exige la fase 3 (aislar tamaño de modelo / idioma del reconocedor / idioma del
detector).

COPIA ADAPTADA de bench/salidas-ocr-ppp/20_ocr_lote.py. El original no se toca.

Cambios respecto al original, y por que:
  * usa ocr_eval_d4.evaluar(texto, referencia) -> reporta cer_ascii y cer_acentos.
  * rapidocr: OCRVersion / ModelType / LangDet / LangRec por variable de entorno.
  * paddleocr: text_detection_model_name / text_recognition_model_name / lang por
    variable de entorno. En PaddleOCR 3.7.0 el `lang` NO elige tamaño dentro de
    PP-OCRv6 (siempre medium), asi que forzar el nombre del modelo es la UNICA
    forma de cruzar tamaño contra idioma sin confundirlos.

uso: python ocr_lote_d4.py <rapidocr|paddleocr|easyocr> <cpu|cuda> <glob> <ref_id>
env: REPS(9) SUFIJO IMGDIR SIN_MUESTREO
     RO_VER RO_TIPO RO_LANGDET RO_LANGREC
     PD_LANG PD_DET PD_REC
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
BASE = os.path.join(RAIZ, r"bench\salidas-corpus-d4")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
OUT = os.path.join(BASE, "texto")
JSN = os.path.join(BASE, "json")
sys.path.insert(0, BASE)
from ocr_eval_d4 import evaluar  # noqa: E402

os.makedirs(OUT, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
patron = sys.argv[3] if len(sys.argv) > 3 else "*.png"
REF = sys.argv[4] if len(sys.argv) > 4 else "d4"
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


def util():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True).stdout.strip().splitlines()[0])
    except Exception:
        return -1


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


def carga_cpu():
    """Pico de uso de CPU en 5 muestras. Necesario porque en esta sesion hay otros
    agentes midiendo en CPU a la vez: sin esta linea base, una tanda de CPU no es
    un dato, es ruido con aspecto de dato. El arnes solo vigila la GPU."""
    pico = -1
    for _ in range(5):
        try:
            # RUTA ABSOLUTA a proposito: lanzado desde Git Bash, el PATH que hereda
            # el hijo es la version unix (/c/Windows/System32) y Windows no la
            # resuelve -> FileNotFoundError [WinError 2]. Con "powershell" a secas
            # esta sonda devolvio -1 en las 11 tandas de la fase 4.
            v = subprocess.run(
                [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                 "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor).LoadPercentage"],
                capture_output=True, text=True, timeout=30).stdout.strip()
            pico = max(pico, int(v.splitlines()[0]))
        except Exception:
            pass
        time.sleep(0.5)
    return pico


quiet = 0
for _ in range(5):
    quiet = max(quiet, util())
    time.sleep(1)
base_vram = vram()
flag = "limpia" if quiet < 10 else f"SUCIA(pico {quiet}%)"
cpu_pico = carga_cpu() if os.environ.get("MEDIR_CPU") == "1" else None
if cpu_pico is not None and cpu_pico >= 25:
    flag += f"+CPU_OCUPADA({cpu_pico}%)"
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
    # Los pesos que haya que descargar NO deben caer dentro de .venv-ai (regla:
    # los venv se usan para ejecutar, no se modifican). `Global.model_root_dir`
    # los manda a un directorio propio de este agente.
    if os.environ.get("RO_ROOT"):
        params["Global.model_root_dir"] = os.environ["RO_ROOT"]
    for clave, env in (("Det.model_type", "RO_TIPO_DET"), ("Rec.model_type", "RO_TIPO_REC")):
        if os.environ.get(env):
            params[clave] = ModelType(os.environ[env])
    for clave, env in (("Det.ocr_version", "RO_VER_DET"), ("Rec.ocr_version", "RO_VER_REC")):
        if os.environ.get(env):
            params[clave] = OCRVersion(os.environ[env])
    # RO_EXTRA: JSON con cualquier parametro de rapidocr (umbrales del detector,
    # filtro de score del reconocedor...). Es lo que permite pasar de "es la
    # tuberia" a "es ESTE parametro de la tuberia".
    if os.environ.get("RO_EXTRA"):
        params.update(json.loads(os.environ["RO_EXTRA"]))
    lector = RapidOCR(params=params)
    # Que checkpoint se cargo DE VERDAD (el fichero, no la etiqueta pedida).
    # Se busca por varias rutas de atributo y, si fallan, por el nombre de fichero
    # dentro del repr: en rapidocr 3.9.2 `model_info` es un dict anidado enorme.
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
    modelos["pedido"] = {k: str(getattr(v, "value", v)) for k, v in params.items()
                         if k.startswith(("Det.", "Rec.", "Global."))}

    def leer(ruta):
        r = lector(ruta)
        return " ".join(r.txts) if r and r.txts else ""

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
    # PD_EXTRA: JSON con cualquier kwarg de PaddleOCR (umbrales y escalado del
    # detector). Es el otro lado del A/B de la fase 3d.
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
       "referencia": REF, "patron": patron, "imgdir": IMG,
       "carga_frio_s": carga, "vram_base_MiB": base_vram,
       "vram_tras_carga_MiB": tras_carga, "quietud_pct": quiet,
       "cpu_pico_pct": cpu_pico, "flag": flag,
       "modelos": modelos, "reps": REPS, "muestreo_vram": not SIN_MUESTREO}
print(json.dumps(cab, ensure_ascii=False), flush=True)

rutas = sorted(_glob.glob(os.path.join(IMG, patron)))
res = {}
mu = Muestreador(activo=not SIN_MUESTREO)
mu.pico = tras_carga
if not SIN_MUESTREO:
    mu.start()

for ruta in rutas:
    nom = os.path.splitext(os.path.basename(ruta))[0]
    ref = "legado" if ("_d4" not in nom and "d4_" not in nom) else REF
    pico_ini = mu.pico
    try:
        texto = leer(ruta)              # calentamiento, fuera de la medicion
    except Exception as ex:
        res[nom] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
        print(f"{nom:40s} ERROR {type(ex).__name__}: {str(ex)[:80]}", flush=True)
        continue
    ts, textos = [], set()
    for _ in range(REPS):
        t = time.time()
        texto = leer(ruta)
        ts.append((time.time() - t) * 1000)
        textos.add(texto)
    s = sorted(ts)
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
        "normalizada_acentos": ev["normalizada_acentos"],
        "ms_mediana": round(statistics.median(s), 1),
        "ms_min": round(s[0], 1), "ms_max": round(s[-1], 1), "n": len(s),
        "determinista": len(textos) == 1,
        "vram_pico_MiB": mu.pico, "vram_delta_lote_MiB": mu.pico - pico_ini,
    }
    bl = res[nom]["bloques"]
    print(f"{nom:40s} CERac={ev['cer_acentos_pct']:6.2f}%  "
          f"CERascii={ev['cer_ascii_pct']:6.2f}%  "
          f"lin={ev['lineas_exactas']}/{ev['lineas_totales']}  "
          f"bloques={ {k: v for k, v in bl.items()} }  "
          f"{statistics.median(s):7.1f} ms  det={'si' if len(textos) == 1 else 'NO'}",
          flush=True)

mu.vivo = False
if not SIN_MUESTREO:
    mu.join(timeout=2)
fin = {"evento": "fin", "vram_pico_MiB": mu.pico, "vram_base_MiB": base_vram,
       "coste_propio_MiB": mu.pico - base_vram, "pico_util_pct": mu.pico_util,
       "muestreo_vram": not SIN_MUESTREO}
print(json.dumps(fin, ensure_ascii=False), flush=True)
json.dump({"cabecera": cab, "fin": fin, "res": res},
          open(os.path.join(JSN, f"{etiqueta}__cer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
