"""Cruza el decodificador VP8L de FileX contra libwebp, sobre los fixtures.

Dos comparaciones, y hacen falta las dos (`bench/cobertura-webp.md` §2.1):
  - el PLANO ALFA entero  (magick <f> -alpha extract -depth 8 gray:-)
  - el RGBA entero        (magick <f> -depth 8 RGBA:-)

El plano alfa no ve el color cruzado ni el restar verde, que por definicion del
formato solo tocan R y B.

    python bench/salidas-cobertura-webp/cruce_libwebp.py

Escribe `cruce-libwebp.json`. Necesita `magick` en el PATH.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "pruebas"))

import fixtures_cob_webp as F                                    # noqa: E402
import test_cob_webp as T                                        # noqa: E402


def main() -> int:
    d = tempfile.mkdtemp(prefix="cruce-webp-")
    casos = [(n, getattr(F, n)) for n in F.MANIFIESTO]
    # los cuatro filtros del ALPH, alcanzados mutando el nibble de la cabecera
    casos += [("PERDIDA_ALPH_CRUDO+filtro%d" % k,
               F.mutar_cabecera_alph(F.PERDIDA_ALPH_CRUDO, filtro=k))
              for k in range(4)]

    filas = []
    for nombre, datos in casos:
        f = os.path.join(d, nombre.replace("+", "_") + ".webp")
        with open(f, "wb") as fh:
            fh.write(datos)
        fila = {"caso": nombre, "bytes": len(datos)}

        p = subprocess.run(["magick", f, "-alpha", "extract", "-depth", "8",
                            "gray:-"], capture_output=True)
        if p.returncode == 0 and nombre != "ANIMADO":
            mio = T._plano_alfa(datos)
            fila["alfa_libwebp"] = hashlib.sha256(p.stdout).hexdigest()
            fila["alfa_filex"] = hashlib.sha256(mio).hexdigest()
            fila["alfa_igual"] = mio == p.stdout
        else:
            fila["alfa_igual"] = None      # animado: FileX no lo decodifica

        if F.trozo(datos, b"VP8L") is not None:
            from filex import verificador as V
            _, _, rgba = V._vp8l_decodificar(F.trozo(datos, b"VP8L"), None,
                                             None, plano_alfa=False)
            q = subprocess.run(["magick", f, "-depth", "8", "RGBA:-"],
                               capture_output=True).stdout
            fila["rgba_libwebp"] = hashlib.sha256(q).hexdigest()
            fila["rgba_filex"] = hashlib.sha256(bytes(rgba)).hexdigest()
            fila["rgba_igual"] = bytes(rgba) == q
            fila["rgba_bytes_distintos"] = sum(
                1 for a, b in zip(rgba, q) if a != b)
        else:
            fila["rgba_igual"] = None      # con perdida: FileX no decodifica VP8
        filas.append(fila)
        print("%-32s alfa=%-5s rgba=%-5s" % (nombre, fila["alfa_igual"],
                                             fila["rgba_igual"]))

    def cuenta(clave, valor):
        return len([f for f in filas if f.get(clave) is valor])

    res = {"alfa_iguales": cuenta("alfa_igual", True),
           "alfa_distintos": cuenta("alfa_igual", False),
           "alfa_no_aplica": cuenta("alfa_igual", None),
           "rgba_iguales": cuenta("rgba_igual", True),
           "rgba_distintos": cuenta("rgba_igual", False),
           "rgba_no_aplica": cuenta("rgba_igual", None)}
    print("\n%s" % res)
    print("los RGBA distintos son el defecto del predictor 13: %s"
          % [f["caso"] for f in filas if f.get("rgba_igual") is False])
    sal = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "cruce-libwebp.json")
    json.dump({"resumen": res, "casos": filas}, open(sal, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("escrito", sal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
