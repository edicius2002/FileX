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


def sondear(ruta: str, motor: str = "proceso") -> dict:
    return sondear_en_proceso(ruta) if motor == "proceso" else sondear_subproceso(ruta)


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
              sonda_sal: dict | None = None) -> dict:
    """Ejecuta los cuatro puntos del contrato y cronometra cada uno."""
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
                 "4_pedido": sonda_ent is not None and not sonda_sal.get("error")}
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
# CLI
# ===========================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Contrato de verificacion de FileX")
    ap.add_argument("--salida")
    ap.add_argument("--entrada")
    ap.add_argument("--destino")
    ap.add_argument("--params", default="{}")
    ap.add_argument("--motor", choices=["proceso", "subproceso"], default="proceso")
    ap.add_argument("--lote", help="JSON con [{salida, entrada, destino, params}]")
    ap.add_argument("--sondear", help="solo volcar el sondeo de un fichero")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.sondear:
        print(json.dumps(sondear(a.sondear, a.motor), ensure_ascii=False,
                         indent=1, default=str))
        return 0
    if a.lote:
        trabajos = json.load(open(a.lote, encoding="utf-8"))
        res = [verificar(t["salida"], t.get("pedido", t), t.get("entrada"), a.motor)
               for t in trabajos]
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return 0 if all(r["veredicto"] != "fallo" for r in res) else 1
    if not a.salida:
        ap.error("se requiere --salida, --lote o --sondear")
    pedido = {"destino": a.destino or os.path.splitext(a.salida)[1].lstrip("."),
              "params": json.loads(a.params)}
    r = verificar(a.salida, pedido, a.entrada, a.motor)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
    else:
        print("%-10s %s" % (r["veredicto"].upper(), a.salida))
        for h in r["hallazgos"]:
            print("  [p%s %s %s] %s  esperado=%s obtenido=%s"
                  % (h["punto"], h["regla"], h["severidad"], h["mensaje"],
                     h["esperado"], h["obtenido"]))
        print("  ms: %s" % {k: round(v, 3) for k, v in r["ms"].items()})
    return 0 if r["veredicto"] != "fallo" else 1


if __name__ == "__main__":
    sys.exit(main())
