"""N35 — sonda 0: QUE cuenta como «raiz que no confina», sondeado en ejecucion.

El encargo habla de «raices que confinan» y «raices que no confinan» como si
fueran dos clases conocidas. Lo unico escrito en el codigo es el predicado
`os.path.dirname(a) == a` de `Confinamiento._preparar`. Antes de decidir si el
conjunto mixto se poda o se rechaza hay que saber CUANTAS clases hay y cuales,
porque una regla que descarte «las que no confinan» descarta exactamente lo que
ese predicado marque — ni mas ni menos.

Regla del proyecto: sondear en ejecucion, no deducir (CLAUDE.md §5).

Salida: bench/salidas-raices-mixtas/vocabulario.json
"""

from __future__ import annotations

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex import confinamiento as _conf  # noqa: E402


def clasificar(r: str) -> dict:
    """Reproduce el predicado de `_preparar` paso a paso, sin ocultar nada."""
    fila = {"declarada": r}
    try:
        a = _conf._norm(os.path.abspath(r))
        fila["normalizada"] = a
        padre = os.path.dirname(a)
        fila["dirname"] = padre
        fila["no_confina"] = (padre == a)
    except Exception as e:  # noqa: BLE001
        fila["error"] = "%s: %s" % (type(e).__name__, e)
        fila["no_confina"] = None
    # Y el veredicto REAL del constructor, que es lo que decide de verdad.
    try:
        _conf.Confinamiento([r])
        fila["constructor"] = "ok"
    except ValueError as e:
        fila["constructor"] = "ValueError: %s" % e
    except Exception as e:  # noqa: BLE001
        fila["constructor"] = "%s: %s" % (type(e).__name__, e)
    return fila


def main() -> int:
    candidatas = [
        # --- las que se esperan CONFINANTES
        AQUI,
        RAIZ,
        os.path.join(RAIZ, "corpus"),
        os.path.join(RAIZ, "corpus") + os.sep,      # con barra final
        os.path.join(RAIZ, "corpus", ".."),          # con `..` dentro
        "corpus",                                    # relativa
        # --- las que se esperan NO confinantes (raiz de unidad)
        "C:\\",
        "C:/",
        "c:\\",
        "D:\\",
        os.path.abspath(os.sep),
        # --- casos que NADIE ha clasificado y deciden el alcance de la poda
        "C:",                                        # unidad SIN barra
        "\\\\servidor\\recurso",                     # UNC
        "\\\\servidor\\recurso\\sub",                # UNC con subdirectorio
        "\\\\?\\C:\\",                               # prefijo extendido
        "",                                          # vacia
        ".",
    ]
    filas = [clasificar(c) for c in candidatas]
    salida = {
        "plataforma": sys.platform,
        "python": sys.version.split()[0],
        "predicado": "os.path.dirname(_norm(abspath(r))) == _norm(abspath(r))",
        "filas": filas,
        "n_no_confina": sum(1 for f in filas if f.get("no_confina") is True),
        "n_confina": sum(1 for f in filas if f.get("no_confina") is False),
    }
    destino = os.path.join(AQUI, "vocabulario.json")
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, indent=2, ensure_ascii=False)
    for f in filas:
        print("%-34s no_confina=%-5s  %s" % (
            repr(f["declarada"])[:34], f.get("no_confina"), f.get("constructor")))
    print("\n-> %s" % destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
