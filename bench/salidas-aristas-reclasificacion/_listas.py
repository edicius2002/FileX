# -*- coding: utf-8 -*-
"""Vuelca los miembros de cada clase, para pegarlos en el informe."""
import os, json, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
cl = json.load(open(os.path.join(AQUI, "clasificacion.json"), encoding="utf-8"))
cr = {f["clave"]: f for f in json.load(
    open(os.path.join(AQUI, "cruce.json"), encoding="utf-8"))["filas"]}

por = collections.defaultdict(list)
for k, v in cl.items():
    por[v["clase"]].append(k)

for c in sorted(por, key=lambda x: -len(por[x])):
    ks = sorted(por[c])
    print("\n=== %s  (n=%d) ===" % (c, len(ks)))
    if len(ks) <= 30:
        for k in ks:
            f = cr[k]
            extra = ("Module=%s modo=%s '%s'" % (f["modulo"], f["modo"], f["desc"])
                     if f["motor"] == "imagemagick" else
                     "demux=%s mux=%s proto=%s dev=%s" % (f["en_demuxer"], f["en_muxer"],
                                                          f["en_protocolo_in"], f["en_dispositivo_in"]))
            print("   %-28s %s" % (k, extra))
    else:
        print("   " + ", ".join(x.split("|", 1)[1] for x in ks))
