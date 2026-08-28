#!/usr/bin/env python3
"""Un proceso que TIENE un fichero abierto y no hace nada más. Portable.

Se usa desde los dos lados del cruce (Windows y WSL2) sin cambiar una letra.
Emite `ABIERTO <bytes>` en cuanto el descriptor está abierto —ese es el
marcador que la sonda espera, para no dormir a ciegas (trampa 38)— y se queda
así los segundos que le digan.
"""

from __future__ import annotations

import argparse
import os
import time


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ruta", required=True)
    p.add_argument("--modo", default="ab", choices=["ab", "rb", "wb"])
    p.add_argument("--segundos", type=float, default=20.0)
    a = p.parse_args(argv)

    with open(a.ruta, a.modo) as fh:
        if a.modo == "rb":
            fh.read(1)
        try:
            tam = os.path.getsize(a.ruta)
        except OSError:
            tam = -1
        print(f"ABIERTO {tam}", flush=True)
        time.sleep(a.segundos)
    print("CERRADO", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
