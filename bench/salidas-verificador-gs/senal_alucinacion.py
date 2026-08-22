#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HALLAZGO: el verificador declara OK la reparacion por OCR de escaneado_d3,
que es ruido puro.

La cadena es: la regla P5 de referencia.json dice "si la entrada no tiene capa
de texto, no se exige texto en la salida", y la P6 solo exige >= 10 caracteres
imprimibles, umbral calibrado contra la basura de 1-3 caracteres de `txtwrite`.
El OCR alucinado de d3 produce 75 caracteres: pasa el umbral con holgura.

Aqui se busca una senal BARATA y EN PROCESO que separe "texto recuperado" de
"ruido con forma de texto", sobre las cuatro capas OCR realmente producidas.
"""
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
import verificador as V                                      # noqa: E402

VOCALES = set("aeiouaeiouu")


def senales(texto):
    tk = [t for t in re.split(r"[^0-9A-Za-zÀ-ÿ]+", texto) if t]
    if not tk:
        return {"tokens": 0}
    largos = [len(t) for t in tk]
    con_vocal = sum(1 for t in tk if set(t.lower()) & VOCALES)
    de_1 = sum(1 for t in tk if len(t) == 1)
    return {"tokens": len(tk),
            "chars": sum(largos),
            "long_media": round(sum(largos) / len(tk), 2),
            "pct_tokens_de_1_letra": round(100 * de_1 / len(tk), 1),
            "pct_tokens_con_vocal": round(100 * con_vocal / len(tk), 1),
            "pct_tokens_de_3_o_mas": round(
                100 * sum(1 for t in tk if len(t) >= 3) / len(tk), 1)}


def main():
    docs = ["patologico_escaneado", "escaneado_d1", "escaneado_d2", "escaneado_d3"]
    filas = []
    for d in docs:
        pdf = os.path.join(AQUI, "ocr", "%s_ocr_spa.pdf" % d)
        if not os.path.exists(pdf):
            continue
        t, e = V._gs_texto(pdf)
        s = senales(t or "")
        s["documento"] = d
        s["p6_pasa_umbral_10"] = len("".join((t or "").split())) >= V.TEXTO_MIN_CHARS
        s["muestra"] = (t or "").strip()[:70].replace("\n", " | ")
        filas.append(s)
        print("%-22s tokens=%-4d long_media=%-5.2f 1letra=%5.1f%% con_vocal=%5.1f%% "
              ">=3letras=%5.1f%%  P6=%s"
              % (d, s["tokens"], s["long_media"], s["pct_tokens_de_1_letra"],
                 s["pct_tokens_con_vocal"], s["pct_tokens_de_3_o_mas"],
                 s["p6_pasa_umbral_10"]))
    # control: la capa de texto REAL de un PDF que si lo tiene
    t, e = V._gs_texto(os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf"))
    s = senales(t or "")
    s["documento"] = "tipico_texto.pdf (capa de texto REAL, control)"
    s["p6_pasa_umbral_10"] = True
    filas.append(s)
    print("%-22s tokens=%-4d long_media=%-5.2f 1letra=%5.1f%% con_vocal=%5.1f%% "
          ">=3letras=%5.1f%%  P6=True"
          % ("CONTROL tipico_texto", s["tokens"], s["long_media"],
             s["pct_tokens_de_1_letra"], s["pct_tokens_con_vocal"],
             s["pct_tokens_de_3_o_mas"]))
    with open(os.path.join(AQUI, "senal_alucinacion.json"), "w",
              encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=1)
    print("-> senal_alucinacion.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
