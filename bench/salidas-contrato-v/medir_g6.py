#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C27 — ¿se puede subir G6 de `aviso` a `fallo`?

G6 dice: *si la salida tiene la MISMA firma que la entrada y no era eso lo que
se pedia, es sospechosa*. Hoy es `aviso` porque esta calibrada sobre 22 casos
de UN SOLO MOTOR (`bench/firmas-contrato.md` §7.1, §10.5). Subirla exige dos
cosas, y aqui se miden las dos:

  A. MAS MOTORES. ¿Es «devolver el formato de la entrada cuando la extension no
     se reconoce» una manera de fallar de ImageMagick, o de los motores en
     general? Se prueba con `magick`, `ffmpeg`, `gswin64c` y los del contenedor.

  B. FALSOS POSITIVOS sobre conversiones LEGITIMAS entre formatos equivalentes.
     El inventario nombra `png -> apng` y `mkv -> mka`; hay mas, y la busqueda
     no es a ojo: G6 solo puede dispararse cuando la extension de destino NO
     esta en `EXT_A_FIRMAS`, asi que el conjunto de riesgo es exactamente
     `EXT_SIN_FIRMA` (112 extensiones) mas lo que no este en el vocabulario.

Cada celda registra su `rc` (trampa 25) y todo corre en un desechable que se
lista antes y despues (R21). Los contenedores se censan con `docker ps -a`
(trampa 37) y no se crea ninguno: solo `docker exec` sobre los que ya viven.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex import verificador as V  # noqa: E402

TIMEOUT = 120
CONTENEDOR = "filex-convertx"
GS = "gswin64c"


