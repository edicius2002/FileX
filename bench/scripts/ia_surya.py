# -*- coding: utf-8 -*-
"""FASE 1-B.3: surya 0.22.1 OCR sobre el PDF escaneado (sin capa de texto).
API de esta version: SuryaInferenceManager + RecognitionPredictor(full_page=True).
"""
import sys, time, json, os
OUT = r"D:\Work\research\FileX\bench\salidas-fase1\ia"
C   = r"D:\Work\research\FileX\corpus\pdf"
os.makedirs(OUT, exist_ok=True)
modo = sys.argv[1] if len(sys.argv) > 1 else "todo"

import torch
from surya.settings import settings
print(json.dumps({"evento":"torch","cuda":torch.cuda.is_available(),
                  "cc":list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
                  "bf16_soportado": torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
                  "surya_device": settings.TORCH_DEVICE_MODEL,
                  "surya_MODEL_DTYPE": str(settings.MODEL_DTYPE),
                  "surya_MODEL_DTYPE_BFLOAT": str(settings.MODEL_DTYPE_BFLOAT),
                  "surya_VLLM_DTYPE": settings.VLLM_DTYPE}))
sys.stdout.flush()

from surya.inference import SuryaInferenceManager
from surya.recognition import RecognitionPredictor
import pypdfium2

t0 = time.time()
manager = SuryaInferenceManager()
rec = RecognitionPredictor(manager)
t_carga = time.time() - t0
print(json.dumps({"evento":"carga","segundos":round(t_carga,2)})); sys.stdout.flush()

if modo == "solo_carga":
    sys.exit(0)
if modo == "residente":
    print("RESIDENTE_LISTO"); sys.stdout.flush()
    time.sleep(float(os.environ.get("RESIDENTE_SEG","60"))); sys.exit(0)

def paginas(ruta, dpi=192):
    pdf = pypdfium2.PdfDocument(ruta)
    return [pdf[i].render(scale=dpi/72).to_pil().convert("RGB") for i in range(len(pdf))]

res = []
for nombre in ["patologico_escaneado.pdf", "tipico_texto.pdf"]:
    ruta = os.path.join(C, nombre)
    imgs = paginas(ruta)
    t0 = time.time()
    try:
        pages = rec(imgs, full_page=True)
        dt = time.time() - t0
        trozos = []
        for p in pages:
            d = p.model_dump()
            for b in d.get("blocks", []) or []:
                t = b.get("text") or b.get("html") or ""
                if t: trozos.append(str(t))
            if not d.get("blocks"):
                trozos.append(json.dumps(d, ensure_ascii=False)[:2000])
        texto = "\n".join(trozos)
        dst = os.path.join(OUT, f"surya_{nombre}.txt")
        open(dst, "w", encoding="utf-8").write(texto)
        e = {"evento":"ocr","archivo":nombre,"paginas":len(imgs),"segundos":round(dt,2),
             "bloques":len(trozos),"chars":len(texto),"salida":dst,"ok":True}
    except Exception as ex:
        import traceback; traceback.print_exc()
        e = {"evento":"ocr","archivo":nombre,"ok":False,"error":f"{type(ex).__name__}: {ex}"}
    res.append(e); print(json.dumps(e, ensure_ascii=False)); sys.stdout.flush()

json.dump({"carga_s":round(t_carga,2),"tareas":res},
          open(os.path.join(OUT,"surya_resumen.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=2)
