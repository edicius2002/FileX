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
#
# EL VOCABULARIO, Y POR QUE TIENE ESTE TAMANO (F1, bench/firmas-contrato.md).
# Hasta el 21/08/2026 esta tabla tenia 24 nombres, y E1 midio que con ella el
# punto 1 solo fue EVALUABLE en el 12 % de los destinos de una muestra de 498
# aristas (bench/aristas-nominales.md sec.11.3). La ampliacion NO sale de leer
# especificaciones: sale de un CENSO EJECUTADO. Cada uno de los 502 formatos de
# salida que declaran los 20 adaptadores de ConvertX se escribio DOS O TRES veces
# con contenidos deliberadamente distintos (ruido con semillas distintas, otra
# geometria, otra senal de audio) y se miro en que posiciones de los primeros 64
# bytes coincidian TODAS las muestras. 423 de los 502 se pudieron escribir con los
# motores de esta maquina y del contenedor.
#
# Y HAY UNA TERCERA RESPUESTA, que es la que faltaba: EXT_SIN_FIRMA. Son los
# formatos para los que el censo midio que NO HAY marcador — pixeles crudos sin
# cabecera (rgb, gray, yuv, cmyk...), fax CCITT (g3/g4), PCM crudo (sb/ub/sw/al),
# y el texto plano de markup (md, rst, org, txt, csv). Ahi el punto 1 no es un
# fallo ni una laguna nuestra: NO APLICA. Un verificador que dice "no se" donde no
# se puede saber es honesto; uno que dice "fallo" fabrica un falso positivo.
#
# DOS FALSOS POSITIVOS DEL METODO, pagados y corregidos (estan en el informe):
#  (a) dos semillas de audio con el mismo seno de fase 0 dan a los formatos de PCM
#      CRUDO un "prefijo comun" de 64 bytes que es la senal, no un marcador;
#  (b) hay formatos que estampan el nombre o la ruta del fichero en la cabecera
#      (`info`, `shtml`, `uil`, `pdb`): con nombres de muestra parecidos, ese texto
#      compartido se cuenta como marcador. Las muestras van en directorios y con
#      nombres distintos por eso.
# ===========================================================================

_NCAB = 512   # bytes de cabecera que se leen. Un solo read, una sola pagina.

# (desplazamiento, bytes, formato). Orden importante: lo mas especifico antes.
FIRMAS = [
    # --- imagen de trama ---
    (0, b"\x89PNG\r\n\x1a\n", "png"),
    (0, b"\x8aMNG\r\n\x1a\n", "mng"),
    (0, b"\x8bJNG\r\n\x1a\n", "jng"),
    (0, b"\xff\xd8\xff", "jpeg"),                      # SOI: jpg, jls, mjpeg, ljpg
    (0, b"\x00\x00\x00\x0cjP  \r\n\x87\n", "jpeg2000"),
    (0, b"\xff\x4f\xff\x51", "jpeg2000"),              # codestream J2K crudo
    (0, b"\x00\x00\x00\x0cJXL \r\n\x87\n", "jxl"),
    (0, b"\xff\x0a", "jxl"),
    (0, b"GIF87a", "gif"),
    (0, b"GIF89a", "gif"),
    (0, b"BM", "bmp"),
    (0, b"II*\x00", "tiff"),
    (0, b"MM\x00*", "tiff"),
    (0, b"II+\x00", "bigtiff"),
    (0, b"MM\x00+", "bigtiff"),
    (0, b"8BPS", "psd"),                               # psd y psb
    (0, b"\x01\xda", "sgi"),
    (0, b"\x59\xa6\x6a\x95", "sunras"),                # ras, sun, im1/im8/im24, rs
    (0, b"DDS ", "dds"),
    (0, b"v/1\x01", "exr"),
    (0, b"#?RADIANCE", "radiance"),
    (0, b"#?RGBE", "radiance"),
    (0, b"SDPX", "dpx"),
    (0, b"XPDS", "dpx"),
    (0, b"\x80\x2a\x5f\xd7", "cineon"),
    (0, b"\xb1\x68\xde\x3a", "dcx"),
    # JBIG ANTES QUE ICO: comparten `00 00 01 00` y el de JBIG es mas largo. Un ICO
    # valido no puede llevar 0 imagenes, asi que `00 00 01 00 00 00` nunca es un ICO.
    (0, b"\x00\x00\x01\x00\x00\x00", "jbig"),
    (0, b"\x00\x00\x01\x00", "ico"),
    # OJO, colision declarada: un TGA sin comprimir empieza tambien por
    # `00 00 02 00 ...`. No produce falso positivo porque `.tga` esta en
    # EXT_SIN_FIRMA (no tiene marcador), pero un TGA con extension .cur pasaria.
    (0, b"\x00\x00\x02\x00", "cur"),
    (0, b"qoif", "qoi"),
    (0, b"farbfeld", "farbfeld"),
    (0, b"id=ImageMagick", "miff"),
    (0, b"id=MagickPixelCache", "mpc"),
    (0, b"\xab\x01\x01\x03", "viff"),
    (0, b"\xff\x57\x50\x43", "wpg"),
    (0, b"SIMPLE  =", "fits"),
    (0, b"LBLSIZE=", "vicar"),
    (0, b"iiii\x04\x00\x00\x00", "ipl"),
    (0, b"\xd7\xcd\xc6\x9a", "wmf"),                   # WMF "placeable" de Aldus
    (0, b"gimp xcf ", "xcf"),
    (0, b"MATLAB 5.0", "mat"),
    (0, b"srcdocid:", "cals"),
    (0, b"PG ML", "pgx"),
    (0, b"\x1bP", "sixel"),
    (0, b"\x1bE\x1b", "pcl"),
    (0, b"\x08\xf2\xa6\xb6", "vips"),
    (4, b"\x00\x00\x00\x07\x00\x00\x00\x02", "xwd"),   # version 7 + ZPixmap
    # --- audio ---
    (0, b"fLaC", "flac"),
    (0, b"OggS", "ogg"),
    (0, b"ID3", "mp3"),
    (0, b"caff", "caf"),
    (0, b".snd", "au"),
    (0, b"wvpk", "wavpack"),
    (0, b"TTA1", "tta"),
    (0, b"MAC ", "ape"),
    (0, b"MPCK", "musepack"),
    (0, b"MP+", "musepack"),
    (0, b"Creative Voice File", "voc"),
    (0, b".SoX", "sox"),
    (0, b"\x64\xa3\x01\x00", "ircam"),
    (0, b"\x00\x01\x00\x00MThd", "midi"),
    (0, b"MThd", "midi"),
    (0, b"#!AMR", "amr"),
    (0, b"ALP ", "alp"),
    (0, b"STRM\x00", "ast"),
    (0, b"KVAG", "vag"),
    (0, b"FL32", "fl32"),
    (0, b"\x80\x00\x00\x20\x03", "adx"),
    (0, b"\x0b\x77", "ac3"),                           # ac3 y eac3 comparten sync
    # --- video y contenedores ---
    (0, b"\x1a\x45\xdf\xa3", "matroska"),
    (0, b"0&\xb2u\x8ef\xcf\x11", "asf"),
    (0, b"FLV\x01", "flv"),
    (0, b".RMF", "realmedia"),
    (0, b"\x06\x0e+4\x02\x05\x01\x01", "mxf"),
    (0, b"nut/multimedia", "nut"),
    (0, b"DKIF", "ivf"),
    (0, b"YUV4MPEG2", "y4m"),
    (0, b"\x12\x00\x0a", "av1obu"),                     # AV1 OBU: delimitador + secuencia
    # Marcadores textuales que van al principio de ficheros cuyo CUERPO es binario.
    # Tienen que estar aqui y no en MARCAS_TEXTO: la rama de texto solo se alcanza
    # si los 512 primeros bytes son imprimibles, y `y4m` fallaba justo por eso.
    (0, b"#EXTM3U", "m3u8"),
    (0, b"WEBVTT", "vtt"),
    (0, b"[Script Info]", "ass"),
    (0, b";FFMETADATA", "ffmetadata"),
    (0, b"/* XPM */", "xpm"),
    (0, b"#define ", "xbm"),
    (0, b"FWS", "swf"), (0, b"CWS", "swf"), (0, b"ZWS", "swf"),
    (0, b"BBCD", "dirac"),
    (0, b"\xb7\xd8\x00 7I\xda\x11", "wtv"),
    (0, b"FILM\x00\x00", "cpk"),
    (0, b"\x72\xf8\x1f\x4e", "spdif"),
    (40, b" EMF", "emf"),                               # EMF: el marcador va en el 40
    (0, b"\x00\x00\x01\xba", "mpegps"),                # mpeg, mpg, vob, dvd
    (0, b"\x00\x00\x01\xb3", "mpegvideo"),             # m1v, m2v
    # --- documento y empaquetado ---
    (0, b"%PDF-", "pdf"),
    (0, b"%!PS", "postscript"),
    (0, b"\xc5\xd0\xd3\xc6", "eps_binario"),           # EPS con previsualizacion DOS
    (0, b"{\\rtf", "rtf"),
    (0, b"\x1f\x8b", "gzip"),
    (0, b"BZh", "bzip2"),
    (0, b"\xfd7zXZ\x00", "xz"),
    (0, b"7z\xbc\xaf\x27\x1c", "7z"),
    (0, b"Rar!\x1a\x07", "rar"),
    (0, b"AT&TFORM", "djvu"),
    (0, b"ITOLITLS", "lit"),
    (0, b"SNBP000B", "snb"),
    (0, b"!!8-Bit!!", "tcr"),
    (0, b"L\x00R\x00F\x00", "lrf"),
    # --- 3D y varios ---
    (0, b"glTF", "glb"),
    (0, b"ply\n", "ply"),
    (0, b"ASSIMP.binary", "assbin"),
    (0, b"AssimpScene\x00", "stl_binario"),
    (0, b"Kaydara FBX Binary", "fbx"),
    (0, b"ISO-10303-21;", "step"),
    (0, b"xof ", "directx_x"),
    (0, b"Width: ", "brf"),                            # braille formateado
]

# Familia ISO-BMFF: se resuelve por el 'ftyp' de los bytes 4..8.
MARCAS_FTYP = {
    b"avif": "avif", b"avis": "avif", b"mif1": "heif", b"heic": "heif",
    b"heix": "heif", b"hevc": "heif", b"msf1": "heif",
    b"isom": "mp4", b"iso2": "mp4", b"iso4": "mp4", b"iso5": "mp4",
    b"iso6": "mp4", b"mp41": "mp4", b"mp42": "mp4", b"mp71": "mp4",
    b"dash": "mp4", b"avc1": "mp4", b"isml": "mp4", b"MSNV": "mp4",
    b"f4v ": "mp4", b"mmp4": "mp4", b"M4V ": "mp4", b"M4VH": "mp4",
    b"M4VP": "mp4", b"M4P ": "mp4", b"M4B ": "m4a", b"M4A ": "m4a",
    b"qt  ": "mov", b"3gp4": "3gp", b"3gp5": "3gp", b"3gp6": "3gp",
    b"3g2a": "3gp", b"3g2b": "3gp", b"3gr6": "3gp",
    b"jp2 ": "jpeg2000", b"jpx ": "jpeg2000", b"jpm ": "jpeg2000",
    b"mj2s": "mj2", b"crx ": "isobmff",
}

# Los contenedores ZIP y OLE no son un formato: son un envase. La segunda pasada
# lee el primer miembro (ODF/EPUB llevan `mimetype` sin comprimir en el byte 38)
# o los nombres de los miembros (OOXML). Solo se paga en ficheros que ya son ZIP.
MIME_ZIP = {
    b"application/epub+zip": "epub",
    b"application/vnd.oasis.opendocument.text": "odt",
    b"application/vnd.oasis.opendocument.spreadsheet": "ods",
    b"application/vnd.oasis.opendocument.presentation": "odp",
    b"application/vnd.oasis.opendocument.graphics": "odg",
    b"application/vnd.oasis.opendocument.text-template": "odt",
}
OOXML = ((b"word/", "docx"), (b"xl/", "xlsx"), (b"ppt/", "pptx"))


def _firma_zip(ruta: str, cab: bytes) -> str:
    """Desambigua un ZIP: epub / odt / ods / odp / docx / xlsx / pptx / zip."""
    if cab[30:38] == b"mimetype":
        resto = cab[38:38 + 80]
        for m, nombre in MIME_ZIP.items():
            if resto.startswith(m):
                return nombre
    try:
        import zipfile
        with zipfile.ZipFile(ruta) as z:
            nombres = z.namelist()[:400]
        for pref, nombre in OOXML:
            p = pref.decode()
            if any(n.startswith(p) for n in nombres):
                return nombre
        if "mimetype" in nombres:
            try:
                with zipfile.ZipFile(ruta) as z:
                    m = z.read("mimetype")[:80]
                for mm, nombre in MIME_ZIP.items():
                    if m.startswith(mm):
                        return nombre
            except Exception:
                pass
    except Exception:
        pass
    return "zip"


def _firma_cfb(ruta: str) -> str:
    """Contenedor OLE/CFB: doc / xls / ppt / msg. Sin leer el arbol: 'cfb'."""
    return "cfb"


# Marcadores que solo se reconocen en el TEXTO. Se prueban sobre los primeros
# bytes ya sin BOM ni blancos. Un marcador de texto que NO discrimina (todos los
# dialectos XML empiezan por `<?xml`) devuelve el nombre de la FAMILIA, no el del
# formato: decir "es XML" es verdad; decir "es SVG" sin mirar mas, no.
MARCAS_TEXTO = [
    (b"%!PS", "postscript"), (b"%PDF-", "pdf"), (b"{\\rtf", "rtf"),
    (b"#EXTM3U", "m3u8"), (b"WEBVTT", "vtt"), (b"[Script Info]", "ass"),
    (b"YUV4MPEG2", "y4m"), (b";FFMETADATA", "ffmetadata"),
    (b"/* XPM */", "xpm"), (b"/* UIL */", "uil"), (b"#define ", "xbm"),
    (b"# ImageMagick pixel enumeration", "im_texto"),
    (b"GIMP Palette", "gimp_paleta"), (b"#FIG ", "xfig"),
    (b"ply\n", "ply"), (b"solid ", "stl_ascii"),
    (b"#?RADIANCE", "radiance"), (b"ISO-10303-21;", "step"),
]


