# -*- coding: utf-8 -*-
"""Fase 1 - Grafo de conversion.

(a) Reproduce la cifra publicada (152.584 -> 447.398) con las 20 tablas de ConvertX.
(b) Construye el grafo restringido a los motores REALMENTE instalados en esta maquina:
    ffmpeg, ImageMagick (sondeado con `magick -list format`), Ghostscript y Gotenberg.
(c) Separa los pares nuevos de 2-3 saltos en SUSTANTIVOS (ambos extremos son formatos
    que la gente pide, segun las listas por modalidad de SnapOtter) y RUIDO.

Salida: bench/salidas-fidelidad/grafo-resumen.json
"""
import re, os, json, subprocess
from collections import defaultdict

RAIZ = r"D:\Work\research\FileX"
CONV = os.path.join(RAIZ, r"repos\orchestrators\ConvertX\src\converters")
SNAP = os.path.join(RAIZ, r"repos\orchestrators\SnapOtter\packages\shared\src\modality.ts")
GOTEN = os.path.join(RAIZ, r"repos\orchestrators\gotenberg\pkg\modules\libreoffice\api\api.go")

# ---------------------------------------------------------------- parseo ConvertX
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

# ---------------------------------------------------------------- motores locales
def im_real():
    """Formatos que ESTA build de ImageMagick lee / escribe de verdad."""
    out = subprocess.run(["magick", "-list", "format"], capture_output=True, text=True, timeout=60).stdout
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
    out = subprocess.run(["gswin64c", "-h"], capture_output=True, text=True, timeout=60).stdout
    seg = out.split("Available devices:")[1].split("Search path:")[0]
    return set(seg.split())

# Ghostscript: entradas reales del interprete PostScript/PDF, salidas por dispositivo.
GS_IN = {"pdf", "ps", "eps"}
DEV2FMT = {"pdfwrite": "pdf", "ps2write": "ps", "eps2write": "eps", "docxwrite": "docx",
           "txtwrite": "txt", "xpswrite": "xps", "jpeg": "jpg", "jpeggray": "jpg",
           "png16m": "png", "pngalpha": "png", "png256": "png", "pnggray": "png",
           "fpng": "png", "tiff24nc": "tiff", "tiff48nc": "tiff", "tifflzw": "tiff",
           "tiffg4": "tiff", "bmp16m": "bmp", "pcx24b": "pcx", "ppmraw": "ppm",
           "pgmraw": "pgm", "pbmraw": "pbm", "psdrgb": "psd", "pclm": "pclm",
           "hocr": "html", "ocr": "txt", "pdfocr24": "pdf", "pam": "pam"}

def goten_ext():
    txt = open(GOTEN, encoding='utf-8').read()
    seg = txt.split("func (a *Api) Extensions() []string {")[1].split("}")[0]
    return {x.strip().strip('",.').lower() for x in re.findall(r'"\.([a-z0-9]+)"', seg)}

# ---------------------------------------------------------------- popularidad / familias
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

FAM = snap_listas()
POPULAR = set(FAM)

# ---------------------------------------------------------------- grafo
def aristas(mdict):
    E = defaultdict(set)
    for m, (fr, to) in mdict.items():
        for a in {x.lower() for x in fr}:
            for b in {x.lower() for x in to}:
                if a != b:
                    E[(a, b)].add(m)
    return E

def por_saltos(E, maxs=3):
    adj = defaultdict(set)
    for (a, b) in E:
        adj[a].add(b)
    nodos = set(adj) | {b for s in adj.values() for b in s}
    prim = {}   # (a,b) -> primer nº de saltos con que se alcanza
    for o in nodos:
        vis = {o}
        fr = {o}
        for k in range(maxs):
            nueva = set()
            for u in fr:
                nueva |= adj[u]
            nueva -= vis
            vis |= nueva
            fr = nueva
            for v in nueva:
                prim[(o, v)] = k + 1
            if not fr:
                break
    return prim, nodos

def resumen(nombre, E):
    prim, nodos = por_saltos(E)
    c = {k: sum(1 for v in prim.values() if v <= k) for k in (1, 2, 3)}
    print(f"== {nombre} ==  nodos {len(nodos)}  aristas {len(E)}")
    print(f"   1 salto {c[1]}   <=2 {c[2]}   <=3 {c[3]}   multiplicador {c[3]/c[1]:.2f}x")
    return prim, nodos, c

