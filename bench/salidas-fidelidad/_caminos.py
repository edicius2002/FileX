# -*- coding: utf-8 -*-
"""Fase 2 - ejecuta la muestra de caminos y caracteriza cada salida intermedia y final."""
import os, sys, json, time, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _sonda import run, caracteriza, psnr, md5_pcm, ext

RAIZ = r"D:\Work\research\FileX"
COR = os.path.join(RAIZ, "corpus")
ENT = os.path.join(RAIZ, r"bench\salidas-fidelidad\entradas")
OUT = os.path.join(RAIZ, r"bench\salidas-fidelidad\salidas")
os.makedirs(OUT, exist_ok=True)
GOTEN = "http://localhost:3200"
TO = 240

# ------------------------------------------------------------------ motores
def im(src, dst, extra=()):
    return run(["magick"] + list(extra[:0]) + [src] + list(extra) + [dst], timeout=TO)

def im_pre(src, dst, pre=(), post=()):
    return run(["magick"] + list(pre) + [src] + list(post) + [dst], timeout=TO)

def ff(src, dst, extra=()):
    return run(["ffmpeg", "-y", "-v", "error", "-threads", "4", "-i", src] + list(extra) + [dst],
               timeout=TO)

ENV_GS = dict(os.environ, TESSDATA_PREFIX=r"C:\Program Files\Tesseract-OCR\tessdata")

def gs(src, dst, dev, extra=()):
    return run(["gswin64c", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=" + dev]
               + list(extra) + ["-sOutputFile=" + dst, src], timeout=TO, env=ENV_GS)

def gt_lo(src, dst, extra=()):
    cmd = ["curl", "-s", "--max-time", "180", "-o", dst, "-w", "%{http_code}",
           "-F", "files=@" + src] + list(extra) + [GOTEN + "/forms/libreoffice/convert"]
    rc, o, er = run(cmd, timeout=TO)
    cod = o.decode().strip()[-3:]
    return (0 if cod == "200" else 1), o, (b"HTTP " + cod.encode())

def gt_html(src, dst, extra=()):
    d = os.path.join(OUT, "_gt"); os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "index.html")
    shutil.copy(src, tmp)
    cmd = ["curl", "-s", "--max-time", "180", "-o", dst, "-w", "%{http_code}",
           "-F", "files=@" + tmp] + list(extra) + [GOTEN + "/forms/chromium/convert/html"]
    rc, o, er = run(cmd, timeout=TO)
    cod = o.decode().strip()[-3:]
    return (0 if cod == "200" else 1), o, (b"HTTP " + cod.encode())

def gt_shot(src, dst, fmt):
    d = os.path.join(OUT, "_gt"); os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "index.html")
    shutil.copy(src, tmp)
    cmd = ["curl", "-s", "--max-time", "180", "-o", dst, "-w", "%{http_code}",
           "-F", "files=@" + tmp, "-F", "format=" + fmt,
           GOTEN + "/forms/chromium/screenshot/html"]
    rc, o, er = run(cmd, timeout=TO)
    cod = o.decode().strip()[-3:]
    return (0 if cod == "200" else 1), o, (b"HTTP " + cod.encode())

def gt_md(src, dst):
    d = os.path.join(OUT, "_gt"); os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "index.html")
    nom = os.path.basename(src)
    open(tmp, "w", encoding="utf-8").write(
        "<!doctype html><html><head><meta charset='utf-8'><title>md</title></head>"
        "<body>{{ toHTML \"" + nom + "\" }}</body></html>")
    cmd = ["curl", "-s", "--max-time", "180", "-o", dst, "-w", "%{http_code}",
           "-F", "files=@" + tmp, "-F", "files=@" + src,
           GOTEN + "/forms/chromium/convert/markdown"]
    rc, o, er = run(cmd, timeout=TO)
    cod = o.decode().strip()[-3:]
    return (0 if cod == "200" else 1), o, (b"HTTP " + cod.encode())

