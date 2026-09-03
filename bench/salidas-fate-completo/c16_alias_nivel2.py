# -*- coding: utf-8 -*-
"""C16, segundo nivel, sobre los ALIAS -- mismo metodo exacto que
`bench/salidas-fate-y-aristas/c16_muestra_aristas_fate.py` (worker2, ronda
11), aplicado a los origenes VIVOS de `c16_alias_fate.py` (ffmpeg) y
`c16_alias_fate_imagemagick.py` (imagemagick). 6 destinos fijos por
origen, criterio barato `rc==0 && bytes>0` (trampa 75), NO el contrato de
5 puntos completo.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-fate-completo/c16_alias_nivel2.py
"""
from __future__ import annotations

import json
import os
import subprocess
import time

SAL = os.path.dirname(os.path.abspath(__file__))
FFMPEG = r"D:\utils\ffmpeg\bin\ffmpeg.exe"
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TIMEOUT = 20

DESTINOS_FFMPEG = ["mkv", "gif", "png", "mp3", "wav", "flac"]
DESTINOS_MAGICK = ["png", "jpg", "webp", "bmp", "tiff", "gif"]


def corre(args, timeout=TIMEOUT):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=timeout)
        return p.returncode, (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, (time.perf_counter() - t0) * 1000


def main():
    ff = json.load(open(os.path.join(SAL, "c16_alias_fate_resultado.json"), encoding="utf-8"))
    im = json.load(open(os.path.join(SAL, "c16_alias_fate_imagemagick_resultado.json"), encoding="utf-8"))

    origenes = []
    for f in ff["filas"]:
        if f.get("estado") == "viva":
            origenes.append(("ffmpeg", f["formato"], f["fate_ruta"], f.get("forzado_con_-f")))
    for f in im["filas"]:
        if f.get("estado") == "viva":
            origenes.append(("imagemagick", f["formato"], f["fate_ruta"], None))

    print("orígenes vivos (alias) a probar en nivel 2: %d" % len(origenes))

    tmp = os.path.join(SAL, "tmp16c")
    os.makedirs(tmp, exist_ok=True)

    filas = []
    t0 = time.time()
    for i, (motor, fmt, ent, forzar) in enumerate(origenes):
        destinos = DESTINOS_FFMPEG if motor == "ffmpeg" else DESTINOS_MAGICK
        for dest in destinos:
            sal = os.path.join(tmp, "y.%s" % dest)
            if os.path.exists(sal):
                os.remove(sal)
            if motor == "ffmpeg":
                argv = [FFMPEG, "-nostdin", "-y"]
                if forzar:
                    argv += ["-f", forzar]
                argv += ["-i", ent, sal]
            else:
                argv = [MAGICK, ent, "-auto-orient", sal]
            rc, ms = corre(argv)
            cands = [f for f in os.listdir(tmp)
                    if f == "y.%s" % dest or f.startswith("y.%s-" % dest)]
            tam = max((os.path.getsize(os.path.join(tmp, c)) for c in cands), default=0)
            buena = rc == 0 and tam > 0
            filas.append({"motor": motor, "origen": fmt, "destino": dest,
                         "rc": rc, "bytes": tam, "ms": round(ms, 1), "buena": buena})
            for f in os.listdir(tmp):
                try:
                    os.remove(os.path.join(tmp, f))
                except OSError:
                    pass
        print("  %d/%d (%s/%s) (%.0fs)" % (i + 1, len(origenes), motor, fmt, time.time() - t0),
              flush=True)

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    buenas = sum(1 for f in filas if f["buena"])
    por_origen = {}
    for f in filas:
        k = (f["motor"], f["origen"])
        por_origen.setdefault(k, []).append(f["buena"])
    origenes_con_al_menos_una = sum(1 for v in por_origen.values() if any(v))

    resultado = {
        "n_origenes": len(origenes), "n_aristas_probadas": len(filas),
        "n_aristas_buenas": buenas,
        "tasa_aristas_buenas": round(buenas / len(filas), 4) if filas else None,
        "origenes_con_al_menos_un_destino_bueno": origenes_con_al_menos_una,
        "criterio": "rc==0 y bytes>0 (trampa 75), NO el contrato de 5 puntos "
                    "completo",
        "filas": filas,
    }
    with open(os.path.join(SAL, "c16_alias_nivel2_resultado.json"), "w",
             encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)
    print("\n%d/%d aristas buenas (%.1f %%)"
          % (buenas, len(filas), 100 * buenas / len(filas) if filas else 0))
    print("%d/%d orígenes con AL MENOS un destino bueno"
          % (origenes_con_al_menos_una, len(origenes)))


if __name__ == "__main__":
    main()
