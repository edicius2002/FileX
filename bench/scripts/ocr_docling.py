# -*- coding: utf-8 -*-
"""FASE 2-A: docling con distintos motores/backends de OCR sobre el corpus escaneado.

uso: ocr_docling.py <cpu|cuda> <rapidocr|easyocr|tesseract> [onnxruntime|torch|paddle|openvino] [etiqueta]
"""
import json
import os
import sys
import time

# En Windows onnxruntime-gpu necesita encontrar las DLL de CUDA/cuDNN. Las que trae
# torch 2.6.0+cu124 sirven, pero hay que anadir su carpeta a la busqueda de DLL antes
# de importar onnxruntime. Importar torch primero es lo que lo consigue.
try:
    import torch
    _tl = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.isdir(_tl):
        os.add_dll_directory(_tl)
except Exception:
    torch = None

OUT = r"D:\Work\research\FileX\bench\salidas-fase2"
C = r"D:\Work\research\FileX\corpus\pdf"
os.makedirs(OUT, exist_ok=True)

dispositivo = sys.argv[1] if len(sys.argv) > 1 else "cuda"
motor = sys.argv[2] if len(sys.argv) > 2 else "rapidocr"
backend = sys.argv[3] if len(sys.argv) > 3 else "onnxruntime"
etiqueta = sys.argv[4] if len(sys.argv) > 4 else f"docling_{motor}_{backend}_{dispositivo}"

DOCS = ["patologico_escaneado.pdf", "escaneado_d1.pdf", "escaneado_d2.pdf", "escaneado_d3.pdf"]

meta = {"etiqueta": etiqueta, "dispositivo": dispositivo, "motor": motor, "backend": backend}
try:
    import onnxruntime as ort
    meta["onnxruntime"] = ort.__version__
    meta["ort_providers"] = ort.get_available_providers()
except Exception as ex:
    meta["onnxruntime"] = f"ERROR: {ex}"
if torch is not None:
    meta["torch"] = torch.__version__
    meta["torch_cuda"] = torch.cuda.is_available()
print(json.dumps(meta, ensure_ascii=False))
sys.stdout.flush()

# Sonda: registra con que ExecutionProvider acaba cada sesion de onnxruntime.
# Sin esto no hay forma de saber si la CUDA EP se creo de verdad o cayo a CPU.
if os.environ.get("SONDA_ORT") == "1":
    try:
        import onnxruntime as _ort
        _orig = _ort.InferenceSession

        class _Sonda(_orig):  # type: ignore[misc,valid-type]
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                print(json.dumps({"evento": "sesion_ort",
                                  "modelo": os.path.basename(str(a[0]))[:60],
                                  "providers": self.get_providers()}))
                sys.stdout.flush()

        _ort.InferenceSession = _Sonda
    except Exception as ex:
        print(json.dumps({"evento": "sonda_ort_fallo", "error": str(ex)}))

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    EasyOcrOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

dev = AcceleratorDevice.CUDA if dispositivo == "cuda" else AcceleratorDevice.CPU
po = PdfPipelineOptions()
po.accelerator_options = AcceleratorOptions(num_threads=8, device=dev)
po.do_ocr = os.environ.get("SIN_OCR") != "1"
po.do_table_structure = True

if motor == "rapidocr":
    # docling 2.120.3 rellena "Det/Cls/Rec.use_cuda", pero el motor onnxruntime de
    # rapidocr lee "EngineConfig.onnxruntime.use_cuda". Sin este override las sesiones
    # ONNX salen en CPUExecutionProvider aunque la CUDA EP este disponible.
    rp = {}
    if os.environ.get("FORZAR_ORT_CUDA") == "1":
        rp["EngineConfig.onnxruntime.use_cuda"] = True
        rp["EngineConfig.onnxruntime.cuda_ep_cfg.device_id"] = 0
    meta["rapidocr_params"] = {k: str(v) for k, v in rp.items()}
    po.ocr_options = RapidOcrOptions(lang=["english"], backend=backend,
                                     force_full_page_ocr=True,
                                     rapidocr_params=rp)
elif motor == "easyocr":
    po.ocr_options = EasyOcrOptions(lang=["es", "en"], use_gpu=(dispositivo == "cuda"),
                                    force_full_page_ocr=True)
elif motor == "tesseract":
    po.ocr_options = TesseractOcrOptions(lang=["spa", "eng"], force_full_page_ocr=True)

t0 = time.time()
conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po)})
print(json.dumps({"evento": "constructor", "segundos": round(time.time() - t0, 2)}))
sys.stdout.flush()

if torch is not None and torch.cuda.is_available():
    torch.cuda.reset_peak_memory_stats()

REPS = int(os.environ.get("REPS", "1"))
if len(sys.argv) > 5:
    DOCS = sys.argv[5].split(",")

res = []
for nombre in DOCS:
    ruta = os.path.join(C, nombre)
    if not os.path.exists(ruta):
        continue
    tiempos = []
    e = None
    for i in range(REPS):
        t0 = time.time()
        try:
            r = conv.convert(ruta)
            md = r.document.export_to_markdown()
            tiempos.append(time.time() - t0)
            dst = os.path.join(OUT, f"{etiqueta}__{nombre}.txt")
            open(dst, "w", encoding="utf-8").write(md)
            e = {"evento": "convert", "archivo": nombre, "chars": len(md),
                 "salida": dst, "ok": True}
        except Exception as ex:
            e = {"evento": "convert", "archivo": nombre, "ok": False,
                 "error": f"{type(ex).__name__}: {ex}"}
            break
    if tiempos:
        s = sorted(tiempos)
        e["segundos"] = round(s[len(s) // 2], 2)
        e["n"] = len(s)
        e["rango"] = [round(s[0], 2), round(s[-1], 2)]
    res.append(e)
    print(json.dumps(e, ensure_ascii=False))
    sys.stdout.flush()

fin = {"evento": "fin", "etiqueta": etiqueta}
if torch is not None and torch.cuda.is_available():
    fin["torch_max_alloc_MiB"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
    fin["torch_max_reserved_MiB"] = round(torch.cuda.max_memory_reserved() / 2**20, 1)
print(json.dumps(fin, ensure_ascii=False))
json.dump({"meta": meta, "docs": res, "fin": fin},
          open(os.path.join(OUT, f"{etiqueta}__resumen.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
