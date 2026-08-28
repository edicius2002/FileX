"""El TERCERO: un proceso que no pasa por FileX y toca el destino.

Tres modos, y el que importa es `esperar`:

* `abrir`     — abre la ruta y se queda con ella abierta hasta que se le mate o
                agote su tope. Es el ocupante que la DETECCIÓN sí ve.
* `esperar`   — espera a que aparezca un fichero centinela y **entonces** abre o
                crea la ruta, anotando el reloj exacto en que lo consiguió. Es
                el que se cuela en la ventana.
* `martillo`  — crea y abre la ruta en bucle apretado, sin sincronizar con
                nadie. Es el control «sin gancho»: si el atropello sale también
                aquí, la ventana no la fabrica el arnés.

Todos escriben un JSON en `--registro` con el reloj de cada cosa, porque la
trampa 38 dice que hay que registrar **si la condición se dio**, no solo el
resultado. Y todos llevan tope propio: la trampa 52 es que el tope del cliente
no basta.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

# El mismo reloj en los dos procesos, y la elección **está sondeada, no
# deducida** (`sonda_reloj.json`):
#
# * `time.time_ns()` es comparable entre procesos y **tiene 15,625 ms de
#   resolución en esta máquina** (`time.get_clock_info('time').resolution`).
#   Con él, una ventana de microsegundos sale «0 ns» o «1 000 100 ns», que es
#   el tamaño del tic y no el de la ventana. La primera pasada de este arnés lo
#   usó y publicó ~1 ms de mediana: era el reloj, no el código.
# * `time.perf_counter_ns()` da 100 ns **y en Windows es `QueryPerformanceCounter`
#   crudo**, sin origen por proceso: MEDIDO, `perf_counter_ns() == QPC × 100`
#   con la frecuencia de 10 MHz de esta máquina. Así que aquí sí es comparable
#   entre procesos, aunque la documentación solo lo garantice dentro de uno.
reloj = time.perf_counter_ns


def _escribir(registro: str, datos: dict) -> None:
    tmp = registro + ".parcial"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.replace(tmp, registro)


def modo_abrir(ruta: str, registro: str, tope: float, contenido: bytes) -> None:
    datos = {"modo": "abrir", "ruta": ruta}
    with open(ruta, "wb") as f:
        f.write(contenido)
        f.flush()
        os.fsync(f.fileno())
        datos["abierto_ns"] = reloj()
        datos["bytes_escritos"] = len(contenido)
        _escribir(registro, datos)
        # Se queda con el asa. El tope es suyo, no del que le lanzó.
        fin = time.monotonic() + tope
        while time.monotonic() < fin:
            time.sleep(0.02)
    datos["cerrado_ns"] = reloj()
    _escribir(registro, datos)


def modo_esperar(ruta: str, registro: str, tope: float, centinela: str,
                 contenido: bytes) -> None:
    datos = {"modo": "esperar", "ruta": ruta, "centinela_visto_ns": None,
             "abierto_ns": None, "error": ""}
    _escribir(registro, datos)
    fin = time.monotonic() + tope
    while time.monotonic() < fin:
        if os.path.exists(centinela):
            datos["centinela_visto_ns"] = reloj()
            break
    else:
        datos["error"] = "el centinela no llegó"
        _escribir(registro, datos)
        return
    try:
        # `x`/`w` binario: si no existe lo crea, si existe lo abre. Es el
        # escritor de un tercero cualquiera, con el modo compartido POR DEFECTO
        # de CPython (que incluye FILE_SHARE_DELETE, y eso importa).
        f = open(ruta, "ab")
    except OSError as e:
        datos["error"] = f"{e.__class__.__name__}: {getattr(e, 'winerror', '')}"
        datos["fallo_ns"] = reloj()
        _escribir(registro, datos)
        return
    with f:
        f.write(contenido)
        f.flush()
        datos["abierto_ns"] = reloj()
        datos["bytes_escritos"] = len(contenido)
        _escribir(registro, datos)
        resto = fin - time.monotonic()
        if resto > 0:
            time.sleep(min(resto, 3.0))
    datos["cerrado_ns"] = reloj()
    _escribir(registro, datos)


def modo_martillo(ruta: str, registro: str, tope: float, contenido: bytes,
                  pausa: float = 0.0) -> None:
    """Abre, escribe en el offset 0 y cierra, en bucle apretado.

    **Dos detalles del arnés que costaron una tanda cada uno:**

    * **No se puede topar la lista de relojes.** La primera versión guardaba
      solo las 5 000 primeras aperturas de las ~40 000 de una tanda, así que
      `la_ventana_se_abrio` salía `False` en celdas en las que sí se había
      abierto: se estaba mirando el principio del bucle, no la ventana. Es la
      trampa 38 dentro del propio registro de la trampa 38.
    * **No se abre en modo `append`.** Con `ab` el fichero crecía hasta 76 MB en
      seis segundos y el escenario dejaba de ser «un tercero toca el destino»
      para ser «un tercero llena el disco».
    """
    datos = {"modo": "martillo", "ruta": ruta, "intentos": 0, "aberturas": 0,
             "aperturas_ns": [], "cierres_ns": [], "errores": {}}
    fin = time.monotonic() + tope
    while time.monotonic() < fin:
        datos["intentos"] += 1
        try:
            try:
                f = open(ruta, "r+b")
            except FileNotFoundError:
                f = open(ruta, "wb")
            with f:
                datos["aperturas_ns"].append(reloj())
                f.seek(0)
                f.write(contenido)
                f.truncate()
                datos["aberturas"] += 1
            datos["cierres_ns"].append(reloj())
        except OSError as e:
            k = f"{e.__class__.__name__}:{getattr(e, 'winerror', '')}"
            datos["errores"][k] = datos["errores"].get(k, 0) + 1
        if pausa:
            # **La pausa NO es cosmética.** Sin ella el martillo tiene el
            # destino abierto casi todo el tiempo, la detección PREVIA lo caza
            # y salen 11 de 12 `fallo` **antes** de que exista ventana ninguna:
            # el control deja de controlar nada (MEDIDO, tanda `C-E2-antes`
            # con pausa 0 → `se_abrio` 1 de 12). Con pausa, el destino está
            # libre la mayor parte del tiempo y el tercero solo puede colarse
            # donde de verdad hay hueco.
            time.sleep(pausa)
    _escribir(registro, datos)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--modo", required=True,
                   choices=("abrir", "esperar", "martillo"))
    p.add_argument("--ruta", required=True)
    p.add_argument("--registro", required=True)
    p.add_argument("--centinela", default="")
    p.add_argument("--tope", type=float, default=30.0)
    p.add_argument("--bytes", type=int, default=4014)
    p.add_argument("--pausa", type=float, default=0.0,
                   help="segundos entre golpes del martillo")
    a = p.parse_args(argv)
    # 4 014 B: el mismo tamaño del fichero ajeno que FileX pisó en
    # `bench/cerrojo-de-maquina.md` §5. No es decorativo: hace reconocible en
    # el disco quién ganó.
    contenido = b"T" * a.bytes
    if a.modo == "abrir":
        modo_abrir(a.ruta, a.registro, a.tope, contenido)
    elif a.modo == "esperar":
        modo_esperar(a.ruta, a.registro, a.tope, a.centinela, contenido)
    else:
        modo_martillo(a.ruta, a.registro, a.tope, contenido, a.pausa)
    return 0


if __name__ == "__main__":
    sys.exit(main())
