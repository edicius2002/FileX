#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B8(b) -- genera los 20 rasteres del barrido (5 documentos x 2 ppp x
2 deskew), CPU pura, sin tocar la GPU ni el lock.

Familia: escaneado_d4 (-4 grados), d4a (2), d4b (-3), d4c (3), d4e (4) -- las
cinco variantes de 200 ppp nativos que ya vienen en el corpus (MANIFIESTO-d4.md),
cubriendo -4 a +4 grados sin generar nada nuevo. d4f (240 ppp, otro angulo ya
repetido) se deja fuera para no mezclar una escala de ppp distinta en la misma
comparacion.

ppp: nativo (200) y techo x1.4 (280) -- la R1 vigente, sin tocar su forma.

deskew: `magick -deskew 40% +repage` DESPUES de aplanar a gris, antes de
declarar el pHYs. MEDIDO (ver informe): el redimensionado que produce deskew
NO cambia la densidad nominal que magick declara (200x200 antes y despues),
asi que se declara el mismo ppp nominal en las cuatro combinaciones -- no hace
falta recalcularlo, pero SI hay que declararlo (trampa 8/29): -units
PixelsPerInch -density N en el paso que empaqueta a PDF/PNG con pHYs.

uso: python raster_b8.py
"""
import hashlib
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = os.path.join(ROOT, "corpus", "pdf")
BASE = os.path.join(ROOT, "bench", "salidas-deskew-y-fidelidad")
IMG = os.path.join(BASE, "img")
os.makedirs(IMG, exist_ok=True)

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

DOCS = ["escaneado_d4", "escaneado_d4a", "escaneado_d4b", "escaneado_d4c", "escaneado_d4e"]
PPP_NATIVO = 200
PPP_TECHO = 280  # nativo x 1.4, la R1 vigente


def raster(doc, ppp, deskew):
    nombre = f"{doc}__ppp{ppp}__{'deskew' if deskew else 'base'}.png"
    dst = os.path.join(IMG, nombre)
    if os.path.exists(dst):
        return dst
    cmd = [MAGICK, "-density", str(ppp), os.path.join(PDF, doc + ".pdf") + "[0]",
           "-colorspace", "Gray", "-alpha", "remove", "-background", "white", "-flatten"]
    if deskew:
        cmd += ["-deskew", "40%", "+repage"]
    # pHYs declarado, siempre -- el nominal, que MEDIDO no cambia con el deskew.
    cmd += ["-depth", "8", "-units", "PixelsPerInch", "-density", str(ppp), dst]
    p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise RuntimeError(f"magick rc={p.returncode} sobre {nombre}: {p.stderr[:300]}")
    return dst


def main():
    filas = []
    for doc in DOCS:
        for ppp in (PPP_NATIVO, PPP_TECHO):
            for deskew in (False, True):
                dst = raster(doc, ppp, deskew)
                sha = hashlib.sha256(open(dst, "rb").read()).hexdigest()
                tam = os.path.getsize(dst)
                p = subprocess.run([MAGICK, "identify", "-format", "%wx%h", dst],
                                   capture_output=True, text=True)
                geo = p.stdout.strip()
                fila = {"doc": doc, "ppp": ppp, "deskew": deskew,
                        "fichero": os.path.basename(dst), "geometria": geo,
                        "bytes": tam, "sha256": sha}
                filas.append(fila)
                print(json.dumps(fila, ensure_ascii=False))
    json.dump(filas, open(os.path.join(BASE, "rasteres.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)
    print(f"\n{len(filas)} rasteres escritos en {IMG}")


if __name__ == "__main__":
    main()
