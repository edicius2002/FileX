# -*- coding: utf-8 -*-
"""G1 / paso 1 — generador de las candidatas a `escaneado_d4`.

COPIA ADAPTADA de bench/scripts/gen_corpus_ocr.sh (que NO se toca: es arnes
compartido y regenera d1/d2/d3, que son la base de 296 celdas ya medidas).

Diferencias frente al original, todas deliberadas:
  1. La pagina maestra se renderiza a 600 ppp (3882x5376) en vez de 300, para que
     una variante a 200 ppp NATIVOS siga siendo una REDUCCION (x3) y no una
     ampliacion. Condicion (a) del encargo: ppp nativos >= 200.
  2. El texto es castellano con tildes y tres tamaños de letra (24/11/7 pt), no
     tres frases mayusculas. Condiciones (b) y (c).
  3. Se genera un CONTROL SIN DEGRADAR (`d4_limpio`) que no va al corpus: sirve
     para comprobar que el fallo que se mida viene de la degradacion y no de la
     tipografia ni del propio texto.
  4. Se escribe en Python y no en shell porque los heredocs de este entorno se
     comen los backslashes y porque hay que pasar UTF-8 a magick sin que la
     consola de Windows lo destroce (trampa 13 de CLAUDE.md).

El ORDEN de la degradacion es el mismo que el del generador original, a proposito:
    rotar -> reducir a los ppp objetivo -> desenfocar -> escala de grises ->
    +level (bajar contraste) -> ruido gaussiano -> JPEG
El ruido va DESPUES del +level para que la compresion de rango no lo recorte.

uso: python gen_corpus_d4.py [nombre ...]     (sin argumentos: todas)
"""
import hashlib
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from d4_texto import ALTO, ANCHO, MAQUETA, MARGEN_X, pt  # noqa: E402

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
RAIZ = r"D:\Work\research\FileX"
TMP = os.path.join(RAIZ, r"bench\salidas-corpus-d4\tmp")
OUT_PDF = os.path.join(RAIZ, r"corpus\pdf")
MAESTRO = os.path.join(TMP, "d4_master.png")
SEMILLA = 20260821            # semilla fija del ruido gaussiano: reproducibilidad

# nombre        ppp  angulo ruido  nivel(+level)  blur  jpegq
CANDIDATAS = [
    ("d4_limpio", 200,   0,  0.00, None,          0.0,  95),   # control, NO va al corpus
    ("escaneado_d4a", 200,   2,  0.20, "12%,90%",  0.4,  60),
    ("escaneado_d4b", 200,  -3,  0.35, "20%,84%",  0.8,  45),
    ("escaneado_d4c", 200,   3,  0.50, "28%,78%",  1.2,  32),
    # d4d fue la ganadora del cribado y pasa a llamarse `escaneado_d4`: es LA
    # candidata canonica. Sus parametros son exactamente los de la fila d4d.
    ("escaneado_d4", 200,  -4,  0.65, "34%,72%",  1.6,  24),
    ("escaneado_d4e", 200,   4,  0.80, "40%,68%",  2.0,  18),
    ("escaneado_d4f", 240,   3,  0.55, "30%,76%",  1.4,  28),
    # --- ablacion de UN factor cada vez, partiendo de d4d. No van al corpus:
    # sirven para saber QUE perilla de degradacion rompe el OCR, que es lo que
    # convierte el barrido en una medida y no en una coleccion de imagenes feas.
    ("abl_d4d_blur12", 200,  -4, 0.65, "34%,72%",  1.2,  24),   # menos desenfoque
    ("abl_d4d_jq45",   200,  -4, 0.65, "34%,72%",  1.6,  45),   # menos JPEG
    ("abl_d4d_niv20",  200,  -4, 0.65, "20%,84%",  1.6,  24),   # mas contraste
    ("abl_d4d_rui35",  200,  -4, 0.35, "34%,72%",  1.6,  24),   # menos ruido
    ("abl_d4d_ang0",   200,   0, 0.65, "34%,72%",  1.6,  24),   # sin rotacion
]


def run(args):
    p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    if p.returncode != 0:
        raise SystemExit(f"magick fallo ({p.returncode}): {p.stderr[:400]}")
    return p.stdout.strip()


def render_maestro():
    args = [MAGICK, "-size", f"{ANCHO}x{ALTO}", "xc:white", "-fill", "black",
            "-gravity", "NorthWest"]
    for _etq, fuente, tam, y0, inter, lineas in MAQUETA:
        args += ["-font", fuente, "-pointsize", str(pt(tam))]
        for k, linea in enumerate(lineas):
            args += ["-annotate", f"+{MARGEN_X}+{y0 + k * inter}", linea]
    args += [MAESTRO]
    run(args)
    return run([MAGICK, "identify", "-format", "%wx%h", MAESTRO])


def variante(nom, ppp, ang, ruido, nivel, blur, jq):
    w = ANCHO * ppp // 600
    jpg = os.path.join(TMP, nom + ".jpg")
    pdf = os.path.join(OUT_PDF if nom.startswith("escaneado_") else TMP, nom + ".pdf")
    # -seed FIJO: sin el, `+noise Gaussian` usa una semilla aleatoria y el fichero
    # NO es reproducible. Es la diferencia entre un MANIFIESTO que se puede
    # comprobar y uno que solo se puede creer.
    args = [MAGICK, "-seed", str(SEMILLA), MAESTRO,
            "-background", "white", "-rotate", str(ang),
            "-resize", f"{w}x"]
    if blur:
        args += ["-blur", f"0x{blur}"]
    args += ["-colorspace", "Gray"]
    if nivel:
        args += ["+level", nivel]
    if ruido:
        args += ["-attenuate", str(ruido), "+noise", "Gaussian"]
    args += ["-quality", str(jq), jpg]
    run(args)
    run([MAGICK, jpg, "-units", "PixelsPerInch", "-density", str(ppp), pdf])
    dim = run([MAGICK, "identify", "-format", "%wx%h", jpg])
    b = os.path.getsize(pdf)
    sha = hashlib.sha256(open(pdf, "rb").read()).hexdigest()
    print(f"{nom:16s} ppp={ppp:3d} ang={ang:3d} ruido={ruido:.2f} "
          f"nivel={str(nivel):10s} blur={blur:.1f} jq={jq:3d}  px={dim:10s} "
          f"bytes={b:7d}  sha256={sha[:16]}")
    return {"nombre": nom, "pdf": pdf, "ppp": ppp, "px": dim, "bytes": b, "sha256": sha}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(TMP, exist_ok=True)
    print("maestro:", render_maestro())
    quiere = set(sys.argv[1:])
    filas = []
    for c in CANDIDATAS:
        if quiere and c[0] not in quiere:
            continue
        filas.append(variante(*c))
    import json
    json.dump(filas, open(os.path.join(TMP, "..", "json", "candidatas.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=2)
