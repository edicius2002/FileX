"""Quinta sonda: que valor de `--raiz` hace que `FileX` lance `ValueError`
(rama `return 2` de `cli.main`, `api.main` y `watcher.main`)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from filex.confinamiento import Confinamiento

CASOS = [["C:/"], [""], ["C:" + os.sep], ["   "], ["Z:/no-existe"], ["."],
         [os.sep]]
for r in CASOS:
    try:
        c = Confinamiento(r)
        print(repr(r), "OK lectura=", c.lectura)
    except ValueError as e:
        print(repr(r), "ValueError:", e)
    except Exception as e:
        print(repr(r), type(e).__name__, e)
