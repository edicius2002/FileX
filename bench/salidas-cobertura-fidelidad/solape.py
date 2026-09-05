"""Que funciones de `filex/verificador.py` toca la rama SIN FUSIONAR
`cpu/fidelidad-impl`, y cuales de ellas son del carril `cob/fidelidad`.

Se compara por AST y por nombre, no por numero de linea: los dos arboles tienen
inserciones en sitios distintos y las coordenadas no son las mismas (es el
mismo motivo por el que `delta.py` compara por nombre).
"""
import ast
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIAS = {"_num", "svg_textos", "png_tinta_cajas", "fidelidad_imagen",
        "fidelidad_video", "fidelidad_pdf", "fidelidad_vectorial"}


def _fuente(ref):
    p = subprocess.run(["git", "show", "%s:filex/verificador.py" % ref],
                       cwd=RAIZ, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")[:200]
    return p.stdout.decode("utf-8")


def _cuerpos(fuente):
    a = ast.parse(fuente)
    fuera = {}
    for n in a.body:
        if isinstance(n, ast.FunctionDef):
            fuera[n.name] = ast.dump(n, annotate_fields=True)
    return fuera


base = _cuerpos(_fuente("main"))
rama = _cuerpos(_fuente(sys.argv[1] if len(sys.argv) > 1 else "cpu/fidelidad-impl"))
mio = _cuerpos(_fuente("HEAD"))

def _difs(a, b):
    return sorted({n for n in set(a) | set(b) if a.get(n) != b.get(n)})

d_rama = _difs(base, rama)
d_mio = _difs(base, mio)
res = {"funciones_que_toca_la_rama": d_rama,
       "funciones_que_toco_yo": d_mio,
       "interseccion": sorted(set(d_rama) & set(d_mio)),
       "de_las_mias_que_toca_la_rama": sorted(set(d_rama) & MIAS),
       "de_las_mias_que_toco_yo": sorted(set(d_mio) & MIAS)}
print(json.dumps(res, indent=1, ensure_ascii=False))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "solape.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, ensure_ascii=False)
