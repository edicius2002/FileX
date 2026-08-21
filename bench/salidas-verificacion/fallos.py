#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fase 4: los cinco fallos reales, reproducidos contra el verificador.

Un verificador rapido que no atrapa nada no vale. Se reproducen los fallos ya
documentados en HUECOS.md §1 y bench/mcp-refs-multimedia.md §6 y se comprueba
que el contrato los detecta:

  1. PNG con extension .avif                 (ConvertX)
  2. Perdida de una pista de audio           (ConvertX y SnapOtter)
  3. Degradacion de 16 a 8 bits              (SnapOtter)
  4. Redimensionado NO solicitado con barras (image-worker-mcp)
  5. Fichero de 0 bytes presentado como exito (video-audio-mcp)

Los artefactos grandes se generan en el temporal y se borran al terminar.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, AQUI)
import verificador as V           # noqa: E402
from trabajos import trabajos     # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "filex_fallos")
CORPUS = os.path.join(RAIZ, "corpus")
REF = os.path.join(RAIZ, "bench", "salidas-referencia")


def sh(args, timeout=600):
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    return p.returncode


def caso(nombre, descripcion, fuente, salida, entrada, pedido, regla_esperada):
    filas = []
    for motor in ("proceso", "subproceso"):
        s_ent = V.sondear(entrada, motor)
        s_ent.update(EXTRA.get(os.path.normcase(entrada), {}))
        r = V.verificar(salida, pedido, entrada, motor, sonda_ent=s_ent)
        atrapado = any(h["severidad"] == "fallo" for h in r["hallazgos"])
        filas.append({"motor": motor, "veredicto": r["veredicto"],
                      "atrapado": atrapado,
                      "ms_total": round(r["ms"]["total"], 3),
                      "hallazgos": [(h["punto"], h["regla"], h["severidad"],
                                     h["mensaje"], h["esperado"], h["obtenido"])
                                    for h in r["hallazgos"]]})
    return {"caso": nombre, "descripcion": descripcion, "fuente": fuente,
            "regla_esperada": regla_esperada, "resultados": filas}


EXTRA = {}


def main():
    os.makedirs(TMP, exist_ok=True)
    ref = json.load(open(os.path.join(REF, "referencia.json"), encoding="utf-8"))
    for c in ref["corpus"]:
        EXTRA[os.path.normcase(c["ruta"])] = {
            k: c[k] for k in ("alfa_no_trivial", "tiene_alfa") if k in c}

    casos = []

    # ---- 1. PNG con extension .avif (ConvertX) --------------------------
    falso_avif = os.path.join(TMP, "falso.avif")
    shutil.copyfile(os.path.join(CORPUS, "imagen", "tipico.png"), falso_avif)
    casos.append(caso(
        "1. PNG con extension .avif",
        "se copia tipico.png a falso.avif sin convertir nada; 42.855 B en vez "
        "de los ~1.600 de un AVIF real",
        "ConvertX (HUECOS.md §1)", falso_avif,
        os.path.join(CORPUS, "imagen", "tipico.png"),
        {"destino": "avif", "params": {}}, "G3 (punto 1: firma)"))

    # ---- 2. Perdida de una pista de audio (ConvertX y SnapOtter) --------
    mkv = os.path.join(CORPUS, "video", "patologico_2pistas.mkv")
    perdida = os.path.join(TMP, "pierde_pista.mp4")
    rc = sh(["ffmpeg", "-y", "-threads", "4", "-i", mkv, "-c:v", "libx264",
             "-crf", "23", "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k",
             perdida])
    casos.append(caso(
        "2. Perdida de una pista de audio",
        "'ffmpeg -i in.mkv out.mp4' SIN -map 0 sobre un MKV de 2 pistas de "
        "audio con PCM distinto; rc=%d, el motor declara exito" % rc,
        "ConvertX y SnapOtter (HUECOS.md §1)", perdida, mkv,
        {"destino": "mp4", "params": {}}, "V3 (punto 2: flujos)"))

    # ---- 3. Degradacion de 16 a 8 bits (SnapOtter) ----------------------
    tif = os.path.join(CORPUS, "imagen", "patologico_16bit.tif")
    d8 = os.path.join(REF, "imagen", "16bit_tif-to-d8.png")
    casos.append(caso(
        "3. Degradacion de 16 a 8 bits",
        "el MISMO fichero de 8 bits del patron oro, pero con un pedido que NO "
        "solicitaba reducir la profundidad: PNG admite 16 bits",
        "SnapOtter (HUECOS.md §1)", d8, tif,
        {"destino": "png", "params": {}}, "I4 (punto 4: pedido)"))

    # ---- 4. Redimensionado NO solicitado, con barras --------------------
    jpg = os.path.join(CORPUS, "imagen", "tipico.jpg")
    sucio = os.path.join(TMP, "resize_no_pedido.png")
    # reproduce sharp fit='contain' con DEFAULT_WIDTH=800 / DEFAULT_HEIGHT=600
    sh(["magick", "-limit", "thread", "4", jpg, "-resize", "800x600",
        "-background", "black", "-gravity", "center", "-extent", "800x600", sucio])
    limpio = os.path.join(TMP, "solo_formato.png")
    sh(["magick", "-limit", "thread", "4", jpg, limpio])
    casos.append(caso(
        "4a. Redimensionado no solicitado (con barras)",
        "se pidio solo 'format: png'; se entrega 800x600 con el contenido en "
        "800x450 y barras negras de 75 px",
        "image-worker-mcp (bench/mcp-refs-multimedia.md §6.2)", sucio, jpg,
        {"destino": "png", "params": {}}, "I1/V7 (punto 4: pedido)"))
    casos.append(caso(
        "4b. Control: conversion de formato limpia",
        "el mismo JPEG a PNG sin tocar la geometria. NO debe dar fallo.",
        "control negativo", limpio, jpg,
        {"destino": "png", "params": {}}, "ninguna (debe salir OK)"))

    # ---- 5. Fichero de 0 bytes presentado como exito --------------------
    vacio = os.path.join(TMP, "vam_dead.gif")
    open(vacio, "wb").close()
    casos.append(caso(
        "5. Fichero de 0 bytes como exito",
        "residuo del deadlock de video-audio-mcp: 0 bytes en disco y la "
        "herramienta no informa de error",
        "video-audio-mcp (bench/mcp-refs-multimedia.md §6)", vacio,
        os.path.join(CORPUS, "video", "trivial.mp4"),
        {"destino": "gif", "params": {"escala": 320}}, "G1 (punto 1: firma)"))

    with open(os.path.join(AQUI, "fallos.json"), "w", encoding="utf-8") as fh:
        json.dump(casos, fh, ensure_ascii=False, indent=1, default=str)

    for c in casos:
        print("\n### %s" % c["caso"])
        print("    %s" % c["descripcion"])
        for r in c["resultados"]:
            print("    [%-11s] veredicto=%-6s atrapado=%-5s  %.2f ms"
                  % (r["motor"], r["veredicto"], r["atrapado"], r["ms_total"]))
            for hl in r["hallazgos"]:
                print("        p%s %-7s %-12s %s (esp=%s obt=%s)"
                      % (hl[0], hl[1], hl[2], hl[3], hl[4], hl[5]))
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
