# -*- coding: utf-8 -*-
"""E1 - Analisis final: junta el censo de semiaristas con la muestra ejecutada y
produce LA cifra, con su intervalo de Wilson al 95 % y su descomposicion.
"""
import os, json, math
from collections import Counter

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


ag = json.load(open(os.path.join(SAL, "agregado.json"), encoding="utf-8"))
mu = json.load(open(os.path.join(SAL, "muestra.json"), encoding="utf-8"))
POB = ag["total"]
MUERTAS = ag["conteo"]["muerta"]
MARCO = ag["conteo"]["viva"]
INDET = ag["conteo"]["indeterminada"]
OTRO = ag["conteo"]["otro_motor"]

gen = [r for r in mu["general"] if "nominal" in r]
pdf = [r for r in mu["pdf"] if "nominal" in r]
tam = mu["tam_estratos"]

print("=" * 78)
print("POBLACION: %d aristas declaradas por el grafo instalado" % POB)
print("  refutadas por ejecucion de una semiarista (CENSO): %6d  %5.2f %%" % (MUERTAS, 100 * MUERTAS / POB))
print("  con las dos semiaristas vivas (marco muestral)   : %6d  %5.2f %%" % (MARCO, 100 * MARCO / POB))
print("  indeterminadas (origen no materializable)        : %6d  %5.2f %%" % (INDET, 100 * INDET / POB))
print("  otros motores (gs / Gotenberg), tratadas aparte  : %6d  %5.2f %%" % (OTRO, 100 * OTRO / POB))

print("\n" + "=" * 78)
print("MUESTRA SOBRE EL MARCO (n=%d de %d)" % (len(gen), MARCO))
print("%-32s %6s %6s %8s %s" % ("estrato", "N", "n", "nominal", "IC 95 % (Wilson)"))
num, den = 0.0, 0
for k in sorted(tam):
    sub = [r for r in gen if r.get("estrato") == k]
    if not sub:
        continue
    kk = sum(1 for r in sub if r["nominal"])
    p, lo, hi = wilson(kk, len(sub))
    print("%-32s %6d %6d %7.1f %% [%.1f %% , %.1f %%]" % (k, tam[k], len(sub), 100 * p, 100 * lo, 100 * hi))
    num += p * tam[k]
    den += tam[k]
kg = sum(1 for r in gen if r["nominal"])
p, lo, hi = wilson(kg, len(gen))
print("%-32s %6d %6d %7.1f %% [%.1f %% , %.1f %%]  <- global sin ponderar" % ("TODOS", MARCO, len(gen), 100 * p, 100 * lo, 100 * hi))
print("%-32s %6s %6s %7.1f %%" % ("TODOS (ponderado por estrato)", "", "", 100 * num / den))

print("\n  categorias en la muestra general:", dict(Counter(r["categoria"] for r in gen)))
print("  N2 evaluable en %d de %d (%.0f %%)" % (sum(1 for r in gen if r.get("n2_evaluable")),
                                                len(gen), 100 * sum(1 for r in gen if r.get("n2_evaluable")) / len(gen)))

kp, np_ = sum(1 for r in pdf if r["nominal"]), len(pdf)
pp, plo, phi = wilson(kp, np_)
print("\n  ESTRATO PRIORITARIO PDF (%d de %d aristas que tocan pdf): %.1f %% nominal [%.1f %% , %.1f %%]"
      % (np_, mu["pdf_poblacion"], 100 * pp, 100 * plo, 100 * phi))
print("  categorias:", dict(Counter(r["categoria"] for r in pdf)))

print("\n" + "=" * 78)
DET = MUERTAS + MARCO
for etq, pr in (("estimacion puntual", p), ("extremo bajo del IC", lo), ("extremo alto del IC", hi)):
    tot = MUERTAS + pr * MARCO
    print("  %-22s -> nominales %8.0f de %d verificadas = %5.1f %%   (%.1f %% de las %d declaradas)"
          % (etq, tot, DET, 100 * tot / DET, 100 * tot / POB, POB))
print("\n  subpoblacion verificada: %d de %d = %.1f %% de la poblacion" % (DET, POB, 100 * DET / POB))

res = {"poblacion": POB, "muertas_censo": MUERTAS, "marco": MARCO, "indeterminadas": INDET,
       "otro_motor": OTRO, "n_muestra": len(gen), "nominales_muestra": kg,
       "p_residual": p, "ic95": [lo, hi], "p_ponderado": num / den,
       "verificadas": DET,
       "nominal_sobre_verificadas": [(MUERTAS + lo * MARCO) / DET, (MUERTAS + p * MARCO) / DET,
                                     (MUERTAS + hi * MARCO) / DET],
       "cota_inferior_sobre_poblacion": (MUERTAS + lo * MARCO) / POB,
       "pdf": {"n": np_, "nominales": kp, "p": pp, "ic95": [plo, phi],
               "poblacion": mu["pdf_poblacion"]}}
json.dump(res, open(os.path.join(SAL, "resultado.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
