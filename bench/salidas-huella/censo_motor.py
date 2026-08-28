"""Censo del componente `motor`: que hay de nivel superior en los ficheros de
motor que las CLASES leen y la huella de clase NO hashea. Mismo agujero que
`contrato`, o no; se sondea, no se deduce."""
import ast
import collections
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

for f in ("filex/motores.py", "filex/motor_contenedor.py"):
    src = open(os.path.join(RAIZ, f), encoding="utf-8").read()
    a = ast.parse(src)
    print("==", f, dict(collections.Counter(type(n).__name__ for n in a.body)))
    fuera = []
    for n in a.body:
        if isinstance(n, ast.Assign):
            for d in n.targets:
                if isinstance(d, ast.Name):
                    fuera.append(d.id)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            fuera.append(n.target.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fuera.append(n.name)
    print("   nivel superior no-clase:", fuera)
    clases = [n for n in a.body if isinstance(n, ast.ClassDef)]
    refs = set()
    for c in clases:
        refs |= {m.id for m in ast.walk(c) if isinstance(m, ast.Name)}
        refs |= {m.func.id for m in ast.walk(c)
                 if isinstance(m, ast.Call) and isinstance(m.func, ast.Name)}
    print("   REFERENCIADOS por alguna clase y NO hasheados:",
          sorted(set(fuera) & refs))