def _firma_texto(cab: bytes) -> str:
    """Refina 'texto' cuando hay un marcador textual estable."""
    s = cab
    if s[:3] == b"\xef\xbb\xbf":
        s = s[3:]
    s = s.lstrip(b" \t\r\n")
    for marca, nombre in MARCAS_TEXTO:
        if s.startswith(marca):
            return nombre
    bajo = s[:600].lower()
    if bajo.startswith(b"<?xml"):
        # el prologo XML no dice de que dialecto es: hay que mirar el elemento raiz
        if b"<svg" in bajo:
            return "svg"
        if b"<html" in bajo or b"<!doctype html" in bajo:
            return "html"
        return "xml"
    if bajo.startswith(b"<!doctype html") or bajo.startswith(b"<html"):
        return "html"
    if bajo.startswith(b"<svg"):
        return "svg"
    return "texto"


# Nombres de firma que son TEXTO por dentro: la sonda los trata como tales.
FAMILIA_TEXTO = {"texto", "xml", "html", "svg", "postscript", "rtf", "m3u8",
                 "vtt", "ass", "y4m", "ffmetadata", "xpm", "uil", "xbm",
                 "im_texto", "gimp_paleta", "xfig", "stl_ascii", "brf"}


def firma_real(ruta: str) -> str:
    """Formato real por bytes magicos. Ningun subproceso, ninguna extension."""
    try:
        with open(ruta, "rb") as fh:
            cab = fh.read(_NCAB)
    except OSError:
        return "ilegible"
    if not cab:
        return "vacio"
    # --- envases que comparten cabecera: hay que desambiguar el subtipo ---
    if cab[:4] == b"RIFF" and len(cab) >= 12:
        return {b"WEBP": "webp", b"WAVE": "wav", b"AVI ": "avi",
                b"RMID": "midi"}.get(cab[8:12], "riff")
    if cab[:4] == b"RF64":
        return "wav"
    if cab[:8] == b"riff\x2e\x91\xcf\x11":
        return "wave64"
    if cab[:4] == b"FORM" and len(cab) >= 12:
        return {b"AIFF": "aiff", b"AIFC": "aiff"}.get(cab[8:12], "iff")
    if len(cab) >= 12 and cab[4:8] == b"ftyp":
        return MARCAS_FTYP.get(cab[8:12], "isobmff")
    if cab[:2] == b"PK" and cab[2:4] in (b"\x03\x04", b"\x05\x06", b"\x07\x08"):
        return _firma_zip(ruta, cab)
    if cab[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return _firma_cfb(ruta)
    # --- PalmDB: el marcador NO esta al principio, esta en el byte 60. El titulo
    # que va delante es contenido (calibre escribe "Unknown") y NO es firma.
    if len(cab) >= 68 and cab[60:68] in (b"BOOKMOBI", b"TEXtREAd"):
        return "mobi"
    # --- tabla de magicos ---
    for desp, magico, nombre in FIRMAS:
        if cab[desp:desp + len(magico)] == magico:
            return nombre
    # --- casos con predicado, no con literal ---
    # PNM/PAM/PFM: familia P1..P7. El marcador es 'P' + digito/letra + blanco.
    if cab[:1] == b"P" and len(cab) >= 3:
        if cab[1:2] in b"123456" and cab[2:3] in b" \t\r\n":
            return "pnm"
        if cab[1:2] == b"7" and cab[2:3] in b" \t\r\n":
            return "pam"
        if cab[1:2] in b"FfHh" and cab[2:3] in b" \t\r\n":
            return "pfm"
    # PCX: 0x0A, version 0-5, codificacion 1, bits 1/2/4/8.
    if (len(cab) >= 4 and cab[0] == 0x0A and cab[1] in (0, 2, 3, 4, 5)
            and cab[2] == 1 and cab[3] in (1, 2, 4, 8)):
        return "pcx"
    # MPEG-TS: paquetes de 188 bytes que empiezan por 0x47. m2ts lleva 4 de cabecera.
    if len(cab) > 188 and cab[0] == 0x47 and cab[188] == 0x47:
        return "mpegts"
    if len(cab) > 196 and cab[4] == 0x47 and cab[196] == 0x47:
        return "m2ts"
    # Codigos de arranque de un flujo elemental (H.264/265/266, AVS, MPEG-4 part 2).
    # El marcador EXISTE y NO discrimina el codec: se devuelve la familia.
    if cab[:4] == b"\x00\x00\x00\x01" or cab[:3] == b"\x00\x00\x01":
        return "flujo_es"
    # Audio MPEG frente a ADTS: los dos empiezan por 0xFF 0xEx. Los bits de capa
    # (1-2) valen 00 en ADTS y nunca 00 en MPEG-1/2 audio.
    if len(cab) >= 2 and cab[0] == 0xFF and (cab[1] & 0xE0) == 0xE0:
        return "adts" if (cab[1] & 0x06) == 0 else "mpegaudio"
    # Texto: heuristica minima (sin bytes de control fuera de \t\r\n).
    if all(b >= 0x20 or b in (9, 10, 13) for b in cab):
        return _firma_texto(cab)
    return "desconocido"


# ===========================================================================
# QUE FIRMA REAL ES ACEPTABLE PARA CADA EXTENSION PEDIDA.
#
# Esta es la tabla que decide si el punto 1 dispara. Cada entrada nueva es
# capacidad de atrapar un fallo Y riesgo de fabricar un falso positivo, y por eso
# se ha construido con el censo delante: la firma aceptable de cada extension es
# la que produjeron los motores al escribirla, curada para NO aceptar lo que es
# precisamente el fallo que hay que atrapar (`magick x.png y.group4` entrega un
# PNG con rc=0: `.group4` acepta `tiff`, NO acepta `png`).
# ===========================================================================

def _ext(nombres, firmas):
    return {"." + n: set(firmas) for n in nombres.split()}


EXT_A_FIRMAS = {}
for _n, _f in (
    # ---------------- imagen de trama ----------------
    ("png png8 png00 png24 png32 png48 png64 apng", {"png"}),
    ("jpg jpeg jpe jfif pjpeg jps mjpeg mjpg jls ljpg", {"jpeg"}),
    ("jp2 j2k jpc j2c jpx jpm jpf mj2", {"jpeg2000", "mj2", "isobmff"}),
    ("jxl", {"jxl"}),
    ("gif gif87", {"gif"}),
    ("bmp bmp2 bmp3 dib", {"bmp"}),
    ("tif tiff ptif tif64", {"tiff", "bigtiff"}),
    ("tiff64 bigtiff", {"bigtiff", "tiff"}),
    ("webp", {"webp"}),
    ("avif", {"avif", "isobmff"}),
    ("heic heif hif", {"heif", "isobmff"}),
    ("psd psb", {"psd"}),
    ("sgi rgba64", {"sgi"}),
    ("ras sun sunras rs im1 im8 im24", {"sunras"}),
    ("emf", {"emf"}),
    ("xwd", {"xwd"}),
    ("cpk", {"cpk"}),
    ("spdif", {"spdif"}),
    ("dds dxt1 dxt5", {"dds"}),
    ("exr", {"exr"}),
    ("hdr", {"radiance"}),
    ("dpx", {"dpx"}),
    ("cin", {"cineon"}),
    ("pcx", {"pcx"}),
    ("dcx", {"dcx"}),
    ("ico", {"ico"}),
    ("cur icon", {"cur", "ico"}),
    ("qoi", {"qoi"}),
    ("farbfeld ff", {"farbfeld"}),
    ("miff mif ashlar", {"miff"}),
    ("mpc", {"mpc", "musepack"}),
    ("viff xv", {"viff"}),
    ("wpg", {"wpg"}),
    ("fits fts fit", {"fits"}),
    ("vicar", {"vicar"}),
    ("ipl", {"ipl"}),
    ("wmf", {"wmf"}),
    ("xcf", {"xcf"}),
    ("mat", {"mat"}),
    ("cal cals", {"cals"}),
    ("pgx", {"pgx"}),
    ("six sixel", {"sixel"}),
    ("pcl", {"pcl"}),
    ("jbig jbg bie", {"jbig"}),
    ("vips", {"vips"}),
    ("mng", {"mng"}),
    ("jng", {"jng"}),
    ("pbm pgm ppm pnm pgmyuv", {"pnm"}),
    ("pam", {"pam"}),
    ("pfm phm", {"pfm"}),
    ("xpm picon", {"xpm"}),
    ("xbm", {"xbm"}),
    ("uil", {"uil"}),
    ("brf ubrl ubrl6", {"brf"}),
    # ---------------- audio ----------------
    ("mp3 mp2 mpa m1a m2a", {"mp3", "mpegaudio"}),
    ("aac adts", {"adts"}),
    ("ac3 eac3 ec3", {"ac3"}),
    ("flac", {"flac"}),
    ("ogg oga ogv ogx opus spx", {"ogg"}),
    ("wav", {"wav"}),
    ("w64", {"wave64"}),
    ("aif aiff aifc afc", {"aiff"}),
    ("au snd", {"au"}),
    ("caf", {"caf"}),
    ("wv", {"wavpack"}),
    ("tta", {"tta"}),
    ("ape", {"ape"}),
    ("voc", {"voc"}),
    ("sox", {"sox"}),
    ("ircam sf", {"ircam"}),
    ("mid midi rmi", {"midi"}),
    ("amr", {"amr"}),
    ("adx", {"adx"}),
    ("ast", {"ast"}),
    ("vag", {"vag"}),
    ("fl32", {"fl32"}),
    ("m4a m4b", {"m4a", "mp4", "isobmff"}),
    # ---------------- video y contenedores ----------------
    ("mp4 m4v f4v psp ismv isma mp4v", {"mp4", "mov", "m4a", "isobmff"}),
    ("mov qt", {"mov", "mp4", "isobmff"}),
    ("3gp 3g2", {"3gp", "mp4", "isobmff"}),
    ("mkv mka mks", {"matroska"}),
    ("webm", {"matroska"}),
    ("avi", {"avi"}),
    ("asf wmv wma", {"asf"}),
    ("flv", {"flv"}),
    ("rm ra rmvb", {"realmedia"}),
    ("mxf", {"mxf"}),
    ("nut", {"nut"}),
    ("ivf", {"ivf"}),
    ("swf", {"swf"}),
    ("drc vc2", {"dirac"}),
    ("wtv", {"wtv"}),
    ("mpeg mpg vob dvd mpg2 m2p ps2", {"mpegps"}),
    ("m1v m2v mpv", {"mpegvideo", "flujo_es"}),
    ("ts m2t mts", {"mpegts"}),
    ("m2ts", {"m2ts", "mpegts"}),
    # El codigo de arranque de un flujo elemental EXISTE y NO discrimina el codec.
    # `obu` y `avs` se sacaron de aqui porque NO son Annex-B: los dos daban `fallo`
    # sobre una salida legitima en la validacion de _valida_tabla.py.
    ("264 h264 265 h265 hevc 266 h266 vvc av1 265m", {"flujo_es"}),
    ("obu", {"av1obu"}),
    ("y4m", {"y4m"}),
    ("m3u8", {"m3u8"}),
    ("ffmeta", {"ffmetadata"}),
    # ---------------- documento y empaquetado ----------------
    ("pdf pdfa epdf ai pdfpage", {"pdf"}),
    ("ps ps2 ps3 postscript", {"postscript"}),
    ("eps epsf epsi epi eps2 eps3 ept ept2 ept3", {"postscript", "eps_binario"}),
    ("rtf", {"rtf"}),
    ("gz tgz", {"gzip"}),
    ("bz2", {"bzip2"}),
    ("xz", {"xz"}),
    ("7z", {"7z"}),
    ("zip cbz jar 3mf htmlz txtz", {"zip", "docx", "xlsx", "pptx", "odt", "ods",
                                    "odp", "odg", "epub"}),
    ("epub epub2 epub3", {"epub", "zip"}),
    ("docx docm dotx dotm", {"docx", "zip"}),
    ("xlsx xlsm", {"xlsx", "zip"}),
    ("pptx pptm", {"pptx", "zip"}),
    ("odt ott fodt", {"odt", "zip", "xml"}),
    ("ods", {"ods", "zip"}),
    ("odp", {"odp", "zip"}),
    ("odg", {"odg", "zip"}),
    ("doc dot xls ppt wps wpt msg", {"cfb"}),
    ("djvu djv", {"djvu"}),
    ("mobi azw azw3 prc", {"mobi"}),
    ("lit", {"lit"}),
    ("snb", {"snb"}),
    ("tcr", {"tcr"}),
    ("lrf", {"lrf"}),
    ("svg rsvg msvg", {"svg", "xml"}),
    ("svgz", {"gzip"}),
    ("html htm xhtml html4 html5", {"html", "xml", "texto"}),
    ("xml ttml fb2 fxg collada dae xmp icml sif opml mpd assxml gimppath "
     "opendocument", {"xml", "svg", "html", "texto"}),
    ("vtt", {"vtt"}),
    ("ass ssa", {"ass"}),
    # ---------------- 3D ----------------
    ("glb glb2 gltf gltf2", {"glb", "texto"}),
    ("ply plyb", {"ply"}),
    ("assbin", {"assbin"}),
    ("stlb", {"stl_binario"}),
    ("fbx", {"fbx", "texto"}),
    ("stp step", {"step"}),
    ("x", {"directx_x"}),
    # ---------------- datos ----------------
    # Aqui el marcador es de FAMILIA, no de formato: "esto es texto" es
    # comprobable y "esto es CSV y no TSV" no lo es. Se declara como tal en
    # EXT_FAMILIA y se cuenta aparte, porque llamar a esto "punto 1 evaluado" sin
    # matiz seria inflar la cifra.
    ("csv json yaml yml toml srt lrc sub scc jss ipynb geojson csljson dxf",
     {"texto"}),
    ("txt text md markdown tab tsv", {"texto", "im_texto"}),
):
    EXT_A_FIRMAS.update(_ext(_n, _f))

# Extensiones cuya comprobacion es de FAMILIA (texto / XML), no de formato.
EXT_FAMILIA = set()
for _n in ("csv json yaml yml toml txt text md markdown tab tsv srt lrc sub scc "
           "jss xml html htm xhtml html4 html5 ttml fb2 fxg collada dae xmp icml "
           "sif opml gltf gltf2 fbx ipynb geojson csljson dxf mpd assxml gimppath "
           "opendocument"):
    EXT_FAMILIA.add("." + _n)

# ===========================================================================
# LOS FORMATOS QUE NO TIENEN MARCADOR — la tercera categoria.
#
# MEDIDO (bench/firmas-contrato.md sec.2): escritos 2-3 veces con contenidos
# distintos, no comparten NI UN BYTE en posicion fija. No es que no sepamos su
# firma: es que no existe. El punto 1 NO APLICA, y el verificador lo dice.
#
# Y esto no es una comodidad: es donde el contrato es MAS DEBIL. Releer un `.rgb`
# de este ImageMagick con `-depth 8` entrega la geometria exacta pedida y pixeles
# basura, y PASA los cuatro puntos (CLAUDE.md trampa 23). Los formatos sin firma
# son justo aquellos en los que el punto 1 no puede ayudar.
# ===========================================================================
EXT_SIN_FIRMA = {}
for _n, _mot in (
    ("rgb rgba rgbo bgr bgra bgro cmyk cmyka gray graya ycbcr ycbcra yuv uyvy "
     "pal map mono bayer bayera y k m c b g o r", "pixeles crudos sin cabecera"),
    ("g3 g4 fax group4", "datos CCITT crudos: la geometria va fuera del fichero"),
    ("sb ub sw uw s8 u8 s16le s16be u16le f32le al ul mulaw alaw pcm g722 "
     "sbc msbc dfpwm aud gsm latm loas", "muestras PCM crudas"),
    ("otb palm pix rgf hrz strimg mtv aai isobrl isobrl6", "cabecera sin constante"),
    ("avs",
     "la misma extension son TRES formatos: la imagen AVS X de ImageMagick "
     "(anchura y altura BE, sin marcador), el video Argonaut de ffmpeg y un guion "
     "de AviSynth. Ninguna firma puede decidir cual se pidio"),
    ("tga icb vda vst art wbmp",
     "TGA/WBMP no definen numero magico: los 12 primeros bytes son campos. TGA 2.0 "
     "lleva 'TRUEVISION-XFILE' al FINAL y es opcional"),
    ("docbook docbook4 docbook5 jats jats_archiving jats_articleauthoring "
     "jats_publishing tei mediawiki gfm commonmark commonmark_x latex context "
     "man ms muse markua djot jira typst haddock xwiki zimwiki dokuwiki plain "
     "rst org textile asciidoc asciidoctor asciidoc_legacy",
     "markup emitido en fragmento: MEDIDO con tres semillas, ni un byte estable"),
    ("txt text csv tsv tab md markdown markdown_strict markdown_mmd "
     "markdown_phpextra commonmark commonmark_x gfm rst org textile typst muse "
     "jira haddock xwiki zimwiki dokuwiki plain man ms me asciidoc asciidoctor "
     "asciidoc_legacy djot markua opml texinfo tex latex context beamer "
     "biblatex bibtex", "texto plano: no hay marcador de formato"),
):
    for _e in _n.split():
        EXT_SIN_FIRMA.setdefault("." + _e, _mot)
# Una extension no puede estar en las dos tablas: manda la que tiene firma.
for _e in list(EXT_SIN_FIRMA):
    if _e in EXT_A_FIRMAS:
        del EXT_SIN_FIRMA[_e]


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
                # QuickTime pone un SEGUNDO `hdlr` dentro de `minf` con el
                # manejador de DATOS ('url ', 'alis'). Quedarse con el ULTIMO
                # clasifica las tres pistas de un .mov como "otro" y el fichero
                # entero como "0 pistas". MP4 no trae el segundo; MOV si.
                # MEDIDO: bench/sondeo-ffmpeg.md 4.1.
                if estado.get("handler") is None:
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
        # El granulo de Opus SIEMPRE va a 48 kHz; el de Vorbis va a la
        # frecuencia del PROPIO FLUJO. Dividir siempre por 48000 deja un Vorbis
        # de 8,000 s a 44,1 kHz en 7,350 (x0,91875) y dispara A1/V1 fallo en 12
        # aristas. MEDIDO: bench/sondeo-ffmpeg.md 4.3.
        _base = p.get("sample_rate") if p.get("codec") == "vorbis" else 48000
        d["duracion_s"] = round(max(0, gran - preskip) / float(_base or 48000), 4)
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
        # FALLO DEL PROPIO VERIFICADOR, encontrado por F1 al reejecutar la muestra
        # de E1 y corregido aqui: `csv.reader` lanza `_csv.Error: field larger than
        # field limit (131072)` sobre una linea muy larga, y `_csv.Error` NO es
        # subclase de ValueError, asi que se escapaba del `except` de
        # sondear_en_proceso y TUMBABA EL PROCESO. Lo dispara una salida real: el
        # "TXT" de ImageMagick, que es la enumeracion de los pixeles.
        try:
            filas = list(csv.reader(io.StringIO(texto, newline="")))
        except csv.Error as e:
            d["error"] = "csv ilegible: %s" % e
            d["csv_n_filas"] = 0
            d["csv_cabecera"] = []
            d["filas_datos"] = 0
            return d
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


def _pixel_en_byte(octeto, valor, alfa, bd, por_byte, masc):
    """En un PNG de paleta de 1/2/4 bits un byte lleva VARIOS pixeles. Devuelve
    cual de ellos vale 'valor'.

    FALLO ATRAPADO POR EL FIXTURE `plano_4b_esquina.png`: la version anterior
    devolvia `car.index(v)`, que es el indice del BYTE, y lo publicaba como
    coordenada x del primer pixel transparente. Con 2 bits por pixel el error
    es de x4: el pixel (12,8) se reportaba como (3,8). La regla I3 usa esa
    coordenada para leer un pixel de la SALIDA con `magick`, asi que el error
    no era cosmetico: leia otro pixel. No lo vio nadie porque `alpha.png`, la
    unica entrada con alfa del corpus, es de 8 bits.
    """
    for k in range(por_byte):
        if alfa[(octeto >> (8 - bd * (k + 1))) & masc] == valor:
            return k
    return 0


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
            if ct in (0, 2):
                return dict(r, evaluable=False, alfa_min=None,
                            motivo="tRNS de color clave (ct=%d): exige comparar "
                                   "el valor de cada pixel, no hay canal alfa" % ct)
            if m["pos_idat"] is None:
                return dict(r, evaluable=False, alfa_min=None, motivo="sin IDAT")
            return _alfa_min_png_adam7(fh, m, r, exacto)
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
                        b_idx = car.index(v)
                        x = b_idx
                        if bd < 8:
                            x = b_idx * por_byte + _pixel_en_byte(
                                fila[b_idx], v, alfa, bd, por_byte, masc)
                        r["primer_transparente"] = (min(x, an - 1), y)
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


# ---- PNG entrelazado (Adam7) ----------------------------------------------
#
# Adam7 no cambia el filtrado: cambia la GEOMETRIA. El flujo IDAT lleva, una
# tras otra, siete sub-imagenes con su propio ancho, su propio alto y su propia
# fila "anterior" (que en la primera fila de CADA pasada vuelve a ser ceros).
# El carril del alfa se desfiltra igual que en el caso no entrelazado; lo unico
# que hay que llevar bien es de que pixel de la imagen real viene cada muestra.
# Aqui NO se usa el atajo del "patron de fila opaca": las imagenes entrelazadas
# son raras y pequenas, y una pasada de 1 pixel de ancho no lo amortiza.

_ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
          (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))   # (xini, yini, xpaso, ypaso)


