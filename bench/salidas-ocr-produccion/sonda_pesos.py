# -*- coding: utf-8 -*-
"""G5 — ¿que fichero de pesos carga RapidOCR de verdad en cada configuracion?

La primera version de la sonda de `ocr_motor.py` devolvio
`ch_PP-OCRv4_det_mobile.onnx` para las TRES tareas y en las DOS configuraciones,
que es imposible: es un valor por defecto del `cfg` que la sonda leia por el
camino equivocado. Aqui se recorre el objeto y se imprime lo que hay, para
elegir el camino bueno en vez de suponerlo.

uso: sonda_pesos.py <cpu|cuda>
env: RO_VER, RO_TIPO
"""
import json
import os
import sys

import torch
os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR  # noqa: E402

gpu = (sys.argv[1] if len(sys.argv) > 1 else "cuda") == "cuda"
ver = os.environ.get("RO_VER", "PP-OCRv6")
tipo = os.environ.get("RO_TIPO", "small")
lrec = os.environ.get("RO_LANGREC", "ch")

lector = RapidOCR(params={
    "EngineConfig.onnxruntime.use_cuda": gpu,
    "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
    "Det.engine_type": EngineType.ONNXRUNTIME,
    "Cls.engine_type": EngineType.ONNXRUNTIME,
    "Rec.engine_type": EngineType.ONNXRUNTIME,
    "Det.lang_type": LangDet.CH, "Rec.lang_type": LangRec(lrec),
    "Det.ocr_version": OCRVersion(ver), "Rec.ocr_version": OCRVersion(ver),
    "Det.model_type": ModelType(tipo), "Rec.model_type": ModelType(tipo),
})

out = {"pedido": {"ver": ver, "tipo": tipo, "lang_rec": lrec, "cuda": gpu}}
for tarea in ("text_det", "text_cls", "text_rec"):
    o = getattr(lector, tarea, None)
    d = {}
    for camino in ("session.model_path", "model_path", "session.session._model_path",
                   "session.model_info", "cfg.model_path", "cfg"):
        v = o
        for a in camino.split("."):
            v = getattr(v, a, None)
            if v is None:
                break
        d[camino] = str(v)[:220] if v is not None else None
    out[tarea] = d
print(json.dumps(out, ensure_ascii=False, indent=2))
