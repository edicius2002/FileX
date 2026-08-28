# -*- coding: utf-8 -*-
"""Prototipo: ¿se puede sacar la correlación por canal con UNA orden de ffmpeg?

`filex` **no tiene dependencias** y es una decisión escrita en `pyproject.toml`
(*«añadir una dependencia aquí obliga a justificar por qué no se puede hacer en
proceso»*), así que la vía de N16 —numpy, FFT y correlación en Python— **no es
aplicable tal cual**. Esto sondea la alternativa antes de escribir una línea de
producción: la identidad

    RMS(x−y)² = RMS(x)² + RMS(y)² − 2·cov(x,y)

convierte tres RMS en una correlación, y los tres RMS los da `astats` en una
sola pasada sobre un grafo que ffmpeg evalúa en C.
"""
import math
import os
import subprocess
import sys
import tempfile

SR = 48000


def ff(argv, **kw):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + argv,
                          capture_output=True, timeout=300,
                          stdin=subprocess.DEVNULL, **kw)


GRAFO = (
    "[0:a]aresample={sr},aformat=sample_fmts=fltp:channel_layouts={lay},"
    "asplit=2[e1][e2];"
    "[1:a]aresample={sr},aformat=sample_fmts=fltp:channel_layouts={lay},"
    "asplit=2[s1][s2];"
    # `amix=...:weights=1 -1` NO resta: sobre dos FLAC idénticos daba
    # RMS(dif) = 2·RMS(x) (medido en la primera pasada de este prototipo), es
    # decir la SUMA. La negación explícita con `volume=-1` sí resta.
    "[e2]volume=-1[en];"
    "[s2][en]amix=inputs=2:normalize=0:duration=shortest:dropout_transition=0[d];"
    "[e1][s1][d]amerge=inputs=3,"
    "astats=measure_overall=none:measure_perchannel=RMS_level[m]"
)


def rms_por_canal(entrada, salida, lay="stereo"):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", entrada, "-i", salida,
         "-filter_complex", GRAFO.format(sr=SR, lay=lay),
         "-map", "[m]", "-f", "null", "-"],
        capture_output=True, timeout=300, stdin=subprocess.DEVNULL)
    err = (r.stderr or b"").decode("utf-8", "replace")
    vals = []
    for l in err.splitlines():
        l = l.split("] ", 1)[-1].strip()
        if l.startswith("RMS level dB:"):
            t = l.split(":", 1)[1].strip().lower()
            vals.append(-math.inf if t.startswith("-inf") else float(t))
    return r.returncode, vals, err[-400:]


d = tempfile.mkdtemp(prefix="filex-proto-")
CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "corpus", "audio")
jfk = os.path.join(CORPUS, "habla_jfk.flac")
src = os.path.join(d, "src.wav")
ff(["-i", jfk, "-filter_complex",
    "[0:a]pan=mono|c0=c0,atrim=0:8,asplit=2[a][b];"
    "[b]adelay=17|17,lowpass=f=3000[r];[a][r]join=inputs=2:"
    "channel_layout=stereo", "-t", "8", "-ar", str(SR),
    "-c:a", "pcm_s16le", src])
malo = os.path.join(d, "malo.wav")
ff(["-i", src, "-af", "pan=stereo|c0=c0|c1=0*c0", "-c:a", "pcm_s16le", malo])

for etiqueta, org, av, ext in (
        ("BUENA flac", src, ["-c:a", "flac"], "flac"),
        ("MALA  flac", malo, ["-c:a", "flac"], "flac"),
        ("BUENA mp3 192k", src, ["-c:a", "libmp3lame", "-b:a", "192k"], "mp3"),
        ("MALA  mp3 192k", malo, ["-c:a", "libmp3lame", "-b:a", "192k"], "mp3"),
        ("BUENA opus 96k", src, ["-c:a", "libopus", "-b:a", "96k"], "opus"),
        ("MALA  opus 96k", malo, ["-c:a", "libopus", "-b:a", "96k"], "opus"),
        ("BUENA opus 6k", src, ["-c:a", "libopus", "-b:a", "6k"], "opus"),
        ("MALA  opus 6k", malo, ["-c:a", "libopus", "-b:a", "6k"], "opus")):
    dst = os.path.join(d, etiqueta.replace(" ", "_") + "." + ext)
    ff(["-i", org] + av + ["-ac", "2", dst])
    rc, v, err = rms_por_canal(src, dst)
    if len(v) != 6:
        print("%-16s rc=%d  NO SALEN 6 CANALES: %s\n   %s" % (etiqueta, rc, v, err))
        continue
    print("%-16s rc=%d  ent=%s  sal=%s  dif=%s" % (etiqueta, rc, v[0:2], v[2:4], v[4:6]))
    for k in (0, 1):
        Re, Rs, Rd = (10 ** (v[k] / 20), 10 ** (v[2 + k] / 20), 10 ** (v[4 + k] / 20))
        r = ((Re * Re + Rs * Rs - Rd * Rd) / (2 * Re * Rs)) if Re and Rs else 0.0
        print("      canal %d  r = %+.4f" % (k, r))

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)
