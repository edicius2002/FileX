#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificador.py — prototipo del contrato de verificacion post-conversion de FileX.

Implementa los CUATRO puntos del contrato:

  1. FIRMA      bytes magicos reales frente a la extension pedida.
  2. FLUJOS     numero de pistas de video / audio / subtitulo obtenidas
                frente a las esperadas.
  3. PROPIEDADES propiedades declaradas frente a medidas: dimensiones,
                profundidad de bits, canal alfa, ppp, bitrate, duracion.
  4. PEDIDO     propiedades PEDIDAS frente a obtenidas: ninguna transformacion
                no solicitada (el caso image-worker-mcp: redimensionado
                silencioso 1920x1080 -> 800x450 con barras).

Dos motores de sondeo intercambiables, para medir su coste:

  --motor proceso     : solo Python (struct + mmap). CERO subprocesos.
  --motor subproceso  : ffprobe / magick identify / gswin64c.

Sin dependencias externas: solo la biblioteca estandar de Python 3.11.

Uso:
  python verificador.py --salida F --entrada G --destino webp [--motor proceso]
  python verificador.py --lote fichero.json           (lista de trabajos)
  python verificador.py --sondear F                   (volcado del sondeo)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import struct
import subprocess
import sys
import time
import zlib

TIMEOUT = 60  # segundos: ninguna sonda externa puede colgarse

# ===========================================================================
# PUNTO 1 — FIRMA REAL DEL FICHERO (bytes magicos). Siempre en proceso.
# ===========================================================================

# (desplazamiento, bytes, formato). Orden importante: lo mas especifico antes.
FIRMAS = [
    (0, b"\x89PNG\r\n\x1a\n", "png"),
    (0, b"\xff\xd8\xff", "jpeg"),
    (0, b"GIF87a", "gif"),
    (0, b"GIF89a", "gif"),
    (0, b"BM", "bmp"),
    (0, b"II*\x00", "tiff"),
    (0, b"MM\x00*", "tiff"),
    (0, b"%PDF-", "pdf"),
    (0, b"fLaC", "flac"),
    (0, b"OggS", "ogg"),
    (0, b"\x1a\x45\xdf\xa3", "matroska"),
    (0, b"ID3", "mp3"),
    (0, b"\x1f\x8b", "gzip"),
    (0, b"PK\x03\x04", "zip"),
]

# Familia ISO-BMFF: se resuelve por el 'ftyp' de los bytes 4..8.
MARCAS_FTYP = {
    b"avif": "avif", b"avis": "avif", b"mif1": "heif", b"heic": "heif",
    b"heix": "heif", b"msf1": "heif",
    b"isom": "mp4", b"iso2": "mp4", b"mp41": "mp4", b"mp42": "mp4",
    b"M4A ": "m4a", b"M4V ": "mp4", b"qt  ": "mov", b"3gp4": "3gp",
}

# Que firma real es aceptable para cada extension pedida.
EXT_A_FIRMAS = {
    ".png": {"png"}, ".jpg": {"jpeg"}, ".jpeg": {"jpeg"}, ".gif": {"gif"},
    ".bmp": {"bmp"}, ".tif": {"tiff"}, ".tiff": {"tiff"}, ".webp": {"webp"},
    ".avif": {"avif"}, ".heic": {"heif"}, ".pdf": {"pdf"},
    ".mp3": {"mp3"}, ".flac": {"flac"}, ".wav": {"wav"},
    ".opus": {"ogg"}, ".ogg": {"ogg"}, ".oga": {"ogg"},
    ".m4a": {"m4a", "mp4"}, ".mp4": {"mp4", "mov", "m4a"}, ".mov": {"mov", "mp4"},
    ".mkv": {"matroska"}, ".webm": {"matroska"},
    ".csv": {"texto"}, ".json": {"texto"}, ".txt": {"texto"}, ".md": {"texto"},
}


def firma_real(ruta: str) -> str:
    """Formato real por bytes magicos. Ningun subproceso, ninguna extension."""
    try:
        with open(ruta, "rb") as fh:
            cab = fh.read(32)
    except OSError:
        return "ilegible"
    if not cab:
        return "vacio"
    # RIFF: WAV / WEBP / AVI comparten cabecera; discrimina el subtipo.
    if cab[:4] == b"RIFF" and len(cab) >= 12:
        sub = cab[8:12]
        return {b"WEBP": "webp", b"WAVE": "wav", b"AVI ": "avi"}.get(sub, "riff")
    # ISO-BMFF: caja 'ftyp'.
    if len(cab) >= 12 and cab[4:8] == b"ftyp":
        return MARCAS_FTYP.get(cab[8:12], "isobmff")
    for desp, magico, nombre in FIRMAS:
        if cab[desp:desp + len(magico)] == magico:
            return nombre
    # MP3 sin ID3: sincronismo de trama.
    if len(cab) >= 2 and cab[0] == 0xFF and (cab[1] & 0xE0) == 0xE0:
        return "mp3"
    # Texto: heuristica minima (sin bytes de control fuera de \t\r\n).
    if all(b >= 0x20 or b in (9, 10, 13) for b in cab):
        return "texto"
    return "desconocido"


# ===========================================================================
# SONDEO EN PROCESO — cabeceras leidas con struct. Cero subprocesos.
# ===========================================================================

def _u16(b, o, be=True):
    return struct.unpack_from(">H" if be else "<H", b, o)[0]


def _u32(b, o, be=True):
    return struct.unpack_from(">I" if be else "<I", b, o)[0]


# ---- IMAGEN ---------------------------------------------------------------

def _png(fh) -> dict:
    fh.seek(8)
    d = {"formato": "png", "categoria": "imagen"}
    while True:
        cab = fh.read(8)
        if len(cab) < 8:
            break
        long_, tipo = _u32(cab, 0), cab[4:8]
        if tipo == b"IHDR":
            c = fh.read(long_)
            d["ancho"], d["alto"] = _u32(c, 0), _u32(c, 4)
            prof, color = c[8], c[9]
            d["profundidad_bits"] = prof
            d["tiene_alfa"] = color in (4, 6)
            d["canales"] = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color, 0)
            d["paleta"] = color == 3
        elif tipo == b"pHYs":
            c = fh.read(long_)
            if len(c) >= 9 and c[8] == 1:  # unidad = metro
                d["ppp"] = round(_u32(c, 0) * 0.0254)
        elif tipo == b"tRNS":
            d["tiene_alfa"] = True
            fh.seek(long_, io.SEEK_CUR)
        elif tipo in (b"IDAT", b"IEND"):
            break
        else:
            fh.seek(long_, io.SEEK_CUR)
        fh.seek(4, io.SEEK_CUR)  # CRC
    d["n_imagenes"] = 1
    return d


def _jpeg(fh) -> dict:
    d = {"formato": "jpeg", "categoria": "imagen", "tiene_alfa": False,
         "n_imagenes": 1}
    fh.seek(2)
    while True:
        b = fh.read(1)
        if not b:
            break
        if b != b"\xff":
            continue
        marca = fh.read(1)
        while marca == b"\xff":
            marca = fh.read(1)
        if not marca:
            break
        m = marca[0]
        if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7:
            continue
        cab = fh.read(2)
        if len(cab) < 2:
            break
        long_ = _u16(cab, 0) - 2
        cuerpo = fh.read(long_)
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):  # SOF
            d["profundidad_bits"] = cuerpo[0]
            d["alto"], d["ancho"] = _u16(cuerpo, 1), _u16(cuerpo, 3)
            d["canales"] = cuerpo[5]
            break
        if m == 0xE0 and cuerpo[:5] == b"JFIF\x00":  # APP0
            unidad = cuerpo[7]
            xd = _u16(cuerpo, 8)
            if unidad == 1:
                d["ppp"] = xd
            elif unidad == 2:
                d["ppp"] = round(xd * 2.54)
        if m == 0xDA:  # SOS: se acabo la cabecera
            break
    return d


def _webp(fh) -> dict:
    fh.seek(12)
    d = {"formato": "webp", "categoria": "imagen", "tiene_alfa": False,
         "profundidad_bits": 8, "n_imagenes": 1}
    while True:
        cab = fh.read(8)
        if len(cab) < 8:
            break
        tipo, long_ = cab[:4], _u32(cab, 4, be=False)
        cuerpo = fh.read(min(long_, 64))
        salto = long_ + (long_ & 1) - len(cuerpo)
        if tipo == b"VP8X":
            d["tiene_alfa"] = bool(cuerpo[0] & 0x10)
            d["ancho"] = 1 + int.from_bytes(cuerpo[4:7], "little")
            d["alto"] = 1 + int.from_bytes(cuerpo[7:10], "little")
            d["n_imagenes"] = 1
        elif tipo == b"VP8 " and "ancho" not in d:
            d["ancho"] = _u16(cuerpo, 6, be=False) & 0x3FFF
            d["alto"] = _u16(cuerpo, 8, be=False) & 0x3FFF
            d["perdida"] = True
        elif tipo == b"VP8L" and "ancho" not in d:
            bits = int.from_bytes(cuerpo[1:6], "little")
            d["ancho"] = (bits & 0x3FFF) + 1
            d["alto"] = ((bits >> 14) & 0x3FFF) + 1
            d["tiene_alfa"] = bool((bits >> 28) & 1)
            d["perdida"] = False
        elif tipo == b"ALPH":
            d["tiene_alfa"] = True
        elif tipo == b"ANMF":
            d["n_imagenes"] = d.get("n_imagenes", 0) + 1
        if salto > 0:
            fh.seek(salto, io.SEEK_CUR)
    return d


def _gif(fh) -> dict:
    fh.seek(6)
    c = fh.read(7)
    d = {"formato": "gif", "categoria": "imagen", "profundidad_bits": 8,
         "tiene_alfa": True}
    d["ancho"], d["alto"] = _u16(c, 0, be=False), _u16(c, 2, be=False)
    d["colores_paleta"] = 2 ** ((c[4] & 0x07) + 1) if c[4] & 0x80 else 0
    # contar fotogramas es caro: se recorren los bloques
    n = 0
    if c[4] & 0x80:
        fh.seek(3 * d["colores_paleta"], io.SEEK_CUR)
    while True:
        b = fh.read(1)
        if not b or b == b";":
            break
        if b == b",":
            n += 1
            desc = fh.read(9)
            if len(desc) < 9:
                break
            if desc[8] & 0x80:
                fh.seek(3 * 2 ** ((desc[8] & 0x07) + 1), io.SEEK_CUR)
            fh.seek(1, io.SEEK_CUR)  # LZW min code size
            while True:
                s = fh.read(1)
                if not s or s == b"\x00":
                    break
                fh.seek(s[0], io.SEEK_CUR)
        elif b == b"!":
            fh.seek(1, io.SEEK_CUR)
            while True:
                s = fh.read(1)
                if not s or s == b"\x00":
                    break
                fh.seek(s[0], io.SEEK_CUR)
    d["n_imagenes"] = n
    return d


_TIFF_TIPOS = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8,
               11: 4, 12: 8}


def _tiff(fh) -> dict:
    cab = fh.read(8)
    be = cab[:2] == b"MM"
    d = {"formato": "tiff", "categoria": "imagen"}
    desp = _u32(cab, 4, be)
    n_img = 0
    while desp and n_img < 64:
        n_img += 1
        fh.seek(desp)
        n = _u16(fh.read(2), 0, be)
        entradas = fh.read(12 * n)
        campos = {}
        for i in range(n):
            o = 12 * i
            etiq, tipo, cnt = _u16(entradas, o, be), _u16(entradas, o + 2, be), _u32(entradas, o + 4, be)
            bruto = entradas[o + 8:o + 12]
            tam = _TIFF_TIPOS.get(tipo, 1) * cnt
            if tam > 4:
                pos = _u32(bruto, 0, be)
                aqui = fh.tell()
                fh.seek(pos)
                bruto = fh.read(tam)
                fh.seek(aqui)
            if tipo == 3:
                vals = [_u16(bruto, 2 * k, be) for k in range(min(cnt, 8))]
            elif tipo == 4:
                vals = [_u32(bruto, 4 * k, be) for k in range(min(cnt, 4))]
            elif tipo == 5:
                vals = [_u32(bruto, 0, be) / max(1, _u32(bruto, 4, be))] if tam >= 8 else [0]
            else:
                vals = [bruto[0] if bruto else 0]
            campos[etiq] = vals
        if n_img == 1:
            d["ancho"] = campos.get(256, [0])[0]
            d["alto"] = campos.get(257, [0])[0]
            d["profundidad_bits"] = campos.get(258, [1])[0]
            d["canales"] = campos.get(277, [1])[0]
            d["compresion"] = campos.get(259, [1])[0]
            d["tiene_alfa"] = bool(campos.get(338, [0])[0]) or d["canales"] in (2, 4)
            unidad = campos.get(296, [2])[0]
            if 282 in campos and unidad == 2:
                d["ppp"] = round(campos[282][0])
            elif 282 in campos and unidad == 3:
                d["ppp"] = round(campos[282][0] * 2.54)
        desp = _u32(fh.read(4), 0, be)
    d["n_imagenes"] = n_img
    return d


# ---- ISO-BMFF: sirve para AVIF/HEIF y para MP4/M4A/MOV --------------------

def _cajas(fh, fin, prof=0):
    """Itera (tipo, inicio_datos, fin_datos) de las cajas de un ISO-BMFF."""
    while fh.tell() + 8 <= fin:
        ini = fh.tell()
        cab = fh.read(8)
        if len(cab) < 8:
            return
        tam = _u32(cab, 0)
        tipo = cab[4:8]
        if tam == 1:
            tam = struct.unpack(">Q", fh.read(8))[0]
            datos = fh.tell()
        elif tam == 0:
            tam = fin - ini
            datos = fh.tell()
        else:
            datos = fh.tell()
        yield tipo, datos, min(ini + tam, fin)
        fh.seek(min(ini + max(tam, 8), fin))


CONTENEDORAS = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"meta", b"iprp",
                b"ipco", b"udta", b"edts", b"dinf", b"moof", b"traf"}


def _isobmff(fh, tam_fichero: str) -> dict:
    d = {"categoria": "av", "pistas": [], "n_video": 0, "n_audio": 0,
         "n_subtitulo": 0}
    estado = {"handler": None, "timescale": 1000, "dur_mov": 0}

    def recorre(ini, fin, prof=0):
        if prof > 6:
            return
        fh.seek(ini)
        for tipo, di, df in _cajas(fh, fin, prof):
            if tipo == b"mvhd":
                fh.seek(di)
                c = fh.read(min(df - di, 120))
                ver = c[0]
                if ver == 1:
                    ts, dur = _u32(c, 20), struct.unpack_from(">Q", c, 24)[0]
                else:
                    ts, dur = _u32(c, 12), _u32(c, 16)
                if ts:
                    d["duracion_s"] = round(dur / ts, 4)
            elif tipo == b"trak":
                estado["handler"] = None
                estado["pista"] = {}
                recorre(di, df, prof + 1)
                p = estado.get("pista") or {}
                h = estado["handler"]
                if h == b"vide":
                    p["tipo"] = "video"
                    d["n_video"] += 1
                elif h == b"soun":
                    p["tipo"] = "audio"
                    d["n_audio"] += 1
                elif h in (b"subt", b"sbtl", b"text"):
                    p["tipo"] = "subtitulo"
                    d["n_subtitulo"] += 1
                else:
                    p["tipo"] = "otro"
                if p.get("tipo") != "otro":
                    d["pistas"].append(p)
            elif tipo == b"tkhd":
                fh.seek(di)
                c = fh.read(min(df - di, 92))
                ver = c[0]
                o = 84 if ver == 1 else 72
                if len(c) >= o + 8:
                    an = _u32(c, o) / 65536.0
                    al = _u32(c, o + 4) / 65536.0
                    if an > 0 and al > 0:
                        estado.setdefault("pista", {})["ancho"] = int(round(an))
                        estado["pista"]["alto"] = int(round(al))
            elif tipo == b"mdhd":
                fh.seek(di)
                c = fh.read(min(df - di, 40))
                ver = c[0]
                if ver == 1:
                    ts, dur = _u32(c, 20), struct.unpack_from(">Q", c, 24)[0]
                else:
                    ts, dur = _u32(c, 12), _u32(c, 16)
                if ts:
                    estado.setdefault("pista", {})["duracion_s"] = round(dur / ts, 4)
                    estado["pista"]["sample_rate_mdhd"] = ts
            elif tipo == b"hdlr":
                fh.seek(di + 8)
                estado["handler"] = fh.read(4)
            elif tipo == b"stsd":
                fh.seek(di + 8)
                c = fh.read(min(df - di - 8, 200))
                if len(c) >= 12:
                    codec = c[4:8].decode("latin-1").strip()
                    p = estado.setdefault("pista", {})
                    p["codec"] = codec
                    if estado["handler"] == b"vide" and len(c) >= 40:
                        p["ancho"] = _u16(c, 32)
                        p["alto"] = _u16(c, 34)
                        p["profundidad_bits"] = _u16(c, 74) if len(c) >= 76 else None
                    elif estado["handler"] == b"soun" and len(c) >= 32:
                        p["canales"] = _u16(c, 24)
                        p["profundidad_bits"] = _u16(c, 26)
                        p["sample_rate"] = _u32(c, 32) >> 16
            elif tipo == b"ispe":
                fh.seek(di + 4)
                c = fh.read(8)
                d["ancho"], d["alto"] = _u32(c, 0), _u32(c, 4)
                d["categoria"] = "imagen"
            elif tipo == b"pixi":
                fh.seek(di + 4)
                c = fh.read(8)
                if c:
                    d["canales"] = c[0]
                    d["profundidad_bits"] = c[1] if len(c) > 1 else 8
                    d["tiene_alfa"] = c[0] == 4
            elif tipo == b"av1C":
                fh.seek(di)
                c = fh.read(4)
                if len(c) >= 3:
                    alto_bd = bool(c[2] & 0x40)
                    doce = bool(c[2] & 0x20)
                    d.setdefault("profundidad_bits", 12 if doce else (10 if alto_bd else 8))
                d["formato"] = "avif"
            elif tipo == b"auxC":
                d["tiene_alfa"] = True
            elif tipo == b"meta":
                # 'meta' es caja completa: 4 bytes de version/flags antes de las hijas
                recorre(di + 4, df, prof + 1)
            elif tipo in CONTENEDORAS:
                recorre(di, df, prof + 1)

    tam = os.path.getsize(tam_fichero)
    recorre(0, tam)
    d["n_pistas"] = len(d["pistas"])
    if d["categoria"] == "imagen":
        d.setdefault("formato", "avif")
        d.setdefault("n_imagenes", 1)
        d.setdefault("tiene_alfa", False)
        for k in ("pistas", "n_video", "n_audio", "n_subtitulo", "n_pistas"):
            d.pop(k, None)
    else:
        d["formato"] = "mp4"
        d["bitrate_bps"] = int(tam * 8 / d["duracion_s"]) if d.get("duracion_s") else None
    return d


