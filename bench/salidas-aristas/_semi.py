# -*- coding: utf-8 -*-
"""E1 / Nivel 2 - CENSO DE SEMIARISTAS POR EJECUCION.

Idea central: las aristas son |entradas| x |salidas| (cuadratico, 138.501) pero las
SEMIARISTAS son |entradas| + |salidas| (lineal, ~1.100). Un censo de semiaristas SI
cabe en una sesion, y una semiarista muerta mata TODAS las aristas que la usan.

  - semiarista de SALIDA  (* -> b): escribir b partiendo de una semilla canonica.
  - semiarista de ENTRADA (a -> *): leer un fichero autentico de formato a.

Se replica la invocacion REAL de los adaptadores de ConvertX:
  ffmpeg:      ffmpeg -i ENTRADA [-c:v ...] SALIDA        (ffmpeg.ts:733-740)
  imagemagick: magick ENTRADA -auto-orient SALIDA          (imagemagick.ts:~150)
Con tres desviaciones deliberadas y declaradas: stdin=DEVNULL, -y y timeout duro
(CLAUDE.md sec.5; ConvertX no pone ninguna de las tres).

Escribe: semi_salida.json, semi_entrada.json, pool/ (semillas materializadas)
"""
import os, sys, json, time, shutil, subprocess, random
from collections import defaultdict

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")
POOL = os.path.join(SAL, "pool")
TMP = os.path.join(SAL, "tmp")
CORPUS = os.path.join(RAIZ, "corpus")
DEVNULL = subprocess.DEVNULL
TIMEOUT = 20

sys.path.insert(0, SAL)
import _censo as C  # reutiliza el parseo y las sondas del nivel 1


def corre(args, timeout=TIMEOUT):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return p.returncode, (p.stderr or "")[-600:], (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT", (time.perf_counter() - t0) * 1000
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:200], (time.perf_counter() - t0) * 1000


def limpia(d):
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)


# ------------------------------------------------------------------ semillas
def semillas():
    os.makedirs(POOL, exist_ok=True)
    s = {}
    png = os.path.join(POOL, "s.png")
    if not os.path.exists(png):
        corre(["magick", "-size", "64x48", "gradient:red-blue", "-fill", "white",
               "-draw", "rectangle 8,8 40,30", png], 60)
    s["imagen"] = png
    wav = os.path.join(POOL, "s.wav")
    if not os.path.exists(wav):
        corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
               "sine=frequency=440:duration=0.5", "-ar", "8000", "-ac", "1", wav], 60)
    s["audio"] = wav
    mp4 = os.path.join(POOL, "s.mp4")
    if not os.path.exists(mp4):
        corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
               "testsrc=size=64x48:rate=10:duration=0.5", "-f", "lavfi", "-i",
               "sine=frequency=440:duration=0.5", "-c:v", "libx264", "-pix_fmt",
               "yuv420p", "-c:a", "aac", "-shortest", mp4], 90)
    s["video"] = mp4
    pdf = os.path.join(POOL, "s.pdf")
    if not os.path.exists(pdf):
        shutil.copy(os.path.join(CORPUS, "pdf", "tipico_texto.pdf"), pdf)
    s["documento"] = pdf
    for k, v in s.items():
        assert os.path.exists(v) and os.path.getsize(v) > 0, "semilla %s vacia" % k
    return s


# ------------------------------------------------------------------ invocaciones
def inv_ffmpeg(ent, dest, sal):
    extra = []
    if dest == "ico":
        extra = ["-filter:v", "scale='min(256,iw)':min'(256,ih)':force_original_aspect_ratio=decrease"]
    if "." in dest:
        cs = dest.split(".")[0]
        extra += {"av1": ["-c:v", "libaom-av1"], "h264": ["-c:v", "libx264"],
                  "h265": ["-c:v", "libx265"], "h266": ["-c:v", "libx266"]}.get(cs, [])
    return ["ffmpeg", "-nostdin", "-y", "-i", ent] + extra + [sal]


def inv_magick(ent, dest, sal):
    return ["magick", ent, "-auto-orient", sal]


