#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N25 — reproducir la medida de H2 ANTES de aplicar su parche (trampa 58).

H2 (`bench/hito2-nvenc.md` §6.5) deja escrito un parche de una línea para
`filex/nucleo.py:_un_salto` y lo tasa en **1 403,6 µs, el 0,19 %** de una
conversión NVENC de 5 s. Aquí se reproduce esa cifra y se mide **lo que el
parche cuesta de verdad tal como está escrito**, que no es lo mismo: el parche
usa `with gpu.Lock(...)`, y `Lock.__enter__` llama a `guardia()`, que lanza
`nvidia-smi`.

**NO SE TOCA EL LOCK DE LA MÁQUINA.** `GPU_LOCK` apunta a un fichero propio del
directorio desechable, así que esta tanda no se le quita a nadie. Lo único que
toca la tarjeta es la consulta de solo lectura de `nvidia-smi` que hace la
guardia, y se dice.

Uso: python bench/salidas-bitrate/medir_lock.py <dir_trabajo>
"""
import json
import os
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

N = 21
TOPE_TESTIGO = 20.0


def testigo_deriva(vueltas=200_000):
    """Bucle monohilo: mide la DERIVA dentro de la tanda."""
    t0 = time.perf_counter()
    s = 0
    for i in range(vueltas):
        s += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel():
    """Lanzamiento de proceso: mide el NIVEL de carga de la máquina.

    Con tope propio (`CLAUDE.md` §3): *un testigo que puede tumbar la medición
    no es un testigo*. Si agota, devuelve el tope y la tanda sale `SUCIA`.
    """
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=TOPE_TESTIGO)
    except subprocess.TimeoutExpired:
        return TOPE_TESTIGO * 1000, True
    return (time.perf_counter() - t0) * 1000, False


def mediana_us(fn, n=N):
    xs = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t0) * 1e6)
    return {"mediana_us": round(statistics.median(xs), 1),
            "min_us": round(min(xs), 1), "max_us": round(max(xs), 1), "n": n}


def main():
    trabajo = sys.argv[1]
    os.makedirs(trabajo, exist_ok=True)
    # ANTES de importar `filex.gpu`: `GUARD` es una constante de módulo.
    os.environ["GPU_LOCK"] = os.path.join(trabajo, "n4-gpu.lock")
    os.environ["GPU_GUARD"] = "avisar"   # que no aborte; el coste es el mismo
    from filex import gpu  # noqa: E402

    res = {"fichero_lock": gpu.fichero_lock(), "guard": gpu.GUARD,
           "vram_libre_mib_al_empezar": gpu.vram_libre_mib()}

    # calentamiento (trampa 7)
    for _ in range(3):
        l = gpu.Lock("n4-calentar")
        l.tomar(espera=5)
        l.soltar()

    d0 = testigo_deriva()
    n0, sucio0 = testigo_nivel()

    # --- 1. el primitivo, aislado: tomar + soltar, SIN guardia --------------
    def tomar_soltar():
        l = gpu.Lock("n4-medida")
        if not l.tomar(espera=5):
            raise RuntimeError("no se pudo tomar el lock propio")
        l.soltar()

    res["tomar_soltar"] = mediana_us(tomar_soltar)

    # --- 2. la guardia sola -------------------------------------------------
    res["guardia"] = mediana_us(gpu.guardia, n=9)

    # --- 3. el parche TAL COMO ESTÁ ESCRITO: `with gpu.Lock(...)` ----------
    def con_with():
        with gpu.Lock("n4-with"):
            pass

    res["with_lock"] = mediana_us(con_with, n=9)

    # --- 4. lo que paga una conversión que NO usa la tarjeta ----------------
    argv_cpu = ["ffmpeg", "-i", "a.mp4", "-c:v", "libx265", "b.mkv"]
    argv_gpu = ["ffmpeg", "-i", "a.mp4", "-c:v", "hevc_nvenc", "b.mkv"]
    res["usa_gpu_cpu"] = mediana_us(lambda: gpu.usa_gpu(argv_cpu), n=201)
    res["usa_gpu_gpu"] = mediana_us(lambda: gpu.usa_gpu(argv_gpu), n=201)
    res["usa_gpu_veredicto"] = [gpu.usa_gpu(argv_cpu), gpu.usa_gpu(argv_gpu)]

    d1 = testigo_deriva()
    n1, sucio1 = testigo_nivel()
    res["testigos"] = {"deriva_ms": [round(d0, 2), round(d1, 2)],
                       "deriva_ratio": round(d1 / d0, 3) if d0 else None,
                       "nivel_ms": [round(n0, 2), round(n1, 2)],
                       "nivel_agotado": bool(sucio0 or sucio1)}
    # Con la sesión remota activa todo sale `SUCIA`: es estructural (CLAUDE.md §3).
    res["etiqueta"] = "SUCIA"
    res["vram_libre_mib_al_acabar"] = gpu.vram_libre_mib()

    with open(os.path.join(AQUI, "medicion_lock.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
