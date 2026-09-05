"""Cuarta sonda: un formato CONOCIDO sin ningun destino alcanzable
(rama `return 1` de `cli._destinos`), y si hay motores ausentes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from filex import formatos
from filex.nucleo import FileX

fx = FileX()
print("ausentes:", [(m.nombre, m.motivo_ausencia, m.binario) for m in fx.ausentes])
print("conocido('xyzzy') =", formatos.conocido("xyzzy"))
nombres = [n for n in dir(formatos) if not n.startswith("_")]
print("api formatos:", nombres[:20])
sin = []
for ext in sorted(getattr(formatos, "FORMATOS", {}) or {}):
    if not fx.destinos(ext):
        sin.append(ext)
print("conocidos sin destino:", sin[:20], "total", len(sin))
