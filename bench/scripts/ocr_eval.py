# -*- coding: utf-8 -*-
"""Metrica comun de precision de OCR del proyecto. ARNES COMPARTIDO.

=============================================================================
QUE MIDE ESTE FICHERO, Y DESDE CUANDO
=============================================================================
Desde el **2026-08-28** (informe `bench/metrica-ocr.md`, agente A7) la lectura
CANONICA de este arnes —la que sale en `cer_pct`— es la **ACENTUADA**:

    NFC + minusculas + se conserva [a-z0-9 áéíóúüñ y el espacio]
    (todo lo demas, puntuacion incluida, pasa a espacio)

**Hasta esa fecha la canonica era la CIEGA A LAS TILDES** (`CLAUDE.md` trampa
10): `NFKD` + descarte de combinantes + `[^a-z0-9 ]`, que planchaba `razón` a
`razon` y `ñ` a `n`, es decir **normalizaba exactamente el error que se queria
medir** en castellano.

La via ciega NO se ha borrado: sigue disponible y produce cifras identicas a
las publicadas antes de esa fecha.

    evaluar(t)                    -> canonica (acentuada)
    evaluar(t, "ciego")           -> la de antes, bit a bit
    norm(t) / norm_ciega(t)       -> la normalizacion ciega, SIN CAMBIOS
    norm_acentos(t)               -> la normalizacion canonica
    python ocr_eval.py f.txt      -> canonica
    python ocr_eval.py --ciego f.txt
    python ocr_eval.py --ambas f.txt

Y `evaluar` devuelve **siempre las dos lecturas** (`cer_acentos_pct` y
`cer_ciego_pct`) mas la clave `metrica`, que dice cual de las dos esta copiada
en `cer_pct`. Una tabla de CER de este repositorio sin esa clave es una tabla
que no se puede juntar con otra.

=============================================================================
POR QUE SE CAMBIO, Y QUE PRECIO TUVO — MEDIDO (`bench/metrica-ocr.md`)
=============================================================================
Recalculando las **2 917** salidas de OCR ya almacenadas en `bench/salidas-*`:

  * de las **628** celdas de los informes que habian usado la via ciega
    (`ocr-ppp-nativos.md`, `ocrmypdf.md`, `verificador-ghostscript.md`),
    cambian **4** al pasar a la acentuada — y **`ocr-ppp-nativos.md` cambia 0
    de 296**. Cero inversiones de orden, cero cambios de ganador.
  * la alternativa que tambien circulaba por el repositorio,
    `ocr_eval_tildes.py`, conserva ADEMAS la puntuacion `. , ; : ! ? ¿ ¡`.
    Con ella cambiarian **285** de esas 628 celdas y **21 familias**
    cambiarian de configuracion ganadora. **No es la misma metrica y no se
    adopto**: `[a-z0-9áéíóúüñ ]` es lo que prescribe la trampa 10.

=============================================================================
REFERENCIA
=============================================================================
La de la fase 1 y la fase 2, para que las cifras sean comparables:
    DOCUMENTO ESCANEADO / Texto que solo existe como pixeles. / Debe recuperarse con OCR.
**No tiene ni un diacritico** (79 caracteres, `CLAUDE.md` trampa 9: cuantiza a
1,27 puntos por caracter). Por eso el cambio de metrica no mueve las tablas
del corpus legado: para juzgar castellano hace falta ademas una referencia que
lo lleve — la de `escaneado_d4`, 610 caracteres y 35 acentuados.

Se reportan dos cosas:
  * por frase: distancia de edicion minima sobre ventana deslizante (fase 1)
  * global:    CER = distancia_edicion(referencia_completa, salida) / len(ref)
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

# --- identidad de la metrica: va en cada resultado, a proposito -------------
METRICA_CANONICA = "acentos"
METRICA_DESDE = "2026-08-28"
METRICAS = ("acentos", "ciego")

_ACENTOS = "áéíóúüñ"


def norm_ciega(s):
    """La normalizacion CIEGA A LAS TILDES. Fue la canonica hasta el 2026-08-28
    y sigue aqui sin un solo cambio: es lo que reproduce las cifras publicadas
    antes de esa fecha."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_acentos(s):
    """La normalizacion CANONICA. NFC para que 'á' sea UN caracter y no dos: si
    llegara descompuesto, la distancia de edicion lo contaria doble.
    DESCARTA la puntuacion, igual que la ciega: el unico factor que cambia
    respecto de ella son los diacriticos."""
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"[^a-z0-9" + _ACENTOS + r" ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# `norm` es el nombre historico y sigue apuntando a la CIEGA: hay arneses que
# lo importan para normalizar su propia referencia (p. ej. `ocr_gs.py`) y
# cambiarselo por debajo alteraria cifras suyas sin avisar.
norm = norm_ciega

