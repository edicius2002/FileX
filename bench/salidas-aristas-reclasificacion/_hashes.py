# -*- coding: utf-8 -*-
"""Filas del MANIFIESTO. Se ejecuta a mano; su salida se pega en MANIFIESTO.md."""
import os, hashlib

AQUI = os.path.dirname(os.path.abspath(__file__))
for r, ds, fs in sorted(os.walk(AQUI)):
    for f in sorted(fs):
        ruta = os.path.join(r, f)
        rel = os.path.relpath(ruta, AQUI).replace(os.sep, "/")
        b = open(ruta, "rb").read()
        print("| `%s` | %d | `%s…` |" % (rel, len(b), hashlib.sha256(b).hexdigest()[:16]))
