# -*- coding: utf-8 -*-
"""B7 -- calibra la heuristica de "degradacion severa" (`ocr-ppp-nativos.md` SR3)
sobre datos YA MEDIDOS de dos informes (no se repite ninguna celda):

  - `bench/psm-y-rasterizador.md` S2.1 (n=9, deterministas): 12 --psm x 6
    documentos de Tesseract, con CER y BYTES de cada celda. Es el corpus que
    ya contiene, con `rc=0` en las tres, las tres patologias: SILENCIO (0 B),
    CUENTA ATOMICA (2-25 B) y ALUCINACION (hasta 2377 B) -- trampa 25.
  - `bench/salidas-deskew-y-fidelidad/json/{b8_tesseract,b8_rapidocr}.json`
    (ronda 8, propios): 20+20 celdas de la familia `d4`, DOS motores sobre
    LOS MISMOS 20 rasteres -- la variable de MOTOR que pide el encargo.

Senal candidata: `razon = bytes_salida / bytes_referencia`. No usa ninguna
propiedad interna del motor (sirve igual para Tesseract y RapidOCR) y aqui se
calibra contra la referencia CONOCIDA -- que es la practica establecida del
proyecto (R1, R6, etc. tambien se calibraron contra CER conocido antes de
convertirse en regla del adaptador). Sustituir la referencia por un proxy sin
verdad conocida (cobertura de tinta, cajas del detector) es trabajo de
adaptador y queda PENDIENTE, declarado como tal en el informe.

uso: python b7_heuristica.py
"""
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
B8 = os.path.join(ROOT, "bench", "salidas-deskew-y-fidelidad", "json")

# ---------------------------------------------------------------------------
# Tabla de psm-y-rasterizador.md S2.1, transcrita a mano de la tabla publicada
# (12 --psm x 6 documentos, CER acentos y bytes). Referencia: d2/d3 = 79
# caracteres (trampa 9); d4/d4c/d4e/d4f = 610 caracteres (misma trampa).
# ---------------------------------------------------------------------------
REF_CHARS = {"d2": 79, "d3": 79, "d4": 610, "d4c": 610, "d4e": 610, "d4f": 610}

# (psm, doc) -> (cer_pct, bytes)
TABLA_PSM = {
    (1, "d2"): (30.38, 89), (1, "d3"): (100.00, 0), (1, "d4"): (84.56, 107),
    (1, "d4c"): (1.85, 610), (1, "d4e"): (100.00, 0), (1, "d4f"): (2.35, 610),
    (3, "d2"): (30.38, 89), (3, "d3"): (100.00, 0), (3, "d4"): (84.56, 107),
    (3, "d4c"): (1.85, 610), (3, "d4e"): (100.00, 0), (3, "d4f"): (2.35, 610),
    (4, "d2"): (30.38, 89), (4, "d3"): (100.00, 0), (4, "d4"): (84.73, 111),
    (4, "d4c"): (1.85, 610), (4, "d4e"): (100.00, 0), (4, "d4f"): (2.35, 610),
    (5, "d2"): (77.22, 54), (5, "d3"): (198.73, 221), (5, "d4"): (88.93, 111),
    (5, "d4c"): (81.04, 244), (5, "d4e"): (327.85, 2377), (5, "d4f"): (81.04, 278),
    (6, "d2"): (0.00, 82), (6, "d3"): (113.92, 133), (6, "d4"): (55.70, 346),
    (6, "d4c"): (6.54, 586), (6, "d4e"): (190.10, 1463), (6, "d4f"): (6.04, 582),
    (7, "d2"): (100.00, 0), (7, "d3"): (100.00, 0), (7, "d4"): (100.00, 0),
    (7, "d4c"): (99.50, 11), (7, "d4e"): (100.00, 0), (7, "d4f"): (100.00, 0),
    (8, "d2"): (98.73, 2), (8, "d3"): (98.73, 2), (8, "d4"): (99.66, 3),
    (8, "d4c"): (99.83, 2), (8, "d4e"): (100.00, 2), (8, "d4f"): (100.00, 2),
    (9, "d2"): (98.73, 2), (9, "d3"): (100.00, 2), (9, "d4"): (96.48, 22),
    (9, "d4c"): (95.97, 25), (9, "d4e"): (99.83, 2), (9, "d4f"): (95.97, 25),
    (10, "d2"): (98.73, 2), (10, "d3"): (98.73, 2), (10, "d4"): (100.00, 2),
    (10, "d4c"): (100.00, 3), (10, "d4e"): (100.00, 2), (10, "d4f"): (100.00, 3),
    (11, "d2"): (13.92, 91), (11, "d3"): (188.61, 263), (11, "d4"): (41.78, 485),
    (11, "d4c"): (2.68, 625), (11, "d4e"): (119.30, 1335), (11, "d4f"): (2.68, 626),
    (12, "d2"): (13.92, 91), (12, "d3"): (163.29, 233), (12, "d4"): (41.78, 485),
    (12, "d4c"): (2.68, 625), (12, "d4e"): (109.40, 1262), (12, "d4f"): (2.68, 626),
    (13, "d2"): (98.73, 2), (13, "d3"): (98.73, 2), (13, "d4"): (99.66, 3),
    (13, "d4c"): (99.83, 2), (13, "d4e"): (100.00, 2), (13, "d4f"): (100.00, 3),
}


