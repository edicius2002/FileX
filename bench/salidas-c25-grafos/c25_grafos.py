# -*- coding: utf-8 -*-
"""C25 -- las 9 aristas candidatas a otra invocacion del grafo de filtros
(bench/bitrate-por-pista.md, tercera pasada C25).

Todas fallaban con `[af#0:0 ...]`/`[vf#0:0 ...] Task finished with error
code: -22`, que es la huella de un nodo de formato IMPLICITO -- el que
ffmpeg inserta solo entre decodificador y codificador cuando estos no
coinciden -- que revienta al abrir el codificador. La ronda 1 clasifico
esto como «candidata a grafo de filtros» mirando solo el nombre del nodo en
el stderr (af#0:0 / vf#0:0); esta ronda diagnostica la causa exacta bajando
al mensaje de apertura del ENCODER, que es distinto en cada celda, y la
reduce a TRES familias, ninguna de las cuales necesita `filter_complex`
(grafo multi-entrada): basta un `-af`/`-vf` de UN filtro.

  A. Channel layout ambiguo (aptx, msbc, tta): el decodificador entrega un
     layout "N channels" generico (no especificado) y el encoder aac lo
     rechaza literalmente con `Unsupported channel layout "N channels"`.
     Arreglo: `-channel_layout {stereo,mono}` explicito.
  B. Frecuencia de muestreo fija del codificador (loas, uw: `roq_dpcm`
     exige 22050 Hz con el mensaje textual `Audio must be 22050 Hz`; avi,
     mov: `g723_1` exige 8000 Hz, sin mensaje textual -- es conocimiento
     externo del codec, no leido en el stderr). Arreglo: `-ar` al valor que
     el codificador exige.
  C. Geometria de video invalida para el codificador (webp, bmp): `h263`
     solo acepta 5 tamanos enumerados (`Valid sizes are 128x96, 176x144,
     352x288, 704x576, 1408x1152`) y `rv10` ademas tiene un TECHO de
     macrobloques (`Encoding frames with N (>= 4096) macroblocks is not
     implemented`) que 704x576 (1584 mb) no toca pero 1920x1072 (8040 mb,
     solo multiplo de 16) si. Arreglo: `-vf scale=704:576`.

Ninguna de las 9 necesitaba realmente un GRAFO (nodos conectados con `;` /
`[etiquetas]`): un solo filtro basta. La etiqueta de ronda 1 acerto el
SITIO (el filtro), no la NATURALEZA de la causa.

No se reutiliza D:\\Work\\research\\FileX (worktree ajeno; `bench/salidas-invocacion/
_p2_semillas.py` tiene esa raiz cableada y no se toca). Se regeneran aqui
los 9 crudos minimos que hacen falta: derivaciones triviales de una fuente
sintetica compartida (`testsrc=352x288` + `sine`, la misma receta de
`_p2_semillas.py::semillas_base` para `video_cif`) o del corpus.

Control aplicado a cada celda (trampa 75): buena solo si `rc == 0` Y
`bytes > 0`. Control adicional que la trampa 75 no cubre y que si hace
falta aqui: leer la salida de vuelta con `ffprobe` (para `g723_1`, un
formato RAW sin cabecera, con `-f g723_1` explicito, igual que exigiria
leer PCM crudo) -- un `rc=0` con bytes no es un fichero DECODIFICABLE por
si solo si el propio ffmpeg no pudo escribir una cabecera. Control
positivo de aparato (variante de trampa 81 para esta forma de fallo, que no
es un grafo de identidad): la MISMA funcion `corre()`/`con_cota()` que mide
las 9 celdas se aplica primero a una arista YA buena (`m.tta -> .flac`,
sin patologia conocida) -- si el aparato de medida mintiera, tambien
fallaria ahi.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-c25-grafos/c25_grafos.py
"""
from __future__ import annotations

