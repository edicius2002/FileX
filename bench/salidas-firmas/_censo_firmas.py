# -*- coding: utf-8 -*-
"""F1 / paso 2 - CENSO EMPIRICO DE MARCADORES: que formatos de salida tienen firma.

LA PREGUNTA. El punto 1 del contrato solo es evaluable si el formato de destino
tiene bytes magicos estables. "No lo sabemos" y "no existe" son cosas distintas y
esta es la sonda que las separa.

EL METODO, y es el del proyecto: sondear en ejecucion, no deducir.
Se escribe CADA formato de salida DOS O TRES VECES con contenidos deliberadamente
distintos (ruido con semillas distintas, geometrias distintas, duraciones distintas)
y se mira que POSICIONES de los primeros 64 bytes coinciden en todas las muestras.

  - posiciones estables + valores constantes  -> el formato tiene marcador
  - ninguna posicion estable                  -> el formato NO tiene marcador
                                                 (crudo sin cabecera, texto plano...)

Es una medida, no una lectura de especificacion: no hay `file` ni `libmagic` en esta
maquina, y la tabla la construye la propia ejecucion de los motores instalados.

LIMITE DECLARADO: coincidir en una posicion no prueba que el valor sea CONSTANTE para
todo el formato, solo que estas N muestras coinciden. Con N=2 hay riesgo de
coincidencia; por eso se usan 3 muestras siempre que el motor lo permite y se publica
`n_muestras` en cada fila. Y al reves: un formato cuyo marcador este mas alla del byte
64 se declararia sin marcador. Ninguno de los 24 nombres actuales lo esta.

Uso: python _censo_firmas.py [local|contenedor|todo]
Escribe firmas_censo.json  (y NO toca nada fuera de bench/salidas-firmas/ y su tmp)
"""
import os, sys, json, time, shutil, subprocess
from collections import defaultdict

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
BASE = os.environ.get("F1_TMP") or os.path.join(
    os.environ.get("TEMP", r"C:\Windows\Temp"), "f1_firmas")
POOL = os.path.join(BASE, "pool")
TMP = os.path.join(BASE, "tmp")
CORPUS = os.path.join(RAIZ, "corpus")
DEVNULL = subprocess.DEVNULL
NCAB = 64          # bytes de cabecera que se comparan
TIMEOUT = 25


def corre(args, timeout=TIMEOUT, cwd=None):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, text=True,
                           timeout=timeout, errors="replace", cwd=cwd)
        return p.returncode, (p.stderr or "")[-400:], (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT", (time.perf_counter() - t0) * 1000
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:200], (time.perf_counter() - t0) * 1000


