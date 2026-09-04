#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B26 -- el residuo declarado de B23: la rejilla de `k` POR ENCIMA de x1,60.

`bench/k-tesseract-y-configs-faltantes.md` (worker8) cerro B23 sobre la rejilla
de siete factores x0,75..x1,60 y dejo escrito, en la fila del inventario, lo
que no cubre: "la rejilla por encima de x1,60 (EasyOCR y psm 11 mejoran hasta
el borde medido)". Un argmin que cae en el ULTIMO punto del barrido no es un
argmin: es el borde. Este arnes extiende la rejilla hacia arriba para las tres
configuraciones cuyo optimo publicado toca ese borde -- EasyOCR, Tesseract
`psm 11` y Docling+R6 -- y REMIDE tambien los siete factores viejos, para que
el arrepentimiento salga de UNA sola tanda (trampa 59: no se compara con una
cifra historica sin medir tambien la version historica en la propia tanda).

Metodologia heredada de `bench/salidas-k-oem-acantilados/b23_k_d5.py` y
`b23_resto_docling.py`, sin inventar una nueva:

  * mismos 4 documentos de la familia d5, con sus ppp NATIVOS declarados;
  * misma receta de raster por motor -- gris SIN declarar pHYs para EasyOCR
    (es inmune, trampa 29, y esa es la receta que fijo el `k` original),
    sRGB CON `-units PixelsPerInch` para Tesseract (el unico que lo consulta),
    y Docling rasteriza el mismo por `RapidOcrOptions.scale`;
  * mismo evaluador (`bench/scripts/ocr_eval.py`) con la metrica ACENTUADA,
    la canonica desde el 2026-08-28, y la referencia `d4_texto.BLOQUES`
    aplanada -- la misma que uso b23;
  * `k` por MINIMO ARREPENTIMIENTO sobre los documentos, nunca el optimo de
    uno solo (`bench/k-por-motor.md`).

Lo que este arnes ANADE sobre b23, y por que:

  * **`rc` por celda y por repeticion** (trampa 25): una celda a CER 100 % es
    indistinguible entre silencio legitimo y proceso que no arranco, y lo
    unico que las separa es el `rc`. `b23_k_d5.py` no lo registraba.
  * **guardia de VRAM PREDICTIVA antes de cada celda** con el modelo publicado
    en `bench/ocr-produccion-sidecar.md` §5.1 (`ordenada + pendiente x Mpx`),
    porque subir el `k` sube los pixeles y el asignador no devuelve la VRAM
    (trampa 67). Si una celda no cabe, se registra `omitido_vram` -- eso ES el
    resultado, no un hueco.
  * **orden de celdas DESCENDENTE por Mpx** dentro de cada configuracion:
    llegar a un tamano en escalera cuesta x2,25 mas VRAM que ir directo
    (trampa 67). El orden no afecta al CER de motores deterministas, y §"control
    de reproduccion" del informe lo comprueba contra las celdas publicadas.
  * **cache de evaluacion por texto**: `evaluar()` cuesta ~4,6 s por llamada
    (ventana deslizante, trampa 57) y con n=9 repeticiones deterministas
    evaluar nueve veces el mismo texto es tiempo tirado. Se evalua una vez por
    texto DISTINTO; `cer_reps` sale del cache, asi que si una repeticion
    divergiera se veria igual.

uso: python b26_borde.py <easyocr|tess11|tess3|docling-r6> [--reps N]
                         [--factores 1.75,2.00,...] [--sufijo nombre]
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, "bench", "salidas-k-borde-rejilla")
PDF = os.path.join(ROOT, "corpus", "pdf")
IMG = os.path.join(BASE, "img")
JS = os.path.join(BASE, "json")
TXT = os.path.join(BASE, "texto")
for _d in (IMG, JS, TXT):
    os.makedirs(_d, exist_ok=True)

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\PDFgear\tessdata"

