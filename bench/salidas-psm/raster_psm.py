# -*- coding: utf-8 -*-
"""G2 / B17-B18 — rasterizado por FACTOR sobre el raster nativo, con el RASTERIZADOR
como variable explicita.

Copia adaptada de bench/salidas-k-motor/preparar_km.py (M1), que a su vez copia
bench/salidas-ppp-norm/preparar_pn.py. Los originales NO se tocan.

Que cambia frente al de M1: el rasterizador deja de estar cableado. M1 midio en
`k-por-motor.md` §6.2 que ImageMagick y Ghostscript dan 33,22 puntos de CER de
diferencia sobre `escaneado_d4` CON LA MISMA GEOMETRIA Y LA MISMA PROFUNDIDAD. Aqui se
barren VARIANTES para localizar en que paso del camino nace esa diferencia. No se
deduce del codigo: se sondea en ejecucion (CLAUDE.md §5).

Variantes (todas producen PNG en escala de grises de 8 bits, misma geometria):
  im          magick -density D src[0] -colorspace Gray -alpha remove -flatten
              ^ LA DEL CORPUS, de P1 y de M1. ImageMagick NO tiene rasterizador de PDF:
                delega en Ghostscript. Por eso esta variante y `gs` comparten renderer.
                Escribe `pHYs unit=0` (SIN UNIDAD): el PNG no declara resolucion.
  im_ppi      la misma + `-units PixelsPerInch -density D` al final, que hace que el
              PNG lleve `pHYs unit=1`. MISMOS PIXELES que `im`, distinto metadato.
  gs          gswin64c -sDEVICE=pnggray -rD
              ^ la que uso P2 y la de la via de contenedor.
  gs16m       gswin64c -sDEVICE=png16m -rD   (RGB, sin convertir a gris)
  gs16m_im    gs16m + magick -colorspace Gray  (aisla: renderer=gs, gris=IM)
  gs16m_im601 gs16m + magick -intensity Rec601Luma -grayscale Rec601Luma
  gs16m_im709 gs16m + magick -intensity Rec709Luma -grayscale Rec709Luma
  im_sincs    magick -density D src[0] -alpha remove -flatten  (sin -colorspace Gray)
  gs_aa1      gs pnggray con -dTextAlphaBits=1 -dGraphicsAlphaBits=1
  gs_aa4      gs pnggray con -dTextAlphaBits=4 -dGraphicsAlphaBits=4

uso: python raster_psm.py <variante> <f,f,...> <doc> [doc ...]
env: IMGDIR TOPE_LADO_PX
"""
import json
import os
import subprocess
import sys

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
RAIZ = r"D:\Work\research\FileX"
PDF = os.path.join(RAIZ, r"corpus\pdf")
BASE = os.path.join(RAIZ, r"bench\salidas-psm")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
TMP = os.path.join(BASE, "tmp")
os.makedirs(IMG, exist_ok=True)
os.makedirs(TMP, exist_ok=True)
os.makedirs(os.path.join(BASE, "json"), exist_ok=True)

TOPE_LADO_PX = int(os.environ.get("TOPE_LADO_PX", "3400"))
TMO = 600


def run(args):
    p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=TMO)
    if p.returncode != 0:
        raise SystemExit(f"fallo rc={p.returncode}: {args[0]}\n{p.stderr[:400]}")
    return p


def geometria(ruta):
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(ruta)
    p = d[0]
    w_pt, h_pt = p.get_size()
    mejor = None
    for obj in p.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)):
        try:
            m = obj.get_metadata()
            if mejor is None or m.width * m.height > mejor[0] * mejor[1]:
                mejor = (m.width, m.height)
        except Exception:
            pass
    d.close()
    if mejor is None:
        return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2),
                "img_px": None, "ppp_calculado": None}
    return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2),
            "img_px": [mejor[0], mejor[1]],
            "ppp_calculado": round(mejor[0] / (w_pt / 72.0), 1)}


GS_BASE = [GS, "-dNOPAUSE", "-dBATCH", "-dSAFER", "-q",
           "-dFirstPage=1", "-dLastPage=1"]


