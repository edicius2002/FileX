#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C21 — el SUELO DURO de PSNR de V8, calibrado con casos reales.

Hoy V8 avisa por debajo de 40 dB y no tiene suelo: un video ENTERAMENTE NEGRO
sale con 5,39 dB y severidad `aviso` (`bench/contrato-quinto-punto.md` §5).
5,39 dB no es una recodificacion agresiva: es otra imagen.

El suelo NO se pone a ojo. Se mide:

  (a) el peor caso LEGITIMO: recodificaciones deliberadamente brutales de los
      tres videos del corpus (crf 51, tasas de 20 kb/s, escalas minusculas),
      que un usuario puede pedir de verdad;
  (b) el caso PATOLOGICO: negro, blanco, ruido, un fotograma congelado, y el
      video equivocado -- las cinco formas de «es otra imagen»;
  (c) las 53 del patron oro, para que el suelo no mueva ni una.

El suelo va entre el minimo de (a) y el maximo de (b), y se publica el margen.
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
sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-verificacion"))

from filex import verificador as V          # noqa: E402
from trabajos import trabajos               # noqa: E402

TIMEOUT = 90


def ff(args):
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + args,
                       capture_output=True, timeout=TIMEOUT,
                       stdin=subprocess.DEVNULL)
    return p.returncode, p.stderr.decode("utf-8", "replace")[-300:]


def psnr(sal, ent):
    d, err = V._ffmpeg_psnr(sal, ent)
    if d is None:
        return None, err
    return d.get("y"), None


FUENTES = [
    ("trivial_mp4", os.path.join(RAIZ, "corpus", "video", "trivial.mp4")),
    ("tipico_mp4", os.path.join(RAIZ, "corpus", "video", "tipico.mp4")),
    ("2pistas_mkv", os.path.join(RAIZ, "corpus", "video", "patologico_2pistas.mkv")),
]

# (a) recodificaciones LEGITIMAS todo lo agresivas que el motor permite
LEGITIMAS = [
    ("x264_crf51", ["-c:v", "libx264", "-crf", "51", "-preset", "veryfast"], ".mp4"),
    ("x264_20k", ["-c:v", "libx264", "-b:v", "20k", "-preset", "veryfast"], ".mp4"),
    ("x265_crf51", ["-c:v", "libx265", "-crf", "51", "-preset", "veryfast",
                    "-x265-params", "log-level=none"], ".mp4"),
    ("vp9_crf63", ["-c:v", "libvpx-vp9", "-crf", "63", "-b:v", "0",
                   "-deadline", "realtime", "-cpu-used", "8"], ".webm"),
    ("vp9_20k", ["-c:v", "libvpx-vp9", "-b:v", "20k",
                 "-deadline", "realtime", "-cpu-used", "8"], ".webm"),
    ("mpeg4_q31", ["-c:v", "mpeg4", "-q:v", "31"], ".mp4"),
    ("mpeg1_50k", ["-c:v", "mpeg1video", "-b:v", "50k"], ".mpg"),
    ("h264_gris", ["-vf", "format=gray", "-c:v", "libx264", "-crf", "23"], ".mp4"),
    ("h264_2colores", ["-vf", "format=gray,eq=contrast=40", "-c:v", "libx264",
                       "-crf", "23"], ".mp4"),
]

