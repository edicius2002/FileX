#!/usr/bin/env python3
"""Trampa 28: el coste del camino de DENEGACIÓN no puede dispararse (R17: realpath
es un vector de DoS). N38 añade `abrir_confinado`, pero SÓLO en la vía VÁLIDA
—después de que `_resolver` haya pasado—, así que el camino de denegación de una
conversión no lo toca. Aquí se mide para confirmarlo, no para deducirlo.

Windows (donde se midió el 9,4 µs original). Mediana de n grande.
"""
import json
import os
import statistics
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from filex.confinamiento import Confinamiento, Denegado  # noqa

base = tempfile.mkdtemp(prefix="n38-coste-")
dentro = os.path.join(base, "e.txt")
open(dentro, "wb").write(b"hola")
fuera = os.path.join(tempfile.mkdtemp(prefix="n38-fuera-"), "f.txt")
open(fuera, "wb").write(b"secreto")

conf = Confinamiento([base])
N = 20000


def mide(fn):
    # calienta (trampa 7)
    for _ in range(500):
        try:
            fn()
        except Denegado:
            pass
    ts = []
    for _ in range(N):
        t0 = time.perf_counter()
        try:
            fn()
        except Denegado:
            pass
        ts.append((time.perf_counter() - t0) * 1e6)
    return round(statistics.median(ts), 3), round(statistics.quantiles(ts, n=10)[8], 3)


res = {"plataforma": sys.platform, "python": sys.version.split()[0], "n": N,
       "unidad": "microsegundos (mediana, p90)"}

# 1) DENEGACIÓN por lista blanca vía resolver() — es la trampa 28 original, sin tocar.
m, p = mide(lambda: conf.resolver(fuera))
res["resolver_denegado_lexico"] = {"mediana": m, "p90": p}

# 2) DENEGACIÓN por lista blanca vía abrir_confinado() — misma guarda léxica ANTES del disco.
m, p = mide(lambda: conf.abrir_confinado(fuera))
res["abrir_confinado_denegado_lexico"] = {"mediana": m, "p90": p}

# 3) Coste AÑADIDO en la vía VÁLIDA: abrir_confinado sobre un fichero legítimo
#    (abre fd + valida descriptor + cierra). Esto es lo único nuevo por conversión.
def valido():
    e = conf.abrir_confinado(dentro)
    e.cerrar()
m, p = mide(valido)
res["abrir_confinado_valido_con_cierre"] = {"mediana": m, "p90": p}

# 4) Referencia: resolver() sobre el fichero válido (lo que ya se hacía).
m, p = mide(lambda: conf.resolver(dentro))
res["resolver_valido"] = {"mediana": m, "p90": p}

print(json.dumps(res, ensure_ascii=False, indent=2))
OUT = os.path.join(ROOT, "bench", "salidas-toctou-fd", "coste_denegacion.json")
open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=2))

import shutil
shutil.rmtree(base, ignore_errors=True)
shutil.rmtree(os.path.dirname(fuera), ignore_errors=True)
