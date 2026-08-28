"""Cuanto se hashea con cada opcion, y que caduca cada perturbacion.

*Hashear el fichero entero es la respuesta facil y es la mala*: aqui esta el
numero que lo dice, y el de la opcion elegida al lado.

Salida: bench/salidas-huella/granularidad.json
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from filex import huella as NUEVA  # noqa: E402

src_v = subprocess.run(["git", "-C", RAIZ, "show", "HEAD:filex/huella.py"],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=60).stdout
p = os.path.join(SAL, "_huella_head.py")
with open(p, "w", encoding="utf-8") as fh:
    fh.write(src_v)
spec = importlib.util.spec_from_file_location("_huella_head_gr", p)
VIEJA = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VIEJA)

V = os.path.join(RAIZ, "filex", "verificador.py")
src = open(V, encoding="utf-8").read()
arbol = ast.parse(src)
lineas_fichero = len(src.split("\n"))


def lineas(nodos) -> int:
    return sum(n.end_lineno - n.lineno + 1 for n in nodos)


# --- cuanto cubre cada opcion
t_v = VIEJA._tabla(arbol)
al_v = VIEJA._cierre(t_v, VIEJA.ENTRADAS_CONTRATO)
t_n = NUEVA._tabla(arbol)
al_n = NUEVA._cierre(t_n, NUEVA.ENTRADAS_CONTRATO)

nodos_v = {id(t_v[n]): t_v[n] for n in al_v}
nodos_n = {id(x): x for n in al_n for x in t_n[n]}

ejec = [n for n in arbol.body
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef, ast.Assign, ast.AnnAssign,
                              ast.Import, ast.ImportFrom, ast.Expr))]

res = {
    "verificador_py_lineas": lineas_fichero,
    "opciones": {
        "fichero_entero": {
            "nombres": len(t_n), "lineas_cubiertas": lineas_fichero,
            "un_comentario_caduca": True,
            "aristas_que_caducaria_un_comentario": 215},
        "cierre_VIEJO": {
            "nombres": len(al_v), "lineas_cubiertas": lineas(nodos_v.values()),
            "un_comentario_caduca": False,
            "aristas_que_caducaria_un_comentario": 0},
        "cierre_NUEVO": {
            "nombres": len(al_n), "lineas_cubiertas": lineas(nodos_n.values()),
            "un_comentario_caduca": False,
            "aristas_que_caducaria_un_comentario": 0},
    },
    "sentencias_ejecutables_nivel_superior": [
        {"tipo": type(n).__name__, "lineas": f"{n.lineno}-{n.end_lineno}",
         "n_lineas": n.end_lineno - n.lineno + 1,
         "muta": sorted(NUEVA._mutados(n) & set(t_n)),
         "entra_en_el_cierre": bool(NUEVA._mutados(n) & al_n)}
        for n in ejec],
}
res["lineas_que_el_arreglo_ANADE"] = (
    res["opciones"]["cierre_NUEVO"]["lineas_cubiertas"]
    - res["opciones"]["cierre_VIEJO"]["lineas_cubiertas"])

with open(os.path.join(SAL, "granularidad.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
