# -*- coding: utf-8 -*-
"""G4 / B19 — SONDA 1: ¿el motor LEE el `pHYs`? Sondeado EN EJECUCION.

Por que existe este fichero
---------------------------
`bench/corpus-d5.md` §4.1 y `bench/psm-y-rasterizador.md` §6.5 dejan escrito que
«PaddleOCR, RapidOCR y EasyOCR reciben arrays de numpy y no deberian ver el `pHYs`».
Eso es una DEDUCCION, y en este proyecto las deducciones se sondean: `CLAUDE.md` §5
—«sondear capacidades en ejecucion, no deducirlas»— y la trampa 8, donde deducir del
codigo de PaddleX dio el resultado CONTRARIO al que mide la sonda.

Ademas la premisa de la deduccion es falsa: en `bench/scripts/ocr_motor.py` y en
`bench/salidas-k-motor/ocr_lote_km.py` los tres motores reciben la RUTA del PNG y lo
abren ellos. Quien decodifica decide si el metadato llega o no.

Que instrumenta, y por que cada cosa
------------------------------------
1. `builtins.open`  -> quien abre el fichero desde Python. PaddleX lee los bytes con
   `open()` y luego `cv2.imdecode` (paddlex/inference/utils/io/readers.py:296-299).
2. `cv2.imread` / `cv2.imdecode` -> el decodificador de OpenCV NO tiene ningun canal
   de salida para el `pHYs`: devuelve un ndarray y nada mas. Si el motor decodifica
   por aqui, el metadato no puede alcanzarle.
3. `PIL.Image.open` -> PIL SI parsea el `pHYs` y lo deja en `img.info['dpi']`
   (unidad=1) o en `img.info['aspect']` (unidad=0). Que este disponible no significa
   que se use: por eso el `.info` del objeto devuelto se sustituye por un DICCIONARIO
   ESPIA que registra toda consulta de clave. Si nadie pregunta por 'dpi', el motor
   no lo lee — y eso es una MEDIDA, no una lectura del codigo.
4. `skimage.io.imread` -> es lo que usa `easyocr.imgproc.loadImage`.

uso: python sonda_lectura_pm.py <easyocr|rapidocr|paddleocr> <cpu|cuda> <png> [png ...]
env: PD_*/RO_* como en ocr_lote_pm.py (aqui se dejan al defecto canonico)
"""
import builtins
import hashlib
import json
import os
import sys
import traceback

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-phys-multi")
JSN = os.path.join(BASE, "json")
os.makedirs(JSN, exist_ok=True)

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
pngs = sys.argv[3:]
gpu = dispositivo == "cuda"

LOG = {"open": [], "cv2_imread": [], "cv2_imdecode": [], "pil_open": [],
       "skimage_imread": [], "info_consultada": [], "info_expuesta": []}


class DictEspia(dict):
    """Registra TODA consulta de clave sobre el `.info` de una imagen de PIL."""
    def __init__(self, base, etiqueta):
        super().__init__(base)
        self._etq = etiqueta

    def __getitem__(self, k):
        LOG["info_consultada"].append([self._etq, "getitem", str(k)])
        return dict.__getitem__(self, k)

    def get(self, k, d=None):
        LOG["info_consultada"].append([self._etq, "get", str(k)])
        return dict.get(self, k, d)

    def __contains__(self, k):
        LOG["info_consultada"].append([self._etq, "contains", str(k)])
        return dict.__contains__(self, k)


# ------------------------------------------------------------------ instrumentacion
_open = builtins.open


def open_espia(f, *a, **kw):
    try:
        s = str(f)
        if s.lower().endswith(".png"):
            LOG["open"].append([os.path.basename(s), str(a[:1])])
    except Exception:
        pass
    return _open(f, *a, **kw)


builtins.open = open_espia

try:
    import cv2
    _imread, _imdecode = cv2.imread, cv2.imdecode

    def imread_espia(p, *a, **kw):
        LOG["cv2_imread"].append([os.path.basename(str(p)), str(a)])
        return _imread(p, *a, **kw)

    def imdecode_espia(b, *a, **kw):
        LOG["cv2_imdecode"].append([len(b), str(a)])
        return _imdecode(b, *a, **kw)

    cv2.imread, cv2.imdecode = imread_espia, imdecode_espia
except Exception as ex:
    LOG["cv2_imread"].append(["NO_CV2", str(ex)])

try:
    from PIL import Image as _PILImage
    _pil_open = _PILImage.open

    def pil_open_espia(fp, *a, **kw):
        im = _pil_open(fp, *a, **kw)
        etq = os.path.basename(str(fp))
        LOG["pil_open"].append([etq])
        try:
            expuesto = {k: str(v) for k, v in dict(im.info).items()}
            LOG["info_expuesta"].append([etq, expuesto])
            im.info = DictEspia(im.info, etq)
        except Exception as ex:
            LOG["info_expuesta"].append([etq, f"ERROR {ex}"])
        return im

    _PILImage.open = pil_open_espia
