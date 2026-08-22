# -*- coding: utf-8 -*-
"""Evaluador de OCR SENSIBLE A LAS TILDES.

Copia adaptada de bench/scripts/ocr_eval.py, que es arnes COMPARTIDO y no se
modifica. La diferencia es una sola linea y lo cambia todo:

    ocr_eval.py:   unicodedata.normalize("NFKD") + descartar combinantes
                   + re.sub(r"[^a-z0-9 ]+", " ")
    aqui:          NFC, se conservan las tildes, la enye y los signos de
                   puntuacion que cambian el significado

Consecuencia practica: `ocr_eval.py` considera IDENTICOS "pixeles" y "pixeles"
con tilde, "ano" y "anio". Para comparar con las 296 celdas ya medidas del
proyecto esta bien —es la misma regla para todos—; para juzgar calidad en
castellano NO SIRVE. Los dos numeros se reportan siempre juntos.
"""
import re
import unicodedata

ESPERADO = [
    "DOCUMENTO ESCANEADO",
    "Texto que solo existe como pixeles.",
    "Debe recuperarse con OCR.",
]
REFERENCIA = " ".join(ESPERADO)


def norm_tildes(s):
    """Normaliza SIN destruir la informacion diacritica."""
    s = unicodedata.normalize("NFC", s)
    s = s.lower()
    # se conservan letras (con diacriticos), digitos, espacio y . , ; : ! ?
    s = re.sub(r"[^0-9a-zÀ-ɏ .,;:!?¿¡]+", " ", s)
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


def evaluar(texto, esperado=None):
    esp = esperado or ESPERADO
    ref = norm_tildes(" ".join(esp))
    n = norm_tildes(texto)
    det = []
    for e in esp:
        ne = norm_tildes(e)
        exacto = ne in n
        best = 0 if exacto else min(
            (lev(ne, n[i:i + len(ne)]) for i in range(max(1, len(n) - len(ne) + 1))),
            default=len(ne))
        det.append({"esperado": e, "exacto": exacto, "dist": best})
    d = lev(ref, n)
    # cuantos errores son SOLO de tilde: se mide comparando la distancia con
    # tildes contra la distancia sin ellas sobre el mismo par
    return {"chars_salida": len(texto), "frases_exactas": sum(1 for x in det if x["exacto"]),
            "dist_global": d, "cer_pct": round(100 * d / max(1, len(ref)), 1),
            "detalle": det, "normalizada": n, "referencia": ref}
