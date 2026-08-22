# -*- coding: utf-8 -*-
"""M1 / B13 — sonda: ¿por que mi Tesseract da 84,56 % en `d4` a ppp nativos donde P2
midio 51,15 %? Dos variables candidatas, separadas: el RASTERIZADOR (ImageMagick, que
es el del corpus y el de P1, frente a Ghostscript, que es el que uso P2) y el `--psm`.

Es una sonda de diagnostico, n=1, en CPU. No produce ninguna cifra del barrido.

uso: python sonda_tess.py
"""
import io
import json
import os
import subprocess
import sys

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-k-motor")
TMP = os.path.join(BASE, "tmp")
sys.path.insert(0, BASE)
from ocr_eval_km import evaluar, ref_de_nombre  # noqa: E402

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
ENT = dict(os.environ)
ENT["TESSDATA_PREFIX"] = r"C:\Program Files\PDFgear\tessdata"

os.makedirs(TMP, exist_ok=True)
CASOS = [("escaneado_d4", 200), ("escaneado_d3", 100), ("escaneado_d4c", 200)]
out = []

for doc, ppp in CASOS:
    src = os.path.join(RAIZ, "corpus", "pdf", doc + ".pdf")
    # (a) ImageMagick — el rasterizador del corpus, de P1 y de este barrido
    im = os.path.join(TMP, f"sonda_im_{doc}.png")
    subprocess.run([MAGICK, "-density", str(ppp), src + "[0]", "-colorspace", "Gray",
                    "-alpha", "remove", "-background", "white", "-flatten", im],
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=600)
    # (b) Ghostscript — el rasterizador que uso P2
    gsp = os.path.join(TMP, f"sonda_gs_{doc}.png")
    subprocess.run([GS, "-dNOPAUSE", "-dBATCH", "-dSAFER", "-q", "-sDEVICE=pnggray",
                    f"-r{ppp}", "-dFirstPage=1", "-dLastPage=1",
                    f"-sOutputFile={gsp}", src],
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=600)
    for etiqueta, img in (("magick", im), ("ghostscript", gsp)):
        if not os.path.exists(img):
            out.append({"doc": doc, "raster": etiqueta, "error": "no se genero"})
            continue
        dim = subprocess.run([MAGICK, "identify", "-format", "%wx%h %[depth] %[type]",
                              img], stdin=subprocess.DEVNULL, capture_output=True,
                             text=True, timeout=120).stdout.strip()
        for psm in ("3", "4", "6", "11"):
            q = subprocess.run([TESS, img, "stdout", "-l", "spa", "--psm", psm],
                               stdin=subprocess.DEVNULL, capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=600, env=ENT)
            ev = evaluar(q.stdout, ref_de_nombre(doc))
            fila = {"doc": doc, "ppp": ppp, "raster": etiqueta, "png": dim,
                    "psm": psm, "rc": q.returncode, "bytes": len(q.stdout),
                    "cer_acentos": ev["cer_acentos_pct"],
                    "cer_ascii": ev["cer_ascii_pct"]}
            out.append(fila)
            print(f"{doc:16s} {etiqueta:12s} psm={psm:>2s}  {dim:22s} "
                  f"bytes={len(q.stdout):5d}  CERac={ev['cer_acentos_pct']:6.2f}%",
                  flush=True)

json.dump(out, io.open(os.path.join(BASE, "json", "sonda_tess.json"), "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)
print("escrito json/sonda_tess.json")
