# -*- coding: utf-8 -*-
"""K1 / hito 5 — sonda de aristas del motor documental en contenedor.

**Toda invocación pasa por `filex.invocacion.ejecutar()`**, que es el único
sitio del proyecto que puede lanzar un proceso (`stdin=DEVNULL` en el
constructor, antes que las banderas).

Cada arista candidata se ejecuta **en su propio directorio desechable**
(`filex.trabajo.DirectorioDeTrabajo`), que se **censa antes y después** — el
quinto punto del contrato no se puede verificar a posteriori.

    python bench/salidas-hito5/_sonda.py [--solo ID,ID]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import invocacion  # noqa: E402
from filex.trabajo import DirectorioDeTrabajo  # noqa: E402

SAL = os.path.join(RAIZ, "bench", "salidas-hito5")
ENT = os.path.join(SAL, "entradas")

#: **REFUTADO: `filex-convertx` no es una imagen, es un CONTENEDOR.** `docker
#: image inspect filex-convertx` -> «No such image». La imagen es
#: `ghcr.io/c4illin/convertx:latest`, y `filex-c13` es esa misma con `qpdf` y
#: `tesseract` encima (`bench/salidas-invocacion/Dockerfile.c13`).
IMAGEN = os.environ.get("FILEX_IMAGEN_DOC", "filex-c13")
CENTINELA = "FILEXSENTINELA7743"
TIMEOUT = 240.0

# ---------------------------------------------------------------- invocación


def argv_docker(entrada_host: str, nombre_dentro: str, trabajo: str, orden: list[str],
                *, red: bool = False) -> list[str]:
    """`docker run` con el desechable montado como /trabajo y la entrada, SOLA.

    Dos decisiones que no son cosméticas:

    * **La entrada se monta fichero a fichero y de solo lectura.** Montar su
      directorio padre expondría al contenedor todo lo que haya al lado.
    * **El desechable del anfitrión ES el /trabajo del contenedor**, así que el
      censo del punto 5 ve lo que el motor escribió dentro del contenedor. Sin
      esto, `docker cp` traería solo lo declarado y el punto 5 se perdería.

    `--mount` en vez de `-v` porque una ruta de Windows lleva `D:` y `-v` parte
    por `:`.
    """
    a = ["docker", "run", "--rm", "--init"]
    if not red:
        a += ["--network", "none"]
    a += [
        # La imagen trae ENTRYPOINT ["bun","run","dist/src/index.js"] y
        # WorkingDir /app: sin `--entrypoint` la orden se pasa como ARGUMENTOS
        # a la aplicación web de ConvertX y sale «Module not found». Sondeado en
        # ejecución, no deducido.
        "--entrypoint", orden[0],
        "--mount", f"type=bind,source={entrada_host},target=/ent/{nombre_dentro},readonly",
        "--mount", f"type=bind,source={trabajo},target=/trabajo",
        "-w", "/trabajo",
        "-e", "HOME=/tmp",
        IMAGEN,
    ] + orden[1:]
    return a


# ------------------------------------------------------------ recuperar texto


def _limpia(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def texto_de(ruta: str) -> str:
    """Texto recuperable de una salida. Para el centinela y la tabla, no para CER."""
    ext = os.path.splitext(ruta)[1].lower().lstrip(".")
    try:
        if ext == "pdf":
            # Ghostscript NATIVO de Windows. Trampa 4: `txtwrite` emite 1-3
            # caracteres de basura en un PDF sin texto; el umbral es >=10.
            with DirectorioDeTrabajo() as t:
                dst = t.destino("t.txt")
                r = invocacion.ejecutar(
                    ["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                     "-sDEVICE=txtwrite", f"-sOutputFile={dst}", ruta], timeout=90)
                if not r.ok or not os.path.isfile(dst):
                    return ""
                return _limpia(open(dst, encoding="utf-8", errors="replace").read())
        if ext in ("docx", "odt", "epub", "azw3", "mobi"):
            if not zipfile.is_zipfile(ruta):
                # mobi/azw3 no son zip: se lee el binario y se busca el centinela
                d = open(ruta, "rb").read()
                return _limpia(d.decode("latin-1", "replace"))
            out = []
            with zipfile.ZipFile(ruta) as z:
                for n in z.namelist():
                    if n.lower().endswith((".xml", ".html", ".xhtml", ".htm")):
                        try:
                            out.append(re.sub(r"<[^>]+>", " ",
                                              z.read(n).decode("utf-8", "replace")))
                        except Exception:
                            pass
            return _limpia(" ".join(out))
        if ext in ("html", "htm", "xhtml"):
            return _limpia(re.sub(r"<[^>]+>", " ",
                                  open(ruta, encoding="utf-8", errors="replace").read()))
        if ext in ("md", "txt", "rtf", "tex", "csv"):
            return _limpia(open(ruta, encoding="utf-8", errors="replace").read())
    except Exception:
        return ""
    return ""


def sha(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------- las aristas

# (id, motor, origen, destino, rasteriza, plantilla)
# La plantilla recibe ENT (ruta dentro del contenedor) y SAL (ruta de salida).
CASOS = [
    # ---- LibreOffice: la vía ofimática clásica ------------------------------
    ("L01", "libreoffice", "docx", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/trabajo", e]),
    ("L02", "libreoffice", "odt", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/trabajo", e]),
    ("L03", "libreoffice", "rtf", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/trabajo", e]),
    ("L04", "libreoffice", "html", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/trabajo", e]),
    ("L05", "libreoffice", "txt", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/trabajo", e]),
    ("L06", "libreoffice", "docx", "odt", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "odt", "--outdir", "/trabajo", e]),
    ("L07", "libreoffice", "odt", "docx", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "docx", "--outdir", "/trabajo", e]),
    ("L08", "libreoffice", "docx", "html", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "html", "--outdir", "/trabajo", e]),
    # el que RASTERIZA: mismo motor, mismo origen, y pierde el texto entero
    ("L09", "libreoffice", "docx", "png", True,
     lambda e, s: ["soffice", "--headless", "--convert-to", "png", "--outdir", "/trabajo", e]),
    # el que se espera NOMINAL: es la mitad del hallazgo
    ("L10", "libreoffice", "epub", "pdf", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/trabajo", e]),
    # L11 CUELGA y escribe ~1,5 MB/s de `.tmp` en el cwd hasta que se le mata.
    # L12 es la MISMA orden con el mismo filtro sobre ODT y tarda 6,2 s.
    ("L11", "libreoffice", "docx", "txt", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "txt:Text", "--outdir", "/trabajo", e]),
    ("L12", "libreoffice", "odt", "txt", False,
     lambda e, s: ["soffice", "--headless", "--convert-to", "txt:Text", "--outdir", "/trabajo", e]),

    # ---- Pandoc: markup -----------------------------------------------------
    ("P01", "pandoc", "md", "docx", False, lambda e, s: ["pandoc", e, "-o", s]),
    ("P02", "pandoc", "md", "html", False, lambda e, s: ["pandoc", "-s", e, "-o", s]),
    ("P03", "pandoc", "md", "epub", False, lambda e, s: ["pandoc", e, "-o", s]),
    ("P04", "pandoc", "docx", "md", False, lambda e, s: ["pandoc", e, "-o", s]),
    ("P05", "pandoc", "docx", "html", False, lambda e, s: ["pandoc", "-s", e, "-o", s]),
    ("P06", "pandoc", "docx", "rtf", False, lambda e, s: ["pandoc", "-s", e, "-o", s]),
    ("P07", "pandoc", "html", "docx", False, lambda e, s: ["pandoc", e, "-o", s]),
    ("P08", "pandoc", "html", "md", False, lambda e, s: ["pandoc", e, "-o", s]),
    ("P09", "pandoc", "epub", "md", False, lambda e, s: ["pandoc", e, "-o", s]),
    ("P10", "pandoc", "epub", "html", False, lambda e, s: ["pandoc", "-s", e, "-o", s]),
    ("P11", "pandoc", "md", "pdf", False,
     lambda e, s: ["pandoc", e, "--pdf-engine=xelatex", "-o", s]),
    ("P12", "pandoc", "docx", "pdf", False,
     lambda e, s: ["pandoc", e, "--pdf-engine=xelatex", "-o", s]),
    ("P13", "pandoc", "md", "odt", False, lambda e, s: ["pandoc", e, "-o", s]),
    ("P14", "pandoc", "docx", "epub", False, lambda e, s: ["pandoc", e, "-o", s]),
    ("P15", "pandoc", "md", "txt", False,
     lambda e, s: ["pandoc", e, "-t", "plain", "-o", s]),

    # ---- Calibre: ebooks, y la arista que decide el hito --------------------
    ("C01", "calibre", "epub", "pdf", False, lambda e, s: ["ebook-convert", e, s]),
    ("C02", "calibre", "epub", "docx", False, lambda e, s: ["ebook-convert", e, s]),
    ("C03", "calibre", "epub", "mobi", False, lambda e, s: ["ebook-convert", e, s]),
    ("C04", "calibre", "epub", "azw3", False, lambda e, s: ["ebook-convert", e, s]),
    ("C05", "calibre", "epub", "txt", False, lambda e, s: ["ebook-convert", e, s]),
    ("C06", "calibre", "epub", "html", False, lambda e, s: ["ebook-convert", e, s]),
    ("C07", "calibre", "docx", "epub", False, lambda e, s: ["ebook-convert", e, s]),
    ("C08", "calibre", "html", "epub", False, lambda e, s: ["ebook-convert", e, s]),
    ("C09", "calibre", "docx", "pdf", False, lambda e, s: ["ebook-convert", e, s]),
]


def una(caso, guardar_en: str) -> dict:
    cid, motor, o, d, rast, plantilla = caso
    entrada = os.path.join(ENT, f"entrada.{o}")
    if not os.path.isfile(entrada):
        return {"id": cid, "motor": motor, "origen": o, "destino": d,
                "rc": None, "motivo": "falta la entrada"}

    reg = {"id": cid, "motor": motor, "origen": o, "destino": d,
           "rasteriza_esperado": rast}
    t = DirectorioDeTrabajo(prefijo="filex-h5-")
    try:
        nombre_dentro = f"salida.{o}"          # el STEM decide el nombre que
        nombre_salida = f"salida.{d}"          # LibreOffice va a escribir
        argv = argv_docker(entrada, nombre_dentro, t.ruta,
                           plantilla(f"/ent/{nombre_dentro}", f"/trabajo/{nombre_salida}"))
        reg["argv"] = argv
        r = invocacion.ejecutar(argv, timeout=TIMEOUT, cwd=t.ruta)
        reg["rc"] = r.rc
        reg["ms"] = round(r.ms, 1)
        reg["agotado"] = r.agotado
        reg["motivo"] = r.motivo
        reg["err"] = (r.err or "")[-600:]

        # --- punto 5, tomado AQUÍ ---------------------------------------
        censo = t.censo()
        clave = os.path.abspath(t.ruta)
        reg["censo"] = censo["despues"][clave]
        reg["sobrantes"] = t.sobrantes([nombre_salida])

        dst = t.destino(nombre_salida)
        if os.path.isfile(dst):
            reg["bytes"] = os.path.getsize(dst)
            reg["sha256"] = sha(dst)
            txt = texto_de(dst)
            reg["caracteres"] = len(txt)
            reg["centinela"] = CENTINELA in txt
            reg["tabla_ax1"] = "AX-1" in txt
            os.makedirs(guardar_en, exist_ok=True)
            t.recoger(nombre_salida, os.path.join(guardar_en, f"{cid}_{o}2{d}.{d}"))
        else:
            reg["bytes"] = 0
            reg["caracteres"] = 0
            reg["centinela"] = False
            reg["tabla_ax1"] = False
    finally:
        t.cerrar()
    return reg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", default="")
    ap.add_argument("--salida", default=os.path.join(SAL, "sonda.json"))
    ap.add_argument("--out", default=os.path.join(SAL, "out"))
    a = ap.parse_args()

    # La consola de Windows es cp1252 y revienta con una flecha (igual que en
    # `cli.py`). Un arnés que muere al imprimir el nombre de una arista no mide.
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    solo = {x.strip() for x in a.solo.split(",") if x.strip()}
    casos = [c for c in CASOS if not solo or c[0] in solo]

    res = []
    t0 = time.time()
    for c in casos:
        reg = una(c, a.out)
        res.append(reg)
        print(f"{reg['id']:<4} {reg['motor']:<12} {reg['origen']:>5}→{reg['destino']:<5} "
              f"rc={reg.get('rc')} {reg.get('ms', 0):>8.0f} ms "
              f"{reg.get('bytes', 0):>9} B  car={reg.get('caracteres', 0):>6} "
              f"cent={'S' if reg.get('centinela') else 'n'} "
              f"sobra={len(reg.get('sobrantes') or {})}", flush=True)
    print(f"\ntotal {time.time() - t0:.1f} s")
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
