# -*- coding: utf-8 -*-
"""P1 / rasterizado a ppp arbitrarios, con la MISMA orden de ImageMagick que usaron
bench/salidas-ocr-ppp/10_preparar.sh y bench/salidas-corpus-d4/preparar_img.py, para
que las cifras del barrido sean comparables con las 296 + 28 celdas ya medidas.

COPIA ADAPTADA de bench/salidas-corpus-d4/preparar_img.py. El original NO se toca.

Cambios: BASE apunta a bench/salidas-ppp-norm/, acepta una LISTA de ppp separada por
comas, y registra el ancho en PIXELES resultante — que es la variable que este informe
tiene que separar de los ppp.

uso: python preparar_pn.py <ppp[,ppp,...]|nativo> <doc> [doc ...]
env: IMGDIR
"""
import json
import os
import subprocess
import sys

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
RAIZ = r"D:\Work\research\FileX"
PDF = os.path.join(RAIZ, r"corpus\pdf")
BASE = os.path.join(RAIZ, r"bench\salidas-ppp-norm")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
os.makedirs(IMG, exist_ok=True)
os.makedirs(os.path.join(BASE, "json"), exist_ok=True)


def geometria(ruta):
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(ruta)
    p = d[0]
    w_pt, h_pt = p.get_size()
    mejor = None
    for obj in p.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)):
        try:
            m = obj.get_metadata()
            px = m.width * m.height
            if mejor is None or px > mejor[0] * mejor[1]:
                mejor = (m.width, m.height, m.horizontal_dpi, m.vertical_dpi)
        except Exception:
            pass
    d.close()
    if mejor is None:
        return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2), "img_px": None,
                "ppp_calculado": None}
    return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2),
            "img_px": [mejor[0], mejor[1]],
            "dpi_declarado": [mejor[2], mejor[3]],
            "ppp_calculado": round(mejor[0] / (w_pt / 72.0), 1)}


def raster(doc, ppp, src):
    dst = os.path.join(IMG, f"ppp{ppp:04d}__{doc}.png")
    p = subprocess.run([MAGICK, "-density", str(ppp), src + "[0]", "-colorspace", "Gray",
                        "-alpha", "remove", "-background", "white", "-flatten", dst],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=600)
    if p.returncode != 0:
        raise SystemExit(f"magick fallo: {p.stderr[:300]}")
    dim = subprocess.run([MAGICK, "identify", "-format", "%wx%h", dst],
                         stdin=subprocess.DEVNULL, capture_output=True,
                         text=True, timeout=120).stdout.strip()
    return dst, dim


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    modo = sys.argv[1]
    geo = {}
    for doc in sys.argv[2:]:
        src = os.path.join(PDF, doc + ".pdf")
        if not os.path.exists(src):
            src = os.path.join(BASE, "tmp", doc + ".pdf")
        g = geometria(src)
        pppl = ([int(round(g["ppp_calculado"]))] if modo == "nativo"
                else [int(x) for x in modo.split(",")])
        for ppp in pppl:
            dst, dim = raster(doc, ppp, src)
            w, h = (int(x) for x in dim.split("x"))
            clave = f"ppp{ppp:04d}__{doc}"
            geo[clave] = dict(g, ppp_usado=ppp, png=os.path.basename(dst),
                              png_px=[w, h],
                              factor_sobre_nativo=(round(ppp / g["ppp_calculado"], 3)
                                                   if g.get("ppp_calculado") else None))
            print(f"{doc:24s} ppp={ppp:4d} pagina={g['ancho_pt']}x{g['alto_pt']}pt "
                  f"nativos={g.get('ppp_calculado')} factor="
                  f"{geo[clave]['factor_sobre_nativo']}  ->  {dim} px")
    fj = os.path.join(BASE, "json", "geometria_pn.json")
    prev = json.load(open(fj, encoding="utf-8")) if os.path.exists(fj) else {}
    prev.update(geo)
    json.dump(prev, open(fj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
