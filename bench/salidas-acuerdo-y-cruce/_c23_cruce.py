# -*- coding: utf-8 -*-
"""C23 -- la curva fina del cruce "en proceso / sonda externa" de I9.

`bench/contrato-quinto-punto.md` sec.4.3 midio tres puntos (400x200 = 0,08 Mpx,
800x400 = 0,32 Mpx, 1920x960 = 1,84 Mpx) sobre rasters de SVG reales
(Inkscape/resvg/magick) y declaro el cruce en "~0,1 Mpx". Con tres puntos no
hay curva -- el propio informe lo dice de otra regla similar
(verificador-fidelidad.md sec.7.2) sin construirla aqui. Este script anade
puntos intermedios y de los dos extremos, sobre PNG SINTETICOS (no rasters de
SVG reales: mas rapido de generar, deterministas, y lo que se mide es el
DECODIFICADOR de `png_tinta_cajas`, que no sabe de donde vino el PNG).

Diseno de la caja: PROPORCIONAL a la imagen (40% del ancho, 8% del alto,
centrada), no absoluta. Es la misma semantica que el experimento original: el
mismo documento rasterizado a mas resolucion, con TODOS sus elementos
-incluida la caja de texto- creciendo juntos. Una caja de tamano ABSOLUTO fijo
mediria una pregunta distinta (¿crece el coste aun con una caja pequena?) y
queda declarada como NO cubierta aqui.

Metodo: mediana de n=9 (CLAUDE.md sec.3), con calentamiento (primera pasada
descartada). Comparacion contra `magick -crop ... -format "%[fx:standard_deviation]"`,
que es una operacion de la MISMA familia (estadistica de la caja: en vez de
tinta por umbral, desviacion estandar de luminancia -- ambas exigen decodificar
la region entera, que es el coste que se esta midiendo, no el valor exacto).

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-acuerdo-y-cruce/_c23_cruce.py
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAL = os.path.dirname(os.path.abspath(__file__))
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402

N = 9

# (ancho, alto) — proporcion 2:1, igual que el experimento original.
# Incluye los tres puntos ya medidos (400x200, 800x400, 1920x960) como control
# de continuidad con el informe anterior.
TAMANOS = [
    (140, 70), (200, 100), (283, 141), (400, 200), (566, 283),
    (800, 400), (1131, 566), (1600, 800), (1920, 960), (2263, 1131),
    (3200, 1600),
]


def fabricar(an: int, al: int) -> str:
    p = os.path.join(SAL, "sint_%dx%d.png" % (an, al))
    if os.path.isfile(p):
        return p
    # Contenido no trivial (gradiente + ruido determinista via -seed, trampa
    # 22 de CLAUDE.md), 8 bits RGB sin paleta -- para que el decodificador
    # entre por el mismo camino (color type 2) que un raster de SVG real.
    subprocess.run([MAGICK, "-size", "%dx%d" % (an, al), "-seed", "20260903",
                    "plasma:fractal", "+noise", "Gaussian", "-depth", "8", p],
                   stdin=subprocess.DEVNULL, capture_output=True,
                   timeout=60, check=True)
    return p


def caja_proporcional(an: int, al: int):
    cx0, cx1 = int(an * 0.30), int(an * 0.70)
    cy0, cy1 = int(al * 0.46), int(al * 0.54)
    return [{"caja": (cx0, cy0, cx1, cy1)}]


def mediana(fn, n=N):
    fn()  # calentamiento, no se cuenta
    ms = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ms.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(ms), 3)


def en_proceso(png: str, cajas) -> float:
    return mediana(lambda: V.png_tinta_cajas(png, cajas))


def con_magick(png: str, caja) -> float:
    x0, y0, x1, y1 = caja
    w, h = x1 - x0, y1 - y0
    geom = "%dx%d+%d+%d" % (w, h, x0, y0)

    def _una():
        subprocess.run([MAGICK, png, "-crop", geom, "+repage",
                        "-format", "%[fx:standard_deviation]", "info:"],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       timeout=60, check=True)
    return mediana(_una)


def main() -> None:
    filas = []
    for an, al in TAMANOS:
        mpx = round(an * al / 1_000_000, 4)
        png = fabricar(an, al)
        cajas = caja_proporcional(an, al)
        x0, y0, x1, y1 = cajas[0]["caja"]
        t_proc = en_proceso(png, cajas)
        t_magick = con_magick(png, (x0, y0, x1, y1))
        ganador = "proceso" if t_proc < t_magick else "magick"
        ratio = round(max(t_proc, t_magick) / max(min(t_proc, t_magick), 1e-6), 2)
        fila = {"ancho": an, "alto": al, "mpx": mpx,
                "caja_px": [x0, y0, x1, y1],
                "en_proceso_ms": t_proc, "magick_ms": t_magick,
                "gana": ganador, "ratio": ratio}
        filas.append(fila)
        print("%5d x %-5d  %7.4f Mpx  proceso=%9.3f ms  magick=%8.3f ms  "
              "gana=%-8s x%s" % (an, al, mpx, t_proc, t_magick, ganador, ratio))

    with open(os.path.join(SAL, "cruce_c23.json"), "w", encoding="utf-8") as fh:
        json.dump(filas, fh, indent=1, ensure_ascii=False)
    print("escrito cruce_c23.json")


if __name__ == "__main__":
    main()
