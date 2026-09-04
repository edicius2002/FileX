"""N35 — los BORDES de la poda: ¿alguna forma de raiz concede lo que antes negaba?

La decision de podar se apoya en dos propiedades: (a) una raiz que no confina
es INERTE, y (b) podar solo QUITA. Las dos estan medidas en el informe sobre
las formas «normales» de raiz, pero una lista blanca la escribe un humano o un
cliente MCP y las formas raras son justo donde vive el fallo.

Esta sonda barre las que se le pueden colar al predicado `dirname(a) == a`:
`..` que sube hasta la unidad, mayusculas, barra de Unix, unidad sin barra,
prefijo extendido `\\\\?\\`, la cadena vacia y una raiz repetida. **La victima
es siempre la misma y esta fuera de toda raiz legitima**: si alguna forma la
deja leer, es una fuga.

Salida: bench/salidas-raices-mixtas/bordes.json
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex.confinamiento import Confinamiento  # noqa: E402


def main() -> int:
    base = tempfile.mkdtemp(prefix="filex-n35-bordes-")
    legit = os.path.join(base, "legit")
    os.makedirs(legit, exist_ok=True)
    victima = r"C:\Windows\win.ini" if sys.platform == "win32" else "/etc/hostname"
    if not os.path.exists(victima):
        print("ABORTA: no existe la victima %r" % victima)
        return 2

    casos = {
        "raiz_con_..._que_sube_a_la_unidad": [os.path.join(base, *([".."] * 8))],
        "raiz_con_..._mas_una_legitima": [os.path.join(legit, "..", ".."), legit],
        "unidad_en_minuscula": ["c:\\", legit],
        "unidad_con_barra_unix": ["C:/", legit],
        "unidad_sin_barra": ["C:", legit],
        "prefijo_extendido": ["\\\\?\\C:\\", legit],
        "cadena_vacia_mas_legitima": ["", legit],
        "raiz_repetida": ["C:\\", "C:\\", legit],
        "solo_unidades_de_varias_formas": ["C:\\", "c:/", "C:"],
    }

    res = {"plataforma": sys.platform, "base": base, "victima": victima,
           "celdas": {}}
    fugas = []
    for nombre, raices in casos.items():
        celda = {"raices_declaradas": list(raices)}
        try:
            c = Confinamiento(raices)
        except ValueError as e:
            celda.update(constructor="ValueError", mensaje=str(e),
                         lee_la_victima=False)
        else:
            celda.update(constructor="ok", lectura_efectiva=list(c.lectura),
                         lee_la_victima=c.puede_leer(victima))
            if celda["lee_la_victima"]:
                fugas.append(nombre)
        res["celdas"][nombre] = celda

    res["fugas"] = fugas
    res["cero_fugas"] = not fugas
    destino = os.path.join(AQUI, "bordes.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)

    print("victima (fuera de toda raiz legitima): %s\n" % victima)
    print("%-36s %-34s %s" % ("caso", "lectura efectiva", "¿lee la victima?"))
    for nombre, c in res["celdas"].items():
        if c["constructor"] != "ok":
            print("%-36s %-34s %s" % (nombre, "ValueError (no arranca)", "no"))
        else:
            ef = ", ".join(os.path.basename(x) or x
                           for x in c["lectura_efectiva"])[:33]
            print("%-36s %-34s %s" % (
                nombre, ef, "SI  <-- FUGA" if c["lee_la_victima"] else "no"))
    print("\ncasos con acceso indebido: %d" % len(fugas))
    print("-> %s" % destino)
    return 0 if not fugas else 1


if __name__ == "__main__":
    raise SystemExit(main())
