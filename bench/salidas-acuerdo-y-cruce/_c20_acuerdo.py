# -*- coding: utf-8 -*-
"""C20 -- valida el acuerdo entre dos idiomas de OCR FUERA de Ghostscript.

`bench/contrato-quinto-punto.md` sec.6.3 midio el sustituto de P9 (el acuerdo
`spa`/`eng` de un mismo documento, via difflib) sobre Ghostscript y su
Tesseract EMBEBIDO, con separacion perfecta 16/16 y banda vacia de 0,19.
Dejo dos PENDIENTES explicitos: validarlo fuera de Ghostscript (misma trampa
78 que ya midio A7: un umbral calibrado con un solo motor describe a ese
motor) y sobre vocabulario que `eng` no comparta.

Aqui: Tesseract 5.5.0 ESTANDALONE, dentro del contenedor `filex-c13`, no el
Tesseract compilado DENTRO de `gswin64c.exe` que uso la medida original --
proceso, binario y `tessdata` distintos (Debian `tesseract-ocr-spa/-eng`
frente a lo que traiga `gs`). Documentos: los cuatro legado (sin tildes, la
misma referencia de 79 caracteres) mas la familia `escaneado_d4` (castellano
CON tildes, 610 caracteres, vocabulario que `eng` no comparte una sola
palabra con el ingles).

Metodo: magick rasteriza a ppp NATIVOS (trampa 6 de CLAUDE.md: no
sobremuestrear). Dos pasadas de tesseract por documento, `--psm 3` (el
`--oem`/`--psm` por defecto: no es el objeto de esta medida, y variarlo
mezclaria dos preguntas -- trampa 78 de nuevo, aplicada al PROPIO arnes).
Acuerdo = difflib.SequenceMatcher(None, spa, eng).ratio(). Verdad = CER
acentuado (bench/scripts/ocr_eval.py) del texto `spa` contra la referencia.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-acuerdo-y-cruce/_c20_acuerdo.py
"""
from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAL = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(RAIZ, "corpus", "pdf")
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
IMAGEN = "filex-c13:latest"
TOPE_S = 60

# --- referencias, copiadas de las fuentes unicas del proyecto (no se editan
# aqui, solo se citan): bench/scripts/ocr_eval.py (LEGADO) y
# bench/salidas-corpus-d4/d4_texto.py (D4, con tildes).
LEGADO = ["DOCUMENTO ESCANEADO", "Texto que solo existe como pixeles.",
          "Debe recuperarse con OCR."]
D4_REF = [
    "INFORME DE DIGITALIZACIÓN",
    "Expediente núm. 4.827/2026 - Archivo Histórico",
    "El día 14 de marzo se recibió la solicitud de análisis",
    "técnico sobre veintiún volúmenes encuadernados en piel.",
    "La comisión determinó que la reproducción fotográfica",
    "debía realizarse con iluminación difusa y sin contacto,",
    "según la norma UNE 15-402, para evitar daños añadidos",
    "en los pliegos más frágiles del año 1893.",
    "¿Quién autorizó la excepción? El párrafo tercero señala",
    "que la revisión ortográfica y lingüística del legajo",
    "es responsabilidad del área de conservación preventiva.",
    "¡Atención! Los códigos 7-B, 9-Ñ y 12-K quedan anulados.",
]

DOCUMENTOS = {
    "patologico_escaneado": {"ppp": 200, "ref": LEGADO},
    "escaneado_d1":         {"ppp": 150, "ref": LEGADO},
    "escaneado_d2":         {"ppp": 100, "ref": LEGADO},
    "escaneado_d3":         {"ppp": 100, "ref": LEGADO},
    "escaneado_d4a":        {"ppp": 200, "ref": D4_REF},
    "escaneado_d4c":        {"ppp": 200, "ref": D4_REF},
    "escaneado_d4":         {"ppp": 200, "ref": D4_REF},
    "escaneado_d4e":        {"ppp": 200, "ref": D4_REF},
}

