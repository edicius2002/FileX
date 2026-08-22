# -*- coding: utf-8 -*-
"""G2 / B18 — POR QUE difieren ImageMagick y Ghostscript rasterizando el mismo PDF.

M1 (`bench/k-por-motor.md` §6.2) midio 33,22 puntos de CER de diferencia sobre
`escaneado_d4` con la MISMA geometria (1294x1716), la MISMA profundidad (8 bits) y el
MISMO espacio de color declarado. Aqui no se deduce del codigo por que: se sondea en
ejecucion sobre los PIXELES (CLAUDE.md §5, y el precedente de `limit_type` de PaddleX,
donde deducir del codigo dio lo contrario que medir).

Que mide, por par de variantes y por documento:
  * histograma completo de los 256 niveles y su distancia L1 normalizada
  * media, desviacion, minimo, maximo, numero de niveles distintos usados
  * fraccion de pixeles identicos, y la distribucion de la diferencia con signo
  * RMSE y PSNR (CLAUDE.md trampa 5: SSIM devuelve 0 para identicas en esta build)
  * una medida de NITIDEZ: energia del gradiente (|dx|+|dy| medio), que separa
    "remuestreo/antialias distinto" de "transferencia de tono distinta"
  * el ajuste TONAL: para cada nivel de A, la mediana del nivel de B en esos pixeles.
    Si el par difiere SOLO por una curva de tono, este mapeo es monotono y determinista
    y aplicarlo a A reproduce B casi exactamente. Se mide el residuo tras aplicarlo.

uso: python sonda_raster.py <doc> [doc ...]
env: IMGDIR
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-psm")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
Image.MAX_IMAGE_PIXELS = None


def cargar(ruta):
    a = np.asarray(Image.open(ruta).convert("L")).astype(np.int16)
    return a


def stats(a):
    h = np.bincount(a.ravel().astype(np.int64), minlength=256)
    gx = np.abs(np.diff(a.astype(np.int32), axis=1)).mean()
    gy = np.abs(np.diff(a.astype(np.int32), axis=0)).mean()
    return {
        "px": int(a.size), "forma": list(a.shape),
        "media": round(float(a.mean()), 4),
        "desv": round(float(a.std()), 4),
        "min": int(a.min()), "max": int(a.max()),
        "niveles_usados": int((h > 0).sum()),
        "frac_negro_puro": round(float((a == 0).mean()), 6),
        "frac_blanco_puro": round(float((a == 255).mean()), 6),
        "tinta_lt128": round(float((a < 128).mean()), 6),
        "gradiente_medio": round(float((gx + gy) / 2), 4),
        "hist": h.tolist(),
    }


def comparar(a, b):
    if a.shape != b.shape:
        return {"error": f"formas distintas {a.shape} vs {b.shape}"}
    d = (b - a).astype(np.int32)
    rmse = float(np.sqrt((d.astype(np.float64) ** 2).mean()))
    psnr = float("inf") if rmse == 0 else 20 * np.log10(255.0 / rmse)
    # mapeo tonal empirico A->B: mediana de B para cada nivel de A
    mapa = np.arange(256, dtype=np.float64)
    cuenta = np.zeros(256, dtype=np.int64)
    af = a.ravel()
    bf = b.ravel()
    orden = np.argsort(af, kind="stable")
    afs, bfs = af[orden], bf[orden]
    lim = np.searchsorted(afs, np.arange(257))
    for v in range(256):
        i, j = lim[v], lim[v + 1]
        cuenta[v] = j - i
        if j > i:
            mapa[v] = float(np.median(bfs[i:j]))
    # residuo tras aplicar el mapeo tonal
    b_pred = mapa[np.clip(a, 0, 255)]
    res = b.astype(np.float64) - b_pred
    rmse_res = float(np.sqrt((res ** 2).mean()))
    # monotonia del mapeo sobre los niveles realmente presentes
    pres = np.nonzero(cuenta)[0]
    mono = bool(np.all(np.diff(mapa[pres]) >= -0.5)) if len(pres) > 1 else True
    ha = np.bincount(af.astype(np.int64), minlength=256).astype(np.float64) / af.size
    hb = np.bincount(bf.astype(np.int64), minlength=256).astype(np.float64) / bf.size
    return {
        "identicas": bool(rmse == 0),
        "frac_px_iguales": round(float((d == 0).mean()), 6),
        "rmse": round(rmse, 4), "psnr_db": round(psnr, 3) if rmse else None,
        "dif_media": round(float(d.mean()), 4),
        "dif_min": int(d.min()), "dif_max": int(d.max()),
        "dist_L1_histogramas": round(float(np.abs(ha - hb).sum() / 2), 6),
        "mapeo_tonal_monotono": mono,
        "rmse_residuo_tras_mapeo_tonal": round(rmse_res, 4),
        "reduccion_por_mapeo_tonal": (round(1 - rmse_res / rmse, 4) if rmse else None),
        "mapa_tonal_muestra": {str(v): round(mapa[v], 2)
                               for v in range(0, 256, 16) if cuenta[v] > 0},
    }


VARIANTES = ["im", "gs", "gs16m_im", "gs16m_im601", "gs16m_im709",
             "im_sincs", "gs_aa1", "gs_aa4"]

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    out = {"por_imagen": {}, "pares": {}}
    for doc in sys.argv[1:]:
        imgs = {}
        for v in VARIANTES:
            r = os.path.join(IMG, f"{v}__k1000__{doc}.png")
            if os.path.exists(r):
                imgs[v] = cargar(r)
                out["por_imagen"][f"{v}__{doc}"] = dict(
                    stats(imgs[v]), bytes=os.path.getsize(r))
        base = "im"
        if base not in imgs:
            continue
        for v, a in imgs.items():
            if v == base:
                continue
            c = comparar(imgs[base], a)
            out["pares"][f"{doc}::{base}_vs_{v}"] = c
            print(f"{doc:16s} im vs {v:12s} iguales={c.get('frac_px_iguales')} "
                  f"rmse={c.get('rmse')} residuo_tras_tono={c.get('rmse_residuo_tras_mapeo_tonal')} "
                  f"mono={c.get('mapeo_tonal_monotono')}", flush=True)
        for v in imgs:
            s = out["por_imagen"][f"{v}__{doc}"]
            print(f"   {v:12s} media={s['media']:8.3f} desv={s['desv']:7.3f} "
                  f"niveles={s['niveles_usados']:3d} grad={s['gradiente_medio']:7.3f} "
                  f"tinta<128={s['tinta_lt128']:.4f}", flush=True)
    json.dump(out, io.open(os.path.join(BASE, "json", "sonda_raster.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
    print("escrito json/sonda_raster.json")
