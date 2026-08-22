# -*- coding: utf-8 -*-
"""P2 / C15-c segunda vuelta - las 105 nominales que P2-INV no revivio a la primera.

Tres reglas mas, y la primera nace de un ERROR DE MI PROPIA POLITICA que conviene
leer entero, porque invierte una recomendacion:

  U   `-frames:v 1 -update 1` cuando el destino es una IMAGEN UNICA y la entrada
      tiene mas de un fotograma. Es la causa mayoritaria del "Invalid argument" que
      E1 encontro en el estrato de ffmpeg: el fichero se escribe, ffmpeg escribe el
      primer fotograma y luego aborta porque no hay patron %d. Categoria 1.
  C2  si el TOKEN DE DESTINO nombra un codificador (vbn, xface), se usa ese.
  NO-C para el muxer `image2`: NO se fuerza el codec. `image2` deduce el codificador
      de la EXTENSION y su "codec por defecto" declarado es mjpeg, asi que forzarlo
      escribe un JPEG dentro de un fichero .ppm -- una salida peor que la de
      ConvertX. Es la excepcion que la regla C necesita, y sale de equivocarme.
  R2  barrido de los parametros que el codificador declara (todas las tasas, no la
      primera) mas la tabla PERFILES para los codecs de geometria fija.

Escribe resid_p2b.json
"""
import os, sys, json, glob, time, subprocess

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_res2")
sys.path.insert(0, SAL)
from _p2_lib import (corre, limpia, juzga, sonda_y_veredicto, muxer_de, muxer_info,
                     encoder_info, pistas, inv_p2_im, im_formatos, IM_TECHO256,
                     IM_EXIGE_ALFA, PAGINADO)
from _p2_semi_out2 import PERFILES, encoders

IMAGEN_UNICA_MUX = {"image2", "image2pipe", "webp", "apng", "gif", "ico"}


def variantes_ff(ent, b, ENC):
    """Devuelve una lista ORDENADA de invocaciones candidatas. Espacio cerrado."""
    mux = muxer_de(b)
    if mux is None:
        return [], "el token no corresponde a ningun muxer", None
    mi = muxer_info(mux)
    admite = {t for t in "vas" if mi.get(t)} or {"v", "a", "s"}
    tiene = pistas(ent)
    util = admite & tiene
    if not util:
        return [], ("el muxer %s admite %s y la entrada tiene %s" %
                    (mux, "".join(sorted(admite)) or "-", "".join(sorted(tiene)) or "-")), mux
    # codecs a usar
    cod = {t: mi.get(t) for t in sorted(util) if mi.get(t)}
    if b in ENC:                                    # regla C2
        ei = encoder_info(b)
        t = "v" if ei.get("pix_fmt") else ("a" if (ei.get("ar") or ei.get("sample_fmt")) else "s")
        if t in util:
            cod = {t: b}
    imagen_unica = mux in IMAGEN_UNICA_MUX
    if imagen_unica and b not in ENC:
        cod = {}                                    # excepcion NO-C: lo decide la extension
    falta = [c for c in cod.values() if c and c not in ENC and not c.startswith("lib")]
    if falta:
        return [], "codificador ausente del build: " + ",".join(falta), mux
    base = []
    for t in sorted(util):
        base += ["-map", "0:" + t]
    if imagen_unica:
        base += ["-frames:v", "1", "-update", "1"]
    opciones = [[]]
    for t, c in sorted(cod.items()):
        if not c or c == "none":
            continue
        pre = ["-c:" + t, c]
        if t == "v":
            alt = PERFILES.get(c, [[]]) or [[]]
            if [] not in alt:
                alt = [[]] + alt
        else:
            ei = encoder_info(c)
            alt = [[]]
            for ar in (ei.get("ar") or [])[:3]:
                for ac in ("2", "1"):
                    alt.append(["-ar", ar, "-ac", ac])
            if ei.get("experimental"):
                alt = [o + ["-strict", "-2"] for o in alt]
        opciones = [o + pre + a for o in opciones for a in alt]
    if not opciones:
        opciones = [[]]
    return [["ffmpeg", "-nostdin", "-y", "-i", ent] + base + o + ["-f", mux, "__SAL__"]
            for o in opciones[:8]], "", mux


