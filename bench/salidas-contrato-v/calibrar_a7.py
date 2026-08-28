#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C19 — calibracion de la regla A7 (ENERGIA POR CANAL).

Mide, con `ffmpeg -af astats`, el nivel RMS de CADA canal de la entrada y de la
salida en:

  (a) las 53 salidas del patron oro que llevan audio  -> falsos positivos
  (b) los casos fabricados de `fabricar_c19.py`       -> sensibilidad
  (c) recodificaciones AGRESIVAS pero legitimas       -> el margen real

El umbral no se pone a ojo: sale de la separacion medida entre (a)+(c) y (b).
"""
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "bench", "salidas-verificacion"))

from filex import verificador as V          # noqa: E402
from trabajos import trabajos               # noqa: E402

TIMEOUT = 180
_RE_CANAL = re.compile(r"^Channel:\s*(\d+)")
_RE_RMS = re.compile(r"^RMS level dB:\s*(-?[\d.]+|-?inf|nan)", re.I)
_RE_PICO = re.compile(r"^Peak level dB:\s*(-?[\d.]+|-?inf|nan)", re.I)


def astats(ruta, pista=0):
    """[(rms_dB, pico_dB)] por canal. None si no se puede medir."""
    orden = ["ffmpeg", "-hide_banner", "-nostdin", "-i", ruta,
             "-map", "0:a:%d" % pista, "-vn", "-sn",
             "-af", "astats=measure_overall=none:"
                    "measure_perchannel=Peak_level+RMS_level",
             "-f", "null", "-"]
    try:
        p = subprocess.run(orden, capture_output=True, timeout=TIMEOUT,
                           stdin=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, str(e)[:150]
    canales, actual = [], None
    for l in p.stderr.decode("utf-8", "replace").splitlines():
        l = l.split("] ", 1)[-1].strip()
        m = _RE_CANAL.match(l)
        if m:
            actual = {"canal": int(m.group(1)), "rms": None, "pico": None}
            canales.append(actual)
            continue
        if actual is None:
            continue
        m = _RE_RMS.match(l)
        if m:
            actual["rms"] = _f(m.group(1))
        m = _RE_PICO.match(l)
        if m:
            actual["pico"] = _f(m.group(1))
    if not canales:
        return None, "astats sin canales"
    return canales, None


def _f(s):
    s = s.lower()
    if s in ("-inf", "inf", "nan"):
        return float("-inf") if s.startswith("-") else float("nan")
    return float(s)


def par(entrada, salida, etiqueta, esperado):
    ce, ee = astats(entrada)
    cs, es = astats(salida)
    fila = {"caso": etiqueta, "esperado": esperado,
            "entrada": os.path.basename(entrada),
            "salida": os.path.basename(salida),
            "error": ee or es}
    if not (ce and cs):
        return fila
    fila["n_canales_entrada"] = len(ce)
    fila["n_canales_salida"] = len(cs)
    fila["rms_entrada"] = [round(x["rms"], 2) if x["rms"] not in (None, float("-inf"))
                           else x["rms"] for x in ce]
    fila["rms_salida"] = [round(x["rms"], 2) if x["rms"] not in (None, float("-inf"))
                          else x["rms"] for x in cs]
    if len(ce) == len(cs):
        caidas = []
        for a, b in zip(ce, cs):
            if a["rms"] is None or b["rms"] is None:
                caidas.append(None)
            else:
                caidas.append(round(a["rms"] - b["rms"], 2))
        fila["caida_dB"] = caidas
        finitas = [c for c in caidas if c is not None]
        fila["caida_max_dB"] = max(finitas) if finitas else None
    return fila


def main():
    filas = []

    # ---- (a) las 53 del patron oro con audio -------------------------------
    for t in trabajos():
        se = V.sondear(t["entrada"])
        ss = V.sondear(t["salida"])
        if se.get("n_audio", 0) < 1 or ss.get("n_audio", 0) < 1:
            continue
        filas.append(par(t["entrada"], t["salida"],
                         "oro:" + os.path.basename(t["salida"]), "sin_hallazgo"))
        print("oro  %-34s %s" % (filas[-1]["salida"], filas[-1].get("caida_dB")))

    # ---- (b) los fabricados de C19 -----------------------------------------
    base = os.path.join(tempfile.gettempdir(), "filex_c19")
    if os.path.isdir(base):
        ent = os.path.join(base, "entrada.wav")
        for n, esp in (("bueno.mp3", "sin_hallazgo"), ("malo.mp3", "FALLO"),
                       ("malo.opus", "FALLO"), ("malo.m4a", "FALLO"),
                       ("malo.flac", "FALLO"), ("bueno.flac", "sin_hallazgo"),
                       ("atenuado20.mp3", "?"), ("atenuado6.mp3", "?")):
            filas.append(par(ent, os.path.join(base, n), "c19:" + n, esp))
            print("c19  %-34s %s" % (n, filas[-1].get("caida_dB")))
        filas.append(par(os.path.join(base, "mono.wav"),
                         os.path.join(base, "mono2estereo.mp3"),
                         "c19:mono2estereo.mp3", "sin_hallazgo"))
        print("c19  %-34s ent=%s sal=%s" % ("mono2estereo.mp3",
                                            filas[-1].get("rms_entrada"),
                                            filas[-1].get("rms_salida")))

    # ---- (c) recodificaciones agresivas pero LEGITIMAS ---------------------
    # El margen real de la regla no lo da el patron oro (que es benigno): lo da
    # el peor caso legitimo que un usuario puede pedir a proposito.
    dur = os.path.join(tempfile.gettempdir(), "filex_a7_agresivo")
    if os.path.exists(dur):
        shutil.rmtree(dur)
    os.makedirs(dur)
    antes = sorted(os.listdir(dur))
    fuentes = [
        ("estereo_sintetico", os.path.join(base, "entrada.wav")),
        ("mp4_real", os.path.join(RAIZ, "corpus", "video", "tipico.mp4")),
        ("flac_real", os.path.join(RAIZ, "corpus", "audio", "tipico.flac")),
        ("mkv_2pistas", os.path.join(RAIZ, "corpus", "video", "patologico_2pistas.mkv")),
    ]
    agresivas = [
        ("opus8k", ["-c:a", "libopus", "-b:a", "8k"], ".opus"),
        ("mp38k", ["-c:a", "libmp3lame", "-b:a", "8k"], ".mp3"),
        ("aac8k", ["-c:a", "aac", "-b:a", "8k"], ".m4a"),
        ("mp3q9", ["-c:a", "libmp3lame", "-q:a", "9"], ".mp3"),
        ("vorbis_q_1", ["-c:a", "libvorbis", "-q:a", "-1"], ".ogg"),
        # filtros legitimos que SI mueven la energia y que el pedido declara
        ("volumen_-20dB", ["-af", "volume=-20dB", "-c:a", "libmp3lame", "-b:a", "192k"], ".mp3"),
        ("paso_bajo_500", ["-af", "lowpass=f=500", "-c:a", "libmp3lame", "-b:a", "192k"], ".mp3"),
    ]
    for nf, fuente in fuentes:
        if not os.path.exists(fuente):
            continue
        for na, args, ext in agresivas:
            dst = os.path.join(dur, "%s_%s%s" % (nf, na, ext))
            try:
                p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin",
                                    "-i", fuente, "-vn", "-sn", "-map", "0:a:0"]
                                   + args + [dst], capture_output=True,
                                   timeout=TIMEOUT, stdin=subprocess.DEVNULL)
            except (subprocess.TimeoutExpired, OSError):
                continue
            if p.returncode != 0 or not os.path.exists(dst):
                continue
            esp = "declarado_en_pedido" if na.startswith(("volumen", "paso")) \
                else "sin_hallazgo"
            filas.append(par(fuente, dst, "agresivo:%s/%s" % (nf, na), esp))
            print("agr  %-34s %s" % (os.path.basename(dst), filas[-1].get("caida_dB")))
    despues = sorted(os.listdir(dur))

    # ---- coste de la sonda -------------------------------------------------
    coste = {}
    for etiqueta, ruta in (("wav 8 s estereo", os.path.join(base, "entrada.wav")),
                           ("mp3 8 s estereo", os.path.join(base, "malo.mp3")),
                           ("mp4 real (audio)", os.path.join(RAIZ, "corpus", "video", "tipico.mp4"))):
        if not os.path.exists(ruta):
            continue
        astats(ruta)                       # calentar (trampa 7)
        t = []
        for _ in range(9):
            t0 = time.perf_counter()
            astats(ruta)
            t.append((time.perf_counter() - t0) * 1000)
        coste[etiqueta] = {"n": 9, "mediana_ms": round(statistics.median(t), 2),
                           "min_ms": round(min(t), 2), "max_ms": round(max(t), 2)}
        print("coste %-24s %8.2f ms (mediana n=9)" % (etiqueta, coste[etiqueta]["mediana_ms"]))

    res = {"filas": filas, "coste_astats_ms": coste,
           "desechable": dur, "censo_antes": antes, "censo_despues": despues}
    with open(os.path.join(AQUI, "a7_calibracion.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print("\n-> a7_calibracion.json")


if __name__ == "__main__":
    main()
