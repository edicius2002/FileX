# -*- coding: utf-8 -*-
"""E1 / Nivel 2c - CENSO DE SEMIARISTAS DE ENTRADA POR EJECUCION.

Para cada formato declarado como ENTRADA por ffmpeg (473) o por ImageMagick (245):
  1) MATERIALIZAR un fichero autentico de ese formato (corpus > ffmpeg > magick);
  2) LEERLO con el motor que lo declara, convirtiendolo a un destino canonico.

Si no se puede materializar, el formato queda NO MATERIALIZABLE y sus aristas salen
del marco muestral, que se declara con su tamano (bench/fidelidad-caminos.md sec.2 es
el modelo: sesgo declarado, no escondido).

SESGO DECLARADO Y FAVORABLE: la mayoria de las semillas las escribe el propio motor
que luego las lee. Es el mejor caso posible para el motor; la tasa de semiaristas de
entrada muertas que salga de aqui es una COTA INFERIOR.

Escribe semi_entrada.json y pool/in/
"""
import os, sys, json, time, shutil, subprocess

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")
POOL = os.path.join(SAL, "pool")
PIN = os.path.join(POOL, "in")
TMP = os.path.join(SAL, "tmp3")
CORPUS = os.path.join(RAIZ, "corpus")
sys.path.insert(0, SAL)
from _semi import corre, inv_ffmpeg, inv_magick, limpia, semillas
from _semi2 import semillas2
import _censo as C


def corpus_por_ext():
    m = {}
    for r, _, fs in os.walk(CORPUS):
        for f in fs:
            e = f.rsplit(".", 1)[-1].lower()
            p = os.path.join(r, f)
            if e not in m or os.path.getsize(p) < os.path.getsize(m[e]):
                m[e] = p
    return m


def materializa(a, sem, sem2, corp, viva_ff_out, viva_im_out):
    """Devuelve (ruta, procedencia) o (None, motivo)."""
    if a in corp:
        return corp[a], "corpus"
    dest = os.path.join(PIN, "m." + a)
    for c in list(os.listdir(PIN)):
        if c.startswith("m." + a):
            try:
                os.remove(os.path.join(PIN, c))
            except OSError:
                pass
    if a in viva_ff_out:
        for mod in ("video_cif", "subtitulo", "audio48", "jpeg_exif"):
            rc, err, ms = corre(inv_ffmpeg(sem2[mod], a, dest), 25)
            if rc == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0:
                return dest, "ffmpeg<-" + mod
    if a in viva_im_out:
        for mod in ("jpeg_exif", "png_alfa"):
            rc, err, ms = corre(inv_magick(sem2[mod], a, dest), 25)
            cands = [x for x in os.listdir(PIN) if x.startswith("m." + a)]
            if rc == 0 and cands:
                p = os.path.join(PIN, sorted(cands)[0])
                if os.path.getsize(p) > 0:
                    return p, "magick<-" + mod
    return None, "no materializable (ningun motor local lo escribe)"


if __name__ == "__main__":
    os.makedirs(PIN, exist_ok=True)
    limpia(TMP)
    sem = semillas()
    sem2 = semillas2()
    corp = corpus_por_ext()

    s1 = json.load(open(os.path.join(SAL, "semi_salida.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(SAL, "semi_salida2.json"), encoding="utf-8"))
    vivas = {k: (v["vivo"] or s2.get(k, {}).get("vivo", False)) for k, v in s1.items()}
    viva_ff_out = {k.split("|")[1] for k, v in vivas.items() if v and k.startswith("ffmpeg|")}
    viva_im_out = {k.split("|")[1] for k, v in vivas.items() if v and k.startswith("imagemagick|")}

    ff_in = {x.lower() for x in C.MOTORES["ffmpeg"][0]}
    im_lee, im_esc = C.im_real()

    res = {}
    t0 = time.time()
    for motor, entradas, inv, destinos in (
            ("ffmpeg", sorted(ff_in), inv_ffmpeg, ["mkv", "wav", "png"]),
            ("imagemagick", sorted(im_lee), inv_magick, ["png"])):
        for i, a in enumerate(entradas):
            ruta, proc = materializa(a, sem, sem2, corp, viva_ff_out, viva_im_out)
            if ruta is None:
                res["%s|%s" % (motor, a)] = {"estado": "no_materializable", "motivo": proc}
                continue
            tam_ent = os.path.getsize(ruta)
            vivo, det = False, []
            for d in destinos:
                sal = os.path.join(TMP, "x.%s" % d)
                if os.path.exists(sal):
                    os.remove(sal)
                rc, err, ms = corre(inv(ruta, d, sal), 25)
                tam = os.path.getsize(sal) if os.path.exists(sal) else -1
                det.append({"destino": d, "rc": rc, "bytes": tam, "ms": round(ms, 1),
                            "err": err.replace("\n", " ")[-200:] if (rc != 0 or tam <= 0) else ""})
                if rc == 0 and tam > 0:
                    vivo = True
                    break
            res["%s|%s" % (motor, a)] = {"estado": "viva" if vivo else "muerta",
                                         "procedencia": proc, "bytes_entrada": tam_ent,
                                         "intentos": det}
            if i % 40 == 0:
                print("  %s in %d/%d  (%.0fs)" % (motor, i, len(entradas), time.time() - t0), flush=True)
        print("  %s in hecho (%.0fs)" % (motor, time.time() - t0), flush=True)

    json.dump(res, open(os.path.join(SAL, "semi_entrada.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    for motor in ("ffmpeg", "imagemagick"):
        sub = {k: v for k, v in res.items() if k.startswith(motor + "|")}
        nm = sum(1 for v in sub.values() if v["estado"] == "no_materializable")
        vv = sum(1 for v in sub.values() if v["estado"] == "viva")
        mu = sum(1 for v in sub.values() if v["estado"] == "muerta")
        print("\n%s: %d declaradas -> %d no materializables, %d vivas, %d MUERTAS (%.1f %% del marco)"
              % (motor, len(sub), nm, vv, mu, 100 * mu / max(1, vv + mu)))
