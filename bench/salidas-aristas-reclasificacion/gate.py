# -*- coding: utf-8 -*-
"""Por que 71 tokens que ffmpeg declara MUXER salieron `no_materializable`.

_semi_in.materializa() solo INTENTA con ffmpeg si `a in viva_ff_out`, y viva_ff_out
sale del censo de SALIDA (semi_salida.json + semi_salida2.json), no de -muxers.
Aqui se comprueba si esos 71 fueron intentados o ni siquiera se probaron.
Solo lectura.
"""
import os, json, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
SAL = os.path.abspath(os.path.join(AQUI, "..", "salidas-aristas"))
cr = json.load(open(os.path.join(AQUI, "cruce.json"), encoding="utf-8"))

s1 = json.load(open(os.path.join(SAL, "semi_salida.json"), encoding="utf-8"))
s2 = json.load(open(os.path.join(SAL, "semi_salida2.json"), encoding="utf-8"))
vivas = {k: (v["vivo"] or s2.get(k, {}).get("vivo", False)) for k, v in s1.items()}
viva_ff_out = {k.split("|")[1] for k, v in vivas.items() if v and k.startswith("ffmpeg|")}
todos_ff_out = {k.split("|")[1] for k in s1 if k.startswith("ffmpeg|")}
print("semi_salida ffmpeg: %d tokens probados, %d vivos" % (len(todos_ff_out), len(viva_ff_out)))

mux71 = sorted(x["token"] for x in cr["filas"]
               if x["motor"] == "ffmpeg" and x.get("en_muxer"))
print("\ntokens no_materializables que ffmpeg declara MUXER: %d" % len(mux71))
intentados = [t for t in mux71 if t in viva_ff_out]
probados_muertos = [t for t in mux71 if t in todos_ff_out and t not in viva_ff_out]
nunca = [t for t in mux71 if t not in todos_ff_out]
print("  ffmpeg SI se intento (estaba en viva_ff_out) : %d" % len(intentados))
print("  probado como salida y MUERTO -> no se intento: %d  %s" % (len(probados_muertos), probados_muertos[:15]))
print("  nunca probado como salida    -> no se intento: %d  %s" % (len(nunca), nunca[:15]))
