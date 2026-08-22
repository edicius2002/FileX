# -*- coding: utf-8 -*-
"""P2 / C15-b segunda vuelta - las salidas cuyo CODIFICADOR SI EXISTE en el build.

Sondeo previo (log-p2-enc.txt): de las 33 semiaristas de salida muertas de ffmpeg,
19 usan un codificador que NO esta compilado en este build. Esas no son un problema
de invocacion en ninguna lectura razonable: son la dimension `build` de la arista
minima viable. Quedan 14 candidatas reales, y sobre ellas se prueban dos reglas mas:

  R2  barrer el espacio de parametros que el propio codificador DECLARA
      (`Supported sample rates` completo, no solo el primero; layouts; pix_fmts),
      en vez de quedarse con el primer valor.
  P   PERFIL DE CODEC: tabla pequena y declarada de las geometrias/tasas fijas que
      algunos codecs exigen y que no aparecen en `-h encoder=` (DV son 720x576@25,
      X-Face son 48x48). Es conocimiento de producto, no sondeo: se declara.
  C2  si el TOKEN DE DESTINO es el nombre de un codificador, se usa ese y no el
      codec por defecto del muxer. Sin esta regla, `-f image2` escribe un JPEG
      dentro de un fichero llamado .vbn y el arnes lo cuenta como arista viva.
      Es el falso positivo que produjo la primera vuelta.

Escribe semi_out_p2b.json
"""
import os, sys, json, glob, subprocess, time

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_out2")
sys.path.insert(0, SAL)
from _p2_lib import (corre, limpia, juzga, sonda_y_veredicto, muxer_de, muxer_info,
                     encoder_info, pistas)

# Perfiles declarados ANTES de medir. (codec) -> lista de listas de banderas.
PERFILES = {
    "dvvideo": [["-s", "720x576", "-r", "25", "-pix_fmt", "yuv420p"],
                ["-s", "720x480", "-r", "30000/1001", "-pix_fmt", "yuv411p"]],
    "dnxhd": [["-s", "1920x1080", "-r", "25", "-pix_fmt", "yuv422p", "-b:v", "120M"],
              ["-s", "1920x1080", "-r", "25", "-pix_fmt", "yuv422p", "-profile:v", "dnxhr_hq"]],
    "amv": [["-s", "160x120", "-r", "25", "-pix_fmt", "yuvj420p"]],
    "mpeg2video": [["-s", "720x576", "-r", "25", "-pix_fmt", "yuv420p", "-b:v", "5M"]],
    "rawvideo": [["-pix_fmt", "rgba"], ["-pix_fmt", "bgr24"]],
    "vbn": [["-pix_fmt", "rgba"]],
    "xface": [["-s", "48x48", "-pix_fmt", "gray"]],
    "mjpeg": [[]],
}
AUDIO_BARRIDO = {
    "mlp": [("48000", "2"), ("44100", "2"), ("48000", "6")],
    "truehd": [("48000", "2"), ("44100", "2"), ("48000", "6")],
    "pcm_s24daud": [("96000", "6")],
    "adpcm_ima_alp": [("11025", "1"), ("22050", "1")],
    "adpcm_ima_amv": [("22050", "1")],
    "pcm_s16le": [("48000", "2"), ("44100", "2")],
}


def encoders():
    p = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, errors="replace", timeout=60)
    e = set()
    for ln in (p.stdout + p.stderr).splitlines():
        t = ln.split()
        if len(t) >= 2 and len(t[0]) == 6 and t[0][0] in "VAS":
            e.add(t[1])
    return e