def ruta(dest, n, dirn):
    # ConvertX escribe target.<convertTo>; para av1.mkv el nombre acaba en .av1.mkv
    return os.path.join(dirn, "o%04d.%s" % (n, dest))


# ------------------------------------------------------------------ nivel 2a: salidas
def censo_salidas(sem, ff_out, im_out):
    limpia(TMP)
    res = {}
    n = 0
    ordenes = [("video", "video"), ("audio", "audio"), ("imagen", "imagen")]
    t0 = time.time()
    for i, b in enumerate(sorted(ff_out)):
        n += 1
        vivo, detalle = False, []
        for mod, _ in ordenes:
            sal = ruta(b, n, TMP)
            if os.path.exists(sal):
                os.remove(sal)
            rc, err, ms = corre(inv_ffmpeg(sem[mod], b, sal))
            tam = os.path.getsize(sal) if os.path.exists(sal) else -1
            detalle.append({"semilla": mod, "rc": rc, "bytes": tam, "ms": round(ms, 1),
                            "err": err[-220:] if rc != 0 or tam <= 0 else ""})
            if rc == 0 and tam > 0:
                vivo = True
                break
            n += 1
        res[("ffmpeg", b)] = {"vivo": vivo, "intentos": detalle}
        if i % 25 == 0:
            print("  ffmpeg out %d/%d  (%.0fs)" % (i, len(ff_out), time.time() - t0), flush=True)
        for f in os.listdir(TMP):
            try:
                os.remove(os.path.join(TMP, f))
            except OSError:
                pass
    print("  ffmpeg out hecho (%.0fs)" % (time.time() - t0), flush=True)

    for i, b in enumerate(sorted(im_out)):
        n += 1
        sal = ruta(b, n, TMP)
        rc, err, ms = corre(inv_magick(sem["imagen"], b, sal))
        # magick puede escribir out-0.ext, out-1.ext... para multipagina
        cands = [x for x in os.listdir(TMP) if x.startswith("o%04d." % n) or x.startswith("o%04d-" % n)]
        tam = max([os.path.getsize(os.path.join(TMP, c)) for c in cands], default=-1)
        res[("imagemagick", b)] = {"vivo": rc == 0 and tam > 0,
                                   "intentos": [{"semilla": "imagen", "rc": rc, "bytes": tam,
                                                 "ms": round(ms, 1), "err": err[-220:] if rc != 0 or tam <= 0 else ""}]}
        if i % 25 == 0:
            print("  magick out %d/%d  (%.0fs)" % (i, len(im_out), time.time() - t0), flush=True)
        for f in os.listdir(TMP):
            try:
                os.remove(os.path.join(TMP, f))
            except OSError:
                pass
    print("  magick out hecho (%.0fs)" % (time.time() - t0), flush=True)
    return res


if __name__ == "__main__":
    sem = semillas()
    print("semillas:", {k: os.path.getsize(v) for k, v in sem.items()}, flush=True)
    ff_in, ff_out = ({x.lower() for x in C.MOTORES["ffmpeg"][0]},
                     {x.lower() for x in C.MOTORES["ffmpeg"][1]})
    im_lee, im_esc = C.im_real()
    print("censo de salidas: ffmpeg %d, magick %d" % (len(ff_out), len(im_esc)), flush=True)
    r = censo_salidas(sem, ff_out, im_esc)
    out = {"%s|%s" % k: v for k, v in r.items()}
    json.dump(out, open(os.path.join(SAL, "semi_salida.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    vivas_ff = sum(1 for (m, b), v in r.items() if m == "ffmpeg" and v["vivo"])
    vivas_im = sum(1 for (m, b), v in r.items() if m == "imagemagick" and v["vivo"])
    print("\nSEMIARISTAS DE SALIDA VIVAS")
    print("  ffmpeg      %d/%d  (%.1f %% muertas)" % (vivas_ff, len(ff_out), 100 * (1 - vivas_ff / len(ff_out))))
    print("  imagemagick %d/%d  (%.1f %% muertas)" % (vivas_im, len(im_esc), 100 * (1 - vivas_im / len(im_esc))))
