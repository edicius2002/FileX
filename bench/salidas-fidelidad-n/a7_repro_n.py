"""N18/repro — COPIA LITERAL del arnes de N16 (bench/salidas-ventana/a7_bitrate_bajo.py),
cambiados SOLO los nombres de los ficheros de salida. Trampa 58: reproducir la
medida ajena antes de aplicarla.

N16 original — ¿hay alguna señal que separe el canal perdido a bitrates bajos?

`bench/contrato-familia-resvg.md` §2.5 dejó medido el punto ciego de A7: **por
debajo de 48 kb/s Opus rellena el canal mudo con una copia del otro**, así que
la salida ya no tiene un canal silenciado —tiene dos con señal— y la regla, que
mira RMS por canal, no puede opinar. A 32 kb/s falla por **1,03 dB**, y mover el
umbral por 1 dB es ajustar el suelo a una celda (trampa 51).

El pendiente 2 del mismo informe propone *«comparar la CORRELACIÓN entre canales
de entrada y salida. Sin medir.»* Esto lo mide, **sin tocar
`filex/verificador.py`**, que es de otro reparto.

## La hipótesis, escrita antes de medirla

Si el canal derecho se pierde y Opus lo rellena copiando el izquierdo, entonces
**el derecho de la SALIDA se parece al IZQUIERDO de la ENTRADA, no al derecho**.
La señal sería:

    ventaja_cruzada = corr(Rsal, Lent) - corr(Rsal, Rent)

alta cuando el canal se ha perdido, y ~0 o negativa cuando se ha conservado.

## Los dos riesgos declarados antes de empezar

* **Trampa 50 — varía la entrada.** Con una fuente cuyos canales sean IGUALES,
  `corr(Rsal, Lent) == corr(Rsal, Rent)` por construcción y la señal no puede
  existir. Se miden **cinco** fuentes: canales muy distintos (voz / tono), los
  dos canales de una grabación real, mono duplicado, la misma voz retrasada y
  filtrada, y dos voces distintas. **Cuatro de las cinco hay que fabricarlas:
  el único fichero estéreo del corpus tiene `corr(L,R) = 0,9997`.**
* **Trampa 51 — tabula qué atrapa y qué rompe en cada umbral candidato**, y
  pregunta primero si el hueco existe, no dónde está.
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
RAIZ = os.path.dirname(os.path.dirname(AQUI))
CORPUS = os.path.join(RAIZ, "corpus", "audio")
TIMEOUT = 180
SR = 48000                      # Opus fuerza 48 kHz (trampa 3)
DUR = 8.0
TASAS = ("6k", "8k", "12k", "16k", "24k", "32k", "48k", "64k", "96k")
DESFASE_MAX = int(0.020 * SR)   # ±20 ms de búsqueda de alineamiento

log: list[str] = []


def p(msg: str) -> None:
    print(msg)
    log.append(msg)


def ff(argv, **kw):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + argv,
                          capture_output=True, timeout=TIMEOUT,
                          stdin=subprocess.DEVNULL, **kw)


def pcm(ruta: str) -> np.ndarray:
    """`(2, n)` en float32 a 48 kHz. Decodificar dos veces el mismo fichero da
    el mismo array: no hay aleatoriedad que declarar."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", ruta,
                        "-f", "f32le", "-acodec", "pcm_f32le",
                        "-ac", "2", "-ar", str(SR), "-"],
                       capture_output=True, timeout=TIMEOUT,
                       stdin=subprocess.DEVNULL)
    a = np.frombuffer(r.stdout, dtype="<f4")
    n = len(a) // 2
    return a[:n * 2].reshape(n, 2).T.astype(np.float64)


def rms_db(x: np.ndarray) -> float:
    v = float(np.sqrt(np.mean(x * x))) if x.size else 0.0
    return -np.inf if v <= 0 else 20.0 * np.log10(v)


def corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson. Devuelve 0,0 si alguno es constante — un canal mudo no
    correlaciona con nada, y decir «0» es más honesto que un `nan`."""
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    da, db = float(np.sqrt((a * a).sum())), float(np.sqrt((b * b).sum()))
    if da == 0.0 or db == 0.0:
        return 0.0
    return float((a * b).sum() / (da * db))


def alinear(sal: np.ndarray, ent: np.ndarray) -> int:
    """Desfase (en muestras) que maximiza `corr(Lsal, Lent)` en ±20 ms.

    **Hace falta y no es cosmético:** Opus mete un `pre-skip` y la salida no
    empieza en la misma muestra. Sin alinear, una correlación baja podría
    significar «el canal cambió» o «el canal está desplazado 6,5 ms», que son
    dos cosas distintas con la misma pinta (trampa 25).
    """
    mejor, mejor_d = -2.0, 0
    for d in range(-DESFASE_MAX, DESFASE_MAX + 1, 8):
        if d >= 0:
            c = corr(sal[0][d:], ent[0])
        else:
            c = corr(sal[0], ent[0][-d:])
        if c > mejor:
            mejor, mejor_d = c, d
    return mejor_d


def alinear_fft(sal: np.ndarray, ent: np.ndarray) -> int:
    """El mismo desfase, por correlación cruzada con FFT — y es el que se usa.

    **Y no es solo por velocidad: el barrido a fuerza bruta con paso 8 se salta
    el óptimo.** Sobre el mismo par, `alinear` devuelve 0 y `alinear_fft`
    devuelve −2, y con ese desfase la correlación sube de **0,9415 a 0,9718**
    (`a7_coste_senal.json`, control positivo). Un arnés que redondea el
    alineamiento subestima todas las correlaciones buenas, que es justo el lado
    del que depende el hueco. El barrido lento se conserva **como control**.
    """
    n = min(sal.shape[1], ent.shape[1])
    a = sal[0][:n] - sal[0][:n].mean()
    b = ent[0][:n] - ent[0][:n].mean()
    m = 1 << int(np.ceil(np.log2(n + 2 * DESFASE_MAX + 1)))
    r = np.fft.irfft(np.fft.rfft(a, m) * np.conj(np.fft.rfft(b, m)), m)
    cand = np.concatenate([r[:DESFASE_MAX + 1], r[-DESFASE_MAX:]])
    i = int(np.argmax(cand))
    return i if i <= DESFASE_MAX else i - (2 * DESFASE_MAX + 1)


def recortar(sal: np.ndarray, ent: np.ndarray, d: int):
    if d >= 0:
        sal = sal[:, d:]
    else:
        ent = ent[:, -d:]
    n = min(sal.shape[1], ent.shape[1])
    return sal[:, :n], ent[:, :n]


# ---------------------------------------------------------------- fuentes
def fabricar_fuentes(d: str) -> dict:
    jfk = os.path.join(CORPUS, "habla_jfk.flac")
    tip = os.path.join(CORPUS, "tipico.flac")
    f = {}

    # F1 — canales MUY distintos: habla a la izquierda, tono a la derecha.
    f["distintos"] = os.path.join(d, "f1_distintos.wav")
    ff(["-i", jfk, "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=%d" % SR,
        "-filter_complex",
        "[0:a]pan=mono|c0=c0,atrim=0:%.1f[l];[1:a]atrim=0:%.1f,volume=0.3[r];"
        "[l][r]join=inputs=2:channel_layout=stereo" % (DUR, DUR),
        "-t", str(DUR), "-ar", str(SR), "-c:a", "pcm_s16le", f["distintos"]])

    # F2 — canales desiguales REALES: los dos de una grabación de verdad.
    f["reales"] = os.path.join(d, "f2_reales.wav")
    ff(["-i", jfk, "-t", str(DUR), "-ar", str(SR), "-ac", "2",
        "-c:a", "pcm_s16le", f["reales"]])

    # F3 — canales IDÉNTICOS: mono duplicado. El control negativo de la
    # trampa 50: aquí la señal NO PUEDE existir, y hay que verlo, no suponerlo.
    f["identicos"] = os.path.join(d, "f3_identicos.wav")
    ff(["-i", tip, "-af", "pan=stereo|c0=c0|c1=c0", "-t", str(DUR),
        "-ar", str(SR), "-c:a", "pcm_s16le", f["identicos"]])

    # F4 — el estéreo REALISTA: la misma voz retrasada 17 ms y filtrada. Ni
    # ortogonal ni idéntica. Es el caso que decide, porque es el que se parece
    # a una grabación de verdad — y el que ninguna de las tres anteriores cubre.
    f["desfasados"] = os.path.join(d, "f4_desfasados.wav")
    ff(["-i", jfk, "-filter_complex",
        "[0:a]pan=mono|c0=c0,atrim=0:%.1f,asplit=2[a][b];"
        "[b]adelay=17|17,lowpass=f=3000[r];[a][r]join=inputs=2:"
        "channel_layout=stereo" % DUR,
        "-t", str(DUR), "-ar", str(SR), "-c:a", "pcm_s16le", f["desfasados"]])

    # F5 — DOS VOCES distintas, una en cada canal. Correlación ~0 con dos
    # señales de la misma familia (no un tono puro como F1).
    f["dos_voces"] = os.path.join(d, "f5_dos_voces.wav")
    largo = os.path.join(CORPUS, "habla_largo.flac")
    ff(["-i", jfk, "-i", largo, "-filter_complex",
        "[0:a]pan=mono|c0=c0,atrim=0:%.1f[l];"
        "[1:a]pan=mono|c0=c0,atrim=60:%.1f,asetpts=PTS-STARTPTS[r];"
        "[l][r]join=inputs=2:channel_layout=stereo" % (DUR, 60 + DUR),
        "-t", str(DUR), "-ar", str(SR), "-c:a", "pcm_s16le", f["dos_voces"]])
    return f


def main() -> int:
    d = tempfile.mkdtemp(prefix="filex-a7-bajo-")
    antes = sorted(os.listdir(d))
    t_ini = time.perf_counter()
    fuentes = fabricar_fuentes(d)

    filas = []
    for nombre, src in fuentes.items():
        if not os.path.exists(src):
            p("FUENTE NO FABRICADA: %s" % nombre)
            continue
        ent = pcm(src)
        c_LR_ent = corr(ent[0], ent[1])
        p("\n=== fuente %s: corr(Lent,Rent) = %.4f, rms %.2f / %.2f dBFS"
          % (nombre, c_LR_ent, rms_db(ent[0]), rms_db(ent[1])))

        # El fichero MALO: el canal derecho silenciado ANTES de codificar. Es
        # exactamente el `pan` de `a7_margenes.py`.
        malo_wav = os.path.join(d, "%s_malo.wav" % nombre)
        ff(["-i", src, "-af", "pan=stereo|c0=c0|c1=0*c0", "-c:a", "pcm_s16le",
            malo_wav])

        for tasa in TASAS:
            for clase, origen in (("buena", src), ("mala", malo_wav)):
                dst = os.path.join(d, "%s_%s_%s.opus" % (nombre, clase, tasa))
                r = ff(["-i", origen, "-c:a", "libopus", "-b:a", tasa,
                        "-ac", "2", dst])
                if r.returncode != 0 or not os.path.exists(dst):
                    p("  %s %s %s -> rc=%d" % (nombre, clase, tasa, r.returncode))
                    continue
                sal = pcm(dst)
                desf = alinear_fft(sal, ent)
                s, e = recortar(sal, ent, desf)
                fila = {
                    "fuente": nombre, "clase": clase, "tasa": tasa,
                    "rc": r.returncode,
                    "desfase_muestras": desf,
                    "desfase_fuerza_bruta": alinear(sal, ent),
                    "corr_LR_entrada": round(c_LR_ent, 4),
                    "rms_ent": [round(rms_db(e[0]), 2), round(rms_db(e[1]), 2)],
                    "rms_sal": [round(rms_db(s[0]), 2), round(rms_db(s[1]), 2)],
                    # A7 tal y como está hoy, para tener el control en la tabla
                    "A7_dispara": bool(rms_db(e[1]) > -60.0
                                       and rms_db(s[1]) <= -80.0),
                    # S1 — ¿la salida es mono? (RMS de L−R frente a la mezcla)
                    "S1_mono_sal_dB": round(rms_db(s[0] - s[1])
                                            - rms_db((s[0] + s[1]) / 2), 2),
                    "S1_mono_ent_dB": round(rms_db(e[0] - e[1])
                                            - rms_db((e[0] + e[1]) / 2), 2),
                    # S2 — la hipótesis: ¿a quién se parece el derecho de la salida?
                    "S2_corr_Rsal_Rent": round(corr(s[1], e[1]), 4),
                    "S2_corr_Rsal_Lent": round(corr(s[1], e[0]), 4),
                    "S3_corr_Lsal_Lent": round(corr(s[0], e[0]), 4),
                    "S4_corr_Lsal_Rsal": round(corr(s[0], s[1]), 4),
                }
                fila["S2_ventaja"] = round(fila["S2_corr_Rsal_Lent"]
                                           - fila["S2_corr_Rsal_Rent"], 4)
                filas.append(fila)
                p("  %-10s %-5s %-4s  A7=%-5s  ventaja=%+7.4f  "
                  "corrRR=%+7.4f corrRL=%+7.4f  monoS=%7.2f dB"
                  % (nombre, clase, tasa, fila["A7_dispara"],
                     fila["S2_ventaja"], fila["S2_corr_Rsal_Rent"],
                     fila["S2_corr_Rsal_Lent"], fila["S1_mono_sal_dB"]))

    # ------------------------------------------------------- ¿hay hueco?
    # Trampa 51: la pregunta no es «¿dónde está el umbral?» sino «¿existe?».
    #
    # **Y hay una tercera clase que no estaba en el enunciado.** Si los dos
    # canales de la ENTRADA son casi iguales, rellenar el derecho con una copia
    # del izquierdo **no pierde nada**: no hay fallo que atrapar, y contar esas
    # celdas como «malas» inventaría un solape que no existe. Se separan por
    # `corr(Lent,Rent)`, que es un dato de la ENTRADA y por tanto conocido antes
    # de juzgar la salida.
    UMBRAL_PERDIDA = 0.90

    def clase_real(f):
        if f["clase"] == "buena":
            return "buena"
        return ("mala_con_perdida" if f["corr_LR_entrada"] < UMBRAL_PERDIDA
                else "mala_sin_perdida")

    for f in filas:
        f["clase_real"] = clase_real(f)

    resumen = {}
    for señal, sentido in (("S2_ventaja", "alto=malo"),
                           ("S2_corr_Rsal_Rent", "bajo=malo"),
                           ("S1_mono_sal_dB", "alto=malo"),
                           ("S4_corr_Lsal_Rsal", "alto=malo")):
        for solo_bajo in (True, False):
            sel = [f for f in filas
                   if (not solo_bajo or int(f["tasa"][:-1]) < 48)]
            malas = [f[señal] for f in sel
                     if f["clase_real"] == "mala_con_perdida"]
            buenas = [f[señal] for f in sel if f["clase_real"] == "buena"]
            if not malas or not buenas:
                continue
            clave = "%s|%s" % (señal, "menos de 48k" if solo_bajo else "todas")
            hueco = (round(min(malas) - max(buenas), 4) if sentido == "alto=malo"
                     else round(min(buenas) - max(malas), 4))
            resumen[clave] = {
                "sentido": sentido,
                "n_malas": len(malas), "n_buenas": len(buenas),
                "malas_min": round(min(malas), 4), "malas_max": round(max(malas), 4),
                "buenas_min": round(min(buenas), 4), "buenas_max": round(max(buenas), 4),
                # hueco > 0 significa que las dos clases NO se solapan
                "hueco": hueco,
            }

    # La tabla de umbrales candidatos sobre la señal que sale mejor parada.
    # «Antes de elegir un umbral, tabula qué atrapa y qué rompe en cada valor»
    # (trampa 51): casi siempre hay una meseta.
    tabla_umbral = []
    for u in (0.002, 0.005, 0.008, 0.01, 0.02, 0.05, 0.08, 0.10, 0.12, 0.13,
              0.15, 0.20, 0.30, 0.50, 0.70):
        atrapa = sum(1 for f in filas
                     if f["clase_real"] == "mala_con_perdida"
                     and f["S2_corr_Rsal_Rent"] < u)
        total_m = sum(1 for f in filas if f["clase_real"] == "mala_con_perdida")
        rompe = sum(1 for f in filas
                    if f["clase_real"] == "buena"
                    and f["S2_corr_Rsal_Rent"] < u)
        total_b = sum(1 for f in filas if f["clase_real"] == "buena")
        # Y lo que NO debe tocar: la mala que no pierde nada.
        falsos_sin_perdida = sum(1 for f in filas
                                 if f["clase_real"] == "mala_sin_perdida"
                                 and f["S2_corr_Rsal_Rent"] < u)
        tabla_umbral.append({"umbral": u, "atrapa": atrapa, "de": total_m,
                             "falsos_positivos": rompe, "de_buenas": total_b,
                             "falsos_sin_perdida": falsos_sin_perdida})

    # **Y el desglose POR TASA, que es donde estaba la respuesta.** Agregar las
    # nueve tasas en una sola cifra de hueco esconde justo lo que importa: a
    # 6-8 kb/s Opus destruye el canal derecho TAMBIÉN en las conversiones
    # buenas, y esas dos tasas solas hunden el hueco de las otras siete.
    por_tasa = []
    for tasa in TASAS:
        sel = [f for f in filas if f["tasa"] == tasa]
        m = [f["S2_corr_Rsal_Rent"] for f in sel
             if f["clase_real"] == "mala_con_perdida"]
        b = [f["S2_corr_Rsal_Rent"] for f in sel if f["clase_real"] == "buena"]
        sp = [f["S2_corr_Rsal_Rent"] for f in sel
              if f["clase_real"] == "mala_sin_perdida"]
        if not m or not b:
            continue
        por_tasa.append({
            "tasa": tasa, "n_malas": len(m), "n_buenas": len(b),
            "malas_max": round(max(m), 4), "buenas_min": round(min(b), 4),
            "hueco": round(min(b) - max(m), 4),
            "A7_dispara_en_las_malas": sum(1 for f in sel
                                           if f["clase_real"] == "mala_con_perdida"
                                           and f["A7_dispara"]),
            "sin_perdida_min": round(min(sp), 4) if sp else None,
        })

    res = {"cuando": time.strftime("%Y-%m-%d %H:%M:%S"),
           "sr": SR, "dur_s": DUR, "tasas": list(TASAS),
           "ms_total": round((time.perf_counter() - t_ini) * 1000, 1),
           "censo_antes": antes,
           "censo_despues": len(os.listdir(d)),
           "umbral_perdida_corrLR": UMBRAL_PERDIDA,
           "resumen": resumen, "tabla_umbral_S2corrRR": tabla_umbral,
           "por_tasa_S2corrRR": por_tasa,
           "filas": filas}
    p("\n=== ¿hay hueco, agregando las nueve tasas? ===")
    for k, v in resumen.items():
        p("%-36s malas [%s, %s]  buenas [%s, %s]  hueco %s"
          % (k, v["malas_min"], v["malas_max"], v["buenas_min"],
             v["buenas_max"], v["hueco"]))
    p("\n=== corr(Rsal,Rent) POR TASA — donde estaba la respuesta ===")
    for t in por_tasa:
        p("  %-4s  peor mala %+7.4f   mejor buena %+7.4f   hueco %+7.4f   %s"
          % (t["tasa"], t["malas_max"], t["buenas_min"], t["hueco"],
             "SEPARA" if t["hueco"] > 0 else "se solapan"))
    p("\n=== umbral sobre corr(Rsal,Rent) — qué atrapa y qué rompe ===")
    for t in tabla_umbral:
        p("  < %.2f  atrapa %2d/%2d  falsos positivos %2d/%2d  "
          "toca %d malas-sin-perdida"
          % (t["umbral"], t["atrapa"], t["de"], t["falsos_positivos"],
             t["de_buenas"], t["falsos_sin_perdida"]))
    with open(os.path.join(AQUI, "a7_repro_n.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(AQUI, "logs"), exist_ok=True)
    with open(os.path.join(AQUI, "logs", "a7_repro_n.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    print("\ndesechable al terminar:", len(os.listdir(d)), "entradas")
    shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
