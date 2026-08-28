# -*- coding: utf-8 -*-
"""S6 / hito 6 — rasteres para el arnes de coresidencia.

Misma rejilla y mismo rasterizador que `bench/salidas-ocr-produccion/preparar_op.py`
(Ghostscript: ImageMagick delega en el, trampa 8), a proposito, para poder
**comparar los sha256 con el indice que G5 publico**. Si coinciden, la parte de
VRAM de este informe corre sobre exactamente los mismos pixeles que la suya; si no
coinciden, hay que decirlo antes de comparar una sola cifra.

No se usa `-units PixelsPerInch`: los motores de este informe (RapidOCR, EasyOCR,
PaddleOCR) son INMUNES al `pHYs` (trampa 29). La omision es deliberada.

uso: preparar_h6.py <dir_destino>
"""
import hashlib
import json
import os
import subprocess
import sys

GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = os.path.join(RAIZ, "corpus", "pdf")

# (documento, ppp). Los cinco puntos de la recta de G5 mas el documento pequeno.
REJILLA = [
    ("escaneado_d4", 100),   # 0,555 Mpx
    ("escaneado_d4", 150),   # 1,248 Mpx  — la pagina del regimen estacionario
    ("escaneado_d4", 200),   # 2,221 Mpx  — ppp NATIVOS de d4
    ("escaneado_d4", 280),   # 4,352 Mpx
    ("escaneado_d4", 400),   # 8,882 Mpx  — el A4 a 300 ppp equivalente del criterio
    # Los tres documentos de la clausula de precision, **a sus ppp NATIVOS**
    # (`bench/ocr-ppp-nativos.md` §2): 200 el patologico, 150 d1 y 100 d2.
    # d1 es de 150, no de 100 — el error estaba en el enunciado de un encargo,
    # no en el corpus, y ya costo una tabla.
    ("escaneado_d1", 150),
    ("escaneado_d2", 100),
    ("patologico_escaneado", 200),
]

# sha256 publicados por G5 en `bench/salidas-ocr-produccion/img/indice.json`.
# Se comparan, no se suponen: dos rasterizados «con la misma orden» en maquinas o
# worktrees distintos son una hipotesis hasta que el hash lo dice.
SHA_G5 = {
    ("escaneado_d4", 100): "68e8a434f394c461be6ff81af24b7d3fbddce9620732125fe99d79bbd1c00c3f",
    ("escaneado_d4", 150): "e199d9cc5f555253643b48c82457a806126079e7416403206e4e0c5a4dad68ce",
    ("escaneado_d4", 200): "99613281cc45f7a68f6d204a2bcd0df6af4c3884867eb73e76b445a65cf08a7e",
    ("escaneado_d4", 280): "6b145e7b0426febdedc03c9b4684a1262f8c6f407b87a2b442e1b648ef49ea7f",
    ("escaneado_d4", 400): "3d010eaba780bdf03d50796a018410d06f2af4cb2cb89acb330dd30b705275c0",
}

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
    with open(dst, "rb") as f:
        cab = f.read(33)
    ancho = int.from_bytes(cab[16:20], "big")
    alto = int.from_bytes(cab[20:24], "big")
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest()
    esperado = SHA_G5.get((doc, ppp))
    indice.append({"doc": doc, "ppp": ppp, "rc": 0, "png": dst.replace("\\", "/"),
                   "px_w": ancho, "px_h": alto,
                   "mpx": round(ancho * alto / 1e6, 3),
                   "bytes": os.path.getsize(dst), "sha256": h,
                   "sha256_g5": esperado,
                   "coincide_g5": None if esperado is None else (h == esperado),
                   "orden": subprocess.list2cmdline(orden)})

json.dump(indice, open(os.path.join(destino, "indice.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
for e in indice:
    print(json.dumps(e, ensure_ascii=False))
