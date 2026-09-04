# -*- coding: utf-8 -*-
"""Detalle de los cubos del cruce. Solo lectura; no ejecuta motores."""
import os, json, collections, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
d = json.load(open(os.path.join(AQUI, "cruce.json"), encoding="utf-8"))
filas = d["filas"]
ff = [x for x in filas if x["motor"] == "ffmpeg"]

censo = json.load(open(os.path.join(RAIZ, "bench", "salidas-aristas", "censo.json"),
                      encoding="utf-8"))
muertos_in = {x.lower() for x in censo["ffmpeg"]["muertos_in"]}
print("censo.json ffmpeg.muertos_in: %d" % len(muertos_in))

cubos = collections.defaultdict(list)
for x in ff:
    k = (x["en_demuxer"], x["en_muxer"], x["en_protocolo_in"], x["en_dispositivo_in"])
    cubos[k].append(x["token"])

for k in sorted(cubos, reverse=True):
    toks = sorted(cubos[k])
    print("\n(demux=%s mux=%s proto=%s dev=%s)  n=%d" % (k + (len(toks),)))
    print("   ", ", ".join(toks[:25]) + (" ..." if len(toks) > 25 else ""))

desconocidos = set(cubos[(False, False, False, False)])
print("\n--- CONTROL CRUZADO con censo.json ---")
print("desconocidos por mi cruce : %d" % len(desconocidos))
print("en censo.muertos_in       : %d" % len(desconocidos & muertos_in))
print("NO en censo.muertos_in    : %d  %s" % (len(desconocidos - muertos_in),
                                              sorted(desconocidos - muertos_in)[:20]))
print("en censo pero materializ. : %d" % len(muertos_in - desconocidos))