def _alfa_min_png_adam7(fh, m, r, exacto):
    ct, bd = m["color"], m["prof"]
    an, al = m["ancho"], m["alto"]
    canales = bps = 0
    if ct == 3:
        alfa = [255] * 256
        for i, v in enumerate((m["trns"] or b"")[:256]):
            alfa[i] = v
        if min(alfa) == 255:
            return dict(r, tiene_alfa=False, via="cabecera (tRNS opaco)")
        por_byte = 8 // bd
        masc = (1 << bd) - 1
        if bd == 8:
            tabla = bytes(alfa)
        else:
            tabla = bytes(min(alfa[(v >> (8 - bd * (k + 1))) & masc]
                              for k in range(por_byte)) for v in range(256))
        tope = 255
    else:
        canales = 4 if ct == 6 else 2
        bps = bd // 8
        if bps not in (1, 2):
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="profundidad %d no valida para ct=%d" % (bd, ct))
        tope = (1 << (8 * bps)) - 1
    r["via"] = "Adam7, carril alfa"
    mn = tope

    do = zlib.decompressobj()
    buf = bytearray()
    gen = _png_bloques_idat(fh, m["pos_idat"])

    def rellenar(n):
        while len(buf) < n:
            try:
                bloque = next(gen)
            except StopIteration:
                try:
                    buf.extend(do.flush())
                except zlib.error:
                    pass
                return len(buf) >= n
            buf.extend(do.decompress(bloque))
        return True

    for xini, yini, xpaso, ypaso in _ADAM7:
        anp = (an - xini + xpaso - 1) // xpaso
        alp = (al - yini + ypaso - 1) // ypaso
        if anp <= 0 or alp <= 0:
            continue
        if ct == 3:
            tam = (anp * bd + 7) // 8
            sobra = tam * 8 - anp * bd
            previo = bytearray(tam)
        else:
            bpp = canales * bps
            desp = (canales - 1) * bps
            tam = anp * bpp
            previos = [bytearray(anp) for _ in range(bps)]
            rapido = True     # el atajo de fila opaca vale POR PASADA
        for y in range(alp):
            if not rellenar(tam + 1):
                return dict(r, evaluable=False, alfa_min=None,
                            motivo="IDAT incompleto en la pasada Adam7")
            filtro = buf[0]
            filt = bytes(buf[1:tam + 1])
            del buf[:tam + 1]
            r["filas_leidas"] += 1
            if filtro > 4:
                return dict(r, evaluable=False, alfa_min=None,
                            motivo="filtro PNG %r desconocido" % filtro)
            if ct == 3:
                fila = _desfiltrar_carril(filtro, filt, previo)
                previo = fila
                car = fila.translate(tabla)
                if sobra and bd < 8 and len(car):
                    ult = fila[-1]
                    valid = [alfa[(ult >> (8 - bd * (k + 1))) & masc]
                             for k in range(por_byte - sobra // bd)]
                    car = car[:-1] + bytes([min(valid)] if valid else [])
                v = min(car) if car else 255
                idx = car.index(v) if car else 0
                if bd < 8 and car:
                    idx = idx * por_byte + _pixel_en_byte(
                        fila[idx], v, alfa, bd, por_byte, masc)
            else:
                carriles = [filt[desp + k::bpp] for k in range(bps)]
                if rapido:
                    # Mismo atajo que en el PNG no entrelazado, aplicado a cada
                    # pasada por separado: la fila "anterior" de la primera fila
                    # de CADA pasada vuelve a ser ceros. Sin el, tipico_adam7
                    # (1920x1080 RGBA16 opaco) costaba 1 207 ms y perdia contra
                    # magick (413 ms).
                    b0, resto = _PATRON_OPACO[y == 0].get(filtro, (None, None))
                    if b0 is not None and all(
                            c[:1] == bytes([b0]) and c[1:] == _rep(resto, len(c) - 1)
                            for c in carriles):
                        continue
                    rapido = False
                    previos = [bytearray(_rep(0 if y == 0 else 255, anp))
                               for _ in range(bps)]
                rec = [_desfiltrar_carril(filtro, c, previos[k])
                       for k, c in enumerate(carriles)]
                previos = rec
                if bps == 1:
                    v = min(rec[0]) if rec[0] else 255
                    idx = rec[0].index(v) if rec[0] else 0
                else:
                    hi, lo = rec[0], rec[1]
                    mh = min(hi) if hi else 255
                    if mh == 255:
                        v = 65280 + (min(lo) if lo else 255)
                        idx = lo.index(min(lo)) if lo else 0
                    else:
                        v, idx = 65535, 0
                        for j in range(len(hi)):
                            if hi[j] == mh:
                                w = (hi[j] << 8) | lo[j]
                                if w < v:
                                    v, idx = w, j
            if v < mn:
                mn = v
                if r["primer_transparente"] is None:
                    r["primer_transparente"] = (min(xini + idx * xpaso, an - 1),
                                                yini + y * ypaso)
            if mn == 0 or (mn < tope and not exacto):
                break
        if mn == 0 or (mn < tope and not exacto):
            break
    r["alfa_min"] = mn / float(tope)
    r["exacto"] = exacto or mn in (0, tope)
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


# ===========================================================================
# LZW — DOS DIALECTOS, uno por formato. No son intercambiables.
# ===========================================================================
#
# TIFF empaqueta los bits MSB primero y sube el ancho de codigo UN codigo ANTES
# de agotarlo ("early change", TIFF6 seccion 13). GIF empaqueta LSB primero y
# sube el ancho justo al agotarlo. Usar uno por el otro no da error: da bytes
# plausibles y equivocados, que es la peor clase de fallo para un verificador.

def _lzw_tiff(datos: bytes, tope: int | None = None) -> bytearray:
    """LZW de TIFF: MSB primero, ancho 9->12, con early change."""
    out = bytearray()
    dic = [bytes([i]) for i in range(256)]
    dic.append(b"")          # 256 = ClearCode
    dic.append(b"")          # 257 = EndOfInformation
    prox, ancho, prev = 258, 9, None
    acc = nbits = 0
    for b in datos:
        acc = ((acc << 8) | b) & 0xFFFFFFFF
        nbits += 8
        while nbits >= ancho:
            nbits -= ancho
            cod = (acc >> nbits) & ((1 << ancho) - 1)
            if cod == 257:
                return out
            if cod == 256:
                del dic[258:]
                prox, ancho, prev = 258, 9, None
                continue
            if cod < prox:
                ent = dic[cod]
            elif prev is not None:
                ent = prev + prev[:1]
            else:
                return out                      # flujo corrupto: se corta
            if prev is not None:
                dic.append(prev + ent[:1])
                prox += 1
                # early change: el ancho sube cuando el PROXIMO codigo libre
                # llega a 2^ancho - 1, no a 2^ancho.
                if prox + 1 >= (1 << ancho) and ancho < 12:
                    ancho += 1
            out += ent
            prev = ent
            if tope is not None and len(out) >= tope:
                return out
    return out


def _lzw_gif_usa(datos: bytes, mcs: int, objetivo: int, tope: int) -> bool:
    """LZW de GIF: LSB primero, sin early change. Devuelve True EN CUANTO
    aparece el indice 'objetivo'; no decodifica el resto. Ese corte temprano es
    lo que hace barato el caso que importa (el GIF que SI tiene transparencia).
    """
    limpio = 1 << mcs
    fin = limpio + 1
    base = [bytes([i]) for i in range(limpio)]
    dic = base + [b"", b""]
    prox, ancho, prev = fin + 1, mcs + 1, None
    acc = nbits = leidos = 0
    for b in datos:
        acc |= b << nbits
        nbits += 8
        while nbits >= ancho:
            cod = acc & ((1 << ancho) - 1)
            acc >>= ancho
            nbits -= ancho
            if cod == fin:
                return False
            if cod == limpio:
                del dic[fin + 1:]
                prox, ancho, prev = fin + 1, mcs + 1, None
                continue
            if cod < prox:
                ent = dic[cod]
            elif prev is not None:
                ent = prev + prev[:1]
            else:
                return False
            if prev is not None and prox < 4096:
                dic.append(prev + ent[:1])
                prox += 1
                if prox >= (1 << ancho) and ancho < 12:
                    ancho += 1
            if objetivo in ent:
                return True
            prev = ent
            leidos += len(ent)
            if leidos >= tope:
                return False
    return False


def _packbits(datos: bytes, n: int) -> bytearray:
    """Descompresion PackBits (TIFF compresion 32773)."""
    out = bytearray()
    i, ln = 0, len(datos)
    while i < ln and len(out) < n:
        h = datos[i]
        i += 1
        if h < 128:
            out += datos[i:i + h + 1]
            i += h + 1
        elif h > 128:
            if i < ln:
                out += bytes([datos[i]]) * (257 - h)
            i += 1
    return out


# ===========================================================================
# min(alfa) en TIFF COMPRIMIDO — bandas + predictor, solo el carril del alfa
# ===========================================================================
#
# Como en PNG, no hace falta reconstruir la imagen: el predictor horizontal
# (Predictor=2) opera POR MUESTRA con zancada SamplesPerPixel, asi que el
# carril del alfa se des-predice solo, exactamente igual que los filtros de
# PNG. Lo que NO se puede evitar es descomprimir la banda entera: LZW y
# Deflate son secuenciales y el alfa esta entrelazado con el color.

_TIFF_ETIQ_ALFA = (256, 257, 258, 259, 262, 273, 277, 278, 279, 284, 317,
                   322, 323, 338, 339)
_TIFF_COMPR_OK = {1: "sin comprimir", 5: "LZW", 8: "Deflate", 32946: "Deflate",
                  32773: "PackBits"}


def _tiff_ifd0(fh) -> dict:
    """Todas las etiquetas de la PRIMERA IFD que necesita el carril alfa, con
    los arrays COMPLETOS (StripOffsets puede tener cientos de entradas; el
    lector del sondeo los trunca a 8 a proposito, porque no los necesita)."""
    fh.seek(0)
    cab = fh.read(8)
    be = cab[:2] == b"MM"
    e = ">" if be else "<"
    desp = struct.unpack_from(e + "I", cab, 4)[0]
    fh.seek(desp)
    n = struct.unpack_from(e + "H", fh.read(2), 0)[0]
    entradas = fh.read(12 * n)
    campos = {"_be": be}
    for i in range(n):
        o = 12 * i
        etiq, tipo, cnt = struct.unpack_from(e + "HHI", entradas, o)
        if etiq not in _TIFF_ETIQ_ALFA:
            continue
        tam = _TIFF_TIPOS.get(tipo, 1) * cnt
        if tam <= 4:
            bruto = entradas[o + 8:o + 12]
        else:
            pos = struct.unpack_from(e + "I", entradas, o + 8)[0]
            aqui = fh.tell()
            fh.seek(pos)
            bruto = fh.read(tam)
            fh.seek(aqui)
        if tipo == 3:
            campos[etiq] = list(struct.unpack_from(e + "%dH" % cnt, bruto, 0))
        elif tipo == 4:
            campos[etiq] = list(struct.unpack_from(e + "%dI" % cnt, bruto, 0))
        elif tipo in (1, 6, 7):
            campos[etiq] = list(bruto[:cnt])
    return campos


def _tiff_descomprimir(datos: bytes, compr: int, esperado: int) -> bytearray:
    if compr == 1:
        return bytearray(datos[:esperado])
    if compr == 5:
        return _lzw_tiff(datos, esperado)
    if compr in (8, 32946):
        return bytearray(zlib.decompress(datos)[:esperado])
    if compr == 32773:
        return _packbits(datos, esperado)
    raise ValueError("compresion TIFF %d no soportada" % compr)


def _tiff_min_fila_8(carril: bytearray, pred: int) -> int:
    if pred == 2:
        carril = _desfiltrar_carril(1, carril, None)   # Sub == diferencia horiz.
    return min(carril) if carril else 255


def _tiff_min_fila_16(hi: bytearray, lo: bytearray, pred: int) -> int:
    """Devuelve el minimo de los valores de 16 bits del carril alfa."""
    if pred == 2:
        acc = 0
        vals = []
        for k in range(len(hi)):
            acc = (acc + ((hi[k] << 8) | lo[k])) & 0xFFFF
            vals.append(acc)
        return min(vals) if vals else 65535
    mh = min(hi) if hi else 255
    if mh == 255:
        return 65280 + (min(lo) if lo else 255)
    return min(((hi[k] << 8) | lo[k]) for k in range(len(hi)) if hi[k] == mh)


def _alfa_min_tiff(ruta: str, exacto: bool = False) -> dict:
    """TIFF: ExtraSamples dice si hay alfa; el valor minimo exige descomprimir
    las bandas (LZW / Deflate / PackBits) y deshacer el predictor. Cubre
    chunky y planar, 8 y 16 bits, y corta en la primera banda con alfa real."""
    r = {"formato": "tiff", "evaluable": True, "exacto": True,
         "tiene_alfa": False, "alfa_min": 1.0, "primer_transparente": None,
         "filas_leidas": 0, "via": "ExtraSamples/SamplesPerPixel"}
    with open(ruta, "rb") as fh:
        c = _tiff_ifd0(fh)
        be = c["_be"]
        spp = c.get(277, [1])[0]
        if not (c.get(338) or spp in (2, 4)):
            return r                       # sin alfa: solo se leyo la cabecera
        r["tiene_alfa"] = True
        if 322 in c or 323 in c:
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="TIFF en teselas (TileWidth/TileLength): no "
                               "implementado")
        compr = c.get(259, [1])[0]
        if compr not in _TIFF_COMPR_OK:
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="compresion TIFF %d (JPEG/JBIG/otra): exigiria "
                               "un decodificador propio" % compr)
        if c.get(339, [1])[0] not in (1, 2):
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="SampleFormat %d (coma flotante): no implementado"
                               % c.get(339, [1])[0])
        bps_l = c.get(258, [8])
        bps = bps_l[-1] if bps_l else 8
        if bps not in (8, 16):
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="BitsPerSample %d en la muestra alfa: no "
                               "implementado" % bps)
        pred = c.get(317, [1])[0]
        if pred not in (1, 2):
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="Predictor %d (coma flotante): no implementado"
                               % pred)
        an, al = c.get(256, [0])[0], c.get(257, [0])[0]
        offs, cnts = c.get(273, []), c.get(279, [])
        if not an or not al or not offs or len(offs) != len(cnts):
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="bandas TIFF ilegibles (StripOffsets/ByteCounts)")
        rps = c.get(278, [al])[0] or al
        plan = c.get(284, [1])[0]
        nb = (al + rps - 1) // rps
        ancho_m = bps // 8
        tope = (1 << bps) - 1
        mn = tope
        r["via"] = "banda %s%s, carril alfa" % (
            _TIFF_COMPR_OK[compr], " + predictor 2" if pred == 2 else "")

        if plan == 2:
            # Planar: el plano del alfa esta ENTERO en sus propias bandas. Es
            # el caso barato: no hay que separar carriles.
            if len(offs) < nb * spp:
                return dict(r, evaluable=False, alfa_min=None,
                            motivo="PlanarConfig=2 con %d bandas para %d planos"
                                   % (len(offs), spp))
            rango = range((spp - 1) * nb, spp * nb)
            paso, desp0, por_fila = ancho_m, 0, an * ancho_m
        elif plan == 1:
            rango = range(nb)
            paso, desp0, por_fila = spp * ancho_m, (spp - 1) * ancho_m, an * spp * ancho_m
        else:
            return dict(r, evaluable=False, alfa_min=None,
                        motivo="PlanarConfiguration %d desconocida" % plan)

        # ATAJO DE FILA OPACA, el mismo que hace barato el PNG (§1.1b del
        # informe anterior) trasladado al TIFF. Una fila 100 % opaca tiene una
        # forma FIJA en el carril alfa ya descomprimido:
        #   Predictor 1: todas las muestras valen el maximo -> todo 0xFF.
        #   Predictor 2: la primera vale el maximo y el resto son deltas 0
        #                -> 0xFF... y luego 0x00.
        # Es exacto, no heuristico, y son dos comparaciones de bytes en C en
        # vez de un bucle de Python por pixel. Sin el, el peor caso (1920x1080
        # RGBA16 opaco) cuesta 479 ms y PIERDE contra magick (336 ms).
        if pred == 1:
            op_a = op_b = _rep(255, an)
        else:
            op_a = op_b = b"\xff" + bytes(an - 1)

        y0 = 0
        for k in rango:
            fh.seek(offs[k])
            crudo = fh.read(cnts[k])
            filas_banda = min(rps, al - y0)
            try:
                banda = _tiff_descomprimir(crudo, compr, por_fila * filas_banda)
            except (zlib.error, ValueError, IndexError) as e:
                return dict(r, evaluable=False, alfa_min=None,
                            motivo="banda %d ilegible: %s: %s"
                                   % (k, type(e).__name__, e))
            for fy in range(filas_banda):
                o = fy * por_fila + desp0
                fin = o + an * paso
                r["filas_leidas"] += 1
                if bps == 8:
                    carril = banda[o:fin:paso]
                    if carril == op_a:
                        continue                  # fila opaca, demostrado
                    v = _tiff_min_fila_8(bytearray(carril), pred)
                else:
                    b1 = banda[o:fin:paso]
                    b2 = banda[o + 1:fin:paso]
                    if b1 == op_a and b2 == op_b:
                        continue                  # fila opaca, demostrado
                    hi, lo = (bytearray(b1), bytearray(b2)) if be \
                        else (bytearray(b2), bytearray(b1))
                    v = _tiff_min_fila_16(hi, lo, pred)
                if v < mn:
                    mn = v
                    if r["primer_transparente"] is None:
                        r["primer_transparente"] = (0, y0 + fy)
                if mn == 0 or (mn < tope and not exacto):
                    break
            y0 += filas_banda
            if mn == 0 or (mn < tope and not exacto):
                break
        r["alfa_min"] = mn / float(tope)
        r["exacto"] = exacto or mn in (0, tope)
        return r


