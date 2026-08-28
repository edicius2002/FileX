#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerador de las 53 salidas del patron oro FUERA del repositorio.

Por que existe
--------------
En un worktree limpio, `bench/salidas-referencia/` solo trae `MANIFIESTO.md`,
`referencia.json` y `logs/`: las 53 salidas son binarios regenerables y no se
versionan (regla 6 de CLAUDE.md). Cualquier arnes que las necesite tiene que
reconstruirlas antes.

Fuentes de las ordenes
----------------------
- 36 vienen literales de `referencia.json` -> `ordenes` (motor externo).
- 3 son las conversiones de datos, que `referencia.json` describe en prosa
  porque el motor es Python; van implementadas aqui (ver el comentario de
  DATOS: el `conv_datos.py` de `bench/salidas-verificacion/` NO las reproduce).
- 14 no tienen orden en `referencia.json`. Se deducen de la orden HERMANA de
  la misma familia (misma calidad, mismas banderas) y del `pedido` de
  `bench/salidas-verificacion/trabajos.py`; dos de ellas hubo que SONDEARLAS
  porque la deduccion fallaba (`alpha_png-to.png8.png` y `trivial_mp4-to.webm`).
  Cada una lleva anotada su procedencia en el campo `procedencia` del JSON.

Disciplina (CLAUDE.md)
----------------------
- R5: `subprocess.run` sin shell, argumentos en array, `stdin=DEVNULL`,
  `timeout=` explicito.
- Trampa 21: cada orden corre en su propio directorio desechable, que se lista
  ANTES y DESPUES; todo fichero no pedido queda anotado.
- Trampa 25: se registra el `rc` de cada orden. Una salida de 0 bytes puede ser
  un proceso que no arranco.
- Trampa 19: este fichero se escribio con la herramienta de escritura, no por
  la shell.
- NO usa la GPU: ffmpeg va con `-threads 4` y codificadores de software,
  ImageMagick con `-limit thread 4`.

Uso
---
    python bench/salidas-firmas-cierre/_regenera53.py [DESTINO]
