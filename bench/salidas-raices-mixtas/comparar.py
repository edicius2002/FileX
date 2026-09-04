"""N35 — el diff celda a celda de `regresion_antes.json` contra `_despues.json`.

Clasifica cada fila en las cuatro cosas que hay que demostrar:

  RECUPERA_ACCESO   una raiz legitima que antes se perdia y ahora se lee (N35)
  SIN_CAMBIO        identica en las dos corridas — lo que se exige de N7
  GANA_ACCESO       lee algo que antes NO leia y NO deberia: seria la FUGA
  PIERDE_ACCESO     deja de leer algo que antes leia

La celda que decide que no se reabrio la fuga de ayer es
`2_solo_raiz_de_unidad_N7`: tiene que salir SIN_CAMBIO.

Salida: bench/salidas-raices-mixtas/comparacion.json
"""

from __future__ import annotations

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))


def cargar(nombre):
    with open(os.path.join(AQUI, nombre), encoding="utf-8") as fh:
        return json.load(fh)


def acceso(celda) -> dict:
    """Lo unico que importa comparar: que concede la celda, no como lo dice."""
    if celda["constructor"] != "ok":
        return {"lee": {}, "escribe": False, "arranca": False}
    return {"lee": {k: v for k, v in celda["lee"].items()},
            "escribe": celda["escribe"], "arranca": True}


def main() -> int:
    antes, despues = cargar("regresion_antes.json"), cargar("regresion_despues.json")
    if antes["base"] != despues["base"]:
        print("ABORTA: las dos corridas usan bases distintas, no son comparables")
        return 2

    filas, resumen = {}, {}
    for nombre in despues["celdas"]:
        a, d = acceso(antes["celdas"][nombre]), acceso(despues["celdas"][nombre])
        gana = sorted(k for k, v in d["lee"].items() if v and not a["lee"].get(k))
        pierde = sorted(k for k, v in a["lee"].items() if v and not d["lee"].get(k))
        gana_escr = d["escribe"] and not a["escribe"]
        pierde_escr = a["escribe"] and not d["escribe"]

        # El unico acceso que es legitimo GANAR es el de la propia raiz
        # declarada: O1. Ganar cualquier otro objetivo seria una fuga.
        fuga = [k for k in gana if not k.startswith("O1_")]
        if fuga:
            clase = "GANA_ACCESO_INDEBIDO"
        elif gana or gana_escr:
            clase = "RECUPERA_ACCESO"
        elif pierde or pierde_escr:
            clase = "PIERDE_ACCESO"
        else:
            clase = "SIN_CAMBIO"
        filas[nombre] = {
            "clase": clase, "gana": gana, "pierde": pierde,
            "gana_escritura": gana_escr, "pierde_escritura": pierde_escr,
            "constructor_antes": antes["celdas"][nombre]["constructor"],
            "constructor_despues": despues["celdas"][nombre]["constructor"],
            "objetivos_ganados_indebidos": fuga,
        }
        resumen[clase] = resumen.get(clase, 0) + 1

    n7 = filas["2_solo_raiz_de_unidad_N7"]["clase"]
    salida = {
        "base": despues["base"], "filas": filas, "resumen": resumen,
        "N7_no_reabierta": n7 == "SIN_CAMBIO",
        "cero_fugas": resumen.get("GANA_ACCESO_INDEBIDO", 0) == 0,
    }
    destino = os.path.join(AQUI, "comparacion.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, indent=2, ensure_ascii=False)

    print("%-34s %-12s %-12s %s" % ("fila", "antes", "despues", "clase"))
    for nombre, f in filas.items():
        print("%-34s %-12s %-12s %s" % (
            nombre, f["constructor_antes"][:11], f["constructor_despues"][:11],
            f["clase"]))
    print("\nresumen: %s" % resumen)
    print("N7 no reabierta (la fila N7 sale SIN_CAMBIO): %s" % salida["N7_no_reabierta"])
    print("cero accesos indebidos ganados:               %s" % salida["cero_fugas"])
    print("\n-> %s" % destino)
    return 0 if (salida["N7_no_reabierta"] and salida["cero_fugas"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
