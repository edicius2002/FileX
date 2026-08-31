#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B21/B22: reproducible GPU sweep. Run only from Windows Git Bash with harness.sh."""
import argparse, json, os, statistics, subprocess, sys, time

ROOT = r"D:\Work\research\FileX\.ccb\workspaces\worker1"
BASE = os.path.join(ROOT, r"bench\salidas-suelo-ppp")
PDF = os.path.join(ROOT, r"corpus\pdf")
IMG = os.path.join(BASE, "img"); TXT = os.path.join(BASE, "texto"); JS = os.path.join(BASE, "json")
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"
DOCS = [("escaneado_d5a",90),("escaneado_d5c",80),("escaneado_d5",72),("escaneado_d5b",60)] # descending, VRAM rule
R6={"Det.mean":[.485,.456,.406],"Det.std":[.229,.224,.225],"Det.thresh":.2,"Det.box_thresh":.45,"Det.unclip_ratio":1.4,"Det.max_candidates":3000}

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar

def ref():
    # Same source consumed by the d5 generator/evaluator; never parse its .txt copy.
    sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
    from d4_texto import BLOQUES
    return [linea for bloque in BLOQUES.values() for linea in bloque]
REF=ref()

def testigo_mono(n=400000):
    t=time.perf_counter(); z=0
    for i in range(n): z += i*i
    return round((time.perf_counter()-t)*1000,2)