if __name__ == "__main__":
    res = {}

    # (a) grafo completo declarado
    E_all = aristas(MOTORES)
    prim_all, nod_all, c_all = resumen("DECLARADO (20 adaptadores ConvertX)", E_all)

    # (b) grafo instalado
    im_lee, im_esc = im_real()
    devs = gs_devices()
    gs_out = {DEV2FMT[d] for d in devs if d in DEV2FMT}
    lo_in = goten_ext()
    inst = {
        "ffmpeg": MOTORES["ffmpeg"],
        "imagemagick": (im_lee, im_esc),
        "ghostscript": (GS_IN, gs_out),
        "gotenberg-lo": (lo_in, {"pdf"}),
        "gotenberg-chromium": ({"html", "htm", "md", "xhtml", "url"}, {"pdf", "png", "jpeg", "jpg", "webp"}),
    }
    E_i = aristas(inst)
    prim_i, nod_i, c_i = resumen("INSTALADO (ffmpeg, IM sondeado, gs, gotenberg)", E_i)
    for m, (fr, to) in inst.items():
        print(f"     {m}: {len(fr)} entrada / {len(to)} salida")

    # (c) sustantivo vs ruido, sobre el grafo instalado
    nuevos = {p: k for p, k in prim_i.items() if k >= 2}
    sust = {p: k for p, k in nuevos.items() if p[0] in POPULAR and p[1] in POPULAR}
    cruce = {p: k for p, k in sust.items() if FAM.get(p[0]) != FAM.get(p[1])}
    print(f"\n   pares nuevos a >=2 saltos: {len(nuevos)}")
    print(f"   de ellos SUSTANTIVOS (ambos extremos en las listas de SnapOtter): {len(sust)}")
    print(f"   de ellos ademas CRUCE DE FAMILIA: {len(cruce)}")
    print(f"   RUIDO (al menos un extremo fuera del catalogo pedido): {len(nuevos)-len(sust)} "
          f"({100*(len(nuevos)-len(sust))/len(nuevos):.1f} %)")

    # pares populares: cobertura a 1 salto vs multi-salto
    pop_pares = {(a, b) for a in POPULAR for b in POPULAR if a != b}
    p1 = {p for p in pop_pares if prim_i.get(p) == 1}
    p23 = {p for p in pop_pares if prim_i.get(p, 9) in (2, 3)}
    inal = pop_pares - p1 - p23
    print(f"\n   sobre {len(pop_pares)} pares entre formatos populares ({len(POPULAR)} formatos):")
    print(f"     1 salto {len(p1)} | 2-3 saltos {len(p23)} | inalcanzables {len(inal)}")

    # los 3 casos de aceptacion del hito 1
    print("\n   casos de aceptacion del hito 1 (grafo instalado):")
    for a, b in [("epub", "png"), ("docx", "webp"), ("tex", "docx"), ("epub", "docx"),
                 ("xlsx", "png"), ("pptx", "jpg"), ("csv", "png"), ("md", "png"), ("pdf", "docx")]:
        print(f"     {a}->{b}: {prim_i.get((a,b), 'INALCANZABLE')} salto(s)")

    res = {"declarado": c_all, "instalado": c_i,
           "nodos_declarado": len(nod_all), "nodos_instalado": len(nod_i),
           "aristas_declarado": len(E_all), "aristas_instalado": len(E_i),
           "nuevos_multisalto": len(nuevos), "sustantivos": len(sust), "cruce_familia": len(cruce),
           "populares": sorted(POPULAR), "pop_1salto": len(p1), "pop_23salto": len(p23),
           "pop_inalcanzable": len(inal),
           "familias": FAM}
    json.dump(res, open(os.path.join(RAIZ, r"bench\salidas-fidelidad\grafo-resumen.json"), "w"),
              indent=1, ensure_ascii=False)

    # ejemplos concretos de caminos sustantivos de 2-3 saltos, para muestrear
    adj = defaultdict(set)
    for (a, b), ms in E_i.items():
        adj[a].add(b)
    def camino(a, b, maxs=3):
        import heapq
        cola = [(0, a, [a])]
        vis = {a: 0}
        while cola:
            k, u, path = heapq.heappop(cola)
            if u == b:
                return path
            if k == maxs:
                continue
            for v in adj[u]:
                if vis.get(v, 99) > k + 1:
                    vis[v] = k + 1
                    heapq.heappush(cola, (k + 1, v, path + [v]))
        return None
    print("\n   ejemplos de camino:")
    for a, b in sorted(cruce)[:0]:
        pass
    for a, b in [("epub", "png"), ("docx", "webp"), ("xlsx", "png"), ("csv", "png"),
                 ("pdf", "docx"), ("md", "jpg"), ("mp4", "pdf"), ("psd", "pdf"),
                 ("epub", "txt"), ("html", "webp"), ("rtf", "png"), ("odt", "jpg")]:
        print(f"     {a}->{b}: {camino(a,b)}")
