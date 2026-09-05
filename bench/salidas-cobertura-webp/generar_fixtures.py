"""Reproduce los TRECE blobs de `pruebas/fixtures_cob_webp.py` desde cero.

Es la «orden exacta que los reproduce» que pide `CLAUDE.md` §6, en forma de
script en vez de prosa: al terminar compara el `sha256` de cada fichero con el
que declara el manifiesto del módulo de fixtures y **falla si alguno se mueve**.

    python bench/salidas-cobertura-webp/generar_fixtures.py [directorio]

Entorno con el que se midió: `magick` 7.1.2-21 Q16-HDRI con **libwebp 1.6.0**
(`magick -list format | grep WEBP`). Un libwebp distinto puede elegir otras
transformaciones y mover los bytes: si eso pasa, el script lo dirá con el
`sha256` en la mano en vez de dejar pasar unos fixtures que ya no son los que
midió `bench/cobertura-webp.md`.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "pruebas"))


def m(*args: str) -> None:
    subprocess.run(["magick", *args], check=True, capture_output=True)


def generar(d: str) -> dict[str, str]:
    """Devuelve {nombre del blob: ruta}. Cada bloque deja escrito de dónde sale
    la imagen de origen: el WebP lo escribe libwebp, no este script."""
    r = lambda *p: os.path.join(d, *p)                        # noqa: E731

    # --- semilla común: degradado de 24x16 con el alfa cayendo de 255 a 0 ---
    m("-size", "24x16", "gradient:#FF0000FF-#0000FF00", "-depth", "8",
      "PNG32:" + r("g.png"))
    m(r("g.png"), "-alpha", "off", "-define", "webp:lossless=true", r("LL_OPACO.webp"))
    m(r("g.png"), "-define", "webp:lossless=false",
      "-define", "webp:alpha-compression=0", "-quality", "80",
      r("PERDIDA_ALPH_CRUDO.webp"))
    m(r("g.png"), "-define", "webp:lossless=false",
      "-define", "webp:alpha-filtering=2", "-quality", "80",
      r("PERDIDA_ALPH_VP8L.webp"))
    m(r("g.png"), "-alpha", "off", "-define", "webp:lossless=false",
      "-quality", "80", r("PERDIDA_SIN_ALFA.webp"))

    # --- tres colores planos: la paleta sale empaquetada a 8 índices por byte -
    m("-size", "8x8", "xc:#FF0000FF", "-size", "8x8", "xc:#00FF0080", "+append",
      "-size", "16x8", "xc:#0000FF00", "-append", "-depth", "8",
      "PNG32:" + r("pal.png"))
    m(r("pal.png"), "-define", "webp:lossless=true",
      r("LL_PALETA_EMPAQUETADA.webp"))

    # --- plasma de 32x32 con alfa constante: dispara la imagen meta-Huffman ---
    m("-seed", "1", "-size", "32x32", "plasma:fractal", "-depth", "8",
      "-alpha", "set", "-channel", "A", "-evaluate", "set", "50%", "+channel",
      "PNG32:" + r("pl.png"))
    m(r("pl.png"), "-define", "webp:lossless=true", r("LL_META_HUFFMAN.webp"))

    # --- damero de 64x64 con rampa de alfa ---
    m("-size", "64x64", "pattern:checkerboard", "-depth", "8", "-alpha", "set",
      "-channel", "A", "-fx", "j/h", "+channel", "PNG32:" + r("ck.png"))
    m(r("ck.png"), "-define", "webp:lossless=true", r("LL_DAMERO.webp"))

    # --- degradado ondulado: predictor + color cruzado + restar verde ---
    # OJO: `-wave 8x16` sube el alto de 48 a 64, y por eso el fixture es 48x64.
    m("-size", "48x48", "gradient:#FF00FFFF-#00FFFF00", "-wave", "8x16",
      "-depth", "8", "PNG32:" + r("wv.png"))
    m(r("wv.png"), "-define", "webp:lossless=true", r("LL_TRANSFORMACIONES.webp"))

    # --- 24 colores: paleta con bits=0, un índice por píxel ---
    m("-seed", "1", "-size", "32x32", "xc:", "+noise", "Random",
      "-colors", "24", "-depth", "8", "-alpha", "set", "-channel", "A",
      "-evaluate", "set", "40%", "+channel", "PNG32:" + r("p24.png"))
    m(r("p24.png"), "-define", "webp:lossless=true", r("LL_PALETA_ANCHA.webp"))

    # --- alfa diagonal, con pérdida ---
    m("-size", "32x32", "gradient:#FFFFFFFF-#000000FF", "-depth", "8",
      "-alpha", "set", "-channel", "A", "-fx", "(i+j)/(w+h)", "+channel",
      "PNG32:" + r("dg.png"))
    m(r("dg.png"), "-quality", "75", "-define", "webp:lossless=false",
      r("PERDIDA_ALPH_DIAG.webp"))

    # --- con pérdida y alfa totalmente opaco ---
    m("-size", "20x1", "gradient:#000000FF-#FFFFFFFF", "-scale", "20x20!",
      "-depth", "8", "PNG32:" + r("g20.png"))
    m(r("g20.png"), "-quality", "90", "-define", "webp:lossless=false",
      "-define", "webp:alpha-quality=100", r("PERDIDA_ALPH_OPACO.webp"))

    # --- animado de DOS fotogramas ---
    m("-size", "8x8", "xc:red", "-size", "8x8", "xc:blue", "-delay", "10",
      "-loop", "0", r("ANIMADO.webp"))

    # --- el reproductor del defecto del predictor 13 -----------------------
    # Salió de un barrido de 24x24 x 40 semillas buscando la primera imagen en
    # la que el defecto mueve `alfa_min` (bench/cobertura-webp.md §4). La
    # semilla 24 es la que se quedó; el alfa va en una banda estrecha para que
    # el predictor trabaje en vez de copiar.
    m("-seed", "24", "-size", "24x24", "plasma:fractal", "-depth", "8",
      "PNG24:" + r("d_c.png"))
    m("-seed", "524", "-size", "24x24", "plasma:fractal", "-colorspace", "Gray",
      "-evaluate", "Multiply", "0.35", "-evaluate", "Add", "25%", "-depth", "8",
      r("d_m.png"))
    m(r("d_c.png"), r("d_m.png"), "-alpha", "off", "-compose", "CopyOpacity",
      "-composite", "-depth", "8", "PNG32:" + r("d_r.png"))
    m(r("d_r.png"), "-define", "webp:lossless=true", r("DEFECTO_MODO13.webp"))

    return {n[:-5]: r(n) for n in os.listdir(d) if n.endswith(".webp")}


def main() -> int:
    import fixtures_cob_webp as F
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "regenerado")
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    os.makedirs(destino)
    hechos = generar(destino)
    malos = []
    for nombre, (tam, sha) in F.MANIFIESTO.items():
        if nombre not in hechos:
            malos.append("%s: no se generó" % nombre)
            continue
        b = open(hechos[nombre], "rb").read()
        got = hashlib.sha256(b).hexdigest()
        estado = "OK" if got == sha else "DISTINTO"
        print("%-24s %6d B  %s  %s" % (nombre, len(b), got[:16], estado))
        if got != sha:
            malos.append("%s: esperaba %s y salió %s (%d B frente a %d)"
                         % (nombre, sha[:16], got[:16], len(b), tam))
    if malos:
        print("\nNO REPRODUCE:")
        for x in malos:
            print("  -", x)
        return 1
    print("\nlos %d fixtures reproducen su sha256" % len(F.MANIFIESTO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
