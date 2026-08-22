# -*- coding: utf-8 -*-
"""E1 - Escenarios para el estrato INDETERMINADO (origen no materializable).

No se inventa una cifra: se dan tres escenarios con su supuesto escrito, y el
reparto por motor del estrato, que es lo que decide cual es plausible.
"""
import os, json, math
from collections import Counter

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")

ar = json.load(open(os.path.join(SAL, "aristas.json"), encoding="utf-8"))
res = json.load(open(os.path.join(SAL, "resultado.json"), encoding="utf-8"))
mu = json.load(open(os.path.join(SAL, "muestra.json"), encoding="utf-8"))
s1 = json.load(open(os.path.join(SAL, "semi_salida.json"), encoding="utf-8"))
s2 = json.load(open(os.path.join(SAL, "semi_salida2.json"), encoding="utf-8"))
e1 = json.load(open(os.path.join(SAL, "semi_entrada.json"), encoding="utf-8"))
e2 = json.load(open(os.path.join(SAL, "semi_entrada2.json"), encoding="utf-8"))

out = {k: (v["vivo"] or s2.get(k, {}).get("vivo", False)) for k, v in s1.items()}
ent = {}
for k, v in e1.items():
    if v["estado"] == "no_materializable":
        ent[k] = "indet"
    else:
        ent[k] = "viva" if e2.get(k, {}).get("estado", v["estado"]) == "viva" else "muerta"

ind = Counter()
for reg in ar["A"]:
    ab, ms = reg.split("|")
    a, b = ab.split(">")
    ms_l = ms.split(",")
    est = []
    for m in ms_l:
        if m in ("ffmpeg", "imagemagick"):
            ei, so = ent.get("%s|%s" % (m, a), "indet"), out.get("%s|%s" % (m, b))
            if ei == "muerta" or so is False:
                est.append("muerta")
            elif ei == "viva" and so:
                est.append("viva")
            else:
                est.append("indet:" + m)
        else:
            est.append("otro")
    if "viva" in est or "otro" in est or "muerta" in "".join(est).split(":")[0:1] and "muerta" in est:
        pass
    if "viva" not in est and "otro" not in est and "muerta" not in est:
        ind[[x for x in est if x.startswith("indet")][0]] += 1

print("ESTRATO INDETERMINADO por motor:", dict(ind), " total", sum(ind.values()))

# tasa residual medida por motor sobre el marco
gen = [r for r in mu["general"] if "nominal" in r]
tam = mu["tam_estratos"]
por_motor = {}
for motor in ("ffmpeg", "imagemagick"):
    sub = [r for r in gen if r["motor"] == motor]
    N = sum(v for k, v in tam.items() if k.startswith(motor + "|"))
    # ponderada por tamano de estrato
    num = 0.0
    for k, v in tam.items():
        if not k.startswith(motor + "|"):
            continue
        s = [r for r in gen if r.get("estrato") == k]
        if s:
            num += v * sum(1 for r in s if r["nominal"]) / len(s)
    por_motor[motor] = (num / N, len(sub), N)
    print("  residual medido %-12s %.1f %%  (n=%d sobre N=%d)" % (motor, 100 * num / N, len(sub), N))

# muerte de semiarista de ENTRADA medida sobre los formatos materializables
for motor in ("ffmpeg", "imagemagick"):
    sub = {k: v for k, v in ent.items() if k.startswith(motor + "|")}
    vv = sum(1 for v in sub.values() if v == "viva")
    mm = sum(1 for v in sub.values() if v == "muerta")
    print("  semiarista de entrada muerta %-12s %d/%d = %.1f %%" % (motor, mm, vv + mm, 100 * mm / (vv + mm)))

POB, MUERTAS, MARCO, INDET = res["poblacion"], res["muertas_censo"], res["marco"], res["indeterminadas"]
p = res["p_residual"]
print("\nESCENARIOS SOBRE LAS %d ARISTAS DECLARADAS" % POB)
esc = {}
esc["A minimo (todas las indeterminadas son reales)"] = MUERTAS + p * MARCO
# B: las indeterminadas se comportan como el marco de su propio motor, mas la tasa
#    de muerte de semiarista de entrada medida en formatos materializables
tot_b = MUERTAS + p * MARCO
for k, n in ind.items():
    m = k.split(":")[1]
    sub = {kk: v for kk, v in ent.items() if kk.startswith(m + "|")}
    vv = sum(1 for v in sub.values() if v == "viva")
    mm = sum(1 for v in sub.values() if v == "muerta")
    q_ent = mm / (vv + mm)
    q_res = por_motor[m][0]
    tot_b += n * (q_ent + (1 - q_ent) * q_res)
esc["B (indeterminadas = su motor)"] = tot_b
esc["C maximo (indeterminadas todas nominales)"] = MUERTAS + p * MARCO + INDET
for k, v in esc.items():
    print("  %-46s %8.0f  = %5.1f %%" % (k, v, 100 * v / POB))
json.dump({k: v / POB for k, v in esc.items()},
          open(os.path.join(SAL, "escenarios.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
