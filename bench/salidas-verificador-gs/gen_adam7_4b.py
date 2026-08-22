#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ImageMagick no sabe escribir un PNG de paleta de 4 bits ENTRELAZADO que
conserve el tRNS: `-colors 12` aplana el alfa y el fichero sale opaco. Como el
camino "paleta de <8 bits + Adam7 + bits de relleno de la ultima celda" es
justo el que lleva la aritmetica delicada, aqui se fabrica el fixture a mano.

Imagen 13x9 (ancho IMPAR y no multiplo de 8/4/2, para que TODAS las pasadas
tengan relleno), paleta de 4 colores a 2 bits, con tRNS que hace transparente
el indice 3, colocado en un solo pixel: el ultimo de la ultima fila, que es
exactamente el que cae en los bits de relleno si la aritmetica esta mal.

Solo biblioteca estandar.
"""
import hashlib
import json
import os
import struct
import subprocess
import sys
import zlib

AQUI = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(AQUI, "fixtures")
AN, AL, BD = 13, 9, 2
ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
         (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))


def trozo(tipo, cuerpo):
    return (struct.pack(">I", len(cuerpo)) + tipo + cuerpo
            + struct.pack(">I", zlib.crc32(tipo + cuerpo) & 0xFFFFFFFF))


def empaquetar(indices):
    """Fila de indices -> bytes de 2 bits, MSB primero, con relleno a cero."""
    out = bytearray()
    acc = n = 0
    for v in indices:
        acc = (acc << BD) | (v & 3)
        n += BD
        if n == 8:
            out.append(acc)
            acc = n = 0
    if n:
        out.append((acc << (8 - n)) & 0xFF)
    return bytes(out)


def construir(px, entrelazado):
    ihdr = struct.pack(">IIBBBBB", AN, AL, BD, 3, 0, 0, 1 if entrelazado else 0)
    plte = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 9, 9, 9])
    trns = bytes([255, 255, 255, 0])            # el indice 3 es transparente
    crudo = bytearray()
    if entrelazado:
        for xini, yini, xpaso, ypaso in ADAM7:
            anp = (AN - xini + xpaso - 1) // xpaso
            alp = (AL - yini + ypaso - 1) // ypaso
            if anp <= 0 or alp <= 0:
                continue
            for j in range(alp):
                y = yini + j * ypaso
                fila = [px[y][xini + i * xpaso] for i in range(anp)]
                crudo += b"\x00" + empaquetar(fila)
    else:
        for y in range(AL):
            crudo += b"\x00" + empaquetar(px[y])
    return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", ihdr) + trozo(b"PLTE", plte)
            + trozo(b"tRNS", trns)
            + trozo(b"IDAT", zlib.compress(bytes(crudo), 9))
            + trozo(b"IEND", b""))


def main():
    man = []
    # (nombre, pixel transparente o None)
    casos = [("adam7_4b_esquina", (AN - 1, AL - 1)),
             ("adam7_4b_opaco", None),
             ("plano_4b_esquina", (AN - 1, AL - 1))]
    for nombre, tp in casos:
        px = [[(x + y) % 3 for x in range(AN)] for y in range(AL)]
        if tp:
            px[tp[1]][tp[0]] = 3
        datos = construir(px, entrelazado=not nombre.startswith("plano"))
        ruta = os.path.join(FIX, nombre + ".png")
        with open(ruta, "wb") as fh:
            fh.write(datos)
        p = subprocess.run(["magick", ruta, "-format",
                            "%[fx:minima.a] %wx%h %[interlace]", "info:"],
                           capture_output=True, text=True, timeout=120,
                           stdin=subprocess.DEVNULL)
        man.append({"nombre": nombre + ".png", "bytes": len(datos),
                    "pixel_transparente": tp,
                    "sha256": hashlib.sha256(datos).hexdigest(),
                    "magick": (p.stdout or p.stderr).strip()[:80]})
        print("%-22s %5d B  transp=%-9s magick=%s"
              % (nombre, len(datos), tp, man[-1]["magick"]))
    with open(os.path.join(AQUI, "fixtures_adam7_4b.json"), "w",
              encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
