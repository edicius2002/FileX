# -*- coding: utf-8 -*-
"""G1 / fase 3 — resolver la discrepancia PP-OCRv5 / PP-OCRv6.

`bench/ocrmypdf.md` §3.4 dice "RapidOCR corre PP-OCRv5 mobile, PaddleOCR corre PP-OCRv6
medium". `bench/gpu-fase2.md` §5 etiqueta a PaddleOCR como PP-OCRv5. No se resuelve
citando informes: se resuelve mirando los ficheros que hay en disco y el codigo que los
elige. Eso es lo que hace este script; no carga ningun motor ni toca la GPU.

uso: python 50_modelos.py            (con .venv-ai)
     python 50_modelos.py paddle     (con .venv-paddle)
"""
import json
import os
import sys

RAIZ = r"D:\Work\research\FileX"
OUT = os.path.join(RAIZ, r"bench\salidas-ocr-ppp")
modo = sys.argv[1] if len(sys.argv) > 1 else "ai"
res = {}

if modo == "ai":
    # ---------------- 1. ficheros de modelo que trae el paquete rapidocr ----------
    d = os.path.join(RAIZ, r".venv-ai\Lib\site-packages\rapidocr\models")
    res["rapidocr_models_dir"] = d
    res["rapidocr_ficheros"] = sorted(
        (f, os.path.getsize(os.path.join(d, f))) for f in os.listdir(d)
    ) if os.path.isdir(d) else "NO EXISTE"

    # ---------------- 2. que elige docling para cada (backend, lang) -------------
    sys.path.insert(0, os.path.join(RAIZ, r".venv-ai\Lib\site-packages"))
    from docling.models.stages.ocr.rapid_ocr_model import (  # noqa: E402
        _RAPIDOCR_DET_MODEL_LANG, _RAPIDOCR_MODEL_TYPE, _RAPIDOCR_V4V5_MODEL_TYPE,
        _resolve_rapidocr)
    res["docling_constantes"] = {
        "det_model_lang": _RAPIDOCR_DET_MODEL_LANG,
        "model_type_para_v6": _RAPIDOCR_MODEL_TYPE,
        "model_type_para_v4_v5": _RAPIDOCR_V4V5_MODEL_TYPE,
    }
    tabla = {}
    for backend in ("onnxruntime", "torch", "paddle", "openvino"):
        for lang in ("english", "chinese", "latin", "es"):
            try:
                s = _resolve_rapidocr(lang, backend)
                v = str(getattr(s.ppocr_version, "value", s.ppocr_version))
                mt = (_RAPIDOCR_MODEL_TYPE if "v6" in v.lower()
                      else _RAPIDOCR_V4V5_MODEL_TYPE)
                tabla[f"{backend}/{lang}"] = f"{v} {mt} (rec_lang={s.rapidocr_lang_token})"
            except Exception as ex:
                tabla[f"{backend}/{lang}"] = f"ERROR {type(ex).__name__}: {ex}"
    res["docling_resuelve"] = tabla

    # ---------------- 3. que fuerza el banco aislado del proyecto ----------------
    res["banco_aislado_rapidocr"] = (
        "bench/scripts/ocr_motor.py fuerza Det/Rec.ocr_version=PPOCRV5 y "
        "Det/Rec.model_type=MOBILE sobre EngineType.ONNXRUNTIME -> "
        "ch_PP-OCRv5_det_mobile.onnx + ch_PP-OCRv5_rec_mobile.onnx"
    )

elif modo == "paddle":
    # ---------------- 4. modelos que PaddleOCR 3.7.0 descargo de verdad ----------
    cand = [os.path.expanduser(r"~\.paddlex\official_models"),
            os.path.expanduser(r"~/.paddlex/official_models")]
    for c in cand:
        if os.path.isdir(c):
            res["paddlex_cache"] = c
            res["paddlex_modelos"] = sorted(os.listdir(c))
            break
    else:
        res["paddlex_cache"] = "NO ENCONTRADO"
    import importlib.metadata as md
    res["paddleocr"] = md.version("paddleocr")
    try:
        res["paddlepaddle_gpu"] = md.version("paddlepaddle-gpu")
    except Exception:
        pass
    # el mapa lang -> modelo que usa paddleocr 3.x
    try:
        from paddleocr._utils.logging import logger  # noqa: F401
    except Exception:
        pass
    try:
        from paddleocr._models.text_recognition import TextRecognition  # noqa: F401
        res["nota"] = "los nombres reales se registran en json/paddleocr_cuda__cer.json"
    except Exception as ex:
        res["nota"] = f"{type(ex).__name__}: {ex}"

print(json.dumps(res, ensure_ascii=False, indent=2))
p = os.path.join(OUT, f"modelos_{modo}.json")
json.dump(res, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n-> {p}")
