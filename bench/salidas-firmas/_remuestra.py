# -*- coding: utf-8 -*-
"""F1 / paso 5 - LA METRICA HONESTA: reejecutar LA MISMA muestra de E1.

No es "cuantas firmas conozco": es que fraccion de los DESTINOS REALES pasa de
"no evaluable" a "evaluado". Para que la cifra sea comparable con el 12 % de
bench/aristas-nominales.md sec.11.3 hay que medir sobre la MISMA muestra: las 498
aristas generales + las 100 del estrato PDF de bench/salidas-aristas/muestra.json,
con la misma semilla aleatoria, la misma invocacion y las mismas semillas.

bench/salidas-aristas/ es SOLO LECTURA (se leen muestra.json, semi_entrada.json y
semi_salida*.json). El `pool/` de E1 esta borrado —711 MB, regenerable— asi que las
semillas se rehacen aqui, en un directorio desechable propio, con las mismas
recetas: por eso este fichero copia las funciones de _semi.py / _semi2.py /
_semi_in.py en vez de importarlas (esas escriben en el directorio de E1).

Y mide las DOS cosas que importan:
  (a) cuantos destinos tienen el punto 1 evaluable, antes y despues;
  (b) cuantos FALSOS POSITIVOS introduce el vocabulario nuevo, que es el riesgo
      real de ampliarlo: una arista que E1 conto como REAL y que ahora se marca
      DESTRUIDO sin que el motor haya hecho nada mal.

Uso: python _remuestra.py
Escribe remuestra.json
"""
import os, sys, json, time, glob, shutil, subprocess
from collections import Counter, defaultdict

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
ARI = os.path.join(RAIZ, r"bench\salidas-aristas")   # SOLO LECTURA
CORPUS = os.path.join(RAIZ, "corpus")
BASE = os.environ.get("F1_TMP") or os.path.join(os.environ.get("TEMP", "."), "f1")
POOL = os.path.join(BASE, "rpool")
PIN = os.path.join(POOL, "in")
TMP = os.path.join(BASE, "rtmp")
DEVNULL = subprocess.DEVNULL

sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, ARI)
import verificador as V                 # el AMPLIADO
import verificador_congelado as VC      # el que uso E1, para el A/B


# ---------------------------------------------------------------- utilidades
def corre(args, timeout=45):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, text=True,
                           timeout=timeout, errors="replace", cwd=TMP)
        return p.returncode, (p.stderr or "")[-400:], (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT", (time.perf_counter() - t0) * 1000
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:150], (time.perf_counter() - t0) * 1000


def limpia(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)


# --- invocaciones: copia literal de bench/salidas-aristas/_semi.py -----------
def inv_ffmpeg(ent, dest, sal):
    extra = []
    if dest == "ico":
        extra = ["-filter:v",
                 "scale='min(256,iw)':min'(256,ih)':force_original_aspect_ratio=decrease"]
    if "." in dest:
        cs = dest.split(".")[0]
        extra += {"av1": ["-c:v", "libaom-av1"], "h264": ["-c:v", "libx264"],
                  "h265": ["-c:v", "libx265"], "h266": ["-c:v", "libx266"]}.get(cs, [])
    return ["ffmpeg", "-nostdin", "-y", "-i", ent] + extra + [sal]


def inv_magick(ent, dest, sal):
    return ["magick", ent, "-auto-orient", sal]


# --- semillas: copia literal de _semi.py/_semi2.py, con POOL propio ---------
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


def corpus_por_ext():
    m = {}
    for r, _, fs in os.walk(CORPUS):
        for f in fs:
            e = f.rsplit(".", 1)[-1].lower()
            p = os.path.join(r, f)
            if e not in m or os.path.getsize(p) < os.path.getsize(m[e]):
                m[e] = p
    return m


