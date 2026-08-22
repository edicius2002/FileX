# -*- coding: utf-8 -*-
"""F1 / paso 1 - EL UNIVERSO DE DESTINOS Y SU ORDEN DE DEMANDA.

Extrae de los 20 adaptadores de ConvertX los formatos declarados de entrada y de
salida (mismo parser que bench/salidas-aristas/_censo.py, que reprodujo las cifras
canonicas 896 / 503 de analysis/00-matriz-formatos.md), y construye tres proxies de
demanda para priorizar que firmas anadir primero:

  P1  el patron oro: destinos de las 39 ordenes de bench/salidas-referencia/referencia.json
  P2  el catalogo de SnapOtter (repos/orchestrators/SnapOtter/.../modality.ts)
  P3  cuantos de los 20 adaptadores declaran ese formato como SALIDA (consenso del sector)

Escribe formatos.json. NO toca nada.
"""
import os, re, json, sys
from collections import defaultdict, Counter

RAIZ = r"D:\Work\research\FileX"
CONV = os.path.join(RAIZ, r"repos\orchestrators\ConvertX\src\converters")
SNAP = os.path.join(RAIZ, r"repos\orchestrators\SnapOtter\packages\shared\src\modality.ts")
REF = os.path.join(RAIZ, r"bench\salidas-referencia\referencia.json")
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")

PAT = r'"([A-Za-z0-9_.+/-]{1,40})"'


def bloque(txt, clave):
    m = re.search(clave + r"\s*:\s*\{", txt)
    if not m:
        return ""
    i = m.end() - 1
    d = 0
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
    i = m.end() - 1
    d = 0
    blk = ""
    for j in range(i, len(txt)):
        if txt[j] == '{':
            d += 1
        elif txt[j] == '}':
            d -= 1
            if d == 0:
                blk = txt[i:j + 1]
                break
    return set(re.findall(PAT, bloque(blk, "from"))), set(re.findall(PAT, bloque(blk, "to")))


def snap():
    t = open(SNAP, encoding='utf-8').read()
    fam = {}
    for nombre, f in [("IMAGE_INPUTS", "imagen"), ("VIDEO_INPUTS", "video"),
                      ("AUDIO_INPUTS", "audio"), ("SUBTITLE_INPUTS", "subtitulo"),
                      ("DOCUMENT_INPUTS", "documento"), ("FILE_INPUTS", "datos")]:
        seg = t.split(nombre)[1].split("]")[0]
        for e in re.findall(r'"\.([a-z0-9]+)"', seg):
            fam.setdefault(e, f)
    return fam


def ref_destinos():
    d = json.load(open(REF, encoding="utf-8"))
    dest = Counter()
    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("destino", "salida", "archivo", "fichero", "nombre") and isinstance(v, str):
                    ext = os.path.splitext(v)[1].lstrip(".").lower()
                    if ext:
                        dest[ext] += 1
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)
    rec(d)
    return dest


if __name__ == "__main__":
    MOT = {}
    for fn in sorted(os.listdir(CONV)):
        if fn.endswith(".ts") and fn not in ("main.ts", "types.ts"):
            fr, to = props(os.path.join(CONV, fn))
            if fr or to:
                MOT[fn[:-3]] = (sorted({x.lower() for x in fr}), sorted({x.lower() for x in to}))

    ent = set()
    sal = set()
    por_sal = defaultdict(set)
    for m, (fr, to) in MOT.items():
        ent |= set(fr)
        sal |= set(to)
        for b in to:
            por_sal[b].add(m)

    print("adaptadores: %d" % len(MOT))
    for m in sorted(MOT):
        print("   %-16s from=%3d to=%3d" % (m, len(MOT[m][0]), len(MOT[m][1])))
    print("\nFORMATOS DE ENTRADA UNICOS : %d   (canonico 896)" % len(ent))
    print("FORMATOS DE SALIDA UNICOS  : %d   (canonico 503)" % len(sal))

    fam = snap()
    refd = ref_destinos()
    print("\nSnapOtter declara %d extensiones de entrada" % len(fam))
    print("patron oro: %d extensiones de destino distintas -> %s" % (len(refd), dict(refd.most_common())))

    filas = []
    for b in sorted(sal):
        filas.append({
            "formato": b,
            "adaptadores": sorted(por_sal[b]),
            "n_adaptadores": len(por_sal[b]),
            "en_snapotter": b in fam,
            "familia_snapotter": fam.get(b),
            "en_patron_oro": refd.get(b, 0),
        })
    json.dump({"n_entrada": len(ent), "n_salida": len(sal),
               "entrada": sorted(ent), "salida": sorted(sal),
               "por_adaptador": {m: {"from": MOT[m][0], "to": MOT[m][1]} for m in MOT},
               "snapotter": fam, "patron_oro": dict(refd),
               "filas": filas},
              open(os.path.join(SAL, "formatos.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nescrito formatos.json")

    # ranking de demanda
    def puntos(f):
        return (f["en_patron_oro"] * 100 + (50 if f["en_snapotter"] else 0) + f["n_adaptadores"])
    top = sorted(filas, key=lambda f: -puntos(f))[:60]
    print("\nTOP 60 por demanda (patron oro x100 + SnapOtter x50 + n_adaptadores):")
    for f in top:
        print("   %-14s pts=%4d  oro=%d snap=%-5s ad=%d" %
              (f["formato"], puntos(f), f["en_patron_oro"], f["en_snapotter"], f["n_adaptadores"]))
