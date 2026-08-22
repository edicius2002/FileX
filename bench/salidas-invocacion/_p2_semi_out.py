# -*- coding: utf-8 -*-
"""P2 / C15-b - REINTENTO de las 37 semiaristas de SALIDA muertas de E1.

Son la mitad que mas aristas mata: 16.202 + 368 de las 22.235 refutadas.
E1 ya hizo una segunda vuelta con semillas mas ricas (CIF, subtitulo, 48 kHz,
JPEG con EXIF) y revivio 9. Estas 37 sobrevivieron a eso, asi que aqui NO se
cambia la semilla: se cambia la INVOCACION.

P2-INV para salidas: -map 0:<tipo> explicito + -c:<t> el codec por DEFECTO DEL
MUXER (sondeado, no deducido) + regla R (restricciones que el propio codificador
declara: gsm solo 8000 Hz mono, dts s16 44100...) + -f <muxer> explicito.
Se prueban las cuatro semillas de E1, igual que su segunda vuelta.

Escribe semi_out_p2.json
"""
import os, sys, json, glob, time

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
TMP = os.path.join(SAL, "tmp_out")
sys.path.insert(0, SAL)
from _p2_lib import (corre, limpia, inv_convertx_ff, inv_convertx_im, inv_p2_ff,
                     inv_p2_im, juzga, sonda_y_veredicto, muxer_de, muxer_info, pistas)

ORDEN_FF = ["video_cif", "subtitulo", "audio48", "jpeg_exif"]
ORDEN_IM = ["jpeg_exif", "png_alfa", "tif16"]

if __name__ == "__main__":
    limpia(TMP)
    inv = json.load(open(os.path.join(SAL, "inventario_e1.json"), encoding="utf-8"))
    idx = json.load(open(os.path.join(SAL, "pool_indice.json"), encoding="utf-8"))
    sem = idx["__semillas__"]
    muertas = sorted(inv["muertas_salida"])
    print("REINTENTO DE %d SEMIARISTAS DE SALIDA MUERTAS\n" % len(muertas), flush=True)

    res = {}
    t0 = time.time()
    for k in muertas:
        motor, b = k.split("|")
        orden = ORDEN_FF if motor == "ffmpeg" else ORDEN_IM
        intentos, vivo, cat, veredicto = [], False, 3, ""
        diag = ""
        if motor == "ffmpeg":
            mux = muxer_de(b)
            mi = muxer_info(mux) if mux else {}
            diag = "muxer=%s v=%s a=%s s=%s" % (mux, mi.get("v"), mi.get("a"), mi.get("s"))
        for mod in orden:
            ent = sem[mod]
            for f in glob.glob(os.path.join(TMP, "*")):
                try:
                    os.remove(f)
                except OSError:
                    pass
            sal = os.path.join(TMP, "p." + b)
            if motor == "ffmpeg":
                args, reglas, c, m3 = inv_p2_ff(ent, b, sal, None, None)
            else:
                args, reglas, c = inv_p2_im(ent, b, sal, None, None)
                m3 = ""
            if args is None:
                intentos.append({"semilla": mod, "reglas": reglas, "motivo": m3, "rc": None})
                continue
            rc, err, ms = corre(args, 60)
            cands = sorted(x for x in os.listdir(TMP) if x.startswith("p."))
            tam = max([os.path.getsize(os.path.join(TMP, x)) for x in cands], default=-1)
            real = os.path.join(TMP, cands[0]) if cands else None
            son, ver = ({}, {})
            if rc == 0 and tam > 0 and real:
                son, ver = sonda_y_veredicto(real, ent)
            nom, categ, mot, _ = juzga(rc, tam, os.path.getsize(ent), b, son, ver)
            intentos.append({"semilla": mod, "args": args, "reglas": reglas, "rc": rc,
                             "bytes": tam, "ms": round(ms, 1), "veredicto": categ,
                             "motivo": mot,
                             "err": err.replace("\n", " ")[-250:] if nom else ""})
            if not nom:
                vivo, cat, veredicto = True, c, categ
                break
        # linea base ConvertX con la misma semilla que revivio (o la primera)
        entb = sem[intentos[-1]["semilla"]] if intentos else sem[orden[0]]
        for f in glob.glob(os.path.join(TMP, "*")):
            try:
                os.remove(f)
            except OSError:
                pass
        sal0 = os.path.join(TMP, "b." + b)
        inv0 = (inv_convertx_ff if motor == "ffmpeg" else inv_convertx_im)(entb, b, sal0)
        brc, berr, _ = corre(inv0, 60)
        base_ok = brc == 0 and os.path.exists(sal0) and os.path.getsize(sal0) > 0
        res[k] = {"estado": "viva" if vivo else "muerta", "categoria_p2": cat if vivo else 3,
                  "veredicto": veredicto, "diagnostico": diag,
                  "base_convertx_ok": base_ok, "intentos": intentos}
        print("  %-22s %-38s base=%-6s P2=%-6s %s" %
              (k, diag[:38], "OK" if base_ok else "muerta",
               "VIVA" if vivo else "muerta", veredicto), flush=True)

    json.dump(res, open(os.path.join(SAL, "semi_out_p2.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    viv = sum(1 for v in res.values() if v["estado"] == "viva")
    print("\nrevividas %d de %d (%.1f %%)  (%.0f s)" %
          (viv, len(muertas), 100 * viv / len(muertas), time.time() - t0))
