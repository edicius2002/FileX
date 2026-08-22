#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera los ficheros de prueba que el corpus NO tiene y que hacen falta para
ejercitar la cobertura nueva de min(alfa): TIFF comprimido con alfa, GIF con
transparencia REAL usada, y PNG entrelazado (Adam7).

No toca corpus/ ni bench/salidas-referencia/: todo va a fixtures/.
Las ordenes exactas quedan registradas en MANIFIESTO.md.
"""
import hashlib
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
FIX = os.path.join(AQUI, "fixtures")
ALPHA = os.path.join(RAIZ, "corpus", "imagen", "alpha.png")
TIPICO = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
GIFPAL = os.path.join(RAIZ, "bench", "salidas-referencia", "video",
                      "trivial_mp4-to-palette.gif")

# (nombre, orden). La orden se ejecuta SIN shell, con argv en lista.
ORDENES = [
    # --- TIFF con ExtraSamples, cuatro compresiones -----------------------
    ("alpha_tiff_none.tif",
     ["magick", ALPHA, "-define", "tiff:alpha=unassociated",
      "-compress", "None", "TIFF:%s"]),
    ("alpha_tiff_lzw.tif",
     ["magick", ALPHA, "-define", "tiff:alpha=unassociated",
      "-compress", "LZW", "TIFF:%s"]),
    ("alpha_tiff_lzw_pred.tif",
     ["magick", ALPHA, "-define", "tiff:alpha=unassociated",
      "-define", "tiff:predictor=2", "-compress", "LZW", "TIFF:%s"]),
    ("alpha_tiff_zip.tif",
     ["magick", ALPHA, "-define", "tiff:alpha=unassociated",
      "-compress", "Zip", "TIFF:%s"]),
    ("alpha_tiff_zip_pred.tif",
     ["magick", ALPHA, "-define", "tiff:alpha=unassociated",
      "-define", "tiff:predictor=2", "-compress", "Zip", "TIFF:%s"]),
    ("alpha_tiff_rle.tif",
     ["magick", ALPHA, "-define", "tiff:alpha=unassociated",
      "-compress", "RLE", "TIFF:%s"]),
    ("alpha_tiff_planar.tif",
     ["magick", ALPHA, "-define", "tiff:alpha=unassociated",
      "-interlace", "Plane", "-compress", "LZW", "TIFF:%s"]),
    # opaco: el control que NO debe dar alfa no trivial
    ("tipico_tiff_lzw.tif",
     ["magick", TIPICO, "-define", "tiff:alpha=unassociated",
      "-compress", "LZW", "TIFF:%s"]),
    # 16 bits con alfa
    ("alpha_tiff_lzw16.tif",
     ["magick", ALPHA, "-depth", "16", "-define", "tiff:alpha=unassociated",
      "-compress", "LZW", "TIFF:%s"]),
    # peor caso: 1920x1080 RGBA de 16 bits, opaco, comprimido
    ("tipico_tiff_zip16.tif",
     ["magick", TIPICO, "-define", "tiff:alpha=unassociated",
      "-compress", "Zip", "TIFF:%s"]),
    # --- GIF ---------------------------------------------------------------
    ("alpha_gif.gif", ["magick", ALPHA, "GIF:%s"]),
    ("trivial_gif_opaco.gif",
     ["magick", os.path.join(RAIZ, "corpus", "imagen", "trivial.png"), "GIF:%s"]),
    ("tipico_gif_opaco.gif", ["magick", TIPICO, "-alpha", "off", "GIF:%s"]),
    # --- PNG entrelazado (Adam7) -------------------------------------------
    ("alpha_adam7.png", ["magick", ALPHA, "-interlace", "PNG", "PNG:%s"]),
    ("alpha_adam7_rgba.png",
     ["magick", ALPHA, "-define", "png:color-type=6", "-define", "png:bit-depth=8",
      "-interlace", "PNG", "PNG:%s"]),
    ("alpha_adam7_rgba16.png",
     ["magick", ALPHA, "-define", "png:color-type=6", "-define", "png:bit-depth=16",
      "-interlace", "PNG", "PNG:%s"]),
    ("alpha_adam7_4b.png",
     ["magick", ALPHA, "-colors", "12", "-define", "png:color-type=3",
      "-define", "png:bit-depth=4", "-interlace", "PNG", "PNG:%s"]),
    ("tipico_adam7.png",
     ["magick", TIPICO, "-interlace", "PNG", "PNG:%s"]),
    ("tipico_adam7_8b.png",
     ["magick", TIPICO, "-depth", "8", "-interlace", "PNG", "PNG:%s"]),
]


def main():
    man = []
    for nombre, orden in ORDENES:
        dst = os.path.join(FIX, nombre)
        cmd = [x % dst if "%s" in x else x for x in orden]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                           stdin=subprocess.DEVNULL)
        ok = p.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 0
        h = ""
        if ok:
            h = hashlib.sha256(open(dst, "rb").read()).hexdigest()
        man.append({"nombre": nombre, "orden": cmd, "rc": p.returncode,
                    "bytes": os.path.getsize(dst) if os.path.exists(dst) else 0,
                    "sha256": h, "err": (p.stderr or "").strip()[:200]})
        print("%-26s rc=%d %10d B  %s" % (nombre, p.returncode,
                                          man[-1]["bytes"], man[-1]["err"][:60]))
    # el GIF animado con paleta del patron oro se COPIA a la lista, no se genera
    with open(os.path.join(AQUI, "fixtures.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
