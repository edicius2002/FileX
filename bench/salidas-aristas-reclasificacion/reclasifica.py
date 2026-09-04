# -*- coding: utf-8 -*-
"""C49 / worker9 - RECLASIFICACION DE LOS 445 `no_materializable` DE semi_entrada.json.

NO ejecuta ningun motor de conversion. Solo LEE listados de metadatos ya volcados
en crudo/ (magick -list format, -list delegate; ffmpeg -protocols -devices
-demuxers -muxers) y los cruza con bench/salidas-aristas/semi_entrada.json.

Coste de maquina: cero mas alla de los siete listados, que son instantaneos.

Escribe reclasificacion.json y reclasificacion.csv EN ESTE DIRECTORIO.
NO toca bench/salidas-aristas/ (CLAUDE.md sec.1: un fichero de salida por agente).
"""
import os, re, json, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
CRUDO = os.path.join(AQUI, "crudo")
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
SEMI = os.path.join(RAIZ, "bench", "salidas-aristas", "semi_entrada.json")


def lee(n):
    return open(os.path.join(CRUDO, n), encoding="utf-8", errors="replace").read()


# ---------------------------------------------------------------- ImageMagick
def im_formatos():
    """(formato -> {modulo, modo, blob, desc}) desde `magick -list format`.

    Mismo parseo que _censo.im_real() para el nombre y el modo -- se comprueba
    abajo que el conjunto reproducido coincide con el del censo (trampa 58).
    """
    d = {}
    for ln in lee("im-format.txt").splitlines()[2:]:
        p = ln.split()
        if len(p) < 3:
            continue
        if not re.fullmatch(r"[r-][w-][+-]", p[2]):
            continue
        nombre = p[0]
        d[nombre.rstrip("*").lower()] = {
            "modulo": p[1],
            "modo": p[2],
            "blob": nombre.endswith("*"),          # ListMagickInfo: '*' = blob_support
            "desc": " ".join(p[3:]),
        }
    return d


def im_delegados():
    """Extensiones que aparecen a la IZQUIERDA de un `=>` o `<=>` en -list delegate."""
    izq = set()
    for ln in lee("im-delegate.txt").splitlines():
        m = re.match(r"\s*([A-Za-z0-9]+)\s*(<=>|=>|<=)\s", ln)
        if m:
            izq.add(m.group(1).lower())
    return izq


# ---------------------------------------------------------------- ffmpeg
def ff_nombres(fichero):
    """Nombres de -demuxers / -muxers, con la raiz de los `*_pipe` (igual que _censo)."""
    ns = set()
    for ln in lee(fichero).splitlines():
        m = re.match(r"^\s*[DE ]{1,2}\s+([A-Za-z0-9_,.+-]+)\s+\S", ln)
        if m and not ln.startswith("---"):
            for n in m.group(1).split(","):
                if n and n not in ("File", "formats:"):
                    ns.add(n.lower())
    for n in list(ns):
        if n.endswith("_pipe"):
            ns.add(n[:-5])
    return ns


def ff_protocolos():
    ent, sal, cual = set(), set(), None
    for ln in lee("ff-protocols.txt").splitlines():
        s = ln.strip()
        if s == "Input:":
            cual = ent
        elif s == "Output:":
            cual = sal
        elif s and cual is not None and not s.endswith(":"):
            cual.add(s.lower())
    return ent, sal


def ff_dispositivos():
    d, e = set(), set()
    for ln in lee("ff-devices.txt").splitlines():
        m = re.match(r"^\s*([D ])([E ])\s+([A-Za-z0-9_]+)\s+\S", ln)
        if m:
            if m.group(1) == "D":
                d.add(m.group(3).lower())
            if m.group(2) == "E":
                e.add(m.group(3).lower())
    return d, e


if __name__ == "__main__":
    semi = json.load(open(SEMI, encoding="utf-8"))
    nm = sorted(k for k, v in semi.items() if v["estado"] == "no_materializable")
    print("no_materializable en semi_entrada.json: %d" % len(nm))

    IM = im_formatos()
    IM_DELEG = im_delegados()
    DEM = ff_nombres("ff-demuxers.txt")
    MUX = ff_nombres("ff-muxers.txt")
    PIN, POUT = ff_protocolos()
    DDEV, EDEV = ff_dispositivos()

    # --- CONTROL DE SONDA (trampa 66): el parseo tiene que reproducir el del censo.
    im_lee_repro = {f for f, v in IM.items() if v["modo"][0] == "r"}
    im_censo = {k.split("|", 1)[1] for k in semi if k.startswith("imagemagick|")}
    print("control sonda IM: reproducidas %d, censo %d, difieren %s"
          % (len(im_lee_repro), len(im_censo), sorted(im_lee_repro ^ im_censo) or "NINGUNA"))
    print("control sonda ffmpeg: demuxers %d, muxers %d, protocolos in %d, dispositivos D %d"
          % (len(DEM), len(MUX), len(PIN), len(DDEV)))
    # control positivo: dos tokens que SE SABEN distintos no pueden salir iguales
    print("control positivo: png=%s  xc=%s" % (IM.get("png"), IM.get("xc")))

    filas = []
    for k in nm:
        motor, tok = k.split("|", 1)
        f = {"clave": k, "motor": motor, "token": tok}
        if motor == "imagemagick":
            v = IM.get(tok, {})
            f.update(modulo=v.get("modulo"), modo=v.get("modo"),
                     blob=v.get("blob"), desc=v.get("desc"),
                     delegado=tok in IM_DELEG)
        else:
            f.update(en_demuxer=tok in DEM, en_muxer=tok in MUX,
                     en_protocolo_in=tok in PIN, en_protocolo_out=tok in POUT,
                     en_dispositivo_in=tok in DDEV, en_dispositivo_out=tok in EDEV)
        filas.append(f)

    json.dump({"crudo": sorted(os.listdir(CRUDO)), "filas": filas},
              open(os.path.join(AQUI, "cruce.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    # --- reparto grueso, para ver el terreno antes de nombrar clases
    ff = [x for x in filas if x["motor"] == "ffmpeg"]
    im = [x for x in filas if x["motor"] == "imagemagick"]
    print("\nffmpeg (%d):" % len(ff))
    c = collections.Counter((x["en_demuxer"], x["en_muxer"], x["en_protocolo_in"],
                             x["en_dispositivo_in"]) for x in ff)
    print("  (demux, mux, proto_in, dev_in) ->", dict(c))
    print("\nimagemagick (%d) por modulo:" % len(im))
    for mod, n in collections.Counter(x["modulo"] for x in im).most_common():
        print("   %-12s %3d   %s" % (mod, n,
              ", ".join(sorted(x["token"] for x in im if x["modulo"] == mod)[:6])))
