# -*- coding: utf-8 -*-
"""P2 - LOS DOS TESTIGOS DE RUIDO (CLAUDE.md sec.3, verificador-ghostscript.md sec.4).

Uno mide DERIVA (bucle monohilo de SHA-256), el otro mide NIVEL (lanzamiento de
proceso). El monohilo solo es ciego a la contencion multinucleo: con 12 nucleos cabe
en uno libre y etiqueta `limpia` una tanda que va x6,8. Hay dos agentes mas corriendo.

Uso: python _p2_testigo.py <etiqueta>   -> anade una linea a testigo.jsonl
"""
import os, sys, json, time, hashlib, subprocess, statistics

SAL = os.path.dirname(os.path.abspath(__file__))
FF = "ffprobe"


def deriva(n=400000):
    ms = []
    for _ in range(7):
        t0 = time.perf_counter()
        h = b"filex"
        for _ in range(n):
            h = hashlib.sha256(h).digest()
        ms.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(ms), 2)


def nivel(n=9):
    ms = []
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            subprocess.run([FF, "-v", "quiet", "-version"], stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=60)
        except Exception:
            return -1.0
        ms.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(ms), 2)


if __name__ == "__main__":
    et = sys.argv[1] if len(sys.argv) > 1 else "sin-etiqueta"
    d, nv = deriva(), nivel()
    reg = {"etiqueta": et, "cuando": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "deriva_sha256_ms": d, "nivel_lanzamiento_ms": nv,
           "calibracion_reposo_ffprobe_ms": "26,5-26,8 (verificador-ghostscript.md sec.4)"}
    with open(os.path.join(SAL, "testigo.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    print(json.dumps(reg, ensure_ascii=False))
