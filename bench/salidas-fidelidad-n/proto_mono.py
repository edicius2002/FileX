# -*- coding: utf-8 -*-
"""¿Aguanta el grafo lo que hay DE VERDAD en las 53? Mono, vídeo con audio y
una entrada a 44,1 kHz contra una salida a 48 kHz (Opus, trampa 3).

El corpus de calibración de N16 es estéreo fabricado; **las 17 salidas con
audio del patrón oro son casi todas mono**, así que un grafo que solo funcione
con estéreo no sirve de nada aunque la señal separe.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, AQUI)
from a7_grafo import GRAFO  # noqa: E402

CORPUS = os.path.join(RAIZ, "corpus")


def ff(argv):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + argv,
                          capture_output=True, timeout=300,
                          stdin=subprocess.DEVNULL)


def grafo(entrada, salida, sr):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", entrada, "-i", salida,
         "-filter_complex", GRAFO.format(sr=sr), "-map", "[m]", "-f", "null", "-"],
        capture_output=True, timeout=300, stdin=subprocess.DEVNULL)
    err = (r.stderr or b"").decode("utf-8", "replace")
    v = []
    for l in err.splitlines():
        l = l.split("] ", 1)[-1].strip()
        if l.startswith("RMS level dB:"):
            t = l.split(":", 1)[1].strip().lower()
            v.append(-math.inf if t.startswith("-inf") else float(t))
    return r.returncode, v, err[-300:]


def r_de(v):
    n = len(v) // 3
    out = []
    for k in range(n):
        Re = 0.0 if v[k] == -math.inf else 10 ** (v[k] / 20)
        Rs = 0.0 if v[n + k] == -math.inf else 10 ** (v[n + k] / 20)
        Rd = 0.0 if v[2 * n + k] == -math.inf else 10 ** (v[2 * n + k] / 20)
        out.append(0.0 if not Re or not Rs
                   else (Re * Re + Rs * Rs - Rd * Rd) / (2 * Re * Rs))
    return out


d = tempfile.mkdtemp(prefix="filex-proto-mono-")
casos = []

flac = os.path.join(CORPUS, "audio", "tipico.flac")
mp4 = os.path.join(CORPUS, "video", "tipico.mp4")

# 1. mono FLAC 44,1k -> mp3 192k (una de las 53)
o1 = os.path.join(d, "a.mp3")
ff(["-i", flac, "-c:a", "libmp3lame", "-b:a", "192k", o1])
casos.append(("mono flac->mp3 192k, sr=44100", flac, o1, 44100))

# 2. mono FLAC 44,1k -> opus 96k (48 kHz forzados: la trampa 3)
o2 = os.path.join(d, "a.opus")
ff(["-i", flac, "-c:a", "libopus", "-b:a", "96k", o2])
casos.append(("mono flac->opus 96k, sr=48000", flac, o2, 48000))
casos.append(("  (el mismo, con sr=44100)", flac, o2, 44100))

# 3. vídeo con audio -> m4a (otra de las 53)
o3 = os.path.join(d, "a.m4a")
ff(["-i", mp4, "-vn", "-c:a", "copy", o3])
casos.append(("mp4 -> m4a copy, sr=44100", mp4, o3, 44100))

# 4. el fallo que la regla persigue, sobre MONO: no existe canal que perder.
o4 = os.path.join(d, "silencio.mp3")
ff(["-i", flac, "-af", "volume=0", "-c:a", "libmp3lame", "-b:a", "192k", o4])
casos.append(("mono -> mp3 SILENCIADO ENTERO", flac, o4, 44100))

for etiqueta, e, s, sr in casos:
    rc, v, err = grafo(e, s, sr)
    if not v or len(v) % 3:
        print("%-38s rc=%d  MAL: %d valores\n    %s" % (etiqueta, rc, len(v), err))
        continue
    print("%-38s rc=%d  n_canales=%d  RMS=%s  r=%s"
          % (etiqueta, rc, len(v) // 3, [round(x, 2) if x != -math.inf else "-inf"
                                         for x in v],
             [round(x, 4) for x in r_de(v)]))

shutil.rmtree(d, ignore_errors=True)
