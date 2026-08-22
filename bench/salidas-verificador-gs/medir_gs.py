#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Banco de medida del encargo V1 (C1 + C2).

Es una COPIA ADAPTADA de bench/salidas-verificacion-fidelidad/medir_fid.py, que
pertenece al informe anterior y no se toca. Aqui solo hay lo que este informe
necesita, mas los subcomandos nuevos.

Subcomandos:
  cobertura   coste de min(alfa) en los formatos NUEVOS (TIFF, GIF, Adam7)
  reglas      coste unitario de V2 y V5, mediana n>=9
  contrato    re-verificacion de las 53 salidas: falsos positivos, cobertura
  fidelidad   las 53 salidas por las reglas de fidelidad, con V2 y V5
  fallos      los 5 fallos documentados siguen atrapados

Sin GPU. Medianas de n>=9, etiqueta limpia/SUCIA por testigo de CPU determinista
medido ANTES y DESPUES de cada tanda (umbral 20 %). Hay otro agente midiendo en
CPU en paralelo: el etiquetado es obligatorio, no decorativo.
"""
import json
import os
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
VIEJO = os.path.join(RAIZ, "bench", "salidas-verificacion")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, VIEJO)

import verificador as V           # noqa: E402
from trabajos import trabajos     # noqa: E402

FIX = os.path.join(AQUI, "fixtures")
COPIA = {"2pistas_mkv-to-COPY.mp4", "tipico_mp4-to.mkv", "tipico_mp4-audio-copy.m4a"}


def _testigo():
    """Testigo de CPU MONOHILO, el del informe anterior. Se conserva para que
    las etiquetas sigan siendo comparables."""
    t = time.perf_counter()
    s = 0
    for i in range(300000):
        s += i * i
    return (time.perf_counter() - t) * 1000


# CALIBRACION del testigo de subproceso, tomada con la maquina en reposo al
# principio de esta sesion. Ver el informe: el testigo monohilo NO ve la
# contencion multinucleo (12 nucleos, un bucle de Python cabe en uno libre) y
# etiqueto `limpia` una tanda que salio x6,8 respecto a la misma medida del
# informe anterior. El testigo que SI la ve es lanzar un proceso.
TESTIGO_SUB_BASE = None


def _testigo_sub():
    """Testigo de LANZAMIENTO DE PROCESO: mide lo mismo que sufre una sonda
    externa (planificador, E/S, Defender), no lo que sufre un bucle de Python."""
    t = time.perf_counter()
    subprocess.run(["ffprobe", "-v", "quiet", "-version"], capture_output=True,
                   stdin=subprocess.DEVNULL, timeout=60)
    return (time.perf_counter() - t) * 1000


def calibrar():
    global TESTIGO_SUB_BASE
    for _ in range(2):
        _testigo_sub()
    TESTIGO_SUB_BASE = min(_testigo_sub() for _ in range(5))
    print("# testigo de subproceso en reposo: %.1f ms" % TESTIGO_SUB_BASE)
    return TESTIGO_SUB_BASE


def measure(etiqueta, n, fn, calentar=1):
    for _ in range(calentar):
        fn()
    antes = min(_testigo() for _ in range(3))
    sub_a = min(_testigo_sub() for _ in range(3))
    tiempos = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        tiempos.append((time.perf_counter() - t) * 1000)
    despues = min(_testigo() for _ in range(3))
    sub_d = min(_testigo_sub() for _ in range(3))
    desv = abs(despues - antes) / max(antes, 1e-9)
    sub = max(sub_a, sub_d)
    nivel = (sub / TESTIGO_SUB_BASE) if TESTIGO_SUB_BASE else None
    motivos = []
    if desv > 0.20:
        motivos.append("deriva cpu %+.0f%%" % (desv * 100))
    if nivel and nivel > 1.20:
        motivos.append("nivel sub x%.1f" % nivel)
    flag = "limpia" if not motivos else "SUCIA(%s)" % "; ".join(motivos)
    tiempos.sort()
    return {"etiqueta": etiqueta, "n": n,
            "mediana_ms": round(statistics.median(tiempos), 3),
            "min_ms": round(tiempos[0], 3), "max_ms": round(tiempos[-1], 3),
            "flag": flag, "testigo_ms": [round(antes, 2), round(despues, 2)],
            "testigo_sub_ms": [round(sub_a, 1), round(sub_d, 1)],
            "nivel_sub": round(nivel, 2) if nivel else None}


def trabajos_fid():
    out = []
    for t in trabajos():
        t = dict(t)
        t["pedido"] = dict(t["pedido"])
        t["pedido"]["params"] = dict(t["pedido"]["params"])
        if os.path.basename(t["salida"]) in COPIA:
            t["pedido"]["params"]["copia"] = True
        out.append(t)
    return out


def guardar(nombre, obj):
    ruta = os.path.join(AQUI, nombre)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=str)
    print("-> %s" % ruta)


# ===========================================================================
def cmd_cobertura():
    """Coste de min(alfa) en los formatos que ANTES devolvian 'no evaluable'."""
    casos = [
        ("TIFF 200x200 RGBA8 LZW+pred2 con alfa real", "fixtures/alpha_tiff_lzw.tif"),
        ("TIFF 200x200 RGBA8 Deflate+pred2 con alfa real", "fixtures/alpha_tiff_zip.tif"),
        ("TIFF 200x200 RGBA8 PackBits con alfa real", "fixtures/alpha_tiff_rle.tif"),
        ("TIFF 200x200 RGBA8 sin comprimir con alfa real", "fixtures/alpha_tiff_none.tif"),
        ("TIFF 200x200 RGBA8 LZW planar con alfa real", "fixtures/alpha_tiff_planar.tif"),
        ("TIFF 200x200 RGBA16 LZW con alfa real", "fixtures/alpha_tiff_lzw16.tif"),
        ("TIFF 1920x1080 RGBA16 LZW OPACO (peor caso)", "fixtures/tipico_tiff_lzw.tif"),
        ("TIFF 1920x1080 RGBA16 Deflate OPACO", "fixtures/tipico_tiff_zip16.tif"),
        ("TIFF 4000x3000 RGB16 sin alfa (cabecera)", "corpus/imagen/patologico_16bit.tif"),
        ("GIF 200x200 paleta con transparencia USADA", "fixtures/alpha_gif.gif"),
        ("GIF animado 320x240 que DECLARA y no usa (patron oro)",
         "bench/salidas-referencia/video/trivial_mp4-to-palette.gif"),
        ("GIF animado 320x180 sin declararla (patron oro)",
         "bench/salidas-referencia/video/trivial_mp4-to-naive.gif"),
        ("GIF 1920x1080 opaco (cabecera)", "fixtures/tipico_gif_opaco.gif"),
        ("PNG Adam7 200x200 paleta+tRNS con alfa real", "fixtures/alpha_adam7.png"),
        ("PNG Adam7 200x200 RGBA8 con alfa real", "fixtures/alpha_adam7_rgba.png"),
        ("PNG Adam7 200x200 RGBA16 con alfa real", "fixtures/alpha_adam7_rgba16.png"),
        ("PNG Adam7 1920x1080 RGBA16 OPACO (peor caso)", "fixtures/tipico_adam7.png"),
        ("PNG Adam7 1920x1080 RGBA8 OPACO", "fixtures/tipico_adam7_8b.png"),
        ("PNG Adam7 13x9 paleta 2 bits, transp. en la esquina",
         "fixtures/adam7_4b_esquina.png"),
        ("--- controles ya cubiertos antes ---", None),
        ("PNG 1920x1080 RGBA16 OPACO (peor caso del informe anterior)",
         "corpus/imagen/tipico.png"),
        ("PNG 200x200 paleta+tRNS (mejor caso)", "corpus/imagen/alpha.png"),
        ("AVIF con alfa (sigue NO EVALUABLE a proposito)",
         "bench/salidas-referencia/imagen/alpha_png-to.avif"),
    ]
    res = []
    for etiqueta, rel in casos:
        if rel is None:
            continue
        ruta = os.path.join(RAIZ, rel.replace("/", os.sep)) if not rel.startswith("fixtures") \
            else os.path.join(AQUI, rel.replace("/", os.sep))
        if not os.path.exists(ruta):
            print("  (falta %s)" % rel)
            continue
        r0 = V.alfa_minimo(ruta, exacto=True)
        proc = measure("proc:" + etiqueta, 9, lambda ru=ruta: V.alfa_minimo(ru, exacto=True))
        corte = measure("corte:" + etiqueta, 9, lambda ru=ruta: V.alfa_minimo(ru, exacto=False))

        def mag(ru=ruta):
            subprocess.run(["magick", ru, "-format", "%[fx:minima.a]", "info:"],
                           capture_output=True, timeout=300, stdin=subprocess.DEVNULL)
        p = subprocess.run(["magick", ruta, "-format", "%[fx:minima.a]", "info:"],
                           capture_output=True, text=True, timeout=300,
                           stdin=subprocess.DEVNULL)
        magick = measure("magick:" + etiqueta, 9, mag)
        res.append({
            "caso": etiqueta, "ruta": rel, "bytes": os.path.getsize(ruta),
            "evaluable": r0.get("evaluable"), "via": r0.get("via"),
            "motivo": r0.get("motivo"), "nota": r0.get("nota"),
            "alfa_min_proceso": r0.get("alfa_min"),
            "alfa_no_trivial": r0.get("alfa_no_trivial"),
            "exacto": r0.get("exacto"), "filas_leidas": r0.get("filas_leidas"),
            "alfa_min_magick": p.stdout.strip(),
            "proceso_exacto_ms": proc["mediana_ms"], "proceso_flag": proc["flag"],
            "proceso_corte_ms": corte["mediana_ms"], "corte_flag": corte["flag"],
            "magick_ms": magick["mediana_ms"], "magick_flag": magick["flag"],
            "factor": (round(magick["mediana_ms"] / proc["mediana_ms"], 1)
                       if proc["mediana_ms"] else None),
        })
        print("%-56s proc=%9.2f  corte=%9.2f  magick=%9.2f  x%-8s %s"
              % (etiqueta[:56], proc["mediana_ms"], corte["mediana_ms"],
                 magick["mediana_ms"], res[-1]["factor"], proc["flag"]))
    guardar("cobertura_alfa.json", res)
    return res


# ===========================================================================
def cmd_reglas():
    """Coste unitario de V2 y V5, y los controles del informe anterior."""
    r = lambda *p: os.path.join(RAIZ, *p)
    VID = ("bench", "salidas-referencia", "video")
    casos = [
        ("V2 -count_frames trivial.mp4 (540 KB, 90 fotogramas)", 9,
         lambda: V._ffprobe_fotogramas(r("corpus", "video", "trivial.mp4"))),
        ("V2 -count_frames trivial_mp4-to.webm (VP9)", 9,
         lambda: V._ffprobe_fotogramas(r(*VID, "trivial_mp4-to.webm"))),
        ("V2 -count_frames patologico_2pistas.mkv (4 MB)", 9,
         lambda: V._ffprobe_fotogramas(r("corpus", "video", "patologico_2pistas.mkv"))),
        ("V2 -count_frames tipico.mp4 (16 MB, 600 fotogramas)", 9,
         lambda: V._ffprobe_fotogramas(r("corpus", "video", "tipico.mp4"))),
        ("V5 etiquetas de patologico_2pistas.mkv", 9,
         lambda: V._ffprobe_etiquetas(r("corpus", "video", "patologico_2pistas.mkv"))),
        ("V5 etiquetas de tipico.mp4", 9,
         lambda: V._ffprobe_etiquetas(r("corpus", "video", "tipico.mp4"))),
        ("V5 etiquetas de tipico.flac", 9,
         lambda: V._ffprobe_etiquetas(r("corpus", "audio", "tipico.flac"))),
        ("V6 framemd5 de trivial.mp4 (control del informe anterior)", 9,
         lambda: V._ffmpeg_framemd5(r("corpus", "video", "trivial.mp4"))),
        ("CONTRATO completo en proceso (referencia)", 15,
         lambda: V.verificar(r("bench", "salidas-referencia", "imagen",
                               "tipico_png-to.jpg"),
                             {"destino": "jpg", "params": {}},
                             r("corpus", "imagen", "tipico.png"), "proceso")),
    ]
    res = []
    for etiqueta, n, fn in casos:
        m = measure(etiqueta, n, fn)
        res.append(m)
        print("%-58s %10.2f ms  n=%-3d %s" % (etiqueta[:58], m["mediana_ms"],
                                              m["n"], m["flag"]))
    guardar("reglas_v2_v5.json", res)
    return res


# ===========================================================================
def cmd_contrato():
    res = {}
    for motor in ("proceso", "subproceso"):
        for modo in ("inyectado", "en_proceso", "sin_alfa"):
            filas = []
            for t in trabajos_fid():
                se = V.sondear(t["entrada"], motor)
                if modo == "inyectado":
                    se.update(t["extra_entrada"])
                rr = V.verificar(t["salida"], t["pedido"], t["entrada"], motor,
                                 sonda_ent=se, alfa=(modo == "en_proceso"))
                filas.append({
                    "salida": os.path.basename(t["salida"]),
                    "esperado": t["esperado"], "veredicto": rr["veredicto"],
                    "cobertura_completa": all(rr["cobertura"].values()),
                    "sin_cubrir": [k for k, v in rr["cobertura"].items() if not v],
                    "ms_alfa": round(rr["ms"].get("alfa", 0), 3),
                    "hallazgos": [h for h in rr["hallazgos"]
                                  if h["severidad"] in ("fallo", "aviso")],
                })
            fp = [f for f in filas
                  if f["veredicto"] == "fallo" and f["esperado"] != "fallo"]
            fn = [f for f in filas
                  if f["veredicto"] != "fallo" and f["esperado"] == "fallo"]
            parcial = [f["salida"] for f in filas if not f["cobertura_completa"]]
            clave = "%s/%s" % (motor, modo)
            res[clave] = {"n": len(filas), "falsos_positivos": len(fp),
                          "falsos_negativos": len(fn),
                          "detalle_fp": [f["salida"] for f in fp],
                          "cobertura_parcial": len(parcial), "parciales": parcial,
                          "avisos": sum(1 for f in filas if f["veredicto"] == "aviso"),
                          "ms_alfa_total": round(sum(f["ms_alfa"] for f in filas), 2),
                          "filas": filas}
            print("%-24s FP=%d FN=%d parciales=%2d avisos=%d alfa=%.1f ms"
                  % (clave, len(fp), len(fn), len(parcial),
                     res[clave]["avisos"], res[clave]["ms_alfa_total"]))
    guardar("contrato53.json", res)
    return res


# ===========================================================================
def cmd_fidelidad():
    filas = []
    t0g = time.perf_counter()
    for t in trabajos_fid():
        t0 = time.perf_counter()
        rr = V.verificar_fidelidad(t["salida"], t["pedido"], t["entrada"])
        ms = (time.perf_counter() - t0) * 1000
        filas.append({"salida": os.path.basename(t["salida"]), "cat": t["cat"],
                      "esperado": t["esperado"], "veredicto": rr["veredicto"],
                      "cobertura": rr["cobertura"], "ms": round(ms, 1),
                      "ms_regla": {k: round(v, 1) for k, v in rr["ms"].items()},
                      "hallazgos": rr["hallazgos"]})
        print("%-38s %-10s %8.0f ms  %s" % (filas[-1]["salida"], rr["veredicto"],
                                            ms, rr["cobertura"]))
    total = (time.perf_counter() - t0g) * 1000
    fallos = [f for f in filas if f["veredicto"] == "fallo"]
    resumen = {"n": len(filas), "total_ms": round(total, 1),
               "fallos": [f["salida"] for f in fallos],
               "avisos": [f["salida"] for f in filas if f["veredicto"] == "aviso"],
               "ok_parcial": [f["salida"] for f in filas
                              if f["veredicto"] == "ok_parcial"],
               "ms_v2": round(sum(f["ms_regla"].get("V2", 0) for f in filas), 1),
               "ms_v5": round(sum(f["ms_regla"].get("V5", 0) for f in filas), 1),
               "filas": filas}
    print("\nTOTAL %.0f ms | fallos %d | avisos %d | ok_parcial %d | V2 %.0f ms | V5 %.0f ms"
          % (total, len(fallos), len(resumen["avisos"]),
             len(resumen["ok_parcial"]), resumen["ms_v2"], resumen["ms_v5"]))
    guardar("fidelidad53.json", resumen)
    return resumen


# ===========================================================================
def cmd_fallos():
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="filex_gs_")
    r = lambda *p: os.path.join(RAIZ, *p)
    res = []
    try:
        f1 = os.path.join(tmp, "falso.avif")
        shutil.copyfile(r("corpus", "imagen", "tipico.png"), f1)
        f5 = os.path.join(tmp, "vacio.mp4")
        open(f5, "wb").close()
        f2 = r("bench", "salidas-referencia", "video", "2pistas_mkv-to-DEFAULT.mp4")
        f3 = r("bench", "salidas-referencia", "imagen", "16bit_tif-to-d8.png")
        f4 = os.path.join(tmp, "redim.png")
        subprocess.run(["magick", r("corpus", "imagen", "tipico.png"),
                        "-resize", "800x600", "-background", "black", "-gravity",
                        "center", "-extent", "800x600", f4], capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=300)
        f4b = os.path.join(tmp, "control.png")
        subprocess.run(["magick", r("corpus", "imagen", "tipico.jpg"), f4b],
                       capture_output=True, stdin=subprocess.DEVNULL, timeout=300)
        casos = [
            ("1 PNG con extension .avif", f1, r("corpus", "imagen", "tipico.png"),
             {"destino": "avif", "params": {}}, "fallo"),
            ("2 pierde una pista de audio", f2,
             r("corpus", "video", "patologico_2pistas.mkv"),
             {"destino": "mp4", "params": {}}, "fallo"),
            ("3 degradacion 16 -> 8 bits no pedida", f3,
             r("corpus", "imagen", "patologico_16bit.tif"),
             {"destino": "png", "params": {}}, "fallo"),
            ("4a redimensionado no solicitado", f4, r("corpus", "imagen", "tipico.png"),
             {"destino": "png", "params": {}}, "fallo"),
            ("4b control: mismo JPEG -> PNG sin tocar geometria", f4b,
             r("corpus", "imagen", "tipico.jpg"), {"destino": "png", "params": {}}, "ok"),
            ("5 fichero de 0 bytes como exito", f5, r("corpus", "video", "tipico.mp4"),
             {"destino": "mp4", "params": {}}, "fallo"),
        ]
        for motor in ("proceso", "subproceso"):
            for nombre, sal, ent, ped, esp in casos:
                t0 = time.perf_counter()
                v = V.verificar(sal, ped, ent, motor, alfa=True)
                ms = (time.perf_counter() - t0) * 1000
                ok = (v["veredicto"] == "fallo") == (esp == "fallo")
                res.append({"caso": nombre, "motor": motor, "esperado": esp,
                            "veredicto": v["veredicto"], "correcto": ok,
                            "ms": round(ms, 2),
                            "cobertura_completa": all(v["cobertura"].values()),
                            "hallazgos": [h for h in v["hallazgos"]
                                          if h["severidad"] == "fallo"]})
                print("%-9s %-46s %-8s %s %8.2f ms" %
                      (motor, nombre, v["veredicto"], "OK" if ok else "*** MAL",
                       ms))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    guardar("fallos5.json", {"n_mal": sum(1 for x in res if not x["correcto"]),
                             "casos": res})
    return res


CMDS = {"cobertura": cmd_cobertura, "reglas": cmd_reglas,
        "contrato": cmd_contrato, "fidelidad": cmd_fidelidad,
        "fallos": cmd_fallos}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        print("subcomandos: %s" % " ".join(CMDS))
        sys.exit(2)
    calibrar()
    CMDS[sys.argv[1]]()
