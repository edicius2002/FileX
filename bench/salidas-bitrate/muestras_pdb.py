#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N22 — las cuatro muestras de `.pdb`, en base64, y su testigo externo.

`.pdb` NO son dos formatos, son un CONTENEDOR (PalmDB) con varios tipos dentro.
Los 78 primeros bytes son cabecera y **los 32 primeros son el NOMBRE**, que los
motores rellenan con el nombre del fichero (de salida en ImageMagick y
GraphicsMagick, de entrada en Calibre): eso es exactamente lo que el censo de
prefijos comunes de F1 midió cuando escribió *«el prefijo común medido es la
ruta del fichero, no un marcador»*. El marcador de verdad son los **8 bytes
60..67**, que en PalmDB son `type` + `creator`.

MEDIDO el 28/08 en `filex-c13` (`docker run --rm --init --entrypoint timeout`):

| motor                                | bytes | `cab[60:68]` | testigo externo                      |
|--------------------------------------|------:|--------------|--------------------------------------|
| `magick s.png im.pdb`                |   156 | `vIMGView`   | `magick identify` → `PDB 64x48`      |
| `gm convert s.png gm.pdb`            | 1 679 | `vIMGView`   | `gm identify` → `PDB 64x48`          |
| `ebook-convert s.txt c.pdb`          |   147 | `TEXtREAd`   | `ebook-meta` → `Title: s`            |
| `ebook-convert s.txt c.pdb -f ereader`|  333 | `PNRdPPrs`   | `ebook-meta` → `Title: s`            |
| `ebook-convert s.txt c.pdb -f ztxt`  |     0 | —            | `rc=1`: este motor no lo escribe aquí |

Y el árbitro NO es quien escribió el fichero (trampa 71): `magick identify`
sobre el `.pdb` de Calibre responde
`improper image header ... error/pdb.c/ReadPDBImage/348`.

Uso: python bench/salidas-bitrate/muestras_pdb.py <dir_destino>
"""
import base64
import os
import sys

#: nombre -> (motor, base64). Se guardan aquí, en TEXTO, y no como binarios
#: versionados (`CLAUDE.md` §6). Los cuatro juntos pesan 2 315 B.
#: GENERADO por `gen_muestras_pdb.py`, no tecleado: la primera copia a mano
#: perdió 6 bytes de `cal_ereader.pdb` sin que nada fallara.
MUESTRAS = {
    "im.pdb": ("imagemagick / graphicsmagick", "vIMGView",
     "aW0ucGRiAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAapHH9mqRx/YAAAAAAAAAAAAA"
     "AAAAAAAAdklNR1ZpZXcAAAAAAAAAAAABAAAAVkBvgABpbS5wZGIAAAAAAAAAAAAAAAAAAAAA"
     "AAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAP////8AQAAw////////////////"),
    "cal_doc.pdb": ("calibre (por defecto, -f doc)", "TEXtREAd",
     "cwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAapHH92qRx/cAAAAAAAAAAAAA"
     "AAAAAAAAVEVYdFJFQWQAAAACAAAAAAACAAAAYAAAAAAAAABwAAAAAAAAAAIAAAAAACwAARAA"
     "AAAAAFRpdHVsbw0KDQoNgCBQYXJyYWZv5GXwcnVlYmEugNUNCg0K"),
    "cal_ereader.pdb": ("calibre -f ereader", "PNRdPPrs",
     "cwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAapHH+GqRx/gAAAAAAAAAAAAA"
     "AAAAAAAAUE5SZFBQcnMAAAAGAAAAAAAGAAAAgAAAAAAAAAEEAAAAAAAAASEAAAAAAAABMwAA"
     "AAAAAAFAAAAAAAAAAUQAAAAAAAAACgAAAABiQAAAAAAAAwAAAAAAAAAAAAAAAQAAAAAAAAAE"
     "CgAABAAEAAQABAADAAAABAAEAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
     "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB4nAvJLCnNyefi"
     "ikkGoYDEoqLEtHyFlFQAYZ4H3HicUygoKk1NStTj4gIAEnEC4nMAVW5rbm93bgAAAAAAGAAY"
     "TWVUYUluRm8A"),
}


def escribir(destino):
    os.makedirs(destino, exist_ok=True)
    salidas = {}
    for nombre, (motor, marca, b64) in MUESTRAS.items():
        p = os.path.join(destino, nombre)
        with open(p, "wb") as fh:
            fh.write(base64.b64decode(b64))
        salidas[nombre] = p
        with open(p, "rb") as fh:
            cab = fh.read(80)
        assert cab[60:68].decode("latin-1") == marca, (nombre, cab[60:68])
        print("%-18s %-20s bytes=%-5d cab[60:68]=%s  nombre[0:16]=%r"
              % (nombre, motor, os.path.getsize(p),
                 cab[60:68].decode("latin-1"), cab[:16].rstrip(b"\0")))
    return salidas


if __name__ == "__main__":
    escribir(sys.argv[1] if len(sys.argv) > 1 else ".")
