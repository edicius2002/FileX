# -*- coding: utf-8 -*-
"""E1 / Nivel 1 - CENSO DE CAPACIDADES (exacto, no muestreado).

Pregunta: de las 138.501 aristas del grafo INSTALADO de bench/fidelidad-caminos.md
sec.1.2, cuantas tienen un extremo que el binario NO reconoce en ejecucion?

Metodo: sondear capacidades EN EJECUCION, no deducirlas (CLAUDE.md sec.5).
 - ffmpeg: `-demuxers` / `-muxers` da los NOMBRES; `-h demuxer=N` / `-h muxer=N` da
   la linea "Common extensions:". La union de ambos es el conjunto real de tokens
   que ffmpeg reconoce. La tabla de ConvertX se compara contra ese conjunto.
 - ImageMagick: `magick -list format` (ya lo hacia _grafo.py de fidelidad-caminos).
 - Ghostscript: `gswin64c -h` -> dispositivos disponibles.
 - Gotenberg: no hay sonda de nombre; queda entero para el nivel 2.

Escribe bench/salidas-aristas/censo.json
"""
import re, os, json, subprocess, sys
from collections import defaultdict

RAIZ = r"D:\Work\research\FileX"
CONV = os.path.join(RAIZ, r"repos\orchestrators\ConvertX\src\converters")
SNAP = os.path.join(RAIZ, r"repos\orchestrators\SnapOtter\packages\shared\src\modality.ts")
GOTEN = os.path.join(RAIZ, r"repos\orchestrators\gotenberg\pkg\modules\libreoffice\api\api.go")
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")

DEVNULL = subprocess.DEVNULL


def corre(args, timeout=30):
    """Proceso separado, sin shell, stdin=DEVNULL primero (CLAUDE.md sec.5)."""
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT"
    except FileNotFoundError:
        return -127, "NOEXISTE"


# ------------------------------------------------- parseo ConvertX (igual que _grafo.py)
def bloque(txt, clave):
    m = re.search(clave + r"\s*:\s*\{", txt)
    if not m:
        return ""
    i = m.end() - 1
    d = 0
    for j in range(i, len(txt)):
        if txt[j] == '{':
            d += 1
        elif txt[j] == '}':
            d -= 1
            if d == 0:
                return txt[i:j + 1]
    return ""


PAT = r'"([A-Za-z0-9_.+/-]{1,40})"'


def props(f):
    txt = open(f, encoding='utf-8').read()
    m = re.search(r"export const properties\s*(?::\s*\w+)?\s*=\s*\{", txt)
    if not m:
        return set(), set()
    i = m.end() - 1
    d = 0
    blk = ""
    for j in range(i, len(txt)):
        if txt[j] == '{':
            d += 1
        elif txt[j] == '}':
            d -= 1
            if d == 0:
                blk = txt[i:j + 1]
                break
    return set(re.findall(PAT, bloque(blk, "from"))), set(re.findall(PAT, bloque(blk, "to")))


MOTORES = {}
for fn in sorted(os.listdir(CONV)):
    if fn.endswith(".ts") and fn not in ("main.ts", "types.ts"):
        fr, to = props(os.path.join(CONV, fn))
        if fr or to:
            MOTORES[fn[:-3]] = (fr, to)


# ------------------------------------------------- sondas de capacidad
def ff_listas(cual):
    """cual = 'demuxers' | 'muxers'. Devuelve (nombres, extensiones)."""
    rc, out = corre(["ffmpeg", "-hide_banner", "-" + cual], 60)
    nombres = set()
    for ln in out.splitlines():
        m = re.match(r"^\s*[DE ]{1,2}\s+([A-Za-z0-9_,.+-]+)\s+\S", ln)
        if m and ln.strip() and not ln.startswith("---"):
            for n in m.group(1).split(","):
                if n and n not in ("File", "formats:"):
                    nombres.add(n.lower())
    sing = "demuxer" if cual == "demuxers" else "muxer"
    # los demuxers de imagen se llaman "png_pipe", "bmp_pipe"...: el token que usa
    # ConvertX es la raiz. Sin esto el cribado da 20 falsos positivos.
    for n in list(nombres):
        if n.endswith("_pipe"):
            nombres.add(n[:-5])
    exts = set()
    for n in sorted(nombres):
        rc2, o2 = corre(["ffmpeg", "-hide_banner", "-h", sing + "=" + n], 20)
        m = re.search(r"Common extensions:\s*([^\.\n]+)", o2)
        if m:
            for e in m.group(1).split(","):
                e = e.strip().lower()
                if e:
                    exts.add(e)
        m2 = re.search(r"Mime type:\s*([^\.\n]+)", o2)
    return nombres, exts


