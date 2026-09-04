# -*- coding: utf-8 -*-
"""Cuantas aristas indeterminadas cuelgan de cada clase.

Es lo que decide DONDE mirar en la ronda que si pueda usar la maquina: no todas las
clases valen lo mismo, porque cada token multiplica por las salidas vivas de su motor.
Solo lectura.
"""
import os, json, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
SAL = os.path.abspath(os.path.join(AQUI, "..", "salidas-aristas"))

cl = json.load(open(os.path.join(AQUI, "clasificacion.json"), encoding="utf-8"))
ar = json.load(open(os.path.join(AQUI, "aristas_A.json"), encoding="utf-8"))
s1 = json.load(open(os.path.join(SAL, "semi_salida.json"), encoding="utf-8"))
s2 = json.load(open(os.path.join(SAL, "semi_salida2.json"), encoding="utf-8"))
e1 = json.load(open(os.path.join(SAL, "semi_entrada.json"), encoding="utf-8"))
e2 = json.load(open(os.path.join(SAL, "semi_entrada2.json"), encoding="utf-8"))

out = {k: ("viva" if (v["vivo"] or s2.get(k, {}).get("vivo", False)) else "muerta")
       for k, v in s1.items()}
ent = {}
for k, v in e1.items():
    if v["estado"] == "no_materializable":
        ent[k] = "indet"
    else:
        ent[k] = "viva" if e2.get(k, {}).get("estado", v["estado"]) == "viva" else "muerta"

# arista indeterminada -> a que clase(s) de origen pertenece
porclase = collections.Counter()
for reg in ar["A"]:
    ab, ms = reg.split("|")
    a, b = ab.split(">")
    motores = ms.split(",")
    estados, culpables = [], []
    for m in motores:
        if m in ("ffmpeg", "imagemagick"):
            ei = ent.get("%s|%s" % (m, a), "indet")
            so = out.get("%s|%s" % (m, b), "indet")
            if ei == "muerta" or so == "muerta":
                estados.append("muerta")
            elif ei == "viva" and so == "viva":
                estados.append("viva")
            else:
                estados.append("indet")
                if ei == "indet":
                    culpables.append("%s|%s" % (m, a))
        else:
            estados.append("otro")
    if "viva" in estados or "otro" in estados or "indet" not in estados:
        continue
    clases = {cl[c]["clase"] for c in culpables if c in cl}
    porclase["+".join(sorted(clases)) or "(sin origen indet)"] += 1

tot = sum(porclase.values())
print("aristas indeterminadas: %d\n" % tot)
for c, n in porclase.most_common():
    print("  %-46s %7d   %5.2f %%" % (c, n, 100 * n / tot))

# el subconjunto que ffmpeg declara muxer y que NUNCA se probo como salida
todos_out = {k.split("|")[1] for k in s1 if k.startswith("ffmpeg|")}
mux = sorted(k.split("|", 1)[1] for k, v in cl.items() if v["clase"] == "ff_declarado_muxer")
nunca = [t for t in mux if t not in todos_out]
print("\nde los %d `ff_declarado_muxer`, NUNCA probados como salida: %d" % (len(mux), len(nunca)))
n_ar = sum(1 for reg in ar["A"] if reg.split("|")[0].split(">")[0] in set(nunca)
           and "ffmpeg" in reg.split("|")[1])
print("aristas del grafo A con uno de esos %d como ORIGEN: %d" % (len(nunca), n_ar))
print("\nlista:", ", ".join(nunca))
