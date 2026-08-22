# -*- coding: utf-8 -*-
"""F1 / paso 2b - CENSO EMPIRICO DE MARCADORES, DENTRO DEL CONTENEDOR filex-convertx.

Los 340 formatos de salida que ffmpeg + ImageMagick declaran se sondean en Windows
(_censo_firmas.py). Los otros 162 solo existen en motores que en esta maquina viven
en el contenedor: pandoc (61), graphicsmagick (27), assimp (22), libreoffice (17),
calibre (16), inkscape (10), vips (10), potrace (6), dasel (2) y cuatro sueltos.

Mismo metodo: escribir cada formato DOS veces con contenidos distintos y quedarse con
las posiciones de los primeros 64 bytes en las que las dos muestras coinciden.

Invocaciones copiadas de los adaptadores de ConvertX (src/converters/*.ts), mas
stdin=DEVNULL y timeout duro, que ConvertX no pone.

Se ejecuta DENTRO del contenedor:  python3 /tmp/f1/_cont_firmas.py
Escribe /tmp/f1/cont_firmas.json
"""
import os, sys, json, time, shutil, subprocess

BASE = "/tmp/f1"
POOL = BASE + "/pool"
TMP = BASE + "/tmp"
NCAB = 64
DEVNULL = subprocess.DEVNULL


def corre(args, timeout=25, cwd=None):
    try:
        p = subprocess.run(args, stdin=DEVNULL, capture_output=True, timeout=timeout,
                           cwd=cwd)
        return p.returncode, (p.stderr or b"").decode("utf-8", "replace")[-300:], p.stdout
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT", b""
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:150], b""


def limpia(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)


# ------------------------------------------------------------------ semillas
SVG1 = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="48">'
        '<rect x="2" y="2" width="30" height="20" fill="#c33"/>'
        '<circle cx="48" cy="30" r="12" fill="#37a"/></svg>\n')
SVG2 = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="70">'
        '<polygon points="5,5 90,10 50,60" fill="#2a2"/>'
        '<rect x="60" y="40" width="25" height="25" fill="#000"/></svg>\n')
MD1 = "# Titulo uno\n\nParrafo con *enfasis* y una lista:\n\n- a\n- b\n\n"
MD2 = ("## Otro documento\n\nTexto distinto del primero, mas largo, con una tabla:\n\n"
       "| x | y |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nY un cierre.\n")
JSON1 = '{"a": 1, "b": "uno", "c": [1, 2, 3]}\n'
JSON2 = '{"z": {"w": true}, "lista": ["alfa", "beta"], "n": 42}\n'
OBJ1 = ("# cubo\nv 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nv 0 0 1\nv 1 0 1\nv 1 1 1\nv 0 1 1\n"
        "f 1 2 3\nf 1 3 4\nf 5 6 7\nf 5 7 8\n")
OBJ2 = ("# tetraedro\nv 0 0 0\nv 2 0 0\nv 1 2 0\nv 1 1 2\n"
        "f 1 2 3\nf 1 2 4\nf 2 3 4\nf 1 3 4\n")


def semillas():
    os.makedirs(POOL, exist_ok=True)
    s = {}

    def esc(nom, txt):
        p = POOL + "/" + nom
        open(p, "w").write(txt)
        return p

    s["svg"] = [esc("s1.svg", SVG1), esc("s2.svg", SVG2)]
    s["md"] = [esc("m1.md", MD1), esc("m2.md", MD2)]
    s["json"] = [esc("j1.json", JSON1), esc("j2.json", JSON2)]
    s["obj"] = [esc("o1.obj", OBJ1), esc("o2.obj", OBJ2)]
    s["imagen"] = []
    for nom, size, seed, bg in (("a1.png", "64x48", 11, "white"),
                                ("a2.png", "100x70", 29, "black")):
        p = POOL + "/" + nom
        corre(["magick", "-size", size, "xc:" + bg, "-seed", str(seed),
               "+noise", "Random", p], 60)
        s["imagen"].append(p)
    s["pbm"] = []
    for i, src in enumerate(s["imagen"]):
        p = POOL + "/p%d.pbm" % (i + 1)
        corre(["magick", src, "-threshold", "50%", p], 60)
        s["pbm"].append(p)
    s["odt"] = []
    s["epub"] = []
    s["html"] = []
    for i, src in enumerate(s["md"]):
        for ext, lst in (("odt", s["odt"]), ("epub", s["epub"]), ("html", s["html"])):
            p = POOL + "/q%d.%s" % (i + 1, ext)
            corre(["pandoc", src, "-f", "markdown", "-t", ext, "-o", p], 60)
            lst.append(p)
    s["pdf"] = []
    for i, src in enumerate(s["imagen"]):
        p = POOL + "/r%d.pdf" % (i + 1)
        corre(["magick", src, p], 60)
        s["pdf"].append(p)
    for k in list(s):
        s[k] = [p for p in s[k] if os.path.exists(p) and os.path.getsize(p) > 0]
    return s


