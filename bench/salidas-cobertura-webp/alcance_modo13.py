"""Cierra el PENDIENTE 2 de bench/cobertura-png.md.

Su medida: 9 imagenes escritas por magick, el modo 13 no aparece ni una vez, asi
que el alcance del defecto sobre ficheros reales queda PENDIENTE.

Aqui: 40 semillas de 24x24 con el alfa en banda estrecha (que es lo que obliga
al predictor a trabajar en vez de copiar), y por cada una se registra
    - si _predice recibio el modo 13
    - si alfa_min de FileX difiere del que mide libwebp
Ademas se reproduce su receta —imagen generica, alfa plano— como CONTROL, para
comprobar que el modo 13 sigue sin salir por ese camino: si saliera, lo que
cambio seria el instrumento y no el hallazgo.
"""
import json, os, subprocess, sys, tempfile
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W = RAIZ
sys.path.insert(0, W)
sys.path.insert(0, os.path.join(W, "pruebas"))
from filex import verificador as V

d = tempfile.mkdtemp(prefix="alc13-")


def m(*a):
    subprocess.run(["magick", *a], check=True, capture_output=True)


def medir(f):
    """(modos usados, min de libwebp, min de FileX)."""
    vistos = []
    real = V._predice
    V._predice = lambda mo, px, i, w: (vistos.append(mo), real(mo, px, i, w))[1]
    try:
        r = V.alfa_minimo(f)
    finally:
        V._predice = real
    ref = subprocess.run(["magick", f, "-alpha", "extract", "-depth", "8",
                          "gray:-"], capture_output=True).stdout
    return set(vistos), min(ref), round(r["alfa_min"] * 255)


filas = []
for s in range(1, 41):
    b = os.path.join(d, "b%d" % s)
    m("-seed", str(s), "-size", "24x24", "plasma:fractal", "-depth", "8",
      "PNG24:" + b + "c.png")
    m("-seed", str(s + 500), "-size", "24x24", "plasma:fractal", "-colorspace",
      "Gray", "-evaluate", "Multiply", "0.35", "-evaluate", "Add", "25%",
      "-depth", "8", b + "m.png")
    m(b + "c.png", b + "m.png", "-alpha", "off", "-compose", "CopyOpacity",
      "-composite", "-depth", "8", "PNG32:" + b + "r.png")
    f = b + ".webp"
    m(b + "r.png", "-define", "webp:lossless=true", f)
    modos, mref, mfx = medir(f)
    filas.append({"semilla": s, "banda_estrecha": True, "modos": sorted(modos),
                  "modo13": 13 in modos, "min_libwebp": mref, "min_filex": mfx,
                  "difiere": mref != mfx})

# CONTROL, reproduciendo el camino de cob/png: alfa plano, imagen generica
control = []
for s in range(1, 11):
    b = os.path.join(d, "k%d" % s)
    m("-seed", str(s), "-size", "24x24", "plasma:fractal", "-depth", "8",
      "-alpha", "set", "-channel", "A", "-evaluate", "set", "50%", "+channel",
      "PNG32:" + b + ".png")
    f = b + ".webp"
    m(b + ".png", "-define", "webp:lossless=true", f)
    modos, mref, mfx = medir(f)
    control.append({"semilla": s, "banda_estrecha": False,
                    "modos": sorted(modos), "modo13": 13 in modos,
                    "min_libwebp": mref, "min_filex": mfx,
                    "difiere": mref != mfx})

c13 = [x for x in filas if x["modo13"]]
cdif = [x for x in filas if x["difiere"]]
print("BANDA ESTRECHA, 40 semillas:")
print("  disparan el modo 13 : %d" % len(c13))
print("  mueven alfa_min     : %d" % len(cdif))
print("  modo13 Y difiere    : %d" % len([x for x in c13 if x["difiere"]]))
print("  difiere SIN modo 13 : %d" % len([x for x in cdif if not x["modo13"]]))
print("  recorrido de la diferencia: %s" %
      sorted({x["min_libwebp"] - x["min_filex"] for x in cdif}))
k13 = [x for x in control if x["modo13"]]
print("CONTROL (la receta de cob/png), 10 semillas:")
print("  disparan el modo 13 : %d" % len(k13))
print("  mueven alfa_min     : %d" % len([x for x in control if x["difiere"]]))
union = sorted(set().union(*[set(x["modos"]) for x in filas + control]))
print("  union de modos vistos en las 50: %s" % union)

sal = os.path.join(W, "bench", "salidas-cobertura-webp", "alcance-modo13.json")
json.dump({"banda_estrecha": filas, "control_alfa_plano": control,
           "resumen": {"n_banda": len(filas), "modo13_banda": len(c13),
                       "difieren_banda": len(cdif), "n_control": len(control),
                       "modo13_control": len(k13),
                       "difieren_control": len([x for x in control if x["difiere"]])}},
          open(sal, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("escrito", sal)
