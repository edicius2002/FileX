# -*- coding: utf-8 -*-
"""G2 — genera el MANIFIESTO.md y BORRA las rasterizaciones.

CLAUDE.md §6: no se versionan salidas binarias regenerables. Se deja nombre, sha256,
tamaño, geometria y **la orden exacta que las reproduce**.

uso: python manifiesto_psm.py [--borrar]
"""
import hashlib
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "img")
TMP = os.path.join(BASE, "tmp")
BORRAR = "--borrar" in sys.argv

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"

ORDENES = {
    "im": 'magick -density <ppp> corpus/pdf/<doc>.pdf[0] -colorspace Gray '
          '-alpha remove -background white -flatten <salida>',
    "im_ppi": 'magick -density <ppp> corpus/pdf/<doc>.pdf[0] -colorspace Gray '
              '-alpha remove -background white -flatten -units PixelsPerInch '
              '-density <ppp> <salida>',
    "im_sincs": 'magick -density <ppp> corpus/pdf/<doc>.pdf[0] -alpha remove '
                '-background white -flatten <salida>',
    "gs": 'gswin64c -dNOPAUSE -dBATCH -dSAFER -q -dFirstPage=1 -dLastPage=1 '
          '-sDEVICE=pnggray -r<ppp> -sOutputFile=<salida> corpus/pdf/<doc>.pdf',
    "gs_aa1": 'gswin64c ... -sDEVICE=pnggray -r<ppp> -dTextAlphaBits=1 '
              '-dGraphicsAlphaBits=1 -sOutputFile=<salida> corpus/pdf/<doc>.pdf',
    "gs_aa4": 'gswin64c ... -sDEVICE=pnggray -r<ppp> -dTextAlphaBits=4 '
              '-dGraphicsAlphaBits=4 -sOutputFile=<salida> corpus/pdf/<doc>.pdf',
    "gs16m_im": 'gswin64c ... -sDEVICE=png16m -r<ppp> -sOutputFile=<tmp> '
                'corpus/pdf/<doc>.pdf  &&  magick <tmp> -colorspace Gray <salida>',
    "gs16m_im601": 'gswin64c ... -sDEVICE=png16m -r<ppp> ...  &&  magick <tmp> '
                   '-intensity Rec601Luma -grayscale Rec601Luma <salida>',
    "gs16m_im709": 'gswin64c ... -sDEVICE=png16m -r<ppp> ...  &&  magick <tmp> '
                   '-intensity Rec709Luma -grayscale Rec709Luma <salida>',
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


geo = {}
fg = os.path.join(BASE, "json", "geometria_psm.json")
if os.path.exists(fg):
    geo = json.load(open(fg, encoding="utf-8"))

filas = []
total = 0
for n in sorted(os.listdir(IMG)) if os.path.isdir(IMG) else []:
    if not n.endswith(".png"):
        continue
    p = os.path.join(IMG, n)
    clave = n[:-4]
    g = geo.get(clave, {})
    t = os.path.getsize(p)
    total += t
    filas.append((clave, g.get("variante", "?"), g.get("doc", "?"),
                  g.get("factor"), g.get("ppp_usado"),
                  "x".join(str(x) for x in g.get("png_px", [])) or "?",
                  g.get("megapixeles"), t, sha(p)))

# scripts y evaluadores: se versionan, solo se listan con su sha256
scripts = []
for n in sorted(os.listdir(BASE)):
    if n.endswith((".py", ".sh", ".md")) and n != "MANIFIESTO.md":
        scripts.append((n, os.path.getsize(os.path.join(BASE, n)),
                        sha(os.path.join(BASE, n))))

out = ["# MANIFIESTO — `bench/salidas-psm/` (agente G2, B17 · B18 · B14)", "",
       "**Las rasterizaciones son binarios regenerables y NO se versionan**",
       "(`CLAUDE.md` §6). Aquí quedan su `sha256`, su tamaño, su geometría y la orden",
       "exacta que las reproduce.", "",
       f"**{len(filas)} ficheros, {total / 1e6:.1f} MB**, borrados al terminar.", "",
       "## 1. Las órdenes exactas", "",
       "Desde `D:\\Work\\research\\FileX\\bench\\salidas-psm`:", "",
       "```", 'python raster_psm.py <variante> <f,f,...> <doc> [doc ...]', "```", "",
       "que ejecuta, por variante:", ""]
for v, o in ORDENES.items():
    out += [f"- **`{v}`** — `{o}`"]
out += ["", "con `<ppp> = round(ppp_nativos × factor)` y `ppp_nativos` leído de la "
        "imagen incrustada del PDF con `pypdfium2` (`raster_psm.geometria`).", "",
        "Y las tandas de OCR:", "", "```",
        'REPS=9 python tess_psm.py "<glob>" "<psm,psm,...>" "<etiqueta>" spa',
        'TESS_DPI=<n> REPS=9 python tess_psm.py ...   # para el eje de resolucion',
        'bash run_bcd.sh                              # tandas B, C y D en serie',
        'python tablas_psm.py                         # tablas.md + json/resumen.json',
        "```", "",
        "**Entorno de las tandas de OCR:** `TESSDATA_PREFIX=C:\\Program Files\\PDFgear"
        "\\tessdata` (16 idiomas, **los puso PDFgear, no este proyecto**), binario "
        "`C:\\Program Files\\Tesseract-OCR\\tesseract.exe` v5.5.0.20241111, "
        "`-l spa`, `stdin=DEVNULL`, `timeout=600` por llamada.", "",
        "## 2. Las rasterizaciones", "",
        "| fichero | variante | documento | factor | ppp | px | Mpx | bytes | sha256 |",
        "|---|---|---|---:|---:|---|---:|---:|---|"]
for f in filas:
    out.append("| `{}.png` | {} | {} | {} | {} | {} | {} | {} | `{}` |".format(
        f[0], f[1], f[2], f"×{f[3]:g}" if f[3] else "?", f[4] or "?", f[5],
        f[6] if f[6] is not None else "?", f[7], f[8]))
out += ["", "## 3. Los ficheros que SÍ se versionan (texto)", "",
        "| fichero | bytes | sha256 |", "|---|---:|---|"]
for n, t, s in scripts:
    out.append(f"| `{n}` | {t} | `{s}` |")
out += ["", "**Copias byte a byte, verificadas:** `ocr_eval_d4.py` y `d4_texto.py` "
        "tienen el mismo `sha256` que los originales de `bench/salidas-corpus-d4/`, y "
        "`ocr_eval_psm.py` el mismo que `bench/salidas-k-motor/ocr_eval_km.py`. "
        "`bench/scripts/ocr_eval.py` **no se ha abierto**.", "",
        "Además, sin listar aquí por volumen: `json/` (resultados por celda y las dos "
        "sondas), `texto/` (la salida literal de OCR de cada celda) y `logs/` (el "
        "registro completo de cada tanda). Son **texto** y se versionan."]

io.open(os.path.join(BASE, "MANIFIESTO.md"), "w", encoding="utf-8").write("\n".join(out))
print(f"escrito MANIFIESTO.md con {len(filas)} rasterizaciones ({total / 1e6:.1f} MB)")

if BORRAR:
    n = 0
    for f in filas:
        os.remove(os.path.join(IMG, f[0] + ".png"))
        n += 1
    if os.path.isdir(TMP):
        for x in os.listdir(TMP):
            os.remove(os.path.join(TMP, x))
        os.rmdir(TMP)
    try:
        os.rmdir(IMG)
    except OSError:
        pass
    print(f"borradas {n} rasterizaciones y el directorio tmp/")
