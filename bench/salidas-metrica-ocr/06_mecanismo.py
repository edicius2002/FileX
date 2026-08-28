# -*- coding: utf-8 -*-
"""A7 / paso 6 — el MECANISMO, sondeado y no deducido.

La sorpresa del paso 4 es que las 296 celdas de `bench/ocr-ppp-nativos.md` dan
EXACTAMENTE el mismo CER con la metrica ciega y con la acentuada de d4. Antes de
publicarlo hay que saber POR QUE, porque hay dos explicaciones incompatibles:

  (a) las salidas de OCR sobre el corpus legado NO CONTIENEN ni un caracter
      acentuado, asi que no hay nada que la metrica ciega pueda esconder; o
  (b) los contienen, y la coincidencia es una casualidad de la distancia de
      edicion.

Se cuenta, no se supone. Y de paso se aisla la otra variable que separa a las
dos metricas acentuadas entre si: la PUNTUACION.
"""
import io
import json
import os
import re
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(AQUI)

ACENTOS = set("áéíóúüñÁÉÍÓÚÜÑàèìòùâêîôûäëïöçÀÈÌÒÙÂÊÎÔÛÄËÏÖÇ")
PUNT = set(".,;:!?¿¡")


def main():
    r = json.load(io.open(os.path.join(AQUI, "recalculo.json"), encoding="utf-8"))
    filas = [f for f in r["filas"] if "cer_ciego" in f]

    por_ref = {}
    for f in filas:
        ruta = os.path.join(BENCH, f["rel"].replace("/", os.sep))
        t = io.open(ruta, encoding="utf-8", errors="replace").read()
        nac = sum(1 for c in t if c in ACENTOS)
        npu = sum(1 for c in t if c in PUNT)
        d = por_ref.setdefault(f["ref"], {"n": 0, "con_acento": 0, "acentos": 0,
                                          "con_punt": 0, "punt": 0,
                                          "delta0": 0, "ejemplos": []})
        d["n"] += 1
        d["acentos"] += nac
        d["punt"] += npu
        if nac:
            d["con_acento"] += 1
            if len(d["ejemplos"]) < 6:
                d["ejemplos"].append({"rel": f["rel"], "acentos": nac,
                                      "cer_ciego": f["cer_ciego"],
                                      "cer_d4ac": f["cer_d4ac"],
                                      "delta": f["delta_d4ac"]})
        if npu:
            d["con_punt"] += 1
        if abs(f["delta_d4ac"]) < 1e-9:
            d["delta0"] += 1

    print("### caracteres acentuados y de puntuacion PRESENTES en la salida del OCR")
    print("%-12s %6s %12s %10s %12s %10s %10s" %
          ("ref", "n", "con acento", "acentos", "con punt.", "punt.", "delta=0"))
    for ref in sorted(por_ref):
        d = por_ref[ref]
        print("%-12s %6d %12d %10d %12d %10d %10d" %
              (ref, d["n"], d["con_acento"], d["acentos"],
               d["con_punt"], d["punt"], d["delta0"]))

    print("\n### celdas del corpus LEGADO cuya salida SI trae acentos")
    d = por_ref.get("legado", {})
    for e in d.get("ejemplos", []):
        print("  %-70s acentos=%d  ciego=%.2f d4ac=%.2f (delta %+.2f)" %
              (e["rel"][-70:], e["acentos"], e["cer_ciego"], e["cer_d4ac"],
               e["delta"]))

    # --- las celdas de los informes CIEGOS que se moverian ------------------
    print("\n### celdas de los informes que usaron el evaluador CIEGO y que cambian")
    ciegos = ("ocr-ppp-nativos.md", "ocrmypdf.md", "verificador-ghostscript.md")
    for f in sorted(filas, key=lambda x: -abs(x["delta_d4ac"])):
        if f["informe"] in ciegos and abs(f["delta_d4ac"]) >= 1e-9:
            print("  M2 %+6.2f  ciego=%7.2f d4ac=%7.2f  %s"
                  % (f["delta_d4ac"], f["cer_ciego"], f["cer_d4ac"], f["rel"]))
    print("  --- y con la metrica de tildes (M3), las 10 mayores:")
    n = 0
    for f in sorted(filas, key=lambda x: -abs(x["delta_tildes"])):
        if f["informe"] in ciegos and abs(f["delta_tildes"]) >= 1e-9:
            print("  M3 %+6.2f  ciego=%7.2f tildes=%7.2f  %s"
                  % (f["delta_tildes"], f["cer_ciego"], f["cer_tildes"], f["rel"]))
            n += 1
            if n >= 10:
                break
    json.dump(por_ref, io.open(os.path.join(AQUI, "mecanismo.json"), "w",
                               encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
