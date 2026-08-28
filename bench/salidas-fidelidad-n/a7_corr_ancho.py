# -*- coding: utf-8 -*-
"""N18 — la señal de N16, medida FUERA de sus condiciones.

`bench/ventana-antes-del-move.md` §8bis midió `corr(Rsal, Rent)` sobre **un solo
códec** (`libopus`), **cinco fuentes** y **nueve tasas**, y dejó escrito en
§8bis.6 lo que no había medido: otros códecs, y el destino sin pérdida.
`a7_repro_n.py` reproduce esa medida al centésimo (trampa 58). Esto la EXTIENDE,
que es el único modo de comprobar un saldo heredado (trampa 69: *el modo de
comprobarlo no es repetir sus filas, es añadir filas que no tenía*).

Tres ejes nuevos, y cada uno responde a una trampa concreta:

* **Trampa 53 — la cobertura de una regla de fidelidad depende del DESTINO.**
  El mismo fallo va aquí a `opus`, `mp3`, `aac` (con pérdida) **y a `flac` y
  `wav`** (sin pérdida). Si solo separase en uno, sería una regla del destino.
* **Trampa 50 — varía la entrada.** A las cinco fuentes de N16 se añaden tres
  que su corpus no tenía: ruido descorrelacionado (lo que peor lleva un códec),
  estéreo de fase invertida (`corr(L,R) < 0`) y un canal derecho MUY flojo.
* **La tercera clase de falsos positivos: la conversión LEGÍTIMA pero brutal.**
  Un `lowpass=500`, un `highpass=3000`, un remuestreo a 8 kHz y un `-q:a 9`
  destrozan la forma de onda **sin perder ningún canal**. Son las que tienen
  que salir ILESAS, y son las que ningún corpus anterior tenía a la vez que la
  correlación.

Y una cuarta medida, que es la que decide la pregunta de coste: **¿la RMS por
canal sacada del PCM reproduce la de `astats`?** Si no lo hace, la señal no
puede SUSTITUIR a los dos `astats` y solo puede sumarse.

No usa la GPU. Determinista: decodificar dos veces el mismo fichero da el mismo
array, y todas las cifras salen de aritmética sobre él.
"""
from __future__ import annotations

import json
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
SR = 48000                       # Opus fuerza 48 kHz (trampa 3)
DUR = 8.0
DESFASE_MAX = int(0.020 * SR)    # ±20 ms, el mismo que N16

log: list[str] = []


def p(msg: str) -> None:
    print(msg)
    log.append(msg)


def ff(argv, **kw):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + argv,
                          capture_output=True, timeout=TIMEOUT,
                          stdin=subprocess.DEVNULL, **kw)


def pcm(ruta: str, sr: int = SR, ac: int = 2) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", ruta,
                        "-vn", "-sn", "-map", "0:a:0",
                        "-f", "f32le", "-acodec", "pcm_f32le",
                        "-ac", str(ac), "-ar", str(sr), "-"],
                       capture_output=True, timeout=TIMEOUT,
                       stdin=subprocess.DEVNULL)
    a = np.frombuffer(r.stdout, dtype="<f4")
    n = len(a) // ac
    return a[:n * ac].reshape(n, ac).T.astype(np.float64)


def rms_db(x: np.ndarray) -> float:
    v = float(np.sqrt(np.mean(x * x))) if x.size else 0.0
    return -np.inf if v <= 0 else 20.0 * np.log10(v)


def corr(a: np.ndarray, b: np.ndarray) -> float:
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    da, db = float(np.sqrt((a * a).sum())), float(np.sqrt((b * b).sum()))
    if da == 0.0 or db == 0.0:
        return 0.0
    return float((a * b).sum() / (da * db))


def alinear_fft(sal: np.ndarray, ent: np.ndarray) -> int:
    """El de N16, literal. La FFT y no el barrido: trampa 62."""
    n = min(sal.shape[1], ent.shape[1])
    a = sal[0][:n] - sal[0][:n].mean()
    b = ent[0][:n] - ent[0][:n].mean()
    m = 1 << int(np.ceil(np.log2(n + 2 * DESFASE_MAX + 1)))
    r = np.fft.irfft(np.fft.rfft(a, m) * np.conj(np.fft.rfft(b, m)), m)
    cand = np.concatenate([r[:DESFASE_MAX + 1], r[-DESFASE_MAX:]])
    i = int(np.argmax(cand))
    return i if i <= DESFASE_MAX else i - (2 * DESFASE_MAX + 1)


