"""N35 — ¿discriminan las pruebas nuevas? Con el NOMBRE de cada test, no con su docstring.

La primera version de esta comprobacion era un `grep '\\.\\.\\. (ok|ERROR|FAIL)'`
sobre la salida de `unittest -v`, y tenia dos defectos que hicieron publicar un
recuento falso (trampa 48):

  * **`unittest -v` imprime la primera linea del DOCSTRING**, no el nombre,
    cuando el test tiene docstring. La prueba sin docstring salio en el fichero
    **sin veredicto**, porque el `grep` corto su linea: 1 de los 11 veredictos
    no estaba en la evidencia versionada.
  * **Los `subTest` imprimen una linea por subcaso**, asi que el fichero tenia
    **13 lineas para 11 pruebas** y el informe publico «10 de 11 fallan», que
    no cuadra con «3 pasan».

Aqui se cuenta con un `TestResult`, agrupando por **metodo de test**: una
prueba con subtests cuenta UNA vez, y su veredicto es el peor de sus subcasos.

Uso:
    python sonda_discriminacion.py --salida discriminacion_despues.json
    # revertir filex/confinamiento.py al commit a4dc3f3
    python sonda_discriminacion.py --salida discriminacion_antes.json

Salida: bench/salidas-raices-mixtas/discriminacion_{antes,despues}.json
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

MODULOS = ["pruebas.test_hito1.RaicesMixtasN35",
           "pruebas.test_hito4.RaicesMixtasPorMCP"]


def nombre_de(test) -> str:
    """`clase.metodo`, estable frente a subtests y a los docstrings."""
    t = getattr(test, "test_case", test)          # `_SubTest` guarda el padre
    return "%s.%s" % (type(t).__name__, t._testMethodName)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="discriminacion_despues.json")
    args = ap.parse_args()

    # CONTROL DE IDENTIDAD (trampa 119): que quede registrado QUE codigo se
    # midio, para que «antes» y «despues» no puedan confundirse nunca.
    from filex.confinamiento import Confinamiento
    fuente = inspect.getsource(Confinamiento._preparar)
    codigo = "poda" if "continue" in fuente else "rechaza"

    def recorrer(s, acc):
        for x in s:
            if isinstance(x, unittest.TestSuite):
                recorrer(x, acc)
            else:
                acc.setdefault(nombre_de(x), "ok")
        return acc

    # La suite se RECORRE antes de correrla: un `TestSuite` ya ejecutado deja
    # sus casos a `None` para liberar memoria, y recorrerlo despues revienta.
    veredictos = recorrer(unittest.TestLoader().loadTestsFromNames(MODULOS), {})
    res = unittest.TextTestRunner(
        verbosity=0, stream=open(os.devnull, "w")
    ).run(unittest.TestLoader().loadTestsFromNames(MODULOS))
    for lista, etiqueta in ((res.errors, "ERROR"), (res.failures, "FAIL")):
        for test, _tb in lista:
            veredictos[nombre_de(test)] = etiqueta

    rojas = sorted(k for k, v in veredictos.items() if v != "ok")
    verdes = sorted(k for k, v in veredictos.items() if v == "ok")
    salida = {
        "codigo_medido": codigo,
        "control_de_identidad": "`continue` en _preparar" if codigo == "poda"
                                else "`raise ValueError` en _preparar",
        "n_pruebas": len(veredictos),
        "n_rojas": len(rojas), "n_verdes": len(verdes),
        "rojas": rojas, "verdes": verdes,
        "veredictos": veredictos,
    }
    destino = os.path.join(AQUI, args.salida)
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, indent=2, ensure_ascii=False)

    print("codigo medido: %s  (%s)" % (codigo, salida["control_de_identidad"]))
    print("%d pruebas: %d rojas, %d verdes\n" % (
        len(veredictos), len(rojas), len(verdes)))
    for nombre in sorted(veredictos):
        print("  %-6s %s" % (veredictos[nombre], nombre))
    print("\n-> %s" % destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
