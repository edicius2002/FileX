#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Banco de medida del contrato de verificacion de FileX.

Subcomandos:
  correccion   verifica las 53 salidas del patron oro con los dos motores
  unitario     coste por punto del contrato y por categoria (mediana n>=9)
  conversion   tiempo real de las 39 ordenes del patron oro (para la ratio)
  lote         serie frente a paralelo, 12 nucleos
  fallos       los 5 fallos reales reproducidos
"""
import concurrent.futures as cf
import json
import os
import statistics
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, AQUI)

import verificador as V           # noqa: E402
from trabajos import trabajos     # noqa: E402


# ---------------------------------------------------------------------------
# Arnes: mediana de n>=9 y etiqueta limpia/SUCIA.
# El harness.sh original etiqueta por ruido de GPU; aqui no se usa la GPU, asi
# que el testigo es un trabajo de CPU fijo medido antes y despues de la tanda.
# ---------------------------------------------------------------------------
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


def sonda_entrada(t, motor, cache):
    clave = (t["entrada"], motor)
    if clave not in cache:
        s = V.sondear(t["entrada"], motor)
        s.update(t["extra_entrada"])
        cache[clave] = s
    return cache[clave]


def verificar_trabajo(t, motor, cache=None):
    cache = cache if cache is not None else {}
    return V.verificar(t["salida"], t["pedido"], t["entrada"], motor,
                       sonda_ent=sonda_entrada(t, motor, cache))


# ===========================================================================
def cmd_correccion():
    res = {}
    for motor in ("proceso", "subproceso"):
        cache = {}
        filas = []
        for t in trabajos():
            r = verificar_trabajo(t, motor, cache)
            filas.append({"salida": os.path.basename(t["salida"]), "cat": t["cat"],
                          "esperado": t["esperado"], "veredicto": r["veredicto"],
                          "cobertura": r["cobertura"],
                          "hallazgos": [h for h in r["hallazgos"]
                                        if h["severidad"] in ("fallo", "aviso")]})
        res[motor] = filas
    with open(os.path.join(AQUI, "correccion.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    for motor, filas in res.items():
        fp = [f for f in filas if f["veredicto"] == "fallo" and f["esperado"] != "fallo"]
        par = [f for f in filas if f["veredicto"] == "ok_parcial"]
        fn = [f for f in filas if f["veredicto"] != "fallo" and f["esperado"] == "fallo"]
        print("\n=== motor %s ===  n=%d" % (motor, len(filas)))
        print("  falsos positivos (fallo sobre salida correcta): %d" % len(fp))
        for f in fp:
            print("    %-42s %s" % (f["salida"],
                                    [(h["regla"], h["mensaje"], h["esperado"], h["obtenido"])
                                     for h in f["hallazgos"] if h["severidad"] == "fallo"]))
        print("  falsos negativos: %d %s" % (len(fn), [f["salida"] for f in fn]))
        print("  cobertura parcial (no todo evaluable): %d %s"
              % (len(par), [f["salida"] for f in par]))
        av = [f for f in filas if f["veredicto"] == "aviso"]
        print("  avisos: %d" % len(av))
        for f in av:
            print("    %-42s %s" % (f["salida"],
                                    [(h["regla"], h["mensaje"]) for h in f["hallazgos"]]))


# ===========================================================================
def cmd_unitario(n=11):
    trs = trabajos()
    salidas = []
    # --- 1) coste de cada PUNTO del contrato por separado -----------------
    for motor in ("proceso", "subproceso"):
        cache = {}
        for t in trs:
            sonda_entrada(t, motor, cache)  # precalienta la entrada
        # sondeo de la salida (lo caro) por categoria
        por_cat = {}
        for t in trs:
            por_cat.setdefault(t["cat"], []).append(t)
        for cat, lista in sorted(por_cat.items()):
            m = measure("sonda_salida[%s/%s]" % (motor, cat), n,
                        lambda l=lista: [V.sondear(x["salida"], motor) for x in l])
            m["por_fichero_ms"] = round(m["mediana_ms"] / len(lista), 3)
            m["n_ficheros"] = len(lista)
            m["tipo"] = "sonda"
            m["motor"] = motor
            m["cat"] = cat
            salidas.append(m)
        # verificacion completa por categoria
        for cat, lista in sorted(por_cat.items()):
            m = measure("verificacion_total[%s/%s]" % (motor, cat), n,
                        lambda l=lista, mo=motor, c=cache: [verificar_trabajo(x, mo, c) for x in l])
            m["por_fichero_ms"] = round(m["mediana_ms"] / len(lista), 3)
            m["n_ficheros"] = len(lista)
            m["tipo"] = "total"
            m["motor"] = motor
            m["cat"] = cat
            salidas.append(m)

    # --- 2) desglose por punto (medias de los cronometros internos) -------
    desglose = {}
    for motor in ("proceso", "subproceso"):
        cache = {}
        acum = {}
        for t in trs:
            r = verificar_trabajo(t, motor, cache)
            for _ in range(4):  # repetir para estabilizar la logica pura
                r = verificar_trabajo(t, motor, cache)
            d = acum.setdefault(t["cat"], {})
            for k, v in r["ms"].items():
                d.setdefault(k, []).append(v)
        desglose[motor] = {c: {k: round(statistics.median(v), 4) for k, v in d.items()}
                           for c, d in acum.items()}

    # --- 3) coste desnudo de un proceso: el suelo de Windows --------------
    suelo = []
    for etiq, orden in (
            ("ffprobe -version", ["ffprobe", "-version"]),
            ("magick -version", ["magick", "-version"]),
            ("ffprobe salida tipica (mp3)", ["ffprobe", "-v", "error", "-print_format", "json",
                                             "-show_format", "-show_streams",
                                             trs[0]["salida"]]),
            ("magick identify (png 1920x1080)",
             ["magick", "identify", "-format", "%m|%w|%h|%z",
              os.path.join(RAIZ, "corpus", "imagen", "tipico.png")]),
            # la UNICA propiedad del contrato que exige decodificar pixeles:
            # el minimo del canal alfa (trampa del 'alfa trivial')
            ("magick alfa minima (png 1920x1080)",
             ["magick", os.path.join(RAIZ, "corpus", "imagen", "tipico.png"),
              "-format", "%[fx:minima.a]", "info:"]),
            ("ffprobe mkv 4 MB (2 pistas)",
             ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
              "-show_streams", os.path.join(RAIZ, "corpus", "video",
                                            "patologico_2pistas.mkv")]),
            ("ffprobe mp4 16 MB",
             ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
              "-show_streams", os.path.join(RAIZ, "corpus", "video", "tipico.mp4")]),
            ("magick identify tif 72 MB 16 bits",
             ["magick", "identify", "-format", "%m|%w|%h|%z",
              os.path.join(RAIZ, "corpus", "imagen", "patologico_16bit.tif")]),
    ):
        suelo.append(measure(etiq, n, lambda o=orden: subprocess.run(
            o, capture_output=True, timeout=60)))

    # --- 4) firma magica sola: el punto 1 aislado -------------------------
    firma = measure("punto1_firma_53_ficheros", n,
                    lambda: [V.firma_real(x["salida"]) for x in trs])
    firma["por_fichero_ms"] = round(firma["mediana_ms"] / len(trs), 4)

    datos = {"por_categoria": salidas, "desglose_puntos": desglose,
             "suelo_proceso": suelo, "firma": firma}
    with open(os.path.join(AQUI, "unitario.json"), "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1)
    for m in salidas:
        print("%-42s med:%9.2f ms  n=%-3d rango:%.2f-%.2f  [%s]  /fichero:%s"
              % (m["etiqueta"], m["mediana_ms"], m["n"], m["min_ms"], m["max_ms"],
                 m["flag"], m["por_fichero_ms"]))
    print()
    for m in suelo:
        print("%-42s med:%9.2f ms  [%s]" % (m["etiqueta"], m["mediana_ms"], m["flag"]))
    print("\n%-42s med:%9.3f ms  /fichero:%s" % (firma["etiqueta"], firma["mediana_ms"],
                                                 firma["por_fichero_ms"]))
    print("\ndesglose por punto (mediana ms):")
    for motor, d in desglose.items():
        for c, v in sorted(d.items()):
            print("  %-12s %-8s %s" % (motor, c, {k: round(x, 4) for k, x in v.items()}))


# ===========================================================================
def _sonda_top(par):
    """Funcion de nivel superior: ProcessPoolExecutor no serializa lambdas."""
    ruta, motor = par
    return V.sondear(ruta, motor).get("firma")


def cmd_lote(n=5):
    trs = trabajos()
    lote = [t["salida"] for t in trs]
    grandes = [os.path.join(RAIZ, "corpus", "video", f) for f in
               ("tipico.mp4", "patologico_2pistas.mkv", "trivial.mp4")] * 8
    res = []

    # suelo de Windows: lo que cuesta crear un proceso, haga lo que haga
    suelo = measure("suelo: cmd /c exit", 25,
                    lambda: subprocess.run(["cmd", "/c", "exit"],
                                           capture_output=True, timeout=30))
    suelo.update(modo="suelo", motor="-", lote="1 proceso", hilos=1, n_ficheros=1)
    res.append(suelo)

    def serie(rutas, motor):
        return [V.sondear(x, motor) for x in rutas]

    def paralelo(rutas, motor, hilos):
        with cf.ThreadPoolExecutor(hilos) as ex:
            return list(ex.map(lambda x: V.sondear(x, motor), rutas))

    for motor in ("proceso", "subproceso"):
        for etiqueta, rutas in (("53 salidas patron oro", lote),
                                ("24 videos grandes", grandes)):
            res.append(dict(measure("serie[%s] %s" % (motor, etiqueta), n,
                                    lambda ru=rutas, mo=motor: serie(ru, mo)),
                            modo="serie", motor=motor, lote=etiqueta, hilos=1,
                            n_ficheros=len(rutas)))
            for hilos in (4, 12, 24):
                res.append(dict(measure("hilos%d[%s] %s" % (hilos, motor, etiqueta), n,
                                        lambda ru=rutas, mo=motor, h=hilos: paralelo(ru, mo, h)),
                                modo="hilos", motor=motor, lote=etiqueta, hilos=hilos,
                                n_ficheros=len(rutas)))

    # El motor en proceso es CPU puro bajo el GIL: los hilos no lo escalan.
    # Un grupo de PROCESOS persistente si. Se mide con el grupo ya creado,
    # porque en FileX viviria durante toda la sesion.
    for etiqueta, rutas in (("53 salidas patron oro", lote),
                            ("24 videos grandes", grandes)):
        for np in (4, 12):
            with cf.ProcessPoolExecutor(np) as ex:
                list(ex.map(_sonda_top, [(x, "proceso") for x in rutas[:np]]))
                res.append(dict(measure("procesos%d[proceso] %s" % (np, etiqueta), n,
                                        lambda ru=rutas, e=ex: list(
                                            e.map(_sonda_top,
                                                  [(x, "proceso") for x in ru],
                                                  chunksize=2))),
                                modo="procesos", motor="proceso", lote=etiqueta,
                                hilos=np, n_ficheros=len(rutas)))

    with open(os.path.join(AQUI, "lote.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for m in res:
        print("%-46s med:%9.2f ms  n=%d  [%s]  /fichero:%.3f ms"
              % (m["etiqueta"], m["mediana_ms"], m["n"], m["flag"],
                 m["mediana_ms"] / m["n_ficheros"]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "correccion"
    {"correccion": cmd_correccion, "unitario": cmd_unitario,
     "lote": cmd_lote}[cmd]()
