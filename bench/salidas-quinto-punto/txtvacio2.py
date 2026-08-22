# -*- coding: utf-8 -*-
"""¿Por que `gs -sDEVICE=txtwrite` devuelve vacio de vez en cuando?

V1 lo observo (verificador-ghostscript.md §5.9) y NO lo reprodujo en 20
intentos. Aqui ha aparecido SOLO tres veces mientras se median otras cosas.
Este script separa las dos hipotesis con n grande sobre UN solo fichero:

  A) es Ghostscript el que a veces no escribe nada;
  B) es la captura por TUBERIA (-sOutputFile=- + capture_output) la que a
     veces pierde la salida.

La sonda del verificador (`_gs_texto`) usa la tuberia, y de ella cuelga P2, que
es una regla de severidad FALLO.
"""
import json
import os
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
import verificador as V           # noqa: E402

PDF = os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf")
TMP = os.path.join(AQUI, "tmp", "txt2")
os.makedirs(TMP, exist_ok=True)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200

res = {"pdf": os.path.relpath(PDF, RAIZ), "n": N,
       "tuberia": [], "fichero": [], "sonda_actual": []}
for i in range(N):
    # (1) la implementacion ANTERIOR de _gs_texto, tal cual: tuberia
    t0 = time.perf_counter()
    p = subprocess.run(["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                        "-sDEVICE=txtwrite", "-sOutputFile=-", PDF],
                       capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    ms = (time.perf_counter() - t0) * 1000
    res["tuberia"].append([len("".join((p.stdout or "").split())), round(ms, 1)])

    # (3) la sonda del verificador TAL COMO ESTA AHORA
    t0 = time.perf_counter()
    ts, _ = V._gs_texto(PDF)
    ms = (time.perf_counter() - t0) * 1000
    res["sonda_actual"].append([len("".join((ts or "").split())), round(ms, 1)])

    sal = os.path.join(TMP, "s.txt")
    if os.path.exists(sal):
        os.remove(sal)
    t0 = time.perf_counter()
    subprocess.run(["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                    "-sDEVICE=txtwrite", "-sOutputFile=" + sal, PDF],
                   capture_output=True, stdin=subprocess.DEVNULL, timeout=120)
    ms = (time.perf_counter() - t0) * 1000
    t2 = open(sal, encoding="utf-8", errors="replace").read() \
        if os.path.exists(sal) else ""
    res["fichero"].append([len("".join(t2.split())), round(ms, 1)])

for k in ("tuberia", "fichero", "sonda_actual"):
    largos = [x[0] for x in res[k]]
    tiempos = [x[1] for x in res[k]]
    vac = sum(1 for x in largos if x == 0)
    res[k + "_resumen"] = {
        "vacios": vac, "n": N, "tasa_pct": round(100.0 * vac / N, 2),
        "valores_distintos": sorted(set(largos)),
        "mediana_ms": round(statistics.median(tiempos), 1)}
    print("  %-8s %3d/%d vacios (%.2f %%)  valores %s  mediana %.1f ms"
          % (k, vac, N, 100.0 * vac / N, sorted(set(largos)),
             statistics.median(tiempos)))

with open(os.path.join(AQUI, "txtvacio2.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)
print("-> txtvacio2.json")

