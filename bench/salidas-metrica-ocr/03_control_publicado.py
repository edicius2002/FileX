# -*- coding: utf-8 -*-
"""A7 / paso 3 — CONTROL POSITIVO contra las cifras PUBLICADAS.

Antes de decir "la metrica acentuada mueve X puntos" hay que demostrar que mi
reimplementacion de la metrica CIEGA reproduce las cifras que ya estan
publicadas. Si no, cualquier diferencia podria ser mia y no de la metrica.

Fuente: los `*_cer.json` de `bench/salidas-ocr-ppp/json/`, que guardan el
`cer_pct` de cada una de las 296 celdas de `bench/ocr-ppp-nativos.md`, y los
`*__cer.json` de `bench/salidas-ocrmypdf/texto/`.

Se compara celda a celda contra `cer_ciego` recalculado por 02_recalculo.py
sobre el MISMO fichero de texto.
"""
import io
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(AQUI)


def cargar_recalculo():
    r = json.load(io.open(os.path.join(AQUI, "recalculo.json"), encoding="utf-8"))
    return {f["rel"]: f for f in r["filas"]}


def celdas_publicadas():
    """(ruta_rel_del_txt, cer_publicado) de las tandas que guardan JSON por celda."""
    out = []
    faltan = []
    # --- salidas-ocr-ppp: json/<prefijo>__cer.json, claves 'pppNNN__<doc>'
    jd = os.path.join(BENCH, "salidas-ocr-ppp", "json")
    for fn in sorted(os.listdir(jd)):
        if not fn.endswith("__cer.json"):
            continue
        pref = fn[:-len("__cer.json")]
        d = json.load(io.open(os.path.join(jd, fn), encoding="utf-8"))
        for clave, cel in d.get("res", {}).items():
            if "cer_pct" not in cel:
                continue
            rel = "salidas-ocr-ppp/texto/%s__%s.txt" % (pref, clave)
            out.append(("ocr-ppp-nativos.md", rel, cel["cer_pct"]))
    # --- salidas-ocrmypdf: texto/<prefijo>__cer.json
    td = os.path.join(BENCH, "salidas-ocrmypdf", "texto")
    for fn in sorted(os.listdir(td)):
        if not fn.endswith("__cer.json"):
            continue
        pref = fn[:-len("__cer.json")]
        d = json.load(io.open(os.path.join(td, fn), encoding="utf-8"))
        res = d.get("res", d)
        if not isinstance(res, dict):
            continue
        for clave, cel in res.items():
            if not isinstance(cel, dict) or "cer_pct" not in cel:
                continue
            rel = "salidas-ocrmypdf/texto/%s__%s.txt" % (pref, clave)
            out.append(("ocrmypdf.md", rel, cel["cer_pct"]))
    return out, faltan


def main():
    rec = cargar_recalculo()
    pub, _ = celdas_publicadas()
    ok = 0
    dif = []
    sin_txt = []
    for informe, rel, cerpub in pub:
        f = rec.get(rel)
        if f is None:
            sin_txt.append(rel)
            continue
        # el publicado va redondeado a 1 decimal
        mio = round(f["cer_ciego"], 1)
        if abs(mio - cerpub) <= 0.051:
            ok += 1
        else:
            dif.append({"informe": informe, "rel": rel,
                        "publicado": cerpub, "recalculado_ciego": mio,
                        "recalculado_d4ac": round(f["cer_d4ac"], 1),
                        "recalculado_tildes": round(f["cer_tildes"], 1)})
    print("celdas publicadas con JSON por celda: %d" % len(pub))
    print("  reproducidas por mi metrica CIEGA : %d" % ok)
    print("  discrepantes                      : %d" % len(dif))
    print("  sin fichero de texto en disco     : %d" % len(sin_txt))
    for d in dif[:15]:
        print("    %s  pub=%s  mio=%s" % (d["rel"], d["publicado"],
                                          d["recalculado_ciego"]))
    for s in sin_txt[:10]:
        print("    (sin txt) " + s)
    json.dump({"n_publicadas": len(pub), "reproducidas": ok,
               "discrepantes": dif, "sin_txt": sin_txt},
              io.open(os.path.join(AQUI, "control_publicado.json"), "w",
                      encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
