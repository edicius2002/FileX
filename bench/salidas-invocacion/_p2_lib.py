# -*- coding: utf-8 -*-
"""P2 - POLITICA DE INVOCACION P2-INV y arnes comun.

Se declara ANTES de medir (si no, se convierte en un ajuste por caso).
La invocacion de referencia es la REAL de ConvertX, leida del codigo por E1:

    ffmpeg.ts:733-740     ffmpeg -i ENTRADA [-c:v libx264|libx265|libaom-av1] SALIDA
    imagemagick.ts:~150   magick ENTRADA -auto-orient SALIDA

P2-INV la sustituye por siete reglas, cada una etiquetada con la CATEGORIA de
recuperacion que produce si revive la arista:

  imagemagick
    G  -size WxH [-depth 8]   formato crudo sin cabecera en la ENTRADA.
                              La geometria NO esta en el fichero -> CATEGORIA 2.
    X  FMT:ruta               prefijo de codificador explicito (entrada y salida),
                              para no depender de la extension -> CATEGORIA 1.
    L  -resize 256x256>       destino con techo duro de tamano (ico/icon/cur) y
                              -define icon:auto-resize=256,64,32,16 -> CATEGORIA 1.
    A  -alpha set             destino que exige canal alfa (matte/mask/clip) y la
                              entrada no lo trae -> CATEGORIA 1.
    D  -density N             destino paginado (pdf/ps/eps) desde raster: densidad
                              real de la entrada, no 1 px = 1 pt -> CATEGORIA 1.

  ffmpeg
    M  -map 0:<tipo>          mapeo EXPLICITO de las pistas compatibles (CLAUDE.md
                              sec.5: por defecto descarta la segunda de audio).
    C  -c:v/-c:a <defecto>    codec por defecto DEL MUXER, sondeado con
                              `ffmpeg -h muxer=X`, no deducido -> CATEGORIA 1.
    F  -f <muxer>             muxer explicito; y en la entrada, -f rawvideo con
                              -pixel_format/-video_size para los crudos -> CAT. 1/2.

  Y una regla NEGATIVA, que es la que hace honesta la medida:
    si el muxer solo admite un tipo de pista que la entrada NO TIENE, la arista es
    IRRECUPERABLE (categoria 3) y no se fabrica la pista que falta. Convertir un
    hevc sin audio en un opus exigiria inventar el audio.

Las tres desviaciones de CLAUDE.md sec.5 (stdin=DEVNULL primero, -y despues,
timeout duro) se mantienen en las dos invocaciones: son disciplina, no politica.
"""
import os, re, sys, json, time, shutil, subprocess

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
POOL = os.path.join(SAL, "pool")
CORPUS = os.path.join(RAIZ, "corpus")
DEVNULL = subprocess.DEVNULL

# ---------------------------------------------------------------- ejecucion
def corre(args, timeout=45, cwd=None):
    """Proceso separado, SIN shell, argumentos en array, stdin=DEVNULL primero."""
    t0 = time.perf_counter()
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, text=True,
                           timeout=timeout, errors="replace", cwd=cwd)
        return p.returncode, (p.stderr or "")[-700:], (time.perf_counter() - t0) * 1000
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT", (time.perf_counter() - t0) * 1000
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:200], (time.perf_counter() - t0) * 1000


def limpia(d):
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------- catalogos
# Crudos sin cabecera de ImageMagick: la geometria NO esta en el fichero.
IM_CRUDOS = {
    "rgb": 3, "rgba": 4, "rgbo": 4, "bgr": 3, "bgra": 4, "bgro": 4,
    "cmyk": 4, "cmyka": 5, "gray": 1, "graya": 2, "mono": 1, "pal": 1,
    "map": 1, "uyvy": 2, "yuv": 3, "ycbcr": 3, "ycbcra": 4,
    "bayer": 1, "bayera": 2, "ftxt": 1,
}
IM_TECHO256 = {"ico", "icon", "icn", "cur"}
IM_EXIGE_ALFA = {"matte", "mask", "clip", "clipmask"}
PAGINADO = {"pdf", "ps", "ps2", "ps3", "eps", "eps2", "eps3", "epsf", "epi", "epdf"}