# ===========================================================================
# min(alfa) en GIF — descomprimir el LZW del PRIMER fotograma
# ===========================================================================
#
# El GCE DECLARA un indice transparente; que se USE es otra cosa. La version
# anterior devolvia "no evaluable" con esa cota. Ahora se descomprime el LZW y
# se responde. Dos cautelas, ambas medidas y declaradas:
#
#   * el barrido de bloques es REAL, no un `find(b"\x21\xf9\x04")`: esa
#     secuencia aparece por casualidad dentro de los datos LZW;
#   * en un GIF ANIMADO los fotogramas 2..n usan el indice transparente como
#     CODIFICACION DIFERENCIAL ("no toques este pixel"), no como transparencia
#     visible. Por eso se evalua el fotograma 1, que es la imagen que se ve, y
#     se anota que los demas pueden declararla sin mostrarla.

def _gif_bloques(datos: bytes):
    """Itera (tipo, info) sobre los bloques de un GIF. tipo: 'gce' o 'img'."""
    if len(datos) < 13 or datos[:3] != b"GIF":
        return
    i = 13
    if datos[10] & 0x80:
        i += 3 * (2 ** ((datos[10] & 0x07) + 1))
    ln = len(datos)
    while i < ln:
        b = datos[i]
        if b == 0x3B:                                  # trailer
            return
        if b == 0x21:                                  # extension
            etiq = datos[i + 1]
            i += 2
            sub = []
            while i < ln and datos[i]:
                sub.append(datos[i + 1:i + 1 + datos[i]])
                i += 1 + datos[i]
            i += 1
            if etiq == 0xF9 and sub and len(sub[0]) >= 4:
                yield "gce", {"transparente": sub[0][0] & 0x01,
                              "indice": sub[0][3]}
        elif b == 0x2C:                                # descriptor de imagen
            izq, arr, ai, al_ = struct.unpack_from("<HHHH", datos, i + 1)
            banderas = datos[i + 9]
            i += 10
            n_local = 2 ** ((banderas & 0x07) + 1) if banderas & 0x80 else 0
            i += 3 * n_local
            mcs = datos[i]
            i += 1
            trozos = []
            while i < ln and datos[i]:
                trozos.append(datos[i + 1:i + 1 + datos[i]])
                i += 1 + datos[i]
            i += 1
            yield "img", {"izq": izq, "arr": arr, "ancho": ai, "alto": al_,
                          "mcs": mcs, "datos": b"".join(trozos),
                          "local": n_local}
        else:
            return                                     # byte inesperado


