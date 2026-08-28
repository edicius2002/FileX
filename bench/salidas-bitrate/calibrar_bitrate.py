#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N24 — ¿existe un umbral de desvío de bitrate de VÍDEO que separe las clases?

Trampa 51: *antes de preguntar «¿dónde está el umbral?», pregunta «¿existe?»*.
Trampa 50: varía la ENTRADA. Trampa 78: varía el MOTOR del destino.

Dos clases:

``legitima``    se pide `bitrate_video` y el codificador entrega lo que puede.
                Cuatro codificadores de CPU × seis tasas × tres fuentes.
``patologica``  el pedido dice una tasa y el fichero lleva otra porque **el
                motor no respetó la petición** — que es el fallo que una regla
                de bitrate de vídeo existiría para atrapar.

**LA GPU NO SE TOCA.** `gpu._CACHE` se rellena a mano con `False` para los tres
codificadores NVENC: es el idioma que ya usa `pruebas/test_hito2.py` y no toma
el lock de máquina, que en esta ronda lo tiene otro agente. Las filas de NVENC
de este informe son las de H2 (`bench/hito2-nvenc.md` §4.3), CITADAS, no
remedidas.

Uso: python bench/salidas-bitrate/calibrar_bitrate.py <dir_trabajo> [--rapido]
"""
import json
import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex import gpu, nucleo, verificador  # noqa: E402

#: (etiqueta, ruta, extensión de DESTINO).
#
# El destino no es el mismo para las tres, y no es capricho: `2pistas` ya es
# `.mkv`, y `.mkv -> .mkv` no tiene camino —`convertir` devuelve «origen y
# destino son el mismo formato»—. La primera pasada de este arnés se llevó así
# **24 celdas en blanco**, con `veredicto=None` y sin un solo error por
# pantalla; es la trampa 38 otra vez (registra si la condición que dices
# reproducir se dio). De paso, el destino queda VARIADO: Matroska y MP4.
FUENTES = [
    ("trivial", os.path.join(RAIZ, "corpus", "video", "trivial.mp4"), "mkv"),
    ("2pistas", os.path.join(RAIZ, "corpus", "video",
                             "patologico_2pistas.mkv"), "mp4"),
    ("tipico", os.path.join(RAIZ, "corpus", "video", "tipico.mp4"), "mkv"),
]
#: Las cuatro familias que `motores.CODECS_VIDEO` sabe pedir y que NO son NVENC.
CODECS = ["h264", "hevc", "av1", "vp9"]
TASAS = [200_000, 500_000, 1_000_000, 2_000_000, 4_000_000, 8_000_000]

TOPE_FFMPEG = 900.0


def veta_gpu():
    """Ni una orden a la tarjeta, ni un intento de tomar su lock.

    `elegir_codec` consulta `gpu.capacidad(cand)`, que sin caché toma el lock de
    máquina y lanza un `ffmpeg` de sondeo. Precargar la caché con un `False`
    corta antes de las dos cosas.
    """
    for c in ("hevc_nvenc", "h264_nvenc", "av1_nvenc"):
        gpu._CACHE[c] = (False, gpu.AVERROR_EXTERNAL, "vetada por el arnés de N4")


def _ffprobe_bytes_por_tipo(ruta):
    """Bytes de payload por tipo de pista, sumando PAQUETES. El instrumento.

    Trampa 62: pregúntale al instrumento su resolución. Ni la sonda en proceso
    ni `ffprobe -show_streams` publican el `bit_rate` de una pista de VÍDEO en
    MP4 ni en Matroska (MEDIDO, `dbg_sonda.py`), así que la única verdad de
    campo es sumar los paquetes. Esto NO es lo que puede hacer el contrato: es
    la vara con la que se mide cuánto se equivoca lo que sí puede hacer.
    """
    argv = ["ffprobe", "-v", "error", "-show_entries",
            "packet=codec_type,size", "-of", "compact=p=0:nk=0", ruta]
    r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                       timeout=TOPE_FFMPEG, text=True, errors="replace")
    if r.returncode != 0:
        return {}, r.returncode
    tot = {}
    for linea in r.stdout.splitlines():
        t = s = None
        for campo in linea.strip().split("|"):
            if campo.startswith("codec_type="):
                t = campo[11:]
            elif campo.startswith("size="):
                s = campo[5:]
        if t and s and s != "N/A":
            tot[t] = tot.get(t, 0) + int(s)
    return tot, 0


def mide(ruta, pedido_bps):
    """Todo lo observable de una salida, con las dos vías separadas."""
    d = {"bytes": os.path.getsize(ruta) if os.path.exists(ruta) else 0}
    if not d["bytes"]:
        return d
    s = verificador.sondear(ruta)
    dur = s.get("duracion_s") or 0
    d["duracion_s"] = dur
    d["bitrate_contenedor"] = s.get("bitrate_bps")
    d["n_audio"] = sum(1 for x in s.get("pistas", []) if x.get("tipo") == "audio")
    d["audio_bps_sonda"] = [x.get("bitrate_bps") for x in s.get("pistas", [])
                            if x.get("tipo") == "audio"]
    tot, rc = _ffprobe_bytes_por_tipo(ruta)
    d["rc_ffprobe"] = rc
    if dur:
        d["bitrate_video_real"] = int(tot.get("video", 0) * 8 / dur) or None
        d["bitrate_audio_real"] = int(tot.get("audio", 0) * 8 / dur) or None
    if pedido_bps and d.get("bitrate_video_real"):
        d["desvio_real"] = (d["bitrate_video_real"] - pedido_bps) / pedido_bps
    if pedido_bps and d.get("bitrate_contenedor"):
        d["desvio_contenedor"] = ((d["bitrate_contenedor"] - pedido_bps)
                                  / pedido_bps)
    return d


def legitimas(trabajo, fx, rapido, solo=None):
    filas = []
    tasas = TASAS[::2] if rapido else TASAS
    for etiqueta, fuente, ext in FUENTES:
        if solo and etiqueta != solo:
            continue
        for codec in CODECS:
            for bps in tasas:
                dst = os.path.join(trabajo, f"L_{etiqueta}_{codec}_{bps}.{ext}")
                t0 = time.perf_counter()
                c = fx.convertir(fuente, dst,
                                 {"codec_video": codec, "bitrate_video": bps},
                                 timeout=TOPE_FFMPEG)
                ms = (time.perf_counter() - t0) * 1000
                s = c.saltos[-1] if c.saltos else None
                fila = {"clase": "legitima", "fuente": etiqueta, "codec": codec,
                        "pedido_bps": bps, "ok": c.ok, "ms": round(ms, 1),
                        "rc": getattr(s, "rc", None),
                        "veredicto": getattr(s, "veredicto", None),
                        "reglas": sorted({h["regla"] for h in (getattr(s, "hallazgos", None) or [])
                                          if h["severidad"] in ("fallo", "aviso")}),
                        "motivo": c.motivo}
                fila.update(mide(dst, bps))
                filas.append(fila)
                print("L %-8s %-5s %8d  real=%-9s cont=%-9s desv_real=%-8s desv_cont=%-8s %s"
                      % (etiqueta, codec, bps,
                         fila.get("bitrate_video_real"), fila.get("bitrate_contenedor"),
                         _pc(fila.get("desvio_real")), _pc(fila.get("desvio_contenedor")),
                         fila.get("veredicto")), flush=True)
    return filas


#: Las cuatro formas de que el motor IGNORE la tasa pedida. El pedido declara
#: `declara_bps` y el `argv` hace otra cosa: es exactamente el caso de
#: ConvertX entregando 64 kbps cuando se le piden 192.
PATOLOGICAS = [
    ("crf51_infra", ["-c:v", "libx264", "-crf", "51"], 4_000_000),
    ("crf10_supra", ["-c:v", "libx264", "-crf", "10"], 300_000),
    ("diez_veces_menos", ["-c:v", "libx264", "-b:v", "200000"], 2_000_000),
    ("diez_veces_mas", ["-c:v", "libx264", "-b:v", "20000000"], 2_000_000),
]


def patologicas(trabajo, solo=None):
    filas = []
    for etiqueta, fuente, ext in FUENTES:
        if solo and etiqueta != solo:
            continue
        for nombre, banderas, declara in PATOLOGICAS:
            dst = os.path.join(trabajo, f"P_{etiqueta}_{nombre}.{ext}")
            argv = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
                    "-threads", "4", "-i", fuente, "-map", "0", *banderas,
                    "-c:a", "copy", dst]
            r = subprocess.run(argv, stdin=subprocess.DEVNULL, timeout=TOPE_FFMPEG,
                               capture_output=True)
            # Trampa 25: el `rc` de cada celda se registra. Una salida de 0 bytes
            # puede ser un proceso que no arrancó.
            fila = {"clase": "patologica", "fuente": etiqueta, "codec": nombre,
                    "pedido_bps": declara, "rc": r.returncode}
            fila.update(mide(dst, declara))
            # El contrato, con el pedido que el motor DEBERÍA haber respetado.
            ped = {"params": {"codec_video": "h264", "codec_video_real": "libx264",
                              "bitrate_video_bps": declara}}
            res = verificador.verificar(dst, ped, fuente)
            fila["veredicto"] = res["veredicto"]
            fila["reglas"] = sorted({h["regla"] for h in res["hallazgos"]
                                     if h["severidad"] in ("fallo", "aviso")})
            filas.append(fila)
            print("P %-8s %-18s %8d  real=%-9s cont=%-9s desv_real=%-8s desv_cont=%-8s %s"
                  % (etiqueta, nombre, declara,
                     fila.get("bitrate_video_real"), fila.get("bitrate_contenedor"),
                     _pc(fila.get("desvio_real")), _pc(fila.get("desvio_contenedor")),
                     fila["veredicto"]), flush=True)
    return filas


def _pc(x):
    return "-" if x is None else "%+.2f%%" % (x * 100)


def main():
    trabajo = sys.argv[1]
    rapido = "--rapido" in sys.argv
    solo = None
    for a in sys.argv[2:]:
        if a.startswith("--solo="):
            solo = a.split("=", 1)[1]
    os.makedirs(trabajo, exist_ok=True)
    # R21: se lista ANTES y DESPUÉS. Hay motores que escriben en el `cwd`.
    antes = sorted(os.listdir(trabajo))
    veta_gpu()
    fx = nucleo.FileX(raices_lectura=[RAIZ, trabajo],
                      raices_escritura=[trabajo])
    filas = legitimas(trabajo, fx, rapido, solo) + patologicas(trabajo, solo)
    despues = sorted(os.listdir(trabajo))
    res = {"n": len(filas), "trabajo": trabajo,
           "antes_del_directorio": antes, "despues_del_directorio": despues,
           "filas": filas}
    nombre = "calibracion_%s.json" % solo if solo else "calibracion.json"
    with open(os.path.join(AQUI, nombre), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("\n-> %s  (%d celdas)" % (nombre, len(filas)))


if __name__ == "__main__":
    main()
