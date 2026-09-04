# -*- coding: utf-8 -*-
"""Reconstruye el GRAFO A (138 501 aristas) sin ejecutar un solo motor.

`bench/salidas-aristas/aristas.json` esta podado con su orden (`_censo.py`), pero esa
orden relanza ~590 sondas `ffmpeg -h ...`, que es justo el gasto de maquina prohibido
en esta ronda. No hace falta: el grafo A es un PRODUCTO CARTESIANO de conjuntos
DECLARADOS, y los cinco conjuntos estan disponibles sin tocar un motor:

  ffmpeg          -> repos/orchestrators/ConvertX/src/converters/ffmpeg.ts  (fichero)
  imagemagick     -> crudo/im-format.txt                                    (ya volcado)
  ghostscript     -> GS_IN literal + censo.json.ghostscript.salidas_mapeadas
  gotenberg-lo    -> censo.json.gotenberg_lo_ext
  gotenberg-chrom -> literal en _censo.py

Escribe aristas_A.json EN ESTE DIRECTORIO (no en bench/salidas-aristas/).
"""
import os, re, json
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
CRUDO = os.path.join(AQUI, "crudo")
SAL = os.path.abspath(os.path.join(AQUI, "..", "salidas-aristas"))
CONV = r"D:\Work\research\FileX\repos\orchestrators\ConvertX\src\converters"

PAT = r'"([A-Za-z0-9_.+/-]{1,40})"'


def bloque(txt, clave):
    m = re.search(clave + r"\s*:\s*\{", txt)
    if not m:
        return ""
    i, d = m.end() - 1, 0
    for j in range(i, len(txt)):
        if txt[j] == '{':
            d += 1
        elif txt[j] == '}':
            d -= 1
            if d == 0:
                return txt[i:j + 1]
    return ""


def props(f):
    txt = open(f, encoding='utf-8').read()
    m = re.search(r"export const properties\s*(?::\s*\w+)?\s*=\s*\{", txt)
    if not m:
        return set(), set()
    i, d, blk = m.end() - 1, 0, ""
    for j in range(i, len(txt)):
        if txt[j] == '{':
            d += 1
        elif txt[j] == '}':
            d -= 1
            if d == 0:
                blk = txt[i:j + 1]
                break
    return set(re.findall(PAT, bloque(blk, "from"))), set(re.findall(PAT, bloque(blk, "to")))


def im_lee_esc():
    lee, esc = set(), set()
    for ln in open(os.path.join(CRUDO, "im-format.txt"), encoding="utf-8",
                   errors="replace").read().splitlines()[2:]:
        p = ln.split()
        if len(p) < 3 or not re.fullmatch(r"[r-][w-][+-]", p[2]):
            continue
        f = p[0].rstrip('*').lower()
        if p[2][0] == 'r':
            lee.add(f)
        if p[2][1] == 'w':
            esc.add(f)
    return lee, esc


def aristas(mdict):
    E = defaultdict(set)
    for m, (fr, to) in mdict.items():
        for a in {x.lower() for x in fr}:
            for b in {x.lower() for x in to}:
                if a != b:
                    E[(a, b)].add(m)
    return E


if __name__ == "__main__":
    ff_in, ff_out = props(os.path.join(CONV, "ffmpeg.ts"))
    ff_in = {x.lower() for x in ff_in}
    ff_out = {x.lower() for x in ff_out}
    im_lee, im_esc = im_lee_esc()
    censo = json.load(open(os.path.join(SAL, "censo.json"), encoding="utf-8"))
    gs_out = set(censo["ghostscript"]["salidas_mapeadas"])
    lo_in = set(censo["gotenberg_lo_ext"])

    print("ffmpeg     declarado in %d / out %d   (censo dice %d / %d)"
          % (len(ff_in), len(ff_out), censo["ffmpeg"]["declarado_in"],
             censo["ffmpeg"]["declarado_out"]))
    print("imagemagick lee %d / escribe %d       (censo dice %d / %d)"
          % (len(im_lee), len(im_esc), censo["imagemagick"]["lee"],
             censo["imagemagick"]["escribe"]))

    instA = {
        "ffmpeg": (ff_in, ff_out),
        "imagemagick": (im_lee, im_esc),
        "ghostscript": ({"pdf", "ps", "eps"}, gs_out),
        "gotenberg-lo": (lo_in, {"pdf"}),
        "gotenberg-chromium": ({"html", "htm", "md", "xhtml", "url"},
                               {"pdf", "png", "jpeg", "jpg", "webp"}),
    }
    EA = aristas(instA)
    print("\naristas grafo A reconstruidas: %d   (censo.json dice %d)"
          % (len(EA), censo["aristas_A"]))
    print("COINCIDE" if len(EA) == censo["aristas_A"] else "*** NO COINCIDE ***")

    json.dump({"A": sorted(["%s>%s|%s" % (a, b, ",".join(sorted(m))) for (a, b), m in EA.items()])},
              open(os.path.join(AQUI, "aristas_A.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print("escrito aristas_A.json")
