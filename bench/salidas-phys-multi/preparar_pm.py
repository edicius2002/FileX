# -*- coding: utf-8 -*-
"""G4 / B19 — prepara los rasteres y sus VARIANTES DE CABECERA `pHYs`.

Diseño, y por que asi
---------------------
G2 (`bench/psm-y-rasterizador.md` §4) probo que las ocho variantes de rasterizado dan
LOS MISMOS PIXELES —ImageMagick no tiene rasterizador de PDF, delega en Ghostscript— y
que la unica variable real es el trozo `pHYs` de la cabecera del PNG. Aqui NO se
re-rasteriza para cambiar el metadato: se rasteriza UNA VEZ por (documento, factor) y
las variantes se generan por CIRUGIA DE BYTES sobre el PNG.

Ventaja, y es el nucleo del experimento: los IDAT no se tocan, asi que la identidad de
los pixeles no es «medida», es CONSTRUCTIVA — y ademas se comprueba (md5 de la
concatenacion de IDAT y md5 del array decodificado). Si la salida de un motor cambia
entre variantes, solo puede ser por la cabecera.

Variantes (`unidad` del `pHYs`, PNG spec 11.3.5.3):
  sin      -> como lo escribe `magick -density N`: pHYs presente con unidad=0
              (SIN UNIDAD; el valor es una relacion de aspecto, no una densidad).
              ES LA QUE TIENE TODO EL CORPUS DEL PROYECTO.
  ninguno  -> pHYs ELIMINADO del todo. `sin` y `ninguno` no son lo mismo y ningun
              informe del proyecto los ha separado.
  pNNNN    -> pHYs con unidad=1 y NNNN ppp exactos (ppp -> px/m = round(ppp/0.0254)).

uso: python preparar_pm.py <doc>:<factor> [<doc>:<factor> ...]
env: IMGDIR  DECLS (lista de ppp separada por comas)  TOPE_LADO_PX
"""
import hashlib
import json
import os
import struct
import subprocess
import sys

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
RAIZ = r"D:\Work\research\FileX"
PDF = os.path.join(RAIZ, r"corpus\pdf")
BASE = os.path.join(RAIZ, r"bench\salidas-phys-multi")
IMG = os.environ.get("IMGDIR", os.path.join(BASE, "img"))
JSN = os.path.join(BASE, "json")
os.makedirs(IMG, exist_ok=True)
os.makedirs(JSN, exist_ok=True)

TOPE_LADO_PX = int(os.environ.get("TOPE_LADO_PX", "3400"))
DECLS = [int(x) for x in os.environ.get("DECLS", "70,100,150,200,300,400").split(",")]
TMO = 600


def run(args, tmo=TMO):
    p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=tmo)
    if p.returncode != 0:
        raise SystemExit(f"fallo rc={p.returncode}: {args[0]}\n{p.stderr[:400]}")
    return p


# ------------------------------------------------------------------ PNG, a pelo
FIRMA = b"\x89PNG\r\n\x1a\n"


def trozos(b):
    """Devuelve la lista de (tipo, datos) del PNG. No usa ninguna libreria: el
    experimento entero depende de que los IDAT no se toquen."""
    assert b[:8] == FIRMA, "no es un PNG"
    i = 8
    out = []
    while i < len(b):
        ln = struct.unpack(">I", b[i:i + 4])[0]
        tipo = b[i + 4:i + 8]
        datos = b[i + 8:i + 8 + ln]
        out.append((tipo, datos))
        i += 8 + ln + 4          # longitud + tipo + datos + crc
    return out


def empaqueta(trs):
    import zlib
    out = bytearray(FIRMA)
    for tipo, datos in trs:
        out += struct.pack(">I", len(datos)) + tipo + datos
        out += struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
    return bytes(out)


def phys_de(trs):
    for tipo, datos in trs:
        if tipo == b"pHYs":
            x, y = struct.unpack(">II", datos[:8])
            return {"x_ppu": x, "y_ppu": y, "unidad": datos[8],
                    "ppp_x": round(x * 0.0254, 2) if datos[8] == 1 else None}
    return None


def md5_idat(trs):
    h = hashlib.md5()
    for tipo, datos in trs:
        if tipo == b"IDAT":
            h.update(datos)
    return h.hexdigest()


