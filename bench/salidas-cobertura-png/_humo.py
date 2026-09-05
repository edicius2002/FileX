"""Control de que el CONSTRUCTOR de fixtures produce PNG validos, juzgado por
un tercero (`magick identify`) y por el oraculo. Si el constructor esta mal, el
resto del carril mide su propio error."""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from pruebas import fixtures_cob_png as F  # noqa: E402
from filex import verificador as V  # noqa: E402

CASOS = []
for ent in (0, 1):
    for filtros in ((0,), (1,), (2,), (3,), (4,), (0, 1, 2, 3, 4)):
        CASOS.append(("rgba8 ent=%d f=%s" % (ent, filtros),
                      F.png(F.rgba_con_hueco(11, 7, 5, 3, 17), 6, 8,
                            entrelazado=ent, filtros=filtros)))
        CASOS.append(("rgba16 ent=%d f=%s" % (ent, filtros),
                      F.png(F.rgba_con_hueco(9, 5, 4, 2, 3000, bd=16), 6, 16,
                            entrelazado=ent, filtros=filtros)))
        CASOS.append(("ga8 ent=%d f=%s" % (ent, filtros),
                      F.png(F.gris_alfa_con_hueco(10, 6, 2, 4, 40), 4, 8,
                            entrelazado=ent, filtros=filtros)))
    for bd in (1, 2, 4, 8):
        n = 1 << bd
        pal = [(i * 255 // (n - 1), 0, 255 - i * 255 // (n - 1)) for i in range(n)]
        trns = [255] * n
        trns[1] = 30
        CASOS.append(("pal%d ent=%d" % (bd, ent),
                      F.png(F.indices(13, 5, lambda x, y: 1 if (x, y) == (9, 3) else 0),
                            3, bd, plte=pal, trns=trns, entrelazado=ent,
                            filtros=(0, 1, 2, 3, 4))))

tmp = tempfile.mkdtemp(prefix="cobpng-humo-")
malos = 0
for nombre, datos in CASOS:
    p = os.path.join(tmp, nombre.replace(" ", "_").replace("=", "") + ".png")
    with open(p, "wb") as fh:
        fh.write(datos)
    try:
        salida = subprocess.run(["magick", "identify", "-format", "%wx%h", p],
                                capture_output=True, timeout=30)
        idm = salida.stdout.decode("utf-8", "replace").strip(), salida.returncode
    except (OSError, subprocess.TimeoutExpired) as e:
        idm = ("<sin magick: %s>" % e, None)
    ref = F.referencia(datos)
    got = V.alfa_minimo(p, "png", exacto=True)
    ok = (abs(got.get("alfa_min", -1) - ref["alfa_min"]) < 1e-12
          and got.get("primer_transparente") == (list(ref["primer_transparente"])
                                                 if ref["primer_transparente"] else None)
          or got.get("primer_transparente") == ref["primer_transparente"])
    coincide = (got.get("alfa_min") is not None
                and abs(got["alfa_min"] - ref["alfa_min"]) < 1e-12)
    if not coincide:
        malos += 1
    print("%-28s magick=%-10s ref=%.6f got=%s pt_ref=%s pt_got=%s %s"
          % (nombre, idm[0], ref["alfa_min"], got.get("alfa_min"),
             ref["primer_transparente"], got.get("primer_transparente"),
             "OK" if coincide else "*** DISCREPA"))
print("casos:", len(CASOS), "discrepan:", malos, "tmp:", tmp)
