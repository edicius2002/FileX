# -*- coding: utf-8 -*-
"""P2 / C17 - CENSO DE LAS ARISTAS DE GHOSTSCRIPT Y GOTENBERG.

Son el 0,10 % de la poblacion y TODA la superficie documental del grafo, asi que su
tasa nominal pesa mucho mas que su tamano. E1 las dejo fuera de la muestra.

  ghostscript          9 aristas  {pdf,ps,eps} x {docx,pclm,xps}   -> censo completo
  gotenberg-chromium  25 aristas  {html,htm,xhtml,md,url} x {pdf,png,jpeg,jpg,webp}
  gotenberg-lo       102 aristas  102 extensiones x {pdf}

Ghostscript se invoca como proceso separado sin shell. Gotenberg por su API HTTP en
:3200, que es como se invoca de verdad: /forms/libreoffice/convert,
/forms/chromium/convert/{html,url,markdown} y /forms/chromium/screenshot/{...}.

Escribe c17.json
"""
import os, re, sys, json, time, glob, uuid, subprocess, urllib.request, urllib.error

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_c17")
SEM = os.path.join(SAL, "sem_c17")
CORPUS = os.path.join(RAIZ, "corpus")
E1C8 = os.path.join(RAIZ, r"bench\salidas-aristas\c8\in")
GOT = "http://localhost:3200"
sys.path.insert(0, SAL)
from _p2_lib import corre, limpia, juzga, sonda_y_veredicto

GS = r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe"
GS_DEV = {"docx": "docxwrite", "pclm": "pclm", "xps": "xpswrite"}


def multipart(campos, ficheros):
    b = "----filex" + uuid.uuid4().hex
    out = b""
    for k, v in campos:
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                % (b, k, v)).encode()
    for k, nombre, datos in ficheros:
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                "Content-Type: application/octet-stream\r\n\r\n" % (b, k, nombre)).encode()
        out += datos + b"\r\n"
    out += ("--%s--\r\n" % b).encode()
    return b, out


