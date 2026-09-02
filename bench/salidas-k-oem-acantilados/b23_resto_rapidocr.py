#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B23 (resto, ronda 5) -- dos de las cuatro configuraciones que faltaban de la
rejilla original de 9 (`k-por-motor.md`): RapidOCR v6 small DEFECTO y RapidOCR
v5 mobile DEFECTO -- es decir, sin la correccion R6 (ImageNet + post-proceso de
PaddleX) que ya se aplico a "RapidOCR v6 small + R6" en b23_k_d5.py.

MISMA rejilla (4 documentos d5 x 7 factores) y MISMO evaluador que b23_k_d5.py,
para que el arrepentimiento sea comparable celda a celda con las 5
configuraciones ya medidas. MISMA receta de raster (gris, ruta, SIN declarar
pHYs) que "rapidocr-r6" -- RapidOCR es inmune al pHYs (trampa 29) -- y de
hecho REUTILIZA el mismo fichero `kf####__doc.png` si ya existe: mismo nombre,
misma orden de `magick`.

Las dos configuraciones de Docling estan en b23_resto_docling.py aparte:
Docling NO consume un PNG, rasteriza el PDF el mismo con
`RapidOcrOptions.scale` (ver ese fichero).

ROOT se calcula desde la ubicacion del propio script, no se hardcodea: la
ronda 4 hardcodeaba `D:\\...\\​.ccb\\workspaces\\worker1`, que ya no existe tras
desmontar CCB (ESTADO-Y-REPARTO.md, ronda 5) -- un ROOT fijo repetiria
exactamente ese error de volumen la proxima vez que cambie la infraestructura.

uso: python b23_resto_rapidocr.py <rapidocr-v6-def|rapidocr-v5-def> [--reps N]
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, "bench", "salidas-k-oem-acantilados")
PDF = os.path.join(ROOT, "corpus", "pdf")
IMG = os.path.join(BASE, "img")
JS = os.path.join(BASE, "json")
TXT = os.path.join(BASE, "texto")
os.makedirs(IMG, exist_ok=True)
os.makedirs(JS, exist_ok=True)
os.makedirs(TXT, exist_ok=True)
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
DOCS = [("escaneado_d5a", 90), ("escaneado_d5c", 80), ("escaneado_d5", 72), ("escaneado_d5b", 60)]
FACTORES = [0.75, 0.875, 1.00, 1.125, 1.25, 1.40, 1.60]

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
from d4_texto import BLOQUES  # noqa: E402
REF = [linea for bloque in BLOQUES.values() for linea in bloque]
sys.path.insert(0, ROOT)
from filex import gpu  # noqa: E402


def testigo_mono(n=400000):
    t = time.perf_counter()
    z = 0
    for i in range(n):
        z += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope_s=20.0):
    """Tope DENTRO del testigo (CLAUDE.md §3): un testigo que puede tumbar la
    medicion no es un testigo."""
    vals = []
    t_ini = time.perf_counter()
    for _ in range(n):
        restante = tope_s - (time.perf_counter() - t_ini)
        if restante <= 0.5:
            return round(tope_s * 1000, 2)
        t = time.perf_counter()
        try:
            subprocess.run(["ffprobe", "-v", "quiet", "-version"], stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=restante)
        except Exception:
            return round(tope_s * 1000, 2)
        vals.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(vals), 2) if vals else round(tope_s * 1000, 2)


def raster_gris(doc, factor, native):
    """MISMA receta que b23_k_d5.py::raster_gris. Se reutiliza el fichero si
    ya existe (mismo nombre `kf####__doc.png`, misma orden de magick): estas
    dos configuraciones caen sobre el MISMO raster que ya uso rapidocr-r6."""
    ppp = int(round(native * factor))
    dst = os.path.join(IMG, f"kf{int(round(factor * 1000)):04d}__{doc}.png")
    if not os.path.exists(dst):
        p = subprocess.run([MAGICK, "-density", str(ppp), os.path.join(PDF, doc + ".pdf") + "[0]",
                             "-colorspace", "Gray", "-alpha", "remove", "-background", "white",
                             "-flatten", dst], stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=120)
        if p.returncode:
            raise RuntimeError("magick rc=%s: %s" % (p.returncode, p.stderr[:300]))
    return dst, ppp


