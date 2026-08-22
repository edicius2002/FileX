# -*- coding: utf-8 -*-
"""K2 / hito 3 - el diff que hace de prueba.

Compara los volcados de _reg53_hito3.py ignorando SOLO las tres claves que
tienen que diferir (`fuente`, `modulo`, `fichero`: dicen de donde se cargo el
modulo, que es justo lo que cambia). Cualquier otra diferencia es un fallo de
la mudanza.

    python _compara.py reg53_antes.json reg53_despues.json [reg53_envoltorio.json]
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
IGNORA = {"fuente", "modulo", "fichero"}


def carga(nom):
    with open(os.path.join(AQUI, nom), encoding="utf-8") as fh:
        d = json.load(fh)
    return {k: v for k, v in d.items() if k not in IGNORA}


def rutas(o, pre=""):
    """Aplana a {ruta: valor_hoja} para poder decir DONDE difiere."""
    if isinstance(o, dict):
        for k in sorted(o):
            yield from rutas(o[k], "%s.%s" % (pre, k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from rutas(v, "%s[%d]" % (pre, i))
    else:
        yield pre, o


def compara(a, b, na, nb):
    ra, rb = dict(rutas(a)), dict(rutas(b))
    dif = []
    for k in sorted(set(ra) | set(rb)):
        va, vb = ra.get(k, "<AUSENTE>"), rb.get(k, "<AUSENTE>")
        if va != vb:
            dif.append((k, va, vb))
    print("=== %s  vs  %s ===" % (na, nb))
    print("  hojas comparadas: %d / %d" % (len(ra), len(rb)))
    if not dif:
        print("  IDENTICOS: 0 diferencias")
    else:
        print("  %d DIFERENCIAS:" % len(dif))
        for k, va, vb in dif[:80]:
            print("    %s\n      %s -> %s" % (k, va, vb))
    return len(dif)


if __name__ == "__main__":
    noms = sys.argv[1:] or ["reg53_antes.json", "reg53_despues.json"]
    base = carga(noms[0])
    total = 0
    for otro in noms[1:]:
        total += compara(base, carga(otro), noms[0], otro)
    print("\nTOTAL DIFERENCIAS: %d" % total)
    sys.exit(1 if total else 0)
