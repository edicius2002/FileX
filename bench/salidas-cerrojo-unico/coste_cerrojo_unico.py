"""Lo que cuesta el cerrojo ya extraído, TODO en la misma tanda.

Las cifras absolutas de tandas distintas no son comparables en esta máquina, y
hoy hay otro agente trabajando: por eso las cuatro configuraciones y la
conversión de referencia se miden **aquí dentro**, y por eso el informe compara
porcentajes y no milisegundos con los 976,6 µs de N-b.

Dos testigos de ruido, como manda `CLAUDE.md` §3: el bucle monohilo mide la
**deriva dentro** de la tanda, el lanzamiento de proceso mide el **nivel** de
carga de la máquina — y **el testigo lleva su propio tope de 20 s**, porque un
testigo que puede tumbar la medición no es un testigo (caso P3, ×94,6).
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, RAIZ)

N = 20000
TOPE_TESTIGO = 20


def _mediana_p90(xs):
    xs = sorted(xs)
    return round(statistics.median(xs), 1), round(xs[int(len(xs) * 0.9)], 1)


def testigo_monohilo() -> float:
    """Deriva: el mismo bucle al principio y al final de la tanda."""
    t = time.perf_counter()
    s = 0
    for i in range(400000):
        s += i * i
    return (time.perf_counter() - t) * 1000


def testigo_proceso() -> float:
    """Nivel: lanzar un proceso. Con tope propio."""
    t = time.perf_counter()
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=TOPE_TESTIGO)
    except Exception:
        return TOPE_TESTIGO * 1000.0
    return (time.perf_counter() - t) * 1000


def medir_reserva(nucleo, ruta: str, n: int = N):
    for _ in range(300):                       # calentamiento (trampa 7)
        nucleo._reservar_destino(ruta)
        nucleo._soltar_destino(ruta)
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        nucleo._reservar_destino(ruta)
        nucleo._soltar_destino(ruta)
        xs.append((time.perf_counter() - t) * 1e6)
    return xs


def main() -> int:
    res: dict = {"cuando": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": N}
    base = tempfile.mkdtemp(prefix="filex-coste-")
    antes = sorted(os.listdir(base))
    destino = os.path.join(base, "salida.webp")

    d0 = testigo_monohilo()
    n0 = testigo_proceso()
    print(f"testigos al empezar: deriva {d0:.1f} ms · proceso {n0:.1f} ms")

    from filex import cerrojo, nucleo

    # --- las cuatro configuraciones, en la misma tanda ----------------------
    conf = {}
    escenas = [
        ("maquina (mutex + identidad) = LO NUEVO", {"FILEX_CERROJO_DESTINO": "maquina"}),
        ("maquina SIN mutex = el cerrojo de N-b", {"FILEX_CERROJO_DESTINO": "maquina",
                                                   "FILEX_CERROJO_MUTEX": "0"}),
        ("maquina SIN identidad", {"FILEX_CERROJO_DESTINO": "maquina",
                                   "FILEX_CERROJO_IDENTIDAD": "0"}),
        ("proceso (el hito 7)", {"FILEX_CERROJO_DESTINO": "proceso"}),
        ("ninguno", {"FILEX_CERROJO_DESTINO": "ninguno"}),
    ]
    for etiqueta, env in escenas:
        for k in ("FILEX_CERROJO_DESTINO", "FILEX_CERROJO_MUTEX",
                  "FILEX_CERROJO_IDENTIDAD"):
            os.environ.pop(k, None)
        os.environ.update(env)
        med, p90 = _mediana_p90(medir_reserva(nucleo, destino))
        conf[etiqueta] = {"mediana_us": med, "p90_us": p90}
        print(f"  {etiqueta:42s} mediana {med:8.1f} us   p90 {p90:8.1f}")
    for k in ("FILEX_CERROJO_DESTINO", "FILEX_CERROJO_MUTEX",
              "FILEX_CERROJO_IDENTIDAD"):
        os.environ.pop(k, None)
    res["configuraciones"] = conf

    # --- los trozos ---------------------------------------------------------
    print("-- desglose --")
    trozos = {}
    nombre = f"filex-coste-{os.getpid()}"
    for _ in range(300):
        c = cerrojo.Candado(nombre)
        c.tomar()
        c.soltar()
    xs = []
    for _ in range(N):
        t = time.perf_counter()
        h, ocu, av = cerrojo._tomar_mutex(nombre, 0)
        cerrojo._soltar_mutex(h)
        xs.append((time.perf_counter() - t) * 1e6)
    trozos["solo el mutex Global"] = dict(zip(("mediana_us", "p90_us"),
                                              _mediana_p90(xs)))
    xs = []
    for _ in range(N):
        t = time.perf_counter()
        nucleo._clave_destino(destino)
        xs.append((time.perf_counter() - t) * 1e6)
    trozos["clave lexica (realpath del dir)"] = dict(
        zip(("mediana_us", "p90_us"), _mediana_p90(xs)))
    xs = []
    for _ in range(N):
        t = time.perf_counter()
        nucleo._identidad_destino(destino)
        xs.append((time.perf_counter() - t) * 1e6)
    trozos["identidad NTFS, destino que NO existe"] = dict(
        zip(("mediana_us", "p90_us"), _mediana_p90(xs)))
    with open(destino, "wb") as f:
        f.write(b"x" * 64)
    xs = []
    for _ in range(N):
        t = time.perf_counter()
        nucleo._identidad_destino(destino)
        xs.append((time.perf_counter() - t) * 1e6)
    trozos["identidad NTFS, destino que SI existe"] = dict(
        zip(("mediana_us", "p90_us"), _mediana_p90(xs)))
    xs = []
    for _ in range(N):
        t = time.perf_counter()
        nucleo.destino_ocupado_por_un_tercero(destino)
        xs.append((time.perf_counter() - t) * 1e6)
    trozos["deteccion, destino que SI existe"] = dict(
        zip(("mediana_us", "p90_us"), _mediana_p90(xs)))
    os.remove(destino)
    xs = []
    for _ in range(N):
        t = time.perf_counter()
        nucleo.destino_ocupado_por_un_tercero(destino)
        xs.append((time.perf_counter() - t) * 1e6)
    trozos["deteccion, destino que NO existe (el caso normal)"] = dict(
        zip(("mediana_us", "p90_us"), _mediana_p90(xs)))
    for k, v in trozos.items():
        print(f"  {k:42s} mediana {v['mediana_us']:8.1f} us")
    res["trozos"] = trozos

    # --- la conversión de referencia, para el porcentaje --------------------
    print("-- conversion png->webp de referencia --")
    try:
        from filex.nucleo import FileX

        entrada = os.path.join(base, "tipico.png")
        with open(os.path.join(RAIZ, "corpus", "imagen", "tipico.png"), "rb") as f:
            datos = f.read()
        with open(entrada, "wb") as f:
            f.write(datos)
        fx = FileX(raices_lectura=[base])
        ms = []
        for i in range(11):
            sal = os.path.join(base, f"conv{i}.webp")
            t = time.perf_counter()
            fx.convertir(entrada, sal)
            ms.append((time.perf_counter() - t) * 1000)
            try:
                os.remove(sal)
            except OSError:
                pass
        med, p90 = _mediana_p90(ms)
        res["conversion_ms"] = {"mediana": med, "p90": p90, "n": len(ms)}
        print(f"  mediana {med:.1f} ms   p90 {p90:.1f} ms   (n={len(ms)})")
    except Exception as e:            # noqa: BLE001
        res["conversion_ms"] = {"error": f"{e.__class__.__name__}: {e}"}
        print(f"  FALLO: {e}")

    d1 = testigo_monohilo()
    n1 = testigo_proceso()
    deriva = d1 / d0 if d0 else 0
    limpia = 0.7 <= deriva <= 1.4 and max(n0, n1) < TOPE_TESTIGO * 1000
    res["testigos"] = {"deriva_ini_ms": round(d0, 1), "deriva_fin_ms": round(d1, 1),
                       "deriva": round(deriva, 2),
                       "proceso_ini_ms": round(n0, 1), "proceso_fin_ms": round(n1, 1),
                       "etiqueta": "limpia" if limpia else "SUCIA"}
    print(f"testigos al acabar: deriva {d1:.1f} ms (x{deriva:.2f}) · "
          f"proceso {n1:.1f} ms -> {res['testigos']['etiqueta']}")

    despues = sorted(os.listdir(base))
    res["R21"] = {"antes": antes, "despues": despues}
    print(f"R21: antes={antes} despues={despues}")
    with open(os.path.join(AQUI, "coste.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    subprocess.run(["cmd", "/c", "rmdir", "/S", "/Q", base], capture_output=True,
                   timeout=60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
