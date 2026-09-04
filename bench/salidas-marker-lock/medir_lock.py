# -*- coding: utf-8 -*-
"""Coste de `tomar()`+`soltar()` frente al `with`, en la MISMA tanda.

La trampa 88 dice que el `with gpu.Lock(...)` cuesta ×35,4 más que
`tomar()+soltar()` porque `__enter__` llama además a `guardia()` (`nvidia-smi`).
El encargo de B3 obliga a usar `tomar()`/`soltar()` por eso. Aquí se comprueba
**en esta tanda y con esta máquina**, que es lo que exigen las trampas 59 y 79:
un ratio contra una cifra histórica no vale si no se mide también la versión
histórica aquí.

Medianas de n=9. `GPU_LOCK` apunta a un fichero de CONTROL propio, para no
tocar el lock real de la máquina mientras otro carril trabaja.

    GPU_LOCK=%TEMP%/filex-gpu-CONTROL-w1.lock python bench/salidas-marker-lock/medir_lock.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
from filex import gpu  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
N = 9


def mide(fn) -> list[float]:
    ms = []
    for _ in range(N):
        t = time.perf_counter()
        fn()
        ms.append((time.perf_counter() - t) * 1000)
    return ms


def ciclo_tomar_soltar() -> None:
    lk = gpu.Lock("medida-tomar")
    if not lk.tomar(espera=30):
        raise RuntimeError("no se pudo tomar el lock de control")
    lk.soltar()


def ciclo_with() -> None:
    with gpu.Lock("medida-with"):
        pass


def solo_guardia() -> None:
    try:
        gpu.guardia()
    except gpu.GpuOcupada:
        pass


def main() -> None:
    reg = {"n": N, "fichero_lock": gpu.fichero_lock(),
           "vram_libre_mib": gpu.vram_libre_mib()}
    for nombre, fn in (("tomar_soltar", ciclo_tomar_soltar),
                       ("with", ciclo_with),
                       ("solo_guardia", solo_guardia)):
        ms = mide(fn)
        reg[nombre] = {
            "mediana_ms": round(statistics.median(ms), 3),
            "min_ms": round(min(ms), 3), "max_ms": round(max(ms), 3),
        }
        print("%-14s mediana %8.3f ms  rango %.3f-%.3f (n=%d)"
              % (nombre, reg[nombre]["mediana_ms"], reg[nombre]["min_ms"],
                 reg[nombre]["max_ms"], N))
    a = reg["tomar_soltar"]["mediana_ms"]
    b = reg["with"]["mediana_ms"]
    reg["ratio_with_sobre_tomar"] = round(b / a, 2) if a else None
    print("ratio with/tomar_soltar = x%.2f" % reg["ratio_with_sobre_tomar"])
    with open(os.path.join(AQUI, "resultado_lock.json"), "w", encoding="utf-8") as fh:
        json.dump(reg, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
