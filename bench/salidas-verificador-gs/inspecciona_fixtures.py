#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vuelca las etiquetas TIFF y la cabecera PNG/GIF de cada fixture, y la verdad
de referencia (`magick -format %[fx:minima.a]`), para saber que hay que cubrir.
"""
import json
import os
import struct
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(AQUI, "fixtures")

NOMBRES = {256: "ImageWidth", 257: "ImageLength", 258: "BitsPerSample",
           259: "Compression", 262: "Photometric", 273: "StripOffsets",
           277: "SamplesPerPixel", 278: "RowsPerStrip", 279: "StripByteCounts",
           284: "PlanarConfig", 317: "Predictor", 322: "TileWidth",
           323: "TileLength", 338: "ExtraSamples", 339: "SampleFormat"}
TAM = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}


def tiff(ruta):
    d = open(ruta, "rb").read()
    be = d[:2] == b"MM"
    e = ">" if be else "<"
    desp = struct.unpack_from(e + "I", d, 4)[0]
    out = []
    while desp:
        n = struct.unpack_from(e + "H", d, desp)[0]
        campos = {}
        for i in range(n):
            o = desp + 2 + 12 * i
            etiq, tipo, cnt = struct.unpack_from(e + "HHI", d, o)
            tam = TAM.get(tipo, 1) * cnt
            pos = o + 8 if tam <= 4 else struct.unpack_from(e + "I", d, o + 8)[0]
            if tipo == 3:
                v = list(struct.unpack_from(e + "%dH" % min(cnt, 12), d, pos))
            elif tipo == 4:
                v = list(struct.unpack_from(e + "%dI" % min(cnt, 12), d, pos))
            else:
                v = list(d[pos:pos + min(tam, 12)])
            campos[NOMBRES.get(etiq, etiq)] = v if cnt > 1 else v[0]
        out.append(campos)
        desp = struct.unpack_from(e + "I", d, desp + 2 + 12 * n)[0]
    return out


def png(ruta):
    d = open(ruta, "rb").read(33)
    an, al = struct.unpack_from(">II", d, 16)
    return {"ancho": an, "alto": al, "prof": d[24], "color": d[25],
            "entrelazado": d[28]}


def gif(ruta):
    d = open(ruta, "rb").read()
    return {"version": d[:6].decode("latin1"),
            "gce_transparente": d.find(b"\x21\xf9\x04") >= 0 and
            bool(d[d.find(b"\x21\xf9\x04") + 3] & 1),
            "n_bloques_imagen": d.count(b"\x2c")}


def main():
    res = {}
    for n in sorted(os.listdir(FIX)):
        ruta = os.path.join(FIX, n)
        p = subprocess.run(["magick", ruta, "-format", "%[fx:minima.a]", "info:"],
                           capture_output=True, text=True, timeout=180,
                           stdin=subprocess.DEVNULL)
        info = {"bytes": os.path.getsize(ruta),
                "magick_minima_a": p.stdout.strip() or p.stderr.strip()[:80]}
        try:
            if n.endswith(".tif"):
                info["ifds"] = tiff(ruta)
            elif n.endswith(".png"):
                info["ihdr"] = png(ruta)
            elif n.endswith(".gif"):
                info["gif"] = gif(ruta)
        except Exception as e:                                   # noqa: BLE001
            info["error"] = "%s: %s" % (type(e).__name__, e)
        res[n] = info
        print("%-26s %s" % (n, json.dumps(info, ensure_ascii=False)[:220]))
    with open(os.path.join(AQUI, "fixtures_inspeccion.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
