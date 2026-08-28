"""Sonda de los primitivos de cerrojo — «sondear en ejecución, no deducir».

Antes de elegir el mecanismo del cerrojo de máquina hay que MEDIR qué hace cada
primitivo en ESTA máquina (Windows 10, Python 3.11.9), porque los tres
candidatos tienen semántica distinta y la documentación no basta:

  A. `os.open(O_CREAT|O_EXCL)`     — exclusión, pero el huérfano queda para siempre
  B. `msvcrt.locking(LK_NBLCK)`    — bloqueo de rango de bytes, lo suelta el SO
  C. `os.replace(p, p)`            — el detector de la trampa 27

Se ejecuta con un hijo que toma el candado y se queda quieto, y el padre
comprueba desde FUERA del proceso. Sin esto, todo lo demás es deducción.

    python bench/salidas-cerrojo/sonda_primitivos.py            (padre)
    python bench/salidas-cerrojo/sonda_primitivos.py hijo RUTA  (hijo)
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

_ES_WINDOWS = sys.platform == "win32"
OFFSET = 1 << 30  # el byte que se bloquea, lejos de los metadatos


def _bloquear(fd: int) -> None:
    if _ES_WINDOWS:
        import msvcrt
        os.lseek(fd, OFFSET, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def hijo(ruta: str) -> int:
    fd = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o600)
    os.write(fd, f"pid={os.getpid()}\n".encode())
    _bloquear(fd)
    print("HIJO: candado tomado", flush=True)
    time.sleep(60)
    return 0


def hijo_lector(ruta: str) -> int:
    """Solo ABRE PARA LEER. Sirve para saber si `os.replace(p,p)` distingue
    «alguien lo está escribiendo» de «alguien lo está leyendo»."""
    f = open(ruta, "rb")
    f.read(1)
    print("HIJO: abierto para lectura", flush=True)
    time.sleep(30)
    f.close()
    return 0


def _intenta(nombre, fn):
    try:
        fn()
        print(f"  {nombre:<42} -> OK")
        return True
    except OSError as e:
        print(f"  {nombre:<42} -> OSError winerror={getattr(e, 'winerror', None)} "
              f"errno={e.errno} {e.strerror}")
        return False


def padre() -> int:
    base = os.environ.get("TEMP") or "/tmp"
    ruta = os.path.join(base, "filex-sonda-primitivos.lock")
    for p in (ruta, ruta + ".2"):
        if os.path.exists(p):
            os.remove(p)

    print(f"ruta = {ruta}")
    print("== 0. con el fichero LIBRE (nadie lo tiene abierto) ==")
    fd0 = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o600)
    os.close(fd0)
    _intenta("os.replace(p, p) sobre fichero libre", lambda: os.replace(ruta, ruta))
    _intenta("os.remove(p) sobre fichero libre", lambda: os.remove(ruta))

    print("\n== 1. arranco un hijo que toma el candado y se duerme ==")
    proc = subprocess.Popen([sys.executable, __file__, "hijo", ruta],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True)
    linea = proc.stdout.readline().strip()
    print(f"  {linea}   (pid del hijo: {proc.pid})")

    print("\n== 2. desde el PADRE, con el hijo vivo ==")
    fd = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o600)
    t0 = time.perf_counter()
    tomado = _intenta("msvcrt.locking / flock (candado ajeno vivo)",
                      lambda: _bloquear(fd))
    print(f"  (el intento costó {(time.perf_counter() - t0) * 1e6:.1f} us)")
    _intenta("os.open(O_CREAT|O_EXCL) sobre el mismo fichero",
             lambda: os.close(os.open(ruta, os.O_RDWR | os.O_CREAT | os.O_EXCL)))
    _intenta("os.replace(p, p) con el hijo teniéndolo abierto",
             lambda: os.replace(ruta, ruta))
    _intenta("os.remove(p) con el hijo teniéndolo abierto", lambda: os.remove(ruta))
    print("  metadatos legibles desde fuera: "
          f"{open(ruta, 'rb').read(40)!r}")
    os.close(fd)

    print("\n== 3. mato al hijo con taskkill /F (no ejecuta ningún `finally`) ==")
    if _ES_WINDOWS:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=30)
    else:
        proc.kill()
    proc.wait(timeout=30)
    print(f"  hijo muerto, rc={proc.returncode}; el fichero sigue: "
          f"{os.path.exists(ruta)}")

    print("\n== 4. desde el PADRE, con el dueño MUERTO ==")
    fd = os.open(ruta, os.O_RDWR | os.O_CREAT, 0o600)
    t0 = time.perf_counter()
    ok = _intenta("msvcrt.locking / flock (dueño muerto)", lambda: _bloquear(fd))
    print(f"  (recuperación en {(time.perf_counter() - t0) * 1e6:.1f} us)")
    os.close(fd)
    _intenta("os.replace(p, p) con el dueño muerto", lambda: os.replace(ruta, ruta))
    print("\n== 5. ¿el detector distingue LECTOR de ESCRITOR? ==")
    lector = subprocess.Popen([sys.executable, __file__, "lector", ruta],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, text=True)
    print(f"  {lector.stdout.readline().strip()}   (pid {lector.pid})")
    solo_lectura = not _intenta("os.replace(p, p) con un LECTOR abierto",
                                lambda: os.replace(ruta, ruta))
    if _ES_WINDOWS:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(lector.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    else:
        lector.kill()
    lector.wait(timeout=30)

    print(f"\nRESUMEN: candado ajeno vivo bloquea = {not tomado}; "
          f"se recupera solo al morir el dueño = {ok}; "
          f"el detector también dispara con un LECTOR = {solo_lectura}")
    if os.path.exists(ruta):
        os.remove(ruta)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "hijo":
        raise SystemExit(hijo(sys.argv[2]))
    if len(sys.argv) > 2 and sys.argv[1] == "lector":
        raise SystemExit(hijo_lector(sys.argv[2]))
    raise SystemExit(padre())
