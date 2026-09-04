# -*- coding: utf-8 -*-
"""N32, opcion 2 -- mide `FileX.convertir()` YA con el suelo POR OPERACION
(`Confinamiento.operacion()`, `filex/nucleo.py::_resolver`) puesto. Es la
misma metodologia que `bench/salidas-oraculo-n9/medir_convertir.py` (n=500,
mismas tres celdas), para que el ANTES/DESPUES sea comparable: el ANTES ya
esta versionado en `resultado_convertir.json` de esa ronda (existe/prohibido
= 2,111x, mediana; 2,150x aprox a p90).

Comprueba dos cosas:
  1. el residuo existe/prohibido se cierra (objetivo: ~1x, como ya cerro
     no_existe/existe en la ronda anterior).
  2. el coste de la via VALIDA no sube -- el encargo lo exige explicitamente
     ("sin subir el coste del camino valido").

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-suelo-n32/medir_operacion.py
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

N = 500


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
    tmp = tempfile.mkdtemp(prefix="filex-n32-op-")
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
            "existe_sobre_prohibido_mediana": round(
                eq["existe"]["mediana_us"] / eq["prohibido"]["mediana_us"], 3),
            "existe_sobre_prohibido_p90": round(
                eq["existe"]["p90_us"] / eq["prohibido"]["p90_us"], 3),
        }
        # Comparacion directa con la ronda anterior (bench/salidas-oraculo-n9/
        # resultado_convertir.json), citada a mano porque son dos ficheros
        # versionados por agentes distintos (CLAUDE.md: un fichero por agente).
        ANTES_POR_LLAMADA = {
            "existe_mediana_us": 659.55, "existe_p90_us": 715.39,
            "prohibido_mediana_us": 312.50, "prohibido_p90_us": 332.91,
            "ratio_mediana": 2.111, "ratio_p90": round(715.39 / 332.91, 3),
        }
        resultado["comparacion_antes_por_llamada"] = ANTES_POR_LLAMADA
        print("\nAHORA (por operacion), ecualizado: existe/prohibido mediana=%.3fx  p90=%.3fx"
              % (resultado["ratios_ecualizado"]["existe_sobre_prohibido_mediana"],
                 resultado["ratios_ecualizado"]["existe_sobre_prohibido_p90"]))
        print("ANTES (por llamada), ecualizado:    existe/prohibido mediana=%.3fx  p90=%.3fx"
              % (ANTES_POR_LLAMADA["ratio_mediana"], ANTES_POR_LLAMADA["ratio_p90"]))
        print("coste via VALIDA (existe), mediana: %.2f us (antes) -> %.2f us (ahora)"
              % (ANTES_POR_LLAMADA["existe_mediana_us"], eq["existe"]["mediana_us"]))
        print("coste via DENEGADA (prohibido), mediana: %.2f us (antes) -> %.2f us (ahora)"
              % (ANTES_POR_LLAMADA["prohibido_mediana_us"], eq["prohibido"]["mediana_us"]))

        with open(os.path.join(os.path.dirname(__file__), "resultado_operacion.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(resultado, fh, indent=1, ensure_ascii=False)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
