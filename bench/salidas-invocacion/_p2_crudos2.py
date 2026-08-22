# -*- coding: utf-8 -*-
"""P2 / C15-a cuarta vuelta - separar PERDIDA INEVITABLE de DESTRUIDO en los crudos.

En _p2_crudos.py los formatos "lossy a priori" se compararon contra la referencia
EN COLOR, y eso mide la perdida del formato, no la de la invocacion: `gray` tiene
que dar RMSE alto contra una imagen en color. Aqui se compara cada uno contra su
REFERENCIA IDEAL DEGRADADA -- lo mejor que ese formato podria entregar-- y esa
diferencia si es atribuible a la invocacion.

Escribe crudos_ideal.json
"""
import os, re, sys, json

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
POOL3 = os.path.join(SAL, "pool3")
TMP = os.path.join(SAL, "tmp_crudos")
sys.path.insert(0, SAL)
from _p2_lib import corre

W, H = 64, 48
IDEAL = {
    "gray":   ["-colorspace", "Gray"],
    "graya":  ["-colorspace", "Gray"],
    "mono":   ["-monochrome"],
    "bayer":  None,          # mosaico CFA: no hay ideal trivial -> PENDIENTE
    "bayera": None,
    "map":    None,
    "ftxt":   [],            # deberia ser SIN PERDIDA: se compara contra el original
}


def rmse(a, b):
    p = corre(["magick", "compare", "-metric", "RMSE", a, b, "null:"], 60)
    m = re.search(r"\(([0-9.eE+-]+)\)", p[1])
    return float(m.group(1)) if m else None


if __name__ == "__main__":
    ref = os.path.join(POOL3, "ref.png")
    prev = json.load(open(os.path.join(SAL, "crudos_p2.json"), encoding="utf-8"))
    out = {}
    for fmt, ops in IDEAL.items():
        k = "imagemagick|" + fmt
        v = prev.get(k, {})
        if v.get("mejor") is None:
            out[fmt] = {"estado": v.get("estado"), "nota": "no llego a producir salida"}
            print("  %-8s sin salida" % fmt)
            continue
        var = v["mejor"]["variante"]
        args = [i["args"] for i in v["intentos"] if i["variante"] == var][0]
        sem = os.path.join(POOL3, "s." + fmt)
        sal = os.path.join(TMP, "q_%s.png" % fmt)
        corre(["magick"] + args + [fmt + ":" + sem, "-auto-orient", "png:" + sal], 45)
        if ops is None:
            out[fmt] = {"rmse_color": v["mejor"]["rmse"], "ideal": None,
                        "veredicto": "PENDIENTE",
                        "nota": "sin referencia ideal trivial para este formato"}
            print("  %-8s PENDIENTE (rmse color %.5f)" % (fmt, v["mejor"]["rmse"]))
            continue
        ideal = os.path.join(TMP, "ideal_%s.png" % fmt)
        corre(["magick", ref] + ops + ["png:" + ideal], 45)
        r = rmse(ideal, sal)
        ver = ("INTEGRO" if r is not None and r < 0.02 else
               "DEGRADADO" if r is not None and r < 0.15 else "DESTRUIDO")
        out[fmt] = {"rmse_color": v["mejor"]["rmse"], "rmse_vs_ideal": r,
                    "ideal_ops": ops, "veredicto": ver}
        print("  %-8s rmse vs color=%.5f   rmse vs IDEAL=%s -> %s" %
              (fmt, v["mejor"]["rmse"], ("%.5f" % r) if r is not None else "-", ver))
    json.dump(out, open(os.path.join(SAL, "crudos_ideal.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