def _alfa_min_gif(ruta: str, exacto: bool = False) -> dict:
    with open(ruta, "rb") as fh:
        datos = fh.read()
    r = {"formato": "gif", "evaluable": True, "exacto": True,
         "tiene_alfa": False, "alfa_min": 1.0, "primer_transparente": None,
         "via": "bloque de control grafico"}
    if len(datos) < 13 or datos[:3] != b"GIF":
        return dict(r, evaluable=False, alfa_min=None, tiene_alfa=None,
                    motivo="no es un GIF")
    lan, lal = struct.unpack_from("<HH", datos, 6)
    gce = None
    n_img = 0
    declara_despues = False
    for tipo, info in _gif_bloques(datos):
        if tipo == "gce":
            gce = info
            if n_img >= 1 and info["transparente"]:
                declara_despues = True
            continue
        n_img += 1
        if n_img > 1:
            continue                                   # solo el fotograma 1
        r["n_imagenes_min"] = 1
        if not (gce and gce["transparente"]):
            # El fotograma 1 no declara indice transparente. Si ademas no cubre
            # el lienzo, el borde queda sin pintar: eso SI es transparencia.
            if info["ancho"] < lan or info["alto"] < lal:
                r.update({"tiene_alfa": True, "alfa_min": 0.0,
                          "primer_transparente": (0, 0), "exacto": True,
                          "via": "el fotograma 1 (%dx%d) no cubre el lienzo "
                                 "(%dx%d)" % (info["ancho"], info["alto"], lan, lal)})
                return r
            continue
        r["tiene_alfa"] = True
        r["via"] = "LZW del fotograma 1 (indice transparente %d)" % gce["indice"]
        tope_px = max(1, info["ancho"] * info["alto"])
        try:
            usa = _lzw_gif_usa(info["datos"], info["mcs"], gce["indice"], tope_px)
        except (IndexError, ValueError) as e:
            return dict(r, evaluable=False, alfa_min=None, cota_alfa_min=0.0,
                        motivo="LZW del fotograma 1 ilegible: %s: %s"
                               % (type(e).__name__, e))
        if usa:
            r.update({"alfa_min": 0.0, "primer_transparente": (0, 0)})
            return r
        if info["ancho"] < lan or info["alto"] < lal:
            r.update({"alfa_min": 0.0, "primer_transparente": (0, 0),
                      "via": r["via"] + "; ademas no cubre el lienzo"})
            return r
        # declarado y NO usado: opaco de verdad
        r["tiene_alfa"] = False
        r["alfa_min"] = 1.0
    if declara_despues:
        r["nota"] = ("GIF animado: algun fotograma posterior declara indice "
                     "transparente, pero en GIF eso es codificacion diferencial "
                     "(no repintar el pixel), no transparencia visible; se "
                     "evalua el fotograma 1, que es la imagen que se ve")
    if n_img == 0:
        return dict(r, evaluable=False, alfa_min=None,
                    motivo="GIF sin bloques de imagen")
    return r


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
            r = _alfa_min_gif(ruta, exacto)
        elif firma in ("avif", "heif"):
            r = {"formato": firma, "evaluable": False, "alfa_min": None,
                 "exacto": False, "tiene_alfa": None, "primer_transparente": None,
                 "motivo": "AVIF/HEIF: el plano alfa es un flujo AV1/HEVC; "
                           "exige un decodificador de video completo"}
        elif firma == "tiff":
            r = _alfa_min_tiff(ruta, exacto)
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
        # Los formatos de texto CON marcador propio (xml, html, svg, postscript,
        # rtf...) NO son datos tabulares: pasarlos por _datos es lo que hacia que
        # un .html se clasificara como CSV y disparara `D2 numero de campos no
        # constante` (bench/contrato-quinto-punto.md sec.3.1: "un falso positivo
        # que acierta por casualidad"). Ahora se separan.
        if firma == "texto" or firma == "im_texto":
            base.update(_datos(ruta))
            return base
        if firma in FAMILIA_TEXTO:
            base.update({"categoria": "documento", "subtipo": firma})
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
            elif firma in ("avif", "heif", "mp4", "m4a", "mov", "isobmff", "3gp",
                           "mj2"):
                base.update(_isobmff(fh, ruta))
            elif firma == "matroska":
                base.update(_matroska(fh, ruta))
            elif firma == "ogg":
                base.update(_ogg(fh, ruta))
            elif firma == "wav":
                base.update(_wav(fh, ruta))
            elif firma == "flac":
                base.update(_flac(fh, ruta))
            elif firma in ("mp3", "mpegaudio"):
                base.update(_mp3(fh, ruta))
            elif firma == "pdf":
                base.update(_pdf(fh, ruta))
            else:
                base["categoria"] = "desconocida"
    except (OSError, struct.error, IndexError, ValueError, csv.Error) as e:
        # csv.Error se anadio despues de que tumbara el proceso sobre un .txt de
        # 156 MB escrito por ImageMagick: NO es subclase de ValueError.
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
    # --- nombres nuevos del vocabulario ampliado (F1) ---
    "bigtiff": "imagen", "jpeg2000": "imagen", "jxl": "imagen", "psd": "imagen",
    "sgi": "imagen", "sunras": "imagen", "dds": "imagen", "exr": "imagen",
    "radiance": "imagen", "dpx": "imagen", "cineon": "imagen", "pcx": "imagen",
    "dcx": "imagen", "ico": "imagen", "cur": "imagen", "qoi": "imagen",
    "farbfeld": "imagen", "miff": "imagen", "mpc": "imagen", "viff": "imagen",
    "wpg": "imagen", "fits": "imagen", "vicar": "imagen", "ipl": "imagen",
    "wmf": "imagen", "xcf": "imagen", "mat": "imagen", "cals": "imagen",
    "pgx": "imagen", "sixel": "imagen", "jbig": "imagen", "vips": "imagen",
    "mng": "imagen", "jng": "imagen", "pnm": "imagen", "pam": "imagen",
    "pfm": "imagen", "xpm": "imagen", "xbm": "imagen",
    "mpegaudio": "av", "adts": "av", "ac3": "av", "wave64": "av", "aiff": "av",
    "au": "av", "caf": "av", "wavpack": "av", "tta": "av", "ape": "av",
    "musepack": "av", "voc": "av", "sox": "av", "ircam": "av", "midi": "av",
    "amr": "av", "adx": "av", "ast": "av", "vag": "av", "fl32": "av",
    "avi": "av", "asf": "av", "flv": "av", "realmedia": "av", "mxf": "av",
    "nut": "av", "ivf": "av", "swf": "av", "dirac": "av", "wtv": "av",
    "mpegps": "av", "mpegvideo": "av", "mpegts": "av", "m2ts": "av",
    "flujo_es": "av", "y4m": "av", "3gp": "av", "mj2": "av", "iff": "av",
    "postscript": "documento", "rtf": "documento", "xml": "documento",
    "html": "documento", "svg": "documento", "djvu": "documento",
    "mobi": "documento", "lit": "documento", "snb": "documento",
    "tcr": "documento", "lrf": "documento", "epub": "documento",
    "docx": "documento", "xlsx": "documento", "pptx": "documento",
    "odt": "documento", "ods": "documento", "odp": "documento",
    "odg": "documento", "cfb": "documento", "eps_binario": "documento",
    "im_texto": "datos", "m3u8": "datos", "vtt": "datos", "ass": "datos",
    "ffmetadata": "datos", "brf": "datos", "uil": "datos",
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


FIRMAS_INDEFINIDAS = {"desconocido", "vacio", "ilegible", "texto", "riff",
                      "isobmff", "zip", "cfb", "flujo_es"}


def punto1_firma(salida: str, sonda: dict, pedido: dict,
                 sonda_ent: dict | None = None) -> list:
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
    # TRES respuestas, no dos (F1, bench/firmas-contrato.md):
    #  - la extension esta en la tabla  -> se evalua;
    #  - el formato NO TIENE marcador   -> NO APLICA, y se dice asi;
    #  - no esta en ninguna de las dos  -> deuda de vocabulario, y se dice asi.
    # Confundir la segunda con la tercera es lo que hacia que el verificador
    # declarara `1_firma: True` en el 100 % de los ficheros evaluando el 12 %.
    aceptables = EXT_A_FIRMAS.get(ext)
    if aceptables is None:
        motivo = EXT_SIN_FIRMA.get(ext)
        if motivo:
            h.append(_hallazgo(1, "G4", "informativo",
                               "el formato no tiene marcador (%s): el punto 1 NO "
                               "APLICA a %s" % (motivo, ext), None, firma))
        else:
            h.append(_hallazgo(1, "G3", "informativo",
                               "extension sin firma conocida: %s" % ext, None, firma))
    elif firma not in aceptables:
        h.append(_hallazgo(1, "G3", "fallo",
                           "la firma real no corresponde a la extension pedida",
                           "|".join(sorted(aceptables)), firma))
    elif ext in EXT_FAMILIA:
        h.append(_hallazgo(1, "G5", "informativo",
                           "marcador de FAMILIA, no de formato: se comprueba que "
                           "es %s, no que sea %s" % ("|".join(sorted(aceptables)), ext),
                           None, firma))
    # --- G6: LA SALIDA ES DEL MISMO FORMATO QUE LA ENTRADA ---------------------
    # Sale de una medida, no de la especificacion (bench/firmas-contrato.md sec.5):
    # `magick x.png y.group4` devuelve rc=0 y entrega UN PNG, y lo mismo con otros
    # 21 destinos. Cuando la extension no le dice nada al motor, el motor NO falla:
    # conserva el formato de la entrada. Es el fallo emblematico del proyecto — un
    # PNG con la extension equivocada y estado "Done" — con un motor de verdad.
    #
    # Ni el vocabulario viejo ni el nuevo lo atrapan por firma, porque para atrapar
    # `.group4` haria falta saber que firma esperar y `.group4` no es un formato con
    # marcador. Pero NO HACE FALTA saberlo: basta ver que la salida tiene la MISMA
    # firma que la entrada y que no era eso lo que se pedia. Cuesta 0 (las dos
    # firmas ya estan calculadas) y es `aviso`, no `fallo`: prueba que es
    # sospechoso, no que sea incorrecto.
    if (aceptables is None and sonda_ent is not None
            and firma and firma not in FIRMAS_INDEFINIDAS
            and sonda_ent.get("firma") == firma):
        ext_ent = os.path.splitext(sonda_ent.get("ruta") or "")[1].lower()
        if ext_ent != ext:
            h.append(_hallazgo(1, "G6", "aviso",
                               "la salida tiene la MISMA firma que la entrada (%s) y "
                               "se pidio %s: el motor no reconocio la extension y "
                               "conservo el formato de origen" % (firma, ext),
                               "!= %s" % firma, firma))
    return h


def punto1_estado(salida: str) -> str:
    """'evaluado' | 'familia' | 'no_aplica' | 'sin_vocabulario'.

    Es la respuesta a la pregunta que E1 dejo abierta: de los destinos reales,
    ¿en cuantos se puede evaluar el punto 1 del contrato? Se publica aparte del
    veredicto porque la cobertura y el veredicto son cosas distintas.
    """
    ext = os.path.splitext(salida)[1].lower()
    if ext in EXT_A_FIRMAS:
        return "familia" if ext in EXT_FAMILIA else "evaluado"
    if ext in EXT_SIN_FIRMA:
        return "no_aplica"
    return "sin_vocabulario"


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


# ===========================================================================
# PUNTO 5 — ¿ESCRIBIO EL MOTOR FUERA DE LO DECLARADO?
#
# Origen: bench/aristas-nominales.md §5.2 y §9.7. Dos casos REPRODUCIDOS:
#   - `ffmpeg -i x DEST/t.mpd` deja init-stream0.m4s y chunk-stream0-00001.m4s
#     (528 KB) en el DIRECTORIO DE TRABAJO y entrega un .mpd de 1 234 B inutil.
#   - `magick x DEST/u.html` escribe DOS ficheros en el destino (u.html + u.png)
#     y un TERCERO (u_map.shtml) en el directorio de trabajo.
# Los dos pasan los cuatro puntos del contrato: firma correcta, flujos
# correctos, propiedades correctas, pedido = obtenido.
#
# El punto 5 NO se puede evaluar a posteriori sobre un fichero que ya existe:
# la informacion (que habia antes en el directorio) ya no esta. Por eso su
# cobertura es false si no se le pasa un censo, y por eso la regla R18
# —directorio de trabajo propio y DESECHABLE por conversion— no es una
# comodidad: es la condicion que hace el punto 5 barato y exacto.
# ===========================================================================

# Destinos en los que entregar VARIOS ficheros es el comportamiento correcto
# del formato, no un fallo del motor. La clave es la extension PEDIDA.
DESTINOS_MULTIFICHERO = {
    "mpd": "manifiesto DASH: los segmentos son ficheros aparte",
    "m3u8": "lista HLS: los segmentos son ficheros aparte",
    "html": "magick escribe el HTML y el PNG al que apunta",
    "shtml": "mapa de imagen servido aparte",
    "ismv": "Smooth Streaming: fragmentos aparte",
    "vtt": "subtitulos segmentados",
}
# Sufijos que acompañan legitimamente a una salida multifichero.
_SATELITES = (".m4s", ".ts", ".png", ".jpg", ".jpeg", ".shtml", ".map",
              ".vtt", ".m3u8", ".mpd", ".webvtt")


def censar_dir(directorio: str) -> dict:
    """Censo de un directorio: {nombre: tamaño}. Un solo scandir, sin recursion.

    Es la implementacion cara del punto 5 (hay que llamarlo ANTES y DESPUES).
    Con R18 el directorio esta vacio antes y basta el censo de DESPUES.
    """
    d = {}
    try:
        with os.scandir(directorio) as it:
            for e in it:
                try:
                    d[e.name] = e.stat(follow_symlinks=False).st_size if e.is_file() else -1
                except OSError:
                    d[e.name] = -1
    except OSError:
        return {}
    return d


def censar(directorios) -> dict:
    """Censo de varios directorios de una vez. Devuelve {ruta_abs: censo}."""
    return {os.path.abspath(d): censar_dir(d) for d in directorios}


def mtime_dir(directorio: str) -> int:
    """Alternativa barata: un solo stat. Detecta QUE cambio algo, no QUE
    cambio. En NTFS el mtime del directorio se actualiza al crear o borrar una
    entrada; NO se actualiza si solo cambia el CONTENIDO de un fichero ya
    existente. Sirve como disparador, no como censo."""
    try:
        return os.stat(directorio).st_mtime_ns
    except OSError:
        return -1


