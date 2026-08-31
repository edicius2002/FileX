#!/usr/bin/env python3
"""N28 y C22: reproducciones acotadas, CPU y directorio desechable."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

from filex import verificador

TOPE = 180
OUT = os.path.dirname(os.path.abspath(__file__))


def ejecutar(argv, cwd):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=TOPE)
        return {"rc": p.returncode, "ms": round((time.perf_counter() - t0) * 1000, 1),
                "stderr": p.stderr.decode("utf-8", "replace")[-800:]}
    except subprocess.TimeoutExpired as e:
        return {"rc": None, "ms": round((time.perf_counter() - t0) * 1000, 1),
                "timeout_s": TOPE,
                "stderr": (e.stderr or b"").decode("utf-8", "replace")[-800:]}


def censo(d):
    # El punto 5 censará también directorios como ``-1``; no usar su tamaño,
    # que cambia al crear hijos y simularía una sobrescritura N8 inexistente.
    return verificador.censar_dir(d)


def n28(tmp):
    filas = []
    casos = [("tipico", "tipico.mp4"), ("dos_pistas", "patologico_2pistas.mkv")]
    patologias = [("crf10_supra", ["-c:v", "libx264", "-crf", "10"], 300_000),
                  ("diez_veces_mas", ["-c:v", "libx264", "-b:v", "20000000"], 2_000_000)]
    for fuente_nombre, fuente_archivo in casos:
        fuente = os.path.join(RAIZ, "corpus", "video", fuente_archivo)
        for etiqueta, banderas, pedido in patologias:
            salida = os.path.join(tmp, f"n28_{fuente_nombre}_{etiqueta}.mkv")
            orden = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
                     "-threads", "4", "-i", fuente, "-map", "0", *banderas,
                     "-c:a", "aac", "-b:a", "128k", salida]
            r = ejecutar(orden, tmp)
            fila = {"caso": f"{fuente_nombre}_{etiqueta}", "orden": orden,
                    **r, "bytes": os.path.getsize(salida) if os.path.exists(salida) else 0}
            if r["rc"] == 0 and fila["bytes"]:
                s = verificador.sondear(salida)
                na = sum(x.get("tipo") == "audio" for x in s.get("pistas", []))
                cont = s.get("bitrate_bps")
                estimado = cont - na * 128_000 if cont else None
                fila.update({"n_audio": na, "bitrate_contenedor_bps": cont,
                             "bitrate_video_estimado_bps": estimado,
                             "desvio_estimado": ((estimado - pedido) / pedido
                                                   if estimado else None)})
                ped_sin = {"params": {"bitrate_video_bps": pedido}}
                ped_con = {"params": {"bitrate_video_bps": pedido,
                                       "bitrate_audio_bps": 128_000}}
                fila["v10_actual"] = [h for h in verificador.punto4_pedido(s, s, ped_sin)
                                       if h.get("regla") == "V10"]
                fila["v10_con_dato"] = [h for h in verificador.punto4_pedido(s, s, ped_con)
                                          if h.get("regla") == "V10"]
            filas.append(fila)
    return filas


def c22(tmp):
    fuente = os.path.join(RAIZ, "corpus", "video", "trivial.mp4")
    destino = os.path.join(tmp, "destino")
    os.mkdir(destino)
    filas = []
    for nombre, salida, extra, pedido in (
        ("hls", os.path.join(destino, "h.m3u8"),
         ["-c:v", "libx264", "-crf", "30", "-hls_time", "1", "-hls_segment_filename",
          os.path.join(destino, "h%03d.ts")], {"destino": "m3u8"}),
        ("secuencia", os.path.join(destino, "f%03d.png"), ["-vf", "fps=4"],
         {"destino": "png"}),
    ):
        for p in list(os.listdir(destino)):
            os.unlink(os.path.join(destino, p))
        antes_t, antes_d = censo(tmp), censo(destino)
        orden = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
                 "-threads", "4", "-i", fuente, *extra, salida]
        r = ejecutar(orden, tmp)
        despues_t, despues_d = censo(tmp), censo(destino)
        cen = {"antes": {os.path.abspath(tmp): antes_t, os.path.abspath(destino): antes_d},
               "despues": {os.path.abspath(tmp): despues_t, os.path.abspath(destino): despues_d}}
        hs = verificador.punto5_escritura(salida, pedido, cen)
        filas.append({"caso": nombre, "orden": orden, **r,
                      "antes_trabajo": antes_t, "despues_trabajo": despues_t,
                      "antes_destino": antes_d, "despues_destino": despues_d,
                      "hallazgos": hs})
    return filas


def main():
    previo = None
    ruta_resultado = os.path.join(OUT, "resultado.json")
    if "--solo-c22" in sys.argv:
        with open(ruta_resultado, encoding="utf-8") as fh:
            previo = json.load(fh)
    with tempfile.TemporaryDirectory(prefix="filex_n28_c22_") as tmp:
        resultado = {"tmp": tmp, "tope_s": TOPE,
                     "n28": previo["n28"] if previo else n28(tmp), "c22": c22(tmp)}
    with open(ruta_resultado, "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