# Los mismos cuatro documentos de b23, con sus ppp nativos. El tercer campo es
# el area de la pagina en pixeles a 72 ppp (MEDIDO con `magick identify`), que
# es lo que permite predecir los Mpx de cualquier factor sin rasterizar.
DOCS = [
    ("escaneado_d5a", 90, 466 * 641),
    ("escaneado_d5c", 80, 465 * 637),
    ("escaneado_d5", 72, 465 * 636),
    ("escaneado_d5b", 60, 466 * 637),
]
REJILLA_B23 = [0.75, 0.875, 1.00, 1.125, 1.25, 1.40, 1.60]

sys.path.insert(0, os.path.join(ROOT, "bench", "scripts"))
from ocr_eval import evaluar  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "bench", "salidas-corpus-d5"))
from d4_texto import BLOQUES  # noqa: E402
REF = [linea for bloque in BLOQUES.values() for linea in bloque]
sys.path.insert(0, ROOT)
from filex import gpu  # noqa: E402

# bench/corpus-d4.md §7.4 -- normalizacion ImageNet + post-proceso de PaddleX
# que declara el inference.yml de PP-OCRv6 small. Identico a b23.
R6 = {"Det.mean": [0.485, 0.456, 0.406], "Det.std": [0.229, 0.224, 0.225],
      "Det.thresh": 0.2, "Det.box_thresh": 0.45, "Det.unclip_ratio": 1.4,
      "Det.max_candidates": 3000}

# `bench/ocr-produccion-sidecar.md` §5.1: coste = min(ordenada + pendiente*Mpx,
# tope). Los valores de abajo NO son los publicados alli, y el motivo esta
# MEDIDO por `sonda_vram_b26.py` (4 puntos por motor, cada uno en un proceso
# FRESCO -- ir directo, trampa 67), sobre `escaneado_d5a` a x1,60/x2,50/x4,00/
# x6,00 (1,195 / 2,917 / 7,468 / 16,802 Mpx):
#
#   EasyOCR      1 189 / 2 500 / 3 953 / 3 895 MiB  -> SATURA hacia 7,5 Mpx
#   Docling+R6     749 / 1 112 / 1 061 /   953 MiB  -> PLANO desde el principio
#
# Dos correcciones sobre lo heredado, las dos con numero:
#
#  (a) La recta publicada de EasyOCR (641 + 1 080, "tope: ninguno") predice
#      8 706 MiB a 7,468 Mpx y se midieron 3 953: sobrestima x2,20. Su serie
#      original llegaba a 8,88 Mpx en un A4 REAL; aqui EasyOCR reescala la
#      entrada por su `canvas_size` (§ del informe), asi que por encima de ese
#      punto el coste deja de crecer. La recta sigue siendo una cota superior
#      valida -- pero como cota RECORTA la rejilla que este informe extiende,
#      que es el mismo defecto que el informe denuncia, cometido por el
#      instrumento (trampa 85: tabula el residuo antes de presupuestar).
#  (b) A Docling+RapidOCR-torch NO le corresponde la recta de EasyOCR sino la
#      de RAPIDOCR (643 + 109, tope 1 526), que es la del motor que de verdad
#      hace el OCR dentro de docling. Predice 773 MiB a 1,195 Mpx (medido 749)
#      y 1 526 a 16,8 (medido 953): cota superior en los 4 puntos, sin
#      recortar nada.
VRAM_MODELO = {
    "easyocr": (280.0, 761.0, 4200.0),      # MEDIDO aqui; tope = 3 953 + margen
    "docling-r6": (643.0, 109.0, 1526.0),   # recta publicada de RapidOCR
}
MARGEN_MIB = float(os.environ.get("VRAM_MARGEN_MIB", "500"))


def mpx(area_72, native, factor):
    """Megapixeles de la pagina rasterizada a `native*factor` ppp."""
    ppp = native * factor
    return area_72 * (ppp / 72.0) ** 2 / 1e6


