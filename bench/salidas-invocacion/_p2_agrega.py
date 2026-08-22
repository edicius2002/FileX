# -*- coding: utf-8 -*-
"""E1 - Contabilidad a nivel de ARISTA a partir del censo de semiaristas.

Una arista (a -> b, motor m) esta:
  MUERTA POR SEMIARISTA  si m no sabe leer a, o no sabe escribir b (ejecutado).
  VIVA POR SEMIARISTAS   si m sabe leer a y escribir b (las dos mitades ejecutadas).
  INDETERMINADA          si no se pudo materializar un fichero de formato a.
Una arista con varios motores esta viva si lo esta por alguno.

Escribe agregado.json y el marco muestral marco.json para el nivel 3.
"""
import os, sys, json
from collections import defaultdict, Counter

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")
E1D = os.path.join(RAIZ, r"bench\salidas-aristas")   # los semi_*.json son de E1: se LEEN


def carga():
    ar = json.load(open(os.path.join(SAL, "aristas.json"), encoding="utf-8"))
    s1 = json.load(open(os.path.join(E1D, "semi_salida.json"), encoding="utf-8"))
    s2 = json.load(open(os.path.join(E1D, "semi_salida2.json"), encoding="utf-8"))
    e1 = json.load(open(os.path.join(E1D, "semi_entrada.json"), encoding="utf-8"))
    e2 = json.load(open(os.path.join(E1D, "semi_entrada2.json"), encoding="utf-8"))
    out = {}
    for k, v in s1.items():
        out[k] = "viva" if (v["vivo"] or s2.get(k, {}).get("vivo", False)) else "muerta"
    ent = {}
    for k, v in e1.items():
        if v["estado"] == "no_materializable":
            ent[k] = "indet"
        else:
            fin = e2.get(k, {}).get("estado", v["estado"])
            ent[k] = "viva" if fin == "viva" else "muerta"
    return ar, ent, out


if __name__ == "__main__":
    ar, ent, out = carga()
    fam = json.load(open(os.path.join(SAL, "censo.json"), encoding="utf-8"))["familias"]

    cnt = Counter()
    marco = []          # aristas con las dos mitades vivas -> muestreables
    muertas_ej = []     # aristas muertas por semiarista ejecutada
    for reg in ar["A"]:
        ab, ms = reg.split("|")
        a, b = ab.split(">")
        motores = ms.split(",")
        estados = []
        for m in motores:
            if m in ("ffmpeg", "imagemagick"):
                ei = ent.get("%s|%s" % (m, a), "indet")
                so = out.get("%s|%s" % (m, b), "indet")
                if ei == "muerta" or so == "muerta":
                    estados.append("muerta")
                elif ei == "viva" and so == "viva":
                    estados.append("viva")
                else:
                    estados.append("indet")
            else:
                estados.append("otro")   # gs / gotenberg: se tratan aparte
        if "viva" in estados:
            e = "viva"
            marco.append((a, b, ms))
        elif "otro" in estados:
            e = "otro_motor"
        elif "indet" in estados:
            e = "indeterminada"
        else:
            e = "muerta"
            muertas_ej.append((a, b, ms))
        cnt[e] += 1

    tot = sum(cnt.values())
    print("ARISTAS DEL GRAFO INSTALADO (grafo A de fidelidad-caminos sec.1.2): %d" % tot)
    for k in ("viva", "muerta", "indeterminada", "otro_motor"):
        print("   %-16s %7d   %5.2f %%" % (k, cnt[k], 100 * cnt[k] / tot))

    # desglose de las muertas: por que mitad
    porq = Counter()
    for a, b, ms in muertas_ej:
        m = ms.split(",")[0]
        ei = ent.get("%s|%s" % (m, a), "?")
        so = out.get("%s|%s" % (m, b), "?")
        porq[("entrada" if ei == "muerta" else "") + ("+salida" if so == "muerta" else "")] += 1
    print("\n   causa (motor principal):", dict(porq))

    json.dump({"conteo": dict(cnt), "total": tot},
              open(os.path.join(SAL, "agregado.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    json.dump({"marco": ["%s>%s|%s" % t for t in marco]},
              open(os.path.join(SAL, "marco.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("\n   marco muestral (aristas con las dos mitades vivas): %d" % len(marco))
