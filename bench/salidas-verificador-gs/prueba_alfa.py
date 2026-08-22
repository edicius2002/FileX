#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contrasta min(alfa) EN PROCESO contra `magick -format %[fx:minima.a]` sobre
los fixtures nuevos (TIFF comprimido, GIF, PNG Adam7) y sobre los ficheros ya
cubiertos, para comprobar que no se ha roto nada.

`magick` da 2.7431e+303 cuando no hay canal alfa y 1e59 sobre algunos GIF: se
normaliza a 1.0, como hizo el informe anterior.
"""
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
import verificador as V                                      # noqa: E402

FIX = os.path.join(AQUI, "fixtures")


def magick_alfa(ruta):
    p = subprocess.run(["magick", ruta, "-format", "%[fx:minima.a]", "info:"],
                       capture_output=True, text=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    t = (p.stdout or "").strip()
    try:
        v = float(t)
    except ValueError:
        return None, t[:60] or (p.stderr or "").strip()[:60]
    return (1.0 if v > 1.5 else v), t


def main():
    rutas = [os.path.join(FIX, n) for n in sorted(os.listdir(FIX))]
    rutas += [
        os.path.join(RAIZ, "corpus", "imagen", "alpha.png"),
        os.path.join(RAIZ, "corpus", "imagen", "tipico.png"),
        os.path.join(RAIZ, "corpus", "imagen", "trivial.png"),
        os.path.join(RAIZ, "corpus", "imagen", "tipico.webp"),
        os.path.join(RAIZ, "corpus", "imagen", "patologico_16bit.tif"),
        os.path.join(RAIZ, "bench", "salidas-referencia", "imagen",
                     "alpha_png-to.webp"),
        os.path.join(RAIZ, "bench", "salidas-referencia", "imagen",
                     "alpha_png-to.png8.png"),
        os.path.join(RAIZ, "bench", "salidas-referencia", "imagen",
                     "16bit_tif-to-d16.png"),
        os.path.join(RAIZ, "bench", "salidas-referencia", "imagen",
                     "alpha_png-to.avif"),
        os.path.join(RAIZ, "bench", "salidas-referencia", "video",
                     "trivial_mp4-to-palette.gif"),
        os.path.join(RAIZ, "bench", "salidas-referencia", "video",
                     "trivial_mp4-to-naive.gif"),
    ]
    res = []
    mal = 0
    for ruta in rutas:
        if not os.path.exists(ruta):
            continue
        r = V.alfa_minimo(ruta, exacto=True)
        mg, crudo = magick_alfa(ruta)
        ok = None
        if r.get("evaluable") and r.get("alfa_min") is not None and mg is not None:
            ok = abs(r["alfa_min"] - mg) <= 0.002
            if not ok:
                mal += 1
        fila = {"fichero": os.path.relpath(ruta, RAIZ).replace("\\", "/"),
                "bytes": os.path.getsize(ruta),
                "evaluable": r.get("evaluable"), "via": r.get("via"),
                "motivo": r.get("motivo"), "nota": r.get("nota"),
                "alfa_proceso": r.get("alfa_min"), "alfa_magick": mg,
                "magick_crudo": crudo, "exacto": r.get("exacto"),
                "no_trivial": r.get("alfa_no_trivial"),
                "filas_leidas": r.get("filas_leidas"),
                "ms": round(r.get("ms", 0), 3), "coincide": ok}
        res.append(fila)
        print("%-46s proc=%-8s magick=%-8s %-6s %7.1f ms  %s"
              % (os.path.basename(ruta), r.get("alfa_min"), mg,
                 {True: "OK", False: "*MAL*", None: "n/e"}[ok],
                 fila["ms"], (r.get("via") or r.get("motivo") or "")[:44]))
    print("\ndiscrepancias con magick: %d de %d comparables"
          % (mal, sum(1 for x in res if x["coincide"] is not None)))
    with open(os.path.join(AQUI, "alfa_cobertura.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"discrepancias": mal, "filas": res}, fh, ensure_ascii=False,
                  indent=1)
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())
