"""Qué cuesta el cerrojo de máquina, contra el de proceso y contra una conversión.

El cerrojo de proceso del hito 7 costaba **3,2 µs**. Un candado de fichero
cuesta bastante más y **hay que saber cuánto**: si costara lo que una
conversión, no compensaría, y refutar el propio arreglo sería el resultado.

Las tres cifras se toman **en la misma tanda**, porque «las cifras absolutas de
tandas distintas no son comparables; las relativas dentro de una tanda, sí».
Y con los **dos testigos de ruido** de `CLAUDE.md` §3: uno mide deriva (bucle
monohilo) y el otro nivel (lanzamiento de proceso), con tope en el propio
testigo.
"""

from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex import nucleo  # noqa: E402
from filex.nucleo import FileX  # noqa: E402

TOPE_TESTIGO = 20.0


def testigo_deriva(n: int = 200_000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(n):
        x += i * i
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> tuple[float, bool]:
    """Lanzamiento de proceso. **Con tope**: un testigo que puede tumbar la
    medición no es un testigo (`CLAUDE.md` §3, caso P3: ×94,6)."""
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                       timeout=TOPE_TESTIGO)
    except Exception:
        return TOPE_TESTIGO * 1000, True
    return (time.perf_counter() - t0) * 1000, False


def mediana_us(fn, n: int) -> dict:
    ms = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ms.append((time.perf_counter() - t0) * 1e6)
    ms.sort()
    return {"n": n, "mediana_us": round(statistics.median(ms), 2),
            "p90_us": round(ms[int(n * 0.9)], 2), "max_us": round(ms[-1], 2)}


def ciclo(ruta: str) -> None:
    nucleo._reservar_destino(ruta)
    nucleo._soltar_destino(ruta)


def main() -> int:
    base = os.path.join(AQUI, "desechable", "coste")
    shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base, exist_ok=True)
    destino = os.path.join(base, "x.webp")
    entrada = os.path.join(base, "tipico.png")
    shutil.copy2(os.path.join(RAIZ, "corpus", "imagen", "tipico.png"), entrada)

    out: dict = {}
    d0 = testigo_deriva()
    n0, tope0 = testigo_nivel()

    # Calentar: Windows Defender infla el primer arranque (trampa 7), y el
    # directorio de candados se crea la primera vez.
    for modo in ("proceso", "maquina"):
        os.environ["FILEX_CERROJO_DESTINO"] = modo
        for _ in range(500):
            ciclo(destino)

    n = 20_000
    for modo in ("proceso", "maquina", "ninguno"):
        os.environ["FILEX_CERROJO_DESTINO"] = modo
        out[f"reservar+soltar[{modo}]"] = mediana_us(lambda: ciclo(destino), n)

    # La mitad de DETECCIÓN, por separado: es la que se paga DOS veces por
    # conversión (al reservar y justo antes del `move`).
    os.environ["FILEX_CERROJO_DESTINO"] = "maquina"
    with open(destino, "wb") as f:
        f.write(b"x" * 1000)
    out["deteccion[destino existe]"] = mediana_us(
        lambda: nucleo.destino_ocupado_por_un_tercero(destino), n)
    os.remove(destino)
    out["deteccion[destino no existe]"] = mediana_us(
        lambda: nucleo.destino_ocupado_por_un_tercero(destino), n)

    # Y el denominador, en la MISMA tanda: una conversión completa.
    fx = FileX(raices_lectura=[base])
    ms = []
    for i in range(11):
        sal = os.path.join(base, f"c{i}.webp")
        t0 = time.perf_counter()
        conv = fx.convertir(entrada, sal, {})
        ms.append((time.perf_counter() - t0) * 1000)
        assert conv.ok, conv.motivo
    ms.sort()
    out["conversion png->webp"] = {"n": len(ms), "mediana_ms": round(statistics.median(ms), 1),
                                   "p90_ms": round(ms[int(len(ms) * 0.9)], 1)}

    d1 = testigo_deriva()
    n1, tope1 = testigo_nivel()
    deriva = d1 / d0 if d0 else 0
    limpia = 0.7 < deriva < 1.4 and not (tope0 or tope1) and max(n0, n1) < 3 * min(n0, n1)
    out["_testigos"] = {"deriva_monohilo": round(deriva, 2),
                        "nivel_proceso_ms": [round(n0, 1), round(n1, 1)],
                        "testigo_agotado": bool(tope0 or tope1),
                        "etiqueta": "limpia" if limpia else "SUCIA"}

    conv_us = out["conversion png->webp"]["mediana_ms"] * 1000
    for k in ("proceso", "maquina"):
        v = out[f"reservar+soltar[{k}]"]["mediana_us"]
        out[f"reservar+soltar[{k}]"]["porcentaje_de_una_conversion"] = round(
            100 * v / conv_us, 5)
    det = out["deteccion[destino no existe]"]["mediana_us"]
    out["coste_total_por_conversion_us"] = round(
        out["reservar+soltar[maquina]"]["mediana_us"] + 2 * det, 2)
    out["coste_total_porcentaje"] = round(
        100 * out["coste_total_por_conversion_us"] / conv_us, 5)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    with open(os.path.join(AQUI, "coste.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
