# -*- coding: utf-8 -*-
"""P2 / C17 segunda vuelta - mas semillas para Gotenberg/LibreOffice, y el csv.

La primera vuelta materializo 18 de 102 extensiones porque uso una sola base (.odt):
`soffice --convert-to` solo escribe formatos del MISMO tipo de documento que la base.
Aqui se usan tres bases -- texto (.odt), hoja (.xlsx) y dibujo (.odg) -- y se reintenta
el unico caso que fallo por transporte (csv, WinError 10054).

Escribe c17b.json
"""
import os, sys, json, subprocess, time

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_c17")
SEM = os.path.join(SAL, "sem_c17")
E1C8 = os.path.join(RAIZ, r"bench\salidas-aristas\c8\in")
sys.path.insert(0, SAL)
from _p2_lib import corre, juzga, sonda_y_veredicto
from _p2_c17 import post, GOT

BASES = {"texto": os.path.join(E1C8, "entrada.odt"),
         "hoja": os.path.join(E1C8, "entrada.xlsx")}

if __name__ == "__main__":
    os.makedirs(SEM, exist_ok=True)
    prev = json.load(open(os.path.join(SAL, "c17.json"), encoding="utf-8"))
    lo = [r for r in prev if r["motor"] == "gotenberg-lo"]
    ya = {r["a"] for r in lo if "nominal" in r}
    faltan = sorted({r["a"] for r in lo if r.get("estado") == "sin_semilla"})
    print("faltaban %d extensiones" % len(faltan), flush=True)

    idx = {}
    corre(["docker", "exec", "filex-convertx", "sh", "-c", "rm -rf /tmp/c17b; mkdir -p /tmp/c17b"], 60)
    for etiqueta, base in BASES.items():
        if not os.path.exists(base):
            continue
        ext = base.rsplit(".", 1)[-1]
        corre(["docker", "cp", base, "filex-convertx:/tmp/c17b/base_%s.%s" % (etiqueta, ext)], 120)
        sh = ("cd /tmp/c17b && for e in %s; do soffice --headless --convert-to $e "
              "base_%s.%s --outdir /tmp/c17b >/dev/null 2>&1; done" %
              (" ".join(faltan), etiqueta, ext))
        corre(["docker", "exec", "filex-convertx", "sh", "-c", sh], 1200)
    p = subprocess.run(["docker", "exec", "filex-convertx", "sh", "-c", "ls /tmp/c17b"],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    for nombre in (p.stdout or "").split():
        e = nombre.rsplit(".", 1)[-1].lower()
        if e in faltan and e not in idx:
            dst = os.path.join(SEM, "s." + e)
            corre(["docker", "cp", "filex-convertx:/tmp/c17b/" + nombre, dst], 120)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                idx[e] = dst
    print("semillas nuevas: %d  %s" % (len(idx), sorted(idx)), flush=True)

    # reintento del csv (fallo de transporte, no de conversion)
    reint = []
    csv = None
    for r, _, fs in os.walk(E1C8):
        for f in fs:
            if f.endswith(".csv"):
                csv = os.path.join(r, f)
    if csv:
        idx["csv"] = csv

    res = []
    for a in sorted(idx):
        pth = idx[a]
        datos_in = open(pth, "rb").read()
        st, datos, err, msx = post("/forms/libreoffice/convert", [],
                                   [("files", os.path.basename(pth), datos_in)], 180)
        sal = os.path.join(TMP, "lo2_%s.pdf" % a)
        if datos:
            open(sal, "wb").write(datos)
        tam = len(datos)
        son, ver = ({}, {})
        if st == 200 and tam > 0:
            son, ver = sonda_y_veredicto(sal, pth)
        nom, cat, mot, n2 = juzga(0 if st == 200 else 1, tam, len(datos_in), "pdf", son, ver)
        res.append({"motor": "gotenberg-lo", "a": a, "b": "pdf", "http": st, "bytes": tam,
                    "ms": round(msx, 1), "nominal": nom, "veredicto": cat, "motivo": mot,
                    "firma": son.get("firma"), "semilla": os.path.basename(pth),
                    "err": err[-220:]})
        print("  %-8s -> pdf  HTTP %-5s %8d B  %-10s %s" %
              (a, st, tam, cat, err[:70].replace("\n", " ")), flush=True)
    json.dump(res, open(os.path.join(SAL, "c17b.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    k = sum(1 for r in res if r["nominal"])
    print("\nsegunda vuelta: %d evaluables, %d nominales" % (len(res), k))
