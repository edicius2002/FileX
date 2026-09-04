# -*- coding: utf-8 -*-
"""C50 / worker10 - La SEGUNDA MITAD: leer lo que se ha escrito.

Materializar no basta. En `_agrega.py` una semiarista de entrada solo sale del estrato
indeterminado si ademas se LEE: `_semi_in.py` convierte el fichero materializado a
mkv/wav/png y declara `viva` o `muerta`. Sin esta mitad, lo unico que se habria
demostrado es que el motivo del censo era falso -- no cuantas aristas se mueven.

Se replica la invocacion del censo (`inv_ffmpeg`, que replica a su vez el adaptador de
ConvertX) y se anade una segunda vuelta con el DEMUXER forzado, porque los formatos
crudos (`s16le`, `u8`, `rawvideo`...) no llevan cabecera y ffmpeg no puede adivinar
sus parametros. Las dos columnas se publican: la nominal es la que decide el grafo A
—es la que ConvertX ejecutaria— y la forzada dice si el formato es legible siquiera.

ESCRIBE unicamente en este directorio.
"""
import os, json, time, shutil, collections
import escribe_ff as E

MUESTRAS = os.path.join(E.AQUI, "muestras")
DESTINOS = ["mkv", "wav", "png"]


def lee(n, tok, ruta, forzar):
    d = os.path.join(E.TRABAJO, "L%04d" % n)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    det, vivo = [], False
    for dest in DESTINOS:
        sal = os.path.join(d, "x." + dest)
        if os.path.exists(sal):
            os.remove(sal)
        pre = ["-f", tok] if forzar else []
        argv = ["ffmpeg", "-nostdin", "-y"] + pre + ["-i", ruta, sal]
        rc, err, ms = E.corre(argv, d, 25)
        rc = E.signo(rc)
        tam = os.path.getsize(sal) if os.path.exists(sal) else -1
        det.append({"destino": dest, "rc": rc, "bytes": tam, "ms": round(ms, 1),
                    "clase_rc": E.clase_rc(rc, err),
                    "err": err.replace("\r", "").replace("\n", " | ")[-320:]
                           if (rc != 0 or tam <= 0) else ""})
        if rc == 0 and tam > 0:
            vivo = True
            break
    shutil.rmtree(d, ignore_errors=True)
    return vivo, det


if __name__ == "__main__":
    toks = sorted(f[2:] for f in os.listdir(MUESTRAS) if f.startswith("m."))
    print("muestras a leer: %d" % len(toks), flush=True)
    os.makedirs(E.TRABAJO, exist_ok=True)

    res, n, t0 = {}, 0, time.time()
    for tok in toks:
        ruta = os.path.join(MUESTRAS, "m." + tok)
        n += 1
        v1, d1 = lee(n, tok, ruta, False)
        n += 1
        v2, d2 = lee(n, tok, ruta, True)
        res[tok] = {"bytes_muestra": os.path.getsize(ruta),
                    "nominal": {"vivo": v1, "intentos": d1},
                    "demuxer_forzado": {"vivo": v2, "intentos": d2},
                    "estado_grafoA": "viva" if v1 else "muerta"}
        print("  %-12s nominal=%-6s forzado=%-6s -> %s"
              % (tok, v1, v2, res[tok]["estado_grafoA"]), flush=True)

    vv = sum(1 for v in res.values() if v["nominal"]["vivo"])
    vf = sum(1 for v in res.values() if v["demuxer_forzado"]["vivo"])
    solo_f = sorted(k for k, v in res.items()
                    if v["demuxer_forzado"]["vivo"] and not v["nominal"]["vivo"])
    print("\nVIVAS con la invocacion del censo (grafo A): %d de %d" % (vv, len(res)))
    print("VIVAS con el demuxer forzado:                %d de %d" % (vf, len(res)))
    print("solo legibles forzando el demuxer (%d): %s" % (len(solo_f), solo_f))
    print("(%.0fs, %d celdas de lectura)" % (time.time() - t0, n * len(DESTINOS)))
    json.dump({"vivas_nominal": vv, "vivas_forzado": vf, "solo_forzado": solo_f,
               "res": res},
              open(os.path.join(E.AQUI, "lectura.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
