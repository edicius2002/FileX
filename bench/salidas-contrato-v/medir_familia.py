#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C29 — ¿cuanto cuesta llevar el nivel de `familia` al veredicto?

Hoy `punto1_estado` devuelve `familia` cuando la firma cae en la familia
correcta pero no identifica el formato exacto (`.csv` es texto, pero no se
comprueba que sea CSV y no TSV). El hallazgo es `G5 informativo` y la cobertura
cuenta el punto 1 como CUBIERTO. Una lectura estricta las dejaria en
`ok_parcial`, igual que discutio `bench/verificador-ghostscript.md` §2.4 para la
verdad vacua de V5.

La pregunta no se responde opinando: se cuenta.

  1. Cuantas de las 53 del patron oro se moverian.
  2. Que extensiones estan en `EXT_FAMILIA` y cuantas de ellas son destinos
     reales del proyecto.
  3. Cuantas se moverian sobre un conjunto ANCHO de salidas reales: las 45
     celdas que escribieron fichero en `g6.json`.
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-verificacion"))

from filex import verificador as V          # noqa: E402
from trabajos import trabajos               # noqa: E402


def main():
    res = {}

    # ---- 1. las 53 -------------------------------------------------------
    filas = []
    # Censo VACIO: el punto 5 se declara cubierto y sin hallazgos. Hace falta
    # porque sin el las 53 salen ya `ok_parcial` por el punto 5 y la pregunta de
    # C29 no se puede ni formular: todo se moveria a un sitio en el que ya esta.
    censo = {"antes": {}, "despues": {}}
    for t in trabajos():
        se = V.sondear(t["entrada"])
        se.update(t["extra_entrada"])
        r = V.verificar(t["salida"], t["pedido"], t["entrada"], sonda_ent=se,
                        censo=censo)
        p1 = r["punto1"]
        # el veredicto que saldria con la lectura ESTRICTA: `familia` deja de
        # contar como cobertura del punto 1
        cob = dict(r["cobertura"])
        cob["1_firma"] = p1 in ("evaluado", "no_aplica")
        estricto = r["veredicto"]
        if estricto == "ok" and not all(cob.values()):
            estricto = "ok_parcial"
        filas.append({"salida": os.path.basename(t["salida"]),
                      "ext": os.path.splitext(t["salida"])[1].lower(),
                      "punto1": p1, "veredicto": r["veredicto"],
                      "veredicto_estricto": estricto,
                      "se_mueve": estricto != r["veredicto"]})
    mueve = [f for f in filas if f["se_mueve"]]
    fam = [f for f in filas if f["punto1"] == "familia"]
    print("PATRON ORO n=%d  punto1: %s" % (len(filas), {
        e: sum(1 for f in filas if f["punto1"] == e)
        for e in ("evaluado", "familia", "no_aplica", "sin_vocabulario")}))
    print("  se moverian a ok_parcial: %d  %s"
          % (len(mueve), [f["salida"] for f in mueve]))
    res["oro"] = {"n": len(filas), "familia": len(fam), "se_mueven": len(mueve),
                  "detalle_familia": [f["salida"] for f in fam],
                  "detalle_mueven": [f["salida"] for f in mueve],
                  "filas": filas}

    # ---- 2. el vocabulario ----------------------------------------------
    print("\nEXT_FAMILIA n=%d: %s" % (len(V.EXT_FAMILIA), sorted(V.EXT_FAMILIA)))
    ext_oro = sorted({f["ext"] for f in filas})
    print("extensiones de destino del patron oro: %s" % ext_oro)
    print("interseccion: %s" % sorted(set(ext_oro) & V.EXT_FAMILIA))
    res["vocabulario"] = {"ext_familia": sorted(V.EXT_FAMILIA),
                          "ext_oro": ext_oro,
                          "interseccion": sorted(set(ext_oro) & V.EXT_FAMILIA)}

    # ---- 3. el conjunto ANCHO -------------------------------------------
    ancho = []
    g6j = os.path.join(AQUI, "g6.json")
    if os.path.exists(g6j):
        with open(g6j, encoding="utf-8") as fh:
            d = json.load(fh)
        for f in d["parte_a"] + d["parte_a2"] + d["parte_b"]:
            g = f.get("g6")
            if not g:
                continue
            ancho.append({"clave": "%s/%s" % (f.get("motor") or f.get("caso"),
                                              f.get("ext")),
                          "punto1": g["punto1"], "veredicto": g["veredicto"]})
    cuenta = {e: sum(1 for a in ancho if a["punto1"] == e)
              for e in ("evaluado", "familia", "no_aplica", "sin_vocabulario")}
    # solo se mueven las que hoy salen `ok` Y tienen punto1 == familia
    mueven_ancho = [a for a in ancho
                    if a["punto1"] == "familia" and a["veredicto"] == "ok"]
    print("\nCONJUNTO ANCHO n=%d  punto1: %s" % (len(ancho), cuenta))
    print("  se moverian: %d" % len(mueven_ancho))
    res["ancho"] = {"n": len(ancho), "punto1": cuenta,
                    "se_mueven": len(mueven_ancho),
                    "detalle": [a["clave"] for a in mueven_ancho]}

    with open(os.path.join(AQUI, "familia.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print("\n-> familia.json")


if __name__ == "__main__":
    main()