# ---- MATROSKA / WEBM (EBML) ----------------------------------------------

def _ebml_num(fh, quitar_marca=True):
    b = fh.read(1)
    if not b:
        return None, 0
    v = b[0]
    if v == 0:
        return None, 1
    long_ = 8 - v.bit_length() + 1
    resto = fh.read(long_ - 1)
    n = v & (0xFF >> long_) if quitar_marca else v
    for x in resto:
        n = (n << 8) | x
    return n, long_


IDS_MKV = {
    0x18538067: "Segment", 0x1549A966: "Info", 0x1654AE6B: "Tracks",
    0xAE: "TrackEntry", 0xE0: "Video", 0xE1: "Audio",
    0x2AD7B1: "TimecodeScale", 0x4489: "Duration", 0x83: "TrackType",
    0x86: "CodecID", 0xB0: "PixelWidth", 0xBA: "PixelHeight",
    0xB5: "SamplingFrequency", 0x9F: "Channels", 0x6264: "BitDepth",
    0x22B59C: "Language", 0x536E: "Name", 0x55B2: "TrackName",
}
CONT_MKV = {"Segment", "Info", "Tracks", "TrackEntry", "Video", "Audio"}


def _matroska(fh, ruta) -> dict:
    tam = os.path.getsize(ruta)
    d = {"formato": "matroska", "categoria": "av", "pistas": [],
         "n_video": 0, "n_audio": 0, "n_subtitulo": 0}
    ctx = {"escala": 1000000, "dur": None, "pista": None}

    def recorre(fin, prof=0):
        if prof > 5:
            return
        while fh.tell() < fin:
            ident, _ = _ebml_num(fh, quitar_marca=False)
            if ident is None:
                return
            tam_e, _ = _ebml_num(fh)
            if tam_e is None:
                return
            ini = fh.tell()
            nombre = IDS_MKV.get(ident)
            final = min(ini + tam_e, fin)
            if nombre in CONT_MKV:
                if nombre == "TrackEntry":
                    ctx["pista"] = {}
                recorre(final, prof + 1)
                if nombre == "TrackEntry":
                    p = ctx["pista"] or {}
                    t = p.get("_tipo")
                    if t == 1:
                        p["tipo"] = "video"
                        d["n_video"] += 1
                    elif t == 2:
                        p["tipo"] = "audio"
                        d["n_audio"] += 1
                    elif t == 17:
                        p["tipo"] = "subtitulo"
                        d["n_subtitulo"] += 1
                    else:
                        p["tipo"] = "otro"
                    p.pop("_tipo", None)
                    d["pistas"].append(p)
                    ctx["pista"] = None
                fh.seek(final)
                continue
            datos = fh.read(tam_e) if tam_e < 1 << 20 else b""
            if nombre == "TimecodeScale":
                ctx["escala"] = int.from_bytes(datos, "big")
            elif nombre == "Duration":
                ctx["dur"] = struct.unpack(">f" if len(datos) == 4 else ">d", datos)[0]
            elif nombre == "TrackType" and ctx["pista"] is not None:
                ctx["pista"]["_tipo"] = int.from_bytes(datos, "big")
            elif nombre == "CodecID" and ctx["pista"] is not None:
                ctx["pista"]["codec"] = datos.decode("latin-1").strip("\x00")
            elif nombre == "PixelWidth" and ctx["pista"] is not None:
                ctx["pista"]["ancho"] = int.from_bytes(datos, "big")
            elif nombre == "PixelHeight" and ctx["pista"] is not None:
                ctx["pista"]["alto"] = int.from_bytes(datos, "big")
            elif nombre == "SamplingFrequency" and ctx["pista"] is not None:
                ctx["pista"]["sample_rate"] = int(
                    struct.unpack(">f" if len(datos) == 4 else ">d", datos)[0])
            elif nombre == "Channels" and ctx["pista"] is not None:
                ctx["pista"]["canales"] = int.from_bytes(datos, "big")
            elif nombre == "BitDepth" and ctx["pista"] is not None:
                ctx["pista"]["profundidad_bits"] = int.from_bytes(datos, "big")
            elif nombre == "Language" and ctx["pista"] is not None:
                ctx["pista"]["idioma"] = datos.decode("latin-1").strip("\x00")
            fh.seek(final)
            # Tras leer Tracks e Info ya esta todo lo que interesa: los Clusters
            # (el 99,9 % del fichero) NO se tocan. Esa es la clave del coste.
            if nombre is None and prof == 1 and d["pistas"] and ctx["dur"]:
                return

    fh.seek(0)
    # cabecera EBML
    _ebml_num(fh, quitar_marca=False)
    t, _ = _ebml_num(fh)
    fh.seek(fh.tell() + t)
    recorre(tam)
    if ctx["dur"]:
        d["duracion_s"] = round(ctx["dur"] * ctx["escala"] / 1e9, 4)
        d["bitrate_bps"] = int(tam * 8 / d["duracion_s"])
    d["n_pistas"] = len(d["pistas"])
    return d


# ---- OGG / OPUS -----------------------------------------------------------

def _ogg(fh, ruta) -> dict:
    tam = os.path.getsize(ruta)
    d = {"formato": "ogg", "categoria": "av", "pistas": [], "n_video": 0,
         "n_audio": 0, "n_subtitulo": 0}
    fh.seek(0)
    cab = fh.read(4096)
    p = {"tipo": "audio"}
    if b"OpusHead" in cab:
        o = cab.index(b"OpusHead")
        p["codec"] = "opus"
        p["canales"] = cab[o + 9]
        preskip = _u16(cab, o + 10, be=False)
        p["sample_rate"] = 48000  # Opus siempre entrega a 48 kHz
        p["sample_rate_entrada"] = _u32(cab, o + 12, be=False)
    elif b"\x01vorbis" in cab:
        o = cab.index(b"\x01vorbis")
        p["codec"] = "vorbis"
        p["canales"] = cab[o + 11]
        p["sample_rate"] = _u32(cab, o + 12, be=False)
        preskip = 0
    else:
        preskip = 0
        p["codec"] = "desconocido"
    # ultima pagina: granulo final -> duracion
    fh.seek(max(0, tam - 65536))
    cola = fh.read(65536)
    pos = cola.rfind(b"OggS")
    if pos >= 0:
        gran = struct.unpack_from("<q", cola, pos + 6)[0]
        d["duracion_s"] = round(max(0, gran - preskip) / 48000.0, 4)
    d["pistas"] = [p]
    d["n_audio"] = 1
    d["n_pistas"] = 1
    if d.get("duracion_s"):
        d["bitrate_bps"] = int(tam * 8 / d["duracion_s"])
    return d


# ---- WAV / RIFF -----------------------------------------------------------

def _wav(fh, ruta) -> dict:
    fh.seek(12)
    d = {"formato": "wav", "categoria": "av", "n_video": 0, "n_audio": 1,
         "n_subtitulo": 0, "n_pistas": 1}
    p = {"tipo": "audio", "codec": "pcm"}
    bytes_datos = 0
    while True:
        cab = fh.read(8)
        if len(cab) < 8:
            break
        tipo, long_ = cab[:4], _u32(cab, 4, be=False)
        if tipo == b"fmt ":
            c = fh.read(long_)
            fmt = _u16(c, 0, be=False)
            p["canales"] = _u16(c, 2, be=False)
            p["sample_rate"] = _u32(c, 4, be=False)
            p["bitrate_bps"] = _u32(c, 8, be=False) * 8
            p["profundidad_bits"] = _u16(c, 14, be=False)
            p["codec"] = "pcm_s%dle" % p["profundidad_bits"] if fmt == 1 else "fmt%d" % fmt
        elif tipo == b"data":
            bytes_datos = long_
            break
        else:
            fh.seek(long_ + (long_ & 1), io.SEEK_CUR)
    if p.get("bitrate_bps"):
        d["duracion_s"] = round(bytes_datos * 8 / p["bitrate_bps"], 4)
        d["bitrate_bps"] = p["bitrate_bps"]
    d["pistas"] = [p]
    return d


# ---- FLAC -----------------------------------------------------------------

def _flac(fh, ruta) -> dict:
    fh.seek(4)
    cab = fh.read(4)
    long_ = int.from_bytes(cab[1:4], "big")
    si = fh.read(long_)
    bits = int.from_bytes(si[10:18], "big")
    sr = bits >> 44
    canales = ((bits >> 41) & 0x7) + 1
    prof = ((bits >> 36) & 0x1F) + 1
    muestras = bits & ((1 << 36) - 1)
    tam = os.path.getsize(ruta)
    d = {"formato": "flac", "categoria": "av", "n_video": 0, "n_audio": 1,
         "n_subtitulo": 0, "n_pistas": 1,
         "duracion_s": round(muestras / sr, 4) if sr else None,
         "bitrate_bps": int(tam * 8 * sr / muestras) if muestras else None,
         "pistas": [{"tipo": "audio", "codec": "flac", "canales": canales,
                     "sample_rate": sr, "profundidad_bits": prof}]}
    return d


# ---- MP3 ------------------------------------------------------------------

_MP3_BR = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
_MP3_SR = {0: 44100, 1: 48000, 2: 32000}


def _mp3(fh, ruta) -> dict:
    tam = os.path.getsize(ruta)
    fh.seek(0)
    cab = fh.read(10)
    desp = 0
    if cab[:3] == b"ID3":
        desp = 10 + ((cab[6] & 0x7F) << 21 | (cab[7] & 0x7F) << 14 |
                     (cab[8] & 0x7F) << 7 | (cab[9] & 0x7F))
    fh.seek(desp)
    bloque = fh.read(8192)
    i = 0
    while i < len(bloque) - 4:
        if bloque[i] == 0xFF and (bloque[i + 1] & 0xE0) == 0xE0:
            break
        i += 1
    h = bloque[i:i + 4]
    d = {"formato": "mp3", "categoria": "av", "n_video": 0, "n_audio": 1,
         "n_subtitulo": 0, "n_pistas": 1}
    if len(h) == 4:
        br = _MP3_BR[(h[2] >> 4) & 0xF] * 1000
        sr = _MP3_SR.get((h[2] >> 2) & 0x3, 44100)
        modo = (h[3] >> 6) & 0x3
        canales = 1 if modo == 3 else 2
        # Xing/Info -> numero de tramas (VBR fiable)
        cola = bloque[i:i + 1024]
        muestras = None
        for marca in (b"Xing", b"Info"):
            if marca in cola:
                o = cola.index(marca)
                flags = _u32(cola, o + 4)
                if flags & 1:
                    muestras = _u32(cola, o + 8) * 1152
                # Extension LAME (desplazamiento fijo 141 desde la marca):
                # retardo del codificador + relleno. SIN restarlos, la duracion
                # sale 45 ms larga y la regla A1 (+-10 ms) da un falso fallo.
                if muestras and len(cola) >= o + 144:
                    tri = cola[o + 141:o + 144]
                    retardo = (tri[0] << 4) | (tri[1] >> 4)
                    relleno = ((tri[1] & 0xF) << 8) | tri[2]
                    if 0 <= retardo + relleno < muestras:
                        muestras -= retardo + relleno
                break
        if muestras and sr:
            dur = muestras / sr
        else:
            dur = (tam - desp) * 8 / br if br else None
        d["duracion_s"] = round(dur, 4) if dur else None
        d["bitrate_bps"] = int(tam * 8 / dur) if dur else br
        d["pistas"] = [{"tipo": "audio", "codec": "mp3", "canales": canales,
                        "sample_rate": sr, "bitrate_bps": br}]
    return d


# ---- PDF ------------------------------------------------------------------

def _pdf(fh, ruta) -> dict:
    """Cuenta paginas y lee el MediaBox sin Ghostscript.

    No descomprime flujos: cuenta objetos '/Type /Page'. Si el PDF usa
    flujos de objetos comprimidos (xref stream), cae a '/Count'.
    """
    datos = fh.read()
    d = {"formato": "pdf", "categoria": "pdf"}
    n = 0
    i = 0
    while True:
        i = datos.find(b"/Type", i)
        if i < 0:
            break
        j = i + 5
        while j < len(datos) and datos[j] in b" \r\n\t":
            j += 1
        if datos[j:j + 5] == b"/Page" and datos[j + 5:j + 6] not in (b"s",):
            n += 1
        i += 5
    if n == 0:
        k = datos.rfind(b"/Count")
        if k >= 0:
            try:
                n = int(datos[k + 6:k + 16].split()[0])
            except (ValueError, IndexError):
                n = 0
        d["paginas_por_flujo_comprimido"] = True
    d["n_paginas"] = n
    k = datos.find(b"/MediaBox")
    if k >= 0:
        try:
            cuerpo = datos[k + 9:datos.index(b"]", k)].strip(b" [")
            nums = [float(x) for x in cuerpo.split()]
            d["ancho_pt"] = round(nums[2] - nums[0], 2)
            d["alto_pt"] = round(nums[3] - nums[1], 2)
        except (ValueError, IndexError):
            pass
    # Indicio barato de capa de texto: operadores de texto en flujos sin comprimir
    d["indicio_texto"] = b"/Font" in datos
    d["version"] = datos[5:8].decode("latin-1", "replace")
    return d


# ---- DATOS TABULARES ------------------------------------------------------

def _datos(ruta: str) -> dict:
    with open(ruta, "rb") as fh:
        crudo = fh.read()
    d = {"categoria": "datos", "bom_utf8": crudo[:3] == b"\xef\xbb\xbf",
         "crlf": b"\r\n" in crudo}
    try:
        texto = crudo.decode("utf-8-sig")
        d["utf8_valido"] = True
    except UnicodeDecodeError:
        d["utf8_valido"] = False
        texto = crudo.decode("latin-1")
    d["reemplazo_ufffd"] = "�" in texto
    d["no_ascii"] = any(ord(c) > 127 for c in texto)
    d["n_lineas_fisicas"] = texto.count("\n") + (0 if texto.endswith("\n") else 1)
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".json":
        d["formato"] = "json"
        try:
            obj = json.loads(texto)
            d["json_valido"] = True
            if isinstance(obj, dict):
                d["json_claves"] = sorted(obj.keys())
                d["filas_datos"] = 1
                for v in obj.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        d["csv_n_filas"] = d["filas_datos"] = len(v)
                        d["csv_cabecera"] = sorted(v[0].keys())
            elif isinstance(obj, list):
                d["csv_n_filas"] = d["filas_datos"] = len(obj)
                if obj and isinstance(obj[0], dict):
                    d["csv_cabecera"] = sorted(obj[0].keys())
        except json.JSONDecodeError as e:
            d["json_valido"] = False
            d["error"] = str(e)
    else:
        d["formato"] = "csv"
        filas = list(csv.reader(io.StringIO(texto, newline="")))
        filas = [f for f in filas if f]
        d["csv_filas"] = filas
        d["csv_n_filas"] = len(filas)
        d["csv_n_campos_por_fila"] = [len(f) for f in filas]
        d["csv_cabecera"] = filas[0] if filas else []
        # Un CSV cuenta su cabecera como fila y un JSON de objetos no. Comparar
        # 'n_filas' entre ambos da un desfase de 1 que parece perdida de datos.
        d["filas_datos"] = max(0, len(filas) - 1)
    return d


# ===========================================================================
# MINIMO DEL CANAL ALFA, EN PROCESO — la trampa nº 1 ("alfa trivial")
#
# Es el UNICO dato del contrato que exige decodificar pixeles. Con ImageMagick
# (`magick -format "%[fx:minima.a]"`) cuesta 734,6 ms sobre un PNG de
# 1920x1080: 1.975x la verificacion completa en proceso. Aqui se calcula
# leyendo el fichero con zlib y reconstruyendo SOLO el carril de bytes del
# canal alfa.
#
# La clave del coste esta en dos observaciones:
#
#   (a) Los filtros de PNG operan por BYTE con desplazamiento bpp: el byte i
#       solo depende de bytes con el mismo residuo modulo bpp. Por tanto el
#       canal alfa se puede reconstruir SIN tocar R, G ni B: 1 byte de cada 4
#       (RGBA8) o 2 de cada 8 (RGBA16).
#
#   (b) "La fila es 100 % opaca" se puede decidir SIN reconstruir nada. Si la
#       fila anterior es toda 0xFF, el carril alfa FILTRADO de una fila opaca
#       tiene una forma fija por tipo de filtro (ver _PATRON_OPACO). Es una
#       comparacion de bytes en C, no un bucle en Python. Solo cuando el
#       patron falla se reconstruye de verdad — y entonces ya hay alfa real,
#       asi que se corta en el primer pixel no opaco.
#
# Resultado: el caso peor (imagen enteramente opaca, que obliga a recorrerla
# entera) cuesta lo que cuesta descomprimir; el caso mejor (transparencia real
# en las primeras filas) corta en microsegundos.
# ===========================================================================