def post(ruta, campos, ficheros, timeout=90):
    b, cuerpo = multipart(campos, ficheros)
    req = urllib.request.Request(GOT + ruta, data=cuerpo, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + b)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), "", (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, b"", (e.read() or b"")[:300].decode("utf-8", "replace"), \
               (time.perf_counter() - t0) * 1000
    except Exception as e:
        return -1, b"", str(e)[:200], (time.perf_counter() - t0) * 1000


def semillas_lo(exts):
    """Materializa lo que se pueda: corpus, c8/in de E1 y LibreOffice del contenedor."""
    os.makedirs(SEM, exist_ok=True)
    idx = {}
    for d in (CORPUS, E1C8):
        for r, _, fs in os.walk(d):
            for f in fs:
                e = f.rsplit(".", 1)[-1].lower()
                if e in exts and e not in idx:
                    idx[e] = os.path.join(r, f)
    faltan = sorted(set(exts) - set(idx))
    # LibreOffice dentro de filex-convertx escribe muchos de ellos
    base = idx.get("odt") or os.path.join(E1C8, "entrada.odt")
    if os.path.exists(base) and faltan:
        corre(["docker", "exec", "filex-convertx", "mkdir", "-p", "/tmp/c17"], 60)
        corre(["docker", "cp", base, "filex-convertx:/tmp/c17/base.odt"], 120)
        lote = " ".join(faltan)
        sh = ("cd /tmp/c17 && for e in %s; do soffice --headless --convert-to $e "
              "base.odt --outdir /tmp/c17 >/dev/null 2>&1; done; ls /tmp/c17" % lote)
        rc, err, ms = corre(["docker", "exec", "filex-convertx", "sh", "-c", sh], 900)
        rc2, err2, _ = corre(["docker", "exec", "filex-convertx", "sh", "-c",
                              "ls /tmp/c17"], 60)
        p = subprocess.run(["docker", "exec", "filex-convertx", "sh", "-c", "ls /tmp/c17"],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           timeout=60)
        for nombre in (p.stdout or "").split():
            e = nombre.rsplit(".", 1)[-1].lower()
            if e in exts and e not in idx:
                dst = os.path.join(SEM, "s." + e)
                corre(["docker", "cp", "filex-convertx:/tmp/c17/" + nombre, dst], 120)
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    idx[e] = dst
    return idx


if __name__ == "__main__":
    limpia(TMP)
    ar = json.load(open(os.path.join(SAL, "aristas.json"), encoding="utf-8"))
    aristas = []
    for reg in ar["A"]:
        ab, ms = reg.split("|")
        a, b = ab.split(">")
        if not ({"ffmpeg", "imagemagick"} & set(ms.split(","))):
            aristas.append((a, b, ms))
    res = []

    # ---------------------------------------------------------- Ghostscript
    print("GHOSTSCRIPT (%d aristas)" % len([t for t in aristas if "ghostscript" in t[2]]),
          flush=True)
    ent_pdf = os.path.join(CORPUS, "pdf", "tipico_texto.pdf")
    os.makedirs(SEM, exist_ok=True)
    ent = {"pdf": ent_pdf}
    for e, dev in (("ps", "ps2write"), ("eps", "eps2write")):
        p = os.path.join(SEM, "s." + e)
        if not os.path.exists(p):
            corre([GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=" + dev,
                   "-sOutputFile=" + p, ent_pdf], 120)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            ent[e] = p
    for a, b, ms in [t for t in aristas if "ghostscript" in t[2]]:
        if a not in ent:
            res.append({"motor": "ghostscript", "a": a, "b": b, "estado": "sin_semilla"})
            continue
        sal = os.path.join(TMP, "gs_%s_%s.%s" % (a, b, b))
        args = [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-sDEVICE=" + GS_DEV[b],
                "-sOutputFile=" + sal, ent[a]]
        rc, err, ms_ = corre(args, 120, cwd=TMP)
        tam = os.path.getsize(sal) if os.path.exists(sal) else -1
        son, ver = ({}, {})
        if rc == 0 and tam > 0:
            son, ver = sonda_y_veredicto(sal, ent[a])
        nom, cat, mot, n2 = juzga(rc, tam, os.path.getsize(ent[a]), b, son, ver)
        res.append({"motor": "ghostscript", "a": a, "b": b, "rc": rc, "bytes": tam,
                    "ms": round(ms_, 1), "nominal": nom, "veredicto": cat,
                    "motivo": mot, "firma": son.get("firma"), "args": args,
                    "err": err.replace("\n", " ")[-220:] if nom else ""})
        print("  %-5s -> %-6s rc=%-4s %8d B  %s" % (a, b, rc, tam, cat), flush=True)

    # ---------------------------------------------------------- Gotenberg chromium
    chrom = [t for t in aristas if "gotenberg-chromium" in t[2]]
    print("\nGOTENBERG / CHROMIUM (%d aristas)" % len(chrom), flush=True)
    html = ("<!doctype html><html><head><meta charset='utf-8'><title>t</title></head>"
            "<body><h1>FILEXSENTINELA7743</h1><table><tr><td>AX-1</td></tr></table>"
            "</body></html>").encode()
    md = b"# FILEXSENTINELA7743\n\n| AX-1 |\n| --- |\n| x |\n"
    RUTA = {"pdf": "/forms/chromium/convert/", "png": "/forms/chromium/screenshot/",
            "jpeg": "/forms/chromium/screenshot/", "jpg": "/forms/chromium/screenshot/",
            "webp": "/forms/chromium/screenshot/"}
    for a, b, ms in chrom:
        sub = {"html": "html", "htm": "html", "xhtml": "html", "md": "markdown",
               "url": "url"}[a]
        ruta = RUTA[b] + sub
        campos, fich = [], []
        if b != "pdf":
            campos.append(("format", "jpeg" if b in ("jpg", "jpeg") else b))
        if a == "url":
            campos.append(("url", "https://example.com"))
        elif a == "md":
            fich = [("files", "index.html", html), ("files", "f.md", md)]
        else:
            fich = [("files", "index." + ("html" if a != "xhtml" else "html"), html)]
        st, datos, err, msx = post(ruta, campos, fich)
        sal = os.path.join(TMP, "gb_%s_%s.%s" % (a, b, b))
        if datos:
            open(sal, "wb").write(datos)
        tam = len(datos)
        son, ver = ({}, {})
        if st == 200 and tam > 0:
            son, ver = sonda_y_veredicto(sal, sal)
        nom, cat, mot, n2 = juzga(0 if st == 200 else 1, tam, len(html), b, son, ver)
        res.append({"motor": "gotenberg-chromium", "a": a, "b": b, "http": st,
                    "bytes": tam, "ms": round(msx, 1), "nominal": nom,
                    "veredicto": cat, "motivo": mot, "firma": son.get("firma"),
                    "ruta": ruta, "err": err[-220:]})
        print("  %-5s -> %-5s HTTP %-4s %8d B  firma=%-8s %s" %
              (a, b, st, tam, son.get("firma"), cat), flush=True)

    # ---------------------------------------------------------- Gotenberg LO
    lo = [t for t in aristas if "gotenberg-lo" in t[2] and "chromium" not in t[2]]
    exts = sorted({t[0] for t in lo})
    print("\nGOTENBERG / LIBREOFFICE (%d aristas, %d extensiones)" % (len(lo), len(exts)),
          flush=True)
    idx = semillas_lo(set(exts))
    print("  semillas materializadas: %d de %d" % (len(idx), len(exts)), flush=True)
    for a, b, ms in lo:
        p = idx.get(a)
        if not p:
            res.append({"motor": "gotenberg-lo", "a": a, "b": b, "estado": "sin_semilla"})
            continue
        datos_in = open(p, "rb").read()
        st, datos, err, msx = post("/forms/libreoffice/convert", [],
                                   [("files", os.path.basename(p), datos_in)], 180)
        sal = os.path.join(TMP, "lo_%s.pdf" % a)
        if datos:
            open(sal, "wb").write(datos)
        tam = len(datos)
        son, ver = ({}, {})
        if st == 200 and tam > 0:
            son, ver = sonda_y_veredicto(sal, p)
        nom, cat, mot, n2 = juzga(0 if st == 200 else 1, tam, len(datos_in), b, son, ver)
        res.append({"motor": "gotenberg-lo", "a": a, "b": b, "http": st, "bytes": tam,
                    "ms": round(msx, 1), "nominal": nom, "veredicto": cat,
                    "motivo": mot, "firma": son.get("firma"),
                    "semilla": os.path.basename(p), "err": err[-220:]})
        print("  %-8s -> pdf  HTTP %-4s %8d B  %-10s %s" %
              (a, st, tam, cat, err[:60].replace("\n", " ")), flush=True)

    json.dump(res, open(os.path.join(SAL, "c17.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    from collections import Counter
    print("\nRESUMEN C17")
    for m in ("ghostscript", "gotenberg-chromium", "gotenberg-lo"):
        s = [r for r in res if r["motor"] == m]
        ev = [r for r in s if "nominal" in r]
        k = sum(1 for r in ev if r["nominal"])
        print("  %-20s %3d aristas, %3d evaluables, %3d nominales (%.1f %%)  %s" %
              (m, len(s), len(ev), k, 100 * k / max(1, len(ev)),
               dict(Counter(r.get("veredicto") for r in ev))))
