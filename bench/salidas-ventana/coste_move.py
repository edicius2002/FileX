"""Lo que cuesta el arreglo de N12, **medido AISLADO** (trampa 36).

El proyecto ya publicó que el cerrojo entero cuesta **1 169,7 µs, el 0,319 %**
de una conversión, del que la detección son **20,2 µs**. La trampa 36 dice que
por debajo de ±70 µs una diferencia entre dos totales no es una medida, así que
aquí **no se resta nada**: cada fila cronometra su operación y nada más, con el
fichero de origen fabricado FUERA del reloj.

Seis filas, y las dos últimas son las que deciden si el arreglo compensa:

  1. `os.replace`  destino AUSENTE   (mismo volumen)
  2. `os.replace`  destino EXISTENTE (mismo volumen)
  3. `shutil.move` destino AUSENTE   (mismo volumen) — lo de antes
  4. `shutil.move` destino EXISTENTE (mismo volumen) — lo de antes, y aquí cae
                                                       a `copy2`
  5. `mover_a_destino` cruzando volumen (`%TEMP%` → el otro disco)
  6. `shutil.move`     cruzando volumen — lo de antes, para la misma fila

Y dos controles: la detección sola (para poder contrastar con los 20,2 µs ya
publicados y ver si esta tanda vive en el mismo régimen) y `os.makedirs` sobre
un directorio que ya existe, que es lo único que las dos vías comparten.
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

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from filex import nucleo  # noqa: E402

CARGA = b"W" * 17_530     # el tamaño real de la salida `png -> webp` del corpus


def testigo_deriva(vueltas: int = 400_000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(vueltas):
        x += i
    return (time.perf_counter() - t0) * 1000


def testigo_proceso(tope: float = 20.0) -> float:
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=tope)
    except Exception:
        return tope * 1000
    return (time.perf_counter() - t0) * 1000


def medir(nombre: str, preparar, operacion, n: int) -> dict:
    ns = []
    for i in range(n):
        arg = preparar(i)
        t0 = time.perf_counter_ns()
        operacion(*arg)
        ns.append(time.perf_counter_ns() - t0)
    ns.sort()
    us = [x / 1000 for x in ns]
    return {"nombre": nombre, "n": n,
            "mediana_us": round(statistics.median(us), 1),
            "p10_us": round(us[int(n * 0.10)], 1),
            "p90_us": round(us[int(n * 0.90)], 1),
            "min_us": round(us[0], 1), "max_us": round(us[-1], 1)}


def main() -> int:
    n = int(os.environ.get("FILEX_N") or 1500)
    base = tempfile.mkdtemp(prefix="filex-coste-move-")
    otro_vol = os.path.join(AQUI, "tmp-otro-volumen")
    os.makedirs(otro_vol, exist_ok=True)
    mismo_vol = os.path.join(base, "destinos")
    os.makedirs(mismo_vol)
    origenes = os.path.join(base, "origenes")
    os.makedirs(origenes)

    cruza = (os.path.splitdrive(os.path.abspath(otro_vol))[0].lower()
             != os.path.splitdrive(os.path.abspath(base))[0].lower())

    # **El `sello` no es cosmético.** Sin él todas las filas usaban los mismos
    # nombres de destino, así que a partir de la segunda el destino YA existía
    # y las filas «AUSENTE» medían el camino de «EXISTENTE»: `shutil.move`
    # salía a 10 137 µs en un rename que no era tal, porque estaba cayendo a
    # `copy2`. Es la trampa 38 en su versión de medición: el arnés no estaba
    # en el estado que decía.
    def prep(dirdest, existe, sello):
        def _p(i):
            o = os.path.join(origenes, f"{sello}_o{i}.bin")
            with open(o, "wb") as f:
                f.write(CARGA)
            d = os.path.join(dirdest, f"{sello}_d{i}.bin")
            if existe:
                with open(d, "wb") as f:
                    f.write(b"V" * 4014)
            return (o, d)
        return _p

    d0, pr0 = testigo_deriva(), testigo_proceso()
    # Calentar (trampa 7): el primer toque de un directorio nuevo no es típico.
    for _ in range(50):
        o, d = prep(mismo_vol, False, "cal")(999_000 + _)
        os.replace(o, d)

    filas = []
    filas.append(medir("1 os.replace  destino AUSENTE (mismo volumen)",
                       prep(mismo_vol, False, "f1"), os.replace, n))
    filas.append(medir("2 os.replace  destino EXISTENTE (mismo volumen)",
                       prep(mismo_vol, True, "f2"), os.replace, n))
    filas.append(medir("3 shutil.move destino AUSENTE (mismo volumen)",
                       prep(mismo_vol, False, "f3"), shutil.move, n))
    filas.append(medir("4 shutil.move destino EXISTENTE (mismo volumen)",
                       prep(mismo_vol, True, "f4"), shutil.move, n))
    if cruza:
        m = min(n, 400)   # cruzar volumen copia: no hacen falta 1 500
        filas.append(medir("5 mover_a_destino cruzando volumen",
                           prep(otro_vol, False, "f5"), nucleo.mover_a_destino, m))
        filas.append(medir("6 shutil.move     cruzando volumen",
                           prep(otro_vol, False, "f6"), shutil.move, m))
    # El arreglo entero, tal y como lo llama `_un_salto`.
    filas.append(medir("7 mover_a_destino destino AUSENTE (mismo volumen)",
                       prep(mismo_vol, False, "f7"), nucleo.mover_a_destino, n))
    filas.append(medir("8 mover_a_destino destino EXISTENTE (mismo volumen)",
                       prep(mismo_vol, True, "f8"), nucleo.mover_a_destino, n))

    # Controles.
    def prep_det(i):
        d = os.path.join(mismo_vol, f"det{i}.bin")
        return (d,)
    filas.append(medir("C1 detección sobre destino AUSENTE",
                       prep_det, nucleo.destino_ocupado_por_un_tercero, n))

    def prep_det2(i):
        d = os.path.join(mismo_vol, f"det2_{i}.bin")
        with open(d, "wb") as f:
            f.write(b"V" * 4014)
        return (d,)
    filas.append(medir("C2 detección sobre destino EXISTENTE",
                       prep_det2, nucleo.destino_ocupado_por_un_tercero, n))
    filas.append(medir("C3 os.makedirs(exist_ok) del directorio destino",
                       lambda i: (mismo_vol,),
                       lambda p: os.makedirs(p, exist_ok=True), n))

    d1, pr1 = testigo_deriva(), testigo_proceso()
    res = {"cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
           "n": n, "cruza_volumen": cruza,
           "volumen_base": os.path.splitdrive(base)[0],
           "volumen_otro": os.path.splitdrive(os.path.abspath(otro_vol))[0],
           "carga_B": len(CARGA),
           "testigos": {"deriva_ini_ms": round(d0, 1), "deriva_fin_ms": round(d1, 1),
                        "deriva": round(d1 / d0, 2) if d0 else None,
                        "proceso_ini_ms": round(pr0, 1),
                        "proceso_fin_ms": round(pr1, 1),
                        "limpia": bool(d0 and 0.5 < d1 / d0 < 2.0
                                       and max(pr0, pr1) < 2000)},
           "filas": filas}
    with open(os.path.join(AQUI, "coste_move.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for fila in filas:
        print(f"{fila['nombre']:<52} {fila['mediana_us']:>9.1f} µs  "
              f"p90 {fila['p90_us']:>9.1f}")
    print("testigos:", res["testigos"])
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(otro_vol, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