"""
import csv
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(RAIZ, "bench", "salidas-referencia")
SALIDAS_DIR = os.path.join(RAIZ, "bench", "salidas-firmas-cierre")

DESTINO_POR_DEFECTO = os.path.join(
    r"C:\Users\krato\AppData\Local\Temp\claude\D--Work-research-FileX",
    "01b89f8d-cf1d-46e6-a799-e30ab2d26676", "scratchpad", "REF53")

TIMEOUT_S = 300          # tope por orden, explicito; ninguna orden se acerca
NOTA_TIMEOUT = ("MEDIDO: la orden mas lenta de las 53 es el VP9 de "
                "video/tipico_mp4-to.webm, 27,1 y 30,1 s en dos tandas, es "
                "decir un 9-10 % del tope. Los 300 s valen para todas; no hace "
                "falta ninguna excepcion. (Cifras de tanda, no comparables "
                "entre tandas: CLAUDE.md §3.)")

# ---------------------------------------------------------------------------
# Las 14 salidas sin orden en referencia.json.
#   (salida_rel, entrada_rel, orden, procedencia)
# La orden usa nombres SIN ruta, igual que las 36 de referencia.json.
# ---------------------------------------------------------------------------
DEDUCIDAS = [
    ("audio/tipico_mp4-audio.flac", "corpus/video/tipico.mp4",
     "ffmpeg -threads 4 -i tipico.mp4 -vn -c:a flac out.flac",
     "hermana audio/tipico_mp4-audio.mp3 (-vn) + destino flac de "
     "audio/trivial_wav-to.flac (-c:a flac)"),

    ("imagen/16bit_tif-to-d16.png", "corpus/imagen/patologico_16bit.tif",
     "magick -limit thread 4 patologico_16bit.tif -depth 16 16bit_tif-to-d16.png",
     "hermana imagen/16bit_tif-to-d8.png con el 'profundidad_bits: 16' del "
     "pedido de trabajos.py"),

    ("imagen/16bit_tif-to.jpg", "corpus/imagen/patologico_16bit.tif",
     "magick -limit thread 4 patologico_16bit.tif -quality 85 16bit_tif-to.jpg",
     "todas las hermanas a JPEG usan -quality 85; referencia-nativa.md l.41 lo "
     "escribe como '16bit_tif-to.jpg q85'"),

    ("imagen/16bit_tif-to.webp", "corpus/imagen/patologico_16bit.tif",
     "magick -limit thread 4 patologico_16bit.tif -quality 80 16bit_tif-to.webp",
     "todas las hermanas a WebP con perdida usan -quality 80"),

    ("imagen/alpha_png-to.png8.png", "corpus/imagen/alpha.png",
     "magick -limit thread 4 alpha.png -depth 8 alpha_png-to.png8.png",
     "SONDEADO, no deducido: el escritor 'png8:' que sugiere el nombre da "
     "951 B y 2 colores, no los 2 780 B y 210 colores que declara "
     "referencia.json; '-depth 8' (el 'profundidad_bits: 8' del pedido de "
     "trabajos.py) da 2 780 B / PaletteAlpha / 210 colores, exacto"),

    ("imagen/tipico_jpg-to.png", "corpus/imagen/tipico.jpg",
     "magick -limit thread 4 tipico.jpg tipico_jpg-to.png",
     "PNG sin perdida: ninguna hermana a PNG lleva -quality"),

    ("imagen/tipico_webp-to.jpg", "corpus/imagen/tipico.webp",
     "magick -limit thread 4 tipico.webp -quality 85 tipico_webp-to.jpg",
     "hermanas a JPEG con -quality 85"),

    ("imagen/tipico_webp-to.png", "corpus/imagen/tipico.webp",
     "magick -limit thread 4 tipico.webp tipico_webp-to.png",
     "PNG sin perdida"),

    ("imagen/trivial_png-to.jpg", "corpus/imagen/trivial.png",
     "magick -limit thread 4 trivial.png -quality 85 trivial_png-to.jpg",
     "hermanas a JPEG con -quality 85"),

    ("pdf/alpha_png-to.pdf", "corpus/imagen/alpha.png",
     "magick -limit thread 4 alpha.png alpha_png-to.pdf",
     "hermana pdf/tipico_png-to.pdf (sin -density); referencia.json declara "
     "pagina1_pt 200x200, es decir 1 px -> 1 pt sobre un PNG de 200x200"),

    ("pdf/patologico_escaneado_pdf-to-p1.png", "corpus/pdf/patologico_escaneado.pdf",
     "gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=png16m -r150 "
     "-dNumRenderingThreads=4 -sOutputFile=%d.png patologico_escaneado.pdf",
     "hermana pdf/tipico_texto_pdf-to-p1.png; el pedido de trabajos.py fija "
     "dpi 150 y el sufijo '-p1' la pagina 1"),

    ("pdf/tipico_jpg-to.pdf", "corpus/imagen/tipico.jpg",
     "magick -limit thread 4 tipico.jpg tipico_jpg-to.pdf",
     "hermana pdf/tipico_png-to.pdf (sin -density); referencia.json declara "
     "pagina1_pt 1920x1080"),

    ("pdf/trivial_pdf-to-p1.png", "corpus/pdf/trivial.pdf",
     "gswin64c -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=png16m -r150 "
     "-dNumRenderingThreads=4 -sOutputFile=%d.png trivial.pdf",
     "hermana pdf/tipico_texto_pdf-to-p1.png; pedido dpi 150, pagina 1"),

    ("video/trivial_mp4-to.webm", "corpus/video/trivial.mp4",
     "ffmpeg -threads 4 -i trivial.mp4 -c:v libvpx-vp9 -crf 32 -b:v 0 -row-mt 1 "
     "-deadline good -cpu-used 4 -c:a libopus -b:a 96k out.webm",
     "hermana video/tipico_mp4-to.webm PERO con -crf 32, no 33: SONDEADO. "
     "El -crf 33 literal da 607 029 B; barriendo crf 30/31/32/34 y cpu-used "
     "0/1/2/3/5, solo -crf 32 reproduce los 635 908 B del patron oro "
     "(trivial.mp4 no tiene audio, asi que -c:a libopus queda inerte)"),
]

# Las tres conversiones de datos: motor Python, no linea de ordenes.
#
# OJO: `bench/salidas-verificacion/conv_datos.py` NO las reproduce. Difiere en
# dos parametros, y los dos se han SONDEADO contra el sha256 del patron oro:
#   1. abre el CSV con `newline=""`, asi que el salto embebido en el campo
#      "salto\r\nde linea" llega con CR y la salida normalizada pesa 86 B en vez
#      de 85. El patron oro se hizo con saltos universales (sin `newline=""`).
#   2. vuelca el JSON con `indent=1`; el patron oro usa `indent=2` (174 B).
# Con esos dos cambios las tres dan `exacta`. Aqui van implementadas, en vez de
# tocar un arnes compartido que no es mio.
DATOS = [
    ("datos/patologico_bom_csv-to.json", "corpus/datos/patologico_bom.csv",
     "dat.csv2json"),
    ("datos/patologico_bom_csv-to-normalizado.csv", "corpus/datos/patologico_bom.csv",
     "dat.csv2csv"),
    ("datos/tipico_json-to.csv", "corpus/datos/tipico.json", "dat.json2csv"),
]


def conversion_de_datos(oid, entrada, salida):
    """Las tres conversiones de datos del patron oro, en proceso.

    Motor: biblioteca estandar de Python 3.11, tal como declara
    `referencia.json` -> meta.motores.python.
    """
    if oid == "dat.csv2json":
        with open(entrada, encoding="utf-8-sig") as fh:   # saltos universales
            filas = list(csv.reader(fh))
        cab, cuerpo = filas[0], filas[1:]
        obj = [dict(zip(cab, f)) for f in cuerpo]
        with open(salida, "w", encoding="utf-8", newline="") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
    elif oid == "dat.csv2csv":
        with open(entrada, encoding="utf-8-sig") as fh:   # saltos universales
            filas = list(csv.reader(fh))
        with open(salida, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerows(filas)
    elif oid == "dat.json2csv":
        with open(entrada, encoding="utf-8") as fh:
            obj = json.load(fh)
        filas = obj["items"] if isinstance(obj, dict) and "items" in obj else obj
        if filas and isinstance(filas[0], dict):
            cab = list(filas[0].keys())
            datos = [[f.get(k, "") for k in cab] for f in filas]
        else:
            cab, datos = ["valor"], [[x] for x in filas]
        with open(salida, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(cab)
            w.writerows(datos)
    else:
        raise ValueError("orden de datos desconocida: %s" % oid)


# Mecanismos de no-reproducibilidad, SONDEADOS corriendo la misma orden dos
# veces en la misma tanda (si dos ejecuciones difieren entre si, el motor no es
# reproducible; si coinciden y aun asi no dan el patron oro, la causa es otra).
MECANISMOS = {
    "magick-png": "magick estampa tEXt date:create / date:modify / "
                  "date:timestamp con el reloj de pared (10 bytes cambian entre "
                  "dos ejecuciones de la MISMA orden)",
    "magick-pdf": "magick estampa /CreationDate y /ModDate (trampa 22 de "
                  "CLAUDE.md: SOURCE_DATE_EPOCH no lo evita)",
    "gs-pdfwrite": "Ghostscript pdfwrite estampa /CreationDate, /ModDate y un "
                   "/ID aleatorio; ademas el tamano oscila (3 282 / 3 284 / "
                   "3 291 B) porque cambian los desplazamientos del xref",
    "gs-tiff": "el TIFF de Ghostscript lleva la etiqueta DateTime; dos "
               "ejecuciones en el mismo segundo COINCIDEN y separadas en el "
               "tiempo NO (90048c48… en la tanda larga, c90e62b8… en el sondeo)",
    "matroska": "el muxer Matroska escribe un SegmentUID aleatorio y la fecha "
                "de segmento (60 bytes cambian entre dos ejecuciones)",
    "ogg": "el flujo Ogg lleva un numero de serie aleatorio (88 bytes cambian "
           "entre dos ejecuciones)",
}

# Motor no reproducible por salida (solo se anota cuando el veredicto no es
# 'exacta'; si una fila de esta tabla saliera 'exacta', mejor para todos).
NO_REPRODUCIBLE = {
    "audio/tipico_flac-to.opus": "ogg",
    "audio/trivial_wav-to.opus": "ogg",
    "imagen/16bit_tif-to-d16.png": "magick-png",
    "imagen/16bit_tif-to-d8.png": "magick-png",
    "imagen/16bit_tif-to-default.png": "magick-png",
    "imagen/alpha_png-to.png8.png": "magick-png",
    "imagen/tipico_jpg-to.png": "magick-png",
    "imagen/tipico_webp-to.png": "magick-png",
    "pdf/alpha_png-to.pdf": "magick-pdf",
    "pdf/tipico_jpg-to.pdf": "magick-pdf",
    "pdf/tipico_png-to-150dpi.pdf": "magick-pdf",
    "pdf/tipico_png-to.pdf": "magick-pdf",
    "pdf/tipico_texto_rasterizado.pdf": "magick-pdf",
    "pdf/tipico_texto_pdf-to-gs.pdf": "gs-pdfwrite",
    "pdf/tipico_texto_pdf-to.tif": "gs-tiff",
    "video/tipico_mp4-to.mkv": "matroska",
    "video/tipico_mp4-to.webm": "matroska",
    "video/trivial_mp4-to.webm": "matroska",
}

# Salidas cuya ENTRADA es otra salida del patron oro (hay que ordenarlas).
ENCADENADAS = {"pdf/tipico_texto_rasterizado.pdf"}


def sha256_de(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for trozo in iter(lambda: fh.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def producido_por(argv):
    """Nombre del fichero que la orden escribe DENTRO del cwd.

    No se adivina: se lee de la propia orden.
      - gswin64c: el valor de -sOutputFile=, con %d resuelto a la pagina 1.
      - magick / ffmpeg: el ultimo argumento.
    """
    exe = os.path.basename(argv[0]).lower()
    if exe.startswith("gswin64c"):
        for a in argv:
            if a.startswith("-sOutputFile="):
                v = a.split("=", 1)[1]
                return v.replace("%d", "1"), ("%d" in v)
        raise ValueError("orden de Ghostscript sin -sOutputFile: %r" % (argv,))
    ultimo = argv[-1]
    # ImageMagick admite un prefijo de ESCRITOR ("png8:salida.png"); el fichero
    # que aparece en el cwd es lo que va detras de los dos puntos.
    m = re.match(r"^[A-Za-z][A-Za-z0-9]{1,9}:(?=.)", ultimo)
    if m and not re.match(r"^[A-Za-z]:[\/]", ultimo):
        ultimo = ultimo[m.end():]
    return ultimo, False


def cargar_filas():
    with open(os.path.join(REF, "referencia.json"), encoding="utf-8") as fh:
        ref = json.load(fh)

    por_nombre = {}
    for s in ref["salidas"]:
        sub = os.path.basename(os.path.dirname(s["ruta"]))
        por_nombre["%s/%s" % (sub, s["nombre"])] = s

    filas = []
    vistas = set()

    for o in ref["ordenes"]:
        rel = o["salida"]
        if rel.startswith("datos/"):
            continue  # las tres de datos van por conv_datos.py
        filas.append({
            "salida": rel,
            "entrada": o["entrada"],
            "orden": o["orden"],
            "motor_declarado": o.get("motor"),
            "procedencia": "referencia.json -> ordenes[%s]" % o["id"],
        })
        vistas.add(rel)

    for rel, ent, orden, proc in DEDUCIDAS:
        assert rel not in vistas, rel
        filas.append({"salida": rel, "entrada": ent, "orden": orden,
                      "motor_declarado": None, "procedencia": proc})
        vistas.add(rel)

    for rel, ent, oid in DATOS:
        assert rel not in vistas, rel
        filas.append({"salida": rel, "entrada": ent, "orden": None,
                      "oid_datos": oid, "motor_declarado": "Python 3.11 stdlib",
                      "procedencia": "bench/salidas-verificacion/conv_datos.py "
                                     "(%s), que reimplementa la prosa de "
                                     "referencia.json" % oid})
        vistas.add(rel)

    # las encadenadas van al final: su entrada es una salida ya generada
    filas.sort(key=lambda f: (f["salida"] in ENCADENADAS, f["salida"]))
    return ref, por_nombre, filas


def ruta_entrada(entrada_rel, destino):
    """La entrada puede ser del corpus o una salida ya regenerada."""
    if entrada_rel.startswith("salidas/"):
        return os.path.join(destino, entrada_rel[len("salidas/"):]
                            .replace("/", os.sep))
    return os.path.join(RAIZ, entrada_rel.replace("/", os.sep))


def main():
    destino = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 \
        else DESTINO_POR_DEFECTO
    ref, por_nombre, filas = cargar_filas()

    for sub in ("audio", "datos", "imagen", "pdf", "video"):
        os.makedirs(os.path.join(destino, sub), exist_ok=True)

    log = open(os.path.join(SALIDAS_DIR, "log-regenera53.txt"), "w",
               encoding="utf-8", newline="\n")

    def p(txt=""):
        print(txt)
        log.write(txt + "\n")
        log.flush()

    p("# Regeneracion de las 53 salidas del patron oro")
    p("raiz          : %s" % RAIZ)
    p("destino       : %s" % destino)
    p("filas         : %d" % len(filas))
    p("timeout       : %d s por orden" % TIMEOUT_S)
    p("NOTA timeout  : %s" % NOTA_TIMEOUT)
    p("GPU           : NO se usa (ffmpeg -threads 4 software, magick -limit thread 4)")
    p("")

    resultados = []
    t0_global = time.perf_counter()

    for i, f in enumerate(filas, 1):
        rel = f["salida"]
        sub, nombre = rel.split("/", 1)
        destino_final = os.path.join(destino, sub, nombre)
        ent = ruta_entrada(f["entrada"], destino)

        fila = {
            "salida": rel,
            "entrada": f["entrada"],
            "orden": f["orden"],
            "procedencia": f["procedencia"],
            "motor_declarado": f.get("motor_declarado"),
            "rc": None,
            "timeout_s": TIMEOUT_S,
            "bytes_obt": None,
            "bytes_ref": None,
            "sha_obt": None,
            "sha_ref": None,
            "veredicto": None,
            "ms": None,
            "extras_cwd": [],
            "stderr_resumen": "",
            "motivo_no_exacta": None,
        }
        s_ref = por_nombre.get(rel)
        if s_ref:
            fila["bytes_ref"] = s_ref["bytes"]
            fila["sha_ref"] = s_ref["sha256"]

        p("[%2d/%d] %s" % (i, len(filas), rel))

        if not os.path.exists(ent):
            fila["veredicto"] = "ausente"
            fila["stderr_resumen"] = "entrada inexistente: %s" % ent
            p("        ENTRADA AUSENTE: %s" % ent)
            resultados.append(fila)
            continue

        # --- directorio de trabajo desechable (R18 + trampa 21) -------------
        trabajo = tempfile.mkdtemp(prefix="ref53-", suffix="-" + nombre[:20]
                                   .replace(".", "_"))
        try:
            base_ent = os.path.basename(ent)
            shutil.copy2(ent, os.path.join(trabajo, base_ent))
            antes = set(os.listdir(trabajo))

            t0 = time.perf_counter()
            if f["orden"] is None:
                # motor Python: en proceso, no hay subproceso que lanzar
                producido, multipagina = nombre, False
                err = ""
                try:
                    conversion_de_datos(
                        f["oid_datos"], os.path.join(trabajo, base_ent),
                        os.path.join(trabajo, nombre))
                    fila["rc"] = 0
                except Exception as exc:          # noqa: BLE001
                    fila["rc"] = "excepcion"
                    err = "%s: %s" % (type(exc).__name__, exc)
            else:
                argv = shlex.split(f["orden"], posix=True)
                producido, multipagina = producido_por(argv)
                try:
                    pr = subprocess.run(
                        argv, cwd=trabajo, stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        timeout=fila["timeout_s"])
                    fila["rc"] = pr.returncode
                    err = pr.stderr.decode("utf-8", "replace")
                except subprocess.TimeoutExpired:
                    fila["rc"] = "timeout"
                    err = "TimeoutExpired tras %d s" % fila["timeout_s"]
                except FileNotFoundError as exc:
                    fila["rc"] = "no-existe-el-ejecutable"
                    err = str(exc)
            fila["ms"] = round((time.perf_counter() - t0) * 1000, 1)

            # resumen de stderr: ultimas lineas no vacias, recortadas
            lineas = [l.strip() for l in err.splitlines() if l.strip()]
            fila["stderr_resumen"] = " | ".join(lineas[-3:])[:400]

            despues = set(os.listdir(trabajo))
            nuevos = sorted(despues - antes)

            ruta_prod = os.path.join(trabajo, producido)
            if os.path.exists(ruta_prod):
                shutil.move(ruta_prod, destino_final)
                nuevos = [n for n in nuevos if n != producido]

            # trampa 21: todo lo que el motor dejo y nadie pidio
            for n in nuevos:
                ruta_n = os.path.join(trabajo, n)
                fila["extras_cwd"].append({
                    "nombre": n,
                    "bytes": os.path.getsize(ruta_n) if os.path.isfile(ruta_n) else None,
                    "clase": "pagina_extra" if multipagina and n[:-4].isdigit()
                             else "satelite_no_pedido",
                })
        finally:
            shutil.rmtree(trabajo, ignore_errors=True)

        # --- comparacion contra el patron oro -------------------------------
        if not os.path.exists(destino_final):
            fila["veredicto"] = "ausente"
        else:
            fila["bytes_obt"] = os.path.getsize(destino_final)
            fila["sha_obt"] = sha256_de(destino_final)
            if fila["sha_ref"] is None:
                fila["veredicto"] = "sin_referencia"
            elif fila["sha_obt"] == fila["sha_ref"]:
                fila["veredicto"] = "exacta"
            elif fila["bytes_obt"] == fila["bytes_ref"]:
                fila["veredicto"] = "mismo_tamano"
            else:
                fila["veredicto"] = "distinta"

        if fila["veredicto"] != "exacta":
            clave = NO_REPRODUCIBLE.get(rel)
            fila["motivo_no_exacta"] = MECANISMOS[clave] if clave else                 "SIN EXPLICAR: no es un motor no reproducible conocido"

        p("        rc=%-4s %8s ms  %10s B (ref %10s)  -> %s"
          % (fila["rc"], fila["ms"],
             fila["bytes_obt"], fila["bytes_ref"], fila["veredicto"]))
        if fila["extras_cwd"]:
            p("        EXTRAS en el cwd: %s"
              % ", ".join("%s (%s B, %s)" % (e["nombre"], e["bytes"], e["clase"])
                          for e in fila["extras_cwd"]))
        if fila["veredicto"] in ("ausente",) or fila["rc"] not in (0, None):
            p("        stderr: %s" % fila["stderr_resumen"])

        resultados.append(fila)

    total_ms = round((time.perf_counter() - t0_global) * 1000, 1)

    recuento = {}
    for r in resultados:
        recuento[r["veredicto"]] = recuento.get(r["veredicto"], 0) + 1

    satelites = [{"salida": r["salida"], "extras": r["extras_cwd"]}
                 for r in resultados if r["extras_cwd"]]

    resumen = {
        "generado": time.strftime("%Y-%m-%d %H:%M:%S"),
        "destino": destino,
        "n_filas": len(resultados),
        "recuento": recuento,
        "n_ordenes_de_referencia_json": sum(
            1 for r in resultados if r["procedencia"].startswith("referencia.json")),
        "n_deducidas": len(DEDUCIDAS),
        "n_datos_python": len(DATOS),
        "ms_total": total_ms,
        "timeout_s": TIMEOUT_S,
        "nota_timeout": NOTA_TIMEOUT,
        "salidas_con_extras_en_cwd": satelites,
        "mecanismos_de_no_reproducibilidad": MECANISMOS,
        "gpu": "no usada",
        "aviso_tiempos": ("los ms son informativos: la maquina comparte carga, "
                          "no son una medida (CLAUDE.md §3)"),
    }

    with open(os.path.join(SALIDAS_DIR, "regenera53.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump({"resumen": resumen, "filas": resultados}, fh,
                  ensure_ascii=False, indent=1)

    p("")
    p("# Resumen")
    for k in sorted(recuento):
        p("  %-14s %d" % (k, recuento[k]))
    p("  total          %d en %.1f s" % (len(resultados), total_ms / 1000.0))
    p("")
    p("# No exactas")
    for r in resultados:
        if r["veredicto"] != "exacta":
            p("  %-45s %-13s rc=%-4s obt=%s ref=%s"
              % (r["salida"], r["veredicto"], r["rc"],
                 r["bytes_obt"], r["bytes_ref"]))
            p("      motivo: %s" % r["motivo_no_exacta"])
    log.close()


if __name__ == "__main__":
    main()
