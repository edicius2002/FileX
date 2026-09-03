# -*- coding: utf-8 -*-
"""C24 -- que --psm usa el Tesseract EMBEBIDO en Ghostscript, sondeado en
ejecucion por HUELLA DE COMPORTAMIENTO (no se puede pasar --psm a `-sDEVICE=ocr`:
no existe ese switch -- MEDIDO, `gswin64c -h` no lo lista y no hay `-dOCR*` para
segmentacion).

Metodo, tal como pide el encargo: bench/psm-y-rasterizador.md 4.4 mide que
`--psm 6` NUNCA cambia con la resolucion (0 de 22 celdas) porque el analisis de
maqueta no entra; `--psm 3/4/11` SI cambian. Esa es una huella distinguible.
Aqui se reproduce la MISMA forma de experimento -- variar la resolucion,
mirar si el CER se mueve -- sobre DOS motores a la vez y con el MISMO
mecanismo de variacion (remuestreo real via `-r`/`-density`, no declaracion de
pHYs sobre pixeles fijos: ese experimento exacto no se puede replicar porque
`-sDEVICE=ocr` rasteriza el PDF el mismo, no admite un PNG con cabecera
mentirosa como entrada). Se declara la diferencia de mecanismo, no se oculta.

Ademas: TRES controles independientes, cada uno en su propia seccion.
  A. Presencia de "Estimating resolution" en stdout/stderr de gs (el aviso de
     Tesseract cuando el analisis de maqueta corre) -- MEDIDO directamente.
  B. La curva de CER de gs a lo largo de la resolucion, comparada con la
     forma (no el valor) de las curvas psm 3/6/11 medidas AQUI MISMO, en la
     misma tanda, con el mismo evaluador.
  C. rc de cada celda -- para no confundir silencio con "no arranco".

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-psm-gs-y-crudos/_huella_psm_gs.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unicodedata

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
TESS = os.path.join(SAL, "tessdata")
TIMEOUT = 90


def _entorno():
    e = dict(os.environ)
    e["TESSDATA_PREFIX"] = TESS
    return e


def gs_ocr_txt(pdf: str, ppp: int, idioma: str) -> tuple[list, int, str, str]:
    """Texto OCR de un PDF con el Tesseract EMBEBIDO de Ghostscript. Copia
    reducida de `bench/salidas-verificador-gs/ocr_gs.py::gs_ocr_txt` (arnes
    ajeno, no se toca ni se importa por sus dependencias hermanas -- se
    reescribe la funcion, que es de 6 lineas)."""
    orden = [GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
            "-sDEVICE=ocr", "-r%d" % ppp, "-sOCRLanguage=" + idioma,
            "-sOutputFile=-", pdf]
    try:
        p = subprocess.run(orden, capture_output=True, timeout=TIMEOUT,
                           stdin=subprocess.DEVNULL, env=_entorno())
    except subprocess.TimeoutExpired:
        return orden, 124, "", "TIMEOUT %ds" % TIMEOUT
    return (orden, p.returncode, p.stdout.decode("utf-8", "replace"),
           p.stderr.decode("utf-8", "replace"))

# escaneado_d2 y d3: los mismos que usa cmd_ppp del arnes de V, nativos 100 ppp
# los dos. Documentos pequenos, rapidos, ya usados en esta linea de trabajo.
DOCS = [("escaneado_d2", "corpus/pdf/escaneado_d2.pdf", 100),
        ("escaneado_d3", "corpus/pdf/escaneado_d3.pdf", 100)]
RESOLUCIONES = [75, 100, 150, 200, 300]

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


REF = {
    "escaneado_d2": "DOCUMENTO ESCANEADO Texto que solo existe como pixeles. Debe recuperarse con OCR.",
    "escaneado_d3": "DOCUMENTO ESCANEADO Texto que solo existe como pixeles. Debe recuperarse con OCR.",
}


def cer(texto: str, doc: str) -> float:
    ref = norm_acentos(REF[doc])
    n = norm_acentos(texto)
    d = lev(ref, n)
    return round(100 * d / max(1, len(ref)), 2)


def rasterizar(pdf: str, ppp: int, destino: str) -> None:
    subprocess.run([MAGICK, "-density", str(ppp), pdf + "[0]",
                    "-units", "PixelsPerInch", "-flatten", destino],
                   stdin=subprocess.DEVNULL, capture_output=True,
                   timeout=TIMEOUT, check=True)


def tess_psm(png: str, psm: int) -> tuple[str, int]:
    base = os.path.splitext(png)[0] + "_psm%d" % psm
    env = dict(os.environ)
    env["TESSDATA_PREFIX"] = TESS
    r = subprocess.run([TESSERACT, png, base, "-l", "spa", "--psm", str(psm)],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=TIMEOUT, env=env)
    p = base + ".txt"
    if r.returncode != 0 or not os.path.isfile(p):
        return "", r.returncode
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read(), r.returncode


def main() -> None:
    filas = []

    # --- A: la linea "Estimating resolution" en gs, sobre el propio PDF -----
    print("=== A. Aviso de analisis de maqueta en la salida de gs ===")
    a_res = {}
    for nombre, rel, nat in DOCS:
        pdf = os.path.join(RAIZ, rel.replace("/", os.sep))
        _, rc, out, err = gs_ocr_txt(pdf, nat, "spa")
        tiene = "Estimating resolution" in (out + err)
        a_res[nombre] = {"rc": rc, "estimating_resolution": tiene,
                         "stderr_muestra": err.strip()[:200]}
        print("  %-16s rc=%d  'Estimating resolution' en salida: %s"
              % (nombre, rc, tiene))
    with open(os.path.join(SAL, "control_a_estimating.json"), "w", encoding="utf-8") as fh:
        json.dump(a_res, fh, indent=1, ensure_ascii=False)

    # --- B: la curva de CER de gs, y de tesseract standalone psm 3/6/11 -----
    print("\n=== B. Curva CER vs resolucion: gs frente a psm 3/6/11 (mismo mecanismo) ===")
    for nombre, rel, nat in DOCS:
        pdf = os.path.join(RAIZ, rel.replace("/", os.sep))
        for res in RESOLUCIONES:
            fila = {"documento": nombre, "res": res, "nativos": nat}
            # gs, remuestreo REAL via -r
            _, rc, out, err = gs_ocr_txt(pdf, res, "spa")
            fila["gs_rc"] = rc
            fila["gs_cer"] = cer(out, nombre)
            fila["gs_chars"] = len(out.strip())
            # tesseract standalone, MISMO mecanismo: magick rasteriza a `res`,
            # tesseract lee ese PNG con psm 3/6/11
            png = os.path.join(SAL, "%s_%dppp.png" % (nombre, res))
            rasterizar(pdf, res, png)
            for psm in (3, 6, 11):
                txt, rc_t = tess_psm(png, psm)
                fila["psm%d_rc" % psm] = rc_t
                fila["psm%d_cer" % psm] = cer(txt, nombre)
                fila["psm%d_chars" % psm] = len(txt.strip())
            filas.append(fila)
            print("  %-16s %3d ppp  gs=%6.2f%%(rc=%d)  psm3=%6.2f%%  psm6=%6.2f%%  psm11=%6.2f%%"
                  % (nombre, res, fila["gs_cer"], rc, fila["psm3_cer"],
                     fila["psm6_cer"], fila["psm11_cer"]))

    with open(os.path.join(SAL, "curva_psm_gs.json"), "w", encoding="utf-8") as fh:
        json.dump(filas, fh, indent=1, ensure_ascii=False)

    # --- resumen: cuanto se mueve cada curva (max-min sobre las 5 resoluciones) ---
    print("\n=== Resumen: recorrido (max-min) de CER por documento y via ===")
    for nombre, _, _ in DOCS:
        sub = [f for f in filas if f["documento"] == nombre]
        for via in ("gs_cer", "psm3_cer", "psm6_cer", "psm11_cer"):
            vals = [f[via] for f in sub]
            print("  %-16s %-10s recorrido=%.2f  (min=%.2f max=%.2f)"
                  % (nombre, via, max(vals) - min(vals), min(vals), max(vals)))

    print("\nescrito control_a_estimating.json y curva_psm_gs.json")


if __name__ == "__main__":
    main()
