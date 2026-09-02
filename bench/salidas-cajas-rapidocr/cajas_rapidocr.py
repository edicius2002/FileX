#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B22 (residuo) — sonda del MECANISMO detras de los picos de RapidOCR v6+R6
sobre escaneado_d5c/d5a: cuantas cajas detecta, que area cubren y que LINEA
de referencia desaparece en cada ppp, sondeado en ejecucion (no deducido del
codigo de RapidOCR/PaddleX, trampa del proyecto). Toma filex.gpu.Lock: esto
SI usa la tarjeta. Entrada por NDARRAY BGR (trampa 30, misma via que
bench/salidas-suelo-ppp/b21b22.py), declarado."""
import argparse, contextlib, json, os, statistics, subprocess, sys, time

ROOT = r"D:\Work\research\FileX\.ccb\workspaces\worker1"
BASE = os.path.join(ROOT, r"bench\salidas-cajas-rapidocr")
PDF = os.path.join(ROOT, r"corpus\pdf")
IMG = os.path.join(BASE, "img"); TXT = os.path.join(BASE, "texto"); JS = os.path.join(BASE, "json")
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
PPPS = [80, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150]
R6 = {"Det.mean": [.485, .456, .406], "Det.std": [.229, .224, .225], "Det.thresh": .2,
      "Det.box_thresh": .45, "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000}

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar
sys.path.insert(0, ROOT)
from filex import gpu

def ref_lineas():
    # Misma fuente que consume el generador/evaluador de d5 (trampa 92): lista
    # de lineas, con su bloque (tamano de letra), no la cadena concatenada.
    sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
    from d4_texto import BLOQUES
    lineas, bloques = [], []
    for etq, vs in BLOQUES.items():
        for v in vs:
            lineas.append(v); bloques.append(etq)
    return lineas, bloques
REF, REF_BLOQUE = ref_lineas()

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

def run(a, timeout=60, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(a, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=e)

def raster(doc, ppp):
    dst = os.path.join(IMG, f"ppp{ppp:03d}__{doc}.png")
    if not os.path.exists(dst):
        p = run([MAGICK, "-density", str(ppp), os.path.join(PDF, doc+".pdf")+"[0]",
                 "-units", "PixelsPerInch", "-density", str(ppp), "-colorspace", "sRGB",
                 "-alpha", "remove", "-background", "white", "-flatten", dst], timeout=60)
        if p.returncode: raise RuntimeError("magick rc=%s: %s" % (p.returncode, p.stderr[:300]))
    ident = run([MAGICK, "identify", "-format", "%wx%h %x,%y %U", dst])
    return dst, ident.stdout.strip()

def bgr(path):
    """Misma via de entrada que suelo-ppp.md: ndarray BGR de tres canales
    desde PNG sRGB (trampa 30: la via NO es intercambiable con la ruta)."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    if a.ndim != 3 or a.shape[2] != 3:
        raise RuntimeError("entrada no es ndarray BGR de tres canales: %s" % (a.shape,))
    return a[:, :, ::-1].copy()

def area_poligono(box):
    xs = [float(p[0]) for p in box]; ys = [float(p[1]) for p in box]
    n = len(box)
    s = sum(xs[i]*ys[(i+1) % n] - xs[(i+1) % n]*ys[i] for i in range(n))
    return abs(s) / 2.0

def build_engine():
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
    return x, {"motor": "RapidOCR ONNX rapid-v6-r6", "entrada": "ndarray BGR, 3 canales desde PNG sRGB",
               "dispositivo": "GPU cuda:0", "R6": True,
               "det_limit_side_len": x.text_det.limit_side_len, "det_limit_type": x.text_det.limit_type}