def clasificacion(cer, bts, ref_chars):
    """Etiqueta CONOCIDA (no la senal candidata) a partir de rc/CER/bytes.
    silencio: 0 B. atomica: 1-25 B con CER>=95. alucinacion: bytes > 1,3x la
    referencia en CARACTERES (proxy grosero de bytes UTF-8) con CER alto.
    degradado/normal: el resto (incluye lecturas malas SIN sobrar bytes,
    p.ej. d4 psm 1/3/4: 107 B con 84,56% de CER)."""
    if bts == 0:
        return "SILENCIO"
    if bts <= 25 and cer >= 90:
        return "ATOMICA"
    if bts > 1.3 * ref_chars and cer > 50:
        return "ALUCINACION"
    return "NORMAL/DEGRADADO"


filas = []
for (psm, doc), (cer, bts) in TABLA_PSM.items():
    ref = REF_CHARS[doc]
    filas.append({
        "motor": f"tesseract-psm{psm}", "doc": doc, "cer_pct": cer, "bytes": bts,
        "ref_chars": ref, "razon": round(bts / ref, 4),
        "clase": clasificacion(cer, bts, ref),
        "fuente": "psm-y-rasterizador.md S2.1",
    })

# --- ronda 8: 20 Tesseract psm3 + 20 RapidOCR, familia d4, ref=610 ----------
REF_D4 = 610
for nombre, motor in (("b8_tesseract.json", "tesseract-psm3"),
                      ("b8_rapidocr.json", "rapidocr-v6-r6")):
    datos = json.load(open(os.path.join(B8, nombre), encoding="utf-8"))
    for r in datos["rows"]:
        bts = None
        # bytes reales del fichero de texto guardado en la ronda 8
        prefijo = "tesseract" if "tesseract" in motor else "rapidocr"
        nom_txt = f"{prefijo}__{r['doc']}__ppp{r['ppp']}__{'deskew' if r['deskew'] else 'base'}.txt"
        ruta_txt = os.path.join(ROOT, "bench", "salidas-deskew-y-fidelidad",
                                 "texto", nom_txt)
        bts = os.path.getsize(ruta_txt) if os.path.exists(ruta_txt) else None
        if bts is None:
            continue
        cer = r["cer_pct"]
        filas.append({
            "motor": motor, "doc": f"{r['doc']}@{r['ppp']}{'d' if r['deskew'] else ''}",
            "cer_pct": cer, "bytes": bts, "ref_chars": REF_D4,
            "razon": round(bts / REF_D4, 4),
            "clase": clasificacion(cer, bts, REF_D4),
            "fuente": "ronda 8 (b8_tesseract.json / b8_rapidocr.json)",
        })

filas.sort(key=lambda f: f["razon"])

out = os.path.join(AQUI, "json")
os.makedirs(out, exist_ok=True)
json.dump(filas, open(os.path.join(out, "b7_heuristica.json"), "w", encoding="utf-8"),
           ensure_ascii=False, indent=2)

print(f"{'razon':>7} {'clase':17} {'motor':17} {'doc':14} {'cer%':>8} {'bytes':>6} {'ref':>5}")
for f in filas:
    print(f"{f['razon']:7.3f} {f['clase']:17} {f['motor']:17} {f['doc']:14} "
          f"{f['cer_pct']:8.2f} {f['bytes']:6d} {f['ref_chars']:5d}")

print(f"\n{len(filas)} celdas -> {out}/b7_heuristica.json")
