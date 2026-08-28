#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C19 — los MARGENES de A7, calculados de las dos tandas, y el punto ciego.

1. Recorre `a7_calibracion.json` + `a7_asimetria.json` y calcula, sobre TODAS
   las celdas legitimas, el peor nivel de salida de un canal que era audible en
   la entrada. Ese numero es el que fija el umbral, no una estimacion.
2. Sondea EN EJECUCION el punto ciego que sugiere la tanda de asimetria: Opus a
   tasa muy baja colapsa el estereo a mono, asi que un canal SILENCIADO podria
   volver audible y A7 no dispararia. Deducirlo no vale: se mide.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from calibrar_a7 import astats  # noqa: E402

TIMEOUT = 180


def cargar(n):
    with open(os.path.join(AQUI, n), encoding="utf-8") as fh:
        return json.load(fh)


def _v(x):
    if x is None:
        return None
    if isinstance(x, str):
        return float("-inf") if x.lower().startswith("-inf") else None
    return float(x)


def main():
    cal, asi = cargar("a7_calibracion.json"), cargar("a7_asimetria.json")
    celdas = []          # (etiqueta, rms_ent, rms_sal) por CANAL
    for f in cal["filas"]:
        if f.get("caso", "").startswith("c19:") and "malo" in f["caso"]:
            clase = "FALLO_C19"
        else:
            clase = "legitima"
        re_, rs = f.get("rms_entrada"), f.get("rms_salida")
        if not re_ or not rs or len(re_) != len(rs):
            continue
        for i, (a, b) in enumerate(zip(re_, rs)):
            celdas.append((clase, "%s[c%d]" % (f["caso"], i + 1), _v(a), _v(b)))
    for f in asi["filas"]:
        clase = "legitima"
        for i, (a, b) in enumerate(zip(f["rms_entrada"], f["rms_salida"])):
            celdas.append((clase, "%s/%s[c%d]" % (f["fuente"], f["codec"], i + 1),
                           _v(a), _v(b)))

    leg = [c for c in celdas if c[0] == "legitima" and c[2] is not None and c[3] is not None]
    fal = [c for c in celdas if c[0] == "FALLO_C19" and c[2] is not None and c[3] is not None]

    # peor nivel de salida entre las legitimas cuyo canal de entrada era
    # AUDIBLE segun varios umbrales candidatos
    tabla = []
    for u_aud in (-40.0, -50.0, -60.0, -70.0, -80.0, -90.0, -100.0):
        cand = [c for c in leg if c[2] > u_aud]
        peor = min((c for c in cand), key=lambda c: c[3], default=None)
        tabla.append({"umbral_audible_dB": u_aud, "celdas_legitimas": len(cand),
                      "peor_salida_dB": peor[3] if peor else None,
                      "peor_celda": peor[1] if peor else None})
        print("audible > %7.1f dB -> %3d celdas legitimas, peor salida %10.2f dB  (%s)"
              % (u_aud, len(cand), peor[3] if peor else float("nan"),
                 peor[1] if peor else "-"))

    print("\nlado del FALLO (C19), canal audible en la entrada:")
    for c in fal:
        if c[2] > -60:
            print("  %-28s ent=%8.2f dB  sal=%s dB" % (c[1], c[2], c[3]))

    # ---- el punto ciego: Opus a tasa baja colapsa el estereo --------------
    d = os.path.join(tempfile.gettempdir(), "filex_a7_ciego")
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    antes = sorted(os.listdir(d))
    src = os.path.join(tempfile.gettempdir(), "filex_c19", "entrada.wav")
    ciego = []
    for tasa in ("6k", "8k", "12k", "16k", "24k", "32k", "48k", "64k", "96k"):
        dst = os.path.join(d, "silenciado_%s.opus" % tasa)
        p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", src,
                            "-af", "pan=stereo|c0=c0|c1=0*c0",
                            "-c:a", "libopus", "-b:a", tasa, dst],
                           capture_output=True, timeout=TIMEOUT,
                           stdin=subprocess.DEVNULL)
        if p.returncode != 0:
            continue
        cs, _ = astats(dst)
        if not cs:
            continue
        r = [round(x["rms"], 2) if x["rms"] != float("-inf") else "-inf" for x in cs]
        detecta = cs[1]["rms"] <= -80.0
        ciego.append({"tasa": tasa, "rms_salida": r, "A7_dispara": detecta})
        print("opus %-4s canal derecho SILENCIADO -> sal=%-20s A7 %s"
              % (tasa, r, "DISPARA" if detecta else "NO DISPARA (punto ciego)"))
    despues = sorted(os.listdir(d))

    res = {"umbral_audible": tabla, "punto_ciego_opus": ciego,
           "n_celdas_legitimas": len(leg), "n_celdas_fallo": len(fal),
           "desechable": d, "censo_antes": antes, "censo_despues": despues}
    with open(os.path.join(AQUI, "a7_margenes.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print("\n-> a7_margenes.json")


if __name__ == "__main__":
    main()