def ejecuta(args, dest, ent, pref):
    for f in glob.glob(os.path.join(TMP, "*")):
        try:
            os.remove(f)
        except OSError:
            pass
    sal = os.path.join(TMP, pref + "." + dest)
    args = [x.replace("__SAL__", sal) for x in args]
    rc, err, ms = corre(args, 45, cwd=TMP)
    todos = os.listdir(TMP)
    cands = sorted(x for x in todos if x.startswith(pref))
    tam = max([os.path.getsize(os.path.join(TMP, c)) for c in cands], default=-1)
    real = os.path.join(TMP, cands[0]) if cands else None
    son, ver = ({}, {})
    if rc == 0 and tam > 0 and real:
        son, ver = sonda_y_veredicto(real, ent)
    nom, categ, mot, n2 = juzga(rc, tam, os.path.getsize(ent), dest, son, ver)
    return {"rc": rc, "bytes": tam, "ms": round(ms, 1), "nominal": nom,
            "veredicto": categ, "motivo": mot, "firma": son.get("firma"),
            "n2_evaluable": n2, "n_ficheros": len(cands),
            "fuera_del_destino": [x for x in todos if not x.startswith(pref)][:6],
            "err": err.replace("\n", " ")[-220:] if nom else ""}


if __name__ == "__main__":
    limpia(TMP)
    ENC = encoders()
    idx = json.load(open(os.path.join(SAL, "pool_indice.json"), encoding="utf-8"))
    prev = json.load(open(os.path.join(SAL, "resid_p2.json"), encoding="utf-8"))
    pend = [r for r in prev if r.get("p2_estado") == "muerta"]
    print("SEGUNDA VUELTA sobre %d aristas nominales\n" % len(pend), flush=True)

    res, t0 = [], time.time()
    for i, r in enumerate(pend):
        a, b, motor = r["a"], r["b"], r.get("motor")
        ent = (idx.get(a) or {}).get("ruta")
        if not ent:
            continue
        if motor == "ffmpeg":
            cands, causa, mux = variantes_ff(ent, b, ENC)
        else:
            args, reglas, cat = inv_p2_im(ent, b, "__SAL__", None, a)
            cands, causa, mux = ([args] if args else []), "", "magick"
        mejor, vivo = None, False
        for j, args in enumerate(cands):
            out = ejecuta(args, b, ent, "q%03d" % i)
            if mejor is None or (not out["nominal"] and mejor["nominal"]):
                mejor = out
                mejor["args"] = args
            if not out["nominal"]:
                vivo = True
                break
        if mejor is None:
            mejor = {"nominal": True, "veredicto": "FALLO", "motivo": causa,
                     "rc": None, "bytes": -1}
        res.append(dict(r, p2b_estado=("viva" if vivo else "muerta"),
                        p2b_categoria=(1 if vivo else 3),
                        p2b_causa=(causa or mejor.get("err", "")[:150]),
                        p2b=mejor, p2b_n_variantes=len(cands), p2b_muxer=mux))
        if i % 15 == 0:
            print("   %d/%d (%.0fs)" % (i, len(pend), time.time() - t0), flush=True)

    json.dump(res, open(os.path.join(SAL, "resid_p2b.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    from collections import Counter
    viv = [r for r in res if r["p2b_estado"] == "viva"]
    print("\nrevividas en la 2a vuelta: %d de %d (%.1f %%)" %
          (len(viv), len(res), 100 * len(viv) / max(1, len(res))))
    print("  veredicto:", dict(Counter(r["p2b"]["veredicto"] for r in viv)))
    print("  por estrato:", dict(Counter((r.get("estrato"), r["p2b_estado"]) for r in res)))
    for r in viv:
        print("   VIVA  %-8s -> %-10s %-12s %s" %
              (r["a"], r["b"], r.get("motor"), r["p2b"]["veredicto"]))
