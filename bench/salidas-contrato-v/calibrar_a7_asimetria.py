#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C19 — el SEGUNDO escalon de A7: ¿se puede avisar por caida ASIMETRICA?

La primera tanda (`calibrar_a7.py`) dejo el escalon de FALLO con 126 dB de
margen, pero solo tenia UN caso legitimo asimetrico (`lowpass=500`, 8,23 dB de
asimetria). Calibrar un umbral con n=1 es exactamente lo que este proyecto
llama poner un suelo a ojo.

Aqui se varia la ENTRADA (trampa de la SEMILLA: «cuando midas una propiedad del
FORMATO, varia la entrada»): fuentes estereo con los dos canales DESIGUALES,
que es donde el estereo conjunto de MP3/AAC/Opus a tasa baja puede colapsar la
imagen estereo y mover la energia de un canal y no del otro.
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


def ff(args):
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + args,
                       capture_output=True, timeout=TIMEOUT,
                       stdin=subprocess.DEVNULL)
    return p.returncode, p.stderr.decode("utf-8", "replace")[-400:]


# Fuentes estereo con canales DESIGUALES: el caso en que una asimetria de
# energia puede aparecer sin que nadie haya silenciado nada.
FUENTES = [
    ("desigual12dB", ["-f", "lavfi", "-i", "sine=frequency=440:duration=8:sample_rate=44100",
                      "-f", "lavfi", "-i", "sine=frequency=880:duration=8:sample_rate=44100",
                      "-filter_complex",
                      "[1:a]volume=-12dB[r];[0:a][r]join=inputs=2:channel_layout=stereo[a]",
                      "-map", "[a]", "-c:a", "pcm_s16le"]),
    ("desigual30dB", ["-f", "lavfi", "-i", "sine=frequency=440:duration=8:sample_rate=44100",
                      "-f", "lavfi", "-i", "sine=frequency=880:duration=8:sample_rate=44100",
                      "-filter_complex",
                      "[1:a]volume=-30dB[r];[0:a][r]join=inputs=2:channel_layout=stereo[a]",
                      "-map", "[a]", "-c:a", "pcm_s16le"]),
    # ruido descorrelacionado en los dos canales: lo mas parecido a musica real
    ("ruido_descorrelado", ["-f", "lavfi", "-i", "anoisesrc=d=8:c=pink:r=44100:seed=1",
                            "-f", "lavfi", "-i", "anoisesrc=d=8:c=pink:r=44100:seed=2",
                            "-filter_complex",
                            "[1:a]volume=-9dB[r];[0:a][r]join=inputs=2:channel_layout=stereo[a]",
                            "-map", "[a]", "-c:a", "pcm_s16le"]),
    # canal derecho ya CASI silencioso en la ENTRADA: el control que dice si la
    # regla se equivoca cuando la entrada ya venia asi
    ("derecho_-70dB", ["-f", "lavfi", "-i", "sine=frequency=440:duration=8:sample_rate=44100",
                       "-f", "lavfi", "-i", "sine=frequency=880:duration=8:sample_rate=44100",
                       "-filter_complex",
                       "[1:a]volume=-70dB[r];[0:a][r]join=inputs=2:channel_layout=stereo[a]",
                       "-map", "[a]", "-c:a", "pcm_s16le"]),
    # canal derecho EXACTAMENTE silencioso en la entrada
    ("derecho_mudo", ["-f", "lavfi", "-i", "sine=frequency=440:duration=8:sample_rate=44100",
                      "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=8",
                      "-filter_complex",
                      "[0:a][1:a]join=inputs=2:channel_layout=stereo[a]",
                      "-map", "[a]", "-c:a", "pcm_s16le"]),
]

CODECS = [
    ("opus6k", ["-c:a", "libopus", "-b:a", "6k"], ".opus"),
    ("opus8k", ["-c:a", "libopus", "-b:a", "8k"], ".opus"),
    ("mp38k", ["-c:a", "libmp3lame", "-b:a", "8k"], ".mp3"),
    ("mp38k_joint", ["-c:a", "libmp3lame", "-b:a", "8k", "-joint_stereo", "1"], ".mp3"),
    ("aac8k", ["-c:a", "aac", "-b:a", "8k"], ".m4a"),
    ("aac16k", ["-c:a", "aac", "-b:a", "16k"], ".m4a"),
    ("mp3q9", ["-c:a", "libmp3lame", "-q:a", "9"], ".mp3"),
    ("vorbis_q_1", ["-c:a", "libvorbis", "-q:a", "-1"], ".ogg"),
    ("mp3_192k", ["-c:a", "libmp3lame", "-b:a", "192k"], ".mp3"),
]


def main():
    d = os.path.join(tempfile.gettempdir(), "filex_a7_asim")
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    antes = sorted(os.listdir(d))
    filas = []
    for nf, args in FUENTES:
        src = os.path.join(d, nf + ".wav")
        rc, err = ff(args + [src])
        if rc != 0:
            print("NO SE PUDO FABRICAR %s: %s" % (nf, err))
            continue
        ce, _ = astats(src)
        for nc, cargs, ext in CODECS:
            dst = os.path.join(d, "%s__%s%s" % (nf, nc, ext))
            rc, err = ff(["-i", src, "-vn", "-sn", "-map", "0:a:0"] + cargs + [dst])
            if rc != 0 or not os.path.exists(dst):
                continue
            cs, _ = astats(dst)
            if not (ce and cs and len(ce) == len(cs)):
                continue
            caidas = [round(a["rms"] - b["rms"], 2) for a, b in zip(ce, cs)]
            fila = {"fuente": nf, "codec": nc,
                    "rms_entrada": [round(x["rms"], 2) for x in ce],
                    "rms_salida": [round(x["rms"], 2) for x in cs],
                    "caida_dB": caidas,
                    "asimetria_dB": round(max(caidas) - min(caidas), 2)}
            filas.append(fila)
            print("%-20s %-12s ent=%-18s sal=%-18s caida=%-16s asim=%6.2f"
                  % (nf, nc, fila["rms_entrada"], fila["rms_salida"],
                     caidas, fila["asimetria_dB"]))
    despues = sorted(os.listdir(d))
    legit = [f for f in filas if f["fuente"] != "derecho_mudo"]
    res = {"filas": filas, "desechable": d,
           "censo_antes": antes, "censo_despues": despues,
           "peor_asimetria_legitima_dB": max((f["asimetria_dB"] for f in legit),
                                             default=None),
           "peor_asimetria_legitima": max(legit, key=lambda f: f["asimetria_dB"],
                                          default=None)}
    with open(os.path.join(AQUI, "a7_asimetria.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print("\nPEOR ASIMETRIA LEGITIMA: %s dB  (%s)"
          % (res["peor_asimetria_legitima_dB"],
             res["peor_asimetria_legitima"] and
             (res["peor_asimetria_legitima"]["fuente"] + "/" +
              res["peor_asimetria_legitima"]["codec"])))
    print("-> a7_asimetria.json")


if __name__ == "__main__":
    main()
