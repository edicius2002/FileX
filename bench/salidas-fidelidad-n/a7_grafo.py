# -*- coding: utf-8 -*-
"""N18 — la señal de N16 **sin numpy y sin alinear**, y qué cuesta cada renuncia.

Por qué hace falta este arnés
-----------------------------
`filex` no tiene dependencias, y no por descuido: `pyproject.toml` lo dice con
todas las letras (*«añadir una dependencia aquí obliga a justificar por qué no
se puede hacer en proceso»*). La vía de N16 —decodificar a `ndarray`, alinear
con FFT y correlacionar— **no se puede llevar a producción tal cual**, así que
los 183,1 ms de `ventana-antes-del-move.md` §8bis.4 son el coste de una
implementación que este proyecto no puede escribir.

La alternativa se sondea, no se deduce: la identidad

    RMS(x−y)² = RMS(x)² + RMS(y)² − 2·cov(x,y)

convierte **tres RMS en una correlación**, y los tres los da `astats` sobre un
grafo que ffmpeg evalúa en C, en **una sola invocación**. La renuncia es el
ALINEAMIENTO: el grafo resta muestra a muestra, y N16 midió que redondear el
desfase **subestima solo el lado bueno** (trampa 62). Aquí se mide cuánto.

Lo que sale de aquí, por celda:
  * `r_grafo`  — la correlación por canal según el grafo, SIN alinear.
  * `r_ref`    — la de N16: PCM + alineamiento por FFT + Pearson (numpy). Es el
                 patrón contra el que se juzga el grafo; **numpy se usa aquí,
                 en el arnés, no en `filex`**.
  * `desfase`  — el que la FFT encuentra, para saber cuándo importa.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
CORPUS = os.path.join(RAIZ, "corpus", "audio")
TIMEOUT = 300
SR = 48000
DUR = 8.0
DESFASE_MAX = int(0.020 * SR)

sys.path.insert(0, AQUI)
from a7_corr_ancho import (BRUTALES, DESTINOS, alinear_fft, corr,  # noqa: E402
                           fabricar_fuentes, ff, pcm, recortar, rms_db)

log: list[str] = []

# La consola de esta máquina es cp1252 y un signo «menos» tipográfico la tumba
# con `UnicodeEncodeError` — pasó en la primera pasada de este arnés, DESPUÉS de
# 16 minutos de ffmpeg y ANTES de escribir el JSON. Es la trampa 52 en versión
# de arnés: el trabajo se pierde por el final. Se reconfigura la salida y, sobre
# todo, **el JSON se escribe antes de imprimir nada**.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def p(m):
    print(m)
    log.append(m)


# --------------------------------------------------------------- el grafo
#
# **`channel_layouts` NO es decorativo: sin él el grafo NO ARRANCA — MEDIDO**
# (`proto_diag.py`). `amerge` con tres entradas sin disposición declarada da
# `Error reinitializing filters!` y `rc=-5`, en mono, en estéreo y en vídeo con
# audio; con la disposición puesta, `rc=0` y 3·n valores en las tres. La primera
# pasada de este arnés lo tenía quitado y devolvió `grafo=None` en las 264
# celdas: es la trampa 25 en versión de arnés —un `None` uniforme se parece
# mucho a «no hay señal»— y se destapó porque el prototipo, que SÍ lo llevaba,
# funcionaba.
GRAFO = (
    "[0:a]aresample={sr},aformat=sample_fmts=fltp:channel_layouts={lay},"
    "asplit=2[e1][e2];"
    "[1:a]aresample={sr},aformat=sample_fmts=fltp:channel_layouts={lay},"
    "asplit=2[s1][s2];"
    # `amix=...:weights=1 -1` NO resta —sobre dos FLAC idénticos daba
    # RMS(dif)=2·RMS(x), es decir la SUMA (MEDIDO, `proto_graf.py`)—. La
    # negación explícita sí.
    "[e2]volume=-1[en];"
    "[s2][en]amix=inputs=2:normalize=0:duration=shortest:dropout_transition=0[d];"
    "[e1][s1][d]amerge=inputs=3,"
    "astats=measure_overall=none:measure_perchannel=RMS_level[m]"
)


def _db_a_lin(v):
    return 0.0 if v == -math.inf else 10.0 ** (v / 20.0)


def r_por_grafo(entrada, salida, sr=SR, lay="stereo"):
    """Devuelve (lista de r por canal, rms_ent, rms_sal, rc)."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", entrada, "-i", salida,
         "-filter_complex", GRAFO.format(sr=sr, lay=lay),
         "-map", "[m]", "-f", "null", "-"],
        capture_output=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL)
    err = (r.stderr or b"").decode("utf-8", "replace")
    v = []
    for l in err.splitlines():
        l = l.split("] ", 1)[-1].strip()
        if l.startswith("RMS level dB:"):
            t = l.split(":", 1)[1].strip().lower()
            v.append(-math.inf if t.startswith("-inf")
                     else (math.inf if t == "inf" else float(t)))
    if len(v) % 3:
        return None, None, None, r.returncode
    n = len(v) // 3
    ent, sal, dif = v[:n], v[n:2 * n], v[2 * n:]
    rs = []
    for k in range(n):
        Re, Rs, Rd = _db_a_lin(ent[k]), _db_a_lin(sal[k]), _db_a_lin(dif[k])
        rs.append(0.0 if Re == 0.0 or Rs == 0.0
                  else (Re * Re + Rs * Rs - Rd * Rd) / (2 * Re * Rs))
    return rs, ent, sal, r.returncode