except Exception as ex:
    LOG["pil_open"].append(["NO_PIL", str(ex)])

try:
    from skimage import io as _skio
    _sk_imread = _skio.imread

    def sk_imread_espia(f, *a, **kw):
        LOG["skimage_imread"].append([os.path.basename(str(f))])
        return _sk_imread(f, *a, **kw)

    _skio.imread = sk_imread_espia
except Exception:
    pass


# ------------------------------------------------------------------ motores
meta = {"motor": motor, "dispositivo": dispositivo}

if motor == "rapidocr":
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    params = {
        "EngineConfig.onnxruntime.use_cuda": gpu,
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": LangDet.CH, "Rec.lang_type": LangRec.CH,
        "Det.ocr_version": OCRVersion("PP-OCRv6"),
        "Rec.ocr_version": OCRVersion("PP-OCRv6"),
        "Det.model_type": ModelType("small"), "Rec.model_type": ModelType("small"),
        "Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225],
        "Det.thresh": 0.2, "Det.box_thresh": 0.45, "Det.unclip_ratio": 1.4,
        "Det.max_candidates": 3000,
    }
    lector = RapidOCR(params=params)

    def leer(x):
        r = lector(x)
        return " ".join(r.txts) if r and r.txts else ""

    td = getattr(lector, "text_det", None)
    meta["det_efectivo"] = {"limit_side_len": getattr(td, "limit_side_len", "?"),
                            "limit_type": getattr(td, "limit_type", "?"),
                            "mean": str(getattr(td, "mean", "?"))}

elif motor == "paddleocr":
    import paddle
    from paddleocr import PaddleOCR
    lector = PaddleOCR(device="gpu:0" if gpu else "cpu",
                       use_doc_orientation_classify=False,
                       use_doc_unwarping=False, use_textline_orientation=True)
    meta["paddle"] = paddle.__version__

    def leer(x):
        out = []
        for p in lector.predict(x):
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            out.extend(d.get("rec_texts", []))
        return " ".join(out)

elif motor == "easyocr":
    import easyocr
    import torch
    lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)
    meta["torch_cuda"] = str(torch.cuda.is_available())

    def leer(x):
        return " ".join(lector.readtext(x, detail=0, paragraph=False))

else:
    raise SystemExit(f"motor desconocido: {motor}")

# --------------------------------------------------- ¿la API expone algun ppp?
import inspect  # noqa: E402


def firma(obj, nombre):
    try:
        s = str(inspect.signature(obj))
    except Exception as ex:
        return f"ERROR {ex}"
    claves = [t for t in ("dpi", "density", "ppi", "resolution", "scale")
              if t in s.lower()]
    return {"firma": s[:600], "terminos_de_resolucion": claves, "nombre": nombre}


if motor == "easyocr":
    meta["api"] = [firma(lector.readtext, "Reader.readtext"),
                   firma(type(lector).__init__, "Reader.__init__")]
elif motor == "rapidocr":
    meta["api"] = [firma(lector.__call__, "RapidOCR.__call__")]
else:
    meta["api"] = [firma(lector.predict, "PaddleOCR.predict"),
                   firma(type(lector).__init__, "PaddleOCR.__init__")]

# ------------------------------------------------------------------ la sonda
# Se limpia el log DESPUES de cargar el modelo: la carga abre ficheros propios.
carga = {k: len(v) for k, v in LOG.items()}
for k in LOG:
    LOG[k] = []

res = {}
for p in pngs:
    nom = os.path.basename(p)
    marca = {k: len(v) for k, v in LOG.items()}
    try:
        t = leer(p)
        err = None
    except Exception as ex:
        t = ""
        err = f"{type(ex).__name__}: {str(ex)[:200]}"
        traceback.print_exc()
    res[nom] = {
        "error": err, "chars": len(t),
        "md5_texto": hashlib.md5(t.encode("utf-8")).hexdigest(),
        "eventos": {k: LOG[k][marca[k]:] for k in LOG},
    }
    print(f"--- {nom} ---")
    print(json.dumps(res[nom]["eventos"], ensure_ascii=False, indent=1)[:2500])
    sys.stdout.flush()

out = {"meta": meta, "eventos_de_carga": carga, "por_png": res}
dst = os.path.join(JSN, f"sonda_lectura_{motor}_{dispositivo}.json")
json.dump(out, _open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps({"meta": meta, "eventos_de_carga": carga}, ensure_ascii=False,
                 indent=2))
print(f"\n-> {dst}")
