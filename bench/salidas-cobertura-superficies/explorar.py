"""Sonda de exploracion: cuanto cuesta un FileX y que caminos dan
`rechazados`, `hallazgos` o `sobrantes`. No es una medida publicable
(§3: nada de tiempos absolutos); solo sirve para elegir los casos de prueba.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from filex.nucleo import FileX

t0 = time.perf_counter()
fx = FileX()
t1 = time.perf_counter()
fx2 = FileX()
t2 = time.perf_counter()
print("frio  %.1f s" % (t1 - t0))
print("caliente %.1f s" % (t2 - t1))
print("motores", sorted(m.nombre for m in fx.disponibles))
print("destinos png:", fx.destinos("png"))
for dst in ("webp", "gif", "bmp", "pdf", "tiff"):
    d = fx.planificar("x.png", "y." + dst)
    print(dst, "hay=", d.hay, "rechazados=", len(d.rechazados),
          "aviso=", (d.aviso or "")[:60])
    for c, m in d.rechazados[:3]:
        print("   -", c.formatos, m[:70])
