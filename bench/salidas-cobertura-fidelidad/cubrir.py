"""Lanzador de `coverage` sin tocar ningun venv (CLAUDE.md §1).

`coverage` 7.16.0 vive fuera de los entornos virtuales, en el scratchpad de la
sesion. Este script lo mete en `sys.path` y delega en su CLI, para no depender
de una variable de entorno.

Uso:  python bench/salidas-cobertura-fidelidad/cubrir.py run -m unittest ...
      python bench/salidas-cobertura-fidelidad/cubrir.py json -o fichero.json
"""
import os
import sys

PYLIBS = os.environ.get("FILEX_PYLIBS") or (
    r"C:\Users\krato\AppData\Local\Temp\claude"
    r"\D--Work-research-FileX\fcb9a491-62eb-4b09-aa76-a7875fa0ab8d"
    r"\scratchpad\pylibs")
sys.path.insert(0, PYLIBS)
# `python cubrir.py` pone el directorio DEL SCRIPT en sys.path[0], no el
# directorio de trabajo, asi que `-m unittest pruebas.x` no encontraria el
# paquete. `python -m unittest` si lo hace, y de ahi la diferencia.
sys.path.insert(0, os.getcwd())

from coverage.cmdline import main  # noqa: E402

sys.exit(main(sys.argv[1:]))