# (primer byte, resto) que tiene el carril alfa FILTRADO de una fila 100 %
# opaca, por tipo de filtro, sabiendo que la fila anterior tambien lo es.
# Deducido de la definicion de los filtros de la norma PNG (RFC 2083 §6):
#   0 None    recon = filt                      -> filt = 0xFF
#   1 Sub     recon = filt + izq                -> 0xFF y luego 0
#   2 Up      recon = filt + arriba             -> 0 (0xFF en la primera fila)
#   3 Average recon = filt + (izq+arriba)>>1    -> 0x80 y luego 0
#   4 Paeth   recon = filt + paeth(i,a,ia)      -> 0
_PATRON_OPACO = {
    False: {0: (255, 255), 1: (255, 0), 2: (0, 0), 3: (128, 0), 4: (0, 0)},
    True: {0: (255, 255), 1: (255, 0), 2: (255, 255), 3: (255, 128), 4: (255, 0)},
}

_FFS = {}  # cache de b"\xff" * n


def _rep(valor: int, n: int) -> bytes:
    if valor == 0:
        return bytes(n)
    clave = (valor, n)
    if clave not in _FFS:
        _FFS[clave] = bytes([valor]) * n
    return _FFS[clave]


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _desfiltrar_carril(filtro, filt, previo):
    """Reconstruye UN carril de bytes (residuo fijo modulo bpp) de una fila."""
    n = len(filt)
    if filtro == 0:
        return bytearray(filt)
    out = bytearray(n)
    if filtro == 1:
        a = 0
        for j in range(n):
            a = (filt[j] + a) & 255
            out[j] = a
    elif filtro == 2:
        for j in range(n):
            out[j] = (filt[j] + previo[j]) & 255
    elif filtro == 3:
        a = 0
        for j in range(n):
            a = (filt[j] + ((a + previo[j]) >> 1)) & 255
            out[j] = a
    elif filtro == 4:
        a = c = 0
        for j in range(n):
            b = previo[j]
            a = (filt[j] + _paeth(a, b, c)) & 255
            out[j] = a
            c = b
    else:
        raise ValueError("filtro PNG desconocido: %r" % filtro)
    return out


def _png_meta(fh) -> dict:
    """Cabecera de un PNG hasta el PRIMER IDAT. No lee ni un byte de pixel."""
    fh.seek(8)
    m = {"plte": 0, "trns": None, "pos_idat": None}
    while True:
        cab = fh.read(8)
        if len(cab) < 8:
            break
        ln, tipo = _u32(cab, 0), cab[4:8]
        if tipo == b"IHDR":
            c = fh.read(ln)
            m["ancho"], m["alto"] = _u32(c, 0), _u32(c, 4)
            m["prof"], m["color"], m["entrelazado"] = c[8], c[9], c[12]
        elif tipo == b"PLTE":
            m["plte"] = ln // 3
            fh.seek(ln, io.SEEK_CUR)
        elif tipo == b"tRNS":
            m["trns"] = fh.read(ln)
        elif tipo == b"IDAT":
            m["pos_idat"] = fh.tell() - 8
            break
        elif tipo == b"IEND":
            break
        else:
            fh.seek(ln, io.SEEK_CUR)
        fh.seek(4, io.SEEK_CUR)  # CRC
    return m


def _png_bloques_idat(fh, pos):
    """Genera los bloques crudos de los IDAT. PEREZOSO: si el consumidor corta
    en la fila 3, no se lee el resto del fichero."""
    fh.seek(pos)
    while True:
        cab = fh.read(8)
        if len(cab) < 8:
            return
        ln, tipo = _u32(cab, 0), cab[4:8]
        if tipo == b"IDAT":
            yield fh.read(ln)
            fh.seek(4, io.SEEK_CUR)
        elif tipo == b"IEND":
            return
        else:
            fh.seek(ln + 4, io.SEEK_CUR)


def _png_filas(fh, pos, tam_fila):
    """Genera (filtro, bytes_de_la_fila) descomprimiendo lo justo."""
    do = zlib.decompressobj()
    buf = bytearray()
    paso = tam_fila + 1
    for bloque in _png_bloques_idat(fh, pos):
        buf += do.decompress(bloque)
        while len(buf) >= paso:
            yield buf[0], bytes(buf[1:paso])
            del buf[:paso]
    try:
        buf += do.flush()
    except zlib.error:
        pass
    while len(buf) >= paso:
        yield buf[0], bytes(buf[1:paso])
        del buf[:paso]


