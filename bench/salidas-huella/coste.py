"""Coste de la huella, contra los numeros que D1 publico (`deuda-sondeo.md`
sec.2.7): primera huella 168,93 ms, los seis motores en frio 162,04 ms, en
caliente 0,0028 ms.

Medianas de n>=9 y los DOS testigos de ruido: uno mide deriva (bucle monohilo)
y otro mide nivel (lanzamiento de proceso), con tope de 20 s al propio testigo
—un testigo que puede tumbar la medicion no es un testigo—.

El frio se mide en SUBPROCESOS, uno por repeticion: la cache de `huella` es de
proceso y medir el frio dos veces en el mismo proceso mide el caliente.

Salida: bench/salidas-huella/coste.json
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.dirname(os.path.abspath(__file__))
N = 9

HIJO = r'''
import sys, time
sys.path.insert(0, r"{raiz}")
from filex import huella
from filex.motores import ImageMagick, Ghostscript, FFmpeg
from filex.motor_contenedor import (PandocEnContenedor, LibreOfficeEnContenedor,
                                    CalibreEnContenedor)
SEIS = [ImageMagick, Ghostscript, FFmpeg, PandocEnContenedor,
        LibreOfficeEnContenedor, CalibreEnContenedor]
t0 = time.perf_counter()
huella.de_motor(SEIS[0])
t1 = time.perf_counter()
for c in SEIS[1:]:
    huella.de_motor(c)
t2 = time.perf_counter()
cal = []
for _ in range(200):
    a = time.perf_counter()
    for c in SEIS:
        huella.de_motor(c)
    cal.append((time.perf_counter() - a) * 1000)
cal.sort()
print("%.4f %.4f %.6f" % ((t1-t0)*1000, (t2-t0)*1000, cal[len(cal)//2]))
'''


def deriva() -> float:
    """Testigo 1: bucle monohilo. Detecta la deriva DENTRO de la tanda."""
    t = time.perf_counter()
    x = 0
    for i in range(400000):
        x += i * i
    return (time.perf_counter() - t) * 1000


def nivel() -> float:
    """Testigo 2: lanzamiento de proceso. Detecta el NIVEL de carga de la
    maquina, que el monohilo no ve (cabe en un nucleo libre de 12)."""
    t = time.perf_counter()
    try:
        subprocess.run([sys.executable, "-c", "pass"], capture_output=True,
                       timeout=20)
    except subprocess.TimeoutExpired:
        return 20000.0
    return (time.perf_counter() - t) * 1000


def main() -> None:
    src = HIJO.format(raiz=RAIZ.replace("\\", "/"))
    guion = os.path.join(SAL, "_hijo_coste.py")
    with open(guion, "w", encoding="utf-8") as fh:
        fh.write(src)

    # calentar (trampa 7: Windows Defender infla el primer arranque)
    subprocess.run([sys.executable, guion], capture_output=True, timeout=120)

    d0, n0 = deriva(), nivel()
    primera, seis_frio, seis_cal = [], [], []
    for _ in range(N):
        r = subprocess.run([sys.executable, guion], capture_output=True,
                           text=True, timeout=120)
        a, b, c = r.stdout.split()
        primera.append(float(a))
        seis_frio.append(float(b))
        seis_cal.append(float(c))
    d1, n1 = deriva(), nivel()

    med = statistics.median
    res = {
        "n": N,
        "primera_huella_ms": round(med(primera), 2),
        "seis_motores_frio_ms": round(med(seis_frio), 2),
        "seis_motores_caliente_ms": round(med(seis_cal), 6),
        "D1_primera_huella_ms": 168.93,
        "D1_seis_motores_frio_ms": 162.04,
        "D1_seis_motores_caliente_ms": 0.0028,
        "testigos": {
            "deriva_antes_ms": round(d0, 2), "deriva_despues_ms": round(d1, 2),
            "deriva_ratio": round(d1 / d0, 2),
            "nivel_antes_ms": round(n0, 2), "nivel_despues_ms": round(n1, 2),
        },
    }
    res["testigos"]["veredicto"] = (
        "SUCIA" if (max(d0, d1) / min(d0, d1) > 1.3
                    or max(n0, n1) / min(n0, n1) > 2.0) else "limpia")
    res["ratio_primera_vs_D1"] = round(res["primera_huella_ms"] / 168.93, 3)
    res["ratio_frio_vs_D1"] = round(res["seis_motores_frio_ms"] / 162.04, 3)
    res["ratio_caliente_vs_D1"] = round(
        res["seis_motores_caliente_ms"] / 0.0028, 2)

    with open(os.path.join(SAL, "coste.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    os.remove(guion)


if __name__ == "__main__":
    main()