def limpia(d):
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------- semillas
def semillas():
    os.makedirs(POOL, exist_ok=True)
    s = defaultdict(list)
    esp = [("imagen", "a1.png", ["magick", "-size", "64x48", "xc:white", "-seed", "11",
                                 "+noise", "Random", os.path.join(POOL, "a1.png")]),
           ("imagen", "a2.png", ["magick", "-size", "100x70", "xc:black", "-seed", "29",
                                 "+noise", "Random", os.path.join(POOL, "a2.png")]),
           ("imagen", "a3.png", ["magick", "-size", "37x23", "xc:gray50", "-seed", "53",
                                 "+noise", "Random", os.path.join(POOL, "a3.png")])]
    for mod, nom, cmd in esp:
        p = os.path.join(POOL, nom)
        if not os.path.exists(p):
            corre(cmd, 60)
        s[mod].append(p)
    # audio: DOS SENALES DISTINTAS DESDE LA PRIMERA MUESTRA. Con dos senos de fase 0
    # los formatos de PCM crudo (sb, ub, sw, uw, al, ul...) salian con un "prefijo
    # comun" de 12 bytes que es la rampa del seno, no un marcador: es exactamente el
    # falso positivo que este censo tiene que evitar.
    for nom, filtro, ar in (("b1.wav", "sine=frequency=440:duration=0.5", 8000),
                            ("b2.wav", "anoisesrc=color=white:seed=7:duration=0.9", 16000),
                            ("b3.wav", "sine=frequency=110:duration=0.7", 22050)):
        p = os.path.join(POOL, nom)
        if not os.path.exists(p):
            corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i", filtro,
                   "-ar", str(ar), "-ac", "1", p], 60)
        s["audio"].append(p)
    # video: distinta geometria, duracion, patron Y PISTA DE AUDIO. Lo ultimo no es
    # un detalle: los formatos de PCM crudo (sb, ub, sw, uw, al, ul, pcm...) salen de
    # la pista de AUDIO del video, y con dos senos identicos daban un "prefijo comun"
    # de 64 bytes que es la senal, no un marcador.
    for nom, size, rate, dur, pat, au in (
            ("c1.mp4", "64x48", 10, 0.5, "testsrc", "sine=frequency=440:duration=0.5"),
            ("c2.mp4", "96x64", 15, 0.9, "smptebars",
             "anoisesrc=color=white:seed=7:duration=0.9"),
            ("c3.mp4", "48x32", 12, 0.7, "rgbtestsrc", "sine=frequency=110:duration=0.7")):
        p = os.path.join(POOL, nom)
        if not os.path.exists(p):
            corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
                   "%s=size=%s:rate=%d:duration=%s" % (pat, size, rate, dur),
                   "-f", "lavfi", "-i", au,
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                   "-shortest", p], 90)
        s["video"].append(p)
    # subtitulos: dos ficheros .srt con texto distinto
    for nom, txt in (("d1.srt", "1\n00:00:00,000 --> 00:00:01,000\nHola FileX\n\n"),
                     ("d2.srt", "1\n00:00:02,500 --> 00:00:04,000\nSegunda muestra\n\n"
                                "2\n00:00:05,000 --> 00:00:06,000\ncon dos bloques\n\n")):
        p = os.path.join(POOL, nom)
        if not os.path.exists(p):
            open(p, "w", encoding="utf-8").write(txt)
        s["subtitulo"].append(p)
    # documento: dos PDF distintos (uno del corpus, otro rasterizado)
    p1 = os.path.join(POOL, "e1.pdf")
    if not os.path.exists(p1):
        shutil.copy(os.path.join(CORPUS, "pdf", "tipico_texto.pdf"), p1)
    s["documento"].append(p1)
    p2 = os.path.join(POOL, "e2.pdf")
    if not os.path.exists(p2):
        corre(["magick", os.path.join(POOL, "a2.png"), p2], 60)
    s["documento"].append(p2)
    return dict(s)


# ---------------------------------------------------------------- invocaciones
def inv_ffmpeg(ent, dest, sal):
    """Invocacion de ConvertX (ffmpeg.ts:733-740) + stdin=DEVNULL, -y y timeout."""
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


GS_DEV = {"pdf": "pdfwrite", "ps": "ps2write", "eps": "eps2write", "txt": "txtwrite",
          "docx": "docxwrite", "xps": "xpswrite", "pclm": "pclm", "pam": "pam",
          "ppm": "ppmraw", "pgm": "pgmraw", "pbm": "pbmraw", "psd": "psdrgb",
          "bmp": "bmp16m", "pcx": "pcx24b", "png": "png16m", "jpg": "jpeg",
          "tiff": "tiff24nc", "tif": "tiff24nc"}


def inv_gs(ent, dest, sal):
    dev = GS_DEV.get(dest)
    if not dev:
        return None
    return ["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
            "-sDEVICE=" + dev, "-sOutputFile=" + sal, ent]


# ---------------------------------------------------------------- nucleo
def cab(p):
    with open(p, "rb") as fh:
        return fh.read(NCAB)


def escribe(motor, ent, dest, sal, cwd):
    if motor == "ffmpeg":
        cmd = inv_ffmpeg(ent, dest, sal)
    elif motor == "imagemagick":
        cmd = inv_magick(ent, dest, sal)
    elif motor == "ghostscript":
        cmd = inv_gs(ent, dest, sal)
    else:
        return -127, "motor desconocido", 0, None
    if cmd is None:
        return -127, "sin dispositivo gs", 0, None
    rc, err, ms = corre(cmd, TIMEOUT, cwd=cwd)
    # magick puede escribir sal-0.ext / sal-1.ext...
    base = os.path.basename(sal)
    raiz, ext = os.path.splitext(base)
    cands = [f for f in os.listdir(cwd)
             if (f == base or f.startswith(raiz + "-"))
             and os.path.isfile(os.path.join(cwd, f))]
    if not cands:
        return rc, err, 0, None
    cands.sort()
    real = os.path.join(cwd, cands[0])
    try:
        tam = os.path.getsize(real)
    except OSError:
        return rc, err, 0, None
    if tam <= 0:
        return rc, err, tam, None
    return rc, err, tam, cab(real)