def _alfa_min_png(ruta: str, exacto: bool = False) -> dict:
    r = {"formato": "png", "evaluable": True, "exacto": True, "tiene_alfa": False,
         "alfa_min": 1.0, "primer_transparente": None, "filas_leidas": 0,
         "via": "cabecera"}
    with open(ruta, "rb") as fh:
        m = _png_meta(fh)
        ct, bd = m.get("color"), m.get("prof")
        an, al = m.get("ancho"), m.get("alto")
        if ct is None:
            return dict(r, evaluable=False, motivo="IHDR ilegible")
        # Sin ningun mecanismo de transparencia: opaco por construccion y el
        # coste es el de leer la cabecera. Cubre el 90 % del corpus real.
        if m["trns"] is None and ct not in (4, 6):
            return r
        r["tiene_alfa"] = True
        if m["entrelazado"]:
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="PNG entrelazado (Adam7): no implementado")
        if ct in (0, 2):
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="tRNS de color clave (ct=%d): exige comparar el "
                               "valor de cada pixel, no hay canal alfa" % ct)
        if m["pos_idat"] is None:
            return dict(r, evaluable=False, alfa_min=None, motivo="sin IDAT")

        # ---------- PNG de paleta con tRNS ----------
        if ct == 3:
            trns = m["trns"]
            alfa = [255] * 256
            for i, v in enumerate(trns[:256]):
                alfa[i] = v
            if min(alfa) == 255:
                return r  # tRNS presente pero enteramente opaco
            if bd == 8:
                tabla = bytes(alfa)
            else:  # 1, 2 o 4 bits por pixel: la tabla mapea el byte EMPAQUETADO
                por_byte = 8 // bd
                masc = (1 << bd) - 1
                tabla = bytes(min(alfa[(v >> (8 - bd * (k + 1))) & masc]
                                  for k in range(por_byte)) for v in range(256))
            tam_fila = (an * bd + 7) // 8
            bits_utiles = an * bd
            sobra = tam_fila * 8 - bits_utiles
            previo = bytearray(tam_fila)
            mn = 255
            r["via"] = "paleta+tRNS"
            for y, (filtro, filt) in enumerate(_png_filas(fh, m["pos_idat"], tam_fila)):
                fila = _desfiltrar_carril(filtro, filt, previo)
                previo = fila
                r["filas_leidas"] = y + 1
                car = fila.translate(tabla)
                if sobra and bd < 8 and len(car):
                    # los bits de relleno de la ultima celda no son pixeles
                    ultimo = fila[-1]
                    valid = [alfa[(ultimo >> (8 - bd * (k + 1))) & masc]
                             for k in range(por_byte - sobra // bd)]
                    car = car[:-1] + bytes([min(valid)] if valid else [])
                v = min(car) if car else 255
                if v < mn:
                    mn = v
                    if r["primer_transparente"] is None:
                        r["primer_transparente"] = (car.index(v), y)
                if mn == 0 or (mn < 255 and not exacto):
                    break
            r["alfa_min"] = mn / 255.0
            r["exacto"] = exacto or mn == 255 or mn == 0
            return r

        # ---------- PNG con canal alfa real (ct 4 = gris+alfa, 6 = RGBA) ----------
        canales = 4 if ct == 6 else 2
        bps = bd // 8
        if bps not in (1, 2):
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="profundidad %d no valida para ct=%d" % (bd, ct))
        bpp = canales * bps
        tam_fila = an * bpp
        desp = (canales - 1) * bps
        maxv = 255
        rapido = True           # seguimos en el carril rapido "todo opaco"
        previos = None
        mn_pareja = (1 << (8 * bps)) - 1
        r["via"] = "carril alfa (%d de cada %d bytes)" % (bps, bpp)
        for y, (filtro, filt) in enumerate(_png_filas(fh, m["pos_idat"], tam_fila)):
            r["filas_leidas"] = y + 1
            carriles = [filt[desp + k::bpp] for k in range(bps)]
            if rapido:
                b0, resto = _PATRON_OPACO[y == 0].get(filtro, (None, None))
                if b0 is None:
                    return dict(r, evaluable=False, alfa_min=None,
                                motivo="filtro PNG %r desconocido" % filtro)
                if all(c[:1] == bytes([b0]) and c[1:] == _rep(resto, len(c) - 1)
                       for c in carriles):
                    continue                       # fila 100 % opaca, demostrado
                # el patron falla: hay alfa real en esta fila. A partir de aqui
                # se reconstruye de verdad, con la fila anterior = todo 0xFF.
                rapido = False
                previos = [bytearray(_rep(0 if y == 0 else maxv, an))
                           for _ in range(bps)]
            rec = [_desfiltrar_carril(filtro, c, previos[k])
                   for k, c in enumerate(carriles)]
            previos = rec
            if bps == 1:
                v = min(rec[0])
                if v < mn_pareja:
                    mn_pareja = v
                    if r["primer_transparente"] is None:
                        r["primer_transparente"] = (rec[0].index(v), y)
            else:
                hi, lo = rec[0], rec[1]
                if min(hi) < 255:
                    for j in range(an):
                        v = (hi[j] << 8) | lo[j]
                        if v < mn_pareja:
                            mn_pareja = v
                            if r["primer_transparente"] is None:
                                r["primer_transparente"] = (j, y)
            if mn_pareja == 0 or (mn_pareja < ((1 << (8 * bps)) - 1) and not exacto):
                break
        tope = (1 << (8 * bps)) - 1
        r["alfa_min"] = mn_pareja / float(tope)
        r["exacto"] = exacto or rapido or mn_pareja in (0, tope)
        return r


# ---- WebP -----------------------------------------------------------------
#
# WebP guarda el alfa de tres maneras distintas:
#   * VP8  (con perdida) SIN trozo ALPH  -> no hay alfa: min = 1.0, gratis.
#   * VP8  + ALPH con compresion 0       -> plano de bytes en crudo, con un
#                                           filtro horizontal/vertical/gradiente.
#   * VP8  + ALPH con compresion 1       -> el plano alfa va codificado como
#                                           una imagen VP8L (sin perdida) cuyo
#                                           canal VERDE lleva el alfa.
#   * VP8L (sin perdida)                 -> alfa dentro del flujo ARGB.
# Los dos ultimos exigen un decodificador VP8L completo (_vp8l_decodificar).

def _alfa_min_webp(ruta: str, exacto: bool = False) -> dict:
    r = {"formato": "webp", "evaluable": True, "exacto": True, "tiene_alfa": False,
         "alfa_min": 1.0, "primer_transparente": None, "via": "cabecera"}
    with open(ruta, "rb") as fh:
        datos = fh.read()
    if len(datos) < 16 or datos[:4] != b"RIFF" or datos[8:12] != b"WEBP":
        return dict(r, evaluable=False, alfa_min=None, motivo="no es un RIFF/WEBP")
    i = 12
    alph = None
    vp8l = None
    an = al = None
    while i + 8 <= len(datos):
        tipo = datos[i:i + 4]
        ln = int.from_bytes(datos[i + 4:i + 8], "little")
        cuerpo = datos[i + 8:i + 8 + ln]
        if tipo == b"VP8X":
            an = 1 + int.from_bytes(cuerpo[4:7], "little")
            al = 1 + int.from_bytes(cuerpo[7:10], "little")
        elif tipo == b"ALPH":
            alph = cuerpo
        elif tipo == b"VP8L":
            vp8l = cuerpo
        elif tipo == b"VP8 " and an is None and len(cuerpo) >= 10:
            an = _u16(cuerpo, 6, be=False) & 0x3FFF
            al = _u16(cuerpo, 8, be=False) & 0x3FFF
        elif tipo == b"ANMF":
            return dict(r, evaluable=False, alfa_min=None, tiene_alfa=True,
                        motivo="WebP animado: no implementado")
        i += 8 + ln + (ln & 1)

    if alph is None and vp8l is None:
        return r  # ni ALPH ni VP8L: WebP con perdida sin alfa. Coste: cabecera.

    if alph is not None:
        r["tiene_alfa"] = True
        cab = alph[0]
        preproc, filtro, compr = (cab >> 4) & 3, (cab >> 2) & 3, cab & 3
        if an is None or al is None:
            return dict(r, evaluable=False, alfa_min=None, motivo="sin dimensiones")
        if compr == 0:
            plano = alph[1:1 + an * al]
            r["via"] = "ALPH crudo (filtro %d)" % filtro
        elif compr == 1:
            try:
                px = _vp8l_decodificar(alph[1:], an, al, plano_alfa=True)
            except Exception as e:                      # noqa: BLE001
                return dict(r, evaluable=False, alfa_min=None,
                            motivo="VP8L del plano alfa ilegible: %s: %s"
                                   % (type(e).__name__, e))
            plano = px
            r["via"] = "ALPH comprimido sin perdida (VP8L)"
        else:
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="compresion ALPH %d desconocida" % compr)
        if preproc not in (0, 1):
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="preproceso ALPH %d desconocido" % preproc)
        plano = _alph_desfiltrar(plano, an, al, filtro)
        mn = min(plano) if plano else 255
        r["alfa_min"] = mn / 255.0
        if mn < 255:
            k = plano.index(mn)
            r["primer_transparente"] = (k % an, k // an)
        return r

    # VP8L puro. La cabecera lleva un bit 'alpha_is_used' que el codificador
    # pone a 0 cuando TODOS los alfa valen 255 (libwebp:
    # has_alpha = WebPPictureHasTransparency). Cuando vale 0 no hace falta
    # decodificar nada: es la diferencia entre 0,1 ms y 2,3 s en 1920x1080.
    if len(vp8l) >= 5 and vp8l[0] == 0x2F:
        cab5 = int.from_bytes(vp8l[1:5], "little")
        if not ((cab5 >> 28) & 1):
            return dict(r, via="cabecera VP8L (alpha_is_used=0)")
    try:
        px = _vp8l_decodificar(vp8l, None, None, plano_alfa=False)
    except Exception as e:                              # noqa: BLE001
        return dict(r, evaluable=False, alfa_min=None,
                    motivo="VP8L ilegible: %s: %s" % (type(e).__name__, e))
    an2, al2, argb = px
    alfas = argb[3::4] if isinstance(argb, (bytes, bytearray)) else None
    if alfas is None:
        return dict(r, evaluable=False, alfa_min=None, motivo="VP8L sin plano alfa")
    mn = min(alfas) if alfas else 255
    r["tiene_alfa"] = mn < 255
    r["via"] = "VP8L"
    r["alfa_min"] = mn / 255.0
    if mn < 255:
        k = alfas.index(mn)
        r["primer_transparente"] = (k % an2, k // an2)
    return r


# ---- decodificador VP8L (WebP sin perdida) --------------------------------
#
# Es el precio de cubrir WebP: el plano alfa de un WebP con perdida va
# codificado como una imagen VP8L completa (Huffman + cache de color +
# referencias hacia atras + hasta cuatro transformaciones). No hay atajo: o se
# escribe el decodificador o se devuelve "no evaluable".

class _BitsLSB:
    """Lector de bits LSB primero, como exige VP8L."""

    __slots__ = ("d", "pos", "acc", "n")

    def __init__(self, datos):
        self.d = datos
        self.pos = 0
        self.acc = 0
        self.n = 0

    def _llenar(self, k):
        while self.n < k and self.pos < len(self.d):
            self.acc |= self.d[self.pos] << self.n
            self.pos += 1
            self.n += 8

    def leer(self, k):
        if k <= 0:
            return 0
        self._llenar(k)
        v = self.acc & ((1 << k) - 1)
        self.acc >>= k
        self.n -= k
        return v

    def ojear(self, k):
        if k <= 0:
            return 0
        self._llenar(k)
        return self.acc & ((1 << k) - 1)

    def saltar(self, k):
        self.acc >>= k
        self.n -= k


_ORDEN_LONG = (17, 18, 0, 1, 2, 3, 4, 5, 16, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
_REP_EXTRA = (2, 3, 7)
_REP_DESP = (3, 3, 11)
_ALFABETOS = (256 + 24, 256, 256, 256, 40)
_PRESUPUESTO_TABLAS = 4 << 20  # techo de entradas de tabla Huffman


def _codigo_a_plano():
    """Los 120 codigos de plano de VP8L son los desplazamientos (dx, dy) con
    dy en 0..7 y dx en -7..8 (dist >= 1) ORDENADOS por distancia euclidea, y
    a igual distancia por dy descendente y dx positivo antes que negativo.
    Se genera en vez de copiarse: la tabla de libwebp es exactamente esta."""
    pares = [(dx, dy) for dy in range(8) for dx in range(-7, 9)
             if not (dy == 0 and dx <= 0)]
    pares.sort(key=lambda p: (p[0] * p[0] + p[1] * p[1], -p[1], p[0] < 0))
    return pares


_PLANOS = _codigo_a_plano()


def _distancia_plano(xsize, cod):
    if cod > 120:
        return cod - 120
    dx, dy = _PLANOS[cod - 1]
    d = dy * xsize + dx
    return d if d >= 1 else 1


def _huff_tabla(longitudes):
    """Codigo canonico MSB-primero volcado a tabla plana para lectura LSB."""
    activos = [(s, l) for s, l in enumerate(longitudes) if l]
    if not activos:
        raise ValueError("codigo Huffman vacio")
    if len(activos) == 1:
        # Un solo simbolo: VP8L NO consume ningun bit (igual que libwebp).
        return ([(activos[0][0], 0)], 0)
    maxl = max(l for _, l in activos)
    if maxl > 15:
        raise ValueError("longitud de codigo %d > 15" % maxl)
    cuenta = [0] * (maxl + 1)
    for _, l in activos:
        cuenta[l] += 1
    codigo = 0
    siguiente = [0] * (maxl + 1)
    for l in range(1, maxl + 1):
        codigo = (codigo + cuenta[l - 1]) << 1
        siguiente[l] = codigo
    tam = 1 << maxl
    tabla = [None] * tam
    for sim, l in activos:
        c = siguiente[l]
        siguiente[l] += 1
        rev = 0
        for k in range(l):
            rev |= ((c >> (l - 1 - k)) & 1) << k
        for idx in range(rev, tam, 1 << l):
            tabla[idx] = (sim, l)
    return (tabla, maxl)


def _leer_simbolo(br, tabla):
    t, maxl = tabla
    e = t[br.ojear(maxl)]
    if e is None:
        raise ValueError("codigo Huffman invalido")
    if e[1]:
        br.saltar(e[1])
    return e[0]


def _leer_longitudes(br, tabla_cl, n):
    longitudes = [0] * n
    if br.leer(1):
        nbits = 2 + 2 * br.leer(3)
        max_sim = 2 + br.leer(nbits)
    else:
        max_sim = n
    sim = 0
    previa = 8
    while sim < n and max_sim > 0:
        max_sim -= 1
        cl = _leer_simbolo(br, tabla_cl)
        if cl < 16:
            longitudes[sim] = cl
            sim += 1
            if cl:
                previa = cl
        else:
            ranura = cl - 16
            rep = br.leer(_REP_EXTRA[ranura]) + _REP_DESP[ranura]
            if sim + rep > n:
                raise ValueError("repeticion de longitudes fuera de rango")
            valor = previa if cl == 16 else 0
            for _ in range(rep):
                longitudes[sim] = valor
                sim += 1
    return longitudes


def _leer_codigo_huffman(br, n):
    if br.leer(1):  # codigo "simple": 1 o 2 simbolos
        n_sim = br.leer(1) + 1
        longitudes = [0] * n
        primero = br.leer(8) if br.leer(1) else br.leer(1)
        if primero >= n:
            raise ValueError("simbolo simple fuera del alfabeto")
        longitudes[primero] = 1
        if n_sim == 2:
            segundo = br.leer(8)
            if segundo >= n:
                raise ValueError("segundo simbolo fuera del alfabeto")
            longitudes[segundo] = 1
        return _huff_tabla(longitudes)
    cl = [0] * 19
    ncod = br.leer(4) + 4
    for i in range(ncod):
        cl[_ORDEN_LONG[i]] = br.leer(3)
    return _huff_tabla(_leer_longitudes(br, _huff_tabla(cl), n))


def _prefijo(br, sim):
    """Codigo de prefijo de longitud/distancia de VP8L."""
    if sim < 4:
        return sim + 1
    extra = (sim - 2) >> 1
    return ((2 + (sim & 1)) << extra) + br.leer(extra) + 1


def _suma_argb(a, b):
    return ((((a >> 24) + (b >> 24)) & 0xFF) << 24 |
            ((((a >> 16) & 0xFF) + ((b >> 16) & 0xFF)) & 0xFF) << 16 |
            ((((a >> 8) & 0xFF) + ((b >> 8) & 0xFF)) & 0xFF) << 8 |
            (((a & 0xFF) + (b & 0xFF)) & 0xFF))


def _med2(a, b):
    return (((a ^ b) & 0xFEFEFEFE) >> 1) + (a & b)


def _selecciona(a, b, c):
    d = 0
    for desp in (24, 16, 8, 0):
        av, bv, cv = (a >> desp) & 0xFF, (b >> desp) & 0xFF, (c >> desp) & 0xFF
        d += abs(bv - cv) - abs(av - cv)
    return a if d <= 0 else b


def _clamp_full(a, b, c):
    v = 0
    for desp in (24, 16, 8, 0):
        x = ((a >> desp) & 0xFF) + ((b >> desp) & 0xFF) - ((c >> desp) & 0xFF)
        v |= (0 if x < 0 else (255 if x > 255 else x)) << desp
    return v


def _clamp_half(a, b, c):
    m = _med2(a, b)
    v = 0
    for desp in (24, 16, 8, 0):
        av = (m >> desp) & 0xFF
        x = av + (av - ((c >> desp) & 0xFF)) // 2
        v |= (0 if x < 0 else (255 if x > 255 else x)) << desp
    return v


def _predice(modo, px, i, w):
    L = px[i - 1]
    T = px[i - w]
    TL = px[i - w - 1]
    TR = px[i - w + 1]
    if modo == 0:
        return 0xFF000000
    if modo == 1:
        return L
    if modo == 2:
        return T
    if modo == 3:
        return TR
    if modo == 4:
        return TL
    if modo == 5:
        return _med2(_med2(L, TR), T)
    if modo == 6:
        return _med2(L, TL)
    if modo == 7:
        return _med2(L, T)
    if modo == 8:
        return _med2(TL, T)
    if modo == 9:
        return _med2(T, TR)
    if modo == 10:
        return _med2(_med2(L, TL), _med2(T, TR))
    if modo == 11:
        return _selecciona(T, L, TL)
    if modo == 12:
        return _clamp_full(L, T, TL)
    if modo == 13:
        return _clamp_half(L, T, TL)
    raise ValueError("predictor VP8L %d desconocido" % modo)


def _vp8l_flujo(br, xsize, ysize, nivel0, gasto):
    """DecodeImageStream de VP8L. Devuelve (ancho, alto, pixeles ARGB)."""
    transformaciones = []
    vistas = set()
    if nivel0:
        while br.leer(1):
            tipo = br.leer(2)
            if tipo in vistas:
                raise ValueError("transformacion VP8L repetida")
            vistas.add(tipo)
            if tipo in (0, 1):  # predictor / color cruzado
                bits = br.leer(3) + 2
                bx = (xsize + (1 << bits) - 1) >> bits
                by = (ysize + (1 << bits) - 1) >> bits
                _, _, datos = _vp8l_flujo(br, bx, by, False, gasto)
                transformaciones.append((tipo, bits, bx, datos, xsize))
            elif tipo == 2:  # restar verde
                transformaciones.append((2, 0, 0, None, xsize))
            elif tipo == 3:  # indexado de color (paleta)
                ncol = br.leer(8) + 1
                bits = 0 if ncol > 16 else (1 if ncol > 4 else (2 if ncol > 2 else 3))
                _, _, pal = _vp8l_flujo(br, ncol, 1, False, gasto)
                for i in range(1, ncol):
                    pal[i] = _suma_argb(pal[i], pal[i - 1])
                transformaciones.append((3, bits, ncol, pal, xsize))
                xsize = (xsize + (1 << bits) - 1) >> bits
            else:
                raise ValueError("transformacion VP8L %d desconocida" % tipo)

    bits_cache = br.leer(4) if br.leer(1) else 0
    if bits_cache > 11:
        raise ValueError("cache de color de %d bits" % bits_cache)

    meta = None
    prec = mxs = 0
    ngrupos = 1
    if nivel0 and br.leer(1):
        prec = br.leer(3) + 2
        mxs = (xsize + (1 << prec) - 1) >> prec
        mys = (ysize + (1 << prec) - 1) >> prec
        _, _, mimg = _vp8l_flujo(br, mxs, mys, False, gasto)
        meta = [(p >> 8) & 0xFFFF for p in mimg]
        ngrupos = max(meta) + 1

    grupos = []
    for _ in range(ngrupos):
        g = []
        for j in range(5):
            n = _ALFABETOS[j] + ((1 << bits_cache) if (j == 0 and bits_cache) else 0)
            t = _leer_codigo_huffman(br, n)
            gasto[0] += len(t[0])
            if gasto[0] > _PRESUPUESTO_TABLAS:
                raise ValueError("presupuesto de tablas Huffman agotado")
            g.append(t)
        grupos.append(g)

    total = xsize * ysize
    px = [0] * total
    cache = [0] * (1 << bits_cache) if bits_cache else None
    desp_cache = 32 - bits_cache
    ult = 0
    pos = x = y = 0
    g0 = grupos[0]
    while pos < total:
        g = grupos[meta[(y >> prec) * mxs + (x >> prec)]] if meta is not None else g0
        cod = _leer_simbolo(br, g[0])
        if cod < 256:
            rr = _leer_simbolo(br, g[1])
            bb = _leer_simbolo(br, g[2])
            aa = _leer_simbolo(br, g[3])
            px[pos] = (aa << 24) | (rr << 16) | (cod << 8) | bb
            pos += 1
            x += 1
            if x >= xsize:
                x = 0
                y += 1
        elif cod < 280:
            lon = _prefijo(br, cod - 256)
            d = _distancia_plano(xsize, _prefijo(br, _leer_simbolo(br, g[4])))
            if d > pos or pos + lon > total:
                raise ValueError("referencia hacia atras fuera de rango")
            for _ in range(lon):
                px[pos] = px[pos - d]
                pos += 1
            x = pos % xsize
            y = pos // xsize
        else:
            px[pos] = cache[cod - 280]
            pos += 1
            x += 1
            if x >= xsize:
                x = 0
                y += 1
        if cache is not None:
            while ult < pos:
                v = px[ult]
                cache[((0x1E35A7BD * v) & 0xFFFFFFFF) >> desp_cache] = v
                ult += 1

    # las transformaciones se deshacen en orden inverso
    ancho = xsize
    for tipo, bits, aux, datos, ancho_antes in reversed(transformaciones):
        if tipo == 0:
            for yy in range(ysize):
                fila = yy * ancho
                for xx in range(ancho):
                    i = fila + xx
                    if xx == 0 and yy == 0:
                        pred = 0xFF000000
                    elif yy == 0:
                        pred = px[i - 1]
                    elif xx == 0:
                        pred = px[i - ancho]
                    else:
                        modo = (datos[(yy >> bits) * aux + (xx >> bits)] >> 8) & 0xFF
                        pred = _predice(modo, px, i, ancho)
                    px[i] = _suma_argb(px[i], pred)
        elif tipo == 1:
            for yy in range(ysize):
                fila = yy * ancho
                for xx in range(ancho):
                    i = fila + xx
                    m = datos[(yy >> bits) * aux + (xx >> bits)]
                    g2r = (m & 0xFF) - 256 if (m & 0xFF) > 127 else (m & 0xFF)
                    g2b = ((m >> 8) & 0xFF) - 256 if ((m >> 8) & 0xFF) > 127 else ((m >> 8) & 0xFF)
                    r2b = ((m >> 16) & 0xFF) - 256 if ((m >> 16) & 0xFF) > 127 else ((m >> 16) & 0xFF)
                    v = px[i]
                    verde = (v >> 8) & 0xFF
                    vs = verde - 256 if verde > 127 else verde
                    nr = (((v >> 16) & 0xFF) + ((g2r * vs) >> 5)) & 0xFF
                    nrs = nr - 256 if nr > 127 else nr
                    nb = ((v & 0xFF) + ((g2b * vs) >> 5) + ((r2b * nrs) >> 5)) & 0xFF
                    px[i] = (v & 0xFF00FF00) | (nr << 16) | nb
        elif tipo == 2:
            for i in range(len(px)):
                v = px[i]
                verde = (v >> 8) & 0xFF
                px[i] = ((v & 0xFF00FF00) |
                         ((((v >> 16) & 0xFF) + verde) & 0xFF) << 16 |
                         (((v & 0xFF) + verde) & 0xFF))
        elif tipo == 3:
            pal = datos
            npal = len(pal)
            if bits == 0:
                for i in range(len(px)):
                    k = (px[i] >> 8) & 0xFF
                    px[i] = pal[k] if k < npal else 0
            else:
                ppb = 1 << bits
                bpp_ = 8 >> bits
                masc = (1 << bpp_) - 1
                nuevo = [0] * (ancho_antes * ysize)
                for yy in range(ysize):
                    src = yy * ancho
                    dst = yy * ancho_antes
                    for xx in range(ancho_antes):
                        emp = (px[src + (xx >> bits)] >> 8) & 0xFF
                        k = (emp >> ((xx & (ppb - 1)) * bpp_)) & masc
                        nuevo[dst + xx] = pal[k] if k < npal else 0
                px = nuevo
            ancho = ancho_antes
    return ancho, ysize, px


def _vp8l_decodificar(datos, an, al, plano_alfa=False):
    """plano_alfa=True: flujo VP8L sin cabecera cuyo canal VERDE lleva el alfa
    (asi codifica libwebp el trozo ALPH). Devuelve el plano de bytes.
    plano_alfa=False: trozo VP8L completo. Devuelve (ancho, alto, RGBA)."""
    br = _BitsLSB(datos)
    gasto = [0]
    if plano_alfa:
        w, h, px = _vp8l_flujo(br, an, al, True, gasto)
        return bytearray((p >> 8) & 0xFF for p in px)
    if not datos or datos[0] != 0x2F:
        raise ValueError("firma VP8L ausente")
    br.leer(8)
    w = br.leer(14) + 1
    h = br.leer(14) + 1
    br.leer(1)  # alpha_is_used
    if br.leer(3) != 0:
        raise ValueError("version VP8L no soportada")
    w2, h2, px = _vp8l_flujo(br, w, h, True, gasto)
    salida = bytearray(4 * w2 * h2)
    for i, p in enumerate(px):
        salida[4 * i] = (p >> 16) & 0xFF
        salida[4 * i + 1] = (p >> 8) & 0xFF
        salida[4 * i + 2] = p & 0xFF
        salida[4 * i + 3] = (p >> 24) & 0xFF
    return w2, h2, salida


def _alph_desfiltrar(plano, an, al, filtro):
    """Deshace el filtro espacial del trozo ALPH (0 ninguno, 1 horizontal,
    2 vertical, 3 gradiente). Igual que en PNG, es un predictor por byte."""
    if filtro == 0:
        return plano
    out = bytearray(plano)
    for y in range(al):
        base = y * an
        for x in range(an):
            i = base + x
            if i >= len(out):
                return out
            if x == 0 and y == 0:
                continue
            izq = out[i - 1] if x else None
            arr = out[i - an] if y else None
            if filtro == 1:
                pred = izq if izq is not None else arr
            elif filtro == 2:
                pred = arr if arr is not None else izq
            else:
                if izq is None:
                    pred = arr
                elif arr is None:
                    pred = izq
                else:
                    d = izq + arr - out[i - an - 1]
                    pred = 0 if d < 0 else (255 if d > 255 else d)
            out[i] = (out[i] + pred) & 255
    return out


# ---- despachador de min(alfa) --------------------------------------------

def alfa_minimo(ruta: str, firma: str | None = None, exacto: bool = False) -> dict:
    """min(alfa) del fichero, EN PROCESO. Devuelve siempre 'evaluable'.

    Un verificador que no distingue "comprobado" de "no he podido comprobarlo"
    repite el fallo de markitdown-mcp: aqui, cuando el formato no se puede
    decodificar sin un decodificador de video completo, se dice.
    """
    firma = firma or firma_real(ruta)
    t0 = time.perf_counter()
    try:
        if firma == "png":
            r = _alfa_min_png(ruta, exacto)
        elif firma == "webp":
            r = _alfa_min_webp(ruta, exacto)
        elif firma in ("jpeg", "bmp"):
            # JPEG/BMP-24 no tienen canal alfa: opaco por definicion del formato.
            r = {"formato": firma, "evaluable": True, "exacto": True,
                 "tiene_alfa": False, "alfa_min": 1.0, "via": "el formato no "
                 "admite alfa", "primer_transparente": None}
        elif firma == "gif":
            r = _alfa_min_gif(ruta)
        elif firma in ("avif", "heif"):
            r = {"formato": firma, "evaluable": False, "alfa_min": None,
                 "exacto": False, "tiene_alfa": None, "primer_transparente": None,
                 "motivo": "AVIF/HEIF: el plano alfa es un flujo AV1/HEVC; "
                           "exige un decodificador de video completo"}
        elif firma == "tiff":
            r = _alfa_min_tiff(ruta)
        else:
            r = {"formato": firma, "evaluable": False, "alfa_min": None,
                 "exacto": False, "tiene_alfa": None, "primer_transparente": None,
                 "motivo": "formato sin lector de alfa en proceso"}
    except (OSError, struct.error, IndexError, ValueError, zlib.error) as e:
        r = {"formato": firma, "evaluable": False, "alfa_min": None,
             "exacto": False, "tiene_alfa": None, "primer_transparente": None,
             "motivo": "%s: %s" % (type(e).__name__, e)}
    r["ms"] = (time.perf_counter() - t0) * 1000
    if r.get("evaluable") and r.get("alfa_min") is not None:
        r["alfa_no_trivial"] = r["alfa_min"] < 0.999
    else:
        r["alfa_no_trivial"] = None
    return r


def _alfa_min_gif(ruta: str) -> dict:
    """GIF: la transparencia es un INDICE de la paleta marcado en el bloque de
    control grafico. Saber si ese indice se USA exigiria descomprimir el LZW;
    aqui se devuelve la cota (hay transparencia declarada) y se marca inexacto.
    """
    with open(ruta, "rb") as fh:
        datos = fh.read(65536)
    r = {"formato": "gif", "evaluable": True, "exacto": False,
         "tiene_alfa": False, "alfa_min": 1.0, "primer_transparente": None,
         "via": "bloque de control grafico"}
    i = datos.find(b"\x21\xf9\x04")
    while i >= 0 and i + 4 < len(datos):
        if datos[i + 3] & 0x01:
            # COTA, no medida: el GIF declara un indice transparente, pero
            # saber si alguna celda lo usa exige descomprimir el LZW. Se
            # devuelve NO EVALUABLE, no 0.0: "declara" no es "tiene".
            r.update({"tiene_alfa": True, "evaluable": False, "exacto": False,
                      "alfa_min": None, "cota_alfa_min": 0.0,
                      "motivo": "transparencia DECLARADA en el bloque de control "
                                "grafico; confirmar que el indice se usa exigiria "
                                "descomprimir el LZW"})
            return r
        i = datos.find(b"\x21\xf9\x04", i + 1)
    r["exacto"] = True
    return r


def _alfa_min_tiff(ruta: str) -> dict:
    """TIFF: ExtraSamples dice si hay alfa; el valor minimo exigiria
    descomprimir las bandas (LZW/Deflate/JPEG) y deshacer el predictor."""
    with open(ruta, "rb") as fh:
        d = _tiff(fh)
    if not d.get("tiene_alfa"):
        return {"formato": "tiff", "evaluable": True, "exacto": True,
                "tiene_alfa": False, "alfa_min": 1.0, "primer_transparente": None,
                "via": "ExtraSamples/SamplesPerPixel"}
    return {"formato": "tiff", "evaluable": False, "alfa_min": None,
            "exacto": False, "tiene_alfa": True, "primer_transparente": None,
            "motivo": "TIFF con ExtraSamples: exige descomprimir las bandas"}


# ---- despachador en proceso ----------------------------------------------

def sondear_en_proceso(ruta: str) -> dict:
    """Sondeo completo SIN lanzar ni un solo subproceso."""
    firma = firma_real(ruta)
    tam = os.path.getsize(ruta) if os.path.exists(ruta) else 0
    base = {"ruta": ruta, "bytes": tam, "firma": firma, "motor": "proceso"}
    if tam == 0:
        base.update({"categoria": "vacio", "error": "fichero de 0 bytes"})
        return base
    try:
        if firma in ("texto",):
            base.update(_datos(ruta))
            return base
        with open(ruta, "rb") as fh:
            if firma == "png":
                base.update(_png(fh))
            elif firma == "jpeg":
                base.update(_jpeg(fh))
            elif firma == "webp":
                base.update(_webp(fh))
            elif firma == "gif":
                base.update(_gif(fh))
            elif firma == "tiff":
                base.update(_tiff(fh))
            elif firma in ("avif", "heif", "mp4", "m4a", "mov", "isobmff", "3gp"):
                base.update(_isobmff(fh, ruta))
            elif firma == "matroska":
                base.update(_matroska(fh, ruta))
            elif firma == "ogg":
                base.update(_ogg(fh, ruta))
            elif firma == "wav":
                base.update(_wav(fh, ruta))
            elif firma == "flac":
                base.update(_flac(fh, ruta))
            elif firma == "mp3":
                base.update(_mp3(fh, ruta))
            elif firma == "pdf":
                base.update(_pdf(fh, ruta))
            else:
                base["categoria"] = "desconocida"
    except (OSError, struct.error, IndexError, ValueError) as e:
        base["error"] = "%s: %s" % (type(e).__name__, e)
        base.setdefault("categoria", "ilegible")
    return base


# ===========================================================================
# SONDEO POR SUBPROCESO — ffprobe / magick identify / gswin64c
# ===========================================================================

CAT_POR_FIRMA = {
    "png": "imagen", "jpeg": "imagen", "webp": "imagen", "gif": "imagen",
    "tiff": "imagen", "avif": "imagen", "heif": "imagen", "bmp": "imagen",
    "mp4": "av", "m4a": "av", "mov": "av", "matroska": "av", "ogg": "av",
    "wav": "av", "flac": "av", "mp3": "av", "pdf": "pdf", "texto": "datos",
}


def _correr(orden, timeout=TIMEOUT):
    try:
        p = subprocess.run(orden, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return -9, "", "timeout tras %ss" % timeout
    except OSError as e:
        return -1, "", str(e)


def sondear_subproceso(ruta: str) -> dict:
    """Mismo sondeo, delegado a los binarios externos. 1-2 procesos por fichero."""
    firma = firma_real(ruta)  # los bytes magicos nunca necesitan un proceso
    tam = os.path.getsize(ruta) if os.path.exists(ruta) else 0
    d = {"ruta": ruta, "bytes": tam, "firma": firma, "motor": "subproceso",
         "n_procesos": 0}
    if tam == 0:
        d.update({"categoria": "vacio", "error": "fichero de 0 bytes"})
        return d
    cat = CAT_POR_FIRMA.get(firma, "desconocida")
    d["categoria"] = cat
    if cat == "av":
        rc, out, err = _correr(["ffprobe", "-v", "error", "-print_format", "json",
                                "-show_format", "-show_streams", ruta])
        d["n_procesos"] = 1
        if rc != 0:
            d["error"] = err.strip()[:300]
            return d
        j = json.loads(out) if out.strip() else {}
        fm = j.get("format", {})
        d["formato"] = fm.get("format_name")
        d["duracion_s"] = round(float(fm["duration"]), 4) if fm.get("duration") else None
        d["bitrate_bps"] = int(fm["bit_rate"]) if fm.get("bit_rate") else None
        pistas = []
        d["n_video"] = d["n_audio"] = d["n_subtitulo"] = 0
        for s in j.get("streams", []):
            t = s.get("codec_type")
            p = {"tipo": t, "codec": s.get("codec_name")}
            if t == "video":
                d["n_video"] += 1
                p["ancho"], p["alto"] = s.get("width"), s.get("height")
                p["fps"] = s.get("r_frame_rate")
                p["profundidad_bits"] = s.get("bits_per_raw_sample")
            elif t == "audio":
                d["n_audio"] += 1
                p["canales"] = s.get("channels")
                p["sample_rate"] = int(s["sample_rate"]) if s.get("sample_rate") else None
                p["profundidad_bits"] = s.get("bits_per_raw_sample")
                p["bitrate_bps"] = int(s["bit_rate"]) if s.get("bit_rate") else None
            elif t == "subtitle":
                d["n_subtitulo"] += 1
            if s.get("duration"):
                p["duracion_s"] = round(float(s["duration"]), 4)
            pistas.append(p)
        d["pistas"] = pistas
        d["n_pistas"] = len(pistas)
    elif cat == "imagen":
        # OJO: %x sin %U enganna. ImageMagick devuelve la resolucion en la
        # unidad del fichero, y para un PNG es PIXELES POR CENTIMETRO: un PNG
        # de 150 ppp sale como '59'. Sin convertir, la regla P4 da falso fallo.
        fmt = "%m|%w|%h|%z|%[channels]|%x|%A|%[colorspace]|%U\n"
        rc, out, err = _correr(["magick", "identify", "-limit", "thread", "4",
                                "-format", fmt, ruta])
        d["n_procesos"] = 1
        if rc != 0 or not out.strip():
            d["error"] = (err or "identify vacio").strip()[:300]
            return d
        lineas = [l for l in out.strip().splitlines() if l.strip()]
        c = lineas[0].split("|")
        d["formato"] = c[0].lower()
        d["ancho"], d["alto"] = int(c[1]), int(c[2])
        d["profundidad_bits"] = int(c[3])
        d["canales_txt"] = c[4]
        d["tiene_alfa"] = c[6].strip().lower() in ("true", "blend", "on", "associated")
        unidad = c[8].strip() if len(c) > 8 else ""
        try:
            res = float(c[5].split()[0])
            d["ppp"] = round(res * 2.54) if unidad.startswith("PixelsPerCentimeter") \
                else (round(res) if unidad.startswith("PixelsPerInch") else None)
        except (ValueError, IndexError):
            d["ppp"] = None
        d["espacio_color"] = c[7] if len(c) > 7 else None
        d["n_imagenes"] = len(lineas)
    elif cat == "pdf":
        rc, out, err = _correr(["gswin64c", "-q", "-dNODISPLAY", "-dNOSAFER", "-dBATCH",
                                "-c", "(%s) (r) file runpdfbegin pdfpagecount = "
                                      "1 pdfgetpage /MediaBox get {=} forall quit"
                                % ruta.replace("\\", "/")])
        d["n_procesos"] = 1
        lin = [x for x in out.strip().splitlines() if x.strip()]
        try:
            d["n_paginas"] = int(lin[0])
            if len(lin) >= 5:
                caja = [float(x) for x in lin[1:5]]
                d["ancho_pt"] = round(caja[2] - caja[0], 2)
                d["alto_pt"] = round(caja[3] - caja[1], 2)
        except (ValueError, IndexError):
            d["n_paginas"] = None
            d["error"] = (err or out).strip()[:300]
    else:  # datos: no hay binario externo que aporte nada
        d.update(_datos(ruta))
        d["n_procesos"] = 0
    return d


def sondear(ruta: str, motor: str = "proceso", alfa: bool = False) -> dict:
    """El sondeo NUNCA calcula min(alfa) por defecto: es el unico dato del
    contrato que exige decodificar pixeles y no pertenece al camino caliente.
    Con alfa=True se calcula EN PROCESO (nunca con `magick`)."""
    d = sondear_en_proceso(ruta) if motor == "proceso" else sondear_subproceso(ruta)
    if alfa and d.get("categoria") == "imagen":
        a = alfa_minimo(ruta, d.get("firma"))
        d["alfa"] = a
        d["alfa_ms"] = a["ms"]
        if a.get("evaluable"):
            d["alfa_min"] = a["alfa_min"]
            d["alfa_no_trivial"] = a["alfa_no_trivial"]
            if a.get("tiene_alfa") is not None and d.get("tiene_alfa") is None:
                d["tiene_alfa"] = a["tiene_alfa"]
        else:
            d["alfa_no_evaluable"] = a.get("motivo")
    return d


# ===========================================================================
# EL CONTRATO — cuatro puntos
# ===========================================================================

# Profundidad maxima que admite cada formato de destino. Bajar hasta este
# techo es PERDIDA INEVITABLE (regla I5), no un fallo del motor.
PROF_MAX = {"jpeg": 8, "jpg": 8, "webp": 8, "gif": 8, "bmp": 8,
            "avif": 12, "heif": 12, "heic": 12, "pdf": 8}
SIN_ALFA = {"jpeg", "jpg", "pdf"}
# Opus solo opera a 48 kHz (regla A3). Tolerancia de duracion: 10 ms (A1).
TOL_DURACION_AUDIO = 0.010
TOL_DURACION_VIDEO = 0.050

def _codec_norm(c: str) -> str:
    """Normaliza el nombre del codec entre sondas: 'A_AAC', 'libopus', 'mp4a'.

    OJO: str.lstrip('a_') borra TODA a inicial ('aac' -> 'c'). Fue un falso
    positivo real de este verificador.
    """
    c = (c or "").lower()
    for pre in ("a_", "v_", "lib"):
        if c.startswith(pre):
            c = c[len(pre):]
    return {"mp4a": "aac", "avc1": "h264", "mpeg4/iso/avc": "h264"}.get(c, c)


# Muestras por trama de cada codec con perdida. La duracion de un fichero
# basado en tramas SOLO puede ser multiplo de la trama: exigir +-10 ms a un
# MP3, cuya trama dura 26,1 ms, es exigir lo imposible.
MUESTRAS_TRAMA = {"mp3": 1152, "aac": 1024, "mp4a": 1024, "alac": 4096,
                  "opus": 960, "vorbis": 1024, "ac3": 1536}


def _tolerancia_audio(*listas_pistas) -> float:
    """Tolerancia de duracion: la trama mas larga de ORIGEN o DESTINO.

    Hay que mirar tambien el origen: decodificar un AAC (trama de 23,2 ms)
    para reescribirlo en FLAC deja una incertidumbre de una trama de AAC,
    aunque el FLAC de destino no tenga tramas.
    """
    tol = TOL_DURACION_AUDIO
    for pistas in listas_pistas:
        for x in pistas or []:
            if x.get("tipo") != "audio":
                continue
            cod = _codec_norm(x.get("codec"))
            n = MUESTRAS_TRAMA.get(cod)
            sr = x.get("sample_rate") or 48000
            if n:
                tol = max(tol, n / float(sr))
    return tol


# Solo tiene sentido hablar de profundidad de bits INFLADA cuando el destino
# es sin perdida: la 'BitDepth' que Matroska escribe para un AAC es 32 y no
# significa nada.
CODEC_SIN_PERDIDA = {"flac", "alac", "pcm_s16le", "pcm_s24le", "pcm_s32le",
                     "pcm", "wavpack", "tta", "truehd"}


def _hallazgo(punto, regla, severidad, mensaje, esperado=None, obtenido=None):
    return {"punto": punto, "regla": regla, "severidad": severidad,
            "mensaje": mensaje, "esperado": esperado, "obtenido": obtenido}


def punto1_firma(salida: str, sonda: dict, pedido: dict) -> list:
    """1. Firma real del fichero (bytes magicos), no la extension."""
    h = []
    ext = os.path.splitext(salida)[1].lower()
    firma = sonda.get("firma")
    if not os.path.exists(salida):
        return [_hallazgo(1, "G1", "fallo", "el fichero de salida no existe")]
    if sonda.get("bytes", 0) == 0:
        return [_hallazgo(1, "G1", "fallo", "fichero de 0 bytes presentado como exito",
                          "> 0 bytes", "0 bytes")]
    if pedido.get("rc", 0) != 0:
        h.append(_hallazgo(1, "G1", "fallo", "el motor devolvio codigo distinto de 0",
                           0, pedido.get("rc")))
    aceptables = EXT_A_FIRMAS.get(ext)
    if aceptables is None:
        h.append(_hallazgo(1, "G3", "informativo",
                           "extension sin firma conocida: %s" % ext, None, firma))
    elif firma not in aceptables:
        h.append(_hallazgo(1, "G3", "fallo",
                           "la firma real no corresponde a la extension pedida",
                           "|".join(sorted(aceptables)), firma))
    return h


def punto2_flujos(sonda: dict, sonda_ent: dict | None, pedido: dict) -> list:
    """2. Flujos esperados frente a obtenidos: video / audio / subtitulo."""
    h = []
    if sonda.get("categoria") != "av":
        return h
    if sonda.get("error"):
        return [_hallazgo(2, "G2", "fallo", "la sonda no abre el fichero",
                          None, sonda["error"])]
    esperado = pedido.get("flujos")  # {"video":n,"audio":n,"subtitulo":n}
    if esperado is None and sonda_ent and sonda_ent.get("categoria") == "av":
        esperado = {"video": sonda_ent.get("n_video", 0),
                    "audio": sonda_ent.get("n_audio", 0),
                    "subtitulo": sonda_ent.get("n_subtitulo", 0)}
        # destinos que no admiten ciertos flujos: perdida inevitable
        dest = pedido.get("destino", "")
        par = pedido.get("params", {})
        if dest in ("gif",):
            esperado = {"video": 1, "audio": 0, "subtitulo": 0}
        if par.get("solo_audio") or pedido.get("solo_audio"):
            esperado = {"video": 0, "audio": 1, "subtitulo": 0}
        if par.get("solo_video") or pedido.get("solo_video"):
            esperado = {"video": esperado["video"], "audio": 0, "subtitulo": 0}
    if esperado is None:
        return [_hallazgo(2, "V3", "informativo", "sin referencia de entrada: "
                                                  "no se puede comparar el numero de pistas")]
    for clave, regla in (("video", "V7"), ("audio", "V3"), ("subtitulo", "V4")):
        obt = sonda.get("n_" + clave, 0)
        esp = esperado.get(clave, 0)
        if obt != esp:
            sev = "fallo" if obt < esp else "aviso"
            h.append(_hallazgo(2, regla, sev,
                               "numero de pistas de %s distinto del esperado" % clave,
                               esp, obt))
    return h


def _prof(sonda: dict):
    """Profundidad de bits, normalizada a entero (ffprobe la da como cadena)."""
    v = sonda.get("profundidad_bits")
    if not v:
        for p in sonda.get("pistas", []):
            if p.get("profundidad_bits"):
                v = p["profundidad_bits"]
                break
    try:
        return int(v) if v else None
    except (TypeError, ValueError):
        return None


def punto3_propiedades(sonda: dict, sonda_ent: dict | None, pedido: dict) -> list:
    """3. Propiedades DECLARADAS frente a MEDIDAS.

    'Declaradas' = lo que el motor / el contenedor afirma sobre si mismo.
    Comprueba la coherencia interna del fichero de salida.
    """
    h = []
    cat = sonda.get("categoria")
    if sonda.get("error"):
        return [_hallazgo(3, "G2", "fallo", "el fichero no se abre sin errores",
                          None, sonda["error"])]
    if cat == "imagen":
        an, al = sonda.get("ancho"), sonda.get("alto")
        if not an or not al:
            h.append(_hallazgo(3, "G4", "fallo", "sin dimensiones legibles", ">0", (an, al)))
        elif an < 2 or al < 2:
            h.append(_hallazgo(3, "G4", "aviso", "dimensiones implausibles", ">=2", (an, al)))
        pr = sonda.get("profundidad_bits")
        if pr is not None and pr not in (1, 2, 4, 8, 10, 12, 16, 32):
            h.append(_hallazgo(3, "G4", "aviso", "profundidad de bits atipica", None, pr))
    elif cat == "av":
        dur = sonda.get("duracion_s")
        if not dur or dur <= 0:
            h.append(_hallazgo(3, "G4", "fallo", "duracion nula o ilegible", ">0", dur))
        if sonda.get("n_pistas", 0) == 0:
            h.append(_hallazgo(3, "G4", "fallo", "el contenedor no declara ninguna pista"))
        for p in sonda.get("pistas", []):
            if p["tipo"] == "audio":
                if not p.get("canales"):
                    h.append(_hallazgo(3, "A2", "aviso", "pista de audio sin canales"))
                sr = p.get("sample_rate")
                if sr and not (8000 <= sr <= 192000):
                    h.append(_hallazgo(3, "A3", "aviso", "frecuencia atipica", None, sr))
            if p["tipo"] == "video" and (not p.get("ancho") or not p.get("alto")):
                h.append(_hallazgo(3, "V7", "fallo", "pista de video sin dimensiones"))
        br = sonda.get("bitrate_bps")
        if br is not None and br <= 0:
            h.append(_hallazgo(3, "G4", "aviso", "bitrate no positivo", ">0", br))
    elif cat == "pdf":
        n = sonda.get("n_paginas")
        if not n:
            h.append(_hallazgo(3, "P1", "fallo", "el PDF no declara ninguna pagina", ">=1", n))
    elif cat == "datos":
        if not sonda.get("utf8_valido"):
            h.append(_hallazgo(3, "D5", "fallo", "la salida no es UTF-8 valido"))
        if sonda.get("reemplazo_ufffd"):
            h.append(_hallazgo(3, "D5", "fallo", "hay caracteres U+FFFD de reemplazo"))
        if sonda.get("formato") == "json" and not sonda.get("json_valido"):
            h.append(_hallazgo(3, "D8", "fallo", "JSON sintacticamente invalido",
                               None, sonda.get("error")))
        if sonda.get("formato") == "csv":
            anchos = set(sonda.get("csv_n_campos_por_fila", []))
            if len(anchos) > 1:
                h.append(_hallazgo(3, "D2", "fallo",
                                   "numero de campos no constante", None, sorted(anchos)))
    elif cat == "vacio":
        h.append(_hallazgo(3, "G1", "fallo", "fichero de 0 bytes"))
    return h


def punto4_pedido(sonda: dict, sonda_ent: dict | None, pedido: dict) -> list:
    """4. Propiedades PEDIDAS frente a OBTENIDAS.

    Regla nuclear: lo que NO se pidio transformar debe conservarse. Este es
    el punto que atrapa el redimensionado silencioso de image-worker-mcp
    (1920x1080 -> 800x450 con barras negras) y las degradaciones calladas.
    """
    h = []
    if sonda_ent is None:
        return [_hallazgo(4, "-", "informativo", "sin entrada de referencia: "
                                                 "el punto 4 no es evaluable")]
    if sonda.get("error") or sonda_ent.get("error"):
        return h
    p = pedido.get("params", {})
    dest = pedido.get("destino", "").lower().lstrip(".")
    cat, cat_e = sonda.get("categoria"), sonda_ent.get("categoria")

    # ---------- geometria ----------
    def dims(s):
        if s.get("ancho"):
            return s.get("ancho"), s.get("alto")
        for x in s.get("pistas", []):
            if x["tipo"] == "video" and x.get("ancho"):
                return x["ancho"], x["alto"]
        return None, None

    an, al = dims(sonda)
    ane, ale = dims(sonda_ent)
    pedido_geom = any(k in p for k in ("ancho", "alto", "escala", "dpi", "densidad"))
    if an and ane and not pedido_geom and cat_e != "pdf":
        if (an, al) != (ane, ale):
            h.append(_hallazgo(4, "I1/V7", "fallo",
                               "REDIMENSIONADO NO SOLICITADO: no se pidio cambiar el tamano",
                               "%dx%d" % (ane, ale), "%dx%d" % (an, al)))
    elif an and pedido_geom and p.get("ancho"):
        if an != p["ancho"] or (p.get("alto") and al != p["alto"]):
            h.append(_hallazgo(4, "I1", "fallo", "dimensiones distintas de las pedidas",
                               "%sx%s" % (p.get("ancho"), p.get("alto")), "%dx%d" % (an, al)))
    # relacion de aspecto: detecta las barras negras aunque el lienzo cuadre
    if an and ane and al and ale:
        ra, rae = an / al, ane / ale
        if abs(ra - rae) > 0.02 and not p.get("recortar") and not pedido_geom:
            h.append(_hallazgo(4, "I1", "aviso",
                               "la relacion de aspecto cambia (indicio de barras anadidas)",
                               round(rae, 3), round(ra, 3)))

    # ---------- ppp / densidad ----------
    if p.get("dpi") and cat == "imagen":
        if sonda.get("ppp") and abs(sonda["ppp"] - p["dpi"]) > 1:
            h.append(_hallazgo(4, "P4", "fallo", "ppp distinto del pedido",
                               p["dpi"], sonda["ppp"]))
    if p.get("dpi") and cat_e == "pdf" and cat == "imagen" and sonda_ent.get("ancho_pt"):
        esperado = round(sonda_ent["ancho_pt"] * p["dpi"] / 72.0)
        if an and abs(an - esperado) > 1:
            h.append(_hallazgo(4, "P4", "fallo",
                               "la resolucion no corresponde al ppp pedido",
                               esperado, an))

    # ---------- profundidad de bits ----------
    # Solo tiene sentido en IMAGEN. En audio/video la profundidad que declara
    # el contenedor es ruido: Matroska anuncia 32 bits para un AAC que MP4
    # declara como 16 sin que se haya tocado un solo byte (remux -c copy).
    pr, pre = _prof(sonda), _prof(sonda_ent)
    if cat == "imagen" and cat_e == "imagen" and pr and pre and pr < pre:
        techo = PROF_MAX.get(dest)
        if p.get("profundidad_bits") == pr:
            pass  # se pidio explicitamente
        elif techo is not None and pr <= techo:
            h.append(_hallazgo(4, "I5", "informativo",
                               "reduccion de profundidad inevitable en %s (techo %d bits)"
                               % (dest, techo), pre, pr))
        else:
            h.append(_hallazgo(4, "I4", "fallo",
                               "DEGRADACION DE PROFUNDIDAD no pedida ni inevitable", pre, pr))
    elif cat == "av" and pr and pre and pr > pre:
        cods = {_codec_norm(x.get("codec"))
                for x in sonda.get("pistas", []) if x.get("tipo") == "audio"}
        if cods & CODEC_SIN_PERDIDA:
            h.append(_hallazgo(4, "A6", "aviso",
                               "profundidad de bits INFLADA sin informacion nueva", pre, pr))

    # ---------- canal alfa (trampa del 'alfa trivial') ----------
    if cat == "imagen" and cat_e == "imagen":
        alfa_e = sonda_ent.get("tiene_alfa")
        alfa_no_trivial = sonda_ent.get("alfa_no_trivial")
        if alfa_e and alfa_no_trivial and not sonda.get("tiene_alfa"):
            if dest in SIN_ALFA:
                h.append(_hallazgo(4, "I2", "informativo",
                                   "%s no admite alfa: perdida inevitable" % dest))
            else:
                h.append(_hallazgo(4, "I2", "fallo",
                                   "se pierde un canal alfa NO TRIVIAL en un destino que lo admite"))
        elif alfa_e and alfa_no_trivial is None and not sonda.get("tiene_alfa"):
            # NO se da por buena: se dice que no se pudo comprobar. Es la
            # diferencia entre "comprobado y correcto" y "no lo se".
            h.append(_hallazgo(4, "I2", "informativo",
                               "se descarta el canal alfa y min(alfa) de la entrada "
                               "no esta calculado: la regla I2 no es evaluable",
                               "min(alfa) conocido",
                               sonda_ent.get("alfa_no_evaluable") or "sin calcular"))

    # ---------- duracion ----------
    du, due = sonda.get("duracion_s"), sonda_ent.get("duracion_s")
    if p.get("solo_audio"):
        # Al extraer audio de un video hay que comparar PISTA contra PISTA, no
        # contra el contenedor: en tipico.mp4 el contenedor dura 20,0000 s y su
        # pista de audio 20,0232 s. Comparar con el contenedor daba un falso
        # fallo de 15,6 ms; comparar contenedor de salida contra pista de
        # entrada daba otro de 23 ms en sentido contrario.
        for s_, clave in ((sonda_ent, "e"), (sonda, "s")):
            for x in s_.get("pistas", []):
                if x.get("tipo") == "audio" and x.get("duracion_s"):
                    if clave == "e":
                        due = x["duracion_s"]
                    else:
                        du = x["duracion_s"]
                    break
    if du and due and not p.get("recortar") and not p.get("fps"):
        solo_v = sonda.get("n_video", 0) > 0
        tol = TOL_DURACION_VIDEO if solo_v else _tolerancia_audio(
            sonda.get("pistas"), sonda_ent.get("pistas"))
        if abs(du - due) > tol:
            h.append(_hallazgo(4, "A1/V1", "fallo", "la duracion cambia mas de la tolerancia",
                               "%.4f +-%.3f" % (due, tol), du))

    # ---------- frecuencia de muestreo (excepcion Opus) ----------
    def sr(s):
        for x in s.get("pistas", []):
            if x["tipo"] == "audio" and x.get("sample_rate"):
                return x["sample_rate"], x.get("codec")
        return None, None

    s_o, cod_o = sr(sonda)
    s_e, _ = sr(sonda_ent)
    if s_o and s_e and s_o != s_e and not p.get("sample_rate"):
        # el nombre del codec cambia segun la sonda: 'opus', 'A_OPUS', 'libopus'
        if "opus" in (cod_o or "").lower() and s_o == 48000:
            h.append(_hallazgo(4, "A3", "informativo", "Opus fuerza 48 kHz", s_e, s_o))
        else:
            h.append(_hallazgo(4, "A3", "fallo", "frecuencia de muestreo alterada sin pedirlo",
                               s_e, s_o))

    # ---------- canales de audio ----------
    def canales(s):
        for x in s.get("pistas", []):
            if x["tipo"] == "audio" and x.get("canales"):
                return x["canales"]
        return None

    c_o, c_e = canales(sonda), canales(sonda_ent)
    if c_o and c_e and c_o != c_e and not p.get("canales"):
        h.append(_hallazgo(4, "A2", "fallo", "numero de canales alterado sin pedirlo",
                           c_e, c_o))

    # ---------- bitrate pedido ----------
    # El bitrate es una PETICION, no un contrato: el codificador AAC nativo de
    # ffmpeg entrega 129 kbps cuando se le piden 192 sobre material mono.
    # Calibrado con datos reales: <15 % se acepta, 15-50 % es aviso, y >50 %
    # es fallo (ConvertX entregaba 64 kbps pidiendole 192: 67 % de desvio).
    if p.get("bitrate_bps"):
        for x in sonda.get("pistas", []):
            if x["tipo"] == "audio" and x.get("bitrate_bps"):
                desv = abs(x["bitrate_bps"] - p["bitrate_bps"]) / p["bitrate_bps"]
                if desv > 0.50:
                    h.append(_hallazgo(4, "-", "fallo", "bitrate muy lejos del pedido",
                                       p["bitrate_bps"], x["bitrate_bps"]))
                elif desv > 0.15:
                    h.append(_hallazgo(4, "-", "aviso", "bitrate lejos del pedido",
                                       p["bitrate_bps"], x["bitrate_bps"]))
                break

    # ---------- imagen -> PDF: la caja de pagina (regla P7) ----------
    if cat == "pdf" and cat_e == "imagen" and sonda.get("ancho_pt") and ane:
        pt = sonda["ancho_pt"]
        dens = p.get("dpi") or p.get("densidad")
        if dens:
            esp = ane * 72.0 / dens
            if abs(pt - esp) > 1.5:
                h.append(_hallazgo(4, "P7", "fallo",
                                   "la caja de pagina no corresponde a la densidad pedida",
                                   round(esp, 1), pt))
        elif abs(pt - ane) < 1.0 and ane > 1000:
            h.append(_hallazgo(4, "P7", "aviso",
                               "1 px -> 1 pt: pagina absurda (%d x %d pt = %d x %d mm)"
                               % (pt, sonda.get("alto_pt", 0), pt * 25.4 / 72,
                                  sonda.get("alto_pt", 0) * 25.4 / 72),
                               "densidad declarada", "1:1"))

    # ---------- paginas de PDF ----------
    if cat == "pdf" and cat_e == "pdf":
        if sonda.get("n_paginas") and sonda_ent.get("n_paginas"):
            if sonda["n_paginas"] != sonda_ent["n_paginas"]:
                h.append(_hallazgo(4, "P1", "fallo", "cambia el numero de paginas",
                                   sonda_ent["n_paginas"], sonda["n_paginas"]))

    # ---------- datos tabulares ----------
    if cat == "datos" and cat_e == "datos":
        fo, fe = sonda.get("filas_datos"), sonda_ent.get("filas_datos")
        if fo is not None and fe is not None and fo != fe:
            h.append(_hallazgo(4, "D1", "fallo", "cambia el numero de filas logicas", fe, fo))
        co = sonda.get("csv_cabecera")
        ce = sonda_ent.get("csv_cabecera")
        if co and ce and sorted(co) != sorted(ce):
            h.append(_hallazgo(4, "D4", "fallo", "cambia la cabecera (BOM o clave perdida)",
                               ce, co))
        if sonda.get("bom_utf8") and not pedido.get("params", {}).get("bom"):
            h.append(_hallazgo(4, "D4", "aviso", "la salida lleva BOM UTF-8 sin pedirlo"))
    return h


PUNTOS = ("1_firma", "2_flujos", "3_propiedades", "4_pedido")


def verificar(salida: str, pedido: dict | None = None, entrada: str | None = None,
              motor: str = "proceso", sonda_ent: dict | None = None,
              sonda_sal: dict | None = None, alfa: bool = False) -> dict:
    """Ejecuta los cuatro puntos del contrato y cronometra cada uno.

    alfa=True calcula min(alfa) de la ENTRADA en proceso cuando hace falta para
    la regla I2 y no viene inyectado. Es el unico dato del contrato que exige
    decodificar pixeles; por eso es opcional y se cronometra aparte.
    """
    pedido = dict(pedido or {})
    pedido.setdefault("destino", os.path.splitext(salida)[1].lstrip(".").lower())
    ms = {}
    t0 = time.perf_counter()
    if sonda_sal is None:
        sonda_sal = sondear(salida, motor)
    ms["sonda_salida"] = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    if sonda_ent is None and entrada:
        sonda_ent = sondear(entrada, motor)
    ms["sonda_entrada"] = (time.perf_counter() - t0) * 1000

    ms["alfa"] = 0.0
    if (alfa and sonda_ent is not None and entrada
            and sonda_ent.get("categoria") == "imagen"
            and sonda_ent.get("tiene_alfa")
            and sonda_ent.get("alfa_no_trivial") is None):
        t0 = time.perf_counter()
        a = alfa_minimo(entrada, sonda_ent.get("firma"))
        ms["alfa"] = (time.perf_counter() - t0) * 1000
        if a.get("evaluable"):
            sonda_ent["alfa_min"] = a["alfa_min"]
            sonda_ent["alfa_no_trivial"] = a["alfa_no_trivial"]
        else:
            sonda_ent["alfa_no_evaluable"] = a.get("motivo")

    hallazgos = []
    for nombre, fn in (("1_firma", lambda: punto1_firma(salida, sonda_sal, pedido)),
                       ("2_flujos", lambda: punto2_flujos(sonda_sal, sonda_ent, pedido)),
                       ("3_propiedades", lambda: punto3_propiedades(sonda_sal, sonda_ent, pedido)),
                       ("4_pedido", lambda: punto4_pedido(sonda_sal, sonda_ent, pedido))):
        t0 = time.perf_counter()
        r = fn()
        ms[nombre] = (time.perf_counter() - t0) * 1000
        hallazgos.extend(r)

    sev = {h["severidad"] for h in hallazgos}
    veredicto = "fallo" if "fallo" in sev else ("aviso" if "aviso" in sev else "ok")
    # Cobertura: que puntos se pudieron evaluar de verdad. Un verificador que
    # no distingue "comprobado y correcto" de "no he podido comprobarlo" repite
    # el fallo de markitdown-mcp (cadena vacia con isError: false).
    # Un punto cuenta como cubierto si se evaluo O si no aplica a la categoria
    # (el numero de pistas no aplica a una imagen).
    cobertura = {"1_firma": True,
                 "2_flujos": sonda_sal.get("categoria") != "av" or sonda_ent is not None,
                 "3_propiedades": not sonda_sal.get("error"),
                 "4_pedido": sonda_ent is not None and not sonda_sal.get("error"),
                 # min(alfa) es el unico dato del contrato que exige pixeles:
                 # se cubre si la entrada no tiene alfa (nada que comprobar) o
                 # si min(alfa) se conoce (calculado o inyectado).
                 "4_alfa": (sonda_ent is None
                            or not sonda_ent.get("tiene_alfa")
                            or sonda_ent.get("alfa_no_trivial") is not None)}
    if veredicto == "ok" and not all(cobertura.values()):
        veredicto = "ok_parcial"
    ms["total"] = sum(ms.values())
    ms["logica"] = sum(ms[k] for k in PUNTOS)
    return {"salida": salida, "entrada": entrada, "motor": motor,
            "categoria": sonda_sal.get("categoria"), "veredicto": veredicto,
            "cobertura": cobertura,
            "hallazgos": hallazgos, "ms": ms,
            "n_procesos": sonda_sal.get("n_procesos", 0) + (
                sonda_ent.get("n_procesos", 0) if sonda_ent else 0)}


# ===========================================================================
# FIDELIDAD — las reglas que exigen comparar PIXELES o MUESTRAS
#
# NO son el contrato de PLAN-ORQUESTADOR.md §4.2. El contrato responde a
# "¿entregaste lo que pedi?" en microsegundos; la fidelidad responde a
# "¿cuanto se parece a lo que habia?" y cuesta lo que cuesta convertir.
# Por eso viven en funciones separadas, con su propio veredicto y su propia
# cobertura, y NUNCA se ejecutan desde verificar().
#
# Cubiertas: I3 (color del aplanado), I6 (RMSE=0), I7 (PSNR de imagen),
#            V6 (framemd5 por pixel), V8 (PSNR de video), V9 (paleta del GIF),
#            A4/A5 (md5 del PCM), P2/P6 (texto extraido con txtwrite).
# ===========================================================================

PSNR_MIN_IMAGEN = 40.0
PSNR_MIN_VIDEO = 40.0
TEXTO_MIN_CHARS = 10          # regla P6: txtwrite emite 1-3 caracteres de
                              # basura en un PDF sin texto ('FX' en
                              # alpha_png-to.pdf). Un umbral de >0 los
                              # tomaria por una capa de texto.
# El plano alfa de AVIF se comprime CON PERDIDA (referencia.json, perdidas):
# alpha.png -> AVIF da 38,8 dB sobre blanco y hasta un alfa 100 % opaco baja a
# 71,4 dB. Exigirle los 40 dB de I7 seria exigir lo que el formato no da.
PSNR_MIN_AVIF_CON_ALFA = 35.0
# Una entrada de 16 bits cuantizada a 8 tiene un techo de PSNR que no depende
# del motor. Medido: patologico_16bit.tif -> JPEG 35,3 dB, -> WebP 34,8 dB,
# y el propio PNG de 8 bits (conversion impecable) se queda en 59,0 dB.
PSNR_MIN_16BIT = 30.0

LOSSLESS_IMG = {"png", "tif", "tiff", "bmp"}
CODEC_PCM_EXACTO = {"flac", "alac", "pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm",
                    "wavpack", "tta"}


def _fid(regla, severidad, mensaje, esperado=None, obtenido=None):
    return {"punto": "F", "regla": regla, "severidad": severidad,
            "mensaje": mensaje, "esperado": esperado, "obtenido": obtenido}


_SOBRE_BLANCO = ["-background", "white", "-alpha", "remove", "-alpha", "off"]


def _magick_metrica(a: str, b: str, metrica: str, aplanar: bool = False):
    """`magick compare`. OJO: en esta build -metric SSIM devuelve 0 para
    imagenes IDENTICAS (se comporta como disimilitud). Solo PSNR y RMSE.

    aplanar=True compone AMBOS lados sobre blanco antes de comparar: es lo que
    hace falta cuando uno tiene alfa y el otro no (es el
    'psnr_rgb_sobre_blanco_db' de referencia.json). Reproduce sus cifras:
    alpha.png -> AVIF 38,78 dB y -> WebP 43,87 dB.
    """
    if aplanar:
        orden = (["magick", "compare", "-limit", "thread", "4", "-metric", metrica]
                 + ["("] + [a] + _SOBRE_BLANCO + [")"]
                 + ["("] + [b] + _SOBRE_BLANCO + [")"] + ["null:"])
    else:
        orden = ["magick", "compare", "-limit", "thread", "4",
                 "-metric", metrica, a, b, "null:"]
    rc, out, err = _correr(orden)
    txt = (err or out).strip().splitlines()
    if not txt:
        return None, "sin salida (rc=%d)" % rc
    campo = txt[-1].split()[0] if txt[-1].split() else ""
    try:
        return float(campo), None
    except ValueError:
        if campo.lower() in ("inf", "1.#inf", "nan"):
            return float("inf"), None
        return None, txt[-1][:200]


def _ffmpeg_md5_pcm(ruta: str, pista: int = 0):
    rc, out, err = _correr(["ffmpeg", "-v", "error", "-i", ruta, "-vn", "-sn",
                            "-map", "0:a:%d" % pista, "-f", "md5",
                            "-c:a", "pcm_s16le", "-"])
    for l in out.splitlines():
        if l.startswith("MD5="):
            return l[4:].strip(), None
    return None, (err or out).strip()[:200]


def _ffmpeg_pcm(ruta: str, limite: int = 96 << 20):
    """PCM s16le crudo de la primera pista de audio. Se usa SOLO para explicar
    una diferencia de md5 en un remux; por eso lleva techo de memoria."""
    try:
        p = subprocess.run(["ffmpeg", "-v", "error", "-i", ruta, "-vn", "-sn",
                            "-map", "0:a:0", "-f", "s16le", "-c:a", "pcm_s16le", "-"],
                           capture_output=True, timeout=TIMEOUT)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return p.stdout if p.stdout and len(p.stdout) <= limite else None


def _pcm_desfase(a: bytes, b: bytes):
    """Devuelve cuantas MUESTRAS de mas lleva 'b' al principio si, quitadas,
    el PCM es identico byte a byte. None si son genuinamente distintos.

    MEDIDO: tipico.mp4 -> MKV con `-c copy` da PCM distinto porque la edit
    list de MP4 recorta el retardo del codificador AAC y Matroska no puede
    expresarla. b[2048:] == a exactamente: 512 muestras de priming, ni un byte
    mas. Es un artefacto de CONTENEDOR, no una perdida de audio.
    """
    if a is None or b is None:
        return None
    if a == b:
        return 0
    if len(a) == len(b):
        return None
    corto, largo = (a, b) if len(a) < len(b) else (b, a)
    d = len(largo) - len(corto)
    if largo[d:] == corto or largo[:len(corto)] == corto:
        return d // 4 if len(b) > len(a) else -(d // 4)
    return None


def _ffmpeg_framemd5(ruta: str):
    """md5 de la ULTIMA columna de framemd5: el hash por fotograma SIN marcas
    de tiempo. El framemd5 completo cambia al remuxar (la base de tiempos pasa
    de 1/15360 a 1/1000) aunque no se toque un solo pixel."""
    import hashlib
    rc, out, err = _correr(["ffmpeg", "-v", "error", "-i", ruta, "-an", "-sn",
                            "-f", "framemd5", "-"])
    h = hashlib.md5()
    n = 0
    for l in out.splitlines():
        if not l.strip() or l.startswith("#"):
            continue
        h.update(l.rstrip().rsplit(",", 1)[-1].strip().encode())
        n += 1
    if not n:
        return None, 0, (err or "framemd5 vacio").strip()[:200]
    return h.hexdigest(), n, None


def _ffmpeg_psnr(salida: str, entrada: str):
    rc, out, err = _correr(["ffmpeg", "-hide_banner", "-loglevel", "info",
                            "-i", salida, "-i", entrada,
                            "-lavfi", "[0:v][1:v]psnr", "-an", "-sn",
                            "-f", "null", "-"])
    for l in reversed((err or "").splitlines()):
        if "PSNR" in l and " y:" in l:
            d = {}
            for tr in l.split("PSNR", 1)[1].split():
                if ":" in tr:
                    k, v = tr.split(":", 1)
                    try:
                        d[k] = float(v)
                    except ValueError:
                        d[k] = float("inf") if v.lower().startswith("inf") else None
            return d, None
    return None, (err or "").strip()[-200:]


def _gs_texto(pdf: str):
    """Texto extraido con `gs -sDEVICE=txtwrite`. Un `gs` completo ronda los
    180 ms: por eso el contrato usa '/Font' como indicio barato y esto vive
    aqui."""
    rc, out, err = _correr(["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                            "-sDEVICE=txtwrite", "-sOutputFile=-", pdf])
    if rc != 0 and not out:
        return None, (err or "gs fallo").strip()[:200]
    return out, None


def _pixel_magick(ruta: str, x: int, y: int):
    rc, out, err = _correr(["magick", ruta, "-alpha", "off", "-colorspace", "sRGB",
                            "-format", "%%[pixel:p{%d,%d}]" % (x, y), "info:"])
    if rc != 0:
        return None, (err or "").strip()[:200]
    t = out.strip()
    if "(" not in t:
        return None, t[:200]
    try:
        piezas = t[t.index("(") + 1:t.rindex(")")].split(",")
        v = []
        for p in piezas[:3]:
            p = p.strip()
            v.append(round(float(p.rstrip("%")) * 2.55) if p.endswith("%") else int(float(p)))
        return tuple(v), None
    except (ValueError, IndexError):
        return None, t[:200]


def _paleta_gif(ruta: str):
    """Tabla de color global de un GIF. En proceso, 13+3n bytes leidos."""
    with open(ruta, "rb") as fh:
        cab = fh.read(13)
        if len(cab) < 13 or cab[:3] != b"GIF":
            return None
        banderas = cab[10]
        if not banderas & 0x80:
            return []
        n = 2 ** ((banderas & 0x07) + 1)
        cuerpo = fh.read(3 * n)
    return [tuple(cuerpo[3 * i:3 * i + 3]) for i in range(n)]


def _paleta_es_rejilla(pal):
    """Una paleta GENERICA es el producto cartesiano de pocos valores por canal
    (la de ffmpeg por defecto es la rejilla 8x8x4: R y G a pasos de 36, B a
    pasos de 85). Una paleta calculada sobre el clip (palettegen) NO lo es.
    Medido: la generica da |R|.|G|.|B| = 8.8.4 = 256 = n; la buena, 134.120.127
    = 2.042.160 para 256 colores."""
    if not pal:
        return None
    r = {c[0] for c in pal}
    g = {c[1] for c in pal}
    b = {c[2] for c in pal}
    return len(r) * len(g) * len(b) == len(set(pal))


# ---- las reglas ------------------------------------------------------------

def fidelidad_imagen(salida, entrada, pedido, sonda, sonda_ent, ms):
    h = []
    cob = {}
    p = pedido.get("params", {})
    dest = pedido.get("destino", "").lower().lstrip(".")
    pr_e = _prof(sonda_ent)
    pedido_geom = any(k in p for k in ("ancho", "alto", "escala", "dpi", "densidad"))

    # ---- I3: el color del aplanado cuando el destino no admite alfa --------
    # Solo si la ENTRADA es una imagen: un PDF no tiene canal alfa que aplanar
    # y marcar I3 como "no cubierta" ahi seria ruido, no honestidad.
    if (dest in SIN_ALFA and dest != "pdf" and not p.get("fondo")
            and sonda_ent.get("categoria") == "imagen"):
        cob["I3"] = False
        t0 = time.perf_counter()
        a = alfa_minimo(entrada)
        if a.get("evaluable") and a.get("primer_transparente"):
            x, y = a["primer_transparente"]
            px, err = _pixel_magick(salida, x, y)
            ms["I3"] = (time.perf_counter() - t0) * 1000
            if px is None:
                h.append(_fid("I3", "informativo", "no se pudo leer el pixel", None, err))
            else:
                cob["I3"] = True
                if all(v >= 253 for v in px):
                    h.append(_fid("I3", "informativo",
                                  "aplanado sobre BLANCO en (%d,%d): correcto" % (x, y),
                                  "srgb(255,255,255)", "srgb%s" % (px,)))
                elif all(v <= 2 for v in px):
                    h.append(_fid("I3", "aviso",
                                  "APLANADO SOBRE NEGRO: el pixel (%d,%d), 100 %% "
                                  "transparente en la entrada, sale negro" % (x, y),
                                  "srgb(255,255,255)", "srgb%s" % (px,)))
                else:
                    h.append(_fid("I3", "aviso",
                                  "aplanado sobre un color que no es blanco",
                                  "srgb(255,255,255)", "srgb%s" % (px,)))
        else:
            ms["I3"] = (time.perf_counter() - t0) * 1000
            if a.get("evaluable"):
                cob["I3"] = True  # la entrada no tiene zonas transparentes

    if sonda_ent.get("categoria") != "imagen" or sonda.get("categoria") != "imagen":
        return h, cob
    if pedido_geom or p.get("recortar"):
        return h, cob  # geometria distinta: no hay comparacion pixel a pixel

    reduccion = bool(p.get("profundidad_bits") and pr_e and p["profundidad_bits"] < pr_e)
    exacta = dest in LOSSLESS_IMG and not reduccion
    # cuando uno de los dos lleva alfa y el otro no, hay que componer los dos
    # sobre blanco: comparar RGBA contra RGB da cifras sin sentido (alpha.png
    # frente a su JPEG aplanado sobre blanco da 1,9 dB si no se compone).
    aplanar = bool(sonda_ent.get("tiene_alfa")) != bool(sonda.get("tiene_alfa"))
    # Grafismo: pocos colores planos. Indicio EN PROCESO y exacto: el PNG de
    # origen es de paleta (color type 3) o es un GIF. El umbral de 40 dB de I7
    # esta calibrado "para fotografia" (referencia.json): un grafismo con
    # bordes duros cae por debajo aunque la conversion sea correcta
    # (alpha.png -> JPEG aplanado sobre BLANCO da 35,5 dB).
    grafismo = bool(sonda_ent.get("paleta") or sonda_ent.get("colores_paleta"))

    # ---- I6: conversion sin perdida declarada -> RMSE = 0 ------------------
    if exacta:
        t0 = time.perf_counter()
        v, err = _magick_metrica(entrada, salida, "RMSE", aplanar)
        ms["I6"] = (time.perf_counter() - t0) * 1000
        cob["I6"] = v is not None
        if v is None:
            h.append(_fid("I6", "informativo", "RMSE no calculable", None, err))
        elif v > 0:
            h.append(_fid("I6", "fallo",
                          "conversion SIN PERDIDA que no conserva los pixeles",
                          "RMSE 0", v))
        else:
            h.append(_fid("I6", "informativo", "pixeles identicos (RMSE 0)", 0, 0))
        return h, cob

    # ---- I8: grafismo a un destino que admite SIN PERDIDA -------------------
    # referencia.json: "Con -define webp:lossless=true la conversion es exacta Y
    # mas pequena (42 B contra 94 B). Usar codificacion con perdida sobre
    # grafismo es una eleccion mala del motor."
    if grafismo and dest in ("webp", "avif") and sonda.get("perdida") is not False:
        cob["I8"] = True
        h.append(_fid("I8", "aviso",
                      "grafismo (origen de paleta) codificado CON PERDIDA en un "
                      "destino que admite sin perdida", "%s sin perdida" % dest,
                      "%s con perdida" % dest))

    # ---- I7: conversion con perdida -> PSNR --------------------------------
    t0 = time.perf_counter()
    v, err = _magick_metrica(entrada, salida, "PSNR", aplanar)
    ms["I7"] = (time.perf_counter() - t0) * 1000
    cob["I7"] = v is not None
    if v is None:
        h.append(_fid("I7", "informativo", "PSNR no calculable", None, err))
        return h, cob
    nota = " (sobre blanco)" if aplanar else ""
    if v >= PSNR_MIN_IMAGEN:
        h.append(_fid("I7", "informativo", "PSNR %.2f dB%s" % (v, nota),
                      ">= %.1f dB" % PSNR_MIN_IMAGEN, v))
        return h, cob
    # Por debajo del umbral. Tres excepciones justificadas con datos del propio
    # patron oro; fuera de ellas, es un aviso.
    excusa = None
    if dest in ("avif", "heic", "heif") and sonda_ent.get("tiene_alfa"):
        excusa = ("AVIF comprime el plano alfa CON PERDIDA (referencia.json, "
                  "perdidas): alpha.png -> AVIF da 38,8 dB sobre blanco")
    elif grafismo and v >= 20.0:
        # Suelo de 20 dB: la excusa "es un grafismo" cubre la caida por bordes
        # duros (alpha.png -> JPEG sobre blanco: 35,5 dB), NO una imagen
        # distinta. alpha_png-to.jpg da 0,70 dB porque esta aplanada sobre
        # NEGRO, y eso si es un hallazgo (lo firma I3).
        excusa = ("grafismo, no fotografia: el umbral de 40 dB de I7 esta "
                  "calibrado para fotografia; los bordes duros lo hunden")
    elif pr_e and pr_e > 8 and v >= PSNR_MIN_16BIT:
        excusa = ("entrada de %d bits cuantizada a 8: el techo no depende del "
                  "motor (16bit_tif -> JPEG 35,3 dB, -> WebP 34,8 dB)" % pr_e)
    if excusa:
        h.append(_fid("I7", "informativo", "PSNR %.2f dB%s por debajo de %.0f dB, "
                      "excepcion justificada: %s" % (v, nota, PSNR_MIN_IMAGEN, excusa),
                      ">= %.1f dB" % PSNR_MIN_IMAGEN, v))
    else:
        h.append(_fid("I7", "aviso", "PSNR por debajo del umbral" + nota,
                      ">= %.1f dB" % PSNR_MIN_IMAGEN, v))
    return h, cob


def fidelidad_video(salida, entrada, pedido, sonda, sonda_ent, ms):
    h = []
    cob = {}
    p = pedido.get("params", {})
    dest = pedido.get("destino", "").lower().lstrip(".")

    # ---- V9: la paleta del GIF (en proceso, microsegundos) -----------------
    if dest == "gif":
        t0 = time.perf_counter()
        pal = _paleta_gif(salida)
        rejilla = _paleta_es_rejilla(pal)
        ms["V9"] = (time.perf_counter() - t0) * 1000
        cob["V9"] = rejilla is not None
        if rejilla is True:
            r = sorted({c[0] for c in pal})
            h.append(_fid("V9", "aviso",
                          "PALETA GENERICA: la tabla de color es una rejilla "
                          "regular (%dx%dx%d), no se calculo sobre el clip"
                          % (len(r), len({c[1] for c in pal}), len({c[2] for c in pal})),
                          "paleta derivada del clip (palettegen)", "rejilla fija"))
        elif rejilla is False:
            h.append(_fid("V9", "informativo",
                          "paleta calculada sobre el clip", None, len(set(pal))))
        return h, cob

    if sonda.get("n_video", 0) < 1 or sonda_ent.get("n_video", 0) < 1:
        return h, cob
    if p.get("escala") or p.get("fps") or p.get("recortar"):
        return h, cob

    # ---- V6: remux sin recodificar -> framemd5 por pixel identico ----------
    t0 = time.perf_counter()
    hs, ns, es = _ffmpeg_framemd5(salida)
    he, ne, ee = _ffmpeg_framemd5(entrada)
    ms["V6"] = (time.perf_counter() - t0) * 1000
    cob["V6"] = hs is not None and he is not None
    copia = bool(p.get("copia"))
    if hs and he:
        if hs == he:
            h.append(_fid("V6", "informativo",
                          "remux exacto: %d fotogramas con el mismo hash por pixel" % ns,
                          he, hs))
            cob["V8"] = True
            return h, cob
        if copia:
            h.append(_fid("V6", "fallo",
                          "se pidio COPIAR el flujo y los pixeles cambian", he, hs))
        elif ns != ne:
            h.append(_fid("V6", "aviso", "cambia el numero de fotogramas", ne, ns))
    else:
        h.append(_fid("V6", "informativo", "framemd5 no calculable", None, es or ee))

    # ---- V8: recodificacion -> PSNR de luminancia --------------------------
    t0 = time.perf_counter()
    d, err = _ffmpeg_psnr(salida, entrada)
    ms["V8"] = (time.perf_counter() - t0) * 1000
    cob["V8"] = d is not None
    if d is None:
        h.append(_fid("V8", "informativo", "PSNR no calculable", None, err))
    else:
        y = d.get("y")
        if y is None:
            h.append(_fid("V8", "informativo", "PSNR sin componente y", None, d))
        elif y < PSNR_MIN_VIDEO:
            h.append(_fid("V8", "aviso", "PSNR de luminancia bajo",
                          ">= %.0f dB" % PSNR_MIN_VIDEO, y))
        else:
            h.append(_fid("V8", "informativo", "PSNR y %.2f dB" % y,
                          ">= %.0f dB" % PSNR_MIN_VIDEO, y))
    return h, cob


def fidelidad_audio(salida, entrada, pedido, sonda, sonda_ent, ms):
    """A4/A5: el PCM decodificado debe ser identico bit a bit cuando el destino
    es SIN PERDIDA y no se pidio remuestrear ni mezclar canales."""
    h = []
    cob = {}
    p = pedido.get("params", {})
    if sonda.get("n_audio", 0) < 1 or sonda_ent.get("n_audio", 0) < 1:
        return h, cob
    cods = {_codec_norm(x.get("codec")) for x in sonda.get("pistas", [])
            if x.get("tipo") == "audio"}
    if not (cods & CODEC_PCM_EXACTO) and not p.get("copia"):
        return h, cob                     # destino con perdida: nada que exigir
    if p.get("sample_rate") or p.get("canales") or p.get("recortar"):
        return h, cob
    regla = "A5" if p.get("solo_audio") else "A4"
    t0 = time.perf_counter()
    ms_, es = _ffmpeg_md5_pcm(salida)
    me_, ee = _ffmpeg_md5_pcm(entrada)
    ms[regla] = (time.perf_counter() - t0) * 1000
    cob[regla] = ms_ is not None and me_ is not None
    if not (ms_ and me_):
        h.append(_fid(regla, "informativo", "md5 del PCM no calculable", None, es or ee))
    elif ms_ != me_:
        # EXCEPCION JUSTIFICADA CON DATOS: si ffmpeg INFLA la profundidad
        # (regla A6), el PCM ya no es comparable bit a bit. Medido: tipico.mp3
        # da f5ddaa64 en s16; su FLAC, escrito a 24 bits, da 984b4619. La
        # informacion se conserva; lo que cambia es el redondeo de 24 a 16 al
        # medir. Exigir igualdad ahi es un falso positivo, no un fallo.
        pr_s, pr_e = _prof(sonda), _prof(sonda_ent)
        cods_e = {_codec_norm(x.get("codec")) for x in sonda_ent.get("pistas", [])
                  if x.get("tipo") == "audio"}
        prof_efectiva_e = pr_e if (cods_e & CODEC_SIN_PERDIDA) else 16
        desfase = None
        if p.get("copia"):
            # Remux con -c copy: comprobar EXACTAMENTE si la diferencia es el
            # priming del codificador que la edit list de MP4 recorta.
            desfase = _pcm_desfase(_ffmpeg_pcm(entrada), _ffmpeg_pcm(salida))
        if desfase:
            h.append(_fid(regla, "informativo",
                          "remux exacto salvo %d muestras de priming al principio: "
                          "la edit list de MP4 las recorta y Matroska no puede "
                          "expresarla. El resto del PCM es identico byte a byte"
                          % abs(desfase), me_, ms_))
        elif (pr_s and prof_efectiva_e and pr_s > prof_efectiva_e
                and (cods & CODEC_PCM_EXACTO)):
            h.append(_fid(regla, "aviso",
                          "el PCM no coincide, pero la profundidad esta INFLADA "
                          "(%d bits sobre un origen de %d efectivos, regla A6): "
                          "el redondeo al medir explica la diferencia"
                          % (pr_s, prof_efectiva_e), me_, ms_))
        else:
            sev = "aviso" if regla == "A5" else "fallo"
            h.append(_fid(regla, sev, "el PCM decodificado NO es identico", me_, ms_))
    else:
        h.append(_fid(regla, "informativo", "PCM identico bit a bit", me_, ms_))
    return h, cob


def fidelidad_pdf(salida, entrada, pedido, sonda, sonda_ent, ms):
    """P2/P6: el texto extraible. El umbral son 10 caracteres, no 1: txtwrite
    emite basura corta (2 caracteres, 'FX', en alpha_png-to.pdf)."""
    import hashlib
    h = []
    cob = {}
    if sonda.get("categoria") != "pdf":
        return h, cob
    t0 = time.perf_counter()
    ts, es = _gs_texto(salida)
    ms["P6"] = (time.perf_counter() - t0) * 1000
    if ts is None:
        h.append(_fid("P6", "informativo", "txtwrite fallo sobre la salida", None, es))
        return h, cob
    ns = len("".join(ts.split()))
    cob["P6"] = True
    h.append(_fid("P6", "informativo",
                  "texto extraido: %d caracteres imprimibles (umbral %d)"
                  % (ns, TEXTO_MIN_CHARS),
                  ">= %d para considerar que hay capa de texto" % TEXTO_MIN_CHARS,
                  ns))
    if 0 < ns < TEXTO_MIN_CHARS:
        h.append(_fid("P6", "informativo",
                      "txtwrite devuelve %d caracteres (%r): BASURA, no una capa "
                      "de texto" % (ns, ts.strip()[:16]), 0, ns))
    if sonda_ent.get("categoria") != "pdf":
        return h, cob
    t0 = time.perf_counter()
    te, ee = _gs_texto(entrada)
    ms["P2"] = (time.perf_counter() - t0) * 1000
    if te is None:
        h.append(_fid("P2", "informativo", "txtwrite fallo sobre la entrada", None, ee))
        return h, cob
    ne = len("".join(te.split()))
    cob["P2"] = True
    if ne < TEXTO_MIN_CHARS:
        h.append(_fid("P5", "informativo",
                      "la entrada no tiene capa de texto (%d caracteres): no se "
                      "exige texto en la salida" % ne, None, ne))
        return h, cob
    hs = hashlib.sha256("".join(ts.split()).encode("utf-8")).hexdigest()
    he = hashlib.sha256("".join(te.split()).encode("utf-8")).hexdigest()
    if hs != he:
        h.append(_fid("P2", "fallo",
                      "PDF -> PDF que NO conserva el texto (%d -> %d caracteres)"
                      % (ne, ns), he[:16], hs[:16]))
    else:
        h.append(_fid("P2", "informativo", "texto conservado ntegro (sha256 igual)",
                      he[:16], hs[:16]))
    return h, cob


REGLAS_FIDELIDAD = ("I3", "I6", "I7", "V6", "V8", "V9", "A4", "A5", "P2", "P6")


def verificar_fidelidad(salida: str, pedido: dict | None = None,
                        entrada: str | None = None, motor: str = "proceso",
                        sonda_ent: dict | None = None,
                        sonda_sal: dict | None = None) -> dict:
    """Segunda mitad, bajo demanda: las reglas de fidelidad de referencia.json.

    Devuelve su propio veredicto y su propia COBERTURA: una regla que no se
    pudo evaluar no cuenta como aprobada.
    """
    pedido = dict(pedido or {})
    pedido.setdefault("destino", os.path.splitext(salida)[1].lstrip(".").lower())
    ms = {}
    t0 = time.perf_counter()
    if sonda_sal is None:
        sonda_sal = sondear(salida, motor)
    if sonda_ent is None and entrada:
        sonda_ent = sondear(entrada, motor)
    ms["sondeo"] = (time.perf_counter() - t0) * 1000
    hallazgos, cobertura = [], {}
    if entrada and sonda_ent is not None and not sonda_sal.get("error"):
        cat = sonda_sal.get("categoria")
        dest = pedido.get("destino", "").lower().lstrip(".")
        for fn in (fidelidad_imagen, fidelidad_video, fidelidad_audio, fidelidad_pdf):
            if fn is fidelidad_imagen and cat not in ("imagen",):
                continue
            # Un GIF es categoria 'imagen' para la sonda, pero la regla V9 (la
            # paleta) es de video -> GIF: hay que despacharla por el DESTINO.
            if fn is fidelidad_video and cat != "av" and dest != "gif":
                continue
            if fn is fidelidad_audio and cat != "av":
                continue
            if fn is fidelidad_pdf and cat != "pdf":
                continue
            hh, cc = fn(salida, entrada, pedido, sonda_sal, sonda_ent, ms)
            hallazgos.extend(hh)
            cobertura.update(cc)
    else:
        hallazgos.append(_fid("-", "informativo",
                              "sin entrada de referencia: la fidelidad no es evaluable"))
    sev = {x["severidad"] for x in hallazgos}
    veredicto = "fallo" if "fallo" in sev else ("aviso" if "aviso" in sev else "ok")
    if veredicto == "ok" and not (cobertura and all(cobertura.values())):
        veredicto = "ok_parcial"
    ms["total"] = sum(v for k, v in ms.items() if k != "total")
    return {"salida": salida, "entrada": entrada, "veredicto": veredicto,
            "categoria": sonda_sal.get("categoria"), "cobertura": cobertura,
            "hallazgos": hallazgos, "ms": ms}


# ===========================================================================
# CLI
# ===========================================================================

AYUDA = """Contrato de verificacion de FileX, en TRES grupos con presupuestos distintos.

  GRUPO A - CONTRATO (siempre, ~0,37 ms, el 0,032 % de convertir)
      python verificador.py --salida SAL --entrada ENT --destino webp
    Puntos 1-4 de PLAN-ORQUESTADOR.md 4.2. Veredicto: ok / aviso / ok_parcial /
    fallo. Es el unico grupo que puede correr dentro de un lote.

  GRUPO B - CARACTERIZACION DE LA ENTRADA (una vez por ENTRADA, cacheable)
      python verificador.py --alfa-min ENT            # el dato, suelto
      python verificador.py --salida SAL ... --alfa   # y usado por la regla I2
    min(alfa) en proceso: el unico dato del contrato que exige decodificar
    pixeles. SIN el, la regla I2 no es evaluable y el veredicto baja a
    'ok_parcial' con cobertura 4_alfa=false. NUNCA se calcula por defecto.

  GRUPO C - FIDELIDAD (bajo demanda o en regresion; cuesta como convertir)
      python verificador.py --salida SAL --entrada ENT --solo-fidelidad
      python verificador.py --salida SAL --entrada ENT --alfa --fidelidad
    Reglas I3/I6/I7/I8, V6/V8/V9, A4/A5, P2/P6 de referencia.json.

  Los veredictos de A y C son SEPARADOS A PROPOSITO: un aviso de fidelidad
  (por ejemplo 'aplanado sobre negro') NO convierte en 'aviso' el veredicto
  del contrato, porque son preguntas distintas. Con --fidelidad se imprimen
  los dos bloques, cada uno con su veredicto y su cobertura. El codigo de
  salida es 1 si CUALQUIERA de los dos es 'fallo'.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Contrato de verificacion de FileX (grupos A/B/C)",
        epilog=AYUDA, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", metavar="F",
                    help="[A] fichero producido por la conversion, el que se juzga")
    ap.add_argument("--entrada", metavar="F",
                    help="[A] fichero de origen. Sin el, los puntos 2 y 4 no son "
                         "evaluables y el veredicto baja a 'ok_parcial'")
    ap.add_argument("--destino", metavar="EXT",
                    help="[A] extension/formato PEDIDO (webp, mp4, pdf...). Por "
                         "defecto, la extension de --salida")
    ap.add_argument("--params", default="{}", metavar="JSON",
                    help="[A] lo que se pidio de verdad, en JSON: "
                         '{"ancho":800,"profundidad_bits":8,"dpi":150,'
                         '"solo_audio":true,"copia":true,"fondo":"white"}. '
                         "Es lo que separa una conversion impecable de una "
                         "degradacion silenciosa (por defecto: {})")
    ap.add_argument("--motor", choices=["proceso", "subproceso"], default="proceso",
                    help="[A] motor de sondeo: 'proceso' (solo Python, 0,37 ms) o "
                         "'subproceso' (ffprobe/magick/gs, 54 ms). Por defecto: proceso")
    ap.add_argument("--lote", metavar="F.json",
                    help="[A/C] JSON con [{salida, entrada, destino, params}]; "
                         "respeta --alfa y --fidelidad y vuelca todo en JSON")
    ap.add_argument("--sondear", metavar="F",
                    help="[A] solo volcar el sondeo de un fichero, sin juzgarlo "
                         "(anade min(alfa) si se pasa --alfa)")
    ap.add_argument("--alfa-min", metavar="F",
                    help="[B] calcula min(alfa) de UN fichero EN PROCESO, sin "
                         "magick, y lo vuelca en JSON. Cubre PNG y WebP; en "
                         "AVIF, TIFF comprimido, GIF y PNG entrelazado devuelve "
                         "evaluable=false con el motivo, nunca un valor inventado")
    ap.add_argument("--exacto", action="store_true",
                    help="[B] con --alfa-min: recorre la imagen ENTERA para dar el "
                         "minimo exacto. Por defecto se corta en el primer pixel "
                         "no opaco (basta para la regla I2) y se marca exacto=false")
    ap.add_argument("--alfa", action="store_true",
                    help="[B] calcula min(alfa) de la ENTRADA en proceso cuando la "
                         "regla I2 lo necesita y no viene inyectado. Sin esta "
                         "bandera, I2 se declara no evaluable (cobertura "
                         "4_alfa=false) en vez de darse por buena")
    ap.add_argument("--fidelidad", action="store_true",
                    help="[C] ejecuta el contrato Y ADEMAS las reglas de FIDELIDAD "
                         "(I3/I6/I7/I8, V6/V8/V9, A4/A5, P2/P6). Se imprimen DOS "
                         "bloques con DOS veredictos separados: un aviso de "
                         "fidelidad no contamina el veredicto del contrato. "
                         "Cuesta lo que convertir: NO es el camino caliente")
    ap.add_argument("--solo-fidelidad", action="store_true",
                    help="[C] ejecuta SOLO las reglas de fidelidad y omite el "
                         "contrato. Util para reejecutar el grupo C sobre una "
                         "salida ya verificada")
    ap.add_argument("--json", action="store_true",
                    help="vuelca el resultado completo en JSON (hallazgos, "
                         "cobertura y tiempos por punto y por regla)")
    a = ap.parse_args(argv)

    if a.alfa_min:
        print(json.dumps(alfa_minimo(a.alfa_min, exacto=a.exacto),
                         ensure_ascii=False, indent=1, default=str))
        return 0
    if a.sondear:
        print(json.dumps(sondear(a.sondear, a.motor, alfa=a.alfa), ensure_ascii=False,
                         indent=1, default=str))
        return 0
    if a.lote:
        trabajos = json.load(open(a.lote, encoding="utf-8"))
        res = []
        for t in trabajos:
            r = verificar(t["salida"], t.get("pedido", t), t.get("entrada"),
                          a.motor, alfa=a.alfa)
            if a.fidelidad or a.solo_fidelidad:
                r["fidelidad"] = verificar_fidelidad(
                    t["salida"], t.get("pedido", t), t.get("entrada"), a.motor)
            res.append(r)
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0 if all(r["veredicto"] != "fallo" for r in res) else 1
    if not a.salida:
        ap.error("se requiere --salida, --lote, --sondear o --alfa-min")
    pedido = {"destino": a.destino or os.path.splitext(a.salida)[1].lstrip("."),
              "params": json.loads(a.params)}
    if a.solo_fidelidad:
        r = verificar_fidelidad(a.salida, pedido, a.entrada, a.motor)
    else:
        r = verificar(a.salida, pedido, a.entrada, a.motor, alfa=a.alfa)
        if a.fidelidad:
            r["fidelidad"] = verificar_fidelidad(a.salida, pedido, a.entrada, a.motor)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
    else:
        _imprimir(r, a.salida,
                  "FIDELIDAD (grupo C)" if a.solo_fidelidad else "CONTRATO (grupo A)")
        # El grupo C se IMPRIME SIEMPRE que se haya ejecutado, con su propio
        # veredicto. Que los veredictos esten separados es deliberado; que el
        # grupo C fuera invisible en la salida de texto era un cabo.
        if r.get("fidelidad"):
            print()
            _imprimir(r["fidelidad"], a.salida, "FIDELIDAD (grupo C)")
    fid = r.get("fidelidad") or {}
    return 0 if "fallo" not in (r["veredicto"], fid.get("veredicto")) else 1


def _imprimir(r, salida, titulo):
    print("%-22s %-10s %s" % (titulo, r["veredicto"].upper(), salida))
    if not r["hallazgos"]:
        print("  (sin hallazgos)")
    for h in r["hallazgos"]:
        print("  [p%s %s %s] %s  esperado=%s obtenido=%s"
              % (h["punto"], h["regla"], h["severidad"], h["mensaje"],
                 h["esperado"], h["obtenido"]))
    cob = r.get("cobertura") or {}
    sin = [k for k, v in cob.items() if not v]
    print("  cobertura: %s%s" % ("completa" if cob and not sin else
                                 ("sin reglas aplicables" if not cob else "PARCIAL"),
                                 (" (sin cubrir: %s)" % ", ".join(sin)) if sin else ""))
    print("  ms: %s" % {k: round(v, 3) for k, v in r["ms"].items()})


if __name__ == "__main__":
    sys.exit(main())
