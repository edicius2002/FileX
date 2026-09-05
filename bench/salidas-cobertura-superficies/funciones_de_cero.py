"""Que FUNCIONES pasan de CERO lineas ejecutadas a ejecutadas enteras.

El titular de un informe de cobertura no puede ser un porcentaje (trampa 48:
un recuento correcto no prueba un contenido correcto). Esto lista las
funciones y cuantas lineas mueve cada una.

    python bench/salidas-cobertura-superficies/funciones_de_cero.py \
        <base-cobertura.json> bench/salidas-cobertura-superficies/cobertura.json
"""
import ast
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from delta import OBJETIVO, funcion_de, funciones, por_nombre  # noqa: E402


def main(base_json, nuevo_json, raiz):
    base, nuevo = por_nombre(base_json), por_nombre(nuevo_json)
    for nombre in sorted(OBJETIVO):
        b, n = base[nombre], nuevo[nombre]
        tabla = funciones(os.path.join(raiz, "filex", nombre))
        sin_base = set(b["missing_lines"])
        con_base = set(b["executed_lines"])
        ganadas = sin_base & set(n["executed_lines"])
        # Agrupar TODAS las sentencias del fichero por funcion.
        todas = sin_base | con_base
        por_fn = {}
        for l in todas:
            por_fn.setdefault(funcion_de(l, tabla), {"total": 0, "antes": 0,
                                                     "gana": 0})
            por_fn[funcion_de(l, tabla)]["total"] += 1
            if l in con_base:
                por_fn[funcion_de(l, tabla)]["antes"] += 1
            if l in ganadas:
                por_fn[funcion_de(l, tabla)]["gana"] += 1
        de_cero = [(fn, v) for fn, v in por_fn.items()
                   if v["antes"] == 0 and v["gana"] > 0]
        parcial = [(fn, v) for fn, v in por_fn.items()
                   if v["antes"] > 0 and v["gana"] > 0]
        print(f"\n=== {nombre}")
        print(f"  DE CERO A ENTERA ({len(de_cero)} funciones, "
              f"{sum(v['gana'] for _, v in de_cero)} lineas):")
        for fn, v in sorted(de_cero, key=lambda kv: -kv[1]["gana"]):
            print(f"     {fn:<26} {v['gana']:>3} de {v['total']}")
        print(f"  YA SE TOCABAN, se completan ({len(parcial)} funciones, "
              f"{sum(v['gana'] for _, v in parcial)} lineas):")
        for fn, v in sorted(parcial, key=lambda kv: -kv[1]["gana"]):
            print(f"     {fn:<26} {v['gana']:>3} de {v['total']} "
                  f"(ya tenia {v['antes']})")


if __name__ == "__main__":
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main(sys.argv[1], sys.argv[2], raiz)
