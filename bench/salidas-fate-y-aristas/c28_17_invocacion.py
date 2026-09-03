# -*- coding: utf-8 -*-
"""C28 -- los 17 de 23 "con invocacion mejor" que seguian sin probar
(bench/firmas-cierre.md 4.4, clase EINVAL+EXPERIMENTAL+INVALIDDATA=23, de los
que 6 ya se habian escrito de verdad: h261, h263, dnxhd, dts, mlp, thd).
Quedan 15 EINVAL + 2 INVALIDDATA = 17: '302' amv avs2 chk dnxhr gxf js mmf
rco roq sup tco tun vbn xface dv flm.

Mismo metodo que _c28_prueba21.py: DOS semillas por celda, se ESCRIBE de
verdad (no se deduce), y se guarda el prefijo comun si las dos escriben.
La diferencia es que aqui la restriccion de cada formato no estaba en el
censo (truncado a etiquetas de rc): se sondeo en ejecucion con
`ffmpeg -h muxer=X` / `-h encoder=X` (bench/oraculo-y-gotenberg.md ya establecio
la disciplina de sondear, no deducir) antes de escribir este script.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-fate-y-aristas/c28_17_invocacion.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FFMPEG = r"D:\utils\ffmpeg\bin\ffmpeg.exe"
TIMEOUT = 60
SAL = os.path.dirname(os.path.abspath(__file__))


def rc_firmado(rc: int) -> int:
    return rc - 2**32 if rc >= 2**31 else rc


FUENTES = {
    "video": [
        ("v1", ["-f", "lavfi", "-i", "testsrc=size={s}:rate={r}:duration=0.6"]),
        ("v2", ["-f", "lavfi", "-i", "smptebars=size={s}:rate={r}:duration=0.9"]),
    ],
    "audio": [
        ("a1", ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.6"]),
        ("a2", ["-f", "lavfi", "-i", "anoisesrc=color=white:seed=7:duration=0.9"]),
    ],
    "imagen": [
        ("i1", ["-f", "lavfi", "-i", "testsrc=size={s}:rate=1:duration=1", "-frames:v", "1"]),
        ("i2", ["-f", "lavfi", "-i", "smptebars=size={s}:rate=1:duration=1", "-frames:v", "1"]),
    ],
    "subtitulo": [
        ("s1", ["-i", "__SRT1__"]),
        ("s2", ["-i", "__SRT2__"]),
    ],
}

# (formato, modo, [args de codificacion], nota)
# Cada fix de abajo salio de sondear en ejecucion, no de deducir: el mensaje
# EXACTO de ffmpeg (a veces tras 2-4 intentos, cuando el propio ffmpeg iba
# revelando una restriccion nueva a cada paso -- "debe ser exactamente 6
# canales", luego "a 96000 Hz", por ejemplo en `302`). Se documenta la cadena
# completa en el informe; aqui solo queda la invocacion que ya funciona.
CASOS = [
    ("302", "audio", ["-c:a", "pcm_s24daud", "-ar", "96000", "-ac", "6"],
     "daud: EXACTAMENTE 6 canales a 96000 Hz (dos restricciones encadenadas)"),
    ("amv", "video+audio", ["-s", "160x120", "-r", "25", "-strict", "-2",
                            "-block_size", "882", "-ar", "22050"],
     "amv: audio a 22050 Hz (en la fuente) + -strict -2 + -block_size 882 "
     "(el propio ffmpeg lo sugiere: 'Try -block_size 882')"),
    ("avs2", "video", ["-s", "320x240", "-r", "25", "-an"],
     "avs2: video puro, sin pista de audio (el muxer no admite audio)"),
    ("dnxhr", "video", ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq",
                        "-s", "1920x1080", "-pix_fmt", "yuv422p", "-r", "25"],
     "dnxhr: perfil DNxHR explicito + yuv422p"),
    ("gxf", "video+audio", ["-s", "720x576", "-r", "25", "-pix_fmt", "yuv420p",
                            "-c:v", "mpeg2video", "-ar", "48000", "-c:a", "pcm_s16le"],
     "gxf: geometria PAL + mpeg2video/pcm_s16le explicitos"),
    ("mmf", "audio", ["-ar", "44100"],
     "mmf: 44100 Hz explicito (el ruido de la segunda semilla nace a 48000, "
     "que mmf rechaza; la sonda de 440 Hz ya nacia a 44100 y coincidia por suerte)"),
    ("rco", "audio", ["-c:a", "g723_1", "-ar", "8000", "-ac", "1"],
     "g723_1: 8000 Hz (mismo fix de C25, ronda 9)"),
    ("roq", "video", ["-c:v", "roqvideo", "-pix_fmt", "yuvj444p", "-s", "320x240", "-r", "25"],
     "roq VIDEO: yuvj444p explicito (el audio roq_dpcm@22050 ya se fijo en C25)"),
    ("tco", "audio", ["-c:a", "g723_1", "-ar", "8000", "-ac", "1"],
     "g723_1: 8000 Hz (mismo fix de C25, ronda 9)"),
    ("tun", "audio", ["-ar", "22050"],
     "alp/tun: 22050 Hz exacto (\"Sample rate must be 22050 for TUN files\")"),
    ("vbn", "imagen", ["-c:v", "vbn", "-pix_fmt", "rgba"],
     "vbn: codec y pix_fmt explicitos (image2 adivinaba mal)"),
    ("xface", "imagen", ["-c:v", "xface", "-s", "48x48", "-pix_fmt", "monow"],
     "xface: 48x48 fijo + monow (el encoder solo admite ese pix_fmt)"),
    ("dv", "video+audio", ["-s", "720x480", "-r", "30000/1001", "-pix_fmt", "yuv411p",
                           "-c:v", "dvvideo", "-ar", "48000", "-ac", "2"],
     "dv: NTSC 720x480@29.97 yuv411p"),
    ("flm", "imagen", ["-pix_fmt", "rgba"],
     "filmstrip: rgba explicito (rawvideo por defecto, sin restriccion de tamano)"),
]

# Sin invocacion que probar: el propio ffmpeg de esta build no trae el
# encoder, verificado con `-h encoder=X` (misma clase que
# AVERROR_ENCODER_NOT_FOUND, aunque el rc que guardo el censo fuera EINVAL).
SIN_ENCODER = {
    "js": "jacosub: `-h encoder=jacosub` -> \"no encoders for it are available\"",
    "sup": "hdmv_pgs_subtitle: `-h encoder=hdmv_pgs_subtitle` -> \"no encoders for it are available\"",
}

# webm_chunk (chk) exige un protocolo de fragmentacion (chunk_start_index,
# fichero de cabecera aparte) -- no es una invocacion de UN fichero, es una
# forma de invocacion distinta. Se declara aparte, no se fuerza.
OTRO_PARADIGMA = {
    "chk": "webm_chunk: exige fragmentar en varios ficheros con "
          "chunk_start_index/header -- no es 'una bandera', es otro modo de escritura",
}


def escribir_subtitulo(ruta: str, texto: str) -> None:
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(texto)


def prefijo_comun(cabs):
    n = min(len(c) for c in cabs)
    i = 0
    while i < n and len({c[i] for c in cabs}) == 1:
        i += 1
    return cabs[0][:i]


def construir_fuente(modo, plantilla, tmp, tag):
    if modo == "subtitulo":
        srt1 = os.path.join(tmp, "sub1.srt")
        srt2 = os.path.join(tmp, "sub2.srt")
        escribir_subtitulo(srt1, "1\n00:00:00,000 --> 00:00:02,000\nFILEX C28\n\n")
        escribir_subtitulo(srt2, "1\n00:00:00,000 --> 00:00:01,500\nSEGUNDA\n\n"
                                 "2\n00:00:01,500 --> 00:00:03,000\nSEMILLA\n\n")
        return [srt1 if "__SRT1__" in a else srt2 if "__SRT2__" in a else a
                for a in plantilla]
    return [a.format(s="320x240", r="25") if isinstance(a, str) else a for a in plantilla]


def main():
    tmp = os.path.join(SAL, "tmp17")
    os.makedirs(tmp, exist_ok=True)
    antes = sorted(os.listdir(tmp))
    resultados = []

    for fmt, modo, cod, nota in CASOS:
        modos = ["video", "audio"] if modo == "video+audio" else [modo]
        celdas, cabs = [], []
        for sufijo, plantilla in FUENTES[modos[0]]:
            fuente = []
            for m in modos:
                # para video+audio, empareja v1/a1 y v2/a2 por indice
                idx = 0 if sufijo.endswith("1") else 1
                fuente += construir_fuente(m, FUENTES[m][idx][1], tmp, sufijo)
            sal = os.path.join(tmp, "%s_%s.%s" % (fmt, sufijo, fmt))
            argv = [FFMPEG, "-nostdin", "-y"] + fuente + cod + ["-t", "0.6", sal]
            try:
                p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                                   timeout=TIMEOUT)
                rc = rc_firmado(p.returncode)
                err = p.stderr.decode("utf-8", "replace")
            except subprocess.TimeoutExpired:
                rc, err = -9, "TIMEOUT"
            tam = os.path.getsize(sal) if os.path.exists(sal) else 0
            c = {"semilla": sufijo, "rc": rc, "bytes": tam}
            if tam > 0:
                with open(sal, "rb") as fh:
                    cabs.append(fh.read(64))
            else:
                c["stderr"] = err.strip().splitlines()[-1][:200] if err.strip() else ""
            celdas.append(c)
        fila = {"formato": fmt, "nota": nota, "argv_cod": cod, "celdas": celdas,
                "escrito": len(cabs), "buena": len(cabs) == 2}
        if len(cabs) == 2:
            p = prefijo_comun(cabs)
            fila["prefijo_comun_n"] = len(p)
            fila["prefijo_comun_hex"] = p.hex()
        resultados.append(fila)
        print("%-8s escrito=%d/2  %s" % (fmt, len(cabs), nota))

    for fmt, motivo in SIN_ENCODER.items():
        resultados.append({"formato": fmt, "nota": motivo, "escrito": 0, "buena": False,
                           "clase_real": "AVERROR_ENCODER_NOT_FOUND (mal clasificado como EINVAL)"})
        print("%-8s SIN ENCODER en esta build -- %s" % (fmt, motivo))
    for fmt, motivo in OTRO_PARADIGMA.items():
        resultados.append({"formato": fmt, "nota": motivo, "escrito": 0, "buena": False,
                           "clase_real": "otro paradigma de invocacion, no una bandera"})
        print("%-8s OTRO PARADIGMA -- %s" % (fmt, motivo))

    despues = sorted(os.listdir(tmp))
    buenas = sum(1 for r in resultados if r.get("buena"))
    salida = {"desechable_antes": antes, "desechable_despues": despues,
              "n_total": len(resultados), "n_buenas": buenas, "resultados": resultados}
    with open(os.path.join(SAL, "c28_17_resultado.json"), "w", encoding="utf-8") as fh:
        json.dump(salida, fh, indent=1, ensure_ascii=False)
    print("\n%d/%d escritas con exito (2/2 semillas)" % (buenas, len(resultados)))

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
