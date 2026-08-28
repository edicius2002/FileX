# -*- coding: utf-8 -*-
"""G5 / B26 — prepara los rasteres del experimento del asignador de VRAM.

Rasteriza con GHOSTSCRIPT (el unico rasterizador de PDF que hay aqui: ImageMagick
delega en el, `magick -list delegate` lo dice — CLAUDE.md trampa 8) a una rejilla de
ppp elegida para barrer megapixeles, y deja un indice con px, Mpx y sha256 de cada
salida.

No se usa `-units PixelsPerInch`: los tres motores de este informe (PaddleOCR,
RapidOCR, EasyOCR) son INMUNES al `pHYs` (trampa 29). Se deja constancia de que la
omision es deliberada y no un olvido.

uso: preparar_op.py <dir_destino>
"""
import hashlib
import json
import os
import subprocess
import sys

GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
PDF = r"D:\Work\research\FileX\corpus\pdf"

# (documento, ppp) — la rejilla barre megapixeles, que es la variable del asignador.
REJILLA = [
    ("escaneado_d4", 100),
    ("escaneado_d4", 150),
    ("escaneado_d4", 200),   # ppp NATIVOS de d4
    ("escaneado_d4", 280),   # el x1,40 que planto a PaddleOCR (k-por-motor.md 6.3)
    ("escaneado_d4", 400),
    ("escaneado_d2", 100),   # ppp nativos, documento pequeno
    ("patologico_escaneado", 200),
]

destino = sys.argv[1]
os.makedirs(destino, exist_ok=True)
indice = []

for doc, ppp in REJILLA:
    src = os.path.join(PDF, doc + ".pdf")
    dst = os.path.join(destino, f"{doc}_r{ppp}.png")
    orden = [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
             "-sDEVICE=pnggray", f"-r{ppp}", "-dFirstPage=1", "-dLastPage=1",
             f"-sOutputFile={dst}", src]
    r = subprocess.run(orden, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(dst):
        indice.append({"doc": doc, "ppp": ppp, "rc": r.returncode,
                       "error": r.stderr[-400:]})
        continue
    # geometria leida de la cabecera PNG en proceso (R: cabeceras en proceso)
    with open(dst, "rb") as f:
        cab = f.read(33)
    ancho = int.from_bytes(cab[16:20], "big")
    alto = int.from_bytes(cab[20:24], "big")
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest()
    indice.append({"doc": doc, "ppp": ppp, "rc": 0, "png": dst,
                   "px_w": ancho, "px_h": alto,
                   "mpx": round(ancho * alto / 1e6, 3),
                   "bytes": os.path.getsize(dst), "sha256": h,
                   "orden": " ".join(orden)})
    print(f"{doc}_r{ppp}: {ancho}x{alto} = {ancho*alto/1e6:.3f} Mpx")

json.dump(indice, open(os.path.join(destino, "indice.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("indice ->", os.path.join(destino, "indice.json"))
