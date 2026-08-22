# -*- coding: utf-8 -*-
"""E1 / Nivel 2b - SEGUNDA VUELTA sobre las semiaristas de salida declaradas muertas.

Motivo: la primera vuelta usa semillas minimas (64x48, sin pista de subtitulos) y eso
produce FALSOS MUERTOS: `.srt` falla por no haber subtitulo que escribir, `.h261` por
exigir 352x288, `.thumbnail` por no haber miniatura EXIF. Una arista solo se declara
NOMINAL cuando NINGUNA semilla razonable la revive.

Semillas anadidas: video CIF 352x288, subtitulo SRT real, JPEG del corpus con EXIF,
audio PCM 48 kHz estereo.

Escribe semi_salida2.json con el veredicto final por semiarista de salida.
"""
import os, sys, json, time, shutil, subprocess

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")
POOL = os.path.join(SAL, "pool")
TMP = os.path.join(SAL, "tmp2")
CORPUS = os.path.join(RAIZ, "corpus")
DEVNULL = subprocess.DEVNULL
sys.path.insert(0, SAL)
from _semi import corre, inv_ffmpeg, inv_magick, limpia


def semillas2():
    os.makedirs(POOL, exist_ok=True)
    s = {}
    cif = os.path.join(POOL, "s_cif.mp4")
    if not os.path.exists(cif):
        corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
               "testsrc=size=352x288:rate=25:duration=1", "-f", "lavfi", "-i",
               "sine=frequency=440:duration=1:sample_rate=48000", "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-shortest", cif], 90)
    s["video_cif"] = cif
    srt = os.path.join(POOL, "s.srt")
    if not os.path.exists(srt):
        open(srt, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:02,000\nFILEXSENTINELA E1\n\n"
            "2\n00:00:02,000 --> 00:00:04,000\nsegunda linea de subtitulo\n\n")
    s["subtitulo"] = srt
    a48 = os.path.join(POOL, "s48.wav")
    if not os.path.exists(a48):
        corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
               "sine=frequency=440:duration=1:sample_rate=48000", "-ac", "2", a48], 60)
    s["audio48"] = a48
    s["jpeg_exif"] = os.path.join(CORPUS, "imagen", "tipico.jpg")
    s["png_alfa"] = os.path.join(CORPUS, "imagen", "alpha.png")
    s["tif16"] = os.path.join(CORPUS, "imagen", "tipico.png")
    return s


if __name__ == "__main__":
    prev = json.load(open(os.path.join(SAL, "semi_salida.json"), encoding="utf-8"))
    muertas = [k for k, v in prev.items() if not v["vivo"]]
    print("segunda vuelta sobre %d semiaristas de salida" % len(muertas), flush=True)
    s2 = semillas2()
    limpia(TMP)
    orden_ff = ["video_cif", "subtitulo", "audio48", "jpeg_exif"]
    orden_im = ["jpeg_exif", "png_alfa", "tif16"]
    res = {}
    n = 0
    t0 = time.time()
    for k in sorted(muertas):
        motor, b = k.split("|")
        vivo, det = False, []
        orden = orden_ff if motor == "ffmpeg" else orden_im
        for mod in orden:
            n += 1
            sal = os.path.join(TMP, "r%04d.%s" % (n, b))
            inv = inv_ffmpeg if motor == "ffmpeg" else inv_magick
            rc, err, ms = corre(inv(s2[mod], b, sal), 25)
            cands = [x for x in os.listdir(TMP) if x.startswith("r%04d." % n) or x.startswith("r%04d-" % n)]
            tam = max([os.path.getsize(os.path.join(TMP, c)) for c in cands], default=-1)
            det.append({"semilla": mod, "rc": rc, "bytes": tam, "ms": round(ms, 1),
                        "err": err.replace("\n", " ")[-200:] if (rc != 0 or tam <= 0) else ""})
            for f in os.listdir(TMP):
                try:
                    os.remove(os.path.join(TMP, f))
                except OSError:
                    pass
            if rc == 0 and tam > 0:
                vivo = True
                break
        res[k] = {"vivo": vivo, "revivida_por": det[-1]["semilla"] if vivo else None,
                  "intentos": det}
        print("  %-28s %s" % (k, "VIVA por " + det[-1]["semilla"] if vivo else "MUERTA"), flush=True)
    json.dump(res, open(os.path.join(SAL, "semi_salida2.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    rev = sum(1 for v in res.values() if v["vivo"])
    print("\nrevividas %d de %d  (%.0fs)" % (rev, len(muertas), time.time() - t0))