def vram_libre_mib():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.free",
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
    """Testigo de NIVEL, con tope propio: un testigo que puede tumbar la
    medicion no es un testigo (CLAUDE.md §3)."""
    vals = []
    t_ini = time.perf_counter()
    for _ in range(n):
        restante = tope_s - (time.perf_counter() - t_ini)
        if restante <= 0.5:
            return round(tope_s * 1000, 2)
        t = time.perf_counter()
        try:
            subprocess.run(["ffprobe", "-v", "quiet", "-version"],
                           stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=restante)
        except Exception:
            return round(tope_s * 1000, 2)
        vals.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(vals), 2) if vals else round(tope_s * 1000, 2)


def raster(doc, factor, native, declarado):
    """Rasteriza la pagina 0. `declarado` = escribe el pHYs (`-units
    PixelsPerInch`), que es lo unico que consulta Tesseract (trampa 29)."""
    ppp = int(round(native * factor))
    pre = "kd" if declarado else "kf"
    dst = os.path.join(IMG, "%s%04d__%s.png" % (pre, int(round(factor * 1000)), doc))
    if not os.path.exists(dst):
        if declarado:
            argv = [MAGICK, "-density", str(ppp), os.path.join(PDF, doc + ".pdf") + "[0]",
                    "-units", "PixelsPerInch", "-density", str(ppp), "-colorspace", "sRGB",
                    "-alpha", "remove", "-background", "white", "-flatten", dst]
        else:
            argv = [MAGICK, "-density", str(ppp), os.path.join(PDF, doc + ".pdf") + "[0]",
                    "-colorspace", "Gray", "-alpha", "remove", "-background", "white",
                    "-flatten", dst]
        p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=180)
        if p.returncode:
            raise RuntimeError("magick rc=%s: %s" % (p.returncode, p.stderr[:300]))
    return dst, ppp


