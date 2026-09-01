# -*- coding: utf-8 -*-
"""C35: siete entradas del hito 5, Gotenberg frente a filex-c13.

No conserva binarios: cada salida vive sólo en un directorio temporal.  El
contenedor lleva nombre único, --init y timeout DENTRO; el finally hace
docker rm -f porque docker ps no enumera los Created.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

RAIZ = Path(r"D:\Work\research\FileX")
ENTRADAS = RAIZ / "bench" / "salidas-hito5" / "entradas"
SALIDA = Path(__file__).with_name("c35_gotenberg.json")
GOT = "http://localhost:3200"
CASOS = ("docx", "epub", "html", "md", "odt", "rtf", "txt")


def lista_contenedores():
    p = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       errors="replace", timeout=20)
    return (p.stdout or "").splitlines()


def multipart(campos, ficheros):
    b = "----filex" + uuid.uuid4().hex
    out = bytearray()
    for nombre, valor in campos:
        out += (f"--{b}\r\nContent-Disposition: form-data; name=\"{nombre}\"\r\n\r\n"
                f"{valor}\r\n").encode()
    for nombre, fichero, datos in ficheros:
        out += (f"--{b}\r\nContent-Disposition: form-data; name=\"{nombre}\"; "
                f"filename=\"{fichero}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
        out += datos + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return b, bytes(out)


def gotenberg(ext, entrada):
    ruta = "/forms/chromium/convert/markdown" if ext == "md" else "/forms/libreoffice/convert"
    ficheros = [("files", entrada.name, entrada.read_bytes())]
    if ext == "md":
        # Chromium/markdown exige este punto de entrada, aunque convierta f.md.
        ficheros.insert(0, ("files", "index.html", b"<main>FILEX C35</main>"))
    b, cuerpo = multipart([], ficheros)
    req = urllib.request.Request(GOT + ruta, data=cuerpo, method="POST",
                                 headers={"Content-Type": "multipart/form-data; boundary=" + b})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            datos = r.read()
            return {"ruta": ruta, "http": r.status, "bytes": len(datos),
                    "sha256": hashlib.sha256(datos).hexdigest() if datos else "", "err": ""}
    except urllib.error.HTTPError as e:
        return {"ruta": ruta, "http": e.code, "bytes": 0, "sha256": "",
                "err": (e.read() or b"")[:240].decode("utf-8", "replace")}
    except Exception as e:
        return {"ruta": ruta, "http": -1, "bytes": 0, "sha256": "", "err": str(e)[:240]}


def orden_c13(ext, entrada, trabajo, nombre):
    # soffice deriva el nombre de salida del nombre de entrada, no de --outdir.
    dentro = "/ent/salida." + ext
    salida = "/trabajo/salida.pdf"
    if ext == "epub":
        motor = ["ebook-convert", dentro, salida]
    elif ext == "md":
        motor = ["pandoc", "-s", dentro, "--pdf-engine=xelatex", "-o", salida]
    else:
        motor = ["soffice", "--headless", "--convert-to", "pdf", "--outdir", "/trabajo", dentro]
    return ["docker", "run", "--rm", "--init", "--name", nombre, "--network", "none",
            "--entrypoint", "timeout",
            "--mount", f"type=bind,source={entrada},target={dentro},readonly",
            "--mount", f"type=bind,source={trabajo},target=/trabajo", "-w", "/trabajo",
            "-e", "HOME=/tmp", "filex-c13", "-k", "5", "45"] + motor


def c13(ext, entrada, trabajo, n):
    nombre = "filex-c35-" + n
    argv = orden_c13(ext, entrada, trabajo, nombre)
    try:
        p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           errors="replace", timeout=65, cwd=trabajo)
        rc, err = p.returncode, (p.stderr or "")[-240:]
    except subprocess.TimeoutExpired:
        rc, err = -9, "TIMEOUT_EXTERIOR"
    finally:
        # Es idempotente y cubre Created, Running y el caso --rm ya terminado.
        subprocess.run(["docker", "rm", "-f", nombre], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, errors="replace", timeout=25)
    f = Path(trabajo) / "salida.pdf"
    tam = f.stat().st_size if f.is_file() else 0
    return {"argv": argv, "rc": rc, "bytes": tam,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest() if tam else "", "err": err}


def main():
    anterior = None
    if SALIDA.is_file():
        anterior = json.loads(SALIDA.read_text(encoding="utf-8"))
    temporal = Path(tempfile.mkdtemp(prefix="filex-c35-"))
    antes = sorted(p.name for p in temporal.iterdir())
    res = {"contenedores_antes": lista_contenedores(), "temporal": str(temporal),
           "listado_temporal_antes": antes, "celdas": []}
    try:
        for i, ext in enumerate(CASOS):
            entrada = ENTRADAS / ("entrada." + ext)
            celda = temporal / ("c%02d" % i)
            celda.mkdir()
            g = gotenberg(ext, entrada)
            c = c13(ext, entrada, str(celda), uuid.uuid4().hex[:12])
            reg = {"entrada": ext, "gotenberg": g, "c13": c,
                                  "gotenberg_buena": g["http"] == 200 and g["bytes"] > 0,
                                  "c13_buena": c["rc"] == 0 and c["bytes"] > 0}
            if anterior:
                reg["primera_pasada"] = anterior["celdas"][i]
            res["celdas"].append(reg)
        res["listado_temporal_durante"] = sorted(p.name for p in temporal.iterdir())
        res["contenedores_despues"] = lista_contenedores()
    finally:
        shutil.rmtree(temporal)
    res["temporal_borrado"] = not temporal.exists()
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("celdas=%d salida=%s" % (len(res["celdas"]), SALIDA))


if __name__ == "__main__":
    main()
