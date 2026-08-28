"""¿Dónde se van los ~590 µs del candado de fichero?

Publicar un coste sin saber qué lo domina es publicar un número que nadie puede
mejorar. Cada fila añade UNA operación a la anterior, en la misma tanda.
"""

from __future__ import annotations

import json
import os
import shutil
import statistics
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)

from filex import nucleo  # noqa: E402

N = 20_000


def med(fn) -> float:
    v = []
    for _ in range(N):
        t0 = time.perf_counter()
        fn()
        v.append((time.perf_counter() - t0) * 1e6)
    return round(statistics.median(v), 2)


def main() -> int:
    base = os.path.join(AQUI, "desechable", "desglose")
    shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base, exist_ok=True)
    os.environ["FILEX_CERROJO_DESTINO"] = "maquina"
    clave = nucleo._clave_destino(os.path.join(base, "x.webp"))
    lock = nucleo._fichero_cerrojo(clave)
    for _ in range(500):  # calentar (trampa 7)
        nucleo._soltar_candado(nucleo._tomar_candado(clave)[0], clave)

    filas = {}

    def a():
        fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
        os.close(fd)
    filas["1. open(O_CREAT)+close"] = med(a)

    def b():
        fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
        nucleo._bloquear_fd(fd)
        os.close(fd)
    filas["2. + locking/flock"] = med(b)

    def c():
        fd, _ = nucleo._tomar_candado(clave)
        os.close(fd)
    filas["3. + ftruncate+write (metadatos)"] = med(c)

    def d():
        fd, _ = nucleo._tomar_candado(clave)
        nucleo._soltar_candado(fd, clave)
    filas["4. + unlock + remove (ciclo entero)"] = med(d)

    def e():
        fd, _ = nucleo._tomar_candado(clave)
        try:
            if nucleo._ES_WINDOWS:
                import msvcrt
                os.lseek(fd, nucleo._OFFSET_CERROJO, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        os.close(fd)
    filas["5. ciclo SIN el remove final"] = med(e)

    def f_():
        fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
        nucleo._bloquear_fd(fd)
        nucleo._soltar_candado(fd, clave)
    filas["6. ciclo entero SIN los metadatos"] = med(f_)

    print(json.dumps(filas, ensure_ascii=False, indent=1))
    with open(os.path.join(AQUI, "desglose.json"), "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)
    try:
        os.remove(lock)
    except OSError:
        pass
    shutil.rmtree(base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
