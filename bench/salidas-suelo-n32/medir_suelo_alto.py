# -*- coding: utf-8 -*-
"""N32, opcion 1 -- "sube el suelo por encima del p90". Monkeypatchea
`filex.confinamiento.PISO_TEMPORAL_S` (sin tocar el fichero fuente: es un
experimento, no el cambio final) a un candidato CON MARGEN sobre el p90
fresco de `remedir_oraculo.py` (peor de 5 tandas: 335,09 us) y mide:

  1. si el ratio no_existe/prohibido a p90 se cierra de verdad con el
     candidato, en aislado (Confinamiento.resolver()).
  2. cuanto sube el coste de CADA rechazo real (`prohibido`, mediana y p90)
     frente al suelo actual (300 us) -- el amplificador de DoS que la
     trampa 28 nombra, con numero.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-suelo-n32/medir_suelo_alto.py
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

import filex.confinamiento as C  # noqa: E402
from filex.confinamiento import Denegado  # noqa: E402

N = 2000
CANDIDATO_S = 0.0005  # 500 us: margen sobre el peor p90 fresco (335,09 us) y sobre el historico del 03/09 (364,65 us)


def preparar():
    tmp = tempfile.mkdtemp(prefix="filex-n32-alto-")
    permitido = os.path.join(tmp, "permitido")
    os.makedirs(permitido)
    existe = os.path.join(permitido, "s.txt")
    with open(existe, "w", encoding="utf-8") as fh:
        fh.write("x")
    no_existe = os.path.join(permitido, "no_existe.txt")
    prohibido = os.path.join(tmp, "prohibido", "x.txt")
    return tmp, permitido, existe, no_existe, prohibido


def medir_celda(conf, ruta, n=N):
    tiempos = []
    for _ in range(n):
        ini = time.perf_counter()
        try:
            conf.resolver(ruta)
        except Denegado:
            pass
        tiempos.append(time.perf_counter() - ini)
    return tiempos


def resumen(tiempos):
    return {
        "mediana_us": round(statistics.median(tiempos) * 1e6, 2),
        "p90_us": round(statistics.quantiles(tiempos, n=10)[8] * 1e6, 2),
        "n": len(tiempos),
    }


def main():
    tmp, permitido, existe, no_existe, prohibido = preparar()
    try:
        resultado = {"suelo_actual_s": 0.0003, "suelo_candidato_s": CANDIDATO_S}
        celdas = {"prohibido": prohibido, "no_existe": no_existe, "existe": existe}

        for etiqueta, suelo in (("suelo_actual_300us", 0.0003),
                                 ("suelo_candidato_500us", CANDIDATO_S)):
            C.PISO_TEMPORAL_S = suelo
            conf = C.Confinamiento([permitido], ecualizar_temporal=True)
            resultado[etiqueta] = {}
            for nombre, ruta in celdas.items():
                t = medir_celda(conf, ruta)
                resultado[etiqueta][nombre] = resumen(t)
                print("%-22s %-10s mediana=%8.2f us  p90=%8.2f us"
                      % (etiqueta, nombre, resultado[etiqueta][nombre]["mediana_us"],
                         resultado[etiqueta][nombre]["p90_us"]))

        act = resultado["suelo_actual_300us"]
        can = resultado["suelo_candidato_500us"]
        resultado["ratio_p90_no_existe_sobre_prohibido"] = {
            "suelo_actual": round(act["no_existe"]["p90_us"] / act["prohibido"]["p90_us"], 3),
            "suelo_candidato": round(can["no_existe"]["p90_us"] / can["prohibido"]["p90_us"], 3),
        }
        resultado["coste_del_rechazo_prohibido"] = {
            "mediana_actual_us": act["prohibido"]["mediana_us"],
            "mediana_candidato_us": can["prohibido"]["mediana_us"],
            "incremento_x": round(
                can["prohibido"]["mediana_us"] / act["prohibido"]["mediana_us"], 3),
        }
        print("\nratio p90 no_existe/prohibido: actual(300us)=%.3f  candidato(500us)=%.3f"
              % (resultado["ratio_p90_no_existe_sobre_prohibido"]["suelo_actual"],
                 resultado["ratio_p90_no_existe_sobre_prohibido"]["suelo_candidato"]))
        print("coste de CADA rechazo real (mediana): %.2f us -> %.2f us (x%.3f)"
              % (resultado["coste_del_rechazo_prohibido"]["mediana_actual_us"],
                 resultado["coste_del_rechazo_prohibido"]["mediana_candidato_us"],
                 resultado["coste_del_rechazo_prohibido"]["incremento_x"]))

        with open(os.path.join(os.path.dirname(__file__), "resultado_suelo_alto.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(resultado, fh, indent=1, ensure_ascii=False)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
