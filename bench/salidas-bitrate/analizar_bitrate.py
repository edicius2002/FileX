#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N24 — la tabla de la meseta, o la demostración de que no hay umbral.

Trampa 51: *tabula qué atrapa y qué rompe en cada valor candidato; casi siempre
hay una meseta, y el borde de abajo de la meseta es la respuesta* — y antes,
*pregunta si el umbral EXISTE*.

Se tabula sobre las DOS observables, y no son intercambiables:

``desvio_real``        (bytes de los paquetes de vídeo)·8/duración. Es la
                       verdad de campo y **el contrato NO la tiene**: exige un
                       `ffprobe -show_packets`, que recorre el fichero entero.
``desvio_contenedor``  (bytes del fichero)·8/duración menos lo que la sonda
                       sepa del audio. Es lo único que el contrato puede ver
                       en proceso.

Uso: python bench/salidas-bitrate/analizar_bitrate.py
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))

CANDIDATOS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.75, 1.00,
              1.50, 2.00, 3.00, 5.00]


def carga():
    """Las dos pasadas, con la segunda mandando sobre la primera.

    La primera pasada mandó `2pistas` a `.mkv` y las 24 celdas legítimas
    salieron en blanco —`.mkv -> .mkv` no tiene camino—; la segunda las repite
    contra `.mp4`. Se deduplica por `(clase, fuente, codec, pedido)` **quedándose
    con la última**, y se registra cuántas celdas se descartan por no tener
    observable: un `None` uniforme se parece muchísimo a «no hay señal»
    (trampa 81), y aquí lo que había era un destino mal elegido.
    """
    filas, muertas = {}, []
    for n in ("calibracion.json", "calibracion_2pistas.json"):
        p = os.path.join(AQUI, n)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            for f in json.load(fh)["filas"]:
                filas[(f["clase"], f["fuente"], f["codec"], f["pedido_bps"])] = f
    vivas = []
    for f in filas.values():
        (vivas if f.get("bytes") else muertas).append(f)
    if muertas:
        print("celdas SIN salida, descartadas (motivo registrado): %d" % len(muertas))
        for f in muertas[:3]:
            print("   %s %s %s rc=%s motivo=%s"
                  % (f["fuente"], f["codec"], f["pedido_bps"], f.get("rc"),
                     f.get("motivo")))
    return vivas


def tabla(filas, clave):
    leg = [f for f in filas if f["clase"] == "legitima" and f.get(clave) is not None]
    pat = [f for f in filas if f["clase"] == "patologica" and f.get(clave) is not None]
    print("\n### observable: %s   (legítimas n=%d, patológicas n=%d)"
          % (clave, len(leg), len(pat)))
    if not leg or not pat:
        print("  sin datos")
        return
    print("  recorrido legítimas   %+.2f%% .. %+.2f%%"
          % (min(f[clave] for f in leg) * 100, max(f[clave] for f in leg) * 100))
    print("  recorrido patológicas %+.2f%% .. %+.2f%%"
          % (min(f[clave] for f in pat) * 100, max(f[clave] for f in pat) * 100))
    print()
    print("  %-8s | %-28s | %-24s | %s"
          % ("umbral", "falsos positivos (legítimas)", "atrapadas (patológicas)",
             "bilateral / solo por arriba"))
    for u in CANDIDATOS:
        fp_bi = sum(1 for f in leg if abs(f[clave]) > u)
        at_bi = sum(1 for f in pat if abs(f[clave]) > u)
        fp_ar = sum(1 for f in leg if f[clave] > u)
        at_ar = sum(1 for f in pat if f[clave] > u)
        print("  %6.0f%%   | %2d de %-3d  /  %2d de %-3d       | %2d de %-3d  /  %2d de %-3d"
              % (u * 100, fp_bi, len(leg), fp_ar, len(leg),
                 at_bi, len(pat), at_ar, len(pat)))


def solape(filas, clave):
    leg = [f[clave] for f in filas
           if f["clase"] == "legitima" and f.get(clave) is not None]
    pat = [f[clave] for f in filas
           if f["clase"] == "patologica" and f.get(clave) is not None]
    if not leg or not pat:
        return
    a, b = max(abs(x) for x in leg), min(abs(x) for x in pat)
    print("\n  |desvío| máximo legítimo   %+.2f%%" % (a * 100))
    print("  |desvío| mínimo patológico %+.2f%%" % (b * 100))
    print("  -> %s" % ("SE SOLAPAN: no existe umbral bilateral" if b <= a
                       else "hueco de %.2f puntos" % ((b - a) * 100)))


def por_motor(filas, clave):
    print("\n### peor desvío legítimo POR CODIFICADOR (trampa 78)")
    codecs = sorted({f["codec"] for f in filas if f["clase"] == "legitima"})
    for c in codecs:
        xs = [f for f in filas if f["clase"] == "legitima" and f["codec"] == c
              and f.get(clave) is not None]
        if not xs:
            continue
        peor_ab = min(xs, key=lambda f: f[clave])
        peor_ar = max(xs, key=lambda f: f[clave])
        print("  %-6s  n=%-3d  peor por abajo %+8.2f%% (%s @%d)  peor por arriba %+8.2f%% (%s @%d)"
              % (c, len(xs), peor_ab[clave] * 100, peor_ab["fuente"], peor_ab["pedido_bps"],
                 peor_ar[clave] * 100, peor_ar["fuente"], peor_ar["pedido_bps"]))


