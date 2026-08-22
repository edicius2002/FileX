# -*- coding: utf-8 -*-
"""F1 / paso 2c - CONTROL DE SESGO DE SEMILLA sobre los 64 destinos de pandoc.

Las dos semillas del censo (_cont_firmas.py) son markdown que EMPIEZA POR UN
TITULO. Los formatos de markup heredan esa estructura y aparecen con un "prefijo
comun" de 2-5 bytes (`==`, `=====`, `{#`, `\\begin{frame}{`...) que NO es un
marcador del formato: es el titulo de mis dos semillas.

Aqui se anade una TERCERA semilla que empieza por un parrafo llano y se vuelve a
medir. Si el prefijo cae a 0, queda demostrado que era sesgo de semilla; si se
mantiene, es un marcador de verdad. Refutar el propio arnes antes de publicar.

Se ejecuta DENTRO del contenedor: python3 /tmp/f1/_cont_pandoc3.py
Escribe /tmp/f1/pandoc3.json
"""
import os, json, time, shutil, subprocess

BASE = "/tmp/f1"
POOL = BASE + "/pool3"
TMP = BASE + "/tmp3"
NCAB = 64

SEM = [
    ("m1.md", "# Titulo uno\n\nParrafo con *enfasis* y una lista:\n\n- a\n- b\n\n"),
    ("m2.md", "## Otro documento\n\nTexto distinto del primero, mas largo, con una "
              "tabla:\n\n| x | y |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nY un cierre.\n"),
    # LA TERCERA: ni titulo ni lista. Solo prosa.
    ("m3.md", "Esto empieza directamente en prosa, sin ningun titulo delante, y sigue "
              "durante unas cuantas palabras mas para que el fichero no sea trivial.\n"),
]


def corre(args, timeout=40, cwd=None):
    try:
        p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=timeout, cwd=cwd)
        return p.returncode, (p.stderr or b"")[-200:]
    except Exception as e:
        return -9, str(e).encode()[:120]


def limpia(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)


def prefijo(cabs):
    n = min(len(c) for c in cabs)
    i = 0
    while i < n and len({c[i] for c in cabs}) == 1:
        i += 1
    return i


if __name__ == "__main__":
    os.makedirs(POOL, exist_ok=True)
    sems = []
    for nom, txt in SEM:
        p = POOL + "/" + nom
        open(p, "w").write(txt)
        sems.append(p)
    F = json.load(open(BASE + "/formatos.json"))
    destinos = sorted(set(F["por_adaptador"]["pandoc"]["to"]))
    res = {}
    dirs = ["d0", "x1", "y2"]
    pats = ["v%d", "w%d", "u%d"]
    for k, b in enumerate(destinos):
        cabs, ok = [], True
        for j, ent in enumerate(sems):
            sub = TMP + "/" + dirs[j]
            limpia(sub)
            sal = sub + "/" + (pats[j] % (k * 7 + j * 7919)) + "." + b.replace("/", "_")
            rc, err = corre(["pandoc", ent, "-f", "markdown", "-t", b, "-o", sal], 40, sub)
            cands = [x for x in os.listdir(sub) if os.path.isfile(sub + "/" + x)]
            if rc != 0 or not cands:
                ok = False
                break
            with open(sub + "/" + sorted(cands)[0], "rb") as fh:
                cabs.append(fh.read(NCAB))
        if ok and len(cabs) == 3:
            res[b] = {"n": 3, "prefijo_comun": prefijo(cabs),
                      "cab": [c.hex() for c in cabs]}
        else:
            res[b] = {"n": len(cabs), "estado": "no_escribible"}
    json.dump(res, open(BASE + "/pandoc3.json", "w"), indent=0)
    con = [b for b, v in res.items() if v.get("prefijo_comun", 0) >= 2]
    sin = [b for b, v in res.items() if v.get("n") == 3 and v.get("prefijo_comun", 0) < 2]
    print("pandoc: %d destinos, %d escritos" % (len(res), len(con) + len(sin)))
    print("CON prefijo >=2 con TRES semillas (%d): %s" % (len(con), sorted(con)))
    print("SIN prefijo (%d): %s" % (len(sin), sorted(sin)))
    print("HECHO")