def im_real():
    rc, out = corre(["magick", "-list", "format"], 60)
    lee, esc = set(), set()
    for ln in out.splitlines()[2:]:
        p = ln.split()
        if len(p) < 3:
            continue
        f = p[0].rstrip('*').lower()
        modo = p[2]
        if not re.fullmatch(r"[r-][w-][+-]", modo):
            continue
        if modo[0] == 'r':
            lee.add(f)
        if modo[1] == 'w':
            esc.add(f)
    return lee, esc


def gs_devices():
    rc, out = corre(["gswin64c", "-h"], 60)
    seg = out.split("Available devices:")[1].split("Search path:")[0]
    return set(seg.split())


DEV2FMT = {"pdfwrite": "pdf", "ps2write": "ps", "eps2write": "eps", "docxwrite": "docx",
           "txtwrite": "txt", "xpswrite": "xps", "jpeg": "jpg", "jpeggray": "jpg",
           "png16m": "png", "pngalpha": "png", "png256": "png", "pnggray": "png",
           "fpng": "png", "tiff24nc": "tiff", "tiff48nc": "tiff", "tifflzw": "tiff",
           "tiffg4": "tiff", "bmp16m": "bmp", "pcx24b": "pcx", "ppmraw": "ppm",
           "pgmraw": "pgm", "pbmraw": "pbm", "psdrgb": "psd", "pclm": "pclm",
           "hocr": "html", "ocr": "txt", "pdfocr24": "pdf", "pam": "pam"}
GS_IN = {"pdf", "ps", "eps"}


def goten_ext():
    txt = open(GOTEN, encoding='utf-8').read()
    seg = txt.split("func (a *Api) Extensions() []string {")[1].split("}")[0]
    return {x.strip().strip('",.').lower() for x in re.findall(r'"\.([a-z0-9]+)"', seg)}


def snap_listas():
    t = open(SNAP, encoding='utf-8').read()
    fam = {}
    for nombre, f in [("IMAGE_INPUTS", "imagen"), ("VIDEO_INPUTS", "video"),
                      ("AUDIO_INPUTS", "audio"), ("SUBTITLE_INPUTS", "subtitulo"),
                      ("DOCUMENT_INPUTS", "documento"), ("FILE_INPUTS", "datos")]:
        seg = t.split(nombre)[1].split("]")[0]
        for e in re.findall(r'"\.([a-z0-9]+)"', seg):
            fam.setdefault(e, f)
    return fam


def aristas(mdict):
    E = defaultdict(set)
    for m, (fr, to) in mdict.items():
        for a in {x.lower() for x in fr}:
            for b in {x.lower() for x in to}:
                if a != b:
                    E[(a, b)].add(m)
    return E


