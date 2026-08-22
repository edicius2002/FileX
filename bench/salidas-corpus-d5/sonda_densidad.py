# -*- coding: utf-8 -*-
"""G3 / sonda — ¿el "efecto del rasterizador" son los pixeles o la CABECERA?

`bench/k-por-motor.md` §6.2 midio que el RASTERIZADOR vale 33 puntos de CER en
Tesseract: 84,56 % desde ImageMagick y 51,34 % desde Ghostscript sobre `escaneado_d4`,
"misma geometria (1294x1716) y misma profundidad".

Al reproducirlo aparecio algo que no encaja: los dos PNG tienen el MISMO sha256 de
pixeles crudos. Si los pixeles son identicos, la diferencia no puede estar en ellos.

Lo que si difiere es la cabecera:
    ImageMagick -> unidades = Undefined, densidad 200
    Ghostscript -> unidades = PixelsPerCentimeter, densidad 78,74 (= 200 ppp)

Tesseract/Leptonica leen el chunk pHYs del PNG. Sin unidades validas no hay ppp que
leer y Tesseract cae a su valor por defecto.

Esta sonda hace el A/B minimo: coge el PNG de ImageMagick y le escribe la densidad
en pulgadas SIN TOCAR UN PIXEL, y comprueba (a) que el sha256 de los pixeles no
cambia y (b) que el CER se mueve.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ocr_eval_d4 import evaluar  # noqa: E402

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"
BASE = r"D:\Work\research\FileX\bench\salidas-corpus-d5"
IMG = os.path.join(BASE, "img")
TMP = os.path.join(BASE, "tmp")

CASOS = [("escaneado_d4", 200), ("patologico_d5", 200), ("patologico_d5b", 200),
         ("realista_d5", 200), ("realista_d5b", 200), ("realista_d5e", 200),
         ("escaneado_d5", 72), ("escaneado_d5b", 60)]


def run(args, env=None, timeout=600):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, env=e, cwd=TMP)


def sha_pixeles(png):
    p = subprocess.run([MAGICK, png, "-depth", "8", "gray:-"],
                       stdin=subprocess.DEVNULL, capture_output=True, timeout=300,
                       cwd=TMP)
    return hashlib.sha256(p.stdout).hexdigest()


def cabecera(png):
    return run([MAGICK, "identify", "-format", "%x|%y|%U", png]).stdout.strip()


def ocr(png, psm=3, lang="spa"):
    salida = os.path.join(TMP, "sonda_dens")
    p = run([TESS, png, salida, "-l", lang, "--psm", str(psm)],
            env={"TESSDATA_PREFIX": TESSDATA})
    if p.returncode != 0:
        return None, p.stderr[:200]
    return open(salida + ".txt", encoding="utf-8", errors="replace").read(), p.stderr


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    filas = []
    for doc, ppp in CASOS:
        m = os.path.join(IMG, f"magick_ppp{ppp}__{doc}.png")
        g = os.path.join(IMG, f"gs_ppp{ppp}__{doc}.png")
        if not (os.path.exists(m) and os.path.exists(g)):
            print(f"[falta] {doc}")
            continue
        # B: el PNG de ImageMagick con la densidad escrita en pulgadas.
        b = os.path.join(IMG, f"magickdpi_ppp{ppp}__{doc}.png")
        run([MAGICK, m, "-units", "PixelsPerInch", "-density", str(ppp), b])
        shas = {k: sha_pixeles(v) for k, v in (("A_magick", m), ("B_magick_dpi", b),
                                               ("C_gs", g))}
        for psm in (3, 11):
            res = {}
            for etq, png in (("A_magick", m), ("B_magick_dpi", b), ("C_gs", g)):
                txt, _ = ocr(png, psm)
                res[etq] = round(evaluar(txt, "d4")["cer_acentos_pct"], 2) \
                    if txt is not None else None
            fila = {"doc": doc, "ppp": ppp, "psm": psm, "cer": res,
                    "pixeles_identicos": len(set(shas.values())) == 1,
                    "sha_pixeles": shas,
                    "cabecera": {k: cabecera(v) for k, v in
                                 (("A_magick", m), ("B_magick_dpi", b), ("C_gs", g))}}
            filas.append(fila)
            print(f"{doc:16s} ppp={ppp:3d} psm={psm:2d}  "
                  f"A_magick={res['A_magick']:>6}  B_magick_dpi={res['B_magick_dpi']:>6}"
                  f"  C_gs={res['C_gs']:>6}   pixeles_identicos="
                  f"{fila['pixeles_identicos']}")
        os.remove(b)
    json.dump(filas, open(os.path.join(BASE, "json", "sonda_densidad.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n-> json/sonda_densidad.json ({len(filas)} celdas)")


if __name__ == "__main__":
    main()
