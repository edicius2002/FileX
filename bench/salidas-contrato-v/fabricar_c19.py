#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C19 — fabrica el QUINTO miembro de la familia de `resvg`.

    audio estereo con un CANAL SILENCIADO hacia un destino CON PERDIDA.

`bench/contrato-quinto-punto.md` §5 lo deja escrito: de los cinco miembros de
la familia, el contrato atrapa uno (CSV->JSON, D4), la fidelidad atrapa tres
(I9, P2, V8) y **este no lo atrapa nadie**. El contrato ve 2 canales, 44 100 Hz
y 8,000 s -- todo correcto-- y A4/A5 no aplican porque el destino tiene
perdida: no hay PCM que comparar.

Aqui se construye el caso, sus dos controles y su gemelo sin perdida, y se
demuestra que hoy pasa los CINCO puntos del contrato y las QUINCE reglas de
fidelidad.

Todo en un directorio desechable, que se lista ANTES y DESPUES (R21).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

TIMEOUT = 120

# `--antes` carga el verificador TAL Y COMO ESTABA en HEAD, no el del arbol de
# trabajo. Asi la tabla del «antes» se puede regenerar despues de aplicar el
# arreglo, que es la unica forma de que la comparacion siga siendo comprobable.
if "--antes" in sys.argv:
    import importlib.util
    tmp = os.path.join(tempfile.gettempdir(), "filex_verificador_head.py")
    with open(tmp, "wb") as fh:
        fh.write(subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                                capture_output=True, cwd=RAIZ,
                                timeout=60).stdout)
    spec = importlib.util.spec_from_file_location("verificador_head", tmp)
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    SUFIJO = "antes"
else:
    from filex import verificador as V  # noqa: E402
    SUFIJO = "despues"


def correr(orden, cwd=None):
    p = subprocess.run(orden, capture_output=True, timeout=TIMEOUT,
                       stdin=subprocess.DEVNULL, cwd=cwd)
    if p.returncode != 0:
        raise SystemExit("FALLO %s\n%s" % (orden, p.stderr.decode("utf-8", "replace")[-2000:]))
    return p


def censo(d):
    return {n: os.path.getsize(os.path.join(d, n)) for n in sorted(os.listdir(d))}


# ---------------------------------------------------------------------------
# Las cuatro piezas. La entrada lleva DOS tonos distintos, uno por canal: si el
# canal derecho desaparece, la salida sigue declarando 2 canales pero uno de
# ellos ya no lleva senal. Con dos canales IGUALES el caso no existiria.
FABRICA = [
    # (nombre, orden a partir de entrada.wav)
    ("bueno.mp3",  ["-c:a", "libmp3lame", "-b:a", "192k"]),
    ("malo.mp3",   ["-af", "pan=stereo|c0=c0|c1=0*c0", "-c:a", "libmp3lame", "-b:a", "192k"]),
    ("malo.opus",  ["-af", "pan=stereo|c0=c0|c1=0*c0", "-c:a", "libopus", "-b:a", "96k"]),
    ("malo.m4a",   ["-af", "pan=stereo|c0=c0|c1=0*c0", "-c:a", "aac", "-b:a", "192k"]),
    # el gemelo SIN perdida: aqui A4 si lo atrapa (caso 5b del informe P3)
    ("malo.flac",  ["-af", "pan=stereo|c0=c0|c1=0*c0", "-c:a", "flac"]),
    ("bueno.flac", ["-c:a", "flac"]),
    # atenuacion parcial: el canal no desaparece, baja 20 dB. Sirve para
    # calibrar el umbral y para saber si la regla discrimina o solo detecta el
    # silencio absoluto.
    ("atenuado20.mp3", ["-af", "pan=stereo|c0=c0|c1=0.1*c1", "-c:a", "libmp3lame", "-b:a", "192k"]),
    ("atenuado6.mp3",  ["-af", "pan=stereo|c0=c0|c1=0.5*c1", "-c:a", "libmp3lame", "-b:a", "192k"]),
]


def fabricar(dest):
    ent = os.path.join(dest, "entrada.wav")
    correr(["ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=8:sample_rate=44100",
            "-f", "lavfi", "-i", "sine=frequency=880:duration=8:sample_rate=44100",
            "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo[a]",
            "-map", "[a]", "-c:a", "pcm_s16le", ent])
    # un segundo original MONO->ESTEREO legitimo: el control que dice si la
    # regla marcaria una conversion buena en la que los dos canales son iguales.
    mono = os.path.join(dest, "mono.wav")
    correr(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=8:sample_rate=44100",
            "-c:a", "pcm_s16le", mono])
    correr(["ffmpeg", "-y", "-v", "error", "-i", mono, "-ac", "2",
            "-c:a", "libmp3lame", "-b:a", "192k", os.path.join(dest, "mono2estereo.mp3")])
    for nombre, args in FABRICA:
        correr(["ffmpeg", "-y", "-v", "error", "-i", ent] + args
               + [os.path.join(dest, nombre)])
    return ent, mono


def evaluar(salida, entrada, pedido):
    c = V.verificar(salida, pedido, entrada, censo=None)
    f = V.verificar_fidelidad(salida, pedido, entrada)
    return {
        "salida": os.path.basename(salida),
        "entrada": os.path.basename(entrada),
        "contrato": c["veredicto"],
        "contrato_cobertura_incompleta": [k for k, v in c["cobertura"].items() if not v],
        "contrato_hallazgos": [h for h in c["hallazgos"]
                               if h["severidad"] in ("fallo", "aviso")],
        "fidelidad": f["veredicto"],
        "fidelidad_reglas": sorted(f["cobertura"]),
        "fidelidad_hallazgos": [{"regla": h["regla"], "severidad": h["severidad"],
                                 "mensaje": h["mensaje"]} for h in f["hallazgos"]],
    }


def main():
    base = os.path.join(tempfile.gettempdir(), "filex_c19")
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)
    antes = censo(base)
    ent, mono = fabricar(base)
    filas = []
    for nombre, _ in FABRICA:
        filas.append(evaluar(os.path.join(base, nombre), ent, {"params": {}}))
    filas.append(evaluar(os.path.join(base, "mono2estereo.mp3"), mono,
                         {"params": {"canales": 2}}))
    despues = censo(base)
    res = {"dir": base, "censo_antes": antes, "censo_despues": despues,
           "no_declarados": sorted(set(despues) - set(antes)
                                   - {n for n, _ in FABRICA}
                                   - {"entrada.wav", "mono.wav", "mono2estereo.mp3"}),
           "filas": filas}
    with open(os.path.join(AQUI, "c19_%s.json" % SUFIJO), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for f in filas:
        print("%-18s ent=%-12s contrato=%-11s fidelidad=%-11s reglas=%s  %s"
              % (f["salida"], f["entrada"], f["contrato"], f["fidelidad"],
                 ",".join(f["fidelidad_reglas"]) or "-",
                 [h["regla"] + "/" + h["severidad"] for h in f["fidelidad_hallazgos"]
                  if h["severidad"] != "informativo"]))
    print("\n-> c19_%s.json   (el desechable queda en %s)" % (SUFIJO, base))


if __name__ == "__main__":
    main()
