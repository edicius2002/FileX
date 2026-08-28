#!/usr/bin/env python3
"""El cuerpo POSIX de `pruebas/test_watcher_n.py::CerrojoPosix`.

Se ejecuta DENTRO de WSL2 y usa **la función del watcher de verdad**, no una
copia: la sonda tiene su propia implementación para poder comparar siete
primitivos, pero una prueba que valida una copia no valida nada.

El tenedor también vive dentro de WSL2, a propósito: la observación **no cruza**
entre Windows y WSL2 —MEDIDO en las dos direcciones con control positivo— y un
tenedor de Windows daría un `libre` que parecería un fallo del código.

Imprime una línea de `clave=valor` que la prueba parsea. `condicion=True` es la
trampa 38: si el tenedor no llegó a abrir el fichero, la prueba se salta en vez
de contarse como aprobada.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raiz", required=True)
    p.add_argument("--tenedor", required=True)
    p.add_argument("--origen", required=True)
    a = p.parse_args(argv)

    sys.path.insert(0, a.raiz)
    from filex.watcher import _estable_en_disco, _tenedores_posix

    tmp = tempfile.mkdtemp(prefix="prueba-n4-")
    try:
        sujeto = os.path.join(tmp, "sujeto.png")
        shutil.copyfile(a.origen, sujeto)

        # --- sin escritor (control) ---------------------------------------
        replace_sin = "libre"
        try:
            os.replace(sujeto, sujeto)
        except OSError:
            replace_sin = "ocupado"
        proc_sin = "ocupado" if (_tenedores_posix(sujeto) or []) else "libre"
        estable_sin = _estable_en_disco(sujeto)

        # --- con escritor --------------------------------------------------
        hijo = subprocess.Popen(
            [sys.executable, a.tenedor, "--ruta", sujeto, "--modo", "ab",
             "--segundos", "30"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
        marcador = (hijo.stdout.readline() or "").strip()
        condicion = marcador.startswith("ABIERTO") and hijo.poll() is None

        replace_con = "libre"
        proc_con = "?"
        estable_con = None
        if condicion:
            try:
                os.replace(sujeto, sujeto)
            except OSError:
                replace_con = "ocupado"
            tenedores = _tenedores_posix(sujeto) or []
            proc_con = "ocupado" if tenedores else "libre"
            estable_con = _estable_en_disco(sujeto)
        try:
            hijo.kill()
            hijo.wait(timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            pass

        print(f"condicion={condicion} marcador={marcador.replace(' ', '_')} "
              f"replace_sin_escritor={replace_sin} "
              f"replace_con_escritor={replace_con} "
              f"proc_sin_escritor={proc_sin} proc_con_escritor={proc_con} "
              f"estable_sin_escritor={estable_sin} "
              f"estable_con_escritor={estable_con}", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