def punto5_escritura(salida: str, pedido: dict, censo: dict | None) -> list:
    """¿Escribio el motor algo que no declaro?

    `censo` es {"antes": {dir: {nombre: tam}}, "despues": {...},
                "trabajo": dir_de_trabajo_del_motor (opcional)}.
    Con R18, "antes" puede ser {} para el directorio desechable.
    """
    if not censo:
        return []
    h = []
    antes = censo.get("antes") or {}
    despues = censo.get("despues") or {}
    sal_abs = os.path.abspath(salida)
    dir_destino = os.path.dirname(sal_abs)
    base = os.path.basename(sal_abs)
    dest_ext = (pedido.get("destino") or "").lower().lstrip(".")
    # Una SECUENCIA (`salida_%03d.png`) es multifichero por construccion: el
    # patron printf ES la declaracion. Los ficheros que casan con el patron son
    # el fichero declarado, no sobras.
    patron = None
    if "%" in base:
        import re as _re
        patron = _re.compile("^" + _re.sub(r"%0?\d*[diu]", r"\\d+",
                                           _re.escape(base).replace("\\%", "%")
                                           ) + "$")
    multi = (dest_ext in DESTINOS_MULTIFICHERO or bool(pedido.get("multifichero"))
             or patron is not None)

    tam_declarado = 0
    try:
        tam_declarado = os.path.getsize(sal_abs)
    except OSError:
        pass
    if patron is not None:
        tam_declarado = sum(
            t for n, t in (despues.get(dir_destino) or {}).items()
            if patron.match(n) and t > 0
            and n not in (antes.get(dir_destino) or {}))

    nuevos_fuera, nuevos_dentro, sobrescritos = [], [], []
    for d, cens_d in despues.items():
        prev = antes.get(d, {})
        for n, t in cens_d.items():
            if n not in prev:
                (nuevos_dentro if os.path.abspath(d) == dir_destino
                 else nuevos_fuera).append((os.path.join(d, n), t))
            elif prev[n] != t and t >= 0:
                sobrescritos.append((os.path.join(d, n), prev[n], t))
    nuevos_dentro = [(p, t) for p, t in nuevos_dentro
                     if os.path.basename(p) != base
                     and not (patron and patron.match(os.path.basename(p)))]

    bytes_fuera = sum(max(t, 0) for _, t in nuevos_fuera)
    bytes_dentro = sum(max(t, 0) for _, t in nuevos_dentro)

    # ---- 5a. FUGA: ficheros escritos fuera del directorio de destino -------
    if nuevos_fuera:
        # La severidad la decide el REPARTO DE BYTES, no el numero de ficheros.
        # Medido: `ffmpeg -> .mpd` deja 528 447 B fuera y entrega 1 234 B
        # (el contenido se fue); `magick -> .html` deja 98 B fuera y entrega
        # 506 B (suciedad, no perdida de contenido).
        sev = "fallo" if bytes_fuera > max(tam_declarado, 1) else "aviso"
        h.append(_hallazgo(
            5, "N5" if sev == "fallo" else "N6", sev,
            "el motor escribio %d fichero(s) (%d B) FUERA del directorio de "
            "destino: %s" % (len(nuevos_fuera), bytes_fuera,
                             ", ".join(os.path.basename(p)
                                       for p, _ in nuevos_fuera[:4])),
            "0 ficheros fuera de %s" % dir_destino,
            [os.path.relpath(p) for p, _ in nuevos_fuera[:8]]))

    # ---- 5b. SATELITES: mas de un fichero en el destino ---------------------
    if nuevos_dentro:
        acompana = all(os.path.splitext(p)[1].lower() in _SATELITES
                       or os.path.splitext(base)[0] in os.path.basename(p)
                       for p, _ in nuevos_dentro)
        if multi and acompana:
            h.append(_hallazgo(
                5, "N7", "informativo",
                "salida multifichero declarada (%s): %d fichero(s) "
                "acompañan al declarado" % (dest_ext, len(nuevos_dentro)),
                DESTINOS_MULTIFICHERO.get(dest_ext, "pedido.multifichero"),
                [os.path.basename(p) for p, _ in nuevos_dentro[:8]]))
        else:
            h.append(_hallazgo(
                5, "N7", "aviso",
                "la conversion entrego %d fichero(s) ADEMAS del declarado "
                "(%d B) y el destino .%s no es multifichero"
                % (len(nuevos_dentro), bytes_dentro, dest_ext),
                "1 fichero", [os.path.basename(p) for p, _ in nuevos_dentro[:8]]))

    # ---- 5c. SOBRESCRITURA de algo que ya estaba ---------------------------
    if sobrescritos:
        h.append(_hallazgo(
            5, "N8", "aviso",
            "el motor modifico %d fichero(s) que ya existian" % len(sobrescritos),
            "0", [os.path.basename(p) for p, _, _ in sobrescritos[:4]]))

    # ---- 5d. REPARTO: que fraccion de lo escrito lleva el fichero entregado -
    total = tam_declarado + bytes_fuera + bytes_dentro
    if total:
        h.append(_hallazgo(
            5, "N9", "informativo",
            "el fichero declarado lleva el %.1f %% de los bytes escritos "
            "(%d de %d B)" % (100.0 * tam_declarado / total, tam_declarado, total),
            "100 %", round(100.0 * tam_declarado / total, 1)))
    return h


PUNTOS = ("1_firma", "2_flujos", "3_propiedades", "4_pedido", "5_escritura")


