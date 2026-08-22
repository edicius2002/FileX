# -*- coding: utf-8 -*-
"""G1 / paso 2 — rasteriza los PDF a los ppp que se le pidan, con la MISMA orden de
ImageMagick que uso bench/salidas-ocr-ppp/10_preparar.sh (para que las cifras nuevas
sean comparables con las 296 celdas ya medidas).

uso: python preparar_img.py <ppp|nativo> <doc> [doc ...]
     'nativo' calcula los ppp con la regla R1: ancho_px / (ancho_pt/72), sin techo
     (el techo x1,4 solo aplica cuando se SUBE, y aqui no se sube).
"""
import json
import os
import subprocess
import sys

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
RAIZ = r"D:\Work\research\FileX"
PDF = os.path.join(RAIZ, r"corpus\pdf")
IMG = os.environ.get("IMGDIR", os.path.join(RAIZ, r"bench\salidas-corpus-d4\img"))
TMP = os.path.join(RAIZ, r"bench\salidas-corpus-d4\tmp")
os.makedirs(IMG, exist_ok=True)


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
        return {"ancho_pt": w_pt, "alto_pt": h_pt, "imagen": None}
    return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2),
            "img_px": [mejor[0], mejor[1]],
            "dpi_declarado": [mejor[2], mejor[3]],
            "ppp_calculado": round(mejor[0] / (w_pt / 72.0), 1)}


def raster(doc, ppp):
    src = os.path.join(PDF, doc + ".pdf")
    if not os.path.exists(src):
        src = os.path.join(TMP, doc + ".pdf")
    dst = os.path.join(IMG, f"ppp{ppp}__{doc}.png")
    p = subprocess.run([MAGICK, "-density", str(ppp), src + "[0]", "-colorspace", "Gray",
                        "-alpha", "remove", "-background", "white", "-flatten", dst],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=300)
    if p.returncode != 0:
        raise SystemExit(f"magick fallo: {p.stderr[:300]}")
    dim = subprocess.run([MAGICK, "identify", "-format", "%wx%h", dst],
                         stdin=subprocess.DEVNULL, capture_output=True,
                         text=True).stdout.strip()
    return dst, dim


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    modo = sys.argv[1]
    geo = {}
    for doc in sys.argv[2:]:
        src = os.path.join(PDF, doc + ".pdf")
        if not os.path.exists(src):
            src = os.path.join(TMP, doc + ".pdf")
        g = geometria(src)
        ppp = int(round(g["ppp_calculado"])) if modo == "nativo" else int(modo)
        dst, dim = raster(doc, ppp)
        g["ppp_usado"] = ppp
        g["png"] = os.path.basename(dst)
        g["png_px"] = dim
        geo[doc] = g
        print(f"{doc:20s} pagina={g['ancho_pt']}x{g['alto_pt']}pt  "
              f"img={g.get('img_px')}  dpi_decl={g.get('dpi_declarado')}  "
              f"ppp_calc={g.get('ppp_calculado')}  ->  {os.path.basename(dst)} {dim}")
    fj = os.path.join(RAIZ, r"bench\salidas-corpus-d4\json\geometria_d4.json")
    prev = {}
    if os.path.exists(fj):
        prev = json.load(open(fj, encoding="utf-8"))
    prev.update(geo)
    json.dump(prev, open(fj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
