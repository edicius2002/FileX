#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Banco de medida de la EXTENSION de fidelidad del verificador de FileX.

Subcomandos:
  alfa        min(alfa) EN PROCESO frente a `magick -format %[fx:minima.a]`
  contrato    re-verificacion de las 53 salidas: 0 falsos positivos, cobertura
  reglas      coste unitario de cada regla de fidelidad (mediana n>=9)
  fidelidad   las 53 salidas pasadas por las reglas de fidelidad
  texto       umbral de txtwrite (>=10 caracteres) y su coste
  fallos      los 5 fallos documentados siguen atrapados

No usa la GPU. Medianas de n>=9, etiqueta limpia/SUCIA por testigo de CPU.
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

# Salidas del patron oro producidas con -c copy / -map 0 -c copy. El patron oro
# no lo marca en el 'pedido'; se deduce de referencia.json -> ordenes
# (vid.mkv2mp4.copy, vid.mp42mkv, vid.extraer.copy).
COPIA = {"2pistas_mkv-to-COPY.mp4", "tipico_mp4-to.mkv", "tipico_mp4-audio-copy.m4a"}


def _testigo():
    t = time.perf_counter()
    s = 0
    for i in range(300000):
        s += i * i
    return (time.perf_counter() - t) * 1000


def measure(etiqueta, n, fn, calentar=1):
    for _ in range(calentar):
        fn()
    antes = min(_testigo() for _ in range(3))
    tiempos = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        tiempos.append((time.perf_counter() - t) * 1000)
    despues = min(_testigo() for _ in range(3))
    desv = abs(despues - antes) / max(antes, 1e-9)
    flag = "limpia" if desv <= 0.20 else "SUCIA(testigo %+.0f%%)" % (desv * 100)
    tiempos.sort()
    return {"etiqueta": etiqueta, "n": n,
            "mediana_ms": round(statistics.median(tiempos), 3),
            "min_ms": round(tiempos[0], 3), "max_ms": round(tiempos[-1], 3),
            "flag": flag, "testigo_ms": [round(antes, 2), round(despues, 2)]}


def trabajos_fid():
    """Los 53 trabajos con el marcador 'copia' anadido donde toca."""
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
def cmd_alfa():
    """min(alfa) en proceso frente a magick. Mejor caso y peor caso."""
    casos = [
        ("PNG 1920x1080 RGBA16 OPACO (peor caso)", "corpus/imagen/tipico.png"),
        ("PNG 200x200 paleta+tRNS con alfa real (mejor caso)", "corpus/imagen/alpha.png"),
        ("PNG 4000x3000 RGB16 sin alfa", "bench/salidas-referencia/imagen/16bit_tif-to-d16.png"),
        ("PNG 64x64 paleta 1 bit sin alfa", "corpus/imagen/trivial.png"),
        ("PNG 200x200 paleta+tRNS (salida)", "bench/salidas-referencia/imagen/alpha_png-to.png8.png"),
        ("WebP con perdida sin alfa", "corpus/imagen/tipico.webp"),
        ("WebP con perdida + ALPH sin perdida (VP8L)", "bench/salidas-referencia/imagen/alpha_png-to.webp"),
        ("WebP sin perdida (VP8L) sin alfa", "bench/salidas-referencia/imagen/trivial_png-to-lossless.webp"),
        ("JPEG (el formato no admite alfa)", "bench/salidas-referencia/imagen/tipico_png-to.jpg"),
        ("AVIF con alfa (no evaluable en proceso)", "bench/salidas-referencia/imagen/alpha_png-to.avif"),
        ("TIFF 16 bits sin alfa", "corpus/imagen/patologico_16bit.tif"),
        ("GIF con transparencia declarada", "bench/salidas-referencia/video/trivial_mp4-to-palette.gif"),
    ]
    res = []
    for etiqueta, rel in casos:
        ruta = os.path.join(RAIZ, rel.replace("/", os.sep))
        if not os.path.exists(ruta):
            continue
        r0 = V.alfa_minimo(ruta, exacto=True)
        proc = measure("proceso:" + etiqueta, 9,
                       lambda ru=ruta: V.alfa_minimo(ru, exacto=True))
        rapido = measure("proceso-corte:" + etiqueta, 9,
                         lambda ru=ruta: V.alfa_minimo(ru, exacto=False))
        def mag(ru=ruta):
            subprocess.run(["magick", ru, "-format", "%[fx:minima.a]", "info:"],
                           capture_output=True, timeout=120)
        p = subprocess.run(["magick", ruta, "-format", "%[fx:minima.a]", "info:"],
                           capture_output=True, text=True)
        magick = measure("magick:" + etiqueta, 9, mag)
        res.append({
            "caso": etiqueta, "ruta": rel,
            "bytes": os.path.getsize(ruta),
            "evaluable": r0.get("evaluable"), "via": r0.get("via"),
            "motivo": r0.get("motivo"),
            "alfa_min_proceso": r0.get("alfa_min"),
            "alfa_no_trivial": r0.get("alfa_no_trivial"),
            "exacto": r0.get("exacto"),
            "filas_leidas": r0.get("filas_leidas"),
            "alfa_min_magick": p.stdout.strip(),
            "proceso_exacto_ms": proc["mediana_ms"], "proceso_flag": proc["flag"],
            "proceso_corte_ms": rapido["mediana_ms"],
            "magick_ms": magick["mediana_ms"], "magick_flag": magick["flag"],
            "factor": (round(magick["mediana_ms"] / proc["mediana_ms"], 1)
                       if proc["mediana_ms"] else None),
        })
        print("%-52s proc=%8.2f ms  corte=%8.2f ms  magick=%8.2f ms  x%s"
              % (etiqueta[:52], proc["mediana_ms"], rapido["mediana_ms"],
                 magick["mediana_ms"], res[-1]["factor"]))
    # suelo: solo descomprimir el peor caso
    import zlib
    ruta = os.path.join(RAIZ, "corpus", "imagen", "tipico.png")

    def suelo():
        with open(ruta, "rb") as fh:
            m = V._png_meta(fh)
            do = zlib.decompressobj()
            for b in V._png_bloques_idat(fh, m["pos_idat"]):
                do.decompress(b)
    s = measure("suelo zlib del peor caso", 9, suelo)
    guardar("alfa.json", {"casos": res, "suelo_zlib_peor_caso": s})
    return res


