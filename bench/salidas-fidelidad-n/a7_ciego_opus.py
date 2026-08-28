# -*- coding: utf-8 -*-
"""N18 — el punto ciego DECLARADO: qué dice A7 antes y después, celda a celda.

Dos cosas que hay que ver, no suponer:

1. **La tasa deducida.** En un `.opus` la sonda devuelve `bitrate_bps = None`,
   así que la condición se apoya en `8·bytes/duración`. ¿Cae del lado correcto
   del escalón de 48 kb/s en las nueve tasas? Si se pasa por arriba a 32k o por
   abajo a 48k, la regla declara el punto ciego donde no está.
2. **A quién toca.** Se pasa el MISMO fichero por `verificar_fidelidad` con el
   verificador de `HEAD` y con el del árbol, y se comparan `cobertura['A7']` y
   el veredicto. Lo que NO puede cambiar es ningún `fallo`.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)
CORPUS = os.path.join(RAIZ, "corpus", "audio")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def cargar_head():
    tmp = os.path.join(tempfile.gettempdir(), "filex_verificador_head_n3.py")
    with open(tmp, "wb") as fh:
        fh.write(subprocess.run(["git", "show", "HEAD:filex/verificador.py"],
                                capture_output=True, cwd=RAIZ, timeout=60).stdout)
    spec = importlib.util.spec_from_file_location("verificador_head_n3", tmp)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ff(argv):
    return subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin"] + argv,
                          capture_output=True, timeout=300,
                          stdin=subprocess.DEVNULL)


from filex import verificador as NUEVO  # noqa: E402

VIEJO = cargar_head()

d = tempfile.mkdtemp(prefix="filex-ciego-")
antes_censo = sorted(os.listdir(d))
jfk = os.path.join(CORPUS, "habla_jfk.flac")

# Fuente ESTÉREO de canales desiguales (dos voces) y su versión MONO, para ver
# que el punto ciego solo se declara donde el colapso puede esconder algo.
est = os.path.join(d, "est.wav")
# **El canal derecho sale de `habla_largo.flac`, no de `habla_jfk.flac`.** La
# primera pasada de este arnés recortaba `atrim=20:28` sobre jfk, que dura
# menos: `est.wav` salía VACÍO, el `.opus` pesaba 136 B, `astats` devolvía
# `None` y las 27 celdas estéreo mostraban `cobertura A7 = False` **antes y
# después**, que se parece muchísimo a «el cambio no toca nada». Es la trampa
# 38: registra si la condición que dices reproducir se dio.
largo = os.path.join(CORPUS, "habla_largo.flac")
ff(["-i", jfk, "-i", largo, "-filter_complex",
    "[0:a]pan=mono|c0=c0,atrim=0:8[l];"
    "[1:a]pan=mono|c0=c0,atrim=60:68,asetpts=PTS-STARTPTS[r];"
    "[l][r]join=inputs=2:channel_layout=stereo",
    "-t", "8", "-ar", "48000", "-c:a", "pcm_s16le", est])
assert os.path.getsize(est) > 1_000_000, "la fuente estereo salio vacia"
mono = os.path.join(d, "mono.wav")
ff(["-i", jfk, "-t", "8", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", mono])

filas = []
for fuente, etiqueta in ((est, "estereo"), (mono, "mono")):
    for tasa in ("6k", "8k", "16k", "24k", "32k", "40k", "48k", "64k", "96k"):
        for codec, ext, av in (("libopus", "opus", ["-c:a", "libopus"]),
                               ("libmp3lame", "mp3", ["-c:a", "libmp3lame"]),
                               ("aac", "m4a", ["-c:a", "aac"])):
            dst = os.path.join(d, "%s_%s_%s.%s" % (etiqueta, codec, tasa, ext))
            r = ff(["-i", fuente] + av + ["-b:a", tasa, dst])
            if r.returncode != 0 or not os.path.exists(dst):
                continue
            s = NUEVO.sondear(dst)
            tasa_ef = NUEVO._a7_tasa_efectiva(dst, s)
            cs = [x for x in s.get("pistas", []) if x.get("tipo") == "audio"]
            ncan = cs[0].get("canales") if cs else 0
            ciego = NUEVO._a7_punto_ciego(dst, s, [None] * (ncan or 0))
            ped = {"params": {}}
            fv = VIEJO.verificar_fidelidad(dst, ped, fuente)
            fn = NUEVO.verificar_fidelidad(dst, ped, fuente)
            filas.append({
                "fuente": etiqueta, "codec": codec, "tasa_pedida": tasa,
                "canales": ncan,
                "bitrate_sonda": (cs[0].get("bitrate_bps") if cs else None),
                "tasa_efectiva_bps": None if tasa_ef is None else round(tasa_ef),
                "declara_ciego": bool(ciego),
                "A7_cob_antes": fv["cobertura"].get("A7"),
                "A7_cob_despues": fn["cobertura"].get("A7"),
                "veredicto_antes": fv["veredicto"],
                "veredicto_despues": fn["veredicto"],
            })
            print("  %-8s %-11s %-4s can=%d  sonda=%-7s deducida=%-7s ciego=%-5s "
                  "cob %s->%s  ver %s->%s"
                  % (etiqueta, codec, tasa, ncan,
                     filas[-1]["bitrate_sonda"], filas[-1]["tasa_efectiva_bps"],
                     filas[-1]["declara_ciego"], filas[-1]["A7_cob_antes"],
                     filas[-1]["A7_cob_despues"], filas[-1]["veredicto_antes"],
                     filas[-1]["veredicto_despues"]))

cambian = [f for f in filas if f["veredicto_antes"] != f["veredicto_despues"]]
fallos_nuevos = [f for f in cambian if f["veredicto_despues"] == "fallo"]
res = {"n": len(filas), "censo_antes": antes_censo,
       "censo_despues": len(os.listdir(d)),
       "cambian_veredicto": len(cambian),
       "fallos_nuevos": [f["codec"] + "/" + f["tasa_pedida"] for f in fallos_nuevos],
       "declaran_ciego": [f["codec"] + "/" + f["tasa_pedida"] + "/" + f["fuente"]
                          for f in filas if f["declara_ciego"]],
       "filas": filas}
with open(os.path.join(AQUI, "a7_ciego_opus.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)
print("\n  %d celdas; declaran punto ciego: %s" % (len(filas), res["declaran_ciego"]))
print("  cambian de veredicto: %d   FALLOS NUEVOS: %s"
      % (len(cambian), res["fallos_nuevos"]))
shutil.rmtree(d, ignore_errors=True)