def testigo_proceso(n=5):
    vals=[]
    for _ in range(n):
        t=time.perf_counter()
        try: subprocess.run(["ffprobe","-v","quiet","-version"],stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
        except Exception: return -1.0
        vals.append((time.perf_counter()-t)*1000)
    return round(statistics.median(vals),2)

def run(a, timeout=20, env=None):
    e=dict(os.environ); e.update(env or {})
    return subprocess.run(a, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=e)

def raster(doc, ppp):
    dst=os.path.join(IMG, f"ppp{ppp:03d}__{doc}.png")
    if not os.path.exists(dst):
        p=run([MAGICK,"-density",str(ppp),os.path.join(PDF,doc+".pdf")+"[0]",
               "-units","PixelsPerInch","-density",str(ppp),"-colorspace","sRGB",
               "-alpha","remove","-background","white","-flatten",dst], timeout=60)
        if p.returncode: raise RuntimeError("magick rc=%s: %s"%(p.returncode,p.stderr[:300]))
    ident=run([MAGICK,"identify","-format","%wx%h %x,%y %U",dst])
    return dst,ident.stdout.strip()

def engine(name):
    if name.startswith("tess"):
        psm=name[4:]
        def ocr(path):
            out=os.path.join(BASE,"tmp","tess")
            p=run([TESS,path,out,"-l","spa","--psm",psm],env={"TESSDATA_PREFIX":TESSDATA})
            t=open(out+".txt",encoding="utf-8",errors="replace").read() if p.returncode==0 and os.path.exists(out+".txt") else ""
            return t,p.returncode,p.stderr[:200]
        return ocr,{"motor":"Tesseract 5","psm":int(psm),"entrada":"ruta PNG RGB","dispositivo":"GPU no aplica; CPU"}
    if name.startswith("rapid"):
        import torch; os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__),"lib"))
        from rapidocr import EngineType,LangDet,LangRec,ModelType,OCRVersion,RapidOCR
        ver=OCRVersion("PP-OCRv6") if "v6" in name else OCRVersion("PP-OCRv5")
        typ=ModelType("small") if "v6" in name else ModelType("mobile")
        kw={"EngineConfig.onnxruntime.use_cuda":True,"EngineConfig.onnxruntime.cuda_ep_cfg.device_id":0,
            "Det.engine_type":EngineType.ONNXRUNTIME,"Cls.engine_type":EngineType.ONNXRUNTIME,"Rec.engine_type":EngineType.ONNXRUNTIME,
            "Det.lang_type":LangDet("ch"),"Rec.lang_type":LangRec("ch"),"Det.ocr_version":ver,"Rec.ocr_version":ver,"Det.model_type":typ,"Rec.model_type":typ}
        if name.endswith("r6"): kw.update(R6)
        x=RapidOCR(params=kw)
        def ocr(path):
            try:
                r=x(path); return (" ".join(r.txts) if r and r.txts else ""),0,""
            except Exception as ex: return "",1,type(ex).__name__+": "+str(ex)[:160]
        return ocr,{"motor":"RapidOCR ONNX "+name,"entrada":"ruta PNG RGB","dispositivo":"GPU cuda:0","R6":name.endswith("r6"),"torch_cuda":torch.cuda.is_available()}
    if name=="paddle":
        import paddle
        from paddleocr import PaddleOCR
        x=PaddleOCR(device="gpu:0",lang="en",use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=True)
        def ocr(path):
            try:
                out=[]
                for z in x.predict(path):
                    d=z if isinstance(z,dict) else getattr(z,"json",{}).get("res",{})
                    out.extend(d.get("rec_texts",[]))
                return " ".join(out),0,""
            except Exception as ex: return "",1,type(ex).__name__+": "+str(ex)[:160]
        return ocr,{"motor":"PaddleOCR v6 medium","entrada":"ruta PNG RGB","dispositivo":"GPU gpu:0","paddle":paddle.__version__}
    if name=="easy":
        import easyocr
        x=easyocr.Reader(["es"],gpu=True)
        def ocr(path):
            try: return " ".join(x.readtext(path,detail=0)),0,""
            except Exception as ex: return "",1,type(ex).__name__+": "+str(ex)[:160]
        return ocr,{"motor":"EasyOCR CRAFT + latin_g2","entrada":"ruta PNG RGB","dispositivo":"GPU cuda:0"}
    if name.startswith("docling"):
        import torch
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import AcceleratorDevice,AcceleratorOptions,PdfPipelineOptions,RapidOcrOptions
        from docling.document_converter import DocumentConverter,PdfFormatOption
        norm=name.endswith("r6")
        def ocr(path):
            # Docling consumes PDF; ppp is carried in the input basename and supplied below via state.
            ppp=int(os.path.basename(path)[3:6]); doc=os.path.basename(path).split("__",1)[1][:-4]
            po=PdfPipelineOptions(); po.accelerator_options=AcceleratorOptions(num_threads=8,device=AcceleratorDevice.CUDA)
            po.do_ocr=True; po.do_table_structure=False; oo=RapidOcrOptions(lang=["english"],backend="torch",force_full_page_ocr=True); oo.scale=ppp/72
            if norm: oo.rapidocr_params=dict(R6)
            po.ocr_options=oo
            try:
                x=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=po)})
                return x.convert(os.path.join(PDF,doc+".pdf")).document.export_to_markdown(),0,""
            except Exception as ex: return "",1,type(ex).__name__+": "+str(ex)[:160]
        return ocr,{"motor":"Docling+RapidOCR torch"+(" +R6" if norm else " defecto"),"entrada":"PDF via Docling; scale explicita","dispositivo":"GPU CUDA","R6":norm,"torch_cuda":torch.cuda.is_available()}
    raise ValueError(name)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("config"); ap.add_argument("--ppp",required=True); ap.add_argument("--reps",type=int,default=9); args=ap.parse_args()
    pp=[int(x) for x in args.ppp.split(",")]; os.makedirs(TXT,exist_ok=True); os.makedirs(JS,exist_ok=True)
    ocr,meta=engine(args.config); rows=[]; t0=time.time()
    mono_ini=testigo_mono(); proc_ini=testigo_proceso()
    for doc,native in DOCS:
      # B22's common fine sweep plus precisely this document's native point for B21.
      for ppp in sorted(set(pp + [native])):
        path,geom=raster(doc,ppp); warm,rc,err=ocr(path); times=[]; outputs=[]; rcs=[]; errors=[]
        for _ in range(args.reps):
            a=time.perf_counter(); text,code,why=ocr(path); times.append(round((time.perf_counter()-a)*1000,1)); outputs.append(text); rcs.append(code); errors.append(why)
        text=outputs[-1]; ev=evaluar(text,"acentos",REF)
        fn=f"{args.config}__ppp{ppp:03d}__{doc}.txt"; open(os.path.join(TXT,fn),"w",encoding="utf-8").write(text)
        rows.append({"config":args.config,"doc":doc,"ppp_nativo":native,"ppp":ppp,"factor":round(ppp/native,3),"png":os.path.basename(path),"png_identify":geom,"rc":rcs,"error":errors,"n":args.reps,"ms_mediana":statistics.median(times),"determinista":len(set(outputs))==1,"metrica":ev["metrica"],"cer_pct":ev["cer_pct"],"cer_acentos_pct":ev["cer_acentos_pct"],"cer_ciego_pct":ev["cer_ciego_pct"],"dist_acentos":ev["dist_acentos"],"texto":fn})
        print(json.dumps(rows[-1],ensure_ascii=False),flush=True)
    mono_fin=testigo_mono(); proc_fin=testigo_proceso()
    ruido={"testigo_monohilo_ini_ms":mono_ini,"testigo_monohilo_fin_ms":mono_fin,"deriva":round(mono_fin/max(mono_ini,.01),2),"testigo_proceso_ini_ms":proc_ini,"testigo_proceso_fin_ms":proc_fin,"nivel_vs_reposo":round(max(proc_ini,proc_fin)/26.65,2)}
    out={"meta":meta,"config":args.config,"reps":args.reps,"orden_docs":"d5a,d5c,d5,d5b (mayor a menor)","rasterizador":"ImageMagick -units PixelsPerInch -density N; pHYs=N","ruido":ruido,"etiqueta_ruido":"SUCIA" if ruido["nivel_vs_reposo"]>2 else "limpia","rows":rows,"segundos":round(time.time()-t0,1)}
    json.dump(out,open(os.path.join(JS,args.config+".json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
if __name__=="__main__": main()
