# -*- coding: utf-8 -*-
"""M1 / B13 — genera MANIFIESTO.md con el sha256, el tamaño y la ORDEN EXACTA que
reproduce cada salida binaria, antes de borrarla (CLAUDE.md §6).

uso: python manifiesto_km.py
"""
import hashlib
import io
import json
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "img")
TMP = os.path.join(BASE, "tmp")
JSN = os.path.join(BASE, "json")
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"


def sha(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def hoja(ruta):
    return os.path.basename(ruta)


geo = json.load(io.open(os.path.join(JSN, "geometria_km.json"), encoding="utf-8"))
L = []
W = L.append

W("# MANIFIESTO — `bench/salidas-k-motor/` (M1 / B13)\n")
W("Las **44 rasterizaciones** y los ficheros intermedios **se han borrado**: son "
  "regenerables y pesaban 76 MB (`CLAUDE.md` §6). Aquí quedan su `sha256`, su tamaño "
  "y la orden exacta que los reproduce.\n")
W("Lo que **sí** queda versionado: los `.py`, los `.sh`, `tablas.md`, `json/` "
  "(resultados), `texto/` (la salida literal de OCR de las 397 celdas) y `logs/`.\n")

W("\n## 1. Cómo se regenera todo, de cero\n")
W("```bash")
W("cd D:/Work/research/FileX/bench/salidas-k-motor")
W("# 1. las 44 rasterizaciones (4 documentos x 11 factores)")
W("../../.venv-ai/Scripts/python.exe preparar_km.py \\")
W("    0.5,0.625,0.75,0.875,1.0,1.125,1.25,1.4,1.6,1.8 \\")
W("    escaneado_d3 escaneado_d4c patologico_escaneado escaneado_d4")
W("../../.venv-ai/Scripts/python.exe preparar_km.py 1.5 \\")
W("    escaneado_d3 escaneado_d4c patologico_escaneado escaneado_d4")
W("# 2. las tandas, en este orden (A y B toman el lock de GPU)")
W("bash run_a_png.sh          # PaddleOCR + RapidOCR x3")
W("bash run_b_easy.sh         # EasyOCR")
W("bash run_d_paddle_resto.sh # las 9 celdas que la guardia de VRAM omitio")
W("bash run_e_resto.sh        # la celda de EasyOCR omitida")
W("bash run_c_docling.sh      # docling defecto + docling R6")
W("bash run_h_easy_resto.sh   # las 23 celdas de EasyOCR omitidas")
W("bash run_f_tesseract.sh    # Tesseract --psm 3   (CPU, sin lock)")
W("bash run_i_tess_psm.sh     # Tesseract --psm 11  (CPU, sin lock)")
W("bash run_g_k150.sh         # el punto x1,50 en las nueve configuraciones")
W("# 3. sonda de diagnostico y tablas")
W("../../.venv-ai/Scripts/python.exe sonda_tess.py")
W("python tablas_km.py")
W("python manifiesto_km.py    # este fichero, y borra los binarios")
W("```\n")

W("\n## 2. Las 44 rasterizaciones (borradas)\n")
W("Todas con **la misma orden** que `bench/salidas-corpus-d4/preparar_img.py` y "
  "`bench/salidas-ppp-norm/preparar_pn.py`, para que las cifras sean comparables "
  "con las celdas ya medidas:\n")
W("```")
W(f'"{MAGICK}" -density <PPP> <corpus/pdf/DOC.pdf>[0] \\')
W("    -colorspace Gray -alpha remove -background white -flatten \\")
W("    img/k<FACTORx1000>__<DOC>.png")
W("```\n")
W("| fichero | documento | factor | ppp | píxeles | bytes | sha256 |")
W("|---|---|---:|---:|---:|---:|---|")
filas = []
for clave, g in sorted(geo.items()):
    ruta = os.path.join(IMG, clave + ".png")
    if not os.path.exists(ruta):
        continue
    filas.append((clave, g, os.path.getsize(ruta), sha(ruta)))
for clave, g, n, h in filas:
    W(f"| `{clave}.png` | `{g.get('doc')}` | ×{g.get('factor')} | {g.get('ppp_usado')} "
      f"| {g['png_px'][0]}×{g['png_px'][1]} | {n} | `{h}` |")

W("\n## 3. Intermedios de la sonda de Tesseract (borrados)\n")
W("Reproducibles con `sonda_tess.py`. La rasterización de Ghostscript es:\n")
W("```")
W(f'"{GS}" -dNOPAUSE -dBATCH -dSAFER -q -sDEVICE=pnggray -r<PPP> \\')
W("    -dFirstPage=1 -dLastPage=1 -sOutputFile=tmp/sonda_gs_<DOC>.png <PDF>")
W("```\n")
W("| fichero | bytes | sha256 |")
W("|---|---:|---|")
tmps = []
if os.path.isdir(TMP):
    for f in sorted(os.listdir(TMP)):
        r = os.path.join(TMP, f)
        if os.path.isfile(r):
            tmps.append((f, os.path.getsize(r), sha(r)))
for f, n, h in tmps:
    W(f"| `tmp/{f}` | {n} | `{h}` |")

W("\n## 4. Lo que se conserva\n")
W("| directorio | qué es | ficheros |")
W("|---|---|---:|")
for d, q in (("json", "resultados de CER por celda, geometría y la sonda de Tesseract"),
             ("texto", "la salida literal de OCR de cada celda"),
             ("logs", "el registro completo de las nueve tandas")):
    ruta = os.path.join(BASE, d)
    n = len(os.listdir(ruta)) if os.path.isdir(ruta) else 0
    W(f"| `{d}/` | {q} | {n} |")

io.open(os.path.join(BASE, "MANIFIESTO.md"), "w", encoding="utf-8",
        newline="\n").write("\n".join(L) + "\n")
print(f"MANIFIESTO.md escrito: {len(filas)} rasterizaciones, {len(tmps)} intermedios")

# --- borrado de los binarios regenerables ---
borrados = 0
octetos = 0
for d in (IMG, TMP):
    if not os.path.isdir(d):
        continue
    for f in os.listdir(d):
        r = os.path.join(d, f)
        if os.path.isfile(r):
            octetos += os.path.getsize(r)
            os.remove(r)
            borrados += 1
    try:
        os.rmdir(d)
    except OSError:
        pass
print(f"borrados {borrados} ficheros, {octetos / 1e6:.1f} MB")