MOTOR = {
    "im": lambda s, d, a: im_pre(s + a.get("sel", ""), d, a.get("pre", ()), a.get("post", ())),
    "ff": lambda s, d, a: ff(s, d, a.get("extra", ())),
    "gs": lambda s, d, a: gs(s, d, a["dev"], a.get("extra", ())),
    "gt-lo": lambda s, d, a: gt_lo(s, d, a.get("extra", ())),
    "gt-html": lambda s, d, a: gt_html(s, d, a.get("extra", ())),
    "gt-shot": lambda s, d, a: gt_shot(s, d, a["fmt"]),
    "gt-md": lambda s, d, a: gt_md(s, d),
}

# ------------------------------------------------------------------ atajos
P150 = {"dev": "png16m", "extra": ["-r150"]}
J150 = {"dev": "jpeg", "extra": ["-r150", "-dJPEGQ=85"]}
PDFW = {"dev": "pdfwrite"}
TXTW = {"dev": "txtwrite"}
DOCXW = {"dev": "docxwrite"}
OCR = {"dev": "ocr"}
PDFOCR = {"dev": "pdfocr24", "extra": ["-r150"]}
IMD = {"pre": ["-density", "150"]}

def C(cid, entrada, pasos, estrato, nota=""):
    return {"id": cid, "entrada": entrada, "pasos": pasos, "estrato": estrato, "nota": nota}

I = lambda n: os.path.join(COR, "imagen", n)
V = lambda n: os.path.join(COR, "video", n)
A = lambda n: os.path.join(COR, "audio", n)
D = lambda n: os.path.join(COR, "pdf", n)
E = lambda n: os.path.join(ENT, n)