def variante(trs, decl):
    """decl: None -> quita el pHYs; 0 -> lo deja tal cual (unidad=0 de magick);
    entero>0 -> pHYs con unidad=1 y esos ppp."""
    if decl == 0:
        return list(trs)
    sin = [(t, d) for t, d in trs if t != b"pHYs"]
    if decl is None:
        return sin
    ppu = int(round(decl / 0.0254))
    dat = struct.pack(">II", ppu, ppu) + b"\x01"
    # el pHYs va ANTES del primer IDAT (PNG spec 11.3.5.3)
    i = next(k for k, (t, _) in enumerate(sin) if t == b"IDAT")
    return sin[:i] + [(b"pHYs", dat)] + sin[i:]


# ------------------------------------------------------------------ geometria
def geometria(ruta):
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(ruta)
    p = d[0]
    w_pt, h_pt = p.get_size()
    mejor = None
    for obj in p.get_objects(filter=(pdfium.raw.FPDF_PAGEOBJ_IMAGE,)):
        try:
            m = obj.get_metadata()
            if mejor is None or m.width * m.height > mejor[0] * mejor[1]:
                mejor = (m.width, m.height)
        except Exception:
            pass
    d.close()
    if mejor is None:
        return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2),
                "img_px": None, "ppp_calculado": None}
    return {"ancho_pt": round(w_pt, 2), "alto_pt": round(h_pt, 2),
            "img_px": [mejor[0], mejor[1]],
            "ppp_calculado": round(mejor[0] / (w_pt / 72.0), 1)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    censo = {}
    for arg in sys.argv[1:]:
        doc, f = arg.split(":")
        f = float(f)
        src = os.path.join(PDF, doc + ".pdf")
        g = geometria(src)
        nat = g["ppp_calculado"]
        ppp = int(round(nat * f))
        raiz = f"{doc}__k{int(round(f * 1000)):04d}"
        # --- rasterizado UNICO, variante `im`: LA DEL CORPUS (magick, pHYs unidad=0)
        base_png = os.path.join(IMG, raiz + "__sin.png")
        run([MAGICK, "-density", str(ppp), src + "[0]", "-colorspace", "Gray",
             "-alpha", "remove", "-background", "white", "-flatten", base_png])
        b = open(base_png, "rb").read()
        trs = trozos(b)
        dim = subprocess.run([MAGICK, "identify", "-format",
                              "%wx%h %[depth] %[type] %x,%y,%U", base_png],
                             stdin=subprocess.DEVNULL, capture_output=True,
                             text=True, timeout=120).stdout.strip()
        w, h = (int(x) for x in dim.split(" ")[0].split("x"))
        if max(w, h) > TOPE_LADO_PX:
            os.remove(base_png)
            print(f"{raiz} RECHAZADO por tope {TOPE_LADO_PX}px ({w}x{h})")
            continue
        idat0 = md5_idat(trs)
        # el valor VERDADERO de este raster son los ppp de renderizado
        decls = sorted(set(DECLS + [ppp]))
        for etq, decl in ([("sin", 0), ("ninguno", None)]
                          + [(f"p{d:04d}", d) for d in decls]):
            dst = os.path.join(IMG, f"{raiz}__{etq}.png")
            nuevos = variante(trs, decl)
            open(dst, "wb").write(empaqueta(nuevos))
            rl = trozos(open(dst, "rb").read())
            clave = f"{raiz}__{etq}"
            censo[clave] = {
                "doc": doc, "factor": f, "ppp_render": ppp, "ppp_nativos": nat,
                "declaracion": etq, "ppp_declarados": decl,
                "verdadero": (decl == ppp),
                "px": [w, h], "megapixeles": round(w * h / 1e6, 3),
                "identify": dim, "bytes": os.path.getsize(dst),
                "phys": phys_de(rl), "md5_idat": md5_idat(rl),
                "md5_idat_igual_base": md5_idat(rl) == idat0,
                "sha256_png": hashlib.sha256(open(dst, "rb").read()).hexdigest(),
            }
            print(f"{clave:44s} {dim:34s} phys={censo[clave]['phys']} "
                  f"idat_igual={censo[clave]['md5_idat_igual_base']}", flush=True)
        censo[f"{raiz}__GEOM"] = dict(g, doc=doc, factor=f, ppp_render=ppp,
                                      px=[w, h], md5_idat_base=idat0)
    fj = os.path.join(JSN, "geometria_pm.json")
    prev = json.load(open(fj, encoding="utf-8")) if os.path.exists(fj) else {}
    prev.update(censo)
    json.dump(prev, open(fj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    n_ok = sum(1 for v in censo.values() if v.get("md5_idat_igual_base"))
    n_tot = sum(1 for v in censo.values() if "md5_idat_igual_base" in v)
    print(f"\nIDAT identicos al base: {n_ok}/{n_tot}")