def materializa(a, proc, sem, corp):
    """Rehace la semilla de entrada del formato `a` con LA MISMA procedencia que E1."""
    if proc == "corpus" or a in corp and (proc or "").startswith("corpus"):
        return corp.get(a)
    dest = os.path.join(PIN, "m." + a)
    for c in glob.glob(os.path.join(PIN, "m." + a + "*")):
        try:
            os.remove(c)
        except OSError:
            pass
    if proc and "<-" in proc:
        motor, mod = proc.split("<-")
        inv = inv_ffmpeg if motor == "ffmpeg" else inv_magick
        if mod in sem:
            rc, err, ms = corre(inv(sem[mod], a, dest), 25)
            g = sorted(glob.glob(os.path.join(PIN, "m." + a + "*")))
            if rc == 0 and g and os.path.getsize(g[0]) > 0:
                return g[0]
    # respaldo: probar el orden completo, como hacia _semi_in.materializa
    for motor, orden in (("ffmpeg", ["video_cif", "subtitulo", "audio48", "jpeg_exif"]),
                         ("magick", ["jpeg_exif", "png_alfa"])):
        inv = inv_ffmpeg if motor == "ffmpeg" else inv_magick
        for mod in orden:
            rc, err, ms = corre(inv(sem[mod], a, dest), 25)
            g = sorted(glob.glob(os.path.join(PIN, "m." + a + "*")))
            if rc == 0 and g and os.path.getsize(g[0]) > 0:
                return g[0]
    return corp.get(a)


# ---------------------------------------------------------------- criterios
# Criterio N2 de E1, literal (bench/salidas-aristas/_muestra.py lineas 69-96)
CLASE_E1 = {}
for _f, _v in (
    ("png", "png png8 png00 png24 png32 png48 png64"), ("gif", "gif gif87"),
    ("jpeg", "jpg jpeg jpe jfif jpg2"),
    ("tiff", "tif tiff tiff64 ptif group4 g3 g4 fax"), ("bmp", "bmp bmp2 bmp3 dib"),
    ("pdf", "pdf"), ("webp", "webp"), ("wav", "wav w64"), ("avi", "avi"),
    ("matroska", "mkv webm mka mks"),
    ("isobmff", "mp4 m4v m4a m4b mov 3gp 3g2 f4v ismv isma mj2 avif heic heif"),
    ("flac", "flac"), ("mp3", "mp3 mp2 m1a m2a mpa"), ("ogg", "ogg oga ogv opus spx ogx"),
    ("zip", "zip epub docx xlsx pptx odt ods odp cbz jar"), ("gzip", "gz tgz"),
    ("texto", "txt csv json xml html htm md srt vtt ass ssa ttml lrc ffmeta y4m "
               "svg tex rtf ps eps sub scc jss js chk"),
):
    for _e in _v.split():
        CLASE_E1[_e] = _f
FIRMA_CLASE_E1 = {"mp4": "isobmff", "mov": "isobmff", "m4a": "isobmff", "3gp": "isobmff",
                  "avif": "isobmff", "heif": "isobmff", "isobmff": "isobmff",
                  "riff": None, "desconocido": None, "vacio": None, "ilegible": None}
INDEF_E1 = {"desconocido", "riff", None, ""}


def n2_e1(destino, firma):
    esp = CLASE_E1.get(destino)
    fcl = FIRMA_CLASE_E1.get(firma, firma)
    ev = (esp is not None) and (firma not in INDEF_E1) and (fcl is not None)
    return ev, (ev and fcl != esp)


# ---------------------------------------------------------------- testigos
def testigo_cpu(n=400000):
    import hashlib
    t = time.perf_counter()
    h = b"x"
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    return (time.perf_counter() - t) * 1000


def testigo_proc(tope=20.0):
    t = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-v", "quiet", "-version"], capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=tope)
    except Exception:
        return tope * 1000
    return (time.perf_counter() - t) * 1000


