# -*- coding: utf-8 -*-
"""E1 - recuentos de control para el informe: invocaciones totales y timeouts."""
import json, os

S = r"D:\Work\research\FileX\bench\salidas-aristas"
tot = 0
to = []
for f in ("semi_salida.json", "semi_salida2.json"):
    d = json.load(open(os.path.join(S, f), encoding="utf-8"))
    for k, v in d.items():
        for i in v.get("intentos", []):
            tot += 1
            if i.get("rc") == -9 or "TIMEOUT" in (i.get("err") or ""):
                to.append((f, k, i.get("semilla")))
for f in ("semi_entrada.json", "semi_entrada2.json"):
    d = json.load(open(os.path.join(S, f), encoding="utf-8"))
    for k, v in d.items():
        for i in v.get("intentos", []):
            tot += 1
            if i.get("rc") == -9 or "TIMEOUT" in (i.get("err") or ""):
                to.append((f, k, i.get("destino")))
mu = json.load(open(os.path.join(S, "muestra.json"), encoding="utf-8"))
n = 0
for g in ("general", "pdf"):
    for r in mu[g]:
        if "rc" in r:
            tot += 1
            n += 1
            if r["rc"] == -9 or "TIMEOUT" in (r.get("err") or ""):
                to.append((g, r["a"] + ">" + r["b"], ""))
print("invocaciones de motor registradas:", tot, " (de ellas, muestra:", n, ")")
print("timeouts:", len(to))
for x in to:
    print("   ", x)