def estables(cabs):
    """Posiciones de los primeros NCAB bytes en las que TODAS las muestras coinciden."""
    n = min(len(c) for c in cabs)
    pos = [i for i in range(n) if len({c[i] for c in cabs}) == 1]
    return pos, bytes(cabs[0][i] for i in pos)


def prefijo_comun(cabs):
    n = min(len(c) for c in cabs)
    i = 0
    while i < n and len({c[i] for c in cabs}) == 1:
        i += 1
    return i


# Nombres de fichero y directorio DELIBERADAMENTE DISTINTOS entre las muestras.
# Hay formatos que estampan la ruta o el nombre del fichero dentro de los primeros
# bytes (`info` de IM escribe la ruta completa; `shtml` escribe `<map id="NOMBRE`;
# `pdb` y `uil` estampan el nombre). Con nombres parecidos, ese texto compartido se
# cuenta como "marcador" y no lo es. Es el segundo falso positivo del metodo.
NOMBRES = [("d0", "v%d"), ("x1", "w%d")]


def censa(motor, formatos, sem, modalidades):
    """Para cada formato: intenta 2-3 muestras con contenidos distintos."""
    res = {}
    limpia(TMP)
    t0 = time.time()
    for k, b in enumerate(sorted(formatos)):
        fila = {"formato": b, "motor": motor, "muestras": [], "estado": "", "errores": []}
        for mod in modalidades:
            sems = sem.get(mod, [])
            if len(sems) < 2:
                continue
            cabs, tams, ok = [], [], True
            for j, ent in enumerate(sems):
                dirn, patron = NOMBRES[j % len(NOMBRES)] if j < 2 else ("y2", "u%d")
                sub = os.path.join(TMP, dirn)
                limpia(sub)
                sal = os.path.join(sub, (patron % (k * 7 + j * 7919)) + "." + b)
                rc, err, tam, c = escribe(motor, ent, b, sal, sub)
                if rc != 0 or not c:
                    ok = False
                    if j == 0:
                        fila["errores"].append("%s: rc=%d %s" % (mod, rc, err.replace("\n", " ")[-140:]))
                    break
                cabs.append(c)
                tams.append(tam)
            if ok and len(cabs) >= 2:
                pos, val = estables(cabs)
                fila["muestras"] = [{"modalidad": mod, "n": len(cabs), "bytes": tams,
                                     "cab": [c.hex() for c in cabs]}]
                fila["n_muestras"] = len(cabs)
                fila["modalidad"] = mod
                fila["prefijo_comun"] = prefijo_comun(cabs)
                fila["pos_estables"] = pos
                fila["val_estables"] = val.hex()
                fila["estado"] = "escrito"
                break
        if not fila["estado"]:
            fila["estado"] = "no_escribible"
        res[b] = fila
        if k % 20 == 0:
            print("  %s %d/%d (%.0fs)" % (motor, k, len(formatos), time.time() - t0), flush=True)
    limpia(TMP)
    return res


if __name__ == "__main__":
    fase = sys.argv[1] if len(sys.argv) > 1 else "local"
    F = json.load(open(os.path.join(SAL, "formatos.json"), encoding="utf-8"))
    pa = F["por_adaptador"]
    sem = semillas()
    print("semillas:", {k: [os.path.basename(x) for x in v] for k, v in sem.items()}, flush=True)
    for k, v in sem.items():
        for p in v:
            assert os.path.exists(p) and os.path.getsize(p) > 0, "semilla vacia: " + p

    out = {}
    if fase in ("local", "todo"):
        out["ffmpeg"] = censa("ffmpeg", set(pa["ffmpeg"]["to"]), sem,
                              ["video", "audio", "imagen", "subtitulo"])
        out["imagemagick"] = censa("imagemagick", set(pa["imagemagick"]["to"]), sem,
                                   ["imagen"])
        out["ghostscript"] = censa("ghostscript", set(GS_DEV), sem, ["documento"])
    json.dump(out, open(os.path.join(SAL, "firmas_censo_%s.json" % fase), "w",
                        encoding="utf-8"), indent=0, ensure_ascii=False)
    for m, r in out.items():
        esc = sum(1 for v in r.values() if v["estado"] == "escrito")
        conf = sum(1 for v in r.values() if v["estado"] == "escrito" and v.get("prefijo_comun", 0) > 0)
        print("\n%-13s escritos %d/%d   con prefijo comun>0: %d" % (m, esc, len(r), conf))
    print("\nescrito firmas_censo_%s.json" % fase)