if __name__ == "__main__":
    print("sondeando ffmpeg (demuxers)...", flush=True)
    dem_n, dem_e = ff_listas("demuxers")
    print("sondeando ffmpeg (muxers)...", flush=True)
    mux_n, mux_e = ff_listas("muxers")
    # dispositivos (lavfi, gdigrab, dshow...): ConvertX los declara como "formatos"
    rc, odev = corre(["ffmpeg", "-hide_banner", "-devices"], 30)
    dev_d, dev_e = set(), set()
    for ln in odev.splitlines():
        m = re.match(r"^\s*([D ])([E ])\s+([A-Za-z0-9_]+)\s+\S", ln)
        if m:
            if m.group(1) == "D":
                dev_d.add(m.group(3).lower())
            if m.group(2) == "E":
                dev_e.add(m.group(3).lower())
    print(f"  ffmpeg: dispositivos D={len(dev_d)} E={len(dev_e)}")
    ff_in_real = dem_n | dem_e | dev_d
    ff_out_real = mux_n | mux_e | dev_e
    # pseudoformatos "codec.contenedor" de ConvertX (ffmpeg.ts:711-714): av1.mkv,
    # h264.mp4... NO son nombres de muxer y ConvertX los descompone en codigo.
    # Estan vivos si el contenedor lo esta.
    ff_out_real |= {t for t in {x.lower() for x in MOTORES["ffmpeg"][1]}
                    if "." in t and t.split(".")[-1] in ff_out_real}
    print(f"  ffmpeg: {len(dem_n)} demuxers ({len(dem_e)} ext) -> {len(ff_in_real)} tokens de entrada")
    print(f"  ffmpeg: {len(mux_n)} muxers   ({len(mux_e)} ext) -> {len(ff_out_real)} tokens de salida")

    ff_decl_in, ff_decl_out = MOTORES["ffmpeg"]
    ff_decl_in = {x.lower() for x in ff_decl_in}
    ff_decl_out = {x.lower() for x in ff_decl_out}
    ff_in_muertos = sorted(ff_decl_in - ff_in_real)
    ff_out_muertos = sorted(ff_decl_out - ff_out_real)
    print(f"  declarados por ConvertX: {len(ff_decl_in)} in / {len(ff_decl_out)} out")
    print(f"  DESCONOCIDOS por el binario: {len(ff_in_muertos)} in / {len(ff_out_muertos)} out")

    im_lee, im_esc = im_real()
    devs = gs_devices()
    gs_out = {DEV2FMT[d] for d in devs if d in DEV2FMT}
    lo_in = goten_ext()

    # --- grafo A: el "instalado" de fidelidad-caminos sec.1.2 (ffmpeg SIN sondear)
    instA = {
        "ffmpeg": (ff_decl_in, ff_decl_out),
        "imagemagick": (im_lee, im_esc),
        "ghostscript": (GS_IN, gs_out),
        "gotenberg-lo": (lo_in, {"pdf"}),
        "gotenberg-chromium": ({"html", "htm", "md", "xhtml", "url"}, {"pdf", "png", "jpeg", "jpg", "webp"}),
    }
    EA = aristas(instA)

    # --- grafo B: el mismo, con ffmpeg TAMBIEN sondeado en ejecucion
    instB = dict(instA)
    instB["ffmpeg"] = (ff_decl_in & ff_in_real, ff_decl_out & ff_out_real)
    EB = aristas(instB)

    print(f"\n  aristas grafo A (ffmpeg declarado)  : {len(EA)}")
    print(f"  aristas grafo B (ffmpeg sondeado)   : {len(EB)}")
    print(f"  aristas muertas por nombre          : {len(EA)-len(EB)}  ({100*(len(EA)-len(EB))/len(EA):.2f} %)")

    FAM = snap_listas()
    res = {
        "ffmpeg": {
            "demuxer_nombres": len(dem_n), "demuxer_extensiones": len(dem_e),
            "muxer_nombres": len(mux_n), "muxer_extensiones": len(mux_e),
            "declarado_in": len(ff_decl_in), "declarado_out": len(ff_decl_out),
            "vivos_in": len(ff_decl_in & ff_in_real), "vivos_out": len(ff_decl_out & ff_out_real),
            "muertos_in": ff_in_muertos, "muertos_out": ff_out_muertos,
        },
        "imagemagick": {"lee": len(im_lee), "escribe": len(im_esc)},
        "ghostscript": {"dispositivos": len(devs), "salidas_mapeadas": sorted(gs_out)},
        "gotenberg_lo_ext": sorted(lo_in),
        "aristas_A": len(EA), "aristas_B": len(EB),
        "aristas_muertas_nombre": len(EA) - len(EB),
        "familias": FAM,
    }
    json.dump(res, open(os.path.join(SAL, "censo.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    # volcado de las aristas de los dos grafos para el muestreo del nivel 2
    json.dump({"A": sorted(["%s>%s|%s" % (a, b, ",".join(sorted(m))) for (a, b), m in EA.items()]),
               "B": sorted(["%s>%s|%s" % (a, b, ",".join(sorted(m))) for (a, b), m in EB.items()])},
              open(os.path.join(SAL, "aristas.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("\nescrito censo.json y aristas.json")
