# -*- coding: utf-8 -*-
"""N18 — el coste del grafo, medido AISLADO y contra lo que A7 gasta hoy.

Trampa 36: se mide el trozo, no la diferencia entre dos totales que lo
contienen. Trampa 59: la cifra de N16 (183,1 ms) se midió en OTRA tanda y con
numpy; aquí se vuelve a medir **la de N16 también**, en esta tanda, o el ratio
compara dos máquinas y no dos códigos.

Cuatro filas, con el mismo par de ficheros y la misma tanda:

  1. `astats` de la ENTRADA        — la mitad de lo que A7 hace hoy
  2. `astats` de la SALIDA         — la otra mitad
  3. **el grafo**                  — UNA invocación que da los tres RMS por
                                     canal, y con ellos la energía Y la
                                     correlación
  4. *(control)* la vía de N16     — decodificar los dos PCM + FFT + Pearson,
                                     con numpy, que es lo que `filex` no puede
                                     hacer
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, AQUI)
from a7_corr_ancho import SR, DUR, alinear_fft, corr, ff, pcm, recortar  # noqa: E402
from a7_grafo import GRAFO  # noqa: E402

CORPUS = os.path.join(RAIZ, "corpus", "audio")
N = 15
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def testigo_deriva(vueltas: int = 400_000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(vueltas):
        x += i
    return (time.perf_counter() - t0) * 1000


def testigo_proceso(tope: float = 20.0) -> float:
    """Con TOPE: un testigo que puede tumbar la medición no es un testigo."""
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=tope)
    except Exception:
        return tope * 1000
    return (time.perf_counter() - t0) * 1000


def astats(ruta: str):
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", ruta, "-map", "0:a:0",
         "-vn", "-sn", "-af", "astats=measure_overall=none:"
         "measure_perchannel=Peak_level+RMS_level", "-f", "null", "-"],
        capture_output=True, timeout=180, stdin=subprocess.DEVNULL)


def astats_completo(ruta: str):
    """**El control que faltaba.** Es la orden EXACTA de
    `bench/salidas-ventana/a7_coste_senal.py`, con la que N16 midio los 364,0 ms
    que atribuyo a A7: `astats=metadata=1:reset=0`, es decir TODAS las medidas,
    sin `-map 0:a:0` y sin `-vn`. **A7 no ejecuta eso** (trampa 55: una cifra
    citada entre informes puede venir de otra medida, y el texto no lo dice)."""
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", ruta,
         "-af", "astats=metadata=1:reset=0", "-f", "null", "-"],
        capture_output=True, timeout=180, stdin=subprocess.DEVNULL)


def grafo(entrada, salida):
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", entrada, "-i", salida,
         "-filter_complex", GRAFO.format(sr=SR, lay="stereo"),
         "-map", "[m]", "-f", "null", "-"],
        capture_output=True, timeout=180, stdin=subprocess.DEVNULL)


def mediana(f, n=N):
    xs = []
    for _ in range(n):
        t0 = time.perf_counter()
        f()
        xs.append((time.perf_counter() - t0) * 1000)
    xs.sort()
    return {"mediana": round(statistics.median(xs), 2),
            "p90": round(xs[int(0.9 * (len(xs) - 1))], 2),
            "min": round(xs[0], 2), "max": round(xs[-1], 2), "n": n}


def main() -> int:
    d = tempfile.mkdtemp(prefix="filex-a7-coste-")
    antes = sorted(os.listdir(d))
    jfk = os.path.join(CORPUS, "habla_jfk.flac")
    src = os.path.join(d, "src.wav")
    ff(["-i", jfk, "-t", str(DUR), "-ar", str(SR), "-ac", "2",
        "-c:a", "pcm_s16le", src])
    dst = os.path.join(d, "sal.opus")
    ff(["-i", src, "-c:a", "libopus", "-b:a", "96k", "-ac", "2", dst])

    # Calentar: trampa 7 (Defender infla el primer arranque).
    astats(src), astats(dst), grafo(src, dst), pcm(src), pcm(dst)

    dv0, tp0 = testigo_deriva(), testigo_proceso()
    filas = {}
    filas["astats_entrada"] = mediana(lambda: astats(src))
    filas["astats_salida"] = mediana(lambda: astats(dst))
    filas["grafo_una_invocacion"] = mediana(lambda: grafo(src, dst))

    def via_n16():
        e, s = pcm(src), pcm(dst)
        dsf = alinear_fft(s, e)
        s2, e2 = recortar(s, e, dsf)
        return [corr(s2[k], e2[k]) for k in (0, 1)]

    filas["via_N16_numpy"] = mediana(via_n16)
    filas["CONTROL_astats_completo_entrada"] = mediana(lambda: astats_completo(src))
    filas["CONTROL_astats_completo_salida"] = mediana(lambda: astats_completo(dst))
    dv1, tp1 = testigo_deriva(), testigo_proceso()

    a7_hoy = filas["astats_entrada"]["mediana"] + filas["astats_salida"]["mediana"]
    res = {
        "cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n": N, "dur_s": DUR, "sr": SR,
        "testigos": {"deriva_ms": [round(dv0, 1), round(dv1, 1)],
                     "deriva_ratio": round(dv1 / dv0, 2) if dv0 else None,
                     "proceso_ms": [round(tp0, 1), round(tp1, 1)]},
        "filas": filas,
        "A7_hoy_dos_astats_ms": round(a7_hoy, 2),
        "grafo_frente_a_A7_hoy": round(
            filas["grafo_una_invocacion"]["mediana"] / a7_hoy, 3),
        "via_N16_frente_a_A7_hoy": round(
            filas["via_N16_numpy"]["mediana"] / a7_hoy, 3),
        "control_astats_completo_ms": round(
            filas["CONTROL_astats_completo_entrada"]["mediana"]
            + filas["CONTROL_astats_completo_salida"]["mediana"], 2),
        "censo_antes": antes, "censo_despues": sorted(os.listdir(d)),
    }
    with open(os.path.join(AQUI, "a7_coste_grafo.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for k, v in filas.items():
        print("  %-24s %8.2f ms  (p90 %8.2f, n=%d)"
              % (k, v["mediana"], v["p90"], v["n"]))
    print("\n  A7 HOY (dos astats)      %8.2f ms" % a7_hoy)
    print("  el GRAFO                 %8.2f ms   = x%.3f de A7 hoy"
          % (filas["grafo_una_invocacion"]["mediana"], res["grafo_frente_a_A7_hoy"]))
    print("  la via de N16 (numpy)    %8.2f ms   = x%.3f de A7 hoy"
          % (filas["via_N16_numpy"]["mediana"], res["via_N16_frente_a_A7_hoy"]))
    print("  CONTROL: dos `astats=metadata=1:reset=0` (lo que midio N16) %8.2f ms"
          % res["control_astats_completo_ms"])
    print("  testigos: deriva %.1f -> %.1f (ratio %s), proceso %.1f -> %.1f ms"
          % (dv0, dv1, res["testigos"]["deriva_ratio"], tp0, tp1))
    shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
