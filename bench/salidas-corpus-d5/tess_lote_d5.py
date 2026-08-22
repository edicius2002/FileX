# -*- coding: utf-8 -*-
"""G3 / paso 2 — validacion del corpus d5 con Tesseract (CPU).

Por que Tesseract y solo Tesseract
----------------------------------
El encargo de G3 es CONSTRUIR corpus, no medirlo: el barrido de los nueve motores lo
hara otro agente. Pero un corpus sin validar no vale nada — `patologico_escaneado` es
la prueba: 88 de 99 celdas a 0,00 % de CER. Tesseract es CPU, no toca la GPU, no toma
el lock y basta para responder las tres preguntas del encargo:
   (1) ¿da 0,00 % en TODAS las configuraciones?  -> si, no sirve
   (2) ¿los cuatro tamaños de letra dan cifras distintas? -> si no, no hay gradiente
   (3) ¿los ppp nativos son los declarados?      -> se leen del PDF, no se suponen

Disciplina:
  * `TESSDATA_PREFIX` a C:\\Program Files\\PDFgear\\tessdata (donde vive `spa`).
  * El idioma sale de LISTA BLANCA, nunca de la entrada (CLAUDE.md trampa 18).
  * `stdin=DEVNULL`, `timeout` explicito y `cwd` desechable en toda invocacion.
  * Evaluador: `ocr_eval_d4.py`, copia BYTE A BYTE de bench/salidas-corpus-d4/.
    `bench/scripts/ocr_eval.py` NO se usa y NO se toca: es ciego a las tildes.
  * DOS rasterizadores (ImageMagick y Ghostscript), porque `bench/k-por-motor.md` §6.2
    mide que el rasterizador vale 33 puntos de CER en Tesseract. Ninguna cifra de este
    informe se publica sin decir con cual se rasterizo.

uso: python tess_lote_d5.py <etiqueta_tanda> <doc>:<ppp|nativo> [...]
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ocr_eval_d4 import evaluar  # noqa: E402

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-corpus-d5")
TMP = os.path.join(BASE, "tmp")
IMG = os.path.join(BASE, "img")
PDF_CORPUS = os.path.join(RAIZ, r"corpus\pdf")

IDIOMAS = ("spa", "eng")          # LISTA BLANCA. Nada mas entra aqui.
PSM = (3, 6, 11)

os.makedirs(IMG, exist_ok=True)


def _run(args, timeout=600, env=None, cwd=TMP):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, env=e, cwd=cwd)


def ruta_pdf(doc):
    for d in (PDF_CORPUS, TMP):
        p = os.path.join(d, doc + ".pdf")
        if os.path.exists(p):
            return p
    raise SystemExit(f"no encuentro {doc}.pdf")


def geometria(ruta):
    """ppp NATIVOS leidos del PDF, no supuestos: ancho en px de la imagen incrustada
    dividido por el ancho de pagina en pulgadas."""
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(ruta)
    p = d[0]
    w_pt, h_pt = p.get_size()
    mejor = None
    for obj in p.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)):
        try:
            m = obj.get_metadata()
            if mejor is None or m.width * m.height > mejor[0] * mejor[1]:
                mejor = (m.width, m.height, m.horizontal_dpi, m.vertical_dpi)
        except Exception:
            pass
    d.close()
    if mejor is None:
        return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2), "imagen": None}
    return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2),
            "img_px": [mejor[0], mejor[1]], "dpi_declarado": [mejor[2], mejor[3]],
            "ppp_calculado": round(mejor[0] / (w_pt / 72.0), 1)}


def raster(doc, ppp, motor="magick"):
    dst = os.path.join(IMG, f"{motor}_ppp{ppp}__{doc}.png")
    src = ruta_pdf(doc)
    if motor == "magick":
        p = _run([MAGICK, "-density", str(ppp), src + "[0]", "-colorspace", "Gray",
                  "-alpha", "remove", "-background", "white", "-flatten", dst])
    else:
        p = _run([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=pnggray",
                  f"-r{ppp}", "-dFirstPage=1", "-dLastPage=1",
                  f"-sOutputFile={dst}", src])
    if p.returncode != 0:
        raise SystemExit(f"{motor} fallo: {p.stderr[:300]}")
    dim = _run([MAGICK, "identify", "-format", "%wx%h", dst]).stdout.strip()
    return dst, dim


def ocr(png, psm, lang):
    if lang not in IDIOMAS:
        raise SystemExit(f"idioma fuera de lista blanca: {lang!r}")
    salida = os.path.join(TMP, "tess_out")
    t0 = time.perf_counter()
    p = _run([TESS, png, salida, "-l", lang, "--psm", str(psm)],
             timeout=600, env={"TESSDATA_PREFIX": TESSDATA})
    ms = (time.perf_counter() - t0) * 1000
    if p.returncode != 0:
        return None, ms, p.stderr[:200]
    txt = open(salida + ".txt", encoding="utf-8", errors="replace").read()
    return txt, ms, None


def celda(doc, ppp, motor, psm, lang, texto_dir):
    png, dim = raster(doc, ppp, motor)
    txt, ms, err = ocr(png, psm, lang)
    if txt is None:
        return {"doc": doc, "ppp": ppp, "raster": motor, "psm": psm, "lang": lang,
                "error": err}
    nom = f"{doc}__{motor}__ppp{ppp}__psm{psm}__{lang}.txt"
    open(os.path.join(texto_dir, nom), "w", encoding="utf-8").write(txt)
    r = evaluar(txt, "d4")
    fila = {"doc": doc, "ppp": ppp, "raster": motor, "psm": psm, "lang": lang,
            "px": dim, "ms": round(ms, 1),
            "cer_acentos": r["cer_acentos_pct"], "cer_ascii": r["cer_ascii_pct"],
            "acentos": f"{r['acentos_salida']}/{r['acentos_ref']}",
            "lineas_exactas": f"{r['lineas_exactas']}/{r['lineas_totales']}",
            "bloques": {k: (v["cer_pct"] if v else None)
                        for k, v in r["bloques"].items()},
            "txt": nom}
    return fila


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    etiqueta = sys.argv[1]
    texto_dir = os.path.join(BASE, "texto")
    os.makedirs(texto_dir, exist_ok=True)
    rasterizadores = os.environ.get("RASTER", "magick").split(",")
    psms = [int(x) for x in os.environ.get("PSM", "3,11").split(",")]
    langs = os.environ.get("LANGS", "spa").split(",")

    filas = []
    for spec in sys.argv[2:]:
        doc, _, modo = spec.partition(":")
        g = geometria(ruta_pdf(doc))
        nat = int(round(g.get("ppp_calculado") or 0))
        ppp = nat if modo in ("", "nativo") else int(modo)
        for motor in rasterizadores:
            for psm in psms:
                for lang in langs:
                    f = celda(doc, ppp, motor, psm, lang, texto_dir)
                    f["ppp_nativo"] = nat
                    f["geometria"] = g
                    filas.append(f)
                    b = f.get("bloques", {})
                    print(f"{doc:16s} {motor:7s} ppp={ppp:3d}(nat {nat:3d}) "
                          f"psm={psm:2d} {lang} px={f.get('px','-'):10s} "
                          f"CER={f.get('cer_acentos','-'):>6} "
                          f"bloques="
                          f"{b.get('titulo')}/{b.get('subtitulo')}/"
                          f"{b.get('cuerpo')}/{b.get('pequeña')}")
    fj = os.path.join(BASE, "json", f"tess_{etiqueta}.json")
    json.dump(filas, open(fj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n-> {fj}  ({len(filas)} celdas)")


if __name__ == "__main__":
    main()
