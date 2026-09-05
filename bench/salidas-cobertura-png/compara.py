"""Titular del carril: cuantas de las lineas que la suite base NO ejecutaba
ejecuta ahora `pruebas/test_cob_png.py`, y en que funciones.

No se puede lanzar la suite completa (hay mas workers en la maquina; trampas
101 y 123), asi que la cifra honesta es la INTERSECCION: lineas que estaban en
`missing_lines` de la base y que este modulo, por si solo, ejecuta.

La base vive en `base-verificador.json` (congelada aqui a proposito: la medida
original estaba en un scratchpad de sesion y se pierde; trampa 95).

    python bench/salidas-cobertura-png/compara.py
"""
import ast
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
BASE = os.path.join(AQUI, "base-verificador.json")
FUENTE = os.path.join(RAIZ, "filex", "verificador.py")


def de_cobertura(camino):
    d = json.load(open(camino, encoding="utf-8"))
    k = [x for x in d["files"] if "verificador" in x][0]
    v = d["files"][k]
    return set(v["missing_lines"]), set(v["executed_lines"]), v["summary"]


def de_base():
    d = json.load(open(BASE, encoding="utf-8"))
    return (set(d["missing_lines"]), set(d["executed_lines"]), d["summary"],
            d["totals_filex"])


def funciones():
    """(nombre cualificado) -> conjunto de lineas, incluidas las anidadas."""
    arbol = ast.parse(open(FUENTE, encoding="utf-8").read())
    fuera = {}

    def anda(nodo, prefijo):
        for hijo in ast.iter_child_nodes(nodo):
            if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nom = prefijo + hijo.name
                fuera.setdefault(nom, set()).update(
                    range(hijo.lineno, (hijo.end_lineno or hijo.lineno) + 1))
                anda(hijo, nom + ".")
            elif isinstance(hijo, ast.ClassDef):
                anda(hijo, prefijo + hijo.name + ".")
            else:
                anda(hijo, prefijo)

    anda(arbol, "")
    # las lineas de una funcion anidada no cuentan como de la de fuera
    for nom, ls in list(fuera.items()):
        for otro, otras in fuera.items():
            if otro != nom and otro.startswith(nom + "."):
                ls -= otras
    return fuera


faltan_base, _, res_base, tot = de_base()
faltan_aqui, hechas_aqui, res_aqui = de_cobertura(os.path.join(AQUI, "cobertura.json"))
ganadas = faltan_base & hechas_aqui

fn = funciones()
por_fn = []
for nom, ls in sorted(fn.items()):
    antes = len(ls & faltan_base)
    gana = len(ls & ganadas)
    if antes:
        por_fn.append({"funcion": nom, "faltaban": antes, "ahora_ejecutadas": gana,
                       "siguen_sin_ejecutar": antes - gana})

por_fn.sort(key=lambda f: -f["ahora_ejecutadas"])
salida = {
    "base": {"cubiertas": res_base["covered_lines"],
             "sin_ejecutar": res_base["missing_lines"],
             "sentencias": res_base["num_statements"],
             "pct": round(res_base["percent_covered"], 2)},
    "solo_este_modulo": {"cubiertas": res_aqui["covered_lines"],
                         "sentencias": res_aqui["num_statements"],
                         "pct": round(res_aqui["percent_covered"], 2)},
    "lineas_ganadas": len(ganadas),
    "por_funcion": por_fn,
}
json.dump(salida, open(os.path.join(AQUI, "ganancia.json"), "w"), indent=1)

print("base: %d/%d cubiertas (%.2f %%), %d sin ejecutar"
      % (res_base["covered_lines"], res_base["num_statements"],
         res_base["percent_covered"], res_base["missing_lines"]))
print("solo test_cob_png: %d cubiertas (%.2f %%)"
      % (res_aqui["covered_lines"], res_aqui["percent_covered"]))
print("LINEAS GANADAS (estaban sin ejecutar y ahora se ejecutan): %d" % len(ganadas))
print()
print("%-42s %8s %8s %8s" % ("funcion", "faltaban", "ganadas", "quedan"))
for f in por_fn[:40]:
    if f["ahora_ejecutadas"] or f["funcion"] in sys.argv[1:]:
        print("%-42s %8d %8d %8d" % (f["funcion"], f["faltaban"],
                                     f["ahora_ejecutadas"],
                                     f["siguen_sin_ejecutar"]))
print()
print("proyeccion del total de filex/ si se suma este modulo a la base:")
print("  %d/%d = %.2f %%  ->  %d/%d = %.2f %%"
      % (tot["covered_lines"], tot["num_statements"],
         100.0 * tot["covered_lines"] / tot["num_statements"],
         tot["covered_lines"] + len(ganadas), tot["num_statements"],
         100.0 * (tot["covered_lines"] + len(ganadas)) / tot["num_statements"]))