_ACENTOS = "áéíóúüñ"


def norm_acentos(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"[^a-z0-9" + _ACENTOS + r" ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def lev(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer_acentuado(texto: str, ref_lineas: list[str]) -> float:
    ref = norm_acentos(" ".join(ref_lineas))
    n = norm_acentos(texto)
    d = lev(ref, n)
    return round(100 * d / max(1, len(ref)), 2)


def rasterizar(nombre: str, ppp: int) -> str:
    pdf = os.path.join(CORPUS, nombre + ".pdf")
    png = os.path.join(SAL, "%s_%dppp.png" % (nombre, ppp))
    if os.path.isfile(png):
        return png
    subprocess.run([MAGICK, "-density", str(ppp), pdf + "[0]",
                    "-units", "PixelsPerInch", "-flatten", png],
                   stdin=subprocess.DEVNULL, capture_output=True,
                   timeout=TOPE_S, check=True)
    return png


def tesseract_en_contenedor(png: str, lang: str) -> tuple[str, float]:
    # `--init`: sin el, `timeout` queda de PID 1 y `docker run` da rc=125 SIN
    # ejecutar nada -- CLAUDE.md, hallazgo del 28/08. `--workdir /work` +
    # RUTAS RELATIVAS: con rutas absolutas (`/work/x.png`) tesseract fallaba
    # con "could not create TXT output file", reproducido 3 veces seguidas;
    # con `--workdir` y el nombre pelado funciona siempre. No investigado
    # mas alla -- dos intentos, se documenta y se sigue (CLAUDE.md sec.3).
    base = os.path.splitext(os.path.basename(png))[0] + "_" + lang
    t0 = time.perf_counter()
    r = subprocess.run(
        ["docker", "run", "--rm", "--init", "--entrypoint", "timeout",
         "--workdir", "/work", "-v", "%s:/work" % SAL, IMAGEN,
         "-k", "5", str(TOPE_S),
         "tesseract", os.path.basename(png), base, "-l", lang, "--psm", "3"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
        timeout=TOPE_S + 15)
    ms = (time.perf_counter() - t0) * 1000
    salida = os.path.join(SAL, base + ".txt")
    if r.returncode != 0 or not os.path.isfile(salida):
        return "", ms
    with open(salida, encoding="utf-8", errors="replace") as fh:
        return fh.read(), ms


def main() -> None:
    filas = []
    for nombre, cfg in DOCUMENTOS.items():
        png = rasterizar(nombre, cfg["ppp"])
        t_spa, ms_spa = tesseract_en_contenedor(png, "spa")
        t_eng, ms_eng = tesseract_en_contenedor(png, "eng")
        acuerdo = round(difflib.SequenceMatcher(None, t_spa, t_eng).ratio(), 3)
        cer_spa = cer_acentuado(t_spa, cfg["ref"])
        cer_eng = cer_acentuado(t_eng, cfg["ref"])
        fila = {
            "documento": nombre, "ppp": cfg["ppp"], "acuerdo_spa_eng": acuerdo,
            "cer_spa_pct": cer_spa, "cer_eng_pct": cer_eng,
            "ms_spa": round(ms_spa, 1), "ms_eng": round(ms_eng, 1),
            "chars_spa": len(t_spa), "chars_eng": len(t_eng),
        }
        filas.append(fila)
        print("%-24s ppp=%-4d acuerdo=%.3f  CER spa=%6.2f%%  CER eng=%7.2f%%"
              % (nombre, cfg["ppp"], acuerdo, cer_spa, cer_eng))

    with open(os.path.join(SAL, "acuerdo_c20.json"), "w", encoding="utf-8") as fh:
        json.dump(filas, fh, indent=1, ensure_ascii=False)
    print("escrito acuerdo_c20.json")


if __name__ == "__main__":
    main()
