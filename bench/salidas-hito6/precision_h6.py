# -*- coding: utf-8 -*-
"""S6 / hito 6 — la clausula de PRECISION del criterio, verificada contra ESTE
sidecar y no contra el arnes de otro informe.

    «El OCR del PDF escaneado del corpus se recupera con distancia de edicion 0.»

Es la unica mitad del criterio original que ya se cumplia, y por eso mismo hay
que comprobarla **con la implementacion que se entrega**: heredar una cifra de
otro arnes es exactamente lo que la trampa 79 prohibe.

Los tres documentos van a sus **ppp NATIVOS** (`ocr-ppp-nativos.md` §2):
patologico 200, d1 **150** (no 100), d2 100. La entrada llega por **ruta**
(trampa 30) y el dispositivo va **fijado** (trampa 11).

Metrica: `bench/scripts/ocr_eval.py`, canonica **`acentos`** desde el
2026-08-28, IMPORTADA y no reimplementada. Se publica la clave `metrica` en cada
celda (trampa 55).

uso: precision_h6.py [cuda|cpu]
"""
import json
import os
import sys

D = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(D))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))

import ocr_eval                                              # noqa: E402
from filex import gpu, sidecar                               # noqa: E402

PY_OCR = os.environ.get("H6_PY", "D:/Work/research/FileX/.venv-ai/Scripts/python.exe")
DISPOSITIVO = sys.argv[1] if len(sys.argv) > 1 else "cuda"
IMG = os.path.join(D, "img")

DOCS = [("patologico_escaneado", 200), ("escaneado_d1", 150), ("escaneado_d2", 100)]

filas = []
with gpu.Lock("S6-precision") as lk:
    if lk.aviso:
        print(f"[aviso] {lk.aviso}", flush=True)
    with sidecar.Registro(ttl_s=999, python=PY_OCR) as reg:
        for doc, ppp in DOCS:
            ruta = os.path.join(IMG, f"{doc}_r{ppp}.png")
            r = reg.procesar("rapidocr", ruta, dispositivo=DISPOSITIVO)
            texto = r.get("texto", "")
            with open(os.path.join(D, "texto", f"precision_{doc}_{DISPOSITIVO}.txt"),
                      "w", encoding="utf-8") as f:
                f.write(texto)                   # fila N17: el TEXTO se guarda
            ev = ocr_eval.evaluar(texto)
            filas.append({
                "doc": doc, "ppp_nativos": ppp, "mpx": r.get("mpx"),
                "dispositivo": DISPOSITIVO, "via_entrada": r.get("via_entrada"),
                "ok": r.get("ok"), "chars": r.get("chars"),
                "cer_pct": ev.get("cer_pct"), "metrica": ev.get("metrica"),
                "cer_acentos_pct": ev.get("cer_acentos_pct"),
                "cer_ciego_pct": ev.get("cer_ciego_pct"),
                # `dist_global` es LA distancia de edicion del criterio.
                "distancia": ev.get("dist_global"),
                "frases_exactas": ev.get("frases_exactas"),
                "ref_len": ev.get("chars_ref"),
                "decision": r.get("decision"),
                "ms": r.get("ms")})
            print(json.dumps(filas[-1], ensure_ascii=False), flush=True)
        estado = reg.estado()

salida = {"dispositivo": DISPOSITIVO, "motor": "rapidocr PP-OCRv6 small + R6",
          "metrica_canonica": ocr_eval.METRICA_CANONICA,
          "referencia": ocr_eval.REFERENCIA,
          "referencia_len": len(ocr_eval.REFERENCIA),
          "filas": filas, "estado_final": estado,
          "distancia_0_en_los_tres": all(f["distancia"] == 0 for f in filas)}
with open(os.path.join(D, "json", f"precision_{DISPOSITIVO}.json"), "w",
          encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False, indent=2)
print(json.dumps({"distancia_0_en_los_tres": salida["distancia_0_en_los_tres"]}))
