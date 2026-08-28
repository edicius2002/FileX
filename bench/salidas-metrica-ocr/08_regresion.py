# -*- coding: utf-8 -*-
"""A7 / paso 8 — REGRESION del arnes compartido tras el cambio.

`bench/scripts/ocr_eval.py` es arnes COMPARTIDO (`CLAUDE.md` §1). Cambiarlo
solo es legitimo si se demuestra que:

  (1) la via CIEGA sigue dando EXACTAMENTE lo que daba antes. El testigo es
      `ocr_eval_ciego.py`, que es el fichero ORIGINAL copiado byte a byte a
      este directorio ANTES de tocarlo.
  (2) la via CANONICA nueva da exactamente la metrica acentuada de
      `ocr_eval_d4.py::norm_acentos`, que ya produjo 2 279 celdas publicadas.
  (3) la API que otros arneses importan (`norm`, `lev`, `evaluar`, ...) sigue
      en pie, y `norm` sigue siendo la CIEGA (la importa `ocr_gs.py`).

Dos niveles, por coste (MEDIDO: el `detalle` por frase es una ventana
deslizante con `lev` en Python puro, O(|salida| * |frase|^2), y sobre las 2 917
celdas no termina en un tiempo razonable):

  NIVEL A — las 2 917 celdas, comparando las NORMALIZACIONES y el CER GLOBAL,
            que es lo unico que se publica en las tablas.
  NIVEL B — una muestra de 120 celdas repartida por informe, comparando el
            diccionario ENTERO que devuelve `evaluar`, `detalle` incluido.
"""
import io
import json
import os
import sys

from rapidfuzz.distance import Levenshtein

AQUI = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(BENCH, "scripts"))

import ocr_eval as NUEVO          # noqa: E402  el arnes ya modificado
import ocr_eval_ciego as VIEJO    # noqa: E402  copia byte a byte del original
import ocr_eval_d4 as D4          # noqa: E402  el acentuado que publico 2 279 celdas

MUESTRA_POR_INFORME = 12


def main():
    inv = json.load(io.open(os.path.join(AQUI, "inventario.json"), encoding="utf-8"))
    entradas = inv["mapeados"]

    # (3) API ---------------------------------------------------------------
    fallos_api = []
    for nom in ("norm", "norm_ciega", "norm_acentos", "lev", "evaluar",
                "ESPERADO", "REFERENCIA", "METRICA_CANONICA"):
        if not hasattr(NUEVO, nom):
            fallos_api.append("falta " + nom)
    if getattr(NUEVO, "norm", None) is not getattr(NUEVO, "norm_ciega", 1):
        fallos_api.append("norm ya no apunta a la ciega")
    if NUEVO.ESPERADO != VIEJO.ESPERADO or NUEVO.REFERENCIA != VIEJO.REFERENCIA:
        fallos_api.append("la referencia cambio")
    for a, b in (("", "abc"), ("abc", ""), ("añadio", "anadio"),
                 (VIEJO.REFERENCIA, "DOCUMENTO ESCANEADO")):
        if NUEVO.lev(a, b) != VIEJO.lev(a, b):
            fallos_api.append("lev difiere")

    # NIVEL A ---------------------------------------------------------------
    ref_v = VIEJO.norm(VIEJO.REFERENCIA)
    ref_n_ciego = NUEVO.norm_ciega(NUEVO.REFERENCIA)
    ref_n_acent = NUEVO.norm_acentos(NUEVO.REFERENCIA)
    ref_d4 = D4.norm_acentos(NUEVO.REFERENCIA)
    a_ciego = a_acent = 0
    d_ciego, d_acent = [], []
    for e in entradas:
        t = io.open(os.path.join(BENCH, e["rel"].replace("/", os.sep)),
                    encoding="utf-8", errors="replace").read()
        nv, nn = VIEJO.norm(t), NUEVO.norm_ciega(t)
        cv = round(100 * Levenshtein.distance(ref_v, nv) / len(ref_v), 1)
        cn = round(100 * Levenshtein.distance(ref_n_ciego, nn) / len(ref_n_ciego), 1)
        if nv == nn and cv == cn:
            a_ciego += 1
        else:
            d_ciego.append(e["rel"])
        na, nd = NUEVO.norm_acentos(t), D4.norm_acentos(t)
        ca = round(100 * Levenshtein.distance(ref_n_acent, na) / len(ref_n_acent), 1)
        cd = round(100 * Levenshtein.distance(ref_d4, nd) / len(ref_d4), 1)
        if na == nd and ca == cd:
            a_acent += 1
        else:
            d_acent.append(e["rel"])

    # NIVEL B ---------------------------------------------------------------
    muestra, vistos = [], {}
    for e in entradas:
        k = e["informe"]
        if vistos.get(k, 0) < MUESTRA_POR_INFORME:
            vistos[k] = vistos.get(k, 0) + 1
            muestra.append(e)
    b_ok = 0
    d_b = []
    for e in muestra:
        t = io.open(os.path.join(BENCH, e["rel"].replace("/", os.sep)),
                    encoding="utf-8", errors="replace").read()
        v = VIEJO.evaluar(t)
        n = NUEVO.evaluar(t, "ciego")
        campos = ("chars_salida", "frases_exactas", "dist_global", "cer_pct",
                  "acierto_pct", "normalizada", "detalle")
        if all(v[c] == n[c] for c in campos):
            b_ok += 1
        else:
            d_b.append({"rel": e["rel"],
                        "difieren": [c for c in campos if v[c] != n[c]]})

    print("NIVEL A — las %d celdas (normalizacion + CER global)" % len(entradas))
    print("  (1) via CIEGA identica al original     : %d / %d  (discrep. %d)"
          % (a_ciego, len(entradas), len(d_ciego)))
    print("  (2) via CANONICA identica a ocr_eval_d4: %d / %d  (discrep. %d)"
          % (a_acent, len(entradas), len(d_acent)))
    print("NIVEL B — %d celdas, diccionario ENTERO de evaluar() incluido `detalle`"
          % len(muestra))
    print("  via CIEGA identica al original         : %d / %d  (discrep. %d)"
          % (b_ok, len(muestra), len(d_b)))
    print("(3) API                                  : %s"
          % ("OK" if not fallos_api else "; ".join(fallos_api)))
    for x in (d_ciego[:5] + d_acent[:5]):
        print("    " + str(x))
    for x in d_b[:5]:
        print("    " + str(x))
    ok = not (d_ciego or d_acent or d_b or fallos_api)
    print("VEREDICTO: %s" % ("VERDE" if ok else "ROJO"))
    json.dump({"nivel_a_n": len(entradas), "ciega_ok": a_ciego,
               "acent_ok": a_acent, "nivel_b_n": len(muestra), "b_ok": b_ok,
               "disc_ciega": d_ciego, "disc_acent": d_acent, "disc_b": d_b,
               "api": fallos_api or "OK", "veredicto": "VERDE" if ok else "ROJO"},
              io.open(os.path.join(AQUI, "regresion.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
