#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N24 — el contrato ENTERO sobre las 84 celdas, con V10 y sin V10.

No basta con que la aritmética del umbral cuadre: hay que pasar las celdas por
`verificar()` y comparar el veredicto antes y después, porque una regla nueva
puede mover un veredicto por un camino que la tabla no ve (trampa 70: sigue el
valor hasta donde se USA).

`--antes` carga el verificador de `HEAD`, igual que `regresion_53_n4.py`.

Uso: python bench/salidas-bitrate/verificar_v10.py [--antes] <dir_trabajo>
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

FUENTE = {"trivial": ("corpus/video/trivial.mp4", "mkv"),
          "2pistas": ("corpus/video/patologico_2pistas.mkv", "mp4"),
          "tipico": ("corpus/video/tipico.mp4", "mkv")}


def cargar(antes):
    if not antes:
        from filex import verificador as V
        return V, "despues"
    tmp = os.path.join(tempfile.gettempdir(), "n4_verificador_head.py")
    with open(tmp, "wb") as fh:
        fh.write(subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                                capture_output=True, cwd=RAIZ, timeout=60).stdout)
    spec = importlib.util.spec_from_file_location("verificador_head", tmp)
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    return V, "antes"


def celdas():
    vistas = {}
    for n in ("calibracion.json", "calibracion_2pistas.json"):
        p = os.path.join(AQUI, n)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            for f in json.load(fh)["filas"]:
                if f.get("bytes"):
                    vistas[(f["clase"], f["fuente"], f["codec"], f["pedido_bps"])] = f
    return list(vistas.values())


def main():
    antes = "--antes" in sys.argv
    trabajo = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    V, sufijo = cargar(antes)
    filas, resumen = [], {}
    for f in celdas():
        ent_rel, ext = FUENTE[f["fuente"]]
        entrada = os.path.join(RAIZ, ent_rel)
        pre = "L" if f["clase"] == "legitima" else "P"
        nombre = ("%s_%s_%s_%s.%s" % (pre, f["fuente"], f["codec"], f["pedido_bps"], ext)
                  if f["clase"] == "legitima"
                  else "%s_%s_%s.%s" % (pre, f["fuente"], f["codec"], ext))
        ruta = os.path.join(trabajo, nombre)
        if not os.path.exists(ruta):
            # La primera pasada escribió las patológicas de `2pistas` en `.mkv`.
            alt = os.path.splitext(ruta)[0] + ".mkv"
            ruta = alt if os.path.exists(alt) else ruta
        if not os.path.exists(ruta):
            resumen.setdefault("sin_fichero", 0)
            resumen["sin_fichero"] += 1
            continue
        ped = {"params": {"codec_video": f["codec"], "bitrate_video_bps": f["pedido_bps"]}}
        r = V.verificar(ruta, ped, entrada)
        v10 = [h for h in r["hallazgos"] if h.get("regla") == "V10"]
        fila = {"clase": f["clase"], "fuente": f["fuente"], "codec": f["codec"],
                "pedido_bps": f["pedido_bps"], "veredicto": r["veredicto"],
                "v10": [h["severidad"] for h in v10],
                "desvio_contenedor": f.get("desvio_contenedor"),
                "n_audio": f.get("n_audio")}
        filas.append(fila)
        k = (f["clase"], r["veredicto"], tuple(fila["v10"]))
        resumen[str(k)] = resumen.get(str(k), 0) + 1
    salida = {"n": len(filas), "resumen": resumen, "filas": filas}
    with open(os.path.join(AQUI, "v10_%s.json" % sufijo), "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=1)
    print("[%s] %d celdas" % (sufijo, len(filas)))
    for k in sorted(resumen):
        print("   %-60s %d" % (k, resumen[k]))
    fp = [f for f in filas if f["clase"] == "legitima" and "fallo" in f["v10"]]
    fn = [f for f in filas if f["clase"] == "patologica" and "fallo" not in f["v10"]]
    print("  FALSOS POSITIVOS de V10 sobre legítimas: %d" % len(fp))
    print("  patológicas NO atrapadas por V10:        %d %s"
          % (len(fn), [(f["fuente"], f["codec"], f["n_audio"]) for f in fn]))


if __name__ == "__main__":
    main()