FF_CRUDOS = {"rgb": ("rgb24", "rawvideo"), "yuv": ("yuv420p", "rawvideo"),
             "bgr": ("bgr24", "rawvideo"), "gray": ("gray", "rawvideo")}

_CACHE_MUX = {}
_CACHE_EXT2MUX = None


def muxer_info(nombre):
    """Sondea `ffmpeg -h muxer=X`. Devuelve dict con los codecs por defecto."""
    if nombre in _CACHE_MUX:
        return _CACHE_MUX[nombre]
    try:
        p = subprocess.run(["ffmpeg", "-hide_banner", "-h", "muxer=" + nombre],
                           stdin=DEVNULL, capture_output=True, text=True,
                           errors="replace", timeout=20)
        txt = (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        txt = ""
    except OSError:
        txt = ""
    info = {"existe": "Muxer " + nombre in txt or ("Muxer" in txt and "Unknown" not in txt)}
    for tipo, clave in (("v", "Default video codec"), ("a", "Default audio codec"),
                        ("s", "Default subtitle codec")):
        m = re.search(clave + r":\s*([A-Za-z0-9_]+)", txt)
        info[tipo] = m.group(1) if m else None
    m = re.search(r"Common extensions:\s*([^\.\n]+)", txt)
    info["ext"] = [x.strip().lower() for x in m.group(1).split(",")] if m else []
    _CACHE_MUX[nombre] = info
    return info


def ext2mux():
    """Mapa extension -> nombre de muxer, sondeado en ejecucion."""
    global _CACHE_EXT2MUX, _CACHE_MUX
    if _CACHE_EXT2MUX is not None:
        return _CACHE_EXT2MUX
    disco = os.path.join(SAL, "cache_muxers.json")
    if os.path.exists(disco):
        d = json.load(open(disco, encoding="utf-8"))
        _CACHE_MUX.update(d["muxers"])
        _CACHE_EXT2MUX = d["ext2mux"]
        return _CACHE_EXT2MUX
    p = subprocess.run(["ffmpeg", "-hide_banner", "-muxers"], stdin=DEVNULL,
                       capture_output=True, text=True, errors="replace", timeout=60)
    nombres = []
    for ln in ((p.stdout or "") + (p.stderr or "")).splitlines():
        m = re.match(r"^\s*E\s+([A-Za-z0-9_,]+)\s+\S", ln)
        if m:
            nombres += [x for x in m.group(1).split(",") if x]
    mapa = {}
    for n in nombres:
        info = muxer_info(n)
        mapa.setdefault(n.lower(), n)
        for e in info["ext"]:
            mapa.setdefault(e, n)
    _CACHE_EXT2MUX = mapa
    json.dump({"muxers": _CACHE_MUX, "ext2mux": mapa},
              open(disco, "w", encoding="utf-8"), indent=0, ensure_ascii=False)
    return mapa


def muxer_de(dest):
    """Muxer que corresponde al token de destino de ConvertX."""
    d = dest.split(".")[-1].lower() if "." in dest else dest.lower()
    m = ext2mux()
    return m.get(d) or m.get(dest.lower())


_CACHE_ENC = {}


def encoder_info(c):
    """Regla R: sondear las RESTRICCIONES del codificador en ejecucion
    (`ffmpeg -h encoder=X`), no deducirlas. gsm solo admite 8000 Hz mono; si no se
    le da, el muxer no recibe un solo paquete y ConvertX lo cuenta como arista
    inexistente."""
    if c in _CACHE_ENC:
        return _CACHE_ENC[c]
    try:
        p = subprocess.run(["ffmpeg", "-hide_banner", "-h", "encoder=" + c],
                           stdin=DEVNULL, capture_output=True, text=True,
                           errors="replace", timeout=20)
        txt = (p.stdout or "") + (p.stderr or "")
    except (subprocess.TimeoutExpired, OSError):
        txt = ""
    info = {"existe": "is not recognized" not in txt and "Codec '" not in txt}
    for clave, campo in (("Supported sample rates", "ar"),
                         ("Supported sample formats", "sample_fmt"),
                         ("Supported channel layouts", "layout"),
                         ("Supported pixel formats", "pix_fmt"),
                         ("Supported framerates", "fps")):
        m = re.search(clave + r":\s*([^\n]+)", txt)
        info[campo] = m.group(1).split() if m else []
    info["experimental"] = "experimental" in txt.lower()
    _CACHE_ENC[c] = info
    return info


def restricciones(codec, tipo):
    """Banderas que el propio codificador declara necesitar."""
    if not codec or codec == "none":
        return []
    i = encoder_info(codec)
    fl = []
    if tipo == "a":
        if i["ar"]:
            fl += ["-ar", i["ar"][0]]
        if i["layout"]:
            lay = i["layout"][0]
            fl += ["-ac", "1" if lay in ("mono", "1") else "2"] if lay in (
                "mono", "stereo", "1", "2") else []
        if i["sample_fmt"]:
            fl += ["-sample_fmt", i["sample_fmt"][0]]
    else:
        if i["pix_fmt"]:
            fl += ["-pix_fmt", i["pix_fmt"][0]]
        if i["fps"]:
            fl += ["-r", i["fps"][0]]
    if i["experimental"]:
        fl += ["-strict", "-2"]
    return fl


_CACHE_STREAMS = {}


def pistas(ruta):
    """Tipos de pista de un fichero: subconjunto de {'v','a','s'}. Planificacion,
    no verificacion: aqui se decide COMO invocar, no si la salida vale."""
    if ruta in _CACHE_STREAMS:
        return _CACHE_STREAMS[ruta]
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type", "-of", "csv=p=0", ruta],
                       stdin=DEVNULL, capture_output=True, text=True,
                       errors="replace", timeout=30)
    s = set()
    for ln in (p.stdout or "").splitlines():
        ln = ln.strip().rstrip(",")
        if ln.startswith("video"):
            s.add("v")
        elif ln.startswith("audio"):
            s.add("a")
        elif ln.startswith("subtitle"):
            s.add("s")
    _CACHE_STREAMS[ruta] = s
    return s


