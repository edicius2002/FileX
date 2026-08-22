# -*- coding: utf-8 -*-
"""F1 / paso 5c - G6 SOBRE LA MUESTRA DE E1, sin volver a convertir 598 aristas.

`_remuestra.py` evalua el punto 1 SIN sonda de entrada, asi que la regla G6 ("la
salida tiene la misma firma que la entrada y se pidio otra cosa") no llega a
dispararse. G6 solo depende de cuatro datos, y los cuatro estan guardados o son
baratos: la firma de la SALIDA (esta en remuestra.json), la extension pedida, la
extension de la entrada y la firma de la ENTRADA.

Aqui se rematerializan las 188 semillas de entrada con la misma receta y la misma
procedencia que registro E1, se les calcula la firma con el vocabulario nuevo, y se
aplica el predicado de G6 a las 598 filas ya medidas.

Uso: python _g6.py
Escribe g6.json
"""
import os, sys, json, glob, shutil, subprocess
from collections import Counter

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
ARI = os.path.join(RAIZ, r"bench\salidas-aristas")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))
sys.path.insert(0, SAL)
import verificador as V
import _remuestra as R


def main():
    filas = json.load(open(os.path.join(SAL, "remuestra.json"), encoding="utf-8"))["filas"]
    sein = json.load(open(os.path.join(ARI, "semi_entrada.json"), encoding="utf-8"))
    proc = {}
    for k, v in sein.items():
        a = k.split("|")[1]
        if v.get("estado") != "no_materializable":
            proc.setdefault(a, v.get("procedencia"))

    os.makedirs(R.PIN, exist_ok=True)
    R.limpia(R.TMP)
    sem = R.semillas()
    corp = R.corpus_por_ext()
    origenes = sorted({r["a"] for r in filas})
    firma_ent, ext_ent = {}, {}
    for i, a in enumerate(origenes):
        p = R.materializa(a, proc.get(a), sem, corp)
        if p and os.path.exists(p):
            firma_ent[a] = V.firma_real(p)
            ext_ent[a] = os.path.splitext(p)[1].lower()
        if i % 40 == 0:
            print("   %d/%d" % (i, len(origenes)), flush=True)

    disparos = []
    for r in filas:
        f = r.get("firma_nueva")
        if not f:
            continue
        ext = os.path.splitext("x." + r["b"])[1].lower()
        if ext in V.EXT_A_FIRMAS:
            continue
        if f in V.FIRMAS_INDEFINIDAS:
            continue
        if firma_ent.get(r["a"]) != f:
            continue
        if ext_ent.get(r["a"]) == ext:
            continue
        disparos.append(dict(r, firma_entrada=firma_ent.get(r["a"])))

    print("\nG6 se dispara en %d de las %d filas de la muestra" % (len(disparos), len(filas)))
    print("  por categoria de E1:", dict(Counter(d.get("e1_categoria") for d in disparos)))
    print("  nominales segun E1 :", sum(1 for d in disparos if d.get("e1_nominal")))
    print("  REALES segun E1    :", sum(1 for d in disparos if d.get("e1_nominal") is False),
          " <- son las que G6 anade sobre lo que E1 vio")
    c = Counter((d["b"], d["firma_nueva"]) for d in disparos)
    for (b, f), n in c.most_common(60):
        print("     %-14s %-12s %d" % (b, f, n))
    json.dump({"n_disparos": len(disparos), "disparos": disparos,
               "firma_entrada": firma_ent},
              open(os.path.join(SAL, "g6.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    shutil.rmtree(R.POOL, ignore_errors=True)
    R.limpia(R.TMP)
    print("\nescrito g6.json")


if __name__ == "__main__":
    main()
