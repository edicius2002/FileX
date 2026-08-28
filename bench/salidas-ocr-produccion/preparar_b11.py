# -*- coding: utf-8 -*-
"""G5 / B11 — rasteriza el corpus del A/B de configuracion de RapidOCR.

A **ppp NATIVOS**, que es lo que hizo `bench/ppp-y-normalizacion.md` 3.3 y lo que
mantiene la comparacion limpia: la variable de este A/B es el par (checkpoint,
normalizacion), y los ppp tienen que ser una CONSTANTE entre las dos ramas. No se
aplica la regla R1 `max(min(n*1,25, techo), 100)` a proposito: aplicarla movería
dos cosas a la vez.

Los ppp nativos NO se inventan: salen de `corpus/pdf/MANIFIESTO-d4.md` y
`MANIFIESTO-d5.md`, que los derivan del propio PDF.

Rasterizador: GHOSTSCRIPT. ImageMagick no tiene rasterizador de PDF, delega en
Ghostscript (CLAUDE.md trampa 8), asi que declararlo no es una eleccion sino un
dato. `pnggray` porque el corpus entero es gris y porque un PNG de PALETA le
llega a RapidOCR como matriz 2-D de indices (trampa 30).

uso: preparar_b11.py <dir_destino>
"""
import hashlib
import json
import os
import subprocess
import sys

GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
PDF = r"D:\Work\research\FileX\corpus\pdf"

# (documento, ppp NATIVOS, familia de referencia)
CORPUS = [
    # legado: referencia de 79 caracteres, SIN un solo diacritico (trampa 9)
    ("patologico_escaneado", 200, "legado"),
    ("escaneado_d1", 150, "legado"),
    ("escaneado_d2", 100, "legado"),
    ("escaneado_d3", 100, "legado"),
    # `tipico_texto.pdf` NO contiene el texto de la referencia legado: su capa de
    # texto dice «FileX - documento de prueba con texto seleccionable / Segunda
    # linea: acentos aeiou n ^ y simbolos % & @ / Tabla: ...». Y esa capa, sacada
    # con `gs -sDEVICE=txtwrite`, llega ya SIN TILDES («aeiou n ^»), asi que
    # tampoco sirve de patron oro para la metrica acentuada. Se rasteriza y se
    # mide, pero queda FUERA del saldo y declarado: inventar una referencia seria
    # peor que no tenerla (mismo criterio que `oro__trivial_p1` en
    # `ppp-y-normalizacion.md` 3.3).
    ("tipico_texto", 150, "sin_referencia_fiable"),
    # familia d4: referencia de 610 caracteres con tildes
    ("escaneado_d4", 200, "d4"),
    ("escaneado_d4a", 200, "d4"),
    ("escaneado_d4b", 200, "d4"),
    ("escaneado_d4c", 200, "d4"),
    ("escaneado_d4e", 200, "d4"),
    ("escaneado_d4f", 240, "d4"),
    # familia d5: misma referencia, otras degradaciones y ppp por debajo de 100
    ("escaneado_d5", 72, "d4"),
    ("escaneado_d5a", 90, "d4"),
    ("escaneado_d5b", 60, "d4"),
    ("escaneado_d5c", 80, "d4"),
    ("patologico_d5a", 200, "d4"),
    ("patologico_d5b", 200, "d4"),
    ("patologico_d5e", 200, "d4"),
    ("realista_d5a", 200, "d4"),
    ("realista_d5b", 200, "d4"),
    ("realista_d5e", 200, "d4"),
]

destino = sys.argv[1]
os.makedirs(destino, exist_ok=True)
indice = []

for doc, ppp, fam in CORPUS:
    src = os.path.join(PDF, doc + ".pdf")
    dst = os.path.join(destino, doc + ".png")
    orden = [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
             "-sDEVICE=pnggray", f"-r{ppp}", "-dFirstPage=1", "-dLastPage=1",
             f"-sOutputFile={dst}", src]
    r = subprocess.run(orden, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(dst):
        indice.append({"doc": doc, "ppp": ppp, "rc": r.returncode,
                       "error": r.stderr[-400:]})
        print(f"FALLO {doc}: rc={r.returncode} {r.stderr[-200:]}")
        continue
    with open(dst, "rb") as f:
        cab = f.read(33)
    w = int.from_bytes(cab[16:20], "big")
    h = int.from_bytes(cab[20:24], "big")
    indice.append({"doc": doc, "ppp_nativos": ppp, "referencia": fam, "rc": 0,
                   "png": dst, "px_w": w, "px_h": h,
                   "mpx": round(w * h / 1e6, 3), "bytes": os.path.getsize(dst),
                   "sha256": hashlib.sha256(open(dst, "rb").read()).hexdigest(),
                   "orden": " ".join(orden)})
    print(f"{doc}: {w}x{h} = {w*h/1e6:.3f} Mpx  (ref {fam}, {ppp} ppp)")

json.dump(indice, open(os.path.join(destino, "indice.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"{sum(1 for i in indice if i['rc'] == 0)} de {len(CORPUS)} rasterizados")
