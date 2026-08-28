"""Coste VIEJO contra NUEVO en la MISMA tanda.

`CLAUDE.md` sec.3: *las cifras absolutas de tandas distintas no son comparables;
las relativas dentro de una tanda, si*. Los 162,04 ms de D1 son de otra tanda,
asi que el ratio contra ellos no mide el arreglo: mide dos maquinas distintas.
Aqui se monta un paquete `filex` desechable con el `huella.py` de HEAD y se
alternan las dos versiones en la misma tanda, con los dos testigos.

Directorio desechable, listado antes y despues (R21).

Salida: bench/salidas-huella/coste_pareado.json
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

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAL = os.path.dirname(os.path.abspath(__file__))
N = 9

HIJO = '''
import sys, time
sys.path.insert(0, r"{base}")
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


def deriva():
    t = time.perf_counter()
    x = 0
    for i in range(400000):
        x += i * i
    return (time.perf_counter() - t) * 1000


def nivel():
    t = time.perf_counter()
    try:
        subprocess.run([sys.executable, "-c", "pass"], capture_output=True,
                       timeout=20)
    except subprocess.TimeoutExpired:
        return 20000.0
    return (time.perf_counter() - t) * 1000


def main() -> None:
    des = tempfile.mkdtemp(prefix="filex-huella-coste-")
    print("desechable:", des)
    print("antes:", os.listdir(des))
    try:
        base = os.path.join(des, "viejo")
        os.makedirs(base)
        shutil.copytree(os.path.join(RAIZ, "filex"),
                        os.path.join(base, "filex"))
        v = subprocess.run(["git", "-C", RAIZ, "show", "HEAD:filex/huella.py"],
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=60).stdout
        with open(os.path.join(base, "filex", "huella.py"), "w",
                  encoding="utf-8") as fh:
            fh.write(v)

        guiones = {}
        for et, b in (("viejo", base), ("nuevo", RAIZ)):
            g = os.path.join(des, f"h_{et}.py")
            with open(g, "w", encoding="utf-8") as fh:
                fh.write(HIJO.format(base=b.replace("\\", "/")))
            guiones[et] = g
            subprocess.run([sys.executable, g], capture_output=True, timeout=120)

        d0, n0 = deriva(), nivel()
        datos = {"viejo": [], "nuevo": []}
        for _ in range(N):                       # alternando, no en bloques
            for et in ("viejo", "nuevo"):
                r = subprocess.run([sys.executable, guiones[et]],
                                   capture_output=True, text=True, timeout=120)
                datos[et].append([float(x) for x in r.stdout.split()])
        d1, n1 = deriva(), nivel()

        med = statistics.median
        res = {"n": N, "testigos": {
            "deriva_antes_ms": round(d0, 2), "deriva_despues_ms": round(d1, 2),
            "nivel_antes_ms": round(n0, 2), "nivel_despues_ms": round(n1, 2)}}
        res["testigos"]["veredicto"] = (
            "SUCIA" if (max(d0, d1) / min(d0, d1) > 1.3
                        or max(n0, n1) / min(n0, n1) > 2.0) else "limpia")
        for et in ("viejo", "nuevo"):
            res[et] = {
                "primera_huella_ms": round(med(x[0] for x in datos[et]), 2),
                "seis_frio_ms": round(med(x[1] for x in datos[et]), 2),
                "seis_caliente_ms": round(med(x[2] for x in datos[et]), 6)}
        for k in ("primera_huella_ms", "seis_frio_ms", "seis_caliente_ms"):
            res.setdefault("ratio_nuevo_sobre_viejo", {})[k] = round(
                res["nuevo"][k] / res["viejo"][k], 3)

        with open(os.path.join(SAL, "coste_pareado.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, ensure_ascii=False)
        print(json.dumps(res, indent=1, ensure_ascii=False))
    finally:
        print("despues:", sorted(os.listdir(des)))
        shutil.rmtree(des, ignore_errors=True)


if __name__ == "__main__":
    main()