# ---------------------------------------------------------------- invocaciones
def inv_convertx_ff(ent, dest, sal):
    extra = []
    if dest == "ico":
        extra = ["-filter:v", "scale='min(256,iw)':min'(256,ih)':force_original_aspect_ratio=decrease"]
    if "." in dest:
        cs = dest.split(".")[0]
        extra += {"av1": ["-c:v", "libaom-av1"], "h264": ["-c:v", "libx264"],
                  "h265": ["-c:v", "libx265"], "h266": ["-c:v", "libx266"]}.get(cs, [])
    return ["ffmpeg", "-nostdin", "-y", "-i", ent] + extra + [sal]


def inv_convertx_im(ent, dest, sal):
    return ["magick", ent, "-auto-orient", sal]


def inv_p2_im(ent, dest, sal, geom=None, ent_fmt=None):
    """Politica P2-INV para ImageMagick. Devuelve (args, reglas, categoria_max)."""
    pre, post, reglas, cat = [], [], [], 1
    e = (ent_fmt or ent.rsplit(".", 1)[-1]).lower()
    if e in IM_CRUDOS:
        if not geom:
            return None, ["G-sin-geometria"], 2
        pre += ["-size", "%dx%d" % geom, "-depth", "8"]
        reglas.append("G")
        cat = 2
        ent = e + ":" + ent            # regla X en la entrada
        reglas.append("X-in")
    d = dest.lower()
    if d in IM_TECHO256:
        post += ["-resize", "256x256>", "-define", "icon:auto-resize=256,128,64,48,32,16"]
        reglas.append("L")
    if d in IM_EXIGE_ALFA:
        post += ["-alpha", "set"]
        reglas.append("A")
    if d in PAGINADO:
        post += ["-units", "PixelsPerInch", "-density", "150"]
        reglas.append("D")
    if d in im_formatos():             # regla X en la salida, solo si IM lo conoce
        salida = d + ":" + sal
        reglas.append("X-out")
    else:
        salida = sal
    return ["magick"] + pre + [ent, "-auto-orient"] + post + [salida], reglas, cat


