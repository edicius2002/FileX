"""Lee la cobertura base del maestro y resume las lineas sin ejecutar de las
funciones del carril de fidelidad. Solo lectura."""
import json
import sys

RUTA = sys.argv[1]
d = json.load(open(RUTA, encoding="utf-8"))
f = d["files"]
k = [x for x in f if "verificador" in x][0]
v = f[k]
print(k, v["summary"])
falt = set(v["missing_lines"])
print("total sin ejecutar:", len(falt))
# rangos de mis funciones (por numero de linea de def, ver briefing)
import ast
arbol = ast.parse(open("filex/verificador.py", encoding="utf-8").read())
mias = ("_num", "svg_textos", "png_tinta_cajas", "fidelidad_imagen",
        "fidelidad_video", "fidelidad_pdf", "fidelidad_vectorial")
tot = 0
for nodo in arbol.body:
    if isinstance(nodo, ast.FunctionDef) and nodo.name in mias:
        r = range(nodo.lineno, nodo.end_lineno + 1)
        n = sorted(falt & set(r))
        tot += len(n)
        print("%-22s %4d-%4d  %3d sin ejecutar" % (nodo.name, nodo.lineno,
                                                   nodo.end_lineno, len(n)))
print("SUMA carril:", tot)