# ===========================================================================
def cmd_contrato():
    """Las 53 salidas: 0 falsos positivos con y sin min(alfa) en proceso."""
    res = {}
    for motor in ("proceso", "subproceso"):
        for modo in ("inyectado", "en_proceso", "sin_alfa"):
            filas = []
            for t in trabajos_fid():
                se = V.sondear(t["entrada"], motor)
                if modo == "inyectado":
                    se.update(t["extra_entrada"])
                r = V.verificar(t["salida"], t["pedido"], t["entrada"], motor,
                                sonda_ent=se, alfa=(modo == "en_proceso"))
                filas.append({
                    "salida": os.path.basename(t["salida"]),
                    "esperado": t["esperado"], "veredicto": r["veredicto"],
                    "cobertura_completa": all(r["cobertura"].values()),
                    "sin_cubrir": [k for k, v in r["cobertura"].items() if not v],
                    "ms_alfa": round(r["ms"].get("alfa", 0), 3),
                    "hallazgos": [h for h in r["hallazgos"]
                                  if h["severidad"] in ("fallo", "aviso")],
                })
            fp = [f for f in filas
                  if f["veredicto"] == "fallo" and f["esperado"] != "fallo"]
            fn = [f for f in filas
                  if f["veredicto"] != "fallo" and f["esperado"] == "fallo"]
            parcial = [f["salida"] for f in filas if not f["cobertura_completa"]]
            res["%s/%s" % (motor, modo)] = {
                "n": len(filas), "falsos_positivos": len(fp),
                "falsos_negativos": len(fn),
                "detalle_fp": [f["salida"] for f in fp],
                "cobertura_parcial": len(parcial), "parciales": parcial,
                "avisos": sum(1 for f in filas if f["veredicto"] == "aviso"),
                "ms_alfa_total": round(sum(f["ms_alfa"] for f in filas), 2),
                "filas": filas,
            }
            print("%-24s FP=%d FN=%d parciales=%2d avisos=%d alfa=%.1f ms"
                  % ("%s/%s" % (motor, modo), len(fp), len(fn), len(parcial),
                     res["%s/%s" % (motor, modo)]["avisos"],
                     res["%s/%s" % (motor, modo)]["ms_alfa_total"]))
    guardar("contrato.json", res)
    return res


# ===========================================================================
def cmd_fidelidad():
    """Las 53 salidas por las reglas de fidelidad."""
    filas = []
    t0g = time.perf_counter()
    for t in trabajos_fid():
        t0 = time.perf_counter()
        r = V.verificar_fidelidad(t["salida"], t["pedido"], t["entrada"])
        ms = (time.perf_counter() - t0) * 1000
        filas.append({
            "salida": os.path.basename(t["salida"]),
            "cat": t["cat"], "esperado": t["esperado"],
            "veredicto": r["veredicto"], "cobertura": r["cobertura"],
            "ms": round(ms, 1), "ms_regla": {k: round(v, 1) for k, v in r["ms"].items()},
            "hallazgos": r["hallazgos"],
        })
        print("%-38s %-10s %8.0f ms  %s" % (filas[-1]["salida"], r["veredicto"],
                                            ms, r["cobertura"]))
    total = (time.perf_counter() - t0g) * 1000
    fallos = [f for f in filas if f["veredicto"] == "fallo"]
    resumen = {"n": len(filas), "total_ms": round(total, 1),
               "fallos": [f["salida"] for f in fallos],
               "avisos": [f["salida"] for f in filas if f["veredicto"] == "aviso"],
               "ok_parcial": [f["salida"] for f in filas
                              if f["veredicto"] == "ok_parcial"],
               "filas": filas}
    print("\nTOTAL %.0f ms | fallos %d | avisos %d | ok_parcial %d"
          % (total, len(fallos), len(resumen["avisos"]), len(resumen["ok_parcial"])))
    guardar("fidelidad.json", resumen)
    return resumen


