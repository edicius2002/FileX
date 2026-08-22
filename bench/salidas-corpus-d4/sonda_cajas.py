# -*- coding: utf-8 -*-
"""G1 / sonda de DETECCION — ¿cuántas cajas de texto encuentra cada motor?

Es lo que convierte el criterio (b) del encargo ("que ataque al RECONOCEDOR y no
al detector") en una medida y no en un argumento. La pagina tiene 12 renglones.
Si el motor encuentra ~12 cajas y el texto sale mal, el fallo es del reconocedor.
Si encuentra 8, el fallo es del detector.
"""
import json
import os
import sys

RAIZ = r"D:\Work\research\FileX"
IMG = os.path.join(RAIZ, r"bench\salidas-corpus-d4\img_f3")
sys.stdout.reconfigure(encoding="utf-8")
motor = sys.argv[1]
out = {}
DOCS = ["ppp100__escaneado_d3", "ppp200__escaneado_d4c", "ppp200__escaneado_d4"]

if motor == "rapidocr":
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    cfgs = {
        "v5mobile_defecto": {"Det.ocr_version": OCRVersion.PPOCRV5,
                             "Rec.ocr_version": OCRVersion.PPOCRV5,
                             "Det.model_type": ModelType.MOBILE,
                             "Rec.model_type": ModelType.MOBILE},
        "v6small_defecto": {"Det.ocr_version": OCRVersion.PPOCRV6,
                            "Rec.ocr_version": OCRVersion.PPOCRV6,
                            "Det.model_type": ModelType.SMALL,
                            "Rec.model_type": ModelType.SMALL},
        "v6small_normPaddleX": {"Det.ocr_version": OCRVersion.PPOCRV6,
                                "Rec.ocr_version": OCRVersion.PPOCRV6,
                                "Det.model_type": ModelType.SMALL,
                                "Rec.model_type": ModelType.SMALL,
                                "Det.mean": [0.485, 0.456, 0.406],
                                "Det.std": [0.229, 0.224, 0.225],
                                "Det.thresh": 0.2, "Det.box_thresh": 0.45,
                                "Det.unclip_ratio": 1.4,
                                "Det.max_candidates": 3000},
    }
    for nom, extra in cfgs.items():
        p = {"EngineConfig.onnxruntime.use_cuda": True,
             "Det.engine_type": EngineType.ONNXRUNTIME,
             "Cls.engine_type": EngineType.ONNXRUNTIME,
             "Rec.engine_type": EngineType.ONNXRUNTIME,
             "Det.lang_type": LangDet.CH, "Rec.lang_type": LangRec.CH,
             "Global.model_root_dir": os.environ.get("RO_ROOT", "")}
        p.update(extra)
        lec = RapidOCR(params=p)
        for d in DOCS:
            r = lec(os.path.join(IMG, d + ".png"))
            cajas = len(r.boxes) if r is not None and r.boxes is not None else 0
            txts = len(r.txts) if r is not None and r.txts else 0
            out[f"{nom}__{d}"] = {"cajas": cajas, "textos": txts}
            print(f"rapidocr {nom:22s} {d:24s} cajas={cajas:3d} textos={txts:3d}",
                  flush=True)

elif motor == "paddleocr":
    from paddleocr import PaddleOCR
    cfgs = {
        "v6medium": {"text_detection_model_name": "PP-OCRv6_medium_det",
                     "text_recognition_model_name": "PP-OCRv6_medium_rec"},
        "v6small": {"text_detection_model_name": "PP-OCRv6_small_det",
                    "text_recognition_model_name": "PP-OCRv6_small_rec"},
    }
    for nom, extra in cfgs.items():
        lec = PaddleOCR(device="gpu:0", use_doc_orientation_classify=False,
                        use_doc_unwarping=False, use_textline_orientation=True,
                        **extra)
        for d in DOCS:
            res = lec.predict(os.path.join(IMG, d + ".png"))
            cajas = txts = 0
            for pg in res:
                dd = pg if isinstance(pg, dict) else getattr(pg, "json", {}).get("res", {})
                cajas += len(dd.get("dt_polys", []) or [])
                txts += len(dd.get("rec_texts", []) or [])
            out[f"{nom}__{d}"] = {"cajas": cajas, "textos": txts}
            print(f"paddleocr {nom:21s} {d:24s} cajas={cajas:3d} textos={txts:3d}",
                  flush=True)

json.dump(out, open(os.path.join(RAIZ,
                                 rf"bench\salidas-corpus-d4\json\cajas_{motor}.json"),
                    "w", encoding="utf-8"), ensure_ascii=False, indent=2)
