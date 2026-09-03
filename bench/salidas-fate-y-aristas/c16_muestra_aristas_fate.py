# -*- coding: utf-8 -*-
"""C16, segundo nivel -- para los orígenes de FATE que salieron VIVOS en
`c16_semi_entrada_fate.py` (67 de 69), una muestra de ARISTAS reales: cada
origen contra un conjunto FIJO de 6 destinos que cruza familias (vídeo,
imagen, audio), para que la tasa que salga no sea sólo «¿se puede leer?»
sino «¿a cuántos de los destinos declarados llega?».

**Diferencia declarada con el criterio de `aristas-nominales.md`:** aquella
muestra (n=498) pasaba el contrato de 5 puntos completo
(`verificador_congelado.py`). Aquí el criterio es el más barato de la
trampa 75 -- `rc == 0` Y `bytes > 0` --, que es más PERMISIVO (cuenta como
buena una arista que el contrato completo podría rechazar por firma
incorrecta o metadatos mal puestos). **No es el mismo bar** y el número que
sale aquí no se sustituye por el 23,1 % de la muestra original: se declara
aparte, como una segunda medición con un criterio más barato sobre un
estrato que la muestra original no cubría (los orígenes «no
materializables»).

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-fate-y-aristas/c16_muestra_aristas_fate.py
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

# 6 destinos fijos que cruzan familia (vídeo/imagen/audio), el mismo
# criterio de estratificacion motor/familia que `_muestra.py`, simplificado.
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
    previo = json.load(open(os.path.join(SAL, "c16_semi_entrada_fate_resultado.json"),
                            encoding="utf-8"))
    vivas = [f for f in previo["filas"] if f["estado"] == "viva"]
    print("orígenes vivos de la tanda anterior: %d" % len(vivas))

    tmp = os.path.join(SAL, "tmp16b")
    os.makedirs(tmp, exist_ok=True)

    filas = []
    t0 = time.time()
    for i, fila in enumerate(vivas):
        motor, fmt, ent = fila["motor"], fila["formato"], fila["fate_ruta"]
        destinos = DESTINOS_FFMPEG if motor == "ffmpeg" else DESTINOS_MAGICK
        for dest in destinos:
            sal = os.path.join(tmp, "y.%s" % dest)
            if os.path.exists(sal):
                os.remove(sal)
            if motor == "ffmpeg":
                argv = [FFMPEG, "-nostdin", "-y", "-i", ent, sal]
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
        if i % 10 == 0:
            print("  %d/%d orígenes (%.0fs)" % (i, len(vivas), time.time() - t0), flush=True)

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    buenas = sum(1 for f in filas if f["buena"])
    por_origen = {}
    for f in filas:
        k = (f["motor"], f["origen"])
        por_origen.setdefault(k, []).append(f["buena"])
    origenes_con_al_menos_una = sum(1 for v in por_origen.values() if any(v))

    resultado = {
        "n_origenes": len(vivas), "n_aristas_probadas": len(filas),
        "n_aristas_buenas": buenas,
        "tasa_aristas_buenas": round(buenas / len(filas), 4) if filas else None,
        "origenes_con_al_menos_un_destino_bueno": origenes_con_al_menos_una,
        "criterio": "rc==0 y bytes>0 (trampa 75), NO el contrato de 5 puntos "
                    "completo que usa aristas-nominales.md",
        "filas": filas,
    }
    with open(os.path.join(SAL, "c16_muestra_aristas_fate_resultado.json"), "w",
             encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)
    print("\n%d/%d aristas buenas (%.1f %%), criterio rc==0&&bytes>0"
          % (buenas, len(filas), 100 * buenas / len(filas) if filas else 0))
    print("%d/%d orígenes con AL MENOS un destino bueno de los %d probados"
          % (origenes_con_al_menos_una, len(vivas), len(DESTINOS_FFMPEG)))


if __name__ == "__main__":
    main()
