#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sonda del RECORTE: que array recibe de verdad la red, sondeado EN EJECUCION.

El barrido de `k` de este informe se aplana por arriba en los dos motores de
GPU, y una explicacion plausible no es un mecanismo (trampa 36). CLAUDE.md §5
lo dice como regla: *sondear capacidades en ejecucion, no deducirlas* -- y el
propio proyecto ya pago el error contrario con `limit_type` de PaddleX, que
"deducirlo del codigo daba lo contrario".

Aqui se instrumenta la funcion que reescala, no se lee su documentacion:

  * EasyOCR: se envuelve `easyocr.imgproc.resize_aspect_ratio`, que es por
    donde pasa la imagen antes del detector CRAFT, y se registran la forma de
    ENTRADA y la de SALIDA.
  * Docling+RapidOCR: se envuelve `rapidocr.utils.pre_prosessing` /
    `LoadImage`, y a falta de eso se registra la forma que recibe el detector
    interceptando `TextDetector.__call__`.

uso: python sonda_recorte_b26.py <easyocr|docling-r6> <doc> <factor>
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, ROOT)

VISTO = []


def forma(x):
    try:
        return list(getattr(x, "shape", ()))
    except Exception:
        return None


def main():
    config, doc, factor = sys.argv[1], sys.argv[2], float(sys.argv[3])
    import b26_borde as B
    from filex import gpu

    native = dict((d[0], d[1]) for d in B.DOCS)[doc]
    area = dict((d[0], d[2]) for d in B.DOCS)[doc]
    ppp = int(round(native * factor))
    out = {"config": config, "doc": doc, "factor": factor, "ppp": ppp,
           "mpx": round(B.mpx(area, native, factor), 3)}

    with gpu.Lock("B26recorte-" + config):
        if config == "easyocr":
            import torch
            tl = os.path.join(os.path.dirname(torch.__file__), "lib")
            if os.path.isdir(tl):
                os.add_dll_directory(tl)
            import easyocr
            import easyocr.detection as det
            import easyocr.imgproc as imgproc
            orig = imgproc.resize_aspect_ratio

            def espia(img, square_size, *a, **kw):
                r = orig(img, square_size, *a, **kw)
                VISTO.append({"donde": "resize_aspect_ratio", "entrada": forma(img),
                              "square_size": square_size, "salida": forma(r[0])})
                return r
            imgproc.resize_aspect_ratio = espia
            det.resize_aspect_ratio = espia
            x = easyocr.Reader(["es", "en"], gpu=True, verbose=False)
            import inspect
            fx = inspect.signature(x.readtext)
            out["canvas_size_por_defecto"] = (
                fx.parameters["canvas_size"].default if "canvas_size" in fx.parameters else None)
            out["mag_ratio_por_defecto"] = (
                fx.parameters["mag_ratio"].default if "mag_ratio" in fx.parameters else None)
            ruta, _ = B.raster(doc, factor, native, False)
            x.readtext(ruta, detail=0, paragraph=False)

        elif config == "docling-r6":
            import torch
            tl = os.path.join(os.path.dirname(torch.__file__), "lib")
            if os.path.isdir(tl):
                os.add_dll_directory(tl)
            import rapidocr
            from rapidocr.ch_ppocr_det import TextDetector
            orig = TextDetector.__call__

            def espia(self, img, *a, **kw):
                VISTO.append({"donde": "TextDetector.__call__", "entrada": forma(img),
                              "limit_side_len": getattr(getattr(self, "preprocess_op", None),
                                                        "limit_side_len", None)})
                return orig(self, img, *a, **kw)
            TextDetector.__call__ = espia
            cfg = os.path.join(os.path.dirname(rapidocr.__file__), "config.yaml")
            if os.path.exists(cfg):
                with open(cfg, encoding="utf-8") as fh:
                    out["config_yaml_max_side_len"] = [
                        ln.strip() for ln in fh if "side_len" in ln or "min_height" in ln]
            leer, meta = B.build(config)
            leer(os.path.join(ROOT, "corpus", "pdf", doc + ".pdf"), ppp)
        else:
            raise SystemExit("config desconocida")

    out["llamadas"] = VISTO[:6]
    out["n_llamadas"] = len(VISTO)
    print(json.dumps(out, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