def build(config):
    import torch
    tl = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.isdir(tl):
        os.add_dll_directory(tl)
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    kw = {"EngineConfig.onnxruntime.use_cuda": True,
          "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
          "Det.engine_type": EngineType.ONNXRUNTIME, "Cls.engine_type": EngineType.ONNXRUNTIME,
          "Rec.engine_type": EngineType.ONNXRUNTIME, "Det.lang_type": LangDet("ch"),
          "Rec.lang_type": LangRec("ch")}
    if config == "rapidocr-v6-def":
        kw.update({"Det.ocr_version": OCRVersion("PP-OCRv6"), "Rec.ocr_version": OCRVersion("PP-OCRv6"),
                   "Det.model_type": ModelType("small"), "Rec.model_type": ModelType("small")})
        etiqueta = "RapidOCR v6 small (defecto)"
    elif config == "rapidocr-v5-def":
        kw.update({"Det.ocr_version": OCRVersion("PP-OCRv5"), "Rec.ocr_version": OCRVersion("PP-OCRv5"),
                   "Det.model_type": ModelType("mobile"), "Rec.model_type": ModelType("mobile")})
        etiqueta = "RapidOCR v5 mobile (defecto)"
    else:
        raise ValueError(config)
    x = RapidOCR(params=kw)
    return (lambda p: (lambda r: " ".join(r.txts) if r and r.txts else "")(x(p))), \
           {"motor": etiqueta, "dispositivo": "GPU cuda:0", "gpu": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", choices=["rapidocr-v6-def", "rapidocr-v5-def"])
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()
    lock = gpu.Lock("B23resto-" + args.config)
    with lock as lk:
        leer, meta = build(args.config)
        meta["lock_aviso"] = lk.aviso
        mono_ini = testigo_mono()
        proc_ini = testigo_proceso()
        rows = []
        t0 = time.time()
        for doc, native in DOCS:
            for f in FACTORES:
                path, ppp = raster_gris(doc, f, native)
                textos, cers, rcs = [], [], []
                for _ in range(args.reps):
                    # trampa 99: rc explicito por CELDA, cerrando la brecha
                    # que b23_k_d5.py dejaba anotada (no registraba rc para
                    # los motores GPU, solo para Tesseract).
                    try:
                        texto = leer(path)
                        rc = 0
                    except Exception as ex:
                        texto = ""
                        rc = f"{type(ex).__name__}: {str(ex)[:150]}"
                    textos.append(texto)
                    rcs.append(rc)
                    ev = evaluar(texto, "acentos", REF)
                    cers.append(ev["cer_pct"])
                texto = textos[-1]
                nom = os.path.splitext(os.path.basename(path))[0]
                open(os.path.join(TXT, f"{args.config}__{nom}.txt"), "w",
                     encoding="utf-8").write(texto)
                row = {"config": args.config, "doc": doc, "ppp_nativo": native, "factor": f,
                       "ppp": ppp, "n": args.reps, "determinista": len(set(textos)) == 1,
                       "cer_pct": cers[-1], "cer_reps": cers, "rc_reps": rcs}
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
        mono_fin = testigo_mono()
        proc_fin = testigo_proceso()
    ruido = {"mono_ini": mono_ini, "mono_fin": mono_fin,
             "deriva": round(mono_fin / max(mono_ini, .01), 2),
             "proc_ini": proc_ini, "proc_fin": proc_fin,
             "nivel": round(max(proc_ini, proc_fin) / 26.65, 2)}
    out = {"meta": meta, "config": args.config, "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(os.path.join(JS, "b23resto_" + args.config + ".json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
