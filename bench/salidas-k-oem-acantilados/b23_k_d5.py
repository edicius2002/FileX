#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B23 — el k por MINIMO ARREPENTIMIENTO sobre un corpus que SI discrimina: la
familia d5 (60/72/80/90 ppp nativos, CUATRO geometrias de pagina distintas,
NINGUNA comparte generador con las otras tres del d4-original). Rejilla
REDUCIDA y declarada como tal (ver bench/k-oem-acantilados.md): 5
configuraciones de las 9 originales (RapidOCR v6+R6, PaddleOCR v6 medio,
EasyOCR, Tesseract psm3, Tesseract psm11) x 4 documentos x 7 factores.

Raster: MISMA receta que bench/salidas-k-motor/preparar_km.py (gris, ruta,
sin declarar pHYs) para los tres motores no-Tesseract -- son inmunes al pHYs
(trampa 29) y esta es la receta que ya fijo el k original, asi que hay que
igualarla para que el arrepentimiento sea comparable. Tesseract usa la receta
DECLARADA de siempre (-units PixelsPerInch), porque el es el unico que la
consulta.

uso: python b23_k_d5.py <rapidocr-r6|paddleocr|easyocr|tess3|tess11>
"""
import argparse, json, os, statistics, subprocess, sys, time

ROOT = r"D:\Work\research\FileX\.ccb\workspaces\worker1"
BASE = os.path.join(ROOT, r"bench\salidas-k-oem-acantilados")
PDF = os.path.join(ROOT, r"corpus\pdf")
IMG = os.path.join(BASE, "img"); JS = os.path.join(BASE, "json"); TXT = os.path.join(BASE, "texto")
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"
DOCS = [("escaneado_d5a", 90), ("escaneado_d5c", 80), ("escaneado_d5", 72), ("escaneado_d5b", 60)]
FACTORES = [0.75, 0.875, 1.00, 1.125, 1.25, 1.40, 1.60]

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
from d4_texto import BLOQUES
REF = [linea for bloque in BLOQUES.values() for linea in bloque]
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

def raster_gris(doc, factor, native):
    ppp = int(round(native * factor))
    dst = os.path.join(IMG, f"kf{int(round(factor*1000)):04d}__{doc}.png")
    if not os.path.exists(dst):
        p = subprocess.run([MAGICK, "-density", str(ppp), os.path.join(PDF, doc+".pdf")+"[0]",
                             "-colorspace", "Gray", "-alpha", "remove", "-background", "white",
                             "-flatten", dst], stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=120)
        if p.returncode: raise RuntimeError("magick rc=%s: %s" % (p.returncode, p.stderr[:300]))
    return dst, ppp

def raster_declarado(doc, factor, native):
    ppp = int(round(native * factor))
    dst = os.path.join(IMG, f"kd{int(round(factor*1000)):04d}__{doc}.png")
    if not os.path.exists(dst):
        p = subprocess.run([MAGICK, "-density", str(ppp), os.path.join(PDF, doc+".pdf")+"[0]",
                             "-units", "PixelsPerInch", "-density", str(ppp), "-colorspace", "sRGB",
                             "-alpha", "remove", "-background", "white", "-flatten", dst],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        if p.returncode: raise RuntimeError("magick rc=%s: %s" % (p.returncode, p.stderr[:300]))
    return dst, ppp

def build(config):
    if config == "rapidocr-r6":
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
        return (lambda p: (lambda r: " ".join(r.txts) if r and r.txts else "")(x(p))), \
               {"motor": "RapidOCR v6 small + R6", "dispositivo": "GPU cuda:0", "gpu": True}
    if config == "paddleocr":
        from paddleocr import PaddleOCR
        x = PaddleOCR(device="gpu:0", use_doc_orientation_classify=False, use_doc_unwarping=False,
                      use_textline_orientation=True)
        def leer(p):
            out = []
            for z in x.predict(p):
                d = z if isinstance(z, dict) else getattr(z, "json", {}).get("res", {})
                out.extend(d.get("rec_texts", []))
            return " ".join(out)
        return leer, {"motor": "PaddleOCR v6 medium", "dispositivo": "GPU gpu:0", "gpu": True}
    if config == "easyocr":
        import easyocr
        x = easyocr.Reader(["es", "en"], gpu=True, verbose=False)
        return (lambda p: " ".join(x.readtext(p, detail=0, paragraph=False))), \
               {"motor": "EasyOCR CRAFT + latin_g2", "dispositivo": "GPU cuda:0", "gpu": True}
    if config.startswith("tess"):
        psm = config[4:]
        def leer(p):
            out = os.path.join(BASE, "img", "tmp_b23")
            r = subprocess.run([TESS, p, out, "-l", "spa", "--psm", psm], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=20, env={**os.environ, "TESSDATA_PREFIX": TESSDATA})
            return open(out+".txt", encoding="utf-8", errors="replace").read() if r.returncode == 0 and os.path.exists(out+".txt") else ""
        return leer, {"motor": "Tesseract 5, psm " + psm, "dispositivo": "CPU", "gpu": False}
    raise ValueError(config)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", choices=["rapidocr-r6", "paddleocr", "easyocr", "tess3", "tess11"])
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()
    _, meta0 = build(args.config)
    lock = gpu.Lock("B23-" + args.config) if meta0["gpu"] else __import__("contextlib").nullcontext()
    with lock as lk:
        leer, meta = build(args.config)
        if meta["gpu"]:
            meta["lock_aviso"] = lk.aviso
        mono_ini = testigo_mono(); proc_ini = testigo_proceso()
        rows = []; t0 = time.time()
        for doc, native in DOCS:
            for f in FACTORES:
                if args.config.startswith("tess"):
                    path, ppp = raster_declarado(doc, f, native)
                else:
                    path, ppp = raster_gris(doc, f, native)
                textos = []; cers = []
                for _ in range(args.reps):
                    texto = leer(path); textos.append(texto)
                    ev = evaluar(texto, "acentos", REF); cers.append(ev["cer_pct"])
                texto = textos[-1]
                nom = os.path.splitext(os.path.basename(path))[0]
                open(os.path.join(TXT, f"{args.config}__{nom}.txt"), "w", encoding="utf-8").write(texto)
                row = {"config": args.config, "doc": doc, "ppp_nativo": native, "factor": f, "ppp": ppp,
                       "n": args.reps, "determinista": len(set(textos)) == 1,
                       "cer_pct": cers[-1], "cer_reps": cers}
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
        mono_fin = testigo_mono(); proc_fin = testigo_proceso()
    ruido = {"mono_ini": mono_ini, "mono_fin": mono_fin, "deriva": round(mono_fin/max(mono_ini, .01), 2),
             "proc_ini": proc_ini, "proc_fin": proc_fin, "nivel": round(max(proc_ini, proc_fin)/26.65, 2)}
    out = {"meta": meta, "config": args.config, "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time()-t0, 1)}
    json.dump(out, open(os.path.join(JS, "b23_" + args.config + ".json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