def correr(orden, timeout=TIMEOUT):
    try:
        p = subprocess.run(orden, capture_output=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        return p.returncode, p.stderr.decode("utf-8", "replace")[-300:]
    except subprocess.TimeoutExpired:
        return -9, "timeout %ss" % timeout
    except OSError as e:
        return -1, str(e)[:200]


def g6(entrada, salida, rc):
    """Aplica el contrato entero y devuelve si G6 disparo."""
    if not os.path.exists(salida):
        return None
    r = V.verificar(salida, {"rc": rc}, entrada)
    reglas = [h["regla"] for h in r["hallazgos"]]
    return {"veredicto": r["veredicto"], "punto1": r["punto1"],
            "G6": "G6" in reglas, "reglas": sorted(set(reglas)),
            "firma_salida": V.firma_real(salida),
            "firma_entrada": V.firma_real(entrada),
            "bytes": os.path.getsize(salida)}


# ---------------------------------------------------------------------------
# A. MAS MOTORES: destinos que el motor no puede reconocer.
#    22 pseudoformatos de ImageMagick (los de firmas-contrato §7.1) + un
#    puñado de extensiones inventadas, que es el caso real de un usuario.
IM_PSEUDO = ["b", "c", "g", "k", "m", "o", "r", "y", "p7", "preview",
             "data", "flif", "group4", "histogram", "inline", "msl", "mvg",
             "null", "pocketmod", "sparse", "vid", "clipboard"]
INVENTADAS = ["zzz", "xyz", "formato", "dat", "out"]


def parte_a(dur):
    filas = []
    png = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
    mp4 = os.path.join(RAIZ, "corpus", "video", "tipico.mp4")
    pdf = os.path.join(RAIZ, "corpus", "pdf", "tipico_texto.pdf")
    flac = os.path.join(RAIZ, "corpus", "audio", "tipico.flac")

    # --- ImageMagick: la replica del caso conocido -------------------------
    for ext in IM_PSEUDO + INVENTADAS:
        dst = os.path.join(dur, "im_tipico.%s" % ext)
        rc, err = correr(["magick", "-limit", "thread", "4", png,
                          "-auto-orient", dst])
        filas.append({"motor": "magick", "entrada": "tipico.png", "ext": ext,
                      "rc": rc, "err": err if rc else None, "g6": g6(png, dst, rc)})

    # --- ffmpeg: video y audio hacia una extension que no existe -----------
    for fuente, nom in ((mp4, "tipico.mp4"), (flac, "tipico.flac")):
        for ext in INVENTADAS + ["group4", "vid", "null"]:
            dst = os.path.join(dur, "ff_%s.%s" % (os.path.basename(fuente).split(".")[0], ext))
            rc, err = correr(["ffmpeg", "-y", "-v", "error", "-nostdin",
                              "-i", fuente, "-map", "0", "-c", "copy", dst])
            filas.append({"motor": "ffmpeg", "entrada": nom, "ext": ext,
                          "rc": rc, "err": err if rc else None,
                          "g6": g6(fuente, dst, rc)})

    # --- Ghostscript: sin -sDEVICE, y con un dispositivo que no existe -----
    for ext in INVENTADAS:
        dst = os.path.join(dur, "gs_tipico.%s" % ext)
        rc, err = correr([GS, "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                          "-sOutputFile=" + dst, pdf])
        filas.append({"motor": "ghostscript", "entrada": "tipico_texto.pdf",
                      "ext": ext, "rc": rc, "err": err if rc else None,
                      "g6": g6(pdf, dst, rc)})
    return filas


# ---------------------------------------------------------------------------
# A2. Los motores del CONTENEDOR. No se crea ningun contenedor: `docker exec`
#     sobre el que ya vive, con el tope DENTRO (`timeout -k 5`).
CONT = [
    ("vips", ["vips", "copy", "/tmp/g6/tipico.png", "/tmp/g6/vips_out.%s"]),
    ("magick_cont", ["magick", "/tmp/g6/tipico.png", "/tmp/g6/magickc_out.%s"]),
    ("pandoc", ["pandoc", "/tmp/g6/semilla.md", "-o", "/tmp/g6/pandoc_out.%s"]),
    ("soffice", ["soffice", "--headless", "--convert-to", "%s",
                 "--outdir", "/tmp/g6", "/tmp/g6/semilla.md"]),
    ("inkscape", ["inkscape", "/tmp/g6/semilla.svg",
                  "--export-filename=/tmp/g6/inkscape_out.%s"]),
]


def parte_a2(dur):
    filas = []
    rc, err = correr(["docker", "exec", CONTENEDOR, "sh", "-c",
                      "rm -rf /tmp/g6 && mkdir -p /tmp/g6"], 60)
    if rc != 0:
        return [{"motor": "contenedor", "error": "no accesible: %s" % err}]
    # semillas dentro del contenedor
    png = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")
    correr(["docker", "cp", png, "%s:/tmp/g6/tipico.png" % CONTENEDOR], 120)
    sem_md = os.path.join(dur, "semilla.md")
    with open(sem_md, "w", encoding="utf-8") as fh:
        fh.write("Prosa llana sin titulo, para no repetir el sesgo de semilla\n"
                 "de firmas-contrato §2.3.\n")
    sem_svg = os.path.join(dur, "semilla.svg")
    with open(sem_svg, "w", encoding="utf-8") as fh:
        fh.write('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40">'
                 '<rect width="80" height="40" fill="#248"/></svg>\n')
    correr(["docker", "cp", sem_md, "%s:/tmp/g6/semilla.md" % CONTENEDOR], 60)
    correr(["docker", "cp", sem_svg, "%s:/tmp/g6/semilla.svg" % CONTENEDOR], 60)
    local = {"vips": png, "magick_cont": png, "pandoc": sem_md,
             "soffice": sem_md, "inkscape": sem_svg}
    for nombre, plantilla in CONT:
        for ext in INVENTADAS:
            orden = [x.replace("%s", ext) if "%s" in x else x for x in plantilla]
            rc, err = correr(["docker", "exec", CONTENEDOR,
                              "timeout", "-k", "5", "60"] + orden, 90)
            # sacar lo que haya escrito
            trae = subprocess.run(["docker", "exec", CONTENEDOR, "sh", "-c",
                                   "ls /tmp/g6"], capture_output=True, timeout=60,
                                  stdin=subprocess.DEVNULL)
            nombres = trae.stdout.decode("utf-8", "replace").split()
            cand = [n for n in nombres if n.endswith("." + ext)]
            fila = {"motor": nombre, "ext": ext, "rc": rc,
                    "err": err if rc else None, "escribio": cand}
            if cand:
                dst = os.path.join(dur, "cont_%s_%s" % (nombre, cand[0]))
                correr(["docker", "cp", "%s:/tmp/g6/%s" % (CONTENEDOR, cand[0]),
                        dst], 120)
                if os.path.exists(dst):
                    fila["g6"] = g6(local[nombre], dst, rc)
                correr(["docker", "exec", CONTENEDOR, "rm", "-f",
                        "/tmp/g6/" + cand[0]], 60)
            filas.append(fila)
    correr(["docker", "exec", CONTENEDOR, "rm", "-rf", "/tmp/g6"], 60)
    return filas


# ---------------------------------------------------------------------------
# B. FALSOS POSITIVOS: conversiones LEGITIMAS cuya salida tiene, por
#    construccion, la misma firma que la entrada.
EQUIVALENTES = [
    # los dos que nombra el inventario de C27
    ("png2apng", ["magick", "-limit", "thread", "4", "%E", "%S"], "imagen/tipico.png", "apng"),
    ("mkv2mka", ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", "%E", "-vn",
                 "-map", "0:a", "-c", "copy", "%S"], "video/patologico_2pistas.mkv", "mka"),
    # el resto de la familia, que el inventario no nombra
    ("mkv2webm", ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", "%E", "-map", "0:v:0",
                  "-c:v", "libvpx-vp9", "-b:v", "200k", "-deadline", "realtime",
                  "-cpu-used", "8", "%S"], "video/patologico_2pistas.mkv", "webm"),
    ("mp42mov", ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", "%E", "-map", "0",
                 "-c", "copy", "%S"], "video/tipico.mp4", "mov"),
    ("mp42m4a", ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", "%E", "-vn",
                 "-map", "0:a:0", "-c", "copy", "%S"], "video/tipico.mp4", "m4a"),
    ("wav2rf64", ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", "%E",
                  "-c:a", "pcm_s16le", "-rf64", "always", "%S"], "audio/trivial.wav", "rf64"),
    ("jpg2jfif", ["magick", "-limit", "thread", "4", "%E", "%S"], "imagen/tipico.jpg", "jfif"),
    ("tif2tiff", ["magick", "-limit", "thread", "4", "%E", "%S"],
     "imagen/patologico_16bit.tif", "tiff"),
    ("ogg2oga", ["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", "%E",
                 "-c:a", "libopus", "-b:a", "96k", "%S"], "audio/tipico.flac", "oga"),
    # LA FAMILIA SIN MARCADOR: aqui es donde G6 SI puede equivocarse, porque el
    # destino NO esta en EXT_A_FIRMAS y la firma no cambia por construccion.
    ("tga2vda", ["magick", "-limit", "thread", "4", "%E", "%S"], "imagen/tipico.png", "vda"),
    ("tga2icb", ["magick", "-limit", "thread", "4", "%E", "%S"], "imagen/tipico.png", "icb"),
    ("tga2vst", ["magick", "-limit", "thread", "4", "%E", "%S"], "imagen/tipico.png", "vst"),
    ("g32g4", ["magick", "-limit", "thread", "4", "%E", "-monochrome", "%S"],
     "imagen/tipico.png", "g4"),
    ("rgb2bgr", ["magick", "-limit", "thread", "4", "%E", "-depth", "8", "%S"],
     "imagen/tipico.png", "bgr"),
]


