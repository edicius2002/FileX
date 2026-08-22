#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ImageMagick 7.1.2 IGNORA `-define tiff:predictor=2` (los ficheros salen byte
a byte del mismo tamano que sin el). Como el predictor horizontal es justo la
mitad del trabajo de leer un TIFF comprimido, aqui se fabrica el fixture a mano:
se lee la banda cruda de alpha_tiff_none.tif, se aplica la diferenciacion
horizontal (Predictor=2) y se reescribe un TIFF minimo con Deflate y con LZW.

Solo biblioteca estandar. La verdad de referencia la da `magick` al releerlos.
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
BASE = os.path.join(FIX, "alpha_tiff_none.tif")

AN = AL = 200
SPP = 4


def lzw_tiff(datos: bytes) -> bytes:
    """Codificador LZW de TIFF: MSB primero, con 'early change' (el ancho de
    codigo sube UNO antes de agotarse)."""
    salida = bytearray()
    acc = 0
    nbits = 0

    def emitir(codigo, ancho):
        nonlocal acc, nbits
        acc = (acc << ancho) | codigo
        nbits += ancho
        while nbits >= 8:
            nbits -= 8
            salida.append((acc >> nbits) & 0xFF)

    dic = {bytes([i]): i for i in range(256)}
    prox = 258
    ancho = 9
    emitir(256, ancho)
    w = b""
    for b in datos:
        wc = w + bytes([b])
        if wc in dic:
            w = wc
            continue
        emitir(dic[w], ancho)
        dic[wc] = prox
        prox += 1
        # early change: +1 bit UNO antes del limite
        if prox + 1 > (1 << ancho) and ancho < 12:
            ancho += 1
        if prox >= 4094:
            emitir(256, ancho)
            dic = {bytes([i]): i for i in range(256)}
            prox = 258
            ancho = 9
        w = bytes([b])
    if w:
        emitir(dic[w], ancho)
    emitir(257, ancho)
    if nbits:
        salida.append((acc << (8 - nbits)) & 0xFF)
    return bytes(salida)


def escribir_tiff(ruta, banda, compresion, predictor):
    """TIFF minimo, little-endian, una banda, RGBA 8 bits, chunky."""
    campos = [
        (256, 3, 1, AN), (257, 3, 1, AL),
        (258, 3, 4, None),                    # BitsPerSample -> fuera
        (259, 3, 1, compresion), (262, 3, 1, 2),
        (273, 4, 1, None),                    # StripOffsets -> se rellena
        (277, 3, 1, SPP), (278, 3, 1, AL), (279, 4, 1, len(banda)),
        (284, 3, 1, 1), (317, 3, 1, predictor), (338, 3, 1, 2),
    ]
    n = len(campos)
    # disposicion: cabecera(8) | IFD | extras | banda
    ifd_off = 8
    ifd_len = 2 + 12 * n + 4
    extra_off = ifd_off + ifd_len
    bps = struct.pack("<4H", 8, 8, 8, 8)
    banda_off = extra_off + len(bps)
    out = bytearray(b"II*\x00" + struct.pack("<I", ifd_off))
    ifd = bytearray(struct.pack("<H", n))
    for etiq, tipo, cnt, val in campos:
        if etiq == 258:
            bruto = struct.pack("<I", extra_off)
        elif etiq == 273:
            bruto = struct.pack("<I", banda_off)
        elif tipo == 3:
            bruto = struct.pack("<HH", val, 0)
        else:
            bruto = struct.pack("<I", val)
        ifd += struct.pack("<HHI", etiq, tipo, cnt) + bruto
    ifd += struct.pack("<I", 0)
    out += ifd + bps + banda
    with open(ruta, "wb") as fh:
        fh.write(bytes(out))


def main():
    d = open(BASE, "rb").read()
    # alpha_tiff_none.tif: banda unica sin comprimir en StripOffsets=8
    banda = bytearray(d[8:8 + AN * AL * SPP])
    assert len(banda) == AN * AL * SPP, len(banda)
    crudo = bytes(banda)

    # Predictor 2: diferenciacion horizontal POR MUESTRA, zancada = SPP
    pred = bytearray(crudo)
    for y in range(AL):
        o = y * AN * SPP
        for x in range(AN - 1, 0, -1):
            for c in range(SPP):
                i = o + x * SPP + c
                pred[i] = (pred[i] - pred[i - SPP]) & 255
    pred = bytes(pred)

    salidas = [
        ("alpha_tiff_zip_pred2.tif", zlib.compress(pred, 9), 8, 2),
        ("alpha_tiff_lzw_pred2.tif", lzw_tiff(pred), 5, 2),
        ("alpha_tiff_lzw_p1.tif", lzw_tiff(crudo), 5, 1),
    ]
    man = []
    for nombre, banda_c, compr, predictor in salidas:
        ruta = os.path.join(FIX, nombre)
        escribir_tiff(ruta, banda_c, compr, predictor)
        p = subprocess.run(["magick", ruta, "-format",
                            "%[fx:minima.a] %wx%h %[channels]", "info:"],
                           capture_output=True, text=True, timeout=180,
                           stdin=subprocess.DEVNULL)
        man.append({"nombre": nombre, "bytes": os.path.getsize(ruta),
                    "compresion": compr, "predictor": predictor,
                    "sha256": hashlib.sha256(open(ruta, "rb").read()).hexdigest(),
                    "magick": (p.stdout or p.stderr).strip()[:120]})
        print("%-26s %7d B  compr=%-3d pred=%d  magick=%s"
              % (nombre, man[-1]["bytes"], compr, predictor, man[-1]["magick"]))
    with open(os.path.join(AQUI, "fixtures_predictor.json"), "w",
              encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
