"""Tercera sonda: buscar un par (origen, destino) cuyo plan lleve `aviso`,
y un destino que deje ficheros `sobrantes` (punto 5)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from filex.nucleo import FileX

fx = FileX()
origenes = sorted({a.origen for a in fx.grafo.aristas})
destinos = sorted({a.destino for a in fx.grafo.aristas})
print("origenes", len(origenes), "destinos", len(destinos))
con_aviso = []
for o in origenes:
    for d in destinos:
        if o == d:
            continue
        dec = fx.planificar("x." + o, "y." + d)
        if dec.hay and dec.aviso:
            con_aviso.append((o, d, len(dec.camino.pasos)))
print("pares con aviso:", len(con_aviso))
for o, d, n in con_aviso[:20]:
    print("   ", o, "->", d, "saltos", n)
print("mp4 destinos:", [x for x in fx.destinos("mp4")][:40])
