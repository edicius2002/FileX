# -*- coding: utf-8 -*-
"""G1 / sonda de catalogo de PaddleOCR 3.7.0 — que modelo elige cada `lang` y que
nombres de modelo admite explicitamente. Es la base de la fase 3: sin esto, "idioma"
y "tamaño de modelo" estan confundidos, porque el idioma PUEDE estar eligiendo el
tamaño por detras.
No carga pesos: solo resuelve nombres.
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
out = {}

import paddleocr  # noqa: E402
out["paddleocr"] = getattr(paddleocr, "__version__", "?")

try:
    from paddleocr._utils.logging import get_logger  # noqa
except Exception:
    pass

# --- que resuelve cada idioma ---
try:
    from paddleocr._models.text_recognition import TextRecognition  # noqa
except Exception:
    pass

res = {}
for lang in ("es", "en", "ch", "latin", "fr", "pt"):
    try:
        from paddleocr import PaddleOCR
        o = PaddleOCR(lang=lang, device="cpu",
                      use_doc_orientation_classify=False,
                      use_doc_unwarping=False,
                      use_textline_orientation=False,
                      lazy_init=True) if False else None
    except Exception:
        o = None
    res[lang] = None
out["nota"] = "la instanciacion real se hace abajo por lang, con device=cpu"

# resolucion de nombres sin construir la tuberia entera
try:
    from paddleocr._pipelines.ocr import PaddleOCR as _P
    import inspect
    src = inspect.getsource(_P)
    out["tiene__get_ocr_model_names"] = "_get_ocr_model_names" in src
except Exception as ex:
    out["src_error"] = f"{type(ex).__name__}: {ex}"

# catalogo oficial de nombres de modelo que conoce PaddleX
try:
    from paddlex.utils.official_models import OFFICIAL_MODELS
    nombres = sorted(OFFICIAL_MODELS.keys())
    out["paddlex_modelos_ocr"] = [n for n in nombres
                                  if "OCR" in n or "ocr" in n or "rec" in n or "det" in n]
except Exception as ex:
    out["paddlex_error"] = f"{type(ex).__name__}: {str(ex)[:200]}"

print(json.dumps(out, ensure_ascii=False, indent=2))