def celda(x, doc, ppp, native, reps):
    path, geom = raster(doc, ppp)
    im = bgr(path); h, w = im.shape[:2]
    prep = x.text_det.get_preprocess(max(h, w))
    resized_shape = tuple(prep(im).shape)  # sondeado en ejecucion: el mismo callable que usa el detector
    n_boxes = []; areas = []; textos = []; cers = []
    detalle_ultimo = None
    for _ in range(reps):
        pre_img, op_record = x.preprocess_img(im)
        det_res, cls_res, rec_res, crops = x.run_ocr_steps(pre_img, op_record)
        final = x.build_final_output(im, det_res, cls_res, rec_res, crops, op_record)
        nb = len(det_res.boxes) if det_res.boxes is not None else 0
        area = sum(area_poligono(b) for b in det_res.boxes) if det_res.boxes is not None and nb else 0.0
        texto = " ".join(final.txts) if final and final.txts else ""
        n_boxes.append(nb); areas.append(round(area, 1)); textos.append(texto)
        ev = evaluar(texto, "acentos", REF)
        cers.append(ev["cer_pct"]); detalle_ultimo = ev["detalle"]; chars_salida_ultimo = ev["chars_salida"]
    texto = textos[-1]
    lineas = [{"bloque": b, "linea": d["esperado"], "exacto": d["exacto"], "sim_pct": d["sim_pct"]}
              for b, d in zip(REF_BLOQUE, detalle_ultimo)]
    bytes_ref = len(" ".join(REF).encode("utf-8"))
    return {"doc": doc, "ppp": ppp, "ppp_nativo": native, "raster_wh": [w, h],
            "resized_det_input": list(resized_shape), "png_identify": geom,
            "n_boxes": n_boxes, "area_total_px2": areas, "area_frac_pagina": round(areas[-1]/(w*h), 5) if areas[-1] else 0.0,
            "n": reps, "determinista_boxes": len(set(n_boxes)) == 1, "determinista_texto": len(set(textos)) == 1,
            "cer_pct": cers[-1], "cer_pct_reps": cers, "lineas": lineas,
            "chars_salida": chars_salida_ultimo, "bytes_utf8_salida": len(texto.encode("utf-8")),
            "bytes_utf8_ref": bytes_ref, "texto_crudo": texto,
            "texto": f"{doc}__ppp{ppp:03d}.txt"}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("doc"); ap.add_argument("--native", type=int, required=True)
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()
    os.makedirs(TXT, exist_ok=True); os.makedirs(JS, exist_ok=True); os.makedirs(IMG, exist_ok=True)
    with gpu.Lock("cajas-rapidocr-" + args.doc) as lk:
        x, meta = build_engine(); meta["lock_aviso"] = lk.aviso
        mono_ini = testigo_mono(); proc_ini = testigo_proceso()
        rows = []; t0 = time.time()
        for ppp in sorted(set(PPPS + [args.native])):
            row = celda(x, args.doc, ppp, args.native, args.reps)
            log = ["=== texto crudo ===", row["texto_crudo"], "", "=== detalle por linea ==="]
            log += ["[%s] %s -> exacto=%s sim=%.1f" % (l["bloque"], l["linea"], l["exacto"], l["sim_pct"])
                    for l in row["lineas"]]
            open(os.path.join(TXT, row["texto"]), "w", encoding="utf-8").write("\n".join(log))
            rows.append(row)
            print(json.dumps({k: row[k] for k in ("doc", "ppp", "n_boxes", "area_frac_pagina", "cer_pct",
                                                    "resized_det_input", "determinista_boxes", "determinista_texto",
                                                    "chars_salida", "bytes_utf8_salida")},
                              ensure_ascii=False), flush=True)
        mono_fin = testigo_mono(); proc_fin = testigo_proceso()
    ruido = {"testigo_monohilo_ini_ms": mono_ini, "testigo_monohilo_fin_ms": mono_fin,
             "deriva": round(mono_fin/max(mono_ini, .01), 2),
             "testigo_proceso_ini_ms": proc_ini, "testigo_proceso_fin_ms": proc_fin,
             "nivel_vs_reposo": round(max(proc_ini, proc_fin)/26.65, 2)}
    out = {"meta": meta, "doc": args.doc, "reps": args.reps, "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel_vs_reposo"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time()-t0, 1)}
    json.dump(out, open(os.path.join(JS, "cajas_" + args.doc + ".json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
