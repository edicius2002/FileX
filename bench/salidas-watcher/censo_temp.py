#!/usr/bin/env python3
"""N14 — el censo del `%TEMP%` REAL de esta máquina. **Solo lectura.**

No borra nada, a propósito: hay otro agente trabajando y sus desechables no son
míos. Esto solo contesta a *«cuánto ocupa y dónde se acumula»*, que es la mitad
del encargo que no se puede contestar con un experimento de laboratorio.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="")
    p.add_argument("--salida", required=True)
    p.add_argument("--prefijo", default="filex-")
    a = p.parse_args(argv)

    base = a.base or tempfile.gettempdir()
    ahora = time.time()
    dirs = []
    total_entradas = 0
    try:
        it = list(os.scandir(base))
    except OSError as e:
        print("no se puede listar:", e)
        return 1
    for e in it:
        total_entradas += 1
        if not e.name.startswith(a.prefijo):
            continue
        try:
            if not e.is_dir(follow_symlinks=False):
                continue
        except OSError:
            continue
        bytes_ = 0
        ficheros = 0
        nombres = []
        for raiz, _d, fs in os.walk(e.path):
            for f in fs:
                ficheros += 1
                if len(nombres) < 4:
                    nombres.append(f)
                try:
                    bytes_ += os.stat(os.path.join(raiz, f)).st_size
                except OSError:
                    pass
        try:
            edad = ahora - e.stat().st_mtime
        except OSError:
            edad = -1
        dirs.append({"nombre": e.name, "bytes": bytes_, "ficheros": ficheros,
                     "edad_dias": round(edad / 86400, 2), "muestra": nombres})

    dirs.sort(key=lambda d: -d["bytes"])
    res = {
        "base": base, "entradas_totales": total_entradas,
        "desechables": len(dirs),
        "bytes_totales": sum(d["bytes"] for d in dirs),
        "vacios": sum(1 for d in dirs if d["ficheros"] == 0),
        "con_contenido": sum(1 for d in dirs if d["ficheros"] > 0),
        "edad_max_dias": max((d["edad_dias"] for d in dirs), default=0),
        "edad_min_dias": min((d["edad_dias"] for d in dirs), default=0),
        "mayores": dirs[:15],
        "todos": dirs,
    }
    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("mayores", "todos")}, ensure_ascii=False))
    for d in res["mayores"][:8]:
        print(f"  {d['nombre']:34s} {d['bytes']:12,d} B  {d['ficheros']:4d} fich  "
              f"{d['edad_dias']:7.2f} d  {d['muestra']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
