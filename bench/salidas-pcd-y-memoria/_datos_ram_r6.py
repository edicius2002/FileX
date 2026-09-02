# -*- coding: utf-8 -*-
"""K2 / hito 3 - cuanta RAM cuesta `_datos`, con numero.

`bench/firmas-contrato.md` §10 lo declara sin medirlo: "_datos lee el fichero
entero en memoria". Aqui va la cifra, para que el arreglo (que NO se hace en
este hito) tenga un liston al que llegar.

No arregla nada. Mide, y mide el peor caso REAL: el "TXT" de ImageMagick, que es
la enumeracion de los pixeles y que E1 §6 midio en 156 520 548 bytes.

    python _datos_ram.py [--mb 32]
"""
import argparse
import json
import os
import sys
import time
import tracemalloc

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402

TMP = os.path.join(os.environ.get("TEMP", "."), "k2_hito3")


def fabrica_campo_largo(mb):
    """El caso del "TXT" de ImageMagick: una sola linea larguisima.

    Dispara `csv.Error: field larger than field limit` y `_datos` sale por la
    rama degradada SIN construir `filas`. Mide el otro regimen.
    """
    os.makedirs(TMP, exist_ok=True)
    p = os.path.join(TMP, "campolargo_%d.csv" % mb)
    with open(p, "wb") as fh:
        fh.write(b"a" * (mb * (1 << 20)))
    return p


def fabrica(mb):
    """Un CSV sintetico de ~mb megabytes. Determinista."""
    os.makedirs(TMP, exist_ok=True)
    p = os.path.join(TMP, "grande_%d.csv" % mb)
    if os.path.exists(p) and abs(os.path.getsize(p) - mb * (1 << 20)) < (1 << 20):
        return p
    fila = ",".join("%d" % i for i in range(20)) + "\n"
    n = (mb * (1 << 20)) // len(fila)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(",".join("c%d" % i for i in range(20)) + "\n")
        for _ in range(n):
            fh.write(fila)
    return p


def mide(p):
    tracemalloc.start()
    t = time.perf_counter()
    d = V._datos(p)
    ms = (time.perf_counter() - t) * 1000
    actual, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"bytes_fichero": os.path.getsize(p), "pico_bytes": pico,
            "ratio_pico_sobre_fichero": round(pico / max(os.path.getsize(p), 1), 2),
            "ms": round(ms, 1), "csv_n_filas": d.get("csv_n_filas")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mb", type=int, nargs="+", default=[1, 8, 32])
    a = ap.parse_args()
    out = []
    for mb in a.mb:
        p = fabrica(mb)
        r = mide(p)
        r["mb_nominal"] = mb
        r["caso"] = "csv_normal"
        out.append(r)
        print("%4d MB csv normal   -> pico %11d B (x%5.2f del fichero) %8.1f ms  %s filas"
              % (mb, r["pico_bytes"], r["ratio_pico_sobre_fichero"], r["ms"],
                 r["csv_n_filas"]))
        os.remove(p)
        p = fabrica_campo_largo(mb)
        r = mide(p)
        r["mb_nominal"] = mb
        r["caso"] = "campo_largo"  # la rama degradada, la del TXT de ImageMagick
        out.append(r)
        print("%4d MB campo largo  -> pico %11d B (x%5.2f del fichero) %8.1f ms  %s filas"
              % (mb, r["pico_bytes"], r["ratio_pico_sobre_fichero"], r["ms"],
                 r["csv_n_filas"]))
        os.remove(p)
    with open(os.path.join(SAL, "datos_ram.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("escrito datos_ram.json")