def parte_b(dur):
    filas = []
    for nombre, plantilla, rel, ext in EQUIVALENTES:
        ent = os.path.join(RAIZ, "corpus", *rel.split("/"))
        if not os.path.exists(ent):
            continue
        dst = os.path.join(dur, "eq_%s.%s" % (nombre, ext))
        orden = [x.replace("%E", ent).replace("%S", dst) for x in plantilla]
        rc, err = correr(orden)
        filas.append({"caso": nombre, "entrada": rel, "ext": ext, "rc": rc,
                      "err": err if rc else None, "g6": g6(ent, dst, rc)})
    # y el segundo salto: de la salida sin marcador a OTRA de su familia, que es
    # el caso que firmas-contrato §5.4 nombro (`vda -> vid`, `pcds -> pcd`).
    orig = os.path.join(dur, "eq_tga2vda.vda")
    if os.path.exists(orig):
        for ext in ("icb", "vst", "tga", "vid"):
            dst = os.path.join(dur, "eq2_vda2%s.%s" % (ext, ext))
            rc, err = correr(["magick", "-limit", "thread", "4", orig, dst])
            filas.append({"caso": "vda2" + ext, "entrada": "eq_tga2vda.vda",
                          "ext": ext, "rc": rc, "err": err if rc else None,
                          "g6": g6(orig, dst, rc)})
    return filas


def main():
    dur = os.path.join(tempfile.gettempdir(), "filex_g6")
    if os.path.exists(dur):
        shutil.rmtree(dur)
    os.makedirs(dur)
    antes = sorted(os.listdir(dur))
    cont_antes = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"],
                                capture_output=True, timeout=90,
                                stdin=subprocess.DEVNULL).stdout.decode().split()

    a = parte_a(dur)
    a2 = parte_a2(dur)
    b = parte_b(dur)

    cont_despues = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"],
                                  capture_output=True, timeout=90,
                                  stdin=subprocess.DEVNULL).stdout.decode().split()
    despues = sorted(os.listdir(dur))

    def resume(filas, etiqueta):
        con = [f for f in filas if (f.get("g6") or {}).get("G6")]
        escr = [f for f in filas if f.get("g6")]
        print("\n%s: %d celdas, %d escribieron fichero, G6 dispara en %d"
              % (etiqueta, len(filas), len(escr), len(con)))
        for f in filas:
            g = f.get("g6")
            print("  %-12s %-10s rc=%-4s %s" %
                  (f.get("motor") or f.get("caso"), f.get("ext"), f.get("rc"),
                   ("G6=%s firma %s->%s verd=%s p1=%s"
                    % (g["G6"], g["firma_entrada"], g["firma_salida"],
                       g["veredicto"], g["punto1"])) if g else "(sin fichero)"))
        return con

    con_a = resume(a, "A. motores nativos")
    con_a2 = resume(a2, "A2. motores del contenedor")
    con_b = resume(b, "B. conversiones legitimas / formatos equivalentes")

    res = {"parte_a": a, "parte_a2": a2, "parte_b": b,
           "desechable": dur, "censo_antes": antes, "censo_despues": despues,
           "docker_ps_a_antes": cont_antes, "docker_ps_a_despues": cont_despues,
           "huerfanos": sorted(set(cont_despues) - set(cont_antes)),
           "g6_dispara_A": len(con_a), "g6_dispara_A2": len(con_a2),
           "g6_dispara_B": len(con_b),
           "falsos_positivos_B": [f["caso"] for f in con_b]}
    with open(os.path.join(AQUI, "g6.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print("\nHUERFANOS DE DOCKER: %s" % (res["huerfanos"] or "ninguno"))
    print("-> g6.json")


if __name__ == "__main__":
    main()
