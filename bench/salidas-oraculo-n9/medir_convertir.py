# -*- coding: utf-8 -*-
"""N9, segunda mitad -- verifica el suelo al nivel de `FileX.convertir()`, no
del `Confinamiento.resolver()` aislado. `_resolver()` en `nucleo.py` llama a
`Confinamiento.resolver()` DOS VECES para un `convertir()` que pasa de largo
la lista blanca (entrada + directorio de salida), y solo UNA vez para uno que
se deniega en la entrada (nunca llega a resolver la salida): con el suelo
puesto por LLAMADA, eso deja un residuo de ~2x entre «prohibido» y
«no existe»/«existe» que el primer script (medir_oraculo.py, sobre
`Confinamiento.resolver()` en aislado) no puede ver.

Lo que SÍ hace falta comprobar es si «no existe» y «existe» quedan
INDISTINGUIBLES entre sí (el oráculo de existencia que trampa 28 nombra), y
cuánto le queda de ventaja a «prohibido» frente a los otros dos.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-oraculo-n9/medir_convertir.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

from filex.nucleo import FileX  # noqa: E402

N = 500  # convertir() hace más trabajo que resolver(): n menor, sigue siendo holgado


def medir(fx, entrada, salida, n=N):
    tiempos = []
    for _ in range(n):
        ini = time.perf_counter()
        fx.convertir(entrada, salida)
        tiempos.append(time.perf_counter() - ini)
    return tiempos


def resumen(tiempos):
    return {"mediana_us": round(statistics.median(tiempos) * 1e6, 2),
            "p90_us": round(statistics.quantiles(tiempos, n=10)[8] * 1e6, 2)}


def main():
    tmp = tempfile.mkdtemp(prefix="filex-n9-conv-")
    permitido = os.path.join(tmp, "permitido")
    os.makedirs(permitido)
    existe = os.path.join(permitido, "e.txt")
    with open(existe, "w", encoding="utf-8") as fh:
        fh.write("x")
    no_existe = os.path.join(permitido, "no_existe.txt")
    prohibido = os.path.join(tmp, "fuera", "x.txt")
    salida = os.path.join(permitido, "out.txt")

    try:
        resultado = {}
        for etiqueta, eq in (("sin_ecualizar", False), ("ecualizado", True)):
            fx = FileX(raices_lectura=[permitido], ecualizar_temporal=eq)
            resultado[etiqueta] = {}
            for nombre, ent in (("prohibido", prohibido), ("no_existe", no_existe),
                               ("existe", existe)):
                t = medir(fx, ent, salida)
                resultado[etiqueta][nombre] = resumen(t)
                print("%-14s %-10s mediana=%8.2f us  p90=%8.2f us"
                      % (etiqueta, nombre, resultado[etiqueta][nombre]["mediana_us"],
                         resultado[etiqueta][nombre]["p90_us"]))

        eq = resultado["ecualizado"]
        resultado["ratios_ecualizado"] = {
            "no_existe_sobre_existe": round(
                eq["no_existe"]["mediana_us"] / eq["existe"]["mediana_us"], 3),
            "existe_sobre_prohibido": round(
                eq["existe"]["mediana_us"] / eq["prohibido"]["mediana_us"], 3),
        }
        print("\necualizado: no_existe/existe = %.3fx (objetivo: ~1, oráculo de "
              "EXISTENCIA cerrado si converge)"
              % resultado["ratios_ecualizado"]["no_existe_sobre_existe"])
        print("ecualizado: existe/prohibido = %.3fx (residuo esperado: ~2x, "
              "porque convertir() resuelve DOS rutas y prohibido corta en la "
              "primera)" % resultado["ratios_ecualizado"]["existe_sobre_prohibido"])

        with open(os.path.join(os.path.dirname(__file__), "resultado_convertir.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(resultado, fh, indent=1, ensure_ascii=False)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
