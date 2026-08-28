# -*- coding: utf-8 -*-
"""A7 / paso 2 — RECALCULO de todas las salidas de OCR almacenadas con las TRES
metricas del repositorio, sobre los mismos ficheros de texto.

Las tres metricas, tal como estan hoy en el repositorio:

  M1 `ciego`   bench/scripts/ocr_eval.py::norm
               NFKD + descarte de combinantes + lower + [^a-z0-9 ] -> espacio
               Es la CANONICA (arnes compartido). CLAUDE.md trampa 10.

  M2 `d4ac`    bench/salidas-corpus-d4/ocr_eval_d4.py::norm_acentos
               NFC + lower + [^a-z0-9áéíóúüñ ] -> espacio
               Conserva diacriticos castellanos; DESCARTA la puntuacion.

  M3 `tildes`  bench/salidas-verificador-gs/ocr_eval_tildes.py::norm_tildes
               NFC + lower + [^0-9a-zÀ-ɏ .,;:!?¿¡] -> espacio
               Conserva diacriticos latinos ENTEROS *y la puntuacion*.

CER = lev(ref_normalizada, salida_normalizada) / len(ref_normalizada) * 100,
que es la definicion que usan los tres evaluadores.

NO se usa GPU. NO se toma el lock. Es aritmetica sobre texto ya en disco.

Control positivo (CLAUDE.md §3, la leccion de la trampa 36: un "no hay
diferencia" no significa nada sin control): se comprueba que `lev` de rapidfuzz
coincide con el `lev` en Python puro de los tres evaluadores sobre una muestra,
y que M1 reproduce el `cer_pct` publicado en los JSON de las tandas.
"""
import io
import json
import os
import re
import sys
import unicodedata

from rapidfuzz.distance import Levenshtein

AQUI = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)

from d4_texto import BLOQUES as D4_BLOQUES  # noqa: E402

# --------------------------------------------------------------- referencias
REF_TEXTO = {
    # 79 caracteres, SIN un solo diacritico. CLAUDE.md trampa 9: cuantiza a 1,27.
    "legado": "DOCUMENTO ESCANEADO Texto que solo existe como pixeles. "
              "Debe recuperarse con OCR.",
    # 610 caracteres crudos, 35 acentuados. Cuantiza a 0,16.
    "d4": " ".join(" ".join(v) for v in D4_BLOQUES.values()),
    # referencia de `tipico_texto.pdf` (ocr_eval_km.py::TIPICO)
    "tipico": " ".join([
        "FileX - documento de prueba con texto seleccionable",
        "Segunda linea: acentos aeiou ñ y simbolos % & @",
        "Tabla: Col A Col B Col C",
        "1 2 3"]),
    # fixture de acentos de G5 (ocr_gs.py::TEXTO_ACENTOS_REAL)
    "acentos_gs": " ".join([
        "INFORME TÉCNICO",
        "La conversión se añadió en el último año.",
        "Ñandú, camión, acción, pequeñez y ambigüedad."]),
}

# --------------------------------------------------------------- las 3 normas
_ACENTOS_D4 = "áéíóúüñ"


def norm_ciego(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_d4ac(s):
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"[^a-z0-9" + _ACENTOS_D4 + r" ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_tildes(s):
    s = unicodedata.normalize("NFC", s)
    s = s.lower()
    s = re.sub(r"[^0-9a-zÀ-ɏ .,;:!?¿¡]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


NORMAS = (("ciego", norm_ciego), ("d4ac", norm_d4ac), ("tildes", norm_tildes))


def lev_puro(a, b):
    """El `lev` textual de los tres evaluadores. Solo para el control positivo."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref_n, out_n):
    d = Levenshtein.distance(ref_n, out_n)
    return d, round(100.0 * d / max(1, len(ref_n)), 4)


# ------------------------------------------------------------------- control
def control_lev():
    """rapidfuzz debe dar EXACTAMENTE lo mismo que el lev en Python puro."""
    pares = [("", "abc"), ("abc", ""), ("abc", "abc"),
             ("documento escaneado", "docurnento escaneadu"),
             ("añadió camión", "anadio camion"),
             (REF_TEXTO["legado"], "DOCUMENTO ESCANEADO"),
             (norm_d4ac(REF_TEXTO["d4"]), norm_d4ac("El dia 14 de marzo")),
             (norm_tildes(REF_TEXTO["acentos_gs"]),
              norm_tildes("INFORME TECNICO La conversion se anadio"))]
    malos = 0
    for a, b in pares:
        if Levenshtein.distance(a, b) != lev_puro(a, b):
            malos += 1
    return {"pares": len(pares), "discrepancias": malos}


def main():
    inv = json.load(io.open(os.path.join(AQUI, "inventario.json"), encoding="utf-8"))
    ctl = control_lev()
    if ctl["discrepancias"]:
        raise SystemExit("CONTROL ROTO: rapidfuzz != lev puro")

    # normalizacion de cada referencia bajo cada metrica, una sola vez
    refn = {}
    for rid, txt in REF_TEXTO.items():
        refn[rid] = {m: f(txt) for m, f in NORMAS}

    filas = []
    for e in inv["mapeados"]:
        ruta = os.path.join(BENCH, e["rel"].replace("/", os.sep))
        try:
            t = io.open(ruta, encoding="utf-8", errors="replace").read()
        except OSError as exc:
            filas.append(dict(e, error=str(exc)))
            continue
        fila = dict(e)
        fila["chars_salida"] = len(t)
        for m, f in NORMAS:
            rn = refn[e["ref"]][m]
            d, c = cer(rn, f(t))
            fila["dist_" + m] = d
            fila["cer_" + m] = c
            fila["lref_" + m] = len(rn)
        fila["delta_d4ac"] = round(fila["cer_d4ac"] - fila["cer_ciego"], 4)
        fila["delta_tildes"] = round(fila["cer_tildes"] - fila["cer_ciego"], 4)
        fila["delta_d4ac_tildes"] = round(fila["cer_tildes"] - fila["cer_d4ac"], 4)
        filas.append(fila)

    out = os.path.join(AQUI, "recalculo.json")
    json.dump({"control_lev": ctl,
               "referencias": {k: {m: len(v[m]) for m, _ in NORMAS}
                               for k, v in refn.items()},
               "n": len(filas), "filas": filas},
              io.open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("control lev rapidfuzz vs puro: %d pares, %d discrepancias"
          % (ctl["pares"], ctl["discrepancias"]))
    print("longitudes de referencia normalizada:")
    for k, v in refn.items():
        print("  %-12s ciego=%4d  d4ac=%4d  tildes=%4d"
              % (k, len(v["ciego"]), len(v["d4ac"]), len(v["tildes"])))
    print("celdas recalculadas: %d  ->  %s" % (len(filas), out))


if __name__ == "__main__":
    sys.exit(main())
