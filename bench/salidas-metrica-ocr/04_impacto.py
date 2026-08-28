# -*- coding: utf-8 -*-
"""A7 / paso 4 — IMPACTO: cuanto se mueve el NUMERO al cambiar de metrica.

Dos preguntas separadas a proposito (son distintas y el encargo insiste):
  (a) cambia el NUMERO        -> este script
  (b) cambia la CONCLUSION    -> 05_conclusiones.py

Aqui solo se describe el desplazamiento: por informe, por referencia, y entre
las DOS metricas acentuadas entre si (que es la pregunta que el inventario del
proyecto ni se hacia: da por hecho que hay "una buena y una mala").
"""
import io
import json
import os
import statistics as st
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))


def pct(x, n):
    return "%5.1f %%" % (100.0 * x / n) if n else "   n/a"


def resumen(filas, campo):
    v = [f[campo] for f in filas]
    av = [abs(x) for x in v]
    return {
        "n": len(v),
        "iguales_0p01": sum(1 for x in av if x < 0.01),
        "mueven_0p5": sum(1 for x in av if x >= 0.5),
        "mueven_2": sum(1 for x in av if x >= 2.0),
        "mueven_6p3": sum(1 for x in av if x >= 6.3),
        "mediana": round(st.median(v), 3),
        "media": round(sum(v) / len(v), 3) if v else 0,
        "min": round(min(v), 2) if v else 0,
        "max": round(max(v), 2) if v else 0,
        "max_abs": round(max(av), 2) if av else 0,
    }


def main():
    r = json.load(io.open(os.path.join(AQUI, "recalculo.json"), encoding="utf-8"))
    filas = [f for f in r["filas"] if "cer_ciego" in f]
    print("celdas: %d\n" % len(filas))

    for etiq, campo in (("acentuada d4 (M2) - ciega (M1)", "delta_d4ac"),
                        ("acentuada tildes (M3) - ciega (M1)", "delta_tildes"),
                        ("tildes (M3) - d4 (M2)  [las DOS acentuadas]",
                         "delta_d4ac_tildes")):
        s = resumen(filas, campo)
        print("### %s" % etiq)
        print("    identicas (<0,01 pt): %5d  %s" % (s["iguales_0p01"],
                                                     pct(s["iguales_0p01"], s["n"])))
        print("    |delta| >= 0,5 pt   : %5d  %s" % (s["mueven_0p5"],
                                                     pct(s["mueven_0p5"], s["n"])))
        print("    |delta| >= 2,0 pt   : %5d  %s" % (s["mueven_2"],
                                                     pct(s["mueven_2"], s["n"])))
        print("    |delta| >= 6,3 pt   : %5d  %s   (6,3 = lo que dice la trampa 10)"
              % (s["mueven_6p3"], pct(s["mueven_6p3"], s["n"])))
        print("    mediana %+.3f   media %+.3f   recorrido [%+.2f, %+.2f]\n"
              % (s["mediana"], s["media"], s["min"], s["max"]))

    # --- desglose por informe x referencia -------------------------------
    print("### por informe (delta = M2 acentuada d4 - M1 ciega)")
    print("%-26s %-7s %5s %7s %7s %8s %8s" %
          ("informe", "ref", "n", "iguales", ">=0,5", "mediana", "max|d|"))
    grupos = {}
    for f in filas:
        grupos.setdefault((f["informe"], f["ref"]), []).append(f)
    for k in sorted(grupos):
        s = resumen(grupos[k], "delta_d4ac")
        print("%-26s %-7s %5d %7d %7d %+8.3f %8.2f" %
              (k[0], k[1], s["n"], s["iguales_0p01"], s["mueven_0p5"],
               s["mediana"], s["max_abs"]))

    print("\n### por informe (delta = M3 tildes - M1 ciega)")
    print("%-26s %-7s %5s %7s %7s %8s %8s" %
          ("informe", "ref", "n", "iguales", ">=0,5", "mediana", "max|d|"))
    for k in sorted(grupos):
        s = resumen(grupos[k], "delta_tildes")
        print("%-26s %-7s %5d %7d %7d %+8.3f %8.2f" %
              (k[0], k[1], s["n"], s["iguales_0p01"], s["mueven_0p5"],
               s["mediana"], s["max_abs"]))

    # --- las peores celdas ------------------------------------------------
    print("\n### las 15 celdas donde MAS se mueve el numero (M2 - M1)")
    peor = sorted(filas, key=lambda f: -abs(f["delta_d4ac"]))[:15]
    for f in peor:
        print("  %+7.2f  ciego=%6.2f  d4ac=%6.2f  tildes=%6.2f  %s"
              % (f["delta_d4ac"], f["cer_ciego"], f["cer_d4ac"],
                 f["cer_tildes"], f["rel"]))

    print("\n### las 15 celdas donde MAS se separan las DOS acentuadas (M3 - M2)")
    peor2 = sorted(filas, key=lambda f: -abs(f["delta_d4ac_tildes"]))[:15]
    for f in peor2:
        print("  %+7.2f  ciego=%6.2f  d4ac=%6.2f  tildes=%6.2f  %s"
              % (f["delta_d4ac_tildes"], f["cer_ciego"], f["cer_d4ac"],
                 f["cer_tildes"], f["rel"]))

    json.dump({"global": {c: resumen(filas, c) for c in
                          ("delta_d4ac", "delta_tildes", "delta_d4ac_tildes")},
               "por_informe": {"%s|%s" % k: {c: resumen(v, c) for c in
                                             ("delta_d4ac", "delta_tildes",
                                              "delta_d4ac_tildes")}
                               for k, v in grupos.items()}},
              io.open(os.path.join(AQUI, "impacto.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
