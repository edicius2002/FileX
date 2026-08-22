# -*- coding: utf-8 -*-
"""Genera `bench/salidas-sondeo-ff/MANIFIESTO.md` y borra las salidas binarias.

§6 de `CLAUDE.md`: las salidas regenerables no se versionan; lo que se versiona
es el nombre, el `sha256`, el tamaño y **la orden exacta que las reproduce**.

Una salvedad que hay que dejar escrita: **los contenedores de ffmpeg NO son
reproducibles byte a byte.** MP4/MOV estampan `mvhd.creation_time` y Matroska
un `DateUTC`, así que el `sha256` de una repetición no coincide con el de la
tanda. Se publica igual, porque identifica el fichero que se midió, pero el
criterio de reproducción es la ORDEN, no el resumen.

Uso:  python bench/salidas-sondeo-ff/escribir_manifiesto.py <dir_trabajo> [--borrar]
"""
import hashlib
import json
import os
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    trabajo = os.path.abspath(sys.argv[1])
    borrar = "--borrar" in sys.argv
    with open(os.path.join(trabajo, "resultados.json"), encoding="utf-8") as fh:
        crudo = json.load(fh)
    with open(os.path.join(trabajo, "fuentes", "fuentes.json"), encoding="utf-8") as fh:
        fu = json.load(fh)

    L = []
    L.append("# MANIFIESTO — `bench/salidas-sondeo-ff/`\n")
    L.append("Sondeo de las **70 aristas `sin_sondear` de ffmpeg**. "
             "Informe: `bench/sondeo-ffmpeg.md`.\n")
    L.append("**Build medido:** `%s`. Una medida de otro build **no se aplica** "
             "(`filex/sondeo.py`).\n" % crudo["build"])
    L.append("**Los contenedores de ffmpeg no son reproducibles byte a byte** "
             "—MP4/MOV estampan `mvhd.creation_time`, Matroska un `DateUTC`—, "
             "así que el `sha256` identifica el fichero que se midió, no un "
             "objetivo a reproducir. Lo reproducible es **la orden**.\n")
    L.append("Todas las salidas binarias de esta tanda **se han borrado**: "
             "eran %d ficheros y ~%.0f MB.\n"
             % (len(crudo["aristas"]),
                sum((v.get("ffprobe") or {}).get("bytes", 0)
                    for v in crudo["aristas"].values()) / 1e6))

    L.append("\n## 1. Fuentes derivadas (el corpus no trae `.webm`, `.mov`, "
             "`.avi`, `.m4a`, `.opus`, `.ogg`)\n")
    L.append("Se generan con `python bench/salidas-sondeo-ff/preparar_fuentes.py "
             "<dir>`. Todas las de vídeo salen de "
             "`corpus/video/patologico_2pistas.mkv`, que lleva **dos pistas de "
             "audio**: así cada arista de vídeo vigila de paso `-map 0`.\n")
    L.append("| fichero | bytes | sha256 | orden |")
    L.append("|---|---:|---|---|")
    def limpia(x):
        for pre in (trabajo, trabajo.replace("\\", "/"), RAIZ, RAIZ.replace("\\", "/")):
            x = x.replace(pre + "\\", "<dir>/").replace(pre + "/", "<dir>/")
        return x.replace("<dir>/corpus", "corpus").replace("\\", "/")

    for ext in sorted(fu["meta"]):
        m = fu["meta"][ext]
        argv = m["argv"]
        orden = ("*(del corpus: `%s`)*" % os.path.relpath(m["origen"], RAIZ).replace("\\", "/")
                 if not argv else
                 "`" + " ".join(limpia(x) for x in argv) + "`")
        L.append("| `f.%s` | %d | `%s` | %s |" % (ext, m["bytes"], m["sha256"], orden))

    L.append("\n## 2. Las 70 salidas del sondeo\n")
    L.append("Se generan con `python bench/salidas-sondeo-ff/sondear_ff.py <dir> 3`, "
             "que para cada arista sustituye el grafo por uno de **una sola "
             "arista** y llama a `FileX.convertir()` — con el desechable, el "
             "censo del punto 5 y el contrato dentro. La orden literal que "
             "`motores.FFmpeg.orden()` construye está en el campo "
             "`diagnostico.argv` de `resultados.json` para cada `nominal`.\n")
    L.append("| arista | estado | bytes | sha256 | ms (mediana n=3) |")
    L.append("|---|---|---:|---|---:|")
    sal = os.path.join(trabajo, "salidas")
    for clave in sorted(crudo["aristas"]):
        v = crudo["aristas"][clave]
        o, d = clave.split(">")
        p = os.path.join(sal, "%s2%s.%s" % (o, d, d))
        if not os.path.isfile(p):
            p = os.path.join(trabajo, "diagnostico", "%s2%s" % (o, d), "salida.%s" % d)
        if os.path.isfile(p) and os.path.getsize(p):
            h, n = sha(p), os.path.getsize(p)
        else:
            h, n = "—", 0
        L.append("| `%s` | %s | %s | `%s` | %s |"
                 % (clave, v["estado"], n or "—", h, v["ms"] if v["ms"] else "—"))

    L.append("\n## 3. Lo que SÍ queda versionado\n")
    L.append("| fichero | qué es |")
    L.append("|---|---|")
    L.append("| `preparar_fuentes.py` | genera las 7 fuentes derivadas |")
    L.append("| `sondear_ff.py` | el arnés del sondeo |")
    L.append("| `reparacion_verificador.py` | re-sondeo con los dos parches de la sonda en memoria |")
    L.append("| `escribir_json.py` | vuelca `filex/sondeo/ffmpeg.json` |")
    L.append("| `escribir_manifiesto.py` | este fichero |")
    L.append("| `resultados.json` | el crudo: rc, veredicto, hallazgos, censo, testigos, diagnóstico |")
    L.append("| `reparacion.json` | qué aristas recupera arreglar la sonda |")
    L.append("| `reparacion_gif.py` / `gif.json` | la escalera `-map 0` → `-map 0:v:0` → escala declarada |")

    with open(os.path.join(AQUI, "MANIFIESTO.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    for n in ("resultados.json", "reparacion.json", "gif.json"):
        p = os.path.join(trabajo, n)
        if os.path.isfile(p):
            shutil.copy(p, os.path.join(AQUI, n))
    print("MANIFIESTO.md escrito")
    if borrar:
        for n in ("salidas", "diagnostico", "reparadas", "fuentes"):
            shutil.rmtree(os.path.join(trabajo, n), ignore_errors=True)
        print("salidas binarias borradas")


if __name__ == "__main__":
    main()