import json
import os
import subprocess

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAL = os.path.dirname(os.path.abspath(__file__))
FFMPEG = r"D:\utils\ffmpeg\bin\ffmpeg.exe"
FFPROBE = r"D:\utils\ffmpeg\bin\ffprobe.exe"
MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
TIMEOUT_EXTERNO = 30
COTA_INTERNA = "8"  # segundos, -t dentro de la orden (trampa 52)


def rc_firmado(rc: int) -> int:
    return rc - 2**32 if rc >= 2**31 else rc


def corre(argv, timeout=TIMEOUT_EXTERNO):
    try:
        p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=timeout)
        rc = rc_firmado(p.returncode)
        err = p.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        rc, err = -9, "TIMEOUT %ds" % timeout
    return rc, err


# --------------------------------------------------------------------------
# 1. Semillas minimas -- regeneradas aqui, no en D:\Work\research\FileX
# --------------------------------------------------------------------------

def preparar_semillas():
    IN = os.path.join(SAL, "in")
    os.makedirs(IN, exist_ok=True)
    cif = os.path.join(IN, "s_cif.mp4")
    if not os.path.exists(cif):
        rc, err = corre([FFMPEG, "-nostdin", "-y", "-f", "lavfi", "-i",
                         "testsrc=size=352x288:rate=25:duration=1", "-f", "lavfi", "-i",
                         "sine=frequency=440:duration=1:sample_rate=48000", "-c:v", "libx264",
                         "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-shortest", cif], 60)
        assert rc == 0 and os.path.getsize(cif) > 0, ("s_cif.mp4", rc, err[-300:])

    rutas = {}
    for ext in ("aptx", "msbc", "tta", "loas", "avi", "uw", "mov"):
        dest = os.path.join(IN, "m." + ext)
        if not os.path.exists(dest):
            rc, err = corre([FFMPEG, "-nostdin", "-y", "-i", cif, dest], 30)
            assert rc == 0 and os.path.getsize(dest) > 0, (ext, rc, err[-300:])
        rutas[ext] = dest

    bmp = os.path.join(IN, "m.bmp")
    if not os.path.exists(bmp):
        rc, err = corre([MAGICK, os.path.join(RAIZ, "corpus", "imagen", "tipico.jpg"),
                         "-auto-orient", bmp], 30)
        assert rc == 0 and os.path.getsize(bmp) > 0, ("bmp", rc, err[-300:])
    rutas["bmp"] = bmp
    rutas["webp"] = os.path.join(RAIZ, "corpus", "imagen", "tipico.webp")
    return rutas


# --------------------------------------------------------------------------
# 2. Las 9 celdas: argv baseline (reconstruccion fiel de P2) y argv arreglado
# --------------------------------------------------------------------------

# argv posterior a "-i <entrada>", reconstruido AL BYTE del que dejo
# bench/salidas-bitrate-pista/c25-segunda-pasada.json (P2, tercera pasada de
# C25). El nombre de la arista (p.ej. "tta -> h265.mp4") es una ETIQUETA
# descriptiva del residuo, no el nombre del muxer -- confundirlos fue un
# error de la primera version de este script: "h265.mp4" no es un `-f`
# valido. El muxer real de cada celda es el que sigue a `-f` aqui abajo.
ARGV_COLA = {
    "aptx": ["-map", "0:a", "-c:a", "aac", "-ar", "96000", "-sample_fmt", "fltp",
             "-f", "ismv"],
    "msbc": ["-map", "0:a", "-c:a", "aac", "-ar", "96000", "-sample_fmt", "fltp",
             "-f", "ismv"],
    "tta": ["-map", "0:a", "-c:a", "aac", "-ar", "96000", "-sample_fmt", "fltp",
            "-f", "mp4"],
    "loas": ["-map", "0:a", "-c:a", "roq_dpcm", "-sample_fmt", "s16", "-f", "roq"],
    "uw": ["-map", "0:a", "-c:a", "roq_dpcm", "-sample_fmt", "s16", "-f", "roq"],
    "avi": ["-map", "0:a", "-c:a", "g723_1", "-ac", "1", "-sample_fmt", "s16",
            "-f", "g723_1"],
    "mov": ["-map", "0:a", "-c:a", "g723_1", "-ac", "1", "-sample_fmt", "s16",
            "-f", "g723_1"],
    "webp": ["-map", "0:v", "-c:v", "rv10", "-pix_fmt", "yuv420p", "-strict", "-2",
             "-f", "rm"],
    "bmp": ["-map", "0:v", "-c:v", "h263", "-pix_fmt", "yuv420p", "-strict", "-2",
            "-f", "3gp"],
}


