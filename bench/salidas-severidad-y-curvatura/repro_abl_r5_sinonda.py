#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B20 -- reproduce `abl_r5_sinonda` (el control de la sonda de curvatura de
`bench/corpus-d5.md` §5) DENTRO de este worktree, sin escribir en
`D:\\Work\\research\\FileX` (donde `gen_corpus_d5.py` tiene el RAIZ fijo a fuego
y que no es mi worktree).

NO reimplementa la receta: IMPORTA `bench/salidas-corpus-d5/gen_corpus_d5.py`
(no se toca, no se edita) y le sobreescribe en caliente los globals de RUTA
(RAIZ/BASE/TMP/OUT_PDF) para que sus funciones -- `render_maestro`,
`receta_realista`, `run()` -- escriban en un directorio desechable de ESTE
worktree. La receta, los parametros y el orden de las operaciones son
exactamente los de `gen_corpus_d5.py:242` (`r5`) y `:338` (la llamada con
onda=0), byte a byte.

Verificacion de fidelidad: el jpg/pdf resultante se compara por sha256 contra
`bench/salidas-corpus-d5/json/candidatas_d5.json`, que registro los hashes
originales cuando se genero por primera vez.

uso: python repro_abl_r5_sinonda.py
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
ORIGEN = os.path.join(ROOT, "bench", "salidas-corpus-d5")
sys.path.insert(0, ORIGEN)

import gen_corpus_d5 as g  # noqa: E402  (no se edita el fichero, solo se importa)

TMP = os.path.join(AQUI, "tmp")
os.makedirs(TMP, exist_ok=True)
antes = sorted(os.listdir(TMP))

# Redirige los globals de ruta del modulo importado a este worktree. No toca
# `bench/salidas-corpus-d5/gen_corpus_d5.py` en disco.
g.RAIZ = ROOT
g.BASE = AQUI
g.TMP = TMP
g.OUT_PDF = os.path.join(AQUI, "tmp")  # no usado: nom no empieza por AL_CORPUS

maestro = os.path.join(TMP, "maestro_m200.png")
g.render_maestro(g.MAQUETAS["m200"], maestro)
reverso = os.path.join(TMP, "maestro_m200_reverso.png")
g.render_maestro(g.MAQUETAS["m200"], reverso, flop=True)

nom, receta, maq, cfg = g.r5("abl_r5_sinonda", -1.5, 0, 2600, 72, 45, 0.22, 1.2,
                              "26%,80%", 0.35, 33)
assert receta == "realista" and maq == "m200"
cfg = dict(cfg)
cfg["maestro"] = maestro
cfg["reverso"] = reverso
jpg, ppp = g.receta_realista(nom, cfg, None)

pdf = os.path.join(TMP, nom + ".pdf")
g.run([g.MAGICK, jpg, "-units", "PixelsPerInch", "-density", str(ppp), pdf])

sha_jpg = g.sha256(jpg)
sha_pdf = g.sha256(pdf)

original = {f["nombre"]: f for f in
            json.load(open(os.path.join(ORIGEN, "json", "candidatas_d5.json"),
                            encoding="utf-8"))}
o = original.get(nom, {})
# El PDF de magick estampa /CreationDate aunque el JPEG intermedio sea
# identico (trampa 22, ya documentada): el criterio de fidelidad es el JPG,
# que SI es reproducible byte a byte.
identico = sha_jpg == o.get("jpg_sha256")

despues = sorted(os.listdir(TMP))
nuevos = [x for x in despues if x not in antes]

print(json.dumps({
    "nombre": nom, "ppp": ppp,
    "jpg_bytes": os.path.getsize(jpg), "jpg_sha256": sha_jpg,
    "pdf_bytes": os.path.getsize(pdf), "pdf_sha256": sha_pdf,
    "jpg_sha256_original": o.get("jpg_sha256"),
    "pdf_sha256_original": o.get("pdf_sha256"),
    "reproduccion_identica_byte_a_byte": identico,
    "nuevos_en_tmp": len(nuevos),
}, ensure_ascii=False, indent=2))

if not identico:
    raise SystemExit("La reproduccion NO coincide con el jpg/pdf original -- no seguir sin resolver esto")
