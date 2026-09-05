"""M04 no discrimina, y hay que decidir si es un hueco de la prueba o un
MUTANTE EQUIVALENTE. Se comprueba exhaustivamente sobre los 256^3 = 16 777 216
tercetos si `paeth(a,b,c) == paeth(b,a,c)`."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from filex import verificador as V  # noqa: E402

distintos = 0
primero = None
p = V._paeth
for a in range(256):
    for b in range(a + 1, 256):     # a == b es trivialmente simetrico
        for c in range(256):
            if p(a, b, c) != p(b, a, c):
                distintos += 1
                if primero is None:
                    primero = (a, b, c, p(a, b, c), p(b, a, c))
print("tercetos con a<b comprobados: %d" % (256 * 255 // 2 * 256))
print("asimetricos:", distintos, primero)
