# -*- coding: utf-8 -*-
"""E1 / C8 caso 4 - comparacion de rasterizadores de SVG.

Mide, sobre el mismo e1.svg: geometria, RMSE entre pares y TINTA EN LA BANDA DE
TEXTO (y=155..205). La banda de texto es la medida que importa: un rasterizador sin
tipografia devuelve un PNG perfecto, del tamano correcto y sin una sola letra.
"""
import os, json, subprocess, itertools

S = r"D:\Work\research\FileX\bench\salidas-aristas"
O = os.path.join(S, "c8", "out")
IMG = {"inkscape 1.x (contenedor)": os.path.join(O, "out", "s_ink.png"),
       "resvg 0.46.0 (contenedor)": os.path.join(O, "out", "s_resvg.png"),
       "magick 7.1.2 (Windows)": os.path.join(O, "s_magick_win.png")}


def mag(args, t=120):
    p = subprocess.run(["magick"] + args, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=t)
    return ((p.stdout or "") + (p.stderr or "")).strip()


res = {"por_rasterizador": {}, "pares": []}
for k, p in IMG.items():
    geo = mag([p, "-format", "%wx%h", "info:"])
    banda = mag([p, "-crop", "400x50+0+155", "+repage", "-colorspace", "Gray",
                 "-threshold", "60%", "-format", "%[fx:100*(1-mean)]", "info:"])
    total = mag([p, "-colorspace", "Gray", "-threshold", "95%",
                 "-format", "%[fx:100*(1-mean)]", "info:"])
    res["por_rasterizador"][k] = {"bytes": os.path.getsize(p), "geometria": geo,
                                  "tinta_banda_texto_pct": round(float(banda), 3),
                                  "tinta_total_pct": round(float(total), 3)}
    print("%-28s %-9s %8d B  tinta banda texto %6.2f %%  tinta total %5.2f %%"
          % (k, geo, os.path.getsize(p), float(banda), float(total)))
for (ka, pa), (kb, pb) in itertools.combinations(IMG.items(), 2):
    r = mag(["compare", "-metric", "RMSE", pa, pb, "null:"])
    res["pares"].append({"a": ka, "b": kb, "rmse": r})
    print("  RMSE %-28s vs %-28s %s" % (ka, kb, r))
json.dump(res, open(os.path.join(S, "c8", "svg_comparacion.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
