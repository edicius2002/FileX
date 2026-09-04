# -*- coding: utf-8 -*-
"""Genera la tabla de `MANIFIESTO.md` de este directorio: nombre, sha256 y
tamaño de cada salida. La ORDEN que reproduce cada una se escribe a mano en el
manifiesto, porque es lo único que la máquina no puede deducir.

    python bench/salidas-marker-lock/hacer_manifiesto.py
"""
from __future__ import annotations

import hashlib
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
EXCLUIR = {"MANIFIESTO.md"}


def main() -> None:
    filas = []
    for nombre in sorted(os.listdir(AQUI)):
        ruta = os.path.join(AQUI, nombre)
        if not os.path.isfile(ruta) or nombre in EXCLUIR:
            continue
        with open(ruta, "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()
        filas.append((nombre, h, os.path.getsize(ruta)))
    print("| Fichero | `sha256` | Bytes |")
    print("|---|---|---|")
    for nombre, h, n in filas:
        print("| `%s` | `%s` | %d |" % (nombre, h, n))


if __name__ == "__main__":
    main()