def build(config):
    """Devuelve (leer, meta). `leer(ruta_o_pdf, ppp)` -> (texto, rc)."""
    if config == "easyocr":
        import torch
        tl = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.isdir(tl):
            os.add_dll_directory(tl)
        import easyocr
        x = easyocr.Reader(["es", "en"], gpu=True, verbose=False)

        def leer(path, ppp):
            try:
                return " ".join(x.readtext(path, detail=0, paragraph=False)), 0
            except Exception as ex:
                return "", "%s: %s" % (type(ex).__name__, str(ex)[:150])
        return leer, {"motor": "EasyOCR CRAFT + latin_g2", "dispositivo": "GPU cuda:0",
                      "gpu": True, "raster": "gris, pHYs NO declarado", "declarado": False}

    if config.startswith("tess"):
        psm = config[4:]

        def leer(path, ppp):
            out = os.path.join(IMG, "tmp_b26_" + psm)
            try:
                r = subprocess.run([TESS, path, out, "-l", "spa", "--psm", psm],
                                   stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=180,
                                   env={**os.environ, "TESSDATA_PREFIX": TESSDATA})
            except subprocess.TimeoutExpired:
                return "", "TimeoutExpired:180s"
            if r.returncode != 0 or not os.path.exists(out + ".txt"):
                return "", r.returncode
            return open(out + ".txt", encoding="utf-8", errors="replace").read(), 0
        return leer, {"motor": "Tesseract 5, psm " + psm, "dispositivo": "CPU", "gpu": False,
                      "raster": "sRGB, pHYs DECLARADO", "declarado": True}

    if config == "docling-r6":
        import torch
        tl = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.isdir(tl):
            os.add_dll_directory(tl)
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            AcceleratorDevice, AcceleratorOptions, PdfPipelineOptions, RapidOcrOptions)
        from docling.document_converter import DocumentConverter, PdfFormatOption

        # Un `DocumentConverter` por CELDA, no por repeticion: es lo que hacia
        # `b23_resto_docling.py` (lo construia fuera del bucle de reps), y
        # construirlo nueve veces por celda mediria el constructor, no el OCR.
        convs = {}

        def leer(ruta_pdf, ppp):
            if ppp in convs:
                try:
                    return convs[ppp].convert(ruta_pdf).document.export_to_markdown(), 0
                except Exception as ex:
                    return "", "%s: %s" % (type(ex).__name__, str(ex)[:150])
            po = PdfPipelineOptions()
            po.accelerator_options = AcceleratorOptions(num_threads=8,
                                                        device=AcceleratorDevice.CUDA)
            po.do_ocr = True
            po.do_table_structure = False
            oo = RapidOcrOptions(lang=["english"], backend="torch", force_full_page_ocr=True)
            oo.scale = ppp / 72.0
            oo.rapidocr_params = dict(R6)
            po.ocr_options = oo
            conv = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po)})
            convs.clear()
            convs[ppp] = conv
            try:
                return conv.convert(ruta_pdf).document.export_to_markdown(), 0
            except Exception as ex:
                return "", "%s: %s" % (type(ex).__name__, str(ex)[:150])
        return leer, {"motor": "Docling+RapidOCR torch + R6", "dispositivo": "GPU cuda",
                      "gpu": True, "raster": "docling interno (RapidOcrOptions.scale)",
                      "declarado": None, "backend": "torch", "lang": "english"}

    raise ValueError(config)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", choices=["easyocr", "tess11", "tess3", "docling-r6"])
    ap.add_argument("--reps", type=int, default=9)
    ap.add_argument("--factores", default=",".join("%g" % f for f in REJILLA_B23))
    ap.add_argument("--sufijo", default="")
    args = ap.parse_args()
    factores = [float(x) for x in args.factores.split(",") if x.strip()]

    # El motor NO se construye dos veces (b23 lo hacia, y construir EasyOCR
    # fuera del lock reserva VRAM antes de tenerlo): basta saber si usa GPU.
    usa_gpu = args.config in ("easyocr", "docling-r6")
    lock = gpu.Lock("B26-" + args.config) if usa_gpu else __import__("contextlib").nullcontext()

    # Celdas ordenadas de MAYOR a MENOR Mpx (trampa 67: la escalera cuesta
    # x2,25 mas VRAM que ir directo).
    celdas = []
    for doc, native, area in DOCS:
        for f in factores:
            celdas.append((mpx(area, native, f), doc, native, f))
    celdas.sort(key=lambda c: -c[0])

    ord_v, pend_v, tope_v = VRAM_MODELO.get(args.config, (0.0, 0.0, None))
    cache = {}
    mpx_max_ok = 0.0   # mayor Mpx ya servido: define el pool ya reservado

    with lock as lk:
        leer, meta = build(args.config)
        meta["reps"] = args.reps
        meta["factores"] = factores
        meta["orden_celdas"] = "descendente por Mpx"
        if usa_gpu:
            meta["lock_aviso"] = lk.aviso
            meta["vram_modelo"] = {"ordenada_mib": ord_v, "pendiente_mib_mpx": pend_v,
                                   "margen_mib": MARGEN_MIB}
        mono_ini = testigo_mono()
        proc_ini = testigo_proceso()
        rows = []
        t0 = time.time()
        for m, doc, native, f in celdas:
            ppp = int(round(native * f))
            base_row = {"config": args.config, "doc": doc, "ppp_nativo": native,
                        "factor": f, "ppp": ppp, "mpx": round(m, 3)}
            if usa_gpu:
                libre = vram_libre_mib()
                base_row["vram_libre_mib"] = libre
                # La regla de `ocr-produccion-sidecar.md` §5.1 esta escrita para
                # un proceso RECIEN ARRANCADO. Dentro de un proceso que ya
                # tiene un pool reservado, aplicarla cruda rechaza celdas que
                # el proceso SI puede servir -- y las rechaza justo porque el
                # asignador no devuelve la memoria (trampa 67). MEDIDO en el
                # piloto: tras la celda de 7,468 Mpx la VRAM libre baja de 9 941
                # a 6 161 MiB y ahi se queda, asi que dos celdas MENORES
                # (5,851 y 4,732 Mpx) salieron `omitido_vram` sin motivo. Con
                # el orden descendente, una celda que no supera el mayor Mpx ya
                # servido cabe POR CONSTRUCCION en el pool ya reservado; solo
                # el incremento sobre ese maximo pide memoria nueva.
                if m <= mpx_max_ok:
                    base_row["vram_previsto_mib"] = 0.0
                    base_row["vram_razon"] = "cabe en el pool ya reservado (%.3f <= %.3f Mpx)" % (
                        m, mpx_max_ok)
                else:
                    previsto = (ord_v if mpx_max_ok == 0.0 else 0.0) + pend_v * (m - mpx_max_ok)
                    if tope_v:
                        previsto = min(previsto, tope_v)
                    base_row["vram_previsto_mib"] = round(previsto, 1)
                    base_row["vram_razon"] = "incremento sobre %.3f Mpx ya servidos" % mpx_max_ok
                    if libre >= 0 and previsto + MARGEN_MIB > libre:
                        base_row["omitido_vram"] = ("previsto %.0f + margen %.0f > libre %d"
                                                    % (previsto, MARGEN_MIB, libre))
                        rows.append(base_row)
                        print(json.dumps(base_row, ensure_ascii=False), flush=True)
                        continue
            t_c = time.perf_counter()
            if args.config == "docling-r6":
                entrada = os.path.join(PDF, doc + ".pdf")
            else:
                entrada, _ = raster(doc, f, native, meta["declarado"])
            textos, rcs = [], []
            for _ in range(args.reps):
                texto, rc = leer(entrada, ppp)
                textos.append(texto)
                rcs.append(rc)
            cers = []
            for texto in textos:
                if texto not in cache:
                    ev = evaluar(texto, "acentos", REF)
                    cache[texto] = (ev["cer_pct"], ev["metrica"], ev["chars_salida"],
                                    ev["chars_ref"])
                cers.append(cache[texto][0])
            texto = textos[-1]
            nom = "k%04d__%s" % (int(round(f * 1000)), doc)
            with open(os.path.join(TXT, "%s__%s.txt" % (args.config, nom)), "w",
                      encoding="utf-8") as fh:
                fh.write(texto)
            base_row.update({
                "n": args.reps,
                "determinista": len(set(textos)) == 1,
                "cer_pct": statistics.median(cers),
                "cer_reps": cers,
                "rc_reps": rcs,
                "rc_todas_cero": all(r == 0 for r in rcs),
                "bytes_texto": cache[texto][2],
                "chars_ref": cache[texto][3],
                "metrica": cache[texto][1],
                "segundos": round(time.perf_counter() - t_c, 1),
            })
            if base_row["rc_todas_cero"]:
                mpx_max_ok = max(mpx_max_ok, m)
            rows.append(base_row)
            print(json.dumps(base_row, ensure_ascii=False), flush=True)
        mono_fin = testigo_mono()
        proc_fin = testigo_proceso()

    ruido = {"mono_ini": mono_ini, "mono_fin": mono_fin,
             "deriva": round(mono_fin / max(mono_ini, .01), 2),
             "proc_ini": proc_ini, "proc_fin": proc_fin,
             "nivel": round(max(proc_ini, proc_fin) / 26.65, 2)}
    out = {"meta": meta, "config": args.config, "ruido": ruido,
           "etiqueta_ruido": "SUCIA" if ruido["nivel"] > 2 else "limpia",
           "rows": rows, "segundos": round(time.time() - t0, 1)}
    nombre = "b26_" + args.config + (("_" + args.sufijo) if args.sufijo else "") + ".json"
    with open(os.path.join(JS, nombre), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
