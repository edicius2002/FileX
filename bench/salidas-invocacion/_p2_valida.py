# -*- coding: utf-8 -*-
"""P2 - CONTROL ANTIFALSO POSITIVO sobre las aristas revividas.

El vocabulario de firmas del verificador cubre 24 nombres (E1 sec.2, sesgo 3), y casi
ningun destino de imagen exotico esta dentro. Sin este control, una salida que sea un
JPEG dentro de un fichero .ppm pasa como arista viva -- que es exactamente lo que hizo
mi primera vuelta con vbn y xface. Aqui se vuelve a ejecutar cada arista revivida y se
pregunta a un TERCERO (magick identify) que formato es de verdad.

Escribe validacion_p2.json
"""
import os, sys, json, glob, re

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_val")
sys.path.insert(0, SAL)
from _p2_lib import corre, limpia

# como se llama en `magick identify` el formato que se pidio
ALIAS = {"jpeg": "JPEG", "jpg": "JPEG", "tif": "TIFF", "tiff": "TIFF", "ppm": "PPM",
         "pbm": "PBM", "pgm": "PGM", "pfm": "PFM", "exr": "EXR", "jp2": "JP2",
         "bmp": "BMP", "sgi": "SGI", "ras": "SUN", "rs": "SUN", "y": "GRAY",
         "im1": "IM1", "im24": "IM24", "png": "PNG", "ico": "ICO", "icn": "ICON",
         "icon": "ICON", "cur": "CUR", "gif": "GIF", "webp": "WEBP",
         "matte": "MATTE", "inline": "INLINE", "xface": "XFACE", "vbn": "VBN"}


def identifica(p):
    rc, err, _ = corre(["magick", "identify", "-quiet", "-format", "%m %wx%h", p], 45)
    import subprocess
    q = subprocess.run(["magick", "identify", "-quiet", "-format", "%m %wx%h", p],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       errors="replace", timeout=45)
    return (q.stdout or "").strip().split("\n")[0], (q.stderr or "")[-120:]


if __name__ == "__main__":
    limpia(TMP)
    fuentes = []
    for f, campo_args, campo_est in (("resid_p2.json", "p2_args", "p2_estado"),
                                     ("resid_p2b.json", None, "p2b_estado")):
        d = json.load(open(os.path.join(SAL, f), encoding="utf-8"))
        for r in d:
            if r.get(campo_est) == "viva":
                args = r.get(campo_args) if campo_args else r.get("p2b", {}).get("args")
                if args:
                    fuentes.append((r["a"], r["b"], r.get("motor"), args, f))
    print("VALIDACION DE %d ARISTAS REVIVIDAS\n" % len(fuentes), flush=True)
    out = []
    for i, (a, b, motor, args, orig) in enumerate(fuentes):
        for f in glob.glob(os.path.join(TMP, "*")):
            try:
                os.remove(f)
            except OSError:
                pass
        sal = os.path.join(TMP, "v%03d.%s" % (i, b))
        ar = [x.replace("__SAL__", sal) for x in args]
        rc, err, ms = corre(ar, 45, cwd=TMP)
        cands = sorted(x for x in os.listdir(TMP) if x.startswith("v%03d" % i))
        real = os.path.join(TMP, cands[0]) if cands else None
        ident, ierr = identifica(real) if real else ("", "sin fichero")
        fm = ident.split(" ")[0] if ident else ""
        esp = ALIAS.get(b.lower())
        veredicto = ("COINCIDE" if esp and fm.upper() == esp else
                     "DISCREPA" if esp and fm else
                     "NO COMPROBABLE")
        out.append({"a": a, "b": b, "motor": motor, "origen": orig, "rc": rc,
                    "identify": ident, "esperado": esp, "veredicto": veredicto,
                    "bytes": os.path.getsize(real) if real else -1,
                    "err_identify": ierr.replace("\n", " ")})
        print("  %-8s -> %-10s identify='%s' esperado=%-6s %s" %
              (a, b, ident, esp, veredicto), flush=True)
    json.dump(out, open(os.path.join(SAL, "validacion_p2.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    from collections import Counter
    print("\n", dict(Counter(o["veredicto"] for o in out)))
