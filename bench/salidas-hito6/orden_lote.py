# -*- coding: utf-8 -*-
"""S6 / hito 6 — el ORDEN del lote sobre el motor de produccion, repetido.

La primera pasada (V2 de `verificar_criterio.py`, **n=1**) dio el ascendente
**mas barato** que el descendente (1 468 frente a 1 564 MiB), que es lo
contrario de lo que refuto G5 con EasyOCR. Con n=1 eso no es una medida: la
trampa 36 dice que **una diferencia entre dos totales necesita que el signo se
conserve en otra tanda**, y aqui ademas se sospecha que la diferencia entera cae
dentro del ruido, porque RapidOCR **recorta a 2 000 px** y los folios grandes
son el mismo array.

Un proceso NUEVO por celda y las dos ordenes ALTERNADAS dentro de cada
repeticion, para que la deriva no se cargue sobre una de las dos.

uso: orden_lote.py [repeticiones]
"""
import json
import os
import statistics
import subprocess
import sys
import threading
import time

D = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(D))
sys.path.insert(0, RAIZ)
sys.path.insert(0, D)

from filex import gpu, sidecar                                  # noqa: E402
from testigos import testigo_deriva, testigo_nivel, veredicto   # noqa: E402

PY_OCR = os.environ.get("H6_PY", "D:/Work/research/FileX/.venv-ai/Scripts/python.exe")
IMG = os.path.join(D, "img")
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 5

FOLIOS = ["escaneado_d4_r100.png", "escaneado_d4_r150.png",
          "escaneado_d4_r200.png", "escaneado_d4_r280.png",
          "escaneado_d4_r400.png"]           # 0,555 -> 8,882 Mpx


def usada():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=20)
    return int(r.stdout.decode().strip().splitlines()[0])


def una(secuencia):
    """Un lote entero en un proceso NUEVO. Devuelve `(propio, base, pico)`."""
    est = {"pico": usada(), "parar": False}
    base = est["pico"]

    def bucle():
        while not est["parar"]:
            v = usada()
            if v > est["pico"]:
                est["pico"] = v
            time.sleep(0.25)

    h = threading.Thread(target=bucle, daemon=True)
    h.start()
    try:
        with sidecar.Registro(ttl_s=9999, python=PY_OCR) as reg:
            oks = [reg.procesar("rapidocr", os.path.join(IMG, n)).get("ok")
                   for n in secuencia]
    finally:
        est["parar"] = True
        h.join(timeout=5)
    return est["pico"] - base, base, est["pico"], all(oks)


d_ini = testigo_deriva()
n_ini, ag1 = testigo_nivel()
filas = []

with gpu.Lock("S6-orden-lote") as lk:
    if lk.aviso:
        print(f"[aviso] {lk.aviso}", flush=True)
    for i in range(REPS):
        for nombre, sec in (("descendente", list(reversed(FOLIOS))),
                            ("ascendente", list(FOLIOS))):
            propio, base, pico, ok = una(sec)
            filas.append({"rep": i, "orden": nombre, "propio_MiB": propio,
                          "base_MiB": base, "pico_MiB": pico, "ok": ok})
            print(json.dumps(filas[-1]), flush=True)
            time.sleep(2.0)

d_fin = testigo_deriva()
n_fin, ag2 = testigo_nivel()
ruido = veredicto(d_ini, d_fin, n_ini, n_fin, ag1 or ag2)

res = {"reps": REPS, "filas": filas, "ruido": ruido,
       "ruido_instrumento_MiB": 43}
for o in ("descendente", "ascendente"):
    v = [f["propio_MiB"] for f in filas if f["orden"] == o]
    res[o] = {"n": len(v), "mediana": statistics.median(v),
              "min": min(v), "max": max(v), "recorrido": max(v) - min(v)}
dif = res["ascendente"]["mediana"] - res["descendente"]["mediana"]
signos = []
for i in range(REPS):
    a = [f for f in filas if f["rep"] == i and f["orden"] == "ascendente"][0]
    d = [f for f in filas if f["rep"] == i and f["orden"] == "descendente"][0]
    signos.append(1 if a["propio_MiB"] > d["propio_MiB"] else
                  (-1 if a["propio_MiB"] < d["propio_MiB"] else 0))
res["diferencia_asc_menos_desc_MiB"] = dif
res["signos_por_repeticion"] = signos
res["signo_se_conserva"] = len(set(s for s in signos if s)) <= 1
res["supera_el_ruido"] = abs(dif) > 43

with open(os.path.join(D, "json", "orden_lote.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print(json.dumps({k: res[k] for k in
                  ("descendente", "ascendente", "diferencia_asc_menos_desc_MiB",
                   "signos_por_repeticion", "signo_se_conserva",
                   "supera_el_ruido")}, ensure_ascii=False, indent=2))
