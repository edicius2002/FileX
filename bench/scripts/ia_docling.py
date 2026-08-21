# -*- coding: utf-8 -*-
"""FASE 1-B.2: docling con AcceleratorDevice.CUDA sobre los PDF del corpus."""
import sys, time, json, os

OUT = r"D:\Work\research\FileX\bench\salidas-fase1\ia"
C   = r"D:\Work\research\FileX\corpus\pdf"
os.makedirs(OUT, exist_ok=True)
dispositivo = sys.argv[1] if len(sys.argv) > 1 else "cuda"

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
from docling.document_converter import DocumentConverter, PdfFormatOption

dev = AcceleratorDevice.CUDA if dispositivo == "cuda" else AcceleratorDevice.CPU
po = PdfPipelineOptions()
po.accelerator_options = AcceleratorOptions(num_threads=8, device=dev)
po.do_ocr = True
po.do_table_structure = True

t0 = time.time()
conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po)})
print(json.dumps({"evento":"constructor","dispositivo":dispositivo,"segundos":round(time.time()-t0,2)})); sys.stdout.flush()

if len(sys.argv) > 2 and sys.argv[2] == "residente":
    # fuerza la carga real de los modelos en VRAM antes de anunciar que esta listo
    conv.convert(os.path.join(C, "tipico_texto.pdf"))
    conv.convert(os.path.join(C, "patologico_escaneado.pdf"))
    print("RESIDENTE_LISTO"); sys.stdout.flush()
    time.sleep(float(os.environ.get("RESIDENTE_SEG","60")))
    sys.exit(0)

res = []
for nombre in ["tipico_texto.pdf", "patologico_escaneado.pdf", "trivial.pdf"]:
    ruta = os.path.join(C, nombre)
    t0 = time.time()
    try:
        r = conv.convert(ruta)
        md = r.document.export_to_markdown()
        dt = time.time() - t0
        dst = os.path.join(OUT, f"docling_{dispositivo}_{nombre}.md")
        open(dst, "w", encoding="utf-8").write(md)
        e = {"evento":"convert","archivo":nombre,"segundos":round(dt,2),"chars":len(md),"salida":dst,"ok":True}
    except Exception as ex:
        e = {"evento":"convert","archivo":nombre,"ok":False,"error":f"{type(ex).__name__}: {ex}"}
    res.append(e); print(json.dumps(e, ensure_ascii=False)); sys.stdout.flush()

json.dump(res, open(os.path.join(OUT,f"docling_{dispositivo}_resumen.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
