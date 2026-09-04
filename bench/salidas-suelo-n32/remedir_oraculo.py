# -*- coding: utf-8 -*-
"""N32, paso 1 -- REMIDE el oraculo temporal de N9 en ESTA maquina, HOY, antes
de decidir si se sube el suelo. `bench/oraculo-y-gotenberg.md` §1.4 midio p90
de `no_existe` sin ecualizar en 364,65 us el 03/09; la maquina puede haber
cambiado. Es una copia deliberada de la metodologia de
`bench/salidas-oraculo-n9/medir_oraculo.py` (mismos n=2000, mismos dos
testigos de ruido) -- no se reutiliza el script de worker2 para no escribir
sobre su `resultado.json` (CLAUDE.md: "un fichero de salida por agente").

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-suelo-n32/remedir_oraculo.py
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

from filex.confinamiento import Confinamiento, Denegado  # noqa: E402

N = 2000
TOPE_TESTIGO = 20.0


def testigo_proceso():
    ini = time.perf_counter()
    try:
        subprocess.run(["cmd", "/c", "exit", "0"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=TOPE_TESTIGO)
        ms = (time.perf_counter() - ini) * 1000
        return {"ms": round(ms, 2), "sucia": ms > 30, "tope_alcanzado": False}
    except subprocess.TimeoutExpired:
        return {"ms": TOPE_TESTIGO * 1000, "sucia": True, "tope_alcanzado": True}


def preparar():
    tmp = tempfile.mkdtemp(prefix="filex-n32-")
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
    mitad = len(tiempos) // 2
    primera, segunda = tiempos[:mitad], tiempos[mitad:]
    return {
        "mediana_us": round(statistics.median(tiempos) * 1e6, 2),
        "p90_us": round(statistics.quantiles(tiempos, n=10)[8] * 1e6, 2),
        "n": len(tiempos),
        "deriva_primera_vs_segunda_mitad": round(
            statistics.median(segunda) / max(statistics.median(primera), 1e-9), 3),
    }


N_TANDAS = 5  # varias tandas INDEPENDIENTES, no una sola: la del 03/09 estaba
              # SUCIA y su cola de 1,88x no tenia con que compararse.


def una_tanda():
    tmp, permitido, existe, no_existe, prohibido = preparar()
    try:
        testigo_a = testigo_proceso()
        celdas = {"prohibido": prohibido, "no_existe": no_existe, "existe": existe}
        resultado = {"testigo_proceso_antes": testigo_a}

        for etiqueta, ecualizar in (("sin_ecualizar", False), ("ecualizado", True)):
            conf = Confinamiento([permitido], ecualizar_temporal=ecualizar)
            resultado[etiqueta] = {}
            for nombre, ruta in celdas.items():
                t = medir_celda(conf, ruta)
                resultado[etiqueta][nombre] = resumen(t)
                print("%-14s %-10s mediana=%8.2f us  p90=%8.2f us  deriva=%.3f"
                      % (etiqueta, nombre, resultado[etiqueta][nombre]["mediana_us"],
                         resultado[etiqueta][nombre]["p90_us"],
                         resultado[etiqueta][nombre]["deriva_primera_vs_segunda_mitad"]))

        testigo_b = testigo_proceso()
        resultado["testigo_proceso_despues"] = testigo_b
        resultado["sucia"] = testigo_a["sucia"] or testigo_b["sucia"]

        sin_e = resultado["sin_ecualizar"]
        eq = resultado["ecualizado"]
        resultado["ratio_no_existe_sobre_prohibido"] = {
            "sin_ecualizar_mediana": round(
                sin_e["no_existe"]["mediana_us"] / sin_e["prohibido"]["mediana_us"], 2),
            "sin_ecualizar_p90": round(
                sin_e["no_existe"]["p90_us"] / sin_e["prohibido"]["p90_us"], 2),
            "ecualizado_mediana": round(
                eq["no_existe"]["mediana_us"] / eq["prohibido"]["mediana_us"], 2),
            "ecualizado_p90": round(
                eq["no_existe"]["p90_us"] / eq["prohibido"]["p90_us"], 2),
        }
        print("ratio no_existe/prohibido: %s  sucia=%s"
              % (resultado["ratio_no_existe_sobre_prohibido"], resultado["sucia"]))
        return resultado
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    tandas = []
    for i in range(N_TANDAS):
        print("\n=== tanda %d/%d ===" % (i + 1, N_TANDAS))
        tandas.append(una_tanda())

    p90_sin_ecualizar = [t["sin_ecualizar"]["no_existe"]["p90_us"] for t in tandas]
    ratio_p90_ecualizado = [t["ratio_no_existe_sobre_prohibido"]["ecualizado_p90"]
                            for t in tandas]
    import statistics
    resumen_final = {
        "n_tandas": N_TANDAS,
        "sucias": [t["sucia"] for t in tandas],
        "p90_no_existe_sin_ecualizar_us": p90_sin_ecualizar,
        "p90_no_existe_sin_ecualizar_mediana_de_tandas": round(
            statistics.median(p90_sin_ecualizar), 2),
        "p90_no_existe_sin_ecualizar_max": round(max(p90_sin_ecualizar), 2),
        "ratio_p90_ecualizado_por_tanda": ratio_p90_ecualizado,
        "ratio_p90_ecualizado_mediana_de_tandas": round(
            statistics.median(ratio_p90_ecualizado), 3),
        "historico_03_09_p90_no_existe_sin_ecualizar_us": 364.65,
        "historico_03_09_ratio_p90_ecualizado": 1.88,
    }
    print("\n=== RESUMEN de %d tandas ===" % N_TANDAS)
    print(json.dumps(resumen_final, ensure_ascii=False, indent=1))

    with open(os.path.join(os.path.dirname(__file__), "resultado_fresco.json"),
              "w", encoding="utf-8") as fh:
        json.dump({"tandas": tandas, "resumen": resumen_final}, fh,
                  indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
