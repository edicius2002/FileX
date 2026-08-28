#!/usr/bin/env python3
"""Un `filex` vivo con un desechable de R18 y **ningún fichero abierto dentro**.

Es la ventana que la escena C no reproduce en Windows: mientras el motor escribe,
el sistema protege el fichero y un barrido ingenuo no puede llevárselo. Pero
entre que el motor cierra su salida y `t.recoger()` la mueve al destino hay un
tramo —el censo del punto 5 y el contrato entero, que sobre un ráster grande son
cientos de milisegundos— en el que dentro del desechable **no hay nada abierto**
y el directorio es perfectamente borrable.

Imprime `LISTO <ruta>` cuando el desechable existe con su fichero YA CERRADO, y
espera. Al recibir cualquier línea por `stdin` comprueba si su fichero sigue ahí
y lo dice: `RESULTADO <existe_dir> <existe_fichero>`.
"""

from __future__ import annotations

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bytes", type=int, default=4096)
    a = p.parse_args(argv)

    from filex.trabajo import DirectorioDeTrabajo

    t = DirectorioDeTrabajo()
    dentro = t.destino("salida.bin")
    with open(dentro, "wb") as fh:
        fh.write(b"\x00" * a.bytes)
    print(f"LISTO {t.ruta}", flush=True)
    sys.stdin.readline()
    print(f"RESULTADO {os.path.isdir(t.ruta)} {os.path.isfile(dentro)}",
          flush=True)
    t.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
