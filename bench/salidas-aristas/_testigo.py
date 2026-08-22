# -*- coding: utf-8 -*-
"""Testigo de CPU determinista. V1 mide en CPU en paralelo: no se intenta evitar el
ruido, se ETIQUETA (bench/verificador-fidelidad.md hizo lo mismo).

Carga fija: 400.000 iteraciones de SHA-256 encadenado sobre 64 B. Sin E/S, sin GPU,
un solo hilo. Mediana de 7. Uso: python _testigo.py <etiqueta>
Escribe una linea en testigo.jsonl.
"""
import hashlib, time, json, sys, os, statistics

SAL = os.path.dirname(os.path.abspath(__file__))
N = 400000


def una():
    h = b"filex-e1-testigo-0123456789abcdef0123456789abcdef0123456789abcdef"
    t0 = time.perf_counter()
    for _ in range(N):
        h = hashlib.sha256(h).digest()
    return (time.perf_counter() - t0) * 1000


if __name__ == "__main__":
    et = sys.argv[1] if len(sys.argv) > 1 else "sin-etiqueta"
    una()  # calentamiento (Windows Defender infla el primer arranque)
    ms = sorted(una() for _ in range(7))
    med = statistics.median(ms)
    reg = {"etiqueta": et, "mediana_ms": round(med, 2), "min_ms": round(ms[0], 2),
           "max_ms": round(ms[-1], 2), "n": 7, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(os.path.join(SAL, "testigo.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    print(json.dumps(reg, ensure_ascii=False))
