"""Lo que costaría la señal de N16, **medida aislada** (trampa 36).

Tres trozos, cronometrados por separado sobre 8,0 s de estéreo a 48 kHz:

  1. decodificar la ENTRADA a PCM (`ffmpeg -f f32le`)
  2. decodificar la SALIDA
  3. alinear (±20 ms, paso 8) + las tres correlaciones

El punto de comparación es lo que A7 cuesta hoy: **dos `ffmpeg -af astats`**,
que también son dos pasadas completas por el fichero. Se mide igual, en la misma
tanda, para que la cifra que se publique sea una razón y no un absoluto.
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from a7_bitrate_bajo import SR, DUR, alinear, corr, ff, pcm, recortar  # noqa: E402

CORPUS = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "corpus", "audio")
N = 15


def testigo_deriva(vueltas: int = 400_000) -> float:
    t0 = time.perf_counter()
    x = 0
    for i in range(vueltas):
        x += i
    return (time.perf_counter() - t0) * 1000


def testigo_proceso(tope: float = 20.0) -> float:
    t0 = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=tope)
    except Exception:
        return tope * 1000
    return (time.perf_counter() - t0) * 1000


def astats(ruta: str):
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", ruta,
         "-af", "astats=metadata=1:reset=0", "-f", "null", "-"],
        capture_output=True, timeout=180, stdin=subprocess.DEVNULL)


def mediana(f, n=N):
    v = []
    for _ in range(n):
        t0 = time.perf_counter()
        f()
        v.append((time.perf_counter() - t0) * 1000)
    v.sort()
    return {"mediana_ms": round(statistics.median(v), 2),
            "p90_ms": round(v[int(n * 0.9)], 2),
            "min_ms": round(v[0], 2), "max_ms": round(v[-1], 2), "n": n}


def main() -> int:
    d = tempfile.mkdtemp(prefix="filex-a7-coste-")
    antes = sorted(os.listdir(d))
    ent = os.path.join(d, "ent.wav")
    ff(["-i", os.path.join(CORPUS, "habla_jfk.flac"), "-t", str(DUR),
        "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", ent])
    sal = os.path.join(d, "sal.opus")
    ff(["-i", ent, "-c:a", "libopus", "-b:a", "32k", "-ac", "2", sal])

    d0, pr0 = testigo_deriva(), testigo_proceso()
    # Calentar (trampa 7).
    for _ in range(3):
        pcm(ent), astats(ent)

    a = pcm(ent)
    b = pcm(sal)

    filas = {
        "1 decodificar la ENTRADA a PCM": mediana(lambda: pcm(ent)),
        "2 decodificar la SALIDA a PCM": mediana(lambda: pcm(sal)),
        "3 alinear + 3 correlaciones": mediana(lambda: _senal(b, a)),
        "3b solo las 3 correlaciones (sin alinear)": mediana(
            lambda: (corr(b[1], a[1]), corr(b[1], a[0]), corr(b[0], b[1]))),
        "3c alinear por FFT + 3 correlaciones": mediana(lambda: _senal_fft(b, a)),
        "C1 astats de la ENTRADA (lo que A7 hace hoy)": mediana(lambda: astats(ent)),
        "C2 astats de la SALIDA (lo que A7 hace hoy)": mediana(lambda: astats(sal)),
    }
    d1, pr1 = testigo_deriva(), testigo_proceso()
    # Control positivo: la vía rápida tiene que dar el MISMO desfase que la
    # lenta, o no es la misma medida (§3 de CLAUDE.md, «control positivo»).
    desf_lento, desf_fft = alinear(b, a), alinear_fft(b, a)
    senal_lenta, senal_fft = _senal(b, a), _senal_fft(b, a)

    res = {"cuando": time.strftime("%Y-%m-%d %H:%M:%S"), "dur_s": DUR, "sr": SR,
           "censo_antes": antes, "censo_despues": sorted(os.listdir(d)),
           "testigos": {"deriva": round(d1 / d0, 2) if d0 else None,
                        "proceso_ini_ms": round(pr0, 1),
                        "proceso_fin_ms": round(pr1, 1),
                        "limpia": bool(d0 and 0.5 < d1 / d0 < 2.0
                                       and max(pr0, pr1) < 2000)},
           "control_positivo": {
               "desfase_fuerza_bruta": int(desf_lento),
               "desfase_fft": int(desf_fft),
               "misma_senal": [round(x, 4) for x in senal_lenta]
                              == [round(x, 4) for x in senal_fft],
               "senal_fuerza_bruta": [round(x, 4) for x in senal_lenta],
               "senal_fft": [round(x, 4) for x in senal_fft]},
           "filas": filas}
    with open(os.path.join(AQUI, "a7_coste_senal.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for k, v in filas.items():
        print("%-46s %8.2f ms  p90 %8.2f" % (k, v["mediana_ms"], v["p90_ms"]))
    print("testigos:", res["testigos"])
    shutil.rmtree(d, ignore_errors=True)
    return 0


def _senal(sal_pcm: np.ndarray, ent_pcm: np.ndarray):
    desf = alinear(sal_pcm, ent_pcm)
    s, e = recortar(sal_pcm, ent_pcm, desf)
    return corr(s[1], e[1]), corr(s[1], e[0]), corr(s[0], s[1])


def alinear_fft(sal: np.ndarray, ent: np.ndarray) -> int:
    """El mismo desfase, por correlación cruzada con FFT.

    El barrido a fuerza bruta del arnés (240 correlaciones sobre 384 000
    muestras) es correcto y **cuesta 1 800,78 ms**, que descalificaría la señal
    ella sola. Esto mide lo que costaría la implementación que se propondría de
    verdad, no la del arnés. Se comprueba que da el MISMO desfase: una versión
    rápida que respondiera otra cosa no serviría de nada.
    """
    n = min(sal.shape[1], ent.shape[1])
    a = sal[0][:n] - sal[0][:n].mean()
    b = ent[0][:n] - ent[0][:n].mean()
    m = 1 << int(np.ceil(np.log2(n + DESFASE_MAX_LOCAL * 2 + 1)))
    r = np.fft.irfft(np.fft.rfft(a, m) * np.conj(np.fft.rfft(b, m)), m)
    cand = np.concatenate([r[:DESFASE_MAX_LOCAL + 1],
                           r[-DESFASE_MAX_LOCAL:]])
    i = int(np.argmax(cand))
    return i if i <= DESFASE_MAX_LOCAL else i - (2 * DESFASE_MAX_LOCAL + 1)


DESFASE_MAX_LOCAL = int(0.020 * SR)


def _senal_fft(sal_pcm: np.ndarray, ent_pcm: np.ndarray):
    desf = alinear_fft(sal_pcm, ent_pcm)
    s, e = recortar(sal_pcm, ent_pcm, desf)
    return corr(s[1], e[1]), corr(s[1], e[0]), corr(s[0], s[1])


if __name__ == "__main__":
    sys.exit(main())
