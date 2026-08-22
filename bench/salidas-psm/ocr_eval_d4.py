# -*- coding: utf-8 -*-
"""G1 / evaluador de OCR con DOS metricas: con acentos y sin acentos.

COPIA ADAPTADA de bench/scripts/ocr_eval.py (que NO se toca: es arnes compartido).

Por que existe este fichero
---------------------------
`bench/scripts/ocr_eval.py` normaliza con:
    unicodedata.normalize("NFKD") + descarte de combinantes + re.sub(r"[^a-z0-9 ]+", " ")
Es decir, ESTRUCTURALMENTE CIEGO A LAS TILDES: "razon" y "razón" dan distancia 0, y
"ñ" se convierte en "n". Con ese evaluador, añadir un documento acentuado no mide nada.

Este evaluador reporta las dos lecturas sobre la MISMA salida:
  * cer_ascii   -> normalizacion IDENTICA a la de ocr_eval.py. Comparable con las
                   296 celdas ya medidas en bench/ocr-ppp-nativos.md.
  * cer_acentos -> normalizacion que CONSERVA tildes, diereses y eñes (NFC, minusculas,
                   se mantiene [a-z0-9áéíóúüñ ]). Es la que mide castellano de verdad.

Ademas separa el CER por BLOQUE de tamaño de letra (titulo / cuerpo / letra pequeña),
que es lo que permite ver si el fallo esta en el detector o en el reconocedor.

uso:  python ocr_eval_d4.py <referencia_id> fichero.txt [fichero.txt ...]
      referencia_id: d4 | legado
"""
import json
import re
import sys
import unicodedata

# --------------------------------------------------------------- referencias
# La referencia legado es la de los cuatro escaneados existentes (79 chars, SIN tildes).
LEGADO = {
    "cuerpo": [
        "DOCUMENTO ESCANEADO",
        "Texto que solo existe como pixeles.",
        "Debe recuperarse con OCR.",
    ],
}

# La referencia d4: castellano real, con tildes, dieresis, eñes, signos de apertura,
# cifras y puntuacion. Tres bloques de tamaño de letra decreciente.
D4 = {
    "titulo": [
        "INFORME DE DIGITALIZACION",       # se renderiza con tilde: DIGITALIZACIÓN
    ],
    "cuerpo": [
        "El dia 14 de marzo se recibio la solicitud de analisis",
        "tecnico sobre veintiun volumenes encuadernados en piel.",
        "La comision determino que la reproduccion fotografica",
        "debia realizarse con iluminacion difusa y sin contacto,",
        "segun la norma UNE 15-402, para evitar daños añadidos",
        "en los pliegos mas fragiles del año 1893.",
    ],
    "pequeña": [
        "¿Quien autorizo la excepcion? El parrafo tercero señala",
        "que la revision ortografica y la correccion de margenes",
        "son responsabilidad del area de conservacion preventiva.",
        "¡Atencion! Los codigos 7-B, 9-Ñ y 12-U quedan anulados.",
    ],
}

# NOTA: el diccionario de arriba es solo un esqueleto legible. El texto REAL, con sus
# tildes, esta en d4_texto.py (compartido con el generador) para que la referencia de
# medida y la pagina renderizada NO PUEDAN divergir.
try:
    from d4_texto import BLOQUES as D4_BLOQUES  # noqa: E402
except Exception:  # pragma: no cover
    D4_BLOQUES = None


def referencia(rid):
    if rid == "legado":
        return {"cuerpo": LEGADO["cuerpo"]}
    if D4_BLOQUES is None:
        raise SystemExit("falta d4_texto.py junto a este evaluador")
    return D4_BLOQUES


# --------------------------------------------------------------- normalizaciones
_ACENTOS = "áéíóúüñ"


def norm_ascii(s):
    """IDENTICA a bench/scripts/ocr_eval.py. Ciega a las tildes, a proposito."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_acentos(s):
    """Conserva tildes, dieresis y eñes. NFC para que 'á' sea UN caracter y no dos
    (si llegara descompuesto, la distancia de edicion lo contaria doble)."""
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"[^a-z0-9" + _ACENTOS + r" ]+", " ", s)
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


def _bloque(lineas, n, nf):
    """CER de un bloque contra la salida completa, por ventana deslizante."""
    ref = nf(" ".join(lineas))
    if not ref:
        return None
    # mejor alineamiento local: ventana del tamaño de la referencia +-20 %
    mejor = len(ref)
    paso = max(1, len(ref) // 40)
    for w in (len(ref), int(len(ref) * 1.25) + 1):
        for i in range(0, max(1, len(n) - w + 1), paso):
            d = lev(ref, n[i:i + w])
            if d < mejor:
                mejor = d
    if len(n) <= len(ref):
        mejor = min(mejor, lev(ref, n))
    return {"chars_ref": len(ref), "dist": mejor,
            "cer_pct": round(100 * mejor / len(ref), 2)}


def evaluar(texto, rid="d4"):
    bl = referencia(rid)
    plano = " ".join(" ".join(v) for v in bl.values())
    out = {"chars_salida": len(texto)}
    for etiqueta, nf in (("ascii", norm_ascii), ("acentos", norm_acentos)):
        n = nf(texto)
        ref = nf(plano)
        d = lev(ref, n)
        out[f"cer_{etiqueta}_pct"] = round(100 * d / max(1, len(ref)), 2)
        out[f"dist_{etiqueta}"] = d
        out[f"chars_ref_{etiqueta}"] = len(ref)
        out[f"normalizada_{etiqueta}"] = n
    # --- desglose por bloque (solo con la metrica de acentos, que es la fina) ---
    n = norm_acentos(texto)
    out["bloques"] = {k: _bloque(v, n, norm_acentos) for k, v in bl.items()}
    # --- lineas exactas: cuantas aparecen literalmente ---
    exactas = 0
    total = 0
    for v in bl.values():
        for linea in v:
            total += 1
            if norm_acentos(linea) in n:
                exactas += 1
    out["lineas_exactas"] = exactas
    out["lineas_totales"] = total
    # --- cuantos caracteres acentuados sobreviven ---
    ref_ac = sum(1 for c in norm_acentos(plano) if c in _ACENTOS)
    sal_ac = sum(1 for c in n if c in _ACENTOS)
    out["acentos_ref"] = ref_ac
    out["acentos_salida"] = sal_ac
    return out


if __name__ == "__main__":
    rid = sys.argv[1]
    for ruta in sys.argv[2:]:
        t = open(ruta, encoding="utf-8", errors="replace").read()
        r = evaluar(t, rid)
        r["archivo"] = ruta
        print(json.dumps(r, ensure_ascii=False))