CAMINOS = [
    # ---- A. control: misma familia (imagen -> imagen [-> imagen])
    C("A1", I("tipico.png"), [("im", "webp", {}), ("im", "png", {})], "control-imagen"),
    C("A2", I("tipico.png"), [("im", "jpg", {"post": ["-quality", "85"]}), ("im", "png", {})], "control-imagen"),
    C("A3", I("patologico_16bit.tif"), [("im", "png", {}), ("im", "tif", {})], "control-imagen"),
    C("A4", I("patologico_16bit.tif"), [("im", "webp", {}), ("im", "png", {})], "control-imagen"),
    C("A5", I("alpha.png"), [("im", "webp", {}), ("im", "png", {})], "control-imagen"),
    C("A6", I("alpha.png"), [("im", "jpg", {"post": ["-quality", "85"]}), ("im", "png", {})], "control-imagen"),
    C("A7", I("tipico.png"), [("im", "avif", {}), ("im", "png", {}), ("im", "webp", {})], "control-imagen"),
    C("A8", I("tipico.png"), [("im", "bmp", {}), ("im", "gif", {}), ("im", "png", {})], "control-imagen",
      "3 saltos con paleta intermedia"),

    # ---- B. documento -> imagen (cruce de familia con rasterizacion)
    C("B1", E("entrada.epub"), [("gt-lo", "pdf", {}), ("gs", "png", P150)], "doc-a-imagen", "caso hito 1: epub->png"),
    C("B2", E("entrada.docx"), [("gt-lo", "pdf", {}), ("im", "webp", IMD)], "doc-a-imagen", "caso hito 1: docx->webp"),
    C("B3", E("entrada.html"), [("gt-html", "pdf", {}), ("gs", "png", P150)], "doc-a-imagen"),
    C("B4", E("entrada.md"), [("gt-md", "pdf", {}), ("gs", "jpg", J150)], "doc-a-imagen"),
    C("B5", E("entrada.csv"), [("gt-lo", "pdf", {}), ("gs", "png", P150)], "doc-a-imagen", "tabular->imagen"),
    C("B6", E("entrada.xlsx"), [("gt-lo", "pdf", {}), ("gs", "png", P150)], "doc-a-imagen", "tabular->imagen"),
    C("B7", E("entrada.rtf"), [("gt-lo", "pdf", {}), ("im", "png", IMD)], "doc-a-imagen"),
    C("B8", E("entrada.odt"), [("gt-lo", "pdf", {}), ("gs", "jpg", J150)], "doc-a-imagen"),

    # ---- C. documento -> documento pasando (o no) por rasterizacion
    C("C1", E("entrada.epub"), [("gt-lo", "pdf", {}), ("gs", "txt", TXTW)], "doc-a-doc", "conserva texto"),
    C("C2", E("entrada.docx"), [("gt-lo", "pdf", {}), ("gs", "docx", DOCXW)], "doc-a-doc", "docx->pdf->docx"),
    C("C3", E("entrada.docx"), [("gt-lo", "pdf", {}), ("gs", "png", P150), ("im", "pdf", {})], "doc-a-doc",
      "3 saltos que rasterizan: el caso del aviso"),
    C("C4", E("entrada.docx"), [("gt-lo", "pdf", {}), ("gs", "png", P150), ("im", "pdf", {}),
                                ("gs", "txt", TXTW)], "doc-a-doc",
      "orden importa: rasterizar antes de extraer texto (4 saltos)"),
    C("C5", E("entrada.xlsx"), [("gt-lo", "pdf", {}), ("gs", "docx", DOCXW)], "doc-a-doc", "tabla->docx"),
    C("C6", D("tipico_texto.pdf"), [("gs", "png", P150), ("im", "pdf", {})], "doc-a-doc",
      "control conocido de la referencia: PDF->PNG->PDF"),
    C("C7", D("tipico_texto.pdf"), [("gs", "pdf", PDFW), ("gs", "docx", DOCXW)], "doc-a-doc"),
    C("C8", E("entrada.html"), [("gt-shot", "png", {"fmt": "png"}), ("im", "pdf", {})], "doc-a-doc",
      "captura de pantalla -> PDF"),
    C("C9", E("entrada.epub"), [("gt-lo", "pdf", {}), ("gs", "docx", DOCXW)], "doc-a-doc", "epub->docx"),

    # ---- D. imagen -> documento
    C("D1", I("tipico.png"), [("im", "pdf", {}), ("gs", "txt", TXTW)], "imagen-a-doc",
      "trampa txtwrite: basura de 1-3 chars"),
    C("D2", I("patologico_16bit.tif"), [("im", "pdf", {}), ("gs", "png", P150)], "imagen-a-doc",
      "profundidad a traves de PDF"),
    C("D3", I("tipico.jpg"), [("im", "pdf", {"pre": ["-density", "150", "-units", "PixelsPerInch"]}),
                              ("gs", "pdf", PDFW)], "imagen-a-doc"),
    C("D4", I("alpha.png"), [("im", "pdf", {}), ("gs", "png", P150)], "imagen-a-doc", "alfa a traves de PDF"),

    # ---- E. video -> imagen / video -> video
    C("E1", V("tipico.mp4"), [("ff", "gif", {"extra": ["-vf", "fps=12,scale=320:-1", "-t", "3"]}),
                              ("im", "png", {"sel": "[0]"})], "video-a-imagen"),
    C("E2", V("tipico.mp4"), [("ff", "png", {"extra": ["-frames:v", "1"]}), ("im", "webp", {})], "video-a-imagen"),
    C("E3", V("patologico_2pistas.mkv"), [("ff", "mp4", {"extra": ["-c", "copy"]}),
                                          ("ff", "mkv", {"extra": ["-c", "copy"]})], "video-a-video",
      "remux ida y vuelta con -c copy"),
    C("E4", V("patologico_2pistas.mkv"), [("ff", "mp4", {}), ("ff", "mkv", {})], "video-a-video",
      "invocacion ingenua: pierde la 2a pista"),
    C("E5", V("patologico_2pistas.mkv"), [("ff", "webm", {"extra": ["-c:v", "libvpx-vp9", "-crf", "40",
                                                                    "-b:v", "0", "-c:a", "libopus", "-t", "3"]}),
                                          ("ff", "mp4", {})], "video-a-video"),
    C("E6", V("trivial.mp4"), [("ff", "gif", {"extra": ["-vf", "fps=12", "-t", "3"]}),
                               ("ff", "mp4", {})], "video-a-video", "video->gif->video"),
    C("E7", V("tipico.mp4"), [("ff", "mp3", {"extra": ["-vn", "-b:a", "192k"]}),
                              ("ff", "wav", {})], "video-a-audio"),

    # ---- F. audio
    C("F1", A("tipico.flac"), [("ff", "wav", {}), ("ff", "mp3", {"extra": ["-b:a", "192k"]})], "audio"),
    C("F2", A("tipico.flac"), [("ff", "opus", {"extra": ["-c:a", "libopus", "-b:a", "96k"]}),
                               ("ff", "wav", {})], "audio", "Opus fuerza 48 kHz"),
    C("F3", A("tipico.mp3"), [("ff", "flac", {}), ("ff", "wav", {})], "audio"),
    C("F4", A("trivial.wav"), [("ff", "mp3", {"extra": ["-b:a", "192k"]}), ("ff", "flac", {})], "audio",
      "sin perdida despues de con perdida"),

    # ---- G. el orden importa (A->B->C frente a A->C)
    C("G1", I("patologico_16bit.tif"), [("im", "png", {})], "orden", "directo, 1 salto"),
    C("G2", I("patologico_16bit.tif"), [("im", "jpg", {"post": ["-quality", "85"]}), ("im", "png", {})],
      "orden", "el mismo destino via JPEG"),
    C("G3", D("tipico_texto.pdf"), [("gs", "txt", TXTW)], "orden", "directo, 1 salto"),
    C("G4", D("tipico_texto.pdf"), [("gs", "png", P150), ("im", "pdf", {}), ("gs", "txt", TXTW)], "orden",
      "el mismo destino via PNG (3 saltos)"),
    C("G5", V("patologico_2pistas.mkv"), [("ff", "mp4", {"extra": ["-map", "0", "-c", "copy"]})], "orden",
      "directo con -map 0 -c copy"),

    # ---- H. aristas nominales sospechosas (1 salto declarado por la tabla)
    C("H1", V("tipico.mp4"), [("im", "pdf", {})], "nominal", "ImageMagick declara leer mp4"),
    C("H2", E("entrada.txt"), [("im", "png", {})], "nominal", "ImageMagick declara leer txt"),
    C("H3", I("tipico.png"), [("ff", "webp", {})], "nominal", "ffmpeg como conversor de imagen"),
    C("H4", D("tipico_texto.pdf"), [("im", "txt", IMD)], "nominal",
      "ImageMagick declara escribir txt: en realidad vuelca pixeles"),

    # ---- I. aristas de reparacion (OCR) y parametrizacion del motor
    C("I1", D("tipico_texto.pdf"), [("gs", "png", P150), ("im", "pdf", {}), ("gs", "txt", OCR)], "reparacion",
      "rasterizar y recuperar el texto con OCR (3 saltos)"),
    C("I2", E("entrada.docx"), [("gt-lo", "pdf", {}), ("gs", "png", P150), ("im", "pdf", {}),
                                ("gs", "pdf", PDFOCR)],
      "reparacion", "docx->pdf->png->pdf con capa de texto reconstruida por OCR (4 saltos)"),
    C("I3", I("trivial.png"), [("im", "webp", {"post": ["-quality", "80"]})], "parametro",
      "grafismo con perdida (malo)"),
    C("I4", I("trivial.png"), [("im", "webp", {"post": ["-define", "webp:lossless=true"]})], "parametro",
      "el mismo par, sin perdida (bueno y mas pequeno)"),
    C("I5", I("tipico.png"), [("im", "pdf", {})], "parametro", "sin densidad declarada (regla P7)"),
    C("I6", I("tipico.png"), [("im", "pdf", {"pre": ["-density", "150", "-units", "PixelsPerInch"]})],
      "parametro", "con densidad declarada"),
    C("I7", I("alpha.png"), [("im", "jpg", {"post": ["-quality", "85"]})], "parametro",
      "aplanado sobre negro (regla I3)"),
    C("I8", I("alpha.png"), [("im", "jpg", {"pre": ["-background", "white"],
                                            "post": ["-alpha", "remove", "-quality", "85"]})], "parametro",
      "aplanado sobre blanco"),

    # ---- J. controles de 1 salto y casos donde el camino largo GANA
    C("J1", V("tipico.mp4"), [("ff", "wav", {})], "control-1salto", "control de E7"),
    C("J2", A("trivial.wav"), [("ff", "flac", {})], "control-1salto", "control de F4"),
    C("J3", E("entrada.docx"), [("gt-lo", "pdf", {})], "control-1salto", "control de B2/C3"),
    C("J4", D("tipico_texto.pdf"), [("gs", "pdf", PDFW)], "control-1salto", "control de C6"),
    C("J5", D("tipico_texto.pdf"), [("gs", "docx", DOCXW)], "control-1salto", "control de C7"),
    C("J6", E("entrada.xlsx"), [("gt-lo", "pdf", {}), ("gs", "txt", TXTW)], "doc-a-doc",
      "sobrevive la tabla como texto?"),
    C("J7", E("entrada.csv"), [("gt-lo", "pdf", {}), ("gs", "docx", DOCXW)], "doc-a-doc",
      "tabular -> documento"),
    C("J8", D("patologico_escaneado.pdf"), [("gs", "txt", TXTW)], "orden",
      "PDF escaneado -> txt por extraccion: no hay nada que extraer"),
    C("J9", D("patologico_escaneado.pdf"), [("gs", "txt", OCR)], "orden",
      "el mismo par por OCR: la misma arista con otro coste"),
    C("J10", D("patologico_escaneado.pdf"), [("gs", "docx", DOCXW)], "reparacion",
      "1 salto: docx sin texto"),
    C("J11", D("patologico_escaneado.pdf"), [("gs", "pdf", PDFOCR), ("gs", "docx", DOCXW)], "reparacion",
      "2 saltos con OCR intermedio: el camino largo GANA"),
    C("J12", V("tipico.mp4"), [("ff", "gif", {"extra": ["-vf", "fps=12,scale=320:-1", "-t", "3"]})],
      "control-1salto", "control de E1"),
]

