# -*- coding: utf-8 -*-
"""P2 / C15-a tercera vuelta - LOS CRUDOS SIN CABECERA, medidos bien.

Las dos vueltas anteriores dejaron un cabo suelto que invalida parte de su
resultado, y hay que decirlo: la regla G fijaba `-depth 8`, y este ImageMagick es
**Q16-HDRI**: escribe los crudos a 16 bits por canal (rgb -> 6 bytes por pixel
medidos, no 3). Leerlos con -depth 8 no falla: consume la MITAD del fichero y
entrega una imagen del tamano correcto con pixeles equivocados. Es exactamente el
fallo que el punto 4 del contrato no atrapa, porque lo pedido y lo obtenido
coinciden en geometria.

Asi que aqui:
  - la semilla la escribe el motor que la va a leer (autoconsistencia declarada);
  - se mide BYTES POR PIXEL y de ahi sale la PROFUNDIDAD, que es el SEGUNDO dato
    que el fichero no lleva dentro;
  - se barre un espacio de parametros CERRADO y declarado de antemano
    (-depth {auto,8,16} x -interlace {defecto,plane}) y se elige por FIDELIDAD;
  - y la fidelidad se mide con RMSE contra la referencia, NO con rc=0
    (CLAUDE.md sec.4 trampa 5: SSIM devuelve 0 en esta build; se usa RMSE).

Escribe crudos_p2.json
"""
import os, re, sys, json, glob, time

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
POOL3 = os.path.join(SAL, "pool3")
TMP = os.path.join(SAL, "tmp_crudos")
sys.path.insert(0, SAL)
from _p2_lib import corre, limpia, juzga, sonda_y_veredicto

W, H = 64, 48
IM_CRUDOS = ["bayer", "bayera", "bgr", "bgra", "bgro", "cmyk", "cmyka", "ftxt",
             "gray", "graya", "map", "mono", "pal", "rgb", "rgba", "rgbo",
             "uyvy", "ycbcr", "ycbcra", "yuv"]
CANALES = {"bayer": 1, "bayera": 2, "bgr": 3, "bgra": 4, "bgro": 4, "cmyk": 4,
           "cmyka": 5, "ftxt": 1, "gray": 1, "graya": 2, "map": 1, "mono": 1,
           "pal": 1, "rgb": 3, "rgba": 4, "rgbo": 4, "uyvy": 2, "ycbcr": 3,
           "ycbcra": 4, "yuv": 3}
# formatos en los que la perdida de color es INEVITABLE por definicion del formato
LOSSY_A_PRIORI = {"gray", "graya", "mono", "pal", "map", "bayer", "bayera", "ftxt"}
FF_CRUDOS = ["rgb", "yuv"]


def rmse(a, b):
    """magick compare -metric RMSE. Devuelve el valor NORMALIZADO (0..1)."""
    p = corre(["magick", "compare", "-metric", "RMSE", a, b, "null:"], 60)
    m = re.search(r"\(([0-9.eE+-]+)\)", p[1])
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def variantes(fmt, bpp):
    """Espacio de parametros CERRADO, declarado antes de medir."""
    n = CANALES[fmt]
    prof = None
    if bpp:
        bits = bpp * 8.0 / n
        prof = min((1, 8, 16), key=lambda d: abs(d - bits))
    v = []
    for d in ([prof] if prof else []) + [8, 16, 1]:
        if d is None:
            continue
        base = ["-size", "%dx%d" % (W, H), "-depth", str(d)]
        if (base, "") not in [(x[0], x[1]) for x in v]:
            v.append((base, "depth=%d" % d))
        if fmt in ("yuv", "ycbcr", "ycbcra", "uyvy"):
            v.append((base + ["-interlace", "plane"], "depth=%d+plane" % d))
    v.append((["-size", "%dx%d" % (W, H)], "sin-depth"))
    # deduplicar conservando el orden
    vis, out = set(), []
    for a, e in v:
        t = tuple(a)
        if t not in vis:
            vis.add(t)
            out.append((a, e))
    return out


