#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B20 -- amplia la ablacion de `corpus-d5.md` S5.1 (realista_d5 vs
abl_r5_sinonda, solo psm 3 y psm 11) a las TRES clases reales de --psm que
mide `k-oem-acantilados.md` SB24 (auto-layout=3, bloque unico=6, disperso=11).

NO reimplementa tess_lote_d5.py: lo IMPORTA (no se toca, no se edita) y le
sobreescribe en caliente los globals de RUTA para que escriba dentro de este
worktree en vez de D:\\Work\\research\\FileX. Misma funcion `celda()`, mismo
`ocr_eval_d4.evaluar()`, mismo TESSDATA_PREFIX (PDFgear, spa+15 idiomas),
mismo idioma (spa, lista blanca).

uso: python b20_psm_sweep.py
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
ORIGEN = os.path.join(ROOT, "bench", "salidas-corpus-d5")
sys.path.insert(0, ORIGEN)

import tess_lote_d5 as t  # noqa: E402 (no se edita el fichero, solo se importa)

TMP = os.path.join(AQUI, "tmp")          # aqui vive abl_r5_sinonda.pdf ya generado
IMG = os.path.join(AQUI, "img")
os.makedirs(IMG, exist_ok=True)

t.RAIZ = ROOT
t.BASE = AQUI
t.TMP = TMP
t.IMG = IMG
t.PDF_CORPUS = os.path.join(ROOT, "corpus", "pdf")   # aqui vive realista_d5.pdf
# `_run(..., cwd=TMP)` fija el `cwd` como valor por DEFECTO en la definicion de
# la funcion (se evaluo en el import, con el TMP viejo de D:): sobreescribir
# `t.TMP` no lo mueve. Hay que tocar el default explicitamente.
t._run.__defaults__ = (600, None, TMP)

texto_dir = os.path.join(AQUI, "texto")
os.makedirs(texto_dir, exist_ok=True)

DOCS = ["realista_d5", "abl_r5_sinonda"]
PSMS = [3, 6, 11]   # las tres clases reales de k-oem-acantilados.md SB24
LANG = "spa"

filas = []
for doc in DOCS:
    g = t.geometria(t.ruta_pdf(doc))
    ppp = int(round(g.get("ppp_calculado") or 200))
    for psm in PSMS:
        f = t.celda(doc, ppp, "magick", psm, LANG, texto_dir)
        f["ppp_nativo"] = ppp
        f["geometria"] = g
        filas.append(f)
        b = f.get("bloques", {})
        print(f"{doc:16s} ppp={ppp:3d} psm={psm:2d} {LANG} "
              f"CER={f.get('cer_acentos', f.get('error'))}")

fj = os.path.join(AQUI, "json", "b20_psm_sweep.json")
os.makedirs(os.path.dirname(fj), exist_ok=True)
json.dump(filas, open(fj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n-> {fj}  ({len(filas)} celdas)")