def rasterizar(variante, src, ppp, dst):
    if variante == "im":
        run([MAGICK, "-density", str(ppp), src + "[0]", "-colorspace", "Gray",
             "-alpha", "remove", "-background", "white", "-flatten", dst])
    elif variante == "im_ppi":
        run([MAGICK, "-density", str(ppp), src + "[0]", "-colorspace", "Gray",
             "-alpha", "remove", "-background", "white", "-flatten",
             "-units", "PixelsPerInch", "-density", str(ppp), dst])
    elif variante == "im_sincs":
        run([MAGICK, "-density", str(ppp), src + "[0]",
             "-alpha", "remove", "-background", "white", "-flatten", dst])
    elif variante == "gs":
        run(GS_BASE + ["-sDEVICE=pnggray", f"-r{ppp}", f"-sOutputFile={dst}", src])
    elif variante == "gs_aa1":
        run(GS_BASE + ["-sDEVICE=pnggray", f"-r{ppp}", "-dTextAlphaBits=1",
                       "-dGraphicsAlphaBits=1", f"-sOutputFile={dst}", src])
    elif variante == "gs_aa4":
        run(GS_BASE + ["-sDEVICE=pnggray", f"-r{ppp}", "-dTextAlphaBits=4",
                       "-dGraphicsAlphaBits=4", f"-sOutputFile={dst}", src])
    elif variante == "gs16m":
        run(GS_BASE + ["-sDEVICE=png16m", f"-r{ppp}", f"-sOutputFile={dst}", src])
    elif variante in ("gs16m_im", "gs16m_im601", "gs16m_im709"):
        inter = os.path.join(TMP, "inter_" + os.path.basename(dst))
        run(GS_BASE + ["-sDEVICE=png16m", f"-r{ppp}", f"-sOutputFile={inter}", src])
        if variante == "gs16m_im":
            run([MAGICK, inter, "-colorspace", "Gray", dst])
        elif variante == "gs16m_im601":
            run([MAGICK, inter, "-intensity", "Rec601Luma",
                 "-grayscale", "Rec601Luma", dst])
        else:
            run([MAGICK, inter, "-intensity", "Rec709Luma",
                 "-grayscale", "Rec709Luma", dst])
        os.remove(inter)
    else:
        raise SystemExit(f"variante desconocida: {variante}")
    dim = subprocess.run([MAGICK, "identify", "-format", "%wx%h %[depth] %[type]", dst],
                         stdin=subprocess.DEVNULL, capture_output=True, text=True,
                         timeout=120).stdout.strip()
    return dim


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    variante = sys.argv[1]
    factores = [float(x) for x in sys.argv[2].split(",")]
    geo = {}
    for doc in sys.argv[3:]:
        src = os.path.join(PDF, doc + ".pdf")
        g = geometria(src)
        nat = g["ppp_calculado"]
        for f in factores:
            ppp = int(round(nat * f))
            clave = f"{variante}__k{int(round(f * 1000)):04d}__{doc}"
            dst = os.path.join(IMG, clave + ".png")
            dim = rasterizar(variante, src, ppp, dst)
            w, h = (int(x) for x in dim.split(" ")[0].split("x"))
            if max(w, h) > TOPE_LADO_PX:
                os.remove(dst)
                geo[clave] = {"omitido": "tope_lado_px", "px": [w, h], "factor": f,
                              "ppp_usado": ppp, "doc": doc, "variante": variante}
                print(f"{clave:46s} {dim:24s} RECHAZADO tope {TOPE_LADO_PX}px")
                continue
            geo[clave] = dict(g, doc=doc, variante=variante, factor=f, ppp_usado=ppp,
                              png=clave + ".png", png_px=[w, h], identify=dim,
                              bytes=os.path.getsize(dst),
                              megapixeles=round(w * h / 1e6, 3))
            print(f"{clave:46s} ppp={ppp:4d} nat={nat}  {dim:24s} "
                  f"({w * h / 1e6:.2f} Mpx, {os.path.getsize(dst)} B)", flush=True)
    fj = os.path.join(BASE, "json", "geometria_psm.json")
    prev = json.load(open(fj, encoding="utf-8")) if os.path.exists(fj) else {}
    prev.update(geo)
    json.dump(prev, open(fj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
