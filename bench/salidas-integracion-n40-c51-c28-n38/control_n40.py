"""Control rojo N40: ejecutar las regresiones contra nucleo.py de la base.

El fichero original se recibe como argumento, extraído con git show fuera del
contenedor. No modifica el módulo instalado ni el worktree de producto.
"""
from pathlib import Path
import sys
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pruebas import test_n40_contenedor

original = types.ModuleType("filex.nucleo_original")
original.__package__ = "filex"
sys.modules[original.__name__] = original
exec(compile(Path(sys.argv[1]).read_text(encoding="utf-8"), sys.argv[1], "exec"), original.__dict__)
test_n40_contenedor.FileX = original.FileX
resultado = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromModule(test_n40_contenedor))
sys.exit(not resultado.wasSuccessful())
