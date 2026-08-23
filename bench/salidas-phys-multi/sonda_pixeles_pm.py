# -*- coding: utf-8 -*-
"""G4 / B19 — SONDA 2: los PIXELES son los mismos y el METADATO no lo es.

Es el control que hace interpretable todo lo demas. Para cada documento compara las
variantes de cabecera dos a dos y registra:
  * md5 del array decodificado por OpenCV (`cv2.imread`, el camino de PaddleX y de
    la mitad de EasyOCR) — en color y en gris.
  * md5 del array decodificado por PIL (`np.array(Image.open(...))`, el camino de
    RapidOCR y, via skimage, el de `easyocr.imgproc.loadImage`).
  * que expone cada decodificador del `pHYs`: `img.info` de PIL frente a lo que
    devuelve OpenCV (que es un array y nada mas).

Si los md5 coinciden en todas las variantes, cualquier diferencia de salida de un
motor solo puede venir de la cabecera. Y si un motor no cambia, no es que «los
pixeles fueran distintos»: eran identicos.

uso: python sonda_pixeles_pm.py <glob>
"""
import glob as _glob
import hashlib
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-phys-multi")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
JSN = os.path.join(BASE, "json")


def md5a(a):
    return hashlib.md5(np.ascontiguousarray(a).tobytes()).hexdigest()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    patron = sys.argv[1] if len(sys.argv) > 1 else "*.png"
    out = {}
    for ruta in sorted(_glob.glob(os.path.join(IMG, patron))):
        nom = os.path.splitext(os.path.basename(ruta))[0]
        raiz, etq = nom.rsplit("__", 1)
        color = cv2.imread(ruta, cv2.IMREAD_COLOR)
        gris = cv2.imread(ruta, cv2.IMREAD_GRAYSCALE)
        im = Image.open(ruta)
        pil = np.array(im)
        out[nom] = {
            "raiz": raiz, "variante": etq,
            "md5_cv2_color": md5a(color), "md5_cv2_gris": md5a(gris),
            "md5_pil": md5a(pil),
            "forma_cv2_color": list(color.shape), "forma_pil": list(pil.shape),
            "pil_info": {k: str(v) for k, v in dict(im.info).items()},
            "pil_dpi": str(im.info.get("dpi")) if "dpi" in im.info else None,
            "pil_aspect": str(im.info.get("aspect")) if "aspect" in im.info else None,
            "sha256_fichero": hashlib.sha256(open(ruta, "rb").read()).hexdigest(),
            "bytes": os.path.getsize(ruta),
        }
        im.close()
    # --- resumen por raiz: ¿coinciden los tres md5 en todas las variantes? ---
    resumen = {}
    for nom, v in out.items():
        r = resumen.setdefault(v["raiz"], {"variantes": [], "md5_cv2_color": set(),
                                           "md5_cv2_gris": set(), "md5_pil": set(),
                                           "dpi_expuesto": {}})
        r["variantes"].append(v["variante"])
        for k in ("md5_cv2_color", "md5_cv2_gris", "md5_pil"):
            r[k].add(v[k])
        r["dpi_expuesto"][v["variante"]] = v["pil_dpi"] or v["pil_aspect"] or "-"
    fin = {}
    for raiz, r in resumen.items():
        fin[raiz] = {
            "n_variantes": len(r["variantes"]),
            "md5_cv2_color_unicos": len(r["md5_cv2_color"]),
            "md5_cv2_gris_unicos": len(r["md5_cv2_gris"]),
            "md5_pil_unicos": len(r["md5_pil"]),
            "pixeles_identicos": (len(r["md5_cv2_color"]) == 1
                                  and len(r["md5_cv2_gris"]) == 1
                                  and len(r["md5_pil"]) == 1),
            "dpi_expuesto_por_pil": r["dpi_expuesto"],
        }
        print(f"{raiz:34s} variantes={fin[raiz]['n_variantes']:2d}  "
              f"md5 unicos cv2/pil={fin[raiz]['md5_cv2_color_unicos']}/"
              f"{fin[raiz]['md5_pil_unicos']}  "
              f"identicos={fin[raiz]['pixeles_identicos']}")
        print(f"    dpi que PIL expone: {fin[raiz]['dpi_expuesto_por_pil']}")
    json.dump({"por_png": out, "por_raiz": fin},
              open(os.path.join(JSN, "sonda_pixeles.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    ok = sum(1 for v in fin.values() if v["pixeles_identicos"])
    print(f"\nraices con pixeles identicos en todas sus variantes: {ok}/{len(fin)}")
