# -*- coding: utf-8 -*-
"""Sondas de medida: bytes magicos, propiedades por familia y texto extraible.
Reglas tomadas de bench/salidas-referencia/referencia.json (G1-G4, I1-I10, P1-P8, V*, A*).
"""
import os, re, json, zipfile, subprocess, hashlib

TO = 180  # timeout por sonda, segundos

def run(cmd, timeout=TO, **kw):
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, **kw)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, b"", b"TIMEOUT"
    except FileNotFoundError as e:
        return 127, b"", str(e).encode()

MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"), (b"GIF8", "gif"),
    (b"%PDF", "pdf"), (b"%!PS", "ps"), (b"BM", "bmp"), (b"II*\x00", "tiff"),
    (b"MM\x00*", "tiff"), (b"\x1a\x45\xdf\xa3", "mkv/webm"), (b"OggS", "ogg"),
    (b"fLaC", "flac"), (b"RIFF", "riff"), (b"ID3", "mp3"), (b"\xff\xfb", "mp3"),
    (b"\xff\xf3", "mp3"), (b"\xff\xf2", "mp3"), (b"PK\x03\x04", "zip(ooxml/odf/epub)"),
]

def firma(p):
    with open(p, "rb") as f:
        h = f.read(32)
    for pre, n in MAGIC:
        if h.startswith(pre):
            if n == "riff":
                return "wav" if h[8:12] == b"WAVE" else ("webp" if h[8:12] == b"WEBP" else "avi/riff")
            return n
    if h[4:8] == b"ftyp":
        marca = h[8:12].decode("latin1", "ignore")
        if "avif" in marca or "avis" in marca:
            return "avif"
        if "heic" in marca or "mif1" in marca:
            return "heic"
        return "mp4/mov"
    return "?" + h[:8].hex()

FAM_IMG = {"png", "jpg", "jpeg", "webp", "gif", "tiff", "tif", "bmp", "avif", "ppm", "pnm", "psd", "ico", "pcx"}
FAM_VID = {"mp4", "mkv", "webm", "mov", "avi", "gif"}
FAM_AUD = {"mp3", "wav", "flac", "opus", "ogg", "m4a", "aac"}
FAM_DOC = {"pdf", "docx", "odt", "rtf", "txt", "html", "md", "epub", "xlsx", "csv", "ps", "eps"}
CON_TEXTO = {"pdf", "docx", "odt", "rtf", "txt", "html", "md", "epub", "xlsx", "csv", "ps", "eps", "svg"}

def ext(p):
    return os.path.splitext(p)[1].lstrip(".").lower()

