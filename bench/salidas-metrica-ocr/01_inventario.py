# -*- coding: utf-8 -*-
"""A7 / paso 1 — INVENTARIO de las salidas de OCR almacenadas.

No mide nada todavia. Solo contesta: cuantos ficheros de texto de OCR hay en
disco, de que informe vienen, y a que DOCUMENTO pertenece cada uno (que es lo
que decide contra que referencia hay que evaluarlos).

Lo importante es el ultimo apartado: los ficheros cuyo documento NO se puede
deducir del nombre. Esos NO se recalculan y se cuentan como coste, en vez de
adivinarles una referencia (que es justo el error que `ocr_eval_pm.py` señala
de `ocr_eval_km.py::ref_de_nombre`).
"""
import json
import os
import re
import sys

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directorios de salidas que contienen texto de OCR, con el informe que publicaron.
DIRS = {
    "salidas-ocr-ppp": "ocr-ppp-nativos.md",
    "salidas-ocrmypdf": "ocrmypdf.md",
    "salidas-corpus-d4": "corpus-d4.md",
    "salidas-corpus-d5": "corpus-d5.md",
    "salidas-k-motor": "k-por-motor.md",
    "salidas-ppp-norm": "ppp-y-normalizacion.md",
    "salidas-psm": "psm-y-rasterizador.md",
    "salidas-phys-multi": "phys-multimotor.md",
    "salidas-verificador-gs": "verificador-ghostscript.md",
    "salidas-invocacion": "invocacion-aristas.md",
    "salidas-fase2": "gpu-fase2.md",
}

# doc -> id de referencia. CERRADO A PROPOSITO (ocr_eval_pm.py tiene razon:
# un evaluador que adivina no es un evaluador).
#   legado -> 79 caracteres, SIN tildes  (CLAUDE.md trampa 9: cuantiza a 1,27)
#   d4     -> 610 caracteres, 35 acentuados (cuantiza a 0,16)
# La familia d5 usa EXACTAMENTE el texto de d4 (bench/salidas-corpus-d5/d5_texto.py:
# "la cadena de referencia es EXACTAMENTE la misma de escaneado_d4").
REF_POR_DOC = {
    "escaneado_d1": "legado",
    "escaneado_d2": "legado",
    "escaneado_d3": "legado",
    "patologico_escaneado": "legado",
    "trivial": "legado",
    "smoke_d3": "legado",
}
# los que llevan d4/d5 en el nombre van contra la referencia d4 (610 chars)


def doc_de_nombre(nombre):
    """Devuelve (doc, ref) o (None, None) si no se puede deducir con seguridad."""
    n = nombre.lower()
    if n.endswith(".txt"):
        n = n[:-4]
    # orden importa: los tokens largos primero
    for doc in sorted(REF_POR_DOC, key=len, reverse=True):
        if doc in n:
            # 'escaneado_d1' no debe capturar 'escaneado_d1x'; aqui no los hay
            return doc, REF_POR_DOC[doc]
    # familia d4/d5: TODA usa el texto de d4 (610 chars). `cand_p5_*` son los
    # candidatos de degradacion de B19 y `d4_limpio` es la pagina sin degradar.
    m = re.search(r"(escaneado_d4[a-z]?|patologico_d5[a-z]?|realista_d5[a-z]?"
                  r"|escaneado_d5[a-z]?|abl_[a-z0-9_]+|cand_p5_[a-z0-9]+"
                  r"|d4_limpio|d4_pg[0-9]+)", n)
    if m:
        return m.group(1), "d4"
    if "tipico_texto" in n or "tipico" in n:
        return "tipico", "tipico"
    if "acentos_" in n:
        return "acentos_gs", "acentos_gs"
    return None, None


def main():
    inv = []
    sin_doc = []
    for d, informe in DIRS.items():
        raiz = os.path.join(BENCH, d)
        if not os.path.isdir(raiz):
            continue
        for dp, _, fs in os.walk(raiz):
            for f in fs:
                if not f.endswith(".txt") or f.startswith("log-"):
                    continue
                ruta = os.path.join(dp, f)
                doc, ref = doc_de_nombre(f)
                rel = os.path.relpath(ruta, BENCH).replace("\\", "/")
                if doc is None:
                    sin_doc.append(rel)
                    continue
                inv.append({"rel": rel, "dir": d, "informe": informe,
                            "fichero": f, "doc": doc, "ref": ref,
                            "bytes": os.path.getsize(ruta)})
    resumen = {}
    for e in inv:
        k = (e["dir"], e["ref"])
        resumen[k] = resumen.get(k, 0) + 1
    print("=== ficheros de texto de OCR mapeados: %d ===" % len(inv))
    for (d, r), c in sorted(resumen.items()):
        print("  %-26s ref=%-10s %5d" % (d, r, c))
    print("=== sin documento deducible: %d ===" % len(sin_doc))
    for s in sin_doc[:40]:
        print("  " + s)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventario.json")
    json.dump({"mapeados": inv, "sin_doc": sin_doc}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("-> " + out)


if __name__ == "__main__":
    sys.exit(main())