# ---------------------------------------------------------------- principal
def main():
    mue = json.load(open(os.path.join(ARI, "muestra.json"), encoding="utf-8"))
    sein = json.load(open(os.path.join(ARI, "semi_entrada.json"), encoding="utf-8"))
    filas = [dict(r, _estrato="general") for r in mue["general"] if "nominal" in r] + \
            [dict(r, _estrato="pdf") for r in mue["pdf"] if "nominal" in r]
    print("muestra de E1: %d filas" % len(filas), flush=True)

    os.makedirs(PIN, exist_ok=True)
    limpia(TMP)
    sem = semillas()
    corp = corpus_por_ext()

    # procedencia de cada formato de entrada, tal y como la registro E1
    proc = {}
    for k, v in sein.items():
        motor, a = k.split("|")
        if v.get("estado") != "no_materializable":
            proc.setdefault(a, v.get("procedencia"))

    origenes = sorted({r["a"] for r in filas})
    print("materializando %d formatos de entrada..." % len(origenes), flush=True)
    ent_de = {}
    t0 = time.time()
    for i, a in enumerate(origenes):
        ent_de[a] = materializa(a, proc.get(a), sem, corp)
        if i % 25 == 0:
            print("   %d/%d (%.0fs)" % (i, len(origenes), time.time() - t0), flush=True)
    faltan = [a for a, p in ent_de.items() if not p or not os.path.exists(p)]
    print("   sin semilla: %d %s" % (len(faltan), faltan[:20]), flush=True)

    res = []
    t0 = time.time()
    for i, r in enumerate(filas):
        a, b, ms = r["a"], r["b"], r["motores"]
        ent = ent_de.get(a)
        if not ent or not os.path.exists(ent):
            res.append({"a": a, "b": b, "estrato": r.get("_estrato"),
                        "estado": "sin_semilla"})
            continue
        motor = "imagemagick" if "imagemagick" in ms.split(",") else ms.split(",")[0]
        inv = inv_magick if motor == "imagemagick" else inv_ffmpeg
        limpia(TMP)
        sal = os.path.join(TMP, "z%04d.%s" % (i, b))
        rc, err, msx = corre(inv(ent, b, sal), 45)
        cands = sorted(x for x in os.listdir(TMP)
                       if x.startswith("z%04d" % i) and os.path.isfile(os.path.join(TMP, x)))
        tam = max([os.path.getsize(os.path.join(TMP, c)) for c in cands], default=-1)
        real = os.path.join(TMP, cands[0]) if cands else None
        fila = {"a": a, "b": b, "motor": motor, "rc": rc, "bytes": tam,
                "estrato": r.get("_estrato"),
                "e1_nominal": r.get("nominal"), "e1_categoria": r.get("categoria"),
                "e1_firma": r.get("firma"), "e1_n2_evaluable": r.get("n2_evaluable")}
        if rc == 0 and tam > 0 and real:
            fv = VC.firma_real(real)     # vocabulario VIEJO (24 nombres)
            fn = V.firma_real(real)      # vocabulario NUEVO
            ev_v, n2_v = n2_e1(b, fv)
            est = V.punto1_estado(real)
            try:
                son = V.sondear(real, "proceso")
            except Exception as e:
                son = {"firma": fn, "bytes": tam, "error": str(e)[:150]}
            h1 = V.punto1_firma(real, son, {"destino": b, "rc": 0})
            sev = [x["severidad"] for x in h1]
            fila.update({"firma_vieja": fv, "firma_nueva": fn,
                         "n2_evaluable_viejo": ev_v, "n2_destruido_viejo": n2_v,
                         "punto1_nuevo": est,
                         "punto1_fallo": "fallo" in sev,
                         "punto1_msg": [x["mensaje"] for x in h1][:1],
                         "aceptables": sorted(V.EXT_A_FIRMAS.get("." + b, []))[:8]})
        else:
            fila.update({"estado": "sin_fichero", "err": err.replace("\n", " ")[-160:]})
        res.append(fila)
        if i % 40 == 0:
            print("   arista %d/%d (%.0fs)" % (i, len(filas), time.time() - t0), flush=True)

    json.dump({"filas": res}, open(os.path.join(SAL, "remuestra.json"), "w",
                                   encoding="utf-8"), indent=0, ensure_ascii=False)
    limpia(TMP)
    shutil.rmtree(POOL, ignore_errors=True)
    return res


if __name__ == "__main__":
    t1a, t2a = testigo_cpu(), testigo_proc()
    print("testigos ANTES: cpu %.1f ms  proceso %.1f ms" % (t1a, t2a), flush=True)
    res = main()
    t1b, t2b = testigo_cpu(), testigo_proc()
    print("testigos DESPUES: cpu %.1f ms  proceso %.1f ms  deriva x%.2f  nivel x%.2f"
          % (t1b, t2b, t1b / t1a, max(t2a, t2b) / 26.6))
    print("\nescrito remuestra.json")
