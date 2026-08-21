# -*- coding: utf-8 -*-
"""FASE 2-B/C: banco de motores de OCR *sin* docling, sobre las paginas ya rasterizadas.

Aisla el coste del OCR puro (deteccion + reconocimiento), sin la etapa de maquetacion
de docling, para poder comparar motores entre si y CPU contra GPU.

uso: ocr_motor.py <easyocr|rapidocr|paddleocr> <cpu|cuda> [etiqueta]
env: REPS (por defecto 9)
"""
import json
import os
import statistics
import subprocess
import sys
import time

IMG = r"D:\Work\research\FileX\bench\salidas-fase2\img"
OUT = r"D:\Work\research\FileX\bench\salidas-fase2"
DOCS = ["patologico_escaneado", "escaneado_d1", "escaneado_d2", "escaneado_d3"]
REPS = int(os.environ.get("REPS", "9"))

motor = sys.argv[1]
dispositivo = sys.argv[2] if len(sys.argv) > 2 else "cuda"
etiqueta = sys.argv[3] if len(sys.argv) > 3 else f"motor_{motor}_{dispositivo}"
gpu = dispositivo == "cuda"


def vram():
    try:
        return int(subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True).stdout.strip().splitlines()[0])
    except Exception:
        return -1


base_vram = vram()
meta = {"etiqueta": etiqueta, "motor": motor, "dispositivo": dispositivo,
        "vram_base_MiB": base_vram}

# ---------------------------------------------------------------- carga del motor
t0 = time.time()

if motor == "easyocr":
    import torch
    import easyocr
    lector = easyocr.Reader(["es", "en"], gpu=gpu, verbose=False)
    meta["torch"] = torch.__version__
    meta["torch_cuda"] = torch.cuda.is_available()

    def leer(ruta):
        r = lector.readtext(ruta, detail=0, paragraph=False)
        return " ".join(r)

elif motor == "rapidocr":
    import torch
    os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
    from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
    params = {
        "EngineConfig.onnxruntime.use_cuda": gpu,
        "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
        "Det.engine_type": EngineType.ONNXRUNTIME,
        "Cls.engine_type": EngineType.ONNXRUNTIME,
        "Rec.engine_type": EngineType.ONNXRUNTIME,
        "Det.lang_type": LangDet.CH,
        "Rec.lang_type": LangRec.CH,
        "Det.ocr_version": OCRVersion.PPOCRV5,
        "Rec.ocr_version": OCRVersion.PPOCRV5,
        "Det.model_type": ModelType.MOBILE,
        "Rec.model_type": ModelType.MOBILE,
    }
    lector = RapidOCR(params=params)

    def leer(ruta):
        r = lector(ruta)
        return " ".join(r.txts) if r and r.txts else ""

elif motor == "paddleocr":
    import paddle
    from paddleocr import PaddleOCR
    meta["paddle"] = paddle.__version__
    meta["paddle_compiled_cuda"] = paddle.device.is_compiled_with_cuda()
    meta["paddle_device_count"] = paddle.device.cuda.device_count()
    lector = PaddleOCR(lang="es", device="gpu:0" if gpu else "cpu",
                       use_doc_orientation_classify=False,
                       use_doc_unwarping=False,
                       use_textline_orientation=True)

    def leer(ruta):
        r = lector.predict(ruta)
        out = []
        for p in r:
            d = p if isinstance(p, dict) else getattr(p, "json", {}).get("res", {})
            out.extend(d.get("rec_texts", []))
        return " ".join(out)

else:
    raise SystemExit(f"motor desconocido: {motor}")

meta["carga_s"] = round(time.time() - t0, 2)
meta["vram_tras_carga_MiB"] = vram()
print(json.dumps(meta, ensure_ascii=False))
sys.stdout.flush()

# ---------------------------------------------------------------- medicion
pico = meta["vram_tras_carga_MiB"]
res = []
for nombre in DOCS:
    ruta = os.path.join(IMG, nombre + ".png")
    if not os.path.exists(ruta):
        continue
    try:
        texto = leer(ruta)          # calentamiento, fuera de la medicion
    except Exception as ex:
        e = {"archivo": nombre, "ok": False, "error": f"{type(ex).__name__}: {ex}"}
        res.append(e)
        print(json.dumps(e, ensure_ascii=False))
        continue
    ts = []
    for _ in range(REPS):
        t = time.time()
        texto = leer(ruta)
        ts.append((time.time() - t) * 1000)
        v = vram()
        if v > pico:
            pico = v
    dst = os.path.join(OUT, f"{etiqueta}__{nombre}.txt")
    open(dst, "w", encoding="utf-8").write(texto)
    s = sorted(ts)
    e = {"archivo": nombre, "ok": True, "ms_mediana": round(statistics.median(s), 1),
         "ms_min": round(s[0], 1), "ms_max": round(s[-1], 1), "n": len(s),
         "chars": len(texto), "salida": dst}
    res.append(e)
    print(json.dumps(e, ensure_ascii=False))
    sys.stdout.flush()

fin = {"evento": "fin", "vram_pico_MiB": pico, "vram_base_MiB": base_vram,
       "coste_propio_MiB": pico - base_vram}
print(json.dumps(fin, ensure_ascii=False))
json.dump({"meta": meta, "docs": res, "fin": fin},
          open(os.path.join(OUT, f"{etiqueta}__resumen.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
