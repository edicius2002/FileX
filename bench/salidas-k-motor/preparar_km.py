# -*- coding: utf-8 -*-
"""M1 / B13 — rasterizado por FACTOR SOBRE EL RASTER NATIVO, no por ppp absolutos.

COPIA ADAPTADA de bench/salidas-ppp-norm/preparar_pn.py (que a su vez copia
bench/salidas-corpus-d4/preparar_img.py). Los originales NO se tocan.

Por que cambia la unidad: bench/ppp-y-normalizacion.md §2.4 midio que los ppp NO son
la unidad —el mismo JPEG en paginas de 100/200/400 ppp da 19,13 / 19,63 / 36,24 % al
MISMO numero de ppp y coincide a la centesima al MISMO numero de pixeles—. El `k` que
este encargo caracteriza es un FACTOR, asi que el barrido se hace en factores y se
registran los ppp y los PIXELES resultantes.

La orden de ImageMagick es LA MISMA que usaron preparar_img.py y preparar_pn.py, para
que las cifras sean comparables con las celdas ya medidas.

uso: python preparar_km.py <f,f,...> <doc> [doc ...]
env: IMGDIR
"""
import json
import os
import subprocess
import sys

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
RAIZ = r"D:\Work\research\FileX"
PDF = os.path.join(RAIZ, r"corpus\pdf")
BASE = os.path.join(RAIZ, r"bench\salidas-k-motor")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
os.makedirs(IMG, exist_ok=True)
os.makedirs(os.path.join(BASE, "json"), exist_ok=True)

# Tope de presupuesto: barrer hasta 400 ppp llevo a PaddleOCR a 11 942 y a EasyOCR a
# 12 037 de 12 288 MiB SIN dar error (ppp-y-normalizacion.md §7). Se rechaza cualquier
# rasterizacion cuyo lado largo pase de aqui.
TOPE_LADO_PX = int(os.environ.get("TOPE_LADO_PX", "3400"))


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


def raster(doc, factor, ppp, src):
    dst = os.path.join(IMG, f"k{int(round(factor * 1000)):04d}__{doc}.png")
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
    factores = [float(x) for x in sys.argv[1].split(",")]
    geo = {}
    for doc in sys.argv[2:]:
        src = os.path.join(PDF, doc + ".pdf")
        g = geometria(src)
        nat = g["ppp_calculado"]
        for f in factores:
            ppp = int(round(nat * f))
            dst, dim = raster(doc, f, ppp, src)
            w, h = (int(x) for x in dim.split("x"))
            clave = os.path.splitext(os.path.basename(dst))[0]
            if max(w, h) > TOPE_LADO_PX:
                os.remove(dst)
                print(f"{doc:24s} f={f:5.3f} ppp={ppp:4d} -> {dim} px  "
                      f"RECHAZADO por tope de VRAM ({TOPE_LADO_PX} px)")
                geo[clave] = {"omitido": "tope_lado_px", "px": [w, h], "factor": f,
                              "ppp_usado": ppp, "doc": doc}
                continue
            geo[clave] = dict(g, doc=doc, factor=f, ppp_usado=ppp,
                              png=os.path.basename(dst), png_px=[w, h],
                              megapixeles=round(w * h / 1e6, 3))
            print(f"{doc:24s} f={f:5.3f} ppp={ppp:4d} nativos={nat} "
                  f"pagina={g['ancho_pt']}x{g['alto_pt']}pt  ->  {dim} px "
                  f"({w * h / 1e6:.2f} Mpx)")
    fj = os.path.join(BASE, "json", "geometria_km.json")
    prev = json.load(open(fj, encoding="utf-8")) if os.path.exists(fj) else {}
    prev.update(geo)
    json.dump(prev, open(fj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
