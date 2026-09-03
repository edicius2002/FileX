# -*- coding: utf-8 -*-
"""C46 -- las dos guardas que le faltan al acuerdo `spa`/`eng` (bench/acuerdo-y-cruce.md
sec.2, refutado 2/8; el mismo metodo, con las dos guardas puestas).

Copia de `bench/salidas-acuerdo-y-cruce/_c20_acuerdo.py` (arnes de la ronda 7, NO se
edita ahi -- es de otro carril) con dos anadidos, tal como los nombra el propio informe:

  1. GUARDA_TOKENS_MIN: longitud minima no vacia, mismo patron que
     `filex/verificador.py:5383` (`P9_TOKENS_MIN = 8`, "por debajo, la estadistica no se
     sostiene"). Si `spa` o `eng` normalizados tienen menos tokens que el umbral, el
     veredicto es "no_aplica", no un acuerdo fabricado sobre practicamente nada.
  2. `acuerdo_ponderado`: distancia de edicion (Levenshtein, alineamiento completo, no
     difflib.SequenceMatcher) con coste de SUSTITUCION reducido (0,3 en vez de 1,0) cuando
     alguno de los dos caracteres alineados es una vocal acentuada o `n`/`ñ` -- para que
     "o"->"e" en `sol`/`sel` siga costando 1,0 (dos letras SIN tilde, discrepancia real) pero
     "o"->"e" en `sensación`vs`sensacién no cuente como caracter arbitrariamente distinto.
     NO es difflib con NFC/NFKD (eso ya se probo en la ronda 7 y no sube el acuerdo de
     `d4a` de 0,735): es una metrica distinta, calculada aqui.

Metodo identico al de la ronda 7, sin variarlo (mismo Tesseract 5.5.0 STANDALONE dentro de
`filex-c13`, mismos 8 documentos, mismos ppp nativos, mismo `--psm 3` fijo, misma referencia
acentuada de `bench/scripts/ocr_eval.py::norm_acentos` para el CER):

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-c46-guardas/_c46_guardas.py
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

# --- guarda 1: longitud minima no vacia (patron de P9_TOKENS_MIN) -----------
GUARDA_TOKENS_MIN = 8  # mismo valor que filex/verificador.py:5383 (P9_TOKENS_MIN)

# --- guarda 2: coste de sustitucion reducido para caracteres acentuados -----
COSTE_SUST_ACENTO = 0.3   # sustitucion donde uno de los dos lados es acentuado
COSTE_SUST_NORMAL = 1.0
COSTE_INDEL = 1.0
_ACENTOS_SET = set("áéíóúüñ")  # ya en minuscula: norm_acentos() normaliza antes

# --- referencias, copiadas de las fuentes unicas del proyecto (no se editan aqui, solo
# se citan): bench/scripts/ocr_eval.py (LEGADO) y bench/salidas-corpus-d4/d4_texto.py (D4).
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


def lev_ponderado(a: str, b: str) -> float:
    """Levenshtein con coste de sustitucion reducido cuando uno de los dos
    caracteres alineados es una letra acentuada (incluye n~/n~). Insercion y
    borrado SIEMPRE cuestan 1,0 -- solo la sustitucion se abarata, porque solo
    la sustitucion es la que castiga 'o'->'e' como si fueran dos letras
    arbitrarias."""
    if a == b:
        return 0.0
    if not a:
        return float(len(b))
    if not b:
        return float(len(a))
    prev = [j * COSTE_INDEL for j in range(len(b) + 1)]
    for i, ca in enumerate(a, 1):
        cur = [i * COSTE_INDEL]
        for j, cb in enumerate(b, 1):
            if ca == cb:
                c_sust = 0.0
            elif ca in _ACENTOS_SET or cb in _ACENTOS_SET:
                c_sust = COSTE_SUST_ACENTO
            else:
                c_sust = COSTE_SUST_NORMAL
            cur.append(min(prev[j] + COSTE_INDEL,
                            cur[j - 1] + COSTE_INDEL,
                            prev[j - 1] + c_sust))
        prev = cur
    return prev[-1]


def acuerdo_ponderado(a: str, b: str) -> float:
    """1 - distancia_ponderada / max(len(a), len(b)); acotado a [0, 1] porque
    el coste de cualquier operacion es <= 1,0 (la distancia ponderada nunca
    supera al Levenshtein sin ponderar, que a su vez esta acotado por
    max(len(a), len(b)))."""
    m = max(len(a), len(b))
    if m == 0:
        return 1.0
    return round(1.0 - lev_ponderado(a, b) / m, 3)


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
    # Misma disciplina que _c20_acuerdo.py: --init (si no, timeout queda de PID 1 y
    # docker run da rc=125 sin ejecutar nada); --workdir + rutas relativas (con rutas
    # absolutas tesseract fallaba con "could not create TXT output file").
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

        n_spa = norm_acentos(t_spa)
        n_eng = norm_acentos(t_eng)
        tok_spa = len(n_spa.split())
        tok_eng = len(n_eng.split())

        acuerdo_viejo = round(difflib.SequenceMatcher(None, t_spa, t_eng).ratio(), 3)
        acuerdo_nuevo = acuerdo_ponderado(n_spa, n_eng)

        guarda1_no_aplica = tok_spa < GUARDA_TOKENS_MIN or tok_eng < GUARDA_TOKENS_MIN
        if guarda1_no_aplica:
            veredicto = "no_aplica"
            motivo = ("tok_spa=%d o tok_eng=%d por debajo de GUARDA_TOKENS_MIN=%d: "
                       "el acuerdo no se sostiene (patron de P9_TOKENS_MIN, "
                       "filex/verificador.py:5383)" % (tok_spa, tok_eng, GUARDA_TOKENS_MIN))
        elif acuerdo_nuevo >= 0.80:
            veredicto = "bueno"
            motivo = None
        elif acuerdo_nuevo <= 0.70:
            veredicto = "ruido"
            motivo = None
        else:
            veredicto = "banda"
            motivo = "acuerdo en 0,70-0,80: zona sin decidir, igual que P3 original"

        cer_spa = cer_acentuado(t_spa, cfg["ref"])
        cer_eng = cer_acentuado(t_eng, cfg["ref"])

        fila = {
            "documento": nombre, "ppp": cfg["ppp"],
            "acuerdo_viejo_difflib": acuerdo_viejo,
            "acuerdo_nuevo_ponderado": acuerdo_nuevo,
            "tok_spa": tok_spa, "tok_eng": tok_eng,
            "veredicto_con_guardas": veredicto, "motivo": motivo,
            "cer_spa_pct": cer_spa, "cer_eng_pct": cer_eng,
            "ms_spa": round(ms_spa, 1), "ms_eng": round(ms_eng, 1),
            "chars_spa": len(t_spa), "chars_eng": len(t_eng),
        }
        filas.append(fila)
        print("%-24s ppp=%-4d viejo=%.3f nuevo=%.3f tok(spa=%d,eng=%d) -> %-9s "
              "CER spa=%6.2f%% eng=%7.2f%%"
              % (nombre, cfg["ppp"], acuerdo_viejo, acuerdo_nuevo, tok_spa, tok_eng,
                 veredicto, cer_spa, cer_eng))

    with open(os.path.join(SAL, "acuerdo_c46.json"), "w", encoding="utf-8") as fh:
        json.dump(filas, fh, indent=1, ensure_ascii=False)
    print("escrito acuerdo_c46.json")


if __name__ == "__main__":
    main()
