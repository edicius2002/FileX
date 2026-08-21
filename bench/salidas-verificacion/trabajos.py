#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tabla de trabajos: las 53 salidas del patron oro con su entrada y su PEDIDO.

El 'pedido' es lo que el usuario solicito de verdad. Sin el, el punto 4 del
contrato (pedido frente a obtenido) no se puede evaluar: toda diferencia
parece una transformacion no solicitada.

Derivado de bench/salidas-referencia/referencia.json -> 'ordenes' (39) y, para
las 14 salidas sin orden explicita, del convenio de nombres
    <base>_<extorigen>-to[-variante].<extdestino>
"""
import json
import os

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(RAIZ, "bench", "salidas-referencia")


def r(*p):
    return os.path.join(RAIZ, *p)


C_IMG = ("corpus", "imagen")
C_AUD = ("corpus", "audio")
C_VID = ("corpus", "video")
C_PDF = ("corpus", "pdf")
C_DAT = ("corpus", "datos")

# (subdir_salida, nombre, entrada, params, esperado)
#   esperado: "ok" (correcta por construccion) | "fallo" (contraejemplo
#   deliberado del patron oro) | "aviso" (decision discutible del motor)
TABLA = [
    # ---- audio -----------------------------------------------------------
    ("audio", "tipico_flac-to.mp3", r(*C_AUD, "tipico.flac"), {"bitrate_bps": 192000}, "ok"),
    ("audio", "tipico_flac-to.opus", r(*C_AUD, "tipico.flac"), {"bitrate_bps": 96000}, "ok"),
    ("audio", "tipico_flac-to.wav", r(*C_AUD, "tipico.flac"), {}, "ok"),
    ("audio", "tipico_mp3-to.flac", r(*C_AUD, "tipico.mp3"), {}, "ok"),
    ("audio", "tipico_mp3-to.wav", r(*C_AUD, "tipico.mp3"), {}, "ok"),
    ("audio", "tipico_mp4-audio-copy.m4a", r(*C_VID, "tipico.mp4"), {"solo_audio": True}, "ok"),
    ("audio", "tipico_mp4-audio.flac", r(*C_VID, "tipico.mp4"), {"solo_audio": True}, "ok"),
    ("audio", "tipico_mp4-audio.mp3", r(*C_VID, "tipico.mp4"),
     {"solo_audio": True, "bitrate_bps": 192000}, "ok"),
    ("audio", "trivial_wav-to.flac", r(*C_AUD, "trivial.wav"), {}, "ok"),
    ("audio", "trivial_wav-to.m4a", r(*C_AUD, "trivial.wav"), {"bitrate_bps": 192000}, "ok"),
    ("audio", "trivial_wav-to.mp3", r(*C_AUD, "trivial.wav"), {"bitrate_bps": 192000}, "ok"),
    ("audio", "trivial_wav-to.opus", r(*C_AUD, "trivial.wav"), {"bitrate_bps": 96000}, "ok"),
    # ---- datos -----------------------------------------------------------
    ("datos", "patologico_bom_csv-to-normalizado.csv", r(*C_DAT, "patologico_bom.csv"), {}, "ok"),
    ("datos", "patologico_bom_csv-to.json", r(*C_DAT, "patologico_bom.csv"), {}, "ok"),
    ("datos", "tipico_json-to.csv", r(*C_DAT, "tipico.json"), {}, "ok"),
    # ---- imagen ----------------------------------------------------------
    ("imagen", "16bit_tif-to-d16.png", r(*C_IMG, "patologico_16bit.tif"),
     {"profundidad_bits": 16}, "ok"),
    ("imagen", "16bit_tif-to-d8.png", r(*C_IMG, "patologico_16bit.tif"),
     {"profundidad_bits": 8}, "ok"),
    ("imagen", "16bit_tif-to-default.png", r(*C_IMG, "patologico_16bit.tif"), {}, "ok"),
    ("imagen", "16bit_tif-to.jpg", r(*C_IMG, "patologico_16bit.tif"), {}, "ok"),
    ("imagen", "16bit_tif-to.webp", r(*C_IMG, "patologico_16bit.tif"), {}, "ok"),
    ("imagen", "alpha_png-to-flat.jpg", r(*C_IMG, "alpha.png"), {"fondo": "white"}, "ok"),
    ("imagen", "alpha_png-to.avif", r(*C_IMG, "alpha.png"), {}, "ok"),
    ("imagen", "alpha_png-to.jpg", r(*C_IMG, "alpha.png"), {}, "aviso"),
    ("imagen", "alpha_png-to.png8.png", r(*C_IMG, "alpha.png"), {"profundidad_bits": 8}, "ok"),
    ("imagen", "alpha_png-to.webp", r(*C_IMG, "alpha.png"), {}, "ok"),
    ("imagen", "tipico_jpg-to.png", r(*C_IMG, "tipico.jpg"), {}, "ok"),
    ("imagen", "tipico_png-to.avif", r(*C_IMG, "tipico.png"), {}, "ok"),
    ("imagen", "tipico_png-to.jpg", r(*C_IMG, "tipico.png"), {}, "ok"),
    ("imagen", "tipico_png-to.webp", r(*C_IMG, "tipico.png"), {}, "ok"),
    ("imagen", "tipico_webp-to.jpg", r(*C_IMG, "tipico.webp"), {}, "ok"),
    ("imagen", "tipico_webp-to.png", r(*C_IMG, "tipico.webp"), {}, "ok"),
    ("imagen", "trivial_png-to-lossless.webp", r(*C_IMG, "trivial.png"), {}, "ok"),
    ("imagen", "trivial_png-to.jpg", r(*C_IMG, "trivial.png"), {}, "ok"),
    ("imagen", "trivial_png-to.webp", r(*C_IMG, "trivial.png"), {}, "ok"),
    # ---- pdf y rasterizados ---------------------------------------------
    ("pdf", "alpha_png-to.pdf", r(*C_IMG, "alpha.png"), {}, "ok"),
    ("pdf", "patologico_escaneado_pdf-to-p1.png", r(*C_PDF, "patologico_escaneado.pdf"),
     {"dpi": 150}, "ok"),
    ("pdf", "tipico_jpg-to.pdf", r(*C_IMG, "tipico.jpg"), {}, "aviso"),
    ("pdf", "tipico_png-to-150dpi.pdf", r(*C_IMG, "tipico.png"), {"dpi": 150}, "ok"),
    ("pdf", "tipico_png-to.pdf", r(*C_IMG, "tipico.png"), {}, "aviso"),
    ("pdf", "tipico_texto_pdf-to-gs.pdf", r(*C_PDF, "tipico_texto.pdf"), {}, "ok"),
    ("pdf", "tipico_texto_pdf-to-p1.jpg", r(*C_PDF, "tipico_texto.pdf"), {"dpi": 150}, "ok"),
    ("pdf", "tipico_texto_pdf-to-p1.png", r(*C_PDF, "tipico_texto.pdf"), {"dpi": 150}, "ok"),
    ("pdf", "tipico_texto_pdf-to.tif", r(*C_PDF, "tipico_texto.pdf"), {"dpi": 150}, "ok"),
    ("pdf", "tipico_texto_rasterizado.pdf",
     os.path.join(REF, "pdf", "tipico_texto_pdf-to-p1.png"), {}, "ok"),
    ("pdf", "trivial_pdf-to-p1.png", r(*C_PDF, "trivial.pdf"), {"dpi": 150}, "ok"),
    # ---- video -----------------------------------------------------------
    ("video", "2pistas_mkv-to-COPY.mp4", r(*C_VID, "patologico_2pistas.mkv"), {}, "ok"),
    # contraejemplo deliberado del patron oro: 'ffmpeg -i in.mkv out.mp4' sin
    # -map pierde la segunda pista de audio. DEBE dar fallo.
    ("video", "2pistas_mkv-to-DEFAULT.mp4", r(*C_VID, "patologico_2pistas.mkv"), {}, "fallo"),
    ("video", "2pistas_mkv-to-MAP0.mp4", r(*C_VID, "patologico_2pistas.mkv"), {}, "ok"),
    ("video", "tipico_mp4-to.mkv", r(*C_VID, "tipico.mp4"), {}, "ok"),
    ("video", "tipico_mp4-to.webm", r(*C_VID, "tipico.mp4"), {}, "ok"),
    ("video", "trivial_mp4-to-naive.gif", r(*C_VID, "trivial.mp4"),
     {"escala": 320, "fps": 12}, "aviso"),
    ("video", "trivial_mp4-to-palette.gif", r(*C_VID, "trivial.mp4"),
     {"escala": 320, "fps": 12}, "ok"),
    ("video", "trivial_mp4-to.webm", r(*C_VID, "trivial.mp4"), {}, "ok"),
]

# categoria de coste (la del CORPUS, no la del contenedor de salida)
CATEGORIA = {"audio": "audio", "datos": "datos", "imagen": "imagen",
             "pdf": "pdf", "video": "video"}


def cargar_referencia():
    with open(os.path.join(REF, "referencia.json"), encoding="utf-8") as fh:
        return json.load(fh)


def trabajos():
    """Devuelve [{salida, entrada, pedido, cat, esperado}] para las 53 salidas."""
    ref = cargar_referencia()
    # caracterizacion de la entrada que SI exige decodificar pixeles y que un
    # orquestador real calcularia una sola vez por entrada (alfa no trivial).
    extra = {}
    for c in ref["corpus"]:
        extra[os.path.normcase(c["ruta"])] = {
            k: c[k] for k in ("alfa_no_trivial", "tiene_alfa", "colores_unicos")
            if k in c}
    for s in ref["salidas"]:
        extra[os.path.normcase(s["ruta"])] = {
            k: s[k] for k in ("alfa_no_trivial", "tiene_alfa", "colores_unicos")
            if k in s}
    out = []
    for sub, nombre, entrada, params, esperado in TABLA:
        out.append({
            "salida": os.path.join(REF, sub, nombre),
            "entrada": entrada,
            "cat": CATEGORIA[sub],
            "esperado": esperado,
            "pedido": {"destino": os.path.splitext(nombre)[1].lstrip(".").lower(),
                       "params": params},
            "extra_entrada": extra.get(os.path.normcase(entrada), {}),
        })
    return out


if __name__ == "__main__":
    t = trabajos()
    print("%d trabajos" % len(t))
    faltan = [x["salida"] for x in t if not os.path.exists(x["salida"])] + \
             [x["entrada"] for x in t if not os.path.exists(x["entrada"])]
    print("faltan:", sorted(set(faltan)) or "ninguno")