def argv_baseline(a, b, entrada, salida):
    return ([FFMPEG, "-nostdin", "-y", "-i", entrada] + ARGV_COLA[a] +
            ["-t", COTA_INTERNA, salida])


# nombre de familia -> argumentos extra que sustituyen/completan al baseline
ARREGLO = {
    "aptx": (["-channel_layout", "stereo"], "A: channel_layout ambiguo"),
    "msbc": (["-channel_layout", "mono"], "A: channel_layout ambiguo"),
    "tta": (["-channel_layout", "mono"], "A: channel_layout ambiguo"),
    "loas": (["-ar", "22050"], "B: frecuencia fija del codificador (roq_dpcm=22050Hz)"),
    "uw": (["-ar", "22050"], "B: frecuencia fija del codificador (roq_dpcm=22050Hz)"),
    "avi": (["-ar", "8000"], "B: frecuencia fija del codificador (g723_1=8000Hz)"),
    "mov": (["-ar", "8000"], "B: frecuencia fija del codificador (g723_1=8000Hz)"),
    "webp": (["-vf", "scale=704:576"], "C: geometria invalida (rv10: techo de 4096 macrobloques)"),
    "bmp": (["-vf", "scale=704:576"], "C: geometria invalida (h263: 5 tamanos enumerados)"),
}


def argv_filtro(a, b, entrada, salida):
    extra, _ = ARREGLO[a]
    base = argv_baseline(a, b, entrada, salida)
    # insertar los argumentos extra justo antes de "-f" (mismo sitio en las 9)
    i = base.index("-f")
    return base[:i] + extra + base[i:]


CELDAS = [
    ("aptx", "isma"), ("msbc", "ismv"), ("webp", "rm"), ("tta", "h265.mp4"),
    ("loas", "roq"), ("bmp", "3gp"), ("avi", "rco"), ("uw", "roq"), ("mov", "tco"),
]


def clasifica_stderr(err):
    if "[af#0:0" in err:
        return "af#0:0"
    if "[vf#0:0" in err:
        return "vf#0:0"
    return "otro"


def linea_causa(err):
    """La linea de stderr con el mensaje del ENCODER, no del nodo generico."""
    for marca in ("Unsupported channel layout", "Audio must be", "not valid for",
                  "must be a multiple of", "macroblocks is not implemented"):
        i = err.find(marca)
        if i >= 0:
            ini = err.rfind("\n", 0, i) + 1
            fin = err.find("\n", i)
            return err[ini:fin if fin >= 0 else None].strip()
    return ""


def verifica_ffprobe(salida, formato_raw=None):
    """Lee de vuelta con ffprobe. g723_1 es un formato RAW sin cabecera:
    necesita `-f g723_1` explicito para que ffprobe sepa demultiplexarlo,
    igual que exigiria PCM crudo."""
    argv = [FFPROBE, "-v", "error"]
    if formato_raw:
        argv += ["-f", formato_raw]
    argv += ["-show_entries", "stream=codec_name,sample_rate,channels,width,height",
            "-of", "default=noprint_wrappers=1", salida]
    rc, err = corre(argv, 15)
    return rc == 0, err.strip()


