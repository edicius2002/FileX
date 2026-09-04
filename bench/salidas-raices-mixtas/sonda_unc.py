"""N35 — por que la fila 7 (UNC) discrepa entre NUCLEO y MCP con el MISMO candidato.

En `superficies.json`, la fila `7_MIXTA_con_UNC` con el candidato A da
`DENIEGA_DE_MAS` por el nucleo y `ok` por MCP. El candidato es el mismo, asi
que la diferencia esta en el CAMINO, no en la politica — y hasta saber cual,
esa fila no mide lo que su nombre dice (trampa 38: registra si la condicion
que dices reproducir se dio).

La sospecha razonable es `_uri_a_ruta`: MCP no recibe rutas, recibe URIs
`file://`, y una UNC tiene que sobrevivir al viaje de ida y vuelta. Se sondea,
no se deduce.

Salida: bench/salidas-raices-mixtas/unc.json
"""

from __future__ import annotations

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex import mcp as M  # noqa: E402
from filex.confinamiento import _norm  # noqa: E402


def viaje(ruta: str) -> dict:
    """Lo que le pasa a una ruta al ir por el cable de MCP y volver."""
    uri = "file:///" + ruta.replace(os.sep, "/")
    vuelta = M._uri_a_ruta(uri)
    fila = {
        "ruta_declarada": ruta,
        "uri_que_construye_el_doble": uri,
        "ruta_de_vuelta": vuelta,
        "sobrevive_identica": _norm(os.path.abspath(ruta)) == (
            _norm(os.path.abspath(vuelta)) if vuelta else None),
    }
    if vuelta:
        a = _norm(os.path.abspath(vuelta))
        fila["normalizada_de_vuelta"] = a
        fila["no_confina_de_vuelta"] = (os.path.dirname(a) == a)
    else:
        fila["no_confina_de_vuelta"] = None
        fila["nota"] = "la vuelta es vacia: MCP DESCARTA este root"
    a0 = _norm(os.path.abspath(ruta))
    fila["no_confina_de_ida"] = (os.path.dirname(a0) == a0)
    return fila


def main() -> int:
    casos = [
        r"\\servidor\recurso",
        r"\\servidor\recurso\sub",
        "C:\\",
        r"C:\Users",
        AQUI,
    ]
    filas = [viaje(c) for c in casos]
    # La celda que explica la discrepancia: una raiz que NO confina de ida
    # pero que MCP descarta o transforma, nunca llega a `_preparar`.
    discrepan = [f for f in filas
                 if f["no_confina_de_ida"] != f["no_confina_de_vuelta"]]
    salida = {"filas": filas, "discrepan": discrepan,
              "n_discrepan": len(discrepan)}
    destino = os.path.join(AQUI, "unc.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, indent=2, ensure_ascii=False)
    for f in filas:
        print("%-30s -> uri %-42s -> vuelta %-28r  no_confina ida=%s vuelta=%s" % (
            f["ruta_declarada"][:30], f["uri_que_construye_el_doble"][:42],
            f["ruta_de_vuelta"][:28], f["no_confina_de_ida"],
            f["no_confina_de_vuelta"]))
    print("\ndiscrepan ida/vuelta: %d" % len(discrepan))
    print("-> %s" % destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