_NORMAS = {"acentos": norm_acentos, "ciego": norm_ciega}


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


def _global(texto, nf, esperado):
    ref = nf(" ".join(esperado))
    n = nf(texto)
    d = lev(ref, n)
    return n, len(ref), d, round(100 * d / max(1, len(ref)), 1)


def evaluar(texto, metrica=METRICA_CANONICA, esperado=None):
    """Evalua `texto` contra la referencia.

    `metrica`: "acentos" (canonica) o "ciego" (la de antes del 2026-08-28).
    El resultado trae SIEMPRE las dos lecturas y la clave `metrica`, que dice
    cual de las dos esta copiada en `cer_pct`/`acierto_pct`/`detalle`.
    """
    if metrica not in _NORMAS:
        raise ValueError("metrica desconocida: %r (usa %s)" % (metrica, METRICAS))
    esp = list(esperado) if esperado else list(ESPERADO)
    nf = _NORMAS[metrica]

    n = nf(texto)
    det = []
    for e in esp:
        ne = nf(e)
        exacto = ne in n
        best = 0 if exacto else min(
            (lev(ne, n[i:i + len(ne)]) for i in range(max(1, len(n) - len(ne) + 1))),
            default=len(ne))
        det.append({"esperado": e, "exacto": exacto, "dist": best,
                    "sim_pct": round(100 * (1 - best / max(1, len(ne))), 1)})

    _, lref, d_global, cer = _global(texto, nf, esp)
    out = {
        "metrica": metrica,
        "metrica_canonica": METRICA_CANONICA,
        "metrica_desde": METRICA_DESDE,
        "chars_salida": len(texto),
        "chars_ref": lref,
        "frases_exactas": sum(1 for x in det if x["exacto"]),
        "dist_global": d_global,
        "cer_pct": cer,
        "acierto_pct": round(100 * max(0.0, 1 - d_global / max(1, lref)), 1),
        "detalle": det,
        "normalizada": n,
    }
    # las DOS lecturas, siempre: sin esto dos tablas del repositorio no se
    # pueden juntar sin releer el codigo que las produjo.
    for m, f in _NORMAS.items():
        _, lr, dd, cc = _global(texto, f, esp)
        out["cer_%s_pct" % m] = cc
        out["dist_%s" % m] = dd
        out["chars_ref_%s" % m] = lr
    out["puntos_que_ocultaba_la_ciega"] = round(
        out["cer_acentos_pct"] - out["cer_ciego_pct"], 1)
    return out


if __name__ == "__main__":
    args = list(sys.argv[1:])
    metrica = METRICA_CANONICA
    ambas = False
    if "--ciego" in args:
        args.remove("--ciego")
        metrica = "ciego"
    if "--acentos" in args:
        args.remove("--acentos")
        metrica = "acentos"
    if "--ambas" in args:
        args.remove("--ambas")
        ambas = True
    for ruta in args:
        t = open(ruta, encoding="utf-8", errors="replace").read()
        if ambas:
            for m in METRICAS:
                r = evaluar(t, m)
                r["archivo"] = ruta
                print(json.dumps(r, ensure_ascii=False))
        else:
            r = evaluar(t, metrica)
            r["archivo"] = ruta
            print(json.dumps(r, ensure_ascii=False))
