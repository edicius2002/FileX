# -*- coding: utf-8 -*-
"""C16 -- una muestra estratificada de los 445 formatos «no_materializables»
(`bench/salidas-aristas/semi_entrada.json`: 359 de ffmpeg + 86 de ImageMagick,
`estado == "no_materializable"`), medida de verdad con ficheros REALES del
corpus FATE (`D:\\Work\\research\\fate-suite`, 1,3 GB, 2 529 ficheros, fuera del
repositorio a proposito -- no se copia, no se versiona).

De los 445, **69 tienen un subdirectorio en FATE con el mismo nombre que el
formato** (68 de ffmpeg -- 1 de los 359 candidatos, `g723_1`, es en realidad
la RUTA de `rco`/`tco` de la ronda anterior, no un nombre nuevo -- + 1 de
ImageMagick, `heif`). Es un emparejamiento por NOMBRE DE DIRECTORIO, no
exhaustivo: FATE organiza por decodificador/formato y el nombre no siempre
coincide con el que usa `filex`/ffmpeg como extension de entrada -- se
declara como sesgo, no se esconde (ver el informe).

Mismo metodo, mismo `corre()`/`inv_ffmpeg()`/`inv_magick()` que
`bench/salidas-aristas/_semi_in.py` (trampa 79: la MISMA orden que ejecuta el
codigo del censo original, no una reescritura): para ffmpeg, destinos
`["mkv","wav","png"]` en ese orden, cualquiera que funcione basta; para
ImageMagick, `["png"]`. Tope de 25 s por intento, exactamente como el censo.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-fate-y-aristas/c16_semi_entrada_fate.py
"""
from __future__ import annotations

import json
import os
import subprocess
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAL = os.path.dirname(os.path.abspath(__file__))
FATE = r"D:\Work\research\fate-suite"
FFMPEG = r"D:\utils\ffmpeg\bin\ffmpeg.exe"
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TIMEOUT = 25
EXCLUIR = {"md5sum", "csum", "readme", "license", "changelog", "notes",
          "info.txt", "checksums"}


def corre(args, timeout=TIMEOUT):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=timeout, errors="replace")
        return p.returncode, (p.stderr or "")[-600:], (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT", (time.perf_counter() - t0) * 1000
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:200], (time.perf_counter() - t0) * 1000


def inv_ffmpeg(ent, dest, sal):
    return [FFMPEG, "-nostdin", "-y", "-i", ent, sal]


def inv_magick(ent, dest, sal):
    return [MAGICK, ent, "-auto-orient", sal]


def smallest_file(d):
    best = None
    for root, _, files in os.walk(d):
        for f in files:
            base = f.lower().rsplit(".", 1)[0]
            if base in EXCLUIR or f.lower() in EXCLUIR:
                continue
            p = os.path.join(root, f)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if sz < 100:
                continue
            if best is None or sz < best[1]:
                best = (p, sz)
    return best


def main():
    no_mat = json.load(open(os.path.join(RAIZ, "bench", "salidas-aristas",
                                         "semi_entrada.json"), encoding="utf-8"))
    no_mat2 = json.load(open(os.path.join(RAIZ, "bench", "salidas-aristas",
                                          "semi_entrada2.json"), encoding="utf-8"))
    formatos_nm = {"ffmpeg": set(), "imagemagick": set()}
    for d in (no_mat, no_mat2):
        for k, v in d.items():
            motor, fmt = k.split("|", 1)
            if v.get("estado") == "no_materializable":
                formatos_nm[motor].add(fmt)
    print("no_materializable: ffmpeg=%d imagemagick=%d"
          % (len(formatos_nm["ffmpeg"]), len(formatos_nm["imagemagick"])))

    tmp = os.path.join(SAL, "tmp16")
    os.makedirs(tmp, exist_ok=True)

    emparejados = []
    for motor, destinos, inv in (("ffmpeg", ["mkv", "wav", "png"], inv_ffmpeg),
                                 ("imagemagick", ["png"], inv_magick)):
        for fmt in sorted(formatos_nm[motor]):
            d = os.path.join(FATE, fmt)
            if not os.path.isdir(d):
                continue
            bf = smallest_file(d)
            if bf:
                emparejados.append((motor, fmt, bf[0], bf[1], destinos, inv))
    print("emparejados por nombre de directorio en FATE: %d de %d"
          % (len(emparejados), sum(len(v) for v in formatos_nm.values())))

    filas = []
    t0 = time.time()
    for i, (motor, fmt, ruta_fate, bytes_fate, destinos, inv) in enumerate(emparejados):
        vivo, det = False, []
        for dest in destinos:
            sal = os.path.join(tmp, "x.%s" % dest)
            if os.path.exists(sal):
                os.remove(sal)
            rc, err, ms = corre(inv(ruta_fate, dest, sal))
            tam = os.path.getsize(sal) if os.path.exists(sal) else -1
            det.append({"destino": dest, "rc": rc, "bytes": tam, "ms": round(ms, 1),
                       "err": err.replace("\n", " ")[-200:] if (rc != 0 or tam <= 0) else ""})
            if rc == 0 and tam > 0:
                vivo = True
                break
        filas.append({"motor": motor, "formato": fmt, "fate_ruta": ruta_fate,
                     "fate_bytes": bytes_fate, "estado": "viva" if vivo else "muerta",
                     "intentos": det})
        print("  %-12s %-14s FATE=%-40s %6d B  ->  %s  (%.0fs)"
              % (motor, fmt, os.path.basename(ruta_fate), bytes_fate,
                 "VIVA" if vivo else "MUERTA", time.time() - t0))
        for f in os.listdir(tmp):
            try:
                os.remove(os.path.join(tmp, f))
            except OSError:
                pass

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    vivas = sum(1 for f in filas if f["estado"] == "viva")
    resultado = {
        "n_no_materializable_total": {m: len(s) for m, s in formatos_nm.items()},
        "n_emparejados_en_fate": len(emparejados),
        "n_vivas": vivas, "n_muertas": len(filas) - vivas,
        "tasa_viva_muestra": round(vivas / len(filas), 4) if filas else None,
        "filas": filas,
    }
    with open(os.path.join(SAL, "c16_semi_entrada_fate_resultado.json"), "w",
             encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)
    print("\n%d/%d VIVAS de la muestra FATE (%.1f %%)"
          % (vivas, len(filas), 100 * vivas / len(filas) if filas else 0))


if __name__ == "__main__":
    main()
