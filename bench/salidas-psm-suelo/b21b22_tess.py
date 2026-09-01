#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B21/B22 para Tesseract (psm 3 y psm 11). Deriva de
bench/salidas-suelo-ppp/b21b22.py (mismo DOCS, mismo barrido de ppp, mismo
evaluador) para que las filas sean comparables celda a celda con las 336 de
bench/suelo-ppp.md. Solo el motor cambia: aqui no hay rama GPU, Tesseract es
CPU y no toma filex.gpu.Lock (mismo criterio que el script de origen).
Ejecutar solo con el python.exe de Windows (.venv-ai), nunca con el de WSL:
bench/suelo-ppp.md documenta por que (USERPROFILE se hereda como UNC)."""
import argparse, json, os, statistics, subprocess, sys, time

ROOT = r"D:\Work\research\FileX\.ccb\workspaces\worker1"
BASE = os.path.join(ROOT, r"bench\salidas-psm-suelo")
PDF = os.path.join(ROOT, r"corpus\pdf")
IMG = os.path.join(BASE, "img"); TXT = os.path.join(BASE, "texto"); JS = os.path.join(BASE, "json")
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"
DOCS = [("escaneado_d5a",90),("escaneado_d5c",80),("escaneado_d5",72),("escaneado_d5b",60)]

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar
sys.path.insert(0, ROOT)
from filex import gpu  # noqa: F401 (importado para paridad con b21b22.py; no se usa: Tesseract es CPU)

def ref():
    # Misma fuente que consume el generador/evaluador de d5; nunca se parsea su copia .txt (trampa 92).
    sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
    from d4_texto import BLOQUES
    return [linea for bloque in BLOQUES.values() for linea in bloque]
REF = ref()

def testigo_mono(n=400000):
    t = time.perf_counter(); z = 0
    for i in range(n): z += i*i
    return round((time.perf_counter()-t)*1000, 2)

def testigo_proceso(n=5):
    vals = []
    for _ in range(n):
        t = time.perf_counter()
        try:
            subprocess.run(["ffprobe","-v","quiet","-version"], stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=20)
        except Exception:
            return -1.0
        vals.append((time.perf_counter()-t)*1000)
    return round(statistics.median(vals), 2)

def run(a, timeout=20, env=None):
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

def engine(name):
    assert name.startswith("tess"), "este arnes solo mide Tesseract: %r" % name
    psm = name[4:]
    def ocr(path):
        out = os.path.join(BASE, "tmp", "tess_" + name)
        p = run([TESS, path, out, "-l", "spa", "--psm", psm], timeout=20, env={"TESSDATA_PREFIX": TESSDATA})
        t = open(out+".txt", encoding="utf-8", errors="replace").read() if p.returncode == 0 and os.path.exists(out+".txt") else ""
        return t, p.returncode, p.stderr[:200]
    return ocr, {"motor": "Tesseract 5", "psm": int(psm),
                 "entrada": "ruta PNG (Tesseract; no adaptador ndarray)",
                 "dispositivo": "GPU no aplica; CPU"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config"); ap.add_argument("--ppp", required=True); ap.add_argument("--reps", type=int, default=9)
    args = ap.parse_args()
    pp = [int(x) for x in args.ppp.split(",")]
    os.makedirs(TXT, exist_ok=True); os.makedirs(JS, exist_ok=True); os.makedirs(IMG, exist_ok=True)
    ocr, meta = engine(args.config); rows = []; t0 = time.time()
    mono_ini = testigo_mono(); proc_ini = testigo_proceso()
    for doc, native in DOCS:
        for ppp in sorted(set(pp + [native])):
            path, geom = raster(doc, ppp)
            warm, rc0, err0 = ocr(path); times = []; outputs = []; rcs = []; errors = []
            for _ in range(args.reps):
                a = time.perf_counter(); text, code, why = ocr(path)
                times.append(round((time.perf_counter()-a)*1000, 1))
                outputs.append(text); rcs.append(code); errors.append(why)
            text = outputs[-1]; ev = evaluar(text, "acentos", REF)
            fn = f"{args.config}__ppp{ppp:03d}__{doc}.txt"
            open(os.path.join(TXT, fn), "w", encoding="utf-8").write(text)
            rows.append({"config": args.config, "doc": doc, "ppp_nativo": native, "ppp": ppp,
                "factor": round(ppp/native, 3), "png": os.path.basename(path), "png_identify": geom,
                "entrada": meta["entrada"], "dispositivo": meta["dispositivo"], "psm": meta["psm"],
                "rc": rcs, "error": errors, "n": args.reps, "ms_mediana": statistics.median(times),
                "determinista": len(set(outputs)) == 1, "metrica": ev["metrica"],
                "cer_pct": ev["cer_pct"], "cer_acentos_pct": ev["cer_acentos_pct"],
                "cer_ciego_pct": ev["cer_ciego_pct"], "dist_acentos": ev["dist_acentos"], "texto": fn})
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    mono_fin = testigo_mono(); proc_fin = testigo_proceso()
    ruido = {"testigo_monohilo_ini_ms": mono_ini, "testigo_monohilo_fin_ms": mono_fin,
             "deriva": round(mono_fin/max(mono_ini, .01), 2),
             "testigo_proceso_ini_ms": proc_ini, "testigo_proceso_fin_ms": proc_fin,
             "nivel_vs_reposo": round(max(proc_ini, proc_fin)/26.65, 2)}
    out = {"meta": meta, "config": args.config, "reps": args.reps,
           "orden_docs": "d5a,d5c,d5,d5b (mismo orden que bench/salidas-suelo-ppp)",
           "rasterizador": "ImageMagick -units PixelsPerInch -density N; pHYs=N",
           "ruido": ruido, "etiqueta_ruido": "SUCIA" if ruido["nivel_vs_reposo"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time()-t0, 1)}
    json.dump(out, open(os.path.join(JS, args.config+".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
