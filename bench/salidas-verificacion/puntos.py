#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Coste de CADA PUNTO del contrato por separado, con n>=9 repeticiones POR
FICHERO (no una muestra por fichero, que es lo que hacia la primera version y
daba medianas de 3 muestras en la categoria 'datos').

Se separa el SONDEO (leer el fichero) de la LOGICA de cada punto, porque con
el motor de subprocesos un solo ffprobe alimenta a la vez a los puntos 2, 3 y 4:
atribuir su coste a uno solo de ellos seria enganar.
"""
import json
import os
import statistics
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, AQUI)
import verificador as V           # noqa: E402
from trabajos import trabajos     # noqa: E402
from medir import sonda_entrada, _testigo   # noqa: E402

N = 15
CLAVES = ("sonda_salida", "1_firma", "2_flujos", "3_propiedades", "4_pedido",
          "logica", "total")


def main():
    trs = trabajos()
    salida = {}
    for motor in ("proceso", "subproceso"):
        cache = {}
        for t in trs:
            sonda_entrada(t, motor, cache)
        muestras = {}
        antes = min(_testigo() for _ in range(3))
        for t in trs:
            V.verificar(t["salida"], t["pedido"], t["entrada"], motor,
                        sonda_ent=cache[(t["entrada"], motor)])  # calentar
            for _ in range(N):
                r = V.verificar(t["salida"], t["pedido"], t["entrada"], motor,
                                sonda_ent=cache[(t["entrada"], motor)])
                d = muestras.setdefault(t["cat"], {})
                for k in CLAVES:
                    d.setdefault(k, []).append(r["ms"][k])
                g = muestras.setdefault("TODAS", {})
                for k in CLAVES:
                    g.setdefault(k, []).append(r["ms"][k])
        despues = min(_testigo() for _ in range(3))
        desv = abs(despues - antes) / max(antes, 1e-9)
        flag = "limpia" if desv <= 0.20 else "SUCIA(testigo %+.0f%%)" % (desv * 100)
        salida[motor] = {"flag": flag, "n_por_fichero": N,
                         "categorias": {c: {k: {"mediana": round(statistics.median(v), 4),
                                                "min": round(min(v), 4),
                                                "max": round(max(v), 4),
                                                "n": len(v)}
                                            for k, v in d.items()}
                                        for c, d in muestras.items()}}
    with open(os.path.join(AQUI, "puntos.json"), "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=1)

    for motor, d in salida.items():
        print("\n=== motor %s === [%s] n=%d por fichero" % (motor, d["flag"], N))
        print("%-8s %10s %9s %9s %9s %9s %9s %9s"
              % ("cat", "sonda", "p1firma", "p2flujos", "p3props", "p4pedido",
                 "logica", "TOTAL"))
        for c in ("imagen", "audio", "video", "pdf", "datos", "TODAS"):
            if c not in d["categorias"]:
                continue
            v = d["categorias"][c]
            print("%-8s %10.4f %9.4f %9.4f %9.4f %9.4f %9.4f %9.4f"
                  % (c, v["sonda_salida"]["mediana"], v["1_firma"]["mediana"],
                     v["2_flujos"]["mediana"], v["3_propiedades"]["mediana"],
                     v["4_pedido"]["mediana"], v["logica"]["mediana"],
                     v["total"]["mediana"]))


if __name__ == "__main__":
    main()
