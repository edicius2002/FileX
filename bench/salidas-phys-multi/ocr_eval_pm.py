# -*- coding: utf-8 -*-
"""G4 / B19 — envoltorio del evaluador ACENTUADO para la tanda del `pHYs` multimotor.

Que es y que NO es
------------------
`bench/scripts/ocr_eval.py` NO se abre ni se usa: es CIEGO A LAS TILDES
(`CLAUDE.md` trampa 10) y oculta 6,3 puntos de CER sobre castellano.
Este fichero NO reimplementa nada: importa `evaluar` de `ocr_eval_d4.py`, que esta
copiado BYTE A BYTE de `bench/salidas-corpus-d4/ocr_eval_d4.py`
(sha256 350354b261aef60b018b196204648c4c27effc0683f93a4fbcb5f2d551a30d82) junto con
`d4_texto.py` (sha256 fa4b8d5d74980b29f0e640911c42ea07e59ca3910f364bd599407cb79c3cf011).

Lo unico que añade es el MAPA DOCUMENTO -> REFERENCIA, y lo añade EXPLICITO en vez de
deducirlo del nombre. `ocr_eval_km.py::ref_de_nombre` decide por la subcadena "d4", y
eso ya produjo un 94,94 % espurio sobre `trivial` y evaluaria todo el corpus d5 contra
79 caracteres en vez de 610. Aqui: diccionario cerrado, y si el documento no esta,
peta. Un evaluador que adivina no es un evaluador.

La lectura que se PUBLICA en el informe es `cer_acentos_pct` (normalizacion NFC que
conserva `[a-z0-9aeiouun con tildes/dieresis/eñe] y espacio`). La lectura `cer_ascii_pct`
—identica a la de `ocr_eval.py`— se guarda en el JSON de cada celda para que las tablas
se puedan juntar con las de los demas agentes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ocr_eval_d4 import evaluar  # noqa: E402,F401

# documento -> id de referencia del evaluador. CERRADO A PROPOSITO.
#   "d4"     -> 610 caracteres con tildes (d4_texto.BLOQUES). Cuantiza a 0,16 puntos.
#   "legado" -> 79 caracteres sin tildes. Cuantiza a 1,27 puntos: CLAUDE.md trampa 9.
REF = {
    "escaneado_d1": "legado",
    "escaneado_d2": "legado",
    "escaneado_d3": "legado",
    "patologico_escaneado": "legado",
    "escaneado_d4": "d4",
    "escaneado_d4a": "d4",
    "escaneado_d4b": "d4",
    "escaneado_d4c": "d4",
    "escaneado_d4e": "d4",
    "escaneado_d4f": "d4",
}

# documentos cuya referencia es corta: toda conclusion sobre ellos va marcada.
CUANTIZA = {d for d, r in REF.items() if r == "legado"}


def ref_de_doc(doc):
    if doc not in REF:
        raise SystemExit(
            f"documento sin referencia declarada: {doc!r}. "
            "Añadelo a REF en ocr_eval_pm.py; no se adivina.")
    return REF[doc]
