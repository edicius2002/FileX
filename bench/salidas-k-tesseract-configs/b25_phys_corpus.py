#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B23 (cierre, parte 2) -- rejilla 2x2 {con pHYs, sin pHYs} x {corpus viejo, corpus
d5} para el `k` de Tesseract, con el --psm fijado en cada celda (CLAUDE.md trampa 8:
el --psm no es separable del k).

Por que existe: `k-oem-acantilados.md` (B23) dejo el k de Tesseract con pHYs
DECLARADO sobre la familia d5 (x1,40 psm3 / x1,60 psm11) y no es comparable con el
publicado en CLAUDE.md (x0,875/x0,75, SIN declarar), porque mezcla dos variables a
la vez: pHYs Y corpus. Este script mide las DOS celdas que faltan para separarlas;
las otras dos ya estan medidas (bench/salidas-k-motor/json/tesseract_cpu_*__cer.json
para "corpus viejo, sin pHYs"; bench/salidas-k-oem-acantilados/json/b23_tess{3,11}.json
para "corpus d5, con pHYs") y NO se repiten aqui.

Diseno de receta, declarado para que cada comparacion diga que aisla:
  - corpus VIEJO usa SIEMPRE escala de grises (-colorspace Gray), como ya la usaba
    la celda existente "viejo, sin pHYs" (bench/salidas-k-motor/preparar_km.py).
    Aqui se le añade SOLO "-units PixelsPerInch" para declarar el pHYs -> la fila
    "viejo" (existente vs nueva) aisla el efecto de pHYs solo.
  - corpus D5 usa SIEMPRE sRGB (-colorspace sRGB), como ya la usaba la celda
    existente "d5, con pHYs" (b23_k_d5.py:raster_declarado). Aqui se le QUITA
    "-units PixelsPerInch" -> la fila "d5" (nueva vs existente) tambien aisla el
    efecto de pHYs solo.
  - El corpus viejo y el corpus d5 no comparten colorspace (Gray vs sRGB) porque
    heredan la receta que cada uno ya tenia publicada; se mide un control aparte
    (ver b26_control_colorspace.py) para descartar que el colorspace, no solo el
    pHYs, mueva el CER de Tesseract.

Metodo IDENTICO al ya usado (no se inventa uno nuevo):
  - factores = los 7 de k-oem-acantilados.md/B23 (0,75 .. 1,60), no los 11 de
    k-por-motor.md, para que las CUATRO celdas del 2x2 compartan exactamente la
    misma rejilla de factores.
  - evaluador CORPUS VIEJO: ocr_eval_d4.py (copia byte a byte), rid "legado" para
    escaneado_d3/patologico_escaneado, rid "d4" para escaneado_d4/d4c -- el MISMO
    reparto que uso ocr_eval_km.ref_de_nombre en k-por-motor.md.
  - evaluador CORPUS D5: bench/scripts/ocr_eval.py, evaluar(texto,"acentos",REF)
    con REF = d4_texto.BLOQUES aplanado -- el MISMO que uso b23_k_d5.py.
  - k por MINIMO ARREPENTIMIENTO: regret(k) = media_documentos[CER(doc,k) -
    min_f CER(doc,f)] (tablas_km.py, CLAUDE.md trampa 8), nunca el minimo de un
    solo documento.

uso: python b25_phys_corpus.py <viejo-phys|d5-nophys> [--reps 3]
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))  # .../bench/salidas-k-tesseract-configs -> raiz
PDF = os.path.join(ROOT, "corpus", "pdf")
IMG = os.path.join(BASE, "img")
JS = os.path.join(BASE, "json")
TXT = os.path.join(BASE, "texto")
for d in (IMG, JS, TXT):
    os.makedirs(d, exist_ok=True)

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"

FACTORES = [0.75, 0.875, 1.00, 1.125, 1.25, 1.40, 1.60]

DOCS_VIEJO = [("escaneado_d3", 100), ("escaneado_d4c", 200),
              ("patologico_escaneado", 200), ("escaneado_d4", 200)]
DOCS_D5 = [("escaneado_d5a", 90), ("escaneado_d5c", 80),
           ("escaneado_d5", 72), ("escaneado_d5b", 60)]

sys.path.insert(0, BASE)
import ocr_eval_d4  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
import ocr_eval as ocr_eval_compartido  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
from d4_texto import BLOQUES as D5_BLOQUES  # noqa: E402
REF_D5 = [linea for bloque in D5_BLOQUES.values() for linea in bloque]


def testigo_mono(n=400000):
    t = time.perf_counter(); z = 0
    for i in range(n):
        z += i * i
    return round((time.perf_counter() - t) * 1000, 2)


def testigo_proceso(n=5, tope_s=20.0):
    vals = []
    t_ini = time.perf_counter()
    for _ in range(n):
        restante = tope_s - (time.perf_counter() - t_ini)
        if restante <= 0.5:
            return round(tope_s * 1000, 2), True
        t = time.perf_counter()
        try:
            subprocess.run(["ffprobe", "-v", "quiet", "-version"],
                            stdin=subprocess.DEVNULL, capture_output=True,
                            timeout=restante)
        except Exception:
            return round(tope_s * 1000, 2), True
        vals.append((time.perf_counter() - t) * 1000)
    if not vals:
        return round(tope_s * 1000, 2), True
    return round(statistics.median(vals), 2), False


