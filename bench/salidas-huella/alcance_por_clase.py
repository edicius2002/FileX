"""Que entraria en el componente `motor` si se usara el cierre de nombres en
vez de solo la ClassDef. Sirve para decidir la granularidad CON NUMERO:
si el cierre de cada clase se traga el fichero entero, la granularidad por
motor se pierde y el arreglo no compensa."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import huella  # noqa: E402

for f, clases in (("filex/motores.py",
                   ["ImageMagick", "Ghostscript", "FFmpeg", "Motor"]),
                  ("filex/motor_contenedor.py",
                   ["_EnContenedor", "PandocEnContenedor",
                    "LibreOfficeEnContenedor", "CalibreEnContenedor"])):
    src = open(os.path.join(RAIZ, f), encoding="utf-8").read()
    total = len(huella.nombres_alcanzados(src, entradas=()))
    import ast
    arbol = ast.parse(src)
    n_sup = len(huella._tabla(arbol))
    print("==", f, "-- nombres de nivel superior:", n_sup)
    for c in clases:
        al = huella.nombres_alcanzados(src, entradas=(c,))
        print(f"   {c:26s} cierre={len(al):3d}  {sorted(al)}")
