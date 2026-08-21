# -*- coding: utf-8 -*-
"""FASE 2: metrica comun de precision de OCR.

Referencia identica a la de fase 1, para que las cifras sean comparables:
    DOCUMENTO ESCANEADO / Texto que solo existe como pixeles. / Debe recuperarse con OCR.

Se reportan dos cosas:
  * por frase: distancia de edicion minima sobre ventana deslizante (como en fase 1)
  * global:    CER = distancia_edicion(referencia_completa, salida) / len(referencia)
"""
import json
import re
import sys
import unicodedata

ESPERADO = [
    "DOCUMENTO ESCANEADO",
    "Texto que solo existe como pixeles.",
    "Debe recuperarse con OCR.",
]
REFERENCIA = " ".join(ESPERADO)


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def lev(a, b):
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


def evaluar(texto):
    n = norm(texto)
    ref = norm(REFERENCIA)
    det = []
    for e in ESPERADO:
        ne = norm(e)
        exacto = ne in n
        best = 0 if exacto else min(
            (lev(ne, n[i:i + len(ne)]) for i in range(max(1, len(n) - len(ne) + 1))),
            default=len(ne))
        det.append({"esperado": e, "exacto": exacto, "dist": best,
                    "sim_pct": round(100 * (1 - best / max(1, len(ne))), 1)})
    d_global = lev(ref, n)
    return {
        "chars_salida": len(texto),
        "frases_exactas": sum(1 for d in det if d["exacto"]),
        "dist_global": d_global,
        "cer_pct": round(100 * d_global / len(ref), 1),
        "acierto_pct": round(100 * max(0.0, 1 - d_global / len(ref)), 1),
        "detalle": det,
        "normalizada": n,
    }


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        t = open(ruta, encoding="utf-8", errors="replace").read()
        r = evaluar(t)
        r["archivo"] = ruta
        print(json.dumps(r, ensure_ascii=False))