_CACHE_IMF = None


def im_formatos():
    """Nombres de codificador que ImageMagick reconoce como prefijo FMT:."""
    global _CACHE_IMF
    if _CACHE_IMF is not None:
        return _CACHE_IMF
    p = subprocess.run(["magick", "-list", "format"], stdin=DEVNULL,
                       capture_output=True, text=True, errors="replace", timeout=60)
    s = set()
    for ln in ((p.stdout or "") + (p.stderr or "")).splitlines()[2:]:
        t = ln.split()
        if len(t) >= 3 and re.fullmatch(r"[r-][w-][+-]", t[2]):
            s.add(t[0].rstrip("*").lower())
    _CACHE_IMF = s
    return s


def inv_p2_ff(ent, dest, sal, geom=None, ent_fmt=None):
    """Politica P2-INV para ffmpeg. Devuelve (args, reglas, categoria, motivo3)."""
    reglas, cat = [], 1
    ent_args = []
    e = (ent_fmt or ent.rsplit(".", 1)[-1]).lower()
    if e in FF_CRUDOS:
        if not geom:
            return None, ["F-in-sin-geometria"], 2, ""
        pixfmt, demux = FF_CRUDOS[e]
        ent_args += ["-f", demux, "-pixel_format", pixfmt,
                     "-video_size", "%dx%d" % geom]
        reglas += ["F-in"]
        cat = 2
    mux = muxer_de(dest)
    if mux is None:
        return None, ["F-muxer-desconocido"], 3, "el token no corresponde a ningun muxer"
    info = muxer_info(mux)
    admite = {t for t in "vas" if info.get(t)}
    if not admite:                      # muxer sin codec por defecto: se deja elegir
        admite = {"v", "a", "s"}
    tiene = pistas(ent)
    util = admite & tiene
    if not util:
        return (None, ["C-sin-pista-compatible"], 3,
                "el muxer %s admite %s y la entrada tiene %s" %
                (mux, "".join(sorted(admite)) or "-", "".join(sorted(tiene)) or "-"))
    salida_extra = []
    for t in sorted(util):
        salida_extra += ["-map", "0:" + t]
    reglas.append("M")
    # pseudoformatos codec.contenedor de ConvertX
    forz = {}
    if "." in dest:
        forz = {"av1": ("v", "libaom-av1"), "h264": ("v", "libx264"),
                "h265": ("v", "libx265"), "h266": ("v", "libx266")}.get(dest.split(".")[0], {})
    for t in sorted(util):
        c = info.get(t)
        if forz and forz[0] == t:
            c = forz[1]
        if c and c != "none":
            salida_extra += ["-c:" + t, c]
            r = restricciones(c, t)
            if r:
                salida_extra += r
                if "R" not in reglas:
                    reglas.append("R")
    reglas.append("C")
    if dest in IM_TECHO256 or dest == "ico":
        salida_extra += ["-filter:v", "scale='min(256,iw)':'min(256,ih)':force_original_aspect_ratio=decrease"]
        reglas.append("L")
    salida_extra += ["-f", mux]
    reglas.append("F-out")
    return (["ffmpeg", "-nostdin", "-y"] + ent_args + ["-i", ent] +
            salida_extra + [sal]), reglas, cat, ""


# ---------------------------------------------------------------- verificacion
sys.path.insert(0, SAL)
import verificador_p2 as V   # copia congelada; P3 edita el original en paralelo

