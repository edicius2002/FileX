#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B23 (resto, ronda 5) -- las dos configuraciones de Docling que faltaban de
la rejilla original de 9: Docling defecto y Docling+R6.

MISMA rejilla (4 documentos d5 x 7 factores) y MISMO evaluador que
b23_k_d5.py, para que el arrepentimiento sea comparable celda a celda con las
5 configuraciones ya medidas y con las dos de b23_resto_rapidocr.py.

Docling NO consume un PNG pre-rasterizado: rasteriza el PDF el mismo con
`RapidOcrOptions.scale`, igual que bench/salidas-k-motor/docling_lote_km.py
(backend "torch", `lang=["english"]" -- el mismo defecto historico de aquel
script, para que el `k` sea comparable con las filas "Docling..." de
`bench/k-por-motor.md`, que se midieron con ese mismo lang). R6 entra por
`RapidOcrOptions.rapidocr_params`, el punto de extension publico de docling
(pipeline_options.py) -- no hace falta parchear el paquete.

ROOT se calcula desde la ubicacion del propio script (ver
b23_resto_rapidocr.py para el porque).

uso: python b23_resto_docling.py <docling-def|docling-r6> [--reps N]
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, "bench", "salidas-k-oem-acantilados")
PDF = os.path.join(ROOT, "corpus", "pdf")
JS = os.path.join(BASE, "json")
TXT = os.path.join(BASE, "texto")
os.makedirs(JS, exist_ok=True)
os.makedirs(TXT, exist_ok=True)
DOCS = [("escaneado_d5a", 90), ("escaneado_d5c", 80), ("escaneado_d5", 72), ("escaneado_d5b", 60)]
FACTORES = [0.75, 0.875, 1.00, 1.125, 1.25, 1.40, 1.60]

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
from d4_texto import BLOQUES  # noqa: E402
REF = [linea for bloque in BLOQUES.values() for linea in bloque]
sys.path.insert(0, ROOT)
from filex import gpu  # noqa: E402

# bench/corpus-d4.md §7.4/§10 -- normalizacion ImageNet + post-proceso de
# PaddleX que declara el inference.yml de PP-OCRv6 small.
R6 = {"Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225], "Det.thresh": 0.2,
      "Det.box_thresh": 0.45, "Det.unclip_ratio": 1.4, "Det.max_candidates": 3000}

# El asignador no devuelve VRAM (trampa 67): docling es el motor "caro" del
# racimo (hasta 9646 MiB de coste propio en un solo folio, k-por-motor.md), y
# aqui un mismo proceso construye 28 `DocumentConverter` seguidos. Guardia
# ANTES de cada celda, igual que docling_lote_km.py -- sin ella, una celda
# puede reventar en silencio contra el techo de la tarjeta.
VRAM_TOPE_MIB = int(os.environ.get("VRAM_TOPE_MIB", "11500"))


def vram_usada_mib():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                             "--format=csv,noheader,nounits"],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=20)
        return int(r.stdout.decode("utf-8", "replace").strip().splitlines()[0])
    except Exception:
        return -1


def testigo_mono(n=400000):
    t = time.perf_counter()
    z = 0
    for i in range(n):
        z += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope_s=20.0):
    vals = []
    t_ini = time.perf_counter()
    for _ in range(n):
        restante = tope_s - (time.perf_counter() - t_ini)
        if restante <= 0.5:
            return round(tope_s * 1000, 2)
        t = time.perf_counter()
        try:
            subprocess.run(["ffprobe", "-v", "quiet", "-version"], stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=restante)
        except Exception:
            return round(tope_s * 1000, 2)
        vals.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(vals), 2) if vals else round(tope_s * 1000, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", choices=["docling-def", "docling-r6"])
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()
    norm = args.config == "docling-r6"

    import torch
    tl = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.isdir(tl):
        os.add_dll_directory(tl)

    lock = gpu.Lock("B23resto-" + args.config)
    with lock as lk:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            AcceleratorDevice, AcceleratorOptions, PdfPipelineOptions, RapidOcrOptions)
        from docling.document_converter import DocumentConverter, PdfFormatOption

        meta = {"motor": ("Docling+RapidOCR torch + R6" if norm
                          else "Docling+RapidOCR torch (defecto)"),
                "dispositivo": "GPU cuda", "gpu": True, "lock_aviso": lk.aviso,
                "backend": "torch", "lang": "english", "R6": norm}
        mono_ini = testigo_mono()
        proc_ini = testigo_proceso()
        rows = []
        t0 = time.time()
        for doc, native in DOCS:
            ruta = os.path.join(PDF, doc + ".pdf")
            for f in FACTORES:
                ppp = native * f
                v_ahora = vram_usada_mib()
                if v_ahora > VRAM_TOPE_MIB:
                    nom = f"k{int(round(f * 1000)):04d}__{doc}"
                    row = {"config": args.config, "doc": doc, "ppp_nativo": native,
                           "factor": f, "ppp": round(ppp, 1), "omitido_vram": v_ahora,
                           "tope": VRAM_TOPE_MIB}
                    rows.append(row)
                    print(json.dumps(row, ensure_ascii=False), flush=True)
                    continue
                po = PdfPipelineOptions()
                po.accelerator_options = AcceleratorOptions(
                    num_threads=8, device=AcceleratorDevice.CUDA)
                po.do_ocr = True
                po.do_table_structure = False
                oo = RapidOcrOptions(lang=["english"], backend="torch", force_full_page_ocr=True)
                oo.scale = ppp / 72.0
                if norm:
                    oo.rapidocr_params = dict(R6)
                po.ocr_options = oo
                conv = DocumentConverter(
                    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po)})
                textos, rcs = [], []
                for _ in range(args.reps):
                    try:
                        texto = conv.convert(ruta).document.export_to_markdown()
                        rc = 0
                    except Exception as ex:
                        texto = ""
                        rc = f"{type(ex).__name__}: {str(ex)[:150]}"
                    textos.append(texto)
                    rcs.append(rc)
                texto = textos[-1]
                ev = evaluar(texto, "acentos", REF)
                nom = f"k{int(round(f * 1000)):04d}__{doc}"
                open(os.path.join(TXT, f"{args.config}__{nom}.txt"), "w",
                     encoding="utf-8").write(texto)
                row = {"config": args.config, "doc": doc, "ppp_nativo": native, "factor": f,
                       "ppp": round(ppp, 1), "n": args.reps, "determinista": len(set(textos)) == 1,
                       "cer_pct": ev["cer_pct"], "rc_reps": rcs}
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
        mono_fin = testigo_mono()
        proc_fin = testigo_proceso()
    ruido = {"mono_ini": mono_ini, "mono_fin": mono_fin,
             "deriva": round(mono_fin / max(mono_ini, .01), 2),
             "proc_ini": proc_ini, "proc_fin": proc_fin,
             "nivel": round(max(proc_ini, proc_fin) / 26.65, 2)}
    out = {"meta": meta, "config": args.config, "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(os.path.join(JS, "b23resto_" + args.config + ".json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
