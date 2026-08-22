# -*- coding: utf-8 -*-
"""P2 / C15-a segunda vuelta - las 18 semiaristas de entrada que siguieron muertas.

Motivo, y es una autocritica del arnes heredado: E1 materializaba cada formato con
el PRIMER motor que supiera escribirlo, no con el motor que luego lo iba a LEER.
Para los crudos sin cabecera eso es fatal: `ffmpeg -i s_cif.mp4 m.rgb` usa el muxer
rawvideo, que IGNORA la extension y vuelca el pix_fmt de la entrada (yuv420p).
El fichero llamado m.rgb NO contiene RGB. Leerlo como RGB da basura, y mi propia
politica se nego a construir la invocacion porque no tenia geometria.

Segunda vuelta, con dos correcciones y nada mas:
  - semilla ESCRITA POR EL MOTOR QUE LA VA A LEER (autoconsistencia, que es el
    sesgo favorable al catalogo que E1 ya declaraba);
  - semilla PEQUENA (64x48), porque varios fallos eran limites de recurso
    ("unable to extend cache ... No space left on device") y no de formato.
Y una medida nueva: BYTES POR PIXEL de lo que el motor escribio, para detectar si
el escritor y el lector del MISMO binario discrepan en el numero de canales.

Escribe semi_in_p2b.json
"""
import os, sys, json, glob, time

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
POOL2 = os.path.join(SAL, "pool2")
TMP = os.path.join(SAL, "tmp_in2")
sys.path.insert(0, SAL)
from _p2_lib import (corre, limpia, inv_convertx_ff, inv_convertx_im,
                     inv_p2_ff, inv_p2_im, juzga, sonda_y_veredicto, IM_CRUDOS)

W, H = 64, 48
DESTINOS = {"ffmpeg": ["mkv", "png"], "imagemagick": ["png"]}


def semilla_im(a):
    """La escribe magick, que es quien la va a leer. Devuelve (ruta, bpp)."""
    ref = os.path.join(POOL2, "ref.png")
    if not os.path.exists(ref):
        corre(["magick", "-size", "%dx%d" % (W, H), "gradient:red-blue", "-fill", "white",
               "-draw", "rectangle 8,8 40,30", ref], 60)
    dest = os.path.join(POOL2, "im." + a)
    for f in glob.glob(dest + "*"):
        try:
            os.remove(f)
        except OSError:
            pass
    rc, err, _ = corre(["magick", ref, "-auto-orient", dest], 45)
    cands = sorted(glob.glob(os.path.join(POOL2, "im." + a + "*")))
    if rc != 0 or not cands or os.path.getsize(cands[0]) == 0:
        return None, None, ref, err
    p = cands[0]
    return p, os.path.getsize(p) / float(W * H), ref, ""


def semilla_ff(a):
    ref = os.path.join(POOL2, "ref.mp4")
    if not os.path.exists(ref):
        corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
               "testsrc=size=%dx%d:rate=10:duration=0.5" % (W, H), "-c:v", "libx264",
               "-pix_fmt", "yuv420p", ref], 90)
    dest = os.path.join(POOL2, "ff." + a)
    rc, err, _ = corre(["ffmpeg", "-nostdin", "-y", "-i", ref, dest], 45)
    if rc != 0 or not os.path.exists(dest) or os.path.getsize(dest) == 0:
        return None, None, ref, err
    return dest, os.path.getsize(dest) / float(W * H), ref, ""


if __name__ == "__main__":
    limpia(TMP)
    os.makedirs(POOL2, exist_ok=True)
    prev = json.load(open(os.path.join(SAL, "semi_in_p2.json"), encoding="utf-8"))
    pend = sorted(k for k, v in prev.items() if v.get("estado") != "viva")
    print("SEGUNDA VUELTA sobre %d semiaristas de entrada\n" % len(pend), flush=True)

    res = {}
    for k in pend:
        motor, a = k.split("|")
        if motor == "imagemagick":
            ruta, bpp, ref, errsem = semilla_im(a)
        else:
            ruta, bpp, ref, errsem = semilla_ff(a)
        if ruta is None:
            res[k] = {"estado": "sin_semilla", "err_semilla": errsem[-200:]}
            print("  %-24s SIN SEMILLA (%s)" % (k, errsem[-70:].replace("\n", " ")), flush=True)
            continue
        geom = (W, H)
        # linea base ConvertX sobre la MISMA semilla nueva
        d0 = DESTINOS[motor][0]
        sal0 = os.path.join(TMP, "b.%s" % d0)
        for f in glob.glob(os.path.join(TMP, "*")):
            os.remove(f)
        inv0 = (inv_convertx_ff if motor == "ffmpeg" else inv_convertx_im)(ruta, d0, sal0)
        brc, berr, _ = corre(inv0, 45)
        base_ok = brc == 0 and os.path.exists(sal0) and os.path.getsize(sal0) > 0
        intentos, vivo, cat = [], False, 3
        for d in DESTINOS[motor]:
            for f in glob.glob(os.path.join(TMP, "*")):
                try:
                    os.remove(f)
                except OSError:
                    pass
            sal = os.path.join(TMP, "p.%s" % d)
            if motor == "ffmpeg":
                args, reglas, c, m3 = inv_p2_ff(ruta, d, sal, geom, a)
            else:
                args, reglas, c = inv_p2_im(ruta, d, sal, geom, a)
                m3 = ""
            if args is None:
                intentos.append({"destino": d, "reglas": reglas, "motivo": m3, "rc": None})
                continue
            rc, err, ms = corre(args, 45)
            cands = sorted(x for x in os.listdir(TMP) if x.startswith("p."))
            tam = max([os.path.getsize(os.path.join(TMP, x)) for x in cands], default=-1)
            real = os.path.join(TMP, cands[0]) if cands else None
            son, ver = ({}, {})
            if rc == 0 and tam > 0 and real:
                son, ver = sonda_y_veredicto(real, ref)
            nom, categ, mot, _n2 = juzga(rc, tam, os.path.getsize(ref), d, son, ver)
            intentos.append({"destino": d, "args": args, "reglas": reglas, "rc": rc,
                             "bytes": tam, "ms": round(ms, 1), "veredicto": categ,
                             "motivo": mot, "ancho": son.get("ancho"), "alto": son.get("alto"),
                             "err": err.replace("\n", " ")[-250:] if nom else ""})
            if not nom:
                vivo, cat = True, c
                break
        res[k] = {"estado": "viva" if vivo else "muerta", "categoria_p2": cat if vivo else 3,
                  "bytes_por_pixel": round(bpp, 4) if bpp else None,
                  "bytes_semilla": os.path.getsize(ruta), "semilla": os.path.basename(ruta),
                  "base_convertx_ok": base_ok, "intentos": intentos}
        print("  %-24s bpp=%-7s base=%-6s P2=%-6s %s" %
              (k, round(bpp, 3) if bpp else "-", "OK" if base_ok else "muerta",
               "VIVA" if vivo else "muerta", intentos[-1].get("veredicto", "")), flush=True)

    json.dump(res, open(os.path.join(SAL, "semi_in_p2b.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    viv = sum(1 for v in res.values() if v.get("estado") == "viva")
    print("\nrevividas en la 2a vuelta: %d de %d" % (viv, len(pend)))
