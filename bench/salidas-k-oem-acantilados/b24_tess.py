#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B24 — Tesseract: --oem nunca tocado, ocho --psm sin barrer sobre el suelo
declarado, y la tabla de k rehecha con Ghostscript (comparado contra
ImageMagick, los dos con pHYs declarado). Todo CPU, sin filex.gpu.Lock.

uso: python b24_tess.py oem      -> barrido --oem x {psm 3,11} x 4 docs d5, nativo
     python b24_tess.py psm      -> psm restantes x 4 docs d5, nativo, oem por defecto
     python b24_tess.py raster   -> magick declarado vs gs, d4@200 (control) y d5*@nativo
"""
import argparse, hashlib, json, os, statistics, subprocess, sys, time

ROOT = r"D:\Work\research\FileX\.ccb\workspaces\worker1"
BASE = os.path.join(ROOT, r"bench\salidas-k-oem-acantilados")
PDF = os.path.join(ROOT, r"corpus\pdf")
IMG = os.path.join(BASE, "img"); JS = os.path.join(BASE, "json"); TXT = os.path.join(BASE, "texto")
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"
DOCS_D5 = [("escaneado_d5a", 90), ("escaneado_d5c", 80), ("escaneado_d5", 72), ("escaneado_d5b", 60)]
PSM_YA_MEDIDOS = {3, 11}
PSM_RESTANTES = [1, 4, 6, 7, 8, 9, 10, 12, 13]  # 0 y 2 no producen texto comparable (solo OSD)
OEMS = [0, 1, 2, 3]

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
from d4_texto import BLOQUES
REF = [linea for bloque in BLOQUES.values() for linea in bloque]

def run(a, timeout=30, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(a, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=e)

def raster_magick(doc, ppp, dst):
    if not os.path.exists(dst):
        p = run([MAGICK, "-density", str(ppp), os.path.join(PDF, doc+".pdf")+"[0]",
                 "-units", "PixelsPerInch", "-density", str(ppp), "-colorspace", "sRGB",
                 "-alpha", "remove", "-background", "white", "-flatten", dst], timeout=60)
        if p.returncode: raise RuntimeError("magick rc=%s: %s" % (p.returncode, p.stderr[:300]))
    return dst

def tess(path, psm, oem, timeout=20):
    out = os.path.join(BASE, "img", "tmp_out")
    args = [TESS, path, out, "-l", "spa", "--psm", str(psm)]
    if oem is not None:
        args += ["--oem", str(oem)]
    p = run(args, timeout=timeout, env={"TESSDATA_PREFIX": TESSDATA})
    t = open(out+".txt", encoding="utf-8", errors="replace").read() if p.returncode == 0 and os.path.exists(out+".txt") else ""
    return t, p.returncode, p.stderr[:200]

def celda(path, psm, oem, reps=3):
    rcs = []; errs = []; textos = []; times = []
    for _ in range(reps):
        a = time.time(); texto, rc, err = tess(path, psm, oem); times.append(round((time.time()-a)*1000, 1))
        rcs.append(rc); errs.append(err); textos.append(texto)
    texto = textos[-1]; ev = evaluar(texto, "acentos", REF)
    return {"rc": rcs, "error": errs, "n": reps, "determinista": len(set(textos)) == 1,
            "ms_mediana": statistics.median(times), "cer_pct": ev["cer_pct"],
            "chars_salida": ev["chars_salida"], "texto": texto}

def cmd_oem(args):
    rows = []
    for doc, nat in DOCS_D5:
        dst = os.path.join(IMG, f"ppp{nat:03d}__{doc}.png")
        raster_magick(doc, nat, dst)
        for psm in sorted(PSM_YA_MEDIDOS):
            for oem in OEMS:
                c = celda(dst, psm, oem, args.reps)
                row = {"doc": doc, "ppp": nat, "psm": psm, "oem": oem, **c}
                del row["texto"]
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    json.dump({"rows": rows}, open(os.path.join(JS, "b24_oem.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)

def cmd_psm(args):
    rows = []
    for doc, nat in DOCS_D5:
        dst = os.path.join(IMG, f"ppp{nat:03d}__{doc}.png")
        raster_magick(doc, nat, dst)
        for psm in PSM_RESTANTES:
            c = celda(dst, psm, None, args.reps)
            row = {"doc": doc, "ppp": nat, "psm": psm, "oem": "defecto", **c}
            del row["texto"]
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    json.dump({"rows": rows}, open(os.path.join(JS, "b24_psm.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)

def cmd_raster(args):
    casos = [("escaneado_d4", 200), ("escaneado_d5a", 90), ("escaneado_d5c", 80),
             ("escaneado_d5", 72), ("escaneado_d5b", 60)]
    rows = []
    for doc, ppp in casos:
        src = os.path.join(PDF, doc + ".pdf")
        im = os.path.join(IMG, f"raster_im__{doc}.png")
        raster_magick(doc, ppp, im)
        gsp = os.path.join(IMG, f"raster_gs__{doc}.png")
        if not os.path.exists(gsp):
            p = run([GS, "-dNOPAUSE", "-dBATCH", "-dSAFER", "-q", "-sDEVICE=png16m",
                     f"-r{ppp}", "-dFirstPage=1", "-dLastPage=1", f"-sOutputFile={gsp}", src],
                    timeout=120)
            if p.returncode: raise RuntimeError("gs rc=%s: %s" % (p.returncode, p.stderr[:300]))
        dim_im = run([MAGICK, "identify", "-format", "%wx%h %U", im]).stdout.strip()
        dim_gs = run([MAGICK, "identify", "-format", "%wx%h %U", gsp]).stdout.strip()
        pim = subprocess.run([MAGICK, im, "-strip", "rgb:-"], stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        pgs = subprocess.run([MAGICK, gsp, "-strip", "rgb:-"], stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        md5_im = hashlib.md5(pim.stdout).hexdigest(); md5_gs = hashlib.md5(pgs.stdout).hexdigest()
        for psm in (3, 11):
            t_im, rc_im, _ = tess(im, psm, None)
            t_gs, rc_gs, _ = tess(gsp, psm, None)
            ev_im = evaluar(t_im, "acentos", REF); ev_gs = evaluar(t_gs, "acentos", REF)
            row = {"doc": doc, "ppp": ppp, "psm": psm, "dim_magick": dim_im, "dim_gs": dim_gs,
                   "pixeles_iguales": md5_im == md5_gs, "cer_magick": ev_im["cer_pct"],
                   "cer_gs": ev_gs["cer_pct"], "texto_igual": t_im == t_gs}
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    json.dump({"rows": rows}, open(os.path.join(JS, "b24_raster.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["oem", "psm", "raster"])
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()
    os.makedirs(IMG, exist_ok=True); os.makedirs(JS, exist_ok=True); os.makedirs(TXT, exist_ok=True)
    {"oem": cmd_oem, "psm": cmd_psm, "raster": cmd_raster}[args.cmd](args)
