#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Puntua el grid segun el criterio declarado en tareas.json.

Dos metricas, como exige el encargo, porque un catalogo grande tiene mas
formas de acertar y mas de fallar:

  ESTRICTA   : la primera llamada sustantiva es la herramienta 'mejor'
  PERMISIVA  : la primera llamada sustantiva esta en 'acepta'
               (o abstencion cuando la abstencion es lo correcto)

Ademas:
  REQUISITOS : los valores pedidos (bitrate, resolucion...) aparecen en los
               argumentos de alguna llamada -> la peticion se cumple ENTERA
  TRAMPA     : la primera llamada sustantiva esta en 'trampa' -> fichero
               incorrecto sin error

Las herramientas de solo diagnostico (health_check, ffmpeg_get_info) no
cuentan como llamada sustantiva: son preambulo legitimo.
"""
import json
import os
import sys
import math
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DIAG = {"health_check", "ffmpeg_get_info"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / float(n)
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


def fisher(a, b, c, d):
    """p bilateral exacto de Fisher para la tabla [[a,b],[c,d]]."""
    from math import comb
    n = a + b + c + d
    def prob(x):
        return (comb(a + b, x) * comb(c + d, a + c - x)) / float(comb(n, a + c))
    p0 = prob(a)
    lo = max(0, a + c - (c + d))
    hi = min(a + b, a + c)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1)
                        if prob(x) <= p0 + 1e-12))


def puntua_run(r, tarea):
    clave = tarea[r["catalogo"]]
    sust = [t for t in r["herramientas"] if t not in DIAG]
    primera = sust[0] if sust else None
    abst_ok = bool(clave.get("abstencion_correcta"))

    if abst_ok:
        estricta = permisiva = (primera is None)
        trampa = primera in set(clave.get("trampa", []))
        clase = "abstencion" if primera is None else (
            "trampa" if trampa else "otro")
    elif tarea["estrato"] == 3:
        seq = clave["secuencia"]
        estricta = (sust[:len(seq)] == seq) and len(sust) >= len(seq)
        permisiva = set(seq).issubset(set(sust)) or (
            all(any(s in clave["acepta"] for s in sust) for _ in [0])
            and set(sust) <= set(clave["acepta"]) and len(set(sust)) >= 2)
        trampa = any(s in set(clave.get("trampa", [])) for s in sust)
        clase = ("secuencia_exacta" if estricta else
                 "secuencia_completa_desordenada" if set(seq) <= set(sust) else
                 "incompleta")
    else:
        estricta = primera in set(clave.get("mejor", []))
        permisiva = primera in set(clave.get("acepta", []))
        trampa = primera in set(clave.get("trampa", []))
        clase = ("mejor" if estricta else
                 "resuelve" if permisiva else
                 "parcial" if primera in set(clave.get("parcial", [])) else
                 "trampa" if trampa else
                 "abstencion" if primera is None else "otro")

    blob = json.dumps(r["llamadas"], ensure_ascii=False).lower()
    reqs = tarea.get("requisitos_args") or []
    completa = all(q.lower() in blob for q in reqs) if sust else False

    return {"estricta": bool(estricta), "permisiva": bool(permisiva),
            "trampa": bool(trampa), "clase": clase, "completa": bool(completa),
            "n_llamadas": len(sust), "primera": primera}


def main(fichero):
    spec = json.load(open(os.path.join(BASE, "tareas.json"), encoding="utf-8"))
    tareas = {t["id"]: t for t in spec["tareas"]}
    runs = [json.loads(l) for l in open(os.path.join(BASE, fichero), encoding="utf-8")]
    runs = [r for r in runs if r["rc"] == 0]

    filas = []
    for r in runs:
        p = puntua_run(r, tareas[r["tarea"]])
        p.update({k: r[k] for k in ("catalogo", "tarea", "estrato", "rep",
                                    "modelo", "coste_usd", "dur_s", "turnos")})
        p["herramientas"] = r["herramientas"]
        filas.append(p)

    with open(os.path.join(BASE, fichero.replace(".jsonl", "_puntuado.jsonl")),
              "w", encoding="utf-8") as fh:
        for f in filas:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")

    cats = ["A", "C", "B"]
    print("=== N por celda ===")
    for c in cats:
        print(c, len([f for f in filas if f["catalogo"] == c]))

    def tabla(titulo, campo, subconj=None):
        print("\n=== %s ===" % titulo)
        print("%-6s %-10s %8s %8s %-16s" % ("estr", "tarea", "n", "acierto", "IC95"))
        sel = [f for f in filas if (subconj is None or subconj(f))]
        for est in sorted(set(f["estrato"] for f in sel)):
            for c in cats:
                s = [f for f in sel if f["estrato"] == est and f["catalogo"] == c]
                if not s:
                    continue
                k = sum(1 for f in s if f[campo])
                lo, hi = wilson(k, len(s))
                print("  E%d  %-10s %8d %7.0f%% [%.2f, %.2f]"
                      % (est, "cat " + c, len(s), 100.0 * k / len(s), lo, hi))
        print("  ---- global ----")
        for c in cats:
            s = [f for f in sel if f["catalogo"] == c]
            k = sum(1 for f in s if f[campo])
            lo, hi = wilson(k, len(s))
            print("  ALL %-10s %8d %7.0f%% [%.2f, %.2f]"
                  % ("cat " + c, len(s), 100.0 * k / len(s), lo, hi))

    tabla("ACIERTO ESTRICTO (la mejor herramienta)", "estricta")
    tabla("ACIERTO PERMISIVO (una que resuelve)", "permisiva")
    tabla("PETICION CUMPLIDA ENTERA (requisitos en los argumentos)", "completa")
    tabla("ELECCION TRAMPA (fichero incorrecto sin error)", "trampa")

    print("\n=== por tarea: acierto estricto / permisivo / completa / trampa ===")
    print("%-6s %-4s %5s %8s %8s %8s %8s" % ("tarea", "cat", "n", "estr", "perm", "compl", "tramp"))
    for tid in [t["id"] for t in spec["tareas"]]:
        for c in cats:
            s = [f for f in filas if f["tarea"] == tid and f["catalogo"] == c]
            if not s:
                continue
            n = len(s)
            print("%-6s %-4s %5d %7.0f%% %7.0f%% %7.0f%% %7.0f%%" % (
                tid, c, n,
                100.0 * sum(f["estricta"] for f in s) / n,
                100.0 * sum(f["permisiva"] for f in s) / n,
                100.0 * sum(f["completa"] for f in s) / n,
                100.0 * sum(f["trampa"] for f in s) / n))

    print("\n=== contraste A vs C y A vs B (Fisher bilateral) ===")
    for campo in ("estricta", "permisiva", "completa", "trampa"):
        for otro in ("C", "B"):
            a = [f for f in filas if f["catalogo"] == "A"]
            o = [f for f in filas if f["catalogo"] == otro]
            ka, ko = sum(f[campo] for f in a), sum(f[campo] for f in o)
            p = fisher(ka, len(a) - ka, ko, len(o) - ko)
            print("  %-10s A(%d/%d=%.0f%%) vs %s(%d/%d=%.0f%%)  p=%.4f%s"
                  % (campo, ka, len(a), 100.0 * ka / len(a), otro, ko, len(o),
                     100.0 * ko / len(o), p, "  *" if p < 0.05 else ""))

    print("\n=== distribucion de clases ===")
    dist = defaultdict(lambda: defaultdict(int))
    for f in filas:
        dist[f["catalogo"]][f["clase"]] += 1
    for c in cats:
        print(" ", c, dict(dist[c]))

    print("\n=== herramientas elegidas por primera vez, por catalogo ===")
    prim = defaultdict(lambda: defaultdict(int))
    for f in filas:
        prim[f["catalogo"]][f["primera"]] += 1
    for c in cats:
        print(" ", c, dict(sorted(prim[c].items(), key=lambda kv: -kv[1])))

    print("\n=== coste y latencia ===")
    for c in cats:
        s = [f for f in filas if f["catalogo"] == c]
        print("  %s  coste medio %.4f USD  dur media %.1fs  llamadas medias %.2f"
              % (c, sum(f["coste_usd"] or 0 for f in s) / len(s),
                 sum(f["dur_s"] for f in s) / len(s),
                 sum(f["n_llamadas"] for f in s) / float(len(s))))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "grid_haiku.jsonl")
