# -*- coding: utf-8 -*-
"""P2 / C15-a - REINTENTO de las 34 semiaristas de ENTRADA muertas de E1.

Una semiarista de entrada muerta mata TODAS las aristas que la usan: 5.665 + 368
de las 22.235 refutadas por E1. Aqui se reintenta cada una con P2-INV y se
clasifica el resultado en las tres categorias del encargo:

  1 recuperable con bandera         (la arista existe; ConvertX la llama mal)
  2 recuperable con parametro del usuario (existe, pero NO es automatica)
  3 irrecuperable                   (el motor no puede)

Cada reintento se verifica con verificador_p2 EN PROCESO y se juzga con el MISMO
juez que E1 (_p2_lib.juzga). Revivir entregando basura no es revivir.

Escribe semi_in_p2.json
"""
import os, sys, json, glob, time

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_in")
sys.path.insert(0, SAL)
from _p2_lib import (corre, limpia, inv_convertx_ff, inv_convertx_im,
                     inv_p2_ff, inv_p2_im, juzga, sonda_y_veredicto, IM_CRUDOS, FF_CRUDOS)

DESTINOS = {"ffmpeg": ["mkv", "wav", "png"], "imagemagick": ["png"]}


def prueba(motor, ent, dest, sal, geom, ent_fmt, ref):
    """Ejecuta P2-INV y devuelve el registro juzgado."""
    for f in glob.glob(sal.rsplit(".", 1)[0] + "*"):
        try:
            os.remove(f)
        except OSError:
            pass
    if motor == "ffmpeg":
        r = inv_p2_ff(ent, dest, sal, geom, ent_fmt)
        args, reglas, cat, motivo3 = r
    else:
        args, reglas, cat = inv_p2_im(ent, dest, sal, geom, ent_fmt)
        motivo3 = ""
    if args is None:
        return {"destino": dest, "args": None, "reglas": reglas, "categoria": cat,
                "motivo": motivo3 or "P2-INV no puede construir la invocacion",
                "rc": None, "bytes": -1, "vivo": False}
    rc, err, ms = corre(args, 45)
    base = os.path.basename(sal).rsplit(".", 1)[0]
    cands = sorted(x for x in os.listdir(TMP) if x.startswith(base))
    tam = max([os.path.getsize(os.path.join(TMP, c)) for c in cands], default=-1)
    real = os.path.join(TMP, cands[0]) if cands else None
    son, ver = ({}, {})
    if rc == 0 and tam > 0 and real:
        son, ver = sonda_y_veredicto(real, ref)
    nom, categ, mot, n2 = juzga(rc, tam, os.path.getsize(ref) if ref else 0, dest, son, ver)
    return {"destino": dest, "args": args, "reglas": reglas, "categoria": cat,
            "rc": rc, "bytes": tam, "ms": round(ms, 1), "vivo": (not nom),
            "veredicto": categ, "motivo": mot,
            "ancho": son.get("ancho"), "alto": son.get("alto"), "firma": son.get("firma"),
            "err": err.replace("\n", " ")[-250:] if nom else ""}


if __name__ == "__main__":
    limpia(TMP)
    inv = json.load(open(os.path.join(SAL, "inventario_e1.json"), encoding="utf-8"))
    idx = json.load(open(os.path.join(SAL, "pool_indice.json"), encoding="utf-8"))
    sem = idx["__semillas__"]
    muertas = sorted(inv["muertas_entrada"])
    print("REINTENTO DE %d SEMIARISTAS DE ENTRADA MUERTAS\n" % len(muertas), flush=True)

    res = {}
    t0 = time.time()
    for k in muertas:
        motor, a = k.split("|")
        info = idx.get(a) or {}
        ent = info.get("ruta")
        if not ent:
            res[k] = {"estado": "sin_semilla"}
            continue
        # referencia de fidelidad: la semilla ORIGINAL de la que salio el fichero
        proc = info.get("procedencia", "")
        ref = sem.get(proc.split("<-")[-1], ent) if "<-" in proc else ent
        geom = tuple(info["geometria"]) if info.get("geometria") else None
        # 1) linea base: la invocacion de ConvertX, para reproducir el veredicto de E1
        base_rc = None
        d0 = DESTINOS[motor][0]
        sal0 = os.path.join(TMP, "base_%s.%s" % (a, d0))
        inv0 = (inv_convertx_ff if motor == "ffmpeg" else inv_convertx_im)(ent, d0, sal0)
        base_rc, base_err, _ = corre(inv0, 45)
        base_ok = base_rc == 0 and os.path.exists(sal0) and os.path.getsize(sal0) > 0
        # 2) P2-INV sobre los destinos canonicos, hasta que uno viva
        intentos = []
        vivo = False
        for d in DESTINOS[motor]:
            sal = os.path.join(TMP, "p2_%s.%s" % (a, d))
            r = prueba(motor, ent, d, sal, geom, a, ref)
            intentos.append(r)
            if r.get("vivo"):
                vivo = True
                break
        cat = min([i["categoria"] for i in intentos]) if vivo else 3
        if vivo:
            cat = [i["categoria"] for i in intentos if i.get("vivo")][0]
        res[k] = {"estado": "viva" if vivo else "muerta", "categoria_p2": cat,
                  "base_convertx_ok": base_ok, "geometria": geom,
                  "procedencia": proc, "intentos": intentos}
        print("  %-24s base=%s  P2=%s  cat=%d  %s" %
              (k, "OK" if base_ok else "muerta", "VIVA" if vivo else "muerta", cat,
               intentos[-1].get("veredicto", "")), flush=True)
        for f in os.listdir(TMP):
            try:
                os.remove(os.path.join(TMP, f))
            except OSError:
                pass

    json.dump(res, open(os.path.join(SAL, "semi_in_p2.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    from collections import Counter
    c = Counter((v.get("estado"), v.get("categoria_p2")) for v in res.values())
    print("\nRESUMEN: %s   (%.0f s)" % (dict(c), time.time() - t0))
    viv = sum(1 for v in res.values() if v.get("estado") == "viva")
    print("revividas %d de %d (%.1f %%)" % (viv, len(muertas), 100 * viv / len(muertas)))
