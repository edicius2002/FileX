"""Alcance real de D2: convierte PNG con alfa a WebP SIN PERDIDA con `magick`
y compara `alfa_minimo` de los dos. Si difieren, el decodificador VP8L de
`verificador.py` esta leyendo mal pixeles de verdad."""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from pruebas import fixtures_cob_png as F  # noqa: E402
from filex import verificador as V  # noqa: E402

tmp = tempfile.mkdtemp(prefix="cobpng-webp-")
filas = []
import random  # noqa: E402
rnd = random.Random(99)

casos = [("hueco", F.rgba_con_hueco(24, 16, 9, 7, 17))]
for k in range(6):
    casos.append(("azar%d" % k, [[(rnd.randrange(256), rnd.randrange(256),
                                   rnd.randrange(256), rnd.randrange(256))
                                  for _ in range(24)] for _ in range(16)]))
casos.append(("degradado", F.rejilla(32, 32, lambda x, y: (x * 8 % 256, y * 8 % 256,
                                                           128, (x * 7 + y * 3) % 256))))

for nombre, px in casos:
    p = os.path.join(tmp, nombre + ".png")
    w = os.path.join(tmp, nombre + ".webp")
    with open(p, "wb") as fh:
        fh.write(F.png(px, 6, 8, filtros=(0, 1, 2, 3, 4)))
    try:
        rc = subprocess.run(["magick", p, "-define", "webp:lossless=true", w],
                            capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        print("sin magick:", e)
        sys.exit(0)
    if rc.returncode != 0 or not os.path.exists(w):
        print(nombre, "rc", rc.returncode, rc.stderr[:300])
        continue
    a_png = V.alfa_minimo(p, "png", exacto=True)
    a_webp = V.alfa_minimo(w, "webp", exacto=True)
    ref = F.referencia(F.png(px, 6, 8, filtros=(0, 1, 2, 3, 4)))
    filas.append({"caso": nombre, "ref": ref["alfa_min"],
                  "png": a_png.get("alfa_min"), "webp": a_webp.get("alfa_min"),
                  "via_webp": a_webp.get("via"), "motivo": a_webp.get("motivo"),
                  "evaluable": a_webp.get("evaluable")})
    print("%-10s ref=%.6f png=%s webp=%s via=%s %s"
          % (nombre, ref["alfa_min"], a_png.get("alfa_min"), a_webp.get("alfa_min"),
             a_webp.get("via"), a_webp.get("motivo") or ""))

json.dump(filas, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "webp_ida_vuelta.json"), "w"), indent=1)
