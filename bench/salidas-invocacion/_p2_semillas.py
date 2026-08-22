# -*- coding: utf-8 -*-
"""P2 - reconstruye el pool de semillas de E1 (que se borro: 711 MB regenerables).

Solo materializa los formatos que P2 necesita: los 34 de las semiaristas de entrada
muertas y los origenes de las 115 aristas nominales de la muestra de E1.
Replica el mismo orden de procedencia que _semi_in.py: corpus > ffmpeg > magick.
Anota la GEOMETRIA de origen de cada semilla: es el dato que los crudos sin
cabecera no llevan dentro y que la regla G tiene que aportar desde fuera.

Escribe pool/ y pool_indice.json
"""
import os, sys, json, glob

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
POOL = os.path.join(SAL, "pool")
PIN = os.path.join(POOL, "in")
CORPUS = os.path.join(RAIZ, "corpus")
sys.path.insert(0, SAL)
from _p2_lib import corre, limpia


def semillas_base():
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
        import shutil
        shutil.copy(os.path.join(CORPUS, "pdf", "tipico_texto.pdf"), pdf)
    s["documento"] = pdf
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


GEOM_SEM = {}   # geometria de cada semilla, por sonda en proceso


def geom(ruta):
    if ruta in GEOM_SEM:
        return GEOM_SEM[ruta]
    import verificador_p2 as V
    try:
        s = V.sondear(ruta, "proceso")
        g = (s.get("ancho"), s.get("alto")) if s.get("ancho") else None
    except Exception:
        g = None
    GEOM_SEM[ruta] = g
    return g


def corpus_por_ext():
    m = {}
    for r, _, fs in os.walk(CORPUS):
        for f in fs:
            e = f.rsplit(".", 1)[-1].lower()
            p = os.path.join(r, f)
            if e not in m or os.path.getsize(p) < os.path.getsize(m[e]):
                m[e] = p
    return m


def materializa(a, sem, corp, viva_ff_out, viva_im_out):
    """Igual que _semi_in.materializa, y ademas devuelve la geometria de origen."""
    if a in corp:
        return corp[a], "corpus", geom(corp[a])
    dest = os.path.join(PIN, "m." + a)
    for c in glob.glob(os.path.join(PIN, "m." + a + "*")):
        try:
            os.remove(c)
        except OSError:
            pass
    if a in viva_ff_out:
        for mod in ("video_cif", "subtitulo", "audio48", "jpeg_exif"):
            rc, err, ms = corre(["ffmpeg", "-nostdin", "-y", "-i", sem[mod], dest], 25)
            if rc == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0:
                return dest, "ffmpeg<-" + mod, geom(sem[mod])
    if a in viva_im_out:
        for mod in ("jpeg_exif", "png_alfa"):
            rc, err, ms = corre(["magick", sem[mod], "-auto-orient", dest], 25)
            cands = sorted(glob.glob(os.path.join(PIN, "m." + a + "*")))
            if rc == 0 and cands and os.path.getsize(cands[0]) > 0:
                return cands[0], "magick<-" + mod, geom(sem[mod])
    return None, "no materializable", None


if __name__ == "__main__":
    os.makedirs(PIN, exist_ok=True)
    sem = semillas_base()
    corp = corpus_por_ext()
    E1D = os.path.join(RAIZ, r"bench\salidas-aristas")
    s1 = json.load(open(os.path.join(E1D, "semi_salida.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(E1D, "semi_salida2.json"), encoding="utf-8"))
    vivas = {k: (v["vivo"] or s2.get(k, {}).get("vivo", False)) for k, v in s1.items()}
    viva_ff_out = {k.split("|")[1] for k, v in vivas.items() if v and k.startswith("ffmpeg|")}
    viva_im_out = {k.split("|")[1] for k, v in vivas.items() if v and k.startswith("imagemagick|")}

    inv = json.load(open(os.path.join(SAL, "inventario_e1.json"), encoding="utf-8"))
    necesarios = {k.split("|")[1] for k in inv["muertas_entrada"]}
    necesarios |= {r["a"] for r in inv["nominales_muestra"]}
    necesarios |= {r["a"] for r in inv["degradados_pdf"]} | {r["a"] for r in inv["nominales_pdf"]}
    print("formatos de entrada a materializar: %d" % len(necesarios), flush=True)

    idx = {}
    for i, a in enumerate(sorted(necesarios)):
        ruta, proc, g = materializa(a, sem, corp, viva_ff_out, viva_im_out)
        idx[a] = {"ruta": ruta, "procedencia": proc, "geometria": g,
                  "bytes": os.path.getsize(ruta) if ruta else -1}
        if i % 20 == 0:
            print("  %d/%d" % (i, len(necesarios)), flush=True)
    idx["__semillas__"] = {k: v for k, v in sem.items()}
    json.dump(idx, open(os.path.join(SAL, "pool_indice.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    fall = [a for a, v in idx.items() if a != "__semillas__" and v["ruta"] is None]
    print("\nmaterializados %d, sin semilla %d: %s" %
          (len(necesarios) - len(fall), len(fall), fall))
