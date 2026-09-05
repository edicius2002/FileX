"""Suelo de la ganancia sin ImageMagick nativo (el caso del runner de Linux).

Trampa 94: el recuento de una suite declara interprete, entorno y que quedo
fuera. Aqui la unica clase que depende del entorno es `Vp8lDeVerdad`, que pide
`magick` para escribir un WebP sin perdida; sin ella, el decodificador VP8L
completo no se ejecuta.
"""
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))


def de_cobertura(nombre):
    d = json.load(open(os.path.join(AQUI, nombre), encoding="utf-8"))
    k = [x for x in d["files"] if "verificador" in x][0]
    return set(d["files"][k]["executed_lines"])


base = json.load(open(os.path.join(AQUI, "base-verificador.json"), encoding="utf-8"))
faltan_base = set(base["missing_lines"])
con = de_cobertura("cobertura.json")
sin = de_cobertura("cobertura-sin-magick.json")
g_con = faltan_base & con
g_sin = faltan_base & sin
print("ganadas CON magick:", len(g_con))
print("ganadas SIN magick (suelo):", len(g_sin))
print("solo gracias a magick:", len(g_con - g_sin))
json.dump({"ganadas_con_magick": len(g_con), "ganadas_sin_magick": len(g_sin),
           "solo_con_magick": sorted(g_con - g_sin)},
          open(os.path.join(AQUI, "suelo.json"), "w"), indent=1)