def raster_declarado_gray(doc, factor, native):
    """Corpus VIEJO, pHYs DECLARADO: misma receta Gray que preparar_km.py, con
    -units PixelsPerInch añadido (unica diferencia frente a la celda existente)."""
    ppp = int(round(native * factor))
    dst = os.path.join(IMG, f"vphys{int(round(factor*1000)):04d}__{doc}.png")
    if not os.path.exists(dst):
        p = subprocess.run(
            [MAGICK, "-density", str(ppp), os.path.join(PDF, doc + ".pdf") + "[0]",
             "-units", "PixelsPerInch", "-density", str(ppp), "-colorspace", "Gray",
             "-alpha", "remove", "-background", "white", "-flatten", dst],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        if p.returncode:
            raise RuntimeError(f"magick rc={p.returncode}: {p.stderr[:300]}")
    return dst, ppp


def raster_srgb_sin_phys(doc, factor, native):
    """Corpus D5, pHYs SIN declarar: misma receta sRGB que b23_k_d5.py:
    raster_declarado, SIN -units PixelsPerInch (unica diferencia frente a la
    celda existente kd####)."""
    ppp = int(round(native * factor))
    dst = os.path.join(IMG, f"d5nophys{int(round(factor*1000)):04d}__{doc}.png")
    if not os.path.exists(dst):
        p = subprocess.run(
            [MAGICK, "-density", str(ppp), os.path.join(PDF, doc + ".pdf") + "[0]",
             "-colorspace", "sRGB", "-alpha", "remove", "-background", "white",
             "-flatten", dst],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        if p.returncode:
            raise RuntimeError(f"magick rc={p.returncode}: {p.stderr[:300]}")
    return dst, ppp


def leer_tess(ruta, psm):
    out = os.path.join(IMG, "tmp_b25")
    r = subprocess.run([TESS, ruta, out, "-l", "spa", "--psm", psm],
                        stdin=subprocess.DEVNULL, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=20,
                        env={**os.environ, "TESSDATA_PREFIX": TESSDATA})
    txt = ""
    if r.returncode == 0 and os.path.exists(out + ".txt"):
        txt = open(out + ".txt", encoding="utf-8", errors="replace").read()
    return txt, r.returncode


def ref_id_viejo(doc):
    return "legado" if doc in ("escaneado_d3", "patologico_escaneado") else "d4"


def evaluar_viejo(texto, doc):
    return ocr_eval_d4.evaluar(texto, ref_id_viejo(doc))["cer_acentos_pct"]


def evaluar_d5(texto):
    return ocr_eval_compartido.evaluar(texto, "acentos", REF_D5)["cer_pct"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", choices=["viejo-phys", "d5-nophys"])
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    if args.config == "viejo-phys":
        docs = DOCS_VIEJO
        raster = raster_declarado_gray
        evaluar = evaluar_viejo
    else:
        docs = DOCS_D5
        raster = lambda doc, f, n: raster_srgb_sin_phys(doc, f, n)  # noqa: E731
        evaluar = lambda texto, doc: evaluar_d5(texto)  # noqa: E731

    mono_ini = testigo_mono()
    proc_ini, topado_ini = testigo_proceso()
    rows = []
    t0 = time.time()
    for psm in ("3", "11"):
        for doc, native in docs:
            for f in FACTORES:
                path, ppp = raster(doc, f, native)
                textos, cers, rcs = [], [], []
                for _ in range(args.reps):
                    texto, rc = leer_tess(path, psm)
                    textos.append(texto)
                    rcs.append(rc)
                    cers.append(evaluar(texto, doc))
                texto = textos[-1]
                nom = os.path.splitext(os.path.basename(path))[0]
                open(os.path.join(TXT, f"{args.config}_psm{psm}__{nom}.txt"),
                     "w", encoding="utf-8").write(texto)
                row = {"config": args.config, "psm": psm, "doc": doc,
                       "ppp_nativo": native, "factor": f, "ppp": ppp,
                       "n": args.reps, "determinista": len(set(textos)) == 1,
                       "rc": rcs, "cer_pct": cers[-1], "cer_reps": cers}
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)

    mono_fin = testigo_mono()
    proc_fin, topado_fin = testigo_proceso()
    ruido = {"mono_ini": mono_ini, "mono_fin": mono_fin,
             "deriva": round(mono_fin / max(mono_ini, .01), 2),
             "proc_ini": proc_ini, "proc_fin": proc_fin,
             "nivel": round(max(proc_ini, proc_fin) / 26.65, 2),
             "topado": topado_ini or topado_fin}
    out = {"config": args.config, "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time() - t0, 1)}
    json.dump(out, open(os.path.join(JS, "b25_" + args.config + ".json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"escrito json/b25_{args.config}.json  ({len(rows)} celdas, "
          f"{out['segundos']} s, ruido={out['etiqueta_ruido']})")


if __name__ == "__main__":
    main()