TEXTUAL = {"txt", "csv", "json", "xml", "html", "htm", "md", "srt", "vtt", "ass",
           "ssa", "sub", "ttml", "lrc", "scc"}

CLASE = {}
for _f, _v in (
    ("png", "png png8 png00 png24 png32 png48 png64"),
    ("gif", "gif gif87"),
    ("jpeg", "jpg jpeg jpe jfif jpg2"),
    ("tiff", "tif tiff tiff64 ptif group4 g3 g4 fax"),
    ("bmp", "bmp bmp2 bmp3 dib"),
    ("pdf", "pdf"),
    ("webp", "webp"),
    ("wav", "wav w64"),
    ("avi", "avi"),
    ("matroska", "mkv webm mka mks"),
    ("isobmff", "mp4 m4v m4a m4b mov 3gp 3g2 f4v ismv isma mj2 avif heic heif"),
    ("flac", "flac"),
    ("mp3", "mp3 mp2 m1a m2a mpa"),
    ("ogg", "ogg oga ogv opus spx ogx"),
    ("zip", "zip epub docx xlsx pptx odt ods odp cbz jar"),
    ("gzip", "gz tgz"),
    ("texto", "txt csv json xml html htm md srt vtt ass ssa ttml lrc ffmeta y4m "
               "svg tex rtf ps eps sub scc jss js chk"),
):
    for _e in _v.split():
        CLASE[_e] = _f
FIRMA_CLASE = {"mp4": "isobmff", "mov": "isobmff", "m4a": "isobmff", "3gp": "isobmff",
               "avif": "isobmff", "heif": "isobmff", "isobmff": "isobmff",
               "riff": None, "desconocido": None, "vacio": None, "ilegible": None}
INDEF = {"desconocido", "riff", None, ""}


def juzga(rc, tam, tam_ent, destino, son, ver):
    """IDENTICA a la de E1 (_muestra.py:99). No se relaja ni un criterio: si el
    juez cambiara, la comparacion antes/despues no mediria la invocacion."""
    if rc != 0 or tam <= 0:
        return True, "FALLO", "rc=%d bytes=%d" % (rc, tam), False
    firma = (son.get("firma") or "").lower()
    esp = CLASE.get(destino)
    fcl = FIRMA_CLASE.get(firma, firma)
    n2 = (esp is not None) and (firma not in INDEF) and (fcl is not None)
    if n2 and fcl != esp:
        return True, "DESTRUIDO", "N2 firma real '%s' != formato pedido '%s'" % (firma, destino), True
    cat = son.get("categoria")
    if cat == "av" and son.get("n_pistas", 1) == 0:
        return True, "DESTRUIDO", "N3 contenedor sin ninguna pista", n2
    if cat == "imagen" and (son.get("ancho", 1) == 0 or son.get("alto", 1) == 0):
        return True, "DESTRUIDO", "N3 imagen de 0 pixeles", n2
    if destino in TEXTUAL and tam_ent > 0 and tam > 100 * tam_ent:
        return True, "DESTRUIDO", "N3 volcado absurdo: %d B desde %d B" % (tam, tam_ent), n2
    avisos = [h for h in ver.get("hallazgos", []) if h.get("severidad") in ("fallo", "aviso")]
    marca = "" if n2 else " [N2 no evaluable]"
    if not avisos:
        return False, "INTEGRO", marca.strip(), n2
    return False, "DEGRADADO", ("; ".join(
        "%s:%s" % (h.get("regla", ""), h.get("mensaje", "")) for h in avisos)[:220]) + marca, n2


def sonda_y_veredicto(real, ent):
    son, ver = {}, {}
    try:
        son = V.sondear(real, "proceso")
    except Exception as e:
        son = {"error": str(e)[:150]}
    try:
        ver = V.verificar(real, {}, ent)
    except Exception as e:
        ver = {"error": str(e)[:150]}
    return son, ver
