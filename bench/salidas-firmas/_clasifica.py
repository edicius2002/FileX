# -*- coding: utf-8 -*-
"""F1 / paso 3 - CLASIFICAR LOS 502 DESTINOS EN LAS TRES CATEGORIAS.

  1  EVALUABLE Y LO EVALUAMOS  : el verificador ya conoce esa firma
  2  EVALUABLE Y NO LO EVALUAMOS: el formato tiene marcador estable y falta la entrada
  3  NO EVALUABLE POR NATURALEZA: no hay marcador que reconocer

El criterio de la 2 frente a la 3 es MEDIDO: dos o tres escrituras del mismo formato
con contenidos distintos, y las posiciones de los primeros 64 bytes en las que todas
coinciden (_censo_firmas.py / _cont_firmas.py).

Uso: python _clasifica.py
Escribe clasificacion.json y clasificacion.txt
"""
import os, json, sys
from collections import Counter, defaultdict

RAIZ = r"D:\Work\research\FileX"
SAL = os.path.join(RAIZ, r"bench\salidas-firmas")
sys.path.insert(0, os.path.join(RAIZ, "bench", "scripts"))

MIN_PREFIJO = 2   # bytes de prefijo comun para considerar que hay marcador


def carga():
    d = json.load(open(os.path.join(SAL, "firmas_censo_local.json"), encoding="utf-8"))
    try:
        c = json.load(open(os.path.join(SAL, "firmas_censo_contenedor.json"), encoding="utf-8"))
    except OSError:
        c = {}
    for m, v in c.items():
        d[m] = v
    return d


def imprimible(bs):
    return "".join(chr(b) if 32 <= b < 127 else "." for b in bs)


def main():
    cen = carga()
    F = json.load(open(os.path.join(SAL, "formatos.json"), encoding="utf-8"))
    salida = set(F["salida"])
    filas = {f["formato"]: f for f in F["filas"]}

    # mejor evidencia por formato: la que tenga mas prefijo comun
    mejor = {}
    for motor, r in cen.items():
        for b, v in r.items():
            if v.get("estado") != "escrito":
                mejor.setdefault(b, None)
                continue
            cur = mejor.get(b)
            if cur is None or v.get("prefijo_comun", 0) > cur.get("prefijo_comun", 0):
                mejor[b] = v

    res = {}
    for b in sorted(salida):
        v = mejor.get(b)
        fila = dict(filas.get(b, {"formato": b}))
        if not v:
            fila["evidencia"] = "sin_muestra"
            fila["prefijo"] = None
        else:
            pc = v.get("prefijo_comun", 0)
            cabs = v.get("cab") or (v.get("muestras", [{}])[0].get("cab", []))
            cabhex = cabs[0] if cabs else ""
            v = dict(v, cab=cabs)
            pref = bytes.fromhex(cabhex)[:pc] if pc else b""
            fila["evidencia"] = "medida"
            fila["motor_muestra"] = v.get("motor")
            fila["n_muestras"] = v.get("n_muestras")
            fila["prefijo"] = pref.hex()
            fila["prefijo_txt"] = imprimible(pref)
            fila["prefijo_len"] = pc
            fila["pos_estables"] = len(v.get("pos_estables", []))
            fila["val_estables"] = v.get("val_estables")
            fila["cab0"] = cabhex[:96]
            fila["cab1"] = (v.get("cab", ["", ""])[1] if len(v.get("cab", [])) > 1 else "")[:96]
        res[b] = fila

    med = [b for b in res if res[b]["evidencia"] == "medida"]
    sinm = [b for b in res if res[b]["evidencia"] == "sin_muestra"]
    conpref = [b for b in med if res[b]["prefijo_len"] >= MIN_PREFIJO]
    sinpref = [b for b in med if res[b]["prefijo_len"] < MIN_PREFIJO]
    print("destinos declarados        : %d" % len(salida))
    print("con muestra MEDIDA         : %d" % len(med))
    print("   con prefijo >= %d bytes  : %d" % (MIN_PREFIJO, len(conpref)))
    print("   sin prefijo estable     : %d" % len(sinpref))
    print("sin muestra (no escribible): %d" % len(sinm))

    print("\n--- SIN PREFIJO ESTABLE (candidatos a categoria 3) ---")
    print(" ", sorted(sinpref))
    print("\n--- SIN MUESTRA ---")
    print(" ", sorted(sinm))

    # agrupar por prefijo: formatos que comparten marcador
    g = defaultdict(list)
    for b in conpref:
        g[res[b]["prefijo"]].append(b)
    print("\n--- PREFIJOS DISTINTOS: %d ---" % len(g))
    for p, bs in sorted(g.items(), key=lambda kv: -len(kv[1])):
        print("  %-24s %-22s %s" % (p[:24], imprimible(bytes.fromhex(p))[:22], sorted(bs)))

    json.dump(res, open(os.path.join(SAL, "clasificacion.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("\nescrito clasificacion.json")


if __name__ == "__main__":
    main()
