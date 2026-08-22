# -*- coding: utf-8 -*-
"""P1 / B10 — cribado de la correccion de normalizacion sobre TODOS los detectores que
sirve RapidOCR 3.9.2, en UN SOLO proceso (12+ cargas de modelo, un solo arranque de
onnxruntime y una sola reserva de VRAM).

Pregunta que responde: el defecto que `bench/corpus-d4.md` §7.4 midio sobre PP-OCRv6,
¿es de v6 o de todas las versiones? Y ¿hay algun documento donde la correccion EMPEORE?

n=1 por celda: esto es un CRIBADO, igual que el de `corpus-d4.md` §3. Lo que decida
pasa despues por la validacion de n=9 (run_d_b10.sh). El CER de estos motores salio
determinista en las 28 celdas de d4, asi que n=1 no cambia la cifra; lo que n=1 no da
es tiempo fiable, y aqui el tiempo no se usa.

uso: python survey_norm.py <cpu|cuda> <imgdir> <etiqueta_salida>
"""
import glob as _glob
import json
import os
import subprocess
import sys
import time

RAIZ = r"D:\Work\research\FileX"
BASE = os.path.join(RAIZ, r"bench\salidas-ppp-norm")
sys.path.insert(0, BASE)
from ocr_eval_pn import evaluar, ref_de_nombre  # noqa: E402

import torch  # noqa: E402
os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
from rapidocr import (EngineType, LangDet, LangRec, ModelType,  # noqa: E402
                      OCRVersion, RapidOCR)

dispositivo = sys.argv[1] if len(sys.argv) > 1 else "cuda"
IMG = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "img_b10r")
ETQ = sys.argv[3] if len(sys.argv) > 3 else "survey"
gpu = dispositivo == "cuda"
ROOT = os.path.join(BASE, "modelos")

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
POST = {"Det.thresh": 0.2, "Det.box_thresh": 0.45,
        "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000}

# (nombre, ocr_version, model_type_det, lang_det, lang_rec, model_type_rec)
DETECTORES = [
    ("v6_medium", "PP-OCRv6", "medium", "ch", "ch", "medium"),
    ("v6_small", "PP-OCRv6", "small", "ch", "ch", "small"),
    ("v6_tiny", "PP-OCRv6", "tiny", "ch", "ch", "tiny"),
    ("v5_mobile", "PP-OCRv5", "mobile", "ch", "ch", "mobile"),
    ("v5_server", "PP-OCRv5", "server", "ch", "ch", "server"),
    ("v4_mobile", "PP-OCRv4", "mobile", "ch", "ch", "mobile"),
    ("v4_server", "PP-OCRv4", "server", "ch", "ch", "server"),
]

VARIANTES = {
    "defecto": {},
    "R6": dict({"Det.mean": IMAGENET_MEAN, "Det.std": IMAGENET_STD}, **POST),
    "solo_norm": {"Det.mean": IMAGENET_MEAN, "Det.std": IMAGENET_STD},
    "solo_post": dict(POST),
}


def vram():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0])
    except Exception:
        return -1


rutas = sorted(_glob.glob(os.path.join(IMG, "*.png")))
print(json.dumps({"etiqueta": ETQ, "dispositivo": dispositivo, "imgdir": IMG,
                  "n_imagenes": len(rutas), "vram_base_MiB": vram(),
                  "detectores": [d[0] for d in DETECTORES],
                  "variantes": list(VARIANTES)}, ensure_ascii=False), flush=True)

res = {}
for nom, ver, tdet, ldet, lrec, trec in DETECTORES:
    for vnom, extra in VARIANTES.items():
        clave = f"{nom}__{vnom}"
        params = {
            "EngineConfig.onnxruntime.use_cuda": gpu,
            "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Cls.engine_type": EngineType.ONNXRUNTIME,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type": LangDet(ldet), "Rec.lang_type": LangRec(lrec),
            "Det.ocr_version": OCRVersion(ver), "Rec.ocr_version": OCRVersion(ver),
            "Det.model_type": ModelType(tdet), "Rec.model_type": ModelType(trec),
            "Global.model_root_dir": ROOT,
        }
        params.update(extra)
        t0 = time.time()
        try:
            lector = RapidOCR(params=params)
        except Exception as ex:
            res[clave] = {"error": f"{type(ex).__name__}: {str(ex)[:200]}"}
            print(f"{clave:26s} ERROR {type(ex).__name__}: {str(ex)[:90]}", flush=True)
            continue
        carga = round(time.time() - t0, 2)
        fila = {"carga_s": carga, "docs": {}}
        for ruta in rutas:
            n = os.path.splitext(os.path.basename(ruta))[0]
            ref = ref_de_nombre(n)
            try:
                t = time.time()
                r = lector(ruta)
                ms = round((time.time() - t) * 1000, 1)
                texto = " ".join(r.txts) if r and r.txts else ""
                nc = 0 if (r is None or r.boxes is None) else len(r.boxes)
            except Exception as ex:
                fila["docs"][n] = {"error": f"{type(ex).__name__}: {str(ex)[:150]}"}
                continue
            ev = evaluar(texto, ref)
            fila["docs"][n] = {"ref": ref, "cer_acentos_pct": ev["cer_acentos_pct"],
                               "cer_ascii_pct": ev["cer_ascii_pct"],
                               "cajas": nc, "chars": ev["chars_salida"], "ms": ms}
        res[clave] = fila
        linea = "  ".join(
            f"{k.split('__')[-1][:16]}={v.get('cer_acentos_pct', 'ERR')}"
            for k, v in fila["docs"].items())
        print(f"{clave:26s} {linea}", flush=True)
        del lector

json.dump(res, open(os.path.join(BASE, "json", f"{ETQ}.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps({"evento": "fin", "vram_MiB": vram()}), flush=True)
