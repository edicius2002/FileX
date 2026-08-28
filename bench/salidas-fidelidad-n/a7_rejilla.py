# -*- coding: utf-8 -*-
"""N18 — la rejilla de decisión, sobre las 264 celdas de `a7_corr_ancho.json`.

No lanza nada: es aritmética sobre lo ya medido, y por eso es reproducible al
instante. Responde a tres preguntas que la tabla de un solo umbral no puede:

1. ¿Cuántos de los «falsos positivos» del umbral de correlación **ya son fallo
   HOY** por el escalón de silencio de A7? Contarlos como nuevos sería contar
   dos veces (y es la trampa 25 en versión de recuento: dos cosas distintas con
   la misma pinta).
2. Con esos fuera, ¿queda hueco? (trampa 51: primero *¿existe?*, después
   *¿dónde?*).
3. Si no queda, ¿hay una SEGUNDA variable que lo abra? Se prueba la más barata
   de todas —el nivel del canal **relativo al canal más fuerte de la ENTRADA**,
   que ya está calculado— porque el mecanismo medido dice que el problema es un
   canal legítimamente flojo al que Opus se come.
"""
from __future__ import annotations

import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(AQUI, "a7_corr_ancho.json"), encoding="utf-8"))
F = D["filas"]

AUDIBLE = -60.0
SILENCIO = -80.0


def a7_hoy(f):
    """A7 tal y como está: algún canal audible en la entrada sale mudo."""
    for k in (0, 1):
        rs = f["rms_sal"][k]
        if f["rms_ent"][k] > AUDIBLE and (rs is None or rs <= SILENCIO):
            return True
    return False


for f in F:
    f["a7_hoy"] = a7_hoy(f)
    fuerte = max(f["rms_ent"])
    f["rel"] = [round(f["rms_ent"][k] - fuerte, 2) for k in (0, 1)]

print("=== 1. ¿cuántas celdas ya son fallo HOY, por clase? ===")
clases = sorted({f["clase_real"] for f in F})
for c in clases:
    sel = [f for f in F if f["clase_real"] == c]
    print("  %-18s %3d celdas, %3d ya fallo hoy por A7 (silencio)"
          % (c, len(sel), sum(1 for f in sel if f["a7_hoy"])))

print("\n=== 2. la señal, SOLO sobre las celdas que hoy pasan ===")
print("    (las que A7 ya suspende no las puede 'romper' un umbral nuevo)")
vivas = [f for f in F if not f["a7_hoy"] and f["corr_min_audible"] is not None]
mal = [f for f in vivas if f["clase_real"] == "mala_con_perdida"]
bue = [f for f in vivas if f["clase_real"] in ("buena", "buena_brutal")]
print("  malas que hoy se escapan: %d   buenas vivas: %d" % (len(mal), len(bue)))
if mal and bue:
    print("  peor mala  %+7.4f   mejor buena %+7.4f   HUECO %+7.4f"
          % (max(f["corr_min_audible"] for f in mal),
             min(f["corr_min_audible"] for f in bue),
             min(f["corr_min_audible"] for f in bue)
             - max(f["corr_min_audible"] for f in mal)))
print("  las buenas por debajo de 0,13:")
for f in sorted(bue, key=lambda x: x["corr_min_audible"])[:12]:
    print("    %-10s %-13s %-28s corr=%+7.4f  rel=%s  rms_ent=%s"
          % (f["fuente"], f["clase_real"], f["destino"], f["corr_min_audible"],
             f["rel"], f["rms_ent"]))

print("\n=== 3. rejilla (umbral de corr) x (suelo RELATIVO del canal, dB) ===")
print("    'atrapa' = malas con pérdida que hoy se escapan y el par atraparía")
print("    'FP'     = buenas o buenas_brutal que el par rompería")
print("  %-8s %s" % ("corr <", "".join("%12s" % ("rel>=%d" % r)
                                       for r in (-100, -60, -40, -30, -20, -12))))
for u in (0.008, 0.02, 0.05, 0.10, 0.13, 0.20):
    fila = []
    for rel_min in (-100, -60, -40, -30, -20, -12):
        def dispara(f):
            for k in (0, 1):
                if f["rms_ent"][k] <= AUDIBLE or f["rel"][k] < rel_min:
                    continue
                if f["corr_c0" if k == 0 else "corr_c1"] < u:
                    return True
            return False
        a = sum(1 for f in vivas
                if f["clase_real"] == "mala_con_perdida" and dispara(f))
        fp = sum(1 for f in vivas
                 if f["clase_real"] in ("buena", "buena_brutal") and dispara(f))
        fila.append("%5d/%-3d %2d" % (a, len(mal), fp))
    print("  %-8.3f %s" % (u, "".join("%12s" % x for x in fila)))

print("\n=== 4. por FUENTE: dónde se rompe, con corr<0,05 y sin suelo relativo ===")
for fu in sorted({f["fuente"] for f in F}):
    sel = [f for f in vivas if f["fuente"] == fu]
    if not sel:
        continue
    a = sum(1 for f in sel if f["clase_real"] == "mala_con_perdida"
            and f["corr_min_audible"] < 0.05)
    na = sum(1 for f in sel if f["clase_real"] == "mala_con_perdida")
    fp = [f["destino"] for f in sel
          if f["clase_real"] in ("buena", "buena_brutal")
          and f["corr_min_audible"] < 0.05]
    print("  %-11s atrapa %2d/%-2d   FP %d %s" % (fu, a, na, len(fp), fp))

res = {"vivas": len(vivas), "malas_vivas": len(mal), "buenas_vivas": len(bue),
       "detalle": [{k: f[k] for k in ("fuente", "clase_real", "destino",
                                      "corr_c0", "corr_c1", "corr_min_audible",
                                      "rms_ent", "rms_sal", "rel", "a7_hoy")}
                   for f in F]}
with open(os.path.join(AQUI, "a7_rejilla.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)
print("\n-> a7_rejilla.json")
