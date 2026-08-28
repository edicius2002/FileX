# -*- coding: utf-8 -*-
"""C30 / paso 3 - CIERRE: adjudica cada `fallo` y deja el JSON publicable.

`n_falsos_positivos` que sale del arnes cuenta TODO `fallo` sobre un fichero
escrito, y eso mezcla dos cosas que no son la misma: una salida legitima que el
contrato rechaza (falso positivo, que es lo que se venia a contar) y una salida
que el motor escribio en otro formato del que se le pidio (captura legitima, que
es para lo que existe el contrato). La separacion NO se deduce: la decide el
testigo externo de `_c30_triaje.py` -- que otro motor reconozca, o no, el
formato pedido.

Uso (en Windows, sobre el directorio desechable de la tanda):
  python bench/salidas-firmas-cierre/_c30_cierra.py <dir_desechable>
"""
import json
import os
import sys
from collections import Counter

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEST = os.path.join(RAIZ, "bench", "salidas-firmas-cierre")

# La adjudicacion, destino a destino, CON la evidencia que la sostiene. No es
# una opinion del arnes: cada linea cita al testigo externo que la decide.
ADJUDICA = {
    ("graphicsmagick", "mpc"): (
        "falso_positivo",
        "GraphicsMagick escribe `id=MagickCache` y la tabla FIRMAS solo trae el "
        "`id=MagickPixelCache` de ImageMagick. TESTIGO: `gm identify` -> "
        "`MPC 64x48+0+0 DirectClass 16-bit`. El censo del vocabulario se hizo con "
        "ImageMagick, y GM usa otro literal para la misma extension. "
        "Arreglo de una linea: anadir (0, b'id=MagickCache', 'mpc')."),
    ("graphicsmagick", "pcx"): (
        "falso_positivo",
        "El predicado de PCX exige `cab[2] == 1` (codificacion RLE) y GM escribe "
        "PCX SIN COMPRIMIR: el byte 2 vale 0x00 (cabecera medida "
        "`0a 05 00 08 ...`). TESTIGO: `magick identify` -> `PCX 64x48 8-bit` y "
        "`gm identify` -> `PCX 64x48+0+0 DirectClass 8-bit`. "
        "Arreglo de una linea: `cab[2] in (0, 1)`."),
    ("vips", "vips"): (
        "falso_positivo",
        "El magico de VIPS es de ENDIANNESS y la tabla solo trae una mitad: "
        "FIRMAS declara `08 f2 a6 b6` (big-endian) y vips 8.18.3 en x86 escribe "
        "`b6 a6 f2 08`. TESTIGO: `magick identify` -> `VIPS 64x48 16-bit`. "
        "Arreglo de una linea: anadir (0, b'\\xb6\\xa6\\xf2\\x08', 'vips')."),
    ("vips", "mat"): (
        "falso_positivo",
        "COLISION DE EXTENSION, no laguna de firma: `.mat` son dos formatos. La "
        "tabla espera `MATLAB 5.0` y vips escribe su MATRIZ ASCII "
        "(`64 48\\n57847 52168 ...`). TESTIGOS: `vipsheader` -> "
        "`64x48 double, 1 band, b-w, matrixload` y el round-trip "
        "`vips copy m.mat back.png` sale rc=0; ImageMagick y GM lo rechazan los "
        "dos. Ninguna firma puede decidir cual de los dos se pidio: es el caso "
        "`.avs` que EXT_SIN_FIRMA ya documenta, con otro par de motores."),
    ("graphicsmagick", "x"): (
        "captura_legitima",
        "La salida es un PNG con extension `.x` (cabecera `89 50 4e 47`, "
        "`magick identify` -> `PNG 64x48 16-bit`): GM no reconocio la extension y "
        "conservo el formato de la entrada. Es EL fallo emblematico del proyecto, "
        "y lo atrapa G3 y no G6 -- porque `.x` SI esta en el vocabulario, como el "
        "`directx_x` que escribe assimp. Dos motores del mismo contenedor se "
        "reparten la misma extension."),
    ("pandoc", "rtf"): (
        "captura_legitima",
        "pandoc sin `-s` emite un FRAGMENTO: `{\\pard \\ql \\f0 ...`, sin el "
        "`{\\rtf1` de cabecera. MEDIDO en la misma tanda: con `-s` la misma "
        "semilla da `{\\rtf1\\ansi\\deff0...` y `firma_real` devuelve `rtf`. El "
        "fallo es de la INVOCACION heredada de ConvertX, no del vocabulario; y "
        "explica por que los otros escritores de markup de pandoc estan en "
        "EXT_SIN_FIRMA con el motivo «emitido en fragmento»."),
}

