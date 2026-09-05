"""Censo de que predictores VP8L usa de verdad un WebP sin perdida escrito por
`magick`, y si el modo 13 (el del defecto D2) aparece. Envuelve `_predice` con
un contador: no toca el codigo, solo lo observa."""
import collections
import json
import os
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from pruebas import fixtures_cob_png as F  # noqa: E402
from filex import verificador as V  # noqa: E402

rnd = random.Random(7)
tmp = tempfile.mkdtemp(prefix="cobpng-modos-")
orig = V._predice
cuenta = collections.Counter()
divergen = collections.Counter()


def espia(modo, px, i, w):
    cuenta[modo] += 1
    r = orig(modo, px, i, w)
    if modo == 13:
        L, T, TL, TR = px[i - 1], px[i - w], px[i - w - 1], px[i - w + 1]
        if r != F.predice_ref(13, L, T, TL, TR):
            divergen[13] += 1
    return r


V._predice = espia

casos = {
    "ruido": F.rejilla(160, 120, lambda x, y: (rnd.randrange(256), rnd.randrange(256),
                                               rnd.randrange(256), rnd.randrange(256))),
    "suave": F.rejilla(160, 120, lambda x, y: ((x * 3 + y) % 256, (y * 2) % 256,
                                               (x ^ y) % 256, (x + y * 2) % 256)),
    "bandas": F.rejilla(160, 120, lambda x, y: (x % 256, 255 - (y % 256), 64,
                                                (x // 4 * 7 + y // 3 * 11) % 256)),
    "foto": F.rejilla(160, 120, lambda x, y: (
        (x * x + y * y) % 256, (x * 5 + rnd.randrange(9)) % 256,
        (y * 3 + rnd.randrange(9)) % 256, max(0, 255 - (x + y)))),
}
filas = []
for nombre, px in casos.items():
    p = os.path.join(tmp, nombre + ".png")
    w = os.path.join(tmp, nombre + ".webp")
    with open(p, "wb") as fh:
        fh.write(F.png(px, 6, 8, filtros=(0, 1, 2, 3, 4)))
    try:
        rc = subprocess.run(["magick", p, "-define", "webp:lossless=true", w],
                            capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        print("sin magick:", e)
        sys.exit(0)
    if rc.returncode != 0:
        print(nombre, "rc", rc.returncode, rc.stderr[:200])
        continue
    cuenta.clear()
    divergen.clear()
    a_png = V.alfa_minimo(p, "png", exacto=True)
    a_webp = V.alfa_minimo(w, "webp", exacto=True)
    filas.append({"caso": nombre, "png": a_png.get("alfa_min"),
                  "webp": a_webp.get("alfa_min"),
                  "modos": dict(sorted(cuenta.items())),
                  "divergencias_modo13": divergen.get(13, 0)})
    print("%-8s png=%s webp=%s modos=%s div13=%d"
          % (nombre, a_png.get("alfa_min"), a_webp.get("alfa_min"),
             dict(sorted(cuenta.items())), divergen.get(13, 0)))

V._predice = orig
json.dump(filas, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "webp_modos.json"), "w"), indent=1)