def por_fuente(filas, clave):
    print("\n### peor desvío legítimo POR FUENTE (trampa 50)")
    for s in sorted({f["fuente"] for f in filas if f["clase"] == "legitima"}):
        xs = [f for f in filas if f["clase"] == "legitima" and f["fuente"] == s
              and f.get(clave) is not None]
        if not xs:
            continue
        print("  %-8s n=%-3d  %+8.2f%% .. %+8.2f%%"
              % (s, len(xs), min(f[clave] for f in xs) * 100,
                 max(f[clave] for f in xs) * 100))


def audio(filas):
    print("\n### lo que el AUDIO le suma al bitrate del contenedor")
    print("  %-8s %-6s %8s  %10s %10s %10s"
          % ("fuente", "codec", "pedido", "video_real", "contenedor", "delta"))
    vistos = set()
    for f in filas:
        if f["clase"] != "legitima" or f.get("bitrate_video_real") is None:
            continue
        k = (f["fuente"], f["pedido_bps"])
        if k in vistos or f["pedido_bps"] != 2_000_000:
            continue
        vistos.add(k)
        print("  %-8s %-6s %8d  %10d %10d %+10d  (n_audio=%d, sonda_audio=%s)"
              % (f["fuente"], f["codec"], f["pedido_bps"], f["bitrate_video_real"],
                 f["bitrate_contenedor"],
                 f["bitrate_contenedor"] - f["bitrate_video_real"],
                 f.get("n_audio", 0), f.get("audio_bps_sonda")))


def tabla_asimetrica(filas):
    """La tabla de LA REGLA QUE SE PUEDE ESCRIBIR, no la de la que se querría.

    Sobre `desvio_contenedor` las dos clases SE SOLAPAN (legítimo hasta
    +106,13 %, patológico desde +82,13 %), así que no hay umbral bilateral. Lo
    que sí hay es una asimetría con demostración:

      * **por abajo** el audio solo SUMA, luego el contenedor es cota SUPERIOR
        del vídeo y un contenedor corto implica un vídeo corto;
      * **por arriba** solo es decidible cuando no hay pistas de audio.
    """
    clave = "desvio_contenedor"
    leg = [f for f in filas if f["clase"] == "legitima" and f.get(clave) is not None]
    pat = [f for f in filas if f["clase"] == "patologica" and f.get(clave) is not None]
    leg_sa = [f for f in leg if not f.get("n_audio")]
    pat_sa = [f for f in pat if not f.get("n_audio")]
    pat_abajo = [f for f in pat if f[clave] < 0]
    pat_arriba_sa = [f for f in pat_sa if f[clave] > 0]
    print("\n### LA REGLA ASIMÉTRICA (V10), sobre `desvio_contenedor`")
    print("  lado de ABAJO: todas las celdas          legítimas n=%d, patológicas n=%d"
          % (len(leg), len(pat_abajo)))
    print("  lado de ARRIBA: solo sin audio           legítimas n=%d, patológicas n=%d"
          % (len(leg_sa), len(pat_arriba_sa)))
    print("\n  %-8s | %-24s | %-24s" % ("umbral", "ABAJO  fp / atrapadas",
                                        "ARRIBA sin audio  fp / atrapadas"))
    for u in CANDIDATOS:
        fp_ab = sum(1 for f in leg if f[clave] < -u)
        at_ab = sum(1 for f in pat_abajo if f[clave] < -u)
        fp_ar = sum(1 for f in leg_sa if f[clave] > u)
        at_ar = sum(1 for f in pat_arriba_sa if f[clave] > u)
        marca = "  <- meseta" if (fp_ab == 0 and fp_ar == 0
                                  and at_ab == len(pat_abajo)
                                  and at_ar == len(pat_arriba_sa)) else ""
        print("  %6.0f%%   | %2d de %-3d / %2d de %-3d      | %2d de %-3d / %2d de %-3d %s"
              % (u * 100, fp_ab, len(leg), at_ab, len(pat_abajo),
                 fp_ar, len(leg_sa), at_ar, len(pat_arriba_sa), marca))
    print("\n  peor legítimo por ABAJO           %+.2f%%"
          % (min(f[clave] for f in leg) * 100))
    print("  peor patológico por ABAJO (menos malo) %+.2f%%"
          % (max(f[clave] for f in pat_abajo) * 100))
    print("  peor legítimo por ARRIBA sin audio %+.2f%%"
          % (max(f[clave] for f in leg_sa) * 100))
    print("  patológico por ARRIBA sin audio menos malo %+.2f%%"
          % (min(f[clave] for f in pat_arriba_sa) * 100))
    print("\n  celdas legítimas CON audio que un umbral bilateral del 60 %% "
          "marcaría por arriba: %d"
          % sum(1 for f in leg if f.get("n_audio") and f[clave] > 0.60))


def main():
    filas = carga()
    print("celdas: %d (legítimas %d, patológicas %d)"
          % (len(filas),
             sum(1 for f in filas if f["clase"] == "legitima"),
             sum(1 for f in filas if f["clase"] == "patologica")))
    tabla_asimetrica(filas)
    for clave in ("desvio_real", "desvio_contenedor"):
        tabla(filas, clave)
        solape(filas, clave)
        por_motor(filas, clave)
        por_fuente(filas, clave)
    audio(filas)
    ver = {}
    for f in filas:
        ver.setdefault(f["clase"], {}).setdefault(f.get("veredicto"), 0)
        ver[f["clase"]][f.get("veredicto")] += 1
    print("\n### veredicto del contrato HOY")
    print(" ", json.dumps(ver, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
