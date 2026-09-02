#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B16 — refina la rejilla de escaneado_d3 entre los dos acantilados conocidos
(RapidOCR+R6 x1,25->x1,40: 2,53% -> 46,84%; PaddleOCR x1,40->x1,60: 3,80% ->
75,95%), medidos en bench/k-por-motor.md. MISMA orden de rasterizado que
preparar_km.py (gris, sin declarar pHYs) para reproducir los anclajes byte a
byte: RapidOCR y PaddleOCR son inmunes al pHYs (trampa 29), asi que declarar
o no aqui es irrelevante para el resultado, pero declarar ROMPERIA la
comparabilidad con los anclajes ya publicados si el motor SI lo consultara.
Se mantiene la receta original a proposito.

uso: python b16_acantilados.py <rapidocr-r6|paddleocr>
"""
import argparse, json, os, statistics, subprocess, sys, time

ROOT = r"D:\Work\research\FileX\.ccb\workspaces\worker1"
BASE = os.path.join(ROOT, r"bench\salidas-k-oem-acantilados")
PDF = os.path.join(ROOT, r"corpus\pdf")
IMG = os.path.join(BASE, "img"); JS = os.path.join(BASE, "json")
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
DOC = "escaneado_d3"
NATIVO = 100  # bench/k-por-motor.md §1.1: d3 tiene 100 ppp nativos
# Union de las dos rejillas a refinar, mas los tres anclajes ya publicados.
FACTORES = [1.25, 1.28, 1.30, 1.32, 1.35, 1.38, 1.40, 1.44, 1.48, 1.50, 1.52, 1.56, 1.60]

sys.path.insert(0, BASE)
from ocr_eval_km import evaluar, ref_de_nombre
sys.path.insert(0, ROOT)
from filex import gpu

R6 = {"Det.mean": [.485, .456, .406], "Det.std": [.229, .224, .225], "Det.thresh": .2,
      "Det.box_thresh": .45, "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000}

def testigo_mono(n=400000):
    t = time.perf_counter(); z = 0
    for i in range(n): z += i*i
    return round((time.perf_counter()-t)*1000, 2)

def testigo_proceso(n=5):
    vals = []
    for _ in range(n):
        t = time.perf_counter()
        try:
            subprocess.run(["ffprobe", "-v", "quiet", "-version"], stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=20)
        except Exception:
            return -1.0
        vals.append((time.perf_counter()-t)*1000)
    return round(statistics.median(vals), 2)

def raster(factor):
    dst = os.path.join(IMG, f"k{int(round(factor*1000)):04d}__{DOC}.png")
    ppp = int(round(NATIVO * factor))
    if not os.path.exists(dst):
        # MISMA orden que preparar_km.py: gris, sin -units PixelsPerInch.
        p = subprocess.run([MAGICK, "-density", str(ppp), os.path.join(PDF, DOC+".pdf")+"[0]",
                             "-colorspace", "Gray", "-alpha", "remove", "-background", "white",
                             "-flatten", dst], stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=120)
        if p.returncode: raise RuntimeError("magick rc=%s: %s" % (p.returncode, p.stderr[:300]))
    ident = subprocess.run([MAGICK, "identify", "-format", "%wx%h", dst],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True).stdout.strip()
    return dst, ppp, ident

def build_rapidocr():
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    kw = {"EngineConfig.onnxruntime.use_cuda": True, "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
          "Det.engine_type": EngineType.ONNXRUNTIME, "Cls.engine_type": EngineType.ONNXRUNTIME,
          "Rec.engine_type": EngineType.ONNXRUNTIME, "Det.lang_type": LangDet("ch"), "Rec.lang_type": LangRec("ch"),
          "Det.ocr_version": OCRVersion("PP-OCRv6"), "Rec.ocr_version": OCRVersion("PP-OCRv6"),
          "Det.model_type": ModelType("small"), "Rec.model_type": ModelType("small")}
    kw.update(R6)
    x = RapidOCR(params=kw)
    def leer(path):
        r = x(path)
        return " ".join(r.txts) if r and r.txts else ""
    return leer, {"motor": "RapidOCR v6 small + R6", "dispositivo": "GPU cuda:0"}

def build_paddleocr():
    import paddle
    from paddleocr import PaddleOCR
    x = PaddleOCR(device="gpu:0", use_doc_orientation_classify=False, use_doc_unwarping=False,
                  use_textline_orientation=True)
    def leer(path):
        out = []
        for z in x.predict(path):
            d = z if isinstance(z, dict) else getattr(z, "json", {}).get("res", {})
            out.extend(d.get("rec_texts", []))
        return " ".join(out)
    return leer, {"motor": "PaddleOCR v6 medium (defecto)", "dispositivo": "GPU gpu:0", "paddle": paddle.__version__}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("config", choices=["rapidocr-r6", "paddleocr"])
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()
    build = build_rapidocr if args.config == "rapidocr-r6" else build_paddleocr
    with gpu.Lock("B16-" + args.config) as lk:
        leer, meta = build(); meta["lock_aviso"] = lk.aviso
        mono_ini = testigo_mono(); proc_ini = testigo_proceso()
        rows = []; t0 = time.time()
        for f in FACTORES:
            path, ppp, geom = raster(f)
            nom = os.path.splitext(os.path.basename(path))[0]
            ref = ref_de_nombre(nom)  # "legado", el de 79 caracteres de d1-d3
            textos = []; cers = []
            for _ in range(args.reps):
                t = time.time(); texto = leer(path); textos.append(texto)
                ev = evaluar(texto, ref); cers.append(ev["cer_acentos_pct"])
            texto = textos[-1]
            open(os.path.join(BASE, "texto", f"{args.config}__{nom}.txt"), "w",
                 encoding="utf-8").write(texto)
            row = {"config": args.config, "doc": DOC, "factor": f, "ppp": ppp, "geom": geom,
                   "referencia": ref, "n": args.reps, "determinista": len(set(textos)) == 1,
                   "cer_acentos_pct": cers[-1], "cer_reps": cers}
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
        mono_fin = testigo_mono(); proc_fin = testigo_proceso()
    ruido = {"mono_ini": mono_ini, "mono_fin": mono_fin, "deriva": round(mono_fin/max(mono_ini, .01), 2),
             "proc_ini": proc_ini, "proc_fin": proc_fin, "nivel": round(max(proc_ini, proc_fin)/26.65, 2)}
    out = {"meta": meta, "config": args.config, "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time()-t0, 1)}
    json.dump(out, open(os.path.join(JS, "b16_" + args.config + ".json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
