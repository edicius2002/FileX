# -*- coding: utf-8 -*-
"""G5 / B11 — evalua el A/B de configuracion de RapidOCR y publica el SALDO.

Usa el evaluador CANONICO del proyecto, `bench/scripts/ocr_eval.py`, importado y
no copiado: desde el 2026-08-28 su lectura canonica es la ACENTUADA y devuelve la
clave `metrica` en cada celda. Aqui se propaga esa clave a cada fila, porque una
tabla de CER sin su evaluador no se puede juntar con otra (trampa 55).

Dos referencias, y no son intercambiables:
  * `legado`  los 79 caracteres de `ocr_eval.ESPERADO`. **Sin un solo
              diacritico**: cuantiza a 1,27 puntos por caracter (trampa 9) y por
              construccion las dos metricas dan lo mismo (trampa 56).
  * `d4`      los ~610 caracteres con tildes de `d4_texto.BLOQUES`, que es la
              FUENTE UNICA que comparten el generador del corpus y el evaluador.

uso: evaluar_b11.py <dir_salidas> <etiqueta_A> <etiqueta_B> [salida.json]
"""
import json
import os
import sys

RAIZ = r"D:\Work\research\FileX\.claude\worktrees\agent-a4c547156ef35c38f"
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-corpus-d4"))
import ocr_eval  # noqa: E402
from d4_texto import BLOQUES as D4_BLOQUES  # noqa: E402

REF = {
    "legado": list(ocr_eval.ESPERADO),
    "d4": [linea for lineas in D4_BLOQUES.values() for linea in lineas],
}
# Documentos SIN referencia fiable: se miden contra la capa de texto que el
# propio PDF trae (`gs -sDEVICE=txtwrite`) y quedan FUERA del saldo. Se publican
# igual, marcados, porque un control que se esconde no es un control.
SIN_REF = "sin_referencia_fiable"

salidas = sys.argv[1]
etq_a, etq_b = sys.argv[2], sys.argv[3]
destino = sys.argv[4] if len(sys.argv) > 4 else os.path.join(salidas, "b11_saldo.json")

indice = json.load(open(os.path.join(os.path.dirname(os.path.abspath(salidas)),
                                     "img_b11", "indice.json"), encoding="utf-8"))

filas = []
for entrada in indice:
    if entrada.get("rc") != 0:
        continue
    doc = entrada["doc"]
    fila = {"doc": doc, "ppp_nativos": entrada["ppp_nativos"],
            "mpx": entrada["mpx"], "referencia": entrada["referencia"]}
    for lado, etq in (("a", etq_a), ("b", etq_b)):
        ruta = os.path.join(salidas, f"{etq}__{doc}.txt")
        if not os.path.exists(ruta):
            fila[f"cer_{lado}"] = None
            fila[f"chars_{lado}"] = None
            fila[f"falta_{lado}"] = ruta
            continue
        texto = open(ruta, encoding="utf-8", errors="replace").read()
        fam = entrada["referencia"]
        if fam == SIN_REF:
            capa = os.path.join(os.path.dirname(os.path.abspath(salidas)), "img_b11",
                                f"REFERENCIA-{doc}.txt")
            esperado = [l.strip() for l in
                        open(capa, encoding="utf-8", errors="replace")
                        if l.strip()]
        else:
            esperado = REF[fam]
        r = ocr_eval.evaluar(texto, esperado=esperado)
        fila[f"cer_{lado}"] = r["cer_pct"]
        fila[f"cer_ciego_{lado}"] = r["cer_ciego_pct"]
        fila[f"chars_{lado}"] = r["chars_salida"]
        fila["metrica"] = r["metrica"]
        fila["chars_ref"] = r["chars_ref"]
    if (fila.get("cer_a") is not None and fila.get("cer_b") is not None
            and entrada["referencia"] != SIN_REF):
        fila["delta"] = round(fila["cer_b"] - fila["cer_a"], 2)
        # El paso de la escala manda: con 79 caracteres de referencia un solo
        # caracter vale 1,27 puntos, asi que "mejor/peor" se decide por
        # diferencia ESTRICTA y se anota el paso de la celda.
        fila["paso_pct"] = round(100.0 / max(1, fila["chars_ref"]), 2)
        fila["veredicto"] = ("igual" if fila["delta"] == 0 else
                             ("mejor" if fila["delta"] < 0 else "peor"))
    filas.append(fila)

con = [f for f in filas if f.get("veredicto")]
saldo = {"mejor": sum(1 for f in con if f["veredicto"] == "mejor"),
         "igual": sum(1 for f in con if f["veredicto"] == "igual"),
         "peor": sum(1 for f in con if f["veredicto"] == "peor"),
         "celdas": len(con), "sin_pareja": len(filas) - len(con),
         "metrica": con[0]["metrica"] if con else "?",
         "lado_a": etq_a, "lado_b": etq_b}
if con:
    peores = sorted(con, key=lambda f: -f["delta"])[:3]
    mejores = sorted(con, key=lambda f: f["delta"])[:3]
    saldo["mayor_empeoramiento"] = [(f["doc"], f["delta"]) for f in peores
                                    if f["delta"] > 0]
    saldo["mayor_mejora"] = [(f["doc"], f["delta"]) for f in mejores
                             if f["delta"] < 0]
    saldo["suma_delta"] = round(sum(f["delta"] for f in con), 2)

print(f"{'documento':24s} {'ppp':>4s} {'A':>8s} {'B':>8s} {'delta':>8s}  veredicto")
for f in filas:
    if not f.get("veredicto"):
        a = f"{f['cer_a']:8.2f}" if f.get("cer_a") is not None else f"{'?':>8s}"
        b = f"{f['cer_b']:8.2f}" if f.get("cer_b") is not None else f"{'?':>8s}"
        print(f"{f['doc']:24s} {f['ppp_nativos']:4d} {a} {b} {'-':>8s}  "
              f"FUERA DEL SALDO ({f['referencia']})")
        continue
    print(f"{f['doc']:24s} {f['ppp_nativos']:4d} {f['cer_a']:8.2f} {f['cer_b']:8.2f} "
          f"{f['delta']:+8.2f}  {f['veredicto']}")
print()
print(json.dumps(saldo, ensure_ascii=False, indent=2))

json.dump({"saldo": saldo, "filas": filas}, open(destino, "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("->", destino)