# ===========================================================================
def cmd_reglas():
    """Coste unitario de cada regla de fidelidad, mediana n>=9."""
    r = lambda *p: os.path.join(RAIZ, *p)
    IMG = ("bench", "salidas-referencia", "imagen")
    VID = ("bench", "salidas-referencia", "video")
    AUD = ("bench", "salidas-referencia", "audio")
    PDF = ("bench", "salidas-referencia", "pdf")
    casos = [
        ("I3 aplanado (magick 1 pixel, JPEG 200x200)", 9,
         lambda: V._pixel_magick(r(*IMG, "alpha_png-to.jpg"), 0, 0)),
        ("I6 RMSE 200x200 paleta", 9,
         lambda: V._magick_metrica(r("corpus", "imagen", "alpha.png"),
                                   r(*IMG, "alpha_png-to.png8.png"), "RMSE")),
        ("I6 RMSE 4000x3000 16 bits (72 MB TIFF vs 61 MB PNG)", 9,
         lambda: V._magick_metrica(r("corpus", "imagen", "patologico_16bit.tif"),
                                   r(*IMG, "16bit_tif-to-d16.png"), "RMSE")),
        ("I7 PSNR 1920x1080", 9,
         lambda: V._magick_metrica(r("corpus", "imagen", "tipico.png"),
                                   r(*IMG, "tipico_png-to.jpg"), "PSNR")),
        ("I7 PSNR 200x200 sobre blanco (2 composiciones)", 9,
         lambda: V._magick_metrica(r("corpus", "imagen", "alpha.png"),
                                   r(*IMG, "alpha_png-to.avif"), "PSNR", True)),
        ("V9 paleta del GIF (EN PROCESO)", 9,
         lambda: V._paleta_es_rejilla(V._paleta_gif(r(*VID, "trivial_mp4-to-naive.gif")))),
        ("V6 framemd5 de trivial.mp4 (540 KB, 90 fotogramas)", 9,
         lambda: V._ffmpeg_framemd5(r("corpus", "video", "trivial.mp4"))),
        ("V6 framemd5 de tipico.mp4 (16 MB, 600 fotogramas)", 9,
         lambda: V._ffmpeg_framemd5(r("corpus", "video", "tipico.mp4"))),
        ("V8 PSNR de video 640x360 (trivial -> webm)", 9,
         lambda: V._ffmpeg_psnr(r(*VID, "trivial_mp4-to.webm"),
                                r("corpus", "video", "trivial.mp4"))),
        ("V8 PSNR de video 1920x1080 (tipico -> webm)", 5,
         lambda: V._ffmpeg_psnr(r(*VID, "tipico_mp4-to.webm"),
                                r("corpus", "video", "tipico.mp4"))),
        ("A4 md5 del PCM (WAV 706 KB, 8 s)", 9,
         lambda: V._ffmpeg_md5_pcm(r("corpus", "audio", "trivial.wav"))),
        ("A4 md5 del PCM (FLAC 104 KB, 8 s)", 9,
         lambda: V._ffmpeg_md5_pcm(r("corpus", "audio", "tipico.flac"))),
        ("A5 md5 del PCM de la pista de un MP4 de 16 MB", 9,
         lambda: V._ffmpeg_md5_pcm(r("corpus", "video", "tipico.mp4"))),
        ("P6 txtwrite sobre un PDF de texto (3 KB)", 9,
         lambda: V._gs_texto(r("corpus", "pdf", "tipico_texto.pdf"))),
        ("P6 txtwrite sobre un PDF rasterizado (6 KB)", 9,
         lambda: V._gs_texto(r(*PDF, "alpha_png-to.pdf"))),
        ("P6 txtwrite sobre un PDF escaneado (8,5 MB)", 9,
         lambda: V._gs_texto(r("corpus", "pdf", "patologico_escaneado.pdf"))),
        ("CONTRATO completo en proceso (referencia)", 15,
         lambda: V.verificar(r(*IMG, "tipico_png-to.jpg"),
                             {"destino": "jpg", "params": {}},
                             r("corpus", "imagen", "tipico.png"), "proceso")),
    ]
    res = []
    for etiqueta, n, fn in casos:
        m = measure(etiqueta, n, fn)
        res.append(m)
        print("%-58s %10.2f ms  n=%-3d %s" % (etiqueta[:58], m["mediana_ms"],
                                              m["n"], m["flag"]))
    guardar("reglas.json", res)
    return res


