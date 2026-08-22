# -*- coding: utf-8 -*-
"""G1 / paso 0 — geometria real del corpus escaneado.

Mide, sin suponer nada: tamano de pagina en puntos, tamano en pixeles de la
imagen incrustada, y los ppp nativos que se deducen de dividir una cosa entre
la otra. Es el dato que invalida las marcas de d2/d3 de `bench/gpu-fase2.md`.

uso: python 00_geometria.py
"""
import json
import os

import pypdfium2 as pdfium

C = r"D:\Work\research\FileX\corpus\pdf"
OUT = r"D:\Work\research\FileX\bench\salidas-ocr-ppp"
DOCS = ["patologico_escaneado", "escaneado_d1", "escaneado_d2", "escaneado_d3"]

res = {}
print(f"{'documento':<24} {'pagina (pt)':<18} {'imagen (px)':<14} "
      f"{'dpi declarado':<14} {'ppp nativos':<12} {'x200ppp seria':<14}")
for d in DOCS:
    doc = pdfium.PdfDocument(os.path.join(C, d + ".pdf"))
    pg = doc[0]
    w_pt, h_pt = pg.get_size()
    imgs = list(pg.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)))
    if not imgs:
        print(f"{d:<24} SIN IMAGEN INCRUSTADA")
        continue
    m = imgs[0].get_metadata()
    ppp_x = m.width / (w_pt / 72.0)
    ppp_y = m.height / (h_pt / 72.0)
    r200 = (round(w_pt / 72.0 * 200), round(h_pt / 72.0 * 200))
    res[d] = {
        "pagina_pt": [round(w_pt, 2), round(h_pt, 2)],
        "imagen_px": [m.width, m.height],
        "bits_por_pixel": m.bits_per_pixel,
        "dpi_declarado": [round(m.horizontal_dpi, 1), round(m.vertical_dpi, 1)],
        "ppp_nativos": [round(ppp_x, 1), round(ppp_y, 1)],
        "ppp_nativo": int(round(ppp_x)),
        "px_si_200ppp": list(r200),
        "factor_interpolacion_a_200": round(200.0 / ppp_x, 3),
        "n_imagenes": len(imgs),
    }
    print(f"{d:<24} {w_pt:7.2f}x{h_pt:<9.2f} {m.width:5d}x{m.height:<8d} "
          f"{m.horizontal_dpi:<14.1f} {ppp_x:<12.1f} {r200[0]}x{r200[1]} "
          f"(x{200.0/ppp_x:.2f})")
    doc.close()

json.dump(res, open(os.path.join(OUT, "geometria.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\n-> geometria.json")
