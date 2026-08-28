# -*- coding: utf-8 -*-
"""Diagnóstico: por qué el grafo falla, y qué variante aguanta mono, estéreo y
vídeo con audio. Sondear en ejecución, no deducir."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
CORPUS = os.path.join(RAIZ, "corpus")

VARIANTES = {
    "sin_layout":
        "[0:a]aresample={sr},aformat=sample_fmts=fltp,asplit=2[e1][e2];"
        "[1:a]aresample={sr},aformat=sample_fmts=fltp,asplit=2[s1][s2];"
        "[e2]volume=-1[en];"
        "[s2][en]amix=inputs=2:normalize=0:duration=shortest:dropout_transition=0[d];"
        "[e1][s1][d]amerge=inputs=3,"
        "astats=measure_overall=none:measure_perchannel=RMS_level[m]",
    "con_layout":
        "[0:a]aresample={sr},aformat=sample_fmts=fltp:channel_layouts={lay},"
        "asplit=2[e1][e2];"
        "[1:a]aresample={sr},aformat=sample_fmts=fltp:channel_layouts={lay},"
        "asplit=2[s1][s2];"
        "[e2]volume=-1[en];"
        "[s2][en]amix=inputs=2:normalize=0:duration=shortest:dropout_transition=0[d];"
        "[e1][s1][d]amerge=inputs=3,"
        "astats=measure_overall=none:measure_perchannel=RMS_level[m]",
    # Sin `amerge`: TRES astats, uno por rama, en la MISMA invocación. Cada
    # rama va a su propio `-f null`, y astats etiqueta por canal igual.
    "tres_astats":
        "[0:a]aresample={sr},aformat=sample_fmts=fltp,asplit=2[e1][e2];"
        "[1:a]aresample={sr},aformat=sample_fmts=fltp,asplit=2[s1][s2];"
        "[e2]volume=-1[en];"
        "[s2][en]amix=inputs=2:normalize=0:duration=shortest:dropout_transition=0[d];"
        "[e1]astats=measure_overall=none:measure_perchannel=RMS_level[a];"
        "[s1]astats=measure_overall=none:measure_perchannel=RMS_level[b];"
        "[d]astats=measure_overall=none:measure_perchannel=RMS_level[c]",
}


def ff(argv):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + argv,
                          capture_output=True, timeout=300,
                          stdin=subprocess.DEVNULL)


def correr(variante, entrada, salida, sr, lay):
    g = VARIANTES[variante].format(sr=sr, lay=lay)
    mapas = (["-map", "[a]", "-f", "null", "-", "-map", "[b]", "-f", "null", "-",
              "-map", "[c]", "-f", "null", "-"]
             if variante == "tres_astats" else
             ["-map", "[m]", "-f", "null", "-"])
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", entrada, "-i", salida,
         "-filter_complex", g] + mapas,
        capture_output=True, timeout=300, stdin=subprocess.DEVNULL)
    err = (r.stderr or b"").decode("utf-8", "replace")
    v = [l.split(":", 1)[1].strip()
         for l in (x.split("] ", 1)[-1].strip() for x in err.splitlines())
         if l.startswith("RMS level dB:")]
    return r.returncode, v, err


d = tempfile.mkdtemp(prefix="filex-diag-")
flac = os.path.join(CORPUS, "audio", "tipico.flac")
mp4 = os.path.join(CORPUS, "video", "tipico.mp4")
o_mono = os.path.join(d, "mono.mp3")
ff(["-i", flac, "-c:a", "libmp3lame", "-b:a", "192k", o_mono])
st = os.path.join(d, "st.wav")
ff(["-i", flac, "-ac", "2", "-t", "8", "-c:a", "pcm_s16le", st])
o_st = os.path.join(d, "st.mp3")
ff(["-i", st, "-c:a", "libmp3lame", "-b:a", "192k", o_st])
o_m4a = os.path.join(d, "v.m4a")
ff(["-i", mp4, "-vn", "-c:a", "copy", o_m4a])

casos = [("MONO  flac->mp3", flac, o_mono, 44100, "mono"),
         ("EST.  wav->mp3", st, o_st, 44100, "stereo"),
         ("VIDEO mp4->m4a", mp4, o_m4a, 44100, "mono")]

for var in VARIANTES:
    print("\n########## %s" % var)
    for etiqueta, e, s, sr, lay in casos:
        rc, v, err = correr(var, e, s, sr, lay)
        linea = [x for x in err.splitlines()
                 if "rror" in x or "nvalid" in x or "atch" in x][:1]
        print("  %-18s rc=%-11d valores=%-2d %s  %s"
              % (etiqueta, rc, len(v), v[:6], linea))

shutil.rmtree(d, ignore_errors=True)
