#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C2 — el OCR que FileX obtiene sin tarjeta: el Tesseract embebido en
Ghostscript 10.07 (`-sDEVICE=ocr`, `hocr`, `pdfocr8/24/32`).

Subcomandos:
  sonda        que dispositivos existen, que idiomas cargan y con que error fallan
  cer          CER sobre los 4 PDF escaneados, en eng / spa / spa+eng, a ppp NATIVOS
  ppp          barrido de ppp sobre d3 y d2: comprueba la regla R1 sin GPU
  tiempo       mediana n>=9 del OCR de CPU, comparable con la tabla de GPU
  reparacion   la arista `pdf escaneado -> pdf(OCR) -> docx` y el 99,0 % de I1
  acentos      un PDF castellano CON TILDES fabricado aqui: la laguna del proyecto

Toda invocacion es sin shell, con argv en lista, stdin=DEVNULL y timeout.
TESSDATA_PREFIX se fija en el entorno del HIJO, no en la maquina.
"""
import json
import os
import re
import statistics
import subprocess
import sys
import time
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
OCR = os.path.join(AQUI, "ocr")
TESS = os.path.join(AQUI, "tessdata")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, AQUI)

import ocr_eval as EV_CIEGO           # noqa: E402  (arnes compartido, sin tocar)
import ocr_eval_tildes as EV_TILDE    # noqa: E402

TIMEOUT = 300
GS = "gswin64c"

# ppp NATIVOS medidos en bench/ocr-ppp-nativos.md 1. NO se sobremuestrea:
# rasterizar d2/d3 a 200 fue el artefacto que invalido una fase entera.
DOCS = [
    ("patologico_escaneado", "corpus/pdf/patologico_escaneado.pdf", 200),
    ("escaneado_d1", "corpus/pdf/escaneado_d1.pdf", 150),
    ("escaneado_d2", "corpus/pdf/escaneado_d2.pdf", 100),
    ("escaneado_d3", "corpus/pdf/escaneado_d3.pdf", 100),
]


def entorno(tessdata=TESS):
    e = dict(os.environ)
    if tessdata is None:
        e.pop("TESSDATA_PREFIX", None)
    else:
        e["TESSDATA_PREFIX"] = tessdata
    return e


def correr(orden, tessdata=TESS, timeout=TIMEOUT, binario=False):
    try:
        p = subprocess.run(orden, capture_output=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, env=entorno(tessdata))
    except subprocess.TimeoutExpired:
        return 124, b"" if binario else "", "TIMEOUT %ds" % timeout
    out = p.stdout if binario else p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    return p.returncode, out, err


def _testigo():
    t = time.perf_counter()
    s = 0
    for i in range(300000):
        s += i * i
    return (time.perf_counter() - t) * 1000


TESTIGO_SUB_BASE = None


def _testigo_sub():
    """Testigo de LANZAMIENTO DE PROCESO. El testigo monohilo del informe
    anterior NO ve la contencion multinucleo: con 12 nucleos, un bucle de
    Python cabe en uno libre y sale `limpia` mientras las sondas externas van
    x6,8 mas lentas. Medido en este mismo informe. Este si lo ve."""
    t = time.perf_counter()
    subprocess.run([GS, "--version"], capture_output=True,
                   stdin=subprocess.DEVNULL, timeout=60)
    return (time.perf_counter() - t) * 1000


def calibrar():
    global TESTIGO_SUB_BASE
    for _ in range(2):
        _testigo_sub()
    TESTIGO_SUB_BASE = min(_testigo_sub() for _ in range(5))
    print("# testigo de subproceso en reposo: %.1f ms" % TESTIGO_SUB_BASE)


def measure(etiqueta, n, fn, calentar=1):
    for _ in range(calentar):
        fn()
    antes = min(_testigo() for _ in range(3))
    sub_a = min(_testigo_sub() for _ in range(3))
    ts = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t) * 1000)
    despues = min(_testigo() for _ in range(3))
    sub_d = min(_testigo_sub() for _ in range(3))
    desv = abs(despues - antes) / max(antes, 1e-9)
    nivel = max(sub_a, sub_d) / TESTIGO_SUB_BASE if TESTIGO_SUB_BASE else None
    motivos = []
    if desv > 0.20:
        motivos.append("deriva cpu %+.0f%%" % (desv * 100))
    if nivel and nivel > 1.20:
        motivos.append("nivel sub x%.1f" % nivel)
    ts.sort()
    return {"etiqueta": etiqueta, "n": n,
            "mediana_ms": round(statistics.median(ts), 1),
            "min_ms": round(ts[0], 1), "max_ms": round(ts[-1], 1),
            "flag": "limpia" if not motivos else "SUCIA(%s)" % "; ".join(motivos),
            "testigo_ms": [round(antes, 2), round(despues, 2)],
            "testigo_sub_ms": [round(sub_a, 1), round(sub_d, 1)],
            "nivel_sub": round(nivel, 2) if nivel else None}


def guardar(nombre, obj):
    ruta = os.path.join(AQUI, nombre)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=str)
    print("-> %s" % ruta)


def gs_ocr_txt(pdf, ppp, idioma, destino=None, dispositivo="ocr", extra=(),
               tessdata=TESS):
    """Texto OCR de un PDF con el Tesseract EMBEBIDO. Sin binario externo."""
    orden = [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
             "-sDEVICE=" + dispositivo, "-r%d" % ppp]
    if idioma:
        orden.append("-sOCRLanguage=" + idioma)
    orden += list(extra)
    orden += ["-sOutputFile=" + (destino or "-"), pdf]
    rc, out, err = correr(orden, tessdata=tessdata, binario=bool(destino))
    return orden, rc, out, err


def texto_docx(ruta):
    """Texto de un .docx sin dependencias: word/document.xml sin etiquetas."""
    try:
        with zipfile.ZipFile(ruta) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile) as e:
        return None, "%s: %s" % (type(e).__name__, e)
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", " ", xml)
    return re.sub(r"<[^>]+>", "", xml), None


def dos_lecturas(texto):
    a = EV_CIEGO.evaluar(texto)
    b = EV_TILDE.evaluar(texto)
    return {"cer_ciego_pct": a["cer_pct"], "dist_ciego": a["dist_global"],
            "frases_ciego": a["frases_exactas"],
            "cer_tildes_pct": b["cer_pct"], "dist_tildes": b["dist_global"],
            "frases_tildes": b["frases_exactas"],
            "chars": a["chars_salida"], "texto": texto.strip()}


# ===========================================================================
def cmd_sonda():
    """Que hay dentro de gsdll64.dll y con que falla exactamente."""
    res = {"gs_version": correr([GS, "--version"])[1].strip()}
    pdf = os.path.join(RAIZ, "corpus", "pdf", "escaneado_d2.pdf")

    # 1. sin TESSDATA_PREFIX (se BORRA del entorno del hijo)
    for etiqueta, td in (("sin_tessdata_prefix", None),
                         ("tessdata_de_tesseract_ocr",
                          "C:\\Program Files\\Tesseract-OCR\\tessdata")):
        for lang in (None, "spa"):
            _, rc, out, err = gs_ocr_txt(pdf, 100, lang, tessdata=td)
            clave = etiqueta + ("_spa" if lang else "_por_defecto")
            res[clave] = {"rc": rc, "err": err.strip()[:400],
                          "out": out.strip()[:120]}
            print("%-34s lang=%-4s rc=%-4d %s"
                  % (etiqueta, lang, rc,
                     (err.strip().splitlines() or [out.strip()[:60]])[0][:100]))

    # 2. dispositivos
    rc, out, err = correr([GS, "-h"])
    disp = " ".join(out.split())
    res["dispositivos_ocr"] = [d for d in ("ocr", "hocr", "pdfocr8", "pdfocr24",
                                           "pdfocr32", "txtwrite", "docxwrite",
                                           "xpswrite", "pclm")
                               if re.search(r"\b%s\b" % d, disp)]
    print("dispositivos declarados: %s" % res["dispositivos_ocr"])

    # 3. idiomas: los que hay en el tessdata al que apuntamos y uno que no esta
    res["tessdata"] = sorted(os.listdir(TESS))
    idiomas = {}
    for lang in ("eng", "spa", "spa+eng", "eng+spa", "deu", "osd"):
        _, rc, out, err = gs_ocr_txt(pdf, 100, lang)
        idiomas[lang] = {"rc": rc, "chars": len(out.strip()),
                         "muestra": out.strip()[:60].replace("\n", " | "),
                         "err": err.strip()[:160]}
        print("  -sOCRLanguage=%-8s rc=%-4d %3d chars  %s"
              % (lang, rc, len(out.strip()),
                 idiomas[lang]["muestra"] or idiomas[lang]["err"][:60]))
    res["idiomas"] = idiomas

    # 4. la forma de pasar el idioma: -d frente a -s
    rc, out, err = correr([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                           "-sDEVICE=ocr", "-dOCRLanguage=spa", "-r100",
                           "-sOutputFile=-", pdf])
    res["dOCRLanguage"] = {"rc": rc, "err": err.strip()[:200],
                           "out": out.strip()[:200]}
    print("  -dOCRLanguage=spa -> rc=%d  %s" % (rc, (err or out).strip()[:110]))

    # 5. de donde sale spa.traineddata
    res["origen_spa"] = {
        "ruta": "C:/Program Files/PDFgear/tessdata/spa.traineddata",
        "bytes": os.path.getsize(os.path.join(TESS, "spa.traineddata")),
        "puesto_por_el_proyecto": False,
        "nota": "no lo instalo FileX; venia con PDFgear. Si no estuviera, "
                "habria que descargarlo de tessdata_fast/best."}
    guardar("ocr_sonda.json", res)
    return res


# ===========================================================================
def cmd_cer():
    """CER a ppp NATIVOS, en eng / spa / spa+eng. Las dos lecturas."""
    filas = []
    for nombre, rel, ppp in DOCS:
        pdf = os.path.join(RAIZ, rel.replace("/", os.sep))
        for lang in ("eng", "spa", "spa+eng"):
            orden, rc, out, err = gs_ocr_txt(pdf, ppp, lang)
            dst = os.path.join(OCR, "%s_%s_%dppp.txt" % (nombre, lang.replace("+", "-"), ppp))
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(out)
            f = {"documento": nombre, "ppp_nativos": ppp, "idioma": lang,
                 "rc": rc, "salida": os.path.relpath(dst, RAIZ).replace("\\", "/"),
                 "orden": " ".join(orden), "err": err.strip()[:160]}
            f.update(dos_lecturas(out))
            filas.append(f)
            print("%-22s %-8s %3d ppp  CER ciego %5.1f %%  CER tildes %5.1f %%  %r"
                  % (nombre, lang, ppp, f["cer_ciego_pct"], f["cer_tildes_pct"],
                     f["texto"][:44].replace("\n", " | ")))
    guardar("ocr_cer.json", filas)
    return filas


# ===========================================================================
def cmd_ppp():
    """R1 sin GPU: la curva de ppp del OCR de Ghostscript."""
    filas = []
    for nombre, rel, nat in (("escaneado_d3", "corpus/pdf/escaneado_d3.pdf", 100),
                             ("escaneado_d2", "corpus/pdf/escaneado_d2.pdf", 100),
                             ("escaneado_d1", "corpus/pdf/escaneado_d1.pdf", 150)):
        pdf = os.path.join(RAIZ, rel.replace("/", os.sep))
        for ppp in (75, 100, 125, 140, 150, 160, 175, 200, 250, 300):
            for lang in ("spa", "eng"):
                orden, rc, out, err = gs_ocr_txt(pdf, ppp, lang)
                f = {"documento": nombre, "ppp": ppp, "ppp_nativos": nat,
                     "factor": round(ppp / nat, 2), "idioma": lang, "rc": rc}
                f.update(dos_lecturas(out))
                f.pop("texto")
                f["muestra"] = out.strip()[:70].replace("\n", " | ")
                filas.append(f)
            print("%-14s %3d ppp (x%.2f)  spa %5.1f %%  eng %5.1f %%"
                  % (nombre, ppp, ppp / nat, filas[-2]["cer_ciego_pct"],
                     filas[-1]["cer_ciego_pct"]))
    guardar("ocr_ppp.json", filas)
    return filas


# ===========================================================================
def cmd_tiempo():
    """Mediana n>=9. Comparable con la tabla de GPU de ocr-ppp-nativos.md 7.1
    con una salvedad que hay que decir: alli se mide el OCR sobre una imagen ya
    rasterizada; aqui el gs rasteriza Y reconoce dentro de la misma invocacion,
    e incluye el arranque del proceso."""
    res = []
    for nombre, rel, ppp in DOCS:
        pdf = os.path.join(RAIZ, rel.replace("/", os.sep))
        for lang in ("eng", "spa"):
            m = measure("%s %s %dppp" % (nombre, lang, ppp), 9,
                        lambda p=pdf, q=ppp, l=lang: gs_ocr_txt(p, q, l))
            m.update({"documento": nombre, "idioma": lang, "ppp": ppp,
                      "dispositivo": "ocr"})
            res.append(m)
            print("%-22s %-4s %3d ppp  %8.1f ms  n=%d  %s"
                  % (nombre, lang, ppp, m["mediana_ms"], m["n"], m["flag"]))
    # el coste de txtwrite (sin OCR) como suelo: cuanto es rasterizar+arrancar
    pdf = os.path.join(RAIZ, "corpus", "pdf", "escaneado_d2.pdf")
    m = measure("suelo: txtwrite sobre d2 (sin OCR)", 9,
                lambda: correr([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                                "-sDEVICE=txtwrite", "-sOutputFile=-", pdf]))
    m.update({"documento": "escaneado_d2", "idioma": "-", "ppp": 0,
              "dispositivo": "txtwrite"})
    res.append(m)
    print("%-22s %-4s %3s      %8.1f ms  n=%d  %s"
          % ("suelo txtwrite d2", "-", "-", m["mediana_ms"], m["n"], m["flag"]))
    # pdfocr8: el dispositivo que produce la arista de reparacion
    for nombre, rel, ppp in DOCS:
        pdf = os.path.join(RAIZ, rel.replace("/", os.sep))
        dst = os.path.join(OCR, "%s_pdfocr8.pdf" % nombre)
        m = measure("%s pdfocr8 spa %dppp" % (nombre, ppp), 9,
                    lambda p=pdf, q=ppp, d=dst: gs_ocr_txt(
                        p, q, "spa", destino=d, dispositivo="pdfocr8"))
        m.update({"documento": nombre, "idioma": "spa", "ppp": ppp,
                  "dispositivo": "pdfocr8",
                  "bytes_salida": os.path.getsize(dst) if os.path.exists(dst) else 0})
        res.append(m)
        print("%-22s %-4s %3d ppp  %8.1f ms  n=%d  %s  (pdfocr8, %d B)"
              % (nombre, "spa", ppp, m["mediana_ms"], m["n"], m["flag"],
                 m["bytes_salida"]))
    guardar("ocr_tiempo.json", res)
    return res


# ===========================================================================
def cmd_reparacion():
    """La arista de reparacion: pdf escaneado -> pdf(OCR) -> docx, y el 99,0 %
    de similitud del camino I1 de fidelidad-caminos.md."""
    res = {"cadenas": [], "i1": None}
    for nombre, rel, ppp in DOCS:
        pdf = os.path.join(RAIZ, rel.replace("/", os.sep))
        fila = {"documento": nombre, "ppp": ppp}

        # (a) el camino de UN salto que fidelidad-caminos.md marco DESTRUIDO
        d1 = os.path.join(OCR, "%s_directo.docx" % nombre)
        orden_a = [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                   "-sDEVICE=docxwrite", "-sOutputFile=" + d1, pdf]
        t0 = time.perf_counter()
        rc_a, _, err_a = correr(orden_a)
        ms_a = (time.perf_counter() - t0) * 1000
        txt_a, e_a = texto_docx(d1)
        fila["directo"] = {"rc": rc_a, "ms": round(ms_a, 1), "orden": " ".join(orden_a),
                           "bytes": os.path.getsize(d1) if os.path.exists(d1) else 0,
                           "err": (err_a or e_a or "").strip()[:160]}
        fila["directo"].update(dos_lecturas(txt_a or ""))

        # (b) dos saltos: pdfocr8 y luego docxwrite
        p2 = os.path.join(OCR, "%s_ocr_spa.pdf" % nombre)
        orden_b1 = [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                    "-sDEVICE=pdfocr8", "-sOCRLanguage=spa", "-r%d" % ppp,
                    "-sOutputFile=" + p2, pdf]
        t0 = time.perf_counter()
        rc_b1, _, err_b1 = correr(orden_b1)
        ms_b1 = (time.perf_counter() - t0) * 1000
        d2 = os.path.join(OCR, "%s_ocr.docx" % nombre)
        orden_b2 = [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                    "-sDEVICE=docxwrite", "-sOutputFile=" + d2, p2]
        t0 = time.perf_counter()
        rc_b2, _, err_b2 = correr(orden_b2)
        ms_b2 = (time.perf_counter() - t0) * 1000
        txt_b, e_b = texto_docx(d2)
        fila["reparado"] = {
            "rc": [rc_b1, rc_b2], "ms": round(ms_b1 + ms_b2, 1),
            "ms_ocr": round(ms_b1, 1), "ms_docx": round(ms_b2, 1),
            "orden": [" ".join(orden_b1), " ".join(orden_b2)],
            "bytes_pdf": os.path.getsize(p2) if os.path.exists(p2) else 0,
            "bytes_docx": os.path.getsize(d2) if os.path.exists(d2) else 0,
            "err": (err_b1 + " " + err_b2 + " " + (e_b or "")).strip()[:160]}
        fila["reparado"].update(dos_lecturas(txt_b or ""))

        # (c) el PDF con capa OCR, leido con txtwrite: la capa esta o no esta
        rc_c, out_c, err_c = correr([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                                     "-sDEVICE=txtwrite", "-sOutputFile=-", p2])
        fila["capa_txtwrite"] = dict(dos_lecturas(out_c), rc=rc_c)
        res["cadenas"].append(fila)
        print("%-22s directo: %3d chars CER %5.1f %%   reparado: %3d chars CER %5.1f %%  (%.0f ms)"
              % (nombre, fila["directo"]["chars"], fila["directo"]["cer_ciego_pct"],
                 fila["reparado"]["chars"], fila["reparado"]["cer_ciego_pct"],
                 fila["reparado"]["ms"]))

    # --- I1: pdf CON TEXTO -> png -> pdf -> txt(OCR). El 99,0 % ------------
    orig = os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf")
    png = os.path.join(OCR, "i1_rasterizado.png")
    pdf2 = os.path.join(OCR, "i1_rasterizado.pdf")
    ordenes = [
        [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=png16m",
         "-r150", "-sOutputFile=" + png, orig],
        ["magick", png, "-density", "150", "-units", "PixelsPerInch", pdf2],
    ]
    for o in ordenes:
        correr(o)
    rc0, texto_orig, _ = correr([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                                 "-sDEVICE=txtwrite", "-sOutputFile=-", orig])
    rc1, sin_ocr, _ = correr([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                              "-sDEVICE=txtwrite", "-sOutputFile=-", pdf2])
    i1 = {"orden": [" ".join(o) for o in ordenes],
          "texto_original": texto_orig.strip(),
          "chars_original": len("".join(texto_orig.split())),
          "sin_ocr_chars": len("".join(sin_ocr.split())),
          "por_idioma": {}}
    for lang in ("eng", "spa"):
        _, rc, out, err = gs_ocr_txt(pdf2, 150, lang)
        a = " ".join(texto_orig.split())
        b = " ".join(out.split())
        d = EV_TILDE.lev(a, b)
        i1["por_idioma"][lang] = {
            "rc": rc, "texto": out.strip(), "chars": len(b),
            "distancia": d,
            "similitud_pct": round(100 * max(0.0, 1 - d / max(1, len(a))), 1),
            "similitud_pct_ciego": round(100 * max(0.0, 1 - EV_TILDE.lev(
                EV_CIEGO.norm(a), EV_CIEGO.norm(b)) / max(1, len(EV_CIEGO.norm(a)))), 1)}
        print("I1 %s: similitud %.1f %% (ciega %.1f %%) frente al 99,0 %% de "
              "fidelidad-caminos.md" % (lang, i1["por_idioma"][lang]["similitud_pct"],
                                        i1["por_idioma"][lang]["similitud_pct_ciego"]))
    res["i1"] = i1
    guardar("ocr_reparacion.json", res)
    return res


# ===========================================================================
TEXTO_ACENTOS = [
    "INFORME TECNICO",
    "La conversion se anadio en el ultimo anio.",
    "Nandu, camion, accion, pequenez y ambiguedad.",
]
TEXTO_ACENTOS_REAL = [
    "INFORME TÉCNICO",
    "La conversión se añadió en el último año.",
    "Ñandú, camión, acción, pequeñez y ambigüedad.",
]


def cmd_acentos():
    """La laguna que arrastra el proyecto entero: ninguna medida de OCR lleva
    tildes. Aqui se fabrica un PDF castellano CON tildes, enyes y dieresis y se
    mide con LOS DOS evaluadores. El fixture es de este informe: NO se toca el
    corpus, que es la base de 296 celdas ya medidas."""
    base = os.path.join(AQUI, "fixtures", "acentos_150ppp")
    png = base + ".png"
    pdf = base + ".pdf"
    ordenes = [
        ["magick", "-size", "1240x600", "xc:white", "-fill", "black",
         "-font", "Arial", "-pointsize", "44", "-annotate", "+80+140",
         TEXTO_ACENTOS_REAL[0], "-pointsize", "32",
         "-annotate", "+80+240", TEXTO_ACENTOS_REAL[1],
         "-annotate", "+80+320", TEXTO_ACENTOS_REAL[2],
         "-density", "150", "-units", "PixelsPerInch", png],
        ["magick", png, "-density", "150", "-units", "PixelsPerInch", pdf],
    ]
    for o in ordenes:
        rc, _, err = correr(o)
        if rc != 0:
            print("FALLO generando el fixture: %s" % err[:200])
            return None
    res = {"orden": [" ".join(o) for o in ordenes],
           "texto_real": TEXTO_ACENTOS_REAL, "ppp": 150, "lecturas": []}
    for lang in ("spa", "eng", "spa+eng"):
        _, rc, out, err = gs_ocr_txt(pdf, 150, lang)
        dst = os.path.join(OCR, "acentos_%s.txt" % lang.replace("+", "-"))
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(out)
        ciego = EV_CIEGO.evaluar(out)
        # el evaluador ciego usa SU referencia; hay que recalcular con la nuestra
        ref_c = EV_CIEGO.norm(" ".join(TEXTO_ACENTOS_REAL))
        n_c = EV_CIEGO.norm(out)
        d_c = EV_TILDE.lev(ref_c, n_c)
        t = EV_TILDE.evaluar(out, TEXTO_ACENTOS_REAL)
        fila = {"idioma": lang, "rc": rc, "texto": out.strip(),
                "cer_ciego_pct": round(100 * d_c / max(1, len(ref_c)), 1),
                "cer_tildes_pct": t["cer_pct"],
                "frases_exactas_tildes": t["frases_exactas"],
                "salida": os.path.relpath(dst, RAIZ).replace("\\", "/")}
        fila["puntos_que_oculta_el_evaluador_ciego"] = round(
            fila["cer_tildes_pct"] - fila["cer_ciego_pct"], 1)
        res["lecturas"].append(fila)
        print("%-8s CER ciego %5.1f %%   CER con tildes %5.1f %%   (oculta %4.1f puntos)\n         %r"
              % (lang, fila["cer_ciego_pct"], fila["cer_tildes_pct"],
                 fila["puntos_que_oculta_el_evaluador_ciego"],
                 out.strip()[:110].replace("\n", " | ")))
        del ciego
    guardar("ocr_acentos.json", res)
    return res


CMDS = {"sonda": cmd_sonda, "cer": cmd_cer, "ppp": cmd_ppp, "tiempo": cmd_tiempo,
        "reparacion": cmd_reparacion, "acentos": cmd_acentos}

if __name__ == "__main__":
    os.makedirs(OCR, exist_ok=True)
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        print("subcomandos: %s" % " ".join(CMDS))
        sys.exit(2)
    if sys.argv[1] == "tiempo":
        calibrar()
    CMDS[sys.argv[1]]()
