"""Compara los 14 predictores VP8L de `verificador.py` con el oraculo escrito
desde la especificacion de libwebp. Busca discrepancias."""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from pruebas import fixtures_cob_png as F  # noqa: E402
from filex import verificador as V  # noqa: E402

rnd = random.Random(4321)
casos = []
# esquinas + azar
vals = [0x00000000, 0xFFFFFFFF, 0xFF000000, 0x0000FF00, 0x80808080, 0x017F01FE,
        0x01020304, 0xFEFDFCFB]
for _ in range(400):
    vals.append(rnd.randrange(1 << 32))

por_modo = {m: 0 for m in range(14)}
ejemplos = {}
for _ in range(4000):
    L, T, TL, TR = (rnd.choice(vals) for _ in range(4))
    w = 8
    px = [0] * 32
    i = 12
    px[i - 1] = L
    px[i - w] = T
    px[i - w - 1] = TL
    px[i - w + 1] = TR
    for m in range(14):
        a = V._predice(m, px, i, w)
        b = F.predice_ref(m, L, T, TL, TR)
        if a != b:
            por_modo[m] += 1
            ejemplos.setdefault(m, (L, T, TL, TR, a, b))

print("discrepancias por modo:", {k: v for k, v in por_modo.items() if v})
for m, e in sorted(ejemplos.items()):
    print("  modo %d: L=%08X T=%08X TL=%08X TR=%08X  sujeto=%08X libwebp=%08X"
          % (m, e[0], e[1], e[2], e[3], e[4], e[5]))

# minimo reproducible del modo 13, canal a canal
print("--- caso minimo modo 13 ---")
for (L, T, TL) in [(0x00000000, 0x14141414, 0x1E1E1E1E),
                   (0x0A0A0A0A, 0x0A0A0A0A, 0x0F0F0F0F)]:
    a = V._clamp_half(L, T, TL)
    b = F.clamp_half_ref(L, T, TL)
    print("  L=%08X T=%08X TL=%08X -> sujeto=%08X libwebp=%08X %s"
          % (L, T, TL, a, b, "IGUAL" if a == b else "DISCREPA"))

# tabla de planos
print("--- _codigo_a_plano contra los 8 primeros kCodeToPlane ---")
ok = 0
for k, cod in enumerate(F.KCODE_A_PLANO_8):
    for xsize in (1, 2, 7, 100):
        esperado = F.distancia_plano_ref(xsize, cod)
        obtenido = V._distancia_plano(xsize, k + 1)
        if esperado == obtenido:
            ok += 1
        else:
            print("  cod %d xsize %d: esperado %d obtenido %d"
                  % (k + 1, xsize, esperado, obtenido))
print("  celdas iguales:", ok, "de", len(F.KCODE_A_PLANO_8) * 4)
print("  planos generados:", len(V._PLANOS))
json.dump({"discrepan_por_modo": por_modo}, open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "vp8l.json"), "w"),
    indent=1)
