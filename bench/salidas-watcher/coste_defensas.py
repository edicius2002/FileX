#!/usr/bin/env python3
"""El coste de las tres defensas del watcher, **tal y como quedaron en el código**.

No mide la copia de la sonda: importa `filex.watcher` y mide sus funciones. Y
mide **el trozo aislado**, no la diferencia entre dos totales que lo contienen
(trampa 36). Todo en la MISMA tanda, con los dos testigos de ruido.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)


def mediana_us(fn, repes=21):
    fn()
    ms = []
    for _ in range(repes):
        t0 = time.perf_counter()
        fn()
        ms.append((time.perf_counter() - t0) * 1e6)
    return {"mediana_us": round(statistics.median(ms), 2),
            "min_us": round(min(ms), 2), "max_us": round(max(ms), 2),
            "n": repes}


def testigo_deriva(n=300000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(n):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> float:
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return 20000.0
    return (time.perf_counter() - t0) * 1000


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--salida", required=True)
    a = p.parse_args(argv)

    from filex import watcher as w

    wav = os.path.join(RAIZ, "corpus", "audio", "trivial.wav")
    png = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
    tif = os.path.join(RAIZ, "corpus", "imagen", "patologico_16bit.tif")
    csvb = os.path.join(RAIZ, "corpus", "datos", "patologico_bom.csv")

    d0, n0 = testigo_deriva(), testigo_nivel()
    res = {"celdas": {}}
    for etiqueta, ruta in (("wav 705 678 B", wav), ("png 42 855 B", png),
                           ("tif 72 001 016 B", tif), ("csv 92 B", csvb)):
        res["celdas"][f"coherencia_declarada @ {etiqueta}"] = mediana_us(
            lambda r=ruta: w._coherencia_declarada(r))
        res["celdas"][f"estable_en_disco @ {etiqueta}"] = mediana_us(
            lambda r=ruta: w._estable_en_disco(r))
        res["celdas"][f"os.stat @ {etiqueta}"] = mediana_us(
            lambda r=ruta: os.stat(r))
    d1, n1 = testigo_deriva(), testigo_nivel()
    res["testigos"] = {"deriva_ms": [round(d0, 2), round(d1, 2)],
                       "nivel_ms": [round(n0, 2), round(n1, 2)],
                       "deriva_ratio": round(d1 / d0, 3),
                       "nivel_ratio": round(n1 / n0, 3)}
    res["testigos"]["etiqueta"] = (
        "limpia" if res["testigos"]["deriva_ratio"] < 1.5
        and res["testigos"]["nivel_ratio"] < 3.0 else "SUCIA")
    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for k, v in res["celdas"].items():
        print(f"{k:44s} {v['mediana_us']:10.2f} us")
    print("testigos:", json.dumps(res["testigos"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
