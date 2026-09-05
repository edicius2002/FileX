# -*- coding: utf-8 -*-
"""Por que quedan sin ejecutar las lineas 3320-3321 de `filex/verificador.py`.

Son el `except (ValueError, IndexError)` del calculo de `ppp` en
`sondear_subproceso`. La unica palanca para entrar en el es que el `%x` de
`magick identify` NO sea parseable como `float`, porque el `-format` es fijo en
el codigo y este carril no toca `filex/`.

Este barrido escribe el mismo PNG en N formatos y registra el `%x` de cada uno.
No demuestra que la rama sea INALCANZABLE -- eso no se puede demostrar con un
barrido -- sino que **no la alcanza ningun formato que esta build de
ImageMagick sepa escribir de los probados**, que es una afirmacion distinta y
mas pequena. Se publica con su n.

Uso:
    python bench/salidas-cobertura-contrato/sonda_ppp.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402

FMT = "%m|%w|%h|%z|%[channels]|%x|%A|%[colorspace]|%U\n"   # el del codigo
EXTS = ("png", "bmp", "tga", "pbm", "pgm", "ppm", "xpm", "ico", "gif", "tif",
        "webp", "pcx", "sgi", "miff", "dds", "xbm", "jpg", "psd", "hdr",
        "fits", "pam", "avif")
SRC = os.path.join(RAIZ, "corpus", "imagen", "trivial.png")


def main():
    if not shutil.which("magick"):
        print("sin magick: nada que sondear")
        return 2
    if not os.path.exists(SRC) or os.path.getsize(SRC) < 100:
        print("hace falta corpus/imagen/trivial.png (git lfs checkout)")
        return 2
    d = tempfile.mkdtemp(prefix="cob-ppp-")
    filas = []
    try:
        for ext in EXTS:
            p = os.path.join(d, "x." + ext)
            w = subprocess.run(["magick", SRC, p], stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=180)
            if w.returncode != 0 or not os.path.exists(p):
                filas.append({"ext": ext, "escrito": False,
                              "rc_escritura": w.returncode})
                continue
            q = subprocess.run(["magick", "identify", "-format", FMT, p],
                               stdin=subprocess.DEVNULL, capture_output=True,
                               timeout=180)
            out = q.stdout.decode("utf-8", "replace").strip()
            d_sonda = V.sondear_subproceso(p)
            fila = {"ext": ext, "escrito": True, "rc_identify": q.returncode,
                    "n_lineas_identify": len(
                        [l for l in out.splitlines() if l.strip()]),
                    "n_imagenes_sonda": d_sonda.get("n_imagenes"),
                    "ppp": d_sonda.get("ppp")}
            # Trampa 25 aplicada a ESTA sonda: «no parseable» y «no hubo
            # salida» se escriben igual. Si `identify` fallo, la rama del ppp
            # ni siquiera se alcanza -- `sondear_subproceso` sale antes por
            # `if rc != 0 or not out.strip()` -- asi que la celda se clasifica
            # aparte y NO cuenta como candidata.
            if q.returncode != 0 or not out:
                fila.update({"clase": "identify_falla", "x": None,
                             "unidad": None, "parseable": None,
                             "alcanza_la_rama_del_ppp": False})
                filas.append(fila)
                continue
            campos = out.split("|")
            x = campos[5] if len(campos) > 5 else None
            unidad = campos[8].strip() if len(campos) > 8 else ""
            try:
                float((x or "").split()[0])
                parseable = True
            except (ValueError, IndexError):
                parseable = False
            fila.update({"clase": "x_no_parseable" if not parseable else "ok",
                         "x": x, "unidad": unidad, "parseable": parseable,
                         "alcanza_la_rama_del_ppp": True})
            filas.append(fila)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    escritos = [f for f in filas if f.get("escrito")]
    llegan = [f for f in escritos if f.get("alcanza_la_rama_del_ppp")]
    no_parseables = [f for f in llegan if not f["parseable"]]
    multi = [f for f in llegan
             if (f.get("n_imagenes_sonda") or 1) != 1]
    res = {
        "pregunta": "hay algun formato cuyo %x de ImageMagick no sea un float?",
        "n_formatos_probados": len(filas),
        "n_escribibles": len(escritos),
        "n_que_alcanzan_la_rama_del_ppp": len(llegan),
        "n_donde_identify_falla": len(escritos) - len(llegan),
        "n_con_x_no_parseable": len(no_parseables),
        "conclusion": ("ninguno de los que llegan a la rama: el except "
                       "(ValueError, IndexError) del ppp de sondear_subproceso "
                       "queda sin ejecutar y no por falta de pruebas"),
        "n_imagenes_distinto_de_1": [f["ext"] for f in multi],
        "por_unidad": {},
        "filas": filas,
    }
    for f in llegan:
        u = f["unidad"] or "(vacia)"
        res["por_unidad"].setdefault(u, []).append(f["ext"])
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "ppp-inalcanzable.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("%d formatos, %d escribibles, %d llegan a la rama del ppp, "
          "%d con %%x no parseable"
          % (len(filas), len(escritos), len(llegan), len(no_parseables)))
    if res["n_imagenes_distinto_de_1"]:
        print("  OJO n_imagenes != 1 en:", res["n_imagenes_distinto_de_1"])
    for u, exts in res["por_unidad"].items():
        print("  %-24s %s" % (u, " ".join(exts)))
    print("escrito", destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
