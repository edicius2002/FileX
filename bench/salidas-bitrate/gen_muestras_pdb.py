#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reescribe el diccionario `MUESTRAS` de `muestras_pdb.py` desde el volcado
base64 del contenedor, SIN transcripción manual.

La primera versión se copió a mano y `cal_ereader.pdb` salió con **6 bytes de
menos** (327 en vez de 333) sin que nada fallara: el fichero seguía abriéndose y
el marcador del byte 60 seguía siendo el bueno. Es la trampa 48 en miniatura —un
recuento que cuadra no prueba un contenido correcto—, y por eso el fixture se
genera, no se teclea.

Uso: python bench/salidas-bitrate/gen_muestras_pdb.py <b64.txt>
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
MOTOR = {"im.pdb": ("imagemagick / graphicsmagick", "vIMGView"),
         "cal_doc.pdb": ("calibre (por defecto, -f doc)", "TEXtREAd"),
         "cal_ereader.pdb": ("calibre -f ereader", "PNRdPPrs")}


def main():
    with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
        lineas = [l.rstrip("\r\n") for l in fh if l.strip()]
    datos, actual = {}, None
    for l in lineas:
        if l.startswith("@@"):
            actual = l[2:].strip()
        elif actual:
            datos[actual] = l.strip()
            actual = None
    trozos = ["MUESTRAS = {"]
    for nombre, b64 in datos.items():
        motor, marca = MOTOR[nombre]
        trozos.append('    "%s": ("%s", "%s",' % (nombre, motor, marca))
        for i in range(0, len(b64), 72):
            trozos.append('     "%s"%s' % (b64[i:i + 72],
                                           "" if i + 72 < len(b64) else "),"))
    trozos.append("}")
    print("\n".join(trozos))


if __name__ == "__main__":
    main()
