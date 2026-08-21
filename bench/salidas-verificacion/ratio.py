#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La cifra que decide todo: coste de VERIFICAR dividido por coste de CONVERTIR.

Cruza conversion.json (tiempo real de cada una de las 39 ordenes del patron
oro) con el coste de verificar esa misma salida, medido fichero a fichero con
mediana de n>=9 y con los dos motores.
"""
import json
import os
import statistics
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, AQUI)
import verificador as V           # noqa: E402
from trabajos import trabajos     # noqa: E402
from medir import measure, sonda_entrada, verificar_trabajo   # noqa: E402

# orden del patron oro -> nombre de la salida caracterizada
def mapa_ordenes():
    ref = json.load(open(os.path.join(RAIZ, "bench", "salidas-referencia",
                                      "referencia.json"), encoding="utf-8"))
    return {o["id"]: os.path.basename(o["salida"]) for o in ref["ordenes"]}


def main(n=9):
    conv = {c["id"]: c for c in json.load(
        open(os.path.join(AQUI, "conversion.json"), encoding="utf-8"))}
    mapa = mapa_ordenes()
    porn = {os.path.basename(t["salida"]): t for t in trabajos()}
    filas = []
    for motor in ("proceso", "subproceso"):
        cache = {}
        for t in trabajos():
            sonda_entrada(t, motor, cache)
        for oid, nombre in mapa.items():
            t = porn.get(nombre)
            if t is None or oid not in conv:
                continue
            m = measure("verif[%s] %s" % (motor, oid), n,
                        lambda x=t, mo=motor, c=cache: verificar_trabajo(x, mo, c))
            filas.append({"orden": oid, "cat": conv[oid]["cat"], "motor": motor,
                          "salida": nombre,
                          "bytes_salida": conv[oid]["bytes_salida"],
                          "convertir_ms": conv[oid]["mediana_ms"],
                          "convertir_n": conv[oid]["n"],
                          "verificar_ms": m["mediana_ms"], "verificar_n": n,
                          "verificar_min": m["min_ms"], "verificar_max": m["max_ms"],
                          "flag": m["flag"],
                          "ratio_pct": round(100.0 * m["mediana_ms"] /
                                             conv[oid]["mediana_ms"], 4)})
            print("%-22s %-11s conv %9.1f ms  verif %8.3f ms  ratio %7.3f %%  [%s]"
                  % (oid, motor, conv[oid]["mediana_ms"], m["mediana_ms"],
                     filas[-1]["ratio_pct"], m["flag"]), flush=True)
    with open(os.path.join(AQUI, "ratio.json"), "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=1)

    print("\n=== resumen por categoria (mediana de las ratios) ===")
    for motor in ("proceso", "subproceso"):
        for cat in ("imagen", "audio", "video", "pdf", "datos"):
            sub = [f for f in filas if f["motor"] == motor and f["cat"] == cat]
            if not sub:
                continue
            print("  %-11s %-8s n=%-3d ratio mediana %8.3f %%  (min %.3f  max %.3f)"
                  % (motor, cat, len(sub),
                     statistics.median(f["ratio_pct"] for f in sub),
                     min(f["ratio_pct"] for f in sub),
                     max(f["ratio_pct"] for f in sub)))
        tot_c = sum(f["convertir_ms"] for f in filas if f["motor"] == motor)
        tot_v = sum(f["verificar_ms"] for f in filas if f["motor"] == motor)
        print("  %-11s TOTAL   convertir %9.0f ms  verificar %9.1f ms  ratio %.3f %%"
              % (motor, tot_c, tot_v, 100.0 * tot_v / tot_c))


if __name__ == "__main__":
    main()
