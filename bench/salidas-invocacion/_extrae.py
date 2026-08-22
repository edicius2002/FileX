# -*- coding: utf-8 -*-
"""P2 / paso 0 - extraer de los datos de E1 los casos sospechosos de INVOCACION.

No mide nada: solo lee bench/salidas-aristas/ y produce el inventario de partida.
"""
import os, sys, json
from collections import Counter, defaultdict

RAIZ = r"D:\Work\research\FileX"
E1 = os.path.join(RAIZ, r"bench\salidas-aristas")
SAL = os.path.join(RAIZ, r"bench\salidas-invocacion")


def jload(n):
    return json.load(open(os.path.join(E1, n), encoding="utf-8"))


if __name__ == "__main__":
    se, se2 = jload("semi_entrada.json"), jload("semi_entrada2.json")
    ss, ss2 = jload("semi_salida.json"), jload("semi_salida2.json")
    mu = jload("muestra.json")

    # --- semiaristas de ENTRADA muertas (tras la 2a vuelta de E1)
    muertas_in = {}
    for k, v in se.items():
        est = v.get("estado")
        if est == "muerta":
            v2 = se2.get(k)
            if v2 and v2.get("estado") == "viva":
                continue
            err = ""
            for it in v.get("intentos", []):
                if it.get("err"):
                    err = it["err"]
            muertas_in[k] = err
    print("SEMIARISTAS DE ENTRADA MUERTAS: %d" % len(muertas_in))
    for k in sorted(muertas_in):
        print("   %-22s %s" % (k, muertas_in[k][:120]))

    # --- semiaristas de SALIDA muertas
    muertas_out = {}
    for k, v in ss.items():
        if v["vivo"]:
            continue
        if ss2.get(k, {}).get("vivo"):
            continue
        err = ""
        for it in (ss2.get(k) or v).get("intentos", []):
            if it.get("err"):
                err = it["err"]
        muertas_out[k] = err
    print("\nSEMIARISTAS DE SALIDA MUERTAS: %d" % len(muertas_out))
    cau = Counter()
    for k, e in sorted(muertas_out.items()):
        c = ("Encoder not found" if "Encoder not found" in e else
             "received no packets" if "no packets" in e else
             "no alpha" if "alpha channel" in e else "otra")
        cau[c] += 1
    print("   causas:", dict(cau))

    # --- muestra: nominales por estrato y por motivo
    gen = [r for r in mu["general"] if "nominal" in r]
    pdf = [r for r in mu["pdf"] if "nominal" in r]
    print("\nMUESTRA: general %d, pdf %d" % (len(gen), len(pdf)))
    for nom, rs in (("general", gen), ("pdf", pdf)):
        c = Counter((r["estrato"], r["categoria"]) for r in rs)
        print(" ", nom, dict(c))

    nomi = [r for r in gen if r["nominal"]]
    print("\nNOMINALES en la muestra general: %d" % len(nomi))
    ce = Counter()
    for r in nomi:
        e = r.get("err", "") or r.get("motivo", "")
        for pat in ("Invalid argument", "received no packets", "Encoder not found",
                    "exceeds limit", "alpha channel", "must specify image size",
                    "Unable to find a suitable output format", "no such file",
                    "Could not write", "N2 firma", "N3 "):
            if pat.lower() in e.lower():
                ce[pat] += 1
                break
        else:
            ce["OTRA: " + e[:70]] += 1
    for k, v in ce.most_common(30):
        print("   %4d  %s" % (v, k))

    # guardar el inventario
    json.dump({"muertas_entrada": muertas_in, "muertas_salida": muertas_out,
               "nominales_muestra": nomi,
               "degradados_pdf": [r for r in pdf if r["categoria"] == "DEGRADADO"],
               "nominales_pdf": [r for r in pdf if r["nominal"]]},
              open(os.path.join(SAL, "inventario_e1.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    print("\n-> inventario_e1.json")
