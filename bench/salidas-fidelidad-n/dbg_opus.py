# -*- coding: utf-8 -*-
"""Depuración: por qué la sonda no da duración en un `.opus` ESTÉREO."""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", ".."))
sys.path.insert(0, RAIZ)
from filex import verificador as V  # noqa: E402


def ff(a):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + a,
                          capture_output=True, timeout=300,
                          stdin=subprocess.DEVNULL)


d = tempfile.mkdtemp(prefix="filex-dbg-")
jfk = os.path.join(RAIZ, "corpus", "audio", "habla_jfk.flac")
est = os.path.join(d, "est.wav")
ff(["-i", jfk, "-i", jfk, "-filter_complex",
    "[0:a]pan=mono|c0=c0,atrim=0:8[l];"
    "[1:a]pan=mono|c0=c0,atrim=20:28,asetpts=PTS-STARTPTS[r];"
    "[l][r]join=inputs=2:channel_layout=stereo",
    "-t", "8", "-ar", "48000", "-c:a", "pcm_s16le", est])
mono = os.path.join(d, "mono.wav")
ff(["-i", jfk, "-t", "8", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", mono])

for etiq, src in (("estereo", est), ("mono", mono)):
    o = os.path.join(d, etiq + ".opus")
    ff(["-i", src, "-c:a", "libopus", "-b:a", "8k", o])
    s = V.sondear(o)
    print("\n### %s  (%d B)" % (etiq, os.path.getsize(o)))
    print("  claves:", {k: v for k, v in s.items() if k != "pistas"})
    print("  pistas:", s.get("pistas"))
    print("  tasa efectiva:", V._a7_tasa_efectiva(o, s))
    ce, ee = V._ffmpeg_astats(src)
    cs, es = V._ffmpeg_astats(o)
    print("  astats ent:", ce, ee)
    print("  astats sal:", cs, es)

shutil.rmtree(d, ignore_errors=True)
