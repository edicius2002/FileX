# -*- coding: utf-8 -*-
"""K1 / hito 5 — medianas de n=9 de las aristas que deciden el hito.

`CLAUDE.md` §3: medianas de n>=9 y **dos testigos de ruido, siempre**: uno mide
la DERIVA dentro de la tanda (bucle monohilo de Python) y otro el NIVEL de carga
de la máquina (lanzamiento de proceso). El monohilo solo es ciego a la
contención multinúcleo, y ya etiquetó `limpia` una tanda que salió x6,8.

**Y el testigo lleva su propio tope de 20 s**: un testigo que puede tumbar la
medición no es un testigo (van tres casos en un día).

    python bench/salidas-hito5/_medianas.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import invocacion  # noqa: E402
from filex.trabajo import DirectorioDeTrabajo  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _sonda import CASOS, ENT, argv_docker  # noqa: E402

N = 9
TOPE_TESTIGO = 20.0

#: Las cuatro que deciden el hito, más el arranque en vacío del contenedor, que
#: es la línea base: sin él no se sabe cuánto del coste es el motor y cuánto es
#: la frontera.
QUIERO = ["L01", "L09", "C01", "P01"]


def testigo_deriva() -> float:
    """Bucle monohilo. Detecta deriva DENTRO de la tanda. Ciego a la contención."""
    t0 = time.perf_counter()
    x = 0
    for i in range(400_000):
        x = (x * 31 + i) & 0xFFFFFFFF
    return (time.perf_counter() - t0) * 1000


def testigo_nivel() -> tuple[float, bool]:
    """Lanzamiento de proceso. Detecta el NIVEL de carga. Con tope propio."""
    t0 = time.perf_counter()
    r = invocacion.ejecutar(["ffprobe", "-hide_banner", "-version"],
                            timeout=TOPE_TESTIGO)
    ms = (time.perf_counter() - t0) * 1000
    return ms, r.agotado


def vacio_docker(imagen: str = "filex-convertx") -> float:
    """Arranque de contenedor en vacío: la frontera, sin motor."""
    r = invocacion.ejecutar(["docker", "run", "--rm", "--init", "--network", "none",
                             imagen, "true"], timeout=120)
    return r.ms


def main() -> int:
    casos = {c[0]: c for c in CASOS}
    out = {"n": N, "muestras": {}, "testigos": {}}

    d0 = statistics.median([testigo_deriva() for _ in range(5)])
    n0, ago0 = testigo_nivel()

    vac = []
    for _ in range(N):
        vac.append(vacio_docker())
    out["muestras"]["_vacio"] = {"ms": sorted(vac), "mediana": statistics.median(vac)}
    print(f"_vacio   mediana {statistics.median(vac):8.0f} ms")

    for cid in QUIERO:
        _, motor, o, d, _, plantilla = casos[cid]
        entrada = os.path.join(ENT, f"entrada.{o}")
        ms = []
        for _ in range(N):
            t = DirectorioDeTrabajo(prefijo="filex-h5m-")
            try:
                argv = argv_docker(entrada, f"salida.{o}", t.ruta,
                                   plantilla(f"/ent/salida.{o}", f"/trabajo/salida.{d}"))
                r = invocacion.ejecutar(argv, timeout=300, cwd=t.ruta)
                ms.append(r.ms)
            finally:
                t.cerrar()
        out["muestras"][cid] = {
            "motor": motor, "arista": f"{o}->{d}",
            "ms": sorted(round(x, 1) for x in ms),
            "mediana": round(statistics.median(ms), 1),
        }
        print(f"{cid:<8} {motor:<12} {o}->{d:<6} mediana {statistics.median(ms):8.0f} ms")

    d1 = statistics.median([testigo_deriva() for _ in range(5)])
    n1, ago1 = testigo_nivel()
    out["testigos"] = {
        "deriva_antes_ms": round(d0, 2), "deriva_despues_ms": round(d1, 2),
        "deriva_factor": round(d1 / d0, 2) if d0 else None,
        "nivel_antes_ms": round(n0, 1), "nivel_despues_ms": round(n1, 1),
        "nivel_agotado": bool(ago0 or ago1),
        # La sesión de escritorio remoto está activa a propósito: TODO sale
        # etiquetado SUCIA. Es estructural, no un fallo.
        "etiqueta": "SUCIA",
    }
    print("\ntestigos:", json.dumps(out["testigos"], ensure_ascii=False))

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "medianas.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
