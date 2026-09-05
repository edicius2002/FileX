"""Cuanto se mueve la cobertura de las cuatro superficies, por MODULO y por
FUNCION.

    python bench/salidas-cobertura-superficies/delta.py \
        <base-cobertura.json> bench/salidas-cobertura-superficies/cobertura.json

La base la midio el maestro sobre la suite entera (517 pruebas). Este carril
NO puede reejecutar la suite entera —hay cinco agentes mas en la maquina y
seis suites a la vez fabrican la carga que pone roja `test_cancelacion_procesos`
sin que nadie toque el codigo (trampas 101 y 123)—, asi que el delta se calcula
como interseccion:

    ganadas = (lineas SIN EJECUTAR en la base) ∩ (lineas EJECUTADAS por este
              modulo de pruebas)

Es exacto, no una estimacion: la cobertura es monotona bajo la union de
ejecuciones, luego una linea que la base no tenia y este modulo si ejecuta
esta ejecutada en la union. Lo que este calculo NO puede decir es cuantas
lineas quedan sin ejecutar en la union para el resto de `filex/`, y por eso el
informe publica el delta de estos cuatro ficheros y de nadie mas.
"""
import ast
import json
import os
import sys

OBJETIVO = ("cli.py", "__main__.py", "api.py", "watcher.py")


def por_nombre(ruta):
    d = json.load(open(ruta, encoding="utf-8"))
    out = {}
    for k, v in d["files"].items():
        nombre = os.path.basename(k.replace("/", os.sep))
        if nombre in OBJETIVO and "filex" in k.replace("\\", "/").split("/"):
            out[nombre] = v
    return out


def funciones(fuente):
    """(primera_linea, ultima_linea, nombre) de cada def del fichero."""
    arbol = ast.parse(open(fuente, encoding="utf-8").read())
    out = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((nodo.lineno, nodo.end_lineno, nodo.name))
    return sorted(out)


def funcion_de(linea, tabla):
    mejor = "<modulo>"
    ancho = 10 ** 9
    for ini, fin, nombre in tabla:
        if ini <= linea <= fin and (fin - ini) < ancho:
            mejor, ancho = nombre, fin - ini
    return mejor


def main(base_json, nuevo_json, raiz):
    base = por_nombre(base_json)
    nuevo = por_nombre(nuevo_json)
    total_ganadas = 0
    resumen = {}
    for nombre in sorted(OBJETIVO):
        b, n = base.get(nombre), nuevo.get(nombre)
        if not b or not n:
            print(f"{nombre}: falta en uno de los dos informes")
            continue
        sin_base = set(b["missing_lines"])
        ejecutadas = set(n["executed_lines"])
        ganadas = sorted(sin_base & ejecutadas)
        quedan = sorted(sin_base - ejecutadas)
        stmts = b["summary"]["num_statements"]
        antes = b["summary"]["percent_covered"]
        despues = 100.0 * (stmts - len(quedan)) / stmts
        print(f"\n{nombre}  {stmts} sentencias   "
              f"{antes:.1f} % -> {despues:.1f} %   "
              f"ganadas {len(ganadas)}   quedan {len(quedan)}")
        tabla = funciones(os.path.join(raiz, "filex", nombre))
        por_fn = {}
        for l in ganadas:
            por_fn.setdefault(funcion_de(l, tabla), []).append(l)
        for fn, ls in sorted(por_fn.items(), key=lambda kv: -len(kv[1])):
            print(f"    +{len(ls):>3}  {fn}")
        if quedan:
            faltan = {}
            for l in quedan:
                faltan.setdefault(funcion_de(l, tabla), []).append(l)
            print("    sin ejecutar todavia:")
            for fn, ls in sorted(faltan.items(), key=lambda kv: -len(kv[1])):
                print(f"    -{len(ls):>3}  {fn}  {ls}")
        total_ganadas += len(ganadas)
        resumen[nombre] = {
            "sentencias": stmts, "antes_pct": round(antes, 1),
            "despues_pct": round(despues, 1), "ganadas": ganadas,
            "quedan": quedan,
            "ganadas_por_funcion": {k: v for k, v in sorted(por_fn.items())},
        }
    print(f"\nTOTAL ganadas: {total_ganadas}")
    resumen["_total_ganadas"] = total_ganadas
    return resumen


if __name__ == "__main__":
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    r = main(sys.argv[1], sys.argv[2], raiz)
    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
