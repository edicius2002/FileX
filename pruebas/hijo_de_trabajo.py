"""Un proceso `filex` de verdad, para probar lo que es ENTRE PROCESOS.

N10 dice que cancelar deja de ser de proceso. Eso **no se puede probar con dos
`Servicio` en el mismo intérprete**: comparten el registro de `filex.invocacion`
y el resultado saldría verde sin que exista el canal. Es exactamente la forma de
la trampa 38 (*«un arnés de carrera que espera al hilo mide la carrera
equivocada, y sale verde»*), así que aquí hay un proceso separado.

El hijo habla por `stdout`, una línea JSON por evento, y **con `flush`**:

    {"evento": "arrancado", "job_id": ..., "pid": ...}
    {"evento": "en_vuelo"}                      # el motor ya tiene un `Popen`
    {"evento": "fin", "estado": ..., "ms": ...}

Uso (lo llama `pruebas/test_cancelacion_procesos.py`, no una persona)::

    python pruebas/hijo_de_trabajo.py --trabajos DIR --entrada F --salida F

`--no-mando` pone `FILEX_MANDO=0` dentro del hijo para medir el ANTES en la
misma tanda.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)


def _pids_motores() -> list[int]:
    """Los PID de los motores que este proceso tiene en vuelo.

    Hace falta para poder matar al DUEÑO sin dejar el motor huérfano: si se
    mata primero al dueño, el motor pierde a su padre y `taskkill /T` sobre el
    abuelo ya no lo alcanza. Se barre **por identidad, no por nombre** —trampa
    47—, y por eso el identificador tiene que salir de aquí.

    Lee el registro privado de `invocacion` a propósito: es un arnés, y añadir
    un accesor público a `filex/` por comodidad de una prueba movería el AST de
    un módulo sellado (trampas 32 y 97). El `pid` de un motor **sí** es el de
    verdad: la trampa 93 es del `python.exe` de un venv, que es un lanzador;
    `ffmpeg.exe` no lo es.
    """
    from filex import invocacion as _inv
    with _inv._CERROJO_VUELO:                            # noqa: SLF001
        return [proc.pid for proc, _ in _inv._EN_VUELO.values()]


def di(**kw) -> None:
    sys.stdout.write(json.dumps(kw, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--trabajos", required=True)
    p.add_argument("--entrada", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--no-mando", action="store_true")
    p.add_argument("--tope", type=float, default=120.0)
    a = p.parse_args()

    if a.no_mando:
        os.environ["FILEX_MANDO"] = "0"

    from filex import invocacion, servicio as S
    from filex.nucleo import FileX

    sv = S.Servicio(FileX(), S.Trabajos(a.trabajos))
    t0 = time.perf_counter()
    r = sv.convert(a.entrada, a.salida)
    if "job_id" not in r:
        di(evento="error", detalle=r)
        return 2
    di(evento="arrancado", job_id=r["job_id"], pid=os.getpid(),
       aviso_cerrojo=r.get("aviso_cerrojo", ""))

    t = sv.trabajos.get(r["job_id"])
    # Se avisa cuando el motor está REALMENTE en vuelo. Cancelar antes mediría
    # la ventana entre saltos, que es otra prueba — trampa 38.
    limite = time.perf_counter() + a.tope
    while invocacion.en_vuelo() == 0 and time.perf_counter() < limite:
        time.sleep(0.01)
    di(evento="en_vuelo", hay=invocacion.en_vuelo() > 0,
       motores=_pids_motores())

    if t is not None and t.hilo is not None:
        t.hilo.join(timeout=a.tope)
    di(evento="fin", estado=(t.estado if t is not None else "?"),
       ms=round((time.perf_counter() - t0) * 1000, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
