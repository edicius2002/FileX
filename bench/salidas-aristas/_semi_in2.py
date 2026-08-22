# -*- coding: utf-8 -*-
"""E1 / Nivel 2d - CORRECCION de la primera vuelta de semiaristas de ENTRADA.

Fallo propio detectado al revisar los errores: la sonda buscaba exactamente `x.png`,
pero ImageMagick escribe `x-0.png`, `x-1.png`... cuando la entrada tiene varios
fotogramas o capas (avi, gif, mkv, mp4, psd, ptif, ept...). Trece formatos salieron
MUERTOS con stderr VACIO: sintoma clasico de un falso negativo del arnes, no del motor.

Esta vuelta repite solo las declaradas muertas, detectando la salida por prefijo y con
timeout de 60 s (magick delega el video en ffmpeg y es lento).

Escribe semi_entrada2.json
"""
import os, sys, json, time, subprocess

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-aristas")
TMP = os.path.join(SAL, "tmp4")
sys.path.insert(0, SAL)
from _semi import corre, inv_ffmpeg, inv_magick, limpia


def prueba(inv, ruta, dest, n):
    sal = os.path.join(TMP, "y%04d.%s" % (n, dest))
    rc, err, ms = corre(inv(ruta, dest, sal), 60)
    cands = [x for x in os.listdir(TMP) if x.startswith("y%04d" % n)]
    tam = max([os.path.getsize(os.path.join(TMP, c)) for c in cands], default=-1)
    for c in cands:
        try:
            os.remove(os.path.join(TMP, c))
        except OSError:
            pass
    return rc, tam, ms, err.replace("\n", " ")[-220:], len(cands)


if __name__ == "__main__":
    prev = json.load(open(os.path.join(SAL, "semi_entrada.json"), encoding="utf-8"))
    muertas = [k for k, v in prev.items() if v["estado"] == "muerta"]
    print("recomprobando %d semiaristas de entrada" % len(muertas), flush=True)
    limpia(TMP)
    res = {}
    n = 0
    t0 = time.time()
    for k in sorted(muertas):
        motor, a = k.split("|")
        ruta = None
        proc = prev[k]["procedencia"]
        # recuperar la ruta materializada
        for cand in (os.path.join(SAL, "pool", "in", "m." + a),):
            if os.path.exists(cand):
                ruta = cand
        if ruta is None:
            import glob
            g = glob.glob(os.path.join(SAL, "pool", "in", "m." + a + "*"))
            if g:
                ruta = g[0]
        if ruta is None:
            from _semi_in import corpus_por_ext
            corp = corpus_por_ext()
            ruta = corp.get(a)
        if ruta is None:
            res[k] = {"estado": "muerta", "nota": "semilla perdida", "procedencia": proc}
            continue
        inv = inv_ffmpeg if motor == "ffmpeg" else inv_magick
        destinos = ["mkv", "wav", "png"] if motor == "ffmpeg" else ["png", "miff"]
        vivo, det = False, []
        for d in destinos:
            n += 1
            rc, tam, ms, err, nf = prueba(inv, ruta, d, n)
            det.append({"destino": d, "rc": rc, "bytes": tam, "ficheros": nf,
                        "ms": round(ms, 1), "err": err if (rc != 0 or tam <= 0) else ""})
            if rc == 0 and tam > 0:
                vivo = True
                break
        res[k] = {"estado": "viva" if vivo else "muerta", "procedencia": proc,
                  "intentos": det}
        print("  %-24s %-7s %s" % (k, res[k]["estado"], det[-1]["err"][-90:]), flush=True)
    json.dump(res, open(os.path.join(SAL, "semi_entrada2.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    rev = sum(1 for v in res.values() if v["estado"] == "viva")
    print("\nrevividas %d de %d  (%.0fs)" % (rev, len(muertas), time.time() - t0))