# ===========================================================================
def cmd_texto():
    """El umbral de txtwrite: >=10 caracteres, no >0."""
    casos = [
        ("corpus/pdf/tipico_texto.pdf", "con capa de texto real"),
        ("corpus/pdf/trivial.pdf", "sin texto"),
        ("corpus/pdf/patologico_escaneado.pdf", "escaneado, sin capa de texto"),
        ("corpus/pdf/escaneado_d1.pdf", "escaneado, sin capa de texto"),
        ("bench/salidas-referencia/pdf/alpha_png-to.pdf", "imagen -> PDF"),
        ("bench/salidas-referencia/pdf/tipico_png-to.pdf", "imagen -> PDF"),
        ("bench/salidas-referencia/pdf/tipico_jpg-to.pdf", "imagen -> PDF"),
        ("bench/salidas-referencia/pdf/tipico_texto_rasterizado.pdf", "PDF rasterizado"),
        ("bench/salidas-referencia/pdf/tipico_texto_pdf-to-gs.pdf", "PDF -> PDF con gs"),
    ]
    res = []
    for rel, nota in casos:
        ruta = os.path.join(RAIZ, rel.replace("/", os.sep))
        if not os.path.exists(ruta):
            continue
        txt, err = V._gs_texto(ruta)
        n = len("".join((txt or "").split()))
        m = measure(rel, 9, lambda ru=ruta: V._gs_texto(ru))
        res.append({"ruta": rel, "nota": nota, "n_chars": n,
                    "muestra": (txt or "").strip()[:40],
                    "umbral_10": n >= V.TEXTO_MIN_CHARS,
                    "umbral_0": n > 0,
                    "ms": m["mediana_ms"], "flag": m["flag"], "bytes": os.path.getsize(ruta)})
        print("%-52s n=%-5d >=10:%-5s >0:%-5s %8.1f ms  %r"
              % (rel[-52:], n, n >= V.TEXTO_MIN_CHARS, n > 0, m["mediana_ms"],
                 (txt or "").strip()[:20]))
    falsos_con_0 = [x for x in res if x["umbral_0"] and not x["umbral_10"]]
    print("\nCon umbral >0 se declararian %d PDF con 'capa de texto' que NO la tienen: %s"
          % (len(falsos_con_0), [x["ruta"] for x in falsos_con_0]))
    guardar("texto.json", {"casos": res,
                           "falsos_positivos_con_umbral_0": len(falsos_con_0)})
    return res


# ===========================================================================
def cmd_fallos():
    """Los 5 fallos documentados siguen atrapados tras la extension."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="filex_fid_")
    r = lambda *p: os.path.join(RAIZ, *p)
    res = []
    try:
        # 1. PNG con extension .avif
        f1 = os.path.join(tmp, "falso.avif")
        shutil.copyfile(r("corpus", "imagen", "tipico.png"), f1)
        # 5. fichero de 0 bytes
        f5 = os.path.join(tmp, "vacio.mp4")
        open(f5, "wb").close()
        # 2. pierde una pista de audio
        f2 = r("bench", "salidas-referencia", "video", "2pistas_mkv-to-DEFAULT.mp4")
        # 3. degradacion de 16 a 8 bits SIN pedirlo
        f3 = r("bench", "salidas-referencia", "imagen", "16bit_tif-to-d8.png")
        # 4. redimensionado no solicitado con barras
        f4 = os.path.join(tmp, "redim.png")
        subprocess.run(["magick", r("corpus", "imagen", "tipico.png"),
                        "-resize", "800x600", "-background", "black", "-gravity",
                        "center", "-extent", "800x600", f4], capture_output=True)
        f4b = os.path.join(tmp, "control.png")
        subprocess.run(["magick", r("corpus", "imagen", "tipico.jpg"), f4b],
                       capture_output=True)
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
    guardar("fallos.json", {"n_mal": sum(1 for x in res if not x["correcto"]),
                            "casos": res})
    return res


CMDS = {"alfa": cmd_alfa, "contrato": cmd_contrato, "fidelidad": cmd_fidelidad,
        "reglas": cmd_reglas, "texto": cmd_texto, "fallos": cmd_fallos}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        print("subcomandos: %s" % " ".join(CMDS))
        sys.exit(2)
    CMDS[sys.argv[1]]()
