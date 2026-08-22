# -*- coding: utf-8 -*-
"""P1 / B10 — DECLARADO frente a APLICADO, con fichero y linea.

Esto no mide CER: documenta el mecanismo con la precision que hace falta para
reportarlo aguas arriba. Lee (a) lo que el fichero de configuracion de RapidOCR
declara, (b) lo que el `inference.yml` que Baidu distribuye CON cada modelo declara,
y (c) lo que el objeto `TextDetector` ya construido tiene REALMENTE en memoria.

Corre en CPU y no toca la GPU: no necesita el lock.

uso: python probe_norm.py
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-ppp-norm")
ROOT = os.path.join(BASE, "modelos")
PADDLEX = os.path.expanduser(r"~\.paddlex\official_models")

out = {}

# ---------------------------------------------------------------- (a) RapidOCR
import rapidocr  # noqa: E402
RO = os.path.dirname(rapidocr.__file__)
cfg = os.path.join(RO, "config.yaml")
lineas = open(cfg, encoding="utf-8").read().splitlines()
det_ini = next(i for i, l in enumerate(lineas) if l.startswith("Det:"))
det_fin = next(i for i in range(det_ini + 1, len(lineas))
               if lineas[i] and not lineas[i][0].isspace())
bloque = {}
for i in range(det_ini, det_fin):
    m = re.match(r"\s+(\w+):\s*(.+?)\s*$", lineas[i])
    if m:
        bloque[m.group(1)] = {"valor": m.group(2), "linea": i + 1}
out["rapidocr_config_yaml"] = {"fichero": cfg.replace(RAIZ, "<RAIZ>"),
                               "Det": bloque}
utils = os.path.join(RO, "ch_ppocr_det", "utils.py")
u = open(utils, encoding="utf-8").read().splitlines()
out["rapidocr_donde_se_aplica"] = [
    {"fichero": "rapidocr/ch_ppocr_det/utils.py", "linea": i + 1, "codigo": l.strip()}
    for i, l in enumerate(u) if "self.mean" in l or "self.std" in l]
main = os.path.join(RO, "ch_ppocr_det", "main.py")
m = open(main, encoding="utf-8").read().splitlines()
out["rapidocr_donde_se_lee"] = [
    {"fichero": "rapidocr/ch_ppocr_det/main.py", "linea": i + 1, "codigo": l.strip()}
    for i, l in enumerate(m) if 'cfg.get("mean")' in l or 'cfg.get("std")' in l
    or "DetPreProcess(" in l]

# ---------------------------------------------------------------- (b) los modelos
mods = {}
if os.path.isdir(PADDLEX):
    for d in sorted(os.listdir(PADDLEX)):
        f = os.path.join(PADDLEX, d, "inference.yml")
        if not os.path.exists(f):
            continue
        txt = open(f, encoding="utf-8").read()
        mm = re.search(r"NormalizeImage:\s*\n\s*mean:\s*\n((?:\s*-\s*[\d.]+\n)+)"
                       r"(?:\s*order:.*\n)?(?:\s*scale:.*\n)?(?:\s*std:\s*\n"
                       r"((?:\s*-\s*[\d.]+\n)+))?", txt)
        if mm:
            mean = [float(x) for x in re.findall(r"[\d.]+", mm.group(1))]
            std = ([float(x) for x in re.findall(r"[\d.]+", mm.group(2))]
                   if mm.group(2) else None)
            if std is None:
                ms = re.search(r"std:\s*\n((?:\s*-\s*[\d.]+\n)+)", txt)
                std = [float(x) for x in re.findall(r"[\d.]+", ms.group(1))] if ms else None
            mods[d] = {"mean": mean, "std": std,
                       "es_imagenet": mean[:3] == [0.485, 0.456, 0.406]}
out["inference_yml_de_los_modelos"] = mods

# ---------------------------------------------------------------- (c) en memoria
import torch  # noqa: E402
os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
from rapidocr import (EngineType, LangDet, LangRec, ModelType,  # noqa: E402
                      OCRVersion, RapidOCR)

R6 = {"Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225],
      "Det.thresh": 0.2, "Det.box_thresh": 0.45,
      "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000}

mem = {}
for nom, ver, tipo in (("v6_small", "PP-OCRv6", "small"),
                       ("v5_mobile", "PP-OCRv5", "mobile"),
                       ("v4_mobile", "PP-OCRv4", "mobile")):
    for vnom, extra in (("defecto", {}), ("R6", R6)):
        p = {"EngineConfig.onnxruntime.use_cuda": False,
             "Det.engine_type": EngineType.ONNXRUNTIME,
             "Cls.engine_type": EngineType.ONNXRUNTIME,
             "Rec.engine_type": EngineType.ONNXRUNTIME,
             "Det.lang_type": LangDet("ch"), "Rec.lang_type": LangRec("ch"),
             "Det.ocr_version": OCRVersion(ver), "Rec.ocr_version": OCRVersion(ver),
             "Det.model_type": ModelType(tipo), "Rec.model_type": ModelType(tipo),
             "Global.model_root_dir": ROOT}
        p.update(extra)
        try:
            r = RapidOCR(params=p)
        except Exception as ex:
            mem[f"{nom}__{vnom}"] = {"error": f"{type(ex).__name__}: {ex}"}
            continue
        td = r.text_det
        pp = td.postprocess_op
        mem[f"{nom}__{vnom}"] = {
            "mean": list(td.mean) if td.mean is not None else None,
            "std": list(td.std) if td.std is not None else None,
            "limit_side_len": td.limit_side_len, "limit_type": td.limit_type,
            "thresh": pp.thresh, "box_thresh": pp.box_thresh,
            "unclip_ratio": pp.unclip_ratio, "max_candidates": pp.max_candidates,
        }
        del r
out["en_memoria"] = mem

json.dump(out, open(os.path.join(BASE, "json", "probe_norm.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
