"""Por que el A/B ancho sale en CERO: que ficheros podrian tocar lo arreglado.

Un resultado nulo necesita saber POR QUE es nulo (trampa 56). Este censo mira,
sobre los mismos 94 ficheros del A/B, cuantos entran siquiera en cada uno de los
seis caminos arreglados dentro del cierre.
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
            if not f.endswith((".txt", ".md")):
                fs.append(os.path.join(raiz, f))
    oro = os.path.dirname(os.path.dirname(ref["salidas"][0]["ruta"]))
    for s in ref["salidas"]:
        for raiz, _, ff in os.walk(oro):
            if s["nombre"] in ff:
                fs.append(os.path.join(raiz, s["nombre"]))
                break

    firmas = collections.Counter()
    det = {"png_16_bits_con_alfa": [], "gif": [], "webp": [],
           "webp_animado": [], "tiff": [], "tiff_packbits": []}
    for p in fs:
        fr = V.firma_real(p)
        firmas[fr] += 1
        if fr == "png":
            d = V.sondear_en_proceso(p)
            if d.get("profundidad_bits") == 16 and d.get("tiene_alfa"):
                det["png_16_bits_con_alfa"].append(p)
        elif fr == "gif":
            det["gif"].append(p)
        elif fr == "webp":
            det["webp"].append(p)
            if b"ANMF" in open(p, "rb").read():
                det["webp_animado"].append(p)
        elif fr == "tiff":
            det["tiff"].append(p)
            try:
                with open(p, "rb") as fh:
                    c = V._tiff_ifd0(fh)
                if 32773 in (c.get(259) or []):
                    det["tiff_packbits"].append(p)
            except Exception:                       # noqa: BLE001
                pass

    r = {"n_ficheros": len(fs), "firmas": dict(firmas),
         "alcance": {k: [os.path.basename(x) for x in v]
                     for k, v in det.items()},
         "n_alcance": {k: len(v) for k, v in det.items()}}
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "censo_alcance.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
    print(json.dumps(r["firmas"], ensure_ascii=False))
    for k, v in r["n_alcance"].items():
        print("%-24s %3d  %s" % (k, v, r["alcance"][k][:6]))
    print("escrito:", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
