# -*- coding: utf-8 -*-
"""N9 -- mide el oráculo temporal de R4 (trampa 28) EN ESTA máquina (worktree
`C:`, no las cifras históricas de `D:\\Work\\research\\FileX`, que no son
comparables) y verifica que el suelo `ecualizar_temporal=True` de
`Confinamiento.resolver()` cierra la brecha sin convertirse en un suelo
absurdamente caro.

Tres celdas, medianas de n=2000 (in-process, no hay proceso que lanzar, igual
que hizo `hito7-superficies.md` §7.2):
  - prohibido: ruta fuera de la lista blanca (corta en R1, nunca toca disco)
  - no_existe: ruta dentro de la raíz, componente final ausente
  - existe:    ruta dentro de la raíz, fichero real

Cada celda se mide DOS veces: con `ecualizar_temporal=False` (reproduce la
asimetría ya publicada, control negativo) y con `True` (verifica que converge).

Dos testigos de ruido:
  A. Deriva monohilo: mediana de la primera mitad de cada celda contra la
     segunda mitad -- un desplazamiento grande dentro de la propia celda avisa
     de que otra cosa entró a competir a mitad de la tanda.
  B. Nivel de proceso: lanzar `cmd /c exit` (con tope de 20 s, un testigo que
     puede tumbar la medición no es un testigo) antes y después de la tanda
     completa -- worker1 está en el carril GPU usando la CPU en paralelo.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-oraculo-n9/medir_oraculo.py
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
    tmp = tempfile.mkdtemp(prefix="filex-n9-")
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


def main():
    tmp, permitido, existe, no_existe, prohibido = preparar()
    try:
        testigo_a = testigo_proceso()
        print("testigo de proceso (cmd /c exit), ANTES: %s" % testigo_a)

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
        print("testigo de proceso (cmd /c exit), DESPUÉS: %s" % testigo_b)
        resultado["testigo_proceso_despues"] = testigo_b
        resultado["sucia"] = testigo_a["sucia"] or testigo_b["sucia"]

        sin_e = resultado["sin_ecualizar"]
        ratio_sin = sin_e["no_existe"]["mediana_us"] / sin_e["prohibido"]["mediana_us"]
        eq = resultado["ecualizado"]
        ratio_eq = eq["no_existe"]["mediana_us"] / eq["prohibido"]["mediana_us"]
        resultado["ratio_no_existe_sobre_prohibido"] = {
            "sin_ecualizar": round(ratio_sin, 2), "ecualizado": round(ratio_eq, 2)}
        print("\nratio no_existe/prohibido: sin ecualizar=%.2fx, ecualizado=%.2fx"
              % (ratio_sin, ratio_eq))

        with open(os.path.join(os.path.dirname(__file__), "resultado.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(resultado, fh, indent=1, ensure_ascii=False)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