# ------------------------------------------------------------------ texto
def texto(p):
    """Devuelve el texto extraible del fichero (cadena) o '' si no hay."""
    e = ext(p)
    if e in ("txt", "md", "csv", "html", "htm", "xhtml"):
        s = open(p, encoding="utf-8", errors="replace").read()
        if e in ("html", "htm", "xhtml"):
            s = re.sub(r"<[^>]+>", " ", s)
        return s
    if e == "rtf":
        s = open(p, encoding="latin1", errors="replace").read()
        return re.sub(r"\\[a-z]+-?\d*\s?|[{}]", " ", s)
    if e in ("docx", "odt", "xlsx", "epub", "pptx"):
        try:
            with zipfile.ZipFile(p) as z:
                # docProps/* son metadatos del generador ("Normal.dotm Microsoft Office Word"),
                # no contenido del documento: contarlos falsea el umbral de "tiene texto".
                partes = [n for n in z.namelist()
                          if n.endswith((".xml", ".xhtml", ".html")) and "rels" not in n
                          and not n.startswith("docProps/") and "Content_Types" not in n]
                s = ""
                for n in partes:
                    s += re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "replace"))
                return s
        except Exception as ex:
            return ""
    if e in ("pdf", "ps", "eps"):
        sal = p + ".txtwrite.txt"
        rc, o, er = run(["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                         "-sDEVICE=txtwrite", "-sOutputFile=" + sal, p])
        if rc == 0 and os.path.exists(sal):
            s = open(sal, encoding="utf-8", errors="replace").read()
            os.remove(sal)
            return s
        return ""
    return ""

def n_imprimibles(s):
    return len(re.sub(r"\s+", "", "".join(c for c in s if c.isprintable())))

def tiene_texto(p):
    """Regla P6: umbral >= 10 caracteres imprimibles."""
    return n_imprimibles(texto(p)) >= 10

def centinela(p, marca="FILEXSENTINELA7743"):
    t = texto(p)
    # tolera separaciones introducidas por el extractor
    return marca in re.sub(r"\s+", "", t)

# ------------------------------------------------------------------ imagen
def identify(p):
    rc, o, er = run(["magick", "identify", "-quiet", "-format",
                     "%m|%w|%h|%z|%[channels]|%[colorspace]|%k|%x|%y\\n", p])
    if rc != 0:
        return None, er.decode("latin1", "ignore")[:200]
    filas = [l for l in o.decode("latin1", "ignore").strip().splitlines() if l.strip()]
    if not filas:
        return None, "identify vacio"
    c = filas[0].split("|")
    return {"formato": c[0], "w": int(c[1]), "h": int(c[2]), "prof": int(c[3]),
            "canales": c[4], "espacio": c[5], "colores": int(c[6]),
            "dpix": c[7], "dpiy": c[8], "n_imagenes": len(filas)}, ""

def alfa_min(p):
    rc, o, er = run(["magick", p + "[0]", "-alpha", "extract", "-format", "%[fx:minima]", "info:"])
    if rc != 0:
        return None
    try:
        return float(o.decode().strip())
    except Exception:
        return None

def psnr(a, b):
    rc, o, er = run(["magick", "compare", "-metric", "PSNR", a, b, "null:"])
    s = (er or o).decode("latin1", "ignore").strip().split()
    try:
        return float(s[0])
    except Exception:
        return None

# ------------------------------------------------------------------ av
def ffprobe(p):
    rc, o, er = run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                     "-of", "json", p])
    if rc != 0:
        return None, er.decode("latin1", "ignore")[:200]
    try:
        d = json.loads(o.decode("utf-8", "replace"))
    except Exception as e:
        return None, str(e)
    v = [s for s in d.get("streams", []) if s.get("codec_type") == "video"]
    a = [s for s in d.get("streams", []) if s.get("codec_type") == "audio"]
    f = d.get("format", {})
    return {"formato": f.get("format_name"), "dur": float(f.get("duration", 0) or 0),
            "n_v": len(v), "n_a": len(a),
            "codec_v": v[0]["codec_name"] if v else None,
            "codec_a": a[0]["codec_name"] if a else None,
            "w": v[0].get("width") if v else None, "h": v[0].get("height") if v else None,
            "sr": a[0].get("sample_rate") if a else None,
            "canales_a": a[0].get("channels") if a else None,
            "bitrate": f.get("bit_rate")}, ""

def md5_pcm(p, idx=0):
    rc, o, er = run(["ffmpeg", "-v", "error", "-i", p, "-map", f"0:a:{idx}",
                     "-f", "s16le", "-ac", "1", "-ar", "44100", "-"])
    if rc != 0:
        return None
    return hashlib.md5(o).hexdigest()[:12]

def n_paginas_pdf(p):
    rc, o, er = run(["gswin64c", "-q", "-dNODISPLAY", "-dNOSAFER", "-c",
                     f"({p.replace(chr(92), '/')}) (r) file runpdfbegin pdfpagecount = quit"])
    try:
        return int(o.decode().strip())
    except Exception:
        return None

# ------------------------------------------------------------------ caracterizacion completa
def caracteriza(p):
    if not os.path.exists(p):
        return {"existe": False}
    d = {"existe": True, "bytes": os.path.getsize(p), "firma": firma(p), "ext": ext(p)}
    e = d["ext"]
    if e in FAM_IMG and e != "gif":
        d["img"], d["img_err"] = identify(p)
        if d["img"]:
            d["alfa_min"] = alfa_min(p)
    elif e in FAM_VID or e in FAM_AUD:
        d["av"], d["av_err"] = ffprobe(p)
        if e == "gif":
            d["img"], _ = identify(p)
    if e in CON_TEXTO:
        t = texto(p)
        d["chars"] = n_imprimibles(t)
        d["texto"] = d["chars"] >= 10
        d["centinela"] = "FILEXSENTINELA7743" in re.sub(r"\s+", "", t)
        d["tabla"] = bool(re.search(r"AX-1", re.sub(r"\s+", "", t))) and bool(re.search(r"CX-3", re.sub(r"\s+", "", t)))
        if e == "pdf":
            d["paginas"] = n_paginas_pdf(p)
    return d
