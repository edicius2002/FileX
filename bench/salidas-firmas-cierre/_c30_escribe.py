# -*- coding: utf-8 -*-
"""C30 - LA PRUEBA ANCHA DE FALSOS POSITIVOS, DENTRO DEL CONTENEDOR filex-c13.

`bench/firmas-contrato.md` sec.10.7 lo dejo PENDIENTE: la verificacion del censo
del contenedor solo guardo 64 bytes de cabecera por muestra, asi que la prueba
ancha de falsos positivos (sec.6.2, y su version de C37 `_c37_ancha_local.py`)
cubre los destinos LOCALES y no los del contenedor. Repetirla dentro exige llevar
el verificador alli, y eso es lo que hace este arnes.

COPIADO Y ADAPTADO de `bench/salidas-firmas/_cont_firmas.py` (F1). Lo que cambia:

 1. No se buscan posiciones estables de cabecera: se ESCRIBE cada destino que el
    censo declara `escrito` y se pasa el verificador de FileX sobre la salida
    (`firma_real`, `punto1_estado`, `punto1_firma` con la sonda de la ENTRADA
    puesta, para que G6 pueda dispararse).
 2. TRES semillas por modalidad, no dos (CLAUDE.md sec.3, tercer sesgo: si no
    varias la entrada, mides tu entrada; y sec.2.3 del informe de firmas, donde
    dos semillas de markdown que empezaban por titulo inventaron 42 marcadores).
    La tercera de markdown empieza por PROSA a proposito.
 3. Se registra el `rc` de CADA celda (trampa 25: 0 bytes puede ser un proceso
    que no arranco, y es indistinguible del silencio legitimo sin el `rc`).
 4. Se lista el desechable ANTES y DESPUES de cada celda (trampa 21) y se anotan
    los ficheros satelite que el motor deja sin pedirselos.
 5. Todo `subprocess.run` va sin shell, con argumentos en array,
    `stdin=DEVNULL`, `timeout=` explicito Y con `timeout -k 5 N` DELANTE de la
    orden: el tope tiene que estar dentro de la orden, no solo alrededor.

Se ejecuta DENTRO del contenedor:   python3 /w/_c30_escribe.py
  Lee     /w/verificador.py   /w/censo.json
  Escribe /w/c30_contenedor.json   (incremental: se vuelca tras cada motor)

El `sha256` del `verificador.py` que se cargo va en el JSON: la version del
fichero se estaba moviendo mientras se medio y una tabla sin su version no es
comparable (trampa 55, en su version de contrato).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter

W = "/w"                 # bind mount: entradas del arnes y salida del JSON
BASE = "/tmp/c30"        # DESECHABLE, dentro del contenedor
POOL = BASE + "/pool"
TMP = BASE + "/tmp"
DEVNULL = subprocess.DEVNULL

sys.path.insert(0, W)
import verificador as V  # noqa: E402  (biblioteca estandar; no toca la GPU)


def corre(args, timeout=25, cwd=None):
    """Sin shell, argumentos en array, stdin=DEVNULL y DOS topes: `timeout -k 5`
    dentro de la orden y el de `subprocess.run` alrededor, con margen."""
    orden = ["timeout", "-k", "5", str(timeout)] + list(args)
    try:
        p = subprocess.run(orden, stdin=DEVNULL, capture_output=True,
                           timeout=timeout + 15, cwd=cwd)
        return (p.returncode,
                (p.stderr or b"").decode("utf-8", "replace")[-300:],
                p.stdout)
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT_CLIENTE", b""
    except OSError as e:
        return -127, "OSERROR:" + str(e)[:150], b""


def limpia(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)


# ------------------------------------------------------------------ semillas
# Tres contenidos DELIBERADAMENTE distintos por modalidad. La tercera de
# markdown empieza por prosa (no por titulo) porque esa fue justamente la
# diferencia que refuto los 42 marcadores de pandoc.
SVG1 = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="48">'
        '<rect x="2" y="2" width="30" height="20" fill="#c33"/>'
        '<circle cx="48" cy="30" r="12" fill="#37a"/></svg>\n')
SVG2 = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="70">'
        '<polygon points="5,5 90,10 50,60" fill="#2a2"/>'
        '<rect x="60" y="40" width="25" height="25" fill="#000"/></svg>\n')
SVG3 = ('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="90" '
        'viewBox="0 0 120 90"><path d="M10 80 L60 10 L110 80 Z" fill="#f80" '
        'stroke="#204" stroke-width="3"/><ellipse cx="60" cy="70" rx="30" '
        'ry="9" fill="#0aa"/></svg>\n')
MD1 = "# Titulo uno\n\nParrafo con *enfasis* y una lista:\n\n- a\n- b\n\n"
MD2 = ("## Otro documento\n\nTexto distinto del primero, mas largo, con una tabla:\n\n"
       "| x | y |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nY un cierre.\n")
MD3 = ("Esta tercera semilla empieza por prosa y no por un titulo, que es "
       "exactamente la diferencia que refuto los 42 marcadores de pandoc.\n\n"
       "Sigue un parrafo mas, sin encabezados de ningun nivel, con una cita:\n\n"
       "> nada de titulos aqui\n\nY termina sin lista ni tabla.\n")
JSON1 = '{"a": 1, "b": "uno", "c": [1, 2, 3]}\n'
JSON2 = '{"z": {"w": true}, "lista": ["alfa", "beta"], "n": 42}\n'
JSON3 = '{"solo": "una clave de texto largo y sin numeros ni listas dentro"}\n'
OBJ1 = ("# cubo\nv 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nv 0 0 1\nv 1 0 1\nv 1 1 1\nv 0 1 1\n"
        "f 1 2 3\nf 1 3 4\nf 5 6 7\nf 5 7 8\n")
OBJ2 = ("# tetraedro\nv 0 0 0\nv 2 0 0\nv 1 2 0\nv 1 1 2\n"
        "f 1 2 3\nf 1 2 4\nf 2 3 4\nf 1 3 4\n")
OBJ3 = ("# piramide de base cuadrada\nv -1 -1 0\nv 1 -1 0\nv 1 1 0\nv -1 1 0\nv 0 0 3\n"
        "f 1 2 3\nf 1 3 4\nf 1 2 5\nf 2 3 5\nf 3 4 5\nf 4 1 5\n")

# Nombres de fichero y de directorio DISTINTOS entre muestras: hay formatos que
# estampan el nombre del fichero en la cabecera (`info`, `shtml`, `uil`, `pdb`).
NOMBRES = [("d0", "v%d"), ("x1", "w%d"), ("k2", "z%d")]


def semillas(log):
    os.makedirs(POOL, exist_ok=True)
    s = {}

    def esc(nom, txt):
        p = POOL + "/" + nom
        with open(p, "w") as fh:
            fh.write(txt)
        return p

    s["svg"] = [esc("s1.svg", SVG1), esc("s2.svg", SVG2), esc("s3.svg", SVG3)]
    s["md"] = [esc("m1.md", MD1), esc("m2.md", MD2), esc("m3.md", MD3)]
    s["json"] = [esc("j1.json", JSON1), esc("j2.json", JSON2), esc("j3.json", JSON3)]
    s["obj"] = [esc("o1.obj", OBJ1), esc("o2.obj", OBJ2), esc("o3.obj", OBJ3)]
    s["imagen"] = []
    for nom, size, seed, bg in (("a1.png", "64x48", 11, "white"),
                                ("a2.png", "100x70", 29, "black"),
                                ("a3.png", "80x120", 47, "gray50")):
        p = POOL + "/" + nom
        corre(["magick", "-size", size, "xc:" + bg, "-seed", str(seed),
               "+noise", "Random", p], 60)
        s["imagen"].append(p)
    s["pbm"] = []
    for i, src in enumerate(s["imagen"]):
        p = POOL + "/p%d.pbm" % (i + 1)
        corre(["magick", src, "-threshold", "50%", p], 60)
        s["pbm"].append(p)
    s["odt"], s["epub"], s["html"] = [], [], []
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
    log("semillas: " + json.dumps({k: len(v) for k, v in s.items()}))
    return s


# ------------------------------------------------------------------ invocaciones
# Copiadas TAL CUAL de `_cont_firmas.py`, que a su vez las copio de los
# adaptadores de ConvertX (src/converters/*.ts). Cambiarlas aqui haria que el
# «escrito» del censo y el de esta tanda no fuesen la misma medida.
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
        # `-z` NO estaba en `_cont_firmas.py`, y sin el `dvisvgm -o x.svgz`
        # escribe un SVG EN CLARO con nombre `.svgz`: rc=0, fichero valido, y la
        # extension pedida mintiendo. Lo destapo la prueba de humo de C30 y lo
        # atrapo el punto 1 (G3, `gzip` esperado y `svg` obtenido). Es un defecto
        # de la INVOCACION, no un falso positivo del contrato, asi que se corrige
        # aqui: si no, la tanda ancha mediria el arnes y no el verificador.
        arg = ["dvisvgm", "--pdf", ent, "-o", sal]
        if dest == "svgz":
            arg.insert(1, "-z")
        return arg, 25
    return None, 25


def inv_libjxl(ent, dest, sal, inter):
    """libjxl son DOS binarios, y `_cont_firmas.py` usaba solo uno.

    `cjxl` escribe SIEMPRE un JXL, mire la extension que mire: pedirle un `.apng`
    o un `.exr` daba rc=0 y un fichero JXL con la extension equivocada -- el fallo
    emblematico del proyecto, cometido por el propio arnes del censo. Los destinos
    que NO son `jxl` los escribe `djxl`, y para eso hace falta un JXL de partida:
    png -> cjxl -> .jxl -> djxl -> destino.
    """
    if dest == "jxl":
        return [(["cjxl", ent, sal], 40)]
    return [(["cjxl", ent, inter], 40), (["djxl", inter, sal], 40)]


MODAL = {"graphicsmagick": "imagen", "vips": "imagen", "pandoc": "md",
         "calibre": "epub", "libreoffice": "odt", "inkscape": "svg",
         "potrace": "pbm", "assimp": "obj", "libjxl": "imagen",
         "libheif": "imagen", "vtracer": "imagen", "resvg": "svg",
         "dvisvgm": "pdf", "dasel": "json"}


def localiza(sub, sal, dest, antes):
    """Cual de los ficheros del desechable es la salida. Devuelve (ruta, como).

    `soffice` y `ebook-convert` escriben <nombre-entrada>.<fmt>, no el nombre
    que se les pide, asi que la busqueda tiene tres reglas y una de ultimo
    recurso; se anota CUAL acerto, porque «el nombre no es el pedido» es un dato,
    no un detalle del arnes.
    """
    cands = sorted(x for x in os.listdir(sub) if os.path.isfile(sub + "/" + x))
    nuevos = [c for c in cands if c not in antes]
    base = os.path.basename(sal)
    raiz = os.path.splitext(base)[0]
    for c in nuevos:
        if c == base:
            return sub + "/" + c, "exacta"
    for c in nuevos:
        if c.startswith(raiz):
            return sub + "/" + c, "raiz"
    for c in nuevos:
        if c.endswith("." + dest):
            return sub + "/" + c, "extension"
    if len(nuevos) == 1:
        return sub + "/" + nuevos[0], "unico"
    return None, "ninguno"


def evalua(ruta, ent, dest, rc):
    """El contrato sobre UNA salida. Todo en proceso, ningun subproceso."""
    try:
        son = V.sondear(ruta, "proceso")
    except Exception as e:                      # una sonda no puede tumbar la tanda
        son = {"ruta": ruta, "bytes": os.path.getsize(ruta),
               "firma": V.firma_real(ruta),
               "error": type(e).__name__ + ": " + str(e)[:120]}
    son_ent = {"ruta": ent, "firma": V.firma_real(ent)}
    h = V.punto1_firma(ruta, son, {"destino": dest, "rc": rc}, son_ent)
    return {
        "firma_real": son.get("firma"),
        "firma_entrada": son_ent["firma"],
        "punto1_estado": V.punto1_estado(ruta),
        "hallazgos": [[x["regla"], x["severidad"]] for x in h],
        "mensajes": [x["mensaje"][:200] for x in h if x["severidad"] == "fallo"],
        "fallo": any(x["severidad"] == "fallo" for x in h),
        "g6": any(x["regla"] == "G6" for x in h),
        "sonda_error": son.get("error"),
    }


def celda(motor, dest, ent, j, k, sub):
    """Una conversion + su verificacion. Devuelve la fila del JSON."""
    dirn, patron = NOMBRES[j % len(NOMBRES)]
    limpia(sub)
    antes = set(os.listdir(sub))
    sal = sub + "/" + (patron % (k * 7 + j * 7919)) + "." + dest.replace("/", "_")
    fila = {"motor": motor, "destino": dest, "semilla": os.path.basename(ent),
            "entrada": ent, "rc": None, "bytes": None}
    err = ""
    if motor == "dasel":
        rc, err, so = corre(["dasel", "-r", "json", "-w", dest, "-f", ent], 25, cwd=sub)
        if rc == 0 and so:
            with open(sal, "wb") as fh:
                fh.write(so)
    elif motor == "libjxl":
        # El intermedio vive FUERA del desechable, para que el censo de satelites
        # del punto 5 no lo cuente como un fichero que el motor dejo sin pedirselo.
        inter = POOL + "/inter_%d.jxl" % j
        rc, pasos = 0, inv_libjxl(ent, dest, sal, inter)
        for cmd, to in pasos:
            rc, err, _ = corre(cmd, to, cwd=sub)
            if rc != 0:
                break
    else:
        cmd, to = inv(motor, ent, dest, sal, sub)
        if cmd is None:
            fila.update({"rc": -1, "estado": "sin_invocacion"})
            return fila
        rc, err, _ = corre(cmd, to, cwd=sub)
    fila["rc"] = rc
    ruta, como = localiza(sub, sal, dest, antes)
    despues = sorted(x for x in os.listdir(sub) if os.path.isfile(sub + "/" + x))
    if ruta is None or os.path.getsize(ruta) <= 0:
        fila.update({"estado": "no_escrito", "como": como,
                     "bytes": os.path.getsize(ruta) if ruta else 0,
                     "err": err.replace("\n", " ")[-200:],
                     "ficheros": despues})
        return fila
    fila["bytes"] = os.path.getsize(ruta)
    fila["nombre"] = os.path.basename(ruta)
    fila["como"] = como
    fila["satelites"] = [x for x in despues if x != os.path.basename(ruta)]
    fila["estado"] = "escrito"
    fila.update(evalua(ruta, ent, dest, rc))
    return fila


def main():
    t0 = time.time()
    reg = open(W + "/log-c30-dentro.txt", "w")

    def log(msg):
        linea = "[%7.1fs] %s" % (time.time() - t0, msg)
        print(linea, flush=True)
        reg.write(linea + "\n")
        reg.flush()

    with open(W + "/verificador.py", "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    log("verificador.py sha256=%s  python=%s" % (sha, sys.version.split()[0]))
    log("FIRMAS=%d FIRMAS_LARGAS=%d EXT_A_FIRMAS=%d EXT_FAMILIA=%d EXT_SIN_FIRMA=%d"
        % (len(V.FIRMAS), len(getattr(V, "FIRMAS_LARGAS", [])), len(V.EXT_A_FIRMAS),
           len(V.EXT_FAMILIA), len(V.EXT_SIN_FIRMA)))

    censo = json.load(open(W + "/censo.json"))
    limpia(BASE)
    sem = semillas(log)

    orden = ["graphicsmagick", "vips", "pandoc", "inkscape", "potrace", "assimp",
             "dasel", "libjxl", "libheif", "vtracer", "resvg", "dvisvgm",
             "libreoffice", "calibre"]
    filas = []
    for motor in orden:
        if motor not in censo:
            continue
        dests = sorted(d for d, v in censo[motor].items() if v.get("estado") == "escrito")
        mod = MODAL.get(motor)
        sems = sem.get(mod, [])
        if not dests:
            log("%-16s 0 destinos `escrito` en el censo: nada que medir" % motor)
            continue
        t1 = time.time()
        for k, dest in enumerate(dests):
            for j, ent in enumerate(sems):
                sub = TMP + "/" + NOMBRES[j % len(NOMBRES)][0]
                filas.append(celda(motor, dest, ent, j, k, sub))
            if k % 10 == 0:
                log("  %s %d/%d (%.0fs)" % (motor, k, len(dests), time.time() - t1))
        esc = sum(1 for f in filas if f["motor"] == motor and f["estado"] == "escrito")
        n = sum(1 for f in filas if f["motor"] == motor)
        log("%-16s celdas escritas %d/%d en %.0fs" % (motor, esc, n, time.time() - t1))
        volcado(filas, sha, censo, reg)
    volcado(filas, sha, censo, reg)
    log("HECHO en %.0fs" % (time.time() - t0))
    reg.close()


def volcado(filas, sha, censo, reg):
    buenas = [f for f in filas if f.get("estado") == "escrito"]
    fp = [f for f in buenas if f.get("fallo")]
    g6 = [f for f in buenas if f.get("g6")]
    # La cobertura se cuenta por DESTINO (no por celda): las tres semillas de un
    # mismo destino dan el mismo `punto1_estado`, y contarlas tres veces inflaria
    # el reparto sin anadir informacion.
    por_dest = {}
    for f in buenas:
        por_dest.setdefault((f["motor"], f["destino"]), f)
    res = {
        "sha256_verificador": sha,
        "celdas": len(filas),
        "celdas_escritas": len(buenas),
        "destinos_declarados_escrito": sum(
            1 for m in censo for d, v in censo[m].items() if v.get("estado") == "escrito"),
        "destinos_escritos": len(por_dest),
        "falsos_positivos": [
            {"motor": f["motor"], "destino": f["destino"], "semilla": f["semilla"],
             "firma_real": f["firma_real"], "punto1_estado": f["punto1_estado"],
             "hallazgos": f["hallazgos"], "mensajes": f["mensajes"]} for f in fp],
        "n_falsos_positivos": len(fp),
        "n_falsos_positivos_destinos": len({(f["motor"], f["destino"]) for f in fp}),
        "g6": [{"motor": f["motor"], "destino": f["destino"], "semilla": f["semilla"],
                "firma_real": f["firma_real"], "firma_entrada": f["firma_entrada"]}
               for f in g6],
        "n_g6": len(g6),
        "n_g6_destinos": len({(f["motor"], f["destino"]) for f in g6}),
        "cobertura_por_destino": dict(Counter(v["punto1_estado"] for v in por_dest.values())),
        "cobertura_por_celda": dict(Counter(f["punto1_estado"] for f in buenas)),
        "no_escritas": [{"motor": f["motor"], "destino": f["destino"],
                         "semilla": f["semilla"], "rc": f["rc"],
                         "err": f.get("err", "")}
                        for f in filas if f.get("estado") != "escrito"],
        "satelites": [{"motor": f["motor"], "destino": f["destino"],
                       "semilla": f["semilla"], "satelites": f["satelites"]}
                      for f in buenas if f.get("satelites")],
        "sondas_con_error": [{"motor": f["motor"], "destino": f["destino"],
                              "error": f["sonda_error"]}
                             for f in buenas if f.get("sonda_error")],
    }
    with open(W + "/c30_contenedor.json", "w") as fh:
        json.dump({"resumen": res, "filas": filas}, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