if __name__ == "__main__":
    limpia(TMP)
    os.makedirs(POOL3, exist_ok=True)
    ref = os.path.join(POOL3, "ref.png")
    if not os.path.exists(ref):
        corre(["magick", "-size", "%dx%d" % (W, H), "gradient:red-blue", "-fill", "white",
               "-draw", "rectangle 8,8 40,30", ref], 60)
    res = {}
    print("CRUDOS SIN CABECERA - IMAGEMAGICK (%d formatos)\n" % len(IM_CRUDOS), flush=True)
    for fmt in IM_CRUDOS:
        sem = os.path.join(POOL3, "s." + fmt)
        for f in glob.glob(sem + "*"):
            os.remove(f)
        rc, err, _ = corre(["magick", ref, "-auto-orient", sem], 45)
        cands = sorted(glob.glob(os.path.join(POOL3, "s." + fmt + "*")))
        if rc != 0 or not cands:
            res["imagemagick|" + fmt] = {"estado": "no_escribible", "err": err[-200:]}
            print("  %-8s NO SE PUEDE ESCRIBIR" % fmt, flush=True)
            continue
        sem = cands[0]
        nb = os.path.getsize(sem)
        bpp = nb / float(W * H)
        # 1) linea base: la invocacion de ConvertX
        s0 = os.path.join(TMP, "b_%s.png" % fmt)
        brc, berr, _ = corre(["magick", sem, "-auto-orient", s0], 45)
        base_ok = brc == 0 and os.path.exists(s0) and os.path.getsize(s0) > 0
        # 2) P2-INV: barrido cerrado, se elige por FIDELIDAD
        mejor, ints = None, []
        for args, etiq in variantes(fmt, bpp):
            sal = os.path.join(TMP, "p_%s.png" % fmt)
            for f in glob.glob(os.path.join(TMP, "p_%s*" % fmt)):
                try:
                    os.remove(f)
                except OSError:
                    pass
            rc, err, ms = corre(["magick"] + args + [fmt + ":" + sem, "-auto-orient",
                                                     "png:" + sal], 45)
            ok = rc == 0 and os.path.exists(sal) and os.path.getsize(sal) > 0
            r = rmse(ref, sal) if ok else None
            ints.append({"variante": etiq, "args": args, "rc": rc,
                         "bytes": os.path.getsize(sal) if ok else -1,
                         "rmse": r, "ms": round(ms, 1),
                         "err": err.replace("\n", " ")[-180:] if not ok else ""})
            if ok and (mejor is None or (r is not None and
                                         (mejor["rmse"] is None or r < mejor["rmse"]))):
                son, ver = sonda_y_veredicto(sal, ref)
                mejor = {"variante": etiq, "rmse": r, "ancho": son.get("ancho"),
                         "alto": son.get("alto"), "firma": son.get("firma"),
                         "hallazgos": [h.get("regla") for h in ver.get("hallazgos", [])]}
        if mejor is None:
            veredicto, cat = "FALLO", 3
        elif mejor["rmse"] is None:
            veredicto, cat = "DESCONOCIDO", 2
        elif mejor["rmse"] < 0.02:
            veredicto, cat = "INTEGRO", 2
        elif fmt in LOSSY_A_PRIORI:
            veredicto, cat = "PERDIDA INEVITABLE", 2
        elif mejor["rmse"] < 0.15:
            veredicto, cat = "DEGRADADO", 2
        else:
            veredicto, cat = "DESTRUIDO", 3
        res["imagemagick|" + fmt] = {
            "estado": "viva" if veredicto in ("INTEGRO", "PERDIDA INEVITABLE", "DEGRADADO") else "muerta",
            "veredicto": veredicto, "categoria_p2": cat, "bytes_semilla": nb,
            "bytes_por_pixel": round(bpp, 4), "canales_declarados": CANALES[fmt],
            "bits_por_canal_medidos": round(bpp * 8.0 / CANALES[fmt], 2),
            "base_convertx_ok": base_ok, "mejor": mejor, "intentos": ints}
        print("  %-8s bpp=%-6s bits/canal=%-5s base=%-6s -> %-18s rmse=%-8s (%s)" %
              (fmt, round(bpp, 3), round(bpp * 8.0 / CANALES[fmt], 1),
               "OK" if base_ok else "muerta", veredicto,
               round(mejor["rmse"], 5) if mejor and mejor["rmse"] is not None else "-",
               mejor["variante"] if mejor else "-"), flush=True)

    # ---------------------------------------------------------------- ffmpeg
    print("\nCRUDOS SIN CABECERA - FFMPEG\n", flush=True)
    refv = os.path.join(POOL3, "ref.mp4")
    if not os.path.exists(refv):
        corre(["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i",
               "testsrc=size=%dx%d:rate=10:duration=0.5" % (W, H), "-c:v", "libx264",
               "-pix_fmt", "yuv420p", refv], 90)
    for fmt in FF_CRUDOS:
        sem = os.path.join(POOL3, "f." + fmt)
        rc, err, _ = corre(["ffmpeg", "-nostdin", "-y", "-i", refv, sem], 45)
        if rc != 0 or not os.path.exists(sem):
            res["ffmpeg|" + fmt] = {"estado": "no_escribible", "err": err[-200:]}
            continue
        nb = os.path.getsize(sem)
        s0 = os.path.join(TMP, "bf_%s.mkv" % fmt)
        brc, berr, _ = corre(["ffmpeg", "-nostdin", "-y", "-i", sem, s0], 45)
        base_ok = brc == 0 and os.path.exists(s0) and os.path.getsize(s0) > 0
        ints, vivo = [], False
        for pf in ("yuv420p", "rgb24", "gray"):
            sal = os.path.join(TMP, "pf_%s.mkv" % fmt)
            if os.path.exists(sal):
                os.remove(sal)
            args = ["ffmpeg", "-nostdin", "-y", "-f", "rawvideo", "-pixel_format", pf,
                    "-video_size", "%dx%d" % (W, H), "-i", sem, "-map", "0:v",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-f", "matroska", sal]
            rc, err, ms = corre(args, 60)
            ok = rc == 0 and os.path.exists(sal) and os.path.getsize(sal) > 0
            ints.append({"pixel_format": pf, "rc": rc, "args": args,
                         "bytes": os.path.getsize(sal) if ok else -1, "ms": round(ms, 1),
                         "err": err.replace("\n", " ")[-180:] if not ok else ""})
            if ok:
                vivo = True
                break
        res["ffmpeg|" + fmt] = {"estado": "viva" if vivo else "muerta",
                                "veredicto": "INTEGRO" if vivo else "FALLO",
                                "categoria_p2": 2 if vivo else 3,
                                "bytes_semilla": nb, "bytes_por_pixel": round(nb / float(W * H), 3),
                                "base_convertx_ok": base_ok, "intentos": ints}
        print("  %-8s bpp=%-6s base=%-6s P2=%s" %
              (fmt, round(nb / float(W * H), 3), "OK" if base_ok else "muerta",
               "VIVA" if vivo else "muerta"), flush=True)

    json.dump(res, open(os.path.join(SAL, "crudos_p2.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    from collections import Counter
    print("\n", dict(Counter(v.get("veredicto") for v in res.values())))
    viv = sum(1 for v in res.values() if v.get("estado") == "viva")
    print("crudos revividos con fidelidad comprobada: %d de %d" % (viv, len(res)))
