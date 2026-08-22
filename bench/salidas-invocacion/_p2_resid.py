# -*- coding: utf-8 -*-
"""P2 / C15-c - REINTENTO DE LAS 115 ARISTAS NOMINALES DE LA MUESTRA DE E1.

No es una submuestra: es el CENSO de los fallos de la muestra de 498 con la que E1
estimo el 23,1 % de residuo. Reintentar las 115 una a una con P2-INV da la tasa de
recuperacion del residuo con la misma incertidumbre muestral que la cifra original,
sin anadir ninguna nueva.

Cada arista se ejecuta dos veces: con la invocacion de ConvertX (linea base, que
tiene que reproducir el veredicto de E1) y con P2-INV. La salida de las dos se juzga
con el MISMO juez que E1.

Categoria de recuperacion:
  1 revivio solo con banderas que el orquestador puede poner solo;
  2 revivio, pero necesito un dato que NO esta en el fichero (geometria, profundidad);
  3 no revivio.

Escribe resid_p2.json
"""
import os, sys, json, glob, time

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_res")
sys.path.insert(0, SAL)
from _p2_lib import (corre, limpia, inv_convertx_ff, inv_convertx_im, inv_p2_ff,
                     inv_p2_im, juzga, sonda_y_veredicto, muxer_de, muxer_info)
import subprocess

CRUDOS_OK = {}   # formatos crudos ya resueltos por _p2_crudos.py, con su profundidad


def carga_crudos():
    p = os.path.join(SAL, "crudos_p2.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    out = {}
    for k, v in d.items():
        if v.get("estado") == "viva" and v.get("mejor"):
            out[k.split("|")[1]] = v["mejor"]["variante"]
    return out


def encoders():
    p = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, errors="replace", timeout=60)
    e = set()
    for ln in (p.stdout + p.stderr).splitlines():
        t = ln.split()
        if len(t) >= 2 and len(t[0]) == 6 and t[0][0] in "VAS":
            e.add(t[1])
    return e


def ejecuta(args, dest, ent, pref):
    for f in glob.glob(os.path.join(TMP, "*")):
        try:
            os.remove(f)
        except OSError:
            pass
    sal = os.path.join(TMP, pref + "." + dest)
    # OJO: la salida de ImageMagick llega como "fmt:__SAL__", no como "__SAL__".
    # Sustituir por igualdad exacta dejaba el literal en la orden y magick escribia
    # un fichero llamado __SAL__ en el cwd. Se sustituye por SUBCADENA.
    args = [x.replace("__SAL__", sal) for x in args]
    # cwd = directorio desechable: CLAUDE.md sec.4 trampa 21. Lo que el motor escriba
    # fuera del destino cae aqui y se cuenta (quinto punto del contrato).
    rc, err, ms = corre(args, 45, cwd=TMP)
    todos = os.listdir(TMP)
    cands = sorted(x for x in todos if x.startswith(pref))
    extra = [x for x in todos if not x.startswith(pref)]
    tam = max([os.path.getsize(os.path.join(TMP, c)) for c in cands], default=-1)
    real = os.path.join(TMP, cands[0]) if cands else None
    son, ver = ({}, {})
    if rc == 0 and tam > 0 and real:
        son, ver = sonda_y_veredicto(real, ent)
    nom, categ, mot, n2 = juzga(rc, tam, os.path.getsize(ent), dest, son, ver)
    return {"rc": rc, "bytes": tam, "ms": round(ms, 1), "nominal": nom,
            "veredicto": categ, "motivo": mot, "firma": son.get("firma"),
            "n2_evaluable": n2, "n_ficheros": len(cands),
            "fuera_del_destino": extra[:6],
            "err": err.replace("\n", " ")[-220:] if nom else ""}


if __name__ == "__main__":
    limpia(TMP)
    ENC = encoders()
    CRUDOS_OK = carga_crudos()
    inv = json.load(open(os.path.join(SAL, "inventario_e1.json"), encoding="utf-8"))
    idx = json.load(open(os.path.join(SAL, "pool_indice.json"), encoding="utf-8"))
    casos = inv["nominales_muestra"] + inv["nominales_pdf"]
    vistos, lista = set(), []
    for r in casos:
        t = (r["a"], r["b"], r.get("motor"))
        if t in vistos:
            continue
        vistos.add(t)
        lista.append(r)
    print("REINTENTO DE %d ARISTAS NOMINALES (muestra general + estrato PDF)\n" % len(lista),
          flush=True)

    res, t0 = [], time.time()
    for i, r in enumerate(lista):
        a, b, motor = r["a"], r["b"], r.get("motor")
        info = idx.get(a) or {}
        ent = info.get("ruta")
        if not ent:
            res.append(dict(r, p2_estado="sin_semilla"))
            continue
        geom = tuple(info["geometria"]) if info.get("geometria") else None
        # ---- linea base: ConvertX
        inv0 = (inv_convertx_ff if motor == "ffmpeg" else inv_convertx_im)(ent, b, "__SAL__")
        base = ejecuta(inv0, b, ent, "b%03d" % i)
        # ---- P2-INV
        if motor == "ffmpeg":
            args, reglas, cat, m3 = inv_p2_ff(ent, b, "__SAL__", geom, a)
        else:
            args, reglas, cat = inv_p2_im(ent, b, "__SAL__", geom, a)
            m3 = ""
        if args is None:
            p2 = {"rc": None, "nominal": True, "veredicto": "FALLO", "motivo": m3,
                  "bytes": -1}
            catf, causa = 3, m3 or "P2-INV no puede construir la invocacion"
        else:
            # codificador ausente del build -> categoria 3 con causa explicita
            causa = ""
            if motor == "ffmpeg":
                cods = [args[j + 1] for j, x in enumerate(args) if x.startswith("-c:")]
                falta = [c for c in cods if c not in ENC and not c.startswith("lib")]
                if falta:
                    causa = "codificador ausente del build: " + ",".join(falta)
            p2 = ejecuta(args, b, ent, "p%03d" % i)
            if p2["nominal"]:
                catf = 3
                causa = causa or p2.get("err", "")[:120]
            else:
                catf = cat
        res.append(dict(r, p2_estado=("viva" if not p2["nominal"] else "muerta"),
                        p2_categoria=catf, p2_reglas=(reglas if args else []),
                        p2_causa=causa, p2=p2, base=base,
                        p2_args=(args if args else None)))
        if i % 10 == 0:
            print("   %d/%d (%.0fs)" % (i, len(lista), time.time() - t0), flush=True)

    json.dump(res, open(os.path.join(SAL, "resid_p2.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)

    from collections import Counter
    n = len([r for r in res if "p2_estado" in r])
    viv = [r for r in res if r.get("p2_estado") == "viva"]
    print("\nRESULTADO: %d de %d aristas nominales revividas (%.1f %%)" %
          (len(viv), n, 100 * len(viv) / max(1, n)))
    print("  por categoria:", dict(Counter(r["p2_categoria"] for r in res if "p2_categoria" in r)))
    print("  veredicto de las revividas:", dict(Counter(r["p2"]["veredicto"] for r in viv)))
    print("  por estrato:", dict(Counter((r.get("estrato"), r.get("p2_estado")) for r in res)))
    # coherencia: la linea base tiene que reproducir el veredicto NOMINAL de E1
    disc = [r for r in res if "base" in r and not r["base"]["nominal"]]
    print("\n  DISCREPANCIAS con E1 (la linea base NO reproduce el fallo): %d" % len(disc))
    for r in disc[:20]:
        print("     %s>%s (%s): %s" % (r["a"], r["b"], r.get("motor"), r["base"]["veredicto"]))
