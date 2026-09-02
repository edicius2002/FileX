# -*- coding: utf-8 -*-
"""P1 / evaluador. ENVOLTORIO DELGADO sobre bench/salidas-corpus-d4/ocr_eval_d4.py,
que es el fichero que produjo las cifras de d4 y por tanto EL UNICO COMPARABLE con
ellas. Aqui NO se reimplementa la metrica: se importa.

  * `norm_ascii`, `norm_acentos`, `lev`, `_bloque` y `evaluar` vienen tal cual de
    `ocr_eval_d4.py` (copiado a este directorio sin un solo cambio; sha256 en el
    MANIFIESTO). Ese fichero es a su vez copia adaptada de `bench/scripts/ocr_eval.py`,
    que sigue intacto y sigue siendo ciego a las tildes.
  * Lo unico que este envoltorio añade son DOS referencias mas que B10 necesita y que
    d4 no tenia:
      - `tipico`: el texto realmente extraible de corpus/pdf/tipico_texto.pdf, leido
        con pypdfium2 (105 caracteres). Es la unica referencia del proyecto que no
        procede de un generador.
      - `ref_de_nombre`: deduce la referencia del nombre del fichero, para que una
        tanda pueda mezclar documentos del corpus d4, del corpus legado y tipico.

uso: python ocr_eval_pn.py <referencia_id> fichero.txt [...]
"""
import json
import sys

import ocr_eval_d4 as _d4

norm_ascii = _d4.norm_ascii
norm_acentos = _d4.norm_acentos
lev = _d4.lev

# El texto realmente presente en corpus/pdf/tipico_texto.pdf, extraido con
# pypdfium2 (get_textpage().get_text_range()). El PDF lleva un caracter roto en la
# eñe (u+0091 tras una circunfleja), asi que la referencia se escribe con la eñe
# correcta: el OCR debe leer lo que se VE, no lo que el PDF codifica mal.
TIPICO = {
    "cuerpo": [
        "FileX - documento de prueba con texto seleccionable",
        "Segunda linea: acentos aeiou ñ y simbolos % & @",
        "Tabla: Col A Col B Col C",
        "1 2 3",
    ],
}


def referencia(rid):
    if rid == "tipico":
        return TIPICO
    return _d4.referencia(rid)


def evaluar(texto, rid="d4"):
    if rid == "tipico":
        _orig = _d4.referencia
        try:
            _d4.referencia = lambda _r: TIPICO
            return _d4.evaluar(texto, rid)
        finally:
            _d4.referencia = _orig
    return _d4.evaluar(texto, rid)


def ref_de_nombre(nombre):
    """ppp0200__escaneado_d4.png -> 'd4'; ppp0150__escaneado_d1.png -> 'legado'."""
    n = nombre.lower()
    if "tipico_texto" in n:
        return "tipico"
    if "d4" in n:
        return "d4"
    return "legado"


if __name__ == "__main__":
    rid = sys.argv[1]
    for ruta in sys.argv[2:]:
        t = open(ruta, encoding="utf-8", errors="replace").read()
        r = evaluar(t, rid)
        r["archivo"] = ruta
        print(json.dumps(r, ensure_ascii=False))
