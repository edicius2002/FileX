# -*- coding: utf-8 -*-
"""G1 / paso 1b — via B: extraer la imagen incrustada SIN rasterizar.

`pdfimages` (poppler) no existe en este Windows; el agente anterior lo invocaba
a traves de WSL. Aqui se usa pypdfium2, que ya esta instalado en los dos venv que
hacen falta, y que decodifica el stream de imagen del objeto de pagina sin pasar
por el renderizador: los pixeles que salen son los del JPEG incrustado.

Se guardan dos variantes por documento:
  ext__<doc>.png      la imagen tal cual (color original)
  extg__<doc>.png     la misma en escala de grises, para que la comparacion con
                      las vias rasterizadas (que son -colorspace Gray) aisle los
                      ppp y no mezcle el efecto del espacio de color.
"""
import os

import pypdfium2 as pdfium

C = r"D:\Work\research\FileX\corpus\pdf"
IMG = r"D:\Work\research\FileX\bench\salidas-ocr-ppp\img"
DOCS = ["patologico_escaneado", "escaneado_d1", "escaneado_d2", "escaneado_d3"]
os.makedirs(IMG, exist_ok=True)

for d in DOCS:
    doc = pdfium.PdfDocument(os.path.join(C, d + ".pdf"))
    pg = doc[0]
    objs = list(pg.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)))
    if not objs:
        print(f"  {d:<24} SIN IMAGEN")
        continue
    im = objs[0].get_bitmap(render=False).to_pil()
    a = os.path.join(IMG, f"ext__{d}.png")
    b = os.path.join(IMG, f"extg__{d}.png")
    im.save(a)
    im.convert("L").save(b)
    print(f"  {'ext__'+d:<38} {im.size[0]}x{im.size[1]} {im.mode}")
    print(f"  {'extg__'+d:<38} {im.size[0]}x{im.size[1]} L")
    doc.close()
