# -*- coding: utf-8 -*-
"""C36-7 -- "el coste de un `convert` con ruta denegada, que gasta un
`job_id`" (`bench/hito4-mcp.md` §8.6, `bench/gotenberg-y-mcp.md` §C36).

Mide `Servicio.convert()` end a end (la parte SINCRONA: `_arrancar` espera a
que el candado del hilo este tomado antes de volver -- ver su docstring --
asi que el tiempo medido incluye job_id + escritura a disco del trabajo +
arranque de hilo + espera del candado, no la conversion en si).

`fx.convertir` se monkeypatchea a un stub rapido para que la parte ASINCRONA
(el motor de verdad) no gaste Docker/CPU en las N repeticiones -- el punto
de esta medida es el coste de SERVICIO, no el del motor, y ese coste ya
esta medido en otros informes.

Compara DOS ROUTINGS de la misma `Servicio.convert()`:
  - "sin_gate": la ruta denegada solo se descubre DENTRO del hilo (el
    codigo antes de C36-7): job_id, disco y candado se pagan igual para
    valido y denegado.
  - "con_gate": `Servicio.convert()` llama a `fx.validar()` ANTES de
    `trabajos.nuevo()` (C36-7) -- una ruta denegada nunca llega a pedir un
    `job_id`.

`Trabajos()` apunta a un directorio PROPIO (no al `%TEMP%/filex-trabajos`
por defecto, compartido por toda la maquina) para no interferir con ningun
otro proceso `filex` que pueda estar corriendo.

    D:\\Work\\research\\FileX\\.venv-mcp-filex\\Scripts\\python.exe bench/salidas-suelo-n32/medir_job_denegado.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
import types

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

from filex.nucleo import Conversion, FileX  # noqa: E402
from filex.servicio import Servicio, Trabajos  # noqa: E402

N = 200  # esto SI toca disco (job_id) en la via valida/sin_gate: n menor que el resolver aislado


def _fx_convertir_stub(self, entrada, salida, pedido=None, *, timeout=None):
    return Conversion(entrada=entrada, salida=salida, ok=True, camino=None)


def preparar():
    tmp = tempfile.mkdtemp(prefix="filex-n32-job-")
    permitido = os.path.join(tmp, "permitido")
    os.makedirs(permitido)
    entrada_valida = os.path.join(permitido, "e.txt")
    with open(entrada_valida, "w", encoding="utf-8") as fh:
        fh.write("x")
    entrada_denegada = os.path.join(tmp, "fuera", "d.txt")
    salida = os.path.join(permitido, "out.pdf")
    return tmp, permitido, entrada_valida, entrada_denegada, salida


def construir_servicio(permitido, dir_trabajos, *, con_gate):
    fx = FileX(raices_lectura=[permitido], ecualizar_temporal=False)
    fx.convertir = types.MethodType(_fx_convertir_stub, fx)
    srv = Servicio(fx, Trabajos(directorio=dir_trabajos))
    if con_gate:
        _instrumentar_gate(srv)
    return srv, fx


def _instrumentar_gate(srv: Servicio) -> None:
    """C36-7: reproduce el parche de `Servicio.convert()` sin editar
    `filex/servicio.py` para este experimento -- envuelve el metodo real
    con el gate `fx.validar()` ANTES de `trabajos.nuevo()`. El parche real,
    si se adopta, va en `filex/servicio.py`; esto solo AISLA su efecto para
    medirlo antes/despues en el mismo proceso."""
    original = Servicio.convert.__get__(srv, Servicio)

    def convert_con_gate(entrada, salida, formato_destino="", parametros=None,
                         timeout_s=None):
        if not srv.fx.validar(entrada, salida):
            return srv._denegado()
        return original(entrada, salida, formato_destino, parametros, timeout_s)

    srv.convert = convert_con_gate


def medir(srv, entrada, salida, n=N):
    tiempos = []
    ids = []
    for _ in range(n):
        ini = time.perf_counter()
        r = srv.convert(entrada, salida)
        tiempos.append(time.perf_counter() - ini)
        if "job_id" in r:
            ids.append(r["job_id"])
    return tiempos, ids


def resumen(tiempos, ids):
    return {
        "mediana_us": round(statistics.median(tiempos) * 1e6, 2),
        "p90_us": round(statistics.quantiles(tiempos, n=10)[8] * 1e6, 2)
        if len(tiempos) >= 10 else None,
        "n": len(tiempos),
        "job_ids_gastados": len(ids),
    }


def main():
    tmp, permitido, entrada_valida, entrada_denegada, salida = preparar()
    resultado = {}
    try:
        for etiqueta, con_gate in (("sin_gate", False), ("con_gate", True)):
            dir_trabajos = os.path.join(tmp, f"trabajos-{etiqueta}")
            srv, fx = construir_servicio(permitido, dir_trabajos, con_gate=con_gate)
            resultado[etiqueta] = {}
            for nombre, ent in (("prohibido", entrada_denegada),
                               ("existe", entrada_valida)):
                t, ids = medir(srv, ent, salida)
                # Deja que los hilos en vuelo terminen antes de la siguiente celda.
                time.sleep(0.2)
                resultado[etiqueta][nombre] = resumen(t, ids)
                print("%-10s %-10s mediana=%9.2f us  p90=%9s us  job_ids=%d/%d"
                      % (etiqueta, nombre, resultado[etiqueta][nombre]["mediana_us"],
                         str(resultado[etiqueta][nombre]["p90_us"]),
                         resultado[etiqueta][nombre]["job_ids_gastados"], N))

        sg, cg = resultado["sin_gate"], resultado["con_gate"]
        resultado["comparacion"] = {
            "prohibido_mediana_us": {"sin_gate": sg["prohibido"]["mediana_us"],
                                      "con_gate": cg["prohibido"]["mediana_us"]},
            "existe_mediana_us": {"sin_gate": sg["existe"]["mediana_us"],
                                   "con_gate": cg["existe"]["mediana_us"]},
            "job_ids_gastados_en_denegado": {"sin_gate": sg["prohibido"]["job_ids_gastados"],
                                              "con_gate": cg["prohibido"]["job_ids_gastados"]},
        }
        print("\njob_id gastados en 'prohibido' (de %d intentos): sin_gate=%d  con_gate=%d"
              % (N, sg["prohibido"]["job_ids_gastados"], cg["prohibido"]["job_ids_gastados"]))
        print("coste mediana 'prohibido': %.2f us (sin_gate) -> %.2f us (con_gate)"
              % (sg["prohibido"]["mediana_us"], cg["prohibido"]["mediana_us"]))
        print("coste mediana 'existe' (via valida, no debe subir mucho): %.2f us (sin_gate) -> %.2f us (con_gate)"
              % (sg["existe"]["mediana_us"], cg["existe"]["mediana_us"]))

        with open(os.path.join(os.path.dirname(__file__), "resultado_job_denegado.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(resultado, fh, indent=1, ensure_ascii=False)
    finally:
        import shutil
        time.sleep(0.5)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
