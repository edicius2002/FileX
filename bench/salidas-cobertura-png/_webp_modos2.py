"""Segundo intento de elicitar el predictor 13 (defecto D2) con texturas de
gradiente, que es donde ClampedAddSubtractHalf gana al resto."""
import collections
import json
import math
import os
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from pruebas import fixtures_cob_png as F  # noqa: E402
from filex import verificador as V  # noqa: E402

rnd = random.Random(11)
tmp = tempfile.mkdtemp(prefix="cobpng-modos2-")
orig = V._predice
cuenta = collections.Counter()
div = collections.Counter()


def espia(modo, px, i, w):
    cuenta[modo] += 1
    r = orig(modo, px, i, w)
    if modo == 13:
        L, T, TL, TR = px[i - 1], px[i - w], px[i - w - 1], px[i - w + 1]
        if r != F.predice_ref(13, L, T, TL, TR):
            div[13] += 1
    return r


V._predice = espia

casos = {
    "rampa": F.rejilla(200, 150, lambda x, y: (
        min(255, x), min(255, y), min(255, (x + y) // 2), min(255, (x * 2 + y) // 2))),
    "radial": F.rejilla(200, 150, lambda x, y: (
        int(127 + 120 * math.sin(x / 9.0)), int(127 + 120 * math.cos(y / 7.0)),
        int(127 + 120 * math.sin((x + y) / 11.0)),
        int(127 + 120 * math.sin(math.hypot(x - 100, y - 75) / 13.0)))),
    "escalon": F.rejilla(200, 150, lambda x, y: (
        (x // 7 * 13) % 256, (y // 5 * 17) % 256, ((x + y) // 3 * 5) % 256,
        (x // 11 * 23) % 256)),
    "ruidosuave": F.rejilla(200, 150, lambda x, y: (
        min(255, max(0, x + rnd.randrange(-3, 4))),
        min(255, max(0, y + rnd.randrange(-3, 4))),
        min(255, max(0, (x + y) // 2 + rnd.randrange(-3, 4))),
        min(255, max(0, (x * 3 + y) // 2 + rnd.randrange(-3, 4))))),
    "diagonal": F.rejilla(200, 150, lambda x, y: (
        (x - y) % 256, (x + 2 * y) % 256, (3 * x - y) % 256, (x + y) % 256)),
}
filas = []
for nombre, px in casos.items():
    p = os.path.join(tmp, nombre + ".png")
    w = os.path.join(tmp, nombre + ".webp")
    with open(p, "wb") as fh:
        fh.write(F.png(px, 6, 8, filtros=(0, 1, 2, 3, 4)))
    rc = subprocess.run(["magick", p, "-define", "webp:lossless=true", w],
                        capture_output=True, timeout=180)
    if rc.returncode != 0:
        print(nombre, "rc", rc.returncode, rc.stderr[:200])
        continue
    cuenta.clear()
    div.clear()
    apng = V.alfa_minimo(p, "png", exacto=True)
    aw = V.alfa_minimo(w, "webp", exacto=True)
    coincide = apng.get("alfa_min") == aw.get("alfa_min")
    filas.append({"caso": nombre, "png": apng.get("alfa_min"),
                  "webp": aw.get("alfa_min"), "coincide": coincide,
                  "modos": dict(sorted(cuenta.items())), "div13": div.get(13, 0)})
    print("%-11s coincide=%s modos=%s div13=%d"
          % (nombre, coincide, dict(sorted(cuenta.items())), div.get(13, 0)))

V._predice = orig
json.dump(filas, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "webp_modos2.json"), "w"), indent=1)