# (b) «es otra imagen»: las cinco formas de que el envase sea correcto y el
#     contenido no tenga nada que ver
PATOLOGICAS = [
    ("negro", ["-vf", "geq=lum=0:cb=128:cr=128", "-c:v", "libx264", "-crf", "23"], ".mp4"),
    ("blanco", ["-vf", "geq=lum=255:cb=128:cr=128", "-c:v", "libx264", "-crf", "23"], ".mp4"),
    ("ruido", ["-vf", "geq=lum=random(1)*255:cb=128:cr=128", "-c:v", "libx264",
               "-crf", "23"], ".mp4"),
    # OJO: `loop=loop=-1` genera un video INFINITO. La primera version de este
    # arnes lo tenia sin tope y dejo un ffmpeg HUERFANO vivo 9 minutos con el
    # fichero abierto, que tumbo la tanda siguiente con WinError 32 al borrar el
    # desechable. `-frames:v 60` es el tope que faltaba.
    ("congelado", ["-vf", "select=eq(n\\,0),loop=loop=-1:size=1:start=0",
                   "-frames:v", "60", "-c:v", "libx264", "-crf", "18"], ".mp4"),
    ("negativo", ["-vf", "negate", "-c:v", "libx264", "-crf", "18"], ".mp4"),
]


def main():
    d = os.path.join(tempfile.gettempdir(), "filex_v8")
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    antes = sorted(os.listdir(d))
    filas = []
    for nf, fuente in FUENTES:
        if not os.path.exists(fuente):
            print("falta %s" % fuente)
            continue
        for clase, tabla in (("legitima", LEGITIMAS), ("patologica", PATOLOGICAS)):
            for nc, args, ext in tabla:
                dst = os.path.join(d, "%s__%s%s" % (nf, nc, ext))
                rc, err = ff(["-i", fuente, "-an", "-sn", "-map", "0:v:0"]
                             + args + [dst])
                if rc != 0 or not os.path.exists(dst):
                    filas.append({"fuente": nf, "caso": nc, "clase": clase,
                                  "psnr_y": None, "error": err[-160:]})
                    print("%-14s %-16s %-11s  NO SE PUDO: %s" % (nf, nc, clase, err[-70:]))
                    continue
                y, err2 = psnr(dst, fuente)
                filas.append({"fuente": nf, "caso": nc, "clase": clase,
                              "psnr_y": y, "bytes": os.path.getsize(dst),
                              "error": err2})
                print("%-14s %-16s %-11s  PSNR y = %s" % (nf, nc, clase, y))
    despues = sorted(os.listdir(d))

    # (c) las 53 del patron oro: V8 solo se evalua en las que tienen video
    oro = []
    for t in trabajos():
        ss = V.sondear(t["salida"])
        se = V.sondear(t["entrada"])
        if ss.get("n_video", 0) < 1 or se.get("n_video", 0) < 1:
            continue
        if t["pedido"]["params"].get("escala") or t["pedido"]["params"].get("fps"):
            continue
        y, err = psnr(t["salida"], t["entrada"])
        oro.append({"salida": os.path.basename(t["salida"]), "psnr_y": y,
                    "error": err})
        print("oro %-32s PSNR y = %s" % (oro[-1]["salida"], y))

    leg = [f["psnr_y"] for f in filas
           if f["clase"] == "legitima" and isinstance(f["psnr_y"], (int, float))]
    pat = [f["psnr_y"] for f in filas
           if f["clase"] == "patologica" and isinstance(f["psnr_y"], (int, float))]
    oro_v = [f["psnr_y"] for f in oro if isinstance(f["psnr_y"], (int, float))]
    res = {"filas": filas, "oro": oro, "desechable": d,
           "censo_antes": antes, "censo_despues": despues,
           "min_legitima": min(leg) if leg else None,
           "max_patologica": max(pat) if pat else None,
           "min_oro": min(oro_v) if oro_v else None,
           "n_legitimas": len(leg), "n_patologicas": len(pat), "n_oro": len(oro_v)}
    with open(os.path.join(AQUI, "v8_calibracion.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print("\nLEGITIMAS  n=%d  minimo  %.2f dB" % (len(leg), min(leg)) if leg else "")
    print("PATOLOGICAS n=%d maximo  %.2f dB" % (len(pat), max(pat)) if pat else "")
    print("PATRON ORO n=%d  minimo  %.2f dB" % (len(oro_v), min(oro_v)) if oro_v else "")
    print("-> v8_calibracion.json")


if __name__ == "__main__":
    main()
