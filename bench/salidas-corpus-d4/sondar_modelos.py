# -*- coding: utf-8 -*-
"""G1 / sonda de catalogo — que combinaciones (version, tamaño, idioma) admiten de
verdad rapidocr y paddleocr en ESTA maquina. Sin esto, la fase 3 seria adivinar
etiquetas en vez de cruzar variables. No usa GPU: solo lee metadatos.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
out = {}

try:
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
except Exception:
    pass

try:
    import rapidocr
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion
    out["rapidocr_version"] = getattr(rapidocr, "__version__", "?")
    out["LangDet"] = [e.name + "=" + str(e.value) for e in LangDet]
    out["LangRec"] = [e.name + "=" + str(e.value) for e in LangRec]
    out["ModelType"] = [e.name + "=" + str(e.value) for e in ModelType]
    out["OCRVersion"] = [e.name + "=" + str(e.value) for e in OCRVersion]
    out["EngineType"] = [e.name + "=" + str(e.value) for e in EngineType]
    # catalogo real de modelos descargables/instalados
    try:
        from rapidocr.utils import DownloadFile  # noqa
    except Exception:
        pass
    base = os.path.join(os.path.dirname(rapidocr.__file__), "models")
    out["modelos_en_disco"] = sorted(os.listdir(base)) if os.path.isdir(base) else []
    # el fichero yaml que mapea (version, tipo, lang) -> fichero
    for raiz, _d, ficheros in os.walk(os.path.dirname(rapidocr.__file__)):
        for f in ficheros:
            if f.endswith(".yaml") and "model" in f.lower():
                out.setdefault("yaml_modelos", []).append(os.path.join(raiz, f))
except Exception as ex:
    out["rapidocr_error"] = f"{type(ex).__name__}: {ex}"

try:
    from docling.models.stages.ocr.rapid_ocr_model import (
        _RAPIDOCR_MODEL_TYPE, _RAPIDOCR_V4V5_MODEL_TYPE, _resolve_rapidocr)
    out["docling_model_type_v6"] = _RAPIDOCR_MODEL_TYPE
    out["docling_model_type_v4v5"] = _RAPIDOCR_V4V5_MODEL_TYPE
    r = {}
    for lang in ("english", "es", "spanish", "latin", "ch"):
        for be in ("torch", "onnxruntime"):
            try:
                s = _resolve_rapidocr(lang, be)
                r[f"{lang}/{be}"] = {
                    "lang_token": str(s.rapidocr_lang_token),
                    "ppocr": str(getattr(s.ppocr_version, "value", s.ppocr_version)),
                }
            except Exception as ex:
                r[f"{lang}/{be}"] = f"{type(ex).__name__}: {str(ex)[:120]}"
    out["docling_resolucion"] = r
except Exception as ex:
    out["docling_error"] = f"{type(ex).__name__}: {ex}"

print(json.dumps(out, ensure_ascii=False, indent=2))
