"""Verificacion de salidas en disco: bytes magicos + sonda del formato.

El diferenciador n.1 de FileX es la verificacion obligatoria de la salida.
Aqui se aplica a los propios MCP de referencia: si un servidor dice haber
escrito un fichero, se comprueba (a) que existe, (b) que sus bytes magicos
corresponden al formato que la extension promete, y (c) que ffprobe/magick
lo abren y declaran el mismo formato.

Uso:  python verificar_salidas.py <dir1> [dir2 ...]
"""

import json
import os
import subprocess
import sys

# (offset, firma, etiqueta). Firmas en bytes crudos.
FIRMAS = [
    (0, b"\x89PNG\r\n\x1a\n", "png"),
    (0, b"\xff\xd8\xff", "jpeg"),
    (0, b"GIF87a", "gif"),
    (0, b"GIF89a", "gif"),
    (0, b"ID3", "mp3"),
    (0, b"\xff\xfb", "mp3"),
    (0, b"\xff\xf3", "mp3"),
    (0, b"\xff\xf2", "mp3"),
    (0, b"fLaC", "flac"),
    (0, b"OggS", "ogg"),
    (0, b"\x1a\x45\xdf\xa3", "matroska/webm"),
    (0, b"RIFF", "riff(wav/webp/avi)"),
]

# Que extension deberia dar que formato sondeado.
ESPERADO = {
    ".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp",
    ".gif": "gif", ".avif": "avif", ".mp3": "mp3", ".flac": "flac",
    ".wav": "wav", ".webm": "webm", ".mkv": "matroska", ".mp4": "mp4",
    ".ogg": "ogg", ".m4a": "m4a",
}

IMAGENES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".tif", ".tiff"}


def magico(ruta):
    with open(ruta, "rb") as f:
        cab = f.read(32)
    hits = [et for off, fir, et in FIRMAS if cab[off:off + len(fir)] == fir]
    if cab[0:4] == b"RIFF":
        sub = cab[8:12]
        if sub == b"WEBP":
            hits = ["webp"]
        elif sub == b"WAVE":
            hits = ["wav"]
    if cab[4:8] == b"ftyp":
        marca = cab[8:12].decode("ascii", "replace")
        hits.append("isobmff/" + marca)
    return (hits or ["DESCONOCIDO"]), cab[:16].hex()


def sondear(ruta):
    """Devuelve (formato_declarado, detalle) usando magick o ffprobe."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext in IMAGENES:
        try:
            r = subprocess.run(
                ["magick", "identify", "-format", "%m|%wx%h", ruta],
                capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                return r.stdout.strip().lower().split("|")[0], r.stdout.strip()
            return "ERROR", (r.stderr or "").strip()[:200]
        except Exception as e:
            return "ERROR", str(e)[:200]
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=format_name,duration,size:stream=codec_name,codec_type",
             "-of", "json", ruta],
            capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            return "ERROR", (r.stderr or "").strip()[:300]
        j = json.loads(r.stdout)
        fmt = j.get("format", {}).get("format_name", "?")
        cods = ",".join(
            "{}:{}".format(s.get("codec_type"), s.get("codec_name"))
            for s in j.get("streams", []))
        dur = j.get("format", {}).get("duration", "?")
        return fmt, "{} | dur={} | {}".format(fmt, dur, cods)
    except Exception as e:
        return "ERROR", str(e)[:200]


def veredicto(ext, hits, fmt):
    esp = ESPERADO.get(ext)
    if fmt == "ERROR":
        return "NO_ABRE"
    if esp is None:
        return "SIN_REFERENCIA"
    ok_sonda = esp in fmt.lower() or fmt.lower() in esp
    # matroska/webm comparten contenedor
    if ext == ".webm" and "matroska" in fmt.lower():
        ok_sonda = True
    if ext == ".mkv" and "webm" in fmt.lower():
        ok_sonda = True
    if ext == ".mp4" and ("mov" in fmt.lower() or "mp4" in fmt.lower()):
        ok_sonda = True
    ok_magico = any(esp in h or h in esp or
                    (ext in (".mp4", ".m4a") and h.startswith("isobmff"))
                    for h in hits)
    if ok_sonda and ok_magico:
        return "OK"
    if ok_sonda and not ok_magico:
        return "OK_SONDA_MAGICO_RARO"
    return "MIENTE"


def main(dirs):
    filas = []
    for d in dirs:
        if not os.path.isdir(d):
            print("(no existe)", d)
            continue
        for nom in sorted(os.listdir(d)):
            ruta = os.path.join(d, nom)
            if not os.path.isfile(ruta):
                continue
            ext = os.path.splitext(nom)[1].lower()
            if ext in (".json", ".log", ".py", ".md", ".txt"):
                continue
            tam = os.path.getsize(ruta)
            hits, cab = magico(ruta)
            fmt, det = sondear(ruta)
            v = veredicto(ext, hits, fmt)
            filas.append({
                "fichero": nom, "dir": d, "bytes": tam,
                "magico": "/".join(hits), "cabecera_hex": cab,
                "formato_sondeado": fmt, "detalle": det, "veredicto": v,
            })
            print("{:<34} {:>10} b  magico={:<18} sonda={:<22} -> {}".format(
                nom[:34], tam, "/".join(hits)[:18], fmt[:22], v))
    with open(os.path.join(dirs[0], "..", "verificacion.json"), "w",
              encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=2)
    print("\n-- resumen --")
    for v in sorted(set(f["veredicto"] for f in filas)):
        print("  {}: {}".format(v, sum(1 for f in filas if f["veredicto"] == v)))


if __name__ == "__main__":
    main(sys.argv[1:])
