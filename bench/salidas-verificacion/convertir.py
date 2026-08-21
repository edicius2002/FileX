#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tiempo REAL de conversion de las 39 ordenes del patron oro.

referencia.json dice explicitamente: "NO se han tomado mediciones de tiempo".
Sin ese numero no hay ratio verificar/convertir, que es la cifra que sostiene
o hunde el diferenciador nº 1 de FileX. Aqui se mide.

Las salidas se escriben en el directorio temporal y se borran: el repositorio
ya tiene un problema de peso.
"""
import json
import os
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
REF = os.path.join(RAIZ, "bench", "salidas-referencia")
SAL = os.environ.get("FILEX_TMP") or os.path.join(tempfile.gettempdir(), "filex_conv")

# id -> (entrada_absoluta, orden_como_lista, nombre_salida)
def _e(*p):
    return os.path.join(RAIZ, *p)


ORDENES = {}


def cargar():
    with open(os.path.join(REF, "referencia.json"), encoding="utf-8") as fh:
        return json.load(fh)


def construir(ref):
    """Traduce cada 'orden' del patron oro a una lista ejecutable."""
    trabajos = []
    for o in ref["ordenes"]:
        oid, orden = o["id"], o["orden"]
        ent = _e(*o["entrada"].split("/")) if o["entrada"].startswith("corpus") else \
            os.path.join(REF, *o["entrada"].split("/")[1:])
        destino = os.path.join(SAL, oid.replace(".", "_") + "_" +
                               os.path.basename(o["salida"]))
        if orden.startswith("magick"):
            partes = shlex.split(orden, posix=False)
            args = ["magick", "-limit", "thread", "4"]
            resto = partes[4:]           # tras 'magick -limit thread 4'
            args += [ent] + [x.strip('"') for x in resto[1:-1]] + [destino]
            cat = "imagen" if not destino.endswith(".pdf") else "pdf"
        elif orden.startswith("gswin64c"):
            partes = shlex.split(orden, posix=False)
            args = [p for p in partes[:-1] if not p.startswith("-sOutputFile")]
            args += ["-sOutputFile=" + destino, ent]
            cat = "pdf"
        elif orden.startswith("ffmpeg"):
            partes = shlex.split(orden, posix=False)
            args = ["ffmpeg", "-y", "-threads", "4", "-i", ent]
            resto = partes[5:-1]
            args += [x.strip('"') for x in resto] + [destino]
            cat = "video" if "/video/" in o["entrada"] or destino.endswith(
                (".mp4", ".mkv", ".webm", ".gif")) else "audio"
            if o["entrada"].startswith("corpus/audio"):
                cat = "audio"
        else:                              # las tres de datos: se reimplementan
            args = [sys.executable, os.path.join(AQUI, "conv_datos.py"), oid, ent, destino]
            cat = "datos"
        trabajos.append({"id": oid, "cat": cat, "orden": args, "salida": destino,
                         "entrada": ent})
    return trabajos


def correr(args, timeout=900):
    return subprocess.run(args, capture_output=True, timeout=timeout).returncode


def medir(t, n):
    ts = []
    for _ in range(n):
        ini = time.perf_counter()
        rc = correr(t["orden"])
        ts.append((time.perf_counter() - ini) * 1000)
    ts.sort()
    return {"id": t["id"], "cat": t["cat"], "n": n, "rc": rc,
            "mediana_ms": round(statistics.median(ts), 1),
            "min_ms": round(ts[0], 1), "max_ms": round(ts[-1], 1),
            "bytes_salida": os.path.getsize(t["salida"]) if os.path.exists(t["salida"]) else 0}


def main():
    os.makedirs(SAL, exist_ok=True)
    trabajos = construir(cargar())
    # 1) una pasada de tanteo para saber cuanto cuesta cada una
    tanteo = {}
    for t in trabajos:
        ini = time.perf_counter()
        rc = correr(t["orden"])
        tanteo[t["id"]] = ((time.perf_counter() - ini) * 1000, rc)
        print("tanteo %-22s %8.0f ms rc=%s" % (t["id"], *tanteo[t["id"]]), flush=True)
    # 2) repeticiones segun coste: n=9 barato, n=5 medio, n=3 caro
    res = []
    for t in trabajos:
        ms, rc = tanteo[t["id"]]
        n = 9 if ms < 1500 else (5 if ms < 8000 else 3)
        r = medir(t, n)
        r["rc_tanteo"] = rc
        res.append(r)
        print("%-22s %-8s mediana %9.1f ms (n=%d) rango %.0f-%.0f rc=%s"
              % (r["id"], r["cat"], r["mediana_ms"], r["n"], r["min_ms"],
                 r["max_ms"], r["rc"]), flush=True)
    with open(os.path.join(AQUI, "conversion.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    shutil.rmtree(SAL, ignore_errors=True)
    print("borrado", SAL)


if __name__ == "__main__":
    main()
