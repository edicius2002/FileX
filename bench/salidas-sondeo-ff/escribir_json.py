# -*- coding: utf-8 -*-
"""Convierte `resultados.json` (el crudo del sondeo) en `filex/sondeo/ffmpeg.json`.

El fichero que consume `filex/sondeo.py` lleva **solo** lo que ese módulo lee:
`estado`, `ms` y `motivo`. Se añade `causa` —una palabra— porque es la
distinción que pedía el encargo (build / parametrización / verificador / motor)
y `sondeo.aplicar` ignora las claves que no conoce.

Uso:  python bench/salidas-sondeo-ff/escribir_json.py <dir_trabajo>
"""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESTINO = os.path.join(RAIZ, "filex", "sondeo", "ffmpeg.json")
INFORME = "bench/sondeo-ffmpeg.md"
FECHA = "2026-08-22"


#: Un motivo de UNA línea, sin `stderr` crudo (R: «nunca devolver `stderr`
#: crudo al modelo»). Cada uno nombra la causa exacta, no el síntoma.
MOTIVO_MOV = ("rc=0 y el fichero es correcto para ffprobe (1 video + 2 audio); "
              "el contrato dicta fallo porque la sonda EN PROCESO lee 0 pistas "
              "en todo .mov: QuickTime pone un segundo hdlr ('url ') dentro de "
              "minf y _isobmff se queda con el ultimo")
MOTIVO_OGG = ("rc=0 y el fichero es correcto para ffprobe; el contrato dicta "
              "fallo porque la sonda EN PROCESO divide el granulo de Vorbis "
              "por 48 kHz fijos y la duracion sale x0,91875 (8,000 s -> 7,350)")
MOTIVO_M4A = ("rc=0 y el fichero es correcto para ffprobe (10,031 s); el "
              "contrato dicta fallo porque la sonda EN PROCESO no lee el elst "
              "y cuenta la trama de priming del AAC: 10,054 s, +31 ms sobre "
              "una tolerancia de 23,2 ms")
MOTIVO_GIF = ("rc=3165764104 (AVERROR_ENCODER_NOT_FOUND): el muxer gif no "
              "tiene codec de audio y `-map 0` arrastra las pistas de audio "
              "de la entrada; con `-map 0:v:0` la arista funciona")


def motivo_de(clave, causa, v):
    d = clave.split(">")[1]
    if d == "gif":
        return MOTIVO_GIF
    if d == "mov":
        return MOTIVO_MOV
    if d == "ogg" or clave.startswith("ogg>"):
        return MOTIVO_OGG
    if causa == "verificador_tolerancia":
        return MOTIVO_M4A
    return (v.get("motivo") or "")[:220]


def main():
    trabajo = os.path.abspath(sys.argv[1])
    with open(os.path.join(trabajo, "resultados.json"), encoding="utf-8") as fh:
        crudo = json.load(fh)
    rep, gif = {}, {}
    p = os.path.join(trabajo, "reparacion.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as fh:
            rep = json.load(fh)
    p = os.path.join(trabajo, "gif.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as fh:
            gif = json.load(fh)

    tabla = {}
    for clave, v in crudo["aristas"].items():
        if v["estado"] == "real":
            tabla[clave] = {"estado": "real", "ms": v["ms"]}
            continue
        d = v.get("diagnostico") or {}
        ff = d.get("ffprobe") or {}
        r = rep.get(clave) or {}
        if d.get("rc") not in (0, None) or not ff.get("existe"):
            causa = "parametrizacion"          # el motor no llegó a escribir
        elif r.get("recuperada"):
            causa = "verificador"              # el fichero es bueno; la sonda no
        else:
            causa = "verificador_tolerancia"   # ni rc ni fichero: el umbral
        tabla[clave] = {"estado": "nominal",
                        "motivo": motivo_de(clave, causa, v),
                        "causa": causa}

    # `mp4>gif` NO estaba en las 70: el catálogo lo declara `real` desde
    # `referencia.json:vid.2gif.paleta`. **Está refutado** — MEDIDO: la
    # referencia usó `trivial.mp4`, que NO tiene pista de audio, y con
    # cualquier MP4 que sí la tenga `-map 0` arrastra el audio a un muxer que
    # no tiene códec de audio y ffmpeg aborta con AVERROR_ENCODER_NOT_FOUND.
    # 5 de 5 aristas vídeo→gif fallan con el código de hoy.
    a = (gif.get("A_hoy") or {}).get("mp4>gif")
    if a and a["estado"] == "nominal":
        tabla["mp4>gif"] = {
            "estado": "nominal",
            "motivo": MOTIVO_GIF,
            "causa": "parametrizacion",
        }
    salida = {
        "motor": "ffmpeg",
        "build": crudo["build"],
        "fecha": FECHA,
        "informe": INFORME,
        "aristas": dict(sorted(tabla.items())),
    }
    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    r = sum(1 for x in tabla.values() if x["estado"] == "real")
    print("escritas %d aristas: %d real, %d nominal -> %s"
          % (len(tabla), r, len(tabla) - r, DESTINO))


if __name__ == "__main__":
    main()