if __name__ == "__main__":
    limpia(TMP)
    ENC = encoders()
    idx = json.load(open(os.path.join(SAL, "pool_indice.json"), encoding="utf-8"))
    sem = idx["__semillas__"]
    prev = json.load(open(os.path.join(SAL, "semi_out_p2.json"), encoding="utf-8"))
    pend = sorted(k for k, v in prev.items() if k.startswith("ffmpeg|"))

    res = {}
    for k in pend:
        b = k.split("|")[1]
        mux = muxer_de(b)
        mi = muxer_info(mux) if mux else {}
        # regla C2: el token puede ser el nombre del CODIFICADOR
        cod = {}
        for t in "vas":
            c = mi.get(t)
            if c:
                cod[t] = c
        if b in ENC:
            ei = encoder_info(b)
            tipo = "v" if ei.get("pix_fmt") else ("a" if ei.get("ar") or ei.get("sample_fmt") else "s")
            cod = {tipo: b}
        faltan = [c for c in cod.values() if c not in ENC]
        if faltan:
            res[k] = {"estado": "muerta", "categoria_p2": 3,
                      "causa": "codificador ausente del build: " + ",".join(faltan),
                      "muxer": mux}
            print("  %-10s CODIFICADOR AUSENTE (%s)" % (b, ",".join(faltan)), flush=True)
            continue
        if not cod:
            res[k] = {"estado": "muerta", "categoria_p2": 3,
                      "causa": "el muxer no declara ningun codec por defecto (%s)" % mux,
                      "muxer": mux}
            print("  %-10s MUXER SIN CODEC POR DEFECTO (%s)" % (b, mux), flush=True)
            continue
        # construir el barrido
        variantes = []
        for t, c in sorted(cod.items()):
            base = ["-map", "0:" + t, "-c:" + t, c]
            opts = PERFILES.get(c, [[]]) if t == "v" else \
                [["-ar", ar, "-ac", ac] for ar, ac in AUDIO_BARRIDO.get(c, [("48000", "2"), ("44100", "1")])]
            variantes.append([(base + o) for o in opts])
        combos = [[]]
        for v in variantes:
            combos = [c + o for c in combos for o in v]
        vivo, cat, intentos, veredicto = False, 3, [], ""
        for mod in ("video_cif", "audio48", "subtitulo", "jpeg_exif"):
            ent = sem[mod]
            tiene = pistas(ent)
            if not (set(cod) & tiene):
                continue
            for combo in combos[:6]:
                for f in glob.glob(os.path.join(TMP, "*")):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                sal = os.path.join(TMP, "p." + b)
                args = (["ffmpeg", "-nostdin", "-y", "-i", ent] +
                        [x for x in combo] + ["-f", mux, sal])
                rc, err, ms = corre(args, 60)
                tam = os.path.getsize(sal) if os.path.exists(sal) else -1
                son, ver = ({}, {})
                if rc == 0 and tam > 0:
                    son, ver = sonda_y_veredicto(sal, ent)
                nom, categ, mot, _ = juzga(rc, tam, os.path.getsize(ent), b, son, ver)
                intentos.append({"semilla": mod, "args": args, "rc": rc, "bytes": tam,
                                 "ms": round(ms, 1), "veredicto": categ, "motivo": mot,
                                 "firma": son.get("firma"),
                                 "err": err.replace("\n", " ")[-200:] if nom else ""})
                if not nom:
                    vivo, cat, veredicto = True, 1, categ
                    break
            if vivo:
                break
        res[k] = {"estado": "viva" if vivo else "muerta", "categoria_p2": cat,
                  "muxer": mux, "codecs": cod, "veredicto": veredicto,
                  "n_intentos": len(intentos), "intentos": intentos[-8:]}
        print("  %-10s mux=%-14s cod=%-28s %s %s" %
              (b, mux, str(cod), "VIVA" if vivo else "muerta", veredicto), flush=True)

    json.dump(res, open(os.path.join(SAL, "semi_out_p2b.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    from collections import Counter
    print("\n", dict(Counter((v["estado"], v.get("causa", "")[:30]) for v in res.values())))
    print("revividas: %d de %d" % (sum(1 for v in res.values() if v["estado"] == "viva"), len(pend)))
