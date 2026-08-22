# -*- coding: utf-8 -*-
"""M1 / B13 — control de reproducción: mis celdas de `escaneado_d4` frente a las que
P1 publicó en `bench/ppp-y-normalizacion.md` §2.1 y §2.1b, medidas otro día, en otra
tanda y con otro directorio de pesos.

`CLAUDE.md` §3 dice que las cifras absolutas de tandas distintas no son comparables:
eso vale para los TIEMPOS. El CER, con el dispositivo fijado y `det=si` en las 397
celdas, tiene que salir idéntico. Esto lo comprueba, celda a celda.

uso: python repro_p1.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tablas_km import CONFIGS, _res_fusionada, clave  # noqa: E402

# ppp -> factor sobre los 200 nativos de escaneado_d4
P1 = {
    "PaddleOCR v6 medium": {
        0.5: 19.13, 0.625: 16.95, 0.75: 17.11, 0.875: 21.64, 1.0: 19.30,
        1.125: 20.97, 1.25: 13.09, 1.4: 36.24, 1.5: 25.17, 1.6: 36.24, 1.8: 36.41},
    "RapidOCR v5 mobile (defecto)": {
        0.5: 40.44, 0.625: 40.94, 0.75: 41.28, 0.875: 42.11, 1.0: 41.78,
        1.125: 42.28, 1.25: 41.61, 1.4: 41.95, 1.5: 41.61, 1.6: 41.28, 1.8: 41.61},
    "RapidOCR v6 small (defecto)": {
        0.5: 36.58, 0.625: 36.74, 0.75: 36.58, 0.875: 37.25, 1.0: 36.91,
        1.125: 42.79, 1.25: 32.72, 1.4: 36.58, 1.5: 36.58, 1.6: 33.05, 1.8: 36.91},
    "RapidOCR v6 small + R6": {
        0.5: 30.70, 0.625: 26.68, 0.75: 18.96, 0.875: 21.31, 1.0: 18.62,
        1.125: 23.32, 1.25: 24.50, 1.4: 28.86, 1.5: 30.20, 1.6: 23.83, 1.8: 29.19},
    "Docling+RapidOCR torch (defecto)": {
        0.5: 36.58, 0.625: 54.70, 0.75: 36.74, 0.875: 36.91, 1.0: 36.91,
        1.125: 32.72, 1.25: 33.22, 1.4: 33.05, 1.6: 32.89},
    "Docling+RapidOCR torch + R6": {
        0.5: 37.92, 0.625: 23.49, 0.75: 25.34, 0.875: 18.12, 1.0: 19.63,
        1.125: 19.13, 1.25: 22.82, 1.4: 23.15, 1.6: 22.82},
    # EasyOCR: P1 lo midio con n=3 y muestreador de VRAM
    "EasyOCR (CRAFT + latin_g2)": {
        0.5: 62.58, 0.625: 62.25, 0.75: 61.58, 0.875: 63.26, 1.0: 61.41,
        1.125: 62.42, 1.25: 61.41, 1.4: 60.91, 1.6: 62.42, 1.8: 58.39},
}

pref = {n: e for e, n in CONFIGS}
tot = ok = 0
lineas = []
for nombre, celdas in P1.items():
    res, _f, _c = _res_fusionada(pref[nombre])
    if res is None:
        lineas.append((nombre, "sin datos", None, None))
        continue
    for f, esperado in sorted(celdas.items()):
        r = res.get(clave(f, "escaneado_d4"))
        mio = r.get("cer_acentos_pct") if r and "cer_acentos_pct" in r else None
        tot += 1
        igual = mio is not None and abs(mio - esperado) < 0.005
        ok += igual
        if not igual:
            lineas.append((nombre, f"×{f:g}", esperado, mio))

print(f"celdas comprobadas: {tot}   idénticas: {ok}   distintas: {tot - ok}")
for n, f, e, m in lineas:
    print(f"  DIFIERE  {n:34s} {f:>7s}  P1={e}  M1={m}")
json.dump({"celdas": tot, "identicas": ok, "distintas": tot - ok,
           "detalle": [{"config": n, "factor": f, "p1": e, "m1": m}
                       for n, f, e, m in lineas]},
          io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "json", "repro_p1.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
