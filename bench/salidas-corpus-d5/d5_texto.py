# -*- coding: utf-8 -*-
"""G3 — maquetas de la familia d5. El TEXTO no es mio: lo importo de `d4_texto.py`,
que esta copiado byte a byte en este directorio.

Por que asi y no con un texto nuevo
-----------------------------------
`bench/k-por-motor.md` §9 dice que el `k` esta ajustado sobre CUATRO documentos y que
uno de ellos (`patologico_escaneado`) no discrimina. Lo que falta no es texto nuevo:
es DEGRADACION nueva y RESOLUCION nueva. Si cambiara tambien el texto, cualquier
diferencia de CER frente a la familia d4 seria inatribuible.

Asi que la cadena de referencia es EXACTAMENTE la misma de `escaneado_d4`:
610 caracteres crudos, 35 acentuados, cuatro bloques. Se puede evaluar con
`ocr_eval_d4.py` (copia byte a byte) y `rid="d4"` sin tocar una linea, y las cifras
son comparables celda a celda con las 396 de `bench/k-por-motor.md`.

Lo que SI cambia por documento:
  * `escaneado_d5*`  -> ppp nativos 60-90 (B15). Los tamaños de letra suben para que
    a 72 ppp los cuatro bloques caigan a los dos lados del punto de ruptura, en vez
    de caer todos al lado malo. Ver §2 de bench/corpus-d5.md.
  * `patologico_d5*` -> maqueta IDENTICA a la de d4 (24/13/11/7 pt a 200 ppp).
    Solo cambia la degradacion (B19).
  * `realista_d5*`   -> maqueta IDENTICA a la de d4. Solo cambia la degradacion (B12).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d4_texto import ALTO, ANCHO, BLOQUES, MARGEN_X, MAQUETA, PPP_MAESTRO, pt  # noqa

# ---------------------------------------------------------------------------
# Maqueta A — la de d4, sin tocar. La usan `patologico_d5` y `realista_d5`.
# ---------------------------------------------------------------------------
MAQUETA_200 = MAQUETA

# ---------------------------------------------------------------------------
# Maqueta B — para los documentos de POCOS ppp nativos (B15).
#
# El razonamiento, en pixeles y no en ppp (que es la unidad que `bench/ppp-y-
# normalizacion.md` §2 dejo demostrado que importa):
#
#   en `escaneado_d4`, a 200 ppp nativos, los cuatro bloques miden de em
#       24 pt -> 66,7 px    13 pt -> 36,1 px    11 pt -> 30,6 px    7 pt -> 19,4 px
#   y el gradiente medido cae entre los 30,6 px (CER 1,6-14 %) y los 19,4 px
#   (CER 58,7-75,1 %). El punto de ruptura de este corpus esta, por tanto, entre
#   ~20 y ~31 px de em.
#
#   A 72 ppp nativos, 1 pt = 1 px. Si conservara los tamaños de d4 (24/13/11/7)
#   los cuatro bloques medirian 24/13/11/7 px, es decir LOS CUATRO por debajo del
#   punto de ruptura: una pared, no un gradiente (y una pared no mide nada, que es
#   justo el defecto de `patologico_escaneado` visto del otro lado).
#
#   Con 26/18/13/9 pt los cuatro bloques miden 26/18/13/9 px a 72 ppp: uno por
#   encima del punto de ruptura, uno justo en el, y dos por debajo. Eso es un
#   gradiente por construccion, y ademas deja sitio para que la subida a 90 ppp
#   (= 72 x 1,25, que es lo que la regla vigente produce) mueva algo: 32/22/16/11.
# ---------------------------------------------------------------------------
MAQUETA_72 = [
    ("titulo", "Arial-Bold", 26, 520, 0, BLOQUES["titulo"]),
    ("subtitulo", "Arial", 18, 900, 0, BLOQUES["subtitulo"]),
    ("cuerpo", "Arial", 13, 1300, 178, BLOQUES["cuerpo"]),
    ("pequeña", "Arial", 9, 2500, 124, BLOQUES["pequeña"]),
]

# etiqueta de maqueta -> (lista de bloques, ppp objetivo por defecto)
MAQUETAS = {
    "m200": MAQUETA_200,
    "m72": MAQUETA_72,
}

REFERENCIA = " ".join(" ".join(v) for v in BLOQUES.values())

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"referencia: {len(REFERENCIA)} caracteres crudos")
    for nom, maq in MAQUETAS.items():
        ppp = 200 if nom == "m200" else 72
        print(f"\n--- {nom} (a {ppp} ppp nativos) ---")
        for etq, f, p, y, i, lineas in maq:
            print(f"  [{etq:10s}] {f:11s} {p:2d} pt = {pt(p):4d} px maestro "
                  f"= {pt(p) * ppp / PPP_MAESTRO:5.1f} px de em a {ppp} ppp "
                  f"({len(lineas)} lineas, max {max(len(x) for x in lineas)} chars)")
