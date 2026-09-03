#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Analisis de la rejilla 2x2 {con pHYs, sin pHYs} x {corpus viejo, corpus d5}
para el `k` de Tesseract. Lee las CUATRO celdas -- dos ya medidas (no se tocan),
dos nuevas de este encargo -- y aplica el MISMO metodo de minimo arrepentimiento
que tablas_km.py / k-oem-acantilados.md:

    regret(k) = media_documentos[ CER(doc, k) - min_f CER(doc, f) ]

sobre la MISMA rejilla de 7 factores en las cuatro celdas, para que la
comparacion sea de pHYs y corpus, no de rejilla.

Escribe json/analisis_2x2.json y tablas.md (parte).
"""
import io
import json
import os
import statistics

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
JS = os.path.join(BASE, "json")

FACTORES = [0.75, 0.875, 1.00, 1.125, 1.25, 1.40, 1.60]
DOCS_VIEJO = ["escaneado_d3", "escaneado_d4c", "patologico_escaneado", "escaneado_d4"]
DOCS_D5 = ["escaneado_d5a", "escaneado_d5c", "escaneado_d5", "escaneado_d5b"]


def clave_viejo(f, doc):
    return f"k{int(round(f * 1000)):04d}__{doc}"


def cargar_celda_C(psm):
    """corpus VIEJO, SIN pHYs -- YA MEDIDA (bench/salidas-k-motor), NO se repite."""
    fn = ("tesseract_cpu_D_tess_spa__cer.json" if psm == "3"
          else "tesseract_cpu_I_tess11_spa__cer.json")
    d = json.load(io.open(os.path.join(ROOT, "bench", "salidas-k-motor", "json", fn),
                           encoding="utf-8"))
    tabla = {doc: {} for doc in DOCS_VIEJO}
    for f in FACTORES:
        for doc in DOCS_VIEJO:
            r = d["res"].get(clave_viejo(f, doc))
            if r and "cer_acentos_pct" in r:
                tabla[doc][f] = r["cer_acentos_pct"]
    return tabla


def cargar_celda_D(psm):
    """corpus D5, CON pHYs -- YA MEDIDA (bench/salidas-k-oem-acantilados/b23_k_d5.py),
    NO se repite."""
    fn = f"b23_tess{psm}.json"
    d = json.load(io.open(os.path.join(ROOT, "bench", "salidas-k-oem-acantilados",
                                        "json", fn), encoding="utf-8"))
    tabla = {doc: {} for doc in DOCS_D5}
    for r in d["rows"]:
        if r["doc"] in tabla:
            tabla[r["doc"]][r["factor"]] = r["cer_pct"]
    return tabla


def cargar_celda_nueva(config, psm, docs):
    """corpus VIEJO con pHYs (config=viejo-phys) o corpus D5 sin pHYs
    (config=d5-nophys) -- NUEVAS, medidas por b25_phys_corpus.py."""
    d = json.load(io.open(os.path.join(JS, f"b25_{config}.json"), encoding="utf-8"))
    tabla = {doc: {} for doc in docs}
    for r in d["rows"]:
        if r["psm"] == psm and r["doc"] in tabla:
            tabla[r["doc"]][r["factor"]] = r["cer_pct"]
    return tabla, d["ruido"], d["etiqueta_ruido"]


def optimo_doc(fila):
    vals = [(f, fila[f]) for f in FACTORES if f in fila]
    if not vals:
        return None
    return min(c for _f, c in vals)


def regret_por_k(tabla, docs):
    mejores = {doc: optimo_doc(tabla[doc]) for doc in docs}
    reg = {}
    for f in FACTORES:
        difs = []
        for doc in docs:
            if f in tabla[doc] and mejores[doc] is not None:
                difs.append(tabla[doc][f] - mejores[doc])
        if difs:
            reg[f] = (round(statistics.mean(difs), 2), round(max(difs), 2))
    return reg, mejores


def resumen(tabla, docs):
    reg, mejores = regret_por_k(tabla, docs)
    if not reg:
        return None
    kmej = min(reg, key=lambda f: reg[f][0])
    return {"k": kmej, "regret_medio": reg[kmej][0], "regret_max": reg[kmej][1],
            "regret_por_factor": {f"{f:g}": v for f, v in reg.items()},
            "optimo_por_doc": {doc: (min(((f, c) for f, c in tabla[doc].items()),
                                          key=lambda x: x[1]) if tabla[doc] else None)
                               for doc in docs}}


def main():
    celdas = {}
    # C: viejo, sin pHYs -- YA MEDIDA
    for psm in ("3", "11"):
        tabla = cargar_celda_C(psm)
        celdas[("viejo", "sin_phys", psm)] = (tabla, resumen(tabla, DOCS_VIEJO), "existente")
    # D: d5, con pHYs -- YA MEDIDA
    for psm in ("3", "11"):
        tabla = cargar_celda_D(psm)
        celdas[("d5", "con_phys", psm)] = (tabla, resumen(tabla, DOCS_D5), "existente")
    # A: viejo, con pHYs -- NUEVA
    ruido_a = {}
    for psm in ("3", "11"):
        tabla, ruido, etq = cargar_celda_nueva("viejo-phys", psm, DOCS_VIEJO)
        celdas[("viejo", "con_phys", psm)] = (tabla, resumen(tabla, DOCS_VIEJO), "nueva")
        ruido_a[psm] = (ruido, etq)
    # B: d5, sin pHYs -- NUEVA
    ruido_b = {}
    for psm in ("3", "11"):
        tabla, ruido, etq = cargar_celda_nueva("d5-nophys", psm, DOCS_D5)
        celdas[("d5", "sin_phys", psm)] = (tabla, resumen(tabla, DOCS_D5), "nueva")
        ruido_b[psm] = (ruido, etq)

    out = {}
    for (corpus, phys, psm), (tabla, res, origen) in celdas.items():
        out[f"{corpus}__{phys}__psm{psm}"] = {"origen": origen, "resumen": res,
                                               "tabla": tabla}
    out["ruido_nuevas"] = {"viejo-phys": ruido_a, "d5-nophys": ruido_b}
    json.dump(out, io.open(os.path.join(JS, "analisis_2x2.json"), "w", encoding="utf-8"),
               ensure_ascii=False, indent=2)

    # --- imprime el 2x2 para pegar en el informe ---
    for psm in ("3", "11"):
        print(f"\n=== psm {psm} ===")
        print(f"{'':20s} {'sin pHYs':>18s} {'con pHYs':>18s}")
        for corpus, etiqueta in (("viejo", "corpus viejo"), ("d5", "corpus d5")):
            fila = []
            for phys in ("sin_phys", "con_phys"):
                r = celdas[(corpus, phys, psm)][1]
                origen = celdas[(corpus, phys, psm)][2]
                if r:
                    fila.append(f"k={r['k']:g} (reg {r['regret_medio']:.2f}/"
                                f"{r['regret_max']:.2f}) [{origen}]")
                else:
                    fila.append("—")
            print(f"{etiqueta:20s} {fila[0]:>18s} {fila[1]:>18s}")

    print("\nescrito json/analisis_2x2.json")


if __name__ == "__main__":
    main()
