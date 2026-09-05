"""Espia sobre `_predice`: cual de los WebP reales dispara el modo 13.

El A/B ancho sale en cero y hay que decir por que (trampa 56). Para el arreglo
del predictor 13 la pregunta concreta es si algun WebP del corpus o del patron
oro llega siquiera a usarlo. `cobertura-webp.md` §4.2 midio 14 de 50 sobre
imagenes GENERADAS a proposito con alfa texturado; aqui se mide sobre las que
hay.
"""

import collections
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from filex import verificador as V  # noqa: E402

REF = os.path.join(RAIZ, "bench", "salidas-referencia", "referencia.json")


def main() -> int:
    ref = json.load(open(REF, encoding="utf-8"))
    fs = []
    for raiz, _, ff in os.walk(os.path.join(RAIZ, "corpus")):
        for f in ff:
            fs.append(os.path.join(raiz, f))
    oro = os.path.dirname(os.path.dirname(ref["salidas"][0]["ruta"]))
    for s in ref["salidas"]:
        for raiz, _, ff in os.walk(oro):
            if s["nombre"] in ff:
                fs.append(os.path.join(raiz, s["nombre"]))
                break
    webps = [p for p in fs if V.firma_real(p) == "webp"]

    original = V._predice
    filas = []
    for p in webps:
        vistos = collections.Counter()

        def espia(modo, px, i, w, _o=original, _v=vistos):
            _v[modo] += 1
            return _o(modo, px, i, w)

        V._predice = espia
        try:
            r = V.alfa_minimo(p, "webp", exacto=True)
        finally:
            V._predice = original
        filas.append({"fichero": os.path.basename(p),
                      "modos": dict(sorted(vistos.items())),
                      "usa_el_modo_13": 13 in vistos,
                      "alfa_min": r.get("alfa_min"),
                      "via": r.get("via")})

    # CONTROL POSITIVO: un «0 de 6» solo significa algo si el espia dispara
    # donde debe (trampa 66/128). `DEFECTO_MODO13` es el fixture que SI lo usa.
    sys.path.insert(0, os.path.join(RAIZ, "pruebas"))
    import tempfile
    import fixtures_cob_webp as FW
    d = tempfile.mkdtemp(prefix="fixverif-m13-")
    pc = os.path.join(d, "control.webp")
    with open(pc, "wb") as f:
        f.write(FW.DEFECTO_MODO13)
    vistos = collections.Counter()

    def espia_c(modo, px, i, w, _o=original, _v=vistos):
        _v[modo] += 1
        return _o(modo, px, i, w)

    V._predice = espia_c
    try:
        rc = V.alfa_minimo(pc, "webp", exacto=True)
    finally:
        V._predice = original
    control = {"fichero": "DEFECTO_MODO13 (fixture)",
               "modos": dict(sorted(vistos.items())),
               "usa_el_modo_13": 13 in vistos,
               "alfa_min": rc.get("alfa_min"), "via": rc.get("via")}

    r = {"n_webp": len(webps),
         "n_que_usan_el_modo_13": sum(f["usa_el_modo_13"] for f in filas),
         "control_positivo": control,
         "filas": filas}
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "espia_modo13.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
    for f in filas:
        print("%-34s modo13=%-5s modos=%s" % (f["fichero"], f["usa_el_modo_13"],
                                              sorted(f["modos"])))
    print("%d de %d usan el modo 13" % (r["n_que_usan_el_modo_13"], len(webps)))
    print("escrito:", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
