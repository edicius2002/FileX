# -*- coding: utf-8 -*-
"""G2 / B18 — el censo que localiza los 33,22 puntos del "rasterizador".

`bench/k-por-motor.md` §6.2 atribuyo 33,22 puntos de CER al RASTERIZADOR: sobre
`escaneado_d4` a 200 ppp, Tesseract da 84,56 % desde ImageMagick y 51,34 % desde
Ghostscript, "con la misma geometria, la misma profundidad y el mismo espacio de
color". `sonda_raster.py` mide que ademas tienen LOS MISMOS PIXELES (42 pares, RMSE 0).

Esta sonda busca la variable que si difiere. No la deduce del codigo: la lee del
fichero y la contrasta CAMBIANDOLA (`-c user_defined_dpi=N`), que es la unica forma de
probar causalidad y no correlacion.

Para cada documento y variante registra:
  * el chunk `pHYs` del PNG: valor y UNIDAD (0 = sin unidad / solo relacion de aspecto,
    1 = pixeles por metro). Un `pHYs` con unidad 0 NO declara resolucion.
  * el md5 de los PIXELES (via PPM crudo): la clase de equivalencia de imagen.
  * lo que Tesseract dice por stderr sobre la resolucion.
  * el md5 del TEXTO devuelto y su CER, por `--psm`.
  * la misma llamada forzando `-c user_defined_dpi=<ppp reales>`.

Sonda de diagnostico, n=1, CPU. No produce ninguna cifra del barrido.
uso: python sonda_phys.py <doc> [doc ...]
"""
import hashlib
import io
import json
import os
import struct
import subprocess
import sys

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-psm")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
sys.path.insert(0, BASE)
from ocr_eval_psm import evaluar, ref_de_nombre  # noqa: E402

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
ENT = dict(os.environ)
ENT["TESSDATA_PREFIX"] = r"C:\Program Files\PDFgear\tessdata"

VARIANTES = ["im", "im_ppi", "gs", "gs16m_im", "im_sincs", "gs_aa1", "gs_aa4"]
PSMS = ["3", "6", "11"]
NATIVOS = {"escaneado_d2": 100, "escaneado_d3": 100, "escaneado_d4": 200,
           "escaneado_d4c": 200, "escaneado_d4e": 200, "escaneado_d4f": 240}


def phys(ruta):
    d = open(ruta, "rb").read()
    i = 8
    while i < len(d):
        ln = struct.unpack(">I", d[i:i + 4])[0]
        t = d[i + 4:i + 8].decode("latin1")
        if t == "pHYs":
            x, y, u = struct.unpack(">IIB", d[i + 8:i + 8 + ln])
            return {"x": x, "y": y, "unidad": u,
                    "declara_ppp": round(x / 39.3701, 2) if u == 1 else None,
                    "lectura": (f"{x / 39.3701:.2f} ppp" if u == 1
                                else "SIN UNIDAD (no declara resolucion)")}
        if t == "IEND":
            break
        i += 12 + ln
    return {"ausente": True, "lectura": "sin chunk pHYs"}


def md5_px(ruta):
    p = subprocess.run([MAGICK, ruta, "-depth", "8", "gray:-"],
                       stdin=subprocess.DEVNULL, capture_output=True, timeout=300)
    return hashlib.md5(p.stdout).hexdigest()


def tess(ruta, psm, dpi=None):
    args = [TESS, ruta, "stdout", "-l", "spa", "--psm", psm]
    if dpi:
        args += ["-c", f"user_defined_dpi={dpi}"]
    q = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600, env=ENT)
    err = " | ".join(l.strip() for l in q.stderr.splitlines() if l.strip())
    return q.stdout, err


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    out = []
    for doc in sys.argv[1:]:
        ref = ref_de_nombre(doc)
        nat = NATIVOS[doc]
        for v in VARIANTES:
            r = os.path.join(IMG, f"{v}__k1000__{doc}.png")
            if not os.path.exists(r):
                continue
            ph = phys(r)
            mpx = md5_px(r)
            for psm in PSMS:
                t0, e0 = tess(r, psm)
                t1, e1 = tess(r, psm, nat)
                fila = {
                    "doc": doc, "variante": v, "psm": psm, "ppp_reales": nat,
                    "phys": ph, "md5_pixeles": mpx, "bytes_png": os.path.getsize(r),
                    "sin_forzar": {
                        "md5_texto": hashlib.md5(t0.encode("utf-8")).hexdigest(),
                        "bytes": len(t0), "stderr": e0[:200],
                        "cer": evaluar(t0, ref)["cer_acentos_pct"]},
                    "forzando_dpi": {
                        "md5_texto": hashlib.md5(t1.encode("utf-8")).hexdigest(),
                        "bytes": len(t1), "stderr": e1[:200],
                        "cer": evaluar(t1, ref)["cer_acentos_pct"]},
                }
                out.append(fila)
                print(f"{doc:14s} {v:11s} psm{psm:>2s}  pHYs={ph['lectura']:32s} "
                      f"px={mpx[:8]}  CER={fila['sin_forzar']['cer']:7.2f} -> "
                      f"forzado {fila['forzando_dpi']['cer']:7.2f}   "
                      f"txt={fila['sin_forzar']['md5_texto'][:8]}/"
                      f"{fila['forzando_dpi']['md5_texto'][:8]}", flush=True)
    json.dump(out, io.open(os.path.join(BASE, "json", "sonda_phys.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
    # clases de equivalencia: ¿agrupan por rasterizador o por resolucion declarada?
    clases = {}
    for f in out:
        clave = (f["doc"], f["psm"])
        clases.setdefault(clave, {}).setdefault(
            f["sin_forzar"]["md5_texto"], []).append(f["variante"])
    print("\n=== clases de equivalencia de la SALIDA, sin forzar dpi ===")
    for (doc, psm), c in sorted(clases.items()):
        print(f"{doc:14s} psm{psm:>2s}: " +
              "  ||  ".join("{" + ",".join(v) + "}" for v in c.values()))
    print("escrito json/sonda_phys.json")
