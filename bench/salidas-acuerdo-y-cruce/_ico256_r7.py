# -*- coding: utf-8 -*-
"""Remedida de las siete `*->ico` con la semilla D (256x144), n=3.

Copia adaptada del bloque de `bench/sondeo-imagemagick.md` sec.3.2 (no se
guardo como script en su dia). Mismo formato de salida que
`bench/salidas-sondeo-im/ico256.json`: {origen: {"ms": float, "veredicto": str}}.

Uso: python _ico256_r7.py <dir_semillas_D> <dir_salidas> <destino.json>
"""
from __future__ import annotations

import json
import os
import statistics
import sys

RAIZ = "C:/Users/krato/orca/workspaces/FileX/filex-cpu"
sys.path.insert(0, RAIZ)

from filex.grafo import Arista, Grafo, SIN_SONDEAR  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

FORMATOS = ["png", "jpg", "webp", "avif", "gif", "bmp", "tif"]


def main() -> None:
    sem, out_dir, destino = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    fx = FileX()
    build = fx.motores["imagemagick"].build

    out = {}
    for fmt in FORMATOS:
        src = os.path.join(sem, "D." + fmt)
        fx.grafo = Grafo([Arista(origen=fmt, destino="ico", motor="imagemagick",
                                 build=build, parametrizacion="", estado=SIN_SONDEAR,
                                 coste=1.0)])
        tiempos, ultimo = [], None
        salida = os.path.join(out_dir, "D2ico." + fmt + ".ico")
        for _ in range(3):
            if os.path.isfile(salida):
                os.remove(salida)
            c = fx.convertir(src, salida, timeout=120.0)
            ultimo = c
            if c.saltos and c.saltos[0].ms:
                tiempos.append(c.saltos[0].ms)
        s = ultimo.saltos[0] if ultimo and ultimo.saltos else None
        out[fmt] = {"ms": round(statistics.median(tiempos), 1) if tiempos else None,
                    "veredicto": ultimo.veredicto if ultimo else "?"}
        print(fmt, "->", out[fmt])

    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print("escrito", destino)


if __name__ == "__main__":
    main()