def ejecutar(c):
    reg = {"id": c["id"], "estrato": c["estrato"], "nota": c["nota"],
           "entrada": os.path.relpath(c["entrada"], RAIZ), "pasos": [], "ok": True}
    reg["car_entrada"] = caracteriza(c["entrada"])
    src = c["entrada"]
    for i, (motor, fmt, args) in enumerate(c["pasos"], 1):
        dst = os.path.join(OUT, f"{c['id']}_p{i}.{fmt}")
        t0 = time.time()
        rc, o, er = MOTOR[motor](src, dst, args)
        dt = time.time() - t0
        paso = {"n": i, "motor": motor, "destino": fmt, "args": {k: list(v) if isinstance(v, (list, tuple)) else v
                                                                for k, v in args.items()},
                "rc": rc, "ms": int(dt * 1000),
                "stderr": er.decode("latin1", "ignore")[:300].strip(),
                "salida": os.path.basename(dst)}
        existe = os.path.exists(dst) and (os.path.getsize(dst) > 0 or fmt == "txt")
        if rc != 0 or not existe:
            paso["fallo"] = True
            reg["ok"] = False
            reg["pasos"].append(paso)
            break
        paso["car"] = caracteriza(dst)
        reg["pasos"].append(paso)
        src = dst
    reg["final"] = reg["pasos"][-1].get("car") if reg["pasos"] else None
    return reg

if __name__ == "__main__":
    sel = sys.argv[1:] if len(sys.argv) > 1 else None
    res = []
    for c in CAMINOS:
        if sel and c["id"] not in sel:
            continue
        print("->", c["id"], c["estrato"], flush=True)
        try:
            r = ejecutar(c)
        except Exception as e:
            r = {"id": c["id"], "estrato": c["estrato"], "excepcion": repr(e)[:300], "ok": False}
        res.append(r)
        print("   ", "OK" if r.get("ok") else "FALLO",
              " | ".join(f"{p['motor']}->{p['destino']}" + ("(!)" if p.get("fallo") else "")
                         for p in r.get("pasos", [])), flush=True)
    fn = os.path.join(RAIZ, r"bench\salidas-fidelidad\resultados.json")
    prev = []
    if os.path.exists(fn) and sel:
        prev = [x for x in json.load(open(fn, encoding="utf-8")) if x["id"] not in [r["id"] for r in res]]
    json.dump(prev + res, open(fn, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("escrito", fn)
