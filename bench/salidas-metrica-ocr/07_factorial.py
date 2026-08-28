# -*- coding: utf-8 -*-
"""A7 / paso 7 — SEPARAR LOS DOS FACTORES que el inventario mezcla.

`ocr_eval.py` (ciego) y `ocr_eval_tildes.py` no se diferencian en UNA cosa: se
diferencian en DOS, y el proyecto las llama a las dos "la metrica acentuada".

    factor A (diacriticos): conservarlos o plancharlos con NFKD
    factor B (puntuacion) : conservar `. , ; : ! ? ¿ ¡` o mandarlos a espacio

  `ocr_eval.py`        -> A=no  B=no
  `ocr_eval_d4.py`     -> A=si  B=no      (solo el juego castellano áéíóúüñ)
  `ocr_eval_tildes.py` -> A=si  B=si      (todo el bloque latino À-ɏ)

Con solo esas tres no se puede atribuir nada: falta la cuarta esquina. Aqui se
construye A=no/B=si (metrica AUXILIAR, no se propone como canonica: existe solo
para poder repartir la culpa) y se mide el 2x2 completo sobre las mismas celdas.
"""
import io
import json
import os
import re
import statistics as st
import sys
import unicodedata

from rapidfuzz.distance import Levenshtein

AQUI = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
from d4_texto import BLOQUES as D4_BLOQUES  # noqa: E402

REF_TEXTO = {
    "legado": "DOCUMENTO ESCANEADO Texto que solo existe como pixeles. "
              "Debe recuperarse con OCR.",
    "d4": " ".join(" ".join(v) for v in D4_BLOQUES.values()),
    "tipico": " ".join(["FileX - documento de prueba con texto seleccionable",
                        "Segunda linea: acentos aeiou ñ y simbolos % & @",
                        "Tabla: Col A Col B Col C", "1 2 3"]),
    "acentos_gs": " ".join(["INFORME TÉCNICO",
                            "La conversión se añadió en el último año.",
                            "Ñandú, camión, acción, pequeñez y ambigüedad."]),
}
PUNT = r".,;:!?¿¡"


def _plancha(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def n00(s):  # A=no B=no  == ocr_eval.py
    s = _plancha(s).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def n01(s):  # A=no B=si  == la esquina que faltaba (auxiliar)
    s = _plancha(s).lower()
    return re.sub(r"\s+", " ",
                  re.sub(r"[^a-z0-9 " + re.escape(PUNT) + r"]+", " ", s)).strip()


def n10(s):  # A=si B=no  == ocr_eval_d4.py::norm_acentos
    s = unicodedata.normalize("NFC", s).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9áéíóúüñ ]+", " ", s)).strip()


def n11(s):  # A=si B=si  == ocr_eval_tildes.py::norm_tildes
    s = unicodedata.normalize("NFC", s).lower()
    return re.sub(r"\s+", " ",
                  re.sub(r"[^0-9a-zÀ-ɏ .,;:!?¿¡]+", " ", s)).strip()


ESQ = (("00_ciego", n00), ("01_solo_punt", n01),
       ("10_solo_acentos", n10), ("11_ambos", n11))


def main():
    inv = json.load(io.open(os.path.join(AQUI, "inventario.json"), encoding="utf-8"))
    refn = {r: {e: f(t) for e, f in ESQ} for r, t in REF_TEXTO.items()}
    filas = []
    for e in inv["mapeados"]:
        t = io.open(os.path.join(BENCH, e["rel"].replace("/", os.sep)),
                    encoding="utf-8", errors="replace").read()
        fila = {"rel": e["rel"], "informe": e["informe"], "doc": e["doc"],
                "ref": e["ref"]}
        for nom, f in ESQ:
            rn = refn[e["ref"]][nom]
            fila["cer_" + nom] = round(
                100.0 * Levenshtein.distance(rn, f(t)) / max(1, len(rn)), 4)
        filas.append(fila)

    def res(sel, a, b):
        v = [f["cer_" + b] - f["cer_" + a] for f in sel]
        av = [abs(x) for x in v]
        return (len(v), sum(1 for x in av if x < 1e-9),
                round(st.median(v), 3), round(max(av), 2) if av else 0.0)

    print("### 2x2: cuanto mueve cada factor por su cuenta (todas las %d celdas)"
          % len(filas))
    print("%-46s %6s %8s %8s %8s" % ("efecto", "n", "iguales", "mediana", "max|d|"))
    for etq, a, b in (
            ("SOLO acentos          (00 -> 10)", "00_ciego", "10_solo_acentos"),
            ("SOLO puntuacion       (00 -> 01)", "00_ciego", "01_solo_punt"),
            ("acentos + puntuacion  (00 -> 11)", "00_ciego", "11_ambos"),
            ("puntuacion sobre acentos (10 -> 11)", "10_solo_acentos", "11_ambos"),
            ("acentos sobre puntuacion (01 -> 11)", "01_solo_punt", "11_ambos")):
        n, ig, me, mx = res(filas, a, b)
        print("%-46s %6d %8d %+8.3f %8.2f" % (etq, n, ig, me, mx))

    print("\n### lo mismo, SOLO sobre el corpus legado (referencia sin un diacritico)")
    leg = [f for f in filas if f["ref"] == "legado"]
    for etq, a, b in (("SOLO acentos", "00_ciego", "10_solo_acentos"),
                      ("SOLO puntuacion", "00_ciego", "01_solo_punt"),
                      ("ambos", "00_ciego", "11_ambos")):
        n, ig, me, mx = res(leg, a, b)
        print("%-46s %6d %8d %+8.3f %8.2f" % (etq, n, ig, me, mx))

    print("\n### lo mismo, SOLO sobre la familia d4 (referencia con 35 acentuados)")
    d4 = [f for f in filas if f["ref"] == "d4"]
    for etq, a, b in (("SOLO acentos", "00_ciego", "10_solo_acentos"),
                      ("SOLO puntuacion", "00_ciego", "01_solo_punt"),
                      ("ambos", "00_ciego", "11_ambos")):
        n, ig, me, mx = res(d4, a, b)
        print("%-46s %6d %8d %+8.3f %8.2f" % (etq, n, ig, me, mx))

    # celdas 0,00 que dejan de serlo: es lo que caduca una tabla "sin error"
    print("\n### celdas con CER 0,00 con la ciega que DEJAN de estar a cero")
    ceros = [f for f in filas if f["cer_00_ciego"] < 1e-9]
    print("  celdas a 0,00 con la ciega: %d" % len(ceros))
    for nom in ("10_solo_acentos", "01_solo_punt", "11_ambos"):
        rot = [f for f in ceros if f["cer_" + nom] >= 1e-9]
        print("    dejan de ser 0,00 con %-16s: %4d   (%s)"
              % (nom, len(rot),
                 ", ".join(sorted({f["informe"] for f in rot})) or "-"))
    json.dump(filas, io.open(os.path.join(AQUI, "factorial.json"), "w",
                             encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
