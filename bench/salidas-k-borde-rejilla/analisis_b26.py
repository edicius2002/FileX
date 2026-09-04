#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B26 -- analisis: `k` por MINIMO ARREPENTIMIENTO sobre la rejilla extendida,
y cuanto de lo publicado era un artefacto del TECHO de la rejilla.

Tres tablas, todas POR CONFIGURACION y nunca promediadas entre configuraciones
(la interaccion motor x documento es el 76,7 % de la varianza; promediarla la
destruye -- `bench/k-por-motor.md`, CLAUDE.md trampa 8):

  1. CER por (documento, factor), con `rc` y determinismo.
  2. Arrepentimiento por factor: `regret(k) = media_doc[CER(doc,k) - min_f
     CER(doc,f)]`, y su maximo sobre documentos.
  3. La comparacion que responde al encargo: argmin sobre la rejilla TRUNCADA
     en x1,60 (la de B23) frente al argmin sobre la rejilla ENTERA, medidos
     los dos en ESTA tanda -- trampa 59: la version historica se mide en la
     propia tanda, no se cita.

El arrepentimiento se calcula solo sobre los factores RECTANGULARES (aquellos
con celda valida en los 4 documentos): un factor al que le falta un documento
por `omitido_vram` tendria un minimo por documento calculado sobre otra
muestra y no seria comparable. Los factores parciales se listan aparte.

uso: python analisis_b26.py [--json-dir ...]
"""
import argparse
import json
import os
import statistics

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = ["escaneado_d5a", "escaneado_d5c", "escaneado_d5", "escaneado_d5b"]
REJILLA_B23 = [0.75, 0.875, 1.00, 1.125, 1.25, 1.40, 1.60]
CONFIGS = ["easyocr", "tess11", "docling-r6"]


def carga(js_dir, config):
    ruta = os.path.join(js_dir, "b26_%s.json" % config)
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def malla(d):
    """(cer, omitidos, incidencias) indexado por [factor][doc]."""
    cer, omit, inc = {}, [], []
    for r in d["rows"]:
        f, doc = r["factor"], r["doc"]
        if "omitido_vram" in r:
            omit.append((f, doc, r["omitido_vram"]))
            continue
        cer.setdefault(f, {})[doc] = r["cer_pct"]
        if not r.get("rc_todas_cero", True):
            inc.append((f, doc, "rc", r.get("rc_reps")))
        if not r.get("determinista", True):
            inc.append((f, doc, "no determinista", r.get("cer_reps")))
    return cer, omit, inc


def regret(cer, factores):
    """regret(k) medio y maximo sobre los documentos, restringido a `factores`."""
    factores = [f for f in factores if f in cer and len(cer[f]) == len(DOCS)]
    if not factores:
        return {}, []
    mejor = {doc: min(cer[f][doc] for f in factores) for doc in DOCS}
    out = {}
    for f in factores:
        dif = [cer[f][doc] - mejor[doc] for doc in DOCS]
        out[f] = (round(statistics.fmean(dif), 3), round(max(dif), 3))
    return out, factores


def argmin(reg):
    return min(reg, key=lambda f: (reg[f][0], reg[f][1])) if reg else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-dir", default=os.path.join(BASE, "json"))
    args = ap.parse_args()

    resumen = {}
    for config in CONFIGS:
        d = carga(args.json_dir, config)
        if d is None:
            print("== %s: SIN FICHERO (no medido)\n" % config)
            continue
        cer, omit, inc = malla(d)
        factores = sorted(cer)
        rect = [f for f in factores if len(cer[f]) == len(DOCS)]
        parciales = [f for f in factores if len(cer[f]) != len(DOCS)]

        print("== %s | %s | ruido %s (deriva %s, nivel %s) | %s s"
              % (config, d["meta"]["motor"], d["etiqueta_ruido"],
                 d["ruido"]["deriva"], d["ruido"]["nivel"], d["segundos"]))
        print("   raster: %s | n=%s | metrica: acentos" % (d["meta"]["raster"], d["meta"]["reps"]))
        cab = "   %-16s" % "documento" + "".join("%8s" % ("x%.3g" % f) for f in factores)
        print(cab)
        for doc in DOCS:
            fila = "   %-16s" % doc
            for f in factores:
                v = cer[f].get(doc)
                fila += ("%8.2f" % v) if v is not None else "     ---"
            print(fila)

        # Arrepentimiento sobre la rejilla ENTERA y sobre la TRUNCADA en x1,60.
        reg_all, usados_all = regret(cer, rect)
        reg_b23, usados_b23 = regret(cer, [f for f in rect if f <= 1.60])
        k_all, k_b23 = argmin(reg_all), argmin(reg_b23)

        print("   arrepentimiento (medio / max), rejilla ENTERA (%d factores):" % len(usados_all))
        print("   %-16s" % "regret medio" + "".join("%8.2f" % reg_all[f][0] for f in factores
                                                    if f in reg_all))
        print("   %-16s" % "regret max" + "".join("%8.2f" % reg_all[f][1] for f in factores
                                                  if f in reg_all))
        if parciales:
            print("   factores PARCIALES (excluidos del arrepentimiento): %s"
                  % ", ".join("x%.3g" % f for f in parciales))
        for f, doc, motivo in omit:
            print("   omitido_vram: x%.3g %s -- %s" % (f, doc, motivo))
        for x in inc:
            print("   INCIDENCIA: %s" % (x,))

        print("   k por minimo arrepentimiento:")
        if k_b23:
            print("     rejilla B23 (<= x1,60): x%.3g  (regret %.2f / %.2f)"
                  % (k_b23, reg_b23[k_b23][0], reg_b23[k_b23][1]))
        if k_all:
            print("     rejilla ENTERA        : x%.3g  (regret %.2f / %.2f)"
                  % (k_all, reg_all[k_all][0], reg_all[k_all][1]))
        if k_b23 and k_all:
            coste = reg_all[k_b23][0] - reg_all[k_all][0]
            print("     COSTE de haberse quedado en el borde: %.2f pt de arrepentimiento medio"
                  % coste)
            print("     borde tocado por B23: %s" % ("SI (argmin en x1,60)" if k_b23 == 1.60
                                                     else "no"))
        print()
        resumen[config] = {
            "k_rejilla_b23": k_b23, "k_rejilla_entera": k_all,
            "regret_b23": reg_b23.get(k_b23), "regret_entera": reg_all.get(k_all),
            "regret_de_k_b23_en_rejilla_entera": reg_all.get(k_b23),
            "factores_rectangulares": usados_all, "factores_parciales": parciales,
            "omitidos_vram": [{"factor": f, "doc": doc, "motivo": m} for f, doc, m in omit],
            "incidencias": [list(map(str, x)) for x in inc],
            "cer": {("x%.3g" % f): cer[f] for f in factores},
            "regret_entera_por_factor": {("x%.3g" % f): reg_all[f] for f in reg_all},
        }

    with open(os.path.join(BASE, "json", "b26_analisis.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
