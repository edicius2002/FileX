"""Que lineas del encargo siguen sin ejecutar, con su texto."""
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
FUENTE = os.path.join(RAIZ, "filex", "verificador.py")

DEL_ENCARGO = {
    "_alfa_min_png": (1794, 1941), "_alfa_min_png_adam7": (1942, 2073),
    "_clamp_full": (2372, 2379), "_clamp_half": (2380, 2389),
    "_distancia_plano": (2245, 2250), "_leer_plte": (4757, 4769),
    "_paeth": (1671, 1677), "_predice": (2390, 2424), "_rep": (1662, 1669),
    "_selecciona": (2364, 2371),
}

base = json.load(open(os.path.join(AQUI, "base-verificador.json"), encoding="utf-8"))
faltan_base = set(base["missing_lines"])
d = json.load(open(os.path.join(AQUI, "cobertura.json"), encoding="utf-8"))
k = [x for x in d["files"] if "verificador" in x][0]
faltan_aqui = set(d["files"][k]["missing_lines"])
src = open(FUENTE, encoding="utf-8").read().splitlines()

quedan = sorted(faltan_base & faltan_aqui)
print("del encargo (289 lineas), siguen sin ejecutar:")
total = 0
for nom, (a, b) in sorted(DEL_ENCARGO.items(), key=lambda kv: kv[1]):
    ls = [n for n in quedan if a <= n <= b]
    antes = len([n for n in faltan_base if a <= n <= b])
    total += len(ls)
    print("  %-24s antes %3d  quedan %d %s" % (nom, antes, len(ls), ls))
    for n in ls:
        print("        %5d| %s" % (n, src[n - 1]))
print("total del encargo sin ejecutar:", total)