def main():
    rutas = preparar_semillas()
    out = os.path.join(SAL, "out")
    os.makedirs(out, exist_ok=True)

    # --- control positivo de aparato: una arista SIN patologia conocida ---
    ctrl_dest = os.path.join(out, "_control_tta_flac")
    ctrl_argv = [FFMPEG, "-nostdin", "-y", "-i", rutas["tta"], "-map", "0:a",
                "-c:a", "flac", "-f", "flac", "-t", COTA_INTERNA, ctrl_dest]
    ctrl_rc, ctrl_err = corre(ctrl_argv)
    ctrl_bytes = os.path.getsize(ctrl_dest) if os.path.exists(ctrl_dest) else 0
    ctrl_ok, ctrl_probe_err = verifica_ffprobe(ctrl_dest) if ctrl_rc == 0 and ctrl_bytes else (False, "")
    print("CONTROL POSITIVO (tta->flac, sin patologia): rc=%d bytes=%d ffprobe_ok=%s"
          % (ctrl_rc, ctrl_bytes, ctrl_ok))
    assert ctrl_rc == 0 and ctrl_bytes > 0 and ctrl_ok, \
        "el aparato de medida falla en un caso SANO -- no midas nada mas"

    filas = []
    for a, b in CELDAS:
        entrada = rutas[a]
        base_dest = os.path.join(out, "%s_%s_base" % (a, b))
        fil_dest = os.path.join(out, "%s_%s_filtro" % (a, b))
        rc_b, err_b = corre(argv_baseline(a, b, entrada, base_dest))
        tam_b = os.path.getsize(base_dest) if os.path.exists(base_dest) else 0
        rc_f, err_f = corre(argv_filtro(a, b, entrada, fil_dest))
        tam_f = os.path.getsize(fil_dest) if os.path.exists(fil_dest) else 0
        buena_f = rc_f == 0 and tam_f > 0
        formato_raw = "g723_1" if a in ("avi", "mov") else None
        probe_ok, probe_err = verifica_ffprobe(fil_dest, formato_raw) if buena_f else (False, "")
        fila = {
            "a": a, "b": b, "familia": ARREGLO[a][1],
            "base_argv": argv_baseline(a, b, entrada, base_dest),
            "base_rc": rc_b, "base_bytes": tam_b, "base_nodo": clasifica_stderr(err_b),
            "base_causa": linea_causa(err_b),
            "filtro_argv": argv_filtro(a, b, entrada, fil_dest),
            "filtro_rc": rc_f, "filtro_bytes": tam_f,
            "buena_base": rc_b == 0 and tam_b > 0,
            "buena_filtro": buena_f,
            "ffprobe_decodifica": probe_ok,
            "ffprobe_muestra": probe_err[-200:] if not probe_ok else "",
        }
        filas.append(fila)
        print("%-6s -> %-9s  base rc=%-5d  filtro rc=%-4d bytes=%-6d ffprobe=%s  %s"
              % (a, b, rc_b, rc_f, tam_f, probe_ok,
                 "ARREGLADO" if buena_f and not fila["buena_base"] else
                 ("sigue rota" if not buena_f else "ya iba bien")))

    resultado = {"control_positivo": {"rc": ctrl_rc, "bytes": ctrl_bytes, "ffprobe_ok": ctrl_ok},
                "filas": filas}
    with open(os.path.join(SAL, "resultado_c25.json"), "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=1, ensure_ascii=False)

    n_rotas_base = sum(1 for f in filas if not f["buena_base"])
    n_arreglo = sum(1 for f in filas if f["buena_filtro"] and not f["buena_base"])
    n_decodifica = sum(1 for f in filas if f["ffprobe_decodifica"])
    print("\n%d/9 confirmadas rotas en la base" % n_rotas_base)
    print("%d/9 arregladas con un filtro explicito de UN solo nodo" % n_arreglo)
    print("%d/9 de las arregladas se releen con ffprobe sin error" % n_decodifica)


if __name__ == "__main__":
    main()