def verificar(salida: str, pedido: dict | None = None, entrada: str | None = None,
              motor: str = "proceso", sonda_ent: dict | None = None,
              sonda_sal: dict | None = None, alfa: bool = False,
              censo: dict | None = None) -> dict:
    """Ejecuta los CINCO puntos del contrato y cronometra cada uno.

    alfa=True calcula min(alfa) de la ENTRADA en proceso cuando hace falta para
    la regla I2 y no viene inyectado. Es el unico dato del contrato que exige
    decodificar pixeles; por eso es opcional y se cronometra aparte.

    censo = {"antes": {dir: {nombre: tam}}, "despues": {...}} habilita el
    PUNTO 5 (¿escribio el motor fuera de lo declarado?). Sin censo el punto 5
    NO se da por bueno: se declara no cubierto, porque a posteriori es
    irrecuperable. Ver punto5_escritura y la regla R18.
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
    for nombre, fn in (("1_firma", lambda: punto1_firma(salida, sonda_sal, pedido,
                                                        sonda_ent)),
                       ("2_flujos", lambda: punto2_flujos(sonda_sal, sonda_ent, pedido)),
                       ("3_propiedades", lambda: punto3_propiedades(sonda_sal, sonda_ent, pedido)),
                       ("4_pedido", lambda: punto4_pedido(sonda_sal, sonda_ent, pedido)),
                       ("5_escritura", lambda: punto5_escritura(salida, pedido, censo))):
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
    # 1_firma DEJA DE SER True INCONDICIONAL (F1). Estaba mintiendo: declaraba el
    # punto 1 cubierto en el 100 % de los ficheros mientras E1 medía que solo era
    # evaluable en el 12 % de los destinos. Ahora vale True si se evaluo (aunque
    # sea a nivel de familia) o si el formato no tiene marcador que evaluar
    # -- "no aplica" es cobertura, "no tengo la firma en la tabla" no lo es.
    _p1 = punto1_estado(salida)
    cobertura = {"1_firma": _p1 in ("evaluado", "familia", "no_aplica"),
                 "2_flujos": sonda_sal.get("categoria") != "av" or sonda_ent is not None,
                 # CORRECCION F1: no basta con que la sonda no haya dado error. Un
                 # formato CRUDO SIN CABECERA (.rgb, .gray, .yuv) no da error: la
                 # sonda devuelve categoria "desconocida" porque no hay cabecera que
                 # leer, y el contrato declaraba los puntos 3 y 4 cubiertos habiendo
                 # medido cero propiedades. Es la misma mentira que 1_firma: "no he
                 # podido comprobarlo" no es "comprobado y correcto".
                 "3_propiedades": (not sonda_sal.get("error")
                                   and sonda_sal.get("categoria") not in
                                   (None, "desconocida", "ilegible", "vacio")),
                 "4_pedido": (sonda_ent is not None and not sonda_sal.get("error")
                              and sonda_sal.get("categoria") not in
                              (None, "desconocida", "ilegible", "vacio")),
                 # min(alfa) es el unico dato del contrato que exige pixeles:
                 # se cubre si la entrada no tiene alfa (nada que comprobar) o
                 # si min(alfa) se conoce (calculado o inyectado).
                 "4_alfa": (sonda_ent is None
                            or not sonda_ent.get("tiene_alfa")
                            or sonda_ent.get("alfa_no_trivial") is not None),
                 # El punto 5 solo es evaluable EN EL MOMENTO DE CONVERTIR: si
                 # nadie censo el directorio, la informacion ya no existe.
                 # Decirlo es el trabajo del verificador; darlo por bueno seria
                 # el fallo de markitdown-mcp otra vez.
                 "5_escritura": censo is not None}
    if veredicto == "ok" and not all(cobertura.values()):
        veredicto = "ok_parcial"
    ms["total"] = sum(ms.values())
    ms["logica"] = sum(ms[k] for k in PUNTOS)
    return {"salida": salida, "entrada": entrada, "motor": motor,
            "categoria": sonda_sal.get("categoria"), "veredicto": veredicto,
            "cobertura": cobertura, "punto1": _p1,
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


def _ffprobe_fotogramas(ruta: str):
    """V2: numero REAL de fotogramas de video. `nb_frames` viene vacio en
    MKV/WebM y ffprobe no lo estima, asi que hay que contarlos de verdad con
    -count_frames. Es la sonda mas cara del grupo C sobre video largo."""
    rc, out, err = _correr(["ffprobe", "-v", "error", "-count_frames",
                            "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames", "-of",
                            "default=nokey=1:noprint_wrappers=1", ruta])
    t = (out or "").strip().splitlines()
    for l in t:
        l = l.strip()
        if l.isdigit():
            return int(l), None
    return None, ((err or out).strip()[:200] or "sin nb_read_frames")


def _ffprobe_etiquetas(ruta: str):
    """V5: etiquetas de idioma y titulo por pista, en orden."""
    rc, out, err = _correr(["ffprobe", "-v", "error", "-show_entries",
                            "stream=index,codec_type:stream_tags=language,title",
                            "-of", "json", ruta])
    try:
        d = json.loads(out or "{}")
    except ValueError:
        return None, (err or out).strip()[:200]
    fuera = []
    for s in d.get("streams", []):
        tg = s.get("tags") or {}
        fuera.append({"tipo": s.get("codec_type"),
                      "language": (tg.get("language") or "").lower() or None,
                      "title": tg.get("title") or None})
    return fuera, None


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
    aqui.

    FALLO ATRAPADO Y CORREGIDO (P3): la version anterior usaba
    `-sOutputFile=-` y leia la TUBERIA. Medido sobre el mismo PDF, 250
    ejecuciones de cada una: la tuberia devolvio VACIO 12 veces (4,80 %) y el
    fichero temporal 0 veces (0,00 %), con la misma mediana (184,9 frente a
    184,6 ms). Nunca devolvia texto parcial: o 105 caracteres o cero. Es la
    observacion no reproducida de verificador-ghostscript.md §5.9, ahora
    reproducida y localizada: NO es Ghostscript, es la captura por tuberia.
    Importa porque de aqui cuelgan P2 (severidad FALLO), P5, P6 y P9.
    """
    import tempfile
    fd, tmp = tempfile.mkstemp(suffix=".txt", prefix="filex_txtwrite_")
    os.close(fd)
    try:
        rc, out, err = _correr(["gswin64c", "-q", "-dNOPAUSE", "-dBATCH",
                                "-dSAFER", "-sDEVICE=txtwrite",
                                "-sOutputFile=" + tmp, pdf])
        try:
            with open(tmp, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            texto = ""
        if rc != 0 and not texto:
            return None, (err or "gs fallo").strip()[:200]
        return texto, None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


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


# ---------------------------------------------------------------------------
# I9 — TINTA DONDE HABIA <text>: la regla que atrapa a resvg
#
# bench/aristas-nominales.md §8.2: resvg 0.46.0 devuelve rc=0, un PNG con firma
# valida, de la geometria EXACTA pedida, y SIN UNA SOLA LETRA (0,00 % de tinta
# en la banda de texto frente al 14,02 % de Inkscape). Pasa los cuatro puntos
# del contrato. Lo unico que lo delata esta en stderr, que por regla de diseño
# no se devuelve al modelo.
#
# La regla: si el SVG de origen tiene elementos <text> con contenido, la salida
# rasterizada debe tener TINTA donde estaban. Todo en proceso: xml.etree para
# el origen, decodificador PNG propio para la salida.
# ---------------------------------------------------------------------------

TINTA_MIN_TEXTO = 0.5      # % de pixeles con tinta en la caja del texto.
TINTA_AVISO_TEXTO = 2.0    # por debajo: aviso (texto mutilado, no ausente)
_NS_SVG = "{http://www.w3.org/2000/svg}"


def _num(v, por_defecto=0.0):
    if v is None:
        return por_defecto
    try:
        t = str(v).strip()
        for u in ("px", "pt", "mm", "cm", "in", "%", "em"):
            if t.endswith(u):
                t = t[:-len(u)]
                break
        return float(t)
    except ValueError:
        return por_defecto


def _estilo(el, clave, heredado=None):
    """Atributo o propiedad dentro de style=. SVG admite las dos formas."""
    v = el.get(clave)
    if v is None:
        st = el.get("style") or ""
        for par in st.split(";"):
            if ":" in par:
                k, _, w = par.partition(":")
                if k.strip() == clave:
                    v = w.strip()
                    break
    return v if v is not None else heredado


def svg_textos(ruta: str) -> dict:
    """Elementos <text> de un SVG, con su caja ESTIMADA en coordenadas de
    usuario. En proceso, con xml.etree (biblioteca estandar).

    La caja es una estimacion tipografica deliberadamente ESTRECHA: la banda
    vertical va de y-0,75em a y+0,20em (la zona donde cualquier fuente pinta
    mayusculas y minusculas) y la horizontal cubre los primeros caracteres a
    0,50 em de avance medio. Estrecha es lo correcto: una caja generosa que
    incluyera otras figuras daria falsos NEGATIVOS (tinta ajena que tapa la
    ausencia de letras).
    """
    import xml.etree.ElementTree as ET
    r = {"evaluable": False, "motivo": None, "n_textos": 0, "cajas": [],
         "ancho_usuario": None, "alto_usuario": None}
    try:
        arbol = ET.parse(ruta)
    except Exception as e:                                   # noqa: BLE001
        r["motivo"] = "no es un XML analizable: %s" % type(e).__name__
        return r
    raiz = arbol.getroot()
    if not raiz.tag.endswith("svg"):
        r["motivo"] = "la raiz no es <svg>"
        return r
    vb = (raiz.get("viewBox") or "").replace(",", " ").split()
    if len(vb) == 4:
        vx, vy, vw, vh = [_num(x) for x in vb]
    else:
        vx = vy = 0.0
        vw, vh = _num(raiz.get("width"), 0), _num(raiz.get("height"), 0)
    if not (vw and vh):
        r["motivo"] = "sin viewBox ni width/height utilizables"
        return r
    r["ancho_usuario"], r["alto_usuario"] = vw, vh

    for el in raiz.iter():
        if el.tag != _NS_SVG + "text" and el.tag != "text":
            continue
        txt = "".join(el.itertext()).strip()
        if not txt:
            continue
        fs = _num(_estilo(el, "font-size"), 16.0) or 16.0
        x = _num(el.get("x"), 0.0)
        y = _num(el.get("y"), 0.0)
        anchor = (_estilo(el, "text-anchor") or "start").strip()
        n = min(len(txt), 24)
        an = 0.50 * fs * n                       # avance medio conservador
        if anchor == "middle":
            x0 = x - an / 2.0
        elif anchor == "end":
            x0 = x - an
        else:
            x0 = x
        caja = (max(x0 - vx, 0.0), max(y - 0.75 * fs - vy, 0.0),
                min(x0 + an - vx, vw), min(y + 0.20 * fs - vy, vh))
        if caja[2] <= caja[0] or caja[3] <= caja[1]:
            continue
        r["cajas"].append({"caja": [round(c, 2) for c in caja],
                           "texto": txt[:40], "font_size": fs})
        r["n_textos"] += 1
    r["evaluable"] = True
    return r


def _desfiltrar_fila(filtro, filt, previo, bpp):
    """Desfiltrado COMPLETO de una fila de PNG (RFC 2083 §6), no de un carril."""
    n = len(filt)
    if filtro == 0:
        return bytearray(filt)
    out = bytearray(n)
    if filtro == 1:
        out[:bpp] = filt[:bpp]
        for j in range(bpp, n):
            out[j] = (filt[j] + out[j - bpp]) & 255
    elif filtro == 2:
        # 'Up' no depende del pixel de la izquierda: se puede hacer sin indexar,
        # que en Python puro es la mitad de caro.
        return bytearray((a + b) & 255 for a, b in zip(filt, previo))
    elif filtro == 3:
        for j in range(n):
            a = out[j - bpp] if j >= bpp else 0
            out[j] = (filt[j] + ((a + previo[j]) >> 1)) & 255
    elif filtro == 4:
        for j in range(n):
            a = out[j - bpp] if j >= bpp else 0
            c = previo[j - bpp] if j >= bpp else 0
            out[j] = (filt[j] + _paeth(a, previo[j], c)) & 255
    else:
        raise ValueError("filtro PNG desconocido: %r" % filtro)
    return out


def png_tinta_cajas(ruta: str, cajas, esc_x=1.0, esc_y=1.0) -> dict:
    """% de pixeles con TINTA dentro de cada caja de un PNG, EN PROCESO.

    'Tinta' se define contra el fondo REAL de la caja (el valor de luminancia
    mas frecuente), no contra el negro: asi vale igual para texto oscuro sobre
    claro que al reves. Umbral: |lum - fondo| > 64 de 255.

    No entrelazado. Adam7 devuelve evaluable=false con el motivo (la maquinaria
    de las 7 pasadas existe para min(alfa) pero reconstruir la imagen completa
    es otro problema y decirlo es mejor que inventar un numero).
    """
    r = {"evaluable": False, "motivo": None, "cajas": [], "filas_leidas": 0}
    try:
        fh = open(ruta, "rb")
    except OSError as e:
        r["motivo"] = str(e)
        return r
    with fh:
        if fh.read(8) != b"\x89PNG\r\n\x1a\n":
            r["motivo"] = "no es PNG (la regla solo cubre PNG en proceso)"
            return r
        m = _png_meta(fh)
        if m.get("entrelazado"):
            r["motivo"] = "PNG entrelazado (Adam7): no implementado para pixeles"
            return r
        if m.get("pos_idat") is None:
            r["motivo"] = "sin IDAT"
            return r
        an, al, bd, ct = m["ancho"], m["alto"], m["prof"], m["color"]
        canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ct)
        if canales is None or bd not in (1, 2, 4, 8, 16):
            r["motivo"] = "color type %s / profundidad %s no cubiertos" % (ct, bd)
            return r
        paleta = None
        if ct == 3:
            fh.seek(8)
            paleta = _leer_plte(fh)
            if paleta is None:
                r["motivo"] = "PNG de paleta sin PLTE"
                return r
        bits_px = canales * bd
        tam_fila = (an * bits_px + 7) // 8
        bpp = max(1, bits_px // 8)
        # Cajas en pixeles de la imagen, y hasta que fila hay que llegar.
        pix = []
        for c in cajas:
            x0, y0, x1, y1 = c["caja"] if isinstance(c, dict) else c
            pix.append((max(int(x0 * esc_x), 0), max(int(y0 * esc_y), 0),
                        min(int(round(x1 * esc_x)), an),
                        min(int(round(y1 * esc_y)), al)))
        if not pix:
            r["motivo"] = "sin cajas que medir"
            return r
        y_max = max(p[3] for p in pix)
        hist = [[0] * 256 for _ in pix]
        previo = bytearray(tam_fila)
        y = 0
        for filtro, filt in _png_filas(fh, m["pos_idat"], tam_fila):
            if y >= y_max:
                break
            fila = _desfiltrar_fila(filtro, filt, previo, bpp)
            previo = fila
            r["filas_leidas"] += 1
            for k, (x0, y0, x1, y1) in enumerate(pix):
                if not (y0 <= y < y1):
                    continue
                hk = hist[k]
                for x in range(x0, x1):
                    hk[_lum_png(fila, x, ct, bd, canales, paleta)] += 1
            y += 1
    total_tinta = 0.0
    for k, (x0, y0, x1, y1) in enumerate(pix):
        hk = hist[k]
        n = sum(hk)
        if not n:
            r["cajas"].append({"caja": [x0, y0, x1, y1], "pixeles": 0,
                               "tinta_pct": None})
            continue
        fondo = max(range(256), key=lambda v: hk[v])
        tinta = sum(hk[v] for v in range(256) if abs(v - fondo) > 64)
        pct = 100.0 * tinta / n
        total_tinta = max(total_tinta, pct)
        r["cajas"].append({"caja": [x0, y0, x1, y1], "pixeles": n,
                           "fondo_lum": fondo, "tinta_pct": round(pct, 3)})
    r["evaluable"] = True
    r["tinta_max_pct"] = round(total_tinta, 3)
    return r


def _leer_plte(fh):
    while True:
        cab = fh.read(8)
        if len(cab) < 8:
            return None
        ln, tipo = _u32(cab, 0), cab[4:8]
        if tipo == b"PLTE":
            d = fh.read(ln)
            return [(d[i], d[i + 1], d[i + 2]) for i in range(0, ln - 2, 3)]
        if tipo in (b"IDAT", b"IEND"):
            return None
        fh.seek(ln + 4, io.SEEK_CUR)


def _lum_png(fila, x, ct, bd, canales, paleta):
    """Luminancia 0-255 del pixel x de una fila ya desfiltrada."""
    if bd == 8:
        o = x * canales
        if ct == 3:
            r, g, b = paleta[fila[o]] if fila[o] < len(paleta) else (0, 0, 0)
        elif ct in (0, 4):
            return fila[o]
        else:
            r, g, b = fila[o], fila[o + 1], fila[o + 2]
        return (r * 299 + g * 587 + b * 114) // 1000
    if bd == 16:
        o = x * canales * 2
        if ct in (0, 4):
            return fila[o]
        return (fila[o] * 299 + fila[o + 2] * 587 + fila[o + 4] * 114) // 1000
    # 1/2/4 bits: gris o paleta
    por_byte = 8 // bd
    v = (fila[x // por_byte] >> (8 - bd * (x % por_byte + 1))) & ((1 << bd) - 1)
    if ct == 3:
        r, g, b = paleta[v] if v < len(paleta) else (0, 0, 0)
        return (r * 299 + g * 587 + b * 114) // 1000
    return v * 255 // ((1 << bd) - 1)


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


# Interruptor de V2 (C12). Lista de un elemento para que la CLI y los arneses
# puedan cambiarlo sin tocar el resto; v2(False) lo apaga.
_V2_ACTIVA = [True]


def v2(activa: bool):
    """Enciende o apaga la regla V2 (recuento real de fotogramas)."""
    _V2_ACTIVA[0] = bool(activa)


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

    # ---- V5: etiquetas de idioma y titulo ---------------------------------
    # Va ANTES de los cortes por 'escala'/'fps': reescalar no es excusa para
    # perder el idioma de una pista. La nota de la propia regla avisa de que
    # patologico_2pistas.mkv NO trae etiquetas: cuando la ENTRADA no tiene
    # ninguna, la regla no puede discriminar y se declara informativa con
    # cobertura, no aprobada en silencio.
    if dest not in ("wav", "bmp", "png", "jpg", "jpeg"):
        t0 = time.perf_counter()
        te, ee = _ffprobe_etiquetas(entrada)
        ts, es = _ffprobe_etiquetas(salida)
        ms["V5"] = (time.perf_counter() - t0) * 1000
        cob["V5"] = te is not None and ts is not None
        if te is None or ts is None:
            h.append(_fid("V5", "informativo", "etiquetas no legibles",
                          None, ee or es))
        else:
            con_etiqueta = [x for x in te if x["language"] or x["title"]]
            if not con_etiqueta:
                h.append(_fid("V5", "informativo",
                              "la entrada no trae etiquetas de idioma ni titulo "
                              "en ninguna de sus %d pistas: la regla no "
                              "discrimina" % len(te), None, 0))
            else:
                perdidas = []
                for i, x in enumerate(te):
                    if not (x["language"] or x["title"]):
                        continue
                    y = ts[i] if i < len(ts) else None
                    for campo in ("language", "title"):
                        # 'und' es el valor por defecto de MP4/Matroska: que la
                        # salida ponga 'und' donde la entrada no decia nada no
                        # es una perdida; al reves si.
                        v = x[campo]
                        w = (y or {}).get(campo)
                        if v and v != "und" and w != v:
                            perdidas.append("pista %d %s: %r -> %r"
                                            % (i, campo, v, w))
                if perdidas:
                    h.append(_fid("V5", "aviso",
                                  "se pierden etiquetas de pista: " +
                                  "; ".join(perdidas[:4]),
                                  [x for x in te], [x for x in ts]))
                else:
                    h.append(_fid("V5", "informativo",
                                  "las %d etiquetas de pista se conservan"
                                  % len(con_etiqueta), None, None))

    if sonda.get("n_video", 0) < 1 or sonda_ent.get("n_video", 0) < 1:
        return h, cob
    if p.get("escala") or p.get("recortar"):
        return h, cob

    # ---- V2: numero de fotogramas, contados de verdad ----------------------
    # Solo si NO se pidio cambiar el fps: si se pidio, el numero DEBE cambiar y
    # exigir igualdad seria un falso positivo.
    #
    # INTERRUPTOR PROPIO (C12): `ffprobe -count_frames` DECODIFICA el video
    # entero. Es el 36 % de la suite de fidelidad y la sube un 60,6 %. Con
    # V2=off la regla se declara NO CUBIERTA, no aprobada.
    if not _V2_ACTIVA[0]:
        cob["V2"] = False
        h.append(_fid("V2", "informativo",
                      "recuento de fotogramas DESACTIVADO (--sin-v2): decodifica "
                      "el video entero", None, None))
    elif not p.get("fps"):
        t0 = time.perf_counter()
        ns_, es2 = _ffprobe_fotogramas(salida)
        ne_, ee2 = _ffprobe_fotogramas(entrada)
        ms["V2"] = (time.perf_counter() - t0) * 1000
        cob["V2"] = ns_ is not None and ne_ is not None
        if ns_ is None or ne_ is None:
            h.append(_fid("V2", "informativo", "recuento de fotogramas no "
                          "calculable", None, es2 or ee2))
        elif ns_ != ne_:
            h.append(_fid("V2", "fallo",
                          "el numero de fotogramas de video NO se conserva",
                          ne_, ns_))
        else:
            h.append(_fid("V2", "informativo",
                          "%d fotogramas conservados (contados)" % ns_, ne_, ns_))

    if p.get("fps"):
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


# P9 — la señal contra la alucinacion del OCR (verificador-ghostscript.md §5.8).
#
# *** AVISO: P9 ESTA REFUTADA COMO CRITERIO. NO USARLA PARA DECIDIR. ***
# Validada por P3 (bench/contrato-quinto-punto.md §6) contra 32 capas OCR
# REALES y 19 capas de texto legitimo:
#   - sensibilidad 1 de 12 = 8,3 %. El unico caso que detecta es aquel sobre el
#     que se calibro. A resoluciones altas Ghostscript alucina palabras LARGAS
#     y plausibles (longitud media 4,4-5,6): los tokens de una letra son UN
#     modo de alucinar, no LA alucinacion.
#   - 5 falsos positivos de 14 capas legitimas evaluables (36 %): una tabla,
#     una formula, iniciales, una lista de letras y un texto corto mixto.
#   - especificidad sobre capas OCR: 20 de 20. Por eso se conserva como AVISO.
# El sustituto medido (16 de 16, sin un error) es el ACUERDO entre dos pasadas
# de OCR con idiomas distintos: >= 0,80 de similitud = texto reconocido,
# <= 0,70 = invencion. Cuesta una segunda pasada de OCR y esta PENDIENTE de
# validarse fuera de Ghostscript.
P9_LONG_MEDIA_MIN = 3.0
P9_PCT_1LETRA_MAX = 50.0
P9_TOKENS_MIN = 8          # por debajo, la estadistica no se sostiene


def senal_alucinacion(texto: str) -> dict:
    """Estadistica de tokens de una capa de texto. Microsegundos, sin procesos:
    el texto ya lo extrajo P6."""
    tk = texto.split()
    n = len(tk)
    if not n:
        return {"tokens": 0, "long_media": 0.0, "pct_una_letra": 0.0,
                "alucinacion": False, "motivo": "sin tokens"}
    lm = sum(len(t) for t in tk) / n
    p1 = 100.0 * sum(1 for t in tk if len(t) == 1) / n
    if n < P9_TOKENS_MIN:
        return {"tokens": n, "long_media": lm, "pct_una_letra": p1,
                "alucinacion": False,
                "motivo": "menos de %d tokens: la señal no discrimina"
                          % P9_TOKENS_MIN}
    return {"tokens": n, "long_media": lm, "pct_una_letra": p1,
            "alucinacion": lm < P9_LONG_MEDIA_MIN or p1 >= P9_PCT_1LETRA_MAX,
            "motivo": None}


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
    # ---- P9: ¿es una capa de texto o es una ALUCINACION del OCR? -----------
    # verificador-ghostscript.md §5.8: el verificador daba OK a la reparacion
    # alucinada de escaneado_d3 porque P5 dice "si la entrada no tenia texto no
    # se exige texto" y el umbral de P6 (>=10) lo superan 75 caracteres de
    # ruido. El texto YA esta extraido por P6: la regla no lanza ningun proceso.
    if ns >= TEXTO_MIN_CHARS:
        t0 = time.perf_counter()
        sen = senal_alucinacion(ts)
        ms["P9"] = (time.perf_counter() - t0) * 1000
        cob["P9"] = True
        pidio_ocr = bool(pedido.get("params", {}).get("ocr") or pedido.get("ocr"))
        if sen["alucinacion"]:
            h.append(_fid("P9", "fallo" if pidio_ocr else "aviso",
                          "TEXTO SOSPECHOSO DE ALUCINACION: longitud media de "
                          "token %.2f (umbral %.1f) y %.1f %% de tokens de una "
                          "sola letra (umbral %.0f %%)"
                          % (sen["long_media"], P9_LONG_MEDIA_MIN,
                             sen["pct_una_letra"], P9_PCT_1LETRA_MAX),
                          ">= %.1f y < %.0f %%" % (P9_LONG_MEDIA_MIN,
                                                   P9_PCT_1LETRA_MAX),
                          [sen["long_media"], sen["pct_una_letra"]]))
        else:
            h.append(_fid("P9", "informativo",
                          "capa de texto plausible (long. media %.2f, %.1f %% "
                          "de tokens de una letra)"
                          % (sen["long_media"], sen["pct_una_letra"]),
                          None, [sen["long_media"], sen["pct_una_letra"]]))
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
        # CAMBIO DE FIRMA (C11): la propia regla P5 dice "salvo que se pidiera
        # OCR", y hasta ahora el `pedido` no llevaba ese dato. Con
        # params.ocr=true la exigencia se invierte: la salida DEBE traer texto.
        if pedido.get("params", {}).get("ocr") or pedido.get("ocr"):
            if ns < TEXTO_MIN_CHARS:
                h.append(_fid("P5", "fallo",
                              "se pidio OCR y la salida no trae capa de texto "
                              "(%d caracteres, umbral %d)"
                              % (ns, TEXTO_MIN_CHARS), ">= %d" % TEXTO_MIN_CHARS,
                              ns))
            else:
                h.append(_fid("P5", "informativo",
                              "se pidio OCR y la salida trae %d caracteres; su "
                              "plausibilidad la juzga P9" % ns, None, ns))
        else:
            h.append(_fid("P5", "informativo",
                          "la entrada no tiene capa de texto (%d caracteres) y no "
                          "se pidio OCR: no se exige texto en la salida"
                          % ne, None, ne))
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


def es_svg(ruta: str) -> bool:
    """¿Es un SVG? Por contenido, no por extension. (La sonda del contrato lo
    clasifica hoy como 'datos/csv': su vocabulario de firmas no lo conoce, que
    es el pendiente C14.)"""
    try:
        with open(ruta, "rb") as fh:
            cab = fh.read(1024).lstrip()
        return cab.startswith(b"<svg") or (cab.startswith(b"<?xml")
                                           and b"<svg" in cab)
    except OSError:
        return False


def fidelidad_vectorial(salida, entrada, pedido, sonda, sonda_ent, ms):
    """I9: si el SVG de origen tiene <text>, la salida rasterizada debe tener
    TINTA donde estaban. Es la regla que atrapa a resvg 0.46.0."""
    h = []
    cob = {}
    t0 = time.perf_counter()
    tx = svg_textos(entrada)
    ms["I9_origen"] = (time.perf_counter() - t0) * 1000
    if not tx["evaluable"]:
        ms["I9"] = ms["I9_origen"]
        h.append(_fid("I9", "informativo", "el origen no es un SVG analizable",
                      None, tx["motivo"]))
        return h, cob
    if not tx["n_textos"]:
        ms["I9"] = ms["I9_origen"]
        h.append(_fid("I9", "informativo",
                      "el SVG de origen no tiene elementos <text>: la regla no "
                      "aplica", None, 0))
        return h, cob
    an = sonda.get("ancho")
    al = sonda.get("alto")
    if not (an and al):
        h.append(_fid("I9", "informativo", "la salida no declara geometria",
                      None, None))
        return h, cob
    t0 = time.perf_counter()
    ti = png_tinta_cajas(salida, tx["cajas"],
                         an / tx["ancho_usuario"], al / tx["alto_usuario"])
    ms["I9_salida"] = (time.perf_counter() - t0) * 1000
    ms["I9"] = ms["I9_origen"] + ms["I9_salida"]
    if not ti["evaluable"]:
        cob["I9"] = False
        h.append(_fid("I9", "informativo", "no se pudo leer la tinta de la salida",
                      None, ti["motivo"]))
        return h, cob
    cob["I9"] = True
    peor = min((c["tinta_pct"] for c in ti["cajas"]
                if c["tinta_pct"] is not None), default=None)
    mejor = ti.get("tinta_max_pct")
    if peor is None:
        cob["I9"] = False
        h.append(_fid("I9", "informativo", "cajas de texto fuera del lienzo",
                      None, None))
    elif mejor is not None and mejor < TINTA_MIN_TEXTO:
        h.append(_fid("I9", "fallo",
                      "TEXTO PERDIDO: el SVG tiene %d elemento(s) <text> y la "
                      "salida rasterizada no tiene tinta donde estaban "
                      "(%.2f %% maximo)" % (tx["n_textos"], mejor),
                      ">= %.1f %% de tinta" % TINTA_MIN_TEXTO, mejor))
    elif peor < TINTA_MIN_TEXTO:
        h.append(_fid("I9", "fallo",
                      "TEXTO PARCIALMENTE PERDIDO: %d de %d elementos <text> "
                      "no dejaron tinta"
                      % (sum(1 for c in ti["cajas"]
                             if (c["tinta_pct"] or 0) < TINTA_MIN_TEXTO),
                         tx["n_textos"]),
                      ">= %.1f %% de tinta" % TINTA_MIN_TEXTO, peor))
    elif peor < TINTA_AVISO_TEXTO:
        h.append(_fid("I9", "aviso",
                      "texto con muy poca tinta: puede estar mutilado",
                      ">= %.1f %%" % TINTA_AVISO_TEXTO, peor))
    else:
        h.append(_fid("I9", "informativo",
                      "los %d elementos <text> dejaron tinta (%.2f %% el peor)"
                      % (tx["n_textos"], peor), None, peor))
    return h, cob


REGLAS_FIDELIDAD = ("I3", "I6", "I7", "I8", "I9", "V2", "V5", "V6", "V8", "V9",
                    "A4", "A5", "P2", "P6", "P9")


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
        svg_ent = es_svg(entrada)
        for fn in (fidelidad_imagen, fidelidad_vectorial, fidelidad_video,
                   fidelidad_audio, fidelidad_pdf):
            # I9 se despacha por el ORIGEN (un SVG), no por la categoria de la
            # salida: la sonda del contrato clasifica hoy un SVG como 'datos'.
            if fn is fidelidad_vectorial and not (svg_ent and cat == "imagen"):
                continue
            if fn is fidelidad_imagen and (cat not in ("imagen",) or svg_ent):
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
    Puntos 1-5 de PLAN-ORQUESTADOR.md 4.2. Veredicto: ok / aviso / ok_parcial /
    fallo. Es el unico grupo que puede correr dentro de un lote.

    PUNTO 5 - ¿escribio el motor FUERA de lo declarado? Necesita el censo del
    directorio de trabajo, que SOLO existe en el momento de convertir:
      python verificador.py --censar DIR_TRABAJO DIR_DESTINO > /otro/antes.json
      ... la conversion ...
      python verificador.py --censar DIR_TRABAJO DIR_DESTINO > /otro/desp.json
      python verificador.py --salida SAL --censo censo.json
    (los censos se escriben FUERA de los directorios censados, o el propio
    fichero de censo aparece como escritura no declarada)
    donde censo.json es {"antes": <censar>, "despues": <censar>}. Sin censo el
    punto 5 se declara NO CUBIERTO y el veredicto baja a ok_parcial: a
    posteriori la informacion ya no existe. Con la regla R18 (directorio de
    trabajo propio y desechable) el "antes" es {} y basta el "despues".

  GRUPO B - CARACTERIZACION DE LA ENTRADA (una vez por ENTRADA, cacheable)
      python verificador.py --alfa-min ENT            # el dato, suelto
      python verificador.py --salida SAL ... --alfa   # y usado por la regla I2
    min(alfa) en proceso: el unico dato del contrato que exige decodificar
    pixeles. SIN el, la regla I2 no es evaluable y el veredicto baja a
    'ok_parcial' con cobertura 4_alfa=false. NUNCA se calcula por defecto.

  GRUPO C - FIDELIDAD (bajo demanda o en regresion; cuesta como convertir)
      python verificador.py --salida SAL --entrada ENT --solo-fidelidad
      python verificador.py --salida SAL --entrada ENT --alfa --fidelidad
    Reglas I3/I6/I7/I8/I9, V2/V5/V6/V8/V9, A4/A5, P2/P5/P6/P9.
    I9: si el SVG de origen tiene <text>, la salida rasterizada debe tener
        tinta donde estaban (el caso resvg: PNG perfecto, sin una sola letra).
    P9: la capa de texto de una reparacion por OCR no puede ser ruido.
        Con params.ocr=true la severidad sube de aviso a fallo.
        OJO: P9 esta REFUTADA COMO CRITERIO (8,3 % de sensibilidad sobre 32
        capas OCR reales y 36 % de falsos positivos sobre texto legitimo
        corto). Sirve de aviso, no para decidir. Ver contrato-quinto-punto.md.
    AVISO: V2 cuenta los fotogramas con `ffprobe -count_frames`, que DECODIFICA
    el video entero. Sobre un MP4 de 16 MB son 3,5 s, x10 000 el contrato: es,
    con diferencia, la regla mas cara del grupo C. Tiene interruptor: --sin-v2.

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
                         "magick, y lo vuelca en JSON. Cubre PNG (incluido "
                         "Adam7), WebP, TIFF (sin comprimir/LZW/Deflate/"
                         "PackBits, con predictor, chunky y planar) y GIF (LZW "
                         "del fotograma 1). En AVIF/HEIF, TIFF en teselas o con "
                         "compresion JPEG, y WebP animado devuelve "
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
    ap.add_argument("--censo", metavar="F.json",
                    help="[A] censo del directorio de trabajo para el PUNTO 5: "
                         '{"antes":{dir:{nombre:tam}},"despues":{...}}. Sin el, '
                         "el punto 5 se declara NO CUBIERTO (a posteriori es "
                         "irrecuperable). Ver la regla R18")
    ap.add_argument("--censar", metavar="DIR", nargs="+",
                    help="[A] utilidad: vuelca en JSON el censo de uno o varios "
                         "directorios (para tomar el 'antes' y el 'despues')")
    ap.add_argument("--sin-v2", action="store_true",
                    help="[C] apaga la regla V2 (recuento real de fotogramas con "
                         "`ffprobe -count_frames`, que DECODIFICA el video "
                         "entero: el 36 %% de la suite de fidelidad). Con el "
                         "interruptor apagado V2 se declara NO CUBIERTA")
    ap.add_argument("--json", action="store_true",
                    help="vuelca el resultado completo en JSON (hallazgos, "
                         "cobertura y tiempos por punto y por regla)")
    a = ap.parse_args(argv)
    v2(not a.sin_v2)
    censo = json.load(open(a.censo, encoding="utf-8")) if a.censo else None

    if a.censar:
        print(json.dumps(censar(a.censar), ensure_ascii=False, indent=1))
        return 0
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
                          a.motor, alfa=a.alfa, censo=t.get("censo", censo))
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
        r = verificar(a.salida, pedido, a.entrada, a.motor, alfa=a.alfa,
                      censo=censo)
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
    if r.get("punto1"):
        # las CUATRO respuestas del punto 1 (F1): evaluado / familia (el marcador
        # es de familia, no de formato) / no_aplica (el formato no tiene marcador)
        # / sin_vocabulario (deuda nuestra).
        print("  punto 1: %s" % r["punto1"])
    cob = r.get("cobertura") or {}
    sin = [k for k, v in cob.items() if not v]
    print("  cobertura: %s%s" % ("completa" if cob and not sin else
                                 ("sin reglas aplicables" if not cob else "PARCIAL"),
                                 (" (sin cubrir: %s)" % ", ".join(sin)) if sin else ""))
    print("  ms: %s" % {k: round(v, 3) for k, v in r["ms"].items()})


if __name__ == "__main__":
    sys.exit(main())