def recortar(sal, ent, d):
    if d >= 0:
        sal = sal[:, d:]
    else:
        ent = ent[:, -d:]
    n = min(sal.shape[1], ent.shape[1])
    return sal[:, :n], ent[:, :n]


def astats_rms(ruta: str):
    """La sonda que A7 usa HOY, para poder comparar las dos en la misma tanda
    (§3 de CLAUDE.md: las relativas dentro de una tanda sí son comparables)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", ruta,
                        "-map", "0:a:0", "-vn", "-sn",
                        "-af", "astats=measure_overall=none:"
                               "measure_perchannel=Peak_level+RMS_level",
                        "-f", "null", "-"],
                       capture_output=True, timeout=TIMEOUT,
                       stdin=subprocess.DEVNULL)
    err = (r.stderr or b"").decode("utf-8", "replace")
    out, actual = [], None
    for l in err.splitlines():
        l = l.split("] ", 1)[-1].strip()
        if l.startswith("Channel:"):
            actual = None
        elif l.startswith("RMS level dB:"):
            t = l.split(":", 1)[1].strip().lower()
            if t in ("-inf", "inf"):
                actual = float("-inf") if t.startswith("-") else float("inf")
            else:
                try:
                    actual = float(t)
                except ValueError:
                    actual = None
            out.append(actual)
    return out


# ------------------------------------------------------------------ fuentes
def fabricar_fuentes(d: str) -> dict:
    jfk = os.path.join(CORPUS, "habla_jfk.flac")
    tip = os.path.join(CORPUS, "tipico.flac")
    largo = os.path.join(CORPUS, "habla_largo.flac")
    f = {}

    # --- las CINCO de N16, literales (control positivo: si estas cinco no dan
    #     lo mismo que en `a7_repro_n.json`, el arnes cambio y no el mundo)
    f["distintos"] = os.path.join(d, "f1.wav")
    ff(["-i", jfk, "-f", "lavfi",
        "-i", "sine=frequency=440:sample_rate=%d" % SR, "-filter_complex",
        "[0:a]pan=mono|c0=c0,atrim=0:%.1f[l];[1:a]atrim=0:%.1f,volume=0.3[r];"
        "[l][r]join=inputs=2:channel_layout=stereo" % (DUR, DUR),
        "-t", str(DUR), "-ar", str(SR), "-c:a", "pcm_s16le", f["distintos"]])

    f["reales"] = os.path.join(d, "f2.wav")
    ff(["-i", jfk, "-t", str(DUR), "-ar", str(SR), "-ac", "2",
        "-c:a", "pcm_s16le", f["reales"]])

    f["identicos"] = os.path.join(d, "f3.wav")
    ff(["-i", tip, "-af", "pan=stereo|c0=c0|c1=c0", "-t", str(DUR),
        "-ar", str(SR), "-c:a", "pcm_s16le", f["identicos"]])

    f["desfasados"] = os.path.join(d, "f4.wav")
    ff(["-i", jfk, "-filter_complex",
        "[0:a]pan=mono|c0=c0,atrim=0:%.1f,asplit=2[a][b];"
        "[b]adelay=17|17,lowpass=f=3000[r];[a][r]join=inputs=2:"
        "channel_layout=stereo" % DUR,
        "-t", str(DUR), "-ar", str(SR), "-c:a", "pcm_s16le", f["desfasados"]])

    f["dos_voces"] = os.path.join(d, "f5.wav")
    ff(["-i", jfk, "-i", largo, "-filter_complex",
        "[0:a]pan=mono|c0=c0,atrim=0:%.1f[l];"
        "[1:a]pan=mono|c0=c0,atrim=60:%.1f,asetpts=PTS-STARTPTS[r];"
        "[l][r]join=inputs=2:channel_layout=stereo" % (DUR, 60 + DUR),
        "-t", str(DUR), "-ar", str(SR), "-c:a", "pcm_s16le", f["dos_voces"]])

    # --- las TRES nuevas (trampa 50: variar la entrada, otra vez)
    # F6 — RUIDO descorrelacionado en los dos canales. Es lo que peor lleva un
    # códec con pérdida: si algo va a hundir la correlación de una conversión
    # BUENA, es esto.
    f["ruido"] = os.path.join(d, "f6.wav")
    ff(["-f", "lavfi", "-i", "anoisesrc=color=white:seed=11:sample_rate=%d" % SR,
        "-f", "lavfi", "-i", "anoisesrc=color=pink:seed=22:sample_rate=%d" % SR,
        "-filter_complex",
        "[0:a]atrim=0:%.1f,volume=0.25[l];[1:a]atrim=0:%.1f,volume=0.25[r];"
        "[l][r]join=inputs=2:channel_layout=stereo" % (DUR, DUR),
        "-t", str(DUR), "-ar", str(SR), "-c:a", "pcm_s16le", f["ruido"]])

    # F7 — FASE INVERTIDA: el derecho es el izquierdo cambiado de signo. Es el
    # estéreo «ancho» de estudio, `corr(L,R) = −1`, y es el caso en que un
    # códec que colapse a mono deja el canal en NADA aunque nadie lo silenciara.
    f["fase_inv"] = os.path.join(d, "f7.wav")
    ff(["-i", jfk, "-af", "pan=stereo|c0=c0|c1=-1*c0", "-t", str(DUR),
        "-ar", str(SR), "-c:a", "pcm_s16le", f["fase_inv"]])

    # F8 — el canal derecho MUY flojo pero audible (−40 dB respecto al otro).
    # Es el vecino legítimo del canal perdido, y el que decide si el umbral se
    # come una conversión buena.
    f["flojo"] = os.path.join(d, "f8.wav")
    ff(["-i", jfk, "-i", largo, "-filter_complex",
        "[0:a]pan=mono|c0=c0,atrim=0:%.1f[l];"
        "[1:a]pan=mono|c0=c0,atrim=60:%.1f,asetpts=PTS-STARTPTS,volume=0.01[r];"
        "[l][r]join=inputs=2:channel_layout=stereo" % (DUR, 60 + DUR),
        "-t", str(DUR), "-ar", str(SR), "-c:a", "pcm_s16le", f["flojo"]])
    return f


# ------------------------------------------------------------------ destinos
# (etiqueta, extension, argv de codificacion, con_perdida)
DESTINOS = [
    ("opus_6k", "opus", ["-c:a", "libopus", "-b:a", "6k"], True),
    ("opus_8k", "opus", ["-c:a", "libopus", "-b:a", "8k"], True),
    ("opus_16k", "opus", ["-c:a", "libopus", "-b:a", "16k"], True),
    ("opus_32k", "opus", ["-c:a", "libopus", "-b:a", "32k"], True),
    ("opus_96k", "opus", ["-c:a", "libopus", "-b:a", "96k"], True),
    ("mp3_32k", "mp3", ["-c:a", "libmp3lame", "-b:a", "32k"], True),
    ("mp3_64k", "mp3", ["-c:a", "libmp3lame", "-b:a", "64k"], True),
    ("mp3_192k", "mp3", ["-c:a", "libmp3lame", "-b:a", "192k"], True),
    ("mp3_q9", "mp3", ["-c:a", "libmp3lame", "-q:a", "9"], True),
    ("aac_32k", "m4a", ["-c:a", "aac", "-b:a", "32k"], True),
    ("aac_64k", "m4a", ["-c:a", "aac", "-b:a", "64k"], True),
    ("aac_192k", "m4a", ["-c:a", "aac", "-b:a", "192k"], True),
    # Trampa 53: el MISMO fallo contra un destino SIN pérdida.
    ("flac", "flac", ["-c:a", "flac"], False),
    ("wav", "wav", ["-c:a", "pcm_s16le"], False),
]

# Las LEGÍTIMAS BRUTALES: destrozan la onda y no pierden ningún canal. Tienen
# que salir ilesas, y son la clase que fija el techo del umbral.
BRUTALES = [
    ("brutal_lowpass500", "mp3", ["-af", "lowpass=f=500", "-c:a", "libmp3lame",
                                  "-b:a", "64k"]),
    ("brutal_highpass3k", "mp3", ["-af", "highpass=f=3000", "-c:a", "libmp3lame",
                                  "-b:a", "64k"]),
    ("brutal_8khz", "opus", ["-ar", "8000", "-c:a", "libopus", "-b:a", "12k"]),
    ("brutal_aformat_u8", "wav", ["-c:a", "pcm_u8"]),
    ("brutal_opus6k_mono_a_estereo", "opus",
     ["-af", "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1",
      "-c:a", "libopus", "-b:a", "6k"]),
]


def main() -> int:
    d = tempfile.mkdtemp(prefix="filex-a7-ancho-")
    antes = sorted(os.listdir(d))
    t_ini = time.perf_counter()
    fuentes = fabricar_fuentes(d)

    filas, acuerdo = [], []
    for nombre, src in fuentes.items():
        if not os.path.exists(src):
            p("FUENTE NO FABRICADA: %s" % nombre)
            continue
        ent = pcm(src)
        c_LR = corr(ent[0], ent[1])
        p("\n=== %s: corr(L,R)=%+.4f  rms %.2f / %.2f dBFS"
          % (nombre, c_LR, rms_db(ent[0]), rms_db(ent[1])))

        malo_wav = os.path.join(d, "%s_malo.wav" % nombre)
        ff(["-i", src, "-af", "pan=stereo|c0=c0|c1=0*c0", "-c:a", "pcm_s16le",
            malo_wav])

        trabajos = [(et, ex, av, per, cl, org)
                    for (et, ex, av, per) in DESTINOS
                    for (cl, org) in (("buena", src), ("mala", malo_wav))]
        trabajos += [(et, ex, av, True, "buena_brutal", src)
                     for (et, ex, av) in BRUTALES]

        for et, ex, av, per, clase, origen in trabajos:
            dst = os.path.join(d, "%s_%s_%s.%s" % (nombre, clase, et, ex))
            r = ff(["-i", origen] + av + ["-ac", "2", dst])
            if r.returncode != 0 or not os.path.exists(dst):
                p("  %-10s %-12s %-26s rc=%d  SALTADA" % (nombre, clase, et,
                                                          r.returncode))
                continue
            sal = pcm(dst)
            desf = alinear_fft(sal, ent)
            s, e = recortar(sal, ent, desf)
            rms_pcm_sal = [rms_db(s[0]), rms_db(s[1])]
            fila = {
                "fuente": nombre, "clase": clase, "destino": et,
                "con_perdida": per, "rc": r.returncode,
                "corr_LR_entrada": round(c_LR, 4),
                "desfase": desf,
                "rms_ent": [round(rms_db(e[0]), 2), round(rms_db(e[1]), 2)],
                "rms_sal": [None if x == -np.inf else round(x, 2)
                            for x in rms_pcm_sal],
                "corr_c0": round(corr(s[0], e[0]), 4),
                "corr_c1": round(corr(s[1], e[1]), 4),
            }
            # A7 tal y como esta HOY, con la sonda de HOY
            fila["A7_hoy"] = bool(rms_db(e[1]) > -60.0 and rms_pcm_sal[1] <= -80.0)
            filas.append(fila)

            # --- el acuerdo PCM / astats, sobre el MISMO fichero
            ast = astats_rms(dst)
            if len(ast) == 2:
                dif = []
                for k in (0, 1):
                    a, b = ast[k], rms_pcm_sal[k]
                    if a is None:
                        dif.append(None)
                    elif a == -np.inf and b == -np.inf:
                        dif.append(0.0)
                    elif a == -np.inf or b == -np.inf:
                        dif.append(None)   # uno dice silencio y el otro no
                    else:
                        dif.append(round(b - a, 4))
                acuerdo.append({"fichero": os.path.basename(dst),
                                "astats": [None if x == -np.inf else x for x in ast],
                                "pcm": fila["rms_sal"], "dif_dB": dif})
            p("  %-10s %-12s %-26s corr c0=%+7.4f c1=%+7.4f  A7hoy=%-5s"
              % (nombre, clase, et, fila["corr_c0"], fila["corr_c1"],
                 fila["A7_hoy"]))

    # ------------------------------------------------------- clasificación
    UMBRAL_PERDIDA = 0.90

    def clase_real(f):
        if f["clase"] == "buena":
            return "buena"
        if f["clase"] == "buena_brutal":
            return "buena_brutal"
        return ("mala_con_perdida" if f["corr_LR_entrada"] < UMBRAL_PERDIDA
                else "mala_sin_perdida")

    for f in filas:
        f["clase_real"] = clase_real(f)

    # La regla candidata mira el canal cuya ENTRADA es audible; el fallo
    # fabricado esta siempre en el canal 1, pero la regla no lo sabe: se
    # evalua el MINIMO de las correlaciones de los canales audibles, que es
    # lo que hara el codigo.
    for f in filas:
        cs = []
        for k, clave in ((0, "corr_c0"), (1, "corr_c1")):
            if f["rms_ent"][k] > -60.0:
                cs.append(f[clave])
        f["corr_min_audible"] = round(min(cs), 4) if cs else None

    tabla = []
    for u in (0.002, 0.005, 0.008, 0.01, 0.02, 0.05, 0.08, 0.10, 0.13, 0.15,
              0.20, 0.30, 0.50):
        def cuenta(cl):
            return sum(1 for f in filas if f["clase_real"] == cl
                       and f["corr_min_audible"] is not None
                       and f["corr_min_audible"] < u)
        tabla.append({
            "umbral": u,
            "atrapa": cuenta("mala_con_perdida"),
            "de": sum(1 for f in filas if f["clase_real"] == "mala_con_perdida"),
            "fp_buenas": cuenta("buena"),
            "de_buenas": sum(1 for f in filas if f["clase_real"] == "buena"),
            "fp_brutales": cuenta("buena_brutal"),
            "de_brutales": sum(1 for f in filas if f["clase_real"] == "buena_brutal"),
            "toca_sin_perdida": cuenta("mala_sin_perdida"),
        })

    # Por DESTINO: la trampa 53 exige mirar si separa en los dos regimenes.
    por_destino = []
    for et, ex, av, per in DESTINOS:
        sel = [f for f in filas if f["destino"] == et]
        m = [f["corr_min_audible"] for f in sel
             if f["clase_real"] == "mala_con_perdida"]
        b = [f["corr_min_audible"] for f in sel if f["clase_real"] == "buena"]
        if not m or not b:
            continue
        por_destino.append({"destino": et, "con_perdida": per,
                            "n_malas": len(m), "n_buenas": len(b),
                            "peor_mala": round(max(m), 4),
                            "mejor_buena": round(min(b), 4),
                            "hueco": round(min(b) - max(m), 4),
                            "A7_hoy_atrapa": sum(1 for f in sel
                                                 if f["clase_real"] == "mala_con_perdida"
                                                 and f["A7_hoy"])})

    difs = [x for a in acuerdo for x in a["dif_dB"] if x is not None]
    discordes = [a for a in acuerdo if any(x is None for x in a["dif_dB"])]
    res = {"cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
           "sr": SR, "dur_s": DUR,
           "n_filas": len(filas),
           "ms_total": round((time.perf_counter() - t_ini) * 1000, 1),
           "censo_antes": antes, "censo_despues": len(os.listdir(d)),
           "tabla_umbral": tabla, "por_destino": por_destino,
           "acuerdo_pcm_astats": {
               "n_canales_comparados": len(difs),
               "max_abs_dB": round(max(abs(x) for x in difs), 4) if difs else None,
               "mediana_dB": round(float(np.median(difs)), 4) if difs else None,
               "discordes": [a["fichero"] for a in discordes],
               "detalle": acuerdo},
           "filas": filas}

    p("\n=== corr minima de canal audible — que atrapa y que rompe ===")
    for t in tabla:
        p("  < %.3f  atrapa %2d/%2d  FP buenas %2d/%2d  FP brutales %2d/%2d  "
          "toca %d malas-sin-perdida"
          % (t["umbral"], t["atrapa"], t["de"], t["fp_buenas"], t["de_buenas"],
             t["fp_brutales"], t["de_brutales"], t["toca_sin_perdida"]))
    p("\n=== por DESTINO (trampa 53) ===")
    for t in por_destino:
        p("  %-26s %-11s peor mala %+7.4f  mejor buena %+7.4f  hueco %+7.4f  "
          "A7 hoy %d/%d"
          % (t["destino"], "con perdida" if t["con_perdida"] else "SIN perdida",
             t["peor_mala"], t["mejor_buena"], t["hueco"],
             t["A7_hoy_atrapa"], t["n_malas"]))
    p("\n=== acuerdo RMS  PCM  vs  astats ===")
    p("  %d canales comparados, |dif| max %s dB, mediana %s dB, %d discordes: %s"
      % (res["acuerdo_pcm_astats"]["n_canales_comparados"],
         res["acuerdo_pcm_astats"]["max_abs_dB"],
         res["acuerdo_pcm_astats"]["mediana_dB"],
         len(discordes), [a["fichero"] for a in discordes][:6]))

    with open(os.path.join(AQUI, "a7_corr_ancho.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(AQUI, "logs"), exist_ok=True)
    with open(os.path.join(AQUI, "logs", "a7_corr_ancho.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    print("\ndesechable al terminar:", len(os.listdir(d)), "entradas")
    shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