# Defectos de invocacion HEREDADOS de `_cont_firmas.py` que la prueba de humo
# destapo ANTES de la tanda ancha y que se corrigieron en `_c30_escribe.py`. Se
# publican porque miden algo real: el censo de F1 conto como `escrito` ficheros
# con la extension mintiendo, y el punto 1 los atrapa.
INVOCACION_CORREGIDA = [
    {"motor": "libjxl", "destinos": "todos los que no son `jxl`",
     "antes": "`cjxl entrada salida.<dest>` escribe SIEMPRE un JXL, mire la "
              "extension que mire: `apng` y `exr` salieron con `firma_real=jxl` "
              "y G3 fallo (3 celdas cada uno en la prueba de humo).",
     "ahora": "png -> `cjxl` -> .jxl -> `djxl` -> destino."},
    {"motor": "dvisvgm", "destinos": "svgz",
     "antes": "`dvisvgm --pdf x.pdf -o y.svgz` sin `-z` escribe un SVG EN CLARO "
              "con nombre `.svgz`: rc=0, fichero valido, extension mintiendo "
              "(G3 fallo, `gzip` esperado y `svg` obtenido, 3 celdas).",
     "ahora": "se anade `-z`."},
]


ENTORNO = {
    "imagen": "filex-c13 (sha 6d359bad483e, 5,78 GB)",
    "python_dentro": "3.13.14",
    "motores": {"graphicsmagick": "GraphicsMagick 1.3.46 2025-10-29 Q16",
                "vips": "vips-8.18.3", "pandoc": "pandoc 3.9.0.2",
                "libjxl": "0.11.2 [AVX2,SSE4,SSE2]"},
    "contenedores": ["c30-humo-20260828a", "c30-ancha-20260828",
                     "c30-triaje-20260828", "c30-vips-mat", "c30-chk-1"],
    "tope": "--entrypoint timeout ... -k 5 <s>, con --init",
    "AVISO_TOPE_MEDIDO": (
        "LA RECETA DE CLAUDE.md sec.3 NO FUNCIONA TAL CUAL EN ESTA IMAGEN. "
        "`docker run --entrypoint timeout filex-c13 -k 5 N <orden>` devuelve "
        "rc=125 SIN UN SOLO BYTE en stdout ni en stderr, para CUALQUIER orden "
        "-- tambien `timeout 30 /bin/echo hi`. La causa es que `timeout` "
        "(coreutils 9.10, Debian) queda de PID 1: con `--init` (tini de PID 1) "
        "la MISMA orden sale rc=0, y `timeout -k 5 3 sleep 30` devuelve 124 en "
        "3 s, o sea el tope de verdad mata. MEDIDO. "
        "Y el 125 es la trampa 25 otra vez: es indistinguible de «docker run "
        "fallo», que es el significado documentado del 125 -- dos causas "
        "distintas con la misma pinta, y sin mensaje que las separe."),
}


def main():
    tmp = sys.argv[1]
    d = json.load(open(os.path.join(tmp, "c30_contenedor.json"), encoding="utf-8"))
    tri = json.load(open(os.path.join(tmp, "c30_triaje.json"), encoding="utf-8"))
    r = d["resumen"]

    fp, cap, sin_juzgar = [], [], []
    for f in r["falsos_positivos"]:
        k = (f["motor"], f["destino"])
        veredicto, razon = ADJUDICA.get(k, (None, None))
        fila = dict(f, veredicto=veredicto, razon=razon)
        if veredicto == "falso_positivo":
            fp.append(fila)
        elif veredicto == "captura_legitima":
            cap.append(fila)
        else:
            sin_juzgar.append(fila)

    r["triaje"] = {
        "metodo": "el arbitro es un motor que no escribio el fichero: "
                  "`magick identify`, `gm identify`, `vipsheader` y el round-trip "
                  "del propio motor. Sin testigo externo, `fallo` sobre salida "
                  "legitima y `fallo` sobre salida con la extension mintiendo "
                  "tienen la misma pinta.",
        "falsos_positivos_reales": fp,
        "n_falsos_positivos_reales": len(fp),
        "n_falsos_positivos_reales_destinos": len({(x["motor"], x["destino"]) for x in fp}),
        "capturas_legitimas": cap,
        "n_capturas_legitimas": len(cap),
        "n_capturas_legitimas_destinos": len({(x["motor"], x["destino"]) for x in cap}),
        "sin_juzgar": sin_juzgar,
        "invocacion_corregida_antes_de_la_tanda": INVOCACION_CORREGIDA,
        "evidencia": tri["filas"],
        "sondas": tri["sondas"],
    }
    r["g6_por_motor"] = dict(Counter(x["motor"] for x in r["g6"]))
    r["entorno"] = ENTORNO
    d["resumen"] = r
    with open(os.path.join(DEST, "c30_contenedor.json"), "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(DEST, "c30_triaje.json"), "w", encoding="utf-8") as fh:
        json.dump(tri, fh, indent=1, ensure_ascii=False)
    print("falsos positivos REALES:", len(fp),
          sorted({(x["motor"], x["destino"]) for x in fp}))
    print("capturas legitimas    :", len(cap),
          sorted({(x["motor"], x["destino"]) for x in cap}))
    print("sin juzgar            :", len(sin_juzgar))
    print("cobertura por destino :", r["cobertura_por_destino"])
    print("G6 por motor          :", r["g6_por_motor"])


if __name__ == "__main__":
    main()
