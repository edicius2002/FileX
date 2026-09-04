# -*- coding: utf-8 -*-
"""Sonda previa (no forma parte del resultado publicado): para cada alias
candidato de C16, mira que fichero mas pequeno hay en el directorio de FATE
y que demuxer/codec detecta ffprobe SIN forzar formato -- para confirmar
antes de gastar la tanda completa que el alias es GENUINO y no una colision
de nombre (misma disciplina que la trampa 73/70)."""
import os
import subprocess

FATE = r"D:\Work\research\fate-suite"
FFPROBE = r"D:\utils\ffmpeg\bin\ffprobe.exe"
EXCLUIR = {"md5sum", "csum", "readme", "license", "changelog", "notes",
          "info.txt", "checksums"}

CANDIDATOS = {
    "cavsvideo": "cavs", "vc1test": "vc1", "roq": "idroq",
    "anm": "deluxepaint-anm", "c93": "cyberia-c93",
    "dfa": "chronomaster-dfa", "iss": "funcom-iss", "wsvqa": "vqa",
    "wsaud": "westwood-aud", "daud": "d-cinema",
    "argo_asf": "argo-asf", "asf_o": "asf", "amr": "amrnb",
    "ipmovie": "interplay-mve", "dsicin": "delphine-cin",
    "ans": "ansi", "psxstr": "psx-str", "film_cpk": "film",
    "bethsoftvid": "bethsoft-vid", "brender_pix": "brenderpix",
    "alias_pix": "aliaspix", "ea_cdata": "ea-cdata",
    "tiertexseq": "tiertex-seq",
}


def smallest_file(d):
    best = None
    for root, _, files in os.walk(d):
        for f in files:
            base = f.lower().rsplit(".", 1)[0]
            if base in EXCLUIR or f.lower() in EXCLUIR:
                continue
            p = os.path.join(root, f)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if sz < 100:
                continue
            if best is None or sz < best[1]:
                best = (p, sz)
    return best


for fmt, dirname in CANDIDATOS.items():
    d = os.path.join(FATE, dirname)
    bf = smallest_file(d)
    if not bf:
        print("%-14s %-20s SIN FICHERO VALIDO" % (fmt, dirname))
        continue
    ruta, sz = bf
    p = subprocess.run([FFPROBE, "-hide_banner", ruta], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=15, errors="replace")
    primera = ""
    for ln in (p.stderr or "").splitlines():
        if ln.strip().startswith("Input #0"):
            primera = ln.strip()
            break
    print("%-14s %-20s %8d B  %-50s %s" % (fmt, os.path.basename(ruta), sz, primera,
                                            os.path.basename(ruta)))
