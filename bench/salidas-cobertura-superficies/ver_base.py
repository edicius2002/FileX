"""Lee el JSON de cobertura base del maestro y saca las lineas sin ejecutar
de los cuatro modulos del carril de superficies.

    python bench/salidas-cobertura-superficies/ver_base.py <base-cobertura.json>
"""
import json
import os
import sys

OBJETIVO = ("cli.py", "__main__.py", "api.py", "watcher.py")


def base(ruta):
    d = json.load(open(ruta, encoding="utf-8"))
    out = {}
    for k, v in d["files"].items():
        nombre = os.path.basename(k.replace("/", os.sep))
        if nombre in OBJETIVO and (os.sep + "filex" + os.sep) in (os.sep + k.replace("/", os.sep)):
            out[nombre] = v
    return out


if __name__ == "__main__":
    for nombre, v in sorted(base(sys.argv[1]).items()):
        s = v["summary"]
        print(f"{nombre:<14} stmts={s['num_statements']:>4} "
              f"cubiertas={s['covered_lines']:>4} "
              f"sin={s['missing_lines']:>4} {s['percent_covered']:.1f}%")
        print("   faltan:", v["missing_lines"])