# ------------------------------------------------------------------ invocaciones
def inv(motor, ent, dest, sal, outdir):
    if motor == "graphicsmagick":
        return ["gm", "convert", ent, sal], 25
    if motor == "vips":
        acc = "pdfload" if ent.endswith(".pdf") else "copy"
        return ["vips", acc, ent, sal], 25
    if motor == "pandoc":
        return ["pandoc", ent, "-f", "markdown", "-t", dest, "-o", sal], 40
    if motor == "calibre":
        return ["ebook-convert", ent, sal], 90
    if motor == "libreoffice":
        return ["soffice", "--headless", "--convert-to", dest, "--outdir", outdir, ent], 60
    if motor == "inkscape":
        return ["inkscape", ent, "-o", sal], 40
    if motor == "potrace":
        return ["potrace", ent, "-o", sal, "-b", dest], 25
    if motor == "assimp":
        return ["assimp", "export", ent, sal, "-f" + dest], 25
    if motor == "libjxl":
        return ["cjxl", ent, sal], 40
    if motor == "libheif":
        return ["heif-enc", ent, "-o", sal], 40
    if motor == "vtracer":
        return ["vtracer", "--input", ent, "--output", sal], 40
    if motor == "resvg":
        return ["resvg", ent, sal], 25
    if motor == "dvisvgm":
        return ["dvisvgm", "--pdf", ent, "-o", sal], 25
    return None, 25


MODAL = {"graphicsmagick": ["imagen"], "vips": ["imagen"], "pandoc": ["md"],
         "calibre": ["epub"], "libreoffice": ["odt"], "inkscape": ["svg"],
         "potrace": ["pbm"], "assimp": ["obj"], "libjxl": ["imagen"],
         "libheif": ["imagen"], "vtracer": ["imagen"], "resvg": ["svg"],
         "dvisvgm": ["pdf"]}


def cab(p):
    with open(p, "rb") as fh:
        return fh.read(NCAB)


def estables(cabs):
    n = min(len(c) for c in cabs)
    pos = [i for i in range(n) if len({c[i] for c in cabs}) == 1]
    return pos, bytes(cabs[0][i] for i in pos)


def prefijo_comun(cabs):
    n = min(len(c) for c in cabs)
    i = 0
    while i < n and len({c[i] for c in cabs}) == 1:
        i += 1
    return i


# Nombres de fichero y de directorio DELIBERADAMENTE DISTINTOS entre las dos
# muestras: hay formatos que estampan el nombre del fichero en la cabecera y ese
# texto compartido se contaria como marcador sin serlo.
NOMBRES = [("d0", "v%d"), ("x1", "w%d")]


def censa(motor, formatos, sem):
    res = {}
    t0 = time.time()
    for k, b in enumerate(sorted(formatos)):
        fila = {"formato": b, "motor": motor, "estado": "", "errores": []}
        for mod in MODAL.get(motor, []):
            sems = sem.get(mod, [])
            if len(sems) < 2:
                continue
            cabs, tams, ok = [], [], True
            for j, ent in enumerate(sems):
                dirn, patron = NOMBRES[j % len(NOMBRES)]
                sub = TMP + "/" + dirn
                limpia(sub)
                sal = sub + "/" + (patron % (k * 7 + j * 7919)) + "." + b.replace("/", "_")
                if motor == "dasel":
                    cmd, to = ["dasel", "-r", "json", "-w", b, "-f", ent], 25
                    rc, err, so = corre(cmd, to, cwd=sub)
                    if rc == 0 and so:
                        open(sal, "wb").write(so)
                else:
                    cmd, to = inv(motor, ent, b, sal, sub)
                    if cmd is None:
                        ok = False
                        break
                    rc, err, _ = corre(cmd, to, cwd=sub)
                cands = sorted(x for x in os.listdir(sub)
                               if os.path.isfile(sub + "/" + x))
                base = os.path.basename(sal)
                raiz = os.path.splitext(base)[0]
                real = None
                for c in cands:
                    if c == base or c.startswith(raiz):
                        real = sub + "/" + c
                        break
                if real is None:
                    # soffice / calibre pueden escribir <nombre-entrada>.<fmt>
                    for c in cands:
                        if c.endswith("." + b):
                            real = sub + "/" + c
                            break
                if rc != 0 or real is None or os.path.getsize(real) <= 0:
                    ok = False
                    if j == 0:
                        fila["errores"].append("rc=%s %s" % (rc, err.replace("\n", " ")[-140:]))
                    break
                cabs.append(cab(real))
                tams.append(os.path.getsize(real))
            if ok and len(cabs) >= 2:
                pos, val = estables(cabs)
                fila.update({"n_muestras": len(cabs), "modalidad": mod, "bytes": tams,
                             "cab": [c.hex() for c in cabs],
                             "prefijo_comun": prefijo_comun(cabs),
                             "pos_estables": pos, "val_estables": val.hex(),
                             "estado": "escrito"})
                break
        if not fila["estado"]:
            fila["estado"] = "no_escribible"
        res[b] = fila
        if k % 10 == 0:
            print("  %s %d/%d (%.0fs)" % (motor, k, len(formatos), time.time() - t0), flush=True)
    return res


if __name__ == "__main__":
    F = json.load(open(BASE + "/formatos.json"))
    pa = F["por_adaptador"]
    sem = semillas()
    print("semillas:", {k: len(v) for k, v in sem.items()}, flush=True)
    out = {}
    orden = ["graphicsmagick", "vips", "pandoc", "inkscape", "potrace", "assimp",
             "dasel", "libjxl", "libheif", "vtracer", "resvg", "dvisvgm",
             "libreoffice", "calibre"]
    for m in orden:
        if m not in pa:
            continue
        out[m] = censa(m, set(pa[m]["to"]), sem)
        esc = sum(1 for v in out[m].values() if v["estado"] == "escrito")
        print("%-16s escritos %d/%d" % (m, esc, len(out[m])), flush=True)
        json.dump(out, open(BASE + "/cont_firmas.json", "w"), indent=0)
    json.dump(out, open(BASE + "/cont_firmas.json", "w"), indent=0)
    print("HECHO")
