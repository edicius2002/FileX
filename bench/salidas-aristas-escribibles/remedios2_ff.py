# -*- coding: utf-8 -*-
"""C50 / worker10 - PASADA 3: los mismos remedios CON el muxer forzado.

Por que existe este fichero: la pasada 2 (`remedios_ff.py`) construye el `argv` como
`ffmpeg -i SEM <remedio> <dest>` y **pierde el `-f <token>`** que la pasada 1 si
llevaba, asi que el muxer volvia a deducirse de la extension. Diez tokens la pasaron
igual (la extension coincide con el muxer), pero los que fallaron devolvieron
`Error initializing the muxer ...: Invalid argument`, que es la firma de haber
elegido otro muxer o de no haberle dado el codec que espera.

**Es un defecto del arnes, no un segundo intento del problema** (CLAUDE.md sec.5:
*fuerza el muxer*). Se corrige y se vuelve a medir; el resultado de la pasada 2 se
publica igual, porque la diferencia entre las dos pasadas ES el dato.

ESCRIBE unicamente en este directorio.
"""
import os, json, time
import escribe_ff as E
from remedios_ff import R

if __name__ == "__main__":
    p1 = json.load(open(os.path.join(E.AQUI, "escritura_ff.json"), encoding="utf-8"))["res"]
    p2 = json.load(open(os.path.join(E.AQUI, "remedios_ff.json"), encoding="utf-8"))
    pend = sorted(k for k, v in p2.items() if not v["materializado"] and k in R)
    sem = E.semillas()
    os.makedirs(E.TRABAJO, exist_ok=True)
    print("pendientes con remedio en la tabla: %d  %s\n" % (len(pend), pend))

    res, n, t0 = {}, 6000, time.time()
    for tok in pend:
        celdas, ok = [], False
        for mod, extra, porque in R[tok]:
            n += 1
            c = E.celda(n, tok, mod, sem[mod], "remedio+muxer", ["-f", tok] + list(extra))
            c["motivo_del_remedio"] = porque
            celdas.append(c)
            if c["ok"]:
                ok = True
                break
        res[tok] = {"materializado": ok, "celdas": celdas,
                    "remedio": " ".join(celdas[-1]["argv"][5:-1]) if ok else None,
                    "bytes": celdas[-1]["bytes"] if ok else -1}
        print("  %-10s %s" % (tok, ("ESCRITO %d B  [%s]" % (celdas[-1]["bytes"], res[tok]["remedio"]))
                              if ok else "no (%s)" % ", ".join(sorted({c["clase_rc"] for c in celdas}))), flush=True)

    esc = sum(1 for v in res.values() if v["materializado"])
    print("\nRECUPERADOS POR EL `-f` QUE FALTABA: %d de %d  (%.0fs)" % (esc, len(pend), time.time() - t0))
    json.dump(res, open(os.path.join(E.AQUI, "remedios2_ff.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
