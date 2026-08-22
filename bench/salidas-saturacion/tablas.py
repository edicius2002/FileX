#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Genera las tablas del informe en Markdown a partir de los ficheros
*_puntuado.jsonl que produce puntuar.py. Sin transcripcion a mano.
"""
import json
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from puntuar import wilson, fisher  # noqa: E402

CATS = ["A", "C", "B"]
ETIQ = {"A": "A · 27 herr. · 7.886 tok",
        "C": "C · 14 herr. · 4.749 tok",
        "B": "B · 8 herr. · 2.306 tok"}


def carga(f):
    return [json.loads(l) for l in open(os.path.join(BASE, f), encoding="utf-8")]


def pct(k, n):
    return "%.0f %%" % (100.0 * k / n) if n else "n/d"


def bloque(filas, titulo):
    print("\n### %s\n" % titulo)
    print("| Catálogo | n | Acierto estricto (IC 95 %) | Acierto permisivo | Petición cumplida entera | Elección trampa |")
    print("|---|---:|---:|---:|---:|---:|")
    for c in CATS:
        s = [f for f in filas if f["catalogo"] == c]
        if not s:
            continue
        n = len(s)
        ke = sum(f["estricta"] for f in s)
        kp = sum(f["permisiva"] for f in s)
        kc = sum(f["completa"] for f in s)
        kt = sum(f["trampa"] for f in s)
        lo, hi = wilson(ke, n)
        print("| %s | %d | **%s** [%.2f–%.2f] | %s | %s | %s |"
              % (ETIQ[c], n, pct(ke, n), lo, hi, pct(kp, n), pct(kc, n), pct(kt, n)))


def main(fichero, nombre_modelo):
    filas = carga(fichero)
    print("## Modelo: %s — n = %d ejecuciones" % (nombre_modelo, len(filas)))
    bloque(filas, "Global")
    nom = {1: "Estrato 1 · inequívocas (control)",
           2: "Estrato 2 · ambiguas con pista",
           3: "Estrato 3 · encadenadas",
           4: "Estrato 4 · ambiguas sin pista"}
    for e in sorted(set(f["estrato"] for f in filas)):
        bloque([f for f in filas if f["estrato"] == e], nom[e])

    print("\n### Por tarea (acierto estricto)\n")
    print("| Tarea | Estrato | A (27) | C (14) | B (8) |")
    print("|---|---:|---:|---:|---:|")
    ids = []
    for f in filas:
        if f["tarea"] not in ids:
            ids.append(f["tarea"])
    for tid in sorted(ids):
        fila = ["| %s | %d " % (tid, [f for f in filas if f["tarea"] == tid][0]["estrato"])]
        for c in CATS:
            s = [f for f in filas if f["tarea"] == tid and f["catalogo"] == c]
            fila.append("| %s " % (pct(sum(x["estricta"] for x in s), len(s)) if s else "n/d"))
        print("".join(fila) + "|")

    print("\n### Contrastes (Fisher exacto bilateral)\n")
    print("| Métrica | A (27) | C (14) | p (A vs C) | B (8) | p (A vs B) |")
    print("|---|---:|---:|---:|---:|---:|")
    for campo, et in (("estricta", "acierto estricto"),
                      ("permisiva", "acierto permisivo"),
                      ("completa", "petición cumplida entera"),
                      ("trampa", "elección trampa")):
        a = [f for f in filas if f["catalogo"] == "A"]
        cc = [f for f in filas if f["catalogo"] == "C"]
        b = [f for f in filas if f["catalogo"] == "B"]
        ka, kc, kb = (sum(f[campo] for f in x) for x in (a, cc, b))
        pac = fisher(ka, len(a) - ka, kc, len(cc) - kc)
        pab = fisher(ka, len(a) - ka, kb, len(b) - kb)
        print("| %s | %s | %s | %.3f%s | %s | %.3f%s |"
              % (et, pct(ka, len(a)), pct(kc, len(cc)), pac,
                 " **\\***" if pac < 0.05 else "",
                 pct(kb, len(b)), pab, " **\\***" if pab < 0.05 else ""))

    print("\n### Coste de la decisión (no de la conversión)\n")
    print("| Catálogo | Coste medio USD/petición | Latencia media | Llamadas sustantivas medias |")
    print("|---|---:|---:|---:|")
    for c in CATS:
        s = [f for f in filas if f["catalogo"] == c]
        print("| %s | %.4f | %.1f s | %.2f |"
              % (ETIQ[c], sum(f["coste_usd"] or 0 for f in s) / len(s),
                 sum(f["dur_s"] for f in s) / len(s),
                 sum(f["n_llamadas"] for f in s) / float(len(s))))

    print("\n### Distribución de clases\n")
    dist = defaultdict(lambda: defaultdict(int))
    for f in filas:
        dist[f["catalogo"]][f["clase"]] += 1
    clases = sorted({k for c in CATS for k in dist[c]})
    print("| Catálogo | " + " | ".join(clases) + " |")
    print("|---" * (len(clases) + 1) + "|")
    for c in CATS:
        print("| %s | " % ETIQ[c] + " | ".join(str(dist[c].get(k, 0)) for k in clases) + " |")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
