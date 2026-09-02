# -*- coding: utf-8 -*-
"""Prepara las FUENTES que el corpus no tiene (webm, mov, avi, m4a, opus, ogg).

Esto NO es el sondeo: es preparación de material. Se hace con `ffmpeg` directo
y a propósito, para que el sondeo de una arista no dependa de que otra arista
del mismo lote haya salido bien (si `wav→ogg` fallara, no habría fuente `.ogg`
y 5 aristas más se caerían por un motivo que no es el suyo).

Todas las fuentes de VÍDEO derivan de `corpus/video/patologico_2pistas.mkv`,
que lleva **dos pistas de audio**: así cada arista de vídeo sondeada puede
comprobar de paso que `-map 0` sigue conservando la segunda.

Uso:  python bench/salidas-sondeo-ff/preparar_fuentes.py <dir_destino>
"""
import hashlib
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MKV = os.path.join(RAIZ, "corpus", "video", "patologico_2pistas.mkv")
WAV = os.path.join(RAIZ, "corpus", "audio", "trivial.wav")
FLAC = os.path.join(RAIZ, "corpus", "audio", "tipico.flac")
MP3 = os.path.join(RAIZ, "corpus", "audio", "tipico.mp3")

BASE = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-threads", "4"]


def receta(dst):
    """{extension: (argv, origen)} — argv completo, reproducible."""
    return {
        "mp4": (BASE + ["-i", MKV, "-map", "0", "-c", "copy",
                        "-f", "mp4", os.path.join(dst, "f.mp4")], MKV),
        "mov": (BASE + ["-i", MKV, "-map", "0", "-c", "copy",
                        "-f", "mov", os.path.join(dst, "f.mov")], MKV),
        # AVI, primer intento: `-c:v copy -c:a libmp3lame`. **Falla**, y el
        # motivo es del contenedor, no de la invocación: el H.264 que sale de
        # un MKV viene en formato AVCC y el índice clásico de AVI exige
        # Annex B — «Error writing trailer: Invalid data found». Se escribe el
        # AVI canónico (MPEG-4 parte 2 + MP3), que además es lo que un `.avi`
        # de verdad lleva dentro. Siguen siendo DOS pistas de audio, que es lo
        # que hace falta para vigilar `-map 0`.
        "avi": (BASE + ["-i", MKV, "-map", "0", "-c:v", "mpeg4", "-q:v", "5",
                        "-c:a", "libmp3lame", "-b:a", "128k",
                        "-f", "avi", os.path.join(dst, "f.avi")], MKV),
        "webm": (BASE + ["-i", MKV, "-map", "0", "-c:v", "libvpx-vp9",
                         "-crf", "40", "-b:v", "0", "-row-mt", "1",
                         "-deadline", "realtime", "-cpu-used", "8",
                         "-c:a", "libopus", "-b:a", "96k",
                         "-f", "webm", os.path.join(dst, "f.webm")], MKV),
        "m4a": (BASE + ["-i", WAV, "-vn", "-c:a", "aac", "-b:a", "192k",
                        "-f", "ipod", os.path.join(dst, "f.m4a")], WAV),
        "opus": (BASE + ["-i", WAV, "-vn", "-c:a", "libopus", "-b:a", "192k",
                         os.path.join(dst, "f.opus")], WAV),
        "ogg": (BASE + ["-i", WAV, "-vn", "-c:a", "libvorbis", "-b:a", "192k",
                        os.path.join(dst, "f.ogg")], WAV),
    }


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    dst = os.path.abspath(sys.argv[1])
    os.makedirs(dst, exist_ok=True)
    fuentes = {"mkv": MKV, "wav": WAV, "flac": FLAC, "mp3": MP3}
    meta = {}
    for ext, (argv, origen) in receta(dst).items():
        salida = argv[-1]
        r = subprocess.run(argv, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, errors="replace", timeout=600, cwd=dst)
        if r.returncode != 0 or not os.path.isfile(salida):
            print("FALLO fuente", ext, r.returncode, r.stderr[-400:])
            sys.exit(1)
        fuentes[ext] = salida
        meta[ext] = {"argv": argv, "origen": origen,
                     "bytes": os.path.getsize(salida), "sha256": sha(salida)}
    for ext in ("mkv", "wav", "flac", "mp3"):
        meta[ext] = {"argv": None, "origen": fuentes[ext],
                     "bytes": os.path.getsize(fuentes[ext]),
                     "sha256": sha(fuentes[ext])}
    with open(os.path.join(dst, "fuentes.json"), "w", encoding="utf-8") as fh:
        json.dump({"fuentes": fuentes, "meta": meta}, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: meta[k]["bytes"] for k in sorted(meta)}, indent=1))


if __name__ == "__main__":
    main()
