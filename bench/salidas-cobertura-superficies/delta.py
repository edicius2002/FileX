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
    total_ramas = 0
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
        # Las RAMAS son el otro eje, y el porcentaje que publica coverage con
        # `--branch` es el COMBINADO de los dos: compararlo contra un
        # porcentaje de sentencias seria mezclar dos metricas (trampa 55).
        ram_base_fuera = {tuple(x) for x in b["missing_branches"]}
        ram_mias = {tuple(x) for x in n["executed_branches"]}
        ram_ganadas = sorted(ram_base_fuera & ram_mias)
        ram_quedan = sorted(ram_base_fuera - ram_mias)
        stmts = b["summary"]["num_statements"]
        nram = b["summary"]["num_branches"]
        antes = b["summary"]["percent_covered"]
        cub = (stmts - len(quedan)) + (b["summary"]["covered_branches"]
                                       + len(ram_ganadas))
        despues = 100.0 * cub / (stmts + nram)
        print(f"\n{nombre}  {stmts} sentencias + {nram} ramas   "
              f"{antes:.1f} % -> {despues:.1f} % (combinado)")
        print(f"    sentencias: ganadas {len(ganadas)}, quedan {len(quedan)}")
        print(f"    ramas:      ganadas {len(ram_ganadas)}, "
              f"quedan {len(ram_quedan)}  {ram_quedan if ram_quedan else ''}")
        total_ramas += len(ram_ganadas)
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
            "sentencias": stmts, "ramas": nram,
            "antes_pct_combinado": round(antes, 1),
            "despues_pct_combinado": round(despues, 1),
            "ganadas": ganadas, "quedan": quedan,
            "ramas_ganadas": [list(x) for x in ram_ganadas],
            "ramas_que_quedan": [list(x) for x in ram_quedan],
            "ganadas_por_funcion": {k: v for k, v in sorted(por_fn.items())},
        }
    print(f"\nTOTAL sentencias ganadas: {total_ganadas}")
    print(f"TOTAL ramas ganadas:      {total_ramas}")
    resumen["_total_ganadas"] = total_ganadas
    resumen["_total_ramas_ganadas"] = total_ramas
    return resumen


if __name__ == "__main__":
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    r = main(sys.argv[1], sys.argv[2], raiz)
    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