def main() -> int:
    d = tempfile.mkdtemp(prefix="filex-a7-grafo-")
    antes = sorted(os.listdir(d))
    t0g = time.perf_counter()
    fuentes = fabricar_fuentes(d)

    filas = []
    for nombre, src in fuentes.items():
        if not os.path.exists(src):
            continue
        ent = pcm(src)
        c_LR = corr(ent[0], ent[1])
        malo_wav = os.path.join(d, "%s_malo.wav" % nombre)
        ff(["-i", src, "-af", "pan=stereo|c0=c0|c1=0*c0", "-c:a", "pcm_s16le",
            malo_wav])
        p("\n=== %s: corr(L,R)=%+.4f" % (nombre, c_LR))

        trabajos = [(et, ex, av, per, cl, org)
                    for (et, ex, av, per) in DESTINOS
                    for (cl, org) in (("buena", src), ("mala", malo_wav))]
        trabajos += [(et, ex, av, True, "buena_brutal", src)
                     for (et, ex, av) in BRUTALES]

        for et, ex, av, per, clase, origen in trabajos:
            dst = os.path.join(d, "%s_%s_%s.%s" % (nombre, clase, et, ex))
            rr = ff(["-i", origen] + av + ["-ac", "2", dst])
            if rr.returncode != 0 or not os.path.exists(dst):
                continue
            sal = pcm(dst)
            desf = alinear_fft(sal, ent)
            s, e = recortar(sal, ent, desf)
            rg, rms_e, rms_s, rc = r_por_grafo(src if clase != "mala" else src, dst)
            # OJO: el grafo compara SIEMPRE contra la ENTRADA REAL de la
            # conversión (`src`), que es lo que hará el verificador. En la clase
            # `mala` el motor recibió `malo_wav`, pero eso es un artificio del
            # arnés para fabricar el fallo: FileX vería `src` como entrada.
            fila = {
                "fuente": nombre, "clase": clase, "destino": et,
                "con_perdida": per, "corr_LR_entrada": round(c_LR, 4),
                "desfase": desf, "rc_grafo": rc,
                "rms_ent": [round(rms_db(e[0]), 2), round(rms_db(e[1]), 2)],
                "rms_sal": [None if rms_db(s[k]) == -np.inf else round(rms_db(s[k]), 2)
                            for k in (0, 1)],
                "r_ref": [round(corr(s[0], e[0]), 4), round(corr(s[1], e[1]), 4)],
                "r_grafo": [round(x, 4) for x in rg] if rg else None,
                "rms_ent_grafo": [None if x == -math.inf else round(x, 2)
                                  for x in (rms_e or [])],
                "rms_sal_grafo": [None if x == -math.inf else round(x, 2)
                                  for x in (rms_s or [])],
            }
            filas.append(fila)
            p("  %-12s %-26s desf=%4d  ref=[%+.4f %+.4f]  grafo=%s"
              % (clase, et, desf, fila["r_ref"][0], fila["r_ref"][1],
                 fila["r_grafo"]))

    # ------------------------------------------------- lo que cuesta no alinear
    pares = [(f, k) for f in filas if f["r_grafo"] and len(f["r_grafo"]) == 2
             for k in (0, 1)]
    difs = [f["r_grafo"][k] - f["r_ref"][k] for f, k in pares]
    peor_baja = min(difs) if difs else None

    AUDIBLE, SILENCIO = -60.0, -80.0

    def a7_hoy(f):
        for k in (0, 1):
            rs = f["rms_sal"][k]
            if f["rms_ent"][k] > AUDIBLE and (rs is None or rs <= SILENCIO):
                return True
        return False

    for f in filas:
        f["a7_hoy"] = a7_hoy(f)
        fuerte = max(f["rms_ent"])
        f["rel"] = [round(f["rms_ent"][k] - fuerte, 2) for k in (0, 1)]
        f["clase_real"] = ("buena" if f["clase"] == "buena" else
                           "buena_brutal" if f["clase"] == "buena_brutal" else
                           "mala_con_perdida" if f["corr_LR_entrada"] < 0.90
                           else "mala_sin_perdida")

    vivas = [f for f in filas if not f["a7_hoy"] and f["r_grafo"]]

    def dispara(f, u, rel_min, clave="r_grafo"):
        for k in (0, 1):
            if f["rms_ent"][k] <= AUDIBLE or f["rel"][k] < rel_min:
                continue
            if f[clave][k] < u:
                return True
        return False

    rejilla = []
    for clave in ("r_grafo", "r_ref"):
        for u in (0.008, 0.02, 0.05, 0.10, 0.13, 0.20, 0.30):
            for rel_min in (-100, -40, -30, -20, -15, -12, -9, -6):
                a = sum(1 for f in vivas if f["clase_real"] == "mala_con_perdida"
                        and dispara(f, u, rel_min, clave))
                fp = sum(1 for f in vivas
                         if f["clase_real"] in ("buena", "buena_brutal")
                         and dispara(f, u, rel_min, clave))
                fpb = sum(1 for f in vivas if f["clase_real"] == "buena"
                          and dispara(f, u, rel_min, clave))
                rejilla.append({"metrica": clave, "umbral": u,
                                "suelo_rel_dB": rel_min, "atrapa": a,
                                "de": sum(1 for f in vivas
                                          if f["clase_real"] == "mala_con_perdida"),
                                "fp_total": fp, "fp_solo_buenas": fpb})

    res = {"cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
           "n_filas": len(filas), "n_vivas": len(vivas),
           "ms_total": round((time.perf_counter() - t0g) * 1000, 1),
           "censo_antes": antes, "censo_despues": len(os.listdir(d)),
           "acuerdo_grafo_vs_ref": {
               "n_pares": len(pares),
               "peor_caida": round(peor_baja, 4) if difs else None,
               "mediana": round(float(np.median(difs)), 4) if difs else None,
               "p10": round(float(np.percentile(difs, 10)), 4) if difs else None},
           "rejilla": rejilla, "filas": filas}

    with open(os.path.join(AQUI, "a7_grafo.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)

    p("\n=== lo que cuesta NO alinear (r_grafo - r_ref) ===")
    p("  %d pares; mediana %s; p10 %s; peor caída %s"
      % (len(pares), res["acuerdo_grafo_vs_ref"]["mediana"],
         res["acuerdo_grafo_vs_ref"]["p10"], res["acuerdo_grafo_vs_ref"]["peor_caida"]))
    for clave in ("r_grafo", "r_ref"):
        p("\n=== rejilla con %s — celdas que HOY se escapan ===" % clave)
        p("  %-8s %s" % ("corr <", "".join(
            "%11s" % ("rel>=%d" % r) for r in (-100, -40, -30, -20, -15, -12, -9, -6))))
        for u in (0.008, 0.02, 0.05, 0.10, 0.13, 0.20, 0.30):
            fila = []
            for rel_min in (-100, -40, -30, -20, -15, -12, -9, -6):
                x = [q for q in rejilla if q["metrica"] == clave
                     and q["umbral"] == u and q["suelo_rel_dB"] == rel_min][0]
                fila.append("%2d/%-2d FP%2d" % (x["atrapa"], x["de"], x["fp_total"]))
            p("  %-8.3f %s" % (u, "".join("%11s" % y for y in fila)))

    with open(os.path.join(AQUI, "a7_grafo.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(AQUI, "logs"), exist_ok=True)
    with open(os.path.join(AQUI, "logs", "a7_grafo.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    print("\ndesechable al terminar:", len(os.listdir(d)), "entradas")
    shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
