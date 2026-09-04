# -*- coding: utf-8 -*-
"""C16 -- alias de ImageMagick entre los 85 formatos "no_materializable"
restantes. A diferencia de ffmpeg, la mayoria de estos 85 son "coders"
SINTETICOS de ImageMagick (canvas, gradient, plasma, pattern, msl, pango,
xc, text, label, stegano, tile, hald, radial-gradient...) que GENERAN una
imagen desde parametros -- no son un formato de fichero real que pueda
existir en un corpus como FATE. Otro bloque son formatos RAW de camara
(arw, cr2, cr3, crw, dcr, erf, fff, iiq, k25, kdc, mef, mos, mrw, nef, nrw,
orf, pef, raf, rw2, rwl, sr2, srf, srw, x3f) y de fuente (otf/ttf/ttc/pfa/
pfb/dfont) -- fuera del dominio de FATE (corpus de conformidad de CODECS
de audio/video). Y un tercer bloque son esquemas de red (ftp/http/https),
no ficheros.

De los 85, se busco por EXTENSION en los 2 529 ficheros del corpus (no por
directorio, porque ImageMagick no tiene convenio de nombres de directorio
por formato como FATE) y salieron TRES hits, verificados con `magick
identify` antes de convertir (misma disciplina que la trampa 73/70):

  - `.heic` (6 ficheros en `heif-conformance/`): identify los reconoce
    como HEIC de verdad -- GENUINO.
  - `.3gp` (4 ficheros en `aac/CT_DecoderCheck/`): son contenedores 3GP
    reales (de las pruebas de audio AAC), pero SOLO llevan audio, sin
    pista de video -- el delegado de video de ImageMagick (que reenvia a
    ffmpeg) falla con "Output file does not contain any stream". Es un
    MUERTA genuino, no un fallo de metodo: el fichero es un .3gp real y
    el motor lo intenta, pero no hay fotograma que extraer.
  - `.raw` (3 ficheros): COLISION de extension, confirmada con
    `identify` -- ImageMagick los intenta leer como DNG
    (`error/dng.c/ReadDNGImage`) y falla con "Unsupported file format or
    not RAW file": son un dump de audio TrueHD y dos rasters de filtro,
    no una imagen RAW de camara con la cabecera que el coder espera. Se
    declara la colision, no se cuenta como acierto (misma familia que el
    ".bit" de ffmpeg).

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-fate-completo/c16_alias_fate_imagemagick.py
"""
from __future__ import annotations

import json
import os
import subprocess
import time

SAL = os.path.dirname(os.path.abspath(__file__))
FATE = r"D:\Work\research\fate-suite"
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TIMEOUT = 25


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


CANDIDATOS = {
    "heic": r"heif-conformance\C002.heic",
    "3gp": r"aac\CT_DecoderCheck\File6.3gp",
}
RECHAZADOS = {
    "raw": {
        "candidatos": [r"filter-reference\owdenoise-scenwin.raw",
                       r"filter-reference\owdenoise-scenwin-jpeg.raw",
                       r"lossless-audio\truehd_5.1.raw"],
        "motivo": ("colision de extension: identify los intenta leer como "
                  "DNG (error/dng.c/ReadDNGImage) y falla con 'Unsupported "
                  "file format or not RAW file' -- son un dump de audio "
                  "TrueHD y dos rasters de filtro, no una imagen RAW de "
                  "camara"),
    },
}


def main():
    tmp = os.path.join(SAL, "tmp16im")
    os.makedirs(tmp, exist_ok=True)
    filas = []
    for fmt, rel in CANDIDATOS.items():
        ruta = os.path.join(FATE, rel)
        tam_fate = os.path.getsize(ruta)
        rc_id, err_id, _ = corre([MAGICK, "identify", ruta])
        sal = os.path.join(tmp, "x.png")
        if os.path.exists(sal):
            os.remove(sal)
        rc, err, ms = corre([MAGICK, ruta, "-auto-orient", sal])
        tam = os.path.getsize(sal) if os.path.exists(sal) else -1
        vivo = rc == 0 and tam > 0
        fila = {
            "formato": fmt, "fate_ruta": ruta, "fate_bytes": tam_fate,
            "identify_rc": rc_id,
            "identify_reconoce": (rc_id == 0),
            "convert_rc": rc, "convert_bytes": tam, "convert_ms": round(ms, 1),
            "convert_err": err.replace("\n", " ")[-300:] if not vivo else "",
            "estado": "viva" if vivo else "muerta",
            "resultado": "medido",
        }
        filas.append(fila)
        print("  %-6s identify_ok=%-5s convert_rc=%s bytes=%d -> %s"
              % (fmt, rc_id == 0, rc, tam, "VIVA" if vivo else "MUERTA"))
        if os.path.exists(sal):
            os.remove(sal)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    for fmt, meta in RECHAZADOS.items():
        filas.append({"formato": fmt, "resultado": "colision_de_extension",
                     "candidatos": meta["candidatos"], "motivo": meta["motivo"]})
        print("  %-6s COLISION de extension (declarada, no contada)" % fmt)

    medidas = [f for f in filas if f["resultado"] == "medido"]
    vivas = sum(1 for f in medidas if f["estado"] == "viva")
    resultado = {"n_medidos": len(medidas), "n_vivas": vivas,
                "n_muertas": len(medidas) - vivas, "filas": filas}
    with open(os.path.join(SAL, "c16_alias_fate_imagemagick_resultado.json"),
             "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)
    print("\n%d/%d VIVAS (imagemagick, alias)" % (vivas, len(medidas)))


if __name__ == "__main__":
    main()
