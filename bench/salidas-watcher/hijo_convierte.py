#!/usr/bin/env python3
"""Un `filex` de VERDAD que convierte y se deja matar. Para N14.

Imprime `LISTO <pid>` en cuanto el núcleo está construido —el sondeo tarda—, y
luego `ARRANCA` justo antes de llamar a `convertir`. Los dos marcadores son lo
que permite matarlo **dentro de la conversión** y no antes, que es la trampa 38:
un arnés que mata mientras el proceso todavía está sondeando motores no
reproduce nada, porque en ese momento no hay ningún desechable creado.

Si termina, imprime `FIN <ok> <veredicto>`; si lo matan, no imprime nada — y esa
ausencia es la prueba de que murió a mitad.
"""

from __future__ import annotations

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--entrada", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--timeout", type=float, default=300.0)
    a = p.parse_args(argv)

    from filex.nucleo import FileX

    fx = FileX()
    print(f"LISTO {os.getpid()}", flush=True)
    print("ARRANCA", flush=True)
    conv = fx.convertir(a.entrada, a.salida, {}, timeout=a.timeout)
    print(f"FIN {conv.ok} {conv.veredicto}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
