"""C28 / paso 4 - FIRMAS HUERFANAS: nombres que la sonda sabe devolver y que
NINGUNA extension acepta.

Sale de mirar los 17 «banner del escritor» uno a uno: `#FIG `, `GIMP Palette` y
`solid ` **ya estaban en `MARCAS_TEXTO`**, asi que `firma_real` acierta con
`xfig`, `gpl` y `stl` desde hace tiempo — lo que falta no es el marcador, es la
fila de `EXT_A_FIRMAS` que lo acepta. Con ella el punto 1 se queda en
`sin_vocabulario` sobre un formato que la sonda identifica bien, que es la
version cara del problema que F1 vino a cerrar.

Este script audita la tabla entera: para cada nombre que `firma_real` puede
devolver, ¿hay alguna extension que lo acepte?

Uso:  python bench/salidas-firmas-cierre/_c28_huerfanas.py
"""
import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402


def nombres_posibles():
    """Todo lo que `firma_real` puede devolver, leido de sus tablas."""
    n = {x[2] for x in V.FIRMAS}
    n |= {x[2] for x in V.FIRMAS_LARGAS}
    n |= set(V.MARCAS_FTYP.values())
    n |= {x[1] for x in V.MARCAS_TEXTO}
    n |= set(V.MIME_ZIP.values())
    n |= {x[1] for x in V.OOXML}
    # los que salen de un predicado o de una rama, no de una tabla
    n |= {"pnm", "pam", "pfm", "pcx", "mpegts", "m2ts", "flujo_es", "adts",
          "mpegaudio", "texto", "xml", "html", "svg", "3ds",
          "webp", "wav", "avi", "midi", "riff", "wave64", "aiff", "iff",
          "isobmff", "zip", "cfb", "mobi", "desconocido", "vacio", "ilegible"}
    return n


def main():
    aceptadas = set()
    for ext, fs in V.EXT_A_FIRMAS.items():
        aceptadas |= set(fs)
    posibles = nombres_posibles()
    huerfanas = sorted(posibles - aceptadas - V.FIRMAS_INDEFINIDAS
                       - {"vacio", "ilegible", "desconocido", "texto"})
    # y al reves: extensiones que esperan un nombre que la sonda no sabe dar
    inalcanzables = sorted(aceptadas - posibles)
    res = {"n_nombres_posibles": len(posibles),
           "n_nombres_aceptados_por_alguna_extension": len(aceptadas),
           "huerfanas": huerfanas,
           "n_huerfanas": len(huerfanas),
           "inalcanzables": inalcanzables,
           "categoria_de_las_huerfanas": {
               h: V.CAT_POR_FIRMA.get(h, "(sin categoria)") for h in huerfanas}}
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
